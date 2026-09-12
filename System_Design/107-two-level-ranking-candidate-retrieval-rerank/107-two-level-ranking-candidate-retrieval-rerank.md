# Two-Level Ranking: Candidate Retrieval + Re-Ranking
### How Instagram/YouTube/search rank millions of items in under 100ms without scoring all of them

---

## PART 1 — THE STUDENT CONVERSATION

Suppose you want to show someone the "best" 20 posts for their Instagram feed, out of the millions of posts that exist across everyone they follow, everyone THEY follow, and trending content. The ideal approach, in theory, is: run your best machine-learning ranking model — the one that predicts "will this specific user like/comment/watch this specific piece of content" — over EVERY candidate post, sort by predicted score, and return the top 20.

The problem is pure arithmetic. If your ranking model takes even 1 millisecond per (user, item) pair to score — and realistic deep-learning ranking models are much slower than that — and you have a candidate pool of 2 million posts, scoring every single one takes 2,000 seconds. Nobody waits 33 minutes for a feed to load. Your latency budget for an entire feed request is more like 100-200 milliseconds, total.

So platforms don't run one model over everything. They run a cheap, fast, "good enough" filter FIRST to shrink millions of candidates down to a few hundred, and THEN run the expensive, accurate model only on that much smaller shortlist. This is the classic two-stage "funnel" pattern: candidate retrieval (also called "candidate generation") narrows the field cheaply and inclusively — its whole job is to make sure good candidates aren't accidentally left out (optimizing for recall), even if it lets some mediocre candidates through too. Then re-ranking takes that shortlist and is allowed to be slow and precise per-item, because it's now only scoring a few hundred things instead of millions (optimizing for precision).

Think of it like hiring: you don't do a 3-hour deep technical interview with every one of the 5,000 people who apply for a job. You run a cheap resume screen first (candidate retrieval — quick, imperfect, but narrows 5,000 down to 50), and only THEN do you spend the expensive, high-signal interview time (re-ranking) on those 50 candidates. The screen doesn't need to be perfectly accurate — it just needs to not throw away the people who would have been great hires. The interview is where the real precision happens.

---

## PART 2 — THE TWO-LEVEL RANKING ARCHITECTURE DIAGRAMS

### The Funnel: Millions → Hundreds → Top-N

```
                    ┌─────────────────────────────────────┐
                    │   FULL CANDIDATE UNIVERSE             │
                    │   ~2,000,000 posts                    │
                    │   (everything posted in last 48h by   │
                    │    people you follow + trending pool) │
                    └───────────────────┬────────────────────┘
                                        │
                                        v
              ┌─────────────────────────────────────────────────┐
              │  STAGE 1: CANDIDATE RETRIEVAL (cheap, high-recall)│
              │                                                     │
              │  Method A: most recent 500 posts from people you    │
              │            follow (simple recency filter)           │
              │  Method B: ANN (Approximate Nearest Neighbor) search │
              │            over embedding vectors — find posts whose │
              │            content-embedding is close to a vector    │
              │            representing your recent engagement       │
              │            history (e.g. FAISS / HNSW index lookup)   │
              │                                                     │
              │  Latency budget: ~20-50ms                          │
              │  Output: ~300-500 candidates                        │
              └───────────────────┬─────────────────────────────────┘
                                  │
                                  v
              ┌─────────────────────────────────────────────────┐
              │  STAGE 2: RANKING / RE-RANKING (expensive, high-  │
              │           precision)                              │
              │                                                     │
              │  Learned ranking model (e.g. gradient-boosted trees │
              │  or a small neural net) scores EACH of the ~300-500 │
              │  candidates using rich per-pair features:            │
              │    - recency (age of post in minutes)                │
              │    - predicted_engagement_probability (like/comment) │
              │    - author_affinity_score (how often you engage      │
              │      with this specific author historically)          │
              │    - content_type_diversity (avoid 10 videos in a row)│
              │                                                     │
              │  Latency budget: ~50-100ms for ~300-500 items       │
              │  Output: re-ordered list, top 20 selected            │
              └───────────────────┬─────────────────────────────────┘
                                  │
                                  v
                    ┌───────────────────────────┐
                    │   FINAL FEED PAGE (top 20)│
                    │   Total latency: ~100-150ms│
                    └───────────────────────────┘

Compare: running the Stage 2 model over ALL 2,000,000 candidates directly
would take on the order of seconds to tens of minutes depending on model
cost — completely outside any acceptable request latency budget.
```

### ANN-Based Candidate Retrieval (Embedding Similarity)

```
User's "interest vector" (built from recent likes/watches/embeddings,
updated continuously): u = [0.12, -0.87, 0.44, ..., 0.03]  (128-dim)

Every candidate post has a precomputed content embedding vector,
indexed in an Approximate Nearest Neighbor structure (HNSW graph
or FAISS IVF index) built OFFLINE as new content is created:

  Post embeddings index (built ahead of time, not per-request):
  ┌───────────┬──────────────────────────────┐
  │ post_id   │ embedding (128-dim vector)    │
  ├───────────┼──────────────────────────────┤
  │ post_9981 │ [0.10, -0.90, 0.41, ...]      │  <- close to user vector
  │ post_1204 │ [0.95,  0.30, -0.20, ...]     │  <- far from user vector
  │ post_5567 │ [0.14, -0.85, 0.39, ...]      │  <- close to user vector
  └───────────┴──────────────────────────────┘

  Query: ANN_search(index, u, k=300)
  → returns the 300 posts whose embeddings are closest (cosine similarity
    or L2 distance) to the user's interest vector, WITHOUT scanning all
    2,000,000 posts — HNSW graph traversal visits a small fraction of
    nodes (typically O(log N) hops), giving approximate but very fast
    top-K nearest-neighbor results.

  Real numbers: HNSW ANN search over ~10M vectors, 128 dimensions,
  typically resolves in 2-10ms per query on a single node, vs. a brute-
  force exact nearest-neighbor scan over 10M vectors taking hundreds of
  milliseconds to seconds.
```

### Stage 2 Feature Vector Per Candidate (Ranking Model Input)

```
For each of the ~300-500 shortlisted candidates, the ranking model
receives a feature vector like:

  Candidate: post_9981 (author: bob_the_baker)
  ┌────────────────────────────────┬───────────┐
  │ Feature                        │ Value     │
  ├────────────────────────────────┼───────────┤
  │ recency_minutes                │ 12        │
  │ predicted_like_probability     │ 0.68      │
  │ predicted_comment_probability  │ 0.09      │
  │ author_affinity_score          │ 0.82      │  <- you engage w/ bob often
  │ content_type                   │ "photo"   │
  │ diversity_penalty              │ 0.0       │  <- no recent photos shown yet
  │ is_from_followed_account       │ true      │
  └────────────────────────────────┴───────────┘

  Model output: relevance_score = 0.74  (combined weighted signal)

  All ~300-500 candidates scored this way, sorted descending by
  relevance_score, top 20 returned. Diversity constraints (e.g. "no
  more than 3 video posts in the top 10") are applied as a final
  re-ranking pass AFTER the raw model scores, to avoid a feed that's
  monotonous even if individually high-scoring.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Stage 1: Candidate Retrieval Service

```java
@Service
public class CandidateRetrievalService {

    public List<Candidate> retrieve(String userId) {
        List<Candidate> candidates = new ArrayList<>();

        // Method A: recency-based from followed accounts (cheap DB/cache read)
        candidates.addAll(
            feedCache.getRecentPosts(userId, /* limit */ 500)
        );

        // Method B: ANN embedding similarity search (broader discovery/trending)
        float[] userInterestVector = userEmbeddingService.getInterestVector(userId);
        candidates.addAll(
            annIndex.search(userInterestVector, /* topK */ 300)
        );

        // Dedup — same post might appear via both methods
        return candidates.stream().distinct().limit(500).collect(Collectors.toList());
        // Total Stage 1 latency budget: 20-50ms
    }
}
```

### Stage 2: Ranking Model Invocation

```python
# Ranking service — scores each of the ~300-500 candidates individually.
# Model: gradient-boosted decision trees (e.g. XGBoost) trained offline
# on historical engagement labels (did the user like/comment/watch-to-completion).

def rank_candidates(user_id: str, candidates: list[Candidate]) -> list[RankedItem]:
    features_batch = [
        build_feature_vector(user_id, c) for c in candidates
    ]  # ~300-500 feature vectors, each ~20-50 features

    scores = ranking_model.predict_batch(features_batch)  # single batched inference call

    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)

    final = apply_diversity_reranking(ranked)  # e.g. cap consecutive same-content-type items

    return final[:20]

# Real numbers:
#   Batched XGBoost inference over 500 rows, ~30 features each: ~15-40ms
#   Neural ranking model (small MLP) over same batch: ~50-100ms on CPU,
#     faster with GPU batching at high QPS
#   This is why "few hundred candidates" is the practical ceiling for
#   Stage 2 — batch inference cost grows roughly linearly with candidate
#   count, and the total budget for this stage is ~50-100ms.
```

### Feature Store Lookup (Author Affinity Example)

```sql
-- Author affinity score, precomputed offline (batch job), NOT computed live:
-- "how often has this user engaged with this specific author's content
--  over the last 90 days" — updated nightly, read at ranking time.

SELECT author_affinity_score
FROM user_author_affinity
WHERE user_id = 'alice' AND author_id = 'bob_the_baker';
-- p99 read latency from a feature store (Redis-backed): <5ms per lookup
-- Ranking service does this in BATCH for all candidates in one round-trip:
-- MGET affinity:alice:bob_the_baker affinity:alice:erin ... (pipelined)
```

### Latency Budget Breakdown (Full Request)

```
Total feed-request SLA target: ~150-200ms end-to-end

  Stage                          | Budget    | What happens
  --------------------------------|-----------|---------------------------------
  Stage 1: Candidate Retrieval    | 20-50ms   | Recency filter + ANN search,
                                   |           | ~2M candidates → ~300-500
  Feature assembly (batch lookup) | 10-20ms   | Pull affinity/engagement features
                                   |           | for all shortlisted candidates
  Stage 2: Ranking model inference| 50-100ms  | Score ~300-500 candidates,
                                   |           | batched model call
  Diversity re-rank + assembly    | 5-10ms    | Final ordering constraints
  --------------------------------|-----------|---------------------------------
  TOTAL                           | ~85-180ms | Within SLA

  Infeasible comparison:
  Running the Stage 2 model directly over the FULL 2,000,000-candidate
  pool (no Stage 1 filter) at the same per-item cost (~0.15-0.3ms/item
  for the cheapest realistic model) would take 300-600 SECONDS — six
  orders of magnitude over budget. This is precisely why the two-stage
  funnel exists: it's not an optimization, it's the only way the
  precise model can run at all within a request's latency budget.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "You have a machine learning model that's great at predicting whether a user will engage with a piece of content, but it takes tens of milliseconds per item to score. How do you use that model to rank a feed drawn from millions of candidate posts, within a 150ms latency budget?"

**You (architect answer):**

> "You can't run the expensive model over the full candidate pool — the arithmetic doesn't work. If the model costs even a fraction of a millisecond per item and I have millions of candidates, scoring all of them would take seconds to minutes, and my entire request budget is under 200 milliseconds.
>
> So I'd split ranking into two stages. Stage one is candidate retrieval — a cheap, high-recall pass whose only job is to shrink millions of candidates down to a few hundred without throwing away anything that's likely to be good. I'd combine a simple recency filter — the most recent posts from accounts the user follows — with an ANN embedding-similarity search, using something like an HNSW index over content embeddings, to also surface relevant content from outside the user's direct follows for discovery. That whole stage runs in 20-50 milliseconds because it's either simple recency sorting or approximate nearest-neighbor lookups, both of which are designed to be fast, not perfectly precise.
>
> Stage two is where the expensive model earns its keep — it only has to score the few hundred candidates that survived stage one, which fits comfortably in a 50-100 millisecond budget for batched inference. At this stage I'd build a rich feature vector per candidate — recency, predicted engagement probability, an author-affinity score precomputed offline from historical engagement, and content-type signals for diversity — and let the model rank those few hundred precisely, since precision is what this stage is optimizing for, unlike stage one which optimizes for recall.
>
> The operational concern I'd flag is stage-one recall quality — if the candidate retrieval stage is too aggressive or its embeddings go stale, you silently drop genuinely great content before the precise model ever sees it, and no amount of stage-two tuning fixes that. I'd mitigate this by continuously measuring 'recall@K' offline — checking what fraction of items that WOULD have ranked in the top 20 under a full brute-force pass actually made it into the stage-one shortlist — and alerting if that recall metric drops, since it's an easy blind spot that doesn't show up in simple latency dashboards."

---

## PART 5 — DECISION FRAMEWORK

### Ranking Architecture Comparison

| Approach | How It Works | Tradeoff | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **Single-stage (score everything)** | Run the precise model over the entire candidate pool | Perfectly precise, but doesn't scale | Seconds-minutes for large pools | Low | Any pool beyond a few thousand candidates blows the latency budget |
| **Recency-only (no ranking model)** | Just show newest posts first | Trivially fast, zero model cost | <10ms | Very Low | Ignores relevance entirely — low engagement, high scroll-past rate |
| **Two-level (retrieval + re-rank)** | Cheap high-recall filter, then expensive high-precision model on shortlist | Adds a stage-1 recall risk (good items dropped early) | ~100-150ms total | Medium-High | Stage-1 recall degrades (stale embeddings, bad ANN tuning) silently hides good content |
| **Multi-stage funnel (3+ stages)** | Add a mid-tier "lightweight ranker" stage between retrieval and full re-rank | Better precision/latency curve at very large scale | ~100-200ms, better quality at scale | High | Overkill for smaller platforms; extra stage = extra tuning surface |

### When two-level ranking is right
```
✓ Candidate pool per request is large (hundreds of thousands to millions)
✓ You have (or can afford) a precise ranking model that's too slow to run
  over the full pool
✓ You can build/maintain a cheap high-recall retrieval mechanism (ANN
  index, recency filters, simple heuristics)
```

### Skip it when
```
✗ Candidate pool per request is already small (hundreds of items) — just
  run the precise model directly, no funnel needed
✗ You don't yet have engagement-labeled training data for a precise model
  — start with heuristic/recency ranking first, add ML ranking later
✗ Latency budget is generous (batch/offline recommendation emails, not
  live page loads) — full scoring may be affordable
```

---

## QUICK REFERENCE CARD

```
TWO-STAGE FUNNEL:
  Stage 1 (Candidate Retrieval): millions → ~300-500 candidates
    Methods: recency filter, ANN/embedding similarity (HNSW/FAISS)
    Optimizes for: RECALL (don't drop good candidates)
    Budget: ~20-50ms

  Stage 2 (Ranking / Re-Ranking): ~300-500 → top-N (e.g. 20)
    Method: learned model (GBDT / small neural net) scoring rich features
    Features: recency, predicted_engagement_probability,
              author_affinity_score, content_type_diversity
    Optimizes for: PRECISION (best possible final order)
    Budget: ~50-100ms

TOTAL BUDGET: ~100-200ms end-to-end (vs. seconds-minutes for single-stage
              scoring of the full candidate pool)

KEY METRIC TO WATCH: Stage-1 recall@K — measure offline whether genuinely
  top-ranking items are being dropped before Stage 2 ever sees them.
```
