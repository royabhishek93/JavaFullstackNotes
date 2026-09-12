# Interview Guide: Concurrency Control in Distributed Systems (Optimistic vs. Pessimistic Concurrency Control)

## 🗣️ The Interview Scenario

> "Three users simultaneously try to book the same movie theater seat. Your first instinct might be to slap a `synchronized` block around the booking logic — explain why that doesn't work once your service is horizontally scaled across multiple machines. Then walk me through optimistic vs. pessimistic concurrency control, and tell me: what are the four transaction isolation levels, which specific consistency problem does each one solve, and which of the two concurrency control strategies is deadlock-prone?"

This is a favorite in both LLD (parking lot / seat booking) and HLD interviews specifically because the naive answer (`synchronized`) reveals whether a candidate understands the difference between **in-process** concurrency and **cross-process/distributed** concurrency.

## 🏗️ Architect's Explanation (For a New Developer)

Picture three people trying to book the exact same movie seat at the exact same moment. All three read "seat is FREE" simultaneously, all three then write "seat is BOOKED," and all three get a success response. That's the **critical section** problem: multiple concurrent requests reading-then-writing a **shared resource** without coordination, causing an incorrect outcome (in this case, the same seat allocated three times).

The instinctive fix in a single Java process is a `synchronized` block — it works because a `synchronized` block coordinates **threads within one process**. But in a distributed system, your service is likely running as **multiple separate processes on multiple separate machines**, each behind a load balancer. `synchronized` has zero visibility across process boundaries — it simply cannot stop Machine-2's thread from racing Machine-1's thread. This is exactly why **distributed concurrency control** exists — you need a mechanism that works across machines, and that mechanism lives at the **database** layer.

There are two competing philosophies for distributed concurrency control:
- **Pessimistic concurrency control**: assume conflicts *will* happen, so lock the data up front before anyone else can touch it, and make everyone else wait.
- **Optimistic concurrency control**: assume conflicts are *rare*, let everyone read and compute freely, but validate before the final write — and if someone else changed the data in the meantime, reject and retry.

To actually understand *how* these are implemented, you first need three foundational building blocks: **what a transaction is for**, **the two types of DB locks (shared vs. exclusive)**, and **the four isolation levels** — each of which solves a specific, named consistency problem.

## 📊 Visualize It

**Optimistic Concurrency Control — version-based conflict detection:**

```
Time →   T1 reads row (version=1)         T2 reads row (version=1)
              │                                  │
         [computes new value]              [computes new value]
              │                                  │
         SELECT FOR UPDATE                        │
         checks: DB version == 1? ✔ YES            │
         → UPDATE, version becomes 2, COMMIT        │
                                            SELECT FOR UPDATE
                                            checks: DB version == 1? ✖ NO (it's now 2!)
                                            → VALIDATION FAILS → ROLLBACK → retry
```

**Pessimistic Concurrency Control — the classic Deadlock:**

```
T1: holds lock on A ──wants lock on B──► [WAITING for T2 to release B]
T2: holds lock on B ──wants lock on A──► [WAITING for T1 to release A]

           T1 waits on T2, T2 waits on T1  →  DEADLOCK
           (both transactions must be aborted to break the cycle)
```

## 🔧 Deep Dive: How It Actually Works

### Why `synchronized` Fails in Distributed Systems
`synchronized` coordinates multiple **threads within one process**. In a microservices deployment, the "same service" typically runs as **multiple independent processes** across **multiple machines** behind a load balancer — e.g., User-1's request lands on Machine-1, User-2's on Machine-2, User-3's on Machine-3, all executing the same critical section in parallel. Since each machine's `synchronized` lock is local to its own JVM process, it provides **zero cross-machine coordination** — the race condition on the shared DB resource still occurs exactly as if no lock existed at all.

### Foundation 1: What Transactions Are For — Integrity
A transaction groups multiple DB statements so that **either all succeed or all roll back**, preserving consistency. Worked example: debit ₹20 from A, credit ₹20 to B. If the credit step fails, the transaction **rolls back** the already-successful debit step too, restoring A to its original state — this is what prevents the DB from ending up in an inconsistent in-between state (money vanished from A without appearing in B).

### Foundation 2: DB Locking — Shared vs. Exclusive Locks
- **Shared Lock (S)** — generally used for **reads**. Multiple transactions can hold a shared lock on the same row simultaneously and all read it concurrently. However, while any shared lock exists on a row, **no transaction can acquire an exclusive lock** on it (writes are blocked until all readers release their shared locks).
- **Exclusive Lock (X)** — generally used for **writes**. Only **one** transaction can hold an exclusive lock on a row. While held, **no other transaction can acquire either a shared lock (read) or an exclusive lock (write)** on that row — it's fully locked out to everyone else.

### Foundation 3: The Four Isolation Levels & The Three Problems They Solve
Three named consistency problems motivate the four isolation levels:

1. **Dirty Read** — Transaction A reads data that Transaction B has written but **not yet committed**. If B later rolls back, A has now acted on data that never actually existed in the committed DB state.
2. **Non-Repeatable Read** — Transaction A reads the *same row* multiple times within one transaction and gets **different values** each time, because another transaction committed a change to that row in between A's reads.
3. **Phantom Read** — Transaction A runs the *same range query* multiple times within one transaction and gets a **different set of rows** each time, because another transaction inserted (or deleted) a row matching that range in between.

| Isolation Level | Locking Strategy | Dirty Read | Non-Repeatable Read | Phantom Read | Concurrency |
|---|---|---|---|---|---|
| **Read Uncommitted** | No locks acquired at all (read or write) | ✅ Possible | ✅ Possible | ✅ Possible | Highest |
| **Read Committed** | Shared lock: acquired & released immediately after read. Exclusive lock: held until end of transaction. | ❌ Solved | ✅ Possible | ✅ Possible | High |
| **Repeatable Read** | Shared lock: held until end of transaction (not released early). Exclusive lock: held until end of transaction. | ❌ Solved | ❌ Solved | ✅ Possible | Medium |
| **Serializable** | Same as Repeatable Read, **plus a range lock** covering the queried range (and nearby values) held until end of transaction. | ❌ Solved | ❌ Solved | ❌ Solved | Lowest |

- **Read Uncommitted** is only safe for **pure-read applications** — the moment writes are involved, all three problems (dirty read, non-repeatable read, phantom read) are possible, making it unsafe for transactional workloads that write data.
- **Read Committed** solves dirty reads specifically because an exclusive lock is held for the writer's *entire* transaction — so a reader can only ever see a row once it's actually committed (or the writer rolled back and the reader waits/sees the prior committed value).
- **Repeatable Read** additionally solves non-repeatable reads by **holding the shared lock for the reader's entire transaction too** — this blocks any other transaction from acquiring the exclusive lock needed to change that row until the reader's transaction finishes.
- **Serializable** additionally solves phantom reads via a **range lock**: when a transaction queries a range (e.g., "ID between 1 and 3"), it locks not just the matching rows but the **surrounding range itself**, preventing any new row from being inserted into that range until the transaction completes.

### Optimistic Concurrency Control (OCC)
- **Typically pairs with the Read Committed isolation level.**
- Mechanism: **versioning.** Every row has a version number (some DBs like MySQL track this natively; others like Oracle require you to add and manually increment a version column on every update).
- **Flow:**
  1. Transaction reads a row and its version (e.g., version = 1), releasing any shared lock immediately after reading (multiple transactions can read concurrently, no blocking).
  2. Transaction computes the intended update in application logic.
  3. Before writing, it issues a `SELECT FOR UPDATE` (acquiring an exclusive lock) and performs **version validation**: does the DB's current version still match the version that was originally read?
  4. **If versions match** → proceed with the update, increment the version, commit, release the lock.
  5. **If versions don't match** (meaning some other transaction updated the row in between) → **validation fails, roll back, and retry** the whole operation from scratch.
- **Why it has no deadlock risk:** since read locks are released immediately and only a brief exclusive lock is taken right before the final write (with validation, not blocking, handling conflicts), transactions never hold two competing locks simultaneously waiting on each other.
- **Best suited for:** low-conflict scenarios — "less chance that concurrency suddenly comes" — where most transactions won't actually collide, so retries are rare and the higher concurrency/throughput of OCC pays off.

### Pessimistic Concurrency Control (PCC)
- **Typically pairs with Repeatable Read or Serializable isolation levels.**
- Mechanism: locks are acquired **up front and held for the duration**, not released early — this inherently serializes conflicting transactions (whichever gets the lock first proceeds; others must wait their turn).
- **The defining risk: Deadlock.** Worked example: Transaction-1 wants to read A then write B; Transaction-2 wants to read B then write A. If T1 locks A and T2 locks B simultaneously, then T1 waits for T2 to release B (to write it) while T2 waits for T1 to release A (to write it) — **both wait on each other forever**, and both transactions must eventually be **aborted** to break the cycle.
- **Comparison recap:** the same "read A write B / read B write A" scenario under **optimistic** concurrency control has **no deadlock**, because shared locks are released immediately after reading, so by the time each transaction reaches its write step, the other transaction's read lock is already gone — the write locks can be acquired without contention.

## 🔥 Real Production Incident & Fix

**What broke:** A ticket-booking platform used a naive **pessimistic locking** approach (`SELECT ... FOR UPDATE` under Serializable isolation) for its seat-reservation flow, where the booking transaction would read the seat row, then — in the same transaction — check and update a related "user wallet balance" row for payment, in that fixed order. A newly added refund-processing job ran the *reverse* order: lock the wallet row first, then lock the seat row to reverse a booking. During a high-traffic release, the system started throwing a spike of transaction timeouts and aborts during peak booking windows.

**How it was detected:** Application logs showed a surge of database driver exceptions matching a deadlock signature (e.g., PostgreSQL's `40P01 deadlock detected` error code), and the DB's own deadlock log (`pg_stat_activity` combined with `deadlock_timeout` logging) confirmed cycles between the booking transaction and the refund transaction, each holding a lock the other needed.

**Root cause:** Two different code paths (booking flow and refund flow) acquired locks on the **same two resources (seat row, wallet row) in opposite orders**, creating the exact circular-wait condition described in the deadlock scenario above — a textbook lock-ordering bug that pessimistic locking is especially prone to when different transactions don't agree on a consistent lock acquisition order.

**The fix:** The team enforced a **strict, consistent lock ordering rule** across all transactions touching both resources — always lock the seat row before the wallet row, regardless of which business flow initiated the transaction — which structurally eliminates the possibility of the circular wait. For the specific refund flow (which rarely conflicts with fresh bookings for the *same* seat once it's already been reserved), they additionally migrated it to **optimistic concurrency control** using a version column on the wallet table, since refunds are a low-conflict scenario well-suited to OCC's retry-on-conflict model instead of blocking pessimistic locks.

```
BEFORE (inconsistent lock order → deadlock):        AFTER (consistent lock order + OCC for refunds):
Booking: lock(seat) → lock(wallet)                  Booking: lock(seat) → lock(wallet)   [same order]
Refund:  lock(wallet) → lock(seat)  ✖ CYCLE          Refund:  version-check(wallet), no lock ordering issue
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: If `synchronized` doesn't work across distributed processes, what's the actual mechanism that replaces it?**
Database-level locking (shared/exclusive locks tied to a transaction and isolation level) or application-level versioning (optimistic concurrency control) — both mechanisms live at the shared data-store layer that all your distributed process instances actually talk to, rather than relying on in-memory, per-process coordination like `synchronized`.

**Q2: Why does Read Committed solve dirty reads but not non-repeatable reads?**
Because under Read Committed, the **exclusive lock is held for the writer's entire transaction** (so nobody can read an uncommitted write — solving dirty reads), but the **reader's shared lock is released immediately after each individual read** — meaning nothing stops another transaction from committing a change between the reader's first and second read of the same row, which is exactly the non-repeatable read problem.

**Q3: How does a range lock under Serializable isolation actually prevent phantom reads?**
It locks not just the rows currently matching the query's range condition, but the range itself — so any transaction attempting to `INSERT` a new row that would fall within that locked range is blocked until the range lock is released, preventing the "new row silently appears on re-query" scenario that defines a phantom read.

**Q4: What determines whether you should reach for optimistic vs. pessimistic concurrency control in a real design?**
The expected conflict rate for the specific resource/operation. Low-conflict, high-read scenarios (most requests won't actually collide) favor optimistic concurrency control for its higher throughput and lack of deadlock risk, accepting occasional retries. High-conflict scenarios, or ones where a failed retry is unacceptable/expensive, favor pessimistic locking despite its deadlock risk and lower concurrency, because retries under heavy contention with OCC could thrash repeatedly.

**Q5: Does optimistic concurrency control eliminate the need for any locking at all?**
No — it still briefly acquires an exclusive lock (via something like `SELECT FOR UPDATE`) right before the final write, specifically to perform the version check and commit atomically. What it eliminates is holding a lock for the *entire read-compute-write* window; the lock is only held for the short final validate-and-commit step.

**Q6: In the deadlock example, why does aborting one of the two transactions actually resolve the deadlock?**
Aborting releases that transaction's held locks, which frees up the resource the *other* transaction was waiting on — breaking the circular wait. Both transactions can't simply "wait a bit longer" because neither will ever release its lock until it acquires the other's lock first; the cycle can only be broken by force-releasing one side.

## 🔑 Key Takeaway
Say this out loud: **"`synchronized` only coordinates threads within a single process, so distributed systems need database-level concurrency control — pessimistic locking (pairs with Repeatable Read/Serializable) prevents conflicts up front at the cost of deadlock risk, while optimistic concurrency control (pairs with Read Committed, using row versioning) allows free concurrent reads and only validates-and-retries at write time, trading occasional retries for higher throughput and zero deadlock risk."**
