# Why UUID as Primary Key is Bad
### B-Tree Page Splits, Fragmentation, and Slower Inserts at Scale

---

## PART 1 — THE STUDENT CONVERSATION

**Let me ask you something first.**

You have a filing cabinet with 10 drawers. Each drawer holds papers sorted by number: drawer 1 holds papers 1–100, drawer 2 holds 101–200, and so on. Every drawer is full but organized.

Now I hand you a new paper with number **47**. Where do you put it?
You go to drawer 1 (which already has 100 papers), pull out papers 48–100, put 47 in the right spot, push everything back. Done — but that was work.

Now I hand you papers numbered: **7a3f-91bc, 2e4d-aa01, f901-3312** (random UUIDs). You have no idea which drawer they belong to. You open a random drawer, shove them in, the drawer overflows, you split it — and you do this 1000 times per second.

That is exactly what happens when you use UUID as a primary key in MySQL.

---

## PART 2 — WHAT ACTUALLY HAPPENS INTERNALLY

### How MySQL Stores Primary Keys (Clustered Index)

MySQL InnoDB stores rows **in the order of the primary key** on disk. This is called a **clustered index**. The primary key IS the physical order of the data.

```
AUTO-INCREMENT Primary Key (sequential inserts):
───────────────────────────────────────────────

  Page 1          Page 2          Page 3
┌──────────┐    ┌──────────┐    ┌──────────┐
│ id=1     │    │ id=1001  │    │ id=2001  │
│ id=2     │    │ id=1002  │    │ id=2002  │
│ id=3     │    │ id=1003  │    │ id=2003  │
│ ...      │    │ ...      │    │ ...      │
│ id=1000  │    │ id=2000  │    │ id=3000  │
└──────────┘    └──────────┘    └──────────┘
     ↑ FULL          ↑ FULL         ↑ has space

New insert: id=3001 → goes to Page 3 (has space) → append to end
→ No reorganization needed. Fast. Predictable. O(1) page writes.
```

```
UUID Primary Key (random inserts):
───────────────────────────────────

  Page 1          Page 2          Page 3
┌──────────────────────────────────────────┐
│ 1a2b3c4d-...  │ 5e6f7a8b-...  │ 9c0d1e2f│
│ 3f4e5d6c-...  │ 7b8a9c0d-...  │ ...     │
│ ...            │ ...           │ FULL    │
└──────────────────────────────────────────┘

New insert: 2b3c4d5e-... (random UUID)
→ MySQL looks up: "where does this UUID sort?"
→ It belongs INSIDE Page 1 (alphabetical order of UUID string)
→ Page 1 is FULL → PAGE SPLIT

PAGE SPLIT:
┌──────────────┐        ┌──────────────┐
│ 1a2b3c4d-... │        │ 2b3c4d5e-... │  ← new entry
│ 1c2d3e4f-... │        │ 3f4e5d6c-... │  ← moved here
└──────────────┘        └──────────────┘
→ Parent node must be updated to point to both new pages
→ If parent is also full → parent splits → cascades up
→ At 10K inserts/sec: thousands of splits per second
```

---

## PART 3 — THE FRAGMENTATION PROBLEM

```
After 6 months of UUID inserts:

  Page 1    Page 2    Page 3    Page 4    Page 5    Page 6
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ 40%    │ │ 55%    │ │ 38%    │ │ 61%    │ │ 42%    │ │ 50%    │
│ full   │ │ full   │ │ full   │ │ full   │ │ full   │ │ full   │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘

Average fill factor: ~48%
→ You need 2x the disk space to store the same amount of data
→ A full table scan reads TWICE as many pages as it should
→ Buffer pool (RAM cache) wastes space on half-empty pages
→ Range queries are slow: related rows are scattered across non-adjacent pages

After 6 months of AUTO_INCREMENT inserts:

  Page 1    Page 2    Page 3    Page 4    Page 5    Page 6
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  95%   │ │  95%   │ │  95%   │ │  95%   │ │  95%   │ │  60%   │
│  full  │ │  full  │ │  full  │ │  full  │ │  full  │ │  full  │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘

→ Tight packing, minimal wasted space
→ Range scans are fast: rows are physically adjacent
→ Last page has space → new inserts just append
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your schema uses UUID as the primary key everywhere. Is that a concern?"

**You (architect answer):**

> "Yes, it's worth flagging. The issue is how MySQL InnoDB stores data.
> InnoDB uses a clustered index — the primary key IS the physical sort order of rows on disk.
> With UUID, every insert lands at a random position in the B-Tree, because UUIDs are random 128-bit
> values with no sequential ordering. This has two consequences.
>
> First, page splits. When a UUID inserts into a page that's already full, MySQL has to split that
> page into two, update the parent node, and sometimes cascade that split upward. At 10K inserts per
> second, you're doing thousands of page splits per second — each one requiring multiple random disk writes.
>
> Second, fragmentation. After sustained UUID inserts, pages end up 40–50% full on average instead of
> 90%+. A table scan reads twice as many pages, the buffer pool wastes RAM on half-empty pages, and
> range queries become slow because related rows are scattered across non-adjacent pages.
>
> The fix depends on the use case. If I need a globally unique ID exposed to clients (for URLs, APIs),
> I use ULID or UUID v7 — both are time-ordered, so they sort sequentially like auto-increment but
> carry global uniqueness. If the ID is purely internal (never exposed), auto-increment BIGINT is the
> right choice. The UUID stays as a secondary column for external exposure."

---

## PART 5 — THE SOLUTIONS

### Option 1: AUTO_INCREMENT BIGINT (best for internal IDs)
```sql
CREATE TABLE orders (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,  -- sequential, fast
    public_id VARCHAR(36) NOT NULL UNIQUE,          -- UUID for external exposure
    ...
);
```
- Insert to last page always → no splits
- Exposes sequential IDs externally → use `public_id` (UUID) for API URLs
- BIGINT gives you 9.2 quintillion IDs — never runs out

### Option 2: ULID (Universally Unique Lexicographically Sortable Identifier)
```
UUID:  f47ac10b-58cc-4372-a567-0e02b2c3d479  ← random, no order
ULID:  01ARZ3NDEKTSV4RRFFQ69G5FAV           ← first 10 chars = timestamp, rest = random

01ARZ3NDEK  TSV4RRFFQ69G5FAV
└─────────┘ └──────────────┘
 timestamp    randomness
 (sorted)     (uniqueness)
```
- Sorts chronologically → inserts always go near the end → minimal splits
- Still globally unique → safe for distributed systems (no central counter)

### Option 3: UUID v7 (newer standard)
```
UUID v4 (random):  4a7b1c3d-8e9f-4abc-b012-3d4e5f6a7b8c  ← pure random
UUID v7 (ordered): 018e1234-5678-7abc-8def-123456789abc  ← first 48 bits = millisecond timestamp
```
- Supported natively in PostgreSQL 17, MySQL 9.0+
- Drop-in replacement for UUID v4 but without the page split problem

---

## PART 6 — WHEN UUID IS ACTUALLY FINE

```
UUID is acceptable when:
  ✓ PostgreSQL with HEAP storage (not clustered by default)
     → PG doesn't cluster on PK by default, so UUID PK hurts less
  ✓ The table has low write volume (<1K inserts/sec)
  ✓ You're using it as a secondary key (not the clustered primary key)
  ✓ You need distributed ID generation across multiple DBs
     (no shared counter possible)
  ✓ You're using CockroachDB / Spanner (they handle UUID clustering internally)

UUID is harmful when:
  ✗ MySQL InnoDB, high write volume (>5K inserts/sec)
  ✗ Table is frequently range-scanned
  ✗ Table has limited RAM for buffer pool (fragmentation fills cache inefficiently)
  ✗ Using as foreign key reference (all foreign key lookups become random reads)
```

---

## QUICK REFERENCE CARD

```
┌──────────────────┬─────────────────┬──────────────────┬─────────────────┐
│                  │  AUTO_INCREMENT  │      ULID        │    UUID v4      │
├──────────────────┼─────────────────┼──────────────────┼─────────────────┤
│ Insert pattern   │ Sequential       │ Sequential       │ Random          │
│ Page splits      │ Almost never     │ Almost never     │ Constant        │
│ Fragmentation    │ Minimal          │ Minimal          │ High (40-50%)   │
│ Global unique    │ No (per DB)      │ Yes              │ Yes             │
│ Expose in URL    │ No (guessable)   │ Yes              │ Yes             │
│ Sortable by time │ Yes              │ Yes              │ No              │
│ DB support       │ All              │ App-generated    │ All             │
└──────────────────┴─────────────────┴──────────────────┴─────────────────┘

Bottom line:
  Internal-only IDs → AUTO_INCREMENT BIGINT
  External IDs in distributed system → ULID or UUID v7
  Never → UUID v4 as MySQL clustered primary key at scale
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** UUID PKs are a hidden performance bomb at scale — interviewers specifically probe this to see if you understand B-tree internals and write amplification.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **07 — Payment System** | Millions of daily inserts. Random UUID PKs cause constant B-tree page splits and a 40-50% index fill factor. Solution: BIGINT AUTO_INCREMENT as the clustered PK for write locality, plus a separate public_id UUID column (non-clustered, indexed) for external API exposure. |
| **09 — E-Commerce** | Flash sales push 10K+ orders/second. Sequential BIGINT PKs keep all inserts on the rightmost leaf page of the B-tree — zero fragmentation, zero page splits under load. UUID PKs would scatter inserts randomly across the entire index tree. |
| **11 — Ticket Booking** | Flash sale seat reservations. UUID inserts compete for random pages across the B-tree, increasing lock contention. Sequential IDs localize write contention to the rightmost page, reducing deadlock probability under the concurrent-booking storm. |
| **19 — Stock Broker** | Trades arrive at microsecond intervals. UUID PKs cause buffer pool cache thrashing — the working set of "hot" pages is scattered across the entire index. ULID or a sequential trade_id keeps the working set in the rightmost pages, maximizing buffer pool hit rate. |

**Architect's one-liner for the interview:**
*"UUID v4 as a clustered primary key trades write locality for global uniqueness — at 10K inserts/second that tradeoff costs you 40% index fragmentation; use a sequential BIGINT PK and expose UUID only at the API boundary."*
