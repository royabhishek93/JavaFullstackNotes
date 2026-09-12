# #129 — Virtual Threads Deep Dive — Pinning and Monitoring

> **Category:** JVM Tuning Production Playbook | **Type:** Advanced Scenario Q&A | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"We migrated to Java 21 virtual threads. We're seeing unexpected blocking behavior. The CPU is at 100% on the carrier threads. What are you looking for?"

## 😊 Explain It Simply (for anyone)
Imagine a small team of expert drivers (carrier/platform threads) who can each drive an unlimited number of passengers (virtual threads) by cleverly hopping between cars whenever one passenger is just sitting and waiting (waiting on I/O like a database call) — the driver hops out and drives someone else in the meantime. But sometimes a passenger insists the driver *personally* stay glued to the wheel and can't leave, even while waiting (this is "pinning," caused by things like `synchronized` blocks) — now that one driver is stuck babysitting a single waiting passenger instead of serving everyone else. If enough passengers all demand this "stay glued" treatment at once, you effectively run out of drivers even though you have thousands of passengers waiting to be served.

## 📊 Visualize It
```
Normal (no pinning):            Pinned (bad):
Carrier Thread                  Carrier Thread
  │                                │
  ├─ VThread A (I/O wait) ─┐       ├─ VThread A (synchronized, I/O wait)
  │   unmounts, carrier     │      │   CANNOT unmount — carrier stuck too
  │   free to run others    ▼      │
  └─ VThread B runs now ✅         └─ VThread B/C/... starved ❌
```

## 🏭 The Real Production Answer (15-YOE Level)
> "Virtual thread pinning — one of the key gotchas of Java 21 virtual threads.
>
> Background: Virtual threads are multiplexed onto platform threads (carrier threads). When a virtual
> thread is waiting on I/O, it unmounts from the carrier thread, which is free to run another virtual
> thread. This is the magic that makes virtual threads efficient.
>
> Pinning: A virtual thread becomes 'pinned' to its carrier thread and cannot unmount when:
> 1. Inside a synchronized block or method
> 2. Calling a native method
>
> When pinned threads block (e.g., waiting for DB response), the carrier thread is also blocked.
> With 8 carrier threads (default = CPU count) and 8 pinned virtual threads all blocked on DB,
> no other virtual threads can run. CPU goes to 0% (not 100% — I need to correct the premise:
> if all carriers are blocked, CPU would be near 0%, not 100%.
> 100% CPU on carrier threads suggests actual computation, not blocking.)
>
> Diagnostic:
>   // Enable pinning detection:
>   -Djdk.tracePinnedThreads=full
>   // Or full logging:
>   -Djdk.tracePinnedThreads=short
>
>   // JFR virtual thread events:
>   jfr print --events jdk.VirtualThreadPinned recording.jfr
>
>   // Count carrier threads:
>   -Djdk.virtualThreadScheduler.parallelism=16
>   (default = Runtime.getRuntime().availableProcessors())
>
> Common pinning sources in Spring:
> - JDBC drivers using synchronized internally (Oracle, MySQL old versions)
>   Fix: Use async/reactive driver or wait for JDBC loom support
>   PostgreSQL driver has virtual-thread-friendly mode since 42.7.0
>
> - Caffeine cache has some synchronized methods (fixed in newer versions)
>
> - synchronized(this) in application code — replace with ReentrantLock or use j.u.c.locks
>
> Monitoring virtual threads:
>   jcmd <pid> Thread.dump_to_file -format=json /tmp/vthread-dump.json
>   JConsole: virtual threads appear in thread listing with vthread- prefix"

## 🔑 Key Takeaway
If virtual threads seem stuck, suspect pinning from `synchronized` blocks or old JDBC drivers first — `-Djdk.tracePinnedThreads=full` will show you exactly where.
