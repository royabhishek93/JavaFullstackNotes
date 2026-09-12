# #55 — Cache Without Eviction

> **Category:** Memory Leaks End-to-End | **Type:** Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"Your caching layer is growing unbounded. Show the Guava/Caffeine mistake and fix."

## 😊 Explain It Simply (for anyone)
A cache (a fast, temporary storage layer that remembers recently-used data so you don't have to fetch it again) is supposed to be like a small fridge — it keeps things fresh and useful, but it has LIMITED SPACE, so old or unused items must eventually be thrown out (this is called "eviction"). If you build a fridge with no size limit and no expiration policy, it's not really a fridge anymore — it's a garage you keep piling boxes into forever. Eventually there's no room left to walk (memory runs out), and the "convenience" the cache was supposed to provide has become the very thing crashing your system.

## 📊 Visualize It
```
 Unbounded Cache (no maximumSize, no expireAfterWrite):

  key1 -> value1
  key2 -> value2
  key3 -> value3
  ...
  key999999 -> value999999   <-- keeps growing, nothing ever removed

 Bounded Cache (maximumSize=50000, expireAfterWrite=10min):

  [oldest entries evicted automatically]
  key_recent1 -> value1
  key_recent2 -> value2
  (capped at 50,000 entries, each expires after 10 min)
```

## 🏭 The Real Production Answer (15-YOE Level)

Buggy code:
```java
// LEAK: no size limit, no expiry — this is just a HashMap with extra steps
private final Cache<String, ProductDetails> cache =
    CacheBuilder.newBuilder().build(); // Guava, no bounds
```

Also leaks with Caffeine:
```java
private final Cache<String, byte[]> imageCache =
    Caffeine.newBuilder().build(); // no maximumSize, no expiry
```

Fix:
```java
private final Cache<String, ProductDetails> cache =
    Caffeine.newBuilder()
        .maximumSize(50_000)               // cap by entry count
        .expireAfterWrite(10, TimeUnit.MINUTES)
        .expireAfterAccess(5, TimeUnit.MINUTES)
        .recordStats()                     // expose hit rate to metrics
        .build();
```

For large values (byte arrays), bound by weight not count:
```java
private final Cache<String, byte[]> imageCache =
    Caffeine.newBuilder()
        .maximumWeight(256 * 1024 * 1024)  // 256 MB total
        .weigher((key, value) -> ((byte[]) value).length)
        .expireAfterWrite(30, TimeUnit.MINUTES)
        .build();
```

Architect note: always expose cache stats to Prometheus — `cache.stats().hitRate()`. A hit rate below 20% with a large cache is a red flag (you're caching but not benefiting, just retaining).

## 🔑 Key Takeaway
A cache without `maximumSize`/`maximumWeight` and an expiry policy is just a memory leak with a friendlier name.
