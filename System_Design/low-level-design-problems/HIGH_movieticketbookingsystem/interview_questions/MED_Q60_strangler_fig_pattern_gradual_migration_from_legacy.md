# Q60: Strangler Fig Pattern - Gradual migration from legacy

### Difficulty: ⭐⭐⭐⭐⭐ (Principal)

### ✅ Solution: Facade + Feature Flags

```java
@RestController
@RequestMapping("/api/bookings")
public class BookingFacadeController {
    
    @Value("${new-booking-service.percentage}")
    private int newServicePercentage;  // 0-100
    
    @Autowired
    private LegacyBookingService legacyService;
    
    @Autowired
    private NewBookingServiceClient newService;
    
    @PostMapping
    public BookingResponse createBooking(
            @RequestBody BookingRequest request,
            @RequestHeader("X-User-Id") Long userId) {
        
        // Decide which implementation to use
        if (shouldUseNewService(userId)) {
            log.info("Routing to NEW booking service");
            return newService.createBooking(request);
        } else {
            log.info("Routing to LEGACY booking service");
            return legacyService.createBooking(request);
        }
    }
    
    private boolean shouldUseNewService(Long userId) {
        
        // Strategy 1: Percentage-based rollout
        int userBucket = (int) (userId % 100);
        if (userBucket < newServicePercentage) {
            return true;
        }
        
        // Strategy 2: Whitelist (internal users first)
        if (isInternalUser(userId)) {
            return true;
        }
        
        // Strategy 3: Feature flag (per-user override)
        if (featureFlagService.isEnabled("new-booking-service", userId)) {
            return true;
        }
        
        return false;
    }
}
```

**Migration Timeline:**

```
WEEK 1: Deploy new service (0% traffic)
═══════════════════════════════════════════════════════════
- Deploy new booking microservice
- Route 0% traffic (testing only)
- Run shadow testing (duplicate writes)

WEEK 2: Internal rollout (5% traffic)
═══════════════════════════════════════════════════════════
- Route internal users to new service
- Monitor errors, latency, correctness
- Compare results: legacy vs new

WEEK 3: Gradual rollout (25% traffic)
═══════════════════════════════════════════════════════════
- Route 25% of users to new service
- Monitor P99 latency, error rate
- Validate data consistency

WEEK 4: Majority rollout (75% traffic)
═══════════════════════════════════════════════════════════
- Route 75% of users to new service
- Legacy handles 25% (fallback)

WEEK 5: Full rollout (100% traffic)
═══════════════════════════════════════════════════════════
- Route 100% to new service
- Keep legacy code (1 week buffer)

WEEK 6: Decommission legacy
═══════════════════════════════════════════════════════════
- Remove legacy booking code
- Celebrate! 🎉
```

---

## Key Takeaways:

```
Q56: Monolith to Microservices
✅ Strangler Fig pattern (gradual migration)
✅ Extract Payment Service first
✅ Feature flag rollout (5% → 100%)
✅ 6 services, 20 engineers

Q57: Service Boundaries
✅ Domain-Driven Design (bounded contexts)
✅ Database per service
✅ Avoid: shared database, service per table
✅ Loose coupling via events

Q58: API Gateway
✅ Spring Cloud Gateway
✅ Routing, rate limiting, circuit breaker
✅ Load balancing (lb://)
✅ Fallback endpoints

Q59: CQRS Pattern
✅ Separate read and write models
✅ Write: normalized, strong consistency
✅ Read: denormalized, eventual consistency
✅ Event-driven sync via Kafka

Q60: Strangler Fig Pattern
✅ Facade routes legacy vs new
✅ Percentage-based rollout
✅ 6-week migration timeline
✅ Shadow testing for validation
```

This demonstrates production architecture patterns expertise! 🎯
