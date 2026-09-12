# Kafka Log Compaction & Tombstones — LinkedIn Post

## Post Text (copy-paste ready)

A consumer down for 3 days can silently miss a delete. Here's the Kafka setting that prevents it.

- Log compaction keeps exactly ONE record per key forever — a background thread deletes older duplicates, keeping surviving records at their original offsets
- To delete a key entirely, write a "tombstone" (null value) — compaction keeps the tombstone around for `delete.retention.ms` (default 24h) so consumers can react, then purges it
- The trap: if a consumer is down LONGER than `delete.retention.ms`, it replays the log and never sees tombstones purged during its downtime — its local state believes deleted keys are still active, silently, forever
- Fix: size `delete.retention.ms` around your worst-case consumer downtime, not the 24h default
- Compaction is NOT real-time — the active segment is never compacted, and it only shrinks a topic if key cardinality is bounded (a random UUID per event never compacts)

Swipe → to see the before/after of a compaction pass and the full tombstone lifecycle.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
A consumer down for 3 days can silently miss a delete in Kafka. Here's the setting that prevents it 👇

### Variant B — Long (400–600 chars)
Log compaction keeps exactly one record per key forever — perfect for KTable changelogs, config topics, and "current state" caches. Deleting a key means writing a tombstone (null value), which compaction keeps around for `delete.retention.ms` (default 24h) before purging. The trap: a consumer down longer than that window replays the log and never sees the tombstone, silently believing a deleted key is still active. Size the retention window around your worst-case consumer downtime, not the default.

---

## Best Time to Post
Thursday, 9:00–10:00 AM IST (Kafka/streaming infrastructure content performs well mid-week)

## Engagement Hook
"Has a Kafka consumer outage ever caused your team to miss a tombstone/delete event? How did you catch it?"
