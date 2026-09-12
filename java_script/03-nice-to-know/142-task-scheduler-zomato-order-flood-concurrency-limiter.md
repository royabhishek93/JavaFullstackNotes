# Concurrency Limiter for Zomato Order Flood
> **Topic:** Task Scheduler | **Level:** Intermediate | **Frequency:** High

## The Setup

Zomato receives 5,000 orders per minute during dinner rush. Each order triggers a DB write, a payment charge, and a push notification. Processing all of them with `Promise.all` saturates the DB connection pool, triggers payment API rate limits, and cascades into timeouts and OOM crashes. This scenario tests whether the candidate can identify the bottleneck and apply the correct concurrency limit.

## The Question

"Zomato receives 5,000 orders per minute during dinner rush. Each order triggers a DB write, a payment charge, and a push notification. What breaks if you use `Promise.all` to process all of them? How do you fix it?"

## Diagram

```
WITHOUT SCHEDULER (Promise.all):
=================================

  5000 orders arrive
       │
       v
  Promise.all(orders.map(processOrder))
       │
       v  5000 simultaneous:
       │  - DB connections → pool exhausted (pool: 20-100 connections)
       │  - Payment API calls → 429 rate-limit errors
       │  - DB query queue fills → latency spikes → timeouts cascade
       v
  First symptom: slow queries
  Final symptom: process OOM crash

WITH SCHEDULER (concurrency=10):
==================================

  5000 orders arrive
       │
       v
  scheduler.addTask(() => processOrder(order))  ×5000
       │
       v  At any moment: exactly 10 processOrder calls in-flight
       │  4990 tasks wait in queue
       │  DB pool: max 10 connections at once ← safe
       │  Payment API: max 10 req/s ← within rate limit
       v
  All 5000 complete — no timeouts, no crashes
```

## Model Answer (15 YOE)

```js
// DANGEROUS — launches all 5000 tasks simultaneously
async function processAllOrders_WRONG(orders) {
  await Promise.all(orders.map(order => processOrder(order)));
}

// CORRECT — at most 10 processOrder calls in-flight at any time
async function processAllOrders(orders) {
  const scheduler = new TaskScheduler(10);

  const results = await Promise.all(
    orders.map(order =>
      scheduler.addTask(() => processOrder(order))
    )
  );

  return results;
}
```

`Promise.all` still waits for every task to complete and still collects all results. But at any moment, only 10 `processOrder` calls are actually running. The other 4,990 wait in the queue. The DB connection pool never sees more than 10 simultaneous requests. The payment API never sees a flood.

Failure modes prevented:
- **DB pool exhaustion**: typical PG pool is 20 connections; 5000 simultaneous requests queue up and time out waiting for a connection
- **Payment API rate limiting**: most payment gateways enforce req/s limits; `Promise.all` blasts past them in milliseconds
- **Memory**: 5000 in-flight promises hold onto their closures and response buffers simultaneously; a scheduler keeps at most N active

**Choosing the right N:**

Match `concurrency` to the bottleneck's capacity. If the DB pool has 20 connections and each task uses one, set `concurrency = 15` (leave 5 for health checks, migrations, and other queries). If the payment API allows 20 req/s, set `concurrency` so that throughput stays under that ceiling.

## Follow-up

**Q:** "Would you create one scheduler per request or share a single scheduler across all requests?"

**A:** Share a single scheduler. The goal is to limit total concurrency against a shared resource (the DB pool, the payment API). A per-request scheduler only limits concurrency within one request — ten simultaneous requests each with `concurrency=10` gives you 100 total concurrent calls. One shared scheduler with `concurrency=10` gives you 10 total.

**Q:** "What about error handling — if one order's payment fails, do the others continue?"

**A:** Yes. Each task's Promise rejects independently. The scheduler does not stop on failure — it frees the slot and starts the next task regardless. The `Promise.all` call rejects when the first task fails (fast-fail), but all already-started tasks continue running. Use `Promise.allSettled` instead of `Promise.all` if you want to wait for all tasks and collect individual outcomes.
