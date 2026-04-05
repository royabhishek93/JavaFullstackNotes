# Q29: Denormalization - When to denormalize for performance?

### Difficulty: ⭐⭐⭐ (Senior)

### ✅ Solution: Strategic Denormalization

**Example: `available_seats` in `show` table**

```sql
-- NORMALIZED (Poor Performance)
CREATE TABLE show (
    id BIGINT PRIMARY KEY,
    movie_id BIGINT,
    screen_id BIGINT,
    total_seats INT
    -- No available_seats
);

-- To get available seats:
SELECT COUNT(*) 
FROM seat_availability 
WHERE show_id = 123 
  AND status = 'AVAILABLE';
-- ↑ Full table scan on 500 rows per show
-- 10k shows × 500 rows = 5M rows scanned
-- Query time: 500ms ❌


-- DENORMALIZED (Fast)
CREATE TABLE show (
    id BIGINT PRIMARY KEY,
    movie_id BIGINT,
    screen_id BIGINT,
    total_seats INT,
    available_seats INT  -- ← Denormalized!
);

-- To get available seats:
SELECT available_seats 
FROM show 
WHERE id = 123;
-- ↑ Index lookup
-- Query time: 5ms ✅
```

**Maintaining Consistency:**

```java
@Service
public class SeatReservationService {
    
    @Transactional
    public void reserveSeats(Long showId, List<Long> seatIds) {
        
        // Step 1: Update seat_availability
        seatRepository.updateStatus(showId, seatIds, SeatStatus.RESERVED);
        
        // Step 2: Decrement available_seats (denormalized field)
        int count = seatIds.size();
        
        int updated = showRepository.decrementAvailableSeats(showId, count);
        
        if (updated == 0) {
            throw new ConcurrentModificationException(
                "Failed to update available_seats"
            );
        }
    }
}

// Repository method
@Query("UPDATE show SET available_seats = available_seats - :count " +
       "WHERE id = :showId AND available_seats >= :count")
int decrementAvailableSeats(
    @Param("showId") Long showId,
    @Param("count") int count
);
```

**When to Denormalize:**

```
✅ DENORMALIZE WHEN:
═══════════════════════════════════════════════════════════
1. Read-heavy (99:1 read:write ratio)
2. Computation expensive (COUNT, SUM, JOIN)
3. Data rarely changes
4. Strong consistency not critical

Examples:
- available_seats (read 1000x/sec, write 10x/sec)
- theater.total_screens (read often, write never)
- movie.rating (read often, write daily)

❌ DON'T DENORMALIZE WHEN:
═══════════════════════════════════════════════════════════
1. Write-heavy
2. Strong consistency critical
3. Complex update logic
4. Multiple sources of truth

Examples:
- payment.status (critical consistency)
- booking.user_id (frequently joined)
- seat.price (complex calculation)
```

---
