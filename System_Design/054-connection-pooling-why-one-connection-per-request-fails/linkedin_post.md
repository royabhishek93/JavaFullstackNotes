# Connection Pooling — LinkedIn Post

## Post Text (copy-paste ready)

1,000 requests/sec. MySQL's default max_connections is 151. You hit the limit in 0.1 seconds — and your app is down.

- Opening a raw DB connection costs 50–150ms (TCP handshake + TLS + DB auth) — at 1,000 req/sec that's 100 seconds of wasted setup work every single second
- Pool exhaustion is silent and dangerous: pool size 10, 50 concurrent slow queries → 40 requests queue, time out after 30s, and your app's CPU drops to near-zero while every thread is just blocked waiting
- The #1 production bug: connection leaks — a forgotten early-return skips releasing the connection, the pool drains over hours, and only a restart "fixes" it (until it happens again)
- A payment system doing 5,000 TPS with 3 DB calls/transaction = 15,000 raw connection attempts vs Postgres's ~500 connection limit — a pool of just 20-30 connections handles it via queuing
- At fleet scale, pool sizes silently add up: 3 services × 50 connections each = 150, right at MySQL's 151 limit — one more service instance and everything crashes; the fix is PgBouncer/ProxySQL in front of the DB

Swipe → to see the pool-exhaustion diagram, the sizing formula, and the PgBouncer/RDS Proxy/HikariCP comparison.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
1,000 req/sec + 1 connection per request = MySQL down in 0.1s. Here's the pool-sizing formula that actually works 👇

### Variant B — Long (400–600 chars)
Opening a database connection isn't free — TCP handshake, TLS, and DB auth cost 50-150ms before any query runs. Do that per-request at 1,000 req/sec and you blow past MySQL's default 151-connection limit in a tenth of a second. A connection pool (HikariCP, sized at cores×2 + spindle count) fixes it — but pools fail in production too: silent connection leaks that drain the pool over hours, transactions held open across slow external API calls, and pool-size mismatches across services that add up past the DB's real limit. At real scale — 5,000 TPS payment systems, 100K-user flash sales — the fix layers a proxy like PgBouncer or RDS Proxy in front of a small, bounded pool.

---

## Best Time to Post
Tuesday, 9:00–10:00 AM IST (technical deep-dives on connection/infra internals perform best early week when engineers are debugging fresh incidents)

## Engagement Hook
"Has a connection leak ever taken down your app in prod — and how long did it take you to spot it was leaks, not load?"
