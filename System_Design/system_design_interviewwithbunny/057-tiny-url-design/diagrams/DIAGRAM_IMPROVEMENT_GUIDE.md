# 🎯 Diagram Improvement Guide for Beginners

**Problem**: Current diagrams are too abstract for beginners. This guide shows exactly what to fix in each diagram to match the INTERVIEW_GUIDE.md structure.

---

## 🔧 **How to Apply These Improvements**

1. Open each `.drawio` file in [diagrams.net](https://app.diagrams.net)
2. Follow the "What to Change" instructions below
3. Save the updated diagram
4. Compare with the "After" description to verify

---

## 📊 **Diagram 1: Context** (`01-context.drawio`)

### **Current Problems**
❌ Missing clear separation of actors  
❌ No indication of request/response types  
❌ Doesn't show the 100:1 read-to-write ratio  

### **What to Change**

#### **1. Split User Types**
Add three distinct actors on the LEFT:
```
┌─────────────┐
│   Regular   │  → "Shortens 100M URLs/day"
│    User     │
└─────────────┘

┌─────────────┐
│  Anonymous  │  → "Clicks 10B short URLs/day" 
│   Clicker   │     (100x more traffic)
└─────────────┘

┌─────────────┐
│   Premium   │  → "Can create custom aliases"
│    User     │     (e.g., bit.ly/my-store)
└─────────────┘
```

#### **2. Label the System Boundary**
Change the central box label from just "TinyURL System" to:
```
┌─────────────────────────────────────────┐
│     TinyURL System                      │
│  (10B redirects/day, <10ms p99)         │
│                                         │
│  Core Capabilities:                     │
│  • Generate unique short codes          │
│  • Store URL mappings                   │
│  • Redirect users (READ HEAVY)          │
│  • Track click analytics                │
└─────────────────────────────────────────┘
```

#### **3. Show Interaction Arrows with Examples**
Replace generic arrows with labeled flows:
```
Regular User → System
  Label: "POST /shorten {longUrl: 'amazon.com/product/12345'}"
  
System → Regular User
  Label: "Response: {shortUrl: 'tiny.url/aB3xY7z'}"

Anonymous Clicker → System
  Label: "GET /aB3xY7z" (100x more frequent)
  
System → Anonymous Clicker
  Label: "HTTP 302 Redirect → amazon.com/product/12345"
```

#### **4. Add Key Insights Box**
Add a callout box at the bottom:
```
┌─────────────────────────────────────────────────────────┐
│  🔑 KEY INSIGHT: Read-Heavy System                      │
│                                                         │
│  WRITES: 1,157/sec  (creating short URLs)               │
│  READS:  115,740/sec (clicking short URLs)              │
│  Ratio:  100:1 READ HEAVY                               │
│                                                         │
│  → Every design decision optimizes the READ path!       │
└─────────────────────────────────────────────────────────┘
```

---

## 🏗️ **Diagram 2: HLD Components** (`02-hld-components.drawio`)

### **Current Problems**
❌ Doesn't separate WRITE path from READ path (interview guide emphasizes this)  
❌ Missing Zookeeper for ID generation  
❌ No traffic volume indicators  
❌ Redis cache placement unclear  

### **What to Change - Complete Redesign**

**Draw TWO SEPARATE FLOWS side-by-side:**

### **LEFT SIDE: WRITE PATH (1,157/sec)**

```
┌───────────────────────────────────────┐
│   WRITE PATH — Creating Short URLs   │
│        (1,157 requests/sec)          │
└───────────────────────────────────────┘

[1] Client
     │ POST /shorten {longUrl}
     ▼
[2] API Gateway
     │ • Rate limit check
     │ • Route to available instance
     ▼
[3] Shortener Service (stateless)
     │
     │──[A]→ Zookeeper: Get ID from local range
     │      (Server A has IDs 1-1M pre-allocated)
     │      Only hits Zookeeper when range exhausted
     │
     │──[B]→ Base62 encode: 12345 → "dnh"
     │
     │──[C]→ MySQL Primary: Store mapping
     │      INSERT INTO url_mappings
     │      (short_code, long_url, user_id)
     │
     │──[D]→ Kafka: Publish creation event (async)
     │
     ▼
Response: {shortUrl: "tiny.url/dnh"}

┌─────────────────────────────────────┐
│  🧠 Why Zookeeper?                  │
│                                     │
│  Problem: 10 servers creating URLs  │
│  simultaneously. How to ensure no   │
│  two servers generate same code?    │
│                                     │
│  Solution: Zookeeper hands out      │
│  non-overlapping ranges:            │
│  • Server A: IDs 1 - 1,000,000      │
│  • Server B: IDs 1,000,001 - 2M     │
│  • Server C: IDs 2,000,001 - 3M     │
│                                     │
│  Zero collisions, O(1) generation!  │
└─────────────────────────────────────┘
```

### **RIGHT SIDE: READ PATH (115,740/sec)**

```
┌───────────────────────────────────────┐
│    READ PATH — Redirecting Users     │
│       (115,740 requests/sec)         │
│         🔥 THIS IS THE HOT PATH      │
└───────────────────────────────────────┘

[1] Client
     │ GET /aB3xY7z
     ▼
[2] CDN / Edge (optional)
     │ Check if cached at edge
     ▼
[3] API Gateway
     │ Forward to redirect service
     ▼
[4] Redirect Service (stateless)
     │
     │──[A]→ Redis Cache: GET url:aB3xY7z
     │        ✅ HIT (99% of requests)
     │        Return in 0.1ms
     │
     │──[B]→ MySQL Shard: (on cache miss)
     │        SELECT long_url FROM url_mappings
     │        WHERE short_code = 'aB3xY7z'
     │        Takes ~5ms
     │
     │──[C]→ Check expiry: expires_at > NOW()
     │
     │──[D]→ Populate Redis: SET url:aB3xY7z → longUrl
     │
     │──[E]→ Kafka: Publish click event (async)
     │        Don't wait for this!
     │
     ▼
Response: HTTP 302 Location: original-long-url.com

┌─────────────────────────────────────┐
│  🏎️ Why Redis Cache?                │
│                                     │
│  80% of traffic goes to 20% of URLs │
│  (Zipf distribution — same reason   │
│  top 10 songs get most streams)     │
│                                     │
│  That hot 20% = ~10GB of data       │
│  Fits entirely in RAM!              │
│                                     │
│  Result:                            │
│  • Cache hit: 0.1ms response        │
│  • Cache miss: 5ms (hit MySQL)      │
│  • 99% cache hit rate achieved      │
│                                     │
│  Without cache: MySQL would drown   │
│  under 115,740 queries/sec          │
└─────────────────────────────────────┘
```

### **BOTTOM: Analytics Pipeline (Async)**

```
┌─────────────────────────────────────────────────────────┐
│          Analytics Pipeline (Decoupled)                 │
└─────────────────────────────────────────────────────────┘

Kafka Topic: url.click.events
  │ (short_code, ip, country, referrer, timestamp)
  │ Buffered, not blocking redirects
  ▼
ClickHouse Consumer
  │ Bulk insert every 10 seconds
  ▼
ClickHouse Table: click_events
  │ Columnar database optimized for:
  │ • COUNT(*) GROUP BY country
  │ • Clicks per day time-series
  │ • Top referrers analysis
  ▼
Analytics Dashboard
  "Your URL had 14,203 clicks from 47 countries"

┌─────────────────────────────────────┐
│  ⚡ Why Async?                       │
│                                     │
│  Bad approach:                      │
│  1. User clicks /aB3xY7z            │
│  2. Wait for DB write to analytics  │
│  3. Then redirect (10ms+ latency)   │
│                                     │
│  Good approach:                     │
│  1. User clicks /aB3xY7z            │
│  2. Redirect immediately (0.1ms)    │
│  3. Drop event in Kafka queue       │
│  4. Process analytics later         │
│                                     │
│  User never waits for analytics!    │
└─────────────────────────────────────┘
```

---

## 🔄 **Diagram 3: Primary Sequence** (`03-primary-sequence.drawio`)

### **Current Problems**
❌ Doesn't show cache hit vs miss paths  
❌ Missing timing annotations  
❌ No clear indication of async operations  

### **What to Change**

**Draw TWO SEQUENCE FLOWS:**

### **Sequence 1: Redirect (Cache Hit — Happy Path)**

```
Browser    CDN/Edge    Redirect Service    Redis Cache    Kafka
  │            │              │                │            │
  │ GET /abc   │              │                │            │
  │───────────>│              │                │            │  ⏱️ 0ms
  │            │ (edge miss)  │                │            │
  │            │─────────────>│                │            │  ⏱️ 2ms
  │            │              │ GET url:abc123 │            │
  │            │              │───────────────>│            │  ⏱️ 2.05ms
  │            │              │<───────────────│            │
  │            │              │  [HIT: longUrl]│            │  ⏱️ 2.1ms
  │            │              │                │            │
  │            │              │ publish click  │            │
  │            │              │ (fire & forget)│            │  ⏱️ 2.11ms
  │            │              │───────────────────────────>│
  │            │              │                │            │
  │            │ 302 Location │                │            │
  │<────────────────────────  │                │            │  ⏱️ 2.15ms
  │            │  [longUrl]   │                │            │
  │            │              │                │            │
  │ Follow     │              │                │            │
  │ redirect   │              │                │            │
  │───────────────────────────────────────────>            │  ⏱️ 3ms
             (browser goes to original URL)

┌─────────────────────────────────────────────────────────┐
│  📊 Timing Breakdown (Cache Hit)                        │
│                                                         │
│  Total redirect latency: ~2.15ms                        │
│  • Network to edge: 2ms                                 │
│  • Redis lookup: 0.1ms                                  │
│  • Response: 0.05ms                                     │
│  • Kafka publish: 0.01ms (doesn't block)                │
│                                                         │
│  ✅ Meets <10ms p99 requirement easily                  │
└─────────────────────────────────────────────────────────┘
```

### **Sequence 2: Redirect (Cache Miss — Rare Path)**

```
Browser    Redirect Service    Redis    MySQL Shard    Kafka
  │              │               │           │            │
  │ GET /xyz     │               │           │            │
  │─────────────>│               │           │            │  ⏱️ 0ms
  │              │ GET url:xyz   │           │            │
  │              │──────────────>│           │            │  ⏱️ 0.1ms
  │              │<──────────────│           │            │
  │              │   [MISS]      │           │            │  ⏱️ 0.2ms
  │              │               │           │            │
  │              │ SELECT long_url WHERE short_code='xyz' │
  │              │──────────────────────────>│            │  ⏱️ 0.3ms
  │              │<──────────────────────────│            │
  │              │            [longUrl]      │            │  ⏱️ 5ms
  │              │               │           │            │
  │              │ SET url:xyz   │           │            │
  │              │──────────────>│           │            │  ⏱️ 5.1ms
  │              │               │           │            │
  │              │ publish click (async)     │            │
  │              │───────────────────────────────────────>│  ⏱️ 5.11ms
  │              │               │           │            │
  │ 302 Location │               │           │            │
  │<─────────────│               │           │            │  ⏱️ 5.2ms
  │   [longUrl]  │               │           │            │

┌─────────────────────────────────────────────────────────┐
│  📊 Timing Breakdown (Cache Miss)                       │
│                                                         │
│  Total redirect latency: ~5.2ms                         │
│  • Redis check: 0.2ms (miss)                            │
│  • MySQL query: 4.8ms                                   │
│  • Redis write: 0.1ms                                   │
│  • Response: 0.1ms                                      │
│                                                         │
│  ⚠️ Still under 10ms, but 26x slower than cache hit     │
│  → This is why 99% cache hit rate is critical!          │
└─────────────────────────────────────────────────────────┘
```

### **Add Annotations**

Label these clearly on the diagram:
- **Red dashed line** around Kafka publish: "ASYNC — doesn't block response"
- **Green highlight** on Redis hit path: "99% of requests (hot path)"
- **Yellow highlight** on MySQL query: "1% of requests (cold path)"

---

## 🗃️ **Diagram 4: Data Model** (`04-data-model.drawio`)

### **Current Problems**
❌ Doesn't show why each field exists  
❌ Missing Redis and ClickHouse schemas  
❌ No sharding visualization  

### **What to Change**

**Draw THREE SEPARATE STORAGE SYSTEMS:**

### **1. MySQL Schema (Permanent URL Mappings)**

```
┌─────────────────────────────────────────────────────────┐
│  TABLE: url_mappings (Sharded by short_code hash)       │
├──────────────────┬─────────────┬────────────────────────┤
│ Column           │ Type        │ Why it exists          │
├──────────────────┼─────────────┼────────────────────────┤
│ short_code       │ VARCHAR(10) │ PRIMARY KEY            │
│                  │             │ "aB3xY7z"              │
│                  │             │ Shard key: hash(code)  │
│                  │             │ mod 10 → shard 0-9     │
├──────────────────┼─────────────┼────────────────────────┤
│ long_url         │ TEXT(2048)  │ Destination URL        │
│                  │             │ Up to 2KB              │
├──────────────────┼─────────────┼────────────────────────┤
│ user_id          │ BIGINT      │ Who owns this URL      │
│                  │             │ (for deletion rights)  │
├──────────────────┼─────────────┼────────────────────────┤
│ created_at       │ TIMESTAMP   │ When URL was created   │
├──────────────────┼─────────────┼────────────────────────┤
│ expires_at       │ TIMESTAMP   │ NULL = never expires   │
│                  │  NULL       │ Checked on redirect    │
├──────────────────┼─────────────┼────────────────────────┤
│ is_custom_alias  │ BOOLEAN     │ TRUE if user chose     │
│                  │             │ the short code         │
├──────────────────┼─────────────┼────────────────────────┤
│ long_url_hash    │ CHAR(32)    │ MD5 of long_url        │
│                  │             │ For de-dup check:      │
│                  │             │ "Did I shorten this    │
│                  │             │  URL before?"          │
└──────────────────┴─────────────┴────────────────────────┘

INDEXES:
  PRIMARY KEY (short_code)  ← Used for redirects
  INDEX (user_id, created_at DESC)  ← "List my URLs"
  INDEX (user_id, long_url_hash)  ← De-dup lookup

┌─────────────────────────────────────────────────────────┐
│  🔍 Why long_url_hash?                                  │
│                                                         │
│  Problem: User pastes amazon.com/product/12345 twice    │
│  Bad: Create 2 different short codes (waste)            │
│  Good: Check "have I seen this before?" via hash        │
│                                                         │
│  Can't index TEXT columns (too big)                     │
│  Can index CHAR(32) hash (MD5 fingerprint)              │
│                                                         │
│  Query:                                                 │
│  SELECT short_code FROM url_mappings                    │
│  WHERE user_id = 123                                    │
│    AND long_url_hash = MD5('amazon.com...')             │
│                                                         │
│  → Instant de-dup detection!                            │
└─────────────────────────────────────────────────────────┘

SHARDING VISUALIZATION:
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Shard 0     │  │  Shard 1     │  │  Shard 9     │
│ codes ending │  │ codes ending │  │ codes ending │
│ hash(X)%10=0 │  │ hash(X)%10=1 │  │ hash(X)%10=9 │
└──────────────┘  └──────────────┘  └──────────────┘
      ↑                  ↑                  ↑
  hash("aB3xY7z") % 10 = 3 → goes to Shard 3
  
  Why hash sharding?
  • Evenly distributes data
  • Any shard can answer any query (no hot spots)
  • Viral URL's traffic spread across shards
```

### **2. Redis Schema (Hot Cache)**

```
┌─────────────────────────────────────────────────────────┐
│  REDIS: In-Memory Cache                                 │
├─────────────────────────────────────────────────────────┤
│  Key Pattern    │ Value              │ TTL             │
├─────────────────┼────────────────────┼─────────────────┤
│ url:aB3xY7z     │ "https://long.url" │ 24h (or expiry) │
│ url:xK7dQ       │ "https://other.url"│ 1h              │
├─────────────────┴────────────────────┴─────────────────┤
│                                                         │
│  Cache Strategy: LRU (Least Recently Used)              │
│  • Most clicked URLs stay in cache                      │
│  • Rarely clicked URLs get evicted                      │
│                                                         │
│  Size: ~10-20 GB (hot set of ~20M URLs)                 │
│  Hit Rate: 99%                                          │
│                                                         │
│  TTL Logic:                                             │
│  • If URL expires_at is set: TTL = expires_at - now()   │
│  • If URL never expires: TTL = 24h (refresh daily)      │
│                                                         │
│  On cache miss:                                         │
│  1. Query MySQL shard                                   │
│  2. Store result in Redis                               │
│  3. Return to user                                      │
└─────────────────────────────────────────────────────────┘
```

### **3. ClickHouse Schema (Analytics)**

```
┌─────────────────────────────────────────────────────────┐
│  CLICKHOUSE TABLE: click_events (Columnar)              │
├────────────────┬──────────────────┬─────────────────────┤
│ Column         │ Type             │ Why this type       │
├────────────────┼──────────────────┼─────────────────────┤
│ short_code     │ String           │ Partition key       │
│                │                  │ Group analytics     │
│                │                  │ per URL             │
├────────────────┼──────────────────┼─────────────────────┤
│ clicked_at     │ DateTime         │ Time-series queries │
│                │                  │ "clicks per day"    │
├────────────────┼──────────────────┼─────────────────────┤
│ country        │ LowCardinality   │ Compressed enum     │
│                │ (String)         │ ~200 countries      │
│                │                  │ saves space         │
├────────────────┼──────────────────┼─────────────────────┤
│ referrer       │ String           │ "Where did click    │
│                │                  │  come from?"        │
├────────────────┼──────────────────┼─────────────────────┤
│ user_agent     │ String           │ Browser/device      │
├────────────────┼──────────────────┼─────────────────────┤
│ ip_address     │ String (hashed)  │ Privacy-safe        │
│                │                  │ (GDPR compliance)   │
└────────────────┴──────────────────┴─────────────────────┘

PARTITION BY: toYYYYMM(clicked_at)  ← One partition per month
ORDER BY: (short_code, clicked_at)  ← Optimizes queries

EXAMPLE QUERY:
  SELECT 
    toDate(clicked_at) AS day,
    COUNT(*) AS clicks
  FROM click_events
  WHERE short_code = 'aB3xY7z'
    AND clicked_at >= '2026-08-01'
    AND clicked_at < '2026-09-01'
  GROUP BY day
  ORDER BY day;

  → Returns daily click counts for August 2026
  → Runs in <100ms on billions of rows (columnar magic)

┌─────────────────────────────────────────────────────────┐
│  🎯 Why ClickHouse, not MySQL?                          │
│                                                         │
│  MySQL (row-based):                                     │
│  Stores: [code='abc', time='10:00', country='US']       │
│           [code='abc', time='10:01', country='IN']      │
│  To count: Must read ALL columns of ALL rows            │
│  10B rows × 500 bytes = slow aggregation                │
│                                                         │
│  ClickHouse (column-based):                             │
│  Stores: country column: [US, IN, US, IN, ...]         │
│          time column: [10:00, 10:01, ...]               │
│  To count by country: Only read country column!         │
│  Compressed, sequential reads = 100x faster             │
│                                                         │
│  Perfect for: COUNT, SUM, GROUP BY queries              │
│  Bad for: Point lookups (use MySQL for that)            │
└─────────────────────────────────────────────────────────┘
```

---

## ⚙️ **Diagram 5: Scale & Failures** (`05-scale-failures.drawio`)

### **Current Problems**
❌ Doesn't show failure scenarios  
❌ Missing retry logic  
❌ No indication of circuit breakers  

### **What to Change**

**Draw FAILURE SCENARIOS and MITIGATIONS:**

### **1. Database Failure Handling**

```
SCENARIO 1: MySQL Primary Fails
────────────────────────────────

         ❌ MySQL Primary (DOWN)
              │
              │ Failover (automated)
              ▼
         ✅ MySQL Replica → Promoted to Primary
              │
              │ All writes now go here
              │
         New Replicas ← Spin up from backup

Mitigation:
• Multi-AZ deployment (primary in us-east-1a, replica in 1b)
• Automatic failover via RDS (30-60 seconds)
• Read replicas handle reads during failover
• Application uses connection pool with retry logic

Code Example (connection retry):
```java
@Retryable(
  value = {SQLException.class},
  maxAttempts = 3,
  backoff = @Backoff(delay = 100)
)
public URL saveURL(String shortCode, String longUrl) {
  // Will retry 3 times with 100ms between attempts
  return jdbcTemplate.save(...);
}
```

┌─────────────────────────────────────────────────────────┐
│  🛡️ Why Multi-AZ?                                       │
│                                                         │
│  Single-AZ: Data center loses power → ALL down          │
│  Multi-AZ: Data center fails → replica in other zone    │
│            takes over in <60 seconds                    │
│                                                         │
│  AWS Availability Zones are separate buildings          │
│  with independent power/network                         │
└─────────────────────────────────────────────────────────┘
```

### **2. Redis Cache Failure**

```
SCENARIO 2: Redis Cluster Node Fails
─────────────────────────────────────

    ┌──────┐  ┌──────┐  ┌──────┐
    │Redis │  │Redis │  │Redis │
    │ Node1│  │ Node2│  │ Node3│  ← 3-node cluster
    └──────┘  └──────┘  └──────┘
                  ❌
              (Node 2 crashes)
                  │
                  │ Auto-failover
                  ▼
    ┌──────┐           ┌──────┐
    │Node1 │           │Node3 │  ← Cluster continues
    │      │           │      │     with 2 nodes
    └──────┘           └──────┘
         │                  │
         └──────┬───────────┘
                │
         New Node ← Spin up replacement
           (Node 4)

Impact: Cache miss rate increases temporarily
        (some keys were on Node 2)
        MySQL sees more traffic (but can handle it)

Mitigation:
• Redis Cluster mode: data replicated across nodes
• Client-side fallback: on Redis error → query MySQL directly
• Monitoring: alert if cache hit rate drops below 95%

Code Example (cache fallback):
```java
public String getLongUrl(String shortCode) {
  try {
    String cached = redis.get("url:" + shortCode);
    if (cached != null) return cached;
  } catch (RedisException e) {
    log.warn("Redis unavailable, falling back to DB");
  }
  
  // Fallback to MySQL
  String longUrl = mysql.query(
    "SELECT long_url FROM url_mappings WHERE short_code = ?", 
    shortCode
  );
  return longUrl;
}
```
```

### **3. ID Generation Failure**

```
SCENARIO 3: Zookeeper Unavailable
──────────────────────────────────

Shortener Service: "I've used 999,950 of my 1M IDs,
                     need to get a new range from Zookeeper"
           │
           │ Request new range
           ▼
      ❌ Zookeeper (DOWN/slow)
      
Impact: Can still create 50 more URLs with remaining IDs
        After that, URL creation fails

Mitigation:
• Pre-allocate ranges early (when 90% used, not 100%)
• Multiple Zookeeper nodes (quorum of 3 or 5)
• Fallback: Emergency local counter (accept risk of
  collision for short period until Zookeeper recovers)

Code Example (early pre-fetch):
```java
class IDRangeManager {
  private long currentID = start;
  private long rangeEnd = end;
  
  public long getNextID() {
    currentID++;
    
    // Pre-fetch next range at 90% used
    if (currentID > rangeEnd * 0.9 && !fetchInProgress) {
      asyncFetchNextRange();  // Don't block!
    }
    
    return currentID;
  }
}
```
```

### **4. Circuit Breaker Pattern**

```
SCENARIO 4: MySQL Shard #3 Becomes Slow
────────────────────────────────────────

Redirect Service detects:
  "Queries to shard 3 timing out (>1 second)"

Circuit Breaker State Machine:
┌─────────┐  5 failures    ┌──────┐  30 sec   ┌──────────┐
│ CLOSED  │───────────────>│ OPEN │──────────>│ HALF-OPEN│
│ (normal)│                │(fail │           │(test if  │
│         │<───────────────│ fast)│<──────────│ recovered│
└─────────┘  3 successes   └──────┘           └──────────┘

When OPEN:
  • Don't send requests to shard 3
  • Return cached data only
  • Or return error: "Service temporarily unavailable"

After 30 seconds:
  • Send 1 test request (HALF-OPEN state)
  • If succeeds 3 times → CLOSED (back to normal)
  • If fails → OPEN again

┌─────────────────────────────────────────────────────────┐
│  🔄 Why Circuit Breaker?                                │
│                                                         │
│  Without it:                                            │
│  • All requests keep hitting slow DB                    │
│  • Threads pile up waiting                              │
│  • Entire service crashes from thread exhaustion        │
│                                                         │
│  With it:                                               │
│  • Detect failure fast                                  │
│  • Stop sending requests (give DB time to recover)      │
│  • Service stays alive, users get error instead of hang │
└─────────────────────────────────────────────────────────┘
```

### **5. Rate Limiting**

```
SCENARIO 5: DDoS Attack on Short URL Creation
──────────────────────────────────────────────

Attacker sends 10,000 create requests/sec
  POST /shorten {longUrl: "spam.com"}

Rate Limiter (at API Gateway):
┌──────────────────────────────────────┐
│  Token Bucket Algorithm              │
│                                      │
│  Per IP address:                     │
│  • Bucket capacity: 100 tokens       │
│  • Refill rate: 10 tokens/sec       │
│                                      │
│  Each request consumes 1 token       │
│  No tokens left → HTTP 429 Too Many  │
│                    Requests          │
└──────────────────────────────────────┘

Redis Key:
  ratelimit:{IP_ADDRESS} → {token_count, last_refill}

Code Example:
```java
public boolean allowRequest(String ipAddress) {
  String key = "ratelimit:" + ipAddress;
  long now = System.currentTimeMillis();
  
  RateLimitState state = redis.get(key);
  if (state == null) {
    state = new RateLimitState(100, now); // Full bucket
  }
  
  // Refill tokens
  long elapsed = (now - state.lastRefill) / 1000; // seconds
  state.tokens = Math.min(100, state.tokens + elapsed * 10);
  state.lastRefill = now;
  
  if (state.tokens >= 1) {
    state.tokens -= 1;
    redis.set(key, state, 60); // TTL 60 sec
    return true; // Allow request
  } else {
    return false; // Rate limited
  }
}
```

Result:
• Legitimate users: 10 requests/sec → always allowed
• Attacker: blocked after first 100 requests, throttled to 10/sec
• System protected from overload
```

---

## ✅ **Verification Checklist**

After updating all diagrams, verify:

- [ ] Diagram 1 (Context): Shows 100:1 read-to-write ratio
- [ ] Diagram 2 (HLD): Separates write path and read path visually
- [ ] Diagram 2: Includes Zookeeper, Redis, MySQL, Kafka, ClickHouse
- [ ] Diagram 2: Shows traffic volumes (1,157/sec vs 115,740/sec)
- [ ] Diagram 3 (Sequence): Shows cache hit and cache miss paths
- [ ] Diagram 3: Includes timing annotations
- [ ] Diagram 3: Marks Kafka as async (doesn't block)
- [ ] Diagram 4 (Data Model): Shows MySQL, Redis, AND ClickHouse schemas
- [ ] Diagram 4: Explains WHY each field exists
- [ ] Diagram 5 (Failures): Shows at least 3 failure scenarios with mitigations
- [ ] All diagrams: Include beginner explanation boxes
- [ ] All diagrams: Use consistent color coding (write=blue, read=green, analytics=orange)

---

## 🎨 **Visual Design Tips**

### **Color Palette (Consistency)**
```
Write Path Components:    Light Blue #ADD8E6
Read Path Components:     Light Green #90EE90
Analytics Components:     Light Orange #FFB84D
Failure States:           Light Red #FFB6C1
Cache Layers:             Light Yellow #FFFFE0
```

### **Icon Usage**
- 🔥 Hot path (high traffic)
- ❌ Failure scenarios
- ✅ Success paths
- ⚠️ Warning/edge cases
- 🧠 Key insights
- 🏎️ Performance optimizations
- 🛡️ Reliability patterns
- 🔍 Detailed explanations

### **Text Formatting**
- **Bold**: Component names, key concepts
- *Italic*: Explanatory notes, analogies
- `Monospace`: Code, URLs, commands
- UPPERCASE: Emphasis on critical points

---

## 📖 **How to Use These Diagrams in an Interview**

1. **Start with Diagram 1 (Context)**: Set expectations about read-heavy nature
2. **Draw Diagram 2 (HLD) on whiteboard**: WRITE path on left, READ path on right
3. **Deep dive with Diagram 3 (Sequence)**: Explain cache hit vs miss
4. **If asked about storage**: Show Diagram 4 (Data Model)
5. **If asked about reliability**: Discuss Diagram 5 (Failures)

**Pro tip**: Don't draw all 5 diagrams! Start with #2 (HLD), then go deeper based on interviewer's questions.

---

## 🚀 **Next Steps**

1. Open each `.drawio` file in diagrams.net
2. Apply the changes above (start with Diagram 2 - most important)
3. Save and export as PNG for quick reference
4. Practice drawing Diagram 2 on paper/whiteboard in under 5 minutes

**Remember**: These diagrams should match the clarity and beginner-friendliness of the INTERVIEW_GUIDE.md. Every component should have a "why it exists" explanation visible on the diagram!
