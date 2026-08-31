# Tenant Lifecycle — Onboarding & Offboarding

## Concept: SAP BTP onSubscription/offSubscription → Spring Boot Provisioning Service

SAP BTP automates tenant lifecycle through `onSubscription` (POST/DELETE) callbacks from the SaaS Provisioning service. We replicate this pattern with a dedicated **Tenant Provisioning Service** and **AWS EventBridge** for async orchestration.

---

## Tenant States

```
         ┌─────────────────────────────────────────────────────────┐
         │                  TENANT STATE MACHINE                    │
         │                                                           │
         │    PENDING_PROVISIONING                                   │
         │           │                                               │
         │    (async provisioning job runs)                          │
         │           │                                               │
         │           ▼                                               │
         │         ACTIVE  ◄──────────── SUSPENDED                  │
         │           │            (re-activate)     │               │
         │           │                              │               │
         │    (admin suspends)──────────────────────►               │
         │           │                                               │
         │    (admin deletes)                                        │
         │           │                                               │
         │           ▼                                               │
         │   PENDING_DELETION                                        │
         │           │                                               │
         │    (data retention period ends - e.g. 30 days)           │
         │           │                                               │
         │           ▼                                               │
         │         DELETED                                           │
         └─────────────────────────────────────────────────────────┘
```

---

## Tenant Entity (Platform Schema)

```java
@Entity
@Table(schema = "platform", name = "tenants")
public class Tenant {

    @Id
    private String tenantId;           // "acmecorp" (subdomain)

    private String displayName;        // "Acme Corporation"
    private String adminEmail;
    private String schemaName;         // "tenant_acmecorp"
    private String plan;               // FREE, PRO, ENTERPRISE

    @Enumerated(EnumType.STRING)
    private TenantStatus status;       // PENDING_PROVISIONING, ACTIVE, SUSPENDED, DELETED

    private LocalDateTime subscribedAt;
    private LocalDateTime provisionedAt;
    private LocalDateTime deletedAt;

    // Cognito app client for this tenant (Strategy B) or null (Strategy A)
    private String cognitoAppClientId;
}
```

---

## Onboarding Flow

```
Provider Admin Dashboard  (or REST API call)
         │
         │  POST /internal/tenants
         │  { "tenantId": "acmecorp", "plan": "PRO",
         │    "adminEmail": "admin@acmecorp.com",
         │    "displayName": "Acme Corp" }
         │
         ▼
Tenant Registry Service
    1. Validate tenantId not taken
    2. Insert tenant record (status=PENDING_PROVISIONING)
    3. Return 202 Accepted + tenantId
    4. Publish TENANT_ONBOARDING_REQUESTED event → EventBridge
         │
         ▼
EventBridge Rule → Lambda (or ECS Task) — Provisioning Worker
    Step 1: createSchema(tenantId)
    Step 2: runMigrations(schemaName)
    Step 3: createCognitoResources(tenantId)
    Step 4: createS3TenantPrefix(tenantId)
    Step 5: sendWelcomeEmail(adminEmail)
    Step 6: updateTenantStatus(ACTIVE)
    Step 7: Publish TENANT_ONBOARDED event → EventBridge
         │
         ▼
Other services subscribe to TENANT_ONBOARDED:
    - Billing service: initialize subscription
    - Notification service: send welcome package
    - Analytics service: set up tenant dashboard
```

---

## TenantProvisioningService — Spring Boot

```java
@Service
@Transactional
public class TenantProvisioningService {

    private final TenantRepository tenantRepository;
    private final SchemaProvisioner schemaProvisioner;
    private final CognitoProvisioner cognitoProvisioner;
    private final S3Provisioner s3Provisioner;
    private final EmailService emailService;
    private final EventBridgePublisher eventPublisher;

    public TenantRegistrationResponse registerTenant(TenantRegistrationRequest req) {
        validateTenantIdAvailable(req.getTenantId());

        Tenant tenant = Tenant.builder()
            .tenantId(req.getTenantId())
            .displayName(req.getDisplayName())
            .adminEmail(req.getAdminEmail())
            .plan(req.getPlan())
            .schemaName("tenant_" + req.getTenantId().replace("-", "_"))
            .status(TenantStatus.PENDING_PROVISIONING)
            .subscribedAt(LocalDateTime.now())
            .build();

        tenantRepository.save(tenant);

        eventPublisher.publish(TenantOnboardingRequestedEvent.of(tenant));

        return TenantRegistrationResponse.builder()
            .tenantId(tenant.getTenantId())
            .status(tenant.getStatus())
            .message("Provisioning started. Tenant will be active within 2 minutes.")
            .build();
    }

    // Called by async provisioning worker
    @EventListener
    public void handleProvisioningRequested(TenantOnboardingRequestedEvent event) {
        String tenantId = event.getTenantId();
        String schemaName = event.getSchemaName();

        try {
            schemaProvisioner.createSchema(schemaName);          // Step 1
            schemaProvisioner.runMigrations(schemaName);         // Step 2
            cognitoProvisioner.createResources(tenantId);        // Step 3
            s3Provisioner.createTenantPrefix(tenantId);          // Step 4
            emailService.sendWelcomeEmail(event.getAdminEmail(), tenantId); // Step 5

            tenantRepository.updateStatus(tenantId,
                TenantStatus.ACTIVE, LocalDateTime.now());

            eventPublisher.publish(TenantOnboardedEvent.of(tenantId));

        } catch (Exception e) {
            // Mark as failed, alert platform admin
            tenantRepository.updateStatus(tenantId, TenantStatus.PROVISIONING_FAILED, null);
            alertService.notifyProvisioningFailure(tenantId, e);
        }
    }
}
```

---

## Schema Provisioner — Dynamic Schema Creation

```java
@Service
public class SchemaProvisioner {

    private final DataSource masterDataSource;
    private final FlywayConfigurer flywayConfigurer;

    public void createSchema(String schemaName) {
        try (Connection conn = masterDataSource.getConnection();
             Statement stmt = conn.createStatement()) {
            // Safe: schemaName is validated (alphanumeric + underscore only)
            stmt.execute("CREATE SCHEMA IF NOT EXISTS " + schemaName);
            stmt.execute("GRANT USAGE ON SCHEMA " + schemaName + " TO app_user");
            stmt.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA " + schemaName
                + " GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user");
        }
    }

    public void runMigrations(String schemaName) {
        // Run Flyway migrations scoped to this tenant's schema
        Flyway flyway = Flyway.configure()
            .dataSource(masterDataSource)
            .schemas(schemaName)
            .locations("classpath:db/migration/tenant")  // tenant-specific migrations
            .table("flyway_schema_history")
            .load();

        flyway.migrate();
    }

    public void dropSchema(String schemaName) {
        try (Connection conn = masterDataSource.getConnection();
             Statement stmt = conn.createStatement()) {
            stmt.execute("DROP SCHEMA IF EXISTS " + schemaName + " CASCADE");
        }
    }
}
```

---

## Offboarding Flow

```
Tenant Admin or Provider Admin
         │
         │  DELETE /internal/tenants/{tenantId}
         │
         ▼
Tenant Registry Service
    1. Check tenant exists and is ACTIVE
    2. Set status = PENDING_DELETION
    3. Record deletion request timestamp
    4. Publish TENANT_OFFBOARDING_REQUESTED event
    5. Return 202 Accepted

EventBridge → Offboarding Worker (runs after 30-day retention)
    Step 1: Revoke all active sessions (Cognito token revocation)
    Step 2: Export tenant data to S3 (30-day accessible archive)
    Step 3: Delete Cognito users for this tenant
    Step 4: Drop tenant schema from RDS
    Step 5: Delete S3 tenant prefix (after 30-day grace period)
    Step 6: Update status = DELETED
    Step 7: Publish TENANT_OFFBOARDED event
```

---

## Offboarding Service

```java
@Service
public class TenantOffboardingService {

    public void initiateOffboarding(String tenantId) {
        Tenant tenant = tenantRepository.findById(tenantId)
            .orElseThrow(() -> new TenantNotFoundException(tenantId));

        if (!TenantStatus.ACTIVE.equals(tenant.getStatus())) {
            throw new IllegalStateException("Only active tenants can be offboarded");
        }

        tenant.setStatus(TenantStatus.PENDING_DELETION);
        tenant.setDeletionRequestedAt(LocalDateTime.now());
        tenantRepository.save(tenant);

        eventPublisher.publish(TenantOffboardingRequestedEvent.of(tenantId));
    }

    // Scheduled job — runs nightly, processes tenants past retention period
    @Scheduled(cron = "0 2 * * *") // 2 AM daily
    public void processPendingDeletions() {
        LocalDateTime retentionCutoff = LocalDateTime.now().minusDays(30);

        List<Tenant> toDelete = tenantRepository
            .findByStatusAndDeletionRequestedAtBefore(
                TenantStatus.PENDING_DELETION, retentionCutoff);

        for (Tenant tenant : toDelete) {
            try {
                cognitoProvisioner.deleteResources(tenant.getTenantId());
                dataArchiver.exportToS3(tenant.getTenantId());
                schemaProvisioner.dropSchema(tenant.getSchemaName());
                s3Provisioner.deleteTenantPrefix(tenant.getTenantId());

                tenant.setStatus(TenantStatus.DELETED);
                tenant.setDeletedAt(LocalDateTime.now());
                tenantRepository.save(tenant);

                eventPublisher.publish(TenantOffboardedEvent.of(tenant.getTenantId()));

            } catch (Exception e) {
                log.error("Failed to delete tenant {}: {}", tenant.getTenantId(), e.getMessage());
            }
        }
    }
}
```

---

## Tenant Subscription REST API

```java
@RestController
@RequestMapping("/internal/tenants")
@PreAuthorize("hasRole('PLATFORM_ADMIN')")
public class TenantManagementController {

    @PostMapping
    public ResponseEntity<TenantRegistrationResponse> register(
            @Valid @RequestBody TenantRegistrationRequest request) {
        return ResponseEntity.status(HttpStatus.ACCEPTED)
            .body(provisioningService.registerTenant(request));
    }

    @GetMapping("/{tenantId}")
    public ResponseEntity<TenantDto> getTenant(@PathVariable String tenantId) {
        return ResponseEntity.ok(tenantService.getTenant(tenantId));
    }

    @PatchMapping("/{tenantId}/suspend")
    public ResponseEntity<Void> suspend(@PathVariable String tenantId) {
        tenantService.suspend(tenantId);
        return ResponseEntity.noContent().build();
    }

    @PatchMapping("/{tenantId}/activate")
    public ResponseEntity<Void> activate(@PathVariable String tenantId) {
        tenantService.activate(tenantId);
        return ResponseEntity.noContent().build();
    }

    @DeleteMapping("/{tenantId}")
    public ResponseEntity<Void> delete(@PathVariable String tenantId) {
        offboardingService.initiateOffboarding(tenantId);
        return ResponseEntity.accepted().build();
    }
}
```

---

## EventBridge Event Schema

```json
{
  "source": "saas.tenant-registry",
  "detail-type": "TENANT_ONBOARDED",
  "detail": {
    "tenantId": "acmecorp",
    "schemaName": "tenant_acmecorp",
    "adminEmail": "admin@acmecorp.com",
    "plan": "PRO",
    "provisionedAt": "2024-01-15T10:30:00Z"
  }
}
```

Other services (billing, analytics, notifications) subscribe via EventBridge rules, decoupled from the tenant registry.
