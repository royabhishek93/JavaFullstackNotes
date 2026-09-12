# #5 — Shallow Heap vs Retained Heap — The Trap

> **Category:** Heap Dump Analysis | **Type:** Senior Trap Question | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"MAT shows a `HashMap` with shallow heap of 48 bytes. So it's not the memory leak."

## 😊 Explain It Simply (for anyone)
A filing cabinet (a `HashMap` object) itself might weigh almost nothing empty — just the metal frame (that's "shallow heap," the size of the object itself, ignoring its contents). But that same empty-looking cabinet could be the ONLY thing holding open a door to a massive warehouse full of millions of boxes (all its entries and everything they reference) — if you removed the cabinet, the entire warehouse behind it would also become inaccessible and get cleaned up.

That total "everything that disappears if I remove this one thing" weight is called "retained heap," and it's the number that actually tells you whether something is your leak — not the weight of the empty frame sitting in front of it.

## 📊 Visualize It
```
HashMap object itself:        Shallow Heap = 48 bytes  (tiny!)

But what it points to:
  HashMap ──▶ Entry[] ──▶ 40,000,000 entries ──▶ 2.1 GB of data
                                                  (only reachable via this map)

  Retained Heap(HashMap) = 48 bytes + all 2.1 GB behind it = 2.1 GB   ← THE LEAK

MAT fix: sort Dominator Tree by RETAINED HEAP (not shallow heap), descending.
Formula:
  Retained(A) = Shallow(A) + Σ Shallow(B) for every B only reachable through A
```

## 🏭 The Real Production Answer (15-YOE Level)

Shallow heap is almost always irrelevant for identifying leaks. Shallow heap is just the size of the object itself — the header + primitive fields + reference pointers. A `HashMap` wrapper object is 48 bytes whether it holds 0 entries or 40 million.

What matters is **retained heap**: the total memory that would be freed if this object (and everything reachable only through it) were garbage collected.

In MAT:
- Sort the Dominator Tree by **Retained Heap** (descending) — first column to check
- A `HashMap` with 48 bytes shallow heap but 2.1 GB retained heap is your leak root
- Use "Show Retained Heap" option in the histogram view

The formula: `Retained Heap(A) = Shallow(A) + sum of Shallow(B) for all objects B where A is the only path to B from any GC root`

## 🔑 Key Takeaway
Always sort MAT's Dominator Tree by retained heap, not shallow heap — the leak root is often a tiny wrapper object hiding gigabytes behind it.
