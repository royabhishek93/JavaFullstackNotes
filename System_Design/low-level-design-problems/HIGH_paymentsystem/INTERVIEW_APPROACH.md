# Interview Approach - Payment System LLD

## 1) Start With Risk Framing
"Payments are correctness-critical. A tiny bug can double-charge users or lose money."

## 2) Present Core Guarantees
- Exactly-once effect per idempotency key (business level)
- No double spend on order state transitions
- Immutable ledger for audit trail
- Gateway/webhook reconciliation for unknown outcomes

## 3) Walk Through Happy Path
1. Create `payment_order` with idempotency key.
2. Create `payment_attempt` and call gateway.
3. On success, update order -> `CAPTURED` and write ledger entries.
4. Return stable response for retries.

## 4) Walk Through Failure Path
1. Timeout -> set attempt `UNKNOWN`.
2. Accept webhook with signature validation.
3. Reconcile state with gateway reference.
4. Update order once (idempotent transition).

## 5) Mention Scale Levers
- Gateway adapters + routing policy
- Async queue for webhook and reconciliation
- Hot indexes on `status`, `created_at`, and idempotency key
- Partition high-volume attempt table by date

## 6) Close With Trade-offs
- Strong consistency for order transition, eventual consistency for settlement reports.
- Simpler model first, then split into microservices when throughput/team size demands it.
