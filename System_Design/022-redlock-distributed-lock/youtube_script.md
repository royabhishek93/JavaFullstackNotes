# Redlock — Distributed Locking with Redis — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 22 of 29

## HOOK (0:00–0:30)

[Screen cue: title card — "Redlock: Distributed Locking with Redis" with a graphic of 5 bank vaults]

Imagine 5 bank vaults sitting in a row. To open the shared safety deposit box, you don't need to unlock all 5 — you just need to physically lock at least **3 of them**. That's a majority.

You walk up, lock vault 1. Lock vault 2. Lock vault 3. Boom — 3 out of 5. The lock is yours, even if vaults 4 and 5 are on fire right now.

That's Redlock in one picture. And by the end of this video, you'll know exactly why locking just ONE vault — one single Redis node — is a production incident waiting to happen, and how the real algorithm behind Redlock fixes it with hard numbers, not vibes.

[Screen cue: "Episode 22 of 29 — System Design Deep Dives"]

## THE PROBLEM (0:30–2:00)

[Screen cue: code — `SET lock:payment "client_A" EX 30 NX`]

Let's start where most engineers start: a single Redis node, `SETNX` with a TTL. Client A acquires the lock, does its work, deletes the key. Looks fine in a demo. It is NOT fine in production, and there are two specific ways it breaks.

[Screen cue: timeline diagram — Problem 1: GC Pause]

**Problem 1 — the GC pause.** Walk through this timeline with me:

- `t=0`: Client A acquires the lock. TTL is 30 seconds.
- `t=5`: Client A starts processing the payment.
- `t=6`: A JVM garbage collection pause kicks in on Client A. The process is frozen — not crashed, just paused.
- `t=36`: 30 seconds have ticked by since acquisition. The lock's TTL expires. Redis doesn't know or care that Client A is "still working" — it just sees an expired key.
- Also at `t=36`: the lock is now free, so Client B acquires it and starts its own processing.
- `t=38`: Client A finally resumes from the GC pause. As far as Client A knows, it still holds the lock — it never got a notification that its TTL expired.

Now you have **both A and B inside the exclusive section at the same time.** That's the entire point of a lock — mutual exclusion — completely violated. Nobody wrote buggy code. The lock just... expired while nobody was looking.

[Screen cue: timeline diagram — Problem 2: Deleting someone else's lock]

**Problem 2 is worse — and it happens even without a pause, from naive cleanup code.**

- `t=0`: Client A acquires the lock.
- `t=31`: Client A's lock expires because A was just slow — one second past its own TTL.
- Also `t=31`: Client B acquires the now-free lock.
- `t=32`: Client A finally wakes up and, following the "clean up after yourself" pattern, runs `DEL lock:payment`. Except — that's not A's lock anymore. **Client A just deleted Client B's lock.**
- Still `t=32`: Client C swoops in and acquires the lock. Now you've got **two concurrent holders — B and C** — both thinking they're exclusive.

[Screen cue: Lua script code block]

The fix for Problem 2 is well known: never blindly `DEL`. Set the lock value to a **unique random token** per client, and release with an atomic Lua script:

```lua
if redis.call("GET", KEYS[1]) == ARGV[1] then
  return redis.call("DEL", KEYS[1])
else
  return 0
end
```

This only deletes the key if the value still matches *your* token — so you can only ever delete your own lock. That solves Problem 2. Notice it does **nothing** for Problem 1 — the GC pause is a fundamentally harder problem, and we'll come back to it in the deep dive.

## THE SOLUTION (2:00–5:00)

[Screen cue: diagram — 5 independent Redis nodes]

So the token fixes "deleting the wrong lock." But we still haven't fixed "what if the single Redis node just dies." That's what Redlock actually solves — not the GC pause, but node failure. Here's the exact algorithm, step by step, with the numbers from the spec.

Setup: **5 independent Redis instances** — not replicas of each other, genuinely independent nodes, ideally on different machines or even different failure domains. Goal: acquire `lock:cron_job` with a TTL of 10 seconds.

[Screen cue: numbered steps overlay]

**Step 1 — record the start time.** `t_start = current_time_ms()`. You need this to measure how much time the acquisition itself consumed.

**Step 2 — try to acquire on ALL 5 nodes in parallel.** For each node: `SET lock:cron_job <random_token> PX 10000 NX`. You use a short per-node timeout — around 50 milliseconds — so a dead or slow node doesn't stall your whole acquisition attempt.

**Step 3 — count the successes.** How many of the 5 nodes actually accepted your `SET`?

**Step 4 — this is the step everyone skips in interviews, and it's the important one: check majority AND check the remaining validity window.**

```
elapsed = current_time_ms() - t_start
clock_drift = max(2ms, elapsed * 0.01)     // 1% of elapsed, floor of 2ms
remaining_validity = 10000 - elapsed - clock_drift
```

You need **`acquired_count >= 3`** — that's the majority of 5 — **AND** `remaining_validity > 0`. If both hold: lock acquired, and critically, you only trust it for `remaining_validity` milliseconds, not the original 10 seconds you asked for. Why subtract clock drift? Because these are 5 independent machines with 5 independent clocks, and clocks drift relative to each other. You're pessimistically shaving off a safety margin.

If you don't get majority, or the validity window is already gone by the time you finish acquiring — **you fail safe.** Release whatever partial locks you did get (using the same Lua check-and-delete on each), wait a random backoff — 100 to 500 milliseconds — and retry.

[Screen cue: release step]

**Step 5 — release.** On all 5 nodes, run the same Lua script: if the value matches your token, delete it.

Why does this survive single-node failure? If vault 4 and vault 5 — sorry, Redis node 4 and 5 — are down, you still get SETs on nodes 1, 2, 3. That's 3 out of 5. Majority achieved. Lock valid. That's the entire value proposition of Redlock over single-node SETNX: no single Redis instance is a single point of failure anymore.

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

[Screen cue: "Redlock does NOT solve this" banner]

Here's the part that trips up even senior engineers in interviews: **Redlock, even with all 5 nodes healthy, does not solve Problem 1 — the GC pause.** Majority quorum protects you from Redis dying. It does nothing if YOUR process is the one that goes away temporarily.

[Screen cue: fencing token timeline, t=0 to t=14]

The real fix is a **fencing token**. Walk through this exact scenario:

- `t=0`: Client A acquires Redlock. Remaining validity comes out to 9800ms.
- `t=1`: Client A writes to storage with `token=33`. Storage accepts it: `last_seen_token=33`.
- `t=2`: Client A pauses for 12 seconds — a GC pause, or a VM got preempted, doesn't matter which.
- `t=10`: The lock's validity window has expired. Client B acquires Redlock and is issued `token=34`.
- Still `t=10`: Client B writes to storage with `token=34`. Storage accepts: `last_seen_token=34`.
- `t=14`: Client A finally wakes up from its pause, completely unaware time has passed, and tries to write with its old `token=33`.

**Storage looks at 33, compares it to the last seen token of 34, and REJECTS the write.** 33 is less than 34 — this is a stale write from a client that no longer effectively holds the lock. Safe.

[Screen cue: text overlay — "fencing token = monotonic integer, checked at the storage layer, not the lock layer"]

The critical insight: **the fencing token isn't checked by the lock service — it's checked by whatever you're writing to.** Your database, your storage layer, needs an explicit `if incoming_token < last_seen_token: reject` check. This is a contract between the lock and the storage, and you have to build it yourself in most cases.

Who gives you this token for free? **ZooKeeper** — its `zxid`, the transaction ID, is monotonically increasing by design, so you just use that. **etcd** — the lease revision number does the same job. **Redlock — does NOT provide this natively.** If you want fencing with Redlock, you're bolting it on yourself, typically with a Redis `INCR` before you even attempt the lock.

[Screen cue: comparison table]

Let's put this side by side, because this table is exactly the kind of thing that shows up in a staff-level system design interview:

| Scenario | SETNX (single) | Redlock (5 node) | ZooKeeper |
|---|---|---|---|
| Single Redis crash | Lock lost or stuck | 2 of 4 remain — OK | Leader re-elected |
| Two Redis crash | N/A, single node | 2 of 5 remain — lock FAILS SAFE | Quorum lost if more than half down |
| GC pause > TTL | Dual holders | Dual holders — same problem | Dual holders — same problem |
| GC pause + fencing token | No protection | No protection | PROTECTED via zxid ordering |
| Network partition | Split brain | Minority side simply can't acquire | No split brain — quorum write |

Notice the "GC pause" row is identical across all three until you add fencing. That's the whole point of this section: **the lock mechanism and the fencing mechanism are two separate concerns**, and Redlock alone only solves one of them.

[Screen cue: heartbeat code snippet]

One more pattern engineers get wrong: TTL sizing for long jobs. If your job might run longer than the TTL, don't just pick a bigger TTL and hope — use a **heartbeat**. Spin up a background thread that extends the TTL at roughly **one-third of the original interval**. So for a 30-second TTL, you re-extend every 10 seconds:

```java
heartbeat.scheduleAtFixedRate(() -> {
    if (token.equals(redis.get(lockKey))) {
        redis.pexpire(lockKey, ttlMs);
    }
}, 10, 10, TimeUnit.SECONDS);
```

Notice it checks the token still matches before extending — same discipline as the release script. This way, a job that legitimately runs for 5 minutes keeps its lock alive the whole time, but a job that silently died stops heartbeating and its lock naturally expires for someone else to pick up.

## REAL WORLD (8:00–9:30)

[Screen cue: 5 real-world system cards]

Let's ground this in systems you've actually built or used.

**Payment processing** — think PhonePe or Paytm handling a UPI transaction. If everything lives in one database, you don't need Redlock at all — a `pg_advisory_xact_lock(payment_id)` held for the transaction's duration is simpler and stronger. It auto-releases on commit or rollback, no TTL guesswork required. You only reach for Redlock here if payments are sharded across services with no shared database.

**Ticket booking during a flash sale** — this is the textbook BookMyShow scenario. Big movie release, thousands of users hitting "book seat" on the same show at the same second. You key the lock as `lock:event:{eventId}:seat:{seatId}` with a **TTL of 10 minutes** — that's your checkout hold window. One instance gets the lock and proceeds to payment; every other instance immediately gets a lock failure and shows "seat unavailable." If the user abandons checkout, the TTL naturally releases the seat back into inventory after 10 minutes.

**Job scheduling** — if you've got 10 replicated pods all running the same cron trigger, you don't want the same job firing 10 times. **ShedLock** with `@SchedulerLock` is the production-grade Spring answer here — it can sit on top of your existing PostgreSQL, no new infrastructure needed. `lockAtMostFor` gives you a safety TTL, `lockAtLeastFor` prevents rapid re-fire on clock skew.

**Flash sale inventory** — a Zerodha-style order-matching engine or an e-commerce flash sale both care about the same thing: don't oversell. `lock:inventory:{productId}` with a **TTL of just 5 seconds** — deliberately tight, because you want failed attempts to retry aggressively rather than queue up behind a slow holder. A Lua script checks stock count before decrementing, all inside the lock.

**Stock broker order matching** — for something like Zerodha's matching engine, if the whole exchange runs against a single database per market, a PostgreSQL advisory lock on `instrument_id` is actually the *stronger* choice — no distributed coordination needed at all, because you never left one database.

The pattern across all five: **the right lock depends on whether you're actually distributed, not just whether Redis is in your stack already.**

## OUTRO + NEXT EPISODE (9:30–10:00)

[Screen cue: recap bullets on screen]

So — Redlock: majority quorum across 5 independent Redis nodes protects you from node failure. Fencing tokens protect you from your own process pausing too long. Those are two different problems, and conflating them is the single biggest mistake I see in interviews on this topic.

[Screen cue: next episode teaser card — "Episode 23: Push vs Pull Notifications — APNs & FCM"]

Next episode, we're leaving locks behind and going into how your phone actually gets that notification the instant something happens — push versus pull, and the real mechanics of APNs and FCM. See you there.
