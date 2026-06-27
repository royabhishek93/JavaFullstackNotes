# MED Q02 - Redis Down: Fail Open or Fail Closed?

## Scenario
Counter store is unavailable for 2 minutes.

## Answer
- Auth, payment, OTP, abuse-prone APIs: usually fail-closed or degrade strictly.
- Product catalog, low-risk reads: usually fail-open.
- Decision should be policy-driven, not hardcoded globally.

## Interview One-Liner
Failure semantics are endpoint-specific business decisions, not purely technical ones.
