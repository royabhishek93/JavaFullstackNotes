# URL Shortener — Conversational Interview Script (12-Year Level)
Speak this. Natural flow, ASCII diagrams, no fluff.

Print settings: Landscape, Courier New/Consolas 9-10pt, narrow margins.

---

## OPENING

Interviewer: "Design a URL shortener like Bitly or TinyURL."

You:
"Sure. Before I start drawing, let me ask a few quick questions to make sure we're aligned."

"First — do users get to choose a custom alias, or is the short code always auto-generated?"
"Second — do we need click analytics — counts, device, geo?"
"Third — should URLs expire? If yes, what's the default?"
"Fourth — what scale are we targeting — daily active users and total URLs?"

[Assume interviewer says: 100M DAU, 1B URLs total, custom alias is a premium feature, default expiry 90 days, analytics out of scope for now.]

You:
"Perfect. Let me structure this. I'll start with requirements and capacity, then do a high-level design, then go deep on the most critical part — short code generation — because that's where most designs break. Then I'll cover database, caching, and failure handling."

---

## STEP 1 — REQUIREMENTS

You:
"Let me quickly list what we're building."

```text
FUNCTIONAL:
  - Shorten a long URL -> get a short URL back
  - Visit the short URL -> redirect to the original
  - Custom alias for premium users
  - URL expiration (default 90 days, custom for premium)

NON-FUNCTIONAL:
  - Redirect latency: p99 < 10ms (cached), < 100ms (cache miss)
  - URL creation: p95 < 200ms
  - 99.99% availability
  - No duplicate short codes — ever
  - Eventual consistency is fine (tiny lag after creation is acceptable)
  - Scale: 100M DAU, 1B total URLs
```

You:
"One thing I want to call out early — this system is heavily read-skewed. Every URL gets created once but clicked many times. My read-to-write ratio will be around 100:1. That shapes every caching and scaling decision I make."

---

## STEP 2 — CAPACITY

You:
"Quick math — let me think out loud."

```text
WRITES (URL creation):
  Assume 1% of DAU create a URL/day
  = 100M x 1% = 1M creations/day
  = ~12 writes/second  (peak: ~120/sec)

READS (redirects):
  Each short URL clicked ~100 times on average
  = 1M creations/day x 100 = 100M redirects/day
  = ~1,200 redirects/second  (peak: ~6,000/sec)

STORAGE:
  1B URLs x 500 bytes avg = 500 GB — fits in a relational DB cluster easily

SHORT CODE SPACE:
  Base62, 7 characters = 62^7 = 3.5 trillion unique codes
  Way more than enough for 1B URLs
```

You:
"So writes are trivial at 120/sec. Reads at 6,000/sec need caching to stay under 10ms. Storage is 500GB — manageable in SQL."

---

## STEP 3 — HIGH-LEVEL DESIGN

You:
"Let me draw the basic shape first, then I'll go deeper."

```text
         +------------------+
         |     Client       |
         +--------+---------+
                  |
                  v
         +------------------+
         |  Load Balancer   |
         +----+--------+----+
              |        |
         +----+--+  +--+----+
         |URL Svc|  |URL Svc|   (multiple nodes)
         +----+--+  +--+----+
              |        |
         +----+--------+----+
         |                  |
         v                  v
  +-----------+      +-------------+
  | URL DB    |      | Redis Cache |
  | (SQL)     |      | short->long |
  +-----------+      +-------------+
```

You:
"Two flows — creation and redirect."

```text
CREATE:
  Client -> URL Service -> generate short_code
         -> DB: INSERT (short_code, long_url, expires_at)
         -> Cache: SET short_code -> long_url
         -> return short URL to client

REDIRECT:
  Client -> GET /r/{short_code}
  URL Service -> Cache lookup
    HIT  -> 302 redirect  (~5ms)
    MISS -> DB lookup -> write to cache -> 302 redirect (~80ms)
```

Interviewer: "Why 302 and not 301?"

You:
"Good catch. 301 is a permanent redirect — the browser caches it and goes directly to the long URL on future visits, bypassing our server entirely. That saves bandwidth but kills analytics — we never see those clicks again. 302 is temporary — every visit hits us first. Since we want to keep analytics as a future option, I'll use 302."

### 3.1 Separate Create Service vs Redirect Service

You:
"One more thing before I go deep on code generation. I want to split the URL service into two separate microservices — a Create Service and a Redirect Service. Here's why."

```text
TRAFFIC SPLIT:
  ~20% of users are creating short URLs
  ~80% of users are hitting short URLs to redirect

If I put both in the same service, I'm forced to scale them together.
But they have completely different load profiles and resource needs.

BETTER:

+------------------+     +------------------+
| Create Service   |     | Redirect Service |
| (20% of traffic) |     | (80% of traffic) |
|                  |     |                  |
| - generate code  |     | - cache lookup   |
| - DB write       |     | - DB read        |
| - cache write    |     | - 302 redirect   |
| 3 instances      |     | 6-8 instances    |
+------------------+     +------------------+
```

You:
"Now I can scale the Redirect Service independently — more instances, more Redis read replicas. The Create Service stays lean. This is separation of concerns at the infrastructure level."

"Load balancer routes based on path:"

```text
POST /v1/urls      -> Create Service cluster
GET  /r/{code}     -> Redirect Service cluster
```

You:
"This is where most designs fail in interviews. Let me walk through the approaches in order — each one fixes the previous one's problem."

---

### APPROACH 1 — MD5 / SHA1 Hash

You:
"First instinct most people have: hash the long URL, take the first 6 characters."

```text
long_url -> MD5() -> "91c0a3f8b2d4e6..." -> take first 6 -> "91c0a3"
```

You:
"Seems fine, but there's a serious problem. MD5 was designed for full-string uniqueness. When you crop it to 6 characters, collision probability skyrockets. At 1 billion URLs, you'll get frequent collisions where two different long URLs produce the same 6-char code."

"Handling collisions means re-hashing with a salt, checking the DB again — potentially multiple times per creation. Latency becomes unpredictable."

"I'd only use this for very small scale — under a million URLs. Not here."

---

### APPROACH 2 — Single Counter + Base62

You:
"Better approach. Keep a counter. Each URL gets the next number. Encode that number to Base62."

```text
Base62 uses: 0-9 (10) + a-z (26) + A-Z (26) = 62 characters

Counter  -> Base62
1        -> "0000001"
62       -> "0000010"
1000000  -> "4c92"

Encode algorithm:
  chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
  while num > 0:
    result.append(chars[num % 62])
    num = num / 62
  return reverse(result), padded to 7 chars
```

You:
"This guarantees uniqueness — counter never repeats. No DB check needed. Fast."

"But there's a problem. The counter lives in the server's local memory. The moment I scale to multiple servers, each one starts at zero. Server-1 gives 'URL-A' the code '000001'. Server-2 gives 'URL-B' the code '000001'. Collision."

"Single server only. Not suitable for 100M DAU."

---

### APPROACH 3 — Global Counter in Redis

You:
"Fix: move the counter out of local memory into Redis. Redis INCR is atomic — only one server gets each number."

```text
Client -> URL Service (any node)
       -> Redis: INCR global_counter -> returns N (atomic)
       -> encode N to Base62 -> short_code
       -> DB: INSERT (short_code, long_url)
       -> return short URL
```

You:
"This works, and I'd use it for medium scale. But there are two issues. One — Redis is now a single point of failure. If it goes down, all URL creation stops. Two — every creation makes a synchronous network call to Redis. At very high throughput, Redis becomes a serialisation bottleneck."

"Mitigations: Redis Sentinel for HA, Redis Cluster for scale. Still valid for most real-world use. But let me show you the cleaner distributed solution."

---

### APPROACH 4 — Zookeeper Range Allocation

You:
"Instead of one global counter with a lock on every write, use Zookeeper to allocate non-overlapping counter ranges to each server. Each server increments its own local counter — no network call per URL."

```text
Zookeeper allocates:
  Server-1 -> range [1 .. 1,000,000]
  Server-2 -> range [1,000,001 .. 2,000,000]
  Server-3 -> range [2,000,001 .. 3,000,000]

Each server increments locally:
  Server-1: 1, 2, 3, 4 ...  (fully local, no network hop)
  Server-2: 1,000,001, 1,000,002 ...

When Server-1 reaches 1,000,000:
  -> contact Zookeeper -> get next range [3,000,001 .. 4,000,000]
  -> resume local increments
```

You:
"Zookeeper is only contacted when a range is exhausted — which is rare. Daily at 120 writes/sec, 1M range lasts over 2 hours. So Zookeeper load is minimal. No per-request coordination. Scales to any number of servers."

"Zookeeper itself runs as a quorum — 3 or 5 nodes — so no SPOF."

#### Zookeeper Node Types — Know This for the Interview

You:
"Zookeeper stores data in a tree structure — like a filesystem. Two types of nodes matter here."

```text
EPHEMERAL NODE:
  - Lives only as long as the server that created it is alive
  - Zookeeper sends heartbeats to registered servers
  - If heartbeat times out -> server is dead -> ephemeral node is deleted automatically
  - Used for: service registration, leader election

PERSISTENT NODE:
  - Survives server restarts, crashes, Zookeeper restarts
  - Must be explicitly deleted — never auto-deleted
  - Used for: storing the counter value (must survive crashes!)

For URL shortener:
  - Each server registers as an EPHEMERAL node -> gets a worker ID
  - The global counter is a PERSISTENT node -> survives any crash
  - When a server restarts, it re-registers, gets a new worker ID,
    and resumes from whatever counter state was last persisted
```

---

### APPROACH 4b — Snowflake ID (The Hybrid — Recommended for Production)

You:
"This is the approach I'd actually use in production — it combines Zookeeper worker IDs with a local counter and timestamp to generate a globally unique 64-bit ID. No network call per URL creation. Everything is local."

```text
SNOWFLAKE ID STRUCTURE (64 bits total):

  | 1 bit  | 41 bits       | 10 bits   | 12 bits        |
  | sign   | timestamp(ms) | worker ID | sequence/local |

  Sign bit    : always 0 (positive)
  Timestamp   : milliseconds since epoch (~69 years of range)
  Worker ID   : assigned by Zookeeper at server startup (unique per server)
  Sequence    : local counter per server, resets every millisecond

HOW IT GENERATES A UNIQUE ID:
  1. Server starts -> registers with Zookeeper -> receives worker ID (e.g. 123)
  2. Request comes in:
     - read current timestamp in ms       -> 41 bits
     - use worker ID from Zookeeper       -> 10 bits
     - increment local sequence counter  -> 12 bits
     - combine -> 64-bit integer
  3. Encode 64-bit integer to Base62      -> 7-char short code

EXAMPLE:
  timestamp  = 1718000000000 (41 bits)
  worker_id  = 123           (10 bits)
  sequence   = 5             (12 bits)
  snowflake  = 7624839593475 (combined 64-bit number)
  Base62     = "bK9pQ3x"     (7 chars, URL-safe)
```

You:
"Why is this better than plain Zookeeper ranges? Two reasons. One — you never contact Zookeeper per request. Worker ID is fetched once at startup and cached. Two — even if two servers happen to fire at the same millisecond, they have different worker IDs — the IDs are still unique. And within a single server, sequence handles up to 4,096 IDs per millisecond before rolling over."

"What if Zookeeper is down at startup? The server can't get a worker ID and refuses to start. That's the right behaviour — better to fail fast than to generate IDs with a duplicate worker ID."

```text
Snowflake vs Zookeeper Ranges:

Zookeeper Ranges   : ranges allocated upfront, server uses them locally
                     good, but range management is manual
Snowflake ID       : no ranges needed — timestamp + worker ID + sequence
                     is inherently unique across all servers at all times
                     more elegant, used by Twitter, Discord, Instagram
```

Interviewer: "What if the server clock goes backward?"

You:
"Clock skew is a real risk with Snowflake IDs. If the system clock goes back — say due to NTP correction — we could regenerate a timestamp we already used. Fix: track the last-used timestamp. If current timestamp < last timestamp, either wait until the clock catches up, or throw an exception and refuse to generate until the clock is consistent."

---

### APPROACH 5 — Pre-Generated Key Generation Service (KGS)

You:
"This is the approach I recommend for simplicity and correctness. A dedicated Key Generation Service pre-generates millions of random Base62 codes and stores them in a keys database."

```text
KGS architecture:

  +------------------+      +------------------+
  |  keys_available  |      |  keys_used        |
  |------------------|      |------------------|
  | short_code (PK)  |      | short_code (PK)  |
  |  "3xK9pQ"        |      |  "2aB8mN"        |
  |  "7mR2qW"        |      +------------------+
  |  "4pL5xN"        |
  +------------------+

URL Service -> KGS: "give me a key"
KGS: BEGIN TXN
     -> move one key from available to used (atomic)
     COMMIT
     -> return key to URL Service
URL Service -> DB: INSERT (key, long_url)
```

You:
"KGS pre-generates keys offline — no collision possible since they're pre-validated against the primary key. URL service never hashes, never checks DB for duplicates — just takes a key and saves."

"To avoid KGS being a SPOF, I run two KGS instances. Each one loads a batch of keys — say 1,000 — into memory from the DB. They never overlap because the DB atomic transaction ensures each key is claimed once."

```text
KGS-1: loads keys [k1 .. k1000] into memory
KGS-2: loads keys [k1001 .. k2000] into memory
Both serve from their own in-memory batch — no lock contention
```

You:
"Even if KGS briefly goes down, each URL service node keeps a local buffer of ~100 keys. Creation continues during KGS restart window."

---

### APPROACH COMPARISON

```text
Approach              Unique?   Scales?   Latency   Complexity   Use when
-----------------------------------------------------------------------
MD5 hash (6 chars)    Risky     No        High      Low          < 1M URLs
Single counter        Yes       No        Low       Low          Single server
Redis global counter  Yes       Medium    Medium    Medium       Medium scale
Zookeeper ranges      Yes       Yes       Low       Medium       Large scale
KGS pre-generated     Yes       Yes       Low       Medium       Recommended
```

---

## STEP 5 — DATABASE DESIGN

You:
"Let me draw the schema."

```text
+---------------------------+         +---------------------------+
| users                     |         | short_urls                |
|---------------------------|         |---------------------------|
| user_id (PK)              |         | short_code (PK)           |
| email (UNIQUE)            |         | long_url                  |
| api_key (UNIQUE)          |         | user_id (FK, INDEX)       |
| subscription_type         |         | custom_alias (INDEX)      |
| created_at                |         | expires_at (INDEX)        |
+---------------------------+         | created_at                |
                                      | is_active (BOOL)          |
                                      +---------------------------+

KGS database:
+---------------------------+         +---------------------------+
| keys_available            |         | keys_used                 |
|---------------------------|         |---------------------------|
| short_code (PK)           |         | short_code (PK)           |
+---------------------------+         | assigned_at               |
                                      +---------------------------+
```

You:
"Key index decisions:"

```text
short_urls:
- PRIMARY KEY (short_code)           -> O(1) redirect lookup
- INDEX (expires_at)                 -> expiry cleanup job
- INDEX (custom_alias)               -> fast uniqueness check for custom alias
- INDEX (user_id, created_at DESC)   -> list user's URLs
```

Interviewer: "Why SQL and not NoSQL?"

You:
"Three reasons. One — schema is simple and fixed. Two — 500GB fits in a sharded SQL cluster without pain. Three — I need ACID transactions in KGS to atomically move keys from available to used — that's much cleaner in SQL. If we were at 10TB+ or needed highly variable schema, I'd reconsider Cassandra or DynamoDB. For this problem, SQL is the right call."

---

## STEP 6 — CACHING

You:
"This is where I recover the latency. The redirect path is read-heavy at 6,000 req/sec. I put Redis in front of the DB."

```text
Redirect flow:
  GET /r/{short_code}
       |
       v
  Redis: GET short_code
       |
  HIT  +-> return long_url -> 302 redirect  (~5ms)
       |
  MISS +-> DB: SELECT long_url WHERE short_code=? AND expires_at > NOW()
            |
            +-> Redis: SET short_code -> long_url  TTL=1hr
            |
            +-> 302 redirect  (~80ms)

On URL creation: write-through
  -> also SET in cache immediately (first redirect is fast, no cold miss)
  -> TTL = min(1hr, remaining_lifetime_of_url)
     e.g. URL expires in 2 hours -> TTL = 2 hours
          URL expires in 30 mins -> TTL = 30 mins
          URL never expires      -> TTL = 1 hour (standard)

On URL deletion/expiry:
  -> explicitly DELETE from cache (don't wait for TTL)
```

You:
"One subtle thing here — I match the Redis TTL to the URL's actual expiry time. If I just set a flat 1-hour TTL for everything, a URL that expires in 10 minutes will still be cached and serve redirects for up to an hour after it should have stopped. Setting TTL = remaining lifetime of the URL prevents that."

"The formula:"

```text
  redis_ttl = min(standard_ttl, expires_at - NOW())

  If expires_at is null (no expiry) -> use standard_ttl (1hr)
  If expires_at - NOW() < 0         -> URL already expired, don't cache at all
```

You:
"Cache sizing: the web follows an 80/20 rule — 20% of URLs get 80% of traffic. Active URLs = ~200M. At ~107 bytes per entry, that's ~21GB. A Redis cluster of 3 nodes handles this easily."

"Cache hit rate of 80% means DB sees only 20% of redirect traffic — roughly 1,200 req/sec, well within replica read capacity."

Interviewer: "What eviction policy?"

You:
"LRU — Least Recently Used. Hot URLs stay cached, cold ones are evicted automatically. If Redis memory pressure grows, I increase cluster size or reduce TTL for low-traffic URLs."

---

## STEP 7 — FULL ARCHITECTURE

You:
"Let me now draw the complete picture with all components."

```text
            +-------------------------------+
            |  Client (browser / app)       |
            +---------------+---------------+
                            |
                            v
            +-------------------------------+
            |  CDN (optional edge cache     |
            |  for extremely hot short URLs)|
            +---------------+---------------+
                            |
                            v
            +-------------------------------+
            |  Load Balancer (L7)           |
            +------+------+------+----------+
                   |      |      |
             +-----+  +---+--+  +-----+
             |URL Svc|  |URL Svc|  |URL Svc|
             +--+----+  +--+---+  +--+----+
                |          |         |
        +-------+----------+---------+-------+
        |                  |                 |
        v                  v                 v
+-------------+    +-------------+    +--------------+
| Redis Cache |    | URL DB      |    | KGS          |
| short->long |    | (Primary +  |    | (KGS-1,KGS-2)|
| LRU, TTL    |    |  2 Replicas)|    | key batches  |
+-------------+    +------+------+    +------+-------+
                          |                  |
                          v                  v
                   +-----------+      +-------------+
                   | Expiry    |      | Keys DB     |
                   | Cron Job  |      | available / |
                   | (nightly) |      | used tables |
                   +-----------+      +-------------+
```

---

## STEP 8 — FAILURE HANDLING

Interviewer: "What if Redis goes down?"

You:
"URL service falls back directly to DB. Redirect latency goes from 5ms to 80ms — users notice a slowdown but nothing breaks. I also alert on cache hit rate drop so the on-call team can investigate. Redis Cluster with Sentinel handles most failures automatically."

Interviewer: "What if KGS goes down?"

You:
"Each URL service node keeps a local buffer of 100 pre-fetched keys. During KGS restart, creation continues from the buffer. Buffer refills in background when KGS comes back. KGS itself runs two instances — if one dies, the other keeps serving."

Interviewer: "What about DB primary failure?"

You:
"Semi-sync replication to 2 replicas. Auto-failover in under 30 seconds. Redirects continue unaffected — they're served from cache or read replicas. URL creation queues briefly or returns 503 during the failover window. Acceptable given 99.99% availability target."

Interviewer: "Two users try to register the same custom alias simultaneously?"

You:
"The DB primary key on short_code rejects the second INSERT atomically. The URL service catches DataIntegrityViolationException and returns HTTP 409 Conflict. No application-level locking needed. The DB handles it."

---

## STEP 9 — EXPIRY HANDLING

You:
"Two-layer approach."

```text
Layer 1 — At redirect time (immediate):
  SELECT long_url WHERE short_code = ? AND (expires_at IS NULL OR expires_at > NOW())
  If expired -> return 410 Gone  (not 404 — 410 means "gone permanently")

Layer 2 — Background cleanup (nightly cron):
  DELETE FROM short_urls WHERE expires_at < NOW()
  Keeps the DB lean over time
```

You:
"I do the check in SQL, not in application code — avoids a race condition where the app reads expires_at, time passes, and the cached value is stale."

---

## STEP 10 — TRADEOFFS

You:
"Let me be explicit about the tradeoffs I'm making."

```text
302 over 301           : keep analytics capability, at cost of higher server load
KGS over MD5           : zero collision risk, at cost of an extra service
SQL over NoSQL         : ACID, simpler ops, at cost of harder sharding above 1TB
Write-through cache    : first redirect is fast, at cost of extra write on creation
LRU eviction           : hot URLs always cached, cold URLs always miss — accepted
Eventual consistency   : high availability, tiny lag on new URLs — acceptable for this domain
```

---

## STEP 11 — CROSS-QUESTIONS

Q: Why not use UUID for the short code?
A: "UUID is 36 characters — way too long for a short URL. Base62 with 7 chars gives 3.5 trillion unique values, is URL-safe, and is human-readable. Much better fit."

Q: How do you prevent someone from enumerating all short URLs?
A: "With KGS, codes are pre-generated randomly — not sequential. Even with Zookeeper ranges, Base62 encoding of interleaved range numbers looks random. Rate limiting on the redirect endpoint also blocks bulk scraping."

Q: What if someone creates a short URL pointing to a malicious site?
A: "Validate long URL against Google Safe Browsing API at creation time. Reject known malware and phishing domains. For custom aliases, additional manual review for premium accounts. Flag URLs reported by users for takedown."

Q: How would you add analytics without slowing down redirects?
A: "Fire-and-forget. After serving the 302, publish a click event to Kafka asynchronously. The redirect path is not blocked. A separate consumer reads Kafka and writes to ClickHouse or BigQuery for analytics. Latency SLO preserved."

Q: How do you scale if we hit 10 billion URLs?
A: "Shard the URL DB by hash(short_code) across multiple nodes. Each shard holds a subset of short_urls. KGS keys space partitioned across shards. Redis cluster already handles the read scale. Short code length extended to 8 chars (62^8 = 218 trillion) if needed. Same architecture — just more nodes."

---

## STEP 12 — CLOSING

You:
"Let me summarise the design."

```text
1) Short code: KGS pre-generates random Base62 7-char codes
               Two KGS instances, each serving from in-memory key batch
               URL service buffers 100 keys locally per node

2) Redirect  : Redis cache (LRU, 1hr TTL) absorbs 80% of traffic
               Cache HIT -> 302 in ~5ms
               Cache MISS -> DB read -> cache write -> 302 in ~80ms
               Write-through on creation

3) Database  : SQL (PostgreSQL), PRIMARY KEY on short_code
               2 read replicas for redirect fallback
               Nightly cron deletes expired rows

4) Scale     : Load balancer -> multiple URL service nodes (stateless)
               Redis Cluster for cache, Redis Sentinel for HA
               DB sharding if URL count exceeds 1TB

5) Failures  : Redis down -> fall back to DB, alert on hit rate
               KGS down   -> serve from local buffer, two instances
               DB down     -> replica promotion in < 30s

6) Expiry    : checked at redirect time in SQL, 410 if expired
               cleaned up nightly by cron job
```

One-line close:
"Uniqueness via KGS, speed via Redis, simplicity via SQL — that's the design."
