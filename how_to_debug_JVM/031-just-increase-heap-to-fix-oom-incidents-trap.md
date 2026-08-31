# #31 — "Just Increase the Heap to Fix OOM Incidents"

> **Category:** Common Production Incidents | **Type:** Senior Trap Question | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"We keep hitting OutOfMemoryError — let's just increase the heap size and move on, right?"

## 😊 Explain It Simply (for anyone)
If your closet keeps overflowing because you never throw anything away, buying a bigger closet doesn't fix the hoarding problem — it just means the mess takes longer to become visible, and when it finally does overflow again, there's a lot more junk to sort through to find what went wrong. Making the heap bigger for a genuine leak is exactly this: it delays the crash, but the crash still comes, and now the "clean-up investigation" (a heap dump analysis) takes even longer because there's more data to sift through. The right first step is figuring out whether you're dealing with a true leak (something never gets thrown away, no matter what) or just a pool of memory that's honestly too small for legitimate peak demand.

## 📊 Visualize It
```
Leak (bigger heap just delays it):
  Old Gen: grows steadily regardless of load, NEVER drops
  -> bigger heap = OOM in 14 days instead of 7 (still crashes eventually)

Undersized heap (bigger heap actually helps):
  Old Gen: fills on peak load, DRAINS during low load
  -> bigger heap = handles peak fine, no leak present
```

## 🏭 The Real Production Answer (15-YOE Level)
**WRONG** (for leaks). Increasing heap for a memory leak:
- Delays the OOM by days or weeks
- Makes heap dumps slower and harder to analyze (4GB dump vs 2GB dump)
- Can increase Full GC pause times when they do occur (more to scan)
- Is not an engineering solution

**Correct answer:** First determine if OOM is from a leak or from undersized heap. Heap is undersized if: Old Gen fills on peak load but drains during low load. It's a leak if: Old Gen grows steadily regardless of load and never drops. Only increase heap for the undersized case. For leaks, find and fix the retention.

## 🔑 Key Takeaway
Check whether Old Gen drains during low-load periods before touching `-Xmx` — if it never drains, you have a leak that a bigger heap will only postpone.
