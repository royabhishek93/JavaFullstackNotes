# Advanced Scenario 6: Using Fault Injection to Validate Resilience Before an Incident Happens

**Interviewer:** "How do you use fault injection to actually validate resilience before an incident happens, not after?"

**You (15-yr Architect):**

This is **chaos engineering** using the mesh's own fault-injection features — no separate chaos tool needed for network-level faults.

## Fault Injection Test Plan (ASCII)

```
  VirtualService fault injection
        |
        +--> Inject 500ms delay on 10% of requests
        |    to payment-service
        |         |
        |         v
        |    Observe: does checkout-service
        |    timeout/circuit-break correctly?
        |
        +--> Inject 5xx abort on 5% of requests
             to shipping-service
                  |
                  v
             Observe: does frontend show a
             graceful error, not a blank crash?
```

## Where to Run This

I'd run this in a staging environment that mirrors prod traffic patterns first (or even in prod, carefully, on a tiny percentage, during low-traffic windows — "chaos in production" is a mature practice at companies like Netflix, popularized by tools like Chaos Monkey).

## The Actual Goal

> "The goal is to prove your timeout/retry/circuit-breaker configuration actually behaves as designed **before** a real outage tests it for you for the first time. If you've never deliberately broken `payment-service` on purpose and watched `checkout-service` handle it gracefully, you don't actually know your resilience configuration works — you're just hoping it does."

## What to Check For During the Test

| Configured Behavior | What "Passing" Looks Like |
|---|---|
| Timeout on payment-service call | `checkout-service` fails fast at the configured timeout, doesn't hang |
| Circuit breaker / outlier detection | After N injected errors, traffic stops being sent to the "unhealthy" instance |
| Retry policy | Retries happen only the configured number of times, don't amplify load |
| Frontend error handling | User sees a graceful degraded-state message, not a raw 500 or blank page |

---
See also: [01-Concepts-Reference.md — Part 4: Traffic Management](01-Concepts-Reference.md#4-traffic-management-canary-retries-circuit-breaking)
