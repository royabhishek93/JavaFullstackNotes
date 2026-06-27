# Component Diagram - UPI System Architecture

## High-Level System Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UPI ECOSYSTEM OVERVIEW                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   PhonePe    │     │   Google Pay │     │    Paytm     │
│     App      │     │      App     │     │     App      │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                     │
       │                    │                     │
       └────────────────────┼─────────────────────┘
                            │
                            │ HTTPS/REST
                            │
       ┌────────────────────▼─────────────────────┐
       │         API GATEWAY LAYER                │
       │  (Kong/AWS API Gateway/Nginx)            │
       │  - Rate Limiting                         │
       │  - Authentication                        │
       │  - SSL Termination                       │
       └────────────────────┬─────────────────────┘
                            │
       ┌────────────────────▼─────────────────────┐
       │       LOAD BALANCER (AWS ALB/ELB)        │
       │       - Round Robin                      │
       │       - Health Checks                    │
       └────────────────────┬─────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
       ┌─────────────────┐    ┌─────────────────┐
       │   PSP Server 1  │    │   PSP Server N  │
       │  (Payment App)  │    │  (Payment App)  │
       └────────┬────────┘    └────────┬────────┘
                │                      │
                └───────────┬──────────┘
                            │
                            │ Dedicated Leased Line
                            │ (High Security)
                            │
                ┌───────────▼──────────┐
                │   NPCI SWITCH        │
                │   (Central Hub)      │
                └───────────┬──────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
   ┌──────────┐       ┌──────────┐      ┌──────────┐
   │  Bank A  │       │  Bank B  │      │  Bank C  │
   │   PSP    │       │   PSP    │      │   PSP    │
   └─────┬────┘       └─────┬────┘      └─────┬────┘
         │                  │                  │
         ▼                  ▼                  ▼
   ┌──────────┐       ┌──────────┐      ┌──────────┐
   │Core Bank │       │Core Bank │      │Core Bank │
   │ System A │       │ System B │      │ System C │
   └──────────┘       └──────────┘      └──────────┘
```

## Detailed PSP (Payment Service Provider) Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PSP MICROSERVICES ARCHITECTURE                           │
└─────────────────────────────────────────────────────────────────────────────┘

                          ┌─────────────────────┐
                          │   API GATEWAY       │
                          │   - JWT Validation  │
                          │   - Rate Limiting   │
                          └──────────┬──────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│   User        │          │   Payment     │          │   VPA         │
│   Service     │          │   Service     │          │   Resolution  │
│               │          │               │          │   Service     │
│ - Register    │          │ - Initiate    │          │               │
│ - KYC         │          │ - Validate    │          │ - VPA Lookup  │
│ - Profile     │◄─────────│ - Execute     │◄─────────│ - Bank Route  │
└───────┬───────┘          └───────┬───────┘          └───────────────┘
        │                          │
        │                          │
        ▼                          ▼
┌───────────────┐          ┌───────────────┐
│   Account     │          │ Transaction   │
│   Service     │          │ Management    │
│               │          │ Service       │
│ - Balance     │          │               │
│ - Link Acc    │          │ - Status      │
│ - Validate    │          │ - History     │
└───────┬───────┘          │ - Query       │
        │                  └───────┬───────┘
        │                          │
        └──────────┬───────────────┘
                   │
                   ▼
        ┌────────────────────┐
        │   NPCI Adapter     │
        │   Service          │
        │                    │
        │ - Request Format   │
        │ - Response Parse   │
        │ - Retry Logic      │
        └─────────┬──────────┘
                  │
                  │ HTTPS (Mutual TLS)
                  │
                  ▼
        ┌────────────────────┐
        │   NPCI SWITCH      │
        └────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                    SUPPORTING SERVICES LAYER                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   Auth        │   │   Fraud       │   │   Notification│   │   Analytics   │
│   Service     │   │   Detection   │   │   Service     │   │   Service     │
│               │   │   Service     │   │               │   │               │
│ - MPIN        │   │               │   │ - SMS         │   │ - Reports     │
│ - OTP         │   │ - ML Model    │   │ - Push        │   │ - Dashboard   │
│ - Biometric   │   │ - Rules       │   │ - Email       │   │ - Insights    │
└───────────────┘   │ - Scoring     │   └───────────────┘   └───────────────┘
                    └───────────────┘

┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   Compliance  │   │   Settlement  │   │   Webhook     │   │   Retry       │
│   Service     │   │   Service     │   │   Service     │   │   Service     │
│               │   │               │   │               │   │               │
│ - AML Check   │   │ - Batch       │   │ - Events      │   │ - Failed Txn  │
│ - Limits      │   │ - Reconcile   │   │ - Delivery    │   │ - Exponential │
│ - Audit       │   │ - Reports     │   │ - Tracking    │   │   Backoff     │
└───────────────┘   └───────────────┘   └───────────────┘   └───────────────┘
```

## Data Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                        CACHE LAYER (Redis Cluster)                   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │  VPA Resolution │  │  User Sessions  │  │  Rate Limiting  │    │
│  │   Cache         │  │   Cache         │  │   Counters      │    │
│  │  (TTL: 1 hour)  │  │  (TTL: 30 min)  │  │  (TTL: 1 min)   │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐                          │
│  │ Account Balance │  │  Idempotency    │                          │
│  │ Cache (30 sec)  │  │  Keys (24 hr)   │                          │
│  └─────────────────┘  └─────────────────┘                          │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│              PRIMARY DATABASE (PostgreSQL Cluster)                   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │  Master (Write)           Read Replicas (Read-heavy)    │        │
│  │                                                          │        │
│  │  - Users                  Replica 1    Replica 2        │        │
│  │  - Accounts                  │             │            │        │
│  │  - Transactions              │             │            │        │
│  │  - Settlements               └─────────────┘            │        │
│  │                          (Load Balanced Reads)          │        │
│  └─────────────────────────────────────────────────────────┘        │
│                                                                      │
│  Sharding Strategy: Hash-based on user_id                           │
│  Replication: Synchronous for critical data                         │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                 DOCUMENT STORE (MongoDB)                             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  - Transaction Logs (High write throughput)                         │
│  - Audit Trails                                                     │
│  - Event Sourcing Store                                             │
│  - User Activity Logs                                               │
│                                                                      │
│  Sharding: Range-based on timestamp                                 │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                  MESSAGE QUEUE (Kafka)                               │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Topics:                                                            │
│  - transaction.initiated                                            │
│  - transaction.completed                                            │
│  - transaction.failed                                               │
│  - notification.send                                                │
│  - fraud.detected                                                   │
│  - settlement.trigger                                               │
│                                                                      │
│  Partitions: 32 per topic (based on user_id hash)                   │
│  Retention: 7 days                                                  │
└──────────────────────────────────────────────────────────────────────┘
```

## Service Communication Pattern

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    INTER-SERVICE COMMUNICATION                              │
└─────────────────────────────────────────────────────────────────────────────┘

Synchronous (REST/gRPC):
┌──────────┐  HTTP/gRPC   ┌──────────┐  HTTP/gRPC   ┌──────────┐
│ Payment  │─────────────►│   VPA    │─────────────►│  Account │
│ Service  │◄─────────────│Resolution│◄─────────────│  Service │
└──────────┘   Response   └──────────┘   Response   └──────────┘
     │
     │ (Critical Path - Low Latency Required)
     │
     ▼
┌──────────┐
│   NPCI   │
│ Adapter  │
└──────────┘


Asynchronous (Event-Driven via Kafka):
┌──────────┐              ┌──────────┐              ┌──────────┐
│ Payment  │              │  Kafka   │              │Notification│
│ Service  │─────────────►│  Topic   │─────────────►│  Service │
└──────────┘   Publish    └──────────┘   Subscribe  └──────────┘
                               │
                               │
                               ├─────────────►┌──────────┐
                               │              │Analytics │
                               │              │  Service │
                               │              └──────────┘
                               │
                               └─────────────►┌──────────┐
                                              │Settlement│
                                              │  Service │
                                              └──────────┘

(Non-critical Path - High Throughput, Eventual Consistency)
```

## Security Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SECURITY LAYERS                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                    WAF (Web Application Firewall)      │
│  - DDoS Protection                                     │
│  - SQL Injection Prevention                            │
│  - XSS Protection                                      │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│               API Gateway Security                     │
│  - JWT Validation                                      │
│  - Rate Limiting (1000 req/min per user)               │
│  - IP Whitelisting (for merchants)                     │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│           Service Mesh (Istio/Linkerd)                 │
│  - Mutual TLS between services                         │
│  - Service-to-service authentication                   │
│  - Encryption in transit                               │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│           Application Security                         │
│  - MPIN Encryption (AES-256)                           │
│  - Device Binding                                      │
│  - OTP Validation                                      │
│  - Fraud Detection (Real-time ML)                      │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│           Data Security                                │
│  - Encryption at Rest (Database TDE)                   │
│  - Tokenization (Card/Account Numbers)                 │
│  - PII Data Masking                                    │
│  - Key Management Service (KMS)                        │
└────────────────────────────────────────────────────────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  KUBERNETES DEPLOYMENT (Multi-Zone)                         │
└─────────────────────────────────────────────────────────────────────────────┘

       ┌──────────────────────────────────────────────────────┐
       │            INGRESS CONTROLLER (NGINX)                │
       └────────────────────┬─────────────────────────────────┘
                            │
       ┌────────────────────┴─────────────────────────────────┐
       │                                                      │
   ┌───▼────┐   ZONE A                              ┌────▼───┐  ZONE B
   │  POD   │                                        │  POD   │
   │ Payment│   ┌──────┐  ┌──────┐  ┌──────┐        │Payment │
   │Service │───│Redis │  │PG DB │  │Kafka │        │Service │
   │(3 Rep) │   │Master│  │Master│  │Broker│        │(3 Rep) │
   └────────┘   └──────┘  └──────┘  └──────┘        └────────┘
       │            │         │         │                │
       │            │         │         │                │
   ┌───▼────┐   ┌──▼───┐ ┌──▼───┐  ┌──▼───┐        ┌──▼─────┐
   │  POD   │   │Redis │ │PG DB │  │Kafka │        │  POD   │
   │  Auth  │   │Slave │ │Slave │  │Broker│        │  Auth  │
   │Service │   └──────┘ └──────┘  └──────┘        │Service │
   │(2 Rep) │                                       │(2 Rep) │
   └────────┘                                       └────────┘

Auto-scaling: HPA based on CPU (70%) and custom metrics (req/sec)
Health Checks: Liveness & Readiness probes every 10s
Resource Limits: CPU: 2 cores, Memory: 4GB per pod
```
