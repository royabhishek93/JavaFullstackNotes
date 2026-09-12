# Saga Pattern
### Alternative to 2PC — Choreography vs Orchestration Saga

---

## PART 1 — THE STUDENT CONVERSATION

**2PC is like getting all chefs to agree before anyone starts cooking.**
The kitchen manager gathers everyone: "Can you all commit to finishing this dish?" Everyone says yes. Manager says go. If anyone drops the pan, everyone stops and reverses their work. Coordinated, but slow — and if the manager faints mid-way, everyone's frozen.

**Saga is like a relay race.**
Runner 1 completes their leg, passes the baton to Runner 2. Runner 2 passes to Runner 3. If Runner 3 drops the baton, Runner 2 runs backward to undo their leg, then Runner 1 runs backward. Each step is independent. No "manager" freezing everyone.

A Saga is a sequence of local transactions, where each step publishes an event that triggers the next step. If a step fails, compensating transactions undo the previous steps.

**Key insight:** there's no distributed lock. Each service only locks its own database for its own local transaction. Atomicity is eventual — the system eventually converges to either "all done" or "all undone."

---

## PART 2 — THE TWO TYPES OF SAGA

### Type 1: Choreography (event-driven, no central orchestrator)

```
Place Order Saga — Choreography:
────────────────────────────────────────────────────────────────────

  User places order
       │
       ▼
  Order Service
  ├── INSERT order (status=PENDING) into orders DB  ← local transaction
  └── Publish: OrderCreated event to Kafka
       │
       ▼
  Inventory Service (listens to OrderCreated)
  ├── DECREMENT stock in inventory DB               ← local transaction
  ├── If success: Publish: StockReserved event
  └── If failure: Publish: StockReservationFailed event
       │
       ├─── StockReserved ──────────────────────────────────────────►
       │                                                           ▼
       │                                                   Payment Service
       │                                                   ├── DEBIT user account
       │                                                   ├── If success: PaymentCompleted
       │                                                   └── If failure: PaymentFailed
       │                                                           │
       │                                                   Order Service (listens)
       │                                                   └── UPDATE order status=CONFIRMED
       │
       └─── StockReservationFailed ─────────────────────────────────►
                                                              Order Service
                                                              └── UPDATE order status=FAILED
                                                                  (no inventory compensation needed,
                                                                   stock was never decremented)

  Compensating transactions (unhappy path with PaymentFailed):
  Payment Service publishes: PaymentFailed
  Inventory Service listens: StockReserved + PaymentFailed → RESTORE stock (compensating txn)
  Order Service listens: PaymentFailed → UPDATE order status=CANCELLED
```

### Type 2: Orchestration (central saga orchestrator)

```
Place Order Saga — Orchestration:
────────────────────────────────────────────────────────────────────

  User places order
       │
       ▼
  Saga Orchestrator (stateful service / workflow engine)
  State machine: tracks current step, what to do on success/failure

  Step 1: Orchestrator calls Inventory Service
    "Reserve stock for order #X"
    Inventory: OK → Orchestrator moves to Step 2

  Step 2: Orchestrator calls Payment Service
    "Charge user for order #X"
    Payment: FAILED (insufficient funds) → Orchestrator begins rollback

  Step 2 rollback: Orchestrator calls Inventory Service
    "Release stock reservation for order #X" (compensating transaction)
    Inventory: OK → stock restored

  Step 1 rollback: no further steps to undo

  Orchestrator updates order status: FAILED

  Orchestrator state (persisted in DB):
  {
    saga_id: "saga-123",
    order_id: "order-X",
    current_step: 2,
    status: "COMPENSATING",
    steps: [
      { service: "inventory", action: "reserve", status: "COMPLETED", compensation: "release" },
      { service: "payment", action: "charge", status: "FAILED" }
    ]
  }
```

---

## PART 3 — COMPARISON DIAGRAM

```
Choreography vs Orchestration:
──────────────────────────────────────────────────────────────────────────

  Choreography:                          Orchestration:
  ─────────────                          ──────────────
  No central coordinator                 Central orchestrator manages flow

  Service A                              Orchestrator
  │ publish event                        │ call A
  ▼                                      ▼
  Service B (reacts to A's event)        Service A
  │ publish event                        │ return result
  ▼                                      ▼
  Service C (reacts to B's event)        Orchestrator
                                         │ call B
  Advantages:                            ▼
  ✓ Loose coupling                       Service B
  ✓ No SPOF                              │ return result
  ✓ Each service just reacts             ▼
                                         Orchestrator
  Disadvantages:
  ✗ Hard to trace the full flow          Advantages:
  ✗ Hard to understand what happens      ✓ Single place to see entire flow
    when things go wrong                 ✓ Easy to add steps, timeout logic
  ✗ Circular event loops possible        ✓ Clear rollback logic centralized
  ✗ Difficult to add new services        ✓ Easy to retry failed steps
    (must update event subscriptions)
                                         Disadvantages:
  Best for: simple 2-3 step flows        ✗ Orchestrator is a new service to build
                                         ✗ Can become a coupling point
  Used in: Notification system           ✗ Single point of operational concern
  (simple chain: send → track → done)
                                         Best for: complex multi-step flows (5+ steps)
                                         Used in: order flows, payment flows,
                                         onboarding workflows
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Order placement involves deducting inventory, charging the user, and creating a shipment. How do you ensure atomicity across these three services?"

**You (architect answer):**

> "I wouldn't use 2PC here — each of these is a separate microservice with its own database,
> and 2PC would introduce distributed locking across all three. One slow database would block
> all three. Instead, I'd use an Orchestration Saga.
>
> The saga orchestrator maintains a state machine for each order. It calls each step in sequence:
> first reserve inventory, then charge payment, then create shipment. Each step is a local
> transaction in its own service — the orchestrator just sequences them.
>
> For the happy path: all three succeed → order confirmed.
>
> For the failure path: if payment fails, the orchestrator calls the inventory service's
> compensating transaction — 'release the reservation.' If shipment creation fails, the
> orchestrator calls payment's compensating transaction — 'refund the charge' — and then
> inventory's — 'release reservation.'
>
> The compensating transactions are the key design challenge. Every forward step must have
> a corresponding undo step, and undo steps must be idempotent — if the compensating
> transaction is called twice (retry scenario), it shouldn't double-refund.
>
> I'd use a workflow engine like Temporal or Conductor for the orchestrator rather than
> building a custom state machine. Temporal persists every step's state in its own database,
> so if the orchestrator crashes mid-saga, it resumes from exactly where it left off."

---

## PART 5 — IDEMPOTENCY IN COMPENSATING TRANSACTIONS

```
Critical requirement: compensating transactions must be IDEMPOTENT
(safe to call multiple times without different effects)
──────────────────────────────────────────────────────────────────────────

BAD compensating transaction:
  "Refund $100 to user"
  Called twice due to retry → user gets $200 refund ← WRONG

GOOD compensating transaction:
  "Set payment status=REFUNDED, refund amount=$100
   WHERE payment_id = 'pay-123' AND status != 'REFUNDED'"
  Called twice → second call finds status already REFUNDED → no-op ← CORRECT

Implementation pattern:
  Each saga step has a unique saga_step_id (e.g., "saga-456-step-2-compensate")
  Before processing: check if this step_id was already processed
  If yes: return success (idempotent)
  If no: process and record the step_id

  INSERT INTO processed_saga_steps (step_id) VALUES ('saga-456-step-2-compensate')
  ON DUPLICATE KEY IGNORE;
  ← If duplicate → step already done → skip
```

---

## PART 6 — REAL TOOLS FOR SAGA ORCHESTRATION

```
Temporal (most popular for Java/Go):
  workflow.io — persists saga state automatically
  Each step is a deterministic function call
  Automatic retry with configurable retry policy
  Built-in timeout handling
  Used by: Netflix, Stripe, DoorDash

  @WorkflowImpl
  public class OrderSagaWorkflow {
      public void placeOrder(OrderRequest req) {
          inventoryActivity.reserve(req);     // if fails → throws → triggers retry/compensate
          try {
              paymentActivity.charge(req);
          } catch (Exception e) {
              inventoryActivity.release(req); // compensating transaction
              throw e;
          }
          shipmentActivity.create(req);
      }
  }

Apache Camel / Conductor (Netflix OSS):
  BPMN-style workflow definition in JSON/YAML
  Good for teams that want declarative (not code) saga definition

Manual (simple cases):
  Saga state stored in the Order table:
  saga_status: STARTED / INVENTORY_RESERVED / PAYMENT_DONE / COMPLETED / COMPENSATING / FAILED
  Each step checks current saga_status → knows what to do next
```

---

## QUICK REFERENCE CARD

```
Saga = sequence of local transactions + compensating transactions for rollback

Choreography:
  Services react to each other's events (Kafka topics)
  No central coordinator
  Best for: 2-3 services, simple linear flow

Orchestration:
  Central saga orchestrator calls each service in sequence
  Manages state, retries, compensations in one place
  Best for: 5+ services, complex branching logic, long-running workflows

Compensating transactions:
  Every forward step MUST have an undo step
  Must be idempotent (safe to call multiple times)
  Must be semantic undo, not literal undo
    "Remove item from cart" ≠ rollback the INSERT
    "Mark item as removed" = correct approach (keeps audit trail)

Vs 2PC:
  2PC: synchronous, distributed locks, atomic, blocking on coordinator failure
  Saga: asynchronous, local transactions only, eventually consistent, no blocking

Tools:
  Temporal: code-first, durable execution, best DX
  Conductor (Netflix): JSON workflow definition
  Axon Framework (Java): event sourcing + saga built-in
  AWS Step Functions: managed orchestrator

Interview one-liner:
"Saga replaces 2PC's distributed lock with a sequence of local transactions.
If a step fails, we run compensating transactions to undo completed steps.
No distributed lock means no blocking on coordinator failure — at the cost
of eventual consistency instead of atomic consistency."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Any multi-step business transaction across microservices is a Saga — knowing choreography vs orchestration and when to use each is a senior-level differentiator.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **07 — Payment** | International transfer: debit source → convert currency → credit destination. If currency conversion fails → compensating transaction credits source back. Orchestration saga via Temporal: coordinator manages retry/rollback state. |
| **08 — Food Delivery** | Order placed → payment charged → restaurant confirmed → driver assigned. If restaurant rejects: cancel payment, release driver. Choreography via Kafka events or orchestration via Temporal workflow owning the state machine. |
| **09 — E-Commerce** | Reserve inventory → process payment → confirm order. If payment fails → release inventory (compensating tx). Choreography saga via Kafka events: inventory service listens for PaymentFailed event and releases stock. |

**Architect's one-liner for the interview:**
*"Choreography gives you loose coupling but makes it hard to see the overall flow; orchestration makes the flow explicit in one place but introduces a coordinator as a single point of knowledge — I pick orchestration when the business logic is complex enough that I need to debug it."*
