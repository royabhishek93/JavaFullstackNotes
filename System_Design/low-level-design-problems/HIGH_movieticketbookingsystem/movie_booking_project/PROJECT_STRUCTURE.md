# 🎯 Project Structure - FOR INTERVIEW

## ✅ Use This Structure (Production-Ready)

```
movie_booking_project/
│
├── 📂 src/                          ⭐ MAIN PRODUCTION CODE
│   ├── main/
│   │   ├── java/com/moviebooking/
│   │   │   ├── model/
│   │   │   │   ├── entity/         ✅ JPA Entities (10 files)
│   │   │   │   ├── dto/            ⚠️  Need to create
│   │   │   │   └── enums/          ✅ Enums (5 files)
│   │   │   ├── repository/         ⚠️  Need to create
│   │   │   ├── service/            ✅ BookingService.java (CRITICAL)
│   │   │   ├── controller/         ⚠️  Need to create
│   │   │   ├── exception/          ✅ Custom exceptions (4 files)
│   │   │   ├── config/             ⚠️  Need to create
│   │   │   └── MovieBookingApplication.java  ⚠️  Main class
│   │   │
│   │   └── resources/
│   │       ├── application.yml     ✅ Main config
│   │       └── application-test.yml ✅ Test config
│   │
│   └── test/java/                  ⚠️  Need to create tests
│
├── 📂 legacy_basic_implementation/  ❌ IGNORE FOR INTERVIEW
│   ├── BookingManager.java          (Reference only)
│   ├── MovieBookingService.java     (Basic version)
│   ├── SeatLockManager.java         (In-memory)
│   └── MovieBookingDemo.java        (Demo)
│
├── 📄 pom.xml                       ✅ Maven config
├── 📄 README_PRODUCTION.md          ✅ Full guide
├── 📄 INTERVIEW_APPROACH.md         ✅ Interview strategy
├── 📄 DATABASE_SCHEMA_VISUAL.md     ✅ DB diagrams
└── 📄 SUMMARY.md                    ✅ Quick reference
```

---

## 🚀 What to Focus On (45-60 min Interview)

### ✅ **Already Complete (Show These)**

1. **Entity Layer** - `/src/main/java/com/moviebooking/model/entity/`
   - `Seat.java` ⭐ - Locking logic
   - `Booking.java` - Transaction management
   - `Payment.java` - Payment handling
   - 7 other entities

2. **Service Layer** - `/src/main/java/com/moviebooking/service/`
   - `BookingService.java` ⭐⭐⭐ **MOST IMPORTANT**
     - Pessimistic locking
     - Transaction management
     - Idempotency
     - Payment integration

3. **Exception Handling** - `/src/main/java/com/moviebooking/exception/`
   - Custom exceptions with clear messages

4. **Configuration**
   - `pom.xml` - All dependencies
   - `application.yml` - Production config

---

### ⚠️ **Quick to Add (If Time Permits)**

These are **simple boilerplate** - don't spend interview time here:

1. **Repositories** (5 interfaces, ~10 lines each)
```java
@Repository
public interface SeatRepository extends JpaRepository<Seat, UUID> {
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT s FROM Seat s WHERE s.id IN :ids")
    List<Seat> findAllByIdForUpdate(@Param("ids") List<UUID> ids);
}
```

2. **Main Application Class** (1 file, 8 lines)
```java
@SpringBootApplication
@EnableScheduling
public class MovieBookingApplication {
    public static void main(String[] args) {
        SpringApplication.run(MovieBookingApplication.class, args);
    }
}
```

3. **Controllers** (Optional - mention but don't code)
```java
@RestController
@RequestMapping("/api/v1/bookings")
public class BookingController {
    // Thin wrapper over BookingService
}
```

---

## 🎬 Interview Timeline (45-60 min)

### **Phase 1: Architecture (5-7 min)**
Show this diagram from `README_PRODUCTION.md`:
```
User API → Booking Service → [Lock Seats → Payment → Confirm]
                ↓
          Seat Inventory (with locking)
```

### **Phase 2: Database Design (5-8 min)**
Open `DATABASE_SCHEMA_VISUAL.md` → Show:
- ER diagram
- Seat locking columns (`locked_by`, `locked_until`)
- Indexes for performance

### **Phase 3: Core Implementation (25-30 min)** ⭐ **CRITICAL**
Open `src/main/java/com/moviebooking/service/BookingService.java`

Walk through these methods:
1. `createBooking()` - Main flow with transaction
2. `lockSeats()` - Pessimistic locking with SELECT FOR UPDATE
3. `releaseSeats()` - Rollback on failure
4. `confirmBooking()` - Mark seats as BOOKED

**Code to explain**:
```java
@Transactional(isolation = Isolation.READ_COMMITTED, rollbackFor = Exception.class)
public Booking createBooking(...) {
    // 1. Check idempotency
    Booking existing = bookingRepository.findByIdempotencyKey(key);
    if (existing != null) return existing;
    
    // 2. Lock seats with SELECT FOR UPDATE
    List<Seat> seats = lockSeats(show, seatIds, user);
    
    try {
        // 3. Process payment
        Payment payment = paymentService.processPayment(...);
        
        // 4. Confirm booking
        confirmBooking(booking, seats);
        
        return booking;
    } catch (Exception e) {
        // 5. Rollback: Release seats
        releaseSeats(seats);
        throw e;
    }
}
```

### **Phase 4: Concurrency Discussion (10-15 min)**
Explain:
- **Race condition prevention** - Database row-level locks
- **Timeout handling** - TTL + scheduled cleanup
- **Transaction isolation** - READ_COMMITTED
- **Idempotency** - Prevent duplicate bookings

### **Phase 5: Scaling (5 min)** (If asked)
- Database sharding by `show_id`
- Redis caching for seat availability
- Read replicas for search queries
- Message queue for async operations

---

## ❌ What NOT to Show

### **legacy_basic_implementation/** folder
- ❌ Not production-ready
- ❌ In-memory only (no database)
- ❌ No Spring Boot framework
- ❌ Basic concurrency (ConcurrentHashMap)

**Only mention**: "I also have a basic prototype for quick demos, but the production version uses proper database transactions and Spring Boot."

---

## 🎯 Interview Strategy

### **When Asked to Code**

✅ **DO:**
- Start with architecture diagram (5 min)
- Focus on `BookingService.createBooking()` method
- Explain design decisions as you go
- Mention trade-offs (pessimistic vs optimistic locking)

❌ **DON'T:**
- Try to write everything from scratch
- Spend time on boilerplate (controllers, DTOs)
- Over-engineer simple parts
- Code without explaining

### **When Asked About Implementation**

✅ **DO:**
- Reference your existing code in `src/`
- Walk through critical sections line-by-line
- Explain concurrency control in detail
- Discuss testing strategy

❌ **DON'T:**
- Show the legacy folder
- Apologize for missing boilerplate
- Dive into framework details (Spring internals)

### **When Asked "How Would You Scale?"**

✅ **DO:**
- Database sharding by `show_id`
- Redis caching with TTL
- Horizontal scaling (stateless services)
- Message queue for async tasks

❌ **DON'T:**
- Suggest premature optimization
- Over-complicate with microservices
- Ignore the current implementation

---

## 📝 Key Files to Have Open

### **During Interview, Open These:**

1. `src/main/java/com/moviebooking/service/BookingService.java` ⭐⭐⭐
2. `src/main/java/com/moviebooking/model/entity/Seat.java` ⭐⭐
3. `DATABASE_SCHEMA_VISUAL.md` ⭐⭐
4. `README_PRODUCTION.md` ⭐ (for reference)

### **Keep These Handy for Questions:**
- `INTERVIEW_APPROACH.md` - Talking points
- `pom.xml` - Dependency discussion
- `application.yml` - Configuration discussion

---

## 🏆 What Makes This 10 YOE Level?

### ✅ **You Have:**
- Production architecture (layered, clean)
- Database-level concurrency control
- Transaction management with rollback
- Idempotency for retry safety
- Scheduled cleanup jobs
- Proper exception handling
- Scalability considerations
- Comprehensive documentation

### ❌ **You DON'T Need:**
- Every single repository interface
- Complete controller layer
- Full test coverage
- Frontend/UI
- Deployment scripts
- Monitoring dashboards

**In 45-60 min, focus on demonstrating design thinking, not complete code.**

---

## 💡 Quick Reference

| Question | Answer |
|----------|--------|
| What's the main code? | `src/main/java/com/moviebooking/` |
| What's most important? | `BookingService.java` |
| What about legacy files? | Ignore, use `src/` folder |
| Do I need controllers? | Mention, don't implement |
| What about tests? | Discuss strategy, don't write |
| How complete is this? | 70% - enough for interview |

---

## 🚀 Final Checklist Before Interview

- [ ] Review `BookingService.java` - understand every line
- [ ] Read `DATABASE_SCHEMA_VISUAL.md` - understand concurrency
- [ ] Scan `INTERVIEW_APPROACH.md` - memorize talking points
- [ ] Know the architecture diagram
- [ ] Prepare scaling discussion
- [ ] Have `src/` folder open in IDE
- [ ] Close/hide `legacy_basic_implementation/` folder

---

**You're ready! Focus on the `/src/` folder and explain your design decisions confidently! 🎯**
