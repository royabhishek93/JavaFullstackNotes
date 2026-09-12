# MVCC — How PostgreSQL Reads Never Block Writes — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 24 of 29

## HOOK (0:00–0:30)

[Screen cue: open a Google Doc side-by-side with a second cursor typing in it]

Open Google Docs right now. Start reading a long document. Now get a friend to start editing that same document at the same time.

What do you NOT see? You don't see "Document locked — someone else is editing." You don't see their half-typed sentence flicker in and out as they type it. You see the document exactly as it was the moment you opened it — clean, consistent, complete. Their edits show up the next time you refresh.

[Screen cue: text overlay — "You were reading a SNAPSHOT, not the live data"]

That's exactly what PostgreSQL does for every row in your database, on every single read, automatically, invisibly. It's called MVCC — Multi-Version Concurrency Control — and today we're going to open it up and see exactly how it works, where it breaks, and why a doctor on-call scheduling bug is the best interview story you'll ever tell.

## THE PROBLEM (0:30–2:00)

[Screen cue: whiteboard diagram — "Reader holds shared lock" with a queue forming behind it]

Let's say PostgreSQL didn't have MVCC. Let's say it worked like a lot of engineers *assume* databases work — with plain old locking.

You kick off a report. It scans 10,000 rows in the `orders` table. To do that safely under a locking model, it grabs a shared read lock on those rows — or worse, the whole table. Now, a completely unrelated transaction comes in half a second later and wants to update one row in that table. What happens?

It waits. It can't touch a row that's currently being read. So it sits in a queue.

[Screen cue: animate the queue growing — reader, then writer waiting, then more readers piling up]

Now imagine this at scale. More readers pile up behind the first one. The writer that's been waiting is now blocked for seconds, not milliseconds. Other writers queue up behind that one. Your connection pool — which has a fixed number of connections, say 100 — starts filling up with connections that are just sitting there, blocked, doing nothing except waiting for a lock. Once the pool is exhausted, new requests can't even get a connection. The service falls over. Not because the database is slow — because everything is standing in a single-file line waiting for a lock that a report query is holding.

That's the nightmare scenario: **reader holds shared lock → writer waits → queue builds → connection pool exhausts → service falls over.**

[Screen cue: text overlay — "This is NOT how PostgreSQL works. Here's why."]

This is the model a junior engineer has in their head when they say "reads will block during heavy writes." And it's wrong for PostgreSQL — because PostgreSQL doesn't use locks for this. It uses versions.

## THE SOLUTION (2:00–5:00)

[Screen cue: diagram — a single row with two hidden columns highlighted, xmin and xmax]

Here's the trick. Every row in PostgreSQL has two hidden system columns you never see in a normal `SELECT *`: `xmin` and `xmax`.

`xmin` is the ID of the transaction that **created** this row version. `xmax` is the ID of the transaction that **deleted or updated** it — and if that's zero, it means "nobody has touched this version yet, it's still alive."

When a write happens, PostgreSQL does NOT edit the row in place. It creates a brand new row version and marks the old one as superseded. Let's walk through the exact example, because this is the part that makes it click.

[Screen cue: animate three states appearing one after another]

Transaction 100 inserts a row: `xmin=100, xmax=0, name="Alice"`. That row is alive, visible to anyone whose transaction started after 100 committed.

Now transaction 200 comes along and updates that row — changes the name to "Alicia." PostgreSQL doesn't touch the original row. Instead:

- The OLD row gets `xmax=200` stamped on it. It's now dead to any transaction with an ID of 200 or higher — but it's still physically sitting there on disk.
- A NEW row version is created: `xmin=200, xmax=0, name="Alicia"`. This one's alive.

[Screen cue: split screen — Transaction 150 on the left, Transaction 250 on the right, both pointing at the same two row versions]

Now here's where it gets good. Transaction 150 started reading *before* transaction 200 committed. Its snapshot says "I can see everything committed with an ID less than 200." When it looks at the row, the old version has `xmin=100` — committed, visible — and `xmax=200`, but 200 wasn't committed yet when 150 took its snapshot. So the old version is still visible. Transaction 150 reads "Alice." Correct, for what it saw at the moment it started.

Transaction 250 starts reading *after* transaction 200 committed. Its snapshot includes everything up through 200. It looks at the row and sees the new version — `xmin=200`, committed, `xmax=0`, still alive. Transaction 250 reads "Alicia."

Neither transaction blocked the other. Neither transaction saw wrong data. They just saw *different, both-correct* snapshots in time.

[Screen cue: timeline diagram — Txn A and Txn B running in parallel over t=0 to t=6, writes happening in between]

Zoom out and this is snapshot isolation. Picture a timeline: at t=0, Transaction A starts under READ COMMITTED. At t=1 and t=2, two writes happen to rows X and Y from other transactions. At t=3, Transaction B starts. At t=4, Transaction A reads row X — its snapshot was taken back at t=0, so it doesn't include the write at t=1, and it sees the OLD value. At t=5, Transaction B reads the same row X — but Transaction B's snapshot includes everything up to t=3, which includes that write — so it sees the NEW value.

Same row. Same table. Two transactions running at the exact same wall-clock moment, each getting a completely consistent, completely correct — but different — view of the data. No blocking. No waiting. That's MVCC.

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

[Screen cue: text overlay — "MVCC has a cost. It's called bloat."]

Okay, so this sounds free. It's not free. Every one of those old row versions — "Alice" with `xmax=200` — doesn't just vanish. It stays on disk until something cleans it up. If a row gets updated four times, you might have four physical copies sitting there, only one of which is actually "live." This is called **table bloat**, and on a busy table, it can genuinely double or triple your disk usage.

The cleanup process is called **VACUUM**. VACUUM scans the table, finds dead row versions that no active transaction can possibly still need, and marks that space as reusable — free space that future inserts and updates can reuse. But here's the detail that trips people up: **VACUUM does not shrink the file on disk.** The table file stays the same size; it just has more "free space" inside it now. If you actually want to return that space to the OS, you need `VACUUM FULL` — and `VACUUM FULL` takes a full table lock. On a production table, that's a maintenance-window operation, not something you run casually at 2pm on a Tuesday.

[Screen cue: text overlay — "XID WRAPAROUND — the bug that can take your database offline"]

Now here's the one that should genuinely scare you, because it's caused real production outages at real companies. PostgreSQL identifies every transaction with a 32-bit Transaction ID — an XID. Do the math: 32 bits gives you about 4.2 billion possible values. If your system is doing 1,000 transactions per second — which isn't even that aggressive for a busy service — you burn through all 4.2 billion IDs in roughly 49 days.

What happens when it wraps around? PostgreSQL uses modular arithmetic to compare XIDs — transaction 1 and transaction 4,294,967,297 look identical to the comparison logic. So a row that was inserted way in the past by transaction 50 could suddenly look like it was inserted "in the future" relative to a current transaction after wraparound. PostgreSQL would think that row doesn't exist yet. That's not a performance problem — that's **silent, catastrophic data loss.**

The defense is VACUUM "freezing" old XIDs before they get dangerously close to wraparound. PostgreSQL tracks this with an "age" metric you can query directly:

[Screen cue: show the query on screen]

```sql
SELECT datname, age(datfrozenxid) AS xid_age
FROM pg_database
ORDER BY xid_age DESC;
```

The operational thresholds every senior engineer should know cold: alert your team when that age crosses **150 million**. At **2 billion**, PostgreSQL doesn't ask politely — it forces the entire database into **read-only mode** and refuses all new writes until you VACUUM it back under the limit. Imagine explaining to your VP that the database stopped accepting writes because nobody was watching a counter. That's the AUTOVACUUM story you tell in interviews.

Speaking of AUTOVACUUM — the defaults are conservative, tuned for small toy databases, not your write-heavy production table. For high-churn tables like a `sessions` or `events` table, you drop `autovacuum_vacuum_scale_factor` from the default 20% down to 1%, so VACUUM kicks in way sooner instead of letting dead rows pile up. You bump `autovacuum_max_workers` so more cleanup runs in parallel, and you lower `autovacuum_vacuum_cost_delay` so it's not throttled into uselessness. And it's not just table bloat — the same dead-version problem happens inside your B-tree indexes too. Index bloat is real, and the fix there is `REINDEX INDEX CONCURRENTLY`, which rebuilds the index online without locking the table.

[Screen cue: table on screen — isolation levels vs. what they prevent]

Now, isolation levels. PostgreSQL gives you three that matter: **READ COMMITTED**, the default, which takes a fresh snapshot for every single statement — meaning two identical SELECTs in the same transaction can return different results if something committed in between. **REPEATABLE READ**, which takes one snapshot for the whole transaction, so every read inside it sees the same consistent picture — and PostgreSQL is actually stricter than the SQL standard here, blocking phantom reads too. And **SERIALIZABLE**, full serialization, using something called SSI — Serializable Snapshot Isolation — which tracks dependencies between transactions and aborts the ones that would create an inconsistency.

[Screen cue: whiteboard — two doctors, two transactions, side by side]

And this brings us to the single best "gotcha" story in this whole topic: **write skew.** Here's the setup. You run an on-call system for doctors. The rule — the invariant — is simple: at least one doctor must always be on call. Right now, Doctor A and Doctor B are both on call.

Doctor A opens the app and checks: "is anyone else currently on call?" The system says yes — Doctor B is. Satisfied, Doctor A sets their own status to off-call.

At almost the exact same moment, Doctor B opens the app and checks the exact same question: "is anyone else on call?" The system says yes — Doctor A is. Satisfied, Doctor B sets their own status to off-call.

[Screen cue: text overlay in red — "ZERO doctors on call. Invariant violated."]

Both transactions read *different* rows — well, they each read the *other* doctor's row — and each wrote to their *own* row. From MVCC's point of view, there's no conflict. No row was written by two transactions. Both commit cleanly. And now there are zero doctors on call, and nobody gets paged when a patient needs help.

This is write skew, and it is NOT caught by regular MVCC, and it is NOT caught by REPEATABLE READ either. The only thing that catches it is SERIALIZABLE. PostgreSQL's SSI detects that read-write dependency cycle between the two transactions and aborts one of them with the error `could not serialize access due to read/write dependencies`. Your application catches that error and retries — and on the retry, the second transaction sees the updated state and correctly refuses to also go off-call. That's the fix. That's the interview answer that separates "I know MVCC exists" from "I know exactly when MVCC isn't enough."

## REAL WORLD (8:00–9:30)

[Screen cue: logos or text — PhonePe, Paytm, Flipkart, BookMyShow]

Let's ground this in systems you actually use. Think about **PhonePe or Paytm** checking your wallet balance at the exact moment a debit transaction is being processed against that same account. MVCC means the balance read gets a clean, consistent snapshot — it's not blocked waiting for the debit to finish, and it's not reading some half-written partial state. But balance reads alone aren't enough to stop double-spend — that's exactly where you'd wrap the actual debit-credit pair in SERIALIZABLE isolation, so write skew between two simultaneous debits against the same balance gets caught instead of silently succeeding twice.

Think about **Flipkart's** product catalog. Thousands of people are browsing, searching, and viewing product pages at any given second, while somewhere in the background a price-update transaction is writing new prices. Because of MVCC, none of those catalog reads ever sit around waiting for the price write to commit. The moment that price transaction commits, brand-new reads instantly see the new price — no cache invalidation dance required at the database layer.

And the big one — **BookMyShow during a flash sale.** Picture 50,000 people simultaneously hitting "check seat availability" on a blockbuster movie release, while booking transactions are simultaneously deducting seats in real time. MVCC gives you zero read-write contention on that seat table — all those reads just flow. But you still need something stronger for the actual seat-booking write itself — a `SELECT FOR UPDATE` on the seat row, or SERIALIZABLE — to guarantee two different people don't both walk away thinking they booked seat 14.

And for something like hotel booking, where an availability check needs to stay consistent across an entire multi-step booking flow, REPEATABLE READ gives you one stable snapshot for the whole transaction, so the inventory numbers don't shift out from under you mid-booking.

Same core mechanism — xmin, xmax, snapshots — powering four completely different products, from payments to flash-sale ticketing.

## OUTRO + NEXT EPISODE (9:30–10:00)

[Screen cue: recap bullets on screen — xmin/xmax, snapshot isolation, VACUUM, XID wraparound, write skew + SERIALIZABLE]

So here's the whole thing in one line: PostgreSQL never makes reads wait for writes or writes wait for reads, because every write just creates a new row version stamped with `xmin` and `xmax`, and every read just picks the version that matches its snapshot. The cost is bloat, which VACUUM cleans up, and the danger is XID wraparound, which AUTOVACUUM prevents — as long as you're watching it. And the one gap MVCC can't close on its own is write skew, which is why SERIALIZABLE and SSI exist.

[Screen cue: end card — "Next: Episode 25 — CQRS & Event Sourcing"]

Next episode, we're moving from "how one database handles concurrency" to "how you split your entire system into a write model and a read model" — CQRS and Event Sourcing. If MVCC was about versioning one row, event sourcing is about versioning your *entire* application state. See you there.
