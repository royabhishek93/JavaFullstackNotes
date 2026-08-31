# Cache Eviction — LRU, LFU, TTL, and Redis maxmemory-policy
### When Your Cache Is Full, Which Keys Get Deleted First?

---

## PART 1 — THE STUDENT CONVERSATION

Your desk has space for 10 folders. You have 100 folders in the filing cabinet. You keep the most useful ones on your desk. When the desk is full and you need a new folder, which one do you remove to make space?

**LRU (Least Recently Used):** Remove the folder you haven't touched in the longest time. "I haven't looked at this since March — probably not needed soon." Recency is a proxy for future usefulness.

**LFU (Least Frequently Used):** Remove the folder you've accessed the fewest times total. "I've only opened this 2 times ever — versus that one 500 times." Frequency is a proxy for future usefulness.

**TTL (Time to Live):** Every folder has an expiry date written on it. Expired folders are removed regardless of how recently or frequently accessed. The data has a known freshness window.

**Random:** Just grab a random folder and remove it. Surprisingly effective at scale — if your access pattern is roughly uniform, random is nearly as good as LRU with none of the bookkeeping overhead.

The question isn't which algorithm is "best" — it's which one matches your access pattern:

- If **recency predicts future access** (most caches) → LRU
- If **a small hot set gets most traffic** (celebrity profiles, trending content) → LFU
- If **data has a natural freshness window** (API responses, session tokens) → TTL
- If **you just need fast eviction with low overhead** → Random

Redis gives you 8 policies to pick from. Choosing the wrong one can tank your cache hit rate or silently evict the data you need most.

---

## PART 2 — ALGORITHM DIAGRAMS AND REDIS POLICIES

### LRU Cache Mechanics

```
Cache capacity: 4 keys. Access sequence: A, B, C, D, (access A again), add E

After accessing A, B, C, D:
  LRU queue (head = most recent, tail = least recent):
  [D] ← [C] ← [B] ← [A]   (A was first, D was most recent)

Access A again → A moves to head:
  [A] ← [D] ← [C] ← [B]

Add E (cache full → evict tail):
  Evict: B (least recently used — hasn't been touched since initial load)
  [E] ← [A] ← [D] ← [C]

Data structure: doubly-linked list (for O(1) move-to-head) + hash map (for O(1) lookup)
Combined: O(1) get, O(1) put, O(1) eviction
Redis approximation: samples 5 (default) random keys, evicts the least-recently-used among them
  → Not exact LRU, but close. Saves memory vs exact LRU (no linked list overhead).
```

### LFU Counter Mechanics

```
Each key has a frequency counter (logarithmic, not exact count):

Key        | Access Count | LFU Counter
-----------|-------------|------------
celebrity  | 10,000/hr   | 255 (saturated)
trending   | 500/hr      | 180
normal     | 10/hr       | 45
one-time   | 1 total     | 1

On eviction: remove key with LOWEST counter (one-time → evicted first)

Counter decay: every lfu-decay-time minutes, counters are halved
  → Prevents old hot keys from staying warm forever
  → "Trending last week" slowly decays if not accessed this week

Redis LFU counter: 8-bit logarithmic counter (0-255)
  lfu-log-factor=10: counter increments by 1 per access probabilistically
  lfu-decay-time=1:  counter halved every 1 minute of idle time
```

### All 8 Redis maxmemory-policy Options

```
┌───────────────────┬──────────────────────────────────────────────────────────────┐
│ Policy            │ Behavior                                                     │
├───────────────────┼──────────────────────────────────────────────────────────────┤
│ noeviction        │ Default. Reject ALL writes when memory full. Clients get     │
│                   │ OOM errors. Use when cache MUST not lose data.               │
├───────────────────┼──────────────────────────────────────────────────────────────┤
│ allkeys-lru       │ Evict any key using LRU order. Best general-purpose policy.  │
│                   │ Works for most caching use cases.                            │
├───────────────────┼──────────────────────────────────────────────────────────────┤
│ volatile-lru      │ Evict only keys WITH a TTL set, LRU order. Keys without TTL  │
│                   │ are never evicted. Use when some keys are permanent.         │
├───────────────────┼──────────────────────────────────────────────────────────────┤
│ allkeys-lfu       │ Evict any key using LFU order. Best for highly skewed        │
│                   │ access (1% of keys = 99% of traffic).                        │
├───────────────────┼──────────────────────────────────────────────────────────────┤
│ volatile-lfu      │ Evict only TTL keys, LFU order.                              │
├───────────────────┼──────────────────────────────────────────────────────────────┤
│ allkeys-random    │ Evict any key randomly. Fastest. Surprisingly effective for  │
│                   │ uniform access patterns.                                     │
├───────────────────┼──────────────────────────────────────────────────────────────┤
│ volatile-random   │ Evict TTL keys randomly.                                     │
├───────────────────┼──────────────────────────────────────────────────────────────┤
│ volatile-ttl      │ Evict the key with the SMALLEST remaining TTL first.         │
│                   │ "Soonest-to-expire anyway" evicted first.                    │
└───────────────────┴──────────────────────────────────────────────────────────────┘
```

### LFU vs LRU — When They Disagree

```
Scenario: Cache at 100% capacity, need to evict one key.

Key A: Celebrity profile — accessed 10,000 times over the past hour.
       Last accessed: 5 minutes ago.

Key B: One-time report — accessed 1 time ever (10 minutes ago).
       Last accessed: 10 minutes ago.

LRU decision: evict Key A (older last-access timestamp = 5 min vs 10 min)
              LRU says A was accessed MORE recently — so B is evicted?
              Wait — B was accessed 10 min ago, A was 5 min ago.
              LRU evicts B (10 min idle > 5 min idle). That's correct here.

Tricky case:
Key A: Celebrity — 10,000 accesses/hr, last access 2 minutes ago
Key B: One-time   — 1 access ever,     last access 1 minute ago

LRU: evicts Key A (2 min idle > 1 min idle) ← WRONG. Celebrity is valuable!
LFU: evicts Key B (frequency 1 << frequency 10000) ← CORRECT.

Use LFU when your access pattern is SKEWED (power law distribution).
Use LRU when your access pattern is UNIFORM (recency = good proxy for future access).
```

---

## PART 3 — PRODUCTION CONFIGURATION AND MONITORING

### Redis Configuration

```
# redis.conf
maxmemory 8gb
maxmemory-policy allkeys-lru

# For LFU tuning:
lfu-log-factor 10      # Higher = slower counter increment = coarser LFU
                       # 10 is default. Lower for more sensitivity.
lfu-decay-time 1       # Minutes before counter starts decaying
                       # 1 minute default. Increase for slower-moving hot sets.

# LRU sample size (applies to all lru/lfu policies):
maxmemory-samples 5    # Default. Higher = more accurate but more CPU.
                       # 10 is good balance for production.
```

### Monitoring Evictions

```bash
# Real-time eviction rate
redis-cli INFO stats | grep evicted_keys
# evicted_keys:0        ← healthy (no evictions since restart)
# evicted_keys:142531   ← evictions have occurred

# Evictions per second (compute delta over time)
watch -n 1 'redis-cli INFO stats | grep evicted_keys'

# Alert threshold: any evictions in production = cache too small or TTL too aggressive
# Exception: volatile-ttl + noeviction combo for leaderboard safety (see below)

# Find biggest memory consumers
redis-cli --bigkeys

# Inspect individual key's LFU/LRU state
redis-cli OBJECT FREQ celebrity:profile:12345   # LFU counter (0-255)
redis-cli OBJECT IDLETIME user:session:abc      # Seconds since last access (LRU)

# Memory usage breakdown
redis-cli INFO memory
# used_memory_human: 7.23G
# maxmemory_human: 8.00G
# mem_fragmentation_ratio: 1.08   ← healthy (<1.5). >1.5 = fragmentation issue.
```

### TTL Best Practices

```python
# Set TTL based on data freshness, not arbitrary numbers:
redis.setex("user:profile:42",    3600,  serialize(profile))   # 1hr — profile changes rarely
redis.setex("feed:timeline:42",   300,   serialize(feed))      # 5min — feed changes often
redis.setex("rate:limit:ip:1.2.3.4", 60, "10")                # 60s — sliding window
redis.setex("session:token:abc",  86400, user_id)              # 24hr — session
redis.setex("search:result:q=foo", 180,  serialize(results))  # 3min — search freshness

# Never set TTL = 0 (means no expiry — key lives until evicted)
# For keys you NEVER want evicted (source-of-truth data), use volatile-lru
# and do NOT set a TTL — they'll never be in the eviction candidate pool.
```

### Memory Sizing Rules of Thumb

| Data Type | Overhead per Key | Notes |
|-----------|-----------------|-------|
| String value < 44 bytes | ~64 bytes total | Redis embstr encoding |
| String value 45-512 bytes | ~100-600 bytes | Raw string encoding |
| Hash (small, < 128 fields) | ~300 bytes | ziplist encoding |
| Hash (large) | 200 bytes + per-field | hashtable encoding |
| ZSET (small) | ~500 bytes | ziplist encoding |
| ZSET (large) | ~100 bytes + per-member | skiplist encoding |

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your Redis cache for a social media feed is using 80% of memory and evictions are spiking during peak hours. Most of the cache value comes from 1% of users (celebrities). Which eviction policy do you choose and why?"

**You (architect answer):**

> "Switch from `allkeys-lru` to `allkeys-lfu`. Here's why: celebrity profiles are accessed thousands of times per hour — their LFU frequency counter will be near the maximum (255 in Redis's 8-bit counter). A first-time visitor's profile (accessed once this hour) will have an LFU counter near 1. LFU evicts the lowest-frequency key first, so the one-time visitor's profile gets evicted, and the celebrity profile stays warm.
>
> LRU would get this wrong in a common scenario: if a celebrity profile was last accessed 5 minutes ago (because no one has requested it in the last 5 minutes, not because it's unpopular), and a random visitor's profile was accessed 4 minutes ago (literally just once), LRU evicts the celebrity profile. That's the wrong call — the celebrity profile is far more likely to be requested again.
>
> Beyond the policy change, I'd also: increase `maxmemory` if the budget allows (evictions during peak = cache undersized for peak load); reduce TTL on low-value keys like one-time search results (they don't need to live for an hour); and add alerting on `evicted_keys` — if that number is non-zero in production, the cache is undersized. One more thing: tune `maxmemory-samples` from 5 to 10 for better LFU accuracy — the CPU cost is minimal."

---

## PART 5 — DECISION FRAMEWORK

### Which Eviction Policy to Use

| Access Pattern | Recommended Policy | Why |
|---------------|-------------------|-----|
| General purpose cache (mixed access) | `allkeys-lru` | Recency is good proxy for future access in uniform patterns |
| Social media (celebrity/trending effect) | `allkeys-lfu` | Small hot set accessed far more than long tail |
| Mix of permanent + cached data in same Redis | `volatile-lru` | Permanent keys have no TTL — never evicted |
| Rate limit counters with window expiry | `volatile-ttl` | Soonest-to-expire counters evicted first when memory tight |
| Session store (uniform short-lived sessions) | `allkeys-random` | Uniform TTLs + random eviction is surprisingly effective |
| Leaderboard (source of truth — must not be evicted) | `volatile-lru` + no TTL on leaderboard keys | Leaderboard keys without TTL are never eviction candidates |
| Cache that MUST not drop data | `noeviction` | Clients get errors instead of silent eviction — at least you know |

### LRU vs LFU Decision Rule

```
Is your traffic distribution uniform (all keys roughly equally popular)?
  YES → allkeys-lru (simpler, slightly less CPU overhead)
  NO → Is 1-10% of keys getting >80% of traffic?
         YES → allkeys-lfu (hot keys stay warm, cold long-tail evicted first)
         UNSURE → Add: redis-cli OBJECT FREQ on your top 100 vs bottom 100 keys
                  If top keys have counters >100x bottom keys → use LFU
```

---

## QUICK REFERENCE CARD

```
REDIS EVICTION POLICIES
========================
noeviction      → Block writes. Use when data must not be lost.
allkeys-lru     → General purpose. Evict coldest (by recency) key.
volatile-lru    → Like allkeys-lru but only TTL-tagged keys.
allkeys-lfu     → Best for power-law traffic. Evict least-accessed key.
volatile-lfu    → Like allkeys-lfu but only TTL-tagged keys.
allkeys-random  → Fast. Good for uniform access.
volatile-random → Like allkeys-random but only TTL-tagged keys.
volatile-ttl    → Evict soonest-to-expire key first.

LRU vs LFU
===========
LRU: evict by recency. Good for uniform access patterns.
LFU: evict by frequency. Good for skewed (celebrity/trending) patterns.

MONITORING
===========
redis-cli INFO stats | grep evicted_keys   → alert if > 0
redis-cli OBJECT FREQ <key>                → LFU counter
redis-cli OBJECT IDLETIME <key>            → LRU idle seconds
redis-cli --bigkeys                        → memory hogs

KEY RULES
==========
Keys you NEVER want evicted → volatile-lru + no TTL on those keys.
Evictions during peak       → cache is undersized for peak load.
mem_fragmentation_ratio > 1.5 → restart or increase maxmemory.
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Cache eviction policy determines which data gets dropped when memory is full — choosing wrong means the most-needed keys are evicted first, killing your hit rate at exactly the worst moment.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **02 — Distributed Rate Limiter** | Redis stores rate limit counters with short TTLs (window expiry). `volatile-ttl` policy ensures the soonest-expiring window counters are evicted first when memory is tight — expired counters are useless anyway. |
| **05 — Social Media Feed** | Feed cache and profile cache exhibit celebrity effect — 1% of users get 99% of traffic. `allkeys-lfu` keeps celebrity profiles warm and evicts one-time visitor profiles first, maintaining high cache hit rate at peak. |
| **13 — Leaderboard** | The leaderboard ZSET is the source of truth (not just a cache). Must never be evicted. Use `volatile-lru` and set NO TTL on leaderboard keys — only TTL-tagged cache entries are eviction candidates. |

**Architect's one-liner for the interview:**
*"Use allkeys-lfu when 1% of keys get 99% of traffic — LFU keeps hot keys warm and evicts cold ones; use allkeys-lru for uniform access patterns where recency predicts future use."*
