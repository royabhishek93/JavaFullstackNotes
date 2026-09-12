# Redis LRU Cache Layer for URL Shortener
> **Topic:** LRU Cache | **Level:** Intermediate | **Frequency:** High

## The Setup

You are designing the caching layer for TinyURL. Redis is configured with `maxmemory-policy allkeys-lru` and `maxmemory 512mb`. The service resolves 50,000 short URLs per second at peak. The long-URL lookup from Postgres takes ~8ms. Redis serves it in ~0.2ms. At peak that gap — 7.8ms saved per request across 50k RPS — is the difference between a responsive product and a timeout storm.

## The Question

Walk me through how an LRU cache works internally. Why is HashMap + doubly linked list the right data structure for O(1) get and put? How does Redis approximate this in production?

## Diagram

```
REQUEST FLOW
============

  Client → [Redis GET short:abc123]
                │
         HIT ───┘ → return long URL  (0.2ms)
         MISS ──┘ → query Postgres   (8ms)
                      → Redis SET short:abc123 <long_url>
                      → return long URL

REDIS MEMORY PRESSURE (allkeys-lru)
=====================================

  When Redis reaches maxmemory (512mb):
    1. New write arrives
    2. Redis samples N random keys (default N=5, set via maxmemory-samples)
    3. Among those N, evicts the one with the oldest last-access timestamp
    4. Repeats until enough memory is free

  This is approximate LRU — not exact — but within 5-10% eviction quality
  at a fraction of the per-key memory overhead of a full linked list.
```

## Model Answer (15 YOE)

"I use a HashMap combined with a doubly linked list. The HashMap gives O(1) key-to-node lookup with no scanning. The doubly linked list gives O(1) structural moves: because every node holds both `prev` and `next`, removing a node from anywhere in the list requires only four pointer rewrites — no traversal. I keep a dummy sentinel at each end so I never have to null-check on insert or remove.

The list is always ordered by recency: head side is most recently used, tail side is least recently used. Every `get` moves the node to the head. Every `put` on a full cache removes `tail.prev` — the LRU node — before inserting the new one. Both operations are O(1) time and the total space is O(capacity).

For this URL shortener, I'd configure Redis with `allkeys-lru` because every key is a valid eviction candidate — there are no 'important' keys that must never be evicted. The Postgres fallback handles misses cleanly. I'd tune `maxmemory-samples` to 10 (instead of the default 5) to improve eviction accuracy at a modest CPU cost — worth it at 50k RPS."

**Redis nuance — why approximate LRU:**

Exact LRU requires maintaining a doubly linked list across all keys. For millions of Redis keys that is substantial per-key memory overhead and pointer-chasing on every operation. Redis instead samples a small random set of keys (default 5, configurable via `maxmemory-samples`) and evicts the least recently used among those samples. This approximates true LRU at ~5-10% of the memory cost. For URL shortener workloads the difference in eviction quality is negligible.

## Follow-up

**Q:** When would you choose `volatile-lru` over `allkeys-lru` for this service?

**A:** `volatile-lru` only evicts keys that have a TTL set. You would use it if some keys must never be evicted regardless of memory pressure — for example, a master routing table or feature flag keys stored alongside the URL cache. Keys without a TTL are protected from eviction. The trade-off: if all eviction candidates have TTLs set, Redis may still reject writes when memory is full. For a pure URL cache where every key is expendable, `allkeys-lru` is cleaner.
