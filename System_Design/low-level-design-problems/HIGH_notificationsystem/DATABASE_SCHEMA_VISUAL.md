# Database Schema Visual Guide - Notification System

## Complete ER Diagram

```
┌─────────────────────────────────┐
│         TEMPLATES               │
│─────────────────────────────────│
│ PK id (UUID)                    │
│    event_type                   │
│    channel                      │
│    subject_template             │
│    body_template                │
│    version                      │
│    is_active                    │
│    created_at                   │
└──────────────┬──────────────────┘
               │ used by
               ▼
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│    NOTIFICATION_REQUESTS        │         │        USER_PREFERENCES         │
│─────────────────────────────────│         │─────────────────────────────────│
│ PK id (UUID)                    │         │ PK id (UUID)                    │
│    producer_service             │         │    user_id                      │
│    user_id                      │         │    topic                        │
│    topic                        │         │    channel                      │
│    dedupe_key                   │         │    enabled                      │
│    priority                     │         │    quiet_hours_start            │
│    status                       │         │    quiet_hours_end              │
│    created_at                   │         │    created_at                   │
└──────────────┬──────────────────┘         └─────────────────────────────────┘
               │ has many
               ▼
┌─────────────────────────────────┐
│     NOTIFICATION_MESSAGES       │
│─────────────────────────────────│
│ PK id (UUID)                    │
│ FK request_id -> requests.id    │
│ FK template_id -> templates.id  │
│    channel                      │
│    rendered_subject             │
│    rendered_body                │
│    recipient_address            │
│    status                       │
│    scheduled_at                 │
│    next_attempt_at              │
│    created_at                   │
└──────────────┬──────────────────┘
               │ has many
               ▼
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│      DELIVERY_ATTEMPTS          │         │   PROVIDER_CALLBACK_EVENTS      │
│─────────────────────────────────│         │─────────────────────────────────│
│ PK id (UUID)                    │         │ PK id (UUID)                    │
│ FK message_id -> messages.id    │         │    provider                     │
│    provider                     │         │    provider_message_id          │
│    attempt_no                   │         │    event_type                   │
│    status                       │         │    payload_hash                 │
│    provider_message_id          │         │    processed_at                 │
│    error_code                   │         │    created_at                   │
│    created_at                   │         └─────────────────────────────────┘
└─────────────────────────────────┘
```

## Constraints
- UNIQUE `(producer_service, dedupe_key)` on `notification_requests`
- UNIQUE `(user_id, topic, channel)` on `user_preferences`
- UNIQUE `(message_id, attempt_no)` on `delivery_attempts`
- UNIQUE `provider_message_id` when provider guarantees uniqueness

## Status Enums
- notification_requests.status: RECEIVED, PROCESSING, COMPLETED, PARTIAL_FAILED, FAILED
- notification_messages.status: QUEUED, PROCESSING, SENT, DELIVERED, FAILED, DLQ
- delivery_attempts.status: INITIATED, SUCCESS, FAILED, UNKNOWN
