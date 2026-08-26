# Q11: Spring Boot Production Traps — 15-Year Architect Interview (The 3 AM Incidents)

**Study Time:** 25-30 minutes | **Frequency:** Every architect round 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> These are not textbook questions. These are production incidents. A 15-year architect answers from experience — "I've been woken up by this."

---

## Trap 1: OSIV (Open Session In View) — Silent N+1 Factory

### The Incident
App runs fine in dev. In production, DB CPU spikes to 100%, connection pool exhausts, requests time out. No obvious code change. Nobody touched the queries.

### Root Cause
```yaml
# Spring Boot default — almost nobody knows this is ON:
spring.jpa.open-in-view=true   # DEFAULT ← the culprit
```

```
What OSIV does:
  HTTP Request arrives
       ↓
  Hibernate session OPENS  ← here (before controller)
       ↓
  Service layer runs (TX commits, but session stays open)
       ↓
  Controller runs
       ↓
  View/serializer runs — accesses lazy fields → Hibernate issues SELECT ← N+1 here
       ↓
  HTTP Response sent
       ↓
  Hibernate session CLOSES  ← only here

Result:
  - Jackson serializes Order → accesses order.getItems() → SELECT * FROM items WHERE order_id=1
  - 100 orders in response → 100 extra SELECTs → N+1
  - DB connection held for ENTIRE request duration → pool exhaustion under load
```

### The Silent Part
No exception is thrown. Everything "works." Performance degrades gradually under load.

### Fix
```yaml
spring.jpa.open-in-view=false   # disable OSIV — forces explicit fetching
```

```java
// After disabling OSIV, you MUST load associations explicitly:

// Option 1: JPQL fetch join
@Query("SELECT o FROM Order o JOIN FETCH o.items WHERE o.id = :id")
Optional<Order> findByIdWithItems(@Param("id") Long id);

// Option 2: @EntityGraph
@EntityGraph(attributePaths = {"items", "items.product"})
Optional<Order> findById(Long id);

// Option 3: DTO projection — only load what you need
@Query("SELECT new com.example.OrderSummaryDTO(o.id, o.status, COUNT(i)) " +
       "FROM Order o LEFT JOIN o.items i WHERE o.userId = :userId GROUP BY o.id")
List<OrderSummaryDTO> findSummariesByUser(@Param("userId") Long userId);
```

### Interview Answer
> "OSIV is enabled by default in Spring Boot. It keeps the Hibernate session open for the entire HTTP request lifetime, allowing lazy loading in the view/controller layer. In production, this causes N+1 queries in serializers, holds DB connections for the full request duration exhausting HikariCP, and causes unpredictable DB load. I always set `spring.jpa.open-in-view=false` and load associations explicitly in the service layer."

---

## Trap 2: HikariCP Connection Pool Exhaustion

### The Incident
App is "healthy" — JVM heap fine, CPU fine, pods running. But requests pile up, latency spikes to 30s, then timeouts. DB shows `max_connections` not hit. Restarting the app fixes it for 2 hours, then it happens again.

### Root Cause: @Transactional Holding Connection During External Call

```java
// WRONG ❌ — DB connection held for the entire method including HTTP call
@Transactional
public Order processOrder(CreateOrderRequest req) {
    Order order = orderRepo.save(new Order(req));  // connection acquired here

    // HTTP call to payment service — takes 2-5 seconds
    PaymentResult result = paymentClient.charge(req.getPaymentToken(), req.getAmount());
    // Connection is HELD during this entire HTTP call ← pool exhaustion

    order.setPaymentStatus(result.getStatus());
    return orderRepo.save(order);  // connection released after this
}
```

```
With 20 connections in pool, 20 concurrent requests each waiting 3s for payment API
= all 20 connections held for 3s
= request 21 waits for connection → SQLTimeoutException after 30s
```

### Fix: Minimise Transaction Scope

```java
// CORRECT ✅ — DB connection released before HTTP call
@Service
public class OrderService {

    @Transactional
    public Order createOrderRecord(CreateOrderRequest req) {
        return orderRepo.save(new Order(req));  // TX commits, connection released
    }

    @Transactional
    public Order updatePaymentStatus(Long orderId, String status) {
        Order order = orderRepo.findById(orderId).orElseThrow();
        order.setPaymentStatus(status);
        return orderRepo.save(order);           // TX commits, connection released
    }

    // Orchestrator — NOT @Transactional, no connection held
    public Order processOrder(CreateOrderRequest req) {
        Order order = createOrderRecord(req);                    // connection: 5ms
        PaymentResult result = paymentClient.charge(...);       // no connection held: 2-5s
        return updatePaymentStatus(order.getId(), result.getStatus()); // connection: 5ms
    }
}
```

### HikariCP Tuning

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 20         # formula: (2 × CPU cores) + effective_spindle_count
      minimum-idle: 5               # keep 5 connections warm
      connection-timeout: 3000      # fail fast after 3s — don't queue forever
      idle-timeout: 600000          # 10min idle before closing
      max-lifetime: 1800000         # 30min max — avoids stale connections
      leak-detection-threshold: 5000  # warn if connection held > 5s — catches Trap 2 above
      connection-test-query: SELECT 1 # validate before use (for MySQL)
```

### Connection Leak Detection Log
```
HikariPool-1 - Connection leak detection triggered for connection
  com.mysql.cj.jdbc.ConnectionImpl@7f3b2c1 on thread http-nio-8080-exec-3,
  stack trace follows:
    at OrderService.processOrder(OrderService.java:45)   ← your code holding the connection
```

---

## Trap 3: @Cacheable Production Traps

### Trap 3a: Cache Stampede (Dog-Pile Effect)

```
Cache entry expires at 14:00:00.000
1000 concurrent requests arrive at 14:00:00.001
All 1000 miss cache → all 1000 query DB simultaneously
DB overwhelmed → timeouts → cascading failure
```

```java
// No built-in fix in Spring Cache — need probabilistic early expiry or lock

// Fix 1: Caffeine with probabilistic refresh (expires before TTL, not after)
@Bean
public CacheManager cacheManager() {
    CaffeineCacheManager manager = new CaffeineCacheManager("products");
    manager.setCaffeine(
        Caffeine.newBuilder()
                .expireAfterWrite(10, TimeUnit.MINUTES)
                .refreshAfterWrite(8, TimeUnit.MINUTES) // refresh before expiry
                .maximumSize(10_000)
    );
    return manager;
}

// Fix 2: Redis with distributed lock around cache population
@Service
public class ProductService {

    @Autowired
    private RedisTemplate<String, Product> redisTemplate;

    @Autowired
    private RedissonClient redisson;

    public Product getProduct(Long id) {
        String key = "product:" + id;
        Product cached = (Product) redisTemplate.opsForValue().get(key);
        if (cached != null) return cached;

        // Distributed lock — only 1 thread populates, rest wait
        RLock lock = redisson.getLock("lock:product:" + id);
        lock.lock(5, TimeUnit.SECONDS);
        try {
            // Double-check after acquiring lock
            cached = (Product) redisTemplate.opsForValue().get(key);
            if (cached != null) return cached;

            Product product = productRepo.findById(id).orElseThrow();
            redisTemplate.opsForValue().set(key, product, 10, TimeUnit.MINUTES);
            return product;
        } finally {
            lock.unlock();
        }
    }
}
```

### Trap 3b: @Cacheable on Private/Same-Class Method (Proxy Issue)

```java
// WRONG ❌ — same class, same proxy problem as @Transactional
@Service
public class ProductService {

    public List<Product> getFeaturedProducts() {
        return this.getTopProducts(10); // self-invocation — @Cacheable ignored ❌
    }

    @Cacheable("top-products")
    private List<Product> getTopProducts(int limit) { // also: private method → no proxy
        return productRepo.findTop(limit);
    }
}
```

### Trap 3c: @CacheEvict on Wrong Method

```java
// WRONG ❌ — evicts cache key "product-42" but cached with key "42"
@CacheEvict(value = "products", key = "'product-' + #id")
public void updateProduct(Long id, Product updated) { ... }

@Cacheable(value = "products", key = "#id")  // cached as "42"
public Product getProduct(Long id) { ... }

// Fix: consistent key strategy — use SpEL, centralise in @CacheConfig
@CacheConfig(cacheNames = "products")
@Service
public class ProductService {
    @Cacheable(key = "#id")
    public Product getProduct(Long id) { ... }

    @CacheEvict(key = "#product.id")
    public void updateProduct(Product product) { ... }

    @CachePut(key = "#result.id")      // update cache after save
    public Product saveProduct(Product product) { ... }
}
```

---

## Trap 4: @Scheduled in Clustered Environment

### The Incident
Email digest runs every night at 8 PM. Users receive 3 emails. You have 3 pods.

```java
@Scheduled(cron = "0 0 20 * * *")  // every pod runs this ❌
public void sendNightlyDigest() {
    userService.getAllUsers().forEach(emailService::sendDigest);
}
// 3 pods × 1 execution = 3 emails per user
```

### Fix: ShedLock — Distributed Lock for @Scheduled

```xml
<dependency>
    <groupId>net.javacrumbs.shedlock</groupId>
    <artifactId>shedlock-spring</artifactId>
    <version>5.10.0</version>
</dependency>
<dependency>
    <groupId>net.javacrumbs.shedlock</groupId>
    <artifactId>shedlock-provider-jdbc-template</artifactId>
    <version>5.10.0</version>
</dependency>
```

```sql
-- DB table for distributed lock
CREATE TABLE shedlock (
    name        VARCHAR(64)  NOT NULL,
    lock_until  TIMESTAMP    NOT NULL,
    locked_at   TIMESTAMP    NOT NULL,
    locked_by   VARCHAR(255) NOT NULL,
    PRIMARY KEY (name)
);
```

```java
@Configuration
@EnableScheduling
@EnableSchedulerLock(defaultLockAtMostFor = "10m")
public class SchedulerConfig {

    @Bean
    public LockProvider lockProvider(DataSource dataSource) {
        return new JdbcTemplateLockProvider(dataSource);
    }
}

@Service
public class DigestService {

    @Scheduled(cron = "0 0 20 * * *")
    @SchedulerLock(name = "nightly-digest", lockAtLeastFor = "5m", lockAtMostFor = "9m")
    public void sendNightlyDigest() {
        // Only 1 pod acquires lock → only 1 execution ✅
        userService.getAllUsers().forEach(emailService::sendDigest);
    }
}
```

### Trap: @Scheduled Default Single Thread

```java
// Default scheduler has 1 thread
// Job A runs for 5 minutes → Job B (every 1 min) misses 5 executions

@Bean
public TaskScheduler taskScheduler() {
    ThreadPoolTaskScheduler scheduler = new ThreadPoolTaskScheduler();
    scheduler.setPoolSize(5);                          // 5 scheduler threads
    scheduler.setThreadNamePrefix("scheduled-task-");
    scheduler.setErrorHandler(t ->
        log.error("Scheduled task error: {}", t.getMessage(), t));
    return scheduler;
}
```

---

## Trap 5: SecurityContext Not Propagated to @Async Thread

### The Incident
JWT auth works fine in controllers. But in @Async email service, `SecurityContextHolder.getContext().getAuthentication()` returns null. Audit logs show null user.

```java
// SecurityContextHolder uses ThreadLocal — @Async runs on NEW thread → null
@Async
public void sendOrderConfirmation(Long orderId) {
    String currentUser = SecurityContextHolder.getContext()
                                              .getAuthentication()
                                              .getName(); // NullPointerException ❌
    auditLog.record(currentUser, "EMAIL_SENT", orderId);
}
```

### Fix: DelegatingSecurityContextAsyncTaskExecutor

```java
@Configuration
@EnableAsync
public class AsyncSecurityConfig {

    @Bean(name = "securityAwareExecutor")
    public Executor securityAwareExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(10);
        executor.setMaxPoolSize(50);
        executor.setQueueCapacity(200);
        executor.setThreadNamePrefix("secure-async-");
        executor.initialize();

        // Wraps executor — copies SecurityContext to each async thread
        return new DelegatingSecurityContextAsyncTaskExecutor(executor);
    }
}

@Async("securityAwareExecutor")
public void sendOrderConfirmation(Long orderId) {
    String currentUser = SecurityContextHolder.getContext()
                                              .getAuthentication()
                                              .getName(); // works ✅
}
```

### Also: MDC (Trace IDs) Not Propagated

```java
// MDC (for traceId in logs) is also ThreadLocal — same problem
// Fix: TaskDecorator
@Bean
public Executor mdcAwareExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setTaskDecorator(runnable -> {
        Map<String, String> mdcContext = MDC.getCopyOfContextMap();
        return () -> {
            try {
                if (mdcContext != null) MDC.setContextMap(mdcContext);
                runnable.run();
            } finally {
                MDC.clear();
            }
        };
    });
    executor.initialize();
    return executor;
}
```

---

## Trap 6: @TransactionalEventListener — Data Not Visible to Listener

### The Incident
Order placed, OrderPlacedEvent fired, email service consumes event, queries DB for the order — `EntityNotFoundException`. The order "doesn't exist" even though it was just saved.

```java
@Transactional
public void placeOrder(Order order) {
    orderRepo.save(order);
    eventPublisher.publishEvent(new OrderPlacedEvent(order.getId()));
    // Event fires HERE — before commit
    // Listener runs, queries DB → order not committed yet → not found ❌
}

@EventListener  // runs synchronously BEFORE outer TX commits
public void onOrderPlaced(OrderPlacedEvent event) {
    Order order = orderRepo.findById(event.getOrderId()).orElseThrow(); // EntityNotFoundException
    emailService.send(order);
}
```

### Fix: @TransactionalEventListener(phase = AFTER_COMMIT)

```java
@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
public void onOrderPlaced(OrderPlacedEvent event) {
    // Runs AFTER outer TX commits — order is now visible in DB ✅
    Order order = orderRepo.findById(event.getOrderId()).orElseThrow();
    emailService.send(order);
}

// IMPORTANT: AFTER_COMMIT listener runs in the ORIGINAL thread after commit.
// If you do DB writes in the listener, they need their own new TX:
@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
@Transactional(propagation = Propagation.REQUIRES_NEW)  // new TX for listener writes
public void onOrderPlaced(OrderPlacedEvent event) {
    auditRepo.save(new AuditLog("ORDER_PLACED", event.getOrderId())); // needs new TX ✅
}
```

### TransactionPhase Options

| Phase | When it runs |
|-------|-------------|
| `BEFORE_COMMIT` | Just before commit — TX still open, can write to DB |
| `AFTER_COMMIT` (use this) | After successful commit — data visible to all |
| `AFTER_ROLLBACK` | After TX rolled back — use for compensating actions |
| `AFTER_COMPLETION` | After commit OR rollback — cleanup (close resources) |

---

## Trap 7: @Transactional(readOnly=true) Misunderstanding

### What Most Devs Think
> "readOnly=true gives automatic performance boost — DB does optimised read-only transaction."

### What Actually Happens

```java
@Transactional(readOnly = true)
public List<Product> getAllProducts() {
    return productRepo.findAll();
}
```

```
readOnly=true effects (actual):
  ✅ Hibernate FlushMode set to NEVER — dirty checking skipped (minor CPU saving)
  ✅ Hibernate skips version checking for @Version fields
  ✅ Some JDBC drivers forward to read replica if routing DataSource configured
  ❌ Does NOT automatically route to read replica without explicit config
  ❌ Does NOT prevent writes at DB level (no SQL "SET TRANSACTION READ ONLY" on most drivers)
  ❌ Does NOT give significant performance boost for simple queries
```

### Actual Read Replica Routing Requires Explicit Configuration

```java
// AbstractRoutingDataSource — routes based on TX readOnly flag
public class ReadWriteRoutingDataSource extends AbstractRoutingDataSource {

    @Override
    protected Object determineCurrentLookupKey() {
        boolean isReadOnly = TransactionSynchronizationManager.isCurrentTransactionReadOnly();
        return isReadOnly ? "read-replica" : "primary";
    }
}

@Bean
public DataSource routingDataSource(
        @Qualifier("primaryDataSource") DataSource primary,
        @Qualifier("replicaDataSource") DataSource replica) {

    ReadWriteRoutingDataSource routing = new ReadWriteRoutingDataSource();
    routing.setDefaultTargetDataSource(primary);
    routing.setTargetDataSources(Map.of(
        "primary", primary,
        "read-replica", replica
    ));
    return routing;
}
// NOW readOnly=true routes to replica ✅
```

---

## Trap 8: Spring Security FilterChain (Spring Boot 3 / Security 6)

### The Breaking Change
`WebSecurityConfigurerAdapter` removed in Spring Security 6 / Spring Boot 3.

```java
// WRONG ❌ — Spring Boot 3 compile error
@Configuration
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    @Override
    protected void configure(HttpSecurity http) throws Exception { ... }
}

// CORRECT ✅ — Spring Boot 3 / Security 6
@Configuration
@EnableWebSecurity
@EnableMethodSecurity  // replaces @EnableGlobalMethodSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())               // stateless REST API
            .sessionManagement(session ->
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/actuator/health/**").permitAll()
                .requestMatchers("/api/auth/**").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .addFilterBefore(jwtAuthFilter(), UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    @Bean
    public JwtAuthenticationFilter jwtAuthFilter() {
        return new JwtAuthenticationFilter(jwtService, userDetailsService);
    }
}

// Method-level security (replaces @PreAuthorize on controller)
@PreAuthorize("hasRole('ADMIN') or #userId == authentication.principal.id")
public UserProfile getProfile(Long userId) { ... }
```

### CSRF: Why Disabled for REST APIs

```
CSRF (Cross-Site Request Forgery) protection:
  Browser sends cookie automatically with every request to your domain.
  Attacker can trick browser into making requests with valid cookie.
  Spring adds CSRF token to validate request came from YOUR page.

Why disable for REST APIs:
  REST APIs use JWT in Authorization header — NOT cookies.
  Browser doesn't auto-send Authorization headers for cross-origin requests.
  Therefore: no CSRF risk → disable to simplify stateless APIs.

Keep CSRF enabled for: server-rendered forms, session-based auth.
```

---

## Trap 9: Bean Initialization — BPP Dependency Breaks Proxy

### The Silent Bug

```
Scenario:
  MetricsAspect (a BeanPostProcessor) @Autowired MetricsService
  → Spring must create MetricsService early to satisfy BPP
  → MetricsService created BEFORE @Transactional BPP runs
  → MetricsService has NO @Transactional proxy

Spring logs (easy to miss):
  "Bean 'metricsService' is not eligible for getting processed by
   all BeanPostProcessors (for example: not eligible for auto-proxying)"
```

```java
// WRONG ❌ — BPP depends on a regular bean
@Component
public class MetricsAspect implements BeanPostProcessor {
    @Autowired
    private MetricsService metricsService; // forces early creation of MetricsService
    // MetricsService @Transactional methods silently not transactional
}

// FIX ✅ — use ApplicationContext to lazy-get the bean
@Component
public class MetricsAspect implements BeanPostProcessor, ApplicationContextAware {

    private ApplicationContext context;

    @Override
    public void setApplicationContext(ApplicationContext ctx) {
        this.context = ctx;
    }

    @Override
    public Object postProcessAfterInitialization(Object bean, String beanName) {
        MetricsService metrics = context.getBean(MetricsService.class); // lazy get ✅
        // ...
        return bean;
    }
}
```

---

## Trap 10: @ConfigurationProperties vs @Value in Production

```java
// @Value — fragile, fails silently
@Value("${payment.gateway.url}")
private String gatewayUrl; // NoSuchBeanDefinitionException if key missing at startup

@Value("${payment.timeout:5000}")  // default only if you remember to add it
private int timeout;

// @ConfigurationProperties — validated, structured, IDE-friendly
@Component
@ConfigurationProperties(prefix = "payment")
@Validated
public class PaymentConfig {

    @NotBlank
    private String gatewayUrl;     // fails at startup with clear message if missing

    @Min(1000) @Max(30000)
    private int timeoutMs = 5000;  // default in code, not in property string

    @NotNull
    private RetryConfig retry;     // nested config objects — impossible with @Value

    // getters/setters
}

public class RetryConfig {
    private int maxAttempts = 3;
    private Duration backoff = Duration.ofSeconds(1);
}
```

```yaml
# application.yml
payment:
  gateway-url: https://payment.example.com
  timeout-ms: 5000
  retry:
    max-attempts: 3
    backoff: 1s

# application-prod.yml (overrides above for prod profile)
payment:
  gateway-url: https://payment-prod.example.com
  timeout-ms: 3000
```

---

## Master Cheat Sheet: The 15-Year Trap Questions

```
1. OSIV (spring.jpa.open-in-view=true by default)
   → N+1 in serializer, connection held for full request
   → Fix: spring.jpa.open-in-view=false + explicit @EntityGraph / JOIN FETCH

2. HikariCP exhaustion
   → @Transactional wrapping external HTTP call holds connection
   → Fix: narrow TX scope, set leakDetectionThreshold=5000
   → Sizing: (2 × CPU cores) + spindle count, connection-timeout=3000

3. @Cacheable proxy trap
   → Same-class, private method: proxy bypassed, caching ignored
   → Cache stampede: distributed lock or refresh-before-expiry
   → @CacheEvict with wrong key = stale cache forever

4. @Scheduled in cluster
   → Runs on every pod → duplicate execution
   → Fix: ShedLock + JDBC-backed distributed lock
   → Default scheduler has 1 thread → jobs queue up

5. SecurityContext in @Async
   → ThreadLocal not copied to new thread → null Authentication
   → Fix: DelegatingSecurityContextAsyncTaskExecutor
   → Same for MDC traceId: TaskDecorator

6. @TransactionalEventListener
   → @EventListener fires BEFORE commit → data not visible
   → Fix: @TransactionalEventListener(phase = AFTER_COMMIT)
   → If listener writes to DB: add @Transactional(REQUIRES_NEW)

7. readOnly=true misunderstanding
   → Only skips Hibernate dirty check + flush
   → Does NOT route to replica without AbstractRoutingDataSource config

8. Spring Security 6 breaking change
   → WebSecurityConfigurerAdapter removed
   → Use SecurityFilterChain @Bean + lambda DSL
   → CSRF disabled for stateless JWT APIs (Authorization header ≠ cookie)

9. BPP dependency breaks @Transactional proxy
   → BPP @Autowiring regular bean → bean created before proxy BPP runs
   → Fix: lazy ApplicationContext.getBean() in BPP methods

10. @ConfigurationProperties vs @Value
    → @Value: fails silently, no validation, no nesting
    → @ConfigurationProperties + @Validated: fails fast with message
```

---

## Key 3 AM Questions

**Q: App was healthy at midnight, dead at 8 AM. What do you check first?**
HikariCP active connections (at max), OSIV N+1 under load, scheduled job that started at 7 AM holding connections, thread pool exhaustion.

**Q: User got someone else's data. Security audit shows no code bug. How?**
Missing tenant filter (OSIV-related lazy load returned wrong tenant's data), or cache key collision (two users share a cache key because SpEL key expression didn't include tenant).

**Q: 3 pods, each running a @Scheduled job — emails sent 3x. Fix without code deploy?**
Scale down to 1 pod as immediate fix. Proper fix: ShedLock with DB-backed lock. Long term: move to dedicated scheduler service or use K8s CronJob (1 pod for scheduling).

**Q: @Transactional method works in tests, fails in production with no rollback on exception.**
Exception is checked (non-RuntimeException) — Spring only rolls back on RuntimeException by default. Fix: `@Transactional(rollbackFor = Exception.class)`. Or exception is swallowed somewhere in the call chain.

**Q: New developer added a BeanPostProcessor. Next morning, @Transactional stopped working on one service.**
Classic BPP dependency trap — the new BPP @Autowired that service, forcing early creation before the @Transactional proxy BPP ran. Check Spring startup logs for "not eligible for auto-proxying".
