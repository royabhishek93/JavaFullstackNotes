# Interview Approach - E-commerce System LLD

## 1. Start With Business Risks
"The two biggest correctness risks are overselling inventory and duplicate order placement."

## 2. Define Invariants
- Inventory cannot go negative.
- One idempotency key should produce one order effect.
- Order total must match order item price snapshots.

## 3. Walk Through Happy Path
1. User builds cart.
2. Checkout reserves stock.
3. Order is created.
4. Payment succeeds.
5. Inventory sold quantity increases.
6. Shipment is created.

## 4. Walk Through Failure Path
1. Payment fails after reservation.
2. Reservation is released.
3. Order transitions to FAILED/CANCELLED.

## 5. Discuss Scale Levers
- Search/index for catalog
- Read replicas for product pages
- Reservation queue for flash sales
- Async shipment and notification events

## 6. Trade-offs
- Strong consistency for inventory write path
- Eventual consistency for search, recommendations, analytics

## 7. Close Strongly
"Separate browse path from purchase path: reads optimize for speed, checkout optimizes for correctness."
