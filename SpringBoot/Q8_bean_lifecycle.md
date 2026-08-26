# Q8: Spring Bean Lifecycle — @PostConstruct, BeanPostProcessor, Scopes (Architect Guide)

**Study Time:** 15-20 minutes | **Frequency:** 80% in architect interviews 🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

---

## Why This Matters in Production

Bean lifecycle controls:
- When connections/caches are initialised (startup order bugs)
- When resources are released (memory leaks on shutdown)
- How cross-cutting concerns (logging, validation, proxying) are injected globally
- Why @Transactional and @Async work at all (they're BeanPostProcessors)

---

## The Full Bean Lifecycle (in order)

```
1. BeanDefinition loaded (classpath scan / @Bean / XML)
        ↓
2. Constructor called (dependency injection via constructor)
        ↓
3. Setter/field injection (@Autowired fields set)
        ↓
4. BeanNameAware.setBeanName()          ← optional, rarely used
        ↓
5. BeanFactoryAware.setBeanFactory()    ← optional
        ↓
6. ApplicationContextAware.setApplicationContext()  ← optional
        ↓
7. BeanPostProcessor.postProcessBeforeInitialization()  ← runs for ALL beans
        ↓
8. @PostConstruct method               ← your initialisation code
        ↓
9. InitializingBean.afterPropertiesSet()  ← alternative to @PostConstruct
        ↓
10. @Bean(initMethod="...")            ← alternative for third-party beans
        ↓
11. BeanPostProcessor.postProcessAfterInitialization()  ← proxies created HERE
        ↓
12. Bean is ready — stored in ApplicationContext
        ↓
        ... application runs ...
        ↓
13. @PreDestroy method                 ← cleanup code
        ↓
14. DisposableBean.destroy()           ← alternative to @PreDestroy
        ↓
15. @Bean(destroyMethod="...")         ← alternative for third-party beans
```

**Critical insight:** AOP proxies (@Transactional, @Async, @Cacheable) are created at step 11 by `AnnotationAwareAspectJAutoProxyCreator` — a BeanPostProcessor.

---

## @PostConstruct — Initialisation After Injection

### Why @PostConstruct Instead of Constructor?

```java
// WRONG ❌ — dependencies not injected yet in constructor
@Service
public class CacheService {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    public CacheService() {
        redisTemplate.opsForValue().set("init", "value"); // NullPointerException
        // redisTemplate is null here — @Autowired runs AFTER constructor
    }
}

// CORRECT ✅ — all dependencies injected before @PostConstruct runs
@Service
public class CacheService {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @PostConstruct
    public void init() {
        redisTemplate.opsForValue().set("app:status", "STARTING");
        log.info("Cache initialised");
        // redisTemplate is fully injected ✅
    }
}
```

### Production Use Cases for @PostConstruct

```java
@Service
public class ProductCatalogService {

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private Cache<Long, Product> localCache;

    // Pre-warm cache on startup to avoid cold-start latency spike
    @PostConstruct
    public void warmUpCache() {
        log.info("Pre-warming product cache...");
        productRepository.findTop1000ByOrderBySalesDesc()
                         .forEach(p -> localCache.put(p.getId(), p));
        log.info("Cache warmed: {} products loaded", localCache.size());
    }
}

@Service
public class DatabaseMigrationService {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    // Validate DB schema version on startup — fail fast if wrong
    @PostConstruct
    public void validateSchema() {
        String version = jdbcTemplate.queryForObject(
            "SELECT version FROM schema_version ORDER BY installed_on DESC LIMIT 1",
            String.class
        );
        if (!EXPECTED_VERSION.equals(version)) {
            throw new IllegalStateException("DB schema version mismatch: expected "
                + EXPECTED_VERSION + " got " + version);
        }
    }
}
```

### @PostConstruct Rules

| Rule | Detail |
|------|--------|
| Return type | Must be `void` |
| Parameters | Must have none |
| Exceptions | Can throw checked exceptions (Spring wraps in BeanCreationException) |
| Called once | Per bean instance (prototype = called per instance) |
| Thread | Called on startup thread — do not start long-running tasks here |

---

## @PreDestroy — Cleanup Before Shutdown

```java
@Service
public class ConnectionPoolService {

    private final ExecutorService executorService =
        Executors.newFixedThreadPool(10);

    @PreDestroy
    public void cleanup() {
        log.info("Shutting down connection pool...");
        executorService.shutdown();
        try {
            if (!executorService.awaitTermination(30, TimeUnit.SECONDS)) {
                executorService.shutdownNow();
            }
        } catch (InterruptedException e) {
            executorService.shutdownNow();
            Thread.currentThread().interrupt();
        }
        log.info("Connection pool shut down cleanly");
    }
}
```

**Note:** `@PreDestroy` is NOT called for prototype-scoped beans — Spring doesn't track them after creation. Use `DisposableBean` interface or manual tracking for prototype cleanup.

---

## BeanPostProcessor — Intercept ALL Beans Globally

### What It Does

```
For every bean Spring creates, BeanPostProcessor runs twice:
  1. postProcessBeforeInitialization() — before @PostConstruct
  2. postProcessAfterInitialization()  — after @PostConstruct (proxy creation happens here)
```

### Production Example: Inject Custom Annotation Values

```java
// Custom annotation to inject config values with validation
@Target(ElementType.FIELD)
@Retention(RetentionPolicy.RUNTIME)
public @interface ValidatedValue {
    String key();
    boolean required() default true;
}

// BeanPostProcessor that processes it
@Component
public class ValidatedValueProcessor implements BeanPostProcessor {

    @Autowired
    private Environment environment;

    @Override
    public Object postProcessBeforeInitialization(Object bean, String beanName) {
        ReflectionUtils.doWithFields(bean.getClass(), field -> {
            ValidatedValue annotation = field.getAnnotation(ValidatedValue.class);
            if (annotation != null) {
                String value = environment.getProperty(annotation.key());
                if (annotation.required() && value == null) {
                    throw new BeanCreationException(beanName,
                        "Required config key missing: " + annotation.key());
                }
                field.setAccessible(true);
                ReflectionUtils.setField(field, bean, value);
            }
        });
        return bean;
    }
}

// Usage in any bean
@Service
public class PaymentService {

    @ValidatedValue(key = "payment.gateway.url", required = true)
    private String gatewayUrl;

    @ValidatedValue(key = "payment.timeout.ms", required = false)
    private String timeoutMs;
}
```

### Production Example: Performance Logging for All @Service Beans

```java
@Component
public class ServicePerformancePostProcessor implements BeanPostProcessor {

    @Override
    public Object postProcessAfterInitialization(Object bean, String beanName) {
        if (bean.getClass().isAnnotationPresent(Service.class)) {
            return Proxy.newProxyInstance(
                bean.getClass().getClassLoader(),
                bean.getClass().getInterfaces(),
                (proxy, method, args) -> {
                    long start = System.currentTimeMillis();
                    try {
                        return method.invoke(bean, args);
                    } finally {
                        long duration = System.currentTimeMillis() - start;
                        if (duration > 1000) {
                            log.warn("SLOW: {}.{} took {}ms",
                                beanName, method.getName(), duration);
                        }
                    }
                }
            );
        }
        return bean;
    }
}
```

### BeanPostProcessor vs @Aspect

| | BeanPostProcessor | @Aspect (AOP) |
|---|---|---|
| Runs | During container startup, for each bean | At runtime, per method call |
| Purpose | Modify/wrap bean instances, inject fields | Cross-cutting runtime behaviour |
| Access to bean | Full object access | Only method interception |
| Timing | Once at startup | Every invocation |
| Examples | @Transactional proxy creation, @Autowired injection | Logging, security checks, metrics |

---

## BeanFactoryPostProcessor — Modify Bean Definitions Before Creation

```java
// BeanFactoryPostProcessor runs BEFORE any beans are created
// Can modify bean definitions (change class, scope, property values)

@Component
public class DatabaseUrlPostProcessor implements BeanFactoryPostProcessor {

    @Override
    public void postProcessBeanFactory(ConfigurableListableBeanFactory beanFactory) {
        // Override datasource URL based on environment
        BeanDefinition datasourceDef = beanFactory.getBeanDefinition("dataSource");
        String envUrl = System.getenv("DATABASE_URL");
        if (envUrl != null) {
            datasourceDef.getPropertyValues().add("url", envUrl);
        }
    }
}
```

**Key difference:**
- `BeanFactoryPostProcessor` → modifies bean *definitions* (metadata) before instantiation
- `BeanPostProcessor` → modifies bean *instances* after instantiation

---

## Bean Scopes — The Prototype-in-Singleton Trap

### Available Scopes

| Scope | Instance created | Lifetime |
|-------|-----------------|---------|
| `singleton` (default) | Once per ApplicationContext | App lifetime |
| `prototype` | Every time `.getBean()` is called | Managed by caller |
| `request` | Once per HTTP request | Request lifetime |
| `session` | Once per HTTP session | Session lifetime |
| `application` | Once per ServletContext | App lifetime |

### The Classic Production Bug: Prototype Inside Singleton

```java
// WRONG ❌ — prototype bean injected once into singleton
@Component
@Scope("prototype")
public class RequestContext {
    private final String requestId = UUID.randomUUID().toString();
    // Intended: new instance per usage
}

@Service  // singleton
public class OrderService {

    @Autowired
    private RequestContext requestContext; // injected ONCE at startup!

    public void placeOrder() {
        // requestContext.requestId is ALWAYS the same value
        // You get a singleton, not a new prototype per call ❌
        log.info("Processing request: {}", requestContext.getRequestId());
    }
}
```

### Fix: ObjectProvider / ApplicationContext.getBean()

```java
// Fix 1: ObjectProvider (Spring 4.3+, preferred)
@Service
public class OrderService {

    @Autowired
    private ObjectProvider<RequestContext> requestContextProvider;

    public void placeOrder() {
        RequestContext ctx = requestContextProvider.getObject(); // new instance each call ✅
        log.info("Processing request: {}", ctx.getRequestId());
    }
}

// Fix 2: @Lookup method injection
@Service
public abstract class OrderService {

    @Lookup
    public abstract RequestContext getRequestContext(); // Spring overrides this

    public void placeOrder() {
        RequestContext ctx = getRequestContext(); // new instance each call ✅
    }
}

// Fix 3: @Scope(proxyMode = ScopedProxyMode.TARGET_CLASS)
@Component
@Scope(value = "prototype", proxyMode = ScopedProxyMode.TARGET_CLASS)
public class RequestContext {
    // Spring creates a proxy — each method call on the proxy
    // delegates to a new prototype instance
}

@Service
public class OrderService {
    @Autowired
    private RequestContext requestContext; // injects proxy ✅
    // Each call to requestContext.method() routes to a fresh instance
}
```

---

## Startup Order — @DependsOn and SmartLifecycle

### Controlling Initialisation Order

```java
// Ensure DatabaseService initialises before CacheService
@Service
@DependsOn("databaseService")
public class CacheService {

    @PostConstruct
    public void init() {
        // databaseService is fully initialised here ✅
    }
}

// For fine-grained ordering with phases:
@Component
public class ApplicationStartupRunner implements SmartLifecycle {

    private boolean running = false;

    @Override
    public void start() {
        // Runs after all beans initialised, in phase order
        running = true;
        log.info("Application startup complete — opening for traffic");
    }

    @Override
    public void stop() {
        running = false;
        log.info("Application stopping — draining requests");
    }

    @Override
    public boolean isRunning() { return running; }

    @Override
    public int getPhase() { return Integer.MAX_VALUE; } // run last on start, first on stop
}
```

---

## Interview Cheat Sheet

```
Bean lifecycle order:
  Constructor → @Autowired injection → BeanPostProcessor.before
  → @PostConstruct → BeanPostProcessor.after (proxies created here)
  → ready
  ... shutdown ...
  → @PreDestroy → destroy

@PostConstruct:
  - Runs after all @Autowired injected (safe to use dependencies)
  - Use for: cache warm-up, DB validation, connection init
  - NOT called in constructor — dependencies are null there

BeanPostProcessor:
  - Intercepts EVERY bean before/after init
  - postProcessAfterInitialization = where AOP proxies are created
  - Use for: global annotation processing, wrapping beans with proxies

BeanFactoryPostProcessor:
  - Runs before beans are created
  - Modifies bean DEFINITIONS (metadata), not instances

Prototype-in-singleton bug:
  @Autowired prototype bean → injected once → always same instance
  Fix: ObjectProvider<T>.getObject() or @Scope(proxyMode=TARGET_CLASS)

@PreDestroy NOT called for prototype beans.
```

---

## Key Architect Questions

**Q: Why is @PostConstruct preferred over constructor for initialisation?**
`@Autowired` field/setter injection happens after the constructor. Dependencies are `null` in the constructor. `@PostConstruct` is guaranteed to run after all injection is complete.

**Q: Where does Spring create AOP proxies in the lifecycle?**
In `BeanPostProcessor.postProcessAfterInitialization()`, specifically via `AnnotationAwareAspectJAutoProxyCreator`. This is why `@Transactional` and `@Async` only work when called through the proxy, not via `this.method()`.

**Q: What happens if a BeanPostProcessor itself requires an @Autowired dependency?**
Spring instantiates BeanPostProcessors early, before other beans. If a BeanPostProcessor depends on a regular bean, that bean is also instantiated early — potentially before its own BeanPostProcessors run. This can cause beans to not be proxied (no @Transactional). Spring logs a warning: "Bean X is not eligible for getting processed by all BeanPostProcessors."

**Q: Can you have multiple BeanPostProcessors? What order do they run in?**
Yes. Implement `Ordered` or `PriorityOrdered` to control sequence. `PriorityOrdered` runs before `Ordered`, which runs before unordered. Spring's own processors (for @Autowired, @Transactional, @Async) implement `PriorityOrdered`.

**Q: How does Spring handle circular dependencies?**
For singleton beans with setter/field injection: Spring uses a 3-level cache to resolve cycles. For constructor injection: throws `BeanCurrentlyInCreationException` — circular dependency via constructor is not supported. Recommendation: avoid circular dependencies; they indicate design issues.
