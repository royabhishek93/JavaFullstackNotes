# Cache Strategies: Cache-Aside vs Write-Through vs Write-Behind
### How your app keeps the cache in sync with the database — and what breaks when it doesn't

---

## PART 1 — THE STUDENT CONVERSATION

Imagine a restaurant. You're the waiter. The kitchen (database) has the full menu with current prices and availability. You carry a small notepad (cache) to avoid running to the kitchen every time a customer asks a question.

**Three strategies for keeping your notepad in sync with the kitchen:**

---

**Cache-Aside (Lazy Loading)**

A customer asks: "Is the salmon available?"

1. You check your notepad — it's not there (cache miss).
2. You run to the kitchen and ask.
3. You write the answer in your notepad.
4. You tell the customer.

Next customer asks the same question:
1. You check your notepad — it's there (cache hit)!
2. You answer immediately without bothering the kitchen.

When the kitchen runs out of salmon and updates the menu, you don't automatically update your notepad. You either wait until the note expires (TTL) or someone explicitly tells you to cross it out (invalidation). There's a window where your notepad is wrong.

**Key insight:** The cache only gets populated when someone asks for something. On first ask: slow. On repeat ask: fast. But the cache can be stale.

---

**Write-Through**

The kitchen rule: "Any time we update the menu, the waiter's notepad must be updated simultaneously."

A customer orders, and the kitchen marks salmon as "sold out":
1. Kitchen updates its menu (DB write).
2. Kitchen ALSO tells you to update your notepad (cache write).
3. Both happen before you confirm to the customer.

Your notepad is always fresh. But every single write now takes longer because you must update two places.

**Key insight:** No stale data. No cache misses after the first write. But every write is slower, and at cold start (brand new cache) the notepad is empty until the first writes arrive.

---

**Write-Behind (Write-Back)**

The kitchen rule: "Update your notepad immediately, then batch-update the kitchen menu later."

A customer orders:
1. You update your notepad immediately.
2. You tell the customer "done!" right away.
3. Every few seconds, you batch-send all notepad updates to the kitchen.

Lightning-fast responses. But if you drop your notepad before the kitchen gets updated — that data is gone forever.

**Key insight:** Fastest writes. Best for high write-volume workloads. But durability risk: if the cache crashes before the async write, you lose data.

---

**The fourth pattern worth knowing: Read-Through**

Same as cache-aside from the application's perspective, except the cache itself (not your app code) is responsible for fetching from the DB on a miss. The app always talks to the cache. The cache manages the DB relationship. Redis doesn't natively support this — it's typically a caching layer like AWS ElastiCache with a custom read-through provider, or a library like NCache.

---

## PART 2 — READ PATH AND WRITE PATH DIAGRAMS

### Cache-Aside

**READ PATH:**
```
Client
  │
  ▼
Application
  │
  ├──► Cache.get(key)
  │         │
  │    HIT ─┘   ──────────────────────────► return cached value
  │
  │    MISS
  │         │
  ▼         ▼
     Database.query(key)
         │
         ▼
     Application writes to Cache
     cache.set(key, value, TTL=300s)
         │
         ▼
     return value to client
```

**WRITE PATH:**
```
Client
  │
  ▼
Application
  │
  ├──► Database.write(key, newValue)   ← write to DB first
  │
  └──► Cache.delete(key)               ← INVALIDATE (don't update)
       OR                               ← let TTL expire naturally
       Cache.set(key, newValue, TTL)    ← update (risky: see Part 3)

       return 200 OK
```

---

### Write-Through

**READ PATH:**
```
Client
  │
  ▼
Application
  │
  └──► Cache.get(key)
            │
       HIT ─┘  ──────────────────────────► return cached value
       (Write-through guarantees no cold misses after first write)
       (Cold start: first read is still a miss until first write)
```

**WRITE PATH:**
```
Client
  │
  ▼
Application
  │
  ├──► Cache.set(key, newValue, TTL)   ┐
  │                                    ├── Both must succeed
  └──► Database.write(key, newValue)   ┘

  return 200 OK to client
  (slower — two synchronous writes)
```

---

### Write-Behind (Write-Back)

**WRITE PATH:**
```
Client
  │
  ▼
Application
  │
  └──► Cache.set(key, newValue)   ──► return 200 OK immediately
            │
            │  (async, buffered)
            ▼
       Write Buffer / Queue
            │
            │  every 1-5 seconds (or batch threshold)
            ▼
       Database.batchWrite(buffered_changes)

       ⚠ If cache crashes between step 1 and DB write → DATA LOST
```

---

### Side-by-Side Summary

```
                  CACHE-ASIDE    WRITE-THROUGH    WRITE-BEHIND
Read latency:     Slow on miss   Always fast      Always fast
Write latency:    Fast           Slow (2x writes) Fastest (async)
Cache freshness:  Can be stale   Always fresh     Fresh (not yet in DB)
Durability risk:  Low            Low              HIGH
Complexity:       Low            Low              High (need WAL/AOF)
Best for:         Read-heavy     Read+write       Write-heavy
                  workloads      balanced         burst workloads
```

---

## PART 3 — PRODUCTION INTERNALS

### The Double-Write Consistency Problem (Cache-Aside Write Path)

When writing in cache-aside, you face an ordering dilemma:

**Option A: Write DB first, then update cache**
```
1. DB.write(key, newValue)     ← succeeds
2. Cache.set(key, newValue)    ← fails (Redis timeout, OOM, network)
Result: DB has new value. Cache has OLD value. Stale cache!
```

**Option B: Write cache first, then write DB**
```
1. Cache.set(key, newValue)    ← succeeds
2. DB.write(key, newValue)     ← fails (DB down, timeout, violation)
Result: Cache has new value. DB has OLD value. Inconsistency!
```

**Production best practice: Write DB first, then INVALIDATE (delete) the cache key — never update it.**
```java
// DO THIS:
db.write(key, newValue);
cache.delete(key);  // next read will miss + repopulate from DB

// NOT THIS:
db.write(key, newValue);
cache.set(key, newValue);  // what if these race with another writer?
```

Why invalidate instead of update? Cache invalidation is idempotent and safe. If the delete fails, the worst outcome is a stale cache entry that expires via TTL. If the update races with another write, you can end up with permanently wrong data.

---

### Cache Stampede on First Miss (Cache-Aside weakness)

If 10,000 concurrent requests all miss the cache at the same moment (cache cold start or TTL expiry):
- All 10,000 hit the DB simultaneously
- DB gets 10,000 queries for the same data
- DB slows or crashes

Write-through **prevents** this — the cache is populated on every write, so misses only happen at cold start before any writes have occurred.

Cache-aside **solutions:**
1. Mutex lock: first requester holds lock, others wait (see File 5)
2. Pre-warming: populate cache at deploy time before traffic arrives
3. Staggered TTLs: add jitter (random 0-60s) to TTL so not all keys expire simultaneously

---

### Write-Behind Durability: Redis AOF Persistence

Redis is an in-memory store. By default, if Redis crashes, all data in write-behind buffer is lost before the async DB write completes.

**Mitigation: Redis AOF (Append-Only File)**
```
# redis.conf
appendonly yes
appendfsync everysec   # flush to disk every second (1s max data loss)
# appendfsync always   # flush every write (zero data loss, ~50% slower)
# appendfsync no       # OS decides (fastest, most data loss risk)
```

AOF logs every write operation to disk. On restart, Redis replays the AOF to rebuild state. With `appendfsync everysec`, you risk at most 1 second of write-behind buffer loss.

---

### TTL Strategy: The Freshness vs Load Tradeoff

```
Short TTL (e.g., 30s):
  + Low staleness risk
  + Cache always fairly fresh
  - More DB hits (cache expires frequently)
  - More stampede risk

Long TTL (e.g., 1 hour):
  + DB load minimized
  + Fewer stampedes
  - Data can be stale for up to 1 hour
  - User sees outdated prices, inventory, etc.

Production pattern: Use long TTL + explicit invalidation on write
  - TTL = 1 hour (safety net for missed invalidations)
  - Explicit cache.delete(key) on every write (correctness)
  - Best of both worlds
```

---

### Read-Through vs Cache-Aside: What's the Difference?

```
Cache-Aside:
  App code: if (cache.miss) { val = db.read(); cache.set(val); }
  App is responsible for DB lookup on miss

Read-Through:
  App code: val = cache.get(key);  // always call cache
  Cache is responsible for DB lookup on miss
  App never talks to DB directly

In practice: Read-through is an architectural pattern.
Cache-aside is the specific implementation most engineers write.
Redis doesn't natively support read-through — you need a caching library
(e.g., AWS DAX for DynamoDB, NCache, Ehcache) that wraps the DB.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your product page has a 5-second load time under Black Friday load. The DB is being hammered with product queries. How do you use caching to fix this?"

**You (architect answer):**

> "First, I'd profile which queries are the hot spots. Product detail pages — name, description, images, base price — are read thousands of times per second but change at most a few times a day. That's a perfect cache-aside candidate. I'd add Redis with a 5-minute TTL on product metadata. On every product page load, the app checks Redis first. On a miss, it queries Postgres and populates the cache. After the first request per product, all subsequent reads go to Redis, not Postgres. That alone should drop DB query volume by 90%+ for product reads.

> Now, for price and inventory — those are trickier. Showing a customer a stale price is a business problem: they add to cart at $99, the real price is $149. So for price and inventory, I'd use write-through caching. Every time the price is updated in the DB (by an admin or pricing engine), we also update the Redis cache. This guarantees the cache always has the latest price. The write is slightly slower — two synchronous writes — but acceptable for the write frequency.

> For the shopping cart itself, I'd use write-behind. Cart updates are extremely write-heavy (every item add, quantity change, coupon apply). The user doesn't need the DB to be updated before they see confirmation. I'd write to Redis immediately and async-persist to Postgres every few seconds. I'd enable Redis AOF persistence to limit data loss to at most 1 second if Redis crashes.

> The last concern is cache stampede. On Black Friday, we'll have 100,000 users hitting the site at once. If a product cache entry expires at exactly 9:00 AM, all 100K users miss simultaneously and hammer Postgres. I'd mitigate this by pre-warming the cache for the top 1,000 products before the sale starts, and adding random jitter to TTLs so not all entries expire at the same second."

---

## PART 5 — DECISION FRAMEWORK

### Which Caching Strategy Should You Use?

| Dimension | Cache-Aside | Write-Through | Write-Behind |
|-----------|------------|---------------|--------------|
| **Read frequency** | High | High | Any |
| **Write frequency** | Low-medium | Low-medium | High (bursts) |
| **Staleness tolerance** | Minutes OK | Zero (always fresh) | Seconds OK |
| **Durability requirement** | High | High | Medium (AOF helps) |
| **Cold start problem** | Yes (first miss is slow) | Yes (empty until first write) | No |
| **Implementation complexity** | Low | Low | High |
| **Cache miss behavior** | App fetches from DB | Rare (only cold start) | N/A |
| **Write latency** | Fast (1 write) | Slow (2 sync writes) | Fastest (async) |
| **Best use case** | Product details, user profiles | Prices, inventory counts | Shopping carts, counters, session data |

### Decision Tree

```
Is data write-heavy (many writes per second)?
  YES → Write-Behind (async DB sync, AOF for durability)
  NO ↓

Is stale data ever acceptable?
  NO (prices, inventory, account balance) → Write-Through
  YES (product description, user bio, menu items) ↓

Is the DB lookup on cache miss acceptable latency?
  YES → Cache-Aside (simplest, most common)
  NO → Consider Read-Through with pre-warming
```

---

## QUICK REFERENCE CARD

```
# Cache-Aside (most common pattern)
# READ
value = redis.get(key)
if value is None:
    value = db.query(key)
    redis.setex(key, ttl=300, value=value)
return value

# WRITE (invalidate, don't update)
db.write(key, new_value)
redis.delete(key)   # NOT redis.set() — avoids race conditions

# Write-Through
# WRITE (both sync)
redis.setex(key, ttl=3600, value=new_value)
db.write(key, new_value)
# Both must succeed — use try/catch with rollback strategy

# Write-Behind
# WRITE (async DB)
redis.setex(key, ttl=3600, value=new_value)
write_queue.push({"key": key, "value": new_value})   # async consumer writes to DB
return 200  # immediately

# Redis AOF for write-behind durability
# redis.conf: appendonly yes | appendfsync everysec

# TTL with jitter (anti-stampede)
base_ttl = 300
jitter = random.randint(0, 60)
redis.setex(key, ttl=base_ttl + jitter, value=value)
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Every system that has a database and handles more than moderate traffic needs a caching strategy — knowing which strategy to recommend and why separates junior from senior answers.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **05 — Social Media** | User profile data: cache-aside (invalidate on profile edit). Post content: cache-aside with 5-min TTL. Feed fan-out: write-through so that when a celebrity posts, all follower caches are updated synchronously. |
| **08 — Food Delivery** | Restaurant menu cache: cache-aside with 5-min TTL. Menus change infrequently (maybe twice a day) but are read thousands of times per hour. Cache-aside keeps DB load minimal while tolerating 5-min staleness. |
| **09 — E-Commerce** | Product details (name, description, images): cache-aside. Price and inventory: write-through — stale price shown to customer creates order disputes. Shopping cart: write-behind — high write frequency per session, async DB persist is acceptable. |
| **12 — Hotel Booking** | Hotel availability (rooms left): cache-aside with short TTL + explicit invalidation on booking. Hotel metadata (name, address, photos): write-through — changes infrequently, always want fresh data for search results, and write cost is low. |

**Architect's one-liner for the interview:**
*"Cache-aside for read-heavy data where staleness is tolerable, write-through when you can never show stale data, and write-behind when your write volume outpaces what your DB can synchronously absorb."*
