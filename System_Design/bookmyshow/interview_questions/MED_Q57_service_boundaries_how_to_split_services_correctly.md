# Q57: Service Boundaries - How to split services correctly?

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: Domain-Driven Design (DDD)

```
BOUNDED CONTEXTS
═══════════════════════════════════════════════════════════

1. Identity Context
   Entities: User, Role, Permission
   Services: AuthenticationService, AuthorizationService
   
2. Catalog Context
   Entities: Movie, Theater, Screen, Show
   Services: MovieSearchService, ShowSchedulingService
   
3. Booking Context ⭐ (Core Domain)
   Entities: Booking, SeatAvailability, Seat
   Services: BookingService, SeatReservationService
   
4. Payment Context
   Entities: Payment, Transaction, Refund
   Services: PaymentProcessingService, RefundService
   
5. Notification Context
   Entities: Notification, Template
   Services: EmailService, SMSService, PushNotificationService
```

**Anti-Patterns to Avoid:**

```
❌ ANTI-PATTERN 1: Shared Database
═══════════════════════════════════════════════════════════
Service A ──┐
             ├──→ Shared Database
Service B ──┘

Problem: Tight coupling, schema changes affect both services


✅ CORRECT: Database per Service
═══════════════════════════════════════════════════════════
Service A ──→ Database A
Service B ──→ Database B
     ↓             ↓
  API calls for cross-service communication


❌ ANTI-PATTERN 2: Service per Table
═══════════════════════════════════════════════════════════
UserService (users table)
AddressService (addresses table)
PhoneService (phones table)

Problem: Too granular, chatty network calls


✅ CORRECT: Service per Bounded Context
═══════════════════════════════════════════════════════════
UserService (users, addresses, phones)


❌ ANTI-PATTERN 3: Distributed Monolith
═══════════════════════════════════════════════════════════
Every service depends on every other service
A → B → C → D → A (circular dependencies)

Problem: Cannot deploy independently


✅ CORRECT: Loose Coupling
═══════════════════════════════════════════════════════════
Services communicate via events (Kafka)
No synchronous dependencies
```

---
