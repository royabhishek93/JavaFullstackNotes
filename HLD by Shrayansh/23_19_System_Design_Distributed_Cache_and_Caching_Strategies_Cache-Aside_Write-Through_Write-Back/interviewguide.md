# Interview Guide: Distributed Cache & Caching Strategies (Cache-Aside, Read-Through, Write-Around, Write-Through, Write-Back)

## 🗣️ The Interview Scenario

> "Your application has a read-heavy endpoint backed by a database, and you've added a cache in front of it. Walk me through what happens on a cache miss versus a cache hit. Then: a write comes in and updates the DB — does the cache automatically know about it? What caching strategy would you use to keep them in sync, and what's the tradeoff of that strategy versus just letting stale reads happen occasionally? Finally, how would you scale this cache across multiple app servers without a single cache instance becoming a single point of failure?"

This is one of the most-asked HLD questions because almost every real system has a cache, and the interviewer is really testing whether you understand the **consistency vs. performance tradeoff** behind each strategy — not just that "caching makes things faster."

## 🏗️ Architect's Explanation (For a New Developer)

Caching is simple at heart: **store frequently-used data in a fast-access memory (like RAM) instead of always hitting a slow-access source (like a hard disk or a database)**. This makes reads faster (lower latency) and, in some strategies, even makes your system more fault-tolerant — if the primary data store goes down temporarily, the cache can still serve some requests.

Caching shows up at every layer of a system: browser caches (so you don't reload the same webpage assets), CDN caches (serving static content from a location near the user), load-balancer-level caches, and — the focus of this guide — **server-side application caching** (e.g., Redis) sitting between your application servers and your database.

The mental model:
```
Client → Load Balancer → App Server → [Cache] → Database
```
Before the app server queries the database directly, it first asks the cache: "do you already have this?" If yes (**cache hit**), it returns instantly. If no (**cache miss**), it falls through to the database, and — depending on the strategy — may then populate the cache for next time.

There isn't one "correct" strategy — there are **five named strategies**, each solving a different problem (read performance, write performance, consistency, or fault tolerance), and production systems often **combine two of them** (one for reads, one for writes) rather than picking just one.

## 📊 Visualize It

**Cache-Aside — the most common pattern, read path + the "write does nothing to cache" write path:**

```
READ PATH:
  Client ──GET──► App ──check──► Cache
                          │
                 ┌────────┴────────┐
              HIT│                 │MISS
                 ▼                 ▼
          return cached value   App reads DB → App WRITES result into Cache → return value

WRITE PATH (plain Cache-Aside, no special write handling):
  Client ──PUT/POST(new value)──► App ──writes──► DB   (cache is NOT touched!)
       ⚠ Cache may now hold STALE data if this key was already cached
```

**Write-Back (Write-Behind) — decoupling the write from the DB via a queue:**

```
Client ──POST──► App ──writes──► Cache (fast, immediate success response)
                          │
                          └──► pushes message ──► Queue ──(async, later)──► DB

FAILURE MODE:
  Cache TTL = 3 hours, DB down for 5 hours
  → after 3 hours, cached value evicted, but Queue STILL hasn't written to DB
  → data is now unavailable in BOTH cache and DB until DB recovers and queue drains
```

## Choosing a Strategy (Decision Flowchart)

```text
Choose a caching strategy
|
+-- Read-heavy?
|     |
|     +-- App code owns miss-handling         --> Cache-Aside (Lazy Loading)
|     |
|     +-- Caching library owns miss-handling  --> Read-Through
|
+-- Write-heavy or write+read combo?
      |
      +-- Must stay consistent, only needs invalidation (not re-population)
      |      --> Write-Around (pair with Cache-Aside/Read-Through)
      |
      +-- Must stay consistent, can tolerate write latency
      |      --> Write-Through (pair with Cache-Aside/Read-Through for reads)
      |
      +-- Want lowest write latency + DB fault tolerance
             --> Write-Back / Write-Behind (watch TTL vs DB-outage risk)
```

*(Interactive Mermaid version: [mermaid-diagrams.md](mermaid-diagrams.md))*

## 🔧 Deep Dive: How It Actually Works

### Distributed Caching — Why & How
A single cache server has two hard limits: **scalability** (fixed resources — you can't scale past a point) and **single point of failure** (if it dies, all caching capability is gone). The fix is a **cache pool** — multiple cache servers (Cache-1, Cache-2, Cache-3, Cache-4...) — with each app server using a **cache client** to determine which specific cache server to talk to for a given key.

The mechanism used to decide "which cache server owns this key" is **consistent hashing** (the same ring-based technique used for general distributed node assignment): cache servers are placed as nodes on a hash ring; a key's hash determines a point on the ring, and the **first cache server encountered walking clockwise** from that point is the one responsible for storing/serving that key.

### Strategy 1: Cache-Aside (a.k.a. Lazy Loading)
1. Application checks the cache first.
2. **Cache hit** → return data directly from cache.
3. **Cache miss** → application itself fetches from the DB, **writes the result into the cache**, then returns it to the client.

- **Pros:**
  - Great for **read-heavy** workloads.
  - **Resilient to cache outages** — if the cache goes down, every request just becomes a cache miss and falls through to the DB; the request still succeeds (just without the cache speed benefit).
  - **Cache schema is independent of the DB schema** — since the *application* controls what gets written into the cache, you can reshape/combine data from multiple DB tables into a single cache document however is most convenient for reads.
- **Cons:**
  - **Write operations don't touch the cache at all** — a plain `INSERT`/`UPDATE` goes straight to the DB, so any new/changed data always causes a cache miss on the next read (cache has to catch up).
  - **Inconsistency risk:** if a write updates the DB (e.g., value goes from 10 → 11) but the cache still holds the old cached value (10) from a prior read, subsequent reads will keep returning the **stale value (10)** until that cache entry naturally expires or is evicted — cache-aside alone provides no mechanism to invalidate on write.

### Strategy 2: Read-Through Cache
Nearly identical to cache-aside on the surface (check cache → hit returns immediately; miss falls through to DB), but the **key difference is *who* is responsible for the miss-handling logic**:
- In cache-aside, the **application** contains the "if miss, fetch from DB and write to cache" logic.
- In read-through, the **caching library/layer itself** takes on that responsibility — the app just asks the cache, and the cache internally fetches from the DB on a miss, populates itself, and returns the value; the app doesn't need its own miss-handling code path.

- **Pros:** same read-heavy benefit as cache-aside; additionally, the fetch/populate logic is **cleanly separated from application code**, living inside the cache library instead.
- **Cons:** same as cache-aside (new-data cache miss, inconsistency risk on writes) **plus** an additional constraint — the **cache's document structure must mirror the DB table structure** one-to-one, since the caching library (not your app) is the one populating it, and it doesn't know your custom desired shape.

### Strategy 3: Write-Around Cache
Writes go **directly to the DB only** — the cache is never written to directly on a write. Instead, the write **invalidates** (marks dirty) any existing cached entry for that key.

Mechanism: a **dirty flag** is set on the cache entry when the underlying DB value changes. On a subsequent read, the cache checks the dirty flag — if dirty, it's treated as a cache miss, forcing a fresh read from the DB (which then re-populates the cache with the current value).

- **Note:** write-around is **not useful on its own** — it must be paired with cache-aside or read-through to have any actual read benefit; write-around alone only solves the "stale cache after write" consistency problem for reads that go through one of those other strategies.
- **Pros:** resolves the inconsistency problem between cache and DB (via the dirty-flag/invalidation mechanism).
- **Cons:**
  - New data still always causes a **cache miss on first read** (same limitation as the base strategies it pairs with).
  - **Not fault-tolerant for writes** — since writes go directly and only to the DB, if the DB is down, **the write operation fails outright**. There's no fallback.

### Strategy 4: Write-Through Cache
On a write, data is written to the **cache first**, then **synchronously** written to the DB. **Both must succeed, or the whole write is treated as failed** (if either the cache write or the DB write fails, the transaction must be rolled back / the exception thrown) — this is effectively a **two-phase commit**-style guarantee between cache and DB.

- **Pros:**
  - **Cache and DB always remain consistent** — because it's an all-or-nothing (two-phase) write.
  - **Cache-hit chances increase significantly**, because even **new data** gets written into the cache immediately at write time (not just on subsequent reads).
- **Cons:**
  - **Useless in isolation** — write-through alone just adds write latency (you're now writing to two places) with zero benefit unless something is actually reading from that cache; it must be paired with cache-aside or read-through to realize any read-side gain.
  - Requires implementing this **two-phase commit** semantics correctly — if cache succeeds but DB fails, you must roll back the cache write too, or the cache will hold data the DB doesn't have.
  - **Not fully fault-tolerant** — if either the DB or the cache goes down, the write operation fails; there's no fallback path.

### Strategy 5: Write-Back (a.k.a. Write-Behind) Cache
On a write, data is written to the **cache first** (same as write-through), but instead of writing to the DB synchronously, the write is **pushed onto a queue** and persisted to the DB **asynchronously**, later, by a separate consumer process.

- **Pros:**
  - **Write API latency drops significantly** — the client gets a success response as soon as the cache write + queue publish completes, without waiting on a (slower) DB write.
  - **Brings fault tolerance to writes** — even if the DB is completely down (e.g., for a couple of hours), write requests can still succeed because they only depend on the cache and the queue; the queue will drain into the DB once it recovers.
  - **Cache-hit chances increase a lot**, similar to write-through, since the cache always has the latest written data immediately.
  - Gives **much better performance when paired with read-through or cache-aside**, since reads then also benefit from the cache always being fresh.
- **Cons — the critical failure scenario to know:**
  - If the cache entry's **TTL (time-to-live)** expires **before** the queued write actually makes it to the DB (e.g., TTL = 3 hours, but the DB has been down for 5 hours), the data is evicted from the cache **and still isn't in the DB** — the data becomes **completely unavailable** until the DB recovers and the backlog is processed. This is the single biggest risk unique to write-back and must be called out explicitly in any design discussion of it.

## 🔥 Real Production Incident & Fix

**What broke:** An e-commerce team used **Cache-Aside** for product pricing data with no companion write-invalidation strategy. A pricing team pushed a flash-sale discount update directly to the database, but the Redis cache entries for those product IDs (populated hours earlier from normal browsing traffic) were not touched. For roughly 40 minutes — until the cache TTL naturally expired — customers kept seeing the old, higher prices on already-cached product pages while the checkout service (which read straight from the DB) correctly applied the discount, causing a mismatch between displayed price and charged price and a spike in customer support tickets.

**How it was detected:** Customer support flagged a pattern of complaints ("the page said $49.99 but I was charged $39.99") within the first 15 minutes. Engineers checked the Redis `TTL` command against affected product keys and confirmed those entries were populated *before* the price update timestamp in the DB's audit log — proving the cache was serving stale, pre-discount data.

**Root cause:** Plain Cache-Aside has no write-time invalidation mechanism by design — writes go straight to the DB and never touch the cache. The team had relied purely on a fairly long TTL for "eventual" freshness, which was fine for slow-changing catalog data but broke down the moment a business process needed near-real-time price updates.

**The fix:** The team added an explicit **cache invalidation step** to the pricing update pipeline — whenever a price changes in the DB, the same transaction now publishes a small event that triggers an explicit `DEL` on the corresponding Redis key (an application-level version of the write-around "mark dirty" mechanism). They also reduced the default TTL for price-sensitive keys from 4 hours to 5 minutes as a safety net, so even if an invalidation event were ever missed, staleness would be capped much more tightly.

```
BEFORE (Cache-Aside, no invalidation):        AFTER (Cache-Aside + explicit invalidation on write):
DB price updated ──► (cache untouched) ✖      DB price updated ──► event fired ──► Redis DEL(key)
Cache still serves OLD price for ~40 min       Next read = cache MISS → fresh price fetched from DB
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why is Write-Around "useless alone" — what exactly is missing without pairing it with a read strategy?**
Write-around only handles invalidating stale cache entries on write (via the dirty flag) — it doesn't populate the cache on read. Without pairing it with cache-aside or read-through (which *does* populate the cache on a miss), there's no mechanism for data to ever get *into* the cache in the first place, so write-around alone provides zero read-performance benefit.

**Q2: Between Write-Through and Write-Back, which would you pick for a payment-processing write, and why?**
Write-Through — because it enforces synchronous, two-phase-commit-style consistency between cache and DB (both succeed or both fail), which matters for financial correctness. Write-Back's asynchronous DB persistence introduces a window where a confirmed "successful" write could still be lost if the queue backlog outlives the cache TTL — an unacceptable risk for payment data.

**Q3: How does consistent hashing help distributed caching specifically, versus a simple `hash(key) % number_of_servers` approach?**
With plain modulo hashing, adding or removing a single cache server changes the modulus, which reshuffles almost every key's assigned server, causing a massive wave of cache misses. Consistent hashing places servers on a ring so that adding/removing one server only remaps the keys that fell in that server's specific range on the ring, keeping cache-miss storms localized instead of system-wide.

**Q4: In Cache-Aside, what happens to a request if the cache server is completely down?**
The request degrades gracefully — since the app first checks the cache and falls back to the DB on any failure to retrieve from it, a downed cache is effectively treated the same as a cache miss. The request still succeeds by going straight to the DB; you simply lose the speed benefit until the cache recovers, but you don't lose correctness or availability.

**Q5: How would you decide the right TTL for a Write-Back cache to avoid the "data unavailable" failure mode discussed?**
The TTL should be set well beyond your **expected worst-case DB outage/recovery time plus queue-processing backlog time** — if your DB has historically taken up to 2 hours to recover and the queue can take another hour to drain a backlog, a 3-hour TTL is already too tight; you'd want a much larger buffer or an explicit alerting mechanism that pauses eviction when the write-back queue is backed up.

**Q6: Can you combine Write-Through and Read-Through in the same system, and what would that give you?**
Yes — this is a very common production pairing. Read-Through handles cache population on misses (keeping the cache-population logic out of application code), and Write-Through ensures every write immediately updates both cache and DB consistently, so the combination gives you consistently fresh data on both the read and write path, at the cost of added write latency from the two-phase write.

## 🔑 Key Takeaway
Say this out loud: **"Every caching strategy is a tradeoff between read performance, write performance, consistency, and fault tolerance — Cache-Aside and Read-Through optimize reads but leave writes untouched (risking staleness), Write-Through and Write-Back optimize writes and freshness but add complexity or async risk, and in practice you pair a read strategy with a write strategy rather than relying on just one."**
