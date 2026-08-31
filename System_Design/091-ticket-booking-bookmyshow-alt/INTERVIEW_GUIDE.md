# BookMyShow — Interview Script
## Design a Ticket Booking System (BookMyShow / Ticketmaster)
### Speak This Word-for-Word to Your Interviewer

> How to use this: Read PAGE 1 first to get the big picture in your head. Study the ASCII diagrams — do NOT draw them during the interview, they are for YOUR understanding. When the interviewer asks you to design the system, follow the FULL INTERVIEW SCRIPT on PAGE 4+. The Senior Trap Questions at the end are the real differentiators — practice saying them out loud.

# ═══════════════ PAGE 1 — START HERE ═══════════════

## BIG PICTURE (Understand This Before Anything Else)

> **► STUDY this diagram, don't draw it ◄**
> BookMyShow is fundamentally a seat inventory management problem with extreme concurrency spikes. What makes it uniquely hard: a seat can only be sold once, but thousands of users try to claim the same seat at the same millisecond. Unlike an e-commerce cart (where you can just buy more inventory), seats are finite, physical, and positional. The core challenge is: lock the seat, take payment, confirm booking — all without race conditions, without killing DB performance, and without a terrible user experience when the seat gets stolen mid-checkout.

```
                         ┌─────────────────────────────────────────────────────┐
                         │              BOOKMYSHOW — DATA FLOW                  │
                         └─────────────────────────────────────────────────────┘

  ┌──────────┐   Search    ┌──────────────┐   Event/      ┌──────────────────┐
  │  Browser │ ──────────► │   API        │   Show data   │   MySQL          │
  │  Mobile  │             │   Gateway    │ ─────────────►│  (events/shows/  │
  │  App     │             │  (Rate Limit │               │   bookings/seats)│
  └──────────┘             │   Auth/TLS)  │               └──────────────────┘
       │                   └──────┬───────┘                        │
       │                          │                                 │
       │  SSE (seat map           │  Route to                      │ READ
       │  live updates)           ▼  service                       ▼
       │                   ┌──────────────┐   Seat Lock   ┌──────────────────┐
       │ ◄──────────────── │   Booking    │ ─────────────►│   Redis          │
       │                   │   Service    │               │  seats:locked:*  │
       │                   │  (Core Flow) │ ◄─────────────│  show_seats:*    │
       │                   └──────┬───────┘  Lock result  │  (bitmap/TTL)    │
       │                          │                       └──────────────────┘
       │                          │ Publish
       │                          ▼
       │                   ┌──────────────┐  Payment      ┌──────────────────┐
       │                   │    Kafka     │ ─────────────►│  Payment Service │
       │                   │  (Async bus) │               │  (Stripe/Razorpay│
       │                   └──────┬───────┘               │   integration)   │
       │                          │                       └──────────────────┘
       │                          │ Consume
       │                          ▼
       │                   ┌──────────────┐  Store PDF    ┌──────────────────┐
       └─── Ticket URL ─── │  Ticket      │ ─────────────►│   S3 + CDN       │
                           │  Generator   │               │  (PDF/QR codes)  │
                           │  Worker      │               │   seat maps      │
                           └──────────────┘               └──────────────────┘
                                                                    │
                                                           ┌────────▼─────────┐
                                                           │ Elasticsearch    │
                                                           │ (event search:   │
                                                           │  city/date/genre)│
                                                           └──────────────────┘
```

---

## RAPID ANSWER — If You Only Have 5 Minutes

Say this verbatim if time is short:

"BookMyShow is a seat inventory system with a thundering-herd concurrency problem.

First, the seat locking flow: when a user selects a seat, I use Redis SET with NX and EX 600 — that atomically claims the seat for 10 minutes. If the key already exists, the seat is taken. This is a Redis distributed lock, not a DB row lock, because DB locks held during payment create 2-3 minute connection exhaustion and deadlock risk.

Second, the booking confirmation: on payment success, I run a MySQL transaction — UPDATE seat status to BOOKED where status is AVAILABLE, INSERT booking and booking_seats rows, then DEL the Redis lock. On failure or timeout, Redis TTL auto-expires and the seat is available again.

Third, for scale: Coldplay India — 1M concurrent users at noon for 2 lakh seats. I use a virtual waiting room in Redis. Users get a queue position number. I drip them into the booking flow at 10K/sec. Without this, Redis and MySQL get overwhelmed simultaneously.

Fourth, seat map availability: Redis bitmap per show. 50,000 seats = 6KB total. O(1) GETBIT and SETBIT. Entire venue state in memory.

Fifth, tickets: generated asynchronously via Kafka event to a worker that creates PDF + QR code, uploads to S3, and stores the URL in the tickets table."

---

# ═══════════════ PAGE 2 — GLOSSARY ═══════════════

```
┌─────────────────────────────┬────────────────────────────────────────────────────────────┐
│ TERM                        │ WHAT IT MEANS                                              │
├─────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Seat Lock                   │ Temporary claim on a seat (Redis, 10min TTL). Not a        │
│                             │ booking. Prevents another user from selecting same seat.   │
├─────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Thundering Herd             │ 1M users simultaneously hitting the same endpoint at        │
│                             │ noon (event goes on sale). Collapses DB + Redis together.  │
├─────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Redis NX (SET NX)           │ "Set if Not eXists" — atomic conditional set. Only one     │
│                             │ thread wins; all others get 0 back. Core of seat locking.  │
├─────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Redis EX (TTL)              │ Expiry in seconds. SET key val EX 600 = auto-delete after  │
│                             │ 10 minutes. Prevents orphaned locks if user abandons.      │
├─────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Redis Bitmap                │ Bit array. SETBIT show_seats:123 seatPos 1. Entire 50K     │
│                             │ seat venue = 6KB. O(1) read/write per seat.                │
├─────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Lua Script (Redis)          │ Atomically executes multiple Redis commands. Used to GET   │
│                             │ + SET NX in one atomic operation (no race between check    │
│                             │ and set).                                                  │
├─────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Virtual Waiting Room        │ Queue system (Redis sorted set by join time). Users get    │
│                             │ a position number and are admitted into booking flow in     │
│                             │ controlled batches (10K/sec).                              │
├─────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Payment Intent (Stripe)     │ Idempotent payment object. Create once, retry safely.      │
│                             │ If user retries payment, Stripe deduplicates by intent ID. │
├─────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Idempotency Key             │ Unique key per operation. On retry, same key = same result │
│                             │ (no double charge). Critical for payment retry safety.     │
├─────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Show                        │ Specific instance of an event: "Coldplay @ Wankhede, 25   │
│                             │ Jan 2025, 8PM." An event can have multiple shows.          │
├─────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Booking States              │ PENDING (lock held, payment in progress) → CONFIRMED       │
│                             │ (payment done, seat booked) → CANCELLED                   │
├─────────────────────────────┼────────────────────────────────────────────────────────────┤
│ QR Code / E-Ticket          │ Generated async post-booking. Contains booking_id encoded. │
│                             │ Venue scanner validates by calling /tickets/validate API.  │
├─────────────────────────────┼────────────────────────────────────────────────────────────┤
│ CDN for Seat Maps           │ Static seat map images (SVG/PNG) of venue layout served    │
│                             │ from CDN edge. Never DB-fetched on each request.           │
├─────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Elasticsearch               │ Inverted-index search engine. Handles: "concerts in        │
│                             │ Bangalore this weekend" — full text + geo + date filter.   │
├─────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Optimistic Locking          │ DB-level concurrency control with version column. Why NOT  │
│                             │ used here: seat lock semantics are better served by Redis  │
│                             │ distributed lock (lock-then-pay vs check-at-commit).       │
├─────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Seat Category               │ VIP / Gold / Silver / General. Different price + location  │
│                             │ in venue. Stored in seats.category ENUM.                   │
└─────────────────────────────┴────────────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 3 — WHY EACH COMPONENT ═══════════════

```
┌──────────────────┬──────────────────────────────────┬──────────────────────────────────┐
│ TECHNOLOGY       │ WHY WE USE IT                    │ WHY NOT ALTERNATIVE               │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Redis            │ Sub-millisecond lock check.       │ Not ZooKeeper: heavier, not       │
│ (Seat Locking)   │ SET NX EX is atomic. TTL means   │ optimized for high-frequency      │
│                  │ no cleanup job needed. Handles   │ lock/unlock. Not DB row lock:      │
│                  │ 100K lock ops/sec.               │ held during payment = deadlock.    │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Redis            │ 50K bits = 6KB per show. O(1)    │ Not DB column: querying 50K rows  │
│ (Seat Bitmap)    │ GETBIT/SETBIT. Entire venue      │ per seat map request is too slow. │
│                  │ state fits in L1 cache.          │ Not in-memory map: not shared     │
│                  │                                  │ across multiple app instances.    │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ MySQL            │ ACID transactions for bookings.  │ Not Cassandra: eventual consist-  │
│ (Bookings/       │ JOINs across events/shows/seats. │ ency is dangerous for financial   │
│  Seats)          │ Strong consistency needed for    │ data — double booking risk.       │
│                  │ "seat sold exactly once."        │ Not MongoDB: less mature ACID.    │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Elasticsearch    │ Full-text search with filters.   │ Not MySQL LIKE query: no inverted │
│ (Event Search)   │ "concerts in Bangalore this      │ index, slow on 10M+ events.       │
│                  │ weekend" needs geo+text+date.    │ Not Solr: ES has better REST API  │
│                  │                                  │ and managed cloud options.        │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Kafka            │ Decouple booking confirmation    │ Not RabbitMQ: Kafka retains msgs. │
│ (Async           │ from ticket generation. Worker   │ If ticket generator crashes,      │
│  Ticket Gen)     │ retries are safe. High           │ replays from offset. RabbitMQ     │
│                  │ throughput, durable events.      │ msg is gone on consumer crash.    │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ S3 + CDN         │ Ticket PDFs and QR codes are     │ Not DB BLOB: 5MB PDFs in DB       │
│ (Tickets/Maps)   │ static after generation. CDN     │ = table bloat, slow queries.      │
│                  │ serves seat map images at edge.  │ Not local disk: not scalable       │
│                  │ 99.999% durability, cheap.       │ across multiple app servers.       │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ API Gateway      │ Rate limiting per user/IP.       │ Not nginx alone: no rate limiting │
│                  │ JWT auth validation. TLS         │ logic without Lua scripting.      │
│                  │ termination. Route to services.  │ Not service mesh only: GW handles │
│                  │                                  │ north-south traffic specifically.  │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Virtual Queue    │ Shapes thundering herd. Users    │ Not just rate limiting: that      │
│ (Redis Sorted    │ enter queue → get position →     │ returns errors, UX is terrible.   │
│  Set)            │ admitted in batches. Transparent │ Queue gives fair ordering and     │
│                  │ wait experience vs hard errors.  │ estimated wait time feedback.     │
└──────────────────┴──────────────────────────────────┴──────────────────────────────────┘
```

---

# ═══════════════ PAGE 4 — FULL INTERVIEW SCRIPT ═══════════════

## OPENING

Say this to start:

"Before I dive into the architecture, let me clarify requirements and scope. BookMyShow has a few distinct user journeys: searching for events, browsing shows, selecting seats, completing payment, and receiving a ticket. The hardest technical problem is the seat selection race condition — multiple users selecting the same seat simultaneously. I want to make sure I solve that correctly. Let me start with requirements."

---

## STEP 1 — Requirements Gathering

```
┌─────────────────────────────────────────────────────────────────────┐
│ CLARIFYING QUESTIONS TO ASK                                         │
├─────────────────────────────────────────────────────────────────────┤
│ 1. Are we building only the booking flow, or also event management? │
│ 2. Do we need to handle general admission (no seat selection)?      │
│ 3. What's the expected peak concurrency? (Popular event launch?)    │
│ 4. Do we need real-time seat map updates for other users?           │
│ 5. Mobile app + web, or just web?                                   │
│ 6. International or India-focused? (Payment gateway choice)         │
└─────────────────────────────────────────────────────────────────────┘
```

**Functional Requirements:**
- Users can search for events by city, date, genre, venue
- Users can view available shows for an event
- Users can see a live seat map showing available/locked/booked seats
- Users can select up to 10 seats and proceed to payment
- Seat is locked during payment window (10 minutes)
- On payment success: booking confirmed, e-ticket generated
- On payment failure or timeout: seat is released
- Users can view booking history and download tickets

**Non-Functional Requirements:**
- Consistency: a seat must never be double-booked (strong consistency required)
- Availability: 99.99% uptime (ticket sales = revenue-critical)
- Low latency: seat lock operation < 100ms
- Scale: 500K concurrent users during peak event launches
- Durability: booking records must never be lost

---

## STEP 2 — Capacity Estimation

Say these numbers confidently:

```
┌──────────────────────────────────────────────────────────────────┐
│ CAPACITY NUMBERS                                                  │
├─────────────────────┬────────────────────────────────────────────┤
│ Registered users    │ 50 million                                 │
│ Bookings per day    │ 5 million                                  │
│ Bookings per sec    │ ~58/sec average, ~5,000/sec peak          │
│ Peak concurrent     │ 500,000 (popular event launch)             │
│ Cities              │ 500+ cities                                │
│ Venues              │ 5,000 venues                               │
│ Seats per show      │ 10,000 – 50,000                           │
│ Seat bitmap size    │ 50K seats = 6 KB per show (Redis)         │
│ Redis lock TTL      │ 600 seconds (10 minutes)                  │
│ Ticket PDF size     │ ~200 KB per ticket                        │
│ Coldplay scenario   │ 200K seats, 1M users at 12pm noon        │
│ Search QPS          │ ~10K searches/sec peak                    │
│ DB write TPS        │ ~5K bookings/sec peak                     │
└─────────────────────┴────────────────────────────────────────────┘
```

"At 500K concurrent users all trying to book in the first 5 minutes of a popular event — that's the thundering herd scenario. I'll address this with a virtual waiting room."

---

## STEP 3 — Core Entities

"Let me define the core entities before drawing the architecture."

- **User**: profile, payment methods, booking history
- **Venue**: physical location (stadium, theater), total capacity, section layout
- **Event**: Coldplay World Tour (artist, organizer, description)
- **Show**: Event at Venue at DateTime (FK to both). One event can have multiple shows.
- **Seat**: individual physical seat in a venue (section, row, number, category)
- **Booking**: user's confirmed reservation (links user, show, seats, payment)
- **BookingSeat**: junction table (booking_id, seat_id) — many-to-many
- **Payment**: payment transaction record (Stripe payment intent ID, amount, status)
- **Ticket**: generated e-ticket (QR code URL, seat info)

---

## STEP 4 — API Design

```
GET  /events/search?city=mumbai&date=2025-01-25&genre=concert
     → Returns: [{ event_id, name, venue, thumbnail_url, min_price }]

GET  /events/{eventId}/shows
     → Returns: [{ show_id, start_time, available_seats, price_by_category }]

GET  /shows/{showId}/seatmap
     → Returns: seat map data (available/locked/booked status per seat)
     → Served from Redis bitmap + CDN for layout image

POST /bookings/lock-seats
     Body: { show_id, seat_ids: [123, 124], user_id }
     → Returns: { booking_id, lock_expires_at, total_amount }
     → Internally: Redis SET seats:locked:{seatId} {userId} EX 600 NX

POST /bookings/{bookingId}/pay
     Body: { payment_method_id, idempotency_key }
     → Returns: { booking_id, status: CONFIRMED, ticket_url }
     → Internally: Stripe charge → MySQL transaction → Kafka event

GET  /bookings/{bookingId}
     → Returns: booking details, ticket download URL

DELETE /bookings/{bookingId}/cancel
     → Releases seat lock, initiates refund if confirmed

GET  /tickets/{ticketId}/validate
     → Used by venue scanners at entry. Returns: VALID / USED / INVALID
```

---

> **► DRAW THIS on the whiteboard ◄**

## JSON REQUEST / RESPONSE EXAMPLES

```json
// GET /api/v1/shows/{showId}/seats
// Response 200 OK:
{
  "showId": "show_coldplay_2025",
  "venue": "DY Patil Stadium, Mumbai",
  "showTime": "2025-03-15T19:00:00Z",
  "categories": [
    {
      "category": "VIP",
      "price": 25000,
      "availableSeats": 142,
      "totalSeats": 500
    },
    {
      "category": "GOLD",
      "price": 10000,
      "availableSeats": 893,
      "totalSeats": 2000
    }
  ],
  "seatMap": "bitmap_base64_encoded..."
}

// POST /api/v1/bookings/lock
// Request:
{
  "showId": "show_coldplay_2025",
  "seatIds": ["VIP-A1", "VIP-A2"]
}
// Response 200 OK:
{
  "lockToken": "lock_9f2a3b4c",
  "lockedSeats": ["VIP-A1", "VIP-A2"],
  "expiresIn": 600,
  "totalAmount": 50000,
  "currency": "INR"
}
// Response 409 Conflict (seat taken):
{
  "error": "SEAT_UNAVAILABLE",
  "unavailableSeats": ["VIP-A1"],
  "message": "Seat VIP-A1 was just taken. Please choose another."
}

// POST /api/v1/bookings/confirm
// Request:
{
  "lockToken": "lock_9f2a3b4c",
  "paymentMethodId": "pm_card_visa_4242"
}
// Response 201 Created:
{
  "bookingId": "bkg_xyz789",
  "status": "CONFIRMED",
  "tickets": [
    { "ticketId": "tkt_001", "seat": "VIP-A1", "qrCode": "https://cdn.bms.com/tickets/tkt_001.png" },
    { "ticketId": "tkt_002", "seat": "VIP-A2", "qrCode": "https://cdn.bms.com/tickets/tkt_002.png" }
  ],
  "totalAmount": 50000,
  "paymentStatus": "CHARGED"
}
```

---

## STEP 5 — High-Level Architecture

► DRAW THIS ◄

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                HIGH-LEVEL ARCHITECTURE                   │
                    └─────────────────────────────────────────────────────────┘

  Users (Web/App)
       │
       ▼
┌─────────────┐        ┌────────────────────────────────────────────────────┐
│   CDN       │        │                  API Gateway                        │
│ (seat map   │        │        (Auth + Rate Limit + SSL Termination)        │
│  images,    │        └─────────────────────┬──────────────────────────────┘
│  static)    │                              │ Route by path
└─────────────┘              ┌───────────────┼───────────────┐
                             │               │               │
                    ┌────────▼───┐  ┌────────▼───┐  ┌────────▼───────┐
                    │  Search    │  │  Booking   │  │  User/Auth     │
                    │  Service   │  │  Service   │  │  Service       │
                    └────────┬───┘  └────────┬───┘  └────────────────┘
                             │               │
                    ┌────────▼───┐  ┌────────▼───────────────────────┐
                    │  Elastic-  │  │            Redis                │
                    │  search    │  │  seats:locked:{seatId} → userId │
                    │  (events   │  │  show_seats:{showId} → bitmap   │
                    │   index)   │  │  queue:{showId} → sorted set    │
                    └────────────┘  └────────────────────────────────┘
                                             │
                                    ┌────────▼───────┐
                                    │     MySQL       │
                                    │  (events,shows  │
                                    │   seats,book-   │
                                    │   ings,users)   │
                                    └────────┬────────┘
                                             │
                    ┌────────────────────────▼────────────────────────┐
                    │                     Kafka                        │
                    │   Topics: booking-confirmed, payment-processed   │
                    └──────────────┬──────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │     Ticket Generator Worker  │
                    │  (consumes Kafka events,     │
                    │   generates PDF + QR → S3)   │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │     S3 + CDN                 │
                    │  (ticket PDFs, QR codes)     │
                    └──────────────────────────────┘
```

---

> **► DRAW THIS on the whiteboard ◄**

## SEQUENCE DIAGRAM — SEAT BOOKING (Happy Path)

```
  User App      Booking Service     Redis (Lua)      MySQL          Stripe
     │               │                  │               │              │
     │ GET /shows/   │                  │               │              │
     │ {showId}/seats│                  │               │              │
     │──────────────▶│                  │               │              │
     │               │ BITMAP show_seats:{showId}       │              │
     │               │──────────────────▶               │              │
     │ [seat map:    │◀──────────────────               │              │
     │  0=avail,     │  [6000-bit bitmap]│               │              │
     │  1=taken]     │                  │               │              │
     │◀──────────────│                  │               │              │
     │               │                  │               │              │
     │ POST /lock    │                  │               │              │
     │ {seatIds:[A1, │                  │               │              │
     │  A2], showId} │                  │               │              │
     │──────────────▶│                  │               │              │
     │               │ Lua script (atomic for each seat):             │
     │               │ SET seats:locked:{A1} {userId} EX 600 NX      │
     │               │──────────────────▶               │              │
     │               │◀──────────────────               │              │
     │               │  [1=locked]      │               │              │
     │               │ SET seats:locked:{A2} {userId} EX 600 NX      │
     │               │──────────────────▶               │              │
     │               │◀──────────────────               │              │
     │               │  [1=locked]      │               │              │
     │               │                  │               │              │
     │ {lockToken,   │                  │               │              │
     │  expiresIn:600│                  │               │              │
     │  amount:1200} │                  │               │              │
     │◀──────────────│                  │               │              │
     │               │                  │               │              │
     │ POST /checkout│                  │               │              │
     │ {lockToken,   │                  │               │              │
     │  paymentMethod│                  │               │              │
     │──────────────▶│                  │               │              │
     │               │ Stripe charge    │               │              │
     │               │──────────────────────────────────────────────▶│
     │               │◀──────────────────────────────────────────────│
     │               │  {SUCCESS}       │               │              │
     │               │                  │               │              │
     │               │ BEGIN TX         │               │              │
     │               │ UPDATE seats status=BOOKED       │              │
     │               │ INSERT booking   │               │              │
     │               │ INSERT booking_seats              │              │
     │               │ COMMIT           │               │              │
     │               │──────────────────────────────────▶             │
     │               │◀──────────────────────────────────             │
     │               │                  │               │              │
     │               │ DEL seats:locked:{A1}            │              │
     │               │ DEL seats:locked:{A2}            │              │
     │               │──────────────────▶               │              │
     │               │                  │               │              │
     │ {bookingId,   │                  │               │              │
     │  qrCodeUrl}   │                  │               │              │
     │◀──────────────│                  │               │              │
```

---

## STEP 6 — Database Schema

► DRAW THIS ◄

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          MYSQL SCHEMA                                    │
└─────────────────────────────────────────────────────────────────────────┘

venues
┌──────────────┬───────────────────────────────────────────────────────────┐
│ venue_id     │ BIGINT PK AUTO_INCREMENT                                  │
│ name         │ VARCHAR(200)                                              │
│ city         │ VARCHAR(100)                                              │
│ address      │ TEXT                                                      │
│ total_cap    │ INT                                                       │
│ lat          │ FLOAT                                                     │
│ lon          │ FLOAT                                                     │
└──────────────┴───────────────────────────────────────────────────────────┘

events
┌──────────────┬───────────────────────────────────────────────────────────┐
│ event_id     │ BIGINT PK AUTO_INCREMENT                                  │
│ name         │ VARCHAR(300)                                              │
│ artist       │ VARCHAR(200)                                              │
│ genre        │ VARCHAR(50)                                               │
│ organizer_id │ BIGINT FK                                                 │
│ description  │ TEXT                                                      │
│ banner_url   │ TEXT                                                      │
└──────────────┴───────────────────────────────────────────────────────────┘

shows
┌────────────────┬─────────────────────────────────────────────────────────┐
│ show_id        │ BIGINT PK AUTO_INCREMENT                                │
│ event_id       │ BIGINT FK → events                                      │
│ venue_id       │ BIGINT FK → venues                                      │
│ start_time     │ TIMESTAMP                                               │
│ total_seats    │ INT                                                      │
│ available_seats│ INT  (decremented on booking, cache in Redis)           │
│ status         │ ENUM('UPCOMING','OPEN','SOLD_OUT','CANCELLED')          │
└────────────────┴─────────────────────────────────────────────────────────┘

seats
┌──────────────┬───────────────────────────────────────────────────────────┐
│ seat_id      │ BIGINT PK AUTO_INCREMENT                                  │
│ venue_id     │ BIGINT FK → venues                                        │
│ section      │ VARCHAR(50)  (e.g. "WEST STAND")                         │
│ row_no       │ CHAR(3)      (e.g. "A", "B", "AA")                       │
│ seat_no      │ INT                                                       │
│ category     │ ENUM('VIP','GOLD','SILVER','GENERAL')                    │
│ price        │ BIGINT  (paise, e.g. 250000 = Rs 2500)                   │
└──────────────┴───────────────────────────────────────────────────────────┘

bookings
┌──────────────┬───────────────────────────────────────────────────────────┐
│ booking_id   │ CHAR(36) PK  (UUID)                                       │
│ user_id      │ BIGINT FK → users                                         │
│ show_id      │ BIGINT FK → shows                                         │
│ total_amount │ BIGINT  (paise)                                           │
│ status       │ ENUM('PENDING','CONFIRMED','CANCELLED','REFUNDED')        │
│ payment_id   │ CHAR(36) FK → payments                                    │
│ created_at   │ TIMESTAMP DEFAULT NOW()                                   │
│ confirmed_at │ TIMESTAMP NULL                                            │
└──────────────┴───────────────────────────────────────────────────────────┘

booking_seats   (junction table — many bookings to many seats)
┌──────────────┬───────────────────────────────────────────────────────────┐
│ booking_id   │ CHAR(36) FK → bookings                                    │
│ seat_id      │ BIGINT FK → seats                                         │
│ show_id      │ BIGINT FK → shows  (for partition-friendly queries)       │
│ PRIMARY KEY  │ (booking_id, seat_id)                                     │
└──────────────┴───────────────────────────────────────────────────────────┘

payments
┌──────────────┬───────────────────────────────────────────────────────────┐
│ payment_id   │ CHAR(36) PK  (UUID)                                       │
│ booking_id   │ CHAR(36) FK → bookings                                    │
│ provider     │ ENUM('STRIPE','RAZORPAY','UPI')                          │
│ provider_ref │ VARCHAR(200)  (Stripe payment intent ID)                  │
│ amount       │ BIGINT                                                    │
│ status       │ ENUM('PENDING','SUCCESS','FAILED','REFUNDED')             │
│ created_at   │ TIMESTAMP                                                 │
└──────────────┴───────────────────────────────────────────────────────────┘

tickets
┌──────────────┬───────────────────────────────────────────────────────────┐
│ ticket_id    │ CHAR(36) PK  (UUID)                                       │
│ booking_id   │ CHAR(36) FK → bookings                                    │
│ seat_id      │ BIGINT FK → seats                                         │
│ show_id      │ BIGINT FK → shows                                         │
│ qr_code_url  │ TEXT  (S3 URL)                                            │
│ pdf_url      │ TEXT  (S3 URL)                                            │
│ scanned_at   │ TIMESTAMP NULL  (set when scanned at venue)               │
└──────────────┴───────────────────────────────────────────────────────────┘
```

---

> **► DRAW THIS on the whiteboard ◄**

## ER RELATIONSHIP DIAGRAM

```
┌────────────────────────────────────────────────────────────────────┐
│               BOOKMYSHOW — ENTITY RELATIONSHIP                      │
└────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌────────────────────┐     ┌─────────────────┐
│    users     │     │      events         │     │     venues       │
│   (MySQL)    │     │     (MySQL)         │     │    (MySQL)       │
├──────────────┤     ├────────────────────┤     ├─────────────────┤
│ PK user_id   │     │ PK event_id UUID   │     │ PK venue_id UUID │
│    email TEXT│     │    name VARCHAR    │     │    name VARCHAR  │
│    phone TEXT│     │    category ENUM   │     │    city VARCHAR  │
│    created_at│     │    description TEXT│     │    total_seats INT│
└──────────────┘     │    poster_url TEXT │     │    seating_map   │
        │            │    organizer_id FK │     └────────┬────────┘
        │ N          └────────┬───────────┘              │ 1
        │                     │ 1                         │ N
        │            N        │                  ┌────────▼────────┐
┌───────▼─────────┐  ┌───────▼───────────────┐  │      seats       │
│    bookings     │  │        shows           │  │     (MySQL)      │
│    (MySQL)      │  │       (MySQL)          │  ├─────────────────┤
├─────────────────┤  ├───────────────────────┤  │ PK seat_id UUID │
│ PK booking_id   │  │ PK show_id UUID       │  │ FK venue_id UUID │
│ FK user_id UUID │  │ FK event_id UUID      │  │    section VARCHAR│
│    total_amount │  │ FK venue_id UUID      │  │    row_no CHAR   │
│    status ENUM  │  │    start_time TS      │  │    seat_no INT   │
│    payment_id   │  │    total_seats INT    │  │    category ENUM │
│    created_at   │  │    available_seats INT│  └─────────────────┘
└────────┬────────┘  └───────────────────────┘
         │ 1
         │ N
┌────────▼────────────┐
│   booking_seats      │  ← join table (many-to-many)
│      (MySQL)         │
├─────────────────────┤
│ PK booking_id UUID  │
│ PK seat_id    UUID  │
│    price_paid BIGINT│
└─────────────────────┘

Redis Keys:
┌─────────────────────────────────────────────────────┐
│ seats:locked:{seatId}  → userId  EX 600 (10 min)   │
│ show_seats:{showId}    → BITMAP  (1 bit per seat)   │
│ show_cache:{showId}    → JSON show details TTL 5min │
└─────────────────────────────────────────────────────┘
```

---

## STEP 7 — Deep Dive: Seat Locking Protocol

"This is the most important part. Let me walk through the exact concurrency protocol."

► DRAW THIS on the whiteboard ◄

```
┌─────────────────────────────────────────────────────────────────────────┐
│             SEAT LOCKING PROTOCOL — STEP BY STEP                        │
└─────────────────────────────────────────────────────────────────────────┘

  USER A selects Seat #123                USER B selects Seat #123
          │                                        │
          ▼                                        ▼
  Lua script (atomic):              Lua script (atomic):
  GET seats:locked:123              GET seats:locked:123
    → nil (not locked)                → "userA" (LOCKED!)
  SET seats:locked:123              Return: SEAT_UNAVAILABLE
    "userA" EX 600 NX               User B shown: seat taken
    → OK (success)
          │
          ▼
  Return lock_token to User A
  User A proceeds to payment
  (Stripe payment intent created)
          │
    ┌─────▼──────────────────────┐
    │   PAYMENT IN PROGRESS      │
    │   Redis lock held: 10 min  │
    └─────┬──────────────────────┘
          │
   ┌──────▼──────────────────────────────────────────────────┐
   │  Payment SUCCESS              Payment FAILURE/TIMEOUT   │
   │       │                             │                    │
   │       ▼                             ▼                    │
   │  MySQL TRANSACTION:           Redis TTL expires          │
   │  BEGIN                        automatically              │
   │    UPDATE seats SET           Seat #123 becomes          │
   │      status='BOOKED'          available again            │
   │      WHERE seat_id=123                                   │
   │      AND show_id=456                                     │
   │      AND status='AVAILABLE'                              │
   │    (if 0 rows updated: ABORT)                            │
   │    INSERT INTO bookings ...                              │
   │    INSERT INTO booking_seats ...                         │
   │    UPDATE shows SET                                      │
   │      available_seats = available_seats - 1               │
   │  COMMIT                                                  │
   │  DEL seats:locked:123  ← explicit cleanup               │
   │  SETBIT show_seats:456 seatPos 1  ← mark bitmap         │
   │  Publish Kafka: booking-confirmed {bookingId}            │
   └──────────────────────────────────────────────────────────┘
```

**Why the MySQL check is still needed even with Redis lock:**
"The MySQL UPDATE with AND status='AVAILABLE' is a safety net. If Redis fails (network partition, Redis crash) and two instances both think they have the lock, the DB constraint prevents double-booking. Defense in depth."

---

## STEP 7B — Virtual Waiting Room (Thundering Herd)

"For Coldplay India — 1M users at noon for 200K seats. Without traffic shaping, here's what happens: 1M concurrent Redis SET NX operations → Redis CPU saturates. Then MySQL gets 100K booking transactions simultaneously → connection pool exhausted → everyone fails. Terrible experience.

My solution: virtual waiting room."

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      VIRTUAL WAITING ROOM FLOW                           │
└─────────────────────────────────────────────────────────────────────────┘

  User opens booking page for Coldplay show:
       │
       ▼
  POST /queue/join { show_id: 456 }
       │
       ▼
  Redis: ZADD queue:show:456 {timestamp} {userId}
  Return: { position: 47832, estimated_wait_minutes: 4 }
       │
       ▼
  Client polls GET /queue/position every 5 sec
  (or SSE push for position updates)
       │
       ▼
  Queue Drip Worker (runs every second):
    ZPOPMIN queue:show:456 10000  → get next 10,000 users
    For each: send "your turn" notification (SSE/push)
    User gets 5-minute token to enter booking flow
       │
       ▼
  Only 10,000 users/sec enter seat selection + locking
  Redis and MySQL workload stays manageable
```

---

## STEP 8 — Scalability

**BOTTLENECK 1: Redis Seat Lock at Peak**

"At 500K concurrent users, Redis gets flooded with lock operations. Solution: Redis Cluster sharded by show_id. All lock keys for show_id:456 go to the same shard (consistent hashing on key prefix). Single Redis instance handles ~100K ops/sec; cluster of 10 handles 1M ops/sec."

**BOTTLENECK 2: MySQL at Booking Confirmation**

"5K confirmed bookings/sec = 5K MySQL transactions/sec. Solution: Connection pooling (HikariCP, max 200 connections per app server, 20 app servers = 4K DB connections). Read replicas for non-transactional reads (seat map status display). MySQL cluster with semi-synchronous replication for the primary."

**BOTTLENECK 3: Seat Map Display for 500K Users**

"Showing which seats are available/locked/booked to 500K concurrent users — that's 500K requests for seat state per show. Solution: Redis bitmap serves all seat state reads. Seat map SVG layout served from CDN. Only real-time lock/book status from Redis. No DB read for seat map display."

**BOTTLENECK 4: Ticket Generation Spike**

"5K bookings confirmed/sec → 5K PDFs to generate. PDFs are CPU-intensive. Solution: Kafka decouples confirmation from generation. Ticket generator worker pool (auto-scales on Kafka consumer lag). Workers: read booking details → render PDF → upload to S3 → update ticket table. Async, so user sees 'Ticket is being generated' immediately, gets URL in 30 seconds."

---

## STEP 8 — TRADE-OFFS

*"Let me walk through the key architectural trade-offs I made and why."*

```
┌─────────────────────────────┬────────────────────────────┬──────────────────────────────────────────────────────────┐
│ DECISION                    │ CHOICE MADE                │ TRADE-OFF                                                │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Seat locking mechanism      │ Redis SET NX EX 600        │ Sub-ms lock + auto-expire on timeout vs. Redis not       │
│                             │                            │ durable (lock lost on crash — acceptable, re-selects)    │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Seat availability store     │ Redis Bitmap per show      │ O(1) GETBIT/SETBIT, 6KB for 50K seats vs. can't         │
│                             │                            │ store metadata per seat                                  │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ DB for bookings             │ MySQL ACID transaction     │ Guarantees exactly-one booking per seat vs. doesn't      │
│                             │                            │ scale to 100M bookings/day (partition by event_id)       │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Payment integration         │ Stripe PaymentIntent       │ Idempotent retry on timeout vs. slightly higher latency  │
│                             │                            │ than direct bank API                                     │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Concurrency model           │ Redis lock (optimistic)    │ Lightweight, auto-expire, handles payment timeout        │
│                             │                            │ gracefully vs. DB lock held 3 min = deadlocks            │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Ticket PDF generation       │ Async Kafka + S3           │ Booking response is fast; PDF ready in seconds vs.       │
│                             │                            │ need polling/webhook for PDF completion                  │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Virtual waiting room        │ Redis sorted set queue     │ Prevents thundering herd on Coldplay-scale events vs.    │
│                             │                            │ adds complexity and user confusion                       │
└─────────────────────────────┴────────────────────────────┴──────────────────────────────────────────────────────────┘
```

*"The most important trade-off was Redis locking vs DB locking. If we used a DB row lock and held it during payment (2-3 minutes), we'd get connection pool exhaustion and deadlocks at scale. Redis TTL auto-releases the lock if payment times out — no manual cleanup."*

---

## WHAT NOT TO SAY ✗

- ✗ "I'll use a database row lock for seat reservation" — DB locks held for 2-3 minutes during payment = deadlock + connection exhaustion. Always Redis for the lock, DB for the final commit.
- ✗ "I'll use optimistic locking with a version field on the seat" — version conflict at payment commit means user pays and then finds out the seat is gone. Terrible UX. Lock FIRST, pay SECOND.
- ✗ "I'll just use a unique constraint on (show_id, seat_id) in the bookings table" — unique constraint prevents duplicates in committed data but doesn't handle concurrent PENDING bookings racing to confirm.
- ✗ "I'll handle the thundering herd with just rate limiting" — rate limiting returns 429 errors. Virtual queue gives users a fair wait time and much better UX.
- ✗ "Redis is a cache so it's okay if it loses the lock data" — Redis lock state MUST be persistent during payment. Use Redis with AOF persistence or treat loss as "seat available again" (TTL protects this).
- ✗ "I'll generate tickets synchronously in the booking confirmation API call" — PDF generation is slow (200ms–2sec). Never block the booking confirmation response on PDF creation. Use Kafka async.
- ✗ "The seat map can be refreshed from MySQL on every page load" — at 500K concurrent users each loading a 50K-seat venue map, that's catastrophic DB load. Bitmap in Redis + CDN for layout.

---

## SENIOR TRAP QUESTIONS (15 YOE Level)

### Category 1: Extreme Concurrency

**Q: "1M users try to book Coldplay tickets the moment they go on sale at noon. Your Redis gets 1M SET NX operations in the first second. What happens and how do you handle it?"**

A: "Redis can handle ~100K ops/sec on a single instance, so 1M in the first second would saturate it. My answer is the virtual waiting room — I don't let all 1M users hit Redis simultaneously. When users open the booking page, they join a Redis sorted set queue. A drip worker admits 10K users/sec into the actual booking flow. The remaining users see their queue position and estimated wait time. This caps Redis seat lock operations at 10K/sec, well within single-instance capacity. The queue itself uses a different Redis keyspace (queue:show:456 sorted set), and I'd shard by show_id to spread load further."

**Q: "Two users select the same 5 seats simultaneously. Your Lua script runs atomically per seat. How do you handle locking multiple seats without partial lock state?"**

A: "I lock all 5 seats in a single Lua script that runs atomically. The script: checks all 5 seats are unlocked, and only if ALL are free, sets all 5 locks. If any seat is already locked, the script returns which seat failed and sets none. This all-or-nothing multi-seat lock prevents scenarios where user gets seats 1,2,3 locked but seat 4 is taken — I'd have to manually rollback the first 3 locks, which is error-prone. Atomic Lua script handles it cleanly."

### Category 2: Payment Edge Cases

**Q: "User has their seat locked for 10 minutes, proceeds to payment, and the payment gateway call times out after 8 minutes. Did we charge the user? How do we handle this?"**

A: "Three possibilities: (1) Charge succeeded but response lost in network — idempotency key on the Stripe call lets me retry safely; Stripe returns the same success result. (2) Charge failed before Stripe processed — retry is safe. (3) The 10-minute Redis TTL is about to expire mid-payment. I extend the TTL when the payment API call starts: EXPIRE seats:locked:{seatId} 900 (extend to 15 min). On payment timeout: I query Stripe's payment intent by idempotency key to check actual charge status. If charged: confirm booking. If not charged: release lock (or let TTL expire), notify user to retry. I never release a lock while a payment is actively in-flight — I check Stripe's status first."

**Q: "What if the booking service crashes after Stripe charges the user but before the MySQL transaction commits?"**

A: "This is the dual-write problem. My defense: Kafka outbox pattern. Before charging, I write a 'payment_pending' record to the DB. After Stripe returns success, instead of directly committing the booking, I publish to Kafka. A separate booking-confirmer service consumes the Kafka event and commits the MySQL transaction. If the service crashes after Stripe charge but before Kafka publish: on restart, I check all payment_pending records against Stripe's API — if Stripe says paid, I re-publish the Kafka event. Idempotent processing ensures the booking confirmer won't double-insert. The user gets their booking confirmed within seconds of restart."

### Category 3: Operations and Organizer Features

**Q: "An organizer wants to add 5,000 standing-room-only tickets to a sold-out show 30 minutes before it starts. Walk me through what changes in the system."**

A: "I'd need to update five things atomically: (1) INSERT 5,000 new seat rows into MySQL seats table with category='GENERAL'. (2) UPDATE shows SET total_seats = total_seats + 5000, available_seats = available_seats + 5000. (3) Extend the Redis bitmap show_seats:{showId} — SETBIT doesn't need resizing, it auto-extends. New bits default to 0 (available). (4) Invalidate any cached seat map data so users see the new seats immediately. (5) Push a real-time notification via SSE to all users currently on the sold-out page: 'New standing room tickets added.' The seat map CDN cache for the static layout image needs a new version (add cache-busting query param to the CDN URL). I'd wrap the MySQL operations in a transaction but steps 3–5 are async post-commit."

---

## KEY NUMBERS

```
┌─────────────────────────────────┬──────────────────────────────────────────┐
│ METRIC                          │ VALUE / NOTES                            │
├─────────────────────────────────┼──────────────────────────────────────────┤
│ Registered users                │ 50 million                               │
│ Bookings per day                │ 5 million                                │
│ Peak bookings/sec               │ ~5,000/sec (event launch)                │
│ Redis lock TTL                  │ 600 sec (10 minutes)                     │
│ Max seats user can book         │ 10 seats per transaction                 │
│ Seat bitmap for 50K seat venue  │ 50,000 bits = 6.25 KB                   │
│ Redis single instance ops/sec   │ ~100,000 ops/sec                        │
│ MySQL max connections           │ ~4,000 (200 per server × 20 servers)    │
│ Virtual queue drip rate         │ 10,000 users/sec                        │
│ Ticket PDF size                 │ ~200 KB                                  │
│ S3 ticket storage cost          │ ~$0.023/GB/month                        │
│ Kafka retention for booking     │ 7 days (for replay on failure)          │
│ Redis cluster shards            │ 10 shards (handles 1M lock ops/sec)     │
│ CDN cache TTL for seat maps     │ 24 hours (invalidated on seat add/remove)│
│ Elasticsearch event index size  │ ~10 million events × ~2KB = ~20 GB      │
└─────────────────────────────────┴──────────────────────────────────────────┘
```
