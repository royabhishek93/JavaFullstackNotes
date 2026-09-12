# Kafka Failure Scenarios — Debug and Recovery
### Producer Failures, Broker Crashes, Consumer Crashes — With Production Debugging

---

## HOW TO USE THIS FILE

Read each scenario out loud before your interview. Each section has:
- What actually happens internally (not textbook, what the code does)
- ASCII flow diagram of the failure path
- Production app example (Swiggy order service, Flipkart inventory)
- Exact debug commands and metrics to check
- Recovery steps

---

## BIG PICTURE — The Kafka Data Flow

```
NORMAL HAPPY PATH:
────────────────────────────────────────────────────────────────────

  [Producer]          [Broker Cluster]              [Consumer]
  Order Service  ──►  Partition Leader  ──►  ISR Followers
                            │                         │
                       writes to log            replicates
                            │
                     Consumer polls ◄── Consumer Group (Order Worker)
                            │
                       processes message
                            │
                       commits offset

  Each step can fail. Let's go through each one.
```

---

## SCENARIO 1 — PRODUCER FAILS TO SEND TO BROKER

### What actually happens internally

```
producer.send(orderRecord) is called:
────────────────────────────────────────────────────────────────────

  Step 1: Message enters RecordAccumulator (in-memory ring buffer)
  ┌────────────────────────────────────────────────────────────────┐
  │  RecordAccumulator (default 32MB)                              │
  │  batch for partition 0: [msg1, msg2, msg3]  ← your message here│
  │  batch for partition 1: [msg4, msg5]                           │
  └────────────────────────────────────────────────────────────────┘

  Step 2: Sender thread wakes up (linger.ms elapsed or batch full)
  Sender: "I'll send batch to broker 3 (leader of partition 0)"
  
  Step 3: Network call to broker
  → FAILURE: TimeoutException / NetworkException / NotLeaderException

  Step 4: What happens?
  ┌─────────────────────────────────┐
  │  retries > 0?                   │
  │  YES → wait retry.backoff.ms    │
  │        → retry (up to retries)  │
  │  NO  → message DROPPED          │
  │        → callback fires with    │
  │          exception              │
  └─────────────────────────────────┘

  Step 5: If delivery.timeout.ms exceeded (default 2 min):
  Message DROPPED regardless of retries remaining.
  RecordAccumulator clears the batch.
  Your data is GONE unless you handle the callback.
```

### Production example: Swiggy Order Service

```
Scenario: Swiggy's order-service sends "OrderPlaced" event to Kafka.
Broker 2 (leader of orders partition 3) goes down for 30 seconds.
────────────────────────────────────────────────────────────────────

  Without proper config:
  acks=1, retries=3, retry.backoff.ms=100
  → 3 retries × 100ms = 300ms total retry window
  → Broker is down for 30s
  → Message dropped after 300ms
  → Order placed in DB but no downstream processing
  → Inventory not reserved, restaurant not notified
  → Customer sees "order confirmed" but kitchen never knows

  With proper config:
  acks=all
  retries=Integer.MAX_VALUE
  delivery.timeout.ms=120000  (2 minutes)
  enable.idempotence=true
  → Kafka retries for up to 2 minutes
  → Broker recovers in 30s, new leader elected
  → Message delivered successfully, no data loss
```

### The acks setting — this determines data loss risk

```
acks=0:  Producer sends and FORGETS. No ACK waited.
         → Fastest. Maximum data loss. Use for: metrics, logs you can afford to lose.

acks=1:  Leader writes to its log → sends ACK → replicates to followers.
         → Leader crashes AFTER ACK but BEFORE replication → DATA LOST.
         → Use for: high-throughput non-critical events.

acks=all: Leader writes → ALL ISR followers confirm → ACK sent.
(acks=-1) → Broker crashes after ACK impossible unless all ISR crash simultaneously.
         → Safest. Use for: financial transactions, order events, inventory updates.

         GOTCHA: if ISR = [leader only] (followers lagging),
         acks=all effectively becomes acks=1!
         Set min.insync.replicas=2 to refuse writes if ISR < 2.
         This forces a choice: either 2+ replicas confirmed, or fail the write.
```

### Java config for production

```java
Properties props = new Properties();
props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, "broker1:9092,broker2:9092,broker3:9092");
props.put(ProducerConfig.ACKS_CONFIG, "all");                        // wait for all ISR
props.put(ProducerConfig.RETRIES_CONFIG, Integer.MAX_VALUE);          // retry forever
props.put(ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG, 120000);         // give up after 2 min
props.put(ProducerConfig.RETRY_BACKOFF_MS_CONFIG, 100);               // 100ms between retries
props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);            // no duplicates on retry
props.put(ProducerConfig.MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION, 5);   // safe with idempotence
props.put(ProducerConfig.LINGER_MS_CONFIG, 5);                        // batch for 5ms
props.put(ProducerConfig.BATCH_SIZE_CONFIG, 16384);                   // 16KB batch size

// ALWAYS use callback to detect failures
producer.send(record, (metadata, exception) -> {
    if (exception != null) {
        log.error("FAILED to send order event: topic={}, key={}, error={}",
                  record.topic(), record.key(), exception.getMessage());
        // Push to fallback: DB outbox table, retry queue, alerting
        fallbackOutbox.save(record);
    } else {
        log.debug("Sent: partition={}, offset={}", metadata.partition(), metadata.offset());
    }
});
```

### How to debug producer failures

```bash
# 1. Check if broker is reachable
kafka-broker-api-versions.sh --bootstrap-server broker1:9092

# 2. Check topic partition leaders
kafka-topics.sh --describe --topic orders --bootstrap-server broker1:9092
# Look for: Leader: none (means no leader elected yet)
# Look for: Isr: only 1 replica (min.insync.replicas violation risk)

# 3. Producer JMX metrics to monitor
# record-error-rate       → errors per second (should be 0)
# record-retry-rate       → retries per second (should be near 0)
# request-latency-avg     → avg time to get ACK from broker
# buffer-available-bytes  → how much RecordAccumulator space left
#                           (if 0: producer is backing up, send() will block)

# 4. In Spring Boot: expose via Micrometer
management.metrics.enable.kafka=true
# Then check: kafka.producer.record-error-total in Prometheus/CloudWatch
```

---

## SCENARIO 2 — BROKER CRASHES WHILE PRODUCER IS WRITING

### What happens inside the broker on crash

```
Timeline of a broker crash:
────────────────────────────────────────────────────────────────────

  T=0ms:   Producer sends batch to Leader (Broker 2, partition 0)
  T=5ms:   Leader writes to its log segment file
  T=8ms:   Leader starts replicating to Follower (Broker 3, Broker 4)
  T=10ms:  Broker 2 CRASHES (power loss, OOM kill, JVM crash)

  What happens to the in-flight message?

  Case A: acks=1
  ─────────────────────────────────────────────────────────────────
  Broker 2 sent ACK at T=6ms (before replication at T=8ms).
  Producer: "got ACK, message delivered" ← believes success
  Broker 3 and 4: never received the message (crash before replication)
  New leader elected from ISR: Broker 3 or 4
  New leader's log: message DOES NOT EXIST
  Message LOST. Producer doesn't know.

  Case B: acks=all
  ─────────────────────────────────────────────────────────────────
  Broker 2 crashed before ALL ISR confirmed → ACK never sent
  Producer: "no ACK, retrying..."
  Controller: detects Broker 2 gone (ZooKeeper session expired / KRaft heartbeat missed)
  Controller: elects Broker 3 as new leader
  Follower Broker 3: had replicated up to T=8ms — message IS there (if crash at T=10ms)
  Producer: retries → hits new leader Broker 3 → success

  Case C: acks=all + broker crashes before any replication
  ─────────────────────────────────────────────────────────────────
  Producer: retries → new leader doesn't have message → writes fresh
  enable.idempotence=true: sequence numbers prevent duplicate if original did arrive
  No data loss with idempotent producer.
```

### The ISR shrink danger

```
Normal ISR: [Broker1, Broker2, Broker3]
acks=all → waits for all 3 to confirm → safe

Slow follower scenario:
  Broker3 is GC-paused for 15 seconds
  replica.lag.time.max.ms=10000 (10s default)
  → Broker3 removed from ISR after 10s of lag

  New ISR: [Broker1, Broker2]
  acks=all still works (waits for 2)

  Broker2 crashes:
  New ISR: [Broker1]
  acks=all effectively = acks=1 (only 1 in ISR)

  Protection: min.insync.replicas=2 on the topic
  → If ISR < 2, broker REFUSES writes with NotEnoughReplicasException
  → Producer gets error, can handle it (store to outbox, alert)
  → Better: explicit failure than silent data loss
```

### Leader election timing

```
Broker crash → how long is partition unavailable?
────────────────────────────────────────────────────────────────────

  ZooKeeper mode (Kafka < 3.x):
  1. Broker's ZooKeeper session expires (zookeeper.session.timeout.ms = 18000ms = 18s)
  2. Controller detects broker gone
  3. Controller reads ISR, elects new leader
  4. Controller updates ZooKeeper with new leader
  5. All brokers refresh metadata
  Total: ~20-30 seconds of partition unavailability

  KRaft mode (Kafka 3.x):
  1. Raft heartbeat missed (faster detection)
  2. Controller election via Raft consensus
  Total: ~6-10 seconds (configurable lower)

  Your producer: gets LeaderNotAvailableException
  With retries=MAX_VALUE and delivery.timeout.ms=120s:
  → Kafka client retries during the 20-30s election window
  → No data loss, just latency spike
  → Requests queue up in RecordAccumulator during election
```

### How to debug broker crashes

```bash
# 1. Check under-replicated partitions (MOST IMPORTANT broker health metric)
kafka-topics.sh --describe --under-replicated-partitions --bootstrap-server broker1:9092
# Output: any partition where ISR < replication factor
# Should be 0 in healthy cluster. > 0 = alert immediately.

# 2. Check controller
kafka-metadata-quorum.sh --describe --bootstrap-server broker1:9092  # KRaft
# OR for ZooKeeper: check ActiveControllerCount JMX metric

# 3. Find which broker is missing
kafka-broker-api-versions.sh --bootstrap-server broker1:9092,broker2:9092,broker3:9092
# If one fails to respond: that broker is down

# 4. Key JMX metrics to alert on
# kafka.server:UnderReplicatedPartitions > 0     → ISR shrinking, broker may be down
# kafka.controller:ActiveControllerCount = 0     → no controller! severe
# kafka.server:OfflinePartitionsCount > 0        → no leader for some partitions
# kafka.server:UnderMinIsrPartitionCount > 0     → writes being refused

# 5. Check broker logs for crash reason
grep "ERROR\|FATAL\|OutOfMemory\|GC overhead" /var/log/kafka/server.log | tail -50
```

### Production example: Flipkart Flash Sale

```
Scenario: During Big Billion Days, Broker 4 OOM-killed by OS
(heap too small, JVM allocation failure during traffic spike).

Impact without preparation:
  Partitions 12-15 lose their leader.
  ~25% of inventory update events can't be written for 30 seconds.
  Sellers see "order processing delayed" errors.

With proper setup:
  min.insync.replicas=2: producers get NotEnoughReplicasException
  → fallback to Outbox pattern: write to DB outbox table
  → CDC (Debezium) picks up from outbox and re-publishes when broker recovers
  Replication factor=3: Broker 4 crash doesn't lose data
  Heap alert at 80%: ops team increases heap before flash sale

Recovery:
  Restart Broker 4 with -Xmx8g instead of -Xmx4g
  Partition leaders redistribute automatically
  Outbox events published: no data loss
```

---

## SCENARIO 3 — BROKER SIDE: CONSUMER CAN'T READ

### The critical insight: Kafka is PULL-based

```
MySQL / RabbitMQ style (PUSH):
  Broker: "here's your message" → pushes to consumer
  If consumer is down: message is lost or bounced

Kafka (PULL):
  Consumer: "give me messages from offset 500" → polls broker
  Broker: serves from log
  Consumer down: broker does nothing. Message sits in log.
  Consumer restarts: polls from last committed offset. No loss.

This is the fundamental reason Kafka messages are durable.
The broker NEVER loses data because a consumer is slow or down.
(Until retention period expires: default 7 days)
```

### What happens when consumer can't reach broker

```
Consumer poll() flow on broker failure:
────────────────────────────────────────────────────────────────────

  consumer.poll(Duration.ofMillis(1000))
  → sends FetchRequest to partition leader (Broker 2)
  → Broker 2 is DOWN: ConnectionException / TimeoutException
  
  Kafka consumer client auto-handles:
  1. Detects broker 2 gone
  2. Fetches updated metadata (new leader for that partition)
  3. Retries FetchRequest against new leader
  4. Returns records normally

  Your consumer code sees: slight delay on that poll() call
  (duration of leader election ~20-30s)
  poll() returns empty list during unavailability period
  Then returns queued messages once broker recovers

  Messages during downtime: safely stored in log.
  Consumer just reads them when broker recovers.
  Lag metric grows during downtime, drains on recovery.
```

### Consumer lag — the key metric

```
Consumer lag = (Log End Offset) - (Current Consumer Offset)
────────────────────────────────────────────────────────────────────

  Example: partition 0 of topic "orders"
  Producer has written up to offset 10,000  ← Log End Offset
  Consumer has committed offset 9,500       ← Current Consumer Offset
  Lag = 500 messages behind

  Lag = 0          → consumer keeping up perfectly ✓
  Lag slowly growing → consumer slower than producer
                       (add more consumers, scale up consumer instances)
  Lag suddenly jumps → consumer crashed, not reading
  Lag = millions    → consumer has been down for hours
                       (messages still safe until retention expires)
```

### How to debug consumer lag

```bash
# 1. The most important consumer debug command
kafka-consumer-groups.sh \
  --bootstrap-server broker1:9092 \
  --describe \
  --group order-processor-group

# Output:
# GROUP                TOPIC   PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG     CONSUMER-ID
# order-processor-group orders  0          9500            10000           500     consumer-1-abc123
# order-processor-group orders  1          8200            8200            0       consumer-2-def456
# order-processor-group orders  2          -               7500            -       (empty = no active consumer!)

# partition 2 shows "-" for CONSUMER-ID = no consumer assigned to it!
# This means your consumer group has fewer consumers than partitions
# → partition 2 messages accumulating, never processed

# 2. Check all consumer groups
kafka-consumer-groups.sh --bootstrap-server broker1:9092 --list

# 3. Check if consumer is actually alive
kafka-consumer-groups.sh --bootstrap-server broker1:9092 \
  --describe --group order-processor-group --members --verbose

# 4. Reset offset (use carefully — only for debugging/recovery)
kafka-consumer-groups.sh --bootstrap-server broker1:9092 \
  --group order-processor-group \
  --topic orders:0 \
  --reset-offsets --to-latest --execute  # skip to latest (lose unprocessed)
  # OR
  --reset-offsets --to-datetime 2026-08-31T00:00:00.000 --execute  # replay from timestamp
```

### Production example: Swiggy Notification Service goes down

```
Scenario: notification-service crashes at 7pm (dinner peak).
Producer (order-service) keeps producing "OrderPlaced" events.
notification-service is down for 45 minutes.

During downtime:
  ~100,000 orders placed × 1 event each = 100,000 events in Kafka log
  Consumer lag grows to 100,000
  Customers don't receive "order confirmed" notifications
  BUT: orders are safely in DB. Kafka has all events.

When notification-service restarts:
  Consumer polls from last committed offset
  Processes 100,000 queued events
  Customers receive notifications (45 min late)
  Lag drains in ~10 minutes (10K events/min processing rate)

Alert configuration:
  Alert: consumer_lag > 10000 for group "notification-service"
  Action: PagerDuty → restart notification-service pod
  SLA: notifications delivered within 2 minutes of order placement
  → If lag growing: auto-scale consumer instances (KEDA on EKS)
```

---

## SCENARIO 4 — CONSUMER CRASHES MID-PROCESSING

### The auto-commit trap (most common production bug)

```
enable.auto.commit=true (DEFAULT — dangerous):
────────────────────────────────────────────────────────────────────

  Timeline:
  T=0ms:   consumer.poll() returns messages 500-509 (10 messages)
  T=100ms: consumer starts processing message 500 (charge payment, update DB)
  T=200ms: consumer starts processing message 501
  T=5000ms: AUTO COMMIT FIRES (auto.commit.interval.ms=5000 default)
            → offset 509 committed to broker
            → broker believes: "consumer processed up to 509"
  T=6000ms: consumer is processing message 507
  T=6001ms: consumer POD CRASHES (OOM, deploy, kill -9)

  What happens on restart?
  Consumer asks broker: "where was I?"
  Broker: "your last committed offset was 509"
  Consumer: polls from offset 510
  Messages 507, 508, 509: NEVER PROCESSED. LOST.

  Real-world impact:
  Payment charged but order_service never processes confirmation
  Inventory decremented for messages 507-509 but order status never updated
  Customer charged, no order confirmation, no delivery
```

```
enable.auto.commit=false + manual commitSync (AT-LEAST-ONCE — correct):
────────────────────────────────────────────────────────────────────

  T=0ms:   consumer.poll() returns messages 500-509
  T=100ms-6000ms: consumer processes 500, 501, 502, 503, 504, 505, 506
  T=6001ms: consumer POD CRASHES at message 507
            NO commitSync was called yet

  On restart:
  Consumer asks broker: "where was I?"
  Broker: "your last committed offset was 499"
  Consumer: polls from offset 500
  Messages 500-506: REPROCESSED (at-least-once delivery)

  Your job: make the consumer IDEMPOTENT so reprocessing is harmless.
```

### Java code: manual commit patterns

```java
// Pattern 1: Commit after processing entire batch
@KafkaListener(topics = "orders", groupId = "order-processor")
public void processOrders(List<ConsumerRecord<String, String>> records,
                           Acknowledgment ack) {
    for (ConsumerRecord<String, String> record : records) {
        try {
            processOrder(record.value());  // your business logic
        } catch (Exception e) {
            log.error("Failed to process offset={}, key={}", record.offset(), record.key());
            // Don't ack — message will be redelivered
            // OR: send to DLQ after N retries
            sendToDLQ(record);
        }
    }
    ack.acknowledge();  // commit ONLY after all records processed
}

// application.properties:
// spring.kafka.listener.ack-mode=manual_immediate

// Pattern 2: Commit per message (lower throughput, finer granularity)
consumer.poll(Duration.ofMillis(100)).forEach(record -> {
    processRecord(record);
    consumer.commitSync(Collections.singletonMap(
        new TopicPartition(record.topic(), record.partition()),
        new OffsetAndMetadata(record.offset() + 1)  // +1: next offset to read
    ));
});
```

### Making your consumer idempotent

```
Problem: messages 500-506 will be reprocessed after crash.
Your processOrder() must handle being called twice for same orderId.

Option 1: Database UPSERT / ON CONFLICT DO NOTHING
────────────────────────────────────────────────────────────────────

  INSERT INTO order_status (order_id, status, updated_at)
  VALUES ('order-123', 'CONFIRMED', NOW())
  ON CONFLICT (order_id) DO NOTHING;  -- second insert silently ignored

  Works for: PostgreSQL, MySQL with INSERT IGNORE

Option 2: Deduplication table (universal pattern)
────────────────────────────────────────────────────────────────────

  // Before processing
  boolean alreadyProcessed = dedupeRepository.exists(
      record.topic(), record.partition(), record.offset()
  );
  if (alreadyProcessed) {
      log.info("Skipping already-processed offset={}", record.offset());
      return;
  }
  
  // Process the message
  processOrder(record.value());
  
  // Mark as processed (in same DB transaction as the processing)
  dedupeRepository.save(record.topic(), record.partition(), record.offset());

  Table: processed_messages(topic, partition, offset, processed_at)
  Unique constraint on (topic, partition, offset)

Option 3: Conditional update (check version/state before updating)
────────────────────────────────────────────────────────────────────

  UPDATE orders
  SET status = 'CONFIRMED'
  WHERE order_id = ? AND status = 'PENDING'  -- only if still PENDING
  -- Second execution: status already 'CONFIRMED', WHERE fails, 0 rows updated
  -- No error, idempotent ✓
```

### Consumer rebalancing — the silent killer

```
What is rebalancing?
  Consumer group has 3 consumers for 6 partitions.
  Consumer 2 crashes.
  Kafka triggers REBALANCE: reassign partitions 2-3 to consumers 1 and 3.
  During rebalance: ALL consumers STOP processing (stop-the-world).
  Rebalance can take 30-60 seconds for large groups.

Why it causes problems:
  Consumer 2 was processing partition 3, offset 850.
  Consumer 2 crashes without committing.
  After rebalance: Consumer 1 takes partition 3.
  Consumer 1 reads from last committed offset (say, 800).
  Messages 800-849: reprocessed. (at-least-once — acceptable if idempotent)
  Messages 850-current: processed fresh. ✓

Config to reduce rebalance frequency:
  session.timeout.ms=45000         # wait 45s before declaring consumer dead
  heartbeat.interval.ms=15000      # heartbeat every 15s (should be < session.timeout/3)
  max.poll.interval.ms=300000      # 5 min max between polls (for slow processing)
  partition.assignment.strategy=
    CooperativeStickyAssignor      # incremental rebalancing (only reassign changed partitions)
                                   # avoids stop-the-world for all consumers
```

### How to debug a crashed consumer

```bash
# 1. Describe the consumer group — look for missing consumers
kafka-consumer-groups.sh --bootstrap-server broker1:9092 \
  --describe --group order-processor-group

# Healthy output:
# PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG  CONSUMER-ID
# 0          10000           10000           0    consumer-abc (host1)
# 1          9800            9800            0    consumer-def (host2)
# 2          9500            9500            0    consumer-ghi (host3)

# Crashed consumer output:
# 0          8000            10000           2000  consumer-abc (host1)
# 1          7500            9800            2300  consumer-def (host2)
# 2          -               9500            -     (no consumer!)  ← CRASH

# 2. Check consumer application logs
kubectl logs -n production order-processor-0 --previous  # previous container (crashed one)
grep "ERROR\|FATAL\|Exception\|OutOfMemory" /var/log/order-processor/app.log | tail -100

# 3. Check JVM heap (if OOM caused crash)
# Look for: java.lang.OutOfMemoryError: Java heap space
# Fix: increase -Xmx, or find memory leak

# 4. Check max.poll.interval.ms violation (very common cause of rebalance)
# Log message: "consumer poll interval exceeded" or "Commit cannot be completed"
# This means: consumer took longer than max.poll.interval.ms between poll() calls
# Fix: increase max.poll.interval.ms OR process messages faster

# 5. Check if consumer is stuck in infinite retry loop
# Symptom: lag stays flat (not growing, not draining)
# Cause: one poison pill message that always fails, retried forever
# Fix: implement DLQ (Dead Letter Queue) pattern

# 6. Reset offset for manual recovery
# USE WITH CARE — this can replay or skip messages
# First: stop all consumers in the group
# Then reset:
kafka-consumer-groups.sh --bootstrap-server broker1:9092 \
  --group order-processor-group \
  --topic orders \
  --reset-offsets --to-datetime "2026-08-31T18:00:00.000" \
  --dry-run   # preview first!
  # --execute  # then execute
```

---

## THE DEAD LETTER QUEUE PATTERN

### When to use it

```
Problem: one "poison pill" message that always causes an exception.
────────────────────────────────────────────────────────────────────

  Message 9001: { "orderId": null, "amount": -500 }  ← malformed

  Consumer processes it: NullPointerException
  Consumer does NOT commit offset 9001
  Consumer retries: NullPointerException again
  Consumer retries: NullPointerException again
  ← STUCK FOREVER. All messages after 9001 never processed.

Solution: after N retries, move message to DLQ topic.
  orders-dlq topic: receives poison pills
  order-processor: continues from offset 9002
  Ops team: inspects orders-dlq, fixes bad messages, replays manually
```

→ For full Spring `@RetryableTopic` + `@DltHandler` implementation code, see **`Kafka_Exactly_Once_At_Least_Once_DLQ.md`**.

---

## ALL ARCHITECT INTERVIEW SCENARIOS

| Interviewer asks | Architect answers |
|-----------------|-------------------|
| "Producer retried and sent duplicate message" | `enable.idempotence=true` — broker assigns each producer a PID + sequence number per partition. On retry, broker sees same sequence → deduplicates silently. |
| "Consumer auto-committed offset but crashed before processing" | Auto-commit is dangerous. Switch to `enable.auto.commit=false` + manual `commitSync` after processing. Trade-off: at-least-once delivery → make consumer idempotent. |
| "One message always fails, blocking the queue" | Dead Letter Queue pattern. After N retries, move to `-dlt` topic. Consumer continues. Ops team inspects DLT. Spring `@RetryableTopic` + `@DltHandler`. |
| "Consumer is slow, lag growing to millions" | (1) Scale out consumers — add instances up to partition count. (2) Increase partitions to allow more parallelism. (3) Profile consumer: is it DB-bound? Add connection pool. (4) Use async processing inside consumer with bounded queue. |
| "All ISR replicas for a partition went down" | `unclean.leader.election.enable=false` (default) → partition stays OFFLINE until ISR member returns. Availability sacrificed for durability. `=true` → elect out-of-sync replica → risk data loss. It's a business decision. For orders: stay offline. For metrics: allow unclean election. |
| "Exactly-once semantics end-to-end?" | Transactional producer (`transactional.id`) + `isolation.level=read_committed` on consumer. Expensive (~30% throughput drop). Only use for financial flows (payment events, ledger updates). For most use cases: at-least-once + idempotent consumer is sufficient and faster. |
| "Broker disk full?" | `log.retention.bytes` per partition (size cap), `log.retention.ms` (time cap). Alert at 70% disk. Add brokers and use `kafka-reassign-partitions.sh` to rebalance. S3-backed tiered storage (Kafka 3.6+) for infinite cheap retention. |
| "How do you know if data was lost?" | Producer: `record-error-rate` metric + callback exception counter. Consumer: compare `kafka.consumer:records-consumed-total` vs producer `records-sent-total` over a time window. Discrepancy = data loss or processing failure. |
| "Broker goes down — how long is partition unavailable?" | ZooKeeper mode: 20-30 seconds (session timeout + election). KRaft mode: 6-10 seconds. During this: producers queue in RecordAccumulator (if delivery.timeout.ms is long enough), consumers retry automatically. With proper config: transparent to application layer, just a latency spike. |
| "What is ISR and why does it matter?" | In-Sync Replicas = replicas currently within `replica.lag.time.max.ms` of leader. `acks=all` only waits for ISR, not ALL replicas. If ISR = [leader only], `acks=all` = `acks=1`. Set `min.insync.replicas=2` to refuse writes if ISR < 2 — better fail explicitly than lose data silently. |
| "How does Kafka guarantee ordering?" | Only within a partition. Same partition key → MurmurHash2 → same partition → ordered. Different partition keys → different partitions → no global order. Design: use entity ID (orderId, userId) as partition key for per-entity ordering. Cross-partition ordering: use a single-partition topic (throughput capped at 1 partition's limit). |
| "Consumer group rebalancing causing slowdowns?" | Use `CooperativeStickyAssignor` — incremental rebalance, only reassigns changed partitions, other consumers keep processing. Old `RangeAssignor` / `RoundRobinAssignor` = stop-the-world. Tune `session.timeout.ms` and `max.poll.interval.ms` to avoid false rebalances from slow consumers. |
| "What if the DLQ topic itself fills up?" | Alert on DLQ consumer lag. DLQ should have its own consumer group monitoring. Operations runbook: inspect DLQ messages, fix root cause, replay via `kafka-consumer-groups.sh --reset-offsets`. Never silently drop DLQ messages — they represent real business events. |

---

## QUICK REFERENCE CARD

```
Producer failure survival guide:
  acks=all + retries=MAX_VALUE + delivery.timeout.ms=120000
  enable.idempotence=true  (prevents duplicates on retry)
  ALWAYS use send() callback to detect dropped messages
  Fallback: Outbox table in DB → CDC to re-publish

Broker crash survival guide:
  replication.factor=3 (lose 2 brokers, still have data)
  min.insync.replicas=2 (refuse writes if ISR shrinks to 1)
  Alert: UnderReplicatedPartitions > 0 immediately
  KRaft mode: leader election ~6s (vs 30s ZooKeeper)

Consumer crash survival guide:
  enable.auto.commit=false
  commitSync() AFTER processing (not before)
  Make consumer idempotent: ON CONFLICT DO NOTHING or dedup table
  DLQ pattern: @RetryableTopic(attempts=3) + @DltHandler

Key metrics to monitor (alert thresholds):
  Producer: record-error-rate > 0 → immediate alert
  Broker:   UnderReplicatedPartitions > 0 → immediate alert
  Consumer: consumer_lag > 10000 → warning; > 100000 → critical
  Broker:   OfflinePartitionsCount > 0 → immediate alert

Key commands:
  Check partition health:
    kafka-topics.sh --describe --under-replicated-partitions
  Check consumer lag:
    kafka-consumer-groups.sh --describe --group <group>
  Reset offset (recovery):
    kafka-consumer-groups.sh --reset-offsets --to-datetime <ts> --execute
  Check broker availability:
    kafka-broker-api-versions.sh --bootstrap-server <host:port>

Delivery semantics summary:
  at-most-once:  acks=0 or auto-commit before processing → fast, data loss
  at-least-once: acks=all + manual commit after processing → duplicates possible
  exactly-once:  transactional.id + read_committed → slowest, use for finance only
  Practical default: at-least-once + idempotent consumer = safe + fast
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

| System | Kafka failure scenarios that come up |
|--------|------------------------------------|
| **08 — Food Delivery (Zomato/Swiggy)** | OrderPlaced event: producer failure → outbox pattern. Driver location events: at-least-once acceptable (latest location wins). Consumer crash (notification service): lag recovery, 45-min delayed notifications. DLQ for malformed delivery events. |
| **09 — E-Commerce (Amazon/Flipkart)** | Flash sale: broker overload during spike → min.insync.replicas protection. Inventory deduction: exactly-once required (oversell risk). DLQ for malformed order events. Consumer lag alert → auto-scale consumers. |
| **06 — UBER/OLA** | Driver location events: acks=1 acceptable (losing 1 location update harmless). Ride state events (REQUESTED → ACCEPTED → PICKED_UP): acks=all + idempotent consumer. Consumer crash during ride matching: rebalance, at-least-once, idempotent via orderId unique constraint. |
| **04 — Chat (WhatsApp)** | Message delivery: at-least-once acceptable (duplicate "hello" harmless vs missing "hello"). Producer retry with idempotence prevents duplicate messages. Consumer crash: replay from offset, dedup by message_id. |
| **19 — Stock Broker** | Trade events: exactly-once required (duplicate trade execution = serious bug). Transactional producer + read_committed consumer. DLQ for rejected trades (compliance hold). Broker crash during market hours: min.insync.replicas=2, KRaft for fast election. |
| **15 — Distributed Logging** | Log events: acks=1 acceptable (losing 1 log line ok). Consumer (Firehose to S3): crash recovery via offset replay. High throughput: tune batch.size, linger.ms, compression.type=snappy. |

**Architect's one-liner:**
*"Kafka itself never loses data — the log is the source of truth until retention expires. Data loss in Kafka systems happens in two places: producer side (acks=0/1 with broker crash) and consumer side (auto-commit before processing). Fix both with acks=all + idempotent producer, and manual commit + idempotent consumer. Everything else is a latency problem, not a data loss problem."*

---

## PRODUCTION DEBUGGING — SIMPLE ENGLISH GUIDE

### The 3 tools you open when Kafka breaks in prod

When something breaks, you have 3 questions:

```
"What went wrong?"           → search your logs     → ELK (Kibana)
"When did it go wrong?"      → look at charts       → Grafana
"Which exact order got lost?" → follow the trail    → Distributed Tracing (Jaeger)
```

---

### Tool 1 — ELK / Kibana (Searching your logs)

**ELK is Google Search but for your app's log lines.**

When your Kafka consumer crashes, it logs an error. That error goes to Elasticsearch. You open Kibana and search for it.

The problem without structured logging:
```
# Bad log — you can't filter anything
"ERROR: Kafka failed"

# Good log — you can search by orderId, partition, offset
"ERROR: kafka.send.failed orderId=ORD-123 topic=orders partition=3 offset=9001 error=NetworkException"
```

Add Kafka context to every log line using MDC:
```java
MDC.put("orderId", record.key());
MDC.put("kafkaTopic", record.topic());
MDC.put("kafkaPartition", String.valueOf(record.partition()));
MDC.put("kafkaOffset", String.valueOf(record.offset()));
log.info("Processing order");   // every log inside processOrder() now has orderId
MDC.clear();
```

Kibana searches for common problems:

| Problem | Search query in Kibana |
|---------|----------------------|
| Find all errors for one order | `orderId:ORD-123` |
| Find all messages that went to DLQ | `topic:orders-dlt` |
| Find all consumer crash events | `error:CommitFailedException` |
| Find consumer kicked out of group | `"max.poll.interval"` |
| Find producer failures | `kafka.send.failed AND level:ERROR` |
| Find broker unavailable errors | `error:NetworkException OR error:LeaderNotAvailable` |

**That's it. ELK = write good logs → search them when something breaks.**

---

### Tool 2 — Grafana (Charts that show numbers over time)

Think of it like your car's dashboard — speed, fuel, temperature. You glance at it and know if something is wrong.

The 4 numbers that matter for Kafka:

```
UnderReplicatedPartitions  → should ALWAYS be 0
                              if > 0: a broker is struggling or crashed

ConsumerLag                → how many messages your consumer is behind
                              = 0:         consumer keeping up ✓
                              = 50,000:    consumer is behind ⚠️ (alert)
                              = 1,000,000: consumer has been down for hours 🔴

ProducerErrorRate          → how many messages producer FAILED to send
                              should be 0 always
                              if > 0: messages are being DROPPED right now

ActiveControllerCount      → should ALWAYS be exactly 1
                              = 0: cluster has no controller, nothing works 🔴
```

Set alerts in Grafana:
```
ConsumerLag > 10,000  → send Slack/PagerDuty alert
UnderReplicatedPartitions > 0 → immediate PagerDuty (broker crashed)
ProducerErrorRate > 0 → immediate PagerDuty (messages dropping)
```

That's how you know before the customer calls support.

---

### Tool 3 — Distributed Tracing / Jaeger (Follow one message end to end)

Most useful when a customer says "my order ORD-123 never arrived."

Without tracing — you manually search 3 separate log files and spend 2 hours.

With OpenTelemetry, every message carries a trace ID from producer all the way to consumer. You go to Jaeger and search `orderId=ORD-123`:

```
ORD-123 journey (trace ID: abc-123):

  HTTP POST /orders           50ms   ✓  (order created in DB)
  Kafka send: orders           5ms   ✓  (message sent to broker)
  Kafka consume: orders        ???   ✗  ← MISSING SPAN

  → consumer never processed this message
  → consumer was down at 7:02pm
  → message is sitting in Kafka at partition=3 offset=9001
  → check Grafana: consumer_lag = 47,000 messages behind
```

You now know in 30 seconds: the message is safe in Kafka, consumer is lagging, restart it and ORD-123 will be processed when it catches up.

---

### Real scenario — how all 3 tools work together

```
Step 1: Grafana alert fires at 7pm
        "consumer_lag = 200,000 for group order-processor"

Step 2: Open Kibana
        Search: group:order-processor AND level:ERROR after 6:55pm
        See: CommitFailedException spam starting at 6:58pm
        See: "consumer poll interval exceeded" at 6:58pm

Step 3: Open Jaeger
        Search a few recent orders → consumer spans missing from 6:58pm
        Producer spans: all present ✓ (messages reached broker safely)

Step 4: Root cause found
        Bad deployment at 6:58pm caused consumer to take >5 min between poll() calls
        Kafka kicked it out of the group (max.poll.interval.ms exceeded)
        Consumer kept crashing and restarting, never catching up

Step 5: Fix
        Roll back the bad deployment
        Consumer restarts healthy
        Processes 200,000 queued messages in ~20 minutes
        Lag drains to 0. No data loss (messages were safe in Kafka the whole time)
```

---

### Simple summary table

| Tool | What it tells you | When to open it |
|------|------------------|-----------------|
| **Kibana (ELK)** | "show me all errors for orderId X" | Customer complains about specific order |
| **Grafana** | "consumer is 200K messages behind since 7pm" | Alert fires / something feels slow |
| **Jaeger (Tracing)** | "producer sent it OK but consumer never touched it" | Need end-to-end trail for one request |

---

→ For `acks` deep dive with ISR mechanics, safety matrix, and `min.insync.replicas` configs, see **`Kafka_ISR_acks_Replication_Guarantees.md`**.
