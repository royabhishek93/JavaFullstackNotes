# Multi-Tenant Data Isolation: Row-Level Security, Schema-per-Tenant, and Tenant Routing
### How to keep 10,000 customers' data apart in one database without paying for 10,000 databases

---

## PART 1 — THE STUDENT CONVERSATION

Imagine you're renting out space in a building. You have three ways to do it.

Cheapest option: one big open-plan floor, everyone shares the same rooms, but every desk has a locked drawer and a strict "you may only open drawers labeled with your company name" rule enforced by a security guard standing at every door. That's **shared schema + a `tenant_id` column**, with the "security guard" being Row-Level Security (RLS) — a database-enforced rule that automatically filters every single query so a session can only ever see rows where `tenant_id` matches its own. It's cheap (one building, one set of furniture, thousands of desks) and dense, but the entire safety model rests on the guard never being distracted — if one query path forgets to check the badge (a raw SQL query that bypasses RLS, or a missing `WHERE tenant_id = ?` in application code that isn't backed by RLS), one tenant can read another tenant's data.

Middle option: each company gets its own locked *floor* in the same building — separate space, separate keys, but sharing the building's elevators, electricity, and structural foundation. That's **schema-per-tenant**: every tenant gets their own PostgreSQL schema (`tenant_4521.orders`, `tenant_4521.users`, etc.) inside the *same* database instance. Much stronger isolation — a bug in one tenant's query literally cannot reach another schema's tables without an explicit schema-qualified reference — but now when you ship a new column, you're not running one migration, you're running the same migration once per floor, thousands of times.

Most expensive option: each company gets an entirely separate building. That's **database-per-tenant** — a fully separate database instance (sometimes even separate hardware/region) per tenant. Total physical isolation: no shared connection pool, no shared query planner, no shared disk I/O contention. This is what you reach for when a customer's contract, industry regulation, or sheer scale demands it — a healthcare enterprise tenant subject to HIPAA data-residency rules, or a customer so large their query load would drown out everyone else on a shared instance anyway.

Most real SaaS platforms don't pick one — they run a **hybrid**: the long tail of small customers packed densely into shared schema + RLS, mid-size customers on schema-per-tenant for extra isolation without full operational overhead, and the handful of largest/most regulated enterprise accounts on database-per-tenant. The engineering problem isn't "which one is correct" — it's building a tenant-routing layer that can transparently place a tenant on any of the three tiers and correctly route every request to the right physical location, every time, with zero cross-tenant leakage.

---

## PART 2 — THE MULTI-TENANCY ARCHITECTURE DIAGRAMS

### Request Lifecycle: Subdomain/JWT → TenantContext → DB-Level Filter

```
Incoming HTTP request
  https://acme-corp.myapp.com/api/orders
  Header: Authorization: Bearer eyJhbGciOi...  (JWT claim "tenant_id": "acme-corp")
        │
        v
  ┌─────────────────────────────────────────────┐
  │  TenantResolutionFilter (Servlet Filter)     │
  │  1. Parse subdomain "acme-corp" from Host    │
  │     OR decode JWT claim tenant_id            │
  │  2. Look up TenantMetadata in cache:         │
  │     { tenantId: "acme-corp",                 │
  │       isolationTier: "SCHEMA",               │
  │       schemaName: "tenant_acme_corp",         │
  │       dataSourceKey: "shared-pg-cluster-2" }  │
  │  3. TenantContext.set(tenantId, tier, schema) │
  │     → stored in a ThreadLocal for this        │
  │       request's lifetime                     │
  └─────────────────────────────────────────────┘
        │
        v
  ┌─────────────────────────────────────────────┐
  │  OrderController → OrderService → Repository │
  │  Business logic NEVER references tenant_id   │
  │  explicitly — it's threaded through silently  │
  └─────────────────────────────────────────────┘
        │
        v
  ┌─────────────────────────────────────────────┐
  │  Hibernate Session opened for this request   │
  │  session.enableFilter("tenantFilter")        │
  │    .setParameter("tenantId", "acme-corp")     │
  │  → EVERY query Hibernate issues for this      │
  │    session gets "AND tenant_id = :tenantId"   │
  │    silently appended, even ad-hoc HQL queries │
  └─────────────────────────────────────────────┘
        │
        v
  PostgreSQL: SELECT * FROM orders
              WHERE customer = 'X' AND tenant_id = 'acme-corp'  <- auto-added
        │
        v
  Postgres RLS policy ALSO checks: tenant_id = current_setting('app.tenant_id')
  → belt-and-suspenders: app-level filter AND DB-level policy both must agree
        │
        v
  Response: only acme-corp's rows, even if application code had a bug
```

### Three Isolation Strategies Side by Side

```
(a) SHARED SCHEMA + RLS                (b) SCHEMA-PER-TENANT              (c) DATABASE-PER-TENANT
────────────────────────               ──────────────────────             ───────────────────────
One DB, one schema "public"            One DB instance, N schemas         N separate DB instances

public.orders                          tenant_acme.orders                 db-acme-corp (own instance)
┌────┬───────────┬────────┐            tenant_globex.orders                 └── public.orders
│ id │ tenant_id │ amount │            tenant_initech.orders               db-globex-inc (own instance)
├────┼───────────┼────────┤            ...(one schema per tenant)            └── public.orders
│ 1  │ acme      │ 4999   │            2,000 schemas in one Postgres        (each fully independent:
│ 2  │ globex    │ 1200   │            catalog                              own connections, own
│ 3  │ acme      │ 899    │                                                 storage, own backup/restore,
└────┴───────────┴────────┘            search_path = tenant_acme            own failover)
RLS POLICY enforces:                   → same SQL text works per tenant,
  tenant_id = current session's        connection routed to correct         Used for: enterprise/compliance
  tenant (auto-filtered, cannot        schema via AbstractRoutingDataSource tenants, huge tenants whose
  be bypassed even by raw SQL          or SET search_path per connection    load would dominate a shared
  from an app bug)                                                          instance, data-residency
                                        Migration: run once PER SCHEMA       requirements (must live in a
Density: thousands of tenants          (2,000 schemas = 2,000 migration     specific region/instance)
per instance, cheapest $/tenant        executions, batched/parallelized)
                                                                             Cost: highest $/tenant,
Risk: one missing WHERE clause,       Isolation: strong — cross-schema      full ops overhead per tenant
one RLS policy misconfigured on       queries require explicit schema-
a new table = cross-tenant leak       qualified SQL, accidental leakage
                                       is structurally harder
```

### Edge Case: Missing RLS Policy Leak & Noisy Neighbor

```
FAILURE MODE 1 — the forgotten policy (data leak):
  Engineer adds a new table "invoices" to shared schema.
  Forgets to run:
    ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
    CREATE POLICY invoices_tenant_isolation ON invoices
      USING (tenant_id = current_setting('app.tenant_id')::uuid);

  Result: RLS is OFF by default on new tables. ANY session, regardless of
  app.tenant_id, can SELECT * FROM invoices and see EVERY tenant's invoices.
  This is the single most common multi-tenant security bug in production.
  MITIGATION: CI check that fails the build if any table in the tenant
  schema lacks an RLS policy; a migration template that always pairs
  "CREATE TABLE" with "ENABLE ROW LEVEL SECURITY + CREATE POLICY" as one
  atomic reviewed unit, never two separate PRs.

FAILURE MODE 2 — noisy neighbor:
  Tenant "BigCorp" (shared schema, tier: standard) runs a reporting job
  that issues a 40-second full-table-scan query against the orders table
  every hour. This saturates the shared connection pool and CPU, and
  every OTHER tenant on the same instance sees their p99 API latency
  jump from 80ms to 3-4 seconds during that window.

  MITIGATION:
    - Bulkhead pattern: cap BigCorp's connection pool allocation
      separately from other tenants (see 010-bulkhead-pattern-isolate-
      failures.md) so its query storm cannot exhaust the shared pool.
    - Per-tenant rate limiting on expensive query endpoints (token
      bucket keyed by tenant_id, not just by IP/user).
    - Long-term fix: migrate BigCorp to schema-per-tenant or its own
      read replica once its usage pattern is identified as an outlier.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### PostgreSQL Row-Level Security (Shared Schema)

```sql
-- Enable RLS on the table (OFF by default even after this — need a policy too)
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- Policy: a session can only see/modify rows matching its tenant context
CREATE POLICY tenant_isolation_policy ON orders
  USING (tenant_id = current_setting('app.tenant_id')::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);

-- Force RLS even for the table owner (critical — owners bypass RLS by default!)
ALTER TABLE orders FORCE ROW LEVEL SECURITY;

-- Application sets tenant context per connection/transaction:
SET app.tenant_id = 'acme-corp';
SELECT * FROM orders WHERE customer_name = 'Jane Doe';
-- Postgres silently rewrites this as:
-- SELECT * FROM orders WHERE customer_name = 'Jane Doe'
--   AND tenant_id = 'acme-corp'   <- enforced at the storage engine level

-- Measured overhead: RLS policy evaluation adds ~2-5% query latency
-- versus the same query with no policy, for simple equality-predicate
-- policies (index on tenant_id keeps this cheap).
```

### Hibernate `@Filter` for Session-Level Auto-Filtering

```java
@FilterDef(
    name = "tenantFilter",
    parameters = @ParamDef(name = "tenantId", type = "string")
)
@Filter(name = "tenantFilter", condition = "tenant_id = :tenantId")
@Entity
@Table(name = "orders")
public class Order {
    @Id
    private Long id;
    private String tenantId;
    private BigDecimal amount;
    // ...
}

// Enabled once per Hibernate Session, typically in an interceptor:
@Component
public class TenantHibernateInterceptor implements HandlerInterceptor {

    @PersistenceContext
    private EntityManager entityManager;

    @Override
    public boolean preHandle(HttpServletRequest req, HttpServletResponse res, Object handler) {
        String tenantId = TenantContext.getCurrentTenant();  // set by earlier filter
        Session session = entityManager.unwrap(Session.class);
        session.enableFilter("tenantFilter").setParameter("tenantId", tenantId);
        return true;
    }
}
// From this point, EVERY Hibernate query in the request — HQL, Criteria,
// even lazy-loaded associations — has "AND tenant_id = ?" silently applied.
// This is the app-level safety net; Postgres RLS is the DB-level backstop.
```

### Schema-per-Tenant Routing (Dynamic DataSource)

```java
public class TenantRoutingDataSource extends AbstractRoutingDataSource {
    @Override
    protected Object determineCurrentLookupKey() {
        return TenantContext.getCurrentTenant();  // e.g. "tenant_acme_corp"
    }
}

// Connection-level schema switch (cheaper than N separate DataSources
// when tenant count is in the thousands):
@Override
public Connection getConnection() throws SQLException {
    Connection conn = super.getConnection();
    conn.createStatement().execute(
        "SET search_path TO " + TenantContext.getCurrentTenant() + ", public");
    return conn;
}

/* Operational limits observed in practice:
   - A single PostgreSQL instance comfortably handles ~1,000-2,000 tenant
     schemas before catalog bloat (pg_class, pg_attribute row counts grow
     linearly with schema count) starts slowing planner/catalog lookups.
   - Beyond that, shard tenants across multiple Postgres instances,
     keyed by a tenant→instance mapping in the routing metadata store.
   - Connection pooling MUST be tenant-aware: PgBouncer in transaction-
     pooling mode with SET search_path per transaction, since search_path
     is session state and cannot be blindly reused across tenants in a
     naive shared pool. */
```

### Expand-Contract Migration Across Thousands of Tenant Schemas

```
Goal: add a NOT NULL column "region" to orders across 2,000 tenant schemas,
without taking any tenant offline.

Phase 1 — EXPAND (deploy immediately, zero downtime):
  FOR EACH schema IN tenant_schemas:      -- batched, e.g. 50 schemas in parallel
    ALTER TABLE {schema}.orders
      ADD COLUMN region VARCHAR(20) NULL;   -- nullable, safe, non-blocking
  -- 2,000 schemas x ~150ms DDL each, 50-way parallel batches
  -- ≈ 2,000 / 50 x 150ms ≈ 6 seconds of DDL wall-clock time total

Phase 2 — BACKFILL (background job, throttled):
  UPDATE {schema}.orders SET region = infer_region(shipping_address)
    WHERE region IS NULL
    LIMIT 10000;   -- batched updates to avoid long-running locks/WAL spikes
  -- Repeated per schema until fully backfilled; run during off-peak hours

Phase 3 — DUAL-WRITE (application code deployed BEFORE contract phase):
  orderRepository.save(order);   // writes to BOTH old default logic AND
                                  // explicitly sets `region` going forward
  // Application now tolerant of `region` being present OR null (during
  // the transition window across all 2,000 schemas, which don't all
  // finish backfill at the same instant)

Phase 4 — CONTRACT (weeks later, once ALL schemas confirmed backfilled):
  FOR EACH schema IN tenant_schemas:
    ALTER TABLE {schema}.orders
      ALTER COLUMN region SET NOT NULL;   -- now safe, no more nulls exist

Why this matters: you cannot run one blocking "ADD COLUMN ... NOT NULL"
across 2,000 live tenant schemas simultaneously — some tenants would see
lock contention or downtime while their schema's DDL runs, and a single
mistake in an early schema batch could block the whole rollout. Expand-
contract lets each tenant schema migrate independently, at its own pace,
without ever taking any tenant fully offline.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Design the data isolation model for a B2B SaaS platform. You have 8,000 small customers, 200 mid-size customers, and 5 large enterprise customers — one of whom is in healthcare and has strict data-residency requirements. How do you architect tenant isolation, and how do you migrate schema changes across all of them?"

**You (architect answer):**

> "I wouldn't pick a single isolation model — I'd run a tiered hybrid, because the 8,000 small customers and the 5 enterprise customers have fundamentally different risk and cost profiles.
>
> For the 8,000 small tenants, I'd use shared schema with a `tenant_id` column, enforced by PostgreSQL Row-Level Security as the database-level backstop, plus a Hibernate `@Filter` at the application layer as a defense-in-depth measure — belt and suspenders, so an application bug alone can't leak data past the RLS policy, and a misconfigured policy alone can't leak data past the application filter. This is the cheapest and highest-density option, and it's the right one when the isolation requirement is 'don't let tenants see each other's data' rather than 'physically separate infrastructure.'
>
> For the 200 mid-size customers, I'd move them to schema-per-tenant within the same Postgres cluster — stronger isolation with a much smaller blast radius if something goes wrong, at the cost of running migrations once per schema instead of once globally.
>
> For the 5 enterprise customers, especially the healthcare one with data-residency obligations, I'd go database-per-tenant — potentially a fully separate instance in a specific region for that customer, full physical isolation, independent backup and failover.
>
> A resolved tenant-routing layer sits in front of all three tiers: an incoming request's subdomain or JWT claim resolves to a `TenantContext` that carries not just the tenant ID but its isolation tier and physical location, and the persistence layer routes accordingly — the business logic code never has to know or care which tier a given tenant is on.
>
> For schema migrations, I'd use the expand-contract pattern universally: add new columns nullable first, backfill in a background job, deploy code that tolerates both old and new states, and only drop old columns or add NOT NULL constraints once every tenant — across all three tiers — has confirmed migration. You cannot take 8,000 tenants offline simultaneously for a blocking schema change.
>
> The operational concern I'd flag immediately is noisy-neighbor risk within the shared-schema tier — one of those 8,000 small tenants running an expensive reporting query can degrade everyone else sharing that instance. I'd mitigate this with the bulkhead pattern — capping each tenant's share of the connection pool — plus per-tenant rate limiting on expensive endpoints, so one tenant's usage spike is contained rather than cascading into a platform-wide incident."

---

## PART 5 — DECISION FRAMEWORK

### Isolation Strategy Comparison

| Approach | How It Works | Tradeoff | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **Shared schema + tenant_id + RLS** | One schema, `tenant_id` column, DB policy auto-filters every query | Cheapest, highest density; isolation depends on RLS + app filter both being correct | Baseline (+2-5% RLS overhead) | Low-Medium | Missing RLS policy on a new table = silent cross-tenant leak |
| **Shared schema + tenant_id, no RLS (app-filter only)** | App code adds `WHERE tenant_id = ?` manually everywhere | Cheapest, but zero DB-level backstop | Baseline | Low | One forgotten WHERE clause anywhere in the codebase = leak; anti-pattern for anything sensitive |
| **Schema-per-tenant** | One Postgres schema per tenant, same instance, routed via `search_path`/DataSource | Strong isolation, but N migrations instead of 1; catalog bloat past ~1-2K schemas | Baseline, negligible per-schema overhead | Medium | Migration script fails on schema #1,743 of 2,000 — partial rollout state to reconcile |
| **Database-per-tenant** | Fully separate DB instance per tenant | Total physical isolation, highest cost/ops overhead, easiest compliance story | Baseline (own resources, no contention) | High | Ops overhead scales linearly with tenant count; expensive for long-tail small tenants |

### When Each Tier Is Right

```
Shared schema + RLS is right when:
  ✓ Large number of small/low-risk tenants, cost-per-tenant must stay low
  ✓ No hard regulatory/data-residency requirement demanding physical separation
  ✓ You can enforce RLS-by-default via migration tooling/CI checks

Schema-per-tenant is right when:
  ✓ Mid-size tenants need stronger isolation guarantees than RLS alone
  ✓ You want blast-radius containment (a bug affects one schema, not all data)
  ✓ Tenant count is bounded enough to keep catalog size manageable (~1-2K/instance)

Database-per-tenant is right when:
  ✓ Regulatory/compliance/data-residency mandates physical separation
  ✓ A single tenant's load would dominate a shared instance anyway
  ✓ Customer contract explicitly requires dedicated infrastructure

Skip full isolation tiers when:
  ✗ You're pre-product-market-fit — shared schema + RLS is enough, don't
    over-engineer database-per-tenant for 12 customers
  ✗ The "isolation" need is really just per-tenant configuration, not data
    separation — a feature-flag/config table solves that more cheaply
```

---

## QUICK REFERENCE CARD

```
ROW-LEVEL SECURITY (shared schema):
  ALTER TABLE t ENABLE ROW LEVEL SECURITY;
  ALTER TABLE t FORCE ROW LEVEL SECURITY;   -- also applies to table owner!
  CREATE POLICY p ON t USING (tenant_id = current_setting('app.tenant_id')::uuid);
  SET app.tenant_id = '<tenant>';           -- per session/transaction

HIBERNATE APP-LEVEL FILTER:
  @FilterDef(name="tenantFilter", parameters=@ParamDef(name="tenantId", type="string"))
  @Filter(name="tenantFilter", condition="tenant_id = :tenantId")
  session.enableFilter("tenantFilter").setParameter("tenantId", tenantId);

SCHEMA-PER-TENANT ROUTING:
  class TenantRoutingDataSource extends AbstractRoutingDataSource
  determineCurrentLookupKey() -> TenantContext.getCurrentTenant()
  SET search_path TO tenant_<id>, public;

EXPAND-CONTRACT MIGRATION (per-tenant-schema rollout):
  1. EXPAND:   ADD COLUMN nullable
  2. BACKFILL: batched UPDATE, throttled
  3. DUAL-WRITE: app tolerates old + new state
  4. CONTRACT: SET NOT NULL / DROP old column (only after 100% migrated)

OPERATIONAL LIMITS:
  ~1,000-2,000 tenant schemas per Postgres instance before catalog bloat
  RLS overhead: ~2-5% added query latency
  Noisy neighbor mitigation: bulkhead (connection pool cap) + per-tenant
  rate limiting — see 010-bulkhead-pattern-isolate-failures.md
```
