# MED Q03 - Hot Key From One Abusive Tenant

## Scenario
One tenant sends 1M requests/minute to one endpoint, making one Redis key extremely hot.

## Mitigations
- Hash-split the tenant across multiple subkeys when approximation is acceptable.
- Pre-filter using local leaky bucket at app node.
- Move abusive tenant to isolated rate-limiter shard.
- Apply circuit breaker or temporary hard block.

## Interview One-Liner
Hot keys are a scaling problem caused by success of a single dimension in the key model.
