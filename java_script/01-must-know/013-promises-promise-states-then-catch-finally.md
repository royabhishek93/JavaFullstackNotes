# Promise States, then, catch, and finally
> **Topic:** Promises | **Level:** Fundamental | **Frequency:** High

## The Setup

You are onboarding a new team member who has only used callbacks. You need to explain how Promises work as a mental model before they read any async code in the codebase.

## The Question

Walk me through what a Promise is, what states it can be in, and how `.then`, `.catch`, and `.finally` fit together.

## Diagram

```
  Promise State Machine
  ┌─────────────────────────────────────────────┐
  │                                             │
  │   new Promise(executor)                     │
  │         |                                   │
  │      PENDING  ──── resolve(value) ──> FULFILLED ──> .then fires
  │         |                                   │
  │         └───── reject(reason) ───> REJECTED  ──> .catch fires
  │                                             │
  │   State is FINAL — never transitions again  │
  │   .finally fires on BOTH outcomes           │
  └─────────────────────────────────────────────┘

  Your JS Code
       |
       v
  [ Call Stack ]  <---- runs to empty
       |
       |  Promise settles (network/timer/etc)
       v
  [ Microtask Queue ]         <- .then / .catch / await continuations
       |  drained fully before next macrotask
       v
  [ Macrotask Queue ]         <- setTimeout, setInterval, I/O callbacks
       |
       v
  [ Event Loop ] picks next macrotask -> re-fills call stack
```

## Model Answer (15 YOE)

A Promise is a state machine with exactly three states: `pending`, `fulfilled`, and `rejected`. Once it transitions out of `pending` it never changes again — state is final.

When you call `new Promise((resolve, reject) => { ... })`, the executor function runs immediately and synchronously. You call `resolve(value)` to move the Promise to `fulfilled`, or `reject(reason)` to move it to `rejected`. If the executor throws, the Promise rejects automatically.

`.then(onFulfilled)` registers a callback that runs when the Promise fulfills. It returns a new Promise, which means chains are possible. `.catch(onRejected)` is syntactic sugar for `.then(undefined, onRejected)`. `.finally(fn)` runs `fn` on both fulfillment and rejection — it does not receive any value, it is for cleanup (hiding spinners, closing connections).

The callbacks registered with `.then` and `.catch` are not called immediately when the Promise settles — they are pushed onto the **microtask queue**. The microtask queue is drained completely before the event loop picks the next macrotask (setTimeout, I/O). This is why Promise resolution feels "immediate" but is technically async.

`async/await` is compiled sugar over this same mechanism. Every `await` is a `.then` under the hood, and a rejected `await` is an unhandled `.catch` if not wrapped in `try/catch`.

```js
// Full chain
fetch('/api/data')
  .then(res  => res.json())          // transform the response
  .then(data => renderDashboard(data)) // use the result
  .catch(err => showErrorBanner(err))  // handle any rejection in the chain
  .finally(() => hideLoadingSpinner()); // always runs

// Equivalent with async/await
async function loadData() {
  try {
    const res  = await fetch('/api/data');
    const data = await res.json();
    renderDashboard(data);
  } catch (err) {
    showErrorBanner(err);
  } finally {
    hideLoadingSpinner();
  }
}
```

## Follow-up

**Q:** Can a `.then` callback turn a fulfilled Promise into a rejected one?

**A:** Yes, in two ways. If the `.then` callback throws an error, the returned Promise rejects with that error. If the `.then` callback returns a rejected Promise (or a Promise that later rejects), the returned Promise also rejects. This is how errors propagate through a chain — any `.then` in the middle can reject, and execution skips to the next `.catch`.
