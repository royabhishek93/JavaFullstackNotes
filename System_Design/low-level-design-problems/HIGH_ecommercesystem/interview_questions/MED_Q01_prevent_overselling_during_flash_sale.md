# MED Q01 - Prevent Overselling During Flash Sale

## Scenario
10,000 users try to buy the last 100 units of a product.

## Correct Design
- Inventory row with version or conditional update.
- Reserve inventory first, then create order.
- Reject when `available_qty < requested_qty`.
- Release reservation on payment failure/timeout.

## Interview One-Liner
Oversell prevention belongs in the inventory write path, not in cart validation.
