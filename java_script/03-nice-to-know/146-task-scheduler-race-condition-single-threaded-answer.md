# Race Condition Question — JS Single-Threaded Answer (Senior Trap)
> **Topic:** Task Scheduler | **Level:** Senior Trap | **Frequency:** Medium

## The Setup

Interviewers ask this to catch candidates who apply multi-threaded reasoning to JavaScript. Two `.finally()` callbacks "firing simultaneously" sounds like a race condition. It is not. The correct answer requires explaining the microtask queue and JavaScript's run-to-completion execution model.

## The Question

"Can there be a race condition in this scheduler when two tasks finish simultaneously? Both `.finally()` callbacks fire at the same time — could they both read `runningTasks` at the old value and double-decrement incorrectly?"

## Diagram

```
EVENT LOOP — two tasks finishing in the same tick:
====================================================

  t=1000ms: T2 and T3 both resolve (their I/O completed)

  Microtask queue after both resolve:
    [ T2's .finally() callback, T3's .finally() callback ]
                                        ↑
                          queued, NOT executing simultaneously

  Microtask 1 executes:
    T2's .finally() → runningTasks: 2 → 1 → runNextTask() → T4 starts
    (T3's .finally() is still in the queue, has not run)

  Microtask 2 executes:
    T3's .finally() → runningTasks: 1 → 0 → runNextTask() → T5 starts

  Result: runningTasks is always a correct integer.
  No mutex needed. No atomic operation needed.

COMPARE: multi-threaded language (Java):
  Thread A and Thread B run TRULY simultaneously on different CPUs.
  Both read runningTasks = 2.
  Both write runningTasks = 1.
  Result: one decrement is lost — runningTasks should be 0 but is 1.
  Fix: synchronized block or AtomicInteger.
```

## Model Answer (15 YOE)

No. There are no race conditions in this scheduler. JavaScript is single-threaded.

"Two tasks finishing simultaneously" means their Promises resolved in the same event loop tick. Their `.finally()` callbacks are placed in the microtask queue — a FIFO queue that executes completely between each macro-task. Microtasks execute one at a time, sequentially. No two JavaScript callbacks ever execute in parallel.

```
Event loop tick:
  Microtask 1: T2's .finally() runs → runningTasks: 2→1, runNextTask() called, T4 starts
  Microtask 2: T3's .finally() runs → runningTasks: 1→0, runNextTask() called, T5 starts

These execute sequentially. runningTasks is always a correct integer.
```

In a multi-threaded language (Java, Go, Rust), two threads can read `runningTasks` simultaneously, each see the old value, and each write back `oldValue - 1` — losing one decrement. This requires a mutex or atomic operation to fix.

In JavaScript, that scenario is impossible. Between the read and the write of `runningTasks`, no other JavaScript executes. The callback runs to completion before the next callback starts.

The only time JavaScript behaves otherwise: `SharedArrayBuffer` + `Atomics` with Web Workers gives true shared memory across threads. That is the one scenario where JS needs atomic operations. This scheduler does not use shared memory, so no mutex is needed.

## Why It's a Trap

The question is deliberately phrased to trigger multi-threaded intuition. Candidates who learned concurrency in Java or C++ immediately think "race condition" and reach for locks. This reveals that they do not understand JavaScript's execution model. The correct answer earns points not just for being right but for demonstrating deep understanding of the event loop.

## What NOT to Say

- "Yes, we need a mutex or lock" — there is no mutex in JS (except with SharedArrayBuffer).
- "We should use `Atomics.add()` to decrement safely" — only needed for SharedArrayBuffer across Workers.
- "JavaScript is single-threaded so concurrency isn't possible" — concurrency IS possible (multiple in-flight promises), but parallelism is not. The distinction matters.

## Follow-up

**Q:** "Is there any scenario in this scheduler where execution order could be surprising even without a race condition?"

**A:** Yes. If `runNextTask()` is called re-entrantly — for example, if a task's completion triggers `addTask` which calls `runNextTask()` again inside the same microtask — you could see unexpected ordering. But this is deterministic, not a race. JavaScript's run-to-completion guarantee means you can always reason about the exact execution order; you just need to trace the call stack carefully.
