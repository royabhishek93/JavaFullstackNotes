# MED Q02 - Payment Timeout on Exit Gate

## Scenario
Driver reaches exit. Fee calculated. Payment gateway times out.

## Handling
1. Mark payment attempt as PENDING/UNKNOWN.
2. Keep ticket ACTIVE for grace window.
3. Reconcile via webhook/poll.
4. If payment succeeds, close ticket and open gate.
5. If failed after grace window, route to manual assistance.

## Anti-Pattern
Immediately charging again without idempotency key.

## Interview One-Liner
Timeout means unknown outcome, not failure. Reconcile first, retry second.
