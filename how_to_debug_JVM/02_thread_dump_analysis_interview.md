# Thread Dump Analysis — Production Debugging Interview Prep
## 15 Years of Experience | Java Architect Level

---

## 1. BIG PICTURE: Thread State Machine

```
                        +----------+
                        |   NEW    |  (Thread created, not yet started)
                        +----+-----+
                             | start()
                             v
                    +--------+--------+
              +---->|   RUNNABLE      |<----+
              |     | (running or     |     |
              |     |  ready to run)  |     |
              |     +---+------+------+     |
              |         |      |            |
              |  notify()|     | wait()     |
              |  notifyAll()   | join()     |
              |  timeout       | sleep()    |
              |         |      v            |
              |         |  +---+------------+-+
              |         |  | TIMED_WAITING    |  (sleep(n), wait(n), join(n))
              |         |  +------------------+
              |         |
              |         | wait() / join() / park()
              |         v
              |     +---+-----------+
              |     |   WAITING     |  (Object.wait, LockSupport.park,
              +-----+               |   Thread.join with no timeout)
              |     +---------------+
              |
              |     +---------------+
              |     |   BLOCKED     |  (waiting to acquire a monitor lock)
              +-----+   <<<THE      |   This is your problem state
                    |   DANGER ZONE |
                    +---------------+
                             |
                             v
                    +--------+--------+
                    | TERMINATED      |  (run() returned or threw exception)
                    +-----------------+
```

### Deadlock Cycle Diagram

```
Thread-A holds Lock-1, wants Lock-2
Thread-B holds Lock-2, wants Lock-1

   Thread-A ──────holds──────► Lock-1
      │                           │
      │ waiting for               │ (already owned by A)
      │                           │
      ▼                           │
   Lock-2 ◄──────holds────── Thread-B
      │                           │
      │ (already owned by B)      │ waiting for
      │                           │
      └───────────────────────────┘
               CIRCULAR WAIT → DEADLOCK
               CPU = 0%, Threads = BLOCKED forever

jstack output will show:
"Found 1 deadlock."
  Thread-A: waiting to lock <0x00000006c2800f60> (held by Thread-B)
  Thread-B: waiting to lock <0x00000006c2800f20> (held by Thread-A)
```

### Thread Pool Exhaustion Diagram

```
Incoming HTTP Requests
         │
         ▼
  [Tomcat Thread Pool]  maxThreads=200
  ┌──────────────────────────────────┐
  │ Thread-1  [BLOCKED - DB wait]   │
  │ Thread-2  [BLOCKED - DB wait]   │
  │ Thread-3  [BLOCKED - DB wait]   │
  │ ...                             │
  │ Thread-200 [BLOCKED - DB wait]  │
  └──────────────────────────────────┘
         │
         ▼ (pool full, no available thread)
  [Connection Refused / 503 Service Unavailable]

Root cause: DB connection pool (e.g. HikariCP maxPoolSize=10)
All 200 threads fight for 10 DB connections → 190 threads blocked waiting
```

---

## 2. CONVERSATIONAL INTERVIEW SCRIPT

**Interviewer:** "Walk me through how you debug a production system that's hanging. Users are getting timeouts. What's your approach?"

**You (15-YOE Architect):**

"Okay, first thing I want to know is: is the system completely frozen or just slow? That distinction matters because they have very different root causes.

If the system is completely frozen — CPU is near zero, no responses at all — I'm thinking deadlock or thread pool exhaustion. If it's slow with high CPU, I'm thinking a different problem entirely, maybe a runaway loop or GC pressure.

For a hanging system, my first move is to grab a thread dump. I typically take three in a row, 10 seconds apart. A single snapshot doesn't tell me if threads are stuck — I need to see the *same* threads in the *same* state across multiple dumps. That's my confirmation signal.

For capture, I have options. If I have PID access: `jstack -l <pid>`. The `-l` flag gets me lock info, which is critical. If jstack isn't responding — which happens when the JVM itself is in trouble — I fall back to `kill -3 <pid>`. That sends SIGQUIT and the JVM writes the thread dump to stdout/the log file without killing the process. On Spring Boot with Actuator, I can hit `/actuator/threaddump` which is great in Kubernetes where I might not have direct shell access to the pod.

Once I have the dumps, I look for two things immediately: the line that says 'Found X deadlock(s)' and threads in BLOCKED state. If I see BLOCKED threads, I trace who's holding the lock they're waiting on. That thread is my suspect. Then I ask: what is *that* thread waiting on?

In a typical production incident I've dealt with, it's usually one of three patterns: a deadlock from out-of-order lock acquisition, thread pool exhaustion from a slow downstream (usually DB), or a synchronized block that became a bottleneck at scale."

---

**Interviewer:** "What's the difference between BLOCKED and WAITING?"

**You:**

"This is a really important distinction that a lot of people get wrong.

BLOCKED means a thread is trying to enter a `synchronized` block or method, and another thread already holds that monitor. It's actively being prevented from doing something specific — acquiring a particular lock.

WAITING means a thread has voluntarily given up the CPU and said 'wake me up when something happens.' It's in `Object.wait()`, `Thread.join()`, or `LockSupport.park()`. The thread isn't fighting for a lock — it's passively waiting for a signal.

The critical difference for diagnosis: BLOCKED is almost always a problem. Multiple threads BLOCKED on the same lock screams contention. WAITING is often completely normal — idle threads in a thread pool sit in WAITING state, which is fine. 

In jstack output, BLOCKED looks like:
  `- waiting to lock <0xABCD> (a java.lang.Object)`

WAITING looks like:
  `- waiting on <0xABCD> (a java.lang.Object)` with `Object.wait()` in the stack

Subtle difference in wording — 'waiting *to* lock' vs 'waiting *on*' — but completely different meaning."

---

**Interviewer:** "You mentioned taking multiple thread dumps. How many and how far apart?"

**You:**

"I take at least three dumps, 10 seconds apart. The key insight is that thread dumps are point-in-time snapshots. A thread could be in BLOCKED state temporarily due to normal brief lock contention. But if I see the same thread in the same BLOCKED state across three dumps 30 seconds apart, that's a stuck thread — not transient contention.

For a high-traffic system, I might take 5 dumps at 5-second intervals. The pattern I'm looking for: threads that don't move. Their stack trace is identical dump after dump. That's your smoking gun.

I also diff the dumps. If thread count is growing over time, that tells me the application is spawning threads but not cleaning them up, which is a leak. If the same stack frame appears across hundreds of threads in the same state, I've found the bottleneck."

---

## 3. SCENARIO Q&As — PRODUCTION INCIDENTS

### Scenario 1: E-Commerce Checkout Dead Stop

**Q:** "Your e-commerce platform completely stops accepting orders for 8 minutes during Black Friday peak traffic. CPU is near zero. No errors in application logs. On-call engineer pages you. What do you do?"

**A:**

"CPU near zero with no throughput — classic deadlock or thread pool exhaustion signature. Here's my exact sequence:

First, get a PID: `ps aux | grep java` or check the service wrapper.

Take three thread dumps immediately, 10 seconds apart:
```bash
jstack -l 12345 > /tmp/dump1.txt
sleep 10
jstack -l 12345 > /tmp/dump2.txt
sleep 10
jstack -l 12345 > /tmp/dump3.txt
```

Open dump1.txt and search for 'deadlock' first. If found, I see something like:
```
Found 1 deadlock.
=============================
"checkout-thread-5":
  waiting to lock monitor 0x00000006c2800f60 (object 0x000000076ab3d0c0, a com.shop.CartService),
  which is held by "payment-thread-3"
"payment-thread-3":
  waiting to lock monitor 0x00000006c2800f20 (object 0x000000076ab3d050, a com.shop.InventoryService),
  which is held by "checkout-thread-5"
```

If no deadlock, I count BLOCKED threads. If all Tomcat threads are BLOCKED with a HikariCP stack frame, it's pool exhaustion — likely a slow DB query holding connections.

For the immediate fix: if it's deadlock, restart the service (painful but necessary for Black Friday). File the incident. Fix the code post-peak.

For pool exhaustion: check if DB is alive, check slow query log, potentially kill long-running DB queries to unblock the connection pool.

Root cause always gets a post-mortem."

---

### Scenario 2: Payment Service Random Freezes

**Q:** "A payment microservice freezes randomly every few hours for about 2 minutes then recovers. How do you diagnose this systematically?"

**A:**

"The 'recovers after 2 minutes' hint is significant — this suggests a timeout is involved, not a permanent deadlock. My suspects: connection pool acquisition timeout (HikariCP default is 30 seconds, but with 4 retries that could be minutes), a distributed lock with a TTL, or a circuit breaker half-open state.

I'd set up automated thread dump capture triggered on JVM thread count spike or response time degradation. In a Spring Boot app I'd add:

```java
@Scheduled(fixedDelay = 5000)
public void dumpThreadsOnDegradation() {
    if (responseTimeP99 > threshold) {
        ThreadMXBean mxBean = ManagementFactory.getThreadMXBean();
        long[] deadlocked = mxBean.findDeadlockedThreads();
        if (deadlocked != null) {
            log.error("DEADLOCK DETECTED: {} threads", deadlocked.length);
            // dump full info
            ThreadInfo[] infos = mxBean.getThreadInfo(deadlocked, true, true);
            for (ThreadInfo info : infos) log.error(info.toString());
        }
    }
}
```

I'd also enable HikariCP metrics:
```yaml
spring.datasource.hikari.connection-timeout=5000
spring.datasource.hikari.leak-detection-threshold=10000
```

The leak detection threshold logs a warning with the stack trace of the thread that acquired the connection and didn't return it — which is usually the culprit in 'random freeze' scenarios."

---

### Scenario 3: REST API Suddenly 503ing

**Q:** "A REST API starts returning 503s. Thread dump shows all Tomcat threads in WAITING state with `java.lang.Object.wait()` in the stack. Is this a problem?"

**A:**

"No — and this is a trap. WAITING is the *expected* state for idle threads in a Tomcat thread pool. Tomcat's NIO connector threads sit in `java.lang.Object.wait()` waiting for the selector to signal incoming work. If all threads are in WAITING, that means the thread pool is *idle* — there are no incoming requests being processed.

So the 503 is coming from somewhere else. I'd look at:

1. Is Tomcat even receiving the requests? Check the connector acceptCount queue.
2. Is there a load balancer upstream that's timing out before Tomcat responds?
3. Is the application crash-looping and not actually serving?
4. Check `server.tomcat.max-connections` — if you've hit the max connections limit, new connections are rejected even if threads are available.

The distinguishing jstack pattern for a real Tomcat problem is threads in BLOCKED state on a shared resource, not WAITING state. WAITING Tomcat threads = healthy idle pool."

---

### Scenario 4: Batch Job Hanging

**Q:** "A nightly batch job that processes 1M records hangs at 60% completion. Thread dump shows one thread in RUNNABLE and 49 other threads in BLOCKED state. What's your diagnosis?"

**A:**

"One thread RUNNABLE, 49 BLOCKED on it — this is a synchronized bottleneck. One thread holds a lock and is doing something slow (likely I/O — DB write, file write), and all other threads are queued behind it waiting for that monitor.

In the thread dump I'd see something like:

```
"batch-worker-2" BLOCKED on 0x000000076c3a2318 (a com.corp.BatchProcessor)
  at com.corp.BatchProcessor.writeResult(BatchProcessor.java:142)
  - waiting to lock <0x000000076c3a2318>

"batch-worker-1" RUNNABLE
  at com.corp.BatchProcessor.writeResult(BatchProcessor.java:142)
  - locked <0x000000076c3a2318>
  at java.io.BufferedWriter.write(BufferedWriter.java:...)
```

The fix depends on what's in that synchronized block. If it's a shared output stream, I'd switch to a concurrent queue where workers enqueue results and a dedicated writer thread drains it. If it's a shared counter, replace with `AtomicLong`. If it's updating shared state, consider thread-local accumulators with a merge step.

This is Amdahl's Law in practice — that one serialized section caps your parallelism ceiling no matter how many threads you add."

---

### Scenario 5: Microservice Memory Leak + Thread Leak

**Q:** "Kubernetes pod memory keeps growing. Thread dump shows thread count at 3,000 and growing. What's happening and how do you fix it?"

**A:**

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

---

### Scenario 6: Async CompletableFuture Blocking Main Pool

**Q:** "You have a service using CompletableFuture for async operations. Under load, response times degrade and thread dump shows many threads blocked in `CompletableFuture.get()`. What went wrong?"

**A:**

"This is a classic mistake I've seen many teams make. They adopt CompletableFuture for 'async' but then call `.get()` or `.join()` on it in the same thread that's supposed to be async. This is synchronous blocking in async clothing — it defeats the purpose entirely.

The pattern in jstack looks like:
```
"http-nio-8080-exec-7" WAITING
  at java.util.concurrent.CompletableFuture.get(CompletableFuture.java:1999)
  at com.service.OrderService.processOrder(OrderService.java:87)
  at com.service.OrderController.placeOrder(OrderController.java:43)
```

The Tomcat thread is blocking on `.get()`, waiting for a CompletableFuture that's running on the ForkJoinPool common pool. Under load, the common pool also gets saturated.

The fix is to never call `.get()` on a request-handling thread. Instead, return the CompletableFuture to the framework and let the framework handle async completion. With Spring WebFlux or Spring MVC's async support (returning `CompletableFuture<ResponseEntity>` from controllers), the Tomcat thread is freed immediately and re-engaged only when the future completes.

If you must use `.get()`, use a separate dedicated executor for the blocking call, not the HTTP thread pool."

---

### Scenario 7: Database Connection Pool Starvation

**Q:** "Application is healthy at 100 RPS. At 200 RPS, all requests start timing out with 'Connection is not available, request timed out after 30000ms.' Thread dump analysis?"

**A:**

"That's HikariCP's connection acquisition timeout message. The thread dump will show me the exact picture:

```
"http-nio-8080-exec-15" TIMED_WAITING
  at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:213)
  at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:162)
  at com.corp.repository.UserRepository.findById(UserRepository.java:...)
```

All request threads are sitting in HikariCP's queue waiting for a DB connection. The pool is exhausted. This means: requests/second × average query time > pool size.

At 100 RPS with avg 50ms query time: 100 × 0.05 = 5 concurrent connections needed.
At 200 RPS with avg 50ms: 200 × 0.05 = 10 concurrent connections needed.

If maxPoolSize=10, 200 RPS is right at the edge. Any query slowdown pushes you over.

Diagnosis steps:
1. Check HikariCP metrics (if Micrometer is wired): `hikaricp.connections.active`, `hikaricp.connections.pending`
2. Enable leak detection: `spring.datasource.hikari.leak-detection-threshold=2000`
3. Check DB for long-running queries: `SELECT * FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC`

Fix options: increase pool size (carefully — DB has connection limits), reduce query time (indexes, query optimization), add read replicas for read queries, add a caching layer for repeated queries."

---

### Scenario 8: Producer-Consumer Deadlock

**Q:** "A message processing system deadlocks occasionally. Both Producer and Consumer threads use synchronized methods on shared state. How do you find and fix it?"

**A:**

"This is the classic producer-consumer deadlock. Here's the code pattern that causes it:

```java
class MessageQueue {
    private final Object producerLock = new Object();
    private final Object consumerLock = new Object();

    // Producer acquires producerLock then consumerLock
    public synchronized void produce(Message m) {
        synchronized(consumerLock) { // nested lock acquisition
            queue.add(m);
            notifyConsumer();
        }
    }

    // Consumer acquires consumerLock then producerLock (OPPOSITE ORDER!)
    public synchronized void consume() {
        synchronized(producerLock) { // opposite order — deadlock!
            return queue.poll();
        }
    }
}
```

jstack shows:
```
Found 1 deadlock.
"producer-thread-1":
  waiting to lock <0x00000006c1> (consumerLock)
  held by "consumer-thread-1"
"consumer-thread-1":
  waiting to lock <0x00000006c2> (producerLock)
  held by "producer-thread-1"
```

Fix: always acquire locks in the same order. Or better, eliminate nested locks by using `java.util.concurrent.BlockingQueue` which handles thread-safety internally without any explicit synchronization needed by callers:

```java
class MessageQueue {
    private final BlockingQueue<Message> queue =
        new LinkedBlockingQueue<>(1000);

    public void produce(Message m) throws InterruptedException {
        queue.put(m); // blocks if full, no explicit lock needed
    }

    public Message consume() throws InterruptedException {
        return queue.take(); // blocks if empty, no explicit lock needed
    }
}
```"

---

## 4. ADVANCED SCENARIO Q&As

### Advanced Scenario 1: Virtual Threads (Java 21) and Carrier Thread Pinning

**Q:** "You've migrated to Java 21 virtual threads for your web layer. Under load you see degraded performance and thread dumps show 'carrier thread pinned' messages. Explain what's happening and how to fix it."

**A:**

"Virtual threads in Project Loom run on top of platform (carrier) threads from a ForkJoinPool. Normally, when a virtual thread blocks on I/O or `Object.wait()`, it unmounts from the carrier thread, freeing the carrier to run other virtual threads. This is the whole value proposition.

But carrier thread *pinning* happens when a virtual thread cannot unmount from its carrier. Two causes:
1. The virtual thread is inside a `synchronized` block or method
2. The virtual thread calls native code that holds a JNI monitor

When pinned, the virtual thread holds the carrier thread captive — defeating the entire purpose of virtual threads. Under load with many pinned virtual threads, you exhaust the ForkJoinPool's carrier threads and you're back to the old problem.

In a Java 21 thread dump:
```
#119 virtual  [carrier thread: ForkJoinPool.commonPool-worker-3]
    java.lang.VirtualThread$VThreadContinuation.onPinned(VirtualThread.java:...)
    -- Carrier thread pinned --
    at com.corp.LegacyService.processRequest(LegacyService.java:78)
    - locked <0x000000076c> (synchronized method — cause of pinning)
```

The JVM flag `-Djdk.tracePinnedThreads=full` logs whenever a virtual thread gets pinned.

Fix: replace `synchronized` with `ReentrantLock` in hot paths:
```java
// Before — causes pinning
public synchronized void processRequest() { ... }

// After — virtual thread friendly
private final ReentrantLock lock = new ReentrantLock();
public void processRequest() {
    lock.lock();
    try { ... }
    finally { lock.unlock(); }
}
```"

---

### Advanced Scenario 2: Programmatic Deadlock Detection with ThreadMXBean

**Q:** "You need to add automated deadlock detection to your service that fires an alert and triggers a heap dump when detected. How do you implement this?"

**A:**

```java
@Component
public class DeadlockDetector {

    private static final Logger log = LoggerFactory.getLogger(DeadlockDetector.class);
    private final ThreadMXBean mxBean = ManagementFactory.getThreadMXBean();

    @Scheduled(fixedDelay = 10_000) // every 10 seconds
    public void detectDeadlocks() {
        long[] deadlockedThreadIds = mxBean.findDeadlockedThreads();
        // findDeadlockedThreads() covers java.util.concurrent locks too
        // findMonitorDeadlockedThreads() only covers synchronized monitors

        if (deadlockedThreadIds == null) return;

        log.error("DEADLOCK DETECTED! {} threads involved", deadlockedThreadIds.length);

        ThreadInfo[] threadInfos = mxBean.getThreadInfo(
            deadlockedThreadIds,
            true,   // include locked monitors
            true    // include locked synchronizers
        );

        for (ThreadInfo info : threadInfos) {
            log.error("Thread: {} State: {} Blocked on: {}",
                info.getThreadName(),
                info.getThreadState(),
                info.getLockName());
            log.error("Lock owner: {}", info.getLockOwnerName());
        }

        alertingService.fireAlert("DEADLOCK", "Deadlock detected in " +
            deadlockedThreadIds.length + " threads");
        triggerHeapDump(); // optional: capture heap state
    }

    private void triggerHeapDump() {
        try {
            MBeanServer server = ManagementFactory.getPlatformMBeanServer();
            HotSpotDiagnosticMXBean hotspot = ManagementFactory.newPlatformMXBeanProxy(
                server, "com.sun.management:type=HotSpotDiagnostic",
                HotSpotDiagnosticMXBean.class);
            hotspot.dumpHeap("/tmp/deadlock-heapdump.hprof", true);
        } catch (Exception e) {
            log.error("Failed to dump heap", e);
        }
    }
}
```

"Note: `findDeadlockedThreads()` detects deadlocks involving both intrinsic monitors (`synchronized`) AND `java.util.concurrent` locks (`ReentrantLock`). The older `findMonitorDeadlockedThreads()` only detects `synchronized` monitor deadlocks. Always use `findDeadlockedThreads()` in modern code."

---

### Advanced Scenario 3: Thread Dump Comparison Across Time

**Q:** "You have thread dumps captured 30 seconds apart. How do you systematically compare them to identify stuck threads vs. normally cycling threads?"

**A:**

"I do this in three passes:

**Pass 1: Thread state distribution**
Count states in each dump. If BLOCKED count grows dump-over-dump, you have escalating contention. If it's stable but high, you have a steady-state bottleneck.

```bash
grep "java.lang.Thread.State:" dump1.txt | sort | uniq -c
grep "java.lang.Thread.State:" dump2.txt | sort | uniq -c
```

**Pass 2: Identify stuck threads**
A thread is stuck if its stack trace is byte-for-byte identical across dumps. I extract each thread's stack:
```bash
# Get all thread names + first 5 stack frames from dump1
awk '/^"/{name=$0} /at /{print name": "$0}' dump1.txt | head -100
```

If `http-nio-exec-5` shows the exact same `OrderService.java:87` in both dumps, that thread is stuck.

**Pass 3: Lock ownership tracking**
Find who owns contended locks. In dump1, if Lock-X is held by Thread-A and 50 threads wait for it, and in dump2 it's still held by Thread-A — Thread-A is your bottleneck. Trace what Thread-A is doing.

For large thread dumps (hundreds of threads), I use fastthread.io — paste your dump, it generates a visual breakdown of states, groups identical stack traces, and highlights stuck threads immediately. TDA (Thread Dump Analyzer) is a local GUI option if you can't share dumps externally."

---

### Advanced Scenario 4: Lock-Free Alternative Analysis

**Q:** "Senior architect question: When should you use `synchronized`, `ReentrantLock`, `StampedLock`, or `Atomic*` classes? Give production-relevant guidance."

**A:**

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

---

## 5. SENIOR TRAP QUESTIONS

### Trap 1: "A deadlock means the CPU spikes to 100%"

**Interviewer plants:** "We had a deadlock last week — CPU was pegged at 100%, definitely a deadlock."

**Correct response:**

"Actually, a deadlock produces the *opposite* CPU pattern — CPU drops to near *zero*. That's one of the diagnostic signatures I use to distinguish deadlock from other issues.

In a deadlock, all involved threads are in BLOCKED state — they're not executing any code, not consuming CPU. They're just sitting there waiting for locks that will never be released. The JVM scheduler doesn't even give them CPU time because they have nothing runnable to do.

High CPU — 100% — suggests a different problem: a runaway loop (infinite loop in RUNNABLE state), a garbage collection storm (GC threads running constantly), or CPU-intensive work without throttling.

If you saw 100% CPU, you likely had a livelock (threads keep retrying and failing), a tight polling loop, or significant GC pressure — all of which look very different in a thread dump."

---

### Trap 2: "Add more threads to handle the load"

**Interviewer plants:** "Our thread pool is exhausted. We should just increase maxThreads to 2000 to handle more requests."

**Correct response:**

"That's a band-aid that usually makes things worse. Thread count is not the primary throughput lever — the bottleneck is downstream resource capacity, almost always.

Each thread has a stack (default 512KB-1MB). 2000 threads = up to 2GB just for stacks, before any heap usage. Context switching overhead at 2000 threads is significant — the OS scheduler spends meaningful CPU cycles just deciding which thread to run next.

More critically: if those 2000 threads are all blocked waiting for DB connections from a pool of size 10, you now have 1990 threads sitting uselessly. The real fix is to address the bottleneck: increase DB pool (if DB can handle it), add a read replica, cache hot data, or adopt async non-blocking I/O where threads don't sit blocked at all.

The right mental model: for I/O-bound thread pools, optimal thread count ≈ CPU cores / (1 - blocking factor). If 80% of time is spent waiting on I/O (blocking factor = 0.8), and you have 8 cores: 8 / (1 - 0.8) = 40 threads. Not 2000.

For true high concurrency, the modern answer is virtual threads (Java 21) or reactive/non-blocking I/O — not bigger thread pools."

---

### Trap 3: "Thread pool size should equal CPU core count"

**Interviewer plants:** "We size our thread pool to match CPU cores — 8 cores, 8 threads. That's optimal, right?"

**Correct response:**

"That's optimal for CPU-bound work — number crunching, image processing, pure computation. But it's incorrect for the I/O-bound work that makes up most web service workloads.

The formula is Little's Law applied to thread sizing:
```
Optimal threads = CPU cores × (1 + wait time / compute time)
```

If a request spends 50ms waiting on DB and 5ms computing: ratio is 10.
8 cores × (1 + 10) = 88 threads optimal.

With only 8 threads on a service spending 90% of time waiting on I/O, 7 of your 8 threads are constantly blocked. You're using 1 CPU core's worth of CPU capacity out of 8 available. Massive waste.

The 'cores = threads' rule comes from CPU-bound thread pools like ForkJoinPool's compute pool — and even there, Java 21's virtual threads largely obsolete that thinking for I/O-bound services."

---

### Trap 4: "All those WAITING threads in the dump are a bug"

**Interviewer plants:** "The thread dump shows 180 threads in WAITING state. That's clearly wrong — we should investigate."

**Correct response:**

"Not necessarily a bug at all — WAITING is the *healthy* resting state for idle threads in a pool.

Tomcat NIO threads sit in `Object.wait()` when they have no active request to handle. HikariCP's connection pool maintenance thread parks in WAITING. `@Async` executor threads wait on a task queue. Kafka consumer threads wait on poll. All completely normal.

The state to be alarmed about is BLOCKED — that means a thread is actively trying to do work but can't because another thread is holding a lock it needs. That's contention.

Also concerning is a large number of threads in TIMED_WAITING for a surprisingly long duration — `Thread.sleep(30000)` in production code, for example — but WAITING itself is healthy.

When I open a thread dump, I look for BLOCKED first, then look for unusual stack frames in WAITING threads — like application code that shouldn't be waiting sitting in `Object.wait()` — not at the raw WAITING count."

---

### Trap 5: "Just kill the deadlocked thread to resolve the deadlock"

**Interviewer plants:** "We wrote a script that detects deadlocked threads via ThreadMXBean and interrupts them. Problem solved, right?"

**Correct response:**

"That's a workaround, not a fix — and it can cause data corruption if the deadlocked threads were in the middle of a transaction or holding resources that need cleanup.

When you forcibly interrupt a thread holding a lock on an object that's in an inconsistent state, you can leave that object permanently broken. The thread you interrupted was probably mid-write. Now you have a monitor held by a dead thread (Java marks it as broken) and other threads that acquire it will get `IllegalMonitorStateException`.

The correct fix is in the code: design lock acquisition to always happen in consistent global order. Or use `ReentrantLock.tryLock(timeout, unit)` so threads give up after a timeout and retry with backoff rather than waiting forever:

```java
ReentrantLock lock1 = new ReentrantLock();
ReentrantLock lock2 = new ReentrantLock();

public void doWork() throws InterruptedException {
    while (true) {
        if (lock1.tryLock(50, TimeUnit.MILLISECONDS)) {
            try {
                if (lock2.tryLock(50, TimeUnit.MILLISECONDS)) {
                    try {
                        // do work with both locks
                        return;
                    } finally { lock2.unlock(); }
                }
            } finally { lock1.unlock(); }
        }
        Thread.sleep(10 + ThreadLocalRandom.current().nextInt(20)); // jitter
    }
}
```

The interrupt-deadlocked-threads script is a circuit breaker at best — a temporary safety valve. The underlying code must be fixed."

---

### Trap 6: "Thread dump shows my async code is non-blocking"

**Interviewer plants:** "We use CompletableFuture everywhere so our threads are non-blocking. The thread dump should show minimal activity."

**Correct response:**

"CompletableFuture alone doesn't make your code non-blocking — it depends on *what* runs inside the future and whether you call `.get()` or `.join()` on the calling thread.

If your CompletableFuture wraps a JDBC call and runs on the ForkJoinPool, that pool thread is blocked on the DB for the duration of the query. You've just moved the blocking from one thread pool to another.

True non-blocking requires the entire I/O chain to be non-blocking: an async DB driver (R2DBC, not JDBC), async HTTP client (WebClient, not RestTemplate), reactive streams (Project Reactor/RxJava).

A thread dump will tell you the truth. If you have `CompletableFuture` in your stack but see `SocketInputStream.read()` or `ResultSet.next()` below it in the same frame — that thread is *blocking*. The async wrapper didn't help.

The only truly non-blocking JVM concurrency is: reactive streams, Java 21 virtual threads with non-blocking I/O (Netty-backed), or async I/O with callbacks (NIO). CompletableFuture is a *coordination* mechanism, not an I/O model."

---

## 6. JAVA CODE EXAMPLES + jstack OUTPUT

### Reading a Real jstack Block

```
"http-nio-8080-exec-3" #47 daemon prio=5 os_prio=0 cpu=1234.56ms
   elapsed=890.23s tid=0x00007f3c2c001000 nid=0x1a2b
   waiting to lock <0x000000076c3a2318> (a java.lang.Object)
   [0x00007f3b8c0fe000]
   java.lang.Thread.State: BLOCKED (on object monitor)
   at com.corp.OrderService.updateOrder(OrderService.java:142)
   - waiting to lock <0x000000076c3a2318> (owned by thread-15)
   at com.corp.OrderController.update(OrderController.java:67)
```

**Reading this line by line:**
- `"http-nio-8080-exec-3"` — thread name (Tomcat NIO executor thread 3)
- `#47` — internal thread ID
- `daemon` — daemon thread (dies when all non-daemon threads finish)
- `prio=5` — JVM thread priority
- `tid=0x...` — JVM-level thread pointer
- `nid=0x1a2b` — native OS thread ID (map to `ps -T -p <pid>` for CPU usage)
- `BLOCKED (on object monitor)` — the state
- `waiting to lock <0x000000076c3a2318>` — the specific lock it wants
- `owned by thread-15` — the thread currently holding that lock

---

### Minimal Deadlock Code

```java
public class DeadlockDemo {
    static final Object LOCK_A = new Object();
    static final Object LOCK_B = new Object();

    public static void main(String[] args) {
        Thread t1 = new Thread(() -> {
            synchronized (LOCK_A) {
                sleep(100); // let t2 grab LOCK_B
                synchronized (LOCK_B) { System.out.println("T1 done"); }
            }
        }, "DeadlockThread-1");

        Thread t2 = new Thread(() -> {
            synchronized (LOCK_B) {
                sleep(100); // t1 already holds LOCK_A
                synchronized (LOCK_A) { System.out.println("T2 done"); }
            }
        }, "DeadlockThread-2");

        t1.start(); t2.start();
        // CPU goes to 0%, both threads BLOCKED forever
    }
}
```

---

### HikariCP Pool Exhaustion in jstack

```
"http-nio-8080-exec-10" TIMED_WAITING
  at java.base/java.lang.Object.wait(Native Method)
  at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:208)
  at com.corp.repo.UserRepository.findUser(UserRepository.java:55)
  at com.corp.service.UserService.getUser(UserService.java:33)

"http-nio-8080-exec-11" TIMED_WAITING (identical stack — also waiting for connection)
"http-nio-8080-exec-12" TIMED_WAITING (identical stack — pool starved)
```

When you see 50+ threads with identical HikariCP stacks, the DB connection pool is the bottleneck.

---

### Capturing Thread Dumps — All Methods

```bash
# Method 1: jstack — requires tools.jar / JDK, cleanest output
jstack -l <pid> > /tmp/dump.txt        # -l includes ownable synchronizers

# Method 2: kill -3 — SIGQUIT, output goes to stdout/log
kill -3 <pid>                          # safe, no process kill
# check catalina.out or app log for the dump

# Method 3: jcmd — modern, more options
jcmd <pid> Thread.print > /tmp/dump.txt
jcmd <pid> Thread.print -l             # with locks

# Method 4: Spring Boot Actuator (when no shell access, e.g. Kubernetes)
curl http://localhost:8080/actuator/threaddump
curl -H "Accept: text/plain" http://localhost:8080/actuator/threaddump

# Method 5: jvisualvm / Java Mission Control (GUI, with live thread monitoring)
# Use for development/staging, not usually available in prod

# WHEN TO USE WHICH:
# Live container (k8s, no exec): actuator/threaddump
# Shell access available: jstack -l for clean output
# JVM unresponsive to jstack: kill -3 (always works, goes to log)
# Scripted/automated: jcmd in scripts (more stable than jstack in automation)
```

---

### Thread Pool Starvation — Code Pattern

```java
// BROKEN: all threads block on .get() — no parallelism achieved
ExecutorService pool = Executors.newFixedThreadPool(10);
for (Order order : orders) {
    Future<Result> future = pool.submit(() -> processOrder(order));
    Result r = future.get(); // BLOCKS the calling thread! Defeats the pool.
    results.add(r);
}

// FIXED: submit all, collect all
List<Future<Result>> futures = orders.stream()
    .map(o -> pool.submit(() -> processOrder(o)))
    .collect(toList()); // all tasks running in parallel
List<Result> results = futures.stream()
    .map(f -> f.get()) // now collect — tasks already running
    .collect(toList());
```

---

### Virtual Thread Example (Java 21)

```java
// Old style: platform thread per request (expensive, JDBC blocks carrier)
ExecutorService traditional = Executors.newFixedThreadPool(200);

// Java 21: virtual thread per request — scales to millions
ExecutorService virtual = Executors.newVirtualThreadPerTaskExecutor();

// Spring Boot 3.2+:
// spring.threads.virtual.enabled=true
// — automatically uses virtual threads for Tomcat, @Async, etc.

// Check for pinning at runtime:
System.setProperty("jdk.tracePinnedThreads", "full");
// Logs any virtual thread that gets pinned to a carrier
```

---

## 7. INTERVIEW CHEAT SHEET

### Thread States — One-Liner Summary

| State | Meaning | Normal? | Action |
|-------|---------|---------|--------|
| NEW | Created, not started | Yes | None |
| RUNNABLE | Running or ready to run | Yes | None |
| BLOCKED | Waiting to acquire monitor lock | Sometimes | Investigate if many |
| WAITING | Waiting for notify/join/unpark | Yes (idle threads) | Check stack frame context |
| TIMED_WAITING | Same but with timeout | Yes | Check if unusually long |
| TERMINATED | Finished | Yes | None |

### jstack Capture Quick Reference

| Method | Command | When to use |
|--------|---------|-------------|
| jstack | `jstack -l <pid>` | Default choice, shell access |
| SIGQUIT | `kill -3 <pid>` | JVM unresponsive to jstack |
| jcmd | `jcmd <pid> Thread.print -l` | Scripts and automation |
| Actuator | `GET /actuator/threaddump` | Kubernetes, no shell access |

### Deadlock vs. Thread Pool Exhaustion vs. Live Contention

| Pattern | CPU | BLOCKED count | Lock pattern | Fix |
|---------|-----|---------------|--------------|-----|
| Deadlock | ~0% | 2+ in cycle | Circular wait | Fix lock order, use tryLock |
| Pool exhaustion | low | Many on same lock | All waiting for same downstream | Fix downstream, right-size pool |
| Hot contention | moderate | Many same lock, cycling | Single bottleneck lock | Split lock, use Concurrent* classes |
| Livelock | ~100% | Few | No lock, spinning | Add backoff + jitter |

### Lock Choice Cheat Sheet

```
Single variable? → Atomic* (AtomicInteger, AtomicReference)
Simple mutual exclusion? → synchronized
Need tryLock/timeout/fair? → ReentrantLock
Read-heavy, rare writes? → StampedLock (optimistic reads)
Multiple readers OR one writer? → ReadWriteLock
Producer-consumer queue? → BlockingQueue (no explicit sync)
Virtual threads (Java 21)? → ReentrantLock (no synchronized — avoid pinning)
```

### Top Thread Pool Anti-Patterns

1. **`Executors.newCachedThreadPool()`** without bounds — thread leak under load
2. **Calling `.get()` on `Future` in the submitting thread** — synchronous blocking disguised as async
3. **Nested executor submissions** — thread pool deadlock (inner task waits for outer thread that's blocked waiting for inner task)
4. **Sharing `ForkJoinPool.commonPool()`** for blocking I/O — starves other framework internals
5. **Per-request `new Thread()`** without pooling — thread leak, stack memory explosion

### HikariCP Health Indicators

```
hikaricp.connections.active     → currently in use
hikaricp.connections.idle       → available in pool
hikaricp.connections.pending    → threads waiting for a connection (> 0 is warning)
hikaricp.connections.timeout.total → cumulative acquisition timeouts (> 0 is incident)
```

Enable with: `management.metrics.enable.hikaricp=true` in Spring Boot.

### Five Questions to Ask in First 60 Seconds of an Incident

1. **CPU usage?** Near zero = deadlock/pool exhaustion. Near 100% = runaway code/GC storm.
2. **Memory trending up?** Yes = potential leak (thread leak, memory leak)
3. **When did it start?** Correlate with deployments, traffic spike, cron jobs
4. **Any errors in logs?** `Connection timeout`, `OutOfMemoryError`, exceptions pointing to a class
5. **How many threads BLOCKED?** One = isolated contention. Many on same lock = bottleneck. Circular = deadlock.

### Thread Dump Tools

| Tool | Type | Best For |
|------|------|---------|
| fastthread.io | Web (upload) | Quick visual analysis, groups identical stacks |
| TDA (Thread Dump Analyzer) | Local GUI | Offline analysis, large dumps |
| jvisualvm | GUI IDE | Live thread monitoring in dev/staging |
| `grep` + `awk` | CLI | Scripted analysis, CI/CD integration |
| IntelliJ Analyzer | IDE | Thread dump analysis integrated in IDE |

### Key JVM Flags for Thread Debugging

```bash
-Djdk.tracePinnedThreads=full          # Java 21: log virtual thread pinning
-XX:+PrintConcurrentLocks              # older JDKs: print lock info in dumps
-Djava.util.concurrent.ForkJoinPool.common.parallelism=N  # tune common pool
-XX:ThreadStackSize=512k               # reduce stack per thread (default 512k-1m)
```

### The Deadlock Prevention Rules (Lock Ordering)

```
Rule 1: Always acquire multiple locks in the same global order
        Sort by System.identityHashCode() if no natural order

Rule 2: Use tryLock(timeout) — prefer liveness over safety-by-locking

Rule 3: Minimize lock scope — hold locks for the shortest possible time

Rule 4: Never call external/unknown code while holding a lock

Rule 5: Use concurrent data structures instead of synchronized wrappers
        (ConcurrentHashMap > Collections.synchronizedMap())
```

---

*Prepared for 15-YOE Java Architect interviews — production debugging focus*
*Thread dump analysis, deadlock diagnosis, JVM concurrency internals*
