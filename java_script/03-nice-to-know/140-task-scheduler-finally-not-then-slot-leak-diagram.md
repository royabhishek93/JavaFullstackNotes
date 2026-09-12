# Why .finally() Not .then() — The Slot Leak Diagram
> **Topic:** Task Scheduler | **Level:** Fundamental | **Frequency:** High

## The Setup

Using `.then()` to decrement `runningTasks` is the single most common implementation mistake in a task scheduler. It looks correct — but on any task failure, the slot is permanently leaked. The scheduler silently accumulates ghost slots and eventually stalls. This scenario is a litmus test for whether a candidate understands Promise chain semantics.

## The Question

"What happens if you use `.then()` to decrement `runningTasks` and call `runNextTask()` instead of `.finally()`? Show the failure mode step by step."

## Diagram

```
SLOT LEAK — step by step  (concurrency = 3)
============================================

  Initial: T1, T2, T3 running. T4, T5 in queue.

  T2 throws an error.

  BROKEN implementation:
  .then(result => {
    resolve(result);
    this.runningTasks--;   // ← only on SUCCESS
    this.runNextTask();
  })
  .catch(err => {
    reject(err);
    // runningTasks NEVER decremented ← BUG
    // runNextTask() NEVER called     ← BUG
  });

  State after T2 failure:
    runningTasks = 3  (T2's slot was never freed — ghost slot)
    T4, T5 still in queue — waiting forever for a slot

  T1 finishes → runningTasks = 2 → T4 starts
  T3 finishes → runningTasks = 1 → T5 starts

  After T4 and T5 complete:
    runningTasks = 1  (ghost slot from T2 persists)

  Next failure → runningTasks = 2 (two ghosts)
  After enough failures → scheduler thinks it is at capacity
  → all new tasks queue forever → DEADLOCK
```

## Model Answer (15 YOE)

```js
// BROKEN implementation
Promise.resolve(task())
  .then(result => {
    resolve(result);
    this.runningTasks--;   // only runs on SUCCESS
    this.runNextTask();
  })
  .catch(err => {
    reject(err);
    // runningTasks is NEVER decremented on failure
    // runNextTask() is NEVER called
  });
```

The slot leak is silent. No exception is thrown. The scheduler appears to work for successful tasks. But every failed task permanently inflates `runningTasks` by 1. Over time, the scheduler reaches a state where `runningTasks >= concurrency` is always true, `runNextTask()` always returns early, and all queued tasks wait forever.

The fix:

```js
new Promise(r => r(task()))
  .then(resolve)    // settle caller's Promise on success
  .catch(reject)    // settle caller's Promise on failure
  .finally(() => {
    this.runningTasks--;   // ALWAYS runs — success or failure
    this.runNextTask();    // ALWAYS picks the next task
  });
```

Three responsibilities, clearly separated:
- `.then(resolve)` — tell the caller their task succeeded
- `.catch(reject)` — tell the caller their task failed
- `.finally(...)` — scheduler bookkeeping, completely independent of outcome

`.finally()` does not receive the resolved value or the rejection reason. It just runs cleanup. This is exactly what we need: the scheduler does not care about the task's result — it only cares that the slot is freed.

## Follow-up

**Q:** "Does `.finally()` change the Promise chain's value?"

**A:** No. `.finally()` is transparent to the value. If the Promise resolved with `42`, a `.finally()` that returns nothing still passes `42` down the chain. If `.finally()` throws, it converts the chain to a rejection. If `.finally()` returns a Promise, the chain waits for it to settle before continuing.

**Q:** "In the broken implementation, could you just move `runningTasks--` and `runNextTask()` into both `.then()` and `.catch()`?"

**A:** Yes, that also fixes the bug, but it duplicates code. `.finally()` is the idiomatic, DRY solution for logic that must run regardless of outcome. Using `.finally()` also protects against future edits adding a second `.catch()` that forgets to include the cleanup.
