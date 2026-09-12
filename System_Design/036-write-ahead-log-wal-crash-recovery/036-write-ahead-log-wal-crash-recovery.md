# Write-Ahead Log (WAL)
### How Databases Survive Crashes — And How CDC Reads From the Log

---

## PART 1 — THE STUDENT CONVERSATION

You're doing your taxes. You don't erase your work-in-progress. You keep a scratch pad where you write every number you're about to add before adding it to the final form. If your computer crashes, you can reconstruct exactly where you were from the scratch pad.

That's the Write-Ahead Log — every change is written to the log BEFORE it's written to the actual data file.

**"Write-Ahead" = log first, data page second.**

Here's why this matters: writing to a data file (a random page somewhere on disk) is dangerous. If the machine loses power halfway through writing 900 over the old value of 1000, the page is half-written garbage. You can't tell if it says "900" or "1900" or corrupted bytes. There's no way back.

But the WAL is always appended (sequential writes — fast, safe). And the WAL record contains everything needed to reconstruct the intent: what the old value was, what the new value should be, which transaction it belongs to.

So the database makes a deal with itself: "I will write to the log first, durably, before I call anything a success. The actual data page can be written later, lazily, in the background. If I crash, I'll re-read my log on restart and finish what I started."

This is how every production database (PostgreSQL, MySQL InnoDB, Oracle, SQL Server) guarantees you never lose a committed transaction — even if the power dies at the worst possible moment.

**Bonus:** Debezium and other CDC tools don't add overhead to your database writes. They simply tail the WAL that was already being written for crash recovery. It's reading a log that already exists.

---

## PART 2 — WAL WRITE SEQUENCE AND STRUCTURE

### What Happens Without vs With WAL

```
WITHOUT WAL:
  Transaction: UPDATE accounts SET balance=900 WHERE id=42
  → Write 900 to page 5 in data file
  → CRASH during write
  → Page 5 is half-written (900 partially over 1000)
  → Data is CORRUPT. No way to recover.

WITH WAL:
  Transaction: UPDATE accounts SET balance=900 WHERE id=42
  → STEP 1: Write to WAL: [LSN=1234, txn=567, UPDATE accounts id=42 balance=1000→900]
  → STEP 2: fsync WAL to disk (durable now)
  → RETURN "commit successful" to client
  → STEP 3 (async): Apply change to data page in background (dirty buffer flush)
  → CRASH during Step 3:
      Data page: still has old value (1000)
      WAL: has [LSN=1234, txn=567, UPDATE ... balance=900]
      Recovery: replay WAL from last checkpoint → re-apply → balance=900 ✓
      Data is NEVER corrupt.
```

### PostgreSQL WAL File Structure

```
PostgreSQL WAL file structure:
/var/lib/postgresql/data/pg_wal/
  000000010000000000000001  ← WAL segment (16MB each)
  000000010000000000000002
  000000010000000000000003

WAL record format (simplified):
  LSN (Log Sequence Number): 0/1A23B450   ← position in WAL stream
  Transaction ID: 12345
  Operation: HEAP_UPDATE
  Relation: 16384 (table OID)
  Block: 5
  Offset: 128
  Old tuple: {balance: 1000}
  New tuple: {balance: 900}

Checkpoint: every 5 minutes (default), flushes dirty pages to disk
  → After checkpoint, WAL before checkpoint LSN = safe to delete
  → Recovery: replay from last checkpoint LSN only (not from the beginning)
```

### How Debezium Reads the WAL (CDC)

```
PostgreSQL logical replication slots:
  SELECT pg_create_logical_replication_slot('debezium', 'pgoutput');

Debezium connector reads:
  Poll: "give me WAL changes since LSN 0/1A23B450"
  PostgreSQL: streams WAL records (decoded into INSERT/UPDATE/DELETE events)
  Debezium: converts to Kafka messages

This is why CDC has near-zero overhead — it reads the log that was
already being written for crash recovery. No additional writes needed.
```

### Recovery Flow on Restart

```
PostgreSQL crash → restart sequence:

1. Read pg_control file → find last checkpoint LSN (e.g., 0/1A200000)
2. Open WAL segment containing that LSN
3. Replay forward:
   - COMMIT record found? → Apply all writes from that txn (REDO)
   - No COMMIT record? → Txn was in-flight at crash → rollback (UNDO via before-images)
4. Reach end of WAL → database is in consistent committed state
5. Open for connections

Total recovery time: proportional to WAL since last checkpoint
  → Default checkpoint every 5 min, max_wal_size=1GB
  → Recovery typically < 30 seconds for most workloads
```

---

## PART 3 — PRODUCTION CONFIGURATION AND INTERNALS

### WAL Level Settings

```sql
-- Check current WAL level
SHOW wal_level;

-- WAL levels (set in postgresql.conf):
-- minimal:  Only enough for crash recovery. No replication, no CDC.
-- replica:  Includes info for streaming replication to standbys.
-- logical:  Includes full tuple data for logical decoding (required for Debezium/CDC).

-- For CDC (Debezium):
wal_level = logical
max_replication_slots = 10     -- one per Debezium connector
max_wal_senders = 10           -- concurrent WAL streaming connections
```

### synchronous_commit Settings

```
synchronous_commit = on (default):
  → WAL fsynced to disk BEFORE "commit success" returned to client
  → Durability guaranteed: zero data loss even on power failure
  → ~1-2ms added latency per transaction (fsync cost)
  → USE FOR: payments, financial records, any data you cannot lose

synchronous_commit = off:
  → WAL written to OS buffer, NOT fsynced before returning success
  → Up to ~0.6 seconds of data loss risk (wal_writer_delay = 200ms × 3)
  → 40% faster writes (no fsync blocking)
  → USE FOR: audit logs, analytics events, session data, metrics
  → NEVER USE FOR: money, orders, anything with financial consequence

synchronous_commit = remote_write:
  → Primary waits for standby to receive WAL (not fsync it)
  → Protects against primary disk failure
  → USE FOR: read replicas with high availability requirement
```

### WAL Size Tuning

```
# postgresql.conf
max_wal_size = 1GB       # Max WAL before forcing checkpoint
min_wal_size = 80MB      # Min WAL to keep on disk
checkpoint_timeout = 5min  # Force checkpoint if not triggered by size
checkpoint_completion_target = 0.9  # Spread checkpoint I/O over 90% of interval

# DANGER: Replication slot lag
# If Debezium falls behind (e.g., Kafka outage), PostgreSQL cannot delete
# WAL that the slot hasn't consumed yet.
# → pg_wal directory grows indefinitely
# → Disk full → PostgreSQL crashes

# Monitor:
SELECT slot_name, active, restart_lsn, pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) AS lag_bytes
FROM pg_replication_slots;

# Alert when: lag_bytes > 5GB or pg_wal directory > 10GB
```

### Recovery Performance Numbers

| Scenario | Recovery Time | Notes |
|----------|--------------|-------|
| Checkpoint every 5 min, light load | 5-10 seconds | Typical dev/staging |
| Checkpoint every 5 min, heavy OLTP | 30-60 seconds | Production normal |
| max_wal_size=4GB hit | 2-5 minutes | Checkpoint delayed by large transactions |
| WAL corruption | Manual recovery or replica promotion | pg_wal_replay_pause() for inspection |

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "A PostgreSQL server crashes mid-transaction while writing payment records. When it restarts, what happens? How does the DB know which transactions to keep and which to discard?"

**You (architect answer):**

> "On restart, PostgreSQL enters crash recovery mode. It reads the `pg_control` file to find the LSN of the last completed checkpoint — that's the point where all dirty pages were flushed to disk. It then opens the WAL files starting from that checkpoint LSN and replays them forward.
>
> For every WAL record, PostgreSQL checks: is there a COMMIT record for this transaction ID later in the WAL? If yes, it re-applies all the writes (this is the REDO phase — bringing the data pages up to the state they were in before the crash). If no COMMIT record exists — meaning the transaction was in-flight when the machine died — PostgreSQL uses the 'before' images in the WAL records to roll back any partial work (UNDO phase).
>
> The critical point: a transaction is 'committed' if and only if a COMMIT WAL record was written and fsynced to disk before the crash. The client only receives a success response after that fsync — that's what `synchronous_commit = on` guarantees. So if the client got a 200 OK, the COMMIT WAL record exists, and recovery will re-apply it. If the client never got a success, either the COMMIT wasn't written or wasn't durable, and recovery rolls it back cleanly.
>
> For payment systems specifically, you'd never use `synchronous_commit = off` — the ~0.6 second loss window is unacceptable. Every payment write must fsync before returning success."

---

## PART 5 — DECISION FRAMEWORK

### synchronous_commit: Which Setting to Use

| Data Type | synchronous_commit | Reason |
|-----------|-------------------|--------|
| Payment transactions | `on` | Cannot lose committed payments. fsync is mandatory. |
| Order records | `on` | Order placed = money taken. Must be durable. |
| User sessions | `off` | Session loss = minor inconvenience. 40% write speedup. |
| Analytics events | `off` | Losing a few events is acceptable. High write volume. |
| Audit log entries | `off` | Approximate audit is acceptable; performance matters. |
| File metadata (S3 mappings) | `on` | Losing which S3 key a file maps to = permanent data loss. |

### wal_level: Which Setting to Use

| Use Case | wal_level | Reason |
|----------|-----------|--------|
| Single-node, no CDC, no replication | `minimal` | Smallest WAL, fastest writes |
| Primary with read replicas | `replica` | Required for streaming replication |
| CDC with Debezium | `logical` | Required for logical decoding |
| Multi-datacenter replication | `logical` | Encompasses `replica` + CDC capability |

### WAL-Related Alert Thresholds (Production)

| Metric | Warning | Critical |
|--------|---------|----------|
| pg_wal directory size | 5GB | 10GB |
| Replication slot lag | 1GB | 5GB |
| Recovery time (after crash) | 60s | 5min |
| Checkpoint write time | 200ms | 1s |

---

## QUICK REFERENCE CARD

```
WAL ESSENTIALS
==============
Write-Ahead Log: write to log FIRST, data page SECOND.
LSN = position in WAL stream (monotonically increasing).
Checkpoint = flush all dirty pages; WAL before checkpoint = safe to delete.
Recovery = replay WAL from last checkpoint LSN forward.
COMMIT in WAL = transaction survived crash. No COMMIT = rolled back.

synchronous_commit=on  → fsync before success. Zero loss. Use for money.
synchronous_commit=off → no fsync. 0.6s loss window. Use for analytics.

wal_level=logical      → required for Debezium/CDC.
CDC overhead           → near-zero (reads existing WAL).
Replication slot lag   → monitor pg_wal size. Unbounded growth = disk full crash.

Key commands:
  SELECT pg_current_wal_lsn();           -- current WAL position
  SELECT pg_wal_lsn_diff(a, b);          -- bytes between two LSNs
  SELECT * FROM pg_replication_slots;    -- slot lag monitoring
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** WAL is the reason your database never loses data — it's written to by every transaction, making crash recovery and CDC essentially free.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **07 — Payment System** | WAL is the durability guarantee for payment transactions. Crash mid-debit → WAL recovery restores consistent state. `synchronous_commit=on` is non-negotiable — a payment must never be lost. |
| **09 — E-Commerce Platform** | Order writes use WAL. Debezium reads the WAL to sync new orders into Elasticsearch for search indexing — zero extra DB load for the sync. |
| **10 — Cloud Storage (S3 Clone)** | PostgreSQL WAL for file metadata (which S3 key maps to which filename). `synchronous_commit=on` required — losing this mapping means a file is permanently inaccessible. |
| **15 — Distributed Logging** | Debezium tails application DB WAL → ships change events to Elasticsearch for operational log aggregation without polling. |

**Architect's one-liner for the interview:**
*"WAL writes the change to a log before applying it to data pages — crash recovery replays the log, making committed transactions permanent and incomplete ones disappear."*
