# Deployment & Infrastructure Architecture

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

## 3. Kubernetes (EKS) Deployment

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  KUBERNETES CLUSTER ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────────┘

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
│                                                                            │
│  Namespace: upi-payment-prod                                               │
│                                                                            │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐  │
│  │ Payment Service     │  │ User Service        │  │ VPA Resolution   │  │
│  │                     │  │                     │  │ Service          │  │
│  │ Deployment:         │  │ Deployment:         │  │                  │  │
│  │ - Replicas: 20      │  │ - Replicas: 5       │  │ Deployment:      │  │
│  │ - CPU: 2 cores      │  │ - CPU: 1 core       │  │ - Replicas: 10   │  │
│  │ - Memory: 4GB       │  │ - Memory: 2GB       │  │ - CPU: 1 core    │  │
│  │ - HPA: 10-50        │  │ - HPA: 3-20         │  │ - Memory: 2GB    │  │
│  │                     │  │                     │  │ - HPA: 5-30      │  │
│  │ Service Type:       │  │ Service Type:       │  │                  │  │
│  │ ClusterIP           │  │ ClusterIP           │  │ Service Type:    │  │
│  │ Port: 8080          │  │ Port: 8081          │  │ ClusterIP        │  │
│  └─────────────────────┘  └─────────────────────┘  │ Port: 8082       │  │
│                                                     └──────────────────┘  │
│                                                                            │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐  │
│  │ Auth Service        │  │ Fraud Detection     │  │ Notification     │  │
│  │                     │  │ Service             │  │ Service          │  │
│  │ Deployment:         │  │                     │  │                  │  │
│  │ - Replicas: 10      │  │ Deployment:         │  │ Deployment:      │  │
│  │ - CPU: 1 core       │  │ - Replicas: 5       │  │ - Replicas: 5    │  │
│  │ - Memory: 2GB       │  │ - CPU: 2 cores      │  │ - CPU: 1 core    │  │
│  │ - HPA: 5-30         │  │ - Memory: 4GB       │  │ - Memory: 2GB    │  │
│  │                     │  │ - HPA: 3-15         │  │ - HPA: 3-20      │  │
│  │ Service Type:       │  │ - GPU: Optional     │  │                  │  │
│  │ ClusterIP           │  │                     │  │ Service Type:    │  │
│  │ Port: 8083          │  │ Service Type:       │  │ ClusterIP        │  │
│  └─────────────────────┘  │ ClusterIP           │  │ Port: 8085       │  │
│                           │ Port: 8084          │  └──────────────────┘  │
│                           └─────────────────────┘                         │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                       CONFIGURATION LAYER                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │  ConfigMaps: Database URLs, Feature Flags                           │ │
│  │  Secrets: API Keys, Certificates, Encryption Keys                    │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘

HPA = Horizontal Pod Autoscaler
Resource Limits Enforced: Yes
OOMKilled Prevention: Memory buffer 20%
```

## 4. Container Specifications

```yaml
# Example: Payment Service Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  namespace: upi-payment-prod
spec:
  replicas: 20
  selector:
    matchLabels:
      app: payment-service
  template:
    metadata:
      labels:
        app: payment-service
        version: v1.2.5
    spec:
      containers:
      - name: payment-service
        image: upi-registry/payment-service:v1.2.5
        ports:
        - containerPort: 8080
          name: http
        resources:
          requests:
            memory: "4Gi"
            cpu: "2000m"
          limits:
            memory: "8Gi"
            cpu: "4000m"
        env:
        - name: DB_HOST
          valueFrom:
            configMapKeyRef:
              name: db-config
              key: host
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: password
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8080
          initialDelaySeconds: 15
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: payment-service-hpa
  namespace: upi-payment-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: payment-service
  minReplicas: 10
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
```

## 5. Database Deployment

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
│  │  AZ-1a             │         │  (Sync Replication) │         │
│  └─────────┬──────────┘         └─────────────────────┘         │
│            │                                                    │
│            │ Async Replication                                  │
│            │                                                    │
│     ┌──────┴──────┬───────────────────────┐                    │
│     │             │                       │                    │
│  ┌──▼───────┐  ┌──▼───────┐  ┌──────────▼──┐                  │
│  │ Read     │  │ Read     │  │ Read        │                  │
│  │ Replica  │  │ Replica  │  │ Replica     │                  │
│  │ (AZ-1a)  │  │ (AZ-1b)  │  │ (AZ-1c)     │                  │
│  └──────────┘  └──────────┘  └─────────────┘                  │
│                                                                  │
│  Connection Pooling: PgBouncer (max 1000 connections/instance)  │
│  Monitoring: CloudWatch, Enhanced Monitoring (1-sec interval)    │
└──────────────────────────────────────────────────────────────────┘
```

## 6. Redis (ElastiCache) Deployment

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      REDIS CLUSTER DEPLOYMENT                               │
└─────────────────────────────────────────────────────────────────────────────┘

Redis Cluster Mode Enabled: 16 Shards (1 primary + 2 replicas each)

Shard 1:                 Shard 2:                 Shard 16:
┌────────────┐          ┌────────────┐          ┌────────────┐
│ Primary    │          │ Primary    │    ...   │ Primary    │
│ (AZ-1a)    │          │ (AZ-1b)    │          │ (AZ-1a)    │
└─────┬──────┘          └─────┬──────┘          └─────┬──────┘
      │                       │                       │
   ┌──┴───┐               ┌──┴───┐               ┌──┴───┐
   │      │               │      │               │      │
┌──▼──┐┌──▼──┐         ┌──▼──┐┌──▼──┐         ┌──▼──┐┌──▼──┐
│Repl1││Repl2│         │Repl1││Repl2│         │Repl1││Repl2│
│AZ-1b││AZ-1c│         │AZ-1c││AZ-1a│         │AZ-1b││AZ-1c│
└─────┘└─────┘         └─────┘└─────┘         └─────┘└─────┘

Instance Type: cache.r6g.2xlarge (8 vCPU, 52GB RAM per node)
Total Capacity: 16 shards × 52GB = 832GB RAM
Replication: Async (sub-millisecond lag)
Failover: Automatic (<30 seconds)
```

## 7. Kafka (MSK) Deployment

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      KAFKA CLUSTER (MSK)                                    │
└─────────────────────────────────────────────────────────────────────────────┘

Kafka Brokers: 9 nodes (3 per AZ)

AZ-1a:              AZ-1b:              AZ-1c:
┌─────────┐        ┌─────────┐        ┌─────────┐
│Broker-1 │        │Broker-4 │        │Broker-7 │
│kafka.m5 │        │kafka.m5 │        │kafka.m5 │
│.2xlarge │        │.2xlarge │        │.2xlarge │
└─────────┘        └─────────┘        └─────────┘
┌─────────┐        ┌─────────┐        ┌─────────┐
│Broker-2 │        │Broker-5 │        │Broker-8 │
└─────────┘        └─────────┘        └─────────┘
┌─────────┐        ┌─────────┐        ┌─────────┐
│Broker-3 │        │Broker-6 │        │Broker-9 │
└─────────┘        └─────────┘        └─────────┘

Topics Configuration:
- transaction.initiated: 32 partitions, RF=3
- transaction.completed: 32 partitions, RF=3
- notification.send: 16 partitions, RF=3
- fraud.detected: 8 partitions, RF=3

Retention: 7 days
Storage: 5TB EBS per broker
```

## 8. CI/CD Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CI/CD WORKFLOW                                      │
└─────────────────────────────────────────────────────────────────────────────┘

Developer Push      Jenkins Pipeline         Deployment
     │                     │                       │
     │  git push           │                       │
     ├────────────────────►│                       │
     │                     │                       │
     │                     │ 1. Build & Test       │
     │                     │    (Unit Tests)       │
     │                     │ 2. Static Analysis    │
     │                     │    (SonarQube)        │
     │                     │ 3. Security Scan      │
     │                     │    (Trivy)            │
     │                     │ 4. Build Docker Image │
     │                     │ 5. Push to ECR        │
     │                     │                       │
     │                     │ 6. Deploy to Staging  │
     │                     ├──────────────────────►│
     │                     │                       │ Staging Tests
     │                     │                       │ - Integration
     │                     │                       │ - E2E
     │                     │                       │ - Load Tests
     │                     │                       │
     │                     │◄──────────────────────┤
     │                     │   Tests Passed        │
     │                     │                       │
     │  Approve Deploy?    │                       │
     │◄────────────────────┤                       │
     │                     │                       │
     │  Approved ✓         │                       │
     ├────────────────────►│                       │
     │                     │                       │
     │                     │ 7. Blue-Green Deploy  │
     │                     ├──────────────────────►│
     │                     │    to Production      │
     │                     │                       │ New Version
     │                     │                       │ (Green)
     │                     │                       │
     │                     │ 8. Smoke Tests        │
     │                     │◄──────────────────────┤
     │                     │                       │
     │                     │ 9. Switch Traffic     │
     │                     │    (Green → Blue)     │
     │                     ├──────────────────────►│
     │                     │                       │
     │                     │ 10. Monitor           │
     │                     │     (15 min)          │
     │                     │                       │
     │                     │ 11. Rollback if       │
     │                     │     errors            │

Deployment Strategy: Blue-Green
Rollback Time: <2 minutes (switch traffic back)
Deployment Frequency: 10-15 times/day
```

## 9. Monitoring & Observability Stack

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   OBSERVABILITY ARCHITECTURE                                │
└─────────────────────────────────────────────────────────────────────────────┘

Application Services
        │
        ├─── Metrics ──────────► Prometheus ──► Grafana Dashboards
        │                        (2-min scrape)
        │
        ├─── Logs ────────────► Fluentd ──► Elasticsearch ──► Kibana
        │                       (Buffer)     (7-day hot)
        │
        ├─── Traces ──────────► Jaeger ──► Jaeger UI
        │                       (Sampling)
        │
        └─── Alerts ──────────► AlertManager ──► PagerDuty / Slack

Key Metrics Collected:
- Transaction latency (p50, p95, p99)
- Error rate (4xx, 5xx)
- Request throughput (RPS)
- Database connection pool usage
- Cache hit rate
- Queue depth (Kafka lag)

Log Aggregation:
- All application logs → Fluentd
- Structured JSON format
- Correlation ID for tracing
- Retention: 7 days hot, 30 days warm, 365 days cold (S3)

Distributed Tracing:
- OpenTelemetry instrumentation
- Jaeger for visualization
- Sampling rate: 1% (production), 100% (staging)
```

## 10. Disaster Recovery Plan

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DISASTER RECOVERY STRATEGY                             │
└─────────────────────────────────────────────────────────────────────────────┘

Scenario 1: Single AZ Failure
├─ Detection: <10 seconds (health checks fail)
├─ Action: Auto-failover to other AZs
├─ Impact: No downtime (handled by LB)
└─ RTO: 0, RPO: 0

Scenario 2: Region Failure
├─ Detection: <30 seconds (region health checks)
├─ Action: DNS failover to DR region
├─ Impact: 30-60 seconds downtime
├─ RTO: 30 seconds
└─ RPO: 0 (synchronous replication)

Scenario 3: Database Corruption
├─ Detection: Automated data integrity checks
├─ Action: Restore from point-in-time backup
├─ Impact: Service degraded (read-only mode)
├─ RTO: 2 hours
└─ RPO: 5 minutes (backup frequency)

Scenario 4: Complete Data Center Loss
├─ Detection: Manual verification
├─ Action: Activate DR site
├─ Impact: Service outage
├─ RTO: 4 hours
└─ RPO: 15 minutes

Backup Strategy:
- Automated daily snapshots (7-day retention)
- Continuous WAL archiving (PostgreSQL)
- Cross-region backup replication
- Monthly DR drills
```

## 11. Cost Optimization

```
Monthly Infrastructure Cost Estimate (USD):

EKS Cluster:
- Control Plane: $73/month
- Worker Nodes (30 × m5.4xlarge): $18,432/month
- Reserved Instances (1-year): Save 40% → $11,059/month

RDS PostgreSQL:
- Master (db.r6g.8xlarge): $4,896/month
- Read Replicas (3x): $14,688/month
- Storage (10TB io2): $6,400/month
- Reserved Instances: Save 50% → $12,992/month

ElastiCache Redis:
- 16 shards × cache.r6g.2xlarge: $13,824/month
- Reserved: Save 40% → $8,294/month

MSK (Kafka):
- 9 brokers (kafka.m5.2xlarge): $11,664/month
- Storage (45TB): $4,500/month

Data Transfer:
- Inter-AZ: ~$2,000/month
- CloudFront: ~$1,500/month

S3 Storage:
- Backups, Logs: ~$500/month

Total: ~$45,000/month (~$540K/year)

Optimization Tips:
- Use Spot Instances for non-critical workloads (60-70% savings)
- Right-size instances based on actual usage
- Enable RDS/ElastiCache reserved instances
- Compress logs before S3 storage
- Use S3 Lifecycle policies (move to Glacier)
```

This deployment architecture provides high availability, disaster recovery, and scalability for a production-grade UPI payment system!
