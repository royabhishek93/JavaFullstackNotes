# Posting-List Intersection & Scatter-Gather Query Execution
### How a search engine actually resolves "system AND design" across billions of documents in milliseconds

---

## PART 1 — THE STUDENT CONVERSATION

You already know that Elasticsearch (and search engines generally) use an inverted index — for every term, a list of which documents contain it (see [014-inverted-index-how-elasticsearch-works.md](014-inverted-index-how-elasticsearch-works.md) for how that index structure itself is built). But knowing the index exists doesn't explain how a query with MULTIPLE terms — like "system AND design" — actually gets resolved into a ranked result list. That's what this file covers.

Think of each term's posting list like a phone book, sorted by document ID (not alphabetically by name — sorted by an internal numeric doc ID). The posting list for "system" might be `[3, 7, 19, 42, 100, 250, ...]` (every doc ID containing "system"), and the posting list for "design" might be `[7, 19, 55, 100, 300, ...]`. To answer "system AND design," you need the INTERSECTION of these two lists — document IDs present in BOTH.

The naive way to intersect two lists is a nested loop: for every ID in list A, scan through all of list B looking for a match. That's O(n×m) — brutally slow for long lists. But because both lists are already SORTED by the same doc-ID ordering (a deliberate design choice when building the index), there's a much smarter way: walk two pointers simultaneously, one per list. Compare the current elements; if they're equal, it's a match — record it and advance both pointers. If list A's current element is smaller, advance ONLY list A's pointer (since nothing before it in A can match anything in B, given both are sorted ascending). This is the classic sorted-merge intersection, and it's O(n+m) — you touch each element at most once. For very long posting lists (a common term like "the" might have billions of entries), there's a further optimization: skip pointers, extra "shortcut" links embedded every K entries in the list that let you jump ahead by many entries at once when you know the target is far away, avoiding scanning every single entry one at a time.

Now scale this up: a real search engine's index is way too big to fit on one machine, so it's SHARDED — split across many nodes, each holding a slice of the documents (and correspondingly, a slice of every term's posting list). When a query comes in, a coordinator node "scatters" the same query out to every shard in parallel. Each shard does its own local posting-list intersection (using the exact merge algorithm above) and returns its own local top-K best matches. The coordinator then "gathers" all those partial results back and does one final merge/re-rank across all of them to produce the truly global top-K. This scatter-gather pattern is how Elasticsearch's "query-then-fetch" execution model works under the hood. The catch: your overall response time is bounded by the SLOWEST shard that participates — if one shard is overloaded, garbage-collecting, or has a hot partition, every query touching it gets dragged down, even if the other 49 shards responded instantly (see [042-long-tail-latency-p99-percentiles.md](042-long-tail-latency-p99-percentiles.md) for why tail latency, not average latency, is what actually determines user-perceived slowness in a fan-out system like this).

---

## PART 2 — THE POSTING-LIST/SCATTER-GATHER ARCHITECTURE DIAGRAMS

### Sorted-Merge Intersection: "system" AND "design"

```
Posting list for "system"  (sorted ascending by doc_id):
  [ 3,   7,  19,  42, 100, 250, 300, 512 ]
    ▲
    pointer_A

Posting list for "design"  (sorted ascending by doc_id):
  [ 7,  19,  55, 100, 300, 900 ]
    ▲
    pointer_B

Step-by-step two-pointer walk:

  Step 1:  A=3,   B=7    →  3 < 7   → advance A only         → A=7
  Step 2:  A=7,   B=7    →  MATCH!  → record doc_id=7          → advance BOTH → A=19, B=19
  Step 3:  A=19,  B=19   →  MATCH!  → record doc_id=19         → advance BOTH → A=42, B=55
  Step 4:  A=42,  B=55   →  42 < 55 → advance A only          → A=100
  Step 5:  A=100, B=55   →  55 < 100→ advance B only          → B=100
  Step 6:  A=100, B=100  →  MATCH!  → record doc_id=100        → advance BOTH → A=250, B=300
  Step 7:  A=250, B=300  →  250<300 → advance A only          → A=300
  Step 8:  A=300, B=300  →  MATCH!  → record doc_id=300        → advance BOTH → A=512, B=900
  Step 9:  A=512, B=900  →  512<900 → advance A only          → A exhausted, STOP

  Result: intersection = [7, 19, 100, 300]
  Cost: 9 comparisons total for lists of length 8 and 6 → O(n+m), not O(n×m)=48
```

### Skip Pointers on a Long Posting List

```
Posting list for a COMMON term like "the" (millions of entries).
Without skip pointers, a query needing to intersect against a target
far down the list must walk every single entry sequentially:

  [1, 2, 3, 4, 5, 6, 7, 8, ... , 9997, 9998, 9999, 10000, ...]
   ▲ start here, target doc_id=9999 is 9999 hops away — SLOW

With skip pointers embedded every √n entries (a common heuristic):

  [1, 2, 3, ... , 100] ──skip──▶ [101, ... , 200] ──skip──▶ [201, ...] ──skip──▶ ...
   ▲
   Query wants doc_id=9999:
   1. Check skip target at position 100: doc_id there is way < 9999 → JUMP
   2. Check skip target at position 200: still < 9999 → JUMP
   3. ... repeat, jumping in chunks of ~100 instead of stepping by 1 ...
   4. Land near position 9900-10000, then walk normally within that
      small final chunk to find the exact match.

  Cost without skips: up to n comparisons (n = list length)
  Cost with skips (chunk size √n): roughly O(√n) jumps + small local walk
  For a 10,000,000-entry posting list: √n ≈ 3,162 — a huge reduction
  versus scanning up to 10 million entries sequentially in the worst case.

  Skip pointers are most valuable when intersecting a very long list
  (e.g. "the") against a very short one (e.g. a rare term) — you can
  skip through most of the long list's irrelevant regions in large jumps.
```

### Scatter-Gather Across Sharded Index (Query-Then-Fetch)

```
Query: "system design interview" arrives at Query Coordinator

Index sharded across 5 nodes (each holds ~1/5 of all documents,
and therefore ~1/5 of every term's global posting list):

                          ┌─────────────────────┐
                          │  Query Coordinator    │
                          └──────────┬────────────┘
                                     │  SCATTER: send same query to ALL shards, parallel
        ┌──────────────┬────────────┼────────────┬──────────────┐
        v              v            v            v              v
   ┌─────────┐   ┌─────────┐  ┌─────────┐  ┌─────────┐   ┌─────────┐
   │ Shard 0 │   │ Shard 1 │  │ Shard 2 │  │ Shard 3 │   │ Shard 4 │
   │         │   │         │  │         │  │         │   │         │
   │ local   │   │ local   │  │ local   │  │ local   │   │ local   │
   │ posting-│   │ posting-│  │ posting-│  │ posting-│   │ posting-│
   │ list    │   │ list    │  │ list    │  │ list    │   │ list    │
   │ intersect│  │ intersect│ │ intersect│ │ intersect│  │ intersect│
   │ + local │   │ + local │  │ + local │  │ + local │   │ + local │
   │ top-K   │   │ top-K   │  │ top-K   │  │ top-K   │   │ top-K   │
   │ (BM25   │   │ (BM25   │  │ (BM25   │  │ (BM25   │   │ (BM25   │
   │ scoring)│   │ scoring)│  │ scoring)│  │ scoring)│   │ scoring)│
   │         │   │         │  │         │  │         │   │         │
   │ 12ms    │   │ 9ms     │  │ 340ms   │  │ 11ms    │   │ 10ms    │
   │ ✓ fast  │   │ ✓ fast  │  │ ⚠ SLOW  │  │ ✓ fast  │   │ ✓ fast  │
   │         │   │         │  │(GC pause│  │         │   │         │
   │         │   │         │  │ or hot  │  │         │   │         │
   │         │   │         │  │partition)│  │         │   │         │
   └────┬────┘   └────┬────┘  └────┬────┘  └────┬────┘   └────┬────┘
        │             │            │            │             │
        └─────────────┴────GATHER──┴────────────┴─────────────┘
                                     │
                                     v
                          ┌─────────────────────┐
                          │  Query Coordinator    │
                          │  merges 5 local top-K │
                          │  lists → global top-K │
                          │  (re-sort by score)   │
                          └──────────┬────────────┘
                                     │
                                     v
                            Final response returned
                            to client after ALL 5 shards
                            respond → bounded by Shard 2's
                            340ms, NOT by the 4 fast shards' ~10ms

  Tail-latency problem: response time = MAX(all shard latencies), not
  average. One slow/overloaded shard drags down EVERY query that touches
  it, even though 80% of the work finished in ~10ms.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Posting-List Intersection (Java Pseudocode)

```java
// Two-pointer sorted-merge intersection — O(n + m)
public static List<Integer> intersect(int[] postingListA, int[] postingListB) {
    List<Integer> result = new ArrayList<>();
    int i = 0, j = 0;
    while (i < postingListA.length && j < postingListB.length) {
        int a = postingListA[i];
        int b = postingListB[j];
        if (a == b) {
            result.add(a);
            i++; j++;
        } else if (a < b) {
            i++;   // advance the pointer pointing at the smaller value
        } else {
            j++;
        }
    }
    return result;
}
// For a multi-term AND query ("system" AND "design" AND "interview"),
// intersect the two SHORTEST posting lists first, then intersect that
// result against the next-shortest list — minimizes total comparisons,
// since the running intersection can only shrink or stay the same size.
```

### Skip-List-Augmented Posting List (Conceptual Structure)

```
Real search engines (Lucene, which underlies Elasticsearch) store
posting lists in compressed blocks with embedded skip data:

  Block 0: doc_ids [1..128],    skip_to_offset → Block 8  (doc_id ~1024)
  Block 1: doc_ids [129..256],  skip_to_offset → Block 9  (doc_id ~1152)
  ...
  Lucene's actual implementation uses a multi-level skip list (like a
  skip-list data structure), where higher levels skip larger distances —
  similar in spirit to how a database B-tree index lets you avoid
  scanning every leaf node.

  Compression detail: Lucene stores doc IDs as DELTA-encoded (gap)
  integers rather than raw IDs — e.g. instead of [1042, 1055, 1201],
  it stores [1042, 13, 146] (each entry = gap from previous), which
  compresses far better (smaller integers) — typical compressed posting
  list size: 1-3 bytes per doc ID entry versus 4-8 bytes uncompressed.
```

### Scatter-Gather Query Execution (Elasticsearch-style, Simplified)

```java
@Service
public class QueryCoordinatorService {

    public SearchResponse search(String queryText, int topK) {
        List<CompletableFuture<ShardResult>> futures = shardClients.stream()
            .map(shard -> CompletableFuture.supplyAsync(
                () -> shard.executeLocalQuery(queryText, topK),
                executorPool))
            .collect(Collectors.toList());

        // GATHER: wait for all shards (bounded by the SLOWEST one)
        List<ShardResult> shardResults = futures.stream()
            .map(CompletableFuture::join)   // blocks until each shard responds
            .collect(Collectors.toList());

        // Final merge: combine all shards' local top-K into a global top-K
        return shardResults.stream()
            .flatMap(r -> r.getHits().stream())
            .sorted(Comparator.comparingDouble(Hit::getBm25Score).reversed())
            .limit(topK)
            .collect(collectingAndThen(toList(), SearchResponse::of));
    }
}

// Elasticsearch's real "query then fetch" phases:
//   Phase 1 (query): each shard returns doc IDs + scores only (cheap payload)
//   Coordinator merges scores, determines final global top-K doc IDs
//   Phase 2 (fetch): coordinator asks ONLY the shards holding those final
//     top-K doc IDs to return the full document body (avoids transferring
//     full documents from EVERY shard's local top-K, most of which get discarded)
```

### Real Numbers: Shard Count vs Tail Latency

```
Single-shard local intersection + BM25 scoring over ~2M docs/shard: ~8-15ms typical
Coordinator fan-out/merge overhead: ~2-5ms

  Shard count | p50 latency | p99 latency | Why p99 diverges from p50
  ------------|-------------|-------------|--------------------------------
  1 shard     | 12ms        | 25ms        | No fan-out — single-node variance only
  10 shards   | 14ms        | 90ms        | 1-in-10 chance a query hits a slow shard
  50 shards   | 15ms        | 340ms       | 1-in-50 chance grows to near-certainty
                                            over many queries/sec — SOME shard is
                                            always having a bad moment (GC, hot
                                            partition, disk I/O contention)
  100 shards  | 16ms        | 600ms+      | At this fan-out width, tail latency
                                            dominates the user-perceived response
                                            time almost every single query

  Mitigations:
  1. Replica shards: each shard has 1-2 replicas; coordinator sends the
     request to whichever replica currently has the lowest observed
     latency, rather than a fixed primary.
  2. Hedged requests: if the primary hasn't responded within, say, the
     p95 latency threshold (~20-30ms), fire the SAME request to a replica
     concurrently and take whichever response comes back first — trades
     a small amount of duplicate work for a large tail-latency reduction.
  3. Reduce shard count where possible (fewer, larger shards) — fewer
     independent chances for one shard to be the slow outlier, at the
     cost of less parallelism per query and larger per-shard index size.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "A user searches for 'system design interview' against your search index, which is sharded across 50 nodes. Walk me through exactly how that query gets resolved, and what could make it slow."

**You (architect answer):**

> "Within a single shard, the core mechanic is posting-list intersection. Each term in the query — 'system', 'design', 'interview' — has its own posting list: a sorted list of document IDs containing that term. Because all posting lists are sorted by the same doc-ID ordering, I don't need a nested loop to find documents containing ALL three terms — I can do a two-pointer merge-based intersection, walking each list once and advancing whichever pointer is behind, which is O(n+m) instead of O(n×m). I'd also intersect the shortest posting lists first, since the running intersection can only shrink, which minimizes total comparisons for multi-term queries. For very long posting lists — common terms like 'the' — I'd rely on skip pointers embedded in the list so I can jump ahead in large chunks instead of walking every single entry, which matters a lot when intersecting a long list against a short, selective one.
>
> That's the local, single-shard story. But the index is sharded across 50 nodes, so the coordinator has to fan this same query out to every shard in parallel — that's the 'scatter' — each shard runs its own local intersection and returns its own local top-K matches with BM25 scores. Elasticsearch actually splits this into two phases: a cheap 'query' phase where shards return just doc IDs and scores, then a 'fetch' phase where the coordinator asks only for the full document bodies of the FINAL merged top-K, avoiding pulling full documents from every shard's local candidates that end up discarded anyway. The coordinator then does one final merge-and-resort across all shard results — that's the 'gather' — to produce the true global top-K.
>
> The thing that could make this slow isn't the algorithm — it's that my overall response time is bounded by the SLOWEST of those 50 shards. If even one shard is having a bad moment — a GC pause, a hot partition getting disproportionate traffic, disk contention — every query that happens to touch it gets dragged down to that shard's latency, even though the other 49 shards responded in single-digit milliseconds. At 50-way fan-out, the odds that AT LEAST ONE shard is slow on any given query become uncomfortably high over a sustained request rate, which is exactly why p99 latency diverges so sharply from p50 in scatter-gather systems.
>
> The mitigation I'd put in place is hedged requests combined with replica shards: if a shard hasn't responded within roughly its own p95 latency threshold, I fire the same request to a replica of that shard concurrently and take whichever comes back first. It costs a small amount of duplicate work on the slow tail, but it converts a small number of very slow queries into a much smaller number of moderately duplicated ones, which is a good trade for user-perceived latency."

---

## PART 5 — DECISION FRAMEWORK

### Query Resolution Strategy Comparison

| Approach | How It Works | Tradeoff | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **Nested-loop intersection** | For each doc in list A, scan list B for a match | Simple to implement, no sort dependency | O(n×m) — poor at scale | Very Low | Any posting list beyond a few thousand entries becomes unusably slow |
| **Sorted two-pointer merge intersection** | Walk both sorted lists once, advance the smaller pointer | Requires posting lists sorted consistently (already true in inverted indexes) | O(n+m) | Low | Doesn't help if one list is astronomically longer than the other without skips |
| **Skip-pointer-augmented intersection** | Embedded shortcuts let you jump ahead in a long list | Slightly more index storage for skip metadata | O(√n) typical jump cost | Medium | Less benefit when both lists are similarly short (overhead not worth it) |
| **Single-node full index (no sharding)** | Entire index fits and is queried on one machine | No scatter-gather tail-latency problem at all | Bounded only by single-node query cost | Low | Doesn't scale past what one machine's memory/CPU can hold |
| **Scatter-gather across shards** | Fan out to all shards, merge local top-K results | Enables horizontal scale, but introduces tail-latency risk | Bounded by slowest shard | High | One slow/overloaded shard drags down every query touching it |
| **Scatter-gather + hedged requests/replicas** | Same as above, plus retry-to-replica on slow primary | Extra duplicate work on the tail, better p99 | Bounded by faster of primary/replica | High | Doesn't help if ALL replicas of a shard are uniformly overloaded |

### When scatter-gather is right
```
✓ Your index is too large for a single node's memory/CPU to serve
  acceptable query latency
✓ You need horizontal scalability as document count or query volume grows
✓ You can afford (and provision) replica shards to mitigate tail latency
```

### Skip scatter-gather (single-node/simpler sharding) when
```
✗ Your entire index comfortably fits and performs well on one machine —
  don't add distributed-systems complexity you don't need yet
✗ You cannot provision replicas — scatter-gather WITHOUT replicas/hedging
  has no mitigation for the slow-shard tail-latency problem
```

---

## QUICK REFERENCE CARD

```
POSTING LIST:  for each term, sorted list of doc_ids containing it

TWO-POINTER INTERSECTION (AND query):
  i, j = 0, 0
  while i < len(A) and j < len(B):
    if A[i] == B[j]: emit A[i]; i++; j++
    elif A[i] < B[j]: i++
    else: j++
  → O(n + m); intersect shortest lists first for multi-term queries

SKIP POINTERS:
  Embedded shortcuts every ~√n entries → jump instead of linear scan
  Most useful: long list ∩ short/rare-term list

SCATTER-GATHER (sharded index):
  1. Coordinator SCATTERS query to all shards in parallel
  2. Each shard: local posting-list intersection + local top-K (BM25)
  3. Coordinator GATHERS all local top-K → final merge/re-sort → global top-K
  Elasticsearch: "query" phase (IDs+scores) then "fetch" phase (full docs,
  only for the final merged top-K)

TAIL LATENCY:
  response_time = MAX(all shard latencies), not average
  Mitigate: replica shards + hedged requests (fire to replica if primary
  exceeds its own p95 threshold)

RELATED:
  see 014-inverted-index-how-elasticsearch-works.md for index structure
  see 042-long-tail-latency-p99-percentiles.md for why tail latency dominates
```
