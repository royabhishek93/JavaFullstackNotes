# Synchronized Methods on Same Object: Thread Blocking

**Study Time:** 5-7 minutes | **Frequency:** 70% in interviews | **Difficulty:** ⭐⭐⭐⭐

---

## 🤔 Problem Scenario

Two threads are created that call two different **synchronized methods** on the **same object**. One method enters an infinite loop:

```java
class MultiThreadExample {

    public synchronized void test1() {
        System.out.println("Inside test1 method");
        while (true) {
            try {
                Thread.sleep(5000);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
    }

    public synchronized void test2() {
        System.out.println("Inside test2 method");
        while (true) {
            try {
                Thread.sleep(5000);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
    }
}

public class ThreadTest {

    public static void main(String[] args) {
        MultiThreadExample executor = new MultiThreadExample();

        Runnable r1 = () -> { executor.test1(); };
        Runnable r2 = () -> { executor.test2(); };

        new Thread(r1).start();
        new Thread(r2).start();
    }
}
```

**Question:** What happens when you run this code?

---

## 🧠 Key Principle: Synchronized Methods Share Object Lock

**Critical Concept:**
- When you mark a method as `synchronized`, it locks on **`this` object**
- Multiple synchronized methods on the **same object** share the **same lock**
- Only one thread can hold the lock at a time
- Other threads are blocked until the lock is released

```
MultiThreadExample executor = new MultiThreadExample();

executor.test1();  // Synchronized on 'executor'
executor.test2();  // Also synchronized on 'executor' (SAME LOCK!)
```

---

## ✅ Step-by-Step Execution

### Timeline of Events

**Step 1: Thread-1 Acquires Lock**
```
Thread-1 calls executor.test1()
↓
Acquires lock on 'executor' object
↓
Prints: "Inside test1 method"
↓
Enters while(true) loop
↓
Lock is HELD (never released!)
```

**Output at this point:**
```
Inside test1 method
(program hangs)
```

---

**Step 2: Thread-2 Tries to Enter test2()**
```
Thread-2 calls executor.test2()
↓
Tries to acquire lock on 'executor' object
↓
BLOCKED ❌
Lock is already held by Thread-1

Thread-2 waits in BLOCKED state forever
```

**No additional output.**

---

### Why Only One Output?

| Component | State |
|-----------|-------|
| Thread-1 | RUNNING (in test1 infinite loop) |
| Thread-2 | **BLOCKED** (waiting for lock) |
| Lock on `executor` | Held by Thread-1 |
| Output | Only test1's output prints |

---

## ❌ The Problem: Thread Starvation

| Issue | Explanation |
|-------|------------|
| **Infinite Loop in Synchronized Method** | `while(true)` with `Thread.sleep()` never exits |
| **Lock Never Released** | Thread-1 holds the lock forever |
| **Thread-2 Never Executes** | Blocked indefinitely waiting for the lock |
| **Thread Starvation** | Thread-2 is alive but cannot make progress |
| **Resource Waste** | Both threads consume resources doing nothing |

---

## ✅ How to Fix It (5 Solutions)

### **Solution 1: Remove the Infinite Loop (Simplest)**

```java
public synchronized void test1() {
    System.out.println("Inside test1 method");
    // Removed while(true) - method exits quickly
}

public synchronized void test2() {
    System.out.println("Inside test2 method");
    // Removed while(true) - method exits quickly
}
```

**Output:**
```
Inside test1 method
Inside test2 method
(or reversed order - depends on scheduling)
```

**Why it works:**
- Methods exit quickly after printing
- Locks are released immediately
- Thread-2 is not blocked anymore

---

### **Solution 2: Use Separate Objects (Different Locks)**

```java
public class ThreadTest {
    public static void main(String[] args) {
        // Create SEPARATE objects
        MultiThreadExample executor1 = new MultiThreadExample();
        MultiThreadExample executor2 = new MultiThreadExample();

        Runnable r1 = () -> { executor1.test1(); };
        Runnable r2 = () -> { executor2.test2(); };

        new Thread(r1).start();
        new Thread(r2).start();
    }
}
```

**Why it works:**
- Each object has its own lock
- Thread-1 locks `executor1`, Thread-2 locks `executor2`
- Both can run simultaneously (if infinite loops removed)

---

### **Solution 3: Use Unsynchronized Methods**

```java
class MultiThreadExample {

    public void test1() {  // Removed synchronized
        System.out.println("Inside test1 method");
        // Now no lock needed
    }

    public void test2() {  // Removed synchronized
        System.out.println("Inside test2 method");
        // Now no lock needed
    }
}
```

**Use when:**
- No shared mutable state between threads
- Each thread has its own data

**Caveat:**
- Only safe if threads don't access shared data

---

### **Solution 4: Use ReentrantLock with Different Locks**

```java
import java.util.concurrent.locks.ReentrantLock;

class MultiThreadExample {
    private final ReentrantLock lock1 = new ReentrantLock();
    private final ReentrantLock lock2 = new ReentrantLock();

    public void test1() {
        lock1.lock();
        try {
            System.out.println("Inside test1 method");
            // Only test1 is protected by lock1
        } finally {
            lock1.unlock();
        }
    }

    public void test2() {
        lock2.lock();
        try {
            System.out.println("Inside test2 method");
            // Only test2 is protected by lock2
        } finally {
            lock2.unlock();
        }
    }
}
```

**Advantages:**
- Fine-grained control
- Each method can have its own lock
- More flexible than synchronized

---

### **Solution 5: Use CountDownLatch or Flag to Exit Loop**

```java
import java.util.concurrent.CountDownLatch;

class MultiThreadExample {
    private volatile boolean running = true;

    public synchronized void test1() {
        System.out.println("Inside test1 method");
        while (running) {
            try {
                Thread.sleep(5000);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
        System.out.println("test1 exiting - lock released!");
    }

    public synchronized void test2() {
        System.out.println("Inside test2 method");
        while (running) {
            try {
                Thread.sleep(5000);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
        }
        System.out.println("test2 exiting - lock released!");
    }
    
    public void stop() {
        running = false;
    }
}

public class ThreadTest {
    public static void main(String[] args) throws InterruptedException {
        MultiThreadExample executor = new MultiThreadExample();

        Runnable r1 = () -> { executor.test1(); };
        Runnable r2 = () -> { executor.test2(); };

        new Thread(r1).start();
        new Thread(r2).start();
        
        // Let them run for a while
        Thread.sleep(10000);
        
        // Signal shutdown
        executor.stop();
    }
}
```

**Why it works:**
- Provides a graceful way to exit the loop
- Lock is released when the method exits
- Controlled shutdown instead of infinite blocking

---

## 📊 Comparison Table: Which Fix to Use?

| Solution | Use Case | Pros | Cons |
|----------|----------|------|------|
| **Remove Loop** | No background work needed | Simple, clean | Limited if you need continuous work |
| **Separate Objects** | Independent synchronized work | Works well | More objects, more memory |
| **Remove synchronized** | No shared state | Fast, simple | Risk of data races |
| **ReentrantLock** | Fine-grained control | Flexible, composable | More complex code |
| **Graceful Shutdown** | Long-running tasks | Proper cleanup | Requires shutdown mechanism |

---

## 🎯 Interview Q&A

### Q1: "What's the output of this code?"

**Answer (20-30 seconds):**
```
Only ONE line prints, either:
"Inside test1 method"
OR
"Inside test2 method"

(depending on which thread acquires the lock first)

The program then hangs forever because the first thread
that entered holds the lock in an infinite loop, preventing
the second thread from ever executing.
```

---

### Q2: "Why does only one method execute?"

**Answer:**
```
Both synchronized methods lock on the SAME object: 'executor'

Synchronized method = lock on 'this'

When Thread-1 calls test1():
- Acquires executor's lock
- Prints message
- Enters infinite loop while holding the lock

When Thread-2 calls test2():
- Tries to acquire executor's lock
- BLOCKED because Thread-1 holds it
- Waits forever (never gets to print)

Key insight: Synchronized methods share locks at the INSTANCE level,
not at the method level.
```

---

### Q3: "How would you fix this?"

**Answer (Most Common Fixes):**

**Option 1 - Simplest:**
```
Remove the infinite loop. The method exits quickly,
releasing the lock, allowing Thread-2 to proceed.
```

**Option 2 - Keep Synchronized Behavior:**
```
Create separate objects for each thread:

MultiThreadExample obj1 = new MultiThreadExample();
MultiThreadExample obj2 = new MultiThreadExample();

Now each has its own lock. But you still need to remove
the infinite loop, otherwise they still hang individually.
```

**Option 3 - Best Practice:**
```
Use graceful shutdown with a volatile flag:

private volatile boolean running = true;

while (running) { ... }

Then call stop() to signal shutdown.
```

---

### Q4: "What if you want to run both methods simultaneously with synchronized?"

**Answer:**
```
Use separate locks for each method:

private final Object lock1 = new Object();
private final Object lock2 = new Object();

public void test1() {
    synchronized(lock1) {
        // Protected by lock1
    }
}

public void test2() {
    synchronized(lock2) {
        // Protected by lock2
    }
}

Now they can run simultaneously!

Or use ReentrantLock:

private final ReentrantLock lock1 = new ReentrantLock();
private final ReentrantLock lock2 = new ReentrantLock();
```

---

### Q5: "What's the difference between blocking and hanging?"

**Answer:**
```
BLOCKING:
- Thread is waiting for a resource (lock, I/O)
- Thread is alive but cannot proceed
- When the resource is available, it continues
- Example: Thread-2 waiting for the lock

HANGING:
- Thread is stuck in an infinite loop or deadlock
- Cannot proceed even if resources become available
- Thread is "stuck" in its current state
- Example: Thread-1 in while(true)

In this code: Thread-2 is BLOCKED, Thread-1 is HANGING
```

---

### Q6: "What about thread interruption? Would that help?"

**Answer:**
```java
// Thread-2 could do this in the main thread:
Thread t1 = new Thread(r1);
Thread t2 = new Thread(r2);
t1.start();
t2.start();

// After 10 seconds, interrupt Thread-1
Thread.sleep(10000);
t1.interrupt();  // Signals Thread-1 to stop

// But Thread-1 must handle InterruptedExecution:
public synchronized void test1() {
    System.out.println("Inside test1 method");
    try {
        while (true) {
            Thread.sleep(5000);  // Throws InterruptedException on interrupt
        }
    } catch (InterruptedException e) {
        System.out.println("Thread-1 interrupted");
        // exit gracefully, release lock
    }
}
```

This works! But requires proper exception handling and
re-checking interrupt status.
```

---

## 🔑 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Synchronized methods share instance lock | Core Java multithreading concept | ⭐⭐⭐⭐⭐ |
| Only one thread can hold a lock | Ensures mutual exclusion | ⭐⭐⭐⭐⭐ |
| BLOCKED vs RUNNING state | Debugging deadlocks | ⭐⭐⭐⭐⭐ |
| Lock is released when method exits | Prevents starvation | ⭐⭐⭐⭐ |
| Multiple solutions to fix | Practical problem-solving | ⭐⭐⭐⭐ |

---

## ⚠️ Common Mistakes

### ❌ Mistake 1: Not Understanding Synchronized Scope

```java
// WRONG - Thinking synchronized protects just one method
class MultiThreadExample {
    public synchronized void test1() { ... }
    public synchronized void test2() { ... }
}

// These DO NOT have independent locks!
// Both lock on 'this' object

// CORRECT - If you need independent locks:
class MultiThreadExample {
    private final Object lock1 = new Object();
    private final Object lock2 = new Object();
    
    public void test1() {
        synchronized(lock1) { ... }
    }
    
    public void test2() {
        synchronized(lock2) { ... }
    }
}
```

---

### ❌ Mistake 2: Not Exiting Synchronized Methods

```java
// WRONG - Infinite loop in synchronized method
public synchronized void test1() {
    while (true) {
        // Lock never released!
    }
}

// CORRECT - Ensure method can exit
public synchronized void test1() {
    while (shouldContinue) {
        // Will eventually exit and release lock
    }
}
```

---

### ❌ Mistake 3: Confusing Method Lock with Block Lock

```java
// Method-level synchronized
public synchronized void test1() {
    // Locks entire method on 'this'
}

// Block-level synchronized
public void test1() {
    synchronized(this) {
        // Locks only this block
    }
    // Lock released here, method continues
}

// Different lock object
private Object lock = new Object();
public void test1() {
    synchronized(lock) {
        // Locks on a different object
    }
}
```

---

## Complete Fixed Example (All Methods Work)

```java
import java.util.concurrent.locks.ReentrantLock;

// Version 1: Separate objects
class MultiThreadExampleV1 {
    public synchronized void test1() {
        System.out.println("test1 started");
        Thread.sleep(2000);
        System.out.println("test1 done");
    }

    public synchronized void test2() {
        System.out.println("test2 started");
        Thread.sleep(2000);
        System.out.println("test2 done");
    }
}

// Version 2: Separate locks
class MultiThreadExampleV2 {
    private final Object lock1 = new Object();
    private final Object lock2 = new Object();

    public void test1() {
        synchronized(lock1) {
            System.out.println("test1 started");
            Thread.sleep(2000);
            System.out.println("test1 done");
        }
    }

    public void test2() {
        synchronized(lock2) {
            System.out.println("test2 started");
            Thread.sleep(2000);
            System.out.println("test2 done");
        }
    }
}

// Version 3: ReentrantLock
class MultiThreadExampleV3 {
    private final ReentrantLock lock1 = new ReentrantLock();
    private final ReentrantLock lock2 = new ReentrantLock();

    public void test1() {
        lock1.lock();
        try {
            System.out.println("test1 started");
            Thread.sleep(2000);
            System.out.println("test1 done");
        } finally {
            lock1.unlock();
        }
    }

    public void test2() {
        lock2.lock();
        try {
            System.out.println("test2 started");
            Thread.sleep(2000);
            System.out.println("test2 done");
        } finally {
            lock2.unlock();
        }
    }
}

// Test usage
public class ThreadTest {
    public static void main(String[] args) {
        MultiThreadExampleV2 executor = new MultiThreadExampleV2();

        new Thread(() -> executor.test1()).start();
        new Thread(() -> executor.test2()).start();
    }
}
```

**Output:**
```
test1 started
test2 started
test1 done
test2 done
(possibly interleaved differently, but both run)
```

---

## Interview Winning Strategy

1. **Identify the problem immediately:**
   - "Both methods are synchronized on the same object"
   - "Only one can hold the lock at a time"

2. **Explain the execution flow:**
   - "Thread-1 enters test1, acquires lock"
   - "Thread-2 tries test2 but is BLOCKED waiting for lock"
   - "Thread-1's infinite loop prevents lock release"

3. **Propose fixes (mention multiple):**
   - "Remove the infinite loop - method exits, lock released"
   - "Use separate objects - each gets its own lock"
   - "Use ReentrantLock - fine-grained control"

4. **Show deeper understanding:**
   - "This is an example of thread starvation"
   - "Graceful shutdown pattern prevents hanging"
   - "Know when to use synchronized vs ReentrantLock"

---

**Priority:** ✅ SHOULD KNOW (Very common interview question)

**Related Topics:**
- [Thread States and Transitions](#)
- [Deadlocks and Prevention](#)
- [Producer-Consumer Pattern](#)
- [ReentrantLock vs Synchronized](#)

---

**Last Updated:** March 5, 2026
