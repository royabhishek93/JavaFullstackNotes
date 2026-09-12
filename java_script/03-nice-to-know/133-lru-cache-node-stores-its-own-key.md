# Node Stores Its Own Key — Why
> **Topic:** LRU Cache | **Level:** Senior Trap | **Frequency:** High

## The Setup

You have just implemented an LRU cache. The interviewer points to the `Node` constructor and asks: "Your node stores both `key` and `value`. Why does it need the `key`? The HashMap already maps key to node — isn't storing the key in the node redundant?"

## The Question

Why does each Node in the doubly linked list store its own key? What would break if you only stored the value?

## Diagram

```
EVICTION PATH — why key must be in the node
=============================================

  Cache full. New put() arrives.

  Step 1:  lru = tail.prev          ← O(1): direct pointer to LRU node
  Step 2:  removeNode(lru)          ← O(1): 2 pointer writes
  Step 3:  map.delete(lru.key)      ← O(1): direct key available from node
  Step 4:  insertAtHead(newNode)    ← O(1): 4 pointer writes
  Step 5:  map.set(key, newNode)    ← O(1)

  If Node did NOT store its key:
  Step 3 becomes:
    map.forEach((node, k) => {      ← O(n): scan entire Map
      if (node === lru) map.delete(k);
    });
  → Eviction degrades from O(1) to O(n)
  → At capacity=100,000 this fires on every put when full

WHAT THE NODE KNOWS
====================
  lru node (tail.prev):
    node.value  →  the cached data  (needed for get)
    node.key    →  the Map key      (needed for eviction's map.delete)
    node.prev   →  predecessor in list
    node.next   →  successor in list

  The Map holds key → node.
  The node holds key so the reverse direction (node → key) is also O(1).
```

## Model Answer (15 YOE)

"The key is stored in the node to make Map deletion O(1) during eviction.

Eviction is triggered when the cache is full and a new entry arrives. We grab the LRU node directly via `tail.prev` — that is O(1). We then need to remove it from the HashMap. `map.delete` requires the key, not the node. If the node stores its own key, `map.delete(lru.key)` is O(1). If the node stores only the value, we have no way to find which Map entry points to this node without scanning the entire Map — O(n).

This is the only reason the key lives in the node. It is not for identification in the general sense. It is specifically to enable the reverse lookup: given a node, find its Map key in O(1)."

## Why It's a Trap

Candidates who say "so you can identify the node" have not thought through the eviction path. The node is already identified — we reached it via `tail.prev`. The problem is not identification; it is the reverse mapping from node back to key so the Map can be updated. The interviewer is testing whether you understand the two-direction dependency between the Map and the list.

## What NOT to Say

- "So you know what the node contains" — vague, misses the point
- "For debugging purposes" — wrong
- "So you can print the cache" — wrong
- "The Map lookup gives you the node; the node lookup gives you… the node. I'm not sure why the key is there" — shows you haven't traced the eviction code path

## Follow-up

**Q:** Is there any scenario where NOT storing the key in the node would be acceptable?

**A:** Only if you replace the eviction step with a different reverse-lookup mechanism — for example, a second Map from `node reference → key`. That is strictly worse: double the Map memory, double the write overhead on every insert and evict, and no performance gain. Storing the key directly in the node is the canonical solution.
