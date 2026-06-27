# Movie Ticket Booking - Interview Approach (10 YOE)

## 🎯 Time Allocation (45-60 min)
- Requirements: 5-7 min
- High-Level Design: 8-10 min
- Core Classes: 15-20 min
- Concurrency & Edge Cases: 10-15 min
- Follow-ups: 5-10 min

---

## Phase 1: Requirements Clarification (5-7 min)

### Questions to Ask (Shows Senior-Level Thinking)

**Scale & Performance:**
- "How many concurrent users? Thousands or millions?"
- "What's the expected TPS for booking operations?"
- "Is this single city or multi-city deployment?"
- "Read-heavy or write-heavy? (Browsing vs Booking ratio)"

**Business Logic:**
- "How long should we hold seats during booking? 10 min?"
- "What happens on payment failure? Auto-release?"
- "Do we support partial bookings or all-or-nothing?"
- "Can users cancel bookings? Full/partial refund?"

**Technical Constraints:**
- "Should this be thread-safe for concurrent bookings?"
- "Do we need ACID guarantees?"
- "Any preference: microservices vs monolith?"
- "Database choice: SQL vs NoSQL?"

---

## Phase 2: High-Level Architecture (8-10 min)

### Draw This First

```
┌───────────────────────────────────────────────────────┐
│                    API Gateway                        │
└─────────────┬─────────────────────────────────────────┘
              │
    ┌─────────┴──────────┐
    │                    │
┌───▼─────────────┐  ┌──▼───────────────┐
│ Catalog Service │  │ Booking Service  │
│ (Read-Heavy)    │  │ (Write-Heavy)    │
│                 │  │                  │
│ - Movies        │  │ - Lock Seats     │
│ - Theaters      │  │ - Process Payment│
│ - Shows         │  │ - Confirm Booking│
└─────────────────┘  └───┬──────────────┘
                         │
              ┌──────────┴────────────┐
              │                       │
     ┌────────▼────────┐   ┌─────────▼────────┐
     │ Inventory DB    │   │  Payment Gateway │
     │ (Seat Locking)  │   │    (External)    │
     └─────────────────┘   └──────────────────┘
```

### Key Design Decisions to Mention

1. **Separation of Concerns:**
   - Catalog Service: Browse movies/shows (can be cached heavily)
   - Booking Service: Handle transactions (needs strong consistency)

2. **Seat Locking Strategy:**
   - "I'll use **pessimistic locking** with TTL (10 min expiry)"
   - "Prevents double-booking race conditions"
   - "Auto-release if payment not completed"

3. **Transaction Management:**
   - Lock seats → Process payment → Confirm booking
   - Rollback seats if payment fails
   - Idempotency for retries

---

## Phase 3: Core Class Design (15-20 min)

### Start with Critical Path: Booking Flow

```java
// 1. Main Service (Orchestrator)
public class BookingService {
    private final SeatInventory seatInventory;
    private final PaymentService paymentService;
    private final BookingRepository bookingRepository;
    
    /**
     * Critical method - explain concurrency handling
     */
    @Transactional
    public Booking bookTickets(Show show, List<Seat> seats, User user) {
        // Step 1: Lock seats (with TTL)
        if (!seatInventory.lockSeats(show.getId(), seats, user.getId(), Duration.ofMinutes(10))) {
            throw new SeatsNotAvailableException();
        }
        
        try {
            // Step 2: Process payment
            Payment payment = paymentService.processPayment(user, calculateTotal(seats));
            
            // Step 3: Confirm booking
            Booking booking = createBooking(show, seats, user, payment);
            bookingRepository.save(booking);
            
            // Step 4: Mark seats as booked (release lock, mark BOOKED)
            seatInventory.confirmSeats(show.getId(), seats);
            
            return booking;
            
        } catch (PaymentException e) {
            // Rollback: Release locked seats
            seatInventory.releaseSeats(show.getId(), seats);
            throw new BookingFailedException("Payment failed", e);
        }
    }
}

// 2. Seat Inventory (Concurrency Critical)
public class SeatInventory {
    // Using Redis or Database with row-level locking
    private final ConcurrentHashMap<String, SeatLock> seatLocks;
    
    /**
     * Thread-safe seat locking
     * Key insight: Use database row-level lock or Redis SETNX
     */
    public synchronized boolean lockSeats(
            String showId, 
            List<Seat> seats, 
            String userId, 
            Duration ttl) {
        
        String lockKey = showId + ":" + userId;
        
        // Check if all seats are available
        for (Seat seat : seats) {
            if (!isSeatAvailable(showId, seat.getId())) {
                return false;
            }
        }
        
        // Lock all seats atomically
        for (Seat seat : seats) {
            SeatLock lock = new SeatLock(userId, Instant.now().plus(ttl));
            seatLocks.put(getLockKey(showId, seat.getId()), lock);
            updateSeatStatus(showId, seat.getId(), SeatStatus.LOCKED);
        }
        
        // Schedule auto-release after TTL
        scheduleAutoRelease(showId, seats, ttl);
        
        return true;
    }
    
    private boolean isSeatAvailable(String showId, String seatId) {
        SeatLock lock = seatLocks.get(getLockKey(showId, seatId));
        
        // Available if no lock OR lock expired
        return lock == null || lock.getExpiryTime().isBefore(Instant.now());
    }
}

// 3. Core Entities
public class Show {
    private final String id;
    private final Movie movie;
    private final Theater theater;
    private final LocalDateTime showTime;
    private final Map<String, Seat> seats;
    
    public List<Seat> getAvailableSeats() {
        return seats.values().stream()
                .filter(seat -> seat.getStatus() == SeatStatus.AVAILABLE)
                .collect(Collectors.toList());
    }
}

public class Seat {
    private final String id;
    private final SeatType type; // REGULAR, PREMIUM, VIP
    private final String row;
    private final int number;
    private SeatStatus status; // AVAILABLE, LOCKED, BOOKED
    private double price;
    
    // Thread-safe status transition
    public synchronized boolean updateStatus(SeatStatus from, SeatStatus to) {
        if (this.status == from) {
            this.status = to;
            return true;
        }
        return false;
    }
}

public enum SeatStatus {
    AVAILABLE,
    LOCKED,    // Temporarily held during booking
    BOOKED     // Confirmed booking
}

public class Booking {
    private final String id;
    private final Show show;
    private final List<Seat> seats;
    private final User user;
    private final Payment payment;
    private final LocalDateTime bookingTime;
    private BookingStatus status;
}

public enum BookingStatus {
    PENDING,
    CONFIRMED,
    CANCELLED,
    EXPIRED
}
```

---

## Phase 4: Concurrency & Edge Cases (10-15 min)

### Critical Scenarios to Discuss

#### 1. **Race Condition: Two Users Booking Same Seat**

```java
// BAD: Race condition possible
if (seat.isAvailable()) {
    // Another thread could book here!
    seat.book();
}

// GOOD: Atomic operation
public synchronized boolean lockSeat(Seat seat) {
    return seat.updateStatus(SeatStatus.AVAILABLE, SeatStatus.LOCKED);
}
```

**Solution Options:**
- Database: `SELECT ... FOR UPDATE` (row-level lock)
- Redis: `SETNX` with expiry
- Application: `synchronized` blocks or `ReentrantLock`

#### 2. **Payment Failure After Seat Lock**

```java
try {
    lockSeats();
    processPayment(); // Fails here
    confirmBooking();
} catch (PaymentException e) {
    releaseSeats(); // Critical: Must rollback
    throw new BookingFailedException();
}
```

#### 3. **Seat Lock Expiry (User Abandons Booking)**

```java
// Schedule auto-release after 10 minutes
ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);

scheduler.schedule(() -> {
    if (seat.getStatus() == SeatStatus.LOCKED) {
        seat.updateStatus(SeatStatus.LOCKED, SeatStatus.AVAILABLE);
    }
}, 10, TimeUnit.MINUTES);
```

#### 4. **Idempotency (Retry on Failure)**

```java
@Transactional
public Booking bookTickets(String idempotencyKey, ...) {
    // Check if already processed
    Booking existing = bookingRepository.findByIdempotencyKey(idempotencyKey);
    if (existing != null) {
        return existing; // Return cached result
    }
    
    // Process booking...
}
```

---

## Phase 5: Follow-Up Questions & Scaling (5-10 min)

### Expected Follow-ups

#### Q1: "How would you scale this to 10M users?"

**Answer:**
1. **Database Sharding:**
   - Shard by `show_id` (hot shows on separate shards)
   - Read replicas for catalog queries

2. **Caching:**
   - Redis for show/seat availability (invalidate on booking)
   - CDN for movie posters, metadata

3. **Load Balancing:**
   - Multiple booking service instances
   - Use message queue for async operations (notifications, analytics)

4. **Database Optimization:**
   ```sql
   -- Index for fast seat lookup
   CREATE INDEX idx_seat_status ON seats(show_id, status);
   
   -- Partition by show date
   PARTITION BY RANGE (show_time);
   ```

#### Q2: "How do you handle show with 1000 seats and 10,000 users trying to book?"

**Answer:**
1. **Queue System:**
   - Put users in virtual queue (like IRCTC/BookMyShow)
   - Process bookings in FIFO order
   - Show position in queue

2. **Rate Limiting:**
   - Limit booking attempts per user per minute
   - Prevent bot attacks

3. **Optimistic UI:**
   - Show tentative seat selection
   - Confirm after lock acquired

#### Q3: "How do you ensure data consistency across microservices?"

**Answer:**
1. **Saga Pattern:**
   - Choreography: Event-driven (SeatLocked → PaymentProcessed → BookingConfirmed)
   - Orchestration: Central coordinator

2. **Two-Phase Commit (2PC):**
   - Prepare phase: Lock resources
   - Commit phase: Finalize or rollback

3. **Eventual Consistency:**
   - For non-critical operations (notifications, analytics)

---

## Key Design Patterns to Mention

| Pattern | Where Used | Why |
|---------|------------|-----|
| **Singleton** | BookingService | Single instance managing bookings |
| **Factory** | Creating Seat types (Regular/Premium/VIP) | Flexible seat creation |
| **Strategy** | Payment methods (Credit/Debit/UPI/Wallet) | Pluggable payment strategies |
| **Observer** | Booking notifications | Notify user, send email/SMS |
| **State** | Booking status transitions | Manage booking lifecycle |
| **Repository** | Data access layer | Abstraction over database |

---

## Database Schema (Mention if Asked)

```sql
-- Shows table
CREATE TABLE shows (
    id UUID PRIMARY KEY,
    movie_id UUID REFERENCES movies(id),
    theater_id UUID REFERENCES theaters(id),
    show_time TIMESTAMP,
    status VARCHAR(20)
);

-- Seats table (critical for concurrency)
CREATE TABLE seats (
    id UUID PRIMARY KEY,
    show_id UUID REFERENCES shows(id),
    seat_number VARCHAR(10),
    seat_type VARCHAR(20),
    status VARCHAR(20), -- AVAILABLE, LOCKED, BOOKED
    price DECIMAL(10,2),
    locked_by UUID REFERENCES users(id),
    locked_at TIMESTAMP,
    locked_until TIMESTAMP,
    version INT -- Optimistic locking
);

-- Bookings table
CREATE TABLE bookings (
    id UUID PRIMARY KEY,
    show_id UUID REFERENCES shows(id),
    user_id UUID REFERENCES users(id),
    booking_time TIMESTAMP,
    status VARCHAR(20),
    total_amount DECIMAL(10,2),
    payment_id UUID,
    idempotency_key VARCHAR(100) UNIQUE
);

-- Indexes for performance
CREATE INDEX idx_seat_availability ON seats(show_id, status);
CREATE INDEX idx_booking_user ON bookings(user_id, booking_time DESC);
CREATE INDEX idx_show_time ON shows(show_time);
```

---

## Red Flags to Avoid

❌ **Don't:**
- Forget thread safety / concurrency handling
- Ignore payment failure rollback
- Over-engineer with complex patterns
- Skip edge cases (double booking, timeouts)
- Hardcode seat lock duration

✅ **Do:**
- Start with core booking flow
- Discuss trade-offs (pessimistic vs optimistic locking)
- Mention real-world systems (BookMyShow, Ticketmaster)
- Show knowledge of distributed systems
- Ask clarifying questions upfront

---

## Sample Talking Points (Copy-Paste Ready)

**When explaining locking:**
> "I'll use pessimistic locking with a 10-minute TTL. When a user selects seats, we immediately lock them in the database using `SELECT ... FOR UPDATE`. This prevents race conditions where two users try to book the same seat. If payment isn't completed within 10 minutes, we auto-release the seats using a scheduled job."

**When discussing scalability:**
> "For scale, I'd shard the database by `show_id` since hot shows will have high contention. We can use Redis for caching seat availability with aggressive invalidation on bookings. For the booking service itself, we'd have multiple stateless instances behind a load balancer, using a message queue for async operations like sending confirmation emails."

**When asked about failures:**
> "Payment failures are handled with transaction rollback. We wrap the entire booking flow in a database transaction, so if payment fails, seat locks are automatically released. We also use idempotency keys to handle retries - if the user clicks 'Book' twice, we detect the duplicate request and return the original booking."

---

## Time Management Cheat Sheet

| Time | Phase | What to Cover |
|------|-------|--------------|
| 0-5 min | Requirements | Ask 5-6 clarifying questions |
| 5-15 min | Architecture | Draw high-level diagram, explain flow |
| 15-35 min | Class Design | Core classes: Booking, Seat, Show, Inventory |
| 35-45 min | Concurrency | Race conditions, locking, transactions |
| 45-60 min | Follow-ups | Scaling, edge cases, DB schema |

---

## Final Checklist Before Interview

- [ ] Understand seat locking with TTL
- [ ] Know difference between pessimistic vs optimistic locking
- [ ] Understand transaction rollback on payment failure
- [ ] Can explain race condition prevention
- [ ] Know how to scale to millions of users
- [ ] Prepared to discuss real-world systems (BookMyShow)
- [ ] Can draw architecture diagram in 5 minutes
- [ ] Know key database indexes needed

---

**Good luck! 🎬🎟️**
