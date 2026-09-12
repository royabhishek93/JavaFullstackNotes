# Synchronous Throw Edge Case (Senior Trap)
> **Topic:** Task Scheduler | **Level:** Senior Trap | **Frequency:** Medium

## The Setup

`Promise.resolve(task())` looks safe but has a subtle bug: `task()` is called synchronously before `Promise.resolve` receives anything. If `task()` throws, the exception propagates out of `runNextTask()` as an uncaught synchronous exception — `runningTasks` was already incremented, but `.finally()` never runs to decrement it. The slot is leaked and the scheduler is broken.

## The Question

"What happens if a task function throws synchronously instead of returning a rejected Promise? Does `Promise.resolve(task())` handle this? How do you fix it?"

## Diagram

```
Promise.resolve(task()) — execution order:
===========================================

  Step 1: task() is called SYNCHRONOUSLY
          ← if task() throws here, the throw exits runNextTask()
          ← runningTasks was already incremented (line above)
          ← .finally() never runs → slot permanently leaked

  Step 2 (only if step 1 succeeds): Promise.resolve(result)
          ← wraps the return value in a resolved Promise

new Promise(r => r(task())) — execution order:
===============================================

  The Promise constructor callback runs synchronously.
  r(task()) is called:
    Step 1: task() is called SYNCHRONOUSLY
            if task() throws → the Promise constructor catches it
            → Promise is created in REJECTED state
    Step 2: .catch(reject) runs → caller's Promise rejects cleanly
    Step 3: .finally() runs → slot freed, runNextTask() called

  The throw is CAPTURED inside the Promise, not propagated.
```

## Model Answer (15 YOE)

```js
// Task that throws synchronously (not a rejected promise)
const badTask = () => { throw new Error('sync throw'); };

scheduler.addTask(badTask);
```

With `Promise.resolve(task())`:

```js
runNextTask() {
  // ...
  this.runningTasks++;

  Promise.resolve(task())  // ← task() throws HERE, BEFORE Promise.resolve sees it
    .then(resolve)
    .catch(reject)
    .finally(() => {
      this.runningTasks--;   // NEVER REACHED
      this.runNextTask();    // NEVER REACHED
    });
  // The throw propagates out of runNextTask() as an uncaught exception
  // runningTasks remains inflated — slot leaked forever
}
```

The fix:

```js
// Option 1: new Promise constructor (preferred)
new Promise(r => r(task()))
// The Promise constructor wraps the entire callback in a try/catch.
// Any synchronous throw from task() becomes a rejected Promise.
// .catch(reject) and .finally() run correctly.

// Option 2: Promise.resolve().then(() => task())
// Defers task() into a microtask, so the throw becomes an async rejection.
// Slightly more overhead but equally correct.
```

Why this matters in production: validation logic is often synchronous. A task that validates input before making an API call might throw `new Error('invalid input')` synchronously. The scheduler must handle this without leaking slots.

```js
// Example: sync throw in a real task
const processOrderTask = () => {
  if (!order.userId) throw new Error('Missing userId'); // sync throw
  return fetch('/api/process', { body: JSON.stringify(order) }); // async
};
```

Without the fix, one bad order permanently leaks a slot. With 5 such orders, a `concurrency=5` scheduler deadlocks.

## Why It's a Trap

`Promise.resolve(value)` is the most common way to "promisify" a synchronous value, and candidates use it without thinking about call order. The phrase "wraps the result in a Promise" is true — but `task()` runs before `Promise.resolve` gets to wrap anything. The fix is non-obvious: `new Promise(r => r(task()))` works because the Promise constructor's executor is wrapped in a try/catch by the spec.

## What NOT to Say

- "`Promise.resolve(task())` catches synchronous throws" — it does not.
- "Tasks should never throw synchronously" — this is not something you can enforce in a general-purpose scheduler.
- "You can add a try/catch around the whole thing" — a try/catch outside `Promise.resolve(task())` would work but is less idiomatic than `new Promise(r => r(task()))`.

## Follow-up

**Q:** "Does `async function` wrap synchronous throws automatically?"

**A:** Yes. An `async function` always returns a Promise. If the function body throws synchronously before any `await`, the returned Promise is rejected. But `runNextTask()` is not `async` — it would need to be redesigned. The `new Promise` form is simpler and does not require making `runNextTask` async.
