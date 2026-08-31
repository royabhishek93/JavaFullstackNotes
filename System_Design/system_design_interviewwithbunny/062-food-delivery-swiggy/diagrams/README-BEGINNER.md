# ZOMATO/SWIGGY Food Delivery System — BEGINNER Study Guide

> **Three-sided marketplace**: Customer (demand) ↔ Restaurant (supply) ↔ Delivery Partner (logistics) — all coordinated in real-time

---

## 📚 **How to Use These Diagrams**

This folder contains **4 beginner-friendly diagrams** for learning Food Delivery system design:

1. **[01-context-BEGINNER.drawio](./01-context-BEGINNER.drawio)** — System boundary, actors, external systems, key challenges
2. **[02-architecture-components-BEGINNER.drawio](./02-architecture-components-BEGINNER.drawio)** — High-level architecture with WHY boxes
3. **[03-order-flow-sequence-BEGINNER.drawio](./03-order-flow-sequence-BEGINNER.drawio)** — Complete order placement flow (14 swim lanes, 4 phases)
4. **[04-data-model-BEGINNER.drawio](./04-data-model-BEGINNER.drawio)** — MySQL schema, Redis keys, Cassandra tables, Elasticsearch index, Kafka topics

**Recommended study sequence**: Context → Architecture → Sequence → Data Model → Review all

---

## 🗓️ **5-7 Day Study Plan** (1-2 hours/day)

### **Day 1: System Context & Actors**
- **Diagram**: 01-context-BEGINNER.drawio
- **Focus**: Three-sided marketplace concept
  - Customer: searches, orders, tracks
  - Restaurant: accepts orders, sets prep time
  - Delivery Partner: receives dispatch, sends GPS every 5s, picks up, delivers
- **Key challenge**: Real-time coordination across all three parties
- **Real-world analogy**: Traditional delivery (manual phone calls) vs Zomato (automated coordination)
- **Self-check**:
  - What are the 3 actors? What does each do?
  - What external systems are needed? (Maps API, Payment Gateway, Push Notifications, CDN)
  - Why is geospatial indexing needed? (500K partners, find nearest <10ms)

### **Day 2: High-Level Architecture**
- **Diagram**: 02-architecture-components-BEGINNER.drawio
- **Focus**: Microservices breakdown
  - **Client layer**: Customer App, Restaurant Tablet, Partner App
  - **Gateway layer**: Load Balancer, API Gateway, WebSocket Gateway
  - **Core services**: Order, Restaurant Discovery, Location Tracking, Partner Assignment, Real-Time Tracking, Notification, Payment, Rating, Surge Pricing, ETA Calculator, Menu
  - **Data stores**: MySQL (ACID), Redis GEO (geospatial), Redis Cache, Cassandra (time-series), Elasticsearch (search), Kafka (events)
- **WHY boxes** (critical to memorize):
  - **Redis GEO**: GEORADIUS finds 10 nearest from 500K in <10ms (vs MySQL PostGIS 50-100ms)
  - **Kafka**: Decouples services, 7-day retention for replay (vs RabbitMQ loses messages on crash)
  - **SSE for customer tracking**: One-way push, simpler than WebSocket at scale
  - **Order state machine**: Enforces legal transitions, prevents bugs
- **Self-check**:
  - Draw the service layers from memory
  - Explain why Redis GEO instead of MySQL for partner locations
  - Why Kafka instead of RabbitMQ?
  - Why SSE for customer tracking instead of HTTP polling?

### **Day 3: Order Flow Sequence**
- **Diagram**: 03-order-flow-sequence-BEGINNER.drawio
- **Focus**: Step-by-step order lifecycle
  - **Phase 1 (0-100ms)**: Customer places order → Order Service validates → MySQL INSERT → Kafka publish → 201 Created response → Restaurant receives WebSocket push
  - **Phase 2 (5-20 min)**: Restaurant accepts → status = RESTAURANT_ACCEPTED → Kafka event
  - **Phase 3 (30-60s)**: Assignment Service consumes event → GEORADIUS 5km → filter ONLINE partners → dispatch to nearest → 30s timeout → partner accepts → status = PARTNER_ASSIGNED
  - **Concurrent**: Partner sends GPS every 5s → GEOADD to Redis → Cassandra audit log → Kafka event → SSE push to customer (animate marker on map)
  - **Phase 4 (15-30 min)**: Partner marks PICKED_UP → drives to customer → marks DELIVERED → Kafka event → FCM push → customer rates
- **Key insights**:
  - GEORADIUS: 10 nearest from 500K in <10ms
  - 30s timeout prevents one partner blocking order
  - WebSocket: 500K partners, 100K GPS updates/sec
  - Cassandra: 30-day location history for disputes
  - Kafka: decouple order events from notifications
  - SSE: push partner location to customer every 5s
- **Self-check**:
  - Walk through order placement (POST /orders → MySQL → Kafka → 201 response)
  - Explain partner assignment algorithm (GEORADIUS → filter → dispatch → timeout → escalate)
  - How does customer see partner location on map? (GPS → Kafka → SSE push)
  - Why Cassandra for location history? (100K writes/sec, 30-day TTL)

### **Day 4: Data Model & Relationships**
- **Diagram**: 04-data-model-BEGINNER.drawio
- **Focus**: Schema design for each data store
  - **MySQL tables**: restaurants, menu_items, orders, order_items, delivery_partners, payments (ACID transactions)
  - **Redis GEO**: `GEOADD delivery_partners lon lat partnerId`, `GEORADIUS` for nearest search
  - **Redis Cache**: `menu:{restaurantId}` TTL 30min, `surge:{geohash7}` TTL 2min, `session:{userId}` TTL 1hr
  - **Cassandra**: `partner_location_history` (partition by partner_id, sort by recorded_at DESC, 30-day TTL), `order_status_events` (event sourcing audit)
  - **Elasticsearch**: `restaurant_index` (geo_point + text + filters for cuisine, rating, is_open)
  - **Kafka topics**: order-placed, restaurant-accepted, partner-assigned, partner-location-update, order-delivered (partition by order_id or partner_id)
- **WHY boxes**:
  - **MySQL**: Multi-table ACID transaction (orders + order_items + payments)
  - **ENUM status**: Enforces valid states in DB schema
  - **Cassandra**: Write-heavy (100K GPS/sec), automatic TTL cleanup
  - **Kafka for GPS**: Decouple producers from consumers, replay on crash
- **Self-check**:
  - Draw MySQL ER diagram (restaurants → menu_items, orders → order_items/payments)
  - What Redis keys are used? What's the TTL strategy?
  - Why Cassandra for location history? (vs MySQL unbounded growth)
  - Explain Kafka partition keys (order_id for order events, partner_id for GPS updates)

### **Day 5: Interview Practice (Core Questions)**
- **Scenario 1**: "Design Zomato. Walk me through the architecture."
  - Start with context (3 actors, external systems)
  - Explain microservices (Order, Restaurant Discovery, Location Tracking, Partner Assignment, Real-Time Tracking, Notification, Payment)
  - Justify technology choices (MySQL for ACID, Redis GEO for geospatial, Cassandra for time-series, Kafka for events)
  - Walkthrough sequence (order placement → restaurant acceptance → partner assignment → tracking → delivery)
- **Scenario 2**: "500K delivery partners send GPS every 5 seconds. How do you handle 100K writes/sec?"
  - Partner app → WebSocket → Location Service → Kafka (partner-location-update topic)
  - Kafka consumers: Redis GEO (GEOADD), Cassandra (audit log), Real-Time Service (SSE push)
  - Redis GEO: in-memory, sub-millisecond GEOADD
  - Cassandra: optimized for write-heavy, LSM tree, 30-day TTL auto-cleanup
  - If Redis crashes: partners re-send GPS in next 5s, data regenerates (ephemeral OK)
- **Scenario 3**: "Restaurant accepts order. How do you find nearest available delivery partner in <60s?"
  - Order Service publishes `restaurant.accepted` event to Kafka
  - Assignment Service consumes event → GEORADIUS delivery_partners rest_lon rest_lat 5km ASC COUNT 10
  - Filter to status = ONLINE (exclude BUSY/OFFLINE)
  - Dispatch to nearest partner → 30s timeout
  - If no response: try next nearest → escalate radius 5km → 7km → 10km
  - Why GEORADIUS? (geohash indexing, <10ms for 10 nearest from 500K)
- **Scenario 4**: "Customer wants to track delivery partner on map in real-time. How do you push location updates?"
  - Partner app sends GPS every 5s → Kafka (partner-location-update)
  - Real-Time Tracking Service subscribes to Kafka → filters for customer's order → SSE push to customer app
  - SSE (Server-Sent Events): persistent HTTP/2 connection, one-way push, auto-reconnect
  - Alternative (HTTP polling): 500K orders × 1 req/5s = 100K req/sec (vs SSE 10× less bandwidth)
  - Alternative (WebSocket): bidirectional (overkill for one-way push), harder to scale

### **Day 6: Deep Dive (Advanced Topics)**
- **Order State Machine**:
  - Valid transitions: PLACED → RESTAURANT_ACCEPTED → PREPARING → PARTNER_ASSIGNED → PICKED_UP → OUT_FOR_DELIVERY → DELIVERED
  - Invalid: PLACED → DELIVERED (skips pickup), PICKED_UP → PLACED (backwards)
  - Enforcement: Application validates transitions, MySQL ENUM prevents invalid values
  - Audit: Cassandra `order_status_events` table logs every transition with timestamp
- **Surge Pricing Calculator**:
  - Geohash-7 cells (~153m × 153m precision)
  - Formula: `surge_multiplier = pending_orders / available_partners` per cell
  - Update frequency: every 60s
  - Redis key: `surge:{geohash7}` TTL 2min
  - Smoothing: 70% current + 30% previous (prevent wild swings)
- **ETA Calculation**:
  - ML model inputs: distance, traffic (Google Maps API), prep_time (restaurant avg), partner_speed (avg from Cassandra history)
  - Output: delivery_minutes
  - Update: recalculate every 60s while order IN_PROGRESS
- **Partner Assignment Edge Cases**:
  - No partners in 5km → escalate radius 7km → 10km
  - All partners reject → notify restaurant, refund customer, log to analytics
  - Partner accepts but doesn't move in 5 min → auto-reassign to next nearest
  - Concurrent assignments: Zookeeper distributed lock (prevent double-assignment)
- **Data Consistency**:
  - MySQL master-replica lag: read-after-write from master (orders, payments)
  - Cassandra eventual consistency: acceptable for location history (audit, not critical path)
  - Redis GEO: single-instance or Redis Cluster (consistent hashing by partner_id)
  - Kafka: at-least-once delivery (idempotent consumers handle duplicates)

### **Day 7: Production Considerations & Scale Numbers**
- **Scale targets** (memorize these):
  - 100M orders/month (3.3M/day, 500 orders/sec peak)
  - 500K active delivery partners
  - 100K GPS updates/sec (500K partners × 1 update/5s)
  - 200K restaurants
  - 10K restaurant searches/sec
  - 99.99% availability (52 min downtime/year)
  - Partner assignment latency: <60s (p99)
  - GEORADIUS latency: <10ms (p99)
  - Order placement latency: <100ms
  - SSE push latency: <500ms
  - Redis cluster: 8 shards (partition by partner_id geohash)
  - MySQL replicas: 1 master (writes), 5 read replicas
- **Production edge cases**:
  - **GPS spoof detection**: Validate partner location with cell tower triangulation, speed limits
  - **Fraud detection**: ML model on order patterns (same address, different users = account farming)
  - **Restaurant downtime**: Mark `is_open = false`, exclude from Elasticsearch results
  - **Payment failure**: Kafka retry (3 attempts), then refund, notify customer
  - **Partner app offline**: WebSocket disconnect → status = OFFLINE, remove from Redis GEO after 60s
  - **Database failover**: MySQL master crash → promote replica to master (30s downtime)
  - **Redis crash**: Replicas take over, partners re-send GPS, data regenerates
  - **Kafka lag**: If consumer falls behind >1 min, alert ops team
- **Monitoring & alerting**:
  - Orders/sec, Partner GPS updates/sec, Partner assignment latency (p50/p99)
  - Redis GEO GEORADIUS latency, Order state transitions (funnel: placed → delivered %)
  - Partner acceptance rate (first offer vs escalated radius)
  - Alert: if assignment failure >5% → page ops team

---

## 💡 **Key Concepts to Master**

### **1. Three-Sided Marketplace Coordination**
Traditional delivery: Customer calls restaurant → restaurant prepares → restaurant calls courier agency → courier picks up → delivers. **Zomato automates**: Customer taps → system notifies restaurant AND pre-identifies nearby riders → rider dispatched when food ready → customer tracks on map. The hard part: all three parties (customer, restaurant, rider) have independent state that must sync continuously.

### **2. Redis GEO for Geospatial Indexing**
500K partners × 1 update/5s = 100K writes/sec. Redis GEO stores geohash internally → O(log N) search. GEORADIUS finds 10 nearest in <10ms. MySQL PostGIS alternative: 50-100ms for same query (disk I/O bound). Redis is in-memory → sub-millisecond. If Redis crashes: partners re-send GPS in next 5s, data regenerates (ephemeral OK).

### **3. Partner Assignment Algorithm**
1. Order Service publishes `restaurant.accepted` event
2. Assignment Service GEORADIUS 5km → returns 10 nearest
3. Filter to status = ONLINE (exclude BUSY/OFFLINE)
4. Dispatch to nearest partner → 30s timeout
5. If no response: try next nearest → escalate radius 5km → 7km → 10km
6. If all reject: notify restaurant, refund customer

**Why 30s timeout?** Prevent one partner blocking order. If partner ignoring, move to next.

### **4. Cassandra for Time-Series Location History**
100K GPS writes/sec, 30-day retention = 259B records. MySQL can't handle (disk I/O bottleneck, unbounded growth). Cassandra optimized: write-heavy (LSM tree), time-series partitioning (partner_id, recorded_at DESC), automatic TTL cleanup. Use case: Customer dispute "Partner never came to my address" → replay GPS trail.

### **5. Kafka for Event-Driven Architecture**
Order placement: Order Service fires `order.placed` event → returns 201 Created in <100ms. Multiple consumers process independently: Notification Service (push), Assignment Service (find partner), Analytics (fraud), Cassandra (audit). If Notification Service crashes 2 min: replays from stored offset → no lost notifications. RabbitMQ loses queued messages on crash. Kafka retains 7 days (replay-able).

### **6. SSE for Real-Time Customer Tracking**
HTTP polling: 500K active orders × 1 req/5s = 100K req/sec (full TCP handshake + auth headers). SSE: persistent HTTP/2 connection, server pushes updates when partner moves (event-driven), binary frames ~100 bytes vs 500-1000 bytes HTTP. Latency: <500ms (instant push) vs 1-3s (polling). WebSocket alternative: bidirectional (overkill for one-way push), harder to scale.

### **7. Order State Machine**
Valid: PLACED → RESTAURANT_ACCEPTED → PREPARING → PARTNER_ASSIGNED → PICKED_UP → OUT_FOR_DELIVERY → DELIVERED. Invalid: PLACED → DELIVERED (skips pickup), PICKED_UP → PLACED (backwards). Without state machine: raw 'status' text field → bugs write any value. Each state controls allowed actions: Cancellation free before PREPARING, impossible after PICKED_UP. Customer rates only after DELIVERED. Cassandra `order_status_events` = full audit trail.

### **8. Surge Pricing (Demand/Supply per Geohash)**
Geohash-7 cells (~153m precision). `surge_multiplier = pending_orders / available_partners` per cell. Update every 60s. Redis key `surge:{geohash7}` TTL 2min. Smoothing: 70% current + 30% previous (prevent wild swings). Customer sees "High demand in your area, 1.5x pricing" (transparency).

---

## 🎯 **Interview Q&A** (Expect These Questions)

### **Q1: Why Redis GEO instead of MySQL with PostGIS extension?**
**Strong answer**: 500K partners send GPS every 5 seconds, that's 100K writes/sec. MySQL is disk-based, can't handle that write throughput (disk I/O bottleneck). Redis GEO is in-memory, sub-millisecond GEOADD. GEORADIUS finds 10 nearest partners from 500K in <10ms using geohash indexing (O(log N)). MySQL PostGIS same query takes 50-100ms. Plus, partner locations are ephemeral—if Redis crashes, partners re-send GPS in next 5 seconds and data regenerates. We don't need durable persistence for this use case.

**Weak answer**: Redis is faster. (Why? What's the throughput? What happens if it crashes?)

### **Q2: How do you prevent double-assignment of same order to two partners?**
**Strong answer**: When Assignment Service dispatches order to partner P1, it acquires a distributed lock in Zookeeper with key `order:{orderId}:assignment` with 30-second TTL. If P1 doesn't respond in 30s, lock expires, Assignment Service tries next partner P2. If P1 accepts after 29s, updates order status to PARTNER_ASSIGNED and releases lock. If two Assignment Service instances try to assign same order concurrently, only one acquires lock, the other sees lock exists and skips. Zookeeper's atomic compare-and-set prevents race conditions.

**Weak answer**: We check the database. (What if two services check simultaneously? Race condition!)

### **Q3: Customer sees partner on map moving in real-time. How is this implemented at scale?**
**Strong answer**: Partner app sends GPS every 5 seconds via WebSocket to Location Service. Location Service publishes to Kafka topic `partner-location-update` (partition key: partner_id). Real-Time Tracking Service subscribes to Kafka, filters for partners assigned to active orders, pushes location updates to customer apps via SSE (Server-Sent Events). SSE is persistent HTTP/2 connection, server pushes when new data arrives. This is better than HTTP polling (500K orders × 1 req/5s = 100K req/sec overhead) or WebSocket (bidirectional overkill, harder to scale). SSE is one-way push, auto-reconnects on disconnect, works through load balancers.

**Weak answer**: We use WebSockets. (Why not HTTP polling? What's the throughput? How do you scale?)

### **Q4: Why Cassandra for partner location history instead of MySQL?**
**Strong answer**: We need to store 100K GPS updates/sec for 30-day retention. That's 259 billion records. MySQL can't handle this—disk I/O bottleneck, unbounded table growth, slow queries. Cassandra is optimized for write-heavy time-series data: uses LSM tree (append-only, no disk seeks), partitions by partner_id (queries by partner are fast), sorts by recorded_at DESC (recent locations first), automatic TTL cleanup (no manual DELETE jobs). Use case: Customer dispute "Partner never came to my address"—we replay GPS trail from Cassandra for proof. We don't need to query all partners' locations (that would be slow), only specific partner_id (partition key query is fast).

**Weak answer**: Cassandra scales better. (Why? What's the data model? What queries do you run?)

### **Q5: Restaurant accepts order at 12:00. How do you find nearest partner and dispatch in <60s?**
**Strong answer**:
1. Order Service updates status to RESTAURANT_ACCEPTED, publishes Kafka event
2. Assignment Service consumes event, extracts restaurant lat/lon
3. `GEORADIUS delivery_partners 77.5946 12.9716 5 km WITHDIST ASC COUNT 10` → returns 10 nearest partners with distances
4. Filter to status = ONLINE (exclude BUSY/OFFLINE)
5. Dispatch order offer to nearest partner P1 via WebSocket (30s timeout)
6. If P1 accepts: update status to PARTNER_ASSIGNED, release lock
7. If P1 rejects or timeout: try next nearest P2
8. If all 10 reject: escalate radius 5km → 7km → 10km
9. If still no partners: notify restaurant, refund customer, log to analytics for ML model
GEORADIUS is <10ms because Redis GEO uses geohash indexing (O(log N)). Total latency: <60s for 99% of orders.

**Weak answer**: We search the database for nearby partners. (How? What's the query? What index? What's the latency?)

### **Q6: What if a partner accepts order but then goes offline or doesn't move for 5 minutes?**
**Strong answer**: When partner accepts, we start a 5-minute watchdog timer. We expect GPS updates every 5 seconds. If partner hasn't sent GPS update in 60 seconds, we mark status = OFFLINE, remove from Redis GEO. If order is still in PARTNER_ASSIGNED state and partner hasn't marked PICKED_UP after 5 minutes, we auto-reassign: run GEORADIUS again, exclude previous partner, dispatch to next nearest. Notify original partner "Order reassigned due to inactivity". Log to analytics for partner rating impact. This prevents bad actors from accepting orders and going offline.

**Weak answer**: We cancel the order. (Why not reassign? What about customer experience?)

### **Q7: How do you handle surge pricing fairly and transparently?**
**Strong answer**: We divide city into geohash-7 cells (~153m × 153m). Every 60 seconds, Surge Calculator counts `pending_orders` and `available_partners` (status = ONLINE, not assigned) per cell. `surge_multiplier = pending_orders / available_partners`. If >1.5, apply surge. Smoothing: 70% current + 30% previous (prevent wild swings). Store in Redis `surge:{geohash7}` TTL 2min. Customer sees "High demand in your area, 1.5x pricing" with transparent reason. Customer can choose to order now or wait. We don't hide surge, we explain it.

**Weak answer**: We increase prices when demand is high. (How do you calculate? What's the granularity? How do you communicate to customer?)

### **Q8: What happens if MySQL master crashes during order placement (after INSERT but before Kafka publish)?**
**Strong answer**: We use transaction with two-phase commit:
```sql
BEGIN;
  INSERT INTO orders ...;
  INSERT INTO order_items ...;
  INSERT INTO payments ...;
  -- Mark outbox event
  INSERT INTO outbox_events (event_type='order.placed', payload=..., status='PENDING');
COMMIT;
```
Separate background worker polls `outbox_events` table every 100ms, publishes to Kafka, marks status='PUBLISHED'. If MySQL crashes after COMMIT but before Kafka publish, worker restarts, sees PENDING events, publishes to Kafka. This is **transactional outbox pattern**—guarantees event eventually published. If MySQL crashes before COMMIT, transaction rolls back, customer gets 500 error, retries.

**Weak answer**: We publish to Kafka inside the transaction. (Kafka is not transactional with MySQL! 2PC across systems is complex.)

### **Q9: How do you prevent GPS spoofing (partner fakes location)?**
**Strong answer**: 
1. **Cell tower triangulation**: Validate reported GPS against cell tower location (partner app includes cell_tower_id)
2. **Speed limit validation**: If partner reports moving 5km in 5 seconds (3600 km/h), reject as spoof (max bike speed ~80 km/h)
3. **Historical pattern**: ML model learns partner's usual areas, flags if suddenly reporting from 200km away
4. **Platform APIs**: Use iOS CLLocationManager / Android FusedLocationProviderClient (harder to spoof than raw GPS)
5. **Audit trail**: Store all GPS updates in Cassandra (if dispute, replay entire trail)
If fraud detected: suspend partner, investigate, ban if confirmed.

**Weak answer**: We trust the partner. (No validation = easy fraud!)

### **Q10: Explain order placement latency: why <100ms is critical.**
**Strong answer**: Customer clicks "Place Order" → expects instant feedback. If >1 second, customer thinks app crashed, clicks again → double order. Our flow:
1. POST /orders → API Gateway (10ms auth/rate limit)
2. Order Service validates (10ms: restaurant open? items available?)
3. MySQL INSERT transaction (20ms: orders + order_items + payments + outbox)
4. Return 201 Created (don't wait for Kafka publish, outbox worker does that async)
5. Total: ~50ms p50, <100ms p99
Why async Kafka publish? If we wait for Kafka (10-20ms), then Notification Service (50ms), total becomes 150ms+. Customer doesn't need to wait for notification to know order succeeded. We respond immediately, process downstream async.

**Weak answer**: We insert into database and return. (What about validation? Kafka publish? Latency breakdown?)

---

## 🧠 **Self-Check Questions** (Before Interview)

After studying all diagrams, test yourself:

1. **Context**:
   - What are the 3 actors in Food Delivery system? What does each do?
   - What external systems are integrated? (Maps, Payment, Notifications, CDN)
   - Why is this called a "three-sided marketplace"?

2. **Architecture**:
   - Draw the service layers (Client → Gateway → Core Services → Data Stores)
   - Name 5 core microservices and their responsibilities
   - Why Redis GEO instead of MySQL PostGIS?
   - Why Kafka instead of RabbitMQ?
   - Why SSE for customer tracking instead of WebSocket or HTTP polling?
   - Why Cassandra for location history instead of MySQL?

3. **Order Flow**:
   - Walk through order placement: what happens in first 100ms?
   - How does restaurant receive new order notification? (WebSocket push)
   - Explain partner assignment algorithm step-by-step (GEORADIUS → filter → dispatch → timeout → escalate)
   - How does customer see partner location on map? (GPS → Kafka → SSE push)

4. **Data Model**:
   - What MySQL tables exist? What foreign keys?
   - What Redis keys are used? (menu:{id}, surge:{geohash}, GEOSPATIAL delivery_partners)
   - What Cassandra tables exist? What's the partition key? (partner_id)
   - What Kafka topics exist? What's the partition key? (order_id or partner_id)
   - Explain order state machine: valid transitions?

5. **Scale**:
   - How many GPS updates/sec? (100K from 500K partners)
   - How fast is GEORADIUS? (<10ms for 10 nearest from 500K)
   - What's the partner assignment latency? (<60s p99)
   - How many restaurant searches/sec? (10K)
   - How many orders/sec peak? (500)

6. **Edge Cases**:
   - What if partner accepts order but goes offline? (watchdog timer, auto-reassign after 5 min)
   - What if MySQL crashes during order placement? (transaction rolls back, customer retries)
   - What if Redis GEO crashes? (partners re-send GPS in next 5s, data regenerates)
   - What if all partners reject order? (escalate radius, notify restaurant, refund customer)
   - What if partner spoofs GPS location? (cell tower validation, speed limit check, ML fraud detection)

7. **Interview scenarios**:
   - "Design Zomato" — how do you start? (context, actors, then architecture, then sequence)
   - "Handle 100K GPS updates/sec" — what's your approach? (Kafka → Redis GEO + Cassandra)
   - "Find nearest partner in <60s" — explain algorithm (GEORADIUS → filter → dispatch → timeout)

---

## 📊 **Key Numbers to Memorize**

| Metric | Value | Why? |
|--------|-------|------|
| **Orders/month** | 100M | (3.3M/day, 500 orders/sec peak) |
| **Active partners** | 500K | Need geospatial indexing |
| **GPS updates/sec** | 100K | (500K partners × 1 update/5s) |
| **Restaurants** | 200K | Need search indexing (Elasticsearch) |
| **Restaurant searches/sec** | 10K | Elasticsearch handles easily |
| **GEORADIUS latency** | <10ms | (p99 for 10 nearest from 500K) |
| **Partner assignment latency** | <60s | (p99, includes timeout + escalation) |
| **Order placement latency** | <100ms | Customer expects instant feedback |
| **SSE push latency** | <500ms | For real-time tracking feel |
| **GPS update frequency** | Every 5s | Balance accuracy vs bandwidth |
| **Partner dispatch timeout** | 30s | Prevent blocking order |
| **Redis cluster shards** | 8 | Partition by partner_id geohash |
| **MySQL read replicas** | 5 | Scale read queries |
| **Cassandra location retention** | 30 days | Audit trail for disputes |
| **Kafka retention** | 7 days | Replay on consumer crash |
| **Redis menu cache TTL** | 30 min | Balance freshness vs load |
| **Redis surge cache TTL** | 2 min | Frequent updates |
| **Surge calculation interval** | 60s | Balance responsiveness vs churn |
| **Availability target** | 99.99% | (52 min downtime/year) |

---

## 🎤 **20-Minute Whiteboard Interview Template**

**Minute 0-2: Clarify requirements**
- "Are we designing Zomato/Swiggy/Uber Eats food delivery system?"
- "Three actors: customer, restaurant, delivery partner?"
- "Scope: restaurant search, order placement, partner assignment, real-time tracking, delivery?"
- "Out of scope: restaurant onboarding, menu management, payment processing details, ML fraud detection?"
- "Scale: 100M orders/month, 500K partners, 200K restaurants?"

**Minute 2-5: Draw context diagram**
- System boundary
- 3 actors: Customer (search, order, track), Restaurant (accept, prep), Partner (GPS, pickup, deliver)
- External systems: Maps API (ETA), Payment Gateway, Notifications (FCM/SMS), CDN (images)
- Key challenges: Three-sided real-time coordination, 100K GPS updates/sec, partner assignment <60s

**Minute 5-10: Draw architecture**
- Client layer: 3 apps
- Gateway layer: Load Balancer, API Gateway, WebSocket Gateway
- Core services: Order, Restaurant Discovery (Elasticsearch), Location Tracking (Redis GEO), Partner Assignment (GEORADIUS), Real-Time Tracking (SSE), Notification, Payment
- Data stores: MySQL (ACID), Redis GEO (geospatial), Cassandra (time-series), Kafka (events)
- Explain one WHY box: "Why Redis GEO? GEORADIUS finds 10 nearest from 500K in <10ms. MySQL PostGIS takes 50-100ms."

**Minute 10-15: Walk through order flow sequence**
- Customer places order → MySQL INSERT → Kafka publish → 201 response (<100ms)
- Restaurant receives WebSocket push → accepts → Kafka event
- Assignment Service GEORADIUS → filter ONLINE → dispatch to nearest → 30s timeout
- Partner accepts → status = PARTNER_ASSIGNED → SSE push to customer
- Concurrent: Partner GPS every 5s → Kafka → GEOADD Redis → SSE customer (animate map)
- Partner marks PICKED_UP → drives → DELIVERED → FCM push → customer rates

**Minute 15-18: Discuss data model**
- MySQL: orders (ENUM status state machine), restaurants, menu_items, order_items, payments (ACID transaction)
- Redis GEO: GEOADD delivery_partners, GEORADIUS for nearest search
- Cassandra: partner_location_history (partition by partner_id, 30-day TTL, 100K writes/sec)
- Kafka: order-placed, partner-location-update (partition by order_id or partner_id)

**Minute 18-20: Handle follow-up questions**
- "What if partner goes offline after accepting?" → watchdog timer, auto-reassign after 5 min
- "What if Redis crashes?" → partners re-send GPS, data regenerates (ephemeral OK)
- "How do you prevent GPS spoofing?" → cell tower validation, speed limit check, ML fraud detection
- "How do you scale to 1M orders/sec?" → shard MySQL (by region), Redis Cluster (by geohash), more Kafka partitions

---

## 🔥 **Common Mistakes to Avoid**

1. **Using MySQL for partner locations**: Can't handle 100K writes/sec, slow geospatial queries. Use Redis GEO.
2. **Forgetting 30s timeout on partner dispatch**: One partner ignoring blocks order. Always timeout and escalate.
3. **Not explaining WHY for each technology**: Interviewer wants to hear your reasoning, not just "Redis is fast".
4. **Missing order state machine**: Don't use raw 'status' string field. Use ENUM and validate transitions.
5. **Not handling Redis crash**: "What if it goes down?" → partners re-send GPS, data regenerates.
6. **Forgetting Cassandra for audit trail**: Customer disputes need GPS history. 30-day TTL in Cassandra.
7. **Using HTTP polling for tracking**: 100K req/sec overhead. Use SSE (persistent connection, push-based).
8. **Not partitioning Kafka topics**: Partner GPS should partition by partner_id (ordered per partner).
9. **Forgetting MySQL transaction**: Order placement is multi-table (orders + items + payments). Must be atomic.
10. **Not explaining scale numbers**: "How many GPS updates/sec?" If you don't know, interviewer doubts you.

---

## 📖 **Related System Designs**

- **UBER/OLA Ride Sharing**: Similar geospatial partner matching, but two-sided (rider-driver) not three-sided
- **Distributed Rate Limiter**: Used in API Gateway to prevent abuse (1000 req/min per user)
- **Notification System**: Used to send order updates via FCM/APNs/SMS
- **Chat Application**: WebSocket similar to partner GPS streaming, but bidirectional

---

## 🎓 **Production Best Practices**

1. **Idempotency**: Partner app may retry GPS update. Use `INSERT ... ON DUPLICATE KEY UPDATE` or Cassandra UPSERT.
2. **Circuit breaker**: If Maps API down, use fallback (straight-line distance). Don't block order placement.
3. **Graceful degradation**: If Elasticsearch down, fallback to MySQL search (slower but works).
4. **Database connection pooling**: 5 replicas, 100 connections each = 500 total. Limit per service instance.
5. **Kafka consumer lag monitoring**: If >1 min behind, alert ops team. May need more consumer instances.
6. **Redis GEO expiry**: If partner doesn't send GPS in 60s, remove from index (ZREM). Prevent stale data.
7. **MySQL slow query log**: Identify queries >100ms, add indexes (e.g., idx_status on orders table).
8. **Rate limiting**: Prevent partner app from spamming GPS updates (max 1 update per 4 seconds).
9. **Load testing**: Simulate 500 orders/sec, 100K GPS/sec before production. Find bottlenecks.
10. **Chaos engineering**: Kill Redis, MySQL replica, Kafka broker randomly. Ensure system recovers.

---

## ✅ **Sign-Off Checklist**

Before considering yourself "interview-ready" for Food Delivery system design:

- [ ] Can draw context diagram from memory (3 actors, external systems, challenges)
- [ ] Can draw architecture diagram from memory (all service layers, data stores)
- [ ] Can explain WHY for each technology choice (Redis GEO, Cassandra, Kafka, SSE, MySQL ACID)
- [ ] Can walk through order flow sequence step-by-step (4 phases)
- [ ] Can explain partner assignment algorithm (GEORADIUS → filter → dispatch → timeout → escalate)
- [ ] Can design MySQL schema (tables, foreign keys, indexes, ENUM status)
- [ ] Can design Redis keys (GEO, cache patterns, TTLs)
- [ ] Can design Cassandra schema (partition key, sort key, TTL)
- [ ] Can design Kafka topics (partition keys, consumer groups)
- [ ] Can explain order state machine (valid transitions, enforcement)
- [ ] Know all scale numbers (100K GPS/sec, <10ms GEORADIUS, <60s assignment, 500 orders/sec)
- [ ] Can handle edge cases (partner offline, Redis crash, MySQL failover, GPS spoofing)
- [ ] Can answer all interview Q&A questions confidently with strong answers
- [ ] Can complete 20-minute whiteboard interview template

---

## 📬 **Next Steps**

After mastering Food Delivery system:
1. **Practice whiteboarding**: Time yourself, 20 minutes, no notes
2. **Mock interview**: Ask friend to grill you on edge cases
3. **Compare with UBER/OLA**: What's similar? What's different? (two-sided vs three-sided)
4. **Study next system**: Move to System #09 (E-Commerce Amazon)

**Good luck! 🚀**
