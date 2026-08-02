# Concert Ticket Booking System - High-Level Design

## 1. System Overview

A concert ticket booking platform enables users to discover concerts, search events by artist/venue/date, book tickets with seat selection, process payments securely, manage ticket transfers, implement anti-scalping mechanisms, handle flash sales during high-demand events, provide QR code-based entry verification, and support dynamic pricing based on demand. The system must handle millions of concurrent users during ticket releases, prevent overselling, ensure fair ticket distribution, and maintain sub-second response times.

## 2. Requirements

### Functional Requirements
- **Event Discovery**: Search concerts by artist, venue, city, date
- **Seat Selection**: Interactive seat map with availability
- **Ticket Booking**: Reserve and purchase tickets
- **Payment Processing**: Multiple payment methods, split payments
- **Ticket Management**: View, transfer, resell tickets
- **Entry Verification**: QR code scanning at venue
- **Waitlist**: Join waitlist for sold-out events
- **Notifications**: Alerts for on-sale dates, price drops
- **Anti-Scalping**: Limit tickets per user, identity verification
- **Dynamic Pricing**: Adjust prices based on demand

### Non-Functional Requirements
- **Scalability**: Handle 1M+ concurrent users during ticket drops
- **Availability**: 99.99% uptime
- **Consistency**: Strong consistency for seat inventory (no double-booking)
- **Performance**: Booking < 3s, search < 500ms
- **Fairness**: Queue system for high-demand events
- **Security**: Prevent bot attacks, secure ticket validation

## 3. Capacity Estimation

### Scale Assumptions
- **Total Users**: 50M registered, 5M DAU
- **Daily Events**: 1000 events globally
- **Average Event**: 5000 seats
- **Tickets Sold/Day**: 500K tickets
- **Peak Load**: Taylor Swift drop = 2M users in 10 minutes
- **Transaction Size**: 3KB per booking

### Storage Estimation
- **User Data**: 50M users × 2KB = 100GB
- **Event Data**: 1000 events/day × 50KB × 365 = 18.25GB/year
- **Booking Data**: 500K/day × 3KB × 365 = 547.5GB/year
- **Historical Data** (5 years): ~3TB
- **Total Storage**: ~5TB (with replicas: 15TB)

### Bandwidth
- **Search Traffic**: 5M DAU × 10 searches × 20KB = 1TB/day = 11.6MB/s
- **Booking Traffic**: 500K/day × 3KB = 1.5GB/day = 17.4KB/s
- **Peak Bandwidth**: 2M users × 20KB = 40GB in 10 min = 68MB/s

### QPS Estimation
- **Search QPS**: 50M searches/day / 86400s = 579 QPS (peak 3000 QPS)
- **Booking QPS**: 500K/day / 86400s = 5.8 QPS (peak 3333 QPS during drops)

## 4. System Architecture

```
┌──────────────┐                    ┌─────────────────┐
│   Mobile     │◄───────────────────┤   CDN (Static)  │
│   Apps       │                    │   Cloudflare    │
└──────────────┘                    └─────────────────┘
                                             │
┌──────────────┐                    ┌────────▼────────┐
│   Web App    │◄───────────────────┤  API Gateway    │
│  (React)     │                    │  (Rate Limit,   │
└──────────────┘                    │   Bot Detection)│
                                    └────────┬────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
          ┌─────────▼──────┐      ┌─────────▼─────────┐    ┌────────▼───────┐
          │  Virtual Queue │      │   Search Service  │    │   User         │
          │  Service       │      │  (Elasticsearch)  │    │   Service      │
          │  (Redis)       │      └───────────────────┘    └────────────────┘
          └─────────┬──────┘
                    │
          ┌─────────▼──────────────────────────────────────┐
          │          Booking Service                       │
          │  (Distributed Lock, Idempotency)               │
          └─────────┬──────────────────────────────────────┘
                    │
        ┌───────────┼───────────────┬──────────────────┐
        │           │               │                  │
 ┌──────▼──────┐  ┌▼────────────┐ ┌▼──────────────┐  ┌▼─────────────┐
 │  Inventory  │  │   Payment   │ │   Ticket      │  │  Waitlist    │
 │  Service    │  │   Service   │ │   Service     │  │  Service     │
 └──────┬──────┘  └┬────────────┘ └┬──────────────┘  └──────────────┘
        │           │               │
        └───────────┼───────────────┴─────────────────────┐
                    │                                      │
          ┌─────────▼──────────────────────────────┐      │
          │    Message Queue (Kafka)               │      │
          │  Topics: bookings, payments,           │      │
          │          notifications, analytics      │      │
          └─────────┬──────────────────────────────┘      │
                    │                                      │
        ┌───────────┼──────────────────────────────┐      │
        │           │                              │      │
 ┌──────▼──────┐  ┌▼───────────────┐  ┌──────────▼───┐  │
 │Notification │  │   Analytics    │  │   Fraud      │  │
 │  Service    │  │   Service      │  │   Detection  │  │
 └─────────────┘  └────────────────┘  └──────────────┘  │
                                                         │
┌────────────────────────────────────────────────────────▼──┐
│                    Data Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ PostgreSQL   │  │    Redis     │  │ Elasticsearch│   │
│  │ (Events,     │  │  (Inventory, │  │ (Event       │   │
│  │  Bookings)   │  │   Queue)     │  │  Search)     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└───────────────────────────────────────────────────────────┘
```

## 5. Core Components

### Virtual Queue Service
- **Queue Management**: Create virtual queue for high-demand events
- **Position Tracking**: Assign queue position, estimated wait time
- **Fair Entry**: FIFO entry into booking system
- **Bot Detection**: CAPTCHA, browser fingerprinting, device verification
- **Rate Limiting**: Throttle users to prevent system overload

### Booking Service
- **Seat Locking**: Pessimistic locking for selected seats (10-minute hold)
- **Idempotency**: Prevent duplicate bookings with idempotency keys
- **Two-Phase Commit**: Coordinate seat reservation → payment → confirmation
- **Timeout Management**: Release locked seats after timeout
- **Priority Handling**: VIP, presale, general sale tiers

### Inventory Service
- **Real-Time Availability**: Track available seats per event
- **Hold Management**: Manage temporary holds during checkout
- **Atomic Updates**: Use Redis atomic operations for inventory updates
- **Overbooking Prevention**: Strict consistency checks
- **Release Management**: Staged release (presale, general, last-minute)

### Payment Service
- **Payment Gateway**: Integrate Stripe, PayPal, Apple Pay
- **Split Payments**: Allow multiple payment methods per booking
- **Refund Processing**: Handle cancellations and refunds
- **PCI Compliance**: Tokenize card data
- **Retry Logic**: Exponential backoff for failed payments

### Ticket Service
- **Ticket Generation**: Create unique QR codes per ticket
- **Transfer**: Enable peer-to-peer ticket transfers
- **Resale Platform**: Manage ticket resales with price caps
- **Validation**: Verify ticket authenticity at venue
- **Anti-Duplication**: Prevent screenshot-based entry fraud

### Waitlist Service
- **Queue Management**: Maintain waitlist for sold-out events
- **Auto-Notification**: Alert when tickets become available
- **Priority Scoring**: Rank users by engagement, loyalty
- **Conversion Tracking**: Monitor waitlist-to-booking rate

## 6. Database Design

### Schema Design

```sql
-- Events Table
CREATE TABLE events (
    event_id BIGSERIAL PRIMARY KEY,
    event_name VARCHAR(255) NOT NULL,
    artist VARCHAR(255),
    venue_id INT REFERENCES venues(venue_id),
    event_date TIMESTAMP NOT NULL,
    doors_open_time TIME,
    event_type VARCHAR(50), -- CONCERT, FESTIVAL, THEATER, SPORTS
    total_capacity INT,
    available_seats INT,
    status VARCHAR(20) DEFAULT 'UPCOMING', -- UPCOMING, ON_SALE, SOLD_OUT, CANCELLED
    on_sale_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_event_date (event_date),
    INDEX idx_status (status),
    INDEX idx_artist (artist)
);

-- Venues Table
CREATE TABLE venues (
    venue_id SERIAL PRIMARY KEY,
    venue_name VARCHAR(255),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    country VARCHAR(50),
    capacity INT,
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    seat_map_url VARCHAR(500),
    INDEX idx_city (city)
);

-- Seats Table
CREATE TABLE seats (
    seat_id BIGSERIAL PRIMARY KEY,
    event_id BIGINT REFERENCES events(event_id),
    section VARCHAR(50),
    row VARCHAR(10),
    seat_number VARCHAR(10),
    seat_type VARCHAR(30), -- VIP, PREMIUM, REGULAR, ACCESSIBLE
    price DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'AVAILABLE', -- AVAILABLE, HELD, SOLD
    held_until TIMESTAMP,
    held_by INT,
    UNIQUE(event_id, section, row, seat_number),
    INDEX idx_event_status (event_id, status),
    INDEX idx_held (held_by, held_until)
);

-- Users Table
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    verified BOOLEAN DEFAULT FALSE,
    loyalty_tier VARCHAR(20), -- BRONZE, SILVER, GOLD, PLATINUM
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_email (email)
);

-- Bookings Table (Partitioned by booking_date)
CREATE TABLE bookings (
    booking_id BIGSERIAL,
    booking_reference VARCHAR(10) UNIQUE NOT NULL,
    user_id BIGINT REFERENCES users(user_id),
    event_id BIGINT REFERENCES events(event_id),
    seat_ids BIGINT[] NOT NULL,
    total_amount DECIMAL(10,2),
    booking_status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, CONFIRMED, CANCELLED
    payment_status VARCHAR(20) DEFAULT 'PENDING',
    booking_date TIMESTAMP DEFAULT NOW(),
    idempotency_key VARCHAR(100) UNIQUE,
    PRIMARY KEY (booking_id, booking_date),
    INDEX idx_user_booking (user_id, booking_date),
    INDEX idx_event_booking (event_id, booking_date),
    INDEX idx_booking_ref (booking_reference)
) PARTITION BY RANGE (booking_date);

-- Tickets Table
CREATE TABLE tickets (
    ticket_id BIGSERIAL PRIMARY KEY,
    booking_id BIGINT,
    seat_id BIGINT REFERENCES seats(seat_id),
    ticket_code VARCHAR(50) UNIQUE NOT NULL, -- QR code data
    qr_code_url VARCHAR(500),
    status VARCHAR(20) DEFAULT 'VALID', -- VALID, TRANSFERRED, USED, CANCELLED
    transferred_to INT REFERENCES users(user_id),
    used_at TIMESTAMP,
    INDEX idx_ticket_code (ticket_code),
    INDEX idx_booking (booking_id)
);

-- Waitlist Table
CREATE TABLE waitlist (
    waitlist_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    event_id BIGINT REFERENCES events(event_id),
    priority_score INT DEFAULT 0,
    joined_at TIMESTAMP DEFAULT NOW(),
    notified BOOLEAN DEFAULT FALSE,
    UNIQUE(user_id, event_id),
    INDEX idx_event_priority (event_id, priority_score DESC, joined_at)
);
```

## 7. API Design

### Search Events
```http
GET /api/v1/events/search?city=New+York&artist=Taylor+Swift&from_date=2026-06-01

Response: 200 OK
{
  "events": [
    {
      "event_id": 12345,
      "event_name": "Taylor Swift - Eras Tour",
      "artist": "Taylor Swift",
      "venue": "Madison Square Garden",
      "event_date": "2026-06-15T19:00:00Z",
      "available_seats": 1250,
      "price_range": {
        "min": 79.00,
        "max": 499.00
      },
      "status": "ON_SALE"
    }
  ]
}
```

### Join Virtual Queue
```http
POST /api/v1/events/{event_id}/queue/join
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "queue_position": 15234,
  "estimated_wait_minutes": 45,
  "queue_id": "queue_abc123",
  "message": "You're in line! Keep this page open."
}
```

### Complete Booking
```http
POST /api/v1/bookings/complete
Authorization: Bearer <jwt_token>
Idempotency-Key: <unique_key>

{
  "reservation_id": "res_xyz789",
  "payment_method": "card",
  "payment_token": "tok_visa_1234"
}

Response: 201 Created
{
  "booking_id": 98765,
  "booking_reference": "CON123XYZ",
  "status": "CONFIRMED",
  "tickets": [
    {
      "ticket_id": 111,
      "seat": "FLOOR A1",
      "ticket_code": "TCK-98765-111-ABCD1234",
      "qr_code_url": "https://tickets.concertbooking.com/qr/111"
    }
  ],
  "total_charged": 598.00
}
```

## 8. Scalability Strategy

### Virtual Queue System
```python
class VirtualQueue:
    def __init__(self, event_id):
        self.event_id = event_id
        self.queue_key = f"queue:{event_id}"
        self.processing_rate = 100  # users per minute
    
    def join_queue(self, user_id):
        timestamp = time.time()
        redis.zadd(self.queue_key, {user_id: timestamp})
        
        position = redis.zrank(self.queue_key, user_id) + 1
        estimated_wait = position / self.processing_rate
        
        return {
            "queue_position": position,
            "estimated_wait_minutes": estimated_wait
        }
```

### Seat Locking with Distributed Lock
```python
def lock_seats(seat_ids, user_id, duration=600):
    pipe = redis.pipeline()
    
    for seat_id in seat_ids:
        lock_key = f"seat_lock:{seat_id}"
        pipe.set(lock_key, json.dumps({
            "user_id": user_id,
            "expires_at": time.time() + duration
        }), nx=True, ex=duration)
    
    results = pipe.execute()
    
    if all(results):
        return {"success": True, "expires_at": time.time() + duration}
    else:
        release_seats(seat_ids, user_id)
        return {"success": False, "error": "Some seats unavailable"}
```

### Database Sharding
```
Shard Key Strategy:
- Events: Shard by event_date (temporal locality)
- Bookings: Partition by booking_date (monthly)
- Seats: Shard by event_id (co-locate event and seats)

Read Replicas:
- 3 read replicas per shard
- Event search → read replicas
- Seat availability → Redis (cache)
```

## 9. Fault Tolerance & High Availability

### Anti-Scalping Mechanisms
```python
def detect_scalper(user_id, event_id):
    user_tickets = db.count("""
        SELECT COUNT(*) FROM bookings
        WHERE user_id = %s AND event_id = %s
    """, (user_id, event_id))
    
    if user_tickets >= MAX_TICKETS_PER_USER:
        return {"blocked": True, "reason": "Ticket limit exceeded"}
    
    recent_bookings = redis.get(f"velocity:{user_id}")
    if recent_bookings > 5:
        return {"blocked": True, "reason": "Suspicious activity"}
    
    device_hash = get_device_fingerprint(request)
    accounts_on_device = redis.smembers(f"device:{device_hash}")
    if len(accounts_on_device) > 3:
        return {"blocked": True, "reason": "Multiple accounts on same device"}
    
    return {"blocked": False}
```

### Ticket Validation at Venue
```python
def validate_ticket(ticket_code):
    ticket = db.get_ticket(ticket_code)
    
    if not ticket:
        return {"valid": False, "reason": "Ticket not found"}
    
    if ticket.status != 'VALID':
        return {"valid": False, "reason": f"Ticket status: {ticket.status}"}
    
    if ticket.used_at:
        return {"valid": False, "reason": "Ticket already scanned"}
    
    db.execute("""
        UPDATE tickets 
        SET status = 'USED', used_at = NOW()
        WHERE ticket_id = %s
    """, (ticket.ticket_id,))
    
    return {"valid": True, "seat": ticket.seat}
```

## 10. Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Frontend** | React + Next.js | SEO, server-side rendering |
| **API Gateway** | Kong | Rate limiting, bot detection |
| **Backend** | Node.js / Go | High concurrency |
| **Primary DB** | PostgreSQL 14+ | ACID, partitioning |
| **Cache** | Redis Cluster | Real-time inventory, queue |
| **Search** | Elasticsearch | Full-text search |
| **Message Queue** | Apache Kafka | Event streaming |
| **CDN** | Cloudflare | Global edge caching |
| **Payment** | Stripe | PCI-compliant |
| **Monitoring** | Datadog | Real-time monitoring |

## 11. Interview Discussion Points

### Q1: How do you prevent bots from buying all tickets?

**Answer**: Multi-layered bot detection with CAPTCHA, rate limiting, browser fingerprinting, and behavioral analysis to identify and block automated bots.

### Q2: How do you handle seat locking during checkout?

**Answer**: Use Redis atomic operations with distributed locks and 10-minute timeout. Lua scripts ensure atomicity across multiple seat locks.

### Q3: How do you implement fair queue during high-demand ticket drops?

**Answer**: Virtual queue with token bucket algorithm. Users join FIFO queue, admitted at controlled rate (100/min) to prevent system overload.

### Q4: How do you prevent duplicate QR code fraud?

**Answer**: Generate cryptographically signed ticket codes with HMAC. Validate signature at entry and use atomic Redis operation to mark as used (one-time use only).

### Q5: How do you handle refunds and cancellations?

**Answer**: Saga pattern with compensating transactions. Cancel booking, release seats, process refund, invalidate tickets, and notify waitlist users automatically.

---

**End of Document**
