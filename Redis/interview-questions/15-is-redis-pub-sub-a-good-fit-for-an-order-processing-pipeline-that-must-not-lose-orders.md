# Is Redis Pub/Sub a good fit for an order-processing pipeline that must not lose orders?

**Type:** Advanced Scenario-Based
**Topic:** Redis Pub/Sub — Fit-for-Purpose Decisions
**Level:** Staff Interview (10–15+ YOE)

## Direct Answer
**No.** Order processing requires guaranteed delivery — every order must eventually be handled, even if a worker was briefly offline when it was created. Pub/Sub cannot replay a missed message to a reconnecting worker, which makes it fundamentally unsuitable here. Use Redis Streams with a consumer group (or a dedicated message queue) instead, so work is retained and can be recovered.

## Easy Explanation
An order isn't like a typing indicator — you can't just "wait for the next one" if it's missed, because there might not be a "next one" for that exact order. Every single order matters and must be accounted for. That requirement — "nothing may ever silently disappear" — is precisely what Pub/Sub does not promise, and precisely what Streams (with their retained log and per-worker acknowledgment tracking) are built for.

## Diagram
```
WRONG tool for this job:
Order Service --PUBLISH--> orders:new --> [ worker temporarily offline ] --> order LOST FOREVER

RIGHT tool for this job:
Order Service --XADD--> orders-stream --> [ consumer group: order-workers ]
                                                 |
                                    worker offline? no problem —
                                    entry stays in the stream,
                                    delivered/redelivered once a worker is available
                                                 |
                                                 v
                                    XACK only after the order is fully processed
```

## Production Example
```bash
# WRONG — a worker restart during a deploy can silently drop orders
PUBLISH orders:new '{"orderId": 900}'

# RIGHT — retained, resumable, acknowledgment-tracked
XADD orders-stream * orderId 900
XGROUP CREATE orders-stream order-workers $ MKSTREAM
XREADGROUP GROUP order-workers worker-1 STREAMS orders-stream >
```

A real e-commerce platform migrated its "process new order" event from Pub/Sub to Streams after discovering that orders placed during routine deployments were occasionally never processed — a defect that Pub/Sub's design made structurally impossible to fully fix without switching data structures.

## Why Interviewers Ask This
It's the direct counterpart to the typing-indicator question, and together they test whether a candidate applies a consistent decision framework — "can this feature tolerate occasional loss?" — rather than picking Pub/Sub or Streams based on habit or familiarity alone.
