# 🎬 BookMyShow - Low Level Design Interview Guide
## _15 YOE Architect-Level Conversational Script_

---

## 📋 **Table of Contents**
1. [Architecture Diagram](#1-architecture-diagram)
2. [API Design](#2-api-design)
3. [ER Diagram & Database Design](#3-er-diagram--database-design)
4. [Sequence Diagrams](#4-sequence-diagrams)
5. [Scenario-First Explanations](#5-scenario-first-explanations)
6. [Cross Questions](#6-cross-questions)
7. [Trade-offs](#7-trade-offs)
8. [Senior Trap Questions](#8-senior-trap-questions)
9. [Technology Choices](#9-technology-choices)

---

## 1. Architecture Diagram

**Interviewer**: "Design a movie ticket booking system like BookMyShow."

**You**: "Great question! Let me start with the big picture first. See, when I approach this problem, I think about the user journey—what does a user actually do? They select a city, pick a movie, choose a theater, select seats, and book. So my architecture needs to reflect that flow."

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BOOKMYSHOW ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────────┘

                                   ┌─────────────┐
                                   │   CLIENT    │
                                   │  (Web/App)  │
                                   └──────┬──────┘
                                          │
                                          ▼
                         ┌────────────────────────────────┐
                         │      API GATEWAY / LB          │
                         │   (Rate Limiting, Auth)        │
                         └────────────┬───────────────────┘
                                      │
                   ┌──────────────────┼──────────────────┐
                   │                  │                  │
                   ▼                  ▼                  ▼
         ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
         │ MOVIE SERVICE   │  │ THEATER SERVICE │  │ BOOKING SERVICE │
         │                 │  │                 │  │                 │
         │ - MovieCtrl     │  │ - TheaterCtrl   │  │ - Booking Mgr   │
         │ - City mapping  │  │ - Show Mgr      │  │ - Seat Locking  │
         └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
                  │                    │                     │
                  │                    │                     │
                  ▼                    ▼                     ▼
         ┌─────────────────────────────────────────────────────────┐
         │                   DATA LAYER                            │
         │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────────┐ │
         │  │ Movies  │  │Theaters │  │ Shows   │  │ Bookings  │ │
         │  │   DB    │  │   DB    │  │   DB    │  │    DB     │ │
         │  └─────────┘  └─────────┘  └─────────┘  └───────────┘ │
         └─────────────────────────────────────────────────────────┘
                  │                    │                     │
                  └────────────────────┼─────────────────────┘
                                       ▼
                              ┌─────────────────┐
                              │  REDIS CACHE    │
                              │ - Seat Status   │
                              │ - Show Metadata │
                              └─────────────────┘
```

### **Why This Design?**

**You**: "Notice I've separated concerns by service. Here's my thinking:

1. **Movie Service** manages all movies and their city associations. Why? Because movies are relatively static—they don't change every second.

2. **Theater Service** owns theaters, screens, and shows. This is critical because shows are what tie movies to physical locations and time slots.

3. **Booking Service** is isolated because it's the most critical path. High concurrency, needs transactional guarantees, seat locking—it deserves its own service.

4. **Redis Cache** sits in front for two reasons:
   - Seat availability queries are HOT path
   - TTL-based seat locks (10-minute hold)

The interviewer will love that you're thinking about scalability and separation of concerns upfront."

---

## 2. API Design

**Interviewer**: "What APIs would you expose?"

**You**: "Let me walk you through the user journey and map each step to an API. I'll show you RESTful endpoints with proper status codes."

### **2.1 Movie Discovery APIs**

```http
GET /api/v1/cities
Response: 200 OK
[
  { "cityId": "DEL", "cityName": "Delhi" },
  { "cityId": "BLR", "cityName": "Bengaluru" }
]

GET /api/v1/movies?cityId=BLR
Response: 200 OK
{
  "movies": [
    {
      "movieId": "m1",
      "name": "Avengers",
      "duration": 180,
      "language": "English",
      "rating": "PG-13"
    }
  ]
}
```

### **2.2 Show Discovery APIs**

```http
GET /api/v1/shows?movieId=m1&cityId=BLR&date=2026-08-31
Response: 200 OK
{
  "shows": [
    {
      "showId": "s1",
      "theaterId": "t1",
      "theaterName": "INOX Koramangala",
      "screenId": "scr1",
      "startTime": "08:00:00",
      "availableSeats": 45
    }
  ]
}
```

### **2.3 Seat Selection API**

```http
GET /api/v1/shows/{showId}/seats
Response: 200 OK
{
  "seats": [
    {
      "seatId": 30,
      "row": "C",
      "category": "GOLD",
      "price": 250.00,
      "status": "AVAILABLE",  // AVAILABLE | BOOKED | LOCKED
      "version": 1  // Optimistic locking!
    }
  ]
}
```

### **2.4 Booking APIs** (Critical Path!)

```http
POST /api/v1/bookings/lock
Request:
{
  "showId": "s1",
  "seatIds": [30, 31],
  "userId": "u123"
}

Response: 200 OK
{
  "lockId": "lock-uuid-1234",
  "expiresAt": "2026-08-31T10:10:00Z",  // 10-min window
  "totalPrice": 500.00
}

---

POST /api/v1/bookings/confirm
Request:
{
  "lockId": "lock-uuid-1234",
  "paymentId": "pay-5678"
}

Response: 201 CREATED
{
  "bookingId": "book-9999",
  "status": "CONFIRMED",
  "qrCode": "base64-encoded-qr"
}

// If payment fails or timeout:
Response: 409 CONFLICT
{
  "error": "LOCK_EXPIRED",
  "message": "Seat lock expired. Please try again."
}
```

### **Why This API Design?**

**You**: "Notice three things:

1. **Two-phase booking** (lock → confirm). This is intentional! We don't block seats permanently during payment processing. If payment fails, seats auto-release.

2. **Version field** in seat status. This is for optimistic locking—we'll get to concurrency in a bit.

3. **Idempotency keys** (not shown but implied)—if user hits 'Confirm' twice, we don't double-book."

---

## 3. ER Diagram & Database Design

**Interviewer**: "Show me your database schema."

**You**: "Absolutely. Let me draw the entity relationships first, then explain normalization choices."

```
┌───────────────────────────────────────────────────────────────────────────┐
│                            ER DIAGRAM                                     │
└───────────────────────────────────────────────────────────────────────────┘

    ┌─────────┐                    ┌──────────┐
    │  CITY   │                    │  MOVIE   │
    │─────────│                    │──────────│
    │*cityId  │                    │*movieId  │
    │ name    │                    │ name     │
    └────┬────┘                    │ duration │
         │                         │ language │
         │                         └─────┬────┘
         │                               │
         │  ┌────────────────────────────┘
         │  │ M:N (CityMovies mapping)
         │  │
         ▼  ▼
    ┌──────────────┐         ┌───────────┐
    │ CITY_MOVIES  │         │  THEATER  │
    │──────────────│         │───────────│
    │*cityId   (FK)│         │*theaterId │
    │*movieId  (FK)│◄────┐   │ name      │
    └──────────────┘     │   │ address   │
                         │   │ cityId(FK)│
                         │   └─────┬─────┘
                         │         │
                         │         │ 1:N
                         │         ▼
                         │   ┌───────────┐
                         │   │  SCREEN   │
                         │   │───────────│
                         │   │*screenId  │
                         │   │ theaterId │
                         │   └─────┬─────┘
                         │         │
                         │         │ 1:N
                         │         ▼
                         │   ┌───────────┐
                         │   │   SEAT    │
                         │   │───────────│
                         │   │*seatId    │
                         │   │ screenId  │
                         │   │ seatNumber│
                         │   │ category  │
                         │   │ price     │
                         │   └───────────┘
                         │
                         └───────┐
                                 │
                                 ▼
                           ┌──────────┐
                           │   SHOW   │
                           │──────────│
                           │*showId   │
                           │ movieId  │
                           │ screenId │
                           │ startTime│
                           │ endTime  │
                           └────┬─────┘
                                │
                                │ 1:N
                                ▼
                         ┌──────────────┐
                         │  SHOW_SEAT   │ ◄── CRITICAL!
                         │──────────────│
                         │*showId   (FK)│
                         │*seatId   (FK)│
                         │ status       │
                         │ version      │ ◄── Optimistic Lock
                         │ lockedAt     │
                         │ lockedBy     │
                         └──────┬───────┘
                                │
                                │ M:1
                                ▼
                           ┌──────────┐
                           │ BOOKING  │
                           │──────────│
                           │*bookingId│
                           │ userId   │
                           │ showId   │
                           │ seatIds[]│
                           │ totalAmt │
                           │ status   │
                           │ createdAt│
                           └────┬─────┘
                                │
                                │ 1:1
                                ▼
                           ┌──────────┐
                           │ PAYMENT  │
                           │──────────│
                           │*paymentId│
                           │ bookingId│
                           │ amount   │
                           │ status   │
                           │ gateway  │
                           └──────────┘
```

### **Schema Details**

```sql
-- CRITICAL TABLE: Show-Seat Mapping with Optimistic Locking
CREATE TABLE show_seats (
    show_id VARCHAR(50) NOT NULL,
    seat_id INT NOT NULL,
    status ENUM('AVAILABLE', 'LOCKED', 'BOOKED') DEFAULT 'AVAILABLE',
    version INT DEFAULT 1,  -- For optimistic locking
    locked_at TIMESTAMP NULL,
    locked_by VARCHAR(50) NULL,
    booking_id VARCHAR(50) NULL,
    
    PRIMARY KEY (show_id, seat_id),
    INDEX idx_status_version (status, version),
    INDEX idx_locked_at (locked_at),  -- For TTL cleanup
    
    FOREIGN KEY (show_id) REFERENCES shows(show_id),
    FOREIGN KEY (seat_id) REFERENCES seats(seat_id)
);

-- Booking table
CREATE TABLE bookings (
    booking_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    show_id VARCHAR(50) NOT NULL,
    seat_ids JSON NOT NULL,  -- [30, 31, 32]
    total_amount DECIMAL(10,2) NOT NULL,
    status ENUM('PENDING', 'CONFIRMED', 'CANCELLED'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP NULL,
    
    INDEX idx_user_id (user_id),
    INDEX idx_show_id (show_id),
    INDEX idx_status (status)
);
```

### **Why This Schema?**

**You**: "Three design decisions worth highlighting:

1. **`show_seats` table is the heart**. Notice it's NOT in the `seats` table—why? Because seat availability is per-show, not per-screen. Same seat can be booked in 8 AM show but available in 12 PM show.

2. **Version column** for optimistic locking. Two users try to book seat 30? First one increments version from 1 to 2. Second one fails because they have stale version 1.

3. **`locked_at` + TTL**. Background job runs every minute: `UPDATE show_seats SET status='AVAILABLE', locked_by=NULL WHERE locked_at < NOW() - INTERVAL 10 MINUTE`. Auto-releases abandoned locks."

---

## 4. Sequence Diagrams

**Interviewer**: "Walk me through the booking flow."

**You**: "Let me show you the happy path and the conflict scenario."

### **4.1 Happy Path: Successful Booking**

```
User          API          BookingSvc    ShowSeatRepo    PaymentSvc    DB
 │              │              │              │              │          │
 │─GET seats────▶│              │              │              │          │
 │              │─getSeats─────▶│              │              │          │
 │              │              │─SELECT────────────────────────────────▶│
 │              │              │◀─────seats (version=1)─────────────────│
 │◀─────────────│◀─────────────│              │              │          │
 │              │              │              │              │          │
 │─POST lock────▶│              │              │              │          │
 │ seatIds:[30] │              │              │              │          │
 │              │─lockSeats────▶│              │              │          │
 │              │              │─UPDATE show_seats            │          │
 │              │              │  SET status='LOCKED',        │          │
 │              │              │      version=2,              │          │
 │              │              │      locked_at=NOW()         │          │
 │              │              │  WHERE seat_id=30            │          │
 │              │              │    AND version=1 ───────────────────▶│
 │              │              │◀─────1 row updated──────────────────│
 │              │◀─lockId──────│              │              │          │
 │◀─lockId─────│              │              │              │          │
 │              │              │              │              │          │
 │─POST confirm─▶│              │              │              │          │
 │   +paymentId │              │              │              │          │
 │              │─────────────────────────────────processPayment───▶│
 │              │◀─────────────────────────────────success──────────│
 │              │─confirmBooking▶│              │              │          │
 │              │              │─UPDATE show_seats            │          │
 │              │              │  SET status='BOOKED'         │          │
 │              │              │  WHERE seat_id=30            │          │
 │              │              │    AND locked_by='lockId'────────────▶│
 │              │              │─INSERT booking────────────────────────▶│
 │              │◀─bookingId───│              │              │          │
 │◀─bookingId──│              │              │              │          │
```

### **4.2 Conflict Scenario: Concurrent Booking**

```
User1         User2         BookingSvc    ShowSeatRepo    DB
 │              │              │              │          │
 │─GET seats────▶│              │              │          │
 │              │─GET seats────▶│              │          │
 │              │              │─SELECT (version=1)────────▶│
 │◀─version=1───│              │◀──────────────────────────│
 │              │◀─version=1───│              │          │
 │              │              │              │          │
 │─POST lock────▶│              │              │          │
 │ seat=30      │              │              │          │
 │              │              │─UPDATE WHERE version=1───▶│
 │              │              │◀─1 row (version→2)────────│
 │◀─lockId─────│              │              │          │
 │              │              │              │          │
 │              │─POST lock────▶│              │          │
 │              │ seat=30      │              │          │
 │              │              │─UPDATE WHERE version=1───▶│
 │              │              │◀─0 rows (version is 2!)───│
 │              │◀─409 CONFLICT│              │          │
 │              │  seat taken  │              │          │
```

**You**: "See the beauty of optimistic locking? User2's UPDATE fails because version changed. No explicit locks, no deadlocks, pure database-level atomic CAS (Compare-And-Swap)."

---

## 5. Scenario-First Explanations

### **5.1 Why City-Based Architecture?**

**Scenario**: "Mumbai has 500 theaters. Delhi has 400. User in Mumbai shouldn't query Delhi data."

**You**: "Exactly! That's why I have:
```java
Map<City, List<Movie>> cityVsMovies;  // Movie Controller
Map<City, List<Theater>> cityVsTheaters;  // Theater Controller
```

This enables:
- **Geographic sharding**: Mumbai data → Mumbai DB shard
- **CDN optimization**: Static movie posters served from nearest edge
- **Regulatory compliance**: Some movies banned in certain states—easy to filter

Without city isolation, every query scans global dataset. With 10M users, that's a disaster."

### **5.2 Why Separate Show from Screen?**

**Scenario**: "Screen 1 has 100 seats. It shows Avengers at 8 AM, 12 PM, 4 PM."

**You**: "If I put seat booking in Screen table:
```java
class Screen {
    List<Seat> seats;  // ❌ WRONG! All shows share same seats?
}
```

Problem: 8 AM show is full, but 12 PM show has seats. Can't represent this!

Solution:
```java
class Show {
    Screen screen;
    List<Integer> bookedSeatIds;  // ✅ Per-show booking!
}
```

Now each show independently tracks its seat bookings."

### **5.3 Why Optimistic Locking Over Pessimistic?**

**Scenario**: "10,000 users trying to book Avengers opening day. Seats gone in seconds."

**You**: "If I use pessimistic locking:
```java
synchronized(seat) {  // ❌ Locks entire seat object
    if (seat.isAvailable()) {
        seat.book();
    }
}
```

Problem:
- Only 1 thread can check availability at a time
- 9,999 threads blocked waiting
- With 100 seats × 10,000 users = only 100 concurrent ops

With optimistic locking:
```java
UPDATE show_seats 
SET status='LOCKED', version=version+1
WHERE seat_id=30 AND version=1;

// ✅ Returns 0 rows if someone else booked it
```

Benefits:
- 10,000 concurrent reads (no blocking!)
- Database does CAS atomically
- Failed bookings retry immediately (no deadlock risk)"

---

## 6. Cross Questions

**Interviewer**: "What if payment takes 30 seconds? Should we hold the seat?"

**You**: "Great question! This is the classic trade-off between user experience and inventory efficiency.

**Option A**: Hold seat during payment (current design)
- ✅ User doesn't lose seat mid-payment
- ❌ Seat blocked from others for 30s
- **When to use**: Low-traffic scenarios, premium events (concerts)

**Option B**: Payment after booking (release seat immediately)
- ✅ Maximizes inventory utilization
- ❌ User might lose seat if payment gateway slow
- **When to use**: High-traffic movies (opening day)

I'd go with **Option A + 10-minute TTL** because:
1. Payment usually completes in 5-10 seconds
2. If TTL expires, background job releases seat
3. User gets clear error: 'Seat lock expired, try again'

Real-world example: BookMyShow holds seats for 10 min. Paytm Insider does 15 min for concerts."

---

**Interviewer**: "How do you handle partial failures? User booked 5 seats, payment succeeds for 3?"

**You**: "This is a distributed transaction problem. Two approaches:

**Approach 1: All-or-Nothing (Recommended)**
```java
@Transactional
public Booking confirmBooking(String lockId, String paymentId) {
    // Step 1: Verify payment FIRST
    Payment payment = paymentService.verify(paymentId);
    if (!payment.isSuccess()) {
        throw new PaymentFailedException();  // Rollback!
    }
    
    // Step 2: Update ALL seats atomically
    int updated = seatRepo.updateAll(seatIds, "BOOKED");
    if (updated != seatIds.size()) {
        throw new ConcurrentModificationException();  // Rollback!
    }
    
    // Step 3: Create booking
    return bookingRepo.save(new Booking(...));
}
```

**Approach 2: Saga Pattern (For microservices)**
- Use compensating transactions
- If payment succeeds but seat booking fails → refund payment
- Example: `PaymentCompensator.refund(paymentId)`

I prefer **Approach 1** for booking service because it's a single transaction. Saga adds unnecessary complexity."

---

**Interviewer**: "10,000 users hit your API at the same time. How do you prevent database meltdown?"

**You**: "Great question! This is where caching + rate limiting saves the day.

**Layer 1: API Gateway Rate Limiting**
```
Rate limit: 100 req/sec per user
Burst: 200 req/5sec per IP
```

**Layer 2: Redis Cache (Hot Data)**
```java
@Cacheable(value = "shows", key = "#movieId + #cityId")
public List<Show> getShows(String movieId, String cityId) {
    // Only hits DB if cache miss
}

// TTL: 5 minutes (shows don't change frequently)
```

**Layer 3: Database Connection Pooling**
```
HikariCP config:
- Max connections: 200
- Min idle: 50
- Connection timeout: 5 seconds
```

**Layer 4: Circuit Breaker**
```java
@CircuitBreaker(name = "booking", fallbackMethod = "bookingFallback")
public Booking createBooking(...) {
    // If 50% failures in 10 sec → open circuit → fail fast
}
```

**Real numbers**:
- Without cache: DB dies at 500 req/sec
- With cache: Handle 10,000 req/sec (95% cache hit rate)
- Cost: $200/month Redis vs $5,000/month bigger RDS"

---

## 7. Trade-offs

### **7.1 Optimistic vs Pessimistic Locking**

| Aspect | Optimistic | Pessimistic |
|--------|-----------|-------------|
| **Concurrency** | High (10K+ concurrent reads) | Low (serialized access) |
| **Consistency** | Eventual (retry on conflict) | Immediate |
| **Best For** | High-traffic, low-conflict | Low-traffic, high-conflict |
| **Example** | Movie bookings (many seats) | Bank transfers (single account) |

**You**: "For BookMyShow, optimistic wins because:
- 100 seats per show = low conflict probability
- Peak traffic matters more than absolute consistency
- Failed booking just means 'Try another seat'—no money lost

But for bank transfers, you NEED pessimistic locks. Can't have two withdrawals overdrawing same account!"

### **7.2 Monolith vs Microservices**

| Aspect | Monolith | Microservices |
|--------|----------|---------------|
| **Deployment** | Single deploy | Independent deploys |
| **Transactions** | ACID (easy) | Saga (complex) |
| **Scaling** | Scale entire app | Scale only booking service |
| **Latency** | Low (in-process) | High (network calls) |

**You**: "I'd start with **modular monolith**:
```
Monolith
├── MovieModule (independent package)
├── TheaterModule
└── BookingModule (separate DB schema)
```

Why?
- Day 1: 1,000 users → Monolith handles it fine
- Day 100: 100K users → Extract BookingModule to separate service
- Day 365: 1M users → Full microservices

Premature microservices = premature optimization. BookMyShow started as PHP monolith!"

### **7.3 SQL vs NoSQL for Bookings**

| Aspect | PostgreSQL (SQL) | MongoDB (NoSQL) |
|--------|------------------|-----------------|
| **Transactions** | ACID, multi-table | Limited (single doc) |
| **Joins** | Efficient | Requires app logic |
| **Schema** | Strict (good for $) | Flexible |
| **Scaling** | Vertical, sharding hard | Horizontal, sharding easy |

**You**: "For bookings, **PostgreSQL** is non-negotiable:

Why SQL?
1. **ACID transactions**: Seat lock → Payment → Booking must be atomic
2. **Joins**: `SELECT * FROM bookings JOIN payments JOIN users` (reporting!)
3. **Constraints**: Foreign keys prevent orphaned bookings
4. **Audit trail**: Money involved = strict schema

When to use NoSQL?
- Movie catalog (read-heavy, schema changes often)
- User reviews (no joins needed)
- Session data (key-value)

Real example: Netflix uses Cassandra for movie catalog but PostgreSQL for billing."

---

## 8. Senior Trap Questions

### **Trap #1: "Just use a distributed lock like Redlock!"**

**Interviewer**: "Why not use Redis distributed lock instead of database versioning?"

**❌ Junior Answer**: "Sure, Redis is faster than database locks."

**✅ Senior Answer**: "Actually, Redis Redlock has a fatal flaw for financial transactions. Let me show you:

```
User A                    Redis                   User B
│                           │                       │
├─ LOCK seat-30 ───────────▶│                       │
│  SET seat-30-lock ttl=10s │                       │
│◀─ OK ──────────────────────│                       │
│                           │                       │
│  [GC pause 11 seconds]    │                       │
│                           │                       │
│                           │◀─ LOCK seat-30 ───────┤
│                           │  (lock expired!)      │
│                           ├─ OK ──────────────────▶│
│                           │                       │
├─ Book seat-30 ────────────┼───────────────────────┤
│  (thinks it has lock!)    │                       │
│                           │                       ├─ Book seat-30
│                           │                       │  (also thinks it has lock!)
│                           │                       │
│      💥 DOUBLE BOOKING! 💥
```

**Problem with Redlock**:
- GC pauses, network delays can cause lock expiry
- No happens-before guarantee
- Martin Kleppmann (distributed systems expert) wrote famous critique

**Why DB optimistic locking wins**:
```sql
UPDATE show_seats 
SET version = version + 1, status = 'BOOKED'
WHERE seat_id = 30 AND version = 1;

-- ✅ Atomic! Only ONE thread succeeds
-- ✅ Database guarantees serializability
-- ✅ No lock expiry footgun
```

I'd use Redis for **cache**, not **correctness**. Money is involved—can't risk double booking."

---

### **Trap #2: "Just scale the database!"**

**Interviewer**: "If you have performance issues, why not just add more database replicas?"

**❌ Junior Answer**: "Yes, read replicas will solve it."

**✅ Senior Answer**: "Read replicas help reads, but booking is a WRITE-heavy operation. Let me break it down:

**Problem with replicas**:
```
Primary (Write)          Replica (Read)
    │                        │
    ├─ Book seat 30 ────────┐
    │  version: 1→2         │
    │                        │
    │                        │  [Replication lag: 200ms]
    │                        │
    │                        ├─ SELECT seat 30
    │                        │  version: 1 (stale!)
    │                        │
    │                        └─ Shows AVAILABLE (WRONG!)
```

**What actually works**:

1. **Write to primary, read from cache**:
```java
// Write path (low QPS)
db.execute("UPDATE show_seats SET status='BOOKED'");
cache.delete("seat-30");  // Invalidate cache

// Read path (high QPS)
seatStatus = cache.get("seat-30");
if (seatStatus == null) {
    seatStatus = db.query("SELECT status FROM show_seats");
    cache.set("seat-30", seatStatus, ttl=60s);
}
```

2. **Sharding by showId**:
```
Show_1 to Show_100K   → Shard 1 (Mumbai)
Show_100K to Show_200K → Shard 2 (Delhi)
```

3. **Event sourcing for high-traffic**:
```
Instead of UPDATE (locks entire row):
INSERT INTO seat_events (seat_id, event_type, timestamp);
-- Read seat status by replaying events
```

**Real numbers**:
- 10 read replicas: Still only 1 primary write → bottleneck remains
- 1 primary + Redis cache: 100x write throughput
- Sharding: Linear scaling (10 shards = 10x write capacity)

The lesson? **Scaling reads ≠ Scaling writes**. Booking is write-bound."

---

### **Trap #3: "Use microservices from day one!"**

**Interviewer**: "Shouldn't you build this as microservices from the start for scalability?"

**❌ Junior Answer**: "Yes, microservices are best practice for scalability."

**✅ Senior Answer**: "Actually, premature microservices have killed more startups than they've saved. Here's why:

**Cost of microservices early on**:

1. **Distributed transactions nightmare**:
```java
// Monolith (simple):
@Transactional
void bookTicket() {
    seatRepo.lock(seatId);      // 
    paymentRepo.charge(userId); // All ACID!
    bookingRepo.create();       // 
}

// Microservices (complex):
void bookTicket() {
    // Step 1: Lock seat (Seat Service)
    seatService.lock(seatId);
    
    try {
        // Step 2: Charge payment (Payment Service)
        paymentService.charge(userId);
    } catch (PaymentFailedException e) {
        // ❌ Compensating transaction needed!
        seatService.unlock(seatId);  // What if this fails?
        throw e;
    }
    
    // Step 3: Create booking (Booking Service)
    bookingService.create();
    // ❌ What if network fails here? Charged but no booking!
}

// Need: Saga pattern, 2PC, or event sourcing (months of work!)
```

2. **Operational complexity**:
```
Monolith:   1 deploy, 1 log file, 1 monitoring dashboard
Microservices: 10 deploys, 10 log aggregation, 10 dashboards,
               service mesh, API gateway, distributed tracing...
```

3. **Team size requirement**:
- 2 engineers → Microservices = 80% time on DevOps, 20% on features
- 20 engineers → Microservices = 2 engineers per service (manageable)

**My recommendation: Modular Monolith**
```java
// Single deployment, separate modules
@Module(name = "booking", database = "booking_db")
class BookingModule { }

@Module(name = "payment", database = "payment_db")
class PaymentModule { }

// Future: Extract to separate service in 1 week (already modular!)
```

**Evolution path**:
- **Day 1 (100 users)**: Monolith on single server ($50/month)
- **Month 6 (10K users)**: Monolith + Redis + Read replicas ($500/month)
- **Year 1 (100K users)**: Extract Booking Service ($2K/month)
- **Year 3 (1M users)**: Full microservices ($20K/month)

Amazon, Netflix, Uber all started as monoliths. Don't over-engineer."

---

### **Trap #4: "2PC solves distributed transactions!"**

**Interviewer**: "For payment + booking, can't you just use two-phase commit?"

**❌ Junior Answer**: "Yes, 2PC guarantees ACID across services."

**✅ Senior Answer**: "2PC is a textbook solution but a production nightmare. Let me show you why:

**2PC Happy Path**:
```
Coordinator           Payment Service      Booking Service
    │                      │                     │
    ├─ PREPARE ───────────▶│                     │
    │                      ├─ Lock payment       │
    │                      └─ VOTE YES ──────────┤
    │                                            │
    ├─ PREPARE ────────────────────────────────▶│
    │                                            ├─ Lock seats
    │                                            └─ VOTE YES
    │                                            │
    ├─ COMMIT ─────────────▶│                     │
    │                      └─ Charge & Release   │
    ├─ COMMIT ──────────────────────────────────▶│
    │                                            └─ Book & Release
```

**2PC Failure Scenarios**:

```
Scenario 1: Coordinator crashes after PREPARE
Payment Service: ❌ LOCKED (indefinitely!)
Booking Service: ❌ LOCKED (indefinitely!)
Result: Entire system frozen

Scenario 2: Network partition during COMMIT
Coordinator → Payment: ✅ COMMIT received
Coordinator → Booking: ❌ Network timeout
Result: Payment charged, no booking! (inconsistency)

Scenario 3: Booking Service crashes after VOTE YES
Coordinator: Waiting for COMMIT response (forever)
Payment Service: Still locked (degraded)
Result: Cascading failures
```

**Why 2PC fails in production**:
1. **Blocking**: Locks held during network I/O (10-100ms)
2. **Single point of failure**: Coordinator crash = system halt
3. **Amplification**: 1 slow service → all services slow
4. **Heisenbugs**: Works in test (low latency), fails in prod (high latency)

**What works: Saga Pattern**:
```java
// Saga Orchestrator
class BookingSaga {
    void execute() {
        try {
            // Step 1: Reserve seats
            String seatLockId = seatService.lock(seatIds);
            
            try {
                // Step 2: Charge payment
                String paymentId = paymentService.charge(amount);
                
                try {
                    // Step 3: Confirm booking
                    bookingService.create(seatLockId, paymentId);
                    
                } catch (BookingException e) {
                    // Compensate: Refund payment
                    paymentService.refund(paymentId);
                    throw e;
                }
                
            } catch (PaymentException e) {
                // Compensate: Release seats
                seatService.unlock(seatLockId);
                throw e;
            }
            
        } catch (SeatLockException e) {
            // Nothing to compensate
            throw e;
        }
    }
}
```

**Trade-offs**:
- ✅ No locks held across services
- ✅ Eventual consistency (acceptable for bookings)
- ✅ Each service fails independently
- ❌ Compensating transactions can fail (need retry + idempotency)

**Real-world**:
- Google Spanner: Uses 2PC but has atomic clocks (not realistic)
- Amazon: Uses Saga for order processing
- Uber: Uses Saga for trip bookings

For BookMyShow, **Saga + idempotent APIs** is the pragmatic choice."

---

## 9. Technology Choices

### **9.1 Database: PostgreSQL vs MySQL**

**Interviewer**: "Which database and why?"

**You**: "Let me compare the top two for transactional systems:"

| Aspect | PostgreSQL | MySQL (InnoDB) |
|--------|-----------|----------------|
| **Concurrency** | MVCC (better for reads) | Gap locking (can deadlock) |
| **ACID** | Stronger guarantees | Good but nuances |
| **JSON** | Native JSONB (indexed!) | JSON (not indexed) |
| **Window Functions** | Full support | Limited |
| **Replication** | Logical (flexible) | Statement/Row |
| **Performance** | Better for complex queries | Better for simple queries |

**When PostgreSQL**:
```sql
-- Booking system (complex queries, strong ACID)
SELECT 
    b.booking_id,
    array_agg(s.seat_number) as seats,
    SUM(s.price) OVER (PARTITION BY b.show_id) as revenue
FROM bookings b
JOIN show_seats ss ON b.booking_id = ss.booking_id
JOIN seats s ON ss.seat_id = s.seat_id
WHERE b.created_at > NOW() - INTERVAL '1 day'
GROUP BY b.booking_id, b.show_id;

-- ✅ PostgreSQL handles this beautifully
-- ❌ MySQL struggles with window functions
```

**When MySQL**:
```sql
-- Simple CRUD (user profiles, session data)
SELECT user_id, name, email 
FROM users 
WHERE email = 'user@example.com';

-- ✅ MySQL is 10-20% faster for simple queries
-- ✅ Wider ecosystem (more DBAs know it)
```

**My Choice: PostgreSQL**
- Booking system has complex reporting needs
- Strong ACID critical for money
- JSONB for flexible seat metadata (wheelchair, premium, etc.)

**Real examples**:
- Instagram: PostgreSQL (complex social graph)
- Facebook: MySQL (sharded simple KV)

---

### **9.2 Cache: Redis vs Memcached**

| Aspect | Redis | Memcached |
|--------|-------|-----------|
| **Data Structures** | Strings, Lists, Sets, Sorted Sets, Hashes | Key-Value only |
| **Persistence** | RDB + AOF | None |
| **Replication** | Master-Slave | No native support |
| **Atomic Ops** | INCR, SETNX, etc. | Limited |
| **TTL Granularity** | Per-key | Per-key |
| **Multi-threading** | Single-threaded | Multi-threaded |

**When Redis**:
```java
// Seat locking with TTL (Redis only)
redis.set("lock:seat-30", userId, "EX", 600, "NX");
// EX 600 = Expires in 600 seconds
// NX = Set only if not exists (atomic!)

// Sorted set for leaderboards
redis.zadd("top-movies", 9.2, "Avengers");
redis.zrevrange("top-movies", 0, 9);  // Top 10
```

**When Memcached**:
```java
// Simple cache (faster for pure KV)
memcached.set("movie:m1", movieJson, ttl=3600);
// ✅ 10-15% faster than Redis for simple GET/SET
// ✅ Better memory efficiency (LRU eviction)
```

**My Choice: Redis**
- Need TTL-based seat locks (Memcached can't expire mid-operation)
- Need sorted sets for "trending movies"
- Need pub/sub for real-time seat updates
- Persistence needed for lock recovery (server crash)

**Real examples**:
- Twitter: Redis (complex data structures)
- Pinterest: Memcached (simple caching layer)

---

### **9.3 Message Queue: Kafka vs RabbitMQ**

| Aspect | Kafka | RabbitMQ |
|--------|-------|----------|
| **Throughput** | 1M+ msg/sec | 10K-50K msg/sec |
| **Latency** | 10-50ms (batched) | 1-10ms (immediate) |
| **Ordering** | Per-partition | Per-queue |
| **Retention** | Days/weeks (log) | Until consumed |
| **Use Case** | Event streaming | Task queues |

**When Kafka**:
```java
// Booking analytics (event stream)
producer.send("booking-events", bookingEvent);
// Events: seat-locked, payment-attempted, booking-confirmed

// Consumer 1: Real-time analytics
consumer.subscribe("booking-events");
// Track: conversion rate, revenue, popular shows

// Consumer 2: Data warehouse (batch processing)
sparkJob.read("booking-events").window(1.hour).aggregate();
```

**When RabbitMQ**:
```java
// Email notifications (task queue)
queue.publish("email-queue", {
    to: user.email,
    subject: "Booking Confirmed",
    template: "booking-confirmation"
});

// Worker: Process ASAP (low latency)
worker.consume("email-queue", (msg) -> {
    sendEmail(msg);
    msg.ack();  // Remove from queue
});
```

**My Choice: Both!**
- **Kafka**: Booking events (analytics, audit log)
- **RabbitMQ**: Email/SMS notifications (task queue)

**Real examples**:
- Uber: Kafka for trip events + RabbitMQ for driver notifications
- LinkedIn: Kafka for activity streams

---

### **9.4 API Gateway: Kong vs AWS API Gateway**

| Aspect | Kong (Self-hosted) | AWS API Gateway (Managed) |
|--------|-------------------|---------------------------|
| **Latency** | <5ms | 10-50ms (network hop) |
| **Cost** | $0 (EC2 cost) | $3.50 per million requests |
| **Rate Limiting** | Flexible | Basic (burst/rate) |
| **Plugins** | 100+ | Limited |
| **Vendor Lock-in** | None | AWS |

**When Kong**:
```lua
-- Custom rate limiting per user tier
if user.tier == "premium" then
    rate_limit = 1000  -- 1000 req/min
else
    rate_limit = 100   -- 100 req/min
end

-- IP-based blocking (fraud prevention)
if redis.get("blocked-ips:" .. client_ip) then
    return 403
end

-- ✅ Full control, complex logic
```

**When AWS API Gateway**:
```yaml
# Managed, zero-ops
/api/v1/bookings:
  throttling:
    burst: 5000
    rate: 1000
  cors: enabled
  auth: Cognito

# ✅ Deploy in 5 minutes, auto-scales
```

**My Choice: Hybrid**
- **Development**: Kong (local testing, faster iteration)
- **Production**: AWS API Gateway (managed, 99.99% SLA)

**Cost comparison** (1M requests/month):
- Kong on EC2: $50 (t3.medium) + maintenance time
- AWS API Gateway: $3.50 + zero maintenance

**Real examples**:
- Stripe: Kong (complex rate limiting, fraud detection)
- Slack: AWS API Gateway (managed, focus on core product)

---

### **9.5 Load Balancer: NGINX vs ALB**

| Aspect | NGINX | AWS ALB |
|--------|-------|---------|
| **Layer** | L4 (TCP) + L7 (HTTP) | L7 (HTTP/HTTPS) |
| **Health Checks** | TCP/HTTP | HTTP/HTTPS (advanced) |
| **WebSocket** | Full support | Full support |
| **Cost** | $50/month (EC2) | $25/month + $0.008/LCU |
| **SSL Termination** | Manual cert management | ACM (auto-renewal) |

**When NGINX**:
```nginx
upstream booking_service {
    # Consistent hashing (sticky sessions)
    hash $request_uri consistent;
    
    server booking-1:8080 weight=3;
    server booking-2:8080 weight=2;
    server booking-3:8080 weight=1;
}

# Advanced routing
location /api/v1/bookings {
    if ($request_method = POST) {
        proxy_pass http://booking_write;  # Write pool
    }
    proxy_pass http://booking_read;  # Read pool
}

# ✅ Full control, complex routing
```

**When ALB**:
```yaml
# Target groups with health checks
TargetGroup: booking-service
  HealthCheck:
    Path: /health
    Interval: 30s
    Timeout: 5s
    UnhealthyThreshold: 2

# Path-based routing
Rules:
  - Path: /api/v1/bookings/*
    Target: booking-service
  - Path: /api/v1/movies/*
    Target: movie-service

# ✅ Managed, auto-scaling, ACM integration
```

**My Choice: ALB**
- Managed SSL certificates (ACM)
- Native integration with ECS/EKS
- Pay-per-use (scales to zero)
- Health checks + auto-deregister failed instances

**Cost comparison** (10 instances, 100M requests/month):
- NGINX on EC2: $100 (2× t3.small for HA)
- AWS ALB: $25 + $72 (LCU hours) = $97

**Real examples**:
- CloudFlare: NGINX (edge network, max performance)
- Airbnb: ALB (managed, focus on application)

---

## 🎓 **Final Tips for 15 YOE Architect Interview**

1. **Start with Why**: Always explain business rationale before technical details
   - ❌ "I'll use Redis for caching"
   - ✅ "Seat availability is queried 100x more than it changes, so caching reduces DB load by 95%"

2. **Show Evolution**: Demonstrate you've scaled systems before
   - "I'd start with monolith (1K users), extract booking service at 100K users"

3. **Talk Trade-offs**: No perfect solution exists
   - "Optimistic locking trades immediate consistency for throughput"

4. **Use Real Numbers**: Vague answers = junior
   - ❌ "We'll cache it"
   - ✅ "Redis cache with 60s TTL gives 95% hit rate, reducing DB queries from 10K/sec to 500/sec"

5. **Admit Unknowns**: Senior engineers say "I don't know" + "Here's how I'd find out"
   - "I haven't implemented Saga pattern in production, but I'd start with Temporal workflow engine based on Uber's paper"

6. **Reference Real Systems**: Shows you study production architectures
   - "Similar to how BookMyShow uses optimistic locking for seats"

7. **Think Like a CTO**: Mention cost, ops, team size
   - "Microservices need 10+ engineers. With 3 engineers, I'd do modular monolith"

---

**Good luck! Remember**: Interviewers want to see **how you think**, not memorized answers. Walk them through your reasoning, admit trade-offs, and reference real systems. You've got this! 🚀

