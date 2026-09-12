# Async Memoize — Thundering Herd Problem
> **Topic:** Higher-Order Functions | **Level:** Senior Trap | **Frequency:** Medium

## The Setup
A Razorpay pricing engine works with the sync `memoize` you built. Now the pricing function is refactored to hit an external exchange-rate API — it becomes async. A candidate extends memoize by caching the resolved value. The interviewer says: "What happens when ten requests arrive simultaneously before the first one resolves?"

## The Question
Implement a memoize HOF that handles async functions. Specifically, prevent the thundering herd problem.

## Diagram

```
WRONG — caching the resolved value (thundering herd):

  t=0ms: call 1 arrives, cache miss, fires API request, waits...
  t=1ms: call 2 arrives, cache miss (still empty!), fires ANOTHER API request
  t=2ms: call 3 arrives, cache miss, fires ANOTHER API request
  ...
  t=50ms: all 10 calls return, all 10 write to cache
  -- 10 API calls instead of 1

CORRECT — caching the Promise itself:

  t=0ms: call 1 arrives, cache miss, fires API request, caches the Promise
  t=1ms: call 2 arrives, cache HIT (Promise is there), returns same Promise
  t=2ms: call 3 arrives, cache HIT, returns same Promise
  ...
  t=50ms: Promise resolves, all 10 awaits resolve from the same result
  -- 1 API call, 10 consumers
```

## Model Answer (15 YOE)

```js
function memoizeAsync(fn) {
  const cache = new Map();
  return async function(...args) {
    const key = JSON.stringify(args);
    if (cache.has(key)) return cache.get(key);
    // Store the Promise itself — prevents duplicate in-flight calls for same args
    const promise = fn.apply(this, args);
    cache.set(key, promise);
    try {
      return await promise;
    } catch (e) {
      cache.delete(key); // Don't cache rejections — next call retries
      throw e;
    }
  };
}

// Usage — pricing engine
async function fetchExchangeRate(currency) {
  const res = await fetch(`https://api.rates.io/${currency}`);
  return res.json();
}

const memoizedRate = memoizeAsync(fetchExchangeRate);

// 10 simultaneous calls — only 1 HTTP request fires
await Promise.all(Array(10).fill(null).map(() => memoizedRate('USD')));

// With TTL (production pattern):
function memoizeAsyncTtl(fn, ttlMs = 60_000) {
  const cache = new Map();
  return async function(...args) {
    const key = JSON.stringify(args);
    const entry = cache.get(key);
    if (entry && Date.now() - entry.ts < ttlMs) return entry.promise;
    const promise = fn.apply(this, args);
    cache.set(key, { promise, ts: Date.now() });
    try {
      return await promise;
    } catch (e) {
      cache.delete(key);
      throw e;
    }
  };
}
```

The key insight: store the Promise in the cache immediately — before it resolves. This is what prevents the thundering herd. Ten simultaneous calls for the same key all get back the same Promise object and await it together. Only one actually invokes the underlying function.

Rejection handling: delete the cache entry on failure. If you cache a rejected Promise, every future call for that key immediately throws — a thundering failure instead of a thundering herd. Deleting on rejection lets the next call retry.

## Follow-up

**Q:** When should you add a TTL to async memoize?

**A:** When the underlying data changes over time — exchange rates, feature flags, pricing tiers. Without TTL, the first result is cached forever: a stale exchange rate from Monday is served on Friday. TTL lets you tune the freshness vs. performance trade-off per use case: 30 seconds for exchange rates, 5 minutes for pricing tiers, 24 hours for static config. Without TTL, async memoize is appropriate only for truly immutable computations (e.g., fetching a static asset by hash).

## Why It's a Trap

Most engineers implement sync memoize correctly. The async extension looks simple — just `async/await` the result and cache it. The trap is caching the resolved value instead of the Promise, which silently allows duplicate in-flight calls. Interviewers use this to find engineers who understand the event loop and Promise lifecycle, not just syntax.

## What NOT to Say

- "I'd just `await` the function and cache the result" — misses thundering herd entirely
- "The cache will be populated after the first call so subsequent calls will hit it" — only true after the first call *resolves*, not during in-flight time
- "I'd add a mutex/lock" — valid but complex; caching the Promise IS the lock
