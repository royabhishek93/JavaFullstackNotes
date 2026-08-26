# Billing, Metering & Plan Enforcement

## Why Billing Is an Architect Concern

Feature flags (file 07) tell the app what a tenant *can* do.
Billing tells the app what they *have paid for* and whether they are *within quota*.

Without this layer:
- Free tenants use the system unlimited → infrastructure cost exceeds revenue
- Paid tenants hit invisible limits → churn risk
- No revenue visibility → business is flying blind

---

## 1. Usage Metering Architecture

```
API Request                         Billing Service
     │                                    │
     ▼                                    │
TenantContextFilter              ┌────────▼────────┐
     │                           │  Usage Tracker  │
     ▼                           │  (Redis + DB)   │
Request Handler ──USAGE_EVENT──► │                 │
                  (async)        │  Per-tenant      │
                                 │  counters:       │
                                 │  - api_calls     │
                                 │  - active_users  │
                                 │  - storage_gb    │
                                 └────────┬────────┘
                                          │
                                          ▼
                                  Stripe / AWS Marketplace
                                  (subscription + metered billing)
```

---

## 2. Usage Events — Emit Asynchronously

```java
@Component
public class UsageEventEmitter {

    private final SqsTemplate sqsTemplate;

    // Fire-and-forget — never block the request thread for billing
    @Async
    public void recordApiCall(String tenantId, String endpoint) {
        sqsTemplate.send(billingQueueUrl, UsageEvent.builder()
            .tenantId(tenantId)
            .metric(UsageMetric.API_CALL)
            .quantity(1)
            .timestamp(Instant.now())
            .metadata(Map.of("endpoint", endpoint))
            .build());
    }

    @Async
    public void recordStorageUsage(String tenantId, long bytes) {
        sqsTemplate.send(billingQueueUrl, UsageEvent.builder()
            .tenantId(tenantId)
            .metric(UsageMetric.STORAGE_BYTES)
            .quantity(bytes)
            .timestamp(Instant.now())
            .build());
    }
}
```

Aspect to auto-emit on every API call — no boilerplate in services:

```java
@Aspect
@Component
public class UsageMeteringAspect {

    private final UsageEventEmitter emitter;

    @AfterReturning(
        pointcut = "@within(org.springframework.web.bind.annotation.RestController)" +
                   " && execution(* com.saas.api..*(..))",
        returning = "result"
    )
    public void recordApiCall(JoinPoint joinPoint, Object result) {
        if (TenantContextHolder.hasContext()) {
            String endpoint = joinPoint.getSignature().toShortString();
            emitter.recordApiCall(TenantContextHolder.getTenantId(), endpoint);
        }
    }
}
```

---

## 3. Usage Aggregator — Billing Service

```java
@Service
public class UsageAggregatorService {

    private final RedisTemplate<String, Long> redisTemplate;
    private final TenantUsageRepository usageRepository;

    // Called by SQS listener
    public void processUsageEvent(UsageEvent event) {
        String key = usageKey(event.getTenantId(), event.getMetric(),
            YearMonth.now());

        // Increment in Redis (fast, in-memory counter)
        redisTemplate.opsForValue()
            .increment(key, event.getQuantity());

        // Check quota on every increment for API_CALL metric
        if (event.getMetric() == UsageMetric.API_CALL) {
            checkQuotaAndEnforce(event.getTenantId());
        }
    }

    private String usageKey(String tenantId, UsageMetric metric, YearMonth period) {
        return String.format("usage:%s:%s:%s", tenantId, metric.name(),
            period.toString()); // usage:acmecorp:API_CALL:2024-01
    }

    // Nightly job: flush Redis counters → RDS for durable billing records
    @Scheduled(cron = "0 1 * * *")
    public void flushCountersToDb() {
        tenantRepository.findAllActive().forEach(tenant -> {
            for (UsageMetric metric : UsageMetric.values()) {
                String key = usageKey(tenant.getTenantId(), metric, YearMonth.now());
                Long count = redisTemplate.opsForValue().get(key);
                if (count != null && count > 0) {
                    usageRepository.upsert(tenant.getTenantId(), metric,
                        YearMonth.now(), count);
                }
            }
        });
    }
}
```

---

## 4. Plan Limits Definition

```java
public enum PlanLimit {
    FREE(
        100,          // api_calls per day
        5,            // max users
        1_073_741_824 // 1 GB storage
    ),
    PRO(
        100_000,
        50,
        10_737_418_240L  // 10 GB
    ),
    ENTERPRISE(
        Long.MAX_VALUE,  // unlimited
        Long.MAX_VALUE,
        107_374_182_400L // 100 GB (custom per contract)
    );

    final long dailyApiCallLimit;
    final long maxUsers;
    final long maxStorageBytes;
}
```

---

## 5. Quota Enforcement at API Level

```java
@Component
public class QuotaEnforcementFilter extends OncePerRequestFilter {

    private final QuotaService quotaService;

    @Override
    protected void doFilterInternal(HttpServletRequest req,
                                    HttpServletResponse res,
                                    FilterChain chain)
            throws ServletException, IOException {

        if (!TenantContextHolder.hasContext()) {
            chain.doFilter(req, res);
            return;
        }

        String tenantId = TenantContextHolder.getTenantId();
        QuotaStatus status = quotaService.checkQuota(tenantId,
            UsageMetric.API_CALL);

        if (status.isExceeded()) {
            res.setStatus(HttpStatus.PAYMENT_REQUIRED.value()); // 402
            res.getWriter().write(buildQuotaExceededResponse(status));
            return;
        }

        // Warn if approaching limit (80%)
        if (status.getUsagePercent() > 80) {
            res.setHeader("X-Quota-Warning",
                String.format("%.0f%% of daily limit used",
                    status.getUsagePercent()));
        }

        chain.doFilter(req, res);
    }
}

@Service
public class QuotaService {

    public QuotaStatus checkQuota(String tenantId, UsageMetric metric) {
        String plan = tenantRegistry.getPlan(tenantId);
        long limit = PlanLimit.valueOf(plan).getDailyApiCallLimit();

        // Read from Redis (fast — no DB hit on every request)
        String key = "usage:" + tenantId + ":" + metric.name() + ":"
            + LocalDate.now();
        Long used = redisTemplate.opsForValue().get(key);
        long usedCount = (used != null) ? used : 0;

        return QuotaStatus.builder()
            .tenantId(tenantId)
            .metric(metric)
            .limit(limit)
            .used(usedCount)
            .exceeded(usedCount >= limit)
            .usagePercent((double) usedCount / limit * 100)
            .build();
    }
}
```

---

## 6. Stripe Integration — Subscription Lifecycle

```java
@Service
public class StripeSubscriptionService {

    private final Stripe stripeClient;

    // Called during tenant onboarding
    public String createSubscription(String tenantId, String plan,
                                     String stripeCustomerId) {
        SubscriptionCreateParams params = SubscriptionCreateParams.builder()
            .setCustomer(stripeCustomerId)
            .addItem(SubscriptionCreateParams.Item.builder()
                .setPrice(getPriceId(plan))
                .build())
            .setMetadata(Map.of("tenantId", tenantId))
            .setTrialPeriodDays(14L)  // 14-day trial
            .build();

        Subscription subscription = Subscription.create(params);
        tenantRepository.updateStripeSubscriptionId(tenantId,
            subscription.getId());
        return subscription.getId();
    }

    // Webhook handler for Stripe events
    @PostMapping("/webhooks/stripe")
    public ResponseEntity<Void> handleStripeWebhook(
            @RequestBody String payload,
            @RequestHeader("Stripe-Signature") String sigHeader) {

        Event event = Webhook.constructEvent(payload, sigHeader, webhookSecret);

        switch (event.getType()) {
            case "invoice.payment_failed" -> handlePaymentFailed(event);
            case "customer.subscription.deleted" -> handleSubscriptionCancelled(event);
            case "customer.subscription.updated" -> handlePlanChanged(event);
        }

        return ResponseEntity.ok().build();
    }

    private void handlePaymentFailed(Event event) {
        String tenantId = extractTenantId(event);
        // Grace period: 7 days before suspending
        tenantService.scheduleGracePeriod(tenantId, Duration.ofDays(7));
        emailService.sendPaymentFailedNotice(tenantId);
    }

    private void handleSubscriptionCancelled(Event event) {
        String tenantId = extractTenantId(event);
        tenantService.suspend(tenantId);
        // Initiate data retention period before full deletion
        offboardingService.initiateOffboarding(tenantId);
    }
}
```

---

## 7. Billing Dashboard — Tenant Self-Service

```
GET /api/billing/usage

Response:
{
  "tenantId": "acmecorp",
  "plan": "PRO",
  "billingPeriod": "2024-01",
  "usage": {
    "apiCalls": {
      "used": 45230,
      "limit": 100000,
      "percentUsed": 45.2
    },
    "activeUsers": {
      "used": 18,
      "limit": 50,
      "percentUsed": 36.0
    },
    "storageGB": {
      "used": 3.7,
      "limit": 10.0,
      "percentUsed": 37.0
    }
  },
  "nextBillingDate": "2024-02-01",
  "estimatedInvoice": 99.00
}
```

---

## 8. Overage Handling Strategy

```
┌──────────────────┬────────────────────────────────────────────────────────┐
│ Strategy         │ When to use                                            │
├──────────────────┼────────────────────────────────────────────────────────┤
│ Hard stop (402)  │ Free tier — no overage allowed, upgrade to continue    │
│ Soft limit +     │ Pro tier — allow 20% overage, charge $0.001/extra call │
│   metered charge │                                                        │
│ Notify + grace   │ Enterprise — warn tenant, no auto-stop for 30 days     │
│ Auto-upgrade     │ High-growth accounts — upgrade plan automatically      │
└──────────────────┴────────────────────────────────────────────────────────┘
```
