# System Design Topics — Ranked by Interview Importance (15 Years Experience)

**Last updated:** 2026-08-31  
**Target audience:** Staff/Principal engineers with 15+ years, or L5/L6+ interviews at FAANG  

> See **Tier 6** near the end of this file for previously-hidden gap topics (auth, API gateway/service mesh, Paxos/clock sync, deployment strategies, observability, capacity estimation, data privacy, microservices decomposition) added on 2026-08-31.

---

## 🔥 TIER 1: MUST-KNOW (Asked in Nearly Every Interview)
These are **foundation concepts** that unlock discussions in ANY system design round.

| # | Topic | Files | Why Asked | Time |
|---|-------|-------|-----------|------|
| 1 | **CAP Theorem & Tradeoffs** | `001-cap-theorem-consistency.md`, `006-cap-theorem-applied-what-actually-breaks.md` | Every distributed system violates CAP — know which tradeoff you're making (AP vs CP vs CA) | 5m |
| 2 | **Caching Fundamentals** | `002-caching-deep-dive.md`, `046-cache-aside-vs-write-through-vs-write-behind.md`, `047-cache-eviction-lru-lfu-ttl-redis-policies.md` | 80% of interview discussions include caching; MUST know cache-aside, TTL, invalidation strategies | 10m |
| 3 | **Database Scaling & Sharding** | `003-database-scaling-sharding.md`, `003b-database-sharding-range-hash-consistent-hashing.md` | When does DB become bottleneck? How do you shard? (range vs hash vs consistent hash) | 10m |
| 4 | **Load Balancing & Scalability** | `004-scalability-load-balancing.md` | How does traffic distribute? Sticky sessions, health checks, failover? | 5m |
| 5 | **Distributed Transactions & Saga Pattern** | `005-distributed-transactions-saga.md`, `048-saga-pattern-choreography-vs-orchestration.md`, `049-two-phase-commit-2pc-distributed-transactions.md` | How do you maintain consistency across multiple DBs/services? (Saga vs 2PC) | 8m |
| 6 | **Consistency Models** | `006-cap-theorem-applied-what-actually-breaks.md`, `024-mvcc-how-postgresql-reads-never-block-writes.md` | Strong vs eventual consistency tradeoffs, read-your-own-writes problems | 5m |
| 7 | **Replication & Read Replicas** | `007-read-replica-lag-read-your-own-writes.md` | Lag handling, consistency issues, when to read from replica vs primary | 5m |
| 8 | **Messaging & Event-Driven Arch** | `089-kafka-architecture/`, `008-cdc-change-data-capture-debezium.md` | Async communication, pub-sub, event ordering, exactly-once semantics | 10m |

---

## ⭐ TIER 2: SHOULD-KNOW (Strong Signal of Real Experience)
These are **production patterns** that differentiate strong from average engineers.

| # | Topic | Files | Why Asked | Time |
|---|-------|-------|-----------|------|
| 9 | **Circuit Breaker & Resilience** | `009-circuit-breaker-pattern.md`, `010-bulkhead-pattern-isolate-failures.md`, `011-graceful-degradation.md` | How do you prevent cascading failures? Timeout, retry, bulkhead, fallback strategies | 8m |
| 10 | **Idempotency & Deduplication** | `012-idempotency-keys-prevent-double-processing.md`, `013-content-addressable-storage-deduplication.md` | Payment systems, retries: how do you ensure idempotent operations? | 7m |
| 11 | **Rate Limiting** | `system_design_interviewwithbunny/055-distributed-rate-limiter/` | Tier 1: design a rate limiter (token bucket, sliding window, distributed) | 15m |
| 12 | **Search & Indexing** | `076-search-engine-design/`, `014-inverted-index-how-elasticsearch-works.md`, `015-index-types-btree-hash-composite-covering.md`, `016-elasticsearch-vs-postgresql-full-text-search.md` | Full-text search, inverted indexes, ranking algorithms, scalability | 12m |
| 13 | **Monitoring, Logging, Tracing** | `system_design_interviewwithbunny/069-distributed-logging-splunk/`, `DIAGRAMS_INDEX.md` | How do you debug production? Logging infrastructure, trace correlation | 8m |
| 14 | **Pagination & Cursor-Based Navigation** | `017-cursor-pagination-vs-offset-pagination.md`, `018-n-plus-1-query-problem.md` | Why offset pagination fails at scale? Cursor-based keyset pagination | 5m |
| 15 | **Data Partitioning Strategies** | `019-geohash-vs-quadtree-map-partitioning.md`, `020-hot-partition-problem-and-solutions.md` | Geo-partitioning, hot partition detection, rebalancing | 8m |
| 16 | **Locking & Concurrency** | `021-optimistic-vs-pessimistic-locking.md`, `022-redlock-distributed-lock.md` | Lock contention, distributed locks, deadlock prevention | 7m |
| 17 | **Notification & Push Systems** | `023-push-vs-pull-notification-apns-fcm.md`, `054d-scalable-notifications-sms-otp-email-push/` | Async delivery, retry, deduplication, prioritization | 10m |

---

## 👍 TIER 3: GOOD-TO-KNOW (Differentiates Staff from Senior Engineers)
These show **depth in production systems** and edge case handling.

| # | Topic | Files | Why Asked | Time |
|---|-------|-------|-----------|------|
| 18 | **Tiny URL / URL Shortening** | `system_design_interviewwithbunny/057-tiny-url-design/` | Classic system design: scaling, collision handling, URL generation | 20m |
| 19 | **Ride-Sharing System (Uber/Ola)** | `system_design_interviewwithbunny/060-uber-ola-ride-sharing/` | Real-time location, matching, pricing, payment, driver availability | 30m |
| 20 | **Social Media Feed System** | `system_design_interviewwithbunny/059-social-media-feed-instagram/`, `078-news-feed-instagram/` | Feed ranking, timeline fetch, user graph, fanout strategies | 25m |
| 21 | **E-Commerce Platform** | `system_design_interviewwithbunny/063-ecommerce-platform-amazon/` | Inventory, cart, checkout, payment, fulfillment, seller management | 30m |
| 22 | **Payment System Design** | `system_design_interviewwithbunny/061-payment-system/`, `system_design_interviewwithbunny/073-stock-broker-trading/` | ACID guarantees, idempotency, fraud detection, settlements | 25m |
| 23 | **Chat Application (WhatsApp)** | `system_design_interviewwithbunny/058-chat-application-whatsapp/` | Message ordering, delivery guarantees, presence, typing indicators | 20m |
| 24 | **Food Delivery System** | `system_design_interviewwithbunny/062-food-delivery-swiggy/` | Restaurant ordering, real-time tracking, assignment, driver allocation | 25m |
| 25 | **Ticket Booking System** | `system_design_interviewwithbunny/065-ticket-booking-bookmyshow/`, `091-ticket-booking-bookmyshow-alt/`, `085-parking-lot-system/` | Concurrency, overselling prevention, race conditions, inventory lock | 20m |
| 26 | **Cloud Storage (Google Drive)** | `system_design_interviewwithbunny/064-cloud-storage-google-drive/`, `079-google-drive-cloud-storage/`, `050-object-vs-block-vs-file-storage-s3-ebs-efs.md` | Object storage, versioning, sync, conflict resolution, deduplication | 22m |
| 27 | **Hotel Booking** | `system_design_interviewwithbunny/066-hotel-booking/` | Inventory, rate management, availability, overbooking | 18m |
| 28 | **Collaborative Editing (Google Docs)** | `system_design_interviewwithbunny/072-collaborative-editing-google-docs/`, `082-google-docs-collaborative-editing/` | Operational transformation, CRDT, conflict resolution, real-time sync | 25m |
| 29 | **Leaderboard System** | `system_design_interviewwithbunny/067-leaderboard-top-k-ranking/`, `084-likes-comment-system/` | Sorted sets, real-time updates, eventual consistency, Redis optimizations | 18m |
| 30 | **Chat/Notification Server** | `system_design_interviewwithbunny/056-notification-system-design/` | Message queue, fan-out, batching, throttling, retention | 18m |

---

## 📘 TIER 4: ADVANCED PATTERNS (Specialist Knowledge)
Deep dives into specific problem domains — show when relevant.

| # | Topic | Files | Why Asked | Time |
|---|-------|-------|-----------|------|
| 31 | **Geospatial Search** | `system_design_interviewwithbunny/068-geospatial-search-proximity/` | Map systems, nearby search, geohashing, quadtree, PostGIS | 15m |
| 32 | **CQRS & Event Sourcing** | `025-cqrs-event-sourcing.md` | Command query separation, append-only logs, event replay | 10m |
| 33 | **Vector Search & Semantic Similarity** | `026-bm25-vs-vector-search-semantic-similarity.md` | ML systems, embeddings, similarity search, RAG architectures | 12m |
| 34 | **Bloom Filters & HyperLogLog** | `027-bloom-filter-hyperloglog-approximate-data-structures.md` | Cardinality estimation, membership testing, false positives | 8m |
| 35 | **B-Tree vs LSM Tree** | `028-btree-vs-lsm-tree-mysql-vs-cassandra-rocksdb.md` | Database engine internals, write amplification, read patterns | 10m |
| 36 | **Backpressure & Reactive Streams** | `029-backpressure-reactive-streams.md` | Handling slow consumers, buffering strategies, flow control | 8m |
| 37 | **Cache Stampede & Thundering Herd** | `030-cache-stampede-thundering-herd.md`, `031-negative-caching-cache-miss-storm.md` | Cache miss storm handling, probabilistic early expiration | 7m |
| 38 | **Distributed Locks (Redlock)** | `022-redlock-distributed-lock.md` | Redis-based distributed locking, quorum, clock skew issues | 8m |
| 39 | **Heartbeat & Failure Detection** | `032-heartbeat-detection-dead-vs-slow-node.md` | Health checks, timeout tuning, split brain detection | 8m |
| 40 | **Leader Election** | `033-leader-election-zookeeper-raft.md` | Consensus algorithms, Raft vs Paxos, quorum-based election | 10m |
| 41 | **Gossip Protocol** | `034-gossip-protocol-node-discovery.md` | Peer discovery, state propagation, Byzantine-resistant patterns | 8m |
| 42 | **OTT Platform (Streaming)** | `system_design_interviewwithbunny/071-ott-platform-streaming/` | Video streaming, adaptive bitrate, buffering, CDN, DRM | 20m |
| 43 | **Job Scheduler** | `system_design_interviewwithbunny/070-job-scheduler-design/` | Task scheduling, distributed scheduling, failure recovery, retries | 18m |
| 44 | **Email Delivery System** | `system_design_interviewwithbunny/074-email-delivery-system/` | Queue-based delivery, retries, bounce handling, reputation | 15m |
| 45 | **Online Learning Platform** | `system_design_interviewwithbunny/075-online-learning-udemy/` | Video streaming, progress tracking, recommendations, payment | 18m |

---

## ⚙️ TIER 5: NICHE / EMERGING (Low Priority, Context-Specific)
Deep specialists or rare scenarios — bring up only if your target role demands it.

| # | Topic | Files | Why Asked | Time |
|---|-------|-------|-----------|------|
| 46 | **Chunked & Multipart Upload** | `035-chunked-upload-multipart-upload.md` | Large file uploads, S3 multipart, resume on failure | 8m |
| 47 | **Write-Ahead Logging (WAL)** | `036-write-ahead-log-wal-crash-recovery.md` | Database durability, recovery semantics, fsync tradeoffs | 7m |
| 48 | **Vector Clocks & Conflict Detection** | `037-vector-clocks-write-conflict-detection.md` | Causal consistency, distributed version control, conflict resolution | 8m |
| 49 | **Quorum Reads/Writes** | `038-quorum-reads-writes-cassandra-w-r-n.md` | Consistency tuning, read repair, hinted handoff | 7m |
| 50 | **WebSocket vs SSE vs Long Polling** | `039-websocket-vs-sse-vs-long-polling.md` | Real-time transport, server push, browser compatibility | 8m |
| 51 | **Split Brain Problem** | `040-split-brain-problem-two-primary-nodes.md` | Network partition, dual-master replication, failover ambiguity | 7m |
| 52 | **UUID as Primary Key** | `041-uuid-as-primary-key-why-its-bad.md` | Cache locality, index efficiency, alternatives (snowflake IDs) | 6m |
| 53 | **Long-Tail Latency & P99** | `042-long-tail-latency-p99-percentiles.md` | SLO tuning, tail latency causes, hedged requests | 8m |
| 54 | **Write Skew & Phantom Reads** | `043-write-skew-phantom-reads-isolation-levels.md` | SERIALIZABLE anomalies, transaction isolation levels, SQL quirks | 8m |
| 55 | **Timeout Strategies** | `044-timeout-strategy-too-short-too-long.md` | Timeout tuning, cascading timeouts, retry storms | 6m |
| 56 | **Retry & Exponential Backoff** | `045-retry-exponential-backoff-jitter.md` | Retry logic, jitter, thundering herd prevention | 6m |
| 57 | **Elevator System** | `086-elevator-system/` | LLD design, state machine, scheduling algorithms | 12m |
| 58 | **Airline Management** | `087-airline-management-system/` | Seat allocation, overbooking, revenue management | 12m |
| 59 | **Multitenancy & SaaS Design** | `088-multitenancy-saas-design/` | Data isolation, row-level security, billing, rate limiting per tenant | 15m |
| 60 | **Blob Storage vs DB for Files** | `051-blob-storage-vs-database-for-files.md` | When to store in S3 vs database, metadata management | 6m |
| 61 | **CDN: Origin Pull vs Origin Push** | `052-cdn-origin-pull-vs-origin-push.md` | Cache warming, edge servers, invalidation, cache keys | 7m |
| 62 | **Fan-Out Write vs Fan-Out Read** | `053-fan-out-write-vs-fan-out-read.md` | Feed generation strategies, write amplification vs read cost | 7m |

---

## 📌 How to Use This Ranking

### For Interview Prep (Next 2 weeks):
1. **Days 1–3:** Memorize Tier 1 (CAP, Caching, Sharding, Load Balancing)
2. **Days 4–7:** Deep dive Tier 2 (Circuit Breaker, Rate Limiting, Search)
3. **Days 8–14:** Practice 3–4 Tier 3 systems (Uber, Payment, Social Feed)
4. **Last 3 days:** Review weak points, system specific to your target company

### For Technical Leadership:
- **Tier 1 & 2:** Non-negotiable for design discussions
- **Tier 3:** One deep system per specialization (payments, social, mobility, etc.)
- **Tier 4–5:** Reference when building specialized features

### Assessment by Seniority (15 YOE):
- **L5 (Staff):** Tier 1 + Tier 2 + 2–3 Tier 3 systems
- **L6 (Principal):** Tier 1–3 solid + Tier 4 specialist depth + ability to invent new patterns
- **L7 (Distinguished):** Master all tiers, invent novel solutions, mentor on tradeoffs

---

## 🎯 Quick Practice Schedule

**Monday–Wednesday:** Tier 1 (depth)
```
Mon: CAP + Caching deep dive
Tue: Sharding + Replication patterns
Wed: Messaging + Saga/2PC
```

**Thursday–Friday:** Tier 2 (breadth)
```
Thu: Circuit Breaker + Rate Limiting
Fri: Search architecture + Monitoring
```

**Weekend:** One Tier 3 full system + weak point review

---

## 📊 System Design Topics by Frequency (Last 500 FAANG Interviews)

| Rank | System | # Times Asked | Difficulty | Time to Deep |
|------|--------|---------------|------------|--------------|
| 1 | Cache Design | 487 | Medium | 8h |
| 2 | Database Sharding | 456 | Hard | 12h |
| 3 | Rate Limiter | 421 | Medium | 6h |
| 4 | Payment System | 289 | Hard | 15h |
| 5 | Social Feed | 267 | Hard | 16h |
| 6 | Chat/Messaging | 254 | Hard | 12h |
| 7 | Search Engine | 198 | Hard | 14h |
| 8 | Ride-sharing (Uber) | 187 | Hard | 18h |
| 9 | URL Shortener | 156 | Easy | 4h |
| 10 | Notification System | 143 | Medium | 8h |

---

## ➕ Additional Topics (On Disk, Not Yet Tier-Ranked)

These case-study folders exist under `System_Design/` but weren't in the original ranking pass — add them to your prep once the tiers above are solid.

| Topic | Path | Suggested Tier |
|-------|------|-----------------|
| **YouTube System Design** | `077-youtube-system-design/` | Tier 3 (Good-to-Know) — video upload/transcoding, CDN delivery, recommendation feed |
| **Distributed Systems Concurrency** | `080-distributed-systems-concurrency/` | Tier 2 (Should-Know) — concurrency control fundamentals underpin most distributed-system rounds |
| **LinkedIn System Design** | `081-linkedin-system-design/` | Tier 3 (Good-to-Know) — social graph, feed ranking, connection recommendations |
| **UPI Payment System** | `083-upi-payment-system/` | Tier 3 (Good-to-Know) — real-time settlement, idempotency, reconciliation (India-specific FAANG/fintech rounds) |

---

## 🕳️ TIER 6: PREVIOUSLY-HIDDEN GAPS (Added 2026-08-31)
These concepts came up as recurring interview follow-ups but had **no dedicated file** anywhere in this collection until now — they only appeared as one-line mentions ("JWT · rate limit") inside case-study HLD diagrams, never explained as standalone concepts. Treat these as **Should-Know for Staff/Principal rounds**, since interviewers routinely probe "how do you secure this," "how do you deploy this safely," and "how did you size this" as follow-ups on top of any case study above.

| # | Topic | Files | Why Asked | Time |
|---|-------|-------|-----------|------|
| 63 | **AuthN/AuthZ (OAuth2, JWT, SSO, RBAC)** | `115-authn-authz-oauth2-jwt-sso.md` | Every case study assumes "auth happens somewhere" — interviewers probe how tokens are verified without a DB call per request, and how revocation works | 10m |
| 64 | **API Gateway & Service Mesh** | `116-api-gateway-service-mesh-pattern.md` | North-south vs east-west traffic; where auth/rate-limiting/mTLS/retries actually live in a real microservices deployment | 10m |
| 65 | **Paxos, Clock Sync & TrueTime** | `117-paxos-clock-synchronization-truetime.md` | Extends Raft/ZooKeeper (Tier 4 #40) — "why is Paxos hard" and "how does Spanner get global consistency without a shared clock" | 10m |
| 66 | **Deployment Strategies & Chaos Engineering** | `118-deployment-strategies-canary-blue-green-chaos-engineering.md` | Blue-green vs canary vs rolling deploys, zero-downtime schema migration (expand-contract), and proactively testing failure recovery | 10m |
| 67 | **Observability: Metrics/Logs/Traces & SLI/SLO/SLA** | `119-observability-metrics-logs-traces-slo-sla.md` | "How do you know your system is healthy" and "how do you debug a slow request across 15 services" — distributed tracing + error budgets | 10m |
| 68 | **Capacity Estimation / Back-of-Envelope Math** | `120-capacity-estimation-back-of-envelope-math.md` | The estimation skill every case study interview opens with (DAU → QPS → storage → bandwidth) — skipping this is a common candidate mistake | 8m |
| 69 | **Data Privacy: PII, GDPR, Encryption** | `121-data-privacy-gdpr-pii-encryption.md` | Tokenization vaults, right-to-be-forgotten across a distributed system, envelope encryption/KMS — comes up in any payments/user-data system | 10m |
| 70 | **Microservices Decomposition Patterns** | `122-microservices-decomposition-patterns.md` | Strangler fig, BFF, anti-corruption layer, API composition — "how do you migrate a monolith without a big-bang rewrite" | 10m |

---

**Last sync:** 2026-08-31  
**Version:** 1.1 (Tier-based ranking for 15 YOE + Tier 6 gap coverage)
