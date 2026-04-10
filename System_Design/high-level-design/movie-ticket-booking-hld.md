# Movie Ticket Booking System - High-Level Design

## System Overview
A movie ticket booking platform like BookMyShow, Fandango, or Atom Tickets allows users to browse movies, select theaters and showtimes, choose seats with real-time seat availability, and complete payments. The system handles high concurrency during blockbuster releases, prevents double-booking through distributed locking, and manages complex relationships between theaters, screens, shows, and seats.

## Requirements

### Functional Requirements
1. **Movie Management**: Browse movies, view details, ratings, reviews, trailers
2. **Theater & Screen Management**: Multi-city, multi-theater, multi-screen support
3. **Showtime Management**: Dynamic show scheduling, pricing variations (matinee, prime)
4. **Seat Selection**: Interactive seat map, real-time availability, seat types (regular, premium, recliner)
5. **Booking Flow**: Search, select seats, apply offers, payment, ticket generation
6. **Payment Processing**: Multiple payment methods, wallets, gift cards, refunds
7. **Seat Locking**: Temporary lock during checkout (10 minutes), auto-release on timeout
8. **Ticket Management**: E-tickets, QR codes, cancellation, refunds
9. **Concessions**: Food and beverage orders, combo offers
10. **User Management**: Profiles, booking history, favorites, notifications
11. **Admin Panel**: Theater managers can add shows, manage pricing, view analytics

### Non-Functional Requirements
- **Availability**: 99.95% uptime (21 minutes downtime/month)
- **Consistency**: Strong consistency for seat bookings, eventual for movie listings
- **Latency**: P95 < 200ms for search, < 500ms for seat selection
- **Throughput**: 10,000 concurrent bookings during peak (blockbuster releases)
- **Scalability**: Support 50M users, 100K theaters, 500K screens globally
- **Concurrency**: Handle 100K users viewing same show without double-booking
- **Data Retention**: Bookings for 3 years, user data indefinitely

## Capacity Estimation

### Traffic Estimates
- **Daily Active Users (DAU)**: 5M users
- **Bookings per day**: 2M bookings (40% conversion from browsing)
- **Average tickets per booking**: 2.5 tickets
- **Total tickets per day**: 5M tickets
- **Bookings per second (BPS)**: 2M / 86400 = 23 BPS (average)
- **Peak BPS**: 23 * 50 = 1,150 BPS (Friday evening, blockbuster releases)
- **Read:Write Ratio**: 95:5 (browsing vs actual bookings)

### Storage Estimates
- **Movies**: 50KB per movie * 10K active movies = 500MB
- **Theaters**: 10KB per theater * 100K theaters = 1GB
- **Screens**: 5KB per screen * 500K screens = 2.5GB
- **Shows**: 2KB per show * 10M shows/year = 20GB/year
- **Bookings**: 5KB per booking * 2M bookings/day * 365 days = 3.65TB/year
- **Users**: 10KB per user * 50M users = 500GB
- **Total Storage (3 years with replication 3x)**: (3.65TB * 3 + 1GB) * 3 = 33TB

### Bandwidth Estimates
- **Incoming**: 23 BPS * 3KB (avg request) = 69 KB/s = 0.55 Mbps
- **Outgoing**: 23 BPS * 50KB (seat map + details) = 1.15 MB/s = 9.2 Mbps
- **Peak Bandwidth**: 9.2 Mbps * 50 = 460 Mbps

### Cache Estimates
- **Hot Movies (top 100)**: 100 * 50KB = 5MB
- **Hot Showtimes (next 48 hours)**: 100K shows * 2KB = 200MB
- **Seat Maps (cached)**: 10K hot screens * 50KB = 500MB
- **User Sessions**: 500K concurrent * 10KB = 5GB
- **Total Cache**: 6GB (easily fit in single Redis instance)

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Client Applications                                │
│              (Mobile Apps, Web Browser, Cinema Kiosks)                       │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ HTTPS
┌──────────────────────────────▼──────────────────────────────────────────────┐
│                         CDN (CloudFront)                                     │
│           (Static Assets: Images, Trailers, Seat Maps)                       │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────────┐
│                API Gateway (Kong) + Load Balancer                            │
│           (Rate Limiting, Authentication, SSL Termination)                   │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────────┘
       │          │          │          │          │          │
  ┌────▼────┐ ┌──▼─────┐ ┌──▼────┐ ┌───▼────┐ ┌──▼─────┐ ┌──▼────────┐
  │ Movie   │ │Theater │ │Booking│ │Payment │ │ User   │ │Notification│
  │ Service │ │Service │ │Service│ │Service │ │Service │ │  Service  │
  └────┬────┘ └───┬────┘ └───┬───┘ └───┬────┘ └───┬────┘ └─────┬─────┘
       │          │          │         │          │            │
  ┌────▼──────────▼──────────▼─────────▼──────────▼────────────▼─────┐
  │                  Redis Cluster (Cache + Locks)                    │
  │      (Seat Locks, Session, Movie Cache, Showtime Cache)           │
  └────────────────────────────┬──────────────────────────────────────┘
                               │
  ┌────────────────────────────▼──────────────────────────────────────┐
  │             PostgreSQL Cluster (Primary + Replicas)                │
  │  (Movies, Theaters, Shows, Bookings, Seats, Users, Payments)      │
  └────────────────────────────┬──────────────────────────────────────┘
                               │
  ┌────────────────────────────▼──────────────────────────────────────┐
  │                  Kafka (Event Streaming)                           │
  │      (Booking Events, Payment Events, Notification Events)         │
  └──────┬────────────┬──────────────┬──────────────┬─────────────────┘
         │            │              │              │
    ┌────▼───┐  ┌────▼─────┐  ┌─────▼────┐  ┌──────▼──────┐
    │Analytics│  │Email/SMS │  │Seat Lock │  │  Metrics    │
    │ Worker │  │  Worker  │  │ Cleanup  │  │ Aggregation │
    └─────────┘  └──────────┘  └──────────┘  └─────────────┘

┌──────────────────────────────────────────────────────────────────┐
│              External Integrations                                │
├─────────────┬─────────────┬──────────────┬─────────────────────┤
│ Payment     │ TMDB/OMDB   │ Email/SMS    │ Cinema POS          │
│ Gateways    │ (Movie Data)│ (Twilio)     │ (Ticket Printers)   │
└─────────────┴─────────────┴──────────────┴─────────────────────┘
```

## Core Components

### 1. Movie Service
**Responsibilities**:
- Movie catalog management (titles, descriptions, trailers, posters)
- Genre, language, cast, crew information
- Ratings and reviews aggregation
- Movie search and filtering
- Sync with external movie databases (TMDB, OMDB)

**Technology**: Spring Boot, PostgreSQL
**Cache**: Redis (hot movies, search results)
**CDN**: CloudFront (images, trailers)

### 2. Theater Service
**Responsibilities**:
- Theater and screen management
- Location-based theater search
- Screen layout configuration (seat arrangement)
- Amenities (parking, food court, accessibility)
- Operating hours and holidays

**Technology**: Spring Boot, PostgreSQL with PostGIS
**Cache**: Redis (theater locations, screen layouts)

### 3. Showtime Service
**Responsibilities**:
- Show scheduling and management
- Dynamic pricing (matinee, prime time, weekend)
- Show status (upcoming, live, houseful, cancelled)
- Seat availability calculation
- Show search by movie, theater, time

**Technology**: Spring Boot, PostgreSQL
**Cache**: Redis (upcoming shows for next 48 hours)

**Key Operations**:
```java
// Get available seats for a show
public SeatMap getAvailableSeats(String showId) {
    // Check cache first
    SeatMap cached = redis.get("show:seats:" + showId);
    if (cached != null && !cached.isExpired()) {
        return cached;
    }
    
    // Fetch from database
    Show show = showRepository.findById(showId);
    List<Seat> allSeats = seatRepository.findByScreenId(show.getScreenId());
    List<Booking> bookings = bookingRepository.findByShowId(showId);
    Set<String> lockedSeats = seatLockService.getLockedSeats(showId);
    
    // Calculate availability
    SeatMap seatMap = new SeatMap();
    for (Seat seat : allSeats) {
        if (bookings.stream().anyMatch(b -> b.getSeatIds().contains(seat.getId()))) {
            seat.setStatus(SeatStatus.BOOKED);
        } else if (lockedSeats.contains(seat.getId())) {
            seat.setStatus(SeatStatus.LOCKED);
        } else {
            seat.setStatus(SeatStatus.AVAILABLE);
        }
        seatMap.addSeat(seat);
    }
    
    // Cache for 10 seconds (high churn during booking)
    redis.setex("show:seats:" + showId, 10, seatMap);
    
    return seatMap;
}
```

### 4. Booking Service
**Responsibilities**:
- Seat selection and locking mechanism
- Booking creation and confirmation
- Ticket generation with QR codes
- Cancellation and refund processing
- Booking history and management

**Technology**: Spring Boot, PostgreSQL
**Distributed Lock**: Redis (Redlock algorithm)
**Pattern**: Saga pattern for booking workflow

**Critical: Seat Locking Mechanism**:
```java
@Service
public class SeatLockService {
    
    private static final int LOCK_TIMEOUT_SECONDS = 600; // 10 minutes
    
    public boolean lockSeats(String showId, List<String> seatIds, String userId) {
        String lockKey = "lock:show:" + showId;
        
        try {
            // Acquire distributed lock for this show
            boolean acquired = redisLock.tryLock(lockKey, 5, TimeUnit.SECONDS);
            if (!acquired) {
                throw new LockAcquisitionException("Could not acquire lock");
            }
            
            // Check if seats are available
            for (String seatId : seatIds) {
                String seatLockKey = "seat:lock:" + showId + ":" + seatId;
                
                // Check if seat is already locked or booked
                if (redis.exists(seatLockKey)) {
                    return false; // Seat already locked by someone else
                }
                
                // Check if seat is booked
                boolean isBooked = bookingRepository.existsByShowIdAndSeatId(showId, seatId);
                if (isBooked) {
                    return false;
                }
            }
            
            // Lock all seats
            for (String seatId : seatIds) {
                String seatLockKey = "seat:lock:" + showId + ":" + seatId;
                redis.setex(seatLockKey, LOCK_TIMEOUT_SECONDS, userId);
            }
            
            // Store user's locked seats for easy lookup
            String userLockKey = "user:locks:" + userId;
            redis.setex(userLockKey, LOCK_TIMEOUT_SECONDS, 
                       showId + ":" + String.join(",", seatIds));
            
            return true;
            
        } finally {
            redisLock.unlock(lockKey);
        }
    }
    
    public void releaseSeats(String showId, List<String> seatIds) {
        for (String seatId : seatIds) {
            String seatLockKey = "seat:lock:" + showId + ":" + seatId;
            redis.del(seatLockKey);
        }
    }
    
    @Scheduled(fixedRate = 60000) // Run every minute
    public void cleanupExpiredLocks() {
        // Redis TTL handles this automatically
        // This method logs expired locks for analytics
    }
}
```

**Booking Workflow (Saga Pattern)**:
```java
@Service
public class BookingOrchestrator {
    
    @Transactional
    public BookingResult createBooking(BookingRequest request) {
        String sagaId = UUID.randomUUID().toString();
        
        try {
            // Step 1: Validate show and seats
            validateShowAndSeats(request);
            
            // Step 2: Lock seats (already done in previous step)
            // Seats should already be locked by user
            verifySeatsLocked(request.getShowId(), request.getSeatIds(), 
                             request.getUserId());
            
            // Step 3: Calculate total amount
            BigDecimal totalAmount = pricingService.calculateTotal(
                request.getShowId(), request.getSeatIds(), 
                request.getConcessions());
            
            // Step 4: Create booking record (PENDING status)
            Booking booking = new Booking();
            booking.setId(sagaId);
            booking.setUserId(request.getUserId());
            booking.setShowId(request.getShowId());
            booking.setSeatIds(request.getSeatIds());
            booking.setTotalAmount(totalAmount);
            booking.setStatus(BookingStatus.PENDING);
            bookingRepository.save(booking);
            
            // Step 5: Process payment
            PaymentResult payment = paymentService.processPayment(
                booking.getId(), totalAmount, request.getPaymentMethod());
            
            if (payment.isSuccess()) {
                // Step 6: Confirm booking
                booking.setStatus(BookingStatus.CONFIRMED);
                booking.setPaymentId(payment.getPaymentId());
                booking.setBookedAt(Instant.now());
                bookingRepository.save(booking);
                
                // Step 7: Release seat locks
                seatLockService.releaseSeats(request.getShowId(), 
                                            request.getSeatIds());
                
                // Step 8: Generate ticket
                Ticket ticket = ticketService.generateTicket(booking);
                
                // Step 9: Send confirmation
                notificationService.sendBookingConfirmation(booking, ticket);
                
                // Step 10: Publish event
                kafkaProducer.send("booking.confirmed", booking);
                
                return BookingResult.success(booking, ticket);
            } else {
                // Payment failed, compensate
                compensate(sagaId, "Payment failed");
                return BookingResult.failure("Payment failed");
            }
            
        } catch (Exception e) {
            compensate(sagaId, e.getMessage());
            throw new BookingException(e);
        }
    }
    
    private void compensate(String sagaId, String reason) {
        Booking booking = bookingRepository.findById(sagaId);
        if (booking != null) {
            // Release seat locks
            seatLockService.releaseSeats(booking.getShowId(), 
                                        booking.getSeatIds());
            
            // Mark booking as failed
            booking.setStatus(BookingStatus.FAILED);
            booking.setFailureReason(reason);
            bookingRepository.save(booking);
            
            // Refund if payment was captured
            if (booking.getPaymentId() != null) {
                paymentService.refund(booking.getPaymentId());
            }
        }
    }
}
```

### 5. Payment Service
**Responsibilities**:
- Payment processing (credit/debit cards, wallets, UPI)
- Gift card and coupon validation
- Refund processing
- Payment gateway integration
- PCI-DSS compliance

**Technology**: Spring Boot, Stripe/Razorpay
**Database**: PostgreSQL (payment records)
**Pattern**: Idempotency for payment operations

### 6. User Service
**Responsibilities**:
- User registration and authentication
- Profile management
- Booking history
- Favorite theaters and movies
- Notifications preferences

**Technology**: Spring Boot, JWT, OAuth2
**Database**: PostgreSQL

### 7. Notification Service
**Responsibilities**:
- Booking confirmations (email, SMS, push)
- Show reminders (1 hour before)
- Cancellation notifications
- Promotional offers
- New movie releases

**Technology**: Spring Boot, Kafka, Twilio, Firebase
**Queue**: Kafka topics for async notifications

## Database Design

### Movies Table
```sql
CREATE TABLE movies (
    movie_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    duration_minutes INT NOT NULL,
    release_date DATE NOT NULL,
    language VARCHAR(50) NOT NULL,
    genres VARCHAR(200), -- Comma-separated
    rating DECIMAL(2, 1), -- 0.0 to 10.0
    poster_url VARCHAR(500),
    trailer_url VARCHAR(500),
    cast JSONB, -- Array of actors
    crew JSONB, -- Director, producer, etc.
    status VARCHAR(20) NOT NULL DEFAULT 'UPCOMING',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_rating CHECK (rating >= 0 AND rating <= 10),
    CONSTRAINT chk_status CHECK (status IN ('UPCOMING', 'NOW_SHOWING', 'ENDED'))
);

CREATE INDEX idx_movies_title ON movies USING gin(to_tsvector('english', title));
CREATE INDEX idx_movies_release_date ON movies(release_date DESC);
CREATE INDEX idx_movies_status ON movies(status);
CREATE INDEX idx_movies_language ON movies(language);
```

### Theaters Table
```sql
CREATE TABLE theaters (
    theater_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    country VARCHAR(50) NOT NULL,
    zip_code VARCHAR(20),
    location GEOGRAPHY(POINT), -- PostGIS for geo queries
    phone VARCHAR(20),
    amenities JSONB, -- Parking, food court, etc.
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_theater_status CHECK (status IN ('ACTIVE', 'INACTIVE', 'MAINTENANCE'))
);

CREATE INDEX idx_theaters_city ON theaters(city);
CREATE INDEX idx_theaters_location ON theaters USING GIST(location);
CREATE INDEX idx_theaters_status ON theaters(status);
```

### Screens Table
```sql
CREATE TABLE screens (
    screen_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    theater_id UUID NOT NULL REFERENCES theaters(theater_id),
    screen_number INT NOT NULL,
    screen_type VARCHAR(50) NOT NULL, -- IMAX, 4DX, STANDARD, etc.
    total_seats INT NOT NULL,
    layout JSONB NOT NULL, -- Seat arrangement matrix
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_screen_type CHECK (screen_type IN 
        ('STANDARD', 'IMAX', '4DX', 'DOLBY', 'VIP')),
    CONSTRAINT uk_theater_screen UNIQUE(theater_id, screen_number)
);

CREATE INDEX idx_screens_theater ON screens(theater_id);
```

### Seats Table
```sql
CREATE TABLE seats (
    seat_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    screen_id UUID NOT NULL REFERENCES screens(screen_id),
    seat_number VARCHAR(10) NOT NULL, -- A1, A2, B1, etc.
    row_name VARCHAR(5) NOT NULL,
    column_number INT NOT NULL,
    seat_type VARCHAR(20) NOT NULL DEFAULT 'REGULAR',
    is_blocked BOOLEAN DEFAULT FALSE, -- Maintenance, broken
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_seat_type CHECK (seat_type IN 
        ('REGULAR', 'PREMIUM', 'RECLINER', 'WHEELCHAIR')),
    CONSTRAINT uk_screen_seat UNIQUE(screen_id, seat_number)
);

CREATE INDEX idx_seats_screen ON seats(screen_id);
CREATE INDEX idx_seats_type ON seats(seat_type);
```

### Shows Table
```sql
CREATE TABLE shows (
    show_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    movie_id UUID NOT NULL REFERENCES movies(movie_id),
    screen_id UUID NOT NULL REFERENCES screens(screen_id),
    show_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    base_price DECIMAL(10, 2) NOT NULL,
    pricing_tier VARCHAR(20) NOT NULL DEFAULT 'REGULAR',
    available_seats INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_pricing_tier CHECK (pricing_tier IN 
        ('MATINEE', 'REGULAR', 'PRIME', 'WEEKEND')),
    CONSTRAINT chk_show_status CHECK (status IN 
        ('SCHEDULED', 'LIVE', 'COMPLETED', 'CANCELLED', 'HOUSEFUL'))
);

CREATE INDEX idx_shows_movie ON shows(movie_id, show_date);
CREATE INDEX idx_shows_screen_date ON shows(screen_id, show_date, start_time);
CREATE INDEX idx_shows_date_time ON shows(show_date, start_time);
CREATE INDEX idx_shows_status ON shows(status);
```

### Bookings Table
```sql
CREATE TABLE bookings (
    booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    show_id UUID NOT NULL REFERENCES shows(show_id),
    seat_ids UUID[] NOT NULL, -- Array of seat IDs
    total_amount DECIMAL(10, 2) NOT NULL,
    booking_fee DECIMAL(10, 2) DEFAULT 0,
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    payment_id UUID,
    coupon_code VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    booked_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    cancellation_reason TEXT,
    refund_amount DECIMAL(10, 2),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_booking_status CHECK (status IN 
        ('PENDING', 'CONFIRMED', 'CANCELLED', 'REFUNDED', 'FAILED'))
);

CREATE INDEX idx_bookings_user ON bookings(user_id, created_at DESC);
CREATE INDEX idx_bookings_show ON bookings(show_id);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_bookings_payment ON bookings(payment_id);
```

### Seat Bookings Table (Junction)
```sql
CREATE TABLE seat_bookings (
    id BIGSERIAL PRIMARY KEY,
    booking_id UUID NOT NULL REFERENCES bookings(booking_id),
    show_id UUID NOT NULL REFERENCES shows(show_id),
    seat_id UUID NOT NULL REFERENCES seats(seat_id),
    price DECIMAL(10, 2) NOT NULL,
    seat_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_show_seat UNIQUE(show_id, seat_id)
);

CREATE INDEX idx_seat_bookings_booking ON seat_bookings(booking_id);
CREATE INDEX idx_seat_bookings_show_seat ON seat_bookings(show_id, seat_id);
```

### Reviews Table
```sql
CREATE TABLE reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    movie_id UUID NOT NULL REFERENCES movies(movie_id),
    user_id UUID NOT NULL REFERENCES users(user_id),
    rating INT NOT NULL,
    review_text TEXT,
    is_spoiler BOOLEAN DEFAULT FALSE,
    helpful_count INT DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_rating CHECK (rating >= 1 AND rating <= 10),
    CONSTRAINT uk_user_movie_review UNIQUE(user_id, movie_id)
);

CREATE INDEX idx_reviews_movie ON reviews(movie_id, created_at DESC);
CREATE INDEX idx_reviews_user ON reviews(user_id);
```

## API Design

### 1. Search Movies
```http
GET /api/v1/movies/search?city=New York&date=2026-04-10&query=avatar
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "movies": [
    {
      "movie_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Avatar: The Way of Water",
      "language": "English",
      "genres": ["Action", "Sci-Fi"],
      "duration_minutes": 192,
      "rating": 8.5,
      "poster_url": "https://cdn.example.com/avatar.jpg",
      "theaters_count": 45
    }
  ],
  "total_count": 1
}
```

### 2. Get Theaters for Movie
```http
GET /api/v1/movies/{movie_id}/theaters?city=New York&date=2026-04-10
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "theaters": [
    {
      "theater_id": "660e8400-e29b-41d4-a716-446655440000",
      "name": "AMC Lincoln Square 13",
      "address": "1998 Broadway, New York, NY 10023",
      "distance_km": 2.5,
      "amenities": ["Parking", "Food Court", "IMAX"],
      "shows": [
        {
          "show_id": "770e8400-e29b-41d4-a716-446655440000",
          "screen_type": "IMAX",
          "start_time": "10:00:00",
          "end_time": "13:12:00",
          "pricing_tier": "MATINEE",
          "base_price": 12.50,
          "available_seats": 87,
          "status": "SCHEDULED"
        },
        {
          "show_id": "880e8400-e29b-41d4-a716-446655440000",
          "screen_type": "STANDARD",
          "start_time": "14:00:00",
          "end_time": "17:12:00",
          "pricing_tier": "REGULAR",
          "base_price": 15.00,
          "available_seats": 120,
          "status": "SCHEDULED"
        }
      ]
    }
  ]
}
```

### 3. Get Seat Map
```http
GET /api/v1/shows/{show_id}/seats
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "show_id": "770e8400-e29b-41d4-a716-446655440000",
  "screen_type": "IMAX",
  "total_seats": 200,
  "available_seats": 87,
  "layout": {
    "rows": 15,
    "columns": 20,
    "seats": [
      {
        "seat_id": "aa0e8400-e29b-41d4-a716-446655440000",
        "seat_number": "A1",
        "row": "A",
        "column": 1,
        "type": "REGULAR",
        "price": 12.50,
        "status": "AVAILABLE"
      },
      {
        "seat_id": "bb0e8400-e29b-41d4-a716-446655440000",
        "seat_number": "A2",
        "row": "A",
        "column": 2,
        "type": "REGULAR",
        "price": 12.50,
        "status": "BOOKED"
      },
      {
        "seat_id": "cc0e8400-e29b-41d4-a716-446655440000",
        "seat_number": "G10",
        "row": "G",
        "column": 10,
        "type": "PREMIUM",
        "price": 18.00,
        "status": "LOCKED"
      }
    ]
  },
  "legend": {
    "AVAILABLE": "Available for booking",
    "BOOKED": "Already booked",
    "LOCKED": "Temporarily locked by another user",
    "BLOCKED": "Not available (maintenance)"
  }
}
```

### 4. Lock Seats
```http
POST /api/v1/shows/{show_id}/lock-seats
Authorization: Bearer <jwt_token>
Content-Type: application/json

Request:
{
  "seat_ids": [
    "aa0e8400-e29b-41d4-a716-446655440000",
    "ab0e8400-e29b-41d4-a716-446655440000"
  ]
}

Response: 200 OK
{
  "locked": true,
  "lock_expires_at": "2026-04-07T10:45:00Z",
  "locked_seats": [
    {
      "seat_id": "aa0e8400-e29b-41d4-a716-446655440000",
      "seat_number": "A1",
      "price": 12.50
    },
    {
      "seat_id": "ab0e8400-e29b-41d4-a716-446655440000",
      "seat_number": "A2",
      "price": 12.50
    }
  ],
  "total_amount": 25.00
}

Response: 409 Conflict (if seats already locked/booked)
{
  "error": "SEATS_UNAVAILABLE",
  "message": "One or more seats are already booked or locked",
  "unavailable_seats": ["aa0e8400-e29b-41d4-a716-446655440000"]
}
```

### 5. Create Booking
```http
POST /api/v1/bookings
Authorization: Bearer <jwt_token>
Content-Type: application/json

Request:
{
  "show_id": "770e8400-e29b-41d4-a716-446655440000",
  "seat_ids": [
    "aa0e8400-e29b-41d4-a716-446655440000",
    "ab0e8400-e29b-41d4-a716-446655440000"
  ],
  "concessions": [
    {
      "item_id": "popcorn_large",
      "quantity": 1
    }
  ],
  "coupon_code": "FIRSTSHOW",
  "payment_method": {
    "type": "CARD",
    "card_token": "tok_visa_1234"
  }
}

Response: 201 Created
{
  "booking_id": "dd0e8400-e29b-41d4-a716-446655440000",
  "status": "CONFIRMED",
  "show_details": {
    "movie_title": "Avatar: The Way of Water",
    "theater_name": "AMC Lincoln Square 13",
    "screen_type": "IMAX",
    "show_date": "2026-04-10",
    "start_time": "10:00:00"
  },
  "seats": [
    {"seat_number": "A1", "price": 12.50},
    {"seat_number": "A2", "price": 12.50}
  ],
  "concessions_total": 8.50,
  "subtotal": 33.50,
  "booking_fee": 2.50,
  "discount": 5.00,
  "total_amount": 31.00,
  "ticket_url": "https://cdn.example.com/tickets/dd0e8400.pdf",
  "qr_code": "data:image/png;base64,iVBORw0KG...",
  "booked_at": "2026-04-07T10:40:00Z"
}
```

### 6. Get Booking Details
```http
GET /api/v1/bookings/{booking_id}
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "booking_id": "dd0e8400-e29b-41d4-a716-446655440000",
  "status": "CONFIRMED",
  "movie": {
    "title": "Avatar: The Way of Water",
    "poster_url": "https://cdn.example.com/avatar.jpg"
  },
  "theater": {
    "name": "AMC Lincoln Square 13",
    "address": "1998 Broadway, New York, NY 10023"
  },
  "show": {
    "show_date": "2026-04-10",
    "start_time": "10:00:00",
    "screen_type": "IMAX"
  },
  "seats": ["A1", "A2"],
  "total_amount": 31.00,
  "ticket_url": "https://cdn.example.com/tickets/dd0e8400.pdf",
  "qr_code": "QR_CODE_BASE64",
  "can_cancel": true,
  "cancellation_deadline": "2026-04-10T08:00:00Z",
  "booked_at": "2026-04-07T10:40:00Z"
}
```

### 7. Cancel Booking
```http
POST /api/v1/bookings/{booking_id}/cancel
Authorization: Bearer <jwt_token>
Content-Type: application/json

Request:
{
  "reason": "Change of plans"
}

Response: 200 OK
{
  "booking_id": "dd0e8400-e29b-41d4-a716-446655440000",
  "status": "CANCELLED",
  "refund_amount": 28.00,
  "cancellation_fee": 3.00,
  "refund_status": "PROCESSING",
  "estimated_refund_date": "2026-04-12",
  "cancelled_at": "2026-04-08T15:30:00Z"
}
```

### 8. Get User Bookings
```http
GET /api/v1/users/me/bookings?status=CONFIRMED&limit=10&offset=0
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "bookings": [
    {
      "booking_id": "dd0e8400-e29b-41d4-a716-446655440000",
      "movie_title": "Avatar: The Way of Water",
      "theater_name": "AMC Lincoln Square 13",
      "show_date": "2026-04-10",
      "start_time": "10:00:00",
      "seats": ["A1", "A2"],
      "total_amount": 31.00,
      "status": "CONFIRMED",
      "booked_at": "2026-04-07T10:40:00Z"
    }
  ],
  "total_count": 15,
  "has_more": true
}
```

### 9. Add Review
```http
POST /api/v1/movies/{movie_id}/reviews
Authorization: Bearer <jwt_token>
Content-Type: application/json

Request:
{
  "rating": 9,
  "review_text": "Absolutely stunning visuals and compelling story!",
  "is_spoiler": false
}

Response: 201 Created
{
  "review_id": "ee0e8400-e29b-41d4-a716-446655440000",
  "movie_id": "550e8400-e29b-41d4-a716-446655440000",
  "rating": 9,
  "review_text": "Absolutely stunning visuals and compelling story!",
  "helpful_count": 0,
  "created_at": "2026-04-11T18:00:00Z"
}
```

### 10. Get Movie Reviews
```http
GET /api/v1/movies/{movie_id}/reviews?sort=helpful&limit=20
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "movie_id": "550e8400-e29b-41d4-a716-446655440000",
  "average_rating": 8.5,
  "total_reviews": 1523,
  "reviews": [
    {
      "review_id": "ee0e8400-e29b-41d4-a716-446655440000",
      "user_name": "John D.",
      "rating": 9,
      "review_text": "Absolutely stunning visuals...",
      "helpful_count": 145,
      "created_at": "2026-04-11T18:00:00Z"
    }
  ]
}
```

## Caching Strategy

### Redis Cache Layers

**1. Movie Cache (Hot Movies)**
```
Key Pattern: movie:details:{movie_id}
TTL: 1 hour
Value: Movie JSON
Example: movie:details:550e8400 -> {title, poster, rating, ...}
```

**2. Showtime Cache**
```
Key Pattern: shows:theater:{theater_id}:date:{date}
TTL: 5 minutes
Value: List of shows
Example: shows:theater:660e8400:date:2026-04-10 -> [show1, show2, ...]
```

**3. Seat Map Cache**
```
Key Pattern: seats:show:{show_id}
TTL: 10 seconds (high churn during booking)
Value: Seat availability map
Example: seats:show:770e8400 -> {seats: [...], available_count: 87}
```

**4. Seat Lock Cache**
```
Key Pattern: seat:lock:{show_id}:{seat_id}
TTL: 600 seconds (10 minutes)
Value: User ID who locked the seat
Example: seat:lock:770e8400:aa0e8400 -> "user_123"
```

**5. User Lock Tracking**
```
Key Pattern: user:locks:{user_id}
TTL: 600 seconds
Value: Show ID and locked seat IDs
Example: user:locks:user_123 -> "770e8400:aa0e8400,ab0e8400"
```

**6. Theater Location Cache**
```
Key Pattern: theaters:city:{city_name}
TTL: 24 hours
Value: List of theaters
Example: theaters:city:newyork -> [{theater1}, {theater2}, ...]
```

**7. User Session Cache**
```
Key Pattern: session:{user_id}
TTL: 24 hours
Value: JWT token, user profile
```

**Cache Invalidation**:
- Seat map: Invalidate on booking/cancellation
- Shows: Invalidate when show is updated/cancelled
- Movies: Invalidate on movie data update
- Seat locks: TTL-based auto-expiry

## Scalability

### Horizontal Scaling

**1. Service Layer**
- Stateless microservices
- Kubernetes HPA with target CPU 70%
- Scale booking service independently during peak
- Min 3 replicas, max 50 replicas per service

**2. Database Sharding**

**Sharding Strategy for Bookings**:
```sql
-- Shard by show_id (consistent hashing)
Shard Key: HASH(show_id) % 8
Shard 0: show_id hash 0-999
Shard 1: show_id hash 1000-1999
...
Shard 7: show_id hash 7000-7999

-- Benefits:
-- - All bookings for a show in same shard (data locality)
-- - Parallel processing of different shows
-- - Easy to query seat availability
```

**Partitioning for Shows**:
```sql
-- Partition by show_date (range partitioning)
Partition shows_2026_q2 VALUES FROM ('2026-04-01') TO ('2026-07-01');
Partition shows_2026_q3 VALUES FROM ('2026-07-01') TO ('2026-10-01');
...

-- Old partitions archived after show ends
```

**3. Read Replicas**
- Primary: Write operations (bookings)
- Replicas: Read operations (search, browse)
- 1 primary + 3 read replicas per shard
- Lag < 50ms

**4. Cache Scaling**
- Redis Cluster with 6 nodes (3 master + 3 replicas)
- Client-side sharding for seat locks
- Separate cache pools for different data types

### Load Balancing

**Geographic Load Balancing**:
- Route US East traffic to us-east-1
- Route US West traffic to us-west-2
- Route EU traffic to eu-west-1
- Use Route53 geolocation routing

**Service Mesh (Istio)**:
- Circuit breaker for payment service
- Retry with exponential backoff
- Request timeout: 5 seconds
- Connection pooling

### Handling Thundering Herd

**Problem**: 100K users trying to book same blockbuster show

**Solution 1: Queue System**
```java
@Service
public class BookingQueueService {
    
    public QueuePosition joinQueue(String showId, String userId) {
        // Add user to Redis sorted set (queue)
        String queueKey = "queue:show:" + showId;
        double score = System.currentTimeMillis();
        redis.zadd(queueKey, score, userId);
        
        // Get user's position
        Long position = redis.zrank(queueKey, userId);
        Long queueSize = redis.zcard(queueKey);
        
        return new QueuePosition(position + 1, queueSize, 
                                estimateWaitTime(position));
    }
    
    @Scheduled(fixedRate = 1000) // Process 10 users per second
    public void processQueue() {
        for (String showId : getActiveShows()) {
            String queueKey = "queue:show:" + showId;
            
            // Get next 10 users from queue
            Set<String> users = redis.zrange(queueKey, 0, 9);
            
            for (String userId : users) {
                // Send notification to user that it's their turn
                notificationService.notifyUserTurn(userId, showId);
                
                // Remove from queue
                redis.zrem(queueKey, userId);
                
                // Set TTL for booking (5 minutes)
                redis.setex("booking:turn:" + userId + ":" + showId, 
                           300, "active");
            }
        }
    }
}
```

**Solution 2: Rate Limiting**
```java
// Rate limit booking attempts per user
@RateLimiter(name = "bookingLimiter", fallbackMethod = "bookingFallback")
public BookingResult createBooking(BookingRequest request) {
    // Process booking
}

// Resilience4j configuration
resilience4j.ratelimiter:
  instances:
    bookingLimiter:
      limitForPeriod: 5
      limitRefreshPeriod: 1m
      timeoutDuration: 0s
```

**Solution 3: Captcha for Suspected Bots**
```java
if (isHighDemandShow(showId) && isSuspiciousBehavior(userId)) {
    requireCaptcha();
}
```

## Fault Tolerance & High Availability

### 1. Circuit Breaker
```java
@CircuitBreaker(name = "paymentService", fallbackMethod = "paymentFallback")
public PaymentResult processPayment(PaymentRequest request) {
    return paymentGateway.charge(request);
}

public PaymentResult paymentFallback(PaymentRequest request, Exception e) {
    // Queue for retry
    paymentRetryQueue.enqueue(request);
    return PaymentResult.pending();
}
```

**Configuration**:
- Failure threshold: 50%
- Wait duration: 60 seconds
- Sliding window: 100 requests

### 2. Distributed Lock Failure Handling
```java
public boolean lockSeats(String showId, List<String> seatIds, String userId) {
    try {
        return redisLock.tryLock(seatIds, 10, TimeUnit.SECONDS);
    } catch (RedisConnectionException e) {
        // Fallback to database-level locking
        return databaseLockService.lockSeats(showId, seatIds, userId);
    }
}
```

### 3. Database Failover
- Automatic failover to replica if primary fails
- Promote replica to primary within 30 seconds
- Use connection pooler (PgBouncer) for seamless failover
- Health checks every 5 seconds

### 4. Idempotency
- All booking operations use idempotency keys
- Retry safe for network failures
- Duplicate prevention

### 5. Graceful Degradation
- If seat map service is slow, show cached data with warning
- If payment service is down, queue bookings for later processing
- If notification service fails, retry asynchronously

### 6. Data Backup
- Automated database snapshots every 6 hours
- Transaction log archival (WAL)
- Point-in-time recovery (PITR)
- Cross-region replication
- RTO: 30 minutes, RPO: 5 minutes

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Client** | React, React Native, Flutter | Web and mobile apps |
| **CDN** | CloudFront, Akamai | Static assets, images, videos |
| **API Gateway** | Kong, AWS API Gateway | Rate limiting, auth, routing |
| **Load Balancer** | AWS ALB, NGINX | Traffic distribution |
| **Service Layer** | Spring Boot (Java 17), Node.js | Business logic microservices |
| **Message Queue** | Apache Kafka, RabbitMQ | Event streaming, async tasks |
| **Cache** | Redis Cluster | Seat locks, sessions, hot data |
| **Primary DB** | PostgreSQL 15 with PostGIS | Transactional data, geo queries |
| **Search** | Elasticsearch | Movie search, text search |
| **Object Storage** | AWS S3 | Posters, trailers, tickets (PDF) |
| **Payment** | Stripe, Razorpay, PayPal | Payment processing |
| **Monitoring** | Prometheus, Grafana, Datadog | Metrics, dashboards |
| **Logging** | ELK Stack | Centralized logging |
| **Tracing** | Jaeger, Zipkin | Distributed tracing |
| **Container** | Docker, Kubernetes (EKS) | Container orchestration |
| **CI/CD** | Jenkins, GitLab CI, ArgoCD | Automated deployments |
| **IaC** | Terraform | Infrastructure as code |
| **Notifications** | Twilio (SMS), SendGrid (Email), FCM (Push) | Multi-channel messaging |
| **QR Code** | ZXing, qrcode.js | Ticket generation |

## Interview Discussion Points

### Q1: How do you prevent double-booking of seats when thousands of users are booking simultaneously?

**Answer**: We use a multi-layered approach:

**1. Distributed Locking (Primary Mechanism)**:
```java
public boolean lockSeats(String showId, List<String> seatIds, String userId) {
    // Use Redis distributed lock (Redlock algorithm)
    String lockKey = "lock:show:" + showId;
    
    try (RedisLock lock = redisLock.acquire(lockKey, 5, TimeUnit.SECONDS)) {
        // Check each seat availability
        for (String seatId : seatIds) {
            String seatLockKey = "seat:lock:" + showId + ":" + seatId;
            
            // Atomic check and set
            boolean locked = redis.setnx(seatLockKey, userId);
            if (!locked) {
                // Seat already locked, rollback and fail
                rollbackLocks(showId, seatIds, userId);
                return false;
            }
            
            // Set TTL (10 minutes)
            redis.expire(seatLockKey, 600);
        }
        
        return true;
    }
}
```

**2. Database Constraint (Safety Net)**:
```sql
-- Unique constraint ensures no duplicate bookings even if cache fails
CREATE UNIQUE INDEX idx_seat_bookings_show_seat 
ON seat_bookings(show_id, seat_id);
```

**3. Optimistic Locking (Version Control)**:
```java
// Seats table has version column
UPDATE seats 
SET status = 'BOOKED', version = version + 1
WHERE seat_id = ? AND show_id = ? AND version = ? AND status = 'AVAILABLE';

// If rows affected = 0, seat was already booked (concurrent modification)
```

**4. Transaction Isolation**:
```java
@Transactional(isolation = Isolation.SERIALIZABLE)
public void confirmBooking(Booking booking) {
    // SERIALIZABLE ensures no concurrent modifications
    // Trade-off: Lower throughput but guaranteed consistency
}
```

**Trade-offs**:
- Redis lock: Fast but can fail in network partition
- DB constraint: Slower but guaranteed consistency
- Use both for defense in depth

---

### Q2: How do you design the seat locking mechanism to handle user abandonment?

**Answer**: Implement automatic lock expiration with cleanup:

**Architecture**:
1. **TTL-based Expiration** (Primary):
```java
// Lock seats with TTL
redis.setex("seat:lock:" + showId + ":" + seatId, 600, userId);

// Redis automatically removes expired locks
// No manual cleanup needed
```

2. **Background Cleanup Job** (Safety):
```java
@Scheduled(fixedRate = 60000) // Every minute
public void cleanupExpiredLocks() {
    // Find bookings in PENDING state older than 10 minutes
    List<Booking> expiredBookings = bookingRepository
        .findByStatusAndCreatedAtBefore(
            BookingStatus.PENDING, 
            Instant.now().minus(10, ChronoUnit.MINUTES)
        );
    
    for (Booking booking : expiredBookings) {
        // Release seat locks
        seatLockService.releaseSeats(booking.getShowId(), 
                                    booking.getSeatIds());
        
        // Update booking status
        booking.setStatus(BookingStatus.EXPIRED);
        bookingRepository.save(booking);
        
        // Notify user
        notificationService.notifyBookingExpired(booking);
    }
}
```

3. **Heartbeat Mechanism**:
```java
// Client sends heartbeat every 30 seconds during checkout
@PostMapping("/bookings/heartbeat")
public void extendLock(@RequestParam String bookingId) {
    Booking booking = bookingRepository.findById(bookingId);
    
    // Extend lock TTL by another 10 minutes
    for (String seatId : booking.getSeatIds()) {
        redis.expire("seat:lock:" + booking.getShowId() + ":" + seatId, 600);
    }
}
```

4. **Graceful Warning**:
```java
// Warn user 2 minutes before expiration
if (lockTimeRemaining < 120) {
    notificationService.warnLockExpiring(userId, lockTimeRemaining);
}
```

**Implementation Details**:
- Lock duration: 10 minutes (enough for payment)
- Warning at: 2 minutes remaining
- Heartbeat interval: 30 seconds (if user is active)
- Cleanup job: Every 1 minute
- Grace period: 30 seconds after expiry before hard cleanup

---

### Q3: How do you handle flash sales for blockbuster movies (high concurrency)?

**Answer**: Use a combination of queue, rate limiting, and caching:

**1. Virtual Waiting Room**:
```java
@Service
public class WaitingRoomService {
    
    public WaitingRoomToken joinWaitingRoom(String showId, String userId) {
        String queueKey = "waitingroom:" + showId;
        
        // Add to sorted set with timestamp
        double score = System.currentTimeMillis();
        redis.zadd(queueKey, score, userId);
        
        // Get position
        Long position = redis.zrank(queueKey, userId);
        Long totalWaiting = redis.zcard(queueKey);
        
        // Generate token
        String token = JWT.create()
            .withClaim("userId", userId)
            .withClaim("showId", showId)
            .withClaim("position", position)
            .withExpiresAt(Date.from(Instant.now().plus(1, ChronoUnit.HOURS)))
            .sign(Algorithm.HMAC256(secret));
        
        return new WaitingRoomToken(token, position, totalWaiting);
    }
    
    @Scheduled(fixedRate = 100) // Every 100ms
    public void admitUsersFromWaitingRoom() {
        for (String showId : getHighDemandShows()) {
            String queueKey = "waitingroom:" + showId;
            
            // Admit 10 users per second (configurable)
            Set<String> users = redis.zrange(queueKey, 0, 0); // Get first user
            
            for (String userId : users) {
                // Generate admission token
                String admissionToken = generateAdmissionToken(userId, showId);
                
                // Notify user (push notification)
                notificationService.notifyAdmission(userId, showId, admissionToken);
                
                // Remove from waiting room
                redis.zrem(queueKey, userId);
                
                // Set admission token TTL (5 minutes to complete booking)
                redis.setex("admission:" + userId + ":" + showId, 300, admissionToken);
            }
        }
    }
}
```

**2. Rate Limiting**:
```java
// Global rate limit per show
@RateLimiter(name = "showBooking")
public BookingResult bookShow(String showId, BookingRequest request) {
    // Max 100 concurrent bookings per show
    return bookingService.createBooking(request);
}

// Configuration
resilience4j.ratelimiter.instances.showBooking:
  limitForPeriod: 100
  limitRefreshPeriod: 1s
```

**3. Caching Seat Availability**:
```java
// Use Redis counter for quick availability check
String availableCountKey = "show:available:" + showId;
Long availableSeats = redis.get(availableCountKey);

if (availableSeats == null) {
    // Cache miss, fetch from DB
    availableSeats = countAvailableSeats(showId);
    redis.setex(availableCountKey, 10, availableSeats);
}

if (availableSeats < requestedSeats) {
    throw new NotEnoughSeatsException();
}
```

**4. Progressive Disclosure**:
```java
// Don't show all seats at once for high-demand shows
// Show seats in batches to reduce load
public SeatMap getAvailableSeats(String showId, String section) {
    // Only load seats for requested section (front, middle, back)
    return seatService.getSeatsBySection(showId, section);
}
```

**5. CAPTCHA for Bots**:
```java
if (isHighDemandShow(showId) && !isVerifiedUser(userId)) {
    verifyCaptcha(request.getCaptchaToken());
}
```

---

### Q4: How do you calculate pricing dynamically (surge pricing for high-demand shows)?

**Answer**: Implement dynamic pricing based on demand, time, and seat type:

**Pricing Formula**:
```
Final Price = Base Price × Tier Multiplier × Seat Type Multiplier × Demand Multiplier
```

**Implementation**:
```java
@Service
public class DynamicPricingService {
    
    public BigDecimal calculatePrice(String showId, String seatId) {
        Show show = showRepository.findById(showId);
        Seat seat = seatRepository.findById(seatId);
        
        // Base price from show
        BigDecimal basePrice = show.getBasePrice();
        
        // 1. Time-based tier (matinee, regular, prime)
        BigDecimal tierMultiplier = getTierMultiplier(show.getStartTime());
        
        // 2. Seat type multiplier
        BigDecimal seatMultiplier = getSeatTypeMultiplier(seat.getSeatType());
        
        // 3. Demand multiplier (surge pricing)
        BigDecimal demandMultiplier = calculateDemandMultiplier(showId);
        
        // 4. Day of week
        BigDecimal dayMultiplier = getDayMultiplier(show.getShowDate());
        
        // Calculate final price
        BigDecimal finalPrice = basePrice
            .multiply(tierMultiplier)
            .multiply(seatMultiplier)
            .multiply(demandMultiplier)
            .multiply(dayMultiplier);
        
        // Round to 2 decimal places
        return finalPrice.setScale(2, RoundingMode.HALF_UP);
    }
    
    private BigDecimal getTierMultiplier(LocalTime startTime) {
        int hour = startTime.getHour();
        
        if (hour < 12) {
            return new BigDecimal("0.75"); // Matinee: 25% discount
        } else if (hour >= 18) {
            return new BigDecimal("1.25"); // Prime time: 25% premium
        } else {
            return BigDecimal.ONE; // Regular
        }
    }
    
    private BigDecimal getSeatTypeMultiplier(String seatType) {
        return switch (seatType) {
            case "REGULAR" -> BigDecimal.ONE;
            case "PREMIUM" -> new BigDecimal("1.5");  // 50% more
            case "RECLINER" -> new BigDecimal("2.0"); // 100% more
            case "WHEELCHAIR" -> BigDecimal.ONE;
            default -> BigDecimal.ONE;
        };
    }
    
    private BigDecimal calculateDemandMultiplier(String showId) {
        // Calculate occupancy rate
        Show show = showRepository.findById(showId);
        int totalSeats = show.getScreen().getTotalSeats();
        int bookedSeats = bookingRepository.countBookedSeats(showId);
        double occupancyRate = (double) bookedSeats / totalSeats;
        
        // Surge pricing based on occupancy
        if (occupancyRate > 0.8) {
            return new BigDecimal("1.5"); // 50% surge for high demand
        } else if (occupancyRate > 0.6) {
            return new BigDecimal("1.25"); // 25% surge
        } else if (occupancyRate < 0.2) {
            return new BigDecimal("0.9"); // 10% discount for low demand
        } else {
            return BigDecimal.ONE;
        }
    }
    
    private BigDecimal getDayMultiplier(LocalDate showDate) {
        DayOfWeek dayOfWeek = showDate.getDayOfWeek();
        
        if (dayOfWeek == DayOfWeek.SATURDAY || dayOfWeek == DayOfWeek.SUNDAY) {
            return new BigDecimal("1.2"); // Weekend: 20% premium
        } else {
            return BigDecimal.ONE;
        }
    }
}
```

**Caching Prices**:
```java
// Cache price for 5 minutes
@Cacheable(value = "seat-prices", key = "#showId + ':' + #seatId")
public BigDecimal getPrice(String showId, String seatId) {
    return calculatePrice(showId, seatId);
}
```

**Price Locking**:
```java
// Lock price when user selects seat
public void lockPrice(String bookingId, String showId, List<String> seatIds) {
    for (String seatId : seatIds) {
        BigDecimal price = calculatePrice(showId, seatId);
        
        // Store locked price
        redis.setex("price:lock:" + bookingId + ":" + seatId, 
                   600, // 10 minutes
                   price.toString());
    }
}
```

---

### Q5: How do you handle refunds and cancellations at scale?

**Answer**: Implement async refund processing with proper state management:

**Cancellation Policy**:
```java
public class CancellationPolicy {
    
    public CancellationResult canCancel(Booking booking) {
        LocalDateTime showTime = LocalDateTime.of(
            booking.getShow().getShowDate(),
            booking.getShow().getStartTime()
        );
        
        LocalDateTime now = LocalDateTime.now();
        long hoursUntilShow = ChronoUnit.HOURS.between(now, showTime);
        
        if (hoursUntilShow < 2) {
            return CancellationResult.notAllowed("Too close to show time");
        }
        
        // Calculate refund amount based on timing
        BigDecimal refundAmount = calculateRefund(booking, hoursUntilShow);
        BigDecimal cancellationFee = booking.getTotalAmount()
            .subtract(refundAmount);
        
        return CancellationResult.allowed(refundAmount, cancellationFee);
    }
    
    private BigDecimal calculateRefund(Booking booking, long hoursUntilShow) {
        BigDecimal totalAmount = booking.getTotalAmount();
        
        if (hoursUntilShow >= 24) {
            // Full refund (minus convenience fee)
            return totalAmount.multiply(new BigDecimal("0.95"));
        } else if (hoursUntilShow >= 12) {
            // 75% refund
            return totalAmount.multiply(new BigDecimal("0.75"));
        } else if (hoursUntilShow >= 6) {
            // 50% refund
            return totalAmount.multiply(new BigDecimal("0.50"));
        } else {
            // 25% refund
            return totalAmount.multiply(new BigDecimal("0.25"));
        }
    }
}
```

**Async Refund Processing**:
```java
@Service
public class RefundService {
    
    @Transactional
    public void cancelBooking(String bookingId, String reason) {
        Booking booking = bookingRepository.findById(bookingId);
        
        // Validate cancellation allowed
        CancellationResult result = cancellationPolicy.canCancel(booking);
        if (!result.isAllowed()) {
            throw new CancellationNotAllowedException(result.getReason());
        }
        
        // Update booking status
        booking.setStatus(BookingStatus.CANCELLED);
        booking.setCancelledAt(Instant.now());
        booking.setCancellationReason(reason);
        booking.setRefundAmount(result.getRefundAmount());
        bookingRepository.save(booking);
        
        // Release seats (make available again)
        for (String seatId : booking.getSeatIds()) {
            seatBookingRepository.deleteByShowIdAndSeatId(
                booking.getShowId(), seatId);
        }
        
        // Update available seat count
        showRepository.incrementAvailableSeats(
            booking.getShowId(), 
            booking.getSeatIds().size()
        );
        
        // Publish refund event (async processing)
        RefundEvent event = new RefundEvent(
            booking.getId(),
            booking.getPaymentId(),
            result.getRefundAmount()
        );
        kafkaProducer.send("refund.requested", event);
        
        // Invalidate cache
        redis.del("show:seats:" + booking.getShowId());
    }
}

@KafkaListener(topics = "refund.requested")
public void processRefund(RefundEvent event) {
    try {
        // Process refund with payment gateway
        RefundResult result = paymentGateway.refund(
            event.getPaymentId(),
            event.getAmount()
        );
        
        // Update booking with refund status
        Booking booking = bookingRepository.findById(event.getBookingId());
        booking.setStatus(BookingStatus.REFUNDED);
        booking.setRefundedAt(Instant.now());
        bookingRepository.save(booking);
        
        // Notify user
        notificationService.notifyRefundProcessed(booking);
        
    } catch (Exception e) {
        // Retry with exponential backoff
        throw new RetryableException(e);
    }
}
```

## Cost Estimation

### Infrastructure Costs (Monthly)

| Component | Configuration | Unit Cost | Quantity | Monthly Cost |
|-----------|--------------|-----------|----------|--------------|
| **Compute (EKS)** | m5.xlarge (4 vCPU, 16GB) | $140 | 20 nodes | $2,800 |
| **Database (RDS)** | db.r5.xlarge (4 vCPU, 32GB) | $400 | 8 shards * 4 | $12,800 |
| **Cache (ElastiCache)** | cache.r5.large (2 vCPU, 13GB) | $150 | 6 nodes | $900 |
| **Kafka (MSK)** | kafka.m5.large | $150 | 3 brokers | $450 |
| **Elasticsearch** | r5.large.elasticsearch | $150 | 3 nodes | $450 |
| **Load Balancers** | ALB | $25 | 3 ALBs | $75 |
| **CloudFront (CDN)** | Data transfer + requests | - | - | $500 |
| **S3 Storage** | Standard | $0.023/GB | 10TB | $230 |
| **Data Transfer** | Outbound | $0.09/GB | 5TB | $450 |
| **CloudWatch** | Logs + metrics | - | - | $300 |
| **External APIs** | TMDB, Twilio, SendGrid | - | - | $2,000 |
| **Payment Gateway** | Stripe (2.9% + $0.30) | - | - | $15,000 |
| **Backup & DR** | Snapshots, replication | - | - | $1,000 |
| **Monitoring** | Datadog | - | - | $500 |
| **Total** | | | | **$37,455/month** |

**Annual Cost**: $449,460

**Cost per Booking**: $449,460 / (2M bookings/day * 365) = $0.0006 per booking

**Revenue Model**:
- Booking fee: $2.50 per booking
- Service fee per ticket: $1.50
- Concessions markup: 30%
- Monthly revenue: 2M bookings/day * $2.50 * 30 days = $150M/month
- Net profit: $150M - $0.037M = $149.96M/month

**Break-even**: 15,000 bookings/day

---

**Document Version**: 1.0  
**Last Updated**: 2026-04-07  
**Author**: System Design Interview Prep  
**Review Status**: Production-Ready
