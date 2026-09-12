# Reusing a Completed Generator (Senior Trap)
> **Topic:** Generator Functions | **Level:** Senior Trap | **Frequency:** Medium

## The Setup

Candidates who know generators superficially assume that a `break` in a `for...of` loop finishes the generator, or that they can restart it by calling `.next()` after it has completed. Both assumptions are wrong and lead to subtle, hard-to-debug bugs in production.

## The Question

"What happens when you spread a generator into an array twice? What is the state of the generator after a `for...of` loop exits via `break`? How do you get a fresh generator?"

## Diagram

```
  finite() — yields 1, 2, then returns

  const g = finite();
  [...g]  →  [1, 2]   (exhausts generator → state: COMPLETED)
  [...g]  →  []        (completed generator yields nothing)

  ---

  infinite gen = orderIdGenerator('FK')
  for (const id of gen) {
    if (id === 'FK-00000005') break;
  }
  // gen state: SUSPENDED-YIELD (NOT completed)
  gen.next().value  →  'FK-00000006'  ✓
```

## Model Answer (15 YOE)

```js
function* finite() { yield 1; yield 2; }

const g = finite();
console.log([...g]); // [1, 2] — spread exhausts the generator
console.log([...g]); // [] — generator is in completed state, done forever

// Fix: call the function again — this creates a fresh generator object
console.log([...finite()]); // [1, 2]
```

```js
// break does NOT complete the generator
const gen = orderIdGenerator('FK');
for (const id of gen) {
  if (id === 'FK-00000005') break; // exits loop, generator is NOT done
}
// gen is in suspended-yield state — still usable
console.log(gen.next().value); // 'FK-00000006' — works fine
```

A completed generator permanently returns `{ value: undefined, done: true }` for every subsequent `.next()` call. It cannot be reset. The generator *object* is done. The generator *function* can be called again to produce a new, independent generator object.

`break` only exits the consuming loop — it leaves the generator in `suspended-yield` state. The generator is paused at the last `yield` line, waiting for the next `.next()` call. Calling `generator.return()` explicitly transitions it to `completed` and runs `finally` blocks.

## Why It's a Trap

Candidates see `[...g]` work once and assume it always works. Spreading an array twice works fine (arrays are not consumed). Spreading a generator twice silently returns an empty array the second time — no error, no warning. This becomes a production bug when a generator is stored in a module-level variable and reused across requests.

## What NOT to Say

- "The generator resets after you spread it" — false, it is permanently completed.
- "`break` finishes the generator" — false, `break` exits the loop but leaves the generator suspended.
- "Call `.reset()` to reuse it" — there is no `.reset()` method on generators.

## Follow-up

**Q:** "In a React component, the same generator is passed as a prop and two child components both try to iterate it. What happens?"

**A:** The first child consumes some or all of the generator. The second child starts from wherever the first child left off — or gets `{ done: true }` immediately if the first child exhausted it. Generators are not shareable iterators. Each consumer that needs independent iteration needs its own generator object, created by calling the generator function separately.
