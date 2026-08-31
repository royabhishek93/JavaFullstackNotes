# Resilience & Noisy Neighbor

## The Problem

In shared infrastructure, **one misbehaving tenant can degrade all others**.

```
Tenant A: launches bulk import job → 500 DB connections consumed
Tenant B: normal user request     → connection pool exhausted → 503 error
Tenant C: normal user request     → 503 error  (never touched Tenant A's data)
```

This is the **noisy neighbor problem** — the most dangerous operational risk in multitenant SaaS.

---

## 1. Noisy Neighbor Sources & Mitigations

```
┌──────────────────────┬────────────────────────┬───────────────────────────────┐
│ Noisy Neighbor Source│ Symptom                │ Mitigation                    │
├──────────────────────┼────────────────────────┼───────────────────────────────┤
│ DB connection hog    │ Pool exhaustion         │ RDS Proxy + per-tenant limit  │
│ CPU-heavy query      │ Shared CPU spike        │ DB query timeout per tenant   │
│ API request flood    │ Thread pool exhaustion  │ Rate limiting (Bucket4j)      │
│ Large file upload    │ S3 bandwidth throttle   │ Per-tenant upload size limit  │
│ Cache stampede       │ Redis CPU spike         │ Tenant-prefixed keys + limits │
│ Async job flood      │ Queue starvation        │ Separate queues per tier      │
└──────────────────────┴────────────────────────┴───────────────────────────────┘
```

---

## 2. Rate Limiting — Bucket4j + Redis (Service Level)

API Gateway rate limiting is per-IP. Service-level rate limiting is **per-tenant**, regardless of IP.

```xml
<dependency>
    <groupId>com.giffing.bucket4j.spring.boot.starter</groupId>
    <artifactId>bucket4j-spring-boot-starter</artifactId>
</dependency>
```

```java
@Component
public class TenantRateLimitFilter extends OncePerRequestFilter {

    private final ProxyManager<String> proxyManager;  // Bucket4j Redis proxy

    private static final Map<String, Bandwidth> PLAN_LIMITS = Map.of(
        "FREE",       Bandwidth.simple(100, Duration.ofMinutes(1)),   // 100 req/min
        "PRO",        Bandwidth.simple(1_000, Duration.ofMinutes(1)), // 1k req/min
        "ENTERPRISE", Bandwidth.simple(10_000, Duration.ofMinutes(1)) // 10k req/min
    );

    @Override
    protected void doFilterInternal(HttpServletRequest req,
                                    HttpServletResponse res,
                                    FilterChain chain)
            throws ServletException, IOException {

        String tenantId = TenantContextHolder.getTenantId();
        String plan = tenantRegistry.getPlan(tenantId); // cached in Redis

        Bandwidth limit = PLAN_LIMITS.getOrDefault(plan, PLAN_LIMITS.get("FREE"));

        // Key: "rl:tenant:{id}" — one bucket per tenant, stored in Redis
        Bucket bucket = proxyManager.builder()
            .build("rl:tenant:" + tenantId,
                () -> BucketConfiguration.builder()
                    .addLimit(limit)
                    .build());

        ConsumptionProbe probe = bucket.tryConsumeAndReturnRemaining(1);

        if (!probe.isConsumed()) {
            long retryAfterSeconds = probe.getNanosToWaitForRefill() / 1_000_000_000;
            res.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
            res.setHeader("X-Rate-Limit-Retry-After-Seconds",
                String.valueOf(retryAfterSeconds));
            res.setHeader("X-Tenant-Plan", plan);
            res.getWriter().write("{\"error\":\"Rate limit exceeded\"}");
            return;
        }

        res.setHeader("X-Rate-Limit-Remaining",
            String.valueOf(probe.getRemainingTokens()));
        chain.doFilter(req, res);
    }
}
```

---

## 3. Bulkhead Pattern — Thread Pool Isolation (Resilience4j)

Prevent one tenant from consuming all application threads.

```xml
<dependency>
    <groupId>io.github.resilience4j</groupId>
    <artifactId>resilience4j-spring-boot3</artifactId>
</dependency>
```

```java
@Service
public class TenantIsolatedExecutor {

    // Separate thread pools per plan tier — not per tenant (avoid thread explosion)
    private final ThreadPoolBulkhead freeBulkhead = ThreadPoolBulkhead.of(
        "free-tier",
        ThreadPoolBulkheadConfig.custom()
            .maxThreadPoolSize(10)   // max 10 threads for ALL free tenants combined
            .coreThreadPoolSize(5)
            .queueCapacity(20)
            .build()
    );

    private final ThreadPoolBulkhead proBulkhead = ThreadPoolBulkhead.of(
        "pro-tier",
        ThreadPoolBulkheadConfig.custom()
            .maxThreadPoolSize(50)
            .coreThreadPoolSize(20)
            .queueCapacity(100)
            .build()
    );

    private final ThreadPoolBulkhead enterpriseBulkhead = ThreadPoolBulkhead.of(
        "enterprise-tier",
        ThreadPoolBulkheadConfig.custom()
            .maxThreadPoolSize(200)
            .coreThreadPoolSize(100)
            .queueCapacity(500)
            .build()
    );

    public <T> CompletableFuture<T> executeForTenant(
            String tenantId, String plan,
            Supplier<T> task) {

        ThreadPoolBulkhead bulkhead = switch (plan) {
            case "ENTERPRISE" -> enterpriseBulkhead;
            case "PRO"        -> proBulkhead;
            default           -> freeBulkhead;
        };

        TenantContext ctx = TenantContextHolder.get(); // capture before switching threads

        return ThreadPoolBulkhead.decorateSupplier(bulkhead, () -> {
            TenantContextHolder.set(ctx); // restore on worker thread
            try {
                return task.get();
            } finally {
                TenantContextHolder.clear();
            }
        }).get()
        .exceptionally(ex -> {
            if (ex.getCause() instanceof BulkheadFullException) {
                throw new TenantCapacityExceededException(tenantId, plan);
            }
            throw new RuntimeException(ex);
        });
    }
}
```

---

## 4. Circuit Breaker — Per Downstream Service

Prevent cascading failures when a downstream service (DB, external API) degrades:

```java
@Service
public class OrderService {

    private final CircuitBreaker dbCircuitBreaker = CircuitBreaker.of(
        "order-db",
        CircuitBreakerConfig.custom()
            .failureRateThreshold(50)          // open if 50% calls fail
            .waitDurationInOpenState(Duration.ofSeconds(30))
            .slidingWindowSize(10)
            .permittedNumberOfCallsInHalfOpenState(3)
            .build()
    );

    public List<OrderDto> getOrders(Pageable pageable) {
        return CircuitBreaker.decorateSupplier(dbCircuitBreaker,
            () -> orderRepository.findAll(pageable)
                                 .map(OrderDto::from)
                                 .getContent()
        ).get();
        // Falls through to GlobalExceptionHandler on CallNotPermittedException
    }
}
```

```java
// Global handler for circuit breaker open state
@ExceptionHandler(CallNotPermittedException.class)
public ResponseEntity<ErrorResponse> handleCircuitOpen(CallNotPermittedException e) {
    return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
        .header("Retry-After", "30")
        .body(new ErrorResponse("SERVICE_UNAVAILABLE",
            "Service temporarily unavailable. Please retry in 30 seconds."));
}
```

---

## 5. DB Query Timeout — Per Tenant Statement Limit

Prevent one tenant's runaway query from holding DB locks:

```java
@Component
public class SchemaRoutingInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest req,
                             HttpServletResponse res, Object handler) {
        if (!TenantContextHolder.hasContext()) return true;

        String schema = TenantContextHolder.getSchemaName();
        String plan   = tenantRegistry.getPlan(TenantContextHolder.getTenantId());

        // Set search_path AND statement timeout in one round-trip
        int timeoutMs = switch (plan) {
            case "ENTERPRISE" -> 30_000;  // 30s
            case "PRO"        -> 10_000;  // 10s
            default           -> 3_000;   // 3s for FREE
        };

        jdbc.execute(String.format(
            "SET search_path TO %s, public; SET statement_timeout = %d",
            schema, timeoutMs));
        return true;
    }
}
```

---

## 6. Separate SQS Queues per Tenant Tier

For async jobs, don't let free-tier bulk jobs starve enterprise-tier operations:

```
enterprise-jobs-queue  → consumed by 20 worker threads (high priority)
pro-jobs-queue         → consumed by 10 worker threads
free-jobs-queue        → consumed by  2 worker threads (low priority)
```

```java
@Service
public class AsyncJobDispatcher {

    private final SqsTemplate sqsTemplate;

    public void dispatch(String tenantId, JobRequest job) {
        String plan = tenantRegistry.getPlan(tenantId);
        String queueUrl = switch (plan) {
            case "ENTERPRISE" -> enterpriseQueueUrl;
            case "PRO"        -> proQueueUrl;
            default           -> freeQueueUrl;
        };

        sqsTemplate.send(queueUrl, job,
            MessageAttributeValue.builder()
                .stringValue(tenantId)
                .dataType("String")
                .build());
    }
}
```

---

## 7. Resilience Summary for Architect Interviews

```
Question: "How do you prevent one tenant from affecting others?"

Answer (layered defense):

Layer 1 — API Gateway:      Per-tenant usage plan, throttling rules
Layer 2 — Rate Limiter:     Bucket4j + Redis, per-tenant token bucket
Layer 3 — Bulkhead:         Resilience4j thread pool per tier
Layer 4 — DB Timeout:       PostgreSQL statement_timeout per plan
Layer 5 — Connection Pool:  RDS Proxy limits connections per client
Layer 6 — Queue Priority:   Separate SQS queues per tier
Layer 7 — Circuit Breaker:  Fail fast on downstream degradation
Layer 8 — Monitoring:       Alert on per-tier latency breach
```
