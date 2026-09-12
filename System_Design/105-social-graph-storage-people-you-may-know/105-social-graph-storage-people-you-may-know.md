# Social Graph Storage & "People You May Know"
### How LinkedIn/Facebook store a billion-edge friend graph AND turn it into a recommendation feature

---

## PART 1 — THE STUDENT CONVERSATION

Imagine you're building the "friends" feature for a social network. The naive idea: one table, `friendships(user_id, friend_id)`. To find "who does Alice follow," you run `SELECT friend_id FROM friendships WHERE user_id = 'alice'`. To find "who follows Alice," you run `SELECT user_id FROM friendships WHERE friend_id = 'alice'`. Both queries look fine on a whiteboard.

Now scale it up. You have 1 billion users and 300 billion edges (connections). That second query — "who follows Alice" — if `friend_id` isn't indexed the same way, becomes a full scan of a 300-billion-row table. Even with an index, at that scale, a poorly partitioned table means the query might hit dozens of different physical shards to assemble one answer, because a single "friendships" table sharded by `user_id` puts Alice's outgoing edges on one shard and her incoming edges scattered across every shard that has a user who follows her.

The fix mirrors a trick you use with paper filing cabinets: if you need to look things up two different ways (by sender AND by receiver), keep two copies of the data, each filed under the way you'll look it up. So for every connection, you write it twice: once as a row keyed by `user_id` (so "who does Alice know" is a single-partition read), and once as a row keyed by `friend_id` (so "who knows Alice" is also a single-partition read). This is denormalization for read performance — you pay extra storage and a slightly trickier write path (two writes instead of one), in exchange for every graph read being O(1) partition lookups instead of a scatter query.

This is exactly what wide-column stores like Cassandra are built for: a partition key that colocates all the rows you need for one query onto one physical node, so a single-partition read is fast no matter how big the total dataset is.

But storing the graph is only half the story. The other half — "People You May Know" (PYMK) — is a completely different beast. It isn't a storage problem, it's a graph-algorithm problem: given Alice's 1st-degree connections, find candidates 2 hops away (her friends' friends) who aren't already her friends, and rank them by how many mutual friends they share with her. That's not something you want to compute live on every page load — it's a batch analytics job that touches nearly the whole graph, so it runs offline overnight and the results are cached, ready to serve instantly the next morning.

---

## PART 2 — THE SOCIAL GRAPH ARCHITECTURE DIAGRAMS

### Bidirectional Storage in Cassandra: Two Rows Per Connection

```
Alice connects with Bob (mutual follow / friend request accepted)

Application writes TWO rows in ONE logical operation (batch statement):

Table: connections_by_user
Partition key: user_id
─────────────────────────────────────────────────────────
| user_id (PK) | friend_id | connected_at        | status  |
|--------------|-----------|---------------------|---------|
| alice        | bob       | 2026-08-20T09:00:00Z| ACTIVE  |
| alice        | charlie   | 2026-07-11T14:22:00Z| ACTIVE  |
| alice        | dave      | 2026-01-03T08:15:00Z| ACTIVE  |

  Query: "who does Alice know?"
  SELECT friend_id FROM connections_by_user WHERE user_id = 'alice';
  → single partition read, ~2-5ms, regardless of total graph size

Table: connections_by_friend   (the "reverse index" copy)
Partition key: friend_id
─────────────────────────────────────────────────────────
| friend_id (PK)| user_id   | connected_at        | status  |
|---------------|-----------|---------------------|---------|
| bob           | alice     | 2026-08-20T09:00:00Z| ACTIVE  |
| bob           | erin      | 2026-08-19T11:40:00Z| ACTIVE  |

  Query: "who knows Bob?"
  SELECT user_id FROM connections_by_friend WHERE friend_id = 'bob';
  → also a single partition read, ~2-5ms

Write path (LOGGED BATCH, both writes succeed or both fail):
  BEGIN BATCH
    INSERT INTO connections_by_user  (user_id, friend_id, connected_at, status)
      VALUES ('alice', 'bob', toTimestamp(now()), 'ACTIVE');
    INSERT INTO connections_by_friend(friend_id, user_id, connected_at, status)
      VALUES ('bob', 'alice', toTimestamp(now()), 'ACTIVE');
  APPLY BATCH;

Cost:  2x storage, 2x write ops per connection.
Gain:  O(1) partition lookups both directions, no cross-shard scatter.
       For a symmetric "friend" relationship, connections_by_user and
       connections_by_friend can actually collapse into ONE table if
       every insert is done symmetrically (alice→bob AND bob→alice) —
       common in Facebook-style mutual friendships. Twitter/LinkedIn-style
       asymmetric "follow" relationships need the true two-table split
       above because A following B does not imply B following A.
```

### Native Graph DB (Neo4j) for Multi-Hop Traversal

```
When the query is NOT "give me Alice's direct connections" but
"find the shortest path of professional intros between Alice and
a hiring manager at Company X, going through people Alice knows" —
that's a multi-hop traversal, and Cassandra-style partition lookups
fall apart because each hop requires a NEW partition read, and the
number of partition reads explodes combinatorially with hop depth.

Cassandra approach to a 3-hop query (BAD):
  Hop 1: read alice's ~500 connections           → 1 partition read
  Hop 2: read each of those 500 people's conns   → 500 partition reads
  Hop 3: read each of THOSE people's connections → up to 250,000 reads
  Total: ~250,501 reads for one 3-hop query. Infeasible online.

Neo4j approach (index-free adjacency — pointers, not lookups):
  MATCH path = shortestPath(
    (alice:Person {id:'alice'})-[:KNOWS*..4]-(hm:Person {id:'hiring_mgr_42'})
  )
  RETURN path;

  Internally: each node stores direct in-memory pointers to its
  relationship records (no index lookup per hop — pointer chasing,
  O(1) per edge traversal regardless of total graph size).
  Typical latency for a 3-4 hop shortestPath query on a graph with
  50M nodes / 500M edges: 10-80ms.

  ┌──────────┐   KNOWS    ┌──────────┐   KNOWS    ┌────────────┐
  │  alice   │───────────▶│   dave   │───────────▶│ hiring_mgr │
  └──────────┘            └──────────┘             └────────────┘
       │                                                  ▲
       │ KNOWS          ┌──────────┐   KNOWS              │
       └───────────────▶│  frank   │──────────────────────┘
                         └──────────┘
  shortestPath = alice → frank → hiring_mgr  (2 hops, chosen over 3-hop path)

Tradeoff:
  - Cassandra: cheap, horizontally scalable, great for 1-hop "who are
    my connections" reads at massive write throughput (LinkedIn/FB scale).
  - Neo4j: purpose-built for multi-hop path-finding, "mutual connections"
    queries, and graph algorithms (PageRank, community detection) — but
    horizontal write scaling is harder, and it's usually run as a
    secondary/derived store fed by CDC from the primary Cassandra graph,
    not as the system of record for 300B+ edges.
```

### PYMK Candidate Generation: 2nd-Degree Fan-Out

```
Alice's 1st-degree connections (500 people): Bob, Charlie, Dave, ...

For EACH 1st-degree connection, fetch THEIR 1st-degree connections
(Alice's 2nd-degree candidates):

  Bob's connections (500)     → candidates: {Erin, Frank, Alice, ...}
  Charlie's connections (500) → candidates: {Frank, Grace, Alice, ...}
  Dave's connections (500)    → candidates: {Erin, Henry, Alice, ...}
  ... x 500 first-degree connections

  Raw candidate pool BEFORE dedup: 500 × 500 = 250,000 (person, mutual-source) pairs

  Mutual-connection counting (group by candidate, count distinct sources):
  ┌───────────┬──────────────────────────────┬───────────────┐
  │ Candidate │ Mutual connections (via)     │ Mutual count  │
  ├───────────┼──────────────────────────────┼───────────────┤
  │ Erin      │ Bob, Dave, Henry             │ 3             │
  │ Frank     │ Bob, Charlie                 │ 2             │
  │ Grace     │ Charlie                      │ 1             │
  │ Alice     │ (self — FILTERED OUT)        │ —             │
  │ Bob       │ (already 1st-degree — FILTER)│ —             │
  └───────────┴──────────────────────────────┴───────────────┘

  After filtering (remove self + existing connections) and dedup:
  250,000 raw pairs → typically 5,000-20,000 unique candidates
  (real graphs are clustered/triadic-closure heavy, so the same
  candidates reappear via many paths — that's WHY they rank high)

  Rank by mutual_count DESC, take top 50 → shown as "People You May Know"
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Cassandra Schema (CQL)

```sql
CREATE TABLE connections_by_user (
    user_id       text,
    friend_id     text,
    connected_at  timestamp,
    status        text,           -- ACTIVE, PENDING, BLOCKED
    PRIMARY KEY (user_id, friend_id)
) WITH CLUSTERING ORDER BY (friend_id ASC);

CREATE TABLE connections_by_friend (
    friend_id     text,
    user_id       text,
    connected_at  timestamp,
    status        text,
    PRIMARY KEY (friend_id, user_id)
) WITH CLUSTERING ORDER BY (user_id ASC);

-- Reads are always single-partition, bounded by connection count (~500-5000 rows):
SELECT friend_id FROM connections_by_user WHERE user_id = 'alice';
-- p99 latency at 300B edges: 3-8ms (single node, in-memory row cache hit)
```

### PYMK as an Offline Batch Job (Spark GraphX Pseudocode)

```scala
// Nightly Spark GraphX job, runs over the FULL connection graph snapshot
// (loaded from Cassandra via a bulk export, NOT live queries)

val edges: RDD[Edge[Byte]] = loadConnectionsFromCassandraSnapshot()
val graph: Graph[Long, Byte] = Graph.fromEdges(edges, defaultValue = 0L)

val pymkCandidates = graph.aggregateMessages[Map[VertexId, Int]](
  // For each edge A-B, B tells A about ITS neighbors (2nd-degree fan-out)
  triplet => {
    triplet.sendToSrc(Map(triplet.dstId -> 1))       // direct connection marker
    triplet.dstAttr // second-degree relay happens via a 2-hop pregel-style pass
  },
  (a, b) => a ++ b.map { case (k, v) => k -> (a.getOrElse(k, 0) + v) }
)

// Simplified logical result per user: Map[candidateId -> mutualConnectionCount]
// Filter: candidateId != self, candidateId not in 1st-degree set
// Sort by mutualConnectionCount DESC, take top 50
// Write result to a fast key-value cache (Redis / DynamoDB) keyed by user_id

// Job stats (LinkedIn-scale reference):
//   Input: ~300B edges, ~1B vertices
//   Cluster: ~2,000 executor cores
//   Runtime: 4-6 hours nightly batch window
//   Output: ~1B users × top-50 candidates = 50B (user, candidate, score) rows
//   Output storage: ~2TB compacted, written to a serving cache
```

### Serving Layer — Fast Online Read of Precomputed Results

```java
@RestController
public class PymkController {

    @Autowired
    private RedisTemplate<String, List<PymkCandidate>> pymkCache;

    @GetMapping("/api/pymk/{userId}")
    public List<PymkCandidate> getSuggestions(@PathVariable String userId) {
        // Precomputed nightly by Spark job, just a cache read — no live graph traversal
        List<PymkCandidate> cached = pymkCache.opsForValue().get("pymk:" + userId);
        return cached != null ? cached : Collections.emptyList();
        // p99 latency: <10ms (Redis GET), vs. minutes for a live 2-hop traversal
    }
}

// Cache entry, capped at top-50, TTL 24h (refreshed by next nightly batch):
// key: "pymk:alice"
// value: [{candidateId: "erin", mutualCount: 3}, {candidateId: "frank", mutualCount: 2}, ...]
```

### Why Sampling/Capping Matters at Scale

```
Worst case for a "super-connector" user (500 connections, each with
~500 connections): 500 × 500 = 250,000 raw (candidate, source) pairs
BEFORE de-duplication, for a SINGLE user's PYMK computation.

Across 1B users, naive full fan-out:
  1B users × 250,000 pairs = 250 TRILLION intermediate pairs generated
  in a single batch pass. Even with Spark's distributed shuffle, this
  blows out memory and shuffle I/O.

Mitigations used in practice:
  1. Cap 1st-degree fan-out per user at, say, the 200 MOST RECENT or
     MOST ACTIVE connections (not all 500) before doing the 2nd-degree
     expansion — bounds the worst case to 200×200 = 40,000 pairs/user.
  2. Sample: for users with connection counts far above the median
     (celebrities, recruiters with 30K connections), randomly sample
     a few hundred of their connections for the fan-out rather than
     using all of them — mutual-count ranking is statistically stable
     under sampling because the top candidates surface via MULTIPLE
     independent paths anyway.
  3. Pre-aggregate with combiners (Spark's aggregateMessages / combineByKey)
     so partial mutual-counts are summed incrementally per-partition
     before the final shuffle, instead of materializing all 250K raw
     pairs and shuffling them whole.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Design the data storage for a social network's friend/follow graph at LinkedIn scale, and explain how you'd build the 'People You May Know' feature on top of it."

**You (architect answer):**

> "I'd split this into two separate concerns: storing the graph efficiently for the reads the product actually needs, and computing recommendations, which is a completely different access pattern.
>
> For storage, I wouldn't use a single normalized table. At billions of edges, 'who does Alice follow' and 'who follows Alice' need to be independent single-partition reads, so I'd store the connection twice in Cassandra — once in a table partitioned by `user_id` for outgoing lookups, and once partitioned by `friend_id` for incoming lookups — written together in a logged batch so they stay consistent. This trades 2x storage and write amplification for O(1) partition reads regardless of graph size, which is the right trade for a system that's read-dominated by orders of magnitude.
>
> If the product also needed complex multi-hop queries — like 'shortest path of introductions to this hiring manager' — I'd introduce a Neo4j instance as a derived, secondary store fed by CDC from Cassandra, because index-free adjacency makes multi-hop traversal near-constant-time per edge, which Cassandra's partition-per-hop model can't do without a combinatorial blow-up in reads.
>
> For PYMK, the core idea is mutual-connection counting: for each of your first-degree connections, look at THEIR connections — that's your candidate pool — then rank candidates by how many of your friends they're also connected to, filtering out people you already know. I would never compute this live on a page load; a full 2-hop fan-out for a user with 500 connections, each with 500 connections, generates up to 250,000 candidate pairs before dedup, and doing that for every user in real time doesn't scale. So I'd run it as an offline Spark GraphX batch job nightly over the full graph snapshot, write the top-50 ranked candidates per user into a Redis cache, and serve reads from that cache in single-digit milliseconds.
>
> The operational concern I'd flag is fan-out blow-up for super-connected users — recruiters with 20K+ connections would make the batch job's worst-case partition explode. I'd mitigate that by capping the 1st-degree fan-out at a few hundred of the most recent/active connections per user before doing the 2nd-degree expansion, and by using combiners in the Spark aggregation so partial mutual-counts are summed per-partition before the final shuffle instead of materializing every raw pair."

---

## PART 5 — DECISION FRAMEWORK

### Graph Storage & Recommendation Approach Comparison

| Approach | How It Works | Tradeoff | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **Single normalized table** | One `friendships(user_id, friend_id)` table, index on both columns | Simple schema, but reverse lookups scatter across shards | 50-500ms (scatter) at scale | Low | Falls apart past ~10M edges |
| **Bidirectional wide-column (Cassandra)** | Two rows per connection, partitioned both ways | 2x storage/write cost | 2-8ms (single partition) | Medium | Multi-hop queries need N sequential reads |
| **Native graph DB (Neo4j)** | Index-free adjacency, pointer-chasing traversal | Harder to horizontally scale writes at 300B+ edge scale | 10-80ms (multi-hop) | High (ops) | Simple 1-hop reads at massive write QPS are overkill for this |
| **Live PYMK computation (on-request)** | Traverse 2 hops at read time | No staleness, but O(connections²) per request | Seconds (infeasible) | Low (code), High (runtime cost) | Any user with >100 connections makes this too slow |
| **Offline batch PYMK (Spark GraphX + cache)** | Nightly full-graph job, results cached per-user | Recommendations are up to 24h stale | <10ms (cache read) | Medium-High | Doesn't reflect same-day new connections until next run |

### When bidirectional Cassandra storage is right
```
✓ Read pattern is dominated by 1-hop lookups ("my connections", "my followers")
✓ Write throughput and horizontal scalability matter more than multi-hop queries
✓ You can tolerate 2x storage cost for O(1) partition reads
```

### Skip it (use a graph DB instead) when
```
✗ The product needs multi-hop path-finding as a primary feature (intro paths, community detection)
✗ Query patterns are exploratory/ad-hoc rather than fixed single-hop lookups
```

### When offline-batch PYMK is right
```
✓ Recommendation freshness of "up to 24 hours old" is acceptable
✓ Graph is large enough that live 2-hop traversal is computationally infeasible
✓ You have (or can run) a distributed processing framework like Spark GraphX
```

### Skip batch PYMK when
```
✗ Graph is small enough (<100K users) that live traversal is cheap
✗ Recommendations must reflect connections made in the last few minutes (needs a hybrid: batch + incremental real-time update layer)
```

---

## QUICK REFERENCE CARD

```
CASSANDRA BIDIRECTIONAL GRAPH:
  connections_by_user  (PK: user_id)   → "who do I know"
  connections_by_friend(PK: friend_id) → "who knows me"
  Write: LOGGED BATCH (both inserts atomic together)
  Read latency: 2-8ms, single partition, size-independent

NEO4J MULTI-HOP:
  MATCH path = shortestPath((a)-[:KNOWS*..4]-(b)) RETURN path;
  Index-free adjacency → O(1) per edge hop
  Use as derived store (CDC-fed), not system of record at 300B+ edges

PYMK ALGORITHM:
  1. candidates = union(friends_of_friends) - self - existing_friends
  2. score(candidate) = count(distinct mutual connection paths)
  3. rank DESC by score, take top-N (e.g. 50)

PYMK SCALE MATH:
  500 connections × 500 connections/each = 250,000 raw candidate pairs/user
  1B users × naive fan-out = infeasible online
  → Compute OFFLINE (Spark GraphX, nightly), cache per-user (Redis, TTL 24h)
  → Cap fan-out per user + use combiners to bound intermediate shuffle size

SERVING:
  GET pymk:{userId} from Redis → <10ms, precomputed
```
