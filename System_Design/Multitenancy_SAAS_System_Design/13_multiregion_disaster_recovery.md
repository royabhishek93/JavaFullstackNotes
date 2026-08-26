# Multi-Region & Disaster Recovery

## RTO / RPO Targets Per Tenant Tier

| Tier | RTO (Recovery Time Objective) | RPO (Recovery Point Objective) | DR Strategy |
|------|-------------------------------|-------------------------------|-------------|
| FREE | 4 hours | 24 hours | Single region, daily backup |
| PRO | 1 hour | 1 hour | Single region, RDS Multi-AZ, hourly snapshot |
| ENTERPRISE | 15 minutes | 5 minutes | Aurora Global DB, cross-region active-passive |

**RTO** = how long the system is down before recovery completes.
**RPO** = how much data is lost (time window of data loss).

---

## 1. Active-Passive vs Active-Active — Multitenant Decision

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ACTIVE-PASSIVE (Recommended for most SaaS)                             │
│                                                                          │
│  us-east-1 (Primary)          us-west-2 (Standby)                       │
│  ┌──────────────────────┐     ┌──────────────────────┐                  │
│  │  ECS + RDS + Cognito │     │  ECS (stopped)       │                  │
│  │  serving all traffic │     │  Aurora replica      │                  │
│  │                      │────►│  (lag < 1s)          │                  │
│  │  Route 53 active     │     │  Route 53 standby    │                  │
│  └──────────────────────┘     └──────────────────────┘                  │
│                                                                          │
│  Failover: Route 53 health check detects failure → DNS flips to standby │
│  Promotion: Aurora replica promoted to writer                            │
│  ECS starts: standby tasks scale up from 0                               │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  ACTIVE-ACTIVE (Only for Enterprise tier / strict latency SLA)           │
│                                                                          │
│  Challenges in multitenant:                                              │
│  - Write conflicts when tenant switches region mid-session               │
│  - Schema migrations must be coordinated across regions                  │
│  - Cognito has no native active-active multi-region                      │
│  - Much higher operational complexity                                     │
│                                                                          │
│  Prefer active-passive unless you have 99.99%+ SLA obligations           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Aurora Global Database — Primary DR Tool

Aurora Global DB replicates at the storage layer — typically < 1 second lag:

```typescript
// CDK: Aurora Global Database for cross-region DR
const globalCluster = new rds.CfnGlobalCluster(this, 'GlobalCluster', {
  globalClusterIdentifier: 'saas-global-cluster',
  engine: 'aurora-postgresql',
  engineVersion: '15.3',
  deletionProtection: true,
});

// Primary region cluster (us-east-1)
const primaryCluster = new rds.DatabaseCluster(this, 'PrimaryCluster', {
  engine: rds.DatabaseClusterEngine.auroraPostgres({
    version: rds.AuroraPostgresEngineVersion.VER_15_3,
  }),
  instanceProps: { instanceType: ec2.InstanceType.of(
    ec2.InstanceClass.R6G, ec2.InstanceSize.XLARGE), vpc },
  storageEncrypted: true,
  backup: { retention: cdk.Duration.days(30) },
});

// Attach secondary region (us-west-2) — done via AWS Console or CLI for cross-region
// aws rds create-db-cluster \
//   --global-cluster-identifier saas-global-cluster \
//   --region us-west-2 \
//   --engine aurora-postgresql \
//   (creates read replica cluster automatically)
```

**Failover time**: ~30-60 seconds for Aurora Global to promote secondary to writer.

---

## 3. Cognito — Multi-Region Challenge

Cognito User Pools are **regional**. No native cross-region replication.

```
Problem: us-east-1 goes down → Cognito is unavailable → users can't authenticate.

Solutions:

Option A — Pre-issue long-lived tokens (simplest)
  - Access tokens: 1 hour (already set)
  - In-flight tokens still valid during failover window
  - Users mid-session continue working for up to 1 hour without re-auth

Option B — Sync users to secondary region (for RTO < 30 min)
  - EventBridge rule: Cognito PostConfirmation trigger → Lambda → replicate
    user to us-west-2 Cognito User Pool
  - Secondary pool has same users, different pool ID
  - DNS failover switches app to secondary pool
  - Limitation: new users created during outage window are lost

Option C — External IdP (Keycloak / Auth0) with replication
  - Keycloak supports active-active clustering
  - More ops overhead but true HA auth
```

---

## 4. S3 Cross-Region Replication

```typescript
// CDK: replicate tenant files bucket to DR region
const primaryBucket = new s3.Bucket(this, 'TenantFilesBucket', {
  bucketName: 'saas-tenant-files-us-east-1',
  versioned: true,          // required for replication
  encryption: s3.BucketEncryption.KMS_MANAGED,
  replicationRules: [
    {
      destination: {
        bucket: s3.Bucket.fromBucketArn(this, 'DrBucket',
          'arn:aws:s3:::saas-tenant-files-us-west-2'),
        storageClass: s3.StorageClass.STANDARD_IA, // cheaper in DR
      },
      filter: { prefix: 'tenants/' },
      enabled: true,
    }
  ],
});
```

---

## 5. Route 53 Health Check — Automated Failover

```typescript
// CDK: health check + failover routing
const healthCheck = new route53.CfnHealthCheck(this, 'ApiHealthCheck', {
  healthCheckConfig: {
    type: 'HTTPS',
    fullyQualifiedDomainName: 'api.yourdomain.com',
    resourcePath: '/actuator/health',
    requestInterval: 10,
    failureThreshold: 2,  // 2 consecutive failures → unhealthy
  },
});

// Primary record (us-east-1)
new route53.ARecord(this, 'PrimaryApi', {
  zone,
  recordName: 'api',
  target: route53.RecordTarget.fromAlias(primaryLoadBalancer),
  comment: 'Primary region',
  setIdentifier: 'primary',
  region: 'us-east-1',
  healthCheck: healthCheck,
  ttl: cdk.Duration.seconds(30), // short TTL for fast failover
});

// Secondary record (us-west-2) — only used when primary is unhealthy
new route53.ARecord(this, 'SecondaryApi', {
  zone,
  recordName: 'api',
  target: route53.RecordTarget.fromAlias(secondaryLoadBalancer),
  setIdentifier: 'secondary',
  region: 'us-west-2',
  ttl: cdk.Duration.seconds(30),
});
```

---

## 6. DR Runbook — Step-by-Step Failover

```
INCIDENT: us-east-1 experiencing RDS or ECS failure affecting >20% of tenants

T+0min  — Alert fires (CloudWatch → PagerDuty)
T+2min  — On-call engineer acknowledges, opens incident channel
T+5min  — Verify: is this a full AZ failure or service-specific?
           - If service-specific → restart ECS tasks, check RDS Multi-AZ
           - If full region failure → initiate DR failover

T+10min — Promote Aurora Global DB secondary to writer (us-west-2):
           aws rds failover-global-cluster \
             --global-cluster-identifier saas-global-cluster \
             --target-db-cluster-identifier saas-secondary-cluster-us-west-2

T+12min — Scale up ECS tasks in us-west-2 (were at 0):
           aws ecs update-service --cluster saas-cluster-dr \
             --service core-api --desired-count 10

T+15min — Verify health checks in us-west-2 pass:
           curl https://api-dr.yourdomain.com/actuator/health

T+18min — Route 53 health check already flipped DNS (automated at T+2min)
           Verify: dig api.yourdomain.com (should return us-west-2 IPs)

T+20min — Communicate to tenants via status page

T+30min — Confirm all SQS queue consumers running in us-west-2
           Re-process any DLQ messages that failed during failover window

RECOVERY (when us-east-1 restored):
  - Do NOT immediately fail back (risk of second disruption)
  - Wait 30+ minutes, verify primary is stable
  - Fail back during low-traffic window
  - Aurora: failover-global-cluster back to us-east-1
  - ECS: scale down us-west-2, scale up us-east-1
  - Update Route 53 health check to point back to us-east-1
```

---

## 7. Data Residency for ENTERPRISE Tenants

Some Enterprise tenants (especially EU) contractually require data to stay in a specific region:

```java
@Entity
@Table(schema = "platform", name = "tenants")
public class Tenant {
    // ...
    private String dataRegion; // "us-east-1", "eu-west-1", "ap-southeast-1"
}
```

For EU tenants:
- Dedicated ECS cluster in `eu-west-1`
- Separate RDS instance in `eu-west-1` (not replicated to US)
- Separate S3 bucket with `eu-west-1` location constraint
- Route 53 geolocation routing: EU traffic → eu-west-1

```java
// Tenant provisioner creates region-appropriate resources
public void provisionTenant(TenantRegistrationRequest req) {
    String region = req.getDataResidencyRegion(); // "eu-west-1"
    if (!region.equals(currentRegion)) {
        // Delegate provisioning to regional service via SNS cross-region message
        regionalProvisioner.delegate(region, req);
        return;
    }
    // Normal provisioning flow...
}
```
