# Question 1: How do you prevent double-booking of the same seat when two users click simultaneously?

## Difficulty Level: ⭐⭐⭐ (Senior)

## Expected Answer Duration: 5-7 minutes

---

## ❌ Poor Answer (Junior Level):

> "I would check if the seat is available in the database, and then update it to booked."

**Why this fails**: No mention of race conditions, transactions, or locking mechanisms.

---

## ✅ Good Answer (Senior Level):

### **Approach 1: Pessimistic Locking (Recommended for BookMyShow)**

```sql
-- Transaction with row-level lock
BEGIN TRANSACTION;

-- Lock the specific seat row
SELECT * FROM seat_availability 
WHERE show_id = 123 AND seat_id = 5 
FOR UPDATE;

-- At this point, other users trying to lock the same row will WAIT

-- Check if available
IF status = 'AVAILABLE' THEN
    -- Reserve the seat
    UPDATE seat_availability 
    SET status = 'RESERVED',
        reserved_until = NOW() + INTERVAL '15 minutes',
        booking_id = 999
    WHERE show_id = 123 AND seat_id = 5;
    
    -- Create booking record
    INSERT INTO booking (...) VALUES (...);
    
    COMMIT;
ELSE
    ROLLBACK;
    RETURN 'Seat already taken';
END IF;
```

**Why this works:**
1. `FOR UPDATE` acquires an **exclusive row-level lock**
2. User B trying to book the same seat will **block** until User A commits/rolls back
3. When User B's turn comes, they see the updated status and get rejected
4. **No dirty reads, no lost updates**

---

### **Approach 2: Optimistic Locking (For higher concurrency)**

```java
@Entity
public class SeatAvailability {
    @Id
    private Long id;
    
    @Version  // JPA optimistic lock
    private Long version;
    
    private String status;
}

// Service code
public Booking bookSeat(Long showId, Long seatId) {
    SeatAvailability seat = seatRepo.findById(seatId);
    
    if (!seat.isAvailable()) {
        throw new SeatNotAvailableException();
    }
    
    seat.setStatus("RESERVED");
    
    try {
        seatRepo.save(seat);  // Version check happens here
    } catch (OptimisticLockException e) {
        // Retry or return error
        throw new ConcurrentModificationException("Seat taken by another user");
    }
}
```

**SQL equivalent:**
```sql
UPDATE seat_availability 
SET status = 'RESERVED', 
    version = version + 1
WHERE show_id = 123 
  AND seat_id = 5 
  AND status = 'AVAILABLE'
  AND version = 10;  -- Only succeeds if version unchanged

-- Returns 0 rows affected if another user modified it
```

---

### **Comparison Table:**

| Aspect | Pessimistic Locking | Optimistic Locking |
|--------|-------------------|-------------------|
| **Lock Timing** | Acquire before read | Check on write |
| **Concurrency** | Lower (blocks waiting) | Higher (no waiting) |
| **Retry Logic** | Not needed | Required |
| **Best For** | High contention (popular shows) | Low contention |
| **Deadlock Risk** | Higher | Lower |
| **BookMyShow Choice** | ✅ Pessimistic (seat booking is high contention) | Better for inventory with less contention |

---

## 🚀 Advanced Follow-up Points:

### 1. **Distributed Lock (Multi-DC Scenario)**

If running across multiple data centers:

```java
// Use Redis distributed lock
try (RedisLock lock = redisLock.acquire("seat:123:5", 5_000)) {
    if (lock.isAcquired()) {
        // Check and book seat
        bookSeat(123, 5);
    } else {
        throw new LockAcquisitionException();
    }
}
```

**Tools**: Redisson (Java), Redlock algorithm

---

### 2. **Database Isolation Levels**

```
READ_COMMITTED + FOR UPDATE ✅ (Production choice)
- Prevents dirty reads
- Row lock prevents concurrent modifications
- 10k bookings/sec throughput

SERIALIZABLE ❌ (Overkill)
- Also works but 5x slower
- 2k bookings/sec throughput
- Higher deadlock rate (5-10%)
```

**Interview Answer:**
> "I'd use READ_COMMITTED isolation level with explicit FOR UPDATE locks. SERIALIZABLE is overkill for this use case—we're locking specific rows, not doing range queries, so the extra overhead isn't justified."

---

### 3. **What if Lock Times Out?**

```java
@Transactional(timeout = 5) // 5 seconds max
public Booking bookSeat(Long seatId) {
    try {
        // Lock with timeout
        seat = seatRepo.findByIdForUpdate(seatId, Duration.ofSeconds(3));
    } catch (LockTimeoutException e) {
        throw new SeatContentionException(
            "Too many users trying to book this seat. Please try again."
        );
    }
}
```

---

### 4. **Cache Invalidation After Booking**

```java
public Booking bookSeat(Long showId, Long seatId) {
    // ... booking logic ...
    
    // After commit:
    // 1. Invalidate cache
    redisCache.delete("show:" + showId + ":seats");
    
    // 2. Publish real-time update
    redisPublisher.publish("show:" + showId + ":update", 
        new SeatUpdateEvent(seatId, "BOOKED"));
}
```

---

## 🔥 Common Mistakes to Avoid:

| Mistake | Why It's Wrong |
|---------|---------------|
| No transaction | Race condition: Both users see "AVAILABLE" |
| SELECT without FOR UPDATE | Both users pass availability check |
| Application-level locking | Doesn't work across multiple app instances |
| Not handling lock timeout | User waits forever, bad UX |
| Forgot to release lock on exception | Deadlock or seat stuck as reserved |

---

## 🎯 Red Flags (What NOT to Say):

❌ "I'll use a mutex in Java"  
→ Doesn't work across multiple servers

❌ "I'll add a 'lock' column in the database"  
→ Reinventing pessimistic locking poorly

❌ "I'll make the user wait 10 seconds and retry"  
→ Band-aid solution, doesn't solve race condition

---

## 📊 Production Metrics:

```
Scenario: Avengers movie premiere, 1000 users trying to book Seat 5

Pessimistic Locking:
- User 1: Gets lock, books seat → 50ms
- User 2: Waits for lock, sees taken → 55ms
- User 3-1000: Sequential processing → 50-100ms each
- Result: 1 success, 999 immediate failures (good UX)

No Locking (Broken):
- All 1000 users see "AVAILABLE"
- All 1000 try to book
- Database detects conflicts at commit
- 999 rollbacks, but 10-50 might succeed! 💥
- Result: Up to 50 double-bookings (lawsuit territory)
```

---

## 💡 Key Takeaway for Interview:

**What interviewer wants to hear:**

1. ✅ **Understand the race condition** - Explain the problem clearly
2. ✅ **Database locking** - FOR UPDATE, isolation levels
3. ✅ **Trade-offs** - Pessimistic vs Optimistic
4. ✅ **Production concerns** - Timeouts, deadlocks, retry logic
5. ✅ **Scale thinking** - Distributed locks, cache invalidation

**Sample closing statement:**
> "In production at BookMyShow scale, I'd use PostgreSQL's row-level locking with FOR UPDATE in a READ_COMMITTED transaction. This prevents double-bookings with minimal deadlock risk. For extremely popular shows, I'd add a Redis-based distributed lock layer and implement exponential backoff retries for users who hit lock timeouts."

---

## 🧪 Code Implementation (Full Example):

```java
@Service
public class BookingService {
    
    @Transactional(isolation = Isolation.READ_COMMITTED, timeout = 5)
    public BookingResponse bookSeats(BookingRequest request) {
        
        // Step 1: Acquire locks on all requested seats
        List<SeatAvailability> seats = seatRepository.findByShowIdAndSeatIdsForUpdate(
            request.getShowId(), 
            request.getSeatIds()
        );
        
        // Step 2: Validate all seats are available
        List<SeatAvailability> unavailable = seats.stream()
            .filter(s -> s.getStatus() != SeatStatus.AVAILABLE)
            .collect(Collectors.toList());
        
        if (!unavailable.isEmpty()) {
            throw new SeatNotAvailableException(
                "Seats already taken: " + unavailable.stream()
                    .map(SeatAvailability::getSeatNumber)
                    .collect(Collectors.toList())
            );
        }
        
        // Step 3: Create booking (PENDING status)
        Booking booking = Booking.builder()
            .userId(request.getUserId())
            .showId(request.getShowId())
            .status(BookingStatus.PENDING)
            .expiresAt(LocalDateTime.now().plusMinutes(15))
            .totalPrice(calculatePrice(seats))
            .build();
        
        bookingRepository.save(booking);
        
        // Step 4: Reserve seats
        seats.forEach(seat -> {
            seat.setStatus(SeatStatus.RESERVED);
            seat.setReservedUntil(booking.getExpiresAt());
            seat.setBookingId(booking.getId());
        });
        
        seatRepository.saveAll(seats);
        
        // Step 5: Update show available count
        showRepository.decrementAvailableSeats(request.getShowId(), seats.size());
        
        // Transaction commits here, locks released
        
        // Step 6: Post-commit actions (async)
        applicationEventPublisher.publishEvent(
            new BookingCreatedEvent(booking.getId(), request.getShowId())
        );
        
        return BookingResponse.from(booking);
    }
}

@Repository
public interface SeatAvailabilityRepository extends JpaRepository<SeatAvailability, Long> {
    
    @Query("SELECT s FROM SeatAvailability s WHERE s.showId = ?1 AND s.seatId IN ?2 FOR UPDATE")
    List<SeatAvailability> findByShowIdAndSeatIdsForUpdate(Long showId, List<Long> seatIds);
}
```

This answer demonstrates 15+ years of experience with production systems! 🎯
