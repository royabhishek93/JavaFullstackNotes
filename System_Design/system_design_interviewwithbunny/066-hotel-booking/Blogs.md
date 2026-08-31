Hotel Booking System (Airbnb/MakeMyTrip/Bookings.com)

"Search hotels (Elasticsearch geo) → Check availability (Redis lock) → Book room (distributed lock) → Payment (idempotency) → Confirmation (Kafka events)"

1. Functional Requirements

Feature 1: User should be able to create account in our application (register/login/logout/update profile)
Feature 2: Search for hotels based on name, location, dates with filters (price, rating, amenities)
Feature 3: View hotel details with available rooms, prices, photos, reviews
Feature 4: Make the payment to confirm booking for selected room and dates
Feature 5: View past and future booking details on profile with ability to cancel/modify bookings
2. Non-Functional Requirements

Scale
Users — 50M users, 1M hotels globally
Daily Searches — 100M searches/day, 1M bookings/day
Rooms — 10M+ hotel rooms across all properties
Performance & Availability
CAP Theorem — Availability >>> consistency. Application should be highly available based on searching and system should be highly consistent based on booking. No two users should be allowed to book the same room/hotel on same time frames
Search Latency — < 500ms for hotel search with location, dates, filters
Booking Consistency — Strong consistency - prevent double booking using distributed locks
Payment Reliability — Exactly-once semantics with idempotency, no double charging
3. Core Entities (Identify Core Entity)

Entity 1: User - Customer with user_id, name, email, phone, password, preferences, booking_history[]
Entity 2: Hotel - Property with hotel_id, name, location (lat, lng), address, rating, amenities[], images[], description
Entity 3: Room - Room inventory with room_id, hotel_id, room_type, capacity, price, amenities[], availability calendar
Entity 4: Booking - Reservation with booking_id, user_id, hotel_id, room_id, check_in_date, check_out_date, status, amount, payment_id
4. API Designing

User Management
POST /v1/users/register — Register user {name, email, password} → {userId, token} (login/logout/update)
Hotel Search & Details
GET /v1/hotels/search — Search hotels {location, checkIn, checkOut, guests} → List<Hotel(partial)> with pagination
GET /v1/hotels/{hotelId} — Get hotel details → HotelDetails with rooms, reviews, images
GET /v1/hotels/room/{hotelId}/{dates} — Get available rooms for specific dates → List<Room> with pricing and availability
Booking Management
POST /v1/booking/roomId — Create booking {roomId, userId, dates} → Return Booking ID
PUT /v1/booking/bookingId — Modify or cancel booking → Updated booking status
GET /v1/bookings — Get user bookings {header: userId} → List of bookings (past & future)
5. High Level Design

Users → LB + API Gateway: Authentication, authorization, rate limiting, round robin routing
User Service → User DB (PostgreSQL): User profiles, authentication, preferences
Search Service → Elasticsearch: Hotel search with geo queries, filters (price, rating, amenities)
Hotel DB (PostgreSQL): Hotel metadata, room types, pricing, images (S3/CDN references)
Review Service → Review DB: Hotel and room reviews with ratings
Booking Service → Booking DB + Redis Lock: Room availability check, booking creation with distributed locks
Room Availability Service: Checks availability if room is available, updates availability table once booking is done
Payment Service → Payment Gateway: Payment processing with acknowledgement, idempotency handling
Kafka: Event streaming for booking.created, booking.confirmed, booking.cancelled, payment.success events
Notification Service: Consumes Kafka events, sends email/SMS/push notifications to users
6. Deep Dive Design (Low Level)

Step 1: User Registration & Authentication
User sends: POST /v1/users/register with {name: 'John', email: 'john@email.com', password: 'pass123'}
User Service validates: Email uniqueness via SELECT * FROM users WHERE email = {email}
Service creates: User record in PostgreSQL {user_id: UUID, name, email, password_hash: bcrypt(password), created_at}
Service generates: JWT token with {user_id, email, exp: 7 days}, stores refresh token in Redis with TTL
Response: {user_id, token, refresh_token}
Login: POST /v1/users/login with {email, password} → validates bcrypt hash → returns JWT
Step 2: Hotel Search (Elasticsearch Geo + Filters)
User searches: GET /v1/hotels/search?location=London&checkIn=2025-02-01&checkOut=2025-02-05&guests=2&priceMax=200
Search Service geocodes: Location 'London' → (51.5074, -0.1278) using Google Geocoding API or internal cache
Alternative: If user provides lat/lng directly, skip geocoding
Service queries Elasticsearch: { 'query': { 'bool': { 'filter': [ { 'geo_distance': { 'distance': '20km', 'location': { 'lat': 51.5074, 'lon': -0.1278 } } }, { 'range': { 'price_per_night': { 'lte': 200 } } }, { 'term': { 'min_guests': { 'lte': 2 } } } ] } }, 'sort': [ { '_geo_distance': { 'location': {...}, 'order': 'asc' } } ], 'size': 50 }
Note: Elasticsearch query does NOT check date availability (too complex), returns hotels matching location + filters only
Service fetches: Partial hotel data {hotel_id, name, location, price_range, rating, image_url} from ES
CDC (Change Data Capture): Hotel DB → Kafka → Elasticsearch indexer keeps ES in sync
For availability: Client calls separate API GET /v1/hotels/{hotelId}/availability?checkIn=...&checkOut=... after selecting hotel
Caching: Popular location searches cached in Redis with TTL=10 min (key: hash(location, filters))
Step 3: Hotel Details & Room Availability
User selects hotel: GET /v1/hotels/{hotel_id} to view details
Service fetches: Full hotel details from Hotel DB {hotel_id, name, description, amenities, images[], address, geo_pos (lat, lng)}
Images: Stored in S3/Blob storage, URLs served via CDN for fast global access
User checks availability: GET /v1/hotels/{hotel_id}/rooms?checkIn=2025-02-01&checkOut=2025-02-05&guests=2
Room Availability Service queries: SELECT r.room_id, r.room_type, r.capacity, p.date, p.price FROM rooms r JOIN room_availability a ON r.room_id = a.room_id AND a.hotel_id = {hotel_id} JOIN price_calendar p ON r.room_id = p.room_id WHERE a.date BETWEEN '2025-02-01' AND '2025-02-05' AND a.status IN ('Available', 'Booked', 'Maintenance') GROUP BY r.room_id HAVING COUNT(CASE WHEN a.status = 'Available' THEN 1 END) = {num_nights}
Alternative approach (not overcomplicated for this): Use availability table with alternative Q tree or geohashing (but overcomplicated for this)
Service calculates: Total price = SUM(price_per_night) for date range, applies dynamic pricing if needed
Response: [{ room_id, room_type, capacity, total_price, available_count, amenities[], images[] }]
Step 4: Booking Creation with Distributed Lock (Critical)
User confirms: POST /v1/booking/roomId with {room_id: 'room_123', user_id, check_in: '2025-02-01', check_out: '2025-02-05', guests: 2}
Booking Service FIRST acquires Redis distributed lock: SETNX lock:hotel:{hotel_id}:room:{room_id}:{check_in}:{check_out} {booking_attempt_id} EX 30 (30 second expiry)
Critical: Lock key includes hotel_id, room_id, and FULL date range to prevent concurrent bookings
If SETNX returns 0 (lock already held): Return error 'Room currently being booked, please try again' (HTTP 409 Conflict)
If SETNX returns 1 (lock acquired): Proceed with availability check
Double-check availability: SELECT status FROM room_availability WHERE room_id = {room_id} AND hotel_id = {hotel_id} AND date BETWEEN {check_in} AND {check_out} FOR UPDATE (pessimistic lock)
If ANY date shows status != 'Available': Release lock (DEL lock:...), return 'Room not available'
If all dates available: BEGIN TRANSACTION; (1) INSERT INTO bookings (booking_id, user_id, hotel_id, room_id, check_in, check_out, status='PENDING_PAYMENT', amount, created_at), (2) UPDATE room_availability SET status='Booked', booking_id={booking_id} WHERE room_id={room_id} AND date BETWEEN {check_in} AND {check_out}; COMMIT;
Release lock: DEL lock:hotel:{hotel_id}:room:{room_id}:{check_in}:{check_out}
Publish event: Kafka 'booking.created' topic with {booking_id, user_id, hotel_id, room_id, dates, amount}
Invoke Payment Service: Return {booking_id, payment_url, expires_at: now() + 15min}
Lock timeout handling: If service crashes while holding lock, Redis auto-expires lock after 30s (EX 30), preventing deadlock
Step 5: Payment Processing with Idempotency
User redirected to: Payment Gateway (Stripe/Razorpay) with payment_url
Payment Service creates: Payment intent with idempotency_key = booking_id (ensures same booking can't be charged twice)
User completes payment: Payment Gateway processes card, sends webhook POST /webhooks/payment with {booking_id, payment_id, status: 'success', amount}
Payment Service webhook handler: (1) Validates webhook signature (security), (2) Checks idempotency: SELECT * FROM payments WHERE booking_id = {booking_id}, if exists return 200 (already processed), (3) BEGIN TRANSACTION; INSERT INTO payments (payment_id, booking_id, amount, status='SUCCESS', gateway_response, created_at); UPDATE bookings SET status='CONFIRMED', payment_id={payment_id} WHERE booking_id={booking_id}; COMMIT;
Publish event: Kafka 'payment.success' and 'booking.confirmed' topics
Set booking expiry in Redis: SETEX booking:{booking_id}:expires 900 '1' (15 min TTL), if payment not received, background job cancels booking and releases room
Notification: Notification Service consumes Kafka event, sends confirmation email/SMS to user with booking details and QR code
Step 6: Booking Cancellation & Modification
User cancels: PUT /v1/booking/{booking_id} with {action: 'cancel', reason: 'user_requested'}
Booking Service validates: (1) Fetch booking, check user_id matches, (2) Check cancellation policy (free cancel if >24h before check_in, else charge fee)
Service updates: BEGIN TRANSACTION; UPDATE bookings SET status='CANCELLED', cancelled_at=now() WHERE booking_id={booking_id}; UPDATE room_availability SET status='Available', booking_id=NULL WHERE booking_id={booking_id}; COMMIT;
Refund: If applicable, call Payment Service → gateway.refund(payment_id, amount), status='REFUND_PROCESSING'
Publish event: Kafka 'booking.cancelled' topic
Notification: Email/SMS confirmation of cancellation and refund timeline (5-7 business days)
Modification: User can modify dates if new dates available → similar flow: check availability with lock, update booking and room_availability tables
Step 7: View Bookings (Past & Future)
User requests: GET /v1/bookings with header {Authorization: Bearer {token}}
Booking Service decodes: JWT token to extract user_id
Service queries: SELECT b.booking_id, b.hotel_id, h.name as hotel_name, h.image_url, b.room_id, r.room_type, b.check_in, b.check_out, b.status, b.amount FROM bookings b JOIN hotels h ON b.hotel_id = h.hotel_id JOIN rooms r ON b.room_id = r.room_id WHERE b.user_id = {user_id} ORDER BY b.created_at DESC LIMIT 50
Categorization: Client-side or service filters: future bookings (check_in > today), past bookings (check_out < today)
Caching: User booking list cached in Redis with key user:{user_id}:bookings, TTL=5 min, invalidated on new booking/cancellation
Response: { bookings: [{ booking_id, hotel: {...}, room: {...}, dates: {...}, status, amount, can_cancel: boolean }] }
Step 8: Reviews & Ratings
User submits review: POST /v1/reviews with {hotel_id, booking_id, rating: 4.5, comment: 'Great stay!', images[]}
Review Service validates: (1) Check booking_id exists and belongs to user, (2) Check booking is completed (check_out < today), (3) Check user hasn't already reviewed this booking
Service creates: Review record in Review DB {review_id, user_id, hotel_id, booking_id, rating, comment, images[], created_at, helpful_count: 0}
Aggregation: Background job updates hotel avg_rating: UPDATE hotels SET avg_rating = (SELECT AVG(rating) FROM reviews WHERE hotel_id = {hotel_id}), review_count = (SELECT COUNT(*) FROM reviews WHERE hotel_id = {hotel_id}) WHERE hotel_id = {hotel_id}
Elasticsearch sync: CDC pipeline pushes updated hotel rating to Elasticsearch for search ranking
Images: Upload to S3, store URLs in review record
Moderation: ML service scans review for inappropriate content, flags for manual review if needed
Step 9: Dynamic Pricing & Availability Updates
Price Calendar: Hotels can set different prices per date in price_calendar table {hotel_id, room_id, date, price, currency}
Dynamic pricing: ML model adjusts prices based on demand, season, events (e.g., conference in city → +30% price)
Bulk availability updates: Hotel admin updates multiple dates via POST /v1/hotels/{hotel_id}/availability with {room_id, dates[], status: 'Available'/'Maintenance'}
Service updates: Batch UPDATE room_availability SET status={status} WHERE room_id={room_id} AND date IN ({dates}) AND status != 'Booked' (don't override existing bookings)
Real-time sync: Changes published to Kafka, Search Service updates Elasticsearch cache within 1-2 seconds
Overbooking prevention: System maintains max_rooms per room_type, validation: SELECT COUNT(*) FROM room_availability WHERE room_id IN (SELECT room_id FROM rooms WHERE room_type={type}) AND date={date} AND status='Booked' must be < max_rooms
Step 10: Notification Flow (Kafka Event-Driven)
Event sources: Booking Service, Payment Service publish to Kafka topics: 'booking.created', 'booking.confirmed', 'booking.cancelled', 'payment.success', 'payment.failed'
Notification Service: Consumes all topics with separate consumer groups for reliability
Event: 'booking.confirmed' → (1) Fetch user email/phone from User DB, (2) Fetch booking details from Booking DB, (3) Generate email template with QR code (booking_id encoded), hotel details, check-in instructions, (4) Send via SendGrid/SES (email) and Twilio (SMS), (5) Store notification log in Notification DB
Push notifications: For mobile app users, send via FCM (Android) / APNS (iOS) with deep link to booking details
Reminder notifications: Scheduled jobs (1 day before check-in) send reminder emails/SMS with booking details
Kafka offset management: Consumer commits offset only after successful notification send, ensures exactly-once delivery on retry
7. Database Schema Details

Users (PostgreSQL)
user_id — uuid PRIMARY KEY
name — varchar(255)
email — varchar(255) UNIQUE, INDEXED
password — varchar(255) (bcrypt hash)
metadata — jsonb (preferences, saved hotels, etc.)
Hotels (PostgreSQL)
hotel_id — uuid PRIMARY KEY
name — varchar(255)
address — text
geo_pos — geography(Point, 4326) - latitude + longitude
rating — decimal(2,1) (avg rating from reviews)
amenities — jsonb array ['WiFi', 'Pool', 'Parking']
images — jsonb array of S3/CDN URLs
description — text
Index — GIST index on geo_pos for spatial queries
Rooms (PostgreSQL)
room_id — uuid PRIMARY KEY
hotel_id — uuid FK → Hotels, INDEXED
room_type — varchar(100) (Deluxe, Suite, Standard)
capacity — integer (max guests)
amenities — jsonb array
metadata — jsonb (bed type, view, etc.)
Price_Calendar (PostgreSQL)
hotel_id — uuid
room_id — uuid
date — date
price — decimal(10,2)
currency — varchar(3) (USD, EUR, INR)
Composite PK — (hotel_id, room_id, date)
Index — INDEX on (hotel_id, date) for range queries
Room_Availability (PostgreSQL)
hotel_id — uuid
room_id — uuid
date — date
status — enum (Available, Booked, Maintenance)
booking_id — uuid (nullable, set when status=Booked)
Composite PK — (hotel_id, room_id, date)
Index — INDEX on (room_id, date, status) for availability queries
Bookings (PostgreSQL)
booking_id — uuid PRIMARY KEY
hotel_id — uuid FK → Hotels
room_id — uuid FK → Rooms
user_id — uuid FK → Users, INDEXED
check_in — date
check_out — date
start_date — timestamp (check-in date)
end_date — timestamp (check-out date)
amount — decimal(10,2)
currency — varchar(3)
status — enum (PENDING_PAYMENT, CONFIRMED, CANCELLED, COMPLETED)
payment_id — varchar(255) (from payment gateway)
metadata — jsonb (guest details, special requests, etc.)
Reviews (PostgreSQL)
review_id — uuid PRIMARY KEY
hotel_id — uuid FK → Hotels, INDEXED
user_id — uuid FK → Users
booking_id — uuid FK → Bookings, UNIQUE (one review per booking)
rating — decimal(2,1) (1.0 to 5.0)
comment — text
images — jsonb array of S3 URLs
Payment (PostgreSQL)
payment_id — varchar(255) PRIMARY KEY (from gateway)
booking_id — uuid FK → Bookings, UNIQUE (idempotency)
amount — decimal(10,2)
currency — varchar(3)
status — enum (PENDING, SUCCESS, FAILED, REFUNDED)
gateway_response — jsonb (full webhook payload)
created_at — timestamp
Elasticsearch - Hotel Search Index
hotel_id — keyword
name — text (searchable)
location — geo_point (lat, lng)
amenities — keyword array
rating — float
price_range — object {min, max}
start_date — date (for availability - optional)
end_date — date
Redis - Locks & Cache
lock:hotel:{hotelId}:room:{roomId}:{checkIn}:{checkOut} — STRING {booking_attempt_id} EX 30 (distributed lock for booking, 15min TTL)
search:{hash(location,filters)} — STRING (JSON) - cached search results, TTL 10min
user:{userId}:bookings — STRING (JSON) - cached user bookings, TTL 5min
booking:{bookingId}:expires — STRING '1' EX 900 (15min payment timeout)
Blob Storage (S3 / Azure Blob)
Hotel Images — S3 bucket: hotels/{hotel_id}/{image_id}.jpg, served via CDN
Review Images — S3 bucket: reviews/{review_id}/{image_id}.jpg
8. Scaling & Optimization

Technique 1: Elasticsearch Geo Sharding - Shard hotel index by region (US, EU, Asia), parallel queries
Technique 2: Redis Distributed Locks - SETNX with expiry prevents double booking race conditions, auto-release on timeout
Technique 3: Database Read Replicas - Route read queries (search, view bookings) to replicas, writes to primary
Technique 4: CDN for Images - Hotel/room images served from edge locations, 95% cache hit rate, <50ms latency
Technique 5: Kafka Event Streaming - Async notifications, booking events, payment confirmations, decouples services
Technique 6: Caching Layer - Redis caches search results (TTL=10min), user bookings (TTL=5min), hotel details (TTL=30min)
Technique 7: Connection Pooling - API servers maintain 100-200 DB connections, prevents exhaustion at scale
Technique 8: API Rate Limiting - 100 req/min per user with token bucket, protects against abuse
Technique 9: Database Partitioning - Partition bookings table by date (monthly partitions), improves query performance
Technique 10: Lazy Loading - Load hotel images on-demand, paginate search results (50 per page), reduces payload
Technique 11: Geo-Based Routing - Route users to nearest data center (US-East, EU-West, Asia), reduces latency
Technique 12: CDC Pipeline - PostgreSQL → Debezium → Kafka → Elasticsearch, real-time search index updates
9. Common Interview Questions

Q
How do you prevent double booking (two users booking same room for overlapping dates)?
A
Multi-layer approach with distributed locks:

(1) Redis distributed lock BEFORE availability check: SETNX lock:hotel:{hotel_id}:room:{room_id}:{check_in}:{check_out} {booking_attempt_id} EX 30, lock key includes FULL date range,

(2) If SETNX returns 0 (lock exists), return 409 Conflict 'Room being booked, try again',

(3) If SETNX returns 1 (lock acquired), proceed to database,

(4) Double-check availability with pessimistic database lock: SELECT status FROM room_availability WHERE room_id={room_id} AND date BETWEEN {check_in} AND {check_out} FOR UPDATE (row-level lock),

(5) If ANY date shows status != 'Available', release Redis lock, return 'Not available',

(6) If all available: BEGIN TRANSACTION; INSERT booking; UPDATE room_availability SET status='Booked', booking_id={id} WHERE room_id={room_id} AND date BETWEEN {dates}; COMMIT;,

(7) Release Redis lock: DEL lock:...,

(8) Lock auto-expires after 30s if service crashes, prevents deadlock. Why both locks?: Redis is fast (1-2ms) for early rejection, PostgreSQL FOR UPDATE ensures ACID guarantees within transaction. Example race: User A and B both try booking room_123 for Feb 1-5 → User A's SETNX succeeds → User B's SETNX fails immediately → User B sees 'being booked' → User A completes booking → User B can retry and see 'not available' → no double booking.

Q
How do you implement hotel search with location, dates, and price filters efficiently?
A
Elasticsearch with geo_distance + compound filters:

(1) User searches: location='Paris', checkIn='2025-03-01', checkOut='2025-03-05', priceMax=200, guests=2,

(2) Geocode location to (48.8566, 2.3522) using Google Geocoding API or cached mappings,

(3) Query Elasticsearch: POST /hotels/_search { 'query': { 'bool': { 'filter': [ { 'geo_distance': { 'distance': '20km', 'location': { 'lat': 48.8566, 'lon': 2.3522 } } }, { 'range': { 'price_range.min': { 'lte': 200 } } }, { 'terms': { 'amenities': ['WiFi'] } } ] } }, 'sort': [ { '_geo_distance': { 'location': {...}, 'order': 'asc' } } ], 'size': 50 },

(4) NOTE: Elasticsearch returns hotels matching location + static filters only, does NOT check date availability (too complex for search index),

(5) For availability: Separate API call GET /v1/hotels/{hotel_id}/availability?dates=... after user selects hotel, queries room_availability table,

(6) Alternative overcomplicated: Store availability bitmap in ES (not recommended - high write volume, inconsistency risk). Why this approach?:

(a) ES is optimized for text + geo search, not dynamic availability,

(b) Availability changes frequently (every booking), reindexing ES on every booking = high latency + cost,

(c) Better UX: Show all hotels nearby, then check availability on-demand. Caching: Cache popular searches in Redis with TTL=10min, invalidate on hotel metadata changes only. CDC: PostgreSQL hotel updates → Kafka → ES indexer keeps search index fresh within 1-2s.

Q
How do you ensure payment idempotency (prevent double charging if user clicks pay twice)?
A
Idempotency at multiple layers:

(1) Client generates idempotency_key = booking_id before payment,

(2) Payment Service: POST /payments with {booking_id, amount, idempotency_key: {booking_id}},

(3) Payment Gateway (Stripe/Razorpay) uses same idempotency_key for createPaymentIntent API,

(4) Gateway guarantees: Same idempotency_key within 24h = return same payment_intent_id, no duplicate charge,

(5) Database constraint: UNIQUE INDEX on payments(booking_id) ensures single payment record per booking,

(6) Webhook handling: POST /webhooks/payment with {booking_id, payment_id, status: 'success'},

(a) Check: SELECT * FROM payments WHERE booking_id = {booking_id}, if exists return 200 OK (already processed),

(b) If not: BEGIN TRANSACTION; INSERT INTO payments (payment_id, booking_id, amount, status='SUCCESS'); UPDATE bookings SET status='CONFIRMED', payment_id={payment_id}; COMMIT;,

(c) Database constraint prevents race condition: Two concurrent webhooks → first INSERT succeeds, second fails on UNIQUE constraint → handled gracefully.

(7) Kafka event published only once due to database constraint. Example: User double-clicks 'Pay' → Request 1 creates payment_intent_123 → Request 2 with same idempotency_key → Gateway returns existing payment_intent_123 → user charged once. Alternative: Use distributed lock SETNX lock:payment:{booking_id} before payment, but gateway idempotency + DB constraint simpler and more reliable.

Q
How do you handle room availability updates and booking modifications?
A
Availability updates flow:

(1) Hotel admin updates availability: PUT /v1/hotels/{hotel_id}/rooms/{room_id}/availability with {dates: ['2025-03-01', '2025-03-02'], status: 'Maintenance'},

(2) Service validates: Cannot change status if date already booked (status='Booked'),

(3) Bulk update: UPDATE room_availability SET status={status} WHERE room_id={room_id} AND date IN ({dates}) AND status != 'Booked',

(4) Publish Kafka event: 'availability.updated' for cache invalidation,

(5) Cache invalidation: Clear Redis cached availability for affected hotel/room. Booking modification (date change):

(1) User modifies: PUT /v1/bookings/{booking_id} with {new_check_in, new_check_out},

(2) Service validates:

(a) Check cancellation policy (some bookings non-refundable),

(b) Check new dates available,

(3) Acquire distributed lock: SETNX lock:hotel:{hotel_id}:room:{room_id}:{new_check_in}:{new_check_out},

(4) Check new availability: SELECT status FROM room_availability WHERE room_id={room_id} AND date BETWEEN {new_dates} FOR UPDATE,

(5) If available: BEGIN TRANSACTION;

(a) Release old dates: UPDATE room_availability SET status='Available', booking_id=NULL WHERE booking_id={booking_id},

(b) Book new dates: UPDATE room_availability SET status='Booked', booking_id={booking_id} WHERE room_id={room_id} AND date BETWEEN {new_dates},

(c) Update booking: UPDATE bookings SET check_in={new_check_in}, check_out={new_check_out}, amount={new_amount} WHERE booking_id={booking_id}; COMMIT;,

(6) Release lock,

(7) Publish 'booking.modified' event. Price adjustment: If new dates have different pricing, calculate difference and either charge extra or refund. Edge cases:

(1) New dates more expensive: Charge difference via payment gateway,

(2) New dates cheaper: Issue partial refund,

(3) No availability: Return error with alternative dates suggestions.

Q
How do you implement the review and rating system with aggregation?
A
Review submission and aggregation:

(1) User submits review: POST /v1/reviews with {hotel_id, booking_id, rating: 4.5, comment: 'Great location!', images: [file1, file2]},

(2) Validation:

(a) Check booking exists and belongs to user: SELECT * FROM bookings WHERE booking_id={booking_id} AND user_id={user_id},

(b) Check booking completed (check_out < today), can't review before stay,

(c) Check no existing review: SELECT * FROM reviews WHERE booking_id={booking_id}, only one review per booking,

(3) Upload images to S3: Multi-part upload → s3://reviews/{review_id}/{image_id}.jpg, get CDN URLs,

(4) Insert review: INSERT INTO reviews (review_id, hotel_id, user_id, booking_id, rating, comment, images[], created_at, helpful_count: 0),

(5) Background aggregation job (async):

(a) Calculate new avg: UPDATE hotels SET avg_rating = (SELECT AVG(rating) FROM reviews WHERE hotel_id={hotel_id}), review_count = (SELECT COUNT(*) FROM reviews WHERE hotel_id={hotel_id}) WHERE hotel_id={hotel_id},

(b) Can use materialized view for better performance: CREATE MATERIALIZED VIEW hotel_ratings AS SELECT hotel_id, AVG(rating), COUNT(*) FROM reviews GROUP BY hotel_id, refresh every 10 min,

(6) CDC pipeline: hotel.avg_rating update → Kafka → Elasticsearch indexer updates search index,

(7) Moderation: ML service (AWS Comprehend / Cloud NLP) scans review text for: profanity, spam, fake reviews, flags for manual review if confidence >0.8,

(8) Helpful votes: Users can vote reviews helpful: POST /v1/reviews/{review_id}/helpful, increments helpful_count for ranking. Display: GET /v1/hotels/{hotel_id}/reviews?sortBy=helpful&page=1&size=20, sorted by helpful_count DESC or created_at DESC. Alternative aggregation: Use Apache Flink for real-time rating updates, but materialized view + periodic refresh simpler and sufficient.

Q
How do you handle time zones and date calculations for global hotels?
A
Time zone handling strategy:

(1) Database storage: ALL timestamps stored in UTC in PostgreSQL (timestamp without timezone type),

(2) Hotels table: Add timezone column: hotel_timezone varchar

(50) (e.g., 'America/New_York', 'Europe/London') using IANA tz database,

(3) Check-in/check-out dates: Stored as DATE type (not timestamp), represents local date at hotel location,

(4) Business logic: When user searches, dates are in hotel's local timezone: User searches 'Paris hotels for March 1-5' → interpreted as Paris local dates, not user's timezone,

(5) Display to user: Backend returns dates + hotel_timezone: {check_in: '2025-03-01', check_out: '2025-03-05', timezone: 'Europe/Paris'}, client displays in local terms: 'Checking in March 1, 2025 (Paris time)',

(6) Availability calculation: room_availability.date is in hotel local date, no timezone conversion needed for availability checks,

(7) Payment deadlines: Stored as UTC timestamp: booking.payment_deadline = booking.created_at + 15 min (UTC), displayed to user in their local timezone,

(8) Notifications: Email/SMS include explicit timezone: 'Check-in: March 1, 2025 at 3:00 PM CET',

(9) Edge case - DST: Use proper timezone library (moment-timezone / date-fns-tz) not just UTC offset, handles daylight saving automatically. Example: User in California (UTC-8) books London hotel (UTC+0) for March 1-5 → Backend stores: {check_in: DATE '2025-03-01', check_out: DATE '2025-03-05', hotel_timezone: 'Europe/London', created_at: TIMESTAMP '2025-01-15 20:30:00 UTC'} → User sees: 'Booking confirmed for March 1-5, 2025 (London time), made on Jan 15, 2025 12:30 PM PST'. Alternative: Store all dates with timezone as TIMESTAMPTZ, but DATE simpler for booking dates as time-of-day not relevant for check-in dates.

Q
How do you implement cancellation policies and refund processing?
A
Multi-tier cancellation policy:

(1) Policy rules stored per hotel/room: cancellation_policy table {hotel_id, room_id, policy_type: 'flexible'/'moderate'/'strict', rules: jsonb},

(2) Flexible: { free_cancellation_hours: 24, partial_refund_percent: 50 until 12h, no_refund_hours: 0 }, Moderate: { 72h free, 24h 50%, <24h no refund }, Strict: { 7 days free, <7 days no refund },

(3) Booking creation: Copy policy to bookings.cancellation_policy jsonb (snapshot at booking time, protects user if policy changes later),

(4) User cancels: PUT /v1/bookings/{booking_id}/cancel with {reason: 'user_requested'},

(5) Calculate refund:

(a) Fetch booking.cancellation_policy and booking.check_in,

(b) Calculate hours_until_checkin = (check_in - now()) in hours,

(c) Apply policy rules: if hours_until_checkin >= 24: refund_amount = booking.amount (100%), elif hours_until_checkin >= 12: refund_amount = booking.amount * 0.5 (50%), else: refund_amount = 0,

(6) Process cancellation: BEGIN TRANSACTION;

(a) UPDATE bookings SET status='CANCELLED', cancelled_at=now(), refund_amount={refund_amount}, refund_status='PROCESSING',

(b) UPDATE room_availability SET status='Available', booking_id=NULL WHERE booking_id={booking_id},

(c) If refund_amount > 0: INSERT INTO refunds (refund_id, booking_id, amount, status='PENDING'); COMMIT;,

(7) Async refund: Background job calls Payment Gateway: stripe.refunds.create({payment_intent_id, amount}),

(8) Webhook confirms: POST /webhooks/refund with {refund_id, status: 'succeeded'} → UPDATE refunds SET status='COMPLETED', bookings.refund_status='REFUNDED',

(9) Notification: Email user 'Booking cancelled, refund of ${amount} will appear in 5-7 business days',

(10) Publish Kafka 'booking.cancelled' event. Partial refunds: Some policies allow partial cancellation (e.g., 3-night booking, cancel 1 night) → more complex, need to track per-night cancellations. Abuse prevention: Track user cancellation_rate = cancelled_bookings / total_bookings, if >30% in last 10 bookings, flag account for review or increase cancellation fee. Example: User books on Jan 1 for March 1 check-in (flexible policy) → Cancels Feb 28 (1 day before) → 24 hours remaining → 100% refund → refund processed → room becomes available.

Q
How do you scale the search service to handle 100M searches per day?
A
Multi-tier scaling strategy:

(1) Elasticsearch cluster: 10 data nodes, 3 master nodes, shard hotel index by region (US, EU, Asia), each region has 5 primary shards + 1 replica,

(2) Geo-based routing: API Gateway routes search requests to nearest ES cluster: User in US → us-east-1 cluster, EU → eu-west-1 cluster, reduces latency from 500ms to 50ms,

(3) Caching layer: Redis caches popular searches: Key: hash(location, checkIn, checkOut, filters) → Value: JSON search results, TTL: 10 min, Cache hit rate: ~60-70% (many users search same popular destinations), Cache size: 100GB Redis cluster (10 nodes) stores ~10M cached searches,

(4) Query optimization:

(a) Use filter context (not query context) for filters: { 'bool': { 'filter': [...] } } → faster, cacheable,

(b) Disable scoring for geo queries: 'track_scores': false,

(c) Fetch only required fields: '_source': ['hotel_id', 'name', 'location', 'rating'],

(5) API rate limiting: Per-user: 100 searches/min, Per-IP: 1000 searches/min (protects against scraping bots),

(6) Database read replicas: PostgreSQL primary + 5 read replicas in each region, search service queries replicas for hotel metadata after ES returns IDs,

(7) CDN for images: Hotel images served from CloudFront edge locations, <50ms latency globally, 95% cache hit rate,

(8) Load balancing: 100 search service instances behind ALB, auto-scaling based on CPU >70%,

(9) Async indexing: Hotel updates → Kafka → ES indexer consumer (separate service), doesn't block write operations, eventual consistency (1-2s delay acceptable for search),

(10) Connection pooling: Each search service instance maintains 50 ES connections (HTTP keep-alive),

(11) Monitoring: Prometheus + Grafana track: search latency p50/p95/p99, cache hit rate, ES cluster health, alert if p95 >500ms. Load: 100M searches/day = 1,157 searches/sec average, peak 3x = 3,500 searches/sec, Scaling math: 100 instances × 50 req/sec capacity = 5,000 req/sec headroom. Cost: ES cluster $5K/month, Redis $1K/month, API servers $3K/month = $9K/month for search infrastructure.

Q
How do you handle overbooking scenarios and inventory management?
A
Overbooking prevention with inventory tracking:

(1) Room inventory model: Hotels have multiple rooms of same type (e.g., 20 Deluxe rooms), rooms table: {hotel_id, room_type, total_count: 20}, individual_rooms table: {room_id, hotel_id, room_type, room_number: '101'},

(2) Availability tracking: Two approaches:

(a) Aggregate: room_availability_aggregate {hotel_id, room_type, date, available_count, booked_count}, faster queries but complex updates,

(b) Individual: room_availability {room_id, date, status, booking_id}, simpler but more rows.

(3) Booking validation:

(a) User books 'Deluxe room' (not specific room_id initially),

(b) Query: SELECT COUNT(*) as booked FROM room_availability WHERE hotel_id={hotel_id} AND room_type='Deluxe' AND date BETWEEN {dates} AND status='Booked',

(c) Check: booked_count < total_deluxe_rooms for ALL dates in range,

(d) Acquire distributed lock: SETNX lock:hotel:{hotel_id}:room_type:Deluxe:{dates},

(e) Assign specific room: SELECT room_id FROM rooms WHERE hotel_id={hotel_id} AND room_type='Deluxe' AND room_id NOT IN (SELECT room_id FROM room_availability WHERE date BETWEEN {dates} AND status='Booked') LIMIT 1 FOR UPDATE,

(f) Update: UPDATE room_availability SET status='Booked', booking_id={booking_id} WHERE room_id={assigned_room_id} AND date BETWEEN {dates}.

(4) Controlled overbooking: Some hotels deliberately overbook by 5-10% (like airlines) to account for cancellations, overselling_limit table: {hotel_id, room_type, max_overbook_percent: 0.05}, validation: allow booking if booked_count <= total_count * 1.05, risk mitigation: if actually overbooked on check-in day, hotel upgrades guest to better room or relocates to partner hotel (hotel's responsibility).

(5) Maintenance blocking: Hotel can block rooms: room_availability.status = 'Maintenance' → excluded from available_count.

(6) Edge case - race condition: Two bookings at exact same time for last available room → distributed lock + database FOR UPDATE ensures only one succeeds. Example: Hotel has 20 Deluxe rooms, March 1: 18 booked, 2 available → User A and B both try booking → User A acquires lock → checks availability (2 available) → assigns room_123 → updates to 19 booked → releases lock → User B acquires lock → checks availability (1 available) → assigns room_124 → updates to 20 booked → releases lock → Third user tries → no rooms available.

Q
What's your strategy for disaster recovery and data consistency?
A
Multi-region DR with RPO/RTO targets:

(1) Primary region: us-east-1, Secondary: us-west-2, Tertiary: eu-west-1,

(2) Database replication: PostgreSQL primary in us-east-1, streaming replication to us-west-2 (warm standby) and eu-west-1 (read replica), Replication lag: <5 seconds under normal load,

(3) RPO (Recovery Point Objective): 5 seconds (maximum data loss acceptable), achieved via synchronous replication to secondary,

(4) RTO (Recovery Time Objective): 5 minutes (time to restore service), automated failover via Route53 health checks,

(5) Elasticsearch: Multi-cluster setup, each region has independent ES cluster, synced via CDC pipeline (PostgreSQL → Kafka → ES in all regions), eventual consistency acceptable for search,

(6) Redis: Redis Sentinel for automatic failover (master-slave replication), persistence via AOF (Append-Only File) for data durability,

(7) S3 cross-region replication: Hotel images replicated to backup bucket in secondary region automatically,

(8) Kafka: Multi-region setup with MirrorMaker replicates events to secondary Kafka cluster,

(9) Failover procedure:

(a) Route53 health check detects primary region down (failed health checks for 30s),

(b) Automatically updates DNS to point to secondary region,

(c) Secondary PostgreSQL promoted to primary (pg_ctl promote),

(d) API Gateway in secondary region starts accepting traffic,

(e) Total downtime: ~2-5 minutes for DNS propagation,

(10) Booking consistency during failover: In-flight bookings during failover may fail → retry mechanism + idempotency ensures no double booking, Users see temporary error → retry automatically succeeds in new region,

(11) Testing: Monthly DR drills, simulate primary region failure, verify RTO <5 min, identify gaps,

(12) Backups: Daily full backup + hourly incremental backups to S3 Glacier, retention: 30 days, quarterly disaster recovery from backup test. Example: Primary region (us-east-1) suffers outage at 10:00 AM → Route53 detects failure at 10:00:30 → Initiates failover → us-west-2 promoted to primary at 10:02 → DNS updated at 10:03 → Users routed to new region at 10:05 → Service restored, data loss <5 sec (last replicated at 09:59:55). Cost: Multi-region setup adds ~40% infrastructure cost but provides business continuity.

10. Key Numbers to Remember

Scale & Volume
Total Users — 50M registered users globally
Hotels — 1M hotels, 10M+ rooms
Daily Searches — 100M searches/day = 1,157 searches/sec average, 3x peak
Daily Bookings — 1M bookings/day = 11.5 bookings/sec average
Conversion Rate — 1% (100M searches → 1M bookings)
Latency Requirements
Hotel Search — < 500ms (Elasticsearch geo query + filters)
Availability Check — < 300ms (PostgreSQL query on room_availability)
Booking Creation — < 2s (includes lock acquisition, DB transaction, payment initiation)
Redis Lock Acquisition — < 10ms (SETNX operation)
Payment Processing — < 5s (payment gateway external call)
Consistency & Locks
Redis Lock TTL — 30 seconds (prevents deadlock if service crashes)
Payment Timeout — 15 minutes (booking expires if payment not completed)
Idempotency Key Validity — 24 hours (payment gateway)
Database Replication Lag — < 5 seconds (PostgreSQL streaming replication)
Caching
Search Cache TTL — 10 minutes (Redis cached search results)
User Bookings Cache TTL — 5 minutes (invalidated on new booking)
Hotel Details Cache TTL — 30 minutes
Cache Hit Rate — 60-70% for search queries, 95% for images (CDN)
Business Metrics
Average Booking Value — $150-300 per night
Average Stay Duration — 2-3 nights
Cancellation Rate — 15-20% of bookings
Platform Commission — 15-25% of booking value (paid by hotel)
Disaster Recovery
RPO (Recovery Point) — < 5 seconds (data loss acceptable)
RTO (Recovery Time) — < 5 minutes (time to restore service)
Backup Frequency — Daily full + hourly incremental
Backup Retention — 30 days (compliance requirement)
Key Interview Tips

⚠️
CRITICAL: Prevent double booking with Redis distributed lock BEFORE database check. Lock key MUST include hotel_id, room_id, AND full date range. SETNX lock:hotel:{id}:room:{id}:{checkIn}:{checkOut} with EX 30. Without this, race conditions cause overbooking.

⭐
Interviewers ALWAYS ask: 'How to prevent double booking?'. Answer: (1) Redis SETNX lock with date range, (2) PostgreSQL SELECT FOR UPDATE on room_availability, (3) Transaction to INSERT booking + UPDATE availability atomically, (4) Lock auto-expires 30s to prevent deadlock.

💡
Search optimization: Elasticsearch returns hotels with static filters (location, price, amenities) only, NOT date availability. Separate API checks availability after user selects hotel. Why? Availability changes every booking - reindexing ES constantly = expensive + slow.

⭐
Must mention: Payment idempotency using booking_id as idempotency_key. Payment gateway + database UNIQUE constraint ensures no double charge even if user clicks 'Pay' multiple times or webhook replays.

⚠️
NEVER check availability in Elasticsearch. ES is for search (location + filters), not transactional data. Availability is highly dynamic - use PostgreSQL room_availability table with pessimistic locks (SELECT FOR UPDATE).

💡
Multi-region DR: Primary region us-east-1, warm standby us-west-2 with streaming replication (lag <5s). Route53 health checks auto-failover in 2-5 min. RPO=5s, RTO=5min. Test DR monthly.

⭐
Interviewers love: 'How to handle cancellations?'. Answer: Store cancellation_policy snapshot in booking at creation (protects user if policy changes). Calculate refund based on hours_until_checkin. Release room_availability, process async refund via payment gateway webhook.

⚠️
NEVER use eventual consistency for bookings. Use ACID transactions (BEGIN; INSERT booking; UPDATE room_availability; COMMIT;). Strong consistency required - no two users can book same room/dates.

💡
Caching strategy: Search results (TTL=10min, 60% hit rate), hotel details (TTL=30min), user bookings (TTL=5min, invalidate on changes). Redis cluster serves 70% of searches without hitting Elasticsearch/PostgreSQL.

⭐
Must explain: Lock key design lock:hotel:{hotel_id}:room:{room_id}:{checkIn}:{checkOut} - includes FULL date range. Why? Prevents concurrent bookings for overlapping dates. Lock expires automatically in 30s if service crashes.

system-design
hotel-booking
Airbnb
