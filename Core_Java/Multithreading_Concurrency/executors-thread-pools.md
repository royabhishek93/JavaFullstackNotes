# Executors and Thread Pools

**Interview Priority:** Senior: 🔥 MUST KNOW | Mid: 🔥 MUST KNOW

---

## Scenario

**Given this code, what can go wrong?**

```java
public class UnboundedThreads {
    public static void main(String[] args) {
        for (int i = 0; i < 100_000; i++) {
            new Thread(() -> work()).start();
        }
    }

    private static void work() {
        try {
            Thread.sleep(1000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
```

**Problem:** Creating thousands of OS threads can crash the JVM or the OS.

---

## Key Principle

**Thread pools reuse a bounded number of threads and control concurrency.**

---

## Why It Happens (Simple English)

Every platform thread is expensive. Without a limit, the OS runs out of memory or context-switches too much. Executors keep a fixed or managed number of threads and queue the rest.

---

## ExecutorService Basics

```java
import java.util.concurrent.*;

public class ExecutorExample {
    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(4);

        Future<Integer> f = pool.submit(() -> 1 + 2);
        System.out.println(f.get()); // 3

        pool.shutdown();
    }
}
```

---

## Implementing ExecutorService (Custom)

```java
import java.util.concurrent.*;

public class CustomPoolExample {
    public static void main(String[] args) {
        ThreadPoolExecutor pool = new ThreadPoolExecutor(
            2,                 // core threads
            4,                 // max threads
            30, TimeUnit.SECONDS,
            new ArrayBlockingQueue<>(100),
            new ThreadPoolExecutor.CallerRunsPolicy() // backpressure
        );

        for (int i = 0; i < 10; i++) {
            pool.execute(() -> work());
        }

        pool.shutdown();
    }

    private static void work() {
        try {
            Thread.sleep(200);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
```

---

## ScheduledExecutorService (Periodic Tasks)

```java
import java.util.concurrent.*;

public class ScheduledExample {
    public static void main(String[] args) {
        ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);

        scheduler.scheduleAtFixedRate(
            () -> System.out.println("heartbeat"),
            0, 1, TimeUnit.SECONDS
        );
    }
}
```

---

## Wrong vs Right

| ❌ Wrong | ✅ Right |
|---|---|
| `new Thread()` for each task | `ExecutorService` with bounded pool |
| No backpressure | Queue + rejection policy |

**Wrong:**
```java
new Thread(() -> task()).start();
```

**Right:**
```java
ExecutorService pool = Executors.newFixedThreadPool(8);
pool.submit(() -> task());
```

---

## Interview Tip (Exact Answer)

"I use `ExecutorService` to bound concurrency and reuse threads. For CPU work I use a fixed pool sized to cores. For I/O work I use a larger or virtual-thread pool. I also choose a rejection policy to handle overload."

---

## Quick Checklist

- Fixed pool for CPU-bound tasks.
- Larger pools or virtual threads for I/O.
- Always call `shutdown()`.
- Use backpressure (queue + rejection policy).

---

## Critical Pitfalls

- `Executors.newCachedThreadPool()` can create unbounded threads.
- Forgetting `shutdown()` causes JVM to hang on exit.
- Too large pool = context switching overhead.

---

## Follow-up Questions & Answers

**Q:** How many threads for CPU tasks?

**A:** Usually number of cores (or cores + 1). More threads just add context switches.

**Q:** When to use ScheduledExecutorService?

**A:** For periodic tasks like cleanup, metrics, or heartbeats.

---

## How to Use for Interviews

- Mention pool size rules (CPU vs I/O).
- Explain why unbounded threads are dangerous.
- Mention rejection policy.

---

**Last Updated:** March 5, 2026
