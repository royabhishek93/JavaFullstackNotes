# Scenario 2: Canary Rollout Spiked to 40% Errors and Nobody Noticed for 20 Minutes

**Interviewer:** "We rolled out payment-service v3.0 with 10% canary traffic. Error rates for v3.0 spiked to 40%, but nobody noticed for 20 minutes. How do we prevent that next time?"

**You (15-yr Architect):**

Two gaps here: **automated rollback** and **granular alerting**. Since every request through the canary already generates uniform Envoy metrics, this should have triggered an alert on `istio_requests_total{response_code=~"5..",destination_version="v3"}`.

In practice, I'd pair the mesh with a **progressive delivery controller** like Flagger or Argo Rollouts — these tools watch the exact same Prometheus metrics the mesh emits, and automatically **roll back the weight to 0%** if the canary's error rate crosses a threshold, without waiting for a human to look at a dashboard.

## Automated Progressive Delivery (ASCII)

```
  Flagger / Argo Rollouts
        |
        | watches
        v
  Prometheus metrics from Envoy sidecars
        |
        +--- if error rate > threshold --> Automatically set canary weight
        |                                   back to 0% (instant rollback)
        |
        +--- if healthy --> Gradually increase weight
                              10% -> 30% -> 60% -> 100%
```

## Root Cause Breakdown

| Gap | What Should Have Happened |
|---|---|
| No automated rollback | Progressive delivery controller watching live error-rate metrics, auto-reverting weight |
| No granular alert | Alert scoped to `destination_version="v3"` specifically, not just aggregate service health |
| Manual dashboard watching | Replace "someone staring at Grafana" with an automated analysis step (Flagger's built-in metric analysis, or a custom Prometheus alerting rule) |

## Why This Matters for the Interview

> "Canary deployments are only as safe as the automation watching them. A canary with a human-only rollback plan is really just 'deploy and hope someone's awake' — the mesh gives you the signal, but you still need automation consuming that signal to actually get the safety benefit."

---
See also: [01-Concepts-Reference.md — Part 4: Traffic Management](01-Concepts-Reference.md#4-traffic-management-canary-retries-circuit-breaking), [07-Trap-Canary-vs-Blue-Green.md](07-Trap-Canary-vs-Blue-Green.md)
