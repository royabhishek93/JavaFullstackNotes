# BM25 vs Vector Search — Keyword Relevance vs Semantic Similarity
### When Full-Text Search Fails and Why Embeddings Find What Keywords Miss

---

## PART 1 — THE STUDENT CONVERSATION

**"Our search returns zero results for 'affordable wireless earbuds' even though we have thousands of matching products. The database is full of inventory. What's wrong?"**

You have two different kinds of librarians, and you picked the wrong one.

**BM25 is a librarian who looks for exact words.** You say "affordable wireless earbuds." The librarian scans every book for the words "affordable", "wireless", "earbuds." If none of your products use those exact words — if they're all titled "Budget Bluetooth Headphones" or "Cheap In-Ear Monitors" — the librarian comes back empty-handed. Zero results. The librarian found nothing because zero words matched. They're not wrong; they just don't understand meaning.

**Vector search is a librarian who understands meaning.** You say "affordable wireless earbuds." The librarian knows:
- "affordable" ≈ "budget" ≈ "cheap" ≈ "low-cost"
- "wireless" ≈ "bluetooth" ≈ "cordless"
- "earbuds" ≈ "headphones" ≈ "in-ear" ≈ "earphones"

Even though zero words matched, they find hundreds of relevant products because they understood what you *meant*.

**The critical insight:** BM25 is great when users know the exact terminology — searching for a product SKU, an error code, a person's name. Vector search is great when users describe what they want in their own words, or when your catalog uses different vocabulary than your users.

The production answer for any serious search system: **use both.** BM25 for precision on exact terms. Vector for recall on semantics. Combine with a ranking algorithm to get the best of both.

---

## PART 2 — HOW EACH ALGORITHM WORKS

### BM25 — The Scoring Formula Explained

```
BM25 (Best Match 25) — the standard relevance algorithm in Elasticsearch and Solr

BM25(doc, query) = Σ IDF(term) × TF_normalized(term, doc)
                   term∈query

Where:
┌──────────────────────────────────────────────────────────────────────┐
│ IDF(term) = log( (N - df + 0.5) / (df + 0.5) + 1 )                 │
│   N  = total documents in corpus                                     │
│   df = number of documents containing this term                     │
│                                                                      │
│   Rare term:  "photovoltaic"  → df=100,   N=1M → IDF = 9.2 (HIGH)  │
│   Common term: "the"          → df=999K,  N=1M → IDF ≈ 0.0 (LOW)   │
│   ← Rare terms are MORE informative, score HIGHER                   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ TF_normalized(term, doc) =                                          │
│   TF(term,doc) × (k1 + 1)                                          │
│   ──────────────────────────────────────────────────                │
│   TF(term,doc) + k1 × (1 - b + b × |doc| / avgdl)                 │
│                                                                      │
│   TF(term,doc) = count of term in document                         │
│   k1  = 1.2  ← saturation factor (diminishing returns)             │
│             mentioning "iPhone" 10x vs 1x = 3x boost, not 10x      │
│   b   = 0.75 ← length normalization                                │
│             long documents get slight penalty (avoid stuffing)      │
│   |doc|    = document length (word count)                           │
│   avgdl    = average document length across corpus                  │
└──────────────────────────────────────────────────────────────────────┘

Example: Query "cheap flights"
  Corpus = 1,000,000 travel documents

  "cheap":   df = 10,000  → IDF = log(1M/10K) = 4.6
  "flights": df = 100,000 → IDF = log(1M/100K) = 2.3

  Document A: "Cheap flights to Paris — budget airline deals" (10 words)
    TF("cheap",A) = 1, TF("flights",A) = 1
    score ≈ 4.6 × 1.0 + 2.3 × 1.0 = 6.9 (relatively short, high score)

  Document B: Long 500-word blog post mentioning "cheap" 3x and "flights" 5x
    TF saturation: 3 mentions ≈ 1.8× boost (not 3×, thanks to k1=1.2)
    Length penalty: 500 words vs avgdl=100 → b=0.75 normalizes score down
    score ≈ 5.5 (less than A despite more mentions!)
    ← Length normalization works correctly
```

### Vector Search — Semantic Similarity via Embeddings

```
Step 1: Text → Embedding (high-dimensional vector)

  "affordable car hire"    → model → [0.23, -0.11, 0.87, 0.04, ...]  (768 dims)
  "cheap vehicle rental"   → model → [0.24, -0.10, 0.86, 0.05, ...]  (768 dims)
  "quantum mechanics"      → model → [0.91,  0.43, -0.22, 0.71, ...] (768 dims)

Step 2: Similarity measurement (Cosine Similarity)

  cosine_similarity(A, B) = (A · B) / (||A|| × ||B||)
                           = dot product / (norm_A × norm_B)
  Range: [-1, 1]
    1.0  = identical meaning
    0.0  = orthogonal (unrelated)
   -1.0  = opposite meaning

  sim("affordable car hire", "cheap vehicle rental") ≈ 0.94 ← very similar!
  sim("affordable car hire", "quantum mechanics")    ≈ 0.12 ← unrelated

Step 3: ANN Index (Approximate Nearest Neighbor) — HNSW

  Brute force search: O(N × D) where N=docs, D=dimensions
    At 10M docs × 768 dims: 7.68B multiply-adds per query → 5-10 seconds
    Completely unusable.

  HNSW (Hierarchical Navigable Small World):
  ┌──────────────────────────────────────────────────────────────────┐
  │ Layer 2 (sparse):  O─────────────────────O                      │
  │                                                                  │
  │ Layer 1 (medium):  O──────O──────O──────O──────O                │
  │                           │             │                       │
  │ Layer 0 (dense):   O─O─O─O─O─O─O─O─O─O─O─O─O─O                │
  │                                     ↑                           │
  │                                  Query enters at top layer      │
  │                              Navigates down to local neighbors  │
  └──────────────────────────────────────────────────────────────────┘

  Performance at 10M vectors:
    Query time:   1-10ms  (vs 5-10s brute force)
    Recall@10:    95-99%  (approximate — misses ~1-5% of true neighbors)
    Index build:  O(N log N) time, O(N × M × D × 4 bytes) memory
                  where M = HNSW parameter (edges per node, typically 16-64)
    
  Elasticsearch HNSW config:
    "index": { "knn": true }
    "knn_vector": { "dimension": 768, "method": { "name": "hnsw",
                    "parameters": { "m": 16, "ef_construction": 100 } } }
    m=16:              16 edges per node (higher = better recall, more memory)
    ef_construction:   100 nodes examined during index build per insertion
```

### Hybrid Search — Best of Both Worlds

```
Scenario: E-commerce search for "buy iPhone 15 case"

BM25 results (keyword precision):
  Rank 1: "iPhone 15 Case - Clear Slim Cover"     ← exact keyword match
  Rank 2: "iPhone 15 Case - Black Leather"        ← exact keyword match
  Rank 3: "iPhone 14 Case"                        ← close but wrong model
  ...
  (Misses: "phone protective shell", "mobile cover" — different words)

Vector results (semantic recall):
  Rank 1: "Protective phone cover transparent"    ← semantic match
  Rank 2: "Mobile device case slim fit"           ← semantic match
  Rank 3: "Smartphone armor case heavy duty"      ← semantic match
  ...
  (Misses: ranking iPhone 15 specifically — doesn't understand model numbers)

Problem: BM25 misses synonyms. Vector misses specificity on model numbers.
Solution: RRF (Reciprocal Rank Fusion)

RRF_score(doc) = Σ 1 / (rank_in_list + k)
                 each_list
  k = 60 (smoothing constant, reduces impact of very top ranks)

Example calculation (k=60):
  "iPhone 15 Case - Clear" BM25=rank1, Vector=rank7:
    RRF = 1/(1+60) + 1/(7+60) = 0.01639 + 0.01493 = 0.03132

  "Protective phone cover"  BM25=rank100, Vector=rank1:
    RRF = 1/(100+60) + 1/(1+60) = 0.00625 + 0.01639 = 0.02264

  Final order: iPhone 15 Case > Protective phone cover
  ← Exact keyword match ranks higher, semantic fills the gaps

Elasticsearch 8.x hybrid query:
{
  "query": {
    "bool": {
      "should": [
        {
          "match": {
            "title": { "query": "buy iPhone 15 case", "boost": 1.0 }
          }
        }
      ]
    }
  },
  "knn": {
    "field": "title_vector",
    "query_vector": <embedding of "buy iPhone 15 case">,
    "k": 10,
    "num_candidates": 100,
    "boost": 1.0
  },
  "rank": { "rrf": { "window_size": 100, "rank_constant": 60 } }
}
```

### When BM25 Wins vs Vector Wins

```
BM25 WINS when:                        VECTOR WINS when:
───────────────────────────────────    ────────────────────────────────────
Exact product SKU: "iphone-15-pro"     User intent: "phone for low light photos"
Error code: "NullPointerException"     Synonym mismatch: "affordable" vs "cheap"
Person name: "John Smith"              Cross-lingual: "voiture" finds "car"
ISBN/model number search               Describe, don't name: "camping cold weather"
Medical code: "ICD-10 E11.9"           Conceptual match: "budget" ≈ "affordable"
Legal case citations                   Fuzzy intent: "something for cooking pasta"

BM25 SCORE → 0 when: zero query words appear in document
Vector SCORE → low when: topic is genuinely unrelated (not just different words)

Real failure mode of pure BM25:
  Query: "I need something to protect my new iPhone"
  BM25 result: 0 matches (no document contains "protect" "new" "iPhone" together)
  ← User says "protect", catalog says "case" "cover" "armor"
  
Real failure mode of pure Vector:
  Query: "model A1234 battery replacement"
  Vector: finds "battery" and "replacement" semantically but model A1234
          might map to wrong model if embeddings conflate model numbers
  ← Specific codes/identifiers don't encode well as semantic vectors
```

---

## PART 3 — IMPLEMENTATION DEEP DIVE

### Embedding Generation Pipeline

```python
# Option 1: OpenAI API (hosted, best quality)
from openai import OpenAI

client = OpenAI()

def get_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    # Dimensions: text-embedding-3-small = 1536
    #             text-embedding-3-large = 3072 (better quality, 2x cost)
    response = client.embeddings.create(model=model, input=text)
    return response.data[0].embedding  # list of 1536 floats

# Batch embedding (much cheaper):
texts = ["iPhone 15 case", "wireless earbuds", "laptop stand"]
response = client.embeddings.create(model="text-embedding-3-small", input=texts)
embeddings = [r.embedding for r in response.data]

# Cost: $0.02 per 1M tokens (text-embedding-3-small)
#       At avg 20 tokens/product title: $0.02/1M × 20 × 1M products = $0.40 for 1M products


# Option 2: Local model (no API cost, runs in your infra)
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')  # 80MB, 384 dims, fast
# OR
model = SentenceTransformer('all-mpnet-base-v2')  # 420MB, 768 dims, better quality

embedding = model.encode("affordable wireless earbuds")  # numpy array, 384 floats


# Indexing pipeline (at product catalog load):
def index_product(product: dict, es_client):
    embedding = get_embedding(product['title'] + ' ' + product['description'])
    es_client.index(
        index='products',
        id=product['id'],
        body={
            'title': product['title'],
            'description': product['description'],
            'price': product['price'],
            'category': product['category'],
            'title_vector': embedding  # stored as dense_vector field
        }
    )
```

### Elasticsearch Index Mapping for Hybrid Search

```json
PUT /products
{
  "mappings": {
    "properties": {
      "title": {
        "type": "text",
        "analyzer": "english"
      },
      "description": {
        "type": "text",
        "analyzer": "english"
      },
      "title_vector": {
        "type": "dense_vector",
        "dims": 1536,
        "index": true,
        "similarity": "cosine",
        "index_options": {
          "type": "hnsw",
          "m": 16,
          "ef_construction": 100
        }
      },
      "price": { "type": "float" },
      "category": { "type": "keyword" }
    }
  }
}
```

### Synonym Expansion for BM25 (Complementary to Vector)

```json
PUT /products/_settings
{
  "analysis": {
    "filter": {
      "product_synonyms": {
        "type": "synonym",
        "synonyms": [
          "affordable, cheap, budget, low-cost, inexpensive",
          "earbuds, headphones, earphones, in-ear monitors",
          "wireless, bluetooth, cordless",
          "phone, mobile, smartphone, cell phone",
          "case, cover, shell, armor, protector"
        ]
      }
    },
    "analyzer": {
      "product_search_analyzer": {
        "type": "custom",
        "tokenizer": "standard",
        "filter": ["lowercase", "product_synonyms", "english_stemmer"]
      }
    }
  }
}
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your e-commerce search returns zero results for 'affordable wireless earbuds' even though you have 1,000 products fitting that description. What's wrong and how do you fix it?"

**You:** "Zero results from a large catalog is a classic BM25 vocabulary mismatch. The products probably have titles like 'Budget Bluetooth Headphones' or 'Cheap In-Ear Monitors' — none of which contain the words 'affordable', 'wireless', or 'earbuds' exactly. BM25 needs at least one query term to match a document term. If none match, score = 0.

Two complementary fixes:

**Fix 1 — Synonym expansion in the BM25 analyzer.** Define a synonym filter: `affordable → [cheap, budget, low-cost]`, `earbuds → [headphones, earphones, in-ear]`, `wireless → [bluetooth, cordless]`. Now BM25 matches on the expanded terms. This handles the known vocabulary gap but requires maintaining the synonym dictionary — it won't auto-adapt to new phrasings.

**Fix 2 — Add vector search (semantic layer).** Encode all product titles as embeddings using a sentence transformer model. Build an HNSW index on those vectors. When the user queries 'affordable wireless earbuds', embed that query and find the 20 most semantically similar product vectors. 'Budget Bluetooth Headphones' will have cosine similarity of 0.88 to the query — they'll appear in results even with zero keyword overlap.

**Production recommendation: hybrid search with RRF.** Run BM25 and vector in parallel. Merge rankings using Reciprocal Rank Fusion with k=60. Products that rank well in both (exact keyword match AND semantic match) float to the top. Products that match only by semantics fill in when keyword results are thin. Elasticsearch 8.x supports this natively with the `rank: {rrf: {}}` parameter.

On the embedding pipeline: generate embeddings at index time when products are created or updated. Store the vector in a `dense_vector` field in Elasticsearch. At query time, embed the search query — that's the only runtime embedding call (takes ~5ms with a local model). Total overhead of the hybrid vs pure BM25: about 5ms for the query embedding + HNSW lookup, which returns in ~3ms. Total latency increase: ~8ms. Completely acceptable for a 100ms search SLA."

**Interviewer:** "When would you NOT use vector search?"

**You:** "Three cases. First, exact lookup by identifier: searching for a user ID, product SKU, order number, or error code. These don't have semantic meaning — they're just identifiers. BM25 or a direct database lookup is correct; vector search would actually return wrong results (nearby embeddings of similar-looking codes). Second, when the catalog is small — under 10,000 documents. The engineering overhead of embedding generation, vector index maintenance, and hybrid ranking isn't worth it; BM25 with synonym expansion solves the problem. Third, when freshness is critical. Vector indexes take longer to update than BM25 (you need to regenerate the embedding on every document change). If products update by the second and you need sub-second search freshness, vector search requires more infrastructure."

---

## PART 5 — DECISION FRAMEWORK

### Query Type × Search Method Matrix

```
┌──────────────────────┬──────────┬──────────────┬────────────────────────┐
│ Query Type           │ BM25     │ Vector       │ Hybrid                 │
├──────────────────────┼──────────┼──────────────┼────────────────────────┤
│ Exact identifier     │ ✅ Best  │ ❌ Wrong     │ ❌ Overkill            │
│ (SKU, error code)    │         │              │                        │
├──────────────────────┼──────────┼──────────────┼────────────────────────┤
│ Known terminology    │ ✅ Best  │ Good         │ Slight improvement     │
│ (exact product name) │         │              │                        │
├──────────────────────┼──────────┼──────────────┼────────────────────────┤
│ Synonym-heavy domain │ ❌ Poor  │ ✅ Best      │ ✅ Best               │
│ (natural language)   │         │              │                        │
├──────────────────────┼──────────┼──────────────┼────────────────────────┤
│ Conceptual intent    │ ❌ Miss  │ ✅ Best      │ ✅ Best               │
│ ("cold camping gear")│         │              │                        │
├──────────────────────┼──────────┼──────────────┼────────────────────────┤
│ Typo / misspelling   │ ❌ Miss  │ Good         │ Good (vector rescues) │
│ ("iphon cse")        │         │              │                        │
├──────────────────────┼──────────┼──────────────┼────────────────────────┤
│ Mixed: name + intent │ Partial  │ Partial      │ ✅ Best               │
│ ("cheap iPhone case")│         │              │                        │
└──────────────────────┴──────────┴──────────────┴────────────────────────┘
```

### Embed Model Selection Guide

```
Model                              Dims   Size    Latency  Quality  Cost
──────────────────────────────────────────────────────────────────────────
OpenAI text-embedding-3-small      1536   hosted  ~20ms    Good     $0.02/1M tokens
OpenAI text-embedding-3-large      3072   hosted  ~30ms    Best     $0.13/1M tokens
sentence-transformers/all-MiniLM   384    80MB    ~3ms     OK       Free (local)
sentence-transformers/all-mpnet    768    420MB   ~10ms    Good     Free (local)
BAAI/bge-large-en-v1.5             1024   1.3GB   ~15ms    Best     Free (local)

Rule of thumb:
  Prototype / small scale: all-MiniLM (fast, free, good enough)
  Production / high quality: OpenAI text-embedding-3-small (hosted, no infra)
  Production / cost-sensitive: BGE-large (best free model, host it yourself)
```

---

## QUICK REFERENCE CARD

```
BM25 FORMULA (simplified):
  score(doc, query) = Σ IDF(term) × TF_saturated(term, doc)
  IDF: rare terms score higher
  TF_saturated: diminishing returns (k1=1.2), length normalized (b=0.75)

COSINE SIMILARITY:
  similarity = dot_product(A, B) / (||A|| × ||B||)
  Range: [-1, 1], higher = more similar meaning
  Threshold for "similar enough": typically 0.75-0.85 (domain-dependent)

HNSW KEY PARAMETERS:
  m = 16               ← edges per node (higher = better recall, more RAM)
  ef_construction=100  ← search depth during index build (higher = better recall)
  ef_search=50         ← search depth at query time (higher = better recall, slower)
  Expected recall@10: ~97% at m=16, ef_search=50

RRF FUSION:
  score(doc) = Σ 1/(rank_in_list + 60) across all lists
  k=60: standard smoothing, reduces dominance of rank 1
  Use when combining 2+ ranking lists of different scales

HYBRID SEARCH CHECKLIST:
  1. Add dense_vector field to ES mapping (dims must match model)
  2. Index time: generate embedding, store alongside document
  3. Query time: embed query (~5ms), run knn + bm25 in parallel, RRF merge
  4. Monitor: measure P50/P99 of embedding call + HNSW search separately
  5. Evaluate: offline A/B with NDCG metric on labeled query set

EMBEDDING LATENCY BUDGET:
  Local model (all-MiniLM): ~3ms per query → negligible
  Hosted API (OpenAI):      ~20ms per query → add to p99 budget
  At 1000 QPS: 1000 × 0.02s = 20s of compute/second → needs batching or GPU
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

```
┌──────┬─────────────────────┬────────────────────────────────────────────────────────────────┐
│  #   │ System              │ Search Pattern                                                 │
├──────┼─────────────────────┼────────────────────────────────────────────────────────────────┤
│  09  │ E-Commerce          │ Product search: BM25 for exact SKU/brand. Vector for           │
│      │                     │ "find me something for camping in cold weather." Hybrid for     │
│      │                     │ general product discovery. Synonym dict for common categories. │
├──────┼─────────────────────┼────────────────────────────────────────────────────────────────┤
│  14  │ Proximity Search    │ "Find Italian restaurants nearby" — BM25 on cuisine/name field  │
│      │                     │ + vector on review text + geo_distance filter applied on top.  │
│      │                     │ Elasticsearch handles geo + text in a single query.            │
├──────┼─────────────────────┼────────────────────────────────────────────────────────────────┤
│  20  │ Email (Gmail-like)  │ Gmail search: BM25 for exact sender/subject/keyword. Vector    │
│      │                     │ for "find emails about the Q3 budget meeting" even if the      │
│      │                     │ emails say "Q3 finance discussion." Hybrid with date-based     │
│      │                     │ recency boost.                                                 │
├──────┼─────────────────────┼────────────────────────────────────────────────────────────────┤
│  All │ RAG / LLM systems   │ Vector search is the retrieval step in RAG (Retrieval-         │
│      │                     │ Augmented Generation). Query → embed → kNN → top-K chunks →   │
│      │                     │ LLM context. BM25 used for hybrid RAG to improve precision.   │
└──────┴─────────────────────┴────────────────────────────────────────────────────────────────┘
```

---

> **Architect's one-liner:** "BM25 matches keywords, vector search matches meaning — use hybrid search with RRF fusion to get exact matches first and semantic fallback when keywords fail."
