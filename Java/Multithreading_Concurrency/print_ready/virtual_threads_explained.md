# Virtual Threads — Why We Need Them & How They Solve Production Problems

---

## The Problem: Platform Threads are OS Threads

Every time your app creates a `Thread`, the JVM asks the OS to create an OS thread. That's expensive:

```
OS Thread cost:
  - ~1 MB stack memory reserved per thread
  - Context switching = kernel mode switch (expensive)
  - OS scheduler limit ≈ ~10,000 threads before thrashing
```

**The classic production scenario:**

```
                    PLATFORM THREADS (old way)
                    ──────────────────────────

  HTTP Request ──►  Thread-1   ──► calls DB  ──► WAITING 200ms
  HTTP Request ──►  Thread-2   ──► calls API ──► WAITING 500ms
  HTTP Request ──►  Thread-3   ──► calls DB  ──► WAITING 200ms
  ...
  HTTP Request ──►  Thread-200 ──► calls DB  ──► WAITING 200ms
  HTTP Request ──►  [QUEUED]   ──► waiting for a free thread!
  HTTP Request ──►  [QUEUED]
  HTTP Request ──►  [QUEUED]   ← 9800 requests stuck!

  All 200 threads are ALIVE but doing nothing — just waiting on I/O.
  OS thread is blocked. 200MB RAM wasted on idle stacks.
```

---

## The Fix: Virtual Threads (JVM-managed, not OS-managed)

```
                    VIRTUAL THREADS (new way)
                    ─────────────────────────

  JVM has ~8 "carrier threads" (= CPU cores)

  Virtual Thread-1    ──► calls DB  ──► [PARKED by JVM]
                                             │
                            carrier freed ───┘──► picks up VT-5001
  Virtual Thread-5001 ──► runs      ──► calls API ──► [PARKED]
                                             │
                            carrier freed ───┘──► picks up VT-2

  1,000,000 virtual threads? Fine.
  Each one parks when it blocks. Carrier thread never idles.
  Memory per VT: ~few KB (vs 1 MB for OS thread)
```

---

## How It Works Internally

```
  Virtual Thread lifecycle on blocking I/O:

  VT calls Thread.sleep() or socket.read()
       │
       ▼
  JVM intercepts (not OS!)
       │
       ▼
  VT state saved to HEAP (cheap — just an object)
       │
       ▼
  Carrier thread UNMOUNTED from VT
       │
       ▼
  Carrier thread picks up next RUNNABLE virtual thread
       │
       ▼
  When I/O completes → VT marked RUNNABLE → mounted back onto a carrier
```

---

## Production Impact

```
Scenario: REST service, each request does 3 DB calls × 50ms each

  Platform threads (pool = 200):
    Throughput  = 200 threads / 150ms = ~1,333 req/sec
    At 2,000 req/sec → queue backs up → latency spike → timeouts

  Virtual threads:
    Throughput limited by DB connection pool, NOT thread count
    10,000 req/sec? Carrier threads just keep parking/unparking VTs
    Memory: same 8 carrier threads + tiny VT heap objects
```

---

## The One Gotcha — PINNING

```
  PINNING — virtual thread gets STUCK on carrier thread when:

  synchronized(lock) {
      Thread.sleep(1000);   ← VT CANNOT unmount here!
  }                           Carrier thread blocked for 1 sec too.

  ❌ PINNING (avoid with virtual threads)        ✅ NO PINNING
  ──────────────────────────────────────         ─────────────────────────
  synchronized(lock) {                           ReentrantLock lock = new ReentrantLock();
      Thread.sleep(1000);                        lock.lock();
      Files.readAllBytes(path);                  try {
  }                                                  Thread.sleep(1000);
                                                     Files.readAllBytes(path);
                                                 } finally { lock.unlock(); }

  Diagnose pinning: -Djdk.tracePinnedThreads=full
```

---

## How to Use It

```java
// Option 1: simple
Thread.ofVirtual().start(() -> handleRequest());

// Option 2: executor (recommended)
try (var ex = Executors.newVirtualThreadPerTaskExecutor()) {
    ex.submit(() -> handleRequest());  // 1 virtual thread per task
}

// Option 3: Spring Boot 3.2+ (zero code change to business logic)
@Bean
public TomcatProtocolHandlerCustomizer<?> useVirtualThreads() {
    return h -> h.setExecutor(Executors.newVirtualThreadPerTaskExecutor());
}
// Every HTTP request now runs on a virtual thread automatically
```

---

## Platform vs Virtual — Quick Comparison

```
  Aspect            Platform Thread        Virtual Thread
  ──────────────    ───────────────────    ────────────────────────
  Managed by        OS                     JVM
  Memory            ~1 MB per thread       ~few KB per thread
  Max practical     ~10,000                Millions
  Blocking I/O      Blocks OS thread       JVM parks, carrier freed
  Creation cost     High (syscall)         Near-zero (heap object)
  Best for          CPU-bound work         I/O-bound work
  synchronized      Fine                   Causes PINNING (avoid)
  Code style        Imperative             Imperative (no change!)
```

---

## Interview One-Liner

> "Virtual threads are JVM-managed, not OS-managed. When they block on I/O, the JVM
> unmounts them from the carrier thread — freeing that carrier to run other virtual threads.
> You get reactive-level scalability while writing plain blocking Java code. The one gotcha
> is pinning: blocking I/O inside a synchronized block prevents unmounting. Fix it by
> replacing synchronized with ReentrantLock."
