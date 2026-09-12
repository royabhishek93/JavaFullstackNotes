# Does Currying Improve Performance?
> **Topic:** Currying | **Level:** Senior Trap | **Frequency:** Low

## The Setup
You have demonstrated currying in several scenarios. The interviewer asks a performance question that sounds like it should have an obvious "yes" answer. Candidates who have memorised that currying is elegant and efficient without thinking through the mechanics fall here.

## The Question
Does currying improve performance? A junior engineer on your team argues that by pre-computing partial results, currying should be faster than calling the full function each time. How do you respond?

## Diagram
```
  DIRECT CALL — no intermediate allocations:
  ┌──────────────────────────────────────────────┐
  │  function add(a, b, c) { return a + b + c; } │
  │  add(1, 2, 3)  → single function call        │
  │  Stack frames: 1                              │
  │  Closures allocated: 0                        │
  └──────────────────────────────────────────────┘

  CURRIED CALL — two extra closure allocations:
  ┌──────────────────────────────────────────────┐
  │  const add = a => b => c => a + b + c;       │
  │  add(1)(2)(3)                                 │
  │    add(1)   → allocates closure { a=1 }      │
  │    (b => ...)(2) → allocates closure { a,b } │
  │    (c => ...)(3) → computes result            │
  │  Stack frames: 3                              │
  │  Closures allocated: 2                        │
  └──────────────────────────────────────────────┘

  WHERE CURRYING INDIRECTLY HELPS (via reuse):
  ┌──────────────────────────────────────────────┐
  │  const add10 = add(10);  // ONE allocation   │
  │  add10(1);  add10(2);  add10(3); // × 10000  │
  │  ← saving is from REUSE, not from currying   │
  └──────────────────────────────────────────────┘
```

## Model Answer (15 YOE)
Currying generally has a small negative impact on performance compared to a direct function call. Each intermediate call allocates a new closure object. Calling `add(1)(2)(3)` allocates two intermediate closure environments that a direct `add(1, 2, 3)` does not. Modern JavaScript engines optimize closures heavily, so this is negligible in practice — but it is not a performance win.

Where currying indirectly helps performance is through partial application enabling function reuse. If `add10 = add(10)` is created once and called ten thousand times, you save the work of repeatedly evaluating the partial — but only because you are reusing a single partially-applied function, not because currying itself is faster.

The wrong answer: "currying speeds up computation by pre-calculating partial results." That is only true if the partial function performs expensive computation that does not depend on the final argument. For pure data transformation like `a + b + c`, there is nothing to pre-calculate.

Real performance optimization in functional pipelines comes from memoization, lazy evaluation, and avoiding unnecessary allocations — not from the currying transformation itself.

```js
// Benchmark intuition (not exact numbers):
const direct = (a, b, c) => a + b + c;
const curried = a => b => c => a + b + c;

// direct(1, 2, 3)       — fastest, no intermediate closures
// curried(1)(2)(3)       — marginally slower, 2 closure allocs
// curried(1)(2)          — then reuse 10000 times → wins by reuse, not currying
```

The practical guidance I give teams: choose currying for code clarity and composability. If you hit a real performance bottleneck in a functional pipeline, profile first — the bottleneck is almost always I/O, rendering, or a hot loop doing unnecessary work, not the currying overhead.

## Follow-up
**Q:** Are there any JavaScript engines that inline or eliminate intermediate closure allocations in curried chains?

**A:** V8 performs escape analysis and inlining for some closure patterns, particularly in hot code paths. But this optimization is not guaranteed and is not something you can depend on. For performance-critical code paths (e.g., a parser loop processing millions of tokens), I replace curried calls with direct multi-argument calls and measure. For application-level code, the overhead is immeasurable in practice.

## Why It's a Trap
The intuitive answer is "yes, because you pre-compute partial results" — but that is wrong. This traps candidates who have memorised that currying is "efficient" without thinking through the mechanics.

## What NOT to Say
"Currying speeds up computation by pre-calculating partial results." Unless the partial function does expensive computation independent of the final argument (rare), there is nothing to pre-calculate — most curried functions just capture values and combine them at the last step.
