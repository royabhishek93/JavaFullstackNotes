# Zomato / Swiggy - Food Delivery System Design
**YouTube-Style Interview Guide**

**Print Settings:** Landscape mode, monospace font (Courier New 9-10pt), narrow margins

---

## TABLE OF CONTENTS

1. [Requirements Gathering](#section-1-requirements-gathering)
2. [Capacity Estimation](#section-2-capacity-estimation)
3. [High-Level Architecture](#section-3-high-level-architecture)
4. [Core Workflows](#section-4-core-workflows)
5. [Scalability & Optimizations](#section-5-scalability--optimizations)
6. [Interview Q&A](#section-6-interview-qa)

---

## SECTION 1: REQUIREMENTS GATHERING

### 1.1 Functional Requirements

```
✅ Core Features:
1. Customer: Browse restaurants, place orders, track delivery
2. Restaurant: Manage menus, accept/reject orders, update order status
3. Delivery Agent: Accept deliveries, update location, mark delivered
4. Payment: Multiple payment methods, split settlements
5. Search: Find restaurants by location, cuisine, rating
6. Notifications: Real-time updates to all parties
7. Rating & Review: Rate food quality and delivery

❌ Out of Scope:
- Scheduled orders
- Group ordering
- Subscription models
- Loyalty programs
```

### 1.2 Non-Functional Requirements

```
Availability:  99.99% uptime
Scalability:   Handle millions of concurrent users
Latency:       Search < 500ms, Order placement < 2s, Location updates < 3s
Consistency:   Strong for orders/payments, Eventual for search
Real-time:     Live tracking with < 5s update intervals
```

---

## SECTION 2: CAPACITY ESTIMATION

**Assumptions:**
- 50 million DAU (Daily Active Users)
- Average 2 orders per user per week
- Peak hour traffic: 20% of daily orders

**Calculations:**
```
Orders per day:       14M orders
Orders per second:    
  - Average: 162 orders/sec
  - Peak: 810 orders/sec
  
Read:Write ratio:     100:1 (browsing vs ordering)
Search queries:       16,200 QPS

Storage:
- Per order: 8 KB (metadata + items + tracking)
- Daily: 14M × 8KB = 112 GB/day
- Annual: 40 TB/year
- With replication (3x): 120 TB/year
- 5-year total: ~600 TB

Bandwidth:
- Incoming: 15 MB/s (orders + location updates)
- Outgoing: 3 GB/s (search results + tracking)
```

---

## SECTION 3: HIGH-LEVEL ARCHITECTURE

### 3.1 System Architecture Diagram

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Customer  │         │  Restaurant  │         │   Driver    │
│     App     │         │     App      │         │     App     │
└──────┬──────┘         └──────┬───────┘         └──────┬──────┘
       │                       │                        │
       └───────────────────────┼────────────────────────┘
                               │ HTTPS
                    ┌──────────▼──────────┐
                    │    API Gateway      │
                    │  (Rate Limiting)    │
                    │   Load Balancer     │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
    ┌───────▼────────┐ ┌──────▼──────┐  ┌───────▼────────┐
    │ User Service   │ │Order Service│  │Delivery Service│
    │ (Auth, Profile)│ │(Cart, Place)│  │(Driver Match)  │
    └───────┬────────┘ └──────┬──────┘  └───────┬────────┘
            │                  │                  │
    ┌───────▼────────┐ ┌──────▼──────┐  ┌───────▼────────┐
    │Restaurant Svc  │ │Payment Svc  │  │ Location Svc   │
    │(Menu, Search)  │ │(Stripe, UPI)│  │(Real-time GPS) │
    └───────┬────────┘ └──────┬──────┘  └───────┬────────┘
            │                  │                  │
    ┌───────▼────────┐ ┌──────▼──────┐  ┌───────▼────────┐
    │Notification Svc│ │Analytics Svc│  │   Search Svc   │
    │(Push/SMS/Email)│ │(Dashboards) │  │(Elasticsearch) │
    └────────────────┘ └─────────────┘  └────────────────┘
            │                  │                  │
    ┌───────┴──────────────────┴──────────────────┴────────┐
    │              Message Queue (Kafka)                    │
    │  Topics: order-events, location-updates, notifications│
    └───────────────────────────────────────────────────────┘
            │                  │                  │
    ┌───────▼────────┐ ┌──────▼──────┐  ┌───────▼────────┐
    │   PostgreSQL   │ │   MongoDB   │  │     Redis      │
    │   (Orders)     │ │(Restaurants)│  │    (Cache)     │
    │   (Users)      │ │  (Menus)    │  │  (Sessions)    │
    │   (Payments)   │ │             │  │  (Locations)   │
    └────────────────┘ └─────────────┘  └────────────────┘
            │                  │                  │
    ┌───────▼────────┐ ┌──────▼──────┐  ┌───────▼────────┐
    │  Elasticsearch │ │   Cassandra │  │      S3        │
    │   (Search)     │ │  (Tracking) │  │(Food Images)   │
    └────────────────┘ └─────────────┘  └────────────────┘
```

### 3.2 Microservices Breakdown

**User Service (Node.js/Go):**
- Authentication & authorization (JWT tokens)
- Profile management (customer, restaurant, driver)
- Address management with geocoding
- Database: PostgreSQL + Redis (sessions)

**Restaurant Service (Java/Spring Boot):**
- Restaurant CRUD operations
- Menu management with item variants
- Availability and timing management
- Database: MongoDB (flexible menu schema)
- Search: Elasticsearch

**Order Service (Java/Spring Boot):**
- Shopping cart management
- Order placement and validation
- Order state machine management
- Order history and tracking
- Database: PostgreSQL (ACID transactions)
- Cache: Redis for active orders

**Delivery Service (Python/Go):**
- Driver onboarding and verification
- Driver availability management
- Order-driver matching algorithm
- Route optimization
- Database: PostgreSQL + Redis (geospatial)

**Location Service (Go):**
- Real-time driver location tracking
- Customer order tracking
- ETA calculation
- Database: Cassandra (time-series data)
- Real-time: WebSockets

**Payment Service (Java/Spring Boot):**
- Payment processing (Stripe, PayPal, UPI)
- Transaction recording
- Split payments (platform fee, restaurant revenue)
- Driver payouts and refunds
- Database: PostgreSQL (PCI-DSS compliance)

**Search Service (Python):**
- Restaurant and menu item search
- Filters: cuisine, price, rating, delivery time
- Autocomplete suggestions
- Personalized ranking with ML
- Search Engine: Elasticsearch

**Notification Service (Node.js):**
- Push notifications (FCM, APNs)
- SMS (Twilio)
- Email (SendGrid)
- Queue: Kafka

### 3.3 Database Strategy (Production-Ready with High Availability)

#### 3.3.1 Service-to-Database Mapping

| **Service** | **Primary Database** | **Cache/Search** | **Why** |
|-------------|---------------------|------------------|---------|
| User Service | PostgreSQL | Redis (sessions) | ACID for user data, strong consistency |
| Order Service | PostgreSQL | Redis (active orders) | Transactions, financial integrity |
| Payment Service | PostgreSQL | - | PCI-DSS compliance, ACID required |
| Restaurant Service | MongoDB | Elasticsearch | Flexible menu schemas per restaurant |
| Delivery Service | PostgreSQL | Redis (geospatial) | Driver assignments need ACID |
| Location Service | Cassandra | Redis (real-time) | 100K+ writes/sec, time-series data |
| Search Service | Elasticsearch | Redis (query cache) | Full-text + geo-distance search |
| Notification Service | Kafka (events) | - | Fire-and-forget async pattern |

---

#### 3.3.2 Database High Availability Details

**1. PostgreSQL (AWS RDS) - Transactional Data**
```
Use Case: Orders, Users, Payments, Delivery Agents
AWS Service: RDS PostgreSQL 15

High Availability Setup:
├─ 1 Primary Instance (db.r6g.4xlarge) - WRITES only
├─ 3 Read Replicas (different AZs) - READS only
│  ├─ Replica 1: db.r6g.4xlarge (AZ-1)
│  ├─ Replica 2: db.r6g.4xlarge (AZ-2)
│  └─ Replica 3: db.r6g.2xlarge (AZ-3)
├─ Storage: 2 TB (auto-scaling to 10 TB)
├─ IOPS: 12,000 provisioned
├─ Automatic Failover: < 60 seconds
├─ Backup: Every 6 hours, 7-day retention
├─ Point-in-Time Recovery (PITR): 7 days
└─ Encryption: AES-256 at rest, TLS 1.2+ in transit

Connection Pooling: PgBouncer (1000 connections per replica)
```

**2. Redis (AWS ElastiCache) - In-Memory Cache**
```
Use Case: Sessions, Active Orders, Search Results, Driver Locations
AWS Service: ElastiCache Redis 7.x (Cluster Mode)

High Availability Setup:
├─ 6-Node Cluster (3 primary + 3 replica)
│  ├─ Shard 1: Primary (AZ-1) + Replica (AZ-2)
│  ├─ Shard 2: Primary (AZ-2) + Replica (AZ-3)
│  └─ Shard 3: Primary (AZ-3) + Replica (AZ-1)
├─ Instance Type: r6g.large (13 GB memory each)
├─ Total Memory: 78 GB (across all nodes)
├─ Throughput: 1M+ operations/sec
├─ Multi-AZ Automatic Failover: Enabled
├─ Backup: Daily snapshots to S3
└─ Special Commands: GEOADD, GEORADIUS (for driver search)

TTL Strategy:
├─ Active Orders: 2 hours
├─ User Sessions: 7 days
├─ Search Results: 5 minutes
└─ Driver Locations: 30 seconds
```

**3. MongoDB (AWS DocumentDB) - Flexible Schemas**
```
Use Case: Restaurants, Menus, Menu Items (variable structure)
AWS Service: DocumentDB (MongoDB-compatible)

High Availability Setup:
├─ 3-Node Replica Set
│  ├─ Primary (r6g.xlarge, AZ-1) - WRITES
│  ├─ Secondary 1 (r6g.xlarge, AZ-2) - READS
│  └─ Secondary 2 (r6g.xlarge, AZ-3) - READS
├─ Storage: 500 GB (auto-scaling)
├─ Automatic Failover: < 30 seconds
├─ Continuous Backup: To S3
├─ Sharding: By restaurant_id (4 shards for 1M+ restaurants)
└─ Read Preference: Secondary nodes (for search queries)

Why MongoDB: Each restaurant has different menu structure
Example: Pizza place has sizes/toppings, Burger place has combos
```

**4. Elasticsearch (AWS OpenSearch) - Search Engine**
```
Use Case: Restaurant search, menu item search, autocomplete
AWS Service: OpenSearch (Elasticsearch-compatible)

High Availability Setup:
├─ 3-Node Cluster
│  ├─ Data Node 1 (r6g.xlarge, AZ-1)
│  ├─ Data Node 2 (r6g.xlarge, AZ-2)
│  └─ Master Node (r6g.large, AZ-3)
├─ Storage: 500 GB EBS (gp3)
├─ Indexes: restaurants, menu_items (with geo_point)
├─ Shards: 3 primary + 1 replica each
├─ Backup: Automated snapshots every hour to S3
└─ Cross-Cluster Replication: To DR region

Query Features: Full-text, Geo-distance, Filters, Scoring
```

**5. Cassandra (AWS Keyspaces) - Time-Series Data**
```
Use Case: Driver location tracking (append-only logs)
AWS Service: Keyspaces (Apache Cassandra-compatible)

High Availability Setup:
├─ Serverless (fully managed)
├─ Replication Factor: 3x across 3 AZs (automatic)
├─ Throughput: Auto-scaling (handles 100K+ writes/sec)
├─ Storage: Unlimited (pay-per-use)
├─ TTL: 7 days (auto-delete old data)
├─ Point-in-Time Recovery: 35 days
└─ Multi-Region Replication: Optional

Schema:
Table: location_tracking
Partition Key: driver_id
Clustering Key: timestamp (DESC)
Columns: lat, lon, accuracy, speed

Why Cassandra: Write-optimized, no read-before-write
```

**6. S3 (Object Storage) - Images & Backups**
```
Use Case: Food images, restaurant logos, backups
AWS Service: S3

High Availability Setup:
├─ Cross-Region Replication: us-east-1 → us-west-2
├─ Versioning: Enabled (rollback protection)
├─ Durability: 99.999999999% (11 nines)
├─ CloudFront CDN: 99% cache hit rate
└─ Lifecycle Policies:
   ├─ Standard Storage: 0-30 days
   ├─ Infrequent Access (IA): 31-90 days
   └─ Glacier: 90+ days

Buckets:
├─ zomato-food-images (50 TB, public CDN)
├─ zomato-backups (100 TB, Glacier)
└─ zomato-logs (30-day retention)
```

**7. Kafka (AWS MSK) - Event Streaming**
```
Use Case: Order events, payment events, location updates
AWS Service: MSK (Managed Streaming for Kafka)

High Availability Setup:
├─ 3-Broker Cluster (one per AZ)
├─ Replication Factor: 3x
├─ Partitions: 12 per topic
├─ Retention: 7 days
├─ Throughput: 200 MB/s per broker
├─ Encryption: TLS + at-rest (KMS)
└─ Auto-healing: Failed brokers replaced automatically

Topics:
├─ order-events (12 partitions)
├─ payment-events (12 partitions)
├─ location-updates (12 partitions)
├─ notification-events (12 partitions)
└─ analytics-events (12 partitions)
```

---

#### 3.3.3 Data Flow Patterns

**Write Path:**
```
User Action → API Gateway → Service → Primary DB → Kafka Event → Other Services
Example: Place Order → Order Service → PostgreSQL Primary → Kafka → Notification
```

**Read Path:**
```
User Query → API Gateway → Service → Redis Cache (miss) → Read Replica → Cache Update
Cache Hit Rate: 90%+ for hot data
```

**Geo-Spatial Queries (Driver Search):**
```
Redis Command: GEORADIUS drivers:available {lat} {lon} 5km WITHDIST
Returns: List of driver IDs within 5km radius
Performance: < 10ms for 100K drivers
```

### 3.4 Complete Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                   ZOMATO ERD - COMPLETE SCHEMA                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐
│      USERS          │
├─────────────────────┤
│ PK  id              │◄──────────────────┐
│     email (UNIQUE)  │                   │
│     phone (UNIQUE)  │                   │ 1 (owner)
│     password_hash   │                   │
│     full_name       │                   │
│     user_type  ENUM │                   │
│     is_active       │                   │
│     created_at      │                   │
│                     │                   │
│ ENUM: CUSTOMER,     │                   │
│       RESTAURANT_   │                   │
│       OWNER,        │                   │
│       DELIVERY_     │                   │
│       AGENT         │                   │
└──────────┬──────────┘                   │
           │ 1                            │
           │                              │
           │ *                            │
┌──────────▼──────────────┐               │
│     ADDRESSES           │               │
├─────────────────────────┤               │
│ PK  id                  │               │
│ FK  user_id             │               │
│     address_type  ENUM  │               │
│     address_line1       │               │
│     city, state         │               │
│     postal_code         │               │
│     latitude   DECIMAL  │               │
│     longitude  DECIMAL  │               │
│     is_default BOOLEAN  │               │
│                         │               │
│ ENUM: HOME, WORK, OTHER │               │
│ INDEX: (lat, lon)       │               │
└─────────────────────────┘               │
           │ *                            │
           │ (delivery_address)           │
           │ 1                            │
┌──────────▼──────────────────────┐       │
│      RESTAURANTS                │       │
├─────────────────────────────────┤       │
│ PK  id                          │       │
│ FK  owner_id                    │───────┘
│     name                        │
│     description                 │
│     cuisine_types   TEXT[]      │       ┌────────────────────────┐
│     address, city               │◄──────│  MENU_ITEMS            │
│     latitude        DECIMAL     │ 1   * ├────────────────────────┤
│     longitude       DECIMAL     │       │ PK  id                 │
│     average_rating  DECIMAL(3,2)│       │ FK  restaurant_id      │
│     is_active       BOOLEAN     │       │     name               │
│     is_accepting_orders         │       │     description        │
│     opens_at, closes_at  TIME   │       │     category           │
│     minimum_order_amount        │       │     price      DECIMAL │
│     delivery_fee    DECIMAL     │       │     is_vegetarian      │
│     cover_image_url             │       │     is_available       │
│                                 │       │     preparation_time   │
│ INDEX: city, (lat,lon), rating  │       │     tags       TEXT[]  │
└──────────┬──────────────────────┘       │                        │
           │ 1                            │ INDEX: restaurant_id   │
           │                              └────────────┬───────────┘
           │ *                                         │ *
┌──────────▼──────────────────────┐                   │
│      ORDERS                     │                   │ 1
├─────────────────────────────────┤       ┌───────────▼───────────┐
│ PK  id                          │       │ ORDER_ITEMS           │
│     order_number      UNIQUE    │       ├───────────────────────┤
│ FK  customer_id  (→ users)      │◄──────│ PK  id                │
│ FK  restaurant_id               │ 1   * │ FK  order_id          │
│ FK  delivery_address_id         │       │ FK  menu_item_id      │
│ FK  delivery_agent_id (→ users) │       │     quantity          │
│     status            ENUM      │       │     unit_price        │
│     subtotal          DECIMAL   │       │     total_price       │
│     delivery_fee      DECIMAL   │       │                       │
│     taxes, discount   DECIMAL   │       │ INDEX: order_id       │
│     total_amount      DECIMAL   │       └───────────────────────┘
│     payment_method    ENUM      │
│     payment_status    ENUM      │       ┌───────────────────────┐
│     estimated_delivery_time     │       │ PAYMENTS              │
│     actual_delivery_time        │       ├───────────────────────┤
│     created_at                  │    ┌──│ PK  id                │
│                                 │    │  │ FK  order_id          │
│ ENUM status:                    │    │  │     amount            │
│   PLACED, CONFIRMED, PREPARING, │    │  │     payment_method    │
│   READY_FOR_PICKUP, PICKED_UP,  │    │  │     status  ENUM      │
│   IN_TRANSIT, DELIVERED,        │    │  │     transaction_id    │
│   CANCELLED                     │    │  │     gateway           │
│                                 │    │  │     refund_amount     │
│ INDEX: customer_id,             │    │  │                       │
│        restaurant_id, status    │    │  │ ENUM: PENDING,        │
└──────────┬──────────────────────┘    │  │       SUCCESS,        │
           │ 1                         │  │       FAILED,         │
           │                           │  │       REFUNDED        │
           │ *                         │  │                       │
┌──────────▼──────────────────────┐    │  │ INDEX: order_id,      │
│   ORDER_TRACKING (Time-series)  │    │  │        transaction_id │
├─────────────────────────────────┤    │  └───────────┬───────────┘
│ PK  id                          │    │              │ 1
│ FK  order_id                    │    │              │
│     status            VARCHAR   │    │              │ 1
│     latitude          DECIMAL   │    └──────────────┘
│     longitude         DECIMAL   │
│     updated_by        VARCHAR   │    ┌───────────────────────┐
│     notes             TEXT      │    │ RATINGS_REVIEWS       │
│     created_at        TIMESTAMP │    ├───────────────────────┤
│                                 │ ┌──│ PK  id                │
│ PARTITION BY: created_at (month)│ │  │ FK  order_id          │
│ INDEX: order_id, created_at     │ │  │ FK  customer_id       │
└─────────────────────────────────┘ │  │ FK  restaurant_id     │
                                    │  │ FK  delivery_agent_id │
┌─────────────────────────────────┐ │  │     food_rating (1-5) │
│   DELIVERY_AGENTS               │ │  │     delivery_rating   │
├─────────────────────────────────┤ │  │     review_text       │
│ PK  id                          │ │  │     images     TEXT[] │
│ FK  user_id          UNIQUE     │ │  │     helpful_count     │
│     vehicle_type     VARCHAR    │ │  │     created_at        │
│     vehicle_number              │ │  │                       │
│     is_available     BOOLEAN    │ │  │ INDEX: restaurant_id  │
│     current_latitude  DECIMAL   │ │  └───────────────────────┘
│     current_longitude DECIMAL   │ │
│     last_location_update        │ │  ┌───────────────────────┐
│     average_rating   DECIMAL    │ │  │ COUPONS               │
│     total_deliveries  INTEGER   │ │  ├───────────────────────┤
│     earnings_today    DECIMAL   │ │  │ PK  id                │
│                                 │ │  │     code      UNIQUE  │
│ INDEX: available, (lat,lon)     │ │  │     discount_type     │
└─────────────────────────────────┘ │  │     discount_value    │
                                    │  │     min_order_amount  │
┌─────────────────────────────────┐ │  │     usage_limit       │
│   NOTIFICATIONS                 │ │  │     valid_from/until  │
├─────────────────────────────────┤ │  │     is_active         │
│ PK  id                          │ │  │                       │
│ FK  user_id                     │ │  │ INDEX: code           │
│     type              VARCHAR   │ │  └─────────┬─────────────┘
│     title             VARCHAR   │ │            │ *
│     message           TEXT      │ │            │
│     related_order_id  BIGINT    │ │            │ *
│     is_read           BOOLEAN   │ │  ┌─────────▼─────────────┐
│     sent_via          VARCHAR   │ │  │ USER_COUPONS (M:M)    │
│     created_at                  │ │  ├───────────────────────┤
│                                 │ │  │ PK  id                │
│ ENUM type:                      │ └──│ FK  user_id           │
│   ORDER_PLACED,                 │    │ FK  coupon_id         │
│   ORDER_CONFIRMED,              │    │ FK  order_id          │
│   OUT_FOR_DELIVERY,             │    │     used_at           │
│   DELIVERED, CANCELLED          │    │                       │
│                                 │    │ UNIQUE: (user_id,     │
│ INDEX: user_id, is_read         │    │         coupon_id,    │
└─────────────────────────────────┘    │         order_id)     │
                                       └───────────────────────┘

CARDINALITY SUMMARY:
───────────────────
• users (1) → (*) addresses
• users (1) → (*) restaurants (as owner)
• restaurants (1) → (*) menu_items
• users (1) → (*) orders (as customer)
• orders (*) → (1) restaurants
• orders (*) → (1) delivery_agents
• orders (1) → (*) order_items
• orders (1) → (1) payments
• orders (1) → (*) order_tracking
• orders (1) → (*) ratings_reviews
• users (*) ↔ (*) coupons (via user_coupons)
```

### 3.5 Production-Ready AWS Architecture (High Availability)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   USERS (Customer, Restaurant, Driver Apps)                 │
│               React.js (Web) + React Native (iOS/Android)                   │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ HTTPS/WSS
                                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AWS ROUTE 53 (DNS + Health Checks)                       │
│              Latency-based Routing | Failover to DR Region                  │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AWS CLOUDFRONT CDN (Global)                          │
│        • Food Images (99% cache hit) • Static Assets (JS/CSS)               │
│        • Edge Locations: 400+ worldwide • TTL: 24 hours                     │
│        • Origin: S3 + ALB (for API calls)                                   │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ Cache Miss / Dynamic Content
                                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AWS WAF (Web Application Firewall)                     │
│        • DDoS Protection (Shield Standard) • Rate Limiting                  │
│        • SQL Injection / XSS Protection • Geo-blocking                      │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│            AWS APPLICATION LOAD BALANCER (ALB) - Multi-AZ                   │
│    • SSL Termination (ACM Certificates) • Health Checks every 30s           │
│    • Path-based Routing: /api/orders → Order Service Target Group          │
│    • Cross-Zone Load Balancing Enabled                                     │
│    • Sticky Sessions (for WebSocket) • Connection Draining: 300s           │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                ┌────────────────┴────────────────┐
                │   AWS VPC (10.0.0.0/16)         │
                │   • 3 Availability Zones        │
                │   • Public Subnets (ALB, NAT)   │
                │   • Private Subnets (Services)  │
                │   • Isolated Subnets (DB)       │
                └────────────────┬────────────────┘
                                 │
                                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                     API GATEWAY (Spring Cloud Gateway)                      │
│                    Running on AWS EKS (Kubernetes)                          │
│   • JWT Authentication (Auth0/Cognito) • Rate Limiting (Redis)             │
│   • Circuit Breaker (Resilience4j) • Request/Response Logging              │
│   • Min: 3 pods, Max: 50 pods (HPA based on CPU 70%)                       │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
┌───────▼─────────┐    ┌─────────▼────────┐    ┌────────▼─────────┐
│  User Service   │    │  Order Service   │    │Restaurant Service│
│  (Java/Spring)  │    │  (Java/Spring)   │    │  (Java/Spring)   │
│  EKS Deployment │    │  EKS Deployment  │    │  EKS Deployment  │
│                 │    │                  │    │                  │
│ Pods: 3-20      │    │ Pods: 5-50 (peak)│    │ Pods: 3-30       │
│ CPU: 1-2 vCPU   │    │ CPU: 2-4 vCPU    │    │ CPU: 1-2 vCPU    │
│ Memory: 2-4 GB  │    │ Memory: 4-8 GB   │    │ Memory: 2-4 GB   │
│                 │    │                  │    │                  │
│ Features:       │    │ Features:        │    │ Features:        │
│ • Auth (JWT)    │    │ • Cart           │    │ • Menu CRUD      │
│ • Profile CRUD  │    │ • Place Order    │    │ • Search         │
│ • Address Mgmt  │    │ • Order Tracking │    │ • Availability   │
│                 │    │                  │    │                  │
│ DB: RDS PG      │    │ DB: RDS PG       │    │ DB: DocumentDB   │
│ Cache: Redis    │    │ Cache: Redis     │    │ Search: OpenSrch │
└─────────────────┘    └──────────────────┘    └──────────────────┘
        │                        │                        │
┌───────▼─────────┐    ┌─────────▼────────┐    ┌────────▼─────────┐
│ Payment Service │    │ Delivery Service │    │ Location Service │
│  (Java/Spring)  │    │     (Go)         │    │  (Go + WebSocket)│
│  EKS Deployment │    │  EKS Deployment  │    │  EKS Deployment  │
│                 │    │                  │    │                  │
│ Pods: 3-20      │    │ Pods: 5-30       │    │ Pods: 10-100     │
│ CPU: 2-4 vCPU   │    │ CPU: 2-4 vCPU    │    │ CPU: 2-4 vCPU    │
│ Memory: 4-8 GB  │    │ Memory: 4-8 GB   │    │ Memory: 4-8 GB   │
│                 │    │                  │    │                  │
│ • Stripe API    │    │ • Driver Match   │    │ • Real-time GPS  │
│ • Razorpay      │    │ • Assignment     │    │ • ETA Calc       │
│ • UPI Gateway   │    │ • Route Optimize │    │ • Track Delivery │
│ • Refunds       │    │ • GeoRadius      │    │ • WebSocket Pool │
│                 │    │                  │    │                  │
│ DB: RDS PG      │    │ DB: RDS PG       │    │ DB: Keyspaces    │
│ Vault: Secrets  │    │ Cache: Redis     │    │ Cache: Redis     │
└─────────────────┘    └──────────────────┘    └──────────────────┘
        │                        │                        │
┌───────▼─────────┐    ┌─────────▼────────┐    ┌────────▼─────────┐
│  Search Service │    │Notification Svc  │    │ Analytics Service│
│    (Python)     │    │    (Node.js)     │    │ (Python/Spark)   │
│ EKS Deployment  │    │  EKS Deployment  │    │  EMR Cluster     │
│                 │    │                  │    │                  │
│ • OpenSearch    │    │ • Push (FCM/APNs)│    │ • Dashboards     │
│ • Geo Queries   │    │ • SMS (Twilio)   │    │ • Reports        │
│ • ML Ranking    │    │ • Email(SendGrid)│    │ • ML Models      │
│                 │    │ • Kafka Consumer │    │ • S3/Redshift    │
└─────────────────┘    └──────────────────┘    └──────────────────┘
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│              AWS MSK (Managed Streaming for Apache Kafka)                   │
│                          Multi-AZ Deployment                                │
│                                                                             │
│  Cluster: 3 brokers (AZ-1, AZ-2, AZ-3) | Replication Factor: 3             │
│  Topics: order-events, payment-events, location-updates,                   │
│          notification-events, analytics-events                              │
│  Partitions: 12 per topic | Retention: 7 days                               │
│  Throughput: 200 MB/s per broker | Encryption: TLS + At-rest (KMS)         │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATA LAYER - HIGH AVAILABILITY                       │
│                                                                             │
│ ┌──────────────────────────────────────────────────────────────────┐      │
│ │           RDS PostgreSQL 15 (Multi-AZ) - PRIMARY DB              │      │
│ │  ┌────────────┐    ┌────────────┐    ┌────────────┐             │      │
│ │  │   Primary  │───>│ Read Rep-1 │    │ Read Rep-2 │             │      │
│ │  │   (AZ-1)   │    │   (AZ-2)   │    │   (AZ-3)   │             │      │
│ │  │  db.r6g.4xl│    │ db.r6g.4xl │    │ db.r6g.2xl │             │      │
│ │  │  16 vCPU   │    │  16 vCPU   │    │   8 vCPU   │             │      │
│ │  │  128 GB RAM│    │  128 GB RAM│    │  64 GB RAM │             │      │
│ │  └────────────┘    └────────────┘    └────────────┘             │      │
│ │                                                                  │      │
│ │  Tables: users, orders, payments, delivery_agents, ratings      │      │
│ │  Storage: 2 TB (Auto-scaling to 10 TB)                          │      │
│ │  IOPS: 12,000 provisioned | Backup: Automated (6-hour interval) │      │
│ │  PITR: 7-day retention | Encryption: AES-256 (KMS)              │      │
│ │  Failover: Automatic < 60 seconds                                │      │
│ │                                                                  │      │
│ │  Connection Pooling: PgBouncer (1000 connections per replica)   │      │
│ │  Write: Primary only | Read: Load-balanced across 2 replicas    │      │
│ └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│ ┌──────────────────────────────────────────────────────────────────┐      │
│ │         AWS DocumentDB (MongoDB-compatible) - FLEXIBLE SCHEMA    │      │
│ │  ┌────────────┐    ┌────────────┐    ┌────────────┐             │      │
│ │  │  Primary   │───>│Secondary-1 │    │Secondary-2 │             │      │
│ │  │   (AZ-1)   │    │   (AZ-2)   │    │   (AZ-3)   │             │      │
│ │  │ r6g.xlarge │    │ r6g.xlarge │    │ r6g.xlarge │             │      │
│ │  │  4 vCPU    │    │  4 vCPU    │    │  4 vCPU    │             │      │
│ │  │ 32 GB RAM  │    │ 32 GB RAM  │    │ 32 GB RAM  │             │      │
│ │  └────────────┘    └────────────┘    └────────────┘             │      │
│ │                                                                  │      │
│ │  Collections: restaurants, menus, menu_items                    │      │
│ │  Sharding: By restaurant_id (4 shards for 1M+ restaurants)      │      │
│ │  Storage: 500 GB (Auto-scaling) | Backup: Continuous to S3      │      │
│ │  Failover: Automatic < 30 seconds                                │      │
│ │  Read Preference: Secondary (for search queries)                 │      │
│ └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│ ┌──────────────────────────────────────────────────────────────────┐      │
│ │          AWS ElastiCache Redis 7.x (Cluster Mode)                │      │
│ │                                                                  │      │
│ │  ┌────────────┐    ┌────────────┐    ┌────────────┐             │      │
│ │  │ Shard-1    │    │ Shard-2    │    │ Shard-3    │             │      │
│ │  │ Primary    │    │ Primary    │    │ Primary    │             │      │
│ │  │ (AZ-1)     │    │ (AZ-2)     │    │ (AZ-3)     │             │      │
│ │  │ r6g.large  │    │ r6g.large  │    │ r6g.large  │             │      │
│ │  └─────┬──────┘    └─────┬──────┘    └─────┬──────┘             │      │
│ │        │                 │                 │                    │      │
│ │  ┌─────▼──────┐    ┌─────▼──────┐    ┌─────▼──────┐             │      │
│ │  │ Replica-1  │    │ Replica-2  │    │ Replica-3  │             │      │
│ │  │ (AZ-2)     │    │ (AZ-3)     │    │ (AZ-1)     │             │      │
│ │  └────────────┘    └────────────┘    └────────────┘             │      │
│ │                                                                  │      │
│ │  Total: 6 nodes (3 primary + 3 replica) | Memory: 13 GB each    │      │
│ │  Total Cache: 78 GB | Throughput: 1M+ ops/sec                   │      │
│ │  Keys: active_orders, sessions, search_cache, driver_locations  │      │
│ │  TTL Strategy: Orders (2h), Sessions (7d), Search (5m)           │      │
│ │  Geo Commands: GEOADD, GEORADIUS (for driver matching)          │      │
│ │  Backup: Daily snapshots to S3 | Multi-AZ Auto-failover         │      │
│ └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│ ┌──────────────────────────────────────────────────────────────────┐      │
│ │          AWS OpenSearch (Elasticsearch-compatible)                │      │
│ │  ┌────────────┐    ┌────────────┐    ┌────────────┐             │      │
│ │  │Data Node-1 │    │Data Node-2 │    │Master Node │             │      │
│ │  │  (AZ-1)    │    │  (AZ-2)    │    │  (AZ-3)    │             │      │
│ │  │ r6g.xlarge │    │ r6g.xlarge │    │ r6g.large  │             │      │
│ │  │  4 vCPU    │    │  4 vCPU    │    │  2 vCPU    │             │      │
│ │  │ 32 GB RAM  │    │ 32 GB RAM  │    │ 16 GB RAM  │             │      │
│ │  └────────────┘    └────────────┘    └────────────┘             │      │
│ │                                                                  │      │
│ │  Indexes: restaurants, menu_items (with geo_point fields)       │      │
│ │  Storage: 500 GB EBS (gp3) | Shards: 3 primary + 1 replica      │      │
│ │  Search Queries: Full-text + Geo-distance + Filters              │      │
│ │  Backup: Automated snapshots hourly to S3                        │      │
│ │  Cross-cluster Replication: To DR region                         │      │
│ └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│ ┌──────────────────────────────────────────────────────────────────┐      │
│ │          AWS Keyspaces (Apache Cassandra-compatible)              │      │
│ │                    Serverless - Fully Managed                    │      │
│ │                                                                  │      │
│ │  Table: location_tracking (Time-series data)                     │      │
│ │  Partition Key: driver_id | Clustering Key: timestamp            │      │
│ │  Replication: 3x across 3 AZs (automatic)                        │      │
│ │  Throughput: Auto-scaling (handles 100K+ writes/sec)             │      │
│ │  Storage: Unlimited | Retention: TTL 7 days (auto-delete)        │      │
│ │  PITR: 35-day point-in-time recovery                             │      │
│ │  Multi-region: Optional cross-region replication                 │      │
│ │  Use Case: Append-only driver location logs                      │      │
│ └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│ ┌──────────────────────────────────────────────────────────────────┐      │
│ │                    AWS S3 (Object Storage)                        │      │
│ │                                                                  │      │
│ │  Buckets:                                                        │      │
│ │  • zomato-food-images (Standard → IA → Glacier)                  │      │
│ │    - Versioning: Enabled | Size: 50 TB                           │      │
│ │    - Lifecycle: Standard (30d) → IA (90d) → Glacier              │      │
│ │    - CloudFront CDN origin (99% cache hit rate)                  │      │
│ │                                                                  │      │
│ │  • zomato-backups (Glacier Instant Retrieval)                    │      │
│ │    - RDS snapshots, DocumentDB backups, Kafka data               │      │
│ │    - Retention: 90 days                                          │      │
│ │                                                                  │      │
│ │  • zomato-logs (Intelligent-Tiering)                             │      │
│ │    - Application logs, ALB logs, CloudTrail logs                 │      │
│ │    - Retention: 30 days                                          │      │
│ │                                                                  │      │
│ │  Cross-Region Replication: To DR region (us-west-2)              │      │
│ │  Encryption: SSE-S3 (AES-256) | Access: IAM + Bucket Policies    │      │
│ └──────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                   OBSERVABILITY & SECURITY (Production-Grade)               │
│                                                                             │
│  Monitoring & Alerting:                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐      │
│  │ • CloudWatch: Metrics, Logs, Alarms (CPU, Memory, Disk, Latency)│      │
│  │ • Prometheus + Grafana: Custom business metrics dashboards       │      │
│  │ • AWS X-Ray: Distributed tracing (request flow across services)  │      │
│  │ • ELK Stack: Centralized logging (Elasticsearch, Logstash, Kibana)│     │
│  │ • PagerDuty: On-call alerts (P0: Payment down, DB failover)      │      │
│  └─────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│  Security:                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐      │
│  │ • AWS Secrets Manager: DB credentials, API keys rotation         │      │
│  │ • AWS KMS: Encryption keys for databases, S3, EBS volumes        │      │
│  │ • Security Groups: Whitelist only required ports (DB: 5432, 27017)│     │
│  │ • Network ACLs: Subnet-level firewall rules                       │      │
│  │ • VPC Flow Logs: Network traffic audit logs                       │      │
│  │ • AWS IAM: Least-privilege roles for services                     │      │
│  │ • AWS GuardDuty: Threat detection and continuous monitoring       │      │
│  └─────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│  CI/CD & Infrastructure:                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐      │
│  │ • AWS CodePipeline: Automated deployments (GitHub → Build → EKS) │      │
│  │ • GitHub Actions: Unit tests, integration tests, security scans   │      │
│  │ • Terraform: Infrastructure as Code (version-controlled)          │      │
│  │ • AWS Cloud Map: Service discovery for microservices              │      │
│  │ • Docker + ECR: Container images repository                        │      │
│  └─────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│  Disaster Recovery:                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐      │
│  │ • RTO (Recovery Time Objective): 15 minutes                       │      │
│  │ • RPO (Recovery Point Objective): 5 minutes (data loss tolerance) │      │
│  │ • Multi-Region Setup: Primary (us-east-1), DR (us-west-2)         │      │
│  │ • Automated Failover: Route 53 health checks + DNS failover       │      │
│  │ • Backup Strategy: 6-hour snapshots, 7-day retention               │      │
│  │ • Runbooks: Documented disaster recovery procedures               │      │
│  └─────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘

PRODUCTION TECH STACK SUMMARY:
──────────────────────────────
Frontend:        React.js (Web), React Native (Mobile)
API Gateway:     Spring Cloud Gateway (Java) on EKS
Backend:         • Java/Spring Boot: Order, Payment, Restaurant, User
                 • Go: Delivery, Location (high concurrency)
                 • Python: Search, Analytics, ML
                 • Node.js: Notifications (async I/O)

Databases:       • PostgreSQL 15 (Multi-AZ, 1 Primary + 2 Read Replicas)
                 • DocumentDB (3-node replica set, sharded)
                 • ElastiCache Redis (6-node cluster, 3 AZ)
                 • OpenSearch (3-node, Multi-AZ)
                 • Keyspaces (Serverless Cassandra, 3x replication)
                 • S3 (Cross-region replication)

Message Queue:   AWS MSK (Managed Kafka, 3-broker, Multi-AZ)
Container:       AWS EKS (Kubernetes) + Docker + ECR
Monitoring:      CloudWatch, Prometheus, Grafana, X-Ray, ELK
Security:        WAF, Secrets Manager, KMS, IAM, GuardDuty
CI/CD:           CodePipeline, GitHub Actions, Terraform
CDN:             CloudFront (400+ edge locations)

Cost (Monthly):  ~$25,000 - $40,000 for 50M DAU (optimized with Reserved Instances)
```

### 3.6 Design Patterns Applied

**Architectural Patterns:**
- Microservices Architecture (independent scaling)
- Event-Driven Architecture (Kafka-based Saga pattern)
- API Gateway Pattern (single entry point)
- CQRS (write to master, read from replicas)

**Application Patterns:**
- State Pattern (order state machine)
- Strategy Pattern (driver assignment algorithms)
- Observer Pattern (real-time notifications)
- Circuit Breaker Pattern (payment gateway failures)
- Factory Pattern (payment gateway selection)

**Caching Patterns:**
- Cache-Aside (lazy loading)
- Write-Through (order updates)
- Refresh-Ahead (popular restaurants)

---

## SECTION 4: CORE WORKFLOWS

### 4.1 Order Placement Flow

```
┌─────────┐  ┌──────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐
│Customer │  │Order Svc │  │Payment  │  │Restaurant│  │Delivery  │
│   App   │  │          │  │  Svc    │  │   Svc    │  │   Svc    │
└────┬────┘  └────┬─────┘  └────┬────┘  └────┬─────┘  └────┬─────┘
     │            │             │            │             │
     │1. Add items to cart      │            │             │
     ├───────────>│             │            │             │
     │            │             │            │             │
     │2. Place Order            │            │             │
     ├───────────>│             │            │             │
     │            │             │            │             │
     │            │3. Validate cart (prices, availability)  │
     │            ├─────────────────────────>│             │
     │            │<─────────────────────────┤             │
     │            │             │            │             │
     │            │4. Create order (status: PENDING)       │
     │            │   Save to PostgreSQL     │             │
     │            │             │            │             │
     │            │5. Process payment        │             │
     │            ├────────────>│            │             │
     │            │             │ Stripe/UPI │             │
     │            │<────────────┤            │             │
     │            │             │            │             │
     │<───────────┤6. Return order_id        │             │
     │            │             │            │             │
     │            │7. Publish order-placed event            │
     │            ├─────────────┼───────────>│             │
     │            │             │            │             │
     │            │             │            │8. Notify restaurant
     │            │             │            ├────────────>│
     │            │             │            │             │
     │            │             │            │9. Confirm order
     │            │<─────────────────────────┤             │
     │            │             │            │             │
     │            │10. Update status: CONFIRMED            │
     │            │             │            │             │
     │            │11. Find nearby drivers (GeoRadius)     │
     │            ├────────────────────────────────────────>│
     │            │             │            │             │
     │            │12. Assign driver          │            │
     │            │<────────────────────────────────────────┤
     │            │             │            │             │
     │13. Send notifications (Push/SMS)       │             │
     ├<───────────┴─────────────┴────────────┴─────────────┘
     │   "Order confirmed! ETA: 30 mins"
```

### 4.2 Order State Machine

```
Order Status Flow:

CART ──────────────> PLACED ──────────> CONFIRMED
                       │                    │
                       │                    ↓
                       │               PREPARING
                       │                    │
                       │                    ↓
                       │           READY_FOR_PICKUP
                       │                    │
                       │                    ↓
                       │               PICKED_UP
                       │                    │
                       │                    ↓
                       │              IN_TRANSIT
                       │                    │
                       │                    ↓
                       │               DELIVERED
                       │                    │
                       │                    ↓
                       │               COMPLETED
                       │
                       ↓
                   CANCELLED

Cancellation Rules:
- PLACED → CONFIRMED: Full refund
- CONFIRMED → PREPARING: Full refund
- PREPARING → READY: Partial refund (restaurant charges)
- PICKED_UP+: No refund
```

### 4.3 Driver Assignment Algorithm

**Step 1: Find nearby drivers (Redis GeoRadius)**
```python
# Find drivers within 5km radius
GEORADIUS drivers:available {restaurant_lat} {restaurant_lon} 5 km WITHDIST
```

**Step 2: Score drivers**
```python
score = (
    distance_weight * (1 - normalized_distance) +  # 40% - Closer is better
    rating_weight * normalized_rating +             # 20% - Higher rating better
    utilization_weight * (1 - utilization) +        # 20% - Less busy better
    eta_weight * (1 - normalized_eta)               # 20% - Faster ETA better
)
```

**Step 3: Broadcast to top 5 drivers (Kafka)**
```
Topic: driver-assignment-requests
Message: {order_id, restaurant, customer_address, earning, timeout: 30s}

First driver to accept gets the order.
If timeout → re-broadcast to next batch.
```

### 4.4 Real-Time Location Tracking

**Driver Side (Mobile App):**
```
Every 10 seconds:
1. Get GPS coordinates (lat, lon, accuracy)
2. Batch with last 3 updates
3. Send to Location Service via HTTP/gRPC
4. Service updates Redis + Cassandra
```

**Customer Side (WebSocket):**
```
1. Customer connects: ws://api/track/{order_id}
2. Server fetches driver_id from order
3. Subscribe to driver location updates (Redis Pub/Sub)
4. Push location to customer every 5 seconds
5. Calculate ETA using Google Maps Distance Matrix API
6. Send update: {lat, lon, eta_minutes, distance_remaining}
```

### 4.5 Restaurant Search Flow

**Elasticsearch Query:**
```
Query Structure:
1. Geo Filter: Within 5km delivery radius
2. Filters: cuisine, rating > 4.0, is_open = true
3. Scoring:
   - Text relevance (BM25): 30%
   - Rating: 25%
   - Delivery time: 20%
   - Popularity: 15%
   - Distance: 10%
4. Personalization: Boost based on order history

Cache: Redis for popular queries (TTL: 5 min)
```

---

## SECTION 5: SCALABILITY & OPTIMIZATIONS

### 5.1 Horizontal Scaling

**Service Layer:**
- Stateless microservices behind load balancers
- Auto-scaling based on CPU/memory (Kubernetes HPA)
- Pod count: min 3, max 50

**Database Layer:**
- PostgreSQL: Primary-Replica replication (1 primary + 3 read replicas)
- MongoDB: Sharding by restaurant_id (4 shards)
- Cassandra: Partition by driver_id
- Redis Cluster: 6 nodes (3 primary + 3 replica)

### 5.2 Caching Strategy

**Multi-level Caching:**
1. **CDN**: Food images, static assets (CloudFront)
2. **Redis**: Hot data (90% cache hit rate)
   - Restaurant menus: TTL 1 hour
   - Active orders: TTL 2 hours
   - Search results: TTL 5 minutes
3. **Application Cache**: In-memory (Caffeine)

**Cache Invalidation:**
- Write-through for critical data (order status)
- TTL-based for non-critical (menus)
- Event-driven invalidation (Kafka)

**Redis Key Patterns:**
```
- active_orders:{order_id}        → Order JSON (TTL: 2 hours)
- restaurant:{id}                 → Restaurant JSON (TTL: 1 hour)
- driver_location:{driver_id}     → GeoHash (TTL: 30 sec)
- search_results:{query_hash}     → Results (TTL: 5 min)
- user_session:{token}            → User context (TTL: 7 days)
```

**Geospatial Commands:**
```
GEOADD drivers:available 77.5946 12.9716 driver_123
GEORADIUS drivers:available 77.5946 12.9716 5 km
```

### 5.3 Real-Time System at Scale

**Location Updates (100K active drivers):**
```
Write Path:
1. Mobile app batches updates (every 10s)
2. Load balancer → Go service (handles 50K writes/sec)
3. Batch write to Cassandra (100 updates per write)
4. Update Redis cache (GEOADD)
5. Publish to Kafka (for analytics)

Read Path:
1. Customer subscribes via WebSocket
2. Fetch driver location from Redis (GEOPOS)
3. Calculate ETA (Google Maps API)
4. Push update every 5s
```

**WebSocket Scaling:**
- Sticky sessions at load balancer
- Redis Pub/Sub for message broadcasting
- Horizontal scaling with connection pooling

### 5.4 Fault Tolerance

**Circuit Breaker Pattern:**
```
Payment Service:
- If 50% requests fail in 10s → Open circuit
- Fallback: Queue payment for later processing
- Try again after 30s

Restaurant Service:
- If unavailable → Serve stale cache
- Mark restaurant as "temporarily unavailable"
```

**Retry with Exponential Backoff:**
```
Notification Service:
- Failed push notification → Retry after 1s, 2s, 4s, 8s
- Max 3 retries
- After 3 failures → Move to dead letter queue
```

**Data Durability:**
- Database replication (sync for orders, async for reads)
- Cross-region backups (daily to S3)
- Point-in-time recovery (PITR)
- Event sourcing for order state

### 5.5 Consistency Model

**Strong Consistency (Cannot compromise):**
- Order placement: Database transactions
- Payment: Distributed transaction
- Driver assignment: Pessimistic locking

**Eventual Consistency (Acceptable):**
- Search results: Slightly stale OK
- Ratings: Update async
- Analytics: Delayed OK

### 5.6 API Design (Key Endpoints)

**Restaurant APIs:**
```
GET /api/v1/restaurants/search
Query: lat, lng, cuisine, rating_min, delivery_time_max, page

GET /api/v1/restaurants/{restaurant_id}/menu
```

**Order APIs:**
```
POST /api/v1/orders
Body: {restaurant_id, items, delivery_address_id, payment_method_id}

GET /api/v1/orders/{order_id}

PUT /api/v1/orders/{order_id}/cancel
```

**Tracking APIs:**
```
GET /api/v1/orders/{order_id}/track

WebSocket: ws://api/v1/track/{order_id}
Events: location_update, status_change, eta_update
```

**Driver APIs:**
```
PUT /api/v1/drivers/status
POST /api/v1/drivers/location
PUT /api/v1/drivers/orders/{order_id}/pickup
PUT /api/v1/drivers/orders/{order_id}/deliver
```

---

## SECTION 6: INTERVIEW Q&A

### Q1: How do you handle the driver assignment problem efficiently?

**Answer:**
"Driver assignment is a complex optimization problem. Here's my approach:

**Algorithm:**
1. **Spatial Indexing**: Use Redis GEORADIUS to find drivers within 5km
2. **Scoring System**:
   - Distance: 40% (closer is better)
   - Driver rating: 20%
   - Current utilization: 20% (less busy better)
   - Estimated delivery time: 20%
3. **Assignment Flow**:
   - Broadcast to top 5 drivers with 30s timeout
   - First to accept gets the order
   - If timeout, re-broadcast to next batch

**Advanced Optimizations:**
- **Batch Assignment**: Assign multiple orders to one driver
- **Predictive Positioning**: ML predicts demand hotspots, pre-position drivers
- **Dynamic Zones**: Adjust zone boundaries based on real-time demand"

### Q2: How do you ensure consistency in order lifecycle across services?

**Answer:**
"We use **Saga Pattern** with event-driven choreography:

**Flow:**
```
Order Placed → Payment (charge)
           → Restaurant (notify)
           → Delivery (assign driver)
           → Notification (send updates)
```

**Implementation:**
- **Event Sourcing**: Store all state changes as events in Kafka
- **Compensating Transactions**: Rollback on failure
  - Payment failed → Cancel order → Refund
  - Driver not found → Cancel → Refund payment
- **Idempotency**: All APIs use request IDs to prevent duplicates
- **Strong Consistency**: Payment uses 2-phase commit
- **Eventual Consistency**: Search results, ratings"

### Q3: How do you handle real-time location tracking at scale?

**Answer:**
"For 100K+ active drivers:

**Write Path:**
1. Mobile app batches updates every 10s
2. Go service receives, validates, buffers
3. Batch write to Cassandra (100 updates/write)
4. Update Redis cache (GeoHash, TTL: 30s)
5. Publish to Kafka for analytics

**Read Path:**
1. Customer subscribes via WebSocket
2. Fetch from Redis (GEOPOS)
3. Calculate ETA (Google Maps Distance Matrix API)
4. Push update every 5s

**Optimizations:**
- Geohash precision: 6 chars (~1km)
- Only update if moved > 50m
- Protocol Buffers for compression
- Cassandra partitioned by driver_id, clustered by timestamp"

### Q3.1: Why use WebSocket for real-time tracking instead of HTTP polling?

**Answer:**
"Great question! Let me explain with numbers:

**The Problem:**
Customer needs driver location updates every 5 seconds in real-time.

**Option 1: HTTP Polling (Bad)**
```
Customer makes request every 5 seconds: GET /api/location
Problems:
- 720 requests per order (12/min × 60 min)
- For 100K active orders: 72 million requests/hour!
- Most requests return 'no change' (wasteful)
- Latency: Up to 5s delay between updates
- Battery drain on mobile
```

**Option 2: WebSocket (Optimal)**
```
Persistent bidirectional connection - like a phone call that stays open

Advantages:
├─ Full-duplex: Both sides can send data anytime
├─ Low overhead: No HTTP headers after initial handshake
├─ Real-time: < 100ms latency for updates
├─ Efficient: One connection for entire delivery (30-45 min)
├─ Binary support: Can send compressed data
└─ Auto-reconnect: Client libraries handle disconnections

Connection lifecycle:
1. Customer opens tracking page
2. WebSocket connection established: ws://api/track/{order_id}
3. Server subscribes to driver location updates (Redis Pub/Sub)
4. Driver sends location every 10s → Location Service → Redis Pub/Sub
5. Server pushes to customer via WebSocket immediately
6. Order delivered → WebSocket closed
```

**Numbers Comparison:**

| Method | Requests/Hour | Bandwidth (100K orders) | Latency | Server Load |
|--------|---------------|-------------------------|---------|-------------|
| HTTP Polling | 720 per order | 7.2 GB | 0-5s delay | Very High |
| WebSocket | 1 connection | 50 MB | < 100ms | Low |

**WebSocket uses 99% less server resources!**

**Real-world Analogy:**
```
HTTP Polling = Calling restaurant every 5 min asking 'Where's my food?'
WebSocket = One phone call that stays open until food arrives
```

**Why this matters at scale:**
- 100K simultaneous deliveries
- HTTP: 72 million requests/hour → Server overload
- WebSocket: 100K persistent connections → Easily handled

This is why all real-time apps (Uber, Zomato, WhatsApp, live sports) use WebSocket."

### Q4: How do you design restaurant search with geo-proximity?

**Answer:**
"We use **Elasticsearch** with geospatial indexing:

**Query Logic:**
1. **Geo Filter**: Within 5km delivery radius
2. **Filters**: Cuisine, rating, delivery time
3. **Scoring**:
   - Text relevance (BM25): 30%
   - Rating: 25%
   - Delivery time: 20%
   - Popularity: 15%
   - Distance: 10%
4. **Personalization**: Boost based on order history

**Cache**: Redis for popular queries (TTL: 5 min)"

### Q5: How do you handle payment failures and refunds?

**Answer:**
"Payment requires robust error handling:

**Payment Flow:**
1. **Pre-authorization**: Hold amount on card
2. **Order Processing**: Wait for restaurant confirmation
3. **Capture**: Capture payment after food prepared
4. **Settlement**: Split (platform fee, restaurant revenue)

**Failure Scenarios:**

**Gateway Timeout:**
- Retry with exponential backoff (3 attempts)
- Try backup payment method
- If all fail, cancel order

**Payment Captured but Order Failed:**
- Automatic refund initiation
- Refund to original method
- If refund fails, manual intervention + support ticket

**Refund Scenarios:**
- Restaurant cancellation: Full refund + delivery fee
- Customer cancels before preparation: Full refund
- After pickup: No refund

**Implementation:**
- Idempotency keys prevent duplicate charges
- Webhook handling (async via Kafka)
- Nightly reconciliation job
- Audit log for every state change"

### Q6: How do you implement surge pricing during peak hours?

**Answer:**
"Dynamic pricing balances supply-demand:

**Formula:**
```
surge_multiplier = base * (1 + demand_factor + supply_factor)

demand_factor = (current_orders - avg_orders) / avg_orders
supply_factor = (required_drivers - available_drivers) / required_drivers

Capped at 3x max
```

**Implementation:**
1. Calculate every 5 minutes per zone
2. Gradual changes (max 0.2x increase per interval)
3. Clear notification to customers
4. A/B testing for optimization

**Advanced:**
- Predictive surge (ML predicts 30 min ahead)
- Loyal customers get lower surge
- Premium members get capped surge

**Challenges:**
- Customer backlash → Clear communication
- Driver gaming → Surge based on accepted orders, not online count"

### Q7: How do you handle high-traffic events (10x spike)?

**Answer:**
"Preparation strategy:

**Before Event:**
1. Pre-provision 3x capacity
2. Load testing with Gatling
3. Feature flags to disable non-critical features
4. Aggressive rate limiting

**Degradation Strategy:**
- Serve stale cache if DB overloaded
- Queue non-critical updates
- Disable real-time ETA, show static estimate
- Place orders in queue if overloaded, process FIFO

**Monitoring:**
- Real-time dashboards (order rate, latency, errors)
- Auto-scaling at 70% capacity
- Alerts for anomalies"

### Q8: How do you handle the three-party coordination problem?

**Answer:**
"Unlike two-party systems (YouTube), Zomato has Customer-Restaurant-Driver:

**Challenge:**
- Order can fail at any stage (payment, restaurant, driver)
- Need distributed transaction across 3 services

**Solution: Saga Pattern**
```
Step 1: Order Service creates order → PENDING
Step 2: Payment Service charges → PAID
Step 3: Restaurant Service confirms → CONFIRMED
Step 4: Delivery Service assigns → ASSIGNED

If any step fails:
- Compensating transactions rollback previous steps
- Customer gets refund
- Restaurant notified of cancellation
```

**Implementation:**
- Each service publishes events to Kafka
- State machine tracks order lifecycle
- Timeout handlers for stuck orders
- Manual intervention queue for edge cases"

---

## SECTION 7: MONITORING & OBSERVABILITY

### 7.1 Key Metrics

**Service Level Indicators (SLIs):**
```
- Order placement success rate: > 99.9%
- Search latency (p99): < 500ms
- Order status update latency: < 2s
- Payment success rate: > 99.5%
- Driver assignment time: < 30s
```

**Business Metrics:**
```
- Orders per minute
- Average order value
- Delivery time (actual vs estimated)
- Driver utilization rate
- Restaurant acceptance rate
- Customer cancellation rate
```

### 7.2 Alerting

**Critical Alerts (PagerDuty):**
- Payment gateway down
- Order service latency > 5s
- Database connection pool exhausted
- Kafka consumer lag > 10K messages
- No available drivers in major cities

**Warning Alerts (Slack):**
- Cache hit rate < 80%
- API error rate > 1%
- Slow queries > 1s

---

## SECTION 8: TECHNOLOGY STACK

### 8.1 Service Stack
- **Java/Spring Boot**: Order, Payment (transactional)
- **Go**: Location, Delivery (high throughput)
- **Python**: Search, Analytics, ML
- **Node.js**: User, Notification (I/O intensive)

### 8.2 Data Stores
- **PostgreSQL**: Orders, Users, Payments (ACID)
- **MongoDB**: Restaurants, Menus (flexible schema)
- **Cassandra**: Location tracking (time-series)
- **Redis**: Cache, Sessions, Geospatial
- **Elasticsearch**: Restaurant search

### 8.3 Message Queue
- **Apache Kafka**: Order events, Location updates, Notifications

### 8.4 Infrastructure
- **Cloud**: AWS/GCP
- **Container Orchestration**: Kubernetes (EKS/GKE)
- **Load Balancer**: ALB/Nginx
- **CDN**: CloudFront
- **Storage**: S3 for images
- **Monitoring**: Prometheus + Grafana, ELK Stack

---


```

### Key Trade-offs Discussed
1. **ACID vs Eventual Consistency**: Strong for orders/payments, eventual for search
2. **Microservices vs Monolith**: Microservices for independent scaling
3. **Sync vs Async**: Async for notifications, sync for order placement
4. **SQL vs NoSQL**: PostgreSQL for transactions, MongoDB for flexible schemas
5. **Push vs Pull**: Push notifications for real-time updates
6. **Batch vs Real-time**: Batch location writes, real-time reads

### Must-Mention Points (Unique to Zomato)
✅ Saga pattern for distributed transactions (3-party coordination)
✅ Redis GeoRadius for driver assignment (location-based)
✅ Real-time location tracking with Cassandra + WebSocket
✅ Order state machine with cancellation policies
✅ Surge pricing algorithm (supply-demand balancing)
✅ Polyglot persistence: PostgreSQL (orders), MongoDB (menus), Cassandra (tracking)

---

**END OF INTERVIEW GUIDE**

*This guide follows YouTube-style system design interview format: Requirements → Architecture → Workflows → Scaling → Trade-offs*

*No database schemas, no code implementation, no LLD classes - just high-level design discussions*

*Total: ~650 lines | Estimated PDF: 15-18 pages*
