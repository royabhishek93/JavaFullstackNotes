# Q32: Rate Limiting - Prevent user from hammering booking API

### Difficulty: ⭐⭐⭐ (Senior)

### ✅ Solution: Token Bucket + Redis

```java
@Component
public class RateLimiter {
    
    private final RedisTemplate<String, String> redisTemplate;
    
    // Rate limit: 10 requests per minute per user
    private static final int CAPACITY = 10;
    private static final int REFILL_RATE = 10;  // tokens per minute
    private static final Duration WINDOW = Duration.ofMinutes(1);
    
    public boolean allowRequest(Long userId, String endpoint) {
        
        String key = "ratelimit:" + userId + ":" + endpoint;
        
        // Get current token count
        String value = redisTemplate.opsForValue().get(key);
        
        if (value == null) {
            // First request, initialize bucket
            redisTemplate.opsForValue().set(
                key,
                String.valueOf(CAPACITY - 1),
                WINDOW
            );
            return true;
        }
        
        int tokens = Integer.parseInt(value);
        
        if (tokens > 0) {
            // Token available, consume it
            redisTemplate.opsForValue().decrement(key);
            return true;
        } else {
            // No tokens, rate limited
            return false;
        }
    }
}

@RestControllerAdvice
public class RateLimitInterceptor implements HandlerInterceptor {
    
    private final RateLimiter rateLimiter;
    
    @Override
    public boolean preHandle(
            HttpServletRequest request,
            HttpServletResponse response,
            Object handler) throws Exception {
        
        Long userId = getCurrentUserId(request);
        String endpoint = request.getRequestURI();
        
        if (!rateLimiter.allowRequest(userId, endpoint)) {
            response.setStatus(429);  // Too Many Requests
            response.setHeader("X-RateLimit-Limit", "10");
            response.setHeader("X-RateLimit-Remaining", "0");
            response.setHeader("Retry-After", "60");
            
            response.getWriter().write(
                "{\"error\": \"Rate limit exceeded. Try again in 60 seconds.\"}"
            );
            
            return false;
        }
        
        return true;
    }
}
```

**Advanced: Sliding Window Rate Limiter**

```java
@Component
public class SlidingWindowRateLimiter {
    
    private final RedisTemplate<String, String> redisTemplate;
    
    public boolean allowRequest(Long userId, String endpoint, int limit) {
        
        String key = "ratelimit:sliding:" + userId + ":" + endpoint;
        long now = System.currentTimeMillis();
        long windowStart = now - Duration.ofMinutes(1).toMillis();
        
        // Remove old entries outside window
        redisTemplate.opsForZSet().removeRangeByScore(
            key,
            0,
            windowStart
        );
        
        // Count requests in current window
        Long count = redisTemplate.opsForZSet().zCard(key);
        
        if (count != null && count >= limit) {
            return false;  // Rate limited
        }
        
        // Add current request
        redisTemplate.opsForZSet().add(
            key,
            UUID.randomUUID().toString(),
            now
        );
        
        // Set expiry
        redisTemplate.expire(key, Duration.ofMinutes(2));
        
        return true;
    }
}
```

**Different Limits for Different Endpoints:**

```yaml
rate-limits:
  bookings:
    create: 10/minute
    search: 100/minute
    get: 200/minute
  
  payments:
    create: 5/minute
    retry: 3/minute
  
  search:
    movies: 1000/minute
    shows: 500/minute
```

---
