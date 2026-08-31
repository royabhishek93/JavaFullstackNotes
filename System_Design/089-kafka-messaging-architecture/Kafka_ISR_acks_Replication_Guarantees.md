# Kafka ISR, acks, and Replication Guarantees
### Why acks=all Doesn't Guarantee What You Think, and What ISR Has To Do With It

---

## PART 1 — THE STUDENT CONVERSATION

Imagine your Kafka broker has 3 replicas of a topic partition. Think of it like 3 people taking notes in a meeting.

- **acks=0**: You shout your idea, don't wait for anyone to write it down. Fastest, least safe.
- **acks=1**: You wait for the team lead (leader) to write it down. One confirmation, then move on.
- **acks=all**: You wait for EVERYONE on the ISR list to write it down. Safest — or so you think.

Here's the catch. ISR stands for **In-Sync Replicas** — the list of brokers that are currently keeping up with the leader. If one person fell asleep at the meeting (replica fell behind due to GC pause, slow network, etc.), Kafka removes them from the ISR list after a configurable timeout.

Now "everyone" means 2 people, not 3.

If the leader crashes right after those 2 acknowledged the write, and the 3rd broker (now out of ISR, 50 messages behind) becomes the new leader — the messages you thought were safely written to "all replicas" might be gone.

The second config you MUST know: `min.insync.replicas`. This tells Kafka: "don't even pretend acks=all succeeded unless at least N replicas are in-sync right now." If ISR shrinks below that number, throw an error to the producer. No silent data loss — just a loud failure that your retry logic can handle.

---

## PART 2 — ISR STATE DIAGRAMS

### ISR (In-Sync Replicas) Definition

```
Topic: payments, Partition 0
Replication factor: 3

Normal state:
  Leader:    Broker-1  <-- all writes go here first
  Follower:  Broker-2  <-- replicates from leader (lag = 0ms)
  Follower:  Broker-3  <-- replicates from leader (lag = 0ms)
  ISR = {Broker-1, Broker-2, Broker-3}   <-- all 3 in-sync

Broker-3 falls behind (slow network, GC pause):
  replica.lag.time.max.ms = 10000 (default: 10 seconds)
  Broker-3 lag > 10s --> removed from ISR
  ISR = {Broker-1, Broker-2}   <-- only 2 in ISR now!

Producer sends with acks=all:
  acks=all = "wait for all replicas IN ISR"
  ISR has 2 replicas --> only needs 2 acknowledgements!
  Broker-3 (out of ISR) is NOT waited for.
```

### The Data Loss Scenario with acks=all

```
State: ISR = {Broker-1, Broker-2}. Broker-3 is out of ISR, 50 messages behind.

Producer sends msg-1000 with acks=all:
  Broker-1 (leader): writes msg-1000
  Broker-2: replicates msg-1000
  acks=all satisfied: returns "success" to producer [OK]

Broker-1 crashes!
  Kafka controller: elect new leader from ISR = {Broker-2}
  New leader: Broker-2 (has msg-1000) [OK]

But what if Broker-2 ALSO crashes (network partition)?
  Only available broker: Broker-3 (out of ISR, 50 messages behind)

  min.insync.replicas = 1 (default): allow Broker-3 to become leader
  Result: msg-951 to msg-1000 are LOST (Broker-3 doesn't have them)

  min.insync.replicas = 2: refuse to elect Broker-3
  Result: partition is OFFLINE until Broker-2 recovers
          Availability reduced, but no data loss
```

### The acks + min.insync.replicas Safety Matrix

```
+-------------+--------------------------+---------------------------------------------+
|  acks       |  min.insync.replicas     |  Guarantee                                  |
+-------------+--------------------------+---------------------------------------------+
|  0          |  (ignored)               | Fire and forget. No guarantee.              |
|  1          |  (ignored)               | Leader only. Leader crash = data loss if    |
|             |                          | follower hasn't replicated yet.             |
|  all (-1)   |  1                       | Only leader needed. Same risk as acks=1.    |
|  all (-1)   |  2                       | At least 2 replicas. Good for most cases.   |
|  all (-1)   |  3 (= replication_factor)| All replicas. Strongest. Slowest write.     |
+-------------+--------------------------+---------------------------------------------+

Recommended production: acks=all + min.insync.replicas=2 + replication_factor=3
```

---

## PART 3 — INTERNALS: CONFIGS, CODE, AND MONITORING

### Producer Configuration for Payment Systems

```java
Properties props = new Properties();

// Durability
props.put("acks", "all");                                         // wait for full ISR
props.put("retries", Integer.MAX_VALUE);                          // retry forever
props.put("delivery.timeout.ms", 120000);                         // 2 minute total timeout
props.put("max.in.flight.requests.per.connection", 5);            // safe with idempotence
props.put("enable.idempotence", "true");                          // prevents duplicates on retry

// Batching for throughput
props.put("linger.ms", 5);                                        // wait 5ms to batch
props.put("batch.size", 65536);                                   // 64KB batch

// Connection
props.put("bootstrap.servers", "broker1:9092,broker2:9092,broker3:9092");
props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
props.put("value.serializer", "io.confluent.kafka.serializers.KafkaAvroSerializer");
```

### Broker / Topic Configuration

```bash
# Create topic with replication guarantees
kafka-topics.sh --create \
  --topic payments \
  --replication-factor 3 \
  --partitions 12 \
  --config min.insync.replicas=2 \
  --config retention.ms=604800000 \
  --bootstrap-server broker:9092

# Alter existing topic
kafka-configs.sh --alter \
  --entity-type topics \
  --entity-name payments \
  --add-config min.insync.replicas=2 \
  --bootstrap-server broker:9092
```

### Key Broker-Level Configs

```
# server.properties

# How long a follower can be out of sync before being removed from ISR
replica.lag.time.max.ms=10000          # default: 10s — tune down to 5s in production

# Replication throttle (to prevent replication overloading during broker recovery)
replica.fetch.max.bytes=1048576        # 1MB per fetch request

# Unclean leader election: allow out-of-ISR broker to become leader?
# false = prefer availability loss over data loss
unclean.leader.election.enable=false   # MUST be false for financial systems
```

### Monitoring ISR Health

```bash
# Check ISR for all partitions of a topic
kafka-topics.sh --describe \
  --topic payments \
  --bootstrap-server broker:9092

# Output to look for:
# Topic: payments  Partition: 0  Leader: 1  Replicas: 1,2,3  Isr: 1,2,3   <-- healthy
# Topic: payments  Partition: 1  Leader: 1  Replicas: 1,2,3  Isr: 1,2     <-- broker 3 out!

# Check all under-replicated partitions across the cluster
kafka-topics.sh --describe \
  --under-replicated-partitions \
  --bootstrap-server broker:9092

# Alert: under_replicated_partitions > 0 for more than 5 consecutive minutes
# Metric: kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions
```

### What NotEnoughReplicasException Looks Like

```java
try {
    RecordMetadata metadata = producer.send(record).get();
} catch (ExecutionException e) {
    if (e.getCause() instanceof NotEnoughReplicasException) {
        // ISR shrank below min.insync.replicas
        // Safe to retry with exponential backoff
        retryWithBackoff(record);
    } else if (e.getCause() instanceof NotEnoughReplicasAfterAppendException) {
        // Message was written to leader but ISR shrank before followers acked
        // This is idempotent-safe: retry will not duplicate if enable.idempotence=true
        retryWithBackoff(record);
    }
}
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer**: Your Kafka cluster has replication factor 3 and acks=all. A senior engineer says this guarantees no data loss. Is that true?

**You**: Not quite — and this is a common misconception worth clarifying. `acks=all` waits for all replicas **in the ISR** — the In-Sync Replicas list. ISR is dynamic. If a broker falls behind and is removed from ISR, the ISR might shrink to just the leader. At that point, `acks=all` is effectively `acks=1` — only one broker acknowledges the write.

**Interviewer**: So how do you actually prevent data loss?

**You**: You need two configs working together. First, `acks=all` on the producer. Second, `min.insync.replicas=2` on the topic. This tells Kafka: "if ISR drops below 2 replicas, reject the produce request with a `NotEnoughReplicasException`." The producer retries with backoff rather than silently succeeding with weak durability. Third, make sure `unclean.leader.election.enable=false` on the brokers — otherwise Kafka might elect an out-of-ISR broker as leader during a partition, and you'd lose all messages that replica missed.

**Interviewer**: What's the tradeoff?

**You**: Availability. With `min.insync.replicas=2` on a 3-broker cluster, if 2 brokers go down simultaneously, the partition becomes unavailable — producers get errors. You're choosing CP over AP in the CAP sense. For payment systems, that's the right call — I'd rather have a partition go offline than silently lose a payment event. For analytics events or log streams where occasional loss is acceptable, I'd use `acks=1` and gain throughput. The numbers: `acks=all` with 3 replicas adds roughly 10–30ms latency vs `acks=1` on a well-tuned cluster in the same AZ. Across AZs, that can be 50–100ms.

**Interviewer**: What about exactly-once semantics?

**You**: That requires `enable.idempotence=true` on the producer plus `isolation.level=read_committed` on the consumer. Idempotence gives you exactly-once **per partition** — no duplicates on retry. For cross-partition exactly-once (e.g., consume-transform-produce), you need Kafka Transactions: `transactional.id` on the producer and a `beginTransaction / commitTransaction` block. This is the Kafka Streams model.

---

## PART 5 — DECISION FRAMEWORK

### acks Setting by Use Case

| Use Case | acks | min.insync.replicas | Reasoning |
|---|---|---|---|
| Payment processing | all | 2 | No silent data loss. NotEnoughReplicasException triggers retry. |
| Order events | all | 2 | Transactional. Can't lose order creation events. |
| User activity logs | 1 | 1 (default) | Loss of a few clicks is acceptable. Throughput matters. |
| Analytics events | 1 | 1 (default) | Best-effort. Downstream handles occasional gaps. |
| Audit trail | all | 3 | Every event must be written to all replicas. Slow but safe. |
| Real-time metrics | 0 | 1 (ignored) | Ultra-low latency. Metrics aggregated anyway; single-point loss fine. |
| IoT sensor data | 1 | 1 | High volume, low value per event. Aggregated upstream. |
| Trade execution | all | 2 | Financial obligation. Same as payments. |

### When to Use min.insync.replicas = 1, 2, or 3

| Value | When | Risk |
|---|---|---|
| 1 | Default. Acceptable for non-critical topics. | acks=all degrades to acks=1 silently if ISR is healthy. |
| 2 | Recommended for production financial/transactional topics. | Partition offline if 2 of 3 brokers fail simultaneously. |
| 3 | Audit logs, compliance data where loss is legally unacceptable. | Partition offline if ANY broker fails. Very high availability cost. |

---

## QUICK REFERENCE CARD

```
PRODUCER CONFIGS:
  acks=0          Fire and forget. Max throughput, no durability.
  acks=1          Leader ack only. Fast. Leader crash = potential loss.
  acks=all (-1)   All ISR members ack. Safe IF min.insync.replicas > 1.

TOPIC CONFIGS:
  min.insync.replicas=2     Require 2 brokers in ISR (for RF=3)
  replication.factor=3      Standard 3-way replication
  unclean.leader.election.enable=false   Never elect stale leaders

BROKER CONFIGS:
  replica.lag.time.max.ms=10000    10s lag = removed from ISR

MONITORING:
  under_replicated_partitions > 0   Alert: ISR is degraded
  kafka-topics.sh --describe --under-replicated-partitions

EXCEPTION HANDLING:
  NotEnoughReplicasException          ISR too small. Retry with backoff.
  NotEnoughReplicasAfterAppendException  Written to leader, ISR shrunk. Idempotent retry.

GOLDEN CONFIG (payments):
  acks=all + min.insync.replicas=2 + RF=3 + unclean.leader.election=false + enable.idempotence=true
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

| System | Config Used | Why |
|---|---|---|
| **07 Payment System** | `acks=all + min.insync.replicas=2 + RF=3` | Payment events must never be silently lost. `NotEnoughReplicasException` triggers retry with jitter. Financial obligation. |
| **13 Leaderboard** | `acks=1 + min.insync.replicas=1` | Losing a few score update events is acceptable — rank might be slightly stale for seconds. Throughput > durability. High write volume from millions of players. |
| **19 Stock Broker** | Trade events: `acks=all + min.insync.replicas=2`. Market data feed: `acks=1`. | Trade execution events create legal obligations — cannot lose them. Market data is broadcast; losing one price tick is cosmetic. |
| **03 Notification System** | `acks=all + min.insync.replicas=2` | Missed notification events = missed notifications to users. Downstream consumers are idempotent anyway. |
| **09 E-Commerce** | Order events: `acks=all`. Inventory events: `acks=1`. | Order creation is transactional. Inventory count events are high-volume aggregates — minor loss corrected by periodic reconciliation. |

---

> **Architect one-liner**: "acks=all only waits for in-sync replicas — if ISR shrinks to 1 due to a lagging broker, you have no more guarantee than acks=1; set min.insync.replicas=2 to enforce a minimum safety floor."
