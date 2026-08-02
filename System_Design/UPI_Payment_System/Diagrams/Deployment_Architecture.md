# Deployment & Infrastructure Architecture (Interview Focus)

## 1. Multi-Region Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GLOBAL ARCHITECTURE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

                          ┌──────────────────┐
                          │  CloudFlare CDN  │
                          │  (Global Edge)   │
                          └────────┬─────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
         ┌──────────▼─────────┐       ┌──────────▼─────────┐
         │  REGION 1          │       │  REGION 2          │
         │  Mumbai (Primary)  │       │  Delhi (DR)        │
         │                    │       │                    │
         │  ┌──────────────┐  │       │  ┌──────────────┐  │
         │  │ 3 AZ Zones   │  │       │  │ 3 AZ Zones   │  │
         │  │ - AZ-1a      │  │       │  │ - AZ-2a      │  │
         │  │ - AZ-1b      │  │       │  │ - AZ-2b      │  │
         │  │ - AZ-1c      │  │       │  │ - AZ-2c      │  │
         │  └──────────────┘  │       │  └──────────────┘  │
         │                    │       │                    │
         │  Status: ACTIVE    │       │  Status: STANDBY   │
         │  Traffic: 100%     │       │  Traffic: 0%       │
         │  Database: Master  │       │  Database: Replica │
         └────────────────────┘       └────────────────────┘

Replication: Synchronous (for critical data)
Failover Time: <30 seconds (automated)
RPO (Recovery Point Objective): 0 (no data loss)
RTO (Recovery Time Objective): 30 seconds
```

**Interview Discussion Points**:
- **Why 2 regions?** Disaster recovery, compliance (data localization)
- **Why synchronous replication?** Zero data loss (financial transactions)
- **Cost of DR?** ~50% of primary (standby servers, data replication)

---

## 2. Single Region (Availability Zone) Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    REGION 1 - MUMBAI (DETAILED VIEW)                        │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌────────────────┐
                              │  Route 53 DNS  │
                              └───────┬────────┘
                                      │
                         ┌────────────┴────────────┐
                         │                         │
                ┌────────▼────────┐       ┌───────▼────────┐
                │   AWS ALB       │       │   AWS NLB      │
                │ (HTTP/HTTPS)    │       │  (TCP/UDP)     │
                └────────┬────────┘       └───────┬────────┘
                         │                        │
        ┌────────────────┼────────────────┬───────┘
        │                │                │
┌───────▼────────┐ ┌─────▼──────┐ ┌─────▼──────┐
│   AZ-1a        │ │   AZ-1b    │ │   AZ-1c    │
│                │ │            │ │            │
│ ┌────────────┐ │ │┌──────────┐│ │┌──────────┐│
│ │ EKS Nodes  │ │ ││EKS Nodes ││ ││EKS Nodes ││
│ │ (Workers)  │ │ ││(Workers) ││ ││(Workers) ││
│ │ - 10 Nodes │ │ ││- 10 Nodes││ ││- 10 Nodes││
│ │ - m5.4xl   │ │ ││- m5.4xl  ││ ││- m5.4xl  ││
│ └────────────┘ │ │└──────────┘│ │└──────────┘│
│                │ │            │ │            │
│ ┌────────────┐ │ │┌──────────┐│ │┌──────────┐│
│ │PostgreSQL  │ │ ││PostgreSQL││ ││PostgreSQL││
│ │ Master     │─┼─┼▶ Replica  │◀─┼▶ Replica  ││
│ │(RDS Multi) │ │ ││(Read-R1) ││ ││(Read-R2) ││
│ └────────────┘ │ │└──────────┘│ │└──────────┘│
│                │ │            │ │            │
│ ┌────────────┐ │ │┌──────────┐│ │┌──────────┐│
│ │Redis       │ │ ││Redis     ││ ││Redis     ││
│ │Master      │─┼─┼▶Replica   │◀─┼▶Replica   ││
│ │(ElastiC)   │ │ ││(Read)    ││ ││(Read)    ││
│ └────────────┘ │ │└──────────┘│ │└──────────┘│
│                │ │            │ │            │
│ ┌────────────┐ │ │┌──────────┐│ │┌──────────┐│
│ │Kafka       │ │ ││Kafka     ││ ││Kafka     ││
│ │Broker-1    │◀┼─┼▶Broker-2  │◀─┼▶Broker-3  ││
│ │(MSK)       │ │ ││(MSK)     ││ ││(MSK)     ││
│ └────────────┘ │ │└──────────┘│ │└──────────┘│
└────────────────┘ └────────────┘ └────────────┘

Auto-Scaling: Yes (CPU > 70%, Memory > 80%)
Health Checks: Every 10 seconds
Unhealthy Threshold: 2 consecutive failures
```

**Interview Discussion Points**:
- **Why 3 AZs?** Even if 1 AZ fails, 2 remain (99.99% availability)
- **Why separate ALB and NLB?** ALB for HTTP (Layer 7), NLB for high-performance TCP (Layer 4)
- **Master-Replica split?** 20% writes → Master, 80% reads → Replicas

---

## 3. Kubernetes (EKS) Deployment - Key Components

```
┌────────────────────────────────────────────────────────────────────────────┐
│                  KUBERNETES CLUSTER ARCHITECTURE                            │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                          INGRESS LAYER                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  Ingress Controller (NGINX)                                          │ │
│  │  - SSL Termination                                                   │ │
│  │  - Path-based routing                                                │ │
│  │  - Rate limiting                                                     │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                       APPLICATION LAYER                                    │
│  Namespace: upi-payment-prod                                               │
│                                                                            │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐  │
│  │ Payment Service     │  │ User Service        │  │ VPA Resolution   │  │
│  │ - Replicas: 20      │  │ - Replicas: 5       │  │ - Replicas: 10   │  │
│  │ - CPU: 2 cores      │  │ - CPU: 1 core       │  │ - CPU: 1 core    │  │
│  │ - Memory: 4GB       │  │ - Memory: 2GB       │  │ - Memory: 2GB    │  │
│  │ - HPA: 10-50        │  │ - HPA: 3-20         │  │ - HPA: 5-30      │  │
│  └─────────────────────┘  └─────────────────────┘  └──────────────────┘  │
│                                                                            │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐  │
│  │ Auth Service        │  │ Fraud Detection     │  │ Notification     │  │
│  │ - Replicas: 10      │  │ - Replicas: 5       │  │ - Replicas: 5    │  │
│  │ - CPU: 1 core       │  │ - CPU: 2 cores      │  │ - CPU: 1 core    │  │
│  │ - Memory: 2GB       │  │ - Memory: 4GB       │  │ - Memory: 2GB    │  │
│  │ - HPA: 5-30         │  │ - HPA: 3-15         │  │ - HPA: 3-20      │  │
│  └─────────────────────┘  └─────────────────────┘  └──────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘

HPA = Horizontal Pod Autoscaler (adds/removes pods based on CPU/Memory)
```

**Interview Discussion Points**:
- **Why Payment Service has most replicas (20)?** Handles 80% of traffic
- **HPA range (10-50)?** Min 10 for redundancy, Max 50 to prevent runaway scaling
- **Why separate services?** Microservices → Independent scaling, deployment, failure isolation

---

## 4. Container Resource Limits (Key Concept)

**Payment Service Deployment** (Simplified for Interview):
```yaml
Payment Service Pod:
  Resources:
    Requests:  # Minimum guaranteed
      CPU: 2 cores
      Memory: 4GB
    Limits:    # Maximum allowed
      CPU: 4 cores
      Memory: 8GB
      
  Health Checks:
    Liveness:  /health/live  (Is pod alive?)
      - Initial delay: 30s
      - Check every: 10s
      - Fail after: 3 attempts → Kill & Restart
      
    Readiness: /health/ready (Is pod ready for traffic?)
      - Initial delay: 15s
      - Check every: 5s
      - Fail after: 2 attempts → Remove from load balancer
```

**Interview Discussion Points**:
- **Liveness vs Readiness?** 
  - Liveness: Pod crashed → Restart it
  - Readiness: Pod booting/overloaded → Stop sending traffic
- **Why Limits > Requests?** Burst capacity (sudden spike handling)
- **What if pod exceeds memory limit?** OOMKilled (Out of Memory) → Restart

---

## 5. Database Deployment - PostgreSQL

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      POSTGRESQL DEPLOYMENT                                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  RDS PostgreSQL 14 (Multi-AZ)                                    │
│                                                                  │
│  Master (AZ-1a):                                                 │
│  - Instance: db.r6g.8xlarge (32 vCPU, 256GB RAM)               │
│  - Storage: 10TB SSD (io2, 40K IOPS)                           │
│  - Backup: Automated daily, 7-day retention                     │
│  - Encryption: AES-256 at rest                                  │
│                                                                  │
│  ┌────────────────────┐         ┌─────────────────────┐         │
│  │  Master (Write)    │────────▶│  Standby (AZ-1b)   │         │
│  │  AZ-1a             │ Sync    │  (Auto Failover)    │         │
│  └─────────┬──────────┘         └─────────────────────┘         │
│            │ Async                                               │
│     ┌──────┴──────┬───────────────────────┐                    │
│     │             │                       │                    │
│  ┌──▼───────┐  ┌──▼───────┐  ┌──────────▼──┐                  │
│  │ Read     │  │ Read     │  │ Read        │                  │
│  │ Replica  │  │ Replica  │  │ Replica     │                  │
│  │ (AZ-1a)  │  │ (AZ-1b)  │  │ (AZ-1c)     │                  │
│  └──────────┘  └──────────┘  └─────────────┘                  │
│                                                                  │
│  Connection Pooling: PgBouncer (max 1000 connections/instance)  │
└──────────────────────────────────────────────────────────────────┘
```

**Interview Discussion Points**:
- **Multi-AZ = High Availability**: If Master fails, Standby promoted in 30 seconds
- **Sync vs Async replication?**
  - Sync (Master → Standby): Zero data loss, slower writes
  - Async (Master → Read Replicas): Fast writes, may lag by 1-2 seconds
- **Why PgBouncer?** Reuse connections (opening new connection takes 50ms)
- **IOPS = Input/Output Operations Per Second**: 40K IOPS = 40,000 disk reads/writes per second

---

## 6. Redis (ElastiCache) Deployment

```
┌──────────────────────────────────────────────────────────────────┐
│  Redis Cluster (16 Shards)                                       │
│                                                                  │
│  Instance Type: cache.r6g.2xlarge (8 vCPU, 52GB RAM)           │
│  Total Memory: 16 shards × 52GB = 832GB                         │
│                                                                  │
│  Shard 1:  [Master] ──▶ [Replica-1] ──▶ [Replica-2]            │
│  Shard 2:  [Master] ──▶ [Replica-1] ──▶ [Replica-2]            │
│  ...                                                             │
│  Shard 16: [Master] ──▶ [Replica-1] ──▶ [Replica-2]            │
│                                                                  │
│  Eviction Policy: allkeys-lru (Least Recently Used)             │
│  Persistence: Disabled (cache only, not primary storage)         │
└──────────────────────────────────────────────────────────────────┘
```

**Interview Discussion Points**:
- **Why 16 shards?** Horizontal scaling (each shard independent)
- **allkeys-lru?** When memory full, delete least recently used key
- **Why no persistence?** Cache data can be rebuilt from database (performance > durability)
- **What's cached?**
  - VPA → Account mapping (1 hour TTL)
  - User sessions (30 min TTL)
  - Rate limit counters (1 min TTL)
  - Idempotency keys (24 hour TTL)

---

## 7. Kafka (MSK) Deployment

```
┌──────────────────────────────────────────────────────────────────┐
│  Kafka Cluster (3 Brokers across 3 AZs)                          │
│                                                                  │
│  Broker Type: kafka.m5.4xlarge (16 vCPU, 64GB RAM)             │
│  Storage per Broker: 10TB                                        │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ Broker 1 │  │ Broker 2 │  │ Broker 3 │                      │
│  │  (AZ-1a) │  │  (AZ-1b) │  │  (AZ-1c) │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
│                                                                  │
│  Key Topics:                                                     │
│  - txn-initiated      (32 partitions, 3 replicas, 7-day TTL)   │
│  - txn-success        (32 partitions, 3 replicas, 7-day TTL)   │
│  - txn-failed         (32 partitions, 3 replicas, 7-day TTL)   │
│  - fraud-alerts       (16 partitions, 3 replicas, 30-day TTL)  │
│  - settlement-events  (8 partitions, 3 replicas, 90-day TTL)   │
└──────────────────────────────────────────────────────────────────┘
```

**Interview Discussion Points**:
- **Why 3 brokers?** Minimum for fault tolerance (quorum = 2)
- **Why 32 partitions?** Parallel processing (32 consumers can read simultaneously)
- **Why 3 replicas?** Even if 2 brokers fail, 1 copy survives
- **7-day retention?** Balance between replay capability and storage cost

---

## 8. Monitoring & Observability Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                  MONITORING ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────┘

Application Logs → Fluentd → S3 + OpenSearch
                      ↓
Metrics → Prometheus → Grafana Dashboards
                      ↓
Traces → Jaeger → Distributed Tracing
                      ↓
Alerts → AlertManager → PagerDuty → Oncall Engineer
```

**Key Metrics Monitored**:
```
Golden Signals (Google SRE):
1. Latency:   p50, p95, p99 transaction time
2. Traffic:   Requests per second (TPS)
3. Errors:    Error rate, failed transactions
4. Saturation: CPU, Memory, Disk, Network usage

Business Metrics:
- Transaction success rate (>99.5%)
- Reversal rate (<0.1%)
- NPCI response time (<1s)
- Database connection pool usage
- Cache hit rate (>90%)

Critical Alerts (PagerDuty):
- Success rate < 98%       → Page immediately
- p95 latency > 5 seconds  → Page immediately
- Circuit breaker open     → Page immediately
- Database master down     → Page immediately
```

**Interview Discussion Points**:
- **Why OpenSearch (not CloudWatch)?** Better search, long-term retention, cheaper
- **What's distributed tracing?** Track 1 request across multiple services (see entire flow)
- **Why p95, not average?** Average hides outliers (1% users get 10s latency = bad UX)

---

## 9. Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                               │
└─────────────────────────────────────────────────────────────────┘

Layer 1: Network Security
┌──────────────────────────────────────┐
│ CloudFlare WAF                       │ → Block DDoS, SQL injection
│ - Rate limiting: 1000 req/min       │
│ - Bot detection                      │
│ - Geo-blocking (India only)         │
└──────────────────────────────────────┘

Layer 2: API Gateway
┌──────────────────────────────────────┐
│ Kong API Gateway                     │ → Authentication, rate limiting
│ - JWT validation                     │
│ - API key verification               │
│ - Request/response logging           │
└──────────────────────────────────────┘

Layer 3: Service Mesh
┌──────────────────────────────────────┐
│ Istio Service Mesh                   │ → Mutual TLS, traffic control
│ - mTLS between all services          │
│ - Circuit breaker                    │
│ - Retry policies                     │
└──────────────────────────────────────┘

Layer 4: Application Security
┌──────────────────────────────────────┐
│ Service Code                         │ → Input validation, auth checks
│ - MPIN encryption (AES-256)          │
│ - SQL injection prevention           │
│ - OWASP Top 10 compliance            │
└──────────────────────────────────────┘

Layer 5: Data Security
┌──────────────────────────────────────┐
│ Database + Storage                   │ → Encryption at rest
│ - TDE (Transparent Data Encryption)  │
│ - Field-level encryption (PII)       │
│ - Backup encryption                  │
└──────────────────────────────────────┘
```

**Interview Discussion Points**:
- **DDoS Risk Example**:
  ```
  Attack: 10,000 bots send 1M requests/sec
  Impact: NPCI overwhelmed, real users blocked
  Solution: Rate limit (1000 req/min per IP), CAPTCHA
  ```
- **mTLS = Mutual TLS**: Both client and server verify each other (not just client verifies server)
- **Why encrypt MPIN client-side?** Never send plain MPIN over network (man-in-the-middle attack)

---

## 10. CI/CD Pipeline (Blue-Green Deployment)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CI/CD PIPELINE                                │
└─────────────────────────────────────────────────────────────────┘

Developer Push → GitHub → Jenkins
                            ↓
                    ┌───────┴────────┐
                    │ Build & Test   │
                    │ - Unit tests   │
                    │ - Integration  │
                    └───────┬────────┘
                            ↓
                    ┌───────┴────────┐
                    │ Docker Build   │
                    │ - Create image │
                    │ - Push to ECR  │
                    └───────┬────────┘
                            ↓
                ┌───────────┴────────────┐
                │                        │
        ┌───────▼────────┐    ┌─────────▼────────┐
        │  Blue Env      │    │  Green Env       │
        │  (Current v1)  │    │  (New v2)        │
        │  100% traffic  │    │  0% traffic      │
        └───────┬────────┘    └─────────┬────────┘
                │                        │
                │  Run smoke tests       │
                │  on Green env          │
                │                        │
                │  ✓ Tests pass          │
                │  Switch traffic:       │
                │  Blue 0% → Green 100%  │
                └────────────────────────┘
```

**Interview Discussion Points**:
- **Blue-Green = Zero Downtime**: Run 2 identical environments, switch instantly
- **Why not Rolling Update?** Financial system needs all-or-nothing (not gradual rollout)
- **What if Green fails?** Instant rollback to Blue (flip load balancer back)
- **Smoke tests?** Quick tests on production-like environment (10 min max)

---

## 11. Cost Estimation (Monthly)

```
┌──────────────────────────────────────────────────────────────────┐
│                  INFRASTRUCTURE COST BREAKDOWN                    │
└──────────────────────────────────────────────────────────────────┘

Compute (EKS):
- 30 worker nodes × m5.4xlarge × $0.768/hr × 730hr = $16,800

Database (RDS):
- 1 Master db.r6g.8xlarge × $2.50/hr × 730hr = $1,825
- 3 Read Replicas × $2.50/hr × 730hr = $5,475
- Storage: 10TB × $0.125/GB = $1,250
Total Database: $8,550

Cache (ElastiCache Redis):
- 16 shards × 3 replicas × cache.r6g.2xlarge × $0.504/hr × 730hr = $14,500

Kafka (MSK):
- 3 brokers × kafka.m5.4xlarge × $0.70/hr × 730hr = $1,533

Load Balancers:
- 2 ALB + 1 NLB × $25/month = $75

Data Transfer:
- 50TB/month × $0.09/GB = $4,500

Monitoring (CloudWatch + Prometheus):
- $500/month

Total: ~$46,000/month (~₹38 lakhs/month)
```

**Interview Discussion Points**:
- **Most expensive?** Compute (EKS nodes) + Redis cache = 68% of cost
- **How to reduce cost?**
  - Use Spot instances for non-critical services (50% discount)
  - Reserved instances (1-year commit = 40% discount)
  - Optimize Redis (reduce shards if cache hit rate low)
- **Why so expensive?** High availability (multi-AZ, replicas) = 3x resources

---

## 12. Disaster Recovery (DR) Strategy

```
┌──────────────────────────────────────────────────────────────────┐
│              DISASTER RECOVERY SCENARIOS                          │
└──────────────────────────────────────────────────────────────────┘

Scenario 1: Single AZ Failure
├─ Impact: 1/3 capacity lost
├─ Action: Load balancer redirects to other 2 AZs
└─ RTO: 0 seconds (automatic), RPO: 0 (no data loss)

Scenario 2: Database Master Failure
├─ Impact: Write operations fail
├─ Action: RDS auto-promotes Standby to Master
└─ RTO: 30 seconds, RPO: 0

Scenario 3: Entire Region Failure (Mumbai datacenter fire)
├─ Impact: All services down in Mumbai
├─ Action: 
│   1. DNS failover to Delhi region (Route 53)
│   2. Promote Delhi database replica to master
│   3. Scale up Delhi EKS nodes (10 → 30)
└─ RTO: 5 minutes, RPO: <10 seconds (async replication lag)

Scenario 4: NPCI Switch Failure
├─ Impact: No transactions can proceed
├─ Action:
│   1. Circuit breaker opens (stop calling NPCI)
│   2. Show maintenance message to users
│   3. Fallback to IMPS (alternate payment method)
└─ RTO: Depends on NPCI recovery
```

**Interview Discussion Points**:
- **RTO = Recovery Time Objective**: How long can we be down?
- **RPO = Recovery Point Objective**: How much data can we lose?
- **Why can't we prevent NPCI failure?** External dependency (single point of failure)
- **What if both regions fail?** Unlikely (AWS has 99.99% SLA), but backup to tape + offline storage

---

## 13. Interview Cheat Sheet - Key Discussion Points

### When Asked: "How do you deploy this system?"

**Answer Flow**:
1. **Multi-Region** → Mumbai (primary) + Delhi (DR)
2. **Multi-AZ** → 3 availability zones per region (99.99% SLA)
3. **Kubernetes** → Microservices on EKS, auto-scaling
4. **Database** → PostgreSQL master + 3 read replicas
5. **Cache** → Redis cluster (16 shards)
6. **Messaging** → Kafka (3 brokers, 32 partitions)
7. **Blue-Green Deploy** → Zero downtime releases

### When Asked: "What if database goes down?"

**Answer**:
- **Master down?** Standby promoted in 30 seconds (Multi-AZ)
- **Read replica down?** Traffic routed to other replicas
- **Connection pool full?** Queue requests, increase pool size
- **Disk full?** Auto-scale storage (AWS RDS feature)

### When Asked: "How do you monitor?"

**Answer**:
- **Logs** → Fluentd → S3 + OpenSearch (searchable)
- **Metrics** → Prometheus → Grafana dashboards
- **Traces** → Jaeger (distributed tracing)
- **Alerts** → PagerDuty (page oncall engineer)

**Golden Signals**: Latency, Traffic, Errors, Saturation

### When Asked: "Security concerns?"

**Answer**:
**5 Layers**:
1. **Network** → WAF (block DDoS, SQL injection)
2. **API Gateway** → JWT validation, rate limiting
3. **Service Mesh** → mTLS (encrypted service-to-service)
4. **Application** → Input validation, MPIN encryption
5. **Data** → TDE (database encryption at rest)

**DDoS Example**: 10K bots spam API → Rate limit blocks them → Real users unaffected

---

## Interview Red Flags to Avoid

❌ **Don't Say**:
- "We'll run everything on 1 server" → Single point of failure
- "We don't need monitoring" → How to detect issues?
- "We'll use only 1 database" → No read scaling, single point of failure
- "Blue-Green is overkill" → Financial system needs zero downtime

✅ **Say Instead**:
- "Multi-AZ for high availability"
- "Comprehensive monitoring with alerts"
- "Master-replica split for read scaling"
- "Blue-Green deployment to prevent downtime"

---

**Total Infrastructure**: ~₹38 lakhs/month for 50K TPS, 99.99% availability 🚀
