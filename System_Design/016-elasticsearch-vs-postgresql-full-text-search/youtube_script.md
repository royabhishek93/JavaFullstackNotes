# Elasticsearch vs PostgreSQL Full-Text Search — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 16 of 29

## HOOK (0:00–0:30)

[Screen cue: Title card — "Elasticsearch vs PostgreSQL: Do You Actually Need a Search Cluster?"]

Your team just shipped product search, and someone in standup says: "We should add Elasticsearch." Nobody asks why. It just... happens. Six weeks later you're running a 3-node cluster, paying $500 a month, and debugging index lag at 2 AM — for a catalog with 200,000 products that PostgreSQL could've handled in its sleep.

Here's the thing — Elasticsearch is not "the professional way to do search." It's a specific tool for a specific scale. And today I'm going to show you exactly where the line is, with real numbers, so you stop guessing.

## THE PROBLEM (0:30–2:00)

[Screen cue: Split diagram — "Notebook" vs "Google Search Appliance"]

Let's start with an analogy, because this is the mental model that actually sticks.

Think of PostgreSQL full-text search as adding a searchable index to a notebook you already own. Your notebook — PostgreSQL — is already great at storing and retrieving structured data. Bolt on a `tsvector` column with a GIN index, and now you've got solid keyword search: stemming, ranking, stop words, all built in. It's fast enough for millions of rows, and — here's the key part — you already have the notebook. Zero extra infrastructure.

Elasticsearch, on the other hand, is a search engine first and a storage system second. It's like plugging in a dedicated, Google-quality search appliance next to your notebook. It's purpose-built: distributed by design, optimized for text analysis, and it natively handles things like faceted search — filtering by category AND price AND brand in one query — typo tolerance, autocomplete, even vector search. It can answer queries across a billion documents in under 10 milliseconds.

But — and this is the part everyone skips — it's a separate system. You have to deploy it, operate it, keep it in sync with your PostgreSQL source of truth, and pay for the infrastructure every single month.

So the real question is never "which one is better." It's: does my use case actually justify the added complexity? A product catalog with 500K items and basic search? PostgreSQL full-text search is completely sufficient. An e-commerce platform with 50 million products, faceted search, typo tolerance, and semantic search? Now you're in Elasticsearch territory.

And the pattern almost every large system converges on isn't "pick one" — it's PostgreSQL as the source of truth for ACID writes, and Elasticsearch as the search index for fast reads, running in parallel, synced through Change Data Capture. Let's build both sides.

## THE SOLUTION (2:00–5:00)

[Screen cue: Code — ALTER TABLE with GENERATED ALWAYS AS tsvector]

Start with PostgreSQL. Step one: add a generated `tsvector` column.

```sql
ALTER TABLE products
ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    to_tsvector('english',
      coalesce(title, '')
      || ' ' || coalesce(description, '')
      || ' ' || coalesce(brand, '')
    )
  ) STORED;
```

Two things to notice. `STORED` means this is computed once, on insert or update, and stored on disk — no runtime cost at query time. And `to_tsvector('english', ...)` applies the English dictionary, which gives you stemming and stop-word removal for free.

[Screen cue: Code — CREATE INDEX ... USING GIN]

Step two, build a GIN index — a Generalized Inverted Index — on that column:

```sql
CREATE INDEX products_search_gin_idx ON products USING GIN(search_vector);
```

Build time is roughly 10 minutes for 10 million rows, about 100 minutes for 100 million. Index size lands around 30 to 40% of your original text column size.

[Screen cue: Code — SELECT ... ts_rank ... plainto_tsquery]

Step three, query it with ranking:

```sql
SELECT id, title, ts_rank(search_vector, query) AS rank
FROM products, plainto_tsquery('english', 'wireless headphones') query
WHERE search_vector @@ query
ORDER BY rank DESC LIMIT 10;
```

Now, PostgreSQL gives you three flavors of query parsing, and picking the wrong one is a common bug. `plainto_tsquery` treats your input as separate words and ANDs them together — all must match. `phraseto_tsquery` requires the words to be adjacent, so "red apple" won't match "apple red." And `websearch_to_tsquery` is the one you actually want for a user-facing search box — it supports a minus sign to exclude terms and quotes for exact phrases, just like Google.

Want highlighted snippets in your search UI? `ts_headline` does that natively:

```sql
SELECT ts_headline('english', description,
  plainto_tsquery('english', 'wireless headphones'),
  'StartSel=<b>, StopSel=</b>, MaxWords=30') FROM products WHERE id = 1;
```

And for typo tolerance — someone searches "headphons" — you bring in the `pg_trgm` extension:

```sql
CREATE EXTENSION pg_trgm;
CREATE INDEX products_trgm_idx ON products USING GIN(title gin_trgm_ops);

SELECT title, similarity(title, 'headphons')
FROM products WHERE title % 'headphons'
ORDER BY similarity DESC;
```

Important catch here: this is a completely separate index from your tsvector GIN index. Two indexes, two maintenance costs. Keep that in your mental ledger.

[Screen cue: Diagram — Elasticsearch capability map: boosting, BM25, aggregations, autocomplete, vector search]

Now flip to Elasticsearch. Everything here is stuff PostgreSQL either can't do natively or does slowly.

Field boosting lets you weight `title^3` over `description^1.0` — tell the engine title matches matter three times more. Under the hood it's using BM25 for relevance scoring, with tunable parameters for term-frequency saturation and length normalization.

Fuzzy matching is native — no separate index required. Set `fuzziness: AUTO` and Elasticsearch automatically allows zero edits for short words, one edit for words 3-5 characters, two edits for anything longer. "Headphons" becomes "headphones" automatically.

Then there's aggregations — this is the single biggest reason teams reach for Elasticsearch. One query, like this:

```
GET /products/_search
{ "query": { "match": {"title": "wireless"} },
  "aggs": {
    "categories": { "terms": { "field": "category" } },
    "price_range": { "histogram": { "field": "price", "interval": 50 } }
  }
}
```

That single call returns your top 10 ranked results, a count per category, AND a price histogram — all in one round trip. In PostgreSQL, that's N separate GROUP BY queries.

Autocomplete comes from the completion suggester — type "wirel" and get back "wireless headphones," "wireless charger," "wireless keyboard" in milliseconds. For semantic search, you get a `dense_vector` field backed by an HNSW index, so you can do kNN vector search, or fuse it with BM25 for hybrid search.

And horizontally, Elasticsearch scales by sharding — split an index across nodes, add replicas for read throughput and fault tolerance, and it rebalances automatically when you add nodes. Documents become searchable within about 1 second by default — that's the "near real-time" refresh interval, and you can tune it down to 30 seconds if you're doing bulk indexing and don't need instant visibility.

The tradeoff column matters just as much: no ACID transactions, eventual consistency on writes, no foreign keys, your data is now duplicated between PG and ES, you've got a cluster to operate, and schema changes mean a reindex. Keep that list in your head — we're about to see exactly when those tradeoffs are worth it.

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

[Screen cue: Table — the full scale comparison, side by side]

Here's where most engineers get the decision wrong: they look at Elasticsearch's ceiling instead of their own floor. Let's look at actual numbers.

Query latency: PostgreSQL FTS is 10 to 100 milliseconds at 10 million rows, but that degrades to 1 to 5 seconds at 100 million rows. Elasticsearch stays under 10 milliseconds at 100 million docs, and under 50 milliseconds even at a billion.

Faceted search — category plus price plus brand — is the sharpest contrast. PostgreSQL: N separate GROUP BY queries, 200 to 500 milliseconds. Elasticsearch: one query with native aggregations, 10 to 30 milliseconds. That's not a small optimization, that's an order of magnitude, and it's the single most common reason teams migrate.

Cost: PostgreSQL FTS is zero extra — you already have the database. Elasticsearch managed service runs $500 to $2000 a month for a 3-node cluster on AWS. That's a real recurring line item you have to justify to your team, every month, forever.

And consistency: PostgreSQL is ACID, immediately consistent. Elasticsearch is eventually consistent — a 1-second refresh window by default. If your product just got a stock update and someone searches within that window, they might see stale availability. That's a real product decision, not just an engineering one.

[Screen cue: Architecture diagram — API → PostgreSQL (WAL) → Debezium → Kafka → ES Indexer → Elasticsearch]

So if you do need Elasticsearch, how do you actually run two systems without them drifting apart? The answer almost everyone converges on is Change Data Capture — specifically Debezium plus Kafka.

The flow: a product update hits the API, gets written to PostgreSQL — ACID, immediate. Debezium reads PostgreSQL's Write-Ahead Log, the WAL, and captures that change. It publishes a change event to a Kafka topic — call it "product-changes." An ES indexer service consumes that event, transforms it — maybe generates an embedding if you're doing hybrid search — and updates the document in Elasticsearch. The document becomes searchable after the next refresh, typically within a second.

Now — what happens when things break, because they will. If Elasticsearch goes down, writes still succeed to PostgreSQL, no data loss, and ES catches up once it's back online reading from Kafka. If Kafka lags, Elasticsearch just gets temporarily stale — minutes behind — but PostgreSQL stays current and correct. And if the ES index gets corrupted, you do a full reindex from PostgreSQL, because Postgres is always your source of truth. This is exactly why PostgreSQL owning the writes matters — Elasticsearch can fail, restart, even get rebuilt from scratch, and you never lose a write.

[Screen cue: Decision checklist / flowchart on screen]

So here's the actual decision checklist, and I want you to run your own system through this before writing a single line of ES config:

Document count over 10 million? Lean Elasticsearch. Under that, PostgreSQL FTS is fine. Do you need faceted search — filtering by multiple attributes with live counts? That alone justifies ES. Do you need sub-10-millisecond latency at scale, not just "acceptable," but sub-10? That's ES. Do you need vector or semantic search over more than a million vectors? ES with native HNSW — under a million, `pgvector` extension handles it fine inside Postgres. And critically — does your team have operational experience running a search cluster, or access to a managed service? If the answer is no and your scale doesn't force the issue, stay on PostgreSQL.

If you check three or more of those boxes, Elasticsearch is justified. If you check one or zero, you're about to build infrastructure you don't need.

## REAL WORLD (8:00–9:30)

[Screen cue: "The Interview" — 50M products scenario]

Let's put this in an actual interview frame, because this is exactly how it gets asked. "Your e-commerce site has 50 million products. Search must return results under 100 milliseconds, with typo tolerance, filtering by category, price, and brand simultaneously, plus relevance ranking. PostgreSQL or Elasticsearch?"

The strong answer: Elasticsearch — and here's why, with the two specific things that push it over the edge. First, faceted search. Filtering by category, price range, and brand while ranking by relevance means, in PostgreSQL, a full-text query combined with GROUP BY across multiple dimensions — expensive under concurrent load. Elasticsearch does the whole thing in one query using native aggregations. The measured difference: 200 to 500 milliseconds in PostgreSQL versus 10 to 30 milliseconds in Elasticsearch. Second, scale under concurrent load — at 50 million products your GIN index is 5 to 10 gigabytes, and at 500 concurrent searches you start seeing lock contention, plus search now competes with your OLTP writes on the same database. Elasticsearch is an isolated system — it never touches your write latency.

The architecture: PostgreSQL as source of truth for all writes, Elasticsearch as the read-only search index, synced via Debezium CDC through Kafka, documents searchable within a second of the PostgreSQL commit. Cost for that 3-node cluster at 50 million products: roughly $500 to $600 a month. For a core revenue-generating feature — product search on a marketplace the size of a Flipkart or a Myntra — that's an easy justification. Same logic applies to a food delivery search experience at Swiggy or Zomato scale, where facets like cuisine, price, and delivery time all need to combine in one fast query.

[Screen cue: Counter-example — 2M product startup]

But here's the follow-up that trips people up: "What if this is a startup, 2 million products, and the team has zero Elasticsearch experience?"

The strong answer flips completely: use PostgreSQL FTS. At 2 million rows, the GIN index is maybe 200 to 300 megabytes. Query latency is 10 to 20 milliseconds for simple searches — comfortably inside a 100ms SLA. Add the generated `tsvector` column, GIN index, `plainto_tsquery` for search, `pg_trgm` for fuzzy matching, and implement facets as plain WHERE clauses — `WHERE category = 'electronics' AND price BETWEEN 50 AND 200` on indexed columns is fast at this scale. One database, one system to operate, consistent by default.

And you build in a trigger to know when to migrate: real-time faceted counts become a hard requirement, PostgreSQL search latency crosses 50 milliseconds under load, or you cross 10 million products. At that point the migration path — Debezium, Kafka, Elasticsearch — is well understood, and by then you'll have the resources to run it properly.

## OUTRO + NEXT EPISODE (9:30–10:00)

[Screen cue: Recap card — "PostgreSQL FTS < 10M docs. ES for facets, sub-10ms, or vector search at scale — synced via CDC, never as source of truth."]

So the one-liner to remember: use PostgreSQL full-text search up to about 10 million documents with simple ranking. Add Elasticsearch when you need faceted search, sub-10-millisecond latency at scale, or semantic search — but always sync it from PostgreSQL via CDC. Never let it become your source of truth.

If this saved you from provisioning a cluster you didn't need — or convinced you that you actually do need one — drop a comment with your document count, I'm curious where everyone's systems actually sit on this line.

[Screen cue: Next episode teaser — "017: Cursor Pagination vs Offset Pagination"]

Next episode, we're tackling pagination — cursor-based versus offset-based — and why that "LIMIT / OFFSET" query that works fine at page 2 completely falls apart at page 10,000. See you there.
