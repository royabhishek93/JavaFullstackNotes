# Social Graph Storage & "People You May Know" — LinkedIn Post

## Post Text (copy-paste ready)

1 billion users. 300 billion connections. "Who follows Alice" can become a scatter query across dozens of shards.

- The fix: write every connection TWICE — once keyed by user_id ("who do I know"), once keyed by friend_id ("who knows me") — both in one atomic Cassandra batch. 2x storage, but O(1) partition reads in both directions at 2-8ms
- "People You May Know" is a completely different problem — for each of your friends, fetch THEIR friends, count mutual-connection paths, rank by that count
- The scary math: 500 connections × 500 connections each = 250,000 raw candidate pairs for ONE user. Across 1B users, naive fan-out = 250 TRILLION pairs — infeasible
- Mitigations: cap fan-out to your ~200 most active connections, sample for super-connectors (recruiters with 30K+ connections), use Spark combiners to pre-aggregate before the final shuffle
- Never compute PYMK live — it's a nightly Spark GraphX batch job (4-6 hours), cached, served in <10ms — vs. minutes for a live 2-hop traversal

Swipe → to see the bidirectional Cassandra schema and when you actually need a native graph DB like Neo4j instead.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
"Who follows Alice" can become a scatter query across dozens of shards at scale. Here's how LinkedIn avoids that 👇

### Variant B — Long (400–600 chars)
Storing a social graph at billion-user scale means every connection gets written twice — once keyed for outgoing lookups, once for incoming — trading 2x storage for O(1) reads in both directions. "People You May Know" is a separate problem entirely: a nightly batch job that fans out to friends-of-friends, counts mutual connections, and caches the ranked result — never computed live, because the raw candidate math explodes into hundreds of trillions of pairs at scale without careful fan-out capping and sampling.

---

## Best Time to Post
Tuesday, 9:00–10:00 AM IST (graph/data-modeling deep-dives perform well early in the week)

## Engagement Hook
"Has your platform had to deal with 'super-connector' users breaking a graph algorithm's assumptions? How did you handle it?"
