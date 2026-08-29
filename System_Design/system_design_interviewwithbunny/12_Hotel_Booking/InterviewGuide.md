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

---

## 6. Low-Level Design — Step by Step

### Step 1: User Registration & Auth
- `POST /v1/users/register` → validate email uniqueness → store `bcrypt(password)` → return JWT (7d) + refresh token in Redis
- Login: validate bcrypt hash → issue JWT

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
