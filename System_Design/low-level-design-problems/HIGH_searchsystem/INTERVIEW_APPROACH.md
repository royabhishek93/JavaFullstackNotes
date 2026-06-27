# Interview Approach - Search System LLD

## 1. Start With The Core Idea
"Search is usually not served directly from the transactional database; it needs its own index optimized for retrieval."

## 2. Define Guarantees
- Fast reads with rich filtering
- Eventually consistent indexing
- Stable pagination semantics where possible
- Relevance tuning without changing source-of-truth schema

## 3. Walk Through Query Path
1. Query normalization
2. Search index lookup
3. Ranking + business boosts
4. Facets + pagination
5. Logging and analytics

## 4. Walk Through Indexing Path
1. Source change event
2. Queue
3. Index worker transforms document
4. Upsert into search engine

## 5. Mention Scale Levers
- Shard by tenant/domain
- Separate autocomplete index
- Query cache for hot searches
- Replica scaling for read-heavy traffic

## 6. Trade-offs
- Better relevance often costs more CPU.
- Fresher indexing often costs more write throughput.
- Deep pagination is expensive.

## 7. Close Strongly
"The best search design treats index freshness, query latency, and ranking quality as separate knobs."
