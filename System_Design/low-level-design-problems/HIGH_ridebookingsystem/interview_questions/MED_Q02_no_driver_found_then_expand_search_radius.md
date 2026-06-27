# MED Q02 - No Driver Found, Then Expand Radius

## Scenario
No available driver is found within 2 km for 20 seconds.

## Correct Handling
1. Increase search radius to 5 km.
2. Recompute candidate pool.
3. Raise estimated wait time and surge if needed.
4. Cancel gracefully after max attempts.

## Interview One-Liner
Matching should degrade progressively, not fail immediately.
