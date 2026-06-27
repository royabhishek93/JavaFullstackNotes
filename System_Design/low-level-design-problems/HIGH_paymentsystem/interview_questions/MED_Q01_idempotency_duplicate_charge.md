# MED Q01 - Prevent Duplicate Charge With Idempotency

## Scenario
Client timed out and retried `POST /payment-orders/{id}/confirm` three times with same idempotency key.

## What Should Happen
- First request processes charge.
- Subsequent retries return same response body and status.
- No extra `payment_attempt` is created.

## Design Points
- Unique key: `(merchant_id, idempotency_key)`
- Persist response hash/body for deterministic replay.
- Protect with transaction + row lock for first writer.

## Interview One-Liner
"Idempotency is a business-level exactly-once contract built via unique key + stored response replay."
