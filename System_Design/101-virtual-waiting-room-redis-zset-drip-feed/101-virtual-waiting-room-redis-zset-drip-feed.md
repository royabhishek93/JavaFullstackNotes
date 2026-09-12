# Virtual Waiting Room: Redis Sorted Set Drip-Feed Admission
### How BookMyShow lets 500K people queue for a blockbuster without letting 500K people hit the booking page at once

---

## PART 1 — THE STUDENT CONVERSATION

Imagine a blockbuster movie drops tickets at 10:00 AM sharp. 500,000 people refresh the page at the exact same second. If your backend lets all 500,000 requests straight through to the "select seat" API, your database connection pool (maybe sized for 500 concurrent connections) is annihilated in milliseconds. Seat-locking queries pile up, connections time out, and even the 200 people who *could* have booked successfully now get 500 errors too. Everyone loses.

The instinct is to rate-limit: reject requests over some threshold. But that's unfair and wasteful — the 499,700th person to click isn't a malicious attacker, they're a genuine customer who deserves a ticket eventually, just not *this millisecond*. Rejecting them outright means they have to keep refreshing and retrying, hammering you even harder.

The better idea, borrowed from real-world queueing (think Disneyland's virtual FastPass, or the literal line outside a concert box office): give everyone a numbered ticket the instant they arrive, and process people in the order they arrived, at a rate your system can actually sustain. Nobody is rejected. Everybody is queued fairly, FIFO, and let in in small controlled batches.

Technically: the moment a user hits "join queue," you don't let them anywhere near the booking flow. You just record their arrival time and give them a position. A Redis Sorted Set (ZSET) is perfect for this — the "score" is the arrival timestamp (or a monotonic sequence number), and the "member" is the user's session/queue-token ID. `ZADD` is O(log N), so adding 500K people to the set in a burst is trivial for Redis, even though it would flatten a relational database.

A background worker — the "usher" — periodically looks at the front of the line (`ZRANGE waiting_room 0 N-1`, the N lowest scores = N earliest arrivals), admits exactly N of them into the real booking flow (issues them a short-lived "admitted" token), and removes them from the ZSET (`ZREM`). This keeps the number of people *actually inside* the booking flow — where DB writes and seat locks happen — bounded to whatever your backend can safely handle, say 2,000 concurrent active bookers. Everyone else keeps polling their position with `ZRANK`, watching the number tick down, like watching your position in a phone hold queue.

The key mental shift from rate limiting: rate limiting says "no" to excess traffic. A waiting room says "yes, eventually, in order" to *everyone*, while capping how many are simultaneously active inside the expensive part of the system.

---

## PART 2 — THE WAITING ROOM ARCHITECTURE DIAGRAMS

### Happy Path: Join → Wait → Admit → Book

```
User Browser                Edge / Queue Service              Redis                      Booking Service
─────────────                ─────────────────────            ─────                      ────────────────

GET /join-queue                                                                                                                     :10:00:00.000
  movie_id=avengers5   ───►  Generate queueId = uuid()
                              (session-bound, HttpOnly cookie)
                                                          ───►  ZADD waiting_room
                                                                  1735689600.001  "q-8f3a"
                                                                (score = arrival epoch ms,
                                                                 sub-ms jitter breaks ties)
                             ◄─── 200 OK {queueId:"q-8f3a"}

Client polls every 3s:
GET /queue-position?
    queueId=q-8f3a       ───► ZRANK waiting_room "q-8f3a"  ───►  returns 428,391
                             ◄─── {"position": 428391,
                                    "estWaitSec": 1285}
                                    (estimate = position / admitRate)

... background worker on its own 2s tick ...

                                                          Admission Worker (cron-like loop, every 2s)
                                                          ────────────────────────────────────────────
                                                          1. ZRANGE waiting_room 0 1999 WITHSCORES
                                                             (pop lowest 2000 scores = oldest arrivals)
                                                          2. For each: ZREM waiting_room <member>
                                                          3. SETEX admitted:q-8f3a 300 "1"
                                                             (5-min admitted-slot TTL)
                                                          4. Push to "admitted" pub/sub channel
                                                             or client polls and sees state flip

Client's next poll sees:
GET /queue-position?
    queueId=q-8f3a       ───► GET admitted:q-8f3a         ───► "1"
                             ◄─── {"status":"ADMITTED",
                                    "admittedToken":"...",
                                    "expiresInSec": 300}

Client redirects to
/select-seat?token=...                                                              ───►  Seat-lock flow begins
                                                                                            (bounded to ~2000
                                                                                             concurrent bookers —
                                                                                             DB pool never overloaded)
```

### Edge Case: Abandoned Admitted Slot (User Doesn't Act)

```
Problem: User "q-8f3a" gets admitted at 10:00:05, opens the tab, then
walks away to make coffee. Their "admitted" slot (one of the precious
2000 concurrent booking slots) sits idle for the full 5-minute TTL,
while 428,390 people behind them are still waiting.

Timeline:
  10:00:05  Admission worker admits q-8f3a. SETEX admitted:q-8f3a 300 "1"
            Concurrency counter: INCR active_bookers  → 2000/2000 (FULL)
  10:00:05  Admission worker pauses next batch:
              if (active_bookers >= MAX_CONCURRENT) skip this tick
  10:02:00  q-8f3a still hasn't hit /select-seat. Slot is "wasted" —
            but nobody behind them can get in because active_bookers
            reads 2000/2000.

Fix: Reclaim on TTL expiry using Redis keyspace notifications:

  redis-cli> CONFIG SET notify-keyspace-events Ex
  (Ex = expired-key events)

  Subscriber process:
    PSUBSCRIBE __keyevent@0__:expired
    → message: "admitted:q-8f3a" expired
    → handler: DECR active_bookers
               (slot freed, next admission-worker tick can fill it)

  10:05:05  admitted:q-8f3a TTL expires (5 min elapsed, no booking
            completed). Keyspace notification fires.
            DECR active_bookers → 1999/2000
  10:05:07  Next worker tick: ZRANGE waiting_room 0 0 → admits
            the next oldest person in line.

Alternative without keyspace notifications (simpler, cheaper at scale):
  Admission worker recomputes active_bookers directly instead of
  a counter, each tick:
    active_bookers = SCARD active_booking_set
  where booking_service does:
    SADD active_booking_set q-8f3a   (on admit)
    SREM active_booking_set q-8f3a   (on booking complete OR on
                                       explicit expiry sweep job)
  A separate sweep job runs every 30s:
    for member in SMEMBERS active_booking_set:
      if NOT EXISTS admitted:{member}: SREM active_booking_set {member}
  Slightly higher latency to reclaim (~30s) but avoids relying on
  keyspace notification delivery guarantees (they are NOT persisted
  or replicated reliably across Redis failover).
```

### Waiting Room vs Plain Rate Limiting (Behavioral Contrast)

```
RATE LIMITING (token bucket, e.g. 500 req/sec allowed):
  500,000 requests arrive in 1 second
  ─► 500 pass through immediately
  ─► 499,500 get HTTP 429 "Too Many Requests"
  ─► Client must retry (often immediately, worsening the storm)
  ─► No memory of who already tried — 429'd users compete equally
     with brand-new arrivals on the next second's retry. UNFAIR.
  ─► No guarantee the same person ever gets in.

WAITING ROOM (ZSET drip-feed, admit 2000 every 2s = 1000/sec):
  500,000 requests arrive in 1 second
  ─► ALL 500,000 succeed at ZADD (O(log N), Redis handles this easily)
  ─► Each gets a durable, ordered position — no retry storm
  ─► Worker drains 1000/sec into the booking flow, FIFO
  ─► Total drain time: 500,000 / 1000 per sec ≈ 500 seconds (~8.3 min)
  ─► Every single person WILL get a turn, in arrival order.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Redis Commands: Join, Rank, Admit

```bash
# 1. User joins the queue (score = arrival time in epoch millis,
#    with a random fractional jitter to avoid exact-tie collisions
#    when many requests land in the same millisecond)
ZADD waiting_room:avengers5 1735689600123.0473 "q-8f3a"

# 2. Client polls their position (0-indexed rank by ascending score)
ZRANK waiting_room:avengers5 "q-8f3a"
# -> (integer) 428391

# 3. Total queue size, for "X people ahead of you" UX
ZCARD waiting_room:avengers5
# -> (integer) 500000

# 4. Admission worker: atomically pop the 2000 oldest members
#    Must be atomic (read + remove) so two worker instances never
#    double-admit — wrap in a Lua script for atomicity:
EVAL "
  local batch = redis.call('ZRANGE', KEYS[1], 0, ARGV[1] - 1)
  if #batch > 0 then
    redis.call('ZREM', KEYS[1], unpack(batch))
  end
  return batch
" 1 waiting_room:avengers5 2000
# -> returns array of the 2000 queueIds just admitted & removed

# 5. Mark each admitted queueId with a short-lived token
SETEX admitted:q-8f3a 300 "1"
```

### Admission Worker (Java / Spring Scheduled Task)

```java
@Component
public class WaitingRoomAdmissionWorker {

    private static final int BATCH_SIZE = 2000;
    private static final int MAX_CONCURRENT_BOOKERS = 2000;
    private static final int ADMITTED_TTL_SECONDS = 300;

    @Autowired
    private StringRedisTemplate redis;

    private final DefaultRedisScript<List> popOldestScript = new DefaultRedisScript<>(
        "local batch = redis.call('ZRANGE', KEYS[1], 0, ARGV[1] - 1) " +
        "if #batch > 0 then redis.call('ZREM', KEYS[1], unpack(batch)) end " +
        "return batch", List.class);

    @Scheduled(fixedRate = 2000) // every 2 seconds
    public void drip(String eventId) {
        String activeSetKey = "active_bookers:" + eventId;
        Long activeCount = redis.opsForSet().size(activeSetKey);
        long headroom = MAX_CONCURRENT_BOOKERS - (activeCount == null ? 0 : activeCount);
        if (headroom <= 0) return; // booking flow is at capacity, skip this tick

        List<String> admitted = redis.execute(popOldestScript,
            List.of("waiting_room:" + eventId),
            String.valueOf(Math.min(headroom, BATCH_SIZE)));

        for (String queueId : admitted) {
            redis.opsForValue().set("admitted:" + queueId, "1",
                Duration.ofSeconds(ADMITTED_TTL_SECONDS));
            redis.opsForSet().add(activeSetKey, queueId);
        }
    }

    // Called by booking-service when the user actually completes checkout
    // OR by a 30s sweep job that removes expired "admitted:*" keys.
    public void releaseSlot(String eventId, String queueId) {
        redis.opsForSet().remove("active_bookers:" + eventId, queueId);
    }
}
```

### Real Numbers

```
Scenario: Avengers 5 ticket drop, single show, 500K queue-joins in 60s

ZADD throughput:        Redis single instance handles ~100K-200K ops/sec
                         for simple ZADD → 500K joins absorbed in 2.5-5s,
                         no problem even under a genuine thundering herd.

ZSET memory footprint:  Each member ≈ (queueId string ~10 bytes) +
                         (score 8 bytes double) + skip-list overhead
                         (~80 bytes/entry typical). 500K entries ≈ 45 MB.
                         Trivial for a Redis instance with a few GB RAM.

Admission rate:          Booking-service DB pool sized for 2000 concurrent
                         writers (HikariCP maximumPoolSize=2000 split across
                         app instances). Draining at 2000 every 2s = 1000/sec
                         empties a 500K queue in ~500s (~8.3 minutes).

ZRANK poll cost:         O(log N) per call. At 500K polling clients checking
                         every 3s, that's ~167K ZRANK calls/sec at peak —
                         still comfortably within a single Redis node's
                         capacity (bench: >1M simple ops/sec on typical
                         cloud Redis, e.g. cache.r6g.xlarge).

Client poll backoff:     Increase poll interval as estimated wait grows
                         (poll every 2s if <60s wait, every 15s if >10min
                         wait) to reduce needless load — this is the
                         single biggest lever to cut Redis read QPS.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "We're launching ticket sales for a huge concert and expect 500,000 people to hit 'Buy' within the first 10 seconds. Our booking backend can only safely handle about 2,000 concurrent users doing seat-selection and payment. How do you design this so the system doesn't fall over, and it's fair to users?"

**You (architect answer):**

> "The core insight is that rate limiting and a waiting room solve different problems. Rate limiting rejects excess traffic — that's unfair here, because a request that arrives at second 3 is just as legitimate as one at second 0, it just needs to wait its turn. What I want is admission control with fairness: everyone gets in eventually, in the order they arrived, but the number of people simultaneously inside the expensive part of the system — seat locking, payment — is capped to what the backend can actually sustain.
>
> I'd implement this with a Redis Sorted Set as the waiting room. The instant a user clicks 'Buy,' before touching the booking service at all, I issue them a queue token and run `ZADD waiting_room <arrivalTimestamp> <queueId>`. That's an O(log N) operation, so even 500,000 simultaneous joins are trivial for Redis — this is exactly the kind of write burst that would kill a relational database but is a non-event for an in-memory sorted set.
>
> A background admission worker runs on a fixed interval — say every 2 seconds — and pops the lowest-scored (oldest) N entries off the ZSET using an atomic Lua script that does `ZRANGE` then `ZREM` together, so multiple worker replicas never double-admit the same person. N is dynamically sized to the current headroom: I track active bookers in a Redis Set, and only admit enough new users to top back up to the 2,000 cap. Admitted users get a short-lived token, say a 5-minute TTL, and the client polls `ZRANK` to show their live position and estimated wait time.
>
> The operational concern I'd flag immediately is the abandoned admitted-slot problem: a user gets admitted, but doesn't act — they tabbed away, their payment failed silently, whatever. If I don't reclaim that slot, it sits wasted for the full TTL while thousands of people behind them wait unnecessarily. My mitigation is twofold: the 5-minute TTL is a hard backstop, and I run a lightweight sweep every 30 seconds that checks the active-bookers set against which admitted tokens have actually expired, removing stale entries so the next admission tick can immediately fill the freed slot. That keeps the effective concurrency close to the true 2,000 cap instead of silently degrading over the sale window."

---

## PART 5 — DECISION FRAMEWORK

### Waiting Room vs Alternatives for Flash-Traffic Admission Control

| Approach | How It Works | Tradeoff | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **Rate limiting (token bucket)** | Reject/delay requests above N/sec | Unfair, no ordering, retry storms | <5ms | Low | Legitimate users get 429s indefinitely under sustained load |
| **Simple hard queue (DB table)** | `INSERT INTO queue` row per user, poll `SELECT COUNT(*) WHERE id < mine` | The queue table itself becomes the bottleneck under burst writes | 50-200ms (DB round trip) | Low | Falls over at exactly the burst it's meant to protect against |
| **Redis ZSET waiting room (this file)** | `ZADD`/`ZRANGE`/`ZREM` drip-feed, FIFO by score | Requires a reclaim strategy for abandoned admitted slots | 1-5ms (Redis) | Medium | Slot-abandonment left unhandled silently shrinks effective throughput |
| **Load-shedding at CDN/edge (e.g. static "queue-it" page)** | Edge serves a static holding page, no origin hit until admitted | No real FIFO fairness unless paired with a backend queue anyway | <10ms (edge cached) | Medium | Doesn't solve backend concurrency alone — usually layered ON TOP of a real waiting room |
| **Optimistic concurrency + retry (no queue at all)** | Let everyone through, rely on DB row locks / optimistic version checks to fail fast | Massive wasted work — most requests fail after doing partial work | Highly variable | Low | Guaranteed backend meltdown at genuine flash-sale scale |

### When a waiting room is right

```
✓ Traffic arrives in a predictable, scheduled burst (ticket drop, product launch)
✓ Backend has a hard concurrency ceiling (DB connections, payment gateway rate limits)
✓ Fairness matters — users will notice and complain if order isn't FIFO
✓ You can tolerate users waiting minutes, as long as they see live position/ETA
✓ You need graceful admission ramp-up, not a wall of rejections
```

### Skip a waiting room when

```
✗ Traffic is organic and roughly steady-state — a simple rate limiter + autoscaling suffices
✗ Backend can horizontally scale fast enough to absorb the burst directly
✗ The "resource" being contended isn't scarce (e.g. reading a public catalog page —
  just cache it, no admission control needed at all)
✗ Sub-second end-to-end latency is a hard requirement (queueing inherently adds wait time)
```

---

## QUICK REFERENCE CARD

```
JOIN QUEUE:
  ZADD waiting_room:{eventId} <epochMillis>.<jitter> <queueId>

CHECK POSITION:
  ZRANK waiting_room:{eventId} <queueId>      -> 0-indexed rank
  ZCARD waiting_room:{eventId}                -> total queue size

ADMIT BATCH (atomic pop, Lua):
  local batch = redis.call('ZRANGE', KEYS[1], 0, ARGV[1]-1)
  if #batch > 0 then redis.call('ZREM', KEYS[1], unpack(batch)) end
  return batch

MARK ADMITTED (TTL = abandonment backstop):
  SETEX admitted:{queueId} 300 "1"

TRACK ACTIVE CONCURRENCY:
  SADD active_bookers:{eventId} {queueId}     (on admit)
  SREM active_bookers:{eventId} {queueId}     (on complete/expiry sweep)
  SCARD active_bookers:{eventId}              -> current concurrency

RATE LIMIT vs WAITING ROOM:
  Rate limit  -> rejects excess, no fairness, no memory of who tried
  Waiting room -> admits everyone eventually, FIFO, caps concurrency

DRAIN TIME ESTIMATE:
  totalQueueSize / admitRatePerSec = estimated full-drain seconds
```

---
