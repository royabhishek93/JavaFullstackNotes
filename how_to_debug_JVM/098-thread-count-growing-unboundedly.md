# #98 — Spring Boot Service Thread Count Growing Unboundedly

> **Category:** JVM Tuning Production Playbook | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"jstack shows our service growing from 50 threads at startup to 800+ threads over several hours. Memory is fine, but response times degrade as threads grow. Root cause?"

## 😊 Explain It Simply (for anyone)
Imagine a call center (your service) that, instead of routing calls to a fixed team of 50 operators, keeps hiring a brand-new operator (a new thread) for every single incoming call and never lets any of them go home — even after their call ends. Within hours you have 800 operators crammed into a room built for 50, and even though there's technically enough "desk space" (memory is fine), everyone is bumping into each other and stepping on each other's toes (context-switching and lock contention), so it actually gets slower to handle calls, not faster. The modern fix (Java 21 virtual threads) is like giving each caller a lightweight sticky note instead of a full-time employee — cheap to create, cheap to discard, no crowding.

## 📊 Visualize It
```
Thread Count
 800 |                              ▄▄▄▄▄▄▄
     |                    ▄▄▄▄▄▄▄▄▄
     |          ▄▄▄▄▄▄▄▄▄▄
  50 |▄▄▄▄▄▄▄▄▄▄
     └──────────────────────────────────────► time (hours)
     Unbounded executor/thread pool never shrinks back down
```

## 🏭 The Real Production Answer (15-YOE Level)
> "Thread explosion with degrading performance is often an ExecutorService or ThreadPoolTaskExecutor
> that's not properly bounded or not properly shutting down submitted tasks.
>
> Common sources:
>
> 1. Unbounded ThreadPoolExecutor with LinkedBlockingQueue
>    Spring's default ThreadPoolTaskExecutor has default queue capacity of Integer.MAX_VALUE.
>    It accepts unlimited tasks, and with a fixed pool, tasks queue but don't spawn threads.
>    But if max pool size > core pool size and queue is bounded, you do get thread growth.
>
> 2. Async methods (@Async) using the default executor which may be unbounded
>
> 3. WebClient or HttpClient connection pool + timeout misconfiguration leaking threads
>
> 4. CompletableFuture.supplyAsync() using ForkJoinPool.commonPool() which has unlimited parallelism
>    under load
>
> Diagnostic:
>   jstack <pid> | grep 'java.lang.Thread.State' | sort | uniq -c | sort -rn
>   # Shows thread state distribution
>
>   jstack <pid> | grep -A 5 'WAITING\|BLOCKED' | head -100
>   # What are threads waiting on?
>
> Modern fix with Java 21:
>   Platform threads are expensive (1MB stack, OS thread).
>   For I/O-bound tasks (HTTP calls, DB queries), virtual threads eliminate this problem entirely.
>   spring.threads.virtual.enabled=true  # Spring Boot 3.2+
>   One virtual thread per request, no thread pooling needed, OS manages scheduling.
>   800 concurrent requests = 800 virtual threads = trivial memory vs 800 platform threads."

## 🔑 Key Takeaway
Unbounded thread growth is almost always a misconfigured executor or pool — diagnose with jstack's thread-state histogram, then consider virtual threads to eliminate the pooling problem entirely.
