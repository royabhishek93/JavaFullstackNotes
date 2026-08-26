# Database Optimization — Indexing, Partitioning, Replication, Sharding
> How to scale a database from 100 req/sec to 5000 req/sec without replacing it.

---

# PAGE 1 — Title & Rapid Answer Script

## What This Topic Is Really About
A database that was correct at launch becomes the bottleneck as traffic grows.
This guide covers the 6-technique escalation ladder to fix it — in the right order,
for the right reason, with the right trade-offs.

---

## Rapid Answer Script (speak this in 2-3 minutes)

```
"When the database becomes a bottleneck, I follow a measured escalation ladder.

 I start by profiling queries — finding full table scans and N+1 patterns
 that waste the database I already have. Then I add targeted indexes on
 columns used in WHERE and JOIN clauses, which gets me O(log N) lookups
 instead of full scans.

 If single-node CPU or memory is the ceiling, I scale vertically first —
 it's cheap and fast with no architecture change.

 Next I introduce caching (Redis) for hot repeated reads and read replicas
 for read-heavy workloads. Replicas don't help writes — they only copy
 the same data to multiple nodes.

 When a table gets too large to manage — say 100M+ rows — I partition it
 by time or range. Partition pruning means March queries only scan March.

 Finally, if one machine can't hold the dataset or handle write throughput,
 I shard: hash(user_id) % N routes each user to one shard. This is the
 most complex step and I only do it when measurement proves it's needed.

 The key: each technique solves one specific bottleneck. I don't apply
 all six at day one."
```

---

# PAGE 2 — Glossary

| Term | Simple definition | Real-world example |
|---|---|---|
| Full Table Scan | Database reads every row to find matches | 100M users, no index on email → scans all 100M |
| B-Tree Index | Sorted tree structure for fast lookup | `email` index: O(log N) lookup instead of O(N) |
| Composite Index | Index on multiple columns together | `(customer_id, created_at)` for order history |
| Query Plan | How the DB engine executes a query | `EXPLAIN SELECT ...` shows index use vs full scan |
| Primary | Write-accepting master DB node | All INSERTs/UPDATEs go here |
| Replica (Slave) | Read-only copy of primary | SELECT queries routed here to reduce primary load |
| Replication Lag | Delay before replica reflects primary's writes | User updates profile → reads replica → sees old value |
| Partitioning | Split one logical table into smaller pieces | `orders_2026_01`, `orders_2026_02` — same DB server |
| Partition Pruning | Query only scans relevant partition | `WHERE month=3` → only reads `orders_2026_03` |
| Sharding | Different data on different DB servers | `hash(user_id) % 3` → user goes to shard 1/2/3 |
| Shard Key | Column used to route data to a shard | `user_id`, `tenant_id`, `region` |
| Hot Partition | One partition gets disproportionate traffic | All new orders in 2026_04 partition → overloaded |
| N+1 Problem | 1 query to list + N queries per item | Fetch 100 orders → 100 separate user lookups |
| Connection Pool | Reuse DB connections instead of opening new ones | HikariCP: 50 connections shared by 500 threads |
| Vertical Scaling | Bigger hardware (more CPU/RAM) on same node | 4 cores → 16 cores, 16GB → 128GB RAM |
| Horizontal Scaling | More nodes, each with a subset of data | Sharding: add 3 more DB servers |
| OLTP | Transactional workload — small fast reads/writes | Orders, payments, user login |
| OLAP | Analytical workload — large aggregations | BI dashboards, reporting, GROUP BY |

---

# PAGE 3 — The Core Scenario (from image)

## User Onboarding Service — Scaling Journey

```
The system: User Onboarding Svc → UserDB

Traffic grows step by step — and each step needs a different technique:

┌─────────────────────────────────────────────────────────────────────────────┐
│  Step │  Load          │  Problem                    │  Technique           │
├───────┼────────────────┼─────────────────────────────┼──────────────────────┤
│  1    │  100 req/sec   │ Queries are slow             │ Query Optimisation   │
│  2    │  1000 req/sec  │ Full table scans on email    │ Indexing (READ)      │
│  3    │  1500 req/sec  │ DB CPU/memory is saturated   │ Vertical Scaling     │
│  4    │  1800 req/sec  │ Too many reads hit primary   │ Replication (Read)   │
│  5    │  2000 req/sec  │ Table too large to manage    │ Partitioning         │
│  6    │  2500 req/sec  │ 20% write + 80% read traffic │ Sharding             │
│  7    │  5000 req/sec  │ No single node can handle it │ Full sharded cluster │
└─────────────────────────────────────────────────────────────────────────────┘

Key insight from step 6:
  2500 req/sec = 20% registration (Write) + 80% login/fetch (Read)
  → Writes and reads have different bottlenecks, need different solutions

ARCHITECTURE EVOLUTION:

  Stage 1–3 (single node):
  ┌───────────────────────────────────────────────┐
  │  User Onboarding Svc                          │
  │         │ write                               │
  │         ▼                                     │
  │   [ UserDB (master) ]   ← all reads + writes  │
  └───────────────────────────────────────────────┘

  Stage 4 (replication — 1000 req/sec slave):
  ┌───────────────────────────────────────────────────┐
  │  User Onboarding Svc                              │
  │         │ write                                   │
  │         ▼                                         │
  │   [ UserDB (master) ] ──replicate──► [ UserDB ]   │
  │                                     [ UserDB ]   │
  │                                  (Slaves: reads)  │
  │                                  1000 req/sec     │
  │                                  1000 req/sec     │
  └───────────────────────────────────────────────────┘

  Stage 5–6 (partition + shard):
  ┌──────────────────────────────────────────────────┐
  │  [ 1 million ]  → partition 1                    │
  │  [ 1M+ – 2M ]  → partition 2                    │
  │  [ 2M+ – 3M ]  → partition 3                    │
  │  Each partition on a different shard DB server   │
  └──────────────────────────────────────────────────┘
```

---

# PAGE 4 — Technique 0: Query Optimisation (Before Everything Else)

```
Before adding ANY infrastructure, fix the queries that waste what you have.

CHECKLIST:
  ✓ Which queries consume the most DB CPU / time?
    → EXPLAIN ANALYZE SELECT ... (look for Seq Scan → needs index)
  ✓ Are you selecting unnecessary columns?
    → SELECT * FROM users    BAD  (fetches 50 columns)
    → SELECT name, email     GOOD (fetches 2 columns)
  ✓ N+1 problem?
    → SELECT * FROM orders LIMIT 100            (1 query)
    → then for each order: SELECT * FROM users  (100 queries)
    → Fix: JOIN or batch fetch
  ✓ Are writes batched?
    → INSERT one row at a time × 1000           BAD
    → INSERT ... VALUES (row1),(row2),...,(row1000) GOOD
  ✓ Are connections pooled?
    → 500 threads each opening/closing DB connection  BAD
    → HikariCP: 50 reused connections for 500 threads GOOD

REAL QUERY EXAMPLE (from image):
  select name, profile_img, address
  from UserDB
  where emailId = 'asda@gmail.com'

  WITHOUT INDEX: Full table scan — 100M rows checked one by one.
  WITH INDEX on emailId: B-Tree lookup — O(log N), found in milliseconds.
```

**Interview line**: "Before I add any infrastructure, I run `EXPLAIN ANALYZE` on the slowest queries. A missing index or an N+1 pattern can cause 100× slowdown that no amount of hardware fixes."

---

# PAGE 5 — Technique 1: Indexing

## B-Tree Index (from image)

```
QUERY: select name, profile_img, address from UserDB where emailId = 'asda@gmail.com'

WITHOUT INDEX (Full Table Scan):
  users table
  row 1  → not it
  row 2  → not it
  ...
  row 78,422,901 → MATCH   ← scanned every row!

WITH B-TREE INDEX ON emailId:

                      ┌──────────────┐
                      │  Root Page   │
                      └──────┬───────┘
                             │
                      ┌──────▼───────┐
                      │  Index Node  │  Root Node
                      │   1 – 1000   │
                      └──────┬───────┘
                       ┌─────┴──────┐
              ┌────────▼───┐    ┌───▼────────┐
              │ Index Node │    │ Index Node │  Index Nodes
              │  1 – 500   │⇔  │ 501 – 1000 │
              └──┬─────────┘    └─────────┬──┘
         ┌───────┴────┐          ┌────────┴───────┐
  ┌──────▼──┐  ┌──────▼──┐  ┌───▼─────┐  ┌───────▼──┐
  │ 1 – 250 │  │251 – 500│  │501 – 750│  │751 – 1000│  Index Nodes
  └──┬──────┘  └──┬──────┘  └──┬──────┘  └──┬───────┘
     │             │            │             │
  ┌──▼──────┐ ┌───▼─────┐ ┌───▼─────┐ ┌────▼──────┐
  │Leaf Node│ │Leaf Node│ │Leaf Node│ │ Leaf Node │
  │1, 2,…125│ │126…,250 │ │251,…375 │ │376,…,500  │
  └─────────┘ └─────────┘ └─────────┘ └───────────┘
  (continues for all 8 leaf nodes: 501-625, 626-750, 751-875, 876-1000)

  ← Leaf nodes are doubly-linked for range scans →

  RESULT: O(log N) traversal — find emailId in 4-5 hops, not 100M row scans.
```

## Index Design Rules

```
GOOD INDEX CANDIDATES:
  ✓ Columns in WHERE clause:    WHERE emailId = 'x'
  ✓ Columns in JOIN:            JOIN orders ON orders.user_id = users.id
  ✓ Columns in ORDER BY:        ORDER BY created_at DESC
  ✓ Columns in GROUP BY:        GROUP BY customer_id
  ✓ Composite for common combo: INDEX(customer_id, created_at)

BAD — DO NOT INDEX:
  ✗ Every column  → writes/updates must maintain ALL indexes (write amplification)
  ✗ Low-cardinality columns  → INDEX(gender) has 2 values, scans 50% of table anyway
  ✗ Columns never in WHERE/JOIN → unused index = wasted storage + slower writes

WRITE COST:
  INSERT / UPDATE / DELETE → must also update every index on that table
  Trade-off: +storage, -write speed, +read speed for targeted queries.
```

**Interview line**: "An index is a B-Tree data structure. Finding a value becomes O(log N) instead of O(N). But every index slows writes because the tree must be updated. I only index columns actually used in WHERE, JOIN, or ORDER BY."

---

# PAGE 6 — Technique 2: Vertical Scaling

```
SIMPLEST first step — bigger hardware, zero architecture change.

  Database server upgrade:
  ┌─────────────────────────────────────────────────────────────┐
  │  CPU:   4 cores    →  16 cores   (handle more connections)  │
  │  RAM:   16 GB      →  128 GB     (more data fits in memory) │
  │  Disk:  HDD/SATA   →  NVMe SSD   (10× faster I/O)          │
  │  IOPS:  3,000      →  100,000    (high-throughput storage)  │
  └─────────────────────────────────────────────────────────────┘

WHEN TO USE:
  ✓ Query optimization already done (no obvious waste)
  ✓ Bottleneck is DB CPU or memory (not query logic)
  ✓ Budget allows it and scale is not extreme yet
  ✓ Fastest path to relief — no code change required

WHEN TO STOP:
  ✗ There's a hardware ceiling (biggest RDS instance still not enough)
  ✗ Cost of vertical scaling exceeds horizontal alternatives
  ✗ Single node = single point of failure (no HA)

TRADE-OFF:
  Pro:  Immediate relief, no code change, simple operations
  Con:  Ceiling exists, SPOF risk, can be expensive, not infinite
```

---

# PAGE 7 — Technique 3: Caching

```
PROBLEM: Same expensive query runs 10,000 times/sec for the same product page.
SOLUTION: Cache the result in Redis — serve from memory, skip the DB.

CACHE-ASIDE FLOW (most common pattern):

  App ──────GET product:42──────► Redis
              │
              │ MISS (not in cache)
              ▼
  App ────SELECT FROM products──► Database
              │
              │ result
              ▼
  App ──SET product:42 {..} EX 300──► Redis
              │
              │ next 300 sec: serve from cache
              ▼
           Client

WHAT TO CACHE:
  ✓ Hot product/user pages (same data, many reads)
  ✓ Expensive aggregation results (SUM, COUNT over large tables)
  ✓ Session state, rate-limit counters, OTP codes
  ✓ Configuration and reference data (rarely changes)

WHAT NOT TO CACHE:
  ✗ Financial balances (must always be accurate)
  ✗ Inventory counts during checkout (stale = oversell)
  ✗ Anything requiring strong consistency

FAILURE PATTERNS:
  Cache stampede:  Many requests miss simultaneously → all hit DB at once
  Fix: mutex/lock on cache miss, or probabilistic early expiry

  Hot key:  One viral product's key receives 100K req/sec to one Redis node
  Fix: key-level sharding or local in-process L1 cache

  Treating cache as source of truth: cache crash → data loss
  Fix: cache is ALWAYS a copy; DB is source of truth

TRADE-OFF:
  Pro:  Dramatic read latency reduction (<1ms vs 30ms DB), reduces DB load
  Con:  Stale data risk, invalidation complexity, extra component to operate
```

---

# PAGE 8 — Technique 4: Replication

## Primary-Replica Architecture (from image)

```
PROBLEM: 1800 req/sec — too many reads for one node. Writes must be durable.
SOLUTION: Replicate data to read-only slave nodes.

  User Onboarding Svc
          │
          │ write (20% of traffic)
          ▼
  ┌───────────────────┐
  │  UserDB (master)  │ ──── replicates ────►  [ UserDB (Slave 1) ]
  │  (primary)        │                              ↕ reads
  └───────────────────┘ ──── replicates ────►  [ UserDB (Slave 2) ]
                                                     ↕ reads
                                              1000 req/sec each slave

  ALL writes → primary
  SELECT queries → distributed across slaves (round-robin or load balancer)

WHAT REPLICATION SOLVES:
  ✓ More read capacity (add slaves for more SELECT throughput)
  ✓ Failover (if primary dies → promote a slave to primary)
  ✓ Geo-replication (replica in US-EAST, EU-WEST for local reads)
  ✓ Analytics isolation (run expensive reports against replica, not primary)

WHAT REPLICATION DOES NOT SOLVE:
  ✗ Write bottleneck (all writes still go to primary)
  ✗ Storage limit (every replica stores the SAME full dataset)
  ✗ Very large table queries (full scan still full scan on replica)

REPLICATION LAG:
  With async replication (default): replica may lag 10ms–1sec behind primary.
  Scenario: user changes profile → immediately reads from replica → sees old data.

  Solutions:
  ─ Read-your-own-writes: route user's own reads to primary for 1 sec after write
  ─ Synchronous replication: primary waits for replica ACK (slower writes, no lag)
  ─ Sticky sessions: route same user to same replica

TRADE-OFF:
  Pro:  Simple to set up, scales reads linearly, improves availability
  Con:  Replication lag, no write scale, each replica stores full copy
```

---

# PAGE 9 — Technique 5: Partitioning

## Dividing a Large Table (from image)

```
PROBLEM: 2000 req/sec, orders table has 500M rows. Queries scan too much data.
SOLUTION: Split one logical table into smaller physical pieces.

PARTITIONING VISUAL (from image):

  ORDERS (one logical table, 500M rows)
  ┌─────────────────────────────────────────────────────────┐
  │  [ 1 million  ]  →  Partition 1  (rows 1 to 1M)        │
  │  [ 1M+ – 2M  ]  →  Partition 2  (rows 1M to 2M)       │
  │  [ 2M+ – 3M  ]  →  Partition 3  (rows 2M to 3M)       │
  │  [ 3M+ – 4M  ]  →  Partition 4  (rows 3M to 4M)       │
  └─────────────────────────────────────────────────────────┘
  Query for rows 1.2M–1.5M → only scans Partition 2 (partition pruning!)

REAL EXAMPLE — orders by month:
  ORDERS (one logical table)
  ├── orders_2026_01  (January only)
  ├── orders_2026_02  (February only)
  ├── orders_2026_03  (March only)
  └── orders_2026_04  (April only)

  Query: SELECT * FROM orders WHERE created_at BETWEEN '2026-03-01' AND '2026-03-31'
  → Only scans orders_2026_03  ← PARTITION PRUNING

PARTITIONING STRATEGIES:
  Range:  date, price, ID intervals
          → "partition by month" or "partition by ID range 1M-2M"
  List:   region, category, status
          → "partition by country: IN, US, EU"
  Hash:   distribute evenly when no natural range
          → hash(user_id) % 4 → 4 roughly equal partitions

WHAT PARTITIONING SOLVES:
  ✓ Large table queries faster (only scan relevant partition)
  ✓ Archive/delete old data easily (DROP PARTITION orders_2024_01 = instant)
  ✓ Maintenance per partition (REINDEX on one month, not full table)
  ✓ Separate hot recent data from cold historical data

WHAT PARTITIONING DOES NOT SOLVE:
  ✗ Write bottleneck (all still go to same DB server)
  ✗ Storage limit (all partitions still on same machine)
  ✗ Cross-partition queries (query touching all partitions = no benefit)

CRITICAL: partitioning ≠ sharding
  Partitioning: logical split, same DB server
  Sharding:     physical split, different DB servers

TRADE-OFF:
  Pro:  Faster range queries, easy archival, manageable large tables
  Con:  Poor partition key → hot partitions, no improvement for cross-partition queries
```

---

# PAGE 10 — Technique 6: Sharding

## Distributing Data Across Servers (from image)

```
PROBLEM: 2500 req/sec (20% write + 80% read). One server can't hold or serve the data.
SOLUTION: Different subsets of data on different DB servers.

SHARDING VISUAL (from image):

  User Onboarding Svc
          │
          ▼
  ┌───────────────────┐
  │   Routing Layer   │  ← hash(user_id) % 3 → which shard?
  └──┬────────┬───────┘
     │        │        │
     ▼        ▼        ▼
  ┌──────┐ ┌──────┐ ┌──────┐
  │Shard1│ │Shard2│ │Shard3│   ← each shard: independent DB server
  │users │ │users │ │users │     with its own storage + CPU
  │0-33% │ │34-66%│ │67-99%│
  └──────┘ └──────┘ └──────┘

SHARD KEY SELECTION (most important decision):
  ✓ hash(user_id)   → even distribution, query by user → one shard
  ✓ tenant_id       → SaaS: each org on its own shard
  ✓ region          → geographic sharding: IN data in India shard
  ✗ created_at      → all new data hits latest shard (time-based hot spot)
  ✗ status          → all "active" rows on one shard (cardinality problem)

WHAT SHARDING SOLVES:
  ✓ Dataset no longer fits on one machine (storage scale)
  ✓ Write throughput distributed across shards
  ✓ Tenant or regional isolation
  ✓ Compute and storage grow by adding shards

WHAT BECOMES HARDER:
  ✗ Cross-shard JOINs (user in shard1, orders in shard2 → no easy JOIN)
  ✗ Cross-shard transactions (2PC needed, complex and slow)
  ✗ Global uniqueness (auto-increment IDs collide across shards → use UUID/Snowflake)
  ✗ Resharding (adding a 4th shard → massive data migration)
  ✗ Operational complexity (backups, monitoring, migrations per shard)

TRADE-OFF:
  Pro:  Unlimited horizontal scale for writes + storage
  Con:  Largest complexity jump — routing, resharding, cross-shard queries, distributed txns
  Rule: Only shard when measurement proves one node is the bottleneck.
```

---

# PAGE 11 — Technique Comparison Table

```
┌─────────────────┬──────────────────────┬──────────────────────┬─────────────────────────┐
│ Technique       │ What it solves       │ What it does NOT     │ When to apply           │
│                 │                      │ solve                │                         │
├─────────────────┼──────────────────────┼──────────────────────┼─────────────────────────┤
│ Query           │ Wasteful queries,    │ Hardware limits,     │ ALWAYS first — before   │
│ Optimisation    │ N+1, missing index   │ storage limits       │ any infrastructure      │
├─────────────────┼──────────────────────┼──────────────────────┼─────────────────────────┤
│ Indexing        │ Slow targeted reads  │ Write speed,         │ After profiling shows   │
│                 │ (WHERE, JOIN)        │ full table scans     │ full scans              │
├─────────────────┼──────────────────────┼──────────────────────┼─────────────────────────┤
│ Vertical        │ CPU/RAM/IO ceiling   │ HA, cost ceiling,    │ Before distributing —   │
│ Scaling         │                      │ data distribution    │ fast + simple           │
├─────────────────┼──────────────────────┼──────────────────────┼─────────────────────────┤
│ Caching         │ Repeated reads,      │ Write load, strong   │ Hot read-heavy data     │
│                 │ expensive queries    │ consistency needs    │ with acceptable staleness│
├─────────────────┼──────────────────────┼──────────────────────┼─────────────────────────┤
│ Replication     │ Read scale,          │ Write scale,         │ Read-heavy, >70% reads, │
│                 │ HA + failover        │ storage limit        │ need failover           │
├─────────────────┼──────────────────────┼──────────────────────┼─────────────────────────┤
│ Partitioning    │ Large tables,        │ Write bottleneck,    │ Tables with 100M+ rows, │
│                 │ range queries,       │ cross-partition load │ time-range heavy queries│
│                 │ archival             │                      │                         │
├─────────────────┼──────────────────────┼──────────────────────┼─────────────────────────┤
│ Sharding        │ Write throughput,    │ Cross-shard joins,   │ One node is proven      │
│                 │ storage beyond       │ distributed txns,    │ insufficient for writes │
│                 │ one node             │ global uniqueness    │ or storage              │
└─────────────────┴──────────────────────┴──────────────────────┴─────────────────────────┘

CRITICAL DISTINCTIONS (interviewers love testing these):

  Partitioning vs Sharding:
  ┌──────────────────────────┬──────────────────────────────────────────────────┐
  │ Partitioning             │ Sharding                                         │
  ├──────────────────────────┼──────────────────────────────────────────────────┤
  │ One logical table        │ Different subsets on DIFFERENT servers           │
  │ Smaller physical pieces  │ Each shard is an independent DB instance         │
  │ Same DB server           │ Different DB servers                             │
  │ Manages large datasets   │ Distributes storage AND write load               │
  │ Logical division         │ Physical, distributed division                   │
  └──────────────────────────┴──────────────────────────────────────────────────┘

  Replication vs Sharding:
  ┌──────────────────────────┬──────────────────────────────────────────────────┐
  │ Replication              │ Sharding                                         │
  ├──────────────────────────┼──────────────────────────────────────────────────┤
  │ Same data on all nodes   │ Different data on each node                      │
  │ Scales READS             │ Scales WRITES + storage                          │
  │ Improves availability    │ Does not improve availability by itself          │
  │ Simple failover          │ Complex routing + resharding                     │
  └──────────────────────────┴──────────────────────────────────────────────────┘
```

---

# PAGE 12 — Full Architecture Evolution Diagram

```
STAGE 1: 100 req/sec — Single node, just query + index
┌──────────────────────────────────────────────────────────┐
│  App Server  →  UserDB (Primary)                         │
│                 ↑                                        │
│              INDEX on emailId (B-Tree)                   │
└──────────────────────────────────────────────────────────┘

STAGE 2: 1000 req/sec — Add vertical scaling
┌──────────────────────────────────────────────────────────┐
│  App Server  →  UserDB                                   │
│                 CPU: 4→16 cores, RAM: 16→128GB           │
└──────────────────────────────────────────────────────────┘

STAGE 3: 1500 req/sec — Add caching layer
┌──────────────────────────────────────────────────────────┐
│  App Server  →  Redis Cache  →  UserDB (on miss)         │
│                 90% hits ↑     10% fallthrough           │
└──────────────────────────────────────────────────────────┘

STAGE 4: 1800 req/sec — Add read replicas
┌──────────────────────────────────────────────────────────┐
│  App Server                                              │
│     │ writes (20%)          reads (80%)                 │
│     ▼                           ▼                        │
│  UserDB (Master)  ──replicate──► UserDB (Slave 1)        │
│                               ──► UserDB (Slave 2)       │
│                                  1000 req/sec each       │
└──────────────────────────────────────────────────────────┘

STAGE 5: 2000 req/sec — Add partitioning
┌──────────────────────────────────────────────────────────┐
│  UserDB (still on one server, logically partitioned)     │
│  ├── users_partition_1    (IDs 1 – 1M)                  │
│  ├── users_partition_2    (IDs 1M – 2M)                 │
│  └── users_partition_3    (IDs 2M – 3M)                 │
│  Query for user 1.4M → only scans partition_2            │
└──────────────────────────────────────────────────────────┘

STAGE 6: 2500 req/sec — Full sharded cluster
┌──────────────────────────────────────────────────────────────────────┐
│  App Server                                                          │
│       │                                                              │
│       ▼                                                              │
│  Routing Layer: hash(user_id) % 3                                    │
│       │                                                              │
│  ┌────┴────────────────────────────┐                                 │
│  ▼            ▼                   ▼                                  │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐                              │
│ │ Shard 1  │ │ Shard 2  │ │ Shard 3  │  each: independent server    │
│ │users 0-33│ │users34-66│ │users67-99│  with own storage + replicas │
│ └──────────┘ └──────────┘ └──────────┘                              │
└──────────────────────────────────────────────────────────────────────┘

STAGE 7: 5000 req/sec — Scale shards + add replicas per shard
  Add shard 4, 5, 6 + read replicas per shard + CDN/cache layer
```

---

# PAGE 13 — Sequence View: Read Path with Cache + Replica

```
Client       App Server     Redis Cache     DB Replica     DB Primary
  │               │               │               │               │
  │─GET /user/42─►│               │               │               │
  │               │─GET user:42──►│               │               │
  │               │◄──HIT {..}────┤               │               │
  │◄──200 {user}──│               │               │               │
  │  (< 1 ms)     │               │               │               │


── CACHE MISS ──────────────────────────────────────────────────────────

  │─GET /user/42─►│               │               │               │
  │               │─GET user:42──►│               │               │
  │               │◄──MISS (nil)──┤               │               │
  │               │               │               │               │
  │               │──SELECT * FROM users──────────►│               │
  │               │◄──{user data}─────────────────┤               │
  │               │               │               │               │
  │               │─SET user:42 {..} EX 300───────►               │
  │◄──200 {user}──│               │               │               │
  │  (~ 30 ms)    │               │               │               │


── WRITE PATH ──────────────────────────────────────────────────────────

  │─POST /user────►│               │               │               │
  │               │──INSERT INTO users────────────────────────────►│
  │               │◄──OK──────────────────────────────────────────┤
  │               │                                               │
  │               │──replicate────────────────────►│               │
  │               │  (async, ~10ms lag)            │               │
  │               │─DEL user:42───────────────────►│               │
  │◄──201 Created─┤               │               │               │
```

---

# PAGE 14 — Capacity Estimation Framework

```
GIVEN (typical interview numbers):
  Users:           50 million
  Reads/day:       1 billion  → 11,574 req/sec avg, ~50K peak
  Writes/day:      200 million → 2,315 req/sec avg, ~10K peak
  Read:Write ratio = 80:20

INDEXING DECISION:
  Table size: 50M rows × 500 bytes = 25 GB
  B-Tree index on email: ~2 GB additional
  Write overhead: index updated on every INSERT/UPDATE → +5% write latency
  Read benefit: O(log N) ≈ 26 comparisons for 50M rows vs 50M full scan

REPLICATION DECISION:
  11,574 read req/sec
  Single MySQL replica: ~5,000 SELECT/sec
  Replicas needed: 11,574 / 5,000 = ~3 replicas (with headroom → 5)
  Each replica stores full 25 GB copy (25 GB × 5 = 125 GB total replica storage)

CACHING IMPACT:
  Assume 20% of users are "hot" (read repeatedly): 10M users
  Cache working set: 10M × 500 bytes = 5 GB  → fits in Redis
  Cache hit rate 90% → only 1,157 req/sec reach the DB
  DB load reduced: 11,574 → 1,157 req/sec (10× reduction)

PARTITIONING DECISION:
  orders table: 1B rows, growing 3M/day
  Partition by month: each partition ~90M rows (30 days × 3M/day)
  Query "last 30 days" → only scans current month partition
  Archival: DROP PARTITION orders_2023_01 → instant, no DELETE overhead

SHARDING DECISION:
  When does one node fail?
  Storage: 1B rows × 500 bytes = 500 GB → fine on modern hardware
  Writes: 2,315/sec → fine for a well-tuned Postgres primary
  Shard trigger: write throughput >20K/sec OR data >2 TB on one node
  Shard count: start with 4 shards (N = power of 2 for easy resharding)
```

---

# PAGE 15 — Database Selection Framework (from blog)

```
Before choosing ANY optimization technique, choose the right database.

STEP 1 — DATA SHAPE:
  Rows and columns, fixed schema?              → SQL (Postgres, MySQL)
  Nested JSON, variable schema?               → Document (MongoDB, Firestore)
  Simple key → value lookups?                 → Key-Value (Redis, DynamoDB)
  Time-stamped measurements?                  → Time-Series (InfluxDB, TimescaleDB)
  Connected entities, traversal queries?      → Graph (Neo4j, Neptune)
  Full-text search, relevance ranking?        → Search (Elasticsearch, OpenSearch)
  Embedding similarity, semantic search?      → Vector (Pinecone, pgvector)
  Historical aggregations, BI reports?        → OLAP (BigQuery, ClickHouse, Redshift)
  Global transactions + horizontal scale?     → NewSQL (Spanner, CockroachDB)

STEP 2 — ACCESS PATTERN:
  Point lookup by PK?                         → Any SQL or Key-Value
  Range query (date, price)?                  → SQL with index, or Cassandra
  JOIN across entities?                       → SQL
  Graph traversal?                            → Graph DB
  Aggregate SUM/COUNT over huge data?         → OLAP / Warehouse

STEP 3 — CONSISTENCY GUARANTEE:
  Money, orders, inventory?                   → ACID SQL
  Eventual consistency OK (feeds, analytics)? → NoSQL
  Globally consistent transactions?           → NewSQL (Spanner, CockroachDB)

STEP 4 — SCALE & LATENCY:
  <10ms reads, cache-able?                    → Redis in front of any DB
  Write throughput >100K/sec?                 → Cassandra, DynamoDB, or shard SQL
  Multi-region global?                        → NewSQL or per-region replicas

DATABASE CHOICE MAP (from blog):
┌────────────────────────────────┬─────────────────────┬──────────────────────────┐
│ Use Case                       │ Category            │ Engines                  │
├────────────────────────────────┼─────────────────────┼──────────────────────────┤
│ Banking / payments / orders    │ Relational (SQL)    │ PostgreSQL, MySQL, Oracle│
│ Caching / sessions / rate limit│ Key-Value           │ Redis, Memcached         │
│ Product catalog / user profile │ Document            │ MongoDB, Firestore       │
│ Metrics / IoT / monitoring     │ Time-Series         │ InfluxDB, TimescaleDB    │
│ Event logs / write-heavy       │ Wide-Column         │ Cassandra, ScyllaDB      │
│ Social graph / fraud detection │ Graph               │ Neo4j, Neptune           │
│ Full-text search / logs        │ Search              │ Elasticsearch, OpenSearch│
│ AI / RAG / embeddings          │ Vector              │ Pinecone, pgvector       │
│ Global scale + transactions    │ NewSQL              │ Spanner, CockroachDB     │
│ BI dashboards / reporting      │ Warehouse (OLAP)    │ BigQuery, ClickHouse     │
└────────────────────────────────┴─────────────────────┴──────────────────────────┘
```

---

# PAGE 16 — Interview Scripts

## Requirement Clarification Script

```
"Before designing, let me clarify a few things:

  1. What is the current load and what's the target we need to hit?
     (helps decide which techniques are actually needed)
  2. What is the read:write ratio?
     (read-heavy → caching + replicas; write-heavy → sharding)
  3. Is consistency critical or is eventual consistency acceptable?
     (financial data → strong; feeds → eventual)
  4. What is the dominant query pattern?
     (point lookup → index; range by date → partition; full-text → search engine)
  5. Have we profiled the current slow queries?
     (most slowdowns are query problems, not architecture problems)
  6. What's the approximate data size?
     (fits on one machine → no sharding needed yet)"
```

---

## Trade-Off Script

```
"The key trade-offs I see:

  Indexing vs Write Speed:
  Adding an index makes reads O(log N) but every write must update the index.
  For a write-heavy table, too many indexes can slow inserts more than they help reads.

  Replication vs Consistency:
  Async replication gives us read scale but introduces lag.
  If a user updates their profile and immediately reads it from a replica,
  they might see the old value for up to a second.

  Caching vs Freshness:
  Cache dramatically reduces DB load, but stale data is a real risk.
  For product prices or inventory counts, we need short TTLs or write-through invalidation.

  Partitioning vs Cross-Partition Queries:
  Partitioning by month makes monthly reports 100× faster.
  But a query without a partition key (e.g., GROUP BY user_id) still touches all partitions.

  Sharding vs Complexity:
  Sharding solves write scale and storage at the cost of:
  no cross-shard joins, no distributed transactions, complex resharding.
  I will only propose sharding when measurement proves it's needed."
```

---

## Final Recommendation Script

```
"For this system, I recommend the following in order:

  1. Profile current slow queries — EXPLAIN ANALYZE, look for full scans
  2. Add indexes on (emailId), (user_id, created_at) — most gains, lowest cost
  3. Vertical scale the DB instance — immediate relief, no architecture change
  4. Redis cache in front of DB — absorb 80%+ of hot read traffic
  5. Add 2-3 read replicas — distribute remaining read load, provide failover
  6. Partition orders table by month — faster range queries, easy archival
  7. Shard by user_id only if write throughput exceeds ~20K/sec or data > 2TB

  At each step I'll measure the bottleneck before adding the next layer.
  Complexity should only be added when it solves a proven problem."
```

---

# PAGE 17 — Senior Trap Questions

## Q1: "Replicas solve write scalability, right?"

```
WRONG ANSWER: "Yes — more replicas = more write capacity."

CORRECT ANSWER:
  "No. Read replicas copy the same data to multiple nodes.
   ALL writes still go to the primary. Adding replicas does not help write throughput.

   Replicas solve:
   ─ Read scale (SELECT queries distributed across replicas)
   ─ Availability (promote replica if primary fails)
   ─ Analytics isolation (run heavy reports against replica)

   Write scale requires:
   ─ Sharding (different data on different servers)
   ─ Or a distributed DB (Cassandra, CockroachDB)

   Confusing these is the most common mistake in DB scaling interviews."
```

---

## Q2: "What's the difference between partitioning and sharding?"

```
WEAK ANSWER: "They're basically the same thing — splitting data."

STRONG ANSWER:
  "Partitioning: one logical table split into smaller pieces, same DB server.
   Example: orders_2026_01, orders_2026_02 — all on one Postgres instance.
   Query pruning: WHERE month=3 only scans orders_2026_03.

   Sharding: different subsets on DIFFERENT DB servers.
   Example: hash(user_id) % 3 → user goes to shard 1, 2, or 3.
   Each shard is an independent DB server with its own CPU and storage.

   Sharding = distributed horizontal partitioning.
   Partitioning does NOT imply multiple servers.

   You can partition within each shard (partition + shard together)."
```

---

## Q3: "Why not add an index on every column?"

```
WEAK ANSWER: "Indexes always make things faster."

STRONG ANSWER:
  "Every index has two costs:
   1. Storage: each index is a B-Tree copy of that column's values + row pointers
   2. Write amplification: every INSERT/UPDATE/DELETE must update ALL indexes

   On a write-heavy table with 10 indexes, each INSERT maintains 10 B-Trees.
   This can slow writes 3-5×.

   Also:
   ─ Low-cardinality indexes (status, gender) are useless — they still scan 50% of rows
   ─ Unused indexes consume space and slow writes with zero read benefit

   Rule: only index columns actually used in WHERE, JOIN, or ORDER BY.
   Profile first: `EXPLAIN ANALYZE` shows which indexes are actually used."
```

---

## Q4: "How do you choose a shard key?"

```
WEAK ANSWER: "Use something that distributes data evenly."

STRONG ANSWER:
  "Even distribution is necessary but not sufficient.
   The shard key must also route common queries to a single shard.

   Good shard key criteria:
   ✓ Even distribution: hash(user_id) → all shards roughly equal
   ✓ Query locality: most queries filter BY the shard key → one-shard lookup
   ✓ No hot keys: no single user/tenant generating 80% of traffic

   BAD shard keys:
   ✗ created_at: all new writes hit the 'latest' shard (time hot-spot)
   ✗ status:     all 'active' rows on one shard (low-cardinality skew)
   ✗ country:    India has 10× traffic of other shards (geographic skew)

   Real choice:
   ─ User-facing app: hash(user_id) → even, query by user → one shard
   ─ SaaS: tenant_id → tenant isolation, predictable per-tenant query routing
   ─ E-commerce: hash(order_id) → even distribution, most queries by order ID"
```

---

## Q5: "When would you choose eventual consistency over strong consistency?"

```
STRONG ANSWER:
  "CAP theorem: during a network partition, choose Consistency or Availability.

   Strong consistency (choose C):
   ─ Bank balance, payment processing, inventory during checkout
   ─ Two users cannot both read $100 and spend it simultaneously
   ─ Use: Postgres with synchronous replication, or NewSQL like CockroachDB

   Eventual consistency (choose A):
   ─ Social media feeds, recommendation scores, analytics counts
   ─ If a user's follower count shows 1,234 instead of 1,235 for 1 second — acceptable
   ─ Use: Cassandra, DynamoDB with eventual consistency mode

   Real systems use both:
   ─ Payments DB: PostgreSQL, strong ACID
   ─ Activity feed: Cassandra, eventual
   ─ Search: Elasticsearch, eventual (indexed async from primary DB)"
```

---

# PAGE 18 — What NOT to Say

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  TRAP PHRASE                     │  WHY IT'S WRONG                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Add more replicas to handle     │ Replicas copy same data — writes still  ║
║  write load"                     │ go to primary. Replicas help READS.     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Partition and sharding are      │ Partitioning = same server, logical     ║
║  the same thing"                 │ split. Sharding = different servers,    ║
║                                  │ physical split. Completely different.   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Index every column for speed"   │ Indexes slow writes and waste storage.  ║
║                                  │ Only index WHERE/JOIN/ORDER BY columns. ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Let's just shard from day one"  │ Sharding adds massive complexity.       ║
║                                  │ Only shard when measurement proves it.  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Cache solves everything"        │ Cache introduces stale data.            ║
║                                  │ Financial/inventory data can't be stale.║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "It depends" with no follow-up   │ Always give conditions:                 ║
║                                  │ IF read-heavy → replicas.               ║
║                                  │ IF write-heavy → sharding.              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Replication gives strong        │ Async replication has lag.              ║
║  consistency"                    │ User might read stale data from replica.║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Use MongoDB for everything"     │ Document DBs lack strong multi-document ║
║                                  │ transactions. Use SQL for financial data.║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

# PAGE 19 — Key Numbers to Memorize

```
┌──────────────────────────────────────────────────────────────────────┐
│  Single Postgres read (cached, PK lookup)    ~1 ms                   │
│  Single Postgres read (disk, indexed)        ~5–10 ms                │
│  Single Postgres read (full table scan)      seconds at 100M rows    │
│  Redis GET latency (in-memory)               < 1 ms                  │
│  B-Tree comparisons for 50M rows             log2(50M) ≈ 26 hops     │
│  Postgres primary: max write throughput      ~5K–20K writes/sec      │
│  Postgres replica: max read throughput       ~5K–10K reads/sec       │
│  Replication lag (async)                     10ms – 1 sec            │
│  Typical cache hit rate target               90%+                    │
│  Index write overhead                        +5–20% per index        │
│  Sharding trigger (rule of thumb)            >20K writes/sec         │
│                                              OR >2 TB data           │
│  Partition by month: query speedup           10–100× for date ranges │
│  Connection pool size (HikariCP default)     10 connections          │
└──────────────────────────────────────────────────────────────────────┘
```

---

# PAGE 20 — Whiteboard Draw Order

```
Step 1 — Draw the problem (30 sec)
  Single App Server → Single DB
  "At 100 req/sec this works. At 5000 req/sec, what breaks?"

Step 2 — Draw the 6-step escalation ladder (60 sec)
  Write on whiteboard:
  1. Query Opt  2. Index  3. Vertical  4. Cache  5. Replicate  6. Partition  7. Shard

Step 3 — Draw the B-Tree (45 sec)
  Root → Index Nodes → Leaf Nodes (show ranges: 1-500, 501-1000)
  "emailId lookup: 4 hops instead of 100M row scan"

Step 4 — Draw Replication (30 sec)
  Primary → Replica 1, Replica 2
  "Writes → primary. Reads → round-robin across replicas."

Step 5 — Draw Partitioning (20 sec)
  orders → [1M] [1M-2M] [2M-3M]
  "Query for March → only reads March partition"

Step 6 — Draw Sharding (30 sec)
  Routing Layer → Shard 1 | Shard 2 | Shard 3
  "hash(user_id) % 3 → different physical servers"

Step 7 — Call out the trade-offs (20 sec)
  "Replicas: read scale only. Partitioning: same server. Sharding: most complex."
```

---

# PAGE 21 — How to Adapt for Any Company

## Fintech (Stripe, Razorpay, Brex)
```
─ Strong ACID required: PostgreSQL or NewSQL (CockroachDB for global)
─ No caching of balances/inventory (stale = fraud/compliance risk)
─ Partition transactions by month (billions of rows, archival critical)
─ Shard by account_id or tenant_id (predictable routing)
─ Synchronous replication (no lag acceptable for financial data)
─ Key concern: "What is the consistency guarantee? Can we over-charge a user?"
```

## E-Commerce (Amazon, Flipkart, Shopify)
```
─ Products: MongoDB or PostgreSQL (flexible catalog schema)
─ Orders/Payments: PostgreSQL (ACID mandatory)
─ Product pages: heavy Redis caching (80%+ hit rate target)
─ Inventory during checkout: no cache, direct DB read (oversell risk)
─ Orders table: partition by created_at month
─ Shard by user_id for user tables
─ Key concern: "Don't oversell. Cache everything except checkout inventory."
```

## Social Platform (Twitter, Instagram, LinkedIn)
```
─ User profiles: PostgreSQL
─ Activity feeds: Cassandra (high write throughput, append-only, time-ordered)
─ Follower counts: Redis INCR (approximate, eventually consistent)
─ Media: object storage (S3), DB stores only URL pointer
─ Search: Elasticsearch
─ Key concern: "Feed reads are 1000× more common than writes. Optimize reads."
```

## SaaS (Salesforce, HubSpot)
```
─ Shard by tenant_id (each customer on their own logical shard)
─ Per-tenant query isolation (tenant A can't see tenant B's data)
─ Partition by created_at within each tenant
─ Index on (tenant_id, entity_id) composite — always filter by tenant first
─ Key concern: "Noisy tenant isolation. One tenant's heavy query shouldn't hit others."
```

---

# PAGE 22 — Common Follow-Up Questions

```
Q: What is the N+1 problem and how do you fix it?
A: Fetch 100 orders (1 query), then for each order fetch the user (100 queries) = 101 queries.
   Fix 1: JOIN — SELECT orders.*, users.name FROM orders JOIN users ON orders.user_id = users.id
   Fix 2: Batch fetch — SELECT * FROM users WHERE id IN (list of 100 user IDs)
   Fix 3: Eager loading in ORM — Hibernate: @ManyToOne(fetch = EAGER), or .include(:user) in Rails

Q: What happens if a shard goes down?
A: Other shards continue serving their users — partial availability.
   That shard's users get errors until it recovers.
   Mitigation: each shard has its own primary + replica (replica can serve reads during primary outage).

Q: How do you handle global uniqueness with sharding?
A: Auto-increment IDs from different shards will collide (shard 1 generates ID=5, shard 2 also generates ID=5).
   Fix: UUID (globally unique by design) OR Snowflake ID (timestamp + workerID + sequence).
   Never use simple auto-increment across shards.

Q: What is a hot partition and how do you fix it?
A: One partition receives disproportionate traffic.
   Example: partition by year → all 2026 writes hit the "2026" partition.
   Fix: add a hash component — partition by HASH(user_id) % 4 instead of by date.
   Or: use composite key (region + month) to spread load.

Q: What is connection pooling and why does it matter?
A: Opening a new DB connection costs ~10ms (TCP handshake + auth).
   With 500 threads each opening connections → 5000ms wasted overhead + DB overwhelmed.
   Connection pool (HikariCP): maintain 50 reusable connections shared by 500 threads.
   DB config: max_connections = 200 (Postgres default) → pool must not exceed this.

Q: When would you use Cassandra over PostgreSQL?
A: Cassandra when: write throughput >100K/sec, no complex joins needed, eventual
   consistency OK, data is naturally key-based (user_id → activity events).
   PostgreSQL when: ACID transactions required, complex joins, strong consistency,
   relational data model.
   Example: user profile → Postgres. user activity log → Cassandra.
```

---

# PAGE 23 — Final Quick-Revision Cheat Sheet

```
╔══════════════════════════════════════════════════════════════════════════════╗
║       DATABASE OPTIMIZATION — ONE-PAGE CHEAT SHEET                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  6-TECHNIQUE ESCALATION LADDER (apply in order):                            ║
║  1. Query Opt  → EXPLAIN ANALYZE, fix N+1, add missing WHERE index          ║
║  2. Indexing   → B-Tree on WHERE/JOIN/ORDER BY columns                      ║
║  3. Vertical   → bigger CPU/RAM/SSD, no architecture change                 ║
║  4. Caching    → Redis for hot reads, 90%+ hit rate target                  ║
║  5. Replication → read replicas, writes still → primary                     ║
║  6. Partitioning → logical split same server, range/list/hash               ║
║  7. Sharding   → different data on different servers, last resort           ║
║                                                                              ║
║  KEY DISTINCTIONS:                                                           ║
║  Replication  = same data, different nodes → READ scale + HA                ║
║  Partitioning = logical split, same server → large table management         ║
║  Sharding     = different data, different servers → WRITE scale + storage   ║
║                                                                              ║
║  INDEX RULE:                                                                 ║
║  B-Tree → O(log N). Only index WHERE/JOIN/ORDER BY. Never low-cardinality.  ║
║  Index write cost: every INSERT/UPDATE must update the B-Tree.              ║
║                                                                              ║
║  SHARD KEY RULE:                                                             ║
║  Must: distribute evenly + route common queries to one shard                ║
║  Avoid: created_at (time hot-spot), status (low cardinality)                ║
║  Good:  hash(user_id), tenant_id, region                                    ║
║                                                                              ║
║  REPLICATION LAG:                                                            ║
║  Async replication → 10ms–1sec lag. Read-your-own-writes: route user's      ║
║  own read to primary for 1 sec after write.                                 ║
║                                                                              ║
║  CACHE INVALIDATION:                                                         ║
║  Write-through: update DB + cache together                                  ║
║  Cache-aside: app reads cache; on miss reads DB + populates cache           ║
║  TTL: let stale entries expire naturally (ok for non-critical data)         ║
║                                                                              ║
║  KEY NUMBERS:                                                                ║
║  Redis < 1ms | DB indexed read 5-10ms | Shard at >20K writes/sec           ║
║  Replica: read scale only | B-Tree depth: log2(50M) ≈ 26 hops              ║
║                                                                              ║
║  INTERVIEW LINE:                                                             ║
║  "I follow the escalation ladder: query opt → index → vertical →            ║
║   cache → replicate → partition → shard. Each solves one specific           ║
║   bottleneck. I only add complexity when measurement proves it's needed."   ║
╚══════════════════════════════════════════════════════════════════════════════╝
```
