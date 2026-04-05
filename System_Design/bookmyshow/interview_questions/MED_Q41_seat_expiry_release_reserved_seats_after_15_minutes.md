# Q41: Seat Expiry - Release reserved seats after 15 minutes

### Difficulty: ⭐⭐⭐ (Senior)

### ✅ Solution: Scheduled Job + TTL

```java
@Service
public class SeatExpiryService {
    
    // Option 1: Scheduled Job (Simple, scalable)
    @Scheduled(fixedRate = 30000)  // Every 30 seconds
    public void expireReservedSeats() {
        
        LocalDateTime cutoff = LocalDateTime.now().minusMinutes(15);
        
        // Find expired reservations
        List<SeatAvailability> expiredSeats = seatRepository
            .findByStatusAndReservedUntilBefore(
                SeatStatus.RESERVED,
                cutoff
            );
        
        if (expiredSeats.isEmpty()) {
            return;
        }
        
        // Batch update to AVAILABLE
        seatRepository.updateStatusBatch(
            expiredSeats.stream()
                .map(SeatAvailability::getId)
                .collect(Collectors.toList()),
            SeatStatus.AVAILABLE
        );
        
        // Increment available_seats for affected shows
        Map<Long, Long> showCounts = expiredSeats.stream()
            .collect(Collectors.groupingBy(
                SeatAvailability::getShowId,
                Collectors.counting()
            ));
        
        showCounts.forEach((showId, count) -> {
            showRepository.incrementAvailableSeats(showId, count.intValue());
        });
        
        log.info("Expired {} reserved seats", expiredSeats.size());
    }
    
    // Option 2: Redis TTL (Real-time, complex)
    public void reserveSeatWithTTL(Long showId, Long seatId, String bookingId) {
        
        // Reserve in database
        seatRepository.updateStatus(showId, seatId, SeatStatus.RESERVED);
        
        // Set TTL in Redis (15 minutes)
        String key = "seat:reservation:" + showId + ":" + seatId;
        redisTemplate.opsForValue().set(
            key,
            bookingId,
            Duration.ofMinutes(15)
        );
        
        // Subscribe to key expiration events
        // When Redis key expires, release seat
    }
}

// Redis Key Expiration Listener
@Component
public class RedisExpirationListener extends KeyExpirationEventMessageListener {
    
    public RedisExpirationListener(
            RedisMessageListenerContainer listenerContainer) {
        super(listenerContainer);
    }
    
    @Override
    public void onMessage(Message message, byte[] pattern) {
        
        String expiredKey = new String(message.getBody());
        
        if (expiredKey.startsWith("seat:reservation:")) {
            // Parse show_id and seat_id from key
            String[] parts = expiredKey.split(":");
            Long showId = Long.parseLong(parts[2]);
            Long seatId = Long.parseLong(parts[3]);
            
            // Release seat
            seatRepository.updateStatus(showId, seatId, SeatStatus.AVAILABLE);
            showRepository.incrementAvailableSeats(showId, 1);
            
            log.info("Released expired seat: show={}, seat={}", showId, seatId);
        }
    }
}
```

**Comparison:**

```
┌────────────────────┬──────────────────┬────────────────────┐
│    Approach        │   Scheduled Job  │   Redis TTL        │
├────────────────────┼──────────────────┼────────────────────┤
│ Complexity         │ Low ✅           │ High ❌            │
│ Latency            │ Up to 30s ⚠️     │ Real-time ✅       │
│ Scalability        │ Good ✅          │ Redis dependency ❌│
│ Reliability        │ High ✅          │ Medium ⚠️          │
│ Database load      │ Batched ✅       │ Per-seat ❌        │
└────────────────────┴──────────────────┴────────────────────┘

Recommendation: Scheduled Job ✅
- 30-second delay acceptable (user has 15 minutes)
- Simpler, more reliable
- Lower Redis load
```

---
