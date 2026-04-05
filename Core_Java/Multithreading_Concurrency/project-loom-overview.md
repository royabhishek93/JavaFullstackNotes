# Project Loom (Why It Exists + What It Enables)

**Interview Priority:** Senior: 🔥 MUST KNOW | Mid: 👍 GOOD TO KNOW

---

## Scenario

**Given this code, why does it not scale?**

```java
public class BlockingWorkflow {
    public static void main(String[] args) throws Exception {
        for (int i = 0; i < 100_000; i++) {
            new Thread(() -> {
                try {
                    Thread.sleep(1000); // Simulated blocking call
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }).start();
        }
    }
}
```

**Problem:** Platform threads are expensive. 100k OS threads will crash most systems.

---

## Key Principle

**Project Loom makes thread-per-task practical again by introducing virtual threads.**

---

## Why It Happens (Simple English)

Java's classic model uses **OS threads**. Each thread consumes memory and OS resources. Loom introduces **virtual threads**, which are managed by the JVM and multiplexed on a small set of OS threads (carrier threads). This keeps the same simple blocking programming style, but with massive scalability.

---

## The Need for a New Model

- Reactive APIs are powerful but complex.
- Thread-per-request is simple but did not scale with OS threads.
- Loom makes **blocking code scalable**, so you can keep the simple model.

---

## Project Loom and Virtual Threads

```java
public class LoomExample {
    public static void main(String[] args) {
        Thread.startVirtualThread(() -> {
            // Looks blocking, but JVM parks it cheaply
            doBlockingIO();
        });
    }

    private static void doBlockingIO() {
        try {
            Thread.sleep(1000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
```

---

## Platform Threads vs Virtual Threads

| Feature | Platform Thread | Virtual Thread |
|---|---|---|
| Cost to create | High | Very low |
| Blocking | Expensive | Cheap (parked by JVM) |
| Best for | CPU work | I/O work |
| Count | Thousands | Millions |

---

## Wrong vs Right

| ❌ Wrong | ✅ Right |
|---|---|
| Huge number of OS threads | Millions of virtual threads |
| Complex reactive flow for simple I/O | Simple blocking code + virtual threads |

**Wrong:**
```java
new Thread(() -> blockingIO()).start();
```

**Right:**
```java
Thread.startVirtualThread(() -> blockingIO());
```

---

## Interview Tip (Exact Answer)

"Project Loom introduces virtual threads so Java can keep simple blocking code while scaling like async systems. It maps many virtual threads onto a few carrier threads, which makes thread-per-request practical again."

---

## Quick Checklist

- Loom = virtual threads + scalable blocking.
- Virtual threads are cheap and park on I/O.
- Use for I/O-heavy workloads.
- Keep CPU work on bounded pools.

---

## Critical Pitfalls

- Mixing long synchronized blocks with blocking I/O can pin carriers.
- Loom does not make CPU work faster.
- ThreadLocal usage can explode memory with millions of threads.

---

## Follow-up Questions & Answers

**Q:** Does Loom replace reactive programming?

**A:** It reduces the need for reactive code in many I/O-heavy cases, but reactive still helps for streaming and backpressure-heavy systems.

**Q:** Is Loom only virtual threads?

**A:** Loom also brings structured concurrency APIs that help manage task lifecycles cleanly.

---

## How to Use for Interviews

- Pick this topic for Java 21+ or concurrency-heavy roles.
- Explain "virtual threads = scalable blocking" in one sentence.
- Show the platform vs virtual comparison table.

---

**Last Updated:** March 5, 2026
