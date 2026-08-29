# Distributed Rate Limiter — Senior Interview Guide
> Token Bucket + Redis Lua + Circuit Breaker. <5ms latency. 1M rps.

---

# PAGE 1 — Opening Script (Speak in 90 seconds)

```
"A rate limiter is middleware that sits between the load balancer and your backend.
 Every request passes through the API Gateway, which extracts the client identity —
 user ID, API key, or IP — and checks Redis: does this client have budget left?

 I'd go with Token Bucket implemented as a Redis Lua script.
 Each client gets a bucket. Bucket has a capacity — say 100 tokens.
 Tokens refill at a fixed rate — say 10 per second.
 One request consumes one token. If the bucket is empty, I return 429.

 The Lua script runs atomically inside Redis — single-threaded, nothing can
 interleave. Two Gateway instances hitting the same user at the same moment?
 Redis queues the EVAL calls and runs them one at a time. No race conditions.
 No locks. One network roundtrip.

 Rate limit policies — who gets 100/min vs 1000/min — live in Postgres
 and are cached in Redis for an hour. The hot path never touches the database.

 Total overhead per request: under 5ms."
```

---

# PAGE 2 — Requirement Clarification Script

**Say this before drawing anything:**

```
"Before I start designing, let me ask a few things that will change my approach:

 First — scale. Are we talking 10K requests per second or 1 million?
 That determines whether we need Redis Cluster or a single Redis instance.

 Second — what's the rate limit key? User ID, API key, IP address, or all three?
 Multi-level limiting is more complex but prevents abuse at each level independently.

 Third — should limits be configurable at runtime without a service restart?
 That means storing policies in Postgres and caching in Redis with write-through.

 Fourth — do different tiers get different limits?
 Free: 100/min, Premium: 1000/min, Enterprise: 10K/min.

 Fifth — consistency vs availability. If Redis goes down for 30 seconds,
 should we fail open and allow all requests, or fail closed and return 503?
 My default is fail open — rate limiting is best-effort protection.
 A full outage is always worse than a brief permissive window.

 Sixth — latency budget. Should this add under 5ms? Under 1ms?
 That determines how aggressively I optimise the Redis path."
```

## Functional Requirements

```
FR1  Limit requests per client (User ID / API Key / IP) per time window
FR2  Rules configurable at runtime — no redeploy
FR3  Reject excess with HTTP 429 + Retry-After + X-RateLimit-Reset headers
FR4  Tier-based limits: Free=100/min  Premium=1000/min  Enterprise=10K/min
FR5  Multi-level: per-user AND per-IP AND per-endpoint simultaneously
FR6  Burst support: full bucket = all tokens usable instantly
```

## Non-Functional Requirements

```
Scale      1,000,000 req/sec across cluster
Latency    <5ms added per request (rate limit MUST NOT be the bottleneck)
CAP        AP — slight over-limit acceptable; never block on correctness
Durability Token state survives Redis failover (replication lag <1ms)
```

---

# PAGE 3 — Decision Framework

**Walk through this out loud:**

```
"Let me think through the data model first, because that drives everything.

 Each request is a read + write on a counter. At 1M rps that's 1M writes/sec.
 A relational DB tops out at maybe 10K writes/sec with good indexing.
 That's a 100x gap. So counters go in Redis — sub-millisecond, in-memory,
 atomic operations.

 Now the distributed consistency problem.
 I have 40 API Gateway instances. They all need to share the same counter.
 If I keep counters local per-instance, a user can abuse the system by
 round-robining requests across instances. So state must be centralised.
 Centralised in-memory store with atomic operations — that's Redis.

 Next, race condition.
 Two instances read tokens=1 simultaneously. Both see 1 token. Both allow.
 Tokens go to -1. That's wrong. The fix is to make read + decrement atomic.
 Redis is single-threaded. A Lua script runs as one EVAL — indivisible.
 No lock needed. No retry needed. Just one roundtrip.

 Finally, policy storage.
 Policies change rarely — an admin updates a limit maybe once a week.
 But they're read on every single request. So: store truth in Postgres
 (CRUD-friendly, transactional), cache in Redis with 1hr TTL.
 On update: write-through to Redis + Pub/Sub to invalidate all Gateway caches."
```

---

# PAGE 4 — Algorithm Comparison

```
┌────────────────────────┬───────────┬──────────────┬──────────────┬──────────────────────┐
│ Algorithm              │ Memory    │ Accuracy     │ Burst        │ Production Use       │
├────────────────────────┼───────────┼──────────────┼──────────────┼──────────────────────┤
│ Fixed Window Counter   │ Very Low  │ Low          │ Edge spike   │ Internal APIs only   │
│ Sliding Window Log     │ Very High │ Perfect      │ No           │ Fraud / low-traffic  │
│ Sliding Window Counter │ Low       │ Good (approx)│ No           │ Middle-ground        │
│ Token Bucket ★         │ Low       │ Good         │ Yes          │ AWS, Stripe, GitHub  │
│ Leaky Bucket           │ Medium    │ Good         │ No (queued)  │ Traffic shaping only │
└────────────────────────┴───────────┴──────────────┴──────────────┴──────────────────────┘
★ = recommended
```

**Algorithm pick script:**

```
"If someone asks me to pick: Token Bucket, always, for user-facing APIs.

 Here's why I rule out the others quickly:

 Fixed Window — there's a boundary spike problem. A user can send 100 requests
 at 10:00:59 and 100 more at 10:01:00 — 200 requests in 2 seconds while claiming
 they respected 100/min. Exploitable at the boundary.

 Sliding Window Log — perfect accuracy but stores one timestamp per request.
 At 50M users × 100 req/min that's 5 billion entries in Redis. Not viable.

 Sliding Window Counter — uses a weighted approximation across two windows.
 Better than fixed, worse than log. I'd use this if Token Bucket isn't available
 but it doesn't support bursts naturally.

 Leaky Bucket — smooths output to a fixed rate. Good for shaping outbound traffic
 to a 3rd-party API that can't handle bursts. Bad for user-facing APIs because
 requests queue up — that adds latency.

 Token Bucket — low memory (2 integers per user), supports bursts by design,
 no exploitable boundary, continuous refill. This is what AWS API Gateway,
 Stripe, and GitHub all use in production."
```

---

# PAGE 5 — Token Bucket Deep Dive

## Visual: Bucket State Over Time

```
capacity = 100 tokens   refill_rate = 10 tokens/sec

t=0s    ████████████████████████████████████████  100 tokens (full)
        │
        │  100 requests arrive at once (burst)
        ▼
t=0s    ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    0 tokens  ← ALL 100 ALLOWED ✅
        │
        │  5 seconds pass, no requests
        ▼
t=5s    ████████████████████████░░░░░░░░░░░░░░░░   50 tokens  (5s × 10/s refill)
        │
        │  60 requests arrive
        ▼
t=5s    ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░    0 tokens  ← 50 allowed, 10 → 429
        │
        │  0.1 seconds pass
        ▼
t=5.1s  █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    1 token   (0.1s × 10/s = 1 token)
        │
        │  1 request arrives
        ▼
t=5.1s  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    0 tokens  ← 1 allowed ✅

KEY:
  capacity     = max burst you allow at once
  refill_rate  = sustained throughput (tokens/sec)
  These are tuned independently — that's the power of Token Bucket.
```

## Redis State Per Client

```
Redis HASH:  rate_limit:{clientId}:{endpoint}
             ┌─────────────────────────────────────┐
             │  tokens      │  95.4                │  ← fractional (double)
             │  last_refill │  1706270445823        │  ← epoch ms
             └─────────────────────────────────────┘
             TTL: 3600s (auto-expire inactive users)

Policy Cache:  policy:{clientId}:{endpoint}
             ┌──────────────────────────────────────────────────────────┐
             │  { "limit": 100, "refill_rate": 10, "burst": 100,        │
             │    "algorithm": "TOKEN_BUCKET", "enforce_by": "USER_ID" }│
             └──────────────────────────────────────────────────────────┘
             TTL: 3600s
```

## Lua Script Logic (narrate this, don't write it)

```
"The Lua script does 5 things atomically:

  1. Read tokens + last_refill from the Redis HASH
  2. Calculate elapsed = now - last_refill  (in seconds)
  3. Refill: tokens = min(capacity,  tokens + elapsed × refill_rate)
  4. If tokens >= 1:
       subtract 1, write back to Redis, set TTL, return 1 (allow)
     Else:
       write back last_refill only, return 0 (deny → 429)

 All of this is one EVAL call. Redis runs it without interruption.
 No other command executes between the read and the write.
 That's the guarantee that eliminates the race condition."
```

## Concurrent Request Race — Before and After Lua

```
WITHOUT LUA (broken):
  Time ─────────────────────────────────────────────────────────►

  Gateway 1:  GET tokens ──► sees 1 ──────────────────► DECR ──► -1 ← BUG
                                       ↑
  Gateway 2:              GET tokens ──► sees 1 ──────► DECR ──► -1 ← BUG
                                                    ↑
  Gap between GET and DECR = race window            │
  Both see 1, both allow, both decrement            │
                                                    └── both requests go through ❌

WITH LUA (correct):
  Time ─────────────────────────────────────────────────────────►

  Gateway 1:  EVAL ──► [Redis queues] ──► runs atomically ──► returns 1 (allow) ✅
  Gateway 2:  EVAL ──► [Redis queues] ──► waits ─────────────► runs ──► returns 0 (deny) ✅

  Redis queues concurrent EVALs and runs them serially.
  Second request sees tokens = 0 after first consumed the last token.
```

---

# PAGE 6 — Architecture Diagrams

## Component View

```
                            ┌──────────────────────────────────────────┐
                            │             REDIS CLUSTER                 │
                            │                                           │
                            │  Shard 1        Shard 2        Shard 3   │
                            │  (users A-F)    (users G-N)   (users O-Z)│
                            │  ┌──────────┐   ┌──────────┐  ┌────────┐│
                            │  │tokens=95 │   │tokens=40 │  │tokens= ││
                            │  │refill=.. │   │refill=.. │  │  100   ││
                            │  └──────────┘   └──────────┘  └────────┘│
                            │  consistent hashing: hash(userId) → shard│
                            └──────────────────────────────────────────┘
                                    ▲               ▲              ▲
                                    │               │              │
                            ┌───────┘        ┌──────┘       ┌─────┘
                            │                │              │
                   ┌────────────────┐ ┌──────────────┐ ┌────────────────┐
  Client           │  API Gateway 1 │ │ API Gateway 2│ │  API Gateway 3 │
   │               │                │ │              │ │                │
   │  ┌─────────┐  │  1.Auth check  │ │              │ │                │
   └─►│  Load   │─►│  2.Get policy  │ │  (same flow) │ │  (same flow)   │
      │Balancer │  │  3.EVAL Lua    │ │              │ │                │
      └─────────┘  │  4.Allow/429   │ │              │ │                │
                   └────────┬───────┘ └──────┬───────┘ └───────┬────────┘
                            │                │                  │
                            └────────────────┼──────────────────┘
                                             ▼
                   ┌─────────────────────────────────────────────────┐
                   │                  BACKEND SERVICES                │
                   │  UserSvc    OrderSvc    PaymentSvc    SearchSvc  │
                   └─────────────────────────────────────────────────┘
                                             ▲
                                             │ (cache miss only — ~1% of requests)
                   ┌─────────────────────────┴───────────────────────┐
                   │            POLICY DATABASE (Postgres)            │
                   │           rate_limit_rules — ~250M rows          │
                   └─────────────────────────────────────────────────┘
```

**How to walk through this:**

```
"Start at the left. Client hits the Load Balancer. LB distributes to one of
 40 API Gateway instances — any instance can serve any request.

 The Gateway is stateless. It holds no counters locally. All rate limit state
 lives in Redis Cluster. So it doesn't matter which Gateway receives the request.

 The Redis Cluster is sharded by userId using consistent hashing. user123 always
 maps to Shard 1. This means all requests for user123 go to the same Redis node —
 no cross-shard coordination needed for a single user's counter.

 Each shard stores two things per user: the token state HASH and the policy cache.
 The EVAL call is under 1ms co-located. Total Gateway overhead: under 5ms.

 Postgres is the cold path. First request after TTL expiry hits it.
 99% of requests hit Redis cache only."
```

---

## Request Flow — Step by Step

```
  Client Request: GET /api/orders   Authorization: Bearer <jwt>
         │
         ▼
  ┌──────────────────────────────────────────────────────────────┐
  │  API GATEWAY                                                  │
  │                                                              │
  │  Step 1: Extract identity                                    │
  │    Parse JWT → userId = "user123"                            │
  │    endpoint  = "/api/orders"                                 │
  │                                                              │
  │  Step 2: Get policy (Redis first)                            │
  │    GET policy:user123:/api/orders                            │
  │    ├── HIT  → {"limit":100, "refill":10, ...}  ← 99% path   │
  │    └── MISS → SELECT from Postgres → SET in Redis EX 3600   │
  │                                                              │
  │  Step 3: EVAL Lua script (atomic)                            │
  │    EVAL lua_script rate_limit:user123:/api/orders 100 10 now │
  │    ├── returns 1 → ALLOW                                     │
  │    └── returns 0 → DENY                                      │
  │                                                              │
  │  Step 4a (ALLOW): Set response headers, forward to backend   │
  │    X-RateLimit-Limit:     100                                │
  │    X-RateLimit-Remaining: 99                                 │
  │    X-RateLimit-Reset:     1706274045                         │
  │                                                              │
  │  Step 4b (DENY): Return 429 immediately, never hit backend   │
  │    HTTP 429                                                  │
  │    Retry-After:           1                                  │
  │    X-RateLimit-Remaining: 0                                  │
  └──────────────────────────────────────────────────────────────┘
```

---

## Redis Consistent Hashing — Shard Assignment

```
USER IDs mapped to Redis shards via consistent hashing:

hash("user-alice")  = 12847  → Shard 1  (range 0–16383)
hash("user-bob")    = 28941  → Shard 2  (range 16384–32767)
hash("user-carol")  = 41002  → Shard 3  (range 32768–49151)
hash("user-dave")   = 57234  → Shard 4  (range 49152–65535)

Hash Ring:
     0
    ╱ ╲
Shard4  Shard1
  |        |
Shard3  Shard2
    ╲ ╱
   32767

Key property:
  All requests for user-alice ALWAYS go to Shard 1.
  No cross-shard coordination. No distributed transaction needed.
  Single user's counter is always on one node → atomicity guaranteed.

When a shard is added (scale-out):
  Only ~1/N keys move. Other users unaffected.
  This is why consistent hashing beats modulo hashing (mod N moves N/2 keys).
```

---

## Circuit Breaker State Machine

```
                    ┌─────────────────┐
                    │                 │
           ┌───────►│     CLOSED      │◄──────────────────┐
           │        │  (normal ops)   │                   │
           │        └────────┬────────┘                   │
           │                 │                            │
           │    10 consecutive Redis failures             │
           │                 │                            │
           │                 ▼                            │
           │        ┌─────────────────┐                   │
           │        │                 │                   │
           │        │      OPEN       │                   │
           │        │  (fail all      │                   │ 1 test request
           │        │   requests      │                   │ succeeds
           │        │   in ~0ms,      │                   │
           │        │   no Redis call)│                   │
           │        └────────┬────────┘                   │
           │                 │                            │
           │         after 30 seconds                     │
           │                 │                            │
           │                 ▼                            │
           │        ┌─────────────────┐                   │
           │        │                 │──────────────────►┘
           │        │   HALF-OPEN     │
           └────────│  (try 1 request)│ 1 test request fails
                    │                 │──────────────────►(back to OPEN)
                    └─────────────────┘

OPEN state behaviour:
  fail OPEN → allow all requests through
  Why: rate limiting is best-effort. Full outage is worse than a
       brief permissive window. Users shouldn't see errors because
       our rate limiter's Redis is having a bad day.

FAIL CLOSED alternative (when to use):
  Fintech, healthcare, compliance-critical APIs where a brief burst
  would violate regulatory limits. Accept the outage risk.
```

---

## Policy Update — Write-Through Cache Flow

```
Admin UI          Policy Service       Postgres         Redis           API Gateways
   │                    │                 │               │               (all 40)
   │─ PUT /rules/5 ────►│                 │               │                  │
   │  {limit: 200}      │                 │               │                  │
   │                    │─ UPDATE ───────►│               │                  │
   │                    │  rate_limit_rules               │                  │
   │                    │  SET limit=200  │               │                  │
   │                    │  WHERE rule_id=5│               │                  │
   │                    │◄─ OK ───────────┤               │                  │
   │                    │                                 │                  │
   │                    │─ SET policy:user123 ───────────►│                  │
   │                    │  {limit:200,...} EX 3600         │                  │
   │                    │                                 │                  │
   │                    │─ PUBLISH policy_update ─────────┼─────────────────►│
   │                    │  {rule_id: 5,                   │  all 40 gateways │
   │                    │   subject: "user123"}           │  subscribed to   │
   │                    │                                 │  this channel    │
   │◄─ 200 OK ──────────┤                                 │                  │
   │                    │                                 │         [on receive]
   │                    │                                 │    DEL local cache
   │                    │                                 │    for rule_id=5
   │                    │                                 │    (next request
   │                    │                                 │     re-fetches)

Propagation latency: <1 second (vs TTL-only: up to 1 hour stale)
```

---

# PAGE 7 — Database Schema

## ER Diagram

```
┌─────────────────────────────────┐         ┌───────────────────────────────────────────┐
│           clients               │         │           rate_limit_rules                 │
├─────────────────────────────────┤         ├───────────────────────────────────────────┤
│ client_id      UUID  PK         │         │ rule_id        UUID  PK                    │
│ api_key        VARCHAR  UNIQUE  │         │ subject_type   ENUM                        │
│ tier           ENUM             │         │                (USER_ID, API_KEY,          │
│                (FREE,PREMIUM,   │◄────────│                 IP, TIER, GLOBAL)          │
│                 ENTERPRISE)     │         │ subject_value  VARCHAR  (user123/PREMIUM/*)│
│ quota          INT              │         │ endpoint       VARCHAR  (* = all)          │
│ created_at     TIMESTAMPTZ      │         │ algorithm      ENUM  (TOKEN_BUCKET)        │
└─────────────────────────────────┘         │ request_limit  INT                         │
                                            │ window_sec     INT                         │
                                            │ burst_capacity INT                         │
                                            │ refill_rate    DECIMAL(10,2)               │
                                            │ enforce_by     VARCHAR                     │
                                            │                (USER_ID/TENANT_ID)         │
                                            │ is_active      BOOLEAN  DEFAULT true       │
                                            │ created_at     TIMESTAMPTZ                 │
                                            │ updated_at     TIMESTAMPTZ                 │
                                            ├───────────────────────────────────────────┤
                                            │ INDEX(subject_type, subject_value,         │
                                            │       endpoint)                            │
                                            └───────────────────────────────────────────┘
```

## enforce_by — The Key Design Decision

```
"When the interviewer asks about multi-tenant, this is the field to mention."

CASE A: enforce_by = USER_ID
┌──────────────────────────────────────────────────────┐
│  Rule: TIER=PREMIUM, limit=1000/min, per USER        │
│                                                      │
│  userA ──► own bucket  [████░░░░] 600/1000 tokens    │
│  userB ──► own bucket  [████████] 1000/1000 tokens   │
│  userC ──► own bucket  [██░░░░░░] 200/1000 tokens    │
│                                                      │
│  Redis keys:                                         │
│    rate_limit:userA:/api/users                       │
│    rate_limit:userB:/api/users                       │
│    rate_limit:userC:/api/users                       │
└──────────────────────────────────────────────────────┘

CASE B: enforce_by = TENANT_ID
┌──────────────────────────────────────────────────────┐
│  Rule: TIER=ENTERPRISE, limit=10000/min, per TENANT  │
│                                                      │
│  org-ABC shared bucket:                              │
│  [████████░░░░░░░░░░░░░░] 4000/10000 tokens         │
│         ▲        ▲       ▲                           │
│       userA    userB   userC (all drain same bucket) │
│                                                      │
│  Redis key:                                          │
│    rate_limit:tenant-ABC:/api/users                  │
└──────────────────────────────────────────────────────┘

Interview line:
  "enforce_by decides whether each user gets their own bucket
   or all users in an org share one bucket. Enterprise B2B customers
   typically want TENANT-level so they control distribution internally."
```

---

# PAGE 8 — Sequence Diagrams

## Happy Path (Token Available)

```
Client      LB         API Gateway         Redis           Backend
  │          │               │               │                │
  ├─GET /api/orders─────────►│               │                │
  │          │               │               │                │
  │          │               ├─GET policy:u1─►               │
  │          │               │◄─{limit:100}──┤               │
  │          │               │               │                │
  │          │               ├─EVAL lua──────►               │
  │          │               │               │[atomic]        │
  │          │               │               │tokens=99       │
  │          │               │◄─ return 1 ───┤               │
  │          │               │               │                │
  │          │               ├─────────────────────────────► │
  │          │               │◄─ 200 {orders:[...]} ─────────┤
  │◄─200 ────────────────────┤               │                │
  │  X-RateLimit-Limit: 100  │               │                │
  │  X-RateLimit-Remaining:99│               │                │
  │  X-RateLimit-Reset: {ts} │               │                │
```

## Rejected Path (Bucket Empty)

```
Client      LB         API Gateway         Redis           Backend
  │          │               │               │                │
  ├─GET /api/orders─────────►│               │                │
  │          │               ├─EVAL lua──────►               │
  │          │               │               │[tokens=0]      │
  │          │               │◄─ return 0 ───┤               │
  │          │               │               │                │
  │◄─429 ────────────────────┤               │    (never      │
  │  Retry-After: 1          │               │     reached)   │
  │  X-RateLimit-Remaining: 0│               │                │
```

## Cache Miss Path (First Request or TTL Expired)

```
Client      API Gateway         Redis        Postgres       Backend
  │               │               │              │              │
  ├─GET /api/orders─────────────► │              │              │
  │               ├─GET policy───►│              │              │
  │               │◄─ nil ────────┤              │              │
  │               │                             │              │
  │               ├─SELECT limit FROM rules──────►             │
  │               │◄─ {limit:100, refill:10} ───┤              │
  │               │                                            │
  │               ├─SET policy:u1 {..} EX 3600─►│             │
  │               ├─EVAL lua──────────────────► │             │
  │               │◄─ return 1 ────────────────┤              │
  │               ├─────────────────────────────────────────► │
  │◄─200 ─────────┤               │              │             │
```

---

# PAGE 9 — Production Techniques

## T1 — Redis Lua for Atomicity

```
"The core distributed systems problem here is the check-then-act race.
 You read the counter, decide to allow, then write. Between read and write,
 another instance can do the same thing. Both see enough tokens. Both allow.

 The solution: Redis Lua. Redis is single-threaded internally. When you
 send an EVAL command, Redis processes the entire Lua script before
 accepting the next command. It's like a database transaction that's
 guaranteed to not interleave with anything.

 No distributed locks. No Redlock complexity. No retries.
 Just one EVAL call per request. That's it."
```

## T2 — Policy Caching

```
"Rate limit rules change maybe once a week. But they're read on every
 single request — potentially 1 million times per second.

 Storing rules only in Postgres would mean 1M DB reads/sec on a system
 that handles maybe 50K reads/sec under load. That's instant catastrophe.

 So: Postgres is the source of truth. Redis is the cache with 1-hour TTL.
 On cache miss (first request or expiry): fetch from Postgres, write to Redis.
 On admin update: write to Postgres first, then immediately write-through
 to Redis and publish a Pub/Sub event. All Gateway instances see the new
 rule in under 1 second. No stale limits. No restart needed."
```

## T3 — Token Bucket

```
"Token Bucket is the industry standard for user-facing APIs for three reasons:

 First, it supports bursts naturally. A user who hasn't made requests for
 5 minutes has accumulated tokens up to the bucket capacity. They can spend
 all of them at once. That's legitimate use — a batch job, a mobile app
 that just came online.

 Second, no exploitable boundary. Fixed Window resets at a clock boundary.
 Token Bucket refills continuously. There's no 'boundary second' where
 a user can double their effective rate.

 Third, two knobs: capacity and refill_rate. Tune them independently.
 capacity = max burst. refill_rate = sustained throughput.
 A trading API might want capacity=5 but refill_rate=2/sec.
 An image generation API might want capacity=10 but refill_rate=1/sec."
```

## T4 — Redis Cluster + Consistent Hashing

```
"At 1M rps, one Redis node handles about 300K EVAL commands/sec.
 We need at least 4 shards. With 2x headroom: 8 shards.

 Consistent hashing ensures user123 always maps to the same shard.
 This is critical because the Lua script's atomicity guarantee only holds
 within a single Redis node. If user123 could land on different shards,
 we'd need cross-shard transactions — expensive, complex, fragile.

 With consistent hashing: one user, one shard, one atomic EVAL. Clean."
```

## T5 — Multi-Tier Limiting

```
"Three independent limits enforced simultaneously:

  per-user:     user123 can't exceed their personal quota
  per-IP:       single IP can't DDoS through multiple accounts
  per-endpoint: /ai/generate capped at 10/min regardless of tier

 If ANY level is exceeded → 429. Strictest wins.

 In Redis, each dimension is a separate key:
   rate_limit:user:user123:/api/generate
   rate_limit:ip:203.0.113.5:/api/generate
   rate_limit:endpoint:/api/generate

 Three EVAL calls per request, all to the same Redis cluster.
 If one returns 0, short-circuit — skip the other checks."
```

## T6 — Horizontal Gateway Scaling

```
"The API Gateway is completely stateless. No local counters. No sessions.
 All rate limit state lives in Redis. So you can run 40 instances or 400 —
 they're all identical. Auto-scaling on CPU or request queue depth works
 perfectly because adding an instance doesn't change the rate limit logic.

 This is why centralised Redis is non-negotiable. Local counters would
 mean per-instance limits, and users could exploit that by spreading
 requests across instances."
```

## T7 — Circuit Breaker

```
"Redis is highly available but not perfectly available. Network partitions,
 memory pressure, Redis Cluster rebalancing — these cause brief outages.

 The circuit breaker pattern handles this:
 After 10 consecutive Redis timeouts → open the circuit for 30 seconds.
 During those 30 seconds: don't even try Redis. Allow all requests through.
 After 30 seconds: half-open. Try one request. If Redis is back → close circuit.
 If still failing → open for another 30 seconds.

 I always fail OPEN, not CLOSED. Here's why: rate limiting is a protection
 mechanism. If the protection mechanism breaks, the right move is to let
 traffic through — not to take down the entire API for everyone.
 The exception: financial APIs where over-limit = compliance violation.
 Those fail CLOSED."
```

## T8 — 429 Headers

```
"Four headers that every rate-limited response must include:

  X-RateLimit-Limit:     100   ← what the limit is
  X-RateLimit-Remaining: 0     ← how many left (zero = why you got 429)
  X-RateLimit-Reset:     {ts}  ← unix timestamp when bucket refills to 1
  Retry-After:           1     ← seconds to wait before retrying

 These let clients implement intelligent backoff. Without them, clients
 retry immediately and hammer your already-strained API. With them,
 a mobile SDK can schedule the retry at exactly the right moment.

 Retry-After = ceil((1 - current_tokens) / refill_rate)"
```

## T9 — Monitoring & Alerting

```
"Two alerts I'd configure from day one:

 First: rejection rate > 5% of total traffic.
 Either a misconfigured limit is blocking legitimate users,
 or there's an active attack. Investigate immediately.

 Second: Redis p99 latency > 10ms.
 Our budget is 5ms total for the rate limit check.
 If Redis is taking 10ms p99, we're blowing the budget.
 Usually means a shard is overloaded or Redis needs more memory.

 Metrics to track: request count, 429 rate, Redis latency p50/p95/p99,
 policy cache hit rate, per-endpoint breakdown."
```

## T10 — Write-Through Cache + Pub/Sub

```
"When an admin changes a rate limit rule, two things must happen:

 First, write to Postgres. That's the source of truth.
 Second, immediately update the Redis cache — don't wait for TTL expiry.
 If you don't do this, a Premium user's limit might stay at 100/min for
 an hour after you bumped it to 1000/min. That's a bad support experience.

 After writing to Redis, publish a message on a Pub/Sub channel:
 'rule_id:5 changed'. All 40 API Gateways are subscribed to this channel.
 On receiving the message, each gateway deletes its local in-process cache
 for that rule. The next request re-fetches from Redis, which now has the
 new value. Total propagation: under 1 second."
```

---

# PAGE 10 — Capacity Estimation

**Speak this, don't just write numbers:**

```
"Let me do a quick back-of-envelope to sanity-check the design.

 Traffic: 1M req/sec. Users: 50M active.

 Redis memory for token state:
   Each user + endpoint: one HASH with 2 fields.
   Key: ~40 bytes. Values: ~30 bytes. Redis overhead: ~100 bytes.
   Total: ~170 bytes per user per endpoint.
   With 3 endpoints per user: 50M × 3 × 170B = 25GB.
   But most users are inactive — TTL=3600s means only the last-hour
   active users have live keys. Maybe 5-10% hot = 1-2GB actual.

 Redis throughput:
   1M EVAL/sec. Single Redis node: ~300K EVAL/sec.
   1M / 300K = 4 shards minimum. With 2x headroom = 8 shards.
   That's 8 Redis masters, each with 1-2 read replicas.

 Latency breakdown:
   Policy cache lookup:  0.5ms
   EVAL Lua script:      1.0ms
   Network roundtrip:    1.0ms
   Total:               ~2.5ms — well within 5ms budget.

 API Gateway instances:
   Each handles ~50K req/sec. 1M / 50K = 20 minimum.
   With 2x headroom = 40 instances.

 Postgres:
   250M rows, ~50GB. Handles maybe 50K reads/sec, but with 99% cache
   hit rate on Redis, actual read load is near zero."
```

---

# PAGE 11 — Senior Trap Questions

## Q1: Race condition in distributed rate limiting?

```
WEAK:  "Use Redis locks."
WHY WRONG: Distributed locks add complexity, have timeout edge cases,
           deadlock risk, and Redis is single-threaded anyway — locks are overkill.

STRONG:
"Redis is single-threaded. Every command executes serially.
 The race is: two Gateway instances both read tokens=1,
 both decide to allow, both decrement → tokens=-1.

 Fix: Redis Lua EVAL. The entire script — read + calculate + write —
 executes as one indivisible operation. Nothing can interleave.
 Gateway 1 and Gateway 2 both send EVAL. Redis processes one, then the other.
 The second one sees tokens=0 after the first consumed the last token.

 No locks. No deadlocks. No extra roundtrips. Just EVAL."
```

## Q2: Token Bucket vs Leaky Bucket?

```
WEAK:  "They're basically the same."
WHY WRONG: Fundamentally different output characteristics.

STRONG:
"The difference is on the output side, not the input side.

 Token Bucket: I send 100 requests. All 100 hit the backend immediately.
 The burst propagates through. Good for APIs where latency matters.

 Leaky Bucket: I send 100 requests. They queue. They exit at 10/sec.
 The backend sees a perfectly smooth stream — never a burst.
 Good for shaping outbound traffic to a 3rd-party API that has
 its own rate limit or charges per call.

 For our API Gateway: Token Bucket.
 For outbound Webhook delivery, email sending, SMS: Leaky Bucket."
```

## Q3: Redis goes down?

```
WEAK:  "Restart Redis."

STRONG:
"Two valid approaches, different trade-offs.

 Fail open: allow all requests during Redis outage.
   Pro: zero availability impact.
   Con: brief unlimited access window (15-30 seconds typically).
   Use when: any API where a brief burst is not catastrophic.

 Fail closed: return 503 during Redis outage.
   Pro: no policy violation window.
   Con: full API outage for all users.
   Use when: financial, compliance, or fraud-sensitive endpoints.

 My default implementation: circuit breaker.
 10 consecutive Redis timeouts → open circuit for 30 seconds.
 During open: fail OPEN, log the event, alert on-call.
 After 30s: half-open, test one request, auto-recover if Redis is back.

 The circuit breaker prevents thundering herd when Redis recovers —
 all 40 instances don't hammer Redis simultaneously on reconnect."
```

## Q4: Multi-region rate limiting?

```
WEAK:  "Single Redis cluster, route everything there."
WHY WRONG: +100ms latency from distant regions. Blows the 5ms budget.

STRONG:
"Three options with different trade-offs:

 Option A — Per-region limits (my default):
   Redis cluster per region: us-east, eu-west, ap-south.
   User gets 100/min in each region → 300/min globally.
   Pro: zero cross-region latency. Simple. Fast.
   Con: slight global over-limit possible.
   Use when: slight over-limit is acceptable (most APIs).

 Option B — Global single Redis:
   All Gateways worldwide route to one cluster.
   Pro: exact global enforcement.
   Con: 50-150ms added latency for distant regions. Unacceptable.
   Use when: fintech, compliance-critical, where over-limit = violation.
   Mitigation: co-locate the single cluster in the lowest-latency region
   for the most sensitive users.

 Option C — CRDT-based eventual consistency:
   Each region tracks local count. Periodically sync deltas.
   Pro: low latency, approximate global limit.
   Con: significant implementation complexity, hard to reason about.
   Use when: you have a distributed systems team and Option A isn't accurate enough.

 My recommendation: start with Option A. Implement Option B for endpoints
 that are compliance-sensitive."
```

## Q5: Fixed Window boundary problem?

```
STRONG:
"Fixed Window resets its counter at a hard clock boundary.

 Example: limit = 100/min.
 User sends 99 requests at 10:00:59 — last second of window 1. All allowed.
 User sends 100 requests at 10:01:00 — first second of window 2. All allowed.
 Result: 199 requests in 2 seconds. Violated the spirit of 100/min.

     Window 1     │     Window 2
     ─────────────│─────────────
     99 req at :59│100 req at :00
                  │
                  └── 199 requests in 2 seconds!

 Token Bucket has no boundary. Refill is continuous from the last request timestamp.
 There's no 'reset moment' to exploit.
 And since it's checked via Lua atomically, you can't race against the refill either."
```

## Q6: How would you test this?

```
STRONG:
"Three levels of testing:

 Unit: test the Lua script in isolation.
 Feed it known input: tokens=1, rate=10, elapsed=0.5.
 Assert output: tokens=1.5 → 1 consumed → 0.5 returned → allowed.
 Test edge cases: tokens=0, refill exactly 1, overflow to capacity.

 Integration: spin up Redis in Docker.
 Fire 101 requests for the same user with limit=100.
 Assert first 100 return allow (1), 101st returns deny (0).
 Assert no race: run 1000 concurrent threads, verify exactly 100 allows.

 Load: JMeter or k6 at 10K concurrent users × 120 req/min each.
 Assert: rejection rate = ~50% (half requests over limit).
 Assert: no race conditions (total allowed count = 100 × users × window_count)."
```

---

# PAGE 12 — What NOT to Say

```
╔════════════════════════════════════════════════════════════════════════════╗
║  TRAP PHRASE                    WHY IT'S WRONG                            ║
╠════════════════════════════════════════════════════════════════════════════╣
║  "Store counters in the DB"     DB can't handle 1M writes/sec.            ║
║                                 Postgres tops at ~10K. 100x gap.          ║
╠════════════════════════════════════════════════════════════════════════════╣
║  "GET then INCR in Redis"       Race condition. Two instances both see 1. ║
║                                 Both allow. Counter goes to -1.           ║
╠════════════════════════════════════════════════════════════════════════════╣
║  "Use SETNX for distributed     Lock complexity, deadlock risk, timeout   ║
║   locks"                        edge cases. Redis is single-threaded —   ║
║                                 Lua EVAL is simpler and faster.           ║
╠════════════════════════════════════════════════════════════════════════════╣
║  "It depends" (no follow-up)    Say: production API → Token Bucket.       ║
║                                 Accuracy-critical → Sliding Window Log.   ║
╠════════════════════════════════════════════════════════════════════════════╣
║  "100% accurate rate limiting"  At 1M rps, CAP says choose AP.           ║
║                                 Slight over-limit is the correct trade-off║
╠════════════════════════════════════════════════════════════════════════════╣
║  "Redis per service"            Counters must be centralised.             ║
║                                 Per-service = no global enforcement.      ║
╠════════════════════════════════════════════════════════════════════════════╣
║  "Fail closed is always safer"  Full outage affects 100% of users.        ║
║                                 Brief permissive window is usually better.║
╠════════════════════════════════════════════════════════════════════════════╣
║  "Leaky Bucket = Token Bucket"  Different output: leaky = smooth stream.  ║
║                                 Token = burst allowed through immediately.║
╚════════════════════════════════════════════════════════════════════════════╝
```

---

# PAGE 13 — Whiteboard Draw Order (7 steps, 4 minutes)

```
Step 1 — Draw the spine (30 sec)
  Client → Load Balancer → API Gateway → Redis → Backend
  Add: Policy DB below Redis

Step 2 — Add 3 Gateway boxes (20 sec)
  Show all 3 pointing to the same Redis
  Say: "All share state. Gateway is stateless."

Step 3 — Redis internals (45 sec)
  Draw two boxes inside Redis:
  ┌─────────────────────┐   ┌─────────────────────────┐
  │  Token State (HASH) │   │  Policy Cache (JSON)     │
  │  tokens=95          │   │  limit=100, refill=10    │
  │  last_refill=ts     │   │  TTL=3600s               │
  └─────────────────────┘   └─────────────────────────┘

Step 4 — Draw the Token Bucket (30 sec)
  [████████░░] capacity=10, tokens=8
  Arrow from bucket to "EVAL Lua" box

Step 5 — Write the Lua summary (not full script)
  "Atomic: read → refill → deduct → write → return 1/0"

Step 6 — 429 response headers (20 sec)
  Four header names on the response arrow:
  Limit / Remaining / Reset / Retry-After

Step 7 — Circuit Breaker (20 sec)
  Small box: "CB: 10 failures → open 30s → fail OPEN"
```

---

# PAGE 14 — Key Numbers (memorise these)

```
┌────────────────────────────────────────────────────────────┐
│  Redis single node EVAL throughput   ~300K ops/sec          │
│  Redis p99 latency (co-located)      <1ms                   │
│  Target added latency per request    <5ms                   │
│  Policy cache TTL                    3600s (1 hour)         │
│  Token state TTL (inactive users)    3600s                  │
│  Pub/Sub propagation delay           <1 second              │
│  Circuit breaker threshold           10 consecutive fails   │
│  Circuit breaker open duration       30 seconds             │
│  Redis HASH memory per user          ~170 bytes             │
│  Redis shards for 1M rps             8 (with 2x headroom)   │
│  API Gateway instances for 1M rps    40                     │
│                                                             │
│  Tier limits (typical):                                     │
│    Free       100 req/min                                   │
│    Premium    1000 req/min                                  │
│    Enterprise 10,000 req/min                                │
│    Login/auth 10 req/min (brute-force protection)           │
│                                                             │
│  HTTP status  429 Too Many Requests                         │
│  Headers:     Retry-After / X-RateLimit-Limit               │
│               X-RateLimit-Remaining / X-RateLimit-Reset     │
└────────────────────────────────────────────────────────────┘
```

---

# PAGE 15 — Final Recommendation Script

```
"Let me summarise my recommendation:

 Algorithm: Token Bucket. Burst-friendly, continuous refill, no exploitable
 boundary, proven at AWS API Gateway / Stripe / GitHub.

 Atomicity: Redis Lua EVAL. Single atomic operation. No locks. No retries.

 State: Redis Cluster with 8 shards, consistent hashing by userId.
 All API Gateway instances share the same Redis. Gateway is stateless.

 Policies: Postgres as source of truth. Redis as write-through cache, 1hr TTL.
 On admin update: write-through + Pub/Sub. Sub-second propagation to all Gateways.

 Resilience: Circuit breaker. 10 consecutive Redis failures → open for 30s.
 Fail OPEN — allow all traffic. Alert on-call. Auto-recover.

 Response: 429 with all 4 headers — Limit, Remaining, Reset, Retry-After.

 Multi-level: per-user + per-IP + per-endpoint. ANY exceeded → 429.

 Scale: <5ms added latency. Handles 1M rps. 40 Gateway instances. 8 Redis shards."
```

---

# PAGE 16 — One-Page Cheat Sheet

```
╔══════════════════════════════════════════════════════════════════════════╗
║          DISTRIBUTED RATE LIMITER — CHEAT SHEET                         ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  ALGORITHM:                                                              ║
║  Token Bucket → production APIs (burst + continuous refill)              ║
║  Sliding Window Log → fraud/login (perfect accuracy, low volume only)    ║
║  Fixed Window → internal APIs only (boundary spike exploitable)          ║
║  Leaky Bucket → outbound traffic shaping (not user-facing)               ║
║                                                                          ║
║  ATOMICITY: Redis Lua EVAL — never GET + DECR separately                 ║
║                                                                          ║
║  REDIS STATE:                                                            ║
║  HASH rate_limit:{subject}:{endpoint}  → tokens, last_refill  TTL=1hr   ║
║  JSON policy:{subject}:{endpoint}      → limit, refill, ...   TTL=1hr   ║
║                                                                          ║
║  REQUEST FLOW:                                                           ║
║  Auth → GET policy (cache) → EVAL Lua → allow/deny → headers            ║
║                                                                          ║
║  429 HEADERS (all 4):                                                    ║
║  X-RateLimit-Limit      → total quota                                    ║
║  X-RateLimit-Remaining  → remaining tokens                               ║
║  X-RateLimit-Reset      → unix ts when next token arrives                ║
║  Retry-After            → seconds to wait                                ║
║                                                                          ║
║  POLICY UPDATE:                                                          ║
║  UPDATE Postgres → SET Redis (write-through) → PUBLISH Pub/Sub          ║
║  → all Gateways invalidate local cache → <1 sec propagation             ║
║                                                                          ║
║  REDIS FAILURE:                                                          ║
║  CB: 10 failures → open 30s → fail OPEN → auto-recover                  ║
║                                                                          ║
║  MULTI-LEVEL:                                                            ║
║  per-user + per-IP + per-endpoint → ANY exceeded → 429                   ║
║                                                                          ║
║  SCALE (1M rps):                                                         ║
║  8 Redis shards  │  40 API Gateway instances  │  1 Postgres primary      ║
║                                                                          ║
║  ONE-LINE ANSWER:                                                        ║
║  "Token Bucket in Redis Lua — atomic, burst-friendly, proven at          ║
║   AWS and Stripe, <5ms overhead, circuit breaker for Redis failure."     ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

# PAGE 17 — LLD: Strategy Pattern (Code Round)

## Why Strategy Pattern

```
"I'd use Strategy Pattern here because the algorithm is a runtime decision
 driven by config. That's exactly what Strategy is for — swap behaviour
 at runtime without touching the calling code.

 Four pieces:
   RateLimiterStrategy  — interface, one method: isAllowed(clientId)
   TokenBucketLimiter   — the concrete strategy (production default)
   RateLimiterFactory   — reads config, returns the right strategy
   APIGateway           — calls isAllowed(), knows nothing about the algorithm

 Open/Closed Principle: APIGateway never changes if we add a new algorithm.
 We just add a new class implementing RateLimiterStrategy."
```

```
RateLimiterStrategy (interface)
        ↑
 TokenBucketLimiter

RateLimiterFactory.create(config) → returns TokenBucketLimiter
APIGateway.handleRequest()        → strategy.isAllowed(clientId)
```

## Class Responsibilities

```
┌──────────────────────────────────────────────────────────────┐
│  RateLimiterStrategy (interface)                             │
│  ─────────────────────────────                               │
│  + isAllowed(clientId: String): boolean                      │
│                                                              │
│  Contract: return true = allow, false = return 429           │
│  Why only clientId? Strategy fetches capacity/rate from      │
│  config internally. Caller never needs to know.              │
└──────────────────────────────────────────────────────────────┘
                        ↑ implements
┌──────────────────────────────────────────────────────────────┐
│  TokenBucketLimiter                                          │
│  ──────────────────                                          │
│  - capacity: int          (max tokens = max burst)           │
│  - refillRatePerSecond: int                                  │
│  - clientState: Map<userId, [tokens, lastRefillMs]>          │
│                           (Redis HASH in production)         │
│                                                              │
│  + isAllowed(clientId):                                      │
│    1. read tokens + last_refill                              │
│    2. elapsed = now - last_refill                            │
│    3. tokens = min(capacity, tokens + elapsed × rate)        │
│    4. if tokens >= 1: tokens--, write, return true           │
│       else:           write, return false                    │
│                                                              │
│  NOTE: synchronized here for demo. In prod: Redis Lua EVAL.  │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  RateLimiterFactory                                          │
│  ──────────────────                                          │
│  + create(config: RateLimiterConfig): RateLimiterStrategy    │
│                                                              │
│  Reads algorithmType from config, returns TokenBucketLimiter │
│  Caller (APIGateway) never does new TokenBucketLimiter().    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  APIGateway                                                  │
│  ──────────                                                  │
│  - strategy: RateLimiterStrategy                             │
│                                                              │
│  + handleRequest(clientId, endpoint): int                    │
│    1. isAuthenticated()       → 401 if not                   │
│    2. strategy.isAllowed()    → 429 if false                 │
│    3. forwardToBackend()      → 200 if allowed               │
└──────────────────────────────────────────────────────────────┘
```

## Expected Output (narrate while coding)

```
"With capacity=10, refillRate=1/sec:

 Requests 1–10  → HTTP 200  (tokens drain: 10, 9, 8 ... 1, 0)
 Request  11    → HTTP 429  (bucket empty)
 Request  12    → HTTP 429  (still empty)

 After 1 second: 1 token refills.
 Next request → HTTP 200 again.

 This demonstrates burst (all 10 at once) and sustained rate (1/sec after)."
```

## Production Upgrade: Move isAllowed to Redis Lua

```
"In production I don't use synchronized Java. I don't use local state.
 The entire isAllowed logic becomes one Redis EVAL call.

 The Lua script receives:
   KEYS[1]  = rate_limit:{clientId}:{endpoint}
   ARGV[1]  = capacity (100)
   ARGV[2]  = refillRate (10)
   ARGV[3]  = now in milliseconds

 It reads tokens + last_refill from the HASH.
 Calculates refill based on elapsed time.
 If tokens >= 1: subtract 1, write back, EXPIRE key 3600, return 1 (allow).
 Else: write back last_refill, return 0 (deny).

 Why this replaces synchronized:
   synchronized works within one JVM — one process.
   We have 40 Gateway processes. synchronized does nothing across processes.
   Redis Lua runs atomically within the single-threaded Redis engine.
   It's the distributed equivalent of synchronized."
```
