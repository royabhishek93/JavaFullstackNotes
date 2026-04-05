# Q12: Elasticsearch vs SQL - Why not PostgreSQL LIKE query?

### Comparison:
```
┌────────────────────┬──────────────────┬────────────────────┐
│    Feature         │   PostgreSQL     │   Elasticsearch    │
├────────────────────┼──────────────────┼────────────────────┤
│ Full-text search   │ Basic (tsvector) │ Advanced (Lucene)  │
│ Fuzzy matching     │ No               │ Yes (typo-tolerant)│
│ Geo-spatial        │ PostGIS (complex)│ Built-in           │
│ Faceted search     │ Multiple JOINs   │ Aggregations       │
│ Latency            │ 500ms+           │ <100ms             │
│ Scale              │ Vertical         │ Horizontal         │
└────────────────────┴──────────────────┴────────────────────┘

Use Elasticsearch when:
✅ Full-text search required
✅ Geo-spatial queries
✅ Faceted filters (genre + language + rating)
✅ Sub-200ms latency needed

Use PostgreSQL when:
✅ ACID transactions
✅ Complex joins
✅ Strong consistency
```

---
