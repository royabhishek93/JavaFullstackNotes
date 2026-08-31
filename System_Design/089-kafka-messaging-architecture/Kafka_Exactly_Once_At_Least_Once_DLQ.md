# Kafka Delivery Guarantees & Dead Letter Queues
### At-most-once, at-least-once, exactly-once — and what to do when processing fails permanently

---

## PART 1 — THE STUDENT CONVERSATION

Imagine you're shipping packages. Three different courier services give you three very different guarantees.

**At-most-once** — you drop the package in a public mailbox. If the postal truck crashes, the package is gone. You never know. It arrives zero or one times. You chose speed over reliability. Fine for: access logs, metrics pings, telemetry. Catastrophic for: payments.

**At-least-once** — you use registered mail with a return receipt. If no receipt arrives within 3 days, you send another copy. The recipient might get two identical packages. They need to handle duplicates: "did I already process this?" This is what most Kafka applications do by default. Requires idempotent consumers.

**Exactly-once** — you use a specialized courier with a tracking system that atomically confirms delivery. The courier will never deliver twice AND will never lose it. Sounds perfect. But this courier charges 30% more and is slower — because they need to coordinate between the sender, the Kafka broker, and the consumer in a two-phase-commit-like protocol. Use only when the cost of a duplicate is catastrophic (payments, seat reservations).

**Dead Letter Queue (DLQ)** — imagine your recipient keeps refusing the package: wrong address format, damaged contents, signature mismatch. After 3 attempts, instead of blocking your entire delivery truck, you put the package in a "problem shelf" for a human to review later. That's a DLQ. Without it, one bad message can permanently block an entire Kafka partition — nothing else gets through.

---

## PART 2 — DELIVERY GUARANTEE DIAGRAMS

### At-Least-Once: The Crash Before Commit Scenario

```
Normal flow (happy path):
  Producer → Kafka → Consumer → process() → commitSync() → DONE
                                  offset stored in __consumer_offsets

Crash scenario:
  Producer → Kafka → Consumer → process() → [POD CRASHES]
                                              ↑
                                              commit never happened
                                              offset NOT saved

  Consumer restarts:
    Kafka: "last committed offset for this group = 1499"
    Consumer receives messages 1499, 1500, 1501 again
    process() runs AGAIN for message 1500
    Side effect (charge card, send email) happens TWICE

  Fix: idempotent consumer
    Before processing: "did I already handle message_id=X?"
    Check DB / Redis / dedup cache → skip if already done
    Then process → then commit
```

### Exactly-Once: Kafka Transactions

```
Producer side (transactional write):

  initTransactions()          ← one-time setup with unique transactional.id
  |
  beginTransaction()          ← marks start of atomic operation
  |
  send(record to topic-A)     ← write to output topic
  |
  sendOffsetsToTransaction()  ← atomically commit consumer input offset
  |
  commitTransaction()         ← ATOMIC: both writes land or both roll back
      |
      broker crashes here?
      → transaction rolled back
      → record NOT visible in topic-A
      → consumer offset NOT advanced
      → consumer replays input, retries transaction
      → result: record appears ONCE, offset advances ONCE

Isolation level on consumer side:
  props.put("isolation.level", "read_committed");
  // Only reads messages from committed transactions
  // Transactional messages in-flight are invisible until committed
```

### DLQ Flow: Retry Backoff Then Surrender

```
Message arrives: payment_id=789, amount=$1500

  Attempt 1: process() → PaymentGatewayException (timeout)
             wait 1s (exponential backoff starts)

  Attempt 2: process() → PaymentGatewayException (still down)
             wait 2s

  Attempt 3: process() → PaymentGatewayException (still down)
             MAX RETRIES EXCEEDED

  → publish to DLQ topic: payments-dlt
  → commitSync() for original message  ← partition unblocked, moves on
  → message 790 is now processed

  payments-dlt topic:
    message: {original_payload, exception_type, retry_count, timestamp}
    Consumed by: alerting system, human review dashboard, auto-remediation
    Human fixes gateway config → republishes message to payments topic
```

### Without DLQ: Partition Blocked Forever

```
Message 500: bad payload (null account_id)
  → process() throws NullPointerException
  → retry... retry... retry...
  → never committed
  → message 501, 502, ... NEVER PROCESSED

  Entire partition is STUCK.
  Every consumer group monitoring tool shows lag growing to infinity.
  Fix: restart consumer → same message 500 → same crash → stuck again.

With DLQ:
  Message 500 → 3 retries → DLQ → committed → message 501 processed
  Partition lag stays near zero.
```

---

## PART 3 — IMPLEMENTATION

### Producer: Idempotent and Transactional

```java
// ── IDEMPOTENT PRODUCER (prevents duplicate sends on retry) ──────────────────
// Kafka assigns a sequence number to each message.
// If broker receives duplicate (same producer epoch + seq number) → deduped automatically.

Properties idempotentProps = new Properties();
idempotentProps.put("bootstrap.servers", "kafka:9092");
idempotentProps.put("enable.idempotence", "true");       // acks=all, retries=MAX_INT,
                                                          // max.in.flight.per.connection=5
// That's it. Idempotent by default for Kafka 3.0+


// ── TRANSACTIONAL PRODUCER (exactly-once, read-process-write) ────────────────
Properties txProps = new Properties();
txProps.put("bootstrap.servers", "kafka:9092");
txProps.put("transactional.id", "payment-processor-instance-1"); // unique per producer instance
txProps.put("enable.idempotence", "true");                        // required for transactions

KafkaProducer<String, String> producer = new KafkaProducer<>(txProps);
producer.initTransactions();   // one-time, registers with broker's transaction coordinator

// In your processing loop:
try {
    producer.beginTransaction();

    // Write output record
    producer.send(new ProducerRecord<>("processed-payments", key, enrichedPayload));

    // Atomically advance the consumer offset (so input is not reprocessed)
    Map<TopicPartition, OffsetAndMetadata> offsets = Map.of(
        new TopicPartition("raw-payments", partition),
        new OffsetAndMetadata(offset + 1)
    );
    producer.sendOffsetsToTransaction(offsets, consumer.groupMetadata());

    producer.commitTransaction();   // atomic: output written + input offset advanced

} catch (ProducerFencedException | OutOfOrderSequenceException e) {
    // Fatal: another instance took over this transactional.id
    // This instance must shut down
    producer.close();
    throw e;
} catch (KafkaException e) {
    // Transient error: roll back and retry
    producer.abortTransaction();
    // retry the whole unit
}
```

### Consumer: DLQ with Spring Kafka

```java
// Spring Kafka makes DLQ/retry trivial via @RetryableTopic

@Service
public class PaymentConsumer {

    @KafkaListener(topics = "payments", groupId = "payment-processors")
    @RetryableTopic(
        attempts = "3",                         // 1 original + 2 retries
        backoff = @Backoff(delay = 1000, multiplier = 2.0),  // 1s, 2s backoff
        dltTopicSuffix = "-dlt",               // DLQ topic = payments-dlt
        autoCreateTopics = "true"
    )
    public void process(Payment payment, @Header(KafkaHeaders.RECEIVED_TOPIC) String topic) {
        paymentService.charge(payment);        // throws on failure
    }

    // Receives from payments-dlt automatically
    @DltHandler
    public void handleDlt(Payment payment, @Header(KafkaHeaders.RECEIVED_TOPIC) String topic) {
        log.error("DLQ: failed payment after all retries. topic={}, paymentId={}",
                  topic, payment.getId());
        alertingService.page("PAYMENT_DLQ_ALERT", payment);
        // Optionally: store in dead_letter_payments DB table for human review
    }
}
```

### Manual DLQ (without Spring Kafka)

```java
private static final int MAX_RETRIES = 3;

void processWithDLQ(ConsumerRecord<String, Payment> record) {
    int attempts = 0;
    while (attempts < MAX_RETRIES) {
        try {
            paymentService.charge(record.value());
            consumer.commitSync();
            return;
        } catch (RetryableException e) {
            attempts++;
            Thread.sleep((long) Math.pow(2, attempts) * 1000); // exponential backoff
        } catch (NonRetryableException e) {
            // Bad data — no point retrying
            publishToDLQ(record, e);
            consumer.commitSync();
            return;
        }
    }
    publishToDLQ(record, new MaxRetriesExceededException());
    consumer.commitSync();
}

void publishToDLQ(ConsumerRecord<String, Payment> record, Exception cause) {
    ProducerRecord<String, String> dlqRecord = new ProducerRecord<>(
        record.topic() + "-dlt",
        record.key(),
        toJson(Map.of(
            "original_payload", record.value(),
            "exception", cause.getClass().getName(),
            "message", cause.getMessage(),
            "original_partition", record.partition(),
            "original_offset", record.offset(),
            "timestamp", Instant.now().toString()
        ))
    );
    dlqProducer.send(dlqRecord).get(); // synchronous — ensure DLQ write before commit
}
```

### Exactly-Once Performance Cost

```
Benchmark: same hardware, same message size, same consumer logic

  at-least-once (acks=all, no transactions):  ~500K msg/s
  exactly-once (transactional):               ~350K msg/s

  ~30% throughput reduction due to:
    - 2-phase commit coordination with transaction coordinator
    - Extra metadata writes per transaction
    - read_committed isolation adds read latency

  Verdict: pay the 30% cost only for payments, reservations, financial events.
           Don't pay it for notifications, analytics, feed generation.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your payment processing Kafka consumer sometimes processes the same payment twice after a pod restart. How do you fix this?"

**You (architect answer):**

> "This is a classic at-least-once problem. The consumer processes the payment, the pod crashes before calling commitSync(), and when it restarts, Kafka replays from the last committed offset. The payment processes again.
>
> There are two layers of fix, and I'd implement both.
>
> Layer one: idempotency in the consumer. Before charging the payment gateway, I check a dedup store — typically Redis with a TTL of 24 hours or a payments DB table — for 'has this payment_id already been processed successfully?' If yes, skip and commit. This is the most important fix and works regardless of delivery semantics.
>
> Layer two: for a payment system, I'd upgrade to exactly-once using Kafka transactions. The producer atomically writes the 'payment-processed' event to the output topic AND commits the consumer offset in one transaction. If the pod crashes mid-transaction, both roll back. The consumer replays, but the idempotency check in layer one catches it anyway — two layers of safety.
>
> I'd also add a DLQ for payments that fail after 3 retries — gateway timeouts, card declines that can't be retried. Without a DLQ, one bad payment blocks the entire partition. The DLQ message carries the original payload plus exception context so a human or automated system can review and reprocess.
>
> Monitoring: alert on DLQ topic receiving any messages (each one is a failed payment), and alert on consumer lag > 1000 for the payments topic."

---

## PART 5 — DECISION FRAMEWORK

### Which Delivery Guarantee for Which Use Case

| Use Case | Guarantee Needed | Why | Cost Acceptable? |
|----------|-----------------|-----|-----------------|
| Payment processing | Exactly-once | Duplicate charge = critical bug, financial loss | Yes — 30% throughput hit is worth it |
| Seat/ticket reservation | At-least-once + idempotent | Duplicate reservation must be caught in app logic, not Kafka | Yes — idempotency check is cheap |
| Email/push notification | At-least-once | Duplicate notification is annoying but not catastrophic | No need for exactly-once |
| Analytics / clickstream | At-most-once or at-least-once | Losing a few events doesn't change aggregate stats meaningfully | At-most-once is fine here |
| Audit log | At-least-once | Must not lose events; duplicates can be deduplicated on read | No need for exactly-once |
| Inventory deduction | Exactly-once or at-least-once + idempotent | Duplicate deduction oversells stock | Depends on transaction volume |
| Leaderboard score update | At-least-once + idempotent SET | Use SET not INCR — duplicate update sets same value | At-least-once is fine |

### When to Use a DLQ

```
Use DLQ when ANY of these are true:
  ✓ Processing can fail due to bad data (malformed payload, null fields)
  ✓ Downstream service can be permanently unavailable
  ✓ You need an audit trail of failed messages for compliance
  ✓ The topic is business-critical (payments, orders, reservations)

Skip DLQ when:
  - Messages are truly ephemeral (metrics, telemetry) and loss is OK
  - You have a universal schema with validation at producer side

DLQ sizing rule:
  - Separate DLQ topic per source topic: payments-dlt, notifications-dlt
  - Retention: 7-30 days (enough for human review + auto-remediation)
  - Consumer lag alert on DLQ: any lag > 0 should page on-call for payments
```

---

## QUICK REFERENCE CARD

```
AT-LEAST-ONCE (default):
  Config: enable.auto.commit=false + commitSync() after processing
  Risk:   duplicate processing on crash before commit
  Fix:    idempotent consumer (dedup by message_id in Redis/DB)

EXACTLY-ONCE:
  Producer: transactional.id + enable.idempotence=true
  Consumer: isolation.level=read_committed
  Pattern:  beginTx → send output → sendOffsetsToTransaction → commitTx
  Cost:     ~30% throughput reduction

AT-MOST-ONCE:
  Config: commitSync() BEFORE processing (or enable.auto.commit=true)
  Risk:   lost messages on crash
  Use:    telemetry, metrics, non-critical analytics only

DLQ SETUP (Spring Kafka):
  @RetryableTopic(attempts="3", backoff=@Backoff(delay=1000, multiplier=2))
  → auto-creates topic-dlt after exhausting retries
  @DltHandler → receives failed messages for alerting/storage

IDEMPOTENT PRODUCER:
  props.put("enable.idempotence", "true")
  → broker deduplicates retried messages automatically
  → does NOT prevent consumer-side duplicates on crash

DELIVERY CHOICE CHEATSHEET:
  payments, bookings          → exactly-once or at-least-once + idempotent
  notifications, feeds        → at-least-once (idempotent check optional)
  analytics, logs, telemetry  → at-most-once or at-least-once
  anything with DLQ           → at-least-once (DLQ handles poison pills)
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** The delivery guarantee you choose is a contract — pick it based on what failure mode is cheaper: a duplicate or a miss. For money, duplicates are catastrophic. For notifications, they're just annoying. Design accordingly.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **03 — Notification System** | At-least-once is the right call — a duplicate push notification is annoying, not catastrophic. Idempotency check: "has notification_id=X already been sent?" stored in Redis with 24h TTL. DLQ for malformed payloads (bad device token, null user_id) — these will never succeed and must not block the partition. |
| **07 — Payment Processing** | Exactly-once is mandatory. Duplicate payment charge is a P0 incident. Transactional Kafka + idempotency key in the payments DB (unique constraint on payment_id). DLQ for payments rejected by the gateway (invalid card, fraud hold) — needs human review or automated retry after card update. |
| **11 — Ticket Booking** | At-least-once with idempotent seat reservation. Consumer checks "is reservation_id=X already committed in the seats table?" before executing. DLQ for reservations where the seat_id no longer exists (event cancelled mid-booking) — needs refund workflow trigger. |
| **13 — Real-Time Leaderboard** | At-least-once for score events is acceptable. Use idempotent SET (not INCR) in Redis: store the latest known score per user and SET it, don't blindly add. Duplicate event sets the same score again — harmless. DLQ for malformed score events (non-numeric score, unknown leaderboard_id). |

**Architect's one-liner for the interview:**
*"At-least-once plus idempotency covers 90% of use cases at minimal cost — reserve exactly-once for the narrow class of financial operations where a duplicate is indistinguishable from fraud."*
