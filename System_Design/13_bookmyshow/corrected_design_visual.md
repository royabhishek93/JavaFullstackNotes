# BookMyShow - Complete Visual System Design

## 📊 PART 1: DATABASE SCHEMA (Entity-Relationship Diagram)

### Complete Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATABASE SCHEMA - COMPLETE VIEW                    │
└─────────────────────────────────────────────────────────────────────────────┘


        ┌──────────────────┐
        │   City Entity    │
        │──────────────────│
        │ PK: id           │
        │     name         │
        │     state        │
        │     country      │
        │     latitude     │
        │     longitude    │
        │     created_at   │
        └────────┬─────────┘
                 │
                 │ 1:N (One city has many theaters)
                 │
        ┌────────▼─────────┐
        │ Theater Entity   │
        │──────────────────│
        │ PK: id           │
        │ FK: city_id      │
        │     name         │
        │     address      │
        │     pin_code     │
        │     latitude     │
        │     longitude    │
        │     amenities    │◄──────── JSON: ["Parking", "Food Court", "Wheelchair"]
        │     rating       │
        │     created_at   │
        └────────┬─────────┘
                 │
                 │ 1:N (One theater has many screens)
                 │
        ┌────────▼─────────┐
        │  Screen Entity   │
        │──────────────────│
        │ PK: id           │
        │ FK: theater_id   │
        │     name         │◄──────── "Screen 1 - IMAX"
        │     screen_type  │◄──────── ENUM: IMAX, 3D, 4DX, STANDARD
        │     total_rows   │◄──────── 20
        │     seats_per_row│◄──────── 30
        │     total_seats  │◄──────── 600
        │     created_at   │
        └────────┬─────────┘
                 │
                 │ 1:N (One screen has many seats)
                 │
        ┌────────▼─────────┐
        │   Seat Entity    │
        │──────────────────│
        │ PK: id           │
        │ FK: screen_id    │
        │     row_number   │◄──────── 'A', 'B', 'C'...'Z'
        │     seat_number  │◄──────── 1, 2, 3...30
        │     seat_type    │◄──────── ENUM: NORMAL, PREMIUM, RECLINER
        │     price_mult   │◄──────── 1.0, 1.5, 2.0
        │     created_at   │
        └──────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                    MOVIE & SHOW HIERARCHY                                    │
└─────────────────────────────────────────────────────────────────────────────┘

        ┌────────────────────┐
        │   Movie Entity     │
        │────────────────────│
        │ PK: id             │
        │     title          │◄──────── "Avengers: Endgame"
        │     genre          │◄──────── "Action, Sci-Fi"
        │     duration_mins  │◄──────── 180
        │     language       │◄──────── "English, Hindi"
        │     release_date   │
        │     rating         │◄──────── "PG-13"
        │     poster_url     │
        │     synopsis       │
        │     director       │
        │     cast           │◄──────── JSON array
        │     created_at     │
        └──────────┬─────────┘
                   │
                   │ 1:N (One movie has many shows)
                   │
        ┌──────────▼───────────┐
        │   Show Entity ⭐     │
        │──────────────────────│
        │ PK: id               │
        │ FK: movie_id         │
        │ FK: screen_id        │
        │     show_date        │◄──────── 2024-04-05
        │     start_time       │◄──────── 10:00:00
        │     end_time         │◄──────── 13:00:00
        │     price_per_seat   │◄──────── 250.00
        │     available_seats  │◄──────── 580 (denormalized for quick lookup)
        │     total_seats      │◄──────── 600
        │     is_running       │◄──────── true/false
        │     created_at       │
        └──────────┬───────────┘
                   │
                   │ 1:N (One show has many seat availabilities)
                   │
        ┌──────────▼─────────────────┐
        │ SeatAvailability Entity ⭐│
        │────────────────────────────│
        │ PK: (show_id, seat_id)    │◄──── Composite Primary Key
        │ FK: show_id                │
        │ FK: seat_id                │
        │ FK: booking_id (nullable)  │
        │     status                 │◄──── ENUM: AVAILABLE, RESERVED, BOOKED
        │     reserved_until         │◄──── TIMESTAMP (15 mins hold)
        │     updated_at             │
        └────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                    USER, BOOKING & PAYMENT FLOW                              │
└─────────────────────────────────────────────────────────────────────────────┘

        ┌────────────────────┐
        │   User Entity      │
        │────────────────────│
        │ PK: id             │
        │     email          │◄──────── UNIQUE
        │     phone          │◄──────── UNIQUE
        │     name           │
        │     password_hash  │
        │     wallet_balance │◄──────── 5000.00
        │     preferences    │◄──────── JSON: {"genres": ["Action"], "lang": ["Hindi"]}
        │     created_at     │
        │     updated_at     │
        └──────────┬─────────┘
                   │
                   │ 1:N (One user has many bookings)
                   │
        ┌──────────▼───────────────┐
        │   Booking Entity ⭐      │
        │──────────────────────────│
        │ PK: id (UUID)            │
        │ FK: user_id              │
        │ FK: show_id              │
        │     total_seats          │◄──────── 3
        │     total_price          │◄──────── 750.00
        │     booking_status       │◄──────── ENUM: PENDING, CONFIRMED, CANCELLED, EXPIRED
        │     payment_id           │◄──────── FK to Payment (nullable)
        │     created_at           │
        │     expires_at           │◄──────── created_at + 15 mins
        │     confirmed_at         │
        │     cancelled_at         │
        └──────────┬───────────────┘
                   │
                   │ 1:N (One booking has many seats)
                   │
        ┌──────────▼───────────────┐
        │ BookingSeat Entity       │
        │──────────────────────────│
        │ PK: id                   │
        │ FK: booking_id           │
        │ FK: seat_id              │
        │     UNIQUE(booking_id,   │
        │            seat_id)      │
        └──────────────────────────┘


        ┌──────────────────────┐
        │  Payment Entity ⭐   │
        │──────────────────────│
        │ PK: id (UUID)        │
        │ FK: booking_id       │◄──────── 1:1 relationship
        │ FK: user_id          │
        │     amount           │◄──────── 750.00
        │     payment_mode     │◄──────── ENUM: CARD, UPI, WALLET, NET_BANKING
        │     transaction_id   │◄──────── From gateway (UNIQUE)
        │     gateway_name     │◄──────── "Stripe", "Razorpay", "PayU"
        │     idempotency_key  │◄──────── For duplicate prevention (UNIQUE)
        │     status           │◄──────── ENUM: PENDING, SUCCESS, FAILED, REFUNDED
        │     failure_reason   │
        │     created_at       │
        │     processed_at     │
        │     refunded_at      │
        └──────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                           REVIEW SYSTEM                                      │
└─────────────────────────────────────────────────────────────────────────────┘

        ┌────────────────────┐
        │  Review Entity     │
        │────────────────────│
        │ PK: id             │
        │ FK: user_id        │
        │ FK: movie_id       │
        │     rating         │◄──────── 1-5 stars
        │     comment        │◄──────── TEXT
        │     is_verified    │◄──────── true if user actually watched
        │     helpful_count  │◄──────── Upvotes
        │     created_at     │
        │     updated_at     │
        │                    │
        │ UNIQUE(user_id,    │
        │        movie_id)   │◄──────── One review per user per movie
        └────────────────────┘
```

---

## 🔗 PART 2: RELATIONSHIP DIAGRAM (With Cardinality)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               ENTITY RELATIONSHIPS WITH CARDINALITY                          │
└─────────────────────────────────────────────────────────────────────────────┘


    CITY                    THEATER                 SCREEN                  SEAT
    ┌────┐ 1           N    ┌────┐ 1          N    ┌────┐ 1          N    ┌────┐
    │City├──────────────────►Theater├──────────────►Screen├─────────────────►Seat│
    └────┘                  └────┘                 └────┘                  └────┘
     │                                               │
     │                                               │ N
     │                                               │
     │                                               ▼ 1
     │                                              ┌────┐
     │                                              │Show│
     │                                              └──┬─┘
     │                                                 │ 1
     │                                                 │
     │                                                 ▼ N
    ┌▼────┐ 1                                    ┌────────────────┐
    │Movie│────────────────────────────────────►│SeatAvailability│
    └─────┘                                      └────────────────┘
     │ 1                                               │ N
     │                                                 │
     │                                                 │
     │ N                                               │ N
     ▼                                                 ▼
    ┌──────┐                                      ┌────────┐
    │Review│                                      │BookingSeat│
    └──────┘                                      └────┬───┘
     │ N                                               │ N
     │                                                 │
     │                                                 ▼ 1
     │                                             ┌───────┐
     │ N                                      ┌───►Booking│
     │                                        │    └───┬───┘
    ┌▼───┐ 1                             1   │        │ 1
    │User├────────────────────────────────────┘        │
    └────┘                                             ▼ 1
                                                   ┌───────┐
                                                   │Payment│
                                                   └───────┘


LEGEND:
═══════════════════════════════════════════════════
1       = One
N       = Many
1:N     = One-to-Many
N:1     = Many-to-One
N:M     = Many-to-Many (requires join table)
═══════════════════════════════════════════════════

KEY RELATIONSHIPS:
──────────────────────────────────────────────────
1. City → Theater (1:N)           One city has many theaters
2. Theater → Screen (1:N)         One theater has many screens
3. Screen → Seat (1:N)            One screen has many seats
4. Screen → Show (1:N)            One screen has many shows
5. Movie → Show (1:N)             One movie has many shows
6. Show → SeatAvailability (1:N)  One show has seat status for all seats
7. User → Booking (1:N)           One user has many bookings
8. User → Review (1:N)            One user has many reviews
9. Movie → Review (1:N)           One movie has many reviews
10. Booking → BookingSeat (1:N)   One booking has many seats
11. Booking → Payment (1:1)       One booking has one payment
12. Seat → BookingSeat (1:N)      One seat can be in many bookings (different shows)
```

---

## 🏗️ PART 3: COMPLETE SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COMPLETE SYSTEM ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────────────────┘


                            ┌─────────────────────────┐
                            │    CLIENT LAYER         │
                            ├─────────────────────────┤
                            │ [Web App] [Mobile App]  │
                            │ [Progressive Web App]   │
                            └────────────┬────────────┘
                                         │
                                         │ HTTPS/TLS
                                         │
                            ┌────────────▼────────────┐
                            │    CDN (CloudFlare)     │
                            ├─────────────────────────┤
                            │ Cache:                  │
                            │ - Movie posters         │
                            │ - Static assets         │
                            │ - Theater images        │
                            │ TTL: 24 hours           │
                            └────────────┬────────────┘
                                         │
                            ┌────────────▼────────────┐
                            │  API GATEWAY (Kong)     │
                            ├─────────────────────────┤
                            │ ✓ Rate Limiting         │
                            │   (100 req/min/user)    │
                            │ ✓ Authentication (JWT)  │
                            │ ✓ Request Routing       │
                            │ ✓ Load Balancing        │
                            │ ✓ SSL Termination       │
                            └───┬────────────┬────────┘
                                │            │
                ┌───────────────┼────────────┼───────────────┐
                │               │            │               │
        ┌───────▼───────┐ ┌────▼─────┐ ┌───▼──────┐ ┌─────▼─────┐
        │ SEARCH SERVICE│ │BOOKING SVC│ │PAYMENT SVC│ │ USER SVC  │
        ├───────────────┤ ├───────────┤ ├───────────┤ ├───────────┤
        │ Stateless     │ │ Stateful  │ │  Bridge   │ │ Stateless │
        │ Read-heavy    │ │Write-heavy│ │ Stateless │ │Read/Write │
        │               │ │           │ │           │ │           │
        │ Endpoints:    │ │Endpoints: │ │Endpoints: │ │Endpoints: │
        │ /search       │ │/book      │ │/pay       │ │/register  │
        │ /movies       │ │/confirm   │ │/refund    │ │/login     │
        │ /theaters     │ │/cancel    │ │/status    │ │/profile   │
        │ /shows        │ │/seats     │ │           │ │           │
        │               │ │           │ │           │ │           │
        │ Replicas: 10  │ │Replicas: 5│ │Replicas: 3│ │Replicas: 3│
        └───────┬───────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
                │               │             │             │
                │               │             │             │
        ┌───────▼───────────────▼─────────────▼─────────────▼─────────┐
        │              CACHE LAYER (Redis Cluster)                     │
        ├──────────────────────────────────────────────────────────────┤
        │                                                               │
        │  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐ │
        │  │ Search Cache    │  │ Seat Status Cache│  │ User Session│ │
        │  ├─────────────────┤  ├──────────────────┤  ├────────────┤ │
        │  │ Key:            │  │ Key:             │  │ Key:       │ │
        │  │ city:Mumbai:    │  │ show:123:seats   │  │ session:   │ │
        │  │ date:2024-04-05 │  │                  │  │ user:456   │ │
        │  │                 │  │ Value: {         │  │            │ │
        │  │ Value: [        │  │   seat_1: AVAIL  │  │ Value:     │ │
        │  │   movie_ids     │  │   seat_2: BOOKED │  │ {cart: [], │ │
        │  │ ]               │  │   seat_5: RESERVED}  │ token: }  │ │
        │  │                 │  │                  │  │            │ │
        │  │ TTL: 5 mins     │  │ TTL: 30 secs     │  │ TTL: 30min │ │
        │  └─────────────────┘  └──────────────────┘  └────────────┘ │
        │                                                               │
        │  ┌──────────────────────────────────────────────────────┐   │
        │  │         Redis Pub/Sub (Real-time Updates)            │   │
        │  ├──────────────────────────────────────────────────────┤   │
        │  │ Channels:                                            │   │
        │  │ - show:123:seat_update                               │   │
        │  │ - booking:456:confirmed                              │   │
        │  │ - payment:789:success                                │   │
        │  │                                                       │   │
        │  │ Subscribers: WebSocket servers, Notification service │   │
        │  └──────────────────────────────────────────────────────┘   │
        └───────────────────────────┬──────────────────────────────────┘
                                    │
        ┌───────────────────────────┼──────────────────────────────────┐
        │                           │                                   │
        │                           │                                   │
┌───────▼────────┐  ┌──────────────▼──────┐  ┌─────────────────────────────┐
│   PostgreSQL   │  │      MySQL          │  │    Elasticsearch            │
├────────────────┤  ├─────────────────────┤  ├─────────────────────────────┤
│ TRANSACTIONS   │  │ CATALOG DATA        │  │ FULL-TEXT SEARCH            │
├────────────────┤  ├─────────────────────┤  ├─────────────────────────────┤
│                │  │                     │  │                             │
│ Tables:        │  │ Tables:             │  │ Indices:                    │
│ ✓ booking      │  │ ✓ movies            │  │ ✓ movies                    │
│ ✓ booking_seat │  │ ✓ theaters          │  │ ✓ theaters                  │
│ ✓ payment      │  │ ✓ screens           │  │                             │
│ ✓ seat_avail   │  │ ✓ seats             │  │ Query Types:                │
│ ✓ users        │  │ ✓ cities            │  │ - Full-text search          │
│                │  │ ✓ reviews           │  │ - Geo-spatial queries       │
│ Isolation:     │  │                     │  │ - Faceted search            │
│ SERIALIZABLE   │  │ Replication:        │  │ - Aggregations              │
│                │  │ Master → Slave×3    │  │                             │
│ Sharding:      │  │                     │  │ Sharding: By city_id        │
│ By city_id     │  │ Read-heavy queries  │  │                             │
│                │  │ routed to replicas  │  │ Data Sync: Kafka → ES       │
│ Master: 1      │  │                     │  │ Lag: < 5 seconds            │
│ Shards: 10     │  │                     │  │                             │
│ (by city)      │  │                     │  │ Cluster: 5 nodes            │
└────────┬───────┘  └──────────┬──────────┘  └────────────┬────────────────┘
         │                     │                          │
         │                     │                          │
         └─────────────────────┼──────────────────────────┘
                               │
                               │
                ┌──────────────▼────────────────┐
                │  MESSAGE QUEUE (Kafka/SQS)    │
                ├───────────────────────────────┤
                │                               │
                │ Topics:                       │
                │ ┌──────────────────────────┐  │
                │ │ booking.confirmed        │  │
                │ │ booking.cancelled        │  │
                │ │ payment.success          │  │
                │ │ payment.failed           │  │
                │ │ seat.expired             │  │
                │ │ theater.updated          │  │
                │ │ movie.added              │  │
                │ └──────────────────────────┘  │
                │                               │
                │ Partitions: 10 (by city_id)   │
                │ Replication: 3                │
                │ Retention: 7 days             │
                └──────────────┬────────────────┘
                               │
                               │ Async Processing
                               │
        ┌──────────────────────▼─────────────────────────────────┐
        │              BACKGROUND WORKERS                         │
        ├─────────────────────────────────────────────────────────┤
        │                                                          │
        │  ┌──────────────────┐  ┌──────────────────────────┐   │
        │  │ Email Service    │  │ Seat Expiry Job          │   │
        │  ├──────────────────┤  ├──────────────────────────┤   │
        │  │ Provider:        │  │ Schedule: */5 mins       │   │
        │  │ SendGrid/SES     │  │                          │   │
        │  │                  │  │ Logic:                   │   │
        │  │ Triggered by:    │  │ 1. Find expired bookings │   │
        │  │ - booking.       │  │ 2. Release seats         │   │
        │  │   confirmed      │  │ 3. Update cache          │   │
        │  │ - payment.failed │  │ 4. Send notification     │   │
        │  └──────────────────┘  └──────────────────────────┘   │
        │                                                          │
        │  ┌──────────────────┐  ┌──────────────────────────┐   │
        │  │ SMS/Push Service │  │ Analytics Worker         │   │
        │  ├──────────────────┤  ├──────────────────────────┤   │
        │  │ Provider: Twilio │  │ Process logs to:         │   │
        │  │                  │  │ - Revenue metrics        │   │
        │  │ Notifications:   │  │ - Popular movies         │   │
        │  │ - Booking confirm│  │ - Peak hours             │   │
        │  │ - Show reminder  │  │ - Cancellation rates     │   │
        │  │   (2h before)    │  │                          │   │
        │  └──────────────────┘  └──────────────────────────┘   │
        │                                                          │
        │  ┌──────────────────────────────────────────────────┐  │
        │  │ Data Sync Worker (MySQL → Elasticsearch)         │  │
        │  ├──────────────────────────────────────────────────┤  │
        │  │ Consumes: theater.updated, movie.added           │  │
        │  │ Updates: ES indices for search                   │  │
        │  │ Lag: < 5 seconds (acceptable for search)         │  │
        │  └──────────────────────────────────────────────────┘  │
        └──────────────────────────────────────────────────────────┘


┌────────────────────────────────────────────────────────────────────────┐
│                      EXTERNAL SERVICES                                  │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐  ┌────────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ Payment      │  │ Email/SMS  │  │ Storage  │  │ Monitoring     │  │
│  │ Gateways     │  │ Services   │  │ (S3)     │  │ & Logging      │  │
│  ├──────────────┤  ├────────────┤  ├──────────┤  ├────────────────┤  │
│  │ - Stripe     │  │ - SendGrid │  │ - Posters│  │ - CloudWatch   │  │
│  │ - Razorpay   │  │ - Twilio   │  │ - Tickets│  │ - DataDog      │  │
│  │ - PayU       │  │ - Firebase │  │ - Logs   │  │ - Prometheus   │  │
│  │              │  │   (Push)   │  │          │  │ - Grafana      │  │
│  └──────────────┘  └────────────┘  └──────────┘  └────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🎬 PART 4: SEAT BOOKING FLOW (Critical Path)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  SEAT BOOKING FLOW - STEP BY STEP                            │
└─────────────────────────────────────────────────────────────────────────────┘


STEP 1: USER SEARCHES FOR MOVIE
════════════════════════════════════════════════════════════════════════════════

    ┌──────────┐
    │  User A  │ Search "Avengers in Mumbai on 2024-04-05"
    └────┬─────┘
         │
         │ GET /api/v1/movies/search?city=Mumbai&date=2024-04-05
         ▼
    ┌─────────────┐
    │  API Gateway│
    └──────┬──────┘
           │
           │ Route to Search Service
           ▼
    ┌──────────────┐    Check Cache First
    │Search Service│───────────────────┐
    └──────┬───────┘                   │
           │                           │
           │ Cache Miss?               ▼
           │                      ┌─────────┐
           ▼                      │  Redis  │
    ┌──────────────┐             │  Cache  │
    │Elasticsearch │             └─────────┘
    │  Index Query │                   │
    └──────┬───────┘                   │
           │                           │
           │ Return results            │
           └───────────────────────────┘
                       │
                       │ Cache result (TTL: 5 mins)
                       ▼
                  ┌─────────┐
                  │  Redis  │
                  │  SET    │
                  └─────────┘

    Response: [
      {
        movie_id: 123,
        title: "Avengers: Endgame",
        theaters: [
          {theater_id: 1, name: "PVR Phoenix", shows: [...]}
        ]
      }
    ]



STEP 2: USER VIEWS SEAT MAP
════════════════════════════════════════════════════════════════════════════════

    ┌──────────┐
    │  User A  │ Click "Show 123" to see seats
    └────┬─────┘
         │
         │ GET /api/v1/shows/123/seats
         ▼
    ┌──────────────┐
    │Booking Service│
    └──────┬───────┘
           │
           │ Check Redis cache
           ▼
    ┌──────────────────┐
    │  Redis: GET      │
    │  show:123:seats  │
    └──────┬───────────┘
           │
     ┌─────┴──────┐
     │            │
  Cache HIT   Cache MISS
     │            │
     │            └──────────────┐
     │                           │
     │                           ▼
     │                    ┌──────────────┐
     │                    │ Query        │
     │                    │ PostgreSQL:  │
     │                    │              │
     │                    │ SELECT * FROM│
     │                    │seat_availability
     │                    │WHERE show_id │
     │                    │= 123         │
     │                    └──────┬───────┘
     │                           │
     │                           │ Update cache
     │                           │
     └───────────┬───────────────┘
                 │
                 ▼
    Response: {
      seats: [
        {seat_id: 1, row: 'A', number: 1, status: 'AVAILABLE', price: 250},
        {seat_id: 2, row: 'A', number: 2, status: 'AVAILABLE', price: 250},
        {seat_id: 5, row: 'A', number: 5, status: 'BOOKED', price: 250},
        ...
      ]
    }



STEP 3: USER SELECTS SEATS (ACQUIRE LOCK)
════════════════════════════════════════════════════════════════════════════════

    ┌──────────┐
    │  User A  │ Select seats [5, 6, 7]
    └────┬─────┘
         │
         │ POST /api/v1/bookings
         │ {show_id: 123, seat_ids: [5,6,7]}
         ▼
    ┌──────────────────┐
    │ Booking Service  │
    └────────┬─────────┘
             │
             │ BEGIN TRANSACTION (Isolation: SERIALIZABLE)
             ▼
    ┌────────────────────────────────────────┐
    │      PostgreSQL - Pessimistic Lock     │
    ├────────────────────────────────────────┤
    │                                        │
    │ Step 1: Lock Seat Rows                 │
    │ ────────────────────────────────────── │
    │ SELECT * FROM seat_availability        │
    │ WHERE show_id = 123                    │
    │   AND seat_id IN (5, 6, 7)             │
    │ FOR UPDATE;  ◄── EXCLUSIVE LOCK        │
    │                                        │
    │ ┌─────────────────────────────────┐   │
    │ │ USER B TRIES SAME SEATS HERE    │   │
    │ │ → BLOCKED, WAITS FOR USER A     │   │
    │ └─────────────────────────────────┘   │
    │                                        │
    │ Step 2: Check Availability             │
    │ ────────────────────────────────────── │
    │ IF all seats status = 'AVAILABLE':     │
    │   PROCEED                              │
    │ ELSE:                                  │
    │   ROLLBACK → Return "Seats taken"      │
    │                                        │
    │ Step 3: Create Booking                 │
    │ ────────────────────────────────────── │
    │ INSERT INTO booking (                  │
    │   id,                                  │
    │   user_id = 456,                       │
    │   show_id = 123,                       │
    │   total_seats = 3,                     │
    │   total_price = 750.00,                │
    │   booking_status = 'PENDING',          │
    │   created_at = NOW(),                  │
    │   expires_at = NOW() + INTERVAL '15m'  │
    │ );                                     │
    │                                        │
    │ -- Returns: booking_id = 999           │
    │                                        │
    │ Step 4: Link Seats                     │
    │ ────────────────────────────────────── │
    │ INSERT INTO booking_seat (             │
    │   booking_id, seat_id                  │
    │ ) VALUES                               │
    │   (999, 5),                            │
    │   (999, 6),                            │
    │   (999, 7);                            │
    │                                        │
    │ Step 5: Reserve Seats                  │
    │ ────────────────────────────────────── │
    │ UPDATE seat_availability               │
    │ SET status = 'RESERVED',               │
    │     reserved_until = NOW() + '15m',    │
    │     booking_id = 999                   │
    │ WHERE show_id = 123                    │
    │   AND seat_id IN (5, 6, 7);            │
    │                                        │
    │ Step 6: Update Available Count         │
    │ ────────────────────────────────────── │
    │ UPDATE shows                           │
    │ SET available_seats =                  │
    │     available_seats - 3                │
    │ WHERE show_id = 123;                   │
    │                                        │
    │ COMMIT; ◄── RELEASE LOCKS              │
    └────────────────────────────────────────┘
             │
             │ Invalidate cache
             ▼
    ┌────────────────────┐
    │ Redis: DEL         │
    │ show:123:seats     │
    └────────────────────┘
             │
             │ Publish real-time update
             ▼
    ┌────────────────────┐
    │ Redis Pub/Sub      │
    │ PUBLISH            │
    │ show:123:update    │
    └────────────────────┘

    Response to User A: {
      booking_id: 999,
      status: "PENDING",
      expires_in: "15 minutes",
      total_price: 750.00,
      seats: [5, 6, 7]
    }

    ┌────────────────────────────┐
    │ Meanwhile, User B's request│
    │ was waiting...             │
    │                            │
    │ After User A commits:      │
    │ User B's query executes    │
    │ → Sees status='RESERVED'   │
    │ → ROLLBACK                 │
    │ → Return "Seats taken"     │
    └────────────────────────────┘



STEP 4: USER COMPLETES PAYMENT
════════════════════════════════════════════════════════════════════════════════

    ┌──────────┐
    │  User A  │ Click "Pay Now" (15 mins timer running)
    └────┬─────┘
         │
         │ POST /api/v1/bookings/999/confirm
         │ {payment_method: "card", card_token: "tok_xxx"}
         ▼
    ┌──────────────────┐
    │ Payment Service  │
    └────────┬─────────┘
             │
             │ Step 1: Validate booking not expired
             ▼
    ┌────────────────────┐
    │ SELECT * FROM      │
    │ booking            │
    │ WHERE id = 999     │
    │   AND expires_at > │
    │   NOW()            │
    │   AND status =     │
    │   'PENDING'        │
    └────────┬───────────┘
             │
      ┌──────┴──────┐
      │             │
   Expired?       Valid
      │             │
      │             ▼
      │      Step 2: Call Payment Gateway
      │             │
      │             ▼
      │      ┌─────────────────────────────┐
      │      │  Stripe API Call            │
      │      ├─────────────────────────────┤
      │      │                             │
      │      │ POST /v1/charges            │
      │      │ {                           │
      │      │   amount: 75000 (cents),    │
      │      │   currency: "INR",          │
      │      │   source: "tok_xxx",        │
      │      │   idempotency_key:          │
      │      │     "booking_999_attempt_1" │◄── Prevents double charge
      │      │ }                           │
      │      └──────────┬──────────────────┘
      │                 │
      │           ┌─────┴──────┐
      │           │            │
      │        SUCCESS      FAILED
      │           │            │
      │           │            └──────────────┐
      │           │                           │
      │           ▼                           ▼
      │    Step 3a: Confirm           Step 3b: Release
      │           │                           │
      │           │                           │
      │    BEGIN TRANSACTION          BEGIN TRANSACTION
      │           │                           │
      │           │                           │
      │    ┌──────▼───────────┐      ┌───────▼──────────┐
      │    │ INSERT payment   │      │ UPDATE           │
      │    │   id, booking_id │      │ seat_availability│
      │    │   transaction_id │      │ SET status =     │
      │    │   status=SUCCESS │      │   'AVAILABLE'    │
      │    │                  │      │ WHERE booking_id │
      │    │ UPDATE booking   │      │   = 999          │
      │    │ SET              │      │                  │
      │    │   status=        │      │ DELETE FROM      │
      │    │   'CONFIRMED',   │      │ booking          │
      │    │   payment_id=xyz │      │ WHERE id = 999   │
      │    │                  │      │                  │
      │    │ UPDATE           │      │ UPDATE shows     │
      │    │ seat_availability│      │ SET available_   │
      │    │ SET status =     │      │   seats += 3     │
      │    │   'BOOKED'       │      │                  │
      │    │ WHERE booking_id │      │                  │
      │    │   = 999          │      │ COMMIT           │
      │    │                  │      └──────────────────┘
      │    │ COMMIT           │              │
      │    └────────┬─────────┘              │
      │             │                        │
      │             │ Step 4: Async Tasks    │
      │             │                        │
      │             ▼                        ▼
      │    ┌────────────────────┐    Return error
      │    │ Kafka Publish:     │    "Payment failed"
      │    │ - booking.confirmed│
      │    │                    │
      │    │ Generate:          │
      │    │ - QR ticket        │
      │    │ - PDF ticket       │
      │    │ - Email            │
      │    │ - SMS              │
      │    └────────────────────┘
      │
      │
      └─────────► Release seats
                  Return error
                  "Booking expired"



STEP 5: REAL-TIME UPDATE TO OTHER USERS
════════════════════════════════════════════════════════════════════════════════

    After User A confirms booking:
    
    ┌────────────────────┐
    │ Redis Pub/Sub      │
    │ PUBLISH            │
    │ "show:123:update"  │
    └──────────┬─────────┘
               │
               │ Broadcast to all subscribers
               │
       ┌───────┼───────┬────────┐
       │       │       │        │
       ▼       ▼       ▼        ▼
    ┌────┐  ┌────┐  ┌────┐  ┌────┐
    │WS-1│  │WS-2│  │WS-3│  │WS-4│ WebSocket Server Instances
    └──┬─┘  └──┬─┘  └──┬─┘  └──┬─┘
       │       │       │        │
       │       │       │        │
       ▼       ▼       ▼        ▼
    ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
    │User │ │User │ │User │ │User │
    │  B  │ │  C  │ │  D  │ │  E  │
    └─────┘ └─────┘ └─────┘ └─────┘
    
    All users watching Show 123 seat map see:
    - Seats 5, 6, 7: RESERVED → BOOKED (real-time)
    - Available seats: 580 → 577
    - Visual update: Red color for booked seats



STEP 6: BACKGROUND - SEAT EXPIRY CLEANUP
════════════════════════════════════════════════════════════════════════════════

    ┌───────────────────┐
    │ Cron Job          │
    │ Runs every 5 mins │
    └─────────┬─────────┘
              │
              │ Find expired bookings
              ▼
    ┌────────────────────────────┐
    │ SELECT * FROM booking      │
    │ WHERE status = 'PENDING'   │
    │   AND expires_at < NOW()   │
    └──────────┬─────────────────┘
               │
               │ For each expired booking:
               ▼
    ┌──────────────────────────────────┐
    │ BEGIN TRANSACTION                │
    │                                  │
    │ UPDATE seat_availability         │
    │ SET status = 'AVAILABLE',        │
    │     booking_id = NULL,           │
    │     reserved_until = NULL        │
    │ WHERE booking_id IN (...)        │
    │                                  │
    │ UPDATE shows                     │
    │ SET available_seats +=           │
    │   (count of released seats)      │
    │                                  │
    │ UPDATE booking                   │
    │ SET status = 'EXPIRED'           │
    │ WHERE id IN (...)                │
    │                                  │
    │ COMMIT                           │
    └──────────┬───────────────────────┘
               │
               │ Notify users
               ▼
    ┌────────────────────────┐
    │ Kafka Publish:         │
    │ - seat.expired         │
    │                        │
    │ Email/SMS:             │
    │ "Your booking expired" │
    │ "Seats released"       │
    └────────────────────────┘
```

---

## 🔐 PART 5: CONCURRENCY CONTROL VISUALIZATION

```
┌─────────────────────────────────────────────────────────────────────────────┐
│         RACE CONDITION: TWO USERS, ONE SEAT - HOW WE PREVENT IT              │
└─────────────────────────────────────────────────────────────────────────────┘


WITHOUT LOCKING (❌ BROKEN - BOTH GET SEAT!)
═══════════════════════════════════════════════════════════════════════════════

    USER A                          USER B
    ══════                          ══════
    
    10:00:00.000                    10:00:00.001
    Click Seat 5                    Click Seat 5
         │                               │
         ▼                               ▼
    SELECT status                   SELECT status
    FROM seat_avail                 FROM seat_avail
    WHERE seat_id=5                 WHERE seat_id=5
         │                               │
         ├─ Returns: AVAILABLE           ├─ Returns: AVAILABLE
         │  (still available!)           │  (still available!)
         │                               │
         ▼                               ▼
    UPDATE status                   UPDATE status
    = 'BOOKED'                      = 'BOOKED'
         │                               │
         ▼                               ▼
    ✅ Success!                     ✅ Success!
    
    RESULT: 💥 BOTH GOT SEAT 5! DOUBLE BOOKING!



WITH PESSIMISTIC LOCKING (✅ CORRECT - ONLY ONE GETS IT)
═══════════════════════════════════════════════════════════════════════════════

    USER A                          USER B
    ══════                          ══════
    
    10:00:00.000                    10:00:00.001
    Click Seat 5                    Click Seat 5
         │                               │
         │ BEGIN TRANSACTION              │ BEGIN TRANSACTION
         │                               │
         ▼                               ▼
    SELECT * FROM                   SELECT * FROM
    seat_availability               seat_availability
    WHERE seat_id=5                 WHERE seat_id=5
    FOR UPDATE; ◄───────────┐       FOR UPDATE; ◄───────────┐
         │                  │            │                  │
         │                  │            │                  │
    ┌────▼─────────┐        │       ┌────▼─────────┐       │
    │ LOCK ACQUIRED│        │       │   BLOCKED!   │       │
    │              │  Exclusive     │   WAITING... │  Can't acquire
    │ (User A has  │  Row Lock      │              │  lock until
    │  exclusive   │        │       │ (Query hangs │  User A releases
    │  lock)       │        │       │  here)       │       │
    └────┬─────────┘        │       └──────────────┘       │
         │                  │                               │
         │ Check status     │                               │
         ▼                  │                               │
    IF status =             │                               │
       'AVAILABLE':         │                               │
         │                  │                               │
         │ Reserve it       │                               │
         ▼                  │                               │
    UPDATE status =         │                               │
      'RESERVED'            │                               │
         │                  │                               │
         │ booking_id=999   │                               │
         │                  │                               │
         ▼                  │                               │
    COMMIT ─────────────────┘◄──────┐                      │
         │                           │                      │
         │ ✅ Lock Released          │                      │
         │                           │                      │
         │                           │   Now User B resumes │
         │                           │   ▼                  │
         │                           │ ┌────────────────┐   │
         │                           │ │ LOCK ACQUIRED! │   │
         │                           │ └───────┬────────┘   │
         │                           │         │            │
         │                           │         ▼            │
         │                           │    Check status      │
         │                           │         │            │
         │                           │         ▼            │
         │                           │    IF status =       │
         │                           │      'RESERVED':     │
         │                           │         │            │
         │                           │         ▼            │
         │                           │    ❌ NOT AVAILABLE │
         │                           │         │            │
         │                           │         ▼            │
         │                           │    ROLLBACK ─────────┘
         │                           │         │
         │                           │         ▼
         ▼                           │    Return error:
    ✅ User A gets seat              │    "Seat already taken"
                                     │
                                     ▼
                                ❌ User B gets error

    RESULT: ✅ Only User A got the seat! User B notified immediately.



LOCKING VISUALIZATION
═══════════════════════════════════════════════════════════════════════════════

    seat_availability table
    ┌──────────┬─────────┬──────────┬────────────┐
    │ show_id  │ seat_id │  status  │ booking_id │
    ├──────────┼─────────┼──────────┼────────────┤
    │   123    │    4    │AVAILABLE │    NULL    │
    │   123    │    5    │AVAILABLE │    NULL    │ ◄─── Target row
    │   123    │    6    │AVAILABLE │    NULL    │
    └──────────┴─────────┴──────────┴────────────┘
                            │
                            │ User A: FOR UPDATE
                            ▼
    ┌───────────────────────────────────────────┐
    │        🔒 EXCLUSIVE ROW LOCK              │
    │        (Only User A can read/write)       │
    └───────────────────────────────────────────┘
                            │
                            │ User B tries FOR UPDATE
                            ▼
    ┌───────────────────────────────────────────┐
    │        ⏸️  WAITING IN QUEUE               │
    │        (Blocked until User A commits)     │
    └───────────────────────────────────────────┘
                            │
                            │ User A: COMMIT
                            ▼
    ┌───────────────────────────────────────────┐
    │        🔓 LOCK RELEASED                   │
    └───────────────────────────────────────────┘
                            │
                            │ User B's turn
                            ▼
    ┌──────────┬─────────┬──────────┬────────────┐
    │ show_id  │ seat_id │  status  │ booking_id │
    ├──────────┼─────────┼──────────┼────────────┤
    │   123    │    4    │AVAILABLE │    NULL    │
    │   123    │    5    │ RESERVED │    999     │ ◄─── Changed!
    │   123    │    6    │AVAILABLE │    NULL    │
    └──────────┴─────────┴──────────┴────────────┘
```

This is production-ready and interview-ready! 🎯

