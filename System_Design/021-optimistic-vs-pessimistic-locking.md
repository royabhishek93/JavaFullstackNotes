# Optimistic vs Pessimistic Locking
### What Each Is, When Each Causes Deadlocks

---

## PART 1 — THE STUDENT CONVERSATION

**The scenario: two people booking the last seat on a flight.**

User A and User B both see seat 14A is available. They both click "Book."
Two requests hit your server at the same time. Both read: "seat 14A = available."
Both write: "seat 14A = booked by me."

Who wins? In a naive system: whoever writes last wins. Both get a confirmation email.
Both show up at the gate. One person has to sit on the floor. That's a bug.

**Locking is how you prevent two transactions from corrupting shared data.**

There are two philosophies:

**Pessimistic:** "Assume the worst. Lock the row as soon as I read it. Nobody else can touch it until I'm done."

**Optimistic:** "Assume the best. Don't lock anything. But before I write, check if anyone else changed the data since I read it. If yes, reject my write and try again."

---

## PART 2 — PESSIMISTIC LOCKING EXPLAINED

### How It Works

```sql
-- User A's transaction:
BEGIN;
SELECT * FROM seats WHERE id = 14 AND status = 'available' FOR UPDATE;
-- ↑ this LOCKS the row. User B cannot read-for-update or write this row.

UPDATE seats SET status = 'booked', user_id = 'userA' WHERE id = 14;
COMMIT;
-- Lock released here.
```

```
Timeline:
─────────────────────────────────────────────────────────────────────

T=0ms   User A: SELECT ... FOR UPDATE  ← acquires row lock
T=1ms   User B: SELECT ... FOR UPDATE  ← BLOCKED (waiting for lock)
T=5ms   User A: UPDATE ... COMMIT      ← releases lock
T=5ms   User B: lock granted, reads row
T=6ms   User B: sees status = 'booked'
T=6ms   User B: no available seat → return error to user
T=7ms   ✓ Only one booking, correct
```

### The Lock Types in MySQL

```
Row-level locks (InnoDB):
─────────────────────────

SELECT ... FOR UPDATE     → Exclusive lock (X)
  └── Nobody else can read-for-update OR write this row

SELECT ... FOR SHARE      → Shared lock (S)  (also: LOCK IN SHARE MODE)
  └── Others can also read-for-share
  └── Nobody can write this row

Table-level lock:
  LOCK TABLES seats WRITE  → locks entire table (never use in OLTP)
```

### The Deadlock Problem

```
Deadlock scenario:

  Transaction A holds lock on Row 1, wants Row 2
  Transaction B holds lock on Row 2, wants Row 1
  → Both waiting forever → MySQL detects this and kills one

T=0ms   Txn A: locks Row 1 (seat 14A)
T=0ms   Txn B: locks Row 2 (seat 14B)
T=1ms   Txn A: tries to lock Row 2 → BLOCKED (B holds it)
T=1ms   Txn B: tries to lock Row 1 → BLOCKED (A holds it)
T=2ms   MySQL deadlock detector fires
T=2ms   MySQL kills Txn B (rolls back), Txn A proceeds
T=3ms   Txn B receives: ERROR 1213: Deadlock found when trying to get lock

Fix: always lock rows in the SAME ORDER in all transactions
  Txn A: lock Row 1, then Row 2
  Txn B: lock Row 1, then Row 2  ← same order → no deadlock possible
```

---

## PART 3 — OPTIMISTIC LOCKING EXPLAINED

### How It Works

```sql
-- Schema: add a version column
CREATE TABLE seats (
    id INT PRIMARY KEY,
    status VARCHAR(20),
    user_id INT,
    version INT DEFAULT 0   -- ← the version counter
);

-- User A reads:
SELECT id, status, version FROM seats WHERE id = 14;
-- Returns: id=14, status='available', version=5

-- User A writes (checks version hasn't changed):
UPDATE seats
SET status = 'booked', user_id = 'userA', version = version + 1
WHERE id = 14 AND version = 5;  -- ← the optimistic check
-- If version is still 5 → UPDATE succeeds, 1 row affected
-- If version changed   → UPDATE affects 0 rows → conflict detected
```

```
Timeline (two concurrent requests):
────────────────────────────────────────────────────────────────────

T=0ms   User A reads seat 14: status='available', version=5
T=0ms   User B reads seat 14: status='available', version=5
        (both read same data, no locks, both proceed)

T=5ms   User A: UPDATE ... WHERE version=5  → SUCCESS (1 row affected)
                version is now 6
T=5ms   User B: UPDATE ... WHERE version=5  → FAILS  (0 rows affected)
                version is now 6, B's WHERE version=5 doesn't match
T=6ms   User B: detects 0 rows updated → retry or return error to user
T=7ms   ✓ Only one booking, correct
```

### Optimistic Locking in JPA/Hibernate (Java)

```java
@Entity
public class Seat {
    @Id
    private Long id;

    private String status;
    private Long userId;

    @Version                   // ← Hibernate manages version automatically
    private Integer version;
}

// Hibernate generates this SQL automatically:
// UPDATE seats SET status=?, user_id=?, version=? WHERE id=? AND version=?
// If 0 rows updated → throws OptimisticLockException

// Your service:
try {
    seat.setStatus("booked");
    seat.setUserId(currentUser);
    seatRepository.save(seat);  // Hibernate checks version
} catch (OptimisticLockException e) {
    // version conflict → retry or tell user to try again
    return ResponseEntity.status(409).body("Seat was just taken, please retry");
}
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "How do you handle concurrent seat bookings in the ticket booking system?"

**You (architect answer):**

> "The core problem is a lost update: two users read the same available seat and both try to book it.
> Without coordination, whoever commits last wins and you get double bookings.
>
> For seat booking specifically, I'd use pessimistic locking — SELECT FOR UPDATE on the seat row
> at the start of the booking transaction. The reason is that seat availability is finite and highly
> contended during peak events. A conflict means the seat is genuinely gone — there's no useful
> work for the second transaction to do, so there's no point in letting it proceed and fail at commit.
> We lock early, fail fast.
>
> For lower-contention scenarios — like updating a user profile or a product catalog — I'd use
> optimistic locking with a version column. No lock is held, so there's no blocking. The vast
> majority of updates succeed on the first try. Only on the rare conflict do we need to retry.
>
> The key trade-off: pessimistic locking is safe but reduces throughput (lock contention at
> high concurrency). Optimistic locking is high-throughput but causes retries under high contention.
> For Ticket Booking during a Coldplay concert drop, contention on popular seats is near 100% —
> pessimistic wins. For a SaaS app where users are updating their own isolated records,
> optimistic wins."

---

## PART 5 — DECISION FRAMEWORK

```
Is the data highly contended?
(multiple users frequently competing for the same row)
     │
     ├── YES ──► Use Pessimistic Locking (SELECT FOR UPDATE)
     │           Examples: seat booking, inventory deduction,
     │           flash sale limited stock, bank account transfer
     │
     └── NO ──► Is conflict rate < 10%?
                    │
                    ├── YES ──► Use Optimistic Locking (@Version)
                    │           Examples: user profile update,
                    │           CMS content editing, config updates
                    │           (most normal CRUD operations)
                    │
                    └── NO ──► Rethink the data model
                               Maybe use a queue (one writer at a time)
                               or partition data to reduce contention
```

---

## PART 6 — DEADLOCK PREVENTION RULES

```
Rule 1: Always lock rows in the same order across all transactions
─────────────────────────────────────────────────────────────────
  WRONG:
    Transaction A: lock account 100, then lock account 200
    Transaction B: lock account 200, then lock account 100
    → Deadlock possible

  RIGHT:
    Always lock by account_id ascending:
    Transaction A: lock account 100, then lock account 200
    Transaction B: lock account 100, then lock account 200
    → B blocks on 100 until A finishes → no deadlock

Rule 2: Keep transactions short
──────────────────────────────
  WRONG:
    BEGIN
    SELECT FOR UPDATE   ← lock acquired
    call external API   ← takes 2s, lock held for 2s
    UPDATE
    COMMIT

  RIGHT:
    call external API first  ← no lock held
    BEGIN
    SELECT FOR UPDATE   ← lock acquired
    UPDATE              ← immediate
    COMMIT              ← lock released in <10ms

Rule 3: Never upgrade locks within a transaction
──────────────────────────────────────────────────
  WRONG:
    Transaction A: reads (shared lock), then tries UPDATE (exclusive lock)
    Transaction B: also holds shared lock on same row
    → Both waiting for each other to release shared lock before getting exclusive
    → Deadlock

  RIGHT:
    If you know you'll write: use FOR UPDATE from the start
    Don't read-then-upgrade
```

---

## QUICK REFERENCE CARD

```
┌─────────────────────┬───────────────────────┬───────────────────────┐
│                     │  Pessimistic Locking  │  Optimistic Locking   │
├─────────────────────┼───────────────────────┼───────────────────────┤
│ Mechanism           │ SELECT FOR UPDATE     │ WHERE version = N     │
│ Lock held?          │ Yes (until COMMIT)    │ No                    │
│ Conflict detection  │ At read time          │ At write time         │
│ On conflict         │ Block / wait          │ Fail, retry           │
│ Throughput          │ Lower (blocking)      │ Higher (no blocking)  │
│ Best for            │ High contention       │ Low contention        │
│ Deadlock risk       │ Yes (if not careful)  │ No (no locks held)    │
│ JPA/Hibernate       │ @Lock(PESSIMISTIC)    │ @Version              │
│ Example use case    │ Seat booking, payment │ Profile update, draft │
└─────────────────────┴───────────────────────┴───────────────────────┘
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Interviewers use concurrent-write scenarios (two users book the same seat, two transactions debit the same account) to probe whether you understand locking — the wrong answer here fails the interview.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **07 — Payment System** | PESSIMISTIC locking is required. Two concurrent debit requests on the same account: without SELECT FOR UPDATE, both threads read balance=1000, both approve an 800-debit, and the account goes negative. Money correctness requires acquiring the lock at read time so the second thread blocks until the first completes. |
| **11 — Ticket Booking** | PESSIMISTIC locking is required. Seat A10: two users click "Book" simultaneously. SELECT FOR UPDATE on the seat row ensures exactly one user gets it — the second transaction sees the committed state and fails gracefully. Without this, double-booking is near-certain under load. |
| **12 — Hotel Booking** | OPTIMISTIC locking is preferred. Room availability has lower contention than seats or bank accounts. Using @Version: read the row, attempt the update, if the version changed retry. Lower lock overhead gives better throughput, and the retry cost is acceptable at normal booking rates. |
| **19 — Stock Broker** | PESSIMISTIC locking for order matching. A market order matches against a limit order — both sides must be locked to calculate the fill price atomically. Lock acquisition in consistent order (lower order_id first) prevents deadlocks when two matching threads process the same pair. |

**Architect's one-liner for the interview:**
*"Use pessimistic locking when the cost of a conflict (double booking, negative balance) is higher than the cost of waiting; use optimistic locking when conflicts are rare and retrying is cheap."*
