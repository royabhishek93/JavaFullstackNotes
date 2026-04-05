# Option E: Global Ordering Without Kafka

> Use only when interviewer requires one total order across all machines.

## Scenario

All writes from all submachines must be observed in a single global sequence, not only per-machine order.

## Pattern 1: Single Writer Service

1. All writes go through one sequencer/writer service.
2. Sequencer assigns monotonic global sequence.
3. Writer applies operations serially to DB/state machine.

Pros:

- Simple correctness model.
- Easy to explain in interview.

Cons:

- Throughput bottleneck.
- Single hot path and higher tail latency.

## Pattern 2: Consensus Log (Raft/Paxos Style)

1. Cluster leader assigns log index.
2. Entries replicated to quorum.
3. Commit order defines global order.
4. State machine applies in committed index order.

Pros:

- Strong ordering with fault tolerance.
- Better HA than single process.

Cons:

- Higher complexity.
- Quorum latency and operational overhead.

## Correctness Controls

- requestId idempotency table.
- Global sequence checkpointing.
- Retries with deterministic replay.
- Snapshot + log compaction for recovery.

## Interview Follow-Ups

1. Why not always use global order?
Answer direction: expensive and unnecessary for many domains; per-key ordering scales better.

2. How do you recover after crash?
Answer direction: replay committed log from last snapshot checkpoint.

3. What is your CAP trade-off?
Answer direction: strong consistency with quorum can reduce availability during partitions.
