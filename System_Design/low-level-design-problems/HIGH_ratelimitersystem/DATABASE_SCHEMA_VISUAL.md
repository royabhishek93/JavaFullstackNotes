# Database Schema Visual Guide - Rate Limiter System

## Complete ER Diagram

```
┌────────────────────────────────────┐
│       RATE_LIMIT_POLICIES          │
│────────────────────────────────────│
│ PK id (UUID)                       │
│    scope_type                      │
│    scope_value                     │
│    endpoint_pattern                │
│    algorithm                       │
│    limit_value                     │
│    window_sec                      │
│    burst_limit                     │
│    status                          │
│    created_at                      │
│    updated_at                      │
└──────────────┬─────────────────────┘
               │ overridden by
               ▼
┌────────────────────────────────────┐         ┌────────────────────────────────────┐
│         QUOTA_OVERRIDES            │         │        THROTTLE_EVENTS             │
│────────────────────────────────────│         │────────────────────────────────────│
│ PK id (UUID)                       │         │ PK id (UUID)                       │
│ FK policy_id -> policies.id        │         │    request_key                     │
│    tenant_id                       │         │    endpoint                        │
│    temporary_limit                 │         │    decision                        │
│    reason                          │         │    reason                          │
│    expires_at                      │         │    created_at                      │
│    created_at                      │         └────────────────────────────────────┘
└────────────────────────────────────┘


┌────────────────────────────────────┐
│         RATE_LIMIT_COUNTERS        │
│────────────────────────────────────│
│ PK key                             │
│    current_value                   │
│    window_start                    │
│    expires_at                      │
│    updated_at                      │
└────────────────────────────────────┘
```

## Constraints
- UNIQUE `(scope_type, scope_value, endpoint_pattern)` on `rate_limit_policies`
- UNIQUE active override per `(policy_id, tenant_id, endpoint_pattern)` if modeled that way
- TTL expiry on `rate_limit_counters`

## Status Enums
- rate_limit_policies.status: ACTIVE, DISABLED
- throttle_events.decision: ALLOW, DENY
- algorithms: FIXED_WINDOW, SLIDING_WINDOW, TOKEN_BUCKET, LEAKY_BUCKET

## Practical Note
In production, `rate_limit_counters` typically live in Redis, not a primary relational database. The table here is conceptual to explain the data model.
