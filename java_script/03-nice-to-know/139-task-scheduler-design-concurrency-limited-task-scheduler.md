# Design a Concurrency-Limited Task Scheduler — Core Pattern
> **Topic:** Task Scheduler | **Level:** Fundamental | **Frequency:** High

## The Setup

JavaScript is single-threaded. "Concurrent tasks" does not mean parallel CPU threads — it means N promises are in-flight at the same time (waiting on I/O, network, timers). Without a limit, 10,000 incoming orders launch 10,000 simultaneous `fetch` calls, hammering the database and exhausting connection pools. A task scheduler is the foundational pattern for controlling this.

## The Question

"Design and implement a TaskScheduler class that accepts a concurrency limit. Any number of tasks can be submitted, but at most `N` run simultaneously. Tasks submitted while all slots are full wait in a queue and execute as slots free up. Each `addTask` call returns a Promise that resolves or rejects with the task's own result."

## Diagram

```
CONCURRENCY SLOTS + QUEUE  (concurrency = 2)
=============================================

  RUNNING SLOTS           WAITING QUEUE
  ┌──────────┐            ┌────┬────┬────┐
  │  Task 1  │            │ T3 │ T4 │ T5 │
  ├──────────┤            └────┴────┴────┘
  │  Task 2  │              head      tail
  └──────────┘
  (both slots full — T3, T4, T5 wait)

  Task 2 finishes → slot opens → runNextTask() dequeues T3
  ┌──────────┐            ┌────┬────┐
  │  Task 1  │            │ T4 │ T5 │
  ├──────────┤            └────┴────┘
  │  Task 3  │
  └──────────┘

CHAIN REACTION: every .finally() calls runNextTask(),
which immediately fills the freed slot from the queue.

ASCII TIMELINE (concurrency=2, durations shown)
================================================

t=0ms   ├──────────────────── Task1 (2000ms) ─────────────────────┤
t=0ms   ├────── Task2 (1000ms) ──────┤
t=1000  (T2 done → T3 starts)        ├──── Task3 (500ms) ────┤
t=1500  (T3 done → T4 starts)                                 ├─ T4 (300ms) ─┤
t=1800  (T4 done → T5 starts)                                               ├───── Task5 (800ms) ─────┤
t=2000  (T1 done)
t=2600                                                                                                  (T5 done)

At no moment do more than 2 tasks overlap.
```

## Model Answer (15 YOE)

```js
class TaskScheduler {
  constructor(concurrency) {
    if (concurrency < 1) throw new Error('Concurrency must be at least 1');
    this.concurrency = concurrency;
    this.runningTasks = 0;
    this.waitingQueue = [];  // each entry: { task, resolve, reject }
  }

  addTask(task) {
    return new Promise((resolve, reject) => {
      this.waitingQueue.push({ task, resolve, reject });
      this.runNextTask();
    });
  }

  runNextTask() {
    if (this.runningTasks >= this.concurrency || this.waitingQueue.length === 0) {
      return;
    }

    const { task, resolve, reject } = this.waitingQueue.shift();
    this.runningTasks++;

    new Promise(r => r(task()))   // safely captures synchronous throws
      .then(resolve)
      .catch(reject)
      .finally(() => {
        this.runningTasks--;
        this.runNextTask();
      });
  }
}
```

Usage:

```js
const scheduler = new TaskScheduler(3);

const results = await Promise.all(
  tasks.map(task => scheduler.addTask(() => processTask(task)))
);
```

Walk through the design decisions:

1. **`addTask` returns a Promise** — the caller can `await` or `.then()` it to get the result. The Promise is created immediately and stored in the queue. The task runs later.
2. **`resolve` and `reject` are stored in the queue** — because the task runs asynchronously, we need to hold the callbacks to settle the caller's Promise when the task eventually finishes.
3. **`.finally()` not `.then()`** — `.then()` only runs on success. A failed task would never decrement `runningTasks`, permanently leaking a slot.
4. **`new Promise(r => r(task()))` not `Promise.resolve(task())`** — if `task()` throws synchronously, `task()` throws before `Promise.resolve` can see it. The `new Promise` form captures sync throws as rejections.
5. **No `await` between `shift()` and `runningTasks++`** — keeps the block atomic. No other JS can interleave.

## Follow-up

**Q:** "Why not use `Promise.all` directly?"

**A:** `Promise.all` launches all tasks simultaneously. With 1,000 tasks, that is 1,000 in-flight promises with no throttling. DB connection pools have limits (typically 20–100). A scheduler caps concurrency to match the bottleneck's capacity.

**Q:** "What is the right concurrency number?"

**A:** Match it to the bottleneck. If the DB pool has 20 connections and each task uses one, set `concurrency = 15` (leave headroom for other processes). For CPU-bound work, set it to the number of cores.
