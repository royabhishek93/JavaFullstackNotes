# Q08: Idempotency Patterns - Prevent duplicate operations

### Difficulty: ⭐⭐⭐⭐ (Staff)

### Use Cases:
```
1. User clicks "Pay" twice (network glitch)
2. Webhook called multiple times (Stripe retries)
3. User retries booking after timeout
```

### ✅ Solution: Idempotency Keys

```java
@Service
public class IdempotentBookingService {
    
    @Transactional
    public BookingResponse bookSeats(
            BookingRequest request,
            String idempotencyKey) {
        
        // Step 1: Check if already processed
        Optional<IdempotencyRecord> existing = 
            idempotencyRepository.findByKey(idempotencyKey);
        
        if (existing.isPresent()) {
            IdempotencyRecord record = existing.get();
            
            if (record.getStatus() == IdempotencyStatus.COMPLETED) {
                // Already processed, return cached response
                log.info("Idempotent request detected: {}", idempotencyKey);
                return JsonUtils.fromJson(
                    record.getResponseBody(), 
                    BookingResponse.class
                );
            } else if (record.getStatus() == IdempotencyStatus.PROCESSING) {
                // Another request currently processing
                throw new ConcurrentRequestException(
                    "Request already being processed"
                );
            }
        }
        
        // Step 2: Mark as processing
        IdempotencyRecord record = IdempotencyRecord.builder()
            .key(idempotencyKey)
            .requestBody(JsonUtils.toJson(request))
            .status(IdempotencyStatus.PROCESSING)
            .createdAt(LocalDateTime.now())
            .build();
        
        idempotencyRepository.save(record);
        
        try {
            // Step 3: Process booking
            Booking booking = doBookSeats(request);
            
            BookingResponse response = BookingResponse.from(booking);
            
            // Step 4: Store response and mark complete
            record.setStatus(IdempotencyStatus.COMPLETED);
            record.setResponseBody(JsonUtils.toJson(response));
            record.setCompletedAt(LocalDateTime.now());
            idempotencyRepository.save(record);
            
            return response;
            
        } catch (Exception e) {
            // Step 5: Mark as failed
            record.setStatus(IdempotencyStatus.FAILED);
            record.setErrorMessage(e.getMessage());
            idempotencyRepository.save(record);
            
            throw e;
        }
    }
}
```

**Idempotency Table Schema:**

```sql
CREATE TABLE idempotency_record (
    key VARCHAR(255) PRIMARY KEY,
    request_body TEXT NOT NULL,
    response_body TEXT,
    status VARCHAR(20) NOT NULL,  -- PROCESSING, COMPLETED, FAILED
    error_message TEXT,
    created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,  -- Auto-cleanup after 24 hours
    
    INDEX idx_expires_at (expires_at),
    INDEX idx_created_at (created_at DESC)
);
```

**Cleanup Job:**

```java
@Scheduled(cron = "0 0 * * * *")  // Every hour
public void cleanupExpiredIdempotencyRecords() {
    idempotencyRepository.deleteByExpiresAtBefore(
        LocalDateTime.now()
    );
}
```

---
