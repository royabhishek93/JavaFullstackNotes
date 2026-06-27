# Database Schema Visual Guide - Movie Ticket Booking System

## 📊 Complete ER Diagram (Entity Relationship) - CORRECTED

```
┌─────────────────────────────────────┐
│          USERS                      │
│─────────────────────────────────────│
│ 🔑 id (UUID)                        │
│ 🔓 email (UNIQUE, NOT NULL)         │
│    name VARCHAR(255)                │
│    phone VARCHAR(20)                │
│    created_at TIMESTAMP             │
│    updated_at TIMESTAMP             │ ← ADDED
└────────────┬────────────────────────┘
             │
             │ 🔗 locked_by
             │ (ON DELETE SET NULL)
             │
             ▼
┌──────────────────────────┐         ┌──────────────────────────┐
│        MOVIES            │         │      THEATERS            │
│──────────────────────────│         │──────────────────────────│
│ 🔑 id (UUID)             │         │ 🔑 id (UUID)             │
│    title VARCHAR(255)    │         │    name VARCHAR(255)     │
│    duration INT          │         │    location VARCHAR(255) │
│    language VARCHAR(50)  │         │    city VARCHAR(100)     │
│    rating VARCHAR(10)    │         │ ℹ️ total_capacity (REMOVE)
│    genre VARCHAR(100)    │         │    created_at TIMESTAMP  │
│    created_at TIMESTAMP  │         │    updated_at TIMESTAMP  │
│    updated_at TIMESTAMP  │ ← ADDED │ ← ADDED                  │
└────────────┬─────────────┘         └────────────┬─────────────┘
             │                                    │
             │                                    │
             │        ┌───────────────────────────┘
             │        │
             │        │ 🔗 (ON DELETE RESTRICT)
             │        ▼
             │    ┌──────────────────────────────┐
             │    │      SCREENS                 │
             │    │──────────────────────────────│
             │    │ 🔑 id (UUID)                 │
             │    │ 🔗 theater_id (ON DEL RESTR) │
             │    │ 🔓 (theater_id, screen_num)  │ ← UNIQUE
             │    │    screen_number INT         │
             │    │    screen_name VARCHAR(100) │
             │    │    total_seats INT           │
             │    │    created_at TIMESTAMP      │
             │    │    updated_at TIMESTAMP      │ ← ADDED
             │    └────────┬──────────────────────┘
             │             │
             │             │ 🔗 (ON DELETE RESTRICT)
             │         ┌───┘
             │         │
             ▼         ▼
        ┌────────────────────────────────┐
        │       SHOWS                    │
        │────────────────────────────────│
        │ 🔑 id (UUID)                   │
        │ 🔗 movie_id (ON DELETE RESTR)  │
        │ 🔗 screen_id (ON DELETE RESTR) │
        │    show_time TIMESTAMP         │
        │    status: ACTIVE|CANCELLED    │ ← ENUM
        │    created_at TIMESTAMP        │
        │    updated_at TIMESTAMP        │ ← ADDED
        └────────────┬───────────────────┘
                     │
                     │ 🔗 (ONE-TO-MANY)
                     │
                     ▼
        ┌────────────────────────────────────┐
        │       SEATS                        │
        │────────────────────────────────────│
        │ 🔑 id (UUID)                       │
        │ 🔗 show_id (ON DEL CASCADE)        │
        │ 🔗 locked_by (ON DEL SET NULL)     │
        │ 🔓 (show_id, seat_number) UNIQUE   │ ← COMPOSITE KEY
        │    seat_number VARCHAR(10)        │
        │    row VARCHAR(5)                 │
        │    seat_type: STANDARD|PREMIUM    │ ← ENUM
        │    status: AVAIL|LOCKED|BOOKED    │ ← ENUM
        │    price DECIMAL(10,2)            │
        │    locked_at TIMESTAMP            │
        │    locked_until TIMESTAMP (CRIT)  │ ← INDEX for cleanup
        │    version INT (optimistic lock)  │
        │    created_at TIMESTAMP           │
        │    updated_at TIMESTAMP           │ ← ADDED
        └────────────┬─────────────────────┘
                     │                    ▲
                     │                    │
                     │ 🔗 (linked via)    └─ locked by user
                     │                       (see: USERS)
                     ▼
        ┌────────────────────────────────────┐
        │      BOOKINGS                      │
        │────────────────────────────────────│
        │ 🔑 id (UUID)                       │
        │ 🔗 show_id (ON DEL RESTRICT)       │
        │ 🔗 user_id (ON DEL RESTRICT)       │
        │ 🔗 seat_id (ON DEL RESTRICT)       │
        │ 🔗 payment_id (nullable, FKs added)│ ← NULLABLE
        │ 🔓 (show_id, seat_id) UNIQUE       │ ← NO DOUBLE BOOK
        │ 🔓 idempotency_key UNIQUE          │ ← PREVENT DUPES
        │    booking_time TIMESTAMP          │
        │    status: PENDING|CONFIRMED|CANC  │ ← ENUM
        │    total_amount DECIMAL(10,2)     │
        │    booked_at TIMESTAMP             │
        │    payment_timeout TIMESTAMP (NEW) │ ← Booking expires
        │    created_at TIMESTAMP            │
        │    updated_at TIMESTAMP            │ ← ADDED
        └────────────┬─────────────────────┘
                     │
                     │ 🔗 (ONE-TO-ONE)
                     ▼
        ┌────────────────────────────────────┐
        │      PAYMENTS                      │
        │────────────────────────────────────│
        │ 🔑 id (UUID)                       │
        │ 🔗 booking_id (ON DEL RESTRICT)    │
        │    amount DECIMAL(10,2)            │
        │    payment_method VARCHAR(50)      │
        │    status: PENDING|SUCCESS|FAILED  │ ← ENUM
        │    transaction_id VARCHAR(255)     │
        │    paid_at TIMESTAMP (nullable)    │
        │    created_at TIMESTAMP            │
        │    updated_at TIMESTAMP            │ ← ADDED
        └────────────────────────────────────┘
```

**Legend:**
- 🔑 = Primary Key
- 🔗 = Foreign Key (with referential action)
- 🔓 = Unique Constraint
- ℹ️  = Issue/Remove/Normalize
- ENUM = Valid values documented
- ← = NEW or FIXED


## 🔄 Table Relationships Explained

### 0️⃣ **THEATERS ↔ SCREENS** (One-to-Many)

```
One Theater has Multiple Screens (Auditoriums)

Example:
┌────────────────────┐
│ Theater: PVR Phoenix │
└────────┬───────────┘
         │
         ├─── Screen 1 (100 seats)
         ├─── Screen 2 (150 seats)
         ├─── Screen 3 (200 seats)
         └─── Screen 4 (120 seats)
```

**SQL:**
```sql
SELECT sc.screen_name, sc.total_seats
FROM screens sc
WHERE sc.theater_id = 'TH001'
ORDER BY sc.screen_number;
```

---

### 1️⃣ **MOVIES ↔ SHOWS** (One-to-Many)

```
One Movie can have Multiple Shows

Example:
┌────────────────┐
│ Movie: Oppenheimer │
└────────┬───────┘
         │
         ├─── Show 1: Dec 10, 10:00 AM, Theater A
         ├─── Show 2: Dec 10, 2:00 PM, Theater A
         ├─── Show 3: Dec 10, 6:00 PM, Theater B
         └─── Show 4: Dec 11, 10:00 AM, Theater A
```

**SQL:**
```sql
SELECT s.show_time, sc.screen_name, t.name as theater_name
FROM shows s
JOIN movies m ON s.movie_id = m.id
JOIN screens sc ON s.screen_id = sc.id
JOIN theaters t ON sc.theater_id = t.id
WHERE m.title = 'Oppenheimer';
```

---

### 2️⃣ **SCREENS ↔ SHOWS** (One-to-Many)

```
One Screen can host Multiple Shows

Example:
┌────────────────────┐
│ Screen 1: PVR Phoenix │
└────────┬───────────┘
         │
         ├─── Show 1: Oppenheimer, 10:00 AM
         ├─── Show 2: Barbie, 1:00 PM
         ├─── Show 3: Oppenheimer, 4:00 PM
         └─── Show 4: Mission Impossible, 7:00 PM
```

**Key difference from before:**
- Shows are now linked to **SCREENS** (not THEATERS)
- Multiple screens in same theater can show different movies at same time
- Each screen has its own seat inventory

---

### 3️⃣ **SHOWS ↔ SEATS** (One-to-Many)

```
One Show has Multiple Seats

Example:
┌──────────────────────────┐
│ Show: Oppenheimer        │
│ Time: Dec 10, 10:00 AM   │
│ Theater: PVR Phoenix      │
└────────┬─────────────────┘
         │
         ├─── Seat A1 (AVAILABLE, ₹200)
         ├─── Seat A2 (LOCKED by User123, ₹200)
         ├─── Seat A3 (BOOKED, ₹200)
         ├─── Seat B1 (AVAILABLE, ₹300)
         └─── ... (100 more seats)
```

**Critical Columns:**
- `status`: AVAILABLE | LOCKED | BOOKED
- `locked_by`: User who temporarily locked this seat
- `locked_until`: Auto-release time (e.g., 10 min from locked_at)

---

### 4️⃣ **USERS ↔ SEATS** (Temporary Lock - Many-to-Many)

```
User locks seats temporarily during booking flow

Example Timeline:
┌─────────────────────────────────────────────────────┐
│ User: john@example.com (User123)                    │
└─────────────────┬───────────────────────────────────┘
                  │
    T=0 sec       ├─── Locks Seat A2, A3
                  │    (locked_until = T+10min)
                  │
    T=2 min       ├─── Processes payment
                  │
    T=3 min       ├─── Payment SUCCESS
                  │    → Seats A2, A3 status: LOCKED → BOOKED
                  │    → Creates BOOKING record
                  │
                  └─── User gets booking confirmation
```

**If Payment Fails:**
```
    T=2 min       ├─── Payment FAILED
                  │    → Seats A2, A3 status: LOCKED → AVAILABLE
                  │    → locked_by = NULL
                  │
                  └─── User gets error message
```

---

### 5️⃣ **BOOKINGS ↔ SEATS** (Many-to-One per row)

```
One Booking row contains one seat via `seat_id`

Example:
┌──────────────────────────────────┐
│ BOOKING: #BK12345                │
│ User: john@example.com            │
│ Show: Oppenheimer, Dec 10, 10 AM │
│ Seat: A2                         │
│ Total: ₹200                      │
│ Status: CONFIRMED                 │
└────────┬─────────────────────────┘
         │
         └─── Linked directly by bookings.seat_id
```

---

### 6️⃣ **BOOKINGS ↔ PAYMENTS** (One-to-One)

```
One Booking has One Payment

┌──────────────────────┐      ┌──────────────────────┐
│ BOOKING: #BK12345    │──────│ PAYMENT: #PAY789     │
│ Amount: ₹600         │      │ Amount: ₹600         │
│ Status: CONFIRMED    │      │ Method: UPI          │
│                      │      │ Transaction: XYZ123  │
│                      │      │ Status: SUCCESS      │
└──────────────────────┘      └──────────────────────┘
```

---

## 🎬 Complete Booking Flow (Visual)

### Step-by-Step Database State Changes

#### **Initial State (User browsing)**

```
SEATS TABLE:
┌────┬─────────┬────────┬────────────┬───────────┬────────────┐
│ ID │ Show ID │ Number │ Status     │ Locked By │ Locked Until│
├────┼─────────┼────────┼────────────┼───────────┼────────────┤
│ S1 │ SH001   │ A1     │ AVAILABLE  │ NULL      │ NULL       │
│ S2 │ SH001   │ A2     │ AVAILABLE  │ NULL      │ NULL       │
│ S3 │ SH001   │ A3     │ AVAILABLE  │ NULL      │ NULL       │
└────┴─────────┴────────┴────────────┴───────────┴────────────┘
```

#### **Step 1: User Selects Seats (Lock Acquired)**

```
User clicks: "Select A2, A3"

SEATS TABLE:
┌────┬─────────┬────────┬────────────┬───────────┬─────────────────┐
│ ID │ Show ID │ Number │ Status     │ Locked By │ Locked Until     │
├────┼─────────┼────────┼────────────┼───────────┼─────────────────┤
│ S1 │ SH001   │ A1     │ AVAILABLE  │ NULL      │ NULL            │
│ S2 │ SH001   │ A2     │ LOCKED 🔒  │ U123      │ 10:10 AM        │
│ S3 │ SH001   │ A3     │ LOCKED 🔒  │ U123      │ 10:10 AM        │
└────┴─────────┴────────┴────────────┴───────────┴─────────────────┘

Current Time: 10:00 AM
Lock Expires: 10:10 AM (10 minutes)
```

**SQL Executed:**
```sql
-- Lock seats atomically
UPDATE seats 
SET status = 'LOCKED',
    locked_by = 'U123',
    locked_at = NOW(),
    locked_until = NOW() + INTERVAL '10 minutes'
WHERE id IN ('S2', 'S3')
  AND status = 'AVAILABLE'  -- Only lock if available
  AND locked_until < NOW(); -- Or if previous lock expired
```

#### **Step 2: User Proceeds to Payment (Processing)**

```
User enters payment details...

BOOKINGS TABLE: (No entry yet, payment not done)
Empty

SEATS TABLE: (Still locked, unchanged)
┌────┬─────────┬────────┬────────────┬───────────┬─────────────────┐
│ S2 │ SH001   │ A2     │ LOCKED 🔒  │ U123      │ 10:10 AM        │
│ S3 │ SH001   │ A3     │ LOCKED 🔒  │ U123      │ 10:10 AM        │
└────┴─────────┴────────┴────────────┴───────────┴─────────────────┘
```

#### **Step 3a: Payment SUCCESS ✅**

```
Payment gateway returns: SUCCESS

PAYMENTS TABLE:
┌──────────┬────────────┬────────┬────────┬────────────────┬─────────┐
│ ID       │ Booking ID │ Amount │ Method │ Transaction ID │ Status  │
├──────────┼────────────┼────────┼────────┼────────────────┼─────────┤
│ PAY789   │ BK12345    │ ₹400   │ UPI    │ TXN_XYZ123     │ SUCCESS │
└──────────┴────────────┴────────┴────────┴────────────────┴─────────┘

BOOKINGS TABLE:
┌──────────┬─────────┬─────────┬─────────┬────────────┬────────────┬────────────┐
│ ID       │ Show ID │ User ID │ Seat ID │ Status     │ Amount     │ Payment ID │
├──────────┼─────────┼─────────┼─────────┼────────────┼────────────┼────────────┤
│ BK12345  │ SH001   │ U123    │ S2      │ CONFIRMED  │ ₹200       │ PAY789     │
└──────────┴─────────┴─────────┴─────────┴────────────┴────────────┴────────────┘

SEATS TABLE:
┌────┬─────────┬────────┬────────────┬───────────┬──────────────┐
│ ID │ Show ID │ Number │ Status     │ Locked By │ Locked Until │
├────┼─────────┼────────┼────────────┼───────────┼──────────────┤
│ S2 │ SH001   │ A2     │ BOOKED ✅  │ NULL      │ NULL         │
│ S3 │ SH001   │ A3     │ AVAILABLE  │ NULL      │ NULL         │
└────┴─────────┴────────┴────────────┴───────────┴──────────────┘
```

**SQL Executed:**
```sql
-- All in ONE transaction
BEGIN TRANSACTION;

-- 1. Create payment record
INSERT INTO payments (id, amount, status, transaction_id) 
VALUES ('PAY789', 400, 'SUCCESS', 'TXN_XYZ123');

-- 2. Create booking record
INSERT INTO bookings (id, show_id, user_id, seat_id, status, total_amount, payment_id, booked_at)
VALUES ('BK12345', 'SH001', 'U123', 'S2', 'CONFIRMED', 200, 'PAY789', NOW());

-- 3. Mark seat as BOOKED (release lock)
UPDATE seats 
SET status = 'BOOKED',
    locked_by = NULL,
    locked_at = NULL,
    locked_until = NULL
WHERE id = 'S2';

COMMIT;
```

#### **Step 3b: Payment FAILED ❌**

```
Payment gateway returns: FAILED

PAYMENTS TABLE:
┌──────────┬────────────┬────────┬────────┬────────────────┬─────────┐
│ ID       │ Booking ID │ Amount │ Method │ Transaction ID │ Status  │
├──────────┼────────────┼────────┼────────┼────────────────┼─────────┤
│ PAY789   │ NULL       │ ₹400   │ UPI    │ NULL           │ FAILED  │
└──────────┴────────────┴────────┴────────┴────────────────┴─────────┘

BOOKINGS TABLE: (No entry created)
Empty

SEATS TABLE: (Locks released, back to AVAILABLE)
┌────┬─────────┬────────┬──────────────┬───────────┬──────────────┐
│ ID │ Show ID │ Number │ Status       │ Locked By │ Locked Until │
├────┼─────────┼────────┼──────────────┼───────────┼──────────────┤
│ S2 │ SH001   │ A2     │ AVAILABLE ✅ │ NULL      │ NULL         │
│ S3 │ SH001   │ A3     │ AVAILABLE ✅ │ NULL      │ NULL         │
└────┴─────────┴────────┴──────────────┴───────────┴──────────────┘
```

**SQL Executed:**
```sql
-- Rollback transaction
BEGIN TRANSACTION;

-- 1. Record failed payment (for audit)
INSERT INTO payments (id, amount, status) 
VALUES ('PAY789', 400, 'FAILED');

-- 2. Release locked seats
UPDATE seats 
SET status = 'AVAILABLE',
    locked_by = NULL,
    locked_at = NULL,
    locked_until = NULL
WHERE id IN ('S2', 'S3') 
  AND status = 'LOCKED'
  AND locked_by = 'U123';

COMMIT;
```

---

## � Schema Review & Issues Found

### ✅ What's Good
1. ✅ SCREENS table properly added (THEATERS → SCREENS → SHOWS)
2. ✅ Seat locking mechanism with `locked_by`, `locked_at`, `locked_until`
3. ✅ `version` field in SEATS for optimistic locking
4. ✅ `idempotency_key` in BOOKINGS for duplicate prevention
5. ✅ Simplified single-row booking model using `bookings.seat_id`
6. ✅ Proper cascading relationships

### ⚠️ Critical Issues Found

#### 1. **Missing Composite Unique Constraints**
```
❌ ISSUE: Duplicate screens in same theater
  - No unique constraint on (theater_id, screen_number)

❌ ISSUE: Duplicate seats in same show
  - No unique constraint on (show_id, seat_number)

❌ ISSUE: Duplicate seat bookings for same show
  - No unique constraint on (show_id, seat_id)
```

#### 2. **Missing FK Referential Actions (ON DELETE/UPDATE)**
```
❌ ISSUE: What happens when user is deleted?
  - locks in SEATS.locked_by point to non-existent user
  - Solution: SET NULL or RESTRICT

❌ ISSUE: What happens when show is cancelled?
  - SEATS records orphaned
  - BOOKINGS records orphaned
  - Solution: CASCADE DELETE or RESTRICT

❌ ISSUE: Screen deletion from theater?
  - SHOWS still reference deleted screen
  - Solution: RESTRICT (prevent deletion with active shows)
```

**Example:**
```sql
-- Current (INCOMPLETE):
CONSTRAINT fk_seats_show FOREIGN KEY (show_id) REFERENCES shows(id)

-- Should be:
CONSTRAINT fk_seats_show FOREIGN KEY (show_id) 
  REFERENCES shows(id) ON DELETE RESTRICT,
CONSTRAINT fk_seats_locked_by FOREIGN KEY (locked_by) 
  REFERENCES users(id) ON DELETE SET NULL
```

#### 3. **Ambiguous Status Fields (No Valid Values Documented)**
```
❌ SHOWS.status → Valid values? (ACTIVE, CANCELLED, UPCOMING?)
❌ SEATS.status → Valid values? (AVAILABLE, LOCKED, BOOKED, BLOCKED?)
❌ BOOKINGS.status → Valid values? (PENDING, CONFIRMED, CANCELLED, COMPLETED?)
❌ PAYMENTS.status → Valid values? (PENDING, SUCCESS, FAILED, REFUNDED?)
❌ SEATS.seat_type → Valid values? (STANDARD, PREMIUM, VIP, WHEELCHAIR?)
```

#### 4. **Nullable Foreign Key Without Documentation**
```
❌ BOOKINGS.payment_id IS NULLABLE
  - Why? Because booking is created BEFORE payment completes
  - But this needs to be documented with business logic:
    * After payment succeeds → payment_id gets set
    * After payment fails → booking should be CANCELLED
    * After refund → payment_id can stay set but status changes
  
  Problem: If payment_id is still NULL after timeout, is booking invalid?
  Answer needed: What's the max time a booking can stay without payment?
```

#### 5. **Missing Audit Timestamps**
```
❌ No updated_at field for modification tracking
❌ No created_by / updated_by for audit trail

Should add to all tables:
  - created_at ✓ (has)
  - updated_at ✗ (missing)
  - deleted_at (soft delete, optional)
```

#### 6. **Redundant Fields**
```
❌ THEATERS.total_capacity seems redundant
  - This should be SUM(screens.total_seats) for a theater
  - Keeping it requires a maintenance view/trigger
  - Consider: Remove and calculate on-the-fly, OR keep with trigger
```

#### 7. **Missing Indexes in Diagram**
```
❌ Not shown: Critical indexes for performance
  - idx_screens_theater (for finding screens by theater)
  - idx_shows_screen (for finding shows in a screen)
  - idx_seat_availability (show_id, status) CRITICAL
  - idx_seats_locked_until (for auto-release job)
  - idx_bookings_user (for user's booking history)
```

#### 8. **Price Model Issue**
```
⚠️ Each SEAT has individual price column
  - Question: Can seat A1 and A2 have different prices?
  - If yes: ✅ Good for dynamic pricing, surge pricing
  - If no: ❌ Redundant, should use seat_type instead
  
  Current design allows flexibility but uses more storage.
  Consider normalization:
  - seats.seat_type (FK → seat_types table)
  - seat_types.price
```

---

## �🔐 Table Structure & Constraints

### CREATE TABLE Statements (with SCREENS)

```sql
-- Base tables (no FKs)
CREATE TABLE users (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE movies (
    id UUID PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    duration INT NOT NULL,
    language VARCHAR(50),
    rating VARCHAR(10),
    genre VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE theaters (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    total_capacity INT,
    city VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- SCREENS table (new addition)
CREATE TABLE screens (
    id UUID PRIMARY KEY,
    theater_id UUID NOT NULL,
    screen_number INT NOT NULL,
    screen_name VARCHAR(100),
    total_seats INT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_screens_theater FOREIGN KEY (theater_id) REFERENCES theaters(id),
    CONSTRAINT unique_screen_per_theater UNIQUE(theater_id, screen_number)
);

-- SHOWS now references SCREENS instead of THEATERS
CREATE TABLE shows (
    id UUID PRIMARY KEY,
    movie_id UUID NOT NULL,
    screen_id UUID NOT NULL,
    show_time TIMESTAMP NOT NULL,
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_shows_movie FOREIGN KEY (movie_id) REFERENCES movies(id),
    CONSTRAINT fk_shows_screen FOREIGN KEY (screen_id) REFERENCES screens(id)
);

CREATE TABLE seats (
    id UUID PRIMARY KEY,
    show_id UUID NOT NULL,
    seat_number VARCHAR(10) NOT NULL,
    seat_type VARCHAR(50),
    row VARCHAR(5),
    status VARCHAR(50) DEFAULT 'AVAILABLE',
    price DECIMAL(10, 2),
    locked_by UUID,
    locked_at TIMESTAMP,
    locked_until TIMESTAMP,
    version INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_seats_show FOREIGN KEY (show_id) REFERENCES shows(id),
    CONSTRAINT fk_seats_locked_by FOREIGN KEY (locked_by) REFERENCES users(id),
    CONSTRAINT unique_seat_per_show UNIQUE(show_id, seat_number)
);

CREATE TABLE bookings (
    id UUID PRIMARY KEY,
    show_id UUID NOT NULL,
    user_id UUID NOT NULL,
  seat_id UUID NOT NULL,
    booking_time TIMESTAMP DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'PENDING',
    total_amount DECIMAL(10, 2),
    payment_id UUID,
  booked_at TIMESTAMP DEFAULT NOW(),
    idempotency_key VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_bookings_show FOREIGN KEY (show_id) REFERENCES shows(id),
  CONSTRAINT fk_bookings_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_bookings_seat FOREIGN KEY (seat_id) REFERENCES seats(id),
  CONSTRAINT unique_show_seat_booking UNIQUE(show_id, seat_id)
);

CREATE TABLE payments (
    id UUID PRIMARY KEY,
    booking_id UUID NOT NULL,
    amount DECIMAL(10, 2),
    payment_method VARCHAR(50),
    status VARCHAR(50) DEFAULT 'PENDING',
    transaction_id VARCHAR(255),
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT fk_payments_booking FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

-- Add FK for bookings.payment_id (after payments table exists)
ALTER TABLE bookings 
    ADD CONSTRAINT fk_bookings_payment 
    FOREIGN KEY (payment_id) REFERENCES payments(id);

-- Indexes for performance
CREATE INDEX idx_screens_theater ON screens(theater_id);
CREATE INDEX idx_shows_movie ON shows(movie_id);
CREATE INDEX idx_shows_screen ON shows(screen_id);
CREATE INDEX idx_seat_availability ON seats(show_id, status);
CREATE INDEX idx_seat_locked_until ON seats(status, locked_until);
CREATE INDEX idx_bookings_show_seat ON bookings(show_id, seat_id);
CREATE INDEX idx_booking_user ON bookings(user_id, booking_time DESC);
CREATE INDEX idx_booking_status ON bookings(status, created_at);
```

---

## 🔐 Concurrency & Table Locking

### ❓ Which Table Gets Locked During Concurrent Booking?

**Answer: SEATS table (row-level lock)**

When two users try to book the same seat simultaneously, the database acquires an **exclusive row-level lock** on the specific seat row in the `SEATS` table.

**Why SEATS and not others?**
- `SEATS` table is the ONLY table modified when a user selects/locks seats
- `BOOKINGS` table row is created **only after** payment succeeds (not during seat selection)
- `PAYMENTS` table row is created **only during/after** payment processing

**Lock Mechanism:**

```sql
-- User A's UPDATE acquires exclusive lock on SEATS row for seat A2
UPDATE seats 
SET status = 'LOCKED',
    locked_by = 'UserA'
WHERE id = 'A2' 
  AND status = 'AVAILABLE';
-- ✅ SUCCESS: Lock acquired, 1 row updated

-- User B's UPDATE attempts same seat
UPDATE seats 
SET status = 'LOCKED',
    locked_by = 'UserB'
WHERE id = 'A2' 
  AND status = 'AVAILABLE';
-- ❌ FAILS: Row S2 is already locked by UserA OR status is no longer AVAILABLE, 0 rows updated
```

**Lock Flow:**
```
BOOKINGS Table             PAYMENTS Table
(Created after seat lock)  (Created after booking)
     ↑                         ↑
     │                         │
     └─────────────┬───────────┘
          │ NOT involved yet
          │
        SEAT SELECTION HAPPENS
        🔒 SEATS Row Locked 🔒
          │
          ▼
        SEATS Table
        (Row-level lock on seat)
        status: AVAILABLE → LOCKED
```

**Lock Type:** 
- **Pessimistic**: `SELECT ... FOR UPDATE` (explicit database lock)
- **Optimistic**: Atomic `UPDATE WHERE status = 'AVAILABLE'` (CAS - Compare-And-Swap)

---

## 🔐 Concurrency Scenarios

### Scenario 1: Two Users Try to Book Same Seat

```
Timeline:
─────────────────────────────────────────────────────────────
Time        User A                    User B
─────────────────────────────────────────────────────────────
10:00:00    Clicks Seat A2           
10:00:01    Lock acquired ✅          
            (A2 status = LOCKED)      
                                     
10:00:02                             Clicks Seat A2
10:00:03                             Lock FAILED ❌
                                     (A2 already LOCKED)
                                     Shows: "Seat not available"
                                     
10:00:30    Payment SUCCESS          
            A2 status = BOOKED        
─────────────────────────────────────────────────────────────

DATABASE STATE:
┌───────┬────────┬────────────┬───────────┐
│ Time  │ A2     │ Locked By  │ Action    │
├───────┼────────┼────────────┼───────────┤
│ 10:00 │ AVAIL  │ NULL       │ Initial   │
│ 10:01 │ LOCKED │ UserA      │ A locks   │
│ 10:03 │ LOCKED │ UserA      │ B blocked │
│ 10:30 │ BOOKED │ NULL       │ A confirms│
└───────┴────────┴────────────┴───────────┘
```

**SQL that prevents double-booking:**
```sql
-- User A's lock attempt (SUCCESS)
UPDATE seats 
SET status = 'LOCKED', locked_by = 'UserA'
WHERE id = 'A2' 
  AND status = 'AVAILABLE'  -- ✅ Passes
RETURNING id;  -- Returns A2

-- User B's lock attempt (FAILS)
UPDATE seats 
SET status = 'LOCKED', locked_by = 'UserB'
WHERE id = 'A2' 
  AND status = 'AVAILABLE'  -- ❌ Fails (A2 is LOCKED)
RETURNING id;  -- Returns nothing
```

---

### Scenario 2: User Abandons Booking (Timeout)

```
Timeline:
─────────────────────────────────────────────────────
Time        User A                   System
─────────────────────────────────────────────────────
10:00:00    Locks Seat A2           
            (locked_until = 10:10)   
                                    
10:05:00    User closes browser      
                                     
10:10:00                            Auto-release job runs
                                    A2: LOCKED → AVAILABLE
                                    
10:15:00    User B locks A2 ✅       
─────────────────────────────────────────────────────
```

**Auto-release SQL (runs every minute):**
```sql
-- Find and release expired locks
UPDATE seats 
SET status = 'AVAILABLE',
    locked_by = NULL,
    locked_at = NULL,
    locked_until = NULL
WHERE status = 'LOCKED'
  AND locked_until < NOW();  -- Expired locks
```

---

## 📈 Performance Indexes Explained

### Index 1: Seat Availability Query

```sql
-- Without index (SLOW):
SELECT * FROM seats 
WHERE show_id = 'SH001' AND status = 'AVAILABLE';
-- Scans entire seats table (100,000 rows)

-- With index (FAST):
CREATE INDEX idx_seat_availability 
ON seats(show_id, status);
-- Only scans relevant show + status (100 rows)
```

**Visual:**
```
Without Index:                With Index:
Scan all seats                Jump directly to show + status
│                             │
▼                             ▼
SH001 | A1 | BOOKED           SH001 | AVAILABLE | [A1, B2, C3...]
SH001 | A2 | AVAILABLE  ✅    (Only 20 rows scanned)
SH001 | A3 | LOCKED           
SH002 | A1 | AVAILABLE        
SH002 | A2 | BOOKED           
... (100,000 rows)            
```

### Index 2: User Booking History

```sql
-- User wants to see their bookings (most recent first)
SELECT * FROM bookings 
WHERE user_id = 'U123' 
ORDER BY booking_time DESC
LIMIT 10;

-- Index optimizes this query
CREATE INDEX idx_booking_user 
ON bookings(user_id, booking_time DESC);
```

---

## 🎯 Key Takeaways for Interview

### 1. **Foreign Keys Ensure Data Integrity**
```
❌ Without FK: Can create booking with invalid show_id
✅ With FK: Database rejects invalid references
```

### 2. **Indexes Speed Up Queries**
```
Seat availability query:
Without index: 2000ms
With index: 5ms
```

### 3. **Status Transitions Are Critical**
```
AVAILABLE → LOCKED → BOOKED (Success)
AVAILABLE → LOCKED → AVAILABLE (Timeout/Failure)
BOOKED → CANCELLED (User cancels)
```

### 4. **Locking Prevents Race Conditions**
```
Two users can't book same seat simultaneously
Database row-level locks ensure atomicity
```

---

## 📝 Interview Talking Points

**When explaining schema:**
> "The seats table is the most critical. I've added `locked_by`, `locked_at`, and `locked_until` columns to implement temporary seat locking. When a user selects seats, we lock them for 10 minutes. If payment isn't completed, a scheduled job auto-releases them by checking `locked_until < NOW()`."

**When discussing concurrency:**
> "I'm using database row-level locking with `SELECT ... FOR UPDATE`. When User A tries to lock Seat A2, the database acquires an exclusive lock on that row. If User B tries to lock the same seat simultaneously, they'll wait until User A's transaction commits or rollback. The `status` column transition from AVAILABLE to LOCKED is atomic."

**When asked about scale:**
> "For high traffic, I'd partition the seats table by `show_id` since queries always filter by show. I'd also add a compound index on `(show_id, status)` for fast seat availability lookups. For really hot shows, we could use Redis for seat state with TTL-based auto-expiry."

---

**Good luck with your interview! 🎬**
