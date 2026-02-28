# Q1: Race Condition in Counter Increment

**Study Time:** 8-10 minutes | **Frequency:** 85% in interviews 🔥 | **Difficulty:** ⭐⭐⭐

---

## Scenario

**Given this code, what happens?**

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

        System.out.println(counter.getCount());
    }
}
```

**Expected Output?**
- **No fixed output** (non-deterministic)
- You may see: `1987`, `1993`, `1765`, `2000`, etc.

---

## Key Principle

This program has a **race condition** because `count++` is **not atomic**. It executes in three steps:

1. Read `count`
2. Add 1
3. Write back

If two threads read the same value before either writes, **one increment gets lost**.

---

## Step-by-Step Analysis

Assume `count = 41`:

```
Thread A reads count (41)
Thread B reads count (41)
Thread A writes 42
Thread B writes 42  <-- Lost update
```

So after **2 increments**, count increases by **only 1**.

---

## Why Output Is Non-Deterministic

- Thread scheduling is controlled by the OS
- Each run interleaves thread steps differently
- Results can change per execution

---

## Fix Option 1: `synchronized`

```java
static class Counter {
    private int count = 0;

    public synchronized void increment() {
        count++;
    }

    public int getCount() {
        return count;
    }
}
```

✅ Output becomes deterministic: **always 2000**

---

## Fix Option 2: `AtomicInteger` (Best Practice)

```java
import java.util.concurrent.atomic.AtomicInteger;

static class Counter {
    private final AtomicInteger count = new AtomicInteger(0);

    public void increment() {
        count.incrementAndGet();
    }

    public int getCount() {
        return count.get();
    }
}
```

✅ Output becomes deterministic: **always 2000**

**Why better than synchronized?**
- Non-blocking (no locks)
- Faster under high contention
- Uses CPU atomic instructions (CAS)

---

## Important: `join()` Usage

```java
t1.join();
t2.join();
```

`join()` makes the **main thread wait** until worker threads finish.

**Without `join()`:**
- Main thread may print before increments complete
- Output becomes even more unpredictable

---

## Interview Q&A

### Q1: Why is `count++` not thread-safe?

**Answer:**
```
count++ is a read-modify-write sequence:
- read
- add
- write
If two threads interleave these steps, updates are lost.
```

---

### Q2: How do you fix this race condition?

**Answer:**
```
Option 1: synchronize increment()
Option 2: use AtomicInteger (preferred)
Both ensure atomic updates.
```

---

### Q3: Why is AtomicInteger better than synchronized?

**Answer:**
```
AtomicInteger uses lock-free CAS operations.
It avoids blocking and is more scalable under contention.
```

---

### Q4: What happens if you remove join()?

**Answer:**
```
Main thread may finish before worker threads.
Output can be smaller or inconsistent because
not all increments have completed.
```

---

### Q5: What if there are 3 threads? 5 threads?

**Answer:**
```
Race condition worsens as contention increases.
The more threads, the more lost updates.
```

---

## Common Pitfalls

```java
❌ Pitfall 1: Assuming count++ is atomic

❌ Pitfall 2: Using volatile instead of synchronization
// volatile guarantees visibility, not atomicity

❌ Pitfall 3: Forgetting join()
// Leads to premature print

❌ Pitfall 4: Calling getCount() without synchronization
// If using int, may read a stale value
// With AtomicInteger, safe
```

---

## Interview Answer (Concise)

**Q: "Why does this program print a value less than 2000?"**

**Answer:**

> "This program demonstrates a race condition. Two threads increment the same shared variable, and `count++` is not atomic; it performs read, modify, and write steps. When both threads read the same value before either writes, one update is lost. As a result, the final count is non-deterministic and usually less than 2000. To fix it, make `increment()` synchronized or use `AtomicInteger` with `incrementAndGet()`. Also use `join()` so main waits for worker threads before printing."

---

## Key Takeaways

| Concept | Why It Matters | Interview Score |
|---------|----------------|-----------------|
| Race condition | Core multithreading concept | ⭐⭐⭐⭐⭐ |
| Atomicity vs visibility | Common trick question | ⭐⭐⭐⭐⭐ |
| `synchronized` fix | Fundamental thread-safety | ⭐⭐⭐⭐ |
| `AtomicInteger` | Best-practice concurrency | ⭐⭐⭐⭐ |
| `join()` usage | Prevent premature output | ⭐⭐⭐⭐ |
