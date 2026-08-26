# BookMyShow - Movie Ticket Booking System Design

**Comprehensive Interview Guide with Diagrams, Tables, Code, and Explanations**

**Print Settings:** Landscape mode, monospace font (Courier New/Consolas 9-10pt), narrow margins

---

## TABLE OF CONTENTS

1. Requirements & Capacity Estimation
2. High-Level Architecture
3. Database Design
4. Core Workflows
5. Concurrency & Seat Locking
6. Scalability & Optimizations
7. Interview Q&A

---

## SECTION 1: REQUIREMENTS & CAPACITY ESTIMATION

### 1.1 Functional Requirements

```
✓ User Features:
  - Search movies by city, theater, date
  - View available shows and seats
  - Select and book seats (with real-time availability)
  - Make payments (multiple payment gateways)
  - View booking history
  - Cancel bookings (with refund logic)
  - Rate and review movies

✓ Theater/Admin Features:
  - Add/update movies, shows, theaters
  - Define seat layouts and pricing
  - View bookings and analytics

✗ Out of Scope:
  - Food/beverage ordering
  - Loyalty programs
  - Gift cards
  - Third-party integrations (except payment)
```

### 1.2 Non-Functional Requirements

```
Scale:        100M users, 10M bookings/month
Availability: 99.99% uptime (critical during show times)
Latency:      Search < 500ms, Booking < 2s
Consistency:  Strong consistency for seat booking
              Eventual consistency for search/reviews
Concurrency:  Handle 10K+ concurrent bookings per show
Fair Booking: FIFO for seat selection
Security:     PCI-DSS compliant for payments
```

### 1.3 Capacity Estimation

**Assumptions:**
- 100M registered users
- 10M bookings per month
- Average 2.5 tickets per booking
- 80% bookings on weekends
- Peak: Friday/Saturday evenings

**Calculations:**

```
Bookings per day: 10M / 30 = 333K bookings/day
Peak day (weekend): 333K × 1.6 = 533K bookings/day

Bookings per second:
- Average: 333K / 86400 = 3.85 bookings/sec
- Peak: 533K / (8 hours × 3600) = 18.5 bookings/sec
- Peak hour surge: 18.5 × 5 = 92 bookings/sec

Read:Write ratio: 100:1 (browsing vs booking)
Search queries: 385 QPS

Storage:
- Per booking: 2 KB (metadata)
- Per ticket: 500 bytes
- Daily: (333K × 2KB) + (833K × 500B) = 1.08 GB/day
- Annual: 395 GB/year
- With replication (3x): 1.2 TB/year
- 5-year total: ~6 TB

Bandwidth:
- Incoming: 500 KB/s (bookings + images)
- Outgoing: 50 MB/s (search results + images)
```

---

## SECTION 2: HIGH-LEVEL ARCHITECTURE

### 2.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USERS (Web + Mobile)                         │
│                    React Web App + React Native                     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         CloudFront CDN (AWS)                         │
│     Cache: Movie Posters, Trailers, Static Assets (TTL: 24h)       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ Cache Miss / API
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│            API Gateway (Kong / AWS API Gateway)                      │
│  • Authentication (JWT)      • Rate Limiting (100 req/min)          │
│  • Request Routing           • SSL Termination                      │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ Path-based Routing
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                        MICROSERVICES LAYER                           │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ User Service │  │Movie Service │  │Theater Service│              │
│  │  :8081       │  │   :8082      │  │    :8083      │              │
│  │              │  │              │  │               │              │
│  │• Auth (JWT)  │  │• CRUD movies │  │• Theaters     │              │
│  │• Profile     │  │• Ratings     │  │• Screens      │              │
│  │• History     │  │• Reviews     │  │• Shows        │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘              │
│         │                 │                 │                        │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼────────┐             │
│  │Booking Service│ │Search Service │  │Payment Service│             │
│  │   :8084       │ │   :8085       │  │    :8086      │             │
│  │               │ │               │  │               │             │
│  │• Seat Lock    │ │• Elasticsearch│  │• Stripe/      │             │
│  │• Booking      │ │• Filters      │  │  Razorpay     │             │
│  │• Validation   │ │• Auto-complete│  │• Refunds      │             │
│  └──────┬────────┘ └──────┬────────┘  └──────┬────────┘             │
│         │                 │                  │                       │
│  ┌──────▼────────┐  ┌─────▼────────┐                                │
│  │Notification   │  │Analytics Svc │                                │
│  │Service :8087  │  │   :8088      │                                │
│  │               │  │              │                                │
│  │• Email (SG)   │  │• Reports     │                                │
│  │• SMS (Twilio) │  │• Dashboards  │                                │
│  │• Push (FCM)   │  │              │                                │
│  └───────────────┘  └──────────────┘                                │
└─────────────────────────────────────────────────────────────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
         ↓                      ↓                      ↓
┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│ Redis Cluster  │    │   Kafka (MSK)  │    │  PostgreSQL    │
│  (ElastiCache) │    │                │    │     (RDS)      │
│                │    │ Topics:        │    │                │
│• Seat Locks    │    │ - booking-     │    │ Tables:        │
│  TTL: 10 min   │    │   events       │    │ - users        │
│• Session Cache │    │ - payment-     │    │ - bookings     │
│• Search Cache  │    │   events       │    │ - tickets      │
│  TTL: 5 min    │    │ - notification │    │ - payments     │
│                │    │   -events      │    │                │
│• Seat Status   │    │                │    │ Primary +      │
│  Key Pattern:  │    │ Partitions: 12 │    │ 2 Read Replicas│
│  show:{id}:    │    │ Replication: 3 │    │                │
│  seat:{num}    │    │                │    │ Sharding:      │
└────────┬───────┘    └────────┬───────┘    │ By city_id     │
         │                     │             └────────┬───────┘
         │                     │                      │
         ↓                     ↓                      ↓
┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│ MongoDB        │    │ Elasticsearch  │    │  S3 Storage    │
│                │    │                │    │                │
│ Collections:   │    │ Indices:       │    │ Buckets:       │
│ - theaters     │    │ - movies       │    │ - posters      │
│ - screens      │    │ - theaters     │    │ - trailers     │
│ - seat_layouts │    │                │    │ - receipts     │
│                │    │ Geo-Search:    │    │                │
│ Flexible       │    │ by location    │    │ Lifecycle:     │
│ Schema for     │    │                │    │ Std → IA →     │
│ seat layouts   │    │ Full-text      │    │ Glacier        │
└────────────────┘    │ search         │    └────────────────┘
                      └────────────────┘
```

### 2.2 Key Design Decisions

```
Component         Decision                      Reasoning
─────────────────────────────────────────────────────────────────────
Seat Locking      Redis with TTL (10 min)       Fast, distributed locks
Booking DB        PostgreSQL (ACID)             Strong consistency needed
Theater Data      MongoDB                       Flexible seat layout schema
Search            Elasticsearch                 Geo + full-text search
Message Queue     Kafka                         Event-driven, reliable
Cache             Redis Cluster                 High throughput, low latency
CDN               CloudFront                    Global distribution of assets
Payment           Stripe/Razorpay               PCI-DSS compliant
```

**Critical Design Patterns:**
- Distributed Locking (Redis)
- SAGA Pattern (booking workflow)
- CQRS (read/write separation)
- Event Sourcing (audit trail)
- Circuit Breaker (payment gateway)

---

## SECTION 3: DATABASE DESIGN

### 3.1 Entity Relationship Diagram (PostgreSQL)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BOOKMYSHOW - CORE SCHEMA                          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐
│       USERS         │
├─────────────────────┤
│ PK  id              │◄──────────────────┐
│     email (UNIQUE)  │                   │ 1
│     phone (UNIQUE)  │                   │
│     password_hash   │                   │
│     full_name       │                   │
│     created_at      │                   │
└──────────┬──────────┘                   │
           │ 1                            │
           │                              │
           │ *                            │
┌──────────▼──────────────┐               │
│     ADDRESSES           │               │
├─────────────────────────┤               │
│ PK  id                  │               │
│ FK  user_id             │               │
│     city                │               │
│     state               │               │
│     pincode             │               │
│     latitude DECIMAL    │               │
│     longitude DECIMAL   │               │
└─────────────────────────┘               │
                                          │
┌─────────────────────┐                   │
│      CITIES         │                   │
├─────────────────────┤                   │
│ PK  id              │                   │
│     name            │                   │
│     state           │                   │
│     is_active       │                   │
└──────────┬──────────┘                   │
           │ 1                            │
           │                              │
           │ *                            │
┌──────────▼──────────────┐               │
│     THEATERS            │               │
├─────────────────────────┤               │
│ PK  id                  │◄──────────────┤──┐
│ FK  city_id             │               │  │ 1
│     name                │               │  │
│     address             │               │  │
│     latitude DECIMAL    │               │  │
│     longitude DECIMAL   │               │  │
│     total_screens       │               │  │
└──────────┬──────────────┘               │  │
           │ 1                            │  │
           │                              │  │
           │ *                            │  │
┌──────────▼──────────────┐               │  │
│      SCREENS            │               │  │
├─────────────────────────┤               │  │
│ PK  id                  │◄──────────────┤──┤──┐
│ FK  theater_id          │               │  │  │ 1
│     name                │               │  │  │
│     total_seats         │               │  │  │
│     screen_type ENUM    │               │  │  │
│     (2D, 3D, IMAX)      │               │  │  │
└──────────┬──────────────┘               │  │  │
           │ 1                            │  │  │
           │                              │  │  │
           │ *                            │  │  │
┌──────────▼──────────────┐               │  │  │
│    SCREEN_SEATS         │               │  │  │
├─────────────────────────┤               │  │  │
│ PK  id                  │               │  │  │
│ FK  screen_id           │               │  │  │
│     seat_number         │               │  │  │
│     row_name            │               │  │  │
│     seat_type ENUM      │               │  │  │
│     (REGULAR, PREMIUM,  │               │  │  │
│      VIP, RECLINER)     │               │  │  │
│     is_active           │               │  │  │
│                         │               │  │  │
│ UNIQUE(screen_id,       │               │  │  │
│        seat_number)     │               │  │  │
└─────────────────────────┘               │  │  │
                                          │  │  │
┌─────────────────────┐                   │  │  │
│      MOVIES         │                   │  │  │
├─────────────────────┤                   │  │  │
│ PK  id              │◄──────────────────┤──┤──┤──┐
│     title           │                   │  │  │  │ 1
│     description     │                   │  │  │  │
│     duration_mins   │                   │  │  │  │
│     language        │                   │  │  │  │
│     release_date    │                   │  │  │  │
│     genre TEXT[]    │                   │  │  │  │
│     rating DECIMAL  │                   │  │  │  │
│     poster_url      │                   │  │  │  │
│     trailer_url     │                   │  │  │  │
│     certificate     │                   │  │  │  │
│     (U, UA, A)      │                   │  │  │  │
└──────────┬──────────┘                   │  │  │  │
           │ 1                            │  │  │  │
           │                              │  │  │  │
           │ *                            │  │  │  │
┌──────────▼──────────────────┐           │  │  │  │
│        SHOWS                │           │  │  │  │
├─────────────────────────────┤           │  │  │  │
│ PK  id                      │◄──────────┤──┼──┼──┼──┐
│ FK  movie_id                │           │  │  │  │  │ 1
│ FK  screen_id               │───────────┘  │  │  │  │
│     show_date DATE          │              │  │  │  │
│     show_time TIME          │              │  │  │  │
│     available_seats INT     │              │  │  │  │
│     status ENUM             │              │  │  │  │
│     (SCHEDULED, RUNNING,    │              │  │  │  │
│      COMPLETED, CANCELLED)  │              │  │  │  │
│                             │              │  │  │  │
│ INDEX: (theater_id, date)   │              │  │  │  │
│ INDEX: (movie_id, date)     │              │  │  │  │
└──────────┬──────────────────┘              │  │  │  │
           │ 1                               │  │  │  │
           │                                 │  │  │  │
           │ *                               │  │  │  │
┌──────────▼──────────────────┐              │  │  │  │
│    SHOW_SEAT_PRICING        │              │  │  │  │
├─────────────────────────────┤              │  │  │  │
│ PK  id                      │              │  │  │  │
│ FK  show_id                 │              │  │  │  │
│     seat_type VARCHAR       │              │  │  │  │
│     price DECIMAL           │              │  │  │  │
└─────────────────────────────┘              │  │  │  │
                                             │  │  │  │
┌─────────────────────┐                      │  │  │  │
│     BOOKINGS        │                      │  │  │  │
├─────────────────────┤                      │  │  │  │
│ PK  id              │                      │  │  │  │
│     booking_number  │──────────────────────┘  │  │  │
│     (UNIQUE)        │                         │  │  │
│ FK  user_id         │                         │  │  │
│ FK  show_id         │─────────────────────────┘  │  │
│     num_seats INT   │                            │  │
│     total_amount    │                            │  │
│     status ENUM     │                            │  │
│     (PENDING,       │                            │  │
│      CONFIRMED,     │                            │  │
│      CANCELLED,     │                            │  │
│      EXPIRED)       │                            │  │
│     booked_at       │                            │  │
│     expires_at      │                            │  │
│                     │                            │  │
│ INDEX: user_id      │                            │  │
│ INDEX: show_id      │                            │  │
│ INDEX: status       │                            │  │
└──────────┬──────────┘                            │  │
           │ 1                                     │  │
           │                                       │  │
           │ *                                     │  │
┌──────────▼──────────────────┐                    │  │
│    BOOKING_SEATS            │                    │  │
├─────────────────────────────┤                    │  │
│ PK  id                      │                    │  │
│ FK  booking_id              │                    │  │
│ FK  screen_seat_id          │                    │  │
│     seat_number             │                    │  │
│     price_paid              │                    │  │
│                             │                    │  │
│ UNIQUE(booking_id,          │                    │  │
│        screen_seat_id)      │                    │  │
└─────────────────────────────┘                    │  │
                                                   │  │
┌─────────────────────┐                            │  │
│     PAYMENTS        │                            │  │
├─────────────────────┤                            │  │
│ PK  id              │◄───────────────────────────┘  │
│ FK  booking_id      │                               │
│     amount          │                               │
│     payment_method  │                               │
│     (CARD, UPI,     │                               │
│      WALLET, NET)   │                               │
│     status ENUM     │                               │
│     (PENDING,       │                               │
│      SUCCESS,       │                               │
│      FAILED,        │                               │
│      REFUNDED)      │                               │
│     transaction_id  │                               │
│     gateway         │                               │
│     refund_amount   │                               │
│     created_at      │                               │
└─────────────────────┘                               │
                                                      │
┌─────────────────────┐                               │
│  REVIEWS_RATINGS    │                               │
├─────────────────────┤                               │
│ PK  id              │◄──────────────────────────────┘
│ FK  movie_id        │
│ FK  user_id         │
│     rating (1-5)    │
│     review_text     │
│     created_at      │
│                     │
│ UNIQUE(movie_id,    │
│        user_id)     │
└─────────────────────┘
```

### 3.2 Redis Data Structures

**Seat Locking:**
```
Key Pattern: lock:show:{show_id}:seat:{seat_id}
Value: {user_id}
TTL: 600 seconds (10 minutes)

Commands:
SET lock:show:123:seat:A1 user_456 EX 600 NX
GET lock:show:123:seat:A1
DEL lock:show:123:seat:A1
```

**Available Seats Cache:**
```
Key Pattern: show:{show_id}:available_seats
Value: SET of seat IDs
TTL: 30 seconds

Commands:
SADD show:123:available_seats A1 A2 A3 B1 B2
SREM show:123:available_seats A1
SMEMBERS show:123:available_seats
SCARD show:123:available_seats
```

**Search Results Cache:**
```
Key Pattern: search:city:{city_id}:movie:{movie_name}
Value: JSON list of theaters
TTL: 300 seconds (5 minutes)
```

### 3.3 MongoDB Schema (Flexible Seat Layouts)

```javascript
// Collection: theaters
{
  _id: ObjectId("..."),
  name: "PVR Phoenix",
  city_id: 1,
  screens: [
    {
      screen_id: "screen_1",
      name: "Screen 1",
      layout: {
        rows: [
          {
            row_name: "A",
            seats: [
              {seat_number: "A1", type: "REGULAR", price: 200},
              {seat_number: "A2", type: "REGULAR", price: 200},
              {seat_number: "A3", type: "PREMIUM", price: 300}
            ]
          },
          {
            row_name: "B",
            seats: [
              {seat_number: "B1", type: "RECLINER", price: 500},
              {seat_number: "B2", type: "RECLINER", price: 500}
            ]
          }
        ],
        total_seats: 5,
        aisles: [2, 5, 8]  // Seat numbers where aisles exist
      }
    }
  ]
}
```

---

## SECTION 4: CORE WORKFLOWS

### 4.1 Movie Search Flow

```
┌─────────┐  ┌──────────┐  ┌───────┐  ┌─────────────┐  ┌──────────┐
│ User    │  │ API      │  │ Redis │  │Elasticsearch│  │PostgreSQL│
│         │  │ Gateway  │  │       │  │             │  │          │
└────┬────┘  └────┬─────┘  └───┬───┘  └──────┬──────┘  └────┬─────┘
     │            │            │              │              │
     │ 1. GET /search?city=Mumbai&movie=Avengers              │
     ├───────────>│            │              │              │
     │            │            │              │              │
     │            │ 2. Check cache                           │
     │            ├───────────>│              │              │
     │            │            │              │              │
     │            │<───────────┤ MISS         │              │
     │            │            │              │              │
     │            │ 3. Query Elasticsearch (geo + text)      │
     │            ├────────────┼──────────────>│              │
     │            │            │              │              │
     │            │            │ 4. Search:   │              │
     │            │            │    - location.geo_distance  │
     │            │            │    - match: movie title     │
     │            │            │    - filter: city, date     │
     │            │            │              │              │
     │            │<───────────┼──────────────┤ Results      │
     │            │            │              │              │
     │            │ 5. Enrich data (fetch show times)        │
     │            ├────────────┼──────────────┼──────────────>│
     │            │            │              │              │
     │            │<───────────┼──────────────┼──────────────┤
     │            │            │              │              │
     │            │ 6. Cache results (TTL: 5 min)            │
     │            ├───────────>│              │              │
     │            │            │              │              │
     │<───────────┤ 7. Return JSON (theaters, shows, prices) │
     │            │            │              │              │
```

### 4.2 Seat Booking Flow (Critical - With Locking)

```
┌────────┐ ┌────────┐ ┌─────────┐ ┌───────┐ ┌─────────┐ ┌──────────┐
│Customer│ │Booking │ │Payment  │ │ Redis │ │PostgreSQL│ │  Kafka   │
│        │ │ Svc    │ │ Svc     │ │       │ │          │ │          │
└───┬────┘ └───┬────┘ └────┬────┘ └───┬───┘ └────┬─────┘ └────┬─────┘
    │          │           │          │          │            │
    │ 1. Select Seats (A1, A2)        │          │            │
    ├─────────>│           │          │          │            │
    │          │           │          │          │            │
    │          │ 2. Try to lock seats (A1, A2) using Redis SETNX │
    │          ├───────────┼──────────>│          │            │
    │          │           │          │          │            │
    │          │           │          │ SET lock:show:123:seat:A1 user_456 EX 600 NX
    │          │           │          │ SET lock:show:123:seat:A2 user_456 EX 600 NX
    │          │           │          │          │            │
    │          │<──────────┼──────────┤ Success  │            │
    │          │           │          │          │            │
    │          │ 3. Verify seats still available in DB        │
    │          ├───────────┼──────────┼──────────>│            │
    │          │           │          │          │            │
    │          │           │          │ SELECT * FROM show_seats │
    │          │           │          │  WHERE show_id=123      │
    │          │           │          │    AND seat_id IN (A1,A2) │
    │          │           │          │    AND status='AVAILABLE'│
    │          │           │          │  FOR UPDATE;            │
    │          │           │          │          │            │
    │          │<──────────┼──────────┼──────────┤ Available  │
    │          │           │          │          │            │
    │          │ 4. Create booking (status: PENDING)          │
    │          ├───────────┼──────────┼──────────>│            │
    │          │           │          │          │            │
    │          │           │          │ BEGIN TRANSACTION      │
    │          │           │          │ INSERT INTO bookings   │
    │          │           │          │ INSERT INTO booking_seats│
    │          │           │          │ COMMIT;                │
    │          │           │          │          │            │
    │          │<──────────┼──────────┼──────────┤ booking_id │
    │<─────────┤           │          │          │            │
    │ Booking Created, 10 min to pay  │          │            │
    │          │           │          │          │            │
    │ 5. Initiate payment               │          │            │
    ├─────────>│           │          │          │            │
    │          ├───────────>│          │          │            │
    │          │           │          │          │            │
    │          │           │ 6. Process payment (Stripe/Razorpay)│
    │          │           │          │          │            │
    │          │<──────────┤ Success  │          │            │
    │          │           │          │          │            │
    │          │ 7. Confirm booking & update seat status      │
    │          ├───────────┼──────────┼──────────>│            │
    │          │           │          │          │            │
    │          │           │          │ BEGIN TRANSACTION      │
    │          │           │          │ UPDATE bookings        │
    │          │           │          │   SET status='CONFIRMED'│
    │          │           │          │ UPDATE show_seats      │
    │          │           │          │   SET status='BOOKED'  │
    │          │           │          │ COMMIT;                │
    │          │           │          │          │            │
    │          │ 8. Release locks     │          │            │
    │          ├───────────┼──────────>│          │            │
    │          │           │          │ DEL lock:show:123:seat:A1│
    │          │           │          │ DEL lock:show:123:seat:A2│
    │          │           │          │          │            │
    │          │ 9. Publish booking.confirmed event           │
    │          ├───────────┼──────────┼──────────┼────────────>│
    │          │           │          │          │            │
    │<─────────┤ Booking Confirmed!   │          │            │
    │ booking_number       │          │          │            │
    │          │           │          │          │            │
```

**Failure Scenarios:**

```
Scenario 1: Lock acquisition fails (seat already locked)
→ Return 409 Conflict: "Seat already selected by another user"

Scenario 2: Lock acquired, but DB shows seat unavailable
→ Release lock, return 409: "Seat no longer available"

Scenario 3: Lock acquired, booking created, payment times out
→ Background job expires booking after 10 min
→ Release lock, update booking status to EXPIRED

Scenario 4: Payment fails
→ Release lock immediately
→ Update booking status to CANCELLED
```

### 4.3 Seat Lock Expiry (Background Job)

```python
# Cron Job: Runs every 1 minute
def expire_old_bookings():
    """
    Release locks for bookings that:
    1. Are in PENDING status
    2. Created more than 10 minutes ago
    """
    
    expired_bookings = db.query("""
        SELECT id, booking_number 
        FROM bookings 
        WHERE status = 'PENDING' 
          AND created_at < NOW() - INTERVAL '10 minutes'
    """)
    
    for booking in expired_bookings:
        # Update booking status
        db.execute("""
            UPDATE bookings 
            SET status = 'EXPIRED' 
            WHERE id = ?
        """, booking.id)
        
        # Release all seat locks for this booking
        seats = db.query("""
            SELECT screen_seat_id, show_id 
            FROM booking_seats 
            WHERE booking_id = ?
        """, booking.id)
        
        for seat in seats:
            redis.delete(f"lock:show:{seat.show_id}:seat:{seat.screen_seat_id}")
        
        # Publish event
        kafka.publish('booking.expired', {
            'booking_id': booking.id,
            'booking_number': booking.booking_number
        })
```

### 4.4 Concurrency Handling (Multiple Users, Same Seat)

**Scenario:** 1000 users try to book seat A1 at the same time.

**Solution: Distributed Lock with Redis SETNX**

```
User 1: SET lock:show:123:seat:A1 user_1 EX 600 NX → SUCCESS (gets lock)
User 2: SET lock:show:123:seat:A1 user_2 EX 600 NX → FAIL (lock exists)
User 3: SET lock:show:123:seat:A1 user_3 EX 600 NX → FAIL
...
User 1000: FAIL

Result:
- Only User 1 proceeds with booking
- Users 2-1000 get immediate response: "Seat already selected"
- No database queries for 999 users
- Zero race conditions
```

**Why This Works:**
- SETNX is atomic (Set if Not eXists)
- Redis executes commands sequentially
- First request wins, others fail instantly

### 4.5 Show Timing & Availability

**Problem:** How to show real-time seat availability on the seat map?

**Solution: Hybrid Approach**

```
Initial Load:
1. Fetch all seats for show from PostgreSQL
2. Check Redis for locked seats
3. Merge: Available = (Total - Booked - Locked)

Real-time Updates:
1. WebSocket connection to backend
2. Redis Pub/Sub for seat state changes
3. Push updates to connected clients

Flow:
┌─────────┐                     ┌──────────┐
│ Client  │                     │ Backend  │
│         │                     │          │
│ 1. Load seat map              │          │
├────────────────────────────────>         │
│         │                     │          │
│         │ 2. Fetch seat status│          │
│         │    (DB + Redis)     │          │
│         │                     │          │
│<────────────────────────────────         │
│         │ Seat Map            │          │
│         │                     │          │
│ 3. Subscribe to updates       │          │
├────────────────────────────────>         │
│ ws://api/shows/123/seats      │          │
│         │                     │          │
│         │ 4. User B selects A1│          │
│         │ (Redis Pub/Sub)     │          │
│         │                     │◄─────────┤
│         │                     │          │
│         │ 5. Push update      │          │
│<────────────────────────────────         │
│ {"seat": "A1", "status": "LOCKED"}       │
│         │                     │          │
│ UI: Mark A1 as unavailable    │          │
```

---

## SECTION 5: CONCURRENCY & SEAT LOCKING

### 5.1 Why Distributed Locking is Critical

**The Race Condition Problem:**

```
WITHOUT LOCKING:

Time  User A                    User B
────────────────────────────────────────────────────
T1    Read seat A1: available
T2                              Read seat A1: available
T3    Check OK, proceed
T4                              Check OK, proceed
T5    Book seat A1
T6                              Book seat A1
T7    BOTH get confirmation → Double booking! ❌
```

```
WITH REDIS LOCKING:

Time  User A                    User B
────────────────────────────────────────────────────
T1    Try lock seat A1: SUCCESS ✓
T2                              Try lock seat A1: FAIL ❌
T3    Proceed with booking
T4                              Show "Already selected"
T5    Book seat A1
T6    Release lock
T7    ONLY User A gets seat ✓
```

### 5.2 Lock Implementation (Pseudo-code)

```java
public class SeatLockService {
    
    private final RedisTemplate<String, String> redis;
    private static final int LOCK_TTL = 600; // 10 minutes
    
    public boolean lockSeats(Long showId, List<String> seatIds, Long userId) {
        List<String> lockedSeats = new ArrayList<>();
        
        try {
            for (String seatId : seatIds) {
                String lockKey = String.format("lock:show:%d:seat:%s", showId, seatId);
                
                // Atomic SET NX (Set if Not eXists)
                Boolean acquired = redis.opsForValue()
                    .setIfAbsent(lockKey, userId.toString(), 
                                 Duration.ofSeconds(LOCK_TTL));
                
                if (Boolean.FALSE.equals(acquired)) {
                    // Lock failed, rollback all acquired locks
                    releaseSeats(showId, lockedSeats);
                    return false;
                }
                
                lockedSeats.add(seatId);
            }
            
            return true; // All seats locked successfully
            
        } catch (Exception e) {
            // On error, release any acquired locks
            releaseSeats(showId, lockedSeats);
            throw e;
        }
    }
    
    public void releaseSeats(Long showId, List<String> seatIds) {
        for (String seatId : seatIds) {
            String lockKey = String.format("lock:show:%d:seat:%s", showId, seatId);
            redis.delete(lockKey);
        }
    }
    
    public boolean isLocked(Long showId, String seatId) {
        String lockKey = String.format("lock:show:%d:seat:%s", showId, seatId);
        return redis.hasKey(lockKey);
    }
}
```

### 5.3 Database-Level Locking (Pessimistic)

```sql
-- Step 1: Start transaction with row-level locking
BEGIN TRANSACTION;

-- Step 2: Lock the seats (FOR UPDATE = pessimistic lock)
SELECT id, seat_number, status 
FROM show_seats 
WHERE show_id = 123 
  AND seat_id IN ('A1', 'A2') 
  AND status = 'AVAILABLE'
FOR UPDATE;

-- Step 3: If rows returned, seats are available and now locked
-- Other transactions trying to read these rows will wait

-- Step 4: Update seat status
UPDATE show_seats 
SET status = 'BOOKED', 
    booked_by = 456,
    booked_at = NOW()
WHERE show_id = 123 
  AND seat_id IN ('A1', 'A2');

-- Step 5: Commit (releases lock)
COMMIT;
```

**Why Both Redis + Database Locks?**

```
Redis Lock: Fast, distributed, prevents unnecessary DB calls
Database Lock: ACID guarantee, handles edge cases

Flow:
1. Try Redis lock first (fast path)
   - If fail, return immediately
2. On success, acquire DB lock (safety)
3. Double-check seat availability
4. Complete booking
```

### 5.4 Handling Lock Expiry

**Scenario:** User takes > 10 minutes to complete payment

```
Solution 1: Extend lock before expiry
- Set TTL = 10 minutes
- At 9 minutes, check if user still active
- If active, extend TTL by 5 more minutes
- Max 2 extensions (20 min total)

Solution 2: Refresh lock (Heartbeat)
- Client sends heartbeat every 2 minutes
- Backend extends TTL on each heartbeat
- If no heartbeat for 5 min, lock expires

Solution 3: Grace period
- Show warning at 8 minutes: "2 min left"
- At 10 min, mark as EXPIRED
- Give 1-min grace period to complete payment
- After grace, release lock
```

---

## SECTION 6: SCALABILITY & OPTIMIZATIONS

### 6.1 Database Sharding Strategy

**Shard by City:**

```
Shard 0: Mumbai, Pune, Nagpur
Shard 1: Delhi, Gurgaon, Noida
Shard 2: Bangalore, Mysore, Mangalore
Shard 3: Chennai, Coimbatore, Madurai

Benefits:
- Most queries filtered by city (95%+)
- Hot shard: Mumbai gets dedicated resources
- Geographic data locality
- Easy to add more shards (new city = new shard)

Shard Routing:
city_id → shard_id = hash(city_id) % num_shards
```

### 6.2 Caching Strategy (Multi-Level)

```
Layer 1: Browser Cache
- Movie posters, trailers
- TTL: 24 hours

Layer 2: CDN (CloudFront)
- Static assets, images
- TTL: 24 hours

Layer 3: Redis (Application Cache)
- Search results: TTL 5 min
- Seat availability: TTL 30 sec
- Theater listings: TTL 1 hour

Layer 4: Database Query Cache
- Read replicas for search queries
```

### 6.3 Read Replicas

```
Primary DB: All writes (bookings, payments)
Replica 1: Search queries
Replica 2: Analytics, reports
Replica 3: Backup

Replication lag: < 1 second (acceptable for search)
```

### 6.4 Auto-Scaling

```
Kubernetes HPA (Horizontal Pod Autoscaler):

Booking Service:
- Min: 5 pods
- Max: 50 pods
- Scale up: CPU > 70% OR requests > 1000 per pod
- Scale down: CPU < 30% for 5 minutes

Database:
- Primary: Vertical scaling (bigger instance)
- Replicas: Horizontal scaling (more replicas)

Redis:
- Cluster mode: 6 nodes (3 primary + 3 replica)
- Auto-failover enabled
```

### 6.5 Rate Limiting

```
Per User:
- Search: 100 requests/min
- Booking: 10 requests/min
- Payment: 5 requests/min

Per IP:
- 500 requests/min (prevents DDoS)

Implementation:
- Token Bucket algorithm
- Redis for distributed rate limiting
- Return 429 Too Many Requests when exceeded
```

---

## SECTION 7: INTERVIEW Q&A

### Q1: How do you prevent double booking?

**Answer:**

"We use a two-layer locking mechanism:

**Layer 1: Redis Distributed Lock (Fast Path)**
- When user selects seat, we acquire Redis lock using SETNX
- Lock key: `lock:show:{show_id}:seat:{seat_id}`
- TTL: 10 minutes
- Atomic operation ensures only one user gets the lock

**Layer 2: Database Pessimistic Lock (Safety)**
- After acquiring Redis lock, we use SELECT FOR UPDATE in PostgreSQL
- This ensures ACID compliance at database level
- Double-checks seat availability

**Why Both?**
- Redis: Fast, prevents 99% of concurrent access issues
- Database: Safety net, handles edge cases (Redis failure, network partition)

**Example Flow:**
```
1000 users click seat A1 simultaneously
├─ Redis SETNX: User 1 succeeds, 999 fail (< 10ms)
├─ User 1 proceeds to DB lock
├─ Database FOR UPDATE: Ensures consistency
└─ Only User 1 completes booking
```

This approach gives us < 50ms response time for failures and strong consistency guarantees."

---

### Q2: What happens if payment gateway times out?

**Answer:**

"Payment timeouts are handled using the **Saga Pattern** with compensating transactions:

**Scenario:**
1. User books seats, locks acquired
2. Booking created (status: PENDING)
3. Payment gateway called
4. Gateway times out after 30s

**Handling:**

**Immediate Response (Circuit Breaker):**
```
- After 30s timeout, circuit breaker opens
- Return to user: "Payment processing, we'll notify you"
- Booking remains in PENDING state
- Locks remain active for 10 minutes
```

**Background Reconciliation:**
```
- Job runs every 1 minute
- Query payment gateway status API
- Possible outcomes:
  a) Success → Confirm booking, release locks
  b) Failed → Cancel booking, release locks, refund
  c) Still pending → Wait, retry up to 3 times
```

**Idempotency:**
```
- Every payment has unique idempotency key
- Retries use same key
- Gateway deduplicates, prevents double charge
```

**User Experience:**
```
- Email: "Processing your payment..."
- WebSocket: Real-time status update
- If success: "Confirmed!" + ticket PDF
- If fail: "Failed, amount not charged"
- If long pending: "Contact support"
```

**Database State:**
```sql
UPDATE bookings 
SET status = CASE 
    WHEN payment_status = 'SUCCESS' THEN 'CONFIRMED'
    WHEN payment_status = 'FAILED' THEN 'CANCELLED'
    ELSE 'PENDING'
END
WHERE id = ?;
```

**Monitoring:**
- Alert if pending bookings > 100
- Dashboard showing payment success rate
- Circuit breaker metrics"

---

### Q3: How do you handle peak load (Friday evening, new movie release)?

**Answer:**

"We use a multi-pronged approach:

**1. Predictive Scaling (Before Peak)**
```
- Historical data: Friday 6-10 PM = 10x normal load
- Pre-scale Booking Service: 5 → 30 pods (1 hour before)
- Warm up Redis connections
- Increase database connection pool
```

**2. Rate Limiting (During Peak)**
```
- Per user: 10 booking requests/min
- Per IP: 500 requests/min
- Priority queue: Logged-in users > guests
```

**3. Graceful Degradation**
```
Priority 1 (Critical): Booking, Payment
Priority 2 (Important): Seat availability
Priority 3 (Optional): Reviews, recommendations

If CPU > 90%:
- Disable Priority 3 features
- Serve stale cache for Priority 2
- All resources to Priority 1
```

**4. Queueing System**
```
- If bookings/sec > threshold (100)
- Put users in virtual queue
- Show position: "You are #45 in queue"
- Process FIFO, 10 users/sec
```

**5. Database Optimizations**
```
- Read queries → Replicas (3 replicas during peak)
- Write queries → Primary with connection pooling
- Prepared statements (pre-compiled queries)
- Index on (show_id, seat_status, show_date)
```

**6. Caching Aggressive**
```
Normal: Search cache TTL = 5 min
Peak: Search cache TTL = 1 min (slightly stale OK)
- Reduces DB queries by 80%
```

**7. Monitoring & Alerts**
```
- Real-time dashboard: requests/sec, latency, errors
- Auto-alert if:
  - Latency > 3s
  - Error rate > 1%
  - Queue length > 1000
- On-call engineer gets paged
```

**Real Example:**
```
Normal: 10 bookings/sec, 5 pods, 200ms latency
Peak (Avengers Endgame release):
├─ 120 bookings/sec
├─ Auto-scaled to 40 pods
├─ Queued 500 users
├─ Maintained 400ms latency
└─ Zero errors
```"

---

### Q4: How do you design the seat layout schema?

**Answer:**

"Seat layouts vary greatly (IMAX vs regular, theater-specific), so I use **MongoDB for flexibility**:

**Why MongoDB?**
- Different theaters have different layouts
- Adding new seat types shouldn't require schema migration
- Nested structure naturally represents rows → seats

**Schema:**
```javascript
{
  _id: ObjectId("..."),
  theater_id: "pvr_phoenix_mumbai",
  screen_id: "screen_1",
  layout: {
    total_seats: 120,
    rows: [
      {
        row_name: "A",
        row_type: "RECLINER",  // Optional: row-level pricing
        seats: [
          {number: "A1", type: "RECLINER", price: 500, is_available: true},
          {number: "A2", type: "RECLINER", price: 500, is_available: true},
          {type: "AISLE"},  // Represents gap in layout
          {number: "A3", type: "RECLINER", price: 500, is_available: false}
        ]
      },
      {
        row_name: "B",
        row_type: "PREMIUM",
        seats: [
          {number: "B1", type: "PREMIUM", price: 350},
          {number: "B2", type: "PREMIUM", price: 350}
        ]
      }
    ],
    special_features: ["wheelchair_access", "couple_seats"],
    metadata: {
      screen_type: "IMAX",
      sound_system: "Dolby Atmos"
    }
  }
}
```

**Benefits:**
1. Theater can customize any layout
2. Add new seat types without code changes
3. Aisles, gaps, wheelchair seats easily represented
4. Pricing embedded (no separate table)

**PostgreSQL for Bookings:**
```sql
-- We still use PostgreSQL for actual bookings (ACID)
CREATE TABLE screen_seats (
    id SERIAL PRIMARY KEY,
    screen_id INT,
    seat_number VARCHAR,
    seat_type VARCHAR,
    mongo_doc_id VARCHAR  -- Reference to MongoDB layout
);
```

**Hybrid Approach:**
- MongoDB: Layout definition (read-heavy)
- PostgreSQL: Booking transactions (write-heavy)
- Best of both worlds"

---

### Q5: How would you implement a "Hold Seat" feature for payment processing?

**Answer:**

"The current design already implements this with Redis locks:

**Current Flow:**
```
1. User selects seats → Redis lock acquired (TTL: 10 min)
2. Booking created (status: PENDING)
3. User has 10 minutes to complete payment
4. If payment succeeds → Confirm booking, release lock
5. If 10 minutes elapse → Background job expires booking
```

**Enhanced Flow (with UI countdown):**

**Backend:**
```java
// When booking created
String lockKey = "lock:show:" + showId + ":seat:" + seatId;
long ttl = redis.getExpire(lockKey, TimeUnit.SECONDS);

return BookingResponse.builder()
    .bookingId(booking.getId())
    .expiresAt(System.currentTimeMillis() + (ttl * 1000))
    .expiresIn(ttl)  // seconds remaining
    .build();
```

**Frontend (React):**
```javascript
function PaymentPage({ booking }) {
  const [timeLeft, setTimeLeft] = useState(booking.expiresIn);
  
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          alert("Booking expired!");
          navigate('/');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    
    return () => clearInterval(timer);
  }, []);
  
  return (
    <div>
      <h2>Complete payment in: {formatTime(timeLeft)}</h2>
      <PaymentForm />
    </div>
  );
}
```

**Extension Mechanism:**
```
If user clicks "Need more time":
- Check if payment initiated
- If yes, extend by 5 minutes (one time only)
- Update Redis TTL: EXPIRE lockKey 300
```

**Fairness:**
- Can't hold seats indefinitely
- Other users see real-time availability
- Expired seats immediately available

This creates urgency while being fair to all users."

---

### Q6: How do you handle refunds for cancelled bookings?

**Answer:**

"Refunds follow business rules with technical implementation:

**Business Rules:**
```
Cancellation Window          Refund %     Processing
────────────────────────────────────────────────────────────
> 24 hours before show       100%         Automatic
4-24 hours before show       50%          Automatic
< 4 hours before show        0%           Not allowed
After show start             0%           Not allowed
```

**Technical Implementation:**

**Step 1: Validation**
```java
public RefundResponse processCancellation(Long bookingId, Long userId) {
    Booking booking = bookingRepo.findByIdAndUserId(bookingId, userId);
    
    if (booking == null) {
        throw new NotFoundException("Booking not found");
    }
    
    if (booking.getStatus() != BookingStatus.CONFIRMED) {
        throw new InvalidStateException("Only confirmed bookings can be cancelled");
    }
    
    Show show = showRepo.findById(booking.getShowId());
    Duration timeUntilShow = Duration.between(LocalDateTime.now(), show.getShowDateTime());
    
    if (timeUntilShow.toHours() < 4) {
        throw new CancellationNotAllowedException("Cannot cancel < 4 hours before show");
    }
    
    // Calculate refund percentage
    double refundPercent = timeUntilShow.toHours() >= 24 ? 1.0 : 0.5;
    BigDecimal refundAmount = booking.getTotalAmount().multiply(BigDecimal.valueOf(refundPercent));
    
    // Rest of processing...
}
```

**Step 2: Database Transaction**
```sql
BEGIN TRANSACTION;

-- Update booking status
UPDATE bookings 
SET status = 'CANCELLED',
    cancelled_at = NOW()
WHERE id = ?;

-- Free up seats
UPDATE show_seats 
SET status = 'AVAILABLE',
    booked_by = NULL
WHERE show_id = ? AND seat_id IN (?);

-- Record refund
INSERT INTO refunds (booking_id, amount, status, initiated_at)
VALUES (?, ?, 'PENDING', NOW());

COMMIT;
```

**Step 3: Payment Gateway**
```java
// Call payment gateway refund API
RefundRequest refundRequest = RefundRequest.builder()
    .paymentId(payment.getTransactionId())
    .amount(refundAmount)
    .reason("User cancelled booking")
    .idempotencyKey("refund_" + booking.getBookingNumber())
    .build();

RefundResponse response = stripeClient.createRefund(refundRequest);

// Update refund status
refundRepo.updateStatus(refund.getId(), response.getStatus());
```

**Step 4: Async Processing**
```java
// Publish event
kafkaTemplate.send("booking.cancelled", BookingCancelledEvent.builder()
    .bookingId(booking.getId())
    .userId(userId)
    .refundAmount(refundAmount)
    .build());

// Consumers:
// 1. Email service → Send cancellation confirmation
// 2. Notification service → Push notification
// 3. Analytics → Track cancellation metrics
```

**Idempotency:**
```
- User can't cancel twice
- Refund has unique idempotency key
- Gateway deduplicates
```

**Monitoring:**
```
- Track refund success rate (should be > 99%)
- Alert if pending refunds > 100
- Daily reconciliation with payment gateway
```"

---

### Q7: How would you add a "Waitlist" feature?

**Answer:**

"Waitlist for sold-out shows is a great feature:

**Design:**

**Database Schema:**
```sql
CREATE TABLE waitlist (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    show_id BIGINT,
    num_seats INT,
    preferred_seat_type VARCHAR,  -- PREMIUM, REGULAR, etc.
    created_at TIMESTAMP,
    notified BOOLEAN DEFAULT false,
    expires_at TIMESTAMP,
    
    UNIQUE(user_id, show_id)  -- One waitlist entry per user per show
);

CREATE INDEX idx_waitlist_show ON waitlist(show_id, created_at);
```

**Flow:**

**1. User Joins Waitlist:**
```
POST /api/shows/{showId}/waitlist
Body: {
  num_seats: 2,
  preferred_seat_type: "PREMIUM"
}

Response:
{
  position: 15,  // 15th in queue
  message: "We'll notify you if seats become available"
}
```

**2. Cancellation Triggers Waitlist:**
```java
@Transactional
public void onBookingCancelled(BookingCancelledEvent event) {
    // Seats just became available
    List<String> availableSeats = event.getSeats();
    
    // Get waitlist entries for this show, ordered by created_at (FIFO)
    List<WaitlistEntry> waitlist = waitlistRepo.findByShowIdOrderByCreatedAt(event.getShowId());
    
    for (WaitlistEntry entry : waitlist) {
        if (entry.isNotified()) continue;
        
        // Check if we have enough seats of preferred type
        long matchingSeats = availableSeats.stream()
            .filter(seat -> seat.getType().equals(entry.getPreferredSeatType()))
            .count();
        
        if (matchingSeats >= entry.getNumSeats()) {
            // Send notification
            notificationService.send(entry.getUserId(), 
                "Seats available for " + show.getMovie().getTitle() + "! Book now.");
            
            // Mark as notified
            entry.setNotified(true);
            entry.setExpiresAt(LocalDateTime.now().plusMinutes(15));  // 15 min to book
            waitlistRepo.save(entry);
            
            // Remove from available pool
            availableSeats.removeIf(seat -> seat.getType().equals(entry.getPreferredSeatType()));
            
            if (availableSeats.size() < 2) break;  // Not enough for next person
        }
    }
}
```

**3. User Books from Waitlist:**
```
- User gets push notification + SMS
- Deep link opens app to booking page
- User has 15 minutes to complete booking
- If expired, next person in waitlist gets notified
```

**Features:**
- FIFO fairness
- Preference matching (seat type, quantity)
- Time-bound notifications (15 min)
- Cascade to next user if expired

**Scale:**
- Redis Pub/Sub for real-time notifications
- Kafka for async processing
- Background job removes expired waitlist entries"

---

## SECTION 8: MONITORING & OBSERVABILITY

### 8.1 Key Metrics

**Service-Level Indicators (SLIs):**
```
Booking Service:
- Success rate: > 99.9%
- Latency p50: < 200ms
- Latency p99: < 2s
- Lock acquisition time: < 10ms

Search Service:
- Latency p99: < 500ms
- Cache hit rate: > 80%

Payment Service:
- Success rate: > 99%
- Gateway timeout rate: < 1%
```

**Business Metrics:**
```
- Bookings per minute
- Revenue per minute
- Average booking value
- Cancellation rate
- Seat utilization (booked/total)
```

### 8.2 Alerting

```
Critical (PagerDuty):
- Booking service error rate > 1%
- Payment gateway down
- Database connection pool exhausted
- Redis cluster down

Warning (Slack):
- Latency p99 > 3s
- Cache hit rate < 70%
- Pending bookings > 1000
```

### 8.3 Distributed Tracing

```
Jaeger/AWS X-Ray:

Request flow:
┌─────────────────────────────────────────────────┐
│ Trace ID: abc123                                │
│                                                 │
│ Span 1: API Gateway          [50ms]            │
│ Span 2: ├─ Booking Service   [150ms]           │
│ Span 3: │  ├─ Redis Lock     [5ms]             │
│ Span 4: │  ├─ DB Query       [80ms] ← SLOW     │
│ Span 5: │  └─ Payment Svc    [60ms]            │
│ Span 6: └─ Kafka Publish     [5ms]             │
│                                                 │
│ Total: 300ms                                    │
└─────────────────────────────────────────────────┘

Identify bottlenecks quickly
```

---

## APPENDIX: QUICK REFERENCE

### System at a Glance

```
Scale:        100M users, 10M bookings/month, 92 bookings/sec peak
Services:     User, Movie, Theater, Booking, Payment, Search, Notification
Databases:    PostgreSQL (ACID), MongoDB (flexible), Redis (locking), 
              Elasticsearch (search)
Queue:        Kafka (booking-events, payment-events, notifications)
Caching:      Multi-level (CDN, Redis, DB replicas)
Locking:      Redis SETNX + PostgreSQL FOR UPDATE
```

### Key Trade-offs

```
1. Redis vs DB Locking: Both for defense in depth
2. MongoDB vs PostgreSQL: Flexible schema vs ACID
3. Strong vs Eventual: Strong for booking, eventual for search
4. Microservices vs Monolith: Microservices for scale
5. Sync vs Async: Sync for booking, async for notifications
```

### Must-Mention Points (Unique to BookMyShow)

```
✅ Distributed locking (Redis SETNX) for seat booking
✅ Pessimistic locking (FOR UPDATE) in database
✅ Seat lock expiry (10 min TTL) with background cleanup
✅ Two-phase commit (Redis + DB) for consistency
✅ SAGA pattern for payment failures
✅ Sharding by city for geographic locality
✅ MongoDB for flexible theater layouts
✅ Real-time seat availability (WebSocket + Redis Pub/Sub)
✅ Cancellation with refund workflow
✅ Rate limiting and graceful degradation
```

---

**END OF INTERVIEW GUIDE**

**Total:** ~1400 lines | **Estimated PDF:** 30-35 pages
