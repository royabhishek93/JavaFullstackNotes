# How do you redesign order processing so a crashed consumer never causes a double charge?

**Type:** Advanced Scenario-Based
**Topic:** Redis Streams — Reliable Delivery & Idempotency
**Level:** Staff/Principal Interview (15+ YOE)

## Direct Answer
Move the "did we already charge this order" decision out of Redis entirely and into a database with a **unique constraint**. Redis Streams only need to guarantee the *work item* is not lost; the database needs to guarantee the *side effect* only happens once. Combine three layers, each owning one job: the API layer owns request validation and generates an idempotency key; the Stream owns delivery and retry; the payment write owns durability via a unique DB constraint on that idempotency key. `XACK` must be the *last* step in the worker — only sent after the charge is confirmed and persisted.

## Easy Explanation
Imagine a call center where every customer complaint gets a ticket number before anyone picks up the phone. If the same complaint is called in twice by mistake, the agent checks "have we already resolved ticket #4521?" before doing anything. Redis is the phone queue — it makes sure no ticket is lost. The unique ticket number and the "already resolved?" check is what makes calling twice harmless. Without that check, two agents calling the same customer back would waste effort or, worse, issue two refunds.

## Diagram
```
                    +-------------------------------------------------+
                    |               Order Service (API)                |
                    | 1. client sends Idempotency-Key: order-8842      |
                    | 2. INSERT order (status=PENDING) if not exists   |
                    | 3. XADD order-events  requestId=order-8842       |
                    +----------------------+---------------------------+
                                           |
                                           v
                    +-------------------------------------------------+
                    |             Redis Stream: order-events            |
                    |  consumer group: charge-workers                   |
                    +----------------------+---------------------------+
                                           |
                         XREADGROUP >     v
                    +-------------------------------------------------+
                    |  Worker crashes here <-- BEFORE XACK              |
                    |  charge attempt started, response unknown         |
                    +----------------------+---------------------------+
                                           |
                             XAUTOCLAIM (after idle window)
                                           v
                    +-------------------------------------------------+
                    | New worker re-reads same event                    |
                    | SELECT ... WHERE requestId = 'order-8842'         |
                    |   -> already CHARGED?  -> skip charge, just XACK  |
                    |   -> still PENDING?    -> charge once, then XACK  |
                    +-------------------------------------------------+
```

## Production Example
```sql
CREATE UNIQUE INDEX ux_orders_idempotency ON orders(idempotency_key);
```
```java
@Transactional
public void chargeRider(MapRecord<String, Object, Object> message) {
    PaymentEvent event = mapper.toEvent(message);

    int updated = orderRepo.markPaidIfPending(event.orderId(), event.idempotencyKey());
    if (updated == 1) {
        paymentGateway.charge(event.idempotencyKey(), event.amount()); // gateway also dedupes on this key
    }
    // if updated == 0, another worker already handled it — safe to skip

    redisTemplate.opsForStream().acknowledge("payment-workers", message);
}
```
The `markPaidIfPending` update uses a `WHERE status = 'PENDING'` clause, so a redelivered message becomes a no-op the second time — the unique constraint and conditional update are what actually prevent the double charge, not Redis itself. Most payment gateways (Stripe, Razorpay, etc.) also accept an `Idempotency-Key` header for exactly this reason — they expect retries from distributed systems and dedupe on their side too.

## Why Interviewers Ask This
This question checks whether a candidate can design an end-to-end safety net across three systems (API, Redis, database/gateway) instead of trying to solve everything inside Redis. Naming the unique constraint, the idempotency key propagation, and the strict ordering of "do work, then acknowledge" — not just "use Redis Streams" — is a strong signal of production experience with financial or billing systems.
