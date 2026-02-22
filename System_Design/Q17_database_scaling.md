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

**Last Updated:** February 22, 2026  
**Next: [Q18_caching_strategies.md](Q18_caching_strategies.md)**
