# Interview Guide: The Dual-Write Problem in Event-Driven Microservices

## 🗣️ The Interview Scenario

> "You told me your Order service writes to its database *and* publishes an event to Kafka so downstream services (billing, notifications) can react. Walk me back one step — how do you guarantee the DB write and the event publish are never inconsistent with each other? What happens if one succeeds and the other fails?"

This is almost never asked directly as "what is the dual-write problem?" Instead, interviewers lead you there through **Saga pattern** discussion, then pull the rug: *"okay, but how does step 1 (local DB write + event publish) actually stay consistent?"* Recognizing this pivot is itself a signal of seniority.

## 🏗️ Architect's Explanation (For a New Developer)

Imagine you're at a wedding, and you need to (1) write the guest's name in the physical guestbook and (2) shout their name so the DJ announces them. These are **two completely separate systems** — a paper book and a human ear. If you write the name in the book but the DJ never hears you, the guest is registered but never announced. If you shout their name but never write it in the book, they get announced but there's no record.

That's exactly the **dual-write problem**: a service needs to persist a change in **two independent systems** — typically a database and a message broker (Kafka, RabbitMQ) — and there is no built-in mechanism to guarantee both succeed or both fail together. One can succeed while the other fails, leaving your system in a permanently inconsistent state, because nothing rolls the other one back automatically.

The obvious first instinct — "let's wrap both in a distributed transaction using Two-Phase Commit (2PC)" — turns out to be a trap, and understanding *why* it fails is the heart of this topic.

## 📊 Visualize It

```
THE PROBLEM: Two independent systems, no shared transaction

   Service A
   ┌─────────────┐        1. write row           ┌──────────┐
   │ create      │───────────────────────────────▶│ Database │
   │ invoice     │                                 └──────────┘
   │             │        2. publish event         ┌──────────┐
   │             │───────────────────────────────▶│  Kafka   │
   └─────────────┘                                  └──────────┘

   Case A: DB write succeeds, publish fails → downstream services never know
   Case B: publish succeeds, DB write fails  → downstream services react to
            something that was never actually persisted
   Either way = inconsistent system state, nothing auto-rolls-back
```

```
THE FIX (Transactional Outbox): one atomic local transaction covers both facts

   BEGIN TXN
     INSERT INTO invoice (...)         ─┐
     INSERT INTO outbox_event (...)    ─┤── same DB, same transaction
   COMMIT                              ─┘
                     │
                     ▼
        Poller/Publisher reads outbox → publishes to Kafka (async, retried)
```

## 🔧 Deep Dive: How It Actually Works

### Why Two-Phase Commit (2PC) is *not* the answer

2PC uses a coordinator that sends `prepare` to all participants, waits for all "yes," then sends `commit` to all. It sounds perfect for exactly this problem, but it fails for two concrete reasons:

1. **Heterogeneous systems, poor support.** A dual-write spans a relational DB *and* a message broker. Many message brokers (Kafka included) **do not support the 2PC/XA protocol** at all, so there's often no participant-side implementation to even attempt this with.
2. **Latency and availability.** 2PC requires *every* participant to respond to `prepare` before anyone commits — with 3-4 participants this round-trip adds real latency. Worse, **if the coordinator itself crashes** mid-protocol, participants are left blocked in an uncertain state until it recovers. This is precisely why the industry moved toward Saga (local transactions + async events) instead of distributed transactions for microservices.

### Solution 1 — Transactional Outbox Pattern

The core idea: never try to write to two systems at once. Instead, write the **event as a row in your own database**, in the *same local transaction* as your actual business write.

```
BEGIN TRANSACTION
  INSERT INTO user (...)                    -- the real business write
  INSERT INTO outbox_event (user_created, payload, status='pending')
COMMIT
```

Because both inserts are in one local ACID transaction, they succeed or fail together — no partial state is possible.

## Transactional Outbox (Sequence Diagram)

```text
Service (OrderService) -> Local Database        : BEGIN TXN
Service (OrderService) -> Local Database        : INSERT business row (e.g. order)
Service (OrderService) -> Local Database        : INSERT outbox_event (status=pending)
Service (OrderService) -> Local Database        : COMMIT
    [Note: both writes succeed or fail together (ACID)]

    loop (poll, repeats continuously)
      Poller/Publisher -> Local Database        : SELECT unpublished outbox events
      Local Database --> Poller/Publisher       : pending rows
      Poller/Publisher -> Kafka/Message Broker  : publish event
      Kafka/Message Broker --> Poller/Publisher : ack
      Poller/Publisher -> Local Database        : mark event published (or delete)
    end loop

Kafka/Message Broker -> Downstream Consumer     : deliver event
Downstream Consumer -> Downstream Consumer      : idempotency check (business event ID) before acting
```

*(Interactive Mermaid version: [mermaid-diagrams.md](mermaid-diagrams.md))*

A separate **poller/publisher process** continuously polls the outbox table for unpublished events, publishes them to the message broker, and marks them published (or deletes them) on success.

**Challenges you must proactively raise with the interviewer:**
- **Extra engineering effort** — you now own a poller/publisher service.
- **Publish delay** — there's a gap between the commit and the actual publish (the poller works asynchronously; could be milliseconds or minutes).
- **Duplicate publishing** — a poller might crash after publishing but before marking the row as published, and republish on restart. **Fix:** Kafka producer idempotency — set `enable.idempotence=true`; each producer gets a `producerId` + monotonically increasing `sequenceNumber` per message, so the broker can detect and drop true duplicates from the *same* producer.
- **Multiple pollers = idempotency at the consumer, not just the producer.** If you run **two poller instances**, each gets its own `producerId`, so Kafka's built-in idempotence can't detect that `M1` from poller-1 and `M1` from poller-2 are semantically the same message. The real fix is **consumer-side idempotency**: attach a unique business event ID to every message and have the consumer track "already processed" IDs (e.g., an idempotency key table) before acting.
- **Ordering issues.** Kafka **only guarantees order within a single partition written by a single producer.** With multiple pollers/producers writing to the same partition, or the same producer writing across multiple partitions, order is **not guaranteed**. If strict ordering matters (e.g., create → update → delete must be processed in that sequence), you need **Kafka Streams** (which can re-partition/reorder) or a similar stream-processing layer.
- **Retry + dead-lettering.** Build exponential backoff retries in the publisher; if all retries are exhausted, either flip the row back to `pending` for a future retry pass, or move it to a `failed_events` table for manual/automated remediation.
- **Outbox table growth.** Clean up published rows regularly — either delete immediately after successful publish, or run a periodic batch cleanup job.

### Solution 2 — Listen to Yourself Pattern

A variation of Transactional Outbox. Instead of writing the *real* business row and the event in the same transaction, you write **only the event** into the outbox first (e.g., `UserCreationEvent`), commit, and let the poller publish it to the broker. Critically, **the originating service itself is also a consumer** of that event — its own "demon" (background listener) process consumes the event and *then* performs the actual DB write.

- This has all the same challenges as Transactional Outbox, **plus one extra**: **a GET request can arrive before the event has been consumed and written to the real table.** If a client immediately reads right after the POST, the row may not exist yet.
- **Fix:** Write-through cache. The originating write path also writes the payload into a cache (e.g., Redis) synchronously at request time. GET requests check the cache first; if the underlying table isn't populated yet, the cache still serves correct data until the async write completes (and the cache eventually expires or gets superseded by the real DB row).

### Solution 3 — Transaction Log Tailing (Change Data Capture)

This approach **removes the need for an outbox table entirely**. Every relational database already writes a **transaction log** (WAL in Postgres, binlog in MySQL) for every insert/update/delete. A **Change Data Capture (CDC)** tool — the transcript names **Debezium** — tails this log file and turns each detected DB change into a published event, without any application-level outbox code. Some databases (e.g., CockroachDB) have **built-in CDC** so you don't even need an external tool.

**Challenges:**
- **Duplicates** — a CDC tool can emit the same change event twice; you still need consumer-side idempotency.
- **Ordering** — running multiple CDC tool instances (for scale) turns them into multiple producers, so the same Kafka ordering caveats from Solution 1 apply; Kafka Streams (or similar) is again the fix for strict ordering.
- **Higher latency** — end-to-end latency is bound by how fast the *database itself* flushes to its log file; some databases batch log writes (e.g., "flush every 100 writes"), so your event latency depends on DB internals you don't fully control.
- **Noise / over-publishing** — if you don't filter the CDC tool precisely (e.g., "only inserts on table X"), you'll get unwanted update/delete events too and need to filter them out explicitly.

### Kafka ordering — the precise rule to state in an interview

- **One producer + one partition → order is guaranteed** (Kafka preserves the write order within that partition).
- **Multiple producers into the same partition, or one producer across multiple partitions → order is NOT guaranteed.**
- Real ordering guarantees across multiple producers/partitions require **Kafka Streams** style repartitioning/reordering, or consumer-side buffering + sorting.

## 🔥 Real Production Incident & Fix

**What broke:** An e-commerce team's `OrderService` wrote the order row to Postgres and then called `kafkaProducer.send(orderCreatedEvent)` in the same request handler — two separate operations, no shared transaction. During a database failover event, the Postgres write succeeded but the subsequent Kafka publish call timed out and threw, and the exception was swallowed by a generic `catch` block that only logged a warning.

**How it was detected:** The Billing service (a Kafka consumer) started showing a steadily growing gap between "orders created" (from a nightly DB count) and "invoices generated" (from its own event-driven pipeline) — roughly 3% of orders were never billed. This was caught by a **reconciliation job** comparing row counts between `orders` and `invoices` tables, and confirmed via **Kafka consumer lag dashboards** (Burrow/Confluent Control Center) showing no anomaly on the consumer side — meaning the events genuinely were never published, not just unconsumed.

**Root cause:** Classic dual-write: DB write and Kafka publish were two independent I/O calls with no atomicity between them, and a swallowed exception hid every silent failure for weeks.

**The fix:** The team implemented the **Transactional Outbox pattern**. `OrderService` now inserts the order row **and** an `outbox_event` row in one Postgres transaction. A dedicated poller (built with Debezium-style polling against the outbox table) publishes to Kafka with retries and exponential backoff, and failed-after-retries events land in a `failed_events` table with alerting on non-empty state. The reconciliation gap closed to zero, and the team added a Grafana panel tracking outbox table backlog size as an early-warning signal.

```
BEFORE: two independent calls, no atomicity, silent failure possible
   OrderService ──DB write (success)──▶ orders table
                ──Kafka publish (fails, swallowed)──X  Billing never notified

AFTER: one atomic local transaction + reliable async publisher
   OrderService ──BEGIN TXN──▶ orders + outbox_event──COMMIT
                                     │
                          Poller (retry + backoff) ──▶ Kafka ──▶ Billing
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why can't we just use 2PC across the DB and Kafka?**
Because Kafka (and most modern message brokers) don't support the XA/2PC protocol as a participant, and even where a distributed transaction protocol is technically available, it introduces synchronous blocking across all participants and is vulnerable to coordinator crashes leaving the system in an indeterminate, blocked state — unacceptable latency and availability trade-offs for a microservices architecture built around independent scaling.

**Q2: How do you prevent the poller in the Transactional Outbox pattern from publishing the same event twice?**
Enable producer idempotence on the Kafka client (`enable.idempotence=true`), which attaches a producer ID and monotonically increasing sequence number to each message so the broker can drop true duplicates from the same producer. But if you run multiple poller instances (common for scale/HA), that alone isn't enough — you need consumer-side idempotency keyed on a unique business event ID, since two different producer IDs publishing the "same" logical event look distinct to Kafka.

**Q3: Does Kafka guarantee message ordering? Under what conditions?**
Kafka guarantees order only within a single partition written by a single producer. If you have multiple producers (e.g., multiple poller instances) or a single producer spreading messages across multiple partitions, ordering is not guaranteed and you need a stream-processing layer like Kafka Streams to repartition/reorder, or consumer-side buffering and sorting logic.

**Q4: What's the practical difference between Transactional Outbox and Listen-to-Yourself?**
In Transactional Outbox, the real business row and the event are written together in the same local transaction, so the data is immediately query-able. In Listen-to-Yourself, only the event is written first; the actual business row is written later when the service consumes its own published event — which means there's a window where a GET could return "not found" for data that was just accepted, and you typically need a write-through cache to paper over that window.

**Q5: When would you choose Change Data Capture (CDC/log tailing) over an explicit outbox table?**
CDC is attractive when you don't want to add outbox-table plumbing to every service or you want a database-agnostic, less invasive way to capture changes — tools like Debezium tail the DB's native transaction log. The trade-off is less control over exactly what gets published (you must filter carefully to avoid noise), latency tied to how fast the DB flushes its log (some DBs batch log writes), and the same duplicate/ordering challenges as any other event-publishing approach.

**Q6: How do you handle an event that fails to publish even after retries?**
Build exponential backoff retries into the poller/publisher first. If all retries are exhausted, either reset the outbox row's status back to "pending" so a future poll cycle retries it, or move it into a dedicated `failed_events` table for manual inspection or automated remediation — the choice depends on how your outbox schema tracks event status.

## 🔑 Key Takeaway

The dual-write problem exists because writing to a database and publishing to a message broker are two independent operations with no shared transaction — and the fix is never "make them atomic across systems" (2PC doesn't work here); it's "make the write atomic within one system" via the Transactional Outbox pattern, then reliably relay from there with idempotency and ordering safeguards.
