# Q58: API Gateway - Single entry point for microservices

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: Spring Cloud Gateway

```java
@Configuration
public class GatewayConfig {
    
    @Bean
    public RouteLocator customRouteLocator(RouteLocatorBuilder builder) {
        return builder.routes()
            
            // User Service
            .route("user-service", r -> r
                .path("/api/users/**", "/api/auth/**")
                .filters(f -> f
                    .addRequestHeader("X-Gateway", "true")
                    .circuitBreaker(config -> config
                        .setName("user-service-cb")
                        .setFallbackUri("forward:/fallback/user"))
                    .retry(config -> config
                        .setRetries(3)
                        .setBackoff(Duration.ofMillis(100), 
                                   Duration.ofSeconds(1), 2, true)))
                .uri("lb://user-service"))  // Load balanced
            
            // Booking Service
            .route("booking-service", r -> r
                .path("/api/bookings/**", "/api/seats/**")
                .filters(f -> f
                    .requestRateLimiter(config -> config
                        .setRateLimiter(redisRateLimiter())
                        .setKeyResolver(userKeyResolver()))
                    .circuitBreaker(config -> config
                        .setName("booking-service-cb")))
                .uri("lb://booking-service"))
            
            // Payment Service
            .route("payment-service", r -> r
                .path("/api/payments/**")
                .filters(f -> f
                    .addRequestHeader("X-Request-Start", 
                        String.valueOf(System.currentTimeMillis()))
                    .circuitBreaker(config -> config
                        .setName("payment-service-cb")
                        .setFallbackUri("forward:/fallback/payment")))
                .uri("lb://payment-service"))
            
            .build();
    }
    
    @Bean
    public RedisRateLimiter redisRateLimiter() {
        return new RedisRateLimiter(
            10,  // replenishRate: 10 requests per second
            20   // burstCapacity: 20 requests max
        );
    }
    
    @Bean
    public KeyResolver userKeyResolver() {
        return exchange -> Mono.just(
            exchange.getRequest()
                .getHeaders()
                .getFirst("X-User-Id")
        );
    }
}

@RestController
public class FallbackController {
    
    @GetMapping("/fallback/booking")
    public ResponseEntity<Map<String, String>> bookingFallback() {
        return ResponseEntity.status(503).body(Map.of(
            "error", "Booking service temporarily unavailable",
            "message", "Please try again in a few minutes"
        ));
    }
    
    @GetMapping("/fallback/payment")
    public ResponseEntity<Map<String, String>> paymentFallback() {
        return ResponseEntity.status(503).body(Map.of(
            "error", "Payment service temporarily unavailable",
            "message", "Your booking is saved. We'll process payment shortly."
        ));
    }
}
```

**API Gateway Responsibilities:**

```
WHAT API GATEWAY DOES
═══════════════════════════════════════════════════════════
✅ Routing (path → service)
✅ Load balancing
✅ Rate limiting (10 req/sec per user)
✅ Authentication (JWT validation)
✅ Circuit breaker (fallback on failure)
✅ Retry logic (3 retries with backoff)
✅ Request/response transformation
✅ Logging & monitoring
✅ CORS handling

WHAT API GATEWAY SHOULD NOT DO
═══════════════════════════════════════════════════════════
❌ Business logic
❌ Database queries
❌ Heavy computations
❌ Service orchestration (use separate orchestrator)
```

---
