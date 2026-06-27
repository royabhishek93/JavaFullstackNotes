# MED Q01 - Prevent Duplicate Notifications

## Scenario
Order service retries the same event 4 times because it did not receive HTTP 200.

## Correct Design
- Require `dedupe_key` from producer.
- UNIQUE `(producer_service, dedupe_key)`.
- Return same `notification_request_id` for retries.
- Do not create duplicate messages.

## Interview One-Liner
Infrastructure can be at-least-once, but business effect must be deduplicated.
