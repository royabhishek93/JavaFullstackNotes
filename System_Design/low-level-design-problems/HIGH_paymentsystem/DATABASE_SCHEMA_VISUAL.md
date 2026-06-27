# Database Schema Visual Guide - Payment System

## Complete ER Diagram

```
┌─────────────────────────────────┐
│          MERCHANTS              │
│─────────────────────────────────│
│ 🔑 id (UUID)                    │
│    name                         │
│    status                       │
│    created_at                   │
└───────────────┬─────────────────┘
                │
                │ owns
                ▼
┌─────────────────────────────────┐
│        PAYMENT_ORDERS           │
│─────────────────────────────────│
│ 🔑 id (UUID)                    │
│ 🔗 merchant_id (merchants.id)   │
│    customer_id                  │
│    amount                       │
│    currency                     │
│    status                       │
│    idempotency_key              │
│    version                      │
│    created_at                   │
│    updated_at                   │
└───────────┬─────────────┬───────┘
            │             │
            │ has many    │ has many
            ▼             ▼
┌─────────────────────┐   ┌─────────────────────────────┐
│  PAYMENT_ATTEMPTS   │   │         REFUNDS             │
│─────────────────────│   │─────────────────────────────│
│ 🔑 id (UUID)        │   │ 🔑 id (UUID)                │
│ 🔗 order_id         │   │ 🔗 order_id                 │
│    gateway          │   │    amount                   │
│    gateway_txn_id   │   │    reason                   │
│    status           │   │    status                   │
│    attempt_no       │   │    gateway_refund_id        │
│    created_at       │   │    created_at               │
└──────────┬──────────┘   └───────────┬─────────────────┘
           │                          │
           │ reconciled via           │ posts
           ▼                          ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐
│        WEBHOOK_EVENTS       │   │        LEDGER_ENTRIES       │
│─────────────────────────────│   │─────────────────────────────│
│ 🔑 id (UUID)                │   │ 🔑 id (UUID)                │
│    gateway                  │   │    txn_group_id             │
│    gateway_event_id         │   │    account_id               │
│    event_type               │   │    side (DEBIT/CREDIT)      │
│    payload_hash             │   │    amount                   │
│    processed_at             │   │    reference_type           │
│    created_at               │   │    reference_id             │
└─────────────────────────────┘   │    created_at               │
                                  └─────────────────────────────┘
```

## Constraints (Must Have)
- UNIQUE `(merchant_id, idempotency_key)` on `payment_orders`
- UNIQUE `(order_id, attempt_no)` on `payment_attempts`
- UNIQUE `gateway_event_id` on `webhook_events`
- CHECK `amount > 0` for financial tables

## Status Notes
- `payment_orders.status`: CREATED, PROCESSING, CAPTURED, FAILED, REFUNDED
- `payment_attempts.status`: INITIATED, SUCCESS, FAILED, UNKNOWN
- `refunds.status`: REQUESTED, SUCCESS, FAILED
