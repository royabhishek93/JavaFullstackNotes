# #7 — Database Connection Pool Starvation

> **Category:** Thread Dump Analysis | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"Application is healthy at 100 RPS. At 200 RPS, all requests start timing out with 'Connection is not available, request timed out after 30000ms.' Thread dump analysis?"

## 😊 Explain It Simply (for anyone)
Think of a restaurant with only 10 tables (database connections). If 100 customers arrive per hour and each meal takes 3 minutes, the tables turn over fast enough and everyone gets seated quickly. But once 200 customers arrive per hour, the same 10 tables simply cannot keep up — customers start piling up in the waiting area, and eventually the host tells latecomers "sorry, we can't seat you, please come back later" because they've waited too long.

That's exactly what a **connection pool** does: it's a fixed-size set of "tables" (database connections) that every request must borrow before it can talk to the database, and return when it's done. If requests arrive faster than tables free up, everyone queues, and eventually the ones waiting longest get a timeout error instead of a table. The math is simple: how many tables you need depends on how many customers arrive per second multiplied by how long each one sits at their table.

## 📊 Visualize It
```
100 RPS × 50ms/query = 5 connections needed   → OK (pool=10)
200 RPS × 50ms/query = 10 connections needed  → AT THE EDGE
                                                  (any slowdown = timeout)

[ 200 requests ] ──► [ Pool: 10 connections ] ──► DB
                            ▲
                    190 threads TIMED_WAITING
                    "Connection is not available"
```

## 🏭 The Real Production Answer (15-YOE Level)
"That's HikariCP's connection acquisition timeout message. The thread dump will show me the exact picture:

```
"http-nio-8080-exec-15" TIMED_WAITING
  at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:213)
  at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:162)
  at com.corp.repository.UserRepository.findById(UserRepository.java:...)
```

All request threads are sitting in HikariCP's queue waiting for a DB connection. The pool is exhausted. This means: requests/second × average query time > pool size.

At 100 RPS with avg 50ms query time: 100 × 0.05 = 5 concurrent connections needed.
At 200 RPS with avg 50ms: 200 × 0.05 = 10 concurrent connections needed.

If maxPoolSize=10, 200 RPS is right at the edge. Any query slowdown pushes you over.

Diagnosis steps:
1. Check HikariCP metrics (if Micrometer is wired): `hikaricp.connections.active`, `hikaricp.connections.pending`
2. Enable leak detection: `spring.datasource.hikari.leak-detection-threshold=2000`
3. Check DB for long-running queries: `SELECT * FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC`

Fix options: increase pool size (carefully — DB has connection limits), reduce query time (indexes, query optimization), add read replicas for read queries, add a caching layer for repeated queries."

## 🔑 Key Takeaway
Connection pool exhaustion is math: RPS × avg query time must stay under pool size — spot it in `jstack` via threads stuck in `HikariPool.getConnection()`, then fix the query time or scale the pool, not just the thread count.
