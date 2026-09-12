# Thread Pools and ThreadPoolExecutor — Core Size, Max Size, Queueing and Rejection Policies

## What is this? (Plain English)

Think of a customer support call center. The company keeps a fixed number of agents always on duty, even during quiet hours — that's the **core pool**. When call volume increases and all agents are busy, new callers are put **on hold in a queue** instead of being rejected immediately. If the hold queue also fills up, the center calls in **temporary overflow agents**, but only up to a hard limit on total staff — that's the **maximum pool**. If every agent (core + overflow) is busy and the hold queue is also full, the next caller gets a busy signal — that's a **rejected task**.

A Java thread pool works the same way: it is a collection of reusable worker threads that pick up submitted tasks. Once a thread finishes a task, it doesn't die — it goes back to the pool and waits for the next task, so the same threads are reused across many tasks instead of creating a brand-new thread every time.

## The Problem It Solves

Before thread pools, every incoming task meant creating a brand-new `Thread`. That's expensive and unbounded:

- **Thread creation takes real time and memory.** Creating a thread means allocating a stack, a program counter, and other per-thread bookkeeping. Doing this for every single task adds overhead on every request.
- **No control over how many threads exist.** If 100 tasks arrive, the naive approach creates 100 threads. But a machine might only have 2 CPU cores. Only 2 threads can truly run in parallel at any instant — the rest just sit in line for CPU time.
- **Excessive context switching wastes CPU time.** With too many threads competing for too few cores, the CPU spends more time saving/restoring thread state (context switching) than doing actual work. During a context switch the CPU is effectively idle, not processing anything useful.

A thread pool solves this by:
1. **Reusing threads** — threads are created once and kept alive, saving thread-creation time on every task.
2. **Abstracting lifecycle management** — the executor framework manages each thread's life cycle (new → runnable → running → waiting → terminated) for you.
3. **Bounding the number of threads** — by capping how many threads can exist, the pool keeps context switching under control and improves overall throughput.

Java provides this as a framework in `java.util.concurrent`:
- `Executor` — the top interface, exposes only `execute(Runnable)`.
- `ExecutorService` — extends `Executor`, adds lifecycle management methods like `shutdown()`, `shutdownNow()`, `isTerminated()`.
- `ThreadPoolExecutor` and `ForkJoinPool` — concrete classes that implement `ExecutorService`.
- `ScheduledExecutorService` — extends `ExecutorService`, adds the ability to run tasks at a scheduled time / fixed interval.

## Task Submission Flow (ThreadPoolExecutor)

```
[Task submitted to ThreadPoolExecutor]
           v
   Is a core pool thread free?
     Yes │              │ No, all core threads busy
         v              v
 [Assign task to     Is there space in the work queue?
  that free thread]     Yes │              │ No, queue is full
         │               v              v
         │   [Add task to queue,   Current pool size < maximumPoolSize?
         │    wait for a thread      Yes │              │ No, maximumPoolSize reached
         │    to become free]           v              v
         │                    [Create new thread,  [Task is REJECTED
         │                     assign task to it]   RejectedExecutionHandler invoked]
         │                           │
         v                           v
            [Thread finishes task, returns to pool]
                          v
              Any task waiting in the queue?
                Yes │              │ No, thread idle
                    v              v
        [Pick up next        allowCoreThreadTimeOut = true
         queued task]          AND idle time > keepAliveTime?
                                  Yes │          │ No
                                      v          v
                          [Idle thread    [Thread stays alive
                           terminated]     in the pool, waiting]
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

Key rules the transcript walks through:
- **Core pool threads are created up front** (per `corePoolSize`) and, by default, stay alive even while idle.
- **New tasks always try a free core thread first.** Only if all core threads are busy does the task go to the **queue**.
- **The queue is tried before creating extra threads**, even if `maximumPoolSize` hasn't been reached yet. The reasoning: core threads are sized for the *average* load, and the queue absorbs short bursts. Spinning up extra threads for every burst would leave those extra threads sitting idle in the pool once the burst subsides, when the queue could have absorbed it just fine using the existing core threads.
- **Only when the queue is also full** does the executor check if it can create a new thread (up to `maximumPoolSize`).
- **If the pool is at `maximumPoolSize` and the queue is full**, the task is rejected and handed to the `RejectedExecutionHandler`.
- **`keepAliveTime` + `allowCoreThreadTimeOut`** control whether idle threads get terminated: if `allowCoreThreadTimeOut` is `true`, any thread idle for longer than `keepAliveTime` is eliminated. By default `allowCoreThreadTimeOut` is `false`, so `keepAliveTime` has no effect and threads stay alive indefinitely even when idle.

## Key Code / Config

### Constructor parameters

| Parameter | Meaning |
|---|---|
| `corePoolSize` | Number of threads created up front and kept in the pool, even if idle. |
| `maximumPoolSize` | Hard cap on the total number of threads the pool can ever create. |
| `keepAliveTime` + `TimeUnit` | How long an idle thread can live before being eliminated — only takes effect if `allowCoreThreadTimeOut` is set to `true`. |
| `workQueue` (`BlockingQueue<Runnable>`) | Holds tasks waiting for a free thread. Can be **bounded** (fixed capacity, e.g. `ArrayBlockingQueue`) or **unbounded** (no fixed capacity, e.g. `LinkedBlockingQueue`). Bounded queues are generally preferred for full control over how many tasks can be waiting. |
| `threadFactory` | Lets you customize how each worker thread is created — thread name, priority, daemon flag. |
| `RejectedExecutionHandler` | Called when a task cannot be accepted (pool at max size and queue full). |

### Built-in rejection handlers

- **`AbortPolicy`** — throws a `RejectedExecutionException`.
- **`DiscardPolicy`** — silently drops the rejected task, no exception, no notification.
- **`CallerRunsPolicy`** — runs the rejected task on the thread that submitted it (the caller's own thread), instead of a pool thread.
- **`DiscardOldestPolicy`** — removes the oldest task currently sitting in the queue and adds the new task in its place.

### Creating a custom ThreadPoolExecutor with a custom thread factory and rejection handler

```java
import java.util.concurrent.*;

public class ThreadPoolDemo {

    // Custom ThreadFactory: control thread name, priority, and daemon flag
    static class MyCustomThreadFactory implements ThreadFactory {
        @Override
        public Thread newThread(Runnable r) {
            Thread thread = new Thread(r);
            thread.setPriority(Thread.NORM_PRIORITY);
            thread.setDaemon(false);
            thread.setName("custom-worker");
            return thread;
        }
    }

    // Custom RejectedExecutionHandler: log the rejected task instead of throwing/discarding silently
    static class CustomRejectHandler implements RejectedExecutionHandler {
        @Override
        public void rejectedExecution(Runnable r, ThreadPoolExecutor executor) {
            System.out.println("Task rejected: " + r.toString());
        }
    }

    public static void main(String[] args) {
        ThreadPoolExecutor executor = new ThreadPoolExecutor(
                2,                              // corePoolSize
                4,                              // maximumPoolSize
                10,                             // keepAliveTime
                TimeUnit.MINUTES,               // unit for keepAliveTime
                new ArrayBlockingQueue<>(2),    // bounded work queue, capacity 2
                new MyCustomThreadFactory(),
                new CustomRejectHandler()
        );

        for (int i = 1; i <= 4; i++) {
            int taskId = i;
            executor.submit(() -> {
                System.out.println("Task " + taskId + " processed by " + Thread.currentThread().getName());
                try {
                    Thread.sleep(5000); // simulate work taking time
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            });
        }

        executor.shutdown();
    }
}
```

With `corePoolSize=2`, `maximumPoolSize=4`, queue capacity `2`, submitting 4 tasks results in: task 1 and 2 picked up immediately by the 2 core threads, tasks 3 and 4 placed in the queue, and no new threads created — the same 2 core threads pick up tasks 3 and 4 once they finish. Submitting a 5th task (all core threads busy, queue full) causes a new thread to be created (since `maximumPoolSize` allows it) to handle it immediately. Submitting a 7th task when 4 threads are already busy and the queue (capacity 2) is full causes that task to be rejected, since `maximumPoolSize=4` has been reached.

### Lifecycle methods

```java
executor.shutdown();     // Stop accepting new tasks, but let already-submitted/running tasks finish, then move to TERMINATED.
executor.shutdownNow();  // Stop accepting new tasks AND forcefully stop currently running tasks, then move to TERMINATED.
executor.isTerminated(); // Check whether the executor has fully terminated (all threads eliminated).
```

- **RUNNING** — accepts new tasks via `submit()`.
- **SHUTDOWN** (after `shutdown()`) — no new tasks accepted, existing tasks continue to completion, then moves to TERMINATED.
- **STOP** (after `shutdownNow()`) — no new tasks accepted, existing running tasks are forcefully stopped, then moves to TERMINATED.
- **TERMINATED** — all threads eliminated; there is no way back from this state.

## Interview Q&A

**Q1: Why use a thread pool instead of creating a new `Thread` for every task?**
A: Creating a thread is expensive — it requires allocating a stack, a program counter, and other per-thread memory, which takes time on every task. A thread pool creates threads once and reuses them, saving that creation cost. It also caps the total number of threads, which keeps context switching under control (fewer threads competing for limited CPU cores means less time wasted saving/restoring thread state), and it abstracts away manual thread life-cycle management.

**Q2: Walk through what happens internally when you call `submit()` on a `ThreadPoolExecutor`.**
A: First, it checks if a core pool thread is free — if yes, the task is assigned to it directly. If all core threads are busy, it tries to place the task in the work queue. If the queue is also full, it checks whether a new thread can be created without exceeding `maximumPoolSize` — if so, it creates one and assigns the task to it. If the pool is already at `maximumPoolSize` and the queue is full, the task is handed to the `RejectedExecutionHandler`.

**Q3: What's the difference between `corePoolSize` and `maximumPoolSize`?**
A: `corePoolSize` is the number of threads created up front and kept alive in the pool even when idle (by default) — these handle the average/steady load. `maximumPoolSize` is the hard ceiling on total threads; extra threads beyond `corePoolSize` are only created when both the core threads are busy and the queue is full, to absorb sudden bursts.

**Q4: Why does the executor try to queue a task first instead of immediately spinning up a new thread (when `maximumPoolSize` allows it)?**
A: Because `corePoolSize` is sized for the typical/average load, and the queue exists to absorb short bursts using those same core threads. If the executor instead created new threads for every burst, those extra threads would finish their burst work and then sit idle in the pool — wasting the resources that were supposed to only be sized for the average case. Queueing first keeps the pool lean and only escalates to new threads when the queue itself proves insufficient.

**Q5: What's the difference between `shutdown()` and `shutdownNow()`?**
A: `shutdown()` stops the executor from accepting new tasks but lets already-running and already-queued tasks finish normally before moving to the terminated state. `shutdownNow()` stops accepting new tasks *and* forcefully stops tasks that are currently running, then moves to terminated immediately.

**Q6: How would you decide what `corePoolSize` and `maximumPoolSize` should be for a real thread pool — why not just pick 10 or 20?**
A: It depends on several factors: number of CPU cores (fewer cores means fewer threads should run to avoid excessive context switching), available JVM/heap memory (each thread needs stack space, and each request may hold data in the heap), whether the workload is CPU-intensive or IO-intensive (IO-intensive workloads can support more threads since threads sit idle during IO instead of using CPU), the required concurrency level, and per-request memory usage. One starting-point formula is `numberOfThreads = numberOfCPUCores * (1 + waitTime/processingTime)`, where `waitTime` is time spent idle (e.g. waiting on IO) and `processingTime` is actual CPU processing time — a highly CPU-intensive task pushes this ratio toward the number of CPU cores. This formula alone doesn't account for memory, so it should be cross-checked against how much heap/JVM memory is available for threads and per-request data, and refined further with iterative load testing.
