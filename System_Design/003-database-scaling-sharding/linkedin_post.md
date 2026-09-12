# Database Scaling & Sharding — LinkedIn Post

## Post Text (copy-paste ready)

500 million rows. 10-second queries. One wrong sharding choice makes it worse, not better.

- Range sharding is simple but creates a hot shard automatically — all NEW rows go to the latest shard while older shards idle
- Hash sharding spreads load evenly but kills range queries — "all orders from January" now fans out to every shard
- The celebrity problem is real: 1 shard with a 50M-follower account gets hammered while 999 other shards sit idle — fix with a dedicated VIP shard + aggressive caching
- Replication lag causes a nasty trap: user places an order, reads "My Orders" from a replica 200ms behind, sees nothing, panics, and places a duplicate
- Connection pool exhaustion is the silent scaling killer: 50 auto-scaled pods × 10 connections = 500, but Postgres's default max_connections is 100 — the fix is RDS Proxy or PgBouncer, not more pods

Swipe → to see the full scaling ladder (read replicas → connection proxy → sharding → polyglot persistence) and the hot-shard fix.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
500M rows, 10s queries — here's the exact scaling ladder before you shard, and the hot-shard trap that catches everyone 👇

### Variant B — Long (400–600 chars)
A 500-million-row orders table doesn't mean "shard immediately." Most systems scale in order: read replicas first (80% of traffic is reads), then a connection proxy like RDS Proxy before auto-scaling exhausts your DB's max_connections, then sharding only once writes truly outgrow one primary. Pick sharding strategy by access pattern — hash for even load, range for time-series, directory for multi-tenant flexibility. The celebrity/hot-shard problem and replication-lag "my own order disappeared" bug are the two traps every senior engineer has hit at least once.

---

## Best Time to Post
Thursday, 9:00–10:00 AM IST (deep technical posts get strongest engagement mid-week before Friday wind-down)

## Engagement Hook
"Have you ever hit a hot-shard or connection-pool-exhaustion incident in production? What tipped you off first?"
