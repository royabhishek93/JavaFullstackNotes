# Q30: Soft Delete vs Hard Delete - Trade-offs for production

### Difficulty: ⭐⭐ (Mid-Senior)

### ✅ Solution: Soft Delete for Most Tables

```sql
-- SOFT DELETE (Recommended for most tables)
CREATE TABLE booking (
    id VARCHAR(36) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    show_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    deleted_at TIMESTAMP,  -- ← Soft delete flag
    
    INDEX idx_active (deleted_at, created_at DESC)
);

-- Query active bookings
SELECT * FROM booking 
WHERE deleted_at IS NULL;

-- Query deleted bookings (for audit)
SELECT * FROM booking 
WHERE deleted_at IS NOT NULL;


-- HARD DELETE (For temporary data)
CREATE TABLE seat_availability (
    show_id BIGINT,
    seat_id BIGINT,
    status VARCHAR(20),
    reserved_until TIMESTAMP,  -- Expiry time
    
    PRIMARY KEY (show_id, seat_id)
);

-- Hard delete expired reservations
DELETE FROM seat_availability 
WHERE status = 'RESERVED' 
  AND reserved_until < NOW();
```

**Soft Delete Implementation:**

```java
@Entity
@SQLDelete(sql = "UPDATE booking SET deleted_at = NOW() WHERE id = ?")
@Where(clause = "deleted_at IS NULL")
public class Booking {
    
    @Id
    private String id;
    
    @Column(name = "deleted_at")
    private LocalDateTime deletedAt;
    
    public void softDelete() {
        this.deletedAt = LocalDateTime.now();
    }
    
    public boolean isDeleted() {
        return deletedAt != null;
    }
}

@Service
public class BookingService {
    
    // Soft delete booking
    @Transactional
    public void cancelBooking(String bookingId) {
        Booking booking = bookingRepository.findById(bookingId)
            .orElseThrow();
        
        // Soft delete
        booking.softDelete();
        bookingRepository.save(booking);
        
        // Audit log
        auditLog.record("BOOKING_CANCELLED", bookingId);
    }
    
    // Query includes only active bookings (deleted_at IS NULL)
    public List<Booking> getUserBookings(Long userId) {
        return bookingRepository.findByUserId(userId);
        // ↑ Automatically filtered by @Where clause
    }
    
    // Query deleted bookings explicitly
    public List<Booking> getDeletedBookings(Long userId) {
        return bookingRepository.findByUserIdIncludingDeleted(userId);
    }
}
```

**Comparison:**

```
┌────────────────────┬──────────────────┬────────────────────┐
│    Feature         │   Soft Delete    │   Hard Delete      │
├────────────────────┼──────────────────┼────────────────────┤
│ Recovery           │ Easy ✅          │ Impossible ❌      │
│ Audit trail        │ Complete ✅      │ Lost ❌            │
│ Compliance (GDPR)  │ Need hard later  │ Compliant ✅       │
│ Storage cost       │ Higher ❌        │ Lower ✅           │
│ Query performance  │ Slower (filter)  │ Faster ✅          │
│ Referential        │ Preserved ✅     │ Cascade issues ❌  │
└────────────────────┴──────────────────┴────────────────────┘

RECOMMENDATION
═══════════════════════════════════════════════════════════
Soft delete: booking, payment, user, theater, movie
Hard delete: seat_availability, idempotency_record, audit_log (old)

Hybrid: Soft delete + periodic archival
- Soft delete for 90 days
- Archive to S3
- Hard delete from primary DB
```

**Archival Strategy:**

```java
@Scheduled(cron = "0 0 2 * * *")  // 2 AM daily
public void archiveOldDeletedBookings() {
    
    LocalDateTime cutoff = LocalDateTime.now().minusDays(90);
    
    // Find old deleted bookings
    List<Booking> oldDeleted = bookingRepository
        .findDeletedBefore(cutoff);
    
    if (oldDeleted.isEmpty()) {
        return;
    }
    
    // Export to S3
    String json = JsonUtils.toJson(oldDeleted);
    s3Client.putObject(
        "bookmyshow-archive",
        "bookings/deleted/" + LocalDate.now() + ".json.gz",
        compress(json)
    );
    
    // Hard delete from database
    bookingRepository.hardDeleteByIds(
        oldDeleted.stream()
            .map(Booking::getId)
            .collect(Collectors.toList())
    );
    
    log.info("Archived {} deleted bookings", oldDeleted.size());
}
```

---

## Key Takeaways:

```
Q26: Database Schema Design
✅ Complete production-ready schema
✅ Proper indexes and constraints
✅ UUID for security
✅ Partitioning for large tables

Q27: Sharding Strategy
✅ Shard by city_id (natural isolation)
✅ 50 shards = 50k bookings/sec
✅ Scatter-gather for cross-shard queries
✅ Global shard mapping table

Q28: Read Replicas
✅ 3 read replicas for 30k reads/sec
✅ Round-robin load balancing
✅ Handle replication lag (read-after-write)
✅ Cache for 80% hit rate → 150k effective

Q29: Denormalization
✅ available_seats field (500ms → 5ms)
✅ Maintain consistency with atomic updates
✅ Use for read-heavy, expensive computations
✅ Avoid for critical consistency

Q30: Soft Delete vs Hard Delete
✅ Soft delete for audit and recovery
✅ Hard delete for temporary data
✅ Archival strategy (90 days → S3)
✅ GDPR compliance considerations
```

This demonstrates production database scaling expertise! 🎯
