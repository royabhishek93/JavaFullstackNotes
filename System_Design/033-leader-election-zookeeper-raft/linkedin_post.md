# Leader Election: ZooKeeper & Raft — LinkedIn Post

## Post Text (copy-paste ready)

Two "leader" nodes accepting writes at the same time. Same key. Different values. That's split brain — and it's silent until someone's balance is wrong.

Here's how ZooKeeper and Raft actually stop it:

- ZooKeeper: candidates race to create ephemeral sequential znodes — lowest number wins, no voting needed. Leader dies → ZK auto-deletes its znode after a 10–30s session timeout → next node in line takes over.
- Followers don't all watch the leader directly — each one watches only the node ONE position below it ("chain watching"). Otherwise every follower hits ZooKeeper simultaneously the moment the leader dies (thundering herd).
- Raft: every follower has a randomized election timeout (150–300ms). First one to time out becomes candidate, votes for itself, asks for votes — majority wins in ~150ms.
- Raft's safety net: a candidate with a stale log CANNOT win, even with a higher term. Voters check log recency too — this is how Raft guarantees zero data loss during failover.
- Kafka partition leadership and Kubernetes' etcd both run on this exact mechanism under the hood.

Swipe → to see the full election timeline, the split-vote problem, and the ZooKeeper vs Raft vs etcd comparison table.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Split brain happens in seconds. Here's exactly how ZooKeeper and Raft elect one leader and stop it. 🎥👇

### Variant B — Long (400–600 chars)
Five nodes. One should be the leader. But who decides — and what happens the second it crashes?

ZooKeeper answers with ephemeral sequential znodes: lowest number wins, no voting round-trip. Raft answers with randomized timeouts (150–300ms) and majority voting, plus a critical rule — a node with a stale log can never win, no matter how fast it requests votes.

Kafka's partition leaders and Kubernetes' etcd both run on this exact logic. If you've ever wondered why a broker failover takes seconds instead of minutes, this is why.

Full breakdown in the carousel — save it for your next system design round.

---

## Best Time to Post
Tuesday or Wednesday, 8:30–9:30 AM IST (before the Indian tech workday starts, catches commute + coffee scrolling).

## Engagement Hook
Have you ever debugged a split-brain incident in production — what tipped you off that two nodes both thought they were the leader?
