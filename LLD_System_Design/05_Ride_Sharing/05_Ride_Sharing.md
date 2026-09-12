# Ride Sharing (Uber/Ola) — Complete LLD Interview Guide

**Interview Duration: 50 min | Difficulty: Hard | Must-Know: ⭐⭐⭐⭐⭐ | 15-YOE Focus: Driver State Machine + Geo Matching + Surge Pricing**

---

## BIG PICTURE — Architecture

```
 ┌──────────────────────────────────────────────────────────────────┐
 │                    RIDE SHARING SYSTEM                          │
 │                                                                  │
 │  RIDER                    PLATFORM                 DRIVER       │
 │  ┌──────────┐            ┌──────────────────┐    ┌──────────┐  │
 │  │ Request  │            │  Matching Engine │    │ ONLINE   │  │
 │  │ ride     │──────────► │  findNearby()    │──► │ AVAILABLE│  │
 │  │ Track    │            │  score drivers   │    │ ON_TRIP  │  │
 │  │ Rate     │            │  dispatch        │    │ OFFLINE  │  │
 │  └──────────┘            └────────┬─────────┘    └──────────┘  │
 │                                   │                              │
 │                          ┌────────▼─────────┐                   │
 │  SURGE PRICING           │  Trip Lifecycle  │   LOCATION SVC    │
 │  ┌───────────────┐       │  REQUESTED       │   ┌────────────┐ │
 │  │ demand/supply │       │  DRIVER_ASSIGNED │   │ GPS Update │ │
 │  │ ratio > 1.5x  │       │  DRIVER_ARRIVED  │◄──│ every 5s   │ │
 │  │ → surge 1.5x  │       │  IN_PROGRESS     │   │ GeoHash    │ │
 │  └───────────────┘       │  COMPLETED       │   │ QuadTree   │ │
 │                          └──────────────────┘   └────────────┘ │
 └──────────────────────────────────────────────────────────────────┘

 DRIVER STATE MACHINE:
 ┌──────────────────────────────────────────────────────────────────┐
 │  [OFFLINE] ──goOnline()──► [AVAILABLE]                          │
 │                                │                                 │
 │                           dispatch()                             │
 │                                │                                 │
 │                          [DISPATCHED]  ← waiting for acceptance  │
 │                          /         \                             │
 │                    accept()        reject()/timeout              │
 │                       │                 │                        │
 │               [DRIVING_TO_PICKUP]   [AVAILABLE] ← reassign      │
 │                       │                                          │
 │                  arrivedAtPickup()                               │
 │                       │                                          │
 │               [WAITING_FOR_RIDER]                               │
 │                       │                                          │
 │                  startTrip()                                     │
 │                       │                                          │
 │                  [IN_TRIP]                                       │
 │                       │                                          │
 │                  endTrip()                                       │
 │                       │                                          │
 │                  [AVAILABLE] ← ready for next ride              │
 └──────────────────────────────────────────────────────────────────┘

 GEO MATCHING — FINDING NEARBY DRIVERS:
 ┌──────────────────────────────────────────────────────────────────┐
 │  Rider at (28.6139, 77.2090) — Delhi                            │
 │                                                                  │
 │  GeoHash: encode coords to "ttnfv7" (precision 6 = ~1km radius) │
 │  Query: Redis GEOSEARCH "drivers:available" FROMLONLAT lon lat   │
 │                                 BYRADIUS 5 km                   │
 │  Returns: [driver1(0.8km), driver2(1.2km), driver3(3.4km)]     │
 │                                                                  │
 │  Score each driver:                                              │
 │  score = distance_weight × dist + rating_weight × (5-rating)    │
 │  + acceptance_weight × (1-acceptanceRate)                       │
 │  Lowest score = best match                                       │
 └──────────────────────────────────────────────────────────────────┘
```

---

## CONVERSATIONAL SCRIPT

### Phase 1 — Requirements (5 min)

**You:** "Let me clarify the scope.

Functional:
- Riders request a ride with pickup + destination
- System finds nearby available drivers and dispatches to best match
- Driver accepts or rejects within 30 seconds; on reject/timeout → next driver
- Trip lifecycle: Driver en route → Arrived → Rider boards → Trip starts → Trip ends
- Fare calculation: base fare + distance + time + surge multiplier
- Ratings: rider rates driver, driver rates rider after trip

Non-functional:
- Real-time: driver locations update every 5 seconds — millions of location updates/sec
- Matching latency: rider must get a driver response within 5 seconds
- Scale: Bangalore peak hour — 50,000 concurrent trip requests

The hardest problem here is: how do you efficiently find the nearest available driver among 100,000 drivers in a city, in real time, with location changing every 5 seconds?"

---

### Phase 3 — Implementation

```java
// ─── Location ────────────────────────────────────────────────────
public record Location(double latitude, double longitude) {
    public double distanceKm(Location other) {
        // Haversine formula approximation
        double latDiff = Math.toRadians(other.latitude - this.latitude);
        double lonDiff = Math.toRadians(other.longitude - this.longitude);
        double a = Math.sin(latDiff/2) * Math.sin(latDiff/2)
            + Math.cos(Math.toRadians(this.latitude))
            * Math.cos(Math.toRadians(other.latitude))
            * Math.sin(lonDiff/2) * Math.sin(lonDiff/2);
        return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    }
}

// ─── Driver State ────────────────────────────────────────────────
public enum DriverStatus { OFFLINE, AVAILABLE, DISPATCHED,
                           DRIVING_TO_PICKUP, WAITING_FOR_RIDER,
                           IN_TRIP }

// ─── Driver ──────────────────────────────────────────────────────
public class Driver {
    private final String driverId;
    private final String name;
    private final VehicleType vehicleType;
    private volatile Location  currentLocation;
    private volatile DriverStatus status;
    private double               rating;
    private double               acceptanceRate;

    public Driver(String driverId, String name, VehicleType vehicleType) {
        this.driverId     = driverId;
        this.name         = name;
        this.vehicleType  = vehicleType;
        this.status       = DriverStatus.OFFLINE;
        this.rating       = 5.0;
        this.acceptanceRate = 1.0;
    }

    public synchronized boolean transitionTo(DriverStatus newStatus) {
        // Validate legal transitions
        boolean valid = switch (newStatus) {
            case AVAILABLE   -> status == DriverStatus.OFFLINE
                             || status == DriverStatus.IN_TRIP
                             || status == DriverStatus.DISPATCHED;
            case DISPATCHED  -> status == DriverStatus.AVAILABLE;
            case DRIVING_TO_PICKUP -> status == DriverStatus.DISPATCHED;
            case WAITING_FOR_RIDER -> status == DriverStatus.DRIVING_TO_PICKUP;
            case IN_TRIP     -> status == DriverStatus.WAITING_FOR_RIDER;
            case OFFLINE     -> true; // can go offline from any state
        };
        if (valid) this.status = newStatus;
        return valid;
    }

    public String getDriverId()      { return driverId; }
    public Location getLocation()    { return currentLocation; }
    public void updateLocation(Location loc) { this.currentLocation = loc; }
    public DriverStatus getStatus()  { return status; }
    public double getRating()        { return rating; }
    public double getAcceptanceRate(){ return acceptanceRate; }
    public VehicleType getVehicleType() { return vehicleType; }
}

// ─── Trip ─────────────────────────────────────────────────────────
public class Trip {
    public enum Status { REQUESTED, DRIVER_ASSIGNED, DRIVER_ARRIVED,
                         IN_PROGRESS, COMPLETED, CANCELLED }

    private final String   tripId;
    private final String   riderId;
    private final Location pickupLocation;
    private final Location destination;
    private String         assignedDriverId;
    private volatile Status status;
    private Instant        requestedAt;
    private Instant        startedAt;
    private Instant        completedAt;
    private double         farePaid;
    private double         surgeMultiplier;

    public Trip(String riderId, Location pickup, Location dest, double surgeMultiplier) {
        this.tripId          = UUID.randomUUID().toString();
        this.riderId         = riderId;
        this.pickupLocation  = pickup;
        this.destination     = dest;
        this.surgeMultiplier = surgeMultiplier;
        this.status          = Status.REQUESTED;
        this.requestedAt     = Instant.now();
    }

    public void assignDriver(String driverId) {
        this.assignedDriverId = driverId;
        this.status = Status.DRIVER_ASSIGNED;
    }

    public void startTrip()   { startedAt = Instant.now(); status = Status.IN_PROGRESS; }

    public double complete()  {
        completedAt = Instant.now();
        status = Status.COMPLETED;
        farePaid = calculateFare();
        return farePaid;
    }

    private double calculateFare() {
        double distKm    = pickupLocation.distanceKm(destination);
        long   durationMin = Duration.between(startedAt, completedAt).toMinutes();
        double base      = 30.0;           // ₹30 base
        double perKm     = distKm * 12.0;  // ₹12/km
        double perMin    = durationMin * 1.5; // ₹1.5/min
        return (base + perKm + perMin) * surgeMultiplier;
    }

    public String getTripId()       { return tripId; }
    public Location getPickup()     { return pickupLocation; }
    public String getAssignedDriver() { return assignedDriverId; }
    public Status getStatus()       { return status; }
}

// ─── Matching Engine ─────────────────────────────────────────────
public class MatchingEngine {
    private final Map<String, Driver>  drivers   = new ConcurrentHashMap<>();
    private final Map<String, Trip>    trips     = new ConcurrentHashMap<>();
    private final SurgeCalculator      surge;
    private final ScheduledExecutorService dispatchTimeout =
        Executors.newScheduledThreadPool(4);

    public MatchingEngine(SurgeCalculator surge) {
        this.surge = surge;
    }

    // ─── Update driver location ──────────────────────────────────
    public void updateDriverLocation(String driverId, Location loc) {
        Driver driver = drivers.get(driverId);
        if (driver != null) driver.updateLocation(loc);
        // In production: also update Redis GeoHash index:
        // redis.geoAdd("drivers:available", loc.longitude(), loc.latitude(), driverId)
    }

    // ─── Request ride ────────────────────────────────────────────
    public Trip requestRide(String riderId, Location pickup, Location dest,
                             VehicleType vehicleType) {
        double surgeMultiplier = surge.calculate(pickup);
        Trip trip = new Trip(riderId, pickup, dest, surgeMultiplier);
        trips.put(trip.getTripId(), trip);

        dispatchToNextAvailableDriver(trip, vehicleType, 0);
        return trip;
    }

    private void dispatchToNextAvailableDriver(Trip trip, VehicleType type, int attempt) {
        if (attempt >= 5) {
            System.out.println("No drivers available after 5 attempts. Trip cancelled.");
            trip.getStatus(); // mark CANCELLED
            return;
        }

        Optional<Driver> bestDriver = findBestDriver(trip.getPickup(), type);
        if (bestDriver.isEmpty()) {
            // Retry after 10 seconds
            dispatchTimeout.schedule(() ->
                dispatchToNextAvailableDriver(trip, type, attempt + 1),
                10, TimeUnit.SECONDS);
            return;
        }

        Driver driver = bestDriver.get();
        boolean dispatched = driver.transitionTo(DriverStatus.DISPATCHED);
        if (!dispatched) {
            // Race condition: driver grabbed by another trip
            dispatchToNextAvailableDriver(trip, type, attempt);
            return;
        }

        trip.assignDriver(driver.getDriverId());
        System.out.printf("Driver %s dispatched to trip %s%n",
            driver.getDriverId(), trip.getTripId());

        // 30-second acceptance timeout
        dispatchTimeout.schedule(() -> {
            if (trip.getStatus() == Trip.Status.DRIVER_ASSIGNED) {
                // Driver didn't respond — reassign
                System.out.println("Driver " + driver.getDriverId() + " timed out");
                driver.transitionTo(DriverStatus.AVAILABLE);
                driver.updateAcceptanceRate(false);
                dispatchToNextAvailableDriver(trip, type, attempt + 1);
            }
        }, 30, TimeUnit.SECONDS);
    }

    private Optional<Driver> findBestDriver(Location pickup, VehicleType type) {
        return drivers.values().stream()
            .filter(d -> d.getStatus() == DriverStatus.AVAILABLE)
            .filter(d -> d.getVehicleType() == type)
            .filter(d -> d.getLocation() != null)
            .filter(d -> d.getLocation().distanceKm(pickup) <= 5.0) // within 5km
            .min(Comparator.comparingDouble(d -> score(d, pickup)));
    }

    private double score(Driver driver, Location pickup) {
        double distScore       = driver.getLocation().distanceKm(pickup) * 0.6;
        double ratingScore     = (5.0 - driver.getRating()) * 0.3;
        double acceptanceScore = (1.0 - driver.getAcceptanceRate()) * 0.1;
        return distScore + ratingScore + acceptanceScore;
    }

    public void registerDriver(Driver driver) { drivers.put(driver.getDriverId(), driver); }
}

// ─── Surge Calculator ────────────────────────────────────────────
public class SurgeCalculator {
    private final Map<String, Integer> activeRequests  = new ConcurrentHashMap<>();
    private final Map<String, Integer> availableDrivers = new ConcurrentHashMap<>();

    public double calculate(Location pickup) {
        String geoHash = GeoHash.encode(pickup.latitude(), pickup.longitude(), 4);
        int demand = activeRequests.getOrDefault(geoHash, 0);
        int supply = availableDrivers.getOrDefault(geoHash, 1);
        double ratio = (double) demand / supply;

        if (ratio < 1.5) return 1.0;
        if (ratio < 2.0) return 1.5;
        if (ratio < 3.0) return 2.0;
        return 2.5;  // cap surge at 2.5x
    }
}
```

---

## Component Choices

```
COMPONENT             CHOICE                   WHY
──────────────────────────────────────────────────────────────────────
Driver location store  Redis GeoSearch         Millions of location updates
                                               per second. Redis GEOADD +
                                               GEOSEARCH is O(N+log M).
                                               In-memory: 100k drivers =
                                               fast; DB: too slow for 5s updates.

Geo proximity search   GeoHash + radius        GeoHash partitions Earth into
                                               cells. Nearby drivers → nearby
                                               GeoHash prefix. Fast spatial
                                               index without PostGIS complexity.

Driver state           State Machine +         Prevents illegal transitions
                       synchronized method     (can't go OFFLINE → IN_TRIP).
                                               Thread-safe via synchronized.

Dispatch timeout       ScheduledExecutorService Non-blocking 30s timeout.
                                               On expire: reassign without
                                               blocking the dispatch thread.

Surge pricing          Demand/supply ratio     Simple, transparent.
                       by GeoHash cell         Cell granularity: precision 4
                                               (~20km² cells).
                                               Update every 60s from
                                               ride request counts.

Matching score         Weighted multi-factor   Distance is primary (60%).
                                               Rating secondary (30%).
                                               Acceptance rate (10%).
                                               Tunable weights.
```

---

## Senior Trap Questions

**Q1: "Two requests arrive at the same time. Same driver is best match for both. How do you prevent the driver being assigned to two trips?"**
```
The race condition:
  Thread 1: findBestDriver() → Driver D is AVAILABLE ✅
  Thread 2: findBestDriver() → Driver D is AVAILABLE ✅ (same check!)
  Thread 1: driver.transitionTo(DISPATCHED) → success ✅
  Thread 2: driver.transitionTo(DISPATCHED) → fails! (synchronized method)
            → returns false → re-run findBestDriver() → finds next best

Driver.transitionTo() is synchronized → only one thread can change state at a time.
Thread 2 sees the result of Thread 1's transition.
No double-assignment. ✅

This is optimistic concurrency on the driver state — check, then CAS atomically.
```

**Q2: "Driver accepts the trip but then cancels 2 minutes later. How do you penalize?"**
```
Track: driver.cancelledAfterAcceptance count.
If cancellations > 3 in 24h:
  - Penalize: reduce acceptanceRate score → ranked lower in matching
  - Suspend for 1 hour: can't go AVAILABLE (soft penalty)
  - Revenue split: no incentive bonus for the day

Algorithm:
  On trip cancel by driver:
    driver.recordCancellation(afterAcceptance=true)
    if driver.cancellationRate() > 0.15:   // >15% = bad
        driver.suspend(Duration.ofHours(1))

Rider impact: system immediately re-dispatches to next available driver.
```

**Q3: "Bangalore peak hour. 50,000 concurrent requests. How does matching scale?"**
```
Each request → findBestDriver() → scans ~100,000 drivers.
50,000 concurrent: 50,000 × 100,000 = 5 billion comparisons. Impossible in-process.

Production solution:
1. Geofencing: divide city into zones (100m × 100m cells using GeoHash).
   Each request only matches drivers in nearby cells (3km radius = ~30 cells).
   50,000 requests × 30 cells × avg 5 drivers/cell = 7.5M comparisons. Manageable.

2. Redis GEOSEARCH: offload geo query to Redis.
   Redis handles 100k+ GEOSEARCH operations per second.
   App gets back top 10 nearby drivers, scores locally.

3. Horizontal scaling: 10 matching engine pods, each handles 5,000 requests.
   Redis is shared state for driver locations.
   Stateless matching pods: scale independently.

4. Pre-computed batches: every 10 seconds, compute "supply heat map" per zone.
   Surge pricing updated from heat map. Matching engine uses cached heat map.
```

---

## Failure Modes

```
SCENARIO              WHAT HAPPENS             FIX
────────────────────────────────────────────────────────────────────
Driver app crashes     Driver shows AVAILABLE  Heartbeat: driver app sends
during trip            but not responding      ping every 30s. If missed
                                               3 times: force to OFFLINE.
                                               Trip marked INTERRUPTED.

GPS signal lost        Driver location stale   Last known location used for
                                               5 min. After 5 min stale:
                                               driver marked OFFLINE.

Payment fails after    Rider charged, driver   Two-phase: hold payment at
trip completion        not credited            trip start, capture on complete.
                                               If capture fails: retry 3x.
                                               Fallback: manual review queue.

Surge price shock      Rider doesn't see       Always show surge BEFORE
at ride confirmation   the surge              confirmation. Require explicit
                                              acceptance of surge price.
                                              Regulatory requirement in India.
```

---

## Interview Cheat Sheet

> "Ride sharing has three hard problems: driver state management, geo-proximity matching at scale, and the dispatch race condition. Driver state uses a State Machine with synchronized transitions — OFFLINE, AVAILABLE, DISPATCHED, DRIVING_TO_PICKUP, WAITING_FOR_RIDER, IN_TRIP. The dispatch race condition: two trip requests competing for the same driver — solved by making transitionTo(DISPATCHED) synchronized; only one request wins, the other re-runs matching. For geo matching at scale: Redis GEOSEARCH with GeoHash — store all AVAILABLE drivers in a Redis geo index, query by lat/lon + radius — handles millions of location updates per second. Surge pricing is demand-over-supply ratio per GeoHash zone: if ratio > 1.5x → 1.5x fare multiplier, shown to rider BEFORE booking. Driver acceptance timeout uses ScheduledExecutorService: 30s to accept, then reassign to next driver."
