# ThreadLocal & Virtual Threads vs Platform Threads

## What is this? (Plain English)

**ThreadLocal** gives each individual thread its own *private* copy of a variable, even though every thread is using the exact same `ThreadLocal` object. Think of it like a hotel room key card system: one key-card machine (the `ThreadLocal` object) serves every guest, but each guest (thread) can only ever open their own room (their own private value) — never anyone else's, and they don't have to tell the machine which room they're in, it already knows from who's holding the card.

**Virtual threads** solve a completely different problem: how do you run *thousands* of concurrent tasks without needing thousands of expensive OS threads? A platform (normal) thread is a thin wrapper the JVM puts around one real operating-system thread — a strict **1-to-1 mapping**. A virtual thread is a lightweight, JVM-managed object that only *borrows* an OS thread while it has actual work to do, and gives it back the moment it would otherwise sit idle (e.g., waiting on a DB call).

## The Problem It Solves

**ThreadLocal's problem:** you need per-thread state (e.g., a request's user ID, a correlation ID) without threading it as a parameter through every method call. **The trap:** in a thread pool, threads are *reused* across many tasks. If you don't clean up (`threadLocal.remove()`) after each task, the next task that happens to reuse the same thread will silently inherit the previous task's stale value.

**Virtual threads' problem:** creating an OS thread is an expensive system call (milliseconds, not microseconds) — that's *why* thread pools exist, to avoid repeated thread creation. But even with pooling, a platform thread blocked on I/O (a DB call, an HTTP call) ties up its underlying OS thread for the entire wait — that OS thread does nothing useful during that time. At high concurrency this caps your throughput long before you run out of CPU.

## Platform Threads vs Virtual Threads

```
Platform (Normal) Threads — 1:1 mapping
========================================

┌───────────┐            ┌───────────────┐
│ Thread 1  │──────────> │  OS Thread 1  │
└───────────┘            └───────────────┘

┌───────────┐            ┌───────────────┐
│ Thread 2  │──────────> │  OS Thread 2  │
└───────────┘            └───────────────┘

┌───────────────────────────────┐        ┌──────────────────────────────────────┐
│ Thread 3 (blocked on DB call)  │──────> │ OS Thread 3 — ALSO BLOCKED, wasted   │
└───────────────────────────────┘        └──────────────────────────────────────┘


Virtual Threads — many:few mapping
====================================

┌───────────────────┐   mounted, running    ┌──────────────┐
│ Virtual Thread 1   │──────────────────────>│  OS Thread A │
└───────────────────┘                        └──────────────┘

┌───────────────────┐   mounted, running    ┌──────────────┐
│ Virtual Thread 2   │──────────────────────>│  OS Thread B │
└───────────────────┘                        └──────────────┘

┌───────────────────────────────┐  unmounted while blocked —   ┌──────────────┐
│ Virtual Thread 3               │  OS thread freed up          │              │
│ (blocked on DB call)           │- - - - - - - - - - - - - - ->│  OS Thread A │
└───────────────────────────────┘  (dashed = releases, does         └──────────────┘
                                     not stay mounted)

┌───────────────────┐  picks up the freed OS thread   ┌──────────────┐
│ Virtual Thread 4   │────────────────────────────────>│  OS Thread A │
└───────────────────┘                                  └──────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

- **Platform thread**: `new Thread(...).start()` triggers an actual OS-level system call to create a native thread. It's a strict 1:1 wrapper — 10 Java threads means 10 OS threads, always. If that thread blocks on I/O, its OS thread is idle and wasted for the whole wait.
- **Virtual thread**: entirely managed by the JVM. Many thousands of virtual threads share a small pool of OS "carrier" threads. A virtual thread is only **mounted** onto an OS thread while it has CPU work to do; the moment it would block (e.g., a blocking I/O call), the JVM **unmounts** it and frees the OS thread for some other virtual thread to use. All existing thread APIs remain backward-compatible.
- **The goal is throughput, not lower latency per task** — you can serve far more concurrent requests with the same number of OS threads, because none of them sit idle waiting on I/O.

```java
// Creating a virtual thread directly
Thread.ofVirtual().start(() -> System.out.println("running on a virtual thread"));

// Creating an executor that gives every submitted task its own virtual thread
try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
    executor.submit(() -> System.out.println("task on a virtual thread"));
}
```

## ThreadLocal — Usage and the Cleanup Trap

```java
ThreadLocal<String> nameHolder = new ThreadLocal<>();

nameHolder.set(Thread.currentThread().getName()); // implicitly scoped to whichever thread calls this
System.out.println(nameHolder.get());             // reads back THIS thread's own value only
```

**The reuse trap:** in a 5-thread pool processing many tasks, a thread that handled Task 1 (which set some `ThreadLocal` value) later gets reassigned to Task 4. If Task 1 never called `.remove()`, Task 4 silently sees Task 1's stale leftover value on the same physical thread.

```java
// At the end of every task's processing, always:
nameHolder.remove();
```

## Interview Q&A

**Q: Why do you need to call `ThreadLocal.remove()` explicitly?**
A: Because thread pool threads are reused across many tasks. The `ThreadLocal` value is attached to the physical thread, not to a "task" — if you don't remove it, the next task that happens to run on that same thread will inherit the previous task's stale value, which can leak data across unrelated requests.

**Q: What's the core motivation for virtual threads — lower latency or higher throughput?**
A: Higher throughput. A single task doesn't necessarily complete faster; the win is that far more concurrent tasks can be in flight at once because idle/blocked virtual threads don't tie up a scarce OS thread.

**Q: Do virtual threads require rewriting existing threading code?**
A: No — the goal is full backward compatibility. Everything you already know about `Runnable`, `Callable`, `ExecutorService`, etc. still applies; only the underlying mechanism of how the JVM maps virtual threads onto OS threads changes.

**Q: What actually happens when a virtual thread performs a blocking call?**
A: The JVM detects the blocking point, unmounts the virtual thread from its carrier OS thread, and frees that OS thread to run some other ready virtual thread. When the blocking operation completes, the virtual thread is re-mounted onto (potentially a different) OS thread to continue.

**Q: Is there still a limit on how many platform (OS) threads you control directly with virtual threads?**
A: You no longer directly control the number of OS ("carrier") threads — the JVM manages that pool based on the system's capacity. You only control how many virtual threads you create, which can number in the thousands or more.
