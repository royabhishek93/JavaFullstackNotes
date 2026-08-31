# Zomato / Swiggy — Interview Script
## Design a Food Delivery Platform (Zomato / Swiggy / DoorDash)
### Speak This Word-for-Word to Your Interviewer

> How to use this: Study PAGE 1 to lock in the big picture — three-sided marketplace means three data flows to understand cold. Use PAGE 4+ as your interview script, walking through each step confidently. The hardest part of this system is the geospatial real-time delivery partner assignment — make sure you can draw the GEORADIUS flow on demand. The Senior Trap Questions cover the edge cases that separate 10 YOE from 15 YOE candidates.

# ═══════════════ PAGE 1 — START HERE ═══════════════

## BIG PICTURE (Understand This Before Anything Else)

> **► STUDY this diagram, don't draw it ◄**
> Zomato is a three-sided marketplace: customer (demand), restaurant (supply), and delivery partner (logistics). What makes it uniquely hard is real-time coordination across all three simultaneously. A customer order must be matched to a nearby available delivery partner within seconds of the restaurant accepting. The partner's GPS location is updating every 5 seconds across 500K active partners. This is a geospatial, real-time optimization problem running at massive scale — not just a simple CRUD order system.

```
                     ┌───────────────────────────────────────────────────────────┐
                     │                ZOMATO — DATA FLOW                         │
                     └───────────────────────────────────────────────────────────┘

  ┌──────────┐  Place Order  ┌──────────────┐  Route      ┌────────────────────┐
  │ Customer │──────────────►│  API Gateway │────────────►│  Order Service     │
  │  App     │               │ (Auth/Rate   │             │  (core state       │
  │          │◄──────────────│  Limit)      │             │   machine)         │
  │ (SSE for │  Order status │              │             └─────────┬──────────┘
  │ tracking)│  updates      └──────────────┘                       │
  └──────────┘                                                       │ Write order
                                                                     ▼
  ┌──────────┐  GPS update   ┌──────────────┐             ┌────────────────────┐
  │ Partner  │──────────────►│  Location    │  GEOADD     │      Redis         │
  │  App     │               │  Service     │────────────►│  GEO: partners     │
  │          │               │              │             │  delivery_partners  │
  │(WebSocket│               │              │◄────────────│  (lon,lat,id)      │
  │ for      │               │              │  GEORADIUS  │                    │
  │ dispatch)│               └──────────────┘             │  Active orders     │
  └──────────┘                                            │  Surge multipliers │
                                                          │  Restaurant cache  │
  ┌──────────┐  Accept order ┌──────────────┐             └────────────────────┘
  │Restaurant│◄──────────────│  Restaurant  │                       │
  │  Tablet  │               │  Service     │                       │
  │          │──────────────►│              │             ┌─────────▼──────────┐
  │          │  Order ready  └──────────────┘             │      MySQL         │
  └──────────┘                                            │  users/restaurants │
                                                          │  orders/payments   │
                                                          └────────────────────┘
                                                                     │
                                                          ┌──────────▼──────────┐
                                                          │      Kafka           │
                                                          │  order-placed        │
                                                          │  partner-assigned    │
                                                          │  order-delivered     │
                                                          └──────────┬──────────┘
                                                                     │
                                         ┌───────────────────────────┼────────────────────────┐
                                         │                           │                        │
                                ┌────────▼──────┐          ┌─────────▼──────┐       ┌─────────▼──────┐
                                │  Notification │          │  Analytics     │       │  Cassandra      │
                                │  Service      │          │  Service       │       │  (partner       │
                                │  (FCM/APNs/   │          │  (Flink/Spark) │       │   location      │
                                │   SMS)        │          │                │       │   history)      │
                                └───────────────┘          └────────────────┘       └────────────────┘
```

---

> **WHY THREE-SIDED MARKETPLACE IS HARD? (Beginner Explanation)**
>   Most platforms connect two parties — buyer and seller. Zomato coordinates three simultaneously:
>   customer (demand), restaurant (supply), and delivery partner (logistics). The moment a customer
>   places an order, the system must notify the restaurant AND pre-identify nearby riders before the
>   restaurant even accepts. Each party has live state: customer is waiting, restaurant is cooking,
>   partner is physically moving on a map. Any lag in any party's state update breaks the chain.
>   This is what makes Zomato harder than an e-commerce site — Flipkart ships from a warehouse it
>   controls. Zomato coordinates a restaurant it does not own and a rider it does not employ, in
>   real time, every order.

## RAPID ANSWER — If You Only Have 5 Minutes

Say this verbatim if time is short:

"Zomato is a three-sided marketplace: customer, restaurant, and delivery partner. The hardest problem is real-time delivery partner assignment using geolocation.

First, partner location tracking: every delivery partner's app sends GPS coordinates every 5 seconds. We store this in Redis GEO — GEOADD delivery_partners lon lat partnerId. Redis GEO uses geohash internally, giving O(log N) proximity queries.

Second, partner assignment: when a customer places an order and the restaurant accepts, we call GEORADIUS with the restaurant's lat/lon, 5km radius. We get back a list of nearby available partners sorted by distance. We try the closest available one first.

Third, the order lifecycle state machine: PLACED → RESTAURANT_ACCEPTED → PREPARING → PARTNER_ASSIGNED → PICKED_UP → OUT_FOR_DELIVERY → DELIVERED. Each state transition is an event on Kafka, which triggers notifications to the customer.

Fourth, real-time tracking: customer's app connects via SSE. Location service pushes partner GPS updates → Kafka → Notification Service → SSE to customer's browser. Customer sees the partner moving on a map.

Fifth, for scale: 500K partners × 1 update/5sec = 100K GEOADD operations/sec. Redis single instance handles 100K ops/sec. I'd shard Redis by geographic region — separate Redis instance per metro city. Mumbai partners go to Mumbai Redis, Delhi partners to Delhi Redis."

---

# ═══════════════ PAGE 2 — GLOSSARY ═══════════════

```
┌──────────────────────────────┬────────────────────────────────────────────────────────────┐
│ TERM                         │ WHAT IT MEANS                                              │
├──────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Three-Sided Marketplace      │ Platform connecting 3 types of participants: Customer      │
│                              │ (demand), Restaurant (supply), Delivery Partner (logistics)│
├──────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Redis GEO                    │ Redis data structure storing location as geohash. GEOADD   │
│                              │ adds (lon,lat,member). GEORADIUS finds all members within  │
│                              │ N km of a point. O(N+log M) where N=results, M=total.     │
├──────────────────────────────┼────────────────────────────────────────────────────────────┤
│ GEOADD                       │ Redis command: GEOADD key lon lat member. Updates partner  │
│                              │ location: GEOADD delivery_partners 72.87 19.07 partner123 │
├──────────────────────────────┼────────────────────────────────────────────────────────────┤
│ GEORADIUS                    │ Redis command: find all members within radius of a point.  │
│                              │ GEORADIUS delivery_partners 72.87 19.07 5 km ASC          │
├──────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Geohash                      │ Encode lat/lon as a base-32 string. 7-char geohash ≈       │
│                              │ 150m × 150m cell. Used for surge pricing zones.           │
├──────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Partner States               │ OFFLINE (app closed) → ONLINE (available for orders) →    │
│                              │ BUSY (has active order). Only ONLINE partners get orders. │
├──────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Order Lifecycle              │ PLACED → RESTAURANT_ACCEPTED → PREPARING →                │
│                              │ PARTNER_ASSIGNED → PICKED_UP → OUT_FOR_DELIVERY →         │
│                              │ DELIVERED (or CANCELLED at any pre-pickup stage)           │
├──────────────────────────────┼────────────────────────────────────────────────────────────┤
│ SSE (Server-Sent Events)     │ One-directional server → browser push. Used for order      │
│                              │ tracking (partner location updates every 5 sec to          │
│                              │ customer's map). Simpler than WebSocket for one-way push.  │
├──────────────────────────────┼────────────────────────────────────────────────────────────┤
│ WebSocket (Partner App)      │ Full-duplex connection. Partner app sends GPS updates and  │
│                              │ receives order dispatch notifications on same connection.  │
├──────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Surge Pricing                │ When demand > supply in an area: delivery fee multiplier   │
│                              │ increases. Implemented per geohash-7 cell in Redis.        │
│                              │ surge:{geohash7} → multiplier (e.g. 1.5x)                 │
├──────────────────────────────┼────────────────────────────────────────────────────────────┤
│ ETA                          │ Estimated Time of Arrival. ML model combining: distance,   │
│                              │ traffic (Google Maps API), restaurant prep time, partner   │
│                              │ historical speed. Updated every 30 sec on tracking screen.│
├──────────────────────────────┼────────────────────────────────────────────────────────────┤
│ PostGIS                      │ PostgreSQL extension for geospatial queries. Alternative   │
│                              │ to Redis GEO. Better for complex polygon queries but       │
│                              │ slower for high-frequency point updates (100K/sec).        │
├──────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Cassandra (Location History) │ Time-series store for partner location history. Used for   │
│                              │ dispute resolution ("partner never came to restaurant").   │
│                              │ Schema: (partner_id, timestamp) → (lat, lon)              │
├──────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Restaurant Tablet App        │ Android/iOS app on restaurant counter. Receives new orders │
│                              │ via WebSocket push. Accepts order, marks ready for pickup. │
├──────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Delivery Zone                │ Geographic area where a restaurant delivers. Defined as    │
│                              │ polygon or radius. Orders outside zone are rejected.       │
├──────────────────────────────┼────────────────────────────────────────────────────────────┤
│ Menu Cache                   │ Restaurant menu is read-heavy, write-rarely. Cached in     │
│                              │ Redis with TTL. Cache invalidated on menu update.          │
└──────────────────────────────┴────────────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 3 — WHY EACH COMPONENT ═══════════════

```
┌──────────────────┬──────────────────────────────────┬──────────────────────────────────┐
│ TECHNOLOGY       │ WHY WE USE IT                    │ WHY NOT ALTERNATIVE               │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Redis GEO        │ Sub-millisecond geo queries.      │ Not PostGIS: PostgreSQL heavier   │
│ (Partner         │ 100K GEOADD ops/sec on single    │ for 100K update/sec. PostGIS is   │
│  Location)       │ instance. Automatic geohash      │ excellent for static geo data     │
│                  │ encoding. Fits in memory.         │ (polygon delivery zones) but not  │
│                  │                                  │ for real-time moving objects.      │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Cassandra        │ Time-series partner location     │ Not MySQL: 100K writes/sec =      │
│ (Location        │ history. Wide-column = excellent │ table will grow unbounded, index  │
│  History)        │ for (partnerId, timestamp) →     │ degradation over time. Not Redis: │
│                  │ (lat,lon) access pattern.        │ Redis is not durable enough for   │
│                  │ Linear scale, no hot spots.      │ legal/dispute evidence store.     │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ MySQL            │ ACID transactions for orders     │ Not Cassandra: eventual consist-  │
│ (Orders/         │ and payments. "Order total must  │ ency too risky for financial data.│
│  Payments)       │ be charged exactly once" needs   │ Not MongoDB: MySQL has better ACID│
│                  │ strong consistency.              │ and mature read replica support.  │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Kafka            │ Decouples order state changes    │ Not RabbitMQ: Kafka retains msgs  │
│ (Order Events)   │ from notifications, analytics.   │ for replay. If notification       │
│                  │ Order event fan-out to multiple  │ service crashes, replays from     │
│                  │ consumers (notify, analytics,    │ offset. RabbitMQ loses messages   │
│                  │ Cassandra writer).               │ on consumer crash.                │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Elasticsearch    │ Restaurant search: cuisine,       │ Not MySQL LIKE: no geo scoring,  │
│ (Restaurant      │ rating, distance, open-now. Geo  │ slow full-text, can't sort by     │
│  Search)         │ distance scoring + text match.   │ distance × relevance composite.   │
│                  │ Handles 10K searches/sec easily. │ Not Solr: ES has better geo DSL. │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ SSE              │ Real-time partner location push  │ Not WebSocket (customer side):    │
│ (Customer        │ to customer. One-directional.    │ WebSocket is bidirectional, more  │
│  Tracking)       │ Works through HTTP/2, load       │ complex to maintain at scale.     │
│                  │ balancers, CDN. Simpler than WS. │ SSE reconnects automatically.     │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ WebSocket        │ Partner app needs bidirectional: │ Not polling: 5-second GPS polls   │
│ (Partner App)    │ send GPS, receive dispatch.      │ × 500K partners = 100K requests/  │
│                  │ Single connection for both.      │ sec just for "any new order?" —   │
│                  │                                  │ wasteful vs persistent WebSocket.  │
├──────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Redis            │ Surge multiplier per geohash-7   │ Not DB: reading surge multiplier  │
│ (Surge Pricing)  │ cell. O(1) lookup. Updated every │ from DB on every order placement  │
│                  │ 60 sec by demand/supply calc.    │ adds latency to critical path.    │
└──────────────────┴──────────────────────────────────┴──────────────────────────────────┘
```

---

> **WHY REDIS FOR REAL-TIME RIDER LOCATION? (Beginner Explanation)**
>   Redis GEO is the sticky note on the fridge — current, instantly readable, easy to replace every
>   5 seconds. MySQL is the filing cabinet in the basement — durable and great for permanent records,
>   but if 500K riders each update a filing cabinet every 5 seconds, the line wraps around the block.
>   Each database write needs disk I/O, index updates, and row locking. Redis is purely in-memory:
>   sub-millisecond reads, 100K writes/sec on a single instance. When a rider moves 200 meters, nobody
>   cares about their location from 10 seconds ago — it is throwaway data. If Redis crashes, the rider's
>   next GPS ping (in 5 seconds) restores current state. That's why we accept Redis's volatility here:
>   the data regenerates itself automatically every 5 seconds.

> **WHY KAFKA FOR ORDER EVENTS? (Beginner Explanation)**
>   Kafka is the order ticket printer at the restaurant pass — the waiter scribbles the order, drops
>   the ticket on the rail, and walks away immediately. The chef, the cashier, and the delivery counter
>   each pick up their copy when ready. Without Kafka, Order Service would need to directly call
>   Notification Service, Analytics, and Cassandra synchronously inside the same API request. If any
>   downstream service is slow or crashed, the customer's "Place Order" button hangs. With Kafka,
>   Order Service fires an event and immediately returns success to the customer. If Notification Service
>   was down for 2 minutes, it replays missed events from its stored Kafka offset when it recovers —
>   no lost notifications. RabbitMQ would lose those queued messages on consumer crash; Kafka retains
>   them on disk for replay.

---

# ═══════════════ PAGE 4 — FULL INTERVIEW SCRIPT ═══════════════

## OPENING

Say this to start:

"Zomato is a three-sided marketplace connecting customers, restaurants, and delivery partners. Before I start designing, I want to clarify the scope. The two hardest technical problems here are: first, real-time delivery partner assignment using geolocation — this is a geospatial problem at scale. Second, live order tracking — the customer needs to see the partner moving on a map in near-real-time. Let me confirm requirements before diving in."

---

## STEP 1 — Requirements Gathering

```
┌─────────────────────────────────────────────────────────────────────┐
│ CLARIFYING QUESTIONS TO ASK                                         │
├─────────────────────────────────────────────────────────────────────┤
│ 1. Are we building only food delivery or also restaurant discovery? │
│ 2. Do we need real-time partner tracking on a map for the customer? │
│ 3. Should we design the restaurant management portal too?           │
│ 4. What's the peak order volume? (India or global scale?)          │
│ 5. Do we need scheduled orders (pre-order for lunch at 1pm)?       │
│ 6. Live ETA or just static estimate at order placement?            │
└─────────────────────────────────────────────────────────────────────┘
```

**Functional Requirements:**
- Customers can search restaurants by location, cuisine, rating
- Customers can browse menus and place orders
- Restaurants receive orders in real-time and can accept/reject
- System assigns nearest available delivery partner automatically
- Customers can track partner location in real-time on a map
- Push/SMS notifications for each order state change
- Customers can rate restaurant and delivery partner post-delivery
- Surge pricing during peak demand periods

**Non-Functional Requirements:**
- Partner location update latency: < 10 seconds end-to-end
- Order assignment: partner assigned within 60 seconds of restaurant acceptance
- Availability: 99.99% for order placement (revenue-critical)
- Partner location update throughput: 100K updates/sec
- Eventual consistency acceptable for: restaurant search, ratings
- Strong consistency required for: order state, payment

---

## STEP 2 — Capacity Estimation

```
┌──────────────────────────────────────────────────────────────────┐
│ CAPACITY NUMBERS                                                  │
├──────────────────────────┬───────────────────────────────────────┤
│ Orders/month             │ 100 million                           │
│ Orders/second (avg)      │ ~38/sec                               │
│ Orders/second (peak)     │ ~500/sec (lunch 12pm-1pm)            │
│ Registered customers     │ 100 million                           │
│ Restaurants              │ 200,000                               │
│ Active delivery partners │ 500,000 (peak simultaneous)          │
│ Partner GPS updates/sec  │ 500K × 1/5sec = 100,000/sec         │
│ Restaurant search QPS    │ 10,000/sec peak                      │
│ Order status events/sec  │ ~2,000/sec (5 events per order)      │
│ Cities covered           │ 500+ (India), 1,000+ (global)        │
│ Avg order value          │ Rs 350 (~$4)                         │
│ Peak lunch window        │ 12:00pm – 1:30pm local time         │
│ Partner location Redis   │ 500K entries × ~50 bytes = ~25 MB   │
└──────────────────────────┴───────────────────────────────────────┘
```

"100K partner GPS updates/sec is the dominant write workload. A single Redis instance handles 100K ops/sec, so I'll shard by geographic region."

---

## STEP 3 — Core Entities

- **Customer**: user profile, saved addresses, payment methods, order history
- **Restaurant**: profile, location (lat/lon), operating hours, cuisine types, avg rating, is_open
- **MenuItem**: item in a restaurant's menu (name, price, category, is_available)
- **DeliveryPartner**: partner profile, vehicle type, current status (ONLINE/BUSY/OFFLINE), rating
- **Order**: the central entity — links customer, restaurant, partner. Has state machine lifecycle.
- **OrderItem**: specific items in an order (menu_item_id, quantity, unit_price snapshot)
- **Payment**: payment transaction for an order
- **PartnerLocation**: real-time location (Redis GEO) + historical log (Cassandra)
- **DeliveryZone**: polygon defining where a restaurant delivers (PostGIS for static polygon queries)

---

## STEP 4 — API Design

```
# Restaurant Discovery
GET  /restaurants/search?lat=19.07&lon=72.87&cuisine=indian&rating_min=4.0&open_now=true
     → Returns: [{ restaurant_id, name, rating, cuisine, eta_minutes, delivery_fee }]
     → Served from Elasticsearch (geo_distance + filters)

# Menu
GET  /restaurants/{restaurantId}/menu
     → Returns: full menu with categories and items
     → Served from Redis cache (TTL 30 min, invalidated on menu update)

# Place Order
POST /orders
     Body: { restaurant_id, items: [{menu_item_id, qty}], delivery_address, payment_method_id }
     → Returns: { order_id, status: PLACED, estimated_delivery_minutes, total_amount }
     → Validates: restaurant open, all items available, delivery address in zone
     → Creates: MySQL order record, Kafka event, WebSocket push to restaurant tablet

# Order Status
GET  /orders/{orderId}
     → Returns: { order_id, status, partner: {name, phone, lat, lon}, eta_minutes }

# Real-time Tracking (SSE stream)
GET  /orders/{orderId}/track
     → Content-Type: text/event-stream
     → Streams partner location updates every 5 sec until DELIVERED

# Restaurant: Accept Order
PUT  /orders/{orderId}/accept  [restaurant auth]
     Body: { estimated_prep_minutes: 15 }
     → Triggers partner assignment flow

# Partner: Update Location
PUT  /partners/{partnerId}/location  [partner auth]
     Body: { lat: 19.07, lon: 72.87 }
     → GEOADD delivery_partners lon lat partnerId

# Partner: Accept Dispatch
PUT  /orders/{orderId}/partner-accept  [partner auth]
     → order status: PARTNER_ASSIGNED
```

```
# Cancel Order
PATCH /orders/{orderId}/cancel
      Body: { reason: "CUSTOMER_CANCELLED" }
      → Returns: { order_id, status: "CANCELLED", refund_amount, refund_eta_days: 5 }
      → Allowed only before PICKED_UP state (enforced by order state machine)
      → Triggers Kafka event: order-cancelled → Payment Service initiates async refund

# Order History (customer)
GET  /orders?customerId={customerId}&page=1&limit=20
     → Returns: [{ order_id, restaurant_name, status, total_amount, created_at, items_summary }]
     → Served from MySQL read replica with INDEX on (customer_id, created_at)
     → Default sort: newest first; paginated to prevent unbounded result sets

# Rate Order (restaurant + delivery partner)
POST /orders/{orderId}/rating
     Body: { restaurant_rating: 4, partner_rating: 5, review_text: "Fast delivery!" }
     → Allowed only after status = DELIVERED (guarded by state machine)
     → Publishes Kafka event: order-rated → async UPDATE avg_rating on restaurants + delivery_partners
```

> **WHY CANCEL ORDER (PATCH /orders/{orderId}/cancel)?**
> PATCH signals a state transition rather than resource deletion — the order record must be retained for refund processing, audit trails, and restaurant penalty tracking. The state machine is the enforcement layer: cancel is rejected once the order reaches PICKED_UP because food is physically in transit. Earlier-stage cancellations publish a Kafka event consumed by Payment Service which calls the payment provider's refund API asynchronously — decoupling the refund from the cancel acknowledgement keeps the API response fast. Restaurant rejection-rate metrics increment on every restaurant-initiated cancel, feeding into the platform's restaurant quality scoring.

> **WHY ORDER HISTORY (GET /orders?customerId=X)?**
> Order history is a read-heavy, non-realtime query naturally served from MySQL read replicas. The composite index on (customer_id, created_at) in the orders table already exists for partner and restaurant queries — this endpoint reuses it at O(log N) regardless of table size. Without it: customers cannot reorder past favourites, support agents cannot investigate complaints, and the recommendation engine loses its primary personalisation signal. Pagination on the API surface prevents a single query from loading thousands of historical orders into memory.

> **WHY RATE ORDER (POST /orders/{orderId}/rating)?**
> Ratings for both the restaurant and the delivery partner are one user action (a single post-delivery form) but write to two separate entities. Guarding the endpoint to status=DELIVERED prevents gaming and premature ratings from corrupting data. Both avg_rating updates are asynchronous via Kafka — the rating submission never blocks on two separate UPDATEs. The restaurant's avg_rating feeds directly into its Elasticsearch relevance score in search results. The partner's avg_rating feeds into dispatch prioritisation so consistently rated partners get offered orders first.

---

> **► DRAW THIS on the whiteboard ◄**

## JSON REQUEST / RESPONSE EXAMPLES

```json
// POST /api/v1/orders
// Request:
{
  "restaurantId": "rest_pizza_hut_bangalore",
  "items": [
    { "itemId": "item_margherita_medium", "quantity": 2 },
    { "itemId": "item_garlic_bread",      "quantity": 1 }
  ],
  "deliveryAddress": {
    "lat": 12.9716,
    "lon": 77.5946,
    "addressLine": "123 MG Road, Bangalore 560001"
  },
  "paymentMethodId": "pm_card_4242"
}
// Response 201 Created:
{
  "orderId": "ord_abc789xyz",
  "status": "PLACED",
  "estimatedDeliveryMinutes": 35,
  "totalAmount": 67500,
  "currency": "INR",
  "restaurant": { "name": "Pizza Hut", "prepTimeMinutes": 20 }
}

// GET /api/v1/orders/{orderId}/track
// Response 200 OK (SSE or polling):
{
  "orderId": "ord_abc789xyz",
  "status": "OUT_FOR_DELIVERY",
  "deliveryPartner": {
    "name": "Ramesh Kumar",
    "phone": "+91-9876543210",
    "currentLocation": { "lat": 12.9750, "lon": 77.5960 },
    "eta_minutes": 8
  },
  "orderItems": [
    { "name": "Margherita Pizza (Medium)", "quantity": 2 },
    { "name": "Garlic Bread",              "quantity": 1 }
  ]
}
```

---

## STEP 5 — High-Level Architecture

► DRAW THIS ◄

```
                    ┌──────────────────────────────────────────────────────┐
                    │              HIGH-LEVEL ARCHITECTURE                  │
                    └──────────────────────────────────────────────────────┘

  Customer App ──────────────────────────────────────────────────────────────┐
  Partner App  ──────────────────────────────────────────────────────────────┤
  Restaurant   ──────────────────────────────────────────────────────────────┤
  Tablet       ──────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
                                   ┌──────────────────┐
                                   │   API Gateway     │
                                   │ (Auth/JWT, Rate   │
                                   │  Limit, SSL)      │
                                   └────────┬─────────┘
                        ┌───────────────────┼───────────────────┐
                        │                   │                   │
               ┌────────▼───────┐  ┌────────▼───────┐  ┌───────▼────────┐
               │ Order Service  │  │ Location Svc   │  │ Search Service │
               │ (state machine)│  │ (GPS tracking) │  │ (restaurant    │
               │                │  │                │  │  discovery)    │
               └────────┬───────┘  └────────┬───────┘  └───────┬────────┘
                        │                   │                   │
                        │           ┌───────▼────────┐         │
                        │           │  Redis GEO     │         │
                        │           │ delivery_part- │         ▼
                        │           │ ners (real-time│  ┌──────────────┐
                        │           │ locations)     │  │Elasticsearch │
                        │           │                │  │(restaurants  │
                        │           │ + surge:{}     │  │ geo+text     │
                        │           │ + menu cache   │  │ index)       │
                        │           └───────┬────────┘  └──────────────┘
                        │                   │ GEOADD history
                        │                   ▼
                        │           ┌────────────────┐
                        │           │   Cassandra    │
                        │           │ partner_loca-  │
                        │           │ tion_history   │
                        │           └────────────────┘
                        │
                ┌───────▼────────┐
                │     MySQL      │
                │ orders/items   │
                │ restaurants    │
                │ users/payments │
                └───────┬────────┘
                        │
                ┌───────▼────────────────────────────────────────────────┐
                │                    Kafka                                │
                │  Topics: order-placed, order-accepted, partner-assigned │
                │           partner-location-update, order-delivered      │
                └───────┬──────────────────────────────┬─────────────────┘
                        │                              │
               ┌────────▼────────┐           ┌────────▼────────┐
               │  Notification   │           │  SSE Push       │
               │  Service        │           │  Service        │
               │  (FCM/APNs/SMS) │           │  (order track   │
               └─────────────────┘           │   stream →      │
                                             │   customer app) │
                                             └─────────────────┘
```

---

> **► DRAW THIS on the whiteboard ◄**

## SEQUENCE DIAGRAM — FOOD ORDER PLACEMENT AND DELIVERY

```
  Customer App  Order Service  Redis GEO   Restaurant App  Partner App   Kafka
      │               │            │               │             │          │
      │ POST /orders  │            │               │             │          │
      │ {items[],addr}│            │               │             │          │
      │──────────────▶│            │               │             │          │
      │               │ INSERT order              │             │          │
      │               │ status=PLACED             │             │          │
      │               │            │               │             │          │
      │               │ GEORADIUS restaurant_lat   │             │          │
      │               │  restaurant_lon 5km        │             │          │
      │               │ → available partners       │             │          │
      │               │───────────▶│               │             │          │
      │               │◀───────────│               │             │          │
      │               │ [partnerId1,2,3]           │             │          │
      │               │            │               │             │          │
      │ 201 {orderId, │            │               │             │          │
      │  status:PLACED│            │               │             │          │
      │  eta: 35min}  │            │               │             │          │
      │◀──────────────│            │               │             │          │
      │               │            │               │             │          │
      │               │ publish order.placed event │             │          │
      │               │──────────────────────────────────────────────────▶ │
      │               │            │               │             │          │
      │               │ push order to restaurant   │             │          │
      │               │────────────────────────────▶             │          │
      │               │            │               │             │          │
      │               │            │ ACCEPT + prep_time=20min    │          │
      │               │◀───────────────────────────│             │          │
      │               │            │               │             │          │
      │               │ offer order to nearest partner            │          │
      │               │────────────────────────────────────────▶ │          │
      │               │            │               │             │          │
      │               │            │               │ ACCEPT      │          │
      │               │◀────────────────────────────────────────│          │
      │               │            │               │             │          │
      │               │ UPDATE order status=PARTNER_ASSIGNED     │          │
      │               │            │               │             │          │
      │ SSE update:   │            │               │             │          │
      │ partner_name, │            │               │             │          │
      │ partner_loc,  │            │               │             │          │
      │ eta_updated   │            │               │             │          │
      │◀──────────────│            │               │             │          │
```

---

## STEP 6 — Database Schema

► DRAW THIS ◄

```
┌─────────────────────────────────────────────────────────────────────────┐
│                             MYSQL SCHEMA                                 │
└─────────────────────────────────────────────────────────────────────────┘

restaurants
┌──────────────────┬───────────────────────────────────────────────────────┐
│ restaurant_id    │ BIGINT PK AUTO_INCREMENT                              │
│ name             │ VARCHAR(200)                                          │
│ city             │ VARCHAR(100)                                          │
│ lat              │ FLOAT                                                 │
│ lon              │ FLOAT                                                 │
│ avg_rating       │ FLOAT  (updated async, eventually consistent)         │
│ cuisine_tags     │ JSON  ['indian','chinese','pizza']                    │
│ is_open          │ BOOLEAN  (refreshed from operating_hours schedule)    │
│ avg_prep_minutes │ INT  (used in ETA calculation)                        │
│ delivery_radius_m│ INT  (meters, delivery zone radius)                   │
└──────────────────┴───────────────────────────────────────────────────────┘

menu_items
┌──────────────────┬───────────────────────────────────────────────────────┐
│ menu_item_id     │ BIGINT PK AUTO_INCREMENT                              │
│ restaurant_id    │ BIGINT FK → restaurants                               │
│ name             │ VARCHAR(200)                                          │
│ description      │ TEXT                                                  │
│ category         │ VARCHAR(100)  (e.g. "Starters", "Main Course")       │
│ price            │ BIGINT  (paise, e.g. 34900 = Rs 349)                 │
│ is_available     │ BOOLEAN  (restaurant marks OOS in real-time)          │
│ image_url        │ TEXT  (S3 URL)                                        │
└──────────────────┴───────────────────────────────────────────────────────┘

orders  ← CORE TABLE
┌──────────────────────┬─────────────────────────────────────────────────┐
│ order_id             │ CHAR(36) PK  (UUID)                             │
│ customer_id          │ BIGINT FK                                        │
│ restaurant_id        │ BIGINT FK                                        │
│ partner_id           │ BIGINT FK NULL  (null until assigned)            │
│ status               │ ENUM('PLACED','RESTAURANT_ACCEPTED','PREPARING', │
│                      │      'PARTNER_ASSIGNED','PICKED_UP',            │
│                      │      'OUT_FOR_DELIVERY','DELIVERED','CANCELLED') │
│ total_amount         │ BIGINT  (paise)                                  │
│ delivery_address     │ JSON  {street, lat, lon, instructions}           │
│ delivery_fee         │ BIGINT                                           │
│ surge_multiplier     │ DECIMAL(3,2)  (1.00 = no surge, 1.50 = surge)   │
│ estimated_delivery   │ TIMESTAMP                                        │
│ actual_delivery      │ TIMESTAMP NULL                                   │
│ created_at           │ TIMESTAMP DEFAULT NOW()                         │
│ INDEX                │ (restaurant_id, created_at)                     │
│ INDEX                │ (partner_id, created_at)                        │
│ INDEX                │ (customer_id, created_at)                       │
└──────────────────────┴─────────────────────────────────────────────────┘

order_items
┌──────────────────┬───────────────────────────────────────────────────────┐
│ order_item_id    │ BIGINT PK AUTO_INCREMENT                              │
│ order_id         │ CHAR(36) FK → orders                                 │
│ menu_item_id     │ BIGINT FK → menu_items                               │
│ name_snapshot    │ VARCHAR(200)  (copy at order time, menu may change)   │
│ quantity         │ INT                                                   │
│ unit_price       │ BIGINT  (price at order time, not current price)     │
└──────────────────┴───────────────────────────────────────────────────────┘

delivery_partners
┌──────────────────┬───────────────────────────────────────────────────────┐
│ partner_id       │ BIGINT PK AUTO_INCREMENT                              │
│ name             │ VARCHAR(200)                                          │
│ phone            │ VARCHAR(20) UNIQUE                                    │
│ vehicle_type     │ ENUM('BICYCLE','MOTORCYCLE','CAR')                   │
│ current_status   │ ENUM('OFFLINE','ONLINE','BUSY')                      │
│ avg_rating       │ FLOAT                                                 │
│ city             │ VARCHAR(100)  (home city — for Redis shard routing)   │
└──────────────────┴───────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CASSANDRA SCHEMA                                │
└─────────────────────────────────────────────────────────────────────────┘

partner_location_history
  PRIMARY KEY: (partner_id, recorded_at DESC)
  Columns: lat FLOAT, lon FLOAT, speed_kmph FLOAT
  → Query: "Show all locations of partner 123 between 12pm-1pm" 
     SELECT * WHERE partner_id=123 AND recorded_at > '12:00' AND recorded_at < '13:00'
  → Retention: 30 days (TTL per row: 30 * 86400 seconds)

order_status_events  (event sourcing log)
  PRIMARY KEY: (order_id, event_time DESC)
  Columns: status ENUM, actor_id BIGINT, notes TEXT
  → Query: "Full audit log of order 456"
     SELECT * WHERE order_id='456' ORDER BY event_time ASC
```

---

> **► DRAW THIS on the whiteboard ◄**

## ER RELATIONSHIP DIAGRAM

```
┌────────────────────────────────────────────────────────────────────┐
│               ZOMATO / FOOD DELIVERY — ENTITY RELATIONSHIP          │
└────────────────────────────────────────────────────────────────────┘

┌──────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│    users     │   │    restaurants       │   │  delivery_partners  │
│   (MySQL)    │   │      (MySQL)         │   │      (MySQL)         │
├──────────────┤   ├─────────────────────┤   ├─────────────────────┤
│ PK user_id   │   │ PK restaurant_id    │   │ PK partner_id UUID  │
│    name TEXT │   │    name VARCHAR     │   │    name VARCHAR     │
│    phone TEXT│   │    city VARCHAR     │   │    vehicle_type     │
│    addresses │   │    lat FLOAT        │   │    status ENUM      │
│    created_at│   │    lon FLOAT        │   │  ← ONLINE/BUSY/OFF  │
└──────┬───────┘   │    avg_rating FLOAT │   │    rating FLOAT     │
       │ 1         │    prep_time_min INT│   └──────────┬──────────┘
       │ N         │    is_open BOOLEAN  │              │
┌──────▼───────┐   └──────────┬──────────┘             │
│    orders    │              │ 1                        │
│   (MySQL)    │              │ N                        │
├──────────────┤   ┌──────────▼──────────┐              │
│ PK order_id  │   │     menu_items       │              │
│ FK user_id   │   │       (MySQL)        │              │
│ FK restaurant│◄──┤ PK item_id UUID     │ ← N          │
│ FK partner_id├───┘ FK restaurant_id    │              │
│    status ENUM│      name VARCHAR      │              │
│    total BIGINT      price BIGINT      │              │
│    delivery_addr     category VARCHAR  │              │
│    created_at │      is_available BOOL │              │
└──────┬───────┘   └─────────────────────┘              │
       │ 1                                               │
       │ N                                               │
┌──────▼─────────────┐                                  │
│    order_items      │       Redis GEO + Keys           │
│      (MySQL)        │  ┌────────────────────────────┐  │
├─────────────────────┤  │ delivery_partners GEORADIUS │  │
│ PK order_item_id   │  │ score:partner:{id} status  │  │
│ FK order_id UUID   │  │ order:{orderId}:status     │  │
│ FK item_id  UUID   │  │ session:{userId}           │  │
│    quantity INT    │  └────────────────────────────┘  │
│    unit_price BIGINT│                                  │
└─────────────────────┘                                  │
```

---

> **WHY ORDER STATE MACHINE EXISTS? (Beginner Explanation)**
>   Think of a hospital patient's journey: Admitted → Diagnosed → In Surgery → Recovery → Discharged.
>   You cannot discharge a patient who has not been admitted. Same logic for a food order: you cannot
>   mark an order DELIVERED before a partner has PICKED_UP the food. The state machine enforces the
>   legal sequence of transitions. Without it, a bug could jump an order from PLACED to DELIVERED —
>   money charged but no food sent. Each state also controls what actions are allowed: cancellations
>   are free before PREPARING, impossible after PICKED_UP. The state tells every actor (customer,
>   restaurant, partner app) what to display and which buttons to show at each moment.
>   Without a state machine: a raw "status" text field with no enforced transitions — any code could
>   write any value, no audit trail, impossible to debug "how did this order end up in this state?"

> **WHY RESTAURANT MATCHING USES ELASTICSEARCH? (Beginner Explanation)**
>   When a customer types "Indian food near me," the system needs to rank 200K restaurants by three
>   things simultaneously: how close they are (geo distance), how well they match "Indian" (text
>   relevance), and whether they are currently open (filter). MySQL LIKE queries handle text but have
>   no concept of geographic distance scoring. PostGIS handles geography but is slow for full-text
>   ranking. Elasticsearch combines both in one query — geo_distance filter narrows to restaurants
>   within 5km, then text scoring ranks by cuisine match + rating, in under 50ms for 200K restaurants.
>   Think of it as Google Maps for restaurants: the closest AND most relevant result wins, not just
>   the closest or just the most popular.

> **WHY GEOHASH FOR LOCATION INDEXING? (Beginner Explanation)**
>   Imagine Mumbai divided into a grid of 150m × 150m squares, each labeled with a short code (the
>   geohash). To find riders near a restaurant in Bandra, you look up riders whose geohash cell matches
>   — instead of computing distance from that restaurant to every one of 500K rider coordinates.
>   Nearby locations share a common geohash prefix (like how postal codes narrow by prefix: 400050
>   is always closer to 400051 than to 110001). Redis GEO encodes all coordinates as geohash under
>   the hood, giving O(log N) proximity search instead of O(N) brute-force. Without geohash, finding
>   the nearest rider means 500K individual distance calculations per order — each requiring a square
>   root over lat/lon differences — hundreds of milliseconds vs. under 1ms with geohash indexing.

> **WHY DELIVERY PARTNER ASSIGNMENT WORKS THIS WAY? (Beginner Explanation)**
>   Think of it like a taxi dispatch: call the nearest available cab first, not a random one, not the
>   highest-rated one. Speed matters most for a hungry customer — a 4.9-star rider 8km away is worse
>   than a 4.3-star rider 1km away. The nearest partner minimizes both pickup time (restaurant to
>   partner) and total delivery time. The 30-second offer window prevents one distracted partner from
>   blocking the order — if they don't respond, the system immediately moves to the next nearest.
>   Expanding the radius 5km → 7km → 10km is the escalation fallback, like calling a wider taxi pool
>   during heavy rain. Dispatching offers one-by-one (nearest first) avoids two partners racing to
>   the same restaurant pickup simultaneously, which would waste one partner's trip.

## STEP 7 — Deep Dive: Partner Assignment Flow

"This is the most complex algorithmic part. Let me walk through it precisely."

► DRAW THIS ◄

```
┌─────────────────────────────────────────────────────────────────────────┐
│              DELIVERY PARTNER ASSIGNMENT ALGORITHM                       │
└─────────────────────────────────────────────────────────────────────────┘

  Trigger: Restaurant marks order RESTAURANT_ACCEPTED
       │
       ▼
  Assignment Service receives Kafka event: { order_id, restaurant_lat, restaurant_lon }
       │
       ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  STEP 1: Find nearby ONLINE partners                            │
  │                                                                 │
  │  GEORADIUS delivery_partners {rest_lon} {rest_lat} 5 km        │
  │           ASC COUNT 20 WITHCOORD                               │
  │                                                                 │
  │  → Returns: [(partner_id, distance_km, lon, lat), ...]         │
  │    sorted by distance (nearest first)                          │
  └──────────────────────────────┬──────────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  STEP 2: Filter to ONLINE partners                              │
  │                                                                 │
  │  For each partner_id in GEORADIUS result:                      │
  │    Check MySQL/Redis: delivery_partners WHERE                   │
  │    partner_id IN (...) AND current_status = 'ONLINE'           │
  │                                                                 │
  │  → Take first 5 ONLINE partners (sorted by distance)           │
  └──────────────────────────────┬──────────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  STEP 3: Dispatch offer (nearest first)                         │
  │                                                                 │
  │  WebSocket push to partner_1:                                   │
  │  { type: "ORDER_OFFER", order_id, restaurant_name,             │
  │    distance_km: 1.2, delivery_fee: 50, timeout_sec: 30 }       │
  │                                                                 │
  │  Start 30-second timer                                          │
  └──────────────────────────────┬──────────────────────────────────┘
                                 │
                          ┌──────▼──────┐
                          │  Partner    │
                          │  accepts?   │
                          └──────┬──────┘
               ┌─────────────────┼──────────────────┐
               │ YES             │                  │ NO / timeout
               ▼                 │                  ▼
  UPDATE orders SET              │         Try next partner in list
  status='PARTNER_ASSIGNED',     │         (partner_2, partner_3...)
  partner_id=?                   │
  Kafka: partner-assigned event  │         If all 5 rejected:
  Notify customer via SSE        │           Expand radius to 7km
  Partner status → BUSY          │           Repeat search
                                 │
                                 │         If still no one: 10km
                                 │
                                 │         If still no one after
                                 │         5 min: notify customer
                                 │         "no partners available"
                                 └─────────────────────────────────
```

---

> **WHY REAL-TIME TRACKING USES SSE (NOT HTTP POLLING)? (Beginner Explanation)**
>   SSE is a phone call you leave open — the server speaks whenever something new happens. HTTP polling
>   is knocking on the door every 5 seconds asking "any update?" At 500K active orders, polling means
>   500K HTTP requests every 5 seconds = 100K requests/sec just to answer "no update yet." Each request
>   needs a full TCP handshake, auth header processing, and a "nothing changed" 304 response. With SSE,
>   the connection is already open — the server pushes only when the partner actually moves, zero wasted
>   requests. For the partner app, WebSocket is used instead of SSE because it is a two-way conversation:
>   partners both SEND (GPS coordinates every 5 sec) AND RECEIVE (dispatch notifications) on the same
>   connection. SSE is one-directional server → client only, which is exactly what order tracking needs
>   from the customer side — simpler, lighter, and reconnects automatically on mobile network switches.

## STEP 7B — Real-Time Order Tracking

"Customer wants to see the delivery partner moving on a map. Here's the data flow:"

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    REAL-TIME TRACKING DATA FLOW                          │
└─────────────────────────────────────────────────────────────────────────┘

  Partner App (every 5 seconds):
    WebSocket → Location Service → GEOADD delivery_partners lon lat partnerId
                                 → Cassandra INSERT location_history
                                 → Kafka PRODUCE: partner-location-update
                                   { partner_id, order_id, lat, lon }

  Kafka Consumer (SSE Push Service):
    Consumes: partner-location-update
    Finds: active SSE connections for orders assigned to this partner
    Pushes via SSE:
      data: {"type":"location","lat":19.07,"lon":72.87,"eta_min":12}

  Customer App:
    Has SSE connection: GET /orders/{orderId}/track
    Receives location event every ~5 seconds
    Updates partner pin on map
    Keeps SSE open until status=DELIVERED
```

---

## STEP 8 — Scalability

**BOTTLENECK 1: 100K Partner GPS Updates Per Second**

"500K active partners × 1 update every 5 seconds = 100K GEOADD ops/sec. A single Redis instance handles ~100K ops/sec. But I'd shard by city: Mumbai partners → Mumbai Redis, Delhi → Delhi Redis, Bangalore → Bangalore Redis. Each city Redis instance handles 5K-20K partners depending on size. This also makes GEORADIUS efficient — restaurant in Mumbai only queries Mumbai Redis."

**BOTTLENECK 2: Peak Lunch Orders (12pm-1pm)**

"Peak 500 orders/sec × 5 state transitions each = 2,500 MySQL writes/sec plus Kafka events. MySQL handles 5K TPS on a well-tuned instance. For orders older than 7 days, archive to cold storage (S3 Parquet). Active orders table stays small and fast. Read replicas serve all GET /orders queries."

**BOTTLENECK 3: Restaurant Menu Cache**

"200K restaurants × average 50 menu items = 10M menu items. All read-heavy. Redis cache with restaurant:menu:{restaurantId} key. TTL: 30 minutes. Cache invalidated via Kafka event when restaurant updates menu. 99% of menu reads served from Redis — zero DB load for menu display."

> **WHY CACHE THE MENU IN REDIS? (Beginner Explanation)**
>   A restaurant's menu changes at most a few times a month. But customers browse it thousands of
>   times a day. At 10K restaurant searches/sec with average 3 menu views per session, that's 30K
>   MySQL reads/sec hitting the same rows over and over — the same Butter Chicken row, fetched 10K
>   times an hour, unchanged. Redis menu cache is like the laminated menu card already on the table
>   when you sit down — you don't ask the chef to recite it from memory every time a new customer
>   arrives. TTL of 30 minutes means acceptable staleness (a menu price rarely changes mid-service).
>   When a restaurant DOES update their menu, a Kafka event triggers explicit cache invalidation so
>   the next read fetches fresh data from MySQL. Result: 99% of menu reads never touch the database.

**BOTTLENECK 4: SSE Connections at Scale**

"500K concurrent order trackings = 500K open SSE connections. HTTP/2 multiplexing helps but still needs horizontal scaling. SSE Push Service pods scaled to maintain 50K connections each (10 pods for 500K). Kafka consumer group ensures each event goes to the right pod. Sticky sessions via consistent hashing on order_id to SSE pod."

---

## STEP 8 — TRADE-OFFS

*"Let me walk through the key architectural trade-offs I made and why."*

```
┌─────────────────────────────┬────────────────────────────┬──────────────────────────────────────────────────────────┐
│ DECISION                    │ CHOICE MADE                │ TRADE-OFF                                                │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Partner location store      │ Redis GEO (GEORADIUS)      │ Sub-ms geospatial query, 100K updates/sec vs. not        │
│                             │                            │ durable (loss OK — partner sends next GPS in 5s)         │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Location update frequency   │ Every 5 seconds            │ Low bandwidth, low Redis write load vs. ETA accuracy     │
│                             │                            │ degrades slightly                                        │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Assignment algorithm        │ Nearest available (5km)    │ Simple, predictable delivery time vs. doesn't optimize   │
│                             │                            │ for batch routing (multiple orders to same restaurant)   │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Order tracking to customer  │ SSE (Server-Sent Events)   │ Unidirectional push, lower overhead than WebSocket vs.   │
│                             │                            │ requires reconnect on mobile network switch              │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Restaurant notification     │ WebSocket push             │ Real-time order acceptance vs. fallback needed if        │
│                             │                            │ tablet offline (SMS backup required)                     │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Search (restaurants)        │ Elasticsearch              │ Full-text + geo_distance in one query vs. eventual       │
│                             │                            │ consistency (new restaurants take minutes to appear)     │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Surge pricing               │ Redis geohash-7 cells      │ O(1) read per order, per-area granularity vs. cell size  │
│                             │                            │ mismatch (150m cell too coarse for dense areas)          │
└─────────────────────────────┴────────────────────────────┴──────────────────────────────────────────────────────────┘
```

*"The most interesting trade-off is SSE vs WebSocket for order tracking. WebSocket is bidirectional but overkill — customers only receive location updates, they never need to send data back during tracking. SSE is simpler, uses plain HTTP, and reconnects automatically. For the partner app though, we DO need WebSocket because partners both receive orders AND send location updates."*

---

## WHAT NOT TO SAY ✗

- ✗ "I'll poll the database every 5 seconds for partner location" — at 500K concurrent orders, that's 500K DB queries every 5 sec = 100K DB reads/sec. Never poll DB for real-time location. Use Redis GEO + Kafka push.
- ✗ "I'll use MySQL geometry types for partner location" — MySQL geometry is fine for static data (delivery zone polygons). Terrible for 100K high-frequency moving object updates/sec.
- ✗ "The order table stores the entire item list as a JSON column" — you lose the ability to query 'all orders containing item X' for analytics. Separate order_items table is mandatory. JSON column for denormalized snapshot is a secondary optimization.
- ✗ "I'll use HTTP polling on the partner app to get new order dispatches" — partner app needs to poll every few seconds if using HTTP. With 500K partners each polling every 3 sec = 167K requests/sec just for "any orders for me?" — catastrophic. Use persistent WebSocket connection.
- ✗ "Surge pricing is just a multiplier stored in the DB" — reading DB on every order creation adds latency to critical path. Surge multiplier must be in Redis, updated by a background worker, read in <1ms.
- ✗ "I'll compute ETA as distance / average speed" — ETA needs real traffic data (Google Maps Distance Matrix API), restaurant prep time, historical partner speed. Pure distance calculation gives terrible estimates that erode user trust.
- ✗ "I'll use a single Redis instance for all of India" — 100K GEOADD/sec + 10K GEORADIUS/sec on a single Redis is risky for availability. Shard by city/region. Also: single point of failure for entire country.

---

> **WHY ETA IS NOT JUST DISTANCE / SPEED? (Beginner Explanation)**
>   "ETA = distance ÷ average speed" works on a highway at 2am. In Bangalore at noon, it gives wildly
>   wrong answers and destroys user trust. Real ETA is a sum of three separate legs: (1) remaining
>   restaurant prep time — the kitchen may not have started cooking yet; (2) partner travel time from
>   their current location to the restaurant (pickup leg); (3) partner travel time from the restaurant
>   to the customer's door (delivery leg). Each leg uses the Google Maps Distance Matrix API for live
>   traffic data, not straight-line distance. A per-partner correction factor applies based on their
>   personal historical delivery speed profile. ETA that's 15 minutes late causes angry support calls;
>   ETA that's 15 minutes early means cold food at an empty door. Accuracy is a product trust issue.

> **WHY SURGE/DYNAMIC DELIVERY FEE EXISTS? (Beginner Explanation)**
>   Imagine 200 people order biryani simultaneously during an IPL final, but only 10 riders are nearby.
>   Without surge pricing: all 200 orders pile onto 10 riders, average delivery time hits 90 minutes,
>   everyone is furious and leaves bad reviews. Surge pricing does two things at once: it discourages
>   price-sensitive customers from ordering right now (smoothing demand), and it pulls offline riders
>   back online because higher earnings make it worth stepping out. The geohash cell is the unit of
>   surge — 150m × 150m zones let the system be surgical: surge in Bandra does not affect Andheri.
>   The multiplier lives in Redis (not the database) so every order reads it in under 1ms on the
>   critical path. A background worker recalculates it every 60 seconds using live demand/supply
>   ratios per cell, so surge appears and disappears automatically as conditions change.

---

## SENIOR TRAP QUESTIONS (15 YOE Level)

### Category 1: Partner Edge Cases

**Q: "A delivery partner picks up the order, then cancels the delivery mid-route. The food is already with the partner. What happens?"**

A: "This is a nightmare scenario and it happens. My state machine handles it: when partner cancels after PICKED_UP state, the order stays in PICKED_UP (food is physically with them). I immediately trigger a re-assignment flow, but this time GEORADIUS is centered on the partner's CURRENT location — not the restaurant — because the partner has the food. The new partner must collect from the current partner's location or in practice: a supervisor is notified, customer gets an apology notification, and a full refund is issued automatically. The cancelled partner's account gets flagged — too many mid-delivery cancellations → account suspension. I track this in a partner_cancellations table."

**Q: "100,000 GPS updates per second — Redis single instance can handle it, but what about the Cassandra write for location history? Cassandra gets 100K inserts/sec too."**

A: "Cassandra is built for exactly this. Wide-column, LSM-tree storage — 100K writes/sec per node is within spec. I'd run a Cassandra cluster of 5-10 nodes for location history, sharded by partner_id (consistent hashing). But I'd also consider: do we need EVERY 5-second location in Cassandra? For dispute resolution ('partner never reached restaurant'), 30-second granularity is sufficient. I'd filter the Kafka stream: Location Service writes to Redis every 5sec (real-time), Cassandra consumer in the Kafka consumer group writes every 30sec (history). Reduces Cassandra write load by 6x to ~17K inserts/sec — much more comfortable."

### Category 2: Consistency and Correctness

**Q: "Two assignment service instances both run GEORADIUS simultaneously for the same order and both try to dispatch to Partner A. Partner A gets two dispatch requests. How do you prevent double assignment?"**

A: "Distributed assignment race condition. My solution: optimistic locking on the assignment step. Before dispatching to a partner, I do an atomic Redis SET: SETNX order_dispatch_lock:{orderId} {instanceId} EX 60. Only the instance that wins the lock proceeds with dispatch. The loser sees the key exists and aborts. When the partner accepts, I UPDATE orders SET partner_id=?, status='PARTNER_ASSIGNED' WHERE order_id=? AND status='PREPARING' AND partner_id IS NULL. The WHERE clause is the safety net — if two instances somehow both try to write, only one UPDATE gets rows_affected=1. The other sees rows_affected=0 and rolls back. Defense in depth: Redis lock as primary, MySQL conditional UPDATE as fallback."

**Q: "Restaurant rejects an order 4 minutes after it was placed. The customer's payment has already been captured. How does the refund flow work?"**

A: "Order cancellation with payment refund. Flow: Restaurant sends reject → Order Service sets status=CANCELLED → publishes Kafka event order-cancelled. Payment Service consumes: queries payments table for order_id, calls Stripe refund API with the original payment_intent_id, updates payment.status='REFUNDED'. Kafka event: payment-refunded → Notification Service sends customer: 'Restaurant couldn't accept your order. Full refund in 3-5 business days.' The refund is async but the notification is immediate so the customer knows. I also increment restaurant's rejection_rate metric — too high → restaurant gets flagged or temporarily suspended from the platform."

### Category 3: Geo and Surge Pricing

**Q: "Explain how you'd implement surge pricing. Walk me through from the data model to the API response."**

A: "Surge pricing is a per-cell demand/supply ratio calculation. Here's the full flow:

Step 1 — Geohash partitioning: I encode the restaurant's lat/lon into a 7-character geohash (≈ 150m × 150m cell). Each order creation and each partner location update is tagged with its geohash-7.

Step 2 — Demand/supply calculator: a background worker (runs every 60 seconds) for each active geohash cell calculates: demand = orders placed in cell in last 10 min; supply = ONLINE partners currently in cell. Ratio = demand / supply. If ratio > 2.0: multiplier = 1.5x. If ratio > 3.0: multiplier = 2.0x.

Step 3 — Redis store: SETEX surge:{geohash7} 120 1.5 — expires after 2 minutes so stale surges auto-clear.

Step 4 — Order creation: when customer places order, I compute geohash-7 of their delivery address, GET surge:{geohash7} from Redis (< 1ms), apply multiplier to delivery_fee. Store surge_multiplier on the order row.

Step 5 — UI: in the restaurant search results, I show 'Surge pricing: 1.5x' badge on delivery fee to inform customer before they order. This is the same Redis GET, served at the search layer."

---

## KEY NUMBERS

```
┌────────────────────────────────────┬──────────────────────────────────────────┐
│ METRIC                             │ VALUE / NOTES                            │
├────────────────────────────────────┼──────────────────────────────────────────┤
│ Orders/month                       │ 100 million                              │
│ Orders/sec (peak, lunch)           │ 500/sec                                  │
│ Active delivery partners           │ 500,000 (peak India)                     │
│ GPS update frequency               │ Every 5 seconds per partner              │
│ GPS updates/sec (total)            │ 100,000 ops/sec                          │
│ Redis GEO entry size               │ ~50 bytes (lon+lat+member)               │
│ 500K partners in Redis             │ ~25 MB (fits in single instance memory)  │
│ GEORADIUS query time               │ O(N + log M), typically < 1ms            │
│ Geohash-7 cell size                │ ~153m × 153m                             │
│ Partner assignment timeout         │ 30 sec per partner, max 3 attempts       │
│ Radius expansion                   │ 5km → 7km → 10km before giving up       │
│ SSE connection timeout             │ Auto-reconnect, open until DELIVERED     │
│ Redis shard count                  │ 1 per major metro city (Mumbai/Delhi...) │
│ Cassandra location retention       │ 30 days (TTL)                            │
│ Menu cache TTL                     │ 30 minutes                               │
│ Surge calculator interval          │ Every 60 seconds                         │
└────────────────────────────────────┴──────────────────────────────────────────┘
```

---

## KEY PATTERNS REFERENCED IN THIS DESIGN

> **For the 2-year developer:** These are the hidden concepts behind design decisions in this system. Each has a dedicated deep-dive file.

### N+1 Query Problem
**Why it matters here:** Restaurant listing loads 50 restaurants → ORM fetches each restaurant's menu categories → 51 queries. @EntityGraph or JOIN FETCH reduces to 1 query. Critical for home screen load performance.
**Deep dive:** `../../N_Plus_1_Query_Problem.md`

### Saga Pattern
**Why it matters here:** Order placed → payment charged → restaurant confirmed → driver assigned. If restaurant rejects: cancel payment (compensating tx), release driver. Choreography saga via Kafka events.
**Deep dive:** `../../Saga_Pattern_Choreography_vs_Orchestration.md`

### Two-Phase Commit (2PC)
**Why it matters here:** Why NOT 2PC — placing an order across payment service + restaurant service + driver service using 2PC is too slow and has blocking failure modes. Saga is the answer, but knowing 2PC explains why.
**Deep dive:** `../../Two_Phase_Commit_2PC_Distributed_Transactions.md`

### Circuit Breaker
**Why it matters here:** Order service calls restaurant confirmation API. Restaurant's system is down. Circuit OPEN: auto-accept order, notify restaurant via SMS fallback. Users see "Order placed" immediately.
**Deep dive:** `../../Circuit_Breaker_Pattern.md`

### Retry + Exponential Backoff + Jitter
**Why it matters here:** Restaurant API returns 503. 50 simultaneous failed requests retry with full jitter — smooth retry load vs synchronous spikes every 4s.
**Deep dive:** `../../Retry_Exponential_Backoff_Jitter.md`

### Bulkhead Pattern
**Why it matters here:** Driver assignment pool isolated from notification pool. Notification service goes down → driver assignment unaffected. Order is placed and driver assigned; notification fails silently.
**Deep dive:** `../../Bulkhead_Pattern_Isolate_Failures.md`

### Timeout Strategy
**Why it matters here:** Restaurant confirmation API: 3s total timeout. If restaurant doesn't confirm in 3s → auto-accept. Deadline propagated: parent request (5s total) leaves 3s for restaurant call.
**Deep dive:** `../../Timeout_Strategy_Too_Short_Too_Long.md`

### CAP Theorem
**Why it matters here:** AP for delivery tracking (stale driver position by 3s is fine). CP for payment (no double-charge during partition). Different subsystems in the same product make different CAP choices.
**Deep dive:** `../../CAP_Theorem_Applied_What_Actually_Breaks.md`

### [Cache-Aside vs Write-Through vs Write-Behind](../../Cache_Aside_vs_Write_Through_vs_Write_Behind.md)
**Why this system uses it:** Restaurant menu cache uses cache-aside with 5-minute TTL — menus change infrequently, reads are very frequent (every user browsing). On cache miss: fetch from DB, populate cache. On menu update by restaurant: invalidate cache key immediately (don't wait for TTL). Order status uses write-through — write to DB + update Redis cache atomically so "track your order" always shows current status without a cache miss.

### [Kafka vs RabbitMQ vs SQS](../../Kafka_vs_RabbitMQ_vs_SQS_When_to_Use_Which.md)
**Why this system uses it:** Order events use Kafka for high throughput and replay (debug failed orders by replaying from any offset). Restaurant notification uses RabbitMQ or SQS — simple push-to-restaurant-queue semantics: each restaurant has its own queue, and the ordering service sends directly to the restaurant's queue. This is direct routing, not broadcast — RabbitMQ direct exchange handles it cleanly. SQS alternative if on AWS: one SQS queue per restaurant, Lambda trigger for notification.

### [Geohash vs QuadTree Map Partitioning](../../Geohash_vs_QuadTree_Map_Partitioning.md)
**Why this system uses it:** "Find restaurants within your delivery radius" is a spatial query. PostgreSQL PostGIS with GiST index on restaurant `location` column: `ST_DWithin(restaurant.location, user.location, 5000)` (5km radius). For real-time driver tracking (delivery agent location): Redis GEOADD/GEORADIUS same as UBER — agent updates location every 10s, user sees agent on map via Redis spatial query.

### [Long-Tail Latency — P99](../../Long_Tail_Latency_P99_Percentiles.md)
**Why this system uses it:** Order placement P99 affects driver assignment speed. If 1% of order placements take 3 seconds, those drivers sit idle while the order waits. Root cause: restaurant availability check queries hitting a slow DB replica. Fix: add hedged requests — if the restaurant DB query doesn't return in 100ms (P95), send a duplicate query to a second replica and use whichever responds first. This cuts P99 to roughly P95 at ~2% extra DB load. Monitor P99 on the order placement endpoint separately from order status updates.

### [Backpressure & Reactive Streams](../../Backpressure_Reactive_Streams.md)
**Why this system uses it:** Lunch rush (12-2pm) generates 10x normal order volume. Order processing pipeline: order placed → restaurant notified → driver assigned → order tracked. Each step has a different throughput limit. Kafka between each stage provides natural backpressure: restaurant notification queue may lag during peak, but orders are not lost. Driver assignment service autoscales on Kafka lag metric. During the surge, notifications may be 30 seconds delayed (acceptable) but no orders are dropped.

### [AWS API Gateway — REST vs HTTP vs WebSocket](../../../aws/22.api-gateway-rest-http-websocket-architect-interview.md)
**Why this system uses it:** Order placement uses the 29s async pattern: POST /orders returns orderId instantly, order processing (restaurant confirmation, payment, driver dispatch) continues asynchronously. REST API with Usage Plans for per-restaurant API access tiers. WebSocket API for real-time order status push to customer app (order accepted → driver assigned → picked up → delivered).

### [Kinesis vs MSK Kafka vs SQS — Streaming Decision](../../../aws/23.kinesis-vs-msk-kafka-vs-sqs-streaming-decision.md)
**Why this system uses it:** Order events use SQS FIFO (`MessageGroupId=orderId`) — ordered state transitions (PLACED → CONFIRMED → PREPARING → PICKED → DELIVERED) with exactly-once processing. Driver location stream uses Kinesis (`partitionKey=driverId`). Order placed → SNS → multiple SQS queues (inventory service, notification service, analytics) for fan-out. Kinesis Firehose → S3 for order analytics pipeline.

### [CloudWatch + X-Ray Observability](../../../aws/24.cloudwatch-xray-observability-architect-interview.md)
**Why this system uses it:** Custom business metrics: OrderToDeliveryTime (P99), RestaurantAcceptanceRate, DriverAssignmentLatency. P99 alarm: if order-to-driver-assignment > 30s → alert → auto-scale driver dispatch service. X-Ray service map traces: API GW → Order Service → Restaurant Service → Driver Service — when user complains about slow order confirmation, X-Ray shows whether the bottleneck is restaurant API timeout or driver pool exhaustion. Container Insights on EKS: detect which pod is OOMKilling during lunch peak.

### [WAF + Shield + GuardDuty](../../../aws/27.waf-shield-guardduty-security-architect-interview.md)
**Why this system uses it:** Food delivery platforms face promo-abuse attacks — bots creating fake accounts for first-order discounts. WAF rate-based rule: block IPs making > 10 account creation requests/minute. AWSManagedRulesCommonRuleSet blocks SQLi attempts on menu/order search. GuardDuty detects compromised driver accounts (driver app suddenly calling crypto mining endpoints). Shield Standard for DDoS protection during marketing campaigns (peak traffic 10x normal).

### [KMS Envelope Encryption + Secrets Manager](../../../aws/28.kms-envelope-encryption-secrets-manager-architect-interview.md)
**Why this system uses it:** Restaurant POS integration credentials (20+ restaurant partners) stored in Secrets Manager — one secret per integration, auto-rotated when restaurant resets API keys. Driver location history (PII) encrypted with envelope encryption: DEK per driver per day, CMK in KMS. IRSA: order-service EKS pod fetches DB credentials from Secrets Manager at startup, caches in memory — no kubectl exec can reveal credentials since they're not env vars.
