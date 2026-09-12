# Microservices Notes

Interview-prep notes on microservices architecture, distributed systems patterns, and system design — written in plain English with production scenarios, ASCII diagrams, and interview trap/cross-questions.

## Scope
- Inter-service communication & resilience patterns
- Event-driven architecture, saga, outbox, idempotency
- Distributed consistency, CAP theorem, consensus
- Data layer: sharding, scaling, caching, database selection
- Networking fundamentals (OSI, TCP/TLS/HTTP/gRPC)

## Suggested Reading Order

### 1. Foundations
- [19.microservices-vs-monolith.md](19.microservices-vs-monolith.md) — when to split, when not to
- [29.domain-driven-design-bounded-contexts-interview.md](29.domain-driven-design-bounded-contexts-interview.md) — where to draw the boundaries
- [TCP, UPD, TLS, HTTP, HTTPS, WebSocket, gRPC | OSI Layers Explained/README.md](TCP,%20UPD,%20TLS,%20HTTP,%20HTTPS,%20WebSocket,%20gRPC%20%7C%20OSI%20Layers%20Explained/README.md) — networking basics
- [13.cap-theorem-trade-offs.md](13.cap-theorem-trade-offs.md) — consistency vs availability trade-offs

### 2. Resilience & Traffic Control
- [04.bulkhead-backpressure-architect-interview.md](04.bulkhead-backpressure-architect-interview.md)
- [05.load-shedding-springboot-aws-architect-interview.md](05.load-shedding-springboot-aws-architect-interview.md)
- [15.load-balancing-algorithms.md](15.load-balancing-algorithms.md)
- [03.service-mesh-istio-springboot-aws-architect-interview.md](03.service-mesh-istio-springboot-aws-architect-interview.md)
- [23.service-discovery-architect-interview.md](23.service-discovery-architect-interview.md) — how services find healthy instances
- [43.containerization-orchestration-docker-kubernetes-interview.md](43.containerization-orchestration-docker-kubernetes-interview.md) — containers, K8s reconciliation, probes
- [41.configuration-management-spring-cloud-config-vault-interview.md](41.configuration-management-spring-cloud-config-vault-interview.md) — externalized config, Vault, Consul
- [40.blue-green-canary-deployment-interview.md](40.blue-green-canary-deployment-interview.md) — deployment strategies for safe rollout/rollback
- [42.chaos-engineering-interview.md](42.chaos-engineering-interview.md) — proving resilience under real injected failure

### 3. Data Consistency & Transactions
- [01.transactional-outbox-pattern-interview.md](01.transactional-outbox-pattern-interview.md)
- [12.distributed-transactions-saga-vs-2pc.md](12.distributed-transactions-saga-vs-2pc.md)
- [09.leader-election-distributed-systems.md](09.leader-election-distributed-systems.md)
- [27.consensus-raft-paxos-distributed-locks-interview.md](27.consensus-raft-paxos-distributed-locks-interview.md) — how Raft/Paxos/Redlock actually work
- [28.message-delivery-semantics-idempotency-interview.md](28.message-delivery-semantics-idempotency-interview.md) — at-least-once + idempotent consumers
- [25.cqrs-pattern-architect-interview.md](25.cqrs-pattern-architect-interview.md) — splitting read/write models
- [31.event-sourcing-deep-dive-interview.md](31.event-sourcing-deep-dive-interview.md) — event store, snapshotting, event versioning
- [36.clock-synchronization-lamport-timestamps-interview.md](36.clock-synchronization-lamport-timestamps-interview.md) — NTP skew, Lamport timestamps, TrueTime
- [34.conflict-resolution-vector-clocks-crdt-interview.md](34.conflict-resolution-vector-clocks-crdt-interview.md) — LWW, vector clocks, CRDTs

### 4. Data Layer
- [16.database-scaling.md](16.database-scaling.md)
- [14.database-sharding-strategies.md](14.database-sharding-strategies.md)
- [20.caching-strategies.md](20.caching-strategies.md)
- [11.cache-invalidation-patterns.md](11.cache-invalidation-patterns.md)
- [08.Cassandra_Deep_Dive_For_Beginners.md](08.Cassandra_Deep_Dive_For_Beginners.md)
- [How to Choose the Right Database?/](How%20to%20Choose%20the%20Right%20Database%3F/) — database selection guidance
- [Database Optimization Indexing Partitioning Replication Sharding/](Database%20Optimization%20Indexing%20Partitioning%20Replication%20Sharding/) — indexing/partitioning/replication deep dive

### 5. Messaging & Streaming
- [21.message-queues.md](21.message-queues.md)
- [02.kafka-streams-why-need-architect-interview.md](02.kafka-streams-why-need-architect-interview.md)
- [37.batch-vs-streaming-lambda-kappa-architecture-interview.md](37.batch-vs-streaming-lambda-kappa-architecture-interview.md) — Lambda vs Kappa, where streaming fits vs batch

### 6. Integration & Migration Patterns
- [06.strangler-fig-anti-corruption-layer-architect-interview.md](06.strangler-fig-anti-corruption-layer-architect-interview.md)
- [07.ambassador-adapter-aggregator-scatter-gather-failover-interview.md](07.ambassador-adapter-aggregator-scatter-gather-failover-interview.md)
- [18.provider-customer-system-communication-15y.md](18.provider-customer-system-communication-15y.md)
- [33.api-gateway-bff-pattern-interview.md](33.api-gateway-bff-pattern-interview.md) — API Gateway vs Backend-for-Frontend
- [30.schema-evolution-api-versioning-interview.md](30.schema-evolution-api-versioning-interview.md) — safe changes, expand-contract, schema registry
- [39.graphql-vs-rest-long-polling-sse-interview.md](39.graphql-vs-rest-long-polling-sse-interview.md) — API paradigm & real-time transport choice
- [38.contract-testing-consumer-driven-pact-interview.md](38.contract-testing-consumer-driven-pact-interview.md) — Pact, can-i-deploy

### 7. Observability
- [24.distributed-tracing-observability-architect-interview.md](24.distributed-tracing-observability-architect-interview.md) — logs, metrics, traces, OpenTelemetry
- [35.slo-sla-error-budgets-interview.md](35.slo-sla-error-budgets-interview.md) — SLI/SLO/SLA, error budgets, burn-rate alerting
- [32.rate-limiting-algorithms-interview.md](32.rate-limiting-algorithms-interview.md) — token/leaky bucket, sliding window, distributed limits

### 7b. Security
- [26.authn-authz-security-architect-interview.md](26.authn-authz-security-architect-interview.md) — OAuth2/OIDC, JWT, Zero Trust, secrets management

### 8. Scale-Out System Design
- [17.multi-region-geo-distribution.md](17.multi-region-geo-distribution.md)
- [10.payment-gateway-system-design.md](10.payment-gateway-system-design.md)
- [22.COMPLETE_SYSTEM_DESIGN_GUIDE.md](22.COMPLETE_SYSTEM_DESIGN_GUIDE.md) — index/reference across all topics above

## Conventions
- Every file should include: plain-English explanation, a production scenario, at least one ASCII diagram, and an interview trap/cross-question section.
- If a topic is primarily about distributed consistency, it belongs here even if AWS or Spring examples are used.
