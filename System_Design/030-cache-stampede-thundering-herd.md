# Cache Stampede / Thundering Herd
### When your cache protection mechanism becomes the source of your outage

---

## PART 1 — THE STUDENT CONVERSATION

Imagine a famous concert. Taylor Swift announces tickets go on sale at exactly midnight. Her website has a homepage banner: "TICKETS ON SALE AT MIDNIGHT!" — and this banner is cached for 5 minutes to save DB load.

At 11:59:55 PM, the cache was last populated. It will expire at 12:04:55 AM.

But at exactly 12:00:00 AM, 100,000 fans are refreshing the page. The cache is still valid — they all get served from cache. Good.

Now imagine the cache was set to expire at exactly midnight instead. 100,000 users refresh at 12:00:00 AM. The cache is gone. All 100,000 requests simultaneously find a cache miss. All 100,000 simultaneously fire a query to the database to recompute the banner.

The database gets 100,000 identical queries in the same second.

The database buckles. The banner page errors. Fans can't load the site. Tickets don't sell.

**That is a cache stampede.** Also called a thundering herd. The very mechanism you built to protect the database has, through a single expiry event, delivered a blow the database couldn't survive.

It is not a hypothetical. It happens to real systems:
- Reddit went down when their trending posts cache expired under load.
- Facebook described thundering herd in their Memcached at scale paper.
- Every major on-sale moment (concert tickets, sneaker drops, limited product launches) is a stampede risk.

The dangerous characteristic: **your system is most vulnerable at peak traffic, which is exactly when stampedes are most likely.** A cache miss at 2 AM with 10 users is fine. A cache miss at the moment of peak load is fatal.

---

## PART 2 — DIAGRAMS

### The Problem: Cache Expiry Under Load

```
Timeline:

T=0:00    Cache populated (leaderboard computed, TTL=3600s)
          1,000 req/s → all served from cache ✓

T=1:00:00 Cache expires
          │
          ▼
T=1:00:00 50,000 simultaneous requests arrive
          │
          ├── Request 1:  cache.get("leaderboard") → NULL (miss) → fires DB query
          ├── Request 2:  cache.get("leaderboard") → NULL (miss) → fires DB query
          ├── Request 3:  cache.get("leaderboard") → NULL (miss) → fires DB query
          ├── ...
          └── Request 50,000: cache.get("leaderboard") → NULL → fires DB query

          DB receives 50,000 identical queries in <1 second
          DB CPU: 100% │ DB connections: maxed │ DB response time: 30s+
          │
          ▼
          All 50,000 users: timeout / 500 error
```

---

### Solution 1 — Mutex Lock (Serialized Recomputation)

```
T=1:00:00 Cache expires. 50,000 requests arrive simultaneously.

Request 1:
  cache.get("leaderboard") → NULL (miss)
  redis.setnx("lock:leaderboard", "1") → SUCCESS (got the lock)
  → fires DB query
  → populates cache
  → releases lock

Requests 2-49,999:
  cache.get("leaderboard") → NULL (miss)
  redis.setnx("lock:leaderboard", "1") → FAIL (lock held)
  → sleep 100ms → retry
  → cache.get("leaderboard") → HIT (populated by Request 1)
  → return cached value

Result: DB receives exactly 1 query.
        49,999 other requests wait ~100-200ms then get cache hit.

Tradeoff: All 49,999 requests have added latency.
          If Request 1 crashes mid-query, lock hangs until TTL expires.
```

---

### Solution 2 — Probabilistic Early Expiry (PER)

```
Concept: Proactively refresh the cache BEFORE it expires,
         using randomness to spread the recompute load.

Each cache entry stores: value + creation_time + original_ttl

On every read, check:
  remaining_ttl = (creation_time + original_ttl) - current_time
  recompute_now = (-delta × beta × log(random())) > remaining_ttl

  delta  = time to recompute (e.g., 0.1s)
  beta   = tuning constant (typically 1.0)
  random = uniform random between 0 and 1

Timeline:
  TTL=3600s. At T=3550s (50s before expiry):
  Some fraction of requests probabilistically decide to recompute.
  
  T=3550s: 1 in 500 requests triggers early recompute → refreshes cache
  T=3560s: 1 in 200 requests triggers early recompute → may refresh again
  T=3590s: 1 in 50 requests triggers early recompute
  T=3600s: Cache never actually expires in practice because it was
           already refreshed seconds earlier.

  No single thundering moment. Recomputes are spread across time.
  DB receives 1-2 queries per hour instead of 50,000 in 1 second.
```

---

### Solution 3 — Stale-While-Revalidate (Two-TTL Strategy)

```
Cache entry has TWO TTLs:
  soft_ttl = 300s  (5 min): "data is fresh"
  hard_ttl = 600s  (10 min): "data must be discarded"

Timeline:

T=0:00   Cache populated. soft_ttl=300, hard_ttl=600.

T=0:00 to T=5:00  (Fresh zone)
  Any request: cache.get() → "fresh" → return immediately

T=5:00 to T=10:00  (Stale-but-valid zone)
  First request that arrives: gets stale value + triggers ASYNC recompute
  All other requests in this window: get stale value immediately (no wait!)
  Background thread: queries DB → repopulates cache with fresh value

T=10:00  (Hard expiry)
  If async recompute failed for some reason:
  cache.get() → NULL → synchronous recompute (one request waits)

Result:
  Users between T=5:00 and T=5:02 get data that is max 5min stale.
  DB receives exactly 1 query per cache refresh cycle.
  No user experiences added latency.
```

---

## PART 3 — IMPLEMENTATION

### Solution 1: Mutex Lock in Java with Redis

```java
public String getWithMutex(Jedis redis, String key, int ttl) throws InterruptedException {
    // Try cache first
    String value = redis.get(key);
    if (value != null) return value;

    // Cache miss — try to acquire lock
    String lockKey = "lock:" + key;
    String lockValue = UUID.randomUUID().toString(); // unique value to prevent accidental release

    // SET lock NX EX 30 — atomic: set only if not exists, with 30s expiry
    String result = redis.set(lockKey, lockValue, SetParams.setParams().nx().ex(30));

    if ("OK".equals(result)) {
        // We got the lock — we are responsible for recomputing
        try {
            value = db.query(key);                    // expensive operation
            redis.setex(key, ttl, value);             // populate cache
        } finally {
            // Release lock only if we own it (Lua script for atomicity)
            String luaScript = "if redis.call('get', KEYS[1]) == ARGV[1] then " +
                               "return redis.call('del', KEYS[1]) else return 0 end";
            redis.eval(luaScript, 1, lockKey, lockValue);
        }
    } else {
        // Lock held by another request — wait and retry
        Thread.sleep(100);
        value = redis.get(key);  // should now be populated
        if (value == null) {
            // Still null (e.g., original request crashed) — fall back to DB
            value = db.query(key);
        }
    }
    return value;
}
```

**Key details:**
- Lock TTL (30s) prevents deadlock if the lock holder crashes.
- Lua script ensures atomic check-and-delete (you only release the lock you own).
- UUID per lock prevents one request from releasing another's lock after a timeout.

---

### Solution 2: Probabilistic Early Expiry in Java

```java
// When storing in cache, include metadata
public void setWithPER(Jedis redis, String key, String value,
                        int ttlSeconds, double delta) {
    CacheEntry entry = new CacheEntry(
        value,
        System.currentTimeMillis() / 1000L,   // creation_time (epoch seconds)
        ttlSeconds
    );
    redis.setex(key, ttlSeconds, serialize(entry));
}

// When reading from cache
public String getWithPER(Jedis redis, String key, int ttlSeconds, double delta) {
    String raw = redis.get(key);
    if (raw == null) {
        return recomputeAndStore(redis, key, ttlSeconds, delta);
    }

    CacheEntry entry = deserialize(raw);
    long now = System.currentTimeMillis() / 1000L;
    long age = now - entry.creationTime;
    long remaining = entry.ttl - age;

    // Probabilistic check: should we recompute early?
    double recomputeTime = delta * 1.0 * Math.log(Math.random());
    // recomputeTime is negative (log of value < 1 is negative)
    // As remaining TTL shrinks, more requests will trigger early recompute
    if (-recomputeTime > remaining) {
        // Trigger background recompute
        CompletableFuture.runAsync(() ->
            recomputeAndStore(redis, key, ttlSeconds, delta)
        );
    }
    return entry.value;  // return current value immediately regardless
}

// Typical values: delta=0.1 (100ms recompute time), beta=1.0
// With TTL=3600s: recomputes start ~30-60s before expiry
```

---

### Solution 3: Stale-While-Revalidate in Spring Boot

```java
@Service
public class LeaderboardService {

    private static final int SOFT_TTL_SECONDS = 300;   // 5 min: "fresh"
    private static final int HARD_TTL_SECONDS = 600;   // 10 min: absolute max
    private final Set<String> refreshInProgress = ConcurrentHashMap.newKeySet();

    public String getLeaderboard(Jedis redis) {
        String raw = redis.get("leaderboard");

        if (raw == null) {
            // Hard expiry: synchronous recompute (rare case)
            return recomputeSync(redis);
        }

        CacheEntry entry = deserialize(raw);
        long age = (System.currentTimeMillis() / 1000L) - entry.creationTime;

        if (age > SOFT_TTL_SECONDS) {
            // Stale zone: trigger async refresh if not already in progress
            if (refreshInProgress.add("leaderboard")) {
                CompletableFuture.runAsync(() -> {
                    try {
                        String fresh = db.computeLeaderboard();
                        CacheEntry newEntry = new CacheEntry(fresh,
                            System.currentTimeMillis() / 1000L, SOFT_TTL_SECONDS);
                        redis.setex("leaderboard", HARD_TTL_SECONDS, serialize(newEntry));
                    } finally {
                        refreshInProgress.remove("leaderboard");
                    }
                });
            }
            // Return stale data immediately — user gets slightly old leaderboard
        }

        return entry.value;  // Fresh or stale — always return something immediately
    }
}
```

---

### Pre-Warming (Scheduled Content)

For predictable high-traffic moments (ticket sales, product launches), pre-warm the cache before the event:

```java
// Cron job: runs 60 seconds before every scheduled sale
@Scheduled(cron = "0 59 * * * *")  // runs at XX:59:00 every hour
public void preWarmEventCache() {
    List<String> upcomingSaleIds = eventService.getSaleStartingAt(
        LocalDateTime.now().plusMinutes(1)
    );
    for (String saleId : upcomingSaleIds) {
        String data = db.computeSalePageData(saleId);
        redis.setex("sale:" + saleId, 7200, data);  // 2 hour TTL
        log.info("Pre-warmed cache for sale: " + saleId);
    }
}
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your leaderboard's Redis cache expires every hour. At exactly the top of the hour, 50,000 users request the leaderboard. What happens and how do you prevent it?"

**You (architect answer):**

> "What happens is a classic cache stampede. All 50,000 requests find a cache miss at exactly the same moment. They simultaneously fire queries to the database to recompute the leaderboard — which might take several seconds to compute, especially if it's joining across millions of rows. The DB receives 50,000 identical expensive queries in under a second. CPU spikes to 100%, connection pool exhausts, and all 50,000 users get a timeout. This is actually more dangerous the more popular your system is.

> The right fix depends on how much staleness I can tolerate. For a gaming leaderboard updated every minute, I'd use stale-while-revalidate with a two-TTL design. The soft TTL is 5 minutes — within that window, data is 'fresh' and served directly. After 5 minutes (but before the 10-minute hard TTL), I return the stale data immediately AND trigger a single async background refresh. Users see a leaderboard that's at most 5 minutes old, and the DB receives exactly one query per refresh cycle regardless of traffic.

> If freshness is critical — say it's a financial leaderboard where showing yesterday's rank is unacceptable — I'd use probabilistic early expiry. I store the creation time alongside the cached value. On each read, I run a calculation: if minus-delta times beta times log of a random number is greater than the remaining TTL, recompute now. As the TTL approaches zero, progressively more requests trigger early recompute. The cache gets refreshed seconds before it would expire, so the expiry moment never arrives with a full stampede. You get 1-2 DB queries per hour instead of 50,000 in one second.

> The third option — mutex lock — works but introduces latency: all 49,999 non-lock-holders sleep and retry. For a leaderboard with 50,000 concurrent users, that's 49,999 requests adding 100ms of artificial wait. I'd use mutex lock only for low-traffic cases or when I absolutely cannot tolerate stale data.

> I'd also add TTL jitter at the outset. If I have 10 different leaderboards (regional, global, game-type), I don't set them all to expire at exactly 3600 seconds. I set 3600 + random(0, 300) so they don't all expire in the same second."

---

## PART 5 — DECISION FRAMEWORK

### Which Prevention Strategy for Which Scenario?

| Scenario | Best Strategy | Why |
|----------|---------------|-----|
| Low traffic site, simple data | **Mutex Lock** | Simple to implement; added wait latency is acceptable at low concurrency |
| High traffic, staleness tolerable (leaderboards, trending, feeds) | **Stale-While-Revalidate** | Users get instant response always; DB sees 1 query per cycle regardless of traffic |
| High traffic, freshness critical (prices, live scores) | **Probabilistic Early Expiry** | Spreads recomputes before expiry; no stale window; no lock contention |
| Predictable traffic spike (product launches, ticket sales) | **Pre-Warming** | Know in advance when spike will happen; populate cache before it arrives |
| Multiple keys expiring simultaneously | **TTL Jitter** | Add random(0, N) seconds to TTL at write time; staggers expiry across time |

### Decision Tree

```
Is the traffic spike predictable (scheduled sale, event launch)?
  YES → Pre-Warm cache 60s before the event (cron job)
  NO ↓

Can users tolerate slightly stale data (seconds to minutes)?
  YES → Stale-While-Revalidate
        (serve stale immediately + async refresh in background)
  NO ↓

Is concurrency very high (>10K simultaneous requests)?
  YES → Probabilistic Early Expiry
        (spread recomputes randomly before expiry moment)
  NO → Mutex Lock
       (simple, but adds wait latency for non-lock-holders)

Always add: TTL jitter on write to prevent synchronized expiry
```

---

## QUICK REFERENCE CARD

```java
// MUTEX LOCK (Redis SET NX EX)
String lock = redis.set("lock:"+key, uuid, SetParams.setParams().nx().ex(30));
if ("OK".equals(lock)) {
    value = db.query(key);
    redis.setex(key, 300, value);
    redis.eval(releaseLuaScript, 1, "lock:"+key, uuid);
} else {
    Thread.sleep(100);
    value = redis.get(key);  // retry after lock holder populates
}

// STALE-WHILE-REVALIDATE (two TTL)
// Store: {value, created_at} with hard TTL=600
// On read: age > soft_ttl (300)? → serve stale + async refresh
// age > hard_ttl (600)? → synchronous recompute

// PROBABILISTIC EARLY EXPIRY
// On read: if (-delta * beta * log(random())) > remaining_ttl → recompute now
// Typical: delta=0.1 (100ms compute time), beta=1.0

// TTL JITTER (prevent synchronized expiry)
int ttl = BASE_TTL + ThreadLocalRandom.current().nextInt(0, 60);
redis.setex(key, ttl, value);

// PRE-WARM (before scheduled high-traffic moment)
// Cron: 60s before event → db.compute() → redis.setex(key, 7200, value)
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Cache expiry under high concurrent load is one of the most common causes of production outages — understanding stampede prevention separates engineers who have been on-call from those who haven't.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **05 — Social Media** | Trending topics cache expires → all users simultaneously recompute trending hashtags. Stale-while-revalidate solves it: users see trending from 30s ago while background thread recomputes. Trending being 30s stale is acceptable. |
| **09 — E-Commerce** | Product detail cache expires during Black Friday peak. Mutex lock prevents 10K simultaneous recomputes for the same product. At scale with 10K products, combine with TTL jitter so not all products expire simultaneously. |
| **11 — Ticket Booking** | Seat availability cache set to expire exactly when the sale starts (the worst possible time). Pre-warm: a cron job runs 60 seconds before every scheduled sale start, populates the cache so the expiry moment never coincides with peak traffic. |
| **17 — OTT Platform** | "Top 10 Trending Shows" cache expires at midnight when 1M late-night viewers are watching. Probabilistic early expiry starts refreshing the trending list 10 minutes before midnight, so no single stampede moment occurs. |

**Architect's one-liner for the interview:**
*"A cache stampede is when your protection mechanism delivers the fatal blow — the solution is to ensure your cache never actually expires during peak load by proactively refreshing it before it does."*
