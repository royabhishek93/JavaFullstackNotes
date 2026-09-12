# Inverted Index: How Elasticsearch Works — LinkedIn Post

## Post Text (copy-paste ready)

SQL LIKE '%running shoes%' across 50M rows: minutes, zero relevance ranking. Elasticsearch: <100ms, ranked. Here's why.

- An inverted index maps WORD → documents (not document → words) — search becomes a lookup on a pre-built posting list, not a table scan
- SQL's LIKE with a leading wildcard can't use a B-tree index at all — forces a full scan every time
- BM25 scoring ranks by both term frequency AND rarity — "Gore-Tex running shoes" outranks generic "blue shoes" for a "Gore-Tex" search because rare terms carry more weight
- The #1 mapping mistake: using `text` (analyzed) for a field you need to facet/filter by — "Nike" becomes "nike" and breaks exact grouping. Fix: map it both ways with `brand.keyword`
- Put binary conditions (price < 200, in_stock: true) in the `filter` clause, not `must` — filters are cached and skip scoring entirely, essentially free on repeat queries

Swipe → to see the full tokenize→normalize→stem pipeline and the exact query structure (must vs filter) that keeps searches under 100ms at scale.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
SQL LIKE takes minutes on 50M rows. Elasticsearch does it in <100ms, ranked. Here's the data structure that makes it possible 👇

### Variant B — Long (400–600 chars)
An inverted index flips the normal document structure — instead of document-to-words, it's word-to-documents, stored as sorted posting lists. Search becomes a fast lookup, not a scan, and BM25 scoring ranks results by term frequency weighted against how rare that term is across the whole index. The most common mistake: mapping a field as analyzed `text` when you actually need exact `keyword` matching for filters and facets — fix it with a multi-field mapping instead of picking just one.

---

## Best Time to Post
Friday, 9:00–10:00 AM IST (closes the technical series week, strong save rate on reference-card content)

## Engagement Hook
"What's the largest dataset you've had to add full-text search to — and did Postgres or Elasticsearch win?"
