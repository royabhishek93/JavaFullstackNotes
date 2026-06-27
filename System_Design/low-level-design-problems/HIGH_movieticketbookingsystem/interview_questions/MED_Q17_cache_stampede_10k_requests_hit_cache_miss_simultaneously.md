# Q17: Cache Stampede - 10k requests hit cache miss simultaneously

### Problem:
```
Cache expires → 10k requests hit DB → DB overload!
```

### ✅ Solution: Lock-based Cache Refresh

```java
@Service
public class StampedePreventionService {
    
    private final LoadingCache<String, List<Seat>> seatCache;
    
    public StampedePreventionService() {
        this.seatCache = Caffeine.newBuilder()
            .expireAfterWrite(Duration.ofSeconds(30))
            .refreshAfterWrite(Duration.ofSeconds(25))  // Refresh before expiry
            .build(key -> loadSeatsFromDatabase(key));
    }
    
    public List<Seat> getSeats(Long showId) {
        // Only one thread refreshes, others get stale data
        return seatCache.get("show:" + showId);
    }
    
    private List<Seat> loadSeatsFromDatabase(String key) {
        Long showId = Long.parseLong(key.split(":")[1]);
        return seatRepository.findByShowId(showId);
    }
}
```

**Alternative: Redis Lock**

```java
public List<Seat> getSeatsWithLock(Long showId) {
    String cacheKey = "show:" + showId + ":seats";
    String lockKey = "lock:" + cacheKey;
    
    // Try cache first
    List<Seat> cached = redisTemplate.opsForValue().get(cacheKey);
    if (cached != null) {
        return cached;
    }
    
    // Cache miss: Try to acquire lock
    Boolean acquired = redisTemplate.opsForValue()
        .setIfAbsent(lockKey, "1", Duration.ofSeconds(5));
    
    if (Boolean.TRUE.equals(acquired)) {
        try {
            // I got the lock, refresh cache
            List<Seat> seats = seatRepository.findByShowId(showId);
            redisTemplate.opsForValue().set(cacheKey, seats, Duration.ofSeconds(30));
            return seats;
        } finally {
            redisTemplate.delete(lockKey);
        }
    } else {
        // Someone else is refreshing, wait and retry
        Thread.sleep(100);
        return getSeatsWithLock(showId);  // Retry
    }
}
```

---
