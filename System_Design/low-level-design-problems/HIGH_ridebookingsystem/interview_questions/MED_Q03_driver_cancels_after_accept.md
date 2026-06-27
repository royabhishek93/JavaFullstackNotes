# MED Q03 - Driver Cancels After Accept

## Scenario
Driver accepted, rider saw confirmation, but driver cancels 15 seconds later.

## Correct Handling
- Change assignment/trip state consistently.
- Re-run matching with higher priority.
- Apply cancellation penalty if policy requires.
- Notify rider with updated ETA.

## Interview One-Liner
Post-accept cancellation is a rematch problem, not just a status update problem.
