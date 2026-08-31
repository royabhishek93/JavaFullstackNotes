# CQRS and Event Sourcing
### Why the world's most reliable financial systems never UPDATE a row

---

## PART 1 — THE STUDENT CONVERSATION

### CQRS — Command Query Responsibility Segregation

Picture a bank with two counters. Counter A is the teller window: you walk up, hand over cash, and a transaction happens. Counter B is the customer service desk: you ask "what's my balance?" and they look it up.

These counters don't share the same queue. The customer service desk has its own up-to-date snapshot of every account balance — a denormalized summary optimized purely for answering questions fast. They don't run through your full transaction history to calculate your balance every time you ask. The teller counter is where the actual work happens — it validates your transaction, applies business rules, and updates the authoritative records.

That's CQRS. The "write side" (Commands) and the "read side" (Queries) are completely separate:
- Write side: handles validation, business rules, ACID guarantees. Normalized data. Optimized for consistency.
- Read side: handles queries fast. Denormalized, pre-joined, pre-aggregated. Optimized for read performance.

They stay in sync via events published from the write side.

### Event Sourcing

Now a different concept, often used alongside CQRS but independent of it.

Your bank doesn't store "current balance = $1,234." If it did, and someone asked "what was my balance three months ago?" — the answer would be gone. Instead, your bank stores every transaction, forever:
- Jan 1: deposit $500
- Jan 15: withdraw $200
- Feb 3: deposit $934

Your current balance IS the sum of all those events. If you dispute a charge, the full audit trail exists. You can replay history to any point in time. Nothing is ever deleted.

That's Event Sourcing. Instead of storing current state, you store the sequence of events that produced that state. Current state is DERIVED by replaying events.

The combination (CQRS + Event Sourcing) is powerful: the write side stores events (immutable log), multiple read sides can be built from the same event stream — each read model optimized for a different query pattern.

---

## PART 2 — THE ARCHITECTURE DIAGRAMS

### CQRS: Separate Write and Read Models

```
USER REQUEST: "Place an order for 2 blue shoes at $99 each"
                              |
                              v
                    ┌─────────────────────┐
                    │   API Gateway        │
                    └─────────────────────┘
                              |
              ┌───────────────┴───────────────────┐
              │                                   │
              v                                   v
    ┌─────────────────────┐           ┌─────────────────────┐
    │  WRITE SIDE         │           │  READ SIDE          │
    │  (Command Model)    │           │  (Query Model)      │
    │                     │           │                     │
    │  POST /orders       │           │  GET /orders?user=42│
    │  OrderService       │           │  OrderReadService   │
    │                     │           │                     │
    │  - Validates stock  │           │  - No joins needed  │
    │  - Charges payment  │           │  - Pre-denormalized │
    │  - Applies rules    │           │  - Can use any store│
    │                     │           │                     │
    │  PostgreSQL         │           │  Elasticsearch      │
    │  (normalized, ACID) │           │  (denormalized)     │
    │                     │           │                     │
    │  orders             │           │  order_view {       │
    │    id, user_id,     │           │    order_id,        │
    │    status, total    │           │    product_name,    │
    │  order_items        │           │    price,           │
    │    order_id,        │           │    status,          │
    │    product_id, qty  │           │    user_name,       │
    │  products           │           │    delivery_address │
    │    id, name, price  │           │  }                  │
    └─────────────────────┘           └─────────────────────┘
              |                                   ^
              |                                   |
              v                                   |
    ┌─────────────────────┐                       |
    │  Kafka Topic        │                       |
    │  "order-events"     │─── event consumer ────┘
    │                     │    (updates read model)
    │  OrderPlaced        │
    │  OrderShipped       │
    │  OrderDelivered     │
    └─────────────────────┘

Write side: INSERT + publish event (ACID, ~5ms)
Read side update: async, via Kafka consumer (~100ms delay)
Read query: single document lookup, no JOINs (~5ms)
```

### Event Sourcing: The Immutable Event Log

```
Command received: "User 42 places order: 2x BluShoes @ $99"

TRADITIONAL APPROACH (mutable state):
  orders table:
  ┌────┬────────┬──────────┬───────┐
  │ id │ user   │ status   │ total │
  ├────┼────────┼──────────┼───────┤
  │ 42 │ user42 │ PLACED   │ $198  │  ← INSERT
  │ 42 │ user42 │ PAID     │ $198  │  ← UPDATE status
  │ 42 │ user42 │ SHIPPED  │ $198  │  ← UPDATE status
  └────────────────────────────────┘
  Question: "When was order 42 placed?"  → no idea (timestamp gone on UPDATE)
  Question: "What was the price when ordered vs shipped?" → gone

EVENT SOURCING APPROACH (immutable event log):
  event_store table / Kafka stream "orders-42":
  ┌─────┬────────────────┬──────────────────────────────────────────────────┐
  │ seq │ event_type     │ payload                                          │
  ├─────┼────────────────┼──────────────────────────────────────────────────┤
  │  1  │ OrderPlaced    │ {orderId:42, userId:42, items:[{prod:1,qty:2,     │
  │     │                │  priceAtTime:99}], total:198, ts:2024-01-15T...}  │
  ├─────┼────────────────┼──────────────────────────────────────────────────┤
  │  2  │ PaymentCharged │ {orderId:42, amount:198, txnId:"TXN_XYZ",        │
  │     │                │  ts:2024-01-15T10:02:01}                          │
  ├─────┼────────────────┼──────────────────────────────────────────────────┤
  │  3  │ OrderShipped   │ {orderId:42, carrier:"UPS", trackingId:"1Z999",  │
  │     │                │  ts:2024-01-16T08:00:00}                          │
  ├─────┼────────────────┼──────────────────────────────────────────────────┤
  │  4  │ OrderDelivered │ {orderId:42, deliveredAt:"2024-01-18T14:22:00"}  │
  └─────────────────────────────────────────────────────────────────────────┘

  Current state = replay events 1..4 for orderId 42
  "What was the price when ordered?" → event 1, priceAtTime:99
  "When was it shipped?" → event 3, timestamp
  "What happened between Jan 15 10:00 and 10:05?" → filter by ts

Multiple projections from the same event stream:
  Kafka topic "order-events"
      |
      ├── Consumer A → Orders DB (current order status, for ops dashboard)
      ├── Consumer B → User DB  (order history per user, for profile page)
      ├── Consumer C → Analytics warehouse (revenue metrics, for BI)
      └── Consumer D → Fraud detection (pattern analysis, real-time)
```

### Snapshot Optimization

```
Problem: Order 42 has 2000 events (active since 2019).
         Replaying 2000 events on every read is slow.

Solution: Snapshots

  Snapshot after every 100 events:
  snapshot_store:
  ┌───────────┬────────────┬────────────────────────────────────────┐
  │ orderId   │ seq_number │ state_snapshot                         │
  ├───────────┼────────────┼────────────────────────────────────────┤
  │ 42        │ 1000       │ {status: SHIPPED, total: 198, ...}     │
  │ 42        │ 1100       │ {status: DELIVERED, total: 198, ...}   │
  └───────────┴────────────┴────────────────────────────────────────┘

  To get current state:
  1. Load latest snapshot (seq=1100, 1 row read)
  2. Replay only events 1101..current (at most 100 events)
  Total: snapshot + 0-100 events, not 2000 events
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Event Store Options

```
Option 1: Kafka (most common)
  - Each aggregate type gets a topic: "orders", "payments", "users"
  - Each aggregate instance = one partition key: key = orderId
  - All events for orderId=42 go to the same partition (ordered)
  - Retention: set to "forever" (log.retention.ms = -1) for true event store
  - Replay: seek to offset 0 for a topic, consume all events from beginning
  - Limitation: cannot query "get all events for orderId=42" efficiently
    (must consume entire partition). Use Kafka for event streaming,
    a DB for per-aggregate event lookup.

Option 2: EventStoreDB (purpose-built)
  - Native per-stream storage: stream "orders-42" has all events for order 42
  - Optimistic concurrency: append event with expected version number
    (prevents concurrent writes corrupting the stream)
  - Built-in projections: define a function that processes events → state
  - HTTP + gRPC API
  - Best for: true event sourcing at moderate scale (<1B events total)

Option 3: PostgreSQL as event store (simple, battle-tested)
  CREATE TABLE events (
    id           BIGSERIAL PRIMARY KEY,
    aggregate_id VARCHAR(50) NOT NULL,
    event_type   VARCHAR(100) NOT NULL,
    payload      JSONB NOT NULL,
    version      INT NOT NULL,
    created_at   TIMESTAMP DEFAULT NOW(),
    UNIQUE(aggregate_id, version)   -- optimistic concurrency control
  );
  CREATE INDEX ON events(aggregate_id, version);

  -- Load all events for an order:
  SELECT * FROM events WHERE aggregate_id = 'order-42' ORDER BY version;

  -- Append with optimistic locking (fails if version conflict):
  INSERT INTO events (aggregate_id, event_type, payload, version)
  VALUES ('order-42', 'OrderShipped', '{"carrier":"UPS",...}', 4);
  -- Fails with UNIQUE violation if another process wrote version 4 first
```

### Axon Framework (Java) — CQRS + Event Sourcing

```java
// WRITE SIDE: Aggregate (handles Commands, stores Events)
@Aggregate
public class OrderAggregate {

    @AggregateIdentifier
    private String orderId;
    private OrderStatus status;

    @CommandHandler
    public OrderAggregate(PlaceOrderCommand cmd) {
        // Validate business rules here
        if (cmd.getItems().isEmpty()) throw new IllegalArgumentException("No items");

        // DO NOT mutate state here — apply an event
        AggregateLifecycle.apply(new OrderPlacedEvent(
            cmd.getOrderId(), cmd.getUserId(), cmd.getItems(), cmd.getTotal()
        ));
    }

    @EventSourcingHandler  // called when event is replayed to rebuild state
    public void on(OrderPlacedEvent event) {
        this.orderId = event.getOrderId();
        this.status = OrderStatus.PLACED;
    }

    @CommandHandler
    public void handle(ShipOrderCommand cmd) {
        if (this.status != OrderStatus.PAID) throw new IllegalStateException("Not paid");
        AggregateLifecycle.apply(new OrderShippedEvent(
            this.orderId, cmd.getCarrier(), cmd.getTrackingId()
        ));
    }

    @EventSourcingHandler
    public void on(OrderShippedEvent event) {
        this.status = OrderStatus.SHIPPED;
    }
}

// READ SIDE: Event Handler (updates query model)
@Component
public class OrderProjection {

    @Autowired
    private OrderReadRepository readRepository;

    @EventHandler
    public void on(OrderPlacedEvent event) {
        OrderView view = new OrderView();
        view.setOrderId(event.getOrderId());
        view.setStatus("PLACED");
        view.setTotal(event.getTotal());
        readRepository.save(view);
    }

    @EventHandler
    public void on(OrderShippedEvent event) {
        OrderView view = readRepository.findById(event.getOrderId()).orElseThrow();
        view.setStatus("SHIPPED");
        view.setTrackingId(event.getTrackingId());
        readRepository.save(view);
    }
}
```

### Eventual Consistency: The Hard Part

```
Timeline:
  T+0ms:   User clicks "Place Order"
  T+5ms:   Write side: OrderPlacedEvent stored in event store
  T+5ms:   HTTP 200 returned to user: "Order placed!"
  T+105ms: Kafka consumer processes OrderPlacedEvent
  T+110ms: Read model (Elasticsearch) updated with new order

  User immediately requests their order list:
  T+10ms:  GET /orders?userId=42
  T+10ms:  Read model hasn't been updated yet
  T+10ms:  Order might NOT appear in the list yet!

Solutions:
  1. Optimistic UI: Show the order immediately in the UI from the command response
     (don't wait for the read model). Browser-side state management.

  2. Read-your-writes consistency: after a write, route that user's next read
     to the WRITE side (PostgreSQL) for the next 500ms.
     After 500ms, the read model has caught up → route to read side.

  3. Event-driven UI: SSE/WebSocket pushes "OrderConfirmed" event to browser
     when the read model is updated. Browser updates UI then, not before.

  4. Accept it: for most operations, 100ms eventual consistency is fine.
     "Your order is being confirmed..." spinner for 1-2 seconds is acceptable UX.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your payment service needs a complete audit trail of all account changes for regulatory compliance. The regulator can ask 'show me every change to account X between Jan 1 and Jan 31.' How do you design the data storage?"

**You (architect answer):**

> "This is a textbook Event Sourcing use case. The key regulatory requirement is that you can't delete or modify history, and you can answer any 'what happened when' question.
>
> I'd store every account event as an immutable record. The schema would be an `account_events` table with: account_id, event_type (DEBIT, CREDIT, FEE_CHARGED, INTEREST_APPLIED), amount, balance_after, initiated_by (user ID or system), correlation_id (links to the transaction that caused it), and created_at timestamp. No UPDATE, no DELETE — only INSERT.
>
> The current account balance is derived: `SELECT SUM(CASE WHEN event_type = 'CREDIT' THEN amount ELSE -amount END) FROM account_events WHERE account_id = X`. In practice, you'd cache this in a CQRS read model (a separate `account_balances` table), but the source of truth is always the event log.
>
> For the regulator's query, I'd add a GIN index on `account_id` and a BRIN index on `created_at` (append-only data, perfectly suited for BRIN). The query 'show me all changes to account X in January' becomes a simple range scan: `WHERE account_id = X AND created_at BETWEEN Jan-1 AND Jan-31`.
>
> For compliance retention, the events table lives in cold storage after 7 years — but it's never deleted. I'd partition the table by year (`PARTITION BY RANGE (created_at)`) so querying recent data doesn't scan historical partitions.
>
> The CQRS part: real-time balance queries hit a Redis cache populated by an event consumer, not the events table. The events table is for audit and replay — not for serving 10K balance queries per second."

---

## PART 5 — DECISION FRAMEWORK

### When to Use CQRS / Event Sourcing vs Simpler Patterns

| Scenario | Recommended Pattern | Why |
|---|---|---|
| Simple CRUD app, <100K records | Plain MVC + ORM | CQRS overhead not worth it |
| Read-heavy, complex queries (dashboards) | CQRS without Event Sourcing | Separate read model, but store current state |
| Audit trail required (finance, healthcare) | Event Sourcing | Immutable log is the requirement itself |
| Complex domain logic, multiple aggregates | CQRS + Event Sourcing | Bounded contexts, event-driven integration |
| Regulatory compliance (SEC, SEBI, GDPR) | Event Sourcing mandatory | Cannot delete history |
| Microservices integration | Event Sourcing + Kafka | Events are the integration contract |

### CQRS Without Event Sourcing (Simpler, More Common)

```
Write side: Regular DB writes (PostgreSQL, normalized)
            After each write, publish an event to Kafka

Read side:  Separate DB (Elasticsearch, Cassandra, Redis)
            Kafka consumer updates read model

This is MORE COMMON than full Event Sourcing.
Use full Event Sourcing only when:
  (a) audit trail / time-travel queries are required
  (b) domain logic is extremely complex (financial instruments, insurance)
  (c) you need to rebuild read models from scratch (replay all history)
```

### Complexity vs Benefit

```
CQRS alone:
  Complexity added: Medium (two codepaths, eventual consistency to manage)
  Benefit:          High (read scalability, clean separation of concerns)
  When justified:   Read/write ratio > 10:1, different scaling needs

Event Sourcing alone:
  Complexity added: High (replay logic, snapshot strategy, schema evolution)
  Benefit:          High (audit trail, time-travel, event-driven integration)
  When justified:   Audit requirement OR complex business rules

CQRS + Event Sourcing:
  Complexity added: Very High (framework needed, team expertise required)
  Benefit:          Very High (all of the above)
  When justified:   Payment systems, trading platforms, insurance, healthcare
```

---

## QUICK REFERENCE CARD

```
CQRS PATTERN:
  Write path: Command → validate → persist (PostgreSQL) → publish event (Kafka)
  Read path:  Query → read from denormalized store (ES/Redis/Cassandra)
  Sync:       Kafka consumer subscribes to events → updates read model

EVENT SOURCING:
  Never UPDATE or DELETE: only INSERT new events
  Current state = replay(events for aggregateId)
  Snapshot every N events to speed up replay
  Event schema: { aggregateId, eventType, payload, version, timestamp }

AXON ANNOTATIONS (Java):
  @Aggregate          — marks the write-side domain object
  @CommandHandler     — handles incoming commands
  @EventSourcingHandler — called during state replay
  @EventHandler       — read-side: updates projections

EVENTUAL CONSISTENCY COPING:
  - Optimistic UI (show result immediately, confirm async)
  - Read-your-writes routing for 500ms post-write
  - SSE/WebSocket push when read model catches up

WHEN TO REACH FOR THIS:
  "audit trail"  → Event Sourcing
  "read at scale" → CQRS
  "regulatory"   → Event Sourcing mandatory
  "time travel"  → Event Sourcing
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** When an interview mentions "audit trail," "regulatory compliance," "transaction history," or "read/write scaling" — CQRS and Event Sourcing are the tools. Mention both, explain the difference, and apply selectively.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **07 — Payment** | Event sourcing for the payment ledger is non-negotiable. Every debit and credit is stored as an immutable event. Regulators can audit complete history going back years. Current balance = sum of all events for that account. Cannot delete records (legal compliance). CQRS separates the payment processing path from the balance inquiry path. |
| **09 — E-Commerce** | CQRS for the order system. Write model: normalized PostgreSQL with inventory validation and pricing rules (ACID, single source of truth). Read model: Elasticsearch for order history search + Redis for recent orders cache. Each scales independently — Black Friday order queries don't compete with order writes for DB resources. |
| **13 — Leaderboard** | Event sourcing for score history. "Show Alice's score progression over the last month" — replay her score events filtered by timestamp. The read model is a Redis ZSET holding current standings (current leaderboard). The event log holds the full history. Score corrections can be applied by appending a compensating event, not editing history. |
| **19 — Stock Broker** | Event sourcing is legally required. Every order placed, every execution, every cancellation stored as immutable events. SEC/SEBI regulations require full audit trails. Read models: current open positions, daily P&L dashboard, tax lot accounting — each a different projection of the same event stream. |

**Architect's one-liner for the interview:**
*"Event Sourcing treats the database as an append-only ledger of what happened — never what 'currently is' — which gives you a complete audit trail, time-travel queries, and the ability to rebuild any read model from scratch; CQRS then separates who writes to that ledger from who reads from its projections, letting each side scale and evolve independently."*

---
