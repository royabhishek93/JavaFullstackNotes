# Task Scheduler — Cheat Sheet
> **Topic:** Task Scheduler | **Level:** Reference | **Frequency:** High

```
CORE PATTERN
============
class TaskScheduler {
  constructor(concurrency)     // max concurrent tasks
  addTask(task) -> Promise     // task is () => Promise
  runNextTask()                // internal: dequeue + start
}

STATE
=====
runningTasks    integer   currently executing (in-flight promises)
waitingQueue    array     { task, resolve, reject } entries (FIFO)

FLOW
====
addTask(fn):
  new Promise((resolve, reject) => {
    waitingQueue.push({ fn, resolve, reject })
    runNextTask()
  })
  // returns Promise — caller awaits this

runNextTask():
  if runningTasks >= concurrency OR queue empty → return
  const { task, resolve, reject } = waitingQueue.shift()
  runningTasks++
  new Promise(r => r(task()))    // safely wraps sync throws
    .then(resolve)               // settle caller's Promise on success
    .catch(reject)               // settle caller's Promise on failure
    .finally(() => {
      runningTasks--             // ALWAYS free the slot
      runNextTask()              // ALWAYS try to start next task
    })

CRITICAL CORRECTNESS RULES
===========================
1. Use .finally(), NOT .then() — .then() leaks slots on task failure
2. Wrap task() call to catch sync throws:
     new Promise(r => r(task()))  — NOT  Promise.resolve(task())
3. No await between queue.shift() and runningTasks++ — keeps the block atomic
4. No race conditions in single-threaded JS — no mutex needed

COMPLEXITY
==========
addTask:      O(1) amortized
runNextTask:  O(1)
Space:        O(queue size)

EXTENSIONS
==========
Priority:        Replace array with min-heap; addTask(task, priority)
Timeout:         Compose with Promise.race([task(), timeoutPromise(ms)])
Dynamic limit:   setConcurrency(n) + loop runNextTask() for new slots
Pause/resume:    Add paused flag; runNextTask() returns early if paused
Retry:           Wrap task in retry loop before pushing to queue
Rate limiting:   Add token bucket check in runNextTask before dequeue

REAL-WORLD EQUIVALENTS
======================
p-limit:        pLimit(N)(() => fn())               — in-process
BullMQ Worker:  new Worker('q', fn, {concurrency:N}) — distributed, Redis-backed
Java:           Executors.newFixedThreadPool(N)      — true threads
Kafka:          max.poll.records per consumer        — partition-level

USAGE PATTERNS
==============

Batch with results:
  const results = await Promise.all(
    items.map(item => scheduler.addTask(() => processItem(item)))
  );

Fire and forget with error capture:
  scheduler.addTask(myTask).catch(err => logger.error(err));

Timeout composition:
  scheduler.addTask(withTimeout(myTask, 5000));

Per-request scheduler (isolated concurrency):
  async function handleRequest(req) {
    const s = new TaskScheduler(3);  // fresh scheduler per request
    await Promise.all(subtasks.map(t => s.addTask(t)));
  }

INTERVIEW TALKING POINTS
=========================
- Why store resolve/reject in queue: addTask returns a Promise immediately,
  but execution is deferred. The callbacks connect that outer Promise
  to the task's eventual outcome.
- Why no race condition: JS is single-threaded; microtasks execute
  sequentially; no mutex needed.
- Why .finally not .then: .then skips on rejection, leaking slots permanently.
- Why wrap task(): task() may throw synchronously before returning a Promise;
  wrapping in new Promise captures that throw as a rejection.
```
