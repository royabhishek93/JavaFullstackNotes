# #70 — Microservice Memory Leak Plus Thread Leak

> **Category:** Thread Dump Analysis | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"Kubernetes pod memory keeps growing. Thread dump shows thread count at 3,000 and growing. What's happening and how do you fix it?"

## 😊 Explain It Simply (for anyone)
Imagine a company that hires a brand new employee for every single phone call instead of reusing existing staff, and then never lays anyone off after the call ends. Within a day, the building is packed with thousands of employees standing around, each one still taking up a desk (memory) even though they finished their one phone call hours ago. That's a **thread leak**: the program keeps creating brand-new threads instead of reusing a pool, and forgets to get rid of them when they're done.

Each thread needs its own small chunk of memory just to exist (like a desk and chair, roughly 512KB–1MB per thread) — so 3,000 threads alone can eat gigabytes of memory even before any real work happens. The fix is the same as any staffing problem: hire a *fixed* team (a bounded thread pool) that handles calls one after another and gets reused, rather than hiring — and never firing — a new person for every call.

## 📊 Visualize It
```
Time →   pool-1-thread-1  (reused, healthy pool worker)
         pool-1-thread-2  (reused, healthy pool worker)

vs.

Time →   Thread-1  Thread-2  Thread-3 ... Thread-2997
         (unnamed, never-ending new Thread() calls
          = LEAK, each eating stack memory forever)
```

## 🏭 The Real Production Answer (15-YOE Level)
"3,000 threads and growing is a thread leak. Threads themselves use memory — default stack size is 512KB to 1MB per thread — so 3,000 threads is potentially 3GB of stack space alone.

The root cause is almost always one of: creating `new Thread()` without a thread pool, using an unbounded `Executors.newCachedThreadPool()` without proper shutdown, or a framework creating per-request threads that aren't being returned to a pool.

In the thread dump, I look at the names. If I see a pattern like `Thread-1`, `Thread-2`, ... `Thread-2997` — those are unnamed threads from `new Thread()` calls, not pool threads. Named pool threads look like `pool-1-thread-1`, `pool-1-thread-2`.

For diagnosis, I'd add:
```java
// JMX monitoring
ManagementFactory.getThreadMXBean().getThreadCount()
// alert when > 500
```

For fix: audit everywhere `new Thread()` is called. Replace with a properly bounded `ExecutorService`. Ensure executors are shut down when the owning component is destroyed.

In Spring: be careful with `@Async` and unbounded task executors. Configure:
```yaml
spring.task.execution.pool.max-size=50
spring.task.execution.pool.queue-capacity=100
```"

## 🔑 Key Takeaway
Unnamed `Thread-N` threads that keep multiplying in the dump mean uncontrolled `new Thread()` calls — replace them with a bounded, properly shut-down `ExecutorService` and alert on total thread count via `ThreadMXBean`.
