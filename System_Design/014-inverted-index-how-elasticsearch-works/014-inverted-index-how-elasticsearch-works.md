# Inverted Index: How Elasticsearch Works
### From "find text in a file" to ranking 50M products in under 100ms

---

## PART 1 — THE STUDENT CONVERSATION

You know the index at the back of a textbook. The book has 500 pages. You want to find every page that mentions "database." Without the index: read all 500 pages. With the index: look up "database" — see pages 23, 45, 67, 234. Done. Five seconds, not an hour.

That index is INVERTED. Normal document structure: document → words it contains. Inverted index: word → list of documents that contain it. The direction is flipped.

Elasticsearch is essentially a massive, distributed inverted index stored across many machines, with a scoring system to rank results by how relevant they are to your query.

Now here's the thing about your regular database. PostgreSQL has a `LIKE` operator:

```sql
SELECT * FROM products WHERE name LIKE '%running shoes%';
```

This works — but it forces a full table scan. It cannot use a B-tree index because `%` at the start means "could start with anything." At 50M products, this query takes minutes. And it doesn't even score results by relevance — "blue running shoes size 10 for men" and "running shoes" get equal weight.

Elasticsearch solves both problems: sub-100ms search on hundreds of millions of documents, plus TF-IDF/BM25 relevance scoring so "blue running shoes" ranks above "shoes that sometimes run on electricity."

Let's trace exactly what happens when you index a document and then search for it.

---

## PART 2 — THE INVERTED INDEX DIAGRAMS

### Building the Index: From Documents to Posting Lists

```
Step 1 — Raw documents:
  doc_1: "The quick brown fox"
  doc_2: "The fox jumped high"
  doc_3: "Quick brown rabbits"

Step 2 — Tokenize (split on whitespace, punctuation):
  doc_1: ["The", "quick", "brown", "fox"]
  doc_2: ["The", "fox", "jumped", "high"]
  doc_3: ["Quick", "brown", "rabbits"]

Step 3 — Normalize (lowercase, remove stop words like "the"):
  doc_1: ["quick", "brown", "fox"]
  doc_2: ["fox", "jumped", "high"]
  doc_3: ["quick", "brown", "rabbits"]

Step 4 — (Optional) Stem ("running" → "run", "jumped" → "jump"):
  doc_2: ["fox", "jump", "high"]

Step 5 — Build posting list (term → sorted list of docIds):

┌──────────┬────────────────────────────────────────────────────────┐
│  Term    │  Posting List: [(docId, position, termFreq)]           │
├──────────┼────────────────────────────────────────────────────────┤
│  quick   │  [(doc_1, pos=1, tf=1), (doc_3, pos=1, tf=1)]         │
│  brown   │  [(doc_1, pos=2, tf=1), (doc_3, pos=2, tf=1)]         │
│  fox     │  [(doc_1, pos=3, tf=1), (doc_2, pos=1, tf=1)]         │
│  jump    │  [(doc_2, pos=2, tf=1)]                                │
│  high    │  [(doc_2, pos=3, tf=1)]                                │
│  rabbits │  [(doc_3, pos=3, tf=1)]                                │
└──────────┴────────────────────────────────────────────────────────┘

Query: "quick fox"
  "quick" → posting list: [doc_1, doc_3]
  "fox"   → posting list: [doc_1, doc_2]

  AND (both terms required):  doc_1 only
  OR  (either term, scored):  doc_1 (2 terms, highest BM25), doc_2, doc_3

BM25 score for doc_1:
  - Contains "quick": tf=1, idf = log(3 docs / 2 containing "quick") = low-ish
  - Contains "fox":   tf=1, idf = log(3 docs / 2 containing "fox") = low-ish
  - doc_1 score = sum of both term scores (highest of the 3)
```

### Elasticsearch Shard Architecture

```
Index: "products"
Config: 5 primary shards, 1 replica per shard
Cluster: 3 nodes

Distribution:
  Node-1: Shard-0 (primary), Shard-1 (replica), Shard-4 (primary)
  Node-2: Shard-1 (primary), Shard-2 (replica), Shard-0 (replica)
  Node-3: Shard-2 (primary), Shard-3 (primary), Shard-1 (replica)
                                                  ^^ wait, that's wrong
  (Elasticsearch ensures primary and replica are NEVER on same node)

Search flow for "blue running shoes":

  Client
    |
    v
  Coordinating Node (any node can be coordinator)
    |-- broadcasts query to all 5 PRIMARY shards (or replicas for read scaling)
    |
    |-- Shard-0: local inverted index lookup
    |       → top 10 results from this shard, with scores
    |-- Shard-1: local inverted index lookup
    |       → top 10 results from this shard, with scores
    |-- Shard-2: local inverted index lookup
    |       → top 10 results from this shard, with scores
    |-- Shard-3: local inverted index lookup
    |       → top 10 results from this shard, with scores
    |-- Shard-4: local inverted index lookup
    |       → top 10 results from this shard, with scores
    |
    v
  Coordinating node collects 50 results (5 shards x 10 each)
  Merge + re-rank by global BM25 score
  Return global top 10 to client

Total time: ~20-80ms (parallel shard queries + merge)
```

### Lucene Segments (Write Path)

```
Index "products", Shard-0 internal structure:

  segment_1  [immutable, 100K docs, 2GB]  ← older, large, merged
  segment_2  [immutable, 80K docs,  1.6GB]
  segment_3  [immutable, 20K docs,  400MB]
  segment_4  [immutable, 5K docs,   100MB]
  in_memory  [mutable,   300 docs,  6MB]   ← new writes land here

Write: new document → goes to in_memory buffer
       every 1 second (default): flush in_memory → new immutable segment
       (document is now SEARCHABLE — this is "near-real-time" 1s latency)

Background merge: Lucene combines small segments into larger ones
  segment_3 + segment_4 → segment_5 (25K docs, 500MB)
  (old segments deleted after merge, disk space reclaimed)

Why immutable? Simpler, cache-friendly, no concurrent write conflicts.
Delete = mark document as deleted in .del file, excluded from search results.
Update = delete old + insert new.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Index Mapping: The Schema You Must Get Right

```json
PUT /products
{
  "mappings": {
    "properties": {
      "name": {
        "type": "text",
        "analyzer": "english"
      },
      "brand": {
        "type": "keyword"
      },
      "price": {
        "type": "float"
      },
      "category": {
        "type": "keyword"
      },
      "description": {
        "type": "text",
        "analyzer": "standard"
      },
      "tags": {
        "type": "keyword"
      }
    }
  }
}
```

The critical distinction:
- `text` = analyzed (tokenized, lowercased, stemmed). Use for full-text search fields (product name, description). Cannot use for exact match, sorting, or aggregations.
- `keyword` = exact match, no analysis. Use for filtering (category="Shoes"), sorting (price), and aggregations (facets). "Nike" stays "Nike" — not tokenized.

Common mistake: mapping a field as `text` when you need to GROUP BY it (for facets like "show me count by brand"). Solution: use `fields` to index both ways:

```json
"brand": {
  "type": "text",
  "fields": {
    "keyword": { "type": "keyword" }
  }
}
// Search: brand (text, analyzed)
// Facet/filter: brand.keyword (exact)
```

### Analyzers: The Tokenization Pipeline

```
Standard analyzer (default):
  Input:  "Blue Running Shoes, Size 10!"
  Output: ["blue", "running", "shoes", "size", "10"]

English analyzer (language-aware):
  Input:  "Blue Running Shoes"
  Output: ["blue", "run", "shoe"]   ← stemmed: running→run, shoes→shoe
  Benefit: query "run" matches "running", "runner", "runs"

Custom analyzer for product search:
  Input:  "iphone-14 pro max"
  Standard: ["iphone", "14", "pro", "max"]
  Custom:   ["iphone", "14", "pro", "max", "iphone-14"]  ← preserve hyphenated brand
  Benefit: exact search "iphone-14" works, AND individual word search works

Custom analyzer definition:
{
  "analysis": {
    "analyzer": {
      "product_analyzer": {
        "type": "custom",
        "tokenizer": "standard",
        "filter": ["lowercase", "english_stemmer", "word_delimiter_graph"]
      }
    }
  }
}
```

### BM25 Scoring Formula

```
BM25 score for term t in document d:

score(t, d) = IDF(t) * (TF(t,d) * (k1 + 1)) / (TF(t,d) + k1 * (1 - b + b * |d|/avgdl))

Where:
  IDF(t) = log((N - df + 0.5) / (df + 0.5) + 1)
    N    = total number of documents
    df   = number of docs containing term t
    (rare terms get higher IDF — "postgresql" is rarer than "the")

  TF(t,d) = raw term frequency in doc d
  |d|     = length of document d (in terms)
  avgdl   = average document length across index
  k1      = 1.2 (controls TF saturation — after 5 occurrences, barely increases)
  b       = 0.75 (field length normalization — long docs don't dominate)

Practical implication:
  "blue" appears in 10M of 50M products  → low IDF (common term, low weight)
  "Gore-Tex" appears in 5K of 50M products → high IDF (rare term, high weight)
  A product named "Gore-Tex running shoes" outranks "blue shoes" for "Gore-Tex shoes"
```

### Debugging with EXPLAIN API

```bash
# Why did document 42 rank where it did?
GET /products/_explain/42
{
  "query": {
    "match": { "name": "blue running shoes" }
  }
}

# Response shows:
# {
#   "_explanation": {
#     "value": 4.752,
#     "description": "sum of:",
#     "details": [
#       { "value": 2.1, "description": "weight(name:blue in 42)" },
#       { "value": 1.3, "description": "weight(name:run in 42)" },
#       { "value": 1.35, "description": "weight(name:shoe in 42)" }
#     ]
#   }
# }
```

### Full Production Query: "blue running shoes size 10"

```json
GET /products/_search
{
  "query": {
    "bool": {
      "must": [
        {
          "multi_match": {
            "query": "blue running shoes size 10",
            "fields": ["name^3", "description^1", "tags^2"],
            "type": "best_fields",
            "fuzziness": "AUTO"
          }
        }
      ],
      "filter": [
        { "term": { "category": "footwear" } },
        { "range": { "price": { "gte": 20, "lte": 300 } } },
        { "term": { "in_stock": true } }
      ]
    }
  },
  "aggs": {
    "by_brand": { "terms": { "field": "brand.keyword" } },
    "price_range": { "range": { "field": "price",
      "ranges": [{"to":50},{"from":50,"to":100},{"from":100}] } }
  },
  "size": 20
}

// name^3 = name field gets 3x score boost (most important)
// filter = no scoring, just binary include/exclude (faster + cached)
// aggs = facets returned alongside results (brand counts, price buckets)
// fuzziness = "AUTO" handles typos: "shose" matches "shoes"
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your e-commerce search needs to find products by name. You have 50M products. A user types 'blue running shoes size 10'. How does Elasticsearch find relevant products in under 100ms?"

**You (architect answer):**

> "When the user types 'blue running shoes size 10,' Elasticsearch has already built an inverted index at index time. Each product's name was analyzed — tokenized, lowercased, stemmed — so 'running' became 'run' and 'shoes' became 'shoe.' The inverted index maps each term to the list of product IDs containing that term, stored in compressed sorted lists called posting lists.
>
> At query time, Elasticsearch looks up posting lists for 'blue,' 'run,' 'shoe,' and '10' — each lookup is O(log V) where V is vocabulary size. It intersects or unions those lists, and scores each result using BM25, which balances how often the term appears in that specific document against how rare that term is across all 50M products.
>
> The 50M products are spread across, say, 5 shards. The coordinating node fans the query out to all 5 shards in parallel. Each shard runs the inverted index lookup locally and returns its top 20 results. The coordinating node merges 100 results (5 shards × 20 each), re-ranks by global BM25 score, and returns the top 20. This fan-out and merge adds maybe 10ms of network overhead — the rest is pure inverted index lookup, which is fast because it's all compressed in-memory data structures.
>
> To keep the query under 100ms, I'd make sure the heavy BM25 scoring runs in the `must` clause (which scores), and cheap filters like 'in_stock = true' and 'price < 200' run in the `filter` clause — filter results are cached and require no scoring, so they're essentially free."

---

## PART 5 — DECISION FRAMEWORK

### PostgreSQL Full-Text vs Elasticsearch: When to Use Which

| Criteria | PostgreSQL `pg_tsvector` | Elasticsearch |
|---|---|---|
| **Data volume** | Up to ~10M rows comfortably | 10M → 10B+ documents |
| **Query complexity** | Simple keyword match + boolean | Multi-field, fuzzy, facets, nested |
| **Relevance ranking** | Basic (ts_rank) | BM25, custom boosting, learning-to-rank |
| **Faceted search** | Manual GROUP BY (slow) | Aggregations (fast, native) |
| **Autocomplete/suggest** | Partial — needs trigram index | Native (completion suggester) |
| **Operational complexity** | Zero extra infra (already have PG) | Separate cluster, JVM tuning, shard planning |
| **Consistency with writes** | Immediate (same DB transaction) | Near-real-time (1s lag) |
| **Typo tolerance** | No (unless pg_trgm similarity) | Native fuzziness parameter |
| **Best for** | Internal admin search, <5M rows, no facets | Customer-facing search, catalog, log search |

### Scale Thresholds

```
< 1M documents:
  PostgreSQL tsvector + GIN index is fine.
  EXPLAIN ANALYZE your queries. If < 50ms, stay on Postgres.

1M - 10M documents:
  PostgreSQL can still work with careful index tuning.
  Switch to Elasticsearch if you need facets or fuzzy search.

10M - 1B documents:
  Elasticsearch. Multiple shards. Plan shard count upfront
  (cannot split a shard later — must reindex).
  Rule of thumb: 1 shard per 50GB of data, max 30GB per shard.

> 1B documents:
  Elasticsearch + hot/warm/cold tiering.
  Recent data: hot nodes (SSD, high CPU).
  Older data: warm nodes (spinning disk, less CPU).
  Archived data: cold nodes (S3-backed via frozen indices).
```

---

## QUICK REFERENCE CARD

```
INDEX CREATION:
  PUT /products { "mappings": { "properties": {
    "name":     { "type": "text",    "analyzer": "english" },
    "category": { "type": "keyword"                        },
    "price":    { "type": "float"                          }
  }}}

SEARCH QUERY SKELETON:
  { "query": { "bool": {
      "must":   [ match queries (scored)  ],
      "filter": [ term/range queries (not scored, cached) ]
  }},
  "aggs": { "brands": { "terms": { "field": "brand.keyword" }}},
  "size": 20 }

FIELD TYPES (memorize):
  text    = analyzed, for full-text search
  keyword = exact, for filter/sort/agg
  float   = number
  date    = date
  geo_point = lat/lng coordinates

SHARD PLANNING:
  Target shard size: 20-50GB
  formula: shards = ceil(total_data_gb / 40)
  Cannot change shard count without reindexing

NEAR-REAL-TIME:
  Default refresh interval: 1 second
  New docs searchable after ~1s
  To force immediate: POST /products/_refresh (expensive, avoid in prod)
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Every time an interview mentions "search," "full-text," "find by name," or "log search" — Elasticsearch and its inverted index is the answer. Understand that it is not a database — it is an eventually-consistent search index that you populate from your primary database.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **14 — Proximity Search** | Searching for restaurants/places by name AND proximity combined in one query. Elasticsearch `geo_point` field type + full-text match on business name. A single query handles "coffee shops near me" — full-text on "coffee shops" + geo_distance filter. |
| **15 — Distributed Logging (ELK Stack)** | Log search is literally an inverted index problem. Find all logs containing "NullPointerException" across 1TB of log data from 500 servers. Elasticsearch: each log line's tokens are indexed — a query returns matching logs in milliseconds rather than scanning terabytes. This is the "E" in the ELK Stack (Elasticsearch + Logstash + Kibana). |
| **20 — Email (Gmail-scale)** | Gmail-style search: "find emails containing 'invoice' from 'amazon' in 2024." Inverted index on email body + metadata fields (From, Date, Subject) as keyword fields for filtering. At Gmail's scale (1B+ users), sharding by user_id keeps each user's email index isolated. |

**Architect's one-liner for the interview:**
*"Elasticsearch pre-builds an inverted index at write time — a term-to-document map — so at query time it's not scanning documents, it's looking up a sorted list of matching IDs and scoring them by BM25 relevance in milliseconds regardless of dataset size."*

---
