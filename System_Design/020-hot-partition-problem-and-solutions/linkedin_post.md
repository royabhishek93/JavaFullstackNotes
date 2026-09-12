# Hot Partition Problem and Solutions — LinkedIn Post

## Post Text (copy-paste ready)

One Kafka partition processes 1000x more messages than the rest — because Cristiano Ronaldo just posted.

- Your dashboard says "all systems normal" — that's the trap. Total throughput looks fine while ONE partition drowns. You have to watch per-partition metrics, not averages.
- Sharding by date (created_at) feels logical but is almost always wrong — the "today" shard ends up handling 95% of reads/writes while yesterday's shards sit idle.
- Detection rule: if any partition/shard/node carries >5x the average traffic, it's officially a hot partition.
- Fix 1 — Salt the key (userId + random 0-9) to spread load across partitions. Trade-off: you lose per-key ordering, so add a sequence number and re-sort downstream.
- Fix 2 — Pre-identify hot keys (celebrities, whale merchants) and route them to a dedicated topic/shard with more partitions and independent scaling.
- Fix 3 — Cell-based sharding: split one hot entity's writes across multiple rows (e.g., a high-frequency trader's account split into 10 cells) instead of one hot row.
- Fix 4 — Drop a local Caffeine cache in front of Redis so a viral product page never saturates a single cache node.
- Fix 5 — Backpressure: pause/throttle the consumer on the hot partition before lag explodes into an OOM cascade.

Swipe → to see the diagrams, the decision tree, and the exact commands to detect a hot partition in production.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
One Kafka partition = 1000x the traffic of the rest. Celebrity users, viral products, and date-based shards all cause this. 5 fixes inside. 🔥

### Variant B — Long (400–600 chars)
A celebrity posts, and suddenly one Kafka partition is doing 1000x the work of its neighbors — while your monitoring dashboard calmly reports "all systems normal." That's the hot partition problem: your partitioning key assumed uniform traffic, but reality is power-law distributed. Same failure hits Redis (one node saturated by a viral product) and databases (sharding by date turns "today" into a hot shard). This carousel covers the 5x-average detection rule and 5 real fixes: salting, dedicated hot-key partitions, cell-based sharding, local caching, and backpressure — with the ordering trade-offs interviewers always probe.

---

## Best Time to Post
Tuesday–Thursday, 8–10 AM local time (peak LinkedIn engagement for technical/career content, when engineers and engineering managers check feeds before standups).

## Engagement Hook
Ask in the comments: "Have you ever had a 'system healthy' dashboard while one partition was silently dying? What gave it away?" — invites war stories and boosts comment-driven reach.
