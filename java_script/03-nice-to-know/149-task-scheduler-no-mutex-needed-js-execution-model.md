# Why No Mutex Is Needed — JS Single-Threaded Execution Model (Senior Trap)
> **Topic:** Task Scheduler | **Level:** Senior Trap | **Frequency:** Low

## The Setup

Candidates from Java, Go, or C++ backgrounds instinctively reach for locks when they see shared mutable state (`runningTasks`, `waitingQueue`). The trap is that JavaScript's cooperative concurrency model makes explicit synchronisation unnecessary — and understanding *why* demonstrates genuine depth with the event loop.

## The Question

"The scheduler has shared mutable state: `runningTasks` and `waitingQueue`. Multiple tasks can complete at the same time. Why does this implementation not need a mutex, a lock, or any synchronisation primitive?"

## Diagram

```
JS EVENT LOOP — run-to-completion guarantee:
============================================

  Each task in the event loop runs to completion.
  No other JS can execute while a callback is running.
  Context switch only happens at await points.

  runNextTask() synchronous block:
  ─────────────────────────────────
  const entry = this.waitingQueue.shift();   ← read
  this.runningTasks++;                        ← write
  Promise.resolve(...)                        ← starts async work

  Between shift() and runningTasks++:
    → No await
    → No other JS executes
    → Block is effectively atomic

  Java equivalent would need:
    synchronized(this) {
      entry = queue.poll();
      runningTasks++;
    }
  Because Thread A and Thread B can truly run this block simultaneously.

MICROTASK QUEUE — sequential execution:
========================================

  T2 and T3 both resolve at t=1000ms.
  Microtask queue: [ T2.finally(), T3.finally() ]

  T2.finally() executes fully:
    runningTasks-- → 2
    runNextTask() → T4 starts

  T3.finally() executes fully:
    runningTasks-- → 1
    runNextTask() → T5 starts

  Always correct. No interleaving possible.
```

## Model Answer (15 YOE)

JavaScript has cooperative, not preemptive, concurrency. A function runs to completion before any other JavaScript runs. The only way execution yields to another context is via `await` (or other async boundaries like `setTimeout`, I/O callbacks). Between any two `await` points, your code is the only thing executing.

In `runNextTask`, the critical section is:

```js
// This entire block runs atomically — no other JS can interrupt between lines
const { task, resolve, reject } = this.waitingQueue.shift();
this.runningTasks++;
// <-- no await here, so nothing can interleave between shift() and increment
new Promise(r => r(task()))...
```

There is no `await` between `shift()` and `runningTasks++`. By JavaScript's run-to-completion rule, no other code can execute between these two lines. The read-modify-write on `runningTasks` is inherently atomic in this model.

The design constraint: if `runNextTask` ever had an `await` between `shift()` and `runningTasks++`, another event loop turn could call `runNextTask` again before the increment happened. The same task could be dequeued and started twice. This is why the implementation keeps the synchronous setup block free of `await` — it is a deliberate architectural choice, not an accident.

```js
// DANGEROUS — hypothetical broken version
async runNextTask() {
  const entry = this.waitingQueue.shift();   // removes entry
  await someCheck();                          // ← yields to event loop
  this.runningTasks++;                        // ← another runNextTask() could
                                              //   run before we get here
}
```

**The one exception in JS: SharedArrayBuffer + Atomics**

`SharedArrayBuffer` lets two Web Workers truly share memory — they run on separate OS threads. In that model, you do need `Atomics.add()` and `Atomics.compareExchange()` for shared counters. But this scheduler runs in a single thread and has no shared memory across workers, so `Atomics` is irrelevant here.

## Why It's a Trap

Multi-threaded engineers see shared mutable state and immediately think "race condition → mutex." They are right in their native environment. The trap is applying that reasoning to JavaScript without knowing the run-to-completion guarantee. Saying "we need a mutex" in a JS interview reveals a gap in understanding the execution model — which is the most fundamental thing a JavaScript architect must know.

## What NOT to Say

- "We need a mutex to protect `runningTasks`" — no mutex exists in single-threaded JS.
- "We should use `Atomics.add()` here" — only applies to SharedArrayBuffer across Workers.
- "There's no concurrency in JS so this is trivial" — there IS concurrency (in-flight promises); there is just no parallelism. The distinction matters.

## Follow-up

**Q:** "If you moved the scheduler to a Worker thread and called it from the main thread, would you then need synchronisation?"

**A:** The scheduler itself would still be single-threaded inside the Worker. The Worker's internal state (`runningTasks`, `waitingQueue`) is not shared with the main thread — Workers communicate via message passing, not shared memory (unless you explicitly use `SharedArrayBuffer`). So no: even in a Worker, the same scheduler implementation is safe.
