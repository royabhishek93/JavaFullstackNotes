# URL Shortener (TinyURL / Bitly) — Interview Script
## Design Real Examples: TinyURL, Bitly, t.co, LinkedIn Short Links
### Speak This Word-for-Word to Your Interviewer

> How to use this: Read PAGE 1 and PAGE 2 tonight. Read the full script once tomorrow morning.
> During the interview, use the RAPID ANSWER as your opening, then walk through each STEP.
> The WHAT NOT TO SAY section is as important as the rest — interviewers fail candidates on these.

# ═══════════════ PAGE 1 — START HERE ═══════════════

## BIG PICTURE (Understand This Before Anything Else)

> **► STUDY this diagram, don't draw it ◄**
> A URL shortener looks trivially simple — store a mapping and redirect. The hard part is generating
> billions of globally-unique short codes WITHOUT collisions, serving 100K+ redirects/sec with
> sub-5ms latency, and tracking analytics without blocking the critical redirect path.

```
  WRITE PATH (1,157/sec)                     READ PATH (115,740/sec)
  ─────────────────────                     ──────────────────────────

  Client                                    Client
    │                                         │
    │ POST /shorten {longUrl}                 │ GET /{shortCode}  e.g. GET /aB3xY7z
    ▼                                         ▼
  ┌─────────────────┐                      ┌──────────────────┐
  │   API Gateway   │                      │   API Gateway    │
  │  (Rate Limiter) │                      │  + CDN Edge      │
  └────────┬────────┘                      └────────┬─────────┘
           │                                        │
           ▼                                        │  Cache Hit?
  ┌─────────────────┐       YES: Return ◄───────────┤
  │  Shortener Svc  │       NO: miss               │
  │  (stateless)    │                               ▼
  │                 │                      ┌──────────────────┐
  │  1. Get ID from │                      │   Redis Cache    │
  │     Zookeeper   │                      │  url:{code}→url  │
  │     range       │                      │  LRU, 10GB       │
  │  2. Base62      │                      └────────┬─────────┘
  │     encode ID   │                               │ Cache Miss
  │  3. Store in DB │                               ▼
  └────────┬────────┘                      ┌──────────────────┐
           │                               │   MySQL (shard)  │
           │                               │  url_mappings    │
           ▼                               └────────┬─────────┘
  ┌─────────────────┐                               │
  │  MySQL Primary  │◄──────── store mapping        │ Return longUrl
  │  url_mappings   │                               ▼
  └─────────────────┘                      ┌──────────────────┐
           │                               │  Redirect Svc    │
           │ async event                   │  302/301 resp    │
           ▼                               └──────────────────┘
  ┌─────────────────┐
  │  Kafka Topic    │  ◄── click events (async, don't block redirect)
  │  url.clicks     │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │  ClickHouse     │
  │  Analytics DB   │
  └─────────────────┘
```

---

## RAPID ANSWER — If You Only Have 5 Minutes

*Read this first. Understand the whole answer before going deep.*

```
"I'd design TinyURL with five pieces:

1. Short Code Generation: Each server pre-allocates a range of 1 million integer IDs
   from Zookeeper. It converts each integer to Base62 (7 chars = 3.5 trillion codes).
   No network call on the hot path — only when the range is exhausted. Zero collisions.

2. Storage Layer: MySQL stores the url_mappings table (short_code → long_url).
   Rows are small (~500 bytes), queries are pure point lookups by primary key —
   MySQL handles this perfectly. We shard by short_code hash for scale.

3. Redirect Cache: Redis sits in front of MySQL for the read path. 20% of URLs
   get 80% of traffic (Zipf distribution). LRU cache of ~10GB holds the hot set.
   Cache-aside pattern: miss → read MySQL → populate Redis → return.

4. Redirect Type: 302 (temporary redirect) if analytics matter — browser won't cache
   it, every click hits our servers so we can count it. 301 (permanent) if we want
   to reduce server load — browser caches and never calls us again.

5. Analytics Pipeline: Click events go to Kafka asynchronously — the redirect
   response is sent immediately and click tracking happens in the background.
   Kafka consumers write to ClickHouse for fast analytical queries."
```

---

# ═══════════════ PAGE 2 — GLOSSARY ═══════════════

## Terminology — Know These Before Reading Further

```
┌──────────────────────────┬──────────────────────────────────────────────────────────────┐
│ Term                     │ What It Means (Simply)                                       │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Base62                   │ Encoding using 0-9, a-z, A-Z (62 chars). 7 chars = 62^7 =   │
│                          │ 3.5 trillion unique codes. Like hex but more compact.        │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Short Code               │ The 7-character identifier after the domain: tinyurl.com/aB3 │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Zookeeper                │ Distributed coordinator. Here used to hand out non-           │
│                          │ overlapping integer ranges to each server node.               │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ ID Range                 │ A block of integers (e.g., 1–1,000,000) reserved for one      │
│                          │ server to convert to short codes. No two servers share range. │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Cache-Aside              │ App checks cache first → on miss reads DB → writes to cache. │
│                          │ App manages the cache explicitly (not write-through).         │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ LRU Eviction             │ Least Recently Used — when cache is full, evict the entry    │
│                          │ that was accessed longest ago.                                │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Zipf Distribution        │ Power law: a few URLs get most of the traffic. Top 20% of   │
│                          │ URLs generate 80% of clicks. Caching exploits this.          │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ 301 Redirect             │ HTTP "Moved Permanently" — browser caches this forever.      │
│                          │ Subsequent clicks never hit your server. Bad for analytics.  │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ 302 Redirect             │ HTTP "Found" (temporary) — browser does NOT cache.           │
│                          │ Every click hits your server. Enables click counting.        │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ MD5 Hash                 │ Cryptographic hash producing 128-bit output. Taking first 7  │
│                          │ chars risks collision — two different URLs → same code.       │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Collision                │ Two different inputs producing the same short code. This     │
│                          │ would redirect user to the wrong URL. Must be prevented.     │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Custom Alias             │ User-chosen short code (e.g., tinyurl.com/my-product).       │
│                          │ Must be checked for uniqueness before storing.               │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ TTL (Time To Live)       │ Expiry duration. URL TTL in MySQL marks when a URL should    │
│                          │ stop working. Redis TTL auto-evicts cache entries.            │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ 410 Gone                 │ HTTP status for "resource existed but is permanently gone."  │
│                          │ Correct response for expired URLs (not 404 Not Found).       │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ ClickHouse               │ Columnar OLAP database optimized for analytics. Can query   │
│                          │ billions of click events in seconds.                         │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Kafka                    │ Distributed message queue. Click events written async here   │
│                          │ so redirect response is not blocked by analytics writes.     │
├──────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Sharding                 │ Horizontally splitting MySQL data across multiple servers.   │
│                          │ Shard by short_code hash so any shard can answer a query.    │
└──────────────────────────┴──────────────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 3 — WHY EACH COMPONENT ═══════════════

## Component Choices — Why We Picked Each One

```
┌──────────────────────┬─────────────────────────────────────────────────────────────────────┐
│ COMPONENT            │ WHY THIS? NOT SOMETHING ELSE?                                       │
├──────────────────────┼─────────────────────────────────────────────────────────────────────┤
│ Zookeeper for        │ WHY: Provides distributed coordination with strong consistency.     │
│ ID Range             │ Each server gets a unique integer range (e.g., server A gets        │
│ Allocation           │ 1–1M, server B gets 1M–2M). No two servers produce the same ID.    │
│                      │ Server only contacts Zookeeper when its range is exhausted (~rare). │
│                      │ WHY NOT MD5: MD5 hash of longUrl has collision risk. Two different  │
│                      │ long URLs can produce the same 7-char prefix — causes wrong         │
│                      │ redirect. Also requires a DB round-trip to check uniqueness on      │
│                      │ every creation. Zookeeper approach is O(1) and collision-free.      │
├──────────────────────┼─────────────────────────────────────────────────────────────────────┤
│ Base62 Encoding      │ WHY: 62 characters (a-z, A-Z, 0-9) are URL-safe, no encoding       │
│                      │ needed. 7 chars gives 3.5 trillion unique values — ~100 years       │
│                      │ at 100M URLs/day. Compact and human-readable in links.              │
│                      │ WHY NOT Base64: Base64 includes + and / which are not URL-safe      │
│                      │ and require percent-encoding. WHY NOT UUID: UUIDs are 36 chars,     │
│                      │ far too long for a "short" URL.                                     │
├──────────────────────┼─────────────────────────────────────────────────────────────────────┤
│ MySQL for            │ WHY: URL mappings are pure point lookups (GET by primary key).      │
│ url_mappings         │ MySQL's B-tree index on short_code gives O(log n) lookup.           │
│                      │ Rows are tiny (~500 bytes). Horizontal sharding by short_code       │
│                      │ distributes load. ACID ensures no duplicate short codes.            │
│                      │ WHY NOT Cassandra: Cassandra excels at time-series/append workloads │
│                      │ across wide partitions. URL lookups are random point reads —        │
│                      │ Cassandra adds operational complexity with no benefit here.         │
├──────────────────────┼─────────────────────────────────────────────────────────────────────┤
│ Redis Cache          │ WHY (Beginner — The Fridge Analogy):                                │
│                      │ MySQL is like a filing cabinet in the basement. It holds everything │
│                      │ permanently, but going there takes time (~5ms).                     │
│                      │ Redis is like a sticky note on the fridge. The most-used things are │
│                      │ right there, instant (~0.1ms).                                      │
│                      │                                                                     │
│                      │ The insight: 20% of URLs get 80% of clicks (Zipf law — same reason  │
│                      │ top 10 songs get most streams). That hot 20% is only ~10GB. Fits    │
│                      │ entirely in RAM. Redis absorbs most traffic; MySQL only sees the     │
│                      │ rare cache misses.                                                  │
│                      │                                                                     │
│                      │ Flow: Check Redis first → found? Done in 0.1ms.                    │
│                      │       Not there? Go to MySQL (5ms) → put result in Redis for next  │
│                      │       time (cache-aside pattern).                                   │
│                      │                                                                     │
│                      │ "Cluster" = multiple Redis nodes so one node failing doesn't kill   │
│                      │ everything (high availability).                                     │
│                      │                                                                     │
│                      │ WHY NOT Memcached: Redis supports TTL-per-key natively (needed for  │
│                      │ URL expiry). Redis also has richer data structures for future        │
│                      │ features (counters, sorted sets for analytics).                     │
├──────────────────────┼─────────────────────────────────────────────────────────────────────┤
│ Kafka + ClickHouse   │ WHY: Analytics (click counts, geographic data) must NOT block       │
│ for Analytics        │ the redirect. Kafka decouples the click event write from the        │
│                      │ redirect response. ClickHouse is a columnar store that can          │
│                      │ aggregate billions of clicks in seconds for dashboards.             │
│                      │ WHY NOT MySQL for analytics: MySQL is row-based — aggregating       │
│                      │ 10B click rows (COUNT by day, GROUP BY country) would be painfully  │
│                      │ slow. ClickHouse is purpose-built for this. Why not write sync:     │
│                      │ a DB write adding 5-10ms to every redirect would hurt p99 badly.   │
└──────────────────────┴─────────────────────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 4 — FULL INTERVIEW SCRIPT ═══════════════

---

## OPENING — When Interviewer Says "Design TinyURL"

"The core challenge here is not storage — it's generating billions of globally unique short codes
without collisions, and then serving 100,000+ redirects per second with sub-5ms latency. The
write path (creating short URLs) is easy; the read path (redirecting) is where the design lives.
Let me start by confirming requirements."

---

## STEP 1 — Requirements Gathering

```
┌──────────────────────────────────────────┬────────────────────────────────────────────────┐
│ YOU ASK                                  │ INTERVIEWER SAYS (typical)                     │
├──────────────────────────────────────────┼────────────────────────────────────────────────┤
│ How many new URLs per day?               │ 100 million per day                            │
├──────────────────────────────────────────┼────────────────────────────────────────────────┤
│ What's the read-to-write ratio?          │ About 100:1 — 10 billion redirects/day         │
├──────────────────────────────────────────┼────────────────────────────────────────────────┤
│ Should URLs expire?                      │ Yes, configurable TTL. Some permanent.         │
├──────────────────────────────────────────┼────────────────────────────────────────────────┤
│ Do we need custom aliases?               │ Yes, users can choose their own short code.    │
├──────────────────────────────────────────┼────────────────────────────────────────────────┤
│ Do we need click analytics?              │ Yes — clicks, referrer, geography.             │
├──────────────────────────────────────────┼────────────────────────────────────────────────┤
│ Latency target for redirects?            │ Under 10ms p99.                                │
├──────────────────────────────────────────┼────────────────────────────────────────────────┤
│ How long do we store URLs?               │ 5 years after creation.                        │
├──────────────────────────────────────────┼────────────────────────────────────────────────┤
│ Do we need user accounts?                │ Yes, users own their short URLs.               │
└──────────────────────────────────────────┴────────────────────────────────────────────────┘
```

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ REQUIREMENTS SUMMARY                                                                     │
├─────────────────────────────────────────┬────────────────────────────────────────────────┤
│ FUNCTIONAL                              │ NON-FUNCTIONAL                                 │
├─────────────────────────────────────────┼────────────────────────────────────────────────┤
│ 1. Create short URL from long URL       │ Scale: 100M creates/day, 10B redirects/day     │
│ 2. Redirect short URL → long URL        │ Redirect latency: < 10ms p99                  │
│ 3. Custom aliases                       │ Availability: 99.99% (4-nines)                │
│ 4. URL expiry / TTL                     │ Short code length: 7 characters                │
│ 5. Click analytics (count, geo, time)   │ Storage: 5-year retention, ~90 TB total        │
│ 6. User ownership of URLs               │ Consistency: eventual OK for analytics;        │
│ 7. 410 response for expired URLs        │   strong for URL mappings (no wrong redirects) │
└─────────────────────────────────────────┴────────────────────────────────────────────────┘
```

The key insight: this is an extreme read-heavy system (100:1). Every design decision should optimize the read path. Writes are nearly irrelevant at 1,157/sec — any reasonable DB handles that.

---

## STEP 2 — Capacity Estimation

```
WRITES:
  100M URLs/day ÷ 86,400 sec/day = 1,157 writes/sec
  Peak (2x): ~2,300 writes/sec

READS:
  10B redirects/day ÷ 86,400 = 115,740 reads/sec
  Peak (3x): ~350,000 reads/sec
  → This is the design constraint. Must be served mostly from cache.

SHORT CODE SPACE:
  7 chars, Base62 = 62^7 = 3,521,614,606,208 ≈ 3.5 trillion unique codes
  At 100M/day → exhausted in 3.5T ÷ 100M = 35,000 days ≈ 95 years
  → No need to expand code length for the foreseeable future.

STORAGE:
  Per URL row: ~500 bytes (short_code 10B + long_url 200B + metadata 290B)
  5 years × 365 days × 100M URLs/day × 500 bytes = ~91 TB
  → Partition MySQL across 10 shards = ~9 TB/shard (manageable)

REDIS CACHE:
  Hot set = top 20% of daily URLs = 20M URLs × 500 bytes = 10 GB/day active working set
  → Fits comfortably in a Redis cluster. LRU eviction handles rotation.

BANDWIDTH:
  Redirect response: ~200 bytes (Location header)
  115,740/sec × 200B = ~23 MB/sec outbound — trivial
```

---

## STEP 3 — Core Entities

```
┌────────────────────┬────────────────────────────────────────────────────────────────────┐
│ Entity             │ Key Fields                                                         │
├────────────────────┼────────────────────────────────────────────────────────────────────┤
│ ShortUrl           │ short_code (PK), long_url, user_id, created_at, expires_at,        │
│                    │ is_custom_alias (bool), click_count (updated async)                │
├────────────────────┼────────────────────────────────────────────────────────────────────┤
│ User               │ user_id (PK), email, created_at, plan_type (free/paid)             │
├────────────────────┼────────────────────────────────────────────────────────────────────┤
│ ClickEvent         │ event_id, short_code, clicked_at, ip_address, country,             │
│                    │ referrer, user_agent  → stored in ClickHouse, not MySQL            │
└────────────────────┴────────────────────────────────────────────────────────────────────┘
```

KEY INSIGHT: ClickEvent lives in ClickHouse (analytical), NOT in MySQL. Never mix OLTP (URL lookups) with OLAP (aggregation queries) in the same database.

WHY click_events EXISTS (Beginner Explanation):
  When someone clicks a short URL, you want to know: How many total clicks? From which
  countries? On which days? From which websites?

  That data has to be stored somewhere. The obvious bad idea:
    UPDATE url_mappings SET click_count = click_count + 1
  ...every time someone clicks.

  Why that's bad: Imagine 100,000 people clicking the same link per second. Every click
  tries to update the SAME row in the database. The database handles one update at a time
  on that row (row-level locking). Everything queues up. Your server crashes.

  The solution: Instead of UPDATING one row, APPEND a new event row each time:
    (short_code="aB3xY7z", country="IN", clicked_at="2026-08-30 10:31:00")
    (short_code="aB3xY7z", country="US", clicked_at="2026-08-30 10:31:01")

  Appending is fast and parallel — no locking. Then ClickHouse counts/groups these rows
  later for analytics. That is what the click_events entity is: a log of every click.

---

## STEP 4 — API Design

```
1. CREATE SHORT URL
   POST /api/v1/urls
   Request:  { "longUrl": "https://very-long-url.com/...", "customAlias": "my-link", "ttlDays": 30 }
   Response: { "shortUrl": "https://tinyurl.com/aB3xY7z", "shortCode": "aB3xY7z", "expiresAt": "2025-01-01" }
   Status: 201 Created | 409 Conflict (custom alias taken) | 400 Bad Request (invalid URL)

2. REDIRECT
   GET /{shortCode}                                  e.g. GET /aB3xY7z
   Response: HTTP 302 Location: https://original-long-url.com/...
             HTTP 410 Gone (if expired)
             HTTP 404 Not Found (if never existed)
   NOTE: No response body — browser follows Location header immediately.

3. GET URL INFO
   GET /api/v1/urls/{shortCode}
   Response: { "shortCode": "aB3xY7z", "longUrl": "...", "createdAt": "...", "clickCount": 14203 }

4. DELETE URL
   DELETE /api/v1/urls/{shortCode}
   Response: 204 No Content | 403 Forbidden (not owner) | 404 Not Found

5. GET ANALYTICS
   GET /api/v1/urls/{shortCode}/analytics?from=2024-01-01&to=2024-01-31
   Response: { "totalClicks": 14203, "clicksByDay": [...], "topCountries": [...], "topReferrers": [...] }

6. LIST USER'S URLs
   GET /api/v1/urls?user_id=123&page=1&limit=20
   Response: { "urls": [{ "shortCode": "aB3xY7z", "longUrl": "...", "createdAt": "...", "clickCount": 14203 }, ...], "total": 42, "page": 1 }
   Status: 200 OK | 403 Forbidden (not own user_id)

7. UPDATE URL DESTINATION
   PATCH /api/v1/urls/{shortCode}
   Request:  { "longUrl": "https://new-destination.com/..." }
   Response: { "shortCode": "aB3xY7z", "longUrl": "https://new-destination.com/...", "updatedAt": "..." }
   Status: 200 OK | 403 Forbidden (not owner) | 404 Not Found
   NOTE: Must DELETE url:{shortCode} from Redis cache on success to prevent stale redirects.

8. BULK CREATE SHORT URLs
   POST /api/v1/urls/bulk
   Request:  { "urls": [{ "longUrl": "https://...", "customAlias": "link1" }, { "longUrl": "https://..." }] }
   Response: { "created": [{ "shortCode": "aB3xY7z", "longUrl": "..." }, ...], "failed": [{ "longUrl": "...", "reason": "alias taken" }] }
   Status: 201 Created | 400 Bad Request (exceeds max batch size) | 207 Multi-Status (partial success)
```

WHY 302 over 301: A 301 means browsers cache the redirect permanently — every repeat click goes directly to the destination without hitting our servers. That means we cannot count those clicks or track analytics. Use 302 (temporary) when analytics matter. Mention this trade-off explicitly — it shows senior-level thinking.

> **WHY LIST USER'S URLs?** Every URL management dashboard needs this — users must be able to see and manage their own links; without it you have a write-only API that cannot support any real product UI. The idx_user_urls index on (user_id, created_at DESC) in the DB schema is there precisely to serve this query efficiently.

> **WHY PATCH (not PUT) for URL UPDATE?** PATCH means partial update — only the fields sent are changed; PUT would require re-sending the full resource. Also note: changing the destination must invalidate the Redis cache entry (DELETE url:{shortCode}) to prevent stale redirects. This is a key side-effect interviewers probe for.

> **WHY BULK CREATE?** Enterprise/marketing users need to shorten hundreds of URLs at once (e.g., campaign link sets). Bulk reduces N round trips to 1. The 207 Multi-Status response lets callers know which URLs succeeded and which failed (e.g., alias taken), enabling partial-success handling without aborting the whole batch.

---

## STEP 5 — High-Level Architecture

> **► DRAW THIS on the whiteboard ◄**
> Draw two separate flows: the WRITE path (left side) and READ path (right side). Show Zookeeper
> on the write side and Redis cache as the first stop on the read side. Connect both to MySQL in
> the center. Add Kafka → ClickHouse at the bottom for analytics.

```
                     ┌─────────────────────────────────────────────────────────┐
                     │                    CLIENTS                              │
                     └──────────────┬────────────────────┬────────────────────┘
                                    │                    │
                              POST /shorten          GET /{code}
                                    │                    │
                     ┌──────────────▼────────────────────▼────────────────────┐
                     │              API GATEWAY / Load Balancer               │
                     │           (Rate limiting, SSL termination)              │
                     └──────────────┬────────────────────┬────────────────────┘
                                    │                    │
                     ┌──────────────▼──────┐    ┌────────▼─────────────────────┐
                     │   Shortener Service │    │    Redirect Service           │
                     │   (Write Path)      │    │    (Read Path, stateless)     │
                     │                     │    │                              │
                     │  1. Get next ID     │    │  1. Check Redis cache        │
                     │     from local      │    │  2. On miss: query MySQL     │
                     │     range           │    │  3. Check expiry             │
                     │  2. Base62 encode   │    │  4. Populate cache           │
                     │  3. Store in MySQL  │    │  5. Send 302 redirect        │
                     │  4. Publish event   │    │  6. Async: publish to Kafka  │
                     └──────┬──────────────┘    └────────┬─────────────────────┘
                            │                            │
              ┌─────────────▼────┐          ┌────────────▼──────┐
              │    Zookeeper     │          │    Redis Cluster   │
              │  ID Range Mgmt   │          │  url:{code}→url   │
              │  Server gets 1M  │          │  LRU, TTL per key │
              │  IDs at a time   │          │  ~10-20 GB hot    │
              └──────────────────┘          └────────────────────┘
                                                         │ cache miss
                            ┌────────────────────────────▼──────┐
                            │        MySQL (Sharded 10x)         │
                            │        url_mappings table          │
                            │  Shard key: short_code (hash mod)  │
                            │  Primary: RDS Multi-AZ             │
                            │  Replicas: read traffic overflow    │
                            └────────────────────────────────────┘
                                            │
                                            │ click events (async)
                            ┌───────────────▼──────────────────────┐
                            │         Kafka Cluster                │
                            │      Topic: url.click.events         │
                            │      Partitioned by short_code       │
                            └───────────────┬──────────────────────┘
                                            │
                            ┌───────────────▼──────────────────────┐
                            │         ClickHouse                   │
                            │  Columnar OLAP for analytics queries │
                            │  clicks by day, country, referrer    │
                            └──────────────────────────────────────┘
```

### WHY EACH BOX EXISTS (Beginner — Restaurant Analogy)

Think of the system like a restaurant:

| Box | What it does | Restaurant Analogy |
|---|---|---|
| **Client** | Person using TinyURL | Customer placing an order |
| **API Gateway** | Single entry point — checks rate limit, routes requests | Front door + host — checks your reservation, directs you |
| **Shortener Service** | Creates short URLs (write path) | Kitchen that *creates* the dish |
| **Redirect Service** | Looks up and redirects (read path) | Waiter who *delivers* the dish |
| **Zookeeper** | Hands out non-overlapping ID blocks to each server | Manager with the number dispenser |
| **Redis** | In-memory cache of hot URLs — 0.1ms lookup | Whiteboard with today's popular orders — no need to dig through files |
| **MySQL (sharded)** | Permanent storage of all URL mappings | Filing cabinet — real permanent record of everything |
| **Kafka** | Drop click events in a queue; don't slow down the redirect | Order ticket printer — waiter drops ticket, doesn't file paperwork mid-service |
| **ClickHouse** | Processes click events for analytics reports | Accountant who processes all tickets and produces reports |

---

> **► DRAW THIS on the whiteboard ◄**

## STEP 5b — SEQUENCE DIAGRAM: Redirect Flow
```
  Browser         CDN/Edge         Redirect Service    Redis             MySQL
    │                  │                  │               │                 │
    │ GET /abc123      │                  │               │                 │
    │─────────────────▶│                  │               │                 │
    │                  │ cache miss       │               │                 │
    │                  │─────────────────▶│               │                 │
    │                  │                  │ GET url:abc123│                 │
    │                  │                  │───────────────▶                 │
    │                  │                  │◀───────────────│                 │
    │                  │                  │  [longUrl]     │  (cache hit)    │
    │                  │ 302 Location:    │               │                 │
    │◀─────────────────│ longUrl          │               │                 │
    │                  │                  │               │                 │
    │                  │                  │ publish to Kafka (async)        │
    │                  │                  │────────────────────────────────▶│
    │                  │                  │ click_event{shortCode,ip,ua,ts} │
```

---

## STEP 6 — Database Schema

> **► DRAW THIS on the whiteboard ◄**

```
TABLE: url_mappings
┌─────────────────┬──────────────────┬──────────────────────────────────────────────────┐
│ Column          │ Type             │ Notes                                            │
├─────────────────┼──────────────────┼──────────────────────────────────────────────────┤
│ short_code      │ VARCHAR(10)      │ PRIMARY KEY. Shard key. Indexed. e.g. "aB3xY7z"  │
│ long_url        │ TEXT             │ The original destination URL (up to 2048 chars)  │
│ user_id         │ BIGINT           │ FK to users table. Who created this URL.         │
│ created_at      │ TIMESTAMP        │ Creation time. Default NOW().                    │
│ expires_at      │ TIMESTAMP NULL   │ NULL = never expires. Checked on redirect.       │
│ is_custom_alias │ BOOLEAN          │ Whether user provided the short code.            │
│ long_url_hash   │ CHAR(32)         │ MD5 of longUrl for de-dup lookup by same user.   │
└─────────────────┴──────────────────┴──────────────────────────────────────────────────┘
INDEXES:
  PRIMARY KEY (short_code)
  INDEX idx_user_urls (user_id, created_at DESC)   -- for "list my URLs" queries
  INDEX idx_long_url_hash (user_id, long_url_hash) -- for de-duplication

WHY long_url_hash? (Beginner Explanation)
  Problem: If you paste the same long URL twice, without this you'd get two different short
  codes — wasteful and confusing for the user's dashboard.

  The fix: Run the long URL through MD5 — a function that converts any text into a fixed
  32-character "fingerprint":
    "https://amazon.com/very/long/url" → "9191c037d0c5f4408f0caf5c3cd39edd"

  Now you can check: "have I seen this URL before?" by comparing 32-char fingerprints.
  You can't run WHERE long_url = '...' efficiently — TEXT columns can't be indexed (they're
  too long). A CHAR(32) hash column CAN be indexed → fast duplicate detection.

  Important: de-dup is per user, not global. Two different users can have different short
  codes pointing to the same destination (they want separate analytics, aliases, expiry).

TABLE: users
┌─────────────────┬──────────────────┬──────────────────────────────────────────────────┐
│ Column          │ Type             │ Notes                                            │
├─────────────────┼──────────────────┼──────────────────────────────────────────────────┤
│ user_id         │ BIGINT AUTO_INC  │ PRIMARY KEY                                      │
│ email           │ VARCHAR(255)     │ UNIQUE. Login identifier.                        │
│ created_at      │ TIMESTAMP        │ Account creation time.                           │
│ plan_type       │ ENUM             │ 'free', 'pro', 'enterprise'                      │
└─────────────────┴──────────────────┴──────────────────────────────────────────────────┘

REDIS KEY SCHEMA:
  url:{shortCode}     → longUrl           (TTL = URL expiry time, or 24h for no-expiry URLs)
  user_ratelimit:{ip} → request count     (TTL = 1 minute, sliding window rate limit)

CLICKHOUSE TABLE: click_events
┌────────────────┬──────────────────┬──────────────────────────────────────────────────┐
│ Column         │ Type             │ Notes                                            │
├────────────────┼──────────────────┼──────────────────────────────────────────────────┤
│ short_code     │ String           │ Partition key (shard for analytics)              │
│ clicked_at     │ DateTime         │ ORDER BY key for time-range queries              │
│ country        │ LowCardinality   │ Derived from IP via GeoIP                        │
│ referrer       │ String           │ HTTP Referer header                              │
│ user_agent     │ String           │ Browser/device info                              │
│ ip_address     │ String           │ Hashed for privacy compliance                   │
└────────────────┴──────────────────┴──────────────────────────────────────────────────┘
PARTITION BY: toYYYYMM(clicked_at)  -- monthly partitions for efficient range queries
ORDER BY: (short_code, clicked_at)  -- optimizes queries like "clicks for code X in Jan"
```

Partition key choice: We shard MySQL by hash(short_code). This evenly distributes short codes across shards and ensures any redirect query hits exactly one shard. Never shard by user_id — a viral URL on one user would hot-spot a shard.

---

## STEP 7 — Deep Dive: ID Generation Without Collisions

This is the most important technical question in URL shortener design. Know all three options and defend Option C.

```
OPTION A: MD5 / SHA1 Hash of longUrl, Take First 6-7 Chars
────────────────────────────────────────────────────────────
  shortCode = sha1(longUrl).substring(0, 7)

  COLLISION PROBLEM — Visual from image:
  ┌───────────────────────────────────────────────────────────────────────────┐
  │  SHA1("https://www.facebook.com/anindya.s.dasgupta/")                     │
  │    = 9191c0  37d0c5f4408f0caf5c3cd39edd  ← full hash                     │
  │              ↑ take first 6 chars = "9191c0"                              │
  │                                                                           │
  │  SHA1("https://www.amazon.in/")                                           │
  │    = 9191c0  37d0c5f4408f0caf5c3cd39e3r3  ← SAME first 6 chars!          │
  │              ↑ "9191c0" COLLISION — both map to same short code           │
  │                                                                           │
  │  Result: user who clicks bit.ly/9191c0 gets redirected to amazon.in       │
  │          instead of facebook.com  ← CATASTROPHIC wrong redirect           │
  └───────────────────────────────────────────────────────────────────────────┘
  Encryption Logic: sha1(longUrl) → (shortURL, 6 or 7 chars) → response

  PROBLEM 1: Birthday paradox collision risk.
    With 3.5T possible codes but millions of URLs, probability of collision is non-trivial.
    e.g. at 1B URLs stored, probability of collision ≈ 1 - e^(-n²/2m) where n=1B, m=3.5T
    = ~13% collision probability. Unacceptable.

  PROBLEM 2: Every creation needs a DB round-trip to check uniqueness.
    If collision: pick next 7 chars or append counter → retry loop → complexity.

  PROBLEM 3: Same longUrl → same shortCode. Good for de-dup but bad for different users
    who want separate short codes for the same destination.


OPTION B: Global Auto-Increment Counter + Base62
─────────────────────────────────────────────────
  counter++ → base62(counter) → guaranteed unique

  Beginner explanation:
  One shared counter that just counts up: 1, 2, 3, 4...
  Every time a new URL is created, someone asks: "What's the next number?"
  Gets 1001 → Base62 encodes to "0000g3". Next person gets 1002 → "0000g4".
  Guaranteed unique, zero collision.

  PROBLEM: That single counter is like one cashier serving the entire city.
  10 servers all have to wait in line at the same counter. If the counter
  goes down, everything stops. It works fine at small scale but becomes a
  bottleneck and single point of failure as you grow.


OPTION B2: Snowflake ID (Twitter-style, Decentralized)
────────────────────────────────────────────────────────
  64-bit ID generated locally per server — no coordination needed.

  Beginner explanation:
  What if each server could generate unique IDs WITHOUT asking anyone?
  Each server embeds three pieces of information directly into the number:

    [WHEN it was created] [WHICH server made it] [HOW MANY this millisecond]
         41 bits                10 bits                  12 bits

  Example: It's 10:31:05 AM (as a number), you're Server #5, 3rd URL this ms:
    ID = (timestamp) + (server_5) + (sequence_3) → unique number → Base62 encode

  Server #5 and Server #7 at the same millisecond → different server bits → different IDs.
  No coordination needed. No Zookeeper. No shared counter.

  WHY NOT use it for TinyURL?
  The timestamp bits make the numbers LARGE (like 1,722,000,000,000).
  Base62 encoding a large number needs more characters → 10-11 char codes.
  That defeats the "short URL" purpose. Zookeeper ranges produce small sequential
  integers (1, 2, 3...) which encode to exactly 7 chars. So for URL shorteners,
  Zookeeper wins. Snowflake is better for database row IDs, tweet IDs, etc.

  BIT STRUCTURE:
  ┌──────────────────────────────────────────────────────────────────────┐
  │  [1 bit unused][41 bits timestamp][10 bits workerID][12 bits seq]    │
  │                                                                      │
  │  41-bit timestamp: 2^41 / 365 / 24 / 3600 / 1000 = 69.73 years      │
  │  12-bit sequence:  2^12 = 4,096 IDs per millisecond per worker       │
  │  10-bit workerID:  2^10 = 1,024 workers (servers)                    │
  └──────────────────────────────────────────────────────────────────────┘

  Pros: no Zookeeper needed, 4M IDs/sec, time-ordered, decentralized
  Cons: 10-11 chars (longer URL), requires clock sync (NTP), workerID mgmt
  When to choose: very high creation rate (>100K/sec) OR Zookeeper unavailable


OPTION C (BEST for most cases): Zookeeper Range Allocation
─────────────────────────────────────────────
  Each server starts with an empty range.

  WHAT IS ZOOKEEPER? (Beginner Analogy — The Token Dispenser)
  ┌────────────────────────────────────────────────────────────────────┐
  │  Imagine a token counter machine at a government office. When you  │
  │  walk in, you pull a ticket: "You are customer #47." The next      │
  │  person gets #48. No two people EVER get the same number.          │
  │                                                                    │
  │  Now imagine 10 offices (servers) all using the SAME machine.      │
  │  If they pull tickets one by one, they'd be queuing constantly.    │
  │                                                                    │
  │  Zookeeper's smarter solution: each office goes to the machine     │
  │  ONCE and says "Give me tickets 1–1,000,000 for my office."        │
  │  The next office gets 1,000,001–2,000,000. Each office works from  │
  │  its own stack — no queuing, no overlap, no conflict.              │
  │                                                                    │
  │  That's Zookeeper. It hands out non-overlapping blocks of numbers  │
  │  to each server. Each server converts those numbers into short     │
  │  codes (Base62). Zero chance of two servers creating the same      │
  │  short code.                                                       │
  │                                                                    │
  │  Technical: /counters/url_counter node stores the global counter.  │
  │  Atomic setData() ensures no two servers ever get the same range.  │
  └────────────────────────────────────────────────────────────────────┘

  ZOOKEEPER COUNTER FLOW (multiple servers, no collision):
    client → Load Balancer (round robin)
      → Encryption Server 1  (workerID: 123) ─┐
      → Encryption Server 2  (workerID: 234) ──┼──► Zookeeper
      → Encryption Server 3  (workerID: 345) ─┘    (atomic range assignment)
      → Decryption Server N  (handles 80% redirect reads)
                                           ↓
                                       Database  (cron job for expiry cleanup)
                                           ↓
                                       Redis  2ms  (cache layer)

  On startup (or range exhaustion):
    Server contacts Zookeeper.
    Zookeeper atomically increments a global counter by 1,000,000.
    Returns range [N, N+1,000,000) to the server.
    Server stores this range in memory. Zookeeper is NOT contacted again
    until the server has used all 1M IDs.

  On URL creation:
    Server takes next ID from in-memory range.
    base62(id) → 7-char short code.
    No network call. No collision possible (ranges never overlap).
    Single server failure: at most 1M IDs are "lost" — trivially acceptable
    given we have 3.5 trillion total.

  RESULT:
    - Zero collision risk
    - Zero network call on hot path (only 1 Zookeeper call per million URLs)
    - Each server generates IDs independently and in parallel
    - Horizontal scaling: add servers, each gets their own range
```

```
BASE62 ENCODING — How It Creates 3.5 Trillion Codes (Beginner Explanation):
  You know how binary (base 2) with 3 digits gives you 8 combinations?
    000, 001, 010, 011, 100, 101, 110, 111  →  8 = 2³

  Base62 uses 62 symbols instead of 2:
    Digits:    0 1 2 3 4 5 6 7 8 9           (10 symbols)
    Lowercase: a b c ... z                   (26 symbols)
    Uppercase: A B C ... Z                   (26 symbols)
    Total: 62 symbols

  With 7 positions, each position has 62 choices:
    62 × 62 × 62 × 62 × 62 × 62 × 62 = 62⁷ = 3,521,614,606,208 ≈ 3.5 trillion

  At 100 million new URLs per day:
    3,500,000,000,000 ÷ 100,000,000 = 35,000 days ≈ 95 years
  → You won't run out of short codes in your lifetime.

BASE62 ENCODING EXAMPLE (how a number becomes a short code):
  Input integer: 125 (decimal)
  Base62 charset: "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

  125 ÷ 62 = 2 remainder 1  → charset[1] = '1'
    2 ÷ 62 = 0 remainder 2  → charset[2] = '2'

  Short code: "21" (padded to 7 chars with leading zeros: "0000021")

  Java implementation sketch:
  ┌────────────────────────────────────────────────┐
  │ String toBase62(long id) {                     │
  │   char[] chars = "0123456789abcdefghijk...";   │
  │   StringBuilder sb = new StringBuilder();      │
  │   while (id > 0) {                             │
  │     sb.append(chars[(int)(id % 62)]);          │
  │     id /= 62;                                  │
  │   }                                            │
  │   return sb.reverse().toString();              │
  │ }                                              │
  └────────────────────────────────────────────────┘
```

---

## STEP 8 — Scalability

```
BOTTLENECK 1: Read path — 115K RPS redirect queries
  PROBLEM: MySQL cannot serve 115K random point reads/sec without enormous hardware.
  SOLUTION:
    1. Redis cache in front of MySQL. Serves 80%+ of traffic from memory (~1ms latency).
    2. MySQL read replicas for cache misses (split read traffic from write traffic).
    3. CDN edge caching for 301 redirects (if analytics not needed): browser and CDN
       cache the redirect indefinitely, removing server from the loop entirely.
  RESULT: MySQL sees only ~20K RPS (cache misses + new URLs), well within capacity.

BOTTLENECK 2: Single MySQL instance for URL mappings
  PROBLEM: Even with replicas, a single primary MySQL can't handle 90 TB + 1,157 writes/sec
    at extreme scale.
  SOLUTION: Horizontal sharding by hash(short_code) across 10 shards.
    Each shard handles 10% of traffic and 9 TB of data.
    Any redirect query routes to exactly one shard — no cross-shard queries needed.
    Application-level routing: shardIndex = hash(shortCode) % NUM_SHARDS.
  RESULT: Linearly scalable by adding shards.

BOTTLENECK 3: URL expiry cleanup
  PROBLEM: You can't check expiry synchronously during redirect (adds latency) AND
    you can't delete 100M+ rows efficiently without a strategy.
  SOLUTION:
    1. Redis TTL: set Redis key TTL = URL expiry time. Redis auto-evicts the key.
       On cache miss → MySQL query → check expires_at field → return 410 if expired.
    2. Background cleanup job: runs nightly, DELETE FROM url_mappings WHERE
       expires_at < NOW() - INTERVAL 7 DAYS. Batch deletes (1000 rows at a time)
       to avoid locking. 7-day grace period allows any in-flight requests to complete.
  RESULT: Redirect path is never blocked by expiry checks beyond a Redis TTL lookup.

BOTTLENECK 4: Analytics write volume
  PROBLEM: 115K click events/sec → cannot write synchronously to any DB during redirect.
    If analytics DB is slow, ALL redirects slow down.
  SOLUTION:
    1. Fire-and-forget Kafka publish after sending 302 response.
       Redirect response is sent to client immediately.
       Click event is published to Kafka asynchronously.
    2. Kafka consumer batch-writes to ClickHouse (high throughput columnar insert).
    3. Acceptable lag: analytics dashboards can be 30-60 seconds behind real-time.
  RESULT: Redirect latency is decoupled from analytics write latency entirely.
```

---

## WHAT NOT TO SAY ✗

```
✗ "I'll use MD5 hash of the long URL as the short code"
  Why wrong: MD5 has collision risk at scale (13%+ collision probability at 1B URLs).
  Also means same long URL always maps to same code — prevents multiple users from
  having different short codes for the same destination URL. Always use counter + Base62.

✗ "I'll use a global auto-increment counter on the database"
  Why wrong: This is a single point of failure and a serialization bottleneck. At
  scale (1,157 writes/sec) a single counter in MySQL/Redis becomes the ceiling.
  Use Zookeeper range allocation to distribute ID generation across servers.

✗ "I'll store click counts in the url_mappings table with UPDATE ... SET click_count = click_count + 1"
  Why wrong: Hot URLs (100K+ clicks/sec) would cause catastrophic write contention on
  a single row. Row-level locking in MySQL would serialize all click writes. Use Kafka
  async pipeline → ClickHouse for analytics instead.

✗ "Use 301 redirect — it reduces server load"
  Why wrong: Only if you don't need analytics. 301 means browsers cache the redirect
  permanently — those repeat clicks NEVER reach your server. You cannot count them,
  track them, or know they happened. Always ask whether analytics are needed before
  choosing redirect type.

✗ "Use Cassandra for URL storage — it scales better"
  Why wrong: Cassandra is optimized for time-series data with wide rows. URL lookups
  are random point reads by short_code — a perfect B-tree index use case. Cassandra
  adds operational complexity (tunable consistency, tombstone issues) with zero benefit
  for this access pattern.

✗ "I'll return 404 for expired URLs"
  Why wrong: 404 means "never existed." An expired URL did exist — it just expired.
  HTTP 410 Gone is the semantically correct response. This matters for SEO and for
  clients that cache 404 responses differently from 410.

✗ "De-duplication: if two users submit the same long URL, return the same short code"
  Why wrong: Different users may want analytics tracked separately, custom aliases on
  the same URL, or different expiry times. De-dup only within the same user's URLs
  (check long_url_hash per user_id). Different users get different short codes.
```

---

## SENIOR TRAP QUESTIONS (15 YOE Level)

### Category 1: Consistency and Edge Cases

**Q: A user submits a long URL that they've already shortened before. What happens?**

A: We store a long_url_hash column (MD5 of the longUrl) indexed by (user_id, long_url_hash).
On create, we check: SELECT short_code FROM url_mappings WHERE user_id = ? AND long_url_hash = ?
If found and not expired, return the existing short code — no new row created.
If expired or not found, create a new one. This prevents a user's dashboard from filling up
with duplicate entries. Important caveat: this de-dup is per-user, not global — two different
users can legitimately have different short codes pointing to the same long URL for independent
analytics tracking.

**Q: A custom alias conflicts with an auto-generated code we might produce in the future. How do you handle this?**

A: Custom aliases are inserted into the same url_mappings table with the same short_code primary key.
The Zookeeper counter approach means we produce numeric Base62 codes sequentially: "0000001", "0000002", etc.
Custom aliases chosen by users (like "my-blog") are alphanumeric strings that would only collide if a user
happened to choose a code identical to our sequential output at the exact moment that counter value is
reached. Mitigation: reserve a separate namespace — all auto-generated codes are left-padded to exactly
7 chars (e.g., "0000001"), while custom aliases must be ≥ 4 chars and not match the zero-padded pattern.
Alternatively, maintain a separate custom_aliases table and check both tables on redirect.

---

### Category 2: Failure Scenarios

**Q: Your Zookeeper cluster goes down. What happens to URL creation?**

A: Each application server holds a pre-allocated range of 1 million IDs in memory. A Zookeeper outage
only affects servers that have exhausted their current range and need a new one. Servers with remaining
range continue creating URLs normally — they never contact Zookeeper mid-range. To handle this gracefully:
implement a range refresh threshold (when 10% of range remains, proactively fetch the next range while
still serving from the current one). With 1M IDs per range and ~1,157 writes/sec, each server takes
roughly 14 minutes to exhaust a range — enough time to retry Zookeeper or alert ops. Circuit breaker
pattern: if Zookeeper is down and range is exhausted, return 503 to new URL creation requests rather
than corrupt the ID space with duplicates.

**Q: Redis cache goes down completely. What is the impact and how do you recover?**

A: The redirect read path now falls entirely on MySQL. At 115,740 RPS, MySQL (even sharded) will
be overwhelmed — typical MySQL shard handles 5-10K random reads/sec comfortably, much less 115K.
Immediate impact: redirect latency spikes from ~1ms to 50-200ms, likely causing cascading timeouts.
Mitigation strategy: (1) MySQL read replicas absorb read traffic — provision 5-10 replicas per
shard as standby. (2) Implement a local in-process cache (Caffeine/Guava) in each application server
as an L1 cache — holds the hottest 100K URLs in JVM heap. (3) Redis should be deployed in cluster
mode with replicas and AOF persistence — failover is automatic in under 30 seconds with sentinel.
Recovery: on Redis restart, the cache warms organically as traffic flows through (cache-aside pattern).
No manual intervention needed.

---

### Category 3: Scale and Advanced Design

**Q: You need to support 1 billion redirects per second (10x current estimate). What breaks and how do you fix it?**

A: At 1B RPS, the following changes are needed in order of priority. First, Redis alone cannot serve
this — even a large Redis cluster tops out around 100M-500M ops/sec. Solution: push redirect resolution
to CDN edge nodes (CloudFront, Fastly). For non-expiring, non-analytics URLs, the CDN can cache the
redirect rule at the edge — the HTTP response never reaches your origin. This handles 90%+ of traffic
with zero database involvement. Second, the remaining cache-miss traffic (new URLs, cache misses) needs
a globally distributed Redis setup with regional clusters (AWS us-east, eu-west, ap-southeast) using
active-active replication. Third, MySQL shards need to be at 50+ nodes with each shard as a Vitess
cluster. The Zookeeper ID allocation already scales horizontally — no change needed there. Analytics
pipeline scales by adding Kafka partitions and ClickHouse nodes independently.

**Q: How would you implement URL analytics that show "this link is trending right now — 10K clicks in the last 5 minutes"?**

A: This requires a streaming aggregation layer, not just batch analytics. Architecture: Kafka click
events flow into a stream processor (Flink or Kafka Streams). The processor maintains a sliding window
of 5 minutes keyed by short_code, counting events in real-time. When count exceeds a threshold (e.g.,
1000 clicks in 5 min), an event is published to a "trending URLs" Kafka topic. A separate consumer
reads this topic and writes to a Redis sorted set: ZADD trending:urls <score=click_count> <short_code>.
The trending dashboard queries ZREVRANGE trending:urls 0 9 to get the top 10 trending URLs in O(log n).
Key design choice: the stream processor uses approximate counting (HyperLogLog or Count-Min Sketch) to
handle the cardinality at 1B RPS scale without running out of memory.

---

## KEY NUMBERS — Memorize These

```
┌───────────────────────────────────────┬─────────────────────────────────────────────────┐
│ Metric                                │ Value                                           │
├───────────────────────────────────────┼─────────────────────────────────────────────────┤
│ New URL creates/day                   │ 100 million                                     │
│ New URL creates/sec (avg)             │ 1,157 writes/sec                                │
│ Redirects/day                         │ 10 billion                                      │
│ Redirects/sec (avg)                   │ 115,740 reads/sec                               │
│ Read:Write ratio                      │ 100:1                                           │
│ Short code length                     │ 7 characters                                    │
│ Encoding                              │ Base62 (a-z, A-Z, 0-9)                         │
│ Total unique codes (Base62, 7 chars)  │ 3.5 trillion (62^7)                             │
│ Code space exhaustion time            │ ~95 years at 100M URLs/day                      │
│ Storage per URL row                   │ ~500 bytes                                      │
│ Total storage (5 years)               │ ~90 TB                                          │
│ Redis cache working set               │ ~10 GB (top 20% hot URLs)                       │
│ Cache hit rate (Zipf distribution)    │ 80%+ of redirects served from cache             │
│ Zookeeper range per server            │ 1 million IDs                                   │
│ Time to exhaust 1M IDs per server     │ ~14 minutes at 1,157 writes/sec                 │
└───────────────────────────────────────┴─────────────────────────────────────────────────┘
```

*Study order hint: Start with RAPID ANSWER → memorize the 5 components. Then study the ID generation
deep dive (STEP 7) — this is the #1 follow-up question. Memorize the KEY NUMBERS table last.
The WHAT NOT TO SAY section is pass/fail — review it the morning of the interview.*

---

## KEY PATTERNS REFERENCED IN THIS DESIGN

> **For the 2-year developer:** These are the hidden concepts that make this design work. Each one has a dedicated deep-dive file. When asked "why did you choose X?" in your interview — these are the reasons.

### Index Types (Hash Index on short_code)
**Why it matters here:** The redirect query is a pure equality lookup — WHERE short_code = 'abc123'. A hash index answers this in O(1) versus B-tree's O(log N). At 1 billion URLs and 115K QPS redirects, that constant-time lookup is the difference between sub-millisecond and multi-millisecond latency per redirect.
**Deep dive:** `../../Index_Types_BTree_Hash_Composite_Covering.md`

### Leader Election
**Why it matters here:** ID generation requires that only one service instance owns a range of sequential IDs at a time — otherwise two servers generate the same short code. ZooKeeper ephemeral nodes make one server the leader for a given ID range; if it dies, another claims the range via a new ephemeral node.
**Deep dive:** `../../Leader_Election_Zookeeper_Raft.md`

### CAP Theorem
**Why it matters here:** Tiny URL is AP — during a network partition, old short codes must still redirect even if new short code registrations fail. Availability over consistency: a stale redirect is infinitely better than a 503 for every user clicking a link.
**Deep dive:** `../../CAP_Theorem_Applied_What_Actually_Breaks.md`

### [Bloom Filter + HyperLogLog](../../Bloom_Filter_HyperLogLog_Approximate_Data_Structures.md)
**Why this system uses it:** Before assigning a short code, check if it already exists. With 5 billion codes, a HashSet would consume ~40GB of memory. A Bloom filter stores 5B entries in ~9GB with 1% false positive rate — a "definitely new" result skips the DB lookup entirely; a "probably exists" result (99% of the time false) verifies against DB. This cuts DB existence checks by ~99% under normal load.

### [Negative Caching](../../Negative_Caching_Cache_Miss_Storm.md)
**Why this system uses it:** Bots probe URL shorteners with millions of random codes that don't exist. Without negative caching, every probe hits the database — a 1M-request bot attack = 1M DB queries for nothing. Cache "code not found" responses with a 60-second TTL: the first miss hits the DB once; the next 999,999 requests for the same non-existent code return 404 from cache instantly. Combined with a Bloom filter (which handles "definitely doesn't exist" before cache), the DB sees near-zero bot traffic.
