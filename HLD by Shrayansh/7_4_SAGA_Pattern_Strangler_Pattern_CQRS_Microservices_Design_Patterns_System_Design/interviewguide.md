# Interview Guide: Strangler Fig Pattern, Saga Pattern & CQRS

## 🗣️ The Interview Scenario

> "You have a live production monolith processing millions of transactions a day, and management wants it migrated to microservices with zero downtime. First — how do you actually cut traffic over without a big-bang rewrite? Second — once you have separate services with separate databases, how do you keep a multi-service business transaction (like a payment) consistent without a shared database transaction? Third — how do you handle queries that used to be a simple SQL join across tables that now live in different services' databases?"

This single scenario chains together the three most commonly tested microservices patterns: **migration strategy (Strangler Fig)**, **distributed transaction consistency (Saga)**, and **cross-service querying (CQRS)**.

## 🏗️ Architect's Explanation (For a New Developer)

**Strangler Fig Pattern** is named after a real vine that grows around a host tree and, over years, gradually replaces it entirely without the tree ever falling down all at once. In software terms: you never do a risky "flip the switch" migration from monolith to microservices. Instead, you put a **controller/router in front of both systems**, and gradually redirect small slices of live traffic (say, 10%) to the new microservice while the rest keeps flowing to the monolith. If it works, you dial the percentage up. If something breaks, you dial it back down to zero instantly. Over time, the monolith's share shrinks to nothing and you delete it — the "vine" has fully replaced the "tree," with zero big-bang risk.

**Saga Pattern** solves a very specific pain: once each microservice has its **own separate database**, you can no longer wrap a multi-service business operation (e.g., "place order → update inventory → charge payment") in one classic ACID transaction, because ACID transactions don't span multiple independent databases. Saga's answer: break the operation into a **sequence of local transactions**, each one committing to its own service's database and then firing an event that triggers the next step. If any step fails, previously completed steps are undone using explicit **compensating transactions** (the opposite operation) — rather than a database-level rollback.

**CQRS (Command Query Responsibility Segregation)** solves the "I can't JOIN across two different services' databases anymore" pain. It splits **write operations** (Create/Update/Delete — the "Command" side) from **read operations** (Select — the "Query" side), maintaining a separate, denormalized read-optimized store that's kept in sync (usually via events) so that queries needing data "joined" across what used to be multiple tables/services can just read from one pre-joined view instead of trying to join live across service boundaries.

## 📊 Visualize It

```
STRANGLER FIG PATTERN — gradual traffic cutover

           ┌─────────────┐
Traffic ──▶│  Controller │
           └─────────────┘
             90% ↓      ↓ 10% (start small, ramp up over time)
      ┌─────────────┐ ┌──────────────┐
      │  Monolith    │ │ New Microsvc │
      └─────────────┘ └──────────────┘
   If microservice fails → dial its % back to 0% instantly, no big-bang risk
   Over time: 10% → 40% → 100%, then delete the monolith flow entirely
```

```
SAGA PATTERN — sequence of local transactions + compensation on failure

  Balance Svc          Payment Svc
  ┌──────────┐  event   ┌───────────┐
  │ -$10     │─────────▶│ record    │
  │ (local   │          │ payment   │
  │  txn OK) │          │ (FAILS)   │
  └──────────┘          └───────────┘
        ▲                     │
        └────compensating─────┘
             transaction: +$10
             (undo the local debit, since payment never completed)
```

```
CQRS — separate write model and read model

  WRITES (Command)              READS (Query)
  ┌────────┐ ┌────────┐         ┌───────────────────┐
  │ DB1    │ │ DB2    │  events │ Denormalized       │
  │(Svc1)  │ │(Svc2)  │────────▶│ "History" read DB  │
  └────────┘ └────────┘         │ (already "joined") │
                                 └───────────────────┘
   Client queries the read DB directly — no live cross-service join needed
```

## 🔧 Deep Dive: How It Actually Works

### Strangler Fig Pattern — refactoring a live monolith into microservices

- **When to use it:** specifically for **refactoring** an already-live monolith into microservices (as opposed to greenfield microservices design). You've already used a decomposition pattern (Business Capability / DDD) to decide *how* to split things — Strangler Fig answers *how to cut traffic over safely*.
- **Mechanism:** introduce a **controller** in front of both the monolith and the new microservice. Route a small percentage of live traffic (the transcript uses **10%** as the starting point) to the new microservice path, keeping the rest on the monolith.
- **Ramp-up:** as confidence grows (bugs found and fixed at 10% are far cheaper than bugs found at 100%), gradually increase the percentage routed to the new service — the transcript describes this as "slowly, slowly" increasing until you eventually reach 100%.
- **Safety valve:** if an issue is discovered at any point, the controller can immediately route **0%** back to the microservice (fully reverting to the monolith) while the bug is fixed, then resume ramping up.
- **End state:** once 100% of traffic is confidently on the microservice path for a given flow, the corresponding monolith code path becomes dead and is eventually deleted. This whole process repeats **flow by flow** — you never attempt to migrate the entire monolith to microservices in one shot; you strangle it out gradually, one capability/flow at a time.

### Two data-ownership models set up before Saga makes sense

- **Database-per-service:** each independent microservice owns its own database exclusively.
- **Shared database:** multiple services share one common database.
- The transcript frames Saga and CQRS as solutions specifically needed **because of the database-per-service model** — shared database keeps cross-table joins and ACID transactions easy but reintroduces monolith-like coupling; database-per-service gives real independence but loses easy joins and shared transactions, which is exactly the gap Saga and CQRS fill.

### Saga Pattern — sequence of local transactions

**Formal definition used:** *a sequence of local transactions.*

**Walkthrough with the Order/Inventory/Payment example:**
1. A "Place Order" request arrives, and logically it must touch three separate databases: Order DB, Inventory DB, Payment DB.
2. **Order service** commits its own local transaction (creates the order row) and publishes an event.
3. **Inventory service** listens for that event, commits its own local transaction (updates stock), and publishes its own event.
4. **Payment service** listens and attempts its local transaction — but this time it **fails**.
5. Because there's no shared ACID transaction across all three databases, you cannot simply "rollback" like you would in a monolith. Instead, each prior successful step must be **explicitly undone** via a **compensating transaction** — e.g., Inventory service reverses the stock update it already committed, Order service reverses/cancels the order it already created — triggered by a **compensation/failure event** flowing backward through the chain.

**Concrete balance-transfer example used to illustrate compensation:** Two components — a `Balance` service (tracks how much money a user has) and a `Payment` service (records that a payment happened between two people). Flow: `MakePayment(₹10)` request arrives → first, `Balance` service is checked/debited (₹100 → ₹90), local transaction commits → then `Payment` service attempts to record the payment transaction but **fails**. Resolution: this triggers a **compensating transaction on the Balance service** (add back ₹10, restoring ₹100) via a failure event, since the payment itself was never actually completed successfully.

**Two implementation styles for Saga:**
- **Choreography:** there is no central coordinator. Every service listens to relevant events on a shared event bus/message queue and reacts independently, publishing its own follow-up events. **Drawback called out explicitly:** this can create **circular dependencies** between services (Service A listens to Service B's events, but Service B also ends up needing to listen to Service A's events in some flow), making the overall event graph harder to reason about.
- **Orchestration:** a dedicated **orchestrator** component exists that directly calls Service 1, then based on its reply calls Service 2, then Service 3 in sequence, centrally managing the entire flow. If Service 2 fails, the orchestrator is directly responsible for telling Service 1 to roll back (compensate); if Service 3 fails, the orchestrator tells Service 2 to roll back. This removes the circular-dependency risk of choreography by centralizing the flow logic in one place.

**Explicit interview framing given:** Saga is very commonly tested, and a typical interview question is literally the balance-transfer scenario above — "how would you make this consistent using Saga," expecting you to describe the compensating-transaction mechanism by name.

### CQRS (Command Query Responsibility Segregation)

- **Command** = write-side operations: Create, Update, Delete.
- **Query** = read-side operations: Select.
- **Why it's needed:** with database-per-service, you lose the ability to do a simple SQL join across tables that now live in physically separate databases owned by different services (Service 1's table, Service 2's table — no direct join possible).
- **Mechanism:** stand up a **separate read-optimized database/view** (the transcript calls it a "common history view" table) whose sole purpose is serving reads that would otherwise require a cross-service join. Meanwhile, the actual Create/Update/Delete operations continue to happen against each service's own dedicated database as normal.
- **Keeping the read view in sync:** whenever a create/update/delete happens in a service's own database, that service **publishes an event**; a listener consumes that event and applies the same change to the shared read view/table, so it stays up to date without ever requiring a live cross-database join. (Alternative sync mechanisms mentioned: change-data-capture-style log tailing, or scheduled/regular procedures that periodically reconcile the read view.)
- **Net effect:** reads that used to be "just join these tables" become "query the pre-built, already-joined read view" — trading some sync-latency and extra infrastructure for the ability to keep write-side databases fully independent per service.

## 🔥 Real Production Incident & Fix

**What broke:** A travel-booking platform migrated its booking flow to microservices using **choreography-based Saga**: `BookingService`, `InventoryService`, and `PaymentService` all listened to each other's events on a shared bus. Over several sprints, engineers on different teams each added "just one more" event subscription to unblock their own feature, and eventually `InventoryService` ended up listening to an event that `PaymentService` published, while `PaymentService` also listened to an event `InventoryService` published for an unrelated refund flow — an accidental **circular dependency**.

**How it was detected:** During a partial refund flow, a specific edge case caused an infinite loop of events bouncing between `InventoryService` and `PaymentService`, which was first noticed as **Kafka consumer lag spiking abnormally** on both services' topics in the monitoring dashboard, followed by **CPU/memory alerts** on both services as they kept reprocessing the same event chain. The on-call engineer had to manually trace event correlation IDs through the message broker's topic logs to discover the cycle, since no single service's logs showed the full picture.

**Root cause:** Choreography-based Saga was adopted without any centralized ownership of "who is allowed to listen to what," and incremental, uncoordinated additions to event subscriptions over time created exactly the circular-dependency failure mode this pattern is known for.

**The fix:** The team migrated the booking flow's Saga implementation from choreography to **orchestration** — introducing a single `BookingOrchestrator` that explicitly calls `InventoryService`, then `PaymentService`, in a defined sequence, and is solely responsible for issuing compensating calls if any step fails. This eliminated the possibility of circular event dependencies entirely (there is no bus of mutually-subscribed events anymore, just direct orchestrator-to-service calls), and made the entire booking flow's logic auditable by reading one orchestrator class instead of tracing distributed event chains across three codebases.

```
BEFORE (choreography, accidental cycle):
  InventoryService ──event──▶ PaymentService ──event──▶ InventoryService ──event──▶ ...
                      (infinite loop under a specific edge case)

AFTER (orchestration, single source of truth):
  BookingOrchestrator ──calls──▶ InventoryService
                      ──calls──▶ PaymentService
                      (compensates directly if either step fails; no event cycle possible)
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why can't we just use a distributed/2-phase-commit transaction instead of Saga to keep multiple services' databases consistent?**
Distributed transactions across heterogeneous, independently-owned databases introduce tight coupling, blocking behavior, and availability risk (if any participant or the coordinator is slow/down, the whole transaction stalls), which directly contradicts the independence and availability goals that motivated microservices in the first place. Saga trades strict, immediate atomicity for eventual consistency achieved through local transactions plus explicit compensating actions, which fits much better with independently deployable, independently scalable services.

**Q2: What's the real difference between choreography and orchestration in Saga, and when would you pick one over the other?**
Choreography has no central coordinator — each service reacts to events independently, which is simpler to start with but risks circular dependencies and makes the overall flow hard to trace as it grows, as seen in the booking-platform incident. Orchestration centralizes the sequencing and compensation logic in one orchestrator component, making the flow easier to reason about and audit at the cost of that orchestrator becoming a more critical, potentially more complex component — generally preferred for complex, multi-step business flows where correctness and traceability matter more than architectural simplicity.

**Q3: How does the Strangler Fig pattern reduce risk compared to a full cutover migration?**
It routes only a small percentage of live traffic to the new microservice initially, so any bug or performance issue affects a small fraction of real users rather than everyone, and can be instantly reverted by dialing the percentage back to zero. This turns a single high-stakes migration event into a series of small, reversible, low-risk increments, letting the team gain confidence gradually before fully retiring the monolith's code path.

**Q4: Why does CQRS require an extra synchronization mechanism, and what happens if that sync lags?**
Because the read-optimized view is a separate store from the source-of-truth write databases, it can only be updated after the fact (typically via an event published on write), which means there's an inherent, if usually small, delay before a write is reflected in the read view — a form of eventual consistency on the read side. If sync lags significantly, users could see stale query results (like an order status that hasn't caught up to the actual booking state), so teams need to monitor and bound the replication lag of the read view.

**Q5: In the Saga pattern, what exactly is a "compensating transaction," and is it the same as a database rollback?**
A compensating transaction is a business-logic-level operation that reverses the effect of a previously committed local transaction — like crediting back money that was previously debited — because there is no cross-database rollback mechanism available once each service has already committed independently to its own database. It is fundamentally different from a database rollback: it's a new, explicit "undo" transaction that must be designed and implemented per step, and it must itself be idempotent and reliable since it's just another write that could also fail.

**Q6: Does adopting database-per-service always require both Saga and CQRS, or are they independent decisions?**
They solve different problems and can be adopted independently: Saga addresses cross-service transactional consistency for multi-step writes, while CQRS addresses cross-service query/join capability for reads. A system might need Saga because it has multi-service write workflows but might not need CQRS if its query patterns never actually require joining data across service boundaries, and vice versa — the decision should be driven by which specific pain point (write consistency vs. read/join complexity) the team is actually experiencing.

## 🔑 Key Takeaway

Strangler Fig is how you migrate to microservices safely (gradual traffic percentage cutover, instant rollback), Saga is how you keep a multi-service write consistent without a shared database transaction (sequence of local transactions plus compensating actions, via choreography or orchestration), and CQRS is how you keep cross-service reads/joins possible once each service owns its own database (a separately maintained, event-synced read view) — know all three by name and know exactly which specific pain point each one solves.
