# Q13: Spring Cache (@Cacheable) — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 20-25 minutes | **Frequency:** 85% in senior/architect rounds 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "Our cache was working perfectly in dev. In prod, it was serving stale data for 24 hours, causing wrong prices to show on the checkout page." — A real incident.

---

## How Spring Cache Works (Plain English)

```
First call: cache MISS
  → method executes → result stored in cache under key → returned to caller

Second call (same key): cache HIT
  → method body SKIPPED ENTIRELY → cached value returned directly

@CacheEvict: removes entry from cache (e.g., when data changes)
@CachePut:   always executes method AND updates cache (no skip)
```

```java
@EnableCaching   // REQUIRED in @SpringBootApplication or @Configuration
@SpringBootApplication
public class Application { }
```

---

## Scenario 1: Self-Invocation Trap (Same as @Async)

### The Bug
```java
@Service
public class ProductService {

    @Cacheable("products")
    public Product getProduct(Long id) {
        return productRepo.findById(id).orElseThrow();
    }

    public List<Product> getMultiple(List<Long> ids) {
        return ids.stream()
                  .map(this::getProduct)   // ❌ self-invocation!
                  .collect(toList());
        // Spring proxy is bypassed → cache NEVER consulted
        // Every call hits the database directly
    }
}
```

### Why It Fails
```
External caller → Spring Proxy → getMultiple() body
                                      ↓
                               this.getProduct()  ← "this" = raw object, not proxy
                                      ↓
                               @Cacheable ignored, DB hit every time
```

### Fix: Inject Self or Extract to Another Bean
```java
@Service
public class ProductService {

    @Autowired
    private ProductService self;   // inject proxy of self

    @Cacheable("products")
    public Product getProduct(Long id) {
        return productRepo.findById(id).orElseThrow();
    }

    public List<Product> getMultiple(List<Long> ids) {
        return ids.stream()
                  .map(self::getProduct)  // ✅ goes through proxy → cache works
                  .collect(toList());
    }
}
```

```yaml
# application.yml — needed to allow circular self-injection
spring:
  main:
    allow-circular-references: true
```

**Better fix**: extract `getProduct` to a separate `ProductCacheService` bean.

---

## Scenario 2: Cache Stampede (Thundering Herd in Production)

### The Problem
Product catalog cache expires at midnight (TTL = 24h).
At 00:00:01, 5000 simultaneous requests all get cache MISS.
All 5000 hit the database simultaneously. DB CPU → 100%. Cascade failure.

```
00:00:00 → cache entry expires
00:00:01 → Thread 1: MISS → queries DB
           Thread 2: MISS → queries DB  (not waiting for Thread 1)
           Thread 3: MISS → queries DB
           ... × 5000
           → 5000 simultaneous DB queries for the SAME data
```

### Fix 1: Caffeine with Refresh-After-Write (Async Refresh)
```java
@Bean
public CacheManager cacheManager() {
    CaffeineCacheManager manager = new CaffeineCacheManager("products");
    manager.setCaffeine(Caffeine.newBuilder()
        .expireAfterWrite(24, TimeUnit.HOURS)
        .refreshAfterWrite(23, TimeUnit.HOURS)  // refresh 1h BEFORE expiry
        // → only ONE background refresh thread hits DB
        // → other threads keep getting stale-but-valid cache hit
        .maximumSize(10_000));
    return manager;
}
```

### Fix 2: Probabilistic Early Expiration (Jitter)
```java
// Add random jitter to TTL so entries expire at different times
// Not all at midnight simultaneously
int jitterSeconds = ThreadLocalRandom.current().nextInt(0, 3600); // 0-60 min jitter
cache.put(key, value, 24 * 3600 + jitterSeconds, TimeUnit.SECONDS);
```

### Fix 3: Redis with Mutex Lock (One DB call, rest wait)
```java
@Service
public class ProductCacheService {

    private final RedisTemplate<String, Product> redis;
    private final RedisLockRegistry lockRegistry;

    public Product getProduct(Long id) {
        String key = "product:" + id;
        Product cached = redis.opsForValue().get(key);
        if (cached != null) return cached;

        // Acquire distributed lock — only ONE pod loads from DB
        Lock lock = lockRegistry.obtain("lock:product:" + id);
        try {
            lock.lock();
            cached = redis.opsForValue().get(key); // double-check after lock
            if (cached != null) return cached;

            Product product = productRepo.findById(id).orElseThrow();
            redis.opsForValue().set(key, product, 24, TimeUnit.HOURS);
            return product;
        } finally {
            lock.unlock();
        }
    }
}
```

---

## Scenario 3: Wrong Cache Key → Stale Data Bug

### The Bug
```java
@Cacheable("users")   // ❌ ALL users share ONE cache entry!
public User getUser(Long userId) {
    return userRepo.findById(userId).orElseThrow();
}

// getUser(1) → DB → stores under key "users" (just the cache name)
// getUser(2) → HITS CACHE → returns User#1 ← WRONG USER!
```

### Fix: Explicit Key
```java
@Cacheable(value = "users", key = "#userId")
public User getUser(Long userId) { ... }
// Cache key: "users::1", "users::2" etc.

// Complex key:
@Cacheable(value = "products", key = "#category + ':' + #page")
public Page<Product> getByCategory(String category, int page) { ... }

// SpEL on object field:
@Cacheable(value = "orders", key = "#order.id + ':' + #order.status")
public OrderSummary getSummary(Order order) { ... }
```

### Default Key Behaviour (The Silent Trap)
```
No @Cacheable key specified:
  - 0 params  → key = SimpleKey.EMPTY
  - 1 param   → key = param itself
  - 2+ params → key = SimpleKey(param1, param2, ...)

Problem: SimpleKey uses .equals() — if your param is a complex object
         without proper .equals(), all calls share the same key!
         Always specify key explicitly in production.
```

---

## Scenario 4: Caching Null Values (Unexpected Behaviour)

### The Bug
```java
@Cacheable("products")
public Product getProduct(Long id) {
    return productRepo.findById(id).orElse(null);  // returns null if not found
}

// First call with id=999 (not in DB) → returns null → null IS CACHED
// Product 999 is later created in DB
// getProduct(999) → HIT → returns null (stale!) even though product now exists
```

### Fix 1: unless condition (don't cache null)
```java
@Cacheable(value = "products", key = "#id", unless = "#result == null")
public Product getProduct(Long id) {
    return productRepo.findById(id).orElse(null);
}
```

### Fix 2: throw exception for not-found (never returns null)
```java
@Cacheable(value = "products", key = "#id")
public Product getProduct(Long id) {
    return productRepo.findById(id)
                      .orElseThrow(() -> new ProductNotFoundException(id));
    // exception not caught by @Cacheable → nothing cached → correct behaviour
}
```

---

## Scenario 5: @CacheEvict on Wrong Method / Wrong Key

### The Bug
```java
@Service
public class ProductService {

    @Cacheable(value = "products", key = "#id")
    public Product getProduct(Long id) { ... }

    // WRONG ❌ — evicts based on product.id but cache key was the incoming param "id"
    @CacheEvict(value = "products", key = "#product.id")
    public void updateProduct(Product product) {
        productRepo.save(product);
    }

    // ALSO WRONG ❌ — no key = evicts SimpleKey(product) which doesn't match "id"
    @CacheEvict(value = "products")
    public void deleteProduct(Product product) { ... }
}
```

### Fix: Keys Must Match Exactly
```java
@CacheEvict(value = "products", key = "#id")
public void deleteProduct(Long id) {
    productRepo.deleteById(id);
}

@CachePut(value = "products", key = "#product.id")   // update + refresh cache
public Product updateProduct(Product product) {
    return productRepo.save(product);
}
```

### Evict All Entries in Cache
```java
@CacheEvict(value = "products", allEntries = true)
public void refreshProductCatalog() {
    // Called on catalog import — wipe entire "products" cache
}
```

---

## Trap 1: @Transactional + @Cacheable (Wrong Order of Operations)

### The Scenario
```java
@Transactional
@CacheEvict(value = "products", key = "#id")
public void deleteProduct(Long id) {
    productRepo.deleteById(id);
    // TX not yet committed, but cache ALREADY evicted
    // Another thread gets cache MISS → loads from DB → product still there!
    // → Race condition: cache re-populated with data that's about to be deleted
}
```

### Fix: Evict AFTER transaction commits
```java
@Transactional
public void deleteProduct(Long id) {
    productRepo.deleteById(id);
    // TX commits here
}

// Evict cache in @TransactionalEventListener — fires AFTER commit
@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
@CacheEvict(value = "products", key = "#event.productId")
public void onProductDeleted(ProductDeletedEvent event) {
    // cache evicted only after DB change is committed and visible ✅
}
```

---

## Trap 2: Distributed Cache (Redis) — Object Deserialization Fails

### The Bug
```java
// Your cached object — version 1
public class Product implements Serializable {
    private Long id;
    private String name;
}

// You add a field — version 2
public class Product implements Serializable {
    private Long id;
    private String name;
    private BigDecimal price;  // NEW FIELD
}

// Old serialized bytes in Redis cannot deserialize into new class
// → InvalidClassException or silent null fields
// → Usually discovered when Redis is NOT cleared after deployment!
```

### Fix: Use JSON serialization + migration strategy
```java
@Bean
public RedisCacheConfiguration cacheConfiguration() {
    return RedisCacheConfiguration.defaultCacheConfig()
        .entryTtl(Duration.ofHours(1))
        .serializeValuesWith(
            RedisSerializationContext.SerializationPair.fromSerializer(
                new GenericJackson2JsonRedisSerializer()  // JSON, not Java serialization
            )
        );
}
```

JSON is tolerant of new fields (unknown fields ignored by Jackson default config).
Always flush Redis cache on deployment when model structure changes.

---

## Trap 3: Condition vs Unless (Evaluated at Different Times)

```java
// condition: evaluated BEFORE method runs (decides whether to look up cache)
// unless:    evaluated AFTER method runs (decides whether to STORE result)

@Cacheable(
    value = "products",
    key = "#id",
    condition = "#id > 0",         // don't cache for id <= 0 (e.g. test IDs)
    unless = "#result.isDeleted()" // don't cache deleted products
)
public Product getProduct(Long id) { ... }

// TRAP: using #result in condition
@Cacheable(value = "products", condition = "#result != null")  // ❌ WRONG
// #result is not available in condition (method hasn't run yet!)
// → Spring throws SpelEvaluationException

// CORRECT: use unless for result-based conditions
@Cacheable(value = "products", unless = "#result == null")     // ✅
```

---

## Quick Reference

| Annotation | When Method Runs | Cache Updated | Use For |
|---|---|---|---|
| `@Cacheable` | Only on MISS | On MISS | Read-through caching |
| `@CachePut` | Always | Always | Write-through caching |
| `@CacheEvict` | Always | Entry removed | Invalidation on mutation |
| `@Caching` | Always | Composed | Multiple ops at once |

---

## Interview Cheat Sheet

> "In production, I always specify explicit cache keys using SpEL to avoid key collisions. Self-invocation is the #1 bug — @Cacheable is AOP-based, calling the method on `this` bypasses the proxy. For @CacheEvict with @Transactional, I use @TransactionalEventListener with AFTER_COMMIT phase to avoid the race condition where cache is cleared before the TX commits. For Redis, I use JSON serialization (not Java serialization) to survive model changes across deployments. For cache stampede on high-traffic systems, Caffeine's refreshAfterWrite handles background refresh so the cache never actually expires hard."
