# Q2: Object Eligibility for Garbage Collection

**Study Time:** 10-12 minutes | **Interview Frequency:** 90% | **Difficulty:** ⭐⭐⭐

---

## 🤔 The Core Question

**"When exactly does an object become eligible for garbage collection?"**

This is a **critical discriminator** in senior interviews. Many developers know "set it to null" but cannot explain **reachability** properly.

---

## 🧠 Simple Explanation

### The Golden Rule

> **An object becomes garbage when it loses ALL connections to the Stack**

Why Stack?
- Stack = Active program execution
- If Stack cannot reach an object → Object is dead

---

## 📊 Visual Understanding

### Scenario 1: Direct Reference Loss

**Before:**
```
Stack          Heap
-----         ------
p    ------>  Person
```

**Code:**
```java
Person p = new Person();
p = null;  // Break connection
```

**After:**
```
Stack          Heap
-----         ------
p = null      Person (orphan ❌)
```

**Result:** Person object eligible for GC ✅

---

### Scenario 2: Reassignment

**Before:**
```
Stack          Heap
-----         ------
p    ------>  Person(1)
```

**Code:**
```java
Person p = new Person();  // Person(1)
p = new Person();         // Person(2) - reassign!
```

**After:**
```
Stack          Heap
-----         ------
p    ------>  Person(2)
              Person(1) (orphan ❌)
```

**Result:** Person(1) eligible for GC ✅

---

### 🔥 Scenario 3: Indirect Reference Loss (VERY IMPORTANT!)

This is where 80% of candidates fail in interviews.

**Before:**
```
Stack          Heap
-----         ------------------------
p    ------>  Person  -----> Address
                        └----> Integer(1995)
```

**Code:**
```java
Person p = new Person();
p.address = new Address();
p.birthYear = new Integer(1995);

p = null;  // Only nullify Person reference
```

**After:**
```
Stack          Heap (all orphaned!)
-----         ------------------------
p = null      Person  -----> Address  ❌
                        └----> Integer(1995)  ❌
```

**Result:** ALL THREE objects eligible for GC ✅

**Why?**
- Person references Address and Integer
- But Stack ❌→ Person
- So Stack ❌→ Address (indirect)
- So Stack ❌→ Integer (indirect)

**Interview Gold:** *"Even though Person still references Address and Integer, ALL become garbage because none are reachable from Stack. This is called indirect reachability loss."*

---

## ❌ Wrong Code vs ✅ Right Code

### Mistake 1: Thinking Nullifying Nested Objects is Needed

**❌ WRONG (Unnecessary):**
```java
Person p = new Person();
p.address = new Address();

// Unnecessarily verbose
p.address = null;  // ❌ Not needed!
p = null;
```

**✅ RIGHT:**
```java
Person p = new Person();
p.address = new Address();

p = null;  // ✅ Enough! Address also becomes eligible
```

**Why right?**  
Once Person is unreachable, Address automatically becomes unreachable too.

---

### Mistake 2: Assuming System.gc() Immediately Deletes Objects

**❌ WRONG Understanding:**
```java
Person p = new Person();
p = null;
System.gc();
System.out.println("Object deleted!");  // ❌ Not guaranteed!
```

**✅ RIGHT Understanding:**
```java
Person p = new Person();
p = null;
System.gc();  // Only a request, JVM may ignore

// Object MIGHT be deleted, or might not
// GC timing is JVM-controlled
```

**Interview line:** *"System.gc() is only a suggestion to the JVM. The actual garbage collection timing is entirely JVM-controlled and non-deterministic from the developer's perspective."*

---

### Mistake 3: Assuming Eligible = Immediately Deleted

**❌ WRONG:**
```java
Person p = new Person();
p = null;
// Object removed from memory now ❌
```

**✅ RIGHT:**
```java
Person p = new Person();
p = null;
// Object is now ELIGIBLE for GC ✅
// Actual removal happens when JVM runs GC ✅
// Could be milliseconds, seconds, or minutes later ✅
```

---

## 🎯 The Two-Phase Reality

### Phase 1: Eligibility (Developer Control)
```java
Person p = new Person();
p = null;  // ✅ Now eligible
```
- Happens immediately
- Controlled by your code

### Phase 2: Actual Collection (JVM Control)
```
JVM decides:
- When to run GC
- Which generation to collect
- Which algorithm to use
- How much memory to free
```
- Happens later
- Controlled by JVM

**Interview Tip:** Always clarify that "eligible ≠ deleted immediately"

---

## 🔄 How GC Actually Identifies Garbage (Preview)

Two steps:

### Step 1: Mark (Find Live Objects)
```
JVM scans:
1. Stack references
2. Static variables
3. Active threads
4. Follows all connections

Marks objects as: ALIVE ✅
```

### Step 2: Sweep (Remove Unmarked)
```
Everything NOT marked = Garbage
Delete them
Free memory
```

**We'll cover this deeply in Q3 (Marking) and Q4 (Sweeping)**

---

## 🧪 Complete Working Example

```java
public class GCEligibilityDemo {
    
    static class Person {
        String name;
        Address address;
        Integer birthYear;
        
        Person(String name) {
            this.name = name;
            System.out.println("Person created: " + name);
        }
        
        // finalize() called by GC before deletion (deprecated but useful for demo)
        @Override
        protected void finalize() {
            System.out.println("Person GC'd: " + name);
        }
    }
    
    static class Address {
        String city;
        
        Address(String city) {
            this.city = city;
            System.out.println("Address created: " + city);
        }
        
        @Override
        protected void finalize() {
            System.out.println("Address GC'd: " + city);
        }
    }
    
    public static void main(String[] args) {
        // Scenario 1: Direct reference loss
        System.out.println("=== Scenario 1 ===");
        Person p1 = new Person("John");
        p1 = null;  // Eligible
        
        System.gc();  // Suggest GC
        sleep(100);
        
        // Scenario 2: Indirect reference loss
        System.out.println("\n=== Scenario 2 ===");
        Person p2 = new Person("Jane");
        p2.address = new Address("NYC");
        p2.birthYear = 1995;
        
        p2 = null;  // All three eligible!
        
        System.gc();  // Suggest GC
        sleep(100);
        
        // Scenario 3: Reassignment
        System.out.println("\n=== Scenario 3 ===");
        Person p3 = new Person("Bob");
        p3 = new Person("Alice");  // Bob eligible
        
        System.gc();  // Suggest GC
        sleep(100);
        
        System.out.println("\n=== End ===");
    }
    
    static void sleep(int ms) {
        try { Thread.sleep(ms); } catch (Exception e) {}
    }
}
```

**Expected Output:**
```
=== Scenario 1 ===
Person created: John
Person GC'd: John

=== Scenario 2 ===
Person created: Jane
Address created: NYC
Person GC'd: Jane
Address GC'd: NYC

=== Scenario 3 ===
Person created: Bob
Person created: Alice
Person GC'd: Bob

=== End ===
```

**Note:** `finalize()` is deprecated in Java 9+ (use Cleaners instead), but useful for understanding GC behavior.

---

## 🎯 Interview-Ready Answer

**Question:** "When does an object become eligible for garbage collection?"

**Your Answer:**
```
An object becomes eligible for garbage collection when it loses all 
reachability from the Stack - meaning there's no path from any GC Root 
to that object.

This happens in three main scenarios:

1. Direct nullification:
   Person p = new Person();
   p = null;  // Eligible

2. Reassignment:
   p = new Person();  // Old object eligible

3. Indirect reference loss:
   Person p = new Person();
   p.address = new Address();
   p = null;  // Both Person AND Address eligible

It's important to note that eligibility is not the same as immediate 
deletion. Setting an object to null makes it eligible, but actual 
garbage collection happens later when the JVM decides to run GC. 
Calling System.gc() is only a suggestion and doesn't guarantee 
immediate collection.

In production systems, understanding eligibility helps prevent memory 
leaks, such as when static collections hold references to objects that 
should otherwise be garbage collected.
```

---

## 📋 Quick Checklist

- [ ] Can explain "reachability from Stack"
- [ ] Know setting null makes object eligible (not deleted)
- [ ] Understand indirect reference loss
- [ ] Know System.gc() doesn't guarantee immediate GC
- [ ] Can explain eligible ≠ immediately deleted
- [ ] Aware that JVM controls actual GC timing

---

## 🚨 Critical Pitfalls in Production

### Pitfall 1: Static Collection Memory Leak

**❌ Problem Code:**
```java
@Service
public class UserService {
    // Static = never GC'd
    private static List<User> allUsers = new ArrayList<>();
    
    public void registerUser(User user) {
        allUsers.add(user);  // ❌ Never removed!
    }
}
```

**What happens:**
- allUsers is static
- Static variables are GC Roots
- Stack → allUsers → User objects
- User objects NEVER become eligible
- Memory leak!

**Real Impact:** Microservice crashed after 7 days:
```
java.lang.OutOfMemoryError: Java heap space
```
500K users stored → 3GB memory leak

**✅ Solution 1: Remove Static**
```java
@Service
public class UserService {
    private List<User> activeUsers = new ArrayList<>();  // ✅ Instance variable
    
    public void registerUser(User user) {
        activeUsers.add(user);
    }
}
// When UserService instance is GC'd, activeUsers is also GC'd
```

**✅ Solution 2: Use Weak References**
```java
@Service
public class UserService {
    private static Map<String, WeakReference<User>> cache = new HashMap<>();
    
    public void cacheUser(String id, User user) {
        cache.put(id, new WeakReference<>(user));
    }
    
    public User getUser(String id) {
        WeakReference<User> ref = cache.get(id);
        return ref != null ? ref.get() : null;  // May return null if GC'd
    }
}
```

**✅ Solution 3: Use Guava Cache with Eviction**
```java
@Service
public class UserService {
    private static LoadingCache<String, User> cache = CacheBuilder.newBuilder()
        .maximumSize(10000)          // ✅ Limit size
        .expireAfterAccess(1, TimeUnit.HOURS)  // ✅ Auto evict
        .build(new CacheLoader<String, User>() {
            public User load(String id) {
                return loadUser(id);
            }
        });
}
```

---

### Pitfall 2: Thread-Local Memory Leak

**❌ Problem Code:**
```java
@Component
public class RequestContext {
    private static ThreadLocal<User> currentUser = new ThreadLocal<>();
    
    public void setUser(User user) {
        currentUser.set(user);  // ❌ Never removed!
    }
}
```

**What happens in thread pools (like Tomcat):**
```
Thread 1: Request 1 → currentUser.set(user1)
Thread 1: Request ends, but Thread 1 reused
Thread 1: Request 2 → user1 still referenced!
```

**Result:**
- ThreadLocal holds reference
- User objects never GC'd
- Memory leak per thread

**Real Impact:** Payment API in production:
- 200 threads × 50 requests/thread
- Each request leaked 100KB
- After 24 hours: 200 × 50 × 100KB = 1GB leak
- Pod killed by Kubernetes (OOMKilled)

**✅ Solution:**
```java
@Component
public class RequestContext {
    private static ThreadLocal<User> currentUser = new ThreadLocal<>();
    
    public void setUser(User user) {
        currentUser.set(user);
    }
    
    public void clear() {
        currentUser.remove();  // ✅ CRITICAL!
    }
}

@RestController
public class OrderController {
    @Autowired
    private RequestContext context;
    
    @PostMapping("/order")
    public ResponseEntity<?> createOrder(@RequestBody OrderRequest req) {
        try {
            context.setUser(req.getUser());
            // Process order...
            return ResponseEntity.ok("Success");
        } finally {
            context.clear();  // ✅ Always clean up!
        }
    }
}
```

**Better: Use Spring's RequestScope**
```java
@Component
@RequestScope  // ✅ Auto-cleaned after request
public class RequestContext {
    private User currentUser;
    
    // No ThreadLocal needed!
}
```

---

### Pitfall 3: Event Listener Memory Leak

**❌ Problem Code:**
```java
public class UserUI extends JFrame {
    private DataService service;
    
    public UserUI(DataService service) {
        this.service = service;
        service.addListener(new DataListener() {  // ❌ Anonymous class
            @Override
            public void onDataChange(Data data) {
                updateUI(data);
            }
        });
    }
}
```

**What happens:**
- Anonymous listener holds reference to `this` (UserUI)
- Service holds reference to listener
- Even when UserUI closed, Service → Listener → UserUI
- UserUI never GC'd!

**Real Impact:** Desktop app memory grew from 50MB to 2GB after opening/closing windows 100 times.

**✅ Solution:**
```java
public class UserUI extends JFrame {
    private DataService service;
    private DataListener listener;  // ✅ Store reference
    
    public UserUI(DataService service) {
        this.service = service;
        this.listener = new DataListener() {
            @Override
            public void onDataChange(Data data) {
                updateUI(data);
            }
        };
        service.addListener(listener);
    }
    
    // ✅ Remove listener when closing
    @Override
    public void dispose() {
        service.removeListener(listener);  // ✅ Critical!
        super.dispose();
    }
}
```

---

## 🔄 Follow-Up Questions & Answers

### Q1: "What if two objects reference each other but nothing else references them?"

**Answer:**
```
Both objects become eligible for garbage collection.

Example:
A → B
B → A
But: Stack ❌→ A and Stack ❌→ B

Even though A and B reference each other, if there's no path from the 
Stack to either of them, both are garbage. This is called an "Island of 
Isolation".

Modern JVMs use reachability analysis (not reference counting) to 
handle this correctly. We'll cover this in detail in Q3: GC Marking 
Phase.

Code example:
class Node {
    Node next;
}

Node a = new Node();
Node b = new Node();
a.next = b;
b.next = a;  // Circular reference

a = null;
b = null;  // Both now eligible, despite circular reference!
```

---

### Q2: "Can an object become eligible and then reachable again?"

**Answer:**
```
Yes, in rare cases during finalization (but this is deprecated).

Scenario: Object resurrection

class Person {
    static Person resurrected;
    
    @Override
    protected void finalize() {
        resurrected = this;  // ❌ Resurrect! (Anti-pattern)
    }
}

Person p = new Person();
p = null;  // Eligible
// GC runs, calls finalize()
// Now: Person.resurrected → Person object
// Object is reachable again!

However:
1. finalize() is deprecated in Java 9+
2. Resurrection is an anti-pattern
3. finalize() called only ONCE per object
4. Second GC will collect it permanently

Modern alternative: Use java.lang.ref.Cleaner instead of finalize().

Production recommendation: Never rely on finalization. Clean up 
resources explicitly in finally blocks or try-with-resources.
```

---

### Q3: "difference between eligible and collected?"

**Answer:**
```
Eligible = Object loses all references (developer controlled)
Collected = Object removed from memory (JVM controlled)

Timeline:
Time 0ms: p = null → Eligible ✅
Time ???: JVM runs GC → Collected ✅

The gap between eligibility and collection depends on:
- Heap usage (low usage = less GC)
- Which generation object is in (Young vs Old)
- GC algorithm chosen
- Application allocation rate
- JVM tuning flags

Example timing:
- Young Gen object: Usually collected within seconds
- Old Gen object: Might survive minutes or hours
- Low memory pressure: Might never be collected until app shutdown!

Production implication:
Never write code assuming immediate collection:

❌ Wrong:
p = null;
// Assume memory freed

✅ Right:
p = null;
// Memory will be freed eventually by GC
```

---

### Q4: "How do Weak/Soft/Phantom references affect eligibility?"

**Answer:**
```
Java provides special reference types that alter GC behavior:

1. Strong Reference (default)
   Person p = new Person();
   → Never GC'd while p exists
   
2. Weak Reference
   WeakReference<Person> ref = new WeakReference<>(new Person());
   → GC'd in next GC cycle if only weak refs exist
   
3. Soft Reference
   SoftReference<Person> ref = new SoftReference<>(new Person());
   → GC'd only when memory is low
   
4. Phantom Reference
   PhantomReference<Person> ref = new PhantomReference<>(new Person(), queue);
   → Used for cleanup notification, not for accessing object

Eligibility rules:
- Strong reference exists → NOT eligible
- Only weak references exist → Eligible immediately
- Only soft references exist → Eligible when memory low
- Only phantom references exist → Eligible immediately

Use cases:
- Caches: Soft (cleared under memory pressure)
- Listeners: Weak (auto-cleanup)
- Resource tracking: Phantom (cleanup notification)

Example (Guava Cache):
Cache uses Soft references internally, so entries auto-evicted when 
heap fills up, preventing OutOfMemoryError.
```

---

### Q5: "Does setting object fields to null help GC?"

**Answer:**
```
Usually NO, it's unnecessary and makes code messy.

❌ Unnecessary:
Person p = new Person();
p.address = new Address();
p.birthYear = 1995;

p.address = null;     // ❌ Not needed
p.birthYear = null;   // ❌ Not needed
p = null;

✅ Sufficient:
Person p = new Person();
p.address = new Address();
p.birthYear = 1995;

p = null;  // ✅ Enough! address and birthYear also eligible

Exception: When it DOES help:
1. Long-lived objects with unnecessary references
   class Service {
       private HugeObject cache;  // Used only during startup
       
       public void afterStartup() {
           cache = null;  // ✅ Helpful! (Still long-lived)
       }
   }

2. Collection clearing
   List<Order> orders = new ArrayList<>();
   // ... add many orders
   orders.clear();  // ✅ Helpful! (Makes elements eligible)

General rule: Only null out fields if:
- Object stays alive but field no longer needed
- Field holds large object
- Field won't be used for long time

Otherwise: Let GC handle it automatically when parent object becomes 
unreachable.
```

---

## 🎓 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Reachability from Stack | Core GC concept | ⭐⭐⭐⭐⭐ |
| Eligible ≠ Deleted | Common misconception | ⭐⭐⭐⭐⭐ |
| Indirect reference loss | 80% fail this | ⭐⭐⭐⭐⭐ |
| Static collection leaks | #1 production issue | ⭐⭐⭐⭐⭐ |
| ThreadLocal cleanup | Critical in servers | ⭐⭐⭐⭐ |

---

## 🔗 What's Next?

Now that you understand **when objects become eligible**, learn **how JVM identifies them**:
- [Q3: GC Marking Phase](Q3_gc_marking_phase.md) - GC Roots, Islands of Isolation, Reachability Analysis

---

**Last Updated:** March 1, 2026
