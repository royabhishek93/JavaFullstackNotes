# Why Store resolve/reject in the Queue
> **Topic:** Task Scheduler | **Level:** Fundamental | **Frequency:** High

## The Setup

A common candidate mistake is to push only the `task` function into the queue and call `task()` directly inside `runNextTask()`, then return the result somehow. But `addTask` must return a Promise *immediately* — before the task has run. Understanding why `resolve` and `reject` must travel with the task in the queue is the key to understanding deferred Promise resolution.

## The Question

"Why does each queue entry store `{ task, resolve, reject }` instead of just `{ task }`? Why can't you just call `task()` inside `runNextTask()` and return the result directly?"

## Diagram

```
TIMELINE
=========

  t=0  caller: const p = scheduler.addTask(fn)
       addTask creates: new Promise((resolve, reject) => { ... })
       addTask pushes: { task: fn, resolve, reject } into queue
       addTask returns: Promise p  ← caller has this IMMEDIATELY
       (fn has NOT run yet)

  t=0  runNextTask() sees slots full → returns early

  t=500ms  another task finishes → slot freed → runNextTask() called
           dequeues { task: fn, resolve, reject }
           calls fn()
           fn resolves with 42
           .then(resolve) → resolve(42) → Promise p settles with 42

  t=500ms  caller's await resumes with 42

THE BRIDGE:
  resolve / reject are the ONLY link between
  the Promise p (created at t=0) and
  the task result (available at t=500ms).
  Without them stored in the queue, there is no way to settle p.
```

## Model Answer (15 YOE)

`addTask` must return a Promise immediately — the caller uses it to `await` the result or chain `.then()`. This Promise is created at call time, but the task will not execute until a slot opens, which could be milliseconds or seconds later.

```js
addTask(task) {
  return new Promise((resolve, reject) => {
    // resolve and reject are captured here, inside the Promise constructor
    // They are the ONLY way to settle this specific Promise instance
    this.waitingQueue.push({ task, resolve, reject });
    this.runNextTask();
  });
}
```

When the task eventually runs in `runNextTask()`:

```js
const { task, resolve, reject } = this.waitingQueue.shift();
this.runningTasks++;

new Promise(r => r(task()))
  .then(resolve)   // ← resolve settles the Promise that addTask returned
  .catch(reject);  // ← reject settles the Promise that addTask returned
```

The `resolve` and `reject` callbacks are the bridge between two separate moments in time: the moment `addTask` was called (the Promise was created) and the moment the task actually ran (the Promise is settled).

Why you cannot "just return the result directly":

```js
// IMPOSSIBLE — runNextTask is called asynchronously, after addTask already returned
addTask(task) {
  this.waitingQueue.push(task);
  this.runNextTask();
  return ???;  // task hasn't run yet — there's no result to return
}
```

This is the fundamental reason why deferred execution requires storing the Promise callbacks: the return value of `addTask` must be a Promise (created now), and the only way to settle that Promise later is via `resolve`/`reject` closures that were captured when the Promise was constructed.

## Follow-up

**Q:** "Could you use a different signalling mechanism — like an EventEmitter or a custom observable — instead of storing resolve/reject?"

**A:** Yes, technically. But Promises are the standard async primitive in JS. Using resolve/reject means callers can use `await`, `.then()`, `Promise.all()`, and all standard Promise combinators with no extra setup. An EventEmitter approach would require callers to learn a custom API and handle their own sequencing.

**Q:** "What if the task is synchronous and returns a value immediately — does the queue entry still need resolve/reject?"

**A:** Yes. Even if the task is synchronous, `runNextTask` is called asynchronously (after `addTask` returns). The Promise returned by `addTask` has already been created and returned to the caller before the task runs. `resolve` and `reject` are still the only bridge.
