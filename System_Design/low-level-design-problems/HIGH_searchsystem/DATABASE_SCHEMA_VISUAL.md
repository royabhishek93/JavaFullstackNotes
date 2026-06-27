# Database Schema Visual Guide - Search System

## Complete ER Diagram

```
┌────────────────────────────────────┐
│        SOURCE_ENTITIES             │
│────────────────────────────────────│
│ PK id (UUID)                       │
│    entity_type                     │
│    title                           │
│    description                     │
│    status                          │
│    updated_at                      │
└──────────────┬─────────────────────┘
               │ indexed into
               ▼
┌────────────────────────────────────┐         ┌────────────────────────────────────┐
│        SEARCH_DOCUMENTS            │         │         SEARCH_INDEX_JOBS          │
│────────────────────────────────────│         │────────────────────────────────────│
│ PK id (UUID)                       │         │ PK id (UUID)                       │
│    entity_id                       │         │    entity_id                       │
│    entity_type                     │         │    entity_type                     │
│    title                           │         │    operation (UPSERT/DELETE)       │
│    body                            │         │    status                          │
│    tags                            │         │    retry_count                     │
│    facets_json                     │         │    created_at                      │
│    score_signals_json              │         │    updated_at                      │
│    indexed_at                      │         └────────────────────────────────────┘
└──────────────┬─────────────────────┘
               │ generates logs for
               ▼
┌────────────────────────────────────┐         ┌────────────────────────────────────┐
│            QUERY_LOGS              │         │            CLICK_EVENTS            │
│────────────────────────────────────│         │────────────────────────────────────│
│ PK id (UUID)                       │         │ PK id (UUID)                       │
│    query_text                      │         │ FK query_id -> query_logs.id       │
│    filters_json                    │         │    result_document_id              │
│    result_count                    │         │    rank_position                   │
│    latency_ms                      │         │    created_at                      │
│    created_at                      │         └────────────────────────────────────┘
└────────────────────────────────────┘
```

## Constraints
- UNIQUE `(entity_type, entity_id)` on `search_documents`
- Index on `query_logs.created_at`
- Index on `search_index_jobs.status, created_at`

## Practical Note
In production, the real searchable index usually lives in Elasticsearch/OpenSearch. The `search_documents` table here is a conceptual representation of the denormalized search model and metadata.
