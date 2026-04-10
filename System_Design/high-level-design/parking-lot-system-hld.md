# High-Level Design: Parking Lot System

## System Overview
Design a scalable, distributed parking lot management system that handles multiple parking locations, real-time availability tracking, payment processing, and mobile app integration.

---

## Requirements

### Functional Requirements
1. **Multi-location Support**: Manage 100+ parking facilities across multiple cities
2. **Real-time Availability**: Show available spots with <1 second latency
3. **Reservation System**: Book parking spots 24 hours in advance
4. **Payment Processing**: Handle 10,000+ transactions/hour
5. **Mobile App**: iOS/Android apps for booking and navigation
6. **Analytics Dashboard**: Occupancy trends, revenue reports
7. **Dynamic Pricing**: Surge pricing during peak hours

### Non-Functional Requirements
1. **Scalability**: Support 1M+ users, 100K+ daily transactions
2. **Availability**: 99.9% uptime (8.76 hours downtime/year)
3. **Latency**: API response < 200ms (p95), < 100ms (p50)
4. **Consistency**: Strong consistency for bookings (no double booking)
5. **Security**: PCI-DSS compliant payment processing
6. **Disaster Recovery**: RPO < 1 hour, RTO < 4 hours

---

## Capacity Estimation

### Traffic
- **Total Users**: 1M active users
- **Daily Active Users (DAU)**: 200K (20%)
- **Peak Hours**: 8-10 AM, 5-7 PM (3x normal traffic)
- **Requests per second (RPS)**: 
  - Average: ~100 RPS
  - Peak: ~300 RPS
- **Write:Read Ratio**: 1:10 (more reads than writes)

### Storage
- **User Data**: 1M users × 1KB = 1GB
- **Parking Lots**: 100 locations × 100KB = 10MB
- **Parking Spots**: 100 lots × 500 spots × 500B = 25MB
- **Bookings**: 100K/day × 365 days × 2KB = 73GB/year
- **Payment Records**: 100K/day × 365 days × 1KB = 36.5GB/year
- **Total (5 years)**: ~500GB

### Bandwidth
- **Incoming**: 100 RPS × 2KB = 200KB/s = 1.6 Mbps
- **Outgoing**: 1000 RPS × 5KB = 5MB/s = 40 Mbps

---

## System Architecture

### High-Level Components

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Mobile    │────▶│     CDN     │────▶│Load Balancer│
│   App       │     │             │     │   (ALB)     │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
┌─────────────┐                                 │
│   Web       │                                 │
│   Portal    │─────────────────────────────────┤
└─────────────┘                                 │
                                                ▼
                    ┌────────────────────────────────────┐
                    │      API Gateway (Kong/AWS)        │
                    │  - Auth | Rate Limiting | Logging  │
                    └─────────────┬──────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐        ┌───────────────┐        ┌───────────────┐
│   Booking     │        │   Search      │        │   Payment     │
│   Service     │        │   Service     │        │   Service     │
│               │        │               │        │               │
└───────┬───────┘        └───────┬───────┘        └───────┬───────┘
        │                        │                        │
        ▼                        ▼                        ▼
┌───────────────┐        ┌───────────────┐        ┌───────────────┐
│   Postgres    │        │   ElasticSearch│       │   Stripe API  │
│   (Master)    │        │   (Search DB)  │        │               │
└───────┬───────┘        └───────────────┘        └───────────────┘
        │
        ▼
┌───────────────┐        ┌───────────────┐        ┌───────────────┐
│   Postgres    │        │   Redis       │        │   Kafka       │
│   (Replicas)  │        │   (Cache)     │        │   (Events)    │
└───────────────┘        └───────────────┘        └───────────────┘
```

---

## Core Components

### 1. API Gateway
**Technology**: Kong / AWS API Gateway / Nginx

**Responsibilities**:
- Request routing to microservices
- Authentication & Authorization (JWT)
- Rate limiting (100 req/min per user)
- Request/Response transformation
- API versioning
- Logging & monitoring

**Why**:
- Single entry point for all clients
- Centralized security & rate limiting
- Decouples clients from service topology

### 2. Booking Service
**Technology**: Java Spring Boot / Node.js Express

**Responsibilities**:
- Create/Cancel reservations
- Check spot availability
- Handle booking state transitions
- Implement distributed locking
- Emit booking events to Kafka

**Database**: PostgreSQL (ACID compliance for booking integrity)

**API Endpoints**:
```
POST   /api/v1/bookings              # Create booking
GET    /api/v1/bookings/{id}         # Get booking details
DELETE /api/v1/bookings/{id}         # Cancel booking
GET    /api/v1/bookings/user/{id}    # User's bookings
PUT    /api/v1/bookings/{id}/extend  # Extend booking
```

**Scaling Strategy**:
- Horizontal scaling with stateless instances
- Database read replicas for read queries
- Redis for distributed locks (Redlock algorithm)
- Event sourcing for booking history

### 3. Search Service
**Technology**: Python FastAPI / Go

**Responsibilities**:
- Search available parking spots
- Filter by location, price, vehicle type
- Real-time availability updates
- Geospatial queries (find nearby lots)

**Database**: Elasticsearch (for fast full-text and geo search)

**API Endpoints**:
```
GET /api/v1/search?lat=37.7&lon=-122.4&radius=5km
GET /api/v1/search?location=Downtown&date=2026-04-10
GET /api/v1/parking-lots/{id}/availability
```

**Optimization**:
- Cache popular search results (Redis)
- Geohash for proximity searches
- Pre-aggregate availability counts

### 4. Payment Service
**Technology**: Java Spring Boot

**Responsibilities**:
- Process payments via Stripe/PayPal
- Handle refunds for cancellations
- Store payment records
- PCI-DSS compliance
- Retry logic for failed payments

**Integration**: Stripe API / PayPal SDK

**Flow**:
1. Create payment intent
2. Client completes payment (Stripe.js)
3. Webhook confirms payment
4. Update booking status
5. Emit payment event

**Idempotency**: Use idempotency keys to prevent duplicate charges

### 5. Notification Service
**Technology**: Node.js / Python

**Responsibilities**:
- Send booking confirmations (Email/SMS)
- Push notifications (parking time expiring)
- Real-time alerts (spot reserved)

**Integrations**:
- **Email**: SendGrid / AWS SES
- **SMS**: Twilio
- **Push**: Firebase Cloud Messaging (FCM)

**Pattern**: Event-driven (consumes Kafka events)

### 6. Analytics Service
**Technology**: Python / Spark

**Responsibilities**:
- Occupancy trends over time
- Revenue analytics
- Peak hour identification
- User behavior analysis

**Data Pipeline**:
```
Kafka → Spark Streaming → Data Warehouse (Redshift/BigQuery) → Tableau/Grafana
```

---

## Database Design

### PostgreSQL Schema

#### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_users_email ON users(email);
```

#### Parking Lots Table
```sql
CREATE TABLE parking_lots (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    total_spots INT,
    available_spots INT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_parking_lots_location ON parking_lots USING GIST (
    ll_to_earth(latitude, longitude)
);
```

#### Parking Spots Table
```sql
CREATE TABLE parking_spots (
    id UUID PRIMARY KEY,
    lot_id UUID REFERENCES parking_lots(id),
    spot_number VARCHAR(10),
    vehicle_type ENUM('CAR', 'TRUCK', 'MOTORCYCLE'),
    status ENUM('AVAILABLE', 'OCCUPIED', 'RESERVED'),
    floor INT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_spots_lot_status ON parking_spots(lot_id, status);
```

#### Bookings Table
```sql
CREATE TABLE bookings (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    spot_id UUID REFERENCES parking_spots(id),
    lot_id UUID REFERENCES parking_lots(id),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    status ENUM('PENDING', 'CONFIRMED', 'CANCELLED', 'COMPLETED'),
    total_price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_bookings_user ON bookings(user_id, status);
CREATE INDEX idx_bookings_spot_time ON bookings(spot_id, start_time, end_time);
```

#### Payments Table
```sql
CREATE TABLE payments (
    id UUID PRIMARY KEY,
    booking_id UUID REFERENCES bookings(id),
    amount DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    payment_method ENUM('CARD', 'WALLET', 'UPI'),
    status ENUM('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED'),
    stripe_payment_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_payments_booking ON payments(booking_id);
```

---

## Caching Strategy

### Redis Cache Layers

#### L1: Availability Cache (Hot Data)
```
Key: parking_lot:{lot_id}:availability
Value: {available_spots: 45, last_updated: timestamp}
TTL: 30 seconds
```

#### L2: Booking Cache
```
Key: booking:{booking_id}
Value: {user_id, spot_id, status, ...}
TTL: 1 hour
```

#### L3: Search Results Cache
```
Key: search:{lat}:{lon}:{radius}:{vehicle_type}
Value: [list of available parking lots]
TTL: 5 minutes
```

### Cache Invalidation
- **Write-through**: Update DB → Update Cache
- **Event-driven**: Booking created → Invalidate availability cache
- **TTL-based**: Expire stale data automatically

---

## Preventing Double Booking

### Problem
Two users try to book the same spot simultaneously → Race condition

### Solution: Distributed Locking with Redis

```java
public Booking createBooking(BookingRequest request) {
    String lockKey = "lock:spot:" + request.getSpotId();
    RLock lock = redisson.getLock(lockKey);
    
    try {
        // Try to acquire lock (wait max 5s, lock expires in 10s)
        if (lock.tryLock(5, 10, TimeUnit.SECONDS)) {
            // Check availability
            if (isSpotAvailable(request.getSpotId(), request.getStartTime())) {
                // Create booking in DB (within transaction)
                Booking booking = bookingRepository.save(request);
                
                // Update spot status
                spotRepository.updateStatus(request.getSpotId(), "RESERVED");
                
                // Invalidate cache
                cacheService.invalidate("parking_lot:" + booking.getLotId());
                
                return booking;
            } else {
                throw new SpotNotAvailableException();
            }
        } else {
            throw new BookingLockTimeoutException();
        }
    } finally {
        lock.unlock();
    }
}
```

**Alternative**: Optimistic Locking with version field in database

---

## Scalability & High Availability

### Horizontal Scaling
- **API Gateway**: Auto-scaling group (2-10 instances)
- **Booking Service**: Kubernetes HPA (5-50 pods)
- **Search Service**: Auto-scaling (3-20 instances)
- **Payment Service**: 3-10 instances (stateless)

### Database Scaling
```
┌──────────────┐
│   Master     │ ◀── Writes
│  PostgreSQL  │
└───────┬──────┘
        │ (Replication)
        ▼
┌──────────────┐
│   Replica 1  │ ◀── Reads (Search queries)
└──────────────┘
        │
        ▼
┌──────────────┐
│   Replica 2  │ ◀── Reads (Analytics)
└──────────────┘
```

**Read-Write Split**: 
- Writes → Master
- Reads → Replicas (with load balancing)

### Data Partitioning (Sharding)
**Strategy**: Shard by `parking_lot_id`

**Why**: 
- Most queries are location-specific
- Evenly distributes data
- Avoids hotspots

**Example**:
```
Shard 1: lot_id % 4 == 0
Shard 2: lot_id % 4 == 1
Shard 3: lot_id % 4 == 2
Shard 4: lot_id % 4 == 3
```

---

## Fault Tolerance

### Circuit Breaker Pattern
Prevent cascading failures when payment service is down:

```java
@CircuitBreaker(
    name = "paymentService",
    fallbackMethod = "paymentFallback"
)
public PaymentResponse processPayment(PaymentRequest request) {
    return paymentClient.charge(request);
}

public PaymentResponse paymentFallback(PaymentRequest request, Exception e) {
    // Queue for retry
    retryQueue.add(request);
    return new PaymentResponse(PENDING, "Will retry shortly");
}
```

### Retry Mechanism
Exponential backoff for transient failures:
- Attempt 1: Immediate
- Attempt 2: After 1s
- Attempt 3: After 2s
- Attempt 4: After 4s
- Max 5 attempts

### Health Checks
```
GET /health
{
  "status": "UP",
  "database": "UP",
  "redis": "UP",
  "kafka": "UP"
}
```

---

## Security

### Authentication & Authorization
- **JWT Tokens**: Expire in 1 hour, refresh tokens for 7 days
- **OAuth 2.0**: Google/Facebook login
- **Role-based Access Control (RBAC)**: User, Admin, ParkingAttendant

### Data Encryption
- **In Transit**: TLS 1.3 for all API calls
- **At Rest**: Database encryption (AWS RDS encryption)
- **PCI-DSS**: Tokenize credit card data (use Stripe tokens)

### Rate Limiting
```
User: 100 requests/minute
Admin: 1000 requests/minute
Anonymous: 10 requests/minute
```

---

## Monitoring & Observability

### Metrics (Prometheus + Grafana)
- **Golden Signals**:
  - Latency (p50, p95, p99)
  - Traffic (RPS)
  - Errors (5xx rate)
  - Saturation (CPU, memory, DB connections)

- **Business Metrics**:
  - Bookings per hour
  - Revenue per hour
  - Cancellation rate
  - Average booking duration

### Logging (ELK Stack)
```
API Gateway → Logstash → Elasticsearch → Kibana
```

**Log Levels**:
- ERROR: Payment failures, booking failures
- WARN: High latency, cache misses
- INFO: Booking created, payment completed

### Distributed Tracing (Jaeger)
Track requests across microservices:
```
Mobile App → API Gateway → Booking Service → DB
                        → Payment Service → Stripe
```

### Alerting (PagerDuty)
- **P0 (Critical)**: Service down, database down
- **P1 (High)**: Error rate > 5%, latency > 2s
- **P2 (Medium)**: Disk usage > 80%, high memory

---

## Interview Discussion Points

### Q1: How do you handle peak traffic (3x normal)?
**Answer**: 
- Auto-scaling: Kubernetes HPA scales pods based on CPU (70% threshold)
- Read replicas: Scale out database reads
- CDN: Cache static assets (images, JS/CSS)
- Rate limiting: Protect backend from overload
- Queue: Defer non-critical operations (email notifications)

### Q2: What if Redis cache goes down?
**Answer**:
- **Fallback**: Query database directly (slower but works)
- **Graceful degradation**: Show cached results with warning
- **Redis Sentinel**: Automatic failover to replica
- **Circuit breaker**: Stop trying Redis after 3 failures

### Q3: How do you ensure payment consistency?
**Answer**:
- **Two-phase commit**: Reserve spot → Charge payment → Confirm booking
- **Idempotency**: Use idempotency keys (Stripe feature)
- **Saga pattern**: Compensating transactions on failure
- **Dead letter queue**: Retry failed payments
- **Reconciliation job**: Daily job to match payments with bookings

### Q4: How would you scale to 10M users?
**Answer**:
- **Multi-region deployment**: US-East, US-West, EU, Asia
- **Database sharding**: Shard by city/country
- **CDN**: CloudFront for global distribution
- **NoSQL for reads**: Cassandra for high read throughput
- **Event sourcing**: Store events instead of state

### Q5: What's your data retention strategy?
**Answer**:
- **Hot data** (last 3 months): PostgreSQL (fast queries)
- **Warm data** (3-12 months): S3 + Athena (cheaper storage)
- **Cold data** (> 1 year): Glacier (archival)
- **GDPR compliance**: Delete user data on request

---

## Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Load Balancer** | AWS ALB / Nginx | High availability, SSL termination |
| **API Gateway** | Kong / AWS API Gateway | Centralized routing, auth |
| **Backend** | Java Spring Boot / Node.js | Mature, scalable, large ecosystem |
| **Database** | PostgreSQL | ACID, relational data |
| **Cache** | Redis | In-memory, sub-millisecond latency |
| **Search** | Elasticsearch | Full-text & geo search |
| **Message Queue** | Kafka | Event streaming, high throughput |
| **Storage** | AWS S3 | Object storage for images |
| **Monitoring** | Prometheus + Grafana | Metrics & dashboards |
| **Logging** | ELK Stack | Centralized logs |
| **Tracing** | Jaeger | Distributed tracing |
| **Container** | Docker + Kubernetes | Orchestration, auto-scaling |
| **CI/CD** | Jenkins / GitLab CI | Automation |
| **Cloud** | AWS / GCP | Managed services |

---

## Deployment Architecture

### Multi-Region Setup
```
           ┌──────────────────┐
           │   Route 53 (DNS) │
           │   Geo-routing    │
           └────────┬─────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐       ┌───────────────┐
│   US-EAST-1   │       │   US-WEST-2   │
│               │       │               │
│  ┌─────────┐  │       │  ┌─────────┐  │
│  │  ALB    │  │       │  │  ALB    │  │
│  └────┬────┘  │       │  └────┬────┘  │
│       │       │       │       │       │
│  ┌────┴────┐  │       │  ┌────┴────┐  │
│  │  EKS    │  │       │  │  EKS    │  │
│  │ Cluster │  │       │  │ Cluster │  │
│  └────┬────┘  │       │  └────┬────┘  │
│       │       │       │       │       │
│  ┌────┴────┐  │       │  ┌────┴────┐  │
│  │   RDS   │  │       │  │   RDS   │  │
│  │ Primary │──┼───────┼─▶│ Replica │  │
│  └─────────┘  │       │  └─────────┘  │
└───────────────┘       └───────────────┘
```

---

## Cost Estimation (Monthly)

| Service | Specification | Cost |
|---------|--------------|------|
| **EC2** | 10 × t3.medium (24/7) | $300 |
| **RDS PostgreSQL** | db.r5.xlarge + 2 replicas | $800 |
| **Elasticache Redis** | cache.r5.large | $200 |
| **Elasticsearch** | 3-node cluster | $500 |
| **S3** | 100GB storage | $5 |
| **CloudFront CDN** | 1TB transfer | $85 |
| **EKS** | Cluster + nodes | $400 |
| **Load Balancer** | ALB | $30 |
| **Kafka (MSK)** | 3-broker cluster | $250 |
| **Monitoring** | CloudWatch | $100 |
| **Total** | | **~$2,670/month** |

---

## Future Enhancements

1. **AI/ML Features**:
   - Predict parking demand
   - Dynamic pricing based on demand
   - Recommend optimal parking spots

2. **IoT Integration**:
   - Sensor-based real-time occupancy
   - Automatic license plate recognition
   - Smart parking gates

3. **EV Charging**:
   - Find spots with EV chargers
   - Track charging status
   - Charge for electricity usage

4. **Valet Service**:
   - Request valet parking
   - Track car location
   - Digital key sharing

---

**This HLD covers a production-ready, scalable parking system handling millions of users!** 🚀
