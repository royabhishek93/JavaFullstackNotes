# Microtask Queue Ordering — Predict the Output
> **Topic:** Promises | **Level:** Intermediate | **Frequency:** Medium

## The Setup

The interviewer asks you to predict the output of a short snippet, then explain the engine-level reason for the order.

## The Question

What prints, and in what order? Why?

```js
console.log('A');

setTimeout(() => console.log('B'), 0);

Promise.resolve()
  .then(() => console.log('C'))
  .then(() => console.log('D'));

console.log('E');
```

## Diagram

```
  Execution order:
  ┌─────────────────────────────────────────────────────────┐
  │ 1. Call stack runs synchronously                        │
  │    console.log('A')  -> prints A                        │
  │    setTimeout(...)   -> schedules B in macrotask queue  │
  │    Promise.resolve() -> schedules C in microtask queue  │
  │    console.log('E')  -> prints E                        │
  │                                                         │
  │ 2. Call stack empty -> drain microtask queue            │
  │    C callback runs  -> prints C                         │
  │    C's .then schedules D in microtask queue             │
  │    D callback runs  -> prints D                         │
  │                                                         │
  │ 3. Microtask queue empty -> event loop picks macrotask  │
  │    B callback runs  -> prints B                         │
  └─────────────────────────────────────────────────────────┘

  Output: A  E  C  D  B
```

## Model Answer (15 YOE)

Output is `A E C D B`. The rule is: synchronous code first, then microtasks (Promises), then macrotasks (setTimeout/setInterval/I/O).

`A` and `E` are synchronous — they print in source order. `setTimeout` with delay 0 does not mean "run immediately" — it means "put this in the macrotask queue after at least 0 ms." `Promise.resolve().then(...)` puts the callback in the microtask queue. The microtask queue is always fully drained before the event loop picks the next macrotask.

Walk-through:
1. `A` prints synchronously.
2. `setTimeout` registers B in the macrotask queue.
3. `Promise.resolve()` settles immediately; `.then(() => console.log('C'))` is pushed to the microtask queue.
4. `E` prints synchronously.
5. Call stack empties. Event loop checks microtask queue — finds C. C runs, prints `C`. The chained `.then(() => console.log('D'))` is pushed to the microtask queue.
6. D runs, prints `D`. Microtask queue is now empty.
7. Event loop picks the next macrotask: the `setTimeout` callback. B prints.

This ordering is not an implementation detail — it is specified in the ECMAScript spec and the HTML spec (for browsers). The practical implication is that Promise callbacks always run before any `setTimeout`/`setInterval` callbacks, regardless of when the `setTimeout` was registered. This is why Promise-based code feels "immediate" compared to `setTimeout`-based polling.

## Follow-up

**Q:** What would happen if you threw an error inside a `.then()` callback?

**A:** Throwing inside a `.then()` callback automatically turns it into a rejection — the returned Promise rejects with the thrown value. Execution skips all subsequent `.then()` calls and jumps to the next `.catch()` in the chain. This is the same as calling `reject(error)` explicitly. It is one of the nicer parts of the Promise API: you can throw synchronous exceptions inside async chains and they are handled uniformly.
