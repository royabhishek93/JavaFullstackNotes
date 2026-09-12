# MVCC: How PostgreSQL Reads Never Block Writes
### The invisible versioning system that makes your database handle 10,000 concurrent connections without locking up

---

## PART 1 — THE STUDENT CONVERSATION

Open Google Docs. Start reading a long document. Now ask a friend to start editing it at the same time. You don't see a "Document locked — someone is editing" error. You don't see their half-finished sentence appear and disappear as they type. You see the document as it was when you opened it. Clean, consistent, complete.

Their edits appear on your next refresh. You were reading a **snapshot** of the document — a consistent point-in-time view — not the live data.

That's MVCC: **Multi-Version Concurrency Control**. PostgreSQL does this for your database rows, automatically, invisibly, on every single read.

Without MVCC, this is what would happen: you start reading 10,000 rows from the `orders` table for a report. Halfway through your scan, another transaction tries to update one of those rows. It has to wait — it can't touch a row you're currently reading. Your 10-second report is now holding up every write that touches orders for 10 seconds.

This is what traditional locking looks like:

```
Reader holds shared lock on table
  → Writer waits for reader to finish
  → More readers pile up
  → Writer is now blocked for seconds
  → Queue builds up
  → Connection pool exhausts
  → Service falls over
```

PostgreSQL uses MVCC instead. When a write happens, PostgreSQL doesn't modify the row in place. It creates a **new version** of the row and marks the old version as superseded. Readers that started before the write still see the old version. Writers and new readers see the new version. Nobody waits for anybody.

This is the insight that matters for your interviews: **in PostgreSQL, reads never block writes, and writes never block reads.** The only time writes block writes is when two transactions try to modify the exact same row simultaneously — which is fundamentally unavoidable in any database.

---

## PART 2 — DIAGRAMS: ROW VERSIONS, SNAPSHOTS, AND VACUUM

### Row Versions: xmin and xmax

Every PostgreSQL row has two hidden system columns:
- `xmin`: the Transaction ID (XID) of the transaction that **created** this row version
- `xmax`: the XID of the transaction that **deleted or updated** this row version (0 = still alive)

```
Initial state: row inserted by transaction 100
  ┌────────────────────────────────────────┐
  │ xmin=100 │ xmax=0 │ name="Alice" │... │  ← visible to txns >= 100
  └────────────────────────────────────────┘
  (xmax=0 means "not deleted yet")

Transaction 200 updates the row (changes name to "Alicia"):
  ┌────────────────────────────────────────┐
  │ xmin=100 │ xmax=200 │ name="Alice" │  │  ← OLD version, dead to txns >= 200
  └────────────────────────────────────────┘
  ┌────────────────────────────────────────┐
  │ xmin=200 │ xmax=0   │ name="Alicia"│  │  ← NEW version, alive
  └────────────────────────────────────────┘

Transaction 150 reads the row (started BEFORE txn 200 committed):
  → Snapshot says: "I see all committed transactions with XID < 200"
  → Old version: xmin=100 (committed, visible), xmax=200 (NOT committed yet at snapshot time)
  → OLD version is visible to transaction 150
  → Transaction 150 reads "Alice"

Transaction 250 reads the row (started AFTER txn 200 committed):
  → Snapshot says: "I see all committed transactions with XID <= 200"
  → New version: xmin=200 (committed, visible), xmax=0 (still alive)
  → Transaction 250 reads "Alicia"
```

Both transactions got consistent, correct data. Neither blocked the other.

### Snapshot Isolation

```
Timeline:
────────────────────────────────────────────────────────────▶ time
   t=0     t=1     t=2     t=3     t=4     t=5     t=6
    │       │       │       │       │       │       │
  Txn A   Write   Write   Txn B   Txn A   Txn B   Txn A
  starts  row X   row Y   starts  reads   reads   commits
  (READ   (xid=   (xid=   (READ   row X   row X
  COMMIT  101)    102)    COMMIT
  level)                  level)

Txn A snapshot: committed XIDs at t=0 → {1..100}
  → Reads at t=4: row X has xmin=101 → NOT in Txn A's snapshot → sees old value

Txn B snapshot: committed XIDs at t=3 → {1..101, 102 if committed}
  → Reads at t=5: row X has xmin=101 → IN Txn B's snapshot → sees new value

No blocking. No waiting. Consistent snapshots.
```

### The VACUUM Process: Cleaning Up Dead Rows

```
After many updates to a row:
  ┌──────────────────────────────────┐
  │ xmin=50  │ xmax=100 │ "v1" │... │  ← dead (no active txn can see this)
  ├──────────────────────────────────┤
  │ xmin=100 │ xmax=200 │ "v2" │... │  ← dead
  ├──────────────────────────────────┤
  │ xmin=200 │ xmax=300 │ "v3" │... │  ← dead
  ├──────────────────────────────────┤
  │ xmin=300 │ xmax=0   │ "v4" │... │  ← LIVE (current version)
  └──────────────────────────────────┘

Table on disk is growing even though it has 1 logical row.
This is called "table bloat".

VACUUM runs, finds dead row versions, marks their space as reusable:
  ┌──────────────────────────────────┐
  │ (free space)                     │  ← was "v1"
  ├──────────────────────────────────┤
  │ (free space)                     │  ← was "v2"
  ├──────────────────────────────────┤
  │ (free space)                     │  ← was "v3"
  ├──────────────────────────────────┤
  │ xmin=300 │ xmax=0   │ "v4" │... │  ← LIVE
  └──────────────────────────────────┘

VACUUM does NOT return space to OS (table file stays same size).
VACUUM FULL does, but it locks the table — use sparingly.
Free space is reused for new inserts/updates.
```

---

## PART 3 — IMPLEMENTATION DETAILS AND INTERNALS

### Transaction IDs and the XID Wraparound Problem

PostgreSQL uses a 32-bit counter for transaction IDs. That's ~4.2 billion values. In a busy system doing 1,000 transactions per second, that wraps around every 49 days.

PostgreSQL uses **modular arithmetic** for XIDs. Transaction 1 and transaction 4,294,967,297 are considered the same. This means a row inserted by transaction 50 could look "in the future" relative to a current transaction after wraparound — PostgreSQL would think the row doesn't exist yet. This is a **catastrophic data loss bug** if not managed.

The defense: VACUUM must run regularly enough to freeze old XIDs before they become dangerous.

```sql
-- Check how close you are to wraparound (alert if > 150M)
SELECT datname, age(datfrozenxid) AS xid_age
FROM pg_database
ORDER BY xid_age DESC;

-- Alert threshold: age > 150,000,000  (150M)
-- Hard limit:      age > 2,000,000,000 (2B) → PostgreSQL enters read-only mode
--                                             and refuses all writes until VACUUMed
```

AUTOVACUUM handles this automatically, but if it falls behind (very heavy write load, large tables), you can get into trouble. Monitor XID age in production.

### AUTOVACUUM Tuning

AUTOVACUUM is a background daemon that runs VACUUM automatically. Default settings are conservative — tuned for small deployments.

```
# postgresql.conf — production tuning for write-heavy systems
autovacuum_vacuum_scale_factor = 0.01   # vacuum when 1% of rows are dead (default 20%)
autovacuum_analyze_scale_factor = 0.005 # analyze when 0.5% of rows changed
autovacuum_vacuum_cost_delay = 2ms      # less IO throttling (default 20ms)
autovacuum_max_workers = 6              # more parallel workers (default 3)
autovacuum_naptime = 15s                # check more often (default 1min)
```

Per-table overrides (for high-churn tables like `sessions` or `events`):
```sql
ALTER TABLE sessions SET (
  autovacuum_vacuum_scale_factor = 0.01,
  autovacuum_vacuum_cost_delay = 2
);
```

### Index Bloat

Dead row versions accumulate in B-tree indexes too. The index entry for a dead row version points to freed heap space but the index entry itself isn't removed by VACUUM — only by VACUUM (which does clean index entries) but the pages aren't reclaimed in indexes.

```sql
-- Check index bloat
SELECT schemaname, tablename, indexname,
       pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;

-- Rebuild a bloated index without locking (PostgreSQL 12+)
REINDEX INDEX CONCURRENTLY idx_orders_user_id;
```

### MVCC Isolation Levels and What Each Prevents

```
ISOLATION LEVEL          │ Dirty Reads │ Non-Repeatable Reads │ Phantom Reads │ Write Skew
─────────────────────────┼─────────────┼─────────────────────┼───────────────┼───────────
READ COMMITTED (default) │   Blocked   │       Possible       │   Possible    │  Possible
REPEATABLE READ          │   Blocked   │       Blocked        │ Blocked (PG)  │  Possible
SERIALIZABLE             │   Blocked   │       Blocked        │   Blocked     │  Blocked
```

**READ COMMITTED** (PostgreSQL default): Each statement in a transaction gets a fresh snapshot. This means within one transaction, two identical SELECT statements may return different results if another transaction committed between them. This is a non-repeatable read, and it's allowed.

**REPEATABLE READ**: The transaction gets one snapshot at start time. All reads within the transaction see the same data. Non-repeatable reads are impossible. PostgreSQL also blocks phantom reads at this level (unlike SQL standard which allows them).

**SERIALIZABLE**: Full serialization. PostgreSQL uses SSI (Serializable Snapshot Isolation) — it tracks read/write dependencies between transactions and aborts transactions that would cause a serialization anomaly. Slowest but safest.

### Write Skew — The Tricky One

Write skew is not prevented by MVCC alone. It requires SERIALIZABLE isolation.

```
Example: Doctor on-call system
  Invariant: at least 1 doctor must be on-call at all times.
  Currently: Doctor A on-call, Doctor B on-call.

  Transaction 1: Doctor A checks "are there other doctors on-call?"
    → Sees Doctor B. Proceeds to set A's status to off-call.

  Transaction 2: Doctor B checks "are there other doctors on-call?"
    → Sees Doctor A. Proceeds to set B's status to off-call.

  Both transactions read disjoint rows and wrote disjoint rows.
  No conflict detected by MVCC.
  Both commit successfully.
  Result: ZERO doctors on-call. Invariant violated.

Fix: Use SERIALIZABLE isolation level.
  PostgreSQL's SSI detects the read-write dependency cycle
  and aborts one of the transactions with:
    ERROR: could not serialize access due to read/write dependencies
  Caller retries. At least 1 doctor stays on-call.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your PostgreSQL is handling 10,000 concurrent reads and 1,000 writes per second. A junior dev says reads will block during heavy writes. Is that true? Explain what actually happens."

**You (architect answer):**

> "That's incorrect, and it's a common misconception about traditional database locking. PostgreSQL uses MVCC — Multi-Version Concurrency Control — so reads and writes operate on different versions of the data and don't block each other.
>
> Here's what actually happens. When a transaction writes a row, PostgreSQL doesn't modify the row in place. It creates a new version of the row and marks the old version as superseded using a system column called xmax — set to the writing transaction's ID. Readers that started their transaction before the write still have a snapshot that doesn't include the new version. They keep reading the old version as if the write never happened. The writer and the old readers are completely isolated.
>
> So at 10,000 concurrent reads and 1,000 writes per second, the reads are not waiting for the writes to finish. They're reading consistent snapshots of the table. The only things that do block in PostgreSQL: a writer blocks another writer on the same row (unavoidable — can't write the same row twice simultaneously), and DDL operations like ALTER TABLE take AccessExclusiveLock which does block reads. That's the one to watch out for in production — always use tools like pg_repack or CONCURRENTLY variants for schema migrations.
>
> The downside of MVCC is table bloat. Those old row versions accumulate on disk. AUTOVACUUM runs in the background to mark them as free space, but if your write load outpaces AUTOVACUUM, the table grows indefinitely. The other critical issue is XID wraparound — PostgreSQL's transaction ID counter is 32-bit, so it wraps around every ~4 billion transactions. If AUTOVACUUM doesn't freeze old XIDs in time, PostgreSQL enters a read-only panic mode. In production I monitor both table bloat and XID age, alerting when XID age exceeds 150 million."

---

## PART 5 — MVCC HELPS VS HURTS — AND WHEN TO USE SERIALIZABLE

### When MVCC Helps You

| Scenario | MVCC Benefit |
|----------|-------------|
| Long-running reports on live data | Report sees consistent snapshot; writes don't slow it down |
| High-concurrency API (10K+ QPS) | Reads never queue behind writes |
| Price updates with concurrent catalog reads | Thousands of catalog reads see consistent prices while one write changes them |
| Analytics queries on OLTP database | No lock contention with transactional writes |

### When MVCC Hurts You (Bloat and Vacuum Issues)

| Scenario | Problem | Fix |
|----------|---------|-----|
| High-churn table (sessions, events, queue) | Dead row versions accumulate faster than AUTOVACUUM clears them | Tune autovacuum per-table; reduce scale_factor |
| Long-running transaction (hours) | AUTOVACUUM can't clean rows visible to that transaction | Avoid long idle transactions; set `idle_in_transaction_session_timeout` |
| Bulk UPDATE/DELETE on large table | Millions of dead rows created at once | Manual VACUUM after bulk operation |
| Forgotten idle transaction | Holds back VACUUM for entire DB | Monitor `pg_stat_activity` for `idle in transaction` |

### Isolation Level Decision Table

```
REQUIREMENT                                     → USE
─────────────────────────────────────────────────────────────────────
Maximum throughput, slight stale reads OK        READ COMMITTED (default)
Report must see consistent data throughout       REPEATABLE READ
Financial transaction with invariant             SERIALIZABLE
Seat booking (no double-booking allowed)         SERIALIZABLE
Inventory deduction (no oversell)                SERIALIZABLE + advisory lock
Avoid write skew (doctor on-call example)        SERIALIZABLE
```

### VACUUM Tuning Checklist

```sql
-- 1. Check bloat
SELECT schemaname, tablename,
       n_dead_tup, n_live_tup,
       round(n_dead_tup::numeric / nullif(n_live_tup,0) * 100, 2) AS dead_pct,
       last_autovacuum
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 20;

-- 2. Check XID age (alert > 150M)
SELECT datname, age(datfrozenxid)
FROM pg_database ORDER BY age DESC;

-- 3. Check for idle transactions blocking VACUUM
SELECT pid, state, query_start, query
FROM pg_stat_activity
WHERE state = 'idle in transaction'
  AND query_start < now() - interval '5 minutes';

-- 4. Manual vacuum a bloated table (online, no lock)
VACUUM (VERBOSE, ANALYZE) orders;

-- 5. Rebuild bloated index (online, no lock)
REINDEX INDEX CONCURRENTLY idx_orders_user_id;
```

---

## QUICK REFERENCE CARD

```
MVCC CORE MECHANICS:
  xmin = transaction that CREATED this row version
  xmax = transaction that DELETED/UPDATED this row version (0 = live)
  Snapshot = set of committed XIDs visible to this transaction
  Visibility rule: row visible if xmin committed AND (xmax=0 OR xmax not yet committed)

ISOLATION LEVELS:
  READ COMMITTED  → snapshot per statement (default, fast, non-repeatable reads OK)
  REPEATABLE READ → snapshot per transaction (no non-repeatable reads)
  SERIALIZABLE    → SSI, full isolation (use for financial txns, seat booking, on-call)

XID WRAPAROUND MONITORING:
  SELECT datname, age(datfrozenxid) FROM pg_database ORDER BY age DESC;
  Alert:  age > 150,000,000
  Critical: age > 200,000,000 (PostgreSQL may freeze DB at 2B)

BLOAT MONITORING:
  SELECT tablename, n_dead_tup, last_autovacuum FROM pg_stat_user_tables;
  Unhealthy: n_dead_tup > n_live_tup

AUTOVACUUM TUNING (high-write tables):
  autovacuum_vacuum_scale_factor = 0.01   # trigger at 1% dead rows
  autovacuum_vacuum_cost_delay = 2ms      # less IO throttling
  autovacuum_max_workers = 6

WRITE SKEW: not blocked by MVCC
  → Use SERIALIZABLE isolation
  → PostgreSQL uses SSI (Serializable Snapshot Isolation)
  → May abort txn with "could not serialize access" — callers must retry

BLOCKING TRUTH:
  Read  vs Read:  NEVER blocks  ✓
  Read  vs Write: NEVER blocks  ✓
  Write vs Write (same row): blocks ✓
  DDL   vs Read:  blocks (use CONCURRENTLY)  ✗
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** MVCC is why PostgreSQL can handle your entire payment service and catalog service on one cluster without reads grinding to a halt during high write bursts — knowing this lets you justify PostgreSQL over NoSQL alternatives in interviews.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **07 — Payment System** | Payment service reads account balance while another transaction is debiting it. MVCC ensures the balance read sees a consistent snapshot — no partial writes, no lock contention between the balance reader and the debit writer. SERIALIZABLE isolation for the debit-credit pair prevents write skew (double-spend). |
| **09 — E-Commerce** | Product catalog: thousands of concurrent reads (Browse, Search, PDP) while price update transactions write. MVCC means catalog reads never wait for price update transactions to complete. The price update is instantly visible to new reads after commit — no cache-invalidation needed for the DB layer. |
| **11 — Ticket Booking** | Seat availability table hit by 50K concurrent reads during a flash sale while booking writes are simultaneously deducting seats. MVCC: zero read-write contention. SERIALIZABLE or SELECT FOR UPDATE on seat rows to prevent two users booking the same seat. |
| **12 — Hotel Booking** | Availability queries (read-heavy, AP) + booking writes (CP). MVCC enables thousands of availability reads to run concurrently with booking writes without blocking. REPEATABLE READ for booking transactions to see consistent inventory throughout the booking flow. |

**Architect's one-liner for the interview:**
*"PostgreSQL's MVCC means reads and writes never block each other — every read sees a consistent snapshot while writes create new row versions in parallel, which is why you can handle 10,000 concurrent users on a single PostgreSQL instance without the read queue grinding to a halt."*
