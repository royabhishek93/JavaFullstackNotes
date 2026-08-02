# Parking Lot System - Complete Interview Guide
**Comprehensive guide with diagrams, explanations, and cross-questions**

**Print Settings:** Landscape mode, monospace font (Courier New/Consolas 9-10pt), narrow margins

---

## SECTION 1: REQUIREMENTS & CAPACITY ESTIMATION

### 1.1 Functional Requirements

```
✓ Multi-location parking management (100+ facilities)
✓ Real-time availability tracking (<1s latency)
✓ Advance booking (up to 24 hours)
✓ Payment processing (multiple methods)
✓ Mobile app integration (iOS/Android)
✓ Dynamic pricing (surge pricing)
✓ Entry/Exit management (automated gates)
✗ Valet parking (out of scope)
✗ EV charging stations (out of scope)
```

**How to Present:**
"Before diving into the design, let me clarify the requirements. I'll focus on:
- Managing multiple parking facilities across different locations
- Real-time availability updates - users should know which spots are free
- Booking system where users can reserve spots in advance
- Payment integration for seamless transactions
- Mobile-first approach since most users will book via phone
- Dynamic pricing during peak hours to optimize revenue

I'll keep valet services and EV charging out of scope for now."

### 1.2 Non-Functional Requirements

```
Scale:        1M users, 200K DAU, 100K daily bookings
Latency:      <200ms API response, <1s availability updates
Availability: 99.9% uptime (8.76 hours downtime/year)
Consistency:  Strong for bookings (no double-booking)
Security:     PCI-DSS compliant, encrypted data
```

**How to Explain:**
"From a non-functional perspective, I'm assuming:
- **Scale**: 1 million registered users, 200K active daily
- **Performance**: API responses under 200ms, availability updates within 1 second
- **Availability**: 99.9% uptime - we can afford about 8 hours of downtime per year
- **Consistency**: Strong consistency for bookings is critical - we cannot double-book a spot
- **Security**: Payment data must be PCI-DSS compliant with end-to-end encryption"

### 1.3 Capacity Estimation

```
TRAFFIC:
- DAU: 200,000 users
- Average bookings/user/day: 0.5
- Daily bookings: 100,000
- Peak hours (8-10 AM, 5-7 PM): 3x traffic
- RPS Average: 100 requests/sec
- RPS Peak: 300 requests/sec
- Read:Write ratio: 10:1

STORAGE:
- Users: 1M × 1KB = 1 GB
- Parking lots: 100 × 100KB = 10 MB
- Spots: 100 lots × 500 spots × 500B = 25 MB
- Bookings: 100K/day × 365 × 2KB = 73 GB/year
- Payment records: 100K/day × 365 × 1KB = 36.5 GB/year
- 5 years total: ~500 GB

BANDWIDTH:
- Incoming: 100 RPS × 2KB = 200 KB/sec
- Outgoing: 1000 RPS × 5KB = 5 MB/sec
```

**How to Walk Through:**
"Let me do quick calculations:

**Traffic:**
- 200K daily active users, each checking availability 2-3 times
- That's about 400-600K read requests per day
- Write operations (bookings): 100K per day
- Spread over 12 active hours = ~2.3 requests per second average
- But during peak hours (morning and evening rush), we see 3x traffic
- So we need to handle 300 requests per second at peak

**Storage:**
- User data is minimal: 1KB per user = 1GB total
- Parking lot metadata: 100 facilities = 10MB
- The heavy part is booking history
- 100K bookings per day × 365 days = 36.5M bookings per year
- At 2KB per booking record, that's 73GB per year
- Over 5 years: about 365GB just for bookings
- Total system storage: approximately 500GB"

**CROSS-QUESTIONS & ANSWERS:**

**Q1: Why 500 spots per parking lot? Isn't that too many?**
"Good question! Let me clarify:
- **Small lots** (street parking, small buildings): 50-100 spots
- **Medium lots** (shopping malls, offices): 200-500 spots
- **Large lots** (airports, stadiums): 1000-5000 spots

I used 500 as an average across all types. In reality, we'd have:
- 60% small lots: 60 × 75 spots = 4,500 spots
- 30% medium lots: 30 × 350 spots = 10,500 spots
- 10% large lots: 10 × 2000 spots = 20,000 spots
- **Total: ~35,000 spots** across 100 locations

This affects our real-time tracking requirements - we need to update 35K spot statuses efficiently."

**Q2: 99.9% availability seems low for a booking system. Why not 99.99%?**
"Excellent observation. Let me explain the trade-off:

**99.9% (3 nines):**
- Downtime: 8.76 hours/year = 43 minutes/month
- Cost: Moderate (standard redundancy)
- Acceptable for parking (not life-critical)

**99.99% (4 nines):**
- Downtime: 52 minutes/year = 4.3 minutes/month
- Cost: 3-4x higher (multi-region, more replicas)
- Needed for: Banks, hospitals, emergency services

**Why 99.9% is sufficient:**
- Parking isn't life-critical - if system is down for 30 minutes at 3 AM, minimal impact
- Users can fallback to walk-in parking
- Planned maintenance during low-traffic hours (2-5 AM)
- Cost savings can be invested in features

**However**, for critical operations (active bookings, ongoing parking sessions), we maintain **99.99%** availability through:
- Multiple availability zones
- Database replicas
- Graceful degradation (read-only mode during issues)

So we have **tiered availability**: 
- Browse and search: 99.9%
- Active sessions: 99.99%"

**Q3: Why strong consistency for bookings? Won't that hurt performance?**
"This is a critical design decision. Let me explain why strong consistency is non-negotiable:

**Scenario with Eventual Consistency:**
```
10:00:00 - User A books Spot 101 → Writes to DB Master
10:00:01 - User B checks availability → Reads from Replica (not yet replicated)
10:00:01 - User B sees Spot 101 as available (stale data)
10:00:02 - User B books Spot 101 → DOUBLE BOOKING!
```

**Impact:**
- Two users arrive at same spot
- Conflict, one user is turned away
- Terrible user experience, refunds, complaints
- Potential revenue loss

**Solution: Strong Consistency**
```
All booking reads go to Master database
OR
Use distributed locks (Redis) to prevent concurrent bookings
```

**Performance Trade-off:**
- Eventual consistency: 5ms read latency (from replica)
- Strong consistency: 20ms read latency (from master)
- **Extra 15ms is acceptable** to prevent double-booking

**What we CAN use eventual consistency for:**
- Parking lot search results (slightly stale is OK)
- Historical analytics
- User profiles
- Payment history

So we use **hybrid consistency**:
- Critical path (booking): Strong
- Non-critical (browse): Eventual"

---

## SECTION 2: HIGH-LEVEL ARCHITECTURE

### 2.1 System Architecture Diagram

```
┌────────────────────────────────────────────────────────┐
│                   USERS                                 │
│         Mobile App    Web Portal    Kiosk              │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS
                       ↓
┌──────────────────────────────────────────────────────────┐
│               CDN (Static Assets)                        │
│  - Images, JS, CSS cached at edge                       │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────┐
│          Load Balancer (ALB)                             │
│  - SSL Termination                                       │
│  - Health Checks                                         │
│  - Sticky Sessions for WebSocket                        │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────┐
│            API Gateway (Kong / AWS API Gateway)          │
│  - Authentication (JWT validation)                       │
│  - Rate Limiting (100 req/min per user)                 │
│  - Request Logging                                       │
│  - API Versioning (/v1/, /v2/)                          │
└───────────────┬──────────────────────────────────────────┘
                │
    ┌───────────┼───────────┬──────────────┐
    │           │           │              │
    ▼           ▼           ▼              ▼
┌────────┐  ┌────────┐  ┌────────┐  ┌──────────┐
│Booking │  │ Search │  │Payment │  │Analytics │
│Service │  │Service │  │Service │  │ Service  │
│        │  │        │  │        │  │          │
└───┬────┘  └───┬────┘  └───┬────┘  └────┬─────┘
    │           │           │            │
    │           │           │            │
    ▼           ▼           ▼            ▼
┌────────────────────────────────────────────────┐
│           CACHING LAYER (Redis Cluster)        │
│  - Available spots cache (TTL: 5s)             │
│  - User sessions (TTL: 30min)                  │
│  - Booking locks (TTL: 2min)                   │
└────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────┐
│      MESSAGE QUEUE (Kafka)                     │
│  Topics:                                       │
│  - booking-events                              │
│  - payment-events                              │
│  - spot-availability-updates                   │
└────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────┐
│         DATABASE LAYER                         │
│                                                │
│  ┌──────────────┐      ┌─────────────────┐   │
│  │ PostgreSQL   │      │ Elasticsearch   │   │
│  │              │      │                 │   │
│  │ Master +     │      │ - Parking lot   │   │
│  │ 2 Replicas   │      │   search index  │   │
│  │              │      │ - Fuzzy search  │   │
│  │ Tables:      │      └─────────────────┘   │
│  │ - users      │                             │
│  │ - parking_lots│      ┌─────────────────┐  │
│  │ - spots      │      │ MongoDB         │   │
│  │ - bookings   │      │                 │   │
│  │ - payments   │      │ - Event logs    │   │
│  └──────────────┘      │ - Analytics data│   │
│                        └─────────────────┘   │
└────────────────────────────────────────────────┘
```

### 2.2 How to Draw & Explain

**Drawing Strategy (Step-by-Step):**

"Let me draw the architecture from top to bottom:

**Step 1 - User Layer:**
'Users access the system through multiple channels:
- Mobile apps (iOS/Android) for on-the-go booking
- Web portal for advanced features and management
- Physical kiosks at parking lot entrance/exit
All communication is over HTTPS for security.'

**Step 2 - CDN Layer:**
'Static assets (images, JavaScript, CSS) are served from CDN edge locations:
- Reduces latency for mobile app assets
- Offloads traffic from our servers
- Especially important for parking lot photos and maps'

**Step 3 - Load Balancer:**
'ALB (Application Load Balancer) handles:
- SSL certificate termination
- Health checks on backend services
- Sticky sessions for WebSocket connections (real-time updates)
- Distributes traffic across API Gateway instances'

**Step 4 - API Gateway:**
'This is our single entry point for all APIs:
- **Authentication**: Validates JWT tokens before requests reach services
- **Rate Limiting**: 100 requests per minute per user to prevent abuse
- **Logging**: All API calls logged for debugging and analytics
- **Versioning**: Supports /v1/ and /v2/ for backward compatibility'

**Step 5 - Microservices:**
'I'm using microservices because each has different characteristics:

**Booking Service:**
- Handles spot reservations
- Requires strong consistency
- Write-heavy during peak hours
- Needs to scale independently

**Search Service:**
- Full-text search for parking lots
- Read-only operations
- Can use Elasticsearch for complex queries
- Different scaling requirements

**Payment Service:**
- Integrates with Stripe/PayPal
- PCI-DSS compliance requirements
- Isolated for security
- Can be swapped without affecting other services

**Analytics Service:**
- Background processing of metrics
- Low priority, can handle delays
- Uses separate database (MongoDB) for time-series data'

**Step 6 - Caching Layer (Redis):**
'Redis is critical for performance:
- **Available spots cache**: Updated every 5 seconds, TTL 5s
- **User sessions**: JWT token data, TTL 30 minutes
- **Booking locks**: Prevent double-booking, TTL 2 minutes

This reduces database load by 90% - most reads hit cache.'

**Step 7 - Message Queue (Kafka):**
'Kafka decouples services asynchronously:
- **booking-events**: Notify analytics when booking is made
- **payment-events**: Trigger email receipts, update accounting
- **spot-availability-updates**: Fan out to all connected clients

If payment service is down, events queue up and process later - system is resilient.'

**Step 8 - Database Layer:**
'Three databases for different use cases:

**PostgreSQL:**
- ACID transactions for bookings (critical)
- Master-slave replication (1 master + 2 read replicas)
- Handles: users, parking_lots, spots, bookings, payments

**Elasticsearch:**
- Fast full-text search for parking lots
- Geospatial queries (find parking near me)
- Fuzzy search (typo-tolerant)

**MongoDB:**
- Event logs (high write throughput)
- Analytics data (time-series)
- Schema flexibility for evolving metrics'"

---

## SECTION 3: DATABASE DESIGN

### 3.1 Entity Relationship Diagram

```
┌──────────────────┐
│     USERS        │
├──────────────────┤
│ PK id            │◄─────────────┐
│    email (unique)│              │
│    phone         │              │ 1
│    password_hash │              │
│    created_at    │              │
└──────┬───────────┘              │
       │ 1                        │
       │                          │
       │ *                        │
┌──────▼───────────┐              │
│   BOOKINGS       │              │
├──────────────────┤              │
│ PK id            │              │
│ FK user_id       │──────────────┘
│ FK spot_id       │─────────┐
│ FK payment_id    │         │
│    start_time    │         │
│    end_time      │         │
│    status (ENUM) │         │
│    total_amount  │         │
│    created_at    │         │
└──────────────────┘         │
                             │
┌──────────────────┐         │
│  PARKING_LOTS    │         │
├──────────────────┤         │
│ PK id            │◄────┐   │
│    name          │     │   │
│    address       │     │   │
│    latitude      │     │ 1 │
│    longitude     │     │   │
│    total_spots   │     │   │
│    hourly_rate   │     │   │
│    is_active     │     │   │
│    created_at    │     │   │
└──────────────────┘     │   │
                         │   │
┌──────────────────┐     │   │
│  PARKING_SPOTS   │     │   │
├──────────────────┤     │   │
│ PK id            │─────┘   │
│ FK parking_lot_id│         │
│    spot_number   │         │
│    spot_type     │         │ *
│    is_available  │◄────────┘
│    floor_level   │
│    created_at    │
└──────────────────┘

┌──────────────────┐
│    PAYMENTS      │
├──────────────────┤
│ PK id            │
│ FK booking_id    │
│    amount        │
│    payment_method│
│    transaction_id│
│    status (ENUM) │
│    paid_at       │
└──────────────────┘
```

### 3.2 Table Design Explanation

**USERS Table:**
```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
```

**PARKING_LOTS Table:**
```sql
CREATE TABLE parking_lots (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    total_spots INTEGER NOT NULL,
    hourly_rate DECIMAL(10, 2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Geospatial index for "parking near me" queries
CREATE INDEX idx_parking_lots_location ON parking_lots 
    USING GIST (ST_MakePoint(longitude, latitude));

CREATE INDEX idx_parking_lots_active ON parking_lots(is_active);
```

**PARKING_SPOTS Table:**
```sql
CREATE TABLE parking_spots (
    id BIGSERIAL PRIMARY KEY,
    parking_lot_id BIGINT NOT NULL REFERENCES parking_lots(id),
    spot_number VARCHAR(10) NOT NULL,
    spot_type VARCHAR(20) NOT NULL, -- COMPACT, REGULAR, LARGE, HANDICAP
    is_available BOOLEAN DEFAULT TRUE,
    floor_level INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(parking_lot_id, spot_number)
);

CREATE INDEX idx_spots_lot_available ON parking_spots(parking_lot_id, is_available);
CREATE INDEX idx_spots_available ON parking_spots(is_available) WHERE is_available = TRUE;
```

**BOOKINGS Table:**
```sql
CREATE TABLE bookings (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    spot_id BIGINT NOT NULL REFERENCES parking_spots(id),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL, -- PENDING, CONFIRMED, ACTIVE, COMPLETED, CANCELLED
    total_amount DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Prevent overlapping bookings for same spot
    CONSTRAINT no_overlap EXCLUDE USING GIST (
        spot_id WITH =,
        tsrange(start_time, end_time) WITH &&
    )
);

CREATE INDEX idx_bookings_user ON bookings(user_id, created_at DESC);
CREATE INDEX idx_bookings_spot ON bookings(spot_id, start_time);
CREATE INDEX idx_bookings_status ON bookings(status) WHERE status IN ('ACTIVE', 'CONFIRMED');
```

**PAYMENTS Table:**
```sql
CREATE TABLE payments (
    id BIGSERIAL PRIMARY KEY,
    booking_id BIGINT NOT NULL REFERENCES bookings(id),
    amount DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL, -- CREDIT_CARD, DEBIT_CARD, UPI, WALLET
    transaction_id VARCHAR(255) UNIQUE,
    status VARCHAR(20) NOT NULL, -- PENDING, SUCCESS, FAILED, REFUNDED
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_payments_booking ON payments(booking_id);
CREATE INDEX idx_payments_transaction ON payments(transaction_id);
```

### 3.3 Critical Design Points

**1. Preventing Double Bookings:**
```sql
-- PostgreSQL EXCLUDE constraint prevents overlapping time ranges
CONSTRAINT no_overlap EXCLUDE USING GIST (
    spot_id WITH =,
    tsrange(start_time, end_time) WITH &&
)
```

**2. Finding Available Spots:**
```sql
-- Fast query for available spots in a parking lot
SELECT s.* 
FROM parking_spots s
WHERE s.parking_lot_id = 123
  AND s.is_available = TRUE
  AND NOT EXISTS (
      SELECT 1 FROM bookings b
      WHERE b.spot_id = s.id
        AND b.status IN ('CONFIRMED', 'ACTIVE')
        AND tsrange(b.start_time, b.end_time) && 
            tsrange('2024-01-01 10:00', '2024-01-01 12:00')
  );
```

**3. Geospatial Search:**
```sql
-- Find parking lots within 5km radius
SELECT *
FROM parking_lots
WHERE ST_DWithin(
    ST_MakePoint(longitude, latitude)::geography,
    ST_MakePoint(77.5946, 12.9716)::geography,  -- User's location
    5000  -- 5km in meters
)
AND is_active = TRUE
ORDER BY ST_Distance(
    ST_MakePoint(longitude, latitude)::geography,
    ST_MakePoint(77.5946, 12.9716)::geography
) ASC
LIMIT 10;
```

**CROSS-QUESTIONS & ANSWERS:**

**Q1: The EXCLUDE constraint for preventing double bookings - what if there's high concurrency?**
"Excellent question about the race condition! Let me explain the complete solution:

**Database-Level Protection (First Line):**
```sql
CONSTRAINT no_overlap EXCLUDE USING GIST (
    spot_id WITH =,
    tsrange(start_time, end_time) WITH &&
)
```
This prevents overlapping bookings at the database level, but it throws an error on conflict.

**Application-Level Protection (Better UX):**
```python
def book_spot(user_id, spot_id, start_time, end_time):
    # Step 1: Acquire distributed lock
    lock_key = f"booking_lock:spot:{spot_id}"
    lock = redis.set(lock_key, user_id, nx=True, ex=120)  # 2 minute TTL
    
    if not lock:
        return {"error": "Spot is being booked by someone else, try again"}
    
    try:
        # Step 2: Check availability (with lock held)
        existing = db.query("""
            SELECT id FROM bookings 
            WHERE spot_id = %s 
              AND status IN ('CONFIRMED', 'ACTIVE')
              AND tsrange(start_time, end_time) && tsrange(%s, %s)
        """, spot_id, start_time, end_time)
        
        if existing:
            return {"error": "Spot is already booked"}
        
        # Step 3: Create booking
        booking = db.insert("bookings", {
            "user_id": user_id,
            "spot_id": spot_id,
            "start_time": start_time,
            "end_time": end_time,
            "status": "PENDING"
        })
        
        return {"success": True, "booking_id": booking.id}
    
    finally:
        # Step 4: Release lock
        redis.delete(lock_key)
```

**Why This Works:**
- **Redis lock**: Only one request can proceed at a time for the same spot
- **Database constraint**: Backup protection if lock fails
- **Short lock timeout**: If process crashes, lock expires in 2 minutes
- **Grace period**: User has 2 minutes to complete payment

**Performance:**
- Lock acquisition: 5ms (Redis)
- Availability check: 10ms (PostgreSQL with index)
- Booking insert: 15ms
- **Total: ~30ms** - acceptable for booking operation"

**Q2: Won't the geospatial query be slow with millions of parking lots?**
"Great performance concern! Let me show you the optimization:

**Without Optimization (Slow):**
```sql
-- Scans ALL parking lots, calculates distance for each
SELECT *, ST_Distance(...) as distance
FROM parking_lots
ORDER BY distance
LIMIT 10;
-- Execution time: 5000ms for 1M rows
```

**With GIST Index (Fast):**
```sql
-- Uses spatial index, only checks nearby bounding box
SELECT *
FROM parking_lots
WHERE ST_DWithin(
    ST_MakePoint(longitude, latitude)::geography,
    ST_MakePoint(77.5946, 12.9716)::geography,
    5000  -- 5km radius
)
ORDER BY ST_Distance(...) ASC
LIMIT 10;
-- Execution time: 20ms for 1M rows!
```

**How GIST Index Works:**
```
Spatial Index (GIST):
┌─────────────────────────┐
│       Whole City        │
│   (1M parking lots)     │
└───────────┬─────────────┘
            │
     ┌──────┴──────┐
     │             │
┌────▼───┐    ┌───▼────┐
│ North  │    │ South  │
│ 500K   │    │ 500K   │
└────┬───┘    └────────┘
     │
 ┌───┴───┐
 │       │
┌▼─┐   ┌─▼┐
│NW│   │NE│
│10K   │15K  <- User is in NE quadrant
└──┘   └──┘

Only scan 15K lots in NE quadrant, not all 1M!
```

**Additional Optimization: Caching**
```python
# Cache nearby parking lots for 5 minutes
cache_key = f"nearby_lots:{lat}:{lng}:5km"
cached = redis.get(cache_key)

if cached:
    return json.loads(cached)  # 5ms response

lots = db.query(geospatial_query)
redis.setex(cache_key, 300, json.dumps(lots))  # Cache for 5 min
return lots
```

**Result:**
- First request: 20ms (database with GIST index)
- Subsequent requests: 5ms (Redis cache)
- 99% of requests hit cache"

---

*[Document continues with Section 4: Booking Flow, Section 5: Real-time Updates, Section 6: Scalability, Section 7: Interview Questions, etc.]*

---

**END OF PARKING LOT SYSTEM GUIDE**
