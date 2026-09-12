# Scenario 1: Payment Service Crashing Slowly Causes Whole App to Feel Slow

**Interviewer:** "Our payment service pod is crashing, but users are complaining that *everything* is slow, not just payment. Why?"

**You (15-yr Architect):**

This is a classic cascading-latency scenario. Even if `payment-service` isn't fully down, if it's returning errors **slowly** (not instantly), any service configured to call it synchronously — say `checkout-service` — will have its own threads/connections tied up waiting on the slow response, and that backpressure ripples upstream to `frontend`. Without the mesh, you'd have to grep logs across five services to correlate this.

## Diagnosis Flow (ASCII)

```
 Check Kiali / Consul UI topology
            |
            v
 Is payment-service showing HIGH ERROR RATE
 or HIGH p99 LATENCY?
      |                     |
     YES                    NO
      |                     |
      v                     v
 Check outlier detection /   (look elsewhere - maybe
 circuit breaker status       checkout-service itself)
      |
      v
 Is DestinationRule configured
 with reasonable timeouts?
      |                     |
     NO                    YES, but no circuit breaker
      |                     |
      v                     v
 ROOT CAUSE:            ROOT CAUSE:
 default timeout too    unhealthy pod keeps receiving
 high or missing --      traffic - no ejection
 requests hang
```

## Cascading Latency (Sequence Diagram)

```
frontend (FE)          checkout-service (CO)         payment-service (PAY, crashing slowly)
     |                        |                                  |
     |--- request checkout -->|                                  |
     |                        |--- call payment API ------------>|
     |                        |            [pod is failing slowly - errors take
     |                        |             seconds, not instant]
     |                        |<-- slow error / timeout ---------|
     |         [threads/connections held open waiting on payment-service]
     |<-- backpressure (checkout-service now slow too) -----------|
     |                        |                                  |
[frontend appears slow even though only payment-service is unhealthy]
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## The Fix (zero app code changes)

Two mesh-level configs, applied without touching a single line of `payment-service` code:

1. Set an explicit **timeout** (e.g., 2s) on the `payment-service` route so calls fail fast instead of hanging.
2. Configure **outlier detection** so the specific crashing pod gets ejected from the load-balancing pool after N consecutive errors.

## Why This Matters for the Interview

Say this line out loud in your answer — it signals architect-level thinking, not just "I'd restart the pod":

> "Backpressure from one slow dependency doesn't stay contained unless you explicitly bound it with timeouts and circuit breaking. Without those, one struggling service degrades the entire call chain above it."

---
See also: [01-Concepts-Reference.md — Part 4: Traffic Management](01-Concepts-Reference.md#4-traffic-management-canary-retries-circuit-breaking)
