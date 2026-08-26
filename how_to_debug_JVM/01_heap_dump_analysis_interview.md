# JVM Heap Dump Analysis & OOM Debugging — 15-YOE Architect Interview Prep

> Target: Staff/Principal Engineer / Java Architect rounds. Covers production debugging workflow end-to-end.

---

## 1. Big Picture — JVM Heap Layout & OOM Trigger Points

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              JVM MEMORY MAP                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   HEAP (-Xms / -Xmx)                                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │  YOUNG GENERATION                      │  OLD GENERATION (Tenured)     │     │
│  │  ┌──────────┬───────────┬───────────┐  │  ┌───────────────────────┐   │     │
│  │  │          │           │           │  │  │                       │   │     │
│  │  │  Eden    │ Survivor0 │ Survivor1 │  │  │  Long-lived objects   │   │     │
│  │  │  Space   │  (S0/From)│  (S1/To)  │  │  │  promoted from Young  │   │     │
│  │  │          │           │           │  │  │                       │   │     │
│  │  │ ~80%     │  ~10%     │  ~10%     │  │  │  OOM: Heap space      │   │     │
│  │  │ of Young │  of Young │  of Young │  │  │  OOM: GC overhead     │   │     │
│  │  │          │           │           │  │  │       limit exceeded  │   │     │
│  │  └──────────┴───────────┴───────────┘  │  └───────────────────────┘   │     │
│  │        OOM: "Java heap space"           │                               │     │
│  │        (allocation fails in Eden)       │                               │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                                                                 │
│   METASPACE (off-heap, -XX:MaxMetaspaceSize)                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │  Class metadata, method bytecode, static fields (refs only)            │     │
│  │  Grows dynamically. OOM: "Metaspace" — classloader leak!               │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                                                                 │
│   DIRECT MEMORY (-XX:MaxDirectMemorySize, default = -Xmx)                       │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │  ByteBuffer.allocateDirect(), Netty ByteBuf (off-heap pooled)          │     │
│  │  OOM: "Direct buffer memory" — Netty leak, NIO leak                    │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                                                                 │
│   THREAD STACKS (per-thread, -Xss)                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │  Each thread ~512KB–1MB. OOM: "unable to create new native thread"     │     │
│  │  Cause: OS ulimit, too many threads spawned (thread leak)              │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
│                                                                                 │
│   CODE CACHE (-XX:ReservedCodeCacheSize)                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐     │
│  │  JIT-compiled native code. Full = JIT disabled, performance cliff      │     │
│  └────────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────────┘

OOM DECISION TREE:
─────────────────
"java.lang.OutOfMemoryError: Java heap space"
        └─► Heap exhausted. Check: unclosed resources, cache growth, object retention

"java.lang.OutOfMemoryError: GC overhead limit exceeded"
        └─► JVM spending >98% time GC-ing but recovering <2% heap. Effectively a heap leak.

"java.lang.OutOfMemoryError: Metaspace"
        └─► Class metadata full. Check: classloader leak, CGLIB proxy explosion, hot deploy

"java.lang.OutOfMemoryError: Direct buffer memory"
        └─► Off-heap ByteBuffers not released. Check: Netty handlers, NIO channels

"java.lang.OutOfMemoryError: unable to create new native thread"
        └─► OS out of threads. Check: thread leak, OS ulimit -u

"java.lang.OutOfMemoryError: Compressed class space"
        └─► Sub-area of Metaspace (klass pointers). Same fix as Metaspace.
```

---

## 2. Conversational Interview Script — The Real Incident Narrative

> Practice reading this aloud. Interviewers at senior levels want a *story*, not a textbook.

---

### Opening (when asked "Tell me about a production OOM you debugged")

**You say:**

"Sure. This was about three years ago at [company], running a Spring Boot 2.x service behind an API gateway — roughly 40 million requests per day. One Friday evening at about 9 PM we got a PagerDuty alert: heap usage climbing past 90% and response latency spiking. By 9:15 the pod OOM-killed itself and Kubernetes restarted it. We had about 20 minutes before the next OOM.

My first instinct was *not* to just raise the heap. I've seen that pattern before — you buy yourself 20 minutes instead of 10, but the root cause is still there. So I started with two parallel tracks: capture evidence before the next crash, and simultaneously look at what changed in that day's deploy."

---

### Act 1 — Capturing the Heap Dump Before It Dies

**You say:**

"We already had `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps/heapdump.hprof` in the JVM flags. That's table stakes — every production service should have this. But the pod had already restarted, so the dump from the previous crash was in the dead pod's ephemeral filesystem — gone.

For the *next* crash, I did two things. First, I exec'd into the running pod and ran:

```bash
# Get the PID
jcmd

# Trigger heap dump manually while the process was still alive but stressed
jcmd <pid> GC.heap_dump /tmp/heap_before_oom.hprof
```

Why `jcmd` over `jmap`? Because `jmap -dump` does a full heap walk which *can* trigger a Full GC pause and actually cause an OOM mid-dump if you're already close to the limit. `jcmd GC.heap_dump` is safer — it still pauses but with better safety guards. I'll come back to `jmap` risks in a second.

Second, I added a liveness probe that would write a dump on a specific signal — but that was for the next sprint."

---

### Act 2 — Initial Triage with the Histogram

**You say:**

"The dump was about 3.2 GB. I opened it in Eclipse MAT — Memory Analyzer Tool. The very first thing I look at is the **Dominator Tree**, not the Leak Suspects report. Why? Because Leak Suspects is a heuristic — it's a good starting point, but I want to see the raw dominance relationships.

The dominator tree showed one object retaining 2.1 GB out of 3.2 GB heap — a `java.util.LinkedHashMap` inside a custom in-memory cache class. The shallow heap of that map was tiny — a few hundred bytes. The **retained heap** was 2.1 GB. That's the key distinction: retained heap is what *would be freed* if that object were garbage collected. Shallow heap is just the object header + its direct fields.

So I looked at the GC root path to that object. MAT's 'Path to GC Roots' showed it was reachable from a `static` field in a class called `ResponseCacheManager`. Someone had introduced an unbounded static `LinkedHashMap` as a response cache. No eviction policy, no size limit. Every unique request URL was a cache key. After 8 hours of traffic, that was 40 million entries."

---

### Act 3 — Fix, Verify, Post-Mortem

**You say:**

"The fix was straightforward — replace the unbounded map with a Caffeine cache with explicit size and TTL bounds. But the verification step is just as important as the fix. We:

1. Added a Micrometer gauge metric on cache size
2. Added a JVM GC pause metric alert if Old Gen collection frequency exceeded threshold
3. Ran a load test at 2x production traffic in staging — confirmed heap stabilized below 60%
4. Did a canary deploy to 5% of production pods, watched memory trend for 30 minutes before full rollout

And in the post-mortem — the real issue was process: the cache class was introduced without a mandatory review of unbounded data structures. We added that to our PR checklist."

---

## 3. Scenario Q&As — Production Incidents

---

### Scenario 1: Heap Space OOM in a Spring Boot REST API

**Q: Your Spring Boot service is OOM-killing every 4–6 hours with "Java heap space." Heap is 4 GB. How do you approach this?**

**A:**

Step 1 — Gather evidence without guessing.
```bash
# Confirm OOM type in logs
grep "OutOfMemoryError" /var/log/app/app.log | tail -20

# Check if heap dump was auto-captured
ls -lh /dumps/*.hprof

# If no auto-dump, enable it for next crash
# JVM flag: -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps/
```

Step 2 — Look at GC logs before heap dump (faster signal).
```bash
# If GC logging enabled:
# -Xlog:gc*:file=/logs/gc.log:time,level,tags:filecount=5,filesize=20m
grep "Pause Full" /logs/gc.log | awk '{print $1, $NF}' | tail -30
```
A pattern of increasing Full GC frequency with decreasing space reclaimed = leak.

Step 3 — Open heap dump in MAT.
- Dominator Tree: What single object retains the most heap?
- Check GC root path: Is it reachable via static field, thread-local, classloader?
- Look at object counts histogram: Do you see millions of unexpected objects (String, byte[], char[])?

Step 4 — Common Spring Boot culprits to check:
- `@Cacheable` without `maxSize` or TTL
- Hibernate `Session` objects not closed (OSIV - Open Session In View anti-pattern)
- `HttpClient` / `RestTemplate` connection pool misconfiguration causing response body not consumed
- `ThreadLocal` set but never `remove()`d in thread pool threads

Step 5 — Fix, add metric, verify under load.

---

### Scenario 2: GC Overhead Limit Exceeded

**Q: You see "GC overhead limit exceeded" — same as heap space OOM?**

**A:** Mechanically different trigger, same root cause category.

The JVM throws this when it spends more than 98% of CPU time on GC and recovers less than 2% of heap across the last 5 consecutive Full GCs. The default thresholds are `-XX:GCTimeLimit=98 -XX:GCHeapFreeLimit=2`.

This often surfaces *before* raw heap exhaustion. The process is technically alive but effectively frozen — every thread is blocked waiting for GC to complete.

Diagnosis:
```bash
# Check GC log for "GC overhead" trigger vs heap exhaustion
grep -i "overhead\|OutOfMemory" /logs/gc.log

# Use jstat to watch live GC behavior (safer than heap dump capture)
jstat -gcutil <pid> 1000 60
# Columns: S0 S1 E(den) O(ld) M(etaspace) YGC YGCT FGC FGCT GCT
# Watch: FGC climbing fast, O column near 100% = Old Gen full, leak confirmed
```

Fix approach: Same as heap space OOM — find the retention root. Do NOT just add `-XX:-UseGCOverheadLimit` to suppress the error; that hides the symptom, not the cause.

---

### Scenario 3: Metaspace OOM — Classloader Leak

**Q: "java.lang.OutOfMemoryError: Metaspace" in a long-running Spring Boot app after multiple hot reloads (dev environment) and also happening in production after several days. What's happening?**

**A:**

This is a classloader leak. Every time a new classloader loads classes into Metaspace, the metadata is retained until that classloader itself becomes unreachable and gets GC'd. If something strong-references the classloader (or any class it loaded), Metaspace grows forever.

Production patterns:
- **Dynamic class generation**: CGLIB proxies, Spring AOP, Hibernate bytecode enhancement. Each redeploy in an OSGi container or app server creates new classloaders.
- **JDBC driver registration**: `DriverManager` holds static references to `Driver` objects loaded by webapp classloaders — classic Tomcat leak.
- **Groovy/Script engines**: Each `GroovyClassLoader.parseClass()` in a loop generates a new class.
- **Reflections library**: Scanning classpath at runtime can generate and retain synthetic classes.

Diagnosis:
```bash
# Watch Metaspace live
jstat -gcmetacapacity <pid> 2000 30
# MCMN(min) MCMX(max) MC(current committed) CCSMN CCSMX CCSC — watch MC climbing

# Count class count
jcmd <pid> VM.class_histogram | head -50

# Enable classloader leak diagnostic
# JVM flag: -XX:+TraceClassLoading -XX:+TraceClassUnloading (verbose, dev only)
```

MAT analysis for Metaspace leak:
- Open dump → Window → Heap Dump Details → Class Loaders
- Look for hundreds/thousands of classloader instances of the same type

Fix:
```java
// Wrong — leaks Groovy classes in Metaspace
GroovyShell shell = new GroovyShell();
Script script = shell.parse(scriptSource); // New class per parse call in loop

// Correct — cache compiled scripts, reuse classloader
// Use GroovyScriptEngine or cache Script objects keyed by hash of source
```

---

### Scenario 4: Direct Buffer Memory OOM — Netty Leak

**Q: "OutOfMemoryError: Direct buffer memory" in a Netty-based microservice. How do you debug this?**

**A:**

Netty uses off-heap pooled byte buffers (`PooledByteBufAllocator`). Every buffer acquired via `ctx.alloc().buffer()` must be explicitly released. Unlike Java heap objects, these are not GC'd — they're ref-counted.

```java
// Leaking pattern — handler forgets to release
@Override
public void channelRead(ChannelHandlerContext ctx, Object msg) {
    ByteBuf buf = (ByteBuf) msg;
    // Process buf...
    // BUG: missing buf.release() — direct memory never freed
}

// Correct
@Override
public void channelRead(ChannelHandlerContext ctx, Object msg) {
    ByteBuf buf = (ByteBuf) msg;
    try {
        processBuffer(buf);
    } finally {
        buf.release(); // Or use ReferenceCountUtil.release(msg)
    }
}
```

Diagnosis steps:
```bash
# 1. Enable Netty leak detection (resource intensive — use in staging)
# JVM flag: -Dio.netty.leakDetection.level=PARANOID (or SIMPLE for prod)
# Netty will log: "LEAK: ByteBuf.release() was not called before it's garbage-collected"

# 2. Monitor direct memory usage
jcmd <pid> VM.native_memory summary | grep -A5 "Internal"

# 3. Check direct buffer allocation via JMX
# java.nio:type=BufferPool,name=direct → MemoryUsed

# 4. Heap dump - look for Netty internal allocator state
# MAT: search for io.netty.buffer.PoolArena instances, check chunkList sizes
```

Sizing fix (not the root fix — just buys time):
```bash
# Increase direct memory budget
-XX:MaxDirectMemorySize=2g
```

---

### Scenario 5: Unable to Create Native Thread

**Q: "OutOfMemoryError: unable to create new native thread" — is this a heap problem?**

**A:** No — this is an OS-level resource exhaustion, not heap. The JVM cannot create a new OS thread. Two root causes:

1. **Too many threads** — thread pool misconfigured, thread leak, virtual thread misconfiguration in Java 21
2. **OS ulimit too low** — `ulimit -u` (max user processes) or `/proc/sys/kernel/threads-max`

Diagnosis:
```bash
# Count current threads in the JVM process
jcmd <pid> Thread.print | grep "^\"" | wc -l

# Or via /proc
ls /proc/<pid>/task | wc -l

# Check OS limit
ulimit -u
cat /proc/sys/kernel/threads-max

# Thread dump to identify what threads are doing
jcmd <pid> Thread.print > /tmp/threaddump.txt
# Look for patterns: hundreds of threads in WAITING state on the same lock/queue
```

Common thread leak patterns:
```java
// Thread leak — new thread per request
@PostMapping("/process")
public ResponseEntity<?> process(@RequestBody Request req) {
    new Thread(() -> doWork(req)).start(); // Never pooled, never joins
    return ResponseEntity.ok().build();
}

// Fix — use bounded executor
@Autowired
private ThreadPoolTaskExecutor taskExecutor; // Configured with max pool size

@PostMapping("/process")
public ResponseEntity<?> process(@RequestBody Request req) {
    taskExecutor.execute(() -> doWork(req));
    return ResponseEntity.ok().build();
}
```

---

### Scenario 6: Hibernate / OSIV Memory Accumulation

**Q: Spring Boot app with JPA — heap grows steadily over the course of a day but never OOMs. Restarts fix it temporarily. What do you suspect?**

**A:** Classic Open Session In View (OSIV) + large entity graph accumulation pattern.

When `spring.jpa.open-in-view=true` (the Spring Boot default), the Hibernate `Session` is held open for the entire HTTP request lifecycle. If:
- You load large entity graphs
- You trigger lazy loading across the entire request chain
- You're using a second-level cache without eviction

...then the Session accumulates objects, and if sessions are pooled or cached beyond request scope, the objects stay referenced.

Diagnosis in heap dump:
- MAT histogram: Look for high count of `org.hibernate.engine.spi.EntityKey` or `org.hibernate.internal.SessionImpl` objects
- Check retention path: Are `SessionImpl` instances reachable from a long-lived scope (application scope, static field, thread-local)?

```java
// Check Spring config
// application.properties
spring.jpa.open-in-view=false  // Correct for APIs — close session at service layer

// Service layer — explicit transaction boundary
@Transactional(readOnly = true)
public List<OrderDTO> getOrders(Long userId) {
    List<Order> orders = orderRepo.findByUserId(userId);
    return orders.stream().map(OrderDTO::from).collect(toList()); // Convert inside tx
    // Session closes when @Transactional method exits
}
```

---

### Scenario 7: Static Collection Grows Without Bound

**Q: Walk me through diagnosing an unbounded static collection causing OOM.**

**A:**

```java
// The bug — seen in "quick fix" caches
public class RequestTracker {
    // BUG: Never evicted, grows forever with unique request IDs
    private static final Map<String, RequestMetadata> activeRequests =
        new ConcurrentHashMap<>();

    public static void track(String requestId, RequestMetadata meta) {
        activeRequests.put(requestId, meta);
    }

    // Missing: removal on request completion
}
```

MAT diagnosis:
1. Dominator Tree → find the large `ConcurrentHashMap$Node[]` array
2. Right-click → "Path to GC Roots" → exclude weak/soft/phantom refs
3. Path will show: `ConcurrentHashMap` → `RequestTracker.activeRequests` (static field) → `RequestTracker.class` → classloader → GC root
4. The static field is the GC root anchor — that's your leak

Fix:
```java
// Correct — bounded with automatic eviction
private static final Cache<String, RequestMetadata> activeRequests =
    Caffeine.newBuilder()
        .maximumSize(10_000)
        .expireAfterWrite(Duration.ofMinutes(5))
        .recordStats()
        .build();
```

---

### Scenario 8: HTTP Client Connection Pool + Response Body Leak

**Q: OOM on a service that calls 5 downstream APIs. Heap dump shows millions of byte[] objects. No obvious static collection. What do you look for?**

**A:**

When using `RestTemplate`, `HttpClient`, or `WebClient`, if the response body is not fully consumed and closed, the connection cannot be returned to the pool. The `InputStream` backing the response body holds a reference to the buffer.

```java
// Leaking — response not closed
public String fetchData(String url) {
    ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
    if (response.getStatusCode() != HttpStatus.OK) {
        // BUG: early return without consuming body
        return null;
    }
    return response.getBody();
}

// Fix with WebClient — reactive, handles backpressure
public Mono<String> fetchData(String url) {
    return webClient.get()
        .uri(url)
        .retrieve()
        .bodyToMono(String.class)
        .onErrorResume(e -> Mono.empty()); // Always terminates the stream
}
```

Diagnosis in heap dump:
- MAT histogram → look for high count of `byte[]` → check the dominator
- Filter by `sun.net.www.http.KeepAliveStream` or `org.apache.http.impl.io.SessionInputBufferImpl`
- These are the buffers held by unconsumed response bodies

---

## 4. Advanced Scenario Q&As

---

### Advanced 1: Multiple Pods OOM-Killing Simultaneously — Kubernetes

**Q: All 8 pods of a service OOM-kill within 2 minutes of each other every day at 2 AM. What's happening and how do you debug it?**

**A:**

The simultaneous pattern rules out a gradual per-pod leak. This is a scheduled load event. Likely candidates:
1. A nightly batch job triggering this service (cron job, scheduled task)
2. A scheduled `@Scheduled` method in the service itself
3. Report generation / cache warm-up that creates large temporary objects

Investigation:
```bash
# Check scheduled tasks in codebase
grep -r "@Scheduled\|@Cron\|quartz\|scheduler" src/ --include="*.java"

# Check upstream call patterns — did request rate spike at 2 AM?
# Query Prometheus/Grafana: rate(http_server_requests_total[1m]) at 02:00

# Enable JVM GC logging and compare 2 AM vs normal hours
# -Xlog:gc*:file=/logs/gc.log:time,level,tags:filecount=10,filesize=50m

# Heap profiling with async-profiler (allocation profiler) for 5 min at 2 AM
./profiler.sh -e alloc -d 300 -f /tmp/alloc.html <pid>
# Shows call stack that allocated the most bytes — pinpoints the code path
```

Common cause: A batch endpoint loads entire DB table into a `List<Entity>`, processes in-memory, holds the list in scope for the full duration. At 2 AM batch size peaks.

Fix: Stream the result set using `JpaRepository.stream()` inside a transaction, process in chunks, never materialize the full list.

---

### Advanced 2: Memory Leak Only in Production, Not Staging — Environment Difference

**Q: OOM reproduces only in production. Staging has same heap size, same load. How do you find the difference?**

**A:**

This is a classic tracer investigation. The difference is almost always one of:
1. **Data volume** — production data has edge cases (null fields, large payloads, specific encodings) that staging doesn't have
2. **Configuration difference** — prod has a feature flag enabled that causes different code paths
3. **External system difference** — prod calls a real service that returns large responses; staging uses mocks
4. **Time-based** — leak only manifests after N hours; staging tests are shorter

Approach:
```bash
# 1. Diff JVM flags between environments
# prod vs staging: compare -XX flags, system properties
jcmd <pid> VM.flags > /tmp/jvm_flags_prod.txt  # On each env
diff jvm_flags_staging.txt jvm_flags_prod.txt

# 2. Diff application config
jcmd <pid> VM.system_properties | sort > /tmp/props_prod.txt

# 3. Capture heap dumps from BOTH environments after same time window
# Compare object histogram — what's different in prod?
# MAT: File → Compare Baselines → select both .hprof files

# 4. Enable verbose heap allocation sampling in staging with prod data
# Use async-profiler with production DB read replica traffic mirrored
```

Key insight: Use `jcmd <pid> VM.system_properties` to compare full config. A single property like `cache.enabled=true` only in prod can be the entire cause.

---

### Advanced 3: Metaspace Growing in Production — Dynamic Proxy Explosion

**Q: Metaspace steadily grows over weeks in a production Spring Boot app. No hot deploys. No OSGi. Why?**

**A:**

Even without hot deploys, Metaspace can leak via:

1. **CGLIB proxy per-invocation**: If Spring beans are being created (not reusing singletons) and each creation generates a CGLIB subclass
2. **Groovy DSL evaluation**: Scripts compiled at runtime without caching
3. **Reflection-based serialization frameworks**: Jackson or Kryo generating accessor classes per type
4. **Programmatic `ClassLoader` usage**: Library code that creates a new classloader per operation

Diagnosis:
```bash
# Track class count over time
jcmd <pid> VM.classloaders
# Shows classloader hierarchy and class counts per loader

# Monitor via JMX
# java.lang:type=ClassLoading → LoadedClassCount (should be stable)
# java.lang:type=ClassLoading → TotalLoadedClassCount (ever-increasing is expected, but slope matters)

# Heap dump → MAT → Window → Heap Dump Details → Class Loaders tab
# Look for many instances of the same classloader type

# Find retained heap per classloader
# MAT OQL: SELECT * FROM java.lang.ClassLoader WHERE this.@retainedHeapSize > 1000000
```

Pattern catch:
```java
// Bug: new GroovyClassLoader per rule evaluation
public Object evaluateRule(String ruleScript, Map<String, Object> context) {
    GroovyClassLoader loader = new GroovyClassLoader(); // New classloader each time!
    Class<?> ruleClass = loader.parseClass(ruleScript); // New class in Metaspace!
    // loader never closed, class never unloaded
    return ruleClass.newInstance();
}

// Fix: cache compiled classes
private final Map<String, Class<?>> ruleCache = new ConcurrentHashMap<>();
private final GroovyClassLoader sharedLoader = new GroovyClassLoader();

public Object evaluateRule(String ruleScript, Map<String, Object> context) {
    Class<?> ruleClass = ruleCache.computeIfAbsent(
        DigestUtils.sha256Hex(ruleScript),
        key -> sharedLoader.parseClass(ruleScript)
    );
    return ruleClass.newInstance();
}
```

---

### Advanced 4: Memory Pressure from ThreadLocal Leak in Thread Pool

**Q: Explain a ThreadLocal leak pattern and how to find it in a heap dump.**

**A:**

ThreadLocal values are stored in a `ThreadLocalMap` attached to each `Thread` object. In a thread pool (like Tomcat's request threads), threads are reused — they are never garbage collected for the lifetime of the JVM.

If code sets a `ThreadLocal` but never calls `remove()`, the value remains in the thread's map indefinitely. If that value holds a large object graph (e.g., a user session, a Hibernate entity), it accumulates per thread.

```java
// Leak pattern
private static final ThreadLocal<UserContext> userContext = new ThreadLocal<>();

// Servlet filter sets context at request start
userContext.set(new UserContext(request)); // Set on thread pool thread

// BUG: never cleaned up — UserContext stays in thread's ThreadLocalMap forever
// when the same thread handles the next request, old UserContext remains until overwritten
```

```java
// Correct pattern — always remove in finally
public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain) {
    try {
        userContext.set(new UserContext((HttpServletRequest) req));
        chain.doFilter(req, res);
    } finally {
        userContext.remove(); // Critical — cleans up before thread returns to pool
    }
}
```

Heap dump diagnosis:
- MAT: search for `java.lang.ThreadLocal$ThreadLocalMap$Entry` instances
- Check the referent value — is it a large object?
- Follow to parent: `ThreadLocalMap` → `Thread` → thread pool
- OQL query: `SELECT t FROM java.lang.Thread t WHERE t.threadLocals != null`

---

## 5. Senior Trap Questions

---

### TRAP 1: "Just Increase Heap Size"

**Trap:** "We're hitting OOM every 6 hours. If we double the heap from 4 GB to 8 GB, that fixes it, right?"

**Correct Answer:**

No — that's the most common mistake I see from mid-level engineers. Doubling the heap changes the *time to OOM*, not the cause. A leak that fills 4 GB in 6 hours will fill 8 GB in 12 hours. You've just delayed your page by 6 hours.

Worse, a larger heap means longer Full GC pauses when the GC does kick in — a 8 GB heap Full GC with CMS could pause for 10+ seconds, which is harder to hide from users than a smaller heap with more frequent minor GCs.

The correct approach: capture a heap dump, identify the retention root, fix the leak. Heap sizing should be based on the *steady-state* object graph size, not on leak rate.

**When is increasing heap legitimate?** When your application genuinely needs more working memory for the load it handles — e.g., you migrated to larger payloads and the heap is correctly sized too small. But even then, you confirm this with object histogram analysis showing steady-state growth, not runaway growth.

---

### TRAP 2: "jmap -dump is Safe in Production"

**Trap:** "To get a heap dump, I'll just run `jmap -dump:format=b,file=heap.hprof <pid>` on the production server."

**Correct Answer:**

This is risky and I would not run it without careful consideration. `jmap -dump` triggers a **Stop-The-World pause** — all application threads halt while the JVM walks the entire heap. For a 4 GB heap this can take 30–120 seconds of complete application unavailability.

Additionally: if you're running `jmap -dump` while the heap is already under memory pressure (near OOM), the `jmap` process itself connects to the JVM via the JVM tool interface, which can trigger a Full GC, which — if the heap is nearly full — can *cause* the OOM you were trying to capture.

Safer alternatives:
```bash
# Preferred: jcmd — built into JDK, safer implementation
jcmd <pid> GC.heap_dump /tmp/heap.hprof

# For live analysis without full dump:
jcmd <pid> GC.heap_info            # Heap regions summary — instant, no pause
jcmd <pid> VM.class_histogram       # Object count by type — lightweight

# Best: configure auto-dump on OOM (zero production impact)
# JVM flags at startup:
# -XX:+HeapDumpOnOutOfMemoryError
# -XX:HeapDumpPath=/dumps/heapdump-%t.hprof
```

On Kubernetes: mount a `hostPath` or `emptyDir` volume for dump output so it survives pod restart.

---

### TRAP 3: "Shallow Heap = Memory Leak Size"

**Trap:** "MAT shows a `HashMap` with shallow heap of 48 bytes. So it's not the memory leak."

**Correct Answer:**

Shallow heap is almost always irrelevant for identifying leaks. Shallow heap is just the size of the object itself — the header + primitive fields + reference pointers. A `HashMap` wrapper object is 48 bytes whether it holds 0 entries or 40 million.

What matters is **retained heap**: the total memory that would be freed if this object (and everything reachable only through it) were garbage collected.

In MAT:
- Sort the Dominator Tree by **Retained Heap** (descending) — first column to check
- A `HashMap` with 48 bytes shallow heap but 2.1 GB retained heap is your leak root
- Use "Show Retained Heap" option in the histogram view

The formula: `Retained Heap(A) = Shallow(A) + sum of Shallow(B) for all objects B where A is the only path to B from any GC root`

---

### TRAP 4: "OOM in Thread X = Thread X Has the Leak"

**Trap:** "The OOM stack trace shows it happened in the HTTP request handler thread pool. So the leak is in the request handler code."

**Correct Answer:**

This is a critical misunderstanding of where OOM is thrown. `OutOfMemoryError` is thrown at the point where the allocation *fails* — i.e., where the JVM tried to allocate memory and found none available.

The thread that failed to allocate is almost never the thread responsible for the leak. The leaking thread already put the objects on the heap hours or days ago — those objects simply never got collected.

Example: A background thread running a scheduled cache refresh created 2 GB of retained objects at 2 AM. At 3 PM, a routine HTTP request thread tries to allocate a 1 KB `String` and gets OOM. The stack trace points to the HTTP thread's request handling code. But the leak is in the cache refresh scheduled task.

Correct approach: Look at heap dump dominator tree and GC root paths — not the OOM stack trace — to find the responsible code.

---

### TRAP 5: "Metaspace OOM = Not Enough Memory, Add More"

**Trap:** "We're getting Metaspace OOM. Let's add `-XX:MaxMetaspaceSize=512m` — currently it's 256m."

**Correct Answer:**

By default, Metaspace has no maximum and grows until the OS runs out of virtual address space. If you're hitting a `MaxMetaspaceSize` limit, either:

1. You explicitly set it too low (possible — but check if the app *ever* stabilized below that limit)
2. **More likely: there is a classloader leak** and no amount of Metaspace will ever be enough — it'll just OOM later

The tell: run `jstat -gcmetacapacity <pid> 5000 100` and watch whether `MC` (Metaspace Committed) is growing monotonically without any decreases. If it never drops, class unloading is not happening, which means classloaders are being retained.

Increasing `MaxMetaspaceSize` without finding the leak buys time but guarantees the OOM recurs — just later, and potentially with worse impact (larger Metaspace means more time before detection).

Diagnostic first step:
```bash
jcmd <pid> VM.class_histogram | head -30
# Watch for high counts of `$$EnhancerByCGLIB$$` or script class names
```

---

### TRAP 6: "Heap Dump Captures Current State — So Take It Anytime"

**Trap:** "I'll wait until the OOM happens, then take a heap dump to analyze what caused it."

**Correct Answer:**

After an OOM, many runtimes (especially Kubernetes) kill and restart the container immediately. The heap dump file only survives if:
1. You pre-configured `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=...`
2. The dump path is on a persistent volume, not ephemeral container storage

If neither is true, the heap dump from an OOM crash is lost.

Better practice — capture before OOM, while the leak is active but the process is alive:
```bash
# Triggered heap dump when heap usage > threshold (alert-driven)
jcmd <pid> GC.heap_dump /persistent-volume/heap-$(date +%s).hprof

# Or use GC log alerting: alert when OldGen occupancy > 80%, then trigger dump
# This gives you a heap dump while the process is alive and analyzable
```

Also: a post-OOM heap dump may have corrupted data structures if the JVM was mid-allocation. Pre-OOM dumps are more reliable for analysis.

---

## 6. Java Code Examples — Production Patterns

---

### JVM Startup Flags — Production Template

```bash
java \
  -Xms4g -Xmx4g \
  -XX:+UseG1GC \
  -XX:MaxGCPauseMillis=200 \
  -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=/dumps/heapdump-%t.hprof \
  -Xlog:gc*:file=/logs/gc.log:time,level,tags:filecount=5,filesize=20m \
  -XX:+ExitOnOutOfMemoryError \
  -XX:MaxDirectMemorySize=512m \
  -XX:MaxMetaspaceSize=512m \
  -jar app.jar
```

Note: `-XX:+ExitOnOutOfMemoryError` causes the JVM to exit immediately on OOM (triggering K8s restart) rather than limping along in a degraded state. Always use this in containerized deployments.

---

### Caffeine Cache — Bounded, Production-Grade

```java
@Configuration
public class CacheConfig {

    @Bean
    public Cache<String, UserProfile> userProfileCache() {
        return Caffeine.newBuilder()
            .maximumSize(50_000)
            .expireAfterWrite(Duration.ofMinutes(15))
            .recordStats()                          // Expose to Micrometer
            .removalListener((key, val, cause) ->
                log.debug("Evicted key={} cause={}", key, cause))
            .build();
    }

    @Bean
    public CacheMetricsCollector caffeineCacheMetrics(
            Cache<String, UserProfile> userProfileCache) {
        return new CacheMetricsCollector()
            .addCache("user-profile", userProfileCache);
    }
}
```

---

### Detecting Heap Pressure Programmatically

```java
@Component
public class HeapPressureMonitor {

    private static final double HEAP_WARN_THRESHOLD = 0.85;

    @Scheduled(fixedDelay = 60_000)
    public void checkHeapUsage() {
        MemoryMXBean memBean = ManagementFactory.getMemoryMXBean();
        MemoryUsage heapUsage = memBean.getHeapMemoryUsage();
        double usedRatio = (double) heapUsage.getUsed() / heapUsage.getMax();

        if (usedRatio > HEAP_WARN_THRESHOLD) {
            log.warn("Heap pressure: {:.1f}% used ({} of {} MB)",
                usedRatio * 100,
                heapUsage.getUsed() / 1_048_576,
                heapUsage.getMax() / 1_048_576);
            // Optionally: trigger heap dump programmatically via HotSpotDiagnosticMXBean
        }
    }
}
```

---

### Programmatic Heap Dump Trigger

```java
public class HeapDumper {

    private static final String HOTSPOT_BEAN =
        "com.sun.management:type=HotSpotDiagnostic";

    public static void dumpHeap(String filePath, boolean live) throws Exception {
        MBeanServer server = ManagementFactory.getPlatformMBeanServer();
        HotSpotDiagnosticMXBean bean = ManagementFactory.newPlatformMXBeanProxy(
            server, HOTSPOT_BEAN, HotSpotDiagnosticMXBean.class);
        bean.dumpHeap(filePath, live); // live=true: only reachable objects
    }
}
```

---

### Proper Resource Management — Try-With-Resources

```java
// Every InputStream, Connection, PreparedStatement must be auto-closed
public List<OrderDTO> fetchOrders(Long userId) throws Exception {
    String sql = "SELECT * FROM orders WHERE user_id = ?";
    try (Connection conn = dataSource.getConnection();
         PreparedStatement ps = conn.prepareStatement(sql)) {
        ps.setLong(1, userId);
        try (ResultSet rs = ps.executeQuery()) {
            List<OrderDTO> result = new ArrayList<>();
            while (rs.next()) {
                result.add(OrderDTO.fromResultSet(rs));
            }
            return result;
        }
    }
    // All resources closed even on exception — no connection pool exhaustion
}
```

---

### Netty Handler — Correct ByteBuf Release

```java
@ChannelHandler.Sharable
public class SafeMessageHandler extends SimpleChannelInboundHandler<ByteBuf> {

    // SimpleChannelInboundHandler auto-releases msg after channelRead0
    @Override
    protected void channelRead0(ChannelHandlerContext ctx, ByteBuf msg) {
        byte[] bytes = new byte[msg.readableBytes()];
        msg.readBytes(bytes);
        processBytes(bytes);
        // No need to call msg.release() — SimpleChannelInboundHandler does it
    }

    @Override
    public void exceptionCaught(ChannelHandlerContext ctx, Throwable cause) {
        log.error("Handler error", cause);
        ctx.close();
    }
}
```

---

### jstat / jcmd Quick Reference

```bash
# GC stats every second for 60 iterations
jstat -gcutil <pid> 1000 60

# Output columns:
# S0(%) S1(%) E(%) O(%) M(%) CCS(%) YGC YGCT FGC FGCT CGC CGCT GCT
# S0/S1=Survivor, E=Eden, O=OldGen, M=Metaspace, *GC=count, *GCT=time

# Object histogram (top 20 by instance count)
jcmd <pid> VM.class_histogram | head -25

# Thread dump
jcmd <pid> Thread.print > /tmp/threads.txt

# Heap summary (fast, no pause)
jcmd <pid> GC.heap_info

# JVM flags in effect
jcmd <pid> VM.flags

# Heap dump (safer than jmap)
jcmd <pid> GC.heap_dump /tmp/heap.hprof

# List all JVM processes
jcmd

# Force GC (dev/staging only — never production)
jcmd <pid> GC.run
```

---

## 7. Interview Cheat Sheet

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     OOM TYPE → ROOT CAUSE → FIX                           │
├──────────────────────┬───────────────────────────┬────────────────────────┤
│ OOM Type             │ Typical Root Cause         │ First Action           │
├──────────────────────┼───────────────────────────┼────────────────────────┤
│ Java heap space      │ Object retention (static   │ MAT dominator tree     │
│                      │ collection, cache, session)│ + GC root path         │
├──────────────────────┼───────────────────────────┼────────────────────────┤
│ GC overhead limit    │ Heap nearly full — GC      │ Same as heap space     │
│ exceeded             │ thrashing (same as above)  │ (just detected earlier)│
├──────────────────────┼───────────────────────────┼────────────────────────┤
│ Metaspace            │ Classloader leak           │ VM.classloaders,       │
│                      │ Dynamic class gen          │ class_histogram        │
├──────────────────────┼───────────────────────────┼────────────────────────┤
│ Direct buffer memory │ Netty ByteBuf not released │ -Dio.netty.leak=SIMPLE │
│                      │ NIO ByteBuffer not freed   │ Check BufferPool JMX   │
├──────────────────────┼───────────────────────────┼────────────────────────┤
│ Unable to create     │ Thread leak / OS ulimit    │ Thread.print count     │
│ new native thread    │                            │ ulimit -u              │
├──────────────────────┼───────────────────────────┼────────────────────────┤
│ Compressed class     │ Sub-type of Metaspace leak │ Same as Metaspace      │
│ space                │                            │                        │
└──────────────────────┴───────────────────────────┴────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                     HEAP DUMP TOOLS COMPARISON                             │
├──────────────────────┬────────────┬──────────────────────────────────────┤
│ Tool                 │ Production │ Notes                                 │
│                      │ Safe?      │                                       │
├──────────────────────┼────────────┼──────────────────────────────────────┤
│ -XX:+HeapDumpOnOOM   │ YES        │ Best — zero overhead until OOM       │
├──────────────────────┼────────────┼──────────────────────────────────────┤
│ jcmd GC.heap_dump    │ MOSTLY     │ STW pause but safer than jmap        │
├──────────────────────┼────────────┼──────────────────────────────────────┤
│ jmap -dump           │ RISKY      │ Can trigger OOM mid-dump on stressed │
│                      │            │ JVM; full STW pause                  │
├──────────────────────┼────────────┼──────────────────────────────────────┤
│ async-profiler alloc │ YES        │ Sampling — not a heap dump, but      │
│                      │            │ finds allocation hotspots live       │
└──────────────────────┴────────────┴──────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                     MAT WORKFLOW — 60-SECOND TRIAGE                       │
├────────────────────────────────────────────────────────────────────────────┤
│ 1. Open .hprof in MAT                                                      │
│ 2. Dominator Tree → Sort by Retained Heap DESC → note top 3               │
│ 3. Right-click top object → Path to GC Roots → Exclude soft/weak/phantom  │
│ 4. Follow path to static field or thread-local → that's your anchor       │
│ 5. Check Leak Suspects report for confirmation                             │
│ 6. OQL for targeted queries: SELECT * FROM java.util.HashMap h             │
│    WHERE h.@retainedHeapSize > 100000000                                   │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                     PRODUCTION DEBUG WORKFLOW                              │
├────────────────────────────────────────────────────────────────────────────┤
│ 1. REPRODUCE                                                               │
│    - Confirm OOM type from logs                                            │
│    - Correlate with deployment, traffic spike, scheduled job               │
│    - Use jstat -gcutil to confirm heap trend (growing = leak)              │
│                                                                            │
│ 2. CAPTURE                                                                 │
│    - Ensure -XX:+HeapDumpOnOutOfMemoryError is set (if not, add + restart)│
│    - Take manual dump before next OOM: jcmd <pid> GC.heap_dump            │
│    - Thread dump if thread leak suspected: jcmd <pid> Thread.print        │
│                                                                            │
│ 3. ANALYZE                                                                 │
│    - MAT: Dominator Tree → GC root path → identify retention anchor       │
│    - Find the code that creates the retaining structure                    │
│    - Confirm: is this a known Spring pattern? Hibernate? Cache? ThreadLocal│
│                                                                            │
│ 4. FIX                                                                     │
│    - Address the root cause (eviction, resource close, remove())           │
│    - Add metrics (gauge on cache size, GC pause alerting)                  │
│    - Code review for similar patterns in codebase                          │
│                                                                            │
│ 5. VERIFY                                                                  │
│    - Load test at 2x production traffic in staging                         │
│    - Confirm heap stabilizes below 70% after 2+ hours                     │
│    - Canary deploy: 5% traffic, 30-minute observation                     │
│    - Full rollout + post-deploy monitoring dashboard review                │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                     TRAP QUESTION QUICK RECALL                             │
├──────────────────────────────────────┬─────────────────────────────────── │
│ Trap                                 │ One-liner Rebuttal                  │
├──────────────────────────────────────┼───────────────────────────────────┤
│ "Increase heap to fix OOM"           │ Delays crash, doesn't fix leak.    │
│                                      │ GC pauses get worse with bigger     │
│                                      │ heap.                              │
├──────────────────────────────────────┼───────────────────────────────────┤
│ "jmap -dump is safe"                 │ Triggers STW pause; can cause OOM  │
│                                      │ on stressed JVM. Use jcmd instead. │
├──────────────────────────────────────┼───────────────────────────────────┤
│ "Shallow heap = leak size"           │ Use retained heap — what would     │
│                                      │ actually be freed.                 │
├──────────────────────────────────────┼───────────────────────────────────┤
│ "OOM in thread X = thread X leaks"  │ OOM thrown where allocation fails,  │
│                                      │ not where objects were created.     │
├──────────────────────────────────────┼───────────────────────────────────┤
│ "Metaspace OOM = need more memory"  │ Usually a classloader leak —        │
│                                      │ no amount of memory fixes it.      │
├──────────────────────────────────────┼───────────────────────────────────┤
│ "Take heap dump anytime after OOM"  │ Pod may restart; dump path may be   │
│                                      │ ephemeral. Pre-configure OOM dump. │
└──────────────────────────────────────┴───────────────────────────────────┘

KEY TERMS TO DROP IN INTERVIEW:
  - Dominator Tree (MAT)
  - Retained vs Shallow heap
  - GC root path / retention path
  - Stop-The-World (STW) pause
  - Safepoint (required for heap dump)
  - OSIV (Open Session In View) anti-pattern
  - Classloader leak / Metaspace growth
  - PooledByteBufAllocator ref counting (Netty)
  - async-profiler allocation profiling
  - -XX:+ExitOnOutOfMemoryError (containerized apps)
  - jcmd (preferred over jmap in production)
  - jstat -gcutil (live GC monitoring, zero risk)
```

---

## 8. Quick Reference — Common Spring Boot OOM Patterns

| Pattern | Symptom | Detection | Fix |
|---|---|---|---|
| Unbounded static cache | Heap grows monotonically | MAT: static field with huge retained heap | Caffeine with `maximumSize` + TTL |
| OSIV + lazy loading | Heap grows with traffic | High `SessionImpl` count in histogram | `spring.jpa.open-in-view=false` |
| ThreadLocal not removed | Per-thread objects accumulate | `ThreadLocalMap$Entry` count = thread pool size × leaks | Always `remove()` in `finally` |
| Netty ByteBuf not released | Direct memory OOM | Netty leak detection logs | Use `SimpleChannelInboundHandler` or explicit `release()` |
| Groovy script per eval | Metaspace grows | High `$$` class count in histogram | Cache compiled `Class<?>` objects |
| HTTP response body not consumed | Connection pool exhaustion → heap | `KeepAliveStream` objects in dump | Use `WebClient`; always call `.bodyToMono()` |
| Thread-per-request | Native thread OOM | Thread count > 500 in `Thread.print` | Use `ThreadPoolTaskExecutor` with bounds |
| Large batch in-memory | Burst OOM | Correlated with scheduled time | Stream with `JpaRepository.stream()`, process in chunks |

---

*File: `/how_to_debug_JVM/01_heap_dump_analysis_interview.md`*
*Last updated: 2026-08-21*
*Audience: Staff/Principal Java Engineer, Java Architect interviews — 10–18 YOE level*
