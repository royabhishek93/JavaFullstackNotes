# Optimistic vs Pessimistic Locking — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 21 of 29

## HOOK (0:00–0:30)

[Screen cue: split-screen animation — two phones, same flight, same seat]

Two people are booking a flight. Same flight. Same last available seat — 14A.

Both open the app at the exact same millisecond. Both see: "Seat 14A — Available." Both tap "Book."

Your server gets two requests, back to back, microseconds apart. Both read: available. Both write: booked.

Both get a confirmation email. Both feel great. Both show up at the gate.

[Screen cue: text stamp — "ONE OF THEM IS SITTING ON THE FLOOR"]

One of them is sitting on the floor at gate 14, because your database let two transactions win a race that only one of them could actually win.

This is the lost update problem, and today I'm going to show you the two ways serious engineers solve it — pessimistic and optimistic locking — plus the deadlock trap that catches people who think they've already solved it.

## THE PROBLEM (0:30–2:00)

[Screen cue: whiteboard — "READ → READ → WRITE → WRITE" race diagram]

Let's slow down what actually happened. This isn't a UI bug. This is a race condition at the database level.

User A's request: `SELECT status FROM seats WHERE id = 14` → gets back `available`.
User B's request: `SELECT status FROM seats WHERE id = 14` → also gets back `available`.

Neither of them knows the other one exists. As far as each transaction is concerned, it read the truth, and the truth said the seat was free.

Then both write. `UPDATE seats SET status = 'booked' WHERE id = 14`. Whichever one commits last simply overwrites the other. There's no error. There's no conflict detected. The database happily accepts both writes because, individually, each one is a perfectly valid update.

[Screen cue: text — "This is called a LOST UPDATE"]

This is called a **lost update**. It's the same failure mode whether you're booking seats, debiting a bank account, or decrementing inventory count for the last item in a flash sale. Two readers, stale data, two writers, silent corruption.

So how do you stop it? There are exactly two philosophies, and almost every locking strategy you'll ever use is one of these two, or a variation on them.

[Screen cue: two-column split — "PESSIMISTIC" vs "OPTIMISTIC"]

**Pessimistic locking** says: assume the worst. The moment I read this row, I'm going to lock it. Nobody else touches it until I'm done. Guaranteed correctness, at the cost of making everyone else wait in line.

**Optimistic locking** says: assume the best. Most of the time nobody else is touching this row at the same time as me, so why pay the cost of locking? Instead, I'll just check — right before I write — whether the data changed since I read it. If it did, I reject my own write and let the caller retry.

One blocks. The other detects and retries. Let's build both, mechanically, so you understand exactly what's happening at the SQL level.

## THE SOLUTION (2:00–5:00)

[Screen cue: code editor — pessimistic SQL block]

**Pessimistic locking, mechanically.**

```sql
BEGIN;
SELECT * FROM seats WHERE id = 14 AND status = 'available' FOR UPDATE;
UPDATE seats SET status = 'booked', user_id = 'userA' WHERE id = 14;
COMMIT;
```

That `FOR UPDATE` clause is the whole trick. It tells the database: "I'm reading this row because I intend to write to it. Lock it now, exclusively, and hold that lock until I commit or roll back."

Here's the timeline, down to the millisecond:

[Screen cue: timeline graphic, T=0ms to T=7ms]

```
T=0ms   User A: SELECT ... FOR UPDATE   ← acquires row lock
T=1ms   User B: SELECT ... FOR UPDATE   ← BLOCKED, waiting for the lock
T=5ms   User A: UPDATE ... COMMIT       ← releases lock
T=5ms   User B: lock granted, reads row
T=6ms   User B: sees status = 'booked'
T=6ms   User B: no available seat → return error to user
T=7ms   ✓ Only one booking happened. Correct.
```

User B doesn't get a corrupted result — User B gets *made to wait* until User A finishes, and then sees the truth: the seat's gone. That's the guarantee pessimistic locking gives you. It converts a race condition into a queue.

Now, MySQL's InnoDB engine gives you three flavors of this, and picking the wrong one matters:

[Screen cue: table — FOR UPDATE / FOR SHARE / table lock]

`SELECT ... FOR UPDATE` gives you an **exclusive lock**. Nobody else can read-for-update or write this row while you hold it.

`SELECT ... FOR SHARE` — sometimes written `LOCK IN SHARE MODE` — gives you a **shared lock**. Other transactions can also take a shared lock and read, but nobody can write until all shared locks are released.

And then there's `LOCK TABLES seats WRITE`, which locks the *entire table*. Don't use this in an OLTP system. That's a sledgehammer where you need a scalpel — you'll stall every transaction touching that table, not just the one row you care about.

[Screen cue: code editor — optimistic SQL block, version column]

**Optimistic locking, mechanically.**

The trick here is a `version` column.

```sql
CREATE TABLE seats (
    id INT PRIMARY KEY,
    status VARCHAR(20),
    user_id INT,
    version INT DEFAULT 0
);
```

You read the row *and* its version, without taking any lock at all:

```sql
SELECT id, status, version FROM seats WHERE id = 14;
-- id=14, status='available', version=5
```

Then, when you write, you don't just say "set status to booked." You say "set status to booked, *only if the version is still 5*":

```sql
UPDATE seats
SET status = 'booked', user_id = 'userA', version = version + 1
WHERE id = 14 AND version = 5;
```

If nobody else touched the row, this affects exactly 1 row, and version becomes 6. If somebody else already updated it — version is now 6, not 5 — this `WHERE` clause matches zero rows. The update silently does nothing, and your application code checks the affected-row-count to detect that.

[Screen cue: timeline graphic — both users read version=5]

```
T=0ms   User A reads seat 14: status='available', version=5
T=0ms   User B reads seat 14: status='available', version=5
        (no locks — both proceed immediately)

T=5ms   User A: UPDATE ... WHERE version=5   → SUCCESS, 1 row affected
                version is now 6
T=5ms   User B: UPDATE ... WHERE version=5   → FAILS, 0 rows affected
                version is already 6, B's WHERE clause matches nothing
T=6ms   User B: detects 0 rows updated → retry, or tell the user to try again
T=7ms   ✓ Only one booking happened. Correct.
```

Notice nobody was blocked. Both transactions ran instantly, in parallel. The conflict was only discovered at the very last moment — the write — instead of being prevented up front.

[Screen cue: Java/JPA code block, @Version annotation]

If you're on Spring and JPA, Hibernate does the version bookkeeping for you:

```java
@Entity
public class Seat {
    @Id
    private Long id;
    private String status;
    private Long userId;

    @Version
    private Integer version;
}
```

That single `@Version` annotation makes Hibernate automatically generate `UPDATE ... WHERE id = ? AND version = ?` for every update, and if zero rows come back, it throws `OptimisticLockException` for you:

```java
try {
    seat.setStatus("booked");
    seatRepository.save(seat);
} catch (OptimisticLockException e) {
    return ResponseEntity.status(409).body("Seat was just taken, please retry");
}
```

HTTP 409 Conflict, tell the user to retry. That's it. No manual version-checking code.

So — pessimistic blocks and guarantees order. Optimistic never blocks, but you have to handle the retry. Which one do you pick? That's coming up in a minute. First, let's talk about the trap that catches engineers who think pessimistic locking is a free lunch.

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

[Screen cue: title card — "THE DEADLOCK PROBLEM"]

Here's the mistake I see constantly: engineers add `SELECT FOR UPDATE` everywhere because "locking is safe," and then their production system starts throwing mysterious errors under load. The problem isn't locking — it's *unordered* locking. That's what causes a deadlock.

[Screen cue: two-transaction diagram, Row 1 / Row 2 crossing arrows]

Picture this. Transaction A needs to update two rows — say, transfer money from account 100 to account 200. Transaction B is doing the reverse transfer, from 200 to 100, at the same time.

```
T=0ms   Txn A: locks Row 1 (account 100)
T=0ms   Txn B: locks Row 2 (account 200)
T=1ms   Txn A: tries to lock Row 2 → BLOCKED (B holds it)
T=1ms   Txn B: tries to lock Row 1 → BLOCKED (A holds it)
T=2ms   MySQL's deadlock detector fires
T=2ms   MySQL kills Txn B, rolls it back — Txn A proceeds
T=3ms   Txn B receives: ERROR 1213: Deadlock found when trying to get lock
```

Transaction A is holding row 1, waiting for row 2. Transaction B is holding row 2, waiting for row 1. Neither one can ever finish. Neither one will ever release its lock. This is a genuine deadlock — and to its credit, MySQL doesn't just hang forever. InnoDB's deadlock detector notices the cycle, picks a victim — usually the transaction that's done less work — kills it, and rolls it back. That's error 1213, and if you've been running any non-trivial transactional system in production, you've seen it in your logs.

The fix isn't "stop using locks." The fix is three disciplined rules.

[Screen cue: rule card #1 — "SAME LOCK ORDER"]

**Rule one: always lock rows in the same order, in every transaction, everywhere in your codebase.**

If Transaction A locks account 100 then account 200, Transaction B must also lock account 100 then account 200 — never the reverse. A simple, effective convention: always lock by the numerically smaller ID first. If both transactions follow "lock the lower ID first," then whichever transaction gets there first just makes the other one *wait*, in a straight line, no cycle possible. No deadlock, ever, no matter how many concurrent transfers you're running.

[Screen cue: rule card #2 — "KEEP TRANSACTIONS SHORT"]

**Rule two: keep transactions short.** This is the one that bites people who think they understand locking but haven't thought about *duration*.

Here's the anti-pattern:

```
BEGIN
SELECT FOR UPDATE     ← lock acquired
call external API     ← takes 2 seconds. Lock is STILL HELD.
UPDATE
COMMIT
```

You've acquired a row lock, and then you go make a network call — to a payment gateway, a fraud-check service, whatever — and that call takes two full seconds. For those two seconds, every other transaction that wants that row is blocked, waiting on a lock that's just sitting there while your code waits on a socket read. Under load, this is how a single slow downstream dependency turns into a cascading pile-up of blocked database connections.

The fix: do the external call *first*, before you ever open the transaction. Only acquire the lock right before the actual write, hold it for single-digit milliseconds, and commit immediately.

[Screen cue: rule card #3 — "NEVER UPGRADE SHARED TO EXCLUSIVE"]

**Rule three: never upgrade a shared lock to an exclusive lock within the same transaction.**

If Transaction A reads a row with a shared lock, and Transaction B also reads it with a shared lock — that's fine, they can coexist. But if both A and B then try to *upgrade* to an exclusive lock so they can write — each one is waiting for the other's shared lock to be released before it can get its exclusive lock. Both are stuck, forever. It's a deadlock with a different setup, but the same result.

The fix: if you already know you're going to write to a row, acquire the exclusive lock — `FOR UPDATE` — right from the start. Don't read-then-decide-to-upgrade.

Follow those three rules, and pessimistic locking stops being a landmine and becomes exactly what it's supposed to be: a predictable queue.

## REAL WORLD (8:00–9:30)

[Screen cue: logo montage — payment / ticketing / hotel / trading]

Let's ground this in systems you'd actually build or interview about.

**Payment systems** — think PhonePe or Paytm processing a debit. Two concurrent debit requests hit the same account. Without `SELECT FOR UPDATE`, both threads read balance = 1000, both approve an 800-rupee debit, and the account goes negative — a real, embarrassing, auditable bug. Pessimistic locking is non-negotiable here: you lock the account row at read time, the second debit request blocks, and by the time it's unblocked, it sees the *correct*, already-debited balance and can correctly reject itself for insufficient funds.

**Ticket booking** — this is BookMyShow or IRCTC territory. Seat A10, a hundred people hitting refresh during a movie or train-ticket release. `SELECT FOR UPDATE` on that seat row means exactly one booking transaction wins, and every other transaction sees the committed "already booked" state and fails gracefully, instead of both transactions racing to a double-booked seat.

**Hotel booking** is a great contrast case. Room availability has far lower contention than a single movie seat — you've usually got dozens of rooms of the same type, not one specific chair. Here, optimistic locking with `@Version` is the better call: no lock overhead, near-zero conflict rate in practice, and on the rare occasion two people do collide, one gets an `OptimisticLockException` and retries. Higher throughput, same correctness guarantee.

**Stock brokers** — Zerodha, Groww, any order-matching engine. A market order matches against a resting limit order, and both sides of that match need to be locked together so the fill price gets calculated atomically. This is exactly the deadlock-prone two-row-lock scenario from the deep dive — which is why consistent lock ordering, locking the lower order ID first, is what keeps two matching threads processing the same pair of orders from ever deadlocking each other.

[Screen cue: decision framework graphic — contention-based flowchart]

Notice the pattern across all four: it's never "locking is good" or "locking is bad." It's "how contended is this row, and what does a conflict cost me?" High contention, expensive conflict — payment, ticketing — go pessimistic. Lower contention, cheap retry — hotel rooms — go optimistic.

## OUTRO + NEXT EPISODE (9:30–10:00)

[Screen cue: quick recap card — the 5-row comparison table]

So — lost updates happen when two transactions read stale data and both write. Pessimistic locking prevents that by blocking at read time with `SELECT FOR UPDATE`; optimistic locking prevents it by detecting the conflict at write time with a version column and `@Version` in Hibernate. And whichever you pick, watch out for deadlocks — same lock order, short transactions, never upgrade shared to exclusive.

[Screen cue: end card — "NEXT: REDLOCK"]

Now — everything today assumed a *single* database. One node, one lock table. But what happens when your lock needs to work across five different Redis nodes, in a distributed system, where any one of those nodes could crash mid-lock?

That's next episode: **Redlock — Distributed Locking with Redis.** We'll break down why a naive single-Redis lock isn't safe, and how Redlock's multi-node majority algorithm actually works. See you there.
