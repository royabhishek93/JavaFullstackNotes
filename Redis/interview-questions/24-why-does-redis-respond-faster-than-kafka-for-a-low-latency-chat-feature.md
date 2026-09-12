# Why does Redis respond faster than Kafka for a low-latency chat feature?

**Type:** Scenario-Based
**Topic:** Redis vs Kafka — Speed Trade-offs
**Level:** Mid–Senior Interview (5–10+ YOE)

## Direct Answer
Because Redis keeps data entirely in memory, so publishing and delivering a message never touches disk. Kafka, by design, persists every message to disk as part of its write path (that's what makes it durable and replayable) — and that disk write, even when optimized, is inherently slower than an in-memory operation.

## Easy Explanation
Passing a note by hand across a room (Redis, in-memory) is faster than writing the note into a logbook first and then having someone read it back out of the logbook (Kafka, disk-backed) — even if the logbook writer is very fast at their job. The logbook approach is more durable and reviewable later, but that durability has an inherent speed cost that hand-passing doesn't have.

## Diagram
```
Redis (in-memory):
Publisher --PUBLISH--> [ RAM ] --instant fan-out--> Subscribers
   (no disk touched at any point)

Kafka (disk-backed):
Producer --write--> [ disk log ] --read--> Consumers
   (durability requires touching disk, which has higher latency than RAM)

Measured difference in a real chat demo:
  Redis publish-to-receive:  near-instantaneous (sub-millisecond to a few ms)
  Kafka publish-to-receive:  noticeably slower (tens of ms to seconds depending on config)
```

## Production Example
A real-time chat feature (Alice messaging Bob through horizontally scaled backend instances) uses Redis Pub/Sub as the bridge between instances specifically because message delivery needs to feel instantaneous. If the same bridge were built on Kafka, every message would incur the disk-write latency of Kafka's log-based design — acceptable for many systems, but a poor fit when sub-second responsiveness is the entire point of the feature.

## Why Interviewers Ask This
It checks whether a candidate can explain *why* Redis is faster in concrete architectural terms (in-memory vs. disk-backed), rather than repeating "Redis is faster" as an unexplained fact.
