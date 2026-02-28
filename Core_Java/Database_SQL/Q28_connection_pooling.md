# Q28: Connection Pooling (Reuses DB Connections)

**Study Time:** 8-10 minutes | **Frequency:** 75% in interviews 🔥 | **Difficulty:** ⭐⭐⭐

---

## Scenario

A service opens a new DB connection per request:

```java
public void handleRequest() throws SQLException {
	Connection c = DriverManager.getConnection(url, user, pass);
	// query
	c.close();
}
```

Under load, response time spikes and the DB CPU goes high. What is the fix?

---

## Key Principle

**Connection pooling reuses DB connections** instead of opening a new TCP connection each time.

Opening a DB connection is expensive (TCP handshake, auth, TLS, server resources). A pool keeps a fixed set of ready connections and hands them out quickly.

---

## How Pooling Works

```
App Thread → Pool → Existing Connection
				↕
			 Reused
```

1. App borrows a connection from the pool
2. Executes queries
3. Returns it to the pool (not closed physically)
4. Pool reuses it for the next request

---

## Why It Matters

- Faster response time
- Lower DB CPU usage
- Prevents "too many connections" errors
- Smooths spikes under load

---

## Example (Spring Boot + HikariCP)

```properties
# application.properties
spring.datasource.url=jdbc:postgresql://db:5432/app
spring.datasource.username=app
spring.datasource.password=secret

# Pool config
spring.datasource.hikari.maximum-pool-size=20
spring.datasource.hikari.minimum-idle=5
spring.datasource.hikari.connection-timeout=30000
spring.datasource.hikari.idle-timeout=600000
spring.datasource.hikari.max-lifetime=1800000

# Optional: leak detection (log stack trace if not returned)
spring.datasource.hikari.leak-detection-threshold=5000

# Optional: metrics (Micrometer / Actuator)
management.endpoints.web.exposure.include=health,info,metrics
management.metrics.enable.hikari=true
```

---

## Correct Usage Pattern

```java
public void handleRequest(DataSource dataSource) throws SQLException {
	try (Connection c = dataSource.getConnection()) {
		// query
	} // returns to pool, not closed
}
```

✅ `try-with-resources` closes the connection object, which returns it to the pool.

---

## HikariCP Metrics (What to Watch)

If Spring Boot Actuator + Micrometer are enabled, look at:

- `hikaricp.connections.active` - in-use connections
- `hikaricp.connections.idle` - ready connections
- `hikaricp.connections.pending` - threads waiting for a connection
- `hikaricp.connections.max` - pool size

**Healthy signal:** low pending, active below max, idle > 0 under load.

---

## Leak Detection Steps

1. Enable leak detection:

```properties
spring.datasource.hikari.leak-detection-threshold=5000
```

2. Trigger workload and watch logs:

```
HikariPool-1 - Connection leak detection triggered
Connection leak trace:
  at com.app.repo.OrderRepo.findOrders(OrderRepo.java:42)
```

3. Fix the code path:

- Ensure every connection is closed in `try-with-resources`
- Avoid early returns before closing
- Check async code paths that swallow exceptions

---

## Interview Q&A

### Q1: Why is pooling faster than opening connections?

**Answer:**
```
Opening a DB connection requires TCP + auth + TLS.
Pooling reuses existing connections, so each request
avoids that overhead.
```

---

### Q2: What happens if you call close() on a pooled connection?

**Answer:**
```
close() returns the connection to the pool.
It does NOT close the physical DB connection.
```

---

### Q3: How do you pick pool size?

**Answer:**
```
Based on DB capacity and concurrency:
- Too small → waits and timeouts
- Too large → DB overload
Start with 10-20 and load test.
```

---

### Q4: What is a connection leak?

**Answer:**
```
A connection is borrowed but never returned.
Eventually the pool is exhausted and requests block.
```

---

### Q5: How to detect leaks?

**Answer:**
```
Use pool metrics + leak detection logs.
HikariCP has leakDetectionThreshold.
```

---

## Common Pitfalls

```java
❌ Pitfall 1: Creating DriverManager connections directly
// Bypasses pool

❌ Pitfall 2: Not closing connections
// Causes pool exhaustion

❌ Pitfall 3: Pool too large
// DB gets overloaded

❌ Pitfall 4: Using a pool per request
// Defeats pooling benefits
```

---

## Interview Answer (Concise)

**Q: "Why use a connection pool?"**

**Answer:**

> "Because it reuses DB connections. Opening a new connection is expensive. A pool keeps a fixed set of connections ready, so requests borrow and return them quickly. This improves latency, avoids DB connection storms, and prevents 'too many connections' errors."

---

## Key Takeaways

| Concept | Why It Matters | Interview Score |

## ⚠️ Common Pitfalls

**Pitfall 1: Not closing connections (connection leak)**
```java
// ❌ Connection never returned to pool!
Connection conn = dataSource.getConnection();
Statement stmt = conn.createStatement();
ResultSet rs = stmt.executeQuery("SELECT * FROM users");
// Forgot to close! Connection never returns to pool

// ✅ Always use try-with-resources
try (Connection conn = dataSource.getConnection();
	 Statement stmt = conn.createStatement();
	 ResultSet rs = stmt.executeQuery("SELECT * FROM users")) {
	// Automatically closed
}
```

**Pitfall 2: Pool size too small or too large**
```
// ❌ Pool size = 2, but 100 concurrent requests
// Result: 98 requests waiting for connection!

// ❌ Pool size = 1000, but DB max_connections = 100
// Result: DB rejects connections

// ✅ Formula: Pool size = (core_count * 2) + disk_spindles
// Example: 8 cores + 1 SSD = 17 connections
spring.datasource.hikari.maximum-pool-size=20
```

**Pitfall 3: Long-running queries block pool**
```java
// ❌ Query takes 30 seconds, holds connection
Connection conn = pool.getConnection();
// Long query blocks pool for 30 seconds
ResultSet rs = stmt.executeQuery("SELECT * FROM huge_table");  // No LIMIT!

// ✅ Use query timeout + pagination
stmt.setQueryTimeout(5);  // 5 seconds max
String query = "SELECT * FROM huge_table LIMIT 1000";
```

**Pitfall 4: Not monitoring pool metrics**
```
// ❌ Pool exhausted, but you don't know
// All connections in use, requests timing out

// ✅ Monitor HikariCP metrics
Active connections: 19 / 20  // Almost full!
Pending threads: 10  // Requests waiting
→ Increase pool size or investigate slow queries
```

**Pitfall 5: Creating multiple DataSources**
```java
// ❌ Creating new pool per request
public User getUser(int id) {
	DataSource ds = new HikariDataSource(config);  // NEW POOL!
	// Result: No reuse, defeats purpose of pooling
}

// ✅ Single DataSource bean (Spring manages)
@Bean
public DataSource dataSource() {
	return new HikariDataSource(config);  // Singleton
}
```

---

## 🛑 When NOT to Use Connection Pooling

- ❌ Single-user desktop applications (no concurrency)
- ❌ Batch jobs with 1 connection (pooling overhead not worth it)
- ❌ Serverless functions (connection pooling doesn't survive invocations)
- ✅ DO use: Web servers, APIs, microservices (high concurrency)

---

## 🔗 Related Questions

- [Q23_acid_properties.md](Q23_acid_properties.md) - Transaction fundamentals
- [Q24_n_plus_one_problem.md](Q24_n_plus_one_problem.md) - Query optimization
- [../../System_Design/Q17_database_scaling.md](../../System_Design/Q17_database_scaling.md) - Database scaling strategies

---

## Key Takeaways
|---------|----------------|-----------------|
| Reuses DB connections | Core idea | ⭐⭐⭐⭐⭐ |
| Pool sizing | Performance and stability | ⭐⭐⭐⭐ |
| Connection leaks | Common production issue | ⭐⭐⭐⭐ |
| Proper close() usage | Prevents pool exhaustion | ⭐⭐⭐⭐ |
