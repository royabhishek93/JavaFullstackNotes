# Two-Phase Inventory Locking: Soft-Hold + TTL Pattern
### How BookMyShow stops two people from buying the same seat without locking the database for five minutes

---

## PART 1 — THE STUDENT CONVERSATION

Imagine a movie theater box office with exactly one paper seating chart pinned to the wall. Two customers walk up at the same instant, both pointing at seat F12. If the clerk has to physically write each customer's name on the chart, cross it out, and file paperwork before the next customer can even look at the chart — the line backs up for an hour. That's what happens if you use a full database transaction lock for the *entire* time a user is browsing seats, entering payment details, and waiting for their card to authorize. A user can sit on a checkout page for 3-4 minutes; if you hold a row-level DB lock for that whole time, you've turned your booking system into a single-file queue.

So real systems split the problem into two phases, and they use a completely different, much cheaper tool for the first phase: a sticky note with a self-destruct timer.

**Phase 1 — "let me hold this while you think."** When a user clicks seat F12, the system doesn't touch the database at all. It writes a sticky note in a shared whiteboard (Redis) that says "F12 — held by Alice — will vanish in 10 minutes automatically." Because the whiteboard has a rule that only ONE person can pin the *first* sticky note to any given spot (this is the `NX` — "only if not already set" — guarantee), if Bob tries to hold F12 half a second later, the whiteboard rejects him. He sees "already held" instantly, no waiting, no database transaction, no lock contention.

**Phase 2 — "I actually paid, make it permanent."** Once Alice's payment succeeds, the system does the expensive, durable thing exactly once: it opens a real database transaction, inserts the permanent "F12 sold to Alice" row, and only *then* removes the sticky note. This is the only moment a real DB lock is taken, and it's held for milliseconds, not minutes.

**The best part — abandonment costs nothing.** If Alice closes the tab and walks away, nobody has to notice or clean anything up. The sticky note has a self-destruct timer (`EX 600` — expire in 600 seconds). Redis deletes it automatically. Ten minutes later, F12 is available again, with zero manual intervention, zero cron jobs, zero "stuck lock" support tickets.

The one tricky bit students always miss: what if Alice's payment gateway callback comes back *right as* her 10-minute timer expires? What if, in between, the seat has already been re-offered to Bob? You cannot just blindly write "CONFIRMED" to the database — you must first re-check, atomically, "is this hold still mine?" That atomic check-and-commit is why this pattern always pairs with a tiny Lua script (see [100-redis-lua-scripting-atomicity.md](100-redis-lua-scripting-atomicity.md)) rather than a naive GET-then-SET from application code.

---

## PART 2 — THE TWO-PHASE LOCKING ARCHITECTURE DIAGRAMS

### Happy Path: Hold → Confirm

```
User Alice                    Redis (soft-hold layer)              PostgreSQL (source of truth)
───────────                    ──────────────────────              ─────────────────────────────

GET /seats/F12                 seat:F12 → (no key exists)
  → shows "AVAILABLE"

POST /seats/F12/hold
  {userId: "alice-99"}
                                SET seat:F12 "alice-99:tok_8f3a"
                                    NX EX 600
                                → OK (key created)
                                → seat:F12 = "alice-99:tok_8f3a"
                                   TTL = 600s (10 min)
  ← 200 { holdToken: "tok_8f3a",
          expiresInSec: 600 }

  [Alice fills payment form —
   90 seconds pass, no DB
   lock held anywhere]

POST /seats/F12/confirm
  {holdToken: "tok_8f3a",
   paymentRef: "pay_5521"}

                                EVAL confirm_script 1
                                  seat:F12 "alice-99:tok_8f3a"
                                → Lua checks: does
                                  seat:F12 == "alice-99:tok_8f3a"?
                                → YES → proceed
                                                                    BEGIN;
                                                                    INSERT INTO bookings
                                                                      (seat_id, user_id,
                                                                       payment_ref, booked_at)
                                                                    VALUES
                                                                      ('F12','alice-99',
                                                                       'pay_5521', now());
                                                                    COMMIT;
                                → DEL seat:F12
                                  (release the soft hold,
                                   permanent row now exists)
  ← 200 { status: "CONFIRMED",
          bookingId: "bk_77213" }

Total Redis lock duration: ~90 seconds (browsing + payment entry)
Total DB row lock duration: <5 milliseconds (single INSERT + COMMIT)
```

### Edge Case: Two Users Race for the Same Seat

```
Alice                    Redis                              Bob
─────                    ─────                              ───

POST /hold F12
  SET seat:F12 "alice:tok_a" NX EX 600  ──┐
                                          │  Redis processes commands
                                          │  strictly one at a time
                                          │  (single-threaded event loop)
                                                                     POST /hold F12
                                                                       SET seat:F12 "bob:tok_b" NX EX 600
                                          └──> Alice's SET arrives first
                                               key doesn't exist yet → SET succeeds
                                               returns OK
  ← 200 "held, expires in 600s"

                                               Bob's SET arrives 3ms later
                                               key ALREADY exists (NX fails)
                                               returns (nil)
                                                                     ← 409 "seat already held,
                                                                            try another seat"

RESULT: Exactly one of two simultaneous holds wins. No double-booking,
        no distributed lock manager needed — NX is atomic by definition
        of Redis's single-threaded command processing.
```

### Edge Case: Confirm Arrives Right as TTL Expires (The Dangerous Race)

```
Timeline (seat:F12 held by alice:tok_a, TTL=600s, set at T+0)

T+598s   Alice's payment gateway finally responds (slow 3D-Secure step)
         → App server about to call /confirm

T+600s   Redis TTL fires → seat:F12 key is DELETED automatically
         → seat is now "AVAILABLE" again from Redis's point of view

T+600.4s Another user, Carol, immediately holds the now-free seat:
         SET seat:F12 "carol:tok_c" NX EX 600 → succeeds
         seat:F12 = "carol:tok_c"

T+601s   Alice's /confirm request finally arrives at the server
         (network delay from the slow payment gateway)

  WITHOUT atomic check-and-confirm (WRONG, naive code):
    app does: value = GET seat:F12        → "carol:tok_c"  (app ignores mismatch!)
    app does: DEL seat:F12                → deletes Carol's legitimate hold
    app does: INSERT INTO bookings (...)  → Alice gets F12 in the DB
    RESULT: Carol's hold is silently destroyed, AND if Carol had already
            confirmed a millisecond earlier, you now have TWO bookings
            for the same seat — the exact bug this whole pattern exists
            to prevent.

  WITH atomic Lua check-and-confirm (CORRECT):
    EVAL confirm_script 1 seat:F12 "alice:tok_a"
      -- Lua: if redis.call('GET', KEYS[1]) == ARGV[1] then
      --        redis.call('DEL', KEYS[1]); return 1
      --      else return 0 end
    → GET seat:F12 returns "carol:tok_c", NOT "alice:tok_a"
    → mismatch → script returns 0, does NOT delete Carol's key
    ← app receives 0 → responds to Alice:
        409 "Your hold expired before payment completed.
             Please re-select a seat. Your card was NOT charged
             (or: refund the pre-auth automatically)."
    RESULT: Carol's hold is untouched. Alice is safely rejected and
            told to retry. No double-booking, no silent data loss.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Phase 1: Acquiring the Soft Hold

```bash
# The single command that does the entire "phase 1" atomically.
# NX = only set if key does not already exist (mutual exclusion)
# EX 600 = auto-expire in 600 seconds (10-minute checkout window)
SET seat:F12 "alice-99:tok_8f3a" NX EX 600

# Success: (integer) OK   -> hold acquired, TTL started
# Failure: (nil)          -> someone else already holds it

# Token format "userId:randomToken" matters: the random token (tok_8f3a,
# generated with e.g. UUID.randomUUID()) prevents a second request from
# the SAME user id (two browser tabs, a retried request) from being
# mistaken for a legitimate re-confirmation of a DIFFERENT hold attempt.
```

```java
@Service
public class SeatHoldService {

    private final StringRedisTemplate redis;
    private static final Duration HOLD_TTL = Duration.ofSeconds(600);

    public HoldResult tryHold(String seatId, String userId) {
        String token = UUID.randomUUID().toString();
        String value = userId + ":" + token;

        // setIfAbsent == Redis SET ... NX ; withExpiration == EX
        Boolean acquired = redis.opsForValue()
                .setIfAbsent("seat:" + seatId, value, HOLD_TTL);

        if (Boolean.TRUE.equals(acquired)) {
            return HoldResult.held(token, HOLD_TTL.getSeconds());
        }
        return HoldResult.alreadyHeld();
    }
}
```

### Phase 2: Atomic Check-and-Confirm via Lua

```lua
-- confirm_hold.lua
-- KEYS[1] = seat:F12
-- ARGV[1] = expected value, e.g. "alice-99:tok_8f3a"
--
-- Runs as ONE atomic step on the Redis server: no other client's
-- command (including a competing hold or expiry) can interleave
-- between the GET and the DEL.
local current = redis.call('GET', KEYS[1])
if current == ARGV[1] then
    redis.call('DEL', KEYS[1])
    return 1   -- confirmed: caller may now proceed to DB INSERT
else
    return 0   -- hold expired or stolen by someone else: reject
end
```

```java
@Service
public class SeatConfirmService {

    private final StringRedisTemplate redis;
    private final RedisScript<Long> confirmScript =
            RedisScript.of(new ClassPathResource("confirm_hold.lua"), Long.class);

    @Transactional
    public BookingResult confirm(String seatId, String userId, String token,
                                  String paymentRef, BookingRepository repo) {
        String expectedValue = userId + ":" + token;

        Long result = redis.execute(confirmScript,
                List.of("seat:" + seatId),
                expectedValue);

        if (result == null || result == 0L) {
            // Hold expired, was never valid, or already consumed —
            // reject BEFORE touching the database.
            throw new HoldExpiredException(seatId);
        }

        // Only reached if the Lua script atomically confirmed ownership.
        // This is the ONLY place a real (short-lived) DB transaction happens.
        Booking booking = new Booking(seatId, userId, paymentRef, Instant.now());
        repo.save(booking);   // single-row INSERT, commits in ~2-5ms
        return BookingResult.confirmed(booking.getId());
    }
}
```

### Why Not Just Use a DB Row Lock for the Whole Flow

```sql
-- The naive "pessimistic lock for the whole checkout" approach:
BEGIN;
SELECT * FROM seats WHERE id = 'F12' FOR UPDATE;   -- row locked HERE
-- ... user is now shown a payment form ...
-- ... user takes 30-180 seconds to enter card details ...
-- ... waiting on 3rd-party payment gateway callback ...
UPDATE seats SET status = 'SOLD' WHERE id = 'F12';
COMMIT;                                             -- row unlocked HERE

-- PROBLEM: `FOR UPDATE` holds the row lock for the ENTIRE transaction,
-- which in this design spans the whole user checkout — potentially
-- minutes. Every other query touching that row (even a read-committed
-- SELECT FOR UPDATE from another checkout attempt) blocks until this
-- transaction commits or the connection times out.
--
-- Real numbers: a single Postgres connection holding a FOR UPDATE lock
-- for 3 minutes on a flash-sale item ties up:
--   - 1 DB connection from your pool (pools are typically 20-100 conns)
--   - Every concurrent buyer for that same seat, queued serially
--   - At 500 concurrent checkouts on one hot row: instant connection
--     pool exhaustion, cascading timeouts across the whole service.

-- The two-phase pattern instead holds the DB lock for ~2-5ms (a single
-- INSERT), because 599.995 of the 600 "locked" seconds are represented
-- by a Redis key, which costs ~1 Redis connection-slot and a few dozen
-- bytes of memory — Redis handles 100K+ such keys per node trivially.
```

### Real Numbers

```
Redis SET NX EX latency:            0.3 - 1ms   (single command, in-memory)
Lua EVAL confirm script latency:    0.4 - 1.5ms (script + GET + DEL, one round trip)
DB INSERT + COMMIT (Phase 2 only):  2 - 8ms      (single row, indexed PK)

Hold TTL choice (typical, industry-observed):
  Flash sale / high-demand event tickets:   3 - 5 minutes  (force fast decisions)
  Standard e-commerce cart reservation:     10 - 15 minutes
  Hotel room hold during multi-step booking: 15 - 20 minutes

Memory cost per active hold: ~80-120 bytes (key + value + TTL metadata)
  → 1 million concurrent holds ≈ 100MB Redis memory — trivial for one node.

Failure mode to monitor: hold "churn rate" — holds created vs holds confirmed.
  A healthy flash-sale funnel: ~30-50% of holds convert to confirmed bookings.
  If confirm rate drops below ~10%, investigate: bot scalping (mass-holding
  inventory with no intent to buy) is a common real-world attack on this
  exact pattern — mitigate with per-user hold-rate limiting.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Design the seat-locking mechanism for a ticket-booking platform like BookMyShow. Two users must never be able to book the same seat, but you also can't make users complete payment in under a second."

**You (architect answer):**

> "I'd split this into two distinct phases with two different consistency tools, because they have completely different time and durability requirements.
>
> Phase one is the 'soft hold' — the moment a user selects a seat, I do a single Redis command: `SET seat:{id} {userId}:{token} NX EX 600`. The `NX` flag makes this atomic mutual exclusion — Redis processes commands one at a time on a single thread, so if two users click the same seat within milliseconds of each other, exactly one `SET` succeeds and the other gets `nil` back instantly. No database transaction, no row lock, no contention — this scales to tens of thousands of concurrent 'browsing' users on commodity Redis hardware. The `EX 600` gives the user a 10-minute checkout window, and critically, if they abandon the flow — closes the tab, gets distracted — the key self-destructs. I don't need a cleanup job or a 'release expired holds' cron; Redis's TTL mechanism does it for free.
>
> Phase two is the actual commit, which only happens once, when the payment gateway confirms success. At that point I open a real, short-lived database transaction and insert the permanent booking row — this transaction is held for single-digit milliseconds, not minutes, because it's the only place I need real ACID durability.
>
> The subtle part interviewers usually probe on is what happens if the payment confirmation arrives at almost exactly the moment the 10-minute TTL expires. If I naively do `GET` then `DEL` from application code, there's a window where another user could grab the now-expired seat between my `GET` and my `DEL` — I'd delete their legitimate hold, or worse, double-confirm the same seat. So the confirm step has to be a single atomic Lua script: check the current Redis value still matches this user's hold token, and only if it matches, delete it and return success — all as one indivisible operation on the Redis server. If it doesn't match, I reject the confirmation and tell the user their hold expired, rather than silently corrupting someone else's hold.
>
> Operationally, the thing I'd actively monitor in production is hold-to-confirm conversion rate per SKU. On a flash sale, if I see a huge spike in holds with almost none converting, that's usually bot scalping — mass-holding inventory to create artificial scarcity or resell later. I'd mitigate that with a per-user/per-IP rate limit on hold creation, separate from the locking mechanism itself."

---

## PART 5 — DECISION FRAMEWORK

### Two-Phase Soft-Hold vs Alternative Inventory-Locking Approaches

| Approach | How It Works | Consistency/Tradeoff | Latency (hold step) | Complexity | When It Fails |
|---|---|---|---|---|---|
| **Two-phase soft-hold + TTL (Redis)** | `SET NX EX` for temporary claim, DB TX only on confirm | Strong during hold window; DB is final source of truth | 0.3-1ms | Medium | Redis outage during hold window loses in-flight holds (mitigate: short TTL, DB is unaffected) |
| **Pessimistic DB row lock (`SELECT FOR UPDATE`) for whole checkout** | DB row locked from selection until payment completes | Strongly consistent, but lock held for minutes | 2-8ms to acquire, held for full flow | Low | Connection pool exhaustion under concurrent hot-item demand |
| **Optimistic locking (version column)** | Read seat + version, `UPDATE ... WHERE version = X`; retry on conflict | Consistent, but user sees "conflict, retry" late (at confirm time, not selection time) | ~5ms per attempt | Low-Medium | Poor UX in high-contention flash sales — many users only find out they lost the seat after filling out payment |
| **Distributed lock manager (e.g. Redlock across N Redis nodes)** | Quorum-based lock across multiple independent Redis instances | Stronger guarantee against single-node Redis failure | 2-5ms (multiple round trips) | High | Overkill for this use case — soft-hold doesn't need cross-node consensus since DB is the final arbiter anyway (see [022-redlock-distributed-lock.md](022-redlock-distributed-lock.md)) |
| **Queue-based sequential processing (per-seat queue/actor)** | All hold/confirm requests for a seat processed strictly in order by one worker | Perfectly consistent, no races possible by construction | Depends on queue depth, can add 10s-100s ms under load | High | Hot-seat contention creates a queue bottleneck; harder to scale horizontally per item |

### When Two-Phase Soft-Hold + TTL Is the Right Choice

```
Use this pattern when:
  ✓ Users need a multi-step, multi-minute flow between "select" and "pay"
    (seat selection, payment form entry, 3rd-party gateway round trip)
  ✓ Abandonment is common and must self-heal with zero manual cleanup
  ✓ You want selection-time rejection (fast "already taken" feedback),
    not confirm-time rejection (bad UX — user fills out payment then fails)
  ✓ Peak concurrency on hot items (flash sales, popular screenings) would
    exhaust DB connections if held for the whole flow
  ✓ The final commit is a single, fast, well-defined DB write

Skip this pattern when:
  ✗ The "select → confirm" flow is a single synchronous call anyway
    (e.g., "buy now" with stored payment method, no separate hold step)
  ✗ You don't have Redis (or equivalent) in your stack and can't justify
    adding it for one feature — optimistic locking may be simpler
  ✗ Inventory count matters more than a specific identity (e.g., "100 of
    SKU-X in stock" rather than "seat F12 specifically") — that's a
    counter-decrement problem, not a soft-hold-by-key problem
  ✗ You need cross-datacenter strong consistency guarantees on the hold
    itself — a single-node Redis TTL hold is a UX optimization, not a
    replacement for the DB being the ultimate source of truth
```

---

## QUICK REFERENCE CARD

```
PHASE 1 — ACQUIRE SOFT HOLD (atomic, single command):
  SET seat:{id} {userId}:{token} NX EX {ttlSeconds}
  -> OK   = hold acquired
  -> nil  = already held by someone else

PHASE 2 — ATOMIC CHECK-AND-CONFIRM (Lua, single round trip):
  if redis.call('GET', KEYS[1]) == ARGV[1] then
      redis.call('DEL', KEYS[1]); return 1
  else
      return 0
  end
  -> 1 = confirmed, proceed to DB INSERT inside a TX
  -> 0 = hold expired/stolen, reject and ask user to retry

ABANDONMENT: no code needed — Redis TTL expiry auto-releases the seat.

TYPICAL TTL VALUES:
  Flash sale:            3-5 min
  Standard e-commerce:    10-15 min
  Multi-step hotel flow:  15-20 min

STATE DIAGRAM:
  AVAILABLE --hold(NX EX)--> HELD(TTL running) --confirm(Lua match)--> CONFIRMED
  HELD --TTL expires--> AVAILABLE
  HELD --user cancels--> AVAILABLE (explicit DEL)

MONITOR: hold-to-confirm conversion rate (low rate = bot scalping signal)
```

---
