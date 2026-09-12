# Database Sharding: Range, Hash & Consistent Hashing — LinkedIn Post

## Post Text (copy-paste ready)

Adding 1 shard to a 3-shard cluster just triggered a 75% data migration. Here's why.

- Hash sharding (shard = hash(key) % N): adding a shard changes N, which reassigns almost every key at once — 75-90% of data migrates
- Consistent hashing fixes it: shards live on a ring, only the keys between the new node and its neighbor move — roughly 1/N of your data, not 75%
- Cassandra uses 150 virtual nodes per physical shard by default, so load stays proportional even across mismatched hardware
- Cross-shard JOINs don't work at all — the fix is co-locating related tables by the same shard key, or denormalizing to avoid the JOIN entirely
- A good shard key needs 4 things: high cardinality, even distribution, present in most queries, and immutable — email fails on immutability, country_code fails on cardinality

Swipe → to see all 3 sharding strategies compared, plus the 4-phase migration plan for resharding without downtime.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
1 line of code (%3 → %4) can trigger a 75% data migration. Here's the sharding strategy that avoids it entirely 👇

### Variant B — Long (400–600 chars)
Hash sharding gives you even distribution, until you need to add a shard — then the modulo changes and 75-90% of your data has to migrate at once. Consistent hashing solves this: shards sit on a ring, and adding a node only remaps the keys between it and its neighbor, roughly 1/N of your data. It's why Cassandra, DynamoDB, and Redis Cluster all use it. Combine it with careful shard-key selection (high cardinality, even distribution, immutable, present in your queries) and you avoid the two most common sharding disasters.

---

## Best Time to Post
Tuesday, 9:00–10:00 AM IST (technical deep-dives perform best early in the work week)

## Engagement Hook
"Have you ever had to reshard a production database? How much data did you end up migrating?"
