# Option C: Redis Streams + Consumer Groups

> Use when you need lightweight stream processing with low latency.

## Scenario

Multiple submachines send writes to main machine concurrently. Preserve per-machine ordering and support retry recovery.

## Architecture

1. API gateway appends records to Redis Stream.
2. Consumer Group processes entries.
3. Per-machine sequencing checks with `seqNo`.
4. Idempotency state in Redis hash or DB table.
5. Failed pending entries are reclaimed.

## Stream Design

- Stream key: `writes:{shard}`
- Entry fields: `machineId`, `requestId`, `seqNo`, `payload`
- Consumer groups: one group per service
- Partition by machine hash to scale streams

## Ordering Strategy

- Use shard key derived from `machineId`.
- Within shard, process machine lanes in sequence.
- Persist last applied `seqNo` per machine.

## Reliability Strategy

- Process then ACK (`XACK`) only after durable write.
- Reclaim stuck pending entries via `XAUTOCLAIM`.
- Idempotency check prevents replay duplicates.

## Trade-offs

- Very fast and simple to run.
- Durability depends on Redis persistence setup.
- Consumer-group logic must handle pending-message lifecycle.

## Interview Follow-Ups

1. What if Redis restarts?
Answer direction: enable AOF/RDB policies and verify recovery semantics.

2. How do you avoid out-of-order replays?
Answer direction: enforce `seqNo` check against last applied sequence.

3. Where is source of truth?
Answer direction: business DB remains source of truth; stream drives ordered execution.
