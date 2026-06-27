# Interview Approach - Ride Booking System LLD

## 1. Start With Core Risks
"The biggest correctness issues are double driver assignment, stale driver location, and payment reconciliation after trip completion."

## 2. Define Invariants
- One active ride per driver.
- One accepted driver per ride request.
- Trip completion and payment capture must be consistently linked.

## 3. Walk Through Happy Path
1. Rider requests ride.
2. Matching engine finds nearby drivers.
3. Driver accepts.
4. Ride starts.
5. Ride completes.
6. Payment succeeds.

## 4. Walk Through Failure Path
1. No driver accepts within timeout.
2. Retry broader search radius.
3. Driver cancels after accept.
4. Re-match or cancel gracefully.

## 5. Discuss Scale Levers
- Geo indexing by city and grid cell
- Event-driven driver location updates
- Separate matching path from trip history path
- Cached driver availability with DB confirmation

## 6. Trade-offs
- Matching is latency-optimized.
- Assignment confirmation is correctness-optimized.

## 7. Close Strongly
"The architecture works when location search is fast, but assignment confirmation is strongly guarded."
