# Why HashMap + Doubly Linked List — Why Not Array
> **Topic:** LRU Cache | **Level:** Fundamental | **Frequency:** High

## The Setup

A browser keeps rendered pages in memory so that clicking "Back" is instant. Memory budget is fixed. A junior engineer on your team proposes storing the page cache in a plain JavaScript array, using `findIndex`, `splice`, and `unshift` to implement recency ordering.

## The Question

Why will the array-based approach fail at scale? What makes HashMap + doubly linked list the correct choice for O(1) LRU operations?

## Diagram

```
ARRAY APPROACH — O(n) per operation
=====================================
  Cache: [ D, C, B, A ]   (index 0 = most recent)

  get("B"):
    findIndex("B") → scan whole array → O(n)
    splice(2, 1)   → shift elements left → O(n)
    unshift("B")   → shift all elements right → O(n)
    Total: O(n) — 3 linear passes

HASHMAP + DLL APPROACH — O(1) per operation
=============================================
  get("B"):
    map.get("B")    → node reference → O(1)
    removeNode(B)   → 2 pointer writes → O(1)
    insertAtHead(B) → 4 pointer writes → O(1)
    Total: O(1) — always, regardless of cache size
```

## Model Answer (15 YOE)

"With an array, every `get` is three O(n) operations: `findIndex` to locate the item, `splice` to remove it, and `unshift` to prepend it. At 500 cached tabs this is fast enough to hide. At 5,000 entries — developer tools, pre-fetch workers, background tabs — it becomes a measurable jank spike during scroll or navigation.

The fix is HashMap + doubly linked list. The browser engine stores a `Map<url, CacheNode>`. Each `CacheNode` lives in the doubly linked list ordered by last-access time. A cache hit requires four pointer rewrites regardless of whether there are 50 or 500,000 cached entries.

The key insight is that a doubly linked list node can remove itself from any position in O(1) because it holds direct references to both neighbors — no traversal needed. The HashMap makes the node instantly reachable from its key. Together they give O(1) lookup, O(1) detach, and O(1) reinsert."

**Why doubly linked (not singly linked):** A singly linked list can only traverse forward. To remove a node, you need its predecessor — which requires scanning from the head. A doubly linked node holds `prev` directly, so removal is two pointer writes with no scan.

**Why not a balanced BST (e.g., TreeMap):** A BST gives O(log n) lookup and O(log n) reorder. Correct, but worse. The goal is O(1), not O(log n). Sorted order by key is not what we need — we need sorted order by recency, and that changes on every access.

**Why not a heap:** A min-heap gives O(1) access to the minimum but O(log n) removal of an arbitrary element. We need arbitrary removal (the accessed node can be anywhere in the cache), so a heap does not fit.

## Follow-up

**Q:** The browser also factors in page weight (memory size), not just recency. How does this break pure LRU?

**A:** Pure LRU evicts the least recently accessed entry. A 2 MB tab accessed 1 minute ago may deserve eviction over a 50 KB tab accessed 5 minutes ago because the memory savings are 40x larger. Production systems layer a cost/benefit score on top of LRU: `score = size / recency_weight`. Pure LRU is the interview answer; weighted eviction is the production answer.
