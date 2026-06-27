# MED Q02 - SMS Provider Failure and Fallback

## Scenario
Primary SMS provider returns repeated 5xx for OTP traffic.

## Correct Handling
1. Mark delivery attempt failed.
2. Route retry to secondary provider.
3. Preserve same message ID and audit trail.
4. Cap retry budget to avoid spam.

## Interview One-Liner
Provider failover should change the transport, not the business identity of the notification.
