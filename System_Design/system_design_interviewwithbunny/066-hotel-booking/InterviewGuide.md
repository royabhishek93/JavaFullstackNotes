# Hotel Booking System — Interview Guide
> Covers: Airbnb / MakeMyTrip / Bookings.com

---

## Quick Pitch (say this in the first 30 seconds)
> "Search hotels via Elasticsearch geo → Check availability in PostgreSQL → Book room with Redis distributed lock → Process payment with idempotency key → Confirm via Kafka events."

---

## 1. Functional Requirements

| Feature | Detail |
|---------|--------|
| Auth | Register / Login / Logout / Update profile |
| Search | By name, location, dates — filter by price, rating, amenities |
| Hotel Details | Rooms, prices, photos, reviews |
| Booking | Payment to confirm; room + dates locked atomically |
| My Bookings | View past & future; cancel / modify |

---

## 2. Non-Functional Requirements

| Concern | Target |
|---------|--------|
| Users | 50M users, 1M hotels, 10M+ rooms |
| Searches | 100M/day → ~1,157/sec avg, 3,500/sec peak |
| Bookings | 1M/day → ~11.5/sec |
| Search latency | < 500ms |
| Booking creation | < 2s (includes lock + DB + payment init) |
| CAP for Search | **Availability** (eventual consistency ok) |
| CAP for Booking | **Consistency** (no double booking ever) |

---

## 3. Core Entities

```
User        → user_id, name, email, password_hash, metadata
Hotel       → hotel_id, name, address, geo_pos(lat,lng), rating, amenities[], images[]
Room        → room_id, hotel_id, room_type, capacity, amenities[], metadata
Booking     → booking_id, user_id, hotel_id, room_id, check_in, check_out, status, amount, payment_id
Price_Cal   → (hotel_id, room_id, date) → price, currency
Room_Avail  → (hotel_id, room_id, date) → status [Available|Booked|Maintenance], booking_id
Payment     → payment_id (PK from gateway), booking_id UNIQUE, amount, status, gateway_response
Review      → review_id, hotel_id, user_id, booking_id UNIQUE, rating, comment, images[]
```

> **WHY ROOM_AVAILABILITY TABLE EXISTS? (Beginner Explanation)**
>   Think of a hotel like a parking garage where every spot (room) on every day is either "taken" or "free."
>   You can't just store "Room 101 is booked" — you need to know *which specific dates* are occupied.
>   The Room_Availability table is like a wall calendar with one sticky note per room per date; booking Feb 1–5 flips exactly 5 sticky notes from Available → Booked.
>   Real-time availability is hard because thousands of users may be eyeing the same room at the same second — a 1-second stale read = a confirmed double booking.
>   Without per-date granularity you couldn't answer "is Room 101 free on Feb 3 but occupied Feb 4?" or handle multi-night stays with gaps.
>   Alternative (a single booked/free flag per room): works for a motel with one price and no date ranges, but breaks the instant you have partial-date overlaps or variable occupancy.

---

## 4. API Design

```
# Auth
POST /v1/users/register           {name, email, password}     → {userId, token}
POST /v1/users/login              {email, password}           → {token, refresh_token}

# Search & Details
GET  /v1/hotels/search            ?location&checkIn&checkOut&guests&priceMax  → List<Hotel> paginated
GET  /v1/hotels/{hotelId}                                     → HotelDetails
GET  /v1/hotels/{hotelId}/rooms   ?checkIn&checkOut&guests    → List<Room> with pricing

# Booking
POST /v1/booking/{roomId}         {userId, checkIn, checkOut, guests}  → {bookingId, payment_url}
PUT  /v1/booking/{bookingId}      {action: cancel|modify, ...}         → Updated booking
GET  /v1/bookings                 header: Authorization                → List<Booking>

# Reviews
POST /v1/reviews                  {hotel_id, booking_id, rating, comment, images[]}
```

---

### Missing Endpoints (added below — not yet covered above)

```
# Booking Detail & Confirmation
GET  /v1/bookings/{bookingId}                                 → BookingDetail {bookingId, userId, hotelId, roomId, checkIn, checkOut, status, amount, paymentId}
GET  /v1/bookings/{bookingId}/confirmation                    → {confirmationNumber, hotel, room, guestName, checkIn, checkOut, totalAmount, paymentStatus, qrCode}

# Admin / Hotel Inventory Management
PATCH /v1/hotels/{hotelId}/rooms/{roomId}                    {price_override, status: Available|Maintenance, max_guests} → Updated Room
```

> **WHY GET /v1/bookings/{bookingId}?**
> The existing `GET /v1/bookings` returns the full list — but after creating a booking the client needs to poll or deep-link into a *single* booking to check its real-time status (`PENDING_PAYMENT → CONFIRMED`). Without this endpoint, the only way to check "did my payment go through?" is to fetch the entire booking history and filter client-side. In interviews this matters because mobile apps use this endpoint to drive the post-booking status screen and push-notification deep-links.

> **WHY GET /v1/bookings/{bookingId}/confirmation?**
> Booking detail returns raw data; confirmation returns a *presentation-ready* payload — confirmation number, hotel address, QR code / barcode for check-in, guest name as it will appear at the desk. Separating these is standard practice (single responsibility): the booking service owns transactional state, the confirmation endpoint composes a read-model optimised for display and email/PDF rendering. It also lets you cache confirmations aggressively (TTL indefinitely once `CONFIRMED`) without touching the mutable booking record.

> **WHY PATCH /v1/hotels/{hotelId}/rooms/{roomId}?**
> Hotel admins need a management plane separate from the guest-facing booking flow: temporarily pulling a room into `Maintenance` (burst pipe, deep clean), overriding dynamic prices for a single room, or raising capacity for a suite. Without this endpoint the only path is direct database access, which bypasses audit logging, authorization checks, and the CDC pipeline that syncs changes to Elasticsearch. In interviews, mentioning an admin API shows you've thought about the operator persona, not just the end-user path.

---

## 5. High-Level Architecture (from diagram)

```
Users
  └─► LB + API Gateway  (auth, rate-limit, round-robin routing)
        ├─► User Svc        ──► User DB (PostgreSQL)
        ├─► Search Svc      ──► Elasticsearch  ◄── CDC ── Hotel DB
        ├─► Review Svc      ──► Review DB
        └─► Booking Svc     ──► Booking DB
                │                    │
                │             Redis Lock (SETNX)
                │
                └─► Payment Svc ──► Payment Gateway
                                └─► Payment DB

Kafka  ◄── (booking.created / payment.success / booking.cancelled)
  └─► Booking Consumer
  └─► Notification Svc  (email / SMS / push)
```

> **WHY KAFKA (EVENT STREAMING) EXISTS? (Beginner Explanation)**
>   Kafka is the order-ticket printer at a busy restaurant — the waiter drops the ticket at the pass and walks away; they don't stand there waiting for the food to be plated.
>   When a booking is confirmed, the Booking Service publishes one event to Kafka and moves on in milliseconds. Multiple consumers (Notification Service, Analytics, Channel Manager) independently pick up that event and do their own work at their own pace.
>   Without Kafka, the Booking Service would have to call Notification Service, Analytics, and Channel Manager directly and wait for each — if any one is slow or crashes, the entire booking flow stalls and the guest waits.
>   Kafka also acts as a buffer during traffic spikes: if 10,000 bookings confirm in one second, the Notification Service can drain the queue at whatever rate it can handle, instead of being overwhelmed.
>   Alternative (direct synchronous calls between services): simpler to reason about but creates tight coupling — one downstream service going down takes the whole booking path with it.

---

## 6. Low-Level Design — Step by Step

### Step 1: User Registration & Auth
- `POST /v1/users/register` → validate email uniqueness → store `bcrypt(password)` → return JWT (7d) + refresh token in Redis
- Login: validate bcrypt hash → issue JWT

> **WHY ELASTICSEARCH FOR HOTEL SEARCH EXISTS? (Beginner Explanation)**
>   Elasticsearch is like a smart concierge — you say "cozy hotel near the Eiffel Tower, under $150, with a pool" and it instantly understands.
>   A SQL database is like a filing cabinet: great for exact lookups ("give me hotel_id=123"), but painfully slow at "find all hotels within 20 km of this GPS coordinate AND matching fuzzy text AND sort by distance."
>   ES has built-in geo_distance queries, full-text analysis, and filter caching that make it 10–100x faster than SQL for this search pattern.
>   Without ES, a SQL query with geo math + text matching + price range + amenity filters on 1M hotels would timeout at peak load.
>   Alternative (SQL + PostGIS extension): works at small scale but can't handle 3,500 searches/sec without massive hardware; ES scales horizontally by adding nodes.

### Step 2: Hotel Search (Elasticsearch Geo)
```
Geocode "London" → (51.5074, -0.1278)

ES Query:
{
  "query": { "bool": { "filter": [
    { "geo_distance": { "distance": "20km", "location": {...} } },
    { "range": { "price_range.min": { "lte": 200 } } },
    { "term": { "amenities": "WiFi" } }
  ]}},
  "sort": [{ "_geo_distance": { "order": "asc" } }],
  "size": 50
}
```
> **KEY**: ES does NOT check date availability — too dynamic. Separate API call after hotel selection.
> Cache popular searches: `Redis key: hash(location,filters)` TTL=10min

> **WHY DYNAMIC PRICING (Price_Calendar) EXISTS? (Beginner Explanation)**
>   Hotel room prices aren't fixed — they behave like airline tickets. The same room costs $80 on a quiet Tuesday in February but $300 on New Year's Eve.
>   Price_Calendar stores one price per room per date, letting hotels charge peak rates during holidays/events and cut prices during slow periods.
>   Without dynamic pricing, hotels lose money both ways: they undercharge (sell $300 demand at $80) or lose bookings (list $80 rooms at $300 during off-season).
>   The system reads the price from this table *at booking time* and snapshots it into the Booking record — so the guest always pays the price they originally saw, even if the hotel raises it tomorrow.
>   Alternative (one flat price per room type): simple to model but commercially unworkable for any hotel competing on Booking.com or Expedia.

### Step 3: Room Availability Check
```sql
SELECT r.room_id, r.room_type, r.capacity, p.price
FROM rooms r
JOIN room_availability a ON r.room_id = a.room_id
JOIN price_calendar p ON r.room_id = p.room_id
WHERE a.hotel_id = {id}
  AND a.date BETWEEN '2025-02-01' AND '2025-02-05'
  AND a.status IN ('Available','Booked','Maintenance')
GROUP BY r.room_id
HAVING COUNT(CASE WHEN a.status = 'Available' THEN 1 END) = {num_nights}
```

> **WHY DOUBLE BOOKING PREVENTION EXISTS? (Beginner Explanation)**
>   Imagine 500 users all see "1 room left at Hotel X, Feb 1–5" and all click "Book Now" at the same millisecond.
>   Without protection, all 500 transactions read "available," all 500 pass the check, and all 500 insert a booking for the same room — the guest arrives and there are 499 strangers with equally valid confirmations.
>   The multi-layer approach (Redis SETNX → DB FOR UPDATE → atomic transaction) funnels all 500 concurrent requests through a single gate so exactly one wins and the rest get a fast, clean rejection.
>   Why two layers? Redis is the fast bouncer (rejects in 1–2 ms, no DB load). The DB FOR UPDATE is the vault door (ACID guarantee even if Redis fails). Belt and suspenders.

> **WHY REDIS DISTRIBUTED LOCK (SETNX) EXISTS? (Beginner Explanation)**
>   Redis SETNX is like a nightclub wristband system — only one person gets the wristband for "room_123, Feb 1–5" at a time.
>   It's not the *final* safety (the DB transaction is), but it's the *fast fail* — it rejects 499 competing requests in 1–2 ms without even touching PostgreSQL.
>   Without Redis, all 500 requests would queue up waiting for the DB row lock, hammering the database and causing cascading slowdowns across every other query.
>   The 30-second auto-expiry (EX 30) means if the booking service crashes mid-flight, the lock disappears automatically — the room never stays frozen forever.
>   Alternative (only DB lock, no Redis): works but under high concurrency it turns your booking table into a bottleneck; Redis absorbs the shock first.

### Step 4: Booking Creation — THE CRITICAL PATH

```
1. SETNX lock:hotel:{hotel_id}:room:{room_id}:{checkIn}:{checkOut}
   {booking_attempt_id} EX 30
   → returns 0? → 409 "Room being booked, try again"
   → returns 1? → proceed

2. Double-check with pessimistic DB lock:
   SELECT status FROM room_availability
   WHERE room_id={id} AND date BETWEEN {checkIn} AND {checkOut}
   FOR UPDATE
   → any date not 'Available'? → DEL lock → return "Not available"

3. Transaction:
   BEGIN;
     INSERT INTO bookings (..., status='PENDING_PAYMENT');
     UPDATE room_availability SET status='Booked', booking_id={id}
       WHERE room_id={id} AND date BETWEEN {dates};
   COMMIT;

4. DEL lock (release)

5. Publish Kafka: booking.created
6. Return {bookingId, payment_url, expires_at: now()+15min}
```
> Lock auto-expires after 30s if service crashes — prevents deadlock.

> **WHY RESERVATION STATE MACHINE EXISTS? (Beginner Explanation)**
>   A booking isn't just "booked or not" — it travels through stages like a package in transit.
>   PENDING_PAYMENT = order placed, room held for 15 minutes, but no money yet (the room is reserved like a table at a restaurant when you call ahead).
>   CONFIRMED = payment received; the room is yours, keys cut.
>   CANCELLED = booking voided, room returned to inventory for other guests.
>   Each transition has strict rules: you can't go CANCELLED → CONFIRMED, and PENDING_PAYMENT auto-expires if payment doesn't arrive within 15 min.
>   Without a state machine, you'd get orphaned bookings (room marked taken, payment never collected, room stuck offline for days) or double-refund bugs when webhooks fire twice.

> **WHY IDEMPOTENCY IN PAYMENT EXISTS? (Beginner Explanation)**
>   Networks are unreliable — when you click "Pay," the request might timeout: did the charge go through or not? If you retry blindly, you get charged twice.
>   Idempotency means "same request sent N times = exactly one charge, always." Using booking_id as the key is like a restaurant receipt number: order #4521 is paid once — the kitchen won't cook it twice no matter how many times you wave the ticket.
>   Three enforcement layers work together: (1) idempotency_key sent to the payment gateway, (2) UNIQUE INDEX on payments(booking_id) in the DB so a duplicate INSERT fails gracefully, (3) webhook handler checks for existing payment before processing.
>   Without idempotency, one network hiccup = double charge = fraud dispute = very angry guest and a potential chargeback.

### Step 5: Payment with Idempotency
```
idempotency_key = booking_id  (same key → gateway returns same intent, no double charge)

Webhook handler:
  1. Validate signature
  2. SELECT * FROM payments WHERE booking_id = {id}
     → exists? → return 200 (already processed)
     → not exists?
       BEGIN;
         INSERT INTO payments (..., status='SUCCESS');
         UPDATE bookings SET status='CONFIRMED', payment_id={id};
       COMMIT;

  3. Publish: payment.success + booking.confirmed
  4. SETEX booking:{id}:expires 900 (15min TTL for payment window)
```

### Step 6: Cancellation
```
1. Validate user owns booking
2. Calc refund via cancellation_policy snapshot (stored at booking creation time)
   hours_until_checkin ≥ 24h → 100% refund
   12-24h → 50% refund
   < 12h  → 0% refund
3. BEGIN; UPDATE bookings status='CANCELLED'; UPDATE room_avail status='Available'; COMMIT;
4. Async refund via payment gateway webhook
5. Publish booking.cancelled → Notification Svc
```

### Step 7: Booking Modification (date change)
- Acquire new lock for new dates
- `SELECT ... FOR UPDATE` on new dates
- `BEGIN; release old dates → book new dates → update booking; COMMIT;`
- Charge difference or issue partial refund

---

## 7. Database Schema Highlights

### Room_Availability (most critical table)
```sql
CREATE TABLE room_availability (
  hotel_id   UUID,
  room_id    UUID,
  date       DATE,
  status     ENUM('Available','Booked','Maintenance'),
  booking_id UUID NULL,
  PRIMARY KEY (hotel_id, room_id, date)
);
CREATE INDEX idx_avail ON room_availability(room_id, date, status);
```

### Redis Key Patterns
```
lock:hotel:{hotelId}:room:{roomId}:{checkIn}:{checkOut}  EX 30   ← booking lock
search:{hash(location,filters)}                          TTL 10m  ← search cache
user:{userId}:bookings                                   TTL 5m   ← bookings cache
booking:{bookingId}:expires                              EX 900   ← payment timeout
```

### Elasticsearch Index
```json
{
  "hotel_id": "keyword",
  "name": "text",
  "location": "geo_point",
  "amenities": "keyword[]",
  "rating": "float",
  "price_range": { "min": "float", "max": "float" }
}
```
> Kept in sync via CDC: `PostgreSQL → Debezium → Kafka → ES Indexer` (1-2s lag)

---

## 8. Scaling Techniques

| Technique | Detail |
|-----------|--------|
| ES Geo Sharding | Shard by region (US/EU/Asia), 5 primary + 1 replica per region |
| Redis Distributed Lock | SETNX + EX prevents double booking, auto-release on crash |
| DB Read Replicas | 5 replicas per region, reads routed away from primary |
| CDN for Images | S3 + CloudFront, 95% cache hit, <50ms global |
| Kafka Event Streaming | Async notifications, decouples services |
| Caching Layer | Search TTL=10m, hotel details TTL=30m, user bookings TTL=5m |
| DB Partitioning | Monthly partitions on bookings table |
| Rate Limiting | 100 req/min per user (token bucket) |
| Geo Routing | Route to nearest datacenter (us-east-1 / eu-west-1 / ap-south-1) |

> **WHY CDN FOR HOTEL IMAGES EXISTS? (Beginner Explanation)**
>   A hotel in Paris has 200 room photos. If every search from Tokyo had to download those photos from a server in Paris, each image crawls across the Atlantic — 800 ms+ per request.
>   A CDN (Content Delivery Network) is like stocking that hotel's photo album in 200 post offices around the world. A user in Tokyo gets the photo from an edge node in Tokyo in under 50 ms.
>   S3 is the filing cabinet in the basement where originals live; CloudFront is the network of local photocopies at every post office.
>   With a 95% CDN cache hit rate, only 5% of image requests ever reach S3 — slashing bandwidth costs and origin server load dramatically.
>   Alternative (serve images directly from app servers): the app server spends most of its time pushing binary image data instead of processing business logic, and users outside your datacenter region get punishing latency.

---

## 9. Top Interview Q&A

### Q: How do you prevent double booking?
**Multi-layer approach:**
1. `SETNX lock:hotel:{id}:room:{id}:{checkIn}:{checkOut} EX 30` — fast rejection (1-2ms)
2. `SELECT ... FOR UPDATE` on room_availability — ACID guarantee within DB
3. `BEGIN; INSERT booking; UPDATE room_availability; COMMIT;` — atomic
4. Lock expires auto after 30s if service crashes

> Race example: User A and B both try room_123 for Feb 1-5. A's SETNX wins → B gets 409 immediately → A completes → B retries, sees "not available". No double booking.

---

### Q: Why not check availability in Elasticsearch?
- Availability changes on every booking → constant reindexing = expensive + eventual inconsistency
- ES optimized for geo/text search, not transactional data
- Pattern: ES returns hotels by location+filters → separate DB call checks availability after selection

---

### Q: How do you prevent double charging?
1. `idempotency_key = booking_id` sent to payment gateway
2. Gateway: same key within 24h → returns same payment_intent, no new charge
3. DB: `UNIQUE INDEX on payments(booking_id)` — second INSERT fails gracefully
4. Webhook: check `SELECT * FROM payments WHERE booking_id = {id}` before processing

---

### Q: How do you scale search to 100M/day?
- 100 search service instances, auto-scale at CPU >70%
- Redis caches 60-70% of searches (popular destinations)
- ES filter context (not query context) — cacheable, no scoring
- Geo-based routing → nearest ES cluster cuts latency from 500ms → 50ms
- Math: 100M/day = 1,157/sec avg → 3,500/sec peak → 100 instances × 50 req/sec = 5,000 cap

---

### Q: How do you handle cancellations?
- Snapshot `cancellation_policy` in booking at creation (user protected if hotel changes policy later)
- Calculate `hours_until_checkin` → apply tier (100% / 50% / 0%)
- Atomic: cancel booking + release room in one transaction
- Async refund via payment gateway webhook
- Publish `booking.cancelled` → notification

---

### Q: DR strategy?
- Primary: us-east-1, Warm standby: us-west-2 (streaming replication, lag <5s)
- Route53 health checks → auto failover in 2-5 min
- RPO = 5 seconds, RTO = 5 minutes
- Monthly DR drills

---

## 10. Key Numbers to Memorize

| Metric | Value |
|--------|-------|
| Scale | 50M users, 1M hotels, 10M rooms |
| Searches | 100M/day, 1,157/sec avg, 3,500/sec peak |
| Bookings | 1M/day, 11.5/sec |
| Search latency | < 500ms |
| Booking creation | < 2s |
| Redis lock TTL | 30 seconds |
| Payment timeout | 15 minutes |
| Idempotency key validity | 24 hours |
| Search cache TTL | 10 min (60-70% hit rate) |
| Hotel details cache TTL | 30 min |
| User bookings cache TTL | 5 min |
| CDN hit rate | 95% |
| DB replication lag | < 5s |
| RPO | 5 seconds |
| RTO | 5 minutes |

---

## 11. Common Pitfalls — What NOT to Say

| Wrong | Right |
|-------|-------|
| Check availability in Elasticsearch | ES for search only, PostgreSQL FOR UPDATE for availability |
| Eventual consistency for bookings | Strong consistency — ACID transaction always |
| Single Redis lock without date range | Lock key MUST include full date range: `lock:hotel:{id}:room:{id}:{checkIn}:{checkOut}` |
| Rely only on DB lock (no Redis) | Redis SETNX first (fast fail), then DB FOR UPDATE (ACID) |
| Skip idempotency on payment | Always use `booking_id` as idempotency key + DB UNIQUE constraint |
| Store cancellation policy by reference | Snapshot policy into booking at creation time |

---

## 12. Review & Rating System

### Submission Flow
```
POST /v1/reviews {hotel_id, booking_id, rating: 4.5, comment, images[]}

Validations (in order):
  1. Booking exists AND belongs to user
  2. check_out < today (can't review before stay ends)
  3. No existing review for this booking (UNIQUE on booking_id)

Steps:
  1. Upload images → S3: reviews/{review_id}/{img}.jpg → get CDN URLs
  2. INSERT INTO reviews (..., helpful_count: 0)
  3. Async background job:
       UPDATE hotels SET avg_rating = (SELECT AVG(rating) FROM reviews WHERE hotel_id={id}),
                         review_count = (SELECT COUNT(*) FROM reviews WHERE hotel_id={id})
     OR use Materialized View (better for scale):
       CREATE MATERIALIZED VIEW hotel_ratings AS
         SELECT hotel_id, AVG(rating), COUNT(*) FROM reviews GROUP BY hotel_id;
       -- refresh every 10 min
  4. CDC: hotel.avg_rating update → Kafka → ES indexer (updates search ranking)
  5. ML moderation: scan for profanity/spam/fake reviews → flag if confidence > 0.8
```

### Helpful Votes
```
POST /v1/reviews/{reviewId}/helpful → increments helpful_count

GET /v1/hotels/{hotelId}/reviews?sortBy=helpful&page=1&size=20
```

---

## 13. Overbooking & Inventory Management

### Two availability models
| Model | Schema | Tradeoff |
|-------|--------|----------|
| Row-per-date | `(room_id, date, status, booking_id)` | Simple, more rows |
| Aggregate | `(hotel_id, room_type, date, available_count, booked_count)` | Faster queries, complex updates |

### Booking flow for room_type (not specific room)
```
1. User books "Deluxe room" (type, not specific room_id)
2. Check aggregate: SELECT COUNT(*) as booked FROM room_availability
   WHERE hotel_id={id} AND room_type='Deluxe' AND date BETWEEN {dates} AND status='Booked'
   → booked_count < total_deluxe_rooms for ALL dates?

3. Acquire lock: SETNX lock:hotel:{id}:room_type:Deluxe:{dates}

4. Assign specific room:
   SELECT room_id FROM rooms
   WHERE hotel_id={id} AND room_type='Deluxe'
     AND room_id NOT IN (
       SELECT room_id FROM room_availability
       WHERE date BETWEEN {dates} AND status='Booked'
     ) LIMIT 1 FOR UPDATE

5. UPDATE room_availability SET status='Booked', booking_id={id}
   WHERE room_id={assigned_room_id} AND date BETWEEN {dates}
```

> **WHY OVERBOOKING STRATEGY EXISTS? (Beginner Explanation)**
>   Airlines and hotels know from years of data that roughly 5% of guests cancel at the last minute or simply no-show.
>   If a 100-room hotel sells exactly 100 rooms, those ~5 no-show rooms sit empty every night — pure lost revenue that can never be recovered.
>   By selling 105 rooms (5% overbook), the hotel statistically fills all 100 paid rooms. The math works in their favour almost every night.
>   The risk: occasionally all 105 guests actually show up. The mitigation is to upgrade the excess guest to a better room (the hotel absorbs the cost) or pay to relocate them to a partner hotel — which still costs far less than five nightly room losses compounding every single night of the year.
>   This is a deliberate, data-driven business policy — not a bug or a system flaw. The system models it explicitly with an overselling_limit table so it stays controlled and auditable.
>   Alternative (never overbook): guarantees no awkward walk-in situation but consistently costs the hotel thousands in empty rooms per month.

### Controlled Overbooking (like airlines)
```
overselling_limit table: {hotel_id, room_type, max_overbook_percent: 0.05}

Allow booking if: booked_count <= total_count * 1.05

Risk mitigation: if actually overbooked on check-in day,
  hotel upgrades guest OR relocates to partner hotel
```

### Race condition example
> Hotel has 20 Deluxe rooms, 18 booked, 2 available.
> User A + B both try simultaneously.
> A acquires lock → assigns room_123 → 19 booked → releases lock.
> B acquires lock → assigns room_124 → 20 booked → releases lock.
> User C tries → no rooms → "Not available".

---

> **WHY THIRD-PARTY CHANNEL MANAGER INTEGRATION EXISTS? (Beginner Explanation)**
>   A hotel doesn't only sell rooms through your app — it simultaneously lists on Booking.com, Expedia, Airbnb, and its own website at the same time.
>   A Channel Manager is the air traffic controller that keeps all these listings in sync. When a room is booked on Expedia, it fires a webhook to your system (and to Booking.com, and to the hotel's own site) to mark that room unavailable across every channel instantly.
>   Without it, the same room could be booked on three platforms in the same minute — a different kind of double booking that your internal Redis lock can't prevent because the competing request came from outside your system entirely.
>   In the architecture, the Channel Manager sits between your Booking Service and external OTA (Online Travel Agency) platforms, translating your internal room_availability updates into each platform's proprietary API format.
>   Alternative (build direct integrations with each OTA): you'd need to maintain separate adapters for Expedia's API, Booking.com's API, Airbnb's API, etc. — a Channel Manager abstracts all of that behind a single integration point.

## 14. Time Zone Handling

### Rule: Dates are local, timestamps are UTC
| Field | Type | Why |
|-------|------|-----|
| `check_in`, `check_out` | `DATE` (no time) | Hotel local date, no timezone conversion needed |
| `created_at`, `payment_deadline` | `TIMESTAMP UTC` | Absolute moment in time |
| `hotel.timezone` | `varchar(50)` | IANA tz e.g. `'Europe/London'`, `'America/New_York'` |

### Flow
```
User in California books London hotel for March 1-5:

Store:
  check_in: DATE '2025-03-01'          ← London local date
  check_out: DATE '2025-03-05'         ← London local date
  hotel_timezone: 'Europe/London'
  created_at: TIMESTAMP '2025-01-15 20:30:00 UTC'
  payment_deadline: created_at + 15min (UTC)

Display to user:
  "Booking confirmed for March 1–5, 2025 (London time)"
  "Booked on Jan 15, 2025 12:30 PM PST"

Notifications:
  "Check-in: March 1, 2025 at 3:00 PM CET"  ← explicit timezone always
```

### DST handling
- Use proper tz library (`moment-timezone` / `date-fns-tz`), NOT raw UTC offsets
- IANA database handles daylight saving automatically
- Edge case: booking made when clocks change → library handles, raw offset breaks

---

## 15. Diagram Reference

```
High-Level:
  Users → LB/Gateway → [User|Search|Review|Booking] Svcs → DBs
  Booking Svc → Payment Svc → Payment Gateway
  Kafka → Notification Svc

Low-Level adds:
  Search Svc → Elasticsearch (geo search, CDC from Hotel DB)
  Booking Svc → Redis Lock → Booking DB
  Hotel DB → Blob (S3) for images
  Room Avail Svc (checks + updates availability table)
  Kafka → Booking Consumer + Notification Svc
  Payment DB (separate from Booking DB)
```

---

## KEY PATTERNS REFERENCED IN THIS DESIGN

> **For the 2-year developer:** These are the hidden concepts behind design decisions in this system. Each has a dedicated deep-dive file.

### Optimistic vs Pessimistic Locking
**Why it matters here:** OPTIMISTIC for room availability — hotel bookings have lower contention than concert seats (fewer people booking the same specific room simultaneously). @Version on Room entity: concurrent booking attempt → OptimisticLockException → retry → re-check availability → book or show "no longer available."
**Deep dive:** `../../Optimistic_vs_Pessimistic_Locking.md`

### Idempotency Keys
**Why it matters here:** User's browser retries a hotel booking on slow connection. Without idempotency: two bookings, two charges. With Idempotency-Key per booking session: second request returns first booking confirmation.
**Deep dive:** `../../Idempotency_Keys_Prevent_Double_Processing.md`

### CAP Theorem
**Why it matters here:** Hotel booking is CP for reservation writes — don't risk double-booking during partition. AP for hotel search/availability display — slightly stale availability (room may show available but be taken) is acceptable for search; only the actual booking write must be CP.
**Deep dive:** `../../CAP_Theorem_Applied_What_Actually_Breaks.md`

### Cursor Pagination
**Why it matters here:** Hotel search results page. Users may filter and scroll through hundreds of hotels. Offset pagination at page 100 = 2000 rows scanned. Cursor pagination on (rating, hotel_id) = direct index seek.
**Deep dive:** `../../Cursor_Pagination_vs_Offset_Pagination.md`

### [Read Replica Lag & Read-Your-Own-Writes](../../Read_Replica_Lag_Read_Your_Own_Writes.md)
**Why this system uses it:** User books a hotel → immediately sees "Your Bookings" page → the new booking isn't there (replica lag). Fix: the booking API response includes the PostgreSQL LSN (log sequence number) of the write. The client sends this LSN as a header on the next read request. The read router only sends the request to a replica if that replica has applied the LSN; otherwise it routes to primary. This guarantees the booking page shows the just-created booking without always reading from primary.

### [MVCC — How PostgreSQL Reads Never Block Writes](../../MVCC_How_PostgreSQL_Reads_Never_Block_Writes.md)
**Why this system uses it:** Hotel availability page: thousands of reads per second checking if a hotel has rooms for a given date range. Booking writes (fewer but critical) simultaneously update room availability. MVCC: availability reads never block behind booking writes — each read sees a consistent snapshot. The booking transaction uses REPEATABLE READ isolation to ensure the room it's reserving hasn't been taken by a concurrent booking between the availability check and the lock acquisition (prevents phantom bookings).

### [Cache-Aside vs Write-Through vs Write-Behind](../../Cache_Aside_vs_Write_Through_vs_Write_Behind.md)
**Why this system uses it:** Hotel metadata (name, location, description, star rating, photos list): write-through cache — changes infrequently, reads are extremely frequent (every search result). When hotel manager updates their description, write to both DB and Redis cache atomically. Hotel availability: cache-aside with 30-second TTL — availability changes frequently (bookings happen constantly), short TTL keeps cache reasonably fresh. Don't cache availability for more than 60s or users will see "available" for fully-booked hotels.

### [Write Skew + Phantom Reads](../../Write_Skew_Phantom_Reads_Isolation_Levels.md)
**Why this system uses it:** Two guests simultaneously check room availability for the same hotel on the same dates. Both see "1 room available." Both book. The hotel is now double-booked — a classic write skew scenario. Fix: when a booking transaction reads available rooms, use `SELECT ... FOR UPDATE` on the room-availability row for that date range. First booking locks the row; second booking blocks until first commits. After first commits (room now booked), second reads "0 available" and returns "sold out." SERIALIZABLE isolation prevents phantom bookings (a new room entry appearing between the availability check and the reservation write).
