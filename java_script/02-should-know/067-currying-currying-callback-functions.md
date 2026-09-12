# Can You Curry a Function That Takes a Callback?
> **Topic:** Currying | **Level:** Senior Trap | **Frequency:** Low

## The Setup
You are in a deep-dive discussion about functional programming in JavaScript. The interviewer asks a nuanced question about how currying interacts with higher-order functions — one that forces you to reason about what happens when a curried callback is passed into a platform API that calls it with multiple arguments.

## The Question
Can you curry a function that takes a callback? What goes wrong when a curried callback is passed to a platform API like `Array.prototype.map`?

## Diagram
```
  CURRYING A WRAPPER — works fine when YOU control call sites:
  ┌────────────────────────────────────────────────────┐
  │  const mappedWith = curry((fn, arr) => arr.map(fn))│
  │  mappedWith(x => x * 2)([1, 2, 3]) → [2, 4, 6]   │
  │  fn.length === 2 ✓, curry knows to wait for arr    │
  └────────────────────────────────────────────────────┘

  PASSING A CURRIED CALLBACK TO map — breaks:
  ┌────────────────────────────────────────────────────┐
  │  const double = x => x * 2;   // normal fn        │
  │  [1, 2, 3].map(double);       // [2, 4, 6] ✓     │
  │                                                    │
  │  const curriedDouble = x => y => x * y;           │
  │  [1, 2, 3].map(curriedDouble(2));                  │
  │    → map calls callback(element, index, array)     │
  │    → curriedDouble(2)(1)  → returns fn y => 2*y   │
  │    → [fn, fn, fn]  ← array of functions, not nums │
  └────────────────────────────────────────────────────┘

  THE ACTUAL TRAP — partially applied fn + map:
  ┌────────────────────────────────────────────────────┐
  │  const multiply = curry((a, b) => a * b);          │
  │  [1, 2, 3].map(multiply(2));                       │
  │  map calls: multiply(2)(1, 0, [1,2,3])             │
  │    → 2 * 1 = 2  (works — extra args ignored)      │
  │  BUT:                                              │
  │  const log = curry((base, val) => Math.log(val)    │
  │                                    / Math.log(base))│
  │  [10, 100, 1000].map(log(10));  // → [1, 2, 3] ✓  │
  │  This works only because map's extra args (index,  │
  │  array) are IGNORED by the 2-arg curry.            │
  │  Dangerous with functions that accept extra args.  │
  └────────────────────────────────────────────────────┘
```

## Model Answer (15 YOE)
You can, but the shape of the call becomes awkward and there are specific failure modes to understand.

When you curry a utility that wraps `map`, it works because you control the arity:

```js
const mappedWith = curry((fn, arr) => arr.map(fn));
mappedWith(x => x * 2)([1, 2, 3]); // [2, 4, 6] — fine
```

Problems arise when the callback itself is curried and passed into a higher-order function that calls it with multiple arguments. `Array.prototype.map` calls the callback with `(element, index, array)` — three arguments. A curried callback `x => index => array => x * 2` would receive `element` first and return a function waiting for `index`. `map` receives that function as the mapped result — not what you wanted.

```js
// The danger with parseInt and map — classic JS gotcha:
['1', '2', '3'].map(parseInt);
// map calls: parseInt('1', 0), parseInt('2', 1), parseInt('3', 2)
// parseInt's second arg is the radix — unexpected behavior
// [1, NaN, NaN] — not [1, 2, 3]

// Same class of problem with curried callbacks:
const curriedAdd = a => b => a + b;
[1, 2, 3].map(curriedAdd(10));
// map calls curriedAdd(10)(1, 0, [1,2,3])
// b = 1 (element), 0 and [1,2,3] are ignored → 11 ✓
// Happens to work because the fn ignores extra args
// But relies on accident, not design
```

The production rule: only curry functions whose call sites you control. Do not curry callbacks that will be passed to platform APIs (`map`, `filter`, `addEventListener`) unless you wrap the call site to enforce single-argument invocation.

```js
// Safe wrapper pattern:
const safeMap = (fn) => (arr) => arr.map((x) => fn(x)); // forces single arg
[1, 2, 3].pipe(safeMap(curriedAdd(10))); // explicit single-arg call
```

## Follow-up
**Q:** Is the `parseInt` + `map` bug related to currying?

**A:** It is the same class of bug — a multi-argument API calling a function you expected to receive only one argument. `parseInt` is not curried, but `map` passes `(element, index, array)` and `parseInt(string, radix)` accidentally interprets the index as the radix. The fix is identical: wrap in a single-argument arrow: `['1','2','3'].map(x => parseInt(x))`. The lesson — always know what arguments a higher-order function passes to its callback.

## Why It's a Trap
It forces candidates to reason about how currying interacts with functions whose call signature is determined by the platform, not by you. Saying "yes you can curry anything" without addressing the multi-argument callback problem reveals shallow understanding.

## What NOT to Say
"You can curry any function" without qualification. The moment a curried callback is passed to a platform API that calls it with extra arguments (index, event, array), you lose control of the arity and the behavior becomes unpredictable or silently wrong.
