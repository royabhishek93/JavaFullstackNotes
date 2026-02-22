# Multithreading & Concurrency Resources

Advanced Java concurrency, thread safety, and synchronization patterns.

## Deep-Dive Guides (_Guides/ - 60-120 minutes)

| File | Coverage | Study Time |
|------|----------|-----------|
| [java-multithreading-concurrency-guide.md](_Guides/java-multithreading-concurrency-guide.md) | Threads, synchronization, locks, thread pools | 90-120 min |
| [java-volatile-atomic-interview.md](_Guides/java-volatile-atomic-interview.md) | Volatile keyword, atomic operations, memory visibility | 60-90 min |

## Extended Interview Guides (_InterviewGuides/ - 60-90 minutes)

| File | Coverage | Study Time |
|------|----------|-----------|
| [advanced-multithreading-interview.md](_InterviewGuides/advanced-multithreading-interview.md) | 27 questions ranked by importance | 60-90 min |

## Topics Covered

### Core Concepts
- Thread creation and lifecycle
- Synchronization and locks
- Race conditions and deadlocks
- Memory visibility (volatile, happens-before)

### Advanced Patterns
- Thread pools and executors
- Atomic operations (AtomicInteger, AtomicReference)
- Concurrent collections (ConcurrentHashMap, CopyOnWriteArrayList)
- Semaphores, CountDownLatch, CyclicBarrier
- Custom locks and condition variables

### Production Patterns
- ThreadLocal usage and memory leaks
- Executor service shutdown patterns
- Exception handling in concurrent code
- Debugging multi-threaded applications

---

**Suggested study sequence:**
1. Start with one guide file (90 min)
2. Study 27-question interview guide (60 min)
3. Practice: Implement synchronized cache, thread pool executor (2-3 hours)

**Interview frequency:** 50-70% for most questions
