# MED Q03 - Opt-Out and Quiet Hours

## Scenario
Marketing campaign is queued at 9 PM, but user quiet hours begin at 10 PM and worker sends at 10:05 PM.

## Correct Handling
- Re-check preferences right before delivery for delayed messages.
- Reschedule after quiet window or drop based on campaign policy.
- Keep an audit reason like `SKIPPED_QUIET_HOURS`.

## Interview One-Liner
Preference checks at request time are insufficient for delayed delivery systems.
