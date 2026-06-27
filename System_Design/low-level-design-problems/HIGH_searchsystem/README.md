# Search System (LLD)

This folder follows the same structure and interview style as HIGH_movieticketbookingsystem.

## Files
- `search-system.md` - End-to-end low-level design
- `DATABASE_SCHEMA_VISUAL.md` - Schema and entity relationships
- `INTERVIEW_APPROACH.md` - How to present the system in interviews
- `interview_questions/` - Scenario-based Q and A

## Scope
- Full-text search, autocomplete, filters, ranking, and pagination
- Indexing pipeline and denormalized search documents
- Query path vs indexing path separation
- Relevance tuning, typo tolerance, and caching
- Operational concerns like reindexing and eventual consistency

## One-line pitch
A production search system separates source-of-truth writes from optimized read indexes, then tunes ranking, latency, and freshness independently.
