# CI/CD for Multitenant — Zero-Downtime Migrations

## The Hardest Operational Problem in Multitenant SaaS

In a single-tenant app, a migration runs once. In a multitenant app with 500 tenants,
the same migration must run **500 times** — each against a different schema — during deployment,
without taking the application offline.

---

## 1. The Schema Migration Problem

```
Scenario: Add column `discount_code VARCHAR(50)` to orders table.

Single tenant:   ALTER TABLE orders ADD COLUMN discount_code VARCHAR(50);  ← trivial

Multitenant:
  ALTER TABLE tenant_acmecorp.orders ADD COLUMN discount_code VARCHAR(50);
  ALTER TABLE tenant_globex.orders   ADD COLUMN discount_code VARCHAR(50);
  ALTER TABLE tenant_initech.orders  ADD COLUMN discount_code VARCHAR(50);
  ... × 497 more schemas
```

Naive approach (run all migrations before deploying new code) creates downtime.

---

## 2. Expand-Contract Migration Pattern

The only safe approach for zero-downtime schema changes:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  EXPAND PHASE (backward-compatible — deploy before new code)                │
│                                                                              │
│  V5__add_discount_code.sql:                                                  │
│    ALTER TABLE orders ADD COLUMN discount_code VARCHAR(50);  ← nullable!    │
│    (NOT NULL would break old app reading rows before migration completes)    │
│                                                                              │
│  Deploy: New code is deployed — reads NEW column if present, ignores if not │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                              ▼ (after all tenants migrated)
┌─────────────────────────────────────────────────────────────────────────────┐
│  CONTRACT PHASE (after all tenants on new code)                             │
│                                                                              │
│  V6__enforce_discount_code.sql:                                              │
│    ALTER TABLE orders ALTER COLUMN discount_code SET DEFAULT '';             │
│    UPDATE orders SET discount_code = '' WHERE discount_code IS NULL;         │
│    ALTER TABLE orders ALTER COLUMN discount_code SET NOT NULL;               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Rule**: New column = nullable first. Enforce NOT NULL only after all code handles it.

---

## 3. Rolling Flyway Migration — Background Job at Deploy Time

```java
@Service
public class TenantMigrationOrchestrator {

    private final TenantRepository tenantRepository;
    private final SchemaProvisioner schemaProvisioner;
    private final MigrationStatusRepository statusRepo;

    /**
     * Called by deployment pipeline as a pre-deploy step.
     * Runs asynchronously — does NOT block the app startup.
     */
    @Async("migrationExecutor")
    public CompletableFuture<MigrationReport> migrateAllTenants() {
        List<Tenant> tenants = tenantRepository.findAllActive();
        int success = 0, failed = 0;
        List<String> failures = new ArrayList<>();

        log.info("Starting migration for {} active tenants", tenants.size());

        for (Tenant tenant : tenants) {
            try {
                MigrationResult result = migrateOneTenant(tenant);
                statusRepo.record(tenant.getTenantId(), result);
                success++;
            } catch (Exception e) {
                log.error("Migration failed for tenant {}: {}",
                    tenant.getTenantId(), e.getMessage());
                failures.add(tenant.getTenantId());
                failed++;
                // Continue to next tenant — don't abort the whole batch
            }
        }

        log.info("Migration complete. Success: {}, Failed: {}", success, failed);
        if (!failures.isEmpty()) alertService.notifyMigrationFailures(failures);

        return CompletableFuture.completedFuture(
            new MigrationReport(success, failed, failures));
    }

    private MigrationResult migrateOneTenant(Tenant tenant) {
        Flyway flyway = Flyway.configure()
            .dataSource(masterDataSource)
            .schemas(tenant.getSchemaName())
            .locations("classpath:db/migration/tenant")
            .baselineOnMigrate(false) // schema already exists
            .outOfOrder(false)        // strict version ordering
            .validateOnMigrate(true)
            .load();

        MigrateResult result = flyway.migrate();
        return MigrationResult.of(tenant.getTenantId(),
            result.migrationsExecuted, result.success);
    }
}
```

### Thread Pool for Parallel Migration

```java
@Configuration
public class MigrationAsyncConfig {

    @Bean("migrationExecutor")
    public Executor migrationExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(10);   // migrate 10 schemas in parallel
        executor.setMaxPoolSize(20);
        executor.setQueueCapacity(1000);
        executor.setThreadNamePrefix("tenant-migration-");
        executor.initialize();
        return executor;
    }
}
```

500 tenants ÷ 10 parallel workers = ~50 batches. At 1 sec/migration = ~50 seconds total.

---

## 4. CI/CD Pipeline — Blue-Green Deployment

```
┌────────────────────────────────────────────────────────────────────┐
│                     DEPLOYMENT PIPELINE                             │
│                                                                     │
│  1. Build & Test                                                    │
│     └─ Unit tests, integration tests, TenantIsolationTest           │
│                                                                     │
│  2. Run Expand Migrations (pre-deploy)                              │
│     └─ TenantMigrationOrchestrator.migrateAllTenants()              │
│     └─ Wait for completion / alert on partial failure               │
│                                                                     │
│  3. Deploy NEW version to BLUE environment (ECS task set)           │
│     └─ New ECS task definition registered                           │
│     └─ 0 traffic sent to it yet                                     │
│                                                                     │
│  4. Canary: shift 5% of traffic to BLUE                             │
│     └─ CloudWatch monitors error rate, P99 latency                  │
│     └─ If alarm fires → automatic rollback to GREEN                 │
│                                                                     │
│  5. Gradual shift: 5% → 25% → 50% → 100%                           │
│     └─ 10-minute bake time at each stage                            │
│                                                                     │
│  6. GREEN environment (old version) decommissioned                  │
│                                                                     │
│  7. Run Contract Migrations (post-deploy, if any)                   │
│     └─ Now safe to enforce NOT NULL, drop old columns               │
└────────────────────────────────────────────────────────────────────┘
```

---

## 5. Canary Rollout Per Tenant (Feature Flags via AWS AppConfig)

Release a new feature to specific tenants before all tenants:

```java
@Service
public class FeatureFlagService {

    private final AppConfigClient appConfigClient;

    // Cached config document refreshed every 30s
    private volatile FeatureFlagConfig config;

    public boolean isEnabled(String featureKey, String tenantId) {
        FeatureFlag flag = config.getFlag(featureKey);
        if (flag == null || !flag.isEnabled()) return false;

        // Check if this tenant is in the canary cohort
        return switch (flag.getRolloutStrategy()) {
            case ALL          -> true;
            case TENANT_LIST  -> flag.getEnabledTenants().contains(tenantId);
            case PLAN_TIER    -> flag.getEnabledPlans()
                                    .contains(tenantRegistry.getPlan(tenantId));
            case PERCENTAGE   -> isInPercentageCohort(tenantId, flag.getPercentage());
        };
    }

    private boolean isInPercentageCohort(String tenantId, int pct) {
        // Deterministic: same tenant always in/out of cohort for same %
        int hash = Math.abs(tenantId.hashCode()) % 100;
        return hash < pct;
    }
}
```

AppConfig document example (stored in AWS AppConfig, changed without redeployment):
```json
{
  "new_checkout_flow": {
    "enabled": true,
    "rolloutStrategy": "TENANT_LIST",
    "enabledTenants": ["acmecorp", "pilot-tenant-1"]
  },
  "ai_recommendations": {
    "enabled": true,
    "rolloutStrategy": "PERCENTAGE",
    "percentage": 10
  }
}
```

---

## 6. Rollback Strategy

```
Scenario: Migration V7 ran successfully on 200/500 tenants when a bug was detected.

Options:
  A) Fix-forward:  Write V8 that undoes V7. Apply V8 to all 500 tenants.
     (Preferred — Flyway history is clean)

  B) Selective rollback:  Use Flyway repair + manual SQL on affected tenants.
     (Only if fix-forward is not possible)

  C) App rollback: Deploy previous container image.
     Since V7 was expand-compatible (nullable column), old code works fine
     with new schema. Rollback app → old code + new schema = safe.
```

**Key insight**: Expand-contract pattern makes app rollback safe because the old
application code works with the expanded schema (new nullable column is ignored).

---

## 7. GitHub Actions Pipeline Snippet

```yaml
# .github/workflows/deploy.yml

jobs:
  deploy:
    steps:
      - name: Run tests
        run: mvn test

      - name: Run tenant schema migrations
        run: |
          java -jar tenant-migration-tool.jar \
            --spring.profiles.active=prod \
            --migration.parallel-threads=20
        timeout-minutes: 30

      - name: Deploy to ECS (blue-green)
        run: |
          aws ecs update-service \
            --cluster saas-cluster \
            --service core-api \
            --task-definition core-api:${{ env.NEW_VERSION }} \
            --deployment-configuration \
              "deploymentCircuitBreaker={enable=true,rollback=true},\
               maximumPercent=200,minimumHealthyPercent=100"

      - name: Wait for deployment stabilization
        run: |
          aws ecs wait services-stable \
            --cluster saas-cluster \
            --services core-api
        timeout-minutes: 15

      - name: Run smoke tests against production
        run: ./scripts/smoke-test.sh
```
