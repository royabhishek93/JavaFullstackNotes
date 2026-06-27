# HIGH Q01 - Scale Matching for City-Wide Peak Traffic

## Scenario
Rain starts in a metro city. Demand spikes 10x in 5 minutes.

## Design
- Partition driver location streams by city/grid.
- Keep nearby-driver cache by geo cell.
- Use async offer fan-out with short expiry.
- Rate limit rider retries.
- Apply surge pricing based on supply-demand ratio.

## Bottlenecks
- Geo queries
- Notification fan-out to drivers
- Hotspot zones causing repeated candidate overlap

## Interview One-Liner
Search can be approximate and cached, but final assignment must still be transactionally guarded.
