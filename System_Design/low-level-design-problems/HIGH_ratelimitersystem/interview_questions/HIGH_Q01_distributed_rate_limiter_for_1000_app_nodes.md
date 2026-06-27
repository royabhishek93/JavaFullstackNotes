# HIGH Q01 - Distributed Rate Limiter for 1000 App Nodes

## Scenario
1000 application nodes must enforce a shared limit of 10k requests/minute per tenant.

## Design
- Store counters in Redis cluster.
- Use Lua script for atomic check-and-increment.
- Cache policy locally.
- Return standard headers: limit, remaining, reset.
- Use async metrics pipeline for denied events.

## Key Trade-off
Centralized correctness vs added network hop latency.

## Interview One-Liner
Distributed enforcement needs a shared source of truth; otherwise each node only enforces a fraction of the real limit.
