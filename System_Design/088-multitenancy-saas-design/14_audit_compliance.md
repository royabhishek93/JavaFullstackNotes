# Audit Logging & Compliance

## Why Architects Must Own This

Audit logging is not a feature — it's a **compliance obligation** in most regulated industries.
Without it, Enterprise deals don't close. With a flawed implementation, you face GDPR fines.

Core requirement: **immutable, tamper-evident record of who did what to which resource, when, and from where.**

---

## 1. Audit Entry — Data Model

```java
@Entity
@Table(schema = "platform", name = "audit_log")
@Immutable  // Hibernate: this entity is never updated
public class AuditEntry {

    @Id
    @GeneratedValue
    private UUID id;

    // Context
    @Column(nullable = false)
    private String tenantId;

    private String userId;       // null for system actions
    private String userEmail;
    private String userIp;       // from X-Forwarded-For

    // What happened
    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private AuditAction action;  // CREATE, UPDATE, DELETE, LOGIN, EXPORT, etc.

    @Column(nullable = false)
    private String resourceType; // "Order", "User", "TenantConfig"

    private String resourceId;

    // Snapshot (store BEFORE and AFTER for UPDATE operations)
    @Column(columnDefinition = "jsonb")
    private String before;       // JSON of old state

    @Column(columnDefinition = "jsonb")
    private String after;        // JSON of new state

    // Metadata
    @Column(nullable = false)
    private Instant timestamp;

    private String requestId;    // correlates to application logs
    private String serviceId;    // "core-api", "tenant-registry"

    // Integrity
    private String checksum;     // SHA-256(tenantId + action + resourceId + timestamp)
}
```

---

## 2. Audit Service — Write Path

```java
@Service
public class AuditService {

    private final AuditRepository auditRepository;
    private final SqsTemplate sqsTemplate;
    private final ObjectMapper objectMapper;

    // Synchronous audit for critical actions (DELETE, permission changes)
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void recordSync(AuditEvent event) {
        AuditEntry entry = buildEntry(event);
        auditRepository.save(entry);
    }

    // Async audit for high-volume read/write actions (fire-and-forget)
    @Async
    public void recordAsync(AuditEvent event) {
        sqsTemplate.send(auditQueueUrl, buildEntry(event));
    }

    private AuditEntry buildEntry(AuditEvent event) {
        String payload = event.getTenantId() + event.getAction()
            + event.getResourceId() + event.getTimestamp();

        return AuditEntry.builder()
            .tenantId(event.getTenantId())
            .userId(event.getUserId())
            .userEmail(event.getUserEmail())
            .userIp(extractIp())        // from RequestContextHolder
            .action(event.getAction())
            .resourceType(event.getResourceType())
            .resourceId(event.getResourceId())
            .before(toJson(event.getBefore()))
            .after(toJson(event.getAfter()))
            .timestamp(Instant.now())
            .requestId(MDC.get("requestId"))
            .serviceId("core-api")
            .checksum(sha256(payload))  // tamper detection
            .build();
    }
}
```

---

## 3. AOP-Based Auto-Audit — No Boilerplate in Services

```java
// Custom annotation
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Audited {
    AuditAction action();
    String resourceType();
}

// Aspect: intercepts annotated methods, captures before/after state
@Aspect
@Component
public class AuditAspect {

    private final AuditService auditService;

    @Around("@annotation(audited)")
    public Object audit(ProceedingJoinPoint pjp, Audited audited) throws Throwable {
        Object before = captureState(pjp.getArgs()); // snapshot before

        Object result = pjp.proceed(); // execute method

        auditService.recordAsync(AuditEvent.builder()
            .tenantId(TenantContextHolder.getTenantId())
            .userId(SecurityUtils.getCurrentUserId())
            .userEmail(SecurityUtils.getCurrentUserEmail())
            .action(audited.action())
            .resourceType(audited.resourceType())
            .resourceId(extractId(result))
            .before(before)
            .after(result)
            .build());

        return result;
    }
}

// Usage — zero audit boilerplate in the service:
@Audited(action = AuditAction.DELETE, resourceType = "Order")
public void deleteOrder(Long orderId) {
    orderRepository.deleteById(orderId);
}
```

---

## 4. Audit Log — Tenant Self-Service API

Tenant admins can query their own audit log (read-only, their schema only):

```java
@RestController
@RequestMapping("/api/audit")
public class AuditLogController {

    @GetMapping
    @PreAuthorize("hasRole('TENANT_ADMIN')")
    public Page<AuditEntryDto> getAuditLog(
            @RequestParam(required = false) String userId,
            @RequestParam(required = false) AuditAction action,
            @RequestParam(required = false)
            @DateTimeFormat(iso = ISO.DATE_TIME) Instant from,
            @RequestParam(required = false)
            @DateTimeFormat(iso = ISO.DATE_TIME) Instant to,
            Pageable pageable) {

        // Tenant ID comes from TenantContextHolder — tenants can ONLY see their own logs
        String tenantId = TenantContextHolder.getTenantId();

        return auditRepository.search(tenantId, userId, action, from, to, pageable)
            .map(AuditEntryDto::from);
    }

    @GetMapping("/export")
    @PreAuthorize("hasRole('TENANT_ADMIN')")
    public ResponseEntity<Void> exportAuditLog(
            @RequestParam Instant from,
            @RequestParam Instant to) {

        String tenantId = TenantContextHolder.getTenantId();
        String exportKey = auditExportService.exportToS3(tenantId, from, to);

        return ResponseEntity.accepted()
            .header("X-Export-Key", exportKey)
            .build();
    }
}
```

---

## 5. GDPR Compliance Implementation

### Right to Erasure (Article 17)

```java
@Service
public class GdprComplianceService {

    // "Forget me" — anonymize PII but preserve audit trail structure
    @Transactional
    public void eraseUserData(String tenantId, String userId) {
        // Step 1: Anonymize user record (don't delete — breaks foreign keys)
        userRepository.anonymize(userId, tenantId);
        // UPDATE users SET email='deleted@anon', name='Deleted User',
        //   phone=NULL, address=NULL WHERE id=? AND tenant_id=?

        // Step 2: Anonymize audit logs referencing this user
        // Cannot delete audit log rows (compliance requirement)
        // Instead: replace PII fields with anonymized values
        auditRepository.anonymizeUser(tenantId, userId);

        // Step 3: Delete session data from Redis
        redisTemplate.delete("session:" + userId + ":*");

        // Step 4: Remove from Cognito
        cognitoClient.adminDeleteUser(AdminDeleteUserRequest.builder()
            .userPoolId(userPoolId)
            .username(userId)
            .build());

        // Step 5: Record the erasure itself (meta-audit)
        auditService.recordSync(AuditEvent.erasure(tenantId, userId));
    }
}
```

### Data Portability (Article 20)

```java
@Service
public class DataPortabilityService {

    public String exportTenantUserData(String tenantId, String userId) {
        // Collect all user data across tables
        UserExport export = UserExport.builder()
            .user(userRepository.findById(userId))
            .orders(orderRepository.findByUserId(userId))
            .auditLog(auditRepository.findByUserId(tenantId, userId))
            .build();

        // Write as JSON to S3, generate 7-day presigned URL
        String s3Key = "exports/" + tenantId + "/user-" + userId + ".json";
        s3Client.putObject(s3Key, objectMapper.writeValueAsBytes(export));

        return s3Presigner.presignGetObject(s3Key, Duration.ofDays(7)).url();
    }
}
```

---

## 6. Audit Log Retention & Storage

```
┌──────────────────────────────────────────────────────────────────────┐
│ RETENTION POLICY BY COMPLIANCE REQUIREMENT                           │
│                                                                      │
│ General SaaS   → 1 year  (audit_log table in platform schema)        │
│ SOC 2          → 1 year  (required for Type II audit)                │
│ HIPAA          → 6 years (health record audit)                       │
│ PCI-DSS        → 1 year online, 3 years archive                      │
│ GDPR           → as long as purpose exists (but not longer)          │
│ Financial/SEC  → 7 years                                             │
└──────────────────────────────────────────────────────────────────────┘
```

```java
@Scheduled(cron = "0 3 * * 0")  // Sunday 3 AM
public void archiveAuditLogs() {
    Instant cutoff = Instant.now().minus(365, ChronoUnit.DAYS);

    // Move old records from RDS → S3 (cheap, queryable with Athena)
    List<AuditEntry> old = auditRepository.findOlderThan(cutoff);
    s3ArchiveService.write("audit-archive/" + YearMonth.now(), old);
    auditRepository.deleteOlderThan(cutoff); // remove from hot DB
}
```

---

## 7. CloudTrail — AWS Infrastructure Audit

CloudTrail records every AWS API call (who created/deleted RDS, ECS, Cognito users etc.):

```typescript
// CDK: CloudTrail for all accounts/regions
new cloudtrail.Trail(this, 'SaasTrail', {
  trailName: 'saas-platform-trail',
  bucket: auditBucket,
  includeGlobalServiceEvents: true,
  isMultiRegionTrail: true,
  enableFileValidation: true,  // tamper detection
  cloudWatchLogsRetention: logs.RetentionDays.ONE_YEAR,
  managementEvents: cloudtrail.ReadWriteType.ALL,
});
```

Useful CloudTrail queries for incident response:
```sql
-- Who deleted this RDS snapshot?
SELECT userIdentity.arn, eventTime, errorCode
FROM cloudtrail_logs
WHERE eventName = 'DeleteDBClusterSnapshot'
  AND eventTime > '2024-01-15'
ORDER BY eventTime DESC;
```
