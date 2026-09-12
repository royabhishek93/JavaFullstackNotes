# for...of vs for await...of on an Async Generator (Senior Trap)
> **Topic:** Generator Functions | **Level:** Senior Trap | **Frequency:** Medium

## The Setup

Async generators implement both `Symbol.iterator` (sync) and `Symbol.asyncIterator` (async) protocols. Using the wrong loop keyword silently iterates over Promise objects instead of their resolved values. TypeScript does not always catch this. It is a real production bug.

## The Question

"What happens if you use a regular `for...of` loop on an async generator instead of `for await...of`? Why doesn't TypeScript always catch this?"

## Diagram

```
  async function* asyncGen() { yield await Promise.resolve(1); }

  for...of path (WRONG):
    uses Symbol.iterator
    each .next() returns { value: Promise<1>, done: false }
    console.log(val) prints: Promise { <pending> }

  for await...of path (CORRECT):
    uses Symbol.asyncIterator
    awaits each .next() before continuing
    console.log(val) prints: 1
```

## Model Answer (15 YOE)

```js
async function* asyncGen() { yield await Promise.resolve(1); }

// WRONG — for...of does NOT await yielded promises from async generators
for (const val of asyncGen()) {
  console.log(val); // prints Promise { <pending> }, not 1
}

// CORRECT
for await (const val of asyncGen()) {
  console.log(val); // prints 1
}
```

Why this happens: an async generator object implements *both* protocols. `for...of` picks up `Symbol.iterator` — which exists on the generator and synchronously returns the next item from the internal queue. But that item is a `Promise`, not the resolved value. The loop happily iterates over Promise objects.

Why TypeScript misses it: if the async generator's return type is `AsyncGenerator<number>`, TypeScript may still allow `for...of` when `strictFunctionTypes` or iterator checking is not fully configured. The type system sees an iterable and does not always distinguish sync from async iteration.

The rule: **any `async function*` must be consumed with `for await...of`**. There are no exceptions.

## Why It's a Trap

The code runs without errors. `for...of` does not throw. You get Promise objects and may not notice unless you inspect the logged values. The bug is subtle: `if (val > 0)` evaluates to `true` for a Promise object (truthy), so downstream logic may appear to work while operating on wrong data.

## What NOT to Say

- "The two loops are interchangeable for async generators" — they are not.
- "TypeScript always catches this" — it does not in all configurations.
- "You need to `await` inside the `for...of` body" — you need `for await...of`, not manual `await` inside a sync loop.

## Follow-up

**Q:** "Can you use `for await...of` on a sync generator?"

**A:** Yes. `for await...of` falls back to `Symbol.iterator` if `Symbol.asyncIterator` is not present. So `for await...of` works on both sync and async generators. The reverse is not true: `for...of` only uses `Symbol.iterator`.

**Q:** "What about spreading an async generator with `[...asyncGen()]`?"

**A:** This uses the sync iterator protocol and spreads Promise objects into the array, not resolved values. You cannot spread an async generator. Use `Array.from` with `for await...of` inside a helper, or collect results manually.
