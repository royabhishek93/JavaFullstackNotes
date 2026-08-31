# Option D: SQS FIFO Pattern (No Kafka)

> Use on AWS when managed queueing is preferred.

## Scenario

Submachines produce concurrent writes. Need order guarantees and duplicate suppression with minimal operational overhead.

## Architecture

1. API Gateway / Service receives writes.
2. Publish to SQS FIFO queue.
3. `messageGroupId = machineId` for per-machine ordering.
4. `messageDeduplicationId = requestId` for dedupe window.
5. Worker fleet consumes, writes to DB, then deletes message.

## Request Envelope

```json
{
  "machineId": "M1",
  "requestId": "M1-20260401-00045",
  "seqNo": 45,
  "operations": [{"opId": "op1"}, {"opId": "op2"}]
}
```

## Ordering and Delivery

- FIFO queue preserves order within a `messageGroupId`.
- Different machine groups can process in parallel.
- Use idempotency table beyond SQS dedupe window.

## Failure Handling

- Visibility timeout sized above p99 processing time.
- Retry policy with max receive count.
- Dead-letter queue for poison messages.
- Replay safe due to idempotency.

## Trade-offs

- Managed service, low ops burden.
- Throughput limits per queue/group must be planned.
- Dedupe window is time-bounded, so persistent idempotency still required.

## Interview Follow-Ups

1. Is SQS dedupe enough for exactly-once?
Answer direction: no, add persistent idempotency in DB.

2. How do reads stay consistent with writes?
Answer direction: read-after-write token/version or read from primary path.

3. How do you scale?
Answer direction: more groups, multiple queues by tenant/region, horizontal consumers.
