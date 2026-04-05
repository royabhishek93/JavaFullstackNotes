# Virtual Threads (Modern Java)

**Interview Priority:** Senior: 🔥 MUST KNOW | Mid: ✅ SHOULD KNOW

---

## Scenario

**Given this code, what happens under load?**

```java
import java.io.IOException;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.Executors;

public class BlockingServer {
    public static void main(String[] args) throws Exception {
        ServerSocket server = new ServerSocket(8080);

        // Platform thread pool
        var pool = Executors.newFixedThreadPool(200);

        while (true) {
            Socket client = server.accept();
            pool.submit(() -> handle(client));
        }
    }

    private static void handle(Socket client) {
        try {
            // Simulate blocking I/O
            Thread.sleep(2000);
            client.getOutputStream().write("OK".getBytes());
            client.close();
        } catch (IOException | InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
```

**Problem:** 10,000 clients connect. Only 200 platform threads can block at once. Requests queue and latency explodes.

---

## Key Principle

**Virtual threads let you create many cheap threads that block without wasting OS threads.**

---

## Why It Happens (Simple English)

Platform threads are OS threads. They are expensive and limited. When they block on I/O, the OS thread is still occupied. Virtual threads are managed by the JVM, so the JVM can park them when they block and reuse the underlying OS threads (called **carrier threads**) for other work.

---

## Ways to Create Virtual Threads

```java
// 1) Direct start
Thread.startVirtualThread(() -> System.out.println("Hello"));

// 2) Thread builder
Thread.ofVirtual().start(() -> System.out.println("Hello"));

// 3) Executor for virtual threads
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    executor.submit(() -> System.out.println("Hello"));
}
```

---

## Comparing Performance (Platform vs Virtual)

**Scenario:** 10,000 tasks that each sleep for 1 second.

```java
import java.util.concurrent.*;

public class VirtualVsPlatform {
    public static void main(String[] args) throws Exception {
        int tasks = 10_000;

        // Platform threads
        var platformPool = Executors.newFixedThreadPool(200);
        long start1 = System.currentTimeMillis();
        for (int i = 0; i < tasks; i++) {
            platformPool.submit(() -> sleep(1000));
        }
        platformPool.shutdown();
        platformPool.awaitTermination(1, TimeUnit.MINUTES);
        System.out.println("Platform ms: " + (System.currentTimeMillis() - start1));

        // Virtual threads
        long start2 = System.currentTimeMillis();
        try (var vtPool = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < tasks; i++) {
                vtPool.submit(() -> sleep(1000));
            }
        }
        System.out.println("Virtual ms: " + (System.currentTimeMillis() - start2));
    }

    private static void sleep(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
```

**Expected output (approx):**
```
Platform ms: ~50,000+ (queued)
Virtual ms:  ~1,500-3,000 (massive parallel blocking)
```

---

## Wrong vs Right

| ❌ Wrong | ✅ Right |
|---|---|
| Fixed pool for massive blocking I/O | Virtual threads for blocking tasks |
| Blocking calls on limited OS threads | JVM parks virtual threads cheaply |

**Wrong:**
```java
var pool = Executors.newFixedThreadPool(200);
pool.submit(() -> blockingIO());
```

**Right:**
```java
try (var vtPool = Executors.newVirtualThreadPerTaskExecutor()) {
    vtPool.submit(() -> blockingIO());
}
```

---

## Things to Keep in Mind

- Virtual threads shine for **blocking I/O**, not heavy CPU tasks.
- Avoid long synchronized blocks (can **pin** carrier threads).
- ThreadLocal is still per-thread (now millions of threads → memory risk).
- Use structured concurrency when possible (cleaner lifecycle).

---

## Interview Tip (Exact Answer)

"Virtual threads let me scale blocking I/O by parking threads in the JVM instead of blocking OS threads. I use them for request-per-task workloads and keep CPU-heavy work on a small platform pool. I avoid long synchronized blocks to prevent pinning."

---

## Quick Checklist

- Use virtual threads for blocking I/O.
- Keep CPU work on bounded pools.
- Avoid long synchronized sections.
- Watch ThreadLocal memory usage.
- Use structured concurrency where available.

---

## Critical Pitfalls

- **Pinning:** `synchronized` + blocking I/O can pin a carrier thread.
- **Native blocking:** Some native calls do not cooperate with parking.
- **Overuse for CPU:** CPU-heavy tasks still need bounded pools.

---

## Follow-up Questions & Answers

**Q:** Are virtual threads faster than platform threads?

**A:** They are not faster per task. They are cheaper to create and block, so they scale better with many blocking tasks.

**Q:** Do virtual threads replace thread pools?

**A:** For I/O-heavy workloads, yes. For CPU-heavy workloads, you still use bounded pools.

---

## How to Use for Interviews

- Pick this topic if role mentions "Java 21" or "high concurrency".
- Memorize the Interview Tip.
- Explain "virtual threads scale blocking I/O" in 20 seconds.

---

**Last Updated:** March 5, 2026
