Quorum Reads/Writes (Cassandra W+R>N) — LinkedIn Post

## Post Text (copy-paste ready)

Your Cassandra cluster's default settings (W=1, R=1) let a user's message vanish on refresh — here's the 1-line fix.

- Cassandra doesn't guarantee consistency by default — W=1, R=1 out of the box means a write to Node 1 and a read from Node 3 can silently disagree
- The fix is one formula: W + R > N guarantees the read set and write set always overlap on at least one node
- QUORUM reads wait for the (N/2)+1th response — the SECOND-slowest node, not the fastest — so consistency costs latency (~10ms at ONE vs 200ms worst-case at QUORUM)
- Read repair auto-heals stale replicas in the background (10% of reads trigger it even with no visible disagreement)
- Never use W=ALL, R=ALL — one node down and every read/write fails outright; use QUORUM instead (tolerates node failures)

Swipe → to see: the overlap proof, the full N=3 tunable consistency matrix, and where W=2/R=2 shows up in real chat + payment systems.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Cassandra's default settings can silently lose your data. The fix is one formula: W + R > N. Full breakdown 👇

### Variant B — Long (400–600 chars)
Ever seen a "sent" message disappear on refresh? That's Cassandra's default W=1, R=1 eventual consistency showing up in production. The fix isn't complicated — it's one formula: W + R > N. When write quorum plus read quorum exceeds your replication factor N, the read set and write set are mathematically guaranteed to overlap on at least one node, and that node always has the fresh data. The trade-off: QUORUM reads wait for the second-slowest node, not the fastest — you're paying latency for correctness. This post breaks down the overlap proof, Cassandra's consistency levels (ONE/QUORUM/ALL/LOCAL_QUORUM/EACH_QUORUM), read repair, and where chat and payment systems actually configure W and R in production. Save it for your next system design round.

---

## Best Time to Post
Tuesday or Wednesday, 8:00–9:30 AM IST (before the Indian tech workday starts, catches commute scrolling)

## Engagement Hook
What consistency level does your team actually run in production — QUORUM everywhere, or ONE for speed and hoping for the best?
