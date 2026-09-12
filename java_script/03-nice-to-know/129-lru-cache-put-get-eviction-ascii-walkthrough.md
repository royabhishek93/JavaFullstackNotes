# Full Step-by-Step ASCII Walkthrough: put / get / eviction Sequence
> **Topic:** LRU Cache | **Level:** Fundamental | **Frequency:** High

## The Setup

Capacity = 3. Walk through five operations in order: `put(A,1)` → `put(B,2)` → `put(C,3)` → `get(A)` → `put(D,4)`. Show the list state and Map state after each step.

## The Question

Trace every pointer change. After `get(A)`, which node becomes LRU? When `put(D,4)` fires, which node is evicted and why?

## Diagram

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Step 1: put(A, 1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HEAD ◄──► [ A | 1 ] ◄──► TAIL
  Map: { A → nodeA }
  Size: 1 / 3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Step 2: put(B, 2)  — B is newer, goes to head
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HEAD ◄──► [ B | 2 ] ◄──► [ A | 1 ] ◄──► TAIL
  Map: { A → nodeA, B → nodeB }
  Size: 2 / 3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Step 3: put(C, 3)  — cache now FULL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HEAD ◄──► [ C | 3 ] ◄──► [ B | 2 ] ◄──► [ A | 1 ] ◄──► TAIL
  Map: { A → nodeA, B → nodeB, C → nodeC }
  Size: 3 / 3   ← FULL
         MRU ↑                              ↑ LRU

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Step 4: get(A)  — A accessed: detach from tail area, move to head
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  BEFORE:  HEAD ◄──► [ C | 3 ] ◄──► [ B | 2 ] ◄──► [ A | 1 ] ◄──► TAIL
                                                          ↑ removeNode(A)
  AFTER:   HEAD ◄──► [ A | 1 ] ◄──► [ C | 3 ] ◄──► [ B | 2 ] ◄──► TAIL
                          ↑ insertAtHead(A)
  Map: unchanged          MRU                              LRU
  Returns: 1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Step 5: put(D, 4)  — full: evict LRU = tail.prev = B
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  EVICT:  tail.prev = nodeB  →  removeNode(B), map.delete("B")
  INSERT: insertAtHead(nodeD)

  RESULT: HEAD ◄──► [ D | 4 ] ◄──► [ A | 1 ] ◄──► [ C | 3 ] ◄──► TAIL
  Map: { A → nodeA, C → nodeC, D → nodeD }
  B is gone. get("B") → -1
```

## Model Answer (15 YOE)

"The key moment is Step 4. Before `get(A)`, the LRU was A — it was the oldest insertion and had not been touched since. Accessing it with `get` promotes it to MRU via two operations: `removeNode` detaches A from its current position using two pointer writes (its neighbors wire around it), then `insertAtHead` splices A between the head sentinel and the previous MRU node using four pointer writes. After promotion, B becomes the new LRU because C was inserted more recently than B.

In Step 5, `put(D,4)` finds the cache full. The eviction target is always `tail.prev` — no scanning, no comparison, just a direct pointer read. That is nodeB. We call `removeNode(nodeB)` and `map.delete(nodeB.key)`. The key stored inside the node (`nodeB.key = 'B'`) is what makes the Map deletion O(1) — without it we would have to scan the entire Map.

The final state has A, C, D — in that recency order from head. B is permanently gone."

## Follow-up

**Q:** What would happen if we called `get(B)` after Step 5?

**A:** `map.has("B")` returns `false` — the Map entry was deleted during eviction. `get` returns `-1`. The node object for B still exists in memory until garbage collected, but it is unreachable from both the Map and the list.
