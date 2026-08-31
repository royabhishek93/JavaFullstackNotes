# BookMyShow - System Design Interview

## Interview Level: **Senior (Production Scale)**

---

## 🎯 VISUAL ARCHITECTURE - Interview Ready

### Complete System Architecture (Memorize This!)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                     │
│  [Web App] [Mobile App] [Progressive Web App]                           │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             │ HTTPS/TLS
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│                         CDN (CloudFlare/Akamai)                          │
│  Cache: Posters, Trailers, Static Assets                                │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────────┐
│                     API GATEWAY (Kong/AWS)                               │
│  ├─ Rate Limiting (100 req/min per user)                                │
│  ├─ Authentication (JWT)                                                 │
│  ├─ Request Routing                                                      │
│  └─ Load Balancing                                                       │
└──────────┬─────────────────┬────────────────┬──────────────────────────┘
           │                 │                │
     ┌─────▼─────┐    ┌─────▼─────┐   ┌─────▼─────┐
     │  SEARCH   │    │  BOOKING  │   │  PAYMENT  │
     │  SERVICE  │    │  SERVICE  │   │  SERVICE  │
     │           │    │           │   │           │
     │ (Stateles)│    │ (Stateful)│   │  (Bridge) │
     │ Read-heavy│    │Write-heavy│   │           │
     └─────┬─────┘    └─────┬─────┘   └─────┬─────┘
           │                 │                │
           │                 │                │
┌──────────▼─────────────────▼────────────────▼──────────────────────────┐
│                        CACHE LAYER (Redis Cluster)                       │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────────┐  │
│  │ Search Cache │  │ Seat Status  │  │  Redis Pub/Sub              │  │
│  │ TTL: 5 mins  │  │ TTL: 30 secs │  │  "show:123:seats_update"    │  │
│  │              │  │              │  │                              │  │
│  │ Key:         │  │ Key:         │  │  Subscribers:                │  │
│  │ city:Mumbai  │  │ show:{id}    │  │  - WebSocket Servers         │  │
│  │ movie:Avenger│  │              │  │  - Notification Service      │  │
│  └──────────────┘  └──────────────┘  └─────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
     ┌──────▼──────┐  ┌─────▼─────┐  ┌──────▼─────────┐
     │   POSTGRES  │  │   MYSQL   │  │  ELASTICSEARCH │
     │             │  │           │  │                │
     │ Tables:     │  │ Tables:   │  │ Indices:       │
     │ - booking   │  │ - movies  │  │ - movies       │
     │ - payment   │  │ - theaters│  │ - theaters     │
     │ - users     │  │ - screens │  │ (Fast Search)  │
     │ - booking_  │  │ - cities  │  │                │
     │   seat      │  │ - reviews │  │                │
     │ - seat_     │  │           │  │                │
     │   availabil │  │           │  │                │
     │             │  │           │  │                │
     │ Sharding:   │  │ Read      │  │                │
     │ By City     │  │ Replicas  │  │                │
     └──────┬──────┘  └─────┬─────┘  └────────────────┘
            │                │
            │                │
     ┌──────▼────────────────▼──────┐
     │   MESSAGE QUEUE (Kafka/SQS)  │
     │                               │
     │  Topics:                      │
     │  - booking.confirmed          │
     │  - booking.cancelled          │
     │  - payment.success            │
     │  - seat.expired               │
     └──────┬────────────────────────┘
            │
            │ Async Processing
            │
     ┌──────▼──────────────────────────────────────┐
     │        BACKGROUND WORKERS                    │
     │                                              │
     │  ┌────────────────┐  ┌───────────────────┐ │
     │  │ Email Service  │  │ Seat Expiry Job   │ │
     │  │ (SendGrid)     │  │ (Cron: */5 mins)  │ │
     │  └────────────────┘  └───────────────────┘ │
     │                                              │
     │  ┌────────────────┐  ┌───────────────────┐ │
     │  │ SMS Service    │  │ Analytics Worker  │ │
     │  │ (Twilio)       │  │ (Process logs)    │ │
     │  └────────────────┘  └───────────────────┘ │
     └──────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              EXTERNAL SERVICES                                │
│  [Stripe/PayU] [SendGrid] [Twilio] [S3] [CloudWatch]        │
└──────────────────────────────────────────────────────────────┘
```

---

### 🎬 Seat Booking Flow (Critical Path - Draw This in Interview!)

```
USER JOURNEY: Booking Seat 5 for Show 123

Step 1: SELECT SEAT
┌──────────┐
│  User A  │ Clicks Seat 5
└────┬─────┘
     │
     │ GET /shows/123/seats
     ▼
┌─────────────┐    Cache Hit?     ┌──────────┐
│   API GW    │──────YES─────────>│  Redis   │ Return in 50ms
└─────┬───────┘                   └──────────┘
      │                                  │
      │ NO (Cache Miss)                  │
      ▼                                  │
┌──────────────┐                        │
│ Booking Svc  │ Query DB               │
└──────┬───────┘                        │
       │                                 │
       │ SELECT * FROM seat_availability │
       ▼                                 │
┌──────────────┐                        │
│  PostgreSQL  │ Return seat status     │
└──────┬───────┘                        │
       │                                 │
       └────────────Cache Update─────────┘


Step 2: INITIATE BOOKING (Acquire Lock)
┌──────────┐
│  User A  │ POST /bookings {showId:123, seatIds:[5]}
└────┬─────┘
     │
     ▼
┌──────────────────┐ BEGIN TRANSACTION
│  Booking Service │────────────────────┐
└──────────────────┘                    │
     │                                   │
     │ 1. Lock seat row                  │ ISOLATION: SERIALIZABLE
     ▼                                   │
┌──────────────────────────────────┐   │
│ SELECT * FROM seat_availability  │   │
│ WHERE show_id=123 AND seat_id=5  │   │
│ FOR UPDATE;                      │   │ ← User B waits here if trying same seat
└──────────────────────────────────┘   │
     │                                   │
     │ 2. Check if AVAILABLE             │
     ▼                                   │
  [Available?]                          │
     │                                   │
     ├─NO──> Rollback, return error     │
     │                                   │
     └─YES─> 3. Create PENDING booking  │
             INSERT INTO booking         │
             status = PENDING            │
             expires_at = NOW()+15mins   │
                                         │
             4. Update seat status       │
             UPDATE seat_availability    │
             SET status='RESERVED'       │
             reserved_until = +15mins    │
                                         │
             COMMIT ◄────────────────────┘
     │
     │ Return: {bookingId: 999, expiresIn: 15mins}
     ▼
┌──────────┐
│  User A  │ Has 15 mins to pay
└──────────┘


Step 3: PAYMENT (Critical Section)
┌──────────┐
│  User A  │ POST /bookings/999/confirm {paymentToken}
└────┬─────┘
     │
     ▼
┌──────────────────┐
│  Payment Service │
└────┬─────────────┘
     │
     │ 1. Validate booking not expired
     ▼
  [Expired?]
     │
     ├─YES─> Release seat, return error
     │
     └─NO──> 2. Call Payment Gateway (Stripe)
             │
             ▼
        ┌────────────┐
        │   Stripe   │ Charge $50
        └─────┬──────┘
              │
        [Success?]
              │
              ├─FAIL──> Release seat
              │         Mark payment FAILED
              │         Return error
              │
              └─SUCCESS─> 3. Confirm booking
                          │
                          ▼
                    BEGIN TRANSACTION
                    │
                    UPDATE booking
                    SET status='CONFIRMED'
                    payment_id = 'stripe_123'
                    │
                    UPDATE seat_availability
                    SET status='BOOKED'
                    │
                    UPDATE show
                    SET available_seats -= 1
                    │
                    COMMIT
                    │
                    4. Async Operations
                    ├─> Kafka.publish("booking.confirmed")
                    ├─> Redis.publish("show:123:update")
                    └─> Generate QR ticket
     │
     ▼
┌──────────┐
│  User A  │ Receives ticket instantly
└──────────┘


Step 4: REAL-TIME UPDATE (Other Users)
┌──────────────┐
│ Redis Pub/Sub│ show:123:update
└──────┬───────┘
       │
       │ Broadcast
       ▼
┌──────────────────┐
│ WebSocket Servers│ (3 instances subscribed)
└──────┬───────────┘
       │
       │ Push notification
       ▼
┌──────────┐
│  User B  │ Sees: Seat 5 now BOOKED (real-time)
└──────────┘


Step 5: EXPIRY CLEANUP (Background Job)
┌──────────────┐
│  Cron Job    │ Runs every 5 minutes
└──────┬───────┘
       │
       │ Find expired pending bookings
       ▼
SELECT * FROM booking
WHERE status='PENDING'
AND expires_at < NOW()
       │
       │ For each expired:
       ▼
BEGIN TRANSACTION
│
UPDATE seat_availability
SET status='AVAILABLE'
WHERE booking_id IN (...)
│
DELETE FROM booking
WHERE booking_id IN (...)
│
COMMIT
```

---

### 🔐 Concurrency Control Pattern (Draw This!)

```
USER A                          USER B
  │                              │
  │ Click Seat 5                 │ Click Seat 5
  ▼                              ▼
┌─────────────┐              ┌─────────────┐
│ BEGIN TX    │              │ BEGIN TX    │
└──────┬──────┘              └──────┬──────┘
       │                            │
       │ SELECT ... FOR UPDATE      │ SELECT ... FOR UPDATE
       ▼                            ▼
  ┌────────┐                   ┌────────┐
  │  LOCK  │◄──────ACQUIRED────│  WAIT  │ ← User B BLOCKED
  │ Seat 5 │                   │        │   until User A commits
  └────┬───┘                   └────────┘
       │
       │ Check available: YES
       │ UPDATE status='RESERVED'
       │
       ▼
  ┌────────┐
  │ COMMIT │ ← Lock released
  └────┬───┘
       │                            │
       │                            ▼
       │                      ┌────────┐
       │                      │ UNLOCK │
       │                      └────┬───┘
       │                           │
       │                           │ Check available: NO
       │                           │ ROLLBACK
       │                           ▼
       │                      [Error: Seat taken]
       ▼
  [Success: Seat reserved for 15 mins]


KEY MECHANISM: FOR UPDATE
─────────────────────────────
SELECT * FROM seat_availability
WHERE show_id = 123 AND seat_id = 5
FOR UPDATE;  ← This acquires exclusive row lock

Alternative: Optimistic Locking
─────────────────────────────
UPDATE seat_availability
SET status='BOOKED', version=version+1
WHERE seat_id=5 AND version=10;
↑ Only succeeds if version hasn't changed
```

---

### 💳 Payment Flow (3-Phase Commit)

```
┌──────────────────────────────────────────────────────────────┐
│                    PAYMENT FLOW STATES                        │
└──────────────────────────────────────────────────────────────┘

PHASE 1: RESERVE          PHASE 2: CHARGE          PHASE 3: CONFIRM
─────────────────         ───────────────          ─────────────────
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Booking    │         │   Payment    │         │   Ticket     │
│   PENDING    │────────>│   PENDING    │────────>│  CONFIRMED   │
└──────────────┘         └──────────────┘         └──────────────┘
     │                         │                        │
     │ DB Write:               │ External Call:         │ DB Update:
     │ - Create booking        │ - Stripe.charge()      │ - booking.status
     │ - Lock seats            │ - Idempotent key       │ - payment.status
     │ - Set expiry            │ - Webhook registered   │ - Send email
     │   (15 mins)             │                        │ - Generate QR
     │                         │                        │
     │ Rollback if:            │ Rollback if:           │ Async:
     │ - Seats taken           │ - Payment fails        │ - Kafka event
     │ - Show full             │ - Timeout (retry)      │ - Analytics
     │                         │ - Declined card        │ - Push notif
     │                         │                        │
     │                    ┌────▼─────┐                 │
     │                    │ WEBHOOK  │                 │
     │                    │ Confirm  │─────────────────┘
     │                    └──────────┘
     │
     └──[Timeout 15 mins]──> Auto-cancel, release seats


FAILURE SCENARIOS:
──────────────────

1. Payment Success, Server Crash Before Confirm:
   ┌────────┐  Charge OK  ┌────────┐  💥 CRASH
   │ Stripe │────────────>│ Server │
   └────────┘             └────────┘
   
   Solution: Webhook retry (exponential backoff)
   Stripe → POST /webhook/payment-success (retries 10x)

2. Double Submission (User clicks Pay twice):
   Request 1: idempotency_key = "booking_999_attempt_1"
   Request 2: idempotency_key = "booking_999_attempt_1" ← Same key
   
   Result: Stripe deduplicates, charges once

3. Network Timeout:
   Client ← × ← Server (paid successfully, response lost)
   
   Solution: Client polls GET /bookings/999/status
```

---

### 🚦 Traffic Management (Peak Load Strategy)

```
                    1M Concurrent Users (Movie Release Day)
                              │
                              ▼
                    ┌─────────────────┐
                    │  Rate Limiter   │
                    │  (Token Bucket) │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────▼─────┐  ┌────▼────┐  ┌─────▼─────┐
        │  TIER 1   │  │ TIER 2  │  │  TIER 3   │
        │ Immediate │  │ Queued  │  │ Rejected  │
        │  Accept   │  │  Wait   │  │  Retry    │
        └─────┬─────┘  └────┬────┘  └─────┬─────┘
              │              │              │
        100k users     400k users     500k users
        Process Now    Queue for 5s   HTTP 429
              │              │              │
              ▼              ▼              ▼
        ┌─────────┐    ┌─────────┐    ┌─────────┐
        │ Process │    │  Kafka  │    │ Return  │
        │ Booking │    │  Queue  │    │ "Retry  │
        │  (Sync) │    │  Topic  │    │  Later" │
        └─────────┘    └────┬────┘    └─────────┘
                            │
                            │ Async consumer
                            ▼
                       ┌─────────┐
                       │ Process │
                       │ Booking │
                       │ (Async) │
                       └─────────┘

METRICS:
─────────
Tier 1: 10% of traffic  → Sub-second response
Tier 2: 40% of traffic  → 5-second queue
Tier 3: 50% of traffic  → Graceful rejection
```

---

### 🧠 Memory Patterns (Redis Cache Keys)

```
CACHE STRUCTURE
───────────────

1. SEARCH RESULTS (Hot Data)
   Key: "search:city:{cityId}:date:{date}"
   Value: [movieId:123, movieId:456, ...]
   TTL: 300 seconds (5 mins)
   
2. SHOW AVAILABILITY
   Key: "show:{showId}:available_seats"
   Value: 150
   TTL: 30 seconds
   
3. SEAT MAP (Critical)
   Key: "show:{showId}:seats"
   Value: {
     "seat_1": "AVAILABLE",
     "seat_2": "BOOKED",
     "seat_5": "RESERVED"
   }
   TTL: 30 seconds
   Pattern: Write-through cache (update on every booking)

4. THEATER INFO
   Key: "theater:{theaterId}"
   Value: {name, address, amenities, ...}
   TTL: 3600 seconds (1 hour)

5. USER SESSION
   Key: "session:{userId}"
   Value: {cart: [seat_5], expiresAt: ...}
   TTL: 900 seconds (15 mins)


CACHE INVALIDATION STRATEGY
────────────────────────────
Event: Seat Booked
│
├─> Update Redis: show:{showId}:seats
├─> Decrement: show:{showId}:available_seats
└─> Publish: Redis Pub/Sub → "show:{showId}:update"
            │
            └─> All WebSocket servers receive
                │
                └─> Push to connected clients
```

---

### 📊 Database Sharding Strategy

```
SHARD BY CITY (Horizontal Partitioning)
────────────────────────────────────────

┌─────────────────────────────────────────────────┐
│              Application Layer                   │
│         (Routing by city_id hash)               │
└────────┬──────────────┬─────────────┬───────────┘
         │              │             │
    ┌────▼────┐    ┌───▼─────┐  ┌───▼─────┐
    │ Shard 1 │    │ Shard 2 │  │ Shard 3 │
    │ Mumbai  │    │  Delhi  │  │ Bangalore│
    │ Pune    │    │ Gurgaon │  │ Hyderabad│
    └─────────┘    └─────────┘  └─────────┘
        │              │             │
    Cities 1-10    Cities 11-20  Cities 21-30

WHY CITY SHARDING?
──────────────────
✓ User always searches in ONE city (locality)
✓ No cross-shard joins needed
✓ Easy to add new cities (new shard)
✓ Theater capacity tied to city geography


WHAT STAYS GLOBAL?
──────────────────
- Users table (small, <100M records)
- Movies table (small, ~10k active movies)
- Reviews (can be sharded by movie_id)
```

---

### ⏱️ Critical Latency Breakdown

```
USER CLICKS "SEARCH MOVIES IN MUMBAI"
──────────────────────────────────────
Total Budget: 200ms

┌──────────────────┬──────────┬─────────────────────┐
│     Component    │  Latency │   Optimization      │
├──────────────────┼──────────┼─────────────────────┤
│ CDN (if cached)  │   10ms   │ CloudFlare edge     │
│ API Gateway      │   20ms   │ Nginx, no auth      │
│ Redis Cache      │   50ms   │ In-memory, cluster  │
│ Elasticsearch    │   80ms   │ Pre-indexed         │
│ PostgreSQL       │  100ms   │ Read replica        │
│ Network overhead │   40ms   │ Same region         │
└──────────────────┴──────────┴─────────────────────┘

PATH 1 (Cache Hit):   CDN → Gateway → Redis = 80ms ✅
PATH 2 (Cache Miss):  CDN → Gateway → ES = 150ms ✅
PATH 3 (DB Query):    CDN → Gateway → Postgres = 160ms ✅


USER CLICKS "BOOK SEAT 5"
──────────────────────────
Total Budget: 1000ms (1 second)

┌──────────────────┬──────────┐
│     Component    │  Latency │
├──────────────────┼──────────┤
│ API Gateway      │   20ms   │
│ Lock acquisition │   50ms   │
│ DB write (txn)   │  200ms   │
│ Payment call     │  500ms   │ ← Stripe API
│ Confirmation     │  100ms   │
│ Cache update     │   30ms   │
│ Kafka publish    │   50ms   │
│ WebSocket push   │   50ms   │
├──────────────────┼──────────┤
│ TOTAL            │ 1000ms   │
└──────────────────┴──────────┘
```

---

## 🗄️ DATABASE TECHNOLOGY CHOICES - Why Each DB?

### PostgreSQL - For Bookings & Transactional Data

**Why PostgreSQL?**

```
USE CASE: booking, payment, seat_availability, booking_seat
```

**Reasons:**

1. **ACID Compliance (Critical!)**
   - Bookings require STRONG consistency
   - Payment atomicity is non-negotiable
   - No partial bookings allowed (seat reserved but payment failed)
   
2. **Advanced Locking Mechanisms**
   ```sql
   SELECT * FROM seat_availability 
   WHERE seat_id = 5 
   FOR UPDATE;  ← Row-level locks prevent race conditions
   ```
   - PostgreSQL's `FOR UPDATE` is battle-tested
   - Supports SERIALIZABLE isolation level
   - Deadlock detection and resolution

3. **JSONB Support**
   ```sql
   -- Store seat metadata flexibly
   SELECT * FROM seats 
   WHERE metadata @> '{"wheelchair_accessible": true}';
   ```
   - Efficient JSON querying (indexed JSONB)
   - Schema flexibility for seat amenities

4. **Write-Heavy Workload**
   - Bookings are constant writes (50k/min at peak)
   - Excellent WAL (Write-Ahead Logging) performance
   - Better write throughput than MySQL for concurrent writes

5. **Foreign Key Constraints**
   - Prevents orphaned booking_seat records
   - Cascading deletes on booking cancellation
   - Referential integrity is critical for financial data

**Interview Answer:**
> "I chose PostgreSQL for bookings because it offers superior ACID guarantees and row-level locking with `FOR UPDATE`, which is essential to prevent double-booking race conditions. Financial transactions demand strong consistency, and PostgreSQL's SERIALIZABLE isolation level ensures no lost updates during concurrent seat reservations."

---

### MySQL - For Movies & Theater Catalog Data

**Why MySQL?**

```
USE CASE: movies, theaters, screens, seats, cities, reviews
```

**Reasons:**

1. **Read-Heavy Workload**
   - Movie/theater data is read 1000x more than written
   - MySQL has excellent read performance with query cache
   - Read replicas scale horizontally for search queries

2. **Simpler Schema (No Complex Transactions)**
   ```sql
   -- Theater data doesn't need SERIALIZABLE isolation
   SELECT * FROM theaters WHERE city_id = 1;
   SELECT * FROM movies WHERE genre = 'Action';
   ```
   - Movie metadata rarely changes (write once, read millions)
   - No multi-row transactions needed
   - Eventual consistency is acceptable

3. **Mature Replication**
   - Master-slave replication is rock-solid in MySQL
   - Easy to add 10+ read replicas
   - Route all search queries to replicas (reduce master load)

4. **Lower Operational Cost**
   - MySQL is lighter weight for static catalog data
   - Less memory footprint per connection
   - Cheaper to run large replica sets

5. **JSON Support (MySQL 8.0+)**
   ```sql
   -- Store theater amenities
   SELECT * FROM theaters 
   WHERE JSON_CONTAINS(amenities, '["IMAX"]');
   ```
   - MySQL 8.0+ supports JSON columns efficiently
   - Good enough for catalog metadata

**Interview Answer:**
> "I chose MySQL for the movie catalog because it's a read-heavy workload—users search for movies far more often than theaters add new shows. MySQL's mature replication story lets me scale reads horizontally with 10+ replicas. Since theater/movie data doesn't require complex transactions or strong locking, MySQL's simpler model and lower operational cost made it the better fit."

---

### Elasticsearch - For Full-Text Search & Filters

**Why Elasticsearch?**

```
USE CASE: Search movies/theaters by text, genre, location, filters
```

**Reasons:**

1. **Full-Text Search**
   ```json
   // User types: "avengers endgame mumbai"
   GET /movies/_search
   {
     "query": {
       "multi_match": {
         "query": "avengers endgame",
         "fields": ["title^3", "synopsis", "actors"]
       }
     },
     "filter": {
       "term": { "city": "Mumbai" }
     }
   }
   ```
   - Tokenization, stemming, relevance scoring
   - MySQL `LIKE %term%` is too slow for fuzzy matching
   - Sub-50ms search latency (with proper indexing)

2. **Faceted Search (Filters)**
   ```
   User selects:
   ├─ Genre: Action, Thriller
   ├─ Language: Hindi, English
   ├─ Rating: 4+ stars
   └─ Distance: < 5km
   
   ES aggregates instantly (no multiple joins)
   ```
   - Complex filters (genre + language + rating + geo) in single query
   - SQL requires multiple joins → slow at scale
   - ES pre-computes aggregations

3. **Geo-Spatial Queries**
   ```json
   // Find theaters within 5km of user location
   GET /theaters/_search
   {
     "query": {
       "geo_distance": {
         "distance": "5km",
         "location": {
           "lat": 19.0760,
           "lon": 72.8777
         }
       }
     }
   }
   ```
   - PostgreSQL has PostGIS, but ES is faster for this use case
   - Returns sorted by distance (built-in)

4. **Denormalized Data (No Joins)**
   ```json
   // Single ES document contains everything
   {
     "movieId": 123,
     "title": "Avengers: Endgame",
     "genres": ["Action", "Sci-Fi"],
     "theaters": [
       {"theaterId": 1, "name": "PVR Phoenix", "distance": "2.3km"},
       {"theaterId": 2, "name": "INOX Megaplex", "distance": "4.1km"}
     ],
     "showtimes": ["10:00", "13:30", "18:00"]
   }
   ```
   - No joins needed (everything in one doc)
   - Sacrifice consistency for speed (eventual sync from MySQL)
   - Acceptable for search (if 30s stale data is OK)

5. **Scalability for Search**
   - Horizontal scaling with shards (shard by city)
   - Replica shards for high availability
   - Search across 100M documents in < 100ms

**Data Sync Strategy:**
```
MySQL (Source of Truth)
   │
   │ Trigger on INSERT/UPDATE
   ▼
┌──────────────┐
│ Kafka Topic  │ "theater.updated"
└──────┬───────┘
       │
       │ Consumer
       ▼
┌──────────────┐
│ ES Indexer   │ Update ES document
└──────────────┘

Lag: < 5 seconds (acceptable for search)
```

**Interview Answer:**
> "I chose Elasticsearch for search because it's purpose-built for full-text search with tokenization and relevance ranking—something SQL databases struggle with. When users search 'avengers mumbai near me', ES handles text matching, geo-spatial filtering, and faceted aggregations in a single query under 100ms. We sync data from MySQL to ES asynchronously via Kafka with ~5 second lag, which is acceptable for search workloads where eventual consistency is fine."

---

### 🆚 Database Comparison Summary

| Feature | PostgreSQL | MySQL | Elasticsearch |
|---------|-----------|-------|---------------|
| **Primary Use** | Bookings, Payments | Movies, Theaters | Full-text Search |
| **Workload** | Write-heavy | Read-heavy | Read-heavy |
| **Consistency** | ACID (Strict) | ACID (Relaxed) | Eventual |
| **Locking** | Row-level (FOR UPDATE) | Table/Row locks | None (read-only) |
| **Transaction** | SERIALIZABLE | READ COMMITTED | Not transactional |
| **Joins** | Excellent | Good | None (denormalized) |
| **Full-text Search** | Basic (tsvector) | Basic (FULLTEXT) | Advanced ⭐ |
| **Geo-spatial** | PostGIS (good) | Limited | Built-in ⭐ |
| **JSON Support** | JSONB ⭐ | JSON (MySQL 8+) | Native |
| **Scalability** | Vertical + Sharding | Read replicas ⭐ | Horizontal ⭐ |
| **Use Cases** | Financial, Bookings | Catalogs, Metadata | Search, Analytics |

---

### 🎯 Interview Question: "Why not use one database for everything?"

**Answer:**

1. **Different Consistency Requirements**
   - Bookings need SERIALIZABLE (PostgreSQL)
   - Movie search tolerates eventual consistency (Elasticsearch)
   - Wrong tool = over-engineering or under-reliability

2. **Optimized for Different Workloads**
   - PostgreSQL: Concurrent writes with locking
   - MySQL: Massive read scaling (replicas)
   - Elasticsearch: Sub-100ms full-text search

3. **Cost Efficiency**
   - Running PostgreSQL with SERIALIZABLE for all reads = expensive
   - ES search is 10x faster than SQL `LIKE` queries
   - MySQL read replicas are cheaper than PostgreSQL for static data

4. **Blast Radius**
   - If search goes down, bookings still work
   - If booking DB has issues, search remains functional
   - Microservices principle: separate concerns

**Trade-off:**
- More databases = more operational complexity
- Need data synchronization (MySQL → ES via Kafka)
- Acceptable lag: 5 seconds for search, 0 seconds for booking

**Alternative (Not Recommended):**
- Single PostgreSQL for everything
- ❌ Search will be slow (no inverted index for full-text)
- ❌ Read replicas for search can lag (replication delay)
- ❌ Single point of failure
- ❌ Over-provisioning for mixed workload

---

## Scenario

**You're designing a movie booking platform like BookMyShow.** A user opens the app, searches for a movie in their city, sees available theaters and showtimes, selects seats, and completes payment within 10 minutes. Meanwhile, 50,000 concurrent users are doing the same during peak hours. How do you ensure:
- No double bookings of the same seat
- Payment atomicity (seats reserved OR payment fails, never both)
- Sub-200ms response times for "search theaters near me"
- Real-time seat availability updates
- Handling 10x traffic spikes during movie releases

---

## 🔥 MUST KNOW - Core Concepts

### Functional Requirements
- **Search** - Movies by city, title, showtime, genre
- **Browse Theaters** - Filter by location, amenities, ratings
- **Book Seats** - Select multiple seats, real-time availability
- **Payment** - Multiple modes (credit card, wallet, UPI)
- **Confirmation** - Instant ticket generation & email
- **Cancellation** - Refund logic, cancellation deadline
- **Reviews** - Ratings for movies and theaters

### Non-Functional Requirements
| Category | Target | Notes |
|----------|--------|-------|
| Latency (search) | < 200ms | 99th percentile |
| Latency (booking) | < 1s | Including payment |
| Availability | 99.9% | Theater ops criticality |
| Consistency | Strong (booking) | Weak (search results) |
| QPS at Scale | 100k concurrent users | 50k write /min during peak |

---

## ✅ SHOULD KNOW - Data Model

### Core Entities

#### **CITY**
```
CityId (PK)
name
state
latitude, longitude
```

#### **THEATER** 
```
TheatersId (PK)
city_id (FK)
name
address
latitude, longitude
amenities (JSON: IMAX, Dolby, Wheelchair-accessible)
total_screens
rating
```

#### **SCREEN**
```
ScreenId (PK)
theater_id (FK)
name (e.g., "Screen 1 - IMAX")
total_rows (e.g., 20)
seats_per_row (e.g., 30)
screen_type (IMAX, 3D, Standard)
```

#### **SEAT**
```
SeatId (PK)
screen_id (FK)
row_number (A-Z)
seat_number (1-30)
seat_type (NORMAL, PREMIUM, RECLINER)
price_multiplier (1.0, 1.5, 2.0)
```

#### **MOVIE**
```
MovieId (PK)
title
genre
duration_mins
release_date
language
rating (U/A, 12A, 15, 18)
poster_url
producer, director (JSON array)
synopsis
```

#### **SHOW** ⭐ Critical
```
ShowId (PK)
screen_id (FK)
movie_id (FK)
start_time
end_time
available_seats (counter, denormalized)
total_seats
show_date
price_per_seat
is_running (boolean for quick filtering)
```

#### **BOOKING** ⭐ Critical (Transactional)
```
BookingId (PK, UUID)
user_id (FK)
show_id (FK)
total_seats
total_price
booking_status (PENDING, CONFIRMED, CANCELLED)
created_at
expires_at (15 mins, for seat hold)
payment_id (FK, nullable until confirmed)
```

#### **BOOKING_SEAT**
```
booking_seat_id (PK)
booking_id (FK)
seat_id (FK)
```

#### **SEAT_AVAILABILITY** ⭐ Cache/Index
```
show_id, seat_id (PK)
status (AVAILABLE, RESERVED, BOOKED)
reserved_until (timestamp, 15-min hold)
booking_id (FK, if BOOKED)
```

#### **PAYMENT**
```
PaymentId (PK, UUID)
booking_id (FK)
user_id (FK)
amount
payment_mode (CREDIT_CARD, DEBIT_CARD, WALLET, UPI)
transaction_id (from gateway)
status (PENDING, SUCCESS, FAILED, REFUNDED)
created_at
processed_at (nullable)
```

#### **USER**
```
UserId (PK)
email
phone
name
created_at
preferences (JSON: preferred languages, genres)
wallet_balance (for quick payments)
```

#### **REVIEW**
```
ReviewId (PK)
user_id (FK)
movie_id (FK)
rating (1-5)
comment
created_at
```

---

## 👍 GOOD TO KNOW - System Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────┐
│                   Client (Web/Mobile)                    │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
    │  Search │    │  Booking│    │ Payment │
    │  API    │    │  API    │    │  API    │
    │(Read)   │    │(Write)  │    │(Write)  │
    └─────────┘    └─────────┘    └─────────┘
         │               │               │
    ┌────▼───────────────▼───────────────▼─────┐
    │         Load Balancer (Nginx)             │
    └────────────────────┬──────────────────────┘
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
    │  Search │    │  Booking│    │ Payment │
    │ Service │    │ Service │    │ Service │
    │(Multiple)    │(Multiple)    │ Bridge  │
    └────┬────┘    └────┬────┘    └────┬────┘
         │               │               │
    ┌────▼───────────────▼───────────────▼─────┐
    │   Cache Layer (Redis)                     │
    │   - Show availability                     │
    │   - Seat status (hot)                     │
    │   - Search results                        │
    └────────────────────┬──────────────────────┘
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
    │  MySQL  │    │ Postgres│    │ Payment │
    │(Movies, │    │(Booking,│    │ Gateway │
    │ Theaters)    │ Users)  │    │ (Stripe)│
    └─────────┘    └─────────┘    └─────────┘
```

### Seat Availability - Hot Path ⭐

**Problem**: 50k users checking seat availability simultaneously = database overload

**Solution**: Multi-tier caching + eventual consistency

```
User clicks "Check Seats"
    │
    ├─→ Cache (Redis) - 50ms
    │   └─→ If miss: Query from DB (500ms)
    │
    ├─→ Cache key: "show:{showId}:seats"
    │   └─→ Value: JSON { seatId: status, ... }
    │
    ├─→ Update cache on every booking (pub-sub)
    ├─→ TTL: 30 seconds (acceptable for real-time)
    └─→ Fallback to DB if cache unavailable
```

---

## ⚙️ NICHE - Detailed Deep Dives

### Design Decision #1: Seat Booking Race Condition

**Scenario**: User A and User B both select Seat 5. Who gets it?

**Naive Approach** ❌
```sql
-- User A
SELECT available_seats FROM show WHERE show_id = 1;
-- Returns: 150

-- User B  
SELECT available_seats FROM show WHERE show_id = 1;
-- Returns: 150 (same!)

-- User A updates
UPDATE show SET available_seats = 149 WHERE show_id = 1;

-- User B updates
UPDATE show SET available_seats = 149 WHERE show_id = 1;
-- Now available_seats should be 148, but it's 149!
```

**Correct Approach** ✅
```sql
-- Inside a transaction
BEGIN;

-- Row-level lock (pessimistic)
SELECT available_seats FROM show 
WHERE show_id = 1 
FOR UPDATE;

-- Check if seat available
SELECT COUNT(*) FROM seat_availability 
WHERE show_id = 1 AND seat_id = 5 AND status = 'AVAILABLE' 
FOR UPDATE;

-- If count = 1, proceed:
INSERT INTO booking_seat (booking_id, seat_id) VALUES (?, 5);
UPDATE seat_availability SET status = 'BOOKED', booking_id = ? 
WHERE show_id = 1 AND seat_id = 5;

UPDATE show SET available_seats = available_seats - 1 
WHERE show_id = 1;

COMMIT;
```

**Why this works**:
- `FOR UPDATE` acquires row-level lock
- User B waits until User A commits
- Only one can update first

**Alternative: Optimistic Lock** (for scale)
```java
// In entity
@Version
private Long version;

// Update
UPDATE seat_set 
SET status = 'BOOKED', version = version + 1
WHERE show_id = ? AND seat_id = ? 
AND status = 'AVAILABLE' AND version = ?;
```

---

### Why SERIALIZABLE? (Interview Follow-up) ⭐⭐⭐

**Question**: Why not READ_COMMITTED or REPEATABLE_READ with `FOR UPDATE`?

**The Answer Depends on Context:**

#### **Isolation Level Comparison**

| Level | Dirty Read | Non-Repeatable Read | Phantom Read | Performance | Use Case |
|-------|-----------|---------------------|--------------|-------------|----------|
| READ_UNCOMMITTED | ✅ Yes | ✅ Yes | ✅ Yes | ⚡⚡⚡ | Cache-like reads (not safe) |
| READ_COMMITTED | ❌ No | ✅ Yes | ✅ Yes | ⚡⚡ | General queries (MySQL/Postgres default) |
| REPEATABLE_READ | ❌ No | ❌ No | ✅ Yes (MySQL) | ⚡ | Read-heavy with consistency needs |
| SERIALIZABLE | ❌ No | ❌ No | ❌ No | 🐢 | Financial/critical transactions |

---

### 📚 Read Phenomena Explained (For Beginners)

#### **Think of it like reading a book that someone keeps editing while you read:**

---

#### **1. DIRTY READ** - Reading someone's unfinished draft

```
SCENARIO: Checking available seats while someone is booking

Transaction A (User A):           Transaction B (User B):
─────────────────────            ─────────────────────
BEGIN;                            
UPDATE seats                      
SET available = 148               BEGIN;
(not committed yet!)              
                                  SELECT available FROM seats;
                                  Returns: 148  ← DIRTY READ!
ROLLBACK;                         
(Undo! It's 150 again)           
                                  // User B saw 148, but it never existed!
                                  // User B makes decisions based on wrong data
```

**Real-World Analogy:**
> Imagine checking your bank balance while your friend is transferring you $100. You see the updated balance ($1,100), get excited, and buy something. Then your friend's transaction fails and rolls back. Your balance is actually $1,000, but you already spent $1,100!

**Why it's bad:**
- You read data that was **NEVER truly committed**
- The other transaction might rollback
- You make decisions based on **temporary/fake data**

**Prevention:** Use READ_COMMITTED or higher

---

#### **2. NON-REPEATABLE READ** - Same row, different values

```
SCENARIO: Checking seat price twice in the same booking flow

Transaction A (Your booking):     Transaction B (Price update):
─────────────────────            ─────────────────────
BEGIN;                            
                                  
SELECT price FROM seats           
WHERE seat_id = 5;                
Returns: $10                      
                                  BEGIN;
                                  UPDATE seats 
                                  SET price = $15 
                                  WHERE seat_id = 5;
                                  COMMIT;
                                  
// 5 seconds later...             
SELECT price FROM seats           
WHERE seat_id = 5;                
Returns: $15  ← DIFFERENT!       
                                  
// Calculate total using $15      
// But user saw $10 on screen!    
COMMIT;
```

**Real-World Analogy:**
> You're shopping online. You add a $10 shirt to cart. While you're entering payment info, the store changes the price to $15. When you submit payment, you're charged $15 instead of $10. The price **of the same item** changed mid-transaction!

**Why it's bad:**
- You read the **SAME row TWICE** and got **DIFFERENT values**
- User saw price $10, but charged $15
- Inconsistent within a single transaction

**Key Difference from Dirty Read:**
- Non-repeatable read: The other transaction **COMMITTED** (real data)
- Dirty read: The other transaction **NOT committed** (temporary data)

**Prevention:** Use REPEATABLE_READ or SERIALIZABLE

---

#### **3. PHANTOM READ** - New rows appear/disappear like ghosts 👻

```
SCENARIO: Counting available seats twice

Transaction A (Booking logic):    Transaction B (New show added):
─────────────────────            ─────────────────────
BEGIN;                            
                                  
// Count how many seats available 
SELECT COUNT(*) FROM seats        
WHERE show_id = 1                 
AND status = 'AVAILABLE';         
Returns: 150 seats                
                                  BEGIN;
                                  // Theater adds 20 more seats!
                                  INSERT INTO seats 
                                  VALUES (show_id=1, status='AVAILABLE', ...)
                                  ×20 new rows
                                  COMMIT;
                                  
// Count again                    
SELECT COUNT(*) FROM seats        
WHERE show_id = 1                 
AND status = 'AVAILABLE';         
Returns: 170 seats  ← PHANTOM!   
// 20 "ghost" rows appeared!      
                                  
COMMIT;
```

**Real-World Analogy:**
> You walk into a theater and count 150 empty seats. You turn around to tell your friend "150 seats available." You turn back, count again, and now see 170 empty seats! Where did the extra 20 seats come from? They appeared like **phantoms** (theater staff added a new row of seats while you weren't looking).

**Why it's bad:**
- **NEW rows appeared** (or disappeared) between your reads
- You counted 150, but when you try to book based on that count, reality has changed
- Your query's **result set changed** (not just values in existing rows)

**Key Difference from Non-Repeatable Read:**
| Type | What Changed | Example |
|------|--------------|---------|
| **Non-Repeatable Read** | **Existing row's VALUE changed** | Seat 5's price: $10 → $15 |
| **Phantom Read** | **NEW rows appeared/disappeared** | 150 seats → 170 seats (20 rows added) |

**Prevention:** Use SERIALIZABLE (or REPEATABLE_READ in some databases with gap locks)

---

### 🎯 Simple Memory Trick

```
DIRTY READ → Reading someone's DRAFT (uncommitted)
   "That data might not even exist if they cancel!"
   
NON-REPEATABLE READ → Reading the SAME book twice, different words
   "Chapter 5 said 150 seats, now it says 170 seats?!"
   
PHANTOM READ → Counting books, MORE/FEWER books appear
   "I counted 10 books on shelf. Counted again: 12 books! Where did 2 come from?"
```

---

### 📖 BookMyShow Examples

#### **Example 1: DIRTY READ Problem**

```
User A booking seat 5:
├─ BEGIN transaction
├─ UPDATE seat_availability SET status='BOOKED' WHERE seat_id=5
│  (Not committed yet!)
│
│  Meanwhile, User B searches:
│  ├─ SELECT * FROM seat_availability WHERE status='AVAILABLE'
│  └─ Doesn't see seat 5 (thinks it's booked)
│
└─ ROLLBACK (User A's payment failed!)

Result: Seat 5 is available, but User B never saw it!
```

**Solution:** READ_COMMITTED prevents User B from seeing uncommitted "BOOKED" status

---

#### **Example 2: NON-REPEATABLE READ Problem**

```
User's booking flow (single transaction):

Step 1: Check price
SELECT price FROM seats WHERE seat_id = 5;
Returns: $10
↓
Show user: "Total: $10"
↓
User clicks "Pay $10"
↓
Step 2: Deduct from wallet (5 mins later)
SELECT price FROM seats WHERE seat_id = 5;
Returns: $15  ← Theater updated price!
↓
Deduct $15 from wallet (user expected $10!)
```

**Solution:** REPEATABLE_READ locks the row after first read, prevents price changes

---

#### **Example 3: PHANTOM READ Problem**

```
Admin dashboard checking "shows with < 10 seats available":

BEGIN;

// First query
SELECT show_id, available_seats 
FROM shows 
WHERE available_seats < 10;

Returns:
- Show 123: 8 seats
- Show 456: 5 seats
Total: 2 shows
↓
Admin prints report: "2 critical shows"
↓
// 10 seconds later, query again in same transaction
SELECT show_id, available_seats 
FROM shows 
WHERE available_seats < 10;

Returns:
- Show 123: 8 seats
- Show 456: 5 seats
- Show 789: 3 seats  ← PHANTOM! New show appeared
Total: 3 shows

COMMIT;
```

**Why it happened:**
- Between 1st and 2nd query, Show 789 sold tickets (went from 12 → 3 seats)
- Now it matches `WHERE available_seats < 10`
- A **NEW row entered your result set** (phantom)

**Solution:** SERIALIZABLE prevents new rows from appearing in range queries

---

### 🧠 Interview Quick Reference

| Read Issue | What Happened | Who Changed What | Prevention |
|-----------|---------------|------------------|------------|
| **Dirty Read** | Read uncommitted data that might rollback | Other transaction wrote but didn't commit | READ_COMMITTED |
| **Non-Repeatable Read** | Same row, different value | Other transaction updated a row you read | REPEATABLE_READ |
| **Phantom Read** | New rows in your result set | Other transaction inserted/deleted rows matching your query | SERIALIZABLE |

**Mnemonic:**
- **Dirty** = "Draft" (uncommitted)
- **Non-Repeatable** = "Number changed" (same row, new value)
- **Phantom** = "Population changed" (new rows appeared)

#### **Why READ_COMMITTED + FOR UPDATE Usually Works** ✅

```sql
-- With READ_COMMITTED isolation level
BEGIN;

-- Row-level lock (pessimistic)
SELECT available_seats FROM show 
WHERE show_id = 1 
FOR UPDATE;  -- ← This is the key! Prevents dirty reads

-- At this point:
-- User B trying same query BLOCKS until User A commits/rolls back
-- User B will see User A's committed changes

SELECT COUNT(*) FROM seat_availability 
WHERE show_id = 1 AND seat_id = 5 AND status = 'AVAILABLE' 
FOR UPDATE;

-- If available, book it
INSERT INTO booking_seat (...) VALUES (...);
UPDATE seat_availability SET status = 'BOOKED' WHERE ...;

COMMIT;
```

**Why it works**: `FOR UPDATE` creates a **row-level lock** that:
- Blocks other readers from acquiring the same lock
- Forces other transactions to wait for Lock Release
- Ensures they see your committed changes (no dirty reads)

---

#### **So When Do You Need SERIALIZABLE?** 🔍

**Scenario 1: Non-Adjacent Row Reads (Phantom Reads)**

```java
// Transaction A: Book seats 5-8 as a group
BEGIN;
SELECT * FROM seat_availability 
WHERE show_id = 1 AND seat_id IN (5,6,7,8)
FOR UPDATE;
// ← Locks only rows 5,6,7,8

// Transaction B (concurrent): Book seats 9-12 as a group
SELECT * FROM seat_availability 
WHERE show_id = 1 AND seat_id IN (9,10,11,12)
FOR UPDATE;
// ← Locks only rows 9,10,11,12

// NO CONFLICT! Both proceed independently (even with SERIALIZABLE, they're different rows)
```

**Scenario 2: Range Queries (requires SERIALIZABLE)**

```java
// Transaction A: Check total available seats
BEGIN;
SELECT COUNT(*) as available_count FROM seat_availability 
WHERE show_id = 1 AND status = 'AVAILABLE';
// Returns: 150

// Between A's read and A's check, Transaction B inserts a new AVAILABLE seat:
INSERT INTO seat_availability VALUES (1, 999, 'AVAILABLE', NULL, NULL);

// Transaction A continues:
if (available_count > 100) {
    // Insert booking... COMMIT;
}

// PROBLEM: available_seats count changed between read and decision!
// THIS IS PHANTOM READ - read_committed + FOR UPDATE doesn't prevent it
// (You need SERIALIZABLE or gap locks)
```

---

#### **Production Reality: What You Actually Use** 🏭

**Best Practice** (What Netflix/Amazon/Uber use):

```java
// MySQL InnoDB default is REPEATABLE_READ
// Use explicit locking, NOT isolation level changes:

@Transactional(isolation = Isolation.REPEATABLE_READ)  // Default anyway
public BookingResponse bookSeats(BookingRequest request) {
    
    // **Lock the specific rows you're modifying**
    // This is more important than isolation level!
    
    // Step 1: Lock show row
    Show show = showRepository.findByIdForUpdate(request.getShowId());
    // ← Natural language: "Find and lock this row"
    
    // Step 2: Lock seats
    List<Seat> seats = seatRepository.findByIdsForUpdate(request.getSeatIds());
    
    // Step 3: Check availability
    if (seats.stream().anyMatch(s -> s.getStatus() != AVAILABLE)) {
        throw new SeatNotAvailableException();
    }
    
    // Step 4: Update atomically
    booking.setStatus(PENDING);
    booking.setExpiresAt(LocalDateTime.now().plusMinutes(15));
    bookingRepository.save(booking);
    
    seatRepository.updateStatusBatch(request.getSeatIds(), RESERVED);
    show.decrementAvailableSeats(seats.size());
    
    return BookingResponse.from(booking);
}
```

**Repository Implementation**:

```java
@Repository
public interface SeatRepository extends JpaRepository<Seat, Long> {
    
    // ← Explicit FOR UPDATE in query
    @Query("SELECT s FROM Seat s WHERE s.id IN ?1 FOR UPDATE")
    List<Seat> findByIdsForUpdate(List<Long> seatIds);
    
    // Alternative: Pessimistic locking annotation
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT s FROM Seat s WHERE s.id IN ?1")
    List<Seat> findByIds(List<Long> seatIds);
}
```

---

#### **Why You DON'T Need SERIALIZABLE Everywhere** 🚫

**Performance Cost of SERIALIZABLE**:

| Operation | READ_COMMITTED + FOR UPDATE | SERIALIZABLE |
|-----------|--------------------------|--------------|
| Booking confirmation time | ~50ms | ~150-300ms |
| Lock wait time (high concurrency) | 10ms avg | 50-100ms avg |
| Deadlock rate | 0.01% | 5-10% |
| Throughput (1000 concurrent users) | 10,000 bookings/sec | 2,000 bookings/sec |

**Real numbers from production**:
- Stripe uses READ_COMMITTED + explicit locks
- Google Cloud Spanner uses READ_COMMITTED + locking
- PostgreSQL 98% of cases: READ_COMMITTED + FOR UPDATE
- SERIALIZABLE reserved for extreme cases (mutual fund transfers, nuclear power plant control)

---

#### **Interview Answer Format** 📋

**"Why SERIALIZABLE in the diagram?"**

> I showed SERIALIZABLE for educational clarity to emphasize strong consistency. **In production, we'd actually use READ_COMMITTED + explicit row-level locking (FOR UPDATE) because:**
> 
> 1. **Row-level locks (FOR UPDATE) prevent the actual race condition** - Two users can't lock the same seat row simultaneously
> 2. **SERIALIZABLE is overkill** - It prevents phantom reads we don't have (we're locking specific rows, not ranges)
> 3. **Performance** - SERIALIZABLE reduces booking throughput by 5x and increases deadlocks
> 4. **Complexity** - More deadlocks with SERIALIZABLE require retry logic we don't need
>
> **The locks matter more than isolation level:**
> ```
> SERIALIZABLE + no locks = Still unsafe (missing explicit locking)
> READ_COMMITTED + FOR UPDATE = Safe (what we actually use)
> ```

---

#### **When WOULD You Need SERIALIZABLE?** 🎯

```java
// Example: "Calculate average price across all theaters and make a business decision"
@Transactional(isolation = Isolation.SERIALIZABLE)
public PricingDecision recalculatePricing() {
    
    // This reads from 1000+ rows across different theaters
    double avgPrice = seatRepository.calculateAveragePrice();
    // If avg < $10, reduce inventory in high-demand theaters
    
    if (avgPrice < 10) {
        // ... update logic ...
    }
    // Problem: Between avgPrice read and update, 100 new bookings 
    // happened that changed avgPrice
    // SERIALIZABLE prevents this
}
```

But even here, you'd usually use:
- **Snapshot isolation** (PostgreSQL)
- **Versioning** (calculate with point-in-time snapshot)
- Or just accept eventual consistency



---

### Design Decision #2: Payment Atomicity

**Scenario**: Payment succeeds, but crash before saving booking confirmation. User charged, no ticket!

**3-Phase Commit Pattern**:

```
PHASE 1: RESERVE
├─ Lock seats (hold for 15 mins)
├─ Generate unique BookingId
└─ Status: PENDING

PHASE 2: PAYMENT
├─ Call Stripe/PayU
├─ On success: Mark PAYMENT_SUCCESS
├─ On failure: Release seat lock (status → RELEASED)
└─ Log transaction

PHASE 3: CONFIRM
├─ Create ticket
├─ Send confirmation email
├─ Status: CONFIRMED
└─ Release row lock
```

**Code Pattern**:
```java
@Transactional(isolation = Isolation.SERIALIZABLE)
public BookingResponse bookSeats(BookingRequest request) {
    // Phase 1: Reserve
    Booking booking = new Booking();
    booking.setStatus(BookingStatus.PENDING);
    booking.setSeats(request.getSeats());
    booking.setExpiresAt(LocalDateTime.now().plusMinutes(15));
    bookingRepository.save(booking); // DB write
    
    // Phase 2: Payment
    PaymentResult result = paymentGateway.charge(
        booking.getId(), 
        request.getAmount()
    );
    
    if (!result.isSuccess()) {
        // Automatic rollback via @Transactional
        throw new PaymentFailedException();
    }
    
    // Phase 3: Confirm
    booking.setStatus(BookingStatus.CONFIRMED);
    booking.setPaymentId(result.getPaymentId());
    bookingRepository.save(booking);
    
    emailService.sendConfirmation(booking);
    
    return BookingResponse.from(booking);
}
```

---

### Design Decision #3: Real-time Seat Updates

**Problem**: User A books Seat 5, but User B's screen still shows "Available"

**WebSocket + Redis Pub/Sub**:

```
┌─────────────────────────────────┐
│  Service (Seat Booked Event)    │
└──────────────┬──────────────────┘
               │
          Redis PUBLISH
       "show:123:seats_update"
               │
      ┌────────┼────────┐
      │        │        │
   ┌──▼──┐ ┌──▼──┐ ┌─▼───┐
   │WS-1 │ │WS-2 │ │WS-3 │
   │(Sub)│ │(Sub)│ │(Sub)│
   └──┬──┘ └──┬──┘ └──┬──┘
      │       │       │
   Browser Browser Browser
   (Real-time update)
```

**Implementation**:
```java
// Booking Service
public void bookSeats(Booking booking) {
    // ... save booking ...
    
    // Publish to Redis
    redisTemplate.convertAndSend(
        "show:" + booking.getShowId() + ":update",
        new SeatUpdateEvent(booking.getShowId(), booking.getSeats())
    );
}

// WebSocket Service (Subscriber)
@Component
@Slf4j
public class SeatUpdateListener implements MessageListener {
    @Override
    public void onMessage(Message message, byte[] pattern) {
        String channelName = new String(pattern);
        String payload = new String(message.getBody());
        
        // Notify all connected clients for this show
        Long showId = extractShowId(channelName);
        socketService.broadcastToRoom(showId, payload);
    }
}
```

---

### Design Decision #4: Handling Peaks & Scaling

**Scenario**: New Avengers movie releases. 1M concurrent users, 500k trying to book.

**Strategy: Load Shedding + Queue**

```
                Peak Requests → Load Balancer
                       │
        ┌──────────────┼──────────────┐
        │              │              │
      Tier1          Tier2         Tier3
    (Available)    (Queued)       (Rejected)
        │              │              │
    Accept         Wait Queue     HTTP 429
  Immediately     (SQS/Kafka)    (Rate limit)
        │              │              │
      Process      Process        Return error
      within 1s    within 5s       "Try later"
        │              │              │
      ✅ Ticket      ✅ Ticket      ❌ Retry
```

**Code**:
```java
@RestController
public class BookingController {
    
    @PostMapping("/book")
    public ResponseEntity<?> bookSeats(@RequestBody BookingRequest request) {
        // Check rate limits
        if (!rateLimiter.allowRequest(request.getUserId())) {
            return ResponseEntity.status(429)
                .body("Too many requests. Try booking_queue endpoint");
        }
        
        // Try immediate processing
        if (processingQueue.size() < CAPACITY) {
            return processBooking(request); // Sync
        }
        
        // Queue it
        Long queueId = asyncQueue.enqueue(request);
        return ResponseEntity.accepted()
            .body(Map.of("queueId", queueId, "status", "QUEUED"));
    }
    
    @GetMapping("/queue/{queueId}")
    public ResponseEntity<?> checkQueueStatus(@PathVariable Long queueId) {
        QueueItem item = asyncQueue.get(queueId);
        return ResponseEntity.ok(item); // PENDING or CONFIRMED
    }
}
```

---

### Design Decision #5: Seat Expiry (Holds)

**Scenario**: User selects seats but abandons checkout. Should we keep seats reserved?

**Answer**: 15-minute hold with background cleanup

```
User selects Seat 5 (time: 10:00 AM)
    └─→ booking_status = PENDING
    └─→ reserved_until = 10:15 AM
    
At 10:16 AM:
    └─→ Batch job checks: SELECT * FROM booking WHERE status=PENDING AND reserved_until < NOW()
    └─→ For each expired booking:
        ├─ UPDATE seat_availability SET status='AVAILABLE' WHERE booking_id = ?
        ├─ DELETE FROM booking WHERE booking_id = ?
        └─ Notify user "Seats released due to inactivity"
```

---

## Interview Q&A

### Q1: How do you prevent double booking of the same seat?

**Answer**: 
- Use **row-level locking** (`FOR UPDATE`) in database
- In a transaction, lock the seat row before checking availability
- If available, insert booking_seat record
- Only one transaction can acquire lock at a time
- Alternative: **Optimistic locking** with version field for high concurrency

---

### Q2: If 2 users try to pay for the same seats simultaneously, who gets charged?

**Answer**:
- User 1 gets lock first, books seats, commits
- User 2's transaction rolls back because seat is no longer available
- Payment gateway charges are idempotent (same txn_id = no charge)
- Refund automaton handles failed bookings

---

### Q3: How do you handle payment gateway failures?

**Answer**:
- Payment is idempotent (unique idempotency_key)
- If timeout: poll gateway for transaction status (exponential backoff)
- If failed: release seat hold automatically
- Webhook from payment gateway confirms final status (not our API)
- Retry logic: max 3 attempts with exponential backoff

---

### Q4: Movie releases at 10 AM. You expect 1M concurrent users. Design for it.

**Answer**:
1. **Pre-booking** - Open pre-booking 1 week before
2. **Queue System** - Accept 10k requests/sec, queue rest (300k/sec capacity)
3. **Rate Limiting** - 5 bookings per user per day
4. **Cache** - Cache show availability (TTL: 30s, acceptable lag)
5. **CDN** - Serve static content (posters, theater info) via CDN
6. **DB Sharding** - Shard by city/theater to distribute load
7. **Async Processing** - Confirmation email sent via SQS, not sync

---

### Q5: Search by city/genre/rating. How to keep < 200ms latency at scale?

**Answer**:
1. **Elasticsearch** - Index movies by genre, rating, language
2. **Redis Cache** - Cache popular searches (top 100 movies per city)
3. **Read Replicas** - Multiple MySQL replicas for search queries
4. **Denormalization** - Store movie_genre on movie table (no join)
5. **Pagination** - Return only 20 results per page (limit DB scan)

---

### Q6: How do you handle cancellations and refunds?

**Answer**:
```
User cancels booking:
├─ Check if < 4 hours before showtime (non-refundable after)
├─ Mark booking.status = CANCELLED
├─ Release seats (AVAILABLE)
├─ Initiate refund via payment gateway
├─ Process refund to wallet/original bank account
└─ Send cancellation receipt within 30 secs
```

---

---

### Q8: SERIALIZABLE vs READ_COMMITTED - Which isolation level for booking?

**Answer**:

**TL;DR**: Use **READ_COMMITTED + explicit `FOR UPDATE` locks**, not full SERIALIZABLE.

**Breakdown**:

1. **READ_COMMITTED + FOR UPDATE** ✅ (Production choice)
   - Row-level lock prevents same seat from being booked twice
   - User B waits if trying to lock same seat as User A
   - Performance: 10k bookings/sec throughput
   - Deadlock rate: < 0.01%

2. **SERIALIZABLE** ❌ (Overkill)
   - Also works, but 5x slower (2k bookings/sec)
   - Higher deadlock rate (5-10%)
   - Prevents phantom reads we don't have
   - Better for range queries or complex logic

3. **Why the distinction matters**:
   ```
   Booking Logic:
   - Lock specific seat rows? YES (FOR UPDATE handles this)
   - Read data based on those locked rows? YES (safe)
   - Need to prevent phantom reads across 1000s of rows? NO
   
   → READ_COMMITTED + FOR UPDATE sufficient
   ```

4. **Code**:
   ```java
   @Transactional(isolation = Isolation.READ_COMMITTED) // Explicit
   public Booking bookSeats(BookingRequest req) {
       // Lock the specific rows we care about
       Seat seat = seatRepo.findByIdForUpdate(req.getSeatId());
       
       if (seat.getStatus() != AVAILABLE) {
           throw exception; // Safe - nobody can change this between read & check
       }
       
       // Update
       seatRepo.updateStatus(req.getSeatId(), BOOKED);
       return bookingRepo.save(booking);
   }
   ```

---

### Q9: What happens if booking confirmation service crashes mid-transaction?

**Answer**:

Define "mid-transaction":

1. **Crash BEFORE commit** → Transaction rolls back automatically
   ```
   - Seats stay AVAILABLE
   - Row lock released
   - No charge to user (payment gateway didn't receive call)
   - User can retry
   ```

2. **Crash AFTER payment, BEFORE seat update** → Compensating transaction
   ```
   - Payment succeeded (charged user)
   - But booking not saved
   - Solution: 
     ├─ Check if payment_id exists in gateway
     ├─ If yes: Refund automatically
     └─ Alert support team for manual review
   ```

3. **Solution: Idempotency + Saga Pattern**
   ```java
   public Booking bookSeatsWithRecovery(BookingRequest req) {
       String idempotencyKey = UUID.randomUUID().toString();
       
       try {
           // Save idempotency key FIRST (for recovery)
           idempotencyStore.save(idempotencyKey, req);
           
           // Step 1: Reserve seats
           Booking booking = reserveSeats(req, idempotencyKey);
           
           // Step 2: Charge payment
           Payment payment = paymentGateway.charge(booking.getId(), idempotencyKey);
           
           if (!payment.isSuccess()) {
               releaseSeats(booking.getId());
               throw new PaymentFailedException();
           }
           
           // Step 3: Confirm
           booking.setStatus(CONFIRMED);
           return bookingRepository.save(booking);
           
       } catch (Exception e) {
           // Recovery on next retry using same idempotency key
           // Payment gateway deduplicates using idempotencyKey
           log.error("Booking failed", e);
           throw new BookingException("System error, please retry");
       }
   }
   ```



## 🏗️ API Design

### Core Endpoints

```
GET /api/v1/movies/search?city=Mumbai&genre=Action&date=2024-04-01
└─ Response: [{ movieId, title, languages, genres, rating, theaters: [...] }]

GET /api/v1/shows/{movieId}?theater={theaterId}&date=2024-04-01
└─ Response: [{ showId, startTime, endTime, availableSeats, pricePerSeat }]

GET /api/v1/shows/{showId}/seats
└─ Response: [{ seatId, rowNumber, seatNumber, status, priceMultiplier }]

POST /api/v1/bookings
Body: { userId, showId, seatIds: [1, 2, 3], paymentMode }
└─ Response: { bookingId, totalPrice, tempSeatHold: 15mins }

POST /api/v1/bookings/{bookingId}/confirm
Body: { paymentGatewayToken }
└─ Response: { ticketId, confirmationEmail, showtimeDetails }

DELETE /api/v1/bookings/{bookingId}
└─ Response: { refundStatus, refundAmount }
```

---

## Database Schema (SQL)

```sql
CREATE TABLE shows (
    show_id BIGINT PRIMARY KEY,
    screen_id BIGINT,
    movie_id BIGINT,
    show_date DATE,
    start_time TIME,
    duration_mins INT,
    available_seats INT,
    price_per_seat DECIMAL(8,2),
    is_running BOOLEAN,
    created_at TIMESTAMP,
    
    FOREIGN KEY (screen_id) REFERENCES screens(screen_id),
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id),
    INDEX idx_show_date_theater (show_date, screen_id),
    INDEX idx_is_running (is_running)
);

CREATE TABLE booking (
    booking_id BIGINT PRIMARY KEY,
    user_id BIGINT,
    show_id BIGINT,
    total_seats INT,
    total_price DECIMAL(12,2),
    booking_status ENUM('PENDING', 'CONFIRMED', 'CANCELLED'),
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    payment_id VARCHAR(255),
    
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (show_id) REFERENCES shows(show_id),
    INDEX idx_user_show (user_id, show_id),
    INDEX idx_status (booking_status),
    INDEX idx_expires_at (expires_at)
);

CREATE TABLE booking_seat (
    booking_seat_id BIGINT PRIMARY KEY,
    booking_id BIGINT,
    seat_id BIGINT,
    
    FOREIGN KEY (booking_id) REFERENCES booking(booking_id) ON DELETE CASCADE,
    FOREIGN KEY (seat_id) REFERENCES seats(seat_id),
    UNIQUE (booking_id, seat_id)
);

CREATE TABLE seat_availability (
    show_id BIGINT,
    seat_id BIGINT,
    status ENUM('AVAILABLE', 'RESERVED', 'BOOKED'),
    reserved_until TIMESTAMP,
    booking_id BIGINT,
    
    PRIMARY KEY (show_id, seat_id),
    FOREIGN KEY (booking_id) REFERENCES booking(booking_id),
    INDEX idx_status (status)
);

CREATE TABLE payment (
    payment_id VARCHAR(255) PRIMARY KEY,
    booking_id BIGINT,
    user_id BIGINT,
    amount DECIMAL(12,2),
    payment_mode VARCHAR(50),
    transaction_id VARCHAR(255),
    status ENUM('PENDING', 'SUCCESS', 'FAILED', 'REFUNDED'),
    created_at TIMESTAMP,
    processed_at TIMESTAMP,
    
    FOREIGN KEY (booking_id) REFERENCES booking(booking_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE (transaction_id),
    INDEX idx_user_created (user_id, created_at)
);
```

---

## Key Takeaways for Interviews

| Topic | Answer |
|-------|--------|
| **Race Conditions** | Use `FOR UPDATE` locks on seats + row-level isolation |
| **Payment Safety** | 3-phase commit: RESERVE → CHARGE → CONFIRM with idempotency |
| **Seat Expiry** | 15-min holds, background cleanup job, no charge if abandoned |
| **High Concurrency** | Queue system + load shedding (HTTP 429) + async confirmation |
| **Search Latency** | Cache + ES index + read replicas + denormalization |
| **Consistency** | Strong for booking (ACID), Eventual for search (eventual consistency) |

---

## Production Considerations

- **Monitoring**: Alert if booking confirmation > 2 mins
- **Audit**: Log all payment transactions for compliance
- **Backup**: Real-time replication to secondary region
- **Testing**: Chaos engineering for failure scenarios (payment timeout, seat lock deadlock)
- **Compliance**: PCI-DSS for payment data, GDPR for user data
