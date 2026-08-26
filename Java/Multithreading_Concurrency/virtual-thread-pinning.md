# Virtual Thread Pinning & Carrier Threads

**Interview Priority:** Senior: 🔥 MUST KNOW | Mid: 👍 GOOD TO KNOW

---

## Scenario

**You migrated to virtual threads and expected 10x throughput improvement. You got almost none. What's wrong?**

```java
synchronized void callDatabase() {
    Thread.sleep(500); // I/O inside synchronized block
}
```

**Problem:** Virtual threads are pinned to their carrier thread inside `synchronized` blocks. The carrier thread cannot be reused while the virtual thread blocks — defeating the entire purpose of virtual threads.

---

## Key Principle

**A virtual thread is "pinned" when it cannot be unmounted from its carrier thread. Pinning makes virtual threads behave like platform threads — blocking the carrier.**

---

## How Virtual Threads Work (Normal Case)

```
Virtual Thread ──► Carrier Thread (OS thread)
                        │
                   blocks on I/O
                        │
              JVM unmounts virtual thread
              Carrier picks up another virtual thread
              Virtual thread resumes later on (possibly different) carrier
```

This multiplexing is what makes virtual threads scalable. One carrier can serve thousands of virtual threads.

---

## What Pinning Is

```
Virtual Thread inside synchronized block
        │
   blocks on I/O
        │
   JVM CANNOT unmount — carrier is stuck
   Carrier is blocked for the full duration
   Other virtual threads waiting for this carrier cannot run
```

The carrier thread is **pinned** — monopolized by one virtual thread.

---

## Two Causes of Pinning

### 1. `synchronized` block/method with blocking inside

```java
// PINS the carrier thread
synchronized (lock) {
    Thread.sleep(1000); // blocks inside synchronized
    callDatabase();     // any blocking I/O here pins carrier
}
```

### 2. Native method / `Object.wait()` inside a native frame

```java
// JNI calls can also pin carriers
nativeLibraryCall(); // if it blocks, carrier is pinned
```

---

## How to Fix Pinning — Use ReentrantLock

```java
private final ReentrantLock lock = new ReentrantLock();

void callDatabase() throws InterruptedException {
    lock.lock();
    try {
        Thread.sleep(1000); // virtual thread is parked, carrier is FREE
        // I/O here is fine — carrier can serve other virtual threads
    } finally {
        lock.unlock();
    }
}
```

`ReentrantLock` (and all `java.util.concurrent.Lock` implementations) cooperate with the virtual thread scheduler — the carrier is released when the virtual thread parks.

---

## Diagnosing Pinning

### JVM Flag (prints pinning events to stdout)

```bash
java -Djdk.tracePinnedThreads=full -jar app.jar
# short — shows just the blocking line
java -Djdk.tracePinnedThreads=short -jar app.jar
```

### JFR Event

```
jdk.VirtualThreadPinned
```

Enable with:
```bash
java -XX:StartFlightRecording=filename=app.jfr,settings=default -jar app.jar
```

Look for `jdk.VirtualThreadPinned` events in JMC or `jfr print`.

---

## Carrier Thread Pool

```
ForkJoinPool (common pool, size = CPU cores)
    │
    ├── Carrier Thread 1 ──► Virtual Thread A
    ├── Carrier Thread 2 ──► Virtual Thread B
    ├── Carrier Thread 3 ──► Virtual Thread C (pinned — wasted)
    └── Carrier Thread 4 ──► Virtual Thread D
```

The default carrier pool size equals `Runtime.getRuntime().availableProcessors()`. Pinned threads reduce effective parallelism.

Override with:
```bash
-Djdk.virtualThreadScheduler.parallelism=16
-Djdk.virtualThreadScheduler.maxPoolSize=256  # allows pool to grow when pinning detected
```

---

## Other Virtual Thread Gotchas

### ThreadLocal memory with virtual threads

```java
// ThreadLocal fine for a few threads; memory explodes with millions
static ThreadLocal<HeavyObject> tl = new ThreadLocal<>();
// Use ScopedValue instead for per-request context
```

### Don't pool virtual threads

```java
// WRONG — pooling defeats the purpose
ExecutorService pool = Executors.newFixedThreadPool(100); // 100 platform threads

// RIGHT — one virtual thread per task
ExecutorService vt = Executors.newVirtualThreadPerTaskExecutor();
```

### CPU-bound work still needs a bounded pool

```java
// Virtual threads don't help CPU work — still use fixed pools for that
ExecutorService cpuPool = Executors.newFixedThreadPool(
    Runtime.getRuntime().availableProcessors()
);
```

---

## Summary Table

| Scenario | Virtual Thread Behavior | Fix |
|---|---|---|
| I/O blocking (no sync) | Unmounts, carrier free | Nothing needed |
| `synchronized` + blocking | Pinned — carrier blocked | Replace with `ReentrantLock` |
| CPU-intensive loop | Carrier occupied (expected) | Use bounded platform pool |
| `ThreadLocal` with millions of VTs | Memory spike | Use `ScopedValue` |
| Pooling virtual threads | Wasted overhead | `newVirtualThreadPerTaskExecutor()` |

---

## Wrong vs Right

| ❌ Wrong | ✅ Right |
|---|---|
| `synchronized` + blocking I/O inside | `ReentrantLock` + blocking I/O |
| Pooling virtual threads | One virtual thread per task |
| `ThreadLocal` for request context | `ScopedValue` |
| Ignoring pinning in legacy code | Audit with `jdk.tracePinnedThreads` |

---

## Interview Tip (Exact Answer)

"Virtual thread pinning occurs when a virtual thread cannot be unmounted from its carrier, usually inside a `synchronized` block with blocking I/O. The fix is to replace `synchronized` with `ReentrantLock`, which cooperates with the virtual thread scheduler and releases the carrier when the thread parks. Detect pinning with the `jdk.tracePinnedThreads` JVM flag or `jdk.VirtualThreadPinned` JFR events."

---

## Quick Checklist

- Audit all `synchronized` blocks that contain I/O or `Thread.sleep()`.
- Replace them with `ReentrantLock` for virtual thread compatibility.
- Run with `-Djdk.tracePinnedThreads=short` in staging to find pinning.
- Don't pool virtual threads — create one per task.
- Keep CPU work on a bounded `ForkJoinPool` or fixed platform thread pool.

---

## Critical Pitfalls

- JDBC drivers that use `synchronized` internally will pin (check your driver version; most modern drivers have fixed this).
- Increasing `jdk.virtualThreadScheduler.maxPoolSize` treats the symptom, not the cause.
- Even one heavily pinned path can degrade overall throughput if it monopolizes carrier threads.

---

## Follow-up Questions & Answers

**Q:** Does `ReentrantLock` also pin carriers?

**A:** No. `ReentrantLock.lock()` uses `LockSupport.park()` internally, which cooperates with the virtual thread scheduler and allows the carrier to be released.

**Q:** Will `synchronized` ever be fixed?

**A:** Java 24 introduced a fix (JEP 491) that makes `synchronized` no longer pin virtual threads in many cases. But `ReentrantLock` remains the safe choice for Java 21–23 and library code that must work across versions.

---

## How to Use for Interviews

- Open with the pinning definition: "carrier can't be released, virtual thread blocks like a platform thread."
- Name the two causes: `synchronized` + blocking, and native frames.
- Show `ReentrantLock` as the fix.
- Mention `jdk.tracePinnedThreads` and JFR for diagnosis.
- Note JEP 491 (Java 24) as the long-term platform fix.

---

**Last Updated:** August 18, 2026
