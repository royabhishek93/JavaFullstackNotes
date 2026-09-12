# #108 — Lock-Free Alternative Analysis

> **Category:** Thread Dump Analysis | **Type:** Advanced Scenario Q&A | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"Senior architect question: When should you use `synchronized`, `ReentrantLock`, `StampedLock`, or `Atomic*` classes? Give production-relevant guidance."

## 😊 Explain It Simply (for anyone)
Think of four different ways to manage a single shared whiteboard in an office:

1. **Atomic classes** are like a whiteboard with a self-locking mechanism built directly into a single number — anyone can update just that number instantly and safely without ever needing to ask permission, because the whiteboard itself guarantees only one change happens at a time.
2. **`synchronized`** is the simple, old-fashioned rule: "only one person may touch the whiteboard at a time, and if you're waiting, you just stand there patiently until it's free." Simple, but you can get stuck waiting forever with no way to give up.
3. **`ReentrantLock`** is a smarter version of that same rule with an escape hatch: "try to grab the whiteboard, but if it's busy after waiting 5 seconds, give up and go do something else instead of waiting forever."
4. **`StampedLock`** is designed for a whiteboard that's read constantly but rarely written to — instead of always locking it to *read* the current numbers, you peek at it optimistically, and only if someone changed it while you were peeking do you re-check properly. This is much faster when most people are just reading, not writing.

Choosing the right tool depends on how often people write versus just read, and whether you need the ability to give up and retry.

## 📊 Visualize It
```
 Atomic*        → single variable, lock-free, fastest
 synchronized   → simple mutex, no timeout, pins virtual threads
 ReentrantLock  → tryLock(timeout), fair option, virtual-thread friendly
 StampedLock    → optimistic reads, read-heavy workloads, not reentrant
```

## 🏭 The Real Production Answer (15-YOE Level)
"The decision tree I use:

**Use `Atomic*` (AtomicInteger, AtomicReference, etc.) when:**
- Single variable update: counters, flags, references
- CAS (compare-and-swap) semantics are sufficient
- Highest throughput needed, lock-free algorithms
- Example: request counter, cache invalidation flag

**Use `synchronized` when:**
- Simple mutual exclusion, low contention
- Code clarity matters more than maximum performance
- You need `wait()`/`notify()` pattern
- Short critical sections
- Warning: causes carrier thread pinning in virtual threads

**Use `ReentrantLock` when:**
- Need `tryLock()` with timeout (avoids deadlock by giving up)
- Need interruptible lock acquisition
- Need fair ordering (new ReentrantLock(true))
- Using virtual threads (no pinning)
- Multiple conditions needed (`lock.newCondition()`)

**Use `StampedLock` when:**
- Read-heavy workload with rare writes
- Optimistic reads: try without locking, validate, retry with read lock
- Up to 3x faster than `ReadWriteLock` for read-heavy scenarios
- Warning: not reentrant, no condition support

```java
StampedLock lock = new StampedLock();
// Optimistic read — no lock acquired
long stamp = lock.tryOptimisticRead();
double x = this.x, y = this.y; // read values
if (!lock.validate(stamp)) {   // someone wrote — retry with lock
    stamp = lock.readLock();
    try { x = this.x; y = this.y; }
    finally { lock.unlockRead(stamp); }
}
```

In production: for most service-layer code, `ReentrantLock` or `Atomic*`. Reserve `StampedLock` for proven read-heavy bottlenecks measured with JMH."

## 🔑 Key Takeaway
Default to `Atomic*` for single values and `ReentrantLock` for general mutual exclusion; reserve `synchronized` for simple low-contention cases and `StampedLock` only for proven, JMH-measured read-heavy bottlenecks.
