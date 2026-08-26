# Java Memory Leaks — End-to-End Production Incident Interview Guide
### Target: 15-YOE Java Architect | Senior/Staff/Principal Level

---

## 1. Big Picture: Memory Leak Investigation Workflow

```
SYMPTOMS DETECTED
       |
       v
+-------------------------------+
|  Heap usage trending up       |
|  GC time > 10% of CPU         |
|  OOM errors in logs           |
|  App slowdown under load      |
|  Metaspace OOM on redeploy    |
+-------------------------------+
       |
       v
TRIAGE: Is it actually a leak?
  - GC not run yet? (no pressure)   ---> Wait / trigger GC via jcmd
  - Legitimate data growth?         ---> Check business load
  - Cache without eviction?         ---> Check cache config
       |
       v
+-------------------------------+
|    HEAP PROFILING               |
|  jstat -gcutil <pid> 5s         |
|  jcmd <pid> GC.run              |
|  jmap -histo:live <pid>         |
|  Take heap dump:                |
|    jcmd <pid> GC.heap_dump file |
|    -XX:+HeapDumpOnOutOfMemory   |
+-------------------------------+
       |
       v
+-------------------------------+
|    HEAP DUMP ANALYSIS           |
|  Eclipse MAT / VisualVM         |
|  - Dominator tree               |
|  - Leak suspects report         |
|  - Retained heap by class       |
|  - GC root path                 |
+-------------------------------+
       |
       v
ROOT CAUSE IDENTIFICATION
  +------------------+------------------+------------------+
  |  Static fields   |  ThreadLocal     |  Classloader     |
  |  holding refs    |  not removed     |  not released    |
  +------------------+------------------+------------------+
  |  Unclosed res    |  Cache no evict  |  Inner class ref |
  +------------------+------------------+------------------+
  |  Hibernate leak  |  String.intern   |  Future chain    |
  +------------------+------------------+------------------+
       |
       v
+-------------------------------+
|    FIX & DEPLOY                 |
|  Code change                    |
|  Config change                  |
|  JVM flags tuned                |
+-------------------------------+
       |
       v
+-------------------------------+
|    VERIFY                       |
|  Heap trend flat post-GC        |
|  GC overhead < 5%               |
|  No OOM after soak test         |
|  Metaspace stable on redeploy   |
+-------------------------------+
```

---

## 2. Conversational Interview Script — Real Production Incident

**Interviewer:** Walk me through a real memory leak investigation you led.

**Architect (15 YOE voice):**

Sure. This was about three years ago on a high-throughput order processing service — Spring Boot 2, Hibernate 5, running on Kubernetes with a 4GB heap. We started getting PagerDuty alerts at around 2 AM on a Tuesday — pods were OOMKilled roughly every six hours. The restart masked it for a while because K8s just brought the pod back up, so the team had been dismissing it as "transient." When I joined the incident I immediately said: stop restarting — let one pod stay up and get a heap dump before it dies.

**First thing I did: confirm the symptom is actually a leak.**

I ran `jstat -gcutil <pid> 10s` and watched Old Gen — it was at 92% and climbing. After a `jcmd <pid> GC.run` Full GC, it dropped to 78%, then crept back up over the next hour. That pattern — post-GC floor keeps rising — is the telltale sign of a true leak. If it had leveled off after GC, I'd suspect cache or legitimate data growth.

**Heap dump analysis.**

I triggered a dump with `-XX:+HeapDumpOnOutOfMemoryError` already set, waited for the OOM, pulled the dump to my laptop, and opened it in Eclipse MAT. The Leak Suspects report immediately flagged a `java.util.HashMap` inside a class called `AuditContextHolder` that was holding 1.4 GB — which was 80% of retained heap. The dominator tree showed the path: `AuditContextHolder.contextMap` → `HashMap<String, AuditEntry>` → every request ever processed.

**Root cause.**

`AuditContextHolder` had a static `HashMap<String, AuditEntry>` that was being populated on every request with a request ID key and the full audit object as value. No eviction, no TTL, no removal. Someone had added it six months earlier for "debugging convenience" and it slipped through code review. Each `AuditEntry` itself held a reference to the full `HttpServletRequest` snapshot — so we were retaining full request payloads indefinitely.

**The fix.**

Two changes. One: replaced the static HashMap with a Guava `Cache` with `maximumSize(10_000)` and `expireAfterWrite(30, MINUTES)`. Two: added a Servlet filter that explicitly called `AuditContextHolder.clear()` in a `finally` block on every request. Deployed. Heap trend went flat. We ran a 24-hour soak test at 2x production load — no OOM, Old Gen stable at ~40% post-GC.

**Retrospective actions.**

We added a heap monitoring alert at 70% Old Gen post-GC (not just absolute usage). We added an ArchUnit rule that flags any static mutable collection. And we added static analysis via SpotBugs to the CI pipeline.

---

## 3. Scenario Q&As — Specific Java Memory Leak Patterns

### Q1: Static Collections Leak

**Q:** Your service leaks memory through a static Map. Show the bug and fix.

**A:**

Buggy code:
```java
// LEAK: static map, never cleared
public class EventBus {
    private static final Map<String, List<EventListener>> listeners =
        new HashMap<>();

    public static void register(String event, EventListener l) {
        listeners.computeIfAbsent(event, k -> new ArrayList<>()).add(l);
    }
    // No deregister method — listeners accumulate forever
}
```

Why it leaks: `listeners` is a GC root. Every registered listener object and all objects it transitively references are reachable forever. In a web app, if listeners are registered per-request and never removed, this grows unbounded.

Fix:
```java
public class EventBus {
    private static final Map<String, List<WeakReference<EventListener>>> listeners =
        new ConcurrentHashMap<>();

    public static void register(String event, EventListener l) {
        listeners.computeIfAbsent(event, k -> new CopyOnWriteArrayList<>())
                 .add(new WeakReference<>(l));
    }

    public static void deregister(String event, EventListener l) {
        List<WeakReference<EventListener>> list = listeners.get(event);
        if (list != null) list.removeIf(ref -> ref.get() == null || ref.get() == l);
    }
}
```

Better: use `WeakReference` for listeners AND provide an explicit `deregister`. The WeakReference lets the GC collect listeners whose owners are gone, but the deregister is the clean path.

---

### Q2: ThreadLocal Leak in Thread Pool

**Q:** Explain how ThreadLocal causes a memory leak in a thread pool and how to fix it.

**A:**

Buggy code:
```java
public class RequestContext {
    // LEAK: ThreadLocal in a pooled-thread environment
    private static final ThreadLocal<UserSession> session = new ThreadLocal<>();

    public static void set(UserSession s) { session.set(s); }
    public static UserSession get() { return session.get(); }
    // No remove() called after request ends
}
```

Why it leaks: Thread pool threads are reused. ThreadLocal values survive request boundaries. After request 1, the `UserSession` object sits in the thread's `ThreadLocalMap` forever (until that thread is reused and the value overwritten, or the thread dies — which in a pool may be never). Each entry in `ThreadLocalMap` is keyed by a `WeakReference` to the ThreadLocal itself, but the value is a strong reference. So even if the `ThreadLocal` field is GC'd, the value `UserSession` remains reachable.

Fix:
```java
// In a Servlet Filter or Spring HandlerInterceptor:
try {
    RequestContext.set(buildSession(request));
    chain.doFilter(request, response);
} finally {
    RequestContext.remove(); // CRITICAL: always remove in finally
}
```

In Spring: use `HandlerInterceptorAdapter.afterCompletion` to call `ThreadLocal.remove()`.

---

### Q3: Classloader Leak on Redeployment

**Q:** A Tomcat app leaks Metaspace on every hot redeploy. Why? How do you diagnose and fix?

**A:**

The root cause is a classloader leak. When you redeploy a web app, Tomcat creates a new `WebAppClassLoader` for the new version and discards the old one. For the old classloader to be GC'd, nothing in the JVM's parent classloaders or static state can hold a reference to it or any class loaded by it.

Common culprits:

1. JDBC driver registration: `DriverManager` is in the bootstrap classloader. When your app loads a JDBC driver (e.g., MySQL's `com.mysql.jdbc.Driver`), `DriverManager` holds a reference to that driver instance, which is loaded by the app classloader. The app classloader can never be GC'd.

Fix:
```java
// In ServletContextListener.contextDestroyed:
@Override
public void contextDestroyed(ServletContextEvent sce) {
    Enumeration<Driver> drivers = DriverManager.getDrivers();
    while (drivers.hasMoreElements()) {
        Driver driver = drivers.nextElement();
        if (driver.getClass().getClassLoader() == getClass().getClassLoader()) {
            try { DriverManager.deregisterDriver(driver); }
            catch (SQLException e) { log.warn("Driver deregister failed", e); }
        }
    }
    // Also stop any background threads started by your app
}
```

2. Static references in library singletons (e.g., log4j MDC, EhCache) that hold references to web-app classes.

Diagnosis: take two heap dumps — one before redeploy, one after. In MAT, compare. If `WebAppClassLoader` instances keep accumulating, you have a classloader leak.

---

### Q4: Unclosed Resources

**Q:** Show a subtle resource leak that `finally` does not fully prevent.

**A:**

Buggy code (pre try-with-resources):
```java
// LEAK: if new FileInputStream throws, fis is null and finally NPEs
public void process(String path) throws IOException {
    FileInputStream fis = null;
    try {
        fis = new FileInputStream(path); // might throw
        // ... process ...
    } finally {
        fis.close(); // NullPointerException if constructor threw!
    }
}
```

Slightly better but still subtle:
```java
finally {
    if (fis != null) fis.close(); // NPE avoided, but close() can throw
    // If close() throws, that exception masks the original exception
}
```

Fix — Java 7+ try-with-resources:
```java
public void process(String path) throws IOException {
    try (FileInputStream fis = new FileInputStream(path)) {
        // ... process — fis.close() always called, exception properly suppressed
    }
}
```

For JDBC specifically:
```java
// LEAK: statement and connection not closed on exception paths
try (Connection conn = dataSource.getConnection();
     PreparedStatement ps = conn.prepareStatement(SQL);
     ResultSet rs = ps.executeQuery()) {
    while (rs.next()) { /* ... */ }
} // ALL three closed in reverse order automatically
```

---

### Q5: Cache Without Eviction

**Q:** Your caching layer is growing unbounded. Show the Guava/Caffeine mistake and fix.

**A:**

Buggy code:
```java
// LEAK: no size limit, no expiry — this is just a HashMap with extra steps
private final Cache<String, ProductDetails> cache =
    CacheBuilder.newBuilder().build(); // Guava, no bounds
```

Also leaks with Caffeine:
```java
private final Cache<String, byte[]> imageCache =
    Caffeine.newBuilder().build(); // no maximumSize, no expiry
```

Fix:
```java
private final Cache<String, ProductDetails> cache =
    Caffeine.newBuilder()
        .maximumSize(50_000)               // cap by entry count
        .expireAfterWrite(10, TimeUnit.MINUTES)
        .expireAfterAccess(5, TimeUnit.MINUTES)
        .recordStats()                     // expose hit rate to metrics
        .build();
```

For large values (byte arrays), bound by weight not count:
```java
private final Cache<String, byte[]> imageCache =
    Caffeine.newBuilder()
        .maximumWeight(256 * 1024 * 1024)  // 256 MB total
        .weigher((key, value) -> ((byte[]) value).length)
        .expireAfterWrite(30, TimeUnit.MINUTES)
        .build();
```

Architect note: always expose cache stats to Prometheus — `cache.stats().hitRate()`. A hit rate below 20% with a large cache is a red flag (you're caching but not benefiting, just retaining).

---

### Q6: Inner Class / Anonymous Class Holding Outer Reference

**Q:** How can an anonymous Runnable submitted to a thread pool cause a memory leak?

**A:**

Buggy code:
```java
public class OrderService {
    private final List<Order> pendingOrders = new ArrayList<>(); // large list

    public void scheduleNotification(String orderId) {
        // LEAK: anonymous Runnable implicitly holds 'this' (OrderService instance)
        executor.submit(new Runnable() {
            @Override
            public void run() {
                // only uses orderId, but 'this$0' (OrderService) is captured
                notificationService.send(orderId);
            }
        });
    }
}
```

The anonymous `Runnable` holds an implicit strong reference to the enclosing `OrderService` instance (`this$0`). As long as that Runnable is queued or running in the executor, the entire `OrderService` — including `pendingOrders` — is reachable.

Fix — use a static nested class or lambda capturing only what's needed:
```java
// Lambda captures only orderId (String), not 'this'
public void scheduleNotification(String orderId) {
    executor.submit(() -> notificationService.send(orderId));
}

// Or explicit static class
private static class NotificationTask implements Runnable {
    private final String orderId;
    private final NotificationService svc;
    NotificationTask(String id, NotificationService svc) {
        this.orderId = id; this.svc = svc;
    }
    @Override public void run() { svc.send(orderId); }
}
```

---

### Q7: Hibernate / JPA EntityManager Leak

**Q:** Describe how an EntityManager can leak and what the heap dump would show.

**A:**

Buggy code:
```java
@Service
public class ProductRepository {
    @PersistenceUnit
    private EntityManagerFactory emf;

    public Product findById(Long id) {
        EntityManager em = emf.createEntityManager(); // LEAK: never closed
        return em.find(Product.class, id);
        // em.close() missing — first-level cache (persistence context) stays live
    }
}
```

Why it leaks: Each EntityManager has a first-level cache (persistence context) that holds all loaded entities. If the EM is never closed, all those entity objects remain reachable. In a long-running service or batch job, this can balloon.

Secondary leak — L2 cache misconfiguration: if EhCache or Infinispan L2 cache is configured without a TTL or max entries, every loaded entity accumulates.

Fix:
```java
public Product findById(Long id) {
    try (EntityManager em = emf.createEntityManager()) { // Java 7+, EM is AutoCloseable
        return em.find(Product.class, id);
    }
}
```

In Spring: use `@Transactional` with `@PersistenceContext` (Spring manages EM lifecycle) or a `JpaRepository` — never create EntityManagers manually unless you close them.

L2 cache fix (persistence.xml / application.properties):
```properties
spring.jpa.properties.hibernate.cache.use_second_level_cache=true
spring.jpa.properties.hibernate.cache.region.factory_class=jcache
# In ehcache.xml: add maxEntriesLocalHeap and timeToLiveSeconds to all regions
```

---

### Q8: String.intern() Abuse

**Q:** What happens when you call `String.intern()` on user-supplied data at scale?

**A:**

Buggy code:
```java
public class SessionManager {
    private final Map<String, Session> sessions = new HashMap<>();

    public void register(String userId, Session session) {
        // LEAK: interning arbitrary user IDs fills the String pool forever
        sessions.put(userId.intern(), session);
    }
}
```

In Java 7 and earlier: `String.intern()` stored strings in PermGen (method area), which has a fixed size. With millions of unique user IDs (UUIDs, hashed tokens), PermGen fills up: `java.lang.OutOfMemoryError: PermGen space`.

In Java 8+: String pool is in the heap (not Metaspace), but it is still a permanent interning pool — interned strings are GC roots and are only collected when the JVM has aggressive GC pressure. With unique strings, you get unbounded growth in the heap.

Fix: never intern untrusted or high-cardinality user input.
```java
// No intern() — HashMap handles equality via equals() just fine
sessions.put(userId, session);
```

Use `intern()` only for a small, known, finite set of strings (e.g., a fixed set of status codes you compare frequently). Even then, consider `enum` instead.

---

### Q9: DOM Parsing Large XML

**Q:** Why does parsing a 500MB XML file with DocumentBuilder cause an OOM?

**A:**

Buggy code:
```java
public Document parse(InputStream xml) throws Exception {
    // LEAK: loads the ENTIRE document tree into memory at once
    DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
    DocumentBuilder builder = factory.newDocumentBuilder();
    return builder.parse(xml); // 500MB file → easily 3-5x in memory as DOM
}
```

Why it leaks: DOM parsing builds a complete in-memory tree. A 500MB XML can require 1.5–3 GB of heap for the DOM (due to Java object overhead per node — element, attribute, text node each carry ~100-200 bytes of JVM overhead).

Fix — use SAX or StAX for streaming:
```java
// StAX streaming: only current element in memory at once
public void processLargeXml(InputStream xml) throws Exception {
    XMLInputFactory factory = XMLInputFactory.newInstance();
    XMLStreamReader reader = factory.createXMLStreamReader(xml);
    while (reader.hasNext()) {
        int event = reader.next();
        if (event == XMLStreamConstants.START_ELEMENT) {
            handleElement(reader.getLocalName(), reader);
        }
    }
    reader.close();
}
```

For very large files that must be processed as DOM, split into chunks with a SAX-based splitter, or use VTD-XML which provides random access without full in-memory tree.

---

### Q10: CompletableFuture Chain Leak

**Q:** How can CompletableFuture chains cause memory leaks?

**A:**

Buggy code:
```java
public class DataPipeline {
    private final List<CompletableFuture<?>> activeFutures = new ArrayList<>();

    public void process(String input) {
        CompletableFuture<String> future = CompletableFuture
            .supplyAsync(() -> fetch(input))
            .thenApply(this::transform)
            .thenAccept(this::store);
        activeFutures.add(future); // LEAK: never removed, even after completion
    }
}
```

Why it leaks: `activeFutures` holds strong references to every CompletableFuture ever created. Even completed futures retain their result value and the chain of dependent stages until GC'd. With high throughput, thousands of completed futures accumulate.

Second form: futures that are never completed:
```java
// If a future in the chain is never completed (e.g., timeout not handled),
// all downstream stages and their captured lambdas remain reachable indefinitely
CompletableFuture<String> upstream = new CompletableFuture<>();
upstream.thenApply(s -> expensiveObject); // expensiveObject never released
// If nobody calls upstream.complete() or upstream.cancel(), this leaks
```

Fix:
```java
public void process(String input) {
    CompletableFuture
        .supplyAsync(() -> fetch(input))
        .thenApply(this::transform)
        .thenAccept(this::store)
        .orTimeout(30, TimeUnit.SECONDS)      // always set timeout
        .exceptionally(ex -> { log.error("Pipeline failed", ex); return null; });
    // Don't retain reference unless you need to cancel it
}
```

If you need to track active work for cancellation, use a `Set` with a removal callback:
```java
future.whenComplete((r, ex) -> activeFutures.remove(future));
```

---

## 4. Advanced Scenario Q&As

### AQ1: Heap Dump Shows No Single Large Object — Distributed Leak

**Q:** Your MAT dump shows nothing unusual in the leak suspects report. Old Gen is 80% full. No single object dominates. What next?

**A:**

This is a distributed leak — many small objects, each modest, but in aggregate consuming the heap. MAT's Leak Suspects report looks for single large retained heaps; it misses this.

Steps:
1. In MAT: run "Histogram" sorted by "Retained Heap." Look at the top 20 classes — you're looking for something unexpectedly high-count (e.g., 2 million `HashMap$Entry` objects).
2. Use "Group by class" in the dominator tree. If `String` shows 800MB, drill into who holds those strings.
3. Run an OQL query:
   ```
   SELECT s FROM java.util.HashMap s WHERE s.size > 100000
   ```
   This finds all HashMaps with more than 100K entries — a data anomaly, not a leak by one class.
4. Check thread stacks in the dump — sometimes the leak is in a thread-local variable spread across every thread.
5. Consider a second dump 30 minutes later and use MAT's "Compare Snapshots" — the delta report shows which classes grew, even if none is dominant in absolute terms.

---

### AQ2: Metaspace OOM vs. Heap OOM — Triage Difference

**Q:** You see `OutOfMemoryError: Metaspace` in production. Walk through your triage.

**A:**

Metaspace stores class metadata. The two main causes:

1. **Classloader leak** (most common in web apps): old classloaders not GC'd on redeploy (described in Q3). Symptom: Metaspace grows by ~X MB on each redeploy, never released.

Diagnosis:
```bash
jcmd <pid> VM.classloaders      # lists classloaders and class counts
jcmd <pid> GC.heap_info         # check Metaspace committed vs. reserved
```

In MAT: search for `ClassLoader` instances. If you see 15 `WebAppClassLoader` instances after 15 redeploys, that's the leak.

2. **Dynamic class generation**: frameworks that generate proxy classes (CGLIB, Javassist, Byte-Buddy) can generate new classes on every request if misconfigured — e.g., creating a new `ProxyFactory` per request instead of reusing cached proxies.

Fix for dynamic generation: ensure proxy/enhancer caches are per-class not per-request:
```java
// WRONG: new ProxyFactory every call generates new class in Metaspace
ProxyFactory factory = new ProxyFactory();
factory.setSuperclass(MyService.class);

// RIGHT: cache the generated class or use Spring's singleton proxy
```

Sizing: as a stopgap, `-XX:MaxMetaspaceSize=512m` prevents JVM from consuming all native memory, but it just shifts the OOM earlier. The root cause must be fixed.

---

### AQ3: Memory Leak in Reactive / WebFlux Application

**Q:** How do memory leak patterns differ in a reactive (Project Reactor) application vs. a thread-per-request model?

**A:**

In a traditional thread-per-request model, the request's call stack is a natural scope — objects on the stack are freed when the method returns. In reactive code, there is no call stack spanning the request; instead, a pipeline of lambdas is assembled and executed asynchronously.

Leak patterns specific to reactive:

1. **Subscription not disposed**: if you call `flux.subscribe()` without keeping the `Disposable` and calling `dispose()`, the subscription and all its upstream operators remain live. In a long-lived service, each call to `subscribe()` without cleanup adds to Reactor's internal operator chain.

2. **Context propagation through Reactor Context**: Reactor's `Context` (replacing ThreadLocal in reactive) can accumulate data if chained carelessly — each `contextWrite` adds a layer, and if objects stored in context are large, the entire chain holds them.

3. **Backpressure ignored**: if a producer emits faster than a consumer consumes and you use `onBackpressureBuffer()` without a size limit, the buffer grows unbounded:
```java
// LEAK: unbounded buffer
source.onBackpressureBuffer().subscribe(consumer);

// Fix: bounded buffer with drop or error strategy
source.onBackpressureBuffer(10_000, BufferOverflowStrategy.DROP_OLDEST)
      .subscribe(consumer);
```

4. **Hot publisher subscribers**: connecting to a hot `ConnectableFlux` and never calling `dispose` on the subscriber means the subscription chain keeps the upstream alive.

Diagnosis: Reactor has built-in leak detection. Enable it:
```java
Hooks.onOperatorDebug(); // dev only, expensive
// Or in production:
ReactorDebugAgent.init(); // ByteBuddy-based, lower overhead
```

---

### AQ4: JVM Flags for Proactive Memory Leak Detection in Production

**Q:** What JVM flags do you set in production to help detect and recover from memory leaks?

**A:**

```bash
# Heap sizing
-Xms4g -Xmx4g                        # Equal min/max prevents heap resizing pauses
-XX:NewRatio=2                         # Old Gen = 2/3 of heap

# Heap dump on OOM
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/var/log/heapdumps/   # Dedicated volume, not ephemeral

# GC selection and logging (Java 17 — G1GC is default)
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200
-Xlog:gc*:file=/var/log/gc.log:time,level,tags:filecount=10,filesize=20m

# Metaspace
-XX:MaxMetaspaceSize=512m             # Prevent native memory exhaustion
-XX:MetaspaceSize=128m                # Initial commit

# OOM action: restart pod (in K8s + Spring Boot Actuator)
-XX:OnOutOfMemoryError="kill -9 %p"  # Ensures pod restarts immediately

# NativeMemoryTracking for diagnosing off-heap
-XX:NativeMemoryTracking=summary      # Adds ~5% overhead but worth it
```

Monitoring:
- Alert on: Old Gen post-GC trending above 60% for 15 minutes.
- Alert on: GC overhead > 5% of CPU time (via `GarbageCollectionNotificationInfo` JMX).
- Dashboard: Grafana with Micrometer JVM metrics (`jvm_memory_used_bytes`, `jvm_gc_pause_seconds`).

For K8s: set `limits.memory` to `Xmx + 20%` to account for off-heap (Metaspace, native buffers, JIT code cache, direct ByteBuffers).

---

## 5. Senior Trap Questions

### Trap Q1: "WeakReference prevents memory leaks"

**Q:** My team is using `WeakReference<T>` throughout the codebase to "prevent memory leaks." Is that the right approach?

**Trap answer to reject:** "Yes, WeakReference lets the GC collect the object."

**Expert answer:**

WeakReference is a tool for specific patterns, not a general leak prevention mechanism. The key misunderstanding: a WeakReference only allows the referenced object to be collected if there are NO other strong references to it. If any strong reference exists in any reachable chain, the WeakReference does nothing to prevent retention.

Example of the trap:
```java
// Team thinks this "prevents the leak"
WeakReference<BigObject> ref = new WeakReference<>(bigObject);
cache.put(key, ref); // stored in a static Map

// But if somewhere else in the code:
static BigObject globalRef = bigObject; // strong reference!
// GC will NEVER collect bigObject through the WeakReference
```

WeakReference is appropriate for:
- Canonical maps (`WeakHashMap`) — where keys are the objects you want tracked
- Observer/listener patterns — where listener lifetime is tied to the observed object
- Soft caches (`SoftReference`) — for memory-sensitive caches

The right fix for a leak is to find and remove the unexpected strong reference, not to wrap everything in WeakReference.

---

### Trap Q2: "The garbage collector will clean up"

**Q:** A junior dev says: "I'm not worried about the growing object count — the GC will clean it up eventually."

**Trap answer to reject:** "Yes, GC handles memory management so we don't need to worry."

**Expert answer:**

GC only collects objects that are unreachable. A memory leak, by definition, is a situation where objects remain reachable (referenced) but are no longer needed by the application. The GC cannot distinguish between "I'm still using this" and "I forgot to release this."

The GC will never collect:
- An object referenced by a static field
- An object referenced by a running thread
- An object referenced by a live ThreadLocal
- An object referenced by a registered listener
- An object in a cache with no eviction

The GC does not "clean up" — it manages memory for genuinely unreachable objects. Application-level leaks require application-level fixes. The GC running more frequently is actually a symptom of pressure from leaking objects: it's trying to find something to collect and failing.

Analogy: the GC is a garbage truck. If your house is full because you're hoarding (strong references), the truck can't help — it only picks up things you've put outside.

---

### Trap Q3: "Memory usage growing means there's a memory leak"

**Q:** Our heap monitoring shows memory growing steadily over 48 hours. The team declares a memory leak. Is that the right conclusion?

**Trap answer to reject:** "Yes, growing memory = memory leak, we should fix the code."

**Expert answer:**

Growing heap usage has multiple explanations, only one of which is a true leak:

1. **GC not running**: If the heap is not under pressure (lots of free space), the JVM defers GC. Heap used can grow steadily even with zero leak, then drop sharply on first GC. Check with: `jstat -gcutil <pid>` — if Old Gen usage drops significantly after a GC trigger, it's not a leak.

2. **Legitimate business data growth**: an order processing service with growing order history in a cache, or an event store accumulating events. Check business metrics against heap trend.

3. **Cache without TTL**: a correctly functioning cache filling to its size limit looks identical to a growing leak in a 48-hour chart — it just plateaus. Check cache stats.

4. **Increased load**: more users = more live sessions = more heap. Heap growing proportionally to load is expected behavior.

5. **True leak**: post-GC heap floor grows over time. The diagnostic test: trigger a Full GC (`jcmd <pid> GC.run`), record Old Gen usage. Wait one hour, trigger again. If Old Gen floor is higher the second time, you have a leak.

Jumping to "fix code" without this analysis leads to wasted engineering effort and potentially introducing new bugs.

---

### Trap Q4: "Closing in finally block means no leak"

**Q:** The team points to their `finally { conn.close(); }` pattern and says there can be no connection leak. Critique this.

**Trap answer to reject:** "Yes, finally always runs, so the connection is always closed."

**Expert answer:**

The `finally` pattern has several ways to still leak:

Case 1 — object creation throws:
```java
Connection conn = null;
try {
    conn = dataSource.getConnection(); // throws SQLEx → conn is null
    // ...
} finally {
    conn.close(); // NullPointerException — exception suppressed, original exception lost
}
```

Case 2 — close() throws, masking original exception:
```java
} finally {
    conn.close(); // throws RuntimeException
    // Original exception from try block is LOST
}
```

Case 3 — multiple resources, first close throws:
```java
} finally {
    stmt.close(); // throws → next line never runs
    conn.close(); // NEVER CALLED — connection leaks
}
```

The only safe pattern is `try-with-resources`, which handles all of these correctly by calling close in reverse order and using exception suppression:
```java
try (Connection conn = dataSource.getConnection();
     PreparedStatement stmt = conn.prepareStatement(SQL)) {
    // ...
} // Both closed correctly, exceptions suppressed not lost
```

For Java <7 codebases, the correct pattern requires nested try/finally blocks, one per resource — which is exactly why try-with-resources was introduced.

---

### Trap Q5: "The leak is in the library, not my code"

**Q:** MAT shows a Hibernate internal map consuming 600MB. The team says "it's a Hibernate bug." How do you respond?

**Trap answer to reject:** "That's a known Hibernate issue, we should upgrade the version."

**Expert answer:**

This is almost always a misdiagnosis. Hibernate's internal collections grow because your code instructed them to. Libraries retain state on your behalf — they don't acquire resources independently.

In this case: Hibernate's `SessionFactory` has a second-level cache. It grows because:
- Your code configured it without TTL or max size
- Your code is loading and caching thousands of entities
- Your code is not closing `EntityManager` instances, keeping first-level caches alive

What to investigate:
1. How many open EntityManagers are in the dump? (`SELECT em FROM org.hibernate.internal.SessionImpl em`)
2. Is the L2 cache configured with bounds? Check `hibernate.cache.region.*` settings.
3. Are you calling `session.load()` in a loop without clearing the session?

The library is a mirror of your usage patterns. When a library's internal structure is the dominator, ask "what did my code tell it to hold?"

Architect principle: assume your code owns the problem until proven otherwise. Blaming the library is a dead end — you'll find the same issue after the upgrade.

---

### Trap Q6: "We fixed the leak — heap is stable"

**Q:** The team says they fixed the leak because heap usage is now stable after the fix. How do you verify this is actually fixed?

**Trap answer to reject:** "Great, heap is stable, we're done."

**Expert answer:**

"Heap stable" after a fix needs structured verification, not a visual check. Heap can appear stable because:
- Load dropped after deployment (it's weekend, or the fix coincided with lower traffic)
- GC pressure increased and is now keeping up temporarily
- The leak rate slowed but didn't stop — you need to watch for 24-48 hours under production load

Proper verification:
1. **Old Gen post-GC floor test**: trigger `jcmd <pid> GC.run` at T+0, T+1h, T+2h. If the floor is constant (±5%), the leak is fixed. If the floor creeps up, it still leaks.
2. **Soak test**: run your load test at 1.5x production load for 4 hours. Monitor Old Gen. Regression: Old Gen never decreases after GC.
3. **Heap dump comparison**: take a dump before fix deployment and after. Compare `Histogram` — the class counts for the leaked class should be bounded, not correlated with request count.
4. **Monitor for 24 hours of production traffic** before closing the incident — memory leaks are often traffic-pattern-dependent (e.g., only certain API paths trigger the leak).

Also run `jstat -gcutil <pid> 30s` for the first hour post-deployment and watch both `O` (Old Gen %) and `GCT` (cumulative GC time). GCT should grow at a constant low rate, not accelerate.

---

## 6. Java Code Examples — Leak and Fix (Under 20 Lines Each)

### Example A: WeakHashMap as Listener Registry
```java
// CORRECT: WeakHashMap — entries evicted when key is GC'd
private final Map<Object, Listener> registry = new WeakHashMap<>();

public void register(Object owner, Listener l) {
    registry.put(owner, l); // owner held weakly
}
// When owner is GC'd (no other strong refs), entry is automatically removed
// WARNING: WeakHashMap is NOT thread-safe — wrap with Collections.synchronizedMap
```

### Example B: Correct ThreadLocal Lifecycle
```java
public class TenantContext {
    private static final ThreadLocal<String> TENANT = new ThreadLocal<>();

    public static void set(String tenantId) { TENANT.set(tenantId); }
    public static String get() { return TENANT.get(); }
    public static void clear() { TENANT.remove(); } // MUST be called

    // Usage in filter:
    // try { set(resolvedTenant); chain.doFilter(req, res); }
    // finally { clear(); }
}
```

### Example C: Safe Singleton with No Static Collection Growth
```java
public class MetricsRegistry {
    // Use ConcurrentHashMap with computeIfAbsent for safe lazy init
    private static final ConcurrentHashMap<String, AtomicLong> counters =
        new ConcurrentHashMap<>();

    public static void increment(String name) {
        counters.computeIfAbsent(name, k -> new AtomicLong()).incrementAndGet();
    }
    // Only grows by distinct metric names — bounded in practice
    // For truly dynamic names, add a size check or use Micrometer instead
}
```

### Example D: Detecting Leaked Connections at Runtime
```java
// HikariCP configuration — built-in leak detection
HikariConfig config = new HikariConfig();
config.setLeakDetectionThreshold(2000); // warn if connection held > 2 seconds
config.setConnectionTimeout(30_000);
config.setMaximumPoolSize(20);
// HikariCP will log: "Connection leak detection triggered for ..."
// Log includes stack trace of the code that borrowed the connection
```

### Example E: Correct CompletableFuture with Timeout and Cleanup
```java
public CompletableFuture<Result> fetchWithTimeout(String id) {
    return CompletableFuture
        .supplyAsync(() -> repository.fetch(id), executor)
        .orTimeout(5, TimeUnit.SECONDS)
        .exceptionally(ex -> {
            log.warn("Fetch failed for {}: {}", id, ex.getMessage());
            return Result.empty();
        });
    // No external reference retained — future is GC-eligible after completion
}
```

---

## 7. Interview Cheat Sheet

### Instant Diagnosis Commands
```bash
# Is it a leak? (Old Gen floor rising after GC)
jstat -gcutil <pid> 10s

# What's in the heap right now?
jmap -histo:live <pid> | head -30

# Force a full GC before dump (get live objects only)
jcmd <pid> GC.run
jcmd <pid> GC.heap_dump /tmp/heapdump.hprof

# Classloader count (classloader leak check)
jcmd <pid> VM.classloaders

# Thread dump (check for ThreadLocal usage)
jcmd <pid> Thread.print

# Native memory breakdown (off-heap leaks)
jcmd <pid> VM.native_memory summary
```

### MAT Workflow (30-second cheat sheet)
1. Open dump in Eclipse MAT
2. Run "Leak Suspects Report" — first look
3. "Dominator Tree" — what's holding the most retained heap
4. "Histogram" sorted by retained heap — find unexpected class counts
5. Right-click suspect class → "List objects" → "with incoming references" → traces GC root path
6. OQL for specific queries: `SELECT * FROM java.util.HashMap s WHERE s.size > 10000`

### Pattern Quick-Reference
| Pattern | Symptom | Fix |
|---|---|---|
| Static collection | Old Gen grows proportional to requests | Bounded cache or explicit removal |
| ThreadLocal in pool | Memory grows per thread count | `ThreadLocal.remove()` in finally |
| Classloader leak | Metaspace grows on redeploy | Deregister drivers, stop threads in contextDestroyed |
| Unclosed resource | Connection pool exhaustion + heap growth | try-with-resources |
| Cache no eviction | Heap grows to max then OOM | `maximumSize` + `expireAfterWrite` |
| Anonymous inner class | Runnable queue holds large object | Lambda capturing only needed vars |
| EntityManager leak | Hibernate 1st-level cache growing | try-with-resources or @Transactional |
| String.intern() abuse | PermGen/String pool OOM | Remove intern(), use equals() |
| DOM large XML | Heap spike on XML processing | SAX or StAX streaming |
| CompletableFuture chain | Futures accumulate | orTimeout + no external retention |

### Key Numbers to Know
- G1GC default pause target: 200ms
- HikariCP default max pool size: 10
- Old Gen leak signal: post-GC floor rising > 5% per hour under constant load
- Classloader leak signal: `jcmd VM.classloaders` shows N instances of WebAppClassLoader where N = redeploy count
- Memory overhead: DOM parsing ≈ 3-5x raw XML size in heap

### The 5-Minute Diagnosis Protocol
1. `jstat -gcutil <pid> 10s 30` — observe Old Gen trend
2. `jcmd <pid> GC.run` — trigger Full GC
3. `jstat -gcutil <pid> 10s 6` — observe post-GC floor
4. If floor is high: `jmap -histo:live <pid> | head -40` — spot the class
5. `jcmd <pid> GC.heap_dump /tmp/dump.hprof` — for deep analysis

### Phrases That Signal Seniority
- "The diagnostic test for a true leak is whether the post-GC Old Gen floor rises over time, not whether usage is growing."
- "WeakReference only helps if there are no other strong reference paths to the object."
- "try-with-resources solves the silent-exception-masking problem that finally-with-null-check does not."
- "In a thread pool, ThreadLocal values survive request boundaries — always remove in finally."
- "When MAT points to a library's internal structure, the library is a mirror of how your code used it."
- "Classloader leaks are invisible in heap dumps that only count bytes — count ClassLoader instances instead."
- "For reactive apps, an unmanaged subscription is the equivalent of an unclosed resource."

### Architect-Level Preventive Measures
1. **ArchUnit** rule: no `static` mutable collections in non-singleton beans
2. **SpotBugs** + `findbugs-sec`: flags unclosed streams, ThreadLocal without remove
3. **HikariCP leak detection threshold** set in all environments
4. **Heap dump on OOM** configured in all JVM deployments
5. **Old Gen post-GC Grafana alert** at 60% for 15 minutes
6. **Load test (soak)** as release gate: 2h at 1.5x peak load, Old Gen must stay bounded
7. **Caffeine cache stats** exposed to metrics: hit rate, eviction rate, entry count
8. **Structured deployment checklist**: `contextDestroyed` implemented for all web apps, deregisters drivers, stops threads
9. **Code review checklist item**: any new `static` field that holds mutable state must have a documented lifecycle and bounded growth
10. **Reactive apps**: `ReactorDebugAgent.init()` in dev; bounded backpressure buffers in all pipelines

---

*Last updated: 2026-08-22 | Target role: Java Architect / Staff Engineer / Principal Engineer*
