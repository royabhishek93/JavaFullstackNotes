# HIGH Q02 - Dynamic Pricing and Membership

## Scenario
Pricing should vary by occupancy and user tier (regular, monthly pass, VIP).

## Model
- pricing_rules table by lot, slot_type, time_window, occupancy_band
- membership_plan table by user with discounts/caps
- billing engine computes:
  base_fee + surge - membership_discount + taxes

## Guardrails
- Store pricing snapshot on ticket creation.
- Never recalculate historical ticket with new rules.

## Interview One-Liner
Charge must be reproducible: store effective rule version and snapshot on ticket.
