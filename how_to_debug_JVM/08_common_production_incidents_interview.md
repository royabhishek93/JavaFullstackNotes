# Common JVM Production Incidents — 15 YOE Interview Prep

**2026 Edition | OOM · High CPU · Deadlock · Memory Leak · Thread Exhaustion · Slow GC | Scenario Q&As + Senior Traps**

---

## Big Picture: Incident Triage Decision Tree

```
PRODUCTION ALERT ARRIVES
│
├─ CPU > 80%?
│   ├─ jstat -gcutil → FGC column rising fast?
│   │   └─ YES → GC thrashing → heap tuning / leak fix
│   └─ NO → async-profiler cpu 30s → flame graph → hot method
│
├─ Memory growing / OOM?
│   ├─ OOM type?
│   │   ├─ "Java heap space" → heap leak or undersized heap
│   │   ├─ "GC overhead limit exceeded" → heap leak (allocation > collection)
│   │   ├─ "Metaspace" → classloader leak
│   │   └─ "Direct buffer memory" → Netty/NIO leak
│   └─ jcmd GC.class_histogram → top retained objects
│
├─ App unresponsive / all threads stuck?
│   ├─ jstack -l → "Found X deadlock(s)"?
│   │   └─ YES → deadlock → code fix required
│   └─ NO → all threads BLOCKED waiting on same lock / connection pool?
│       └─ HikariCP pool exhaustion → increase pool or fix connection leak
│
├─ Slow responses (latency spikes)?
│   ├─ GC log → Full GC pause times?
│   ├─ Arthas trace → which method is slow?
│   └─ DB slow query? → connection wait in Arthas
│
└─ App crashed (no JVM / hs_err_pid file)?
    └─ Read hs_err_pid<PID>.log → native crash → JNI / OS / JDK bug
```

---

## Conversational Interview Script

**"Tell me about the worst production JVM incident you've debugged."**

> "Black Friday, 2 AM. Order service: p99 latency spiked from 80ms to 45 seconds. Pods were staying up but requests were piling up. First check was GC: `jstat -gcutil <pid> 1000` showed Old Gen at 99%, FGC column incrementing every 10 seconds, FGCT climbing. Full GC every 10 seconds means roughly 30% of time in STW pauses — that explained the latency spike.
>
> Next question: is this a leak or is the heap just undersized for this load? I took two thread dumps 2 minutes apart and compared Old Gen growth rate. It was growing 50MB/minute even when I throttled traffic down to 20% of normal — that's a leak pattern, not load.
>
> I ran `jcmd GC.class_histogram` (fast, no dump pause) — top object was `byte[]` held by `String` objects inside a `HashMap`. Attached Arthas: `trace com.myapp.cache.RequestCache put` — found an unbounded request cache with no eviction. 6 weeks of traffic had filled it, but it only became catastrophic at Black Friday load when allocation rate exceeded collection rate.
>
> Fix: added `maximumSize(10_000).expireAfterWrite(1, HOURS)` to the cache. Deploy took 8 minutes. Incident duration: 47 minutes."

---

## The 10 Incidents

---

### Incident 1: OutOfMemoryError: Java heap space

**Symptoms:**
- Pod OOM-killed by Kubernetes (or JVM exits with OOM)
- Logs show `java.lang.OutOfMemoryError: Java heap space`
- Heap dump shows large retained objects

**Diagnosis:**
```bash
# 1. OOM already happened — check for heap dump (if flag was set)
ls -lh /var/dumps/*.hprof

# 2. If still alive before crash, get histogram (fast)
jcmd <pid> GC.class_histogram | head -30

# 3. Full heap dump (take pod out of LB first)
jcmd <pid> GC.heap_dump /tmp/heap.hprof

# 4. Analyze with MAT — find dominator tree / leak suspects
```

**Root causes (most common):**
1. Unbounded cache (static Map / Caffeine without eviction)
2. Session object accumulation (HttpSession not expiring)
3. List/collection growing forever per request (not cleared)

**Fix:**
```java
// Broken: unbounded static map
private static final Map<String, Data> cache = new HashMap<>();

// Fixed: bounded with eviction
private static final Cache<String, Data> cache = Caffeine.newBuilder()
    .maximumSize(10_000)
    .expireAfterWrite(1, TimeUnit.HOURS)
    .build();
```

**Prevention:** `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/var/dumps/` at all times.

---

### Incident 2: High CPU (100%) — Not a Code Loop

**Symptoms:**
- `top` shows java process at 100-800% CPU (multi-core)
- Response times degraded
- `jstat` shows FGCT climbing rapidly

**Diagnosis:**
```bash
# Step 1: Is it GC threads eating CPU?
jstat -gcutil <pid> 1000 10
# If FGCT growing fast (>1 Full GC every 30s) → GC is the CPU consumer

# Step 2: If not GC, find the hot thread
top -H -p <pid>  # show individual threads, find the hot one (TID)
printf "%x\n" <TID>  # convert decimal TID to hex for jstack matching
jstack <pid> | grep -A 20 "nid=0x<hex_tid>"

# Step 3: Or use async-profiler (better)
profiler.sh -e cpu -d 30 -f /tmp/cpu.html <pid>
```

**Root cause examples:**
- `Pattern.compile()` called on every request (should be a static final)
- `String.format()` in a tight loop with large strings
- HashMap with broken `hashCode()` (all objects in same bucket → O(n) lookup)
- GC thrashing because of memory leak (GC is the CPU, not the application)

**Fix:**
```java
// Broken: compile regex per request
boolean isValid(String input) {
    return input.matches("^[a-zA-Z0-9]{8,20}$"); // compiles every call
}

// Fixed: static compiled Pattern
private static final Pattern PATTERN = Pattern.compile("^[a-zA-Z0-9]{8,20}$");
boolean isValid(String input) {
    return PATTERN.matcher(input).matches();
}
```

---

### Incident 3: Application Completely Frozen — Deadlock

**Symptoms:**
- All requests timeout, no errors, CPU near 0%
- Health check still passes (health endpoint on separate thread)
- Requests pile up in queue

**Diagnosis:**
```bash
# jstack -l includes lock info — will show "Found X deadlock(s)"
jstack -l <pid> > /tmp/threads.txt
grep -A 30 "Found.*deadlock" /tmp/threads.txt

# Or: jcmd (safer, no ptrace)
jcmd <pid> Thread.print -l > /tmp/threads.txt
```

**Deadlock signature in jstack:**
```
Found one Java-level deadlock:
=============================
"Thread-1":
  waiting to lock monitor 0x00007f (object 0x..., a java.lang.Object),
  which is held by "Thread-2"
"Thread-2":
  waiting to lock monitor 0x00007e (object 0x..., a java.lang.Object),
  which is held by "Thread-1"
```

**Classic cause:**
```java
// Lock acquisition in opposite order
// Thread 1: acquires lock A, then tries lock B
// Thread 2: acquires lock B, then tries lock A
synchronized (lockA) {
    synchronized (lockB) { /* Thread 1 */ }
}
synchronized (lockB) {
    synchronized (lockA) { /* Thread 2 */ }
}
```

**Fix:** Always acquire locks in the same consistent order, or use `tryLock()` with timeout:
```java
if (lockA.tryLock(100, TimeUnit.MILLISECONDS)) {
    try {
        if (lockB.tryLock(100, TimeUnit.MILLISECONDS)) {
            try { /* do work */ }
            finally { lockB.unlock(); }
        }
    } finally { lockA.unlock(); }
}
```

---

### Incident 4: Slow Responses Under Load — Connection Pool Exhaustion

**Symptoms:**
- p99 latency spikes under load (200ms → 5000ms)
- Error logs show `HikariPool-1 - Connection is not available, request timed out after 30000ms`
- p50 latency is fine (some requests fast, some very slow)

**Diagnosis:**
```bash
# Check how many threads are waiting for a DB connection
jstack <pid> | grep -c "HikariPool\|getConnection\|JDBC"

# Arthas — see connection pool state
ognl "@com.zaxxer.hikari.HikariDataSource@pool.getActiveConnections()"
ognl "@com.zaxxer.hikari.HikariDataSource@pool.getIdleConnections()"
ognl "@com.zaxxer.hikari.HikariDataSource@pool.getPendingAcquires()"

# Spring metrics
curl localhost:8080/actuator/metrics/hikaricp.connections.pending
```

**Root causes:**
1. Pool too small for load (`maximumPoolSize` default = 10, but you have 200 request threads)
2. Long-running transactions holding connections
3. Connection not returned (forgot to close / not in try-with-resources)
4. DB queries slow under load, connections held longer → pool starved

**Little's Law for sizing:**
```
Pool size = (Concurrent requests) × (DB response time)
         = 100 requests × 0.05s = 5 connections minimum
With safety margin: 5 × 2 = 10 connections

BUT: if DB response time increases to 0.5s under load:
     100 × 0.5 = 50 connections needed
```

**Fix:**
```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 20        # tune based on Little's Law
      connection-timeout: 3000     # fail fast — don't wait 30s
      idle-timeout: 600000
      max-lifetime: 1800000
      leak-detection-threshold: 5000  # warn if connection held >5s
```

---

### Incident 5: Memory Leak — Gradual OOM Over Days

**Symptoms:**
- Memory grows 50-100MB/day
- Weekly restart schedule (masking the leak)
- Eventually OOM-kills pod after ~7 days

**Diagnosis — compare heap over time:**
```bash
# Capture histogram baseline
jcmd <pid> GC.class_histogram > /tmp/hist1.txt

# Wait 30 minutes
jcmd <pid> GC.class_histogram > /tmp/hist2.txt

# Find growing classes
diff <(sort /tmp/hist1.txt) <(sort /tmp/hist2.txt) | grep "^>" | sort -k3 -rn | head -20
```

**Look for:**
- `char[]` / `byte[]` / `String` growing → string accumulation
- `HashMap$Entry` or `LinkedHashMap$Entry` → map growing
- Event listener objects → listener not unregistered
- CGLIB proxies → classloader leak in dynamic proxy

**Common pattern — ThreadLocal not cleaned:**
```java
// Broken: ThreadLocal in thread pool = memory accumulates
private static final ThreadLocal<UserContext> CTX = new ThreadLocal<>();

// In request handler:
CTX.set(new UserContext(userId));  // set on thread
// ... process request ...
// FORGOT: CTX.remove() — next request reuses thread, old context remains

// Fixed: always clean up
try {
    CTX.set(context);
    processRequest();
} finally {
    CTX.remove();  // CRITICAL for thread pool threads
}
```

---

### Incident 6: StackOverflowError

**Symptoms:**
- `java.lang.StackOverflowError` in logs
- Often in recursive code paths (XML parsing, tree traversal, JSON deserialization)
- Stack trace is truncated (only shows top/bottom of deep recursion)

**Diagnosis:**
```bash
# Look at the stack trace — is the same method repeating?
grep "at com.myapp" logs/app.log | uniq -c | sort -rn | head -10
# If one method appears 1000+ times → infinite recursion
```

**Root causes:**
1. Recursive method missing base case
2. Mutual recursion: A calls B calls A
3. Deserialization of circular object graph (Jackson/Gson)
4. Very deep call stack with large local arrays (deep framework wrapping)

**Fix for recursion:**
```java
// Broken: infinite mutual recursion
boolean isEven(int n) { return n == 0 ? true : isOdd(n - 1); }
boolean isOdd(int n)  { return n == 0 ? false : isEven(n - 1); }
// For n=100000 → StackOverflow

// Fixed: convert to iteration or use tail recursion manually
boolean isEven(int n) {
    while (n > 0) n -= 2;
    return n == 0;
}
```

**Stack size tuning (rarely the right fix):**
```bash
-Xss1m   # default 512k-1m; increase only if deep legitimate recursion
# Better fix: convert recursion to iteration with explicit stack
```

---

### Incident 7: Thread Pool Rejection — RejectedExecutionException

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

---

### Incident 8: OOM-Killed by Kubernetes — JVM Never Threw OOM

**Symptoms:**
- Pod restarts with `OOMKilled` reason in `kubectl describe pod`
- No `java.lang.OutOfMemoryError` in application logs
- JVM heap usage looks fine

**Why:** Linux kernel OOM-killer acts on total RSS (Resident Set Size), not just JVM heap. JVM RSS = heap + metaspace + code cache + thread stacks + direct buffers + JVM overhead. If RSS exceeds the container memory limit, the kernel kills the process with SIGKILL — no JVM OOM, no heap dump, just a dead pod.

**Diagnosis:**
```bash
kubectl describe pod <pod-name> | grep -A 5 "Last State"
# Shows: Reason: OOMKilled

# In container, check total memory usage
cat /proc/<pid>/status | grep VmRSS
# Or
jcmd <pid> VM.native_memory summary  # if NMT enabled
```

**Fix:**
```bash
# Leave headroom above -Xmx
# JVM native overhead = ~500MB-1GB on top of heap

# If container limit = 4GB:
-Xmx2g                          # heap
-XX:MaxMetaspaceSize=256m       # metaspace cap
-XX:ReservedCodeCacheSize=256m  # code cache
-Xss512k                        # thread stacks (if many threads)
# Estimated RSS: 2G + 0.25G + 0.25G + threads + ~300MB overhead = ~3.2G
# 800MB headroom in 4G container

# OR use percentage-based sizing:
-XX:MaxRAMPercentage=70.0       # Use 70% of container RAM for heap
```

---

### Incident 9: JVM Native Crash (hs_err_pid file)

**Symptoms:**
- JVM process disappears (no graceful shutdown)
- `hs_err_pid<PID>.log` file in working directory (or /tmp)
- Usually caused by JNI code, native libraries, or JDK bugs

**Diagnosis:**
```bash
# Read the crash file
cat hs_err_pid12345.log | head -100

# Key sections to check:
# 1. "SIGSEGV (0xb)" or "SIGBUS" — native memory access violation
# 2. "Current thread" — which thread crashed
# 3. "Stack" — native frames showing the crash location
# 4. "Java frames (J=compiled Java code..." — Java call stack
# 5. "Heap" section — heap state at time of crash
```

**Sample hs_err header:**
```
#
# A fatal error has been detected by the Java Runtime Environment:
#
#  SIGSEGV (0xb) at pc=0x00007f9a12345678, pid=12345, tid=0x00007f9a00000001
#
# JRE version: OpenJDK 17.0.8 (17.0.8+7)
# Java VM: OpenJDK 64-Bit Server VM (17.0.8+7, mixed mode, tiered, compressed oops)
# Problematic frame:
# C  [libnetty_transport_native.so+0x12345]  <- native library crash
```

**Common causes:**
- JNI library bug (Netty native transport, RocksDB, Snappy compression)
- Out-of-bounds native memory access
- JDK bug (check JDK release notes)
- Native memory corruption from direct ByteBuffer misuse

**Fix:** Update native library version, switch to Java implementation (remove native transport), or upgrade JDK.

---

### Incident 10: Slow Startup / High Memory on Startup

**Symptoms:**
- Spring Boot takes 45-60s to start (should be 10-15s)
- Memory jumps to 1.5GB immediately on startup
- Kubernetes readiness probe fails, pod restarts loop

**Diagnosis:**
```bash
# Enable startup timing
-Dspring.jmx.enabled=false  # disable unneeded JMX
--spring.main.lazy-initialization=true  # defer bean init

# Log class loading
-verbose:class 2>&1 | head -100   # show class loading storm

# Profile startup with JFR
-XX:StartFlightRecording=delay=5s,duration=60s,filename=/tmp/startup.jfr,settings=profile
```

**Common causes:**
1. Eager initialization of all beans (Spring loads everything at startup)
2. Slow database connectivity check (Flyway migration, HikariCP pool warmup)
3. Component scan of too many classes
4. JIT cold start (first requests slow before JIT kicks in)

**Fix:**
```java
// Lazy initialization — only create beans when first needed
@SpringBootApplication
public class App {
    public static void main(String[] args) {
        SpringApplication app = new SpringApplication(App.class);
        app.setLazyInitialization(true);  // Java 2.2+
        app.run(args);
    }
}
```

```bash
# Class Data Sharing — reduces startup time 20-40%
java -Xshare:dump -XX:SharedArchiveFile=app-cds.jsa -cp app.jar
java -Xshare:on  -XX:SharedArchiveFile=app-cds.jsa -jar app.jar
```

---

## Senior Trap Questions

### Trap 1: "High CPU always means my application code is in a loop"

**WRONG.** GC threads are counted as Java process CPU. When Old Gen is >95% and Full GC fires every 10 seconds:
- GC threads can consume 4-8 CPU cores
- Application threads are STW (stopped), adding nothing
- `top` shows 400-800% java CPU — all of it is GC

**Correct answer:** Before profiling application code, run `jstat -gcutil <pid> 1000` for 10 seconds. If `FGCT` is climbing and `FGC` is in double digits per minute, GC is the CPU consumer. Fix the memory issue first (leak, heap size), CPU will normalize.

---

### Trap 2: "A restart fixes the production incident"

**WRONG** (for your incident postmortem). A restart is an operational response that restores service, but it is NOT a fix. Memory leaks, deadlocks, thread pool misconfigurations, and connection leaks will all recur on the same schedule.

**Correct answer:** Restart buys time for root cause analysis. After restart: capture metrics (jstat, thread counts, connection pool stats) to establish baseline. Monitor the trend. Schedule RCA within 24 hours. The fix is in code or configuration — not in restart scripts.

---

### Trap 3: "StackOverflow always means infinite recursion"

**WRONG.** StackOverflow can also happen with:
- Very deep (but finite) recursion through framework layers (Spring AOP wrapping → JPA → Hibernate → JDBC → multiple interceptors → deep enough)
- Local variables that are large arrays: `byte[] buf = new byte[512*1024]` inside a method consumes 512KB of stack frame immediately
- Deeply nested XML/JSON deserialization with legitimate depth

**Correct answer:** Check the stack trace. If the same method repeats → infinite recursion. If it's a unique chain of 500+ different methods → the call stack is legitimately deep. Fix: `-Xss2m` to increase stack size, or refactor deep call chains.

---

### Trap 4: "HikariCP connection timeout means the database is slow"

**WRONG.** Connection timeout = no connection available in pool. Database could be fast but pool is too small. Two separate problems:
- **Pool starvation:** All 10 connections checked out, 11th request waits. Fix: increase `maximumPoolSize`.
- **Slow queries:** Connections are held longer, backing up the pool. Fix: optimize queries.

**Correct answer:** Check `hikaricp.connections.active` vs `maximumPoolSize`. If active = maximumPoolSize and `hikaricp.connections.pending > 0`, it's pool starvation. If active < maximumPoolSize but queries are slow, it's query performance. Different fixes.

---

### Trap 5: "Kubernetes OOMKill means the JVM's heap is too large"

**WRONG.** K8s OOMKill measures total container RSS, not JVM heap. A JVM with `-Xmx2g` can easily consume 3.5GB RSS because of metaspace, code cache, thread stacks, direct buffers, and JVM overhead.

**Correct answer:** RSS = heap + metaspace + code cache + (threads × stack size) + direct buffers + ~300MB JVM overhead. Set container memory limit = `-Xmx` + 1.0-1.5GB headroom. Use `-XX:MaxRAMPercentage=70` to let JVM self-size within container limits.

---

### Trap 6: "Just increase the heap to fix OOM"

**WRONG** (for leaks). Increasing heap for a memory leak:
- Delays the OOM by days or weeks
- Makes heap dumps slower and harder to analyze (4GB dump vs 2GB dump)
- Can increase Full GC pause times when they do occur (more to scan)
- Is not an engineering solution

**Correct answer:** First determine if OOM is from a leak or from undersized heap. Heap is undersized if: Old Gen fills on peak load but drains during low load. It's a leak if: Old Gen grows steadily regardless of load and never drops. Only increase heap for the undersized case. For leaks, find and fix the retention.

---

## Interview Cheat Sheet

### 10 Incidents Quick Reference
| # | Incident | First Diagnostic | Key Fix |
|---|----------|-----------------|---------|
| 1 | Heap OOM | `jcmd GC.class_histogram` | Bounded cache, close resources |
| 2 | High CPU | `jstat -gcutil` then async-profiler | Fix GC cause or hot method |
| 3 | App frozen | `jstack -l` → deadlock | Consistent lock ordering |
| 4 | Slow under load | HikariCP pending connections | Increase pool / optimize queries |
| 5 | Gradual OOM | Histogram diff over time | ThreadLocal.remove(), listener deregister |
| 6 | StackOverflow | Stack trace repeat pattern | Fix base case / iterate |
| 7 | RejectedExecution | Executor queue + thread counts | CallerRunsPolicy or larger queue |
| 8 | K8s OOMKill | kubectl describe → OOMKilled | Add native memory headroom |
| 9 | JVM crash | hs_err_pid log | Update native lib / upgrade JDK |
| 10 | Slow startup | JFR startup recording | Lazy init, CDS |

### Triage Mantra (say this)
> "I follow the signal: CPU? Check GC first, then profile. Memory? Check histogram, then heap dump. Frozen? Thread dump. K8s OOMKill? RSS, not heap. Crash? hs_err file. Never restart before capturing evidence."

### Production-Safe Evidence Capture (in order)
```
1. jstat -gcutil <pid> 1000 10     # GC trend — safe
2. jcmd <pid> Thread.print         # Thread state — safe  
3. jcmd <pid> GC.class_histogram   # Object counts — triggers GC
4. async-profiler cpu 30s          # CPU profile — <3% overhead
5. jcmd <pid> GC.heap_dump         # Heap dump — PAUSE, take pod out first
```
