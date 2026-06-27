# Q56: Monolith to Microservices - Migration strategy for BookMyShow

### Difficulty: ⭐⭐⭐⭐⭐ (Principal)

### ✅ Solution: Strangler Fig Pattern

```
CURRENT STATE (Monolith)
═══════════════════════════════════════════════════════════
┌─────────────────────────────────────────────────────────┐
│                  BookMyShow Monolith                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │ • User Management                                 │  │
│  │ • Movie Catalog                                   │  │
│  │ • Show Management                                 │  │
│  │ • Booking Service                                 │  │
│  │ • Payment Processing                              │  │
│  │ • Notification Service                            │  │
│  │ • Search                                          │  │
│  └──────────────────────────────────────────────────┘  │
│                          ↓                              │
│              Single PostgreSQL Database                 │
└─────────────────────────────────────────────────────────┘

Problems:
❌ Single point of failure
❌ Tight coupling (change in one module affects all)
❌ Difficult to scale (must scale entire monolith)
❌ Long deployment cycles (30+ minutes)
❌ Technology lock-in (stuck with Java/Spring)


TARGET STATE (Microservices)
═══════════════════════════════════════════════════════════
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  User    │  │  Movie   │  │ Booking  │  │ Payment  │
│ Service  │  │ Catalog  │  │ Service  │  │ Service  │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │
   Users DB    Movies DB    Bookings DB    Payments DB

Benefits:
✅ Independent scaling
✅ Independent deployment
✅ Technology diversity
✅ Team autonomy
✅ Fault isolation
```

**Migration Phases:**

```java
// PHASE 1: Extract Payment Service (Strangler Fig)
@RestController
@RequestMapping("/api")
public class MonolithBookingController {
    
    @Value("${payment.service.enabled}")
    private boolean paymentServiceEnabled;
    
    @Autowired
    private PaymentServiceClient paymentServiceClient;  // New microservice
    
    @Autowired
    private LegacyPaymentService legacyPaymentService;  // Old monolith code
    
    @PostMapping("/payments")
    public PaymentResponse processPayment(@RequestBody PaymentRequest request) {
        
        if (paymentServiceEnabled) {
            // Route to new microservice
            log.info("Routing payment to microservice");
            return paymentServiceClient.processPayment(request);
        } else {
            // Route to legacy code
            log.info("Routing payment to legacy monolith");
            return legacyPaymentService.processPayment(request);
        }
    }
}

// Feature flag rollout:
// Week 1: 5% traffic to microservice
// Week 2: 25% traffic
// Week 3: 50% traffic
// Week 4: 100% traffic
// Week 5: Remove legacy code
```

**Service Boundaries:**

```
SERVICE DECOMPOSITION STRATEGY
═══════════════════════════════════════════════════════════

1. User Service
   - Owns: users, authentication, profiles
   - Database: user_db
   - Team: Identity team (3 engineers)
   
2. Movie Catalog Service
   - Owns: movies, theaters, screens, shows
   - Database: catalog_db
   - Team: Catalog team (4 engineers)
   
3. Booking Service ⭐ (Core)
   - Owns: bookings, seat_availability
   - Database: booking_db (sharded)
   - Team: Booking team (6 engineers)
   
4. Payment Service
   - Owns: payments, refunds, transactions
   - Database: payment_db
   - Team: Payment team (3 engineers)
   
5. Notification Service
   - Owns: emails, SMS, push notifications
   - Database: notification_db
   - Team: Platform team (2 engineers)
   
6. Search Service
   - Owns: Elasticsearch indexes
   - Database: elasticsearch_cluster
   - Team: Search team (2 engineers)

Total: 20 engineers, 6 services
```

**Data Consistency (Saga Pattern):**

```java
// Booking workflow across services
@Service
public class BookingSagaOrchestrator {
    
    public Booking createBooking(BookingRequest request) {
        
        String sagaId = UUID.randomUUID().toString();
        
        try {
            // Step 1: Reserve seats (Booking Service)
            bookingService.reserveSeats(sagaId, request);
            
            // Step 2: Process payment (Payment Service)
            Payment payment = paymentService.charge(sagaId, request);
            
            // Step 3: Confirm booking (Booking Service)
            Booking booking = bookingService.confirmBooking(sagaId, payment);
            
            // Step 4: Send notification (Notification Service)
            notificationService.sendConfirmation(sagaId, booking);
            
            return booking;
            
        } catch (Exception e) {
            // Compensate: Rollback all steps
            compensate(sagaId);
            throw e;
        }
    }
    
    private void compensate(String sagaId) {
        // Release seats
        bookingService.releaseSeatsBySagaId(sagaId);
        
        // Refund payment
        paymentService.refundBySagaId(sagaId);
    }
}
```

---
