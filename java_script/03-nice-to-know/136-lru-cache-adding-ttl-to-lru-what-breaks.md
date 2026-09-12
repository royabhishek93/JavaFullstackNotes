# Adding TTL to LRU — What Breaks
> **Topic:** LRU Cache | **Level:** Senior Trap | **Frequency:** Medium

## The Setup

You have a working LRU cache implementation. A product requirement arrives: every cached entry must expire after a configurable TTL. For a pricing cache, stale data causes financial errors. The interviewer asks you to extend your implementation.

## The Question

How do you add per-entry TTL to an LRU cache? Name the two things that break if you implement it carelessly.

## Diagram

```
BUG 1 — LAZY-ONLY EXPIRY: ghost entries starve live entries
=============================================================
  capacity = 1000. All 1000 slots fill with entries, TTL = 60s.
  60 seconds pass. Nobody re-requests any of these keys.
  All 1000 slots now hold EXPIRED entries.

  put(newKey1):
    map.size (1000) > capacity (1000)  →  evict tail.prev (expired)  ✓
  put(newKey2):
    map.size (1000) > capacity (1000)  →  evict tail.prev (expired)  ✓
  put(newKey3):
    evicts newKey1 (now the LRU among live entries)  ← live entry evicted!

  Effective live capacity = 1 at worst
  (each new entry evicts the previous new entry; expired ghosts hold 999 slots)

BUG 2 — TTL CHECK AFTER insertAtHead: expired node becomes MRU
================================================================
  get(key):
    node = map.get(key)
    removeNode(node)
    insertAtHead(node)         ← WRONG: promoted BEFORE checking TTL
    if (Date.now() > node.expiresAt):
      removeNode(node); map.delete(key); return -1

  Result: expired node briefly becomes MRU. Even after removal,
  if a concurrent call (or subtle reordering) reads head.next,
  it may observe the stale node at the front.

CORRECT ORDER
=============
  get(key):
    node = map.get(key)
    if (!node) return -1
    if (Date.now() > node.expiresAt):    ← TTL check FIRST
      removeNode(node)
      map.delete(key)
      return -1
    removeNode(node)                     ← only promote if alive
    insertAtHead(node)
    return node.value
```

## Model Answer (15 YOE)

"Two things break with a careless implementation:

**Break 1 — Lazy-only expiry fills the cache with ghost entries.** If expired nodes are only removed when their key is explicitly requested, a cache where 900 of 1,000 entries expire and are never re-requested becomes effectively a capacity-100 cache. Every `put` evicts an expired node, but those slots are immediately consumed by the new entry, which is then itself evicted by the next `put`. Live entries cannot accumulate.

Fix: add a background sweep (via `setInterval`) that walks from `tail.prev` inward and deletes expired nodes. Walk from the tail because stale entries are older and cluster near the LRU end. For high-throughput caches, use a min-heap keyed on `expiresAt` — schedule the next sweep at the soonest expiry rather than a fixed interval.

**Break 2 — Checking TTL after `insertAtHead` promotes expired nodes to MRU.** If you call `insertAtHead` before checking the TTL, the expired node becomes the most recently used entry, extending its effective lifetime past its intended TTL. Always check TTL before promoting.

Correct order:
```
get(key):  lookup → TTL check → [if expired: delete+return -1] → promote → return value
```"

## Why It's a Trap

Candidates who implement lazy TTL often test only the happy path (requesting a key before it expires) and miss the ghost-entry capacity collapse. The promotion-order bug is subtler: the code returns -1 correctly, but the list state is briefly corrupted, and in multi-threaded environments (or if `head.next` is observed externally) the stale node is visible at the wrong position.

## What NOT to Say

- "I'd just check TTL on get and it's done" — misses the ghost-entry capacity problem
- "Background sweep is over-engineering" — it is required for production correctness
- "Promote first, check TTL second — same result" — wrong; order matters for list state correctness

## Follow-up

**Q:** A min-heap keyed on `expiresAt` — how do you keep it in sync with the LRU list?

**A:** The heap is a secondary index for TTL-ordered eviction; the DLL remains the primary structure for LRU-ordered eviction. On every `put`, push the new node's `expiresAt` into the heap. On expiry sweep, pop from the heap while `heap.peek().expiresAt < Date.now()`, then call `removeNode` and `map.delete` for each popped node. The heap entry must hold the node reference (not just the key) so that `removeNode` can be called in O(1). The heap grows to at most `capacity` entries and each sweep pops only the truly expired ones — O(k log capacity) where k is the number of expired entries, versus O(capacity) for a full list scan.
