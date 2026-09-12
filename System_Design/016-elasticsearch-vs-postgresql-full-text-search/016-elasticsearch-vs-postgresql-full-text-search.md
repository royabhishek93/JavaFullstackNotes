# Elasticsearch vs PostgreSQL Full-Text Search
### When pg_tsvector Is Enough and When You Need Elasticsearch

---

## PART 1 — THE STUDENT CONVERSATION

**"We're building a product search. The team wants to add Elasticsearch but we already have PostgreSQL. Do we really need a separate system?"**

Here's an honest answer: maybe not. Let me explain the difference with an analogy.

**PostgreSQL full-text search is like adding a searchable index to a notebook.** Your notebook (PostgreSQL) is already excellent at storing and retrieving structured data. Adding a `tsvector` column with a GIN index gives you solid keyword search, stemming, ranking, and stop words. Works great. Fast enough for millions of rows. And you already have the notebook — zero extra infrastructure.

**Elasticsearch is a search engine first, storage second.** Like having a dedicated Google-quality search appliance plugged in alongside your notebook. It's purpose-built for search: distributed by design, optimized for text analysis, natively handles faceted search (filter by category AND price AND brand in one query), typo tolerance, autocomplete, vector search, and can answer queries across a billion documents in under 10ms. But it's a separate system — you need to deploy it, operate it, keep it in sync with your PostgreSQL source of truth, and pay for the infrastructure.

**The question is not which is "better."** It's: does my use case justify the added complexity?

For a product catalog with 500K items and basic search, PostgreSQL full-text search is completely sufficient. For an e-commerce platform with 50M products, faceted search, relevance tuning, typo tolerance, and semantic search — that's Elasticsearch territory.

The pattern most large systems use: **PostgreSQL as the source of truth (ACID writes), Elasticsearch as the search index (fast reads)**. They run in parallel, kept in sync via Change Data Capture.

---

## PART 2 — CAPABILITIES SIDE BY SIDE

### PostgreSQL Full-Text Search Setup and Capabilities

```sql
-- Step 1: Add a generated tsvector column
ALTER TABLE products
ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    to_tsvector('english',
      coalesce(title, '')
      || ' ' || coalesce(description, '')
      || ' ' || coalesce(brand, '')
    )
  ) STORED;
-- STORED: computed on insert/update, stored on disk (no runtime cost)
-- to_tsvector('english', ...): applies English dictionary (stemming + stopwords)

-- Step 2: Build GIN index on the tsvector column
CREATE INDEX products_search_gin_idx ON products USING GIN(search_vector);
-- GIN (Generalized Inverted Index): maps lexeme → set of row locations
-- Build time: ~10 min for 10M rows, ~100 min for 100M rows
-- Size: roughly 30-40% of the original text column size

-- Step 3: Query with ranking
SELECT
  id,
  title,
  ts_rank(search_vector, query) AS rank
FROM
  products,
  plainto_tsquery('english', 'wireless headphones') query
WHERE
  search_vector @@ query
ORDER BY rank DESC
LIMIT 10;

-- plainto_tsquery: treats input as words, ANDs them (all must match)
-- phraseto_tsquery: requires words to be adjacent ("red apple" ≠ "apple red")
-- websearch_to_tsquery: supports - for exclude, " " for phrase (like Google)
-- to_tsquery: manual control ('wireless & headphones & !wired')

-- Highlight matching terms (useful for search UI):
SELECT ts_headline(
  'english',
  description,
  plainto_tsquery('english', 'wireless headphones'),
  'StartSel=<b>, StopSel=</b>, MaxWords=30'
) FROM products WHERE id = 1;

-- Fuzzy matching via pg_trgm extension (typo tolerance):
CREATE EXTENSION pg_trgm;
CREATE INDEX products_trgm_idx ON products USING GIN(title gin_trgm_ops);

-- Find titles with similarity > 0.3 to "headphons" (typo):
SELECT title, similarity(title, 'headphons')
FROM products
WHERE title % 'headphons'
ORDER BY similarity DESC;
-- Note: pg_trgm + GIN is a SEPARATE index from tsvector + GIN
--       Two indexes, two maintenance costs
```

### Elasticsearch Capabilities Map

```
Elasticsearch additional capabilities over PostgreSQL FTS:
┌─────────────────────────────────────────────────────────────────────────┐
│ RELEVANCE TUNING                                                         │
│   Field boosting: title^3, description^1.0, brand^2.0                  │
│   BM25 parameter tuning: k1 (TF saturation), b (length norm)           │
│   Function score: boost by popularity, recency, revenue                │
│                                                                         │
│ FUZZY MATCHING (native, no extra index)                                 │
│   "headphons" → "headphones" via Levenshtein distance                  │
│   fuzziness: AUTO (0 edit for len<3, 1 for len 3-5, 2 for len>5)      │
│                                                                         │
│ AGGREGATIONS (faceted search in one query)                              │
│   GET /products/_search                                                 │
│   { "query": { "match": {"title": "wireless"} },                       │
│     "aggs": {                                                           │
│       "categories": { "terms": { "field": "category" } },              │
│       "price_range": { "histogram": { "field": "price", "interval": 50}}│
│     }                                                                   │
│   }                                                                     │
│   Returns: top 10 results + count per category + price histogram        │
│            IN ONE QUERY. PostgreSQL would need N+1 GROUP BY queries.   │
│                                                                         │
│ AUTOCOMPLETE / SUGGESTIONS                                              │
│   completion suggester: "wirel" → ["wireless headphones", "wireless    │
│                                     charger", "wireless keyboard"]      │
│   search_as_you_type field type: optimized for real-time search UI     │
│                                                                         │
│ VECTOR/SEMANTIC SEARCH                                                  │
│   dense_vector field with HNSW index                                   │
│   kNN search + hybrid BM25 + vector with RRF fusion                    │
│   (see BM25_vs_Vector_Search_Semantic_Similarity.md)                   │
│                                                                         │
│ HORIZONTAL SCALING                                                      │
│   Shards: split index across nodes (1B docs across 10 shards = fine)  │
│   Replicas: N copies for read throughput + fault tolerance              │
│   Add nodes to cluster: rebalances shards automatically                │
│                                                                         │
│ NEAR REAL-TIME                                                          │
│   New documents searchable within 1 second (configurable)              │
│   refresh_interval: 1s (default) → can set to 30s for bulk indexing   │
└─────────────────────────────────────────────────────────────────────────┘

Elasticsearch limitations vs PostgreSQL:
  ❌ No ACID transactions
  ❌ Eventual consistency on writes (1s refresh delay)
  ❌ No foreign key constraints
  ❌ Data duplication (search index = copy of data from PG)
  ❌ Separate cluster to operate, monitor, tune
  ❌ Schema changes (mappings) require reindex
```

### Scale Comparison: Measured Performance

```
┌────────────────────┬────────────────────────┬────────────────────────────┐
│ Dimension          │ PostgreSQL FTS          │ Elasticsearch              │
├────────────────────┼────────────────────────┼────────────────────────────┤
│ Sweet spot         │ < 10M documents         │ 10M → 1B+ documents        │
│                    │                         │                            │
│ Query latency      │ 10-100ms at 10M rows    │ < 10ms at 100M docs        │
│ (simple search)    │ 1-5s at 100M rows       │ < 50ms at 1B docs          │
│                    │                         │                            │
│ Concurrent users   │ Up to ~1K QPS           │ Up to 100K+ QPS per shard  │
│                    │ (shared with OLTP!)     │ (dedicated read cluster)   │
│                    │                         │                            │
│ Faceted search     │ N GROUP BY queries      │ 1 query with aggregations  │
│ (category+price)   │ 200-500ms per query     │ 10-30ms single query       │
│                    │                         │                            │
│ Fuzzy matching     │ pg_trgm: functional     │ Native: 2-5x faster        │
│                    │ but slower at scale     │ at high concurrency        │
│                    │                         │                            │
│ Operational cost   │ Zero extra (have PG)    │ Managed: ~$500-2000/mo     │
│                    │                         │ (3-node cluster on AWS ES) │
│                    │                         │                            │
│ Write consistency  │ ACID                    │ Eventual (1s default)      │
│                    │ Immediately consistent  │ Visible after refresh      │
│                    │                         │                            │
│ Relevance tuning   │ ts_rank (limited)       │ Full BM25 + field boost    │
│                    │ ts_rank_cd for coverage │ + function_score           │
│                    │                         │                            │
│ Vector search      │ pgvector extension      │ Native HNSW                │
│                    │ Good for < 1M vectors   │ Better at scale > 1M       │
└────────────────────┴────────────────────────┴────────────────────────────┘
```

### The Dual-Write Architecture (Most Common Production Pattern)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    Production Architecture                               │
│                                                                          │
│   API Service                                                            │
│       │                                                                  │
│       ├── WRITE ──────────→ PostgreSQL (source of truth)                │
│       │                         │                                        │
│       │                     [Debezium CDC]                               │
│       │                         │ captures WAL changes                  │
│       │                         ↓                                        │
│       │                      Kafka topic                                 │
│       │                    ("product-changes")                           │
│       │                         │                                        │
│       │                  [ES Indexing Service]                           │
│       │                         │ transforms + indexes                  │
│       │                         ↓                                        │
│       └── SEARCH ─────────→ Elasticsearch (search index)                │
│                                                                          │
│   Flow:                                                                  │
│     1. Product update → PostgreSQL (ACID, immediate)                    │
│     2. Debezium reads PostgreSQL WAL (Write-Ahead Log)                  │
│     3. Change event published to Kafka ("product-changes" topic)        │
│     4. ES Indexer consumes event, generates embedding (if hybrid search)│
│     5. ES Indexer updates document in Elasticsearch                     │
│     6. Document searchable after next refresh (1s default)              │
│                                                                          │
│   Failure scenarios:                                                     │
│     ES down: writes still succeed to PG. ES catches up on restart.     │
│     Kafka lag: ES is temporarily stale (minutes). PG is current.        │
│     ES corrupt index: full reindex from PG (source of truth).           │
└──────────────────────────────────────────────────────────────────────────┘

Debezium connector configuration (PostgreSQL → Kafka):
{
  "name": "products-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres-primary",
    "database.port": "5432",
    "database.user": "debezium",
    "database.dbname": "ecommerce",
    "database.server.name": "ecommerce",
    "table.include.list": "public.products",
    "plugin.name": "pgoutput",
    "publication.name": "debezium_publication",
    "topic.prefix": "ecommerce"
  }
}
```

---

## PART 3 — DECISION CRITERIA AND MIGRATION PATH

### When PostgreSQL FTS Is Sufficient

```sql
-- Scenario: Internal tool search, blog search, support ticket search
-- Typical scale: 100K - 5M documents, < 100 QPS search

-- PostgreSQL FTS checklist:
-- ✅ Document count < 10M
-- ✅ No faceted search requirement (or only 1-2 simple filters)
-- ✅ Simple relevance ranking (rank by match quality, maybe recency)
-- ✅ English language or supported dictionary
-- ✅ Team has no Elasticsearch expertise
-- ✅ Want to minimize infrastructure (no extra cluster)
-- ✅ Data must be immediately consistent on writes

-- Example: Blog search with ts_rank + recency boost
SELECT
  id, title, published_at,
  ts_rank(search_vector, query) * (1 + EXTRACT(YEAR FROM published_at) - 2020) / 5 AS score
FROM
  posts,
  plainto_tsquery('english', 'kubernetes deployment strategy') query
WHERE
  search_vector @@ query
ORDER BY score DESC
LIMIT 10;
-- Works perfectly at 500K blog posts. Zero extra infrastructure.

-- Performance at 10M rows with GIN index:
-- Simple search: 15-50ms
-- With pg_trgm fuzzy: 50-200ms
-- With many concurrent search queries: watch for lock contention on GIN
```

### When You Need Elasticsearch

```
Elasticsearch decision checklist:
  ❓ Document count > 10M? → lean ES
  ❓ Need faceted search (filter by N attributes in one query)? → ES
  ❓ Need autocomplete (search-as-you-type)? → ES
  ❓ Need relevance tuning (boost by popularity/freshness/margin)? → ES
  ❓ Search QPS > 500 (on shared PostgreSQL with OLTP)? → ES
  ❓ Need vector/semantic search at scale (>1M vectors)? → ES
  ❓ Multi-language support (Arabic, Chinese, Japanese stemming)? → ES
  ❓ Need highlights + snippets at scale? → ES

If 3+ boxes checked: Elasticsearch is justified.

Elasticsearch cluster sizing rule of thumb:
  1 shard per 20-50GB of data (ES recommendation)
  50M products × avg 2KB per doc = 100GB
  → 3-5 primary shards
  → 1 replica per shard (fault tolerance)
  → 3-node cluster (1 master + 2 data nodes, or 3 data nodes)

AWS OpenSearch/Elasticsearch managed service:
  r6g.large.search: 2 vCPU, 16GB RAM, ~$180/month per node
  3 nodes: ~$540/month for 50M products
  vs self-hosted on EC2: similar cost + ops overhead
```

### Reindex Strategy (When Migrating From PG to ES)

```python
# Step 1: Bulk initial load from PostgreSQL to Elasticsearch
from elasticsearch import Elasticsearch, helpers
import psycopg2

es = Elasticsearch("https://localhost:9200")
conn = psycopg2.connect(DSN)
cursor = conn.cursor("products_cursor")  # server-side cursor for large tables

def product_docs():
    cursor.execute("SELECT id, title, description, price, category FROM products")
    while True:
        rows = cursor.fetchmany(500)  # stream 500 at a time, not all into RAM
        if not rows:
            break
        for row in rows:
            yield {
                "_index": "products",
                "_id": row[0],
                "_source": {
                    "title": row[1],
                    "description": row[2],
                    "price": row[3],
                    "category": row[4],
                    "title_vector": get_embedding(row[1])  # generate at index time
                }
            }

helpers.bulk(es, product_docs(), chunk_size=500, request_timeout=60)
# At 500 docs/batch, 10ms/batch: 1M docs in ~20 seconds
# With embedding generation: rate-limited by embedding API (~100 docs/sec)

# Step 2: After initial load, start CDC (Debezium) to capture ongoing changes
# Step 3: Cut over search traffic from PG FTS to ES
# Step 4: Monitor ES lag metric, tune refresh_interval if needed
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your e-commerce site has 50 million products. Search must return results in under 100ms with typo tolerance, filtering by category and price range and brand simultaneously, and text relevance ranking. Do you use PostgreSQL full-text search or Elasticsearch?"

**You:** "Elasticsearch. At 50 million products, PostgreSQL FTS can still work, but two specific requirements push it over the edge.

First, **faceted search** — filtering simultaneously by category, price range, and brand while ranking by text relevance. In PostgreSQL, that's a full-text search query combined with GROUP BY on multiple dimensions to get facet counts. Under concurrent load, those GROUP BY queries are expensive. Elasticsearch handles this in a single query using native aggregations — the same query that returns ranked results also returns category counts, price histograms, and top brands. The difference is 200-500ms in PostgreSQL vs 10-30ms in Elasticsearch for faceted search.

Second, **scale under concurrent load**. At 50 million products, the GIN index in PostgreSQL is substantial — probably 5-10GB. Under 500 concurrent search requests, PostgreSQL's GIN scan shows lock contention. Worse, search competes with OLTP queries on the same database. Elasticsearch is an isolated system dedicated to search — it doesn't impact your write latency.

The architecture I'd propose: PostgreSQL as source of truth — all product writes go there, ACID-compliant. Elasticsearch as the search index — read-only from the API's perspective. Change Data Capture via Debezium reads the PostgreSQL Write-Ahead Log and publishes product change events to a Kafka topic. An Elasticsearch indexer service consumes that topic and updates documents in ES. Documents become searchable within 1 second of the PostgreSQL commit.

The risks with this approach: dual-write complexity, sync lag, and the need to support a full reindex when the ES schema changes. For schema changes, I'd use an alias: index to `products_v2` while `products` alias still points to `products_v1`, switch the alias atomically when ready.

The operational cost: a 3-node AWS OpenSearch cluster for 50M products is roughly $500-600/month. For a core revenue-generating feature like product search, that's completely justified."

**Interviewer:** "What if the team has no Elasticsearch experience and this is a startup with 2M products today?"

**You:** "At 2M products: use PostgreSQL FTS. The GIN index at 2M rows is maybe 200-300MB. Query latency: 10-20ms for simple searches. That's well within a 100ms SLA. Add a `tsvector` generated column, GIN index, use `plainto_tsquery` for the search. Add pg_trgm for fuzzy matching. Implement simple faceted filters as WHERE clauses — at 2M rows, a `WHERE category = 'electronics' AND price BETWEEN 50 AND 200` on indexed columns is fast.

The architecture stays simple: one database, one system to operate, consistent by default.

Build in a trigger to migrate when you hit the decision criteria: when you need faceted search counts in real time, when PostgreSQL search latency exceeds 50ms under concurrent load, or when you hit 10M products. At that point, the migration path is well-defined — Debezium CDC to Kafka to Elasticsearch — and you'll have the engineering resources to support it."

---

## PART 5 — DECISION FRAMEWORK

### Decision Flowchart

```
Start: Do you need full-text search?
  └── YES
       │
       ├── How many documents?
       │    ├── < 1M → PostgreSQL FTS. Done.
       │    ├── 1M - 10M → PostgreSQL FTS (monitor query time, plan ES migration)
       │    └── > 10M → lean towards Elasticsearch
       │
       ├── Do you need faceted search (aggregations on search results)?
       │    ├── NO → PostgreSQL FTS may still work
       │    └── YES → Elasticsearch (native aggregations)
       │
       ├── Do you need sub-10ms latency at scale?
       │    ├── NO (50-100ms acceptable) → PostgreSQL FTS
       │    └── YES → Elasticsearch
       │
       ├── Do you need semantic / vector search?
       │    ├── NO → PostgreSQL FTS or ES (BM25 only)
       │    └── YES + < 1M vectors → pgvector extension
       │         YES + > 1M vectors → Elasticsearch (native HNSW)
       │
       └── Do you have Elasticsearch operational experience?
            ├── NO + scale allows → PostgreSQL FTS
            └── YES or managed service available → Elasticsearch
```

### PostgreSQL FTS vs Elasticsearch Feature Comparison

```
┌──────────────────────────┬──────────────────┬────────────────────────────┐
│ Feature                  │ PostgreSQL FTS   │ Elasticsearch              │
├──────────────────────────┼──────────────────┼────────────────────────────┤
│ Basic full-text search   │ ✅ Native         │ ✅ Native                   │
│ Stemming (English)       │ ✅ Built-in       │ ✅ Built-in                 │
│ Stop words               │ ✅ Built-in       │ ✅ Built-in                 │
│ Relevance ranking        │ ✅ ts_rank        │ ✅ BM25 + field boosting    │
│ Phrase search            │ ✅ phraseto_tsq   │ ✅ match_phrase             │
│ Fuzzy/typo tolerance     │ ⚠️ pg_trgm ext   │ ✅ Native fuzziness         │
│ Faceted search           │ ❌ Separate query │ ✅ Aggregations in 1 query  │
│ Autocomplete             │ ❌ Complex        │ ✅ completion suggester      │
│ Highlighted snippets     │ ✅ ts_headline    │ ✅ Highlight API            │
│ Vector/semantic search   │ ⚠️ pgvector ext  │ ✅ Native HNSW              │
│ Multi-language           │ ⚠️ Limited        │ ✅ Many language analyzers  │
│ Horizontal scale         │ ❌ Vertical only  │ ✅ Add shards / nodes       │
│ ACID consistency         │ ✅ Always         │ ❌ Eventual (1s default)    │
│ Operational complexity   │ ✅ Zero extra     │ ❌ Cluster to manage        │
│ Cost                     │ ✅ Free (have PG) │ ❌ $500+/month for cluster  │
└──────────────────────────┴──────────────────┴────────────────────────────┘
```

---

## QUICK REFERENCE CARD

```
POSTGRESQL FTS SETUP (production-ready):
  -- tsvector column (auto-updated on row change)
  ADD COLUMN search_vec tsvector
    GENERATED ALWAYS AS (
      to_tsvector('english', coalesce(title,'') || ' ' || coalesce(body,''))
    ) STORED;
  
  CREATE INDEX idx_fts ON table USING GIN(search_vec);
  
  -- Search with ranking
  SELECT id, ts_rank(search_vec, q) as rank
  FROM table, websearch_to_tsquery('english', :query) q
  WHERE search_vec @@ q
  ORDER BY rank DESC LIMIT 10;

  -- Fuzzy (add separately)
  CREATE EXTENSION pg_trgm;
  CREATE INDEX idx_trgm ON table USING GIN(title gin_trgm_ops);
  WHERE title % 'serach_term' ORDER BY similarity(title, 'serach_term') DESC;

ELASTICSEARCH HYBRID SEARCH SKELETON:
  POST /products/_search
  {
    "query": {
      "bool": {
        "should": [
          {"match": {"title": {"query": ":q", "boost": 1.0}}},
          {"match": {"description": {"query": ":q", "boost": 0.5}}}
        ],
        "filter": [
          {"range": {"price": {"gte": 50, "lte": 200}}},
          {"term": {"category": "electronics"}}
        ]
      }
    },
    "aggs": {
      "by_category": {"terms": {"field": "category"}},
      "price_histogram": {"histogram": {"field": "price", "interval": 50}}
    },
    "size": 10
  }

CDC SYNC (Debezium → Kafka → ES):
  PG WAL → Debezium connector → Kafka topic → ES indexer consumer → ES index
  Lag: typically 1-3 seconds (configurable, lower with small refresh_interval)

ELASTICSEARCH SHARD SIZING:
  target shard size: 20-50GB
  primary shards = ceil(total_data_size_GB / 40)
  replicas: 1 (fault tolerance) or 2 (read throughput)
  example: 100GB data → 3 primary shards × 1 replica = 6 shards total
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

```
┌──────┬─────────────────────┬────────────────────────────────────────────────────────────────┐
│  #   │ System              │ Search Architecture                                            │
├──────┼─────────────────────┼────────────────────────────────────────────────────────────────┤
│  09  │ E-Commerce          │ PostgreSQL = source of truth. Elasticsearch = product search   │
│      │                     │ index. Debezium CDC via Kafka for sync. ES handles facets,     │
│      │                     │ typo tolerance, semantic search (dense_vector + HNSW).         │
├──────┼─────────────────────┼────────────────────────────────────────────────────────────────┤
│  14  │ Proximity Search    │ PostGIS for pure geo queries (nearest N restaurants within     │
│      │                     │ radius). Elasticsearch for combined text + geo: "Italian       │
│      │                     │ restaurants nearby" uses geo_distance filter + match on        │
│      │                     │ cuisine field in a single ES query.                            │
├──────┼─────────────────────┼────────────────────────────────────────────────────────────────┤
│  20  │ Email (Gmail-scale) │ PostgreSQL stores email metadata (sender, subject, dates) —   │
│      │                     │ ACID, FK integrity. Elasticsearch indexes email body for       │
│      │                     │ full-text search. At Gmail scale (50B+ emails), only ES        │
│      │                     │ handles query volume across that corpus size.                  │
├──────┼─────────────────────┼────────────────────────────────────────────────────────────────┤
│  All │ Internal tools,     │ PostgreSQL FTS is the correct default for internal tools,     │
│      │ < 5M docs           │ admin search, content CMS under 5M docs. No justification     │
│      │                     │ for ES operational overhead at that scale.                    │
└──────┴─────────────────────┴────────────────────────────────────────────────────────────────┘
```

---

> **Architect's one-liner:** "Use PostgreSQL full-text search up to 10M documents with simple ranking; add Elasticsearch when you need faceted search, sub-10ms at scale, or semantic search — but sync it from PostgreSQL via CDC, not as the source of truth."
