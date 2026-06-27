# HIGH Q01 - Scale Search for 100M Documents

## Scenario
Search must serve 100M documents with low latency and high availability.

## Design
- Shard index by tenant/domain or hash.
- Use replicas for query scale.
- Separate autocomplete index from main full-text index.
- Cache hot queries and facets.
- Keep indexing asynchronous with lag monitoring.

## Bottlenecks
- Deep pagination
- Expensive aggregations/facets
- Skewed shard distribution

## Interview One-Liner
At scale, search performance is as much about shard economics as query design.
