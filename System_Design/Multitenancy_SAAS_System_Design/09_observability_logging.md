# Observability & Structured Logging

## The Architect's Challenge

In a multitenant system, a single log stream from one service contains activity from ALL tenants.
Without tenant-aware observability you cannot answer:
- "Why is acmecorp's API slow right now?"
- "Which tenant triggered this error spike?"
- "What's the P99 latency for our Enterprise tier?"

---

## 1. Structured Logging with MDC (Mapped Diagnostic Context)

MDC injects fields into **every log line** automatically, without passing them through method signatures.

```java
// Add to TenantContextFilter — runs first on every request
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 1)
public class TenantContextFilter extends OncePerRequestFilter {

    private static final String REQUEST_ID_HEADER = "X-Request-ID";

    @Override
    protected void doFilterInternal(HttpServletRequest req,
                                    HttpServletResponse res,
                                    FilterChain chain)
            throws ServletException, IOException {

        String tenantId  = req.getHeader("X-Tenant-ID");
        String requestId = req.getHeader(REQUEST_ID_HEADER);
        if (requestId == null) requestId = UUID.randomUUID().toString();

        try {
            TenantContextHolder.set(TenantContext.of(tenantId));

            // MDC fields appear in EVERY log line for this thread
            MDC.put("tenantId",  tenantId);
            MDC.put("requestId", requestId);
            MDC.put("userId",    extractUserId(req));

            // Echo requestId back so clients can correlate
            res.setHeader(REQUEST_ID_HEADER, requestId);

            chain.doFilter(req, res);
        } finally {
            MDC.clear();
            TenantContextHolder.clear();
        }
    }
}
```

### Logback JSON Layout (logback-spring.xml)

```xml
<configuration>
  <appender name="JSON_STDOUT" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
      <includeMdcKeyName>tenantId</includeMdcKeyName>
      <includeMdcKeyName>requestId</includeMdcKeyName>
      <includeMdcKeyName>userId</includeMdcKeyName>
      <customFields>{"service":"core-api","env":"prod"}</customFields>
    </encoder>
  </appender>
  <root level="INFO">
    <appender-ref ref="JSON_STDOUT"/>
  </root>
</configuration>
```

Every log line now looks like:
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "message": "Order created: ORD-001",
  "tenantId": "acmecorp",
  "requestId": "a3f2-...",
  "userId": "user-123",
  "service": "core-api",
  "env": "prod"
}
```

CloudWatch Logs Insights query by tenant:
```sql
fields @timestamp, message, requestId
| filter tenantId = "acmecorp" and level = "ERROR"
| sort @timestamp desc
| limit 50
```

---

## 2. Distributed Tracing — AWS X-Ray

Trace a request across: API Gateway → Spring Cloud Gateway → Core API → RDS

```xml
<!-- pom.xml -->
<dependency>
    <groupId>com.amazonaws</groupId>
    <artifactId>aws-xray-recorder-sdk-spring</artifactId>
</dependency>
<dependency>
    <groupId>com.amazonaws</groupId>
    <artifactId>aws-xray-recorder-sdk-sql-postgres</artifactId>
</dependency>
```

```java
@Configuration
public class XRayConfig {

    @Bean
    public Filter xrayFilter() {
        return new AWSXRayServletFilter("core-api");
    }

    @Bean
    public DataSource dataSource(DataSourceProperties props) {
        // Wrap DataSource with X-Ray instrumentation
        DataSource ds = props.initializeDataSourceBuilder().build();
        return new TracingDataSource(ds); // X-Ray SDK wrapper
    }
}
```

Annotate tenant ID on the X-Ray segment — visible in trace:

```java
@Component
public class XRayTenantAnnotationFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest req,
                                    HttpServletResponse res,
                                    FilterChain chain)
            throws ServletException, IOException {

        if (TenantContextHolder.hasContext()) {
            AWSXRay.getCurrentSegment()
                .putAnnotation("tenantId", TenantContextHolder.getTenantId());
        }
        chain.doFilter(req, res);
    }
}
```

X-Ray trace map shows latency breakdown per service, filterable by `tenantId` annotation.

---

## 3. Custom Metrics — Avoid Cardinality Trap

**Cardinality trap**: adding `tenantId` as a CloudWatch dimension means one metric series per tenant.
At 1000 tenants × 10 metrics = 10,000 metric series → high cost and CloudWatch limits hit.

**Safe approach**: use tenant tiers as dimensions, not tenant IDs.

```java
@Component
public class TenantMetrics {

    private final MeterRegistry meterRegistry;
    private final TenantRepository tenantRepository;

    // OK: low cardinality (3 plans max)
    public void recordApiCall(String tenantId, String endpoint, long latencyMs) {
        String plan = tenantRepository.getPlan(tenantId); // cached

        meterRegistry.timer("api.request.duration",
            "plan",     plan,      // FREE / PRO / ENTERPRISE
            "endpoint", normalize(endpoint)  // /orders, /products etc
        ).record(latencyMs, TimeUnit.MILLISECONDS);
    }

    // For per-tenant metrics: use EMF (Embedded Metric Format) to S3/Firehose
    // instead of CloudWatch — query with Athena later (much cheaper)
    public void emitTenantUsage(String tenantId, String metricName, long value) {
        // Write to Firehose → S3 → Athena for offline analytics
        firehoseClient.putRecord(metricName, tenantId, value);
    }

    private String normalize(String endpoint) {
        // /orders/12345 → /orders/{id} to avoid high cardinality
        return endpoint.replaceAll("/[0-9a-f-]{8,}", "/{id}");
    }
}
```

---

## 4. SLO / SLA Definition Per Tenant Tier

```
┌──────────────┬──────────────┬──────────────┬──────────────────────┐
│ Tier         │ Availability │ API P99      │ Alerting             │
├──────────────┼──────────────┼──────────────┼──────────────────────┤
│ FREE         │ 99.5%        │ < 2000ms     │ no dedicated alert   │
│ PRO          │ 99.9%        │ < 800ms      │ PagerDuty P3         │
│ ENTERPRISE   │ 99.99%       │ < 300ms      │ PagerDuty P1         │
└──────────────┴──────────────┴──────────────┴──────────────────────┘
```

CloudWatch Alarm per tier:

```typescript
// CDK — alarm fires only when Enterprise tenants breach P99
new cloudwatch.Alarm(this, 'EnterpriseLatencyAlarm', {
  metric: new cloudwatch.Metric({
    namespace: 'SaasPlatform',
    metricName: 'api.request.duration.p99',
    dimensionsMap: { plan: 'ENTERPRISE' },
    statistic: 'p99',
    period: cdk.Duration.minutes(1),
  }),
  threshold: 300,       // ms
  evaluationPeriods: 3,
  alarmDescription: 'Enterprise P99 latency breached 300ms',
  alarmActions: [pagerDutyP1Topic],
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
});
```

---

## 5. CloudWatch Dashboard — Tenant Health View

```
┌────────────────────────────────────────────────────────────────────┐
│  SaaS Platform — Operational Dashboard                             │
│                                                                    │
│  [Active Tenants: 127]  [Errors (5m): 3]  [P99 Latency: 245ms]   │
│                                                                    │
│  API Latency P99 by Plan         Error Rate by Plan               │
│  ┌──────────────────────────┐    ┌──────────────────────────┐     │
│  │ ENTERPRISE ────────────  │    │                          │     │
│  │ PRO ──────────────────── │    │ Spikes shown here        │     │
│  │ FREE ─────────────────── │    │                          │     │
│  └──────────────────────────┘    └──────────────────────────┘     │
│                                                                    │
│  Active DB Connections           Tenant Onboarding Events (24h)   │
└────────────────────────────────────────────────────────────────────┘
```

---

## 6. Log Retention & Cost Strategy

```
Hot logs  (0–7 days)   → CloudWatch Logs        (fast query, expensive)
Warm logs (7–90 days)  → CloudWatch → S3 export (Logs Insights, moderate)
Cold logs (90d–7yr)    → S3 Glacier             (compliance archive, cheap)

Automated via CloudWatch Logs subscription filter → Firehose → S3
```

```typescript
// CDK: auto-export logs older than 7 days to S3
new logs.LogGroup(this, 'CoreApiLogs', {
  logGroupName: '/ecs/core-api',
  retention: logs.RetentionDays.ONE_MONTH, // CloudWatch retention
  // S3 export handled by Firehose subscription for long-term
});
```
