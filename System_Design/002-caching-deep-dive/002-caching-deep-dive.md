# SD_Q03: Caching Deep Dive — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 20-25 minutes | **Frequency:** 90% in architect rounds 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "Your product page takes 2 seconds because it queries 8 database tables. How do you bring it to 50ms?" — The caching scenario.

---

## NEW LEARNER FOUNDATION

### What is a Cache? (Plain English)
```
Cache = a fast temporary store close to the reader.

Without cache:
  User requests product page → DB query (5 tables, 2 seconds) → response
  1000 users request same page → DB runs same query 1000 times

With cache:
  First user: DB query (2 seconds) → store result in Redis → response
  Next 999 users: read from Redis (1ms) → response
  DB: runs once instead of 1000 times

Cache hit  = found in cache → fast (1ms)
Cache miss = not in cache  → go to DB, store result → slow (2s) but only once

TTL (Time To Live) = how long a cached value stays valid before auto-expiry
  Product price TTL=5min: price can be 5 minutes stale (acceptable)
  Inventory count TTL=30s: inventory must be near-real-time (flash sale)
  User session TTL=30min: session expires after 30min of inactivity
```

### What is Cache Invalidation? (Plain English)
```
"There are only two hard things in CS: cache invalidation and naming things." — Phil Karlton

Problem: you cached the product price at 12:00. Admin changes price at 12:01.
         The cache still shows the old price until TTL expires (12:05).
         Users see wrong price for 4 minutes.

Cache invalidation = proactively removing/updating stale cache entries
when the underlying data changes.

Three strategies:
  1. TTL-based: just wait for it to expire (simple, sometimes stale)
  2. Event-driven: when admin changes price → IMMEDIATELY delete/update cache key
  3. Write-through: every DB write also writes to cache (always fresh, more writes)
```

---

## BIG PICTURE — Caching Layers

```
 REQUEST PATH — MULTIPLE CACHE LAYERS
 ┌──────────────────────────────────────────────────────────────────┐
 │                                                                  │
 │  [User Browser]                                                  │
 │     │  Cache-Control: max-age=300 (browser caches 5 min)        │
 │     ▼                                                            │
 │  [CloudFront CDN]  ← Cache Layer 1                              │
 │     │  Static: HTML/JS/CSS/Images → cached at CDN edge          │
 │     │  Dynamic: /api/products/123 → usually NOT cached          │
 │     │  Cache hit ratio target: 80-90% for static                │
 │     ▼ (only dynamic API calls pass through)                     │
 │  [API Gateway / Load Balancer]                                   │
 │     ▼                                                            │
 │  [Application Pod (Spring Boot)]                                 │
 │     │  L1 Cache: local in-process (Caffeine)  ← Cache Layer 2  │
 │     │  Hot data: top 100 products, cached for 30s               │
 │     │  Sub-millisecond access, no network hop                    │
 │     │  TTL short (data changes → stale fast for multiple pods)  │
 │     │  cache MISS                                                │
 │     ▼                                                            │
 │  [Redis ElastiCache]  ← Cache Layer 3                           │
 │     │  Shared cache: all pods share same Redis                  │
 │     │  Centralized: one update invalidates for ALL pods         │
 │     │  1-5ms access                                             │
 │     │  cache MISS                                               │
 │     ▼                                                            │
 │  [Aurora PostgreSQL]  ← Source of Truth                        │
 │     │  All cache misses + writes hit DB                         │
 │     │  With good caching: DB handles 1-5% of traffic           │
 │                                                                  │
 └──────────────────────────────────────────────────────────────────┘

 CACHE INVALIDATION FLOW (when admin updates product price):
 ┌──────────────────────────────────────────────────────────────────┐
 │  Admin Service → UPDATE products SET price=999 WHERE id=123     │
 │       │                                                          │
 │       ├──► Kafka event: { type: PRODUCT_UPDATED, id: 123 }      │
 │       │                                                          │
 │       ▼                                                          │
 │  [Cache Invalidation Consumer]                                   │
 │       └──► Redis.DEL("product:123")  ← immediate invalidation   │
 │       └──► CDN API: invalidate /products/123                    │
 │                                                                  │
 │  Next request for product 123 → cache miss → DB → fresh data   │
 └──────────────────────────────────────────────────────────────────┘
```

---

## Scenario 1: The Four Caching Patterns

### Cache-Aside (Lazy Loading) — Most Common
```java
// Application manages the cache manually
public Product getProduct(Long id) {
    String key = "product:" + id;

    // Try cache first
    Product cached = redis.get(key);
    if (cached != null) return cached;      // cache HIT

    // Cache miss: load from DB
    Product product = productRepo.findById(id).orElseThrow();

    // Store in cache for next time
    redis.setex(key, 300, product);         // TTL = 5 minutes

    return product;
}

// On product update:
public void updateProduct(Product p) {
    productRepo.save(p);
    redis.del("product:" + p.getId());      // invalidate cache immediately
}

PROS: only caches what's actually requested (efficient memory use)
CONS: cache miss = two trips (cache + DB) — latency spike on first request
USE FOR: product catalog, user profiles, configuration data
```

### Write-Through — Always Fresh
```java
// Every write goes through cache AND DB simultaneously
public void updateInventory(Long productId, int newQty) {
    // Write to DB AND cache at same time
    inventoryRepo.update(productId, newQty);
    redis.setex("inventory:" + productId, 60, newQty);
}

PROS: cache always up-to-date, never stale
CONS: every write hits both DB and Redis (more latency on writes)
     caches data that may never be read (wasteful)
USE FOR: inventory counts, stock levels (must be fresh for purchase decisions)
```

### Write-Behind (Write-Back) — Deferred Writes
```
Application writes to cache ONLY.
Background process batches and flushes to DB every N seconds.

PROS: writes are ultra-fast (just Redis, no DB roundtrip)
      batch DB writes = fewer DB transactions
CONS: data loss if cache crashes before flush (not durable!)
USE FOR: view counters, like counts, non-critical metrics
         Analytics counters: INCR("views:video123") in Redis every view
         Flush to DB every 10 seconds
         If Redis crashes: we lose 10 seconds of view counts (acceptable)
```

### Refresh-Ahead — Proactive Cache Warming
```
Cache entry expires at T+5min.
At T+4min (before expiry): background job pre-fetches fresh data from DB,
updates cache proactively. Cache never actually expires!

USE FOR: hot product pages during a sale
         Top 10,000 products: refresh every 4 minutes
         Cache is always warm → never a miss on hot items
         DB load is predictable (refreshes happen on schedule, not on traffic spikes)
```

---

## Scenario 2: Cache Stampede (Thundering Herd)

### The Disaster
```
ProductDetailPage cache key: "product:iphone15" TTL=5min

FLASH SALE STARTS at 12:00:00 exactly:
  12:04:59: cache entry about to expire
  12:05:00: 50,000 concurrent users request iPhone 15
  12:05:00.001: ALL 50,000 requests get a cache miss simultaneously
  ALL 50,000 requests query the DB at the exact same moment
  DB receives 50,000 queries for the same row → query queue piles up
  DB CPU: 100% → query latency: 10+ seconds → DB crashes

This is a Cache Stampede (also called Thundering Herd).
Worst case: you're scaling UP traffic = WORSE stampedes
```

### Fix 1: Probabilistic Early Expiry (Simple, Effective)
```java
// Don't use a hard TTL. Add jitter to prevent synchronized expiry.
int ttl = 300 + ThreadLocalRandom.current().nextInt(-30, 30); // 270-330s
redis.setex("product:" + id, ttl, product);

// Different users cached the item at different times → different expiry times
// Stampede is spread over 60s instead of hitting all at once
// At any given second: only ~1/60 of the cache expires → manageable DB load
```

### Fix 2: Mutex Lock (Only One Thread Refreshes)
```java
public Product getProduct(Long id) {
    String key = "product:" + id;
    Product cached = redis.get(key);
    if (cached != null) return cached;

    // Cache miss — acquire distributed lock
    String lockKey = "lock:product:" + id;
    boolean locked = redis.set(lockKey, "1", "NX", "EX", 5); // 5s lock

    if (locked) {
        try {
            // I won the lock — I refresh the cache
            Product product = productRepo.findById(id).orElseThrow();
            redis.setex(key, 300, product);
            return product;
        } finally {
            redis.del(lockKey);
        }
    } else {
        // Another thread is refreshing. Wait briefly and retry.
        Thread.sleep(50);
        cached = redis.get(key);
        return cached != null ? cached : productRepo.findById(id).orElseThrow();
    }
}
// Only 1 thread queries DB per cache key. Others wait 50ms then hit fresh cache.
```

### Fix 3: Caffeine refreshAfterWrite (Best for Hot Data)
```java
// Local Caffeine cache: automatically refreshes before expiry
@Bean
public Cache<Long, Product> productCache() {
    return Caffeine.newBuilder()
        .maximumSize(10_000)
        .expireAfterWrite(5, MINUTES)
        .refreshAfterWrite(4, MINUTES)    // ← proactively refresh at 4min
        .build(id -> productRepo.findById(id).orElseThrow());
        // When refreshAfterWrite triggers: serves STALE value immediately
        // Background thread fetches fresh value → updates cache
        // Next request: gets fresh value
        // Result: zero cache misses, zero stampede
}
```

---

## Trap 1: Cache Penetration — Nonexistent Keys

### The Bug
```
Attacker sends requests for non-existent products:
  GET /products/99999999  (doesn't exist)
  GET /products/88888888  (doesn't exist)
  GET /products/77777777  (doesn't exist)
  ... 1 million different non-existent IDs

Cache check: miss (never cached — they don't exist)
DB query: no result (nothing to cache)
Next request for same ID: miss again (nothing was cached!)

Every single request for a non-existent key → DB query.
1 million requests × DB query = DB overload.
```

```java
// FIX 1: Cache null results
public Product getProduct(Long id) {
    String key = "product:" + id;
    String raw = redis.get(key);

    if ("NULL".equals(raw)) return null;  // cached null → don't hit DB
    if (raw != null) return deserialize(raw);

    Product product = productRepo.findById(id).orElse(null);

    if (product == null) {
        redis.setex(key, 60, "NULL");  // cache the "not found" for 60s
    } else {
        redis.setex(key, 300, serialize(product));
    }
    return product;
}

// FIX 2: Bloom filter (prevents even hitting Redis for known-bad keys)
// BloomFilter stores set of ALL valid productIds (space-efficient, probabilistic)
// Request comes in → check BloomFilter first:
// "Is this ID possibly valid?" If NO → immediately 404, no Redis/DB hit
// False positive rate ~1%: occasionally valid IDs blocked → acceptable
BloomFilter<Long> productIdFilter = BloomFilter.create(Funnels.longFunnel(), 10_000_000);
// Load all valid IDs at startup/refresh hourly
```

---

## Trap 2: CDN Caching Dynamic Pages With User-Specific Content

### The Bug
```
ProductPage includes:
  - Product details (same for everyone) ← safe to cache
  - "Add to cart" button (same for everyone) ← safe to cache
  - "Welcome back, Abhishek!" header ← SPECIFIC TO USER
  - "You have 3 items in cart" ← SPECIFIC TO USER

If CloudFront caches this page:
  User A (Abhishek) visits → page cached at CDN
  User B (Priya) visits → CDN returns Abhishek's page!
  Priya sees: "Welcome back, Abhishek!" and Abhishek's cart

This is a privacy bug AND a correctness bug.
```

```
FIX 1: Don't cache pages with user-specific content at CDN level.
  Cache only: static assets (JS, CSS, images), product data API (JSON)
  Don't cache: full HTML pages that include session data

FIX 2: Fragment caching (micro-frontends approach)
  CDN caches the PAGE SHELL (header container, product details, footer)
  Client-side JavaScript: fetch user-specific data AFTER page load
    GET /api/me → returns { name, cartCount } — not cached by CDN
    GET /api/products/123 → cached by CDN (same for all users)
  Result: fast page load (shell from CDN) + correct user data (API call)

FIX 3: Vary header (CDN caches PER user)
  Cache-Control: max-age=300
  Vary: Cookie  ← CDN caches separate versions per session cookie
  BAD IDEA: you'd have millions of cached variants (one per user)
            CDN cache size explodes, hit rate drops to near 0%
            Only makes sense for small, well-defined variants (e.g. Vary: Accept-Language)
```

---

## Interview Cheat Sheet

> "I layer caching: CDN for static assets (images, JS, CSS), Redis for shared application data, Caffeine local cache for the hottest items (avoids Redis network hop). Pattern selection: cache-aside for product catalog (lazy, efficient), write-through for inventory (must be fresh), write-behind for view counters (high-frequency writes, loss-tolerant). The most dangerous failure mode is cache stampede — when a popular key expires under load, thousands of threads simultaneously miss and hammer the DB. Fix with TTL jitter, mutex locks, or Caffeine's refreshAfterWrite. Cache penetration (attacker spamming non-existent IDs) is fixed by caching null results or a Bloom filter at the entry point."
