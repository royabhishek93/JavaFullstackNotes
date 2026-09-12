# Elasticsearch vs PostgreSQL Full-Text Search — LinkedIn Post

## Post Text (copy-paste ready)

Faceted search: 200-500ms in PostgreSQL vs 10-30ms in Elasticsearch. Same query.

- Under ~10M documents? PostgreSQL FTS (tsvector + GIN) is enough — zero extra infra.
- Faceted search (category + price + brand): Elasticsearch does it in 1 query with aggregations; Postgres needs N separate GROUP BY queries.
- Typo tolerance: pg_trgm works but slows down at scale; Elasticsearch fuzziness is native and 2-5x faster under concurrency.
- ACID vs eventual consistency: Postgres writes are immediately consistent; ES documents go live after a ~1s refresh.
- At scale, don't replace Postgres — sync it: Debezium reads the WAL → Kafka → ES indexer keeps the search index in sync.

Swipe → to see the decision flowchart + the 50M-product vs 2M-product interview answer.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Postgres full-text search works great — until it doesn't. 50M products = Elasticsearch. 2M products = Postgres. Here's the exact line. 🔍

### Variant B — Long (400–600 chars)
"Do we really need Elasticsearch if we already have Postgres?" I get this question constantly.

Short answer: under 10M documents, no. PostgreSQL's tsvector + GIN index handles ranking, stemming, and fuzzy search (pg_trgm) just fine — for free.

But at 50M products with faceted search (category + price + brand), Postgres needs N GROUP BY queries at 200-500ms each. Elasticsearch answers the same query with aggregations in 10-30ms.

The right architecture isn't "replace Postgres" — it's Postgres as source of truth, Elasticsearch as a synced search index via Debezium CDC → Kafka. Cost for a 50M-product cluster: ~$500-600/month.

Full breakdown + decision checklist in the carousel.

---

## Best Time to Post
Tuesday–Thursday, 8–10 AM in your primary audience's timezone (engineers scrolling before/at the start of the workday tend to drive the highest engagement on technical carousels).

## Engagement Hook
End the caption with a direct question in the comments: "At what document count did YOU switch from Postgres to Elasticsearch — or are you still holding out?" This invites war-story replies from engineers who've hit the migration point themselves.
