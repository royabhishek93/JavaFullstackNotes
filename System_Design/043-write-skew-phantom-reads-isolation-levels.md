# Write Skew and Phantom Reads
### The Concurrency Bugs That MVCC and Optimistic Locking Don't Prevent

---

## PART 1 — THE STUDENT CONVERSATION

A hospital has a rule: there must always be at least one doctor on call. Two doctors — Alice and Bob — both check the schedule at the same moment. Both see each other is on call.

Alice thinks: "Bob is here, I can go home." She marks herself off-call.
Bob thinks: "Alice is here, I can go home." He marks himself off-call.

Now nobody is on call. The hospital invariant is violated.

Neither doctor read dirty data. Neither doctor had a "lost update" — they wrote to different rows. Both made a valid individual decision. But together they broke the system.

This is **write skew**: two transactions read an overlapping set of rows, each makes a decision based on what they read, and their combined writes violate a constraint that was true when either read.

This is different from:
- **Dirty read**: reading uncommitted data from another transaction (prevented by READ COMMITTED)
- **Lost update**: two transactions overwrite the same row (prevented by row-level locking or `SELECT FOR UPDATE`)
- **Phantom read**: a new row appears mid-transaction that matches your query (prevented by SERIALIZABLE)

Write skew requires SERIALIZABLE isolation or explicit locking (`SELECT FOR UPDATE`) to prevent — nothing weaker stops it.

---

## PART 2 — ISOLATION LEVELS AND ANOMALY DIAGRAMS

### Write Skew — The Hospital Scenario

```
T1 (Alice leaves):                  T2 (Bob leaves):
  BEGIN                               BEGIN

  SELECT count(*) FROM oncall
    WHERE shift='night'
    → 2 doctors on call

                                      SELECT count(*) FROM oncall
                                        WHERE shift='night'
                                        → 2 doctors on call

  (Both see 2 — both think safe to proceed)

  UPDATE oncall
    SET status='off'
    WHERE doctor='alice'

                                      UPDATE oncall
                                        SET status='off'
                                        WHERE doctor='bob'

  COMMIT                              COMMIT

Result: 0 doctors on call.
Neither transaction saw a dirty read.
Neither transaction had a lost update (they wrote different rows).
This is WRITE SKEW — reads consistent, writes conflict on invariant.
```

### Phantom Read — The Seat Booking Scenario

```
T1: SELECT * FROM seats
      WHERE flight='AA100' AND status='available'
      → 3 rows returned

T2: INSERT INTO seats VALUES ('AA100', '14C', 'available')
    COMMIT

T1: SELECT * FROM seats
      WHERE flight='AA100' AND status='available'
      → 4 rows returned  ← row that didn't exist at T1's start now visible

This is a PHANTOM READ — a new row appeared that matches T1's query predicate.
T1 got a different result set on its second read, not because existing rows changed
but because a new row was inserted by a concurrent transaction.
```

### Isolation Levels — What Each Prevents

```
┌─────────────────────┬─────────────┬────────────────┬───────────────┬────────────┐
│                     │ Dirty Read  │ Non-repeatable │ Phantom Read  │ Write Skew │
│                     │             │ Read           │               │            │
├─────────────────────┼─────────────┼────────────────┼───────────────┼────────────┤
│ READ UNCOMMITTED    │ possible    │ possible       │ possible      │ possible   │
│ READ COMMITTED      │ prevented   │ possible       │ possible      │ possible   │
│ REPEATABLE READ     │ prevented   │ prevented      │ possible*     │ possible   │
│ SERIALIZABLE        │ prevented   │ prevented      │ prevented     │ prevented  │
└─────────────────────┴─────────────┴────────────────┴───────────────┴────────────┘

* PostgreSQL REPEATABLE READ prevents phantom reads via MVCC snapshots.
  But write skew is still possible until SERIALIZABLE.
  MySQL REPEATABLE READ does NOT prevent phantom reads.
```

### Non-Repeatable Read (for completeness)

```
T1: SELECT balance FROM accounts WHERE id=42  → 1000
T2: UPDATE accounts SET balance=500 WHERE id=42; COMMIT
T1: SELECT balance FROM accounts WHERE id=42  → 500  ← DIFFERENT value!

T1 read the same row twice and got different values.
Prevented by: REPEATABLE READ and above.
```

---

## PART 3 — SOLUTIONS AND IMPLEMENTATION

### Option 1: SERIALIZABLE Isolation

```sql
-- PostgreSQL uses Serializable Snapshot Isolation (SSI)
-- Lower overhead than traditional locking-based SERIALIZABLE
-- 10-20% performance cost vs REPEATABLE READ

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;

SELECT count(*) FROM oncall WHERE shift='night';
-- T1 gets count=2

UPDATE oncall SET status='off' WHERE doctor='alice';

COMMIT;
-- If T2 ran concurrently, PostgreSQL detects the serialization conflict
-- and aborts one transaction with:
--   ERROR: could not serialize access due to read/write dependencies among transactions
-- Application must retry the aborted transaction.
```

### Option 2: SELECT FOR UPDATE (Pessimistic Locking)

```sql
-- Prevents write skew by locking rows at read time

BEGIN;

-- Lock ALL oncall rows for this shift
SELECT * FROM oncall WHERE shift='night' FOR UPDATE;
-- T2's SELECT FOR UPDATE blocks here until T1 commits

SELECT count(*) FROM oncall WHERE shift='night';
-- → 2 doctors

-- Safe to proceed: T2 is blocked until we commit
UPDATE oncall SET status='off' WHERE doctor='alice';

COMMIT;
-- Now T2 unblocks, re-reads count=1, decides NOT to go home
```

### Option 3: Materialized Conflict Row

```sql
-- Add a "conflict row" that both transactions must touch
-- Forces serialization through a common row

CREATE TABLE shift_lock (
  shift VARCHAR PRIMARY KEY,
  version INT NOT NULL DEFAULT 0
);

BEGIN;
-- Both T1 and T2 must update this row
UPDATE shift_lock SET version=version+1 WHERE shift='night';
-- T2's UPDATE blocks until T1 commits (row-level lock)

SELECT count(*) FROM oncall WHERE shift='night';
IF count >= 2 THEN
  UPDATE oncall SET status='off' WHERE doctor='alice';
END IF;
COMMIT;
```

### Option 4: Re-check Before Commit

```sql
BEGIN;
-- Lock the rows you care about
SELECT * FROM oncall WHERE shift='night' FOR UPDATE;

-- Check invariant INSIDE the locked transaction
SELECT count(*) FROM oncall WHERE shift='night' AND status='on'
INTO @oncall_count;

IF @oncall_count > 1 THEN
  UPDATE oncall SET status='off' WHERE doctor='alice';
  COMMIT;
ELSE
  ROLLBACK;  -- refuse to leave, invariant would be violated
END IF;
```

### When Each Solution Applies

| Scenario | Recommended Solution | Reason |
|----------|---------------------|--------|
| Seat booking (1 seat left) | `SELECT FOR UPDATE` | Lock the specific seat row. Simple, predictable. |
| Shift scheduling (min N constraint) | `SERIALIZABLE` or `SELECT FOR UPDATE` on all shift rows | Invariant spans multiple rows. |
| Hotel booking (room + date range) | `SELECT FOR UPDATE` on room+date rows | Overlapping ranges need explicit locks. |
| High-throughput flash sale | Optimistic locking + retry | `FOR UPDATE` creates contention; optimistic is faster when conflicts are rare. |
| Financial double-spend | `SELECT FOR UPDATE` on account row | Lock the specific account. Well-understood, low latency. |

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Two users simultaneously try to book the last available seat on a flight. Both read 'available=true'. Both try to reserve it. How do you ensure only one succeeds?"

**You (architect answer):**

> "The naive approach fails because both transactions read 'available=true' before either commits — that's exactly the write skew pattern. Neither sees a dirty read; they each see a valid snapshot. The fix requires one of two approaches.
>
> First choice: `SELECT FOR UPDATE` on the seat row. Transaction 1 issues `SELECT * FROM seats WHERE id=14C FOR UPDATE` — this acquires a row-level exclusive lock. Transaction 2's `SELECT FOR UPDATE` on the same row blocks immediately. When Transaction 1 commits (seat now reserved, `available=false`), Transaction 2 unblocks, re-reads the row, sees `available=false`, and either rolls back with an error or picks another seat. Clean, predictable, zero write skew.
>
> Second choice: SERIALIZABLE isolation. Both transactions run at `ISOLATION LEVEL SERIALIZABLE`. PostgreSQL's SSI tracks read-write dependencies. When T2 tries to commit, PostgreSQL detects that T1 read the same data T2 wrote to, and aborts T2 with a serialization error. The application retries T2. This is more elegant but requires retry logic.
>
> For a ticketing system, I'd choose `SELECT FOR UPDATE` — it's explicit, the lock scope is clear (just the seat row), and there's no need for application-level retry loops. For a system with more complex invariants spanning many rows (like shift scheduling where you're checking a count), SERIALIZABLE is cleaner because you don't have to figure out which rows to lock upfront.
>
> One thing optimistic locking does NOT fix here: it prevents lost updates on a single row, but if the issue is a phantom insert (someone inserts a new competing booking while you're checking availability), optimistic locking won't catch that. For phantom reads, you need either SERIALIZABLE or predicate locking."

---

## PART 5 — DECISION FRAMEWORK

### Isolation Level Selection

| System Type | Isolation Level | Performance Cost | Use When |
|-------------|----------------|------------------|----------|
| General CRUD API | READ COMMITTED | Baseline | No invariants spanning multiple rows |
| Analytics queries | READ COMMITTED | Baseline | Approximate reads acceptable |
| Report generation | REPEATABLE READ | Low (~5%) | Consistent snapshot across multiple selects in one transaction |
| Seat / room booking | SERIALIZABLE or FOR UPDATE | Medium (10-20%) | Last-unit reservation, row-spanning invariants |
| Financial transfers | SERIALIZABLE or FOR UPDATE | Medium | Balance invariants, double-spend prevention |
| Inventory management | SERIALIZABLE or FOR UPDATE | Medium | "At least N in stock" invariants |

### Lock Scope Decision Tree

```
Does your invariant involve a COUNT or SUM across multiple rows?
  YES → SERIALIZABLE isolation (locking all matching rows with FOR UPDATE is fragile)
  NO → Does it involve exactly one row?
         YES → SELECT FOR UPDATE on that row (simple, fast, explicit)
         NO (involves 2-3 specific rows) → SELECT FOR UPDATE on all of them
                                           OR SERIALIZABLE isolation
```

### Performance Guidance

| Approach | Throughput (relative) | Latency | Retry Logic Needed |
|----------|----------------------|---------|-------------------|
| READ COMMITTED | 100% baseline | Lowest | No |
| REPEATABLE READ | ~95% | Low | No |
| SERIALIZABLE (SSI) | ~80-90% | Medium | Yes (serialization errors) |
| SELECT FOR UPDATE | ~85-95% | Medium (blocked) | No (blocks, doesn't abort) |

---

## QUICK REFERENCE CARD

```
ISOLATION ANOMALIES
===================
Dirty read:          Reading uncommitted data. → Prevented by READ COMMITTED+
Non-repeatable read: Same row returns different values within a transaction.
                     → Prevented by REPEATABLE READ+
Phantom read:        New rows appear mid-transaction matching your predicate.
                     → Prevented by SERIALIZABLE (PostgreSQL RR also prevents this)
Write skew:          Two txns read overlapping rows, make decisions, combined
                     writes violate an invariant. → ONLY prevented by SERIALIZABLE
                     or explicit SELECT FOR UPDATE.

KEY SOLUTIONS
=============
SELECT FOR UPDATE:   Lock rows at read time. T2 blocks until T1 commits.
SERIALIZABLE (SSI):  PostgreSQL detects read-write conflicts at commit time.
                     One txn aborts with serialization error → must retry.
Materialized lock:   Add a conflict row both txns must UPDATE → forced serialization.

RULES OF THUMB
==============
Money / invariants → SERIALIZABLE or FOR UPDATE. Never READ COMMITTED.
Booking systems    → FOR UPDATE on the specific resource row.
Count-based check  → SERIALIZABLE (you can't FOR UPDATE rows that don't exist yet).
Read-heavy APIs    → READ COMMITTED. Most CRUD doesn't need stronger isolation.
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Write skew is the sneaky concurrency bug where both transactions see valid data and make valid decisions — but together they break the system; only SERIALIZABLE or SELECT FOR UPDATE stops it.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **07 — Payment System** | Double-spend prevention. Two concurrent transactions both read "balance=1000", both attempt to debit 900. `SELECT FOR UPDATE` on the account row serializes the debits — second transaction sees balance=100 after first commits, and correctly rejects. |
| **11 — Ticket Booking** | Last seat. Both users read "1 seat available." `SELECT FOR UPDATE` prevents double booking. For flash sales with millions of concurrent users: READ COMMITTED + idempotency key + atomic counter in Redis, accepting that DB-level serialization won't scale. |
| **12 — Hotel Booking** | Last room for a date range. Write skew risk: two bookings for same room on overlapping dates both see "room available." `SELECT FOR UPDATE` on room+date rows or SERIALIZABLE isolation prevents the double-booking. |

**Architect's one-liner for the interview:**
*"Write skew happens when two transactions each read rows the other will update — only SERIALIZABLE isolation or SELECT FOR UPDATE prevents the invariant violation."*
