# Kafka vs RabbitMQ vs SQS — When to Use Which
### Three very different tools that all call themselves "message queues" — knowing the difference wins interviews

---

## PART 1 — THE STUDENT CONVERSATION

Three different kinds of postal services. All deliver messages. Completely different contracts.

**Kafka — the newspaper printing press:**
Once printed, the newspaper exists forever (configurable retention, default 7 days). Millions of readers can subscribe. Each reader has their own bookmark (offset) — a reader who was on vacation can come back and read every edition they missed (replay). The press doesn't care if readers are slow — they catch up on their own time. The press runs at industrial scale: millions of papers per second. But the press can't say "deliver this only to readers in New York who asked for sports" — complex routing rules are awkward. The press prints everything; readers filter on their end.

**RabbitMQ — the traditional post office with smart sorting:**
You bring a letter to the exchange (sorting room). The sorting room has rules: "anything marked 'sports' goes to Queue A, anything marked 'weather' goes to Queue B, anything marked 'breaking' goes to both." Once a worker takes a letter from the queue and signs for it, the letter is gone. No replay. But the routing intelligence is exceptional — direct routing, fanout, topic pattern matching, header-based routing. Built-in message priority, TTL, delayed delivery. Great for task queues where one worker should handle each job exactly once.

**SQS — the simple managed mailbox:**
You drop a message in. Workers pull it out. AWS manages everything — no servers, no config, no operations. When a worker picks up a message, it becomes invisible to other workers for 30 seconds (visibility timeout). If the worker acknowledges (deletes) the message, it's gone. If the worker crashes, the message reappears for another worker. Dead Letter Queue is built-in. Integrates perfectly with Lambda. But no replay, no complex routing, max 256KB per message.

**The rule of thumb:**
- Need replay or event sourcing? → Kafka
- Need complex routing or task queue semantics? → RabbitMQ
- Need managed, simple, Lambda-integrated? → SQS

---

## PART 2 — ARCHITECTURE DIAGRAMS

### Kafka: The Distributed Log

```
Producers                 Kafka Cluster                    Consumers
─────────                 ─────────────                    ─────────
Payment      →   Topic: payment-events (6 partitions)
Service              P0: [e1][e4][e7][e10]...       →  Group: payment-processor
                     P1: [e2][e5][e8]...             →    Consumer-A (P0,P1)
                     P2: [e3][e6][e9]...             →    Consumer-B (P2,P3)
                                                     →    Consumer-C (P4,P5)
                         ↑ Log retained 7 days       →  Group: audit-service
                                                     →    Consumer-X (all partitions)
                                                          (own offset, independent)

Key properties:
  ✓ Multiple independent consumer groups — each with its own offset
  ✓ Any group can replay from offset=0
  ✓ Consumers PULL at their own pace
  ✗ Message not deleted after consumption
  ✗ Routing: partition by key only, no topic-level filter routing
```

### RabbitMQ: The Smart Exchange

```
Producers                 RabbitMQ Broker                  Consumers
─────────                 ──────────────                   ─────────
Order        →   Exchange: orders (type=topic)
Service           Binding: "order.created.*" → Queue: new-orders  → Worker-A
                  Binding: "order.*.us-east" → Queue: us-orders   → Worker-B
                  Binding: "#"               → Queue: audit-all   → Audit-Worker

Payment      →   Exchange: payments (type=fanout)
Service           → Queue: payment-db-writer    → DB Writer
                  → Queue: payment-notifier     → Notifier
                  → Queue: payment-fraud-check  → Fraud Checker

Key properties:
  ✓ Rich routing: direct, fanout, topic (wildcard), headers
  ✓ Message acknowledged and DELETED from queue after processing
  ✓ Priority queues, message TTL, delayed delivery built-in
  ✓ Consumers PUSH (broker delivers to consumer)
  ✗ No replay — message gone once consumed
  ✗ Lower throughput than Kafka
```

### SQS: The Managed Mailbox

```
Producer             SQS Queue                     Consumers
────────             ─────────                     ─────────
Lambda    →   Queue: order-processing
API GW    →     [msg1] [msg2] [msg3]...    →   Worker picks up msg1
                  ↑                              visibility timeout: 30s
                  msg1 invisible for 30s          Worker processes
                  If worker crashes:              Worker deletes msg1 (ACK)
                    msg1 reappears
                  After N failures:
                    → Dead Letter Queue

FIFO SQS:
  Exactly-once delivery + strict ordering per MessageGroupId
  Throughput: 300 msg/s (3000 with batching) — much lower than standard

Key properties:
  ✓ Zero operations — AWS manages everything
  ✓ Native Lambda trigger (event-driven compute)
  ✓ Visibility timeout prevents duplicate processing
  ✓ DLQ built-in
  ✗ No replay
  ✗ Max 256KB message size
  ✗ No complex routing
  ✗ No consumer groups with independent offsets
```

---

## PART 3 — FEATURE COMPARISON AND REAL NUMBERS

### Full Feature Comparison Table

```
┌──────────────────────────┬──────────────────┬──────────────────┬──────────────┐
│ Feature                  │ Kafka            │ RabbitMQ         │ SQS          │
├──────────────────────────┼──────────────────┼──────────────────┼──────────────┤
│ Throughput               │ 1M+ msg/s        │ 50K–200K msg/s   │ 10K–40K msg/s│
│ Message replay           │ Yes (7d default) │ No               │ No           │
│ Routing complexity       │ Low (key-based)  │ High (exchange)  │ None/basic   │
│ Message ordering         │ Per partition    │ Per queue        │ FIFO mode    │
│ Consumer model           │ Pull             │ Push             │ Pull         │
│ Max message size         │ 1MB (default)    │ 128MB            │ 256KB        │
│ Message retention        │ Configurable     │ Until consumed   │ 4 days max   │
│ Multiple consumer groups │ Yes (own offset) │ Multiple queues  │ Multiple     │
│                          │                  │ (separate copy)  │ consumers    │
│ Delivery guarantee       │ At-least-once    │ At-least-once    │ At-least-once│
│                          │ Exactly-once     │ (with publisher  │ (FIFO:       │
│                          │ (transactions)   │ confirms)        │ exactly-once)│
│ Ops complexity           │ High             │ Medium           │ Zero         │
│ Managed service (AWS)    │ MSK              │ AmazonMQ         │ Native SQS   │
│ Protocol                 │ Kafka binary     │ AMQP 0-9-1       │ HTTP/HTTPS   │
│ Priority queues          │ No               │ Yes              │ No           │
│ Delayed delivery         │ No (workaround)  │ Yes (plugin)     │ Yes (up 15m) │
│ Message TTL              │ Topic-level only │ Per message      │ Per queue    │
│ Partition / scaling unit │ Partition        │ Queue            │ Queue        │
└──────────────────────────┴──────────────────┴──────────────────┴──────────────┘
```

### When Each System Breaks Down

```
KAFKA — avoid when:
  - Your message volume is < 100K/day (massive over-engineering, high ops cost)
  - You need complex routing: "deliver only to consumers in eu-west region" is awkward
  - Messages are > 1MB frequently (tunable but adds complexity)
  - Your team has no Kafka ops experience (ZooKeeper/KRaft, partition rebalancing,
    ISR tuning — real operational burden)
  - You need built-in delayed delivery (Kafka has no native delay mechanism)

RABBITMQ — avoid when:
  - You need message replay (architectural impossibility — messages deleted on consume)
  - Throughput > 500K msg/s sustained (benchmark before committing)
  - You need the simplicity of zero ops (RabbitMQ needs cluster management)
  - You're heavily AWS-native (AmazonMQ works but SQS/MSK integrate more naturally)

SQS — avoid when:
  - Messages exceed 256KB (use S3 + SQS pointer pattern for large payloads)
  - You need replay or event sourcing
  - You need complex routing rules
  - You need > 40K msg/s on standard queue without sharding
  - You need cross-cloud or on-premise deployment
```

### Real-World Throughput Numbers (Production-Grade Hardware)

```
Kafka (3-broker cluster, m5.2xlarge):
  Write: 800K–1.2M msg/s (1KB messages, acks=1)
  Read:  2M+ msg/s (sequential reads from page cache)
  Latency: 2–5ms p50, 10ms p99

RabbitMQ (3-node cluster, m5.xlarge):
  Write: 80K–150K msg/s (persistent messages, publisher confirms)
  Read:  100K–200K msg/s
  Latency: 1–3ms p50, 5ms p99 (lower latency than Kafka for small workloads)

SQS Standard:
  Write: ~10K–40K msg/s per queue (soft limits, increase via AWS support)
  Read:  limited by consumers; long-polling: 20s wait, up to 10 msg/batch
  Latency: 10–50ms (network-dependent, AWS regional)
  FIFO:  300 msg/s (3,000 with batching), exactly-once

MSK (Managed Kafka on AWS):
  Same throughput as self-hosted Kafka
  Zero broker operations — AWS handles upgrades, scaling, replication
  Cost: ~2–3x self-hosted for equivalent performance
```

### Hybrid Pattern: Kafka + SQS Fan-Out

```
Use case: high-throughput event stream feeding Lambda-based microservices

  Events → Kafka (backbone, replay, audit)
              ↓
           Kafka Consumer (bridge service)
              ↓
           SQS Queue (per microservice)
              ↓
           Lambda Function (auto-scales with queue depth)

Why:
  - Kafka handles 1M+ events/s from producers
  - Lambda can't consume Kafka natively at scale (offset management issues)
  - SQS → Lambda trigger is natively managed by AWS
  - Bridge adds latency (~100ms) but decouples scaling
  - Each microservice has its own SQS queue: independent scaling, independent DLQ
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your food delivery app needs to notify restaurants when new orders arrive. You expect 10,000 orders per minute at peak. Which messaging system do you use?"

**You (architect answer):**

> "10,000 orders/minute is about 167 orders/second — that's well within the range of all three systems, so throughput alone doesn't force the choice. Let me think through the actual requirements.
>
> For restaurant notifications, I need to consider: do I need replay? Yes — if a notification worker crashes, I want to re-deliver missed notifications. Does order history matter for analytics and debugging? Yes. So Kafka makes sense as the primary backbone: I can replay events for failed notifications and audit exactly when each order was dispatched.
>
> But here's the nuance for restaurant notification delivery specifically: restaurants are online at different times. A restaurant might be offline for 10 minutes and then reconnect. I need the notification to reach them when they reconnect, not just while they're online. SQS is actually a great fit here — I'd use Kafka as the event backbone and a bridge service that fans out order events into per-restaurant SQS queues. When the restaurant app connects, it drains its queue. Visibility timeout handles the case where the restaurant app picks up the order but crashes before confirming.
>
> For the mobile push notifications to customers ('your order was accepted'), I'd keep it simple — SQS or just direct calls to FCM/APNS through a notification service, since these are fire-and-forget with no replay requirement.
>
> So my architecture: Kafka as the order event backbone (replay, audit, fan-out to multiple consumers), SQS per-restaurant for reliable delivery with reconnect support, and direct push for customer notifications."

---

## PART 5 — DECISION FRAMEWORK

### Decision Flowchart

```
START: Choosing a messaging system

Do you need to REPLAY messages (re-read old events)?
  YES → Kafka (period — neither RabbitMQ nor SQS can replay)
  NO  → continue

Is your throughput > 500K msg/s?
  YES → Kafka (only option that scales here reliably)
  NO  → continue

Do you need complex routing?
  (e.g., "route to queue A if type=sports AND region=us-east")
  YES → RabbitMQ
  NO  → continue

Are you AWS-native and want zero ops?
  YES → SQS
       Need ordering? → SQS FIFO (300/s limit)
       Lambda trigger? → SQS Standard (native EventSourceMapping)
  NO  → RabbitMQ (if complex routing) or Kafka (if multi-consumer fan-out)

Hybrid cases:
  Kafka backbone + SQS fan-out: high-throughput event stream → Lambda microservices
  Kafka backbone + RabbitMQ: event log + complex task routing for workers
```

### Quick Selection Table

| Scenario | Best Choice | Runner-Up | Why |
|----------|------------|-----------|-----|
| Event sourcing / audit log | Kafka | — | Replay is mandatory |
| Microservice task queue, one worker per job | RabbitMQ or SQS | — | Work queue semantics |
| Lambda-triggered processing | SQS | — | Native AWS integration, zero ops |
| 1M+ events/sec | Kafka | — | Only option at this scale |
| Complex routing rules | RabbitMQ | — | Exchange/binding model purpose-built for this |
| Multi-tenant event stream | Kafka | — | Consumer groups with independent offsets |
| Simple job queue, AWS-native | SQS | RabbitMQ | Simplicity wins |
| Pub-sub with multiple subscribers | Kafka or RabbitMQ (fanout) | SQS SNS fanout | Kafka if replay needed |
| Delayed / scheduled messages | RabbitMQ (plugin) or SQS (15m) | — | Neither Kafka natively |
| Priority message processing | RabbitMQ | — | Native priority queue support |

---

## QUICK REFERENCE CARD

```
KAFKA:
  Use for:   event sourcing, audit logs, replay, 100K+ msg/s, multi-consumer fan-out
  Avoid for: < 100K msg/day, complex routing, large messages (>1MB), zero-ops teams
  AWS managed: MSK (Amazon Managed Streaming for Kafka)
  Retention: default 7 days (configurable to forever with infinite.storage)
  Consumer: PULL (consumer controls pace)

RABBITMQ:
  Use for:   complex routing (topic/direct/fanout/headers), task queues, priority,
             delayed messages, mixed consumers needing different routing rules
  Avoid for: replay, > 500K msg/s, AWS-native teams preferring zero ops
  AWS managed: AmazonMQ
  Retention: until consumed (or TTL)
  Consumer: PUSH (broker delivers to consumer)

SQS:
  Use for:   zero-ops, Lambda triggers, AWS-native, simple task queues
  Avoid for: replay, > 256KB messages, complex routing, > 40K msg/s single queue
  Standard:  at-least-once, unordered, high throughput
  FIFO:      exactly-once, ordered, 300/s (3000 with batching)
  Visibility timeout: message invisible while being processed (default 30s)
  DLQ: built-in (moves message after N receive attempts)

THROUGHPUT LADDER:
  SQS Standard:  10K–40K msg/s
  RabbitMQ:      50K–200K msg/s
  Kafka:         1M+ msg/s

HYBRID PATTERN:
  Kafka → bridge → SQS → Lambda  (high-throughput stream feeding serverless)
  Kafka → bridge → RabbitMQ      (event log + smart task routing)
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** In any system design interview, the moment you say "I'll use a message queue," expect the follow-up: "which one and why?" Having a concrete decision framework with numbers is what separates a junior answer from an architect answer.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **03 — Notification System** | Kafka as the backbone for all notification events — high throughput (10M users), replay for debugging failed delivery batches. SQS as the delivery layer for Lambda-based email sending (simple, managed, handles 256KB HTML email payloads natively). RabbitMQ considered but rejected — no replay capability is a dealbreaker for notification audit requirements. |
| **07 — Payment Processing** | Kafka for payment events — replay is mandatory for financial audit (regulators require 7+ year event history), exactly-once transactions supported natively. For retry/DLQ on failed gateway calls (transient network issues), SQS or a RabbitMQ dead-letter queue is a simpler fit than Kafka's DLQ model — task queue semantics with backoff are natural in RabbitMQ. |
| **08 — Food Delivery** | Order events → Kafka (replay for order history, high throughput at peak dinner hours). Restaurant notification → SQS per-restaurant (restaurants go offline, SQS buffers and delivers on reconnect, visibility timeout handles restaurant app crashes). Customer push notifications → direct to FCM/APNS via notification service (fire-and-forget, no replay needed). |

**Architect's one-liner for the interview:**
*"Kafka is a distributed log you read like a database — choose it when replay and throughput matter. SQS is a managed mailbox — choose it when simplicity and Lambda integration matter. RabbitMQ is a smart router — choose it when complex delivery rules matter. Most real systems use two of the three."*
