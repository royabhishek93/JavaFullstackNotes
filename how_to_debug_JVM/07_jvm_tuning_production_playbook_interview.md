# JVM Tuning Production Playbook — 15-YOE Java Architect Interview Prep

> Target: Senior/Staff/Principal Java Architect interviews. Voice: seasoned engineer who has debugged production
> incidents at 3am, not someone reading from a textbook.

---

## 1. Big Picture: JVM Memory Model & Tuning Decision Trees

### 1a. JVM Memory Layout (What -Xmx Does NOT Control)

```
+---------------------------------------------------------------+
|                     OS PROCESS MEMORY                         |
|                                                               |
|  +---------------------------+  +--------------------------+  |
|  |     JVM HEAP (GC'd)       |  |   JVM NATIVE MEMORY      |  |
|  |                           |  |  (NOT controlled by -Xmx) |  |
|  |  +---------------------+  |  |                          |  |
|  |  |   Young Gen          |  |  |  Metaspace (class meta) |  |
|  |  |  Eden | S0 | S1      |  |  |  Code Cache (JIT)       |  |
|  |  +---------------------+  |  |  Thread Stacks           |  |
|  |  |   Old Gen (Tenured)  |  |  |  Direct Buffers (NIO)   |  |
|  |  |                      |  |  |  GC internal data        |  |
|  |  +---------------------+  |  |  JVM overhead            |  |
|  +---------------------------+  +--------------------------+  |
|                                                               |
|  Total Process RSS = Heap + Native ~= -Xmx * 1.25 to 1.40    |
+---------------------------------------------------------------+
```

**Key insight**: `-Xmx 4g` does NOT mean the JVM process uses 4GB. Expect 5-5.5GB RSS.
This is why K8s containers OOMKill you even when heap looks fine.

---

### 1b. GC Algorithm Selection Decision Tree

```
                   Start: Choose GC Algorithm
                           |
              Is this a batch/offline job?
             /                            \
           YES                             NO
           |                               |
     Parallel GC                  Heap size > 8GB?
  (-XX:+UseParallelGC)            /              \
  Max throughput,                YES              NO
  accept long pauses              |               |
                         Need <1ms pauses?    G1GC (default Java 9+)
                         /           \        Balanced latency+throughput
                        YES           NO      Good for 1GB-8GB heaps
                         |             |
                       ZGC           G1GC
                    or Shenandoah    with tuned
                    (<1ms, 10-20%    MaxGCPauseMillis
                    CPU overhead)
```

---

### 1c. K8s Container Memory Model

```
+----------------------------------------------------------+
|             K8s Pod                                       |
|                                                           |
|  spec.containers[].resources:                             |
|    requests:                                              |
|      memory: "4Gi"   <-- scheduling, node affinity        |
|    limits:                                                |
|      memory: "4Gi"   <-- cgroup hard limit, OOMKill here  |
|                                                           |
|  JVM with -XX:+UseContainerSupport (Java 8u191+):         |
|    Sees 4GB, not host 64GB                                |
|                                                           |
|  Safe allocation:                                         |
|    -XX:MaxRAMPercentage=75.0                               |
|    => JVM heap = 3GB, leaves 1GB for native memory        |
|                                                           |
|  DANGER ZONE:                                             |
|    -Xmx4g with limits.memory=4Gi                          |
|    => Heap alone = 4GB + native = OOMKill from cgroup     |
+----------------------------------------------------------+

Memory Budget Rule:
  Container Limit = Heap + 0.25*Heap (native overhead) + buffer
  Safe Heap = container_limit * 0.70 to 0.75
```

---

### 1d. JVM Startup Tuning Decision Tree

```
  What is your startup time requirement?
           |
    < 50ms needed?
   /              \
  YES              NO
   |               |
GraalVM          < 5 seconds?
Native Image    /            \
(no JIT,      YES              NO
 no reflect)   |               |
               CDS           Standard JVM
            (Class Data     with TieredCompilation
             Sharing) +      C1 warms up in ~30s
            Spring AOT       C2 peak perf ~2-5min
```

---

## 2. Conversational Interview Script (15-YOE Architect Voice)

### Opening: When the interviewer says "tell me about JVM tuning"

> "Happy to. In 15 years I've approached this in layers — you can't tune what you don't measure, so I always
> start with establishing baselines: GC log analysis, JFR recordings, and native memory tracking before
> touching a single flag.
>
> At the heap sizing layer, rule one in production is always set -Xms equal to -Xmx. I've seen teams leave
> Xms at the JVM default and wonder why they're seeing periodic 200ms pauses — that's the JVM resizing
> the heap. In containers, that's actually worse because it can trigger OOMKill while the heap is
> expanding.
>
> At the GC selection layer, I use G1GC as my default for most Spring Boot services — it's been the JVM
> default since Java 9 and it handles the mixed-age collection pattern you get with HTTP request processing
> very well. For services that are genuinely latency-critical — think payment processing or real-time fraud
> detection — I've moved to ZGC. The sub-millisecond pauses are real, but you pay 10-20% CPU overhead
> because GC work is concurrent.
>
> In K8s, there's a whole additional layer: the JVM must be container-aware. Java 8u191 introduced
> UseContainerSupport which is on by default, but I still explicitly set MaxRAMPercentage rather than
> hardcoding Xmx, because it survives resource limit changes without a config update."

---

### On Being Asked: "What flags do you use in production?"

> "Let me give you my baseline Spring Boot production set. For a 4GB container running a REST API:
>
>   -server
>   -XX:+UseG1GC
>   -Xms2g -Xmx2g
>   -XX:MaxGCPauseMillis=200
>   -XX:+HeapDumpOnOutOfMemoryError
>   -XX:HeapDumpPath=/dumps/heap.hprof
>   -Xlog:gc*:file=/logs/gc.log:time,uptime,level,tags:filecount=5,filesize=20m
>   -XX:+ExitOnOutOfMemoryError
>
> That last flag — ExitOnOutOfMemoryError — is opinion-dividing. I prefer it because a JVM with an OOM
> is usually thrashing: GC is running constantly, throughput is near zero, and all you're doing is making
> your users wait while Kubernetes is eventually going to kill it anyway. Exit fast, let the health check
> fail, let the deployment controller restart a fresh instance. The heap dump captured the evidence you
> need for root cause."

---

## 3. Scenario Q&As — Production Tuning

### Scenario 1: Microservice Getting OOMKilled in K8s Despite Low Heap Usage

**Interviewer:** "We have a Spring Boot service running in a pod with 2GB limit. Java heap peaks at 800MB
(monitored via Prometheus JVM metrics). But K8s OOMKills the pod every few hours. What's happening?"

**Answer:**

> "Classic native memory leak masquerading as a heap problem. The 800MB you're seeing in Prometheus is heap
> only. The JVM process RSS includes several other regions that micrometer and standard JVM metrics don't
> expose by default.
>
> My diagnostic path:
>
> Step 1: Enable native memory tracking:
>   -XX:NativeMemoryTracking=summary
>
> Step 2: After reproducing, run:
>   jcmd <pid> VM.native_memory summary
>
> This gives you a breakdown: Heap, Metaspace, Code Cache, Thread stacks, Direct buffers, GC internal.
>
> Common culprits at 15 years of production experience:
>
> 1. Direct ByteBuffer leak (Netty, Kafka, NIO): appears in 'Other' or 'Internal' in native memory.
>    Symptom: off-heap memory grows without bound.
>    Fix: ensure ByteBuffers are released, tune -XX:MaxDirectMemorySize
>
> 2. Metaspace leak: usually from dynamic class generation (CGLIB, Groovy scripts, JOOQ codegen at runtime,
>    Spring proxies in a loop). Metaspace is unbounded by default.
>    Fix: -XX:MaxMetaspaceSize=512m so you get an OOM with a heap dump instead of a silent RSS creep
>
> 3. Thread stack explosion: each platform thread = 512KB-1MB stack.
>    256 threads = 128-256MB just in stacks.
>    Fix: -Xss256k for services that don't use deep recursion, or migrate to virtual threads
>
> 4. Code cache full: long-running services can fill code cache, causing JIT deoptimization.
>    Fix: -XX:ReservedCodeCacheSize=512m
>
> Given the 2GB limit and 800MB heap peak, my first guess is direct buffer leak from a Netty-based client
> (common in WebFlux or gRPC services). The heap looks fine because the allocations are off-heap."

---

### Scenario 2: P99 Latency Spikes Every 2 Hours

**Interviewer:** "Our service has P99 latency of 15ms normally. Every ~2 hours we see a spike to 2-5 seconds
for about 30 seconds. The pattern is regular. What would you investigate?"

**Answer:**

> "That timing regularity is the key signal. Random latency spikes are harder — regular ones usually point
> to a scheduled event. My differential is:
>
> 1. Full GC triggered by Old Gen exhaustion (most likely)
>    Check: gc.log for 'Pause Full' or 'GC(N) Pause Young (Full)' entries
>    The 30-second duration at 2-hour intervals fits a large heap Full GC
>
> 2. Scheduled tasks: Spring's @Scheduled, cron jobs, cache eviction timers
>
> 3. Connection pool maintenance: HikariCP has housekeeping thread every 30 seconds but that wouldn't
>    cause 2-hour intervals
>
> My investigation:
>
> First, grep GC logs:
>   grep 'Pause Full' /logs/gc.log | awk '{print $1, $NF}'
>
> If Full GCs are there, the follow-up question is why Old Gen fills every 2 hours:
> - Objects surviving too many Young GC cycles (tenure threshold too low)
> - Actual memory leak with slow accumulation
> - Large object allocation going directly to Old Gen (TLAB overflow)
>
> Tune path for G1GC:
>   -XX:G1HeapRegionSize=16m           # Prevents large objects bypassing Young Gen
>   -XX:G1NewSizePercent=30            # More Young Gen space
>   -XX:G1MaxNewSizePercent=50
>   -XX:MaxGCPauseMillis=100           # More aggressive GC scheduling
>
> If after tuning Full GCs persist, the answer is ZGC — its concurrent collection eliminates Full GC pauses
> by design, though you take the CPU overhead hit."

---

### Scenario 3: New Deployment is Slow for First 5 Minutes

**Interviewer:** "After each deployment, users complain about slow responses for the first 3-5 minutes.
After that the service is fast. How do you fix this?"

**Answer:**

> "JVM warm-up. This is tiered compilation doing its job but doing it too slowly for your SLO.
>
> What's happening:
>   Level 0: Interpreted (slow, instant start)
>   Level 1-3: C1 compiled (fast compilation, moderate performance, kicks in seconds)
>   Level 4: C2 compiled (slow compilation, peak performance, minutes)
>
> The first N invocations of each method are interpreted. Hot methods get profiled, then C1-compiled,
> then if hot enough C2-compiled. During that ramp, you're running interpreted or lightly optimized code.
>
> Solutions in order of complexity:
>
> Option 1: Traffic warming in the load balancer
>   Use a readiness probe that does internal warm-up calls before the pod enters rotation.
>   Spring Boot Actuator /actuator/health for basic readiness.
>   Better: a custom /actuator/warmup endpoint that exercises hot code paths.
>
> Option 2: Class Data Sharing (CDS) — reduces startup time
>   Step 1: Generate archive on build:
>     java -Xshare:dump -XX:SharedArchiveFile=app.jsa -cp app.jar
>   Step 2: Run with archive:
>     java -Xshare:on -XX:SharedArchiveFile=app.jsa -jar app.jar
>   Savings: 20-40% startup time, lower memory when multiple JVMs share the archive
>
> Option 3: Spring AOT + GraalVM Native
>   If startup < 100ms is required, compile to native image.
>   Trade-off: no JIT means peak throughput is 20-40% lower than JVM.
>   Reflection, dynamic proxies, CGLIB need explicit registration.
>   Not suitable for all Spring applications without significant configuration.
>
> Option 4: AppCDS with dynamic archive (Java 13+)
>   java -XX:ArchiveClassesAtExit=app-dynamic.jsa -jar app.jar
>   Captures classes loaded during an actual run, better than static dump."

---

### Scenario 4: High CPU Usage After Deployment Despite Low Traffic

**Interviewer:** "Immediately after deployment, CPU is pegged at 80-90% even with only 10 RPS.
After 2 minutes it drops to 5%. What's happening?"

**Answer:**

> "This is the JIT compiler at work. During warm-up, the JIT compilation threads run at full blast
> compiling hot methods. For a Spring Boot app, startup involves a burst of class loading and
> compilation activity.
>
> This is actually expected and generally healthy. The question is whether it's causing a problem.
>
> If 2 minutes of high CPU causes pods to be killed by K8s liveness probes or causes SLO violations:
>
> Fix 1: Tune liveness probe to give JVM time to warm up
>   livenessProbe:
>     initialDelaySeconds: 60    # Was 10
>     periodSeconds: 10
>     failureThreshold: 3
>
> Fix 2: Separate readiness from liveness
>   readinessProbe: check if app is ready to serve
>   livenessProbe: check if app is still alive (longer timeout)
>
> Fix 3: Limit JIT compiler thread count to reduce startup CPU burst
>   -XX:CICompilerCount=2    # Default is proportional to CPU count
>   Trade-off: slower warm-up but smoother CPU curve
>
> Fix 4: If using HPA (Horizontal Pod Autoscaler), it may scale up during startup thinking it needs
> more pods. Add a cool-down period or use custom metrics that exclude startup phase."

---

### Scenario 5: Metaspace OutOfMemoryError in Production

**Interviewer:** "We're seeing java.lang.OutOfMemoryError: Metaspace in production on a service that
dynamically processes Groovy scripts. How do you approach this?"

**Answer:**

> "Metaspace OOM from dynamic class loading is a classic problem. Unlike heap, Metaspace stores class
> metadata, and crucially, classes are not GCed unless their ClassLoader is GCed.
>
> The pattern: each Groovy script compilation creates new classes. If you're creating a new
> GroovyShell or GroovyClassLoader per request without caching, each script evaluation loads new
> classes that are never unloaded.
>
> Diagnosis:
>   jcmd <pid> VM.native_memory summary
>   # Look at: Class space and Metaspace lines
>   # Growing Metaspace with growing class count = ClassLoader leak
>
>   jcmd <pid> VM.classloaders
>   # Shows ClassLoader hierarchy and class counts
>
> Fix path:
>
> 1. Cache compiled scripts — use a WeakHashMap<String, Script> or Caffeine cache
>    keyed by script content hash. Same script = same compiled class = no new ClassLoader.
>
> 2. One shared GroovyShell with script caching
>    GroovyShell is thread-safe for eval if scripts are compiled once
>
> 3. Set a Metaspace limit so OOM happens with a heap dump instead of JVM crash:
>    -XX:MaxMetaspaceSize=512m
>    -XX:+HeapDumpOnOutOfMemoryError
>
> 4. For severe leak, periodic reload of the entire application (circuit breaker for bad scripts)
>
> At 15 years experience: I've seen this exact pattern with Drools rule engines, Velocity templates
> with dynamic compilation, and JOOQ code gen running in-process. The fix is always the same:
> cache the compiled artifact, not just the source."

---

### Scenario 6: Service OOMKills After Memory Leak Fix But Before Restart

**Interviewer:** "We found a memory leak, the fix is ready, but deployment is in 2 hours due to change
freeze. The pod will OOMKill before then. What do you do operationally?"

**Answer:**

> "This is an incident response question as much as a JVM question. Options in order:
>
> 1. Increase pod memory limit temporarily (if you have access):
>    kubectl set resources deployment/myservice --limits=memory=4Gi
>    Buys time, doesn't fix root cause. Document why.
>
> 2. Increase JVM heap headroom if Max < Limit:
>    Check: if limits.memory=4Gi but -Xmx=2g, bump -Xmx=3g via env var, rolling restart
>    This is already a restart, but it's your restart on your schedule, not K8s killing pods randomly
>
> 3. Implement a manual JVM heap dump before it dies:
>    jcmd <pid> GC.heap_dump /dumps/pre-oom.hprof
>    Gives you evidence even if pod dies before the fix
>
> 4. Reduce pod replica count during the window to reduce memory pressure on the cluster overall
>
> 5. If it's a scheduled leak accumulation, trigger a rolling restart just before the OOMKill threshold:
>    A cron job that does a rolling restart every hour is an engineering smell, but it's better than
>    random OOMKills affecting users. Make it explicit that this is a temporary measure.
>
> The answer to 'restart fixes memory issues' is: NO. Restart buys time. Fix eliminates the problem.
> Never let operational workarounds become the permanent solution."

---

### Scenario 7: Kafka Consumer Service with 10-Second GC Pauses

**Interviewer:** "Our Kafka consumer service processes large messages (50-100MB each). We're seeing
10-second GC pauses. The service is running G1GC with -Xmx8g. Help."

**Answer:**

> "Large object allocation with G1GC is a known problem area. G1GC has a concept of 'humongous
> allocations' — objects larger than 50% of a G1 heap region go directly to a humongous region in
> Old Gen, bypassing Young Gen entirely.
>
> With default G1 region size (1-32MB depending on heap), a 50-100MB message allocation could be
> humongous or border-humongous. Humongous objects are collected only during concurrent GC cycles or
> Full GC.
>
> Diagnostic:
>   grep -i 'humongous\|Humongous' /logs/gc.log
>   Look for: 'GC(N) Humongous Allocation' lines
>
> Fix path:
>
> 1. Increase G1 region size to make messages non-humongous:
>    -XX:G1HeapRegionSize=64m
>    With 64m regions, a 50MB object is non-humongous, handled normally
>    Valid values: 1, 2, 4, 8, 16, 32, 64 MB
>
> 2. Avoid materializing full message as single object:
>    Use streaming deserialization (Jackson streaming API) instead of readValue() to POJO
>    Process the message in chunks to avoid one large allocation
>
> 3. If large allocations are unavoidable, consider ZGC:
>    ZGC handles large heaps with <1ms pauses, no humongous region concept
>    -XX:+UseZGC -Xmx8g
>    With ZGC on Java 17+, the 10-second pauses disappear entirely
>
> My recommendation: Combine option 2 (streaming) for the 50-100MB messages with ZGC.
> Streaming reduces peak allocation, ZGC handles what remains concurrently."

---

### Scenario 8: Spring Boot Service Thread Count Growing Unboundedly

**Interviewer:** "jstack shows our service growing from 50 threads at startup to 800+ threads over
several hours. Memory is fine, but response times degrade as threads grow. Root cause?"

**Answer:**

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

---

## 4. Advanced Scenario Q&As

### Advanced 1: ZGC vs Shenandoah — When to Choose Which

**Interviewer:** "Walk me through the differences between ZGC and Shenandoah. When would you pick one
over the other in production?"

**Answer:**

> "Both are low-pause GC algorithms designed to scale to terabyte heaps with sub-millisecond pauses.
> The key differences:
>
> ZGC:
> - Oracle/OpenJDK developed, production-ready from Java 15
> - Handles heaps from 8MB to 16TB
> - All GC work is concurrent (relocation is also concurrent in ZGC Gen since Java 21)
> - Pause times are O(1) — fixed overhead regardless of heap size
> - Generational ZGC (Java 21+): adds generational collection, better throughput than old ZGC
> - CPU overhead: 10-20% higher than G1GC
>
> Shenandoah:
> - Red Hat developed, available in OpenJDK and GraalVM
> - Similar pause profile to ZGC
> - Available in Java 8 (backport) — useful if you're on older Java but need low pause
> - Concurrent compaction phase slightly different algorithm
> - Often slightly higher throughput than old ZGC pre-Java 21
>
> My production decision tree:
>
> - Java 21+ with large heap (8GB+), latency-critical: Use Generational ZGC
>   -XX:+UseZGC -XX:+ZGenerational
>   Best of both worlds: low pauses AND good throughput
>
> - Java 11-17, large heap, latency-critical: ZGC or Shenandoah are comparable
>   Team familiarity/tooling decides
>
> - Java 8 (legacy constraint), low pause needed: Shenandoah backport is your only option
>
> - Oracle JDK constraint (commercial license), Java 17: G1GC with tuning,
>   ZGC available in Oracle JDK from Java 15
>
> In practice I've run ZGC in production on payment processing services — the sub-millisecond pause
> guarantee is transformative for P99 latency SLOs. The CPU cost was worth it at 10% extra."

---

### Advanced 2: GraalVM Native Image — Real Production Trade-offs

**Interviewer:** "Your team wants to migrate all microservices to GraalVM Native Image for faster
startup. Walk me through the trade-offs you'd present."

**Answer:**

> "I'd frame this as a decision matrix, not a blanket recommendation.
>
> Benefits of Native Image:
> - Startup time: 50-500ms vs 10-60 seconds for JVM Spring Boot
> - Peak memory: 100-300MB vs 500MB-2GB for JVM equivalent
> - Instant peak performance: no warm-up, code is AOT compiled
> - Container image size: smaller, no JDK needed at runtime
>
> Costs and risks:
>
> 1. No JIT — peak throughput is 20-40% lower for CPU-intensive code
>    JVM with C2 compilation outperforms native for long-running workloads
>    Your payment processor running 24/7 should NOT be on native image
>
> 2. Reflection is a first-class problem
>    Spring Framework is heavily reflection-based
>    Spring AOT (Spring Boot 3+) generates reflection hints at build time, but:
>    - Dynamic bean registration doesn't work
>    - Some third-party libraries need manual reflection config
>    - Every library upgrade may break the native build
>
> 3. Build time is painful
>    Native image compilation: 3-10 minutes vs 30 seconds for JAR
>    CI/CD pipelines need significant memory (8-16GB for compilation)
>
> 4. No runtime class loading
>    Plugins, scripting engines, dynamic proxies — broken by default
>    Fine for microservices, catastrophic for plugin architectures
>
> 5. JFR and JVM diagnostics limited
>    heap dumps, thread dumps work differently or not at all
>
> My recommendation: Native image for:
> - Serverless/Lambda functions (cold start is everything)
> - CLI tools
> - Event-driven functions with infrequent invocations
>
> Keep JVM for:
> - Long-running microservices (>1hr lifetime)
> - CPU-intensive processing (JIT wins)
> - Services with dynamic/plugin architectures
> - Any service where diagnostics capability is critical"

---

### Advanced 3: Virtual Threads Deep Dive — Pinning and Monitoring

**Interviewer:** "We migrated to Java 21 virtual threads. We're seeing unexpected blocking behavior.
The CPU is at 100% on the carrier threads. What are you looking for?"

**Answer:**

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

---

### Advanced 4: JIT Compilation — When Code Gets SLOWER After Warmup

**Interviewer:** "After about 30 minutes of running, our service starts getting slower, not faster.
CPU gradually increases. Redeployment fixes it temporarily. What JIT phenomenon causes this?"

**Answer:**

> "JIT deoptimization — specifically speculative deoptimization followed by recompilation storms.
>
> JIT compilers make speculative optimizations based on observed behavior. If those assumptions are
> violated, the JIT must deoptimize (fall back to interpreted or C1-compiled version) and then
> recompile with less aggressive assumptions.
>
> Symptoms:
> - Gradual CPU increase over time
> - Periodic bursts of high CPU
> - Performance degrades instead of improving
> - Redeployment (fresh JVM) temporarily fixes it
>
> Common triggers:
>
> 1. Polymorphic call sites
>    JIT optimizes for a single concrete class at a call site.
>    If new concrete types start flowing through that site (e.g., after cache warmup loads different
>    subclasses), JIT deoptimizes and recompiles as megamorphic (no devirtualization).
>    Megamorphic call sites are significantly slower.
>
> 2. Class loading after warmup
>    A plugin loads new classes into a ClassLoader at runtime.
>    JIT's assumptions about class hierarchy are invalidated.
>    Deoptimization cascade can affect many compiled methods.
>
> 3. Code cache exhaustion
>    When ReservedCodeCacheSize is full, the JVM starts flushing compiled code.
>    Methods fall back to interpreted mode until recompiled.
>    The 'compiler is running' symptom: CPU spike + throughput drop.
>
>    Check:
>      jcmd <pid> Compiler.codecache
>      Look for: 'CodeCache is full. Compiler has been disabled.'
>      Fix: -XX:ReservedCodeCacheSize=512m (default 240MB is often not enough for large apps)
>
> 4. On-Stack Replacement (OSR) failures
>    Long-running methods that were optimized with speculative assumptions
>    hit deopt points while executing (mid-method).
>
> Diagnostic:
>   -XX:+PrintCompilation  # Logs compilation events, deoptimizations marked with 'made not entrant'
>   JFR event: jdk.Deoptimization
>     jfr print --events jdk.Deoptimization recording.jfr | head -50"

---

## 5. Senior Trap Questions

### Trap 1: "We should set -Xmx as large as possible to avoid OOM"

**What the interviewer is testing:** Do you understand the relationship between heap size and Full GC?

**Wrong answer:** "Yes, more heap = more headroom = safer."

**Correct answer:**

> "Actually this is one of the most dangerous pieces of advice in JVM tuning. Here's why:
>
> Larger heap = longer Full GC pauses. A Full GC must scan and compact the entire live heap.
> A 2GB heap might pause for 2-5 seconds. A 32GB heap might pause for 30-60 seconds. That's a
> service outage, not a GC pause.
>
> In K8s specifically, setting -Xmx to the container limit or beyond is a guaranteed OOMKill
> recipe. The JVM process RSS includes native memory on top of heap. -Xmx=4g in a 4Gi limit
> container will be OOMKilled because RSS will be 5-6GB.
>
> The right approach: Right-size the heap based on actual working set. Measure what lives in
> Old Gen at steady state (via GC logs or JFR), add buffer, that's your -Xmx.
> Typical production sizing: heap = 50-70% of container memory limit.
>
> For low-latency requirements: Use ZGC or Shenandoah where pause time is independent of
> heap size. Then you can use larger heaps without the Full GC pause risk."

---

### Trap 2: "The JVM uses exactly -Xmx memory, so if -Xmx is 4GB, the process uses 4GB"

**Correct answer:**

> "This is false and has caused many K8s OOMKills in production.
>
> -Xmx controls only the Java heap. The JVM process RSS (Resident Set Size) includes:
>
> - Java Heap: up to -Xmx
> - Metaspace: class metadata, ~100-500MB for typical Spring Boot app
> - Code Cache: JIT-compiled code, default 240MB reserved
> - Thread stacks: each thread = 256KB-1MB, 100 threads = 25-100MB
> - Direct Buffers: NIO/Netty off-heap buffers, can be 100s of MB
> - GC overhead: G1GC keeps internal data structures, ~1-2% of heap
> - JVM overhead: shared libraries, JVM internals ~50-100MB
>
> Real world: -Xmx=4g → RSS typically 5.0-5.5GB
>
> For K8s sizing:
>   container_memory_limit = -Xmx / 0.75
>   OR
>   Use -XX:MaxRAMPercentage=75.0 and let JVM calculate heap from container limit
>
> To measure actual native memory:
>   -XX:NativeMemoryTracking=summary
>   jcmd <pid> VM.native_memory summary"

---

### Trap 3: "Restarting the service fixed our memory issue, so we're good"

**Correct answer:**

> "Restart hides the problem, it doesn't fix it. In 15 years I've seen this 'fix' come back to bite
> teams repeatedly.
>
> A service that needs periodic restarts for memory reasons has one of:
> 1. A memory leak (heap: object lifecycle bug; native: resource not freed)
> 2. Unbounded caches or state accumulation
> 3. Connection pool or thread pool leak
>
> The restart cadence will accelerate over time as the leak gets worse with load.
>
> Worse: restart-as-mitigation encourages teams to not fix the root cause. I've seen services
> with scheduled cron restarts running for years in production, accumulating technical debt.
>
> The engineering response to a memory issue:
> 1. Capture a heap dump before restart (jcmd GC.heap_dump, -XX:+HeapDumpOnOutOfMemoryError)
> 2. Analyze with Eclipse MAT or JProfiler
> 3. Find the leak, fix it, add a regression test
> 4. Add memory usage alerts so you catch it early next time
>
> A scheduled restart is acceptable only as a temporary measure with a ticket tracking the root
> cause fix and a deadline."

---

### Trap 4: "More JVM threads means more concurrency and better throughput"

**Correct answer:**

> "This is true for CPU-bound work and false for I/O-bound work, which is most of what Java
> microservices do.
>
> For I/O-bound work (HTTP calls, DB queries, Kafka, file I/O):
> - The thread is blocked waiting for I/O most of the time
> - Adding more threads beyond CPU count doesn't help — they're all blocked
> - More platform threads = more memory (each is ~1MB stack)
> - More threads = more context switching overhead
> - More threads = more lock contention on shared resources
>
> Evidence: A Tomcat service with 200 threads handling 200 concurrent requests, each doing
> a 100ms DB query. You might expect 2000 RPS. Reality: threads block, CPU switches between them,
> you get maybe 200 concurrent in-flight but the CPU is 30% context-switch overhead.
>
> Modern correct answer:
>
> For async non-blocking (Spring WebFlux, Vert.x): 
>   Use small thread pool (CPU count * 2), never block, reactive chains.
>   Handles 10,000+ concurrent requests with 16 threads.
>
> For virtual threads (Java 21):
>   Use unlimited virtual threads, never explicitly pool them.
>   spring.threads.virtual.enabled=true
>   Virtual threads are cheap (KB, not MB), block without holding OS threads.
>   Same programming model as blocking code, none of the thread pool constraints.
>
> Rule: Platform threads for CPU-bound work. Virtual threads or async for I/O-bound work."

---

### Trap 5: "Default JVM flags are good enough for production"

**Correct answer:**

> "JVM ergonomic defaults are designed for development workloads and desktop applications.
> They're conservative and will fail you in production in several predictable ways.
>
> What the defaults get wrong:
>
> 1. Heap sizing: default max heap = 25% of physical RAM on host.
>    In a K8s container with 4GB limit, JVM sees HOST memory (say 64GB) and sets -Xmx=16GB.
>    Without UseContainerSupport or explicit Xmx, you immediately OOMKill.
>    (Thankfully UseContainerSupport is default from Java 8u191+, but explicit is better.)
>
> 2. GC logging: disabled by default.
>    When you have a production incident, you have no GC evidence.
>    Always add: -Xlog:gc*:file=/logs/gc.log:time,uptime:filecount=5,filesize=20m
>
> 3. Heap dump: disabled by default.
>    When OOM happens, you get a stack trace but no heap dump.
>    Always add: -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps/
>
> 4. OOM behavior: by default JVM logs the error and tries to continue.
>    A JVM in OOM state is thrashing, not serving requests.
>    Add: -XX:+ExitOnOutOfMemoryError
>
> 5. Code cache: default 240MB, often not enough for Spring Boot + libraries.
>    Code cache full = JIT disabled = severe performance degradation.
>    Add: -XX:ReservedCodeCacheSize=512m
>
> Minimum production flag set is 8-12 flags beyond defaults."

---

### Trap 6: "G1GC always performs better than Parallel GC because it's newer"

**Correct answer:**

> "G1GC is the better default for most workloads, but Parallel GC is still superior for
> specific scenarios. 'Newer' does not mean 'always better.'
>
> Parallel GC wins when:
> 1. Batch processing jobs: You're processing 100GB of data, and you don't have users waiting.
>    You want maximum throughput, and pause times are irrelevant.
>    Parallel GC dedicates all GC threads to stop-the-world collection = higher throughput.
>
> 2. Simple heaps: If your service has simple object lifecycle (allocate, process, discard),
>    no long-lived objects, Parallel GC's simple generational approach is very efficient.
>    G1GC's complexity adds overhead for simple workloads.
>
> 3. Small heaps (<2GB): G1GC's region-based approach adds overhead below certain heap sizes.
>    For small heaps, Parallel GC or even Serial GC is more efficient.
>
> G1GC wins when:
> - Mixed workloads with both short-lived and long-lived objects
> - Latency matters (G1GC can target pause times with MaxGCPauseMillis)
> - Large heaps (4GB+) where Parallel GC pauses become unacceptable
> - Services with SLAs or user-facing latency requirements
>
> Example production scenario where I used Parallel GC:
> Nightly ETL job processing 50GB of customer records, runs from 2am-4am,
> no users affected by pauses, needs maximum throughput.
> Parallel GC with -XX:ParallelGCThreads=16 was 25% faster than G1GC for this workload."

---

## 6. JVM Flag Configurations — Real Production Configs

### Config 1: Spring Boot REST API, 4GB Container, Latency-Sensitive

```bash
JAVA_OPTS="\
  -server \
  -XX:+UseG1GC \
  -Xms2g -Xmx2g \
  -XX:MaxGCPauseMillis=100 \
  -XX:G1HeapRegionSize=16m \
  -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=/dumps/heap.hprof \
  -XX:+ExitOnOutOfMemoryError \
  -Xlog:gc*:file=/logs/gc.log:time,uptime,level,tags:filecount=5,filesize=20m \
  -XX:ReservedCodeCacheSize=512m \
  -XX:MaxMetaspaceSize=512m"
```

---

### Config 2: K8s Container with Dynamic Memory Limits

```bash
# Use percentage-based sizing — survives resource limit changes
JAVA_OPTS="\
  -server \
  -XX:+UseContainerSupport \
  -XX:MaxRAMPercentage=75.0 \
  -XX:InitialRAMPercentage=75.0 \
  -XX:+UseG1GC \
  -XX:MaxGCPauseMillis=200 \
  -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=/dumps/ \
  -XX:+ExitOnOutOfMemoryError \
  -Xlog:gc*:file=/logs/gc.log:time,uptime:filecount=3,filesize=10m"
```

---

### Config 3: Low-Latency Service (Payments/Trading), 8GB Container

```bash
# ZGC for <1ms pauses
JAVA_OPTS="\
  -server \
  -XX:+UseZGC \
  -XX:+ZGenerational \
  -Xms6g -Xmx6g \
  -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=/dumps/ \
  -XX:+ExitOnOutOfMemoryError \
  -Xlog:gc*:file=/logs/gc.log:time,uptime:filecount=5,filesize=20m \
  -XX:ReservedCodeCacheSize=512m \
  -XX:MaxMetaspaceSize=512m \
  -XX:+UnlockDiagnosticVMOptions"
# Note: No MaxGCPauseMillis for ZGC - it manages pause times internally
# ZGC Java 21+ with ZGenerational for best throughput+latency combo
```

---

### Config 4: Batch/ETL Job, Maximum Throughput

```bash
# Parallel GC for batch — accept pauses, maximize throughput
JAVA_OPTS="\
  -server \
  -XX:+UseParallelGC \
  -Xms8g -Xmx8g \
  -XX:ParallelGCThreads=8 \
  -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=/dumps/ \
  -Xlog:gc*:file=/logs/gc.log:time,uptime:filecount=3,filesize=20m \
  -XX:MaxMetaspaceSize=256m"
# No ExitOnOOM for batch — we want heap dump, not immediate exit
# No ReservedCodeCacheSize bump needed — batch runs, compiles once, finishes
```

---

### Config 5: Memory Leak Investigation — Diagnostic Mode

```bash
# Enable all diagnostics — NOT for production baseline (overhead)
JAVA_OPTS="\
  -server \
  -XX:+UseG1GC \
  -Xms2g -Xmx2g \
  -XX:NativeMemoryTracking=detail \
  -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=/dumps/ \
  -Xlog:gc*:file=/logs/gc.log:time,uptime,level,tags:filecount=10,filesize=50m \
  -XX:+UnlockDiagnosticVMOptions \
  -XX:+PrintNMTStatistics \
  -Djdk.attach.allowAttachSelf=true"
# After startup:
# jcmd <pid> VM.native_memory summary
# jcmd <pid> VM.native_memory baseline
# [after some time under load]
# jcmd <pid> VM.native_memory summary.diff
```

---

### Config 6: Java 21 with Virtual Threads

```bash
# Virtual threads + ZGC for high-concurrency HTTP service
JAVA_OPTS="\
  -server \
  -XX:+UseZGC \
  -XX:+ZGenerational \
  -Xms4g -Xmx4g \
  -Djdk.virtualThreadScheduler.parallelism=16 \
  -Djdk.tracePinnedThreads=short \
  -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=/dumps/ \
  -XX:+ExitOnOutOfMemoryError \
  -Xlog:gc*:file=/logs/gc.log:time,uptime:filecount=5,filesize=20m"
# Spring Boot 3.2+ add to application.properties:
#   spring.threads.virtual.enabled=true
# Remove: all Tomcat/Jetty max-threads tuning — virtual threads make it irrelevant
```

---

### Config 7: Class Data Sharing (CDS) — Faster Startup

```bash
# Step 1: Generate shared archive (in Dockerfile or init container)
java -Xshare:dump \
  -XX:SharedArchiveFile=/app/app.jsa \
  -cp /app/app.jar \
  -Xlog:class+load:file=/tmp/cds-dump.log

# Step 2: Production startup with archive
JAVA_OPTS="\
  -server \
  -XX:+UseG1GC \
  -Xms2g -Xmx2g \
  -Xshare:on \
  -XX:SharedArchiveFile=/app/app.jsa \
  -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=/dumps/"
# Benefit: ~20-40% faster startup, lower memory with multiple JVM instances sharing archive
```

---

## 7. Interview Cheat Sheet

### Heap Sizing Quick Reference

| Container Memory | Heap (-Xmx)  | Ratio | Notes                              |
|-----------------|--------------|-------|------------------------------------|
| 1GB             | 512m         | 50%   | Small service, tight container     |
| 2GB             | 1200m        | 60%   | Typical microservice               |
| 4GB             | 2g-3g        | 60-75%| Most Spring Boot production setups |
| 8GB             | 5g-6g        | 65-75%| Larger services, G1GC or ZGC       |
| 16GB+           | 10g-12g      | 65-75%| Consider ZGC for low pause         |
| Container-aware | MaxRAMPercentage=75 | 75% | Best practice, survives limit changes |

---

### GC Algorithm Quick Reference

| Algorithm   | When to Use                  | Pause Profile         | Java Version | Overhead     |
|-------------|------------------------------|-----------------------|--------------|--------------|
| Serial GC   | <256MB heaps, single CPU     | Stop-the-world        | All          | Lowest       |
| Parallel GC | Batch jobs, max throughput   | Stop-the-world        | All          | Low          |
| G1GC        | Default REST/web services    | <200ms target         | 9+ (default) | Moderate     |
| ZGC         | Latency-critical, 8GB+       | <1ms                  | 15+ prod     | 10-20% CPU   |
| Shenandoah  | Like ZGC, OpenJDK            | <1ms                  | 12+          | Similar ZGC  |
| Gen ZGC     | Best overall Java 21+        | <1ms + better throughput | 21+       | Moderate     |

---

### JVM Memory Regions Quick Reference

| Region          | Controlled By              | Default Limit     | What Lives There        |
|-----------------|---------------------------|-------------------|-------------------------|
| Heap Young      | -Xms/-Xmx, G1 ratios      | Up to -Xmx        | New objects             |
| Heap Old        | -Xms/-Xmx                 | Up to -Xmx        | Long-lived objects      |
| Metaspace       | -XX:MaxMetaspaceSize      | Unlimited (danger!)| Class metadata          |
| Code Cache      | -XX:ReservedCodeCacheSize | 240MB             | JIT compiled code       |
| Thread Stacks   | -Xss per thread           | 512KB-1MB/thread  | Call stacks             |
| Direct Buffers  | -XX:MaxDirectMemorySize   | == -Xmx           | NIO/Netty off-heap      |

---

### One-Liner Diagnostics Reference

```bash
# Check JVM process memory breakdown
jcmd <pid> VM.native_memory summary

# Check GC summary
jcmd <pid> GC.heap_info

# Generate heap dump manually
jcmd <pid> GC.heap_dump /tmp/heap.hprof

# Check thread count and states
jcmd <pid> Thread.print | grep 'java.lang.Thread.State' | sort | uniq -c

# Check code cache
jcmd <pid> Compiler.codecache

# List all JVM flags in effect (includes ergonomic defaults!)
jcmd <pid> VM.flags

# JFR start recording
jcmd <pid> JFR.start duration=60s filename=/tmp/recording.jfr

# Check if container support is working
jcmd <pid> VM.flags | grep -i container
# Should see: UseContainerSupport=true
```

---

### Key Numbers to Remember in Interviews

```
Native memory overhead above -Xmx:    20-30%
G1GC typical pause:                   50-200ms
ZGC pause target:                     <1ms
ZGC CPU overhead vs G1GC:             10-20%
Platform thread stack size:           256KB - 1MB (default 512KB)
Virtual thread stack:                 ~KB (grows on demand)
JVM warm-up to peak performance:      2-5 minutes
CDS startup improvement:              20-40%
GraalVM native startup:               50-500ms (vs 10-60s JVM)
GraalVM native peak throughput loss:  20-40% vs JVM C2
Default code cache size:              240MB (often not enough for Spring Boot)
G1GC humongous threshold:             50% of region size
Default G1 region size:               1-32MB (depends on heap, auto-calculated)
Metaspace default:                    Unlimited (always set MaxMetaspaceSize!)
```

---

### Flag Flags: What to Always Set in Production

```bash
# Never skip these in production Spring Boot:
-Xms == -Xmx                          # Prevent heap resize pauses
-XX:+HeapDumpOnOutOfMemoryError        # Evidence for OOM debugging
-XX:HeapDumpPath=/dumps/               # Where to write dump
-XX:+ExitOnOutOfMemoryError            # Fail fast, let K8s restart
-Xlog:gc*:file=/logs/gc.log:...        # GC evidence for incident investigation
-XX:MaxMetaspaceSize=512m              # Prevent unbounded metaspace growth
-XX:ReservedCodeCacheSize=512m         # Prevent JIT starvation

# In K8s, always use one of:
-XX:+UseContainerSupport               # Default Java 8u191+, but be explicit
-XX:MaxRAMPercentage=75.0              # Better than hardcoded -Xmx in containers
```

---

### The 5-Minute Incident Response Checklist

```
1. Is it a GC issue?
   grep 'Pause Full\|GC overhead' /logs/gc.log | tail -20

2. Is it a memory issue?
   jcmd <pid> GC.heap_info
   jcmd <pid> VM.native_memory summary

3. Is it a thread issue?
   jcmd <pid> Thread.print > /tmp/threads.txt
   grep 'BLOCKED\|WAITING' /tmp/threads.txt | wc -l

4. Is it a CPU issue?
   top -H -p <pid>   # Show JVM threads
   jcmd <pid> Compiler.codecache   # Code cache full?

5. Start a JFR recording immediately for ongoing issues
   jcmd <pid> JFR.start duration=300s filename=/tmp/incident.jfr
```

---

### Common Mistakes Architects Make (And How to Avoid Them)

| Mistake                                      | Why Wrong                                | Correct Approach                          |
|----------------------------------------------|------------------------------------------|-------------------------------------------|
| -Xmx = container limit                       | Native overhead causes OOMKill           | -Xmx = 70-75% of container limit         |
| -Xms much smaller than -Xmx                  | Heap resize pauses                       | Set -Xms = -Xmx                           |
| No MaxMetaspaceSize                           | Unbounded class metadata growth          | Always set -XX:MaxMetaspaceSize=512m      |
| No GC logging                                | No evidence during incidents             | Always enable -Xlog:gc*                   |
| No heap dump on OOM                          | Can't diagnose OOM cause                 | Always set HeapDumpOnOutOfMemoryError      |
| 500+ platform threads for I/O workloads      | Memory waste, context switching          | Virtual threads (Java 21) or async        |
| Default code cache (240MB) for Spring Boot   | JIT disabled when full                   | -XX:ReservedCodeCacheSize=512m            |
| UseZGC without checking CPU budget           | 10-20% CPU overhead may blow budget      | Measure CPU impact in staging             |
| GraalVM native for everything                | No JIT = lower peak throughput           | Native for short-lived, JVM for sustained |
| Restart as the memory leak fix               | Masks bug, accelerates over time         | Heap dump → analyze → fix → test          |

---

*Last updated: 2026 — covers Java 8 through Java 21 LTS*
*Flags syntax: Java 9+ Unified Logging (-Xlog) used throughout*
*Target audience: Principal/Staff Java Architect, 10-15+ YOE interview level*
