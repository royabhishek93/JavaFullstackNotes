# Can You await a Promisified Function Inside a .then() Chain?
> **Topic:** Promisification | **Level:** Senior Trap | **Frequency:** Medium

## The Setup

A developer is mixing `.then()` chains with promisified functions and tries to use `await` inside a `.then()` callback to keep the code readable.

## The Question

What is wrong with this code, and what are the two correct alternatives?

```js
readFile('config.json', 'utf8')
  .then(raw => {
    const data = await parseConfig(raw);  // parseConfig returns a Promise
    return data;
  });
```

## Diagram

```
  BROKEN — await outside async function:
  .then(raw => {
    const data = await parseConfig(raw);  // SyntaxError: await is not in async fn
  });

  The .then callback is a regular function.
  await is only valid inside an async function.
  This is a SyntaxError caught at parse time.

  FIX 1 — make the .then callback async:
  .then(async raw => {
    const data = await parseConfig(raw);
    return data;
  });

  FIX 2 — chain another .then (idiomatic):
  .then(raw => parseConfig(raw))
  .then(data => ...)
```

## Model Answer (15 YOE)

`await` is only valid inside an `async` function. A `.then()` callback is a regular function unless you explicitly declare it `async`. Using `await` inside a non-async `.then()` callback is a **SyntaxError** caught at parse time — the file will not even load.

```js
// BROKEN — SyntaxError
readFile('config.json', 'utf8')
  .then(raw => {
    const data = await parseConfig(raw);  // SyntaxError
    return data;
  });

// FIX 1: Make the callback async
readFile('config.json', 'utf8')
  .then(async raw => {
    const data = await parseConfig(raw);  // valid — callback is async
    return data;
  })
  .catch(err => console.error(err));

// FIX 2: Chain .then calls (idiomatic .then style)
readFile('config.json', 'utf8')
  .then(raw => parseConfig(raw))   // return the Promise directly
  .then(data => ...)
  .catch(err => console.error(err));

// FIX 3: Convert the whole chain to async/await
async function init() {
  const raw  = await readFile('config.json', 'utf8');
  const data = await parseConfig(raw);
  return data;
}
```

Fix 1 (async callback) is valid but introduces a subtle risk: an `async` `.then()` callback that throws will reject the Promise returned by that `.then()`, which propagates down the chain — but only if the next `.catch()` is attached to the same chain. If someone detaches the chain, the async callback's rejection becomes unhandled.

Fix 2 is the idiomatic pure-`.then()` style and has no ambiguity. Fix 3 is the cleanest for multi-step flows.

## Follow-up

**Q:** If you use an `async` function as a `.then()` callback, does the chain wait for the `async` function to finish?

**A:** Yes, because an `async` function returns a Promise, and `.then()` automatically unwraps a Promise returned from its callback. So `.then(async raw => { ... })` works correctly — the chain waits for the inner `async` function to resolve before proceeding to the next `.then()`.

## Why It's a Trap

Developers who mix `async/await` and `.then()` chains instinctively try to add `await` inside a `.then()` callback for readability, not realizing the callback is a regular function. The SyntaxError reveals the misunderstanding: `async/await` is not a general "async keyword" — it requires the `async` function declaration to activate the `await` syntax.

## What NOT to Say

- "You can use `await` anywhere inside an async flow." — Only inside `async` functions, not inside any callback that is not itself `async`.
- "The `.then()` callback is implicitly async." — It is not. You must declare it `async` explicitly.
- "`await` in a `.then()` is a runtime error." — It is a SyntaxError (parse-time), not a runtime error.
