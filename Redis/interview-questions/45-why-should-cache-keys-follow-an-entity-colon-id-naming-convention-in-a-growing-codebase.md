# Why should cache keys follow an entity:id naming convention in a growing codebase?

**Type:** Advanced Scenario-Based
**Topic:** Redis Caching Patterns — Key Design at Scale
**Level:** Senior Interview (8–12+ YOE)

## Direct Answer
Because a consistent `entity:id` (or `entity:id:field`) convention keeps keys self-describing, groups related keys logically for tools and monitoring, and lets you safely reason about invalidation ("delete every key under `user:1000:*`") — all of which break down quickly if keys are named arbitrarily (like plain numbers or unrelated strings) across a growing codebase with many contributors.

## Easy Explanation
Imagine a shared filing cabinet where everyone labels their folders however they feel like that day — "stuff1", "abc", "temp" — versus one where everyone agrees to label folders as `customer:1000`, `customer:1000:orders`, `customer:1000:invoices`. Six months later, with a dozen engineers having added files, the second cabinet is still navigable; the first one is a guessing game where nobody remembers what "stuff1" even means.

## Diagram
```
BAD (arbitrary naming, multiple engineers, no convention):
  10001          -> some user's cached data (which user? unclear)
  abc            -> ??? (nobody remembers 3 months later)
  temp_cache_1   -> ??? (was this ever cleaned up?)

GOOD (entity:id convention, self-describing and groupable):
  user:1000                 -> user 1000's profile hash
  user:1000:followers       -> user 1000's follower set
  order:8842                -> order 8842's cached details
  order:8842:status         -> order 8842's status field

Tools like RedisInsight can visually GROUP keys by their entity prefix:
  user:*    -> folder-like grouping of all user-related keys
  order:*   -> folder-like grouping of all order-related keys
```

## Production Example
```javascript
// Consistent, self-describing key naming
await redisClient.hSet(`user:${userId}`, { name, email });
await redisClient.sAdd(`user:${userId}:followers`, followerId);
await redisClient.set(`order:${orderId}:status`, "shipped", { EX: 3600 });
```

When an on-call engineer needs to investigate "why is user 1000's data acting weird," a consistent convention lets them immediately query `user:1000*` in a monitoring tool and see every related key at a glance — impossible with arbitrary key names.

## Why Interviewers Ask This
It tests operational maturity: does the candidate think about how a cache will be *debugged and maintained* by a team over time, not just how to write the first version of a caching feature.
