# Production JVM Debugging Tools — 15 YOE Interview Prep

**2026 Edition | jcmd · jstack · jmap · jstat · Arthas · async-profiler · JFR | Scenario Q&As + Senior Traps**

---

## Big Picture: Tool Selection Guide

```
WHAT IS THE PROBLEM?
│
├─ High CPU?
│   ├─ Check GC: jstat -gcutil <pid> 1000
│   ├─ Profile: async-profiler -e cpu -d 30 <pid>
│   └─ Live method trace: arthas trace <class> <method>
│
├─ Memory growing / OOM?
│   ├─ Histogram: jcmd <pid> GC.class_histogram
│   ├─ Heap dump: jcmd <pid> GC.heap_dump /tmp/heap.hprof
│   └─ Leak check: jstat -gcutil <pid> 5000 (O% never dropping)
│
├─ App unresponsive / slow?
│   ├─ Thread dump: jcmd <pid> Thread.print
│   ├─ Deadlock check: jstack -l <pid>
│   └─ Lock contention: arthas monitor <class> <method>
│
├─ Need JVM internals?
│   ├─ Flags: jcmd <pid> VM.flags
│   ├─ Properties: jcmd <pid> VM.system_properties
│   └─ Native memory: jcmd <pid> VM.native_memory summary
│
└─ Production-safe continuous profiling?
    └─ JFR: jcmd <pid> JFR.start duration=60s filename=/tmp/rec.jfr
```

```
TOOL SAFETY MATRIX (★ = most production-safe)
┌──────────────────────┬──────────┬──────────────────────────────────┐
│ Tool                 │ Safety   │ Risk                             │
├──────────────────────┼──────────┼──────────────────────────────────┤
│ jcmd Thread.print    │ ★★★★★   │ None — reads thread state        │
│ jcmd VM.flags        │ ★★★★★   │ None — reads flags               │
│ jstat -gcutil        │ ★★★★★   │ None — reads GC counters         │
│ async-profiler cpu   │ ★★★★    │ <3% CPU overhead                 │
│ JFR start            │ ★★★★    │ <1% overhead with defaults       │
│ Arthas trace         │ ★★★     │ Instruments target class         │
│ jcmd GC.heap_dump    │ ★★      │ STW pause while writing dump     │
│ jmap -dump           │ ★       │ STW pause + can OOM mid-dump     │
│ jstack -F            │ ★       │ ptrace attach, disruptive        │
│ /actuator/heapdump   │ ★       │ Full GC + heap write pause       │
└──────────────────────┴──────────┴──────────────────────────────────┘
```

---

## Conversational Interview Script

**"Walk me through how you debug a production JVM issue."**

> "My first move is always the least invasive tool. If I get a 'something is wrong' alert, I'll run `jcmd <pid> VM.flags` to see what JVM was started with — heap size, GC algorithm, any flags that matter. Then `jstat -gcutil <pid> 1000` for 10 seconds to see if GC is the culprit. It shows Eden, Old Gen, Metaspace percentages and GC time columns live.
>
> If CPU is the problem, `async-profiler -e cpu -d 30 -f /tmp/out.html <pid>` gives me a flame graph in 30 seconds with under 3% overhead — much safer than JVisualVM in production. For a memory problem, `jcmd <pid> GC.class_histogram` tells me the top objects by count and size without a full heap dump pause.
>
> I use Arthas when I need to inspect a running method — `trace com.myapp.Service processOrder` shows call tree with timing, and `watch com.myapp.Service processOrder returnObj` lets me see return values live. No restart required.
>
> JFR is my always-on insurance — I run it with a 1-hour circular buffer. When an incident happens, `jcmd <pid> JFR.dump filename=/tmp/incident.jfr` captures everything that happened before the alert, which is invaluable."

---

## Scenario Q&As

### Scenario 1: "Find the slow method in a live Spring Boot service — no restart allowed"

**Q:** Your order processing service response time jumped from 50ms to 800ms. How do you find the slow method in production without restarting?

**A:** Three tools in order:

**Step 1 — Arthas trace (fastest diagnosis):**
```bash
# Start Arthas
java -jar arthas-boot.jar <pid>

# Trace processOrder and all its sub-calls, show top 20 slowest
trace com.myapp.OrderService processOrder '#cost > 100'

# Output shows call tree with timing:
# ---[800ms]--- OrderService.processOrder()
#     ---[780ms]--- InventoryService.checkStock()
#         ---[775ms]--- InventoryRepository.findByProductId()
#             ---[770ms]--- HikariCP.getConnection()  <-- HERE
```

**Step 2 — Watch the slow method's args:**
```bash
# See what product ID causes the slowdown
watch com.myapp.InventoryRepository findByProductId '{params, returnObj}' '#cost > 500'
```

**Step 3 — Root cause:** HikariCP connection wait = pool too small for current load. Fix: increase `maximumPoolSize` or investigate why connections aren't being returned.

---

### Scenario 2: "What jcmd commands do you run first when you SSH into a production box with problems?"

**Q:** You SSH into a production server. The app is behaving oddly. What jcmd commands do you run in what order?

**A:**
```bash
# 1. Find the PID
jps -l

# 2. What flags was JVM started with? (heap size, GC, dump-on-OOM?)
jcmd <pid> VM.flags

# 3. GC health — run for 10 iterations, 1 second apart
jstat -gcutil <pid> 1000 10
# Watch: O% (Old Gen) growing every iteration = memory leak
# Watch: FGC column incrementing = Full GC happening
# Watch: FGCT high relative to uptime = GC overhead

# 4. Thread snapshot
jcmd <pid> Thread.print > /tmp/threads.txt
grep -c "java.lang.Thread.State: BLOCKED" /tmp/threads.txt

# 5. Top objects without heap dump pause
jcmd <pid> GC.class_histogram | head -30

# 6. Native memory breakdown (if NMT enabled)
jcmd <pid> VM.native_memory summary
```

---

### Scenario 3: "jstat output interpretation"

**Q:** You run `jstat -gcutil <pid> 1000`. The output shows: `S0=0 S1=98 E=85 O=97 M=78 YGC=1432 YGCT=12.4 FGC=8 FGCT=45.2`. What does this tell you?

**A:**

```
S0=0    S1=98   → Survivor 1 is 98% full — active copying into S1 from last minor GC
E=85           → Eden 85% full — another minor GC coming soon
O=97           → Old Gen 97% full — CRITICAL, about to trigger Full GC or OOM
M=78           → Metaspace 78% fine
YGC=1432       → 1432 young GCs (check uptime: 1432 GCs in 1 hour = one every 2.5s, frequent)
YGCT=12.4      → 12.4 seconds total young GC time
FGC=8          → 8 Full GCs (this is high)
FGCT=45.2      → 45.2 seconds in Full GC (each Full GC ~5.6s — very long)
```

**Action:** Old Gen 97% is the emergency. Run `jcmd <pid> GC.class_histogram` to find retention. Old Gen this high means either a leak or heap is undersized. With FGC=8 and FGCT=45.2s, we're potentially over the "98% in GC, <2% work done" threshold for GC overhead limit.

---

### Scenario 4: "Arthas in production — what can you safely do?"

**Q:** A colleague suggests using Arthas to debug a production issue. What's safe vs risky?

**A:**

**Safe (read-only operations):**
```bash
# Method call tracing — shows timing tree
trace com.app.Service method '#cost > 200'

# Method monitoring — call count, avg time, error rate
monitor com.app.Service method -c 5  # 5-second cycles

# Watch return values (be careful of sensitive data)
watch com.app.Service method returnObj -x 2

# JVM flags and system info
version / jvm / sysprop / sysenv

# Class/classloader info
classloader -l
sc com.app.*  # class search
sm com.app.Service  # method search

# CPU profiling (async-profiler integration)
profiler start --event cpu
profiler stop --file /tmp/cpu.html
```

**Use with care:**
```bash
# Redefine class (hot-swap) — changes behavior
redefine /tmp/MyClass.class

# Exec OGNL expressions — can trigger side effects
ognl "@com.app.Config@getInstance().reload()"

# Set field value
field com.app.MyService #timeout 5000
```

**Rule:** Arthas uses Java instrumentation — it does NOT change bytecode on disk. Safe for read ops. Hot-swap (`redefine`) should be tested in staging first.

---

### Scenario 5: "How do you use JFR for always-on profiling?"

**Q:** How would you set up Java Flight Recorder for production use?

**A:**

**JVM startup flags (always-on with circular buffer):**
```bash
-XX:StartFlightRecording=name=continuous,
    settings=profile,
    maxsize=250m,
    maxage=1h,
    dumponexit=true,
    filename=/var/log/jfr/exit.jfr
```

**Dump on incident:**
```bash
# Dump last 30 minutes of data
jcmd <pid> JFR.dump name=continuous filename=/tmp/incident.jfr maxage=30m

# Start a timed recording
jcmd <pid> JFR.start duration=120s filename=/tmp/timed.jfr settings=profile

# Check recording status
jcmd <pid> JFR.check
```

**What JFR captures (overhead <1%):**
- CPU samples (method profiling)
- GC events with pause times
- Thread states and locks
- I/O latency
- Exceptions and errors
- Class loading events
- Heap statistics

**Analyze with JMC (Java Mission Control):** Open `.jfr` file, check "Automated Analysis" tab for top issues.

---

### Scenario 6: "jmap vs jcmd for heap dump — which do you use?"

**Q:** You need to capture a heap dump from production. Do you use jmap or jcmd?

**A:** Always `jcmd` first. Here's why:

```bash
# Preferred: jcmd GC.heap_dump
jcmd <pid> GC.heap_dump /tmp/heap-$(date +%Y%m%d-%H%M%S).hprof
# Safe, uses JVM's built-in mechanism, signals JVM cleanly

# Legacy: jmap -dump (avoid in production)
jmap -dump:format=b,live,file=/tmp/heap.hprof <pid>
# Issues: triggers full GC (live filter), can cause OOM mid-dump if heap is near limit

# Best: set flag at startup, JVM auto-dumps on OOM
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/var/dumps/
# Zero extra pause — JVM writes dump during OOM handling
```

**Mitigating the pause:** Heap dump writes all live objects. For 4GB heap, this can take 10-30 seconds of STW pause. Mitigate by:
1. Route traffic to other instances first (take pod out of LB)
2. Schedule during low traffic window
3. Use `-XX:+HeapDumpOnOutOfMemoryError` so it only fires when OOM is inevitable anyway

---

### Scenario 7: "Live debugging with Spring Actuator"

**Q:** How do you use Spring Boot Actuator for production debugging?

**A:**

```yaml
# application.yml — expose carefully
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,threaddump,loggers
        # DO NOT expose heapdump in load-balanced prod
  endpoint:
    health:
      show-details: when_authorized
```

```bash
# Thread dump (safe)
curl -s http://localhost:8080/actuator/threaddump | jq '.threads[] | select(.threadState == "BLOCKED")'

# Live metrics — JVM memory
curl -s http://localhost:8080/actuator/metrics/jvm.memory.used | jq '.measurements[0].value'

# Change log level at runtime (no restart!)
curl -X POST http://localhost:8080/actuator/loggers/com.myapp.OrderService \
  -H 'Content-Type: application/json' \
  -d '{"configuredLevel": "DEBUG"}'
# After debugging, set back to INFO

# Heap dump (HIGH RISK — full GC + write pause)
# curl http://localhost:8080/actuator/heapdump > /tmp/heap.hprof
# Only use on instance already taken out of load balancer
```

---

### Scenario 8: "Reading jstat columns — interview quiz"

**Q:** What does each column in `jstat -gcutil` mean?

**A:**

```
S0   — Survivor space 0 utilization (%)
S1   — Survivor space 1 utilization (%)
E    — Eden space utilization (%)
O    — Old Gen (Tenured) utilization (%)
M    — Metaspace utilization (%)
CCS  — Compressed Class Space utilization (%)
YGC  — Young GC count (cumulative)
YGCT — Young GC time (seconds cumulative)
FGC  — Full GC count (cumulative)
FGCT — Full GC time (seconds cumulative)
GCT  — Total GC time = YGCT + FGCT

Alert thresholds:
  O > 80%       → investigate retention / heap size
  FGC > 1/hr    → too frequent for latency-sensitive service
  FGCT/uptime   → if >5% of uptime spent in Full GC → GC overhead alert
  M > 90%       → Metaspace leak, classloader leak
```

**Pro tip for interview:** Calculate GC overhead: `FGCT / (uptime_seconds)`. If >5%, GC is eating your throughput.

---

## Advanced Scenarios

### Advanced 1: "NMT — finding native memory growth"

**Q:** Your Java process RSS grows past `-Xmx` by 2GB. Where is the extra memory?

**A:** Enable NMT (Native Memory Tracking) at startup:
```bash
-XX:NativeMemoryTracking=summary   # low overhead, show categories
-XX:NativeMemoryTracking=detail    # higher overhead, show per-allocation
```

```bash
# Baseline snapshot
jcmd <pid> VM.native_memory baseline

# After memory growth
jcmd <pid> VM.native_memory summary.diff
```

**Sample output:**
```
Total: reserved=6.2GB, committed=5.8GB  (+800MB since baseline)

-       Java Heap (reserved=2048MB, committed=2048MB)
-          Thread (reserved=2100MB, committed=2100MB)   ← 2100 threads × 1MB stack
-       Metaspace (reserved=512MB, committed=256MB)
-    Code Cache    (reserved=256MB, committed=156MB)
- Direct Buffers  (reserved=400MB, committed=400MB)    ← GROWING
```

**Root cause:** Direct Buffers 400MB and growing = Netty ByteBuf not being released, or NIO ByteBuffer.allocateDirect() leak. Track with `-Dio.netty.leakDetection.level=PARANOID` in non-prod.

---

### Advanced 2: "Arthas OGNL expressions — advanced usage"

**Q:** How do you use Arthas OGNL for live state inspection?

**A:**
```bash
# Read a static field
ognl "@com.myapp.Config@INSTANCE.getTimeout()"

# Read a Spring Bean field (via ApplicationContext)
ognl "#springCtx=@org.springframework.web.context.ContextLoader@getCurrentWebApplicationContext(), \
      #bean=#springCtx.getBean('orderService'), \
      #bean.cacheSize"

# Call a method (read-only)
ognl "@java.lang.Runtime@getRuntime().availableProcessors()"

# Inspect a thread pool
ognl "@com.myapp.ExecutorConfig@executor.getActiveCount()"
ognl "@com.myapp.ExecutorConfig@executor.getQueue().size()"
```

**Warning:** OGNL can call any method. Only call read methods (`get*`, `is*`). Never call mutating methods in production unless you understand exactly what will happen.

---

### Advanced 3: "jcmd VM.native_memory vs -Xmx — the hidden memory gap"

**Q:** A container with 4GB RAM keeps getting OOM-killed by Kubernetes even though `-Xmx2g` is set. Why?

**A:** JVM uses more than just heap. The full breakdown:

```
-Xmx2g      = 2GB heap (max)
+ Metaspace  = typically 256-512MB (unlimited by default!)
+ Code Cache = 240MB default (JIT compiled code)
+ Thread stacks = threads × stack size (200 threads × 1MB = 200MB)
+ Direct buffers = Netty/NIO allocations outside heap
+ GC overhead = G1GC internal bookkeeping ~5-10%
────────────────────────────────────────────
Total RSS    = 3.5-4GB easily with -Xmx2g
```

**Fix:**
```bash
-Xmx2g
-XX:MaxMetaspaceSize=256m      # cap metaspace
-XX:ReservedCodeCacheSize=256m # cap code cache
-Xss512k                       # reduce thread stack (256k minimum safe)
-XX:MaxDirectMemorySize=256m   # cap direct buffers
# Total budget: ~3.1GB, fits in 4GB container with headroom
```

**Always leave 20-25% headroom above JVM memory for OS, off-heap, and JVM overhead.**

---

### Advanced 4: "Programmatic JMX monitoring"

**Q:** How do you monitor JVM metrics programmatically?

**A:**
```java
import java.lang.management.*;

MemoryMXBean mem = ManagementFactory.getMemoryMXBean();
long heapUsed = mem.getHeapMemoryUsage().getUsed();
long heapMax  = mem.getHeapMemoryUsage().getMax();
double heapPct = (double) heapUsed / heapMax * 100;

List<GarbageCollectorMXBean> gcBeans = ManagementFactory.getGarbageCollectorMXBeans();
for (GarbageCollectorMXBean gc : gcBeans) {
    System.out.printf("%s: count=%d, time=%dms%n",
        gc.getName(), gc.getCollectionCount(), gc.getCollectionTime());
}

ThreadMXBean threads = ManagementFactory.getThreadMXBean();
long[] deadlocked = threads.findDeadlockedThreads();
if (deadlocked != null) {
    log.error("DEADLOCK DETECTED: {} threads", deadlocked.length);
}
```

**In Spring Boot:** Micrometer exposes all these via `/actuator/metrics` with Prometheus format automatically.

---

## Senior Trap Questions

### Trap 1: "jmap -dump is the standard way to get a heap dump"

**WRONG.** `jmap -dump` is legacy and risky in production:
- With `live` option, triggers a full GC before dump (causes STW pause)
- Attaches via PTRACE, can destabilize processes under load
- Can fail with OOM if heap is already near limit (dump requires extra memory)

**Correct answer:** Use `jcmd <pid> GC.heap_dump /path/file.hprof` — it uses the JVM's internal safe-dump mechanism. Better yet, set `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps/` at startup so it captures automatically on OOM without any intervention.

---

### Trap 2: "jstack -F is a safe way to get a thread dump from a stuck JVM"

**WRONG.** `-F` uses PTRACE to forcibly attach, which:
- Can take 10-30 seconds on a busy JVM
- May cause other threads to freeze during attachment
- Can kill the JVM if it's in an inconsistent state

**Correct answer:** Try `jcmd <pid> Thread.print` first (signals the JVM to print its own threads, safe). If the JVM is truly hung, `kill -3 <pid>` sends SIGQUIT which triggers a thread dump to stdout/stderr — the JVM handles it internally and continues running. `-F` is last resort.

---

### Trap 3: "Arthas changes production code permanently"

**WRONG.** Arthas uses Java Instrumentation API (`java.lang.instrument`) for bytecode manipulation — it does NOT modify `.class` files on disk or in the JAR. Changes are in-memory only and disappear when:
- Arthas session ends (`stop` command)
- JVM restarts

**Correct answer:** Arthas is safe for read-only operations (trace, watch, monitor, profiler). Hot-swap (`redefine`) modifies the loaded class in memory only. Still: test hot-swaps in staging first, and be careful not to instrument high-throughput methods with expensive watches in production.

---

### Trap 4: "jstat shows real-time GC pauses"

**WRONG.** `jstat -gcutil <pid> 1000` shows **cumulative counters**. The YGCT/FGCT columns accumulate from JVM startup. To get current pause time:
- Take two readings 10 seconds apart
- Calculate delta: `FGCT_now - FGCT_before` = GC time in that window
- `(delta / window_seconds) × 100` = % time in GC

**Correct answer:** `jstat` is for trend analysis, not instantaneous pause time. For real-time GC events with exact pause durations, use GC logging: `-Xlog:gc*:file=gc.log:time,uptime` or JFR.

---

### Trap 5: "Spring Actuator /heapdump is production-safe"

**WRONG.** `/actuator/heapdump` triggers:
1. A full GC (to capture live objects only)
2. Writes entire heap to disk synchronously
3. The HTTP response doesn't return until the dump is written

For a 4GB heap, this means a potential 20-60 second response time and STW pause. On a load-balanced service, this causes timeouts and health-check failures on that pod.

**Correct answer:** Either set `-XX:+HeapDumpOnOutOfMemoryError` and let JVM auto-dump, or use `jcmd GC.heap_dump` after first draining traffic from the pod via load balancer removal.

---

### Trap 6: "More jstat GC columns = more GC happening"

**WRONG.** jstat counts are cumulative since JVM start. A JVM running for 7 days will show large GC counts even if GC rate is perfectly normal. Always contextualize with uptime.

**Correct answer:** Convert to rates: `YGC / uptime_minutes = minor GCs per minute`. For a healthy Spring Boot service, 1-5 minor GCs per minute is normal. More than 10/min suggests excessive object allocation. `FGC > 1 per hour` for latency-sensitive services is worth investigating.

---

## Tool Quick Reference

```bash
# jcmd — Swiss Army Knife
jcmd <pid> help                          # list all commands
jcmd <pid> VM.flags                      # JVM startup flags
jcmd <pid> VM.system_properties          # System properties
jcmd <pid> VM.native_memory summary      # Native memory breakdown (needs NMT)
jcmd <pid> Thread.print                  # Thread dump (safe)
jcmd <pid> GC.heap_dump /tmp/heap.hprof  # Heap dump (causes pause)
jcmd <pid> GC.class_histogram            # Object histogram (fast, triggers GC)
jcmd <pid> JFR.start duration=60s filename=/tmp/rec.jfr  # Start JFR
jcmd <pid> JFR.dump filename=/tmp/now.jfr                # Dump current JFR buffer

# jstat — GC Stats
jstat -gcutil <pid> 1000 20    # 20 iterations, 1s apart
jstat -gccause <pid> 5000      # Include last GC cause
jstat -gcnew <pid> 2000        # Young gen stats

# jstack — Thread Dumps
jstack <pid>                   # Standard thread dump
jstack -l <pid>                # Include lock info (ownable synchronizers)
kill -3 <pid>                  # SIGQUIT — JVM prints dump to stdout

# async-profiler
profiler.sh -e cpu -d 30 -f /tmp/cpu.html <pid>       # CPU flame graph
profiler.sh -e alloc -d 30 -f /tmp/alloc.html <pid>   # Allocation profiling
profiler.sh -e wall -d 30 -f /tmp/wall.html <pid>     # Wall-clock (includes I/O wait)
profiler.sh -e lock -d 30 -f /tmp/lock.html <pid>     # Lock contention

# Arthas (start: java -jar arthas-boot.jar <pid>)
trace com.app.Service method '#cost > 100'    # Method call tree with timing
watch com.app.Service method '{params,returnObj}' '#cost > 200'  # Args + return
monitor com.app.Service method -c 5           # Throughput, avg time, error rate
profiler start --event cpu && profiler stop --file /tmp/cpu.html
ognl "@java.lang.System@currentTimeMillis()"  # OGNL expression
classloader -l                                 # List classloaders + class counts
```

---

## Interview Cheat Sheet

### Tool Selection (say this out loud)
> "I always start with the least-invasive tool: `jstat` for GC trend, `jcmd Thread.print` for thread state. I use `async-profiler` for CPU — never JVisualVM in production because of safepoint bias and overhead. `jcmd GC.heap_dump` not `jmap`. Arthas for live method inspection without restart. JFR as always-on continuous profiling."

### Key Numbers
| Metric | Threshold |
|--------|-----------|
| Young GC frequency | 1-5/min = normal; >10/min = excessive allocation |
| Full GC frequency | <1/hr for latency services |
| GC overhead | <5% of total time |
| Old Gen % | >80% = investigate; >95% = emergency |
| async-profiler overhead | <3% CPU |
| JFR overhead | <1% with default settings |
| jcmd GC.heap_dump | 5-30s STW pause for 2-4GB heap |

### When something is wrong, run these in order:
1. `jcmd <pid> VM.flags` — what's the JVM configured with?
2. `jstat -gcutil <pid> 1000 10` — is GC the cause?
3. `jcmd <pid> Thread.print | grep -c BLOCKED` — thread contention?
4. `jcmd <pid> GC.class_histogram | head -20` — top objects?
5. `async-profiler -e cpu -d 30 -f /tmp/cpu.html <pid>` — CPU profile?
