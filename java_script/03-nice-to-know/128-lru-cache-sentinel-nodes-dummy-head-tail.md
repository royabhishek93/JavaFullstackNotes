# Sentinel Nodes — Why Dummy Head and Tail
> **Topic:** LRU Cache | **Level:** Fundamental | **Frequency:** Medium

## The Setup

You are implementing an LRU cache and have your Node class and HashMap ready. Before writing `removeNode` and `insertAtHead`, your interviewer asks about the two extra nodes you initialized in the constructor.

## The Question

What are sentinel (dummy) nodes? Why do you create a dummy `head` and a dummy `tail` that are never evicted and never returned to callers?

## Diagram

```
WITHOUT SENTINELS — every operation needs null checks
=======================================================
  Empty cache:   head = null,  tail = null

  insertAtHead(A) when empty:
    if (head === null) { head = A; tail = A; A.prev = null; A.next = null; }
    else { A.next = head; head.prev = A; head = A; }   ← two branches

  removeNode(A) when A is the only node:
    if (A.prev) A.prev.next = A.next; else head = A.next;
    if (A.next) A.next.prev = A.prev; else tail = A.prev;
                                         ← four conditional branches

WITH SENTINELS — zero null checks in any operation
====================================================
  Empty cache:
    HEAD (dummy) ◄──► TAIL (dummy)

  insertAtHead(A):
    A.next = HEAD.next  →  A.next = TAIL
    A.prev = HEAD
    HEAD.next.prev = A  →  TAIL.prev = A    ← always safe, TAIL always exists
    HEAD.next = A
    Result:  HEAD ◄──► [A] ◄──► TAIL

  removeNode(A) when A is the only real node:
    A.prev.next = A.next  →  HEAD.next = TAIL   ← always safe
    A.next.prev = A.prev  →  TAIL.prev = HEAD   ← always safe
    Result:  HEAD ◄──► TAIL   (back to empty)
```

## Model Answer (15 YOE)

"Sentinel nodes are permanent dummy nodes at each end of the list. They are never evicted and never stored in the HashMap — they exist purely to eliminate conditional logic in `removeNode` and `insertAtHead`.

Without sentinels, every pointer operation needs null checks: 'is this node the head? is it the tail? is the list empty?' That is four conditional branches in `removeNode` alone — and a source of subtle bugs. With sentinels, every real node always has valid `prev` and `next` neighbors. The two pointer writes in `removeNode` work identically whether the node is in the middle of the list, at the front, or the last real node.

The initialization is simple:

```js
this.head = new Node(0, 0);  // dummy — never evicted
this.tail = new Node(0, 0);  // dummy — never evicted
this.head.next = this.tail;
this.tail.prev = this.head;
```

The invariant that holds for the lifetime of the cache: `head.next` is the MRU real node (or `tail` if empty), and `tail.prev` is the LRU real node (or `head` if empty). Eviction is always `tail.prev` — no null check needed."

## Follow-up

**Q:** Are there other data structures that use this sentinel pattern?

**A:** Yes. Doubly linked list implementations in operating system kernels (Linux `list_head`), Java's `LinkedList` internal structure, and many parser implementations use sentinel/dummy nodes to collapse edge cases. The pattern trades two extra heap allocations for unconditional, branch-free pointer manipulation — a worthwhile trade whenever the list is modified frequently.
