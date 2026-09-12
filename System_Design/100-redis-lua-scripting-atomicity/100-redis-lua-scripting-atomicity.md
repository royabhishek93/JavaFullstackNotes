# Redis Lua Scripting: EVAL/EVALSHA for Atomic Multi-Step Operations
### How to make "check, then act" safe in a database where every OTHER client's commands are also racing to run

---

## PART 1 — THE STUDENT CONVERSATION

Imagine Redis as a single bank teller window with one teller, serving one customer's full request before starting the next. If your entire request is "give me the balance of account 42" — one atomic step — you're safe, no other customer's transaction can interleave with yours.

But now imagine YOUR "request" is actually three separate trips to the window: "what's the balance?" (trip 1), you walk away to do math in your head, then come back and say "okay, subtract $50" (trip 2). Between trip 1 and trip 2, the teller served twenty other customers. Someone else could have already withdrawn from that account. Your math, done outside the teller window, is now stale — a classic **check-then-act race condition**.

This is exactly what happens with plain Redis commands issued from application code: `GET lock:order42` (check who owns it), then in your Java/Python code compare the value, then `DEL lock:order42` (act on it). Redis guarantees each *individual* command (`GET`, `DEL`) is atomic — but it guarantees NOTHING about what happens in between two separate commands from your application. Another client's command can slide into that gap.

The fix: instead of doing the "check" and the "act" as two separate trips to the teller window, you hand the teller a **single written note** with the entire procedure on it: "check the balance, and IF it's over $50, THEN subtract $50, otherwise do nothing — and don't let anyone else at the window while you're reading this note." That note is a **Lua script**. Redis executes the whole script as one indivisible unit, server-side, with its single-threaded command loop guaranteeing no other client's command executes in the middle. `GET`, comparison, and `DEL` all happen as if they were one atomic Redis command.

This is precisely the tool needed to safely release a distributed lock (see [022-redlock-distributed-lock.md](022-redlock-distributed-lock.md)) — you must check "is this still MY lock?" and delete it in the same breath, or you risk deleting someone else's lock that was acquired after yours expired. It's also the exact mechanism behind the atomic "confirm hold" step in [099-two-phase-inventory-locking-soft-hold-ttl.md](099-two-phase-inventory-locking-soft-hold-ttl.md).

---

## PART 2 — THE LUA ATOMICITY ARCHITECTURE DIAGRAMS

### The Race: Separate Commands vs One Atomic Script

```
SCENARIO: Client A wants to unlock resource "order:42", but ONLY if it still
          owns the lock (its token matches). Lock TTL just expired.

────────────────────────────────────────────────────────────────────────────
 UNSAFE: Two separate round trips (GET, then application logic, then DEL)
────────────────────────────────────────────────────────────────────────────

Client A                        Redis Server                    Client B
─────────                       ────────────                    ─────────
GET lock:order42        ──────>  value = "tokenA"
                         <──────  returns "tokenA"
   [Client A now holds
    "tokenA" in its own
    process memory, compares
    it to its own token: MATCH]

    [~2ms network + GC pause
     happens here — Redis is
     free to serve OTHER clients
     during this gap]

                                                                  SET lock:order42
                                                                    "tokenB" NX EX 30
                                  key had just expired (TTL=0)
                                  NX succeeds: lock:order42
                                  = "tokenB" now                 <────── OK

DEL lock:order42         ──────>  DELETE happens unconditionally
                                  lock:order42 is now GONE
                         <──────  (integer) 1

RESULT: Client A just deleted Client B's brand-new, legitimate lock!
        Client B THINKS it holds the lock but Redis says it's free.
        A third client, Client C, can now also acquire it.
        TWO clients believe they exclusively hold the same resource.

────────────────────────────────────────────────────────────────────────────
 SAFE: Single Lua script (GET + compare + DEL as ONE atomic unit)
────────────────────────────────────────────────────────────────────────────

Client A                        Redis Server                    Client B
─────────                       ────────────                    ─────────
EVAL unlock_script 1            ┌─────────────────────────┐
  lock:order42 "tokenA" ──────> │ ENTIRE SCRIPT RUNS ─     │
                                 │ NO OTHER COMMAND CAN     │
                                 │ INTERLEAVE, EVEN FROM    │
                                 │ CLIENT B                 │
                                 │                          │
                                 │ current = GET lock:order42
                                 │   -> "tokenA"            │
                                 │ if current == "tokenA":  │
                                 │   DEL lock:order42       │
                                 │   return 1               │
                                 └─────────────────────────┘
                         <──────  returns 1 (deleted)
                                                                  SET lock:order42
                                                                    "tokenB" NX EX 30
                                  (queued until script finishes,
                                   THEN processed — key doesn't
                                   exist anymore, so this SET
                                   legitimately succeeds)        <────── OK

RESULT: No overlap possible. Client A's unlock and Client B's lock
        acquisition are strictly ordered by Redis's single-threaded
        execution — the script is treated as one opaque command.
```

### EVAL Command Structure

```
EVAL "<lua script body>" numkeys key1 [key2 ...] arg1 [arg2 ...]
      │                   │       │                │
      │                   │       │                └─ becomes ARGV[1], ARGV[2]... inside script
      │                   │       └─ becomes KEYS[1], KEYS[2]... inside script
      │                   └─ tells Redis how many of the following params are KEYS vs ARGV
      └─ the script text itself (sent over the wire every time with EVAL)

Example call:
  EVAL "if redis.call('GET',KEYS[1])==ARGV[1] then return redis.call('DEL',KEYS[1]) else return 0 end"
       1 lock:order42 tokenA
       ▲ numkeys=1     ▲KEYS[1]  ▲ARGV[1]

WHY the KEYS[]/ARGV[] split matters (not just style):
  Redis Cluster uses KEYS[] to figure out which cluster shard/node the
  script's data lives on, so it can route the script correctly and
  reject scripts that touch keys spanning multiple shards. If you just
  hardcode key names as plain strings inside the script body instead of
  passing them via KEYS[], Redis Cluster can't validate slot ownership,
  and cross-slot scripts will error out (or behave incorrectly on a
  single-node/non-cluster setup, which hides the bug until you scale).
```

### EVALSHA + SCRIPT LOAD: Avoiding Re-Sending the Script Body

```
First time ever running this script (typically at app startup):

  Client                          Redis Server
  ──────                          ────────────
  SCRIPT LOAD "if redis.call(...)..."  ──────>  Redis compiles the script,
                                                 computes SHA1 hash of the
                                                 script TEXT, caches the
                                                 compiled script in memory
                                 <──────  returns SHA1 hash:
                                          "e0e1f9fabfc9d4800c877a703b823ac0578ff831"

  [Client stores this SHA1 in memory, reuses it for every future call —
   no need to re-send the full script text on every single lock release]

Every subsequent call (thousands of times per second, e.g. releasing
short-lived locks under high concurrency):

  Client                          Redis Server
  ──────                          ────────────
  EVALSHA "e0e1f9fa...ff831"     ──────>  Redis looks up the hash in its
    1 lock:order42 tokenA                 script cache, finds the compiled
                                           script, EXECUTES it directly —
                                           no re-parsing, no re-sending
                                           kilobytes of Lua text over the
                                           wire on every call
                                 <──────  returns 1 (or 0)

CAVEAT: if Redis restarts or the script cache is flushed (SCRIPT FLUSH,
or a failover to a replica that never saw SCRIPT LOAD), EVALSHA returns
a NOSCRIPT error. Production clients MUST catch this and fall back to
a plain EVAL (which both runs the script AND re-caches it), or proactively
re-run SCRIPT LOAD after any detected failover.

BANDWIDTH SAVING (real numbers):
  Typical lock-release script body: ~150-250 bytes of Lua text
  SHA1 hash: exactly 40 bytes (hex string)
  At 10,000 unlock calls/sec: EVAL costs ~2MB/sec in script-text overhead
                               EVALSHA costs ~0.4MB/sec (just the hash + keys/args)
  Savings compound further with larger/more complex scripts.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### The Canonical Safe-Unlock Lua Script

```lua
-- unlock.lua
-- KEYS[1] = the lock key, e.g. "lock:order42"
-- ARGV[1] = the token this client believes it owns, e.g. "8f3a9c21-uuid"
--
-- Only deletes the lock if the current value STILL matches our token.
-- This prevents deleting a lock that expired and was re-acquired by
-- a different client in the meantime (see PART 2 race diagram above).
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
```

```java
@Component
public class RedisDistributedLock {

    private final StringRedisTemplate redis;
    private final RedisScript<Long> unlockScript =
            RedisScript.of(new ClassPathResource("unlock.lua"), Long.class);

    public String acquire(String resource, Duration ttl) {
        String token = UUID.randomUUID().toString();
        Boolean acquired = redis.opsForValue()
                .setIfAbsent("lock:" + resource, token, ttl);   // SET NX EX
        return Boolean.TRUE.equals(acquired) ? token : null;
    }

    public boolean release(String resource, String token) {
        // Spring Data Redis automatically prefers EVALSHA under the hood,
        // caching the script hash and falling back to EVAL on NOSCRIPT.
        Long result = redis.execute(unlockScript,
                List.of("lock:" + resource),
                token);
        return result != null && result == 1L;
    }
}
```

### Manual EVALSHA Workflow (raw Redis CLI, to see the mechanics explicitly)

```bash
# Step 1: load the script once, get back its SHA1
redis-cli SCRIPT LOAD "$(cat unlock.lua)"
# -> "e0e1f9fabfc9d4800c877a703b823ac0578ff831"

# Step 2: check the script is cached (returns array of 1s/0s per hash queried)
redis-cli SCRIPT EXISTS e0e1f9fabfc9d4800c877a703b823ac0578ff831
# -> (integer) 1

# Step 3: call it cheaply, over and over, without resending the body
redis-cli EVALSHA e0e1f9fabfc9d4800c877a703b823ac0578ff831 1 lock:order42 8f3a9c21-uuid
# -> (integer) 1     <- deleted, we owned the lock
# or
# -> (integer) 0     <- did NOT delete, token mismatch (someone else's lock now)

# If Redis was restarted/failed over and lost the script cache:
redis-cli EVALSHA e0e1f9fabfc9d4800c877a703b823ac0578ff831 1 lock:order42 8f3a9c21-uuid
# -> (error) NOSCRIPT No matching script. Please use EVAL.
# Client-side fallback logic: catch NOSCRIPT -> re-run full EVAL (which
# also re-populates the cache) -> subsequent calls can use EVALSHA again.
```

### A Second Worked Example: Atomic Rate Limiter (Sliding Window Counter)

```lua
-- rate_limit.lua
-- KEYS[1] = counter key, e.g. "ratelimit:user:99"
-- ARGV[1] = max requests allowed in the window, e.g. "100"
-- ARGV[2] = window size in seconds, e.g. "60"
--
-- Without Lua, "INCR then check if > limit then EXPIRE if first request"
-- is three separate round trips with race windows between each.
-- As one script, it's a single atomic increment-and-check.
local current = redis.call("INCR", KEYS[1])
if current == 1 then
    -- first request in this window: set the expiry ONLY now,
    -- so the counter resets every ARGV[2] seconds
    redis.call("EXPIRE", KEYS[1], ARGV[2])
end
if current > tonumber(ARGV[1]) then
    return 0   -- rate limit exceeded, reject
else
    return 1   -- allowed
end
```

```bash
# Called on every incoming request for a given user:
EVALSHA <sha_of_rate_limit_script> 1 ratelimit:user:99 100 60
# -> 1 = allowed (request count so far <= 100 within the 60s window)
# -> 0 = rejected (429 Too Many Requests)
```

### Production Caveat: Long-Running Scripts Block Everything

```
Redis is single-threaded for command execution. A Lua script is treated
as ONE command from the scheduler's point of view — which means for the
ENTIRE duration the script runs, Redis cannot process ANY other client's
command. Not reads, not writes, not even unrelated keys on a completely
different part of the keyspace.

DANGEROUS (unbounded loop over a large dataset):
  local keys = redis.call("KEYS", "session:*")     -- could be millions
  for i, k in ipairs(keys) do
      redis.call("DEL", k)                          -- runs for SECONDS
  end
  -- Every other client (your entire production traffic) is frozen
  -- for the whole duration. This is one of the most common Redis
  -- outage causes: a "one-time cleanup script" that blocks the
  -- primary node for 5-30 seconds, during which health checks fail,
  -- connections time out, and monitoring pages the on-call engineer.

SAFE ALTERNATIVES:
  - Use SCAN (cursor-based, non-blocking) from application code instead
    of KEYS inside a script, and batch DELs across multiple small calls.
  - If a script must touch many keys, cap it: process at most N keys per
    invocation, return a cursor, and call again — never loop unbounded.
  - Configure `lua-time-limit` (default 5000ms) so Redis can at least log
    a warning ("script exceeded busy time") — but note this does NOT
    actually kill a script that's only doing writes; it only allows
    SCRIPT KILL for read-only scripts. A write-heavy runaway script may
    require a full Redis restart to recover from. Prevention, not
    detection, is the real mitigation.

REAL NUMBERS:
  Typical safe script (lock check-and-delete, rate-limit incr): <0.1ms
  Budget rule of thumb: keep scripts well under 1ms of actual server-side
  execution time; anything approaching 10ms+ under load is a red flag.
  Redis single node throughput ceiling: ~100K-200K simple ops/sec —
  a script that takes even 5ms blocks out ~500-1000 other commands'
  worth of that capacity for its own duration.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "You're implementing a distributed lock on top of Redis. Walk me through how you safely release the lock, and why a plain `GET` followed by `DEL` from your application code is a bug."

**You (architect answer):**

> "The core issue is that Redis guarantees atomicity per individual command, not across a sequence of commands issued from application code. If I do `GET lock:order42` in my Java service, compare the returned token to the one I think I own, and then issue a separate `DEL lock:order42` — there's a window between those two round trips where the lock's TTL could expire and a completely different client could legitimately acquire it. If my `DEL` fires after that, I'm not releasing my own lock anymore — I'm deleting someone else's active lock. Now two clients both believe they exclusively hold the same resource, which defeats the entire purpose of having a lock.
>
> The fix is to push the whole check-and-delete sequence into a single Lua script and run it with `EVAL`. Redis executes the entire script as one atomic unit — because Redis processes commands on a single thread, no other client's command, including a competing lock acquisition, can be interleaved in the middle of my script's execution. The script does exactly what I described conceptually — GET, compare, conditionally DEL — but because it all happens server-side as one indivisible step, there's no window for a race.
>
> In production I don't send the raw script text on every call — I load it once with `SCRIPT LOAD`, cache the returned SHA1 hash on the client, and call `EVALSHA` afterward, which is cheaper on the wire and avoids re-parsing the script every time. The one thing I have to handle defensively is a `NOSCRIPT` error, which happens if Redis restarts or fails over to a replica that never saw the script — my client falls back to a full `EVAL` in that case, which both executes the script and re-populates the cache.
>
> The operational risk I'd flag with any Lua script on Redis is that it blocks the entire single-threaded server for its full execution time — so I'd never write a script that loops over an unbounded number of keys or does anything beyond a handful of simple operations. For this specific lock-release script, execution is sub-millisecond, which is exactly the profile you want: correctness gained through atomicity, with negligible impact on the rest of the system's throughput."

---

## PART 5 — DECISION FRAMEWORK

### Lua Scripting vs Alternative Ways to Achieve Atomicity in Redis

| Approach | How It Works | Consistency/Tradeoff | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **Lua script (EVAL/EVALSHA)** | Entire check-and-act sequence runs as one atomic unit server-side | Fully atomic for arbitrary custom logic | 0.3-1ms (single round trip) | Medium (must write/maintain Lua) | Long/unbounded scripts block the whole server; debugging Lua is harder than app code |
| **Native atomic commands (`SET NX`, `INCR`, `GETDEL`)** | Redis-provided single commands that are inherently atomic | Atomic, but only for the exact operation the command supports | 0.2-0.5ms | Low | Can't express custom conditional logic (e.g. "delete only if value matches") |
| **`MULTI`/`EXEC` transactions** | Queue several commands, execute as a batch | Atomic execution, but NO conditional branching mid-transaction (commands are queued blind) | 0.5-1.5ms (multiple commands) | Medium | Can't read a value and branch logic based on it within the same transaction — `WATCH` helps but still needs app-side retry loop |
| **`WATCH` + `MULTI`/`EXEC` (optimistic locking)** | Watch a key, queue commands, abort transaction if the watched key changed before EXEC | Atomic with conflict detection, requires app-level retry on abort | 1-3ms per attempt, more under contention | Medium-High | High contention causes many retries (`EXEC` returns nil repeatedly) |
| **Redis Functions (Redis 7+, replaces some Lua use cases)** | Server-side functions registered once, callable by name, similar atomicity guarantee as Lua | Same atomicity as Lua, better lifecycle/versioning management | Comparable to EVALSHA | Medium | Newer feature, less universal client/tooling support than plain EVAL |

### When Lua Scripting Is the Right Choice

```
Use Lua scripting when:
  ✓ You need to read a value AND conditionally act on it atomically
    (check-then-act: safe unlock, confirm-if-still-valid, etc.)
  ✓ You need multiple related Redis operations to appear as one atomic
    step to every other client (increment + conditional expire, etc.)
  ✓ You want to minimize round trips for a multi-step operation
    (one EVAL instead of GET + app logic + DEL = fewer network hops)
  ✓ The operation's logic is short, bounded, and fast (sub-millisecond)

Skip Lua scripting when:
  ✗ A single native command already does what you need atomically
    (don't write a script for something `SET NX EX` or `INCR` already covers)
  ✗ The logic requires looping over a large/unbounded number of keys
    (use SCAN + batched app-side operations instead — see production
    caveat in Part 3)
  ✗ The logic is genuinely complex/branchy business logic that belongs
    in your application layer, not embedded as opaque Lua in your data
    store (maintainability and testability suffer)
  ✗ You need `WATCH`-style "abort and retry" semantics rather than a
    single deterministic atomic step — that's a `MULTI`/`EXEC` + `WATCH`
    pattern, not a Lua script
```

---

## QUICK REFERENCE CARD

```
EVAL SYNTAX:
  EVAL "<script>" numkeys key1 [key2...] arg1 [arg2...]
  -- inside script: KEYS[1], KEYS[2]...   ARGV[1], ARGV[2]...

SCRIPT CACHING:
  SCRIPT LOAD "<script>"        -> returns SHA1 hash
  EVALSHA <sha1> numkeys ...    -> runs cached script (cheap, no re-send)
  SCRIPT EXISTS <sha1>          -> 1 if cached, 0 if not
  On NOSCRIPT error             -> fall back to full EVAL (also re-caches)

CANONICAL SAFE-UNLOCK PATTERN:
  if redis.call("GET", KEYS[1]) == ARGV[1] then
      return redis.call("DEL", KEYS[1])
  else
      return 0
  end

WHY IT'S SAFE: entire script = one atomic unit, no other command
(from any client) can interleave between the GET and the DEL.

PRODUCTION RULE: keep scripts sub-millisecond and bounded.
  Never loop over KEYS "*" pattern results inside a script.
  Never assume `lua-time-limit` will save you from a write-heavy
  runaway script — it mainly enables SCRIPT KILL for read-only ones.

RELATED PATTERNS:
  Safe distributed lock release  -> this script, exactly
  Atomic hold-confirm (booking)  -> see 099-two-phase-inventory-locking-soft-hold-ttl.md
  Redlock multi-node locking     -> see 022-redlock-distributed-lock.md
```

---
