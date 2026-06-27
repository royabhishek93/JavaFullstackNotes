# MED Q02 - Gateway Timeout: Was User Charged?

## Scenario
Gateway call timed out. Client got no response. Gateway might have charged user.

## Correct Handling
1. Mark attempt `UNKNOWN`.
2. Do not immediately mark order failed.
3. Wait for signed webhook.
4. If webhook absent, poll gateway reconcile API with merchant reference.
5. Transition exactly once.

## Anti-Pattern
- Immediately retry charge without reconciliation (can double charge user).

## Interview One-Liner
"Timeout is an unknown outcome, not a failure outcome."
