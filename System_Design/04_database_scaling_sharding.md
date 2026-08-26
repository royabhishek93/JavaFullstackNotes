# SD_Q02: Database Scaling & Sharding — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 25-30 minutes | **Frequency:** 90% in architect rounds 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "Your orders table has 500 million rows. Queries are taking 10 seconds. Walk me through your scaling strategy." — Real architect round question.

---

## NEW LEARNER FOUNDATION

### What is Database Sharding? (Plain English)
```
Imagine you have a phone book with 1 billion entries. One book is too heavy to search.
Solution: split it into 26 books, one per letter (A-Z).
"Smith, John" → Book S. Fast lookup — only 1/26 of entries to search.

Database sharding = split one huge table across multiple DB servers.
Each server holds a SHARD (subset of rows).

Without sharding:
  All 500M orders on one DB server → slow, single point of failure

With sharding:
  Shard 0: orders where userId % 4 == 0 → DB Server 0
  Shard 1: orders where userId % 4 == 1 → DB Server 1
  Shard 2: orders where userId % 4 == 2 → DB Server 2
  Shard 3: orders where userId % 4 == 3 → DB Server 3
  Each server only holds 125M rows → fast queries
```

### What is Read Replica? (Plain English)
```
Primary DB: handles all WRITES (INSERT, UPDATE, DELETE)
Read Replica: an EXACT COPY of primary, handles only READ queries

Why: 80% of DB traffic in most apps is reads (search, browse, view history).
     Spreading reads across 5 replicas = 5x read capacity.
     Primary DB is freed up for writes.

Replication lag: replica is usually 10-100ms behind primary.
     Problem: user writes then immediately reads — might see old data.
     Fix: read-your-own-writes: route post-write reads to primary for 1 second.
```

---

## BIG PICTURE — Database Scaling Strategy

```
 DATA LAYER — SCALING TIER BY TIER
 ┌──────────────────────────────────────────────────────────────────┐
 │                                                                  │
 │  TIER 1: Single DB (0-10M rows, startup phase)                  │
 │  [Aurora Primary]                                                │
 │  Simple, cheap, easy to maintain.                                │
 │                                                                  │
 │  TIER 2: Read Replicas (10M-100M rows)                          │
 │  [Aurora Primary]  ──replicates──►  [Replica 1]                 │
 │       │ all writes                  [Replica 2]  ◄── reads      │
 │       │                             [Replica 3]                  │
 │  Handles read-heavy workloads. Replication lag ~10ms.            │
 │                                                                  │
 │  TIER 3: Sharding (100M+ rows, write-heavy)                     │
 │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
 │  │ Shard 0    │ │ Shard 1    │ │ Shard 2    │ │ Shard 3    │   │
 │  │ user%4==0  │ │ user%4==1  │ │ user%4==2  │ │ user%4==3  │   │
 │  │ 125M rows  │ │ 125M rows  │ │ 125M rows  │ │ 125M rows  │   │
 │  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
 │  Each shard has its own Primary + 2 Read Replicas.               │
 │                                                                  │
 │  TIER 4: Polyglot Persistence (different DB for different needs) │
 │  ┌──────────────┐ ┌────────────┐ ┌──────────┐ ┌────────────┐   │
 │  │ PostgreSQL   │ │ Cassandra  │ │  Redis   │ │Elasticsearch│  │
 │  │ (orders,     │ │ (activity  │ │ (sessions│ │ (search,    │  │
 │  │  payments)   │ │  feed,     │ │  cache,  │ │  autocomplete│ │
 │  │  ACID needed │ │  time-     │ │  counters│ │  full-text) │  │
 │  │              │ │  series)   │ │          │ │             │  │
 │  └──────────────┘ └────────────┘ └──────────┘ └────────────┘   │
 │                                                                  │
 └──────────────────────────────────────────────────────────────────┘
```

---

## Scenario 1: Choosing a Sharding Strategy

### The Three Strategies

```
RANGE SHARDING: split by value range
  Shard 0: orderId 1 - 10,000,000
  Shard 1: orderId 10,000,001 - 20,000,000
  Shard 2: orderId 20,000,001 - 30,000,000

  ✅ Simple range queries: "orders between Jan 1 and Jan 31" → hit one shard
  ❌ HOT SHARD: all NEW orders go to the latest shard (Shard 2)
     Shard 0, 1 are idle; Shard 2 is overloaded
     Worst for time-series data (orders, logs, events)

HASH SHARDING: shard = hash(key) % N
  Shard = hash(userId) % 4
  Shard 0: userId=1,5,9,13...
  Shard 1: userId=2,6,10,14...

  ✅ Even distribution across shards — no hot shards
  ❌ Range queries are impossible: "all orders from Jan" hits ALL shards
  ❌ Adding shards remaps all keys (use consistent hashing to mitigate)

DIRECTORY SHARDING: lookup table decides which shard
  ShardDirectory: { userId 1-1000 → Shard 0, 1001-2000 → Shard 1 }
  
  ✅ Flexible: move individual users between shards (rebalancing)
  ✅ Hot user (celebrity) → move to dedicated shard
  ❌ Directory lookup on every request — extra network hop
  ❌ Directory itself can become a bottleneck (cache it!)

PRODUCTION DECISION:
  High write throughput + need even distribution → Hash sharding
  Time-series + need range queries → Range sharding + archive old shards
  Large tenants with different traffic patterns → Directory sharding
```

---

## Scenario 2: Hot Shard (Celebrity Problem)

### The Problem
```
Instagram has 500M users. Sharded by userId % 1000 (1000 shards).
Virat Kohli has userId=12345 → shard 345.

Virat posts a photo. 50 million followers check his profile.
50 million reads ALL hit shard 345.
Other 999 shards: idle.
Shard 345: 50 million reads/minute → overloaded → queries time out.

This is the "hot key" / "hot shard" problem.
```

```
FIX 1: Celebrity/VIP shard
  Detect high-traffic users → move them to dedicated "VIP shards"
  Directory sharding: userId=12345 → Shard VIP-1 (dedicated server)
  Other users unaffected

FIX 2: Cache the hot user's data aggressively
  Virat's profile: cache in Redis with TTL=60s
  50M reads hit Redis (fast), NOT the DB
  DB only gets cache misses (~1/min)

FIX 3: Write amplification (fan-out on write vs fan-out on read)
  Push model: when Virat posts, pre-compute feed for all 50M followers
  → Each follower's feed is pre-built in Redis
  → Read is O(1): just read your own cached feed

  Pull model: compute feed on read by fetching Virat's posts
  → 50M concurrent reads all hit DB simultaneously
  → For celebrities (>1M followers): use push model
  → For normal users: use pull model (100 followers = cheap)
```

---

## Scenario 3: Cross-Shard Query

### The Problem
```
You sharded orders by userId.
Business analyst asks: "Show me all orders between $1000-$5000 last month
                        from users in Mumbai."

SQL would be:
  SELECT * FROM orders
  WHERE total BETWEEN 1000 AND 5000
  AND created_at BETWEEN '2026-07-01' AND '2026-07-31'
  AND city = 'Mumbai';

Problem: this doesn't hit one shard — it must hit ALL 100 shards,
         collect results, merge, sort, paginate.
         Cross-shard query = fan-out to all shards = slow + expensive.
```

```
PRODUCTION SOLUTIONS:

Option 1: Separate OLAP database for analytics
  OLAP = Online Analytical Processing (for complex queries, reports)
  Stream all writes to a dedicated analytics DB (Redshift, BigQuery, ClickHouse)
  Business analyst queries the analytics DB, not the production sharded DB
  → Production DB: fast operational queries (by userId, orderId)
  → Analytics DB: fast analytical queries (arbitrary filters, aggregations)

Option 2: Event streaming to Elasticsearch
  All order writes → Kafka → Elasticsearch indexer
  Elasticsearch indexes by: userId, totalAmount, city, createdAt, status
  Business query hits Elasticsearch (distributed full-scan, fast)
  → ES handles fan-out internally across its shards
  → Don't put this load on your transactional DB

Option 3: CQRS (Command Query Responsibility Segregation)
  Write model: sharded PostgreSQL (optimized for writes by userId)
  Read model: denormalized flat table or ES (optimized for any read query)
  Event sourcing: every order event updates both models asynchronously
```

---

## Trap 1: Replication Lag — Reading Stale Data

### The Bug (Flipkart Order Scenario)
```
User places an order (writes to PRIMARY):
  INSERT INTO orders (userId, status) VALUES (123, 'CREATED')

Immediately redirected to "My Orders" page.
"My Orders" reads from READ REPLICA (5 replicas, spreading load).

But the read replica is 200ms behind primary (replication lag).
The new order isn't on the replica yet!
User sees: "You have no recent orders" — even though they just placed one!

Replication lag: Aurora = ~10ms, MySQL RDS = 50-200ms, cross-region = seconds
```

```
FIX 1: Read-your-own-writes (session-level routing)
  After a WRITE: route the SAME user's reads to primary for 1-2 seconds
  Implementation: in Redis, store { userId: lastWriteTimestamp }
  Read request: if lastWrite < 2 seconds ago → route to primary
                otherwise → route to replica

FIX 2: Sticky reads for critical flows
  Checkout flow: reads that immediately follow writes → always primary
  Browse/search: no recent write context → replicas fine

FIX 3: Wait for replica to catch up (Aurora feature)
  // Java with AWS JDBC driver:
  SessionConsistencyMode.EVENTUAL → fast (uses replica)
  SessionConsistencyMode.SESSION  → waits for replica to catch up
  // Use SESSION mode only for read-your-own-writes scenarios
  // Too slow for high-traffic read paths

FIX 4: Accept eventual consistency (most honest)
  Tell UX team: show optimistic UI update immediately (client-side)
  "Your order #12345 has been placed" — show instantly in the UI
  Don't rely on a DB read to confirm what the user just did
```

---

## Trap 2: DB Connection Pool Exhaustion Under Load

### The Bug
```
Spring Boot app with 10 pods × HikariCP pool of 10 connections = 100 connections
PostgreSQL default: max_connections = 100

Works fine at normal load.
Black Friday: HPA scales app to 50 pods × 10 connections = 500 connections
PostgreSQL: REJECTS connections! max 100 exceeded.
All pods get: "too many clients already" errors → 500 errors

The MORE you scale your app, the WORSE the DB connection problem gets!
```

```
FIX: RDS Proxy (or PgBouncer)
  RDS Proxy sits between app and DB.
  App connects to RDS Proxy (max 10,000 connections to proxy).
  Proxy MULTIPLEXES: maintains SMALL pool (e.g. 100) of real DB connections.
  When app pod makes a query: proxy assigns a real DB connection, runs query,
  returns connection to pool immediately.

  50 pods × 10 connections = 500 connections to proxy
  Proxy: 50-100 real connections to PostgreSQL
  PostgreSQL: never exceeds max_connections ✅

  Production config:
  app → RDS Proxy (accepts thousands of connections)
       RDS Proxy → PostgreSQL (maintains small pool of real connections)

  For non-AWS: use PgBouncer (same concept, open source, runs as a sidecar)
```

---

## Polyglot Persistence — Right DB for Right Job

```
USE CASE              → DATABASE          WHY
─────────────────────────────────────────────────────────────────────
Orders, payments      → PostgreSQL/Aurora  ACID, complex queries, joins
User sessions/cache   → Redis              Sub-millisecond reads, TTL
Product search        → Elasticsearch      Full-text, facets, fuzzy match
User activity feed    → Cassandra          High write throughput, time-series
Analytics/reports     → Redshift/BigQuery  Columnar, OLAP, aggregations
Graph (follows/likes) → Neo4j             Relationship traversal
Binary files (images) → S3                Cheap, durable, CDN-able
Counters (views,likes)→ Redis             Atomic INCR, no locking
Config/feature flags  → DynamoDB          Low-latency key-value at scale
```

---

## Interview Cheat Sheet

> "At scale, you hit the DB ceiling in this order: first add read replicas to spread read load (80% of traffic is reads); then add RDS Proxy to prevent connection exhaustion when you scale pods; then shard when writes can't keep up with one primary. For sharding: hash sharding for even distribution (no hot shards), range sharding for time-series data, directory sharding for large multi-tenant systems. The cross-shard query trap catches everyone — analytics and reporting queries should go to a separate OLAP system (Redshift/BigQuery) fed by Kafka, not the transactional sharded DB. Replication lag is real — use read-your-own-writes to prevent users seeing stale data immediately after writing."
