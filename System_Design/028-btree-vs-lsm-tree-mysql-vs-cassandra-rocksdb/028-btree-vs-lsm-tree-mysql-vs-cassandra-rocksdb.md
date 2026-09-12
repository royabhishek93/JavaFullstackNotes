# B-Tree vs LSM Tree — MySQL vs Cassandra / RocksDB

> **The Question:** "Why does MySQL use B-Tree and Cassandra use LSM Tree?
> How does this affect which database you choose?"

---

## PART 1 — THE STUDENT CONVERSATION
### "Let me explain this like you've never touched a database engine before"

---

**Imagine you are a librarian.**

Your job: store books and help people find them.

You have two options for how you organize the library:

---

### Option A — B-Tree Style (MySQL's approach)

You organize books into a **tree of shelves**. Every shelf is sorted.
The top shelf has the index (A–Z). Each section has sub-shelves.
When someone asks for "Harry Potter", you:
1. Go to the index shelf → find "H"
2. Go to the H-section shelf → find "Ha"
3. Go to the Ha-section → pick up "Harry Potter"

**Finding a book is 3 steps.** Fast.

But when a **new book arrives**:
1. You walk to the right shelf
2. The shelf is full → you split it into two shelves
3. Now you have to re-link the parent shelf to point to both new shelves
4. Sometimes this cascades up — 3, 4, 5 reshuffles for one new book

**Adding books is slow and disruptive** (especially at scale).

---

### Option B — LSM Tree Style (Cassandra's approach)

When a new book arrives, you **never reorganize the existing shelves**.
Instead, you drop it on a table near the door — you call this the **MemTable**.

After 100 books pile up on the table, you bundle them together into a **small sorted package** and place it in the back room. You call this an **SSTable**.

When another 100 books arrive, another package goes to the back room.

Over time you have many packages. Periodically you **merge small packages into larger ones** — this process is called **compaction**. It runs in the background, not during writes.

**Writing a book is 1 step: drop it on the table. Always fast.**

Finding a book is harder — you might have to check the table, then 5 packages. But you optimize this with a **Bloom Filter** (a fast "definitely not here" checker) on each package.

---

## PART 2 — THE DIAGRAMS

### B-Tree Internal Structure (MySQL InnoDB)

```
                         ┌─────────────────┐
                         │   ROOT NODE     │
                         │  [30] [60] [90] │
                         └────────┬────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
   ┌─────────────┐        ┌─────────────┐        ┌─────────────┐
   │ INTERNAL    │        │ INTERNAL    │        │ INTERNAL    │
   │ [10][20][30]│        │ [40][50][60]│        │ [70][80][90]│
   └──────┬──────┘        └──────┬──────┘        └──────┬──────┘
          │                      │                      │
    ┌─────┴──────┐          ┌────┴─────┐          ┌─────┴─────┐
    ▼            ▼          ▼          ▼          ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│LEAF    │ │LEAF    │ │LEAF    │ │LEAF    │ │LEAF    │ │LEAF    │
│10,15,20│→│21,25,30│→│31,40,50│→│51,55,60│→│61,70,80│→│81,85,90│
│(data)  │ │(data)  │ │(data)  │ │(data)  │ │(data)  │ │(data)  │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
     ↑
  Leaf nodes are DOUBLY LINKED
  → range scans are fast (just follow the links)
  → all actual data lives at the leaf level (clustered index)
```

**Key insight:** The tree is ALWAYS balanced. A read is always O(log N) = 3–4 disk reads for millions of rows. But inserting key=25 into a full leaf node triggers a **page split** — the leaf splits into two, parent gets a new pointer, sometimes cascades up.

---

### What a Page Split Looks Like

```
BEFORE INSERT (key=22, leaf is full):

┌──────────────────────┐
│  LEAF: 10, 15, 20, 25 │   ← full, no room for 22
└──────────────────────┘

AFTER INSERT — SPLIT:

      ┌──────────────────────────────────────────┐
      │         PARENT NODE                      │
      │  (now has an extra pointer for key=20)   │
      └──────────────────────────────────────────┘
               /                    \
┌─────────────────┐        ┌─────────────────┐
│  LEAF: 10, 15   │        │  LEAF: 20,22,25  │
└─────────────────┘        └─────────────────┘

→ Parent node might also be full → cascades up
→ At high write throughput: constant splits → fragmentation → slower reads over time
→ Solution: OPTIMIZE TABLE or REBUILD INDEX (offline operation, very expensive on large tables)
```

---

### LSM Tree Internal Structure (Cassandra / RocksDB)

```
WRITE PATH:
──────────────────────────────────────────────────────────────────

New Write (key=UserA, score=100)
          │
          ▼
  ┌───────────────────────┐
  │  WAL (Write-Ahead Log)│  ← written to disk first for durability
  │  append-only log file │     (crash recovery: replay WAL on restart)
  └───────────────────────┘
          │
          ▼
  ┌───────────────────────┐
  │  MemTable             │  ← sorted in-memory structure (Red-Black tree)
  │  UserA=100            │     all writes go here first → sub-millisecond
  │  UserB=200            │
  │  UserC=50             │
  └───────────────────────┘
          │  (when MemTable reaches size limit, e.g. 64MB)
          ▼
  ┌───────────────────────┐
  │  SSTable L0 (immutable│  ← flushed to disk, sorted, never modified
  │  sorted file on disk) │     multiple SSTables pile up at L0
  └───────────────────────┘
          │  (compaction process merges L0 → L1 → L2)
          ▼
  ┌───────────────────────┐
  │  SSTable L1           │  ← merged, sorted, deduplicated
  └───────────────────────┘
          │
          ▼
  ┌───────────────────────┐
  │  SSTable L2           │  ← larger, fewer files, more organized
  └───────────────────────┘

DISK LAYOUT (actual files on disk):
─────────────────────────────────────────────────────────────
  Level 0:  [SSTable-001] [SSTable-002] [SSTable-003]   ← overlapping ranges, 4 files max
  Level 1:  [SSTable-010] [SSTable-011] [SSTable-012]   ← no overlap, 10 files max
  Level 2:  [SSTable-020] [SSTable-021] ... [SSTable-030]  ← no overlap, 100 files max
─────────────────────────────────────────────────────────────
  Each SSTable has a Bloom Filter: "does key X exist in this file?"
  → if Bloom Filter says NO → skip the file entirely (0 disk reads)
  → if Bloom Filter says YES → read the file to find key
```

---

### READ PATH Comparison

```
B-Tree READ (MySQL):                  LSM Tree READ (Cassandra):
────────────────────                  ─────────────────────────

Query: SELECT * FROM                  Query: SELECT * FROM
       users WHERE id=42                     users WHERE id=42

Step 1: Root page (in RAM)            Step 1: Check MemTable (RAM) → miss
Step 2: Internal page (1 disk read)   Step 2: Check L0 SSTable-003 Bloom
Step 3: Leaf page (1 disk read)               Filter → "NO" → skip
Step 4: Return row data               Step 3: Check L0 SSTable-002 Bloom
                                              Filter → "MAYBE" → disk read → miss
Total: 2-4 disk reads                 Step 4: Check L1 SSTable-011 Bloom
       O(log N)                               Filter → "YES" → disk read → FOUND

                                      Total: 2-5 disk reads (varies)
                                             but Bloom Filters eliminate most

Winner for point reads: B-Tree        Winner for range scans: B-Tree
                                      (LSM has scattered data across levels)
```

---

### WRITE PATH Comparison

```
B-Tree WRITE (MySQL):                 LSM Tree WRITE (Cassandra):
──────────────────────                ───────────────────────────

INSERT INTO users                     INSERT INTO users
VALUES (id=42, name='Abhi')           VALUES (id=42, name='Abhi')

Step 1: Find the right leaf page      Step 1: Append to WAL (disk, sequential)
        (random disk read)            Step 2: Insert into MemTable (RAM)
Step 2: If page full → SPLIT          Step 3: Return ACK to client ✓
        (random disk write +
         parent update +              Total: 1 sequential disk write + 1 RAM write
         possible cascade)                   O(1) — constant time regardless
Step 3: Write to leaf page            of how much data you have
        (random disk write)
Step 4: Update WAL

Total: 2-10 random disk I/Os          Sequential writes = 10x faster than
       O(log N) with high variance    random writes on both SSD and HDD

Winner for writes: LSM Tree — always
```

---

## PART 3 — THE INTERVIEW CONVERSATION
### "How I'd explain this if you asked me in a system design interview"

---

**Interviewer:** "You've chosen MySQL here — can you explain why not Cassandra?"

**You (architect answer):**

> "Great question. The core difference comes down to the storage engine — MySQL InnoDB uses
> a B-Tree structure and Cassandra uses an LSM Tree. Let me explain why that matters here.
>
> In a B-Tree, data is stored in a balanced tree of fixed-size pages, typically 16KB each.
> Every read is O(log N) — you traverse from root to leaf. For a table with 100 million rows,
> that's roughly 4 page reads. Fast and predictable. Range scans are especially efficient
> because leaf pages are doubly linked — you just follow the chain.
>
> The cost is writes. Every insert must find the right leaf page, and if that page is full,
> it splits. Splits can cascade upward, causing multiple random disk writes per insert.
> At high write throughput — say 50K inserts/second — you get constant page splits,
> fragmentation, and degraded read performance over time.
>
> An LSM Tree works completely differently. Every write is an append to an in-memory
> structure called a MemTable. No searching, no page splits. When MemTable fills up,
> it's flushed to disk as an immutable sorted file called an SSTable.
> Reads are more complex — you might check 3–5 SSTables — but Bloom Filters on each
> SSTable let you skip files that definitely don't contain your key.
>
> For this use case — a payment system where I need consistent read latency under 10ms,
> complex joins across accounts and transactions, and ACID guarantees — B-Tree (MySQL)
> wins. The write volume is moderate, the reads are complex, and I need transactions.
>
> If this were an activity feed ingesting 500K events/second from millions of users,
> I'd pick Cassandra's LSM Tree in a heartbeat — write throughput is the bottleneck,
> eventual consistency is acceptable, and the data model is simple (partition by user)."

---

## PART 4 — WHEN TO PICK WHICH (Decision Framework)

```
START HERE
     │
     ▼
Is write throughput > 50K/sec?
     │
     ├── YES ──► Is the data model simple (key-value, wide column)?
     │                │
     │                ├── YES ──► Use Cassandra / DynamoDB / HBase (LSM)
     │                │           Examples: activity feeds, IoT sensors,
     │                │           time-series metrics, leaderboard score ingestion
     │                │
     │                └── NO ──►  Use Kafka + batch writes into Cassandra
     │                            (buffer the writes, write in batches)
     │
     └── NO ──► Do you need complex queries, joins, or ACID transactions?
                     │
                     ├── YES ──► Use MySQL / PostgreSQL (B-Tree)
                     │           Examples: payments, e-commerce orders,
                     │           user accounts, hotel bookings
                     │
                     └── NO ──►  Do you need full-text search?
                                      │
                                      ├── YES ──► Elasticsearch (inverted index)
                                      │
                                      └── NO ──►  Redis for hot data (skip list)
                                                  + MySQL for persistence
```

---

## PART 5 — REAL-WORLD MAPPING ACROSS YOUR 21 SYSTEMS

| System | DB Choice | Why |
|--------|-----------|-----|
| TinyURL | MySQL | Moderate writes, strong read consistency, simple schema |
| Rate Limiter | Redis + MySQL | Redis for fast counters, MySQL for config/audit |
| Notification | MySQL + Cassandra | MySQL for templates/prefs, Cassandra for notification log (high write) |
| Chat (WhatsApp) | Cassandra | 500K messages/sec, append-only, partition by chat_id |
| Social Feed | Cassandra + Redis | Cassandra for feed storage (high write), Redis for hot feeds |
| Uber/Ola | MySQL + Redis | Trips need ACID (payment), Redis for driver location |
| Payment | MySQL (InnoDB) | ACID is non-negotiable, write volume is moderate |
| Food Delivery | MySQL + Cassandra | Orders need ACID (MySQL), delivery events are high-write (Cassandra) |
| E-Commerce | MySQL + Elasticsearch | Orders/inventory need ACID, product search needs full-text |
| Cloud Storage | MySQL + S3 | Metadata in MySQL (B-Tree for queries), files in object storage |
| Ticket Booking | MySQL | Seat locking needs ACID, write volume is moderate |
| Hotel Booking | MySQL | Same as ticket booking |
| Leaderboard | Cassandra + Redis | Score ingestion is high-write (Cassandra/Kafka), top-K reads from Redis |
| Proximity Search | PostgreSQL/PostGIS | Geospatial indexes, moderate write volume |
| Logging System | Elasticsearch + S3 | Inverted index for search, S3 for cold archive |
| Job Scheduler | MySQL | Job state needs ACID, row locking for claiming jobs |
| OTT Platform | Cassandra + MySQL | View events are high-write (Cassandra), user accounts in MySQL |
| Text Editor | Cassandra | Ops are append-only (insert/delete), high write, partition by doc |
| Stock Broker | MySQL + Cassandra | Orders need ACID (MySQL), tick data is high-write (Cassandra) |
| Email System | MySQL + Cassandra | User settings in MySQL, email event log in Cassandra |
| Learning Platform | MySQL + Elasticsearch | Courses/enrollment need ACID, content search needs full-text |

---

## PART 6 — THE ONE THING INTERVIEWERS TEST

> **Interviewer trap:** "You said Cassandra for the activity feed. What happens if you need
> to query all activities where type='comment' across all users?"

**Wrong answer:** "I'll just add a secondary index on type."

**Right answer:**

> "That query violates Cassandra's data model. Cassandra is optimized for partition-key
> lookups — it partitions data across nodes by a key, and cross-partition queries require
> hitting every node in the cluster. A secondary index on `type` in Cassandra is a distributed
> index — every write updates every node's index, and reads scatter to all nodes anyway.
>
> For analytical queries like 'all comments across all users', I'd push those events to
> a data warehouse (BigQuery, Redshift, Snowflake) via Kafka. Cassandra handles the operational
> write path. The analytics platform handles cross-partition aggregations. Two separate systems,
> each doing what it's good at."

---

## PART 7 — COMPACTION — THE HIDDEN CASSANDRA COST

> This is what most beginners miss about LSM Trees.

```
The LSM write cost doesn't disappear — it's deferred.

WRITE: 1ms (append to MemTable → WAL)  ← looks free!
                │
                │  hours/days later...
                ▼
COMPACTION: Reads all L0 SSTables,
            merges them (sort-merge),
            writes merged L1 SSTable,
            deletes old L0 SSTables

  ┌───────────────────────────────────────────────────────┐
  │  Compaction is a background I/O storm                 │
  │  It can consume 30-50% of disk I/O bandwidth          │
  │  During compaction: reads slow down                   │
  │  You need 2x your data size in free disk for compaction│
  └───────────────────────────────────────────────────────┘

  In production Cassandra clusters:
  → Monitor compaction queue depth (if it grows → you're writing faster than compacting)
  → Size-tiered compaction: merge SSTables of similar size (good for write-heavy)
  → Leveled compaction: smaller SSTables, better read performance (like RocksDB default)
```

**Interview one-liner:** "LSM Tree moves the write cost from the hot path into background compaction. You're not eliminating I/O — you're deferring it and making it sequential instead of random."

---

## QUICK REFERENCE CARD

```
┌─────────────────────┬──────────────────────┬──────────────────────┐
│                     │    B-Tree (MySQL)     │  LSM Tree (Cassandra)│
├─────────────────────┼──────────────────────┼──────────────────────┤
│ Write latency       │ High (page splits)   │ Low (append-only)    │
│ Read latency        │ Low (O log N)        │ Medium (multi-level) │
│ Range scans         │ Excellent            │ Poor                 │
│ Write throughput    │ ~10K-50K/sec         │ ~100K-500K/sec       │
│ Transactions (ACID) │ Yes (InnoDB)         │ No (eventual)        │
│ Storage overhead    │ ~2x (fragmentation)  │ ~2x (compaction)     │
│ Disk I/O pattern    │ Random               │ Sequential           │
│ Update in-place     │ Yes                  │ No (tombstone)       │
│ Best for            │ OLTP, payments,      │ Time-series, feeds,  │
│                     │ bookings, inventory  │ logs, IoT, messaging │
└─────────────────────┴──────────────────────┴──────────────────────┘

Real products using B-Tree:    Real products using LSM:
  MySQL (InnoDB)                 Cassandra
  PostgreSQL                     RocksDB (used inside Facebook, TikTok)
  SQLite                         LevelDB (used inside Chrome's IndexedDB)
  Oracle                         HBase
  SQL Server                     BadgerDB
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Interviewers expect you to justify your storage engine choice — "I used MySQL" is not an answer; "I used MySQL B-tree for range scans on payment history but Cassandra LSM for the append-only audit log" is.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **02 — Distributed Rate Limiter** | Redis uses a skip-list internally for sorted sets — a write-optimized structure similar in spirit to LSM. Counter storage is pure writes (INCR/INCRBY on every request). MySQL B-tree would cause a page write and potential page split on every single increment. Redis wins because it's in-memory with zero I/O overhead per write. |
| **07 — Payment System** | MySQL B-tree for the accounts table: balance lookups and range scans on transaction history benefit from B-tree's sorted structure. Cassandra LSM for the audit log: payment events are append-only and never updated — LSM's sequential write path makes this dramatically faster than random B-tree page writes. |
| **13 — Leaderboard** | Redis sorted set skip-list absorbs billions of ZINCRBY score updates per day. Each score update is O(log N) in the skip-list. MySQL B-tree at this write rate would fragment constantly, causing page splits and index rebuilds. |
| **19 — Stock Broker** | Trade history is append-only at microsecond intervals → Cassandra LSM (sequential writes, no updates). The order book needs range scans on price levels → PostgreSQL B-tree (WHERE price BETWEEN x AND y is a B-tree strength, not LSM's). |

**Architect's one-liner for the interview:**
*"If your workload is mostly writes with no updates, LSM wins on write throughput; if you need sorted range scans on stable data, B-tree wins on read performance — pick the engine that matches your access pattern, not your team's familiarity."*
