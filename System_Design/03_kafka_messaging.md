# SD_Q04: Kafka & Messaging — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 25-30 minutes | **Frequency:** 85% in architect rounds 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "You use Kafka to process payments. One bad message is blocking the entire queue. How does it get there, what happens, and how do you fix it?" — The poison pill scenario.

---

## NEW LEARNER FOUNDATION

### What is a Message Queue? (Plain English)
```
Without a queue (direct call):
  OrderService calls InventoryService directly (HTTP/gRPC).
  If Inventory is slow (DB overload) → Order waits → timeout → error
  If Inventory is DOWN → Order fails immediately

With a queue (async):
  OrderService sends message to queue: "Order #123 placed"
  OrderService returns 202 Accepted immediately (does NOT wait)
  InventoryService reads message when it's ready
  If Inventory is slow: message waits in queue (no timeout)
  If Inventory is DOWN: message stays in queue, processed when it restarts

Message Queue = decoupling + buffer + resilience
```

### What is Kafka? (Plain English)
```
Kafka is a DISTRIBUTED message streaming platform.

Key concepts:
  Topic    = a named stream of messages (like a named pipe or channel)
             Example: "orders" topic, "payments" topic, "notifications" topic

  Partition = a topic is split into partitions (for parallelism)
             Partition 0: orders for users A-M
             Partition 1: orders for users N-Z
             Two consumers can process in parallel!

  Offset   = position of a message in a partition (like a page number)
             Consumer remembers: "I read up to offset 452 in partition 0"
             If consumer crashes → restarts from offset 452 (no lost messages)

  Consumer Group = a group of consumers that share a topic
             Each partition assigned to exactly ONE consumer in the group
             Add more consumers = more parallel processing (up to #partitions)

  Retention = Kafka KEEPS messages for 7 days (default)
             Unlike a queue (messages deleted after consumption)
             You can replay messages, debug by re-reading old events
```

---

## BIG PICTURE — Kafka in an E-Commerce System

```
 EVENT FLOW — ORDER PLACED
 ┌──────────────────────────────────────────────────────────────────┐
 │                                                                  │
 │  [Order Service]                                                 │
 │       │ 1. INSERT order to DB (Transactional Outbox)            │
 │       │ 2. INSERT to outbox_events table (same TX)              │
 │       ▼                                                          │
 │  [Outbox Relay (CDC)]  ← reads from outbox_events table         │
 │       │ publishes to Kafka when DB commits                       │
 │       ▼                                                          │
 │  ┌─────────────────────────────────────────────────────────────┐ │
 │  │  Kafka Topic: "order-events"                                │ │
 │  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │ │
 │  │  │ Partition 0  │ │ Partition 1  │ │ Partition 2  │        │ │
 │  │  │ userId%3==0  │ │ userId%3==1  │ │ userId%3==2  │        │ │
 │  │  │ msg1,msg2... │ │ msg3,msg4... │ │ msg5,msg6... │        │ │
 │  │  └──────────────┘ └──────────────┘ └──────────────┘        │ │
 │  └─────────────────────────────────────────────────────────────┘ │
 │       │                    │                    │                │
 │       ▼                    ▼                    ▼                │
 │  [Inventory Consumer]  [Email Consumer]  [Analytics Consumer]   │
 │  (deduct stock)        (send email)      (update dashboards)     │
 │       │                                                          │
 │       ▼ (on failure after 3 retries)                            │
 │  [DLQ: order-events-dlq]  ← Dead Letter Queue                  │
 │       │                                                          │
 │  [DLQ Handler / Alert]  ← human review / manual reprocess       │
 │                                                                  │
 └──────────────────────────────────────────────────────────────────┘

 PARTITION KEY DECISION:
 ┌──────────────────────────────────────────────────────────────────┐
 │  Key = userId → all orders for same user go to same partition   │
 │  → Ordering guaranteed per user (process user's orders in order) │
 │  Key = null → round-robin across partitions                      │
 │  → Maximum parallelism, no ordering guarantee                    │
 │  Key = orderId → every order independently ordered              │
 │  → Fine for most cases, maximum distribution                    │
 └──────────────────────────────────────────────────────────────────┘
```

---

## Scenario 1: Poison Pill — One Bad Message Blocks Everything

### The Production Disaster
```
Order #99999 is corrupted: JSON is malformed (a new service version sent bad data).
InventoryConsumer tries to process it:
  - Parse JSON → exception
  - Retry 1: exception again
  - Retry 2: exception again
  - Retry 3: exception again
  - Consumer is stuck on offset 452 in Partition 0
  - Cannot advance past the bad message
  - ALL orders behind it in Partition 0 are blocked
  - Inventory not updated for thousands of orders
  - This is a "poison pill"

Partition 1, 2 work fine. Only Partition 0 is frozen.
Alert: "1,500 orders pending, growing every minute"
```

### Fix: Dead Letter Queue (DLQ)
```java
// Spring Kafka configuration
@Bean
public DefaultKafkaConsumerFactory<String, String> consumerFactory() { ... }

@Bean
public ConcurrentKafkaListenerContainerFactory<String, String> kafkaListenerContainerFactory(
        DefaultKafkaConsumerFactory<String, String> cf,
        KafkaTemplate<String, String> template) {

    var factory = new ConcurrentKafkaListenerContainerFactory<String, String>();
    factory.setConsumerFactory(cf);

    // Retry policy: 3 attempts with 1s, 2s, 4s delays
    factory.setCommonErrorHandler(new DefaultErrorHandler(
        new DeadLetterPublishingRecoverer(template,
            (record, ex) -> new TopicPartition("order-events-dlq", record.partition())),
        new FixedBackOff(1000L, 3)  // 3 retries, 1s delay
    ));
    return factory;
}

// After 3 failed retries:
// → Message published to "order-events-dlq" (preserves original headers + payload)
// → Consumer ADVANCES past the bad message to offset 453
// → Partition 0 unblocks immediately
// → DLQ handler alerts on-call engineer with the failed message details
```

```java
// DLQ consumer — for inspection and manual reprocessing
@KafkaListener(topics = "order-events-dlq", groupId = "dlq-inspector")
public void handleDeadLetter(ConsumerRecord<String, String> record,
                              @Header Map<String, Object> headers) {
    String originalTopic = new String((byte[]) headers.get("kafka_dlt-original-topic"));
    String exception = new String((byte[]) headers.get("kafka_dlt-exception-message"));

    log.error("DLQ message from topic={}, partition={}, offset={}, exception={}",
        originalTopic, record.partition(), record.offset(), exception);
    alertService.notifyOnCall("Poison pill in " + originalTopic + ": " + exception);

    // Optionally: fix the data and re-publish to original topic
    // reprocessService.fixAndRequeue(record);
}
```

---

## Scenario 2: Exactly-Once Semantics (Preventing Duplicate Charges)

### The Problem
```
Payment consumer processes a "charge user" Kafka message.
Step 1: charge user's credit card via Stripe API ✅
Step 2: commit Kafka offset → crash BEFORE offset committed!

Consumer restarts → reads same message again (at-least-once delivery)
Step 1: charge user's credit card via Stripe API again → DOUBLE CHARGE!

Kafka default = at-least-once delivery (you WILL see duplicates on failure).
You must make your consumer idempotent.
```

```java
// FIX: Idempotent consumer with deduplication store
@KafkaListener(topics = "payment-events")
public void processPayment(PaymentEvent event) {
    String idempotencyKey = event.getOrderId() + ":" + event.getEventId();

    // Check if already processed
    Boolean processed = redis.get("processed:" + idempotencyKey);
    if (processed != null) {
        log.info("Duplicate event skipped: {}", idempotencyKey);
        return;  // idempotent: silently skip duplicate
    }

    try {
        // Process the payment
        stripeClient.charge(event.getAmount(), event.getCardToken());
        paymentRepo.markPaid(event.getOrderId());

        // Mark as processed AFTER successful processing
        redis.setex("processed:" + idempotencyKey, 86400, "1"); // remember 24h
    } catch (Exception ex) {
        log.error("Payment failed: {}", ex.getMessage());
        throw ex; // re-throw → triggers retry
    }
}
```

```
Kafka Exactly-Once (Kafka Transactions) — for Kafka-to-Kafka:
  Producers can use transactions: produce + commit atomically
  Consumer: isolation.level = read_committed (skip uncommitted messages)
  Works for: Kafka → Kafka pipelines (transform and forward)
  Does NOT help: Kafka → external API (like Stripe) — still need idempotency key
```

---

## Scenario 3: Consumer Group Rebalancing Disruption

### The Problem
```
You have:
  Topic "orders": 6 partitions
  Consumer Group "inventory-service": 3 consumers (one per pod)
  Assignment: Consumer1→P0,P1 | Consumer2→P2,P3 | Consumer3→P4,P5

HPA scales up (traffic spike): adds Consumer4 pod.
Kafka triggers REBALANCING:
  ALL consumers PAUSE processing
  Kafka reassigns partitions: C1→P0 | C2→P1,P2 | C3→P3,P4 | C4→P5
  Rebalance takes 30-60 seconds
  
During rebalance: ZERO messages processed from "orders" topic.
30 seconds × 10,000 messages/second = 300,000 messages queued.
Recovery: 5-10 minutes to drain the backlog.

Every scale-up/down event causes this disruption.
```

### Fix: Cooperative (Incremental) Rebalancing
```java
// Old behavior: "STOP THE WORLD" rebalance (all partitions revoked at once)
// New behavior: cooperative rebalance (only the reassigned partitions pause)

spring:
  kafka:
    consumer:
      group-id: inventory-service
      properties:
        partition.assignment.strategy: >
          org.apache.kafka.clients.consumer.CooperativeStickyAssignor
        # Cooperative: only the moving partitions pause (not all consumers)
        # Sticky: tries to keep current assignments → minimal disruption
```

```
With CooperativeStickyAssignor:
  Adding Consumer4: only P5 is moved from C3 to C4
  C1, C2, C3 (for P0-P4) keep processing WITHOUT pausing
  Only P5 has a brief pause during handoff

Without it:
  ALL 6 partitions pause simultaneously for 30-60 seconds
```

---

## Kafka vs SQS vs RabbitMQ — Decision Matrix

```
CHOOSE KAFKA WHEN:
  ✅ Need to replay events (Kafka retains messages for days/weeks)
  ✅ Multiple independent consumers need same events
     (inventory + email + analytics all consuming "order-placed")
  ✅ Event sourcing / audit trail
  ✅ High throughput (millions of messages/sec)
  ✅ Ordered processing within a partition
  ✅ Stream processing (Kafka Streams, Flink)

CHOOSE SQS WHEN:
  ✅ Simple point-to-point queuing (one producer, one consumer)
  ✅ Serverless (Lambda consumers)
  ✅ Managed AWS service (no cluster to manage)
  ✅ Need visibility timeout (message hidden for 30s while processing)
  ✅ FIFO ordering with exactly-once for small scale (SQS FIFO)
  ❌ Multiple consumers of same message → use SNS+SQS fan-out instead

CHOOSE RABBITMQ WHEN:
  ✅ Complex routing (topic exchanges, direct exchanges, fanout)
  ✅ Priority queues (high priority messages processed first)
  ✅ RPC pattern (request-reply)
  ✅ Message TTL without consumer needed
  ❌ For high-scale event streaming → Kafka is better

NEVER USE:
  ❌ DB polling as a queue (SELECT * WHERE status='PENDING' → update)
      Kills DB with constant polling, doesn't scale
```

---

## Trap: Partition Key Causing Hot Partition

### The Problem
```
You chose orderType as partition key for Kafka topic "orders".
orderType has values: REGULAR (95%), EXPRESS (4%), SAME_DAY (1%)

Partition 0 (REGULAR): 950,000 messages/minute → single consumer overwhelmed
Partition 1 (EXPRESS):  40,000 messages/minute → moderate
Partition 2 (SAME_DAY): 10,000 messages/minute → light load

Partition 0's consumer is the bottleneck.
Adding more partitions for REGULAR helps, but requires rebalancing.
```

```
FIX: Choose a HIGH-CARDINALITY partition key.
  BAD key:  orderType (3 values → uneven distribution)
  BAD key:  city (100 values → Mumbai shard gets 30% of all orders)
  GOOD key: userId or orderId (millions of values → even distribution)
             hash(userId) distributes evenly across all partitions

Rule: partition key cardinality should be >> number of partitions
      If you have 100 partitions and 3 unique key values → guaranteed hot partitions
```

---

## Interview Cheat Sheet

> "Kafka is my default for async event streaming when I need multiple independent consumers (inventory, email, analytics all consuming the same 'order-placed' event), message replay for debugging, and high throughput. The partition key must be high-cardinality (userId/orderId not orderType) or you get hot partitions. Every consumer must be idempotent — Kafka is at-least-once by default, failures cause redelivery, and you'll get duplicate messages. Use a Redis NX set with the eventId as key to deduplicate. Poison pills (malformed messages) block a partition permanently without a DLQ strategy — configure DefaultErrorHandler with 3 retries and a DeadLetterPublishingRecoverer so bad messages park in a DLQ and processing continues. Use CooperativeStickyAssignor to prevent the 30-second 'stop the world' rebalance when pods scale up/down."
