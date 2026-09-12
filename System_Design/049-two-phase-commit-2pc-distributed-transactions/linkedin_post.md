# Two-Phase Commit (2PC) — LinkedIn Post

## Post Text (copy-paste ready)

A coordinator crash at t=7ms once left two databases holding locks for 5 straight minutes. Nothing was wrong with the data — the protocol just had no way to recover.

- 2PC has 2 phases: PREPARE (lock + WAL + vote YES/NO) then COMMIT/ABORT — clean in theory, until the coordinator itself fails between the two
- If the coordinator crashes after all participants vote YES but before sending COMMIT, every participant is stuck holding locks indefinitely — this is the "blocking problem," and it's not theoretical, it's happened in production
- Worst case: the coordinator's WAL is lost too — now a human has to manually inspect both databases and decide commit-or-rollback by hand
- The performance tax is real: a single-DB transaction costs ~2ms, the same operation wrapped in XA 2PC costs 10-50ms — fine at 1,000 TPS, a bottleneck at 100,000 TPS
- The architect's answer in interviews: skip 2PC for microservices entirely — use the Outbox Pattern + Saga (local transaction + outbox table + Debezium + Kafka) with compensating transactions instead

Swipe to see: the full PREPARE/COMMIT flow, the failure-mode matrix, and the exact interview one-liner.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Coordinator crashes at t=7ms, both DBs stay locked for 5 minutes. Here's why 2PC blocks — and what to use instead in microservices 👇

### Variant B — Long (400–600 chars)
Two-Phase Commit sounds bulletproof: PREPARE, everyone votes YES, then COMMIT — atomicity across databases guaranteed. Except if the coordinator crashes in the gap between "all votes received" and "COMMIT sent," every participant is stuck holding locks with no way to decide on its own. That's not a rare edge case — it's the reason banking cores and enterprise ERPs (SAP, Oracle) still use XA 2PC while every high-throughput microservice system moved to Saga with compensating transactions instead. Know when 2PC is the right call, and when it's the wrong one — that distinction is a real interview differentiator.

---

## Best Time to Post
Wednesday, 9:00–10:00 AM IST (mid-week technical deep-dives get strongest engineer engagement)

## Engagement Hook
"Has a distributed transaction coordinator ever left your database holding locks longer than you expected? What did the recovery actually look like?"
