# Tenant Migration — Infrastructure Upgrade

## When Tenant Migration Is Needed

```
Scenario A: PRO tenant upgrades to ENTERPRISE
  → Need to migrate from shared schema (schema-per-tenant)
    to dedicated RDS instance (DB-per-tenant)
  → Zero-downtime, no data loss

Scenario B: EU tenant requires data residency
  → Need to move tenant from us-east-1 to eu-west-1
  → Legal deadline: 30 days

Scenario C: Tenant grows beyond shared RDS capacity
  → Move heavy tenant to dedicated instance
  → Reduce noisy-neighbor impact on shared cluster
```

---

## 1. Shared Schema → Dedicated DB Migration (PRO → ENTERPRISE)

```
┌────────────────────────────────────────────────────────────────────────┐
│  MIGRATION PHASES                                                       │
│                                                                         │
│  Phase 1: Prepare (no downtime)                                         │
│    ├── Provision new RDS instance for tenant                            │
│    ├── Set up pglogical replication: shared DB → new dedicated DB       │
│    └── Let replication catch up (lag < 100ms)                           │
│                                                                         │
│  Phase 2: Cutover (< 30 seconds downtime)                               │
│    ├── Enable maintenance mode for this tenant only                     │
│    ├── Wait for replication lag = 0                                     │
│    ├── Update tenant registry: dataSource = dedicated                   │
│    ├── Clear Redis cache for this tenant                                │
│    └── Disable maintenance mode                                         │
│                                                                         │
│  Phase 3: Verify & Clean up                                             │
│    ├── Run smoke tests against tenant                                   │
│    ├── Monitor for 24 hours                                             │
│    └── Drop old schema from shared DB                                   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. TenantMigrationService — Spring Boot

```java
@Service
public class TenantMigrationService {

    private final TenantRepository tenantRepository;
    private final DedicatedRdsProvisioner rdsProvisioner;
    private final SchemaProvisioner schemaProvisioner;
    private final MaintenanceModeService maintenanceModeService;
    private final RedisTemplate<String, Object> redisTemplate;
    private final DataVerificationService verificationService;

    /**
     * Migrates tenant from shared schema to dedicated RDS instance.
     * Phase 1 (provision + replicate) runs in background.
     * Phase 2 (cutover) is a separate call after replication catches up.
     */
    @Async("migrationExecutor")
    public CompletableFuture<MigrationJob> prepareMigration(String tenantId) {
        Tenant tenant = tenantRepository.findById(tenantId)
            .orElseThrow(() -> new TenantNotFoundException(tenantId));

        MigrationJob job = MigrationJob.builder()
            .tenantId(tenantId)
            .status(MigrationStatus.PROVISIONING)
            .startedAt(Instant.now())
            .build();
        migrationJobRepository.save(job);

        try {
            // Step 1: Provision new dedicated RDS instance
            TenantDbInfo dedicatedDb = rdsProvisioner.provisionDedicatedDb(tenantId);
            job.setDedicatedInstanceId(dedicatedDb.getInstanceId());
            job.setStatus(MigrationStatus.REPLICATING);
            migrationJobRepository.save(job);

            // Step 2: Set up pglogical logical replication
            // Source: shared DB, tenant schema
            // Target: dedicated DB, same schema name
            replicationSetup.createReplicationSlot(
                tenant.getSchemaName(),
                dedicatedDb.getJdbcUrl());

            job.setStatus(MigrationStatus.READY_FOR_CUTOVER);
            migrationJobRepository.save(job);

            alertService.notifyMigrationReadyForCutover(tenantId);

        } catch (Exception e) {
            job.setStatus(MigrationStatus.FAILED);
            job.setError(e.getMessage());
            migrationJobRepository.save(job);
            throw e;
        }

        return CompletableFuture.completedFuture(job);
    }

    /**
     * Phase 2: Perform the actual cutover (< 30s window).
     * Call only after replication lag is confirmed < 100ms.
     */
    @Transactional
    public void performCutover(String tenantId) {
        MigrationJob job = migrationJobRepository.findByTenantId(tenantId)
            .filter(j -> j.getStatus() == MigrationStatus.READY_FOR_CUTOVER)
            .orElseThrow(() -> new IllegalStateException(
                "Tenant not ready for cutover: " + tenantId));

        // Enable maintenance mode for this tenant only (returns 503 with Retry-After)
        maintenanceModeService.enable(tenantId, Duration.ofSeconds(60));

        try {
            // Wait for replication lag to drain completely
            replicationSetup.waitForZeroLag(tenantId, Duration.ofSeconds(25));

            // Switch tenant to dedicated DB in the registry
            tenantRepository.updateDataSource(tenantId,
                DataSourceType.DEDICATED,
                job.getDedicatedInstanceId());

            // Evict ALL cached data for this tenant
            String pattern = "tenant:" + tenantId + ":*";
            redisTemplate.delete(redisTemplate.keys(pattern));

            job.setStatus(MigrationStatus.CUTOVER_COMPLETE);
            migrationJobRepository.save(job);

        } finally {
            maintenanceModeService.disable(tenantId);
        }

        // Async cleanup — drop old schema after 48-hour verification window
        scheduleCleanup(tenantId, Duration.ofHours(48));
    }
}
```

---

## 3. Maintenance Mode — Per-Tenant Only

```java
@Component
public class MaintenanceModeService {

    private final RedisTemplate<String, String> redisTemplate;

    public void enable(String tenantId, Duration duration) {
        redisTemplate.opsForValue().set(
            "maintenance:" + tenantId, "true", duration);
    }

    public void disable(String tenantId) {
        redisTemplate.delete("maintenance:" + tenantId);
    }

    public boolean isUnderMaintenance(String tenantId) {
        return Boolean.parseBoolean(
            redisTemplate.opsForValue().get("maintenance:" + tenantId));
    }
}

// In TenantContextFilter — check before processing any request
if (maintenanceModeService.isUnderMaintenance(tenantId)) {
    res.setStatus(HttpStatus.SERVICE_UNAVAILABLE.value());
    res.setHeader("Retry-After", "30");
    res.getWriter().write("{\"error\":\"Tenant under scheduled maintenance\","
        + "\"retryAfter\":30}");
    return;
}
```

---

## 4. Cross-Region Migration (Data Residency)

```java
@Service
public class CrossRegionMigrationService {

    /**
     * Migrates tenant data from source region to target region.
     * Used when a tenant contractually requires EU data residency.
     */
    public void migrateToRegion(String tenantId, String targetRegion) {
        Tenant tenant = tenantRepository.findById(tenantId)
            .orElseThrow();

        // Step 1: pg_dump of tenant schema to S3
        String dumpKey = "migrations/" + tenantId + "/dump-"
            + Instant.now().toEpochMilli() + ".sql.gz";
        pgDumper.dumpSchema(tenant.getSchemaName(), dumpKey);

        // Step 2: S3 Cross-Region Replication copies dump to target region bucket
        // (CRR configured at bucket level — wait for object to appear in target)
        s3Waiter.waitForObject(targetRegionBucket, dumpKey, Duration.ofMinutes(10));

        // Step 3: Provision target region resources via SNS message to regional service
        regionalProvisioningClient.send(targetRegion,
            ProvisionFromDumpRequest.builder()
                .tenantId(tenantId)
                .dumpS3Key(dumpKey)
                .schemaName(tenant.getSchemaName())
                .build());

        // Step 4: Regional service responds when ready → perform cutover
        // (Event-driven via EventBridge cross-region bus)
    }
}
```

---

## 5. Idempotent Migration Design

Migrations must be safe to retry — network failures or process crashes can interrupt at any point:

```java
@Entity
@Table(schema = "platform", name = "migration_jobs")
public class MigrationJob {

    @Id
    private String tenantId;  // natural key — one active migration per tenant at a time

    @Enumerated(EnumType.STRING)
    private MigrationStatus status;
    // PROVISIONING → REPLICATING → READY_FOR_CUTOVER → CUTOVER_COMPLETE → CLEANUP_DONE

    private String dedicatedInstanceId;
    private String replicationSlotName;
    private Instant startedAt;
    private Instant completedAt;
    private String error;
}
```

Migration steps that check existing state before acting:
```java
// Safe to call twice — no-op if already provisioned
if (rdsClient.describeDBInstances("saas-tenant-" + tenantId).isEmpty()) {
    rdsProvisioner.provisionDedicatedDb(tenantId);
}

// Safe to call twice — Flyway checks migration history
schemaProvisioner.runMigrations(dedicatedSchemaName);
```

---

## 6. Migration Status API — Provider Dashboard

```java
@RestController
@RequestMapping("/internal/tenants/{tenantId}/migration")
@PreAuthorize("hasRole('PLATFORM_ADMIN')")
public class TenantMigrationController {

    @PostMapping("/prepare")
    public ResponseEntity<MigrationJob> prepareMigration(
            @PathVariable String tenantId) {
        return ResponseEntity.accepted()
            .body(migrationService.prepareMigration(tenantId).join());
    }

    @PostMapping("/cutover")
    public ResponseEntity<Void> performCutover(
            @PathVariable String tenantId) {
        migrationService.performCutover(tenantId);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/status")
    public ResponseEntity<MigrationJob> getMigrationStatus(
            @PathVariable String tenantId) {
        return ResponseEntity.ok(migrationJobRepository.findByTenantId(tenantId)
            .orElseThrow());
    }

    @DeleteMapping("/cleanup")
    public ResponseEntity<Void> cleanupOldSchema(
            @PathVariable String tenantId) {
        migrationService.dropOldSchema(tenantId);
        return ResponseEntity.noContent().build();
    }
}
```
