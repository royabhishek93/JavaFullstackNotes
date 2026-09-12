# Trap 13: "We're a Small Team With 3 Microservices — We Should Definitely Adopt a Full Service Mesh, Right?"

**Interviewer:** "We're a small team with 3 microservices. We should definitely adopt a full service mesh for production-grade resilience."

**Correct Answer: Push back — this is a trap that tests judgment, not mesh knowledge.**

```
  Mesh VALUE scales with:
    - Number of services
    - Diversity of languages/teams
    - Number of independent teams operating them

  Mesh COST includes:
    - Operational overhead of running/upgrading a control plane
    - Learning curve for CRDs (VirtualService, DestinationRule,
      AuthorizationPolicy, etc.)
    - Debugging sidecar-related issues
    - Added latency / resource cost per pod

  At 3 services, ONE team:
    COST often OUTWEIGHS the benefit
```

For 3 services owned by one team, the operational overhead of running and upgrading a mesh control plane, learning CRDs, debugging sidecar issues, and the added latency/resource cost, **often outweighs the benefit**.

## What Might Deliver 80% of the Value at a Fraction of the Cost

- A shared HTTP client library with built-in retries/timeouts (e.g., a common internal SDK)
- A lightweight API gateway if you need traffic control primarily at the edge
- Simple structured logging + a shared tracing library, without needing a full mesh's telemetry pipeline

## Where the Mesh Genuinely Shines

Mesh value scales with the **number of services and the diversity of languages/teams** — it's compelling at **20+ services across multiple teams/languages**, not at 3 services owned by one team.

## Why This Trap Exists

> "A senior architect always asks 'do we actually need this' before reaching for a powerful tool. This question tests whether you'll enthusiastically recommend a technology just because it's the topic of the interview, or whether you'll give an honest, context-dependent recommendation — including 'not yet, here's why, and here's what would change my answer.'"

---
See also: [22-Scenario-Sidecar-Latency-Tax-Business-Justification.md](22-Scenario-Sidecar-Latency-Tax-Business-Justification.md)
