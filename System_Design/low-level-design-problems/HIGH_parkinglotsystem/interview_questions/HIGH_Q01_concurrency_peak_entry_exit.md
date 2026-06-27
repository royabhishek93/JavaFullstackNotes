# HIGH Q01 - Peak Concurrency at Entry and Exit

## Scenario
Morning rush: 20,000 vehicles/hour across multiple lots.

## Design
- Partition data by lot_id and floor_id.
- Keep per-type free counters in cache.
- Use DB conditional update for final slot claim.
- Async events for occupancy broadcasts.
- Batch metrics ingestion for analytics.

## Key Bottleneck
Hot rows on popular floors. Mitigate with floor-level sharding and randomization among top N candidate slots.

## Interview One-Liner
Cache guides selection, DB confirms truth.
