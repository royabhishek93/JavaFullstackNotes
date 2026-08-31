# Distributed Rate Limiter — Complete Interview Guide
> Control how many requests a client can make in a time window, at scale, without becoming a bottleneck.

---

# PAGE 1 — Title & Rapid Answer Script

## Rapid Answer Script (speak this in 2-3 minutes)

```
"A rate limiter sits between the Load Balancer and your backend services.
 Every request hits the API Gateway, which extracts the client identity —
 user ID, API key, or IP — and asks Redis: does this client have budget left?

 I'd implement Token Bucket with a Redis Lua script.
 Each user gets a bucket with, say, 100 tokens that refills at 10 tokens/sec.
 The Lua script atomically reads the current token count, calculates how many
 tokens refilled since the last request, deducts one, and returns allow or reject.
 Atomic execution means two simultaneous requests on different Gateway instances
 can never both see 'tokens = 1' and both go through.

 On rejection I return HTTP 429 with Retry-After and X-RateLimit-Reset headers
 so the client can back off intelligently.

 Rate-limit policies — who gets 100/min vs 1000/min — live in a Postgres table
 and are cached in Redis for an hour so the hot path never touches the DB.

 The whole check adds less than 5 ms to every request."
```

---

## Conversation Script (Interviewer ↔ Candidate)

> **Interviewer:** Design a distributed rate limiter.

> **Candidate:** Sure. Before I dive in — are we rate limiting per user, per API key, or per IP? And is this for a public API or internal services?

> **Interviewer:** Public API, per user. Scale it for something like Twitter.

> **Candidate:** Got it. So the rate limiter sits between the Load Balancer and backend services. Every request hits the API Gateway, which extracts the user ID from the JWT token and asks Redis: does this user have budget left?

> **Interviewer:** Why Redis specifically?

> **Candidate:** Two reasons — speed and atomicity. Redis is in-memory so the check takes under 1ms. And it supports Lua scripts, which lets me do the read-modify-write atomically in a single round trip. Without atomicity, two simultaneous requests on different Gateway nodes could both read "tokens = 1", both pass, and I've allowed double the traffic.

> **Interviewer:** What algorithm would you use?

> **Candidate:** Token Bucket. Each user gets a bucket — say 100 tokens — that refills at 10 tokens per second. Every request costs 1 token. The Lua script reads the current count, calculates tokens refilled since the last request using the timestamp, deducts one, and returns allow or reject. It handles bursts naturally — a user who was idle accumulates tokens up to the bucket max.

> **Interviewer:** What do you return on rejection?

> **Candidate:** HTTP 429 with two headers: `Retry-After` telling the client how many seconds to wait, and `X-RateLimit-Reset` with the exact timestamp when their bucket refills. This lets clients back off intelligently instead of hammering the system.

> **Interviewer:** Where do rate limit policies live — who gets 100/min vs 1000/min?

> **Candidate:** In a Postgres table. But I never read Postgres on the hot path — those policies are cached in Redis with a 1-hour TTL. A cache miss fetches from Postgres and repopulates. Policy changes take up to an hour to propagate, which is acceptable for this use case.

> **Interviewer:** What's the latency overhead of all this?

> **Candidate:** The whole check — Redis Lua script + header injection — adds less than 5ms to every request. That's well within acceptable API latency budgets.

---

## Token Bucket vs Leaky Bucket — Deep Explanation

**Setup for the example:** Bucket max = 10 tokens. Refill rate = 2 tokens/second.

**"Refill at 2 tokens/second" means:**
Every second that passes, the system automatically adds 2 tokens to your bucket — whether you made a request or not. Like a tap slowly dripping water into a bucket over time.

```
Second 0:  bucket = 10  (full, you start here)
Second 1:  you send 5 requests → bucket = 5,  then +2 refill → bucket = 7
Second 2:  you send 0 requests → bucket = 7,  then +2 refill → bucket = 9
Second 3:  you send 0 requests → bucket = 9,  then +2 refill → bucket = 10  (capped at max)
Second 4:  you send 0 requests → bucket = 10, then +2 refill → still 10  (can't go above max)
Second 5:  you send 10 requests all at once  → bucket = 0  (this is the BURST)
```

**"Handles bursts naturally" means:**
During seconds 2, 3, 4 you did nothing — so your bucket slowly filled back up on its own. At second 5 you can fire 10 requests all at once. That sudden spike is the burst. Token Bucket allows it because you saved up tokens by being idle.

**"Up to the bucket max" is the safety cap:**
Even if you were idle for 10 hours, you can't accumulate more than 10 tokens. The bucket doesn't overflow. So you can burst 10 requests at once, never 1000.

---

**What "drip" means in Leaky Bucket:**
Leaky Bucket is the opposite — imagine the bucket has a small hole at the bottom. Requests come IN at any speed, but they EXIT at a fixed drip rate — one by one, no matter how many arrived.

```
You send 10 requests all at once → all 10 go INTO the bucket
But they exit slowly at fixed speed:
  req1 processed at second 1
  req2 processed at second 2
  req3 processed at second 3  ...and so on
```

Even if you send 10 requests at the same millisecond, they get processed at a fixed pace — no bursting allowed, output is always smooth and steady.

---

**Summary — when to use which:**

| | Token Bucket | Leaky Bucket |
|---|---|---|
| Idle user | Accumulates tokens over time | Nothing changes |
| Sudden burst | Allowed (up to max) | Not allowed — forced slow drip |
| Good for | APIs with occasional spikes (normal user behavior) | Smooth steady traffic (video uploads, billing) |
| Real-world use | AWS API Gateway, Stripe | Traffic shaping, S3 upload throttle |

---


# PAGE 4 — Decision Framework

## How to Think Through This in an Interview

```
1. DATA SHAPE
   ├── Counters (integers) + timestamps
   ├── Access pattern: READ + WRITE on every single request (hot path)
   └── → Redis (in-memory, <1 ms, atomic operations)

2. CONSISTENCY vs AVAILABILITY
   ├── Slight over-limit is tolerable (CAP = AP)
   ├── Race condition must be prevented (2 instances both see "1 token" → both allow)
   └── → Lua script in Redis (atomic, single-threaded Redis execution)

3. ACCESS PATTERN
   ├── Key-value: rate_limit:{user}:{endpoint} → {tokens, last_refill}
   ├── Write-heavy (every request writes)
   └── → Redis HASH, not SQL DB

4. SCALE & LATENCY
   ├── 1M rps → multiple API Gateway instances needed
   ├── All instances must share same counter → centralized Redis cluster
   └── → Redis Cluster (consistent hashing per user_id)

5. TEAM & OPERATIONAL MATURITY
   ├── Policy changes: Postgres + Redis write-through cache
   └── → Decouple policy storage (SQL, CRUD-friendly) from hot state (Redis)
```

WHY REDIS (NOT A DATABASE) FOR COUNTERS? (Beginner Explanation)
  A MySQL database is like a filing cabinet in the basement — great for permanent records,
  but slow to retrieve: typically 10-50ms per read/write under load.
  Redis is like a sticky note on the fridge — you glance at it and update it in under 1 millisecond
  because everything lives entirely in memory.
  At 1 million requests per second, you need 1 million counter reads and writes per second.
  Routing that to a database adds a 10-50ms penalty on every single request — the rate limiter
  itself becomes the bottleneck it was meant to protect against.
  Redis keeps all counter state in RAM. Reads and writes land in under 1ms.
  That's why every production rate limiter uses Redis for hot counter state, not a database.

---

# PAGE 6 — Algorithm Deep Dives

## Algorithm Comparison (Know This for "What Else Did You Consider?")

| Algorithm | How it works | Flaw | Use when |
|---|---|---|---|
| Fixed Window | Reset counter every 60s | Boundary spike — 199 req in 2 sec at window edge | Internal microservice calls only |
| Sliding Window Log | Store every request timestamp in Redis ZSET, count last 60s | Memory: 100M users × 100 req = 10B entries | Low-traffic, accuracy-critical (fraud, login) |
| Sliding Window Counter | Weighted blend of last two window counters | Approximation — assumes uniform traffic | Good balance if burst support not needed |
| Leaky Bucket | Requests drain from a queue at fixed rate | No burst support — smooth output only | Traffic shaping, video upload throttle |
| **Token Bucket ★** | **Bucket refills at fixed rate; burst up to capacity** | **None for API use cases** | **Production APIs — this is the answer** |

---

## Algorithm 4: Token Bucket ★ (RECOMMENDED)

WHY TOKEN BUCKET EXISTS? (In-Depth Explanation)

**The physical model — a bucket with a tap dripping coins:**

```
         TAP (drips 10 coins/sec)
              │
              ▼
    ┌─────────────────┐  ← max capacity = 100 coins
    │ ● ● ● ● ● ● ● ● │
    │ ● ● ● ● ● ● ● ● │  ← current coins = 80
    │                 │
    └────────┬────────┘
             │ each request takes 1 coin
             ▼
         your API
```

**Knob 1 — `capacity` (max burst):**
How many coins the bucket holds = maximum requests a user can fire all at once.
```
capacity = 100:
  User idle for a while → fires 100 requests simultaneously → all 100 pass
  101st request → 429, bucket empty
  Does NOT affect how fast the bucket refills
```

**Knob 2 — `refill_rate` (sustained throughput):**
How fast coins drip back in = maximum long-term average rate.
```
refill_rate = 10/sec:
  After emptying the bucket with 100 requests:
    1 sec later  → 10 coins back → can fire 10 more
    10 sec later → 100 coins back → fully refilled
  Maximum sustained rate over time = 10 req/sec, regardless of bursting
```

**The two knobs map directly to business requirements:**

| Business requirement | Token Bucket setting |
|---|---|
| Free tier: max 10 req/sec sustained, burst up to 50 | `refill_rate=10, capacity=50` |
| Premium: 100 req/sec, burst up to 500 | `refill_rate=100, capacity=500` |
| OTP endpoint: max 3 attempts per minute, no burst | `refill_rate=0.05, capacity=3` |

**Why "no midnight reset to game" — advantage over Fixed Window:**
```
Fixed Window abuse (predictable boundary):
  User fires 100 req at 11:59:59 → allowed (Window A, counter=100)
  User fires 100 req at 12:00:00 → allowed (Window B resets to 0)
  Result: 200 requests in 2 seconds

Token Bucket (no reset, continuous refill):
  User fires 100 req at 11:59:59 → allowed, bucket now = 0
  User fires 100 req at 12:00:00 → only 10 pass (1 sec × 10/sec = 10 coins refilled)
  No magic moment to time — the boundary is unpredictable by design
```

**Redis stores just 2 values per user (memory efficient):**
```
rate_limit:user123
  tokens      = 80           ← current coin count
  last_refill = 1706270445   ← unix timestamp of last request
```
Refill is calculated lazily on each request using `elapsed = now - last_refill`.
No cron jobs, no scheduled resets — just math on every incoming request.

```
BUCKET STATE  (capacity=100, refill_rate=10 tokens/sec)

  t=0:   [████████████████████] 100 tokens  ← full
  
  t=0:   100 requests arrive instantly
         [                    ]   0 tokens  ← all 100 allowed (burst!)
  
  t=5s:  Refill: 5 × 10 = 50 tokens
         [██████████          ]  50 tokens
  
  t=5s:  50 more requests
         [                    ]   0 tokens  ← all 50 allowed
  
  t=1s:  Only 1 token refilled (10/sec)
         [█                   ]   1 token
         1 request → allowed, 2nd → 429

KEY INSIGHT: capacity = max burst  |  refill_rate = sustained throughput

Redis state (HASH per user+endpoint):
  rate_limit:user123:/api/users
    tokens     → 95
    last_refill → 1706270445  (unix timestamp)

Lua script (ATOMIC — runs as one Redis command):
  ┌──────────────────────────────────────────────────────────┐
  │  local tokens     = redis.call('HGET', key, 'tokens')   │
  │  local last       = redis.call('HGET', key, 'last_refill')│
  │  local elapsed    = now - last                           │
  │  local refilled   = min(capacity, tokens + elapsed×rate) │
  │  if refilled >= 1 then                                   │
  │    redis.call('HMSET', key, 'tokens', refilled-1,        │
  │                             'last_refill', now)          │
  │    return 1  -- allow                                    │
  │  else return 0  -- reject                                │
  │  end                                                     │
  └──────────────────────────────────────────────────────────┘
```

- **Pick when**: Production APIs — this is the industry default
- **Avoid when**: You need perfectly smooth output rate (use Leaky Bucket for traffic shaping)
- **Real examples**: AWS API Gateway, Stripe, GitHub REST API

WHY LUA SCRIPTS FOR ATOMICITY? (Beginner Explanation)
  Picture two cashiers at the same register, both checking the till at the same moment.
  Cashier A reads "1 coin left" and pauses. Cashier B also reads "1 coin left" and pauses.
  Both decide there is enough — both give change. The till is now at -1. Race condition.
  In Redis, two API Gateway instances can both read tokens=1, both decide "allow", and both
  decrement — sending two requests through on a 1-token budget.
  A Lua script runs entirely inside Redis as one atomic command: nothing else can
  read or write between the token check and the decrement. No locks, no deadlocks —
  just a single Redis roundtrip that is guaranteed to be race-free.

---

---

# PAGE 7 — End-to-End Architecture Views

## Component View

WHY DISTRIBUTED COUNTERS? (Beginner Explanation)
  If each API Gateway instance kept its own counter in local memory, you'd have 40 separate
  counters — one per server. User123 could round-robin across all 40 servers and get
  100 × 40 = 4,000 requests through, even though the limit is 100/min.
  The fix: all 40 instances read from and write to ONE shared counter in a central Redis cluster.
  When any gateway checks "does user123 have budget?", they all talk to the same Redis key.
  Shared state = coordinated enforcement, regardless of which server handles each request.
  This is why the rate limiter must be centralized — per-instance counters are meaningless
  in a horizontally scaled system.

```
                                    ┌─────────────────────────────────────┐
                                    │           REDIS CLUSTER             │
                                    │                                     │
                                    │  Shard 1 (users A-M)                │
                                    │  ┌──────────────────────────────┐   │
                                    │  │ rate_limit:user123:/api/users│   │
                                    │  │   tokens=95, last_refill=... │   │
                                    │  │ policy:user123:/api/users    │   │
                                    │  │   {limit:100,refill:10,...}  │   │
                                    │  └──────────────────────────────┘   │
                                    │                                     │
                                    │  Shard 2 (users N-Z)                │
                                    └─────────────────────────────────────┘
                                                     ▲  ▲  ▲
                                                     │  │  │  (all share same Redis)
Client                                               │  │  │
  │                                    ┌─────────────┘  │  └──────────────┐
  ▼                                    │                │                 │
┌──────┐   ┌──────────────┐   ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│Client│──►│Load Balancer │──►│  API Gateway 1  │ │  API Gateway 2  │ │  API Gateway 3  │
└──────┘   └──────────────┘   │  (Rate Limiter) │ │  (Rate Limiter) │ │  (Rate Limiter) │
                               └────────┬───────┘ └────────┬───────┘ └────────┬───────┘
                                        │                   │                  │
                                        ▼                   ▼                  ▼
                               ┌────────────────────────────────────────────────────────┐
                               │                   BACKEND SERVICES                     │
                               │   UserSvc     OrderSvc     PaymentSvc     SearchSvc    │
                               └────────────────────────────────────────────────────────┘
                                                     ▲
                                                     │  (policy lookup on cache miss)
                               ┌─────────────────────┴──────────────────────────────────┐
                               │                    POLICY DATABASE                     │
                               │              (Postgres — rate_limit_rules)             │
                               └────────────────────────────────────────────────────────┘
```

---

## ER View (Database Schema)

```
┌─────────────────────────────────┐         ┌────────────────────────────────────────┐
│           clients               │         │          rate_limit_rules               │
├─────────────────────────────────┤         ├────────────────────────────────────────┤
│ client_id      UUID  PK         │         │ rule_id        UUID  PK                 │
│ api_key        VARCHAR(255) UNQ │         │ subject_type   ENUM(USER_ID,API_KEY,    │
│ tier           ENUM(FREE,       │         │                     IP,TIER,GLOBAL)     │
│                PREMIUM,         │◄────────│ subject_value  VARCHAR(255)             │
│                ENTERPRISE)      │         │                (user_123, PREMIUM,      │
│ created_at     TIMESTAMPTZ      │         │                 null for GLOBAL)        │
└─────────────────────────────────┘         │ endpoint       VARCHAR(500)             │
                                            │                ('*' = all endpoints)    │
                                            │ algorithm      ENUM(TOKEN_BUCKET,       │
                                            │                     FIXED_WINDOW,       │
                                            │                     SLIDING_WINDOW)     │
                                            │ request_limit  INT                      │
                                            │ burst_capacity INT                      │
                                            │ refill_rate    DECIMAL(10,2)            │
                                            │ enforce_by     VARCHAR(50)              │
                                            │                (USER_ID/API_KEY/        │
                                            │                 IP/TENANT)             │
                                            │ is_active      BOOLEAN DEFAULT true     │
                                            │ created_at     TIMESTAMPTZ              │
                                            │ updated_at     TIMESTAMPTZ              │
                                            ├────────────────────────────────────────┤
                                            │ INDEX(subject_type,subject_value,      │
                                            │       endpoint)                        │
                                            └────────────────────────────────────────┘

ENFORCE_BY — PER-USER vs PER-TENANT (KEY DESIGN DECISION):
┌─────────────────────────────────────────┐  ┌──────────────────────────────────────────┐
│  CASE A: enforce_by = USER_ID           │  │  CASE B: enforce_by = TENANT_ID          │
├─────────────────────────────────────────┤  ├──────────────────────────────────────────┤
│  subject_type  = TIER                   │  │  subject_type  = TIER                    │
│  subject_value = PREMIUM                │  │  subject_value = PREMIUM                 │
│  enforce_by    = USER_ID                │  │  enforce_by    = TENANT_ID               │
│  limit         = 1000 req/min           │  │  limit         = 10,000 req/min          │
├─────────────────────────────────────────┤  ├──────────────────────────────────────────┤
│  What this means:                       │  │  What this means:                        │
│  Rule applies to all premium users BUT  │  │  Rule applies to all premium tenants BUT │
│  quota is tracked PER INDIVIDUAL USER   │  │  quota is SHARED ACROSS ENTIRE TENANT    │
│                                         │  │                                          │
│  userA: 1000/min bucket                 │  │  org-ABC: 10,000/min SHARED bucket       │
│  userB: 1000/min bucket  (separate)     │  │    userA ─┐                              │
│  userC: 1000/min bucket  (separate)     │  │    userB ─┼─► same 10K bucket            │
│                                         │  │    userC ─┘                              │
│  Redis key:                             │  │  Redis key:                              │
│  rate_limit:user123:/api/users          │  │  rate_limit:tenant-ABC:/api/users        │
└─────────────────────────────────────────┘  └──────────────────────────────────────────┘
Interview line: "enforce_by decides whether each user has their own bucket
                or all users in an org drain from one shared bucket."

REDIS STRUCTURES:
┌──────────────────────────────────────────────────────────────────────────────┐
│  Token State (HASH)                                                          │
│  Key format A: rate_limit:{subject}:{endpoint}                               │
│               e.g. rate_limit:user123:/api/users                             │
│  Key format B: r1:{policy_id}:{enforce_by}:{value}:{resource}  (from image) │
│               e.g. r1:rule-5:USER_ID:user123:/api/users                      │
│  Field: tokens      → 95                                                     │
│  Field: last_refill → 1706270445                                             │
│  TTL : 3600 sec (auto-expire inactive buckets)                               │
├──────────────────────────────────────────────────────────────────────────────┤
│  Policy Cache (STRING/JSON)                                                  │
│  Key : policy:{subject}:{endpoint}                                           │
│        e.g. policy:user123:/api/users                                        │
│  Val : {"limit":100,"window":60,"refill_rate":10,                            │
│         "burst_capacity":100,"algorithm":"TOKEN_BUCKET",                     │
│         "enforce_by":"USER_ID"}                                              │
│  TTL : 3600 sec (revalidate hourly or on write-through update)               │
├──────────────────────────────────────────────────────────────────────────────┤
│  Sliding Window Log (ZSET — only if using SWL algorithm)                     │
│  Key  : rate_limit_log:{subject}                                             │
│  Score: unix timestamp   Member: request UUID                                │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## API Design (Admin & Client Endpoints)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST`   | `/api/v1/rules`                     | Admin         | Create a new rate limit rule |
| `GET`    | `/api/v1/rules`                     | Admin         | List all rules (filterable by tier, subject, endpoint) |
| `GET`    | `/api/v1/rules/{rule_id}`           | Admin         | Fetch a single rule by ID |
| `PATCH`  | `/api/v1/rules/{rule_id}`           | Admin         | Partially update a rule (limit, burst, refill) |
| `DELETE` | `/api/v1/rules/{rule_id}`           | Admin         | Soft-delete a rule (sets `is_active=false`) |
| `GET`    | `/api/v1/quota/{client_id}`         | Admin/Client  | Read current token state for a client |
| `POST`   | `/api/v1/quota/{client_id}/reset`   | Admin         | Immediately restore a client's bucket to full capacity |

---

### POST /api/v1/rules — Create Rule

```
// Request body
{
  "subject_type":   "TIER",            // USER_ID | API_KEY | IP | TIER | GLOBAL
  "subject_value":  "PREMIUM",         // null for GLOBAL
  "endpoint":       "/api/v1/orders",  // "*" = all endpoints
  "algorithm":      "TOKEN_BUCKET",
  "request_limit":  1000,
  "burst_capacity": 1000,
  "refill_rate":    16.67,
  "enforce_by":     "USER_ID"          // USER_ID | TENANT_ID
}

// Response 201 Created
{ "rule_id": "550e8400-e29b-41d4-a716-...", "is_active": true, "created_at": "2024-04-05T10:00:00Z" }
```

---

### GET /api/v1/rules — List Rules

```
GET /api/v1/rules?subject_type=TIER&subject_value=PREMIUM&page=1&page_size=20

// Response 200 OK
{
  "rules": [
    { "rule_id": "...", "subject_type": "TIER", "subject_value": "PREMIUM",
      "endpoint": "/api/v1/orders", "algorithm": "TOKEN_BUCKET",
      "request_limit": 1000, "burst_capacity": 1000, "refill_rate": 16.67,
      "enforce_by": "USER_ID", "is_active": true }
  ],
  "total": 42, "page": 1, "page_size": 20
}
```

---

### PATCH /api/v1/rules/{rule_id} — Partial Update

```
// Request — send only the fields to change
{ "request_limit": 2000, "burst_capacity": 2000 }

// Response 200 OK — full updated rule returned
// Side effect: write-through Redis SET + Pub/Sub invalidation → < 1 sec propagation to all gateways
```

---

### DELETE /api/v1/rules/{rule_id} — Delete Rule

```
DELETE /api/v1/rules/550e8400-...

// Response 204 No Content
// Side effect: is_active=false in Postgres + DEL policy:{subject}:{endpoint} in Redis
```

---

### GET /api/v1/quota/{client_id} — Current Quota Status

```
GET /api/v1/quota/user123?endpoint=/api/v1/orders

// Response 200 OK
{
  "client_id":   "user123",
  "endpoint":    "/api/v1/orders",
  "tokens":      87,
  "capacity":    1000,
  "refill_rate": 16.67,
  "last_refill": "2024-04-05T10:00:45Z",
  "reset_at":    "2024-04-05T10:01:45Z"
}
// Source: reads rate_limit:user123:/api/v1/orders HASH directly from Redis
```

---

### POST /api/v1/quota/{client_id}/reset — Reset Quota

```
// Request
{ "endpoint": "/api/v1/orders" }   // omit "endpoint" to reset all endpoints for the client

// Response 200 OK
{ "client_id": "user123", "tokens_reset_to": 1000, "reset_at": "2024-04-05T10:01:00Z" }
// Side effect: HMSET rate_limit:user123:/api/v1/orders tokens=capacity last_refill=now
```

---

> **WHY POST /api/v1/rules?** Rate limit policies must be manageable without a redeploy. This is the only correct way to support tier promotions, emergency limit changes, and onboarding new endpoints at runtime. The alternative — config files or hardcoded values — requires a deploy for every policy change.

> **WHY GET /api/v1/rules?** Support teams and dashboards need to audit which rule currently applies to a client. Without a list/get endpoint, debugging a throttling complaint requires direct DB access — a security and operational smell.

> **WHY PATCH over PUT for rule updates?** Rules have many fields; PATCH (partial update) avoids accidentally overwriting unrelated fields with a stale payload. The `PUT /rules/5` seen in the policy-update sequence diagram is a full replacement — risky if the caller omits a field like `burst_capacity`.

> **WHY DELETE /api/v1/rules/{rule_id}?** Rules need to be retired when an endpoint is deprecated or a pricing tier is discontinued. Soft delete (`is_active=false`) is preferred over hard delete so audit logs remain intact and the change can be reversed.

> **WHY GET /api/v1/quota/{client_id}?** Customer support and the client-side SDK both need real-time visibility into token state — how many requests remain, when the bucket resets. Without this endpoint, clients cannot surface a "requests remaining" UI and support cannot diagnose throttling complaints without Redis access.

> **WHY POST /api/v1/quota/{client_id}/reset?** An admin-only escape hatch for support: a client's bucket can get stuck at zero after a burst caused by a client-side bug. Resetting their quota without waiting for natural token refill is a legitimate support workflow that must not require direct Redis access.

---

## Sequence View — One Critical Write Flow (Request Allowed)

```
Client        Load Balancer     API Gateway       Redis          Policy DB    Backend
  │                │                │               │               │            │
  │──GET /api/users─►               │               │               │            │
  │                │───────────────►│               │               │            │
  │                │                │─validate JWT──►               │            │
  │                │                │                               │            │
  │                │                │  GET policy:user123:/api/users│            │
  │                │                │──────────────►│               │            │
  │                │                │◄── cache HIT ─┤               │            │
  │                │                │  {limit:100, refill:10}       │            │
  │                │                │                               │            │
  │                │                │  EVAL lua_script              │            │
  │                │                │  (key, capacity=100,          │            │
  │                │                │   refill=10, now=ts)          │            │
  │                │                │──────────────►│               │            │
  │                │                │               │ [ATOMIC]      │            │
  │                │                │               │ tokens=95+5=  │            │
  │                │                │               │ min(100,100)  │            │
  │                │                │               │ = 100-1 = 99  │            │
  │                │                │◄── return 1 ──┤               │            │
  │                │                │  (allowed)    │               │            │
  │                │                │                               │            │
  │                │                │───────────────────────────────────────────►│
  │                │                │◄─── 200 OK + {users:[...]} ───────────────┤
  │◄──200 OK ──────────────────────┤               │               │            │
  │  X-RateLimit-Limit: 100        │               │               │            │
  │  X-RateLimit-Remaining: 99     │               │               │            │
  │  X-RateLimit-Reset: 1712340788 │               │               │            │


── REJECTED FLOW (no tokens left) ──────────────────────────────────────────────

  │──GET /api/users─►               │               │               │            │
  │                │───────────────►│               │               │            │
  │                │                │  EVAL lua_script              │            │
  │                │                │──────────────►│               │            │
  │                │                │◄── return 0 ──┤               │            │
  │                │                │  (rejected)   │               │            │
  │◄── 429 ────────────────────────┤               │               │            │
  │  X-RateLimit-Limit:     100     │               │               │            │
  │  X-RateLimit-Remaining: 0       │               │               │            │
  │  X-RateLimit-Reset:  {ts}       │               │               │            │
  │  Retry-After:        1          │               │               │            │
  │  Body: {error:"rate_limit_exceeded", retry_after:1}             │            │


── CACHE MISS FLOW (policy not in Redis) ────────────────────────────────────────

  │                │                │  GET policy:user123:/api/users│            │
  │                │                │──────────────►│               │            │
  │                │                │◄── nil ───────┤               │            │
  │                │                │                               │            │
  │                │                │── SELECT limit,refill FROM rate_limit_rules─►
  │                │                │   WHERE subject_value='user123'             │
  │                │                │◄── {limit:100, refill:10} ─────────────────┤
  │                │                │                               │            │
  │                │                │  SET policy:user123 {..} EX 3600           │
  │                │                │──────────────►│               │            │
  │                │                │  (now proceed to EVAL Lua)    │            │
```

---

## Sequence View — Policy Update (Write-Through Cache)

```
Admin         Policy Svc        Policy DB         Redis          API Gateways
  │               │                │               │                │
  │─PUT /rules/5─►│               │               │                │
  │               │─UPDATE rules──►│               │                │
  │               │◄── OK ─────────┤               │                │
  │               │                                │                │
  │               │── SET policy:user123 {limit:200} EX 3600 ──────►│
  │               │── PUBLISH policy_update {rule_id: 5} ──────────►│
  │               │                                │                │
  │               │                                │  [subscribers] │
  │               │                                │  DEL local cache│
  │               │                                │  (next request  │
  │               │                                │  fetches new   │
  │               │                                │  policy)       │
  │◄── 200 OK ────┤               │               │                │
```

---

# PAGE 8 — Scaling & Optimization Techniques

## 12 Techniques (know all of these for senior interviews)

```
Technique 1 — Redis Lua scripts for atomicity
  Single atomic operation: check + decrement tokens in one EVAL call.
  Prevents race condition: two instances both reading tokens=1 → both allowing.
  Faster than separate GET + DECR (one roundtrip vs two).

Technique 2 — Policy caching in Redis
  Cache rules with 1hr TTL → 99% cache hit rate (rules rarely change).
  Reduces Policy DB load by ~100×.
  Write-through on admin updates: immediate propagation, no stale limits.

Technique 3 — Token Bucket algorithm
  Supports bursts naturally (burst_capacity = max instant requests allowed).
  Smooth refill — no sudden resets at window boundaries.
  Production-proven: AWS API Gateway, Stripe, GitHub all use Token Bucket.

Technique 4 — Distributed rate limiting via Redis Cluster
  Consistent hashing: hash(user_id) → same shard every time.
  All API Gateway instances share same Redis state → coordinated enforcement.
  Read replicas for GET (policy cache), master only for EVAL (token state writes).

Technique 5 — Multi-tier rate limiting
  Check per-user + per-IP + per-endpoint + global simultaneously.
  Enforce strictest: if ANY level exceeded → reject 429.
  Prevents: user quota abuse + IP DDoS + endpoint brute-force + cluster overload.

Technique 6 — Horizontal scaling of API Gateway
  Stateless API Gateway instances (10–100+) — no local state.
  All token state in Redis (shared) → instances are interchangeable.
  Auto-scale based on CPU/latency; Redis Cluster scales independently.

Technique 7 — Redis optimizations
  TTL on inactive buckets (3600s): auto-expire → saves memory.
  Connection pooling: each gateway maintains 50 Redis connections.
  Pipelining: batch multiple EVAL calls in one network roundtrip.

Technique 8 — Graceful degradation (circuit breaker)
  After 10 consecutive Redis failures → open circuit for 30 sec.
  Open circuit: fail OPEN (allow all, log error) — availability > strict limiting.
  Half-open after 30s: try one request → success → close circuit.

Technique 9 — 429 response headers for client backoff
  X-RateLimit-Limit:     total quota
  X-RateLimit-Remaining: tokens left
  X-RateLimit-Reset:     unix timestamp when bucket refills to 1 token
  Retry-After:           seconds to wait (ceil((1 - tokens) / refill_rate))
  Why: helps clients implement exponential backoff; avoids hammering the API.

Technique 10 — Monitoring & alerting
  Track: request count, rejection rate (% 429s), Redis latency (p50/p99),
         policy cache hit rate, per-endpoint breakdown.
  Alert: rejection rate > 5% (attack or misconfigured limit).
  Alert: Redis p99 latency > 10ms (scaling issue, investigate shards).

Technique 11 — Dynamic limit adjustment
  Auto-reduce limits if cluster at 80% capacity (protect backend).
  DDoS spike detected → temporarily stricter limits (circuit-level protection).
  Allowlist: trusted IPs / internal services bypass rate limiting entirely.

Technique 12 — Write-through cache + Redis Pub/Sub propagation
  On admin rule change:
    1. UPDATE rate_limit_rules SET limit=200 WHERE rule_id=5
    2. SET policy:user123:/api/users {limit:200,...} EX 3600   ← write-through
    3. PUBLISH policy_update {rule_id:5}
  All API Gateway instances subscribe to policy_update channel.
  On message: DEL local policy cache for that rule → next request re-fetches.
  Propagation latency: <1 sec (vs 1 hour if TTL-only approach).
```

WHY RATE LIMIT HEADERS (X-RateLimit-*)? (Beginner Explanation)
  Without headers, a client that gets a 429 has no idea what to do next. Retry in 1 second?
  10 minutes? Will it hit the same wall if it retries immediately?
  X-RateLimit-Limit tells the client their total quota so they can plan their usage.
  X-RateLimit-Remaining tells them how much budget is left so they can slow down before hitting zero.
  X-RateLimit-Reset tells them exactly when the bucket refills so they wait the right amount of time.
  Retry-After tells them the minimum safe wait so they do not hammer you with instant retries.
  Well-behaved clients — mobile SDKs, API wrappers — read these headers and back off automatically,
  turning a wall of retry storms into polite, scheduled retries.

WHY API GATEWAY NOT IN-APP RATE LIMITING? (Beginner Explanation)
  You could add rate limiting code inside each microservice (UserSvc, OrderSvc, etc.).
  But then every service re-implements the same logic with its own Redis connection and counters.
  A user could hit the 100 req/min limit on UserSvc but make unlimited calls to OrderSvc.
  The API Gateway is the single front door — every request passes through it before reaching
  any backend service. Rate limiting at the gateway means one place to enforce, one place to
  configure, and one shared Redis counter that covers all your services simultaneously.
  Think of it as one security checkpoint at the building entrance instead of a guard at every room.

---

# PAGE 9 — Capacity Estimation

## Mini-Framework

```
GIVEN:
  Traffic       = 1,000,000 req/sec
  Users         = 50,000,000 active users
  Read:Write    = every request is both a read and write (token check + update)
  Token Bucket  = HASH with 2 fields (tokens + last_refill) per user per endpoint

REDIS MEMORY:
  Token state per user per endpoint:
    key size   = ~40 bytes  (rate_limit:user123:/api/users)
    value size = ~30 bytes  (HASH: tokens=int, last_refill=int)
    overhead   = ~100 bytes (Redis per-key overhead)
    total/key  ≈ 170 bytes

  Assume avg 3 endpoints per user:
    50M users × 3 endpoints × 170 bytes = 25.5 GB Redis memory

  Policy cache per user per endpoint:
    ~200 bytes per entry × 50M × 3 = ~30 GB
    (but most inactive users' keys expire after 1 hr → actual ~5-10% hot = 1.5-3 GB)

REDIS THROUGHPUT:
  1M req/sec → 1M Lua EVAL/sec
  Redis single node: ~100K-500K commands/sec
  Need: 1M / 300K = ~4 Redis master shards minimum
  With 2× headroom → 8 shards recommended

LATENCY BUDGET (target <5 ms added):
  Policy cache lookup : 0.5 ms  (Redis GET)
  Lua script EVAL     : 1.0 ms  (Redis atomic op)
  Network roundtrip   : 1.0 ms  (co-located Redis)
  Total               : ~2.5 ms  ✓ within 5ms budget

API GATEWAY INSTANCES:
  Each handles ~50K req/sec → 1M / 50K = 20 instances minimum
  With 2× headroom → 40 instances

STORAGE (Policy DB - Postgres):
  50M users × 5 rules avg = 250M rows
  Each row ~200 bytes → 50 GB (easily fits on one Postgres primary)
  Read load: ~0 (99%+ cache hit rate)
```

---

# PAGE 9 — Interview Scripts

## Requirement Clarification Script

```
"Before designing, let me clarify a few things:

  1. What's the scale — requests per second? 1M? 100K?
  2. What do we key rate limits on — user ID, API key, IP, or all three?
  3. Should limits be configurable without a redeploy?
  4. Do different tiers (free vs premium) get different limits?
  5. Is slight over-limiting acceptable, or do we need hard exact limits?
     (This decides whether we need sliding window log vs token bucket)
  6. Should rate limiting add < 5ms latency, or is 20ms OK?
  7. What happens if Redis goes down — fail open or fail closed?"
```

---

## Trade-Off Script

```
"There are two main trade-offs I want to call out:

  Algorithm choice:
  ─ Sliding Window Log gives perfect accuracy but uses O(requests) memory.
    At 1M users × 100 req/min, that's 100M timestamps in Redis — not viable.
  ─ Token Bucket gives ~good accuracy, supports bursts naturally, low memory
    (just 2 integers per user), and is production-proven (AWS, Stripe, GitHub).
  ─ I'll go Token Bucket unless you need fraud-detection-level precision.

  Consistency vs Availability on Redis failure:
  ─ Fail open: allow all requests when Redis is down.
    Risk: temporary abuse window.
  ─ Fail closed: reject all with 503 when Redis is down.
    Risk: full outage for all users.
  ─ My choice: fail open with circuit breaker + alerting.
    Rate limiting is a best-effort protection; full outage is worse."
```

---

## Final Recommendation Script

```
"My recommendation:
  ─ Token Bucket algorithm with Redis Lua script for atomic check + refill.
  ─ Redis Cluster (8 shards) as shared state across all API Gateway instances.
  ─ Postgres for policy storage, Redis as write-through cache (1hr TTL).
  ─ Redis Pub/Sub for <1sec policy propagation on admin updates.
  ─ Circuit breaker: 10 failures → fail open for 30 sec → auto-recover.
  ─ 429 responses include Retry-After + X-RateLimit-Reset headers.
  ─ Multi-level limits: per-user, per-IP, per-endpoint — reject if any exceeded.

  This gives us <5ms latency, handles 1M rps, supports bursts naturally,
  and stays available even during Redis hiccups."
```

---

# PAGE 10 — Senior Trap Questions

## Q1: "How do you handle race conditions in distributed rate limiting?"

```
WEAK ANSWER: "Use locks in Redis."
  ── WHY IT'S WRONG: Distributed locks (SETNX + EXPIRE) have timeout complexity,
     deadlock risk, and add latency. Redis is already single-threaded.

STRONG ANSWER:
  "Redis is single-threaded — commands execute serially.
   The race condition is two API Gateway instances both reading tokens=1,
   both deciding to allow, and both decrementing → tokens=-1.

   The fix: Redis Lua script.
   The entire check-and-decrement runs as one atomic command inside Redis.
   No other command can interleave between the READ and the WRITE.
   No locks needed, no deadlocks, no extra latency beyond the single EVAL call."
```

---

---

## Q3: "What happens if Redis goes down?"

```
WEAK ANSWER: "Restart Redis."

STRONG ANSWER:
  "Two options — both valid, different trade-offs:

  Fail open:  Allow all requests during Redis outage.
  ── Pro: zero availability impact for users.
  ── Con: brief window of unlimited access (abuse risk).
  ── OK for: most APIs where temporary burst is acceptable.

  Fail closed: Return 503 during Redis outage.
  ── Pro: no abuse window.
  ── Con: all users blocked — availability collapses.
  ── OK for: financial APIs where over-limit is a compliance issue.

  Implementation: Circuit breaker.
  After 10 consecutive Redis timeouts → open circuit for 30 sec.
  During open: fail open (log + alert).
  After 30 sec: half-open → try one request → if success → close circuit.

  My default: fail open. Rate limiting is a best-effort protection.
  Full outage is worse than a brief permissive window."
```

---

## Q4: "How do you handle multi-region rate limiting?"

```
WEAK ANSWER: "Put Redis in one region and route everything there."

STRONG ANSWER:
  "Three options:

  Option A — Per-region limits (simplest):
    Redis cluster in each region: us-east, eu-west, ap-south.
    User gets 100 req/min per region → effectively 300 globally.
    ── OK if slight global over-limit is acceptable.
    ── No cross-region latency.

  Option B — Global Redis (strict):
    Single Redis cluster in one region.
    All API Gateways worldwide route to it.
    ── Exact global limit.
    ── +50-100ms latency for distant regions. Unacceptable for <5ms target.

  Option C — Gossip / CRDT (complex):
    Each region tracks local count.
    Periodically sync deltas across regions.
    ── Approximate global limit with low latency.
    ── Complex to implement correctly.

  My recommendation: Option A (per-region) for most cases.
  Only Option B if strict global compliance is required (fintech, healthcare)."
```

---

## Q5: "Fixed Window vs Sliding Window — explain the boundary problem."

```
"Fixed Window resets the counter at a sharp boundary.
 A user can make 100 requests at 10:00:59 (last second of window 1)
 and 100 more at 10:01:00 (first second of window 2) →
 200 requests in 2 seconds while claiming they respected 100/min.

 Visual:
   Window 1  |  Window 2
   ──────────|──────────
             |
   99 req ───┤─── 100 req  ← 199 in 2 sec!
   at :59    |   at :00

 Token Bucket has no boundary — it's a continuous refill.
 No sudden reset → no exploitable spike."
```

---

# PAGE 11 — What NOT to Say

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  TRAP PHRASE                  │  WHY IT'S WRONG                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Store counters in the DB"    │ DB can't handle 1M rps writes; adds 10-50ms ║
║ "Use GET then INCR in Redis"  │ Race condition — two threads both see 1,    ║
║                               │ both allow, tokens go to -1                 ║
║ "Use Redis SETNX for locks"   │ Lock complexity, deadlock risk, more latency║
║ "It depends" with no answer   │ Say: IF accuracy critical → Sliding Window  ║
║                               │ Log. IF production API → Token Bucket.      ║
║ "Rate limiting must be 100%   │ CAP: at 1M rps, slight over-limit is fine. ║
║  accurate"                    │ Trading strict consistency for availability  ║
║                               │ is the right call.                          ║
║ "Put Redis in every service"  │ Rate limit state must be CENTRALIZED.       ║
║                               │ Per-service Redis means no global enforcement║
║ "Fail closed is always safer" │ Full outage is often worse than brief burst.║
║                               │ Always discuss the trade-off.               ║
║ "Leaky Bucket = Token Bucket" │ Different output: leaky = smooth output;    ║
║                               │ token = burst allowed to backend instantly  ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

# PAGE 12 — Key Numbers to Memorize

```
┌─────────────────────────────────────────────────────────┐
│  Redis single node throughput  ~300K-500K ops/sec        │
│  Redis p99 latency (co-located) <1 ms                    │
│  Target added latency per req   <5 ms                    │
│  Policy cache TTL               3600 sec (1 hour)        │
│  Token state TTL (inactive)     3600 sec                 │
│  Redis pub/sub propagation      <1 sec                   │
│  Circuit breaker threshold      10 consecutive failures  │
│  Circuit breaker open duration  30 sec                   │
│  Free tier limit (typical)      100 req/min              │
│  Premium tier limit (typical)   1000 req/min             │
│  Enterprise tier (typical)      10,000 req/min           │
│  Login endpoint brute-force     10 req/min               │
│  Redis HASH memory per user     ~170 bytes               │
│  HTTP status for rate limit     429 Too Many Requests    │
│  Header for retry guidance      Retry-After: {seconds}   │
│  Header for quota total         X-RateLimit-Limit        │
│  Header for remaining           X-RateLimit-Remaining    │
│  Header for reset time          X-RateLimit-Reset        │
└─────────────────────────────────────────────────────────┘
```

---

# PAGE 13 — Whiteboard Draw Order

```
Step 1 — High-level flow (30 sec)
  Client → LB → API Gateway → Redis → Backend
  (draw boxes and arrows only)

Step 2 — Zoom into API Gateway (60 sec)
  Auth check → extract subject → policy lookup → token bucket check → forward/reject

Step 3 — Redis structures (45 sec)
  Draw two boxes:
  ┌──────────────────────┐   ┌──────────────────────┐
  │  Token State (HASH)  │   │  Policy Cache (JSON) │
  │  tokens=99           │   │  limit=100           │
  │  last_refill=ts      │   │  refill_rate=10      │
  └──────────────────────┘   └──────────────────────┘

Step 4 — Token Bucket visual (30 sec)
  Draw the bucket, show refill and drain arrows

Step 5 — Lua script (mention, don't write in full)
  "Atomic: read tokens → calculate refill → decrement → write → return allow/reject"

Step 6 — 429 response (20 sec)
  Show the 4 headers: Limit, Remaining, Reset, Retry-After

Step 7 — Scale-out (20 sec)
  Add 3 API Gateway boxes → all pointing to same Redis cluster
  "Shared state → no race conditions → horizontal scaling"
```

---

# PAGE 14 — How to Adapt This Guide for Any Company

## Fintech (e.g., Stripe, Brex, Razorpay)

```
─ Fail closed on Redis outage (over-limit = compliance/fraud risk)
─ Per-endpoint limits on /payments, /transfers (very strict: 10/min)
─ Sliding Window Log for audit trail (exact timestamps stored)
─ Allowlist for internal settlement systems (bypass limits)
─ Key concern: "Did we prove we rejected this request? Audit log."
```

## E-Commerce (e.g., Flipkart, Amazon, Shopify)

```
─ Flash sale protection: /product/{id} → 100 req/sec per IP during sale
─ Search endpoint: 30 req/min per user (expensive Elasticsearch query)
─ Checkout: 5 req/min per user (fraud signal if retrying fast)
─ Fail open (availability > strict limits; missed sale > no sale)
─ Key concern: "Don't block legitimate buyers during flash sales."
```

## Social Platform (e.g., Twitter, Instagram, LinkedIn)

```
─ Timeline fetch: 180 req/15min (Twitter's actual limit)
─ Post creation: 300 tweets/3hr per user
─ Tiered by verification: verified accounts get higher limits
─ DM sending: 1000/day (anti-spam)
─ Key concern: "Block bots without blocking power users."
```

## SaaS (e.g., Salesforce, HubSpot, Twilio)

```
─ API key-based limits (not user-based) — tenant isolation
─ Enforce-by = TENANT_ID for shared quota across org's users
─ Enterprise contracts: custom limits per tenant in DB
─ Usage metering for billing: same counter drives both rate limit + invoice
─ Key concern: "Fair usage across tenants; upsell path for heavy users."
```

---

# PAGE 15 — Common Follow-Up Questions

```
Q: How do you test your rate limiter?
A: Unit test Lua script logic. Integration test: spin up Redis in Docker,
   fire 101 requests — verify first 100 succeed and 101st returns 429.
   Load test: 1000 concurrent threads × 10 sec → measure rejection rate,
   verify no race conditions (rejection count should match exactly limit × users).

Q: How do you handle mobile clients with bad Retry-After parsing?
A: Also include reset time as ISO 8601 in the body
   ({"reset_at":"2024-04-05T10:01:28Z"}) in addition to Unix timestamp header.

Q: What if a single user ID is being used by thousands of IPs (shared API key)?
A: Multi-level limiting: per-API-key limit (high) AND per-IP limit (lower).
   Abuse through one IP hits the per-IP limit without affecting other users.

Q: How do you prevent someone from slightly under-limiting to game the system?
A: Token Bucket naturally handles this — refill is continuous, not windowed.
   There's no gaming a boundary since there is no boundary.

Q: How do you rate limit WebSocket connections?
A: Apply limit on connection establishment (HTTP upgrade) via token bucket.
   For message-level limiting inside WebSocket: track message count per
   connection in Redis, check before processing each message frame.

Q: Can you do rate limiting without Redis? What if Redis is too expensive?
A: Local in-memory limiting per instance (no Redis needed),
   but limits are per-instance not global. If you have 10 instances,
   effective global limit = 10× per-instance limit. Acceptable for
   internal APIs where rough limiting is fine. Not acceptable for
   public APIs where users can route to specific instances.

Q: How do you warm up rate limit state after a Redis restart?
A: Token buckets are lazy-initialized on first request (default = full bucket).
   That's correct behaviour — after restart, all users start with full quota.
   No warm-up needed. Policy cache refills from DB on first cache miss.
```

---

# PAGE 16 — Final Quick Revision Cheat Sheet

```
╔══════════════════════════════════════════════════════════════════════════╗
║          DISTRIBUTED RATE LIMITER — ONE-PAGE CHEAT SHEET                ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  ALGORITHM PICK:                                                         ║
║  Token Bucket → production APIs (burst + smooth refill)                  ║
║  Sliding Window Log → fraud/login (perfect accuracy, low traffic only)   ║
║  Fixed Window → internal only (boundary spike bug)                       ║
║  Leaky Bucket → outbound traffic shaping (not user-facing sync APIs)     ║
║                                                                          ║
║  ATOMICITY: Redis Lua script (EVAL). Never GET + DECR separately.        ║
║                                                                          ║
║  REDIS STATE (Token Bucket):                                             ║
║  HASH  rate_limit:{subject}:{endpoint}  {tokens, last_refill}  TTL=1hr  ║
║  JSON  policy:{subject}:{endpoint}      {limit, refill, ...}   TTL=1hr  ║
║                                                                          ║
║  FLOW (happy path):                                                      ║
║  Auth → GET policy (cache) → EVAL Lua → forward → return headers        ║
║                                                                          ║
║  429 HEADERS (must know all 4):                                          ║
║  X-RateLimit-Limit      → total quota                                    ║
║  X-RateLimit-Remaining  → left this window                               ║
║  X-RateLimit-Reset      → unix ts when quota refills                     ║
║  Retry-After            → seconds to wait                                ║
║                                                                          ║
║  POLICY PROPAGATION:                                                     ║
║  Admin update → UPDATE Postgres + SET Redis (write-through) +            ║
║  PUBLISH pub/sub → API Gateways invalidate local cache → <1 sec          ║
║                                                                          ║
║  REDIS FAILURE:                                                          ║
║  Circuit breaker (10 failures → open 30 sec) → fail OPEN (not closed)   ║
║                                                                          ║
║  MULTI-LEVEL LIMITS:                                                     ║
║  per-user + per-IP + per-endpoint + global → ANY exceeded → 429          ║
║                                                                          ║
║  SCALE (1M rps):                                                         ║
║  ~8 Redis shards  |  ~40 API Gateway instances  |  1 Postgres primary    ║
║                                                                          ║
║  KEY NUMBERS:                                                            ║
║  Redis latency <1ms | Added latency <5ms | TTL=3600s | CB=10 fails/30s  ║
║                                                                          ║
║  INTERVIEW LINE:                                                         ║
║  "Token Bucket in Redis Lua — atomic, burst-friendly, proven at AWS      ║
║   and Stripe, adds under 5ms, survives Redis failure via circuit         ║
║   breaker with fail-open."                                               ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

# PAGE 17 — LLD: Strategy Pattern Implementation (Code Round)

> **Interview context**: After HLD discussion, interviewers at product companies ask you to write running code using OOP design patterns. For rate limiter, the answer is always **Strategy Pattern** — each algorithm is a strategy, the API Gateway picks one at runtime based on config.

---

## Why Strategy Pattern?

```
RateLimiterStrategy (interface)
        ↑
 ┌──────┴──────┬──────────────┬──────────────┬───────────────┐
 │             │              │              │               │
TokenBucket  LeakyBucket  FixedWindow  SlidingWindowLog  SlidingWindowCounter
        
RateLimiterFactory.get(config) → returns the right strategy at runtime
APIGateway.handleRequest()     → calls strategy.isAllowed()
```

---

## 1. Strategy Interface
`RateLimiterStrategy` defines one method: `boolean isAllowed(String clientId)`.
All algorithm implementations are interchangeable behind this interface.

---

## 2. Config Object (loaded from Redis/Postgres)
Holds: `algorithmType`, `maxRequests`, `windowSizeSeconds`, `refillRatePerSecond`.
Loaded from DB at startup and cached in Redis — never read from DB on the hot path.

---

## 3. Token Bucket ★ (most common in interviews)

**Key interview points:**
- In production: use Redis Lua atomic script (see Section 12) instead of `synchronized`
- Burst-friendly: unused tokens accumulate up to `capacity`
- `refillRatePerSecond` controls smooth replenishment independent of burst size

---

## 4. Leaky Bucket

**Key interview point:** Use when the downstream service demands uniform traffic (e.g., a fragile 3rd-party API that charges per call). Introduces queuing latency — requests wait their turn instead of being rejected immediately. Not suitable for user-facing synchronous APIs.

---

## 5. Fixed Window Counter

**Key interview point:** Boundary spike problem — a user can send 2× the limit at window edges (last second of window A + first second of window B = 200 requests in 2 seconds on a 100/min limit). Always mention this weakness when discussing Fixed Window.

---

## 6. Sliding Window Log

**Key interview point:** Most accurate algorithm, but memory-heavy — stores one timestamp entry per request per user. At 1M rps with 100 users, that's 100M entries in Redis. Use only for low-traffic sensitive endpoints (login, password reset, OTP).

---

## 7. Sliding Window Counter

**Key interview point:** Uses a deterministic assumption that traffic is uniformly distributed within a window. Not 100% precise but memory-efficient — only 2 integers per user vs. full log. Good balance between accuracy and resource usage.

---

## 8. Factory (Runtime Strategy Selection)
`RateLimiterFactory.create(config)` reads `algorithmType` from config and returns the right strategy.
The API Gateway has zero knowledge of which algorithm is running — open/closed principle.

---

## 9. API Gateway (Enforcement Point)
`handleRequest(clientId, endpoint)` flow: authenticate → `strategy.isAllowed(clientId)` → forward or 429.
The rate limiter is a single call; all algorithm complexity is hidden behind the strategy.

---

## 11. Interview Script for Code Round

```
"I'll implement this using the Strategy Pattern because the algorithm
 is a runtime decision driven by config — that's the exact problem
 the pattern solves.

 The RateLimiterStrategy interface defines isAllowed(clientId).
 Each algorithm — Token Bucket, Leaky Bucket, etc. — is a concrete strategy.
 RateLimiterFactory reads the config from Redis and returns the right strategy.
 APIGateway calls the strategy; it has no knowledge of which algorithm is running.

 For production, the per-client state in each strategy moves into Redis,
 and the isAllowed logic becomes an atomic Lua script to avoid race conditions.
 The strategy objects become stateless, and Redis holds all the mutable state."
```

---

## 12. Production Upgrade: Redis Lua (Token Bucket)

```lua
-- KEYS[1] = "rate_limit:{clientId}:{endpoint}"
-- ARGV[1] = capacity, ARGV[2] = refillRatePerSecond, ARGV[3] = now (ms)
local key       = KEYS[1]
local capacity  = tonumber(ARGV[1])
local refill    = tonumber(ARGV[2])
local now       = tonumber(ARGV[3])

local state     = redis.call("HMGET", key, "tokens", "last_refill")
local tokens    = tonumber(state[1]) or capacity
local lastRefill= tonumber(state[2]) or now

local elapsed   = (now - lastRefill) / 1000.0
tokens = math.min(capacity, tokens + elapsed * refill)

if tokens >= 1 then
    tokens = tokens - 1
    redis.call("HMSET", key, "tokens", tokens, "last_refill", now)
    redis.call("EXPIRE", key, 3600)
    return 1   -- allowed
else
    redis.call("HMSET", key, "tokens", tokens, "last_refill", now)
    return 0   -- denied → 429
end
```

**Why Lua?** Redis executes Lua atomically — no race between GET and SET. This replaces `synchronized` in the Java strategy and handles all replicas correctly.

---

## KEY PATTERNS REFERENCED IN THIS DESIGN

> **For the 2-year developer:** These are the hidden concepts that make this design work. Each one has a dedicated deep-dive file. When asked "why did you choose X?" in your interview — these are the reasons.

### B-Tree vs LSM Tree (Why Redis, Not MySQL, for Counters)
**Why it matters here:** Redis skip-list is write-optimized — each INCR/INCRBY is a pure in-memory write with zero I/O. If you used MySQL B-tree for rate limit counters, every single request would trigger a B-tree page write, causing page splits at high throughput. Redis wins because counter storage is 100% writes with no range scans needed.
**Deep dive:** `../../BTree_vs_LSM_Tree_MySQL_vs_Cassandra_RocksDB.md`

### Heartbeat Detection
**Why it matters here:** Redis Sentinel uses heartbeats to detect primary failure and trigger failover. Timeout too short (e.g., 1s) causes false failovers during GC pauses — your rate limiter resets all counters. Timeout too long (e.g., 30s) means 30 seconds of broken rate limiting after a real failure. Tuning this threshold is a real interview discussion point.
**Deep dive:** `../../Heartbeat_Detection_Dead_vs_Slow_Node.md`

### CAP Theorem
**Why it matters here:** Rate limiter is CP — during a Redis partition, the correct behavior is fail-closed (reject requests) rather than allow unlimited traffic that could overcharge customers or overwhelm downstream services. Correctness over availability when billing-sensitive rate limits are involved.
**Deep dive:** `../../CAP_Theorem_Applied_What_Actually_Breaks.md`

### [Cache Eviction — LRU, LFU, TTL](../../Cache_Eviction_LRU_LFU_TTL_Redis_Policies.md)
**Why this system uses it:** The rate limiter stores counters in Redis — one key per user per window. Redis `maxmemory-policy` determines what happens when memory fills up. Use `volatile-ttl`: rate limit counters all have TTL set (window expiry), so `volatile-ttl` evicts the key with the smallest remaining TTL first — counters about to expire anyway. Never use `allkeys-lru` here: it might evict an active user's counter mid-window, resetting their count to zero and allowing requests that should be blocked.

### [AWS API Gateway — REST vs HTTP vs WebSocket](../../../aws/22.api-gateway-rest-http-websocket-architect-interview.md)
**Why this system uses it:** API Gateway has rate limiting built-in as Usage Plans — per-API-key throttle rate + burst + daily quota. This is the managed alternative to building a custom Redis token bucket. For a SaaS API platform, API GW Usage Plans give you per-client rate limiting without writing any code. Custom Redis rate limiter is needed when: (1) cross-API-GW throttling, (2) user-level limits (not API-key-level), (3) cost at very high volume (API GW charges per request).
