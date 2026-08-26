# AWS Infrastructure — Services, CDK & Operations

## Complete AWS Services Map

```
┌─────────────────────────────────────────────────────────────────┐
│                     AWS SERVICES USED                           │
│                                                                  │
│  NETWORKING & ROUTING                                            │
│  ├── Route 53         Wildcard DNS *.app.yourdomain.com         │
│  ├── CloudFront       CDN, SSL termination, WAF                 │
│  ├── ACM              Wildcard SSL certificate                  │
│  └── VPC              Private subnets for ECS + RDS             │
│                                                                  │
│  COMPUTE                                                         │
│  ├── ECS Fargate      Spring Boot services (no EC2 mgmt)        │
│  ├── ECR              Docker image registry                      │
│  └── Lambda           Cognito authorizer, event processors      │
│                                                                  │
│  API MANAGEMENT                                                  │
│  └── API Gateway      REST API, throttling, Cognito auth        │
│                                                                  │
│  AUTHENTICATION                                                  │
│  └── Cognito          User Pools, hosted UI, JWT tokens         │
│                                                                  │
│  DATABASE & CACHE                                                │
│  ├── RDS PostgreSQL   Multi-AZ, schema-per-tenant               │
│  ├── RDS Proxy        Connection pooling across tenants         │
│  └── ElastiCache      Redis — session cache, tenant config      │
│                                                                  │
│  STORAGE                                                         │
│  ├── S3               SPA hosting, tenant files, exports        │
│  └── Secrets Manager  DB credentials, API keys per tenant      │
│                                                                  │
│  MESSAGING & EVENTS                                              │
│  ├── EventBridge      Tenant lifecycle events                   │
│  ├── SQS              Async job queues                          │
│  └── SNS              Notifications, alerting                   │
│                                                                  │
│  EMAIL                                                           │
│  └── SES              Tenant welcome emails, invitations        │
│                                                                  │
│  OBSERVABILITY                                                   │
│  ├── CloudWatch       Logs, metrics, alarms                     │
│  ├── X-Ray            Distributed tracing                       │
│  └── CloudWatch RUM   Real User Monitoring (frontend)           │
│                                                                  │
│  SECURITY                                                        │
│  ├── WAF              SQL injection, XSS, rate limit rules      │
│  ├── Shield           DDoS protection                           │
│  ├── IAM              Service roles, least-privilege            │
│  └── KMS              Encryption at rest (RDS, S3)              │
│                                                                  │
│  INFRASTRUCTURE AS CODE                                          │
│  └── AWS CDK (TS)     Full stack provisioning                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## AWS CDK Stack Structure

```typescript
// bin/app.ts — entry point
const app = new cdk.App();

new NetworkingStack(app, 'SaasNetworking', { env });
new DatabaseStack(app, 'SaasDatabase', { env });
new AuthStack(app, 'SaasAuth', { env });
new ComputeStack(app, 'SaasCompute', { env });
new FrontendStack(app, 'SaasFrontend', { env });
new ObservabilityStack(app, 'SaasObservability', { env });
```

---

## Networking Stack

```typescript
export class NetworkingStack extends Stack {
  public readonly vpc: ec2.Vpc;

  constructor(scope: Construct, id: string, props: StackProps) {
    super(scope, id, props);

    this.vpc = new ec2.Vpc(this, 'SaasVpc', {
      maxAzs: 3,
      natGateways: 2,  // 2 for HA, in different AZs
      subnetConfiguration: [
        { cidrMask: 24, name: 'Public',   subnetType: ec2.SubnetType.PUBLIC },
        { cidrMask: 24, name: 'Private',  subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
        { cidrMask: 28, name: 'Database', subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      ],
    });

    // Wildcard DNS record
    const zone = route53.HostedZone.fromLookup(this, 'Zone', {
      domainName: 'yourdomain.com',
    });

    // ACM wildcard certificate (DNS validated)
    const cert = new acm.Certificate(this, 'WildcardCert', {
      domainName: '*.app.yourdomain.com',
      subjectAlternativeNames: ['app.yourdomain.com', 'admin.yourdomain.com'],
      validation: acm.CertificateValidation.fromDns(zone),
    });
  }
}
```

---

## Database Stack

```typescript
export class DatabaseStack extends Stack {

  constructor(scope: Construct, id: string, props: DatabaseStackProps) {
    super(scope, id, props);

    const dbSg = new ec2.SecurityGroup(this, 'DbSg', { vpc: props.vpc });

    // Only allow connections from the private subnet (ECS tasks)
    dbSg.addIngressRule(ec2.Peer.ipv4(props.vpc.vpcCidrBlock),
      ec2.Port.tcp(5432));

    // RDS PostgreSQL Multi-AZ
    const db = new rds.DatabaseInstance(this, 'SaasDb', {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_15_3,
      }),
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.R6G, ec2.InstanceSize.XLARGE),
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      securityGroups: [dbSg],
      multiAz: true,
      storageEncrypted: true,
      backupRetention: cdk.Duration.days(30),
      deletionProtection: true,
      enablePerformanceInsights: true,
      cloudwatchLogsExports: ['postgresql'],
      parameters: {
        'log_statement': 'all',
        'log_min_duration_statement': '1000', // log slow queries > 1s
      },
    });

    // RDS Proxy — connection pooling for multitenant connection efficiency
    new rds.DatabaseProxy(this, 'SaasDbProxy', {
      proxyTarget: rds.ProxyTarget.fromInstance(db),
      secrets: [db.secret!],
      vpc: props.vpc,
      iamAuth: true,              // IAM token auth — no password rotation needed
      maxConnectionsPercent: 90,
      requireTLS: true,
    });
  }
}
```

---

## Compute Stack (ECS Fargate)

```typescript
export class ComputeStack extends Stack {

  constructor(scope: Construct, id: string, props: ComputeStackProps) {
    super(scope, id, props);

    const cluster = new ecs.Cluster(this, 'SaasCluster', {
      vpc: props.vpc,
      containerInsights: true,  // CloudWatch Container Insights
    });

    // Core API Service
    this.createFargateService(cluster, {
      name: 'core-api',
      image: 'core-api:latest',
      port: 8080,
      cpu: 1024,
      memory: 2048,
      desiredCount: 2,
      minCapacity: 2,
      maxCapacity: 20,
      environment: {
        SPRING_PROFILES_ACTIVE: 'prod',
        DB_PROXY_ENDPOINT: props.dbProxyEndpoint,
      },
    });

    // Tenant Registry Service
    this.createFargateService(cluster, {
      name: 'tenant-registry',
      image: 'tenant-registry:latest',
      port: 8081,
      cpu: 512,
      memory: 1024,
      desiredCount: 2,
    });
  }

  private createFargateService(
    cluster: ecs.Cluster,
    config: ServiceConfig
  ): ecs.FargateService {

    const taskDef = new ecs.FargateTaskDefinition(this, `${config.name}-task`, {
      cpu: config.cpu,
      memoryLimitMiB: config.memory,
      taskRole: this.createTaskRole(config.name),
    });

    taskDef.addContainer(config.name, {
      image: ecs.ContainerImage.fromEcrRepository(
        ecr.Repository.fromRepositoryName(this, `${config.name}-repo`,
          config.name), 'latest'),
      portMappings: [{ containerPort: config.port }],
      environment: config.environment,
      secrets: {
        DB_PASSWORD: ecs.Secret.fromSecretsManager(
          secretsmanager.Secret.fromSecretNameV2(this, 'DbSecret', 'saas/db')),
      },
      logging: new ecs.AwsLogDriver({
        streamPrefix: config.name,
        logRetention: logs.RetentionDays.THREE_MONTHS,
      }),
      healthCheck: {
        command: ['CMD-SHELL',
          `curl -f http://localhost:${config.port}/actuator/health || exit 1`],
        interval: cdk.Duration.seconds(30),
        retries: 3,
      },
    });

    const service = new ecs.FargateService(this, `${config.name}-svc`, {
      cluster,
      taskDefinition: taskDef,
      desiredCount: config.desiredCount,
      assignPublicIp: false,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
    });

    // Auto-scaling
    const scaling = service.autoScaleTaskCount({
      minCapacity: config.minCapacity ?? 2,
      maxCapacity: config.maxCapacity ?? 10,
    });

    scaling.scaleOnCpuUtilization('CpuScaling', {
      targetUtilizationPercent: 70,
      scaleInCooldown: cdk.Duration.seconds(120),
    });

    scaling.scaleOnRequestCount('RequestScaling', {
      requestsPerTarget: 1000,
      targetGroup: service.loadBalancerTarget({ containerName: config.name }),
    });

    return service;
  }
}
```

---

## EventBridge — Tenant Lifecycle Events

```typescript
// CDK: EventBridge rules for tenant events
const bus = new events.EventBus(this, 'SaasBus', {
  eventBusName: 'saas-platform',
});

// Rule: TENANT_ONBOARDED → Billing Service
new events.Rule(this, 'TenantOnboardedBilling', {
  eventBus: bus,
  eventPattern: {
    source: ['saas.tenant-registry'],
    detailType: ['TENANT_ONBOARDED'],
  },
  targets: [new eventsTargets.SqsQueue(billingQueue)],
});

// Rule: TENANT_ONBOARDED → Analytics Service
new events.Rule(this, 'TenantOnboardedAnalytics', {
  eventBus: bus,
  eventPattern: {
    source: ['saas.tenant-registry'],
    detailType: ['TENANT_ONBOARDED'],
  },
  targets: [new eventsTargets.SqsQueue(analyticsQueue)],
});

// Rule: TENANT_OFFBOARDED → Data archival Lambda
new events.Rule(this, 'TenantOffboarded', {
  eventBus: bus,
  eventPattern: {
    source: ['saas.tenant-registry'],
    detailType: ['TENANT_OFFBOARDED'],
  },
  targets: [new eventsTargets.LambdaFunction(archivalLambda)],
});
```

---

## Observability — CloudWatch Dashboard

Key metrics to monitor per tenant:

```typescript
const dashboard = new cloudwatch.Dashboard(this, 'SaasDashboard', {
  dashboardName: 'SaasPlatform',
});

dashboard.addWidgets(
  // API latency per tenant (custom metric from Spring)
  new cloudwatch.GraphWidget({
    title: 'API Latency P99 by Tenant',
    left: [
      new cloudwatch.Metric({
        namespace: 'SaasPlatform',
        metricName: 'ApiLatencyP99',
        dimensionsMap: { Service: 'core-api' },
        statistic: 'p99',
      }),
    ],
  }),

  // Active tenants
  new cloudwatch.SingleValueWidget({
    title: 'Active Tenants',
    metrics: [new cloudwatch.Metric({
      namespace: 'SaasPlatform',
      metricName: 'ActiveTenants',
    })],
  }),

  // DB connections via RDS Proxy
  new cloudwatch.GraphWidget({
    title: 'DB Connection Pool Usage',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/RDS',
        metricName: 'DatabaseConnections',
      }),
    ],
  })
);
```

Custom Spring Boot metrics:

```java
@Component
public class TenantMetrics {

    private final MeterRegistry meterRegistry;

    public void recordApiCall(String tenantId, String endpoint, long latencyMs) {
        meterRegistry.timer("api.latency",
            "tenant", tenantId,
            "endpoint", endpoint
        ).record(latencyMs, TimeUnit.MILLISECONDS);
    }

    public void incrementActiveUsers(String tenantId) {
        meterRegistry.gauge("tenant.active_users",
            Tags.of("tenant", tenantId),
            activeUserCount.get(tenantId));
    }
}
```

---

## Cost Estimation (Monthly, 50 Tenants)

| Service | Config | Est. Cost |
|---------|--------|-----------|
| ECS Fargate (Core API) | 2 tasks × 1vCPU/2GB | ~$80 |
| ECS Fargate (Gateway) | 2 tasks × 0.5vCPU/1GB | ~$30 |
| RDS PostgreSQL Multi-AZ | db.r6g.xlarge | ~$400 |
| RDS Proxy | included with RDS | ~$20 |
| ElastiCache Redis | cache.r6g.large | ~$130 |
| Cognito | < 50k MAU | ~$0 (free tier) |
| CloudFront | 100GB/month transfer | ~$10 |
| API Gateway | 10M requests/month | ~$35 |
| Route 53 | 1 hosted zone | ~$1 |
| S3 | 100GB storage | ~$5 |
| EventBridge | 1M events | ~$1 |
| CloudWatch | Logs + metrics | ~$20 |
| **Total** | | **~$730/month** |

Shared across 50 tenants = **~$15/tenant/month** fixed infrastructure cost.
Profitable at any plan price above ~$30/month.

---

## Security Checklist

```
Infrastructure:
  ✓ All RDS traffic encrypted in transit (SSL) and at rest (KMS)
  ✓ S3 server-side encryption with KMS
  ✓ Secrets in AWS Secrets Manager (never in env vars or code)
  ✓ VPC — RDS in isolated subnets, ECS in private subnets
  ✓ WAF rules: SQL injection, XSS, rate limiting per IP

Application:
  ✓ Cross-tenant access check: JWT tenantId must match subdomain
  ✓ Schema isolation: search_path set on every request
  ✓ TenantContextHolder.clear() in finally block
  ✓ Tenant schema names validated (alphanumeric + underscore only)
  ✓ RLS as secondary defense for discriminator-column mode
  ✓ No tenant data in logs (mask PII)

Auth:
  ✓ JWT validated using Cognito JWKS (not shared secret)
  ✓ Access tokens: 60-minute expiry
  ✓ Refresh tokens: httpOnly cookie (not localStorage)
  ✓ PKCE enforced on Cognito app client
  ✓ Self-signup disabled — invitation only
```
