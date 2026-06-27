# MED Q01 - Two Drivers Accept Same Ride

## Scenario
Two drivers receive the same offer and both tap Accept nearly simultaneously.

## Correct Design
- Use atomic update on assignment row or ride_request row.
- First accepted transition wins.
- Loser receives `ASSIGNMENT_ALREADY_TAKEN`.
- Driver state changes to BUSY only for winner.

## Interview One-Liner
Offer fan-out is fine; accept path must converge through one atomic winner gate.
