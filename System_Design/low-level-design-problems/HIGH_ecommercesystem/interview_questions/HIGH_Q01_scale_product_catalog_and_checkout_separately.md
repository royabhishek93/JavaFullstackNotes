# HIGH Q01 - Scale Catalog and Checkout Separately

## Scenario
System serves 50M product page views/day, but only 500k orders/day.

## Design
- Separate read-heavy catalog path from correctness-heavy checkout path.
- Use search index/cache/CDN for product browsing.
- Keep checkout on transactional DB with strict inventory rules.
- Async replication from source-of-truth catalog DB to search system.

## Interview One-Liner
Browsing optimizes for latency; checkout optimizes for correctness.
