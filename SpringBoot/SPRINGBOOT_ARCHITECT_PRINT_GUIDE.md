# Spring Boot — Complete Architect Interview Guide (15-Year Level)
**Print Settings:** Portrait, font size 10pt, narrow margins
**Coverage:** 11 topics · Spring Boot internals · Production traps · K8s · WebFlux

---

## QUICK REFERENCE — The Proxy Rule (Foundation of Everything)

```
ALL Spring annotations that add behaviour (@Transactional, @Async, @Cacheable, @AOP)
work via PROXY. The proxy intercepts the call and adds the behaviour.

PROXY IS BYPASSED when:
  1. this.method()          ← self-invocation (most common bug)
  2. private method()       ← proxy can't intercept private
  3. final method()         ← CGLIB can't override final

CONSEQUENCE:
  this.transactionalMethod()  → NO transaction
  this.asyncMethod()          → runs synchronously (no error thrown!)
  this.cacheableMethod()      → not cached

FIX: Extract to a separate @Service bean, or inject self via @Autowired
```

---

## 1. @SpringBootApplication — Auto-configuration

```
@SpringBootApplication = @SpringBootConfiguration + @EnableAutoConfiguration + @ComponentScan

Auto-config flow:
  Classpath scan → spring.factories / AutoConfiguration.imports
  → @Conditional checks (OnClassCondition, OnBeanCondition, OnPropertyCondition)
  → Matching configs activated → beans created

Key conditionals:
  @ConditionalOnClass(DataSource.class)     — activates only if class is on classpath
  @ConditionalOnMissingBean(DataSource.class) — activates only if bean not already defined
  @ConditionalOnProperty("spring.datasource.url") — activates only if property set

Disable specific auto-config:
  @SpringBootApplication(exclude = {DataSourceAutoConfiguration.class})
```

**Q: How does Tomcat start automatically?**
`spring-boot-starter-web` puts `tomcat-embed-core.jar` on classpath → `EmbeddedWebServerFactoryCustomizerAutoConfiguration` activates → creates `TomcatServletWebServerFactory` → starts Tomcat.

---

## 2. Interceptor vs Filter vs AOP

| | Filter | Interceptor | AOP |
|--|--------|-------------|-----|
| Scope | Any servlet (lowest level) | Spring MVC only | Any Spring bean |
| Access | HttpServletRequest/Response | Request + Handler | Method args/return |
| Exception handling | Does NOT reach @ControllerAdvice | Reaches @ControllerAdvice | Reaches @ControllerAdvice |
| Use for | Auth, CORS, encoding | Logging, JWT, rate limit | Metrics, caching |

```
HTTP → Filter → DispatcherServlet → Interceptor.preHandle
     → Controller → Interceptor.postHandle → Response
     → Interceptor.afterCompletion (ALWAYS called, even on exception)
```

```java
@Component
public class JwtInterceptor implements HandlerInterceptor {
    public boolean preHandle(HttpServletRequest req, HttpServletResponse res, Object handler) {
        String token = req.getHeader("Authorization");
        if (!jwtService.isValid(token)) { res.setStatus(401); return false; }
        return true;
    }
}

// Register:
@Configuration
public class WebConfig implements WebMvcConfigurer {
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(jwtInterceptor)
                .addPathPatterns("/api/**")
                .excludePathPatterns("/api/auth/**");
    }
}
```

---

## 3. @Transactional — Proxy Flow

```
Call orderService.placeOrder()
        ↓
Spring Proxy intercepts (CGLIB or JDK proxy)
        ↓
TransactionInterceptor → PlatformTransactionManager
        ↓
BEGIN TRANSACTION (acquire DB connection)
        ↓
Execute placeOrder() body
        ↓
COMMIT (no exception) or ROLLBACK (RuntimeException by default)
        ↓
Release DB connection
```

**Key rules:**
```
Rollback:   RuntimeException only by default
            Fix: @Transactional(rollbackFor = Exception.class) for checked exceptions
Private:    No proxy → no transaction (silent failure)
Self-call:  this.method() → no proxy → no transaction
readOnly:   Skips Hibernate dirty check only — does NOT auto-route to replica
```

**Common interview trap:**
```java
@Transactional
public void outer() {
    inner(); // self-invocation — inner()'s @Transactional IGNORED
}
@Transactional(propagation = REQUIRES_NEW)
public void inner() { ... }
// Fix: inject self, or extract inner() to separate @Service
```

---

## 4. @Transactional Propagation

| Propagation | Outer TX exists | Behaviour |
|---|---|---|
| `REQUIRED` (default) | Yes | Join it |
| `REQUIRED` | No | Create new |
| `REQUIRES_NEW` | Yes | **Suspend outer, create independent TX** |
| `NESTED` | Yes | **Savepoint inside outer TX** |
| `MANDATORY` | Yes | Join it |
| `MANDATORY` | No | **Throw IllegalTransactionStateException** |
| `NOT_SUPPORTED` | Yes | Suspend outer, run without TX |
| `NEVER` | Yes | Throw exception |

```
REQUIRES_NEW vs NESTED:
  REQUIRES_NEW: own connection, commits independently, outer rollback does NOT affect it
                ⚠️ Deadlock risk if touching same tables as outer TX
  NESTED:       same connection, savepoint only, outer rollback KILLS inner too
                Use for: optional sub-steps, batch row processing

MANDATORY: use to enforce contract — "caller must provide a TX"
  Production use: core domain mutations, DDD aggregates
```

**Microservices:** @Transactional does NOT span service boundaries. Use Saga + Transactional Outbox.

---

## 5. AOP — Custom Annotation + @Around

```java
// Custom annotation
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface LogTime {}

// Aspect
@Aspect @Component
public class TimingAspect {
    @Around("@annotation(LogTime)")
    public Object time(ProceedingJoinPoint pjp) throws Throwable {
        long start = System.currentTimeMillis();
        try {
            return pjp.proceed();              // execute real method
        } finally {
            log.info("{} took {}ms", pjp.getSignature(), System.currentTimeMillis() - start);
        }
    }
}
```

**@Around vs @Before/@After:** @Around gives access to return value and full control. Use @Before for pre-checks, @AfterReturning for post-processing, @AfterThrowing for error handling.

---

## 6. @Async Pitfalls

```
Pitfall 1 — Self-invocation:
  this.asyncMethod() → synchronous, no error
  Fix: separate @Service bean

Pitfall 2 — Default thread pool:
  SimpleAsyncTaskExecutor creates a NEW THREAD per call → OOM under load
  Fix: configure ThreadPoolTaskExecutor

Pitfall 3 — Silent exceptions:
  void @Async throws → exception disappears (no log, no alert)
  Fix: AsyncUncaughtExceptionHandler OR return CompletableFuture

Pitfall 4 — @Async + @Transactional:
  Caller's TX never propagates to async thread
  Never pass JPA entities (lazy fields) to @Async — pass IDs

@EnableAsync REQUIRED — without it @Async silently ignored, no error
```

```java
@Configuration @EnableAsync
public class AsyncConfig implements AsyncConfigurer {
    @Bean public Executor getAsyncExecutor() {
        ThreadPoolTaskExecutor e = new ThreadPoolTaskExecutor();
        e.setCorePoolSize(10); e.setMaxPoolSize(50); e.setQueueCapacity(200);
        e.setWaitForTasksToCompleteOnShutdown(true);
        e.setAwaitTerminationSeconds(30);
        e.setThreadNamePrefix("async-");
        e.initialize(); return e;
    }
    @Override
    public AsyncUncaughtExceptionHandler getAsyncUncaughtExceptionHandler() {
        return (ex, method, params) -> log.error("Async failed [{}]: {}", method.getName(), ex.getMessage(), ex);
    }
}
```

**SecurityContext + @Async:** `ThreadLocal` not copied → null Authentication in @Async thread.
Fix: `new DelegatingSecurityContextAsyncTaskExecutor(taskExecutor)`

---

## 7. Bean Lifecycle

```
Constructor
    ↓ @Autowired field/setter injection
    ↓ BeanPostProcessor.postProcessBeforeInitialization()   ← all beans
    ↓ @PostConstruct                                         ← your init code
    ↓ BeanPostProcessor.postProcessAfterInitialization()    ← AOP proxies created HERE
    ↓ Bean ready in ApplicationContext
    ...
    ↓ @PreDestroy                                           ← your cleanup code
    ↓ Bean destroyed
```

```
@PostConstruct:  safe to use @Autowired dependencies (unlike constructor)
                 Use for: cache warm-up, schema validation, connection init
@PreDestroy:     NOT called for prototype beans

BeanPostProcessor:  intercepts ALL beans before/after init
                    postProcessAfterInitialization = where @Transactional/@Async proxies created

Prototype-in-singleton trap:
  @Autowired prototype → injected ONCE → same instance always (not prototype!)
  Fix: ObjectProvider<T>.getObject() or @Scope(proxyMode=TARGET_CLASS)

BPP dependency trap:
  BPP @Autowired regular bean → bean created before proxy BPP runs → no @Transactional!
  Fix: lazy ApplicationContext.getBean() inside BPP methods
  Spring warns: "Bean X is not eligible for all BPPs"
```

---

## 8. @ControllerAdvice — Global Exception Handling

```java
@RestControllerAdvice   // = @ControllerAdvice + @ResponseBody
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

    @ExceptionHandler(ResourceNotFoundException.class)
    public ProblemDetail handleNotFound(ResourceNotFoundException ex, HttpServletRequest req) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        p.setProperty("traceId", MDC.get("traceId"));
        p.setProperty("timestamp", Instant.now());
        return p;                        // RFC 7807 format ✅
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ProblemDetail handleValidation(MethodArgumentNotValidException ex) {
        ProblemDetail p = ProblemDetail.forStatus(HttpStatus.BAD_REQUEST);
        p.setProperty("fieldErrors", ex.getBindingResult().getFieldErrors().stream()
            .collect(groupingBy(FieldError::getField, mapping(FieldError::getDefaultMessage, toList()))));
        return p;
    }

    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public ProblemDetail handleAll(Exception ex, HttpServletRequest req) {
        log.error("Unhandled [{}]: {}", req.getRequestURI(), ex.getMessage(), ex);
        ProblemDetail p = ProblemDetail.forStatusAndDetail(INTERNAL_SERVER_ERROR, "Unexpected error");
        p.setProperty("traceId", MDC.get("traceId")); // never expose stack trace to client
        return p;
    }
}
```

```
Handler priority: local @ExceptionHandler → @ControllerAdvice exact match → parent match → catch-all
RFC 7807: spring.mvc.problemdetails.enabled=true (Spring Boot 3.x)
Filter exceptions: NOT caught by @ControllerAdvice — handle in OncePerRequestFilter
@Async exceptions: NOT caught by @ControllerAdvice — use AsyncUncaughtExceptionHandler
Business exceptions → log.warn | Unexpected exceptions → log.error with stack trace
```

---

## 9. WebFlux — Blocking in Reactive Pipeline

```
Netty event loop: 2 × CPU cores threads handle ALL requests
ONE blocked thread → ALL requests on that thread stall

NEVER on event-loop thread:
  JDBC/JPA calls     → subscribeOn(Schedulers.boundedElastic())
  RestTemplate       → use WebClient instead
  Thread.sleep()     → use Mono.delay()
  .block()           → DEADLOCK (event-loop waits for itself)

FIX:
  Mono.fromCallable(() -> jdbcRepo.findById(id))
      .subscribeOn(Schedulers.boundedElastic())   // blocking work on elastic pool

subscribeOn: where SOURCE runs (use to wrap blocking IO)
publishOn:   switches thread DOWNSTREAM from that point

Detection: BlockHound.install() → throws BlockingOperationError in dev/tests

R2DBC: non-blocking DB driver (replaces JPA in pure reactive stack)
       No lazy loading — must use explicit joins/projections

Spring MVC vs WebFlux:
  MVC: thread-per-request, JPA, familiar — use for CRUD-heavy apps
  WebFlux: event-loop, high-concurrency, streaming, I/O-bound — don't mix
```

---

## 10. Graceful Shutdown + K8s Probes

```yaml
# application.yml
server.shutdown: graceful
spring.lifecycle.timeout-per-shutdown-phase: 30s
management.endpoint.health.probes.enabled: true
management.health.livenessstate.enabled: true
management.health.readinessstate.enabled: true
```

```
Shutdown sequence:
  SIGTERM → stop accepting new requests (503 to new connections)
  → wait up to 30s for in-flight requests to drain
  → SmartLifecycle.stop() → @PreDestroy → connection pool close → JVM exit

K8s probes:
  startupProbe   → slow-starting apps, disables liveness until ready
  livenessProbe  → RESTART pod on failure (deadlock, unrecoverable)
  readinessProbe → REMOVE from load balancer (DB down, overloaded — pod stays alive)

Probe endpoints:
  /actuator/health/liveness   → ApplicationContext alive?
  /actuator/health/readiness  → all HealthIndicators UP?

Rules:
  K8s terminationGracePeriodSeconds > Spring timeout (add 10s buffer)
  preStop: sleep 5-10s — prevents traffic race during SIGTERM
  Pool exhausted → fail readiness (not liveness — don't restart healthy pod)
  Deadlock → fail liveness → restart
```

```yaml
# deployment.yaml
terminationGracePeriodSeconds: 60
startupProbe:
  httpGet: { path: /actuator/health/liveness, port: 8080 }
  failureThreshold: 30
  periodSeconds: 10
livenessProbe:
  httpGet: { path: /actuator/health/liveness, port: 8080 }
  periodSeconds: 10
  failureThreshold: 3
readinessProbe:
  httpGet: { path: /actuator/health/readiness, port: 8080 }
  periodSeconds: 5
  failureThreshold: 3
lifecycle:
  preStop:
    exec: { command: ["sh", "-c", "sleep 10"] }
```

---

## 11. Spring Security 6 — FilterChain (Spring Boot 3)

```java
// WebSecurityConfigurerAdapter REMOVED in Spring Boot 3
// New approach: SecurityFilterChain bean

@Configuration @EnableWebSecurity @EnableMethodSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        return http
            .csrf(csrf -> csrf.disable())                      // stateless REST — no CSRF needed
            .sessionManagement(s -> s.sessionCreationPolicy(STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/actuator/health/**").permitAll()
                .requestMatchers("/api/auth/**").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .addFilterBefore(jwtAuthFilter(), UsernamePasswordAuthenticationFilter.class)
            .build();
    }
}
```

```
CSRF disabled for REST APIs:
  REST uses JWT in Authorization header — browser does NOT auto-send headers cross-origin
  Therefore: no CSRF risk for stateless JWT APIs
  Keep CSRF enabled for: session-based auth, form logins

@PreAuthorize("hasRole('ADMIN') or #userId == authentication.principal.id")
  Needs @EnableMethodSecurity (replaces @EnableGlobalMethodSecurity)
```

---

## 12. Production Traps — The 3 AM Incidents

### Trap 1: OSIV — N+1 Factory (Default: ON)

```yaml
spring.jpa.open-in-view: true   # DEFAULT — almost nobody knows
# Hibernate session stays open for entire HTTP request
# Jackson serializes Order → accesses lazy items → N+1 SELECT per order
# DB connection held for full request → pool exhaustion under load
# Fix:
spring.jpa.open-in-view: false  # + explicit @EntityGraph / JOIN FETCH in service
```

### Trap 2: HikariCP Connection Pool Exhaustion

```java
// WRONG: @Transactional wrapping external HTTP call
@Transactional
public Order processOrder(CreateOrderRequest req) {
    Order o = orderRepo.save(new Order(req)); // connection acquired
    PaymentResult r = paymentClient.charge(req); // 2-5s HTTP call — connection HELD
    o.setStatus(r.getStatus()); return orderRepo.save(o); // connection released
}
// 20 threads × 3s HTTP call = 20 connections held = pool exhausted

// FIX: narrow TX scope — never hold connection during external calls
public Order processOrder(CreateOrderRequest req) {
    Order o = createRecord(req);          // TX 1: 5ms, connection released
    PaymentResult r = paymentClient.charge(req); // no connection held
    return updateStatus(o.getId(), r);    // TX 2: 5ms, connection released
}
```

```yaml
spring.datasource.hikari:
  maximum-pool-size: 20
  connection-timeout: 3000         # fail fast — don't queue forever
  leak-detection-threshold: 5000   # warns if connection held > 5s
```

### Trap 3: @Cacheable Production Bugs

```
Cache stampede: entry expires → 1000 threads miss → hammer DB simultaneously
Fix: Caffeine refreshAfterWrite (refreshes before expiry) + distributed lock

@Cacheable proxy trap: same-class method → proxy bypassed → not cached
@CacheEvict wrong key: key mismatch → cache never cleared → stale forever

Consistent key strategy: @CacheConfig(cacheNames="products") at class level
@CachePut: updates cache after save (prevents stale immediately after write)
```

### Trap 4: @Scheduled in Clustered Environment

```
3 pods × @Scheduled = 3 executions → users receive 3 emails
Fix: ShedLock — @SchedulerLock acquires DB lock, only 1 pod executes

Default scheduler: 1 thread → Job A runs 5 min → Job B (every 1 min) never fires
Fix: @Bean TaskScheduler with poolSize > 1
```

### Trap 5: SecurityContext Not Propagated to @Async

```java
// ThreadLocal SecurityContext → null on new @Async thread
Fix: DelegatingSecurityContextAsyncTaskExecutor wraps your executor
     Copies SecurityContext to each spawned thread

// MDC (traceId) same problem:
Fix: TaskDecorator that copies MDC.getCopyOfContextMap() to async thread
```

### Trap 6: @EventListener — Data Not Visible to Listener

```java
@Transactional
public void placeOrder(Order o) {
    orderRepo.save(o);
    eventPublisher.publishEvent(new OrderPlacedEvent(o.getId())); // fires BEFORE commit
}
@EventListener  // runs before commit → order not in DB yet → EntityNotFoundException
public void onOrder(OrderPlacedEvent e) { orderRepo.findById(e.getId()); } // 404!

// Fix:
@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT) // fires after commit ✅
// If listener writes to DB: add @Transactional(propagation = REQUIRES_NEW)
```

### Trap 7: readOnly=true Misunderstanding

```
readOnly=true DOES:   skip Hibernate dirty check/flush (minor CPU saving)
readOnly=true DOES NOT: auto-route to replica (need AbstractRoutingDataSource)
readOnly=true DOES NOT: prevent writes at DB level (most drivers)

For actual read-replica routing:
  AbstractRoutingDataSource → check TransactionSynchronizationManager.isCurrentTransactionReadOnly()
  → route to replica when true, primary when false
```

### Trap 8: BPP Dependency Breaks @Transactional Proxy

```
BPP @Autowired MyService → Spring creates MyService early
→ before @Transactional BPP runs → MyService has NO @Transactional proxy

Spring logs (easy to miss):
  "Bean 'myService' is not eligible for getting processed by all BPPs"

Fix: lazy ApplicationContext.getBean(MyService.class) inside BPP methods
```

### Trap 9: @Transactional Exception Rollback Rules

```java
// WRONG: checked exception does NOT rollback by default
@Transactional
public void process() throws IOException { // IOException is checked → NO rollback
    repo.save(data);
    throw new IOException("file not found"); // saves committed ❌
}
// FIX:
@Transactional(rollbackFor = Exception.class) // rollback for ALL exceptions ✅
```

### Trap 10: @ConfigurationProperties vs @Value

```java
@Value("${payment.url}")           // NoSuchBeanDefinitionException if missing
private String url;                // no validation, no nesting, magic strings

@ConfigurationProperties(prefix = "payment")
@Validated
public class PaymentConfig {
    @NotBlank private String url;       // fails at startup with clear message ✅
    @Min(1000) private int timeoutMs;   // validated
    private RetryConfig retry;          // nested config — impossible with @Value
}
```

---

## Master Interview Cheat Sheet

```
THE PROXY RULE:
  @Transactional, @Async, @Cacheable all work via proxy
  Self-invocation (this.method()) = proxy bypassed = annotation ignored
  Private methods = proxy can't intercept = annotation ignored

TRANSACTIONAL:
  Default rollback: RuntimeException only
  readOnly: Hibernate flush skip only — NOT replica routing
  REQUIRES_NEW: independent TX (audit logs) — deadlock risk on same table
  NESTED: savepoint (optional sub-steps) — outer rollback kills inner
  MANDATORY: caller must provide TX — use for domain contracts
  Self-invocation: fix with separate @Service or self-injection

ASYNC:
  @EnableAsync required — without it, silently ignored
  Default pool: creates new thread per call → OOM
  Exceptions: silently swallowed unless return CompletableFuture
  SecurityContext: ThreadLocal → null on async thread → DelegatingSecurityContextAsyncTaskExecutor
  Never pass JPA entities to @Async — pass IDs

BEAN LIFECYCLE:
  Constructor → inject → BPP.before → @PostConstruct → BPP.after (proxies) → ready
  Prototype-in-singleton: inject once → same instance always → use ObjectProvider
  BPP dependency: breaks proxy creation → lazy getBean() fix

WEBFLUX:
  Event loop: 2×CPU threads — one blocked = all stall
  Fix blocking IO: subscribeOn(Schedulers.boundedElastic())
  .block() inside chain = deadlock
  BlockHound: catches blocking calls in dev/test

K8S:
  startupProbe: prevents liveness from killing slow-starting app
  readinessProbe: stop traffic (recoverable) — pod stays alive
  livenessProbe: restart pod (unrecoverable) — use sparingly
  K8s terminationGracePeriodSeconds > Spring timeout

PRODUCTION TRAPS:
  OSIV: spring.jpa.open-in-view=true (default) → N+1 + connection leak
  HikariCP: @Transactional + external HTTP call → pool exhaustion
  @Scheduled: runs on ALL pods → ShedLock for distributed lock
  @EventListener: fires before commit → use AFTER_COMMIT
  Security 6: WebSecurityConfigurerAdapter removed → SecurityFilterChain bean
```

---

*SpringBoot Interview Guide — 11 topics · Last updated August 2026 · Architect / 15-year level*
