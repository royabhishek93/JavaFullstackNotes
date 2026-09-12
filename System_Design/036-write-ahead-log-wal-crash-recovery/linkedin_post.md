# Write-Ahead Log (WAL) & Crash Recovery — LinkedIn Post

## Post Text (copy-paste ready)

A power blip mid-write should corrupt your database. It doesn't. Here's the 1 rule that saves it.

- Never write to a data page first — write to an append-only log first, fsync it, THEN return "commit success."
- Data pages get updated later, lazily, in the background — a crash there is 100% recoverable by replaying the log.
- `synchronous_commit=off` gives you 40% faster writes but opens a ~0.6 second data-loss window — fine for analytics, catastrophic for payments.
- Replication slots (used by Debezium/CDC) can silently make `pg_wal` grow unbounded if Kafka goes down — until the disk fills and the primary crashes.
- CDC tools don't add write overhead — they just tail the same WAL that was already being written for crash recovery.

Swipe → to see the crash-recovery timeline, the sync vs async commit tradeoff, and the exact interview answer for "what happens when Postgres crashes mid-transaction."

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Your DB survives power failures because of ONE rule: log first, data page second. Full breakdown 👇

### Variant B — Long (400–600 chars)
Every production database — Postgres, MySQL, Oracle — makes the same promise: a committed transaction survives a crash, no matter when the power dies. The trick is the Write-Ahead Log: every change is written to an append-only log and fsynced BEFORE the data page is touched. Crash mid-write to the actual data? Irrelevant — recovery just replays the log. This is also why CDC tools like Debezium have near-zero overhead: they read the same log your DB already writes for crash safety. Full breakdown of synchronous_commit tradeoffs, wal_level settings, and the replication-slot-lag trap that fills disks in production — in the carousel.

---

## Best Time to Post
Tuesday or Wednesday, 8:30–9:30 AM IST (before the Indian tech workday starts, catches commute scrolling)

## Engagement Hook
Have you ever had a replication slot lag fill up your disk in production? Drop the war story below.
