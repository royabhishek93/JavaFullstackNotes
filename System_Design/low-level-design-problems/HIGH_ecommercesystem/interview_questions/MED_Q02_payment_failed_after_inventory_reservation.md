# MED Q02 - Payment Failed After Reservation

## Scenario
Stock was reserved, but payment failed after 30 seconds.

## Correct Handling
1. Mark payment FAILED.
2. Cancel order or mark payment_failed.
3. Move reserved_qty back to available_qty.
4. Emit event for UI/cart refresh.

## Interview One-Liner
Reservation must have a rollback path, otherwise payment failures become hidden stock loss.
