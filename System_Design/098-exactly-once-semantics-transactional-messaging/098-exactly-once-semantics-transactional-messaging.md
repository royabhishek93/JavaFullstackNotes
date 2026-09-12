# Exactly-Once Semantics & Transactional Messaging in Kafka
### Why "exactly-once" is a lie at the network level, and what Kafka actually guarantees instead

---

## PART 1 — THE STUDENT CONVERSATION

Imagine two generals on opposite hills, each commanding half an army, needing to attack a fortified city at the exact same time or the attack fails. They can only communicate by sending a messenger across the valley between them — and the valley is patrolled by the enemy, so any messenger might get captured. General A sends "attack at dawn." Does he know General B received it? No — the messenger might have been captured. So General B, upon receiving it, sends an acknowledgment back. But now General B doesn't know if *his* acknowledgment got through either! No matter how many rounds of confirmation you add, there is always one more message whose delivery is uncertain. This is the **Two Generals Problem**, and it's a mathematical proof that over an unreliable network, you cannot guarantee both parties have common knowledge that a message was received — full stop, no protocol fixes this.

This is why "exactly-once delivery" over a network is, strictly speaking, impossible. If a producer sends a message and doesn't get an acknowledgment back (because the ack itself got lost, not the message), the producer cannot tell "did the broker never get it?" from "the broker got it, wrote it, and just the ack died on the way back?" Its only safe choice is to retry — and now there's a real chance the message lands twice.

So what does Kafka actually mean when people say it supports "exactly-once semantics"? It's not magic that defeats the Two Generals Problem — it's two clever, narrower guarantees stacked together, each solving a *specific* duplication scenario:

1. **Idempotent producer** — solves "my retry after a lost ack creates a duplicate." The producer tags every message with a unique fingerprint (Producer ID + sequence number), and the broker recognizes "I've already written this exact fingerprint" and silently drops the duplicate on retry. Think of it like a chef writing an order number on every dish ticket — if the same ticket number comes through twice because the printer jammed and someone reprinted it, the kitchen just throws away the reprint instead of cooking the dish twice.

2. **Transactions** — solves the bigger problem of "I read message A, did some processing, and need to write output B and also mark message A as consumed — and either ALL of that happens, or NONE of it does." This is the classic "consume-transform-produce" pattern in Kafka Streams. Without transactions, you could write output B successfully, then crash before marking A as consumed — on restart, you'd reprocess A and write a *second* copy of B. Transactions wrap "commit my offset" and "produce my output" into one atomic unit, like a bank transfer where debiting one account and crediting another either both happen or neither does.

The critical thing to internalize: both of these guarantees only hold **within Kafka's own bookkeeping** — the topics, partitions, and consumer offsets that Kafka itself manages. The moment your consumer does something *outside* Kafka as a side effect of processing a message — calling a payment gateway, writing to a different database, sending an email — Kafka's transactional guarantee cannot protect that external action. If your consumer crashes right after calling the payment API but right before committing its Kafka offset, the message gets reprocessed and the payment API gets called *again*. That's a completely separate problem requiring idempotency keys at the external system's boundary (see 012-idempotency-keys-prevent-double-processing.md) — Kafka transactions and idempotency keys solve two different halves of the same overall "exactly-once effect" goal.

---

## PART 2 — THE EOS ARCHITECTURE DIAGRAMS

### Idempotent Producer: PID + Sequence Number Deduplication

```
Producer starts up, requests a Producer ID (PID) from the broker's
transaction/idempotency coordinator (part of InitProducerId RPC):

  Producer                                    Broker (partition leader for topic-A-0)
  ────────                                    ──────────────────────────────────────

  InitProducerId() ──────────────────────────►
                    ◄────────────────────────── PID=7842, epoch=0

  send(topic-A, partition-0, "order created")
    Producer attaches: PID=7842, seq=0
  ProduceRequest(PID=7842, seq=0, ...) ───────►
                                                Broker checks: last seen seq for
                                                PID=7842 on this partition = -1
                                                seq=0 is next expected → ACCEPT, write
                                                Update: last seen seq(PID=7842) = 0
                    ◄──────────────────────────  ACK (offset=1001)

  [Network glitch: ACK lost in transit, producer times out waiting]

  Producer retries the SAME message (framework does this automatically):
  ProduceRequest(PID=7842, seq=0, ...) ───────►   <-- SAME seq=0, this is a retry
                                                Broker checks: last seen seq for
                                                PID=7842 on this partition = 0
                                                seq=0 was ALREADY processed
                                                → DUPLICATE, do NOT write again
                                                → just re-ACK the existing offset
                    ◄────────────────────────── ACK (offset=1001)  [no new write!]

  Next real message:
  send(topic-A, partition-0, "order shipped")
    Producer attaches: PID=7842, seq=1
  ProduceRequest(PID=7842, seq=1, ...) ───────►
                                                seq=1 is next expected → ACCEPT, write
                    ◄────────────────────────── ACK (offset=1002)

  Key facts:
  - PID + sequence number is PER PARTITION (broker tracks last seq per
    (PID, partition) pair, kept in an in-memory + snapshotted producer
    state map on the partition leader)
  - Enabled by: enable.idempotence=true (default true since Kafka 3.0
    when acks=all is also set)
  - Deduplication window: bounded by producer.id.expiration.ms (default
    7 days broker-side) — PIDs for inactive producers are eventually
    forgotten, this is NOT infinite-duration dedup
```

### Kafka Transactions: Consume-Transform-Produce (EOS v2)

```
Kafka Streams app: reads from "orders" topic, aggregates, writes to
"order-totals" topic AND commits its consumer offset — all atomically.

  Streams App                Transaction Coordinator         Partitions involved
  ───────────────────────    ────────────────────────         ──────────────────
  transactional.id=
    "streams-app-1"

  initTransactions() ────────►
                              Assigns/fences producer epoch
                              for transactional.id
                    ◄──────── PID=5001, epoch=3 (bumped from
                               epoch=2 — fences out any ZOMBIE
                               instance still running epoch=2!)

  beginTransaction() ──(local only, no broker RPC yet)──

  consume "orders" offset=200
    → compute total, produce to "order-totals"

  produce(order-totals, "total=$450") ───────►  Partition: order-totals-0
                                                 Write tagged with
                                                 PID=5001,epoch=3, TX in-progress

  sendOffsetsToTransaction(
    {orders-0: offset 201}) ───────────────────► Written to
                                                 __consumer_offsets partition,
                                                 ALSO tagged as part of this TX

  commitTransaction() ────────►
                              Coordinator runs 2-phase-commit-style protocol:
                              PHASE 1 (prepare): coordinator writes
                                "PrepareCommit" to its own internal
                                __transaction_state log (durable, replicated)
                              PHASE 2 (commit markers): coordinator sends
                                a transaction MARKER to every partition
                                that was written to in this TX:
                                  → order-totals-0: write COMMIT marker
                                  → __consumer_offsets (orders-0's offset
                                    partition): write COMMIT marker
                              Once ALL markers are written: coordinator
                              writes final "CompleteCommit" — TX is done.
                    ◄──────── TX committed

  Consumer reading order-totals with isolation.level=read_committed:
    Sees "total=$450" ONLY after the COMMIT marker is written.
    A consumer with isolation.level=read_uncommitted would see it
    immediately, even if the TX later ABORTS (and would then see a
    later ABORT marker, but many naive consumers never check for that).

  RESULT: "order-totals write" + "orders offset commit" are atomic —
  either both are visible to read_committed consumers, or neither is.
  On crash mid-transaction: the coordinator's transaction timeout
  (transaction.timeout.ms, default 60s) eventually aborts the dangling
  TX, and the fenced-out old epoch prevents a "zombie" instance of the
  same app from writing further under the old, stale epoch.
```

### Failure Mode: Zombie Producer Fencing

```
Scenario: Streams app instance crashes but isn't dead — it's just
partitioned from the network (a "zombie"), while a NEW instance with
the same transactional.id is started by the orchestrator (e.g. k8s
restarts the pod believing the old one is dead).

  OLD instance (zombie,          Transaction Coordinator      NEW instance
  still thinks it's alive)                                    (just started)
  ──────────────────────         ────────────────────         ──────────────
                                                                initTransactions()
                                                                transactional.id=
                                                                  "streams-app-1"
                                                    ◄──────────
                                  Sees existing PID for this
                                  transactional.id at epoch=3
                                  → bumps to epoch=4, returns
                                  it to the NEW instance
                                                    ──────────► PID=5001, epoch=4

  [Zombie OLD instance, unaware
   it's been replaced, still
   tries to commit under epoch=3]

  produce(order-totals,
    PID=5001, epoch=3, ...) ────►
                                  Broker/coordinator compares
                                  epoch=3 (incoming) vs epoch=4
                                  (current known epoch for this PID)
                                  → epoch=3 is STALE
                                  → REJECT with
                                    ProducerFencedException
                    ◄──────────── ERROR: fenced!

  Zombie instance crashes/exits on this exception — it CANNOT
  produce anymore under its old identity. Only the NEW instance
  (epoch=4) can write. This prevents split-brain double-writes
  from two instances of "the same logical producer" running at once.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### The Three Delivery Guarantees, Configured

```java
// AT-MOST-ONCE: fire and forget, acks=0, no retries
// If the broker never gets it or ack is lost, message is simply gone.
Properties atMostOnce = new Properties();
atMostOnce.put(ProducerConfig.ACKS_CONFIG, "0");
atMostOnce.put(ProducerConfig.RETRIES_CONFIG, "0");
// Use case: metrics/telemetry where occasional loss is acceptable,
// latency matters more than completeness.

// AT-LEAST-ONCE: default-ish behavior with retries, no idempotence
// Guarantees delivery, but retries after a lost ACK can duplicate.
Properties atLeastOnce = new Properties();
atLeastOnce.put(ProducerConfig.ACKS_CONFIG, "all");
atLeastOnce.put(ProducerConfig.RETRIES_CONFIG, "3");
atLeastOnce.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, "false");
// Consumer commits offset AFTER processing — if it crashes after
// processing but before committing, it reprocesses on restart = duplicate.

// EFFECTIVELY-ONCE (what people mean by "exactly-once" in Kafka):
// idempotent producer + transactions
Properties effectivelyOnce = new Properties();
effectivelyOnce.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, "true");
effectivelyOnce.put(ProducerConfig.ACKS_CONFIG, "all");           // required w/ idempotence
effectivelyOnce.put(ProducerConfig.TRANSACTIONAL_ID_CONFIG, "order-processor-1");
effectivelyOnce.put(ProducerConfig.MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION, "5"); // <=5 required

// Consumer side: must read only committed data
Properties consumerProps = new Properties();
consumerProps.put(ConsumerConfig.ISOLATION_LEVEL_CONFIG, "read_committed");
consumerProps.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, "false"); // offsets committed via TX instead
```

### Consume-Transform-Produce Loop (Plain Kafka Producer/Consumer API)

```java
KafkaProducer<String, String> producer = new KafkaProducer<>(effectivelyOnce);
producer.initTransactions();   // registers/fences transactional.id, gets PID+epoch

KafkaConsumer<String, String> consumer = new KafkaConsumer<>(consumerProps);
consumer.subscribe(List.of("orders"));

while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(500));
    if (records.isEmpty()) continue;

    try {
        producer.beginTransaction();

        Map<TopicPartition, OffsetAndMetadata> offsetsToCommit = new HashMap<>();
        for (ConsumerRecord<String, String> record : records) {
            String total = computeOrderTotal(record.value());
            producer.send(new ProducerRecord<>("order-totals", record.key(), total));

            offsetsToCommit.put(
                new TopicPartition(record.topic(), record.partition()),
                new OffsetAndMetadata(record.offset() + 1)
            );
        }

        // THE key call: offsets become part of the SAME transaction as the
        // "order-totals" produce above. Either both commit, or both abort.
        producer.sendOffsetsToTransaction(
            offsetsToCommit,
            consumer.groupMetadata()   // ConsumerGroupMetadata, EOS v2 API (KIP-447)
        );

        producer.commitTransaction();
    } catch (ProducerFencedException | OutOfOrderSequenceException e) {
        // Zombie fencing detected — this instance must shut down, cannot recover.
        producer.close();
        throw new IllegalStateException("Fenced out, exiting", e);
    } catch (KafkaException e) {
        producer.abortTransaction();   // roll back the in-flight TX, retry loop continues
    }
}
```

### Kafka Streams EOS Configuration (the framework does the above loop for you)

```java
Properties streamsProps = new Properties();
streamsProps.put(StreamsConfig.APPLICATION_ID_CONFIG, "order-total-aggregator");
streamsProps.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "kafka:9092");

// EOS v2 (Kafka 2.5+): one producer per StreamThread, shared transactional.id
// derived from application.id + task id. Fully replaces the old EOS "alpha"
// (one producer PER TASK, much higher broker resource overhead).
streamsProps.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG,
                  StreamsConfig.EXACTLY_ONCE_V2);

// Under the hood this sets, per internal producer:
//   enable.idempotence=true, transactional.id=<application.id>-<taskId>
//   isolation.level=read_committed on all internal consumers
//   (changelog restore consumers, repartition consumers, etc.)
```

### Real Numbers: Overhead & Failure Windows

```
Idempotent producer overhead:
  Negligible CPU (PID+seq is a few extra bytes in the produce request
  header). Broker keeps an in-memory map of (PID, partition) -> last
  seq, snapshotted into the segment's ".snapshot" file for crash
  recovery — a few KB per active PID per partition. Not a throughput
  bottleneck in practice.

Transaction overhead (measured, typical clusters):
  +2-5ms added latency per transaction commit vs a non-transactional
  produce, dominated by the 2-phase marker write (coordinator write +
  replication of the commit marker to every partition involved).
  Throughput impact: transactions batch multiple records per commit
  (e.g. commit.interval.ms in Streams, default 100ms for EOS, batching
  many messages per TX) — so per-message overhead amortizes down to
  low single-digit percent throughput cost at reasonable batch sizes.

transaction.timeout.ms (default 60000 = 60s):
  Max time a transaction can stay open before the coordinator
  proactively aborts it (protects against a hung producer holding
  locks/blocking read_committed consumers indefinitely on that
  partition — read_committed consumers cannot read PAST an
  open transaction on a partition, they stall until it resolves).

producer.id.expiration.ms (default 604800000 = 7 days):
  How long the broker remembers a PID's last sequence number for
  idempotence purposes if the producer goes silent. Not related to
  transactional.id fencing (that's tracked separately, indefinitely,
  keyed by transactional.id, via the transaction coordinator's log).

__transaction_state topic:
  Internal topic (50 partitions by default, transaction.state.log.
  num.partitions) storing transaction coordinator state durably —
  this is what lets a NEW coordinator (if the old one's broker dies)
  resume tracking in-flight transactions after a broker failover.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your team built a Kafka Streams service that reads payment-authorization events, aggregates them, and calls an external payment gateway API to actually charge the customer. Someone on the team says 'we have exactly-once semantics configured in Kafka Streams, so we're safe from double-charging customers.' Do you agree?"

**You (architect answer):**

> "No, and this is one of the most common misunderstandings of what Kafka's exactly-once semantics actually cover. EOS in Kafka — idempotent producers plus transactions — guarantees exactly-once *within Kafka's own bookkeeping*: if my service reads a message, writes some output to another Kafka topic, and commits its consumer offset, all three of those things happen atomically as one transaction. If the process crashes at any point before the transaction commits, on restart it re-reads from the last committed offset and redoes the work — but because the previous attempt's writes were never committed (the transaction was aborted), a `read_committed` consumer never saw the partial, uncommitted output. That's a real and valuable guarantee, but it only spans Kafka-to-Kafka.
>
> The moment this service calls an external payment gateway API as a side effect of processing a message, we've stepped outside what Kafka's transaction can protect. Picture the exact failure: the service processes the payment-authorization event, successfully calls the payment gateway and charges the card, and then crashes before it commits its Kafka offset. On restart, it resumes from the last committed offset — which is *before* the message it already charged for — and reprocesses that same message, calling the payment gateway a second time. Kafka's transaction did exactly what it promised: the Kafka-side offset commit didn't happen, so Kafka correctly redelivers the message. The problem is entirely on the external side, which Kafka has no visibility into or control over.
>
> The fix is to push idempotency to the boundary where the actual side effect happens: generate a stable idempotency key for each payment-authorization event — I'd typically derive it from something already unique and immutable in the event itself, like the order ID or a UUID assigned when the authorization was first created — and pass that key to the payment gateway's idempotency-key mechanism (most modern payment APIs, Stripe included, support exactly this). The gateway then guarantees that two calls with the same idempotency key result in only one actual charge, regardless of how many times my Kafka consumer redelivers and retries. So the real design is two independent idempotency mechanisms stacked at two different boundaries: Kafka's producer/transaction idempotency protects the Kafka-internal state, and an idempotency-key pattern at the payment gateway call protects the external side effect. I'd correct the team's assumption immediately, because 'we have EOS so we're safe' is exactly the kind of false confidence that leads to a very expensive double-charge incident in production."

---

## PART 5 — DECISION FRAMEWORK

### Delivery Guarantee Approaches Compared

| Approach | How It Works | Consistency / Tradeoff | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **At-most-once** (`acks=0`, no retry) | Fire and forget | May silently lose messages on any transient failure | Lowest | Lowest | Any network blip = permanent data loss, no recovery signal |
| **At-least-once** (`acks=all`, retries, no idempotence) | Retries on ack timeout/failure | Guarantees delivery but retries can create duplicates | Low-medium | Low | Downstream must be idempotent itself, or duplicates corrupt state (e.g. double counters) |
| **Idempotent producer** (`enable.idempotence=true`) | PID + per-partition sequence number dedupes retries at the broker | Removes producer-retry duplicates; does NOT cover consumer-side reprocessing or multi-partition atomicity | Low-medium (negligible added overhead) | Low-medium | Doesn't help if the SAME logical write is sent from two different application instances/producers (different PIDs) — that's a business-logic dedup problem, not a Kafka one |
| **Transactions / EOS v2** (`transactional.id`, `read_committed`) | 2-phase-commit-style marker protocol across all partitions written in a TX, including offset commits | Atomic "read A + write B + commit A's offset" within Kafka; does NOT extend to any non-Kafka side effect | +2-5ms/commit typical, amortized by batching | Medium-High (coordinator, fencing, timeouts to reason about) | External side effects (API calls, non-Kafka DB writes) are NOT covered — need idempotency keys at that boundary |
| **Idempotency keys at external boundary** (see 012-idempotency-keys-prevent-double-processing.md) | Caller attaches a stable key; external system dedupes on that key server-side | Solves the "Kafka delivered twice, but external side-effect only happened once" gap that EOS cannot cover | Depends on external system | Medium (requires external API support or a dedup table you own) | Only as strong as the external system's key-matching window/TTL — if it expires the key before a very delayed retry arrives, dedup can still fail |

### When Full EOS (Idempotence + Transactions) Is the Right Choice

```
Use EOS (idempotent producer + transactions) when:
  ✓ Your pipeline is Kafka-to-Kafka (consume-transform-produce), e.g.
    Kafka Streams aggregations, joins, stateful transformations
  ✓ Duplicate output records would corrupt derived state (double-counted
    aggregates, double-applied balance changes in a KTable)
  ✓ You can tolerate the modest added latency (single-digit ms/commit)
    for a strong correctness guarantee
  ✓ All downstream consumers of your output topics are configured with
    isolation.level=read_committed (EOS provides nothing to a
    read_uncommitted consumer)

Skip full EOS when:
  ✗ Downstream consumers are read_uncommitted and can't be changed —
    you get idempotent-producer benefits but not transactional isolation
  ✗ Extremely latency-sensitive path where even a few ms of transaction
    coordination overhead is unacceptable, and at-least-once + idempotent
    downstream processing is achievable instead
  ✗ The pipeline's only output is a side effect OUTSIDE Kafka (an API
    call, a non-Kafka DB write) — EOS alone does not make that safe,
    you need idempotency keys at that boundary regardless

Always pair with external idempotency keys when:
  ✓ Any consumer in the pipeline calls a non-Kafka system as a side
    effect of processing a message (payment APIs, email/SMS sending,
    writes to a database Kafka doesn't manage transactionally)
```

---

## QUICK REFERENCE CARD

```
PRODUCER CONFIG:
  enable.idempotence=true              # PID + per-partition sequence dedup
  acks=all                             # required alongside idempotence
  max.in.flight.requests.per.connection<=5   # required for idempotence ordering guarantees
  transactional.id=<unique-stable-id>  # enables full transactions (implies idempotence)

TRANSACTION API (produce side):
  producer.initTransactions()
  producer.beginTransaction()
  producer.send(...)
  producer.sendOffsetsToTransaction(offsets, consumer.groupMetadata())  // EOS v2 / KIP-447
  producer.commitTransaction() / producer.abortTransaction()

CONSUMER CONFIG:
  isolation.level=read_committed       # hide records from aborted/open transactions
  enable.auto.commit=false             # offsets committed via the transaction instead

KAFKA STREAMS:
  processing.guarantee=exactly_once_v2 # one producer per StreamThread, shares transactional.id

KEY TIMEOUTS:
  transaction.timeout.ms=60000         # coordinator aborts a stuck TX after this
  producer.id.expiration.ms=604800000  # broker forgets an idle producer's PID after 7d

GUARANTEES SCOPE (the one thing to never forget):
  Kafka EOS = exactly-once WITHIN Kafka's own topics/offsets only.
  External side effects (API calls, non-Kafka writes) still need
  idempotency keys at THAT boundary → see 012-idempotency-keys-prevent-double-processing.md
```

---
