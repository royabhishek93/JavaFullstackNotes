# 🎯 Q17: How to Scale Database for 100k Concurrent Users?

> **Interview Frequency:** 80% | **Difficulty:** ⭐⭐⭐⭐⭐ | **Study Time:** 5 minutes

---

## 🤔 Problem

A successful product has 100k concurrent users. Your database is bottleneck. How do you scale?

---

## 📌 Key Strategies

### 1. **Read Replicas** (Most Common)
- Master handles writes
- Replicas handle reads
- Async replication lag acceptable
- Cost: ↑ Infrastructure

### 2. **Database Sharding**
- Split data by key (user_id % shard_count)
- Each shard is separate database
- Parallel queries on multiple shards
- Complexity: ↑↑↑

### 3. **Caching** (Most Effective)
- Redis/Memcached for hot data
- Cache hit rate 80%+ reduces DB load 80%
- Invalidation strategy critical
- Cost: Medium

### 4. **Connection Pooling**
- Reuse connections (HikariCP)
- Don't create new connection per request
- Max 20-50 active connections
- Cheap, high-impact improvement

### 5. **Query Optimization**
- Indexes (B-tree, hash)
- Query plan analysis
- Avoid N+1 problems
- No full table scans

---

## 💬 Interview Tip (Say This Exactly)

"For 100k concurrent users: 1) Add read replicas for read scaling, 2) Implement caching (Redis) for hot data, 3) Use connection pooling, 4) Shard by user_id if single database can't handle. Monitor: query latency, connection count, cache hit rate."

---

## 📚 Architecture Flow

```
[100k Users]
     ↓
[API Layer] - Load balanced
     ↓
[Connection Pool] - HikariCP(20-50 connections)
     ↓
[Cache] - Redis (Read hot data here first)
     ↓
[DB Master] - Writes only
  ↙      ↘
[Replica1] [Replica2] - Read load distributed
```

---

## ☑️ Scaling Checklist

- ✅ Step 1: Add read replicas (scale reads 3-5x)
- ✅ Step 2: Implement caching (scale reads 10-20x)
- ✅ Step 3: Connection pooling (prevent connection leak)
- ✅ Step 4: Shard by user_id (if replicas maxed)
- ✅ Monitor: Query latency, connection active count, cache hit %

---

## ⚠️ Common Pitfalls

**Pitfall 1: Sharding too early**
```
// ❌ Company with 1000 users implements sharding
// Result: Complexity explosion for no benefit

// ✅ Scaling order:
1. Optimize queries + indexes (free, 10x improvement)
2. Add caching (cheap, 10-20x improvement)
3. Add read replicas (medium cost, 3-5x improvement)
4. Shard database (LAST RESORT - complexity cost is high)
```

**Pitfall 2: Not using connection pooling**
```java
// ❌ Creating new connection per request
public User getUser(int id) {
    Connection conn = DriverManager.getConnection(url);  // 50-100ms overhead!
    // Query takes 5ms, connection creation takes 50ms
}

// ✅ Use connection pool (HikariCP)
@Bean
public DataSource dataSource() {
    HikariConfig config = new HikariConfig();
    config.setMaximumPoolSize(20);  // Reuse connections
    return new HikariDataSource(config);
}
```

**Pitfall 3: Sending writes to read replicas**
```java
// ❌ Write-after-read inconsistency
userService.updateEmail(userId, newEmail);  // Write to master
User user = userService.getUser(userId);  // Read from replica - OLD EMAIL!
// Replication lag (10-100ms) causes stale read

// ✅ Read from master after write
@Transactional
public void updateAndNotify(int userId, String newEmail) {
    userRepo.updateEmail(userId, newEmail);  // Master
    User user = userRepo.findById(userId);  // Force master read
    emailService.send(user.getEmail());  // Sends to correct email
}
```

**Pitfall 4: Not monitoring replication lag**
```
// ❌ Replica is 5 minutes behind, users see old data
// No alerts, no monitoring

// ✅ Monitor replication lag
SELECT TIMESTAMPDIFF(SECOND, executed_gtid_set, received_gtid_set) AS lag;
Alert if lag > 1 second
```

**Pitfall 5: Over-caching without invalidation strategy**
```java
// ❌ Cache never expires, stale data forever
cache.put("user:" + id, user);  // No TTL!

// ✅ Cache with TTL + invalidation
cache.put("user:" + id, user, 5, TimeUnit.MINUTES);  // Auto-expire

@Transactional
public void updateUser(User user) {
    userRepo.save(user);
    cache.evict("user:" + user.getId());  // Explicit invalidation
}
```

---

## 🛑 When NOT to Use Each Strategy

- ❌ **Read Replicas**: Write-heavy workloads (replicas won't help)
- ❌ **Sharding**: Small datasets (<1M rows), low traffic (<1k concurrent users)
- ❌ **Caching**: Data changes frequently (cache hit rate <50%)
- ❌ **Connection Pooling**: Single-user applications (no concurrency)
- ✅ **DO**: Start simple, measure, then scale based on bottlenecks

---

## 🔗 Related Questions

- [Q18_caching_strategies.md](Q18_caching_strategies.md) - Caching layers for read scaling
- [Q19_load_balancing.md](Q19_load_balancing.md) - Load balancer configuration
- [../Core_Java/Database_SQL/Q24_n_plus_one_problem.md](../Core_Java/Database_SQL/Q24_n_plus_one_problem.md) - Query optimization patterns
- [../Core_Java/Database_SQL/Q28_connection_pooling.md](../Core_Java/Database_SQL/Q28_connection_pooling.md) - HikariCP tuning

---

**Last Updated:** February 22, 2026  
**Next: [Q18_caching_strategies.md](Q18_caching_strategies.md)**
