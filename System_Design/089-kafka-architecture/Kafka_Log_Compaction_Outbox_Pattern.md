# Kafka Log Compaction and the Outbox Pattern
### Changelog Topics as Materialized Views — and Transactional Kafka Publish Without 2PC

---

## PART 1 — THE STUDENT CONVERSATION

### Log Compaction

Imagine you keep a notebook where you write price updates for stocks:

```
"price of APPLE = $150"
"price of GOOGLE = $2800"
"price of APPLE = $155"
"price of APPLE = $148"
"price of GOOGLE = $2810"
```

If someone only cares about the CURRENT price of APPLE, they only need the last entry — `$148`. Everything before it is history they don't need. Log compaction periodically "compacts" the notebook by keeping only the **latest value for each key** and discarding all older entries. The notebook is now smaller, but contains the same current state.

This is exactly what Kafka log compaction does. You can treat a compacted Kafka topic like a distributed key-value store. A new consumer reading from the beginning gets the current state of every key without replaying 5 years of updates.

### The Outbox Pattern

You work at a bank. You need to:
1. Update a customer's account balance in PostgreSQL.
2. Publish a `PaymentProcessed` event to Kafka so fraud detection can react.

The naive approach has a race condition:
- If you update the DB first, then crash before publishing to Kafka — fraud detection misses it.
- If you publish to Kafka first, then crash before updating the DB — the notification is a lie.

There's no atomic transaction that spans both PostgreSQL and Kafka without a distributed coordinator (2PC) — and 2PC is slow, complex, and you don't want it.

The solution: write **both** the balance update and the event payload to the database in **one transaction**. The event sits in an `outbox` table inside your DB. A separate process (Debezium CDC or a polling worker) reads the outbox and publishes to Kafka. Two operations, one transaction — atomicity guaranteed by your local DB, no distributed coordinator needed.

---

## PART 2 — LOG COMPACTION AND OUTBOX DIAGRAMS

### Log Compaction: Before and After

```
Partition log BEFORE compaction (key = product_id):
  Offset 0:  [product:42] price=100
  Offset 1:  [product:99] price=50
  Offset 2:  [product:42] price=105   <-- newer value for product:42
  Offset 3:  [product:42] price=108   <-- even newer value for product:42
  Offset 4:  [product:99] price=55    <-- newer value for product:99
  Offset 5:  [product:55] price=200   <-- brand new product, first entry

After compaction (retain only latest per key):
  Offset 3:  [product:42] price=108   <-- KEPT (latest for product:42)
  Offset 4:  [product:99] price=55    <-- KEPT (latest for product:99)
  Offset 5:  [product:55] price=200   <-- KEPT (only entry for product:55)

Offsets 0, 1, 2 are DELETED during compaction.

A new consumer reading from offset 0:
  Sees current state of ALL products without replaying 1000 historical updates.
  Compacted topic = eventually consistent distributed key-value store.
```

### Tombstone Records (Deletes)

```
To DELETE a key from the compacted log:
  Produce: key="product:42", value=null   <-- this is a tombstone record

During compaction:
  Kafka sees value=null --> marks this key for deletion
  After tombstone retention period (delete.retention.ms), key is fully purged

Use case: product discontinued --> send tombstone --> all consumers remove it from their local state
```

### Outbox Pattern: Dual-Write Problem vs Solution

```
WITHOUT Outbox (dual-write problem):
+---------------------------------------------+
|  Application                                |
|                                             |
|  BEGIN TRANSACTION                          |
|    UPDATE accounts                          |
|      SET balance=900 WHERE id=42            |
|  COMMIT                   <-- DB write OK   |
|                                             |
|  kafka.send(                                |
|    "payment-events",      <-- CRASH HERE?   |
|    paymentEvent           <-- Event LOST    |
|  )                                          |
+---------------------------------------------+
Result: Balance updated, fraud detection never notified.

WITH Outbox Pattern:
+---------------------------------------------+
|  Application                                |
|                                             |
|  BEGIN TRANSACTION                          |
|    UPDATE accounts                          |
|      SET balance=900 WHERE id=42            |
|    INSERT INTO outbox                       |
|      (id, topic, key, payload, status)      |
|      VALUES (                               |
|        uuid(), 'payment-events',            |
|        'acct:42',                           |
|        '{"id":42,"amount":100,"ts":...}',   |
|        'PENDING'                            |
|      )                                      |
|  COMMIT    <-- BOTH in one transaction [OK] |
+---------------------------------------------+

+---------------------------------------------+
|  Debezium CDC (separate process)            |
|                                             |
|  Reads PostgreSQL WAL (Write-Ahead Log)     |
|  Detects INSERT on outbox table             |
|  Publishes to Kafka: topic=payment-events   |
|  Tracks WAL offset (LSN)                    |
|                                             |
|  If crash after DB commit, before publish:  |
|    Debezium replays from last committed LSN |
|    Re-publishes event --> at-least-once [OK]|
+---------------------------------------------+
```

### Full Outbox Data Flow

```
PostgreSQL                    Debezium                     Kafka
    |                             |                           |
    |  INSERT outbox row          |                           |
    |<----------------------------|                           |
    |                             |                           |
    |  WAL: outbox INSERT event   |                           |
    |----------------------------->                           |
    |                             |  kafka.send(             |
    |                             |    topic, key, payload)  |
    |                             |-------------------------->|
    |                             |                           |
    |                             |  Commit WAL offset (LSN) |
    |                             |  (stored in Kafka or DB) |
    |                             |                           |

Consumer side:
  Kafka --> Consumer --> process event --> deduplicate by event_id
                                       (at-least-once delivery, idempotent consumer)
```

---

## PART 3 — INTERNALS: CONFIGS, CODE, AND REAL NUMBERS

### Log Compaction Configuration

```bash
# Create a compacted topic
kafka-topics.sh --create \
  --topic product-catalog \
  --partitions 12 \
  --replication-factor 3 \
  --config cleanup.policy=compact \
  --config min.cleanable.dirty.ratio=0.1 \
  --config segment.ms=3600000 \
  --config delete.retention.ms=86400000 \
  --bootstrap-server broker:9092

# cleanup.policy=compact        Only keep latest value per key
# min.cleanable.dirty.ratio=0.1 Start compaction when 10% of log is dirty (new vs compacted)
# segment.ms=3600000            Roll a new segment every hour (compaction works on closed segments)
# delete.retention.ms=86400000  Keep tombstones for 24h before hard deletion
```

### Log Compaction: Mixed Policy (Retain + Compact)

```bash
# For audit/changelog topics: keep history AND compact
--config cleanup.policy=compact,delete \
--config retention.ms=2592000000 \    # keep 30 days of history
--config min.cleanable.dirty.ratio=0.5
```

### Outbox Table Schema (PostgreSQL)

```sql
CREATE TABLE outbox (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    topic        VARCHAR(255) NOT NULL,
    partition_key VARCHAR(255),                -- maps to Kafka partition key
    event_type   VARCHAR(255) NOT NULL,
    payload      JSONB NOT NULL,
    status       VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    processed_at TIMESTAMPTZ,
    error        TEXT
);

CREATE INDEX idx_outbox_status_created ON outbox(status, created_at)
  WHERE status = 'PENDING';   -- partial index for polling queries
```

### Polling Outbox Worker (Simpler, but Polling Interval = Latency)

```java
@Service
public class OutboxRelayService {

    @Scheduled(fixedDelay = 500)   // poll every 500ms
    @Transactional
    public void processOutbox() {
        List<OutboxEvent> events = outboxRepository
            .findTop100ByStatusOrderByCreatedAt("PENDING");

        for (OutboxEvent event : events) {
            try {
                ProducerRecord<String, String> record =
                    new ProducerRecord<>(event.getTopic(), event.getPartitionKey(), event.getPayload());
                kafkaTemplate.send(record).get(5, TimeUnit.SECONDS);   // sync send
                event.setStatus("PROCESSED");
                event.setProcessedAt(Instant.now());
            } catch (Exception e) {
                event.setStatus("FAILED");
                event.setError(e.getMessage());
                log.error("Outbox relay failed for event {}", event.getId(), e);
            }
            outboxRepository.save(event);
        }
    }
}
```

### Debezium CDC Outbox (Better: Zero Polling, WAL-Based, Near Real-Time)

```json
// Debezium PostgreSQL source connector config
{
  "name": "outbox-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "debezium",
    "database.dbname": "payments",
    "database.server.name": "payments-db",
    "table.include.list": "public.outbox",
    "plugin.name": "pgoutput",

    "transforms": "outbox",
    "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter",
    "transforms.outbox.table.field.event.id": "id",
    "transforms.outbox.table.field.event.key": "partition_key",
    "transforms.outbox.table.field.event.payload": "payload",
    "transforms.outbox.route.by.field": "topic",
    "transforms.outbox.route.topic.replacement": "${routedByValue}"
  }
}
```

### Consumer: Idempotent Event Processing

```java
@KafkaListener(topics = "payment-events")
@Transactional
public void handlePaymentEvent(ConsumerRecord<String, String> record) {
    PaymentEvent event = objectMapper.readValue(record.value(), PaymentEvent.class);

    // Idempotency check: skip if already processed
    if (processedEventRepo.existsById(event.getId())) {
        log.info("Duplicate event {}, skipping", event.getId());
        return;
    }

    // Process event
    fraudDetectionService.analyze(event);

    // Mark as processed (in same transaction as any DB writes)
    processedEventRepo.save(new ProcessedEvent(event.getId(), Instant.now()));
}
```

### Real-World Numbers

```
Compacted topic stats (product catalog, 10M products):
  Un-compacted: 10M events x 1KB avg = ~10GB
  Post-compaction: 10M keys x 1KB latest = ~10GB  (same, but no historical bloat)
  After 1 year without compaction: 10M events/day x 365 = 3.65 billion events = ~3.6TB
  With compaction: stays ~10GB regardless of time

Outbox polling latency:
  500ms poll interval = average 250ms additional latency per event
  Acceptable for async notifications; not acceptable for real-time fraud detection

Debezium CDC latency:
  WAL event -> Kafka: typically 50-200ms under normal load
  Much lower than polling, near real-time
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer**: Your e-commerce platform needs to update order status in PostgreSQL and publish an `OrderStatusChanged` event to Kafka — atomically. You can't use distributed transactions (2PC). How do you do it?

**You**: I'd use the Outbox Pattern. In the same PostgreSQL transaction that updates the order status, I insert a row into an `outbox` table containing the event type, partition key, and serialized payload. That transaction either commits both the order update and the outbox row together, or rolls back both. Local DB atomicity — no 2PC needed.

**Interviewer**: Then what? How does the event get to Kafka?

**You**: A CDC process — Debezium in production — watches the PostgreSQL WAL for new outbox rows and publishes them to Kafka. Debezium tracks its position in the WAL. If it crashes between reading and publishing, it replays from the last committed WAL offset and republishes the event. That gives us at-least-once delivery — the consumer must be idempotent. I put an `event_id` UUID in the payload; the consumer checks a `processed_events` table before acting.

**Interviewer**: Why not just do the DB update and Kafka publish in a try-catch, and log failures?

**You**: That's dual-write, and it has a fundamental race condition. After `COMMIT`, the process can crash before `kafka.send()` — that's not catchable. Even if you retry, you'd need to know which committed DB rows haven't been sent to Kafka yet — and that requires queryable state, which is exactly what the outbox table provides. Dual-write also doesn't help if Kafka is temporarily unavailable. The outbox table acts as a durable buffer: events accumulate there and drain to Kafka when it's healthy.

**Interviewer**: What's the difference between log compaction and a regular Kafka topic?

**You**: Regular topics use time-based or size-based retention — old messages are deleted after, say, 7 days regardless of whether newer values for the same key exist. Log compaction retains the latest value per key indefinitely. A new consumer reading from offset 0 on a compacted topic gets the current state of every key — like a full snapshot. We use this for product catalog topics. Rather than every new order service reading 5 years of price updates, it reads the compacted topic once and gets current prices. The compacted topic behaves like a distributed key-value store backed by Kafka's fault tolerance.

---

## PART 5 — DECISION FRAMEWORK

### Log Compaction vs Regular Topic

| Dimension | Regular (delete) | Compacted | Mixed (compact + delete) |
|---|---|---|---|
| Retention behavior | Deletes old messages by time/size | Keeps latest per key indefinitely | Keeps history for N days + latest per key |
| Use case | Event streams (orders, clicks) | State snapshots (prices, user profiles) | Audit + current state |
| Consumer restart | Must replay from last offset | Reads current state from offset 0 | Can replay recent history |
| Storage growth | Bounded by retention window | Bounded by number of unique keys | Bounded by both |
| Example topics | `order-events` | `product-prices` | `account-balance-changelog` |

### Outbox vs Dual-Write vs Saga

| Approach | Atomicity | Complexity | Data Loss Risk | Use When |
|---|---|---|---|---|
| Dual-write (try/catch) | No | Low | Yes (crash window) | Never for critical events |
| Outbox (polling) | Yes | Medium | None | Small teams, acceptable latency (500ms+) |
| Outbox (Debezium CDC) | Yes | Medium-High | None | Production. Near real-time. Recommended. |
| Saga (choreography) | Eventual | High | No loss, but complex rollback | Multi-service transactions |
| 2PC (XA) | Strong | Very High | No loss | Avoid in distributed systems |

---

## QUICK REFERENCE CARD

```
LOG COMPACTION:
  cleanup.policy=compact               Enable log compaction for topic
  min.cleanable.dirty.ratio=0.1        Compact when 10% of log is new/dirty
  segment.ms=3600000                   Roll segments every hour
  delete.retention.ms=86400000         Keep tombstones 24h before purge
  Tombstone = key with null value      Signals deletion of a key

OUTBOX PATTERN:
  Step 1: BEGIN TRANSACTION
  Step 2:   DB update (e.g., UPDATE orders SET status='SHIPPED')
  Step 3:   INSERT INTO outbox(topic, key, payload, status='PENDING')
  Step 4: COMMIT  <-- atomic: both or neither
  Step 5: Debezium reads WAL --> publishes to Kafka --> at-least-once
  Step 6: Consumer deduplicates by event_id (idempotent)

DEBEZIUM SETUP:
  Plugin: io.debezium.transforms.outbox.EventRouter (SMT)
  Routes outbox.topic column --> Kafka topic name
  Routes outbox.partition_key --> Kafka message key
  Routes outbox.payload --> Kafka message value

WHEN TO USE:
  Log compaction: product catalog, user profiles, account state, feature flags
  Outbox: any service that must write to DB AND publish to Kafka atomically
  Both together: stateful topics where you need current state + new events
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

| System | Pattern Used | Why |
|---|---|---|
| **03 Notification System** | Outbox (Debezium) | Write notification event to outbox in same transaction as user action. No partial failures. Debezium streams to Kafka. |
| **07 Payment System** | Outbox + Compacted topic | Balance update + event publish in one DB transaction. Compacted topic `account-state` holds current balance per account_id — new consumers get current snapshot without replaying all transactions. |
| **09 E-Commerce** | Compacted `product-catalog` + Outbox for orders | Product price/stock updates compact to current state. Order service consumers never replay 5 years of catalog history. Outbox ensures order events reach downstream without dual-write risk. |
| **19 Stock Broker** | Compacted `position-state` + Outbox for trades | Current position per trader stored in compacted topic. New portfolio service consumer reads current state in seconds. Trade events published via outbox — atomic with DB update, no lost trades. |
| **04 WhatsApp Chat** | Outbox for message delivery receipts | Message stored in Cassandra + outbox in same transaction. CDC publishes to Kafka for delivery tracking pipeline. Guarantees no delivery event is silently dropped. |

---

> **Architect one-liner**: "Log compaction keeps only the latest value per key — making a Kafka topic a distributed key-value store. The Outbox Pattern uses a local DB transaction to guarantee atomic DB-write + Kafka-publish without 2PC."
