Ride Sharing Service (Uber/Ola/Lyft)

"Rider requests → Geo-search nearby drivers → Zookeeper lock (prevent double assignment) → Driver accepts → WebSocket location tracking → Trip completion → Payment & Rating"

1. Functional Requirements

Feature 1: Riders should be able to get a fare estimation based on start location and destination
Feature 2: Riders should be able to request for a ride based on the estimated fare
Feature 3: Riders should be able to request different categories of car (Sedan, SUV, Bike, Auto)
Feature 4: Rider can see available drivers nearby in real-time on map with their current pickup/drop-off
Feature 5: Upon request, riders should be matched with a driver who is nearby (geo-proximity matching)
Feature 6: Get real-time tracking of the driver & user location during trip
Feature 7: After trip ends, rider should be able to rate their ride post-trip and make payment
Feature 8: Drivers should be able to accept/deny ride requests and update their status (available/busy/offline)
2. Non-Functional Requirements

Scale
Users & Drivers — Millions of users and drivers globally
Concurrent Rides — Hundreds of thousands of concurrent rides at peak hours
Performance & Consistency
CAP Theorem — Availability >> consistency (user) BUT consistency >> availability (driver assignment) - prevent double assignment
Ride Matching — Prevent any driver from being assigned multiple rides simultaneously (strong consistency)
Latency — <1 sec: driver should get assigned to a particular ride request, real-time location updates every 3-5 seconds
3. Core Entities (from image)

Entity 1: Rider - user_id, name, email, phone, payment_methods, current_location (lat/lon)
Entity 2: Driver - driver_id, name, vehicle_details (type, model, license_plate), rating, status (available/busy/offline), current_location
Entity 3: Location - Geospatial coordinates with timestamp for real-time tracking
Entity 4: Fare - fare_id, base_fare, distance_fare, time_fare, surge_multiplier, total_amount
Entity 5: Ride/Trip - ride_id, rider_id, driver_id, pickup_location, drop_location, status (requested/matched/started/completed/cancelled), estimated_fare, actual_fare, start_time, end_time
Entity 6: Rating - rating_id, ride_id, rider_rating (1-5 stars), driver_rating, feedback_text
Entity 7: Payment - payment_id, ride_id, amount, payment_method, status (pending/completed/failed)
4. API Designing (from image)

User/Rider APIs
POST /v1/api/fare/estimate — Get fare estimation with Request ID (different types of vehicle: Sedan, SUV, Bike, Pool)
POST /v1/api/ride/request — {pickup, drop, vehicleType} → Return rideId with driver details (if assigned success) OR (Matched with driver - sent message on the ride)
GET /v1/api/ride/history — Get ride history for user
POST /v1/api/ride/{rideId}/cancel — Cancel ride request
POST /v1/api/ride/{rideId}/rate — Rate driver after trip completion
Driver APIs
WS /v1/driver/location — WebSocket: {body: Lat, Long} - Update driver geolocation continuously every 3-5 seconds
POST /v1/api/ride/rides — {body: requestId, accept/deny} - Driver will accept/deny ride request, return as rideId
POST /v1/api/ride/{ride_id}/start — Mark trip as started when driver picks up rider
POST /v1/api/ride/{ride_id}/complete — Mark trip as completed when destination reached
5. High Level Design (from image)

Users/Clients (riders & drivers) → LB + API Gateway: Load balancing, authentication, authorization, rate limiting, traffic distribution (90%)
Ride Service (fare calculation): Calculates estimated fare based on pickup/drop distance, surge pricing, vehicle type
Driver Matching Service: Geo-proximity search to find nearby available drivers, assigns driver to ride request
Location Map Service (GMaps, Apple Map): Provides mapping, routing, ETA calculations, distance matrix
Rating Service → Rating DB: Stores and retrieves rider/driver ratings and feedback
Payment Service → Payment DB: Processes payments via payment gateway (Stripe/Razorpay), handles refunds
Location Update Service (WebSocket server): Ingests driver location pings every 3-5 seconds, updates Redis
Redis: Stores driver availability status with TTL (ephemeral data), driver locations (geospatial index), ride request status
Zookeeper: Distributed lock for driver assignment - prevents double assignment, ephemeral nodes for driver locks
Notification Service: FCM (Firebase Cloud Messaging) + APN (Apple Push Notification) for real-time notifications
Kafka: Event streaming for trip updates, location history, analytics, notifications
Drivers DB: Persistent storage for driver profiles, vehicle details, availability history
Ride DB: Persistent storage for all ride records, trip details, routes, fare breakdowns
Trip Update Consumer: Consumes Kafka events, persists location history, generates analytics (fare bonus tracking, operations)
6. Deep Dive Design (Low Level - from image)

Step 1: Fare Estimation (Surge Calculator from image)
Rider enters: pickup='123 Main St, SF' and drop='456 Market St, SF' in app
Client sends: POST /v1/api/fare/estimate with {pickup_lat: 37.7749, pickup_lon: -122.4194, drop_lat: 37.7849, drop_lon: -122.4094, vehicle_type: 'sedan'}
Ride Service: (1) Queries Location Map Service (Google Maps Distance Matrix API): GET distance & duration between pickup and drop, (2) Response: {distance: 5.2 km, duration: 12 min}
Calculate base fare: (1) Base rate: $2.50 (flat charge), (2) Distance rate: 5.2 km × $1.50/km = $7.80, (3) Time rate: 12 min × $0.30/min = $3.60, (4) Subtotal: $2.50 + $7.80 + $3.60 = $13.90
Apply surge pricing (from image shows 'Surge Calculator'): (1) Query Redis: GET surge_multiplier:{area_hash} for pickup area, (2) If high demand (>20 requests, <5 available drivers in 2km radius) → surge_multiplier = 1.5x, (3) Final fare: $13.90 × 1.5 = $20.85
Generate fare breakdown: {base_fare: 2.50, distance_fare: 7.80, time_fare: 3.60, surge_multiplier: 1.5, estimated_total: 20.85, currency: 'USD'}
Response to client: {request_id: uuid(), estimated_fare: 20.85, breakdown: {...}, eta_min: 12, distance_km: 5.2, vehicle_options: [{type: 'sedan', fare: 20.85}, {type: 'suv', fare: 28.50}, {type: 'bike', fare: 12.00}]}
Cache estimate: SET fare_estimate:{request_id} {fare_details} EX 300 (5 min TTL - estimate valid for 5 minutes)
Step 2: Ride Request & Driver Matching (Geo-search from image)
Rider confirms: Clicks 'Request Sedan' button
Client sends: POST /v1/api/ride/request with {request_id, pickup_lat, pickup_lon, drop_lat, drop_lon, vehicle_type: 'sedan', payment_method_id}
Ride Service validates: (1) Check fare estimate exists: GET fare_estimate:{request_id} from Redis, (2) Validate payment method: query Payment Service to ensure payment_method_id valid
Create ride request: INSERT INTO ride_requests (request_id, rider_id, pickup_location, drop_location, vehicle_type, estimated_fare, status: 'PENDING', created_at: now())
Store in Redis: SET ride_request:{request_id} {details} EX 600 (10 min TTL - request expires if no driver found)
Trigger driver matching: Publish to Kafka 'ride.requested' topic: {request_id, pickup_location, vehicle_type, timestamp}
Driver Matching Service consumes: Receives ride request event from Kafka
Geo-proximity search (from image shows 'Location Map Svc'): (1) Query Redis Geospatial: GEORADIUS drivers:available {pickup_lon} {pickup_lat} 5 km WITHDIST ASC (find available drivers within 5km, sorted by distance), (2) Filter by vehicle type: SISMEMBER drivers:sedan {driver_id} for each result, (3) Result: [{driver_id: D1, distance: 0.8 km}, {driver_id: D2, distance: 1.2 km}, {driver_id: D3, distance: 2.5 km}]
From image note: 'Ride = Rs 70/km waiting: Rs 1/min, Cab = Rs 50/km' - pricing varies by vehicle type
Iterate through candidates: FOR EACH driver in sorted list (closest first): (1) Attempt to lock driver using Zookeeper (explained in next step), (2) If lock acquired → assign driver, BREAK, (3) If lock failed (driver already assigned) → try next driver, (4) If all drivers tried and none available → return 'No drivers available, please try again'
Step 3: Driver Locking with Zookeeper (CRITICAL - from image diagram)
From image: Zookeeper section shows 'Driver Lock' with ephemeral nodes driver1_001, driver1_002, driver1_003
Purpose: Prevent double assignment - ensure one driver assigned to only one ride at a time
Zookeeper structure: /locks/drivers/{driver_id}/ephemeral_node (ephemeral node created for each lock attempt)
Lock attempt: Driver Matching Service tries to lock driver D1: (1) Create ephemeral node: CREATE /locks/drivers/D1/{request_id} (ephemeral, sequence), (2) Check if this node is lowest sequence number: GET_CHILDREN /locks/drivers/D1 ORDER BY sequence, (3) If our node is first → lock acquired, (4) If another node exists with lower sequence → lock failed (driver already locked by another request)
From image quote: 'when the driver matching service want to create a lock it creates a ephemeral node. if it is successfully, means it got the lock. Incase it got the NumberAlreadyExistException, then the driver is already assigned to someone (another) or try after sometime'
Lock acquired: (1) Mark driver as BUSY in Redis: SET driver:{D1}:status 'BUSY' EX 900, (2) Remove from available drivers geospatial index: GEOREM drivers:available {D1}, (3) Update database: UPDATE drivers SET status='BUSY', current_ride_id={request_id} WHERE driver_id='D1'
Send notification to driver: Publish to Kafka 'driver.ride_offered' → Notification Service sends push notification: FCM/APN to driver's device with {request_id, rider_name, pickup_location, estimated_fare, eta_to_pickup}
Driver app displays: Modal with ride details + 'Accept' / 'Decline' buttons, timeout 30 seconds (if no response, auto-decline)
Lock TTL: Ephemeral node has session timeout 30 seconds, if Driver Matching Service crashes or driver doesn't respond → Zookeeper auto-deletes node → lock released, another service instance can retry with next driver
From image quote: 'This lock is released, server have to delete the ephemeral node manually, of zookeeper will automatically delete it, if the server gets session timeout/disconnected/dies'
Step 4: Driver Accept/Decline
Driver sees ride request: Push notification received, app shows ride details
Driver clicks 'Accept': POST /v1/api/ride/rides with {request_id, action: 'accept'}
Ride Service validates: (1) Check Zookeeper lock still held: EXISTS /locks/drivers/{driver_id}/{request_id}, (2) Check request still pending: GET ride_request:{request_id} status from Redis
Create trip: BEGIN TRANSACTION; INSERT INTO trips (trip_id, request_id, rider_id, driver_id, pickup_location, drop_location, status: 'MATCHED', matched_at: now()); UPDATE ride_requests SET status='MATCHED', matched_at=now(); UPDATE drivers SET current_trip_id={trip_id}; COMMIT;
Update Redis: (1) SET trip:{trip_id}:status 'MATCHED' EX 3600, (2) SET driver:{driver_id}:current_trip {trip_id} EX 3600, (3) DEL ride_request:{request_id} (remove pending request)
Release Zookeeper lock: DELETE /locks/drivers/{driver_id}/{request_id} (lock no longer needed, driver assigned)
Notify rider: Publish Kafka 'ride.matched' → Notification Service sends push: 'Driver {name} accepted your ride! ETA 5 min', WebSocket message to rider app: {type: 'ride_matched', driver: {name, photo, rating, vehicle_details, current_location, eta_min: 5}}
Rider app updates: Shows driver on map with real-time location, driver details card, ETA countdown, 'Contact Driver' button (call/message)
Driver decline: POST /v1/api/ride/rides with {request_id, action: 'decline'} → (1) Release Zookeeper lock, (2) Mark driver available again: SET driver:{driver_id}:status 'AVAILABLE', (3) Retry matching with next closest driver, (4) If all drivers decline → notify rider 'Unable to find driver, please try again later'
Step 5: Real-Time Location Tracking (WebSocket from image)
From image: Shows 'Location Update Svc (websocket server)' receiving location updates from drivers
Driver app: Continuous location tracking (GPS updates every 3-5 seconds)
WebSocket connection: WS /v1/driver/location with Authorization: Bearer {JWT}, authenticated on connect
Location Update Service: (1) Receives location ping via WebSocket: {driver_id, lat: 37.7849, lon: -122.4194, timestamp, accuracy: 10m, speed: 25 km/h}, (2) Validates: driver authenticated, trip in progress or driver available
Update Redis geospatial: (1) GEOADD drivers:available {lon} {lat} {driver_id} if driver status='AVAILABLE', (2) If driver on trip: SET location:{driver_id} '{lat, lon, timestamp}' EX 60 (1 min TTL), (3) Publish to Redis Pub/Sub: PUBLISH driver_location:{driver_id} '{lat, lon, timestamp}' for real-time subscribers
Persist to Kafka: Publish 'driver.location_updated' event: {driver_id, trip_id, lat, lon, timestamp, speed} → consumed by Trip Update Consumer for history tracking
Rider receives updates: (1) Rider app subscribes to WebSocket: WS /v1/trip/{trip_id}/track, (2) Location Update Service forwards driver location: {type: 'driver_location', lat, lon, timestamp, eta_min: 4}, (3) Rider app updates driver marker on map, recalculates ETA, shows 'Driver is 0.5 km away'
From image shows: 'Kafka' → 'Trip Update Consumer' → 'persistently update the driver location, status, rider house tracking (operations), which could driver movement, e.g ETA message'
ETA calculation: (1) Fetch current route from Location Map Service: Google Maps Directions API with current driver location → pickup → drop, (2) Response: {distance_remaining: 2.5 km, duration_remaining: 8 min, route_polyline}, (3) Update ETA: HSET trip:{trip_id}:details 'eta_min' 8 'last_updated' {timestamp}
Geofencing: When driver within 50m of pickup: (1) Detect proximity: distance(driver_location, pickup_location) < 50m, (2) Notify rider: 'Your driver has arrived!', (3) Update trip status: 'DRIVER_ARRIVED'
Step 6: Trip Start
Driver picks up rider: Driver clicks 'Start Trip' button in app
Client sends: POST /v1/api/ride/{trip_id}/start
Ride Service: (1) Validate trip status: SELECT status FROM trips WHERE trip_id={trip_id}, must be 'MATCHED' or 'DRIVER_ARRIVED', (2) Update trip: UPDATE trips SET status='IN_PROGRESS', start_time=now(), start_location={current_driver_location}, (3) Start fare meter: Calculate ongoing fare based on distance/time
Update Redis: SET trip:{trip_id}:status 'IN_PROGRESS' EX 7200 (2 hour max trip duration)
Notify rider: Push notification 'Your trip has started!', WebSocket message: {type: 'trip_started', start_time, start_location}
Real-time tracking continues: Both rider and driver see each other's location on map (from WebSocket updates)
Calculate ongoing fare: (1) Fetch current location periodically: GET location:{driver_id}, (2) Calculate distance traveled: sum of distances between consecutive location updates, (3) Calculate time elapsed: current_time - start_time, (4) Ongoing fare: base_fare + (distance × distance_rate) + (time × time_rate) × surge_multiplier, (5) Update display: Rider app shows 'Current fare: $15.20' updated every 30 seconds
Step 7: Trip Completion & Payment
Driver reaches destination: Driver clicks 'Complete Trip' button
Client sends: POST /v1/api/ride/{trip_id}/complete
Ride Service: (1) Validate trip in progress: SELECT status FROM trips WHERE trip_id={trip_id} = 'IN_PROGRESS', (2) Fetch trip details: start_location, end_location, start_time, (3) Calculate final fare: (a) Total distance: query from location history OR Google Maps Directions API with actual route, (b) Total time: now() - start_time, (c) Final fare: base_fare + (distance × rate) + (time × rate) × surge_multiplier
Update trip record: BEGIN TRANSACTION; UPDATE trips SET status='COMPLETED', end_time=now(), end_location={current_driver_location}, actual_fare={calculated_fare}, distance_km={total_distance}, duration_min={total_time}; UPDATE drivers SET status='AVAILABLE', current_trip_id=NULL; COMMIT;
Update Redis: (1) SET trip:{trip_id}:status 'COMPLETED' EX 86400 (keep for 24 hours), (2) DEL driver:{driver_id}:current_trip, (3) Add driver back to available pool: GEOADD drivers:available {lon} {lat} {driver_id}
Process payment: (1) Fetch payment method: SELECT payment_method_id FROM riders WHERE rider_id={rider_id}, (2) Create payment intent: POST to Payment Gateway (Stripe) with {amount: {actual_fare}, currency: 'USD', customer_id, metadata: {trip_id}}, (3) Execute payment: stripe.paymentIntents.confirm({payment_intent_id}), (4) Handle response: if success → UPDATE trips SET payment_status='COMPLETED', payment_id={stripe_payment_id}; if failure → UPDATE trips SET payment_status='FAILED', retry with exponential backoff or notify rider to update payment method
From image: 'Rating (anonymous)' - ratings stored separately from trip, rider doesn't see who rated whom
Publish events: Kafka 'trip.completed' → {trip_id, rider_id, driver_id, actual_fare, distance, duration, timestamp} for analytics, driver payouts, rider receipts
Send receipt: Email/SMS to rider with trip summary, fare breakdown, payment confirmation, receipt PDF
Step 8: Rating & Feedback (from image shows Rating Service)
Post-trip: Rider app shows rating prompt: 'How was your ride?'
Rider rates: Selects 1-5 stars for driver + optional feedback text
Client sends: POST /v1/api/ride/{trip_id}/rate with {driver_rating: 5, feedback: 'Great driver, smooth ride!'}
Rating Service: (1) Validate: Ensure rider_id matches trip, rating not already submitted, (2) Insert rating: INSERT INTO ratings (rating_id, trip_id, rider_id, driver_id, driver_rating, rider_feedback, created_at), (3) Update driver average: (a) Fetch: SELECT AVG(driver_rating) FROM ratings WHERE driver_id={driver_id}, (b) Update: UPDATE drivers SET avg_rating={new_average}, total_ratings=total_ratings+1
From image: Ratings stored with metadata: 'comment (trimmed) riderId' - anonymous to driver, driver sees rating but not rider identity
Driver also rates rider: Driver app prompts 'Rate your passenger', POST /v1/api/ride/{trip_id}/rate with {rider_rating: 5}, UPDATE riders SET avg_rating={new_average}, total_ratings=total_ratings+1
Rating factors: (1) Driver rating affects future matching (higher rated drivers prioritized), (2) Rider rating affects driver acceptance (low rated riders may have longer wait times), (3) Persistent low ratings (< 4.0) trigger account review
Analytics: Track rating trends, identify issues (if ratings drop for specific driver → trigger manager review), segment by trip type, time of day, location
Step 9: Surge Pricing Algorithm (from image shows 'Surge Calculator')
Purpose: Balance supply (available drivers) and demand (ride requests) through dynamic pricing
Real-time monitoring: (1) Background job runs every 60 seconds per geohash area (5km × 5km grid), (2) Query Redis: GEORADIUS drivers:available {area_center_lon} {area_center_lat} 5 km → count available drivers, (3) Query DB: SELECT COUNT(*) FROM ride_requests WHERE status='PENDING' AND pickup_location IN {area} AND created_at > now() - INTERVAL '10 min' → count pending requests
Calculate demand/supply ratio: (1) demand_ratio = pending_requests / available_drivers, (2) If demand_ratio < 1.5 → no surge (multiplier = 1.0), (3) If 1.5 <= demand_ratio < 3 → low surge (multiplier = 1.3x), (4) If 3 <= demand_ratio < 5 → medium surge (multiplier = 1.5x), (5) If demand_ratio >= 5 → high surge (multiplier = 2.0x or higher, max 3.0x)
Example calculation: Area = Downtown SF, Available drivers = 20, Pending requests = 80, demand_ratio = 80/20 = 4.0 → surge_multiplier = 1.8x, Rider sees: 'Fare increased due to high demand (1.8×)'
Store in Redis: SET surge_multiplier:{area_geohash} 1.8 EX 120 (2 min TTL, recalculated every 60 seconds)
Notify users: (1) Update rider app: Show heatmap with surge areas in red/orange, (2) Display message: 'High demand in your area. Fares are higher than usual.', (3) Option: 'Notify me when prices drop' → push notification when surge multiplier falls below 1.2x
Driver incentives: During high surge, notify nearby offline drivers: 'Earn 1.5× more! Go online now.' to increase supply
Anti-gaming: (1) Cap maximum surge at 3.0× (prevent price gouging), (2) Surge applies only to new requests (not pre-booked rides), (3) Rider must explicitly accept surge before request confirmed
Step 10: Notification System (from image shows FCM + APN)
From image: 'Notification Svc' → 'FCM = Firebase Cloud Messaging' + 'APN = Apple Push Notification'
Architecture: Notification Service consumes Kafka events: 'ride.requested', 'ride.matched', 'trip.started', 'trip.completed', 'driver.ride_offered'
Device token management: (1) On app login: rider/driver registers device token, (2) Store: INSERT INTO device_tokens (user_id, device_token, platform: 'ios'/'android', active: true), (3) Update on app reinstall or token refresh
Send notification: (1) Notification Service receives Kafka event: {type: 'ride.matched', rider_id, driver_name, eta_min}, (2) Fetch device tokens: SELECT device_token, platform FROM device_tokens WHERE user_id={rider_id} AND active=true, (3) Build notification payload: {title: 'Driver Assigned!', body: '{driver_name} will arrive in {eta_min} min', data: {trip_id, driver_id, action: 'open_trip_screen'}}, (4) Send via FCM (Android): fcm.send({to: device_token, notification: {...}, data: {...}}), (5) Send via APN (iOS): apn.send({token: device_token, payload: {...}})
Notification types: (1) Ride matched → rider & driver, (2) Driver arrived → rider, (3) Trip started → rider, (4) Trip completed → rider & driver, (5) Payment processed → rider, (6) Driver declined → internal, retry matching, (7) Surge pricing changed → nearby riders
Delivery handling: (1) If FCM/APN returns invalid token → mark device_token as inactive: UPDATE device_tokens SET active=false, (2) Retry on transient failures (network timeout) with exponential backoff: 1s, 2s, 4s, max 3 retries, (3) Dead letter queue: Failed notifications after retries → stored for manual review
In-app notifications: (1) If app in foreground: Display banner notification + update UI directly, (2) If app in background: OS handles notification display, tapping opens app with deep link to trip screen
WebSocket alternative: For latency-critical updates (driver location, real-time ETA), use WebSocket instead of push notifications (sub-second latency vs 1-3 second push latency)
Step 11: Driver Availability Management
Driver goes online: (1) Driver opens app, clicks 'Go Online', (2) Request location permission (required), (3) POST /v1/api/driver/status with {status: 'AVAILABLE', current_location}
Ride Service: (1) Validate driver approved and documents verified, (2) Update database: UPDATE drivers SET status='AVAILABLE', last_online_at=now(), (3) Add to Redis geospatial index: GEOADD drivers:available {lon} {lat} {driver_id}, (4) Set status in Redis: SET driver:{driver_id}:status 'AVAILABLE' EX 300 (5 min TTL, refreshed by heartbeat)
Heartbeat mechanism: (1) Driver app sends WebSocket ping every 30 seconds: {driver_id, lat, lon, status, timestamp}, (2) Location Update Service: (a) Refresh Redis TTL: EXPIRE driver:{driver_id}:status 300, (b) Update geospatial: GEOADD drivers:available {lon} {lat} {driver_id}, (c) If heartbeat missed for 2 minutes → mark driver offline: DEL driver:{driver_id}:status, GEOREM drivers:available {driver_id}
Driver goes offline: (1) Driver clicks 'Go Offline' OR app closed, (2) POST /v1/api/driver/status with {status: 'OFFLINE'}, (3) Update DB: UPDATE drivers SET status='OFFLINE', (4) Remove from Redis: DEL driver:{driver_id}:status, GEOREM drivers:available {driver_id}, (5) Close WebSocket connection
Automatic offline: If driver doesn't accept rides for 30 min while online → prompt: 'You haven't accepted rides. Still available?' → if no response in 5 min → auto-offline
Status transitions: OFFLINE → AVAILABLE (go online) → BUSY (assigned ride) → IN_TRIP (trip started) → AVAILABLE (trip completed) → OFFLINE (go offline)
Step 12: Trip Cancellation Handling
Rider cancels before driver accepts: (1) POST /v1/api/ride/{request_id}/cancel, (2) Check status: if status='PENDING' → DELETE ride_request, refund any pre-authorization, (3) No cancellation fee
Rider cancels after driver accepts: (1) Check trip status: if status='MATCHED' and driver hasn't started → apply cancellation fee (e.g., $5), (2) UPDATE trips SET status='CANCELLED_BY_RIDER', cancelled_at=now(), cancellation_fee={fee}, (3) Charge cancellation fee: CREATE payment with amount={fee}, (4) Release driver: UPDATE drivers SET status='AVAILABLE', current_trip_id=NULL, (5) Remove Zookeeper lock if still exists, (6) Add driver back to geospatial index: GEOADD drivers:available {lon} {lat} {driver_id}, (7) Notify driver: 'Rider cancelled the trip. $3 cancellation fee credited to your account.'
Rider cancels during trip: Not allowed, must complete trip and resolve disputes through support
Driver cancels: (1) POST /v1/api/ride/{trip_id}/cancel with {reason: 'rider_not_at_pickup'/'rider_misbehaving'/'emergency'}, (2) If cancellation valid (rider no-show after 5 min wait) → no penalty, (3) If cancellation invalid (driver just doesn't want ride) → penalty: (a) Driver rating reduced, (b) Accept rate decreased (affects matching priority), (c) Multiple invalid cancellations → temporary account suspension, (4) Release driver lock, set driver AVAILABLE, retry matching rider with new driver
Grace period: Rider can cancel free within 2 minutes of request if no driver assigned yet
Refund: If rider cancels with valid reason (app error, long wait) → full refund via support ticket
Step 13: Analytics & Monitoring (Trip Update Consumer from image)
From image: 'Trip Update Consumer' consumes Kafka events → 'persistently update the driver location, status, rider house tracking (operations)'
Data pipeline: Kafka 'trip.*' topics → Spark Streaming / Flink → Data Warehouse (BigQuery / Redshift) → BI Dashboards (Tableau / Looker)
Real-time metrics: (1) Active trips count per region, (2) Average wait time (request → driver assigned), (3) Average trip duration, (4) Surge multiplier heatmap, (5) Driver utilization rate (time in trip / time online), (6) Revenue per hour, (7) Cancellation rate (rider vs driver)
Operational dashboards: (1) Live map showing all active trips, drivers, pending requests, (2) Anomaly detection: spike in cancellations, sudden drop in available drivers, region with unusually long wait times, (3) Alerts: if avg_wait_time > 5 min → notify operations team, if available_drivers < 10 in high-demand area → trigger driver incentives
Driver analytics: (1) Earnings dashboard: trips completed today, total earnings, average rating, acceptance rate, (2) Heatmap: high-demand areas with expected surge times, (3) Suggestions: 'Move 2 km north for more rides'
Rider analytics: (1) Trip history, spending patterns, favorite destinations, (2) Personalized offers: 'Ride to work for 20% off tomorrow morning'
Fraud detection: (1) Detect fake GPS (driver not actually moving but location jumps), (2) Detect collusion (driver and rider same person gaming system), (3) Detect fare manipulation (driver taking longer routes intentionally), (4) ML model trained on historical patterns flags suspicious trips for review
Step 14: Scaling & Performance Optimization
Geospatial indexing: (1) Redis Geo commands (GEOADD, GEORADIUS) provide O(log(N)) search for nearby drivers, (2) For 1M active drivers, search within 5km takes ~10ms, (3) Alternative: QuadTree or R-Tree for even faster searches at scale, (4) Partitioning: Shard by geographic region (US-West, US-East, EU, APAC) to distribute load
Database sharding: (1) Shard trips table by geohash of pickup location, each shard handles trips in specific geographic area, (2) Shard drivers table by driver_id hash, (3) Cross-region queries minimized (most queries local to rider's region)
Caching strategy: (1) Driver locations: Redis with 60-second TTL (refreshed by WebSocket pings), (2) Driver availability: Redis geospatial index, evicted on offline/busy, (3) Surge multipliers: Redis with 2-minute TTL, (4) Fare estimates: Redis with 5-minute TTL, (5) Trip details: Redis with 2-hour TTL during active trip
WebSocket scaling: (1) Each WebSocket gateway instance handles 10K connections, (2) For 1M concurrent drivers/riders, need 100 instances, (3) Load balancer with sticky sessions (IP hash) ensures user stays on same instance, (4) Failover: if instance dies, client auto-reconnects to different instance (1-2 second interruption)
Kafka partitioning: (1) Partition 'driver.location_updated' by driver_id (100 partitions), enables parallel consumption, (2) Partition 'trip.*' events by trip_id, (3) Consumer groups: location-persistence (writes to DB), analytics (aggregates metrics), notifications (sends push)
Zookeeper clustering: (1) 5-node Zookeeper ensemble for high availability, (2) Quorum: need 3 nodes for write consensus, (3) Auto-failover: if leader dies, new leader elected in <1 second, (4) Session timeout: 30 seconds (balance between false positives and lock release speed)
CDN for static assets: Driver/rider photos, vehicle images, map tiles served via CloudFront, 95% cache hit rate
Rate limiting: (1) Rider: 10 ride requests per hour (prevent spam/abuse), (2) Driver: 1 status update per second (prevent API flooding), (3) Location updates: 1 per 3 seconds (balance freshness vs bandwidth)
Database optimization: (1) Index on (pickup_location, status) for finding pending requests in area, (2) Index on (driver_id, status) for driver queries, (3) Partition trips table by month for historical data, (4) Archive trips older than 2 years to cold storage (S3 Glacier)
7. Database Schema Details (from image shows Drivers, Ride, Rating, Payment)

Riders (PostgreSQL)
rider_id — uuid PRIMARY KEY
name — varchar(255)
email — varchar(255) UNIQUE
phone — varchar(20) UNIQUE
payment_methods — jsonb ([{type: 'card', last4, stripe_customer_id}])
avg_rating — decimal(3,2) (average rating from drivers)
total_trips — int (lifetime trip count)
Drivers (PostgreSQL - from image)
driver_id — uuid PRIMARY KEY
name — varchar(255)
email — varchar(255) UNIQUE
phone — varchar(20)
vehicle_type — enum (sedan, suv, bike, auto)
vehicle_model — varchar(100) (e.g., 'Toyota Camry 2020')
license_plate — varchar(20)
status — enum (AVAILABLE, BUSY, OFFLINE, IN_TRIP)
current_trip_id — uuid FK → Trips (nullable)
avg_rating — decimal(3,2)
total_trips — int
acceptance_rate — decimal(5,2) (percentage of accepted ride offers)
last_online_at — timestamp
Trips/Rides (PostgreSQL - from image shows 'Ride')
trip_id — uuid PRIMARY KEY
rider_id — uuid FK → Riders
driver_id — uuid FK → Drivers
pickup_location — geography (PostGIS point)
drop_location — geography (PostGIS point)
status — enum (PENDING, MATCHED, DRIVER_ARRIVED, IN_PROGRESS, COMPLETED, CANCELLED_BY_RIDER, CANCELLED_BY_DRIVER)
vehicle_type — enum (sedan, suv, bike)
estimated_fare — decimal(10,2)
actual_fare — decimal(10,2)
surge_multiplier — decimal(3,2) (e.g., 1.5 for 1.5×)
distance_km — decimal(10,2)
duration_min — int
requested_at — timestamp
matched_at — timestamp
start_time — timestamp
end_time — timestamp
payment_status — enum (PENDING, COMPLETED, FAILED, REFUNDED)
Indexes — INDEX on (rider_id, created_at), INDEX on (driver_id, created_at), INDEX on (status, pickup_location) using GIST
Ratings (PostgreSQL - from image shows 'Rating (anonymous)')
rating_id — uuid PRIMARY KEY
trip_id — uuid FK → Trips, UNIQUE (one rating per trip per user)
rider_id — uuid
driver_id — uuid
driver_rating — int (1-5 stars, rider rates driver)
rider_rating — int (1-5 stars, driver rates rider)
rider_feedback — text (optional comment from rider)
driver_feedback — text (optional comment from driver)
created_at — timestamp
Note — Anonymous: drivers see rating but not rider identity, riders see rating but not driver identity in aggregated form
Payments (PostgreSQL - from image shows 'Payment')
payment_id — uuid PRIMARY KEY
trip_id — uuid FK → Trips, UNIQUE
amount — decimal(10,2)
currency — varchar(3) (e.g., 'USD', 'INR')
payment_method — enum (card, wallet, cash, upi)
stripe_payment_id — varchar(255) (external payment gateway reference)
status — enum (PENDING, COMPLETED, FAILED, REFUNDED)
created_at — timestamp
completed_at — timestamp
Redis - Driver Locations & Availability
drivers:available — GEOSPATIAL INDEX - GEOADD for available drivers, GEORADIUS for proximity search
driver:{driverId}:status — STRING (AVAILABLE/BUSY/OFFLINE) EX 300 (5 min TTL, refreshed by heartbeat)
location:{driverId} — STRING (JSON: {lat, lon, timestamp}) EX 60 (1 min TTL, updated every 3-5 sec)
trip:{tripId}:status — STRING (MATCHED/IN_PROGRESS/COMPLETED) EX 7200 (2 hour max trip)
surge_multiplier:{geohash} — STRING (decimal value: 1.5) EX 120 (2 min TTL, recalculated every 60 sec)
ride_request:{requestId} — STRING (JSON request details) EX 600 (10 min TTL, expires if no driver found)
Zookeeper - Driver Locks (from image diagram)
Lock path — /locks/drivers/{driver_id}/{request_id} - ephemeral sequential node
Purpose — Prevent double assignment - only one request can lock a driver at a time
Session timeout — 30 seconds - if service crashes or driver doesn't respond, lock auto-released
From image — Shows ephemeral nodes driver1_001, driver1_002, driver1_003 under Driver Lock
Kafka Topics
ride.requested — Ride request created, triggers driver matching
driver.ride_offered — Driver selected, notification sent for accept/decline
ride.matched — Driver accepted, trip begins
trip.started — Driver picked up rider, fare meter started
trip.completed — Trip ended, payment processed
driver.location_updated — Real-time location ping (100K+ messages/sec), consumed by Trip Update Consumer
8. Zookeeper Driver Locking - Deep Dive (Critical from image)

Problem: Multiple concurrent ride requests trying to assign same driver → double assignment without locking
From image diagram: Shows 'Zookeeper' with 'Driver Lock' containing ephemeral nodes driver1_001, driver1_002, driver1_003
Ephemeral node creation: When Driver Matching Service wants to lock driver D1 for request R1 → CREATE /locks/drivers/D1/request_R1 (ephemeral, sequential)
Lock acquisition check: (1) Get all children of /locks/drivers/D1, (2) Sort by sequence number, (3) If our node has lowest sequence → lock acquired, proceed with assignment, (4) If another node with lower sequence exists → lock failed, driver already locked by different request
From image quote: 'when the driver matching service want to create a lock it creates a ephemeral node. if it is successfully, means it got the lock. Incase it got the NumberAlreadyExistException, then the driver is already assigned to someone (another) or try after sometime'
Success path: Lock acquired → (1) Mark driver BUSY in Redis, (2) Remove from drivers:available geospatial index, (3) Update DB: drivers.status='BUSY', (4) Send notification to driver for accept/decline, (5) Wait for driver response (timeout 30 seconds)
Failure path: Lock not acquired → (1) Release any partial locks, (2) Move to next closest driver in candidate list, (3) Retry lock acquisition with driver D2, (4) If all drivers tried and failed → return 'No drivers available' to rider
Driver accepts: (1) Create trip record in DB, (2) Delete Zookeeper lock (no longer needed), (3) Driver assigned, lock mechanism complete
Driver declines: (1) Delete Zookeeper lock, (2) Mark driver AVAILABLE again in Redis, (3) Retry matching with next driver in list
Timeout handling: Driver doesn't respond within 30 seconds → (1) Zookeeper session timeout triggers, (2) Ephemeral node auto-deleted, (3) Driver marked AVAILABLE, (4) System retries with next driver, (5) Original driver receives late notification: 'Ride request expired'
From image quote: 'This lock is released, server have to delete the ephemeral node manually, of zookeeper will automatically delete it, if the server gets session timeout/disconnected/dies'
Crash recovery: If Driver Matching Service crashes while holding locks → (1) Zookeeper detects session loss, (2) All ephemeral nodes created by that session auto-deleted within 30 seconds, (3) Drivers unlocked automatically, (4) New service instance can retry matching
Why Zookeeper over Redis?: (1) Stronger consistency guarantees (CP system), (2) Built-in session management (ephemeral nodes), (3) Atomic lock operations with ordering, (4) Auto-cleanup on failure, (5) Redis SETNX could work but requires more manual cleanup logic
Alternative: Redis distributed lock with Redlock algorithm, but Zookeeper preferred for critical driver assignment use case
Monitoring: (1) Track lock acquisition time (<10ms typical), (2) Alert if lock acquisition fails >50% (indicates Zookeeper issues), (3) Track ephemeral node count per driver (should be 0 or 1, never >1), (4) Monitor session timeouts (too many = connectivity issues)
9. Scaling & Optimization Techniques

Technique 1: Redis Geospatial indexing - GEORADIUS searches 1M drivers in <10ms, O(log(N)) complexity, shard by geographic region
Technique 2: Zookeeper driver locking - Prevents double assignment with ephemeral nodes, auto-cleanup on timeout, <10ms lock acquisition
Technique 3: WebSocket for location updates - 100K concurrent connections per instance, persistent connection vs HTTP polling (100x less traffic)
Technique 4: Kafka event streaming - 100K+ location updates/sec, decouples services (location persistence, analytics, notifications)
Technique 5: Surge pricing - Dynamic supply/demand balancing, recalculated every 60 seconds per area, stored in Redis with 2-min TTL
Technique 6: Database sharding - Shard trips by pickup location geohash, shard drivers by driver_id, enables horizontal scaling
Technique 7: Caching strategy - Driver locations (60s TTL), availability (geospatial), surge (120s TTL), fare estimates (300s TTL)
Technique 8: Push notifications - FCM/APN for real-time alerts, WebSocket for in-app updates, hybrid approach for best latency
Technique 9: Geofencing - Detect driver arrival within 50m of pickup, trigger automatic status updates, reduce manual actions
Technique 10: Rate limiting - 10 ride requests/hour per rider, 1 location update/3 sec per driver, prevents abuse and API flooding
Technique 11: CDN for assets - Driver/vehicle photos, map tiles via CloudFront, 95% cache hit rate, reduces origin load
Technique 12: Database optimization - PostGIS for geospatial queries, indexes on (status, location), partition by month for historical data
10. Common Interview Questions

Q
How do you prevent double assignment of a driver to multiple ride requests?
A
Use Zookeeper distributed locking with ephemeral nodes: Scenario: Driver D1 available at location X, simultaneously 3 ride requests R1, R2, R3 created nearby. Driver Matching Service instances (DMS1, DMS2, DMS3) each select D1 as best match for their respective requests. Lock acquisition:

(1) DMS1 tries to create /locks/drivers/D1/request_R1_seq0001 (ephemeral, sequential node), Zookeeper assigns sequence 0001,

(2) DMS2 tries to create /locks/drivers/D1/request_R2_seq0002, Zookeeper assigns sequence 0002,

(3) DMS3 tries to create /locks/drivers/D1/request_R3_seq0003, sequence 0003. Checking lock ownership: Each DMS gets children of /locks/drivers/D1: [request_R1_seq0001, request_R2_seq0002, request_R3_seq0003]. DMS1 sees its node (seq0001) is lowest → lock acquired → proceeds with assignment. DMS2 and DMS3 see seq0001 < their sequences → lock NOT acquired → must try next driver. DMS1 proceeds:

(1) Mark D1 as BUSY in Redis: SET driver:D1:status 'BUSY' EX 900,

(2) Remove from available drivers: GEOREM drivers:available D1,

(3) Update database: UPDATE drivers SET status='BUSY', current_ride_id={R1},

(4) Send push notification to driver for accept/decline via Kafka → Notification Service. DMS2 and DMS3 retry:

(1) Delete their Zookeeper nodes (didn't get lock),

(2) Select next closest driver (D2, D3) from candidate list,

(3) Attempt lock acquisition for new drivers. Driver D1 responds: If accepts → DELETE /locks/drivers/D1/request_R1_seq0001 (lock released, no longer needed), CREATE trip in DB, notify rider. If declines or timeout (30 sec) →

(1) Zookeeper session expires → ephemeral node auto-deleted,

(2) D1 marked AVAILABLE again: SET driver:D1:status 'AVAILABLE', GEOADD drivers:available {lon} {lat} D1,

(3) System can retry D1 for other requests. Why Zookeeper?:

(1) Strong consistency (CP system) - guarantees only one lock holder,

(2) Ephemeral nodes - auto-cleanup on failure/timeout,

(3) Atomic operations - sequential node creation with ordering,

(4) Session management - built-in detection of client crashes. Alternative approach: Redis distributed lock with Redlock algorithm:

(1) SETNX lock:driver:D1 {request_id} EX 30,

(2) If returns 1 → lock acquired,

(3) If returns 0 → already locked. But Redis approach requires:

(a) Manual TTL management,

(b) No automatic ordering of concurrent lock attempts,

(c) Risk of TTL expiring before lock released if service slow. Zookeeper provides stronger guarantees for critical use case (preventing revenue loss from double assignments, poor UX).

Q
How does real-time location tracking work with WebSockets?
A
WebSocket enables bidirectional persistent connection for sub-second location updates: Architecture: Driver app maintains WebSocket connection to Location Update Service (WebSocket server), rider app subscribes to driver location updates via separate WebSocket. Driver side:

(1) Driver goes online → app requests location permission → establishes WebSocket: WS /v1/driver/location with JWT token,

(2) Location Update Service authenticates: Validates JWT, checks driver approved, creates session {session_id, driver_id, connected_at},

(3) GPS tracking starts: Android/iOS location API provides updates every 3-5 seconds with {lat, lon, accuracy, speed, timestamp},

(4) App sends via WebSocket: {driver_id, lat: 37.7849, lon: -122.4194, accuracy: 10m, speed: 25 km/h, timestamp},

(5) Location Update Service processes:

(a) Validates driver in active trip or available,

(b) Updates Redis geospatial: GEOADD drivers:available {lon} {lat} {driver_id} if driver available,

(c) Sets location cache: SET location:{driver_id} '{lat, lon, timestamp}' EX 60 (1 min TTL),

(d) Publishes to Redis Pub/Sub: PUBLISH driver_location:{driver_id} '{lat, lon, timestamp}' for real-time subscribers,

(e) Sends to Kafka: 'driver.location_updated' event for persistence → Trip Update Consumer writes to location_history table. Rider side:

(1) Rider matched with driver → app subscribes: WS /v1/trip/{trip_id}/track with rider auth token,

(2) WebSocket Gateway authenticates: Validates rider_id owns this trip_id,

(3) Gateway subscribes to Redis Pub/Sub: SUBSCRIBE driver_location:{driver_id},

(4) When driver location published → Gateway forwards to rider via WebSocket: {type: 'driver_location', lat, lon, timestamp, eta_min: 4, distance_m: 500},

(5) Rider app updates:

(a) Moves driver marker on map smoothly (interpolation),

(b) Recalculates ETA: distance_remaining / avg_speed,

(c) Shows status: 'Driver is 500m away, arriving in 4 min'. During trip: Both rider and driver see each other's locations (bidirectional), rider sees: 'Your trip in progress', driver sees: 'Passenger onboard'. ETA calculation:

(1) Every 30 seconds, Location Update Service queries Google Maps Directions API: {origin: {driver_current_location}, destination: {pickup_location}, mode: 'driving'},

(2) Response: {distance_remaining: 2500m, duration: 8 min, route_polyline},

(3) Broadcast ETA update to rider: {eta_min: 8, distance_m: 2500}. Geofencing:

(1) When driver within 50m of pickup: calculate distance(driver_location, pickup_location) using Haversine formula,

(2) If distance < 50m → trigger event: {type: 'driver_arrived', driver_id, trip_id},

(3) Update trip status: UPDATE trips SET status='DRIVER_ARRIVED',

(4) Notify rider: Push notification + WebSocket message 'Your driver has arrived!',

(5) Rider app shows: Vibrate phone, play arrival sound, display 'Driver is here' banner. Connection management:

(1) Heartbeat: Client sends ping every 30 seconds, server responds with pong + {server_time}, detects stale connections,

(2) Reconnect: If WebSocket closes (network loss, app backgrounded), client auto-reconnects with exponential backoff (1s, 2s, 4s, 8s, max 30s),

(3) Resume: On reconnect, request last known state: {last_received_timestamp}, server sends missed updates. Bandwidth optimization:

(1) Send location only if moved >10 meters (skip updates when stationary),

(2) Reduce frequency if speed < 5 km/h (1 update per 10 sec vs 3 sec),

(3) Compress updates: Binary protocol (Protocol Buffers) instead of JSON (50% size reduction),

(4) Batch: Multiple location updates in single WebSocket frame if queued. Scaling:

(1) Each WebSocket server handles 10K connections (1 connection per active driver + riders),

(2) For 100K active trips (100K drivers + 100K riders = 200K connections), need 20 instances,

(3) Load balancer with sticky sessions (IP hash) ensures rider stays on same instance for trip duration,

(4) Redis Pub/Sub scales horizontally (multiple subscribers),

(5) Kafka buffers location history for offline processing. Why WebSocket vs HTTP polling?: HTTP polling: Client sends GET /location/{driver_id} every 3 seconds → 100K riders × 20 requests/min = 2M requests/min = 33K req/sec. WebSocket: Persistent connection → send update only when location changes → 100K drivers × 20 updates/min = 2M updates/min but NO HTTP overhead (no headers, no handshake) → 10x less bandwidth, <100ms latency vs 1-3 sec polling delay.

Q
How do you calculate surge pricing dynamically?
A
Surge pricing balances supply and demand through real-time monitoring and dynamic multipliers: Geohash grid system: Divide geographic area into 5km × 5km grid cells using geohash (6-character precision), each cell independently tracks supply/demand, example: Downtown SF = 9q8yy, Financial District = 9q8yw. Real-time monitoring (runs every 60 seconds): Background job (Surge Calculator Service) for EACH geohash:

(1) Count available drivers: Redis query: GEORADIUS drivers:available {cell_center_lon} {cell_center_lat} 5 km → count results, example: Downtown SF has 15 available drivers,

(2) Count pending requests: Database query: SELECT COUNT(*) FROM ride_requests WHERE status='PENDING' AND ST_DWithin(pickup_location, ST_MakePoint({cell_center_lon}, {cell_center_lat}), 5000) AND created_at > now() - INTERVAL '10 min' → example: 45 pending requests in last 10 minutes. Calculate demand/supply ratio: demand_ratio = pending_requests / available_drivers = 45 / 15 = 3.0. Determine surge multiplier based on ratio:

(1) demand_ratio < 1.2 → no surge (multiplier = 1.0), plenty of drivers,

(2) 1.2 <= demand_ratio < 2.0 → low surge (multiplier = 1.2×), slight imbalance,

(3) 2.0 <= demand_ratio < 3.0 → medium surge (multiplier = 1.5×), moderate shortage,

(4) 3.0 <= demand_ratio < 5.0 → high surge (multiplier = 1.8×), significant shortage,

(5) demand_ratio >= 5.0 → very high surge (multiplier = 2.0-3.0×), severe shortage, max cap at 3.0×. Example calculation: Downtown SF at 8 PM Friday (high demand):

(1) Available drivers: 15,

(2) Pending requests: 45,

(3) demand_ratio = 3.0 → high surge,

(4) surge_multiplier = 1.8×,

(5) Base fare: $15 → Surge fare: $15 × 1.8 = $27. Store in Redis: SET surge_multiplier:9q8yy 1.8 EX 120 (2 min TTL, refresh every 60 sec ensures always fresh). Rider sees surge:

(1) Fare estimate API: POST /v1/api/fare/estimate → fetches surge: GET surge_multiplier:{pickup_geohash} from Redis,

(2) Response: {estimated_fare: 27.00, base_fare: 15.00, surge_multiplier: 1.8, surge_notice: 'Fares are higher due to increased demand'},

(3) Rider app displays: Red/orange heatmap overlay on map showing surge areas, modal: 'High demand! Fares are 1.8× normal. Want to wait for prices to drop?',

(4) Rider must explicitly accept surge: Click 'Accept higher fare' button before ride request submitted. Driver incentives during surge:

(1) Notify nearby offline drivers: Push notification 'Earn more! High demand in Downtown SF. Surge pricing active (1.8×).' with deep link to 'Go Online' screen,

(2) Bonus offers: 'Complete 3 rides in surge zone in next hour → $20 bonus' to increase supply. Smoothing algorithm: Prevent sudden jumps:

(1) New surge = 0.7 × old_surge + 0.3 × calculated_surge (exponential moving average),

(2) Example: Old surge = 1.5×, Calculated = 2.0×, New surge = 0.7×1.5 + 0.3×2.0 = 1.05 + 0.6 = 1.65×,

(3) Gradual increase feels fairer to users, prevents gaming (riders waiting for surge to drop). Historical trends:

(1) ML model predicts surge: Train on historical data (time of day, day of week, weather, events, holidays),

(2) Proactive driver positioning: 'High demand expected in Financial District at 5 PM. Head there now for more rides.',

(3) Rider notifications: 'Avoid surge! Book your ride 30 min earlier tomorrow.'. Anti-gaming measures:

(1) Surge applies only to NEW requests (pre-scheduled rides locked at original price),

(2) Rider must accept surge before request (can't game by requesting then canceling),

(3) Max cap 3.0× prevents price gouging during emergencies,

(4) Transparent pricing: Show exact breakdown (base + surge) not just total. Edge cases:

(1) Special events: Concert ends → 10K people requesting rides simultaneously → surge spikes to 3.0× but capped, queue system activates (first-come-first-served),

(2) Low supply at night: Only 5 drivers available citywide → surge high but also trigger driver incentives aggressively,

(3) Weather: Rain starts → demand spikes 50% → surge increases, notify off-duty drivers. Monitoring:

(1) Dashboard: Real-time heatmap of surge across city,

(2) Alerts: If surge > 2.5× for > 30 min in area → notify operations team to investigate (event? accident? driver shortage?),

(3) A/B testing: Test different surge algorithms (linear vs exponential) measure impact on:

(a) Driver supply response,

(b) Rider conversion rate,

(c) Total revenue,

(d) User satisfaction. Production metrics: Uber surge pricing increases driver supply by 30-40% during high demand, typical surge duration 15-45 minutes, surge reduces rider wait time by balancing supply/demand, revenue increase during surge but must balance with user retention.

Q
How do you handle geospatial queries efficiently for finding nearby drivers?
A
Redis Geospatial commands with indexing + PostGIS for persistent storage: Redis Geospatial indexing:

(1) Data structure: GEOADD drivers:available {longitude} {latitude} {driver_id} stores driver locations in sorted set with geohash encoding,

(2) Under the hood: Redis uses geohash (52-bit integer encoding of lat/lon) stored in sorted set, enables range queries via ZRANGE operations,

(3) Example: GEOADD drivers:available -122.4194 37.7749 driver_123 adds driver to San Francisco location. Query nearby drivers: GEORADIUS drivers:available -122.4194 37.7749 5 km WITHDIST ASC COUNT 10 →

(1) Finds all drivers within 5km radius of point,

(2) Returns drivers sorted by distance ascending,

(3) Limits to 10 nearest drivers,

(4) Includes distance in results: [(driver_123, 0.8 km), (driver_456, 1.2 km), ...]. Performance:

(1) Time complexity: O(N + log(M)) where N = number of results returned, M = total items in sorted set,

(2) For 1 million drivers, finding 10 nearest within 5km: ~10ms,

(3) Geohash encoding enables quick pruning (only scan nearby cells),

(4) Memory: Each driver entry ~100 bytes (driver_id + geohash), 1M drivers = ~100 MB. Precision levels:

(1) Geohash character length determines precision: 5 chars ≈ 5km × 5km cell, 6 chars ≈ 1.2km × 600m cell, 7 chars ≈ 150m × 150m cell,

(2) Use 6-char precision for driver locations (balance between accuracy and performance). Filtering by vehicle type:

(1) After GEORADIUS, filter results: FOR EACH driver_id in results: SISMEMBER drivers:sedan {driver_id},

(2) Alternative: Maintain separate indexes per vehicle type: GEOADD drivers:available:sedan {lon} {lat} {driver_id}, GEOADD drivers:available:suv {lon} {lat} {driver_id},

(3) Query specific type: GEORADIUS drivers:available:sedan -122.4194 37.7749 5 km. Updating driver locations:

(1) WebSocket receives location ping: {driver_id, lat, lon},

(2) Update geospatial index: GEOADD drivers:available {lon} {lat} {driver_id} (atomic operation, replaces old location),

(3) Time: ~1ms per update,

(4) With 100K drivers updating every 5 seconds = 20K updates/sec = 20K GEOADD operations/sec, Redis handles 100K ops/sec per instance. Removing drivers:

(1) Driver goes offline or accepts ride: GEOREM drivers:available {driver_id},

(2) Atomic removal from sorted set,

(3) O(log(N)) time complexity. Persistent storage with PostGIS:

(1) PostgreSQL with PostGIS extension for geographic data types,

(2) Schema: CREATE TABLE driver_locations (driver_id uuid PRIMARY KEY, location geography(Point, 4326), updated_at timestamp); CREATE INDEX idx_driver_location_gist ON driver_locations USING GIST (location);,

(3) Query: SELECT driver_id, ST_Distance(location, ST_MakePoint(-122.4194, 37.7749)::geography) as distance FROM driver_locations WHERE ST_DWithin(location, ST_MakePoint(-122.4194, 37.7749)::geography, 5000) ORDER BY distance LIMIT 10;,

(4) GIST index enables efficient spatial queries,

(5) Performance: 10-50ms for 1M drivers (slower than Redis but provides persistence and complex queries). Hybrid approach (production):

(1) Redis for real-time queries (sub-10ms latency, ephemeral data with 1-min TTL),

(2) PostGIS for persistent storage + historical analysis,

(3) Background sync: Location Update Service writes to both: Redis (immediate) + Kafka → Consumer → PostgreSQL (async, 1-5 sec lag). Geographic sharding:

(1) Divide world into regions: US-West, US-East, EU, APAC, each region has own Redis instance,

(2) Route requests to nearest region (latency optimization),

(3) Cross-region queries rare (rider in SF won't see driver in NYC). Alternative data structures:

(1) QuadTree: Recursively partition 2D space into 4 quadrants, efficient for sparse data,

(2) R-Tree: Balanced tree for multidimensional data, better for overlapping regions,

(3) S2 Geometry Library (used by Uber): Google's library for spherical geometry, handles edge cases (poles, antimeridian), better accuracy for long distances. Edge cases:

(1) Antimeridian crossing (±180° longitude): Geohash handles correctly, but custom logic needed for queries spanning antimeridian,

(2) Poles (90° latitude): Few drivers at poles, but geohash degenerates, use special handling or different projection,

(3) Very sparse areas: If no drivers within 5km, increase radius to 10km, 20km (exponential backoff) until drivers found or max radius reached. Caching query results:

(1) Frequent queries (e.g., airport, train station): Cache top 10 drivers for location: SET nearby_drivers:{geohash} '[driver_ids]' EX 10 (10 sec TTL),

(2) Invalidate on driver movement,

(3) Reduces load on Redis geospatial queries for hotspots. Monitoring:

(1) Track GEORADIUS query time (p50, p99),

(2) Alert if p99 > 50ms (indicates performance degradation),

(3) Monitor memory usage (sorted set size),

(4) Track cache hit rate for hotspot locations. Production scale: Uber processes millions of geospatial queries per second globally, Redis Cluster with sharding across 100+ nodes, sub-10ms latency for 99th percentile, handles 10M+ driver location updates per minute, PostGIS used for analytics and fraud detection (abnormal GPS patterns).

Q
How do you design the notification system for real-time updates to riders and drivers?
A
Multi-channel notification system with FCM/APN for push + WebSocket for in-app: Architecture: Notification Service consumes Kafka events (ride.matched, trip.started, driver.ride_offered) → routes to appropriate channel (push notification or WebSocket). Push notifications (FCM/APN):

(1) Device token registration: On app login/install → rider/driver registers device token: POST /v1/api/devices with {user_id, device_token, platform: 'ios'/'android'},

(2) Store: INSERT INTO device_tokens (user_id, device_token, platform, active: true, registered_at),

(3) Update on token refresh (iOS rotates tokens periodically). Notification flow:

(1) Event published: Ride Service → Kafka 'ride.matched' topic: {trip_id, rider_id, driver_id, driver_name, vehicle_model, license_plate, eta_min: 5},

(2) Notification Service consumes: Kafka consumer group 'notification-service' processes event,

(3) Fetch device tokens: SELECT device_token, platform FROM device_tokens WHERE user_id={rider_id} AND active=true (user may have multiple devices: iPhone + iPad),

(4) Build payload: {title: 'Driver Assigned!', body: '{driver_name} is on the way in a {vehicle_model}. ETA: 5 min', data: {trip_id, driver_id, action: 'open_trip_screen', deep_link: 'myapp://trip/{trip_id}'}},

(5) Send via FCM (Android): fcm.send({registration_ids: [device_tokens], notification: {title, body}, data: {...}, priority: 'high', time_to_live: 600}),

(6) Send via APN (iOS): apn.send({device_token, payload: {aps: {alert: {title, body}, sound: 'default', badge: 1}, custom_data: {...}}}). Notification types:

(1) Ride matched → rider: 'Driver {name} accepted! ETA 5 min',

(2) Ride matched → driver: 'New ride request from {rider_name}. Pickup at {address}',

(3) Driver arrived → rider: 'Your driver has arrived!',

(4) Trip started → rider: 'Your trip has started. Enjoy your ride!',

(5) Trip completed → rider & driver: 'Trip completed. Fare: $25.50',

(6) Payment processed → rider: 'Payment of $25.50 charged to card ending in 1234',

(7) Surge active → nearby riders: 'High demand in your area. Fares are 1.5× higher.'. Delivery guarantees:

(1) FCM/APN best-effort delivery (not guaranteed),

(2) FCM retry: Up to 4 weeks for devices offline,

(3) APN retry: Up to 1 day for devices offline,

(4) Fallback: If push fails, send SMS for critical notifications (driver assigned, payment failed). WebSocket for in-app real-time:

(1) Rider in app: Maintains WebSocket connection to API Gateway,

(2) Gateway subscribes: Redis Pub/Sub channel user:{rider_id}:notifications,

(3) Notification Service publishes: PUBLISH user:{rider_id}:notifications '{type: ride_matched, data: {...}}',

(4) Gateway forwards to rider via WebSocket: Immediate delivery (<100ms latency),

(5) Rider app handles: {type: 'ride_matched'} → navigate to trip screen, update UI, show driver card. Multi-device synchronization:

(1) User has iPhone + iPad both logged in,

(2) Both devices have WebSocket connections,

(3) Notification sent to both: push notification + WebSocket message,

(4) When one device acknowledges (user taps notification), mark as read: SET notification:{notification_id}:read true,

(5) Other device receives 'notification_read' WebSocket message → dismiss duplicate. Notification preferences:

(1) User settings: Allow push for {ride_updates: true, promotions: false, surge_alerts: true},

(2) Respect preferences: Notification Service checks: SELECT preferences FROM users WHERE user_id={user_id}, skip if category disabled,

(3) Regulatory compliance: GDPR/opt-in requirements for marketing notifications. Rich notifications:

(1) iOS actionable notifications: Buttons on notification (Accept/Decline for driver),

(2) Android heads-up display: Full-screen overlay for critical notifications (driver assigned),

(3) Images: Include driver photo in ride matched notification,

(4) Maps: Show pickup location map thumbnail. Notification analytics:

(1) Track delivery rate: sent / delivered (FCM provides delivery receipts),

(2) Track open rate: notifications delivered / notifications opened (app reports when user taps),

(3) Track action rate: notifications opened / action taken (e.g., accepted ride),

(4) A/B test: Different notification copy, timing, images → optimize engagement. Handling failures:

(1) Invalid token (user uninstalled app): FCM/APN returns 'invalid token' error → UPDATE device_tokens SET active=false WHERE device_token={token},

(2) Transient errors (network timeout): Retry with exponential backoff (1s, 2s, 4s, max 3 retries),

(3) Service unavailable (FCM/APN down): Queue in Kafka (retention 7 days), replay when service restored,

(4) Critical notifications (payment failed): If push fails → send SMS via Twilio as backup. Batching:

(1) Bulk notifications (surge alert to 10K users in area): Batch send 500 tokens per API call,

(2) FCM multicast: Single API call with array of 1000 tokens,

(3) Rate limiting: FCM: 1 million messages/min, APN: no rate limit but throttle sends to avoid overwhelming,

(4) Async processing: Notification Service worker pool (50 threads) sends in parallel. Priority and TTL:

(1) High priority: ride_matched, driver_arrived (immediate delivery, wake device from sleep),

(2) Normal priority: trip_completed, rating_reminder (can wait if device offline),

(3) Time-to-live: ride_matched TTL=10 min (stale after 10 min, driver moved on), promotion TTL=24 hours. Silent notifications:

(1) Background data sync: Send silent push to update trip status without alerting user,

(2) iOS: content-available: 1 flag triggers background app refresh,

(3) Android: data-only message (no notification shown),

(4) Use case: Update driver location, sync ride history, refresh surge map. Localization:

(1) Notification text in user's language: Fetch: SELECT language FROM users WHERE user_id={user_id},

(2) Translate: title_es: '¡Conductor asignado!', title_hi: 'ड्राइवर नियुक्त!',

(3) FCM/APN support localization keys: Send key + parameters, device renders in user's language. Cost optimization:

(1) FCM: Free,

(2) APN: Free (but requires Apple Developer account $99/year),

(3) SMS fallback: $0.01-0.05 per SMS → use sparingly for critical notifications only,

(4) Reduce volume: Don't send promotional push during ride (user focused on trip), batch non-urgent notifications. Production scale: Uber sends 100M+ push notifications daily, delivery rate: 95-99% (devices reachable), open rate: 30-50% depending on notification type, latency: push delivery p50: 1-2 seconds, p99: 5-10 seconds (includes FCM/APN processing), WebSocket: <100ms in-app delivery.

11. Key Numbers to Remember

Scale & Performance
Concurrent Rides — 100K concurrent rides at peak hours globally
Driver Location Updates — Every 3-5 seconds via WebSocket (100K updates/min per 1K drivers)
Matching Latency — <1 second for driver assignment (geo-search + lock acquisition)
Geospatial Query — ~10ms to find 10 nearest drivers from 1M drivers (Redis GEORADIUS)
Locks & Consistency
Zookeeper Lock — Ephemeral node, 30-second session timeout, prevents double assignment
Driver Response Timeout — 30 seconds to accept/decline, auto-release lock if expired
Lock Acquisition Time — <10ms typical (Zookeeper sequential node creation)
Pricing & Surge
Base Fare — $2.50 flat + $1.50/km + $0.30/min (varies by region)
Surge Calculation — Every 60 seconds per geohash area (5km × 5km grid)
Surge Multiplier — 1.0× (normal) to 3.0× (max cap), based on demand/supply ratio
Surge TTL — 2 minutes in Redis, refreshed every 60 seconds
Caching Strategy
Driver Status — Redis TTL 5 min (AVAILABLE/BUSY/OFFLINE), refreshed by heartbeat
Driver Location — Redis TTL 1 min, updated every 3-5 sec via WebSocket
Fare Estimate — Redis TTL 5 min (estimate valid for 5 minutes)
Ride Request — Redis TTL 10 min (expires if no driver found)
Notifications & Messaging
Push Notification Latency — 1-3 seconds (FCM/APN processing + network)
WebSocket In-App Latency — <100ms (direct connection, no intermediary)
Notification Delivery Rate — 95-99% (devices reachable, valid tokens)
SMS Fallback Cost — $0.01-0.05 per SMS (use sparingly for critical notifications)
Key Interview Tips

⚠️
CRITICAL: MUST use Zookeeper distributed locking for driver assignment. Without lock, multiple ride requests can assign same driver simultaneously → double booking → both riders see same driver → terrible UX + revenue loss. Ephemeral nodes ensure automatic lock release on failure.

⭐
Interviewers ALWAYS ask: 'How prevent double assignment?'. Answer: Zookeeper ephemeral sequential nodes. When request R1 tries to lock driver D1 → creates /locks/drivers/D1/request_R1_seq0001, checks if lowest sequence → lock acquired. Concurrent request R2 gets seq0002 → sees seq0001 exists → lock failed → tries next driver.

💡
Redis Geospatial optimization: Use GEORADIUS for sub-10ms proximity search on 1M drivers. Store as sorted set with geohash encoding. Separate indexes per vehicle type (drivers:available:sedan, drivers:available:suv) for faster filtering.

⭐
Must explain: WebSocket vs HTTP polling for location tracking. Polling = 100K riders × 20 req/min = 2M req/min = 33K req/sec overhead. WebSocket = persistent connection, send only when location changes, 100x less traffic, <100ms latency.

⚠️
NEVER trust Redis alone for driver availability. Redis is cache with TTL (ephemeral). Always validate driver status in DB before final assignment: SELECT status FROM drivers WHERE driver_id={id}. Redis provides speed, DB provides truth.

💡
Surge pricing smoothing: Use exponential moving average (new_surge = 0.7×old + 0.3×calculated) prevents sudden jumps. Rider sees gradual increase (1.2× → 1.35× → 1.5×) feels fairer than instant jump (1.0× → 2.0×). Max cap at 3.0× prevents price gouging.

⭐
Interviewers love: 'How calculate ETA dynamically?'. Answer: Every 30 sec query Google Maps Directions API with current driver location → pickup. Response: {distance_remaining: 2.5km, duration: 8 min, route_polyline}. Broadcast ETA update to rider via WebSocket.

⚠️
NEVER skip geofencing. When driver within 50m of pickup: calculate distance(driver_location, pickup_location) using Haversine. If <50m → trigger 'driver_arrived' event → notify rider 'Your driver has arrived!' Push notification + vibrate + sound.

💡
Notification fallback: If FCM/APN push fails (invalid token, device offline), send SMS for CRITICAL notifications (driver assigned, payment failed). SMS costs $0.01-0.05 but ensures delivery. Don't spam SMS for promotions.

⭐
Must mention: Kafka event streaming decouples services. 'driver.location_updated' consumed by: (1) Trip Update Consumer → persists location history to DB, (2) Analytics Service → tracks driver behavior, (3) Fraud Detection → detects GPS spoofing. 100K+ events/sec throughput.

system-design
ride-sharing
uber
ola
lyft
geospatial
Redis-GEORADIUS
Zookeeper-locking
WebSocket-location-tracking
