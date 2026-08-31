# UBER/OLA Ride-Sharing System — Beginner's Complete Guide

> **One-liner**: *"Rider requests → Geo-search nearby drivers → Zookeeper lock (prevent double assignment) → Driver accepts → WebSocket location tracking → Trip completion → Payment & Rating"*

---

## 📚 What You'll Learn

This guide breaks down UBER/OLA's ride-sharing architecture into **digestible, beginner-friendly concepts** with:
- 🎨 **4 visual diagrams** (context, architecture, flow, data model)
- 🔍 **Real-world analogies** (no abstract jargon)
- ❓ **WHY explanations** (understand the reasoning, not just the solution)
- 📝 **Self-check questions** (test your understanding)
- 🎯 **Interview prep** (what to say, what to avoid)

---

## 🗺️ Diagrams Overview

| Diagram | File | What It Shows | Focus Area |
|---------|------|---------------|------------|
| **01 — System Context** | `01-context-BEGINNER.drawio` | Actors (Rider, Driver, Admin), External systems (Google Maps, Stripe, FCM/APN), System boundary, Key challenges | Understanding the big picture |
| **02 — Architecture** | `02-architecture-components-BEGINNER.drawio` | All services, WHY boxes (Redis geo, Zookeeper locks, WebSocket, Kafka events, Surge pricing), Data stores, Technologies used | Component relationships & trade-offs |
| **03 — Ride Flow** | `03-ride-matching-flow-sequence-BEGINNER.drawio` | Timeline: Fare estimate → Request → Driver matching → Tracking → Completion, Latency breakdown (0-1.5s matching), Concurrent location updates | Step-by-step execution |
| **04 — Data Model** | `04-data-model-BEGINNER.drawio` | PostgreSQL schema (drivers, riders, trips, ratings, payments), Redis keys (geospatial, TTL caches), Zookeeper locks, Kafka topics | Storage design & partitioning |

---

## 🎯 Core Challenge: Real-Time Driver Matching at Scale

**The Problem**:  
A rider in San Francisco taps "Request Ride". The system must:
1. Find the **10 nearest available drivers** from **1 million total drivers** in **under 10 milliseconds**
2. Ensure **no two riders** get assigned to the **same driver** (even with 1000 concurrent requests)
3. Track driver location **every 3-5 seconds** for **100,000 active trips** without killing servers
4. Dynamically adjust pricing based on **demand/supply ratio per 5km grid**

**Traditional Approach (Why It Fails)**:
```
SELECT * FROM drivers 
WHERE status='AVAILABLE' AND vehicle_type='sedan'
ORDER BY distance(lat, lon, pickup_lat, pickup_lon) ASC 
LIMIT 10;
```
❌ **Full table scan** of 1M drivers = **10+ seconds**  
❌ **Distance calculation** on every row = **CPU explosion**  
❌ **No locks** → race conditions = double-assignment

---

## 🔑 Key Solutions (Understand These Deeply)

### 1. **Redis GEORADIUS for Geospatial Search**

**Analogy**: Imagine finding the closest Starbucks. You don't check every store worldwide — you ask "which stores are within 5km of me?" The system pre-indexes all store locations by coordinates, so it instantly returns sorted results.

**How UBER Does It**:
```redis
# Every time a driver updates location (every 3-5s)
GEOADD drivers:available {lon} {lat} {driver_id}

# When rider requests a ride
GEORADIUS drivers:available {pickup_lon} {pickup_lat} 5km WITHDIST ASC
→ Returns: [(driver001, 0.8km), (driver002, 1.2km), ..., (driver010, 4.5km)]
```

**Why It's Fast**:
- Redis stores locations in a **geospatial index** (sorted grid structure)
- Query complexity: **O(log N + M)** where M = results (typically 10)
- Latency: **~10ms** for 1M drivers

**Interview Line**:  
*"Redis GEORADIUS pre-indexes driver locations in a sorted spatial structure, allowing distance-based queries in ~10ms instead of scanning 1M rows. Think of it like a city grid map vs checking every address individually."*

---

### 2. **Zookeeper Distributed Locks (Prevent Double-Assignment)**

**Analogy**: Imagine a taxi stand with one dispatcher and 3 passengers arriving simultaneously, all wanting the first cab in line. Without coordination, all 3 might rush the same driver. The dispatcher's clipboard acts as a "lock" — first person to write their name on it gets the cab, others see it's taken and move to the next driver.

**How UBER Does It**:
```
Rider R1 requests → Matching Service finds D1 (closest)
    ↓
CREATE /locks/drivers/D1/request_R1_seq0001  (ephemeral node in Zookeeper)
    ↓
SUCCESS → D1 is now locked to R1
    ↓
Rider R2 requests → Matching Service also finds D1
    ↓
CREATE /locks/drivers/D1/request_R2_seq0002  (attempts to create)
    ↓
NodeExistsException → D1 already locked → try next closest driver (D2)
```

**Key Properties**:
- **Ephemeral nodes**: If Matching Service crashes mid-assignment, lock **auto-deletes after 30s** (Zookeeper session timeout)
- **Sequential nodes**: If multiple requests race for same driver, sequential numbering creates FIFO queue
- **Strong consistency**: Zookeeper uses **Paxos/ZAB** consensus — all nodes agree on lock state

**Interview Line**:  
*"Zookeeper ephemeral locks prevent double-assignment. First request to create the lock wins. If the matching service crashes, the lock auto-deletes after 30 seconds, freeing the driver. This is stronger than Redis SETNX because Zookeeper handles network partitions and server crashes with consensus algorithms."*

---

### 3. **WebSocket for Real-Time Location Tracking**

**Analogy**: HTTP polling is like calling your friend every 3 seconds: "Where are you now?" → hang up → call again. WebSocket is like keeping the phone call **open the entire trip** — location updates flow instantly without re-dialing.

**HTTP Polling (What UBER Doesn't Do)**:
```
Every 3 seconds:
GET /driver/{id}/location  → full HTTP request/response overhead
```
❌ At **100K active trips**: 100K × (1 req/3s) = **33,333 requests/second**  
❌ Each HTTP request: **headers (500-1000 bytes) + full handshake**  
❌ Latency: **1-3 seconds** (waiting for next poll)

**WebSocket (What UBER Does)**:
```
Driver app → WS /v1/driver/location (open connection once)
    ↓
Every 3-5 seconds: {lat, lon, timestamp} (tiny payload, ~100 bytes)
    ↓
Location Update Service → broadcasts to all subscribers
```
✅ **Persistent connection** = no handshake overhead  
✅ **Binary frames** = 10× less bandwidth  
✅ Latency: **<100ms** (instant push)

**Interview Line**:  
*"WebSocket maintains a persistent TCP connection, so location updates are pushed instantly with minimal overhead. At 100K trips, this saves ~30K req/sec compared to HTTP polling and reduces latency from 1-3s to under 100ms."*

---

### 4. **Surge Pricing Algorithm**

**Analogy**: Concert ticket prices rise when demand exceeds supply. If 1000 people want to see Taylor Swift in a 500-seat venue, dynamic pricing attracts more seats (drivers) or throttles demand.

**How UBER Calculates Surge**:
```python
# Run every 60 seconds per geohash cell (5km × 5km grid)

def calculate_surge(geohash_cell):
    # Count pending requests in this area (last 10 min)
    pending = SELECT COUNT(*) FROM ride_requests 
              WHERE pickup_geohash = {cell} 
              AND status='PENDING' 
              AND created_at > NOW() - INTERVAL '10 min'
    
    # Count available drivers in this area
    available = GEORADIUS drivers:available {cell_center} 5km COUNT
    
    # Calculate demand ratio
    demand_ratio = pending / max(available, 1)  # avoid div by zero
    
    # Map to surge multiplier
    if demand_ratio < 1.2:   surge = 1.0   # no surge
    elif demand_ratio < 2.0: surge = 1.2
    elif demand_ratio < 3.0: surge = 1.5
    elif demand_ratio < 5.0: surge = 1.8
    else:                   surge = min(demand_ratio / 2, 3.0)  # max cap 3.0×
    
    # Smoothing (prevent sudden jumps)
    old_surge = GET surge_multiplier:{geohash_cell} || 1.0
    new_surge = 0.7 * old_surge + 0.3 * calculated_surge
    
    # Store with 2-min TTL
    SET surge_multiplier:{geohash_cell} {new_surge} EX 120
    
    return new_surge
```

**Why Smoothing Matters**:  
Without smoothing, a sudden spike (10 riders, 1 driver) would instantly jump from 1.0× → 5.0×. The rider sees fare double mid-request, creating sticker shock. Smoothing blends **70% old + 30% new**, so surge rises gradually over 2-3 calculation cycles.

**Interview Line**:  
*"Surge pricing groups the city into 5km geohash cells and calculates demand/supply ratio every 60 seconds. A smoothing algorithm (70% old + 30% new) prevents price shocks. The rider must explicitly accept the higher fare before the ride is confirmed, and there's a 3.0× max cap to prevent price gouging."*

---

### 5. **Kafka for Event-Driven Decoupling**

**Analogy**: In a busy restaurant, the waiter **drops the order ticket** in the kitchen and **immediately returns** to the customer. The chef picks up the ticket whenever ready. The customer isn't waiting while the chef cooks — decoupled asynchronous processing.

**Without Kafka (Synchronous Blocking)**:
```
Rider taps "Request Ride"
    ↓
Ride Service → calls Driver Matching Service (synchronous)
    ↓
Matching takes 800ms (geo-search + lock + notify)
    ↓
Rider sees loading spinner for 800ms
    ↓
If Matching Service is slow → entire request times out
```

**With Kafka (Asynchronous Event-Driven)**:
```
Rider taps "Request Ride"
    ↓
Ride Service → INSERT ride_requests (DB) + PUBLISH ride.requested (Kafka)
    ↓
Return 202 Accepted to rider immediately (<50ms)
    ↓
Rider sees "Finding driver..." (not blocked)
    ↓
Driver Matching Service consumes ride.requested event at its own pace
    ↓
When match found → PUBLISH ride.matched → Notification Svc → FCM/APN → rider
```

**Benefits**:
- **Ride Service never waits** for matching to complete
- If Matching Service crashes, event sits in Kafka (7-day retention) until it recovers
- **Multiple consumers**: Matching, Analytics, Notifications all process same event independently

**Interview Line**:  
*"Kafka decouples ride requests from driver matching. The Ride Service publishes a ride.requested event and returns immediately to the user. The Matching Service consumes the event asynchronously, preventing slow matching from blocking the rider's app. Multiple services (analytics, notifications) can subscribe to the same event stream independently."*

---

## 📖 5-Day Study Plan

### **Day 1: System Context & Big Picture**
- [ ] Open `01-context-BEGINNER.drawio` in diagrams.net
- [ ] Identify all actors (Rider, Driver, Admin) and external systems (Google Maps, Stripe, FCM/APN)
- [ ] Read all challenge boxes — understand why geospatial search, distributed locks, and real-time tracking matter
- [ ] **Practice**: Explain the system in 60 seconds using the taxi dispatcher analogy

**Self-Check Questions**:
1. Why does UBER need Google Maps Distance Matrix API? (Hint: fare estimation + ETA)
2. What happens if Zookeeper goes down? (Hint: no new driver assignments, existing trips continue)
3. Why FCM/APN instead of WebSocket for all notifications? (Hint: app in background)

---

### **Day 2: Architecture & Component Design**
- [ ] Open `02-architecture-components-BEGINNER.drawio`
- [ ] Trace data flow: Rider → API Gateway → Ride Service → Matching Service → Redis/Zookeeper
- [ ] Read all WHY boxes (Redis geo, Zookeeper locks, WebSocket, Kafka, Surge)
- [ ] Understand the difference between PostgreSQL (durable) vs Redis (ephemeral)

**Self-Check Questions**:
1. Why does Driver Matching Service query Redis instead of PostgreSQL for driver locations?
2. What would break if we used HTTP polling instead of WebSocket for location tracking?
3. How does Kafka prevent the Ride Service from waiting for slow driver matching?

---

### **Day 3: Ride Matching Flow (Most Important)**
- [ ] Open `03-ride-matching-flow-sequence-BEGINNER.drawio`
- [ ] Follow the timeline from fare estimation (0ms) → driver matched (1000ms)
- [ ] Understand Zookeeper locking step-by-step
- [ ] See how location tracking runs concurrently with matching
- [ ] Read all KEY INSIGHTS boxes

**Self-Check Questions**:
1. Why does the system calculate fare estimate BEFORE ride request? (Hint: cache with 5min TTL)
2. What happens if Driver D1 declines the ride? (Hint: try D2, D3, ... in order of distance)
3. How does geofencing detect "driver arrived"? (Hint: Haversine distance < 50m)

---

### **Day 4: Data Model & Storage**
- [ ] Open `04-data-model-BEGINNER.drawio`
- [ ] Review PostgreSQL schema — understand foreign keys (trips → riders, trips → drivers)
- [ ] Memorize Redis key patterns with TTLs (`location:{id}` 60s, `surge:{geohash}` 120s)
- [ ] Understand Zookeeper lock tree structure (`/locks/drivers/{id}/...`)
- [ ] Review Kafka topic partitioning (partition by `trip_id` or `driver_id`)

**Self-Check Questions**:
1. Why does `ratings` table use `sender_id` / `receiver_id` instead of `rider_rating` / `driver_rating`?
2. Why are Zookeeper locks ephemeral nodes? (Hint: auto-delete on crash)
3. Why partition Kafka topics by `trip_id` instead of random? (Hint: ordering guarantees)

---

### **Day 5: Interview Prep & Trade-Offs**
- [ ] Practice whiteboard walkthrough (15-20 minutes):
   1. Start with context diagram (actors + external systems)
   2. Zoom into ride request flow (geosearch → lock → accept → track)
   3. Explain Zookeeper locks with race condition example
   4. Show data model (PostgreSQL + Redis + Kafka)
- [ ] Memorize key numbers (see below)
- [ ] Prepare trade-off answers (see Interview Q&A section)

---

## 📊 Key Numbers to Memorize

```
Scale:
• 100K concurrent rides (global peak)
• 1M total drivers
• 50M active riders

Performance:
• Geosearch latency:      ~10ms (GEORADIUS)
• Driver matching SLA:    <1 second
• Location update freq:   every 3-5 seconds
• WebSocket latency:      <100ms

TTLs:
• Driver location:        60s (Redis)
• Driver status:          300s (5 min, heartbeat refresh)
• Surge multiplier:       120s (2 min)
• Fare estimate cache:    300s (5 min)
• Trip status cache:      7200s (2 hr max trip)

Zookeeper:
• Lock session timeout:   30 seconds
• Ensemble size:          5 nodes
• Quorum:                 3 nodes (consensus)

Kafka:
• Event retention:        7 days
• Partitions per topic:   100
• Replication factor:     3
```

---

## 🎤 Interview Q&A (Senior-Level)

### **Q1: How do you prevent double-assignment of drivers?**

**❌ WEAK ANSWER**: "Use locks."

**✅ STRONG ANSWER**:  
*"We use Zookeeper ephemeral locks. When the Matching Service finds the closest driver D1, it attempts to create an ephemeral node at `/locks/drivers/D1/request_R1_seq0001`. If creation succeeds, the lock is acquired — D1 is now assigned to rider R1. If another request concurrently tries to lock D1, Zookeeper returns NodeExistsException, and the Matching Service immediately tries the next closest driver D2.*

*Ephemeral nodes are critical — if the Matching Service crashes mid-assignment, Zookeeper auto-deletes the lock after a 30-second session timeout, freeing the driver. This is stronger than Redis SETNX because Zookeeper uses Paxos consensus across a 5-node ensemble, guaranteeing strong consistency even during network partitions."*

---

### **Q2: Why Redis geospatial instead of PostgreSQL with PostGIS?**

**✅ STRONG ANSWER**:  
*"Both Redis and PostGIS support geospatial queries, but Redis GEORADIUS is in-memory and returns in ~10ms, while PostGIS requires a disk-based spatial index (GIST) that takes 50-100ms under load.*

*Driver locations are ephemeral — they change every 3-5 seconds and become stale after 60 seconds. Redis's TTL-based auto-expiry handles this naturally. PostgreSQL would accumulate millions of stale location rows that need manual cleanup.*

*We use Redis for the hot path (finding nearby drivers) and PostgreSQL for permanent location history (written asynchronously via Kafka for analytics and route optimization)."*

---

### **Q3: WebSocket vs HTTP polling — justify the choice.**

**✅ STRONG ANSWER**:  
*"HTTP polling for 100K trips at 3-second intervals = 33K req/sec. Each request carries 500-1000 bytes of HTTP headers, TCP handshake overhead, and 1-3s latency waiting for the next poll.*

*WebSocket opens one persistent TCP connection per driver. Location updates are tiny binary frames (~100 bytes) sent instantly when the driver moves, with <100ms latency. This reduces bandwidth by 10× and eliminates polling lag.*

*The trade-off: WebSocket requires sticky sessions (driver stays on same gateway instance) and auto-reconnect logic for failovers. But for real-time tracking, the latency improvement is non-negotiable — users expect smooth marker animation, not jumpy 3-second updates."*

---

### **Q4: How does surge pricing handle sudden spikes without shocking users?**

**✅ STRONG ANSWER**:  
*"Surge is calculated every 60 seconds per geohash cell (5km × 5km grid) by dividing pending requests by available drivers. A 5× demand spike would normally jump from 1.0× to 2.5× instantly.*

*We apply smoothing: `new_surge = 0.7 × old_surge + 0.3 × calculated_surge`. This blends 70% of the previous value with 30% of the new calculation, so surge rises gradually over 2-3 cycles instead of shocking users mid-request.*

*Additionally, the rider must explicitly tap 'Accept higher fare' before the ride is confirmed — no silent surge charges. The max cap is 3.0× to prevent price gouging during emergencies like rainstorms or events."*

---

### **Q5: What happens if Kafka goes down?**

**✅ STRONG ANSWER**:  
*"Ride requests would fail to publish the `ride.requested` event, so driver matching would stop. However, the Ride Service can detect Kafka downtime via health checks and fall back to:*

1. **Synchronous matching**: Directly call Matching Service (blocks rider for ~800ms but functional)
2. **Database queue**: INSERT into a `pending_matches` table, poll with background workers

*For events already in Kafka, the 3-replica setup ensures no data loss. When Kafka recovers, consumers resume from their last committed offset (Kafka tracks consumer group progress).*

*Critical events like `trip.completed` trigger retries with exponential backoff. After 3 failures, we write to a Dead Letter Queue and fallback to SMS notification via Twilio to ensure payment processing doesn't silently fail."*

---

## 🚫 What NOT to Say in Interviews

| ❌ **TRAP PHRASE** | **WHY IT'S WRONG** |
|--------------------|-------------------|
| "Store driver locations in the database" | Database can't handle 100K writes/sec from location updates; adds 10-50ms latency vs Redis's <1ms |
| "Use Redis SETNX for locking" | Possible but weaker than Zookeeper — no auto-expiry on crash, no consensus guarantees across partitions |
| "HTTP polling is fine for location tracking" | 33K req/sec for 100K trips kills servers; 1-3s latency ruins UX (jumpy marker animation) |
| "Just use Kafka for everything" | Kafka is async — can't use for synchronous operations like fare estimation or driver status check |
| "Surge pricing is just price gouging" | It's demand-driven economics with safeguards (smoothing, max cap, explicit accept). Attracts more drivers during high demand. |
| "WebSocket doesn't scale" | With sticky sessions + auto-reconnect, WebSocket scales to millions of connections (WhatsApp, Slack use it) |

---

## 🎯 Interview Whiteboard Flow (20-Minute Template)

### **Minute 0-3: Requirements Clarification**
"Before designing, let me clarify scope:
- Scale: How many concurrent rides? **100K**
- Latency: Driver matching SLA? **<1 second**
- Consistency: Can two riders get assigned to same driver? **No (strict consistency for locks)**
- Features: Just ride matching or also surge pricing, ratings? **All**"

### **Minute 3-8: High-Level Architecture** (Draw box diagram)
```
Rider App → API Gateway → Ride Service → Driver Matching Service
                               ↓                  ↓
                         PostgreSQL        Redis GEORADIUS
                                                 ↓
                                          Zookeeper Locks
                               ↓
Driver App ← WebSocket Gateway ← Location Update Service
```
Explain:
- **Redis GEORADIUS**: Find 10 nearest drivers in ~10ms
- **Zookeeper locks**: Prevent double-assignment (ephemeral nodes)
- **WebSocket**: Real-time location tracking (<100ms)
- **Kafka**: Asynchronous event-driven (ride.requested, trip.completed)

### **Minute 8-14: Deep Dive — Driver Matching Flow**
Walk through step-by-step:
1. Rider taps "Request Ride"
2. Ride Service → PUBLISH `ride.requested` (Kafka)
3. Matching Service → GEORADIUS (Redis) → get 10 nearest drivers
4. Try D1 (closest) → CREATE Zookeeper lock → SUCCESS
5. Update driver status to BUSY → Remove from `drivers:available`
6. Notify driver → FCM/APN push
7. Driver accepts → INSERT trip → Release lock → Notify rider

### **Minute 14-18: Data Model** (Show PostgreSQL + Redis)
PostgreSQL:
- `trips` (trip_id, rider_id, driver_id, status, fare)
- `drivers` (driver_id, vehicle_type, status, avg_rating)
- `ratings` (ride_id, sender_id, receiver_id, rating)

Redis:
- `drivers:available` (GEOSPATIAL)
- `location:{driver_id}` (STRING, TTL 60s)
- `surge_multiplier:{geohash}` (STRING, TTL 120s)

### **Minute 18-20: Trade-Offs & Bottlenecks**
"The main bottleneck is **driver matching under high load**. Solutions:
- **Scale matching service horizontally**: 50 instances, each handling a partition of requests
- **Geoshard Redis**: Partition `drivers:available` by region (US-East, Europe, Asia)
- **Zookeeper cluster**: 5-node ensemble for high availability
- **Fallback**: If matching takes >3 seconds, retry with expanded radius (10km instead of 5km)"

---

## 🏆 Self-Check: Can You Explain...

Before moving to the next system, make sure you can answer:

✅ **Conceptual**:
1. Why does UBER use Zookeeper instead of just Redis locks?
2. What breaks if we remove the surge pricing smoothing algorithm?
3. How does Redis GEORADIUS achieve ~10ms latency for 1M drivers?

✅ **Practical**:
1. Draw the ride matching flow from memory (include Zookeeper locking step)
2. Write the Redis commands for adding a driver, finding nearby drivers, and removing a driver
3. Design the Kafka topic structure (topic names, partition keys, consumers)

✅ **Trade-Offs**:
1. PostgreSQL vs Redis for driver locations — pros/cons of each
2. WebSocket vs HTTP polling — when would you choose polling?
3. Kafka vs RabbitMQ for ride events — justify Kafka's choice

---

## 📁 Files in This Folder

| File | Size | Description |
|------|------|-------------|
| `01-context-BEGINNER.drawio` | 15KB | System boundary, actors, external systems, key challenges |
| `02-architecture-components-BEGINNER.drawio` | 18KB | All services, WHY boxes, technologies, data stores |
| `03-ride-matching-flow-sequence-BEGINNER.drawio` | 22KB | Timeline with latency breakdown, concurrent location tracking |
| `04-data-model-BEGINNER.drawio` | 19KB | PostgreSQL schema, Redis keys, Zookeeper locks, Kafka topics |
| `README-BEGINNER.md` | This file | Complete learning guide, study plan, interview prep |

---

## 🛠️ How to Open Diagrams

### **Option 1: Online (Recommended)**
1. Go to [diagrams.net](https://app.diagrams.net)
2. File → Open → select any `.drawio` file
3. Zoom in/out to explore details

### **Option 2: VS Code**
1. Install "Draw.io Integration" extension
2. Click any `.drawio` file
3. Edit directly in VS Code

### **Option 3: Desktop App**
1. Download [draw.io desktop app](https://github.com/jgraph/drawio-desktop/releases)
2. Open files locally
3. Export to PNG/PDF for presentations

---

## 🎓 Next Steps

After mastering UBER/OLA, apply these concepts to:
- **Food Delivery** (Zomato/Swiggy) — similar geosearch + real-time tracking
- **Maps Navigation** (Google Maps) — live traffic updates, route optimization
- **Taxi Booking** (Lyft, Grab) — nearly identical architecture

**Key Insight**: Once you understand geospatial indexing, distributed locking, and real-time tracking, you can design ANY location-based service.

---

## 📚 Further Reading

- [Redis Geospatial Documentation](https://redis.io/docs/data-types/geospatial/)
- [Zookeeper Locks & Leader Election](https://zookeeper.apache.org/doc/current/recipes.html)
- [WebSocket vs HTTP Polling Comparison](https://ably.com/topic/websockets-vs-http)
- [Kafka Event Streaming Patterns](https://kafka.apache.org/documentation/#uses)
- [UBER Engineering Blog](https://www.uber.com/en-IN/blog/engineering/)

---

**Created**: 2026-08-30  
**Diagrams**: 4 beginner-friendly .drawio files  
**Target Audience**: Interview prep (L3-L5), System design beginners  
**Estimated Study Time**: 5 days (2-3 hours/day)
