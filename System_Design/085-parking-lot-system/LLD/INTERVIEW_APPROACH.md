# Interview Approach - Parking Lot LLD

## 1. Clarify Constraints
- Single city or multi-city lots?
- Hourly billing or slab billing?
- Reserved slots and EV slots?

## 2. Define Invariants
- One active vehicle per slot.
- One active ticket per vehicle per lot.
- Slot status and ticket status must stay consistent.

## 3. Walk Through Entry Flow
1. Validate vehicle type.
2. Find candidate slot list by index.
3. Atomic slot claim.
4. Create ACTIVE ticket.

## 4. Walk Through Exit Flow
1. Fetch active ticket.
2. Compute duration and fee.
3. Capture payment.
4. Close ticket and release slot.

## 5. Discuss Failure Cases
- Payment timeout at exit
- Barrier open but DB write fails
- Duplicate exit request

## 6. Scale Discussion
- Partition by lot and floor.
- Cache availability counters.
- Event bus for occupancy updates to UI.

## 7. Close with Extensibility
- Membership plans
- EV charging sessions
- Pre-booking slots with hold expiry
