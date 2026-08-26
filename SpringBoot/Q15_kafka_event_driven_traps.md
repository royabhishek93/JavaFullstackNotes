# Q15: Spring Kafka & Event-Driven — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 25-30 minutes | **Frequency:** Every microservices/architect round 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "We had a message that threw a NullPointerException. Kafka kept retrying it forever. It clogged the entire consumer. All order processing stopped for 6 hours." — The Poison Pill incident.

---

## Kafka Core Concepts (Quick Architect Recap)

```
Topic: "orders"
  ├── Partition 0: [msg1, msg2, msg5, msg8]  ← ordered within partition
  ├── Partition 1: [msg3, msg6, msg9]
  └── Partition 2: [msg4, msg7, msg10]

Consumer Group: "order-service"
  ├── Pod A: assigned Partition 0
  ├── Pod B: assigned Partition 1
  └── Pod C: assigned Partition 2

Key guarantee: messages with same key → same partition → in-order processing
               messages across partitions → NO ordering guarantee
```

---

## Scenario 1: Poison Pill Message (Most Common Production Incident)

### The Incident
```
Order #12345 has null customerId (data bug in upstream service).
Consumer reads it → NullPointerException in handler.
Spring Kafka retries it 3 times → still fails.
Consumer seeks back to that offset → retries → fails → infinite loop.
No other messages in that partition are processed.
Orders pile up → customers don't get confirmations → revenue impact.
```

### Wrong Setup (Default Retry = Poison Pill Factory)
```java
@KafkaListener(topics = "orders", groupId = "order-service")
public void handleOrder(Order order) {
    // Throws NullPointerException if order.getCustomerId() is null
    Customer customer = customerService.findById(order.getCustomerId());
    processOrder(order, customer);
}
// No error handler → infinite retry → partition blocked
```

### Production Fix: Dead Letter Topic (DLT)
```java
@Configuration
public class KafkaConfig {

    @Bean
    public DefaultErrorHandler errorHandler(KafkaOperations<?, ?> kafkaTemplate) {
        // Dead letter publisher — sends failed messages to "orders-dlt" topic
        DeadLetterPublishingRecoverer recoverer =
            new DeadLetterPublishingRecoverer(kafkaTemplate,
                (record, ex) -> new TopicPartition(
                    record.topic() + "-dlt",   // "orders-dlt"
                    record.partition()          // same partition for ordering
                ));

        // Retry 3 times with exponential backoff, then send to DLT
        ExponentialBackOffWithMaxRetries backOff = new ExponentialBackOffWithMaxRetries(3);
        backOff.setInitialInterval(1000L);   // 1s
        backOff.setMultiplier(2.0);          // 1s, 2s, 4s
        backOff.setMaxInterval(10000L);      // cap at 10s

        DefaultErrorHandler handler = new DefaultErrorHandler(recoverer, backOff);

        // Don't retry on these — they'll never succeed (programming errors)
        handler.addNotRetryableExceptions(
            NullPointerException.class,
            ClassCastException.class,
            DeserializationException.class
        );

        return handler;
    }
}

@KafkaListener(topics = "orders", groupId = "order-service",
               errorHandler = "kafkaErrorHandler")
public void handleOrder(@Payload Order order,
                        @Header(KafkaHeaders.RECEIVED_KEY) String key) {
    processOrder(order);
}

// Separate consumer for DLT — alerting + manual review
@KafkaListener(topics = "orders-dlt", groupId = "order-dlt-monitor")
public void handleDltOrder(@Payload byte[] message,
                           @Header(KafkaHeaders.EXCEPTION_MESSAGE) String exMsg) {
    log.error("DLT message received. Error: {}", exMsg);
    alertingService.notifyOncall("Poison pill in orders topic: " + exMsg);
    // Store for manual reprocessing after fix
    dltRepo.save(new DeadLetterRecord(message, exMsg, Instant.now()));
}
```

---

## Scenario 2: Idempotent Consumer (At-Least-Once = Duplicate Messages)

### The Problem
```
Kafka guarantees at-least-once delivery by default.
Consumer crashes AFTER processing but BEFORE committing offset.
On restart, Kafka re-delivers the same message.
Result: order processed twice → double charge!

Message delivered: msg#100 (orderId=5678, amount=$99)
Consumer: processes payment → charges card ✅
Consumer: crashes before offset commit
Kafka: replays msg#100 on restart
Consumer: processes payment AGAIN → charges card AGAIN ❌
```

### Fix: Idempotency Key
```java
@KafkaListener(topics = "orders", groupId = "order-service")
public void handleOrder(@Payload OrderCreatedEvent event) {

    // Idempotency check BEFORE processing
    String idempotencyKey = "processed:order:" + event.getOrderId();

    // Redis SET NX (set if not exists) — atomic check-and-set
    Boolean isNew = redis.opsForValue().setIfAbsent(
        idempotencyKey, "1", 24, TimeUnit.HOURS
    );

    if (Boolean.FALSE.equals(isNew)) {
        log.info("Duplicate message for orderId={}, skipping", event.getOrderId());
        return;  // already processed — skip safely
    }

    try {
        processOrder(event);
    } catch (Exception ex) {
        // Processing failed — remove idempotency key so retry can reprocess
        redis.delete(idempotencyKey);
        throw ex;
    }
}
```

### Database-Level Idempotency (More Durable)
```java
@Transactional
public void processOrder(OrderCreatedEvent event) {
    // Unique constraint on event_id in processed_events table
    if (processedEventRepo.existsByEventId(event.getEventId())) {
        return; // duplicate
    }
    processedEventRepo.save(new ProcessedEvent(event.getEventId(), Instant.now()));
    // ... actual business logic ...
}
// If duplicate comes in → unique constraint violation → transaction rolls back → harmless
```

---

## Scenario 3: Consumer Rebalance Storm

### The Problem
```
Consumer Group has 6 pods, each processing messages.
One pod is slow (GC pause, DB slow query).
Kafka thinks it's dead (heartbeat timeout).
Kafka triggers REBALANCE — stops ALL consumers while reassigning partitions.
All 6 pods stop processing during rebalance (~30s).
Rebalance completes → slow pod still slow → GC pause → heartbeat miss → rebalance AGAIN.
Infinite rebalance storm → no messages processed for minutes.
```

### Fix: Tune Heartbeat and Max Poll Settings
```yaml
spring:
  kafka:
    consumer:
      # How often consumer sends heartbeat to Kafka broker
      properties:
        heartbeat.interval.ms: 3000         # send heartbeat every 3s
        session.timeout.ms: 45000           # Kafka considers dead after 45s
        max.poll.interval.ms: 300000        # max time between poll() calls (5 min)
        # Trap: max.poll.interval.ms must be > time to process a batch!
        # If your DB call takes 10s and you poll 500 msgs at a time → 5000s > 5min
        # → Kafka thinks consumer is dead → rebalance
        max.poll.records: 50               # reduce batch size if processing is slow
```

```java
// Also: Use Static Group Membership to avoid rebalance on rolling restart
@Bean
public ConsumerFactory<String, Object> consumerFactory() {
    Map<String, Object> config = new HashMap<>();
    config.put(ConsumerConfig.GROUP_INSTANCE_ID_CONFIG, "pod-" + podId);
    // Static member: Kafka waits session.timeout.ms before reassigning
    // Rolling restart: pod comes back with same ID → no rebalance needed
    return new DefaultKafkaConsumerFactory<>(config);
}
```

---

## Trap 1: @KafkaListener + @Transactional (Offset Committed Before TX Commits)

### The Bug
```java
@KafkaListener(topics = "orders")
@Transactional   // ❌ TRAP: Kafka offset commit and DB transaction are separate!
public void handleOrder(Order order) {
    orderRepo.save(order);
    // DB transaction commits ✅
    // Kafka offset committed ✅ (by Spring, independent of DB TX)

    // Now: what if DB TX fails AFTER Kafka offset commit?
    // Kafka thinks message was processed (offset committed)
    // DB has no record
    // Message is LOST — never reprocessed
}
```

### The Real Problem: Two-Phase Commit
```
Option 1: Exactly-once with Kafka transactions (complex, performance cost)
Option 2: Transactional Outbox pattern (most practical for microservices)
Option 3: Idempotent consumer + at-least-once (recommended)
```

### Fix: Separate Kafka Ack from DB Transaction
```java
@KafkaListener(topics = "orders")
public void handleOrder(ConsumerRecord<String, Order> record,
                        Acknowledgment ack) {
    try {
        // DB operation in its own transaction
        orderService.saveOrderTransactionally(record.value());
        // Only ack AFTER successful DB write
        ack.acknowledge();
    } catch (Exception ex) {
        log.error("Failed to process order, will retry: {}", ex.getMessage());
        // Don't ack → Kafka will redeliver
        // But set nack with backoff to avoid tight retry loop
        ack.nack(Duration.ofSeconds(10));
    }
}
```

```yaml
spring:
  kafka:
    listener:
      ack-mode: MANUAL_IMMEDIATE  # manual acknowledgment mode
```

---

## Trap 2: Message Ordering — Partition Key Is Everything

### The Bug
```java
// You want all operations for an order to be processed in order:
// CREATE → UPDATE → CANCEL
// Without partition key, messages spread across partitions randomly:
//   CREATE  → Partition 1 (Consumer A)
//   UPDATE  → Partition 2 (Consumer B) ← processes BEFORE Consumer A gets CREATE!
//   CANCEL  → Partition 0 (Consumer C)
// Consumer B tries to UPDATE an order that doesn't exist yet → error
```

### Fix: Use OrderId as Partition Key
```java
@Service
public class OrderEventPublisher {

    public void publishOrderEvent(OrderEvent event) {
        kafkaTemplate.send(
            "orders",
            event.getOrderId().toString(),  // KEY = orderId → same partition always
            event
        );
        // All events for order #123 → always go to the same partition
        // → processed by the same consumer in order ✅
    }
}
```

### Partition Count vs Consumers
```
Rule: partitions >= consumer instances
      (more consumers than partitions = idle consumers)

Scaling: you can only scale to partition count
         e.g., 12 partitions = max 12 parallel consumers
         To scale further: increase partition count (non-trivial in production!)
         Always start with more partitions than you think you need.
```

---

## Trap 3: Deserialisation Failure Blocks Partition

### The Bug
```java
// Producer sends: { "orderId": 123, "amount": 99.99 }
// Schema changes: producer now sends { "orderId": 123, "amount": 99.99, "currency": "USD" }
// If consumer has no 'currency' field: depends on Jackson config
//   DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES = true  → JsonMappingException
//   → Consumer retries forever → partition blocked
```

### Fix
```java
// Option 1: Jackson config — ignore unknown fields
@Bean
public ObjectMapper kafkaObjectMapper() {
    return new ObjectMapper()
        .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false); // ✅
}

// Option 2: Use Schema Registry (Avro/Protobuf) with schema evolution rules
// Option 3: Consume as byte[] or JsonNode, parse manually with validation

// Option 4: Mark DeserializationException as non-retryable
handler.addNotRetryableExceptions(DeserializationException.class);
// → Immediately goes to DLT, doesn't block partition
```

---

## Advanced Scenario: Transactional Outbox Pattern

### The Problem (Dual Write)
```java
// WRONG ❌ — Two separate writes, no atomicity
@Transactional
public void placeOrder(OrderRequest req) {
    Order order = orderRepo.save(new Order(req));   // DB write ✅
    kafkaTemplate.send("orders", new OrderCreatedEvent(order)); // Kafka write
    // What if Kafka send fails? DB has the order, event never sent.
    // What if process crashes after DB save but before Kafka send?
    // → Downstream services never know the order was placed
}
```

### Fix: Transactional Outbox
```java
// Step 1: Save event to outbox table in SAME DB transaction
@Transactional
public void placeOrder(OrderRequest req) {
    Order order = orderRepo.save(new Order(req));

    // Save event to outbox — SAME transaction, atomic
    OutboxEvent event = OutboxEvent.builder()
        .aggregateId(order.getId().toString())
        .eventType("ORDER_CREATED")
        .payload(objectMapper.writeValueAsString(new OrderCreatedEvent(order)))
        .createdAt(Instant.now())
        .build();
    outboxRepo.save(event);  // if this TX rolls back, event is not saved either
}

// Step 2: Background poller reads outbox and publishes to Kafka
@Scheduled(fixedDelay = 1000)  // every 1 second
@Transactional
public void pollOutbox() {
    List<OutboxEvent> unpublished = outboxRepo.findByPublishedFalseOrderByCreatedAtAsc();
    for (OutboxEvent event : unpublished) {
        kafkaTemplate.send("orders", event.getAggregateId(), event.getPayload());
        event.setPublished(true);
        outboxRepo.save(event);
    }
}
```

```
Guarantee: Either both DB record AND outbox event are saved (committed together)
           OR neither (transaction rolled back).
           Kafka publish is eventually consistent but guaranteed — outbox won't disappear.
```

---

## Quick Reference: Kafka Guarantees

| Config | Guarantee | Use Case |
|---|---|---|
| `acks=0` | Fire and forget | Metrics, logs (loss OK) |
| `acks=1` | Leader acked | Default, some loss on leader failure |
| `acks=all` + `min.insync.replicas=2` | Strong durability | Financial, orders |
| `enable.idempotence=true` | No duplicates in producer | Combined with acks=all |
| Manual ack + idempotent consumer | At-least-once + safe | Most microservices |
| Kafka Transactions | Exactly-once | Complex, use Outbox instead |

---

## Interview Cheat Sheet

> "The two biggest Kafka production issues I've dealt with: poison pill messages blocking partitions indefinitely, and offset commit/DB transaction misalignment causing data loss or duplication. For poison pills: configure `DefaultErrorHandler` with exponential backoff and a Dead Letter Topic — non-retryable exceptions (NPE, deserialization errors) go directly to DLT. For dual-write reliability: Transactional Outbox pattern — save the event to an outbox table in the same DB transaction, then a background poller publishes to Kafka. For exactly-once semantics without Kafka transactions, idempotent consumers with a processed-events table or Redis NX gives you at-least-once delivery with safe deduplication. Always set partition key = aggregate ID to preserve ordering."
