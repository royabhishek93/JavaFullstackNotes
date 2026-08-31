# Why does forgetting to set an expiry on a cached response eventually break the feature?

**Type:** Trap Question
**Topic:** Redis Caching Patterns — TTL Discipline
**Level:** Mid–Senior Interview (5–10+ YOE) — common gotcha

## Direct Answer
Without an expiry, a cached value lives **forever** — it never refreshes on its own, so if the underlying data ever changes, users keep seeing the old, stale response indefinitely. Worse, memory usage only grows as more and more keys accumulate with no automatic cleanup, eventually pressuring Redis's memory limits.

## Easy Explanation
A sticky note with no "throw away after X minutes" instruction just stays on the wall forever, even after the information on it is wrong. Nobody circles back to check if it's still accurate, so it silently becomes permanently outdated — and the wall (Redis's memory) keeps filling up with old notes that were never meant to be permanent.

## Diagram
```
BROKEN — no expiry:
  SET product:42 "<v1 data>"          <- no EX/PX given
  ... months pass, product data changes many times in the real database ...
  GET product:42   -> STILL returns "<v1 data>"   <- permanently stale, forever

CORRECT — with expiry:
  SET product:42 "<v1 data>" EX 300
  ... 5 minutes pass ...
  key automatically disappears -> next request re-fetches fresh data and re-caches it
```

## Production Example
A team cached API responses for a "trending products" widget using plain `SET` calls with no `EX`, assuming they'd "add expiry later." Months later, trending products from an old sale season were still showing on the homepage, because the cache had never once refreshed — nobody had written code to actively invalidate it, and there was no TTL to force a refresh either. The one-line fix:

```javascript
// BEFORE
await redisClient.set(`trending:products`, JSON.stringify(data));

// AFTER
await redisClient.set(`trending:products`, JSON.stringify(data), { EX: 600 }); // refresh every 10 min
```

## Why Interviewers Ask This
It's an easy-to-miss but very real production bug. This question checks whether a candidate has internalized "every cache write needs an explicit expiry policy" as a default habit, not an afterthought.
