# Question 26: Design Complete Database Schema with All Entities and Relationships

## Difficulty Level: ⭐⭐⭐ (Senior)

## Expected Answer Duration: 10-12 minutes

---

## What Interviewer Wants to See:

1. ✅ **Complete entities** (not missing critical ones)
2. ✅ **Proper relationships** (1:1, 1:N, N:M with join tables)
3. ✅ **Appropriate data types** and constraints
4. ✅ **Indexes** for performance
5. ✅ **Normalization** (3NF) vs strategic denormalization
6. ✅ **Audit fields** (created_at, updated_at)

---

## ❌ Common Mistakes (What NOT to Do):

```sql
-- ❌ BAD: Missing Show entity
CREATE TABLE movies (
    id BIGINT PRIMARY KEY,
    title VARCHAR(255),
    show_time TIME,  -- ← Should be in Show entity!
    theater_id BIGINT  -- ← Movie shouldn't know about theater
);

-- ❌ BAD: Wrong relationship (1:1 instead of 1:N)
CREATE TABLE users (
    id BIGINT PRIMARY KEY,
    booking_id BIGINT  -- ← User can only have ONE booking ever?!
);

-- ❌ BAD: No indexes on foreign keys
CREATE TABLE booking_seat (
    booking_id BIGINT,  -- No index!
    seat_id BIGINT      -- No index!
);
```

---

## ✅ Production-Ready Schema:

### **Part 1: Hierarchy Entities (Location → Theater → Screen → Seat)**

```sql
-- ═══════════════════════════════════════════════════════════
-- LOCATION HIERARCHY
-- ═══════════════════════════════════════════════════════════

CREATE TABLE city (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL DEFAULT 'India',
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uk_city_name_state UNIQUE (name, state),
    INDEX idx_city_active (is_active),
    INDEX idx_city_country (country)
);

CREATE TABLE theater (
    id BIGSERIAL PRIMARY KEY,
    city_id BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    pin_code VARCHAR(10),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    amenities JSON,  -- ["Parking", "Food Court", "Wheelchair Access"]
    contact_number VARCHAR(15),
    rating DECIMAL(2, 1) DEFAULT 0.0,
    total_screens INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_theater_city FOREIGN KEY (city_id) 
        REFERENCES city(id) ON DELETE RESTRICT,
    INDEX idx_theater_city (city_id),
    INDEX idx_theater_active (is_active),
    INDEX idx_theater_location (latitude, longitude),
    INDEX idx_theater_rating (rating DESC)
);

CREATE TABLE screen (
    id BIGSERIAL PRIMARY KEY,
    theater_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,  -- "Screen 1 - IMAX"
    screen_type VARCHAR(50) NOT NULL,  -- IMAX, 3D, 4DX, STANDARD
    total_rows INT NOT NULL,  -- 20
    seats_per_row INT NOT NULL,  -- 30
    total_seats INT NOT NULL,  -- 600
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_screen_theater FOREIGN KEY (theater_id) 
        REFERENCES theater(id) ON DELETE CASCADE,
    CONSTRAINT chk_screen_seats CHECK (total_seats = total_rows * seats_per_row),
    INDEX idx_screen_theater (theater_id),
    INDEX idx_screen_type (screen_type)
);

CREATE TABLE seat (
    id BIGSERIAL PRIMARY KEY,
    screen_id BIGINT NOT NULL,
    row_number CHAR(1) NOT NULL,  -- 'A', 'B', 'C'...'Z'
    seat_number INT NOT NULL,  -- 1, 2, 3...30
    seat_type VARCHAR(50) NOT NULL,  -- NORMAL, PREMIUM, RECLINER
    price_multiplier DECIMAL(3, 2) NOT NULL DEFAULT 1.0,  -- 1.0, 1.5, 2.0
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_seat_screen FOREIGN KEY (screen_id) 
        REFERENCES screen(id) ON DELETE CASCADE,
    CONSTRAINT uk_seat_screen_row_number UNIQUE (screen_id, row_number, seat_number),
    INDEX idx_seat_screen (screen_id),
    INDEX idx_seat_type (seat_type)
);
```

---

### **Part 2: Movie & Show Entities**

```sql
-- ═══════════════════════════════════════════════════════════
-- MOVIE CATALOG
-- ═══════════════════════════════════════════════════════════

CREATE TABLE movie (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    genre VARCHAR(100),  -- "Action, Sci-Fi, Thriller"
    language VARCHAR(50),  -- "English, Hindi"
    duration_minutes INT NOT NULL,
    release_date DATE NOT NULL,
    rating VARCHAR(10),  -- "U/A", "PG-13", "R"
    director VARCHAR(255),
    cast JSON,  -- ["Robert Downey Jr.", "Chris Evans"]
    poster_url TEXT,
    trailer_url TEXT,
    imdb_rating DECIMAL(2, 1),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_movie_release_date (release_date DESC),
    INDEX idx_movie_genre (genre),
    INDEX idx_movie_language (language),
    INDEX idx_movie_active (is_active),
    FULLTEXT INDEX ft_movie_title (title, description)
);

CREATE TABLE show (
    id BIGSERIAL PRIMARY KEY,
    movie_id BIGINT NOT NULL,
    screen_id BIGINT NOT NULL,
    show_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    price_per_seat DECIMAL(8, 2) NOT NULL,
    
    -- Denormalized for performance
    available_seats INT NOT NULL,  -- Updated on each booking
    total_seats INT NOT NULL,  -- Copied from screen at show creation
    
    is_running BOOLEAN NOT NULL DEFAULT false,
    is_cancelled BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_show_movie FOREIGN KEY (movie_id) 
        REFERENCES movie(id) ON DELETE RESTRICT,
    CONSTRAINT fk_show_screen FOREIGN KEY (screen_id) 
        REFERENCES screen(id) ON DELETE RESTRICT,
    CONSTRAINT chk_show_time CHECK (end_time > start_time),
    CONSTRAINT chk_show_seats CHECK (available_seats >= 0 AND available_seats <= total_seats),
    
    INDEX idx_show_movie (movie_id),
    INDEX idx_show_screen (screen_id),
    INDEX idx_show_date_time (show_date, start_time),
    INDEX idx_show_available_seats (available_seats),
    INDEX idx_show_running (is_running),
    
    -- Prevent overlapping shows on same screen
    CONSTRAINT uk_show_screen_datetime UNIQUE (screen_id, show_date, start_time)
);

-- For faster seat status lookups
CREATE TABLE seat_availability (
    show_id BIGINT NOT NULL,
    seat_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,  -- AVAILABLE, RESERVED, BOOKED
    reserved_until TIMESTAMP,  -- NULL if AVAILABLE or BOOKED
    booking_id VARCHAR(36),  -- NULL until booking created
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (show_id, seat_id),
    
    CONSTRAINT fk_seat_avail_show FOREIGN KEY (show_id) 
        REFERENCES show(id) ON DELETE CASCADE,
    CONSTRAINT fk_seat_avail_seat FOREIGN KEY (seat_id) 
        REFERENCES seat(id) ON DELETE CASCADE,
    CONSTRAINT fk_seat_avail_booking FOREIGN KEY (booking_id) 
        REFERENCES booking(id) ON DELETE SET NULL,
    CONSTRAINT chk_seat_status CHECK (status IN ('AVAILABLE', 'RESERVED', 'BOOKED')),
    
    INDEX idx_seat_avail_show (show_id),
    INDEX idx_seat_avail_status (status),
    INDEX idx_seat_avail_booking (booking_id),
    INDEX idx_seat_avail_reserved_until (reserved_until)
);
```

---

### **Part 3: User & Booking Entities**

```sql
-- ═══════════════════════════════════════════════════════════
-- USER MANAGEMENT
-- ═══════════════════════════════════════════════════════════

CREATE TABLE user (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(15) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    date_of_birth DATE,
    wallet_balance DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    preferences JSON,  -- {"genres": ["Action"], "languages": ["Hindi"]}
    is_verified BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,  -- Soft delete for GDPR
    
    INDEX idx_user_email (email),
    INDEX idx_user_phone (phone),
    INDEX idx_user_active (is_active),
    INDEX idx_user_deleted (deleted_at)
);

-- ═══════════════════════════════════════════════════════════
-- BOOKING FLOW
-- ═══════════════════════════════════════════════════════════

CREATE TABLE booking (
    id VARCHAR(36) PRIMARY KEY,  -- UUID for idempotency
    user_id BIGINT NOT NULL,
    show_id BIGINT NOT NULL,
    total_seats INT NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    booking_status VARCHAR(20) NOT NULL,  -- PENDING, CONFIRMED, CANCELLED, EXPIRED
    payment_id VARCHAR(36),  -- FK to payment (NULL until payment succeeds)
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,  -- created_at + 15 minutes
    confirmed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_booking_user FOREIGN KEY (user_id) 
        REFERENCES user(id) ON DELETE RESTRICT,
    CONSTRAINT fk_booking_show FOREIGN KEY (show_id) 
        REFERENCES show(id) ON DELETE RESTRICT,
    CONSTRAINT chk_booking_status CHECK (booking_status IN 
        ('PENDING', 'CONFIRMED', 'CANCELLED', 'EXPIRED')),
    
    INDEX idx_booking_user (user_id),
    INDEX idx_booking_show (show_id),
    INDEX idx_booking_status (booking_status),
    INDEX idx_booking_expires_at (expires_at),  -- For expiry job
    INDEX idx_booking_created_at (created_at DESC),
    INDEX idx_booking_user_created (user_id, created_at DESC)
);

CREATE TABLE booking_seat (
    id BIGSERIAL PRIMARY KEY,
    booking_id VARCHAR(36) NOT NULL,
    seat_id BIGINT NOT NULL,
    price DECIMAL(8, 2) NOT NULL,  -- Captured at booking time
    
    CONSTRAINT fk_booking_seat_booking FOREIGN KEY (booking_id) 
        REFERENCES booking(id) ON DELETE CASCADE,
    CONSTRAINT fk_booking_seat_seat FOREIGN KEY (seat_id) 
        REFERENCES seat(id) ON DELETE RESTRICT,
    CONSTRAINT uk_booking_seat UNIQUE (booking_id, seat_id),
    
    INDEX idx_booking_seat_booking (booking_id),
    INDEX idx_booking_seat_seat (seat_id)
);
```

---

### **Part 4: Payment Entity**

```sql
-- ═══════════════════════════════════════════════════════════
-- PAYMENT PROCESSING
-- ═══════════════════════════════════════════════════════════

CREATE TABLE payment (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    booking_id VARCHAR(36) NOT NULL UNIQUE,  -- 1:1 relationship
    user_id BIGINT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    payment_mode VARCHAR(50) NOT NULL,  -- CARD, UPI, WALLET, NET_BANKING
    transaction_id VARCHAR(255) UNIQUE,  -- From payment gateway
    gateway_name VARCHAR(50) NOT NULL,  -- Stripe, Razorpay, PayU
    idempotency_key VARCHAR(255) UNIQUE NOT NULL,  -- Prevent double charging
    status VARCHAR(20) NOT NULL,  -- PENDING, SUCCESS, FAILED, REFUNDED
    failure_reason TEXT,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    refunded_at TIMESTAMP,
    
    CONSTRAINT fk_payment_booking FOREIGN KEY (booking_id) 
        REFERENCES booking(id) ON DELETE RESTRICT,
    CONSTRAINT fk_payment_user FOREIGN KEY (user_id) 
        REFERENCES user(id) ON DELETE RESTRICT,
    CONSTRAINT chk_payment_status CHECK (status IN 
        ('PENDING', 'SUCCESS', 'FAILED', 'REFUNDED')),
    CONSTRAINT chk_payment_amount CHECK (amount > 0),
    
    INDEX idx_payment_booking (booking_id),
    INDEX idx_payment_user (user_id),
    INDEX idx_payment_transaction_id (transaction_id),
    INDEX idx_payment_idempotency_key (idempotency_key),
    INDEX idx_payment_status (status),
    INDEX idx_payment_created_at (created_at DESC)
);
```

---

### **Part 5: Review & Rating Entity**

```sql
-- ═══════════════════════════════════════════════════════════
-- REVIEWS
-- ═══════════════════════════════════════════════════════════

CREATE TABLE review (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    movie_id BIGINT NOT NULL,
    rating INT NOT NULL,  -- 1-5 stars
    comment TEXT,
    is_verified_booking BOOLEAN NOT NULL DEFAULT false,  -- Did user actually watch?
    helpful_count INT NOT NULL DEFAULT 0,  -- Upvotes
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_review_user FOREIGN KEY (user_id) 
        REFERENCES user(id) ON DELETE CASCADE,
    CONSTRAINT fk_review_movie FOREIGN KEY (movie_id) 
        REFERENCES movie(id) ON DELETE CASCADE,
    CONSTRAINT chk_review_rating CHECK (rating BETWEEN 1 AND 5),
    CONSTRAINT uk_review_user_movie UNIQUE (user_id, movie_id),  -- One review per user per movie
    
    INDEX idx_review_movie (movie_id),
    INDEX idx_review_user (user_id),
    INDEX idx_review_rating (rating DESC),
    INDEX idx_review_helpful (helpful_count DESC),
    INDEX idx_review_created_at (created_at DESC)
);
```

---

## 📊 Part 6: Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  ENTITY RELATIONSHIPS                        │
└─────────────────────────────────────────────────────────────┘

    CITY                    THEATER                 SCREEN
    ┌────┐ 1           N    ┌────┐ 1          N    ┌────┐
    │City├──────────────────►Theater├──────────────►Screen│
    └────┘                  └────┘                 └────┬─┘
                                                         │
                                                         │ 1
                                                         │
                                                         ▼ N
                                                    ┌────────┐
                                                    │  Seat  │
                                                    └────────┘
    
    MOVIE                   SHOW                SEAT_AVAILABILITY
    ┌────┐ 1          N    ┌────┐ 1          N    ┌────────────┐
    │Movie├───────────────►│Show├──────────────────►SeatAvailabi│
    └────┘                 └────┘                  └────────────┘
     │ 1                     │ 1
     │                       │
     │ N                     │ N
     ▼                       ▼
    ┌──────┐             ┌────────┐
    │Review│             │Booking │
    └──┬───┘             └────┬───┘
       │ N                    │ 1
       │                      │
       │                      ▼ 1
       │                  ┌─────────┐
       │                  │Payment  │
       │                  └─────────┘
       │                      │ 1
       │                      │
       │ N                    │ N
    ┌──▼──┐                   ▼
    │User │◄──────────────┌───────────┐
    └─────┘               │BookingSeat│
                          └───────────┘
                               │ N
                               │
                               ▼ 1
                           ┌────────┐
                           │  Seat  │
                           └────────┘

CARDINALITY KEY:
1   = One
N   = Many
1:N = One-to-Many
N:M = Many-to-Many (requires join table)
```

---

## 🎯 Part 7: Critical Design Decisions

### **Decision 1: Why UUID for booking_id?**

```sql
-- ✅ GOOD: UUID (VARCHAR(36))
id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()

-- ❌ BAD: Sequential BIGINT
id BIGSERIAL PRIMARY KEY
```

**Reasons:**
1. **Security**: Sequential IDs expose business metrics (booking count)
2. **Idempotency**: Client can generate UUID before request (retry-safe)
3. **Distributed systems**: No coordination needed across shards
4. **URL safety**: `/bookings/550e8400-e29b-41d4-a716-446655440000` vs `/bookings/12345`

**Trade-off**: UUIDs are larger (36 bytes vs 8 bytes), but worth it for security

---

### **Decision 2: Denormalize `available_seats` in Show table?**

```sql
-- Option 1: Denormalized (RECOMMENDED)
CREATE TABLE show (
    ...
    available_seats INT NOT NULL,  -- Updated on each booking
    total_seats INT NOT NULL
);

-- Option 2: Normalized (calculate on demand)
SELECT total_seats - COUNT(CASE WHEN status = 'BOOKED' THEN 1 END)
FROM seat_availability
WHERE show_id = 123;
```

**Why denormalize:**
1. **Performance**: Avoid COUNT() on millions of seat_availability rows
2. **Frequent reads**: "Available seats" shown on every search result
3. **Acceptable staleness**: 1-second cache is fine
4. **Easy to maintain**: Update in same transaction as booking

**How to keep consistent:**
```sql
BEGIN;
-- Book seats
UPDATE seat_availability SET status = 'BOOKED' WHERE ...;
-- Update counter
UPDATE show SET available_seats = available_seats - 3 WHERE id = 123;
COMMIT;
```

---

### **Decision 3: Separate seat_availability table?**

```sql
-- Why not just add status to seat table?
CREATE TABLE seat (
    ...
    status VARCHAR(20)  -- ❌ BAD! Same seat, different status per show
);

-- ✅ GOOD: Separate table
CREATE TABLE seat_availability (
    show_id BIGINT,
    seat_id BIGINT,
    status VARCHAR(20),
    PRIMARY KEY (show_id, seat_id)
);
```

**Reasons:**
1. **Same seat, different shows**: Seat 5 is AVAILABLE for Show 1, BOOKED for Show 2
2. **Isolation**: Each show's seat status is independent
3. **Partitioning**: Can partition by show_id for performance

---

### **Decision 4: Soft delete vs Hard delete?**

```sql
CREATE TABLE user (
    ...
    deleted_at TIMESTAMP,  -- NULL = active, non-NULL = soft deleted
    INDEX idx_user_deleted (deleted_at)
);

-- Query active users
SELECT * FROM user WHERE deleted_at IS NULL;
```

**Reasons:**
1. **GDPR compliance**: User requests deletion, mark as deleted
2. **Audit trail**: Keep booking history even after user deletion
3. **Accidental deletion recovery**: Can undelete within 30 days
4. **Foreign key safety**: Bookings still reference valid user_id

---

## 💡 Interview Key Points:

**Perfect Summary:**

> "I've designed 12 core entities with proper relationships:
> 
> **Location hierarchy**: City (1) → Theater (N) → Screen (N) → Seat (N)
> 
> **Booking flow**: Movie (1) → Show (N) → SeatAvailability (N) → Booking (N) → Payment (1:1)
> 
> **Key decisions**:
> 1. **UUID for booking_id**: Security + idempotency
> 2. **Denormalized available_seats**: Performance (avoid COUNT queries)
> 3. **Separate seat_availability**: Same seat, different shows
> 4. **Soft deletes**: GDPR compliance + audit trail
> 5. **Composite PK (show_id, seat_id)**: Natural for seat_availability
> 
> **Indexes**:
> - All foreign keys indexed
> - Status fields for filtering
> - created_at DESC for pagination
> - expires_at for expiry cleanup job
> 
> **Constraints**:
> - CHECK constraints for enum validation
> - UNIQUE constraints prevent overlapping shows
> - ON DELETE CASCADE for dependent entities
> - ON DELETE RESTRICT for critical references"

This demonstrates senior database design expertise! 🎯
