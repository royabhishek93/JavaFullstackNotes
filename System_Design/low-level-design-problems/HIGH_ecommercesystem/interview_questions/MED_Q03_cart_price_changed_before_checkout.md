# MED Q03 - Cart Price Changed Before Checkout

## Scenario
User added product to cart at 999, but price became 1099 before checkout.

## Correct Handling
- Store `unit_price_snapshot` in cart for UX.
- Re-validate actual payable price at checkout.
- Store final paid snapshot in order_items.
- Inform user if payable amount changed.

## Interview One-Liner
Cart price is informational; order item price snapshot is financial truth.
