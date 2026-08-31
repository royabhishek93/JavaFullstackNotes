# Database Sharding: Range, Hash, and Consistent Hashing
### How to split 500 million rows across multiple databases without losing your mind

---

## PART 1 — THE STUDENT CONVERSATION

Imagine a library with 10 million books. You have one giant shelf. Finding a book takes forever because you have to scan the whole thing. The shelf starts sagging under the weight.

So you get 10 shelves. Now you split the books across 10 shelves. Immediately, the question is: **which book goes on which shelf?**

Option A: Alphabetical by title. A–D on shelf 1, E–H on shelf 2, etc. Easy to find a book — you know exactly which shelf to check. But all the new bestsellers start with "T" this year — shelf 8 gets crushed while shelf 1 is empty. That's a **hotspot**.

Option B: Scramble the title through a formula and the remainder tells you which shelf. Every shelf gets roughly the same load. But now you can't browse "all books published in 2023" without hitting every shelf.

Option C: Imagine the shelves arranged in a circle. Each book's title hash points to a location on the circle. The book goes to the nearest shelf clockwise. When you add a new shelf, you only have to move the books that were between the new shelf's position and the previous shelf's position. Everything else stays put.

These three approaches — **Range Sharding**, **Hash Sharding**, and **Consistent Hashing** — are exactly what production databases use when a single machine can no longer hold your data.

Sharding is horizontal partitioning. You're not splitting columns (that's vertical partitioning). You're splitting rows across multiple database instances. Each instance owns a subset of the rows. The instances are called **shards**.

The value you shard on — user_id, order_id, etc. — is the **shard key**. Choosing it wrong is the #1 mistake. You can't change it later without migrating the entire dataset.

---

## PART 2 — THREE SHARDING STRATEGIES (DIAGRAMS)

### Strategy 1: Range Sharding

```
Users table — 6 million rows

Shard 1          Shard 2          Shard 3
┌─────────┐      ┌─────────┐      ┌─────────┐
│ ID 1    │      │ ID      │      │ ID      │
│  to     │      │ 2000001 │      │ 4000001 │
│ 2000000 │      │  to     │      │  to     │
│         │      │ 4000000 │      │ 6000000 │
│ 2M rows │      │ 2M rows │      │ 2M rows │
└─────────┘      └─────────┘      └─────────┘

Lookup: user_id = 3,500,000
  → 3,500,000 is in range [2M–4M]
  → Route to Shard 2
  → Single shard hit ✓

Range query: users registered in 2023 (IDs 4,100,000 – 4,900,000)
  → All in Shard 3
  → Single shard hit ✓

Problem: New signups → always Shard 3
┌─────────┐      ┌─────────┐      ┌─────────────┐
│ 2M rows │      │ 2M rows │      │ 2M + ALL NEW │  ← HOT SHARD
│ low QPS │      │ low QPS │      │ high QPS    │
└─────────┘      └─────────┘      └─────────────┘
```

### Strategy 2: Hash Sharding

```
shard_number = hash(user_id) % num_shards

user_id = 1,000,001  →  hash = 849203    →  849203 % 3 = 2  →  Shard 2
user_id = 1,000,002  →  hash = 174920    →  174920 % 3 = 1  →  Shard 1
user_id = 1,000,003  →  hash = 991234    →  991234 % 3 = 0  →  Shard 0
user_id = 1,000,004  →  hash = 654321    →  654321 % 3 = 0  →  Shard 0

Even distribution:
Shard 0    Shard 1    Shard 2
┌──────┐   ┌──────┐   ┌──────┐
│~33%  │   │~33%  │   │~33%  │
│ rows │   │ rows │   │ rows │
└──────┘   └──────┘   └──────┘

No hotspot. But...

Range query: users registered in 2023
  → IDs spread across all shards
  → Must hit ALL 3 shards, merge results in application
  → Scatter-gather = expensive

Resharding: add Shard 3
  → shard = hash(user_id) % 4  (WAS % 3)
  → EVERY row changes shard assignment
  → Must migrate ~75% of all data
  → Painful at 500M rows
```

### Strategy 3: Consistent Hashing Ring

```
Hash space: 0 ─────────────────────────────── 2^32

Visualized as a ring:

                    0
                    │
            ┌───────┴───────┐
            │               │
    2^32*3/4 ─── RING ──── 2^32/4
            │               │
            └───────┬───────┘
                    │
                  2^32/2

Nodes placed at hash(node_name):

              hash("DB-A") = 2^32*0.1
                    ↓
              [DB-A]──────────────[DB-B] ← hash("DB-B") = 2^32*0.4
             /                        \
       [DB-C]                          (ring continues)
        ↑
   hash("DB-C") = 2^32*0.75

Key routing: find hash(key), walk clockwise to nearest node.

key_x hash = 2^32*0.25  →  between DB-A and DB-B  →  goes to DB-B
key_y hash = 2^32*0.55  →  between DB-B and DB-C  →  goes to DB-C
key_z hash = 2^32*0.9   →  between DB-C and DB-A  →  goes to DB-A (wrap)

Adding a new node DB-D at position 2^32*0.6:

BEFORE:         DB-B ──── DB-C   (keys in this arc → DB-C)
AFTER:   DB-B ── DB-D ── DB-C   (keys between DB-B..DB-D → DB-D, rest unchanged)

Only the keys between DB-B and DB-D migrate.
~1/N of data moves, not everything.
```

### Virtual Nodes

```
Problem: with 3 physical nodes, each gets 1/3 of ring.
If DB-A has 2x the RAM of DB-B and DB-C, it still gets 1/3 load.

Solution: virtual nodes (vnodes)
Each physical node gets V positions on the ring.

DB-A (high-end):  [A-v1] [A-v42] [A-v87] ... (150 vnodes)
DB-B (mid):       [B-v1] [B-v23] [B-v69] ... (100 vnodes)
DB-C (low-end):   [C-v1] [C-v11] [C-v55] ... (50 vnodes)

Total 300 positions spread randomly on ring.
DB-A gets ~50% of the arc, DB-B ~33%, DB-C ~17%.
Proportional to capacity. Even if DB-A is in a bad part of the ring,
its 150 vnodes average out to roughly the right load.

Also: when a node dies, its vnodes spread load to MANY nodes,
not dumping everything on one neighbor.
```

---

## PART 3 — IMPLEMENTATION AND INTERNALS

### Choosing a Shard Key — The Four Criteria

A good shard key must satisfy all four:

| Criterion | Why It Matters | Bad Example |
|-----------|---------------|-------------|
| High cardinality | Low cardinality = few shards = poor distribution | `country_code` (only 200 values) |
| Even distribution | Skewed distribution = hotspots | `user_id` for a B2B app where 10 enterprise customers = 90% of data |
| Used in most queries | If your WHERE clause never uses it, you scatter-gather every query | `created_at` as shard key when you always query by `user_id` |
| Immutable | Changing a row's shard key means migrating it to another shard | `email` (can change) |

**Good shard keys:** `user_id` for user data, `account_id` for financial data, `order_id` for orders, `session_id` for sessions.

**Bad shard keys:** `created_at` (range = hotspot + sequential writes all go to one shard), `status` (low cardinality), `region` (only a few values, uneven distribution).

### Resharding: The Data Migration Plan

When you need to add shards (because existing shards are getting full):

```
Phase 1: Dual-write
  - New writes go to both old shard mapping AND new shard mapping
  - Old shards are still authoritative for reads

Phase 2: Backfill
  - Background job migrates rows from old shards to new positions
  - Monitor lag: how many rows still need to move

Phase 3: Read cutover
  - Once backfill is complete (lag = 0), flip reads to new shard mapping
  - Keep dual-write running for safety window (24h)

Phase 4: Stop dual-write
  - Drop old shard mapping
  - Decommission old shards if no longer needed
```

With consistent hashing, only ~1/N of data needs to move when adding 1 shard to N shards. With hash sharding (modulo), you may need to move 75–90% of data.

### Cross-Shard Queries — The JOINs Problem

Sharding breaks relational JOINs. If `users` is on Shard 1 and `orders` is on Shard 3, you cannot do:

```sql
SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id
-- This will NOT work across shards
```

Solutions:

**1. Co-locate related data** — shard both `users` and `orders` by `user_id`. User 123's rows and order 123's rows both land on the same shard. JOIN works locally.

**2. Application-level join** — fetch users from Shard 1, fetch orders from Shard 3, join in application memory. Expensive but sometimes unavoidable.

**3. Denormalization** — embed user name in the orders table. Avoids JOIN entirely. Increases storage, but this is the production pattern for high-scale systems.

**4. Broadcast tables** — tiny reference tables (country codes, product categories) replicated to every shard. JOINs against them always work.

### Real Numbers

- Typical shard size before performance degrades: 100GB–500GB per shard (depends on query patterns)
- Virtual nodes per physical node: 150 (Cassandra default), 64–256 in practice
- Hash ring size: 2^32 (Cassandra) or 2^64 (some systems)
- Consistent hashing used by: Cassandra, DynamoDB, Redis Cluster (modified — 16384 hash slots), Memcached

### Redis Cluster: Consistent Hashing with Slots

Redis Cluster uses 16,384 hash slots (0–16383) instead of a pure ring.

```
HASH_SLOT = CRC16(key) % 16384

3 nodes:
  Node A: slots 0 – 5460
  Node B: slots 5461 – 10922
  Node C: slots 10923 – 16383

key "user:123" → CRC16("user:123") % 16384 = 7638 → Node B

Adding Node D:
  Move some slots from A, B, C to D.
  Only keys in moved slots migrate.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your payments table has 500 million rows and inserts are slowing down. How do you shard it?"

**You (architect answer):**

> "First, I'd confirm the bottleneck. Slow inserts usually mean either the write throughput is exceeding the primary's capacity, or the indexes are getting too large to fit in memory and every insert is doing disk I/O to update them. I'd check `pg_stat_activity` and `pg_stat_bgwriter` to confirm.
>
> Assuming we've confirmed we need sharding, the first decision is the shard key. For a payments table, the natural candidates are `account_id` (the payer), `payment_id`, or a composite. I'd choose `account_id` as the primary shard key for two reasons: most reads are 'show me this account's payment history', which hits a single shard. And most writes come from users actively transacting — even distribution follows user activity distribution, which is roughly even except for merchant accounts.
>
> For the sharding strategy, I'd use consistent hashing. We have ~500M rows today, but we'll grow. With modulo hashing, adding a shard means rehashing 75% of the data — for 500M rows at 1KB each, that's 375GB of migration, touching every shard simultaneously. With consistent hashing, adding a shard moves ~1/N of the data. Manageable.
>
> The hardest problem is cross-shard transactions. If a payment debits account A and credits account B, and those are on different shards, I can't use a single database transaction. I'd use a Saga pattern: debit account A (write to shard A), then credit account B (write to shard B), with a compensating transaction (refund to account A) if the credit fails. This means the payment service needs to be idempotent — if we retry, we don't double-debit.
>
> The migration plan is dual-write: write to both old and new shard layout, backfill old data, then cut reads over once backfill is complete. This keeps the service online during migration. For 500M rows, I'd estimate 2–3 weeks of backfill at safe I/O rates to avoid impacting production."

---

## PART 5 — DECISION FRAMEWORK: WHEN TO USE WHICH

| Criterion | Range Sharding | Hash Sharding | Consistent Hashing |
|-----------|---------------|---------------|-------------------|
| Distribution evenness | Poor (hotspots likely) | Good | Good (better with vnodes) |
| Range query support | Excellent (single shard) | Poor (scatter-gather) | Poor (scatter-gather) |
| Resharding cost | Medium (split a range) | Very High (rehash everything) | Low (~1/N data moves) |
| Implementation complexity | Low | Low | Medium-High |
| Best for | Time-series, append-heavy data with range queries | Fixed-size cluster, even distribution needed | Dynamic clusters, frequent node add/remove |
| Example use case | Log data by date, IoT by timestamp | User sessions (fixed 20 shards) | Cassandra, DynamoDB, Redis Cluster |

### Decision Tree

```
Do you need range queries on the shard key?
├── YES → Range Sharding (accept hotspot risk, mitigate with pre-splitting)
└── NO
    ├── Will the cluster size change frequently (add/remove nodes)?
    │   ├── YES → Consistent Hashing
    │   └── NO (fixed number of shards for years)
    │       └── Hash Sharding (simplest, predictable)
    │
    └── Is write distribution extremely uneven (celebrity accounts, etc)?
        └── YES → Consistent Hashing with vnodes (weighted by capacity)
```

---

## QUICK REFERENCE CARD

```
SHARD KEY RULES:
  ✓ High cardinality (millions of distinct values)
  ✓ Even distribution (no 10 keys = 90% of rows)
  ✓ Immutable (never changes after row creation)
  ✓ Present in most queries (avoid scatter-gather)
  ✗ created_at  (hotspot, sequential writes)
  ✗ status      (low cardinality)
  ✗ email       (mutable)

CONSISTENT HASHING KEY NUMBERS:
  Ring size:       2^32 (Cassandra) | 16,384 slots (Redis Cluster)
  Virtual nodes:   150 per physical node (Cassandra default)
  Data migrated on node add: ~1/N (N = current node count)
  Data migrated on hash reshard: ~(N-1)/N ← avoid this

CROSS-SHARD TRANSACTION PATTERNS:
  Co-location:     shard both tables by same key → local JOIN works
  Saga pattern:    debit Shard A, credit Shard B, compensate on failure
  Denormalization: embed join data → no cross-shard query needed

REDIS CLUSTER FORMULA:
  slot = CRC16(key) % 16384
  hash tags: {user}.orders + {user}.profile → same slot (key in {})

RESHARDING MIGRATION PHASES:
  1. Dual-write (old + new shard layout)
  2. Backfill (background migration)
  3. Read cutover (flip reads to new layout)
  4. Stop dual-write
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Every system at scale eventually outgrows one database — sharding is how you grow horizontally without rewriting your application logic.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **05 — Social Media** | User data sharded by `user_id` (hash). Feed data also by `user_id` so user + feed co-locate. Celebrity posts trigger cross-shard fan-out: one write to all shards where followers live. |
| **07 — Payment System** | Payments table sharded by `account_id` (hash) — most queries are per-account. Cross-shard transfers (debit + credit on different shards) require Saga pattern with compensating transactions. |
| **09 — E-Commerce** | Orders by `user_id`. Product catalog by `category_id`. Sessions by `session_id`. Three independent shard keyspaces — cross-service joins happen at application layer, not DB layer. |
| **13 — Leaderboard** | Redis Cluster uses consistent hashing internally. Each key hashes to slot 0–16383, slots assigned to shards. Leaderboard keys spread across cluster; ZADD/ZRANGE hit a single slot/shard. |
| **19 — Stock Broker** | Trade records use ULID (sequential IDs with timestamp prefix) — natural range shard by time. Today's trades are on the current shard. Historical trades are on older shards, which are cold and cheap to store. |

**Architect's one-liner for the interview:**
*"Sharding is a last resort — exhaust read replicas, caching, and vertical scaling first, because once you shard, JOINs die and every distributed transaction becomes a saga."*
