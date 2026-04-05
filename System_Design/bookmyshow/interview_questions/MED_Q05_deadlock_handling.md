# Question 5: User A books seats [1,2,3], User B books [3,2,1]. How to prevent deadlock?

## Difficulty Level: ⭐⭐⭐⭐ (Staff)

## Expected Answer Duration: 10-12 minutes

---

## The Problem:

```
DEADLOCK SCENARIO
═══════════════════════════════════════════════════════════

Timeline:
10:00:00.000 - User A: "Book seats 1, 2, 3"
10:00:00.001 - User B: "Book seats 3, 2, 1" (reverse order!)

Transaction A:                Transaction B:
BEGIN;                        BEGIN;
│                             │
├─ LOCK seat 1 ✅            │
│                             ├─ LOCK seat 3 ✅
│                             │
├─ LOCK seat 2 ✅            │
│                             ├─ LOCK seat 2 ⏳ WAITING...
│                             │
├─ LOCK seat 3 ⏳ WAITING... │
│                             │
│  💥 DEADLOCK DETECTED       │
│  PostgreSQL aborts one txn  │
│                             │
ROLLBACK (automatic)         COMMIT ✅

Result: User A gets error, User B succeeds
But which user gets error is random!
```

---

## ❌ Poor Answer (Mid-Level):

> "I'll use a timeout on the locks so they don't wait forever."

**Why this fails:**
- Doesn't prevent the deadlock, just detects it
- User experience is poor (random failures)
- Retry logic needed (complexity)
- Still wastes resources

---

## ✅ Excellent Answer (Architect Level):

### **Solution 1: Lock in Consistent Order (Recommended)**

```java
@Service
public class DeadlockFreeBookingService {
    
    @Transactional(isolation = Isolation.READ_COMMITTED, timeout = 5)
    public Booking bookSeats(BookingRequest request) {
        
        // CRITICAL: Sort seat IDs before locking!
        List<Long> seatIds = request.getSeatIds()
            .stream()
            .sorted()  // ← This prevents deadlock!
            .collect(Collectors.toList());
        
        // Now lock seats in ascending order
        List<SeatAvailability> seats = 
            seatRepository.findByShowIdAndSeatIdsForUpdate(
                request.getShowId(), 
                seatIds  // [1, 2, 3] for both users
            );
        
        // Validate all available
        validateSeatsAvailable(seats);
        
        // Reserve seats
        Booking booking = reserveSeats(request, seats);
        
        return booking;
    }
}
```

**Why This Works:**

```
User A: "Book seats 1, 2, 3"
  ↓ Sort: [1, 2, 3]
  ↓ Lock order: 1 → 2 → 3

User B: "Book seats 3, 2, 1"  
  ↓ Sort: [1, 2, 3]  ← Same order!
  ↓ Lock order: 1 → 2 → 3

Timeline:
═══════════════════════════════════════════════════════════
10:00:00.000 - User A locks seat 1 ✅
10:00:00.001 - User B tries seat 1 ⏳ WAITS (no deadlock!)
10:00:00.050 - User A locks seat 2 ✅
10:00:00.100 - User A locks seat 3 ✅
10:00:00.150 - User A commits, releases all locks
10:00:00.151 - User B acquires seat 1 ✅
10:00:00.200 - User B locks seat 2 ✅
10:00:00.250 - User B tries seat 3... UNAVAILABLE!
10:00:00.251 - User B rollback, returns "Seat 3 taken"

Result: No deadlock! Clear winner (User A)
```

---

### **Solution 2: Single Lock for Multiple Seats (Advisory Lock)**

```java
@Service
public class SingleLockBookingService {
    
    @Transactional
    public Booking bookSeats(BookingRequest request) {
        
        // Generate deterministic lock ID for this seat combination
        String lockKey = generateLockKey(
            request.getShowId(), 
            request.getSeatIds()
        );
        
        // Acquire advisory lock (PostgreSQL)
        Long lockId = hashLockKey(lockKey);
        
        jdbcTemplate.execute(
            "SELECT pg_advisory_xact_lock(" + lockId + ")"
        );
        // This lock is held until transaction ends
        // Other transactions trying same lock will wait
        
        // Now safely check and book seats
        List<SeatAvailability> seats = 
            seatRepository.findByShowIdAndSeatIds(
                request.getShowId(), 
                request.getSeatIds()
            );
        
        validateSeatsAvailable(seats);
        
        Booking booking = reserveSeats(request, seats);
        
        return booking;
    }
    
    private String generateLockKey(Long showId, List<Long> seatIds) {
        // Sort for consistency
        List<Long> sorted = seatIds.stream()
            .sorted()
            .collect(Collectors.toList());
        
        return "show:" + showId + ":seats:" + 
               sorted.stream()
                   .map(String::valueOf)
                   .collect(Collectors.joining(","));
    }
    
    private Long hashLockKey(String key) {
        // Convert to number (PostgreSQL advisory lock needs bigint)
        return (long) key.hashCode();
    }
}
```

**How Advisory Locks Work:**

```
Advisory Lock: show:123:seats:1,2,3
                       ↓
                Hash: 7482910482
                       ↓
              pg_advisory_xact_lock(7482910482)

User A: "Book seats 1,2,3"
  ↓ Lock key: show:123:seats:1,2,3 → Hash: 7482910482
  ↓ Acquire advisory lock ✅
  ↓ Book seats
  ↓ Commit (lock automatically released)

User B: "Book seats 3,2,1"
  ↓ Lock key: show:123:seats:1,2,3 → Hash: 7482910482 (same!)
  ↓ Try advisory lock ⏳ WAITS for User A
  ↓ User A commits, lock released
  ↓ User B acquires lock ✅
  ↓ Check seats → UNAVAILABLE
  ↓ Rollback

No deadlock! Users serialize through single lock
```

---

### **Solution 3: Deadlock Detection + Retry (Fallback)**

```java
@Service
public class DeadlockRetryBookingService {
    
    private static final int MAX_RETRIES = 3;
    private static final long INITIAL_BACKOFF_MS = 50;
    
    public Booking bookSeatsWithRetry(BookingRequest request) {
        
        int attempt = 0;
        
        while (attempt < MAX_RETRIES) {
            try {
                return bookSeats(request);
                
            } catch (CannotAcquireLockException e) {
                // Deadlock detected by database
                attempt++;
                
                if (attempt >= MAX_RETRIES) {
                    throw new BookingException(
                        "Unable to complete booking after " + 
                        MAX_RETRIES + " attempts. Please try again."
                    );
                }
                
                // Exponential backoff with jitter
                long backoff = INITIAL_BACKOFF_MS * (1L << attempt);
                long jitter = ThreadLocalRandom.current()
                    .nextLong(0, backoff / 2);
                
                try {
                    Thread.sleep(backoff + jitter);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    throw new BookingException("Interrupted during retry");
                }
                
                log.info("Retrying booking after deadlock. Attempt: {}", attempt);
            }
        }
        
        throw new BookingException("Max retries exceeded");
    }
    
    @Transactional
    private Booking bookSeats(BookingRequest request) {
        // Original booking logic (might deadlock)
        List<SeatAvailability> seats = 
            seatRepository.findByShowIdAndSeatIdsForUpdate(
                request.getShowId(), 
                request.getSeatIds()
                // NOT sorted - might deadlock
            );
        
        validateSeatsAvailable(seats);
        return reserveSeats(request, seats);
    }
}
```

**Retry Strategy Visualization:**

```
Attempt 1: Deadlock detected → Wait 50ms + jitter
Attempt 2: Deadlock detected → Wait 100ms + jitter
Attempt 3: Success! ✅

Backoff Times:
═══════════════════════════════════════════════════════════
Attempt 1: 50ms + [0-25ms jitter]
Attempt 2: 100ms + [0-50ms jitter]
Attempt 3: 200ms + [0-100ms jitter]

Why Jitter?
- Prevents "thundering herd"
- If 10 users deadlock simultaneously
- Without jitter: all retry at exact same time → deadlock again!
- With jitter: retries spread out → less likely to collide
```

---

## 📊 Comparison of Approaches:

```
┌──────────────────────┬─────────────┬─────────────┬──────────────┐
│     Approach         │ Prevents    │ Performance │  Complexity  │
│                      │ Deadlock    │             │              │
├──────────────────────┼─────────────┼─────────────┼──────────────┤
│ Lock in Order        │ ✅ Yes      │ High        │ Low ⭐       │
│ (Sort seat IDs)      │ 100%        │ 10k req/s   │              │
├──────────────────────┼─────────────┼─────────────┼──────────────┤
│ Advisory Lock        │ ✅ Yes      │ Medium      │ Medium ⭐⭐  │
│ (Single lock)        │ 100%        │ 5k req/s    │              │
├──────────────────────┼─────────────┼─────────────┼──────────────┤
│ Deadlock Retry       │ ⚠️ Detects  │ Low         │ High ⭐⭐⭐  │
│ (Exponential backoff)│ only        │ 2k req/s    │              │
└──────────────────────┴─────────────┴─────────────┴──────────────┘

Recommendation: Lock in Order (Sort) ✅
- Simplest implementation
- Best performance
- Zero deadlocks
- No retry logic needed
```

---

## 🔥 Advanced: Multi-Show Bookings

**Problem:** User books seats from multiple shows simultaneously

```java
User books:
- Show 123, Seats [5, 10]
- Show 456, Seats [2, 8]

Without ordering: Can deadlock with another user booking:
- Show 456, Seats [8, 2]  ← Same show, reverse order
- Show 123, Seats [10, 5] ← Same show, reverse order
```

**Solution: Two-level sorting**

```java
@Transactional
public List<Booking> bookMultipleShows(
        List<BookingRequest> requests) {
    
    // Level 1: Sort by show_id
    List<BookingRequest> sortedRequests = requests.stream()
        .sorted(Comparator.comparing(BookingRequest::getShowId))
        .collect(Collectors.toList());
    
    List<Booking> bookings = new ArrayList<>();
    
    for (BookingRequest request : sortedRequests) {
        // Level 2: Sort seat_ids within each show
        List<Long> sortedSeatIds = request.getSeatIds()
            .stream()
            .sorted()
            .collect(Collectors.toList());
        
        request.setSeatIds(sortedSeatIds);
        
        Booking booking = bookSeats(request);
        bookings.add(booking);
    }
    
    return bookings;
}
```

**Lock Acquisition Order:**

```
User A: Show 123 [5,10], Show 456 [2,8]
  ↓ Sort shows: [123, 456]
  ↓ Sort seats: [5,10], [2,8]
  ↓ Lock order: Show123-Seat5 → Show123-Seat10 → 
                 Show456-Seat2 → Show456-Seat8

User B: Show 456 [8,2], Show 123 [10,5]
  ↓ Sort shows: [123, 456]  ← Same order!
  ↓ Sort seats: [5,10], [2,8]  ← Same order!
  ↓ Lock order: Show123-Seat5 → Show123-Seat10 → 
                 Show456-Seat2 → Show456-Seat8  ← Same order!

Result: User B waits for User A, no deadlock ✅
```

---

## 🎯 Database Configuration

### **PostgreSQL Deadlock Detection:**

```sql
-- View current deadlock_timeout setting
SHOW deadlock_timeout;
-- Default: 1000ms (1 second)

-- Adjust if needed (application-level)
SET deadlock_timeout = 500;  -- Detect faster

-- Log deadlocks for monitoring
SET log_lock_waits = on;
SET deadlock_timeout = 200;

-- Check for deadlocks in logs
SELECT * FROM pg_stat_database_conflicts;
```

### **Lock Timeout (Prevent Infinite Wait):**

```java
@Transactional(timeout = 5)  // 5 seconds max
public Booking bookSeats(BookingRequest request) {
    // If lock not acquired within 5 seconds, rollback
    // Better than waiting forever
}
```

```sql
-- Or at database level
SET lock_timeout = 5000;  -- 5 seconds
```

---

## 📈 Monitoring Deadlocks

```java
@Component
public class DeadlockMonitor {
    
    private final MeterRegistry meterRegistry;
    
    @Around("@annotation(Transactional)")
    public Object monitorDeadlocks(ProceedingJoinPoint joinPoint) 
            throws Throwable {
        
        try {
            return joinPoint.proceed();
            
        } catch (CannotAcquireLockException e) {
            // Increment deadlock counter
            meterRegistry.counter("database.deadlocks",
                "method", joinPoint.getSignature().getName()
            ).increment();
            
            // Log details
            log.error("Deadlock detected in {}", 
                joinPoint.getSignature().getName(), e);
            
            throw e;
        }
    }
}
```

**Alert if deadlock rate > 0.1%:**

```yaml
alerts:
  - name: HighDeadlockRate
    condition: rate(database_deadlocks[5m]) > 10
    severity: warning
    message: "Deadlock rate exceeding 0.1% (10 per 1000 txns)"
    action:
      - notify: oncall
      - runbook: https://wiki/deadlock-investigation
```

---

## 💡 Key Takeaway for Interview:

**Perfect Answer:**

> "To prevent deadlocks when booking multiple seats, I'd **sort seat IDs before acquiring locks**:
> 
> ```java
> List<Long> sortedSeatIds = seatIds.stream()
>     .sorted()  // Always lock in ascending order
>     .collect(Collectors.toList());
> 
> // Then lock in order
> findByIdsForUpdate(sortedSeatIds);
> ```
> 
> **Why this works:**
> - User A wants seats [1,2,3] → locks 1, 2, 3
> - User B wants seats [3,2,1] → sorts to [1,2,3] → locks 1, 2, 3
> - Both acquire locks in same order → no circular wait → no deadlock
> 
> **For multi-show bookings:**
> - Sort by show_id first
> - Then sort seat_ids within each show
> - Guarantees consistent global lock order
> 
> **Alternative (if sorting not possible):**
> - PostgreSQL advisory locks (single lock per seat group)
> - Serializes all bookings for those seats
> - Trade-off: Lower throughput but zero deadlocks
> 
> **Fallback:**
> - Detect deadlocks (1-second timeout)
> - Retry with exponential backoff + jitter
> - Log and monitor deadlock rate
> - Alert if >0.1% of transactions
> 
> **Real-world metric:**
> - With sorting: 0% deadlock rate ✅
> - Without sorting: 5-10% deadlock rate at peak ❌
> - Performance impact of sorting: negligible (<1ms)"

---

## 🔬 Testing Deadlocks

```java
@SpringBootTest
class DeadlockTest {
    
    @Test
    void testConcurrentBooking_NoDeadlock() throws Exception {
        // Arrange
        Long showId = 123L;
        List<Long> seatsA = List.of(1L, 2L, 3L);
        List<Long> seatsB = List.of(3L, 2L, 1L);  // Reverse!
        
        CountDownLatch latch = new CountDownLatch(2);
        AtomicInteger successCount = new AtomicInteger(0);
        AtomicInteger failureCount = new AtomicInteger(0);
        
        // Act: Start 2 threads booking same seats
        CompletableFuture<Void> userA = CompletableFuture.runAsync(() -> {
            try {
                bookingService.bookSeats(
                    new BookingRequest(showId, seatsA, "userA")
                );
                successCount.incrementAndGet();
            } catch (Exception e) {
                failureCount.incrementAndGet();
            } finally {
                latch.countDown();
            }
        });
        
        CompletableFuture<Void> userB = CompletableFuture.runAsync(() -> {
            try {
                bookingService.bookSeats(
                    new BookingRequest(showId, seatsB, "userB")
                );
                successCount.incrementAndGet();
            } catch (Exception e) {
                failureCount.incrementAndGet();
            } finally {
                latch.countDown();
            }
        });
        
        // Wait for both
        latch.await(10, TimeUnit.SECONDS);
        
        // Assert: Exactly one succeeds (no deadlock, deterministic)
        assertThat(successCount.get()).isEqualTo(1);
        assertThat(failureCount.get()).isEqualTo(1);
        
        // Verify no deadlock exception
        assertThat(failureCount.get())
            .as("Should fail due to seat taken, not deadlock")
            .isEqualTo(1);
    }
}
```

This demonstrates Staff-level concurrency expertise! 🎯
