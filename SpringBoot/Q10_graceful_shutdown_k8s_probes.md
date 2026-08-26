# Q10: Graceful Shutdown + K8s Liveness/Readiness Probes (Architect Guide)

**Study Time:** 15-20 minutes | **Frequency:** 85% in architect interviews 🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

---

## Why This Matters in Production

Without graceful shutdown + correct K8s probes:
- In-flight requests get cut off mid-processing (lost orders, partial writes)
- K8s sends traffic to pods that are still starting up (connection refused, 500s)
- Rolling deployments cause visible downtime
- Database connections are leaked during pod termination
- Health checks report healthy when the app is stuck (DB down, thread pool exhausted)

---

## The Problem: Abrupt Shutdown

```
Without graceful shutdown:
  K8s sends SIGTERM → JVM exits immediately
  → 50 in-flight HTTP requests: cut off
  → 5 @Async jobs mid-execution: killed
  → DB transaction in progress: rolled back, data inconsistent
  → Connection pool: 20 connections leaked (not returned to pool)
```

---

## Graceful Shutdown in Spring Boot

### Enable It (Spring Boot 2.3+)

```yaml
# application.yml
server:
  shutdown: graceful          # default is "immediate"

spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s   # max wait for in-flight requests to finish
```

### What Happens with Graceful Shutdown

```
K8s sends SIGTERM signal
        ↓
Spring Boot receives SIGTERM
        ↓
1. HTTP connector stops accepting NEW requests (returns 503 to new connections)
        ↓
2. Waits up to timeout-per-shutdown-phase for IN-FLIGHT requests to complete
        ↓
3. SmartLifecycle.stop() called for all beans (highest phase first)
        ↓
4. @PreDestroy methods called
        ↓
5. Thread pools shut down (executor.setWaitForTasksToCompleteOnShutdown=true)
        ↓
6. DB connection pool closed
        ↓
7. JVM exits with code 0
```

### Thread Pool Graceful Shutdown

```java
@Configuration
@EnableAsync
public class AsyncConfig {

    @Bean(name = "taskExecutor")
    public ThreadPoolTaskExecutor taskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(10);
        executor.setMaxPoolSize(50);
        executor.setQueueCapacity(200);
        executor.setThreadNamePrefix("async-task-");

        // Graceful shutdown settings
        executor.setWaitForTasksToCompleteOnShutdown(true);  // wait for running tasks
        executor.setAwaitTerminationSeconds(30);              // max wait time

        executor.initialize();
        return executor;
    }
}
```

### Kafka Consumer Graceful Shutdown

```java
@Component
public class OrderEventConsumer {

    @KafkaListener(topics = "orders", groupId = "order-processor")
    public void consume(OrderEvent event) {
        orderService.process(event);
    }

    // Spring Kafka handles graceful shutdown automatically when:
    // spring.kafka.listener.shutdown-timeout is set
}

# application.yml
spring:
  kafka:
    listener:
      shutdown-timeout: 10s   # wait for current message processing to finish
```

---

## K8s Pod Lifecycle + Probe Types

```
Pod created
    ↓
Container starts (JVM boots, Spring context loads — takes 5-30s)
    ↓
startupProbe runs (is the app done starting?)
    ↓ success
livenessProbe runs (is the app alive / not deadlocked?)
    ↓ success
readinessProbe runs (is the app ready to receive traffic?)
    ↓ success
K8s Service routes traffic to this pod
```

### The Three Probe Types

| Probe | Failure Action | Use For |
|-------|---------------|---------|
| `startupProbe` | Restart container | Slow-starting apps — prevents liveness from killing app before it's ready |
| `livenessProbe` | Restart container | Detect deadlock, infinite loop, JVM freeze |
| `readinessProbe` | Remove from Service endpoints | Temporary unavailability (DB down, cache miss, high load) |

**Critical distinction:**
- `liveness` failure → K8s **kills and restarts** the pod
- `readiness` failure → K8s **stops sending traffic** but pod stays alive

---

## Spring Boot Actuator Probes

### Dependency

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

### Configuration

```yaml
# application.yml
management:
  endpoint:
    health:
      probes:
        enabled: true           # enables /actuator/health/liveness and /actuator/health/readiness
      show-details: always      # show component details (DB, Redis, Kafka status)
  endpoints:
    web:
      exposure:
        include: health, info, metrics, prometheus
  health:
    livenessstate:
      enabled: true
    readinessstate:
      enabled: true
```

This exposes:
- `GET /actuator/health/liveness` → `{"status": "UP"}`
- `GET /actuator/health/readiness` → `{"status": "UP", "components": {...}}`

### What Each Probe Checks by Default

```
/actuator/health/liveness:
  → Is the Spring ApplicationContext alive?
  → Has the app entered a broken state (LivenessState.BROKEN)?

/actuator/health/readiness:
  → Is the app ready to serve traffic (ReadinessState.ACCEPTING_TRAFFIC)?
  → Are all health indicators UP? (DB, Redis, Kafka, disk space)
```

---

## Custom Health Indicators

```java
// Custom readiness indicator — app is not ready if external dependency is down
@Component
public class PaymentGatewayHealthIndicator implements HealthIndicator {

    @Autowired
    private PaymentGatewayClient paymentGateway;

    @Override
    public Health health() {
        try {
            boolean reachable = paymentGateway.ping();
            if (reachable) {
                return Health.up()
                             .withDetail("gateway", "reachable")
                             .withDetail("latency", paymentGateway.getLastLatencyMs() + "ms")
                             .build();
            } else {
                return Health.down()
                             .withDetail("gateway", "unreachable")
                             .withDetail("reason", "ping failed")
                             .build();
            }
        } catch (Exception e) {
            return Health.down()
                         .withDetail("gateway", "error")
                         .withDetail("error", e.getMessage())
                         .build();
        }
    }
}

// Custom liveness indicator — app is broken if critical thread pool is exhausted
@Component
public class ThreadPoolLivenessIndicator implements LivenessStateHealthIndicator {

    @Autowired
    @Qualifier("taskExecutor")
    private ThreadPoolTaskExecutor taskExecutor;

    @Override
    public Health health() {
        int activeThreads = taskExecutor.getActiveCount();
        int maxThreads = taskExecutor.getMaxPoolSize();
        int queueSize = taskExecutor.getThreadPoolExecutor().getQueue().size();
        int queueCapacity = taskExecutor.getQueueCapacity();

        // If queue is 90%+ full, declare BROKEN → K8s restarts pod
        if (queueSize > queueCapacity * 0.9) {
            return Health.down()
                         .withDetail("reason", "Task queue nearly full")
                         .withDetail("queueSize", queueSize)
                         .withDetail("queueCapacity", queueCapacity)
                         .build();
        }
        return Health.up()
                     .withDetail("activeThreads", activeThreads)
                     .withDetail("queueSize", queueSize)
                     .build();
    }
}
```

### Programmatic State Changes

```java
// Manually signal readiness state changes during the app lifecycle
@Component
public class ApplicationReadinessManager implements ApplicationListener<ApplicationReadyEvent> {

    @Autowired
    private ApplicationContext applicationContext;

    @Override
    public void onApplicationEvent(ApplicationReadyEvent event) {
        // App is fully started — explicitly signal ready
        AvailabilityChangeEvent.publish(applicationContext, ReadinessState.ACCEPTING_TRAFFIC);
    }
}

// During maintenance or before shutdown — stop receiving traffic
@RestController
public class AdminController {

    @Autowired
    private ApplicationContext applicationContext;

    @PostMapping("/admin/drain")
    public void drainTraffic() {
        // Mark pod as not ready — K8s stops sending traffic
        // Pod stays alive, in-flight requests complete
        AvailabilityChangeEvent.publish(applicationContext, ReadinessState.REFUSING_TRAFFIC);
    }
}
```

---

## K8s Deployment Configuration

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 60   # K8s waits 60s after SIGTERM before SIGKILL

      containers:
        - name: order-service
          image: order-service:1.0.0

          # Startup probe — prevent liveness from killing slow-starting app
          startupProbe:
            httpGet:
              path: /actuator/health/liveness
              port: 8080
            failureThreshold: 30      # try 30 times
            periodSeconds: 10         # every 10s = 5 minutes max startup time
            initialDelaySeconds: 10   # wait 10s before first check

          # Liveness probe — restart if app is deadlocked/broken
          livenessProbe:
            httpGet:
              path: /actuator/health/liveness
              port: 8080
            initialDelaySeconds: 0    # startupProbe already passed
            periodSeconds: 10
            failureThreshold: 3       # restart after 3 consecutive failures
            timeoutSeconds: 5

          # Readiness probe — stop traffic if app is overwhelmed
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness
              port: 8080
            initialDelaySeconds: 0
            periodSeconds: 5          # check every 5s — fast recovery
            failureThreshold: 3
            successThreshold: 1       # 1 success = restore traffic
            timeoutSeconds: 3

          # Resource limits — prevent OOM kill from crashing node
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "1Gi"
              cpu: "1000m"

          # JVM memory must fit within container limit
          env:
            - name: JAVA_OPTS
              value: "-Xms512m -Xmx768m -XX:+UseG1GC"
```

---

## Zero-Downtime Rolling Deployment Flow

```
Rolling deployment (maxUnavailable=0, maxSurge=1):

Step 1: New pod starts
  → startupProbe: checking (old pod still handling traffic)
  ↓ 20s later
  → liveness: UP, readiness: UP
  → K8s adds new pod to Service endpoints

Step 2: Old pod termination starts
  → K8s removes old pod from Service endpoints
  → K8s sends SIGTERM to old pod
  → Spring Boot: stops accepting new requests
  → Spring Boot: waits 30s for in-flight requests to drain
  → @PreDestroy, connection pool close
  → JVM exits cleanly

Step 3: Traffic fully on new pod
  → Zero dropped requests
```

### PreStop Hook — Ensure K8s Removes Pod Before SIGTERM

```yaml
# There's a race condition: K8s removes pod from endpoints
# and sends SIGTERM simultaneously. Some requests may still
# be routed to the pod while it's shutting down.
# Fix: add a preStop sleep to let endpoint propagation complete.

lifecycle:
  preStop:
    exec:
      command: ["sh", "-c", "sleep 10"]
# This delays SIGTERM by 10s, giving load balancers time
# to stop routing traffic before shutdown begins.
```

---

## Interview Cheat Sheet

```
Graceful shutdown:
  server.shutdown=graceful
  spring.lifecycle.timeout-per-shutdown-phase=30s
  executor.setWaitForTasksToCompleteOnShutdown(true)
  terminationGracePeriodSeconds in K8s > Spring shutdown timeout

Three K8s probes:
  startupProbe  → slow-starting apps, prevents premature liveness kill
  livenessProbe → detects deadlock/freeze → RESTARTS pod
  readinessProbe → detects overload/dependency down → REMOVES from load balancer

Spring Actuator probes:
  /actuator/health/liveness   → ApplicationContext alive?
  /actuator/health/readiness  → All health indicators UP?
  Enabled with: management.endpoint.health.probes.enabled=true

Custom HealthIndicator → plugs into readiness automatically
LivenessStateHealthIndicator → plugs into liveness

Readiness failure → pod stays alive, traffic stops (use for: DB down, overloaded)
Liveness failure  → pod restarted (use for: deadlock, unrecoverable error only)

preStop sleep (5-10s) → prevents race between endpoint removal and SIGTERM
```

---

## Key Architect Questions

**Q: What's the difference between liveness and readiness probes? When would you fail each?**
- Fail readiness: DB connection pool exhausted, downstream service down, cache not warmed — temporary, recoverable. Pod stays alive, traffic redirected.
- Fail liveness: JVM deadlock, infinite loop, unrecoverable state. Pod restarts. Don't fail liveness for transient issues — unnecessary restarts cause cascading failures.

**Q: What happens if terminationGracePeriodSeconds < Spring's shutdown timeout?**
K8s sends SIGKILL after `terminationGracePeriodSeconds` regardless. In-flight requests still get killed. Always set K8s timeout > Spring timeout by at least 10 seconds buffer.

**Q: How do you prevent traffic hitting a pod that is still starting up (before Spring context loads)?**
Use `startupProbe` with high `failureThreshold`. Without it, `livenessProbe` starts immediately, sees the app not responding, and kills the pod — crash loop. `startupProbe` temporarily disables `livenessProbe` until the app is up.

**Q: How do you handle DB connection pool exhaustion in K8s?**
Set pool max size to a value that accounts for all pod replicas: `max_pool_size × pod_count < DB max_connections`. When pool is full, mark readiness as DOWN — K8s stops sending more traffic to this pod, giving it time to drain.

**Q: How does Spring Boot signal readiness before it's actually ready (e.g., cache warm-up)?**
Override `ApplicationRunner` or use `SmartLifecycle`. Stay in `REFUSING_TRAFFIC` state during warm-up, then publish `ReadinessState.ACCEPTING_TRAFFIC` when ready. Readiness probe returns DOWN until you publish the event.
