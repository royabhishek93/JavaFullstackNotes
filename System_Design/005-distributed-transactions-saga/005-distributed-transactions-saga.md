# SD_Q05: Distributed Transactions & Saga Pattern — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 25-30 minutes | **Frequency:** 85% in architect rounds 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "You have 3 microservices: Order, Inventory, Payment. A user places an order. How do you ensure all three either succeed or all three roll back?" — The distributed transaction question.

---

## NEW LEARNER FOUNDATION

### Why @Transactional Doesn't Work Across Services (Plain English)
```
@Transactional works by: getting ONE DB connection, wrapping all SQL
in BEGIN/COMMIT, and using the connection pool's TX mechanism.

Microservices problem:
  OrderService    → its OWN DB (PostgreSQL #1)
  InventoryService → its OWN DB (PostgreSQL #2)
  PaymentService  → its OWN DB (PostgreSQL #3)

@Transactional can only control ONE DB connection on ONE JVM.
It has ZERO knowledge of what PaymentService's DB is doing.

@Transactional CANNOT atomically commit/rollback across 3 separate databases.
There is NO magic Spring annotation that fixes this.
You need a distributed coordination strategy.
```

### What is 2PC (Two-Phase Commit)? (Plain English)
```
2PC = old-school attempt to coordinate distributed transactions.
Two rounds of communication:

Phase 1 (PREPARE):
  Coordinator asks each participant: "Can you commit?"
  Participants: lock resources, write to WAL, reply "YES, I'm ready"

Phase 2 (COMMIT):
  If all said YES: Coordinator sends "COMMIT" to all
  If any said NO:  Coordinator sends "ROLLBACK" to all

PROBLEM: During Phase 2, if Coordinator CRASHES:
  Participant A: committed ✅
  Participant B: waiting for COMMIT message (holds locks forever)
  Participant C: waiting for COMMIT message (holds locks forever)
  → B and C are stuck with locked resources, no way to proceed
  → System is in an inconsistent state until Coordinator recovers

2PC is a BLOCKING protocol. Crash = deadlock until recovery.
Not suitable for microservices (100 services, network partitions are normal).
```

### What is the Saga Pattern? (Plain English)
```
Saga = a sequence of LOCAL transactions, each with a COMPENSATING transaction.

If step 3 fails:
  → Run compensating action for step 2 (undo what step 2 did)
  → Run compensating action for step 1 (undo what step 1 did)
  → System returns to a consistent state

NOT ACID — intermediate states are VISIBLE to other operations.
BUT: no cross-service locking, no coordinator bottleneck.
GOOD FOR: business processes where you can describe an "undo" for each step.
```

---

## BIG PICTURE — Saga vs 2PC

```
 2PC (DON'T USE IN MICROSERVICES):
 ┌────────────────────────────────────────────────────────────────┐
 │  Coordinator                                                   │
 │       │  Phase 1: PREPARE                                     │
 │       ├────────────────────► [Order DB]   → "READY" ✅        │
 │       ├────────────────────► [Inventory DB] → "READY" ✅      │
 │       ├────────────────────► [Payment DB] → CRASH 💥          │
 │       │                                                        │
 │       │  Phase 2: Coordinator CRASHES here                    │
 │       │  Order DB and Inventory DB: WAITING FOREVER           │
 │       │  Locks held, services blocked, system STUCK           │
 └────────────────────────────────────────────────────────────────┘

 SAGA CHOREOGRAPHY (event-driven, no coordinator):
 ┌────────────────────────────────────────────────────────────────┐
 │  [Order Service]                                               │
 │       │ 1. Create order (PENDING)                             │
 │       │ 2. Publish: OrderCreated event → Kafka                │
 │       │                                                        │
 │  [Inventory Service]                                           │
 │       │ listens: OrderCreated                                  │
 │       │ 3. Reserve stock                                       │
 │       │ 4. Publish: StockReserved event → Kafka                │
 │       │                                                        │
 │  [Payment Service]                                             │
 │       │ listens: StockReserved                                 │
 │       │ 5. Charge card                                         │
 │       │ 6. Publish: PaymentCompleted OR PaymentFailed          │
 │       │                                                        │
 │  [Order Service]                                               │
 │       │ listens: PaymentCompleted → mark order CONFIRMED       │
 │       │ listens: PaymentFailed → publish OrderCancelled        │
 │       │                                                        │
 │  [Inventory Service]                                           │
 │       │ listens: OrderCancelled → RELEASE reserved stock       │
 │       │         ↑ THIS is the COMPENSATING transaction         │
 └────────────────────────────────────────────────────────────────┘

 SAGA ORCHESTRATION (central coordinator):
 ┌────────────────────────────────────────────────────────────────┐
 │  [Saga Orchestrator (Order Saga)]                              │
 │       │                                                        │
 │       ├──1──► Order Service: CreateOrder                       │
 │       ◄──2─── OrderCreated ✅                                  │
 │       │                                                        │
 │       ├──3──► Inventory Service: ReserveStock                  │
 │       ◄──4─── StockReserved ✅                                 │
 │       │                                                        │
 │       ├──5──► Payment Service: ChargeCard                      │
 │       ◄──6─── PaymentFailed ❌                                 │
 │       │                                                        │
 │       ├──7──► Inventory Service: ReleaseStock  ← compensate   │
 │       ├──8──► Order Service: CancelOrder       ← compensate   │
 │       │                                                        │
 │       Saga completes (rolled back) ✅                          │
 └────────────────────────────────────────────────────────────────┘
```

---

## Scenario 1: Choreography vs Orchestration — When to Use Which

### Choreography (Events Only, No Coordinator)
```
PROS:
  ✅ Loose coupling: services don't know each other exist
  ✅ No single point of failure (no coordinator)
  ✅ Easy to add a new consumer (just listen to existing events)
  ✅ Lower latency (no extra hop through coordinator)

CONS:
  ❌ Hard to see the overall flow — it's distributed across services
  ❌ Debugging: you must trace events across 5 services to understand state
  ❌ Cyclic events: Service A listens to B which listens to A → hard to reason
  ❌ For complex flows (10+ steps) → impossible to understand the "happy path"

USE WHEN: simple flows (2-3 steps), teams that own their own services end-to-end
EXAMPLE: OrderPlaced → InventoryReserved → PaymentProcessed → EmailSent
```

### Orchestration (Central Coordinator Controls Flow)
```java
// Spring State Machine or Temporal/Conductor workflow

// Saga Orchestrator (Axon Framework example):
@Saga
public class OrderSaga {

    @Autowired private transient CommandGateway commandGateway;

    @StartSaga
    @SagaEventHandler(associationProperty = "orderId")
    public void on(OrderCreatedEvent event) {
        // Step 1 succeeded: now reserve inventory
        commandGateway.send(new ReserveStockCommand(event.getOrderId(), event.getItems()));
    }

    @SagaEventHandler(associationProperty = "orderId")
    public void on(StockReservedEvent event) {
        // Step 2 succeeded: now charge payment
        commandGateway.send(new ChargePaymentCommand(event.getOrderId(), event.getAmount()));
    }

    @SagaEventHandler(associationProperty = "orderId")
    public void on(PaymentFailedEvent event) {
        // Step 3 failed: compensate step 2
        commandGateway.send(new ReleaseStockCommand(event.getOrderId()));
        commandGateway.send(new CancelOrderCommand(event.getOrderId()));
        // Saga ends here (rollback complete)
        SagaLifecycle.end();
    }

    @EndSaga
    @SagaEventHandler(associationProperty = "orderId")
    public void on(PaymentCompletedEvent event) {
        commandGateway.send(new ConfirmOrderCommand(event.getOrderId()));
    }
}

PROS:
  ✅ Single place to see the full flow (the orchestrator class)
  ✅ Easy to add retry/timeout logic in the coordinator
  ✅ Easier debugging: check orchestrator state → know exactly where it is
  ✅ Complex flows (10+ steps) are manageable

CONS:
  ❌ Coordinator is a coupling point (knows all services)
  ❌ Coordinator itself can become a bottleneck
  ❌ More code to write (orchestrator class + commands)

USE WHEN: complex multi-step flows, payments (must track state), order fulfilment
```

---

## Scenario 2: Transactional Outbox — Ensuring Event Published After DB Commit

### The Problem Without Outbox
```java
@Service @Transactional
public OrderService {
    public Order placeOrder(OrderRequest req) {
        Order order = orderRepo.save(new Order(req));  // Step 1: save to DB

        kafkaTemplate.send("orders", new OrderPlacedEvent(order.getId()));  // Step 2: publish

        return order;
    }
}

FAILURE SCENARIO 1:
  Step 1: DB commit ✅
  Step 2: Kafka UNAVAILABLE at this moment
  → Exception thrown → TX rolled back (order NOT saved!)
  → But wait — we did commit first, then published...
  Actually with @Transactional: if Step 2 throws BEFORE return,
  TX may or may not roll back depending on the exception.

FAILURE SCENARIO 2 (worse):
  Step 1: DB commit ✅
  Step 2: Kafka publish ✅
  App crashes between steps... no problem here actually

FAILURE SCENARIO 3 (the real trap):
  Step 2 fires Kafka publish BEFORE Step 1 fully commits.
  Downstream service reads the event, tries to find order in DB → not found yet.
  Race condition with replication lag.

ROOT PROBLEM: DB write and Kafka publish are NOT atomic.
              One can succeed while the other fails.
```

### Fix: Transactional Outbox Pattern
```java
// The OUTBOX: a table in the SAME DB as the business data
// Both order save AND outbox write happen in ONE DB transaction (truly atomic)

@Service @Transactional
public class OrderService {
    public Order placeOrder(OrderRequest req) {
        Order order = orderRepo.save(new Order(req));

        // Write event to OUTBOX table (same DB, same TX)
        OutboxEvent outbox = OutboxEvent.builder()
            .aggregateId(order.getId().toString())
            .eventType("ORDER_PLACED")
            .payload(toJson(new OrderPlacedEvent(order.getId(), order.getTotalAmount())))
            .status(OutboxStatus.PENDING)
            .build();
        outboxRepo.save(outbox);

        return order;
        // TX commits: BOTH order AND outbox event are saved atomically
        // If TX fails: NEITHER is saved
        // No inconsistency possible
    }
}

// Outbox Relay (separate process — polls or uses CDC):
@Scheduled(fixedDelay = 100)  // every 100ms
@Transactional
public void relay() {
    List<OutboxEvent> pending = outboxRepo.findByStatus(PENDING);
    for (OutboxEvent event : pending) {
        kafkaTemplate.send(event.getEventType(), event.getPayload());
        event.setStatus(OutboxStatus.PUBLISHED);
        outboxRepo.save(event);
    }
}
// Even if Kafka is temporarily down: events stay as PENDING in the outbox
// Relay retries every 100ms until Kafka is back
// Once published: marked as PUBLISHED (idempotent → OK to retry relay too)
```

---

## Trap 1: Saga Isolation — The "Lost Update" Problem

### The Problem
```
Sagas do NOT provide ACID isolation. Intermediate states are visible.

Order Saga flow:
  Step 1: Reserve 5 iPhones in Inventory (available: 10 → reserved: 5, available: 5)
  Step 2: Charge payment (in progress)

Meanwhile, ANOTHER order saga:
  Sees available inventory: 5 (the intermediate state after step 1 above)
  Reserves 5 more iPhones (available: 0)

First saga: payment fails → compensate step 1 → RELEASE 5 iPhones (available: 5)
Second saga: completes → ships 5 iPhones

Result: inventory shows available: 5 but no iPhones physically in stock.
This is a "lost update" / "dirty read" across sagas.
```

```
FIXES:

Option 1: Semantic Locking (Application-level lock)
  Before step 1: set a "processing" flag on inventory record
  Other sagas: see "processing" flag → return "try again later" (429)
  After saga completes (or compensates): clear the flag
  Simulates ACID isolation at the application level

Option 2: Pessimistic approach — book first, release later
  Reserve inventory only AFTER payment succeeds
  If payment fails: no inventory was reserved → no compensation needed
  Trade-off: inventory not "held" during payment → risk of overselling

Option 3: Countermeasures
  For most business scenarios: acceptable to have brief inconsistency
  Add a reconciliation job that runs every 10 minutes
  Detects and fixes any inventory miscounts
  Better than trying to implement distributed ACID (which doesn't scale)
```

---

## Trap 2: Compensating Transaction Is Not Always Possible

### The Bug
```
You designed a saga for order fulfillment:
  Step 1: Deduct from customer wallet
  Step 2: Process order
  Step 3: Send physical item via courier

Step 3 succeeds — courier picks up the package.
Step 2 then fails (inventory system crash).

Compensation for Step 3: "Cancel the shipment"
But the courier already has the package in transit.
Calling courier API: "shipment cannot be cancelled — out for delivery"
Your compensating transaction FAILED.

For PHYSICAL OPERATIONS (send email, call API, ship package):
  Compensating transactions may be impossible or irreversible.
```

```
SOLUTIONS:

Option 1: Reorder steps — irreversible actions LAST
  Bad order:  Ship → Process → Deduct wallet ← if Deduct fails, can't un-ship
  Good order: Deduct wallet → Process → Ship ← if Processing fails before Ship,
                                                 compensation is easy (refund wallet)
              Ship is the LAST step (only after all reversible steps succeed)

Option 2: Accept imperfection + human process
  Some failures need human intervention:
  If shipment can't be cancelled: create a "return request" workflow
  Customer service team processes exceptions manually
  Not every business scenario can be automated atomically

Option 3: Two-phase commitment for physical actions
  Step 3a: "Reserve" shipment (reversible — courier confirms "can ship" but hasn't yet)
  All other steps complete.
  Step 3b: "Confirm" shipment (triggers physical pickup)
  Compensation: cancel the "reserved" shipment (before physical pickup)
```

---

## Interview Cheat Sheet

> "I never use 2PC for microservices — it's a blocking protocol, and a coordinator crash leaves all participants holding locks forever. For distributed business flows I use the Saga pattern. Choreography for simple flows (loose coupling, events only), orchestration for complex multi-step flows where you need to see the overall state in one place. The transactional outbox pattern is critical: writing an event to Kafka is never atomic with a DB write, so I write to an outbox table in the same DB transaction, then a relay publishes it to Kafka. Saga isolation is the hardest trap — intermediate states are visible to concurrent sagas, causing dirty reads. Fix with semantic locking (mark records as 'processing') or by ordering irreversible actions last so they only execute after all reversible steps succeed."
