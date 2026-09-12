# Does util.promisify Work With Any Callback-Based Function?
> **Topic:** Promisification | **Level:** Senior Trap | **Frequency:** High

## The Setup

A new team member is wrapping several third-party libraries with `util.promisify` before a Node.js migration to `async/await`. They apply it broadly to every function that accepts a callback.

## The Question

"Does `util.promisify` work with any callback-based function?"

## Diagram

```
  util.promisify ASSUMPTIONS (all must be true):

  1. Callback is the LAST argument
     legacyFn(arg1, arg2, callback)   ✓ works
     legacyFn(callback, arg1, arg2)   ✗ broken — callback called with wrong args

  2. Callback follows error-first convention
     callback(err, result)            ✓ works
     callback(result, err)            ✗ broken — result treated as error
     callback(result)                 ✗ broken — no error arg, always resolves with undefined

  3. Callback receives at most ONE result value
     callback(err, result)            ✓ works
     callback(err, a, b, c)           ✗ partial — only 'a' is captured, b and c lost

  4. Function is called once
     EventEmitter emitting repeatedly ✗ wrong tool — use events.once()
     Stream emitting chunks           ✗ wrong tool — use stream.pipeline or async iteration
```

## Model Answer (15 YOE)

No. `util.promisify` only works when the function satisfies all four conditions:

1. The callback is the last argument.
2. The callback follows the Node.js error-first convention: first arg is the error (or `null`), second arg is the result.
3. The callback is called with at most one result value (if there are multiple, only the first is captured).
4. The callback is called exactly once (not for EventEmitters or streams that emit over time).

Any deviation from these produces wrong behavior — and the critical detail is that **it fails silently**. `util.promisify` does not inspect the function signature. It generates the wrapper mechanically. If the convention is wrong, you get a Promise that resolves with the wrong value or rejects for successful operations.

```js
// Standard — works correctly
const readFile = promisify(fs.readFile);

// Non-standard callback order — SILENT BUG: successful calls appear as rejections
const chargeAsync = promisify(gateway.charge);  // gateway uses (result, err) ordering

// Multi-result callback — SILENT DATA LOSS: only first result captured
const getBoundsAsync = promisify(geolib.getBounds);  // (err, minLat, minLng, maxLat, maxLng)
// getBoundsAsync resolves with minLat only

// EventEmitter — WRONG TOOL: Promise never settles or settles only once
const onData = promisify(emitter.on);  // wrong — use events.once()
```

The safe practice: always read the callback signature before applying `util.promisify`. When in doubt, write a manual wrapper — it is 5-7 lines and makes the contract explicit.

## Follow-up

**Q:** How does `util.promisify.custom` help when `util.promisify` cannot handle a function correctly?

**A:** You attach a custom implementation to the function via `fn[util.promisify.custom] = function(...) { return new Promise(...) }`. When `util.promisify` sees this symbol, it uses your implementation instead of generating the default one. This lets you ship the correct behavior while still letting callers use the `promisify` API uniformly.

## Why It's a Trap

The Node.js documentation leads with `fs.readFile` as the canonical example, and all Node.js built-ins follow the error-first convention. Engineers internalize "`util.promisify` = promisify any callback function" without reading the fine print. Third-party libraries from before 2015 are particularly risky — many predate the convention's broad adoption.

## What NOT to Say

- "`util.promisify` handles all callback patterns." — It only handles error-first, callback-last, single-result.
- "If it doesn't throw, it works correctly." — Silent wrong behavior is the exact failure mode. No throw, wrong result.
- "You can use `util.promisify` on streams." — Wrong tool entirely. Use `stream.pipeline` (which can itself be promisified) or async iteration.
