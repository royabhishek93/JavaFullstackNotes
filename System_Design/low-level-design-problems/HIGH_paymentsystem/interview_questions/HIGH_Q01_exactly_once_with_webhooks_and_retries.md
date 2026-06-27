# HIGH Q01 - Exactly Once With Retries + Webhooks + Concurrent Workers

## Scenario
- User retries payment request
- Webhook arrives twice
- Reconciliation worker also runs in parallel

How do you ensure one final state and one financial effect?

## Solution Sketch
1. Idempotent order key at API layer.
2. State transition guard with `version` (optimistic lock) or `FOR UPDATE`.
3. Webhook dedupe by unique `gateway_event_id`.
4. Ledger write in same transaction as terminal state transition.
5. All processors call one shared transition function.

## Invariant
For each `payment_order_id`, terminal state transition occurs once and ledger group is posted once.

## Interview One-Liner
"Multiple delivery paths are fine if they converge through one idempotent transition gate."
