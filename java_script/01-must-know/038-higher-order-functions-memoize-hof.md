# Memoize HOF — Implement and Explain
> **Topic:** Higher-Order Functions | **Level:** Intermediate | **Frequency:** High

## The Setup
A Razorpay pricing engine calls `calculateEmi(principal, rate, tenure)` thousands of times per second during peak traffic. The function is pure and expensive. A junior engineer wants to add Redis caching. You suggest solving it first in-process with a memoize HOF.

## The Question
Implement a generic `memoize` HOF, explain its contract, and say when it breaks down.

## Diagram

```
memoize wraps any pure function and caches results by argument key:

  First call:  memoizedCalc(10000, 8.5, 36)
               |
               v
       [cache miss] --> run original fn --> result: 313.36 --> store in cache
               |
               v
       return 313.36

  Subsequent calls: memoizedCalc(10000, 8.5, 36)
               |
               v
       [cache hit: key "10000|8.5|36"] --> return 313.36 (no computation)

  Cache structure (Map for O(1) lookup):
  Map {
    "10000|8.5|36" => 313.36,
    "5000|9.0|24"  => 232.14,
    ...
  }
```

## Model Answer (15 YOE)

```js
// Generic memoize HOF
function memoize(fn, keyFn = (...args) => JSON.stringify(args)) {
  const cache = new Map();
  return function(...args) {
    const key = keyFn(...args);
    if (cache.has(key)) return cache.get(key);
    const result = fn.apply(this, args);
    cache.set(key, result);
    return result;
  };
}

// EMI calculation — pure, deterministic, expensive
function calculateEmi(principal, rate, tenure) {
  const r = rate / 12 / 100;
  return +(principal * r * Math.pow(1 + r, tenure) / (Math.pow(1 + r, tenure) - 1)).toFixed(2);
}

const memoizedEmi = memoize(calculateEmi);

memoizedEmi(10000, 8.5, 36); // computed: ~313.36
memoizedEmi(10000, 8.5, 36); // cache hit — 0ms
memoizedEmi(5000, 9.0, 24);  // computed: new args

// Bounded cache — evict oldest when size exceeds limit (LRU-lite)
function memoizeBounded(fn, limit = 1000) {
  const cache = new Map();
  return function(...args) {
    const key = JSON.stringify(args);
    if (cache.has(key)) return cache.get(key);
    const result = fn(...args);
    cache.set(key, result);
    if (cache.size > limit) cache.delete(cache.keys().next().value); // evict oldest
    return result;
  };
}
```

The HOF contract: `memoize` must only wrap pure functions. If the wrapped function has side effects (logs, writes to DB, reads from external state), the cached result will be returned on repeat calls and the side effect will silently not fire. The `keyFn` parameter matters for non-primitive arguments — `JSON.stringify` works for plain objects but fails on functions, circular references, or class instances. For those, pass a custom key function (e.g., using `object.id`). Cache size is unbounded by default — the `memoizeBounded` variant caps memory in long-running processes.

## Follow-up

**Q:** What is the difference between memoization and caching, architecturally?

**A:** Memoization is a specific form of caching scoped to a single pure function — keyed on its arguments, stored in-process, with the same lifetime as the function reference. Architectural caching (Redis, Memcached) is distributed, has explicit TTLs, is shared across processes and machines, and is designed for data that changes. Memoize first for in-process hot paths; add Redis when you need cross-instance sharing, TTL-based invalidation, or cache persistence across deploys.
