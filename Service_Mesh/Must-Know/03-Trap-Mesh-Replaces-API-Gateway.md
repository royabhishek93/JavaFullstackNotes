# Trap 1: "Service Mesh Replaces the API Gateway — Can We Delete NGINX/Kong?"

**Interviewer:** "Service mesh replaces the API gateway, right? So we can delete our NGINX/Kong API gateway once we install Istio?"

**Correct Answer: No.**

They solve different problems and are complementary.

```
   NORTH-SOUTH TRAFFIC                    EAST-WEST TRAFFIC
   (external clients -> your system)      (service -> service, INSIDE the cluster)
   ------------------------------          ------------------------------
   Handled by: API Gateway                 Handled by: Service Mesh
   (Kong, NGINX, AWS API Gateway)          (Istio, Consul)

   - API key management                    - Service discovery
   - External rate limiting                - mTLS between services
   - Client-facing API versioning          - Retries/timeouts/circuit breaking
   - Request transformation for partners   - Internal traffic splitting/canary
   - WAF rules                             - Internal observability
```

Istio's own **Ingress Gateway** is a *thin* entry point mechanism, not a full-featured API management product — no built-in developer portal, no API key lifecycle, no monetization features. Many production systems run **both**: API Gateway at the edge for external-facing concerns, service mesh internally for east-west concerns.

## Why This Trap Exists

Interviewers ask this because "gateway" appears in both names (API Gateway, Istio Gateway), and people conflate the two just from vocabulary overlap. The correct answer distinguishes them by **traffic direction and audience** (external clients vs internal services), not by feature overlap.

---
See also: [01-Concepts-Reference.md — Part 7: Istio Gateway vs Ingress](01-Concepts-Reference.md#7-istio-deep-dive-architecture)
