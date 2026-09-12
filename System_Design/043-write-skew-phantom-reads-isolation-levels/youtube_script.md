# Write Skew & Phantom Reads: Isolation Levels — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 43

## HOOK (0:00–0:30)

Picture this: a hospital has one hard rule — there must ALWAYS be at least one doctor on call. Two doctors, Alice and Bob, both check the schedule at the exact same moment. Both see the other one is on call. Alice thinks "cool, Bob's here, I'll head home." Bob thinks the exact same thing about Alice. Both mark themselves off-call. Both commit.

Now nobody is on call. Zero doctors. The invariant is broken — and here's the scary part — neither doctor did anything wrong. No dirty read. No lost update. Every read was valid. Every write was valid. And yet the system is now broken. This bug has a name — write skew — and if you think REPEATABLE READ or optimistic locking protects you from it, I need you to keep watching, because it doesn't.

[Screen cue: Split screen — Dr. Alice's terminal on the left, Dr. Bob's terminal on the right, both showing "2 doctors on call" at the same timestamp, then both flipping to "OFF" simultaneously, then a red banner: "0 DOCTORS ON CALL"]

## THE PROBLEM (0:30–2:00)

Here's the thing most engineers get wrong: we're taught to think about isolation levels in terms of "does my read get dirty data" or "does my update get overwritten." Those are real problems, and yes, READ COMMITTED and row-level locks solve them. But there's a whole category of bugs that live ABOVE the single-row level — bugs where every individual read and write is perfectly correct, but the combination of two transactions violates a rule that spans multiple rows.

Think about it this way: it's not that the data was wrong. It's that the decision was based on a snapshot that stopped being true the moment the other transaction committed. Alice's decision — "I can go off-call" — was true when she read it. Bob's decision was also true when he read it. But by the time both decisions landed, the world had changed underneath them, and nobody re-checked.

This is different from three things you probably already know:
- A dirty read is reading data that hasn't even been committed yet — READ COMMITTED kills that.
- A lost update is two transactions overwriting the SAME row — a `SELECT FOR UPDATE` on that one row kills that.
- A phantom read is when a brand-new row shows up mid-transaction that matches your WHERE clause — like querying "available seats on flight AA100," getting 3, and then somebody inserts a 4th seat and your second identical query now returns 4 rows. Nothing you already read changed — a new row simply appeared.

Write skew is the sneaky one because it doesn't touch the same row, and it doesn't need a phantom insert. Two transactions read overlapping data, each makes a locally-valid decision, and the combined effect breaks the constraint. Nothing weaker than SERIALIZABLE isolation — or explicit locking — stops it.

[Screen cue: Diagram — one box labeled "Dirty Read," one labeled "Lost Update," one labeled "Phantom Read," one labeled "Write Skew" — with a red X and green checkmark grid showing which isolation level blocks which anomaly]

## THE SOLUTION (2:00–5:00)

Let's actually walk through the hospital scenario as a transaction log, because seeing it laid out this way is what makes it click.

Transaction 1, Alice's session: `BEGIN`. She runs `SELECT count(*) FROM oncall WHERE shift='night'` — gets back 2. Now watch what happens when Bob's session runs at almost the exact same instant: Transaction 2 runs the identical `SELECT count(*)` — also gets back 2. Both sessions now believe "there are 2 people on call, I'm one of them, I can safely leave." Alice runs `UPDATE oncall SET status='off' WHERE doctor='alice'` and commits. Bob runs `UPDATE oncall SET status='off' WHERE doctor='bob'` and commits. Different rows. No lock conflict. Both succeed. Final state: zero doctors on call.

Now here's the seat booking version of the same root problem, but manifesting as a phantom read instead. Transaction 1 runs `SELECT * FROM seats WHERE flight='AA100' AND status='available'` and gets 3 rows. Meanwhile Transaction 2 inserts a brand-new seat row and commits. Transaction 1 re-runs the exact same query later in its transaction and now gets 4 rows — a row that didn't exist when T1 started is now visible. That's a phantom — it's a specific flavor of the same underlying issue: the read set you're basing decisions on isn't stable.

So how do you actually fix write skew? Four real options, and I want you to understand the tradeoffs between them, not just memorize them.

Option one: SERIALIZABLE isolation. In PostgreSQL specifically, this uses something called Serializable Snapshot Isolation, or SSI — it's not old-school "lock everything" serializable, it's optimistic: transactions run concurrently, and PostgreSQL tracks read-write dependencies in the background. If it detects that committing would create a cycle — meaning a real serialization anomaly — it aborts ONE of the transactions with the error `could not serialize access due to read/write dependencies among transactions`. Your application has to catch that and retry. This costs roughly 10 to 20 percent more than REPEATABLE READ, but you get correctness for invariants spanning many rows without hand-locking every single one.

Option two: `SELECT FOR UPDATE` — pessimistic locking. Transaction 1 runs `SELECT * FROM oncall WHERE shift='night' FOR UPDATE`. This grabs row-level exclusive locks on every matching row right now. Transaction 2's identical `SELECT ... FOR UPDATE` doesn't get an inconsistent read — it just blocks. It sits there waiting. Only after Transaction 1 commits does Transaction 2 unblock, and when it re-reads, it now correctly sees count=1, and can refuse to let Bob go off-call. No abort, no retry loop — just a wait.

Option three: the materialized conflict row trick. You create a tiny dummy table, say `shift_lock` with one row per shift, and you force every transaction that touches the invariant to `UPDATE shift_lock SET version = version + 1 WHERE shift = 'night'` FIRST. Because that's a real row-level lock on a real row, T2's update blocks until T1 commits — you've turned a multi-row invariant problem into a single-row lock problem.

Option four: re-check right before commit, inside the lock. Lock the rows with `FOR UPDATE`, then re-run your invariant check — literally re-select the count — INSIDE the same transaction, right before you commit. If the invariant would be violated, you `ROLLBACK` instead of committing. This is what a defensive architect does on top of option two — never trust the read from the top of the transaction; re-verify right before you commit.

[Screen cue: Live diagram — two parallel vertical timelines labeled T1 and T2, ticking down in real time, showing BEGIN → SELECT → UPDATE → COMMIT on both sides, with a red flash where the invariant breaks in the unprotected version, then the same diagram redrawn with a lock icon freezing T2's timeline until T1's COMMIT bar clears]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

Now let's talk about the traps, because this is where I see people get burned in real systems.

Trap one: assuming REPEATABLE READ is "basically SERIALIZABLE." It is not. Look at the anomaly table — READ UNCOMMITTED prevents nothing. READ COMMITTED stops dirty reads only. REPEATABLE READ stops dirty reads AND non-repeatable reads, and — this is the part people mess up — in PostgreSQL specifically, REPEATABLE READ also happens to prevent phantom reads because of how its MVCC snapshot works. But write skew? Still possible. Fully possible. Only SERIALIZABLE stops write skew. And don't assume this is portable across databases either — MySQL's REPEATABLE READ does NOT prevent phantom reads the way Postgres's does. If you move your code from Postgres to MySQL assuming isolation semantics carry over, you will reintroduce bugs you thought you'd already fixed.

Trap two: thinking optimistic locking — a version column, a `WHERE version = 5` check — solves this. It doesn't. Optimistic locking protects a SINGLE row from a lost update. It does nothing for a phantom insert. If the real threat is "someone inserts a new competing booking while I'm checking availability," a version column on an existing row is watching the wrong thing entirely. You need SERIALIZABLE or predicate locking to catch a phantom.

Trap three: using `SELECT FOR UPDATE` incorrectly on a count-based invariant. If your invariant is "at least N rows must satisfy this condition," you literally cannot `FOR UPDATE` a row that doesn't exist yet. You can lock the rows that exist, but you can't lock against a future INSERT the same way. That's exactly why the decision tree in this topic says: if your invariant involves a COUNT or SUM across multiple rows, reach for SERIALIZABLE, not FOR UPDATE — because locking all "matching" rows is fragile the moment a phantom row can appear.

Trap four: applying strict serialization everywhere out of fear, and tanking your throughput. Look at the real numbers: READ COMMITTED is your 100% baseline throughput. REPEATABLE READ costs you almost nothing — about 95% of baseline. But SERIALIZABLE with SSI drops you to roughly 80 to 90 percent, and `SELECT FOR UPDATE` — because it blocks rather than aborts — lands around 85 to 95% but with added latency from waiting. If you slap SERIALIZABLE onto every read-heavy CRUD endpoint in your app "just to be safe," you're paying a real performance tax for an invariant that most of those endpoints don't even have.

Trap five: not building retry logic when you DO choose SERIALIZABLE. Because SSI is optimistic, it doesn't block — it aborts at commit time. If your application code doesn't catch that specific serialization error and retry the transaction, you'll just throw 500s at users during any real concurrent load, and you'll blame the database when the actual bug is missing retry logic in your service layer.

Trap six: at flash-sale scale — think millions of concurrent users hitting "buy" in the same 10 seconds — even `SELECT FOR UPDATE` on a single seat row doesn't scale, because you'll have massive lock contention on hot rows. The real-world fix used at that scale isn't a stronger isolation level at all — it's READ COMMITTED plus an idempotency key plus an atomic counter in something like Redis, explicitly accepting that database-level serialization won't hold up under that kind of concurrency and moving the hot-path decision out of the DB entirely.

[Screen cue: Comparison table on screen — rows: READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ, SERIALIZABLE; columns: Dirty Read, Non-repeatable Read, Phantom Read, Write Skew — cells filling in red "possible" / green "prevented" one row at a time as I talk]

## REAL WORLD (8:00–9:30)

Let's ground this in systems you'd actually design in an interview.

Think about a payment system — the kind Paytm or PhonePe run at massive scale. Double-spend prevention is a textbook write-skew risk: two concurrent transactions both read "balance = 1000," both try to debit 900. If you don't serialize access, both debits could succeed and the account goes negative. The fix is `SELECT FOR UPDATE` on that specific account row — transaction two, after transaction one commits, re-reads the balance, correctly sees 100 left, and rejects the second debit. This is exactly why financial systems almost never run on plain READ COMMITTED for the write path — the rule of thumb is "money and invariants mean SERIALIZABLE or FOR UPDATE, never READ COMMITTED."

Now think about ticket booking — the last-seat problem, like what Flipkart or a train/flight booking platform deals with during a flash sale. Two users both see "1 seat available." Without protection, both bookings can succeed and you've oversold the seat. `SELECT FOR UPDATE` on that seat row prevents the double booking cleanly. But — and this is the scale lesson — for a flash sale with millions of concurrent users hammering the same few rows, database-level locking becomes the bottleneck itself. That's when you shift to READ COMMITTED plus an idempotency key plus an atomic counter in Redis, deliberately trading strict DB-level guarantees for something that can actually handle the concurrency.

And think about hotel booking — say a platform like MakeMyTrip or Airbnb-scale booking — where the invariant isn't just "one row," it's "room X, for date range Y, not already booked." Two bookings for the same room on overlapping dates can both read "room available" and both write success. Here you either lock the specific room+date rows with `FOR UPDATE`, or you run the whole check under SERIALIZABLE, because the invariant spans a date range, not a single row.

Across all three, the retry-cost numbers matter: SSI-based SERIALIZABLE runs at roughly 80 to 90% of baseline throughput but needs retry logic on abort; `SELECT FOR UPDATE` runs around 85 to 95% but adds blocking latency instead of aborting. Which one you pick is an architecture decision, not a default.

[Screen cue: Three company-style cards flashing in sequence — "Payment System: SELECT FOR UPDATE, double-spend blocked" — "Ticket Booking (flash sale scale): READ COMMITTED + idempotency key + Redis atomic counter" — "Hotel Booking: FOR UPDATE on room+date OR SERIALIZABLE" — each with a small throughput percentage badge]

## OUTRO + NEXT EPISODE (9:30–10:00)

So here's your one-liner for the interview, and I want you to actually memorize this: "Write skew happens when two transactions each read rows the other will update — only SERIALIZABLE isolation or SELECT FOR UPDATE prevents the invariant violation." Say that in an interview and you've just signaled you understand isolation levels at a level most candidates don't.

If this saved you from shipping a hospital-on-call-style bug into production, hit subscribe — this is episode 43 in a full system design series, and every episode builds on the last. Next up, episode 44: we're talking about timeout strategy — what happens when your timeout is too short, what happens when it's too long, and why getting this one number wrong cascades into outages across your entire dependency graph. See you there.

[Screen cue: End card — "Episode 44: Timeout Strategy — Too Short, Too Long" with subscribe button animation]
