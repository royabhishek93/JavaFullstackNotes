# MED Q01 - Why Not Use PostgreSQL Like a Search Engine?

## Scenario
Interviewer asks: Why not just use SQL LIKE queries on the main database?

## Answer
- Transactional DB is optimized for correctness and normalized writes.
- Search requires stemming, fuzzy matching, ranking, facets, and typo tolerance.
- Complex text queries and high read QPS hurt OLTP workload.
- Search index stores denormalized documents optimized for retrieval.

## Interview One-Liner
A relational DB can do lookup; a search engine is built for relevance.
