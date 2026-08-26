# Q20: Actuator, Observability & Micrometer — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 15-20 minutes | **Frequency:** 80% in architect rounds 🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "Our /actuator/env endpoint was publicly reachable and listed the JWT_SECRET and DATABASE_PASSWORD in plain text. Found during a routine security audit." — Actuator misconfiguration in production.

---

## How Actuator + Micrometer + Tracing Fit Together

```
YOUR SPRING BOOT APP
      │
      ├── Actuator endpoints (/health, /metrics, /info, /env...)
      │     └── secured via Spring Security or management.endpoints config
      │
      ├── Micrometer (metrics library)
      │     ├── Counter, Timer, Gauge — instrument your code
      │     └── exports to: Prometheus, CloudWatch, Datadog, etc.
      │
      └── Micrometer Tracing (distributed trace IDs)
            ├── Injects traceId/spanId into HTTP headers
            ├── Propagates via Kafka headers, async threads
            └── exports to: Zipkin, Jaeger, AWS X-Ray

MONITORING STACK:
  App metrics → Prometheus scrapes /actuator/prometheus → Grafana dashboards
  App logs    → include traceId → CloudWatch/ELK → search by trace
  App traces  → Zipkin → visualise full request journey across services
```

---

## Scenario 1: Custom Health Indicator

### The Problem
```java
// Default /actuator/health only checks:
// - Database connection (if JPA present)
// - Disk space
// - Redis connection (if Redis present)

// Your business-critical dependency: external payment gateway
// If it's down: your checkout feature is broken
// But /actuator/health shows UP — Kubernetes thinks the pod is healthy
// Kubernetes keeps sending traffic to a pod that can't process payments
```

### Fix: Custom HealthIndicator
```java
@Component
public class PaymentGatewayHealthIndicator implements HealthIndicator {

    private final PaymentGatewayClient client;

    @Override
    public Health health() {
        try {
            // Lightweight ping call — not a full transaction
            PingResponse resp = client.ping();   // GET /health → 200 expected

            if (resp.isHealthy()) {
                return Health.up()
                    .withDetail("gateway", "Stripe")
                    .withDetail("latency_ms", resp.getLatencyMs())
                    .build();
            } else {
                return Health.down()
                    .withDetail("gateway", "Stripe")
                    .withDetail("reason", resp.getError())
                    .build();
            }

        } catch (Exception ex) {
            return Health.down(ex)
                .withDetail("gateway", "Stripe")
                .withDetail("error", ex.getMessage())
                .build();
        }
    }
}
```

```yaml
management:
  endpoint:
    health:
      show-details: when-authorized   # show details to authenticated requests only
      show-components: always
  health:
    payment-gateway:
      enabled: true   # component name = "paymentGateway" (camelCase of bean name)
```

### Health in Kubernetes (Liveness vs Readiness)
```java
// Liveness probe: Is the app alive? (restart if NO)
// → should only fail on IRRECOVERABLE state (deadlock, OOM, etc.)
// → payment gateway DOWN = not an app death → don't fail liveness!

// Readiness probe: Is the app ready to receive traffic? (remove from LB if NO)
// → payment gateway DOWN = pod not ready to process payments → fail readiness!

@Component
public class PaymentReadinessIndicator implements ReadinessHealthIndicator {
    // Contributes to /actuator/health/readiness
    // K8s readinessProbe → if DOWN, pod removed from Service endpoints
}

// Liveness probe → /actuator/health/liveness
// Only fail this for: out of memory, corrupted state, deadlock
// NOT for: external API down, DB temporarily unavailable
```

---

## Scenario 2: Custom Metrics with Micrometer

### Production Instrumentation
```java
@Service
public class OrderService {

    private final Counter orderCounter;
    private final Counter orderFailureCounter;
    private final Timer orderProcessingTimer;
    private final AtomicInteger pendingOrdersGauge;

    public OrderService(MeterRegistry registry) {
        // Counter: monotonically increasing count
        this.orderCounter = Counter.builder("orders.placed")
            .description("Total orders placed")
            .tag("service", "order-service")
            .register(registry);

        this.orderFailureCounter = Counter.builder("orders.failed")
            .description("Total failed orders")
            .register(registry);

        // Timer: records duration and count (histogram + percentiles)
        this.orderProcessingTimer = Timer.builder("orders.processing.duration")
            .description("Order processing duration")
            .sla(Duration.ofMillis(100), Duration.ofMillis(500), Duration.ofSeconds(1))
            .percentilePrecision(2)
            .publishPercentiles(0.5, 0.95, 0.99)
            .register(registry);

        // Gauge: current value (not a counter — can go up and down)
        this.pendingOrdersGauge = new AtomicInteger(0);
        Gauge.builder("orders.pending", pendingOrdersGauge, AtomicInteger::get)
             .description("Currently pending orders")
             .register(registry);
    }

    public Order placeOrder(OrderRequest request) {
        return orderProcessingTimer.record(() -> {
            try {
                Order order = processOrder(request);
                orderCounter.increment(1.0);
                pendingOrdersGauge.incrementAndGet();
                return order;
            } catch (Exception ex) {
                orderFailureCounter.increment(1.0);
                throw ex;
            }
        });
    }

    public void completeOrder(Long orderId) {
        // ... complete order ...
        pendingOrdersGauge.decrementAndGet();
    }
}
```

```yaml
management:
  metrics:
    distribution:
      percentiles-histogram:
        orders.processing.duration: true   # enable histogram for this metric
      slo:
        orders.processing.duration: 100ms,500ms,1s  # SLO buckets for Prometheus
```

### Prometheus Scraping
```yaml
# Prometheus scrapes:
# GET /actuator/prometheus

management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus   # expose prometheus endpoint
  endpoint:
    prometheus:
      enabled: true
```

```
# Grafana queries on these metrics:
# Request rate:      rate(orders_placed_total[5m])
# Error rate:        rate(orders_failed_total[5m]) / rate(orders_placed_total[5m])
# P99 latency:       histogram_quantile(0.99, orders_processing_duration_seconds_bucket)
# Pending orders:    orders_pending
```

---

## Trap 1: Actuator Exposing Secrets (Critical Production Trap)

### The Incident
```
GET /actuator/env
{
  "propertySources": [
    {
      "name": "systemEnvironment",
      "properties": {
        "DATABASE_PASSWORD": { "value": "Pr0d$ecretPass!" },   ← PLAIN TEXT
        "JWT_SECRET": { "value": "my-super-secret-256-bit-key" },
        "STRIPE_API_KEY": { "value": "sk_live_xxxxxxxxxxxx" }
      }
    }
  ]
}
// /actuator/env shows ALL environment variables and Spring properties
// If not secured, anyone who can reach the app can read your secrets
```

### Production-Safe Actuator Config
```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus  # ONLY these — never env, beans, heapdump
  endpoint:
    health:
      show-details: when-authorized
    env:
      enabled: false    # explicitly disable
  # Secure all actuator endpoints
  server:
    port: 8081          # separate management port — not exposed to internet
```

```java
@Configuration
public class ActuatorSecurityConfig {
    @Bean
    public SecurityFilterChain actuatorChain(HttpSecurity http) throws Exception {
        http
            .securityMatcher("/actuator/**")
            .authorizeHttpRequests(a -> a
                .requestMatchers("/actuator/health/**").permitAll()
                .requestMatchers("/actuator/prometheus").hasAuthority("MONITORING")
                .anyRequest().denyAll()  // everything else: blocked
            );
        return http.build();
    }
}
```

---

## Trap 2: @Timed on Non-Spring-Managed Bean (Annotation Silently Ignored)

### The Bug
```java
// WRONG ❌ — @Timed on a class not managed by Spring AOP proxy
public class PricingCalculator {   // not @Service, not @Component

    @Timed(value = "pricing.calculation", percentiles = {0.99})
    public BigDecimal calculate(Cart cart) {
        // complex calculation...
    }
}
// @Timed uses Spring AOP — only works on beans in the ApplicationContext
// This class is created with "new PricingCalculator()" somewhere
// → AOP proxy is bypassed → @Timed silently does nothing
// → No metric recorded, no error thrown
```

### Fix
```java
// Option 1: Make it a Spring bean
@Service
public class PricingCalculator {
    @Timed(value = "pricing.calculation")
    public BigDecimal calculate(Cart cart) { ... }
}

// Option 2: Manual timing (works anywhere, even non-Spring classes)
@Service
public class PricingService {
    private final Timer timer;

    public PricingService(MeterRegistry registry) {
        this.timer = registry.timer("pricing.calculation");
    }

    public BigDecimal calculate(Cart cart) {
        return timer.record(() -> pricingCalculator.calculate(cart));
    }
}
```

---

## Scenario 3: Distributed Tracing with Micrometer Tracing

### The Problem Without Tracing
```
User: "My checkout is slow sometimes"
You: tail -f logs on 6 microservices, grep for userId...
     - OrderService: 2024-01-15 12:34:56 INFO Processing order for user 123
     - PaymentService: 2024-01-15 12:34:57 INFO Charging card for order ???
     - InventoryService: 2024-01-15 12:34:58 INFO ??? item reserved
     → No correlation, can't link these log lines to one request
```

### With Distributed Tracing
```java
// Spring Boot 3.x auto-configures Micrometer Tracing
// Just add the dependencies — zero code changes needed
```

```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-tracing-bridge-brave</artifactId>
</dependency>
<dependency>
    <groupId>io.zipkin.reporter2</groupId>
    <artifactId>zipkin-reporter-brave</artifactId>
</dependency>
```

```yaml
management:
  tracing:
    sampling:
      probability: 0.1   # trace 10% of requests in production (cost control)
      # 1.0 in staging/debugging
spring:
  zipkin:
    base-url: http://zipkin:9411
logging:
  pattern:
    level: "%5p [${spring.application.name:},%X{traceId:-},%X{spanId:-}]"
    # Log pattern includes traceId automatically
    # Output: INFO [order-service,abc123def456,def456] Processing order...
```

```
TRACE PROPAGATION FLOW:
  HTTP Request → OrderService (traceId=abc123, spanId=001)
       │ passes traceId in outgoing HTTP header (traceparent: 00-abc123-001-01)
       ├──► InventoryService (traceId=abc123, spanId=002)
       └──► PaymentService (traceId=abc123, spanId=003)
                └──► Stripe API (external, new traceId if they support it)

  In Zipkin:
  Search by traceId=abc123 → see entire request tree
  → OrderService: 200ms total
    → InventoryService call: 30ms
    → PaymentService call: 160ms ← HERE is the slowness
      → Stripe API call: 150ms ← HERE is the root cause
```

### Trap: TraceId Not Propagated to @Async Threads
```java
// WRONG ❌ — traceId lost in async thread
@Async
public void sendNotification(Order order) {
    // MDC (Mapped Diagnostic Context) is ThreadLocal
    // ThreadLocal is NOT inherited by thread pool threads
    log.info("Sending notification"); // traceId = empty!
}

// FIX — use DelegatingSecurityContextExecutor + Micrometer tracing context propagation
// Spring Boot 3 with Micrometer auto-configures context propagation for @Async
// IF you use the TaskExecutor bean configured by Spring

@Bean
public TaskExecutor asyncExecutor(Tracer tracer) {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.initialize();
    // Wrap to propagate Micrometer trace context to spawned threads
    return new ContextPropagatingTaskExecutor(executor);
}
```

---

## Quick Reference

| What to Monitor | Micrometer Type | Example Metric |
|---|---|---|
| How many times X happened | Counter | `orders_placed_total` |
| How long X takes (+ percentiles) | Timer | `orders_processing_seconds_p99` |
| How many X exist right now | Gauge | `orders_pending`, `db_connections_active` |
| Distribution of values | DistributionSummary | `order_amount_dollars` |
| JVM health | Auto (JVM Metrics) | `jvm_memory_used`, `jvm_gc_pause` |

---

## Interview Cheat Sheet

> "In production, Actuator is locked to expose only health and prometheus — /env is never exposed because it prints secrets. Custom HealthIndicators let me model business-critical dependencies (payment gateway, email provider) separately from infrastructure health, and feed K8s readiness probes so the pod is pulled from the load balancer when downstream is degraded. @Timed only works on Spring-managed beans — on non-Spring objects I wire the Timer manually in the constructor. Distributed tracing with Micrometer Tracing is zero-code — just add the bridge dependency and configure sampling. The traceId propagates through HTTP headers automatically; for @Async I use a ContextPropagatingTaskExecutor so the traceId appears in async thread logs for correlation."
