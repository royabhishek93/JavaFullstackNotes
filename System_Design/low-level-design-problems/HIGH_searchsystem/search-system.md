# Designing a Search System (LLD)

## Requirements
1. Support keyword search across documents/products/entities.
2. Support autocomplete and typo tolerance.
3. Support filtering, sorting, and pagination.
4. Return relevant results with ranking.
5. Keep search index near-real-time with source-of-truth updates.
6. Scale query traffic independently from write/index traffic.
7. Support analytics for popular queries and zero-result queries.
8. Support reindexing without downtime.

## Core Components
1. Query API
- Accepts search term, filters, sort, pagination.
- Validates and normalizes query.

2. Ranking Engine
- Computes relevance from BM25/text score + business boosts.

3. Search Index
- Usually Elasticsearch/OpenSearch/Solr.
- Stores denormalized searchable documents.

4. Indexing Pipeline
- Consumes change events from source systems.
- Builds/updates denormalized search documents.

5. Autocomplete Service
- Uses prefix index, edge n-grams, or completion suggester.

6. Analytics Service
- Tracks top queries, abandoned queries, CTR, and zero-result rates.

## Core Entities
1. SearchDocument
- id, entityType, title, description, tags, facets, scoreSignals, updatedAt

2. SearchIndexJob
- id, entityId, entityType, operation, status, retryCount

3. QueryLog
- id, queryText, filters, resultCount, latencyMs, createdAt

4. ClickEvent
- id, queryId, resultId, rankPosition, createdAt

## APIs
- GET /v1/search?q=...&filters=...&page=...
- GET /v1/search/autocomplete?q=...
- POST /v1/search/reindex
- GET /v1/search/analytics/top-queries

## Query Flow
1. Normalize query.
2. Resolve spelling/synonyms.
3. Execute full-text query + filters on search index.
4. Apply ranking boosts and pagination.
5. Return results with facets and metadata.

## Indexing Flow
1. Source-of-truth entity changes.
2. Event emitted to queue.
3. Index worker builds denormalized document.
4. Upsert into search index.
5. Metrics/logging for indexing lag.

## Consistency Model
- Source DB is authoritative.
- Search index is eventually consistent.
- For critical reads, optionally fall back to DB verification.

## Interview One-Liner
Search design is about decoupling write correctness from read relevance and latency.
