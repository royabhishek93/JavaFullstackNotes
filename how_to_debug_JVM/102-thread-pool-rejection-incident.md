# #102 — Thread Pool Rejection — RejectedExecutionException

> **Category:** Common Production Incidents | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"Walk me through diagnosing: `java.util.concurrent.RejectedExecutionException: Task rejected from ThreadPoolExecutor` is appearing, async operations are failing, but CPU and memory both look fine. What's happening and how do you fix it?"

## 😊 Explain It Simply (for anyone)
Picture a small restaurant with a few tables (worker threads), a small waiting area (a queue), and a strict fire-marshal rule: once the waiting area is full AND every table is taken, the host has to turn new customers away at the door instead of letting them cram inside. That "turned away at the door" moment is exactly what `RejectedExecutionException` means — the thread pool (a fixed group of workers) and its queue (the waiting line) are both completely full, so new tasks get flat-out rejected instead of waiting. It's not a memory or CPU problem — the restaurant just doesn't have anywhere left to put people.

## 📊 Visualize It
```
Task submitted --> [corePoolSize threads busy?]
                          |
                    [queue has room?] --yes--> waits in queue
                          | no
                    [below maximumPoolSize?] --yes--> new thread spun up
                          | no
                    REJECTED  <-- RejectedExecutionException
```

## 🏭 The Real Production Answer (15-YOE Level)

**Symptoms:**
- `java.util.concurrent.RejectedExecutionException: Task rejected from ThreadPoolExecutor`
- Async operations failing
- CPU and memory fine, but requests failing

**ThreadPoolExecutor behavior:**
```
Tasks submitted:
  1. Core threads handle them (up to corePoolSize)
  2. Queue buffers them (up to queueCapacity)
  3. New threads created up to maximumPoolSize
  4. Queue full + max threads reached → RejectedExecutionException
```

**Diagnosis:**
```bash
# Check executor queue size via Arthas
ognl "@com.myapp.config.AsyncConfig@executor.getQueue().size()"
ognl "@com.myapp.config.AsyncConfig@executor.getActiveCount()"
ognl "@com.myapp.config.AsyncConfig@executor.getTaskCount()"
```

**Root causes:**
1. Queue capacity too small for burst traffic
2. Consumer (DB / external service) slow, tasks pile up
3. `ThreadPoolExecutor` with `SynchronousQueue` (no buffering) — any rejection with full threads
4. Executor shut down prematurely during graceful shutdown

**Rejection policies:**
```java
ThreadPoolExecutor executor = new ThreadPoolExecutor(
    10, 50,              // core=10, max=50
    60L, SECONDS,
    new LinkedBlockingQueue<>(1000),    // queue capacity
    new ThreadPoolExecutor.CallerRunsPolicy()  // caller thread runs it (backpressure)
    // Other options:
    // AbortPolicy (default) → throws RejectedExecutionException
    // DiscardPolicy          → silently drops (dangerous, lose work)
    // DiscardOldestPolicy    → drops oldest queued task
);
```

## 🔑 Key Takeaway
`RejectedExecutionException` means both the queue and max threads are exhausted — check `getQueue().size()` and `getActiveCount()` before touching CPU or memory tuning.
