# Race Conditions and Thread Problems

**Interview Priority:** Senior: 🔥 MUST KNOW | Mid: 🔥 MUST KNOW

---

## Scenario

**Given this code, what are the two issues?**

```java
public class RaceExample {
    private static int count = 0;
    private static boolean ready = false;

    public static void main(String[] args) throws Exception {
        Thread writer = new Thread(() -> {
            count = 42;
            ready = true;
        });

        Thread reader = new Thread(() -> {
            if (ready) {
                System.out.println(count); // Could print 0
            }
        });

        writer.start();
        reader.start();
        writer.join();
        reader.join();
    }
}
```

**Problem 1:** Race condition on `count++` style updates (thread interference).

**Problem 2:** Memory visibility (`ready` may be seen true before `count` is visible).

---

## Key Principle

**Threads can interleave in unsafe ways (race conditions) and see stale values (visibility issues).**

---

## Counter Race Example (Lost Updates)

```java
public class CounterDemo {
    static class Counter {
        private int count = 0;

        public void increment() {
            count++; // not atomic
        }

        public int getCount() {
            return count;
        }
    }

    public static void main(String[] args) throws InterruptedException {
        Counter counter = new Counter();

        Runnable task = () -> {
            for (int i = 0; i < 1000; i++) {
                counter.increment();
            }
        };

        Thread t1 = new Thread(task);
        Thread t2 = new Thread(task);

        t1.start();
        t2.start();
        t1.join();
        t2.join();

        System.out.println(counter.getCount()); // Often < 2000
    }
}
```

**Why:** `count++` is read-modify-write. Two threads can read the same value and one update is lost.

**Note on `join()`:** It ensures the main thread waits. Without it, output can be even smaller.

---

## Why It Happens (Simple English)

- **Race condition:** Two threads update the same data at the same time. One update can overwrite the other.
- **Visibility issue:** One thread writes, another thread does not see it because the CPU cache has not been flushed.

---

## Data Race vs Thread Interference

- **Thread interference:** Multiple threads modifying shared state without coordination.
- **Data race (memory inconsistency):** A write happens but another thread sees a stale value.

---

## Wrong vs Right

| ❌ Wrong | ✅ Right |
|---|---|
| Shared variables without locks | `volatile` or `synchronized` |
| Read-modify-write without atomicity | `AtomicInteger` |

**Wrong:**
```java
if (ready) System.out.println(count);
```

**Right:**
```java
private static volatile boolean ready = false;
```

---

## Fix 1: Synchronization

```java
public class SafeExample {
    private static int count = 0;
    private static boolean ready = false;
    private static final Object lock = new Object();

    public static void main(String[] args) throws Exception {
        Thread writer = new Thread(() -> {
            synchronized (lock) {
                count = 42;
                ready = true;
            }
        });

        Thread reader = new Thread(() -> {
            synchronized (lock) {
                if (ready) {
                    System.out.println(count); // Always 42
                }
            }
        });

        writer.start();
        reader.start();
        writer.join();
        reader.join();
    }
}
```

---

## Fix 2: Volatile + Atomic

```java
import java.util.concurrent.atomic.AtomicInteger;

public class VolatileAtomicExample {
    private static final AtomicInteger count = new AtomicInteger(0);
    private static volatile boolean ready = false;

    public static void main(String[] args) throws Exception {
        Thread writer = new Thread(() -> {
            count.set(42);
            ready = true;
        });

        Thread reader = new Thread(() -> {
            if (ready) {
                System.out.println(count.get()); // Always 42
            }
        });

        writer.start();
        reader.start();
        writer.join();
        reader.join();
    }
}
```

---

## Interview Tip (Exact Answer)

"Race conditions happen when multiple threads access shared data without coordination. You fix them with `synchronized`, locks, or atomic classes. Visibility issues need `volatile` or synchronization to ensure other threads see updates."

---

## Quick Checklist

- Protect shared state with locks or atomics.
- Use `volatile` for visibility-only flags.
- Avoid read-modify-write without atomicity.
- Keep critical sections small.

---

## Critical Pitfalls

- `volatile` does not make compound operations atomic.
- Synchronizing on different objects does not protect the same state.
- Relying on `sleep()` for ordering is not safe.

---

## Follow-up Questions & Answers

**Q:** Is `volatile` enough for counters?

**A:** No. `volatile` gives visibility but not atomicity.

**Q:** What is a happens-before relationship?

**A:** It is a memory guarantee that writes before a sync action are visible to reads after it.

---

## How to Use for Interviews

- Explain difference between race condition and visibility issue.
- Give one fix: `synchronized` or `AtomicInteger`.
- Mention `volatile` for flags only.

---

**Last Updated:** March 5, 2026
