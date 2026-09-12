# Spring Boot `@Transactional` — Isolation Levels and Their Types

## What is this? (Plain English)

Think of a shared Google Doc that two people are editing at the same time. Isolation level is the rule that decides **what one editor is allowed to see of the other editor's half-finished, unsaved changes** — can you see their draft text before they hit "save," can your view suddenly change mid-read because they just saved, or are you guaranteed a completely stable, frozen snapshot no matter what they do? Database transaction isolation is the same idea applied to concurrent database transactions: **it tells how the changes made by one transaction are visible to another transaction running in parallel.**

In Spring Boot, you configure this with the `isolation` attribute on `@Transactional`:

```java
@Transactional(isolation = Isolation.READ_COMMITTED)
```

There are four isolation levels: `READ_UNCOMMITTED`, `READ_COMMITTED`, `REPEATABLE_READ`, and `SERIALIZABLE`. If you don't specify one, Spring falls back to the **default isolation level of the underlying database** — this is not a fixed value; it depends entirely on which database you're using and can even change across database versions, so you must check your specific database's documentation rather than assuming. Most relational databases default to `READ_COMMITTED`, though some default to `REPEATABLE_READ`.

## The Problem It Solves

Isolation level exists to manage the trade-off between **concurrency** and **data consistency**:

- A weaker (looser) isolation level allows many transactions to run in parallel with little to no waiting — high concurrency, but more risk of seeing inconsistent/incorrect data.
- A stricter isolation level blocks other transactions more aggressively to guarantee consistency — very safe, but far fewer transactions can run in parallel at the same time.

There is no universally "best" choice — picking `READ_UNCOMMITTED` for the concurrency alone is dangerous unless your use case is read-only/static data, because it protects against nothing. The real skill is understanding **which specific data-correctness problem each isolation level prevents**, so you pick the weakest level that still avoids the problems that matter for your business logic.

Three concrete problems (anomalies) motivate the four isolation levels:

**1. Dirty Read** — Transaction A reads data that Transaction B has changed but not yet committed. If B then rolls back, A has read data that never really existed in the database.

```
Time  Transaction A                 Transaction B                 DB row (id=123)
T1    BEGIN                         BEGIN                         status = free
T2                                  UPDATE status = 'booked'      status = booked (uncommitted)
T3    READ id=123 -> "booked"                                     status = booked (uncommitted)
T4                                  ROLLBACK                      status = free (reverted)
```
Transaction A read `"booked"` — a value that was never actually committed to the database. That's a dirty read.

**2. Non-Repeatable Read** — Transaction A reads the same row more than once during its lifetime and gets a different value each time, because another transaction changed and committed that row in between A's reads.

```
Time  Transaction A                 Transaction B                 DB row (id=1)
T1    BEGIN                                                       status = free
T2    READ id=1 -> "free"                                         status = free
T3                                  BEGIN; UPDATE status='booked';
                                    COMMIT                        status = booked (committed)
T4    READ id=1 -> "booked"                                       status = booked
```
Same row, same query, two different answers within the same transaction A.

**3. Phantom Read** — Transaction A runs the same range query more than once and gets a different **set of rows**, because another transaction inserted a new row (matching the range condition) and committed in between.

```
Time  Transaction A                              Transaction B                 DB rows (id BETWEEN 0 AND 5)
T1    BEGIN                                                                    id=1(free), id=3(booked)
T2    READ WHERE id>0 AND id<5 -> rows [1,3]
T3                                                BEGIN; INSERT id=2;
                                                  COMMIT                       id=1, id=2(new), id=3
T4    READ WHERE id>0 AND id<5 -> rows [1,2,3]
```
The same query "phantom-ly" returns an extra row the second time.

### DB Locking Primer (needed to understand how isolation levels work)

```
Shared Lock (S) / Read Lock                  Exclusive Lock (X) / Write Lock
------------------------------               --------------------------------
- Multiple transactions CAN hold             - Only ONE transaction can hold it
  a shared lock on the same row              - Blocks ALL other transactions from
  at the same time                             reading OR writing that row
- Holders can only READ, never write         - Held by the transaction doing a write

Compatibility:
  Shared  + Shared    -> OK (both can read)
  Shared  + Exclusive  -> BLOCKED (must wait for shared lock to release)
  Exclusive + Shared   -> BLOCKED (must wait for exclusive lock to release)
  Exclusive + Exclusive-> BLOCKED (must wait for exclusive lock to release)
```

## Isolation-Level Hierarchy (least to most strict)

Each level up the ladder adds stricter locking, which eliminates exactly one more anomaly at the cost of lower concurrency.

*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

### ASCII fallback

```text
+-------------------+     +-------------------+     +-------------------+     +-------------------+
| READ_UNCOMMITTED  | --> | READ_COMMITTED    | --> | REPEATABLE_READ   | --> | SERIALIZABLE       |
| no locks at all   |     | S-lock: read-only |     | S-lock: held till |     | S+X-lock held till |
|                   |     |   released        |     |   end of txn      |     |   end of txn        |
| X: dirty read     |     | X-lock: held till |     | X-lock: held till |     | + RANGE LOCK over   |
| X: non-repeatable |     |   end of txn       |     |   end of txn      |     |   queried row range |
| X: phantom read   |     |                    |     |                    |     |                     |
|                   |     | OK: dirty read     |     | OK: dirty read     |     | OK: dirty read      |
|                   |     | X: non-repeatable  |     | OK: non-repeatable |     | OK: non-repeatable  |
|                   |     | X: phantom read    |     | X: phantom read    |     | OK: phantom read    |
+-------------------+     +-------------------+     +-------------------+     +-------------------+
   highest concurrency ---------------------------------------------------------> lowest concurrency
```

### Comparison Table: Isolation Level vs Anomaly

| Isolation Level    | Dirty Read | Non-Repeatable Read | Phantom Read | Read Lock Behavior                     | Write Lock Behavior         | Concurrency |
|---------------------|:----------:|:--------------------:|:-------------:|-----------------------------------------|-------------------------------|:-----------:|
| `READ_UNCOMMITTED`  | ❌ Possible | ❌ Possible           | ❌ Possible    | No lock taken at all                    | No lock taken at all          | Highest      |
| `READ_COMMITTED`    | ✅ Prevented | ❌ Possible          | ❌ Possible    | Shared lock, released right after read  | Exclusive, held till end of txn | High       |
| `REPEATABLE_READ`   | ✅ Prevented | ✅ Prevented         | ❌ Possible    | Shared lock, held till end of txn       | Exclusive, held till end of txn | Medium     |
| `SERIALIZABLE`      | ✅ Prevented | ✅ Prevented         | ✅ Prevented   | Shared lock + range lock, held till end of txn | Exclusive, held till end of txn | Lowest |

Why `REPEATABLE_READ` still allows phantom reads: its shared lock only covers the rows it has **already read**, not the entire range described by the query condition — so a brand-new row inserted by another transaction can still slip into the range and show up on a re-read. `SERIALIZABLE` closes this gap by locking the *entire queried range*, so no other transaction can insert a row that would match the condition until the transaction finishes.

## Key Code / Config

```java
@Service
public class BookingService {

    // No locks taken at all on read or write.
    // Only safe for read-only / static-data use cases — vulnerable to all three anomalies.
    @Transactional(isolation = Isolation.READ_UNCOMMITTED)
    public String readStatusUncommitted(Long id) {
        return bookingRepository.findStatusById(id);
    }

    // Shared lock on read (released immediately after the read completes).
    // Exclusive lock on write (held until commit/rollback).
    // Prevents dirty reads only.
    @Transactional(isolation = Isolation.READ_COMMITTED)
    public String readStatusCommitted(Long id) {
        return bookingRepository.findStatusById(id);
    }

    // Shared lock on read held until the end of the transaction.
    // Exclusive lock on write held until the end of the transaction.
    // Prevents dirty reads AND non-repeatable reads.
    @Transactional(isolation = Isolation.REPEATABLE_READ)
    public String readStatusTwiceRepeatable(Long id) {
        String first = bookingRepository.findStatusById(id);
        // ... other work happens here while the shared lock is held ...
        String second = bookingRepository.findStatusById(id);
        return first + " / " + second; // guaranteed to be identical
    }

    // Same locking as REPEATABLE_READ, plus a range lock over the queried row range.
    // Prevents dirty reads, non-repeatable reads, AND phantom reads.
    @Transactional(isolation = Isolation.SERIALIZABLE)
    public List<Booking> readRangeSerializable() {
        return bookingRepository.findByIdBetween(0L, 5L);
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void updateStatus(Long id, String newStatus) {
        // Exclusive lock acquired here, held until this method's transaction
        // commits or rolls back — no other transaction can read or write this row meanwhile.
        bookingRepository.updateStatus(id, newStatus);
    }
}
```

```java
public interface BookingRepository extends JpaRepository<Booking, Long> {

    String findStatusById(Long id);

    List<Booking> findByIdBetween(Long start, Long end);

    @Modifying
    @Query("UPDATE Booking b SET b.status = :status WHERE b.id = :id")
    void updateStatus(@Param("id") Long id, @Param("status") String status);
}
```

### Illustrating the anomalies with two concurrent transactions

```java
// Simulates the dirty-read scenario: Transaction B updates but rolls back,
// yet Transaction A (running READ_UNCOMMITTED) already saw the uncommitted value.
@Service
public class DirtyReadDemoService {

    @Transactional(isolation = Isolation.READ_UNCOMMITTED)
    public String transactionA_read(Long id) {
        return bookingRepository.findStatusById(id); // may read data that gets rolled back
    }

    @Transactional
    public void transactionB_updateThenRollback(Long id) {
        bookingRepository.updateStatus(id, "booked");
        throw new RuntimeException("simulated failure -> triggers rollback");
    }
}
```

```properties
# The isolation level is set purely through the @Transactional annotation above —
# no extra Spring Boot properties are required to enable it. The actual shared/exclusive
# locking logic lives inside the database's transaction manager, not in the application code;
# the application only ever issues plain SELECT / INSERT / UPDATE statements, and the
# isolation level tells the DB transaction manager which locks to take and when to release them.
```

## Important Concepts

- **Isolation Level**: Controls how/when changes made by one in-progress transaction become visible to another transaction running concurrently.
- **Dirty Read**: Reading another transaction's uncommitted changes; if that transaction rolls back, the read value never really existed.
- **Non-Repeatable Read**: Re-reading the same row within one transaction and getting a different value because another transaction committed a change in between.
- **Phantom Read**: Re-running the same range query within one transaction and getting a different set of rows because another transaction inserted (and committed) a matching row in between.
- **Shared Lock (S) / Read Lock**: Multiple transactions can hold it simultaneously; permits reading only, no writing.
- **Exclusive Lock (X) / Write Lock**: Only one transaction can hold it; blocks all other reads and writes on that row until released.
- **`READ_UNCOMMITTED`**: No locks at all; highest concurrency, vulnerable to all three anomalies; suitable only for read-only/static data.
- **`READ_COMMITTED`**: Shared lock released immediately after read, exclusive lock held till end of transaction; prevents only dirty reads.
- **`REPEATABLE_READ`**: Shared lock held till end of transaction; prevents dirty reads and non-repeatable reads, but not phantom reads.
- **`SERIALIZABLE`**: Adds a range lock on top of `REPEATABLE_READ`'s locking; prevents all three anomalies but has the lowest concurrency.
- **DB Transaction Manager**: The database-side component that actually acquires/releases shared and exclusive locks according to the configured isolation level — this locking logic is abstracted away from application code, which only ever writes plain SQL.

## Interview Q&A

**Q1: Why does `READ_UNCOMMITTED` suffer from all three anomalies?**
Because it doesn't take a shared lock while reading and doesn't hold an exclusive lock while writing (or holds none meaningfully) — with no locking at all, any transaction can read or write a row at any time, so dirty reads, non-repeatable reads, and phantom reads are all possible.

**Q2: If `READ_UNCOMMITTED` is so risky, why does it exist at all?**
It's useful when your use case is purely read-only against largely static data, where none of the three anomalies can realistically affect correctness — in exchange, you get the highest possible concurrency since no transaction ever waits on a lock.

**Q3: What's the practical difference between `READ_COMMITTED` and `REPEATABLE_READ`?**
`READ_COMMITTED` releases its shared (read) lock immediately after the read completes, so a re-read later in the same transaction can see a different, newly-committed value (non-repeatable read). `REPEATABLE_READ` holds the shared lock until the transaction ends, so no other transaction can change that row in the meantime — guaranteeing the same value on every re-read within the transaction.

**Q4: Why does `REPEATABLE_READ` still allow phantom reads?**
Its shared lock only covers rows that have already been read/matched — it doesn't lock the "gap" of the query's range condition itself. A new row inserted by another transaction can still satisfy the range condition and appear on a subsequent re-run of the same query.

**Q5: How does `SERIALIZABLE` prevent phantom reads that `REPEATABLE_READ` cannot?**
It uses the same read/write locking as `REPEATABLE_READ`, but additionally applies a range lock across the entire span of rows implied by the query's condition. That blocks other transactions from inserting any new row that would satisfy the condition until the current transaction finishes, so the same range query always returns the same set of rows.

**Q6: How would you decide which isolation level to use for a real application?**
Ask whether non-repeatable reads matter for your business logic. If they don't, `READ_COMMITTED` gives you better concurrency. If they do (and phantom reads don't matter), use `REPEATABLE_READ`. `SERIALIZABLE` is reserved for cases where phantom reads must also be prevented, accepting the lowest concurrency as the trade-off. `READ_UNCOMMITTED` is essentially only for read-only, static-data workloads.
