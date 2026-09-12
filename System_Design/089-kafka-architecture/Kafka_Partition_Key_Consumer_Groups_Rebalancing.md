# Kafka Partition Keys, Consumer Groups & Rebalancing
### How Kafka decides where messages go — and what happens when workers fail

---

## PART 1 — THE STUDENT CONVERSATION

Imagine Kafka as a **highway with multiple lanes**. Each lane is a partition. Messages are cars. The highway is a topic.

**No partition key (round-robin):**
Cars spread evenly across all lanes. Fast, balanced. But car A and car B both going to Alice's house might be in different lanes and arrive out of order. Nobody guaranteed order for Alice.

**user_id as partition key:**
Now imagine a rule: "all cars going to Alice's house MUST use Lane 3." Alice always gets her cars in the exact order they left the garage. Order is guaranteed per user. But if Alice orders pizza 1000 times a day and Bob orders once a week, Lane 3 is jammed — that's a **hot partition**.

**Consumer group:**
Now imagine 3 workers at the highway exits, each responsible for clearing certain lanes. 3 workers + 6 partitions = each worker handles 2 lanes. One worker quits. The remaining two workers pick up the abandoned lanes — that handoff period is called **rebalancing** (~30 seconds of slowdown in the old model).

The key insight: **partition count sets your max parallelism**. 6 partitions = max 6 consumers working in parallel. Adding a 7th consumer is wasted — it gets no partitions.

---

## PART 2 — PARTITION KEY ROUTING AND REBALANCING DIAGRAMS

### Partition Key Routing

```
Topic: payment-events (6 partitions)

Producer sends with key = account_id:

  account:alice   → MurmurHash2("alice")   % 6 = 2  → Partition 2
  account:bob     → MurmurHash2("bob")     % 6 = 5  → Partition 5
  account:charlie → MurmurHash2("charlie") % 6 = 2  → Partition 2 (collision!)
  account:alice   → always                 → Partition 2 (ordering guaranteed)

Timeline for Partition 2:
  P2: [alice:e1] [charlie:e1] [alice:e2] [alice:e3] [charlie:e2]

  ✓ All alice events in P2 are ORDERED relative to each other
  ✓ All charlie events in P2 are ORDERED relative to each other
  ✗ alice vs bob ordering: NOT guaranteed (different partitions)
```

### Consumer Group — Normal State

```
Topic: payment-events | 6 partitions | Consumer Group: payment-processors

  Consumer-A:  ← P0, P1
  Consumer-B:  ← P2, P3
  Consumer-C:  ← P4, P5

  Each consumer pulls at its own pace.
  Consumer-B committed offsets: P2@1500, P3@2300
  (stored in __consumer_offsets topic, not in your app)
```

### Consumer Group — After Consumer-B Crashes

```
Consumer-B crashes. Group Coordinator (Kafka broker) detects missed heartbeat.

  REBALANCING TRIGGERED (~30s for eager strategy)
  All consumers PAUSE (stop processing — "stop the world")

  After rebalance:
  Consumer-A:  ← P0, P1, P2   (inherits P2 from committed offset 1500)
  Consumer-C:  ← P3, P4, P5   (inherits P3 from committed offset 2300)

  Consumer-A resumes P2 from offset 1500.
  Messages P2@1490-1499 that Consumer-B processed but didn't commit? → REPROCESSED.
  → At-least-once delivery. Consumer MUST be idempotent.
```

### Incremental Cooperative Rebalancing (Kafka 2.3+)

```
Old eager rebalance:       New cooperative rebalance:
  All consumers STOP         Only moved partitions pause
  Reassign ALL partitions    Other partitions keep flowing
  All consumers RESUME       Near-zero downtime

  30s pause                  ~2s pause for moved partitions only
```

---

## PART 3 — INTERNALS AND IMPLEMENTATION

### How Partition Assignment Works

```
Default partitioner formula:
  partition = MurmurHash2(key) % numPartitions

No key → round-robin across partitions (Kafka 2.4+: sticky batching per partition
         until batch is full, then rotate — reduces small batches)

Custom partitioner:
  public class RegionPartitioner implements Partitioner {
      public int partition(String topic, Object key, byte[] keyBytes,
                           Object value, byte[] valueBytes, Cluster cluster) {
          String region = extractRegion((String) key);
          return REGION_TO_PARTITION_MAP.get(region); // deterministic
      }
  }
  props.put(ProducerConfig.PARTITIONER_CLASS_CONFIG, RegionPartitioner.class);
```

### Choosing Partition Count

```
Rules of thumb:
  1. partitions >= max consumers you'll EVER deploy
  2. partitions >= throughput_target / single_partition_throughput
     (single partition: ~10MB/s write, ~50MB/s read for typical hardware)
  3. More partitions = more overhead:
     - More open file handles on brokers
     - Longer leader election on broker failure
     - More memory on clients
  4. You CANNOT reduce partition count after creation.
     Increasing: allowed, but existing key routing changes for new messages.

Recommendation: start with 12-24 for most topics. Use multiples of your
consumer count so distribution is even (6 consumers → 12 or 24 partitions).
```

### Consumer Group Internals

```java
// Consumer configuration
Properties props = new Properties();
props.put("bootstrap.servers", "kafka:9092");
props.put("group.id", "payment-processors");            // consumer group name
props.put("auto.offset.reset", "earliest");             // on first start: read from beginning
props.put("enable.auto.commit", "false");               // NEVER use true in production
props.put("max.poll.interval.ms", "300000");            // 5 min: max time between polls
props.put("session.timeout.ms", "45000");               // 45s: heartbeat miss = dead consumer
props.put("partition.assignment.strategy",
    "org.apache.kafka.clients.consumer.CooperativeStickyAssignor"); // Kafka 2.4+

KafkaConsumer<String, Payment> consumer = new KafkaConsumer<>(props);
consumer.subscribe(List.of("payment-events"));

while (true) {
    ConsumerRecords<String, Payment> records = consumer.poll(Duration.ofMillis(100));
    for (ConsumerRecord<String, Payment> record : records) {
        processPayment(record.value());          // your business logic
    }
    consumer.commitSync();                       // commit AFTER successful processing
}
```

### Monitoring Consumer Lag

```bash
# Check lag per consumer group (run from Kafka broker or with bin on PATH)
kafka-consumer-groups.sh \
  --bootstrap-server kafka:9092 \
  --describe \
  --group payment-processors

# Output:
# GROUP               TOPIC           PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
# payment-processors  payment-events  0          145230          145231          1
# payment-processors  payment-events  2          98000           108000          10000  ← ALERT!

# Alert threshold: lag > 5000 for payments, lag > 50000 for non-critical topics
```

### Hot Partition Detection and Fix

```
Detection:
  # Uneven partition sizes = hot partition
  kafka-log-dirs.sh --bootstrap-server kafka:9092 --topic-list payment-events
  
  If Partition 2 has 10x more messages than others → hot partition

Fix Option A: Add random salt (breaks ordering guarantee)
  String key = accountId + "-" + ThreadLocalRandom.current().nextInt(10);
  // Now alice's events spread across 10 different partitions
  // ✗ Ordering per account lost
  // ✓ Even distribution

Fix Option B: More partitions + remapping
  Increase partition count from 6 to 60.
  High-volume accounts now map to different partitions.
  ✓ Ordering still held within each partition
  ✓ Better distribution if hot accounts spread across new partitions
  Risk: might still collide on same partition

Fix Option C: Separate topic for high-volume entities
  Topic: payment-events-vip  (for accounts with > 1000 tx/day)
  Topic: payment-events-standard
  ✓ VIP topic can have more partitions
  ✗ Application complexity increases
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your notification system has one Kafka topic with 12 partitions. You notice all messages from user-id=1 are being delayed, while other users are fine. What's happening?"

**You (architect answer):**

> "My first suspicion is a hot partition. If we're using user_id as the partition key, user-id=1 likely maps to a specific partition — let's say Partition 0. The question is why Partition 0 is slow.
>
> There are two likely causes. First: user-id=1 is generating a disproportionately high volume of messages — maybe it's a test account, or a celebrity account with millions of followers generating fan-out events. All those messages pile up in Partition 0 while the consumer processing Partition 0 can't keep up. I'd check `kafka-consumer-groups.sh --describe` to confirm the lag is specifically on Partition 0.
>
> Second: the consumer assigned to Partition 0 might be slow or stuck — perhaps it's making a slow downstream call (email provider latency, DB bottleneck). I'd check the consumer processing time and GC logs.
>
> Fix for hot partition: if it's volume-driven, I'd change the partition key from user_id to notification_id for this topic. Notifications for user-id=1 spread across all 12 partitions. We lose per-user ordering, but notification events are typically independent — a new notification doesn't depend on a previous one being processed first. This is the right trade-off here.
>
> Fix for slow consumer: scale out consumers (up to 12, one per partition), or optimize the consumer's downstream calls with async processing or batching."

---

## PART 5 — DECISION FRAMEWORK

### When to Choose Which Partition Key Strategy

```
Decision question: Do messages for the same entity need to be processed IN ORDER?

YES → Use entity ID as partition key (user_id, account_id, order_id)
       BUT check: is this entity a potential "celebrity" (high volume)?
         YES → Use a sub-entity key (order_id instead of user_id)
               or add a bounded salt (key + "-" + (hash % 10))
         NO  → Entity key is fine

NO  → Use no key (round-robin) or message_id for even distribution
      Best for: independent events where ordering doesn't matter
```

### Partition Key Trade-off Table

| Strategy | Ordering | Distribution | Hot Partition Risk | Use When |
|----------|----------|--------------|-------------------|----------|
| **No key (round-robin)** | None | Perfect | None | Events are independent, maximize throughput |
| **Entity ID key** | Per-entity | Uneven possible | High if entity is "celebrity" | Must process entity events in sequence |
| **Sub-entity key** (order_id) | Per-order | Good | Low | Entity volume unpredictable, per-order ordering enough |
| **Salted key** (id + random) | None | Perfect | None | Ordering not needed, volume unpredictable |
| **Custom partitioner** | Custom | Custom | Custom | Geographic routing, tenant isolation |

### Consumer Count vs Partition Count

```
partitions = 6, consumers = 3:  ✓ Each consumer gets 2 partitions
partitions = 6, consumers = 6:  ✓ Each consumer gets 1 partition (max parallelism)
partitions = 6, consumers = 7:  ✗ Consumer-7 gets ZERO partitions, sits idle
partitions = 6, consumers = 2:  OK but not ideal — one consumer gets 4 partitions

Rule: consumers <= partitions. Scale up partitions BEFORE consumers.
```

---

## QUICK REFERENCE CARD

```
PARTITION KEY:
  With key:    partition = MurmurHash2(key) % numPartitions
  No key:      round-robin (sticky batch in Kafka 2.4+)

CONSUMER OFFSETS:
  Stored in:   __consumer_offsets internal topic
  Commit:      consumer.commitSync() — after successful processing
  On crash:    consumer resumes from last committed offset
  At-least-once: messages between last commit and crash are reprocessed

REBALANCING:
  Trigger:     consumer joins/leaves, partition count changes
  Eager (old): all consumers pause ~30s, all partitions reassigned
  Cooperative: only moved partitions pause, others keep flowing
  Enable:      CooperativeStickyAssignor (Kafka 2.4+)

PARTITION SIZING:
  Can increase: YES (with routing change for new messages)
  Can decrease: NO
  Rule:         partitions >= max consumers you'll ever deploy

LAG MONITORING:
  Command:     kafka-consumer-groups.sh --describe --group <group>
  Alert on:    lag > N where N depends on SLA (e.g. 5000 for payments)

HOT PARTITION FIX:
  Detect:      one partition has 10x more messages
  Fix A:       change key to sub-entity (breaks ordering)
  Fix B:       increase partition count
  Fix C:       separate topic for high-volume entities
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Every time you design a Kafka consumer, the first question is "what's your partition key?" — that single choice determines ordering guarantees, distribution, and where your hot spots will be.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **03 — Notification System** | Events keyed by user_id ensure all notifications for a user are processed in order. But celebrity users (10M followers) trigger 10M notification events on one partition. Fix: key by notification_id for this topic — per-notification ordering is sufficient. |
| **05 — Social Media Feed** | Feed generation events keyed by author_id so all posts from one author fan out in chronological order. Viral authors become hot partitions — monitor lag per partition and split high-volume authors to their own topic segment. |
| **07 — Payment Processing** | Payment events keyed by account_id so debit/credit events for an account are always ordered. Critical correctness requirement: a debit must be processed before the subsequent balance check. Account with fraud attack generates 1000 tx/min — monitor for hot partitions by account. |
| **13 — Real-Time Leaderboard** | Score update events keyed by leaderboard_id ensures all score updates for a leaderboard reach one consumer in order. Redis ZADD operations are applied sequentially, preventing race conditions between concurrent score updates. |

**Architect's one-liner for the interview:**
*"Partition key is the single most important design decision in Kafka — it determines ordering scope, consumer parallelism, and where your hot spots will form under uneven load."*
