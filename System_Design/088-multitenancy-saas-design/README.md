# Multitenancy SaaS System Design
## Spring Boot + AWS + React.js — Architect's Guide

> Inspired by SAP BTP Multitenancy patterns, re-architected for the AWS ecosystem.

---

## What This Covers

A production-grade, multi-tenant SaaS platform where:
- A **single deployment** serves **multiple customers (tenants)**
- Each tenant gets an **isolated subdomain** (`tenant1.app.com`, `tenant2.app.com`)
- Data is **logically or physically separated** per tenant
- Tenants are **onboarded/offboarded** programmatically
- Resources (compute, DB, cache) are **shared by default**, with upgrade paths to dedicated

---

## SAP BTP → AWS/Spring Concept Mapping

| SAP BTP Concept               | AWS + Spring Equivalent                                  |
|-------------------------------|----------------------------------------------------------|
| SaaS Provisioning Service     | Custom Spring Boot Tenant Registry + AWS EventBridge     |
| XSUAA (auth service)          | AWS Cognito (User Pools) + Spring Security + JWT         |
| App Router                    | AWS API Gateway + Spring Cloud Gateway                   |
| TENANT_HOST_PATTERN           | Route 53 Wildcard DNS + Gateway Subdomain Filter         |
| Provider Subaccount           | AWS Account / VPC (Provider)                             |
| Consumer Subaccount           | Tenant record in DB + isolated namespace/schema          |
| onSubscription callback       | Spring Boot Tenant Provisioning Webhook                  |
| getDependencies callback      | Dependency resolution in Tenant Onboarding Service       |
| HDI Container (schema sep.)   | RDS Schema-per-Tenant + Flyway/Liquibase migrations      |
| HANA Instance separation      | RDS Instance-per-Tenant (premium tier)                   |
| Discriminator column          | Hibernate `@Filter` / row-level security in PostgreSQL   |
| BTP Cockpit                   | React Admin Portal (Provider Dashboard)                  |
| Subscription URL              | `{tenant}.saas.yourdomain.com`                           |

---

## File Index

### Core Architecture
| File | Description |
|------|-------------|
| [01_architecture_overview.md](01_architecture_overview.md) | Full system architecture with AWS component diagram |
| [02_tenant_routing.md](02_tenant_routing.md) | Subdomain routing, tenant context extraction |
| [03_authentication_cognito.md](03_authentication_cognito.md) | AWS Cognito multi-tenant auth, JWT, Spring Security |
| [04_tenant_lifecycle.md](04_tenant_lifecycle.md) | Onboarding, offboarding, provisioning automation |
| [05_data_isolation.md](05_data_isolation.md) | Three data separation strategies with implementation |
| [06_spring_boot_implementation.md](06_spring_boot_implementation.md) | Core Spring Boot code: TenantContext, filters, datasource routing |
| [07_react_frontend.md](07_react_frontend.md) | Tenant-aware React.js frontend architecture |
| [08_aws_infrastructure.md](08_aws_infrastructure.md) | AWS services, CDK infrastructure-as-code, cost estimate |

### Architect-Level Concerns (Production-Critical)
| File | Description |
|------|-------------|
| [09_observability_logging.md](09_observability_logging.md) | MDC structured logging, X-Ray tracing, SLO/SLA per tier, metric cardinality |
| [10_resilience_noisy_neighbor.md](10_resilience_noisy_neighbor.md) | Bulkhead, circuit breaker, rate limiting (Bucket4j), DB query timeouts |
| [11_cicd_migrations.md](11_cicd_migrations.md) | Zero-downtime schema migrations, expand-contract pattern, canary rollout |
| [12_billing_metering.md](12_billing_metering.md) | Usage metering, Stripe integration, quota enforcement, plan tiers |
| [13_multiregion_disaster_recovery.md](13_multiregion_disaster_recovery.md) | RTO/RPO targets, Aurora Global DB, Cognito DR, failover runbook |
| [14_audit_compliance.md](14_audit_compliance.md) | Immutable audit trail, GDPR right-to-erasure, CloudTrail, retention policies |
| [15_tenant_migration.md](15_tenant_migration.md) | Schema → dedicated DB upgrade, cross-region migration, zero-downtime cutover |
| [16_local_development.md](16_local_development.md) | Docker Compose, LocalStack, Keycloak, two-tenant local setup |

---

## Quick Architecture Summary

```
Tenant Browser
     │
     ▼
tenant1.app.com  ──► Route 53 (Wildcard *.app.com)
                          │
                          ▼
                    AWS CloudFront (CDN)
                          │
                    ┌─────┴──────┐
                    │            │
              React SPA     API Gateway
           (S3 + CloudFront) (tenant header injected)
                                 │
                           Spring Cloud Gateway
                           (tenant extraction filter)
                                 │
                    ┌────────────┼───────────────┐
                    ▼            ▼               ▼
             Auth Service  Core API       Tenant Registry
            (Cognito+JWT)  (Spring Boot)  (Onboarding API)
                                 │
                    ┌────────────┼───────────────┐
                    ▼            ▼               ▼
              RDS Schema1   RDS Schema2    RDS SchemaN
              (tenant1)     (tenant2)      (tenantN)
```

---

## Key Design Decisions

1. **Schema-per-tenant** as default (balance of isolation vs cost) — upgradable to DB-per-tenant
2. **Wildcard DNS + subdomain routing** for tenant identification (no path-based routing)
3. **Shared Cognito User Pool** with tenant claims in JWT (cost-effective, scalable to 10k tenants)
4. **ThreadLocal TenantContext** propagated through the entire Spring request lifecycle
5. **Event-driven onboarding** via EventBridge for async tenant provisioning
6. **Flyway per-schema migrations** run during tenant onboarding
