# Collaborative Filtering: The Math Behind "Recommended For You"
### How Netflix and YouTube guess what you'll like without ever asking you directly

---

## PART 1 — THE STUDENT CONVERSATION

Imagine you walk into a bookstore and a clerk who's never spoken to you says, "Based on what you just picked up, you'll also love this." How could they possibly know? They didn't ask about your taste — they noticed something structural: thousands of other customers who bought the book in your hand also bought that other book. They're not reasoning about the *content* of the books at all — they're reasoning about *co-occurrence in behavior* across a huge crowd of other people. That's the entire idea behind collaborative filtering.

There are two ways to frame this. **User-based**: find people whose past behavior looks like yours (they watched/rated the same things you did), then recommend what THEY liked that you haven't seen yet. **Item-based**: instead of comparing you to other users, compare items to each other — "of everyone who watched Video A, what fraction also watched Video B?" — and recommend items similar to what you already liked, based on that co-occurrence pattern across the whole user base.

Item-based tends to win in practice for large platforms, for a very practical reason: the number of distinct users on YouTube is enormous and constantly churns (new users sign up every second, tastes drift), but the catalog of videos, while still large, is comparatively far more stable — a video's "similarity profile" to other videos doesn't change nearly as fast as a user's evolving taste does. Recomputing user-to-user similarity for hundreds of millions of users is a much heavier, more volatile computation than recomputing item-to-item similarity for a comparatively smaller, steadier catalog.

Underneath both approaches is a giant table: the **user-item interaction matrix** — rows are users, columns are items, and each cell is some signal of preference (a star rating, minutes watched, click, purchase). This matrix is almost entirely empty — a given user has interacted with a tiny fraction of the catalog — which is why it's called *sparse*.

The clever trick for handling this sparse matrix at scale is **matrix factorization**: instead of trying to directly fill in every blank cell, you assume that both users and items can be described by a much smaller set of hidden ("latent") factors — maybe 50 or 100 numbers per user and per item, representing things like "how much does this user like fast pacing," "how much does this item have fast pacing," even though no one explicitly labeled those factors. The dot product of a user's factor vector and an item's factor vector approximates how much that user would like that item. **Alternating Least Squares (ALS)** is the standard algorithm for computing these factor vectors at scale across a distributed cluster (commonly via Spark MLlib) — it alternates between fixing the user vectors and solving for the best item vectors, then fixing item vectors and solving for user vectors, repeating until the approximation converges.

The catch: this whole approach needs *some* interaction history to work from. A brand-new user with zero watch history, or a brand-new item nobody has watched yet, has no signal for the matrix to learn from — this is the **cold-start problem**, solved by falling back to content-based signals (genre, description, tags) or simple popularity-based defaults until enough real interaction data accumulates.

---

## PART 2 — THE COLLABORATIVE FILTERING ARCHITECTURE DIAGRAMS

### User-Based vs Item-Based: Two Ways to Read the Same Matrix

```
User-Item Interaction Matrix (rows=users, cols=videos, cell=watch-time minutes)

              VideoA  VideoB  VideoC  VideoD  VideoE
  UserAlice     45      0      38       0      12
  UserBob       40      0      35       0       0
  UserCarol      0     50       0      42       0
  UserDave       0     48       5      39       0
  UserEve       48      0      41       0      10

USER-BASED CF:
  "Who is similar to UserAlice?"
  -> Compare Alice's row vector to every other user's row vector
     (cosine similarity or Pearson correlation)
  -> UserBob and UserEve have highly similar watch patterns to Alice
     (both watched A and C heavily, skipped B and D)
  -> UserEve also watched VideoE (10 min) which Alice hasn't seen
  -> Recommend VideoE to Alice, because "users like you also liked it"

ITEM-BASED CF:
  "What videos are similar to VideoA?" (compare COLUMNS, not rows)
  -> Users who watched VideoA heavily (Alice, Bob, Eve) also watched
     VideoC heavily. Users who barely watched VideoA (Carol, Dave)
     mostly watched VideoB/VideoD instead.
  -> VideoA and VideoC show strong co-occurrence -> "VideoC is similar
     to VideoA" (an ITEM-to-ITEM relationship, computed once, reusable
     for ANY user who liked VideoA)
  -> Recommend VideoC to anyone who just watched VideoA, INCLUDING
     brand-new users we don't have a rich behavioral profile for yet
     (as long as they've watched at least one item)

Why item-based scales better at YouTube/Netflix scale:
  - User count: hundreds of millions, high churn, tastes drift daily
  - Item count: tens of millions of videos, MUCH more stable structurally
    (a video's audience composition doesn't reshuffle hour to hour)
  - Item-item similarity table can be precomputed ONCE per batch cycle
    and reused for millions of users hitting the same "similar to X" query
  - User-user similarity would need re-ranking against a constantly
    shifting population of hundreds of millions of other users — far
    more expensive to keep fresh
```

### Matrix Factorization: Compressing the Sparse Matrix into Latent Factors

```
Original sparse interaction matrix R (users x items), mostly empty:

        VideoA VideoB VideoC VideoD VideoE  ...  VideoZ (10M columns)
Alice     45     ?      38     ?      12    ...    ?
Bob       40     ?      35     ?      ?     ...    ?
Carol     ?      50     ?      42     ?     ...    ?
...(500M rows)

Matrix factorization approximates R ≈ U x I^T
where U is (users x k) and I is (items x k), k = latent factor count (e.g. k=100)

User factor matrix U (500M x 100):        Item factor matrix I (10M x 100):
  Alice: [0.8, -0.3, 0.1, ..., 0.6]         VideoA: [0.9, -0.2, 0.05, ..., 0.5]
  Bob:   [0.7, -0.2, 0.3, ..., 0.4]         VideoC: [0.85, -0.25, 0.1, ..., 0.55]
  Carol: [-0.1, 0.9, -0.4, ..., 0.2]        VideoB: [-0.15, 0.8, -0.3, ..., 0.1]

Predicted preference for Alice x VideoZ (a video Alice never watched):
  predictedScore = dot(Alice_vector, VideoZ_vector)
                 = (0.8 * v1) + (-0.3 * v2) + ... + (0.6 * v100)
  -> a single float score, higher = stronger predicted preference

Storage win: instead of storing 500M x 10M = 5 QUADRILLION cells
(impossible), we store 500M x 100 + 10M x 100 = ~51 BILLION floats
(~204 GB at 4 bytes/float) — still large, but tractable, and captures
the DOMINANT patterns in the original sparse matrix via compression.

ALS (Alternating Least Squares) training loop, distributed (Spark MLlib):

  1. Initialize U and I with small random values
  2. FIX I, solve for the U that minimizes squared error against
     known (non-blank) ratings -> this is now just a least-squares
     regression problem per user, parallelizable across the cluster
  3. FIX U (just solved), solve for the I that minimizes squared error
  4. Repeat steps 2-3 for N iterations (typically 10-20) until the
     error stops improving meaningfully
  5. Output: final U and I matrices, persisted for the serving layer
```

### Failure Mode: Cold Start (New User, New Item)

```
NEW USER "UserFrank" just signed up 30 seconds ago:

  Interaction matrix row for Frank:  [?, ?, ?, ?, ?, ..., ?]  (ALL BLANK)

  Matrix factorization has NOTHING to learn Frank's latent vector from.
  dot(Frank_vector, anything) is meaningless — Frank has no vector yet.

  Fallback strategy (content-based + popularity):
    1. Ask Frank 2-3 onboarding questions ("pick genres you like") ->
       seed a rough initial vector from genre tags, OR
    2. Serve GLOBAL POPULARITY ranking ("Trending this week") until
       Frank accumulates enough watch history (typically 5-10
       interactions) for the CF model to produce a meaningful vector
    3. Some systems use "fast" online heuristics (session-based
       co-view signals from the CURRENT session) as an interim signal
       even before enough history exists for a full batch-trained vector

NEW VIDEO "VideoNew" just uploaded 10 minutes ago:

  Interaction matrix column for VideoNew: [?, ?, ?, ?, ..., ?]  (ALL BLANK)
  No user has watched it yet -> zero co-occurrence signal for
  item-based CF to compute similarity from.

  Fallback strategy:
    1. Content-based signals: title/description/tags/audio-visual
       embeddings (a separate model) place VideoNew in a rough
       "similar to X" neighborhood using CONTENT similarity, not
       behavioral co-occurrence, until real watch data accumulates
    2. Creator's existing audience: push VideoNew to users who are
       subscribed to or have a strong affinity for the SAME creator's
       past videos (a decent proxy signal even with zero direct
       interaction data on this specific new video)
    3. Small-scale exploration: allocate a limited slice of
       recommendation slots to "explore" this new item across a
       sample of users specifically to GENERATE the interaction data
       the CF model needs (classic explore/exploit tradeoff)

Without either mitigation, cold-start users/items get recommended
NOTHING relevant (blank vector -> undefined or zero score everywhere),
which is why every production recommender pairs collaborative filtering
with a content-based or popularity-based fallback layer.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Interaction Matrix as Event Log → Aggregated Table

```sql
-- Raw interaction events (append-only, from a Kafka topic consumer)
CREATE TABLE watch_events (
  user_id      BIGINT,
  video_id     BIGINT,
  watch_secs   INT,
  watched_at   TIMESTAMP
);

-- Nightly Spark batch job aggregates raw events into the
-- (user, item, implicit-rating) matrix input, e.g. normalized
-- watch-time as a proxy for "rating":
SELECT
  user_id,
  video_id,
  LEAST(SUM(watch_secs) / 60.0, 100) AS implicit_rating  -- capped, minutes watched
FROM watch_events
WHERE watched_at > NOW() - INTERVAL 90 DAY
GROUP BY user_id, video_id;

-- Output feeds directly into Spark MLlib's ALS trainer as
-- (userId: Int, itemId: Int, rating: Float) rows.
```

### ALS Training (Spark MLlib, Scala/PySpark-style Pseudocode)

```python
from pyspark.ml.recommendation import ALS

# interactions_df: DataFrame with columns [userId, itemId, rating]
als = ALS(
    userCol="userId",
    itemCol="itemId",
    ratingCol="rating",
    rank=100,                 # k = latent factor dimensionality
    maxIter=15,                # ALS alternation iterations
    regParam=0.05,              # L2 regularization to avoid overfitting sparse data
    implicitPrefs=True,        # watch-time is implicit signal, not an explicit 1-5 star rating
    alpha=40.0,                 # confidence scaling for implicit feedback
    coldStartStrategy="drop"   # drop NaN predictions for unseen users/items in eval
)

model = als.fit(interactions_df)

# model.userFactors: DataFrame[userId, features: Array[Float]]  (the U matrix)
# model.itemFactors: DataFrame[itemId, features: Array[Float]]  (the I matrix)

# Precompute top-N item-item similarities for the SERVING layer
# (offline, batch, e.g. nightly at 2 AM), so online requests never
# run ALS inference live:
item_factors = model.itemFactors.collect()
# For each item, find nearest neighbors by cosine similarity in
# latent space, persist top-50 similar items per video to a
# fast key-value store (e.g. "similar_items:{videoId}" -> [ids]).
```

### Online Serving Path (Java / Spring, Fast Lookup + Re-Rank)

```java
@Service
public class RecommendationService {

    @Autowired private RedisTemplate<String, List<Long>> redis; // precomputed similarities
    @Autowired private UserFactorStore userFactorStore;          // precomputed user vectors
    @Autowired private RealtimeReranker reranker;                // lightweight online re-rank

    public List<Long> getHomepageRecommendations(long userId) {
        // 1. Fast lookup: has the offline batch job produced a vector for this user?
        float[] userVector = userFactorStore.getVectorOrNull(userId);

        List<Long> candidates;
        if (userVector == null) {
            // Cold-start: no batch-trained vector yet, fall back to popularity
            candidates = popularityService.getTrendingVideoIds(200);
        } else {
            // Warm path: precomputed candidate set from nightly batch job
            // (top-N videos per user, already scored via U x I^T offline)
            candidates = redis.opsForValue().get("recs:precomputed:" + userId);
        }

        // 2. Lightweight ONLINE re-ranking using real-time signals
        //    (time of day, current session's last-watched genre, freshness boost)
        //    — deliberately cheap, no model re-training happens here
        return reranker.rerank(userId, candidates, /*limit*/ 20);
    }
}
```

### Real Numbers

```
Scale (YouTube-like platform, illustrative order-of-magnitude):
  Users:                  ~500 million monthly active
  Items (videos):         ~10 million actively-recommended catalog subset
                          (full catalog far larger, but long-tail rarely
                           surfaces in CF-driven recommendations at all)
  Raw interaction events: tens of billions of watch events/month

ALS training job:
  Cluster size:           50-200 Spark executor nodes (varies by platform scale)
  Latent factor rank (k): 50-200 typical (100 is a common middle ground)
  Training frequency:     nightly full retrain, or incremental/hourly
                          updates for freshness-sensitive catalogs
  Training wall-clock:    roughly 1-4 hours for a full nightly batch at
                          hundreds-of-millions-of-users scale, depending
                          on cluster size and iteration count

Precomputed similarity table:
  Size: ~10M items * top-50 similar items * 8 bytes (item ID) ≈ 4 GB
        — easily served from a fast key-value store (Redis/DynamoDB)

Serving latency:
  Precomputed lookup (Redis GET): ~1-5 ms
  Online re-ranking pass (lightweight heuristics, NOT full model inference): ~10-30 ms
  Total homepage recommendation latency budget: typically well under 100 ms,
  because the HEAVY compute (ALS training) already happened offline hours earlier.

Cold-start threshold (typical heuristic):
  Users with <5-10 total interactions: served primarily via popularity/
  content-based fallback, blended increasingly toward pure CF as
  interaction count grows.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Design the 'Recommended for You' system for a video platform with 500 million users and 10 million videos. Walk me through how you'd generate personalized recommendations, and how you'd avoid recomputing everything for every single page load."

**You (architect answer):**

> "The core technique I'd use is collaborative filtering via matrix factorization, and the critical architectural decision is splitting this into an offline batch layer and a fast online serving layer — you never want to run the heavy model computation on the request path.
>
> I'd model the problem as a user-item interaction matrix — users as rows, videos as columns, and cells populated with an implicit preference signal like normalized watch-time, since most users don't leave explicit star ratings. This matrix is enormous and almost entirely sparse — a given user has only interacted with a tiny slice of ten million videos.
>
> Rather than trying to fill in that matrix directly, I'd use matrix factorization — specifically ALS, Alternating Least Squares, run as a distributed Spark MLlib batch job — to decompose it into a user-factor matrix and an item-factor matrix, each with maybe 100 latent dimensions per row. The dot product of a user's vector and an item's vector approximates predicted preference, and critically, storing two 100-dimensional vectors per user and per item is tractable at this scale, whereas the original matrix with 500 million times 10 million cells is not.
>
> I'd lean item-based rather than user-based for the precomputed similarity structure specifically, because the item catalog, while large, is far more stable than the user population — user tastes and the user base itself churn constantly, but a video's relationship to other videos in latent space doesn't reshuffle nearly as fast. That means I can precompute a 'top-50 similar items' table for every video in a nightly batch job and reuse it across millions of requests without recomputing per-request.
>
> On the serving side, the online path is deliberately simple: look up the user's precomputed recommendation candidates — either from their trained latent vector or, for cold-start users with little history, from a popularity or content-based fallback — and apply a lightweight real-time re-ranking pass using cheap signals like time of day or the current session's context. That re-ranking is intentionally NOT re-running the full model; it's a fast heuristic layer on top of an already-computed candidate set, keeping end-to-end latency well under 100 milliseconds.
>
> The operational concern I'd flag is cold start on both sides — brand-new users and brand-new videos have zero interaction history, so their factorization vectors are meaningless. My mitigation is a hard fallback threshold: any user under roughly 5-10 total interactions gets served primarily via popularity and content-based signals, blending progressively toward full collaborative filtering as their history accumulates, and new videos get an initial exploration slice pushed to a small sample of users specifically to bootstrap the interaction data the model needs."

---

## PART 5 — DECISION FRAMEWORK

### Recommendation Strategy Comparison

| Approach | How It Works | Tradeoff | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **User-based CF** | Find similar users, recommend what they liked | Similarity recompute is volatile — user base churns/drifts constantly | Batch: hours; serve: fast lookup | Medium | Doesn't scale well as user count grows into hundreds of millions |
| **Item-based CF (this file's default)** | Find similar items via co-occurrence across all users | Item catalog more stable, precomputed table reusable across users | Batch: hours; serve: ~1-5ms lookup | Medium | Cold-start items have zero co-occurrence signal until watched |
| **Matrix factorization (ALS)** | Compress sparse matrix into latent user/item vectors | Captures deeper patterns than raw co-occurrence, but needs distributed training infra | Batch: 1-4 hrs training; serve: dot-product/lookup ~ms | High | Cold-start users/items produce meaningless vectors |
| **Content-based filtering** | Recommend based on item attributes (genre, tags, embeddings) | No cold-start problem for new items with metadata, but misses "surprising" cross-genre discoveries CF finds | Fast, no behavioral data needed | Low-Medium | Limited to attributes you've encoded; misses emergent taste patterns |
| **Popularity-based** | Recommend globally trending items | Zero personalization, but a safe universal fallback | Trivial, precomputed | Low | Provides no personalization value once enough interaction data exists |

### When collaborative filtering (item-based + ALS) is right

```
✓ Large, established user base with substantial interaction history
✓ Catalog is large enough that content tagging alone misses cross-item
  patterns real behavior reveals (e.g. surprising genre-crossing affinities)
✓ You can afford an offline batch training cycle (nightly/hourly) and
  serve from precomputed tables — not real-time model inference
✓ Item catalog is comparatively more stable than the user population
```

### Skip pure collaborative filtering when

```
✗ Cold-start dominates your traffic (mostly new users/items) -> lean
  more heavily on content-based signals and popularity defaults
✗ You lack the infrastructure for distributed batch training (Spark
  cluster, scheduled jobs) -> simpler content-based or rule-based
  recommendations may be more maintainable at smaller scale
✗ Real-time freshness is critical (breaking news feed) and nightly-batch
  latency is unacceptable -> blend in session-based/online signals,
  don't rely solely on a nightly-retrained CF model
✗ Explainability is a hard requirement (regulated domain) -> latent
  factors are not human-interpretable; content-based reasoning is
  easier to justify to an end user or auditor
```

---

## QUICK REFERENCE CARD

```
CORE CONCEPTS:
  User-based CF:  similar USERS -> recommend what they liked
  Item-based CF:  similar ITEMS (co-occurrence) -> recommend related items
                  (preferred at scale: catalog more stable than user base)

INTERACTION MATRIX:
  rows = users, cols = items, cell = rating/watch-time/click (sparse)

MATRIX FACTORIZATION:
  R (users x items) ≈ U (users x k) · I (items x k)^T
  predictedScore(u, i) = dot(U[u], I[i])
  k = latent factor count, typically 50-200

ALS (Alternating Least Squares):
  fix I -> solve U -> fix U -> solve I -> repeat ~10-20 iterations
  standard distributed implementation: Spark MLlib ALS
  implicitPrefs=True for watch-time/clicks (not explicit star ratings)

COLD START MITIGATION:
  New user (<5-10 interactions)  -> popularity / onboarding genre picks
  New item (no watch history)    -> content-based tags/embeddings,
                                     creator-audience proxy, explore slice

ARCHITECTURE SPLIT:
  OFFLINE (nightly/hourly batch): ALS training, precompute similarity/
    recommendation tables, write to fast KV store
  ONLINE (request path): fast KV lookup (~1-5ms) + lightweight
    real-time re-rank (~10-30ms) — NEVER run full model training/inference
    on the request path
```

---
