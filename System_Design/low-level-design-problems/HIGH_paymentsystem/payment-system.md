# Designing a Payment System (LLD)

## Requirements
1. Create payment order/intents before charging users.
2. Support multiple payment methods (UPI, card, netbanking, wallet).
3. Guarantee idempotency for client retries.
4. Handle gateway timeout and unknown outcome safely.
5. Support webhook-based final reconciliation.
6. Support full and partial refunds.
7. Maintain immutable ledger entries for audit and accounting.
8. Scale for high concurrency and avoid double charge.

## Core Services
1. `PaymentOrchestrator`
- Owns state machine transitions.
- Coordinates order, gateway, ledger, and webhook modules.

2. `IdempotencyService`
- Maps `(merchant_id, idempotency_key)` to a stable response.
- Prevents duplicate charge creation.

3. `GatewayRouter`
- Selects PSP by routing rules (cost, success rate, fallback).
- Supports pluggable provider adapters.

4. `LedgerService`
- Writes immutable debit/credit lines.
- Guarantees sum(debits) = sum(credits) per transaction group.

5. `WebhookProcessor`
- Verifies signature, deduplicates event IDs.
- Reconciles local state with gateway state.

6. `RefundService`
- Handles refund workflow with idempotency.
- Enforces max refundable amount.

## Key Entities
1. `PaymentOrder`
- `id, merchant_id, customer_id, amount, currency, status, idempotency_key, expires_at`

2. `PaymentAttempt`
- `id, payment_order_id, gateway, gateway_txn_id, status, attempt_no, error_code`

3. `LedgerEntry`
- `id, txn_group_id, account_id, side(DEBIT|CREDIT), amount, reference_type, reference_id`

4. `Refund`
- `id, payment_order_id, amount, reason, status, gateway_refund_id`

5. `WebhookEvent`
- `id, gateway, gateway_event_id, event_type, payload_hash, processed_at`

## Suggested APIs
```http
POST /v1/payment-orders
POST /v1/payment-orders/{id}/confirm
GET  /v1/payment-orders/{id}
POST /v1/payment-orders/{id}/refunds
POST /v1/webhooks/{gateway}
```

## State Machine (Order)
```text
CREATED -> PROCESSING -> AUTHORIZED -> CAPTURED -> SETTLED
                 |             |            |
                 |             |            +-> REFUND_PENDING -> REFUNDED
                 |             +-> FAILED
                 +-> FAILED
```

## Concurrency Strategy
- Use optimistic locking (`version`) on `payment_orders`.
- Unique key on `(merchant_id, idempotency_key)`.
- For critical transitions, lock order row (`SELECT ... FOR UPDATE`).

## Failure Scenarios
1. Gateway timeout after request sent
- Mark attempt `UNKNOWN`.
- Start reconciliation job + wait for webhook.

2. Duplicate client retry
- Return previous response from idempotency store.

3. Webhook arrives before client response
- Webhook updates final state; read API returns consistent latest status.

## Interview Q&A (Quick)
1. How do you prevent duplicate charges?
- Idempotency key + unique constraint + deterministic response caching.

2. Why ledger is immutable?
- Auditability and financial correctness. Corrections are compensating entries, not updates.

3. How do you handle eventual consistency?
- Order state + attempt state + webhook reconciliation + periodic gateway polling.
