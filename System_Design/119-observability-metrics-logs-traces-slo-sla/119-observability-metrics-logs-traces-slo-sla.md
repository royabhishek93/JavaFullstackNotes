# Observability: Metrics, Logs, Traces, and the SLI/SLO/SLA Framework
### How you know your system is healthy before a customer has to tell you it isn't

---

## PART 1 — THE STUDENT CONVERSATION

Imagine a hospital patient hooked up to monitoring equipment. The bedside monitor shows a continuously updating number: heart rate, 72 BPM. That single number, sampled every second and graphed over time, tells you the patient's CURRENT state and trend at a glance — is the heart rate climbing, dropping, flatlining? That's a **metric**: a numeric time series, cheap to store, cheap to alert on ("page someone if heart rate exceeds 140"), but it only tells you the WHAT, never the WHY.

Now imagine the nurse's handwritten chart notes: "2:14PM, patient reported chest pain, administered medication X." That's a **log**: a detailed, timestamped, textual record of a SPECIFIC EVENT, rich with context but expensive to store at scale and useless for asking "show me the trend of the last six hours" without expensive post-processing.

Neither one alone answers the hardest question: "this ONE patient's heart rate spiked at 2:14PM — walk me through everything that happened to THIS SPECIFIC PATIENT, across every department they visited, in the exact order it happened." That requires stitching together the ER doctor's notes, the radiology department's notes, and the pharmacy's notes, all tied to the SAME patient ID, in causal order. That's a **distributed trace**: a single request's (patient's) complete journey across every service (department) it touched, with a shared identifier (trace ID) carried along the entire path so you can reconstruct the full story after the fact.

The three pillars — metrics, logs, traces — answer three different questions, and a mature system needs all three because none substitutes for the others: metrics tell you SOMETHING is wrong RIGHT NOW (fast, cheap, coarse); logs tell you the DETAILS of a specific thing that happened (rich, but you need to already know roughly where to look); traces tell you WHERE in a chain of 12 microservices the problem actually originated (essential the moment "it's slow" could mean any of a dozen different services, and log-grepping across all twelve manually simply doesn't scale).

This connects directly to a business-facing concept: an **SLI (Service Level Indicator)** is the actual measured metric ("99.95% of requests in the last 28 days completed under 200ms"). An **SLO (Service Level Objective)** is the internal target you hold yourself to ("we aim for 99.9% of requests under 200ms"). An **SLA (Service Level Agreement)** is the external, often contractual, promise to customers, usually looser than your internal SLO on purpose — you want your own alarm to fire BEFORE you've actually breached what you promised a paying customer. The gap between "100% perfect" and your SLO target is your **error budget** — a deliberately-allowed amount of imperfection, and once you understand it as a BUDGET, you get a genuinely useful operational rule: if you've already spent this month's error budget on incidents, that's a legitimate, quantitative reason to freeze risky deploys until next month's budget resets, rather than an vague appeal to "let's be careful."

---

## PART 2 — THE OBSERVABILITY DIAGRAMS

### Distributed Trace: One Request, Many Services, One Trace ID

```
Client request: GET /checkout
  traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
               │                │                    │
               │                └─ trace-id (shared  └─ parent span-id
               │                    across EVERY hop)
               └─ W3C Trace Context header format

Gateway (span: gateway-handle, 12ms)
  │
  ├──> Order Service (span: order-create, 45ms)
  │     │
  │     └──> Inventory Service (span: inventory-check, 8ms)
  │
  ├──> Payment Service (span: charge-card, 210ms)   ← THE SLOW ONE
  │     │
  │     └──> Fraud Service (span: fraud-score, 190ms)  ← ROOT CAUSE FOUND
  │
  └──> Notification Service (span: send-receipt, 5ms, fire-and-forget)

Total request latency: 280ms.
Without tracing: logs from 5 separate services, no shared correlation ID,
  manual timestamp-guessing across services with clock skew.
With tracing: one query "show me trace 4bf92f...", and the waterfall
  view immediately shows fraud-score's 190ms span nested inside
  charge-card's 210ms span — the actual bottleneck is obvious in seconds.
```

### The Three Pillars — Same Incident, Three Views

```
METRIC (fires the alert):
  payment_service_p99_latency_ms > 500   for 5 consecutive minutes
  → PagerDuty alert fires, on-call engineer paged

LOG (first place engineer looks):
  2026-08-31T14:02:11Z ERROR payment-service [traceId=4bf92f...]
    "Fraud service call timed out after 200ms, falling back to
     synchronous manual review queue"
  → tells you WHAT happened at 14:02:11, but not WHY fraud-service
    was slow, or whether this is isolated or systemic

TRACE (root cause):
  trace 4bf92f... waterfall shows fraud-score span = 190ms, and
  querying 50 more traces from the same window shows EVERY fraud-score
  span in this period is 150-200ms, up from a normal baseline of 20ms
  → points straight at fraud-service's OWN dependency (maybe ITS
    database, or a downstream ML model endpoint) as the true root cause
```

### Error Budget Burn-Down

```
SLO: 99.9% of requests succeed over a rolling 30-day window
     → allowed error budget = 0.1% of requests = 43.2 minutes of full
       downtime-equivalent per 30 days

Day 1-20: steady state, minor blips, budget consumed: 10 minutes (23%)
Day 21: major incident, 25 minutes of elevated error rate
        budget consumed: 35 minutes (81% of month's budget!)
Day 22-30: 8.2 minutes of budget left for the rest of the month

Operational rule some teams adopt:
  budget remaining < 20% → freeze non-critical deploys, prioritize
  reliability work over new features until the 30-day window rolls
  forward and the budget resets — a DATA-DRIVEN version of "let's be
  more careful," not a vague policy.
```

---

## PART 3 — INTERNALS AND REAL NUMBERS

### Sampling: You Cannot (and Should Not) Trace Every Request at Scale

```
HEAD-BASED SAMPLING: decide "trace this request or not" at the very
  start (e.g., random 1% of requests, or 100% of requests carrying a
  special debug header). Simple, cheap, but you might sample OUT the
  exact 1-in-10,000 request that later turns out to have errored.

TAIL-BASED SAMPLING: buffer ALL spans for a request temporarily, and
  decide whether to KEEP the full trace only AFTER the request
  completes — e.g., always keep traces that errored or exceeded a
  latency threshold, and randomly sample only 1% of "boring,
  everything-was-fine" traces. Much better signal for debugging real
  problems, but requires buffering and adds collector-side complexity/cost.
```

### SLI/SLO Math (Concrete Example)

```
SLI  = (successful requests) / (total requests) over trailing 28 days
SLO  = 99.95% (internal target, deliberately tighter than the SLA)
SLA  = 99.9%  (external contractual promise — gives you a buffer zone
               between "we breached our own goal" and "we owe the
               customer a service credit")

Error budget (SLO-based) = (1 - 0.9995) × 28 days × 24h × 60min
                          = 0.05% × 40,320 minutes ≈ 20.16 minutes/month

Burn-rate alerting (better than a flat threshold alert):
  "Alert if we're consuming error budget fast enough that we'd EXHAUST
   the entire month's budget in under 6 hours at the current rate" —
  this catches BOTH a sudden severe outage AND a slow, creeping
  degradation, at different alert severities (fast burn = page now,
  slow burn = ticket for tomorrow).
```

### Real Numbers

```
Trace collection overhead (OpenTelemetry SDK, head sampling): typically
  1-5% CPU overhead at low sampling rates (1-10%); tail-based sampling
  adds a buffering/collector cost layer on top, often run as a separate
  aggregation tier before storage.
Metric cardinality cost: a metric with a "userId" label on it (millions
  of unique values) can blow up a metrics backend's storage/query cost
  by orders of magnitude — a very common real production mistake;
  high-cardinality data belongs in logs/traces, not metric labels.
Log retention at scale: raw logs at high volume are frequently
  retained only 7-30 days hot (searchable) and archived to cold/cheap
  storage afterward, precisely because full-fidelity log retention at
  metric-like durations (months/years) is cost-prohibitive.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Customers report checkout is 'sometimes slow.' You have 15 microservices. How do you find the actual bottleneck?"

**You (architect answer):**

> "First, I'd confirm this is really happening and get a quantitative signal from metrics — p50/p95/p99 latency on the checkout endpoint, over time, to see if this is a constant elevated baseline or intermittent spikes, and whether it correlates with traffic volume or a specific time window. Metrics are cheap and fast, so that's where I start, not logs.
>
> Once I know it's real and roughly WHEN it happens, logs alone across 15 services won't scale — I'd be grepping timestamps and guessing at correlation across services with their own clock skew. This is exactly the case for distributed tracing: every request already carries a trace ID through all 15 services via context propagation, so I'd pull up a handful of traces from the affected time window and look at the waterfall view — which single span, nested inside which service, is actually eating the time. In my experience this almost always surfaces one specific downstream dependency, not a diffuse 'everything is a little slow' problem.
>
> Once tracing narrows it to, say, the fraud-scoring service's own dependency, THEN I'd pull its logs for the exact time range and trace ID to get the specific error or slow-query detail — logs are the right tool at that point because I already know precisely where to look, instead of searching blind.
>
> I'd also want this framed against our actual SLO, not just 'slow.' If our SLO is 99.9% of checkout requests under 300ms and we're burning error budget fast enough to exhaust the month's allowance in a few hours, that changes this from a 'nice to fix eventually' ticket into a page-now incident."

---

## PART 5 — DECISION FRAMEWORK

| Question You're Asking | Right Tool | Why |
|---|---|---|
| "Is anything wrong RIGHT NOW?" | Metrics + alerting | Cheap, real-time, coarse-grained, good for paging |
| "What's the trend over the last week?" | Metrics (time series) | Efficient to store/query at that granularity |
| "What exactly happened to THIS ONE request/user?" | Logs (with trace-id correlation) | Rich detail, but need to know roughly where to look first |
| "WHICH of my 15 services is the actual bottleneck?" | Distributed tracing | Only tool that shows causal, cross-service timing in one view |
| "Are we meeting our reliability promise to customers?" | SLI measured against SLO/SLA + error budget | Turns "be careful" into a quantitative, actionable policy |
| "Should we freeze deploys this week?" | Error budget burn rate | Data-driven answer instead of a subjective judgment call |
