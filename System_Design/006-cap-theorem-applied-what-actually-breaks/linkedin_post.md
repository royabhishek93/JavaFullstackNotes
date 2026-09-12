# CAP Theorem Applied — LinkedIn Post

## Post Text (copy-paste ready)

Same network partition. Your feed shows a 30-second-old post. Your payment system returns a 503. Both are correct.

- CAP isn't a whiteboard choice — partitions are mandatory, so the real decision is: stay available with stale data (AP), or refuse and stay consistent (CP)?
- Social feed on Cassandra (AP): a partition means a stale read for a few seconds — completely fine for a timeline
- Payment system (CP): same partition means a 503 instead of processing against a possibly-wrong balance — correctness beats uptime here
- The trap: CAP isn't ONE choice for your whole system — product catalog is AP, inventory decrement at checkout is CP, in the exact same product
- Cassandra's default last-write-wins can silently lose increments on a "like count" — fix with counter columns (CRDTs) that merge by summing, not overwriting

Swipe → to see how CP vs AP maps across real subsystems, and why PACELC matters more than CAP on a normal (non-partitioned) day.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Same outage. Feed shows stale data. Payments return a 503. Both are the CORRECT CAP choice for that subsystem 👇

### Variant B — Long (400–600 chars)
CAP theorem isn't one decision for your whole system — it's a per-subsystem choice. A social feed on Cassandra is AP: during a partition, users see slightly stale posts, which is fine. A payment system is CP: during that same partition, it returns an error rather than risk processing against a stale balance. The real trap is treating CAP as a single design-time decision instead of asking, subsystem by subsystem, "is a stale answer worse than no answer here?"

---

## Best Time to Post
Wednesday, 9:00–10:00 AM IST (mid-week deep-dive content performs consistently well)

## Engagement Hook
"Which subsystem in your current product made the wrong CAP choice — and how did you find out?"
