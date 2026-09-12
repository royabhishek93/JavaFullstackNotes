# Write-Ahead Log (WAL) & Crash Recovery — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 36

## HOOK (0:00–0:30)

Imagine this. A PostgreSQL server hosting a payments database loses power — literally, the data center has a power blip — at the exact millisecond it's writing a balance update to disk. Not before. Not after. Mid-write.

When the machine comes back up thirty seconds later... the payment is fine. Not corrupted. Not half-written. It's either fully there, or it never happened at all. No in-between state, ever.

That's not luck. That's one single design decision inside every production database — Postgres, MySQL, Oracle, SQL Server — called the Write-Ahead Log. And by the end of this video you'll understand exactly why a half-written disk page should be *impossible*, and how tools like Debezium read this same log to sync your database into Kafka for basically free.

[Screen cue: split-screen animation — left side shows a data page as a jagged, half-overwritten block labeled "CORRUPT"; right side shows a clean append-only log strip labeled "SAFE". A lightning bolt strikes both, only the right survives.]

## THE PROBLEM (0:30–2:00)

Let's start with why this is even a problem. Think about it this way — a data file on disk is organized into fixed-size pages. Say table `accounts` stores your row on page 5. When you run `UPDATE accounts SET balance=900 WHERE id=42`, at some point the database has to physically overwrite the bytes on page 5 that used to say 1000 with new bytes that say 900.

Here's the danger: that overwrite is not instantaneous. It takes time to flush bytes to a spinning disk or even an SSD. If the machine loses power *during* that write — not before, not after, but literally in the middle — you get a page that's neither the old value nor the new value. It might say "900" with garbage bytes trailing, or it could be a mix of the old page and new page interleaved. There is no way, after the fact, to know what it should have said. Your data is just... gone. Silently corrupted.

Now scale that up. A production OLTP database is doing thousands of these random-page writes per second. If you write directly to data pages with no other safety net, every single one of those writes is a moment where a crash produces unrecoverable corruption. That's simply not acceptable for a system that stores money, orders, or anything that matters.

[Screen cue: animate a disk page mid-write — "1000" being overwritten by "900" — freeze it exactly in the middle showing "19_0" garbled bytes, red border, label "UNRECOVERABLE".]

## THE SOLUTION (2:00–5:00)

Now watch what happens when we add one rule: never touch the data page first. Always write a log record first, and only touch the data page later, lazily, in the background.

Here's the sequence. Step one: the transaction generates a WAL record — something like `LSN=1234, txn=567, UPDATE accounts id=42 balance=1000→900`. That record captures everything needed to redo or undo the change: the old value, the new value, which transaction it belongs to.

Step two: that WAL record gets `fsync`'d to disk. Not the data page — the log. And critically, the WAL is *append-only*. You're never rewriting existing bytes, you're just adding new bytes to the end of a file. Sequential appends are fast, and more importantly, if a crash happens mid-append, you just get a WAL that ends abruptly — the last incomplete record is simply ignored during recovery. No corruption, because you never overwrote anything that already existed.

Step three: only *after* that WAL record is durably on disk does the database return "commit successful" to the client.

Step four — and this is the part people miss — the actual data page update happens *asynchronously*, sometime after the commit already returned. It's called a "dirty buffer flush," and it can happen seconds or minutes later.

So what happens if the crash hits during step four, while the data page is still stale? On restart, PostgreSQL reads `pg_control` to find the LSN of the last checkpoint, opens the WAL from that point, and replays every record forward. It sees `LSN=1234, txn=567, UPDATE ... balance=900`, and re-applies it to the data page. Recovery restores exactly the state the client was already told existed. Nothing is lost, because the log — not the data page — is the source of truth.

And here's a nice side effect: a checkpoint just means "all dirty pages have been flushed to disk as of this point" — so any WAL before the checkpoint LSN is now safe to delete. That's how the log doesn't grow forever under normal operation.

[Screen cue: live-drawn sequence diagram — Client → WAL (append + fsync) → "COMMIT OK" returned to client → (async, dashed arrow) → Data Page updated later. Then draw a lightning bolt hitting the "Data Page" box, and an arrow labeled "REPLAY WAL" curving back from the WAL log to fix the data page on restart.]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

Let's talk about where this bites engineers in production, because there are some very expensive traps here.

**Trap #1: Treating `synchronous_commit = off` as a free performance win everywhere.**
Postgres lets you turn off the fsync-before-commit behavior. When you do, WAL is written to the OS buffer but NOT fsynced before the client gets "success" back. That's roughly 40% faster writes because you skip the fsync cost. But you now have a data-loss window — up to about 0.6 seconds, based on the default `wal_writer_delay` of 200 milliseconds times three. If the OS crashes — not even Postgres, the whole machine — inside that window, a transaction the client thinks succeeded... never actually made it durably to disk. For session data or analytics events, fine, who cares. For a payment record? That's a customer who paid and the money vanished from your books. Never, ever use `synchronous_commit=off` for financial writes.

**Trap #2: Forgetting `wal_level` has to be `logical` for CDC.**
If you're running Debezium or any logical-decoding-based CDC tool, and your `wal_level` is set to `minimal` or even `replica`, you don't get the full tuple data needed for logical decoding. Engineers set this up, wonder why Debezium can't create a replication slot, and burn hours debugging a config that was one setting away from working the whole time.

**Trap #3: Replication slot lag — the silent disk-filling time bomb.**
This one's brutal. When Debezium creates a logical replication slot, it tells Postgres "don't you dare delete WAL until I've consumed it." That's normally fine — Debezium reads fast. But if Kafka goes down, or your Debezium connector crashes, or there's a network partition between them... Postgres literally cannot delete WAL segments the slot hasn't acknowledged yet, even past the checkpoint. The `pg_wal` directory just grows. And grows. Until the disk fills up — and a Postgres primary with a full disk doesn't gracefully throttle, it can crash outright. The fix is monitoring: track `pg_wal_lsn_diff` against `restart_lsn` for every slot, and alert when lag exceeds 5GB. If a slot is inactive for too long with unbounded growth, drop it.

**Trap #4: Assuming recovery is always fast.**
Recovery time is proportional to how much WAL exists since the last checkpoint. With the default 5-minute checkpoint interval and light load, recovery takes 5-10 seconds — no big deal. But under heavy OLTP load, or if `max_wal_size` gets bumped to something like 4GB to reduce checkpoint frequency for write throughput, you can be looking at 2 to 5 minutes of recovery time after a crash. If your on-call runbook assumes "restart takes 10 seconds," and it actually takes 5 minutes because nobody tuned checkpoint frequency against your actual write volume, that's an incident escalation nobody saw coming.

**Trap #5: Not understanding what "committed" actually means at the WAL level.**
This is the classic interview trap. A transaction is only committed if a COMMIT record exists in the WAL *and* was fsynced before the crash. If the client got a success response, the COMMIT record is guaranteed to exist — that's the whole contract of `synchronous_commit=on`. If the client never got success — timeout, connection drop, whatever — the transaction might still complete, or it might roll back; you genuinely don't know until you check. This is why retry logic on the client side needs idempotency keys, not blind "did it work?" assumptions.

[Screen cue: comparison table — rows: synchronous_commit on vs off (latency, data-loss window, use case); wal_level minimal vs replica vs logical (what it enables). Highlight the "off" row in red for financial data, green-check the "on" row.]

## REAL WORLD (8:00–9:30)

Let's ground this in real systems, the kind you'd actually build in an interview or at work.

Think about a UPI-style payment system — the kind PhonePe or Paytm runs at massive scale, processing tens of thousands of transactions per second during peak hours like salary day or a big sale. Every single debit and credit has to hit `synchronous_commit=on`. That fsync costs maybe 1 to 2 milliseconds of extra latency per transaction — and that cost is *completely non-negotiable*, because the alternative is a customer's account balance silently disappearing during a power blip. At that transaction volume, even a 0.6-second loss window from `synchronous_commit=off` could mean thousands of in-flight transactions vanish in a single incident.

Now think about an e-commerce platform like Flipkart during a flash sale. Order writes absolutely need `synchronous_commit=on` — an order is money taken from a customer. But here's the elegant part: once that order lands in the database with WAL enabled at `logical` level, Debezium can tail that exact same WAL stream and push change events into a search index like Elasticsearch, so the order shows up in "my orders" search within milliseconds — with zero additional write load on the primary database. That's the CDC trick: you're not adding a second write path, you're reading a log that already existed for crash safety.

And for something like Swiggy's order tracking or delivery-partner location updates — high-frequency, lower-stakes writes — that's exactly the kind of workload where `synchronous_commit=off` earns its 40% speedup. Losing half a second of a location ping during a rare crash is a non-event; losing a completed payment is a headline.

[Screen cue: three company logo cards side by side — PhonePe/Paytm labeled "sync=on, non-negotiable", Flipkart labeled "sync=on + Debezium CDC to Elasticsearch", Swiggy labeled "sync=off, high-frequency low-stakes writes" — with the relevant numbers (1-2ms fsync cost, 0.6s loss window, 40% speedup) stamped under each.]

## OUTRO + NEXT EPISODE (9:30–10:00)

So here's your one-line takeaway, straight from the architect's playbook: WAL writes the change to a log before applying it to data pages — crash recovery replays the log, making committed transactions permanent and incomplete ones disappear. That single sentence answers most WAL interview questions on its own.

If this helped you understand why your database never loses your data, hit subscribe — because next episode we're going somewhere WAL can't help you: what happens when *two different nodes* both accept a write to the same piece of data, at the same time, and now you have to figure out who's right. That's Episode 37 — Vector Clocks and Write Conflict Detection. See you there.

[Screen cue: end card with episode number "37 — Vector Clocks & Write Conflict Detection" and subscribe button animation.]
