# Q22: Spring Boot Performance Tuning — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 20-25 minutes | **Frequency:** 80% in architect rounds 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "We set -Xmx to 2GB for a pod with a 2GB memory limit. K8s OOMKilled the pod before it even finished starting. JVM uses memory beyond the heap — metaspace, thread stacks, off-heap buffers — total was 3GB." — The JVM memory trap.

---

## Scenario 1: JVM Memory Tuning for Kubernetes (Most Common OOMKill)

### How JVM Memory Works Inside a Container
```
Container memory limit: 2GB (set in K8s deployment)

JVM memory breakdown:
  Heap (controlled by -Xmx):       e.g. 2048m   ← your -Xmx value
  Metaspace (class metadata):           ~256m
  Thread stacks (~1MB per thread):      ~200m (200 threads × 1MB)
  Code cache (JIT compiled code):       ~240m
  Direct/off-heap (Netty, NIO):         ~256m
  JVM internal overhead:                ~100m
  ─────────────────────────────────────
  TOTAL:                              ~3100m  ← EXCEEDS 2GB LIMIT!

K8s sees RSS > 2GB → OOMKills the pod → pod restarts → OOMKill loop
Kubernetes events: "OOMKilled" exit code 137
```

### Fix: The 70% Rule
```
-Xmx = 70% of container memory limit
       Leave 30% for JVM overhead, Metaspace, threads, off-heap

Container limit: 2GB (2048MB)
-Xmx:           0.7 × 2048 = ~1433m → use 1400m (round down for safety)
```

```yaml
# Kubernetes deployment.yaml
resources:
  requests:
    memory: "1Gi"
  limits:
    memory: "2Gi"   # hard limit — OOMKill if exceeded

# application startup command or Dockerfile
JAVA_OPTS: >
  -Xms256m          # initial heap — small, grow as needed
  -Xmx1400m         # max heap — 70% of 2GB container limit
  -XX:MaxMetaspaceSize=256m
  -XX:MaxDirectMemorySize=256m
  -XX:+UseContainerSupport    # CRITICAL: makes JVM aware it's in a container
                               # Without this: JVM reads HOST machine's memory
                               # (e.g. 64GB) and sets Xmx to 25GB!
```

### UseContainerSupport — The Silent Default Trap
```
BEFORE Java 8u191 / Java 10+:
  JVM ignores cgroup memory limits
  JVM reads host machine RAM (e.g. 64GB)
  Sets default -Xmx to 25% of 64GB = 16GB
  Your 2GB pod immediately OOMKills on first GC cycle

Java 11+:
  -XX:+UseContainerSupport is ON by default ✅
  JVM reads cgroup limits correctly
  Default heap = 25% of container limit (512MB for 2GB pod)
  -XX:MaxRAMPercentage=70.0 → sets Xmx to 70% of container limit dynamically
```

```bash
# Modern approach — no hardcoded -Xmx, dynamic based on container limit
JAVA_OPTS: "-XX:+UseContainerSupport -XX:MaxRAMPercentage=70.0"
# If container limit is 2GB → Xmx = 1433MB automatically
# If container limit is 4GB → Xmx = 2867MB automatically
# Works correctly across all environment sizes ✅
```

---

## Scenario 2: GC Tuning — G1GC vs ZGC in Containers

### The Production Problem (G1GC in a 1GB Container)
```
G1GC default settings are designed for machines with 4+ GB RAM.
In a 1GB container:
  - G1GC creates many small regions but has memory overhead
  - Full GC pauses: 500ms-2s → request timeouts
  - Frequent GC cycles → CPU throttling → latency spikes

Symptoms:
  - Intermittent 2-5s response time spikes (correlate with GC logs)
  - CPU usage spikes then drops (GC activity)
  - K8s HPA scales OUT but latency still spikes (GC is the bottleneck)
```

### GC Choice Guide
```
Container < 1GB RAM:    SerialGC (-XX:+UseSerialGC)
                        Single-threaded GC, low memory overhead
                        Good for: tiny microservices, serverless-style

Container 1-4GB RAM:    ZGC (-XX:+UseZGC, Java 15+)
                        Sub-millisecond pauses (< 1ms regardless of heap size)
                        Concurrent — doesn't stop application threads
                        Slight throughput trade-off vs G1GC

Container > 4GB RAM:    G1GC (default) or ZGC
                        G1GC: high throughput, predictable pauses
                        ZGC: if pause time < 1ms is required

E-commerce / APIs:      ZGC (latency-sensitive — can't afford 500ms pauses)
Batch processing:       G1GC (throughput over pause time)
```

```bash
# ZGC configuration for Spring Boot API service
JAVA_OPTS: >
  -XX:+UseZGC
  -XX:+UseContainerSupport
  -XX:MaxRAMPercentage=70.0
  -Xlog:gc*:file=/var/log/gc.log:time,uptime:filecount=5,filesize=10m
```

---

## Scenario 3: Startup Time Optimisation

### The Problem
```
Spring Boot app starts in 45 seconds.
K8s rolling deploy: new pods must be Ready before old ones terminate.
K8s readiness probe: checks every 5s, failureThreshold=3 → 15s grace.
45s startup → K8s marks pod as failed → never gets traffic → deploy fails.

Also: Lambda cold starts with Spring Boot = 8-15 seconds → timeouts.
```

### Fix 1: Lazy Initialisation
```yaml
spring:
  main:
    lazy-initialization: true
    # Beans created on first use, not at startup
    # Startup: 45s → ~15s (60-70% faster)
    # First request: slightly slower (beans instantiated)
    # Good for: dev, test, Lambda
    # Caution: hides wiring errors until runtime (not at startup)
```

```java
// Mark specific beans as eager even with lazy init ON
@Bean
@Lazy(false)   // override lazy for this bean — initialise at startup
public DataSource dataSource() { ... }
// Use for: DB connections, caches that must be warm before traffic

// Or: exclude critical paths from lazy init with @DependsOn chain
```

### Fix 2: Component Scan Optimisation
```java
// SLOW ❌ — scans ALL packages recursively
@SpringBootApplication  // default: scans root package and all sub-packages

// FAST ✅ — scan only what you need
@SpringBootApplication(scanBasePackages = {
    "com.flipkart.order",
    "com.flipkart.payment"
})
// Avoids accidentally scanning test classes, third-party packages, etc.
```

### Fix 3: Spring Boot Buildpacks / Layered JAR (Faster Docker Builds)
```dockerfile
# Standard fat JAR — all 200MB in one layer
# Every code change rebuilds the 200MB layer
FROM eclipse-temurin:21
COPY target/order-service.jar /app.jar
ENTRYPOINT ["java", "-jar", "/app.jar"]

# Layered JAR — dependencies cached in separate layer
# Code changes only rebuild the thin code layer (~1MB)
FROM eclipse-temurin:21 as builder
COPY target/order-service.jar /app.jar
RUN java -Djarmode=layertools -jar /app.jar extract --destination /extracted

FROM eclipse-temurin:21
COPY --from=builder /extracted/dependencies /
COPY --from=builder /extracted/spring-boot-loader /
COPY --from=builder /extracted/snapshot-dependencies /
COPY --from=builder /extracted/application /        # only 1-5MB — changes here
ENTRYPOINT ["org.springframework.boot.loader.launch.JarLauncher"]
# Docker layer cache means: 95% of builds only push the 1-5MB application layer
```

---

## Scenario 4: Virtual Threads (Java 21 + Spring Boot 3.2)

### What Are Virtual Threads?
```
Traditional (Platform) Thread:
  1:1 mapping to OS thread
  Each thread uses ~1MB of memory
  Spring Boot with 200 platform threads = 200MB just for threads
  Thread pool of 200: can only handle 200 concurrent blocking operations

Virtual Thread (Java 21 Project Loom):
  M:N mapping — many virtual threads on few OS threads (carrier threads)
  Each virtual thread uses ~KB of memory
  Millions of virtual threads possible — no thread pool sizing needed
  Blocking I/O: virtual thread is parked, carrier thread freed for other work
```

### Enabling Virtual Threads in Spring Boot 3.2
```yaml
spring:
  threads:
    virtual:
      enabled: true   # one line — that's it!
      # All @Async, Tomcat request threads, scheduled tasks → virtual threads
```

```java
// Result:
// Before: 200-thread Tomcat pool → 200 max concurrent HTTP requests
// After:  virtual threads → millions of concurrent HTTP requests
// Ideal for: I/O-bound Spring Boot apps (DB calls, HTTP calls, file I/O)
```

### Virtual Thread Trap: synchronized + Blocking = Carrier Thread Pinning

```java
// TRAP ❌ — synchronized block pins the carrier OS thread
@Service
public class PaymentService {

    private final Object lock = new Object();

    public PaymentResult process(PaymentRequest req) {
        synchronized (lock) {
            // If this calls a blocking DB operation inside synchronized,
            // the CARRIER thread (OS thread) is PINNED and cannot be reused
            // Defeats the entire purpose of virtual threads
            return paymentRepo.findAndLock(req.getOrderId());  // blocking inside sync!
        }
    }
}
// With 200 OS carrier threads + 1000 synchronized-blocking calls
// → 1000 virtual threads all pinned to OS threads
// → Back to platform thread behaviour
```

```java
// FIX ✅ — use ReentrantLock instead of synchronized
@Service
public class PaymentService {

    private final ReentrantLock lock = new ReentrantLock();

    public PaymentResult process(PaymentRequest req) {
        lock.lock();
        try {
            // ReentrantLock allows virtual thread to yield the carrier thread
            // while waiting — no pinning!
            return paymentRepo.findAndLock(req.getOrderId());
        } finally {
            lock.unlock();
        }
    }
}
```

```
IDENTIFY PINNING in production:
  Enable JDK Flight Recorder:
  -Djdk.tracePinnedThreads=full
  Output: "Thread pinned" log shows the pinning stack trace
  
  Common pinning sources: synchronized blocks, native methods, some JDBC drivers
  Spring Boot 3.3+: most Spring internals updated to avoid synchronized
```

---

## Trap 1: Lazy Initialisation Hiding Startup Wiring Errors

### The Bug
```java
@Configuration
public class PaymentConfig {

    @Bean
    public PaymentClient paymentClient(@Value("${payment.api.key}") String apiKey) {
        return new PaymentClient(apiKey);
    }
}

# application.yml (prod) is missing:
payment:
  api:
    key: ...   # MISSING!
```

```
Without lazy init:
  App starts → PaymentClient bean created → @Value injection fails
  → BeanCreationException at startup → pod fails to start → caught immediately ✅

With lazy-initialization=true:
  App starts → PaymentClient NOT created yet (lazy)
  → Pod starts, readiness probe passes, traffic hits pod
  → First request to /checkout → tries to create PaymentClient → fails!
  → 500 error for all users making payment
  → Now you find the missing config in production

FIX: For critical beans (DB, payment, external API clients),
     annotate with @Lazy(false) or initialise eagerly even with lazy mode ON.
```

---

## Quick Reference: Performance Tuning Checklist

```
STARTUP:
  ✅ -XX:+UseContainerSupport (Java 11+, on by default)
  ✅ -XX:MaxRAMPercentage=70.0 (dynamic heap sizing)
  ✅ Lazy init for Lambda / test environments
  ✅ @Lazy(false) on critical beans even with lazy init ON
  ✅ Layered JAR Docker build (fast CI/CD deploys)

GC:
  ✅ ZGC for latency-sensitive APIs (< 1ms pauses)
  ✅ G1GC for batch processing (higher throughput)
  ✅ Enable GC logging (-Xlog:gc*) — silent GC = debugging in the dark

VIRTUAL THREADS:
  ✅ spring.threads.virtual.enabled=true (Spring Boot 3.2+, Java 21)
  ✅ Replace synchronized with ReentrantLock in I/O-bound code
  ✅ Check -Djdk.tracePinnedThreads=full for pinning issues

MEMORY:
  ✅ -Xmx = 70% of container limit
  ✅ Set -XX:MaxMetaspaceSize to avoid unbounded metaspace growth
  ✅ Monitor: jvm_memory_used_bytes in Prometheus/Micrometer
```

---

## Interview Cheat Sheet

> "JVM in containers: always use -XX:+UseContainerSupport (default in Java 11+) — without it, JVM reads host RAM and allocates a heap larger than the container limit, causing OOMKill. Use -XX:MaxRAMPercentage=70.0 for dynamic heap sizing across environments. ZGC for latency-sensitive APIs — sub-millisecond GC pauses vs G1GC's 200ms-2s pauses in low-memory containers. Virtual threads with spring.threads.virtual.enabled=true (Spring Boot 3.2, Java 21) give near-unlimited concurrency for I/O-bound apps — the only trap is synchronized blocks pinning carrier threads; replace with ReentrantLock. Lazy initialisation cuts startup time by 60-70% but hides wiring errors — mark critical infrastructure beans with @Lazy(false) to keep fail-fast behaviour."
