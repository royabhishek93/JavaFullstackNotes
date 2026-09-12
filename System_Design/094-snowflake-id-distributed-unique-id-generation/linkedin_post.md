# Snowflake ID: Distributed Unique ID Generation — LinkedIn Post

## Post Text (copy-paste ready)

1024 workers. 4.2 billion IDs/second. Zero central coordination. Here's the 64-bit trick.

- Snowflake ID = 1 sign bit + 41 bits timestamp + 10 bits worker ID + 12 bits sequence — all minted locally, no round-trip to a central counter
- 12 sequence bits = 4096 IDs/ms/worker = ~4.1M IDs/sec per worker, ~4.2B IDs/sec across 1024 workers
- Because timestamp sits in the highest bits, IDs are roughly time-ordered — as a B-tree primary key, new rows insert at the tail instead of scattering randomly like a UUIDv4 does
- The #1 production trap: clock drift. If NTP corrects a clock backward, you risk a duplicate ID — the fix is to REJECT (throw) or WAIT (spin) rather than silently reuse a (timestamp, sequence) pair
- Discord and Twitter use the same 41/10/12 bit layout; Instagram uses a 76-bit variant with 13 bits for 8192 logical shards

Swipe → to see the exact bit layout, the decode formula, and how worker IDs get assigned via Kubernetes StatefulSet ordinals or ZooKeeper.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
4.2 billion unique IDs/second, zero central coordination. Here's the 64-bit trick behind Snowflake IDs 👇

### Variant B — Long (400–600 chars)
Sharding across hundreds of database nodes means every node needs to generate unique primary keys with zero coordination. UUIDs solve that but cost double the storage and scatter B-tree inserts randomly. Snowflake IDs fix both: a 64-bit long combining a timestamp, worker ID, and per-millisecond sequence counter, minted entirely locally. Because the timestamp sits in the highest bits, IDs sort roughly by creation time — but you must guard against clock drift, or a backward NTP correction can silently produce a duplicate.

---

## Best Time to Post
Monday, 9:00–10:00 AM IST (infrastructure/scaling content performs well opening the week)

## Engagement Hook
"Has your team ever hit a clock-drift bug in a distributed ID generator? How did you catch it?"
