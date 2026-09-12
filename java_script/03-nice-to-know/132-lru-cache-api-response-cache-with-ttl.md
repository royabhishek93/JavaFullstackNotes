# API Response Cache with TTL Extension
> **Topic:** LRU Cache | **Level:** Intermediate | **Frequency:** Medium

## The Setup

Your Node.js backend caches third-party pricing API responses. The cache capacity is 1,000 entries. Each entry must expire after 60 seconds regardless of access frequency — stale pricing data causes real financial loss. The third-party API charges per call, so unnecessary re-fetches cost money.

## The Question

How do you extend an LRU cache to support per-entry TTL? What breaks if you implement lazy expiry carelessly?

## Diagram

```
NODE STRUCTURE WITH TTL
========================
  Node: { key, value, expiresAt, prev, next }
                      ↑
                      Date.now() + ttl_ms (set at insertion time)

get(key) FLOW WITH TTL CHECK
==============================
  map.get(key)
       │
       ▼
  node exists?  ──No──►  return -1
       │
      Yes
       ▼
  Date.now() > node.expiresAt?
       │
      Yes ──►  removeNode(node)
               map.delete(key)
               return -1          ← expired, treat as miss
       │
      No
       ▼
  removeNode(node)
  insertAtHead(node)              ← normal LRU promotion
  return node.value

LAZY-ONLY EXPIRY — THE GHOST PROBLEM
======================================
  Scenario: 900 of 1,000 slots hold expired entries nobody re-requests.

  cache slots:  [ exp | exp | exp | ... 900 expired ... | live | live | ... ]

  put(newKey):
    map.size (1000) > capacity (1000)  →  evict tail.prev
    tail.prev is an expired entry — evicted correctly.
    But: next put evicts another expired entry.
    So: effective live capacity = only 100 slots.
    New entries constantly push each other out.
    Cache behaves as capacity=100 despite being designed for capacity=1000.
```

## Model Answer (15 YOE)

"Store `expiresAt = Date.now() + ttl` in each node alongside `key` and `value`. On every `get`, after the Map lookup, check `Date.now() > node.expiresAt`. If expired, call `removeNode`, call `map.delete`, and return -1. Critically, do the TTL check **before** calling `insertAtHead` — if you promote first, the expired node becomes MRU and survives far longer than its intended TTL.

```
get(key):
  node = map.get(key)
  if (!node) return -1
  if (Date.now() > node.expiresAt):        ← TTL check FIRST
    removeNode(node); map.delete(key)
    return -1
  removeNode(node); insertAtHead(node)     ← promote only if alive
  return node.value
```

**What breaks with lazy-only expiry:** Expired nodes are never removed until someone requests that specific key. If 900 of your 1,000 slots are held by expired entries that nobody re-requests, new entries evict each other immediately — the effective live capacity shrinks to 100.

**Fix:** Add a background `setInterval` sweep (every 30 seconds) that walks from `tail.prev` inward and prunes entries where `Date.now() > node.expiresAt`. Walk from the tail because LRU nodes are older and more likely to be expired — you can short-circuit early once you hit a non-expired node. For high-throughput caches, a min-heap keyed on `expiresAt` is more efficient than a list scan: the heap's minimum is always the soonest-to-expire entry. Schedule the next sweep at `heap.peek().expiresAt` instead of a fixed interval."

## Follow-up

**Q:** Should a `get` that hits an expired entry reset the TTL (effectively extending it)?

**A:** No — that defeats the purpose of TTL. The contract is "this entry is stale after 60 seconds." If the caller needs fresh data, it should fetch from the source and call `put` with a new `expiresAt`. The LRU cache should be a transparent expiry mechanism, not a policy decision maker. If you find yourself wanting to extend TTL on access, the real design smell is that your TTL is too short for the access pattern — fix the TTL value, not the expiry logic.
