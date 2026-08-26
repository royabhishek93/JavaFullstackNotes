# Cache Invalidation Patterns: The Sneaky Interview Question

**Study Time:** 12-15 minutes | **Frequency:** 80% in senior interviews | **Difficulty:** ⭐⭐⭐⭐⭐

---

## 🤔 Problem Scenario

Phil Karlton said: "There are only two hard things in Computer Science: cache invalidation and naming things."

```
User updates profile:

1. Update DB:    users table (age: 30 → 35)
2. Cache has:    users:1 = {age: 30}  ← STALE!

Request comes in:
  - Query cache → age: 30 (WRONG!)
  - Shows old profile to user

How to keep cache up-to-date?
```

**Challenge:** Cache invalidation is HARD and easily broken.

---

## 🧠 Key Principle: Five Cache Invalidation Patterns

| Pattern | Mechanism | Best For | Risk |
|---------|-----------|----------|------|
| **Write-through** | Update cache WITH DB | Strong consistency | Extra latency |
| **Write-around** | Update DB, invalidate cache | Reduce write latency | Cache misses |
| **Write-behind** | Cache first, async to DB | Performance | Data loss |
| **TTL (Time-to-Live)** | Cache expires automatically | Simple | Stale data window |
| **Event-based** | Listen to DB changes | Consistency + performance | Complex setup |

---

## ✅ Pattern 1: Write-Through

Cache and DB both update **synchronously**:

```
User updates profile:

API Request
  ↓
1. Update DB (users table, age: 35)
2. Update Cache (users:1, age: 35)
3. Return success

Both are in sync!
```

### Implementation:

```java
public class WriteThrough {
    private final Database db;
    private final Cache cache;
    
    public void updateUser(User user) {
        // Update DB first
        db.save(user);
        
        // Then update cache
        String cacheKey = "user:" + user.getId();
        cache.set(cacheKey, user);
    }
    
    public User getUser(long userId) {
        String cacheKey = "user:" + userId;
        
        // Try cache first
        User cached = cache.get(cacheKey);
        if (cached != null) return cached;
        
        // Cache miss, query DB
        User user = db.findById(userId);
        cache.set(cacheKey, user);
        return user;
    }
}
```

### Pros & Cons:

```
✅ Strong consistency (cache always correct)
✅ Simple logic

❌ Extra latency (write always slow: DB + cache)
❌ If cache writes fail, inconsistency happens
```

---

## ✅ Pattern 2: Write-Around

Update **only DB**, invalidate cache:

```
User updates profile:

API Request
  ↓
1. Update DB (users table, age: 35)
2. Delete cache (users:1)
3. Return success

Cache is empty. Next read refills from DB.
```

### Implementation:

```java
public class WriteAround {
    private final Database db;
    private final Cache cache;
    
    public void updateUser(User user) {
        // Update DB
        db.save(user);
        
        // Invalidate cache (don't write to it)
        String cacheKey = "user:" + user.getId();
        cache.delete(cacheKey);
        
        // Next read will fetch from DB and populate cache
    }
    
    public User getUser(long userId) {
        String cacheKey = "user:" + userId;
        
        User cached = cache.get(cacheKey);
        if (cached != null) return cached;
        
        // Cache miss (expected after update)
        User user = db.findById(userId);
        cache.set(cacheKey, user);  // Lazy load
        return user;
    }
}
```

### Pros & Cons:

```
✅ Faster writes (only DB)
✅ Avoid write-heavy cache updates

❌ Cache becomes empty on writes
❌ Next reads cause cache miss (slow)
❌ Thundering herd if many simultaneous reads
```

---

## ✅ Pattern 3: Write-Behind (Write-Back)

Write to **cache immediately**, async to DB:

```
User updates profile:

API Request
  ↓
1. Update Cache immediately (users:1, age: 35)
2. Return success immediately
3. Async: Write to DB in background

Super fast but risky!
```

### Implementation:

```java
public class WriteBehind {
    private final Database db;
    private final Cache cache;
    private final ExecutorService asyncExecutor = Executors.newFixedThreadPool(4);
    
    public void updateUser(User user) {
        // Update cache immediately
        String cacheKey = "user:" + user.getId();
        cache.set(cacheKey, user);
        
        // Schedule async DB write
        asyncExecutor.submit(() -> {
            try {
                db.save(user);
            } catch (Exception e) {
                logger.error("Failed to save user to DB", e);
                // User might be lost! (if cache evicted before DB write)
            }
        });
    }
    
    public User getUser(long userId) {
        String cacheKey = "user:" + userId;
        return cache.get(cacheKey, () -> db.findById(userId));
    }
}
```

### Pros & Cons:

```
✅ Extremely fast (respond before DB commit)
✅ Optimal for write-heavy workloads

❌ DATA LOSS RISK (crash before async write)
❌ DB temporarily inconsistent
❌ Only for non-critical data (e.g., click counts, not payments)
```

### When to Use:

```
✅ Click counters (millions/second, loss okay)
✅ Like counts (social media)
✅ Session data (non-persistent)

❌ Payment transactions (never!)
❌ User profiles (critical)
❌ Inventory (must be accurate)
```

---

## ✅ Pattern 4: TTL (Time-to-Live)

Cache expires after **fixed duration**:

```
User updatesat 10:00:00:
  Cache set: users:1 = {age: 30}, TTL=5min

10:04:00: User updates to age: 35
  Cache still has: {age: 30}  ← STALE

10:05:01: Cache expires
  Next read: Query DB → {age: 35}
  Cache refreshed
```

### Implementation:

```java
public class TTLPattern {
    private final Database db;
    private final Cache cache;
    private static final int TTL_SECONDS = 300;  // 5 minutes
    
    public void updateUser(User user) {
        // Can update cache or DB
        // But don't explicitly invalidate
        db.save(user);
    }
    
    public User getUser(long userId) {
        String cacheKey = "user:" + userId;
        
        User cached = cache.get(cacheKey);
        if (cached != null) return cached;
        
        // Cache miss or expired
        User user = db.findById(userId);
        cache.set(cacheKey, user, TTL_SECONDS);  // With expiration
        return user;
    }
}
```

### Pros & Cons:

```
✅ Simple (automatic expiration)
✅ No explicit invalidation needed

❌ Stale data window (up to TTL duration)
❌ Long TTL = staleness, Short TTL = extra DB load
```

---

## ✅ Pattern 5: Event-Based Invalidation

Listen to **database changes**, invalidate cache:

```
User updates profile:

Update DB:
  users.age = 35
  DB triggers event: UserUpdated(id=1, age=35)

Event Queue:
  ↓
Cache Service:
  Receives UserUpdated event
  Invalidates: users:1

Next read: Cache miss, refreshes from DB

BEST: Keep cache consistent AND performant
```

### Implementation:

```java
// Change Data Capture (CDC) approach
public class EventBasedInvalidation {
    private final Database db;
    private final Cache cache;
    private final EventPublisher eventPublisher;
    
    public void updateUser(User user) {
        // Update DB
        db.save(user);
        
        // Publish event
        eventPublisher.publish(new UserUpdatedEvent(
            user.getId(),
            user
        ));
    }
    
    @EventListener(UserUpdatedEvent.class)
    public void onUserUpdated(UserUpdatedEvent event) {
        // Invalidate cache
        String cacheKey = "user:" + event.getUserId();
        cache.delete(cacheKey);
        
        // OR: Update cache with new data
        cache.set(cacheKey, event.getUser());
    }
    
    public User getUser(long userId) {
        String cacheKey = "user:" + userId;
        return cache.get(cacheKey, () -> db.findById(userId));
    }
}

// Alternative: Change Data Capture from DB logs
class CDCService {
    public void onDatabaseChange(DatabaseLog log) {
        // DB change detected (MySQL binlog, PostgreSQL WAL)
        String table = log.getTable();
        String operation = log.getOperation();  // INSERT, UPDATE, DELETE
        
        if (table.equals("users") && operation.equals("UPDATE")) {
            long userId = log.getKey();
            cache.delete("user:" + userId);  // Invalidate
        }
    }
}
```

### Pros & Cons:

```
✅ Consistent (invalidates on DB change)
✅ Automatic (no app logic needed)
✅ Works for all users

❌ Complex setup (CDC infrastructure)
❌ Event ordering issues (distributed systems)
❌ Latency between DB change and cache invalidation
```

---

## 📊 Pattern Comparison

| Pattern | Consistency | Write Latency | Read Latency | Complexity |
|---------|-------------|---------------|--------------|-----------|
| Write-Through | Strong | High | Low | Low |
| Write-Around | Eventual (~RTT) | Low | Medium | Low |
| Write-Behind | Eventual | Very Low | Low | High |
| TTL | Eventual (TTL) | Any | Low | Very Low |
| Event-Based | Strong | Medium | Low | High |

---

## 🚨 Common Invalidation Problems

### Problem 1: Thundering Herd

```java
// Multiple requests hit cache simultaneously and miss:

Request 1: Cache miss for user:1
Request 2: Cache miss for user:1 (same)
Request 3: Cache miss for user:1 (same)

All 3 query DB at once!
DB gets 3 identical queries when only 1 needed.

Solution: Stampede prevention
User cached = cache.get("user:1");
if (cached == null) {
    synchronized("user:1") {  // Only one thread queries DB
        cached = db.findById(1);
        cache.set("user:1", cached);
    }
}
```

---

### Problem 2: Stale Writes

```java
// Thread 1 and 2 race:

T1: Read from cache: age=30
T2: Read from cache: age=30

T1: Update to age=31, write cache
T2: Update to age=32, write cache

Cache: age=32 (T2's value)
T1's update lost!

Solution: Version numbers or Compare-and-Swap (CAS)
cache.compareAndSet("user:1", oldVersion, newVersion);
```

---

### Problem 3: Double-Write Problem

```
Write cache, then DB fails:

1. Update cache: users:1 = age:35
2. DB write fails (network down)
3. Now DB has age:30, cache has age:35

Inconsistent forever (until cache TTL expires)!

Solution: Write DB first, then cache
If cache write fails, retry. If DB is unreachable, don't write cache.
```

---

## 🎯 Interview Q&A

### Q1: "Which invalidation pattern?"

**Answer (30 seconds):**
```
Write-Through: Default, simplest, strong consistency
- Use unless performance is critical

Write-Around: Read-heavy workloads
- Avoid unnecessary cache updates on writes

Write-Behind: Ultra-high throughput (millions/sec)
- Only for non-critical data (click counts, not payments)

TTL: Simple, automatic expiration
- Good for data that doesn't need instant consistency

Event-Based: Distributed systems, consistency critical
- Best for important data (user profiles, inventory)
```

---

### Q2: "How to handle cache stampede?"

**Answer:**
```
Stampede: Many requests hit cache miss simultaneously
→ All query DB at once (expensive!)

Solutions:

1. Locking (simple):
if (cache.miss()) {
    synchronized (key) {
        if (cache.miss())  // Double-check
            db.query();
    }
}

2. Probabilistic early expiration:
if (cache.nearExpiration(0.8)) {
    // Proactively refresh while data fresh
    // Avoid stampede when expired
}

3. Lock + Probabilistic:
Best combination for high traffic
```

---

### Q3: "Cache invalidation order?"

**Answer:**
```
Question: Should you invalidate cache before or after DB?

Before (risky):
DELETE cache
UPDATE db
If DB fails → DB stale, cache empty → OK

After (risky):
UPDATE db
DELETE cache
If DELETE fails → DB new, cache old → STALE!

SOLUTION: Write DB first, then cache
Why: DB is source of truth
If cache update fails, data consistent (cache miss on next read)
```

---

## 🔑 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Pattern selection | Right tool for scenario | ⭐⭐⭐⭐⭐ |
| Consistency trade-offs | Systems thinking | ⭐⭐⭐⭐⭐ |
| Stampede prevention | High-traffic awareness | ⭐⭐⭐⭐ |
| Double-write problems | Real-world bugs | ⭐⭐⭐⭐ |
| Event-based approach | Modern systems | ⭐⭐⭐ |

---

**Priority:** 🔥 MUST KNOW (80% senior interviews)

**Related:**
- Consistency Models
- Distributed Caching
- Cache Strategies

---

**Last Updated:** March 5, 2026
