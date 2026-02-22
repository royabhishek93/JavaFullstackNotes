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

**Last Updated:** February 22, 2026  
**Next: [Q19_load_balancing.md](Q19_load_balancing.md)**
