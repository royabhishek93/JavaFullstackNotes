# shutdown() vs shutdownNow() vs awaitTermination() — and ScheduledThreadPoolExecutor

## What is this? (Plain English)

Three methods that control how an `ExecutorService` winds down, plus the scheduling methods that let a pool run tasks later or repeatedly. Think of `shutdown()` as telling a restaurant kitchen "stop taking new orders, but finish the ones already cooking." `shutdownNow()` is more like "drop everything right now, even food that's mid-cook." `awaitTermination()` is just a waiter periodically asking "are you closed yet?" for up to a timeout — it doesn't force anything to happen, it only reports back.

## The Problem It Solves

You need graceful, predictable pool shutdown so you don't leak threads, corrupt in-flight work, or hang your application on exit — while also being able to *schedule* recurring work (like a cron job) without hand-rolling your own timer thread.

## Shutdown Behavior Comparison

```
                         ┌──────────────────────────────────────────┐
                         │        ExecutorService with:              │
                         │  Thread A running Task-1                  │
                         │  Thread B running Task-2                  │
                         │  Task-3 waiting in queue                  │
                         └──────────────────┬─────────────────────────┘
                                            │
                        ┌───────────────────┴───────────────────┐
                        │                                       │
                        ▼                                       ▼
              ┌───────────────────┐                   ┌───────────────────┐
              │    shutdown()     │                   │  shutdownNow()    │
              └─────────┬─────────┘                   └─────────┬─────────┘
                        │                                        │
        ┌───────────────┼───────────────┐        ┌───────────────┼───────────────────────┐
        ▼               ▼               ▼        ▼               ▼                       ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
│ No new tasks  │ │ Task-1 and    │ │ Task-3 is     │ │ No new tasks  │ │ Task-1 and Task-2 are │ │ Task-3 is NEVER run — │
│ accepted      │ │ Task-2 run to │ │ still picked  │ │ accepted      │ │ INTERRUPTED           │ │ returned as a         │
│               │ │ COMPLETION    │ │ up from queue │ │               │ │ (best-effort — may    │ │ List<Runnable> of     │
│               │ │               │ │ and completed │ │               │ │ not stop immediately) │ │ un-started tasks      │
└───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘ └───────────────────────┘ └───────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

- **`shutdown()`**: stops accepting new submissions. Already-submitted and already-running tasks (including ones still sitting in the queue) run to completion normally. The calling thread does **not** wait — it returns immediately and moves to the next line.
- **`shutdownNow()`**: also stops new submissions, but additionally **interrupts** actively-running tasks (a *best-effort* attempt — a task that ignores `InterruptedException` won't actually stop) and returns the list of tasks that were still waiting in the queue and never got a chance to start.
- **`awaitTermination(timeout, unit)`**: purely observational. Blocks the *calling* thread for up to `timeout`, checking whether the pool has actually finished shutting down. Returns `true` if it terminated within that window, `false` otherwise. It must be called *after* `shutdown()`/`shutdownNow()` — calling it before either has no useful effect. It does not force anything to stop; it is purely a wait-and-check.

```java
ExecutorService pool = Executors.newFixedThreadPool(5);
pool.submit(() -> { Thread.sleep(5000); System.out.println("task completed"); });

pool.shutdown();                 // returns immediately; task above still runs for 5s in background
System.out.println("main thread finished");

boolean terminated = pool.awaitTermination(2, TimeUnit.SECONDS); // waits up to 2s
System.out.println("terminated? " + terminated); // false — 5s task hasn't finished yet after only 2s wait
```

## ScheduledThreadPoolExecutor — the 4 scheduling methods

`ScheduledThreadPoolExecutor` extends `ThreadPoolExecutor` and adds four scheduling-specific methods:

| Method | Runs | Formula for next run |
|---|---|---|
| `schedule(Runnable, delay, unit)` | Once | N/A |
| `schedule(Callable, delay, unit)` | Once, returns a value via `Future.get()` | N/A |
| `scheduleAtFixedRate(task, initialDelay, period, unit)` | Repeats | `previousStartTime + period` |
| `scheduleWithFixedDelay(task, initialDelay, delay, unit)` | Repeats | `previousFinishTime + delay` |

```java
ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(5);

// Run once after 5 seconds
scheduler.schedule(() -> System.out.println("hello"), 5, TimeUnit.SECONDS);

// Run once after 5 seconds, returning a value
Future<String> future = scheduler.schedule(() -> "hello", 5, TimeUnit.SECONDS);
System.out.println(future.get());

// Repeat: first run after 3s, then every 5s after each run STARTS
ScheduledFuture<?> handle = scheduler.scheduleAtFixedRate(
    () -> System.out.println("hello"), 3, 5, TimeUnit.SECONDS);
scheduler.schedule(() -> handle.cancel(true), 10, TimeUnit.SECONDS); // stop after 10s

// Repeat: first run after 3s, then every 5s after each run FINISHES
scheduler.scheduleWithFixedDelay(
    () -> System.out.println("hello"), 3, 5, TimeUnit.SECONDS);
```

**Key overrun behavior:** if a `scheduleAtFixedRate` task takes *longer* than the period (e.g. runs for 6 seconds against a 5-second period), the next run is **not** started in parallel — it's simply queued and starts as soon as the previous run finishes, so back-to-back long runs cause the schedule to drift later and later. `scheduleWithFixedDelay` never has this ambiguity because its clock only starts *after* the previous run completes.

## Interview Q&A

**Q: If you call `shutdown()`, does the main thread wait for running tasks to finish?**
A: No. `shutdown()` returns immediately; it only stops new submissions. The already-running/queued tasks keep executing on their own threads in the background.

**Q: What does `awaitTermination()` actually do — does it stop the pool?**
A: No, it does nothing to the pool itself. It's a blocking check: the calling thread waits up to the given timeout for the pool to report that it has terminated, and returns `true`/`false` accordingly. Call it after `shutdown()`, not instead of it.

**Q: Is `shutdownNow()` guaranteed to stop running tasks immediately?**
A: No — it's "best-effort." It calls `Thread.interrupt()` on running task threads. If a task doesn't check `Thread.interrupted()` or handle `InterruptedException`, it will simply continue running.

**Q: What's the practical difference between `scheduleAtFixedRate` and `scheduleWithFixedDelay` when a task overruns its interval?**
A: `scheduleAtFixedRate` computes the next run relative to the previous **start** time, so if a task overruns, the next execution is queued to start the instant the current one finishes (no parallel execution) — causing schedule drift. `scheduleWithFixedDelay` computes the next run relative to the previous **finish** time, guaranteeing a fixed "cool-down" gap regardless of how long the task took.

**Q: Why must `awaitTermination()` be called after `shutdown()`, not before?**
A: Before `shutdown()`, the pool is still accepting work and has no reason to terminate — `awaitTermination()` would just block for the full timeout and return `false`, since nothing is transitioning to a terminated state.
