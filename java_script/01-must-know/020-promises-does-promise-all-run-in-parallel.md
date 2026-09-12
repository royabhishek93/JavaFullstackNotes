# Does Promise.all Run Promises in Parallel?
> **Topic:** Promises | **Level:** Senior Trap | **Frequency:** High

## The Setup

You are in a technical interview discussing concurrent async operations. The interviewer asks a seemingly simple question about `Promise.all`.

## The Question

"Does `Promise.all` run Promises in parallel?"

## Diagram

```
  Common misconception:
    Promise.all([fetchA(), fetchB(), fetchC()])
              ^-- "Promise.all starts these"   WRONG

  Reality:
    fetchA()   <- Promise CREATED and STARTED here (synchronous call)
    fetchB()   <- Promise CREATED and STARTED here
    fetchC()   <- Promise CREATED and STARTED here
    Promise.all([p1, p2, p3])  <- just observes three already-running Promises

  Evidence:
    const p1 = fetchA();    // starts immediately
    const p2 = fetchB();    // starts immediately
    const p3 = fetchC();    // starts immediately
    // All three are already in flight...
    await Promise.all([p1, p2, p3]);   // waits for all three
```

## Model Answer (15 YOE)

`Promise.all` does not run anything — it observes. You pass it an array of already-started Promises. The parallelism comes from the fact that all the Promises in the array were created (and therefore started) before `Promise.all` was called.

A Promise starts executing the moment it is created. When you write:

```js
await Promise.all([fetchA(), fetchB(), fetchC()]);
```

`fetchA()`, `fetchB()`, and `fetchC()` are all called synchronously in the same expression before `Promise.all` even sees them. They are already in flight. `Promise.all` just aggregates the results into a single Promise that resolves when all three settle.

You could equally write:

```js
const p1 = fetchA();   // starts now
const p2 = fetchB();   // starts now
const p3 = fetchC();   // starts now
const [a, b, c] = await Promise.all([p1, p2, p3]);  // waits for all three
```

The behavior is identical. The "parallelism" is a consequence of JavaScript's event loop — multiple in-flight async operations proceed concurrently because the event loop processes I/O completions as they arrive, not because `Promise.all` has any special scheduling capability.

## Follow-up

**Q:** Can you create Promises "lazily" so they do not start until `Promise.all` is called?

**A:** Yes, by using factory functions (functions that return Promises) instead of Promises directly. `Promise.all` does not have a lazy mode — but you can implement one with a custom scheduler or a library like `p-limit`. The pattern is an array of functions: `const tasks = [() => fetchA(), () => fetchB()]`, then call each one when you are ready to start it.

## Why It's a Trap

Candidates conflate "waiting for Promises in parallel" with "starting Promises in parallel." `Promise.all` only does the waiting. The starting is a consequence of when the Promises were created, which is always before the array is passed in. Saying "Promise.all runs things in parallel" shows a model where `Promise.all` is an active scheduler rather than a passive aggregator.

## What NOT to Say

- "Yes, `Promise.all` runs them in parallel." — Technically imprecise. It observes them; they happen to run concurrently because they were all started before `Promise.all` was called.
- "The Promises start when `Promise.all` receives them." — Wrong. They start at creation time — the moment the function is called.
