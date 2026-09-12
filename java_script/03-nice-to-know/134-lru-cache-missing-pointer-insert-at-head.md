# Missing Pointer in insertAtHead — The Common Bug
> **Topic:** LRU Cache | **Level:** Senior Trap | **Frequency:** High

## The Setup

The interviewer shows you this partial implementation of `insertAtHead` and asks you to find the bug. Candidates who memorize the algorithm without understanding pointer direction always miss it.

## The Question

What is wrong with this implementation? What silent corruption does it cause, and when does the corruption become visible?

```js
insertAtHead(node) {
  node.next = this.head.next;
  node.prev = this.head;
  // ??? something missing here
  this.head.next = node;
}
```

## Diagram

```
BEFORE insertAtHead(C):
  HEAD ◄──► [ B ] ◄──► [ A ] ◄──► TAIL
  HEAD.next = B      B.prev = HEAD

CORRECT insertAtHead(C) — all 4 pointer updates:
  (1) C.next = HEAD.next  →  C.next = B
  (2) C.prev = HEAD
  (3) HEAD.next.prev = C  →  B.prev = C       ← THE MISSING LINE
  (4) HEAD.next = C

  Result:
  HEAD ◄──► [ C ] ◄──► [ B ] ◄──► [ A ] ◄──► TAIL
  HEAD.next=C  C.prev=HEAD  C.next=B  B.prev=C  ✓

BUGGY insertAtHead(C) — missing line (3):
  HEAD  →  [ C ]  →  [ B ]  →  [ A ]  →  TAIL
  HEAD.next=C  C.prev=HEAD  C.next=B  B.prev=HEAD  ✗
                                          ↑ B still points BACK to HEAD, not C

  Forward traversal (HEAD → next):  HEAD → C → B → A  (appears correct)
  Backward traversal (TAIL → prev): TAIL → A → B → HEAD  (C is INVISIBLE)

CORRUPTION BECOMES VISIBLE — when removeNode(B) is later called:
  removeNode uses backward pointers:
    B.prev.next = B.next  →  HEAD.next = A   (skips C entirely — C is lost!)
    B.next.prev = B.prev  →  A.prev = HEAD

  After removeNode(B):
  List: HEAD ◄──► [ A ] ◄──► TAIL
  Map:  { C → nodeC, A → nodeA }   ← C is in the Map but NOT in the list

  Ghost key: map.get("C") returns nodeC,
             but nodeC is unreachable via list traversal.
             Eviction logic based on tail.prev will never reach C.
             C occupies a cache slot indefinitely — memory leak.
```

## Model Answer (15 YOE)

"The missing line is `this.head.next.prev = node`. This updates the backward pointer of the node that was previously first in the list — it needs to point back to the newly inserted node, not to the head sentinel.

`insertAtHead` must make four pointer writes. Two on the new node (its `next` and `prev`), and two on its new neighbors (the head sentinel's `next`, and the old first node's `prev`). The buggy code makes only three — it wires up the new node's pointers and updates the head sentinel, but forgets to update the old first node's backward pointer.

The corruption is silent at first: forward traversal (following `next` pointers from `head`) looks correct. The bug only manifests when a backward pointer is followed — specifically inside `removeNode`, which reads `node.prev`. When the old first node B is later removed, `B.prev` still points to `HEAD` instead of `C`. So `removeNode(B)` sets `HEAD.next = B.next`, jumping over C entirely. C vanishes from the list but remains in the Map — a ghost key that holds a cache slot forever, leaking memory and inflating the apparent size."

## Why It's a Trap

The forward direction of the list looks correct without the missing line. Candidates who only trace `head → next → next` during testing will miss the bug. It surfaces only when a later `removeNode` uses the broken backward pointer. In interviews, candidates who have only memorized the algorithm without building the pointer diagram in their head will write three of the four updates and feel confident.

## What NOT to Say

- "The code looks fine to me" — you did not trace backward pointers
- "It only affects performance" — it silently corrupts the list structure
- "We just need to update `head.next`" — that is line (4), which IS present; the missing line is (3)

## Follow-up

**Q:** Is the order of the four pointer writes in `insertAtHead` important?

**A:** Yes — line (3) must execute before line (4). Line (3) is `this.head.next.prev = node`, which reads `this.head.next` to reach the old first node. If line (4) runs first (`this.head.next = node`), then `this.head.next` now points to the new node, and line (3) would set `node.prev = node` — a self-loop. The safe order: set both of the new node's pointers first (lines 1 and 2), then update the old first node's backward pointer (line 3), then update the head sentinel's forward pointer (line 4).
