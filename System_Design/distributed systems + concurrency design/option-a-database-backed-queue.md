# Option A: Database-Backed Queue + Ordered Workers

> Use when Kafka is not allowed and traffic is moderate.

## Scenario

Five submachines send concurrent writes to one main machine. Each machine may send batch writes or separate calls. Preserve per-machine order and guarantee safe retries.

## Architecture

1. Write Gateway API
2. `queue_requests` table (durable queue)
3. Ordered worker pool
4. Business DB transaction layer
5. Idempotency table

## Data Model

```sql
CREATE TABLE queue_requests (
  id BIGSERIAL PRIMARY KEY,
  machine_id VARCHAR(64) NOT NULL,
  request_id VARCHAR(128) NOT NULL,
  seq_no BIGINT NOT NULL,
  payload JSONB NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE (machine_id, request_id)
);

CREATE INDEX idx_queue_machine_status_seq
ON queue_requests(machine_id, status, seq_no);

CREATE TABLE idempotency (
  machine_id VARCHAR(64) NOT NULL,
  request_id VARCHAR(128) NOT NULL,
  result_hash VARCHAR(128),
  status VARCHAR(20) NOT NULL,
  PRIMARY KEY (machine_id, request_id)
);
```

## Processing Pattern

1. API validates request and stores row in `queue_requests`.
2. Worker pulls rows using `FOR UPDATE SKIP LOCKED`.
3. Worker executes write in DB transaction.
4. Worker marks status `APPLIED` and persists idempotency result.
5. Ack response returned or callback emitted.

## Ordering Strategy

- Per-machine ordering: worker lane keyed by `machine_id`.
- Process by `seq_no` ascending.
- If gap detected (expect 46, got 47), hold or return `409 SequenceConflict`.

## Why It Works

- Durable queue is in DB.
- `SKIP LOCKED` prevents worker contention.
- Idempotency avoids duplicate writes after retries.

## Trade-offs

- Simpler operations than Kafka.
- DB can become bottleneck at high scale.
- Need careful indexing and archiving.

## Interview Follow-Ups

1. What if one machine is too hot?
Answer direction: isolate to dedicated worker lane, rate limit, and shard by machine group.

2. How do you scale beyond one DB?
Answer direction: partition queue table by machine hash, or move to broker later.

3. Is exactly-once guaranteed?
Answer direction: broker/db gives at-least-once; idempotent consumer gives effectively-once.
