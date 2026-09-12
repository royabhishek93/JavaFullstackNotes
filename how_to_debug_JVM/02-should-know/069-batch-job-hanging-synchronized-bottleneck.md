# #69 — Batch Job Hanging on a Synchronized Bottleneck

> **Category:** Thread Dump Analysis | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"A nightly batch job that processes 1M records hangs at 60% completion. Thread dump shows one thread in RUNNABLE and 49 other threads in BLOCKED state. What's your diagnosis?"

## 😊 Explain It Simply (for anyone)
Picture a highway that narrows from 50 lanes down to a single-lane toll booth. It doesn't matter how many cars (worker threads) you have — every single one must funnel through that one toll booth (a shared lock) one at a time. If the toll booth attendant is slow — say, they're also writing a receipt to a paper ledger by hand — everyone behind them piles up into a massive traffic jam, even though 49 lanes of highway sit completely open and unused right before the booth.

This is called a **synchronized bottleneck**: one thread is doing legitimate, slow work (like writing to a file or database) while holding a lock, and every other thread grinds to a halt waiting for that same lock, no matter how many threads you throw at the problem. Adding more cars to the highway doesn't help if there's still only one toll booth.

## 📊 Visualize It
```
worker-1 (RUNNABLE)
  └─ holds lock ──► writeResult() [slow I/O]

worker-2  BLOCKED ┐
worker-3  BLOCKED ├─ all 49 waiting on SAME lock
worker-4  BLOCKED ┘
   ...
worker-50 BLOCKED

  (Amdahl's Law: 1 serialized section caps parallelism)
```

## 🏭 The Real Production Answer (15-YOE Level)
"One thread RUNNABLE, 49 BLOCKED on it — this is a synchronized bottleneck. One thread holds a lock and is doing something slow (likely I/O — DB write, file write), and all other threads are queued behind it waiting for that monitor.

In the thread dump I'd see something like:

```
"batch-worker-2" BLOCKED on 0x000000076c3a2318 (a com.corp.BatchProcessor)
  at com.corp.BatchProcessor.writeResult(BatchProcessor.java:142)
  - waiting to lock <0x000000076c3a2318>

"batch-worker-1" RUNNABLE
  at com.corp.BatchProcessor.writeResult(BatchProcessor.java:142)
  - locked <0x000000076c3a2318>
  at java.io.BufferedWriter.write(BufferedWriter.java:...)
```

The fix depends on what's in that synchronized block. If it's a shared output stream, I'd switch to a concurrent queue where workers enqueue results and a dedicated writer thread drains it. If it's a shared counter, replace with `AtomicLong`. If it's updating shared state, consider thread-local accumulators with a merge step.

This is Amdahl's Law in practice — that one serialized section caps your parallelism ceiling no matter how many threads you add."

## 🔑 Key Takeaway
One RUNNABLE thread with dozens BLOCKED behind it means a serialized bottleneck inside a `synchronized` block — replace shared mutable state with a concurrent queue or atomic type instead of adding more worker threads.
