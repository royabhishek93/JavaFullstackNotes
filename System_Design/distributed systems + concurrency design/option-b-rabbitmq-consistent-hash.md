# Option B: RabbitMQ + Consistent Hash Routing

> Use when you need queueing, routing flexibility, and no Kafka.

## Scenario

N submachines perform concurrent writes. You need strict per-machine ordering and reliable retries.

## Architecture

1. Write Gateway publishes to RabbitMQ exchange.
2. Consistent-hash routing by `machineId` to fixed queue lanes.
3. One active consumer per queue for ordered processing.
4. Idempotency store + business DB.
5. Dead-letter exchange for poison messages.

## Message Contract

```json
{
  "machineId": "M3",
  "requestId": "M3-00077",
  "seqNo": 77,
  "operations": [
    {"opId": "1", "type": "UPSERT", "entityId": "A"}
  ]
}
```

## Ordering Strategy

- Routing key = `machineId`.
- Same `machineId` always lands on same queue lane.
- Queue FIFO + single consumer preserves order.

## Reliability Strategy

- Manual ack only after DB commit.
- On failure: NACK + requeue with bounded retries.
- Exceeded retries -> dead-letter queue.
- Duplicate delivery handled by idempotency table.

## Trade-offs

- Good operational maturity and tooling.
- Ordering preserved per queue, not global by default.
- Rebalancing queue lanes requires planned migration.

## Interview Follow-Ups

1. Why not multiple consumers on one queue?
Answer direction: breaks strict order under parallel consumption.

2. How do you avoid duplicate execution?
Answer direction: unique `(machineId, requestId)` and deterministic operation logic.

3. How to increase throughput?
Answer direction: increase lane count and distribute machine IDs across lanes.
