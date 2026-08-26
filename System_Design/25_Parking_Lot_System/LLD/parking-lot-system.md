# Designing a Parking Lot System (LLD)

## Requirements
1. Support multiple parking lots, floors, and slots.
2. Support vehicle types: BIKE, CAR, TRUCK, ELECTRIC.
3. Allocate nearest available valid slot on entry.
4. Generate a parking ticket with entry time.
5. Calculate fee on exit using pricing rules.
6. Support payment and invoice generation.
7. Prevent double assignment of same slot.
8. Handle high concurrency during peak hours.

## Core Entities
1. ParkingLot
- id, name, address
- floors

2. ParkingFloor
- id, lotId, floorNumber
- slots

3. ParkingSlot
- id, floorId, slotNumber, slotType, status
- reservedFor (optional)

4. Vehicle
- plateNumber, type, ownerId

5. ParkingTicket
- id, lotId, slotId, vehiclePlate, entryTime, status

6. Payment
- id, ticketId, amount, method, status, paidAt

## APIs
- POST /v1/entry
- POST /v1/exit
- GET /v1/tickets/{ticketId}
- GET /v1/availability?lotId=...&vehicleType=...
- POST /v1/tickets/{ticketId}/pay

## Allocation Strategy
- Keep free-slot index by lot + floor + slotType.
- On entry, try preferred floor order (nearest first).
- Atomically mark slot OCCUPIED using conditional update.

## Pricing Strategies
1. Hourly pricing
2. Flat first hour + progressive slabs
3. Surge multiplier by occupancy
4. EV charging surcharge

## State Transitions
- Slot: AVAILABLE -> OCCUPIED -> AVAILABLE
- Ticket: ACTIVE -> CLOSED
- Payment: PENDING -> SUCCESS or FAILED

## Concurrency Model
- Use row-level lock or optimistic update on slot row.
- Unique active ticket per slot constraint.
- Idempotency key for exit and pay APIs.

## Scenario: Two Cars Enter at Same Time
1. Both request nearest car slot on floor 1.
2. First transaction sets slot OCCUPIED.
3. Second transaction fails conditional update and retries next slot.
4. Both get distinct tickets and slots.

## Interview Talking Point
The critical correctness rule is exactly one active ticket per slot and exactly one occupied slot per active ticket.
