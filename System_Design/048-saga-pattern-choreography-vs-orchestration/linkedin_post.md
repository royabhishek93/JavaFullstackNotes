# Saga Pattern — Choreography vs Orchestration — LinkedIn Post

## Post Text (copy-paste ready)

A refund compensating transaction that isn't idempotent can silently double-refund a user. Here's the pattern that prevents it.

- Saga = a sequence of local transactions + compensating transactions for rollback — no distributed lock, no 2PC coordinator that can freeze the whole system
- Choreography (event-driven, Kafka topics) is great for 2-3 step flows but becomes untraceable past 3-4 services — circular event loops and hidden coupling creep in
- Orchestration (a central saga orchestrator/state machine) wins for 5+ step flows — the entire flow lives in one place, but the orchestrator itself becomes a new coupling point to build and operate
- The idempotency trap: "refund $100" called twice on retry = user gets $200 back. Fix: "SET status=REFUNDED WHERE status != REFUNDED" + a processed_saga_steps dedup table
- Compensation must be a semantic undo, not a literal one — "mark item as removed" keeps your audit trail; rolling back the raw INSERT destroys it
- PhonePe/Paytm-style cross-bank transfers (debit → convert → credit) are the textbook orchestration saga: if currency conversion fails, the compensating transaction credits the source account back automatically via Temporal

Swipe to see: choreography vs orchestration trade-off table, the BAD vs GOOD compensating transaction, and the exact interview one-liner for "how do you keep 3 microservices atomic."

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
A non-idempotent refund compensating transaction can double-refund a user. Here's the Saga pattern that prevents it 👇

### Variant B — Long (400–600 chars)
Order placement touches inventory, payment, and shipment — three databases, no single transaction. Reach for 2PC and one slow service freezes everyone. The Saga pattern replaces the distributed lock with local transactions + compensating rollbacks. Choreography (Kafka events) suits simple 2-3 step flows; orchestration (a central state machine via Temporal) wins once you're past 5 services. The trap that catches almost everyone: compensating transactions that aren't idempotent — a retried "refund $100" call can double-refund unless you gate it with a status check and a dedup table.

---

## Best Time to Post
Tuesday, 9:00–10:00 AM IST (architecture/pattern deep-dives get strongest engagement early week when engineers are planning sprints)

## Engagement Hook
"Have you ever shipped a compensating transaction that wasn't idempotent and caused a double-refund or double-release in production? What caught it — an alert, or an angry customer?"
