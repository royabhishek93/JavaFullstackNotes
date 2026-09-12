# Memoization Cache in a Price Calculation Service
> **Topic:** Closures | **Level:** Intermediate | **Frequency:** Medium

## The Setup
You are a backend engineer at MakeMyTrip working on a flight price engine. A `calculateFare` function runs complex pricing logic that takes ~200ms. The same fare is requested hundreds of times per second for popular routes. You need to memoize it without a global cache variable and without modifying the function's signature.

## The Question
Implement a production-grade `memoize` higher-order function using closures. What are the memory management considerations?

## Diagram
```
  memoize(calculateFare)
  ┌───────────────────────────────────────┐
  │  const cache = new Map();  // PRIVATE │◀── closure env
  │                                       │    lives here
  │  return function memoized(...args) {  │
  │    const key = JSON.stringify(args);  │
  │    if (cache.has(key)) {              │
  │      return cache.get(key); // HIT   │
  │    }                                  │
  │    const result = fn(...args);        │
  │    cache.set(key, result); // MISS   │
  │    return result;                     │
  │  }                                    │
  └───────────────────────────────────────┘

  MEMORY CONCERN:
  cache Map grows unbounded unless eviction is implemented
  ┌──────────┐   ┌───────────────────────────────────┐
  │ cache    │──▶│ "BLR-DEL-2024-01-15" → ₹4500     │
  │ (Map)    │   │ "BOM-GOA-2024-01-20" → ₹2100     │
  └──────────┘   │ ... N entries, no eviction = LEAK │
                 └───────────────────────────────────┘
```

## Model Answer (15 YOE)
The cache Map lives in the closure environment of the returned `memoized` function. Each call to `memoize` creates a completely fresh cache — there is no shared global state, which is essential for safety. If two services both call `memoize(calculateFare)`, they get independent caches.

The naive implementation I showed is dangerous in production for exactly one reason: unbounded growth. At MakeMyTrip's scale with thousands of route/date combinations, the cache becomes a memory sink. I add three mitigations: First, a max-size LRU eviction policy — I implement this with a doubly-linked list or just use a fixed-capacity Map by evicting the oldest entry on insert. Second, a TTL per entry — flight prices change, so I store `{ result, expiresAt }` and validate on read. Third, I expose a `memoized.clear()` method on the returned function that wipes the cache — this enables explicit invalidation from external events like a fare update webhook.

One production gotcha: `JSON.stringify(args)` is fine for primitive arguments but breaks for object arguments with different key ordering. For the fare engine, I serialize route + date + passenger count as a normalized string key, never a raw object. Another gotcha: if the wrapped function is async, the naive implementation stores Promises in the cache, which is usually correct — concurrent calls for the same key all await the same Promise — but you must handle the case where the Promise rejects and remove the entry from the cache.

```js
function memoize(fn, { maxSize = 500, ttlMs = 60_000 } = {}) {
  const cache = new Map();

  const memoized = function (...args) {
    const key = JSON.stringify(args);
    const hit = cache.get(key);

    if (hit && Date.now() < hit.expiresAt) return hit.result;

    const result = fn.apply(this, args);

    // Evict oldest if at capacity
    if (cache.size >= maxSize) {
      cache.delete(cache.keys().next().value);
    }
    cache.set(key, { result, expiresAt: Date.now() + ttlMs });
    return result;
  };

  memoized.clear = () => cache.clear();
  return memoized;
}

const memoizedFare = memoize(calculateFare, { maxSize: 1000, ttlMs: 30_000 });
```

## Follow-up
**Q:** How do you handle cache invalidation across multiple instances of a memoized function?

**A:** Closure-based memoize is inherently instance-local. For cross-instance invalidation you need an external cache (Redis, Memcached) rather than a closure cache. The closure approach is appropriate for in-process, single-instance caching where the function's inputs uniquely determine its output and the caller controls the lifecycle of the memoized function.
