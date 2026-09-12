# Distributed Transactions & Saga Pattern — LinkedIn Post

## Post Text (copy-paste ready)

A coordinator crash in 2-Phase Commit doesn't fail gracefully — it deadlocks forever.

- @Transactional can't save you across microservices — Order, Inventory, and Payment each have their own DB, and Spring has zero visibility across them
- 2PC is a blocking protocol: if the coordinator crashes between Phase 1 and Phase 2, participants hold locks forever waiting for a COMMIT that never comes
- Saga pattern replaces it: a sequence of local transactions, each with its own compensating transaction — choreography (event-driven, simple flows) or orchestration (central coordinator, complex flows)
- The trap nobody sees coming: sagas have zero ACID isolation. Saga A reserves 5 iPhones, Saga B reserves the remaining 5, Saga A's payment fails and "releases" its 5 back — but Saga B already shipped its 5. Inventory says 5 available, warehouse has 0.
- Compensating transactions aren't always possible — you can't un-ship a package already out for delivery. Fix: order irreversible actions LAST.

Swipe → to see the transactional outbox pattern that makes a DB write + Kafka event truly atomic.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
2PC deadlocks forever if the coordinator crashes mid-commit. Here's why Saga replaced it — and the trap that still catches people 👇

### Variant B — Long (400–600 chars)
@Transactional can't coordinate a commit across Order, Inventory, and Payment services — each has its own database. 2PC tried to solve this but it's a blocking protocol: a coordinator crash between phases leaves every participant holding locks forever. The Saga pattern fixes it with local transactions plus compensating transactions — but sagas have zero ACID isolation, so two concurrent sagas can both reserve the same inventory and cause a real lost-update bug. And some actions, like a physical shipment, simply can't be compensated once they happen.

---

## Best Time to Post
Friday, 9:00–10:00 AM IST (wraps the week's technical series content, strong save/share rate before the weekend)

## Engagement Hook
"Have you ever hit a 'lost update' bug across two concurrent sagas touching the same resource? How did you catch it?"
