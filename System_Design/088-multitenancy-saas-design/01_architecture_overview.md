# Architecture Overview — Multitenant SaaS on AWS

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PROVIDER INFRASTRUCTURE                           │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         DNS LAYER (Route 53)                         │   │
│  │   Wildcard record:  *.app.yourdomain.com  →  CloudFront              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌─────────────────────────────────▼──────────────────────────────────────┐ │
│  │                    CloudFront (CDN + WAF)                              │ │
│  │   - DDoS protection (AWS Shield)                                      │ │
│  │   - SSL termination (ACM wildcard cert)                               │ │
│  │   - Cache static assets                                               │ │
│  │   - Route /api/* → API Gateway                                        │ │
│  │   - Route /*     → S3 (React SPA)                                     │ │
│  └──────────────────────┬─────────────────────────┬──────────────────────┘ │
│                          │                         │                         │
│          ┌───────────────▼──────┐    ┌─────────────▼──────────────────┐    │
│          │   S3 (React SPA)     │    │   AWS API Gateway               │    │
│          │   - Single build     │    │   - Injects X-Tenant-ID header  │    │
│          │   - Per-tenant theme │    │   - Rate limiting per tenant    │    │
│          │     via runtime env  │    │   - JWT authorizer (Cognito)    │    │
│          └──────────────────────┘    └──────────────┬──────────────────┘    │
│                                                      │                       │
│                                      ┌───────────────▼──────────────────┐   │
│                                      │    Spring Cloud Gateway           │   │
│                                      │    (ECS Fargate)                  │   │
│                                      │    - Extract tenant from hostname │   │
│                                      │    - Validate tenant active       │   │
│                                      │    - Route to microservices       │   │
│                                      └──────────┬────────────────────────┘   │
│                                                  │                            │
│              ┌───────────────────────────────────┼───────────────────────┐   │
│              │               SERVICE MESH (ECS)  │                       │   │
│              │                                   │                       │   │
│  ┌───────────▼───────────┐  ┌───────────────────▼───┐  ┌──────────────┐ │   │
│  │   Core Business API   │  │  Tenant Registry API  │  │ Notification │ │   │
│  │   (Spring Boot)       │  │  (Spring Boot)        │  │ Service      │ │   │
│  │   - TenantFilter      │  │  - Onboard/Offboard   │  │ (SES/SNS)    │ │   │
│  │   - Schema routing    │  │  - Subscription mgmt  │  └──────────────┘ │   │
│  │   - Business logic    │  │  - Dependency graph   │                   │   │
│  └───────────┬───────────┘  └───────────────────────┘                   │   │
│              │                                                            │   │
│  ┌───────────▼──────────────────────────────────────────────────────┐    │   │
│  │                    DATA LAYER (RDS PostgreSQL)                    │    │   │
│  │                                                                   │    │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │    │   │
│  │   │ schema:     │  │ schema:     │  │ schema:     │  ...N        │    │   │
│  │   │ tenant_abc  │  │ tenant_xyz  │  │ tenant_def  │             │    │   │
│  │   │ (isolated)  │  │ (isolated)  │  │ (isolated)  │             │    │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘             │    │   │
│  │                                                                   │    │   │
│  │   ┌─────────────────────────────────┐                            │    │   │
│  │   │ schema: platform (shared)       │ ← tenant registry,         │    │   │
│  │   │                                 │   subscriptions, billing   │    │   │
│  │   └─────────────────────────────────┘                            │    │   │
│  └───────────────────────────────────────────────────────────────────┘    │   │
│                                                                            │   │
│  ┌──────────────────────────────────────────────────────────────────────┐ │   │
│  │              CROSS-CUTTING AWS SERVICES                              │ │   │
│  │  Cognito (Auth)  │  ElastiCache (Redis)  │  S3 (Tenant Files)       │ │   │
│  │  Secrets Manager │  EventBridge          │  CloudWatch (Observability)│ │   │
│  └──────────────────────────────────────────────────────────────────────┘ │   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

### 1. Route 53 — Wildcard DNS

```
*.app.yourdomain.com  →  CloudFront Distribution
```

- Every subdomain (`tenantA.app.com`, `tenantB.app.com`) resolves to the same CloudFront distribution.
- No new DNS records needed per tenant — wildcard handles all future tenants automatically.
- ACM wildcard certificate `*.app.yourdomain.com` covers SSL for all subdomains.

---

### 2. CloudFront + WAF

| Concern | How handled |
|---------|-------------|
| SSL termination | ACM wildcard cert attached to distribution |
| DDoS | AWS Shield Standard (free), Shield Advanced optional |
| Bot protection | AWS WAF web ACL on CloudFront |
| Routing | Behaviors: `/api/*` → API Gateway, `/*` → S3 |
| Tenant branding | React app reads subdomain at runtime to load tenant theme |

---

### 3. AWS API Gateway

- **Purpose:** First AWS entry point for API calls — lightweight, serverless.
- **Tenant header injection:** Lambda authorizer validates JWT, extracts `tenantId` claim, injects `X-Tenant-ID` header.
- **Rate limiting:** Per-tenant usage plans prevent noisy-neighbor throttling.
- **Integration:** HTTP integration proxy to Spring Cloud Gateway (on ECS).

---

### 4. Spring Cloud Gateway (ECS Fargate)

**This is the equivalent of SAP BTP's App Router.**

Responsibilities:
- Extract tenant from `Host` header (e.g., `tenantA` from `tenantA.app.com`)
- Validate tenant exists and is `ACTIVE` (Redis cache, 5-minute TTL)
- Forward `X-Tenant-ID` header downstream
- Load balance across Core API instances

```yaml
# Gateway route config
spring:
  cloud:
    gateway:
      routes:
        - id: core-api
          uri: lb://core-api
          predicates:
            - Path=/api/**
          filters:
            - TenantResolutionFilter   # custom filter — see 02_tenant_routing.md
            - StripPrefix=1
```

---

### 5. Core Business API (Spring Boot)

- Stateless, horizontally scalable on ECS Fargate.
- `TenantContextHolder` (ThreadLocal) carries `tenantId` through the request.
- `TenantAwareDataSource` routes DB calls to the correct schema.
- Business logic is **100% tenant-agnostic** — tenant isolation is infrastructure concern.

---

### 6. Tenant Registry API (Spring Boot)

**Equivalent of SAP SaaS Provisioning Service.**

Endpoints:
```
POST   /internal/tenants           → Onboard new tenant
DELETE /internal/tenants/{id}      → Offboard tenant  
GET    /internal/tenants/{id}      → Get tenant info
GET    /internal/tenants/{id}/status → Check subscription status
```

Triggers on subscription:
1. Create schema in RDS
2. Run Flyway migrations on new schema
3. Create Cognito User Pool App Client for tenant
4. Send welcome email via SES
5. Publish `TENANT_ONBOARDED` event to EventBridge

---

### 7. Data Layer (RDS PostgreSQL)

Three schemas exist:
- `platform` — shared metadata (tenants table, subscriptions, billing)
- `tenant_{id}` — one per tenant, fully isolated tables

See [05_data_isolation.md](05_data_isolation.md) for detailed comparison.

---

## Deployment Model

```
Environment:  production
Compute:      ECS Fargate (auto-scaling, no EC2 management)
Region:       us-east-1 (primary), us-west-2 (failover)
Database:     RDS PostgreSQL Multi-AZ
Cache:        ElastiCache Redis Cluster
Auth:         AWS Cognito User Pool (single, shared)
Secrets:      AWS Secrets Manager (DB credentials, API keys)
IaC:          AWS CDK (TypeScript)
```

---

## Scalability Properties

| Metric | Approach |
|--------|----------|
| Tenants (scale-out) | Schema-per-tenant, no code change needed |
| Users per tenant | Cognito scales to millions per pool |
| API throughput | ECS auto-scaling on CPU/request-count |
| DB connections | RDS Proxy (connection pooling, shared across tenants) |
| Cache | Redis with tenant-prefixed keys (`tenant:{id}:data`) |
| Cost | Fixed infra cost shared across tenants — provider pays |
