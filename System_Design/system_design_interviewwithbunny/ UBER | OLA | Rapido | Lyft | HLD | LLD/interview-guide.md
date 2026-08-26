# Ride-Sharing System Design — Interview Guide
## Uber | Ola | Rapido | Lyft

> One-liner to open: *"Rider requests → Geo-search nearby drivers → Zookeeper lock (prevent double assignment) → Driver accepts → WebSocket location tracking → Trip completion → Payment & Rating"*

---

## 1. Functional Requirements

| # | Feature |
|---|---------|
| 1 | Riders get fare estimate (pickup → drop, per vehicle type) |
| 2 | Riders request ride based on estimate |
| 3 | Riders choose vehicle category: Sedan, SUV, Bike, Auto |
| 4 | See nearby available drivers on map in real-time |
| 5 | Matched with closest available driver (geo-proximity) |
| 6 | Real-time location tracking during trip |
| 7 | Rate & pay after trip ends |
| 8 | Drivers accept/decline requests, update status (available/busy/offline) |

---

## 2. Non-Functional Requirements

| Concern | Requirement |
|---------|------------|
| Scale | Millions of users & drivers globally; 100K concurrent rides at peak |
| CAP Theorem | Availability >> Consistency (user side) BUT Consistency >> Availability (driver assignment — prevent double booking) |
| Matching Latency | < 1 second for driver assignment |
| Location Updates | Every 3–5 seconds via WebSocket |
| Geospatial Query | ~10ms to find 10 nearest drivers from 1M drivers |

---

## 3. Core Entities

```
Rider      → rider_id, name, email, phone, payment_methods, avg_rating
Driver     → driver_id, vehicle_type/model/plate, status(AVAILABLE/BUSY/OFFLINE), avg_rating, acceptance_rate
Location   → lat, lon, timestamp (ephemeral in Redis, persisted via Kafka)
Fare       → base_fare, distance_fare, time_fare, surge_multiplier, total
Ride/Trip  → trip_id, rider_id, driver_id, pickup, drop, status, estimated_fare, actual_fare, start/end_time
Rating     → rating_id, trip_id, driver_rating(1-5), rider_rating(1-5) [ANONYMOUS]
Payment    → payment_id, trip_id, amount, method, stripe_payment_id, status
```

---

## 4. API Design (from diagram)

### Rider APIs
```
POST /v1/api/fare/estimate         → {pickup, drop, vehicle_type} → fare breakdown + request_id
POST /v1/api/ride/request          → {request_id, pickup, drop, vehicle_type} → rideId + driver details
GET  /v1/api/ride/history          → paginated ride history
POST /v1/api/ride/{rideId}/cancel  → cancel request
POST /v1/api/ride/{rideId}/rate    → {driver_rating, feedback}
```

### Driver APIs
```
WS   /v1/driver/location           → {lat, lon} every 3-5s — updates geolocation continuously
POST /v1/api/ride/rides            → {requestId, accept/deny} → rideId
POST /v1/api/ride/{ride_id}/start  → mark trip started
POST /v1/api/ride/{ride_id}/end    → mark trip completed
```

---

## 5. High Level Design (from diagram)

```
users/client ──► LB + API Gateway ──► Ride Svc (fare calculation) ──► Location Map Svc (GMap/Apple Map)
     │                │
     │                ├──► Driver Matching Svc ──► Drivers DB (PostgreSQL)
     │                ├──► Rating Svc           ──► Rating DB
     │                ├──► Payment Svc          ──► Payment DB
     │                ├──► Location Update Svc  ──► Redis (geospatial + TTL)
     │                └──► Notification Svc     ──► FCM (Android) + APN (iOS)
     │
drivers ──────► WebSocket Gateway ──► Location Update Svc (websocket server)
                                              │
                                           Kafka ──► Trip Update Consumer
                                              │
                                        Zookeeper (driver locks — ephemeral nodes)
```

**LB + API Gateway responsibilities:** Authentication, Authorization, Rate Limiting, Routing, Round-Robin traffic distribution

---

## 6. Low Level Design — Step-by-Step Flow

### Step 1: Fare Estimation

```
Rider enters pickup + drop
    ↓
POST /v1/api/fare/estimate
    ↓
Ride Svc → Location Map Svc (Google Distance Matrix)
    Response: {distance: 5.2km, duration: 12min}
    ↓
Calculate base fare:
    base_rate:     $2.50 (flat)
    distance_rate: 5.2km × $1.50/km  = $7.80
    time_rate:     12min × $0.30/min  = $3.60
    subtotal:                          $13.90
    ↓
Apply Surge (from Surge Calculator Svc):
    GET surge_multiplier:{area_geohash} from Redis
    If demand/supply > threshold → surge = 1.5×
    final = $13.90 × 1.5 = $20.85
    ↓
Cache: SET fare_estimate:{request_id} EX 300 (5 min TTL)
    ↓
Response: {estimated_fare, breakdown, vehicle_options: [sedan, suv, bike], eta_min}
```

**India pricing (from diagram):** Bike = Rs 20/km + Rs 1/min waiting; Car = Rs 60/km

---

### Step 2: Ride Request & Driver Matching

```
Rider clicks "Request Sedan"
    ↓
POST /v1/api/ride/request
    ↓
Ride Svc validates:
    - GET fare_estimate:{request_id} from Redis (still valid?)
    - Validate payment method via Payment Svc
    ↓
INSERT ride_requests (status: PENDING)
SET ride_request:{request_id} EX 600 (10 min TTL — expires if no driver found)
    ↓
Publish Kafka: ride.requested topic
    ↓
Driver Matching Svc consumes:
    GEORADIUS drivers:available {pickup_lon} {pickup_lat} 5km WITHDIST ASC
    Filter by vehicle type: SISMEMBER drivers:sedan {driver_id}
    Result: [(D1, 0.8km), (D2, 1.2km), (D3, 2.5km)]
    ↓
Iterate closest-first → attempt Zookeeper lock (Step 3)
```

---

### Step 3: Zookeeper Driver Locking — CRITICAL

> **Purpose:** Prevent double assignment — ensure one driver assigned to ONE ride at a time

```
From diagram: /locks/drivers/{driver_id}/ephemeral_node
```

**Lock Flow:**
```
DMS tries: CREATE /locks/drivers/D1/request_R1_seq0001  (ephemeral + sequential)
    ↓
GET_CHILDREN /locks/drivers/D1 → sorted by sequence
    If our node has LOWEST sequence → LOCK ACQUIRED ✓
    If lower sequence exists → LOCK FAILED → try next driver
    ↓
On LOCK ACQUIRED:
    SET driver:{D1}:status 'BUSY' EX 900       (Redis)
    GEOREM drivers:available D1                (remove from pool)
    UPDATE drivers SET status='BUSY'           (DB)
    Publish Kafka → Notification Svc → FCM/APN → driver device
    Driver has 30 seconds to accept/decline
```

**Quotes from diagram:**
> *"when the driver matching service wants to create a lock it creates an ephemeral node. If it is successful, means it got the lock. Incase it got the NodeExistsException, the driver is already assigned to someone or try after sometime"*

> *"once lock is released, server has to delete the ephemeral node manually, OR zookeeper will automatically delete it if the server gets session timeout/disconnected/dies"*

**Ephemeral nodes (from diagram):** `driverId: 001`, `driverId: 002`, `driverId: 003`
- Auto-deleted on: session timeout (30s), service crash, disconnect

---

### Step 4: Driver Accept / Decline

```
Driver accepts → POST /v1/api/ride/rides {requestId, action: 'accept'}
    ↓
Ride Svc validates Zookeeper lock still held
    ↓
BEGIN TRANSACTION:
    INSERT INTO trips (status: MATCHED)
    UPDATE ride_requests SET status='MATCHED'
    UPDATE drivers SET current_trip_id
COMMIT
    ↓
DELETE /locks/drivers/{driver_id}/{request_id}  (lock no longer needed)
    ↓
Notify rider via Kafka → Notification Svc:
    Push: "Driver {name} accepted! ETA 5 min"
    WebSocket: {type: 'ride_matched', driver: {name, photo, rating, vehicle, location, eta}}

Driver declines:
    DELETE Zookeeper lock
    SET driver status AVAILABLE again
    GEORADIUS → retry with next closest driver
    If ALL drivers decline → notify rider "Unable to find driver"
```

---

### Step 5: Real-Time Location Tracking (WebSocket)

```
From diagram: Location Update Svc (websocket server)

Driver app → WS /v1/driver/location (JWT auth, persistent connection)
    ↓
Every 3-5 seconds: {driver_id, lat, lon, timestamp, speed}
    ↓
Location Update Svc:
    GEOADD drivers:available {lon} {lat} {driver_id}   (if AVAILABLE)
    SET location:{driver_id} '{lat,lon}' EX 60
    PUBLISH driver_location:{driver_id} to Redis Pub/Sub
    Produce Kafka: driver.location_updated → Trip Update Consumer → DB history
    ↓
Rider app → WS /v1/trip/{trip_id}/track
    WebSocket Gateway SUBSCRIBE driver_location:{driver_id}
    Forward to rider: {type: 'driver_location', lat, lon, eta_min}
    Rider app: smooth marker animation + ETA countdown

Geofencing: driver within 50m of pickup →
    distance(driver_loc, pickup_loc) < 50m  [Haversine formula]
    → UPDATE trips SET status='DRIVER_ARRIVED'
    → Push + WebSocket: "Your driver has arrived!"
```

**Bandwidth optimization:**
- Skip update if moved < 10 meters (stationary)
- Reduce frequency if speed < 5 km/h (1 update/10s vs 1/3s)
- Protocol Buffers instead of JSON (50% size reduction)

---

### Step 6: Trip Start → Completion → Payment

```
Driver clicks "Start Trip"
    POST /v1/api/ride/{trip_id}/start
    UPDATE trips SET status='IN_PROGRESS', start_time=now()
    Notify rider: "Your trip has started!"

Driver clicks "Complete Trip"
    POST /v1/api/ride/{trip_id}/complete
    Calculate final fare:
        actual_distance (from location history or Google Maps)
        total_time = now() - start_time
        final = (base + distance×rate + time×rate) × surge_multiplier
    BEGIN TRANSACTION:
        UPDATE trips SET status='COMPLETED', end_time, actual_fare, distance, duration
        UPDATE drivers SET status='AVAILABLE', current_trip_id=NULL
    COMMIT
    GEOADD drivers:available {lon} {lat} {driver_id}  (back in pool)
    Stripe payment: POST to Payment Gateway
    Publish Kafka: trip.completed → analytics, driver payout, receipt
    Send receipt: email/SMS with fare breakdown
```

---

### Step 7: Surge Pricing Algorithm

```
Background Surge Calculator runs every 60 seconds per geohash cell (5km × 5km):

available_drivers  = GEORADIUS drivers:available {cell_center} 5km COUNT
pending_requests   = SELECT COUNT(*) FROM ride_requests WHERE status='PENDING'
                     AND pickup IN area AND created_at > now() - 10min

demand_ratio = pending_requests / available_drivers

demand_ratio < 1.2  →  multiplier = 1.0× (no surge)
1.2 – 2.0           →  multiplier = 1.2×
2.0 – 3.0           →  multiplier = 1.5×
3.0 – 5.0           →  multiplier = 1.8×
>= 5.0              →  multiplier = 2.0–3.0× (MAX CAP = 3.0×)

Store: SET surge_multiplier:{geohash} 1.8 EX 120 (2 min TTL)

Smoothing (prevent sudden jumps):
    new_surge = 0.7 × old_surge + 0.3 × calculated_surge
    Example: old=1.5, calc=2.0 → new = 0.7×1.5 + 0.3×2.0 = 1.65×

Rider must EXPLICITLY accept surge before request is confirmed.
Max cap = 3.0× (anti-price gouging)
```

---

### Step 8: Rating & Feedback (from diagram — Rating Svc + Aggregator Svc)

```
Post-trip: Rider app shows "How was your ride?" prompt (1–5 stars)

POST /v1/api/ride/{trip_id}/rate  {driver_rating: 5, feedback: "Great ride!"}
    ↓
Rating Svc:
    Validate: rider_id matches trip, rating not already submitted
    INSERT INTO ratings (rideId, senderId=rider_id, receiverId=driver_id, rating, timestamp)
    ↓
Aggregator Svc (shown in LLD diagram):
    SELECT AVG(rating) FROM ratings WHERE receiverId = {driver_id}
    UPDATE drivers SET avg_rating = {new_avg}, total_ratings = total_ratings + 1

Driver also rates rider:
    POST /v1/api/ride/{trip_id}/rate  {rider_rating: 4}
    INSERT INTO ratings (senderId=driver_id, receiverId=rider_id, ...)
    UPDATE riders SET avg_rating = {new_avg}
```

**Rating rules (from blog):**
- Higher rated drivers get **prioritized** in matching
- Low rated riders (< 4.0) may have longer wait times — drivers see rider rating before accepting
- Persistent avg < 4.0 → triggers account review
- **ANONYMOUS:** receiver sees score, never sender identity (diagram explicitly labels "anonymous")
- Diagram shows: `senderId, receiverId, rating, timestamp, rideId` — NOT rider_rating/driver_rating as separate columns

---

### Step 10: Notification System — Full Flow (FCM + APN from diagram)

**Architecture:**
```
Kafka events (ride.matched, trip.started, driver.ride_offered, trip.completed)
    → Notification Svc (consumer group)
    → FCM (Android) / APN (iOS)          ← push when app in background
    → Redis Pub/Sub → WebSocket Gateway  ← in-app when app in foreground
```

**Device token registration:**
```
On app login / install:
    POST /v1/api/devices {user_id, device_token, platform: 'ios'/'android'}
    INSERT INTO device_tokens (user_id, device_token, platform, active: true)
    Update on token refresh (iOS rotates tokens periodically)
```

**Full notification send flow:**
```
1. Ride Svc → Kafka 'ride.matched': {trip_id, rider_id, driver_name, vehicle_model, eta_min}
2. Notification Svc consumes event
3. SELECT device_token, platform FROM device_tokens
   WHERE user_id={rider_id} AND active=true
   (user may have iPhone + iPad — send to ALL active devices)
4. Build payload:
   {title: 'Driver Assigned!',
    body: '{driver_name} arriving in {eta_min} min',
    data: {trip_id, action: 'open_trip_screen', deep_link: 'app://trip/{trip_id}'}}
5. FCM (Android): fcm.send({registration_ids: [tokens], notification, data,
                             priority: 'high', time_to_live: 600})
   APN (iOS):     apn.send({token, payload: {aps: {alert, sound:'default', badge:1}}})
6. Simultaneously: PUBLISH user:{rider_id}:notifications to Redis Pub/Sub
   → WebSocket Gateway forwards to rider if app is open (<100ms in-app)
```

**Notification types + priority + TTL:**
```
Type                    Priority    TTL
ride_matched            HIGH        10 min   (stale if driver moved on)
driver_arrived          HIGH        5 min
trip_started            HIGH        -
trip_completed          NORMAL      -
payment_processed       NORMAL      -
surge_active_nearby     NORMAL      1 hr
driver_ride_offered     HIGH        30 sec   (driver must see immediately)
promotion               LOW         24 hr
```

**Multi-device synchronization:**
```
User has iPhone + iPad both logged in → push sent to BOTH
When one device acknowledges (user taps):
    SET notification:{notification_id}:read true
    Publish 'notification_read' → other device dismisses duplicate via WebSocket
```

**Failure handling + Dead Letter Queue:**
```
Invalid token (app uninstalled):
    FCM/APN returns 'invalid token' / 'BadDeviceToken'
    → UPDATE device_tokens SET active=false WHERE device_token={token}

Transient failure (network timeout):
    Retry with exponential backoff: 1s → 2s → 4s (max 3 retries)

Service unavailable (FCM/APN down):
    Queue in Kafka (7-day retention)
    Replay when service restored

Critical notification failure (payment failed, driver assigned):
    After all retries exhausted → Dead Letter Queue (DLQ)
    → Fallback: SMS via Twilio ($0.01–0.05 per SMS)
    → Manual review for DLQ entries
```

**Batching (bulk sends):**
```
Surge alert to 10K users in area:
    Batch 1000 tokens per FCM multicast API call
    Worker pool (50 threads) sends in parallel
    FCM multicast: single API call → array of 1000 tokens
    Rate: FCM handles 1 million messages/min
```

**Silent notifications (background data sync):**
```
Purpose: update app data WITHOUT alerting user
iOS: content-available: 1 flag → triggers background app refresh
Android: data-only message (no notification UI shown)

Use cases:
    Update driver location cache in rider app (background)
    Sync ride history
    Refresh surge pricing heatmap
```

**Push vs WebSocket decision:**
```
App FOREGROUND  → WebSocket (<100ms, direct)
App BACKGROUND  → Push notification (1–3s via FCM/APN)
CRITICAL + push fails → SMS fallback (Twilio)

Do NOT use push for location updates (too slow) → always WebSocket
```

---

### Step 11: Driver Availability Management (heartbeat)

```
Driver goes ONLINE:
    POST /v1/api/driver/status {status: 'AVAILABLE', current_location}
    UPDATE drivers SET status='AVAILABLE', last_online_at=now()
    GEOADD drivers:available {lon} {lat} {driver_id}
    SET driver:{driver_id}:status 'AVAILABLE' EX 300  (5 min TTL)

Heartbeat (every 30 seconds from driver app via WebSocket):
    {driver_id, lat, lon, status, timestamp}
    ↓
Location Update Svc:
    EXPIRE driver:{driver_id}:status 300       (refresh TTL)
    GEOADD drivers:available {lon} {lat} {driver_id}  (update position)

    If heartbeat MISSED for 2 minutes:
        DEL driver:{driver_id}:status
        GEOREM drivers:available {driver_id}
        → driver auto-marked offline

Driver goes OFFLINE:
    POST /v1/api/driver/status {status: 'OFFLINE'}
    UPDATE drivers SET status='OFFLINE'
    DEL driver:{driver_id}:status
    GEOREM drivers:available {driver_id}
    Close WebSocket connection

Auto-offline trigger:
    Driver hasn't accepted a ride in 30 min while online
    → Prompt: "Still available?" → no response in 5 min → auto-offline
```

**Full status transition (from blog):**
```
OFFLINE → AVAILABLE (go online)
        → BUSY      (assigned ride, Zookeeper lock acquired)
        → IN_TRIP   (trip started)
        → AVAILABLE (trip completed, back in pool)
        → OFFLINE   (go offline)
```

---

### Step 12: Trip Cancellation Handling

```
Rider cancels BEFORE driver accepts (status = PENDING):
    DELETE ride_request from Redis + DB
    No cancellation fee
    Grace period: FREE cancel within 2 min of request if no driver assigned yet

Rider cancels AFTER driver accepts (status = MATCHED):
    Check if driver has NOT started yet
    Apply cancellation fee (e.g., $5 / Rs 50)
    UPDATE trips SET status='CANCELLED_BY_RIDER', cancellation_fee={fee}
    Charge fee via Payment Gateway
    Release driver:
        UPDATE drivers SET status='AVAILABLE'
        GEOADD drivers:available {lon} {lat} {driver_id}
        Remove Zookeeper lock if still held
    Notify driver: "Rider cancelled. Rs 50 cancellation fee credited."

Rider cancels DURING trip: NOT ALLOWED
    Must complete trip; disputes handled via support ticket

Driver cancels:
    POST /v1/api/ride/{trip_id}/cancel {reason: 'rider_not_at_pickup'}

    Valid cancellation (rider no-show after 5 min wait):
        No penalty to driver
        Retry matching rider with next available driver

    Invalid cancellation (driver just doesn't want ride):
        Driver rating reduced
        Acceptance rate decreased → affects matching priority (deprioritized)
        Multiple invalid cancellations → temporary account suspension

    Either case:
        Release Zookeeper lock
        SET driver status → AVAILABLE
        GEORADIUS → retry with next driver for rider
```

---

### Step 13: Analytics & Monitoring (Trip Update Consumer from diagram)

**Data pipeline:**
```
Kafka 'trip.*' + 'driver.location_updated' topics
    → Spark Streaming / Flink (real-time processing)
    → Data Warehouse (BigQuery / Redshift)
    → BI Dashboards (Tableau / Looker)
```

**Real-time operational metrics:**
```
Active trips count per region
Average wait time (request → driver assigned)  ← SLA: < 1 min
Average trip duration
Surge multiplier heatmap per geohash
Driver utilization rate (time in trip / time online)
Revenue per hour
Cancellation rate (rider vs driver separately)
```

**Operational dashboard alerts (from blog):**
```
avg_wait_time > 5 min   → notify ops team
available_drivers < 10 in high-demand area → trigger driver incentives
Spike in cancellations  → investigate (driver shortage? bad weather?)
```

**Fraud detection (from blog):**
```
Fake GPS:      driver location jumps (not physically moving) → flag trip
Collusion:     driver + rider same person gaming bonus system → ML model
Fare gaming:   driver taking longer route intentionally → compare actual vs optimal route
Low ratings:   sudden drop for a driver → trigger manager review

ML model: trained on historical patterns, flags suspicious trips for manual review
```

---

### Step 14: Scaling & Performance Optimization

**Database sharding:**
```
Trips table:   shard by geohash of pickup_location
               → each shard handles specific geographic area
               → most queries local to rider's region

Drivers table: shard by driver_id hash
               → horizontal scaling, even distribution

Cross-region queries rare (SF rider won't query NYC drivers)
```

**Kafka partitioning:**
```
driver.location_updated → partition by driver_id  (100 partitions)
trip.* events           → partition by trip_id

Consumer groups:
    location-persistence  → writes location history to DB
    analytics             → aggregates real-time metrics
    notifications         → sends FCM/APN push
```

**Zookeeper clustering (5-node ensemble):**
```
High availability: 5 nodes, quorum = 3 nodes for write consensus
Auto-failover: if leader dies → new leader elected in < 1 second
Session timeout: 30 seconds (balance false-positives vs lock-release speed)
Monitoring: lock acquisition > 10ms → alert; ephemeral node count per driver should be 0 or 1
```

**WebSocket scaling:**
```
Each WS gateway instance: 10K connections
100K active trips = 100K drivers + 100K riders = 200K connections = 20 instances
LB: sticky sessions (IP hash) — rider stays on same instance for trip duration
Failover: client auto-reconnects on instance death (1–2s interruption, exponential backoff)
```

**Caching strategy summary:**
```
Driver locations     → Redis TTL 60s   (refreshed every 3–5s by WebSocket)
Driver availability  → Redis geospatial index, evicted on offline/busy
Surge multipliers    → Redis TTL 120s  (recalculated every 60s)
Fare estimates       → Redis TTL 300s  (5 min)
Trip details         → Redis TTL 7200s (2 hr max trip)
Driver status        → Redis TTL 300s  (5 min, refreshed by heartbeat)
```

**Rate limiting (API Gateway):**
```
Riders:          10 ride requests / hour        (prevent abuse)
Drivers:         1 status update / second        (prevent flooding)
Location updates: 1 per 3 seconds per driver    (balance freshness vs bandwidth)
```

**CDN:**
```
Driver/rider photos, vehicle images, map tiles → CloudFront
95% cache hit rate, reduces origin load
```

---

## 7. Database Schema (from diagram)

### PostgreSQL — Drivers (from diagram)
```sql
driver_id       uuid PRIMARY KEY
name            varchar(255)
email           varchar(255) UNIQUE
phone / mobileNum  varchar(20)
vehicleInfo     jsonb  -- {type, model, license_plate}
vehicle_type    ENUM(sedan, suv, bike, auto)
vehicle_model   varchar(100)
license_plate   varchar(20)
status          ENUM(IDLE, DRIVING, AVAILABLE, BUSY, OFFLINE, IN_TRIP)
                -- diagram uses IDLE / DRIVING explicitly
current_trip_id uuid FK → Trips (nullable)
avg_rating      decimal(3,2)
acceptance_rate decimal(5,2)
last_online_at  timestamp
```

### PostgreSQL — Trips/Rides (from diagram: "Ride" entity)
```sql
trip_id / requestId   uuid PRIMARY KEY
rider_id / userId     uuid FK → Riders
driver_id             uuid FK → Drivers
pickup_location       geography (PostGIS point)  -- pickupLng, pickupLat
drop_location         geography (PostGIS point)  -- dropLng, dropLat
sourceLat, destinationLon, drop_lng              -- from diagram fields
name                  varchar(255)               -- trip label
status          ENUM(PENDING, MATCHED, DRIVER_ARRIVED, IN_PROGRESS,
                     COMPLETED, CANCELLED_BY_RIDER, CANCELLED_BY_DRIVER)
vehicle_type    ENUM(sedan, suv, bike)
currency        varchar(3)                       -- from diagram (USD, INR)
estimated_fare, actual_fare, surge_multiplier
distance_km, duration_min
timestamp / requested_at, matched_at, start_time, end_time
payment_status  ENUM(PENDING, COMPLETED, FAILED, REFUNDED)
metadata        jsonb                            -- from diagram

INDEX (rider_id, created_at)
INDEX (driver_id, created_at)
INDEX (status, pickup_location) USING GIST
```

### PostgreSQL — Location (from diagram — separate history table)
```sql
location_id   uuid PRIMARY KEY
driverId / userId  uuid  -- tracks both driver and rider positions
name          varchar(255)
latitude      decimal(10,7)
longitude     decimal(10,7)
modifiedIS    timestamp   -- "modifiedIS" as shown in diagram (last modified)
```

### PostgreSQL — Ratings (from diagram: senderId / receiverId model)
```sql
rating_id    uuid PRIMARY KEY
rideId / trip_id  uuid FK, UNIQUE
senderId     uuid   -- who gave the rating (rider or driver)
receiverId   uuid   -- who received the rating
rider_id, driver_id  uuid  -- for easy querying
rating       int (1–5 stars)
timestamp    timestamp
feedback     text (optional)
-- ANONYMOUS: diagram shows "Rating (anonymous)" — receiver sees score, not sender identity
-- Aggregator Svc (shown in diagram) computes rolling avg from this table
```

### PostgreSQL — Payments
```sql
payment_id        uuid PRIMARY KEY
trip_id           uuid FK, UNIQUE
amount            decimal(10,2), currency varchar(3)
payment_method    ENUM(card, wallet, cash, upi)
stripe_payment_id varchar(255)
status            ENUM(PENDING, COMPLETED, FAILED, REFUNDED)
created_at, completed_at  timestamp
```

### Redis Keys (from diagram)
```
drivers:available            GEOSPATIAL INDEX  (GEOADD/GEORADIUS)
driver:{driverId}:status     STRING  EX 300    (5 min TTL, refreshed by heartbeat)
location:{driverId}          STRING  EX 60     (1 min TTL, updated every 3-5s)
trip:{tripId}:status         STRING  EX 7200   (2 hr max trip)
surge_multiplier:{geohash}   STRING  EX 120    (2 min TTL)
ride_request:{requestId}     STRING  EX 600    (10 min TTL)
fare_estimate:{requestId}    STRING  EX 300    (5 min TTL)
```

### Zookeeper (from diagram)
```
/locks/drivers/{driver_id}/{request_id}   ephemeral sequential node
Session timeout: 30 seconds
Purpose: prevent double assignment
Auto-cleanup: on timeout / service crash / disconnect
```

### Kafka Topics
```
ride.requested          → triggers Driver Matching Svc
driver.ride_offered     → notification to driver for accept/decline
ride.matched            → trip begins, notify rider
trip.started            → fare meter starts
trip.completed          → payment + analytics + receipt
driver.location_updated → 100K+ msgs/sec → Trip Update Consumer → DB history
```

---

## 8. Key Interview Q&A

### Q1: How do you prevent double assignment of a driver?

**Answer — Zookeeper distributed locking with ephemeral nodes:**

Scenario: Driver D1 available. Requests R1, R2, R3 created simultaneously. DMS1, DMS2, DMS3 each pick D1 as best match.

```
DMS1 creates: /locks/drivers/D1/req_R1_seq0001
DMS2 creates: /locks/drivers/D1/req_R2_seq0002
DMS3 creates: /locks/drivers/D1/req_R3_seq0003

GET_CHILDREN /locks/drivers/D1 → [seq0001, seq0002, seq0003]
DMS1 sees seq0001 is lowest → LOCK ACQUIRED → assigns D1 to R1
DMS2, DMS3 see seq0001 < theirs → LOCK FAILED → try next driver (D2, D3)
```

Why Zookeeper over Redis SETNX:
- Strong consistency (CP system) — guarantees only one lock holder
- Ephemeral nodes — auto-cleanup on failure/timeout (no manual TTL management)
- Sequential ordering — deterministic winner when concurrent
- Session management — detects service crashes automatically

---

### Q2: WebSocket vs HTTP Polling for location tracking?

| | HTTP Polling | WebSocket |
|--|--|--|
| Pattern | GET /location/{id} every 3s | Persistent connection |
| Traffic | 100K riders × 20 req/min = **33K req/sec** | Send only on location change |
| Latency | 1–3 seconds | **< 100ms** |
| Overhead | Full HTTP headers each request | No headers after handshake |
| Bandwidth | High (repeated idle requests) | **10× less** |

**WebSocket scaling:** 10K connections per instance → 200K connections (100K drivers + 100K riders) = 20 instances with sticky sessions (IP hash).

---

### Q3: How does surge pricing work?

```
Every 60s per 5km×5km geohash cell:
    demand_ratio = pending_requests / available_drivers

    < 1.2  → 1.0×   | 1.2–2.0 → 1.2×
    2.0–3.0 → 1.5×  | 3.0–5.0 → 1.8×  | ≥5.0 → up to 3.0× MAX

Smoothing: new = 0.7×old + 0.3×calculated  (no sudden jumps)
Store in Redis with 2-min TTL, recalculate every 60s
Rider MUST explicitly accept before request confirmed
```

---

### Q4: How do you find nearby drivers efficiently (geospatial)?

```
Redis GEORADIUS drivers:available -122.4194 37.7749 5km WITHDIST ASC COUNT 10
→ O(log N), ~10ms for 1M drivers

Filter by vehicle type:
    Option A: SISMEMBER drivers:sedan {driver_id} per result
    Option B: Separate indexes — GEOADD drivers:available:sedan / :suv / :bike

Sharding: US-West, US-East, EU, APAC → own Redis instance
Persistent: PostGIS with GIST index for analytics + fraud detection
Fallback: If no drivers in 5km → expand to 10km → 20km (exponential backoff)
```

---

### Q5: How does the notification system work?

```
Architecture: Kafka events → Notification Svc → FCM (Android) / APN (iOS)

Push (background):
    1-3 sec latency, best-effort delivery
    Retry: up to 4 weeks (FCM) / 1 day (APN) for offline devices
    Fallback: SMS via Twilio for CRITICAL (driver assigned, payment failed)

WebSocket (foreground/in-app):
    < 100ms latency
    Redis Pub/Sub: PUBLISH user:{rider_id}:notifications → Gateway → rider

Priority:
    HIGH: ride_matched, driver_arrived   (wake device from sleep)
    NORMAL: trip_completed, rating_reminder

TTL: ride_matched = 10 min; promotions = 24 hr
```

---

## 9. Key Numbers to Remember

| Metric | Value |
|--------|-------|
| Concurrent rides at peak | 100K globally |
| Location update frequency | Every 3–5 seconds |
| Matching latency target | < 1 second |
| Geospatial query time (1M drivers) | ~10ms (Redis GEORADIUS) |
| Zookeeper lock timeout | 30 seconds (ephemeral) |
| Lock acquisition time | < 10ms |
| WebSocket connections per instance | 10K |
| Push notification latency | 1–3 seconds |
| WebSocket in-app latency | < 100ms |
| Surge calculation interval | Every 60 seconds |
| Surge TTL in Redis | 2 minutes |
| Max surge cap | 3.0× |
| Driver status TTL | 5 min (refreshed by heartbeat) |
| Location TTL | 1 min (updated every 3–5s) |
| Fare estimate TTL | 5 min |
| Ride request TTL | 10 min (no driver = expire) |

---

## 10. Critical Gotchas — Interview Traps

> **NEVER trust Redis alone for driver availability.** Redis is ephemeral cache with TTL. Always validate driver status in DB before final assignment: `SELECT status FROM drivers WHERE driver_id = {id}`. Redis = speed; DB = truth.

> **ALWAYS explain Zookeeper locking** when asked about double assignment. This is the #1 follow-up question. Ephemeral nodes = automatic cleanup on crash. Sequential nodes = deterministic lock winner.

> **NEVER skip geofencing.** When driver within 50m of pickup: Haversine formula, trigger `DRIVER_ARRIVED` status, push notification + vibrate + sound.

> **Surge = explicit rider consent.** Rider MUST tap "Accept higher fare". Never silently charge surge.

> **WebSocket sticky sessions.** Load balancer uses IP hash, not round-robin, so rider stays on same WebSocket instance for trip duration.

> **Kafka decouples everything.** `driver.location_updated` consumed by: (1) Trip Update Consumer → DB history, (2) Analytics, (3) Fraud Detection. 100K+ events/sec.

> **Anonymous ratings.** Drivers see rating score, NOT rider identity. Stored separately from trip record (from diagram: "Rating — anonymous").

---

## 11. Component Summary (from diagram)

| Component | Role |
|-----------|------|
| LB + API Gateway | Auth, rate limiting, routing, RR load distribution |
| Ride Svc | Fare calculation, surge application, trip lifecycle |
| Driver Matching Svc | Geo-proximity search (geohash), Zookeeper lock, driver iteration |
| Location Update Svc | WebSocket server, Redis geospatial update, Kafka producer |
| Notification Svc | FCM + APN push, Kafka consumer, device token management |
| Rating Svc | Ratings aggregation, driver/rider avg update, anonymous storage |
| Payment Svc | Stripe integration, payment intent, refund handling |
| WebSocket Gateway | Auth + Authorization + **Session Stickiness** (IP hash ensures rider stays on same instance), Redis Pub/Sub bridge |
| Aggregator Svc | Computes rolling avg rating from Rating table, updates driver/rider avg_rating (shown in LLD diagram next to Rating) |
| Zookeeper | Driver locks (ephemeral nodes), prevents double assignment |
| Redis | Geospatial index, driver status TTL, surge cache, fare cache |
| Kafka | Event streaming: location, trips, notifications, analytics |
| Trip Update Consumer | Persists location history, generates route analytics |
| Location Map Svc | Google Maps / Apple Map — distance matrix, ETA, routing |
| Surge Calculator Svc | Demand/supply ratio per geohash, 60s background job |

---

*Source: UberSystemDesign diagram + blog deep-dive notes*
