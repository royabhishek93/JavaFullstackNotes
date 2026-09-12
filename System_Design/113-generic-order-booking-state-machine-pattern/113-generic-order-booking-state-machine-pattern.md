# The Generic Order/Booking State Machine Pattern
### Why every payment, ride, booking, and job system in your codebase should be built the same way

---

## PART 1 — THE STUDENT CONVERSATION

Imagine you're asked to add a "cancel order" button. The obvious approach: add an `is_cancelled` boolean column to the `orders` table. Ship it. Two weeks later, someone reports a bug: an order shows `is_cancelled = true` AND `is_shipped = true` at the same time. A cancelled order got shipped. Support has no idea how that happened, and neither do you — because nothing in the code ever said "you can't ship something that's cancelled." The booleans just... exist, independently, and nothing stops any combination of them from being true at once.

This is the core problem with modeling a business lifecycle as a bag of booleans (`is_paid`, `is_shipped`, `is_cancelled`, `is_refunded`, `is_delivered`...). Each flag is set by a different piece of code, at a different time, usually with no awareness of the others. There is no single place that says "these are the only valid combinations." The set of *possible* states grows as $2^n$ for $n$ booleans, but the set of *legal* business states is usually a tiny fraction of that — and nothing enforces the difference.

The fix is to stop thinking in flags and start thinking in **states** and **transitions** — a finite state machine. An order isn't "paid AND shipped AND not-cancelled" — it's in exactly ONE state at a time: `CREATED`, or `PAID`, or `SHIPPED`, or `CANCELLED`, or `DELIVERED`. Never two at once, because there's only one `status` column, not five independent ones. And the crucial second half of the pattern: you don't just declare the states, you declare which **transitions** between them are legal. `SHIPPED → CANCELLED`? Not allowed — you can't unship a package with a status flip; that needs its own `RETURN_INITIATED` state and a real return process. `CANCELLED → COMPLETED`? Never — reject that transition outright, in code, before it ever reaches the database.

This exact shape — a small number of states, a small number of legal transitions, escape hatches to `CANCELLED`/`FAILED` from almost anywhere — shows up over and over: payments (061), food delivery (062), ticket booking (065/091), hotel booking (066), job schedulers (070), stock trading (073). It's not a coincidence; it's the natural shape of "something moves through a real-world process with a point of no return and a possibility of failure at each step." Once you see it in one domain, you see it everywhere.

---

## PART 2 — THE STATE MACHINE ARCHITECTURE DIAGRAMS

### Canonical Shape: Order Lifecycle State Machine

```
                          ┌─────────────┐
                          │   CREATED   │  (order row inserted, cart → order)
                          └──────┬──────┘
                                 │ event: PaymentAuthorized
                                 v
                          ┌─────────────┐
                    ┌─────┤   PENDING   │  (awaiting payment capture / fraud check)
                    │     └──────┬──────┘
      event:        │            │ event: PaymentCaptured
   PaymentFailed     │            v
                    │     ┌─────────────┐
                    │     │  CONFIRMED  │  (payment settled, inventory reserved)
                    │     └──────┬──────┘
                    │            │ event: HandedToCarrier
                    │            v
                    │     ┌─────────────┐
                    │     │   SHIPPED   │  (in transit, tracking number issued)
                    │     └──────┬──────┘
                    │            │ event: CarrierConfirmedDelivery
                    │            v
                    │     ┌─────────────┐
                    │     │  DELIVERED  │  ◄── terminal (happy path)
                    │     └─────────────┘
                    │
                    │  event: CustomerCancelled (only from CREATED/PENDING/CONFIRMED)
                    v
             ┌─────────────┐        event: RefundProcessed      ┌─────────────┐
             │  CANCELLED  ├───────────────────────────────────►│  REFUNDED   │ ◄── terminal
             └─────────────┘                                    └─────────────┘
                    ^
                    │ event: PaymentDeclined / InventoryUnavailable
                    │
             ┌─────────────┐
             │   FAILED    │ ◄── terminal (never charged, or charge reversed same-flow)
             └─────────────┘

Legend:
  - Every arrow = ONE row in the transition table (currentState, event) → newState
  - CANCELLED/FAILED are reachable from MULTIPLE states (CREATED, PENDING, CONFIRMED)
    but NOT from SHIPPED or DELIVERED — those need a separate RETURN/REFUND flow,
    not a backward transition, because physical goods are already in motion.
  - DELIVERED and REFUNDED are terminal: no outgoing arrows. The transition
    table simply has no rows with these as (currentState, *) — any attempted
    transition from them is rejected by definition (missing lookup = illegal).
```

### Persistence: status Column + Append-Only status_history

```
Table: orders                             Table: order_status_history
┌────────────┬───────────┬─────────┐      ┌────┬──────────┬────────────┬────────────┬──────────────┬─────────────────┐
│ order_id   │ status    │ version │      │ id │ order_id │ from_state │ to_state   │ occurred_at  │ actor / reason  │
├────────────┼───────────┼─────────┤      ├────┼──────────┼────────────┼────────────┼──────────────┼─────────────────┤
│ ord-8841   │ SHIPPED   │ 4       │      │ 1  │ ord-8841 │ NULL       │ CREATED    │ 09:00:00.120 │ system:checkout │
└────────────┴───────────┴─────────┘      │ 2  │ ord-8841 │ CREATED    │ PENDING    │ 09:00:01.400 │ system:payment  │
     ▲                                    │ 3  │ ord-8841 │ PENDING    │ CONFIRMED  │ 09:00:03.900 │ system:payment  │
     │ single mutable field,              │ 4  │ ord-8841 │ CONFIRMED  │ SHIPPED    │ 11:32:10.000 │ user:warehouse7 │
     │ ALWAYS updated in the              └────┴──────────┴────────────┴────────────┴──────────────┴─────────────────┘
     │ SAME transaction as the                        ▲
     │ history insert                                 │ append-only, NEVER updated or deleted
     │                                                │ — this is your audit trail for support/disputes/analytics
     └────────────────────────────────────────────────┘

BEGIN;
  -- 1. Guard: verify current status matches expected pre-transition state
  --    (also acts as the optimistic-concurrency check via `version`)
  SELECT status, version FROM orders WHERE order_id = 'ord-8841' FOR UPDATE;
  -- app checks: status == 'CONFIRMED' and (currentState, 'HandedToCarrier') is
  -- a legal transition per the transition table — reject with 409 if not

  -- 2. Apply the transition
  UPDATE orders
    SET status = 'SHIPPED', version = version + 1, updated_at = now()
    WHERE order_id = 'ord-8841' AND version = 3;   -- version check = idempotency guard

  -- 3. Record it, forever, in the same transaction
  INSERT INTO order_status_history (order_id, from_state, to_state, occurred_at, actor)
    VALUES ('ord-8841', 'CONFIRMED', 'SHIPPED', now(), 'user:warehouse7');
COMMIT;
-- Either both rows change or neither does. No "status says SHIPPED but no
-- history record exists" — that gap is exactly what makes disputes unresolvable.
```

### Edge Case: Duplicate/Out-of-Order Events Hitting the State Machine

```
Scenario: warehouse scanner sends "HandedToCarrier" TWICE due to a network
retry (client never got the 200 OK, so it resent the same webhook).

Event 1: HandedToCarrier arrives
  current status = CONFIRMED
  transition table lookup: (CONFIRMED, HandedToCarrier) → SHIPPED   ✓ legal
  UPDATE ... SET status='SHIPPED', version=4 WHERE version=3        ✓ 1 row affected
  → emits OrderShipped event, sends "your order shipped" push notification

Event 2: HandedToCarrier arrives AGAIN (retry, same idempotency key)
  current status = SHIPPED  (already transitioned!)
  transition table lookup: (SHIPPED, HandedToCarrier) → NOT FOUND   ✗ illegal
  → REJECTED. No double transition, no duplicate "your order shipped" push,
    no double-processing.
  → Optionally: log as a no-op/duplicate-event metric, return 200 OK anyway
    (idempotent from the CALLER's perspective — retries are safe to send)

Scenario: message queue redelivers events out of order (rare, but happens
under partition rebalances — see 097-kafka-log-compaction-tombstones.md
for why consumers must tolerate redelivery)

Event arrives: PaymentCaptured (expects PENDING → CONFIRMED)
  current status = CANCELLED (customer cancelled AFTER payment event was
                   queued but BEFORE it was consumed — a real race)
  transition table lookup: (CANCELLED, PaymentCaptured) → NOT FOUND  ✗ illegal
  → REJECTED, and this is exactly correct: the order was already
    cancelled, capturing payment into a CONFIRMED state now would be a
    silent data-integrity bug (charged the customer for a cancelled order).
  → This rejection should trigger an automatic refund workflow, not just
    a swallowed error — "illegal transition" is a signal to route to a
    compensating action, not just log-and-ignore.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### The Transition Table (The Actual Guard)

```java
public enum OrderState {
    CREATED, PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED, FAILED, REFUNDED
}

public enum OrderEvent {
    PaymentAuthorized, PaymentCaptured, PaymentFailed, PaymentDeclined,
    HandedToCarrier, CarrierConfirmedDelivery, CustomerCancelled,
    InventoryUnavailable, RefundProcessed
}

// The transition table IS the business rule — explicit, exhaustive,
// and rejects anything not listed. This is the whole pattern.
public class OrderStateMachine {

    private static final Map<OrderState, Map<OrderEvent, OrderState>> TRANSITIONS =
        Map.of(
            OrderState.CREATED, Map.of(
                OrderEvent.PaymentAuthorized, OrderState.PENDING,
                OrderEvent.CustomerCancelled, OrderState.CANCELLED
            ),
            OrderState.PENDING, Map.of(
                OrderEvent.PaymentCaptured, OrderState.CONFIRMED,
                OrderEvent.PaymentFailed, OrderState.FAILED,
                OrderEvent.CustomerCancelled, OrderState.CANCELLED
            ),
            OrderState.CONFIRMED, Map.of(
                OrderEvent.HandedToCarrier, OrderState.SHIPPED,
                OrderEvent.InventoryUnavailable, OrderState.CANCELLED,
                OrderEvent.CustomerCancelled, OrderState.CANCELLED
            ),
            OrderState.SHIPPED, Map.of(
                OrderEvent.CarrierConfirmedDelivery, OrderState.DELIVERED
                // NOTE: no CustomerCancelled entry here on purpose —
                // once shipped, cancellation must go through a RETURN flow,
                // not a state machine backward edge.
            ),
            OrderState.CANCELLED, Map.of(
                OrderEvent.RefundProcessed, OrderState.REFUNDED
            )
            // DELIVERED, FAILED, REFUNDED: deliberately absent from the map
            // → any event against them is automatically "no transition found"
        );

    public OrderState apply(OrderState current, OrderEvent event) {
        Map<OrderEvent, OrderState> legalNext = TRANSITIONS.getOrDefault(current, Map.of());
        OrderState next = legalNext.get(event);
        if (next == null) {
            // This is the guard — reject, don't silently accept
            throw new IllegalStateTransitionException(
                "Cannot apply " + event + " to order in state " + current);
        }
        return next;
    }
}
```

### Applying a Transition Idempotently (Spring + JDBC)

```java
@Service
public class OrderTransitionService {

    private final JdbcTemplate jdbc;
    private final OrderStateMachine stateMachine;
    private final ApplicationEventPublisher eventPublisher;

    @Transactional
    public void transition(String orderId, OrderEvent event, String actor) {
        // SELECT ... FOR UPDATE: row lock prevents a concurrent transition
        // on the SAME order from racing this one (two warehouse scans,
        // two webhook retries, etc.)
        OrderRow row = jdbc.queryForObject(
            "SELECT status, version FROM orders WHERE order_id = ? FOR UPDATE",
            (rs, i) -> new OrderRow(OrderState.valueOf(rs.getString("status")), rs.getInt("version")),
            orderId);

        OrderState nextState = stateMachine.apply(row.status(), event); // throws if illegal

        int rowsUpdated = jdbc.update(
            "UPDATE orders SET status = ?, version = version + 1, updated_at = now() " +
            "WHERE order_id = ? AND version = ?",
            nextState.name(), orderId, row.version());

        if (rowsUpdated == 0) {
            // version mismatch = a concurrent writer beat us — safer to
            // fail loudly and let the caller retry than to silently skip
            throw new ConcurrentModificationException("Order " + orderId + " changed concurrently");
        }

        jdbc.update(
            "INSERT INTO order_status_history (order_id, from_state, to_state, occurred_at, actor) " +
            "VALUES (?, ?, ?, now(), ?)",
            orderId, row.status().name(), nextState.name(), actor);

        // Same-transaction outbox write, NOT a direct Kafka publish —
        // see 005-distributed-transactions-saga.md and the outbox
        // pattern in 008-cdc-change-data-capture-debezium.md for why
        jdbc.update(
            "INSERT INTO outbox (aggregate_id, event_type, payload) VALUES (?, ?, ?::jsonb)",
            orderId, "Order" + nextState.name(),
            "{\"orderId\":\"" + orderId + "\",\"newState\":\"" + nextState + "\"}");
    }
}
```

### Real Numbers: Why This Matters at Scale

```
Observed in a mid-size e-commerce platform (illustrative, order-of-magnitude):

  Orders/day:                 ~400,000
  Avg transitions per order:  ~5 (CREATED→PENDING→CONFIRMED→SHIPPED→DELIVERED)
  status_history rows/day:    ~2,000,000
  Row size (history table):   ~180 bytes avg (order_id + 2 enums + timestamp + actor)
  Storage growth:              ~360 MB/day, ~130 GB/year — cheap, append-only,
                               indexed by (order_id, occurred_at) for fast lookup

  Illegal-transition rejections observed in production logs (real signal
  of bugs/races caught BEFORE they became data corruption):
    ~0.3-0.8% of all transition attempts — mostly duplicate webhook
    retries and out-of-order queue redelivery, exactly as modeled above.
    Without the guard, a meaningful fraction of these would have silently
    corrupted order state (double-shipped, double-refunded, etc.)

  Optimistic-lock (version column) conflict rate under concurrent writers:
    ~0.05-0.2% of transitions — retried automatically by the caller
    (webhook processor / queue consumer) with exponential backoff,
    see 045-retry-exponential-backoff-jitter.md
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Design the order lifecycle for an e-commerce checkout system — from cart to delivery, including cancellations and refunds. How do you make sure the system never ends up in an inconsistent state, like a cancelled order that somehow gets shipped?"

**You (architect answer):**

> "I model the order lifecycle as an explicit finite state machine rather than a set of independent boolean flags. There's a single `status` column — `CREATED`, `PENDING`, `CONFIRMED`, `SHIPPED`, `DELIVERED`, `CANCELLED`, `FAILED`, `REFUNDED` — and exactly one of those values is true at any moment, by construction. That immediately rules out the class of bug where `is_cancelled` and `is_shipped` are both true, because there's no second flag to disagree with the first.
>
> The core of the design is a transition table: an explicit map of `(currentState, event) → nextState`. Anything not in that map is rejected. So `SHIPPED` plus a `CustomerCancelled` event isn't silently allowed to flip a flag — it's just not in the table, and the state machine throws before it ever reaches the database. Once something ships, cancellation has to go through a separate return/refund flow, because you can't undo a package that's already with a carrier.
>
> For persistence, every transition updates the `status` column AND inserts a row into an append-only `order_status_history` table, in the same database transaction — so I never have a status without a matching audit trail. That history table is what support and the fraud/dispute teams query when a customer says 'I was charged but my order shows cancelled' — I can show them the exact sequence of transitions, timestamps, and which actor triggered each one.
>
> I also treat every transition as idempotent using an optimistic-concurrency version column. Webhook retries and queue redelivery are a fact of life — a 'HandedToCarrier' event might arrive twice. The second attempt sees the order already in `SHIPPED`, looks up `(SHIPPED, HandedToCarrier)` in the transition table, finds nothing, and safely no-ops instead of double-processing or sending a duplicate notification.
>
> The operational concern I'd flag: illegal-transition rejections are actually a useful signal, not just noise to suppress. I'd track the rejection rate as a metric — if it spikes, that usually means either a client is misbehaving (double-firing webhooks) or there's a real race condition upstream, like a cancellation and a payment-capture event arriving out of order from a message queue. Rather than silently swallowing the rejected event, I route it to a manual-review or compensating-action queue — for example, if a payment gets captured against an already-cancelled order, that should automatically trigger a refund, not just log an error and move on."

---

## PART 5 — DECISION FRAMEWORK

### State Machine vs Boolean Flags vs Alternatives

| Approach | How It Works | Tradeoff | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **Explicit state machine + transition table** | Single `status` enum column, transitions validated against a lookup table | Requires upfront design of all states/events; rigid by design (a feature) | ~0ms (in-memory map lookup) | Medium | Underspecified transition table lets an unanticipated event slip through as a no-op instead of a hard error |
| **Boolean flags (`is_paid`, `is_shipped`...)** | Independent columns set by different code paths | Impossible-state combinations are trivially reachable; no single source of truth | ~0ms | Low (deceptively) | Any code path that forgets to check another flag creates a silent contradiction |
| **Status string with no transition guard** | `status` column exists, but any code can `UPDATE status = X` freely | Slightly better than booleans (one field) but still allows illegal jumps like CANCELLED→DELIVERED | ~0ms | Low | No enforcement — same failure mode as flags, just consolidated into one column |
| **Workflow engine (e.g. Temporal, Camunda)** | External engine owns state transitions, retries, and long-running orchestration | Adds an infrastructure dependency and operational surface area | 10-100ms (engine round-trip) | High | Overkill for simple linear lifecycles; justified when steps involve long waits (days) or complex compensation logic |
| **Event sourcing (state = replay of events)** | No `status` column at all — state is derived by folding the event log | Full history "for free," but every read needs a replay or a projection | Read: ~1-5ms with a materialized projection; without one, scales with event count | High | Requires disciplined snapshotting/projections or reads get slower as history grows — see 025-cqrs-event-sourcing.md |

### When the State Machine Pattern Is Right

```
✓ Any entity with a clear real-world lifecycle and a "point of no return"
  (payment captured, order shipped, ride started, seat ticketed)
✓ Multiple services/teams need to react to specific transitions
  (notification service on OrderShipped, warehouse on OrderConfirmed)
✓ Compliance/dispute resolution requires "prove what happened and when"
✓ Duplicate or out-of-order events are a realistic operational concern
  (webhooks, message queues, distributed retries — i.e. almost always)
✓ You want illegal transitions to be structurally impossible, not just
  "checked with an if-statement somewhere, hopefully everywhere"
```

### Skip the Full Pattern When

```
✗ The entity genuinely has independent, orthogonal attributes that
  really can combine freely (e.g. `is_featured` + `is_verified` on a
  user profile — these aren't lifecycle states, they're just flags)
✗ The lifecycle is truly linear with no branching, no cancellation,
  and no concurrent writers — a single status column without a formal
  transition table MAY be acceptable for a low-stakes internal tool
✗ You need long-running human-in-the-loop orchestration spanning days
  with complex compensation — reach for a workflow engine instead of
  hand-rolling the state machine
```

---

## QUICK REFERENCE CARD

```
CORE PRINCIPLE:
  One status enum column, NOT N boolean flags.
  Transition table = Map<(CurrentState, Event), NextState>.
  Anything not in the table is REJECTED, not silently allowed.

STANDARD SHAPE:
  CREATED/PENDING → CONFIRMED/PROCESSING → COMPLETED/DELIVERED
  CANCELLED/FAILED/REFUNDED reachable from multiple early states,
  NEVER from post-point-of-no-return states (SHIPPED, DELIVERED).

PERSISTENCE PATTERN (same transaction, always):
  UPDATE main_table SET status = ?, version = version + 1 WHERE version = ?;
  INSERT INTO status_history (from_state, to_state, occurred_at, actor);
  INSERT INTO outbox (event_type, payload);   -- for downstream services

IDEMPOTENCY GUARD:
  version column (optimistic concurrency) + transition-table lookup
  → duplicate/replayed events become safe no-ops, not double-processing

INTEGRATION:
  Each transition emits a domain event (OrderConfirmed, OrderShipped)
  via the OUTBOX pattern (same TX as the status update) —
  see 005-distributed-transactions-saga.md, 025-cqrs-event-sourcing.md
```

---
