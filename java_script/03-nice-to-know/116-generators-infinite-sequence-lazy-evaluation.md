# Infinite Sequence and Lazy Evaluation — Flipkart Order ID Generator
> **Topic:** Generator Functions | **Level:** Fundamental | **Frequency:** High

## The Setup

Flipkart needs unique, monotonically increasing order IDs across the life of a server process. The sequence is theoretically infinite. A naive approach pre-allocates an array — that is a memory cliff. This scenario tests whether the candidate understands lazy evaluation as a first-class production tool.

## The Question

"We need unique, monotonically increasing order IDs across the life of the process. How would you model that? Why is this a generator problem rather than a closure or an array?"

## Diagram

```
EAGER (bad):                     LAZY (generator):
  allIds = generateAll(1e9)        gen = orderIdGenerator()
  ┌────────────────────┐           ┌────────────────────────┐
  │ 1B strings in heap │           │ just seq=1 in memory   │
  │ 8 GB RAM           │           │ < 100 bytes            │
  └────────────────────┘           └────────────────────────┘
  computed NOW, used later         computed WHEN NEEDED
```

## Model Answer (15 YOE)

```js
function* orderIdGenerator(prefix = 'FK', start = 1) {
  let seq = start;
  while (true) {
    yield `${prefix}-${String(seq).padStart(8, '0')}`;
    seq++;
  }
}

const orderIds = orderIdGenerator('FK');

console.log(orderIds.next().value); // FK-00000001
console.log(orderIds.next().value); // FK-00000002
console.log(orderIds.next().value); // FK-00000003
// Runs forever with O(1) memory — no array ever allocated
```

The `while (true)` does not spin. Each call to `.next()` runs the loop body exactly once — increments `seq`, hits `yield`, hands back the value, and freezes. The CPU cost is one iteration per call, not all iterations upfront. The memory cost is one integer (`seq`), not billions of strings.

Why this is better than a closure counter:

```js
// Closure counter — also works, but:
const makeOrderId = (() => {
  let seq = 1;
  return (prefix = 'FK') => `${prefix}-${String(seq++).padStart(8, '0')}`;
})();
// No iteration protocol — cannot use for...of, spread, destructuring
// No built-in done signal
// Generator expresses "this is a sequence" semantically
```

The generator wins because it participates in the iteration protocol: you can `for...of` it (with a break condition), destructure the first N values, or pass it to any function that accepts an iterable.

## Follow-up

**Q:** "What if the process restarts? You lose the counter."

**A:** Persist `seq` to Redis on each yield, or seed the generator from the last known value at startup: `orderIdGenerator('FK', lastPersistedSeq)`. The generator takes `start` as a parameter precisely for this reason.

**Q:** "Is this safe for concurrent requests hitting the same server?"

**A:** Yes. JavaScript is single-threaded. Two requests can never interleave `.next()` calls on the same generator simultaneously. Each call atomically reads `seq`, yields the value, and increments — no race condition is possible.
