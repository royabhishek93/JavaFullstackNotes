# Distributed Systems + Concurrency Design (No Kafka Options)

Scenario: N submachines concurrently write to one main machine with ordering and correctness guarantees.

## Options

- [Option A: Database-Backed Queue + Ordered Workers](option-a-database-backed-queue.md)
- [Option B: RabbitMQ + Consistent Hash Routing](option-b-rabbitmq-consistent-hash.md)
- [Option C: Redis Streams + Consumer Groups](option-c-redis-streams.md)
- [Option D: SQS FIFO Pattern](option-d-sqs-fifo.md)
- [Option E: Global Ordering Without Kafka](option-e-global-ordering-without-kafka.md)
- [Kafka vs No-Kafka: Ordered Writes](kafka-vs-no-kafka-ordered-writes.md)

## Core Guarantees To Mention In Any Design

- Ordering scope: per-machine vs global
- Idempotency key: `requestId`
- Sequence enforcement: `seqNo`
- Durable state transitions: ACCEPTED -> APPLIED -> ACKED
- Retry with DLQ and bounded retry budget
