# Designing a Ride Booking System (LLD)

## Requirements
1. Riders should request rides with pickup and drop locations.
2. System should find nearby available drivers.
3. Exactly one driver should be assigned to one ride.
4. Support ride status transitions from request to completion.
5. Support fare estimation, surge pricing, and final billing.
6. Handle driver cancellation, rider cancellation, and timeout.
7. Support payment and invoice generation.
8. Scale for large city-level concurrent demand.

## Core Components
1. Rider Service
- Manages rider profile and ride requests.

2. Driver Service
- Tracks driver profile, vehicle, and availability.

3. Location Service
- Stores live driver coordinates and nearby search index.

4. Matching Engine
- Finds best driver candidates and sends offers.

5. Ride Orchestrator
- Owns ride lifecycle and assignment state machine.

6. Pricing Service
- Calculates estimated fare, surge, tolls, and final fare.

7. Payment Service
- Handles payment capture and reconciliation.

## Core Entities
1. Rider
- id, name, phone, rating

2. Driver
- id, name, phone, status, rating

3. Vehicle
- id, driverId, vehicleType, plateNumber

4. RideRequest
- id, riderId, pickupLat, pickupLng, dropLat, dropLng, status, idempotencyKey

5. RideAssignment
- id, rideRequestId, driverId, offeredAt, acceptedAt, status

6. Trip
- id, rideRequestId, startTime, endTime, distanceKm, finalFare, status

7. Payment
- id, tripId, amount, method, status, transactionRef

## APIs
- POST /v1/rides/request
- POST /v1/rides/{id}/cancel
- POST /v1/rides/{id}/accept
- POST /v1/rides/{id}/start
- POST /v1/rides/{id}/complete
- GET /v1/rides/{id}
- POST /v1/payments/webhook

## Ride Flow
1. Rider creates ride request.
2. Matching engine fetches nearby available drivers.
3. Offer is sent to top candidate(s) with timeout.
4. First accepted driver wins atomically.
5. Trip starts and then completes.
6. Payment is charged and receipt generated.

## State Transitions
- Driver: OFFLINE -> AVAILABLE -> BUSY -> AVAILABLE
- RideRequest: CREATED -> SEARCHING -> DRIVER_ASSIGNED -> IN_PROGRESS -> COMPLETED or CANCELLED
- RideAssignment: OFFERED -> ACCEPTED or REJECTED or EXPIRED
- Payment: PENDING -> SUCCESS or FAILED

## Concurrency Strategy
- Unique active assignment per ride.
- Unique active ride per driver.
- Conditional update on driver status AVAILABLE -> BUSY.
- Idempotency key on ride request creation.

## Failure Scenarios
1. Two drivers accept same ride at same time
- One assignment wins by atomic transition, other gets rejection.

2. Driver accepts but app disconnects
- Keep acceptance in DB; retry notify rider.

3. Payment timeout after trip complete
- Trip closes, payment marked UNKNOWN/PENDING_RECONCILE.

## Interview One-Liner
Matching is a race, so the core of ride booking design is controlled contention on driver assignment.
