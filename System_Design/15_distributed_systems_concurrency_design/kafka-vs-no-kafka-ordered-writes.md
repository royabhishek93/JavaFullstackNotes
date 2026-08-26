# Kafka vs No-Kafka: Ordered Concurrent Writes (Interview Implementation)

> **Interview Frequency:** 80% (senior/staff) | **Difficulty:** ⭐⭐⭐⭐⭐ | **Study Time:** 15 minutes

---

## Problem Restated (Simplified)

- 1 Main Machine (central system / DB)
- 5 Submachines (clients/services)
- Each sends multiple write operations
- All writes can arrive concurrently

Requirements:

1. No data loss
2. Maintain sequence/order of writes
3. Handle high concurrency
4. Each submachine gets correct response

---

## Key Challenge

You need both:

1. Concurrency handling
2. Ordering guarantee

These can conflict if not designed explicitly.

---

## Step 1: Clarify Ordering Scope (Always Say This)

1. **Per-machine ordering**
Order must be preserved for each submachine independently.

2. **Global ordering**
One total order across all submachines.

In most interviews, propose per-machine ordering first (better throughput), then explain global-order fallback.

---

## Implementation A: With Kafka

### Architecture

1. Write Gateway API
2. Kafka topic `writes`
3. Partition key = `machineId`
4. Ordered consumer workers
5. Business DB
6. Idempotency store
7. Ack/status endpoint

### Request Contract

```json
{
  "machineId": "M1",
  "requestId": "M1-00045",
  "seqNo": 45,
  "operations": [
    {"opId": "1", "type": "UPSERT", "entityId": "A", "value": 10},
    {"opId": "2", "type": "UPSERT", "entityId": "B", "value": 20}
  ]
}
```

### Write Flow

1. Gateway validates schema/auth.
2. Check idempotency key `(machineId, requestId)`.
3. Publish event to Kafka keyed by `machineId`.
4. Kafka preserves FIFO within partition.
5. Consumer processes message in DB transaction.
6. Persist result + mark idempotency completed.
7. Commit offset only after durable DB commit.
8. Return `202` (async) or `200` (sync after commit).

### Why It Meets Requirements

1. **No data loss:** Kafka durability + replication + retry
2. **Ordering:** FIFO per partition via `machineId` key
3. **High concurrency:** parallel partitions/consumers
4. **Correct response:** status store + idempotent replays

### Failure Handling

1. Consumer crash after DB commit: replay hits idempotency, no duplicate apply
2. Duplicate request from client: same `requestId` returns prior result
3. Out-of-order `seqNo`: hold/buffer or reject with conflict
4. Poison message: move to DLQ after retry limit

### Interview One-Liner (Kafka)

"I would partition Kafka by machineId, process with idempotent consumers, and commit offsets only after DB commit. This guarantees per-machine order with high concurrency and safe retries."

---

## Implementation B: Without Kafka

Choose one transport based on environment:

1. RabbitMQ (consistent-hash queues)
2. DB-backed queue table
3. Redis Streams
4. SQS FIFO

The logic stays same: ordering key + idempotency + durable apply + retry control.

### Example (RabbitMQ)

1. Gateway publishes message with routing key `machineId`.
2. Consistent-hash exchange maps machine to same queue lane.
3. Single consumer per lane preserves FIFO.
4. Consumer writes to DB transactionally.
5. Ack only after commit.
6. On retry/delivery duplicates, idempotency suppresses reapply.

### Example (DB Queue)

1. Insert request into `queue_requests` table.
2. Workers fetch with `FOR UPDATE SKIP LOCKED`.
3. Process by `(machineId, seqNo)` order.
4. Persist idempotency and result state.

### Why It Meets Requirements

1. **No data loss:** durable broker/table + retries
2. **Ordering:** machine-specific lanes and seq checks
3. **High concurrency:** many lanes/consumers
4. **Correct response:** request tracking + dedupe

### Interview One-Liner (No Kafka)

"If Kafka is not allowed, I keep the same correctness model and swap transport to RabbitMQ/Redis/SQS/DB queue. I still enforce machineId ordering, requestId idempotency, and seqNo validation."

### Standalone Interview Solution (Without Kafka, Recommended)

Use **DB-backed queue + ordered worker lanes** as the default no-Kafka design.

#### Components

1. Write API Gateway
2. `queue_requests` durable table
3. Worker pool with lane assignment by `machineId`
4. Business transaction service
5. Idempotency table
6. Ack/status API

#### Minimal Tables

```sql
CREATE TABLE queue_requests (
  id BIGSERIAL PRIMARY KEY,
  machine_id VARCHAR(64) NOT NULL,
  request_id VARCHAR(128) NOT NULL,
  seq_no BIGINT NOT NULL,
  payload JSONB NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  UNIQUE(machine_id, request_id)
);

CREATE INDEX idx_q_machine_status_seq
ON queue_requests(machine_id, status, seq_no);

CREATE TABLE idempotency (
  machine_id VARCHAR(64) NOT NULL,
  request_id VARCHAR(128) NOT NULL,
  result_hash VARCHAR(128),
  status VARCHAR(20) NOT NULL,
  PRIMARY KEY(machine_id, request_id)
);
```

#### Processing Flow

1. Client sends `(machineId, requestId, seqNo, operations)`.
2. API stores request in `queue_requests` with `PENDING`.
3. Worker fetches rows using `FOR UPDATE SKIP LOCKED`.
4. Worker checks idempotency and expected sequence.
5. Worker applies operations in DB transaction.
6. Worker marks request `APPLIED`, stores idempotency result.
7. API returns final status by `requestId`.

#### Why This Satisfies Your Requirements

1. **No data loss:** request is durably inserted before processing.
2. **Maintain sequence:** process by `(machineId, seqNo)`.
3. **High concurrency:** multiple worker lanes in parallel.
4. **Correct response:** status/idempotency table gives deterministic reply.

#### Failure Cases

1. Duplicate request retry -> same `(machineId, requestId)` returns prior result.
2. Crash after commit before response -> replay reads idempotency, no duplicate apply.
3. Out-of-order seq -> hold briefly or return conflict and retry instruction.
4. Poison payload -> move to failed state after bounded retry attempts.

#### 30-Second Answer (No Kafka)

"I would implement a durable DB queue where each write request is persisted with machineId, requestId, and seqNo. Workers process requests in machine-specific order using row locking and transactional apply. Idempotency guarantees safe retries, and status tracking guarantees correct responses. This gives ordered, concurrent, no-loss writes without Kafka."

### Beginner-Friendly Explanation (Important Terms)

#### What is `queue_requests`?

- It is a **database table used like a queue**.
- Each row is one pending write job.
- It stores who sent the request, sequence number, payload, and status.

Think of it like a ticket counter:

- New request -> new ticket row (`PENDING`)
- Worker processes it -> status becomes `APPLIED` or `FAILED`

#### What does `FOR UPDATE SKIP LOCKED` mean?

It helps multiple workers safely pick different rows.

1. `FOR UPDATE` = lock selected row so others cannot process same row.
2. `SKIP LOCKED` = if row is already locked by another worker, skip it and continue.

Why it matters:

- Prevents two workers from processing same request.
- Improves concurrency because workers do not wait unnecessarily.

#### What is a `worker` here?

- Worker is a background processor (thread/process/service instance).
- API receives requests quickly and stores them.
- Worker does the heavy work later: read queue row, execute DB write, update status.

Worker responsibilities:

1. Pick next request from `queue_requests`
2. Check idempotency (dedupe)
3. Validate sequence (`seqNo`)
4. Apply operations in transaction
5. Mark result and finish

#### What is `dedupe` here?

`Dedupe` means **deduplication**: avoid processing same request twice.

Why duplicates happen:

- Client timeout and retry
- Network retry by gateway
- Worker crash after commit but before response

How dedupe works:

1. Every request has unique `requestId`
2. Store `(machineId, requestId)` in `idempotency`
3. If same request comes again, return stored result (do not apply write again)

#### Tiny Example (2 Workers)

Assume requests in table:

- R1: `(M1, req-101, seq=101, PENDING)`
- R2: `(M1, req-102, seq=102, PENDING)`
- R3: `(M2, req-51, seq=51, PENDING)`

Execution:

1. Worker A locks R1 using `FOR UPDATE`.
2. Worker B sees R1 locked, `SKIP LOCKED` picks R3.
3. Both process in parallel safely.
4. If `req-101` is retried, dedupe detects it and returns old result.

This is how we get both concurrency and correctness.

---

## Global Ordering Variant (If Interviewer Insists)

1. Single writer service, or
2. Consensus log service (Raft-style)

Trade-off:

- Simpler global correctness
- Lower throughput and higher latency

---

## Batch vs Single Requests

1. **Batch in one call (10 writes)**
- One `requestId`, inner ordered `opId/index`
- Apply in deterministic list order

2. **10 separate calls**
- Unique `requestId` per call
- `seqNo` enforces arrival/apply order

Always persist both `requestId` and `seqNo`.

---

## Pseudocode (Common to Both)

```text
onWrite(request):
  validate(request)
  if idempotency.exists(machineId, requestId):
    return previousResult

  enqueue(request, key=machineId)
  return accepted(trackingId)

workerProcess(message):
  if idempotency.exists(machineId, requestId):
    ack(message)
    return

  ensureSequence(machineId, seqNo)
  tx.begin()
  applyOperationsInOrder(message.operations)
  saveResultAndIdempotency(machineId, requestId)
  tx.commit()
  ack(message)
```

---

## Follow-Up Questions (Interviewer Usually Asks)

1. Why do you need both `requestId` and `seqNo`?

`requestId` handles dedupe; `seqNo` handles ordering correctness.

2. Is exactly-once guaranteed?

Transport is usually at-least-once; idempotent consumer gives effectively-once behavior.

3. How do you prevent stale reads after write?

Use read-your-write token/version or route critical reads to primary.

4. What breaks first at scale?

Hot keys/partitions and unbounded retries; mitigate by lane scaling, rate limits, DLQ policy.

5. How do you measure success?

- Write accept rate
- Apply latency p95/p99
- Duplicate suppression count
- Sequence conflict count
- DLQ depth

---

## Related Files

- [distributed-systems-concurrency-design-interviews.md](distributed-systems-concurrency-design-interviews.md)
- [option-a-database-backed-queue.md](option-a-database-backed-queue.md)
- [option-b-rabbitmq-consistent-hash.md](option-b-rabbitmq-consistent-hash.md)
- [option-c-redis-streams.md](option-c-redis-streams.md)
- [option-d-sqs-fifo.md](option-d-sqs-fifo.md)
- [option-e-global-ordering-without-kafka.md](option-e-global-ordering-without-kafka.md)
