# BookMyShow - Architect Quick Reference Cheat Sheet

## 🚀 For Last-Minute Interview Prep (15+ Years)

---

## ⚡ Core Numbers to Memorize

```
SCALE ESTIMATES
═══════════════════════════════════════════════════════════
DAU: 10M users
Concurrent: 100k normal, 1M peak
Daily bookings: 500k
Conversion rate: 5%
Seats per booking: 2.5

QPS CALCULATION
═══════════════════════════════════════════════════════════
Daily requests: 10M × 1.5 sessions × 20 requests = 300M
Average QPS: 300M ÷ 86,400 = 3,472 QPS
Peak QPS: 3,472 × 10 = 34,720 QPS
Server capacity: 200 req/sec per c5.2xlarge
Servers needed: 34,720 ÷ 200 × 1.5 (safety) = 260 servers

STORAGE
═══════════════════════════════════════════════════════════
Booking size: 2 KB
Daily storage: 500k × 2 KB = 1 GB/day
Annual: 365 GB
3-year: ~1.1 TB

LATENCY TARGETS
═══════════════════════════════════════════════════════════
Search: <200ms (p99)
Booking: <1s (seat selection)
Payment: <5s (including gateway)
Cache: <50ms
Database: <100ms
```

---

## 🏗️ Key Architecture Decisions

```
TECHNOLOGY STACK
═══════════════════════════════════════════════════════════
Application: Java/Spring Boot (200 req/sec per instance)
Cache: Redis (100k ops/sec per node)
Search: Elasticsearch (2k queries/sec per node)
Queue: Kafka/SQS (100k messages/sec)
CDN: CloudFlare (static assets)

DATABASES (WHY EACH?)
═══════════════════════════════════════════════════════════
PostgreSQL → Bookings (ACID, FOR UPDATE locks)
MySQL → Catalog (read replicas, static data)
Elasticsearch → Search (full-text, geo-spatial)

ISOLATION LEVEL
═══════════════════════════════════════════════════════════
READ_COMMITTED + FOR UPDATE ✅
(NOT SERIALIZABLE - 5x slower, unnecessary)

LOCKING STRATEGY
═══════════════════════════════════════════════════════════
Pessimistic (FOR UPDATE) ✅
- High contention (popular shows)
- 10k bookings/sec throughput

Optimistic (version field) ❌
- Only if low contention
- Many retries at scale
```

---

## 🎯 Critical Interview Answers

### **Q: How prevent double-booking?**

```sql
-- Row-level lock (PostgreSQL)
BEGIN TRANSACTION;
SELECT * FROM seat_availability 
WHERE show_id=123 AND seat_id=5 
FOR UPDATE;  -- ← BLOCKS other users

IF status = 'AVAILABLE' THEN
  UPDATE seat_availability SET status='RESERVED';
  COMMIT;
ELSE
  ROLLBACK;
  RETURN 'Seat taken';
END IF;
```

**Key point:** FOR UPDATE acquires exclusive lock, User B waits until User A commits

---

### **Q: Payment atomicity (user charged, server crashes)?**

```
3-PHASE COMMIT
═══════════════════════════════════════════════════════════
Phase 1: RESERVE
├─ booking.status = PENDING
├─ seat.status = RESERVED  
└─ expires_at = NOW() + 15mins

Phase 2: CHARGE
├─ Call Stripe with idempotency_key
├─ If success: proceed
└─ If fail: release seats

Phase 3: CONFIRM
├─ booking.status = CONFIRMED
├─ seat.status = BOOKED
└─ Generate ticket

FAILURE RECOVERY
═══════════════════════════════════════════════════════════
Stripe webhook retries (up to 10x)
POST /webhooks/stripe { transactionId, bookingId }

if (booking.status == PENDING) {
  confirmBooking(bookingId);  // Idempotent
}
```

**Key point:** Webhook ensures eventual consistency even if server crashes

---

### **Q: Handle 1M concurrent users (100x spike)?**

```
LOAD SHEDDING (3 TIERS)
═══════════════════════════════════════════════════════════
Tier 1 (5%): 50k users → Immediate (sync)
Tier 2 (45%): 450k users → Queue (30s SQS)
Tier 3 (50%): 500k users → Reject (HTTP 429)

AUTO-SCALING
═══════════════════════════════════════════════════════════
Normal: 100 servers
Pre-warm (9 AM): 500 servers
Peak (10 AM): 1500 servers
Cost: $850 for 30-min peak

DATABASE SHARDING
═══════════════════════════════════════════════════════════
50 shards by city_id
Each shard: 1k writes/sec
Total: 50k bookings/sec ✅

CACHE PRE-WARMING
═══════════════════════════════════════════════════════════
At 9 AM (1 hour before):
- All shows for popular movie
- Seat maps (all AVAILABLE initially)
- Theater details
```

---

## 📊 Database Schema (Quick Reference)

```sql
-- Core entities (memorize these)

CREATE TABLE show (
  id BIGINT PRIMARY KEY,
  movie_id BIGINT,
  screen_id BIGINT,
  show_date DATE,
  start_time TIME,
  available_seats INT,  -- Denormalized for performance
  total_seats INT
);

CREATE TABLE seat_availability (
  show_id BIGINT,
  seat_id BIGINT,
  status VARCHAR(20),  -- AVAILABLE, RESERVED, BOOKED
  reserved_until TIMESTAMP,
  booking_id VARCHAR(36),
  PRIMARY KEY (show_id, seat_id)
);

CREATE TABLE booking (
  id VARCHAR(36) PRIMARY KEY,  -- UUID
  user_id BIGINT,
  show_id BIGINT,
  booking_status VARCHAR(20),  -- PENDING, CONFIRMED, EXPIRED
  payment_id VARCHAR(36),
  expires_at TIMESTAMP,  -- created_at + 15 mins
  INDEX idx_expires_at (expires_at)  -- For cleanup job
);

CREATE TABLE payment (
  id VARCHAR(36) PRIMARY KEY,
  booking_id VARCHAR(36) UNIQUE,  -- 1:1 relationship
  transaction_id VARCHAR(255) UNIQUE,
  idempotency_key VARCHAR(255) UNIQUE,  -- ← CRITICAL!
  status VARCHAR(20)  -- PENDING, SUCCESS, FAILED
);
```

**Key Design Decisions:**
- UUID for booking_id (security, idempotency)
- Composite PK (show_id, seat_id) for seat_availability
- Denormalize available_seats (avoid COUNT query)
- expires_at index (for cleanup job every 5 mins)

---

## 💰 Cost Breakdown (Quick)

```
MONTHLY COST ESTIMATE
═══════════════════════════════════════════════════════════
Servers: 260 × $248 = $64,480
Database: 10 shards × $2,920 = $29,200
Cache: 20 Redis × $120 = $2,400
Load Balancers: $337
CDN: $2,700
Network: $31,050
──────────────────────────────────────────────────────────
TOTAL: ~$130,000/month = $1.56M/year

Cost per booking: $1.56M ÷ (500k × 365) = $0.0085

OPTIMIZATION
═══════════════════════════════════════════════════════════
- Use spot instances (70% savings)
- Cache aggressively (reduce DB load)
- CDN for static assets (reduce bandwidth)
- Auto-scale (only pay for peak when needed)
```

---

## 🚨 Common Pitfalls (Avoid These!)

```
❌ DON'T SAY                      ✅ SAY INSTEAD
═══════════════════════════════════════════════════════════
"I'll use a mutex"               "Row-level lock with FOR UPDATE"
"Add more servers"               "Here's the capacity calculation..."
"Use SERIALIZABLE"               "READ_COMMITTED + FOR UPDATE suffices"
"Just cache everything"          "Cache with 30s TTL, here's why..."
"MongoDB for everything"         "PostgreSQL for bookings (ACID needed)"
"Microservices!"                 "Start monolith, extract services later"
"NoSQL is web-scale"             "ACID guarantees critical for booking"
"Eventual consistency is fine"   "For search yes, for booking no"
```

---

## 🎯 Trade-Off Matrix (Memorize This!)

```
┌────────────────────┬─────────────────┬──────────────────┐
│   Approach         │      Pros       │      Cons        │
├────────────────────┼─────────────────┼──────────────────┤
│ Pessimistic Lock   │ Simple, safe    │ Lower throughput │
│ Optimistic Lock    │ High throughput │ Many retries     │
│ Denormalization    │ Fast reads      │ Consistency risk │
│ Microservices      │ Independent     │ Complexity       │
│ Monolith           │ Simple          │ Hard to scale    │
│ Sharding           │ Horizontal scale│ Complex queries  │
│ Read Replicas      │ Scale reads     │ Replication lag  │
│ Cache              │ Fast            │ Staleness       │
│ Queue              │ Decouple        │ Async delay      │
└────────────────────┴─────────────────┴──────────────────┘
```

---

## ⚡ Quick Formulas

```
SERVERS NEEDED
═══════════════════════════════════════════════════════════
servers = (target_qps ÷ capacity_per_server) × safety_factor
Example: (10,000 ÷ 200) × 1.5 = 75 servers

DATABASE SHARDS
═══════════════════════════════════════════════════════════
shards = (peak_writes_per_sec ÷ writes_per_shard) × safety
Example: (5,000 ÷ 500) × 1.5 = 15 shards

CACHE SIZE
═══════════════════════════════════════════════════════════
size_gb = (total_entries × size_per_entry × overhead) ÷ 1GB
Example: (50k shows × 25KB × 1.5) ÷ 1GB = 1.9 GB

BANDWIDTH
═══════════════════════════════════════════════════════════
bandwidth = requests × avg_response_size
Example: 300M × 50KB = 15 TB/day
```

---

## 🎓 Interview Pro Tips

### **Phase 1: Requirements (10 min)**
```
✓ Ask about scale (DAU, concurrent, QPS)
✓ Clarify consistency requirements
✓ Estimate capacity (show math on whiteboard)
✓ Define scope (what's in/out)
```

### **Phase 2: High-Level (15 min)**
```
✓ Draw components (API Gateway, Services, DBs, Cache)
✓ Explain each component's purpose
✓ Show data flow
✓ Design 3-4 key APIs
```

### **Phase 3: Deep Dive (25 min)**
```
✓ Focus on critical path (seat booking)
✓ Handle race conditions (FOR UPDATE)
✓ Payment atomicity (3-phase commit)
✓ Scaling strategy (sharding, caching)
```

### **Phase 4: Wrap-up (10 min)**
```
✓ Identify bottlenecks
✓ Discuss trade-offs
✓ Monitoring & operations
✓ Ask smart questions
```

---

## 🔥 Power Phrases

Use these to impress:

```
"Let me clarify requirements before designing..."
"Here's my capacity estimation..."
"The critical path is seat booking, where..."
"For consistency, I'd use READ_COMMITTED with FOR UPDATE because..."
"The trade-off here is X vs Y, and here's why I chose X..."
"For peak load, I'd implement a load shedding strategy..."
"We'd monitor these key metrics..."
"One optimization would be to..."
"A potential bottleneck is X, which we'd address by..."
"In production, I'd add observability for..."
```

---

## 📝 Final Checklist

Before walking into interview:

```
□ Memorized core numbers (DAU, QPS, storage)
□ Can draw architecture in 5 minutes
□ Explain double-booking solution (FOR UPDATE)
□ Explain payment atomicity (3-phase commit)
□ Know database choices (PostgreSQL, MySQL, ES)
□ Can calculate servers needed (formula)
□ Understand sharding strategy (by city_id)
□ Know caching approach (Redis, 30s TTL)
□ Can discuss peak load (load shedding)
□ Prepared monitoring metrics

8-10 checks: You're ready! 🎯
5-7 checks: Review critical topics
<5 checks: Study more, not ready yet
```

---

## 🚀 Post-Interview

If you get stuck:
- ✅ "Let me think about this for a moment..."
- ✅ "I'm not familiar with X, but here's how I'd approach it..."
- ✅ "Can you give me a hint on X?"

If you don't know:
- ✅ "I haven't used X in production, but conceptually..."
- ✅ "I'd research X approaches and evaluate trade-offs..."
- ❌ Don't make things up!

---

**Remember:** Interviewers want to see:
1. Structured thinking
2. Trade-off analysis
3. Scale understanding
4. Production awareness
5. Communication skills

You got this! 💪🎯
