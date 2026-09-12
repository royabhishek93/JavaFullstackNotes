# TinyURL System Design — Architect's Complete Interview Guide
> **Voice:** First-person, 15 YOE architect. Speak this. Think out loud. This is how a principal engineer runs the room.

---

## HOW TO USE THIS GUIDE

**Tonight (2 hours):** Read Parts 1–5 end-to-end. Draw each ASCII diagram by hand.

**Morning-of (30 min):** Read Parts 11 (trade-offs), 13 (senior traps), 14 (cheat sheet) only.

**During the interview:** Parts 3, 5, and 7 are your anchor points. If you lose the thread, say: *"Let me back up to the redirect path — that's the core of this design"* and return to Part 3.

**Opening line to memorize:**
> "Before I draw anything, I want to ask four questions — because the answers will completely change the design."

---

## PART 1 — THE PROBLEM SCENARIO

*"Imagine you're a senior engineer at a mid-size fintech. The marketing team comes to you and says: 'We're sending 50 million SMS notifications next week for a product launch. The URLs are 180 characters long. Half our users have dumb phones with SMS character limits.' That's why URL shorteners exist — they're not a toy problem. They're a latency, cost, and UX problem."*

### Requirements Gathering — The Dialogue

Every question you ask reveals a constraint. Here's what I ask and why:

**Q1: Custom aliases — allowed or auto-generated only?**
> *"This determines whether I need a uniqueness check at creation time or can trust pre-generated keys. Custom aliases add a conflict resolution path."*

**Q2: Click analytics — counts only, or device + geo?**
> *"Analytics changes the write path completely. If I need it, I'm adding Kafka and ClickHouse. If not, I skip that entire subsystem."*

**Q3: URL expiration — yes/no, and what's the default TTL?**
> *"Expiry determines cache TTL strategy. If URLs expire in 24 hours, my Redis TTL logic is completely different than if they last 90 days."*

**Q4: Scale — DAU and total URL count?**
> *"This tells me whether I need sharding, whether a single Redis node is enough, whether KGS needs two instances or ten."*

**Assume the interviewer says:**
- 100M DAU
- 1B total URLs stored
- Custom alias is a premium feature
- Default expiry: 90 days
- Analytics: out of scope initially

```text
┌─────────────────────────────────────────────────────────┐
│ FUNCTIONAL REQUIREMENTS                                  │
├─────────────────────────────────────────────────────────┤
│ • POST /shorten   → return short URL                    │
│ • GET /{code}     → 302 redirect to original URL        │
│ • Custom alias    → premium users only                  │
│ • URL expiry      → default 90 days, custom for premium │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ NON-FUNCTIONAL REQUIREMENTS                             │
├─────────────────────────────────────────────────────────┤
│ • Redirect latency : p99 < 10ms (cached)               │
│                      p99 < 100ms (cache miss)           │
│ • Creation latency : p95 < 200ms                        │
│ • Availability     : 99.99%                             │
│ • No duplicate codes — ever                             │
│ • Eventual consistency acceptable (tiny creation lag)   │
└─────────────────────────────────────────────────────────┘
```

*"One thing I want to state early: this system is the most read-skewed design I know. Every URL is created once and clicked potentially thousands of times. My read-to-write ratio is 100:1. That single observation shapes every caching, scaling, and database decision I'll make."*

---

## PART 2 — CAPACITY MATH

*"I always estimate before I draw. Not because the numbers are exact — they never are — but because they tell me where the bottlenecks are before I've committed to an architecture."*

```text
┌────────────────────────────────────────────────────────────────┐
│ WRITE PATH (URL creation)                                       │
├────────────────────────────────────────────────────────────────┤
│ 100M DAU × 1% create a URL/day = 1M creations/day             │
│ 1M / 86,400 sec = ~12 writes/sec (avg)                        │
│ Peak (10× avg)  = ~120 writes/sec                             │
│ → Trivial. Any single DB primary handles this easily.          │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ READ PATH (redirects)                                           │
├────────────────────────────────────────────────────────────────┤
│ 1M new URLs/day × avg 100 clicks each = 100M redirects/day    │
│ 100M / 86,400 = ~1,200 redirects/sec (avg)                    │
│ Peak (5× avg)  = ~6,000 redirects/sec                         │
│ → Redis handles this. Need cache to stay under 10ms.           │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ STORAGE                                                         │
├────────────────────────────────────────────────────────────────┤
│ 1B URLs × 500 bytes avg row size = 500 GB                      │
│ → Fits comfortably in a sharded SQL cluster.                   │
│ → No need for distributed file storage.                        │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ SHORT CODE SPACE                                                │
├────────────────────────────────────────────────────────────────┤
│ Base62, 7 chars = 62^7 = 3.5 trillion unique codes            │
│ Need: 1 billion. Have: 3,500× more than needed.               │
│ → 7-char Base62 is sufficient for any realistic scale.         │
└────────────────────────────────────────────────────────────────┘
```

*"So my reads at 6,000/sec need caching. My writes at 120/sec are almost a rounding error. Storage at 500GB is SQL-friendly. And my code space gives me 3,500× headroom. That's my operating envelope."*

---

## PART 3 — BIG PICTURE ARCHITECTURE

*"Here's what I draw first. I call this the 'two-path diagram'. The write path is on the left, the read path is on the right. Every URL shortener is really just these two paths."*

```text
                         ┌─────────────────────┐
                         │   Client             │
                         │ (browser / mobile)   │
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │   CDN (optional)     │
                         │  edge cache for      │
                         │  extremely hot URLs  │
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │   Load Balancer (L7) │
                         │   routes by path     │
                         └───┬──────────────┬───┘
                             │              │
              POST /v1/urls  │              │  GET /{code}
                             │              │
              ┌──────────────▼──┐      ┌───▼──────────────┐
              │  Create Service  │      │  Redirect Service │
              │  (3 instances)   │      │  (6-8 instances)  │
              │                  │      │                   │
              │ 1. get key (KGS) │      │ 1. Redis lookup   │
              │ 2. DB INSERT     │      │ 2. HIT → 302      │
              │ 3. Cache SET     │      │ 3. MISS → DB read │
              │ 4. return URL    │      │    → Cache write  │
              └────────┬─────────┘      │    → 302          │
                       │                └───────┬───────────┘
                       │                        │
              ┌────────▼────────────────────────▼────────┐
              │                                           │
     ┌────────▼────────┐                      ┌──────────▼───────┐
     │   URL Database   │                      │   Redis Cache    │
     │  (MySQL Primary  │◄─ replication ──────►│  short → long    │
     │  + 2 Replicas)   │                      │  LRU, TTL-aware  │
     └────────┬─────────┘                      └──────────────────┘
              │
     ┌────────▼─────────┐     ┌─────────────────┐
     │   KGS            │     │   Expiry Cron    │
     │ (KGS-1, KGS-2)   │     │   (nightly       │
     │  pre-gen keys     │     │   DELETE expired)│
     └──────────────────┘     └─────────────────┘
```

*"Two things to notice. First — I've already split this into a Create Service and a Redirect Service. They have completely different load profiles and I don't want to be forced to scale them together. The Redirect Service might need 8 instances during a viral campaign. The Create Service doesn't care. Second — the Redirect Service goes to Redis first, always. The DB is the fallback, not the primary source of truth for reads."*

### Cross-Questions After This Diagram

**"Why not put the CDN in front of the write path too?"**
> *"CDN is for cacheable, idempotent, GET-style content. URL creation is a POST with side effects — it writes to the DB and KGS. CDNs don't cache POST requests or handle write-path logic. It belongs only on the redirect path where we're serving the same short→long mapping repeatedly."*

**"How does the Load Balancer know which service to route to?"**
> *"L7 load balancer routes based on the HTTP method and path. `POST /v1/urls` goes to the Create Service cluster. `GET /{code}` goes to the Redirect Service cluster. Nginx or AWS ALB handles this in 10 lines of config."*

**"What happens if Kafka goes down?"** *(if analytics is in scope)*
> *"Redirects continue unaffected — Kafka is on the analytics side, not the critical redirect path. Click events buffer in the application's memory briefly, then we fail-open: log to disk, forward when Kafka recovers. We never block a 302 for analytics."*

**"Why two separate services instead of one?"**
> *"If they're in the same service, I'm forced to scale creation and redirect capacity together. But redirect traffic can be 10× higher during a viral event while creation stays flat. Separate services means I can give the Redirect Service 8 pods and the Create Service 2 pods — and change that ratio without redeploying anything. It's separation of concerns at the infrastructure level."*

**"Where do rate limits live?"**
> *"At the Load Balancer or an API Gateway in front of both services. I rate-limit by API key on the creation path (prevent spam) and by IP on the redirect path (prevent scraping). Redis stores the counters with sliding window TTLs."*

**"How do you handle a cold start with an empty Redis cache?"**
> *"Two mechanisms. First, the Create Service writes to Redis immediately on URL creation (write-through), so most recent URLs are already warm. Second, on a full cache restart, the first request for each URL takes an 80ms DB hit and warms the cache. Given the 80/20 rule — 20% of URLs get 80% of traffic — the cache self-heats within minutes of a restart. I'd monitor cache hit rate and alert if it stays below 60% for more than 10 minutes."*

---

## PART 4 — API DESIGN

*"I design APIs from the consumer's perspective first, then work backward to server constraints. What does the client need? Then what does the server need to enforce?"*

### Endpoints

```text
┌──────────────────────────────────────────────────────────────────┐
│ POST /v1/urls                                                     │
│ Content-Type: application/json                                    │
│ Authorization: Bearer {api_key}                                   │
│ Idempotency-Key: {client-generated UUID}                          │
├──────────────────────────────────────────────────────────────────┤
│ Request:                                                          │
│ {                                                                 │
│   "long_url": "https://example.com/very/long/path?query=value",  │
│   "custom_alias": "my-promo",   // optional, premium only         │
│   "expires_in_days": 30         // optional, default 90           │
│ }                                                                 │
├──────────────────────────────────────────────────────────────────┤
│ 201 Created:                                                      │
│ {                                                                 │
│   "short_url": "https://sho.rt/bK9pQ3x",                        │
│   "short_code": "bK9pQ3x",                                       │
│   "expires_at": "2024-09-15T00:00:00Z",                         │
│   "created_at": "2024-06-15T10:30:00Z"                          │
│ }                                                                 │
│ 400 Bad Request     — invalid URL format                         │
│ 409 Conflict        — custom alias already taken                 │
│ 422 Unprocessable   — long_url points to malware (Safe Browsing) │
│ 503 Service Unavail — KGS down, creation paused                  │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ GET /{code}                                                       │
├──────────────────────────────────────────────────────────────────┤
│ 302 Found           → Location: {long_url}                       │
│   X-Cache: HIT | MISS                                            │
│ 404 Not Found       — code never existed                         │
│ 410 Gone            — existed but expired                        │
│ 429 Too Many Req    — IP rate limit exceeded                     │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ GET /v1/urls/{code}       — fetch URL metadata                   │
│ DELETE /v1/urls/{code}    — deactivate URL (owner only)          │
│ GET /v1/urls/{code}/stats — click analytics (if in scope)        │
└──────────────────────────────────────────────────────────────────┘
```

*"Two things I always add that interviewers notice. First — the `Idempotency-Key` header on POST. If the client retries because of a timeout, I don't want to create two URLs. The server caches the response keyed by the idempotency key for 24 hours. Same request, same response. Second — the distinction between 404 and 410. 404 means the code never existed — could be a typo. 410 means it existed and was deleted or expired — the client should stop retrying. They mean completely different things."*

### Technology Comparison: REST vs gRPC (Internal Services)

| | REST | gRPC |
|---|---|---|
| **Why REST** | Public API, browser-compatible, human-readable, easy to debug with curl | — |
| **Why gRPC** | Internal services, typed contracts, protobuf ~10× smaller payload, streaming support | — |
| **Where I'd use REST** | `POST /v1/urls` and `GET /{code}` — external clients | — |
| **Where I'd use gRPC** | Create Service → KGS internal calls, Create Service → DB service layer | — |
| **Real example** | Twitter's public API is REST | Netflix internal service mesh uses gRPC |

*"For this design, I'd use REST externally and gRPC internally between the Create Service and KGS. External clients need REST — they're browsers, SDKs in every language, cURL scripts. Internal service-to-service calls benefit from gRPC's typed contracts and lower overhead."*

### Cross-Questions

**"Why 302 and not 301?"**
> *"301 is permanent — the browser caches it forever and bypasses our server on future visits. We never see those clicks again. We lose analytics, we can't deactivate that URL, we can't redirect the redirect. 302 is temporary — every visit comes through us. Yes, it adds ~5ms per hit versus the browser cache going direct, but we maintain control. For analytics and URL management, control matters more than shaving 5ms off repeat visits."*

**"What does the API return if the database is down?"**
> *"For creation: HTTP 503 with a `Retry-After: 30` header. Client knows to retry in 30 seconds. For redirect: the Redirect Service tries Redis first — if the URL is cached, we still serve the 302 even with the DB down. Only a cache miss during a DB outage returns 503. So most redirects survive a DB outage."*

**"How do you handle custom aliases that collide with API paths?"**
> *"Blocklist. Maintain a set of reserved paths: `api`, `v1`, `v2`, `admin`, `health`, `static`, etc. Validate at creation time — if the alias matches a reserved word, return 400 Bad Request with a clear message: 'That alias is reserved.' Store the blocklist in Redis for O(1) lookup."*

**"Should redirect be a separate service from creation? Why?"**
> *"Yes — I already split them. The reason: different scaling requirements, different failure modes, different SLOs. The Redirect Service needs ultra-low latency and near-zero downtime. The Create Service can tolerate 200ms creation latency. Separate services means separate deployment, separate alerting, separate capacity planning."*

**"How do you version the API without breaking existing short URLs?"**
> *"URI versioning: `/v1/urls`. Existing short codes live at `/{code}` — unversioned, as they should be. The versioning applies to the management API (create, delete, stats), not the redirect path. When I release v2 with new features, I keep v1 running in parallel and deprecate it with a sunset header: `Sunset: 2025-01-01`."*

---

## PART 5 — ID GENERATION DEEP DIVE

*"This is where most candidates stumble. I've interviewed 200+ engineers on system design, and the ID generation section separates the candidates who've thought carefully from the ones who memorized a template. Let me walk through five approaches in order — each one is a direct response to the previous one's failure mode."*

### Approach 1 — MD5/SHA1 Truncation

```text
long_url ──► MD5() ──► "91c0a3f8b2d4e6..." ──► take first 7 chars ──► "91c0a3f"
```

*"The instinct makes sense: hash the input, take a prefix. But MD5 was designed for 128-bit collision resistance on the full hash — when you truncate to 7 characters (42 bits), the birthday paradox kicks in hard. At 1 billion URLs, you'd see frequent collisions where two different long URLs produce the same 7-char prefix. Resolving each collision means re-hashing with a salt, checking the DB, potentially looping. Latency becomes unpredictable. I'd only use this under 1 million URLs."*

### Approach 2 — Single In-Memory Counter

```text
counter = 0
on each creation: counter += 1; encode to Base62

1        → "0000001"
62       → "0000010"
1,000,000 → "4c92"
```

*"Clean, fast, no collisions by definition. But the counter lives in server memory. Scale to two servers, both start at zero, and you get duplicates immediately. Single-server only."*

### Approach 3 — Redis Global Counter

```text
Client ──► URL Service ──► Redis INCR global_counter ──► N (atomic)
                        ──► encode N to Base62 ──► short_code
                        ──► DB INSERT
```

*"Redis INCR is atomic — only one server gets each integer. This works for medium scale. Two failure modes to acknowledge: Redis becomes a SPOF (mitigate with Sentinel), and at very high throughput every creation pays a network round-trip to Redis (mitigate with pipelining). Valid choice for most real-world scale. But there's a cleaner solution."*

### Approach 4 — Zookeeper Range Allocation

```text
┌─────────────────────────────────────────────────────────────┐
│ Zookeeper allocates non-overlapping ranges at startup:       │
│                                                              │
│   Server-1 ──► range [1 .. 1,000,000]                       │
│   Server-2 ──► range [1,000,001 .. 2,000,000]               │
│   Server-3 ──► range [2,000,001 .. 3,000,000]               │
│                                                              │
│ Each server increments its local counter:                    │
│   Server-1: 1, 2, 3, 4 ...  ← zero network hops            │
│   Server-2: 1,000,001, 1,000,002 ...                        │
│                                                              │
│ When Server-1 exhausts its range:                            │
│   ──► contact Zookeeper ──► next range [3,000,001 ..]       │
│   ──► resume local increments                                │
└─────────────────────────────────────────────────────────────┘

Range lifetime at 120 writes/sec = 1,000,000 / 120 = ~138 min
Zookeeper is contacted roughly every 2 hours per server.
```

*"Zookeeper is only contacted when a range exhausts — roughly every 2 hours per server. Between those contacts, every ID is generated locally with zero network I/O. Zookeeper runs as a 3-node quorum — no SPOF. This is what I'd use in production for Approach 4."*

#### Zookeeper Node Types — Interviewers Love This Detail

```text
┌──────────────────────────────────────────────────────────────┐
│ EPHEMERAL NODE                                                │
│ • Lives only as long as the server holding the session       │
│ • Auto-deleted when heartbeat times out                       │
│ • Use: service registration, leader election                  │
│                                                              │
│ PERSISTENT NODE                                               │
│ • Survives server crashes, Zookeeper restarts                │
│ • Must be explicitly deleted                                  │
│ • Use: storing the counter value ← must survive crashes      │
├──────────────────────────────────────────────────────────────┤
│ In URL shortener:                                            │
│   • Each server ──► registers EPHEMERAL node ──► gets ID    │
│   • Counter state ──► stored in PERSISTENT node             │
│   • Server restart: re-registers, resumes from saved state   │
└──────────────────────────────────────────────────────────────┘
```

### Approach 4b — Snowflake ID (Recommended for Production)

```text
┌────────────────────────────────────────────────────────────────┐
│ SNOWFLAKE ID — 64-bit structure:                               │
├────────┬──────────────────┬────────────┬───────────────────────┤
│ 1 bit  │   41 bits        │  10 bits   │      12 bits          │
│  sign  │ timestamp (ms)   │ worker ID  │ per-ms sequence       │
├────────┴──────────────────┴────────────┴───────────────────────┤
│ Sign     : always 0 (positive integers only)                   │
│ Timestamp: ms since custom epoch (~69 years of range)          │
│ Worker ID: assigned by Zookeeper at startup, cached            │
│ Sequence : local counter, resets every millisecond             │
│            handles 4,096 IDs per ms per server                 │
└────────────────────────────────────────────────────────────────┘

GENERATION:
  1. Server starts → registers with Zookeeper → receives workerID=123
  2. Request arrives:
     timestamp = now_ms()                    → 41 bits
     worker_id = 123                         → 10 bits (cached)
     sequence  = local_counter.incrementAndGet() → 12 bits
     snowflake = combine(timestamp, worker_id, sequence) → 64-bit int
  3. Encode 64-bit int to Base62             → 7-char short code

EXAMPLE:
  timestamp  = 1,718,000,000,000  (41 bits)
  worker_id  = 123                (10 bits)
  sequence   = 5                  (12 bits)
  snowflake  = 7,624,839,593,475  (64-bit)
  Base62     = "bK9pQ3x"          (7 chars)
```

*"Why is this better than plain Zookeeper ranges? Two reasons. One — Zookeeper is contacted once at startup, not every 2 hours. After that, zero coordination per request. Two — even if two servers fire at the exact same millisecond, their different worker IDs guarantee uniqueness. The timestamp + workerID + sequence triple is mathematically unique without any shared state during normal operation."*

### Technology Comparison: Zookeeper Range vs Snowflake

| | Zookeeper Range | Snowflake ID |
|---|---|---|
| **Coordination frequency** | Every ~2 hours per server | Once at startup |
| **Dependency during operation** | None (local counter) | None (local generation) |
| **Uniqueness guarantee** | Range ownership | timestamp + workerID + sequence |
| **Clock dependency** | None | Yes — clock skew is a failure mode |
| **Code length** | 7 Base62 chars | 7 Base62 chars (same) |
| **Pick Zookeeper range when** | Simpler architecture, no NTP concern | — |
| **Pick Snowflake when** | Multi-region active-active, >100K writes/sec, Discord/Twitter scale | — |
| **Real example A** | TinyURL at 120 writes/sec — Zookeeper range is fine | — |
| **Real example B** | Discord (snowflake), Twitter (snowflake), Instagram (snowflake at 10K IDs/sec per server) | — |

### Approach 5 — Key Generation Service (KGS)

```text
┌───────────────────────┐      ┌───────────────────────┐
│  keys_available table  │      │  keys_used table       │
│─────────────────────── │      │───────────────────────│
│  short_code (PK)       │      │  short_code (PK)       │
│   "3xK9pQ"             │      │  assigned_at           │
│   "7mR2qW"             │      │  "2aB8mN"              │
│   "4pL5xN"             │      └───────────────────────┘
└────────────┬──────────┘
             │
             │ KGS: BEGIN TXN
             │   move key from available → used (atomic)
             │ COMMIT
             │ return key to URL Service
             ▼
┌───────────────────────┐
│  URL Service           │
│  local key buffer      │
│  [100 keys in memory]  │
│  refills from KGS      │
└───────────────────────┘
```

*"KGS pre-generates keys offline in a background batch job. URL service never hashes, never checks the DB for collision, never talks to Zookeeper — it just picks the next key from its local buffer. No collision is even possible — keys are pre-validated as unique in the DB primary key. The tradeoff: an extra service to operate and a keys database to manage. For simplicity and correctness, this is what I'd actually recommend."*

### Approach Comparison

```text
┌─────────────────────┬──────────┬──────────┬─────────┬────────────┬─────────────┐
│ Approach            │ Unique?  │ Scales?  │ Latency │ Complexity │ Use when    │
├─────────────────────┼──────────┼──────────┼─────────┼────────────┼─────────────┤
│ MD5 truncation      │ Risky    │ No       │ High    │ Low        │ < 1M URLs   │
│ Single counter      │ Yes      │ No       │ Low     │ Low        │ Single srvr │
│ Redis global counter│ Yes      │ Medium   │ Medium  │ Medium     │ Medium scale│
│ Zookeeper ranges    │ Yes      │ Yes      │ Low     │ Medium     │ Large scale │
│ KGS pre-generated   │ Yes      │ Yes      │ Low     │ Medium     │ Recommended │
│ Snowflake ID        │ Yes      │ Yes      │ Lowest  │ Medium     │ Multi-region│
└─────────────────────┴──────────┴──────────┴─────────┴────────────┴─────────────┘
```

### Cross-Questions

**"What if a server crashes mid-range? You lose up to 1M IDs. Is that OK?"**
> *"Yes. We're not using IDs sequentially for billing — they're short codes that encode to Base62. A gap in the counter sequence is invisible to the user. 'bK9pQ3x' and 'bK9pQ3y' don't need to be consecutive. Lost IDs just mean slightly reduced code space, and we have 3.5 trillion to play with. No user impact."*

**"Can you use a database auto-increment instead of Zookeeper?"**
> *"Technically yes, for medium scale. DB auto-increment is atomic and works across restarts. The problem: every URL creation now requires a write to the DB primary just to get an ID — before you even write the URL record. That's an extra write per creation, and it makes the DB primary the bottleneck for ID generation. Zookeeper range allocation amortizes that cost across 1 million IDs per contact."*

**"How would you handle a Zookeeper split-brain?"**
> *"Zookeeper uses the Zab consensus protocol — it requires a quorum (majority) of nodes to process writes. In a 5-node cluster, if more than 2 nodes are partitioned, all writes fail — no split brain is possible because the minority partition can't proceed. The URL server detects the Zookeeper write failure, serves from its local key buffer, and alerts ops. Creation degrades gracefully until quorum is restored."*

**"What if two servers are assigned the same range due to a Zookeeper bug?"**
> *"The DB primary key on `short_code` is the ultimate safety net. If two servers somehow generate the same code, the second INSERT throws a unique constraint violation. The server retries with the next code. This should never happen with correct Zookeeper usage — but defense in depth means we catch it at the DB layer regardless."*

**"Why not just use UUIDs?"**
> *"UUID is 36 characters (`550e8400-e29b-41d4-a716-446655440000`). A short URL with a 36-char code defeats the entire purpose of a URL shortener. Base62 with 7 chars gives 3.5 trillion unique values in a URL-safe, human-typeable format. UUID is the wrong tool here."*

---

## PART 6 — DATABASE SCHEMA & DESIGN

*"The schema is boring until you have to shard it. Let me show you the schema, then I'll explain the one decision that changes everything at scale: the shard key."*

### ER Diagram

```text
┌─────────────────────────────┐       ┌──────────────────────────────────┐
│ users                        │       │ short_urls                        │
│─────────────────────────────│       │──────────────────────────────────│
│ user_id     PK  BIGINT       │       │ short_code  PK  VARCHAR(10)       │
│ email       UNIQUE           │       │ long_url        TEXT              │
│ api_key     UNIQUE           │◄──────│ user_id     FK  BIGINT  (INDEX)   │
│ plan_type   ENUM             │       │ custom_alias    VARCHAR(50)(INDEX)│
│ created_at  DATETIME         │       │ expires_at      DATETIME  (INDEX) │
└─────────────────────────────┘       │ created_at      DATETIME          │
                                       │ is_active       BOOL DEFAULT true  │
                                       │ long_url_hash   CHAR(32) (INDEX)   │
                                       └──────────────────────────────────┘

┌─────────────────────────────┐       ┌──────────────────────────────────┐
│ keys_available               │       │ keys_used                         │
│─────────────────────────────│       │──────────────────────────────────│
│ short_code  PK  VARCHAR(10)  │       │ short_code  PK  VARCHAR(10)       │
└─────────────────────────────┘       │ assigned_at     DATETIME          │
                                       └──────────────────────────────────┘
```

### Index Decisions — The WHY Behind Each

```text
PRIMARY KEY (short_code)
  → O(1) redirect lookup — the most frequent operation in this system

INDEX (expires_at)
  → nightly cron: DELETE WHERE expires_at < NOW()
    without this index, the cron job does a full table scan on 1B rows

INDEX (custom_alias)
  → uniqueness check: "is 'my-promo' already taken?"
    happens on every premium URL creation

INDEX (user_id, created_at DESC)
  → "show me all URLs created by user 123, newest first"
    composite index satisfies both filter and sort in one scan

INDEX (long_url_hash)
  → deduplication: "has this long URL been shortened before?"
    MD5 of long_url stored in char(32); faster than comparing 2KB TEXT values
    OPTIONAL — only worth adding if deduplication is a product requirement
```

### Technology Comparison: MySQL vs PostgreSQL

| | MySQL (InnoDB) | PostgreSQL |
|---|---|---|
| **Replication model** | Simpler, battle-tested at hyperscale; Vitess sharding ecosystem | MVCC more sophisticated; Citus for sharding |
| **Why MySQL** | Meta, Twitter, GitHub all run MySQL at billions of rows; Vitess handles sharding transparently | — |
| **Why PostgreSQL** | JSONB for variable URL metadata, full-text search on long_url, window functions for analytics in-DB | — |
| **When PostgreSQL wins** | You need JSONB custom metadata per URL, or complex analytics stay in the same DB | — |
| **Real example A** | TinyURL main mappings table — MySQL + Vitess sharding | — |
| **Real example B** | Feature flag service with JSONB config — PostgreSQL | — |

*"For this problem, I'd use MySQL. The schema is simple, fixed, and we're doing point lookups on `short_code`. MySQL's Vitess ecosystem is the most proven path for horizontal sharding of SQL at this scale. PostgreSQL is a fine choice too — I'd reach for it if the product roadmap included storing variable metadata as JSONB per URL."*

### Sharding Strategy

*"At 500GB, sharding is optional. At 2TB, it's mandatory. The question to answer now is: what's my shard key? Because changing it later is the most expensive migration you'll ever do."*

```text
Option A: hash(short_code) % N
  ✓ Even distribution — every shard gets equal traffic
  ✓ Redirect lookup hits exactly one shard (know the code → know the shard)
  ✗ "List all URLs for user 123" scatters across all shards — requires scatter-gather

Option B: hash(user_id) % N
  ✓ "All user 123 URLs" hits one shard — locality for user queries
  ✗ Hot users cause hot shards — if a user creates 10M URLs, one shard gets hammered
  ✗ Redirect lookup requires routing table: "which shard has short_code X?"

I choose: hash(short_code) % N

Reason: redirects are 100× more frequent than user-URL listing queries.
Optimize the critical path. Accept scatter-gather for the rare admin query.
```

### Cross-Questions

**"How do you do a 'list all URLs for user X' query across shards?"**
> *"Scatter-gather: fan out the query to all N shards in parallel, collect results, merge and sort in the application layer. Expensive, but this is a dashboard query that users run rarely. I'd also maintain a secondary index in Elasticsearch or a separate user-URL mapping table if this query is frequent."*

**"What's the blast radius if one shard goes down?"**
> *"With N=10 shards, each shard holds 10% of URLs. If shard 3 goes down, 10% of redirects return 503 until replica promotion completes (~30 seconds). The other 90% are unaffected. This is acceptable given 99.99% availability — we tolerate brief partial degradation over full-system unavailability."*

**"Why MD5 the long URL for deduplication instead of a unique constraint on long_url?"**
> *"long_url is a TEXT column — can be up to 2,048 characters. MySQL can't index a TEXT column beyond 767 bytes in InnoDB with the default row format. MD5 produces a fixed 32-char hash — always indexable, always comparable in O(1). We store MD5(long_url) in a char(32) column and index that."*

**"How do you handle the custom alias namespace colliding with auto-generated codes?"**
> *"Both live in the same `short_code` primary key column. The primary key constraint prevents any collision — if a user tries to register 'bK9pQ3x' as a custom alias and that code already exists (auto-generated or previous custom), the INSERT throws a unique constraint violation and returns 409. No separate namespace needed."*

---

## PART 7 — CACHING STRATEGY

*"Caching is where this system wins or loses. The redirect path must be under 10ms at p99. That's only possible with Redis. Here's how I think about what goes in the cache and what doesn't."*

### Cache-Aside Pattern Flow

```text
Redirect Service receives: GET /bK9pQ3x

Step 1: Redis GET bK9pQ3x
        │
        ├── HIT  → long_url returned
        │          → send 302, done. (~5ms)
        │
        └── MISS → Step 2: MySQL SELECT long_url, expires_at
                            WHERE short_code = 'bK9pQ3x'
                            AND (expires_at IS NULL OR expires_at > NOW())
                   │
                   ├── Not found → 404 Not Found
                   ├── Expired   → 410 Gone (do NOT cache this)
                   │
                   └── Found → Step 3: Redis SET bK9pQ3x {long_url}
                                       EX {ttl_seconds}
                               → send 302, done. (~80ms)
```

### TTL Strategy — The Subtle Part

```text
redis_ttl = min(standard_ttl, expires_at - now())

Case 1: URL never expires (expires_at IS NULL)
  → redis_ttl = standard_ttl = 3600s (1 hour)

Case 2: URL expires in 2 hours (expires_at - now() = 7200s)
  → redis_ttl = min(3600, 7200) = 3600s ✓

Case 3: URL expires in 30 minutes (expires_at - now() = 1800s)
  → redis_ttl = min(3600, 1800) = 1800s ✓
  → Cache auto-expires before the URL does

Case 4: URL already expired (expires_at - now() < 0)
  → Do NOT cache. Return 410 immediately.
```

*"The trap most engineers fall into: set a flat 1-hour TTL for everything. A URL that expires in 10 minutes will still be in cache for up to an hour after expiry — users get a 302 to a URL that should be dead. Matching the TTL to the actual URL lifetime eliminates this entirely."*

### Cache Sizing

```text
Zipf distribution: 20% of URLs receive 80% of traffic.
Active URL set  = 200M URLs
Per-entry size  = ~200 bytes (short_code + long_url + metadata)
Hot set size    = 200M × 200B = 40GB

Redis cluster   = 3 nodes × 16GB each = 48GB usable
→ Covers the entire hot set with headroom.

At 80% cache hit rate:
  DB sees 20% of 6,000 req/sec = 1,200 req/sec
  DB read replicas handle this comfortably.
```

### Technology Comparison: Redis vs Memcached

| | Redis | Memcached |
|---|---|---|
| **Data structures** | Strings, hashes, sorted sets, lists, pub/sub | String key-value only |
| **TTL per key** | Yes, native | Yes, native |
| **Persistence** | RDB + AOF options | None |
| **Why Redis** | TTL per key (URL expiry logic), sorted sets for trending URLs, pub/sub for cache invalidation across nodes | — |
| **Why Memcached** | Marginally higher throughput for pure string get/set; simpler operations | — |
| **When Memcached wins** | Pure object cache, no TTL complexity, maximizing cache efficiency on a single machine | — |
| **Real example A** | URL shortener — Redis (TTL strategy, trending, invalidation) | — |
| **Real example B** | HTML fragment cache for a CMS — Memcached (pure speed, simplicity) | — |

### Cross-Questions

**"What happens to the Redis cache if a URL is deleted from MySQL?"**
> *"On deletion, the Create/Management service explicitly calls `DEL short_code` in Redis — don't wait for TTL expiry. If the DEL somehow fails (network blip), the URL is still gone from MySQL, so the next cache miss will return 404/410 from DB and not re-cache it. Worst case: up to 1 hour of stale serves before TTL expires. For most deletions, that's acceptable. For DMCA or abuse takedowns, we also invalidate the CDN edge cache using the CDN's purge API."*

**"Should the Redirect Service write to the cache on a miss, or should the Create Service pre-populate it?"**
> *"Both. The Create Service does write-through — when a URL is created, it immediately caches it. So the first redirect after creation is a cache hit. The Redirect Service handles population for URLs that were created before Redis warm-up (e.g., after a Redis restart). Defense in depth."*

**"How do you prevent a cache stampede when a hot URL's cache entry expires?"**
> *"Three options. (1) Probabilistic early expiration: before TTL expires, randomly refresh it early — prevents the cliff edge. (2) Redis locking: first thread to get a miss acquires a distributed lock, fetches from DB, releases lock; all other threads wait and then read from cache. (3) Background refresh: a separate process monitors TTL and refreshes before expiry. For this system, I'd use option 1 — it's simple and effective for a URL shortener's read pattern."*

**"Would you use Redis Cluster or Redis Sentinel?"**
> *"Both solve different problems. Redis Sentinel provides high availability for a single Redis instance — it monitors the primary, promotes a replica on failure. Redis Cluster provides horizontal sharding — data is distributed across multiple nodes, each owning a subset of the 16,384 hash slots. For 40GB of hot URL data, I'd use Redis Cluster — it gives both HA and horizontal scale. Sentinel alone is insufficient once data exceeds a single node's memory."*

---

## PART 8 — SEQUENCE DIAGRAMS

*"Two critical flows. I draw these to prove I understand the happy path AND the failure modes. These aren't just documentation — they're how I verify my architecture doesn't have race conditions."*

### Flow 1: Create Short URL

```text
Client          Create Service      KGS          MySQL       Redis
  │                   │               │              │           │
  │  POST /v1/urls    │               │              │           │
  │──────────────────►│               │              │           │
  │                   │ get_key()     │              │           │
  │                   │──────────────►│              │           │
  │                   │               │ BEGIN TXN    │           │
  │                   │               │ move key:    │           │
  │                   │               │ available→   │           │
  │                   │               │ used         │           │
  │                   │               │ COMMIT       │           │
  │                   │◄──────────────│              │           │
  │                   │  "bK9pQ3x"   │              │           │
  │                   │                    INSERT     │           │
  │                   │───────────────────────────── ►│           │
  │                   │                              │  SET key  │
  │                   │──────────────────────────────┼──────────►│
  │                   │                              │           │
  │◄──────────────────│                              │           │
  │  201 + short_url  │                              │           │
```

*"One important ordering question: do I write to MySQL first or Redis first? MySQL first. If MySQL succeeds but Redis fails, the URL is created and the first redirect takes a DB hit — that's a minor latency hit, not a data loss. If Redis succeeded but MySQL failed and we rolled back, we'd have a cached URL that doesn't exist in the DB — a ghost entry. Always write the source of truth first."*

### Flow 2: Redirect (Cache Hit vs Miss)

```text
Client        Redirect Service       Redis         MySQL
  │                  │                  │               │
  │  GET /bK9pQ3x   │                  │               │
  │─────────────────►│                  │               │
  │                  │  GET bK9pQ3x    │               │
  │                  │─────────────────►│               │
  │                  │                  │               │
  │   [CACHE HIT]    │◄─────────────────│               │
  │                  │  "https://..."   │               │
  │◄─────────────────│                  │               │
  │  302 + Location  │                  │               │
  │  (~5ms)          │                  │               │
  │                  │                  │               │
  │   [CACHE MISS]   │◄─────────────────│               │
  │                  │  (nil)           │               │
  │                  │                     SELECT       │
  │                  │────────────────────────────────► │
  │                  │◄────────────────────────────────│
  │                  │  "https://..."                   │
  │                  │  SET bK9pQ3x EX 3600             │
  │                  │─────────────────►│               │
  │◄─────────────────│                  │               │
  │  302 + Location  │                  │               │
  │  (~80ms)         │                  │               │
```

### Flow 3: Expired URL (410 Response)

```text
Client        Redirect Service       Redis         MySQL
  │                  │                  │               │
  │  GET /oldCode   │                  │               │
  │─────────────────►│                  │               │
  │                  │  GET oldCode    │               │
  │                  │─────────────────►│               │
  │                  │◄─────────────────│               │
  │                  │  (nil) — TTL expired             │
  │                  │                     SELECT       │
  │                  │────────────────────────────────► │
  │                  │◄────────────────────────────────│
  │                  │  expires_at < NOW()              │
  │                  │  (URL expired in DB)             │
  │◄─────────────────│                  │               │
  │   410 Gone       │                  │               │
  │   (do NOT cache) │                  │               │
```

### Cross-Questions

**"In the redirect flow, you check Redis first. What if Redis returns stale data?"**
> *"Redis can only serve stale data if we failed to delete the key on URL deletion. That's why explicit `DEL` on deletion is non-negotiable. TTL is the backstop, not the primary mechanism. For abuse/DMCA takedowns, we also have a blocklist checked before Redis that is updated in real-time."*

**"Is the Kafka publish (if analytics) before or after the 302? Why?"**
> *"After. Never block a user response for an analytics event. The 302 goes out immediately. The Kafka publish is fire-and-forget in a background thread or async queue. If Kafka is slow or down, the user still gets their redirect in 5ms. The click event might be delayed or lost, but the user experience is unaffected."*

**"In the create flow, you write MySQL then Redis. What if MySQL succeeds but Redis write fails?"**
> *"We log the error and continue. The URL is safely in MySQL — that's the source of truth. The first redirect for that URL will be a cache miss (~80ms) instead of a hit (~5ms). The Redirect Service will then populate Redis on that first miss. No data loss, minor latency impact on first hit. This is the correct behavior for cache-aside."*

---

## PART 9 — ANALYTICS PIPELINE

*"I never block a user response for an analytics write. This is a non-negotiable architectural principle. The redirect path has a p99 < 10ms SLO. No analytics system is fast enough to be on that critical path."*

### Pipeline Design

```text
                              [Redirect happens]
                                     │
                    302 sent ◄───────┤
                                     │
                            fire-and-forget
                                     │
                                     ▼
                           ┌────────────────┐
                           │  Kafka Topic   │
                           │  "url-clicks"  │
                           │  partitioned   │
                           │  by short_code │
                           └───────┬────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
             Consumer-1     Consumer-2     Consumer-3
             (partition 0)  (partition 1)  (partition 2)
                    │
                    ▼
             ┌────────────────┐
             │   ClickHouse   │
             │  clicks table  │
             │  (columnar,    │
             │   partitioned  │
             │   by day)      │
             └───────┬────────┘
                     │
                     ▼
              Analytics API / Dashboard
```

### Technology Comparison 1: Kafka vs SQS/RabbitMQ

| | Apache Kafka | AWS SQS / RabbitMQ |
|---|---|---|
| **Storage model** | Log-based — messages persist, can replay | Queue-based — messages deleted on consume |
| **Consumer model** | Consumer groups — multiple consumers, each gets all messages | Competing consumers — each message consumed once |
| **Throughput** | 100K–1M msgs/sec per partition | ~10K msgs/sec per queue |
| **Why Kafka** | Replay click events for analytics reprocessing; partitioning by short_code groups a URL's clicks; 115K events/sec throughput | — |
| **Why SQS** | Zero ops, serverless, AWS-native, cheaper at low volume | — |
| **When SQS wins** | Early-stage, < 10K events/sec, ops simplicity matters, no replay needed | — |
| **Real example A** | TinyURL at 115K clicks/sec → Kafka, partitioned by short_code | — |
| **Real example B** | Notification service at 1K/sec → SQS (managed, zero ops) | — |

### Technology Comparison 2: ClickHouse vs Elasticsearch

| | ClickHouse | Elasticsearch |
|---|---|---|
| **Storage model** | Columnar OLAP — optimized for aggregation | Row-oriented — optimized for search and retrieval |
| **Aggregation speed** | `COUNT(*) GROUP BY country` on 10B rows < 1 second | 10-100× slower for aggregate queries |
| **Full-text search** | No | Yes |
| **Why ClickHouse** | "Clicks per day per country" dashboard, time-series aggregations, cheap storage | — |
| **Why Elasticsearch** | If you need to search raw click data by user-agent, referrer string, or IP range | — |
| **When Elasticsearch wins** | Log analytics where you search text AND aggregate | — |
| **Real example A** | TinyURL analytics dashboard — ClickHouse | — |
| **Real example B** | Security event search ("find all clicks from this IP range") — Elasticsearch | — |

### Cross-Questions

**"Kafka consumers are slow. Click events are lagging 5 minutes. How do you recover without losing data?"**
> *"Kafka retains messages for 7 days by default (configurable). Lag means consumers are behind, not that data is lost. Recovery: scale out consumers (add more consumer group members — Kafka auto-rebalances partitions). If the underlying issue is ClickHouse write throughput, batch-insert larger chunks per consumer poll cycle. The Kafka offset ensures no event is missed once consumers catch up."*

**"Can you use ClickHouse as a real-time source for the redirect service?"**
> *"No. ClickHouse is optimized for batch reads and writes — not point lookups at 6,000 req/sec. Redirects need sub-millisecond lookups on short_code. That's Redis and MySQL's job. ClickHouse is for analytical aggregations that run on the reporting dashboard, not on the critical redirect path."*

**"How do you handle exactly-once delivery between Kafka and ClickHouse?"**
> *"Kafka's transactions + idempotent producer gives exactly-once on the produce side. On the consume side, ClickHouse's `ReplicatedMergeTree` engine with a deduplication window handles duplicate inserts — if the consumer crashes mid-batch and re-processes, ClickHouse deduplicates by a defined key (short_code + timestamp). At analytics scale, at-least-once with deduplication is practically equivalent to exactly-once."*

**"What's your ClickHouse schema to make 'clicks by day for code X' fast?"**
> *"Partition by day, sort key by (short_code, timestamp). That way, a query filtering on short_code scans only the relevant partition on disk."*

```sql
CREATE TABLE url_clicks (
    short_code  String,
    clicked_at  DateTime,
    country     LowCardinality(String),
    device_type LowCardinality(String),
    referrer    String
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(clicked_at)
ORDER BY (short_code, clicked_at);
```

---

## PART 10 — SCALABILITY DEEP DIVE

*"Let me walk through the four places this system breaks under load, and what I'd do at each inflection point."*

### Bottleneck 1: Read Path (Redirect)

```text
Current:   6,000 req/sec → Redis (80% hit) → DB replicas (20%)
Problem:   Redis single node saturates at ~100K ops/sec
Fix:       Redis Cluster (16,384 hash slots across N nodes)
           Add read replicas of Redis for read-heavy workloads

At 1M req/sec:
  → CDN edge cache for the top 0.01% of URLs (viral links)
  → CDN reduces origin traffic by 99% for hot URLs
  → Edge servers respond in ~2ms from nearest PoP
```

### Bottleneck 2: MySQL Write Path (URL Creation)

```text
Current:   120 writes/sec → single MySQL primary
Problem:   At 10,000 writes/sec, primary CPU saturates
Fix 1:     Connection pooling via PgBouncer/ProxySQL
Fix 2:     Write buffering — batch INSERTs every 100ms
Fix 3:     Shard by hash(short_code) % N

At scale:  Vitess (MySQL sharding proxy — used by YouTube, Slack)
           Transparent sharding, no application changes
```

### Bottleneck 3: URL Expiry Cleanup

```text
Current:   Nightly cron DELETE WHERE expires_at < NOW()
Problem:   At 1B rows, DELETE scan is expensive
Fix:       Partition table by month of expires_at
           Expiry = DROP PARTITION (instant) instead of DELETE (scan)

ALTER TABLE short_urls PARTITION BY RANGE (UNIX_TIMESTAMP(expires_at)) (
  PARTITION p2024_01 VALUES LESS THAN (UNIX_TIMESTAMP('2024-02-01')),
  PARTITION p2024_02 VALUES LESS THAN (UNIX_TIMESTAMP('2024-03-01')),
  ...
);
-- Expire a month: ALTER TABLE short_urls DROP PARTITION p2024_01;
-- This is O(1) regardless of partition size.
```

### Bottleneck 4: Analytics Write Throughput

```text
Current:   ~6,000 click events/sec → Kafka → ClickHouse consumers
Problem:   At 100K events/sec, consumer count must scale
Fix:       Increase Kafka partitions (partition by short_code hash)
           Each partition maps to one consumer — linear scale
           ClickHouse async_insert mode: buffer writes, flush every 1 second
```

---

## PART 11 — EXPLICIT TRADE-OFF TABLE

*"Every design is a set of bets. Here are mine — and why."*

| Decision | Option A | Option B | Trade-off | I Choose | Why |
|---|---|---|---|---|---|
| Redirect type | 302 Temporary | 301 Permanent | Analytics vs server load | **302** | Control analytics, deactivation |
| ID generation | KGS | Snowflake | Extra service vs clock dependency | **KGS** | Simpler, no clock skew risk |
| Cache pattern | Cache-aside | Write-through | Flexibility vs consistency | **Both** | Write-through on create, cache-aside on miss |
| Analytics path | Async Kafka | Sync DB write | Complexity vs latency | **Async** | Never block a redirect |
| Database | MySQL | Cassandra | ACID vs write scale | **MySQL** | Point lookups, ACID for KGS, 500GB fits |
| Shard key | hash(short_code) | hash(user_id) | Even distribution vs locality | **short_code** | Redirects are 100× more frequent |
| Cache eviction | LRU | LFU | Implementation vs optimality | **LRU** | Redis native, good enough |
| Consistency | Eventual | Strong | Availability vs latency | **Eventual** | 302 1s after creation is acceptable |

---

## PART 12 — WHAT NOT TO SAY

These are the answers that immediately signal a candidate hasn't thought carefully.

**"I'll use MongoDB for the URL store."**
> MongoDB's document model adds nothing here. The schema is fixed and simple. We need ACID transactions in KGS (moving keys from available → used atomically). MongoDB's multi-document transactions exist but add complexity for no benefit. SQL is the right tool.

**"I'll use a UUID as the short code."**
> UUIDs are 36 characters. A URL shortener with a 36-character code is a URL lengthener. Base62 with 7 chars gives 3.5 trillion unique values in a human-typeable format.

**"I'll use 301 to reduce server load."**
> This kills analytics permanently. The browser never contacts you again for that URL. You can't deactivate it, you can't update it, you can't track it. 302 is the only viable choice.

**"I'll just keep retrying MD5 with a salt until I find a free slot."**
> Collision detection requires a DB lookup on every creation. Under high load, this can loop multiple times. Latency becomes unbounded. Pre-generated keys or Snowflake IDs solve this structurally — not with retry loops.

**"I'll pre-generate all short codes into a pool table"** — this is actually valid, with caveats.
> KGS is the right implementation of this idea. The mistake is pre-generating codes without the `keys_available/keys_used` atomic swap — without that, two URL service nodes can race to claim the same key. The DB atomic transaction is what makes KGS safe, not just pre-generation.

**"I'll put analytics in the same synchronous write as URL creation."**
> Analytics writes should never be on the critical path. Fire-and-forget to Kafka. The creation API returns 201 before the analytics event is even sent.

---

## PART 13 — SENIOR TRAP QUESTIONS (15 YOE Level)

*These questions appear in staff/principal interviews. The format: Restate → Root cause → Solution → Trade-off → Production example.*

### Category 1: Consistency & Edge Cases

**Q: "Two users simultaneously try to register the same custom alias 'sale2024'. Both requests arrive at the same millisecond. What happens?"**

> *"This is a classic write-conflict race. Both requests hit the Create Service at the same time. Both check Redis or an application-level cache — both see the alias as available. Both try to INSERT into MySQL.*
>
> *The DB primary key on `short_code` is the safety net. MySQL's InnoDB engine uses row-level locking — only one INSERT wins; the second gets a `Duplicate Key` error. The Create Service catches `DataIntegrityViolationException` and returns HTTP 409 Conflict to that client.*
>
> *No application-level locking needed. No distributed lock needed. The DB handles it. Trade-off: the losing request pays a full DB round-trip before learning the conflict. At 120 writes/sec with custom aliases being rare, this is acceptable."*

**Q: "A URL was created 5 seconds ago. A user in Tokyo tries to visit it but gets a 404. Why?"**

> *"Replication lag. The URL was written to the MySQL primary in a US data center. The Tokyo Redirect Service is reading from a read replica that hasn't received the replication event yet — typically < 1 second lag, but can be longer under load.*
>
> *The mitigation: write-through cache on creation. When the Create Service writes to MySQL, it simultaneously writes to the Redis cluster. The Redirect Service checks Redis first — Redis replication lag is typically < 10ms even cross-region. So the user in Tokyo would likely find the URL in Redis even if the MySQL replica is behind.*
>
> *The edge case: Redis write-through also fails (network blip). Now the URL is in MySQL primary only, and the Tokyo replica hasn't caught up. The correct behavior is to document this: 'newly created URLs may take up to 5 seconds to be visible globally.' This is a known, accepted trade-off in the eventual consistency model."*

### Category 2: Failure Scenarios

**Q: "Redis cluster goes down completely. All 3 nodes. What's the user experience?"**

> *"Every redirect becomes a cache miss. All 6,000 req/sec hit MySQL read replicas. MySQL read replicas are provisioned for ~1,200 req/sec (20% of traffic in the happy path). They immediately saturate.*
>
> *First 30 seconds: redirect latency spikes from 5ms to 200-500ms as MySQL replicas queue requests. Then: MySQL replica connection pool exhaustion → 503 Service Unavailable for redirects.*
>
> *Response plan: (1) Alert fires on cache hit rate drop below 60%. (2) Add read replicas or scale up existing replicas within minutes via RDS auto-scaling. (3) Serve a degraded but functional response — even at 200ms, redirects work. (4) Do NOT fail closed — better a slow redirect than a 503.*
>
> *Prevention: Redis Cluster with AOF persistence so restart is fast. Sentinel for automatic failover. Multi-AZ replica for hardware failure. A 6-node cluster (3 primary + 3 replica) means we'd need all 6 nodes down simultaneously — statistically improbable."*

**Q: "KGS goes down. Both instances. What happens to URL creation?"**

> *"Each URL Service node holds a local key buffer of 100 pre-fetched keys. With 3 URL Service nodes, that's 300 keys in distributed local buffers. At 120 writes/sec peak, that's 2.5 seconds of runway.*
>
> *After 2.5 seconds: URL creation returns HTTP 503. We add `Retry-After: 30` header. The KGS typically restarts in under 10 seconds. Redirects are completely unaffected — KGS is only on the write path.*
>
> *Longer-term mitigation: increase local buffer to 10,000 keys (83 seconds of runway at peak). KGS re-syncs the used range to its DB on restart. The keys in local buffers are considered 'in-flight' — we accept potential waste of up to 10,000 IDs on a crash, which is acceptable."*

### Category 3: Scale

**Q: "You're at 10 billion URLs now. Walk me through what breaks first and how you fix it."**

> *"At 10B URLs, storage is 5TB — we need 10 MySQL shards. Writes stay trivial (120/sec). Redirects are still Redis-first, so read scale doesn't change much.*
>
> *What breaks: (1) Nightly cleanup cron — DELETE on a 10TB table is hours-long. Fix: table partitioning by expiry month, DROP PARTITION is instant. (2) Cross-shard user queries — 'show all URLs for user X' now fans out to 10 shards. Fix: secondary user-URL index in Elasticsearch. (3) Short code space — at 10B URLs from 3.5T possible 7-char codes, we've used 0.3%. Fine. (4) KGS pre-generation — offline KGS needs to have pre-generated enough keys. Fix: run KGS continuously, not just nightly.*
>
> *The core architecture doesn't change. It's an operational scale-out, not a redesign."*

**Q: "You're asked to make the redirect p99 < 1ms. What changes?"**

> *"Currently p99 < 10ms. To get to 1ms, I need to eliminate the Redis network round-trip (~1-2ms). Options: (1) Bloom filter in-process — a 1GB in-memory bloom filter can tell me if a code definitely doesn't exist without a Redis call. 99% of real short codes hit the filter → go to Redis. 1% false positive means an extra Redis call on a non-existent code. (2) CDN caching — push the hot 0.1% of URLs to CDN edge nodes globally. Edge serves the redirect from the same PoP as the user at ~0.5ms. (3) In-process L1 cache — each Redirect Service node caches the top 10K URLs (by access frequency) in a local LRU. Sub-millisecond for those URLs. Combined: CDN + local L1 + Redis L2 + MySQL L3. The top 0.001% of URLs never leave the CDN. The top 1% are served from L1. 99% from Redis. < 0.1% hit MySQL."*

### Category 4: Security

**Q: "How do you prevent someone from creating short URLs that redirect to phishing sites?"**

> *"Defense in depth. At creation time: validate the long URL against the Google Safe Browsing API v4 — it returns a threat classification in < 100ms. Block known malware, phishing, and social engineering URLs. This is synchronous on the critical path — it's acceptable latency for a creation (p95 < 200ms). After creation: periodic re-scanning of stored URLs. Safe Browsing threats evolve — a URL clean at creation might be flagged a week later. Run a background job that re-validates stored URLs every 24 hours and sets `is_active = false` on newly-flagged URLs. User reporting: add a 'Report this link' endpoint. Three reports triggers an automatic review queue. Manual review team for borderline cases. Rate limiting: limit new URL creation to 10/minute for free tier — slows mass phishing campaign setup."*

**Q: "A user reports their short URL was hijacked and now redirects somewhere else. How is that possible and how do you prevent it?"**

> *"A hijack scenario implies either: (1) the short code was updated in the DB, (2) Redis was poisoned with a different value, or (3) DNS/BGP hijack at a network level.*
>
> *For (1): the DB should only allow updates by the URL's owner (user_id check on every UPDATE). All updates are audit-logged. (2): Redis should be treated as a cache, not the source of truth. Any tampering in Redis is corrected on the next cache miss from MySQL. (3): Infrastructure security — out of scope for application design.*
>
> *Prevention: append-only URL records. Never allow `long_url` to be updated after creation — only allow `is_active` to be set to false (deactivation). If a user needs to change the destination, they create a new short URL. The original is immutable. This eliminates the entire class of 'hijacked redirect' bugs."*

### Category 5: Cost Optimization

**Q: "Your Redis bill is $50K/month. Your CTO says cut it in half. What do you do?"**

> *"Step 1: analyze the key distribution. What's the actual cache hit rate? If it's 95%, we might be over-provisioned. Use Redis's `INFO stats` and `OBJECT FREQ` to find keys with zero access in 7 days — evict them.*
>
> *Step 2: reduce TTL for low-frequency URLs. Currently 1-hour flat TTL for everything. Change to: top 5% URLs by access frequency get 24-hour TTL; long-tail URLs get 15-minute TTL. Hot URLs stay warm; cold URLs get evicted faster.*
>
> *Step 3: evaluate Bloom filter pre-filter. If 30% of Redis calls are 'does this key exist?' for invalid codes, a small in-memory Bloom filter can answer those without Redis. Reduces Redis call volume.*
>
> *Step 4: right-size the cluster. If memory utilization is 40%, scale down from 3×16GB to 3×8GB. Check eviction rate first.*
>
> *Step 5: CDN for the top 1000 URLs. If viral URLs are consuming 80% of Redis reads, pushing them to CloudFront edge cache eliminates those Redis calls entirely. CDN is cheaper than Redis at high read volume."*

**Q: "You have 5TB in MySQL across 10 shards. Storage cost is significant. How do you reduce it?"**

> *"Long URLs are the biggest storage consumer — average 200 bytes, 10B rows = 2TB for long_url alone. Deduplication: if the same long URL was shortened by 1M different users, we're storing it 1M times. Normalize: extract unique long URLs into a `url_targets` table, store only the foreign key in `short_urls`. Compression: MySQL InnoDB COMPRESSED row format reduces text column storage by 40-60%. ZSTD compression at the column level for `long_url`. Archival: URLs expired > 1 year are deleted from MySQL and optionally moved to cold object storage (S3 Glacier) for compliance. Partition pruning: as described, monthly partitions allow instant deletion of expired data without scan overhead. Combined, these typically achieve 50-70% storage reduction."*

---

## PART 14 — CHEAT SHEET

*Print this. Fold it. Keep it in your pocket. These are the numbers and one-liners you need within 3 seconds of the question.*

### Key Numbers

| Metric | Value |
|---|---|
| Daily writes | 1M/day = 12/sec avg, 120/sec peak |
| Daily reads | 100M/day = 1,200/sec avg, 6,000/sec peak |
| Read:write ratio | 100:1 |
| Storage | 500 GB (1B URLs × 500 bytes) |
| Code space | Base62, 7 chars = 3.5 trillion |
| Redis hot set | 40 GB (200M active URLs × 200B) |
| Cache hit target | 80% → DB sees 1,200 req/sec |
| Redirect p99 (hit) | < 10ms |
| Redirect p99 (miss) | < 100ms |
| Creation p95 | < 200ms |
| Availability | 99.99% |

### One-Sentence Answers Per Component

| Component | One sentence |
|---|---|
| Short code | KGS pre-generates random Base62 7-char codes, each URL service node caches 100 locally |
| Redirect | Redis first (5ms), MySQL fallback on miss (80ms), never block analytics write |
| Database | MySQL with hash(short_code) sharding, PRIMARY KEY on short_code for O(1) lookup |
| Caching | Cache-aside + write-through on creation, TTL = min(1hr, url_remaining_lifetime) |
| Expiry | Checked in SQL at redirect time (410 Gone), nightly DELETE cron as cleanup |
| Analytics | Kafka fire-and-forget after 302 sent, ClickHouse for aggregations |
| Scale | Redis Cluster for cache, Vitess for DB sharding, CDN for viral URLs |

### The One Closing Line

> *"Uniqueness via KGS, speed via Redis, simplicity via MySQL — that's the design."*

---

*Last updated: System_Design/system_design_interviewwithbunny/057-tiny-url-design/INTERVIEW_GUIDE.md*
*Source: Tiny_URL_Master_Guide.md + plan: is-it-following-what-sorted-boole.md*
