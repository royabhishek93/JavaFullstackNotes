# 🎯 Q18: What Caching Strategies Would You Use?

> **Interview Frequency:** 78% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

What caching strategy should Flipkart use for product listings, prices, and user preferences?

---

## 📌 Caching Strategies

### 1. **LRU (Least Recently Used)**
- Keep frequently accessed items
- Evict least recently used when full
- Good for: Product catalog, User preferences
- Trade-off: Less predictable

### 2. **TTL (Time To Live)**
- Cache item expires after X seconds
- Good for: Prices (refresh every minute), Top products (refresh hourly)
- Trade-off: Stale data possible

### 3. **Write-Through**
- Write to cache AND database together
- Expensive but consistent
- Good for: Critical data (inventory)

### 4. **Write-Behind**
- Write to cache, async to database
- Faster but data loss possible if cache fails
- Good for: Non-critical (page views)

### 5. **Cache-Aside**
- Check cache, if miss fetch from DB
- Application handles logic
- Good for: Most scenarios
- Trade-off: Cache stampede

---

## 💬 Interview Tip (Say This EXACTLY)

"Use cache-aside for most data (check cache, miss → fetch DB). Combine with TTL for auto-expiration. LRU for bounded memory. Use write-through for critical (inventory), write-behind for non-critical (analytics). Monitor: hit rate, eviction rate, memory."

---

## 📚 Example Implementation

```java
// With TTL and LRU
Cache<String, Product> cache = new LoadingCache<>(
    5000,  // LRU: max 5000 items
    Duration.ofMinutes(1),  // TTL: 1 minute
    productRepository::findById  // Load function
);

Product product = cache.get("P123");  // Hit or loads from DB
```

---

## ☑️ Strategy Selection

| Data Type | Strategy | TTL | Reason |
|-----------|----------|-----|--------|
| Product catalog | LRU + TTL | 1 hour | Hot items, manual refresh |
| Product prices | TTL | 5 min | Frequently changes |
| User prefs | TTL | 24 hours | Less frequent changes |
| Inventory | Write-through | N/A | Must be accurate |
| Search results | Cache-aside | 30 min | Heavy access |

---

---

## ⚠️ Common Pitfalls

**Pitfall 1: Cache stampede (thundering herd)**
```java
// ❌ 10k requests all miss cache at same time, all hit DB!
Product product = cache.get(id);
if (product == null) {
    product = db.findById(id);  // 10k DB queries simultaneously!
    cache.put(id, product);
}

// ✅ Use locking or probabilistic early expiration
synchronized (lock) {
    product = cache.get(id);
    if (product == null) {
        product = db.findById(id);
        cache.put(id, product);
    }
}
```

**Pitfall 2: Not setting TTL (time-to-live)**
```java
// ❌ Data cached forever, stale data
cache.put("product:" + id, product);  // No expiration!

// ✅ Always set TTL
cache.put("product:" + id, product, 5, TimeUnit.MINUTES);
```

**Pitfall 3: Cache invalidation after DB update**
```java
// ❌ Old data in cache after update
productRepo.save(product);  // DB updated
cache.evict("product:" + id);  // What if this fails? Stale cache!

// ✅ Transactional invalidation or write-through
@Transactional
public void updateProduct(Product product) {
    productRepo.save(product);
    cache.evict("product:" + product.getId());
}
```

**Pitfall 4: Caching large objects**
```java
// ❌ Caching 10MB user profile
cache.put(userId, userWithAllOrders);  // 10MB serialized!

// ✅ Cache only what you need
cache.put(userId, new UserSummary(name, email));  // 1KB
```

**Pitfall 5: Not monitoring cache hit rate**
```
// ❌ Cache hit rate = 20%, but you don't know!
// You're paying for Redis but getting no benefit

// ✅ Monitor metrics
Cache hit rate > 80% = good
Cache hit rate < 50% = review caching strategy
```

---

## 🛑 When NOT to Use Caching

- ❌ Data changes every request (cache hit rate <20%)
- ❌ Data must be real-time (e.g., stock trading prices)
- ❌ Cache infrastructure cost > database cost (rare)
- ✅ DO cache: Read-heavy workloads, hot data (80/20 rule)

---

## 🔗 Related Questions

- [database-scaling.md](database-scaling.md) - Database read replicas and sharding
- [load-balancing-algorithms.md](load-balancing-algorithms.md) - Distributing cache load
- [message-queues.md](message-queues.md) - Cache invalidation via events

---

**Last Updated:** February 22, 2026  
**Next: [load-balancing-algorithms.md](load-balancing-algorithms.md)**
