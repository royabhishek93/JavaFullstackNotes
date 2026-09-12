# B-Tree vs LSM Tree — LinkedIn Post

## Post Text (copy-paste ready)
LSM Trees write 100K-500K ops/sec. B-Trees write 10K-50K/sec. Here's why — and why MySQL still wins for payments.

- MySQL InnoDB (B-Tree) splits a page on every insert once it's full — and that split can cascade up the tree, turning "one insert" into multiple random disk writes.
- Cassandra/RocksDB (LSM Tree) writes are O(1): append to the WAL, insert into an in-memory MemTable, ACK the client. No searching, no splits.
- Bloom Filters on every SSTable answer "definitely not here" in nanoseconds — so LSM reads skip most disk I/O instead of scanning every file.
- The catch: compaction can eat 30-50% of your disk I/O bandwidth. LSM doesn't remove the write cost — it defers it and makes it sequential instead of random.
- Cassandra secondary index trap: querying `type='comment'` across all users means hitting every node in the cluster. Route that to a data warehouse via Kafka — don't fight the partition key.

Real example: WhatsApp-style chat runs on Cassandra doing ~500K messages/sec (append-only, partitioned by chat_id). A payment system runs on MySQL InnoDB because ACID isn't negotiable — write volume is moderate, but every transaction must be consistent.

Swipe → to see the write/read path diagrams and the full decision framework.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---
## Caption Variants

### Variant A — Short (150 chars max)
B-Tree = fast reads, slow writes (page splits). LSM Tree = fast writes, deferred cost (compaction). Know which one your interview answer needs.

### Variant B — Long (400–600 chars)
Why does MySQL use a B-Tree and Cassandra use an LSM Tree? It's not arbitrary — it's a write/read tradeoff. B-Tree keeps data balanced for O(log N) reads, but inserts can trigger cascading page splits. LSM Tree makes writes O(1) (append to MemTable + WAL), but reads check multiple SSTables — sped up by Bloom Filters — and compaction quietly consumes 30-50% of disk I/O in the background. Payment systems need MySQL's ACID guarantees. Chat apps doing 500K msgs/sec need Cassandra's write throughput. Full breakdown — diagrams, decision tree, and the secondary-index trap interviewers love to test — in the post.

---
## Best Time to Post
Tuesday–Thursday, 8–10 AM local time (peak LinkedIn engagement for tech/career audiences).

## Engagement Hook
End the post with a question: "Which one would you pick for a leaderboard that ingests 200K score updates/sec but only needs top-10 reads? Drop your answer below."
