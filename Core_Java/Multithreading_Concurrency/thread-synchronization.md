# Thread Synchronization (Purpose and Use)

**Interview Priority:** Senior: 🔥 MUST KNOW | Mid: 🔥 MUST KNOW

---

## Scenario

**Given this code, why is the output wrong?**

```java
public class CounterRace {
    private static int count = 0;

    public static void main(String[] args) throws Exception {
        Thread t1 = new Thread(CounterRace::increment);
        Thread t2 = new Thread(CounterRace::increment);
        t1.start();
        t2.start();
        t1.join();
        t2.join();
        System.out.println(count); // Sometimes 1
    }

    private static void increment() {
        count++; // Not atomic
    }
}
```

**Problem:** `count++` is a read-modify-write operation and not atomic.

---

## Key Principle

**Synchronization makes a critical section atomic and visible across threads.**

---

## Why It Happens (Simple English)

Two threads read the same value, both increment, and write back. One update is lost. Synchronization ensures only one thread executes that block at a time and that updates are visible to other threads.

---

## Implementing Synchronization

```java
public class SynchronizedCounter {
    private static int count = 0;

    public static void main(String[] args) throws Exception {
        Thread t1 = new Thread(SynchronizedCounter::increment);
        Thread t2 = new Thread(SynchronizedCounter::increment);
        t1.start();
        t2.start();
        t1.join();
        t2.join();
        System.out.println(count); // Always 2
    }

    private static synchronized void increment() {
        count++;
    }
}
```

---

## Wrong vs Right

| ❌ Wrong | ✅ Right |
|---|---|
| Unsynchronized read-modify-write | `synchronized` or `AtomicInteger` |

**Wrong:**
```java
count++;
```

**Right:**
```java
synchronized (lock) {
    count++;
}
```

---

## Other Options

```java
import java.util.concurrent.atomic.AtomicInteger;

AtomicInteger count = new AtomicInteger(0);
count.incrementAndGet();
```

---

## Interview Tip (Exact Answer)

"Synchronization protects a critical section so only one thread updates shared state at a time and changes are visible to others. For simple counters I use `AtomicInteger` because it is lock-free and faster." 

---

## Quick Checklist

- Use `synchronized` for critical sections.
- Keep synchronized blocks short.
- Prefer `AtomicInteger` for counters.
- Avoid holding locks during blocking I/O.

---

## Critical Pitfalls

- Over-synchronization hurts performance.
- Locking different objects does not protect the same data.
- Holding a lock during I/O can cause deadlocks.

---

## Follow-up Questions & Answers

**Q:** Does `synchronized` also guarantee visibility?

**A:** Yes, it establishes a happens-before relationship.

**Q:** Is `volatile` a replacement for `synchronized`?

**A:** No. `volatile` guarantees visibility, not atomicity.

---

## How to Use for Interviews

- Explain that `count++` is not atomic.
- Say `synchronized` gives atomicity + visibility.
- Mention `AtomicInteger` as a faster alternative for counters.

---

**Last Updated:** March 5, 2026
