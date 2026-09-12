# Browser Tab Cache Scenario
> **Topic:** LRU Cache | **Level:** Intermediate | **Frequency:** Medium

## The Setup

A browser keeps rendered pages in memory so that clicking "Back" is instant. Memory budget is fixed. When the user opens too many tabs, the engine must decide which cached page to drop. A junior engineer on your team proposes implementing this with a JavaScript array using `findIndex`, `splice`, and `unshift`.

## The Question

The browser's page cache behaves like an LRU cache. Why will the array-based proposal fail at scale? What would you use instead, and what hidden complexity does a real browser add on top of pure LRU?

## Diagram

```
ARRAY APPROACH — O(n) per cache hit
=====================================
  cache = ["url:D", "url:C", "url:B", "url:A"]  // index 0 = most recent

  get("url:B"):
    findIndex("url:B")  →  scan entire array  →  O(n)
    splice(2, 1)        →  shift elements     →  O(n)
    unshift("url:B")    →  shift elements     →  O(n)
    Total: 3x O(n)

  At n=500 cached tabs:  ~1,500 element operations per click
  At n=5,000 (devtools + workers): jank spike visible to user

HASHMAP + DLL — O(1) per cache hit
=====================================
  map = Map<url, CacheNode>

  get("url:B"):
    map.get("url:B")    →  node ref in O(1)
    removeNode(B)       →  2 pointer writes
    insertAtHead(B)     →  4 pointer writes
    Total: 6 pointer writes regardless of cache size
```

## Model Answer (15 YOE)

"With an array, every `get` is three O(n) operations: `findIndex` to locate the item, `splice` to remove it, and `unshift` to prepend it. At 500 cached tabs this is fast enough to hide. At 5,000 entries — developer tools, pre-fetch workers, background tabs — it becomes a measurable jank spike during scroll or navigation.

The fix is HashMap + doubly linked list. The browser engine stores a `Map<url, CacheNode>`. Each `CacheNode` lives in the doubly linked list ordered by last-access time. A cache hit requires four pointer rewrites regardless of whether there are 50 or 500,000 cached entries.

The hidden depth here: the browser also factors in page weight (memory size), not just recency. This is where pure LRU breaks down — a 2 MB tab accessed 1 minute ago may deserve eviction over a 50 KB tab accessed 5 minutes ago because the memory savings are 40x larger. Production systems layer a cost/benefit score on top of LRU:

```
eviction_score = memory_size / time_since_last_access
```

The entry with the highest score (biggest memory, least recently used) is evicted first. Pure LRU is the interview answer; weighted eviction is the production answer."

## Follow-up

**Q:** How would you handle a tab that the user has pinned? It should never be evicted regardless of LRU rank.

**A:** Add a boolean `pinned` flag to each `CacheNode`. During eviction, walk from `tail.prev` inward and skip any node where `node.pinned === true`. Evict the first unpinned LRU node. This degrades eviction from O(1) to O(n) in the worst case (all tabs pinned), but in practice pinned tabs are rare and the scan terminates quickly. A cleaner approach: maintain a separate doubly linked list for unpinned nodes only. Pinned nodes live in the Map but not in the eviction list. Eviction always hits `tail.prev` of the unpinned list — O(1) restored.
