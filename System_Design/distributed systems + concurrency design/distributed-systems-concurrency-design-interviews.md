# Distributed Systems + Concurrency Design (Interview Framework)

> **Interview Frequency:** 75% (senior/staff) | **Difficulty:** ⭐⭐⭐⭐⭐ | **Study Time:** 15-20 minutes

---

## Scenario

You have 1 main machine and N submachines.

- Each submachine sends read/write requests.
- Writes can arrive concurrently.
- A single call can contain 10 writes, or 10 separate calls may arrive.
- You must preserve order and return correct acknowledgement to each submachine.

Example:

- Machines M1, M2, M3, M4, M5
- Each machine sends 5 writes
- System must process all writes safely and preserve chosen ordering guarantees.

---

## First Interview Clarification (Most Important)

Ask this first:

"Do you need global ordering across all machines, or per-machine ordering only?"

1. **Global ordering**
All writes from all machines are seen in one total order.

2. **Per-machine ordering**
For each machine, its write order is preserved. Interleaving across machines is allowed.

Most real systems choose **per-machine ordering** because global total order reduces throughput.

---

## Framework (Production-Ready)

### Components

1. **Write Gateway (ingress API)**
Accepts write requests, validates auth/schema, assigns idempotency key.

2. **Sequencer Strategy**
- Per-machine sequence: `(machineId, seqNo)`
- Optional global sequence: monotonic log offset

3. **Partitioned Durable Log (Kafka/Pulsar style)**
- Partition key = `machineId` for per-machine ordering
- Single partition topic (or consensus log) for global ordering

4. **Ordered Worker Pool**
- One active consumer per partition to preserve in-partition order
- Applies writes to DB/state machine

5. **Idempotency Store**
- Key: `machineId + requestId` (or operationId)
- Prevents duplicate execution during retries

6. **Result/Ack Service**
- Returns accepted/processed status
- Supports sync ack (after commit) or async callback/event

---

## Write Path (Per-Machine Ordering)

1. Submachine sends write with `machineId`, `requestId`, payload, optional `seqNo`.
2. Gateway validates request and checks idempotency.
3. Gateway publishes to partition keyed by `machineId`.
4. Broker guarantees FIFO inside that partition.
5. Worker reads message, executes operation in DB transaction.
6. Worker stores operation result and marks idempotency key completed.
7. Ack is returned to originating machine.

Guarantees:

- At-least-once delivery from queue + idempotent consumer = effectively-once processing.
- Strict order per machine.
- High parallelism across machines.

---

## If Interviewer Demands Global Ordering

Use one of these patterns:

1. **Single writer service** (simple, lower throughput)
2. **Consensus-backed replicated log** (Raft/Paxos style)
3. **Single queue partition** (easy but throughput bottleneck)

Trade-off to state clearly:

Global order increases correctness simplicity but reduces write scalability and raises tail latency.

---

## Data Model (Minimal)

```text
write_request(
  request_id PK,
  machine_id,
  seq_no,
  payload_hash,
  status,          -- ACCEPTED, APPLIED, FAILED
  created_at,
  applied_at
)

idempotency(
  machine_id,
  request_id,
  result_checksum,
  status,
  PRIMARY KEY(machine_id, request_id)
)
```

---

## API Contract

```http
POST /writes
{
  "machineId": "M1",
  "requestId": "M1-2026-04-01-00045",
  "seqNo": 45,
  "operations": [
    {"opId": "op1", "type": "UPDATE", "entityId": "A", "value": 10},
    {"opId": "op2", "type": "UPDATE", "entityId": "B", "value": 20}
  ]
}
```

Response options:

1. `202 Accepted` with tracking id (async)
2. `200 OK` only after durable apply (sync, higher latency)

---

## Handling 10 Writes in One Call vs 10 Calls

1. **One call with batch of 10**
- Envelope has one `requestId`
- Inner operations have `opId` and deterministic order index
- Worker applies in list order in one transaction (if required)

2. **10 separate calls**
- Each call has unique `requestId`
- `seqNo` ensures per-machine ordering and gap detection

Best practice:

Use both `requestId` (dedupe) and `seqNo` (ordering correctness).

---

## Failure Modes and Controls

1. **Duplicate retries from submachine**
Use idempotency table and return prior result.

2. **Consumer crash after DB commit before ack**
On replay, idempotency check avoids double apply.

3. **Out-of-order arrival**
Detect using `seqNo`; buffer small gaps or reject with `409 SequenceConflict`.

4. **Poison message**
Move to dead-letter queue after retry budget.

5. **Hot partition (one noisy machine)**
Rate-limit at gateway, isolate machine, autoscale consumers.

---

## Concurrency Controls in DB Layer

Pick based on domain:

1. **Optimistic locking** (version column): high read/low conflict
2. **Pessimistic locking**: critical financial paths
3. **Single-writer per key** (queue partition key = entity key): avoids lock contention

Mention in interview:

Queue ordering does not replace transactional integrity; both layers are needed.

---

## What to Say in 30 Seconds

"I would front the main machine with a write gateway and a durable partitioned log. I would key by machineId to guarantee per-machine order, process with idempotent consumers, and persist requestId plus seqNo for dedupe and sequence validation. For strict global ordering, I would switch to a single-writer or consensus log, accepting throughput trade-offs. This gives correctness, retries, and scalability with clear failure handling."

---

## Follow-Up Questions (With Expected Direction)

1. How do you guarantee ordering?

Use partition key strategy and FIFO per partition; define whether guarantee is per-machine or global.

2. How do you avoid duplicate writes during retries?

Idempotency key and result caching in durable store.

3. What if machine sends seq 45 after seq 47?

Detect out-of-order, buffer briefly or reject for client retry.

4. How will reads see fresh writes?

Use read-your-write token/version, or route critical reads to leader/primary.

5. How do you scale from 5 machines to 50k machines?

Increase partitions, shard idempotency store, and enforce rate limits.

6. What metrics prove this works?

- write acceptance rate
- apply latency p95/p99
- duplicate suppression count
- sequence conflict count
- DLQ depth

7. Where can this fail first in production?

Hot partitions, unbounded retries, and missing idempotency TTL policies.

---

## Related Notes

- [message-queues.md](message-queues.md)
- [distributed-transactions-saga-vs-2pc.md](distributed-transactions-saga-vs-2pc.md)
- [database-sharding-strategies.md](database-sharding-strategies.md)
- [cap-theorem-trade-offs.md](cap-theorem-trade-offs.md)
