# MED Q01 - Prevent Double Slot Allocation

## Scenario
Two cars request entry simultaneously, both targeting nearest available slot C-101.

## Correct Design
- Conditional update:
  UPDATE parking_slots
  SET status='OCCUPIED'
  WHERE id=:slotId AND status='AVAILABLE';
- If updated rows = 0, slot already claimed. Retry next slot.

## Why It Works
Atomic compare-and-set guarantees only one winner for a slot.

## Interview One-Liner
Slot assignment must be an atomic state transition, not read-then-write in separate steps.
