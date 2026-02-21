# Q3: How do you make singleton beans thread-safe?

**Study Time:** 3-4 minutes

---

## Problem

Singleton beans are shared across all threads. Mutable state in singletons causes race conditions.

```java
@Component
public class PaymentCounter {
    private int totalPayments = 0;  // ⚠️ Shared state
    
    public void recordPayment() {
        totalPayments++;  // ❌ Not atomic! Race condition!
    }
    
    public int getTotal() {
        return totalPayments;  // ❌ Wrong value likely
    }
}

// Two threads call recordPayment() simultaneously:
// Thread 1: reads totalPayments (0)
// Thread 2: reads totalPayments (0)
// Thread 1: writes totalPayments (1)
// Thread 2: writes totalPayments (1)  [should be 2!]
// Result: totalPayments = 1 ❌
```

## Solution 1: Make Beans STATELESS (BEST) 🔥

Don't store state in singleton beans. Most services should be stateless.

```java
// ✅ BEST: Stateless service
@Component
public class PaymentService {
    @Autowired private PaymentRepository repo;
    
    public void recordPayment(Payment payment) {
        // No instance state - thread-safe by design
        repo.save(payment);
    }
    
    public int getTotalPayments() {
        // Query database - no shared memory
        return repo.count();
    }
}
```

**Why this works:**
- No shared variables
- Each thread has its own local variables
- Thread-safe naturally

## Solution 2: Use Immutable Objects

```java
@Component
public class ConfigService {
    // ✅ Immutable - safe for sharing
    private final Map<String, String> config;
    
    public ConfigService() {
        this.config = Collections.unmodifiableMap(
            loadConfig()
        );
    }
    
    public String getConfig(String key) {
        return config.get(key);  // ✅ Thread-safe read
    }
}
```

## Solution 3: Use Atomic Classes

```java
@Component
public class PaymentCounter {
    // ✅ Atomic operation
    private final AtomicInteger totalPayments = new AtomicInteger(0);
    
    public void recordPayment() {
        totalPayments.incrementAndGet();  // Thread-safe
    }
    
    public int getTotal() {
        return totalPayments.get();  // Thread-safe
    }
}
```

### Common Atomic Classes

```java
AtomicInteger counter = new AtomicInteger(0);
counter.incrementAndGet();      // ++counter
counter.decrementAndGet();      // --counter
counter.addAndGet(5);           // += 5
counter.compareAndSet(0, 5);    // Compare-then-set atomically

AtomicReference<String> ref = new AtomicReference<>("initial");
ref.set("new value");           // Thread-safe update
String value = ref.get();       // Thread-safe read

AtomicLong atomicLong = new AtomicLong(0L);
```

## Solution 4: Use ConcurrentHashMap

```java
@Component
public class CacheService {
    // ✅ Thread-safe HashMap
    private final ConcurrentHashMap<String, Object> cache = 
        new ConcurrentHashMap<>();
    
    public void put(String key, Object value) {
        cache.put(key, value);  // Thread-safe
    }
    
    public Object get(String key) {
        return cache.get(key);  // Thread-safe
    }
}
```

## Solution 5: Use Synchronization

```java
@Component
public class PaymentCounter {
    private int totalPayments = 0;
    
    // ✅ Synchronized - only one thread at a time
    public synchronized void recordPayment() {
        totalPayments++;
    }
    
    public synchronized int getTotal() {
        return totalPayments;
    }
}
```

### Synchronized Block (Lower-Level)

```java
@Component
public class PaymentCounter {
    private int totalPayments = 0;
    
    public void recordPayment() {
        synchronized (this) {  // Lock on this object
            totalPayments++;  // Only one thread here
        }
    }
    
    public int getTotal() {
        synchronized (this) {
            return totalPayments;
        }
    }
}
```

### Lock Objects (More Control)

```java
@Component
public class PaymentCounter {
    private int totalPayments = 0;
    private final Object lock = new Object();  // Lock object
    
    public void recordPayment() {
        synchronized (lock) {  // Lock on separate object
            totalPayments++;
        }
    }
    
    public int getTotal() {
        synchronized (lock) {
            return totalPayments;
        }
    }
}
```

## Solution 6: Use ReentrantReadWriteLock

```java
@Component
public class CacheService {
    private final Map<String, String> cache = new HashMap<>();
    private final ReadWriteLock lock = new ReentrantReadWriteLock();
    
    public void put(String key, String value) {
        lock.writeLock().lock();
        try {
            cache.put(key, value);  // Multiple threads can read
        } finally {
            lock.writeLock().unlock();
        }
    }
    
    public String get(String key) {
        lock.readLock().lock();
        try {
            return cache.get(key);  // Multiple readers OK
        } finally {
            lock.readLock().unlock();
        }
    }
}
```

## Comparison

| Approach | Thread-Safe? | Performance | When to Use |
|----------|-------------|-------------|-----------|
| Stateless | ✅ YES | ⚡ Fastest | 95% of services |
| Immutable | ✅ YES | ⚡ Fast | Read-only data |
| AtomicInteger | ✅ YES | ⚡ Fast | Simple counters |
| ConcurrentHashMap | ✅ YES | ⚡ Fast | Caches |
| synchronized | ✅ YES | 🐌 Slow | Legacy code |
| ReadWriteLock | ✅ YES | 📊 Medium | Heavy reads |

## Real Example: Bad vs Good

### ❌ BAD: Mutable singleton

```java
@Component
public class OrderProcessor {
    private Order currentOrder;  // ⚠️ Shared state
    private String currentUser;   // ⚠️ Shared state
    
    public void process(Order order, String user) {
        this.currentOrder = order;
        this.currentUser = user;
        // Thread 2 could change these while thread 1 is processing!
        validateOrder(currentOrder, currentUser);
        persistOrder(currentOrder);
    }
}
```

### ✅ GOOD: Stateless singleton

```java
@Component
public class OrderProcessor {
    // NO instance state
    @Autowired private OrderValidator validator;
    @Autowired private OrderRepository repo;
    
    public void process(Order order, String user) {
        // All variables are local - thread-safe
        validator.validate(order, user);  // Local parameters
        repo.save(order);
    }
}
```

## Interview Tip

"The best way to make singleton beans thread-safe is to make them STATELESS - no instance variables. If you need state, use immutable objects, AtomicInteger for counters, or ConcurrentHashMap for maps. Avoid synchronized blocks if possible - they hurt performance. 95% of Spring beans should be stateless (services, controllers, etc). Use prototype or request scope for stateful beans instead of trying to make singletons thread-safe."

## Quick Checklist

- ✅ Stateless = BEST solution (no shared state)
- ✅ Immutable objects are inherently thread-safe
- ✅ AtomicInteger, AtomicReference for simple state
- ✅ ConcurrentHashMap instead of HashMap
- ✅ synchronized methods/blocks for old code
- ✅ ReadWriteLock for heavy read scenarios
- ✅ Avoid synchronized if possible (slow)
- ✅ Most services should be stateless singletons

---

**Next:** Study Q4 on singleton vs ThreadLocal
