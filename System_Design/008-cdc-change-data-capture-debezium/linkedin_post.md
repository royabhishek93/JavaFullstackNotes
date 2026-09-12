# Change Data Capture with Debezium — LinkedIn Post

## Post Text (copy-paste ready)

A DB write and a Kafka publish are NEVER atomic on their own. CDC fixes this structurally.

- Dual-write (write to DB, then publish to Kafka) breaks the moment Kafka is unavailable for even 100ms — permanently out of sync, silently
- Debezium reads Postgres's own Write-Ahead Log (the same log used for crash recovery) and turns every INSERT/UPDATE/DELETE into a Kafka event — no application code changes
- One WAL stream can feed unlimited consumers: Elasticsearch sync (~100ms lag), Redis cache invalidation (~50ms), analytics warehouse, audit log — all independently
- The real fix for atomicity is the Outbox Pattern: write your event to an "outbox" table in the SAME transaction as the business write — CDC then streams the outbox, guaranteeing both succeed or both fail
- The #1 operational trap: if your Kafka consumer falls behind, Postgres can't reclaim WAL disk space — monitor replication slot lag and alert above ~500MB

Swipe → to see the outbox pattern architecture and the exact monitoring query to catch slot lag before it fills your disk.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
A DB write and a Kafka publish are never atomic on their own — here's how Debezium + the Outbox Pattern fixes that structurally 👇

### Variant B — Long (400–600 chars)
Dual-writing to a database and Kafka separately is fragile — the moment Kafka blips, you're silently out of sync with no error to catch it. Change Data Capture with Debezium reads Postgres's own Write-Ahead Log and streams every change to Kafka automatically, regardless of where the change came from. Pair it with the Outbox Pattern — writing your event to an outbox table in the same transaction as your business write — and you get true atomicity. The operational trap: monitor replication slot lag, or a stalled consumer will fill your database's disk.

---

## Best Time to Post
Monday, 9:00–10:00 AM IST (infrastructure/data-pipeline content performs well at the start of the week)

## Engagement Hook
"Has a dual-write inconsistency ever bitten your team in production? What tipped you off?"
