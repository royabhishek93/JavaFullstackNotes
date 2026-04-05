# Q26: Database Schema Design - Complete production-ready schema

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Complete Schema:

```sql
-- ═══════════════════════════════════════════════════════════
-- CORE BOOKING ENTITIES
-- ═══════════════════════════════════════════════════════════

CREATE TABLE user (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_email (email),
    INDEX idx_phone (phone)
);

CREATE TABLE movie (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    duration_minutes INT NOT NULL,
    release_date DATE NOT NULL,
    rating VARCHAR(10),  -- U, UA, A, R
    languages JSON NOT NULL,  -- ["English", "Hindi"]
    genres JSON NOT NULL,     -- ["Action", "Thriller"]
    poster_url VARCHAR(500),
    trailer_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_release_date (release_date DESC),
    INDEX idx_title (title)
);

CREATE TABLE city (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'India',
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE theater (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    city_id BIGINT NOT NULL REFERENCES city(id),
    address TEXT NOT NULL,
    location POINT NOT NULL,  -- PostGIS: (lat, lon)
    total_screens INT NOT NULL,
    facilities JSON,  -- ["parking", "food_court", "wheelchair_access"]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_city (city_id),
    INDEX idx_location USING GIST(location)  -- Geo-spatial index
);

CREATE TABLE screen (
    id BIGSERIAL PRIMARY KEY,
    theater_id BIGINT NOT NULL REFERENCES theater(id),
    screen_number INT NOT NULL,
    total_seats INT NOT NULL,
    screen_type VARCHAR(50),  -- IMAX, 4DX, STANDARD
    
    UNIQUE(theater_id, screen_number),
    INDEX idx_theater (theater_id)
);

CREATE TABLE seat (
    id BIGSERIAL PRIMARY KEY,
    screen_id BIGINT NOT NULL REFERENCES screen(id),
    seat_row VARCHAR(5) NOT NULL,   -- A, B, C, ...
    seat_number INT NOT NULL,        -- 1, 2, 3, ...
    seat_type VARCHAR(20) NOT NULL,  -- REGULAR, PREMIUM, RECLINER
    
    UNIQUE(screen_id, seat_row, seat_number),
    INDEX idx_screen (screen_id)
);

-- ═══════════════════════════════════════════════════════════
-- SHOW & AVAILABILITY
-- ═══════════════════════════════════════════════════════════

CREATE TABLE show (
    id BIGSERIAL PRIMARY KEY,
    movie_id BIGINT NOT NULL REFERENCES movie(id),
    screen_id BIGINT NOT NULL REFERENCES screen(id),
    show_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    language VARCHAR(50) NOT NULL,
    total_seats INT NOT NULL,
    available_seats INT NOT NULL,  -- Denormalized for performance
    base_price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_movie_date (movie_id, show_date),
    INDEX idx_screen_date (screen_id, show_date),
    INDEX idx_show_date_time (show_date, start_time),
    
    CONSTRAINT chk_available_seats 
        CHECK (available_seats >= 0 AND available_seats <= total_seats)
);

CREATE TABLE seat_availability (
    show_id BIGINT NOT NULL REFERENCES show(id),
    seat_id BIGINT NOT NULL REFERENCES seat(id),
    status VARCHAR(20) NOT NULL,  -- AVAILABLE, RESERVED, BOOKED
    booking_id VARCHAR(36),
    reserved_until TIMESTAMP,     -- For RESERVED status
    price DECIMAL(10,2) NOT NULL,
    
    PRIMARY KEY (show_id, seat_id),
    INDEX idx_status (show_id, status),
    INDEX idx_reserved_until (reserved_until),
    INDEX idx_booking (booking_id)
);

-- ═══════════════════════════════════════════════════════════
-- BOOKING & PAYMENT
-- ═══════════════════════════════════════════════════════════

CREATE TABLE booking (
    id VARCHAR(36) PRIMARY KEY,  -- UUID for security
    user_id BIGINT NOT NULL REFERENCES user(id),
    show_id BIGINT NOT NULL REFERENCES show(id),
    booking_status VARCHAR(20) NOT NULL,  -- PENDING, CONFIRMED, EXPIRED, CANCELLED
    total_seats INT NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    convenience_fee DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,  -- created_at + 15 minutes
    cancelled_at TIMESTAMP,
    cancellation_reason TEXT,
    
    INDEX idx_user (user_id, created_at DESC),
    INDEX idx_show (show_id),
    INDEX idx_status (booking_status),
    INDEX idx_expires_at (expires_at),  -- For cleanup job
    INDEX idx_created_at (created_at DESC)
);

CREATE TABLE booking_seat (
    id BIGSERIAL PRIMARY KEY,
    booking_id VARCHAR(36) NOT NULL REFERENCES booking(id),
    seat_id BIGINT NOT NULL REFERENCES seat(id),
    price DECIMAL(10,2) NOT NULL,
    
    UNIQUE(booking_id, seat_id),
    INDEX idx_booking (booking_id)
);

CREATE TABLE payment (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    booking_id VARCHAR(36) UNIQUE NOT NULL REFERENCES booking(id),
    transaction_id VARCHAR(255) UNIQUE,  -- Stripe payment intent ID
    idempotency_key VARCHAR(255) UNIQUE NOT NULL,
    payment_method VARCHAR(50),  -- CARD, UPI, WALLET
    payment_gateway VARCHAR(50),  -- STRIPE, RAZORPAY
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    status VARCHAR(20) NOT NULL,  -- PENDING, SUCCESS, FAILED, REFUNDED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    refunded_at TIMESTAMP,
    
    INDEX idx_booking (booking_id),
    INDEX idx_transaction (transaction_id),
    INDEX idx_idempotency (idempotency_key),
    INDEX idx_status (status)
);

-- ═══════════════════════════════════════════════════════════
-- PRICING & OFFERS
-- ═══════════════════════════════════════════════════════════

CREATE TABLE seat_pricing (
    id BIGSERIAL PRIMARY KEY,
    show_id BIGINT NOT NULL REFERENCES show(id),
    seat_type VARCHAR(20) NOT NULL,  -- REGULAR, PREMIUM, RECLINER
    price DECIMAL(10,2) NOT NULL,
    
    UNIQUE(show_id, seat_type),
    INDEX idx_show (show_id)
);

CREATE TABLE offer (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    discount_type VARCHAR(20) NOT NULL,  -- PERCENTAGE, FLAT
    discount_value DECIMAL(10,2) NOT NULL,
    min_booking_amount DECIMAL(10,2),
    max_discount DECIMAL(10,2),
    valid_from TIMESTAMP NOT NULL,
    valid_until TIMESTAMP NOT NULL,
    max_uses INT,
    current_uses INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX idx_code (code),
    INDEX idx_valid_dates (valid_from, valid_until)
);

CREATE TABLE user_offer_usage (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES user(id),
    offer_id BIGINT NOT NULL REFERENCES offer(id),
    booking_id VARCHAR(36) NOT NULL REFERENCES booking(id),
    discount_amount DECIMAL(10,2) NOT NULL,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, offer_id, booking_id),
    INDEX idx_user (user_id),
    INDEX idx_offer (offer_id)
);

-- ═══════════════════════════════════════════════════════════
-- AUDITING & MONITORING
-- ═══════════════════════════════════════════════════════════

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,  -- BOOKING, PAYMENT, SEAT
    entity_id VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL,  -- CREATE, UPDATE, DELETE
    old_value JSONB,
    new_value JSONB,
    user_id BIGINT,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_user (user_id, created_at DESC),
    INDEX idx_created_at (created_at DESC)
);

CREATE TABLE idempotency_record (
    key VARCHAR(255) PRIMARY KEY,
    request_body TEXT NOT NULL,
    response_body TEXT,
    status VARCHAR(20) NOT NULL,  -- PROCESSING, COMPLETED, FAILED
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,  -- created_at + 24 hours
    
    INDEX idx_expires_at (expires_at),
    INDEX idx_created_at (created_at DESC)
);

-- ═══════════════════════════════════════════════════════════
-- PARTITIONING (For large tables)
-- ═══════════════════════════════════════════════════════════

-- Partition booking table by created_at (monthly)
CREATE TABLE booking_2026_01 PARTITION OF booking
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE booking_2026_02 PARTITION OF booking
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

-- Partition audit_log by created_at (monthly)
CREATE TABLE audit_log_2026_01 PARTITION OF audit_log
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

---
