Food Delivery Application (Zomato/Swiggy/Uber Eats)

"Proximity search (Elasticsearch) → Cart & Order management → Driver matching (geospatial) → Real-time tracking (WebSocket) → Payment integration"

1. Functional Requirements

Feature 1: User registration and login with profile management
Feature 2: List all nearby restaurants based on user location (proximity search)
Feature 3: Search restaurants by name, cuisine, dish with filters (rating, price, delivery time)
Feature 4: Show restaurant menu with items, prices, images, customization options
Feature 5: Add items to cart, modify quantities, apply promo codes, calculate total with taxes
Feature 6: Place order with multiple payment methods (card, wallet, UPI, cash on delivery)
Feature 7: Find nearby delivery partner based on driver location and optimize delivery time
Feature 8: Track order status in real-time (order placed, restaurant accepted, food prepared, driver assigned, picked up, out for delivery, delivered)
Feature 9: Real-time location tracking of delivery partner on map
Feature 10: Order history, ratings & reviews for restaurants and drivers
2. Non-Functional Requirements

Scale
Users — 50M users, 1M restaurants globally
Orders — 10M orders per day, peak 100K orders/hour during lunch/dinner
Concurrent Users — 100K-500K active users during peak hours
Performance
CAP Theorem — Availability >> Consistency (eventual consistency acceptable for search, strong for payments)
Search Latency — < 500ms for restaurant search with filters
Order Placement — < 2s for checkout and payment confirmation
Location Updates — Driver location updated every 10-20s for real-time tracking
Reliability
Uptime — Highly available, application should be highly available based on searching and our application should be highly consistent based on payments and order of food from restaurant
Payment Integrity — Strong consistency for payments (ACID transactions), no double charging or lost payments
Order Consistency — Exactly-once order processing, idempotent order placement
3. Core Entities

Entity 1: User - Customer profile with user_id, name, email, phone, addresses[], payment_methods[], order_history
Entity 2: Restaurant - Restaurant details with restaurant_id, name, location (lat, lng), cuisine, rating, delivery_time, menu[]
Entity 3: FoodMenu - Menu items with item_id, restaurant_id, name, price, image_url, category, customizations[]
Entity 4: Cart - Shopping cart with cart_id, user_id, items[], total_amount, promo_code
Entity 5: Order - Order details with order_id, user_id, restaurant_id, items[], status, payment_status, delivery_partner_id, timestamps
Entity 6: Delivery Partner - Driver with driver_id, name, phone, vehicle, current_location, availability_status, assigned_orders[]
Entity 7: Payment - Payment transaction with payment_id, order_id, amount, method, status, gateway_response
4. API Designing

User Operations
POST /v1/users/register — Register user {name, email, phone, password} → {user_id, token}
GET /v1/users/{userId} — Get user profile with saved addresses, payment methods
POST /v1/users/{userId}/addresses — Add delivery address {street, city, lat, lng, label}
Restaurant & Search
GET /v1/restaurants/nearby — List nearby restaurants {lat, lng, radius} → [restaurants] with distance
GET /v1/restaurants/search — Search {query, lat, lng, cuisine, rating, sortBy} → filtered results
GET /v1/restaurants/{id} — Get restaurant details with menu
GET /v1/restaurants/{id}/menu — Paginated menu items with categories
Cart & Orders
GET /v1/cart — Get current cart items
POST /v1/cart/items — Add item {item_id, quantity, customizations} → updated cart
DELETE /v1/cart/items/{itemId} — Remove item from cart
POST /v1/orders — Place order {cart_id, address_id, payment_method, promo_code} → {order_id, payment_link}
GET /v1/orders/{orderId} — Get order details with status, items, delivery partner info
Tracking & Updates
WS /v1/orders/{orderId}/track — WebSocket for real-time order status and driver location updates
GET /v1/delivery/{orderId}/tracking — Get current delivery partner location and ETA
5. High Level Design

Users → LB + Gateway: Authentication, rate limiting, routing
User Service → User DB (PostgreSQL): User profiles, addresses, preferences
Search Service → Elasticsearch + RestaurantDB: Restaurant search with proximity, filters, full-text
Search Service → S3: Restaurant images, food images served via CDN
Cart Service → Cart DB (Redis): Shopping cart state, session management
Order Service → Order DB (PostgreSQL): Order lifecycle, ACID transactions
Payment Service → Payment Gateway: Payment processing (Stripe/Razorpay), transaction management
Driver Matching Service → Driver DB + Redis: Geospatial matching, availability tracking
Order Service → Kafka: Event-driven order lifecycle (order_placed, restaurant_accepted, driver_assigned, etc.)
Restaurant Service → Kafka: Notifies restaurant when order placed, updates preparation status
Notification Service: Push notifications to user, restaurant, driver for status updates
WebSocket Gateway: Real-time location tracking and order status updates
Order Confirmation Service: Validates order, checks inventory, confirms with restaurant
6. Deep Dive Design (Low Level)

Step 1: User Registration & Login
User sends: POST /v1/users/register with {name: 'John', email: 'john@email.com', phone: '+1234567890', password: 'hashed'}
User Service validates: Email/phone uniqueness, password strength, sends OTP for phone verification
Service creates: User record in PostgreSQL {user_id: UUID, name, email, phone, password_hash (bcrypt), created_at}
Service generates: JWT token with {user_id, role: 'customer', exp: 30 days}
Login: POST /v1/users/login with {email, password} → validates bcrypt hash → returns JWT token
Service initializes: Empty cart in Redis cart:{user_id} = {}
Step 2: Search Nearby Restaurants (Proximity Search)
User requests: GET /v1/restaurants/nearby?lat=12.9716&lng=77.5946&radius=5km
Search Service queries: Elasticsearch with geo_distance filter: { query: { bool: { filter: [ { geo_distance: { distance: '5km', location: { lat: 12.9716, lon: 77.5946 } } }, { term: { is_active: true } } ] } }, sort: [{ _geo_distance: { location: {...}, order: 'asc' } }], size: 50 }
Elasticsearch returns: [{ restaurant_id, name, cuisine, rating, avg_delivery_time, distance: 1.2km }] sorted by distance
Service enriches: Fetch additional metadata from RestaurantDB (menu preview, offers, images from S3/CDN)
Caching: Popular queries cached in Redis search:lat:lng:5km with TTL=5 min
Response: { restaurants: [{id, name, cuisine, rating, distance, estimated_delivery: '30-40 min', image_url}] }
Step 3: Restaurant Search with Filters
User searches: GET /v1/restaurants/search?q=pizza&lat=12.97&lng=77.59&cuisine=Italian&rating>=4.0&sortBy=rating
Search Service builds: Elasticsearch query { query: { bool: { must: [ { match: { menu_items: 'pizza' } } ], filter: [ { geo_distance: {...} }, { term: { cuisine: 'Italian' } }, { range: { rating: { gte: 4.0 } } } ] } }, sort: [{ rating: 'desc' }] }
Query execution: (1) Full-text search on menu_items → 5K candidates, (2) Proximity filter → 500, (3) Cuisine + rating filter → 50 results
Faceted search: Aggregations for filters: 'aggs': { 'cuisines': { terms: { field: 'cuisine' } }, 'avg_price': { stats: { field: 'avg_item_price' } } }
Response includes: Matching restaurants + facets for UI filters (Italian: 50, Chinese: 30, etc.)
Step 4: Menu Display & Cart Management
User views menu: GET /v1/restaurants/{restaurant_id}/menu → fetches from RestaurantDB with categories (Starters, Main Course, Desserts)
Add to cart: POST /v1/cart/items with {item_id: 'burger_123', quantity: 2, customizations: [{type: 'add-on', value: 'extra_cheese'}]}
Cart Service: (1) Validates item exists, restaurant is open, (2) Updates Redis cart:{user_id} HSET items:burger_123 '{quantity: 2, customizations, price: 8.99}', (3) Recalculates total: base_price + customizations + taxes
Cart state in Redis: { items: { burger_123: {quantity: 2, price: 17.98}, fries_456: {quantity: 1, price: 3.99} }, subtotal: 21.97, tax: 2.20, delivery_fee: 2.00, total: 26.17, restaurant_id, TTL: 24h }
Apply promo: POST /v1/cart/promo with {code: 'SAVE20'} → validates in Promo DB → applies 20% discount → updates total
Step 5: Order Placement & Payment
User checkout: POST /v1/orders with {cart_id, address_id, payment_method: 'card', payment_method_id: 'pm_123'}
Order Service validates: (1) Cart not empty, (2) Restaurant open and accepting orders, (3) Address within delivery radius, (4) Items still available (inventory check)
Service creates: Order record in PostgreSQL {order_id: UUID, user_id, restaurant_id, items: JSON, total: 26.17, status: 'PENDING_PAYMENT', created_at} with transaction isolation
Payment flow: (1) Call Payment Service → Stripe/Razorpay createPaymentIntent, (2) Return payment_link to client, (3) Client confirms payment, (4) Webhook POST /webhooks/payment with {order_id, status: 'success'}
On payment success: (1) Update order status='CONFIRMED', payment_status='PAID', (2) Publish to Kafka 'order.placed' topic with order details, (3) Clear cart from Redis, (4) Send notifications to user + restaurant
Step 6: Restaurant Acceptance Flow
Restaurant Service consumes: Kafka 'order.placed' event
Service sends: Push notification to restaurant app 'New order #12345 - ₹26.17'
Restaurant accepts: POST /v1/restaurants/orders/{order_id}/accept with estimated_prep_time=20min
Service updates: Order status='RESTAURANT_ACCEPTED', prep_completion_time=now()+20min
Service publishes: Kafka 'order.restaurant_accepted' event
Timeout handling: If restaurant doesn't respond in 5 min, auto-reject order, refund payment, notify user, offer alternative restaurants
Step 7: Driver Matching & Assignment
Driver Matching Service consumes: Kafka 'order.restaurant_accepted' event
Service queries: Redis GEORADIUS drivers:online {restaurant_lng} {restaurant_lat} 5 km WITHDIST ASC to find nearby available drivers
Filtering: (1) Status='online' and available=true, (2) Not currently on delivery, (3) Vehicle type suitable (bike for small orders, car for large)
Scoring: score = (1/distance) × 0.5 + rating × 0.3 + acceptance_rate × 0.2, select top driver
Assignment: (1) Acquire distributed lock SETNX lock:driver:{driver_id} {order_id} EX 60, (2) If acquired, assign order to driver, publish to Kafka 'driver.assigned', (3) If driver rejects, release lock, try next driver
Notification: Push to driver app 'New delivery request: Pickup from Restaurant X, deliver to Location Y, earn ₹50'
Driver confirms: POST /v1/drivers/orders/{order_id}/accept → update order status='DRIVER_ASSIGNED', driver_id={driver_id}
Step 8: Real-Time Location Tracking
Driver app: Updates location every 10-20s via POST /v1/drivers/location with {driver_id, lat, lng, timestamp}
Update Location Service: (1) Updates Redis GEOADD drivers:online {lng} {lat} {driver_id}, (2) If driver on active delivery, publish to Kafka 'driver.location.update' with {driver_id, order_id, location}
Consumer Service: (1) Consumes location updates, (2) Calculates ETA using Google Maps Distance Matrix API, (3) Publishes to Redis Pub/Sub channel location:{order_id}
User tracking: (1) WebSocket connection WS /v1/orders/{order_id}/track, (2) WebSocket Manager subscribes to Redis channel location:{order_id}, (3) Forwards location updates to user's WebSocket: {driver_location: {lat, lng}, eta: '8 min', distance_remaining: '1.2 km'}
Optimization: Batch location updates every 10s instead of real-time (10-20s is sufficient for delivery tracking)
Step 9: Order Status Updates & Lifecycle
Status transitions: PENDING_PAYMENT → CONFIRMED → RESTAURANT_ACCEPTED → FOOD_PREPARING → DRIVER_ASSIGNED → DRIVER_AT_RESTAURANT → PICKED_UP → OUT_FOR_DELIVERY → DELIVERED
Driver picks up: POST /v1/drivers/orders/{order_id}/pickup → status='PICKED_UP', pickup_time=now(), publish Kafka event
Driver delivers: POST /v1/drivers/orders/{order_id}/deliver → status='DELIVERED', delivered_time=now()
Order Status Service: Consumes all Kafka events, updates Order DB, publishes to WebSocket for real-time UI updates
Notification flow: Each status change → Notification Service sends push to user ('Your food is being prepared', 'Driver is on the way', 'Food delivered')
Timeout monitoring: Background job checks if order stuck in any state >threshold time (e.g., FOOD_PREPARING >60 min), escalates to support
Step 10: Post-Delivery Rating & Review
User rates: POST /v1/orders/{order_id}/rating with {restaurant_rating: 5, driver_rating: 4, review: 'Great food!', tags: ['quick_delivery', 'well_packed']}
Service stores: Rating in separate Ratings table {rating_id, order_id, user_id, restaurant_rating, driver_rating, review, timestamp}
Aggregation: Background job updates: (1) Restaurant avg_rating = SELECT AVG(restaurant_rating) FROM ratings WHERE restaurant_id={id}, (2) Driver avg_rating similarly, (3) Updates Restaurant and Driver tables, (4) Reindexes in Elasticsearch for search ranking
Review moderation: ML service scans review for abuse/spam, flags for manual review if needed
Driver sees rating: Displayed in driver app for transparency, low ratings (<4.0 avg) trigger retraining or suspension
7. Client-Side Components

Component 1: Location Picker - Autocomplete address search with Google Places API, GPS location detection
Component 2: Restaurant List - Infinite scroll with lazy loading, filters (cuisine, rating, delivery time)
Component 3: Menu Browser - Categorized menu with search, item customization modal (add-ons, special instructions)
Component 4: Cart Widget - Persistent cart icon with item count, cart summary with price breakdown
Component 5: Checkout Flow - Address selection, payment method, promo code input, order confirmation
Component 6: Order Tracking - Real-time map with driver location, status timeline, ETA countdown
Component 7: WebSocket Manager - Maintains connection, handles reconnection, receives location and status updates
8. Database Schema Details

Users (PostgreSQL)
user_id — uuid PRIMARY KEY
name — varchar(255)
email — varchar(255) UNIQUE
phone — varchar(15) UNIQUE
password_hash — varchar(255) (bcrypt)
addresses — jsonb [{street, city, lat, lng, label: 'home'}]
payment_methods — jsonb [{type: 'card', last4: '1234', is_default: true}]
created_at — timestamp
Restaurants (PostgreSQL + Elasticsearch)
restaurant_id — uuid PRIMARY KEY
name — varchar(255)
location — geography(Point, 4326) (PostGIS) or geo_point (Elasticsearch)
cuisine — varchar(100)[] (array: ['Italian', 'Pizza'])
rating — decimal(2,1) (4.5 stars)
avg_delivery_time — integer (minutes)
is_active — boolean (open/closed)
menu_items — jsonb or separate MenuItems table
image_url — varchar(500) (S3/CDN link)
MenuItems (PostgreSQL)
item_id — uuid PRIMARY KEY
restaurant_id — uuid FK → Restaurants
name — varchar(255)
category — varchar(100) (Starters, Main Course)
price — decimal(10,2)
image_url — varchar(500)
customizations — jsonb [{type: 'size', options: ['Small', 'Large']}]
is_available — boolean
Orders (PostgreSQL - ACID critical)
order_id — uuid PRIMARY KEY
user_id — uuid FK → Users, INDEXED
restaurant_id — uuid FK → Restaurants
driver_id — uuid FK → Drivers (nullable until assigned)
items — jsonb [{item_id, name, quantity, price, customizations}]
delivery_address — jsonb {street, city, lat, lng}
status — enum (PENDING_PAYMENT, CONFIRMED, RESTAURANT_ACCEPTED, FOOD_PREPARING, DRIVER_ASSIGNED, PICKED_UP, OUT_FOR_DELIVERY, DELIVERED, CANCELLED)
payment_status — enum (PENDING, PAID, FAILED, REFUNDED)
subtotal — decimal(10,2)
delivery_fee — decimal(10,2)
tax — decimal(10,2)
discount — decimal(10,2)
total — decimal(10,2)
promo_code — varchar(50)
created_at — timestamp INDEXED
confirmed_at — timestamp
delivered_at — timestamp
Drivers (PostgreSQL)
driver_id — uuid PRIMARY KEY
name — varchar(255)
phone — varchar(15)
vehicle_type — enum (bike, car, scooter)
vehicle_number — varchar(20)
current_location — geography(Point, 4326) (updated periodically)
status — enum (online, offline, on_delivery)
avg_rating — decimal(2,1)
total_deliveries — integer
acceptance_rate — decimal(3,2) (0.85 = 85%)
Cart (Redis - session data)
cart:{user_id} — HASH {restaurant_id, items: {item_id: {quantity, price, customizations}}, subtotal, total, updated_at}
TTL — 24 hours (expire inactive carts)
Driver Location (Redis Geospatial)
drivers:online — GEORADIUS key with {lng, lat, driver_id}
driver:{driver_id}:location — HASH {lat, lng, timestamp, heading, speed}
lock:driver:{driver_id} — STRING {order_id} with EX 60 (distributed lock for assignment)
Elasticsearch - Restaurant Search Index
restaurant_id — keyword
name — text with standard analyzer
location — geo_point
cuisine — keyword (exact match for filters)
menu_items — text (full-text search on dish names)
rating — float
avg_delivery_time — integer
is_active — boolean
9. Key Mechanisms

Idempotent Order Placement
Problem: User clicks 'Place Order' multiple times due to slow network → risk of duplicate orders and double charging
Solution: Idempotency key approach
Implementation: (1) Client generates UUID idempotency_key before submit, (2) Client sends POST /v1/orders with {cart_id, idempotency_key: '550e8400-e29b-41d4-a716-446655440000'}, (3) Order Service checks if order with this idempotency_key exists: SELECT * FROM orders WHERE idempotency_key = {key}, (4) If exists, return existing order_id (idempotent response), (5) If not exists, create order with BEGIN TRANSACTION; INSERT INTO orders (..., idempotency_key) ...; COMMIT;, (6) Idempotency key expires after 24 hours
Database constraint: UNIQUE INDEX on idempotency_key column ensures atomicity
Driver Matching Algorithm
Inputs: Restaurant location (pickup), delivery address (drop-off), order value, current time
Step 1: Find candidates - Redis GEORADIUS drivers:online {restaurant_lng} {restaurant_lat} 5 km → returns [driver_1: 0.8km, driver_2: 1.5km, driver_3: 2.3km]
Step 2: Filter - status='online', available=true, not on another delivery, vehicle suitable for order size
Step 3: Score each driver: score = (proximity_score × 0.4) + (rating_score × 0.3) + (acceptance_rate × 0.2) + (idle_time × 0.1)
Proximity: 1 / (1 + distance_km), closer = higher score
Rating: driver_rating / 5.0 (normalize to 0-1)
Acceptance: acceptance_rate (historical accept/reject ratio)
Idle: Minutes since last delivery (prefer busy drivers to keep them engaged)
Step 4: Select top driver, attempt assignment with lock, if rejected cascade to next
Optimization: Pre-compute driver availability zones, update every 5 min
10. Scaling & Optimization

Technique 1: Elasticsearch Sharding - Restaurant index sharded by location (geo_hash prefix), enables parallel queries across regions
Technique 2: Redis Caching - Cache popular restaurant queries (search:lat:lng:5km) with TTL=5 min, serves 70% of searches from cache
Technique 3: CDN for Images - Restaurant and food images served via CloudFront, reduces origin load by 95%, faster global delivery
Technique 4: Database Read Replicas - PostgreSQL replicas for read queries (restaurant details, order history), writes to primary only
Technique 5: Cart in Redis - Fast cart operations (add/remove items), prevents database overload, TTL=24h auto-cleanup
Technique 6: Kafka for Event Streaming - Decouple order lifecycle events, enables async processing, horizontal scaling of consumers
Technique 7: WebSocket Connection Pooling - Gateway maintains 50K connections per instance, load balanced across multiple instances
Technique 8: Geo-Sharding - Partition restaurants and orders by region (US-West, US-East, India, etc.), reduces cross-region queries
Technique 9: Driver Location Batching - Update Redis every 10-20s instead of real-time, reduces write load by 80%
Technique 10: Lazy Menu Loading - Load only first 20 menu items, paginate on scroll, reduces initial payload from 500KB to 50KB
Technique 11: API Rate Limiting - 100 requests/min per user prevents abuse, protects against DDoS
Technique 12: Connection Pooling - API servers maintain 100 DB connections, prevents connection exhaustion
11. Common Interview Questions

Q
How do you search for nearby restaurants efficiently?
A
Elasticsearch with geo_distance query:

(1) Index restaurants with geo_point mapping: PUT /restaurants { mappings: { properties: { location: { type: 'geo_point' } } } },

(2) Query: POST /restaurants/_search { query: { bool: { filter: [ { geo_distance: { distance: '5km', location: { lat: 12.97, lon: 77.59 } } }, { term: { is_active: true } } ] } }, sort: [{ _geo_distance: { location: {...}, order: 'asc' } }], size: 50 },

(3) Elasticsearch uses BKD tree internally for spatial index, O(log n) queries,

(4) Returns restaurants sorted by distance in ~50ms for millions of docs. Caching: Popular queries cached in Redis search:{lat}:{lng}:{radius} with TTL=5 min, serves 70% from cache <5ms. Alternative: PostgreSQL PostGIS with ST_DWithin for exact distance, Redis GEORADIUS for real-time driver locations. Hybrid: Elasticsearch for search (complex filters), Redis for hot cache, PostgreSQL for source of truth.

Q
How do you implement cart functionality with fast add/remove operations?
A
Redis-based cart with session management:

(1) Schema: HASH key cart:{user_id} with fields {restaurant_id, items: {item_id: {quantity, price, customizations}}, subtotal, tax, total, updated_at},

(2) Add item: HSET cart:{user_id} items:item_123 '{quantity: 2, price: 17.98, customizations: [extra_cheese]}', then recalculate total using HGETALL cart:{user_id}, update subtotal/total fields,

(3) Remove item: HDEL cart:{user_id} items:item_123, recalculate total,

(4) Get cart: HGETALL cart:{user_id} returns entire cart in <1ms,

(5) TTL: EXPIRE cart:{user_id} 86400 (24 hours), auto-cleanup inactive carts. Advantages:

(1) Fast operations ~1ms vs 50ms for database,

(2) Scales to millions of concurrent users,

(3) Reduces DB load,

(4) Session state persists across client restarts. Persistence: On order placement, serialize cart to Order.items JSONB column in PostgreSQL for audit trail, then DEL cart:{user_id}. Edge case: Cart from different restaurant → prompt user 'Clear existing cart?' before adding items from new restaurant.

Q
How do you ensure exactly-once order processing and prevent double charging?
A
Multi-layer idempotency:

(1) Client-side idempotency key: Client generates UUID before submit, includes in request header X-Idempotency-Key: {uuid},

(2) Database constraint: Orders table has UNIQUE INDEX on idempotency_key column,

(3) Order creation: BEGIN TRANSACTION; SELECT * FROM orders WHERE idempotency_key = {key} FOR UPDATE; If found: ROLLBACK; return existing order_id (HTTP 200, idempotent). If not found: INSERT INTO orders (..., idempotency_key) VALUES (...); COMMIT; return new order_id (HTTP 201),

(4) Payment idempotency: Payment gateway (Stripe/Razorpay) uses same idempotency_key, prevents double charging even if retry,

(5) Key expiry: Idempotency keys valid for 24 hours, then removed. Example: User clicks 'Place Order' twice within 2s → Request 1 creates order, Request 2 finds existing order by idempotency_key, returns same order_id → user charged once. Race condition: Two concurrent requests with same key → database UNIQUE constraint ensures only one INSERT succeeds, other gets constraint violation → retry with SELECT. Alternative: Distributed lock with Redis SETNX before order creation, but database constraint simpler.

Q
How do you match drivers to orders efficiently and prevent double assignment?
A
Geospatial matching with distributed locks:

(1) Trigger: Kafka 'order.restaurant_accepted' event consumed by Driver Matching Service,

(2) Find candidates: Redis GEORADIUS drivers:online {restaurant_lng} {restaurant_lat} 5 km WITHDIST ASC returns nearby drivers sorted by distance,

(3) Filter: status='online' AND available=true AND current_orders=0, vehicle_type suitable,

(4) Scoring: score = (1/distance_km) × 0.4 + (rating/5) × 0.3 + acceptance_rate × 0.2 + (idle_time/60) × 0.1, select highest score,

(5) Lock acquisition: Redis SETNX lock:driver:{driver_id} {order_id} EX 60, if returns 1 (success) proceed, if 0 (already locked) try next driver,

(6) Send request: Push notification to driver 'New order: ₹50 earnings', driver has 30s to accept,

(7) Acceptance: Driver accepts → update order.driver_id, status='DRIVER_ASSIGNED', release lock,

(8) Rejection/timeout: DEL lock:driver:{driver_id}, cascade to next driver in queue. Double assignment prevention: Lock ensures only one order can claim driver at a time, even if two orders match same driver concurrently. Example: Order O1 and O2 both match Driver D1 → O1 acquires lock first → O2's SETNX fails → O2 tries D2 instead → no conflict. Alternative: Database pessimistic locking with SELECT ... FOR UPDATE on drivers table, but slower than Redis.

Q
How do you implement real-time order tracking with driver location updates?
A
WebSocket + Redis Pub/Sub architecture:

(1) Driver location updates: Driver app sends POST /v1/drivers/location every 10-20s with {driver_id, lat, lng, timestamp},

(2) Update Location Service:

(a) Updates Redis GEOADD drivers:online {lng} {lat} {driver_id},

(b) If driver on active delivery, publish to Kafka 'driver.location.update' topic,

(3) Location Consumer: Consumes Kafka events, publishes to Redis Pub/Sub channel location:{order_id} with {driver_location, eta, distance_remaining},

(4) WebSocket Gateway: User connects WS /v1/orders/{order_id}/track, gateway subscribes to Redis Pub/Sub location:{order_id},

(5) Real-time push: When new location published to Redis channel, WebSocket Gateway forwards to user's WebSocket connection in <100ms,

(6) Client renders: Update driver marker on map, recalculate ETA, display distance. ETA calculation: Call Google Maps Distance Matrix API with {origin: driver_location, destination: delivery_address, mode: 'driving'}, returns duration considering traffic. Optimization: Batch location updates every 10s instead of every update, send only when distance changed >50m. Scaling: 100K active deliveries × 1 update/10s = 10K updates/sec, Redis Pub/Sub handles 100K msg/sec. Fallback: If WebSocket fails, client falls back to HTTP polling GET /v1/orders/{order_id}/location every 10s. Example: Driver moves from Point A to B → Location Service publishes to Redis → WebSocket Gateway forwards to user → map updates driver position → ETA recalculated '8 min remaining'.

Q
How do you handle order cancellations and refunds?
A
Multi-stage cancellation policy:

(1) Before restaurant acceptance: User can cancel free, POST /v1/orders/{order_id}/cancel → status='CANCELLED', full refund initiated,

(2) After restaurant acceptance: Cancellation fee applies (₹20-50 depending on time), partial refund = total - cancellation_fee,

(3) After driver assignment: Higher fee (₹50-100), compensates driver for time,

(4) Refund processing: Call Payment Service → payment_gateway.refund(payment_id, amount), status='REFUNDING', webhook confirms → status='REFUNDED',

(5) Notification: Push to user 'Order cancelled, ₹X refunded', email with refund receipt. Database updates: UPDATE orders SET status='CANCELLED', cancelled_by='user', cancelled_at=now(), refund_amount={amount}, refund_status='PROCESSING' WHERE order_id={id}. Kafka event: Publish 'order.cancelled' → Restaurant Service notifies restaurant, Driver Service releases driver if assigned. Edge cases:

(1) Food already prepared: No refund, but offer credit for future order,

(2) Driver already picked up: Cannot cancel, must receive delivery,

(3) Payment failed originally: No refund needed, just mark cancelled. Abuse prevention: Track user cancellation_rate, if >30% in last 10 orders, add 5 min waiting period before allowing next order. Example: User cancels 2 min after ordering → restaurant not yet accepted → full refund ₹26.17 → refund appears in wallet/card in 5-7 days.

Q
What's your strategy for handling peak traffic during lunch/dinner hours?
A
Multi-tier scaling strategy:

(1) Auto-scaling: Kubernetes HPA scales API servers based on CPU/memory (threshold 70%), pre-warm 30 min before peak (11:30 AM, 6:30 PM), scale from 20 to 100 instances,

(2) Database connection pooling: Maintain 100 connections per API server (10K total), prevents connection exhaustion, use pgBouncer for connection management,

(3) Read replicas: Route read queries (restaurant search, order history) to 5 PostgreSQL replicas, writes to primary only,

(4) Redis cluster: Shard cart data across 10 Redis nodes using hash(user_id), each node handles 10K concurrent users,

(5) Kafka buffering: Order placement events buffered in Kafka, consumers process at steady rate even if spike in orders, prevents overwhelming downstream services,

(6) CDN caching: Restaurant images, menu items cached at edge, reduces origin load by 95%,

(7) API rate limiting: 100 req/min per user with token bucket algorithm, prevents single user from overwhelming system,

(8) Database query optimization: Materialized views for popular queries (top restaurants per area), refresh every 5 min,

(9) Async processing: Non-critical tasks (email receipts, analytics) processed async via Kafka, doesn't block order flow. Peak load: 100K orders/hour = 1.67K orders/min = 28 orders/sec. With scaling: 100 API instances × 100 orders/sec capacity = 10K orders/sec headroom. Monitoring: Prometheus + Grafana for real-time metrics, alerts if latency >500ms or error rate >1%, auto-scale triggers.

Q
How do you ensure data consistency across multiple microservices?
A
Event-driven architecture with saga pattern:

(1) Order Service is orchestrator, manages distributed transaction,

(2) Order placement saga: Step 1: Create order in Order DB (PENDING_PAYMENT), Step 2: Call Payment Service → if success proceed, if fail rollback (mark order FAILED), Step 3: Publish 'order.paid' to Kafka, Step 4: Restaurant Service updates inventory → if out of stock, compensating transaction (refund, cancel order), Step 5: Driver Matching assigns driver → if no drivers available, retry with backoff or cancel order.

(3) Eventual consistency: Each service has its own database (database-per-service pattern), updates propagated via Kafka events,

(4) Compensating transactions: If downstream step fails, previous steps reversed via 'order.cancelled' event → Payment Service refunds, Restaurant Service restores inventory.

(5) Idempotency: All event handlers idempotent (use event_id to deduplicate), prevents duplicate processing if event replayed.

(6) Outbox pattern: Order Service writes order + event to same database in single transaction, background job publishes events to Kafka → ensures order creation and event publishing are atomic. Example: User orders last pizza → Order created → Payment succeeds → Inventory check fails (out of stock) → Compensating transaction: refund payment, cancel order, notify user 'Item unavailable, refund processed'. Data consistency levels:

(1) Strong: Payments, inventory (use ACID transactions),

(2) Eventual: Search index, analytics (sync async via Kafka). Trade-off: Strong consistency = slower, limited scalability; Eventual = faster, more scalable, acceptable for most use cases.

Q
How do you implement search with multiple filters (cuisine, rating, delivery time)?
A
Elasticsearch with compound boolean query:

(1) Index mapping: PUT /restaurants { mappings: { properties: { name: {type: 'text'}, location: {type: 'geo_point'}, cuisine: {type: 'keyword'}, rating: {type: 'float'}, avg_delivery_time: {type: 'integer'}, price_range: {type: 'keyword'}, is_active: {type: 'boolean'} } } },

(2) Search query: POST /restaurants/_search { query: { bool: { must: [ { match: { name: 'pizza' } } ], filter: [ { geo_distance: { distance: '5km', location: { lat: 12.97, lon: 77.59 } } }, { terms: { cuisine: ['Italian', 'American'] } }, { range: { rating: { gte: 4.0 } } }, { range: { avg_delivery_time: { lte: 45 } } }, { term: { is_active: true } } ] } }, sort: [{ rating: 'desc' }], aggs: { cuisine_facets: { terms: { field: 'cuisine', size: 20 } }, price_facets: { terms: { field: 'price_range' } } }, size: 50 },

(3) Query execution:

(a) Full-text match on 'pizza' → 10K candidates,

(b) Proximity filter → 2K,

(c) Cuisine filter → 500,

(d) Rating + delivery time → 100 results,

(4) Aggregations: Returns facet counts {Italian: 50, Chinese: 30, Mexican: 20} for UI filters. Sorting:

(1) Default: Sort by distance (closest first),

(2) Rating: Sort by rating DESC,

(3) Delivery time: Sort by avg_delivery_time ASC,

(4) Popularity: Sort by total_orders DESC. Pagination: Use from/size for first 10K results, search_after for deep pagination (>10K). Performance: ~50ms p95 for 100M restaurants with 5 filters. Caching: Cache popular filter combinations in Redis with TTL=5 min. Example: User searches 'pizza' near SF, filters: Italian, rating ≥4, delivery ≤45 min → Elasticsearch returns 50 restaurants + facets → user sees results with applied filters + counts for refinement.

Q
How do you calculate delivery ETA accurately?
A
Multi-factor ETA prediction:

(1) Initial estimate: When order placed, estimate = restaurant_prep_time + travel_time_to_restaurant + travel_time_to_customer,

(2) Restaurant prep time: Use historical avg_prep_time from restaurant, adjust for current load (busy hours +10 min),

(3) Travel time: Call Google Maps Distance Matrix API with {origin: driver_current_location, destination: restaurant_location, mode: 'driving', departure_time: 'now'}, returns duration considering real-time traffic,

(4) Dynamic updates: As order progresses, recalculate ETA every 1-2 min, formula: ETA = (distance_remaining / driver_speed) + traffic_adjustment,

(5) Machine learning: Train model on historical data (features: time_of_day, day_of_week, weather, distance, restaurant, driver), predict ETA more accurately than static calculation,

(6) Traffic data: Integrate with Google Maps Traffic API, adjust for congestion (red roads +50% time),

(7) Driver speed: Calculate from last 5 location updates, driver_speed = distance / time, use for real-time ETA. Display: Show range 'Arrives in 25-35 min' instead of exact '30 min' to manage expectations. Update frequency: Recalculate every 60s during preparation, every 10s during delivery. Accuracy target: ±3 min from actual delivery time. Example: Order placed 12:00 PM → initial ETA: prep_time 20 min + travel 15 min = 35 min (arrive 12:35 PM) → at 12:15 driver assigned, recalc: travel 12 min = arrive 12:32 PM → at 12:25 driver picked up, recalc with actual speed and traffic: 10 min = arrive 12:35 PM → actual delivery 12:33 PM (within 2 min of estimate).

12. Key Numbers to Remember

Scale & Volume
Total Users — 50M registered users globally
Restaurants — 1M restaurants, 10M menu items
Daily Orders — 10M orders/day, peak 100K orders/hour
Concurrent Users — 100K-500K during lunch/dinner hours
Active Drivers — 100K-500K drivers online during peak
Latency Requirements
Restaurant Search — < 500ms with proximity + filters
Cart Operations — < 100ms (Redis add/remove items)
Order Placement — < 2s for checkout to confirmation
Location Updates — 10-20s interval for driver tracking
WebSocket Push — < 100ms for real-time status updates
Search & Matching
Search Radius — 5km default, max 20km for restaurants
Driver Matching Radius — 5km from restaurant, expand to 10km if no drivers
Elasticsearch Query — ~50ms for 100M documents with geo + filters
Redis GEORADIUS — <10ms for finding nearby drivers
Caching & Storage
Redis Cart TTL — 24 hours (auto-cleanup inactive)
Search Cache TTL — 5 minutes for popular queries
Driver Location Update — Every 10-20s during active delivery
Image CDN Cache — 30 days, 95% hit rate
Payment & Pricing
Average Order Value — ₹300-500 ($10-15)
Delivery Fee — ₹20-50 based on distance
Platform Commission — 20-30% of order value from restaurant
Driver Earnings — ₹30-100 per delivery
Cancellation Fee — ₹20-100 based on order stage
Timeouts & SLAs
Restaurant Acceptance — 5 min timeout, auto-reject if no response
Driver Response — 30s to accept/reject delivery request
Idempotency Key — Valid for 24 hours
Avg Delivery Time — 30-45 min (prep 20-30 min + delivery 10-15 min)
Key Interview Tips

⚠️
NEVER allow duplicate orders. Use idempotency keys (client-generated UUID) with UNIQUE database constraint. Without this, user clicking 'Place Order' twice = double charge and two food deliveries.

⭐
Interviewers ALWAYS ask: 'How to find nearby restaurants?'. Answer: Elasticsearch geo_distance query for proximity + filters + text search. Cache popular queries in Redis (TTL=5 min). Alternative: PostgreSQL PostGIS for exact distance, Redis GEORADIUS for real-time drivers.

💡
Key optimization: Store cart in Redis, not database. Operations are 50x faster (<1ms vs 50ms), scales to millions of users, auto-expires inactive carts after 24h. Serialize to PostgreSQL only on order placement.

⭐
Must mention: Distributed lock for driver assignment. Redis SETNX lock:driver:{id} prevents double assignment when two orders match same driver concurrently. Lock expires in 60s to prevent deadlock.

⚠️
NEVER update driver location in real-time (every second). Use 10-20s interval to reduce load. 100K drivers × 1 update/sec = 100K writes/sec vs 100K drivers × 1 update/10s = 10K writes/sec (10x reduction).

💡
Event-driven with Kafka: Order lifecycle events (placed, accepted, assigned, delivered) published to Kafka. Enables async processing, decouples services, supports replay for debugging. All status updates flow through Kafka.

⭐
Interviewers love: 'Real-time tracking implementation'. Answer: Driver updates location → Kafka → Redis Pub/Sub → WebSocket Gateway → User's WebSocket. Alternative: HTTP polling every 10s as fallback. ETA from Google Maps API with traffic.

⚠️
NEVER use strong consistency for search. Elasticsearch eventual consistency (~1s refresh) acceptable. Use strong consistency (ACID) only for payments and order placement. Trade-off: availability vs consistency.

💡
Multi-tier caching: (1) Redis for hot queries (70% hit rate, <5ms), (2) Elasticsearch for complex search (~50ms), (3) PostgreSQL for source of truth (~100ms). Serves 70% from cache, 95% from ES, 5% from DB.

⭐
Must explain: Driver matching algorithm. (1) Find candidates via GEORADIUS within 5km, (2) Filter (online, available, suitable vehicle), (3) Score: proximity 40% + rating 30% + acceptance_rate 20% + idle_time 10%, (4) Assign to highest score with distributed lock.