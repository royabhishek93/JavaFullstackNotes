# Backpressure & Reactive Streams — LinkedIn Post

## Post Text (copy-paste ready)

Your producer makes 10,000 orders/sec. Your consumer handles 1,000/sec. That gap = 32.4 million messages piling up in one hour.

Most engineers only discover this the hard way — an OOM crash during a flash sale.

Here's what actually stops the fire hose from drowning the watering can:

- **Unbounded `flatMap` = OOM.** `flux.flatMap(this::callService)` opens unlimited concurrent subscriptions. Use `flatMap(this::callService, 16)` — bounded concurrency, memory stays flat.
- **Kafka's poll loop IS backpressure.** No signaling needed — a slow processing loop means fewer `poll()` calls, which means the broker just holds messages on disk. Nothing crashes, nothing gets lost.
- **5 real strategies, pick by data-loss tolerance:** drop-on-overflow (logs/metrics), block-the-producer (internal batch jobs), external durable queue (Kafka/SQS — most production systems), autoscale-the-consumer (bursty traffic), circuit-breaker-503 (HTTP chains with no queue).
- **Partition math sets your ceiling:** throughput = partitions × throughput_per_consumer. 20 partitions × 10K msg/sec/consumer = 200K msg/sec max — no amount of code tuning gets you past this.
- **Autoscaling on CPU is the wrong signal.** Scale Kubernetes HPA on `kafka_consumer_lag_messages` instead — CPU can look fine while lag balloons into the millions.

Real example: a celebrity post triggers 10M fan-out notification events in seconds. Kafka absorbs the burst on disk, consumers autoscale off lag (not CPU), and a separate priority topic keeps time-sensitive alerts from queuing behind millions of bulk notifications.

Swipe → to see the full pull-model diagram, the strategy comparison table, and the decision tree.

Save this. You'll need it in your next system design interview.

This wraps up the full 29-part system design series — from CAP theorem to backpressure, the complete architect's toolkit.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
10K orders/sec vs 1K/sec consumer = 32.4M messages/hour piling up. Here's how Kafka, bounded flatMap, and HPA-on-lag stop the OOM crash.

### Variant B — Long (400–600 chars)
A fire hose at 500L/sec into a watering can that takes 2L/sec — that's what an unthrottled producer does to a slow consumer. Without backpressure: in-memory buffer overflow, OutOfMemoryError, crash, and every buffered message lost. With it: Kafka's poll loop naturally throttles, bounded `flatMap(n)` caps concurrency instead of exploding it, and Kubernetes HPA scales consumers on `kafka_consumer_lag_messages` instead of misleading CPU graphs. This post breaks down all 5 backpressure strategies with the exact partition-throughput formula and a real 10M-event celebrity fan-out example — the final chapter in the full system design series.

---

## Best Time to Post
Tuesday–Thursday, 8:00–10:00 AM local time (peak LinkedIn engagement for technical/career content, before the workday's meeting load starts).

## Engagement Hook
Close the post with a question to drive comments: "Which backpressure strategy have you actually had to implement in production — drop, block, external queue, autoscale, or circuit breaker? Drop it below."
