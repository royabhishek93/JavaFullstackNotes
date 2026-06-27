# Database Schema Visual Guide - Parking Lot System

## Complete ER Diagram

```
┌──────────────────────────────┐
│         PARKING_LOTS         │
│──────────────────────────────│
│ PK id (UUID)                 │
│    name                      │
│    address                   │
│    city                      │
│    created_at                │
└──────────────┬───────────────┘
               │ has many
               ▼
┌──────────────────────────────┐
│        PARKING_FLOORS        │
│──────────────────────────────│
│ PK id (UUID)                 │
│ FK lot_id -> parking_lots.id │
│    floor_number              │
│    created_at                │
└──────────────┬───────────────┘
               │ has many
               ▼
┌──────────────────────────────┐      ┌──────────────────────────────┐
│        PARKING_SLOTS         │      │           VEHICLES           │
│──────────────────────────────│      │──────────────────────────────│
│ PK id (UUID)                 │      │ PK plate_number              │
│ FK floor_id -> floors.id     │      │    vehicle_type              │
│    slot_number               │      │    owner_id                  │
│    slot_type                 │      │    created_at                │
│    status                    │      └──────────────┬───────────────┘
│    created_at                │                     │ enters
│    updated_at                │                     ▼
└──────────────┬───────────────┘      ┌──────────────────────────────┐
               │ assigned via          │        PARKING_TICKETS       │
               └──────────────────────►│──────────────────────────────│
                                       │ PK id (UUID)                 │
                                       │ FK lot_id -> parking_lots.id │
                                       │ FK slot_id -> parking_slots.id│
                                       │ FK plate_number -> vehicles  │
                                       │    entry_time                │
                                       │    exit_time                 │
                                       │    status                    │
                                       │    idempotency_key           │
                                       │    created_at                │
                                       │    updated_at                │
                                       └──────────────┬───────────────┘
                                                      │ paid by
                                                      ▼
                                       ┌──────────────────────────────┐
                                       │           PAYMENTS           │
                                       │──────────────────────────────│
                                       │ PK id (UUID)                 │
                                       │ FK ticket_id -> tickets.id   │
                                       │    amount                    │
                                       │    payment_method            │
                                       │    status                    │
                                       │    transaction_ref           │
                                       │    paid_at                   │
                                       │    created_at                │
                                       └──────────────────────────────┘
```

## Constraints
- UNIQUE (floor_id, slot_number) on parking_slots
- UNIQUE (ticket_id) on payments for one-to-one payment per ticket
- UNIQUE (idempotency_key) on parking_tickets for retry-safe exit
- CHECK amount >= 0 on payments

## Status Enums
- parking_slots.status: AVAILABLE, OCCUPIED, OUT_OF_SERVICE
- parking_tickets.status: ACTIVE, CLOSED, LOST
- payments.status: PENDING, SUCCESS, FAILED
