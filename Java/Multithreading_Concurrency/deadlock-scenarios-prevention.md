# Deadlock Scenarios & Prevention

**Study Time:** 10-12 minutes | **Frequency:** 80% in interviews | **Difficulty:** ⭐⭐⭐⭐⭐

---

## 🤔 Problem Scenario

Two threads are waiting for each other to release resources, creating an infinite wait:

```java
class DeadlockExample {
    private final Object lock1 = new Object();
    private final Object lock2 = new Object();

    public void method1() {
        synchronized(lock1) {
            System.out.println("Thread-1: Acquired lock1");
            try { Thread.sleep(100); } catch (InterruptedException e) {}
            
            synchronized(lock2) {  // Waiting for lock2
                System.out.println("Thread-1: Acquired lock2");
            }
        }
    }

    public void method2() {
        synchronized(lock2) {
            System.out.println("Thread-2: Acquired lock2");
            try { Thread.sleep(100); } catch (InterruptedException e) {}
            
            synchronized(lock1) {  // Waiting for lock1
                System.out.println("Thread-2: Acquired lock1");
            }
        }
    }
}

public class DeadlockTest {
    public static void main(String[] args) {
        DeadlockExample deadlock = new DeadlockExample();
        
        new Thread(deadlock::method1).start();
        new Thread(deadlock::method2).start();
    }
}
```

**Output:**
```
Thread-1: Acquired lock1
Thread-2: Acquired lock2
(program hangs forever - DEADLOCK)
```

---

## 🧠 Key Principle: Four Conditions for Deadlock

**ALL four must be true for deadlock to occur:**

| Condition | Explanation | Example |
|-----------|-------------|---------|
| **Mutual Exclusion** | Resources cannot be shared | locks, synchronized blocks |
| **Hold and Wait** | Thread holds resource while waiting for another | Thread-1 holds lock1, waits for lock2 |
| **No Preemption** | Cannot forcibly take resources from other threads | No interruption mechanism |
| **Circular Wait** | Threads form a cycle waiting for each other | T1→lock1→lock2→T2→lock2→lock1→T1 |

**Deadlock happens when:**
```
Mutual Exclusion (YES) 
    + Hold and Wait (YES) 
    + No Preemption (YES) 
    + Circular Wait (YES)
    = DEADLOCK
```

---

## ❌ Classic Deadlock Pattern

```
Timeline:

Time 1:  Thread-1: synchronized(lock1)  → Gets lock1
         Thread-2: synchronized(lock2)  → Gets lock2

Time 2:  Thread-1: synchronized(lock2)  → BLOCKED (lock2 held by Thread-2)
         Thread-2: synchronized(lock1)  → BLOCKED (lock1 held by Thread-1)

Time 3+: Both threads wait forever on each other
         DEADLOCK! 🔴
```

---

## ✅ Solution 1: Lock Ordering (Most Common)

**Principle:** Always acquire locks in the same order.

```java
class DeadlockFixed {
    private final Object lock1 = new Object();
    private final Object lock2 = new Object();

    public void method1() {
        synchronized(lock1) {  // Always lock1 first
            System.out.println("Thread-1: Acquired lock1");
            try { Thread.sleep(100); } catch (InterruptedException e) {}
            
            synchronized(lock2) {  // Then lock2
                System.out.println("Thread-1: Acquired lock2");
            }
        }
    }

    public void method2() {
        synchronized(lock1) {  // Also lock1 first (same order!)
            System.out.println("Thread-2: Acquired lock1");
            try { Thread.sleep(100); } catch (InterruptedException e) {}
            
            synchronized(lock2) {  // Then lock2
                System.out.println("Thread-2: Acquired lock2");
            }
        }
    }
}
```

**Output:**
```
Thread-1: Acquired lock1
Thread-1: Acquired lock2
Thread-2: Acquired lock1
Thread-2: Acquired lock2
(completes normally, no deadlock)
```

**Why it works:**
- Both threads acquire locks in same order: lock1 → lock2
- One thread gets lock1 first, completes, releases both
- Other thread then acquires lock1 → lock2
- No circular wait = No deadlock

---

## ✅ Solution 2: Lock Timeout (Graceful Failure)

```java
class DeadlockWithTimeout {
    private final Object lock1 = new Object();
    private final Object lock2 = new Object();

    public void method1() {
        synchronized(lock1) {
            System.out.println("Thread-1: Acquired lock1");
            try { Thread.sleep(100); } catch (InterruptedException e) {}
            
            // TryLock with timeout (if using ReentrantLock)
            // For synchronized, use wait/notify pattern instead
            synchronized(lock2) {
                System.out.println("Thread-1: Acquired lock2");
            }
        }
    }
}

// Better approach with ReentrantLock
class DeadlockWithTimeoutBetter {
    private final ReentrantLock lock1 = new ReentrantLock();
    private final ReentrantLock lock2 = new ReentrantLock();

    public void method1() throws InterruptedException {
        boolean lock1Acquired = lock1.tryAcquire(2, TimeUnit.SECONDS);
        if (!lock1Acquired) {
            System.out.println("Thread-1: Timeout waiting for lock1");
            return;
        }
        
        try {
            System.out.println("Thread-1: Acquired lock1");
            Thread.sleep(100);
            
            boolean lock2Acquired = lock2.tryAcquire(2, TimeUnit.SECONDS);
            if (!lock2Acquired) {
                System.out.println("Thread-1: Timeout waiting for lock2");
                return;
            }
            
            try {
                System.out.println("Thread-1: Acquired lock2");
                System.out.println("Thread-1: Work completed");
            } finally {
                lock2.unlock();
            }
        } finally {
            lock1.unlock();
        }
    }
}
```

**Output:**
```
Thread-1: Acquired lock1
Thread-2: Acquired lock2
Thread-1: Timeout waiting for lock2
Thread-2: Timeout waiting for lock1
Thread-1: Released locks
Thread-2: Released locks
(completes with timeout, no deadlock)
```

---

## ✅ Solution 3: ReentrantLock with Proper Unlock

```java
class SafeLocking {
    private final ReentrantLock lock = new ReentrantLock();

    public void criticalSection() {
        lock.lock();
        try {
            // Do work
            System.out.println("Critical section");
        } finally {
            lock.unlock();  // Always unlock in finally
        }
    }
}

// Multiple locks with try-finally
class MultipleLocksSafe {
    private final ReentrantLock lock1 = new ReentrantLock();
    private final ReentrantLock lock2 = new ReentrantLock();

    public void method() {
        lock1.lock();
        try {
            lock2.lock();
            try {
                // Work with both locks
                System.out.println("Both locks held");
            } finally {
                lock2.unlock();
            }
        } finally {
            lock1.unlock();
        }
    }
}
```

---

## ✅ Solution 4: Use ConcurrentHashMap (Thread-Safe Collections)

Instead of manual synchronization:

```java
// WRONG - Manual synchronization prone to deadlock
class UnsafeCache {
    private Map<String, String> cache = new HashMap<>();
    
    public synchronized void put(String key, String value) {
        cache.put(key, value);
    }
    
    public synchronized String get(String key) {
        return cache.get(key);
    }
}

// CORRECT - ConcurrentHashMap (segment-based locking)
class SafeCache {
    private ConcurrentHashMap<String, String> cache = new ConcurrentHashMap<>();
    
    public void put(String key, String value) {
        cache.put(key, value);  // Thread-safe, no global lock
    }
    
    public String get(String key) {
        return cache.get(key);  // Thread-safe, no global lock
    }
}

// Why it's safer:
// - ConcurrentHashMap uses bucket-level locks (multiple locks)
// - Reduces contention and deadlock risk
// - Better throughput for concurrent access
```

---

## ✅ Solution 5: Use Executors with Single Thread

Guarantee sequential access, no deadlock possible:

```java
class SequentialExecution {
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    
    public void task1() {
        executor.submit(() -> {
            System.out.println("Task 1");
        });
    }
    
    public void task2() {
        executor.submit(() -> {
            System.out.println("Task 2");
        });
    }
    
    public void task3() {
        executor.submit(() -> {
            System.out.println("Task 3");
        });
    }
}

// Output:
// Task 1
// Task 2
// Task 3
// (Always sequential - no concurrent access - no deadlock)
```

---

## 🎯 Interview Q&A

### Q1: "What are the 4 conditions for deadlock?"

**Answer (20 seconds):**
```
1. Mutual Exclusion - resources cannot be shared
2. Hold and Wait - threads hold resources while waiting for others
3. No Preemption - resources cannot be forcibly taken
4. Circular Wait - threads form a cycle waiting for each other

All 4 must be true. Break ANY ONE condition to prevent deadlock.
```

---

### Q2: "Code example - will this deadlock?"

```java
class Example {
    private final Object lock1 = new Object();
    private final Object lock2 = new Object();

    public void methodA() {
        synchronized(lock1) {
            synchronized(lock2) { }
        }
    }

    public void methodB() {
        synchronized(lock2) {
            synchronized(lock1) { }
        }
    }
}
```

**Answer:**
```
YES, this WILL deadlock.

Timeline:
- Thread-1 in methodA: Gets lock1, waits for lock2
- Thread-2 in methodB: Gets lock2, waits for lock1
- Circular wait: T1→lock1→lock2→T2→lock2→lock1→T1
- Result: DEADLOCK

Fix: Both methods acquire locks in same order (lock1 → lock2)
```

---

### Q3: "How do you detect a deadlock?"

**Answer:**
```
1. Build Waits-For Graph (WFG):
   - Nodes = threads
   - Edge T1→T2 if T1 waits for resource held by T2
   - Cycle in graph = deadlock

2. Use jstack (command line):
   jstack <pid>
   (Shows thread dumps, identifies deadlocked threads)

3. Use VisualVM or JConsole:
   - Monitor threads
   - Detects blocked threads
   - Shows lock dependencies

4. In code (if possible):
   ThreadMXBean bean = ManagementFactory.getThreadMXBean();
   long[] deadlockedThreads = bean.findDeadlockedThreads();
```

---

### Q4: "Why use ReentrantLock instead of synchronized?"

**Answer:**
```
ReentrantLock advantages:

1. tryLock(timeout) - detect and avoid deadlock
2. Explicit unlock in finally - cleaner control
3. ReadWriteLock variant - multiple readers
4. Interruptible locks - can interrupt waiting threads
5. Fair locking - prevents thread starvation

synchronized limitations:
- No timeout mechanism
- Cannot check if lock is available
- Cannot interrupt waiting thread
- Fair locking not directly supported
```

---

### Q5: "Deadlock vs Livelock - what's the difference?"

**Answer:**
```
DEADLOCK:
- Thread is blocked, cannot proceed
- Waiting for resource that will never be released
- No progress at all
- Example: Circular lock dependency

LIVELOCK:
- Thread is not blocked (actively running)
- But cannot make progress (always retrying)
- Keeps busy but never finishes
- Example: Two threads keep retrying transaction

Example of Livelock:

class Livelock {
    public void method1(AtomicBoolean active) {
        while (active.get()) {
            // Keep trying...
            if (someCondition) {
                active.set(false);  // Try to stop
            }
        }
    }
}

// Both threads keep retrying but never make progress
```

---

### Q6: "Real-world deadlock scenario?"

**Answer:**
```
Database + Application Deadlock:

Thread-1:
1. Acquires DB lock on table A
2. Updates table A
3. Tries to acquire lock on table B (waits...)

Thread-2:
1. Acquires DB lock on table B
2. Updates table B
3. Tries to acquire lock on table A (waits...)

DEADLOCK!

Fix:
- Acquire locks in same order (A → B always)
- Use transactions with timeout
- Use connection pool with deadlock detection
- Redesign schema to avoid multi-table locks
```

---

## ❌ Common Mistakes

### ❌ Mistake 1: Different Lock Order

```java
// WRONG
public void methodA() {
    synchronized(lock1) {
        synchronized(lock2) { }
    }
}

public void methodB() {
    synchronized(lock2) {  // Different order!
        synchronized(lock1) { }
    }
}

// CORRECT
public void methodA() {
    synchronized(lock1) {
        synchronized(lock2) { }
    }
}

public void methodB() {
    synchronized(lock1) {  // Same order!
        synchronized(lock2) { }
    }
}
```

---

### ❌ Mistake 2: No Timeout with ReentrantLock

```java
// WRONG - Can still deadlock without timeout
ReentrantLock lock = new ReentrantLock();
lock.lock();  // Blocks forever if unavailable
try {
    // work
} finally {
    lock.unlock();
}

// CORRECT - Use tryLock with timeout
if (lock.tryLock(5, TimeUnit.SECONDS)) {
    try {
        // work
    } finally {
        lock.unlock();
    }
} else {
    System.out.println("Timeout - deadlock avoided");
}
```

---

### ❌ Mistake 3: Forgetting to Unlock

```java
// WRONG - If exception occurs, lock not released
lock.lock();
System.out.println("Locked");
throw new Exception("Error");  // Lock never released!

// CORRECT - Always use try-finally
lock.lock();
try {
    System.out.println("Locked");
    throw new Exception("Error");
} finally {
    lock.unlock();  // Always released
}
```

---

## 📊 Comparison: Solutions at a Glance

| Solution | Pros | Cons | Best For |
|----------|------|------|----------|
| Lock Ordering | Simple, effective | Requires discipline | Most cases |
| Lock Timeout | Detects deadlock | May lose work | Critical systems |
| ConcurrentHashMap | Fine-grained locking | Limited use case | Collections |
| Single Executor | Guaranteed no deadlock | Serializes work | Non-critical tasks |
| ReentrantLock | Flexible, tryLock | More verbose | Complex locking |

---

## 🔑 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| 4 deadlock conditions | Fundamental understanding | ⭐⭐⭐⭐⭐ |
| Lock ordering principle | Most practical fix | ⭐⭐⭐⭐⭐ |
| ReentrantLock vs synchronized | API knowledge | ⭐⭐⭐⭐ |
| Detecting deadlock | Production debugging | ⭐⭐⭐⭐ |
| Real-world examples | Practical knowledge | ⭐⭐⭐⭐ |

---

**Priority:** 🔥 MUST KNOW (80% interview frequency)

**Related Topics:**
- [Thread States and Transitions](#)
- [Synchronized Methods](#)
- [Concurrent Collections](#)
- [ReentrantLock Guide](#)

---

**Last Updated:** March 5, 2026
