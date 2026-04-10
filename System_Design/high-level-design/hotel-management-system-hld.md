# Hotel Management System - High Level Design

## 1. Overview

A comprehensive hotel management system handles end-to-end hotel operations including room booking, guest management, housekeeping, billing, inventory management, and staff coordination. The system serves both customer-facing booking functionality and internal hotel operations management.

**Key Features:**
- Room search and availability checking
- Online booking and reservation management
- Guest check-in/check-out processing
- Room assignment and management
- Housekeeping and maintenance tracking
- Point of Sale (POS) for restaurants and services
- Billing and payment processing
- Inventory management
- Staff management and scheduling
- Reporting and analytics

## 2. Requirements

### 2.1 Functional Requirements

**Core Features:**

1. **Booking Management**
   - Search hotels by location, dates, amenities
   - Check room availability in real-time
   - Room booking with multiple room types
   - Booking modification and cancellation
   - Group booking support
   - Corporate booking and contracts

2. **Room Management**
   - Room inventory management
   - Room type configuration (Single, Double, Suite, etc.)
   - Pricing and rate management
   - Dynamic pricing based on occupancy and season
   - Room status tracking (Available, Occupied, Maintenance, etc.)

3. **Guest Management**
   - Guest profile creation and management
   - Guest history and preferences
   - Loyalty program management
   - Guest communication (email, SMS)
   - Special requests handling

4. **Check-in/Check-out**
   - Online check-in
   - Self-service kiosks
   - Front desk check-in/check-out
   - Key card management
   - Early check-in and late check-out

5. **Housekeeping Management**
   - Room cleaning schedules
   - Task assignment to housekeeping staff
   - Room status updates (Clean, Dirty, Inspected)
   - Maintenance request management
   - Inventory tracking (linens, toiletries)

6. **Payment and Billing**
   - Multiple payment methods
   - Invoice generation
   - Split billing
   - Currency support
   - Refund processing
   - Integration with accounting systems

7. **Additional Services**
   - Restaurant and room service
   - Spa and wellness bookings
   - Event and conference room booking
   - Concierge services
   - Laundry services

8. **Staff Management**
   - Employee profiles and roles
   - Shift scheduling
   - Task management
   - Performance tracking

### 2.2 Non-Functional Requirements

1. **Availability**: 99.9% uptime
2. **Scalability**: Support 1000+ hotels, millions of bookings
3. **Performance**:
   - Search results < 2s
   - Booking confirmation < 3s
   - Real-time availability updates
4. **Security**: PCI-DSS compliance, data encryption
5. **Reliability**: No double bookings, accurate inventory
6. **Compliance**: GDPR, data privacy regulations
7. **Multi-tenancy**: Support multiple hotel chains with data isolation

### 2.3 Extended Requirements

- Mobile app for guests and staff
- Integration with OTAs (Booking.com, Expedia)
- Channel manager for multi-platform distribution
- Revenue management system
- CRM integration
- Business intelligence and analytics
- Multi-language and multi-currency support

## 3. Capacity Estimation and Constraints

### 3.1 Traffic Estimates

**Assumptions:**
- 1,000 hotels in the system
- Average 100 rooms per hotel = 100,000 rooms
- Average occupancy rate: 70%
- Average stay: 3 nights
- Daily bookings: (100,000 * 0.7) / 3 = 23,333 bookings/day
- Search to booking ratio: 50:1

**Calculations:**
- Bookings per second (average): 23,333 / 86400 = 0.27 bookings/sec
- Bookings per second (peak): 0.27 * 10 = 2.7 bookings/sec
- Search queries: 2.7 * 50 = 135 QPS
- Read:Write ratio: 20:1

### 3.2 Storage Estimates

**Data per booking:**
- Booking record: 3 KB
- Guest information: 2 KB
- Payment information: 1 KB
- Total per booking: ~6 KB

**Storage calculation:**
- Daily bookings: 23,333 * 6 KB = 140 MB/day
- Annual: 140 MB * 365 = 51 GB/year
- 5-year retention: 255 GB

**Other data:**
- Hotel data: 1,000 hotels * 100 KB = 100 MB
- Room data: 100,000 rooms * 10 KB = 1 GB
- Guest profiles: 1M guests * 5 KB = 5 GB
- Historical data (5 years): 255 GB

**Total storage:** ~300 GB with replication

### 3.3 Bandwidth Estimates

**Incoming:**
- Bookings: 2.7 bookings/sec * 5 KB = 13.5 KB/s
- Status updates: 100 updates/sec * 1 KB = 100 KB/s
- Total: ~150 KB/s

**Outgoing:**
- Search results: 135 QPS * 100 KB = 13.5 MB/s
- Booking confirmations: 2.7/sec * 10 KB = 27 KB/s
- Total: ~14 MB/s

## 4. System Architecture

### 4.1 High-Level Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Guest Portal │    │ Hotel Staff  │    │  Admin Panel │
│  (Web/App)   │    │     App      │    │              │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                    │
       └───────────────────┼────────────────────┘
                           │
                  ┌────────▼─────────┐
                  │   API Gateway    │
                  │  (Auth, Routing) │
                  └────────┬─────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
│  Booking    │    │    Room     │    │   Guest     │
│  Service    │    │   Service   │    │  Service    │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                   │                   │
┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
│  Payment    │    │ Housekeeping│    │   Staff     │
│  Service    │    │   Service   │    │  Service    │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                   │                   │
┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
│ Notification│    │  Inventory  │    │  Analytics  │
│  Service    │    │   Service   │    │   Service   │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
              ┌────────────▼────────────┐
              │   Message Queue (RabbitMQ)  │
              └────────────┬────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
│ PostgreSQL  │    │   MongoDB   │    │    Redis    │
│ (Bookings)  │    │   (Hotels)  │    │   (Cache)   │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
│Elasticsearch│    │      S3     │    │  TimescaleDB│
│  (Search)   │    │   (Images)  │    │ (Analytics) │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 4.2 Multi-Tenancy Architecture

**Data Isolation Strategies:**
1. **Database per Tenant**: Separate database for each hotel chain (high isolation)
2. **Schema per Tenant**: Separate schema within shared database
3. **Row-level Isolation**: Shared tables with tenant_id column (our choice for efficiency)

## 5. Core Components

### 5.1 Booking Service

**Responsibilities:**
- Search available rooms by criteria
- Calculate pricing with dynamic rates
- Create and manage reservations
- Handle booking modifications and cancellations
- Prevent double bookings with locking
- Integration with channel manager for OTA bookings

**Booking State Machine:**
```
REQUESTED → CONFIRMED → CHECKED_IN → CHECKED_OUT → COMPLETED
                ↓
          CANCELLED (with refund policy)
                ↓
          MODIFIED (room change, date change)
```

**Concurrency Control:**
- Optimistic locking with version numbers
- Distributed locks (Redis) for critical sections
- Database transactions with isolation level SERIALIZABLE

**Technology:**
- Service: Java/Spring Boot
- Database: PostgreSQL (ACID transactions)
- Cache: Redis for availability
- Queue: RabbitMQ for async processing

### 5.2 Room Service

**Responsibilities:**
- Room inventory management
- Room type configuration
- Rate management (rack rate, seasonal rates)
- Room status tracking
- Room assignment algorithm
- Amenity management

**Room Status:**
- AVAILABLE: Ready for booking
- OCCUPIED: Guest checked in
- RESERVED: Booked but not checked in
- BLOCKED: Not available for booking
- MAINTENANCE: Under repair
- DIRTY: Needs cleaning
- CLEAN: Cleaned and ready

**Room Assignment Algorithm:**
1. Check guest preferences (floor, view, bed type)
2. Check guest history (assign favorite room if available)
3. Optimize for housekeeping efficiency (group dirty rooms)
4. Balance wear across rooms (rotate usage)

**Technology:**
- Service: Java/Spring Boot
- Database: PostgreSQL
- Cache: Redis for real-time status

### 5.3 Guest Service

**Responsibilities:**
- Guest profile management (CRUD)
- Guest preference tracking
- Loyalty program management (points, tiers)
- Guest history (past bookings, spending)
- Communication preferences
- Special requests management

**Guest Profile:**
```json
{
  "guest_id": "G123456",
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "loyalty_tier": "Gold",
  "loyalty_points": 5000,
  "preferences": {
    "floor": "high",
    "bed_type": "king",
    "pillow_type": "soft",
    "room_features": ["city_view", "quiet"]
  },
  "stay_history": [...],
  "total_bookings": 15,
  "total_spent": 25000
}
```

**Technology:**
- Service: Node.js
- Database: MongoDB (flexible schema)
- Cache: Redis

### 5.4 Housekeeping Service

**Responsibilities:**
- Generate cleaning schedules based on checkouts
- Task assignment to housekeeping staff
- Room inspection workflows
- Maintenance request tracking
- Inventory management (linens, toiletries)
- Priority-based task ordering

**Workflow:**
1. Guest checks out → Room marked DIRTY
2. Housekeeping assigned cleaning task
3. Staff cleans room → Mark as CLEAN
4. Supervisor inspects → Mark as INSPECTED
5. Room becomes AVAILABLE

**Priority Levels:**
- URGENT: Expected check-in within 1 hour
- HIGH: Expected check-in within 4 hours
- NORMAL: Standard turnover
- LOW: Preventive cleaning

**Technology:**
- Service: Python/Django
- Database: PostgreSQL
- Real-time: WebSockets for task updates
- Mobile: React Native for staff app

### 5.5 Payment Service

**Responsibilities:**
- Payment processing (credit card, cash, corporate billing)
- Pre-authorization and capture
- Split billing support
- Invoice generation
- Refund processing
- Integration with accounting systems
- Multi-currency support

**Payment Flow:**
1. **Booking**: Pre-authorize full amount or deposit
2. **Check-in**: Hold additional amount for incidentals
3. **Stay**: Add charges (room service, minibar, etc.)
4. **Check-out**: Calculate final bill, capture payment
5. **Post-checkout**: Handle disputes, partial refunds

**Security:**
- PCI-DSS Level 1 compliance
- Tokenization for card storage
- Encrypted communication
- Fraud detection

**Technology:**
- Service: Java/Spring Boot
- Database: PostgreSQL
- Payment Gateway: Stripe, PayPal
- Encryption: AES-256

### 5.6 Notification Service

**Responsibilities:**
- Booking confirmations
- Check-in reminders
- Room ready notifications
- Promotional campaigns
- Bill notifications
- Multi-channel delivery (Email, SMS, Push)

**Notification Types:**
- Transactional: Booking confirmations, invoices
- Operational: Room ready, housekeeping updates
- Marketing: Promotions, loyalty rewards

**Technology:**
- Service: Node.js
- Queue: RabbitMQ for async delivery
- Email: SendGrid
- SMS: Twilio
- Push: Firebase Cloud Messaging

### 5.7 Analytics Service

**Responsibilities:**
- Revenue reporting
- Occupancy analytics
- Revenue per Available Room (RevPAR)
- Average Daily Rate (ADR)
- Guest analytics (demographics, behavior)
- Staff performance metrics
- Predictive analytics for demand forecasting

**Key Metrics:**
```
Occupancy Rate = (Occupied Rooms / Total Rooms) * 100
ADR = Total Room Revenue / Rooms Sold
RevPAR = Total Room Revenue / Total Available Rooms
        = ADR * Occupancy Rate
```

**Technology:**
- Stream Processing: Apache Flink
- Database: TimescaleDB (time-series)
- Warehouse: Snowflake
- Visualization: Tableau/Grafana

### 5.8 Integration Service

**Responsibilities:**
- Channel Manager integration (OTAs)
- Property Management System (PMS) integration
- Central Reservation System (CRS) sync
- Third-party service integrations (spa, tours)
- Webhook management

**Technology:**
- Service: Node.js
- API: RESTful with webhook support
- Protocol: OAuth 2.0 for authentication

## 6. Database Design

### 6.1 Hotel and Room Schema (PostgreSQL)

```sql
hotels
- id (PK)
- tenant_id (for multi-tenancy)
- name
- address
- city
- country
- star_rating
- total_rooms
- amenities (JSONB)
- check_in_time
- check_out_time
- cancellation_policy (JSONB)
- created_at
- updated_at

room_types
- id (PK)
- hotel_id (FK)
- name (Single, Double, Suite)
- description
- base_price
- max_occupancy
- bed_type
- size_sqft
- amenities (JSONB)
- images (JSONB)

rooms
- id (PK)
- hotel_id (FK)
- room_type_id (FK)
- room_number
- floor
- status (ENUM: available, occupied, maintenance, blocked)
- last_cleaned_at
- notes

room_rates
- id (PK)
- room_type_id (FK)
- rate_type (rack, seasonal, corporate)
- start_date
- end_date
- price
- day_of_week
```

### 6.2 Booking Schema (PostgreSQL)

```sql
bookings
- id (PK)
- hotel_id (FK)
- guest_id (FK)
- booking_reference (unique)
- check_in_date
- check_out_date
- num_adults
- num_children
- status (requested, confirmed, checked_in, checked_out, cancelled)
- total_amount
- payment_status
- special_requests (TEXT)
- booking_source (direct, OTA, phone)
- created_at
- updated_at
- version (for optimistic locking)

booking_rooms
- id (PK)
- booking_id (FK)
- room_id (FK)
- room_type_id (FK)
- check_in_date
- check_out_date
- rate_per_night
- num_nights
- subtotal

room_availability
- room_id (PK)
- date (PK)
- status (available, booked, blocked)
- booking_id (FK, nullable)
```

### 6.3 Guest Schema (MongoDB)

```javascript
guests: {
  _id: ObjectId,
  guest_id: "G123456",
  first_name: "John",
  last_name: "Doe",
  email: "john@example.com",
  phone: "+1234567890",
  date_of_birth: Date,
  nationality: "US",
  passport_number: "encrypted",
  loyalty: {
    tier: "Gold",
    points: 5000,
    member_since: Date
  },
  preferences: {
    room_type: "King",
    floor_preference: "high",
    pillow_type: "soft",
    amenities: ["gym", "pool"]
  },
  payment_methods: [
    {
      type: "credit_card",
      token: "encrypted_token",
      is_default: true
    }
  ],
  addresses: [
    {
      type: "home",
      address_line1: "123 Main St",
      city: "New York",
      country: "US",
      is_default: true
    }
  ],
  stay_history: [
    {
      hotel_id: "H123",
      check_in: Date,
      check_out: Date,
      room_number: "501",
      total_spent: 500
    }
  ],
  created_at: Date,
  updated_at: Date
}
```

### 6.4 Housekeeping Schema (PostgreSQL)

```sql
housekeeping_tasks
- id (PK)
- hotel_id (FK)
- room_id (FK)
- task_type (cleaning, maintenance, inspection)
- priority (urgent, high, normal, low)
- status (pending, assigned, in_progress, completed)
- assigned_to (FK to staff)
- scheduled_at
- started_at
- completed_at
- notes

maintenance_requests
- id (PK)
- hotel_id (FK)
- room_id (FK)
- issue_type (plumbing, electrical, furniture, etc.)
- description
- priority
- status
- reported_by (FK to staff/guest)
- assigned_to (FK to staff)
- created_at
- resolved_at
```

### 6.5 Caching Strategy (Redis)

```
room_availability:{hotel_id}:{date} → Available room IDs (TTL: 1 hour)
hotel:{hotel_id} → Hotel details (TTL: 1 day)
guest:{guest_id} → Guest profile (TTL: 1 hour)
rate:{room_type_id}:{date} → Room rate (TTL: 1 hour)
booking:{booking_id} → Booking details (TTL: 1 hour)
lock:room:{room_id}:{date} → Distributed lock for booking (TTL: 5 min)
```

## 7. API Design

### 7.1 Search and Availability APIs

```
POST /api/v1/hotels/search
  Body: { 
    location: "New York", 
    check_in: "2026-05-01", 
    check_out: "2026-05-05",
    guests: 2,
    room_types: ["Double", "Suite"],
    amenities: ["pool", "gym"],
    price_range: { min: 100, max: 500 }
  }
  Response: { 
    hotels: [
      {
        id, name, rating, address, 
        available_rooms: [{room_type, price, availability}],
        total_price
      }
    ],
    total, page
  }

GET /api/v1/hotels/{hotel_id}/availability
  Query: check_in, check_out, room_type_id
  Response: { available: true, rooms: [...], rates: {...} }
```

### 7.2 Booking APIs

```
POST /api/v1/bookings
  Body: {
    hotel_id, guest_id,
    check_in_date, check_out_date,
    rooms: [{room_type_id, quantity}],
    guests: {adults: 2, children: 0},
    special_requests: "High floor",
    payment_method_id
  }
  Response: {
    booking_id, booking_reference,
    confirmation_number, total_amount,
    status
  }

GET /api/v1/bookings/{booking_id}
  Response: { booking details with rooms, guest, payment }

PUT /api/v1/bookings/{booking_id}
  Body: { check_in_date, check_out_date, rooms }
  Response: { updated booking, price_difference }

DELETE /api/v1/bookings/{booking_id}
  Body: { cancellation_reason }
  Response: { success, refund_amount, cancellation_fee }

GET /api/v1/bookings/history
  Query: guest_id, status, page
  Response: { bookings: [...], total }
```

### 7.3 Check-in/Check-out APIs

```
POST /api/v1/check-in
  Body: { booking_id, guest_id, signature, id_verification }
  Response: { 
    success, room_number, key_card_code,
    wifi_credentials, checkout_time
  }

POST /api/v1/check-out
  Body: { booking_id, additional_charges }
  Response: {
    success, final_bill, payment_status,
    invoice_url
  }

POST /api/v1/express-checkout
  Body: { booking_id, payment_method_id }
  Response: { success, invoice_url, loyalty_points_earned }
```

### 7.4 Housekeeping APIs (Staff)

```
GET /api/v1/housekeeping/tasks
  Query: staff_id, status, priority
  Response: { tasks: [...], total }

PUT /api/v1/housekeeping/tasks/{task_id}/status
  Body: { status: "in_progress", notes }
  Response: { success, updated_task }

POST /api/v1/maintenance/requests
  Body: { room_id, issue_type, description, priority }
  Response: { request_id, status }

PUT /api/v1/rooms/{room_id}/status
  Body: { status: "clean", inspected_by }
  Response: { success, room_status }
```

### 7.5 Guest Management APIs

```
POST /api/v1/guests
  Body: { first_name, last_name, email, phone, preferences }
  Response: { guest_id, loyalty_number }

GET /api/v1/guests/{guest_id}
  Response: { guest profile with history and preferences }

PUT /api/v1/guests/{guest_id}
  Body: { updated fields }
  Response: { success, updated_guest }

GET /api/v1/guests/{guest_id}/bookings
  Query: status, page
  Response: { bookings: [...], loyalty_points }
```

### 7.6 Admin/Analytics APIs

```
GET /api/v1/analytics/occupancy
  Query: hotel_id, start_date, end_date
  Response: { occupancy_rate, adr, revpar, trend }

GET /api/v1/analytics/revenue
  Query: hotel_id, period
  Response: { total_revenue, room_revenue, service_revenue, breakdown }

GET /api/v1/reports/housekeeping
  Query: hotel_id, date
  Response: { completed_tasks, pending_tasks, staff_performance }
```

## 8. Scalability and Performance

### 8.1 Preventing Double Bookings

**Critical Challenge:** Two users trying to book the last available room simultaneously.

**Solutions:**

**1. Pessimistic Locking:**
```sql
BEGIN TRANSACTION;
SELECT * FROM room_availability 
WHERE room_id = 101 AND date = '2026-05-01' 
FOR UPDATE;

-- Check if available
-- If available, update status to booked

COMMIT;
```

**2. Distributed Lock (Redis):**
```python
lock_key = f"lock:room:{room_id}:{date}"
if redis.set(lock_key, user_id, nx=True, ex=300):  # 5 min TTL
    # Check availability and book
    redis.delete(lock_key)
else:
    return "Room is being booked by another user"
```

**3. Optimistic Locking:**
```sql
UPDATE room_availability 
SET status = 'booked', version = version + 1
WHERE room_id = 101 AND date = '2026-05-01' 
  AND status = 'available' AND version = 5;

-- If rows affected = 0, booking failed
```

**Our Approach:** Distributed lock + Optimistic locking
- Redis lock for coordination
- Database version for data integrity

### 8.2 Database Optimization

**Indexing:**
```sql
CREATE INDEX idx_room_availability_date ON room_availability(room_id, date);
CREATE INDEX idx_bookings_guest ON bookings(guest_id, check_in_date);
CREATE INDEX idx_bookings_hotel_date ON bookings(hotel_id, check_in_date, check_out_date);
CREATE INDEX idx_rooms_hotel_status ON rooms(hotel_id, status);
```

**Partitioning:**
- Partition `bookings` by check_in_date (monthly range partitioning)
- Partition `room_availability` by date (daily range partitioning)
- Archive old bookings (> 2 years) to cold storage

**Connection Pooling:**
- HikariCP for PostgreSQL (pool size: CPU cores * 2)
- MongoDB connection pool (100 connections per instance)

### 8.3 Caching Strategy

**Cache Layers:**
1. **L1 - Application Cache**: In-memory cache for static data (hotel details)
2. **L2 - Redis Cache**: Distributed cache for frequently accessed data
3. **L3 - CDN**: Static assets (images, CSS, JS)

**Cache Patterns:**
- **Cache-Aside**: Application checks cache, then DB if miss
- **Write-Through**: Write to cache and DB simultaneously
- **Cache Invalidation**: Event-driven (on booking, status change)

### 8.4 Horizontal Scaling

**Stateless Services:**
- All microservices are stateless
- Session stored in Redis
- Load balanced with round-robin

**Database Scaling:**
- **Read Replicas**: PostgreSQL master-slave replication
- **Sharding**: Shard by hotel_id for multi-hotel chains
- **CQRS**: Separate read and write models for bookings

### 8.5 High Availability

**Service Level:**
- Multi-AZ deployment (AWS)
- Auto-scaling based on CPU/memory
- Health checks and automatic failover

**Database Level:**
- PostgreSQL: Streaming replication with automatic failover
- MongoDB: Replica set with 3 nodes
- Redis: Sentinel for HA, Cluster for scaling

**Disaster Recovery:**
- Automated backups (daily full, hourly incremental)
- Point-in-time recovery (PITR)
- Cross-region replication for critical data

## 9. Technology Stack

### 9.1 Backend Services

**Languages & Frameworks:**
- Java/Spring Boot: Booking, Payment services (transactional)
- Python/Django: Housekeeping, Analytics services
- Node.js/Express: Guest, Notification services
- Go: Integration service (high throughput)

### 9.2 Databases

**Relational:**
- PostgreSQL: Bookings, Payments, Rooms (ACID required)
- TimescaleDB: Analytics time-series data

**NoSQL:**
- MongoDB: Guest profiles, Hotel details (flexible schema)
- Redis: Caching, Session, Distributed locks

**Search:**
- Elasticsearch: Hotel and room search with filters

### 9.3 Message Queue

**RabbitMQ:**
- Booking confirmations
- Notification delivery
- Housekeeping task assignments
- Inventory updates

### 9.4 Infrastructure

**Cloud Platform:** AWS
- Compute: ECS for containers
- Load Balancer: Application Load Balancer (ALB)
- Storage: S3 for images and documents
- CDN: CloudFront

**Monitoring:**
- Logging: ELK Stack (Elasticsearch, Logstash, Kibana)
- Metrics: Prometheus + Grafana
- APM: New Relic
- Alerting: PagerDuty

### 9.5 Frontend

**Guest Portal:**
- React.js: Web application
- React Native: Mobile apps (iOS, Android)

**Staff Applications:**
- React Native: Housekeeping app, Front desk app
- React.js: Admin dashboard

## 10. Interview Questions & Answers

### Q1: How do you prevent double bookings in a distributed system?

**Answer:**
Double booking is the most critical issue in hotel management systems. We use a multi-layered approach:

**Layer 1 - Distributed Lock:**
Before checking availability, acquire a distributed lock using Redis:
```python
lock_key = f"lock:room:{room_id}:dates:{check_in}-{check_out}"
lock_acquired = redis.set(lock_key, booking_session_id, nx=True, ex=300)
```
- Lock timeout: 5 minutes (sufficient for booking flow)
- If lock acquisition fails, inform user "Room is being booked"

**Layer 2 - Optimistic Locking:**
Database table includes version column:
```sql
UPDATE room_availability 
SET status = 'booked', booking_id = 123, version = version + 1
WHERE room_id = 101 AND date BETWEEN '2026-05-01' AND '2026-05-05'
  AND status = 'available' AND version = 5;
```
- If affected rows = 0, booking conflict detected
- Retry with updated version

**Layer 3 - Database Transaction Isolation:**
```sql
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
-- Check availability
-- Create booking
-- Update room status
COMMIT;
```

**Layer 4 - Inventory Reconciliation:**
- Background job runs every 5 minutes
- Checks for inconsistencies between cache and database
- Alerts on mismatches

**Edge Cases:**
1. **Lock timeout while user is booking**: Release lock on timeout, ask user to retry
2. **System crash during booking**: Lock auto-expires, booking is rolled back
3. **Network partition**: Database is source of truth, eventual consistency

### Q2: How do you design the room availability system for efficient queries?

**Answer:**
Room availability queries are the most frequent operations and must be highly optimized:

**Data Model Design:**

**Option 1 - Availability Table (Our Choice):**
```sql
room_availability (room_id, date, status, booking_id)
Primary Key: (room_id, date)
```
- Pre-populate table for next 2 years
- One row per room per day
- Storage: 100,000 rooms * 730 days * 100 bytes = 7.3 GB

**Pros:**
- O(1) lookup for availability
- Simple query: `SELECT * FROM room_availability WHERE date BETWEEN ? AND ? AND status = 'available'`
- Easy to lock specific dates

**Cons:**
- Higher storage
- Need to pre-populate data

**Option 2 - Booking-Centric (Rejected):**
```sql
bookings (booking_id, room_id, check_in, check_out)
```
- Query: Find rooms with NO overlapping bookings
- Complex query with date range overlap checks
- Slower performance

**Optimization Strategies:**

**1. Indexing:**
```sql
CREATE INDEX idx_availability_date_status ON room_availability(date, status, room_id);
CREATE INDEX idx_availability_room ON room_availability(room_id, date) WHERE status = 'available';
```

**2. Caching:**
```python
# Cache available room counts per day
key = f"available:{hotel_id}:{date}"
available_rooms = redis.get(key)
if not available_rooms:
    available_rooms = db.query(...)
    redis.setex(key, 3600, available_rooms)
```

**3. Denormalization:**
Store room_type_id in availability table to avoid joins:
```sql
room_availability (room_id, room_type_id, date, status)
```

**4. Partitioning:**
Partition by date (monthly):
```sql
CREATE TABLE room_availability_2026_05 PARTITION OF room_availability
FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
```

**5. Read Replicas:**
- Route availability queries to read replicas
- Route bookings to master
- Reduces load on master database

**Query Performance:**
- Without optimization: 500ms for 100 rooms, 7 nights
- With indexing: 50ms
- With caching: 5ms

### Q3: How do you handle dynamic pricing and rate management?

**Answer:**
Dynamic pricing maximizes revenue by adjusting rates based on demand, seasonality, and other factors:

**Rate Types:**

1. **Rack Rate**: Base rate for each room type
2. **Seasonal Rates**: Higher during peak season (holidays, events)
3. **Corporate Rates**: Negotiated rates for business clients
4. **Early Bird Rates**: Discounts for advance bookings
5. **Last Minute Rates**: Discounts for unsold inventory
6. **Length-of-Stay Rates**: Discounts for longer stays

**Pricing Algorithm:**

**Base Price Calculation:**
```python
def calculate_price(room_type, check_in, check_out, booking_date):
    base_price = room_type.rack_rate
    
    # Factor 1: Occupancy-based pricing
    occupancy_rate = get_occupancy_rate(check_in)
    if occupancy_rate > 0.8:
        base_price *= 1.3  # 30% increase
    elif occupancy_rate > 0.6:
        base_price *= 1.15  # 15% increase
    elif occupancy_rate < 0.3:
        base_price *= 0.8  # 20% discount
    
    # Factor 2: Days until check-in
    days_ahead = (check_in - booking_date).days
    if days_ahead > 60:
        base_price *= 0.9  # Early bird discount
    elif days_ahead < 7:
        base_price *= 1.1  # Last minute premium
    
    # Factor 3: Day of week
    if check_in.weekday() in [4, 5]:  # Friday, Saturday
        base_price *= 1.2
    
    # Factor 4: Special events
    if is_event_date(check_in):
        base_price *= 1.5
    
    # Factor 5: Length of stay
    num_nights = (check_out - check_in).days
    if num_nights >= 7:
        base_price *= 0.9  # Weekly discount
    
    return base_price
```

**Revenue Management System (RMS):**
- ML model predicts demand based on historical data
- Recommends optimal prices to maximize RevPAR
- Considers competitor pricing

**Implementation:**

**Database Schema:**
```sql
room_rates (
  room_type_id, rate_type, start_date, end_date,
  day_of_week, price, min_length_of_stay
)

pricing_rules (
  id, hotel_id, rule_type, condition, action, priority
)
```

**Caching Strategy:**
```python
# Cache computed prices for common queries
key = f"price:{room_type_id}:{check_in}:{check_out}"
price = redis.get(key)
if not price:
    price = calculate_price(...)
    redis.setex(key, 1800, price)  # 30 min TTL
```

**Price Consistency:**
- Prices locked at time of booking
- Price changes don't affect existing bookings
- Store booked price in booking record

### Q4: How do you design the housekeeping management system?

**Answer:**
Efficient housekeeping is critical for guest satisfaction and operational efficiency:

**Task Generation:**

**Automatic Task Creation:**
1. **On Checkout**: Generate cleaning task for room
2. **Stay-over**: Generate maintenance cleaning task
3. **Scheduled**: Generate preventive maintenance tasks
4. **On-demand**: Guest requests (extra towels, etc.)

**Priority Assignment:**
```python
def assign_priority(room_id, check_in_time, next_booking):
    time_until_checkin = (next_booking.check_in - now()).total_seconds() / 3600
    
    if time_until_checkin < 1:
        return "URGENT"  # Guest waiting
    elif time_until_checkin < 4:
        return "HIGH"  # Check-in soon
    elif next_booking is None:
        return "LOW"  # No immediate booking
    else:
        return "NORMAL"
```

**Task Assignment Algorithm:**

**Factors:**
1. **Staff Location**: Assign tasks on same floor/building
2. **Staff Workload**: Balance tasks across staff
3. **Staff Skills**: Assign maintenance tasks to qualified staff
4. **Priority**: URGENT tasks first

**Algorithm:**
```python
def assign_tasks(pending_tasks, available_staff):
    # Group tasks by floor
    tasks_by_floor = group_by_floor(pending_tasks)
    
    # For each staff member
    for staff in available_staff:
        # Find tasks on staff's current floor
        floor_tasks = tasks_by_floor[staff.current_floor]
        
        # Sort by priority and proximity
        sorted_tasks = sort_by_priority_and_proximity(floor_tasks, staff.location)
        
        # Assign tasks until workload limit
        while staff.remaining_capacity > 0 and sorted_tasks:
            task = sorted_tasks.pop(0)
            assign_task(task, staff)
            staff.remaining_capacity -= task.estimated_duration
```

**Real-time Updates:**

**WebSocket for Staff App:**
```javascript
// Staff app receives real-time task assignments
websocket.on('new_task', (task) => {
  showNotification("New task assigned: Room " + task.room_number);
  updateTaskList(task);
});

websocket.on('task_priority_changed', (task) => {
  updateTaskPriority(task);
});
```

**Room Status Tracking:**
```
DIRTY → ASSIGNED → IN_PROGRESS → CLEAN → INSPECTED → AVAILABLE
```

**Inspection Workflow:**
- Supervisor inspects random 20% of cleaned rooms
- If failed, reassign to original cleaner
- If passed, mark as AVAILABLE

**Inventory Management:**
- Track linen and toiletry usage per room
- Auto-generate restock requests when low
- Forecast needs based on occupancy

**Performance Metrics:**
- Average cleaning time per room type
- Tasks completed per shift
- Quality score (inspection pass rate)
- Guest satisfaction correlation

### Q5: How do you handle multi-tenancy for hotel chains?

**Answer:**
Multi-tenancy allows multiple hotel chains to use the same platform with data isolation:

**Isolation Strategies:**

**Our Approach - Row-Level Isolation:**
Every table has tenant_id (hotel_chain_id):
```sql
hotels (id, tenant_id, name, ...)
bookings (id, tenant_id, hotel_id, ...)
guests (id, tenant_id, name, ...)
```

**Pros:**
- Cost-effective (shared infrastructure)
- Easy to manage
- Supports cross-chain analytics

**Cons:**
- Risk of data leakage (must be careful with queries)
- Performance impact if one tenant is very large

**Safeguards:**

**1. Query-Level Enforcement:**
```java
@Filter(name = "tenantFilter", 
        condition = "tenant_id = :tenantId")
@Entity
public class Booking {
    // Hibernate automatically adds tenant_id to all queries
}
```

**2. Application-Level Context:**
```java
public class TenantContext {
    private static ThreadLocal<String> currentTenant = new ThreadLocal<>();
    
    public static void setCurrentTenant(String tenantId) {
        currentTenant.set(tenantId);
    }
    
    public static String getCurrentTenant() {
        return currentTenant.get();
    }
}

// In API Gateway
@Before
public void setTenantContext(HttpRequest request) {
    String tenantId = extractTenantFromToken(request.getHeader("Authorization"));
    TenantContext.setCurrentTenant(tenantId);
}
```

**3. Database-Level Security:**
```sql
-- Row-Level Security in PostgreSQL
CREATE POLICY tenant_isolation_policy ON bookings
USING (tenant_id = current_setting('app.current_tenant')::int);

ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
```

**4. Indexing for Performance:**
```sql
-- Composite index with tenant_id as first column
CREATE INDEX idx_bookings_tenant_hotel ON bookings(tenant_id, hotel_id, check_in_date);
```

**Alternative Approaches:**

**Schema-per-Tenant:**
```sql
tenant_1.bookings
tenant_2.bookings
tenant_3.bookings
```
- Better isolation
- More complex management
- Used for very large tenants

**Database-per-Tenant:**
```
tenant_1_db
tenant_2_db
tenant_3_db
```
- Maximum isolation
- Expensive to manage
- Used for regulatory compliance (healthcare, finance)

**Tenant Configuration:**
- Custom branding per tenant
- Feature flags (enable/disable features)
- Rate limits per tenant
- Custom integrations per tenant

**Monitoring:**
- Per-tenant metrics (requests, errors, latency)
- Per-tenant billing
- Resource usage tracking

### Q6: How do you integrate with Online Travel Agencies (OTAs)?

**Answer:**
Integration with OTAs like Booking.com and Expedia requires a Channel Manager:

**Channel Manager Architecture:**

**Components:**
1. **Inventory Sync**: Push room availability to OTAs
2. **Rate Sync**: Push pricing to OTAs
3. **Booking Import**: Receive bookings from OTAs
4. **Status Sync**: Update booking status

**Synchronization Flow:**

**Outbound (Hotel → OTA):**
```
Hotel System → Channel Manager → OTA APIs

1. Room availability changes → Push to all connected OTAs
2. Rate changes → Push to all connected OTAs
3. Booking cancellation → Notify OTAs
```

**Inbound (OTA → Hotel):**
```
OTA → Channel Manager → Hotel System

1. New booking received → Create booking in hotel system
2. Booking modification → Update existing booking
3. Booking cancellation → Cancel in hotel system
```

**Implementation:**

**Webhook for Real-time Updates:**
```python
@app.route('/webhook/booking.com', methods=['POST'])
def handle_booking_webhook():
    payload = request.json
    
    if payload['event'] == 'new_booking':
        booking = create_booking_from_ota(payload)
        update_room_availability(booking.rooms, booking.dates)
        send_confirmation(booking)
    
    elif payload['event'] == 'cancellation':
        cancel_booking(payload['booking_id'])
        release_rooms(payload['rooms'], payload['dates'])
    
    return {'status': 'success'}
```

**Availability Push:**
```python
def sync_availability_to_otas(hotel_id, date_range):
    availability = get_availability(hotel_id, date_range)
    
    for ota in get_connected_otas(hotel_id):
        ota_client = get_ota_client(ota.name)
        
        # Transform data to OTA format
        ota_payload = transform_availability(availability, ota.format)
        
        # Push to OTA
        try:
            ota_client.update_availability(ota_payload)
        except Exception as e:
            log_error(f"Failed to sync with {ota.name}: {e}")
            retry_queue.add(ota, ota_payload)
```

**Rate Parity:**
- Ensure consistent pricing across all channels
- Some OTAs require "best rate guarantee"
- Penalties for rate disparity

**Booking Attribution:**
- Track which channel generated booking
- Commission calculation (10-25% for OTAs)
- ROI analysis per channel

**Challenges:**

**1. Inventory Overbooking:**
- OTA has cached old availability
- Two bookings happen simultaneously
- Solution: Maintain buffer inventory, overselling protection

**2. Rate Discrepancies:**
- OTA shows different rate than hotel website
- Solution: Centralized rate management, frequent sync

**3. Booking Conflicts:**
- OTA booking arrives after direct booking for same room
- Solution: Real-time inventory sync, automatic room reassignment

**4. Data Mapping:**
- Different room type names across OTAs
- Solution: Mapping table for room types

```sql
ota_room_mappings (
  hotel_id, ota_name, ota_room_id, 
  internal_room_type_id, room_name_mapping
)
```

### Q7: How do you design the analytics and reporting system?

**Answer:**
Analytics provides insights for revenue optimization and operational efficiency:

**Key Metrics:**

**Revenue Metrics:**
- **ADR (Average Daily Rate)**: Total room revenue / rooms sold
- **RevPAR (Revenue Per Available Room)**: Total room revenue / total rooms
- **Occupancy Rate**: Rooms sold / total rooms available
- **TRevPAR**: Total revenue (rooms + services) / total rooms

**Operational Metrics:**
- Room cleaning time
- Guest satisfaction score
- Staff utilization rate
- Maintenance response time

**Architecture:**

**Data Pipeline:**
```
Operational DB → Change Data Capture (CDC) → Kafka → 
Stream Processing (Flink) → Data Warehouse (Snowflake) → 
BI Tool (Tableau/Grafana)
```

**Stream Processing (Apache Flink):**
```java
DataStream<Booking> bookings = env.addSource(new FlinkKafkaConsumer<>(...));

// Calculate real-time occupancy
DataStream<OccupancyMetric> occupancy = bookings
    .keyBy(booking -> booking.getHotelId())
    .window(TumblingEventTimeWindows.of(Time.minutes(5)))
    .aggregate(new OccupancyAggregator());

// Calculate real-time revenue
DataStream<RevenueMetric> revenue = bookings
    .keyBy(booking -> booking.getHotelId())
    .window(TumblingEventTimeWindows.of(Time.hours(1)))
    .sum("totalAmount");
```

**Data Warehouse Schema (Star Schema):**

**Fact Tables:**
```sql
fact_bookings (
  booking_id, hotel_id, guest_id, room_type_id,
  check_in_date_id, check_out_date_id,
  booking_date_id, revenue, num_nights
)

fact_occupancy (
  date_id, hotel_id, room_type_id,
  total_rooms, occupied_rooms, available_rooms,
  blocked_rooms, occupancy_rate
)
```

**Dimension Tables:**
```sql
dim_hotel (hotel_id, name, city, country, star_rating)
dim_date (date_id, date, day_of_week, month, year, is_weekend, is_holiday)
dim_room_type (room_type_id, name, category, max_occupancy)
dim_guest (guest_id, loyalty_tier, nationality, age_group)
```

**Real-time Dashboard:**
- Current occupancy by hotel
- Revenue today vs. same day last year
- Booking pace (bookings for future dates)
- Top performing hotels/room types

**Predictive Analytics:**

**Demand Forecasting:**
```python
# ML model to predict occupancy
features = [
    'day_of_week', 'month', 'is_holiday', 'local_events',
    'days_until_date', 'historical_occupancy', 'competitor_rates'
]

model = train_xgboost_model(features, target='occupancy_rate')

# Predict occupancy for next 30 days
predictions = model.predict(future_features)

# Adjust pricing based on predictions
recommended_rates = optimize_pricing(predictions, current_rates)
```

**Guest Segmentation:**
- Business travelers (weekday stays, corporate rates)
- Leisure travelers (weekend stays, longer duration)
- Loyal guests (frequent stays, high lifetime value)
- Price-sensitive guests (book during promotions)

**Churn Prediction:**
- Identify guests at risk of not returning
- Targeted retention campaigns
- Personalized offers

This comprehensive design covers all aspects of a modern hotel management system suitable for both independent hotels and large chains, with emphasis on scalability, data consistency, and revenue optimization.
