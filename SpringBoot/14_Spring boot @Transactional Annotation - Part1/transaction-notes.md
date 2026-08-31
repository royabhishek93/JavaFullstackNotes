# Spring Boot @Transactional — Complete Notes

---

## Part 1 — What is a Transaction and Why Does @Transactional Exist?

### The Problem: Critical Sections

A critical section is a code segment where a shared resource is being accessed AND modified.

**Cab booking analogy:** A cab (id=10001, status="available") is in the DB. Four users try to book it at the same millisecond. All four read "available", all four write "booked", all four get a confirmation — but there is only one cab. This is data inconsistency.

Transactions are the solution.

---

### ACID — What a Transaction Guarantees

| Property | Plain English |
|---|---|
| **Atomicity** | All-or-nothing. If step 2 fails, step 1 is undone too. |
| **Consistency** | DB must be valid before AND after. No half-states. |
| **Isolation** | Parallel transactions don't interfere with each other. |
| **Durability** | Once committed, data survives crashes. |

**Money transfer analogy (Atomicity):** A has ₹10, B has ₹20. Transfer ₹5 from A to B.
Step 1: debit A. Step 2: credit B. If step 2 crashes — A is NOT debited. Everything rolls back.

---

### The Boilerplate Problem

Without Spring, every DB method needs this wrapper:

```java
connection.beginTransaction();
try {
    // your 3 lines of actual business logic
    connection.commit();
} catch (Exception e) {
    connection.rollback();
}
```

500 service methods = 500 copies of this wrapper. The business logic is 3 lines; the plumbing is 10.

---

### How @Transactional Fixes It (AOP Under the Hood)

Spring uses **AOP (Aspect-Oriented Programming)**. You write:

```java
@Transactional
public void transferMoney(String from, String to, int amount) {
    debit(from, amount);
    credit(to, amount);
}
```

Spring intercepts this method using `TransactionalInterceptor`. Internally:

```
1. begin transaction
2. → call YOUR method ←
3. if exception → rollback
4. if success → commit
```

You only write step 2. Spring owns the other three.

**Class-level vs method-level:**
- `@Transactional` on the **class** → all public methods get it.
- `@Transactional` on a **method** → only that method gets it.
- Private methods are **never** covered.

---

## Part 2 — Transaction Managers, Declarative vs Programmatic, and Propagation

### Transaction Manager Hierarchy

| Implementation | When to use |
|---|---|
| `DataSourceTransactionManager` | Raw JDBC / manual SQL |
| `JpaTransactionManager` | JPA entities (most Spring Boot apps) |
| `HibernateTransactionManager` | Hibernate ORM directly |
| `JtaTransactionManager` | Distributed transactions across multiple DBs |

Spring Boot auto-picks the right one. You usually don't configure it manually.

---

### Declarative vs Programmatic

**Declarative** = just put `@Transactional` on the method. Simple. Covers the entire method.

**Programmatic** = manually control the transaction in code. Needed when:

```
1. DB operation        ← need transaction
2. External API call   ← do NOT hold DB connection here (3-4 seconds!)
3. DB operation        ← need transaction
```

If you use `@Transactional` on this whole method, the DB connection is held open during the slow API call. Under load, the connection pool gets exhausted.

**Programmatic with TransactionTemplate (the clean way):**

```java
@Autowired TransactionTemplate transactionTemplate;

public void updateUser() {
    // Step 1 — transaction only here
    transactionTemplate.execute(status -> {
        // DB operation
        return null;
    });

    callExternalAPI(); // no transaction held here

    // Step 3 — new transaction only here
    transactionTemplate.execute(status -> {
        // DB operation
        return null;
    });
}
```

---

### Propagation — The Most Asked Interview Topic

**Question it answers:** Method A (with a transaction) calls Method B (also `@Transactional`). Should B join A's transaction or create its own?

| Propagation | Parent exists | Parent does NOT exist |
|---|---|---|
| **REQUIRED** *(default)* | Join the existing transaction | Create a new one |
| **REQUIRES_NEW** | Suspend parent, create new, resume after | Create a new one |
| **SUPPORTS** | Join the existing transaction | Run without any transaction |
| **NOT_SUPPORTED** | Suspend parent, run without transaction | Run without any transaction |
| **MANDATORY** | Join the existing transaction | Throw exception |
| **NEVER** | Throw exception | Run without any transaction |

**Usage:**
```java
@Transactional(propagation = Propagation.REQUIRES_NEW)
public void methodB() { ... }
```

---

## Part 3 — Isolation Levels

### One-Line Definition

> Isolation level = how visible one transaction's uncommitted changes are to other concurrent transactions.

```java
@Transactional(isolation = Isolation.READ_COMMITTED)
public void bookSeat() { ... }
```

---

### The Three Concurrency Problems

**1. Dirty Read** — reading uncommitted data that might get rolled back

```
T1: B updates id=1 to "booked" (NOT committed yet)
T2: A reads id=1 → sees "booked"
T3: B ROLLS BACK → id=1 is "free" again
Result: A read data that never officially existed
```

**2. Non-Repeatable Read** — same row, same query, different value

```
T1: A reads id=1 → "free"
T2: B updates id=1 to "booked" and COMMITS
T3: A reads id=1 again → "booked"  ← different answer!
```

**3. Phantom Read** — same range query, different number of rows

```
T1: A queries WHERE id BETWEEN 1 AND 5 → gets 2 rows
T2: B inserts id=3 and COMMITS
T3: A runs the same query again → gets 3 rows  ← new row appeared!
```

---

### Locks (How Isolation is Enforced by the DB)

| Lock | Also called | Who holds it | Others can read? | Others can write? |
|---|---|---|---|---|
| **Shared (S)** | Read lock | Multiple at once | Yes | No |
| **Exclusive (X)** | Write lock | Only ONE | No | No |

You never write locking code. You declare the isolation level; the DB handles all locking internally.

---

### The Four Isolation Levels

| Level | Dirty Read | Non-Repeatable Read | Phantom Read | Concurrency |
|---|---|---|---|---|
| **READ_UNCOMMITTED** | Not solved | Not solved | Not solved | Highest |
| **READ_COMMITTED** | Solved | Not solved | Not solved | High |
| **REPEATABLE_READ** | Solved | Solved | Not solved | Medium |
| **SERIALIZABLE** | Solved | Solved | Solved | Lowest |

**READ_UNCOMMITTED** — no locks at all. All three problems possible. Only for purely read-only, static data.

**READ_COMMITTED** — takes a shared lock to read, releases it immediately. Solves dirty reads. Doesn't solve non-repeatable reads (lock released too soon).

**REPEATABLE_READ** (MySQL default) — holds the shared lock for the entire transaction duration. Solves non-repeatable reads. Doesn't stop new rows being inserted.

**SERIALIZABLE** — adds a range lock. Nobody can insert into a range you've queried. Fully solves phantom reads but concurrency drops severely.

**Practical guide:**
- Most apps → **READ_COMMITTED** or **REPEATABLE_READ**
- SERIALIZABLE → almost never used in production
- READ_UNCOMMITTED → only for purely static read-only data

---

## Interview — REQUIRED vs REQUIRES_NEW

### How to Explain REQUIRED

> "REQUIRED is the default. It says — if a transaction already exists, join it. If not, create one.
>
> So if method A starts a transaction and calls method B (also REQUIRED), method B doesn't create a new transaction. It borrows A's. They're running inside the same unit of work.
>
> If method B fails, the entire transaction rolls back — including everything method A already did. They're tied together. One fails, both fail."

**Real use case:** Bank transfer. Method A debits the sender, method B credits the receiver. Both must succeed or both must fail — same transaction.

---

### How to Explain REQUIRES_NEW

> "REQUIRES_NEW is the opposite mindset. It says — I don't care if a transaction already exists. Suspend it, give me a fresh independent transaction.
>
> Method A starts a transaction, calls method B (REQUIRES_NEW) — method B pauses A's transaction, runs its own transaction from scratch, commits or rolls back on its own, and then A's transaction resumes.
>
> Method B's outcome is completely independent of A. B can commit even if A later rolls back."

**Real use case:** Audit logging. Method A processes a payment, method B logs the attempt. With REQUIRED, a rollback in A also deletes the audit log. With REQUIRES_NEW, the audit log commits independently regardless of what A does.

---

### One-Line Contrast

```
REQUIRED     → share fate.       One transaction, one commit, one rollback.
REQUIRES_NEW → independent fate. Two separate transactions, each commits/rolls back on its own.
```

---

## Deep Dive — How the Proxy Looks for REQUIRED vs REQUIRES_NEW

### CGLIB Proxy for REQUIRED

```java
public class OrderService$$SpringCGLIB extends OrderService {

    @Override
    public void placeOrder(Order order) {

        ConnectionHolder existing = TransactionSynchronizationManager.getResource(dataSource);

        if (existing != null && existing.isTransactionActive()) {
            // Transaction already exists → just USE IT, do nothing extra
            // No new connection. No new begin. Just join.
            super.placeOrder(order);  // runs on the SAME connection
            // No commit here — outer transaction owns the commit

        } else {
            // No transaction → create one
            Connection conn = hikariPool.getConnection();
            conn.setAutoCommit(false);
            TransactionSynchronizationManager.bindResource(dataSource, conn);

            try {
                super.placeOrder(order);
                conn.commit();
            } catch (RuntimeException e) {
                conn.rollback();
                throw e;
            } finally {
                TransactionSynchronizationManager.unbindResource(dataSource);
                conn.close();
            }
        }
    }
}
```

If a transaction already exists, REQUIRED does **nothing** — no new connection, no new begin. Just runs on the existing connection.

---

### CGLIB Proxy for REQUIRES_NEW

```java
public class AuditService$$SpringCGLIB extends AuditService {

    @Override
    public void log(Long orderId) {

        // Step 1 — SUSPEND whatever is currently on the thread
        ConnectionHolder suspended = TransactionSynchronizationManager.getResource(dataSource);
        if (suspended != null) {
            TransactionSynchronizationManager.unbindResource(dataSource);
            // ThreadLocal is now EMPTY — outer connection saved in local variable
        }

        // Step 2 — get a BRAND NEW connection from the pool
        Connection newConn = hikariPool.getConnection();  // e.g. conn#99
        newConn.setAutoCommit(false);
        TransactionSynchronizationManager.bindResource(dataSource, newConn);

        // Step 3 — run YOUR code on the new independent connection
        try {
            super.log(orderId);    // runs on conn#99, NOT conn#42
            newConn.commit();      // commits independently
        } catch (RuntimeException e) {
            newConn.rollback();
            throw e;
        } finally {
            TransactionSynchronizationManager.unbindResource(dataSource);
            newConn.close();

            // Step 4 — RESTORE the outer transaction
            if (suspended != null) {
                TransactionSynchronizationManager.bindResource(dataSource, suspended);
                // conn#42 is back on the thread — outer TX resumes exactly as before
            }
        }
    }
}
```

---

### Visual Comparison

```
REQUIRED
────────
placeOrder()  ──── conn#42 ──────────────────────────► commit/rollback
                      │
              log()   │  (joins same connection, no separate commit)
                      └── same conn#42


REQUIRES_NEW
────────────
placeOrder()  ── conn#42 ──[SUSPENDED]──────────────────────────► commit/rollback
                                │
              log()             └── conn#99 (new) ──► commit (independent)
                                    conn#42 RESTORED after log() completes
```

| | REQUIRED | REQUIRES_NEW |
|---|---|---|
| ThreadLocal during inner method | still has `conn#42` | emptied, then `conn#99` |
| Connections open at once | 1 | 2 |
| Inner commit | doesn't happen — outer commits both | happens immediately |
| Outer rollback affects inner | yes — same transaction | no — inner already committed |

---

## What Happens to Method A's Connection When Method B Uses REQUIRES_NEW?

Full step-by-step:

```
Method A starts
  → conn#42 acquired from pool
  → conn#42 bound to ThreadLocal
  → ThreadLocal = { DataSource → conn#42 }

Method A does some DB work on conn#42...

Method A calls Method B (REQUIRES_NEW)

  Proxy SUSPENDS:
    → conn#42 UNBOUND from ThreadLocal
    → conn#42 saved in local variable: suspendedHolder
    → ThreadLocal = { }  ← EMPTY

  New connection acquired:
    → conn#99 acquired from pool
    → conn#99 bound to ThreadLocal
    → ThreadLocal = { DataSource → conn#99 }

  Method B runs on conn#99...
  Method B commits conn#99
  conn#99 returned to pool

  Proxy RESUMES:
    → conn#99 unbound
    → suspendedHolder (conn#42) RE-BOUND to ThreadLocal
    → ThreadLocal = { DataSource → conn#42 }  ← exactly as before

Cursor returns to Method A
  → Method A continues using conn#42
  → All Method A's uncommitted work is still there (was never touched)
  → Method A commits or rolls back conn#42 as normal
```

**conn#42 was never closed, never committed, never rolled back during Method B's execution.**
It was just sitting in a local variable (`suspendedHolder`), completely untouched.

Think of it like putting a book face-down on the table to answer a phone call. The page you were on is still there when you pick it back up.

---

### What If Method B Throws?

```
Method B throws RuntimeException
  → conn#99 rolls back (Method B's work undone)
  → conn#99 returned to pool
  → conn#42 RESTORED to ThreadLocal  ← this still happens regardless

Exception propagates to Method A:
  → Method A's proxy sees the exception
  → conn#42 rolls back (Method A's work also undone)
```

If Method A **catches** Method B's exception:

```java
@Transactional
public void methodA() {
    orderRepo.save(order);       // on conn#42

    try {
        auditService.log(id);    // REQUIRES_NEW → conn#99 commits then throws
    } catch (Exception e) {
        // swallowed — Method A continues
    }

    orderRepo.markComplete(id);  // still on conn#42, works fine
    // conn#42 commits → order saved ✅
}
```

Method B rolled back on conn#99. Method A never knew. conn#42 is fine throughout.

---

## Mental Model Summary

```
@Transactional           → Spring wraps your method with begin/commit/rollback (AOP + CGLIB)
ThreadLocal              → each thread has its own DB connection — 200 users = 200 connections
propagation = REQUIRED   → share the existing connection and transaction (shared fate)
propagation = REQUIRES_NEW → park the existing connection, open a new one (independent fate)
suspend                  → unbind conn from ThreadLocal, save in local variable
resume                   → re-bind the saved conn back to ThreadLocal
isolation                → how visible your uncommitted work is to parallel transactions
TransactionTemplate      → use when external API call sits between two DB operations
```

---

## Isolation Levels — Internally How Each One Works

### Foundation: Two Types of Locks

When a transaction touches a row in the DB, it puts a lock on it.

| Lock | Who can hold it | Can others READ? | Can others WRITE? |
|---|---|---|---|
| **Shared (S) — Read Lock** | Multiple transactions at once | Yes | No |
| **Exclusive (X) — Write Lock** | Only ONE transaction | No | No |

You never write locking code. The DB applies locks automatically based on the isolation level you declare.

---

### How Spring Sets Isolation Level Internally

When you write:

```java
@Transactional(isolation = Isolation.READ_COMMITTED)
public void bookSeat() { ... }
```

The CGLIB proxy does this before calling your method:

```
1. Get connection from HikariCP pool
2. conn.setAutoCommit(false)          ← start transaction mode
3. conn.setTransactionIsolation(2)    ← 2 = READ_COMMITTED constant
4. Bind connection to ThreadLocal
5. Call YOUR method
6. commit() or rollback()
7. Unbind from ThreadLocal
8. Return connection to pool
```

The isolation level is a setting on the **connection itself**. The DB applies the appropriate locking for every SQL statement in that transaction.

---

### The Three Problems Isolation Levels Solve

**Problem 1: Dirty Read** — reading uncommitted data that might get rolled back

```
T1: B updates row → "booked"  (NOT committed)
T2: A reads row   → sees "booked"
T3: B ROLLS BACK  → row back to "free"
Result: A used data that never officially existed
```

**Problem 2: Non-Repeatable Read** — same row, same query, different value

```
T1: A reads row → "free"
T2: B updates row → "booked" and COMMITS
T3: A reads same row again → "booked"   ← different!
```

**Problem 3: Phantom Read** — same range query, different number of rows

```
T1: A queries WHERE id < 5 → gets 2 rows
T2: B inserts id=3 and COMMITS
T3: A runs same query → gets 3 rows   ← new row appeared!
```

---

### READ_UNCOMMITTED — Internally

**No locks on reads. Anyone can read anything, even uncommitted.**

```
Transaction A reads a row:
  → Takes NO shared lock
  → Reads whatever is in the row right now (even uncommitted)

Transaction B writes a row:
  → Takes exclusive lock
  → Holds until commit/rollback
```

Timeline:
```
B starts writing: row = "booked"  (exclusive lock, NOT committed)
A reads row: → sees "booked"   ← no lock check at all
B rolls back: row = "free"
A used "booked" which never existed   ← DIRTY READ
```

- Solves: **Nothing**
- Concurrency: **Maximum** (zero blocking)
- Use when: Purely read-only static data where approximate values are fine

---

### READ_COMMITTED — Internally

**Take shared lock → read → release it immediately.**

```
Transaction A reads a row:
  → Tries to acquire SHARED lock
  → If another TX holds EXCLUSIVE lock (writing) → A WAITS
  → Once exclusive lock released (other TX committed/rolled back):
      → A acquires shared lock
      → A reads (only committed data now)
      → A releases shared lock IMMEDIATELY

Transaction B writes a row:
  → Takes exclusive lock
  → Holds until commit/rollback
```

**Why it solves Dirty Read:**
```
B writing: holds EXCLUSIVE lock
A tries to read: wants SHARED lock → BLOCKED (exclusive lock exists)
B COMMITS: exclusive lock released
A acquires shared lock → reads committed value   ✅
```

**Why it does NOT solve Non-Repeatable Read:**
```
A reads row: shared lock → "free" → RELEASES lock immediately
B updates row: no conflict → writes "booked" → COMMITS
A reads same row again: new shared lock → "booked"   ← different!   ❌
```
The lock is released too quickly — row is unprotected between A's two reads.

- Solves: **Dirty Read only**
- Concurrency: **High**
- Default in: **PostgreSQL**. Most common in production.

---

### REPEATABLE_READ — Internally

**Take shared lock and HOLD IT for the entire transaction duration.**

```
Transaction A reads a row:
  → Acquires shared lock
  → Reads value
  → KEEPS the shared lock (does NOT release it)
  → Lock held until A's transaction commits or rolls back

Transaction B tries to write that same row:
  → Tries to acquire exclusive lock
  → BLOCKED — A still holds the shared lock
  → B must wait until A finishes
```

**Why it solves Non-Repeatable Read:**
```
A reads row: shared lock → "free" → HOLDS the lock
B tries to update: exclusive lock → BLOCKED
A reads same row again: lock still held → "free"   ✅ same value
A finishes: shared lock released
B can now write
```

**Why it does NOT solve Phantom Read:**
The shared lock is on **existing rows only**. New rows have no lock yet.

```
A queries WHERE id < 5 → shared locks on id=1, id=3 only
B inserts id=2 (new row) → no lock on id=2 → INSERT succeeds → COMMITS
A runs same query → now gets id=1, id=2, id=3   ← new row!   ❌
```

- Solves: **Dirty Read + Non-Repeatable Read**
- Concurrency: **Medium**
- Default in: **MySQL**

---

### SERIALIZABLE — Internally

**Take shared lock + RANGE LOCK on the entire query range.**

```
Transaction A runs a range query WHERE id < 5:
  → Acquires shared lock on existing rows (id=1, id=3)
  → ALSO acquires RANGE LOCK on the entire range (anything where id < 5)
  → Range lock means: nobody can insert, update, or delete any row in this range

Transaction B tries to INSERT id=2 (falls inside range id < 5):
  → Tries to write → BLOCKED by the range lock
  → Must wait until A's transaction finishes
```

**Why it solves Phantom Read:**
```
A queries WHERE id < 5 → range lock on id < 5
B tries to insert id=2 → BLOCKED
A runs same query again → still gets id=1, id=3   ✅ no new rows
A finishes: range lock released
B can now insert
```

The range lock protects not just existing rows but the entire space — including rows that don't exist yet.

- Solves: **All three problems**
- Concurrency: **Lowest** — transactions block each other frequently
- Use when: Rarely. Only when your query result set must stay 100% stable.

---

### Side-by-Side Comparison

```
Level               Lock on READ          Lock released     New rows blocked?
────────────────────────────────────────────────────────────────────────────────
READ_UNCOMMITTED    None                  N/A               No
READ_COMMITTED      Shared                Immediately       No
REPEATABLE_READ     Shared                End of TX         No (range not locked)
SERIALIZABLE        Shared + Range        End of TX         Yes (range locked)
```

```
Level               Dirty Read   Non-Repeatable Read   Phantom Read   Concurrency
──────────────────────────────────────────────────────────────────────────────────
READ_UNCOMMITTED    ❌           ❌                    ❌             Max
READ_COMMITTED      ✅           ❌                    ❌             High
REPEATABLE_READ     ✅           ✅                    ❌             Medium
SERIALIZABLE        ✅           ✅                    ✅             Low
```

---

### Practical Decision Guide

```
Most apps (default)          → READ_COMMITTED
Need same row value twice    → REPEATABLE_READ
Need stable range queries    → SERIALIZABLE (rare)
Never use in production      → READ_UNCOMMITTED
```
