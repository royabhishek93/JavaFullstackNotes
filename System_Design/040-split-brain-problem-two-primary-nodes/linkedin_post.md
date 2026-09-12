# Split-Brain Problem: Two Primary Nodes — LinkedIn Post

## Post Text (copy-paste ready)

A 30-second network blip once meant order #1001 got charged to Alice AND Bob — on two different "primary" databases.

That's split brain. Here's what actually causes it:

- Replica misses heartbeat → promotes itself → old primary never actually died → both accept writes
- Any write acknowledged but not yet replicated when this happens = permanently lost
- Redis Sentinel's fix: primary with `min-replicas-to-write 1` refuses writes if zero replicas are connected
- ZooKeeper/etcd (Raft/Zab): mathematically impossible for two nodes to both hold a majority — no split brain, ever
- Cassandra has no primary at all — it's leaderless and resolves conflicts with last-write-wins, but clock skew between nodes can pick the WRONG winner silently

Swipe → to see how fencing (STONITH), quorum, and epoch checks each solve this differently — and which system uses which.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Two primaries, one database, zero warning. Split brain explained in under 10 minutes 👇

### Variant B — Long (400–600 chars)
Ever wonder what actually happens when a database "failover" goes wrong? A network partition triggers a replica to promote itself — but the old primary never died. For 60 seconds, both nodes accept writes independently. When the network heals: duplicate order IDs, double-debited accounts, lost writes. This is split brain, and it's why senior interviewers ask "what happens when the network partitions?" the moment you mention primary/replica. The fix isn't a longer timeout — it's quorum (mathematically only one side can have a majority) or fencing (kill the old primary before the new one starts). Full breakdown of how ZooKeeper, etcd, MySQL, Redis Sentinel, and Cassandra each handle it.

---

## Best Time to Post
Tuesday or Wednesday, 8:30–9:30 AM IST (commute scroll window for Indian tech audience)

## Engagement Hook
Have you ever debugged a production incident that turned out to be split brain? What was the giveaway sign?
