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

## Focused Interview Notes (10-15 minutes each)

| File | Coverage |
|------|----------|
| [virtual-threads-basics.md](virtual-threads-basics.md) | Virtual threads, creation patterns, performance notes |
| [project-loom-overview.md](project-loom-overview.md) | Why Loom exists, platform vs virtual threads |
| [executors-thread-pools.md](executors-thread-pools.md) | ExecutorService, thread pools, scheduling |
| [asynchronous-programming-futures.md](asynchronous-programming-futures.md) | Future vs CompletableFuture |
| [fork-join-framework.md](fork-join-framework.md) | Work stealing and ForkJoinPool |
| [concurrent-collections.md](concurrent-collections.md) | Concurrent collections and pitfalls |
| [thread-synchronization.md](thread-synchronization.md) | `synchronized`, atomicity, visibility |
| [race-conditions-thread-problems.md](race-conditions-thread-problems.md) | Race conditions and visibility bugs |
| [deadlock-scenarios-prevention.md](deadlock-scenarios-prevention.md) | Deadlock causes and prevention |
| [producer-consumer-pattern.md](producer-consumer-pattern.md) | Wait/notify and BlockingQueue |
| [synchronized-methods-thread-blocking.md](synchronized-methods-thread-blocking.md) | Object-level locks and blocking |
| [threadlocal-usage-patterns.md](threadlocal-usage-patterns.md) | ThreadLocal usage and memory leaks |

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
