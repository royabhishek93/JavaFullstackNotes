# What Is Promisification — Implement promisify from Scratch
> **Topic:** Promisification | **Level:** Fundamental | **Frequency:** High

## The Setup

An interviewer asks you to explain the concept of promisification and then implement `promisify` from scratch — without using `util.promisify`.

## The Question

What is promisification? Write a `promisify` function that takes any Node.js error-first callback-based function and returns a Promise-returning version of it.

## Diagram

```
  BEFORE: Callback-based function
  ┌─────────────────────────────────────────────────┐
  │  legacyFn(arg1, arg2, callback)                 │
  │                      |                          │
  │                 callback(err, result)            │
  │                 ├── err != null  -> error path   │
  │                 └── err == null  -> success path │
  └─────────────────────────────────────────────────┘

  promisify() TRANSFORMATION
  ┌─────────────────────────────────────────────────┐
  │  function promisify(fn) {                       │
  │    return (...args) =>                          │
  │      new Promise((resolve, reject) => {         │
  │        fn(...args, (err, result) => {           │  <- inject callback
  │          if (err) reject(err);                  │  <- route to Promise
  │          else     resolve(result);              │
  │        });                                      │
  │      });                                        │
  │  }                                              │
  └─────────────────────────────────────────────────┘

  AFTER: Promise-based wrapper
  ┌─────────────────────────────────────────────────┐
  │  const fn = promisify(legacyFn)                 │
  │  const result = await fn(arg1, arg2)            │
  │  // throws on error, returns value on success   │
  └─────────────────────────────────────────────────┘
```

## Model Answer (15 YOE)

Promisification is a single-responsibility adapter pattern: take a function that communicates results through callbacks, return a new function that communicates results through a Promise. The original function is never modified. It is the bridge between the callback-based ecosystem (every Node.js core API pre-Promises) and modern `async/await`.

The entire technique depends on one convention: the **error-first callback** — `callback(err, result)`. The callback is always the last argument; `err` is null on success.

```js
function promisify(fn) {
  return function(...args) {
    return new Promise((resolve, reject) => {
      // Inject the callback as the last argument
      fn.apply(this, [...args, (err, result) => {
        if (err) reject(err);
        else     resolve(result);
      }]);
    });
  };
}
```

Usage:

```js
const fs = require('fs');
const readFile = promisify(fs.readFile);

async function main() {
  const content = await readFile('config.json', 'utf8');
  console.log(JSON.parse(content));
}
```

Key design decisions in the implementation:
- `fn.apply(this, [...args, callback])` preserves `this` context and appends the callback to whatever arguments the caller passed — the callback is always last.
- The callback checks `err` first. Non-null `err` rejects the Promise. Null `err` resolves with `result`.
- The returned wrapper function uses rest syntax (`...args`) so it works for any arity.

Node.js ships `util.promisify` which does exactly this, plus it checks for a `util.promisify.custom` symbol on the function, allowing library authors to override the default behavior.

## Follow-up

**Q:** Why use `fn.apply(this, [...args, callback])` instead of `fn(...args, callback)`?

**A:** `fn.apply(this, ...)` passes the current `this` context into the original function. If the function is a method on an object that uses `this` internally (e.g., `client.query` using `this.connection`), losing `this` causes a runtime error. The spread-and-append pattern `[...args, callback]` achieves the same argument layout as `fn(...args, callback)` but preserves the context. That said, the safest approach is to `.bind` the method to its object before passing it to `promisify`.
