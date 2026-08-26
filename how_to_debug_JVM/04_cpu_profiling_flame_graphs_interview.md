# CPU Profiling & Flame Graphs — Java Architect Interview Prep (15 YOE)

> Target role: Staff / Principal Engineer, Java Architect, Senior SRE  
> Focus: Production CPU profiling, async-profiler, JFR, flame graph interpretation

---

## 1. Big Picture: Profiling Methods & JFR Event Pipeline

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║                     JAVA CPU PROFILING LANDSCAPE                               ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║   HIGH CPU IN PRODUCTION                                                       ║
║         │                                                                      ║
║         ▼                                                                      ║
║   ┌─────────────────────────────────────────────────────────┐                 ║
║   │             PROFILING APPROACH SELECTION                │                 ║
║   └─────────────────────────────────────────────────────────┘                 ║
║         │                           │                                          ║
║         ▼                           ▼                                          ║
║   ┌──────────────┐           ┌──────────────────┐                             ║
║   │  SAMPLING    │           │ INSTRUMENTATION  │                             ║
║   │  (Preferred) │           │  (Use sparingly) │                             ║
║   └──────────────┘           └──────────────────┘                             ║
║         │                           │                                          ║
║    Low overhead                High overhead                                   ║
║    ~1-3% CPU                   10-100x slowdown                                ║
║    Statistical                 Exact counts                                    ║
║    Safe for prod               Avoid in prod                                   ║
║         │                           │                                          ║
║         ▼                           ▼                                          ║
║   ┌──────────────┐           ┌──────────────────┐                             ║
║   │ async-profiler│           │  Byte-buddy      │                             ║
║   │ JFR (built-in)│           │  AspectJ         │                             ║
║   │ Honest-Profiler│          │  -javaagent APM  │                             ║
║   └──────────────┘           └──────────────────┘                             ║
║                                                                                ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║   SAFEPOINT BIAS PROBLEM                                                       ║
║                                                                                ║
║   JVMTI-based profiler (JVisualVM, YourKit JVMTI mode):                       ║
║                                                                                ║
║   Thread Timeline:                                                             ║
║   ████░░░░████░░░░████░░░░████  ← actual execution                            ║
║        ↑         ↑         ↑                                                   ║
║     safepoint  safepoint  safepoint  ← profiler can ONLY sample here          ║
║                                                                                ║
║   Code between safepoints is INVISIBLE to JVMTI-based profilers!              ║
║   Tight loops with no safepoint poll = 0 samples despite 100% CPU             ║
║                                                                                ║
║   async-profiler uses AsyncGetCallTrace (AGCT):                               ║
║   Thread Timeline:                                                             ║
║   ████░░░░████░░░░████░░░░████  ← actual execution                            ║
║   ↑  ↑  ↑  ↑  ↑  ↑  ↑  ↑  ↑   ← AGCT can sample ANYWHERE (perf_events)      ║
║                                                                                ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║   JFR EVENT PIPELINE                                                           ║
║                                                                                ║
║   JVM Runtime                                                                  ║
║   ┌───────────────────────────────────────────────────────┐                   ║
║   │  JVM Events: GC, JIT, Thread, Socket, File, Monitor  │                   ║
║   │  Custom Events: @Label, @Category annotations        │                   ║
║   └──────────────────────┬────────────────────────────────┘                   ║
║                          │  low-overhead circular buffer                      ║
║                          ▼                                                     ║
║   ┌────────────────────────────────────┐                                      ║
║   │  In-Memory Circular Buffer         │  ← configurable size (default 64MB) ║
║   │  (never fills disk by default)     │                                      ║
║   └──────────────────┬─────────────────┘                                      ║
║                      │  triggered dump or periodic                            ║
║                      ▼                                                         ║
║   ┌────────────────────────────────────┐                                      ║
║   │  recording.jfr (binary file)       │                                      ║
║   └──────────────────┬─────────────────┘                                      ║
║                      │                                                         ║
║                      ▼                                                         ║
║   ┌────────────────────────────────────┐                                      ║
║   │  Java Mission Control (JMC)        │  ← GUI analysis                     ║
║   │  jfr print / JFR API              │  ← programmatic                      ║
║   └────────────────────────────────────┘                                      ║
║                                                                                ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║   FLAME GRAPH ANATOMY                                                          ║
║                                                                                ║
║   Y-axis (vertical):  call stack depth — bottom = on-CPU, top = callers       ║
║   X-axis (horizontal): sample count proportion — WIDER = more CPU time        ║
║   Color: arbitrary (heat map aesthetic) — does NOT encode meaning by default  ║
║                                                                                ║
║   ┌─────────────────────────────────────────────────────────┐                 ║
║   │                   main()                                │ ← wide = hot   ║
║   │          ┌─────────────┐  ┌────────────┐               │                 ║
║   │          │ processReq()│  │ serialize()│               │                 ║
║   │  ┌───┐   │   ┌──────┐  │  │  ┌──────┐  │               │                 ║
║   │  │GC │   │   │regex │  │  │  │JSON  │  │               │                 ║
║   │  │   │   │   │      │  │  │  │      │  │               │                 ║
║   └──┴───┴───┴───┴──────┴──┴──┴──┴──────┴──┴───────────────┘                 ║
║                      ↑                                                         ║
║                   PLATEAU — flat top means self-time is HIGH                  ║
║                   This is where time is spent, not delegating further         ║
║                                                                                ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## 2. Conversational Interview Script — 15-YOE Architect Voice

**Interviewer:** "Walk me through how you'd diagnose high CPU on a production JVM service."

---

**Me:** Sure. First thing I do — don't jump straight to a profiler. I triage at the OS level.

I run `top` or `htop` to confirm it's the Java process causing the spike, then I check `top -H -p <pid>` to see which threads are burning CPU. I cross-reference those TIDs (in hex) against a `jstack` dump to see what those threads are doing.

If I see GC threads at the top, that's a different diagnosis path entirely — the root cause might be an allocation storm, not application code. I check GC logs first: `jstat -gcutil <pid> 1000` gives me GC frequency and heap utilization in real time.

If it's application threads, I need a profiler. My default in production is async-profiler. I'm not going to touch JVisualVM — it has safepoint bias and non-trivial overhead for a busy service. async-profiler uses AsyncGetCallTrace under the hood, so it can sample at any point in execution, not just safepoint polls.

I attach it like this:

```bash
./profiler.sh -e cpu -d 30 -f /tmp/profile.html <pid>
```

That gives me 30 seconds of CPU sampling as an interactive flame graph HTML. I open it and look for wide "plateaus" — methods with wide bases but no tall children above them. Those are the self-time hot spots.

Common culprits I've seen in prod: `Pattern.compile()` getting called per request, `String.format()` inside a tight loop, reflection without method caching, `HashMap` key lookup where `hashCode()` does deep object traversal, and serialization frameworks doing repeated class introspection.

Alternatively, if the service is instrumented with JFR — which it should be if we're running JDK 11+ with always-on JFR in circular buffer mode — I'll just dump the in-flight recording:

```bash
jcmd <pid> JFR.dump filename=/tmp/recording.jfr
```

Then analyze in JMC. JFR has virtually zero overhead in circular buffer mode. I can get CPU, allocation, lock contention, and file/socket I/O all from one recording.

For live, surgical inspection without a restart, I use Arthas. `trace com.myapp.OrderService processOrder` gives me per-invocation timing broken down by method. But I only do that in controlled maintenance windows or when the service is already degraded and I need to confirm a suspect method.

---

**Interviewer:** "What if you can't attach a profiler — say it's a locked-down environment?"

**Me:** Then I rely on what I can get non-intrusively. JFR started in the JVM with `always-on` mode means I already have data — I just need `jcmd JFR.dump`. That requires no attach. If jcmd isn't available either, I look at thread dumps taken 5 seconds apart — three or four jstacks. Any method that appears repeatedly in RUNNABLE state across dumps is spending real CPU. It's a poor man's profiler, but it works.

I also look at GC logs, heap dumps if memory looks correlated, and APM data if we have Datadog or New Relic — they do bytecode instrumentation at the framework level, so they won't show me low-level Java hotspots, but they'll confirm which endpoint or service boundary is expensive.

---

## 3. Scenario Q&As — Production CPU Incidents (8+)

---

### Scenario 1: Service CPU Spike After Traffic Increase

**Q:** Your REST service runs fine at 1k RPS. At 5k RPS, CPU jumps to 95% and latency degrades. How do you find the cause?

**A:**

Traffic-proportional CPU escalation — likely a per-request operation that doesn't scale. Safepoint bias is irrelevant here; I need to see what's hot at load.

Step 1 — triage:
```bash
top -H -p <pid>          # which threads are hot
jstat -gcutil <pid> 1000 # is GC involved
```

Step 2 — async-profiler at peak load:
```bash
./profiler.sh -e cpu -d 60 -f /tmp/spike.html <pid>
```

Step 3 — read flame graph. At 5k RPS I've seen `Pattern.compile()` show up as 40% of CPU because an engineer added a regex validator in a request filter without caching the Pattern. Fix: compile once as a static final field.

```java
// WRONG — compiles on every request
public boolean validate(String input) {
    return input.matches("^[a-zA-Z0-9]+$");
}

// RIGHT — compile once
private static final Pattern ALPHANUMERIC = Pattern.compile("^[a-zA-Z0-9]+$");
public boolean validate(String input) {
    return ALPHANUMERIC.matcher(input).matches();
}
```

---

### Scenario 2: CPU Spike With No Traffic Increase

**Q:** CPU suddenly goes to 100% at 2 AM with no deployment and no traffic change. What's happening?

**A:**

This is a scheduled job or a deferred consequence (memory leak finally triggering full GC).

Check:
```bash
jstat -gcutil <pid> 500 20  # 20 samples at 500ms intervals
```

If Old Gen is near 100% and Full GC is running every 5 seconds, that's your CPU. GC threads consume CPU. The real bug is whatever caused heap exhaustion — a cache that wasn't bounded, a session store leaking, a batch job loading too much data.

Also check: `jcmd <pid> VM.native_memory` for native memory, cron logs for 2 AM jobs.

---

### Scenario 3: Specific Endpoint Slow, Others Fine

**Q:** The `/search` endpoint takes 2s at p99. All others are sub-100ms. CPU is elevated only during search calls.

**A:**

Endpoint-scoped profiling. I want to correlate CPU samples with just the search code path.

```bash
# Wall-clock mode to catch all threads including I/O waits
./profiler.sh -e wall -d 30 -t -f /tmp/wall.html <pid>
```

Wall-clock mode shows threads even while they're blocked — useful for distinguishing CPU-bound vs I/O-bound work.

While profiling, hammer the search endpoint:
```bash
ab -n 1000 -c 10 https://myservice/search?q=test
```

Look in the flame graph for the search thread pool. Common findings: Lucene/Elasticsearch client doing repeated JSON deserialization, N+1 database queries expanding into heavy ORM work, or Hibernate second-level cache miss loading full entity graphs.

---

### Scenario 4: Thread Contention Causing CPU Spin

**Q:** You see 50 threads all RUNNABLE, CPU is 100%, but throughput is near zero. What's going on?

**A:**

Classic spin-wait / busy-loop anti-pattern. Threads are RUNNABLE but not making progress — spinning on a lock or a tight retry loop.

```bash
# Take 3 thread dumps 2 seconds apart
jstack <pid> > /tmp/dump1.txt && sleep 2 && jstack <pid> > /tmp/dump2.txt

# Look for same threads appearing RUNNABLE with same stack trace
grep -A 20 "RUNNABLE" /tmp/dump1.txt
```

If you see the same threads in the same place across all dumps, they're spinning. Common cause: hand-written spinlock, a `while (!done) {}` polling loop, or CAS-retry in a lock-free structure under extreme contention.

Fix: introduce backoff, use `LockSupport.parkNanos()`, or replace with proper `ReentrantLock` / `Semaphore`.

---

### Scenario 5: Memory Allocation Storm Driving GC CPU

**Q:** CPU usage is high, async-profiler flame graph shows `GC worker` threads at the top. Application code looks clean. What next?

**A:**

The application is generating garbage faster than GC can collect. CPU is consumed by GC, not app logic. Profiling the wrong thing.

Switch to allocation profiling:
```bash
./profiler.sh -e alloc -d 30 -f /tmp/alloc.html <pid>
```

This shows allocation sites. Common findings: `String.format()` or `+` concatenation in a hot loop creating millions of char arrays, `ArrayList.toArray()` called repeatedly, `new ObjectMapper()` per request (heavyweight, ~1MB allocation cost), Lombok `@Builder` creating intermediate objects per field.

Also look at JFR:
```bash
jcmd <pid> JFR.start duration=60s filename=/tmp/alloc.jfr settings=profile
```

JFR "Allocation in New TLAB" events show exactly what's being allocated and where.

---

### Scenario 6: Reflection-Heavy Code Path

**Q:** After a library upgrade, CPU went up 30%. No other changes. How do you trace it?

**A:**

Library upgrades that change how classes are introspected, especially if they moved from code generation to reflection, can cause this.

async-profiler flame graph will show `java.lang.reflect.Method.invoke()` or `sun.reflect.*` high in the stack. In Java 8, the JVM uses generated bytecode for reflective calls after 15 invocations — but if method objects aren't cached, you re-pay the inflation cost on every call.

```java
// Problematic — re-looks up method every call
public Object invoke(Object target, Object[] args) throws Exception {
    Method m = target.getClass().getMethod("process", String.class);
    return m.invoke(target, args);
}

// Fixed — cache the Method object
private static final Method PROCESS_METHOD;
static {
    try {
        PROCESS_METHOD = MyService.class.getMethod("process", String.class);
        PROCESS_METHOD.setAccessible(true);
    } catch (NoSuchMethodException e) { throw new ExceptionInInitializerError(e); }
}
```

If it's a framework (Jackson, Spring), check if they upgraded from ASM-generated accessors to standard reflection.

---

### Scenario 7: String Operations in Hot Path

**Q:** E-commerce service is CPU-bound on the order formatting path. What are the usual string suspects?

**A:**

```java
// WRONG — StringBuilder created implicitly per concat, O(n) copies
String result = "";
for (Order o : orders) {
    result += o.getId() + "," + o.getTotal() + "\n";
}

// WRONG — String.format parses format string on every call
String line = String.format("Order %s: $%.2f", o.getId(), o.getTotal());

// RIGHT — pre-sized StringBuilder, avoid format parsing
StringBuilder sb = new StringBuilder(orders.size() * 40);
for (Order o : orders) {
    sb.append(o.getId()).append(',').append(o.getTotal()).append('\n');
}
```

In the flame graph, `String.format` shows up because `Formatter` parses the format string, allocates a buffer, and the format string itself isn't cached by the JVM. At 10k calls/sec this is measurable.

---

### Scenario 8: HashMap With Bad hashCode

**Q:** A cache lookup that should be O(1) is showing up as a significant CPU consumer in profiling. How?

**A:**

If the key's `hashCode()` has poor distribution or is expensive to compute, HashMap degrades to O(n).

Two scenarios:
1. `hashCode()` always returns the same value (classic bug) — every key lands in the same bucket, lookup is a linear scan
2. `hashCode()` traverses a deep object graph (e.g., a recursive data structure) — each lookup triggers a full traversal

```java
// Problematic — deeply nested object as cache key
public class GraphNode {
    List<GraphNode> children;
    @Override public int hashCode() {
        return Objects.hash(children); // recursive — O(n^2) for deep graphs
    }
}

// Fix — use a stable identifier-based key
public class GraphNode {
    final String id;
    @Override public int hashCode() { return id.hashCode(); }
}
```

Async-profiler will show `hashCode()` / `equals()` high in the flame graph, directly above `HashMap.get()`. Check the implementation of the key class.

---

## 4. Advanced Scenario Q&As (4+)

---

### Advanced 1: JIT Deoptimization Causing Intermittent CPU Spikes

**Q:** You see periodic CPU spikes every ~5 minutes lasting 200ms. Flame graphs look clean. JFR shows anything?

**A:**

This pattern — periodic short spikes — often points to JIT deoptimization and recompilation cycles.

JFR captures `jdk.Deoptimization` events. When a method is deoptimized (e.g., because a new subclass was loaded that breaks an inlining assumption), the JVM falls back to interpreted bytecode — which is 10-100x slower — until the JIT recompiles.

```bash
jcmd <pid> JFR.start duration=300s filename=/tmp/deopt.jfr settings=profile
# Wait for a spike to occur
jcmd <pid> JFR.dump filename=/tmp/deopt.jfr
```

In JMC, look at the "JIT Compilation" and "Deoptimization" event views. If you see mass deoptimizations following a class loading event, the fix is either: avoid dynamic class loading in hot paths, or use `@Stable` fields to give JIT stronger inlining hints.

Also check: `-XX:+PrintCompilation` output piped to a file during the spike (costs log I/O but fine for a short diagnostic window).

---

### Advanced 2: Profiling Async/Reactive Code

**Q:** Your service uses Project Reactor (WebFlux). Standard CPU flame graphs show `reactor.core.publisher.*` as the top consumer, but you can't see which business logic is hot. How do you profile reactive code?

**A:**

Standard sampling profilers show the operator pipeline, not the logical call chain. You need context propagation.

Option 1 — async-profiler wall-clock mode with thread filtering:
```bash
./profiler.sh -e wall -t --filter "reactor-http-nio" -d 30 -f /tmp/reactive.html <pid>
```

This shows the wall-clock profile of reactor worker threads, and you can see the operator chain.

Option 2 — Reactor's built-in instrumentation:
```java
// Enable checkpoint() to add stack trace markers
Flux.from(source)
    .map(this::transform)
    .checkpoint("after-transform")
    .flatMap(this::enrich)
    .checkpoint("after-enrich")
    .subscribe();
```

Checkpoints add operator identifiers visible in stack traces and JFR events.

Option 3 — reactor-tools agent for full assembly-time stack capture:
```bash
java -javaagent:reactor-tools.jar -jar myapp.jar
```

This instruments every Flux/Mono at assembly time, providing full logical stack traces when profiling.

The key insight: in reactive code, the "caller" and the "computation thread" are decoupled. Wall-clock profiling per-thread gives you real execution, not logical call chains.

---

### Advanced 3: Container CPU Throttling vs JVM CPU

**Q:** In Kubernetes, your pod shows low CPU usage (30% of limit) but is experiencing high latency. JVM profiling shows nothing hot. What's the issue?

**A:**

CPU throttling. Kubernetes CFS (Completely Fair Scheduler) enforces CPU limits in 100ms periods. Even if average usage is 30%, a JVM can burst above the CPU limit in a short window, triggering throttling. The container is throttled — not using more CPU — but threads are paused.

Check:
```bash
# From inside the container
cat /sys/fs/cgroup/cpu/cpu.stat
# Look for: throttled_time (nanoseconds throttled)
# nr_throttled (number of periods throttled)
```

Or via metrics: `container_cpu_cfs_throttled_seconds_total` in Prometheus.

If throttling is significant, options:
1. Increase CPU limit (not request) to allow bursting
2. Set `--cpu-period` and `--cpu-quota` to give longer windows (reduces burst but also reduces average responsiveness)
3. JVM flag: `-XX:ActiveProcessorCount=N` to tell the JVM how many CPUs are available — affects ForkJoinPool size, GC thread count

Also: G1GC uses parallel GC threads that burst CPU. If GC is throttled, GC pause times explode. JFR GC event data will show long pauses not caused by GC work but by scheduler throttling.

---

### Advanced 4: Comparing Two Flame Graphs (Before/After)

**Q:** You deployed a fix for a CPU regression. How do you quantitatively compare pre- and post-deployment flame graphs?

**A:**

Visual comparison of two flame graphs is error-prone. Use differential flame graphs.

async-profiler can produce collapsed stacks:
```bash
# Before deployment
./profiler.sh -e cpu -d 60 -o collapsed -f /tmp/before.txt <pid>

# After deployment
./profiler.sh -e cpu -d 60 -o collapsed -f /tmp/after.txt <pid>

# Generate differential flame graph using Brendan Gregg's tools
./difffolded.pl /tmp/before.txt /tmp/after.txt | ./flamegraph.pl > /tmp/diff.svg
```

In the diff flame graph, red = regression (more CPU after), blue = improvement (less CPU after). The width still represents sample count delta. This makes it immediately obvious if your fix helped and where any new hotspots appeared.

Quantitatively: compare total sample counts for the hot method:
```bash
grep "Pattern.compile" /tmp/before.txt | awk -F' ' '{sum+=$2} END {print sum}'
grep "Pattern.compile" /tmp/after.txt  | awk -F' ' '{sum+=$2} END {print sum}'
```

---

## 5. Senior Trap Questions (6+)

---

### Trap 1: "High CPU Always Means Infinite Loop"

**Q:** "If CPU is at 100%, you have an infinite loop somewhere, right?"

**TRAP:** This is wrong — and a senior engineer should immediately push back.

**Correct answer:**

High CPU has multiple root causes. An infinite loop is one, but consider:

- **GC CPU**: GC threads are JVM threads. During a Full GC or G1 mixed collection, GC can use all available cores. `jstat -gcutil <pid> 1s` will show this immediately. The fix is heap sizing and allocation reduction, not fixing application loops.

- **Thread pool saturation**: If 100 threads are all RUNNABLE doing legitimate work (request handling, serialization), that's also 100% CPU — but it's doing useful work. Check throughput: if requests are completing, it's just load. If they're not completing, then investigate.

- **JIT compilation burst**: After a restart or after a new deployment, the JIT recompiles all hot methods from scratch. This can spike CPU for the first 30-60 seconds as the JVM "warms up". Expected behavior, not a bug.

- **Tight retry loops**: Not infinite, but a retry loop with no backoff (e.g., while DB is unavailable) can spin at 100% CPU doing nothing useful.

Diagnosis order: check GC first, check if work is completing, then look for loops.

---

### Trap 2: "JVisualVM Is Fine for Production Profiling"

**Q:** "We've been using JVisualVM to profile production issues for years. It works fine."

**TRAP:** JVisualVM has two major problems in production.

**Correct answer:**

JVisualVM uses JVMTI (JVM Tool Interface) for CPU profiling. JVMTI profilers can only gather stack traces at **safepoints** — specific points where the JVM guarantees all threads are in a known state. This causes **safepoint bias**: code that runs in tight loops without safepoint polls is systematically under-sampled or entirely invisible.

Classic example: a tight numeric computation loop in Java has no safepoint poll. JVisualVM samples zero from it even if it's consuming 90% of CPU.

Additionally, JVMTI profiling has 10-40% overhead on a busy service — unacceptable in production.

async-profiler uses `AsyncGetCallTrace`, a JVMPI-era API that bypasses safepoints and can capture stack traces at any point via OS-level `perf_events` or `itimer`. It has <3% overhead and is production-safe.

If the team has been using JVisualVM and claiming it works, they may simply not have encountered the cases where safepoint bias hides the real culprit. Switch to async-profiler.

---

### Trap 3: "Flame Graph X-Axis Is Time Order"

**Q:** "On this flame graph, the left side is early in execution and the right side is later, right?"

**TRAP:** The X-axis in a flame graph is NOT chronological.

**Correct answer:**

The X-axis represents **proportional sample count** — width is how often that code appeared in profiler samples. It has nothing to do with time order.

Within the same parent frame, child frames are sorted **alphabetically by function name** by default (in Brendan Gregg's flamegraph.pl). This is to make the same stack always appear at the same X position, enabling visual diffs. Some implementations sort by sample count (wider left), but alphabetical is the default and most common.

What you read from the X-axis:
- Wide = appears in many samples = consumes more CPU
- Narrow = appears in few samples = rarely on-CPU

What you DO NOT read from X-axis:
- Which code ran first
- Which code ran last
- Time sequence of execution

If an interviewer or colleague says "the code on the left ran before the code on the right" — that's a flame graph misreading.

---

### Trap 4: "Profile in Dev, Get the Same Results as Prod"

**Q:** "Just reproduce the issue in your local dev environment and profile there. Saves the risk of attaching to prod."

**TRAP:** Dev profiling results can be misleading for production issues.

**Correct answer:**

Several factors make dev and prod profiling results diverge significantly:

1. **JIT optimization**: JIT compiles based on runtime profile. Under dev load, different methods are hot, so JIT inlines and optimizes different code paths. In prod, under real traffic patterns, inlining decisions differ — what's hot in dev may not be hot in prod and vice versa.

2. **GC pressure**: Dev usually runs with smaller heap and less allocation, so GC behavior is different. You might not see the GC CPU in dev that's consuming 30% in prod.

3. **Thread count and contention**: Dev runs fewer threads. Lock contention issues only manifest at production concurrency levels. A `synchronized` block that's never contested in dev might be a serial bottleneck with 200 production threads.

4. **Data characteristics**: Prod data may have pathological cases dev data doesn't — e.g., very long strings that blow up regex backtracking, or a very popular cache key that causes contention.

5. **ClassLoader and reflection warmup**: In prod with thousands of loaded classes, class lookup is slower. In dev with a sparse classpath, it's trivial.

Conclusion: profile in prod, use async-profiler with its low overhead to make it safe. If absolutely impossible, load-test staging with production-like data and concurrency.

---

### Trap 5: "Fix the Hottest Method First"

**Q:** "The flame graph shows `computeHash()` taking 60% of CPU. Start there."

**TRAP:** The hottest method isn't always where the fix lives.

**Correct answer:**

You need to distinguish between two causes of a method appearing hot:

1. **The method is inherently expensive** — it does too much work per call. Fix: optimize the algorithm, cache results, use a faster implementation.

2. **The method is called too often** — each call is fast, but it's called millions of times unnecessarily. Fix: reduce call frequency, add caching at the caller, batch calls.

The flame graph tells you a method is hot, but not which case applies. You need to check:

- **Call count**: Use async-profiler's `-e itimer` mode or Arthas `monitor` to get invocations per second.
- **Per-call duration**: If `computeHash()` takes 1µs but is called 60M times per second, that's a call frequency problem. Caching the hash result in the key object would be the fix.
- **Caller context**: Who is calling `computeHash()` this often? Go up the flame graph to find the caller — maybe it's `HashMap.containsKey()` inside a hot loop that could use `computeIfAbsent()` pattern with a pre-stored key.

Optimizing the hash function itself when the real problem is redundant calls would be wasted effort.

---

### Trap 6: "async-profiler Is Always Safe — Max It Out"

**Q:** "Since async-profiler has low overhead, I'll profile at 10000 samples/sec for 10 minutes in prod."

**TRAP:** async-profiler overhead scales with sampling frequency and duration. Defaults are usually fine; pushing limits isn't.

**Correct answer:**

The default sampling interval for async-profiler is **10ms** (100 samples/sec). At this rate, overhead is <1-3%. But:

- Increasing to 1000 samples/sec (1ms interval) increases overhead and OS signal delivery frequency — can interfere with application timing, especially for latency-sensitive services.
- 10 minutes of profiling generates a large SVG (potentially 50-100MB) that can be slow to analyze and takes memory to hold in the JVM.
- Wall-clock mode (`-e wall`) profiles ALL threads including I/O-blocked ones — generates far more data than CPU mode and should be time-limited.

Safe production defaults:
```bash
# CPU profiling: 30-60 seconds, default interval, HTML output
./profiler.sh -e cpu -d 60 -f /tmp/cpu.html <pid>

# Allocation profiling: 30 seconds, reduced detail
./profiler.sh -e alloc -d 30 -f /tmp/alloc.html <pid>

# Wall-clock: shorter duration due to data volume
./profiler.sh -e wall -d 15 -f /tmp/wall.html <pid>
```

Always test the profiling command in staging first. Be aware that `perf_events` require kernel capabilities — in containers you may need `--privileged` or the `SYS_ADMIN` capability, which has security implications.

---

## 6. Command Examples & Java Code

### async-profiler Commands

```bash
# Download and set up async-profiler
wget https://github.com/async-profiler/async-profiler/releases/latest/download/async-profiler-linux-x64.zip
unzip async-profiler-linux-x64.zip

# CPU profiling — 30s, interactive HTML flame graph
./profiler.sh -e cpu -d 30 -f /tmp/cpu-profile.html <pid>

# Allocation profiling
./profiler.sh -e alloc -d 30 -f /tmp/alloc-profile.html <pid>

# Wall-clock profiling (all threads, including I/O waiting)
./profiler.sh -e wall -d 30 -f /tmp/wall-profile.html <pid>

# Lock/contention profiling
./profiler.sh -e lock -d 30 -f /tmp/lock-profile.html <pid>

# Collapsed stack output (for differential flame graphs)
./profiler.sh -e cpu -d 60 -o collapsed -f /tmp/stacks.txt <pid>
```

---

### JFR Commands

```bash
# Start recording on JVM startup (always-on, circular buffer)
java -XX:StartFlightRecording=dumponexit=true,filename=/tmp/app.jfr \
     -jar myapp.jar

# Start JFR on running JVM
jcmd <pid> JFR.start duration=120s filename=/tmp/recording.jfr

# Start always-on circular buffer (no end time — dump manually)
jcmd <pid> JFR.start name=continuous settings=profile maxage=5m maxsize=100m

# Dump current circular buffer
jcmd <pid> JFR.dump name=continuous filename=/tmp/snapshot.jfr

# Check active recordings
jcmd <pid> JFR.check

# Stop a named recording
jcmd <pid> JFR.stop name=continuous
```

---

### Arthas Live Profiling

```bash
# Start Arthas (download from arthas.aliyun.com)
java -jar arthas-boot.jar <pid>

# Trace method execution with timing breakdown
trace com.myapp.service.OrderService processOrder

# Monitor method call rate, avg time, failures
monitor com.myapp.service.OrderService processOrder -c 5

# CPU sampling (uses async-profiler internally)
profiler start --event cpu
profiler stop --file /tmp/arthas-cpu.html

# Watch method args/return values
watch com.myapp.service.OrderService processOrder '{args, returnObj}' -n 3
```

---

### JFR Custom Events (Java Code)

```java
import jdk.jfr.*;

@Label("Order Processing")
@Category("Business Logic")
@Description("Tracks order processing time")
public class OrderProcessingEvent extends Event {
    @Label("Order ID")
    public String orderId;

    @Label("Item Count")
    public int itemCount;
}

// Usage
public Order processOrder(String orderId) {
    OrderProcessingEvent event = new OrderProcessingEvent();
    event.begin();
    event.orderId = orderId;
    try {
        Order order = doProcessOrder(orderId);
        event.itemCount = order.getItems().size();
        return order;
    } finally {
        event.commit(); // visible in JFR recording
    }
}
```

---

### Diagnosing Safepoint Bias (Java Code That Confuses JVMTI)

```java
// This tight loop has no safepoint poll in Java 8 (counted loop optimization)
// JVMTI profilers may report 0 samples here despite 100% CPU usage
public long tightLoop(long iterations) {
    long sum = 0;
    for (long i = 0; i < iterations; i++) {
        sum += i; // no object allocation, no method call = no safepoint
    }
    return sum;
}

// Fix for diagnostic clarity: break out of counted loop to insert safepoint check
// Or use -XX:+UseCountedLoopSafepoints (JDK 9+)
```

```bash
# JVM flag to insert safepoints in counted loops (JDK 9+)
java -XX:+UseCountedLoopSafepoints -jar myapp.jar
```

---

### Pattern Caching Fix

```java
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Pattern;

// Anti-pattern: compile per call
public boolean isValid(String input, String regex) {
    return input.matches(regex); // String.matches() compiles every time
}

// Fixed: cache compiled patterns
private static final ConcurrentHashMap<String, Pattern> PATTERN_CACHE =
        new ConcurrentHashMap<>();

public boolean isValid(String input, String regex) {
    Pattern p = PATTERN_CACHE.computeIfAbsent(regex, Pattern::compile);
    return p.matcher(input).matches();
}
```

---

### Reading JFR Programmatically (Java 14+ API)

```java
import jdk.jfr.consumer.*;

Path recording = Path.of("/tmp/recording.jfr");
try (RecordingFile rf = new RecordingFile(recording)) {
    while (rf.hasMoreEvents()) {
        RecordedEvent event = rf.readEvent();
        if (event.getEventType().getName().equals("jdk.CPULoad")) {
            float jvmUser = event.getFloat("jvmUser");
            System.out.printf("JVM CPU user: %.1f%%%n", jvmUser * 100);
        }
    }
}
```

---

## 7. Flame Graph Reading Guide

### How to Read a Flame Graph in 5 Steps

```
Step 1 — Orient yourself
   Bottom = root frames (main, thread-run, framework entry points)
   Top = leaf frames (where CPU actually is)
   
Step 2 — Find the widest bars at the top (plateaus)
   A "plateau" = wide bar with narrow or no children above it
   This is where self-time accumulates = your hot method
   
Step 3 — Follow the stack upward from hot methods
   Who called the hot method? Follow the chain down (visually)
   to understand the execution context

Step 4 — Identify patterns
   Many thin bars side by side = many methods called briefly = diverse work
   One wide bar = single hot method = clear target
   Wide bar at framework level = framework overhead = harder to fix
   
Step 5 — Check call frequency vs per-call cost
   Wide bar high up = hot method called often OR expensive per call
   Use monitor/profiler command to get call count before optimizing
```

### Common Flame Graph Patterns

```
PATTERN 1 — Single Hot Method (Easy Win)
┌──────────────────────────────────────────────┐
│                 HTTP Dispatcher               │
│    ┌──────────────────────────────────┐       │
│    │       OrderController.handle     │       │
│    │    ┌─────────────────────┐       │       │
│    │    │  Pattern.compile()  │       │       │  ← Fix: cache Pattern
│    │    │  [plateau - wide]   │       │       │
│    │    └─────────────────────┘       │       │
│    └──────────────────────────────────┘       │
└──────────────────────────────────────────────┘

PATTERN 2 — GC Consuming CPU (Don't Touch App Code)
┌──────────────────────────────────────────────┐
│  GCTaskThread  │  GCTaskThread  │  App Thread │  ← GC threads wide
│  [G1 Mixed GC] │  [G1 Mixed GC] │  [normal]  │
│  [very wide]   │  [very wide]   │             │
└──────────────────────────────────────────────┘
   Fix: heap tuning, reduce allocation, not app code optimization

PATTERN 3 — Framework Overhead (Hard to Fix Directly)
┌──────────────────────────────────────────────┐
│           Jackson ObjectMapper                │  ← very wide
│  ┌────────────────────────────────────────┐  │
│  │   DeserializationContext.handleUnknown │  │  ← Consider reuse
│  │   ClassIntrospector.findProperties     │  │    ObjectMapper
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘

PATTERN 4 — Thread Contention (Lock Spinning)
┌──────────────────────────────────────────────┐
│ Thread-1: synchronized block [RUNNABLE]       │
│ Thread-2: synchronized block [RUNNABLE]       │  ← Many threads
│ Thread-3: synchronized block [RUNNABLE]       │    same method
│ Thread-N: synchronized block [RUNNABLE]       │
└──────────────────────────────────────────────┘
   All in RUNNABLE but not progressing = spin wait
   Fix: reduce lock scope, use ConcurrentHashMap, reduce contention
```

---

## 8. Interview Cheat Sheet

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║                    CPU PROFILING INTERVIEW CHEAT SHEET                         ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  TOOL SELECTION                                                                ║
║  ─────────────────────────────────────────────────────────────────────────     ║
║  async-profiler  → Production CPU/alloc/lock profiling, <3% overhead          ║
║  JFR             → Always-on observability, JDK built-in, circular buffer      ║
║  JMC             → Analyze .jfr files, GUI with CPU/GC/IO views               ║
║  Arthas          → Live surgical inspection, no restart needed                 ║
║  jstack          → Poor-man's profiler, thread dump analysis                   ║
║  jstat           → GC activity, heap utilization at glance                     ║
║  AVOID: JVisualVM CPU profiling in prod (safepoint bias, high overhead)        ║
║                                                                                ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  TRIAGE ORDER FOR HIGH CPU                                                     ║
║  ─────────────────────────────────────────────────────────────────────────     ║
║  1. top -H -p <pid>          → which threads are hot                          ║
║  2. jstat -gcutil <pid> 1000 → is it GC? (check before profiling app code)    ║
║  3. jstack <pid> x3          → RUNNABLE threads, same stack = spin             ║
║  4. async-profiler cpu       → flame graph for app CPU                        ║
║  5. async-profiler alloc     → if GC is hot, find allocation source           ║
║  6. jcmd JFR.dump            → if JFR running, get full picture               ║
║                                                                                ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  KEY ASYNC-PROFILER COMMANDS                                                   ║
║  ─────────────────────────────────────────────────────────────────────────     ║
║  CPU:    ./profiler.sh -e cpu   -d 30 -f cpu.html   <pid>                     ║
║  Alloc:  ./profiler.sh -e alloc -d 30 -f alloc.html <pid>                     ║
║  Wall:   ./profiler.sh -e wall  -d 30 -f wall.html  <pid>                     ║
║  Lock:   ./profiler.sh -e lock  -d 30 -f lock.html  <pid>                     ║
║  Diff:   ./profiler.sh -e cpu -o collapsed -f stacks.txt <pid>                ║
║                                                                                ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  KEY JFR COMMANDS                                                              ║
║  ─────────────────────────────────────────────────────────────────────────     ║
║  Startup:  -XX:StartFlightRecording=dumponexit=true,filename=app.jfr          ║
║  Start:    jcmd <pid> JFR.start duration=120s filename=rec.jfr                ║
║  Always-on: jcmd <pid> JFR.start name=cont settings=profile maxage=5m         ║
║  Dump:     jcmd <pid> JFR.dump name=cont filename=snap.jfr                    ║
║  Check:    jcmd <pid> JFR.check                                               ║
║                                                                                ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  FLAME GRAPH RULES                                                             ║
║  ─────────────────────────────────────────────────────────────────────────     ║
║  X-axis = SAMPLE COUNT proportion (not time order — alphabetical sort)        ║
║  Y-axis = call stack depth (bottom = root, top = leaf / hot code)             ║
║  Width   = time proportion on CPU (wider = hotter)                            ║
║  Plateau = wide top bar with no children = self-time = your target            ║
║  Color   = arbitrary, no meaning by default                                    ║
║                                                                                ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  COMMON HOT-PATH ANTI-PATTERNS                                                 ║
║  ─────────────────────────────────────────────────────────────────────────     ║
║  Pattern.compile() per request       → static final Pattern                   ║
║  String.format() in tight loop       → StringBuilder                          ║
║  new ObjectMapper() per call         → singleton / @Bean                      ║
║  Method reflection without caching   → cache Method objects                   ║
║  HashMap with O(n) hashCode          → use identifier-based key               ║
║  while(!done){} spin loop            → LockSupport.parkNanos / sleep           ║
║  new ArrayList() in hot path         → pool or pre-size                       ║
║                                                                                ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  TRAP ANSWERS — WHAT TO SAY                                                    ║
║  ─────────────────────────────────────────────────────────────────────────     ║
║  "100% CPU = infinite loop"   → NO: GC CPU, JIT warmup, thread saturation     ║
║  "JVisualVM is fine for prod" → NO: safepoint bias, high overhead              ║
║  "X-axis = time order"        → NO: alphabetical sort, width = sample count   ║
║  "Dev profile = prod profile" → NO: different JIT, load, data, threads        ║
║  "Fix the hottest method"     → NO: check if it's call frequency or cost      ║
║  "Profile at max sample rate" → NO: overhead scales, use defaults (100/s)     ║
║                                                                                ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  SAFEPOINT BIAS SUMMARY                                                        ║
║  ─────────────────────────────────────────────────────────────────────────     ║
║  Problem: JVMTI can only sample at safepoints                                 ║
║  Effect:  Tight loops (no safepoint poll) = invisible to JVisualVM            ║
║  Fix:     async-profiler uses AsyncGetCallTrace + perf_events (no safepoint)  ║
║  JVM Fix: -XX:+UseCountedLoopSafepoints (inserts polls in counted loops)      ║
║                                                                                ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║  PRODUCTION SAFETY CHECKLIST                                                   ║
║  ─────────────────────────────────────────────────────────────────────────     ║
║  [ ] Use async-profiler, not JVisualVM                                        ║
║  [ ] Default sampling rate (10ms / 100 samples/sec)                           ║
║  [ ] Duration 30-60 seconds maximum                                           ║
║  [ ] Test profiler command in staging first                                   ║
║  [ ] Check container needs SYS_ADMIN for perf_events                          ║
║  [ ] Have JFR always-on with circular buffer for zero-overhead baseline       ║
║  [ ] Arthas only in maintenance windows for live inspection                   ║
║                                                                                ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## 9. Quick Reference: Profiling Decision Tree

```
HIGH CPU ALERT
     │
     ▼
Is it GC threads?  ──YES──► Fix heap/allocation, not app code
     │                       jstat -gcutil / GC logs
     NO
     │
     ▼
Are threads making progress?
     │
    YES ──► High load, legitimate work
     │      Check if scale-out needed
     │
     NO
     │
     ▼
Same thread stack across jstack dumps?
     │
    YES ──► Spin loop or blocking retry
     │      Add backoff / proper wait
     │
     NO
     │
     ▼
Run async-profiler CPU mode (30s)
     │
     ▼
Read flame graph — find plateau
     │
     ▼
Is the hot method called too often?  ──YES──► Add caching / reduce call frequency
     │
     NO
     │
     ▼
Is the hot method doing too much?    ──YES──► Optimize algorithm / use faster lib
     │
     NO
     │
     ▼
Is it framework overhead?            ──YES──► ObjectMapper singleton, connection pool
     │                                        framework config tuning
     NO
     │
     ▼
Is it JIT deoptimization?            ──YES──► Check JFR deoptimization events
                                              Avoid dynamic class loading in hot path
```

---

## 10. Additional Notes for Interviewer Follow-Ups

### On Memory vs CPU Profiling

Interviewers sometimes conflate memory and CPU issues. Key distinction:

- **CPU profiling** shows what code runs most — sampling stack traces while threads are on-CPU
- **Memory/allocation profiling** shows what code allocates most — sampling object allocation events
- Both can cause high CPU: allocation pressure drives GC, and GC uses CPU. Always check allocation if GC is the CPU consumer.

### On Production Observability Strategy

A mature answer for a 15-YOE architect:

"We run always-on JFR with circular buffer on all services. No overhead, continuous data. When an incident occurs, I dump the last 5 minutes of JFR data — it has CPU, allocation, lock contention, and any custom business events I've instrumented. For targeted profiling during an active incident, async-profiler for 30-60 seconds. For live surgical inspection during a maintenance window, Arthas. We never need to restart a service to diagnose it."

### On Async/Virtual Threads (Java 21+)

With Project Loom virtual threads, the profiling model shifts:

- Platform threads (OS threads) still profile normally
- Virtual threads are JVM-managed — when a virtual thread parks (I/O wait), it unmounts from its carrier thread
- async-profiler 3.x+ supports virtual thread profiling: each virtual thread gets its own stack trace even when parked
- JFR has `VirtualThreadPinned` event that fires when a virtual thread is pinned to its carrier (can't unmount) — important to monitor as it reduces scalability

```bash
# async-profiler 3.x virtual thread support
./profiler.sh -e cpu --features vtid -d 30 -f vt-profile.html <pid>
```

---

*File created for 15-YOE Java Architect interview preparation.*  
*Topics: async-profiler, JFR, flame graphs, safepoint bias, production CPU diagnosis.*
