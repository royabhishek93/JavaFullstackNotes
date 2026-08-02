# Food Delivery Service - High Level Design

## 1. Overview

A food delivery service like Uber Eats or DoorDash connects customers with restaurants and delivery partners to enable seamless food ordering and delivery. The platform handles restaurant onboarding, menu management, order processing, real-time tracking, payment processing, and logistics optimization.

**Key Features:**
- Restaurant discovery and menu browsing
- Real-time order placement and tracking
- Dynamic pricing and delivery fee calculation
- Driver assignment and route optimization
- Multi-party notifications (customer, restaurant, driver)
- Rating and review system
- Payment processing and split settlements
- Promotions and loyalty programs

## 2. Requirements

### 2.1 Functional Requirements

**Core Features:**
1. **User Management**
   - Customer registration and authentication
   - Restaurant partner onboarding
   - Delivery driver onboarding and verification
   - Profile management for all user types

2. **Restaurant & Menu Management**
   - Restaurant listing with search and filters
   - Menu CRUD operations with item availability
   - Restaurant hours and service area management
   - Cuisine categorization

3. **Order Management**
   - Shopping cart functionality
   - Order placement with customization options
   - Real-time order status updates
   - Order modification and cancellation
   - Order history and reordering

4. **Delivery Management**
   - Driver assignment algorithms
   - Real-time location tracking
   - Route optimization
   - Estimated delivery time calculation
   - Proof of delivery

5. **Payment Processing**
   - Multiple payment methods support
   - Split payment to restaurant and platform
   - Driver payouts
   - Refund processing

6. **Notification System**
   - Order confirmations
   - Status updates via push, SMS, email
   - Driver assignment notifications
   - Promotional notifications

7. **Rating & Review System**
   - Rate restaurants, food quality, and delivery
   - Review moderation
   - Aggregate ratings

### 2.2 Non-Functional Requirements

1. **Availability**: 99.99% uptime (critical for order placement)
2. **Scalability**: Handle millions of concurrent users during peak hours
3. **Latency**: 
   - Search results < 500ms
   - Order placement < 2s
   - Location updates < 3s
4. **Consistency**: Strong consistency for orders, eventual for search
5. **Reliability**: No order loss, guaranteed delivery assignment
6. **Security**: PCI-DSS compliance, secure payment processing
7. **Real-time**: Live order tracking with < 5s update intervals

### 2.3 Extended Requirements

- Analytics dashboard for restaurants and platform
- Dynamic pricing based on demand
- Surge pricing during peak hours
- Scheduled orders
- Group ordering
- Subscription models
- Dark kitchen/cloud kitchen support

## 3. Capacity Estimation and Constraints

### 3.1 Traffic Estimates

**Assumptions:**
- 50 million daily active users (DAU)
- Average 2 orders per user per week
- Peak hour traffic: 20% of daily orders
- Order placement: 14 million orders/day

**Calculations:**
- Orders per second (average): 14M / 86400 = ~162 orders/sec
- Orders per second (peak): 162 * 5 = ~810 orders/sec
- Read:Write ratio: 100:1 (browsing vs ordering)
- Search queries: 162 * 100 = ~16,200 QPS

### 3.2 Storage Estimates

**Data per order:**
- Order metadata: 2 KB
- Order items: 1 KB
- Delivery tracking: 5 KB (location updates every 10s)
- Total per order: ~8 KB

**Storage calculation:**
- Daily: 14M * 8 KB = 112 GB/day
- Annual: 112 GB * 365 = ~40 TB/year
- With replication (3x): 120 TB/year

**User data:**
- 100M total users * 5 KB = 500 GB
- Restaurant data: 1M restaurants * 50 KB = 50 GB
- Menu data: 1M restaurants * 100 KB = 100 GB

**Total storage (5 years):** ~600 TB

### 3.3 Bandwidth Estimates

**Incoming:**
- Order placement: 810 orders/sec * 3 KB = 2.4 MB/s
- Location updates: 100K active drivers * 1 KB / 10s = 10 MB/s
- Total: ~15 MB/s

**Outgoing:**
- Search results: 16,200 QPS * 50 KB = 810 MB/s
- Real-time tracking: 1M active orders * 2 KB = 2 GB/s
- Total: ~3 GB/s

## 4. System Architecture

### 4.1 High-Level Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Customer  │         │  Restaurant  │         │   Driver    │
│     App     │         │     App      │         │     App     │
└──────┬──────┘         └──────┬───────┘         └──────┬──────┘
       │                       │                        │
       └───────────────────────┼────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │    API Gateway      │
                    │  (Rate Limiting)    │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
    ┌───────▼────────┐ ┌──────▼──────┐  ┌───────▼────────┐
    │ User Service   │ │Order Service│  │Delivery Service│
    │                │ │             │  │                │
    └───────┬────────┘ └──────┬──────┘  └───────┬────────┘
            │                  │                  │
    ┌───────▼────────┐ ┌──────▼──────┐  ┌───────▼────────┐
    │Restaurant Svc  │ │Payment Svc  │  │ Location Svc   │
    │                │ │             │  │                │
    └───────┬────────┘ └──────┬──────┘  └───────┬────────┘
            │                  │                  │
    ┌───────▼────────┐ ┌──────▼──────┐  ┌───────▼────────┐
    │Notification Svc│ │Analytics Svc│  │   Search Svc   │
    └────────────────┘ └─────────────┘  └────────────────┘
            │                  │                  │
    ┌───────┴──────────────────┴──────────────────┴────────┐
    │              Message Queue (Kafka)                    │
    └───────────────────────────────────────────────────────┘
            │                  │                  │
    ┌───────▼────────┐ ┌──────▼──────┐  ┌───────▼────────┐
    │   PostgreSQL   │ │   MongoDB   │  │     Redis      │
    │   (Orders)     │ │(Restaurants)│  │    (Cache)     │
    └────────────────┘ └─────────────┘  └────────────────┘
            │                  │                  │
    ┌───────▼────────┐ ┌──────▼──────┐  ┌───────▼────────┐
    │  Elasticsearch │ │   Cassandra │  │      S3        │
    │   (Search)     │ │  (Tracking) │  │   (Images)     │
    └────────────────┘ └─────────────┘  └────────────────┘
```

### 4.2 Component Architecture

**Microservices Pattern:**
- Independent service deployment
- Database per service
- API-first design
- Event-driven communication

## 5. Core Components

### 5.1 User Service

**Responsibilities:**
- User authentication and authorization (JWT tokens)
- Profile management for customers, restaurants, drivers
- Address management with geocoding
- Session management

**Technology:**
- Service: Node.js/Go
- Database: PostgreSQL
- Cache: Redis for sessions

### 5.2 Restaurant Service

**Responsibilities:**
- Restaurant CRUD operations
- Menu management with item variants
- Availability and timing management
- Cuisine and category tagging
- Restaurant search indexing

**Technology:**
- Service: Java/Spring Boot
- Database: MongoDB (flexible schema for menus)
- Search: Elasticsearch

### 5.3 Order Service

**Responsibilities:**
- Shopping cart management
- Order placement and validation
- Order state machine management
- Order history and tracking
- Order cancellation and refunds

**Order States:**
```
CART → PLACED → CONFIRMED → PREPARING → 
READY_FOR_PICKUP → PICKED_UP → IN_TRANSIT → 
DELIVERED → COMPLETED
```

**Technology:**
- Service: Java/Spring Boot
- Database: PostgreSQL with ACID guarantees
- Cache: Redis for active orders

### 5.4 Delivery Service

**Responsibilities:**
- Driver onboarding and verification
- Driver availability management
- Order-driver matching algorithm
- Route optimization
- Delivery fee calculation
- Driver performance tracking

**Matching Algorithms:**
1. **Proximity-based**: Nearest available driver
2. **Zone-based**: Drivers assigned to zones
3. **Batch delivery**: Multiple orders per driver
4. **Predictive positioning**: AI-based driver placement

**Technology:**
- Service: Python/Go
- Database: PostgreSQL
- Geospatial: Redis with GeoHash
- Optimization: OR-Tools

### 5.5 Location Service

**Responsibilities:**
- Real-time driver location tracking
- Customer order tracking
- ETA calculation
- Geofencing for delivery zones
- Location history

**Technology:**
- Service: Go (high throughput)
- Database: Cassandra (time-series data)
- Real-time: WebSockets
- Cache: Redis with Geo commands

### 5.6 Payment Service

**Responsibilities:**
- Payment processing via gateways (Stripe, PayPal)
- Payment method management
- Transaction recording
- Split payments (platform fee, restaurant revenue)
- Driver payouts
- Refund processing

**Technology:**
- Service: Java/Spring Boot
- Database: PostgreSQL (transactional)
- Queue: Kafka for async processing
- PCI-DSS compliance

### 5.7 Search Service

**Responsibilities:**
- Restaurant and menu item search
- Filter by cuisine, price, rating, delivery time
- Autocomplete suggestions
- Personalized ranking
- Fuzzy matching

**Ranking Factors:**
- Relevance score
- Restaurant rating
- Delivery time
- User preferences
- Promotional boost

**Technology:**
- Service: Python
- Search Engine: Elasticsearch
- Cache: Redis
- ML: Collaborative filtering

### 5.8 Notification Service

**Responsibilities:**
- Push notifications (FCM, APNs)
- SMS notifications (Twilio)
- Email notifications (SendGrid)
- In-app notifications
- Notification preferences

**Technology:**
- Service: Node.js
- Queue: Kafka
- Database: MongoDB (notification logs)

### 5.9 Analytics Service

**Responsibilities:**
- Real-time metrics (orders, revenue)
- Restaurant performance dashboards
- Driver performance tracking
- Customer behavior analysis
- A/B testing framework

**Technology:**
- Stream Processing: Apache Flink
- Data Warehouse: Snowflake
- Visualization: Tableau/Grafana

## 6. Database Design

### 6.1 User Database (PostgreSQL)

```sql
users
- id (PK)
- email
- phone
- password_hash
- user_type (CUSTOMER, RESTAURANT, DRIVER)
- created_at
- updated_at

addresses
- id (PK)
- user_id (FK)
- latitude
- longitude
- address_line1
- address_line2
- city
- zipcode
- is_default
```

### 6.2 Restaurant Database (MongoDB)

```javascript
restaurants: {
  _id: ObjectId,
  name: String,
  description: String,
  cuisine_types: [String],
  rating: Number,
  total_reviews: Number,
  location: {
    type: "Point",
    coordinates: [longitude, latitude]
  },
  address: Object,
  delivery_areas: [Polygon],
  operating_hours: Object,
  average_delivery_time: Number,
  menu: [
    {
      category: String,
      items: [
        {
          item_id: String,
          name: String,
          description: String,
          price: Number,
          image_url: String,
          is_available: Boolean,
          customizations: [Object]
        }
      ]
    }
  ],
  created_at: Date,
  updated_at: Date
}
```

### 6.3 Order Database (PostgreSQL)

```sql
orders
- id (PK)
- customer_id (FK)
- restaurant_id (FK)
- driver_id (FK)
- delivery_address_id (FK)
- order_status
- subtotal
- tax
- delivery_fee
- discount
- total_amount
- payment_status
- special_instructions
- placed_at
- confirmed_at
- delivered_at

order_items
- id (PK)
- order_id (FK)
- item_id
- item_name
- quantity
- unit_price
- customizations (JSONB)
- subtotal
```

### 6.4 Location Database (Cassandra)

```
driver_locations
- driver_id (Partition Key)
- timestamp (Clustering Key, DESC)
- latitude
- longitude
- bearing
- speed
- accuracy

TTL: 24 hours
```

### 6.5 Caching Strategy (Redis)

```
active_orders:{order_id} → Order JSON (TTL: 2 hours)
restaurant:{id} → Restaurant JSON (TTL: 1 hour)
driver_location:{driver_id} → GeoHash (TTL: 30 sec)
search_results:{query_hash} → Results (TTL: 5 min)
user_session:{token} → User context (TTL: 7 days)
```

## 7. API Design

### 7.1 Restaurant APIs

```
GET /api/v1/restaurants/search
  Query: lat, lng, cuisine, rating_min, delivery_time_max, page
  Response: { restaurants: [...], total, page, page_size }

GET /api/v1/restaurants/{restaurant_id}
  Response: { id, name, menu, rating, delivery_time, ... }

GET /api/v1/restaurants/{restaurant_id}/menu
  Response: { categories: [...], items: [...] }
```

### 7.2 Order APIs

```
POST /api/v1/orders
  Body: { restaurant_id, items: [{item_id, quantity, customizations}], 
          delivery_address_id, payment_method_id }
  Response: { order_id, estimated_delivery_time, total_amount }

GET /api/v1/orders/{order_id}
  Response: { id, status, items, tracking, eta, ... }

PUT /api/v1/orders/{order_id}/cancel
  Body: { cancellation_reason }
  Response: { success, refund_amount }

GET /api/v1/orders/history
  Query: page, status
  Response: { orders: [...], total }
```

### 7.3 Tracking APIs

```
GET /api/v1/orders/{order_id}/track
  Response: { order_status, driver_location: {lat, lng}, 
              eta_minutes, delivery_address }

WebSocket: ws://api/v1/track/{order_id}
  Events: location_update, status_change, eta_update
```

### 7.4 Driver APIs

```
PUT /api/v1/drivers/status
  Body: { status: "AVAILABLE|BUSY|OFFLINE" }
  Response: { success }

POST /api/v1/drivers/location
  Body: { latitude, longitude, timestamp }
  Response: { success }

GET /api/v1/drivers/orders/active
  Response: { orders: [...] }

PUT /api/v1/drivers/orders/{order_id}/pickup
  Body: { verification_code }
  Response: { success, next_destination }

PUT /api/v1/drivers/orders/{order_id}/deliver
  Body: { proof_of_delivery, signature }
  Response: { success, next_order }
```

### 7.5 Payment APIs

```
POST /api/v1/payments/methods
  Body: { type, token, is_default }
  Response: { payment_method_id }

POST /api/v1/payments/process
  Body: { order_id, payment_method_id }
  Response: { transaction_id, status }

POST /api/v1/payments/refund
  Body: { order_id, amount, reason }
  Response: { refund_id, status }
```

## 8. Scalability and Performance

### 8.1 Horizontal Scaling

**Service Layer:**
- Stateless microservices behind load balancers
- Auto-scaling based on CPU/memory metrics
- Kubernetes for orchestration

**Database Layer:**
- PostgreSQL: Master-slave replication, read replicas
- MongoDB: Sharding by restaurant_id
- Cassandra: Partition by driver_id
- Redis Cluster: Consistent hashing

### 8.2 Load Balancing

**Strategy:**
- L7 load balancer (ALB/Nginx)
- Round-robin for stateless services
- Consistent hashing for location service
- Geographic routing for low latency

### 8.3 Caching Strategy

**Multi-level Caching:**
1. **CDN**: Restaurant images, static assets
2. **Application Cache**: Redis for hot data
3. **Database Cache**: Query result caching
4. **Client Cache**: Mobile app local storage

**Cache Invalidation:**
- TTL-based expiration
- Event-driven invalidation (order updates)
- Write-through for critical data

### 8.4 Database Optimization

**Indexing:**
- B-tree index on order_id, user_id, restaurant_id
- GIN index on JSONB columns (customizations)
- Geospatial index for location queries
- Composite index on (status, created_at)

**Partitioning:**
- Range partition orders by created_at (monthly)
- List partition by order_status
- Archive old orders to cold storage

**Connection Pooling:**
- PgBouncer for PostgreSQL
- Connection pool sizing: (cores * 2) + effective_spindle_count

### 8.5 Real-Time System

**WebSocket Architecture:**
- WebSocket gateway cluster
- Sticky sessions via load balancer
- Redis Pub/Sub for message broadcasting
- Heartbeat mechanism for connection health

**Location Update Optimization:**
- Batch location updates (every 10s)
- Geohash-based proximity queries
- Only update if significant position change
- Client-side interpolation for smooth tracking

### 8.6 Fault Tolerance

**Resilience Patterns:**
- Circuit breaker (Hystrix/Resilience4j)
- Retry with exponential backoff
- Bulkhead isolation
- Timeout configuration

**Data Durability:**
- Database replication (sync for orders, async for reads)
- Cross-region backups
- Point-in-time recovery (PITR)
- Event sourcing for order state

## 9. Technology Stack

### 9.1 Backend Services

**Languages & Frameworks:**
- Java/Spring Boot: Order, Payment services (transactional)
- Go: Location, Delivery services (high throughput)
- Python: Search, Analytics, ML services
- Node.js: User, Notification services (I/O intensive)

### 9.2 Databases

**Relational:**
- PostgreSQL: Orders, Users, Transactions
- Features: ACID, JSONB, PostGIS

**NoSQL:**
- MongoDB: Restaurants, Menus (flexible schema)
- Cassandra: Location tracking (time-series)
- Redis: Caching, Session, Pub/Sub

**Search:**
- Elasticsearch: Restaurant and menu search

### 9.3 Message Queue

**Apache Kafka:**
- Order events stream
- Notification events
- Analytics events
- Location updates stream

### 9.4 Infrastructure

**Cloud Platform:** AWS/GCP
- Compute: ECS/EKS for containers
- Storage: S3 for images
- CDN: CloudFront
- Load Balancer: ALB

**Monitoring:**
- Prometheus + Grafana: Metrics
- ELK Stack: Logging
- Jaeger: Distributed tracing
- PagerDuty: Alerting

### 9.5 Mobile/Web

**Frontend:**
- React Native: Mobile apps
- React.js: Web app
- WebSocket: Real-time tracking

**Maps:**
- Google Maps API / Mapbox
- Geocoding and route optimization

## 10. Interview Questions & Answers

### Q1: How do you handle the driver assignment problem efficiently?

**Answer:**
The driver assignment problem is complex with multiple constraints:

**Algorithm:**
1. **Spatial Indexing**: Use Redis GeoHash to find drivers within a radius
2. **Scoring System**:
   - Distance to restaurant: 40% weight
   - Driver rating: 20% weight
   - Current utilization: 20% weight
   - Estimated delivery time: 20% weight
3. **Assignment Flow**:
   - Broadcast to top 5 drivers with 30s timeout
   - First to accept gets the order
   - If timeout, re-broadcast to next batch
   - Emergency fallback: highest-rated driver auto-assigned

**Advanced Optimizations:**
- **Batch Assignment**: Assign multiple orders to one driver for efficiency
- **Predictive Positioning**: ML model predicts demand hotspots, pre-position drivers
- **Dynamic Zones**: Adjust zone boundaries based on real-time demand
- **Wait-time Optimization**: Balance immediate assignment vs. waiting for better driver

**Handling Edge Cases:**
- No available drivers: Increase delivery fee, expand radius, notify customer
- Driver cancellation: Automatic reassignment with penalty
- Restaurant delay: Adjust ETA, notify driver and customer

### Q2: How do you ensure consistency in the order lifecycle across multiple services?

**Answer:**
Order management requires coordination across multiple services (Order, Payment, Restaurant, Delivery, Notification). We use a combination of patterns:

**Saga Pattern (Choreography):**
```
Order Placed → Payment Service (charge)
           → Restaurant Service (notify)
           → Delivery Service (assign driver)
           → Notification Service (send confirmations)
```

**Implementation:**
1. **Event Sourcing**: Store all order state changes as events
2. **Kafka Topics**: 
   - order-events
   - payment-events
   - delivery-events
3. **Compensating Transactions**: Rollback on failure
   - Payment failed → Cancel order → Refund if partial charge
   - Driver not found → Cancel order → Refund payment

**Eventual Consistency:**
- Order service is source of truth
- Other services eventually converge
- Client displays optimistic UI with rollback on failure

**Strong Consistency Where Needed:**
- Payment transactions: Two-phase commit or distributed transaction
- Order status updates: Database transactions with row-level locking

**Idempotency:**
- All APIs are idempotent with request IDs
- Prevents duplicate charges/orders on retry

### Q3: How do you handle real-time location tracking at scale?

**Answer:**
Location tracking for 100K+ active drivers requires careful design:

**Write Path (Location Updates):**
1. **Client Batching**: Mobile app batches updates every 10s
2. **Write Buffer**: Go service receives updates, validates, and buffers
3. **Batch Write**: Write to Cassandra in batches (100 updates/write)
4. **Cache Update**: Update Redis with latest location (GeoHash)
5. **Stream Processing**: Publish to Kafka for analytics and ETA recalculation

**Read Path (Tracking):**
1. **WebSocket Connection**: Customer subscribes to order tracking
2. **Redis Lookup**: Fetch driver's latest location from cache
3. **ETA Calculation**: Based on current location and traffic (Google Maps API)
4. **Push Updates**: Send to customer every 5s via WebSocket

**Optimizations:**
- **Geohash Precision**: Use 6-character geohash (~1km precision)
- **Change Detection**: Only update if driver moved > 50m
- **TTL**: Location data expires after 24 hours
- **Compression**: Use Protocol Buffers for location payloads

**Scalability:**
- Cassandra partitioned by driver_id, clustered by timestamp
- Redis Cluster with geographic sharding
- WebSocket gateway scales horizontally with Redis Pub/Sub

### Q4: How do you design the restaurant search system?

**Answer:**
Search is critical for user experience and requires multi-faceted design:

**Indexing Strategy (Elasticsearch):**
```json
{
  "restaurant_id": "123",
  "name": "Pizza Palace",
  "cuisine_types": ["Italian", "Pizza"],
  "rating": 4.5,
  "total_reviews": 1200,
  "location": { "lat": 37.7749, "lon": -122.4194 },
  "delivery_time": 30,
  "min_order": 10,
  "popular_items": ["Margherita", "Pepperoni"],
  "is_open": true,
  "features": ["delivery", "pickup", "vegetarian"]
}
```

**Query Logic:**
1. **Geospatial Filter**: Restaurants within delivery radius (5km)
2. **Filters**: Cuisine, rating, delivery time, price range
3. **Scoring**:
   - Text relevance (BM25): 30%
   - Rating: 25%
   - Delivery time: 20%
   - Popularity (reviews count): 15%
   - Distance: 10%
4. **Personalization**: Boost based on user's order history

**Performance Optimizations:**
- **Index Sharding**: Shard by city/region
- **Cache**: Redis for popular queries (TTL 5 min)
- **Auto-complete**: Prefix suggester with edge n-grams
- **Real-time Updates**: Background sync every 1 min for availability

**Challenges:**
- **Stale Data**: Restaurant closes but shows as open
  - Solution: Heartbeat from restaurant app, mark offline if no ping in 5 min
- **Cold Start**: New restaurants have low ranking
  - Solution: Boost new restaurants for first 2 weeks

### Q5: How do you handle payment failures and refunds?

**Answer:**
Payment processing is critical and requires robust error handling:

**Payment Flow:**
1. **Validation**: Verify payment method, order total
2. **Pre-authorization**: Hold amount on customer's card
3. **Order Processing**: Wait for restaurant confirmation
4. **Capture**: Capture payment after food is prepared
5. **Settlement**: Split payment (platform fee, restaurant revenue)

**Failure Scenarios:**

**1. Payment Gateway Timeout:**
- Retry with exponential backoff (3 attempts)
- If still fails, try backup payment method
- If all fail, cancel order and notify customer

**2. Insufficient Funds:**
- Immediate failure, no retries
- Notify customer to update payment method
- Hold order for 5 minutes to update

**3. Payment Captured but Order Failed:**
- Automatic refund initiation
- Refund to original payment method
- If refund fails, manual intervention + customer support ticket

**Refund Scenarios:**

**1. Restaurant Cancellation:**
- Full refund including delivery fee
- Priority refund processing (< 1 hour)

**2. Customer Cancellation:**
- Before restaurant confirms: Full refund
- After preparation starts: No refund or partial refund
- After pickup: No refund

**3. Quality Issues:**
- Customer raises issue → CS review → Partial/full refund
- Automatic refund for severe cases (e.g., missing items)

**Implementation:**
- **Idempotency Keys**: Prevent duplicate charges
- **Webhook Handling**: Process payment gateway webhooks asynchronously
- **Reconciliation**: Nightly job to match payments with orders
- **Audit Log**: Every payment state change logged

### Q6: How would you implement surge pricing during peak hours?

**Answer:**
Dynamic pricing balances supply-demand and maximizes platform revenue:

**Surge Pricing Algorithm:**

**Factors:**
1. **Demand**: Current order rate vs. average
2. **Supply**: Available drivers vs. required
3. **Wait Time**: Average wait time for driver assignment
4. **Zone**: Geographic area (city center vs. suburbs)
5. **Time**: Lunch/dinner hours, weekends, events

**Formula:**
```
surge_multiplier = base_multiplier * (1 + demand_factor + supply_factor)

demand_factor = (current_orders - avg_orders) / avg_orders
supply_factor = max(0, (required_drivers - available_drivers) / required_drivers)

surge_multiplier = min(max(surge_multiplier, 1.0), 3.0)  // Cap at 3x
```

**Implementation:**
1. **Real-time Calculation**: Every 5 minutes per zone
2. **Gradual Changes**: Max 0.2x increase per interval (avoid sticker shock)
3. **Notification**: Show surge pricing clearly to customers
4. **A/B Testing**: Test different surge levels for optimization

**Advanced Features:**
- **Predictive Surge**: ML model predicts surge 30 min ahead, pre-position drivers
- **Personalized Pricing**: Loyal customers get lower surge
- **Subscription**: Premium members get capped surge
- **Transparent Display**: Show "High demand in your area, prices increased 1.5x"

**Challenges:**
- **Customer Backlash**: Clear communication, option to schedule for later
- **Driver Gaming**: Drivers going offline to trigger surge
  - Solution: Surge based on accepted orders, not online drivers
- **Restaurant Impact**: Higher fees might reduce orders
  - Solution: Restaurant doesn't bear surge cost, platform absorbs

### Q7: How do you handle data consistency during high-traffic events?

**Answer:**
During events like Super Bowl or NYE, traffic can spike 10x:

**Preparation:**
1. **Capacity Planning**: Pre-provision 3x normal capacity
2. **Load Testing**: Simulate peak traffic with tools like Gatling
3. **Feature Flags**: Disable non-critical features (e.g., recommendations)
4. **Rate Limiting**: Aggressive rate limiting on non-critical APIs

**Consistency Trade-offs:**

**Strong Consistency (Cannot compromise):**
- Order placement: Use database transactions
- Payment processing: Distributed transaction with idempotency
- Driver assignment: Pessimistic locking

**Eventual Consistency (Acceptable):**
- Search results: Slightly stale restaurant data OK
- Ratings: Update ratings asynchronously
- Analytics: Delayed metrics acceptable

**Degradation Strategies:**
1. **Read from Cache**: Serve stale cache if DB overloaded (with stale indicator)
2. **Async Processing**: Queue non-critical updates (e.g., notification sending)
3. **Graceful Degradation**: 
   - Disable real-time ETA updates, show static estimate
   - Disable live chat, show FAQs
4. **Queueing**: Place orders in queue if system overloaded, process FIFO

**Monitoring:**
- Real-time dashboards for order rate, latency, error rate
- Auto-scaling triggers at 70% capacity
- Alerts for anomalies (sudden spike, high error rate)

**Post-Event:**
- Gradual scale-down to avoid thundering herd
- Audit for data inconsistencies
- Replay failed events from dead-letter queue

This comprehensive design covers all aspects of a production-grade food delivery system. The design emphasizes scalability, reliability, and real-time capabilities while handling complex coordination between multiple parties (customers, restaurants, and drivers).
