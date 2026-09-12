# CDC: Change Data Capture with Debezium
### How to stream every database change to Kafka without touching your application code

---

## PART 1 — THE STUDENT CONVERSATION

Imagine your PostgreSQL database is a busy kitchen. Orders come in all day — food is prepared, items are restocked, orders are updated. You want to know, in real-time, every single thing that happened in that kitchen.

One approach: hire a supervisor to watch every cook and shout out changes. That's your application code doing "dual writes" — whenever it updates the database, it also publishes an event to Kafka. This works, but it's fragile. What if the DB write succeeds and the Kafka write fails? Your data is out of sync. What if someone else updates the DB directly (a migration script, a DBA running a hotfix)? Those changes are invisible.

Better approach: read the kitchen's internal log. Every chef is already required to write down exactly what they did — it's the health and safety regulation of the restaurant. That log is the Write-Ahead Log (WAL) in PostgreSQL. Debezium reads this log and converts every INSERT, UPDATE, and DELETE into a Kafka event.

The WAL exists for crash recovery — PostgreSQL writes every change there BEFORE applying it to the actual table, so if the server crashes, it can replay the WAL to recover. Debezium taps into this same mechanism. It acts like a read replica: it connects to PostgreSQL as if it were another database replica, reads the WAL stream, and publishes decoded changes to Kafka.

The magic: you never touch your application code. Whether the change comes from your Java service, a migration script, a DBA hotfix, or a batch job — Debezium sees it all and streams it to Kafka.

---

## PART 2 — THE CDC ARCHITECTURE DIAGRAMS

### WAL to Kafka: The Debezium Flow

```
PostgreSQL (Source)          Debezium Connector            Kafka (Sink)
──────────────────           ──────────────────            ────────────

Application writes:
INSERT INTO users             Debezium maintains
  {id=42, name="Alice"}       a replication slot
  → WAL entry:                "debezium_slot"               Topic: postgres.public.users
    [LSN 001234]              (acts as a standby replica)
    op=INSERT                                               Event published:
    table=public.users        Reads WAL via                 {
    before: null              logical decoding              "op": "c",
    after:  {id:42,           plugin: pgoutput              "before": null,
             name:"Alice",    (built into PG 10+)           "after": {
             email:"a@b.com"}                                 "id": 42,
                              Converts WAL entry →           "name": "Alice",
                              Debezium change event          "email": "a@b.com"
                                                           },
UPDATE users                                               "source": {
  SET email="new@b.com"       Reads WAL:                     "db": "myapp",
  WHERE id=42                 [LSN 001235]                   "table": "users",
  → WAL entry:                op=UPDATE                      "lsn": "001234",
    op=UPDATE                 table=public.users             "ts_ms": 1704067200000
    before: {email:"a@b.com"}                              }}
    after:  {email:"new@b.com"}
                                                          Topic: postgres.public.users
                                                          {
                                                            "op": "u",
                                                            "before": { "id":42, "email":"a@b.com" },
                                                            "after":  { "id":42, "email":"new@b.com" }
DELETE FROM users                                         }
  WHERE id=42
  → WAL entry:                                            Topic: postgres.public.users
    op=DELETE                                             {
    before: {id:42,...}                                     "op": "d",
    after: null                                             "before": { "id":42, "name":"Alice" },
                                                            "after": null
                                                          }

op codes: "c" = create, "u" = update, "d" = delete, "r" = read (snapshot)
```

### CDC Consumers: One Source, Many Targets

```
PostgreSQL orders + products tables
          |
          | (WAL stream)
          v
    Debezium Connector
          |
          v
   Kafka topic: postgres.public.orders
          |
          ├──────────────────────────────────────────┐
          │                                          │
          v                                          v
  Elasticsearch Sync                         Redis Cache Invalidator
  ─────────────────                          ──────────────────────
  Consumer reads OrderUpdated event          Consumer reads event
  → upserts order in ES index                → DEL order:${orderId} from Redis
  → search index always reflects DB          → next read from DB populates cache
  Lag: ~100ms                                Lag: ~50ms

          |                                          │
          v                                          v
  Analytics Warehouse Loader               Audit Log Service
  ──────────────────────────               ─────────────────
  Consumer reads all events                Consumer writes all events
  → batch inserts into BigQuery            → append-only audit_log table
  → 15-min micro-batches                   → immutable compliance record
  → powers BI dashboards                   → "who changed what, when"

          |
          v
  Cross-service Replication
  ─────────────────────────
  Order service DB changes
  → Notification service gets OrderShipped event
  → Sends "Your order shipped!" email/SMS
  Without this: polling or tight coupling
```

### Snapshot Mode: Handling Existing Data

```
First time Debezium starts on an existing database with 10M rows:

Snapshot mode = "initial" (default):
  Phase 1: SNAPSHOT
    Debezium reads entire table (SELECT * FROM orders)
    Publishes each row as an "r" (read) event to Kafka
    Takes 30-60 minutes for 10M rows
    DB performance impact: similar to a full table scan

  Phase 2: STREAMING (after snapshot completes)
    Debezium switches to WAL streaming
    All changes from the snapshot LSN onward are captured
    No gaps, no data loss

Snapshot mode = "never":
  Skip snapshot, only capture changes from NOW
  Use when: you don't need historical data, or Elasticsearch is already seeded

Snapshot mode = "schema_only":
  Capture only schema (table structure), no data
  Then stream changes. Useful for Elasticsearch index setup.

Snapshot mode = "when_needed":
  Only snapshot if the replication slot doesn't exist
  Subsequent restarts skip snapshot
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### PostgreSQL Configuration

```sql
-- postgresql.conf (requires restart):
wal_level = logical          -- default is "replica", must change to "logical"
max_replication_slots = 10   -- one slot per Debezium connector
max_wal_senders = 10         -- concurrent WAL streaming connections

-- Create a replication slot (Debezium does this automatically, shown for clarity):
SELECT pg_create_logical_replication_slot('debezium', 'pgoutput');

-- Grant permissions to Debezium user:
CREATE USER debezium WITH REPLICATION LOGIN PASSWORD 'secret';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO debezium;
GRANT USAGE ON SCHEMA public TO debezium;

-- Optional: create publication (Debezium can do this, or you control it):
CREATE PUBLICATION debezium_pub FOR TABLE orders, products, users;
-- "FOR ALL TABLES" also works but captures everything
```

### Debezium Connector Configuration

```json
{
  "name": "postgres-orders-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres-primary.internal",
    "database.port": "5432",
    "database.user": "debezium",
    "database.password": "secret",
    "database.dbname": "ecommerce",
    "database.server.name": "postgres",
    "table.include.list": "public.orders,public.order_items,public.products",
    "plugin.name": "pgoutput",
    "snapshot.mode": "initial",

    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": "false",
    "transforms.unwrap.delete.handling.mode": "rewrite",

    "key.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",

    "heartbeat.interval.ms": "10000",
    "slot.name": "debezium"
  }
}

/* Topics auto-created (naming: serverName.schemaName.tableName):
   - postgres.public.orders
   - postgres.public.order_items
   - postgres.public.products
*/
```

### The Outbox Pattern (Solving Dual-Write Atomically)

```
Problem: How do you guarantee that a DB write AND a Kafka event happen atomically?
  - Write to DB succeeds, Kafka publish fails → event lost, downstream out of sync
  - Kafka publish succeeds, DB write fails → phantom event, data corruption

Dual-write (WRONG):
  // in OrderService.placeOrder():
  orderRepository.save(order);              // DB write
  kafkaTemplate.send("orders", event);      // Kafka write
  // If Kafka fails here: DB has order, Kafka doesn't. INCONSISTENT.

Outbox Pattern (CORRECT):
  // Same DB transaction:
  BEGIN;
    INSERT INTO orders (id, status, ...) VALUES (...);
    INSERT INTO outbox (aggregate_id, event_type, payload)
      VALUES ('order-42', 'OrderPlaced', '{"orderId":42,...}');
  COMMIT;
  // Atomically: either both succeed or both fail. No inconsistency.

  // Debezium CDC picks up the outbox INSERT automatically:
  postgres.public.outbox event → Kafka topic: "order-events"

  // Outbox table:
  CREATE TABLE outbox (
    id           UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    aggregate_id VARCHAR(50),
    event_type   VARCHAR(100),
    payload      JSONB,
    created_at   TIMESTAMP DEFAULT NOW()
  );

  // Debezium Outbox Router SMT:
  "transforms": "outbox",
  "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter",
  // Routes to topic based on event_type, uses aggregate_id as Kafka key
  // Ensures events for same order go to same partition (ordering guaranteed)
```

### Elasticsearch Consumer (Java/Spring)

```java
@Component
@KafkaListener(topics = "postgres.public.orders")
public class OrderSearchSyncConsumer {

    @Autowired
    private ElasticsearchOperations elasticsearchOps;

    public void consume(ConsumerRecord<String, String> record) {
        JsonNode event = objectMapper.readTree(record.value());
        String op = event.get("op").asText();

        switch (op) {
            case "c": case "u":   // create or update
                JsonNode after = event.get("after");
                OrderSearchDocument doc = mapToSearchDoc(after);
                elasticsearchOps.save(doc);
                break;
            case "d":             // delete
                String orderId = event.get("before").get("id").asText();
                elasticsearchOps.delete(orderId, OrderSearchDocument.class);
                break;
            case "r":             // snapshot read (initial sync)
                JsonNode row = event.get("after");
                OrderSearchDocument snapDoc = mapToSearchDoc(row);
                elasticsearchOps.save(snapDoc);
                break;
        }
    }
}
```

### Monitoring and Operational Concerns

```bash
# Critical metric: replication slot lag
# If consumer is slow, WAL accumulates in the replication slot
# PostgreSQL cannot reclaim WAL disk space until slot is consumed
# This is the #1 operational risk with CDC

SELECT slot_name, pg_size_pretty(pg_wal_lsn_diff(
    pg_current_wal_lsn(), restart_lsn)
) AS lag
FROM pg_replication_slots;

# Example output:
# slot_name   | lag
# debezium    | 2.3 GB   <-- consumer is 2.3GB behind, disk filling up!

# Alerting: if slot lag > 1GB, page on-call.
# Emergency: if consumer dies and lag grows uncontrolled:
#   - DROP the slot (loses events) to save the DB
#   - Then re-snapshot from Debezium

# Performance overhead:
# CDC (logical replication) adds ~3-8% overhead to PostgreSQL write throughput.
# Primary concern: wal_level=logical generates more WAL than replica.
# For write-heavy tables (100K writes/sec): benchmark first.

# Debezium throughput:
# Single connector: handles ~50K events/sec
# Event size: ~500 bytes average (before + after + metadata)
# At 50K events/sec: ~25MB/sec to Kafka — well within typical Kafka capacity
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "You have an orders table in PostgreSQL and you need to keep your Elasticsearch search index in sync with every order change — creates, updates, and deletes. How do you do it without dual-writes?"

**You (architect answer):**

> "The problem with dual-writes is atomicity — you can't guarantee that a DB write and an Elasticsearch write both succeed or both fail. A network blip between the two operations leaves you with inconsistent state, and no clean way to detect which records are out of sync.
>
> My solution is CDC with Debezium. I configure PostgreSQL with `wal_level = logical`, which enables logical replication. Debezium connects as a replica, reads the WAL stream, and for every INSERT, UPDATE, or DELETE on the orders table, it publishes a structured event to a Kafka topic — `postgres.public.orders`.
>
> A Kafka consumer subscribes to that topic and syncs Elasticsearch. For an 'update' event, it calls Elasticsearch upsert. For a 'delete' event, it calls delete by ID. Because this is asynchronous — typically 50-150ms behind the DB — search results are eventually consistent with the primary store.
>
> The key advantage: no matter where the DB change comes from — my application, a DBA running a hotfix, a migration script, a batch job — Debezium captures it. The application code never needs to know about Elasticsearch.
>
> One operational concern I'd flag: Debezium uses a replication slot to track its WAL position. If the Kafka consumer falls behind and the slot accumulates WAL, PostgreSQL can't reclaim disk space. I'd set an alert when slot lag exceeds 500MB, and I'd have a runbook ready to drop and re-create the slot (with a fresh snapshot) if the consumer dies for an extended period."

---

## PART 5 — DECISION FRAMEWORK

### CDC vs Polling vs Dual-Write

| Approach | How It Works | Consistency | Latency | Complexity | Misses Changes? |
|---|---|---|---|---|---|
| **Dual-write** | App writes to DB + Kafka | Not atomic | <10ms | Low | Yes (on failure) |
| **Polling** | Consumer runs `SELECT * WHERE updated_at > last_check` | Eventually consistent | 1-60s (poll interval) | Low | Yes (hard deletes invisible) |
| **CDC (Debezium)** | Reads WAL, no app changes needed | Eventually consistent | 50-150ms | Medium | No (captures all ops) |
| **Outbox Pattern** | App writes outbox row in same TX, CDC reads it | Atomic | 50-150ms | Medium | No |
| **Triggers (DB)** | DB trigger fires on change, inserts to queue | Eventual | <50ms | High (in DB) | No |

### When CDC is the Right Choice

```
Use CDC when:
  ✓ You cannot modify application code (legacy systems)
  ✓ Changes come from multiple sources (apps, migrations, DBA)
  ✓ You need hard deletes captured (polling misses these)
  ✓ Sub-second latency is needed (vs polling at intervals)
  ✓ Initial full sync + ongoing sync needed (snapshot mode)
  ✓ Building microservice data sync (source of truth → replicas)

Skip CDC when:
  ✗ Simple use case, polling works fine (check `updated_at` every minute)
  ✗ Write throughput is extremely high (>200K/sec) — WAL overhead matters
  ✗ Your DB doesn't support logical replication (some MySQL configs, SQLite)
  ✗ Team has no Kafka experience — polling is simpler to operate

Outbox pattern over raw CDC when:
  ✓ You want event schema control (not raw DB row format)
  ✓ You need routing logic (different events to different Kafka topics)
  ✓ You want to avoid publishing internal DB schema to downstream consumers
```

---

## QUICK REFERENCE CARD

```
POSTGRESQL SETUP:
  postgresql.conf: wal_level = logical
  Grant REPLICATION privilege to Debezium user

DEBEZIUM CONNECTOR KEY CONFIG:
  connector.class: io.debezium.connector.postgresql.PostgresConnector
  plugin.name: pgoutput
  snapshot.mode: initial | never | schema_only
  table.include.list: schema.table1,schema.table2

KAFKA TOPIC NAMING:
  {server.name}.{schema}.{table}
  e.g.: postgres.public.orders

EVENT op CODES:
  "c" = create (INSERT)
  "u" = update (UPDATE)
  "d" = delete (DELETE)
  "r" = read   (snapshot)

OUTBOX PATTERN:
  1. Same DB TX: INSERT orders + INSERT outbox
  2. CDC captures outbox INSERT
  3. Debezium Outbox Router SMT routes to correct Kafka topic
  4. No dual-write risk

SLOT LAG MONITORING:
  SELECT pg_size_pretty(pg_wal_lsn_diff(
    pg_current_wal_lsn(), restart_lsn)) AS lag
  FROM pg_replication_slots;
  Alert if > 500MB, emergency if > 5GB
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Whenever an interview asks "how do you keep service B in sync with service A's database" — CDC is the answer. It solves the dual-write problem, captures all changes regardless of source, and is the foundation of data pipelines at Netflix, LinkedIn, and Uber.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **07 — Payment** | CDC from the PostgreSQL accounts table streams balance changes to Kafka in real-time. The fraud detection service consumes these events — it doesn't need to poll the database or be tightly coupled to the payment service. Real-time balance changes arrive in under 150ms for risk scoring. |
| **09 — E-Commerce** | CDC from orders/products tables syncs changes to Elasticsearch (product search reflects latest inventory and pricing) and Redis (cache invalidation on stock changes). When a product goes out of stock, the CDC event triggers cache invalidation and search index update — no application code change needed. |
| **15 — Distributed Logging** | CDC from application databases generates audit events automatically. Every DB change (user created, permissions modified, config updated) flows to the centralized audit log topic via CDC — without requiring every application team to implement audit logging manually. |

**Architect's one-liner for the interview:**
*"CDC with Debezium reads PostgreSQL's Write-Ahead Log — the same mechanism used for crash recovery and replication — and publishes every INSERT, UPDATE, and DELETE as a Kafka event, solving the dual-write atomicity problem without changing a single line of application code."*

---
