# System Design

Interview preparation for distributed systems, scalability, and architectural patterns.

## Quick Q&A Files (4-5 minutes per question)

| Q# | Question | Study Time |
|----|----------|-----------|
| [Q17](database-scaling.md) | Database scaling for 100k concurrent users? | 5m |
| [Q18](caching-strategies.md) | Caching strategies (Redis, cache patterns)? | 4m |
| [Q19](load-balancing-algorithms.md) | Load balancing - Algorithms and strategies? | 4m |
| [Q20](microservices-vs-monolith.md) | Microservices vs monolith trade-offs? | 5m |
| [Q21](cap-theorem-trade-offs.md) | CAP theorem - Consistency vs Availability? | 4m |
| [Q22](message-queues.md) | Message queues (Kafka, RabbitMQ) - Use cases? | 4m |
| [Q23](distributed-transactions-saga-vs-2pc.md) | Saga pattern for distributed transactions? | 6m |
| [Q24](distributed-systems-concurrency-design-interviews.md) | Distributed systems + concurrency design framework (ordered writes)? | 8m |
| [Q25](distributed systems + concurrency design/README.md) | No-Kafka alternatives: option-by-option solutions | 10m |
| [Q26](distributed systems + concurrency design/kafka-vs-no-kafka-ordered-writes.md) | Same write-ordering problem: with Kafka and without Kafka | 10m |

## Deep Dive Notes (10-15 minutes each)

| Topic | Study Time |
|-------|------------|
| [Cache invalidation patterns](cache-invalidation-patterns.md) | 12-15m |
| [Database sharding strategies](database-sharding-strategies.md) | 12-15m |
| [Multi-region geo distribution](multi-region-geo-distribution.md) | 10-12m |
| [Distributed transactions: Saga vs 2PC](distributed-transactions-saga-vs-2pc.md) | 12-15m |
| [Load balancing algorithms](load-balancing-algorithms.md) | 12-15m |
| [CAP theorem trade-offs](cap-theorem-trade-offs.md) | 15m |

## Interview Prep Strategy

1. **Start here:** Q17-Q19 (scalability fundamentals - 13 minutes)
2. **Then:** Q20 (architecture patterns - 5 minutes)
3. **Advanced:** Q21-Q23 (distributed systems & patterns - 14 minutes)
5. **Practice:** Design a system (Twitter, Uber, etc.) - 2-3 hours

## Interview Frequency

- **80%** - Q17 Database scaling
- **78%** - Q18 Caching strategies
- **76%** - Q19 Load balancing
- **72%** - Q20 Microservices vs monolith
- **55%** - Q21 CAP theorem
- **52%** - Q22 Message queues
- **72%** - Q23 Saga pattern (distributed transactions)

## Key Topics Covered

- Horizontal vs vertical scaling
- Read replicas and sharding
- Caching layers (Redis, CDN)
- Load balancer algorithms (Round Robin, Least Connections)
- Microservices patterns (API Gateway, Service Mesh)
- CAP theorem trade-offs
- Event-driven architecture (Kafka)
- Global distribution and latency
- Saga pattern (Choreography vs Orchestration)
- Distributed transaction compensation logic
- Event-driven architecture with compensation
- Ordered writes under concurrency (per-machine vs global sequencing)

---

**Suggested study time:** 40-50 minutes for all Q&A files

**Interview frequency:** 45-80% (highest for senior roles!)
