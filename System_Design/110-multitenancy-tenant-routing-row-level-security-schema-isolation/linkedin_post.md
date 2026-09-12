# Multi-Tenant Data Isolation: RLS, Schema-per-Tenant & Database-per-Tenant — LinkedIn Post

## Post Text (copy-paste ready)

Postgres Row-Level Security is OFF by default on every new table you create. Even if RLS is enabled everywhere else in your database.

Here's what that means for multi-tenant SaaS architecture:

- One engineer adds a new table, forgets `ENABLE ROW LEVEL SECURITY` + the policy → any tenant's session can `SELECT *` and see EVERY other tenant's rows. This is the single most common multi-tenant security bug in production.
- Even with a policy in place, table **owners bypass RLS by default** unless you explicitly run `ALTER TABLE ... FORCE ROW LEVEL SECURITY`.
- Shared-schema isolation isn't just a leak risk — it's a noisy-neighbor risk. One tenant's 40-second reporting query, run hourly, pushed every other tenant's p99 latency from 80ms to 3-4 seconds on the same instance.
- Schema-per-tenant caps out at ~1,000-2,000 schemas per Postgres instance before catalog bloat (pg_class/pg_attribute) slows the planner for everyone.
- Migrating 2,000 tenant schemas isn't one migration — it's expand → backfill → dual-write → contract, run per schema, because you can't take 8,000 tenants offline at once for a blocking DDL change.

Swipe → to see the 3 isolation tiers, the exact failure modes, and the decision tree real SaaS platforms use to route tenants between them.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
RLS is OFF by default on every new table. One missing policy = every tenant sees every other tenant's data. Full breakdown 👇

### Variant B — Long (400-600 chars)
Multi-tenant SaaS doesn't run on one isolation model — it runs on three: shared schema + Row-Level Security for the long tail, schema-per-tenant for mid-size accounts, database-per-tenant for enterprise/regulated customers (think: a healthcare tenant bound by data-residency law). The catch? RLS is off by default on new tables, table owners bypass it unless FORCE'd, and one noisy tenant's reporting query can drag another tenant's p99 latency from 80ms to 4 seconds on shared infra. This post breaks down the routing layer, the migration strategy across 2,000 schemas, and every trap engineers hit shipping this in production.

---

## Best Time to Post
Tuesday or Wednesday, 9:00–10:30 AM IST (peak scroll window for Indian tech professionals before standup/sprint planning)

## Engagement Hook
Which tier does your team actually run — shared schema, schema-per-tenant, or a hybrid? And have you ever caught a missing RLS policy before it shipped?
