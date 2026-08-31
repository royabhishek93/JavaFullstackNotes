# When should you choose Kafka over Redis Streams for a 90-day replayable event log?

**Type:** Advanced Scenario-Based
**Topic:** Redis Streams vs Kafka
**Level:** Staff/Principal Interview (15+ YOE)

## Direct Answer
Choose Kafka when you need long retention (weeks/months) combined with high throughput and many independent consumer groups replaying history — for example, an analytics platform, audit trail, or fraud-model training pipeline. Redis Streams are excellent for short-to-medium-lived, low-latency workflows near data you already keep in Redis, but 90 days of high-volume events kept entirely in memory becomes very expensive and operationally risky.

## Easy Explanation
Redis Streams are like a whiteboard: fast to write on, easy to read from, but you wouldn't want to store three months of company history on it — it's expensive board space (RAM) and one accidental wipe (a restart without persistence, or a bad `XTRIM`) loses everything. Kafka is like a filing cabinet built for exactly that: durable, disk-based, designed to hold a long, replayable history cheaply.

## Diagram
```
Decision matrix:

                     Retention window       Throughput        # of consumer groups
Redis Streams   -->  short/medium (hours-days)  moderate       few, tightly coupled
Kafka           -->  long (weeks-months+)        very high      many, independent

Example: order events consumed by...
  - fraud-model training (needs 90 days of history)      -> Kafka
  - payment verification workers (process within minutes) -> Redis Streams
  - real-time inventory reservation (seconds matter)       -> Redis Streams
  - analytics warehouse ingestion (replay anytime)          -> Kafka
```

## Production Example
An e-commerce platform uses **both**, for different jobs on the same underlying "order placed" event:

- A Redis Stream (`order-events`, retained ~2 hours via `MAXLEN`) feeds the inventory-reservation and payment-verification workers, because they must react within seconds and never need to replay from 3 weeks ago.
- The same event is also published to a Kafka topic (`order-events-audit`, retained 90 days) consumed independently by the fraud-detection model trainer and the BI/analytics team, who need long history and can tolerate higher latency.

This avoids forcing one system to do a job it's not built for — Redis stays fast and cheap for the short-lived hot path, Kafka handles the long-lived cold path.

## Why Interviewers Ask This
It tests whether a candidate defaults to "just use what we already have" versus reasoning from actual retention, throughput, and consumer-count requirements — and whether they're comfortable recommending two different tools for two different jobs on the same event.
