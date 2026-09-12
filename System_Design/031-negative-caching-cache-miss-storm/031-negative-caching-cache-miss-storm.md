# Negative Caching
### Caching "Not Found" to Stop Database Hammering on Non-Existent Keys

---

## PART 1 — THE STUDENT CONVERSATION

Imagine a spam bot hits your URL shortener with 1 million requests for random short codes — "zzz999", "abc000", "xyz123" — none of which exist.

Every request follows this path: cache miss → DB lookup → "not found" → return 404.

The cache is completely useless here, because it only stores things that exist. The "not found" answer is never cached. The DB handles 1 million lookups for non-existent data and collapses under the load.

**Negative caching** stores the "not found" result too. You cache the absence.

Next time "zzz999" is requested — and a bot will request the same codes repeatedly — the cache returns the null result immediately. The database sees nothing.

This sounds trivial but it's one of the most important cache optimizations for public-facing systems. Any API that takes user-supplied IDs is vulnerable: user IDs, product IDs, order IDs, usernames, short codes. A bot or a bug or a misconfigured client can hammer non-existent keys indefinitely.

Three defensive layers work together:
1. **Bloom filter**: probabilistic check — "definitely does not exist" → skip cache and DB entirely
2. **Negative cache**: store the "not found" answer for keys that slipped through the Bloom filter
3. **API gateway rate limiting**: cap requests per key to prevent unbounded hammering

The Bloom filter is the first line of defense. Negative caching is the second. Together they protect the database from both random and targeted non-existence attacks.

---

## PART 2 — DIAGRAMS AND ARCHITECTURE

### Without Negative Caching — Cache Miss Storm

```
Bot sends 1,000,000 requests for "zzz999" (doesn't exist in DB):

  Request 1:        Cache MISS → DB query → "not found" → return 404
  Request 2:        Cache MISS → DB query → "not found" → return 404
  Request 3:        Cache MISS → DB query → "not found" → return 404
  ...
  Request 1,000,000: Cache MISS → DB query → "not found" → return 404

DB: 1,000,000 queries for nothing.
    Each query takes 1-5ms of CPU, acquires shared locks, scans indexes.
    At 1,000 RPS, DB is fully saturated on queries that return nothing.
    Real traffic (actual URL lookups) starts failing with timeouts.

The cache is completely bypassed — it never has anything to cache.
```

### With Negative Caching

```
Bot sends 1,000,000 requests for "zzz999":

  Request 1:         Cache MISS → DB query → "not found"
                     → Cache SET "zzz999" = NULL_SENTINEL, TTL=60s
                     → return 404

  Request 2-1,000,000: Cache HIT ("zzz999" = NULL_SENTINEL)
                        → return 404 immediately
                        → DB: 0 additional queries

DB: 1 query total for 1,000,000 requests. ✓
Cache: 1 tiny entry (100 bytes), expires in 60 seconds.
```

### Three-Layer Defense Architecture

```
                    Bot Attack: 1M requests for "zzz999"
                           │
                    ┌──────▼──────┐
                    │ API Gateway │
                    │ Rate Limiter│  ← Layer 3: Block >10 req/60s for same key
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │Bloom Filter │  ← Layer 1: "zzz999" not in filter?
                    │             │    Definitely doesn't exist → 404 immediately
                    └──────┬──────┘
                           │ (passes through: false positive ~1%)
                    ┌──────▼──────┐
                    │ Redis Cache │  ← Layer 2: Check for NULL_SENTINEL
                    │             │    Cache hit (NULL) → 404 immediately
                    └──────┬──────┘
                           │ (passes through: cache miss)
                    ┌──────▼──────┐
                    │  Database   │  ← Sees ~0 queries for non-existent keys
                    └─────────────┘
```

### Code Implementation

```python
# Redis negative caching implementation

NULL_SENTINEL = "__NULL__"

def get_url(short_code: str) -> Optional[str]:
    # Layer 1: Bloom filter check
    if not bloom_filter.might_contain(short_code):
        # Definitely not in DB — skip cache and DB entirely
        return None  # 404

    # Layer 2: Cache check (positive or negative)
    cached = redis.get(f"url:{short_code}")

    if cached is None:
        # Cache miss — go to DB
        result = db.query(
            "SELECT long_url FROM urls WHERE short_code = %s",
            (short_code,)
        )

        if result is None:
            # Not in DB — store NEGATIVE cache entry
            redis.setex(f"url:{short_code}", 60, NULL_SENTINEL)
            # Short TTL: 60s. If someone creates this code soon, we'll re-check.
            return None  # 404

        else:
            # Found in DB — store POSITIVE cache entry
            redis.setex(f"url:{short_code}", 3600, result.long_url)
            bloom_filter.add(short_code)  # keep Bloom filter updated
            return result.long_url

    elif cached == NULL_SENTINEL:
        # Negative cache hit — skip DB
        return None  # 404

    else:
        # Positive cache hit
        return cached


# Creation path: invalidate negative cache when a code is created
def create_url(short_code: str, long_url: str) -> None:
    db.insert("INSERT INTO urls (short_code, long_url) VALUES (%s, %s)",
              (short_code, long_url))
    bloom_filter.add(short_code)
    # Explicitly delete negative cache entry (if it existed)
    redis.delete(f"url:{short_code}")
    # Now set positive cache
    redis.setex(f"url:{short_code}", 3600, long_url)
```

### Bloom Filter — How It Eliminates False Negatives

```
Bloom filter: probabilistic set membership check.
  "Is X in the set?" → "DEFINITELY NOT" or "PROBABLY YES"
  False negatives: IMPOSSIBLE (if X was added, it will always answer "probably yes")
  False positives: ~1% (says "probably yes" for a code that was never added)

For URL shortener:
  - Every created short code is added to the Bloom filter
  - "zzz999" not in Bloom filter? → DEFINITELY never created → 404 immediately
  - No cache lookup. No DB lookup.
  - ~1% of non-existent codes produce a false positive → pass to negative cache
  - Bloom filter for 10M codes: ~12MB of memory (1.2 bytes/element at 1% FPR)

Result:
  - 99% of non-existent code requests: blocked at Bloom filter (0 cache, 0 DB)
  - 1% (false positives): blocked at negative cache (0 DB after first miss)
  - DB: ~0 queries from non-existent code requests
```

---

## PART 3 — TTL STRATEGY AND PRODUCTION CONSIDERATIONS

### TTL Selection for Negative Cache Entries

| Use Case | Negative TTL | Positive TTL | Reasoning |
|----------|-------------|-------------|-----------|
| URL shortener | 60s | 3600s (1hr) | Short codes are occasionally created; 60s is acceptable staleness |
| User profile lookup | 30s | 1800s (30min) | Users register; can't serve "not found" for long after signup |
| Product ID lookup | 300s (5min) | 3600s (1hr) | Products are rarely added mid-session; 5min cache is fine |
| Discontinued product | 3600s (1hr) | N/A | Product permanently gone; long negative TTL is safe |
| Username existence | 30s | 900s (15min) | New signups; short negative TTL prevents post-signup 404s |

**Rule of thumb:** Negative TTL = how long you're willing to serve a stale "not found" after the key is actually created. For user-facing registration flows, use 30-60s. For static key spaces, use longer.

**Never set negative TTL = 0 (infinite):** If a user registers and your cache returns "not found" indefinitely, they'll think the signup failed and attempt it again, or call support.

### Memory Impact

```
Negative cache entries are tiny:
  Key:   "url:zzz999"        → ~20 bytes
  Value: "__NULL__"          → ~10 bytes
  Redis overhead per key:    ~60 bytes
  Total per entry:           ~90 bytes

1 million negative entries: 90MB
  → Acceptable for an 8GB Redis instance

Compare to the DB cost of NOT caching:
  1M DB queries × 2ms each = 2000 CPU-seconds = ~33 CPU-minutes of wasted work
  → 90MB of RAM is a very good trade

Set maxmemory-policy = volatile-ttl or volatile-lru so negative entries
(which have TTL) are evicted before permanent data (which has no TTL).
```

### Write Path: Cache Invalidation on Creation

```
Critical: when a key is CREATED, you MUST invalidate the negative cache entry.

Scenario without invalidation:
  t=0:   "user123" doesn't exist → cache NULL with TTL=60s
  t=30:  User registers as "user123" → DB write succeeds
  t=31:  Another request for "user123" → cache HIT (NULL) → returns 404
         User thinks signup failed. Tries again. Gets "username taken" error.
         Support ticket filed.

Correct write path:
  1. INSERT into DB
  2. redis.delete("user:user123")     ← invalidate negative cache
  3. redis.setex("user:user123", ttl, data)  ← set positive cache
  4. bloom_filter.add("user123")      ← update Bloom filter
```

### What Negative Caching Does NOT Protect Against

- **DDoS with infinite unique keys**: If the bot generates new unique keys on every request (truly random), the negative cache fills with millions of unique "not found" entries. Each entry costs ~90 bytes but more importantly each still requires one DB lookup on first miss.
  - Protection: API gateway rate limiting by IP at the ingress level. Bloom filter for the first-DB-miss cost.
- **Cache stampede on popular non-existent keys**: Many requests for the same non-existent key arrive simultaneously before the first one sets the negative cache entry. Use a distributed lock or probabilistic early refresh.
- **Data that changes rapidly**: Negative caching works best when "not found" is stable for at least the TTL. If keys are created and deleted many times per minute, negative TTL must be very short (< 5s) and the protection is limited.

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your URL shortener is being hammered by a bot trying millions of random short codes. Cache hit rate is 0% because the codes don't exist. DB is at 100% CPU. How do you fix it?"

**You (architect answer):**

> "Three-layer fix, each layer handles a different magnitude of the problem.
>
> Layer 1: Bloom filter. Every created short code is inserted into a Bloom filter on write. Incoming requests check the Bloom filter first. If the answer is 'definitely not in the set', we return 404 immediately — zero cache lookups, zero DB queries. A well-tuned Bloom filter for 10 million codes needs about 12MB of memory and has roughly 1% false positive rate. That eliminates 99% of bot traffic at essentially zero cost.
>
> Layer 2: Negative caching for the 1% Bloom filter false positives. When a code passes the Bloom filter but isn't in the DB, cache the 'not found' result in Redis with a 60-second TTL. A small sentinel value like `__NULL__`. The next request for the same code returns from cache in under a millisecond. The DB never sees a repeat query for the same non-existent code.
>
> Layer 3: API gateway rate limiting per short code. If the same non-existent code is requested more than 10 times in 60 seconds, the API gateway blocks it entirely before it even reaches the application. This handles the case where a bot hammers a small set of codes faster than the Bloom filter or cache can absorb.
>
> With these three layers: the DB load from non-existent code queries drops from 1M queries to approximately zero. The key insight about negative caching is that the cache entry is tiny — 90 bytes — but saves one full DB round-trip for every repeat miss on the same key. On a system under bot attack, that's a very good trade."

---

## PART 5 — DECISION FRAMEWORK

### When to Use Negative Caching

| Use Case | Use Negative Cache? | TTL | Notes |
|----------|-------------------|-----|-------|
| URL shortener (random code attacks) | YES | 60s | Classic use case |
| User profile by username (bot enumeration) | YES | 30s | Short TTL for signups |
| Product ID lookup (discontinued products) | YES | 5-60min | Products rarely un-discontinued |
| API key validation (invalid keys) | YES | 5min | Invalid keys are unlikely to become valid |
| Session token lookup (expired sessions) | YES | TTL = session expiry | Session expiry is deterministic |
| Financial account by ID (strict consistency) | NO | — | Stale "not found" could cause missed transfers |
| Real-time inventory (changes every second) | NO | — | TTL would be too short to help |

### Cache Null vs No Entry — Architectural Decision

```
Option A: Store sentinel value (recommended)
  redis.setex(key, 60, "__NULL__")
  Pros:  Explicit. Distinguishable from "cache miss". Easy to monitor.
  Cons:  Need to handle sentinel in all code paths.

Option B: Store empty string
  redis.setex(key, 60, "")
  Pros:  Simple.
  Cons:  Hard to distinguish from legitimate empty value.

Option C: Use a separate "not-found" keyspace
  redis.setex("notfound:" + key, 60, "1")
  Pros:  Separate TTL management. Easy to flush all negative entries.
  Cons:  Two cache lookups per request.

Recommendation: Option A. Clear intent, single lookup, easy to grep in logs.
```

---

## QUICK REFERENCE CARD

```
NEGATIVE CACHING
================
Problem: Cache bypassed for non-existent keys → DB hammered on misses.
Solution: Cache the "not found" answer with a SHORT TTL.

Implementation:
  Cache miss → DB miss → redis.setex(key, 60, "__NULL__")
  Cache hit "__NULL__" → return 404 (skip DB)
  Write path → redis.delete(key) → redis.setex(key, ttl, data)

TTL RULES
==========
Short (30-60s):  Keys may be created soon (user signup, new products).
Medium (5min):   Keys change infrequently.
Long (1hr+):     Key space is effectively static (discontinued IDs).
Never infinite:  User could register → get permanent 404 → bad UX.

THREE-LAYER DEFENSE
====================
Layer 1: Bloom filter   → "definitely not exists" → 404 immediately (0 I/O)
Layer 2: Negative cache → "not found" cached 60s (1 DB query per unique miss)
Layer 3: API gateway    → rate-limit per key > N/min → block before app layer

MEMORY COST
============
1M negative entries × 90 bytes = 90MB
vs. 1M DB queries × 2ms = 2000 CPU-seconds wasted
90MB of RAM is worth it.
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Negative caching stores the "not found" answer so that repeated lookups for the same non-existent key never reach the database.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **01 — Tiny URL** | Cache "code not found" for 60s. Combined with a Bloom filter — Bloom says "definitely not exists" → skip both cache and DB entirely. The two patterns together reduce DB load to near-zero under bot attack. |
| **05 — Social Media** | Username lookup ("does @batman exist?") — cache "not found" for 30s. Prevents hammering the user table for typos, bot enumeration, and misconfigured clients. |
| **09 — E-Commerce Platform** | Product ID lookup for discontinued or deleted products. Instead of a full DB query on every 404 request, cache "product_id_12345 = NOT_FOUND" for 5 minutes. Especially important during sales when bots probe for out-of-stock items. |

**Architect's one-liner for the interview:**
*"Cache the 'not found' answer with a short TTL — a negative cache entry costs 100 bytes but saves one full DB round-trip for every repeat miss."*
