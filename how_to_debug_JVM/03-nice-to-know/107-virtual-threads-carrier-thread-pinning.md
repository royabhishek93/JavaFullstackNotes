# #107 — Virtual Threads and Carrier Thread Pinning

> **Category:** Thread Dump Analysis | **Type:** Advanced Scenario Q&A | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"You've migrated to Java 21 virtual threads for your web layer. Under load you see degraded performance and thread dumps show 'carrier thread pinned' messages. Explain what's happening and how to fix it."

## 😊 Explain It Simply (for anyone)
Imagine a call center where instead of giving every caller their own dedicated agent, the system is smart: it gives an agent to a caller only while they're actively talking, and the moment the caller goes quiet (say, they're looking something up), the agent is instantly freed to help someone else, then reconnected to the original caller when they speak again. This lets a handful of real agents (called "carrier threads," actual OS threads) serve thousands of callers (called "virtual threads," lightweight fake threads that Java 21 introduced) by hot-swapping between them whenever someone goes idle.

But there's a catch: if a caller insists on keeping the *same specific* agent glued to them the entire time — refusing to let go even while silent — that agent becomes stuck, unable to help anyone else. This "stuck agent" situation is called **pinning**, and it happens specifically when code uses old-style `synchronized` blocks, which don't know how to release the agent temporarily. The fix is to swap that old-style lock for a newer one (`ReentrantLock`) that plays nicely with the hot-swapping trick.

## 📊 Visualize It
```
Carrier thread (real OS thread)
   │
   ├─ virtual thread A (normal I/O wait) → UNMOUNTS, carrier freed
   │
   └─ virtual thread B (inside synchronized) → PINNED!
         carrier thread STUCK, can't serve anyone else
         (defeats the purpose of virtual threads)
```

## 🏭 The Real Production Answer (15-YOE Level)
"Virtual threads in Project Loom run on top of platform (carrier) threads from a ForkJoinPool. Normally, when a virtual thread blocks on I/O or `Object.wait()`, it unmounts from the carrier thread, freeing the carrier to run other virtual threads. This is the whole value proposition.

But carrier thread *pinning* happens when a virtual thread cannot unmount from its carrier. Two causes:
1. The virtual thread is inside a `synchronized` block or method
2. The virtual thread calls native code that holds a JNI monitor

When pinned, the virtual thread holds the carrier thread captive — defeating the entire purpose of virtual threads. Under load with many pinned virtual threads, you exhaust the ForkJoinPool's carrier threads and you're back to the old problem.

In a Java 21 thread dump:
```
#119 virtual  [carrier thread: ForkJoinPool.commonPool-worker-3]
    java.lang.VirtualThread$VThreadContinuation.onPinned(VirtualThread.java:...)
    -- Carrier thread pinned --
    at com.corp.LegacyService.processRequest(LegacyService.java:78)
    - locked <0x000000076c> (synchronized method — cause of pinning)
```

The JVM flag `-Djdk.tracePinnedThreads=full` logs whenever a virtual thread gets pinned.

Fix: replace `synchronized` with `ReentrantLock` in hot paths:
```java
// Before — causes pinning
public synchronized void processRequest() { ... }

// After — virtual thread friendly
private final ReentrantLock lock = new ReentrantLock();
public void processRequest() {
    lock.lock();
    try { ... }
    finally { lock.unlock(); }
}
```"

## 🔑 Key Takeaway
`synchronized` blocks pin virtual threads to their carrier thread and defeat Loom's whole scaling benefit — swap hot-path `synchronized` for `ReentrantLock` and use `-Djdk.tracePinnedThreads=full` to find the offenders.
