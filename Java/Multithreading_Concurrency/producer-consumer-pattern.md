# Producer-Consumer Pattern: Thread Synchronization

**Study Time:** 10-12 minutes | **Frequency:** 70% in interviews | **Difficulty:** ⭐⭐⭐⭐

---

## 🤔 Problem Scenario

How do you safely coordinate between multiple threads where one produces data and another consumes it?

```java
class Buffer {
    private int item;
    private boolean empty = true;

    // Producer puts item in buffer
    public void put(int value) {
        synchronized(this) {
            while (!empty) {
                // Buffer full, wait for consumer
            }
            item = value;
            empty = false;
            System.out.println("Produced: " + value);
        }
    }

    // Consumer takes item from buffer
    public int get() {
        synchronized(this) {
            while (empty) {
                // Buffer empty, wait for producer
            }
            empty = true;
            System.out.println("Consumed: " + item);
            return item;
        }
    }
}
```

**Problem:** How do we make threads **wait** when buffer is full/empty?

---

## 🧠 Key Principle: Wait-Notify Pattern

**Three Key Methods:**

| Method | Purpose |
|--------|---------|
| `wait()` | Thread releases lock and waits for notification |
| `notify()` | Wakes ONE waiting thread |
| `notifyAll()` | Wakes ALL waiting threads |

```
Timeline:

Thread-1 calls wait():
  - Releases lock
  - Goes to WAITING state
  - Cannot proceed until notified

Thread-2 calls notify():
  - Wakes Thread-1
  - Thread-1 re-acquires lock
  - Thread-1 continues from wait() call
```

---

## ✅ Solution: Wait-Notify Producer-Consumer

```java
class Buffer {
    private int item;
    private boolean empty = true;

    // Producer puts item
    public synchronized void put(int value) throws InterruptedException {
        while (!empty) {          // While buffer full
            wait();               // Release lock, wait for consumer
        }
        // Now buffer is empty, produce
        item = value;
        empty = false;
        System.out.println("Produced: " + value);
        notify();                 // Wake waiting consumer
    }

    // Consumer takes item
    public synchronized int get() throws InterruptedException {
        while (empty) {           // While buffer empty
            wait();               // Release lock, wait for producer
        }
        // Now buffer is full, consume
        int result = item;
        empty = true;
        System.out.println("Consumed: " + result);
        notify();                 // Wake waiting producer
        return result;
    }
}

// Main
public class ProducerConsumer {
    public static void main(String[] args) {
        Buffer buffer = new Buffer();

        // Producer thread
        new Thread(() -> {
            try {
                for (int i = 1; i <= 5; i++) {
                    buffer.put(i);
                    Thread.sleep(1000);
                }
            } catch (InterruptedException e) {}
        }).start();

        // Consumer thread
        new Thread(() -> {
            try {
                for (int i = 1; i <= 5; i++) {
                    buffer.get();
                    Thread.sleep(1500);
                }
            } catch (InterruptedException e) {}
        }).start();
    }
}
```

**Output (typical):**
```
Produced: 1
Consumed: 1
Produced: 2
Consumed: 2
Produced: 3
Consumed: 3
Produced: 4
Consumed: 4
Produced: 5
Consumed: 5
```

---

## 📊 Execution Flow

```
Timeline:

T=0s   Producer: put(1) → Produces, notifies
       Consumer: waiting...
                 → Wakes up, gets(1)

T=1s   Producer: put(2) → Produces, notifies
       Consumer: still processing (sleep 1.5s)

T=1.5s Producer: trying put(3) → Buffer full, waits
       Consumer: gets(2) → Consumes, notifies
                 → Producer wakes up
       Producer: put(3) → Produces

T=2.5s Consumer: gets(3)
...
```

---

## ✅ Scenario 2: Using BlockingQueue (Modern)

Instead of manual wait/notify, use built-in thread-safe collections:

```java
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;

class ModernProducerConsumer {
    public static void main(String[] args) {
        BlockingQueue<Integer> queue = new LinkedBlockingQueue<>(1);
        // Capacity 1 (buffer size)

        // Producer
        new Thread(() -> {
            try {
                for (int i = 1; i <= 5; i++) {
                    queue.put(i);  // Blocks if full
                    System.out.println("Produced: " + i);
                    Thread.sleep(1000);
                }
            } catch (InterruptedException e) {}
        }).start();

        // Consumer
        new Thread(() -> {
            try {
                for (int i = 1; i <= 5; i++) {
                    int item = queue.take();  // Blocks if empty
                    System.out.println("Consumed: " + item);
                    Thread.sleep(1500);
                }
            } catch (InterruptedException e) {}
        }).start();
    }
}
```

**Advantages:**
- No manual wait/notify
- Thread-safe by design
- Various queue types (LinkedBlockingQueue, ArrayBlockingQueue, etc.)

---

## ✅ Scenario 3: Multiple Producers/Consumers

```java
class SharedBuffer {
    private final BlockingQueue<Integer> queue = new LinkedBlockingQueue<>(5);

    public void produce(int id, int count) throws InterruptedException {
        for (int i = 1; i <= count; i++) {
            int item = id * 100 + i;
            queue.put(item);
            System.out.println("Producer-" + id + " produced: " + item);
            Thread.sleep(500);
        }
    }

    public void consume(int id, int count) throws InterruptedException {
        for (int i = 0; i < count; i++) {
            int item = queue.take();
            System.out.println("Consumer-" + id + " consumed: " + item);
            Thread.sleep(1000);
        }
    }
}

public class MultiProducerConsumer {
    public static void main(String[] args) {
        SharedBuffer buffer = new SharedBuffer();

        // 2 Producers
        new Thread(() -> {
            try { buffer.produce(1, 3); } catch (InterruptedException e) {}
        }).start();

        new Thread(() -> {
            try { buffer.produce(2, 3); } catch (InterruptedException e) {}
        }).start();

        // 2 Consumers
        new Thread(() -> {
            try { buffer.consume(1, 3); } catch (InterruptedException e) {}
        }).start();

        new Thread(() -> {
            try { buffer.consume(2, 3); } catch (InterruptedException e) {}
        }).start();
    }
}
```

---

## ❌ Common Mistakes

### ❌ Mistake 1: Using if Instead of while

```java
// WRONG - Using if
public synchronized void put(int value) throws InterruptedException {
    if (!empty) {  // Only checks once
        wait();    // Wakes up and rechecks? NO!
    }
    item = value;
    empty = false;
}

// CORRECT - Using while
public synchronized void put(int value) throws InterruptedException {
    while (!empty) {  // Keeps checking condition
        wait();       // Wakes up and rechecks loop
    }
    item = value;
    empty = false;
}

// Why? Spurious wakeups (thread wakes without notify)
// or multiple threads waking up
// Always use while to recheck condition after waking
```

---

### ❌ Mistake 2: Forgetting to Release Lock

```java
// WRONG - Lock not released, consumer can't access
public void put(int value) {
    synchronized(this) {
        // while (!empty) wait();  // Commented out
        item = value;  // But wait() is still not called!
        empty = false;  // Consumer waiting forever
    }
}

// Wait releases the lock, allowing consumer to acquire it
```

---

### ❌ Mistake 3: Using notify() Instead of notifyAll()

```java
// WRONG - notify() wakes ONE thread
public void put(int value) throws InterruptedException {
    while (!empty) wait();
    item = value;
    empty = false;
    notify();  // Wakes ONE thread (could be another producer!)
}

// Could wake a producer instead of consumer

// CORRECT - notifyAll() wakes all threads
public void put(int value) throws InterruptedException {
    while (!empty) wait();
    item = value;
    empty = false;
    notifyAll();  // Wakes all, each rechecks condition
}
```

---

### ❌ Mistake 4: Not Throwing InterruptedException

```java
// WRONG - Swallows exception
try {
    wait();
} catch (InterruptedException e) {
    // Just ignore
}

// CORRECT - Propagate or handle properly
try {
    wait();
} catch (InterruptedException e) {
    Thread.currentThread().interrupt();  // Restore interrupt status
    return;  // Exit method
}

// Or declare throws
public void put(int value) throws InterruptedException {
    while (!empty) wait();  // InterruptedException propagates
}
```

---

## 🎯 Interview Q&A

### Q1: "Explain Producer-Consumer pattern"

**Answer (30 seconds):**
```
Producer produces items into a shared buffer.
Consumer consumes items from the buffer.

Using wait/notify:
- Producer waits if buffer full
- Consumer waits if buffer empty
- Each notifies the other when done

Example:
Buffer buffer = new Buffer();
- producer.put(item) - blocks if full, notifies consumer
- consumer.get() - blocks if empty, notifies producer
```

---

### Q2: "Why use while instead of if with wait()?"

**Answer:**
```
Spurious wakeups: A thread can wake up without notify()

Example:
while (!empty) wait();  // Correct
- Wait. Wake up.
- Check: is buffer still empty?
- If yes, wait again
- If no, proceed

if (!empty) wait();  // Wrong
- Wait. Wake up.
- Proceed WITHOUT checking buffer!
- Might consume when buffer still empty

Also: Multiple consumers waiting, both wake up on notify()
- First consumer gets item
- Second wakes up, if uses if, proceeds anyway (ERROR)
- With while, second checks, buffer empty, waits again
```

---

### Q3: "BlockingQueue vs manual wait/notify?"

**Answer:**
```
BlockingQueue:
✅ Simpler, cleaner code
✅ Thread-safe by default
✅ No manual synchronization
✅ Multiple queue variants

Manual wait/notify:
❌ More complex
❌ Easy to make mistakes
❌ Lower-level control
✅ Educational (understand threading)

In production: Use BlockingQueue
In interviews: Show you understand wait/notify
```

---

### Q4: "What if producer is faster than consumer?"

**Answer:**
```
Timeline:
T=0: Producer puts 1, posts 2, puts 3 (buffer size 3)
     Buffer: [1, 2, 3] ← FULL
     Producer BLOCKS on next put()

T=1: Consumer gets 1
     Buffer: [2, 3]
     Producer unblocks, puts 4

T=2: Consumer gets 2
     Buffer: [3, 4]
     Producer puts 5...

Result: Queue acts as buffer to decouple speeds
```

---

## 📚 Queue Variants Available

```java
// Bounded - size limit
BlockingQueue<Integer> bounded = new LinkedBlockingQueue<>(10);
BlockingQueue<Integer> array = new ArrayBlockingQueue<>(10);

// Unbounded - no size limit
BlockingQueue<Integer> unbounded = new LinkedBlockingQueue<>();

// Priority queue
BlockingQueue<Task> priority = new PriorityBlockingQueue<>();

// Synchronous (no buffering)
BlockingQueue<Item> sync = new SynchronousQueue<>();

// Delay queue (elements available after delay)
BlockingQueue<DelayedItem> delayed = new DelayQueue<>();
```

---

## 🔑 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Wait-Notify pattern | Foundation of thread coordination | ⭐⭐⭐⭐⭐ |
| while vs if | Critical correctness issue | ⭐⭐⭐⭐ |
| BlockingQueue | Modern practical approach | ⭐⭐⭐⭐ |
| Multiple producers/consumers | Real-world complexity | ⭐⭐⭐⭐ |
| Interrupt handling | Proper cleanup | ⭐⭐⭐ |

---

**Priority:** ✅ SHOULD KNOW (70% interview frequency, often asked in system design)

**Related Topics:**
- [Deadlock Prevention](#)
- [BlockingQueue Deep Dive](#)
- [Thread States](#)

---

**Last Updated:** March 5, 2026
