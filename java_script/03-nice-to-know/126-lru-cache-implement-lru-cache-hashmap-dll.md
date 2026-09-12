# Implement LRU Cache with O(1) get and put
> **Topic:** LRU Cache | **Level:** Fundamental | **Frequency:** High

## The Setup

You are building the caching layer for a URL shortener handling 50,000 short-URL resolutions per second at peak. A long-URL lookup from Postgres takes ~8ms. The cache must serve it in ~0.2ms. The cache has a fixed capacity and must evict the least recently used entry when full.

## The Question

Implement an LRU cache supporting `get(key)` and `put(key, value)`, both in O(1) time and O(capacity) space. Explain your data structure choices.

## Diagram

```
STRUCTURE OVERVIEW
==================

  Map (key → node reference)
  ┌────────────────────────────────────────────────┐
  │  "user:1" ──────────────────────────┐          │
  │  "user:3" ─────────────────┐        │          │
  │  "user:2" ──────┐          │        │          │
  └─────────────────┼──────────┼────────┼──────────┘
                    │          │        │
                    ▼          ▼        ▼
  Doubly Linked List (recency order, newest → oldest)
  ┌──────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌──────┐
  │ HEAD │◄──►│  user:2    │◄──►│  user:3    │◄──►│  user:1    │◄──►│ TAIL │
  │dummy │    │  val: "B"  │    │  val: "C"  │    │  val: "A"  │    │dummy │
  └──────┘    └────────────┘    └────────────┘    └────────────┘    └──────┘
     MRU end ──► (most recently used)    (least recently used) ◄── LRU end

  head.next = MRU node (user:2)         tail.prev = LRU node (user:1)
```

## Model Answer (15 YOE)

"I use a HashMap combined with a doubly linked list. The HashMap gives O(1) key-to-node lookup with no scanning. The doubly linked list gives O(1) structural moves: because every node holds both `prev` and `next`, removing a node from anywhere in the list requires only four pointer rewrites — no traversal. I keep a dummy sentinel at each end so I never have to null-check on insert or remove. The list is always ordered by recency: head side is most recently used, tail side is least recently used. Every `get` moves the node to the head. Every `put` on a full cache removes `tail.prev` — the LRU node — before inserting the new one. Both operations are O(1) time and the total space is O(capacity)."

```js
class Node {
  constructor(key, value) {
    this.key   = key;    // stored here so eviction can call map.delete(node.key) in O(1)
    this.value = value;
    this.prev  = null;
    this.next  = null;
  }
}

class LRUCache {
  constructor(capacity) {
    this.capacity = capacity;
    this.map      = new Map(); // key → node; O(1) lookup

    // Sentinel nodes: always present, never evicted.
    // Eliminates all null checks in removeNode and insertAtHead.
    this.head = new Node(0, 0); // MRU boundary
    this.tail = new Node(0, 0); // LRU boundary
    this.head.next = this.tail;
    this.tail.prev = this.head;
  }

  get(key) {
    if (!this.map.has(key)) return -1;

    const node = this.map.get(key);
    this.removeNode(node);   // detach from current list position
    this.insertAtHead(node); // promote to MRU
    return node.value;
  }

  put(key, value) {
    if (this.map.has(key)) {
      // Key already exists: remove old node (value may differ), re-insert fresh
      this.removeNode(this.map.get(key));
    }

    const node = new Node(key, value);
    this.insertAtHead(node);
    this.map.set(key, node);

    if (this.map.size > this.capacity) {
      // Evict LRU: the real node just before the tail sentinel
      const lru = this.tail.prev;
      this.removeNode(lru);
      this.map.delete(lru.key); // lru.key is why Node carries its own key
    }
  }

  removeNode(node) {
    // Wire node's neighbors to skip over this node. Two pointer writes.
    node.prev.next = node.next;
    node.next.prev = node.prev;
  }

  insertAtHead(node) {
    // Four pointer writes to splice node between head sentinel and old first node.
    node.next           = this.head.next; // (1) node's forward pointer → old first
    node.prev           = this.head;      // (2) node's back pointer → sentinel
    this.head.next.prev = node;           // (3) old first's back pointer → node  ← DON'T FORGET
    this.head.next      = node;           // (4) sentinel's forward pointer → node
  }
}
```

**Complexity:**

| Operation | Time | Why |
|---|---|---|
| `get` | O(1) | Map lookup O(1) + 6 pointer writes O(1) |
| `put` | O(1) | Same + optional O(1) eviction |
| Space | O(capacity) | Map + list hold at most `capacity` entries |

## Follow-up

**Q:** Why does Redis use an approximation of LRU rather than exact LRU?

**A:** Exact LRU requires a doubly linked list across all keys — for millions of Redis keys that is a substantial per-key memory overhead and pointer-chasing penalty. Redis instead samples a small random set of keys (default 5, configurable via `maxmemory-samples`) and evicts the least recently used among those samples. This approximates true LRU at ~5-10% of the memory cost. For most workloads the difference in eviction quality is negligible.
