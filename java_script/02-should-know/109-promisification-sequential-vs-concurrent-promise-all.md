# Sequential vs Concurrent — Promise.all Refactor
> **Topic:** Promisification | **Level:** Intermediate | **Frequency:** High

## The Setup

An order confirmation endpoint in your Express service does three database lookups: fetch the order, fetch the user, fetch the restaurant. They are independent. The current code uses promisified DB wrappers but runs them sequentially. Each query takes ~80 ms. The endpoint's p99 latency is 280 ms.

## The Question

Refactor to run the queries concurrently. What is the difference in latency, and when would you NOT do this?

## Diagram

```
  SEQUENTIAL (current — 240ms total):
  t=0ms    [fetchOrder starts]
  t=80ms                       [fetchOrder done] [fetchUser starts]
  t=160ms                                        [fetchUser done] [fetchRestaurant starts]
  t=240ms                                                         [fetchRestaurant done]

  CONCURRENT with Promise.all (80ms total):
  t=0ms    [fetchOrder starts] [fetchUser starts] [fetchRestaurant starts]
  t=80ms   [all three done — slowest wins]

  3x latency improvement with one refactor.
```

## Model Answer (15 YOE)

```js
// BEFORE: sequential (slow — 240ms)
async function getOrderConfirmation(orderId) {
  const order      = await db.getOrder(orderId);
  const user       = await db.getUser(order.userId);
  const restaurant = await db.getRestaurant(order.restaurantId);
  return buildConfirmation(order, user, restaurant);
}

// AFTER: concurrent (80ms — 3x faster for this query set)
async function getOrderConfirmation(orderId) {
  const order = await db.getOrder(orderId);  // must be first — need userId/restaurantId

  const [user, restaurant] = await Promise.all([
    db.getUser(order.userId),
    db.getRestaurant(order.restaurantId),
  ]);

  return buildConfirmation(order, user, restaurant);
}
```

Note that the first query (`getOrder`) cannot be parallelized — you need its result to get `userId` and `restaurantId`. Only the second and third queries are independent and can run concurrently. This is the common pattern: fetch the root entity first, then fan out for the independent lookups.

**When NOT to parallelize:**

1. **When there is a dependency between queries** — sequential is correct in that case.
2. **When the database connection pool is small** — firing 20 concurrent queries on a pool of 10 connections will queue 10 of them anyway. The overhead of connection contention can exceed the parallelism benefit. Profile before assuming concurrency always wins at scale.
3. **When queries access the same rows in a transaction** — concurrent queries on the same rows can cause lock contention or read-your-own-writes inconsistencies in some isolation levels.
4. **When you need ordered side effects** — if each query must happen in strict order for correctness (not just performance), use sequential `await`.

## Follow-up

**Q:** What does `Promise.all` do if `db.getUser` rejects?

**A:** It short-circuits: the entire `Promise.all` rejects immediately with the first rejection reason, even if `db.getRestaurant` is still in flight. The restaurant query result is discarded. If you need both results regardless of individual failures — for example, to show a partial UI — use `Promise.allSettled`, which always waits for all Promises and gives you a per-Promise outcome array.
