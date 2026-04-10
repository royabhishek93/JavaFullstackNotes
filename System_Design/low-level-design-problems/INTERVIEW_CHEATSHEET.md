# Low-Level Design Interview Cheatsheet

## Quick Navigation
Jump to: [Common Patterns](#design-patterns-quick-reference) | [Key Problems](#most-asked-problems) | [Talking Points](#interview-talking-points) | [Trade-offs](#common-trade-offs)

---

## Most Asked Problems (Priority Order)

### 🔥 Top 5 Must-Know
1. **Parking Lot System** ⭐⭐⭐⭐⭐
   - **Key Concepts**: Singleton, Strategy pattern, Concurrency
   - **Files**: `parking-lot.md`, `parkinglot/`
   - **Gotchas**: Thread safety, pricing strategies, vehicle type hierarchy
   - **5-min Pitch**: "Multi-level parking with different vehicle types. Use Singleton for parking lot, synchronized methods for thread safety, strategy pattern for pricing"

2. **LRU Cache** ⭐⭐⭐⭐⭐
   - **Key Concepts**: HashMap + Doubly Linked List, O(1) operations
   - **Files**: `lru-cache.md`, `lrucache/`
   - **Gotchas**: Why doubly linked? Thread safety, eviction policy
   - **5-min Pitch**: "Fixed capacity cache with O(1) get/put. HashMap for fast lookup, doubly linked list for LRU ordering. Move to head on access, evict from tail when full"

3. **Elevator System** ⭐⭐⭐⭐⭐
   - **Key Concepts**: Scheduling algorithms (SCAN, LOOK), Multi-threading
   - **Files**: `elevator-system.md`, `elevatorsystem/`
   - **Gotchas**: Request prioritization, direction optimization, starvation prevention
   - **5-min Pitch**: "Multiple elevators serving multiple floors. Use SCAN algorithm for efficiency, request queue per elevator, nearest-elevator selection with direction consideration"

4. **Movie Ticket Booking** ⭐⭐⭐⭐
   - **Key Concepts**: Concurrency, Seat locking, Transaction management
   - **Files**: `movie-ticket-booking-system.md`, `movieticketbookingsystem/`
   - **Gotchas**: Race conditions on seat booking, payment failures, timeout handling
   - **5-min Pitch**: "Book movie seats with concurrency. Lock seats during booking, handle payment, rollback on failure. Use synchronized blocks for thread safety"

5. **Design Splitwise** ⭐⭐⭐⭐
   - **Key Concepts**: Graph algorithms, Debt simplification
   - **Files**: `splitwise.md`, `splitwise/`
   - **Gotchas**: Minimizing transactions, equal/percentage/exact splits, group expenses
   - **5-min Pitch**: "Expense sharing app. Track who owes whom, simplify debts using graph algorithms, support different split types (equal, percentage, exact amounts)"

### 🎯 Next 5 Important
6. **Ride Sharing (Uber/Lyft)** - `ride-sharing-service.md`
7. **Hotel Management** - `hotel-management-system.md`
8. **Library Management** - `library-management-system.md`
9. **Snake and Ladder Game** - `snake-and-ladder.md`
10. **ATM System** - `atm.md`

### 💼 Domain-Specific
- **E-commerce**: `online-shopping-service.md`
- **Social Media**: `linkedin.md`, `social-networking-service.md`, `stackoverflow.md`
- **Streaming**: `music-streaming-service.md`
- **Food Delivery**: `food-delivery-service.md`
- **Finance**: `online-stock-brokerage-system.md`, `digital-wallet-service.md`

---

## Design Patterns Quick Reference

### Singleton Pattern
**When**: Ensure single instance (ParkingLot, BookingManager, PaymentProcessor)
```java
public class ParkingLot {
    private static ParkingLot instance;
    private ParkingLot() {}
    
    public static synchronized ParkingLot getInstance() {
        if (instance == null) {
            instance = new ParkingLot();
        }
        return instance;
    }
}
```
**Used In**: Parking Lot, Airline Management, Elevator System

### Factory Pattern
**When**: Create objects without exposing creation logic
```java
public class VehicleFactory {
    public static Vehicle createVehicle(VehicleType type) {
        switch(type) {
            case CAR: return new Car();
            case TRUCK: return new Truck();
            case MOTORCYCLE: return new Motorcycle();
        }
    }
}
```
**Used In**: Parking Lot, Game pieces (Chess, Tic-Tac-Toe)

### Strategy Pattern
**When**: Multiple algorithms for same task (pricing, payment)
```java
interface PricingStrategy {
    double calculatePrice(Vehicle v, long duration);
}
class HourlyPricing implements PricingStrategy { ... }
class FlatRatePricing implements PricingStrategy { ... }
```
**Used In**: Parking Lot (pricing), Payment processing, Ride sharing (pricing)

### Observer Pattern
**When**: Notify multiple objects about state changes
```java
interface Observer {
    void update(Event event);
}
class NotificationService implements Observer { ... }
```
**Used In**: Stock brokerage (price updates), Pub-Sub system, Social networking (feeds)

### Builder Pattern
**When**: Complex object construction with many parameters
```java
Booking booking = new Booking.Builder()
    .withFlight(flight)
    .withPassenger(passenger)
    .withSeat(seat)
    .withPayment(payment)
    .build();
```
**Used In**: Airline booking, Hotel booking, Food delivery orders

### State Pattern
**When**: Object behavior changes based on internal state
```java
interface ElevatorState {
    void handleRequest(Request r);
}
class IdleState implements ElevatorState { ... }
class MovingState implements ElevatorState { ... }
```
**Used In**: Elevator (idle/moving), Vending machine, ATM

---

## Concurrency & Thread Safety

### Common Techniques

#### 1. Synchronized Methods
```java
public synchronized boolean bookSeat(Seat seat) {
    if (seat.isAvailable()) {
        seat.setAvailable(false);
        return true;
    }
    return false;
}
```
**Pros**: Simple, automatic lock management  
**Cons**: Coarse-grained, can become bottleneck  
**Use**: Low contention scenarios

#### 2. Synchronized Blocks
```java
synchronized(lockObject) {
    // critical section
    if (seat.isAvailable()) {
        seat.setAvailable(false);
    }
}
```
**Pros**: Fine-grained control, better performance  
**Cons**: Manual lock management  
**Use**: High contention, need specific locking

#### 3. ReentrantLock
```java
private final Lock lock = new ReentrantLock();

public void bookSeat() {
    lock.lock();
    try {
        // critical section
    } finally {
        lock.unlock();
    }
}
```
**Pros**: More features (tryLock, timed locks)  
**Cons**: Must manually unlock  
**Use**: Need advanced locking features

#### 4. ConcurrentHashMap
```java
private final ConcurrentHashMap<String, Seat> seats = new ConcurrentHashMap<>();
```
**Pros**: High concurrency, no explicit locking  
**Cons**: Limited to map operations  
**Use**: Mostly read operations with occasional writes

#### 5. Atomic Classes
```java
private final AtomicInteger availableSeats = new AtomicInteger(100);
availableSeats.decrementAndGet();
```
**Pros**: Lock-free, very fast  
**Cons**: Limited to single variable operations  
**Use**: Counters, flags, simple state

### Concurrency Gotchas
❌ **Don't**: Use `synchronized` everywhere (performance killer)  
✅ **Do**: Synchronize only critical sections  

❌ **Don't**: Forget to handle race conditions in booking systems  
✅ **Do**: Lock seat before checking availability  

❌ **Don't**: Hold locks while doing I/O or network calls  
✅ **Do**: Keep critical sections small and fast  

---

## Interview Talking Points

### When Asked "Tell me about your design"

**Structure your answer (STAR format):**

1. **Requirements** (30 seconds)
   - "The system needs to handle X, Y, Z..."
   - "Key constraints are..."

2. **Core Entities** (1 minute)
   - "Main classes are A, B, C..."
   - "Relationships: A has-a B, C is-a D..."

3. **Design Decisions** (1-2 minutes)
   - "I chose Singleton because..."
   - "Used HashMap for O(1) lookup..."
   - "Thread safety via synchronized blocks..."

4. **Trade-offs** (1 minute)
   - "Pros: Fast, simple, scalable"
   - "Cons: Memory overhead, no persistence"
   - "Alternative: Could use... but..."

5. **Extensions** (30 seconds)
   - "Can add: analytics, caching, mobile API..."

### Red Flags to Avoid

❌ Saying "We can scale later" without explaining how  
❌ Ignoring thread safety in multi-user systems  
❌ Not considering edge cases (null, empty, overflow)  
❌ Over-engineering simple problems  
❌ Under-engineering complex problems  
❌ Not asking clarifying questions  

### Green Flags to Show

✅ Ask about scale: "How many concurrent users?"  
✅ Ask about constraints: "Read-heavy or write-heavy?"  
✅ Discuss trade-offs: "X is faster but Y is more maintainable"  
✅ Think about extensions: "We could add..."  
✅ Consider failure cases: "What if payment fails?"  
✅ Mention testing: "We'd unit test... integration test..."  

---

## Common Trade-offs

### Time vs Space
| Choice | Time | Space | When to Use |
|--------|------|-------|-------------|
| **Cache results** | Faster | More memory | Repeated queries |
| **Recompute** | Slower | Less memory | One-time operations |

### Consistency vs Availability
| Choice | Consistency | Availability | When to Use |
|--------|-------------|--------------|-------------|
| **Strong consistency** | Always current | May fail | Banking, bookings |
| **Eventual consistency** | May lag | Always up | Social feeds, analytics |

### Simplicity vs Flexibility
| Choice | Simple | Flexible | When to Use |
|--------|--------|----------|-------------|
| **Fixed capacity** | Easy | Limited | Known requirements |
| **Dynamic sizing** | Complex | Adaptable | Unpredictable load |

### Synchronous vs Asynchronous
| Choice | Response Time | Complexity | When to Use |
|--------|--------------|------------|-------------|
| **Sync** | Immediate | Simple | User-facing operations |
| **Async** | Delayed | Complex | Background tasks |

---

## SOLID Principles Checklist

### Single Responsibility
✅ Each class has one job  
✅ `BookingManager` handles bookings, not payments  
✅ `PaymentProcessor` handles payments, not bookings  

### Open/Closed
✅ Open for extension (new vehicle types)  
✅ Closed for modification (don't change base Vehicle)  
✅ Use interfaces and inheritance  

### Liskov Substitution
✅ Subclasses can replace parent (Car → Vehicle)  
✅ No broken behavior in subclasses  

### Interface Segregation
✅ Small, focused interfaces  
✅ Don't force classes to implement unused methods  

### Dependency Inversion
✅ Depend on abstractions (interfaces), not concrete classes  
✅ Use `PaymentMethod` interface, not `CreditCard` directly  

---

## Quick Code Snippets

### Thread-safe Singleton
```java
public class BookingManager {
    private static volatile BookingManager instance;
    
    public static BookingManager getInstance() {
        if (instance == null) {
            synchronized (BookingManager.class) {
                if (instance == null) {
                    instance = new BookingManager();
                }
            }
        }
        return instance;
    }
}
```

### Enum for Type Safety
```java
public enum VehicleType {
    CAR, TRUCK, MOTORCYCLE;
}

public enum BookingStatus {
    PENDING, CONFIRMED, CANCELLED, COMPLETED;
}
```

### Builder Pattern
```java
public class Booking {
    private final String id;
    private final User user;
    private final Flight flight;
    
    private Booking(Builder builder) {
        this.id = builder.id;
        this.user = builder.user;
        this.flight = builder.flight;
    }
    
    public static class Builder {
        private String id;
        private User user;
        private Flight flight;
        
        public Builder withId(String id) { this.id = id; return this; }
        public Builder withUser(User user) { this.user = user; return this; }
        public Builder withFlight(Flight flight) { this.flight = flight; return this; }
        public Booking build() { return new Booking(this); }
    }
}
```

---

## Time Complexity Quick Reference

| Operation | Target | Why |
|-----------|--------|-----|
| **Cache Get/Put** | O(1) | HashMap + LinkedList |
| **Book Seat** | O(1) | Direct access with sync |
| **Search Available** | O(n) | Need to scan all items |
| **Find Nearest Elevator** | O(n) | Compare all elevators |
| **Graph Traversal** | O(V+E) | BFS/DFS for connections |

---

## Pre-Interview Checklist

### 1 Week Before
- [ ] Review all Top 5 problems
- [ ] Understand diagrams for each
- [ ] Code at least 2 from scratch
- [ ] Practice explaining design decisions

### 1 Day Before
- [ ] Review this cheatsheet
- [ ] Skim through all 33 problem descriptions
- [ ] Practice whiteboarding one problem
- [ ] Prepare questions to ask interviewer

### During Interview
- [ ] Clarify requirements first
- [ ] Draw diagrams (boxes, arrows)
- [ ] Think out loud
- [ ] Discuss trade-offs
- [ ] Ask for feedback
- [ ] Handle gracefully if stuck

---

## Common Questions & Answers

**Q: How do you prevent double booking?**  
A: Use database transactions with row-level locking, or distributed locks (Redis) for scalability

**Q: How do you handle payment failures?**  
A: Implement compensation logic - release locked resources, update booking status, refund if needed

**Q: How would you scale this to millions of users?**  
A: Database sharding, read replicas, caching layer, load balancers, microservices architecture

**Q: What if the database goes down?**  
A: Use database replication, backup strategies, circuit breaker pattern, graceful degradation

**Q: How do you test this system?**  
A: Unit tests for each class, integration tests for workflows, load testing for concurrency, mock external dependencies

---

## Useful Resources in This Folder

- **Diagrams**: See `diagrams/` folder for all UML class diagrams
- **Java Code**: Each problem has a folder with working implementation
- **Problem Descriptions**: Each `.md` file has requirements and design details
- **Main README**: `README.md` has full problem index

---

## Final Tips

1. **Start Simple**: Basic version first, then enhance
2. **Draw First**: Always sketch the design
3. **Think Aloud**: Explain your reasoning
4. **Be Honest**: If you don't know, say so and reason through it
5. **Time Management**: Don't spend 40 min on one class
6. **Ask Questions**: Better to clarify than assume wrong

**Remember**: Interviewers want to see your thought process, not just the final answer!

---

Good luck with your interviews! 🚀
