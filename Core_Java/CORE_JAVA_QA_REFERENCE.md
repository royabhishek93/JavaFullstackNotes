# Core Java - Q&A Reference Guide (Quick Interview Prep)

> **Format:** Each question → Problem → Why It Happens → Wrong vs Right Code → Interview Tip → Checklist
> 
> **Use Case:** 2-3 minute per question. Perfect for last-minute review before interviews.

---

## 📚 String Memory Allocation

### Q1: Where does `"hello"` go in memory?

**Problem:** Understanding where Java stores string literals vs runtime strings.

**Why It Happens:** 
Java has a special memory region called the **String Pool** for string literals. This saves memory by reusing identical strings.

**❌ Wrong Understanding:**
```java
String a = "hello";     // Goes to regular heap
String b = "hello";     // Also goes to regular heap
// Developers think: a and b are different objects
```

**✅ Right Understanding:**
```java
String a = "hello";           // Goes to String Pool
String b = "hello";           // Reuses same String Pool reference
System.out.println(a == b);   // true - SAME object!
```

**Interview Tip:**
"String literals go to the String Pool in memory. Multiple references to the same literal share ONE object. This is why `a == b` returns true for literals but false for `new String("hello")`."

**Quick Checklist:**
- ✅ Literals → String Pool (memory efficient)
- ✅ `new String()` → Heap (always new object)
- ✅ `+` concatenation at runtime → Heap
- ✅ `.intern()` → Moves to pool or returns pool reference

---

### Q2: Why does `c == d` return false when both are `"hi"`?

**Problem:** Confusing behavior of string equality with concatenation.

**Code Scenario:**
```java
String a = "hi";
String b = "hi";
System.out.println(a == b);  // true - literals in pool

String c = a + b;            // Runtime concatenation
String d = "hihi";           // Literal
System.out.println(c == d);  // false - Why?!
```

**Why It Happens:**
- `a + b` happens at **runtime** → result goes to **Heap**
- `"hihi"` is a **literal** → goes to **String Pool**
- Different memory regions = different objects = `==` returns false

**Visual Memory Layout:**
```
String Pool:        Heap:
┌─────────┐         ┌─────────┐
│ "hi"    │         │ "hihi"  │ ← c points here (a + b)
│ "hihi"  │ ← d     │         │
└─────────┘         └─────────┘
```

**✅ Right Way to Compare:**
```java
String c = a + b;
String d = "hihi";

// Use equals() for content comparison
System.out.println(c.equals(d));        // true ✅
System.out.println(c == d);             // false (different objects)

// If you need == to work: use intern()
System.out.println(c.intern() == d);    // true
```

**Interview Tip:**
"The `+` operator creates strings on the heap at runtime. Literals are in the pool. So `c == d` is false even though they have same content. Use `equals()` for comparison, not `==`."

**Quick Checklist:**
- ✅ `==` checks object reference (not content)
- ✅ `.equals()` checks string content
- ✅ Runtime concatenation always → Heap
- ✅ Literals always → String Pool

---

### Q3: What does `.intern()` do and when should you use it?

**Problem:** When to use `.intern()` and what it actually does.

**Code Scenario:**
```java
String str1 = new String("hello");  // Heap
String str2 = "hello";              // Pool

System.out.println(str1 == str2);   // false

// Using intern()
System.out.println(str1.intern() == str2);  // true
```

**Why It Happens:**
`.intern()` does one of two things:
- If string exists in pool → returns that reference
- If string doesn't exist → adds it to pool, returns reference

**✅ Correct Usage:**
```java
// Case 1: Dynamic string that MIGHT appear multiple times
String userInput = readFromFile();  // e.g., "userID"
String pooled = userInput.intern();
// Now if another part of code reads same value,
// pooled references will be identical

// Case 2: Large dataset with many duplicates
String[] filenames = readMillionFilenames();
for (String name : filenames) {
    String interned = name.intern();  // Saves memory if many duplicates
}
```

**❌ When NOT to use:**
```java
// DON'T - Performance killer
for (int i = 0; i < 1_000_000; i++) {
    String str = new String("ID: " + i).intern();  // Creates pool hammer
}

// DO - Just use literals
String str = "ID: " + i;  // Compiles to efficient bytecode
```

**Interview Tip:**
"`.intern()` adds a string to the pool or returns existing pool reference. Use it only when you have many string duplicates and memory is critical. Otherwise avoid it - it's slow and can cause memory issues."

**Quick Checklist:**
- ✅ Use `.intern()` only for duplicate-heavy scenarios
- ✅ Avoid loop use of `.intern()`
- ✅ Pool has finite size (PermGen/Metaspace limits)
- ✅ For most cases: use `.equals()` instead

---

### Q4: How does garbage collection work with the String Pool?

**Problem:** Do strings in the pool get garbage collected?

**Why It Happens:**
The String Pool is part of heap memory (Java 7+, in MetaSpace before). If a string has no references, GC can collect it.

**✅ Correct Understanding:**
```java
String a = "hello";      // In pool
String b = new String("world");  // In heap

a = null;    // Can be GC'd if no other refs
b = null;    // Can be GC'd immediately

// String pool entries with no refs can also be GC'd
```

**Interview Tip:**
"Yes, String Pool entries are garbage collected if there are no references. The pool is part of the heap, not a permanent memory region. However, strings created with literals may have implicit references."

**Quick Checklist:**
- ✅ String Pool is part of heap (Java 7+)
- ✅ Yes, pool strings can be GC'd
- ✅ String deduplication reduces pool size
- ✅ Long-lived pools can cause memory leaks

---

## 🔐 Immutable Classes & Defensive Copying

### Q5: What makes a class immutable?

**Problem:** Understanding all requirements for truly immutable classes.

**Why It Happens:**
Immutability requires multiple safeguards - no partial implementation works.

**❌ Wrong (Partial Immutability):**
```java
// Looks immutable but isn't!
public class Person {
    private final String name;
    private final List<String> hobbies;  // PROBLEM: List is mutable!
    
    public Person(String name, List<String> hobbies) {
        this.name = name;
        this.hobbies = hobbies;  // Direct reference - can be modified!
    }
    
    public List<String> getHobbies() {
        return hobbies;  // Client can modify list!
    }
}

// Usage - breaks immutability!
List<String> list = new ArrayList<>();
list.add("coding");
Person p = new Person("John", list);
list.add("gaming");  // Modifies p's hobbies!
```

**✅ Correct (True Immutability):**
```java
public final class Person {  // 1. Make class final
    private final String name;
    private final List<String> hobbies;  // 2. Fields final
    
    // 3. Defensive copy in constructor
    public Person(String name, List<String> hobbies) {
        this.name = name;
        this.hobbies = new ArrayList<>(hobbies);  // Copy!
    }
    
    // 4. No setter methods
    
    // 5. Defensive copy in getter
    public List<String> getHobbies() {
        return new ArrayList<>(hobbies);  // Return copy, not reference
    }
    
    // 6. Immutable alternatives
    public List<String> getHobbiesImmutable() {
        return Collections.unmodifiableList(hobbies);
    }
}

// Usage - safe!
List<String> list = new ArrayList<>();
list.add("coding");
Person p = new Person("John", list);
list.add("gaming");  // p is still immutable!
```

**Four Requirements for Immutability:**
1. **final class** - prevent extension
2. **final fields** - prevent reassignment
3. **No setters** - prevent modification
4. **Defensive copying** - prevent external modification

**Interview Tip:**
"Immutable classes need FOUR things: final class, final fields, no setters, and defensive copying in constructor and getters. Missing any one breaks immutability. String is immutable because all four requirements are met."

**Quick Checklist:**
- ✅ `public final class` - not `public class`
- ✅ `private final fields` - all mutable fields
- ✅ No setter methods at all
- ✅ Copy in constructor: `new ArrayList<>(list)`
- ✅ Copy in getter: `new ArrayList<>(list)`
- ✅ Return `Collections.unmodifiableList()` if appropriate

---

### Q6: What's the difference between `new ArrayList<>(list)` and `.clone()`?

**Problem:** Defensive copying - which method to use?

**Scenario:**
```java
List<String> original = new ArrayList<>();
original.add("item1");

List<String> copy1 = original.clone();       // Shallow copy
List<String> copy2 = new ArrayList<>(original);  // Also shallow copy
```

**Why It Happens:**
Both are shallow copies - they copy references, not nested objects.

**Deep vs Shallow Copy:**
```java
// Deep copy needed when list contains mutable objects
List<Person> people = new ArrayList<>();
people.add(new Person("John"));

// ❌ Shallow copy - person object still referenced!
List<Person> shallow = new ArrayList<>(people);
shallow.get(0).setAge(30);  // Modifies original person!

// ✅ Deep copy - new person objects
List<Person> deep = people.stream()
    .map(p -> new Person(p.getName(), p.getAge()))
    .collect(Collectors.toList());
deep.get(0).setAge(30);  // Original person unchanged
```

**Interview Tip:**
"Use `new ArrayList<>(list)` for defensive copying of immutable elements. For mutable objects in the list, do deep copy using streams or iteration. Shallow vs deep depends on what's inside the collection."

**Quick Checklist:**
- ✅ `new ArrayList<>(list)` for immutable elements
- ✅ Shallow copy = fine for String, Integer, etc.
- ✅ Deep copy needed for object collections
- ✅ `.clone()` is another option but `new ArrayList<>()` clearer

---

### Q7: How do you return mutable collections safely?

**Problem:** Exposing collections without allowing external modification.

**❌ Wrong (Unsafe):**
```java
public class Database {
    private List<User> users = new ArrayList<>();
    
    public List<User> getUsers() {
        return users;  // DANGER: Client can modify!
    }
}

// Usage - breaks data integrity!
List<User> users = db.getUsers();
users.clear();  // Clears the database!
```

**✅ Right Options:**

**Option 1: Return Copy**
```java
public List<User> getUsers() {
    return new ArrayList<>(users);  // Client gets copy
}
```

**Option 2: Return Unmodifiable View**
```java
public List<User> getUsers() {
    return Collections.unmodifiableList(users);  // View, not copy
}

// Usage
List<User> users = db.getUsers();
users.add(new User());  // Throws UnsupportedOperationException ✅
```

**Option 3: Return Stream (Java 8+)**
```java
public Stream<User> getUsers() {
    return users.stream();  // Client can process but not modify ref
}

// Usage
db.getUsers()
  .filter(u -> u.isActive())
  .forEach(System.out::println);
```

**Option 4: Return Immutable Collection (Java 9+)**
```java
public List<User> getUsers() {
    return List.copyOf(users);  // Immutable copy
}
```

**Interview Tip:**
"Return `Collections.unmodifiableList()` if you want to prevent modifications without copying. Use `new ArrayList<>(list)` if client needs a modifiable copy. Both prevent external modification of your internal state."

**Quick Checklist:**
- ✅ Never return internal collection directly
- ✅ `Collections.unmodifiableList()` - most efficient
- ✅ `new ArrayList<>(list)` - if copy needed
- ✅ `List.copyOf()` - Java 9+, truly immutable
- ✅ Stream - for functional style processing

---

## 🔄 Multithreading & Concurrency

### Q8: What is a race condition?

**Problem:** Understanding the fundamental threading issue.

**Why It Happens:**
Multiple threads access and modify the same variable without coordination = unpredictable results.

**❌ Wrong Code (Race Condition):**
```java
public class Counter {
    private int count = 0;  // Shared mutable state
    
    public void increment() {
        count++;  // NOT atomic! Has 3 steps:
                  // 1. Read: temp = count
                  // 2. Modify: temp = temp + 1
                  // 3. Write: count = temp
    }
    
    public int getCount() {
        return count;
    }
}

// Usage - unpredictable results!
Counter counter = new Counter();

Thread t1 = new Thread(() -> {
    for (int i = 0; i < 1000; i++) counter.increment();
});
Thread t2 = new Thread(() -> {
    for (int i = 0; i < 1000; i++) counter.increment();
});

t1.start();
t2.start();
t1.join();
t2.join();

System.out.println(counter.getCount());  // Prints 1234, not 2000!
```

**Race Condition Timeline:**
```
Thread 1: Read(0) → Increment → Write(1)
Thread 2:              Read(1) → Increment(?) → Write(?)
                              ↑ Problem: Read happens before Thread 1 writes
```

**✅ Fix with Synchronization:**
```java
public class Counter {
    private int count = 0;
    
    public synchronized void increment() {  // Lock added
        count++;  // Now atomic - one thread at a time
    }
    
    public synchronized int getCount() {
        return count;
    }
}

// Usage
Counter counter = new Counter();
// ... same threading code ...
System.out.println(counter.getCount());  // Always 2000 ✅
```

**Interview Tip:**
"A race condition happens when multiple threads access shared mutable state without synchronization. The result depends on the exact timing of when threads execute - unpredictable. Fix it with synchronized, locks, or immutable data."

**Quick Checklist:**
- ✅ Root cause: shared mutable state + no sync
- ✅ Result: unpredictable behavior, data corruption
- ✅ Fix 1: `synchronized` keyword
- ✅ Fix 2: Immutable objects (best)
- ✅ Fix 3: Atomic variables (AtomicInteger)
- ✅ Fix 4: Collections (ConcurrentHashMap)

---

### Q9: What's the difference between synchronized method and synchronized block?

**Problem:** Choosing between synchronized method and block.

**Synchronized Method (Locks entire method):**
```java
public class BankAccount {
    private double balance = 0;
    
    // Entire method is locked
    public synchronized void deposit(double amount) {
        balance += amount;
        // ... lots of other logic ...
        // ... more logic ...
        // Lock held entire time!
    }
}
```

**Issues:**
- Lock held for entire duration
- Other threads blocked even during non-critical sections
- Performance impact

**Synchronized Block (Locks only critical section):**
```java
public class BankAccount {
    private double balance = 0;
    private Object lock = new Object();
    
    public void deposit(double amount) {
        // Non-critical work - no lock
        validateAmount(amount);
        applyFees(amount);
        
        // Only critical section locked
        synchronized (lock) {
            balance += amount;  // Only this locked
        }
        
        // Log and notify - no lock
        notifyAccount();
    }
}
```

**Performance Comparison:**
```
Synchronized Method:
|-----LOCK-----|-----LOCK-----|-----LOCK-----|
[validate][modify][log]

Synchronized Block:
validate [LOCK] log
```

**✅ Best Practice:**
```java
public class SafeCounter {
    private int count = 0;
    private final Object lock = new Object();
    
    // Only critical part synchronized
    public void increment() {
        synchronized (lock) {
            count++;  // Minimal lock time
        }
    }
}
```

**Interview Tip:**
"Use synchronized blocks when you only need to protect a small critical section. Use synchronized methods when the entire method is critical. Blocks are more efficient because they minimize lock contention."

**Quick Checklist:**
- ✅ Synchronized method: entire method locked
- ✅ Synchronized block: only critical section locked
- ✅ Blocks = better performance
- ✅ Methods = simpler, cleaner code
- ✅ Use method for simple classes
- ✅ Use block for complex logic

---

### Q10: What is a deadlock and how do you prevent it?

**Problem:** Understanding and avoiding circular wait conditions.

**❌ Deadlock Code:**
```java
public class DeadlockExample {
    public static Object lock1 = new Object();
    public static Object lock2 = new Object();
    
    public static void main(String[] args) {
        // Thread 1: Lock lock1, then try lock2
        Thread t1 = new Thread(() -> {
            synchronized (lock1) {
                System.out.println("T1: Got lock1");
                sleep(1000);  // Give T2 time to get lock2
                
                synchronized (lock2) {  // WAIT - T2 has it!
                    System.out.println("T1: Got lock2");
                }
            }
        });
        
        // Thread 2: Lock lock2, then try lock1
        Thread t2 = new Thread(() -> {
            synchronized (lock2) {
                System.out.println("T2: Got lock2");
                sleep(1000);  // Give T1 time to get lock1
                
                synchronized (lock1) {  // WAIT - T1 has it!
                    System.out.println("T2: Got lock1");
                }
            }
        });
        
        t1.start();
        t2.start();
        // Output: DEADLOCK - neither thread prints final message!
    }
}
```

**Deadlock Timeline:**
```
T1: Lock lock1 ✓
T2:           Lock lock2 ✓
T1:           Wait for lock2 (held by T2)
T2:           Wait for lock1 (held by T1)
                    ↓
              DEADLOCK - both waiting forever
```

**✅ Prevention Strategy 1: Lock Ordering**
```java
public class NoDeadlock {
    private static Object lock1 = new Object();
    private static Object lock2 = new Object();
    
    // ALWAYS acquire in same order: lock1 before lock2
    public static void method1() {
        synchronized (lock1) {      // Acquire lock1 first
            synchronized (lock2) {  // Acquire lock2 second
                // Safe - never circular wait
            }
        }
    }
    
    public static void method2() {
        synchronized (lock1) {      // Also lock1 first
            synchronized (lock2) {  // Also lock2 second
                // Safe - same order
            }
        }
    }
}
```

**✅ Prevention Strategy 2: Timeout**
```java
public class TimeoutLock {
    public static void main(String[] args) {
        Lock lock1 = new ReentrantLock();
        Lock lock2 = new ReentrantLock();
        
        Thread t1 = new Thread(() -> {
            try {
                if (lock1.tryLock(1, TimeUnit.SECONDS)) {
                    try {
                        if (lock2.tryLock(1, TimeUnit.SECONDS)) {
                            try {
                                System.out.println("T1: Got both locks");
                            } finally {
                                lock2.unlock();
                            }
                        }
                    } finally {
                        lock1.unlock();
                    }
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        });
        
        // If T1 can't get lock2 in 1 sec, it releases lock1 and retries
        // No deadlock!
    }
}
```

**Interview Tip:**
"Deadlock requires four conditions: mutual exclusion, hold and wait, no preemption, and circular wait. Prevent it by acquiring locks in a consistent order across all threads. Or use timeouts like `tryLock(timeout)`."

**Quick Checklist:**
- ✅ Deadlock = circular wait condition
- ✅ T1 waits for T2, T2 waits for T1
- ✅ Prevention 1: Lock ordering (best)
- ✅ Prevention 2: Timeouts (`tryLock`)
- ✅ Prevention 3: Single lock (simple but restrictive)
- ✅ Detection: Thread dump analysis

---

## 🔍 Volatile & AtomicInteger

### Q11: What does `volatile` do?

**Problem:** Understanding visibility of changes across threads.

**Why It Happens:**
Threads cache variables in their own memory for speed. Volatile forces reading/writing from main memory.

**❌ Without Volatile (Visibility Issue):**
```java
public class VolatileExample {
    private boolean flag = false;  // Not volatile!
    
    public static void main(String[] args) {
        Thread writer = new Thread(() -> {
            try {
                Thread.sleep(100);  // Give reader time to start
                flag = true;        // Write flag
                System.out.println("Flag set to true");
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        });
        
        Thread reader = new Thread(() -> {
            while (!flag) {  // Keep checking
                // May never see true!
                // Reader thread caches flag = false in local memory
                // Never checks main memory again
            }
            System.out.println("Flag is now true");
        });
        
        reader.start();
        writer.start();
        
        // Output: 
        // Flag set to true
        // (reader thread never exits - stuck loop!)
    }
}
```

**Memory Diagram (Without Volatile):**
```
Thread 1 cache: flag = false
Thread 2 cache: flag = false
Main Memory:    flag = false

Thread 2 writes flag = true to its cache
↓
Thread 1 cache: flag = false  ← Still false!
Thread 2 cache: flag = true
Main Memory:    flag = ???   (update delayed)

Reader stuck in loop!
```

**✅ With Volatile (Guaranteed Visibility):**
```java
public class VolatileExample {
    private volatile boolean flag = false;  // Volatile!
    
    public static void main(String[] args) {
        Thread writer = new Thread(() -> {
            try {
                Thread.sleep(100);
                flag = true;
                System.out.println("Flag set to true");
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        });
        
        Thread reader = new Thread(() -> {
            while (!flag) {
                // Each iteration reads from main memory
                // Will see true within microseconds
            }
            System.out.println("Flag is now true");
        });
        
        reader.start();
        writer.start();
        
        // Output:
        // Flag set to true
        // Flag is now true  ✅
    }
}
```

**Memory Diagram (With Volatile):**
```
Every write to volatile → flush to main memory immediately
Every read of volatile → read from main memory immediately

Thread 1 writes flag = true (via volatile)
         ↓ (flush to main memory)
Main Memory: flag = true
         ↓ (next read sees it)
Thread 2 sees flag = true
```

**Interview Tip:**
"Volatile keyword forces a thread to read/write from main memory, not cache. Use it for flags that multiple threads check. It guarantees visibility but NOT atomicity - use AtomicInteger for atomic operations."

**Quick Checklist:**
- ✅ Volatile = visibility guarantee
- ✅ NOT atomicity guarantee
- ✅ Use: simple flags between threads
- ✅ Don't use: compound operations like count++
- ✅ Performance: faster than synchronized

---

### Q12: What's the difference between `volatile` and `synchronized`?

**Problem:** Choosing between volatile and synchronized.

**Volatile:**
```java
private volatile int count = 0;

// What it does:
// ✅ Visibility - all threads see latest value
// ❌ NO atomicity - count++ is still NOT atomic!

public void increment() {
    count++;  // STILL has race condition!
    // Steps: read(0) → increment(?) → write(?)
    // Many threads can execute these steps at same time
}
```

**Synchronized:**
```java
private int count = 0;

public synchronized void increment() {
    count++;  // ✅ Atomic - one thread at a time
}

// What it does:
// ✅ Visibility - acquires/releases lock synchronizes memory
// ✅ Atomicity - only one thread executes critical section
```

**Comparison:**

| Feature | Volatile | Synchronized |
|---------|----------|--------------|
| Visibility | ✅ YES | ✅ YES |
| Atomicity | ❌ NO | ✅ YES |
| Speed | ⚡ Fast | 🐢 Slower |
| Use Case | Simple flags | Compound operations |
| Example | `flag`, `stop` | Counter, bank account |

**❌ Wrong: Using volatile for counter:**
```java
private volatile int count = 0;

public void increment() {
    count++;  // WRONG! Race condition still exists
              // Two threads can increment same value
}

// Test: likely won't reach 2000
for (int i = 0; i < 1000; i++) t1.increment();
for (int i = 0; i < 1000; i++) t2.increment();
// Result: ~1500, not 2000
```

**✅ Right: Using synchronized:**
```java
private int count = 0;

public synchronized void increment() {
    count++;  // RIGHT! Atomic increment
}

// Test: always 2000
for (int i = 0; i < 1000; i++) t1.increment();
for (int i = 0; i < 1000; i++) t2.increment();
// Result: Always 2000
```

**Interview Tip:**
"Volatile only guarantees visibility, not atomicity. Use synchronized for compound operations. For atomic counters, use AtomicInteger which combines both visibility and atomicity with better performance than synchronized."

**Quick Checklist:**
- ✅ Volatile: for simple flags/stops
- ✅ Synchronized: for protecting critical sections
- ✅ AtomicInteger: for counters (best choice)
- ✅ Volatile + Synchronized together: overkill
- ✅ volatile doesn't make count++ safe!

---

### Q13: When should you use AtomicInteger?

**Problem:** Choosing between synchronized and Atomic classes.

**Scenario: Simple Counter**

**❌ Option 1: Synchronized (Slower)**
```java
public class SyncCounter {
    private int count = 0;
    
    public synchronized void increment() {
        count++;
    }
    
    public synchronized int get() {
        return count;
    }
}

// All operations serialized - one thread at a time
// Lock overhead for every operation
```

**✅ Option 2: AtomicInteger (Better)**
```java
public class AtomicCounter {
    private AtomicInteger count = new AtomicInteger(0);
    
    public void increment() {
        count.incrementAndGet();  // Atomic, no locks!
    }
    
    public int get() {
        return count.get();
    }
}

// Uses CAS (Compare-And-Swap) - lock-free
// Much faster than synchronized!
```

**How AtomicInteger Works:**
```java
int value = 5;
// Synchronize: Lock, modify, Unlock (slow)
// Atomic:     CAS loop: 
//             - Read current value
//             - Calculate new value  
//             - Try to set if unchanged
//             - Retry if changed by another thread
//             (no locks!)
```

**AtomicInteger Common Methods:**
```java
AtomicInteger counter = new AtomicInteger(0);

counter.incrementAndGet();      // ++i, returns new value
counter.getAndIncrement();      // i++, returns old value
counter.decrementAndGet();      // --i
counter.addAndGet(5);           // += 5
counter.getAndAdd(5);           // i += 5
counter.compareAndSet(0, 1);    // CAS: set if equals
counter.get();                  // read value
counter.set(10);                // write value
```

**Performance Comparison:**
```java
// Test: increment 1M times from 2 threads
// Results on modern CPU:

Synchronized:    ~500ms  (lock contention)
AtomicInteger:   ~50ms   (no locks!)
volatile int:    ❌ Race conditions - wrong results

// 10x faster!
```

**Interview Tip:**
"Use AtomicInteger for simple atomic operations on primitives. It's faster than synchronized because it uses CAS (Compare-And-Swap) instead of locks. Perfect for counters, flags, and simple state."

**Quick Checklist:**
- ✅ AtomicInteger for: counters, versions, IDs
- ✅ Synchronized for: complex critical sections
- ✅ Use `incrementAndGet()` for ++i style
- ✅ Use `getAndIncrement()` for i++ style
- ✅ AtomicLong, AtomicBoolean, AtomicReference also available
- ✅ No need for synchronized with Atomic!

---

## 🚀 Non-Blocking vs Async

### Q14: What's the difference between Blocking and Non-Blocking?

**Problem:** Understanding blocking operations and impact on threads.

**Blocking Example:**
```java
// Traditional blocking approach
Socket socket = serverSocket.accept();  // BLOCKS until connection arrives
InputStream input = socket.getInputStream();
int data = input.read();  // BLOCKS until data available
System.out.println("Received: " + data);

// Thread is stuck - can't do anything else
// If 1000 connections = 1000 threads stuck = resource exhaustion!
```

**Timeline (Blocking):**
```
Thread: DO_WORK → BLOCK_WAITING → GET_DATA → DO_MORE_WORK
        ^^^^^^             ^^^^
        Active        Dead (wasting resources)
```

**Non-Blocking Example:**
```java
// Modern non-blocking approach
Selector selector = Selector.open();
ServerSocketChannel server = ServerSocketChannel.open();
server.configureBlocking(false);  // Non-blocking!
server.register(selector, SelectionKey.OP_ACCEPT);

while (selector.select() > 0) {  // Does NOT block forever
    for (SelectionKey key : selector.selectedKeys()) {
        if (key.isAcceptable()) {
            // Handle connection - execute immediately, doesn't wait
        }
    }
}

// Can handle 1000s of connections with few threads!
```

**Timeline (Non-Blocking):**
```
Thread: Check_Connection → Return_Immediately → DO_OTHER_WORK → Check_Next
        ✅ Always active, never blocked
```

**Real-World Comparison:**

**Blocking (Restaurant Model):**
```
Waiter goes to kitchen, WAITS for food
Can't take other orders while waiting
Need 100 waiters for 100 customers
```

**Non-Blocking (Pizza Make-Line Model):**
```
Chef starts multiple pizzas
Moves between them while waiting
1-2 chefs handle 100 pizzas
```

**Interview Tip:**
"Blocking operations pause the thread until complete. Non-blocking returns immediately, letting thread do other work. Blocking = 1 thread per request (scalability limit). Non-blocking = few threads handle many requests (better scalability)."

**Quick Checklist:**
- ✅ Blocking: Thread pauses, waits for operation
- ✅ Non-Blocking: Thread returns immediately
- ✅ Blocking: Limited by thread count (1000 connections = 1000 threads)
- ✅ Non-Blocking: Few threads handle many connections
- ✅ Blocking: Simple, easier to understand
- ✅ Non-Blocking: Complex, better scalability

---

### Q15: Is async the same as non-blocking?

**Problem:** Understanding the subtle difference.

**Async Code (Callbacks):**
```java
// Async: Operation happens in background, callback when done
public void readFileAsync(String filename, Callback<String> callback) {
    new Thread(() -> {
        try {
            String data = readFileBlocking(filename);  // Still blocking!
            callback.onSuccess(data);  // Call callback
        } catch (Exception e) {
            callback.onError(e);
        }
    }).start();
}

// Usage
readFileAsync("file.txt", new Callback<String>() {
    @Override
    public void onSuccess(String data) {
        System.out.println("Got: " + data);
    }
});
// Returns immediately - caller doesn't block
```

**Is It Non-Blocking?**
- Main thread: ✅ Non-blocking (returns immediately)
- Background thread: ❌ Still blocking (waits for file read)

**Non-Blocking Code (NIO):**
```java
// Non-blocking: Operation never blocks any thread
FileChannel channel = FileChannel.open(Paths.get("file.txt"));
ByteBuffer buffer = ByteBuffer.allocate(1024);

// Returns immediately with partial data or 0
int bytesRead = channel.read(buffer);  // Never blocks!

if (bytesRead > 0) {
    // Process data
} else if (bytesRead == 0) {
    // Not ready yet - do other work
    doOtherWork();
}
```

**Timeline Comparison:**

**Async (with thread pool):**
```
Main Thread: Start → Return immediately → Do other work
BG Thread:   Read (blocking) → Done
```

**Non-Blocking (NIO):**
```
Thread: Try_Read (immediate) → Do_Other_Work → Try_Read_Again
        No waiting, no background threads needed
```

**Interview Tip:**
"Async means 'not waiting for the operation' - usually uses callbacks or futures. Non-blocking means the operation itself never blocks - uses OS facilities. Async can still be blocking (background thread blocks). Non-blocking is truly non-blocking."

**Quick Checklist:**
- ✅ Async: Caller doesn't wait (may use background thread)
- ✅ Non-Blocking: Operation itself never blocks
- ✅ Async ≠ Non-Blocking (can be either)
- ✅ Async + Blocking = thread per request (wasteful)
- ✅ Non-Blocking = best scalability
- ✅ CompletableFuture = async, may use thread pool

---

---

## 🎓 Quick Revision: Top Interview Questions

### 1-Minute Answers

**Q: Where does `"hello"` go in memory?**
→ String Pool (literals saved there for memory efficiency)

**Q: Why is `c == d` false?**
→ Runtime concatenation (`+`) goes to heap, literals go to pool. Different objects.

**Q: What makes a class immutable?**
→ Final class, final fields, no setters, defensive copying

**Q: What's a race condition?**
→ Multiple threads modify shared state without sync → unpredictable results

**Q: Volatile vs Synchronized?**
→ Volatile = visibility only. Synchronized = visibility + atomicity

**Q: Use AtomicInteger or synchronized?**
→ AtomicInteger for counters (faster). Synchronized for complex logic.

**Q: Blocking vs Non-Blocking?**
→ Blocking = thread waits. Non-Blocking = thread returns immediately.

**Q: Async vs Non-Blocking?**
→ Async = caller waits for callback. Non-Blocking = operation never blocks.

---

## 📋 Study Checklist

Use this to track your mastery:

### String Memory
- [ ] Understand String Pool vs Heap
- [ ] Know when strings go to pool
- [ ] Explain why `==` fails for concatenation
- [ ] Know when to use `.intern()`
- [ ] Understand GC of pool strings

### Immutability
- [ ] Can list 4 requirements (final class/fields, no setters, defensive copy)
- [ ] Explain shallow vs deep copy
- [ ] Know defensive copy patterns
- [ ] Explain how to return collections safely
- [ ] Know String is immutable

### Multithreading
- [ ] Define and recognize race conditions
- [ ] Explain synchronized method vs block
- [ ] Prevent deadlock with lock ordering
- [ ] Know volatile vs synchronized
- [ ] Choose AtomicInteger when appropriate
- [ ] Explain happens-before relationships

### Non-Blocking/Async
- [ ] Explain blocking operations
- [ ] Understand scalability issues
- [ ] Know non-blocking NIO
- [ ] Distinguish async from non-blocking
- [ ] Explain callback patterns
- [ ] Know when to use each

---

## 🎯 Interview Tip Summary

**When asked about Core Java concepts:**

1. **Always start with the problem** - "Before sync/volatile, threads face race conditions..."
2. **Show code examples** - ❌ wrong, ✅ right
3. **Explain the "why"** - Not just "use volatile for flags" but why
4. **Mention trade-offs** - Performance vs correctness, simplicity vs scalability
5. **Reference real-world usage** - "Strings use pool to save memory" or "Spring uses Singletons"

---

**Last Updated:** February 21, 2026  
**Questions:** 15  
**Topics:** 5 (String Memory, Immutability, Multithreading, Volatile/Atomic, Non-Blocking)  
**Expected Study Time:** 90-120 minutes

**Happy studying! 🎓**
