# #26 — Slow Responses Under Load — Connection Pool Exhaustion

> **Category:** Common Production Incidents | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"Walk me through diagnosing: p99 latency spikes from 200ms to 5000ms under load, error logs show `HikariPool-1 - Connection is not available, request timed out after 30000ms`, but p50 latency looks fine. How do you find the bottleneck?"

## 😊 Explain It Simply (for anyone)
Imagine a coffee shop with only 10 mugs (database connections). Even if the barista (the database) is fast, if 50 customers show up at once, 40 of them just stand around waiting for a mug to become free — not because the coffee is slow, but because there simply aren't enough mugs. That's connection pool exhaustion: your app has a limited pool of database connections, and under heavy load, requests queue up waiting for one to free up rather than failing or running slow themselves. Some customers (p50) get lucky and grab a mug immediately; others (p99) wait so long they give up — which is exactly the "fine average, terrible tail" pattern you see in the symptoms.

## 📊 Visualize It
```
10 DB connections (mugs), 200 concurrent requests (customers)

[conn][conn][conn]...[conn]  <- all 10 busy
      ↑ 190 requests waiting in line ↑
p50: fast (got a mug immediately)
p99: 30000ms timeout (never got a mug) --> HikariPool error
```

## 🏭 The Real Production Answer (15-YOE Level)

**Symptoms:**
- p99 latency spikes under load (200ms → 5000ms)
- Error logs show `HikariPool-1 - Connection is not available, request timed out after 30000ms`
- p50 latency is fine (some requests fast, some very slow)

**Diagnosis:**
```bash
# Check how many threads are waiting for a DB connection
jstack <pid> | grep -c "HikariPool\|getConnection\|JDBC"

# Arthas — see connection pool state
ognl "@com.zaxxer.hikari.HikariDataSource@pool.getActiveConnections()"
ognl "@com.zaxxer.hikari.HikariDataSource@pool.getIdleConnections()"
ognl "@com.zaxxer.hikari.HikariDataSource@pool.getPendingAcquires()"

# Spring metrics
curl localhost:8080/actuator/metrics/hikaricp.connections.pending
```

**Root causes:**
1. Pool too small for load (`maximumPoolSize` default = 10, but you have 200 request threads)
2. Long-running transactions holding connections
3. Connection not returned (forgot to close / not in try-with-resources)
4. DB queries slow under load, connections held longer → pool starved

**Little's Law for sizing:**
```
Pool size = (Concurrent requests) × (DB response time)
         = 100 requests × 0.05s = 5 connections minimum
With safety margin: 5 × 2 = 10 connections

BUT: if DB response time increases to 0.5s under load:
     100 × 0.5 = 50 connections needed
```

**Fix:**
```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 20        # tune based on Little's Law
      connection-timeout: 3000     # fail fast — don't wait 30s
      idle-timeout: 600000
      max-lifetime: 1800000
      leak-detection-threshold: 5000  # warn if connection held >5s
```

## 🔑 Key Takeaway
Check `active` vs `pending` connections first — if active equals max pool size and pending is climbing, you have pool starvation, not a slow database.
