# Awaiting a Non-Promise Value
> **Topic:** Promises | **Level:** Senior Trap | **Frequency:** Low

## The Setup

A code reviewer flags this function as "potentially broken" because it `await`s the return value of a function that sometimes returns a raw string and sometimes returns a Promise.

## The Question

What happens when you `await` a non-Promise value like a number or a string? Does it throw? Does it block? Is the following code safe?

```js
async function getData(useCache) {
  const result = await (useCache ? getCachedValue() : fetchFromAPI());
  // getCachedValue() returns a string
  // fetchFromAPI()   returns a Promise<string>
  return result;
}
```

## Diagram

```
  await 42           -> resolves immediately with 42     (no suspension)
  await "hello"      -> resolves immediately with "hello"
  await null         -> resolves immediately with null
  await undefined    -> resolves immediately with undefined
  await Promise.resolve("hi") -> resolves with "hi"      (normal async)

  Internally, await calls Promise.resolve() on the operand:
    Promise.resolve(42)        -> fulfilled Promise with value 42
    Promise.resolve("hello")   -> fulfilled Promise with value "hello"
    Promise.resolve(somePromise) -> same Promise (no wrapping)

  The result is always a fulfilled Promise, so await always resolves, never throws.
```

## Model Answer (15 YOE)

`await` on a non-thenable is completely valid and safe. Internally, the engine calls `Promise.resolve()` on the operand. `Promise.resolve(42)` returns a Promise already fulfilled with `42`. `await` on an already-fulfilled Promise resolves immediately — it still technically yields to the microtask queue for one tick, but it does not perform any async work.

The practical consequence: you can `await` a function that sometimes returns a Promise and sometimes returns a plain value, and the calling code does not need to branch.

```js
// All of these are valid:
const a = await 42;                       // a === 42
const b = await "hello";                  // b === "hello"
const c = await null;                     // c === null
const d = await Promise.resolve("world"); // d === "world"
const e = await fetch('/api/data');       // e === Response object (async)
```

The code in the setup is perfectly safe. `await getCachedValue()` where `getCachedValue()` returns a string will work correctly — `result` will be the string. `await fetchFromAPI()` where `fetchFromAPI()` returns a Promise will also work correctly.

One subtlety: `await nonPromise` still yields once to the microtask queue, so it is not literally synchronous. If you `await 42` inside a loop one million times, you incur one million microtask round-trips. For tight performance-critical loops, avoid unnecessary `await` on synchronous values.

## Follow-up

**Q:** What does `await Promise.resolve(Promise.resolve(42))` evaluate to?

**A:** `42`. `Promise.resolve` on a thenable (including a Promise) returns the same thenable rather than wrapping it. So `Promise.resolve(Promise.resolve(42))` is the inner Promise itself. `await` on it resolves to `42`. There is no "Promise of a Promise" — `Promise.resolve` always flattens one level.

## Why It's a Trap

Candidates who have only seen `await` used with explicit async operations assume it requires a Promise. They write defensive code that checks `if (result instanceof Promise) await result; else use result;` which is entirely unnecessary and suggests a gap in understanding `Promise.resolve`'s semantics.

## What NOT to Say

- "`await` on a non-Promise will throw a TypeError." — It will not. It resolves immediately with the value.
- "You must check if the value is a Promise before awaiting it." — Unnecessary. `await` handles both cases identically.
- "`await 42` blocks the thread for one tick." — It yields for one microtask queue drain, but "blocking the thread" implies synchronous CPU holding, which is wrong.
