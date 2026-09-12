# TIMEUUID: Time-Ordered Clustering Keys in Cassandra — LinkedIn Post

## Post Text (copy-paste ready)

We shipped comments on Cassandra with a random UUID primary key. They rendered in random order.

- Cassandra is masterless — 6 nodes, 3 datacenters — so `AUTO_INCREMENT` literally cannot exist; there's no single coordinator to hand out 1, 2, 3...
- A random UUID v4 is 128 bits of pure randomness — zero relationship between the value and when it was created, so sorting by `id` gives you garbage order.
- The fix: TIMEUUID (v1 UUID) — its first bits ARE a 100-nanosecond-precision timestamp since 1582, so Cassandra sorts it chronologically, natively, with no `ORDER BY` and no extra `created_at` column.
- Because Cassandra physically stores rows on disk in clustering-key order, this gets us p99 read latency of ~2-5ms for a single partition — already time-sorted.
- The trap: client clocks drift. 300 microseconds of NTP skew between two app servers can reorder comments by a few hundred microseconds to a few ms. Fine for a comment thread. Never acceptable for a payments ledger — that needs a Snowflake ID instead.

Swipe → to see: the 128-bit anatomy of a TIMEUUID, the clock-skew failure diagram, and the full TIMEUUID vs Snowflake ID vs ULID comparison table.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Random UUIDs make terrible sort keys. Here's the 128-bit trick Cassandra uses to sort comments by time — for free. 🎥👇

### Variant B — Long (400-600 chars)
Cassandra has no single coordinator, so `AUTO_INCREMENT` can't exist — any of your 6 nodes can accept a write at the same instant. The obvious fallback, a random UUID v4, breaks ordering completely: it's 128 bits of pure randomness with zero link to creation time. The real fix is TIMEUUID — a version-1 UUID whose first bits are a 100ns-precision timestamp, so it sorts chronologically on its own. Rows land on disk pre-sorted, reads hit ~2-5ms p99, no ORDER BY, no extra column. The catch: client clock skew (even ~300µs) can reorder writes — imperceptible for comments, disqualifying for financial ledgers, where you'd reach for a Snowflake ID instead. Full breakdown, comparison table, and the exact interview answer in the carousel.

---

## Best Time to Post

Tuesday or Wednesday, 8:00–9:30 AM IST (commute scroll window for Indian tech audience, before standups start).

## Engagement Hook

Have you ever had to explain to your team *why* a random UUID broke sort order in production — what did you switch to?
