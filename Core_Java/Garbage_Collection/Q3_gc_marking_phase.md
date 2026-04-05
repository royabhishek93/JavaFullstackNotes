# Q3: GC Marking Phase - Finding Live Objects

**Study Time:** 12-15 minutes | **Interview Frequency:** 85% | **Difficulty:** ⭐⭐⭐⭐

---

## 🤔 The Core Question

**"How does the JVM identify which objects are still alive during garbage collection?"**

This is a **senior-level discriminator**. Understanding Mark & Sweep is critical for optimizing production applications and understanding STW (Stop-The-World) pauses.

---

## 🧠 Simple Explanation

### The Marking Algorithm

> **GC starts from GC Roots and marks every object it can reach. Anything unmarked = Garbage.**

Think of it like a treasure hunt:
1. Start from all GC Roots (Stack, Static variables, Active threads)
2. Mark each object found ✅
3. Follow references to other objects
4. Mark them too ✅
5. Continue until no more objects found
6. Everything **not marked** = Garbage 🗑️

---

## 📊 Visual Understanding

### Example Object Graph

```
GC Roots (Stack + Static):
  ↓
  p → Person → Address
       ↓
     List → [Order1, Order2]
  
  q → null
  
Orphan → LostObject  (unreachable!)
```

**Marking Process:**

**Step 1:** Start from GC Roots
```
Stack: p (reference exists) ✅
Stack: q = null (skip)
```

**Step 2:** Mark objects directly reachable
```
Person ✅ (reachable from p)
```

**Step 3:** Mark objects indirectly reachable
```
Address ✅ (reachable from Person)
List ✅ (reachable from Person)
Order1 ✅ (reachable from List)
Order2 ✅ (reachable from List)
```

**Step 4:** Identify unmarked objects
```
LostObject ❌ (unreachable from any GC Root)
```

**Result:**
- Marked Objects: Person, Address, List, Order1, Order2 → **KEEP**
- Unmarked Objects: LostObject → **DELETE** in Sweep phase

---

## 🔑 GC Roots: The Starting Points

### What Are GC Roots?

**GC Roots** = Objects that are **definitely alive** and serve as starting points for reachability analysis.

### The Four Main GC Roots

#### 1. **Local Variables (Stack)**

```java
public void processOrder() {
    Order order = new Order();  // ✅ GC Root (on Stack)
    // order is alive while this method runs
}
// Method exits → order removed from Stack → no longer GC Root
```

#### 2. **Static Variables**

```java
public class Config {
    private static Database db = new Database();  // ✅ GC Root (static)
}
// db is a GC Root until:
// - Class unloaded
// - Application shutdown
```

#### 3. **Active Threads**

```java
Thread thread = new Thread(() -> {
    // This thread object is a GC Root
});
thread.start();  // ✅ GC Root while running
thread.join();   // Finished → no longer GC Root
```

#### 4. **JNI References**

```java
// Native code holding Java object references
JNIEXPORT void JNICALL Java_MyClass_nativeMethod(JNIEnv *env, jobject obj) {
    // obj is a GC Root
}
```

**Interview Tip:** Most questions focus on 1 & 2 (Stack and Static).

---

## 🎯 Reachability Analysis vs Reference Counting

### ❌ Old Approach: Reference Counting (C++, Python pre-3.4)

**How it works:**
- Each object has a counter
- Reference added → counter++
- Reference removed → counter--
- Counter = 0 → Delete object

**Problem:** Circular references!

```java
A → B
B → A
Both have counter = 1, but unreachable from Stack → Memory leak!
```

**This is why C++ requires manual delete and smart pointers.**

---

### ✅ Modern Approach: Reachability Analysis (Java, C#, Go)

**How it works:**
- Start from GC Roots
- Mark everything reachable
- Delete everything NOT marked

**Advantage:** Handles circular references correctly!

```java
A → B
B → A
But: Stack ❌→ A and Stack ❌→ B
Result: Both unmarked → Both deleted ✅
```

**Interview Gold:** *"Java uses reachability analysis, not reference counting, so circular references are not a problem. If two objects point to each other but are unreachable from any GC Root, both will be garbage collected."*

---

## 🏝️ Islands of Isolation: The Circle Problem

### Scenario

```java
class Node {
    Node next;
    String data;
    
    Node(String data) {
        this.data = data;
    }
}

public void createIsland() {
    Node a = new Node("A");
    Node b = new Node("B");
    Node c = new Node("C");
    
    // Create circular references
    a.next = b;
    b.next = c;
    c.next = a;  // Circle!
    
    // Now break external reference
    a = null;
    b = null;
    c = null;
}
```

**Visual:**

**Before nullification:**
```
Stack → a → Node(A) → Node(B) → Node(C)
                ↑__________________|
```

**After nullification:**
```
Stack (empty)

        Node(A) → Node(B) → Node(C)
           ↑__________________|
        
        (Island of Isolation!)
```

**Marking Process:**
1. Start from GC Roots (Stack)
2. Stack is empty
3. No references to Node(A), Node(B), or Node(C)
4. All three remain **unmarked**
5. Result: All three deleted in Sweep phase ✅

**This is called an "Island of Isolation" - objects referencing each other but isolated from GC Roots.**

---

## ❌ Wrong Code vs ✅ Right Code

### Mistake 1: Assuming Circular References Prevent GC

**❌ WRONG Understanding:**

```java
// Developer thinks: "These objects will never be GC'd because they
// reference each other"

class Task {
    Task dependency;
}

Task t1 = new Task();
Task t2 = new Task();
t1.dependency = t2;
t2.dependency = t1;

t1 = null;
t2 = null;

// ❌ Wrong: "Memory leak! They reference each other!"
```

**✅ RIGHT Understanding:**

```java
// Both Task objects become eligible for GC

class Task {
    Task dependency;
}

Task t1 = new Task();
Task t2 = new Task();
t1.dependency = t2;
t2.dependency = t1;

t1 = null;
t2 = null;

// ✅ Right: "Both GC'd! Reachability analysis handles circular refs."
```

**Why right?** JVM uses reachability, not reference counting. Both tasks are unreachable from GC Roots, so both are garbage.

---

### Mistake 2: Not Understanding GC Roots

**❌ WRONG Understanding:**

```java
class Service {
    private User currentUser;  // Instance variable
    
    public void login(User user) {
        this.currentUser = user;
        // ❌ Wrong thinking: "currentUser is now a GC Root"
    }
}
```

**✅ RIGHT Understanding:**

```java
class Service {
    private User currentUser;  // Instance variable, NOT a GC Root
    
    public void login(User user) {
        this.currentUser = user;
        // ✅ Right: "currentUser is only reachable if Service instance
        //           is reachable from a GC Root"
    }
}

// GC Root path:
Stack → Service instance → currentUser
// If Service instance becomes unreachable, currentUser also becomes unreachable
```

**GC Roots vs Regular References:**
- **GC Root:** Stack variables, static variables (starting points)
- **Regular Reference:** Instance variables (intermediate links)

---

### Mistake 3: Misunderstanding Static Variables

**❌ WRONG Understanding:**

```java
class UserCache {
    private static List<User> users = new ArrayList<>();
    
    public void addUser(User user) {
        users.add(user);
        // ❌ Wrong thinking: "User will be GC'd when no longer needed"
    }
}
```

**What actually happens:**
```
Static 'users' is a GC Root
↓
List object
↓
User objects

ALL User objects are reachable from GC Root → Never GC'd!
```

**✅ RIGHT Approach:**

```java
class UserCache {
    // Option 1: Remove static
    private List<User> users = new ArrayList<>();
    
    // Option 2: Explicitly clear
    private static List<User> users = new ArrayList<>();
    
    public void clearCache() {
        users.clear();  // ✅ Remove references
    }
    
    // Option 3: Use Weak/Soft references
    private static Map<String, WeakReference<User>> users = new HashMap<>();
}
```

---

## 🧪 Complete Working Example: Visualizing Marking

```java
public class MarkingPhaseDemo {
    
    // Static = GC Root
    static Node staticRoot = new Node("StaticRoot");
    
    static class Node {
        String name;
        Node next;
        
        Node(String name) {
            this.name = name;
            System.out.println("Created: " + name);
        }
        
        @Override
        protected void finalize() throws Throwable {
            System.out.println("GC'd: " + name);
        }
    }
    
    public static void main(String[] args) throws InterruptedException {
        System.out.println("=== Scenario 1: Simple Chain ===");
        simpleChain();
        
        System.out.println("\n=== Scenario 2: Island of Isolation ===");
        islandOfIsolation();
        
        System.out.println("\n=== Scenario 3: Partial Chain ===");
        partialChain();
    }
    
    static void simpleChain() throws InterruptedException {
        // Stack GC Root
        Node root = new Node("Root");
        root.next = new Node("Child1");
        root.next.next = new Node("Child2");
        
        // Marking:
        // Stack → Root ✅ → Child1 ✅ → Child2 ✅
        
        System.out.println("All reachable from Stack");
        
        // Break chain
        root = null;
        
        // Now:
        // Stack (empty)
        // Root ❌ → Child1 ❌ → Child2 ❌
        
        System.gc();
        Thread.sleep(100);
        // All should be GC'd
    }
    
    static void islandOfIsolation() throws InterruptedException {
        // Create circular reference
        Node a = new Node("A");
        Node b = new Node("B");
        Node c = new Node("C");
        
        a.next = b;
        b.next = c;
        c.next = a;  // Circle
        
        System.out.println("Circular reference created");
        
        // Break external references
        a = null;
        b = null;
        c = null;
        
        // Marking:
        // Stack (empty)
        // A → B → C → A (unreachable island)
        // All unmarked ❌
        
        System.gc();
        Thread.sleep(100);
        // All should be GC'd despite circular references
    }
    
    static void partialChain() throws InterruptedException {
        // Stack GC Root
        Node root = new Node("Root");
        root.next = new Node("ToDelete");
        root.next.next = new Node("AlsoDelete");
        
        // Marking:
        // Stack → Root ✅ → ToDelete ✅ → AlsoDelete ✅
        
        // Now break middle of chain
        root.next = null;
        
        // Now:
        // Stack → Root ✅
        // ToDelete ❌ → AlsoDelete ❌
        
        System.out.println("Root still reachable, but children orphaned");
        
        System.gc();
        Thread.sleep(100);
        // ToDelete and AlsoDelete should be GC'd
        // Root should survive
    }
}
```

**Expected Output:**
```
=== Scenario 1: Simple Chain ===
Created: Root
Created: Child1
Created: Child2
All reachable from Stack
GC'd: Child2
GC'd: Child1
GC'd: Root

=== Scenario 2: Island of Isolation ===
Created: A
Created: B
Created: C
Circular reference created
GC'd: C
GC'd: B
GC'd: A

=== Scenario 3: Partial Chain ===
Created: Root
Created: ToDelete
Created: AlsoDelete
Root still reachable, but children orphaned
GC'd: AlsoDelete
GC'd: ToDelete
```

**Observation:** Even circular references (A→B→C→A) are correctly identified as garbage when unreachable from GC Roots.

---

## 🎯 Interview-Ready Answer

**Question:** "Explain how the JVM identifies live objects during GC marking phase."

**Your Answer:**
```
The JVM uses a reachability analysis algorithm starting from GC Roots. 
The process works in four steps:

1. Identify GC Roots: These are the starting points - local variables 
   on the Stack, static variables, active threads, and JNI references. 
   These objects are guaranteed to be alive.

2. Traverse object graph: Starting from each GC Root, the GC follows 
   all references and marks each reachable object as "alive".

3. Recursive marking: For each marked object, the GC examines its 
   fields and marks any referenced objects, continuing recursively.

4. Identify garbage: After marking completes, any object NOT marked is 
   considered garbage and will be deleted in the sweep phase.

This is called reachability analysis, not reference counting. The key 
advantage is that circular references are handled correctly - if two 
objects reference each other but neither is reachable from a GC Root, 
both are correctly identified as garbage. This scenario is called an 
"Island of Isolation".

In production systems, the marking phase causes Stop-The-World pauses 
because the JVM must freeze application threads to ensure a consistent 
snapshot of the object graph. Modern collectors like G1 and ZGC 
minimize these pauses through concurrent marking, but young generation 
collections still typically require full STW pauses.
```

---

## 📋 Quick Checklist

- [ ] Can list the four types of GC Roots
- [ ] Understand reachability analysis vs reference counting
- [ ] Can explain Islands of Isolation
- [ ] Know that circular references are NOT a problem in Java
- [ ] Understand marking causes Stop-The-World pauses
- [ ] Can draw object graph showing reachable/unreachable objects

---

## 🚨 Critical Pitfalls in Production

### Pitfall 1: Static Collections Growing Indefinitely

**❌ Problem Code:**
```java
@Service
public class EventTracker {
    // Static = GC Root forever
    private static List<Event> allEvents = new ArrayList<>();
    
    @EventListener
    public void onApplicationEvent(Event event) {
        allEvents.add(event);  // ❌ Never removed!
    }
}
```

**Marking Analysis:**
```
GC Roots:
  Static 'allEvents' (GC Root) → List → Event[0] ✅
                                       → Event[1] ✅
                                       → Event[2] ✅
                                       ... (all marked, none GC'd)
```

**Real Impact:** E-commerce application:
- 1 million transactions/day
- Each Event object = 2KB
- After 7 days: 1M × 7 × 2KB = 14GB
- Pod killed: **OOMKilled**

**Logs:**
```
java.lang.OutOfMemoryError: Java heap space
java.lang.OutOfMemoryError: GC overhead limit exceeded
```

**✅ Solution 1: Remove Static**
```java
@Service
public class EventTracker {
    private List<Event> recentEvents = new ArrayList<>();  // ✅ Instance variable
    
    @EventListener
    public void onApplicationEvent(Event event) {
        recentEvents.add(event);
        // When EventTracker instance GC'd → recentEvents also GC'd
    }
}
```

**✅ Solution 2: Size-Limited Cache**
```java
@Service
public class EventTracker {
    private static final int MAX_SIZE = 1000;
    private static Queue<Event> recentEvents = new ConcurrentLinkedQueue<>();
    
    @EventListener
    public void onApplicationEvent(Event event) {
        recentEvents.offer(event);
        if (recentEvents.size() > MAX_SIZE) {
            recentEvents.poll();  // ✅ Remove oldest
        }
    }
}
```

**✅ Solution 3: Expiring Cache (Best)**
```java
@Service
public class EventTracker {
    private static LoadingCache<String, Event> cache = CacheBuilder.newBuilder()
        .maximumSize(10000)
        .expireAfterWrite(1, TimeUnit.HOURS)
        .build(CacheLoader.from(() -> null));
    
    @EventListener
    public void onApplicationEvent(Event event) {
        cache.put(event.getId(), event);
        // Auto-evicted after 1 hour ✅
    }
}
```

---

### Pitfall 2: Long GC Pauses Due to Large Object Graphs

**❌ Problem Code:**
```java
@Service
public class OrderService {
    @Autowired
    private EntityManager em;
    
    public List<Order> getAllOrders() {
        // Loads 1 million orders with associations
        return em.createQuery("SELECT o FROM Order o " +
                            "JOIN FETCH o.items " +
                            "JOIN FETCH o.customer " +
                            "JOIN FETCH o.address", Order.class)
                 .getResultList();  // ❌ Huge object graph!
    }
}
```

**What happens:**
```
1 million Orders
  → 5 million OrderItems
  → 1 million Customers
  → 1 million Addresses

Total: 8 million objects in memory!

GC Marking Phase:
- Must traverse all 8 million objects
- Mark each one
- Takes seconds → Long STW pause!
```

**Real Impact:** Admin dashboard in production:
- Export all orders API called
- GC pause: **3.5 seconds**
- All requests blocked during STW
- Timeout errors for other users

**Logs:**
```
[GC pause (G1 Evacuation Pause) (young) 3500ms]
Application paused for 3.5 seconds
```

**✅ Solution 1: Pagination**
```java
@Service
public class OrderService {
    @Autowired
    private EntityManager em;
    
    public List<Order> getOrders(int page, int size) {
        return em.createQuery("SELECT o FROM Order o", Order.class)
                 .setFirstResult(page * size)
                 .setMaxResults(size)  // ✅ Limit to 100 orders
                 .getResultList();
    }
}
```

**✅ Solution 2: Streaming (Best for Large Datasets)**
```java
@Service
public class OrderService {
    @Autowired
    private EntityManager em;
    
    @Transactional(readOnly = true)
    public Stream<Order> streamOrders() {
        return em.createQuery("SELECT o FROM Order o", Order.class)
                 .setHint(QueryHints.HINT_FETCH_SIZE, 100)
                 .getResultStream();  // ✅ Stream, don't load all
    }
}

// Usage:
orderService.streamOrders()
    .forEach(order -> processOrder(order));
    // Each batch of 100 processed separately
    // Old objects GC'd while streaming continues
```

**✅ Solution 3: Database-Side Export**
```java
@Service
public class OrderService {
    @Autowired
    private JdbcTemplate jdbc;
    
    public void exportOrders(OutputStream out) {
        jdbc.query("SELECT * FROM orders", rs -> {
            // Write directly to output stream
            // Never load all into memory ✅
            writeCsvRow(out, rs);
        });
    }
}
```

---

### Pitfall 3: ThreadLocal Preventing GC

**❌ Problem Code:**
```java
@Component
public class RequestContext {
    private static ThreadLocal<Session> session = new ThreadLocal<>();
    
    public void initSession(User user) {
        Session s = new Session(user);
        s.data = loadUserData(user);  // Large object!
        session.set(s);
    }
}
```

**Marking Analysis:**
```
GC Roots:
  Thread (GC Root while alive)
    → ThreadLocalMap
      → Entry
        → Session ✅
          → User ✅
          → data (10MB) ✅

Even after request ends, Thread reused in pool:
  Thread still alive → ThreadLocal still reachable → Session never GC'd!
```

**Real Impact:** Payment service:
- 200 threads in Tomcat
- Each request leaked 10MB Session
- After 100 requests: 200 × 10MB = 2GB leaked
- After 24 hours: Pod restarted due to OOM

**✅ Solution:**
```java
@Component
public class RequestContext {
    private static ThreadLocal<Session> session = new ThreadLocal<>();
    
    public void initSession(User user) {
        Session s = new Session(user);
        session.set(s);
    }
    
    public void clearSession() {
        session.remove();  // ✅ CRITICAL!
    }
}

@RestController
public class PaymentController {
    @Autowired
    private RequestContext context;
    
    @PostMapping("/payment")
    public ResponseEntity<?> processPayment(@RequestBody PaymentRequest req) {
        try {
            context.initSession(req.getUser());
            // Process payment
            return ResponseEntity.ok("Success");
        } finally {
            context.clearSession();  // ✅ Always clear!
        }
    }
}

// Or use Spring's @RequestScope (better):
@Component
@RequestScope  // ✅ Auto-cleaned after request
public class RequestContext {
    private Session session;  // No ThreadLocal needed!
}
```

---

## 🔄 Follow-Up Questions & Answers

### Q1: "What happens during marking if object graph is modified?"

**Answer:**
```
This is why marking requires a Stop-The-World (STW) pause.

Problem without STW:
Time 1: GC marks object A ✅
Time 2: App deletes A's reference to B
Time 3: GC tries to mark B via A → Crash or incorrect marking!

Solution: STW pause
1. GC signals all application threads to pause
2. Threads reach safepoint and pause
3. GC performs marking (consistent snapshot)
4. GC resumes threads

Modern collectors (G1, ZGC) use concurrent marking:
- Most marking happens concurrently (no pause)
- Only initial setup and final remarks are STW
- Uses write barriers to track changes during concurrent phase

Example timing:
- Young GC: 10-50ms STW (entire pause)
- G1 Old GC: 100-200ms STW (marking) + 1-2s concurrent
- ZGC Old GC: <10ms STW + concurrent marking

Production tip: Monitor GC logs for long STW pauses indicating 
oversized heaps or inefficient object graphs.
```

---

###Q2: "How does GC handle objects promoted to Old Gen during marking?"

**Answer:**
```
This is called "floating garbage" - objects that become garbage 
during GC but aren't collected.

Scenario:
1. Young GC starts marking
2. Object A is live, promoted to Old Gen
3. During marking, A's references are nullified
4. A is now garbage, but already promoted!

Result: A survives this GC cycle, collected in next cycle.

Why it happens:
- GC takes snapshot at start
- Objects alive at snapshot time are kept
- Changes during GC are ignored (for consistency)

Impact:
- Slightly more memory used temporarily
- Next GC cycle will collect it
- Not a memory leak, just delayed collection

Modern collectors handle this better:
- Concurrent marking can detect some floating garbage
- G1's remembered sets track inter-region pointers
- ZGC's colored pointers track object states

Production: This is normal behavior, not a concern unless you see 
heap growing continuously (true leak). "Floating garbage" is 
collected in subsequent GC cycles.
```

---

### Q3: "Can you explain tri-color marking algorithm?"

**Answer:**
```
Tri-color marking is used by concurrent collectors (G1, ZGC, Shenandoah) 
to track marking progress.

Three colors:
1. White: Not yet examined (assume garbage)
2. Gray: Marked, but children not yet examined
3. Black: Marked, and all children examined

Algorithm:
1. Start: All objects white
2. Mark GC Roots gray
3. While gray objects exist:
   - Pick a gray object
   - Examine its references
   - Mark referenced objects gray
   - Mark this object black
4. End: Black = alive, White = garbage

Example:
Initial:
  A (white) → B (white)
  ↓
  C (white)

Step 1: A is GC Root
  A (gray) → B (white)
  ↓
  C (white)

Step 2: Process A, mark B and C
  A (black) → B (gray)
  ↓
  C (gray)

Step 3: Process B
  A (black) → B (black)
  ↓
  C (gray)

Step 4: Process C
  A (black) → B (black)
  ↓
  C (black)

All black = all live objects identified!

Concurrent marking challenge:
- App thread: A.child = null; B.child = D;
- Now D reachable via B, but if B already processed (black) → D stays white!

Solution: Write barriers
- When app thread modifies black object
- Re-mark it as gray
- GC will re-scan it

This is why concurrent GC has small STW pauses despite most work being 
concurrent - need consistent view for final marking.
```

---

### Q4: "What are safepoints and why needed for GC?"

**Answer:**
```
Safepoint = A point in code where thread state is consistent and can 
be examined safely.

Why needed:
- GC needs to find GC Roots on Stack
- Can't examine Stack while thread is running (inconsistent state)
- Thread must reach safepoint before pausing

Where are safepoints?
- Method return
- Loop backedge (end of loop iteration)
- Before method call
- NOT in the middle of instruction

Example:

void processOrders() {
    for (Order o : orders) {  // ← Safepoint (loop backedge)
        processOrder(o);       // ← Safepoint (method call)
    }
}  // ← Safepoint (method return)

Safepoint pause process:
1. GC decides to run
2. Signals all threads to pause
3. Each thread continues until next safepoint
4. Thread pauses at safepoint
5. Once all threads paused → GC starts

Time to safepoint problem:
- Long-running loop without safepoints
- Thread takes seconds to reach safepoint
- All other threads blocked waiting!

Example problem:
for (int i = 0; i < 1_000_000_000; i++) {
    sum += i;  // No safepoint! (counted loop optimization)
}

Solution (Java 10+):
-XX:+UseCountedLoopSafepoints  // ✅ Insert safepoints in counted loops

Production monitoring:
Look for "Time to safepoint" in GC logs:
[Times: user=0.02s sys=0.00s real=2.50s]
                                 ↑
                         2.5s to reach safepoint! (bad)

Healthy value: <10ms
Concerning: >100ms
Critical: >1s

If you see long times to safepoint, likely cause:
- Tight loops without safepoints
- Native code executing (can't be interrupted)
- Thread blocked in I/O
```

---

### Q5: "How does JVM mark large heaps efficiently?"

**Answer:**
```
Large heaps (32GB+) make full-heap marking slow. JVMs use several 
optimizations:

1. Card marking (For old-gen references to young-gen):
   - Divide memory into 512-byte "cards"
   - Write barrier marks card as "dirty" when reference updated
   - During Young GC, only scan dirty cards
   - Avoid scanning entire Old Gen

2. Parallel marking:
   - Multiple GC threads mark simultaneously
   - Each thread works on different objects
   - Join at end
   - Flag: -XX:ParallelGCThreads=8

3. Concurrent marking (G1, ZGC):
   - Most marking happens while app runs
   - Write barriers track app modifications
   - Only short STW for initial mark and remark

4. Region-based collection (G1):
   - Heap divided into regions (1-32MB each)
   - Mark regions independently
   - Collect regions with most garbage first
   - Avoid marking entire heap

5. Bitmap marking:
   - Separate bitmap tracks marked objects
   - Bit per address (not per object)
   - Fast bit operations
   - Cache-friendly

Example timings (64GB heap):
- Serial: 5-10s STW (unacceptable)
- Parallel: 1-2s STW (acceptable for batch apps)
- G1: 200ms STW + 2s concurrent (good for most apps)
- ZGC: 10ms STW + 2s concurrent (excellent for low-latency)

Production recommendation for heap size:
- <8GB: Parallel GC (simple, efficient)
- 8-32GB: G1 GC (balanced)
- 32GB+: ZGC or Shenandoah (low-latency)

Flags for G1 tuning:
-XX:MaxGCPauseMillis=200       # Target 200ms pause
-XX:G1HeapRegionSize=16M       # Region size
-XX:ConcGCThreads=4            # Concurrent marking threads
-XX:InitiatingHeapOccupancyPercent=45  # Start concurrent marking at 45%
```

---

## 🎓 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| GC Roots (Stack, Static) | Marking starting points | ⭐⭐⭐⭐⭐ |
| Reachability analysis | How JVM finds garbage | ⭐⭐⭐⭐⭐ |
| Islands of Isolation | Circular reference handling | ⭐⭐⭐⭐⭐ |
| STW pause during marking | Performance implications | ⭐⭐⭐⭐ |
| Static collections leak | #1 production issue | ⭐⭐⭐⭐⭐ |

---

## 🔗 What's Next?

Now that you understand **how JVM marks live objects**, learn **how it deletes garbage**:
- [Q4: GC Sweeping Phase](Q4_gc_sweeping_phase.md) - Deletion, Compaction, Fragmentation

---

**Last Updated:** March 1, 2026
