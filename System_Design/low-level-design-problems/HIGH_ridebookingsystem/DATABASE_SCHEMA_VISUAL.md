# Database Schema Visual Guide - Ride Booking System

## Complete ER Diagram

```
┌─────────────────────────────────┐
│            RIDERS               │
│─────────────────────────────────│
│ PK id (UUID)                    │
│    name                         │
│    phone                        │
│    rating                       │
│    created_at                   │
└──────────────┬──────────────────┘
               │ requests
               ▼
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│        RIDE_REQUESTS            │         │            DRIVERS              │
│─────────────────────────────────│         │─────────────────────────────────│
│ PK id (UUID)                    │         │ PK id (UUID)                    │
│ FK rider_id -> riders.id        │         │    name                         │
│    pickup_lat                   │         │    phone                        │
│    pickup_lng                   │         │    status                       │
│    drop_lat                     │         │    rating                       │
│    drop_lng                     │         │    created_at                   │
│    status                       │         └──────────────┬──────────────────┘
│    idempotency_key              │                        │ owns
│    estimated_fare               │                        ▼
│    created_at                   │         ┌─────────────────────────────────┐
└──────────────┬──────────────────┘         │            VEHICLES             │
               │ assigned via               │─────────────────────────────────│
               ▼                            │ PK id (UUID)                    │
┌─────────────────────────────────┐         │ FK driver_id -> drivers.id      │
│       RIDE_ASSIGNMENTS          │         │    vehicle_type                 │
│─────────────────────────────────│         │    plate_number                 │
│ PK id (UUID)                    │         │    color                        │
│ FK ride_request_id -> requests  │         │    created_at                   │
│ FK driver_id -> drivers.id      │         └─────────────────────────────────┘
│    status                       │
│    offered_at                   │
│    accepted_at                  │
│    expires_at                   │
└──────────────┬──────────────────┘
               │ creates
               ▼
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│             TRIPS               │         │           PAYMENTS              │
│─────────────────────────────────│         │─────────────────────────────────│
│ PK id (UUID)                    │         │ PK id (UUID)                    │
│ FK ride_request_id -> requests  │         │ FK trip_id -> trips.id          │
│ FK driver_id -> drivers.id      │         │    amount                       │
│ FK rider_id -> riders.id        │         │    method                       │
│    start_time                   │         │    status                       │
│    end_time                     │         │    transaction_ref              │
│    distance_km                  │         │    paid_at                      │
│    final_fare                   │         │    created_at                   │
│    status                       │         └─────────────────────────────────┘
│    created_at                   │
└─────────────────────────────────┘
```

## Constraints
- UNIQUE `(rider_id, idempotency_key)` on `ride_requests`
- UNIQUE active ride per driver
- UNIQUE accepted assignment per ride_request_id
- UNIQUE `plate_number` on vehicles

## Status Enums
- drivers.status: OFFLINE, AVAILABLE, BUSY
- ride_requests.status: CREATED, SEARCHING, DRIVER_ASSIGNED, IN_PROGRESS, COMPLETED, CANCELLED
- ride_assignments.status: OFFERED, ACCEPTED, REJECTED, EXPIRED
- trips.status: STARTED, COMPLETED, CANCELLED
- payments.status: PENDING, SUCCESS, FAILED
