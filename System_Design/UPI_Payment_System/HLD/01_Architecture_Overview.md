# High-Level Design - Architecture Overview

## 1. System Requirements

### Functional Requirements
1. **User Management**
   - User registration with KYC
   - Link bank accounts
   - Create/manage UPI handles (VPA)
   - MPIN setup and management

2. **Payment Operations**
   - P2P (Person-to-Person) money transfer
   - P2M (Person-to-Merchant) payments
   - QR code-based payments
   - Request money
   - Bill payments
   - Balance inquiry

3. **Transaction Management**
   - Transaction history
   - Transaction status tracking
   - Receipt generation
   - Refund/reversal processing

4. **Notifications**
   - SMS notifications
   - Push notifications
   - Email notifications
   - Transaction alerts

### Non-Functional Requirements

| Requirement | Target | Justification |
|------------|--------|---------------|
| **Availability** | 99.99% | Financial system, downtime = revenue loss |
| **Latency** | <3 seconds | User experience, competitive parity |
| **Throughput** | 50K TPS (peak) | Handle festival season traffic |
| **Consistency** | Strong | Financial transactions cannot be eventually consistent |
| **Data Retention** | 10 years | RBI compliance requirement |
| **Concurrency** | 10M concurrent users | Support scale |
| **Security** | PCI-DSS Level 1 | Payment card industry standards |

## 2. Capacity Estimation

### Traffic Estimates
```
Active Users: 500 million
Daily Active Users (DAU): 100 million (20%)
Transactions per user per day: 2
Daily transactions: 200 million
Peak hour transactions: 20 million (10% of daily)
Peak TPS: 20M / 3600 = ~5,500 TPS (normal)
Festival/Sale Peak: 10x = 55,000 TPS

Design for: 50,000 - 60,000 TPS
```

### Storage Estimates
```
Per Transaction Data: 500 bytes
Daily storage: 200M × 500 bytes = 100 GB/day
Yearly storage: 100 GB × 365 = 36.5 TB/year
With replication (3x): 110 TB/year
With logs and audit: 150 TB/year

User Data:
500M users × 1 KB = 500 GB (relatively small)

10-year retention: 1.5 PB
```

### Bandwidth Estimates
```
Incoming:
- 50K TPS × 5 KB (avg request) = 250 MB/s = 2 Gbps

Outgoing:
- 50K TPS × 3 KB (avg response) = 150 MB/s = 1.2 Gbps

Total: ~4 Gbps (peak)
Design for: 10 Gbps with buffer
```

### Memory Estimates (Cache)
```
Cache Strategy:
- VPA resolution: 100M active VPAs × 200 bytes = 20 GB
- User sessions: 10M concurrent × 2 KB = 20 GB
- Rate limiting counters: 10M users × 100 bytes = 1 GB
- Idempotency keys (24 hr): 200M × 200 bytes = 40 GB

Total cache: ~80 GB (distributed across cluster)
Design for: 200 GB Redis cluster
```

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          UPI ECOSYSTEM LAYERS                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ PhonePe  │  │Google Pay│  │  Paytm   │  │Bank Apps │                 │
│  │   iOS    │  │ Android  │  │   Web    │  │  Mobile  │                 │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘                 │
└───────────────────────────────┬───────────────────────────────────────────┘
                                │
                                │ HTTPS/TLS 1.3
                                │
┌───────────────────────────────▼───────────────────────────────────────────┐
│                        EDGE LAYER                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  CDN (CloudFlare) - Static Assets, Rate Limiting                   │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  WAF (Web Application Firewall) - DDoS Protection                  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┬───────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────┐
│                        GATEWAY LAYER                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  API Gateway (Kong/AWS API Gateway)                                 │ │
│  │  - Authentication (JWT)                                             │ │
│  │  - Authorization                                                    │ │
│  │  - Request Validation                                               │ │
│  │  - Rate Limiting (1000 req/min per user)                            │ │
│  │  - Request/Response Transformation                                  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┬───────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────┐
│                      LOAD BALANCING LAYER                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  L7 Load Balancer (AWS ALB / NGINX)                                 │ │
│  │  - Round Robin / Least Connections                                  │ │
│  │  - Health Checks                                                    │ │
│  │  - SSL Termination                                                  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┬───────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────┐
│                    APPLICATION/SERVICE LAYER                              │
│  (Microservices Architecture - Kubernetes Pods)                           │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │    User      │  │   Payment    │  │     VPA      │                   │
│  │   Service    │  │   Service    │  │  Resolution  │                   │
│  │              │  │              │  │   Service    │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │   Account    │  │ Transaction  │  │     Auth     │                   │
│  │   Service    │  │   Service    │  │   Service    │                   │
│  │              │  │              │  │              │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │    Fraud     │  │ Notification │  │  Settlement  │                   │
│  │  Detection   │  │   Service    │  │   Service    │                   │
│  │              │  │              │  │              │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
└───────────────────────────────┬───────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────┐
│                      DATA LAYER                                           │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  Cache Layer (Redis Cluster)                                        │ │
│  │  - VPA Cache, Session Cache, Rate Limit Counters                    │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  Primary Database (PostgreSQL - Master/Slave)                       │ │
│  │  - Users, Accounts, Transactions, Settlements                       │ │
│  │  - Sharded by user_id                                               │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  Document Store (MongoDB)                                           │ │
│  │  - Transaction Logs, Audit Trails, Events                           │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  Message Queue (Apache Kafka)                                       │ │
│  │  - Event Streaming, Async Processing                                │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  Object Storage (S3)                                                │ │
│  │  - Transaction Receipts, KYC Documents, Backups                     │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┬───────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────┐
│                    EXTERNAL INTEGRATION LAYER                             │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  NPCI Switch (Dedicated Leased Line)                                │ │
│  │  - Transaction Routing                                              │ │
│  │  - Settlement Processing                                            │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  Bank Core Banking Systems                                          │ │
│  │  - Account Validation                                               │ │
│  │  - Debit/Credit Operations                                          │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  Third-Party Services                                               │ │
│  │  - SMS Gateway (Twilio), Email (SendGrid), Push (FCM)              │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
```

## 4. Key Architectural Decisions

### 4.1 Microservices vs Monolith
**Decision**: Microservices Architecture

**Rationale**:
- **Independent scaling**: Payment service needs 10x more instances than user service
- **Team autonomy**: Different teams can own different services
- **Technology flexibility**: Use best tool for each job (Go for payment processing, Python for ML fraud detection)
- **Fault isolation**: Notification service failure doesn't bring down payments
- **Deployment flexibility**: Deploy payment fixes without touching user service

**Trade-offs**:
- Increased operational complexity
- Network latency between services
- Distributed transaction complexity
- More infrastructure cost

### 4.2 Database Choice
**Decision**: Polyglot Persistence

**SQL (PostgreSQL)** for:
- Users, Accounts, Transactions (ACID required)
- Strong consistency needs
- Complex queries and joins

**NoSQL (MongoDB)** for:
- Logs and audit trails (high write volume)
- Event sourcing
- Schema flexibility

**Redis** for:
- Caching (VPA resolution, sessions)
- Rate limiting
- Idempotency keys

**Rationale**: Different data access patterns require different databases

### 4.3 Synchronous vs Asynchronous Processing
**Decision**: Hybrid Approach

**Synchronous**:
- Critical path: Payment validation, NPCI communication
- User expects immediate response
- Strong consistency required

**Asynchronous** (Kafka):
- Notifications (SMS, email, push)
- Analytics and reporting
- Settlement processing
- Fraud detection scoring

### 4.4 CAP Theorem Trade-off
**Decision**: CP (Consistency + Partition Tolerance)

**Rationale**: 
- Cannot tolerate inconsistent account balances
- Double-spending must be prevented
- Sacrifice availability during network partitions
- Financial correctness > 100% uptime

### 4.5 Data Partitioning Strategy
**Decision**: Hash-based sharding on `user_id`

**Rationale**:
- User's data stays together (transactions, accounts)
- Predictable shard routing
- Easy to add more shards

**Trade-off**: Cross-user queries (receiver's transactions) require scatter-gather

## 5. Technology Stack (Example)

| Component | Technology | Alternatives |
|-----------|-----------|--------------|
| **API Gateway** | Kong | AWS API Gateway, Apigee |
| **Load Balancer** | AWS ALB | NGINX, HAProxy |
| **Backend Services** | Java (Spring Boot) | Go, Node.js, Python |
| **Service Mesh** | Istio | Linkerd, Consul |
| **Container Orchestration** | Kubernetes | Docker Swarm, ECS |
| **Primary Database** | PostgreSQL | MySQL, CockroachDB |
| **Cache** | Redis Cluster | Memcached, Hazelcast |
| **Document Store** | MongoDB | Cassandra, Elasticsearch |
| **Message Queue** | Apache Kafka | RabbitMQ, AWS SQS |
| **Search** | Elasticsearch | Solr, Algolia |
| **Monitoring** | Prometheus + Grafana | Datadog, New Relic |
| **Logging** | ELK Stack | Splunk, Loki |
| **Tracing** | Jaeger | Zipkin, AWS X-Ray |
| **CI/CD** | Jenkins + ArgoCD | GitLab CI, CircleCI |
| **Cloud Provider** | AWS | GCP, Azure |

## 6. Deployment Architecture

```
Multi-Region Deployment for High Availability:

Region A (Primary)          Region B (DR - Active Standby)
├─ 3 Availability Zones     ├─ 3 Availability Zones
├─ Active-Active LB         ├─ Passive (ready to activate)
├─ Database Master          ├─ Database Replica
└─ Full Service Stack       └─ Full Service Stack

Data Replication: Synchronous for critical data
Failover Time: <30 seconds (automated)
```

## 7. Key Principles

1. **Security First**: All communication encrypted, MPIN never stored in plain text
2. **Idempotency**: Every request can be safely retried
3. **Observability**: Comprehensive logging, metrics, tracing
4. **Resilience**: Circuit breakers, retries with exponential backoff, graceful degradation
5. **Compliance**: RBI guidelines, PCI-DSS, data localization (India)
