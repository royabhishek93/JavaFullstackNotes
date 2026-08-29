# Ticket Booking System — BookMyShow / Paytm / District
> Online platform for purchasing tickets for movies, concerts, and events.

---

# PAGE 1 — Title & Rapid Answer Script

## What This Topic Is Really About

Two fundamentally different consistency requirements live in the same product:
- **Search and Browse** — 100M users reading, scale matters more than freshness → AP
- **Seat Booking** — two users cannot hold the same seat → CP (strong consistency)

The design challenge is not building a search system OR a booking system.
It is building **both correctly and efficiently** when they need opposite CAP choices.

The hardest single problem: **seat contention** — "SpiderMan, L12 + L13, user1 AND user2 both trying to book at the same second."

---

## Rapid Answer Script (speak this in 2-3 minutes)

```
"I'd split this into three microservices with different databases because
 the consistency requirements are completely different.

 Search Service → Elasticsearch. Users search by title, location, date.
 Reads dominate (Read >> Write). Eventual consistency is fine —
 if a seat shows 'available' for 200ms after it was taken, no harm.

 Event Service → Cassandra. Stores event/movie metadata, seat maps.
 High read throughput, denormalized, no complex joins.

 Booking Service → MySQL/PostgreSQL. This is the CP path.
 We need ACID transactions. Two users cannot book the same seat.

 For seat contention — which interviewers always ask — I use a
 two-phase approach:
   Phase 1 (Reserve): User selects seats → SETNX in Redis with TTL=10min.
   Only one user wins the lock per seat. Other user sees 'seat unavailable'.

   Phase 2 (Confirm): User completes payment → we commit the booking
   to MySQL in a transaction, then release the Redis lock.

 If payment fails or user abandons, Redis TTL expires and the seat
 becomes available again automatically.

 For search freshness: CDC (Change Data Capture) streams changes from
 the Cassandra/MySQL writes into Elasticsearch asynchronously.

 The key insight is: CAP split. Search is AP. Booking is CP.
 Don't try to make them both use the same database."
```

---

# PAGE 2 — Glossary

| Term | Simple definition | Real example |
|---|---|---|
| Seat contention | Two users attempting to book the exact same seat simultaneously | L12, SpiderMan → user1 and user2 both click 'book' in the same second |
| Optimistic locking | Check version/state before committing, fail if changed | `UPDATE seats SET status='booked' WHERE id=L12 AND status='available'` |
| Pessimistic locking | Lock the row before reading it | `SELECT ... FOR UPDATE` — no other transaction can read/modify until released |
| SETNX | Redis SET if Not eXists — atomic, returns 1 if key was set, 0 if already exists | `SETNX seat:SpiderMan:L12 user1_session EX 600` — user1 wins the lock |
| TTL (Time-to-Live) | Automatic expiry of a Redis key | If user doesn't pay in 10 min, seat lock releases automatically |
| CDC (Change Data Capture) | Stream DB changes to downstream systems | MySQL binlog → Debezium → Kafka → Elasticsearch |
| Debezium | CDC tool that tails MySQL/Postgres binlog and publishes changes to Kafka | Row inserted in events table → Debezium publishes to Kafka → Elasticsearch consumes |
| Elasticsearch | Distributed search engine with full-text, geo, and faceted search | Search "SpiderMan Mumbai 2026-08-23" → ranked results in <100ms |
| Two-phase booking | Reserve (lock) then Confirm (pay + commit) | Phase 1: Redis lock. Phase 2: Payment → DB insert. |
| Idempotency | Same operation can be called multiple times safely | POST /booking/confirm with same booking_id → doesn't double-charge |
| Fan-out on write | Write to cache/search index immediately when DB changes | New event added → event appears in Elasticsearch within seconds |
| Oversell | Selling more seats than available | Without locking: 100 seats available, 200 users book = oversell |
| Soft hold | Temporary reservation of a seat before payment | Redis lock with TTL — not a committed booking yet |
| Hard booking | Committed, paid booking persisted to DB | Row in bookings table with status='confirmed' |
| Venue | Physical location — hall, stadium, cinema | PVR Juhu, Wankhede Stadium |

---

# PAGE 3 — Core Scenario (from image)

```
SCENARIO: "SpiderMan — two users try to book L12, L13 at the same time"

  user1 opens seat map → sees L12 (green = available), clicks Book
  user2 opens seat map → also sees L12 (green = available), clicks Book
                         ↓
  WHO GETS THE SEAT?

WITHOUT LOCKING (wrong):
  user1 reads:  status='available' ✓
  user2 reads:  status='available' ✓
  user1 writes: status='booked' ✓
  user2 writes: status='booked' ✓  ← DOUBLE BOOKING (oversell)

WITH REDIS SETNX (correct):
  user1: SETNX seat:SpiderMan:L12 user1 EX 600  → returns 1 (WIN)
  user2: SETNX seat:SpiderMan:L12 user2 EX 600  → returns 0 (LOSE)
  user2 sees: "Seat L12 is temporarily held. Choose another seat."

  user1 proceeds to payment...
    → payment success → INSERT into bookings → DEL seat:SpiderMan:L12
    → user2 still locked out (booking confirmed)

    OR

    → payment fails / user abandons → Redis TTL expires after 10 min
    → seat:SpiderMan:L12 is gone from Redis → seat becomes AVAILABLE again
    → user2 can now retry

ANNOTATION FROM IMAGE: "Read >> Write"
  For every 1 booking, there are ~1000 reads (search, browse, seat map).
  Design for read scale. Don't let booking consistency hurt search speed.
```

---

# PAGE 4 — Requirements (from image)

```
FUNCTIONAL REQUIREMENTS:
  FR1: User can search events by title, location, date
  FR2: User can view event details (seats, description, metadata)
  FR3: User can book a ticket (reserve seats → confirm + pay)

NON-FUNCTIONAL REQUIREMENTS:
  Scale:    100M DAU
  CAP Split:
    Search & Browse: Highly AVAILABLE (AP) — eventual consistency OK
    Booking:         Highly CONSISTENT (CP) — no double booking, ever

OUT OF SCOPE (for v1):
  ✗ Refunds and cancellations
  ✗ Dynamic pricing
  ✗ Waitlist
  ✗ Group bookings / corporate purchases

KEY NUMBERS:
  100M      DAU
  1B+       searches/day (10× bookings)
  ~10M      bookings/day
  ~115      bookings/second peak
  1000:1    read:write ratio for event browsing
  10 min    seat hold TTL (standard industry practice)
  2-3 sec   max seat map load time (SLA)
```

---

# PAGE 5 — Core Entities (from image)

```
ENTITY 1: User
  id          UUID PRIMARY KEY
  name        VARCHAR
  email       VARCHAR UNIQUE
  phone       VARCHAR
  created_at  TIMESTAMP

ENTITY 2: Event (Movie / Concert) — shown in image
  ┌──────────────────────────────────────┐
  │  Event (Cassandra)                   │
  │  - id                                │
  │  - venue                             │
  │  - artistId                          │
  │  - name                              │
  │  - description                       │
  │  - Seat[]    (seat map)              │
  └──────────────────────────────────────┘

  ┌──────────────────────────────────────┐
  │  Movie (Cassandra)                   │
  │  - id                                │
  │  - title                             │
  │  - Actors[]                          │
  │  - Seat[]    (seat map)              │
  └──────────────────────────────────────┘

ENTITY 3: Venue / Hall / Location
  id          UUID PRIMARY KEY
  name        VARCHAR             (e.g., PVR Juhu)
  city        VARCHAR
  address     TEXT
  capacity    INT
  seat_layout JSONB               (rows × columns grid)

ENTITY 4: Ticket / Booking (MySQL/Postgres)
  booking_id  UUID PRIMARY KEY
  user_id     UUID FK → Users
  event_id    UUID FK → Events
  seat_ids    UUID[]              (e.g., [L12, L13])
  status      ENUM(pending, confirmed, cancelled)
  total_price DECIMAL
  payment_id  VARCHAR             (from payment gateway)
  booked_at   TIMESTAMP
  expires_at  TIMESTAMP           (for pending bookings: +10 min)

ENTITY 5: Seat (within an event's seat map)
  seat_id     UUID PRIMARY KEY
  event_id    UUID FK → Events
  row         CHAR                (e.g., 'L')
  number      INT                 (e.g., 12)
  category    ENUM(gold, silver, platinum)
  price       DECIMAL
  status      ENUM(available, held, booked)
```

---

# PAGE 6 — API Design (from image)

## API 1: Search Events

```
GET /v1/search?q={searchTerm}&location={location}&date={date}
              → List<EventId>  :Pagination

Request params:
  q          = "SpiderMan"
  location   = "Mumbai"
  date       = "2026-08-23"
  page       = 1
  limit      = 20

Response 200:
{
  "events": [
    { "event_id": "ev123", "name": "SpiderMan", "venue": "PVR Juhu",
      "date": "2026-08-23T18:30:00Z", "seats_available": 143 },
    ...
  ],
  "next_page_token": "..."
}

Backed by: Elasticsearch (not the primary DB)
```

## API 2: Get Event Details + Seat Map

```
GET /v1/event/{eventId}
              → Event Details & Location & Seats[]

Response 200:
{
  "event_id": "ev123",
  "name": "SpiderMan: No Way Home",
  "venue": { "name": "PVR Juhu", "city": "Mumbai", "address": "..." },
  "date": "2026-08-23T18:30:00Z",
  "description": "Marvel's blockbuster...",
  "seats": [
    { "seat_id": "L12", "row": "L", "number": 12,
      "category": "gold", "price": 350, "status": "available" },
    { "seat_id": "L13", "row": "L", "number": 13,
      "category": "gold", "price": 350, "status": "held" },
    ...
  ]
}

Backed by: Cassandra (event metadata + live seat status from Redis overlay)
```

## API 3: Two-Phase Booking

```
Phase 1 — Reserve (soft hold):
POST /v1/booking/reserve
{
  "event_id": "ev123",
  "seats": ["L12", "L13"],
  "user_id": "u456"
}

Response 200:
{
  "booking_id": "bk789",
  "status": "pending",
  "expires_at": "2026-08-23T18:40:00Z",  ← 10 min TTL
  "total_price": 700
}

Phase 2 — Confirm (pay + commit):
POST /v1/booking/confirm
{
  "booking_id": "bk789",
  "payment_details": { "card_token": "...", "amount": 700 }
}

Response 200:
{
  "booking_id": "bk789",
  "status": "confirmed",
  "tickets": [...],
  "payment_id": "pay_stripe_xyz"
}
```

---

# PAGE 7 — High Level Architecture (from image)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  TICKET BOOKING — HIGH LEVEL DESIGN                     │
└─────────────────────────────────────────────────────────────────────────┘

  clients (browser / mobile)
          │
          ▼
  ┌───────────────────────────┐
  │     API Gateway           │
  │  - authentication         │
  │  - rate limiting          │
  │  - routing                │
  └──────────┬────────────────┘
             │
    ┌────────┼────────────────┐
    ▼        ▼                ▼
┌────────┐ ┌─────────────┐ ┌─────────┐
│ Search │ │Event Service│ │ Booking │
│  Svc   │ │             │ │  Svc    │
└───┬────┘ └──────┬──────┘ └────┬────┘
    │              │              │
    ▼              ▼              ▼
┌────────────────────────────────────┐
│             Database               │
│  (different DB per service — LLD)  │
└────────────────────────────────────┘

KEY INSIGHT (from image):
  Read >> Write
  For every 1 booking there are 1000+ reads (search, browse, seat map views).
  Optimize the read path independently of the write path.
```

---

# PAGE 8 — Low Level Architecture (from image)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   TICKET BOOKING — LOW LEVEL DESIGN                         │
└─────────────────────────────────────────────────────────────────────────────┘

  clients
     │
     ▼
  API Gateway
  (authentication, rate limiting, routing)
     │
  ┌──┼──────────────────────────────────────────────────────┐
  │  │                                                      │
  ▼  ▼                                                      ▼
┌─────────┐        ┌──────────────┐              ┌──────────────────┐
│  Search │        │ Event Service│              │   Booking Svc    │
│   Svc   │        │              │              │                  │
└────┬────┘        └──────┬───────┘              └───────┬──────────┘
     │                    │                              │
     ▼                    ▼                    ┌─────────┼──────────┐
┌──────────────┐   ┌──────────────┐            ▼         ▼          ▼
│ Elastic      │   │  Cassandra   │      ┌──────────┐ ┌──────┐ ┌────────────┐
│ Search       │   │              │      │ MySQL /  │ │Redis │ │  Kafka     │
│              │   │ Event:       │      │ Postgres │ │      │ │            │
│ (search by   │   │  - id        │      │          │ │ seat:│ │            │
│  title,      │   │  - venue     │      │ bookings │ │ ev123│ │            │
│  location,   │   │  - artistId  │      │ table    │ │ :L12 │ │            │
│  date)       │   │  - name      │      │ (ACID)   │ │ user1│ │            │
└──────────────┘   │  - description│     │          │ │EX600 │ └─────┬──────┘
        ▲          │  - Seat[]    │      └──────────┘ └──────┘       │
        │          │              │                                   ▼
        │ CDC      │ Movie:       │                         ┌──────────────────┐
        │ (Change  │  - id        │                         │  Payment Gateway │
        │  Data    │  - title     │                         │  (Stripe / Razorpay) │
        │  Capture)│  - Actors[]  │                         └──────────────────┘
        │          │  - Seat[]    │
        └──────────┴──────────────┘

CDC DETAIL:
  MySQL/Postgres binlog → Debezium → Kafka → Elasticsearch indexer
  Any change to events table → automatically reflected in search index
  Lag: 1-5 seconds (acceptable for search)

REDIS SEAT LOCK DETAIL:
  Key pattern:  seat:{event_id}:{seat_id}
  Example:      seat:ev123:L12  →  "user1_session_token"  EX 600
  SpiderMan L12, L13 booking scenario:
    user1: SETNX seat:ev123:L12 user1 EX 600  → 1 (held)
    user2: SETNX seat:ev123:L12 user2 EX 600  → 0 (already held)

BOOKING → KAFKA:
  On confirmed booking: publish to 'booking.confirmed' topic
  Consumers: Email/SMS notification svc, Analytics, Recommendation engine
```

---

# PAGE 9 — Seat Contention Deep Dive (Critical Section)

```
THE PROBLEM:
  SpiderMan premieres at 6:30pm. 50,000 users open the booking page at 12:00pm.
  Seat L12 is available. user1 AND user2 BOTH click L12 in the same millisecond.
  One must win. One must lose. No double booking.

SOLUTION: Two-phase booking with Redis SETNX

PHASE 1 — RESERVE (10 second flow):

  User selects L12, L13 → POST /v1/booking/reserve

  Booking Svc:
  1. For each seat, call SETNX atomically:
     SETNX seat:ev123:L12 user1_bk789 EX 600   → 1 = WIN, 0 = LOSE
     SETNX seat:ev123:L13 user1_bk789 EX 600   → 1 = WIN, 0 = LOSE

  2a. All SETNX return 1 (user1 wins both):
      → INSERT bookings (booking_id='bk789', status='pending', expires_at=+10min)
      → Return { booking_id: 'bk789', status: 'pending', expires_at: '...' }

  2b. Any SETNX returns 0 (another user holds a seat):
      → Release all locks acquired so far (DEL seat:ev123:L12)
      → Return 409 { error: 'Seat L13 is currently held by another user' }

PHASE 2 — CONFIRM (payment flow):

  User enters payment → POST /v1/booking/confirm { booking_id, payment_details }

  Booking Svc:
  1. Verify booking_id is still 'pending' and not expired
  2. Charge via Payment Gateway (Stripe/Razorpay)
  3. On payment SUCCESS:
     BEGIN TRANSACTION
       UPDATE bookings SET status='confirmed', payment_id='pay_xyz' WHERE booking_id='bk789'
       UPDATE seats SET status='booked' WHERE seat_id IN ('L12', 'L13')
     COMMIT
     DEL seat:ev123:L12
     DEL seat:ev123:L13
     Publish to Kafka 'booking.confirmed' (for notification svc)

  4. On payment FAILURE:
     UPDATE bookings SET status='cancelled'
     DEL seat:ev123:L12, DEL seat:ev123:L13
     Return 402 { error: 'Payment failed' }

  5. If booking expired (TTL elapsed, user took > 10 min to pay):
     Redis key already gone → seats available again
     Return 410 { error: 'Booking expired. Please start over.' }

RACE CONDITION PREVENTION:
  SETNX is atomic in Redis → guaranteed only one caller gets return value 1.
  No two users can both hold the same seat simultaneously.

SEAT MAP DISPLAY:
  Real-time status for the seat map view:
    Available: no Redis key AND DB status='available'
    Held:      Redis key exists (someone is in checkout, <10 min)
    Booked:    DB status='booked' (confirmed, permanent)
```

---

# PAGE 10 — Sequence Diagrams

## Sequence 1: Successful Booking (Happy Path)

```
User     API GW    Booking Svc    Redis        MySQL/PG    Payment GW    Kafka
 │          │           │            │             │            │           │
 │ POST     │           │            │             │            │           │
 │ /reserve │           │            │             │            │           │
 │─────────►│           │            │             │            │           │
 │          │───────────►            │             │            │           │
 │          │           │ SETNX      │             │            │           │
 │          │           │ L12,L13    │             │            │           │
 │          │           │───────────►│             │            │           │
 │          │           │ 1,1 (won)  │             │            │           │
 │          │           │◄───────────│             │            │           │
 │          │           │ INSERT booking (pending) │            │           │
 │          │           │─────────────────────────►│            │           │
 │ 200{bk789│           │            │             │            │           │
 │◄─────────│           │            │             │            │           │
 │          │           │            │             │            │           │
 │ POST     │           │            │             │            │           │
 │ /confirm │           │            │             │            │           │
 │─────────►│───────────►            │             │            │           │
 │          │           │─────────────────────────────────────► charge     │
 │          │           │◄──────────────────────────────────── success     │
 │          │           │            │             │            │           │
 │          │           │        BEGIN TXN         │            │           │
 │          │           │ UPDATE booking→confirmed │            │           │
 │          │           │ UPDATE seats→booked      │            │           │
 │          │           │        COMMIT            │            │           │
 │          │           │ DEL L12, L13 ───────────►│            │           │
 │          │           │ publish booking.confirmed────────────────────────►│
 │ 200 conf │           │            │             │            │           │
 │◄─────────│           │            │             │            │           │
```

## Sequence 2: Seat Contention (Two Users, Same Seat)

```
User1    API GW    Booking Svc    Redis
 │          │           │            │
 │ /reserve L12         │            │
 │─────────►│───────────►            │
 │          │           │ SETNX L12 user1 EX 600
 │          │           │───────────►│
 │          │           │ 1 (user1 WINS)
 │          │           │◄───────────│
 │ 200 pending          │            │
 │◄─────────│           │            │

User2    API GW    Booking Svc    Redis
 │          │           │            │
 │ /reserve L12         │            │
 │─────────►│───────────►            │
 │          │           │ SETNX L12 user2 EX 600
 │          │           │───────────►│
 │          │           │ 0 (seat HELD)
 │          │           │◄───────────│
 │ 409 Seat L12 is held │            │
 │◄─────────│           │            │
```

## Sequence 3: Search via Elasticsearch + CDC

```
Admin       Event Svc   MySQL/PG    Debezium    Kafka       ES Indexer  Elasticsearch
  │              │           │          │           │             │            │
  │ Add event    │           │          │           │             │            │
  │─────────────►│           │          │           │             │            │
  │              │ INSERT     │          │           │             │            │
  │              │───────────►│          │           │             │            │
  │              │            │ binlog   │           │             │            │
  │              │            │─────────►│           │             │            │
  │              │            │          │ publish   │             │            │
  │              │            │          │───────────►│             │            │
  │              │            │          │           │ consume     │            │
  │              │            │          │           │─────────────►            │
  │              │            │          │           │             │ index doc  │
  │              │            │          │           │             │───────────►│
  │              │            │          │           │   (1-5 sec lag total)    │

User
  │ GET /v1/search?q=SpiderMan&location=Mumbai
  │─────────────────────────────────────────────────────────────────────────────►│
  │◄─────────────────────────────────────────────── List<EventId> in <100ms ─────│
```

---

# PAGE 11 — Database Schema Details

## MySQL / PostgreSQL (Booking Service — ACID)

```sql
CREATE TABLE bookings (
    booking_id   UUID PRIMARY KEY,
    user_id      UUID NOT NULL,
    event_id     UUID NOT NULL,
    status       ENUM('pending','confirmed','cancelled','expired') NOT NULL,
    total_price  DECIMAL(10,2) NOT NULL,
    payment_id   VARCHAR(255),
    created_at   TIMESTAMP DEFAULT NOW(),
    expires_at   TIMESTAMP,           -- for pending bookings: now + 10 min
    confirmed_at TIMESTAMP
);

CREATE TABLE booking_seats (
    booking_id   UUID REFERENCES bookings(booking_id),
    seat_id      VARCHAR(20) NOT NULL, -- e.g., 'L12'
    event_id     UUID NOT NULL,
    price        DECIMAL(10,2),
    PRIMARY KEY (booking_id, seat_id)
);

CREATE TABLE seats (
    seat_id      VARCHAR(20),
    event_id     UUID,
    row          CHAR(3),
    number       INT,
    category     ENUM('gold','silver','platinum'),
    price        DECIMAL(10,2),
    status       ENUM('available','held','booked') DEFAULT 'available',
    version      INT DEFAULT 0,       -- for optimistic locking
    PRIMARY KEY (seat_id, event_id)
);

-- Critical indexes:
CREATE INDEX idx_bookings_user ON bookings(user_id, created_at);
CREATE INDEX idx_bookings_event ON bookings(event_id, status);
CREATE INDEX idx_seats_event_status ON seats(event_id, status);
```

## Cassandra (Event Service — High Read Throughput)

```
Event table (from image):
  id            UUID
  venue         TEXT
  artist_id     UUID
  name          TEXT
  description   TEXT
  seat_map      LIST<UUID>   (all seat IDs)
  date          TIMESTAMP
  city          TEXT
  PRIMARY KEY (id)

Movie table (from image):
  id            UUID
  title         TEXT
  actors        LIST<TEXT>
  seat_map      LIST<UUID>
  PRIMARY KEY (id)

Denormalized: Event_by_city (for city-based reads without secondary index):
  city          TEXT
  event_date    DATE
  event_id      UUID
  name          TEXT
  venue         TEXT
  PRIMARY KEY ((city, event_date), event_id)
```

## Redis Key Space

```
Seat lock:
  seat:{event_id}:{seat_id}     STRING  {user_session_id}   EX 600
  seat:ev123:L12  →  "user1_bk789"  TTL: 600s (10 min)

Booking expiry tracking:
  booking:pending:{booking_id}  STRING  {event_id}          EX 600
  (used to auto-expire pending bookings if user abandons)

Seat map cache (read optimization):
  seatmap:{event_id}            HASH    { seat_id: status }  EX 60
  (60s TTL — refreshed from DB, serves seat map API quickly)

Popular events cache:
  event:{event_id}              STRING  (JSON)              EX 300
  (5 min TTL for event metadata — serves 90%+ of browse traffic)
```

## Elasticsearch Index (Search Service)

```json
{
  "mappings": {
    "properties": {
      "event_id":         { "type": "keyword" },
      "name":             { "type": "text", "analyzer": "standard" },
      "description":      { "type": "text" },
      "venue_name":       { "type": "text" },
      "city":             { "type": "keyword" },
      "event_date":       { "type": "date" },
      "seats_available":  { "type": "integer" },
      "categories":       { "type": "keyword" },
      "min_price":        { "type": "float" },
      "location":         { "type": "geo_point" }
    }
  }
}
```

---

# PAGE 12 — ER Relationship Diagram

```
┌──────────────────────┐        ┌──────────────────────────┐
│        users         │        │         events            │
├──────────────────────┤        ├──────────────────────────┤
│ PK  user_id   UUID   │ 1   N  │ PK  event_id  UUID       │
│     name      VARCHAR│────────┤     name      TEXT       │
│     email     VARCHAR│        │     venue     TEXT       │
│     phone     VARCHAR│        │     artist_id UUID       │
│     created_at       │        │     date      TIMESTAMP  │
└──────────────────────┘        │     city      TEXT       │
                                │     Seat[]    (Cassandra)│
                                └───────────┬──────────────┘
                                            │ 1
                                            │
                                            │ N
┌──────────────────────┐        ┌───────────▼──────────────┐
│    booking_seats     │   N    │        bookings           │
├──────────────────────┤        ├──────────────────────────┤
│ PK  booking_id UUID  │────────┤ PK  booking_id UUID      │
│ PK  seat_id    VARCHAR│   1   │     user_id    UUID      │
│     event_id  UUID   │        │     event_id   UUID      │
│     price     DECIMAL│        │     status     ENUM      │
└──────────────────────┘        │     total_price DECIMAL  │
                                │     payment_id  VARCHAR  │
                                │     expires_at  TIMESTAMP│
                                └──────────────────────────┘

                                ┌──────────────────────────┐
                                │         seats            │
                                ├──────────────────────────┤
                                │ PK  seat_id   VARCHAR    │
                                │ PK  event_id  UUID       │
                                │     row       CHAR       │
                                │     number    INT        │
                                │     category  ENUM       │
                                │     price     DECIMAL    │
                                │     status    ENUM       │
                                │     version   INT        │
                                └──────────────────────────┘

REDIS (not relational, shown for completeness):
  seat:{event_id}:{seat_id}   →   STRING (user session)   EX 600
  seatmap:{event_id}          →   HASH   { seat_id: status }
  event:{event_id}            →   STRING (JSON metadata)  EX 300
```

---

# PAGE 13 — CAP Theorem Analysis

```
CAP THEOREM SPLIT (from image):
  "Highly available with respect to searching and viewing an event,
   and highly consistent with respect to booking a particular ticket."

┌───────────────────────────────────────────────────────────────────┐
│  Feature          │  CAP Choice  │  Why                          │
├───────────────────┼──────────────┼───────────────────────────────┤
│  Search events    │  AP          │  Stale results OK.            │
│                   │              │  If seat shows 'available'    │
│                   │              │  for 2 seconds after it's     │
│                   │              │  taken → no harm.             │
├───────────────────┼──────────────┼───────────────────────────────┤
│  View event       │  AP          │  Event metadata rarely changes│
│  metadata         │              │  Cache heavily. Stale OK.     │
├───────────────────┼──────────────┼───────────────────────────────┤
│  View seat map    │  Near-real   │  Redis overlay on DB.         │
│                   │  time        │  Held seats shown in ~1s.     │
│                   │              │  60s TTL cache acceptable.    │
├───────────────────┼──────────────┼───────────────────────────────┤
│  Reserve a seat   │  CP          │  SETNX atomic.                │
│                   │              │  Exactly one user wins.       │
│                   │              │  No double-holds ever.        │
├───────────────────┼──────────────┼───────────────────────────────┤
│  Confirm booking  │  CP          │  ACID transaction.            │
│  (pay + commit)   │              │  Either committed or not.     │
│                   │              │  No partial states.           │
└───────────────────┴──────────────┴───────────────────────────────┘

THE KEY RULE:
  Money + seats = CP (consistent). Everything else = AP (available).
```

---

# PAGE 14 — Scalability

```
BOTTLENECK 1: Midnight sale (flash sale — 50K users, same second)
  Problem: All users hit "Book" simultaneously for premier seats.
           50K SETNX on same seat:ev123:L12 → Redis queues all.
  Solution:
    → Queue-based reservation: user gets a position number in a Redis sorted set
      ZADD sale:ev123 timestamp user_id  → returns position
    → Show user their queue position: "You are #1247 in line"
    → Process first N users (N = total seats available)
    → Others see "Sold out" once seats exhausted
    → Virtual waiting room (like Ticketmaster) to control flood

BOTTLENECK 2: Seat map reads (1000× more common than writes)
  Problem: Every user refreshes seat map every few seconds.
  Solution:
    → Redis HASH cache: seatmap:{event_id} with 60s TTL
    → Serve seat map from Redis (< 1ms) not DB (10ms+)
    → On booking confirm: HSET seatmap:{event_id} seat_id 'booked'
    → On lock acquire: HSET seatmap:{event_id} seat_id 'held'
    → DB is source of truth; Redis is read cache

BOTTLENECK 3: Search performance
  Problem: 100M DAU doing text search → Cassandra not built for this.
  Solution:
    → Elasticsearch for search (inverted index, geo queries, full-text)
    → CDC from MySQL/Cassandra → Debezium → Kafka → ES indexer
    → 1-5s lag is acceptable for event search results
    → Geo search: user in Mumbai → show Mumbai events first (geo_point field)

BOTTLENECK 4: Popular events (Taylor Swift, IPL Final)
  Problem: 10M users hit the same event simultaneously.
  Solution:
    → Event metadata: cache in Redis (EX 300), serves 95% traffic
    → CDN for event images/poster (never hits origin server)
    → Rate limit per user: 10 reserve attempts/min per user
    → Separate Kafka topic for mega-events ('flash_sale.ev123') with dedicated consumers

BOTTLENECK 5: Payment gateway timeouts
  Problem: Stripe/Razorpay slow at peak → booking limbo.
  Solution:
    → Async payment via Kafka: Booking publishes to 'payment.request'
    → Payment consumer processes, publishes result to 'payment.result'
    → Booking Svc listens to 'payment.result', updates DB
    → User polls status: GET /v1/booking/{id}/status
    → Timeout: if no result in 2 min → retry or cancel

BOTTLENECK 6: DB write overload during booking storm
  Solution:
    → Separate read replicas for all SELECT queries
    → Write only confirmed bookings to primary
    → Batch pending booking cleanup (expired holds): cron job every 5 min
    → Partition bookings table by event_date (current month hot partition)
```

---

# PAGE 15 — Interview Scripts

## Requirement Clarification Script

```
"Before designing, let me ask a few things:

  1. What types of events? Movies only or concerts, sports too?
     (affects entity model — Movie vs Event vs Concert)
  2. What's the scale? 100M DAU is fine — how many bookings/day?
  3. Is this single region or multi-region?
     (multi-region = more complex consistency for seat locking)
  4. Any flash sale requirement?
     (Taylor Swift tickets — 5M users, 50K seats, same second)
  5. What consistency guarantee for booking?
     (I assume CP — no double booking under any circumstance)
  6. Should the seat map be real-time or near-real-time?
     (real-time = harder; near-real-time 60s lag = achievable with cache)"
```

---

## Trade-Off Script

```
"The fundamental trade-off is CAP:

  AP for search: We use Elasticsearch with CDC (1-5s lag).
  A user might see a seat as 'available' for 2 seconds after it was taken.
  This is acceptable — the booking step enforces the real constraint.

  CP for booking: Redis SETNX is atomic. MySQL transactions are ACID.
  Two users can never confirm the same seat. This is non-negotiable.

  Two-phase vs One-phase booking:
  Two-phase (reserve → confirm) is more complex but necessary.
  If we charged during reserve, users would be charged before payment confirmed.
  If we committed the seat before payment, we'd hold seats without revenue.
  Reserve = soft hold (free, temporary). Confirm = hard commit (paid, permanent).

  Redis TTL (10 min) trade-off:
  Too short (2 min): Users may not finish payment in time → frustration.
  Too long (30 min): Seats locked for 30 min if user abandons → lost sales.
  10 min is the industry standard (Ticketmaster, BookMyShow both use ~10 min)."
```

---

# PAGE 16 — Senior Trap Questions

## Q1: "How do you prevent double booking without Redis? What if Redis crashes?"

```
WEAK: "We rely on Redis, so it can't crash."

STRONG:
  "Redis is the fast-path prevention, but the DB is the final enforcer.

  Even without Redis, we prevent double booking via a DB-level unique constraint:
    UNIQUE(event_id, seat_id, status='booked')

  Better: optimistic locking on the seat row:
    SELECT * FROM seats WHERE seat_id='L12' AND event_id='ev123'
    → version = 5

    UPDATE seats SET status='booked', version=6
    WHERE seat_id='L12' AND event_id='ev123' AND version=5 AND status='available'
    → if 0 rows updated: another transaction took the seat → retry or fail

  If Redis crashes: fall back to DB-level optimistic locking.
  Performance degrades (DB calls instead of Redis), but correctness is preserved.

  Redis is an optimization (speed) not a correctness requirement.
  The DB is the source of truth."
```

---

## Q2: "What if the user pays but our server crashes before we write the confirmed booking to DB?"

```
STRONG:
  "This is the classic payment atomicity problem.

  Solution: idempotency key on payment + booking.

  Before charging, we write a payment_intent to DB with status='initiated'
  and a unique idempotency_key = booking_id.

  Stripe/Razorpay accept an idempotency_key parameter.
  If we retry the same payment request, they return the same result (no double charge).

  On server restart:
  1. Query DB for bookings in status='pending' with payment_id not null
  2. Call Stripe: GET /v1/payment_intents/{payment_intent_id}
  3. If status='succeeded' → mark booking confirmed in DB
     If status='failed' → release seat lock, mark booking cancelled

  This handles the crash-after-charge, crash-before-DB-update scenario.
  The idempotency key ensures Stripe never double-charges."
```

---

## Q3: "How does CDC work? What if Debezium falls behind by 10 minutes during peak?"

```
STRONG:
  "CDC (Change Data Capture) tails the MySQL/Postgres binary log.
  Debezium reads each committed transaction and publishes to Kafka.
  An Elasticsearch indexer consumer updates the search index.

  Lag of 10 minutes during peak is acceptable for search results —
  a new event may not appear in search for 10 min. That's fine.

  What's NOT fine is the seat map search showing 'available' when sold out.
  But the seat map is served from the Booking Svc (Redis + DB), not Elasticsearch.
  Elasticsearch is only for search results (list of events) — not seat-level status.

  If CDC falls behind badly (> 1 hour): alert on Kafka consumer lag.
  Recovery: Debezium reads from the last committed offset — no data loss.
  It just catches up.

  Alternative if CDC lag is critical: write-through to Elasticsearch on event creation
  (synchronous write to both DB and ES). This reduces lag to near-zero but
  creates a distributed write problem (DB write succeeds, ES write fails).
  Outbox pattern can solve this too."
```

---

## Q4: "Two users select seats concurrently. Your Redis has a network partition. What happens?"

```
STRONG:
  "During a network partition, Redis may be unavailable.
  SETNX calls fail. We can't acquire the seat lock.

  Response options:

  Option 1 (fail open): Fall back to DB-level optimistic locking.
  Slower (30ms vs 1ms) but correct. This is the right choice.

  Option 2 (fail closed): Return 503 'Service temporarily unavailable.'
  Safe but hurts user experience.

  For the AP/CP split here:
  Since booking is CP (consistency > availability), Option 2 is actually
  acceptable for the booking path. Users can retry in 30 seconds.

  In practice: Redis cluster with Sentinel or Redis Cluster mode
  reduces the risk of full Redis unavailability significantly.
  A partition is unlikely if Redis is in the same datacenter as the app."
```

---

## Q5: "What's wrong with using Cassandra for the booking service?"

```
STRONG:
  "Cassandra is AP — eventual consistency.
  It does not support multi-row ACID transactions.

  For booking a seat:
  We need to atomically:
    1. Check seat is available
    2. Mark seat as booked
    3. Create a booking record

  In Cassandra, these are three separate operations with no transaction boundary.
  Between step 1 and step 2, another user can book the same seat → double booking.

  Cassandra's lightweight transactions (LWT with PAXOS) provide compare-and-swap:
  UPDATE seats SET status='booked' IF status='available'
  This works for single-row, but has 4-round-trip latency and is slow.

  MySQL/Postgres with ACID transactions is the right choice for booking.
  Use Cassandra for what it's good at: event metadata, seat map definitions
  (high read throughput, no transactions needed)."
```

---

# PAGE 17 — What NOT to Say

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  TRAP PHRASE                        │ WHY IT'S WRONG                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Use Cassandra for bookings"        │ Cassandra is AP. Bookings need ACID. ║
║                                     │ Use MySQL/Postgres for booking table. ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Just use a DB lock (SELECT FOR     │ At scale, DB-level row locking can   ║
║  UPDATE) for all seat reservations" │ create lock contention with 50K      ║
║                                     │ concurrent users. Redis SETNX is     ║
║                                     │ faster and doesn't block DB threads. ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "One-phase booking: charge and      │ If payment fails after seat is       ║
║  commit in one step"                │ committed → seat stuck as 'booked'   ║
║                                     │ with no revenue. Always 2-phase:     ║
║                                     │ reserve first, confirm after payment.║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Use MySQL for search"              │ MySQL LIKE '%spiderman%' is a full   ║
║                                     │ table scan. Elasticsearch is built   ║
║                                     │ for full-text, geo, and faceted      ║
║                                     │ search. Never use SQL LIKE for search║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Seat status is always real-time"   │ Seat map can be ~60s stale (from     ║
║                                     │ cache). Only the reserve API enforces║
║                                     │ real-time correctness via Redis.     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Redis is the source of truth for   │ Redis is volatile. If it crashes,    ║
║  booking state"                     │ data is lost. DB (MySQL) is source   ║
║                                     │ of truth. Redis is the fast cache +  ║
║                                     │ distributed lock only.               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "CAP Theorem doesn't apply here"   │ It applies strongly. State the split: ║
║                                     │ AP for search, CP for booking. This  ║
║                                     │ distinction is a key signal for      ║
║                                     │ senior interviewers.                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

# PAGE 18 — Key Numbers to Memorize

```
┌──────────────────────────────────────────────────────────────────────┐
│  Scale:                                                              │
│  100M          DAU                                                   │
│  1B+           searches/day (10× bookings — "Read >> Write")         │
│  10M           bookings/day (~115/sec average, ~1000/sec peak)       │
│                                                                      │
│  Seat Hold:                                                          │
│  10 min        Redis TTL for soft-hold (industry standard)           │
│  EX 600        Redis seconds for 10 min                              │
│                                                                      │
│  Latency SLAs:                                                       │
│  <100ms        search results (Elasticsearch)                        │
│  <200ms        event detail + seat map (Redis cache)                 │
│  <3 sec        booking reserve (Redis SETNX + DB insert)             │
│  <30 sec       payment confirm (sync or async via Kafka)             │
│  1–5 sec       CDC lag (DB changes → Elasticsearch update)           │
│                                                                      │
│  Cache TTLs:                                                         │
│  60 sec        seat map cache (Redis HASH)                           │
│  300 sec       event metadata cache                                  │
│  600 sec       seat lock TTL (booking pending)                       │
│                                                                      │
│  DB choice by service:                                               │
│  Search Svc   → Elasticsearch (full-text, geo)                       │
│  Event Svc    → Cassandra (high read, denormalized metadata)         │
│  Booking Svc  → MySQL / PostgreSQL (ACID transactions)               │
│  Locks        → Redis (SETNX, atomic, TTL)                           │
│  Events bus   → Kafka (booking.confirmed, payment.request)           │
│                                                                      │
│  Payment:                                                            │
│  Idempotency key = booking_id (passed to Stripe/Razorpay)            │
│  Prevents double charge on server crash + retry                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

# PAGE 19 — Whiteboard Draw Order

```
Step 1 — Write the CAP split (30 sec)
  "Search = AP (Elasticsearch, CDC, eventual consistency)"
  "Booking = CP (MySQL, Redis SETNX, ACID)"

Step 2 — Draw the HLD (45 sec)
  clients → API Gateway → Search / Event Svc / Booking Svc → DB

Step 3 — Draw LLD components (60 sec)
  Search → Elasticsearch ← CDC ← MySQL
  Event → Cassandra
  Booking → MySQL/Postgres + Redis + Kafka → Payment Gateway

Step 4 — Draw the seat contention scenario (45 sec)
  "SpiderMan: L12, L13. user1 and user2 both click Book."
  SETNX seat:ev123:L12 user1 EX 600 → 1 (user1 wins)
  SETNX seat:ev123:L12 user2 EX 600 → 0 (user2 loses)

Step 5 — Draw the 2-phase booking (30 sec)
  Phase 1: /reserve → Redis lock + DB pending row
  Phase 2: /confirm → payment → DB confirmed + DEL Redis lock

Step 6 — Call out the trade-offs (20 sec)
  "10 min TTL — industry standard. Not too short, not too long."
  "Redis crashes → fall back to DB optimistic locking. DB is source of truth."
```

---

# PAGE 20 — Company Adaptation

## High-Traffic Events (Ticketmaster-scale: Taylor Swift, IPL Final)
```
  5M concurrent users, 50K seats, 1-second window
  → Virtual waiting room: ZADD sale_queue:{event_id} timestamp user_id
  → Process first 50K users (1 per seat)
  → Show real-time position counter in UI
  → Rate limit: 1 reserve attempt per user per event per minute
  → CDN for event page (static assets cached globally)
  → Dedicate a Kafka partition per mega-event
```

## Multi-City / Multi-Region
```
  Booking: Single-region primary (consistency requirement)
  Search: Multi-region Elasticsearch (local replicas per region)
  Event data: Replicated globally via Cassandra multi-DC
  Seat locks: Single Redis cluster (must be centralized for correctness)
```

## B2B SaaS (Corporate Bookings, Group Tickets)
```
  Extend API: POST /v1/booking/group { seats: [50], user_ids: [...] }
  All 50 seats must be reserved atomically → Lua script in Redis
  If any SETNX fails → rollback all acquired locks (DEL each)
  DB: single transaction for all 50 booking_seats rows
```

---

# PAGE 21 — Final Quick-Revision Cheat Sheet

```
╔══════════════════════════════════════════════════════════════════════════════╗
║       TICKET BOOKING SYSTEM — ONE-PAGE CHEAT SHEET                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  3 SERVICES × 3 DATABASES:                                                  ║
║  Search Svc    → Elasticsearch (full-text, geo, AP)                         ║
║  Event Svc     → Cassandra     (high-read metadata, AP)                     ║
║  Booking Svc   → MySQL/Postgres (ACID transactions, CP)                     ║
║                                                                              ║
║  SEAT LOCKING (core hard problem):                                           ║
║  SETNX seat:{event_id}:{seat_id} {user_session} EX 600                      ║
║  Returns 1 = you win the lock. Returns 0 = seat already held.               ║
║  TTL = 10 min. Auto-expires if user abandons.                                ║
║                                                                              ║
║  TWO-PHASE BOOKING:                                                          ║
║  Phase 1: /reserve → Redis lock + DB 'pending' row                          ║
║  Phase 2: /confirm → payment → DB 'confirmed' + DEL Redis key               ║
║                                                                              ║
║  CAP SPLIT (say this explicitly):                                            ║
║  Search + Browse = AP (Elasticsearch, CDC, ~5s lag OK)                      ║
║  Reserve + Confirm = CP (SETNX atomic, ACID transaction)                    ║
║                                                                              ║
║  CDC CHAIN:                                                                  ║
║  MySQL binlog → Debezium → Kafka → ES Indexer → Elasticsearch               ║
║  Lag: 1-5 sec. Acceptable for search. Seat map served from Redis, not ES.   ║
║                                                                              ║
║  PAYMENT IDEMPOTENCY:                                                        ║
║  Pass booking_id as idempotency_key to Stripe/Razorpay.                     ║
║  On retry after crash → same result, no double charge.                      ║
║                                                                              ║
║  WHAT NOT TO SAY:                                                            ║
║  ✗ Use Cassandra for bookings (AP, no ACID)                                  ║
║  ✗ MySQL LIKE for search (use Elasticsearch)                                 ║
║  ✗ Redis is source of truth (DB is, Redis is cache + lock)                  ║
║  ✗ One-phase booking (reserve + pay together) — use 2-phase                 ║
║                                                                              ║
║  KEY NUMBERS:                                                                ║
║  100M DAU | Read:Write = 1000:1 | 10 min TTL | <100ms search                ║
║  CDC lag 1-5s | seat lock EX 600 | MySQL ACID for bookings                  ║
║                                                                              ║
║  INTERVIEW LINE:                                                             ║
║  "CAP split: AP for search (Elasticsearch + CDC), CP for booking            ║
║   (Redis SETNX + MySQL ACID). Two-phase booking: reserve (Redis            ║
║   lock, 10 min TTL) then confirm (pay + DB commit). Seat contention         ║
║   solved atomically by SETNX — exactly one user wins the lock."             ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

> **Note on blog.md**: The `blog.md` in this folder contains the Notification System design (Video 15),
> not the Ticket Booking System. This guide is built from the design image.
> If you have the Ticket Booking blog.md, add it to this folder and re-run the gap analysis.

*Print: monospace font, 10pt, portrait, standard margins. All ASCII diagrams are print-ready.*
