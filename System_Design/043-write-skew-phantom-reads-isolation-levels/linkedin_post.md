# Write Skew & Phantom Reads: Isolation Levels — LinkedIn Post

## Post Text (copy-paste ready)

Two doctors both saw "someone else is on call" and both went home. Zero doctors on call. No dirty read. No lost update. Just write skew.

- Write skew: 2 transactions read overlapping rows, each makes a valid decision, combined writes break an invariant — neither one did anything technically wrong.
- REPEATABLE READ does NOT stop this. Only SERIALIZABLE or explicit SELECT FOR UPDATE does.
- Optimistic locking (version columns) protects one row from a lost update — it does nothing against a phantom insert.
- PostgreSQL SERIALIZABLE (SSI) costs ~10-20% throughput vs REPEATABLE READ but auto-detects the conflict and aborts one transaction for retry.
- Flash-sale scale (millions of concurrent buyers)? Even SELECT FOR UPDATE chokes on lock contention — real systems fall back to READ COMMITTED + idempotency key + atomic counter in Redis.

Swipe → to see the hospital scenario, the seat-booking phantom read, the 4-solution comparison, and the exact interview answer for "how do you stop two users from booking the same last seat."

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Two doctors both go home. Zero doctors on call. That's write skew — and REPEATABLE READ won't save you. Full breakdown 👇

### Variant B — Long (400–600 chars)
A hospital rule: always keep 1 doctor on call. Two doctors check the schedule, both see the other is covering, both leave. Zero doctors on call — and neither one made a technically wrong decision. That's write skew: two transactions reading overlapping data, each valid alone, together breaking an invariant. It's why payment systems use SELECT FOR UPDATE on account rows for double-spend prevention, and why flash-sale ticket booking abandons strict locking entirely for Redis atomic counters at scale. Only SERIALIZABLE or explicit row locks stop it — REPEATABLE READ isn't enough. Full isolation-level breakdown with the exact interview answer in the carousel.

---

## Best Time to Post
Tuesday or Wednesday, 8:30–9:30 AM IST (before the Indian tech workday starts, catches commute/coffee scrolling).

## Engagement Hook
Which isolation level does your production database actually run at right now — do you even know? Drop it in the comments.
