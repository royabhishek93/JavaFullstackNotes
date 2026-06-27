# BookMyShow - Complete 60-Minute System Design Interview Simulation

## For 15+ Years Experienced Architect

---

## 📋 Interview Overview

```
Duration: 60 minutes
Level: Staff/Principal Engineer
Company: FAANG or equivalent
Interviewer: Senior Staff Engineer
Format: Collaborative design discussion
```

---

## ⏱️ Time Allocation

```
┌──────────────────────────────────────────────────────────┐
│             INTERVIEW PHASES (60 minutes)                 │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Phase 1: Requirements & Scope (10 mins)                 │
│  ├─ Functional requirements                              │
│  ├─ Non-functional requirements                          │
│  ├─ Scale estimation                                     │
│  └─ Out of scope clarification                           │
│                                                           │
│  Phase 2: High-Level Design (15 mins)                    │
│  ├─ System components                                    │
│  ├─ Data flow                                            │
│  ├─ API design                                           │
│  └─ Database schema                                      │
│                                                           │
│  Phase 3: Deep Dive (25 mins)                            │
│  ├─ Critical path: Seat booking flow                     │
│  ├─ Concurrency control                                  │
│  ├─ Payment atomicity                                    │
│  ├─ Caching strategy                                     │
│  └─ Scaling to 1M users                                  │
│                                                           │
│  Phase 4: Wrap-up (10 mins)                              │
│  ├─ Trade-offs discussion                                │
│  ├─ Bottlenecks & solutions                              │
│  ├─ Monitoring & operations                              │
│  └─ Questions for interviewer                            │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## 🎭 PHASE 1: Requirements & Scope (10 minutes)

### **Interviewer Opening:**

> "Design BookMyShow - a movie ticket booking system like Fandango. Users should be able to search for movies, view showtimes, select seats, and complete booking. Let's start with understanding the requirements."

---

### ✅ **GOOD Response (Staff/Principal Level):**

**Candidate:** "Great! Let me clarify the requirements before jumping into design."

#### **1. Functional Requirements (Candidate drives this):**

```
Candidate: "Let me confirm the core features we need to support:

1. Movie Search
   - Search by title, genre, language, location?
   - Filter by rating, release date, theater amenities?
   - Real-time or cached results acceptable?

2. Show Listing
   - View available showtimes for next 7 days?
   - Show available seats count?
   - Price displayed per seat type?

3. Seat Selection
   - Interactive seat map?
   - Multiple seats selection?
   - Real-time availability updates?

4. Booking & Payment
   - Hold seats for X minutes during payment?
   - Multiple payment methods?
   - Instant confirmation or async?

5. Post-Booking
   - QR code ticket generation?
   - Email/SMS notifications?
   - Cancellation/refund support?

Which of these are in scope for this discussion?"
```

**Interviewer:** "Focus on 1-4. Assume cancellations are out of scope."

---

#### **2. Non-Functional Requirements (Critical!):**

```
Candidate: "Now let me understand the scale and performance targets:

Scale:
- How many daily active users?
  Interviewer: "10 million DAU"
  
- Peak concurrent users?
  Interviewer: "100k normally, 1M during movie premieres"
  
- Geographic distribution?
  Interviewer: "Primarily India, expanding to US/EU"

Performance:
- Search latency SLA?
  Interviewer: "Sub-200ms for p99"
  
- Booking completion time?
  Interviewer: "< 1 second for seat selection, < 5 seconds for payment"

Consistency:
- Can we tolerate eventual consistency for search?
  Interviewer: "Yes, but booking must be strongly consistent"
  
- Double-booking acceptable?
  Interviewer: "Absolutely not"

Availability:
- Target uptime?
  Interviewer: "99.9% (three nines)"
```

---

#### **3. Back-of-Envelope Calculations:**

```
Candidate: "Let me do quick capacity estimation:

Users & Traffic:
├─ DAU: 10M users
├─ Sessions per user: 1.5
├─ Requests per session: 20 (search, browse, maybe book)
├─ Total daily requests: 10M × 1.5 × 20 = 300M requests
└─ Average QPS: 300M ÷ 86,400 = 3,472 QPS

Peak Load (Movie Premiere):
├─ Concurrent users: 1M (100x spike)
├─ Peak QPS: 3,472 × 100 = 347,200 QPS
└─ Booking rate: 10k bookings/second

Bookings:
├─ Conversion rate: 5% (users who complete booking)
├─ Daily bookings: 10M × 5% = 500k bookings
├─ Seats per booking: 2.5 (average)
└─ Daily seat bookings: 1.25M seats

Storage:
├─ Booking record: 2 KB
├─ Daily storage: 500k × 2 KB = 1 GB/day
├─ Annual: 365 GB
└─ 3-year retention: ~1.1 TB

Does this align with your expectations?"
```

**Interviewer:** "Yes, that's reasonable. Proceed with design."

---

### ❌ **POOR Response (Mid-Level):**

```
Candidate: "I'll design a system where users can search movies and book tickets."

[Immediately starts drawing architecture without clarifying]

Red Flags:
- Didn't ask about scale
- No discussion of consistency requirements
- No capacity estimation
- Didn't clarify which features are in scope
- Jumping to solution without understanding problem
```

---

## 🏗️ PHASE 2: High-Level Design (15 minutes)

### **Interviewer:** "Draw the high-level architecture."

---

### ✅ **GOOD Response:**

```
Candidate: "Let me start with the major components, then drill down."

┌─────────────────────────────────────────────────────────┐
│              HIGH-LEVEL ARCHITECTURE                     │
└─────────────────────────────────────────────────────────┘

    [Client Apps]
         │
         ▼
    ┌─────────┐
    │   CDN   │ ← Static assets (posters, images)
    └────┬────┘
         │
         ▼
    ┌──────────────┐
    │ API Gateway  │ ← Rate limiting, auth, routing
    └──────┬───────┘
           │
    ┌──────┼──────┐
    │      │      │
    ▼      ▼      ▼
 ┌────┐ ┌────┐ ┌────┐
 │Search Booking│Payment│ ← Microservices
 │Service│Service│Service│
 └──┬─┘ └──┬─┘ └──┬─┘
    │      │      │
    ├──────┼──────┤
    │   Cache    │ ← Redis (seat status, search results)
    └──────┬──────┘
           │
    ┌──────┼──────┐
    │      │      │
    ▼      ▼      ▼
┌─────┐┌────┐┌────┐
│ ES  ││PG  ││MySQL│ ← Elasticsearch, PostgreSQL, MySQL
│Search││Booking││Catalog│
└─────┘└────┘└────┘

Candidate explains each component:

"API Gateway:
- Rate limiting: 100 req/min per user
- JWT authentication
- Request routing to microservices

Search Service:
- Stateless, read-heavy
- Queries Elasticsearch for fast full-text search
- 99% cache hit rate (5-min TTL)

Booking Service:
- Stateful (manages seat locks)
- Writes to PostgreSQL with ACID guarantees
- Pessimistic locking (FOR UPDATE)

Payment Service:
- Integrates with Stripe/Razorpay
- Idempotency keys for safe retries
- Async confirmation via webhooks

Cache (Redis):
- Seat availability: 30-second TTL
- Search results: 5-minute TTL
- Pub/Sub for real-time updates

Databases:
- PostgreSQL: Bookings (strong consistency)
- MySQL: Movie catalog (read replicas)
- Elasticsearch: Fast search with filters"
```

---

### **API Design:**

```
Candidate: "Here are the key APIs:

1. Search Movies
GET /api/v1/movies/search?city=Mumbai&date=2024-04-05&title=Avengers
Response: List of movies with shows

2. Get Seat Map
GET /api/v1/shows/{showId}/seats
Response: Seat layout with status (AVAILABLE/BOOKED/RESERVED)

3. Reserve Seats
POST /api/v1/bookings
Body: { showId, seatIds: [1,2,3], userId }
Response: { bookingId, expiresIn: 15mins }

4. Confirm Booking
POST /api/v1/bookings/{bookingId}/confirm
Body: { paymentToken }
Response: { ticket, qrCode }

All APIs use JWT for auth, return standard error codes."
```

---

### **Database Schema (High-Level):**

```
Candidate: "Let me sketch the core entities:

┌──────┐ 1:N  ┌──────┐ 1:N  ┌──────┐ 1:N  ┌──────┐
│ City │─────>│Theater│─────>│Screen│─────>│ Seat │
└──────┘      └──────┘      └──────┘      └──────┘

┌──────┐ 1:N  ┌──────┐ 1:N  ┌────────────┐
│Movie │─────>│ Show │─────>│SeatAvailabi│
└──────┘      └──────┘      └────────────┘
                    │1           │N
                    │            │
                    ▼            ▼
┌──────┐ 1:N  ┌────────┐ 1:1  ┌────────┐
│ User │─────>│Booking │─────>│Payment │
└──────┘      └────────┘      └────────┘
                    │1
                    │
                    ▼N
              ┌───────────┐
              │BookingSeat│
              └───────────┘

Key tables:
- seat_availability (show_id, seat_id) ← Composite PK
- booking: status (PENDING/CONFIRMED/EXPIRED)
- payment: idempotency_key (prevent double charge)

Indexes on:
- Foreign keys
- Status fields
- created_at (for pagination)
- expires_at (for cleanup job)"
```

**Interviewer:** "Good. Now let's deep dive into the critical path."

---

### ❌ **POOR Response:**

```
Candidate: [Draws boxes without explaining]

"We have web servers connected to database."

Red Flags:
- No component explanation
- Missing cache layer
- No API design
- No database schema
- Too vague, no details
```

---

## 🔍 PHASE 3: Deep Dive (25 minutes)

**Interviewer:** "Walk me through what happens when two users click the same seat simultaneously."

---

### ✅ **EXCELLENT Response:**

```
Candidate: "This is the critical race condition. Let me show how we prevent double-booking:

┌─────────────────────────────────────────────────────────┐
│           SEAT BOOKING FLOW (CRITICAL PATH)              │
└─────────────────────────────────────────────────────────┘

User A                          User B
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
  │  LOCK  │◄──────ACQUIRED────│  WAIT  │ ← BLOCKS HERE
  │ Seat 5 │                   │        │
  └────┬───┘                   └────────┘
       │
       │ Check: Available? YES
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
       │                           │ Check: Available? NO
       │                           │ ROLLBACK
       │                           ▼
       │                      [Error: Seat taken]
       ▼
  [Success: Seat reserved]

Code Implementation:

@Transactional(isolation = Isolation.READ_COMMITTED)
public Booking reserveSeats(BookingRequest request) {
    
    // Step 1: Acquire row-level locks
    List<SeatAvailability> seats = 
        seatRepo.findByIdsForUpdate(request.getSeatIds());
    // FOR UPDATE acquires exclusive lock
    // User B will BLOCK here until User A commits
    
    // Step 2: Validate availability
    if (seats have any BOOKED or RESERVED) {
        throw new SeatNotAvailableException();
    }
    
    // Step 3: Reserve seats
    seats.forEach(s -> {
        s.setStatus(RESERVED);
        s.setReservedUntil(now + 15mins);
    });
    
    // Step 4: Create booking (PENDING)
    Booking booking = new Booking(PENDING, expires in 15mins);
    
    return booking;
}

Why this works:
✓ FOR UPDATE = exclusive row lock
✓ User B blocks until User A commits
✓ When User B executes, sees updated status
✓ No dirty reads (isolation level prevents)"
```

---

**Interviewer:** "What about payment? What if payment succeeds but server crashes?"

```
Candidate: "Great question. This is the distributed transaction problem.
I use a 3-phase commit pattern:

┌─────────────────────────────────────────────────────────┐
│              3-PHASE COMMIT PATTERN                      │
└─────────────────────────────────────────────────────────┘

PHASE 1: RESERVE
├─ Create booking (status: PENDING)
├─ Lock seats (status: RESERVED)
├─ Set 15-minute expiry
└─ Commit to database ✅

PHASE 2: CHARGE
├─ Call Stripe API with idempotency_key
├─ idempotency_key = 'booking_' + bookingId
│  (If retry, Stripe returns cached response - no double charge)
├─ If success: proceed to Phase 3
└─ If failure: release seats, return error

PHASE 3: CONFIRM
├─ Update booking (status: CONFIRMED)
├─ Update seats (status: BOOKED)
├─ Generate ticket
└─ Send email (async)

Failure Handling:
──────────────────────────────────────────────────────────
Scenario: Payment succeeds, server crashes before confirm

Solution: Stripe Webhook
┌────────┐  Charge OK  ┌────────┐  💥 CRASH
│ Stripe │────────────>│ Server │
└────────┘             └────────┘
    │
    │ Retries webhook (up to 10 times)
    ▼
POST /webhooks/stripe { transactionId, bookingId }
    │
    │ Idempotent handler
    ▼
if (booking.status == PENDING) {
    // Server restarted, process confirmation
    confirmBooking(bookingId, transactionId);
}

This ensures eventual consistency:
- User charged → webhook retries until confirmed
- Webhook is idempotent (safe to process multiple times)
- No manual intervention needed"
```

---

**Interviewer:** "How do you handle 1M users during a movie premiere?"

```
Candidate: "I use a load shedding strategy with 3 tiers:

┌─────────────────────────────────────────────────────────┐
│              LOAD SHEDDING (1M USERS)                    │
└─────────────────────────────────────────────────────────┘

                    1M Concurrent Users
                          │
               ┌──────────┼──────────┐
               │          │          │
         ┌─────▼────┐ ┌──▼─────┐ ┌──▼────────┐
         │  TIER 1  │ │ TIER 2 │ │  TIER 3   │
         │IMMEDIATE │ │ QUEUED │ │ REJECTED  │
         └──────────┘ └────────┘ └───────────┘
         50k users    450k users  500k users
         (5%)         (45%)       (50%)
         
TIER 1: Immediate Processing
├─ First 50k requests go through
├─ Processed synchronously
└─ Sub-second response

TIER 2: Queue System
├─ Next 450k requests queued
├─ SQS FIFO queue
├─ Processed within 30 seconds
├─ User polls: GET /queue/{queueId}
└─ WebSocket updates on status

TIER 3: Graceful Rejection
├─ Remaining 500k requests
├─ HTTP 429 (Too Many Requests)
├─ Retry-After: 60 seconds
└─ Better than crashing!

Capacity Planning:
──────────────────────────────────────────────────────────
Normal: 100 servers (10k users)
Peak: 1500 servers (1M users)

Auto-scaling:
- Pre-warm at 9 AM (1 hour before)
- Scale from 100 → 500 servers
- At 10 AM launch: scale to 1500
- Cost: $850 for 30-minute peak vs $500k/year always running

Database:
- Shard by city: 50 shards
- Each shard: 1000 bookings/sec
- Total: 50k bookings/sec ✅

Cache:
- 200 Redis nodes
- Pre-warm all shows at 9 AM
- Hit rate: 95%+"
```

---

### ❌ **POOR Response:**

```
Candidate: "I'll use a lock to prevent double-booking."

Interviewer: "What kind of lock?"
Candidate: "A mutex in Java."
Interviewer: "What about multiple servers?"
Candidate: "Um... distributed lock?"
Interviewer: "How does that work?"
Candidate: [struggles]

Red Flags:
- Vague answers ("use a lock")
- No implementation details
- Doesn't think about distributed systems
- No handling of failure scenarios
```

---

## 📊 PHASE 4: Wrap-up (10 minutes)

**Interviewer:** "Let's discuss trade-offs. What are the bottlenecks?"

---

### ✅ **EXCELLENT Response:**

```
Candidate: "Let me identify bottlenecks and solutions:

1. Database Writes (Bookings)
   Bottleneck:
   ├─ 50k bookings/sec at peak
   ├─ Single master can handle ~1k writes/sec
   └─ Would overload quickly
   
   Solution:
   ├─ Shard by city_id (50 shards)
   ├─ Each shard: 1k writes/sec
   ├─ Total capacity: 50k writes/sec ✅
   └─ Cost: 50 masters + 150 replicas = $350k/year

2. Cache Stampede
   Bottleneck:
   ├─ Popular show cache expires
   ├─ 10k requests hit database simultaneously
   └─ Database overload
   
   Solution:
   ├─ Lock-based cache refresh (only 1 request refreshes)
   ├─ Probabilistic early expiration
   ├─ Pre-warm cache before high traffic
   └─ Fallback to stale cache if DB slow

3. Payment Gateway Timeout
   Bottleneck:
   ├─ Stripe API timeout (30 seconds)
   ├─ User doesn't know if charged
   └─ Support tickets increase
   
   Solution:
   ├─ Poll Stripe API with exponential backoff
   ├─ Webhook for eventual confirmation
   ├─ Show user: "Payment processing, check email"
   └─ Idempotency ensures no double charge

4. WebSocket Connections (Real-time)
   Bottleneck:
   ├─ 1M concurrent WebSocket connections
   ├─ Each server handles 10k connections
   └─ Need 100 servers just for WebSocket
   
   Solution:
   ├─ Use Redis Pub/Sub for broadcast
   ├─ Server-side events (simpler than WebSocket)
   ├─ Polling as fallback (every 5 seconds)
   └─ Cost vs benefit analysis

Trade-offs I made:
──────────────────────────────────────────────────────────
1. Denormalized available_seats in shows table
   ✓ Pro: Fast reads (no COUNT query)
   ✗ Con: Must update in same transaction

2. 15-minute seat hold
   ✓ Pro: User has time to complete payment
   ✗ Con: Seats unavailable to others

3. Eventual consistency for search
   ✓ Pro: Can cache aggressively (fast)
   ✗ Con: May show stale data (acceptable)

4. Single master per shard
   ✓ Pro: Strong consistency, simple
   ✗ Con: Higher write latency from other regions"
```

---

**Interviewer:** "How would you monitor this system?"

```
Candidate: "Key metrics to track:

Availability:
├─ Booking success rate (target: >99%)
├─ API response time (p50, p95, p99)
└─ Error rate by API endpoint

Performance:
├─ Booking latency (target: <1s)
├─ Search latency (target: <200ms)
├─ Cache hit rate (target: >90%)
└─ Database query time

Business:
├─ Bookings per second
├─ Revenue per hour
├─ Conversion rate (search → booking)
└─ Average seats per booking

Alerts:
├─ P99 latency >2 seconds → Page on-call
├─ Error rate >5% → Page on-call
├─ Cache hit rate <80% → Alert team
├─ Database connections >80% → Auto-scale
└─ Payment failures >10% → Alert + circuit breaker

Tools:
├─ Metrics: Prometheus + Grafana
├─ Logs: ELK stack (Elasticsearch, Logstash, Kibana)
├─ Tracing: Jaeger (distributed traces)
└─ APM: DataDog or New Relic"
```

---

## 🎯 Scoring Rubric

```
┌──────────────┬─────────────────────────────────────────────────────┐
│    Level     │               Demonstrated Skills                    │
├──────────────┼─────────────────────────────────────────────────────┤
│   Junior     │ - Draws basic boxes                                 │
│   (Fail)     │ - No scale estimation                               │
│              │ - Doesn't ask clarifying questions                  │
│              │ - Ignores concurrency issues                        │
├──────────────┼─────────────────────────────────────────────────────┤
│   Mid-Level  │ - Identifies main components                        │
│   (Weak)     │ - Some capacity estimation                          │
│              │ - Mentions "use locks" (vague)                      │
│              │ - No discussion of failure handling                 │
├──────────────┼─────────────────────────────────────────────────────┤
│   Senior     │ - Clear architecture with components explained      │
│   (Good)     │ - Accurate capacity estimation                      │
│              │ - Explains pessimistic locking with FOR UPDATE      │
│              │ - Discusses basic failure scenarios                 │
│              │ - API design included                               │
├──────────────┼─────────────────────────────────────────────────────┤
│   Staff      │ - Drives requirements gathering                     │
│ (Excellent)  │ - Detailed capacity planning with calculations      │
│              │ - Multiple solutions with trade-off analysis        │
│              │ - Handles distributed systems (multi-DC)            │
│              │ - Payment atomicity with webhooks                   │
│              │ - Load shedding strategy for peak traffic           │
│              │ - Monitoring and operational considerations         │
├──────────────┼─────────────────────────────────────────────────────┤
│  Principal   │ - Everything from Staff level, plus:                │
│ (Outstanding)│ - Cost analysis with actual numbers                 │
│              │ - Discusses organizational impact                   │
│              │ - Proposes experimentation/A-B testing              │
│              │ - Anticipates interviewer questions                 │
│              │ - References real-world production experiences      │
│              │ - Suggests gradual rollout strategy                 │
└──────────────┴─────────────────────────────────────────────────────┘
```

---

## 💡 Post-Interview Self-Assessment

After the interview, rate yourself:

```
□ Did I ask clarifying questions before diving in?
□ Did I estimate scale (DAU, QPS, storage)?
□ Did I explain my design choices and trade-offs?
□ Did I handle the double-booking race condition correctly?
□ Did I discuss payment atomicity and failure handling?
□ Did I consider peak load and scalability?
□ Did I identify bottlenecks and propose solutions?
□ Did I discuss monitoring and operations?
□ Did I leave time for interviewer questions?
□ Did I communicate clearly and structured my thoughts?

8-10 checks: Strong hire (Staff/Principal)
5-7 checks: Hire (Senior)
3-4 checks: Weak hire (Mid)
0-2 checks: No hire
```

---

## 🎓 Interview Tips

**DO:**
- ✅ Ask questions to clarify requirements
- ✅ Start with high-level, then drill down
- ✅ Use rough numbers for estimation
- ✅ Discuss trade-offs explicitly
- ✅ Draw diagrams as you explain
- ✅ Acknowledge what you don't know
- ✅ Think out loud

**DON'T:**
- ❌ Jump into solution without requirements
- ❌ Design in silence (interviewer can't help)
- ❌ Claim you know everything
- ❌ Ignore interviewer hints
- ❌ Get stuck on minor details
- ❌ Forget about operations/monitoring
- ❌ Run out of time

This is your complete interview simulation guide! 🎯
