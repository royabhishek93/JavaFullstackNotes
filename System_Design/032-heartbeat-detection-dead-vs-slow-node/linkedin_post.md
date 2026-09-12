# Heartbeat Detection: Dead vs Slow Node — LinkedIn Post

## Post Text (copy-paste ready)

A 22-second GC pause once made a Redis cluster run with TWO primaries at the same time.

- Heartbeat detection can never be 100% certain — a silent node is a statistical bet, not a fact
- Timeout too short (e.g. 5s) → GC pauses (5-30s on loaded JVMs) trigger false failovers → split brain risk
- Timeout too long → real crashes go undetected for way too long, users see errors the whole time
- Naive heartbeats don't scale: 100 nodes pinging each other = ~9,900 msgs/sec (O(N²)) — gossip protocol fixes this with O(log N) propagation
- Phi Accrual (Cassandra/Akka) replaces binary alive/dead with an adaptive suspicion score, so it survives GC pauses without panicking

Swipe → to see the gossip protocol spread, the Phi Accrual formula, and real timeout values from Redis Sentinel, Kubernetes, etcd, ZooKeeper and Cassandra.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Can a node ever KNOW a peer is dead vs. just slow? No. Here's how Redis, Cassandra & etcd make that bet anyway. 🎥👇

### Variant B — Long (400–600 chars)
Your Redis primary hits a 22-second GC pause. Sentinel's timeout is 30s default — so it doesn't fail over... but if that pause hits 30s+, you get a false "node is dead" verdict, a promoted replica, and a split-brain cluster with two primaries. This is the core trade-off of heartbeat detection: short timeouts risk false positives, long timeouts risk slow real-failure detection. In this post I break down gossip protocols (Cassandra/Consul), Phi Accrual failure detection (Cassandra/Akka), and the actual timeout values used in production — Redis Sentinel, Kubernetes, etcd, ZooKeeper, Kafka. If you're prepping for system design interviews, this is a pattern that comes up constantly.

---

## Best Time to Post
Tuesday or Wednesday, 8:30–9:30 AM IST (commute/pre-work scroll window for Indian tech audience)

## Engagement Hook
What timeout would YOU set for a Redis Sentinel guarding a payments-critical primary — and why?
