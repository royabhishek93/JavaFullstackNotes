# Advanced Scenario 4: Enforcing Mesh Policies via GitOps So a Rogue Team Can't Disable mTLS

**Interviewer:** "How would you enforce mesh policies via GitOps, and prevent a rogue team from disabling mTLS in their namespace?"

**You (15-yr Architect):**

Two layers of defense:

## Layer 1 — GitOps as the Only Path to Production

All mesh CRDs (`PeerAuthentication`, `AuthorizationPolicy`, `ServiceIntentions`) live in Git, applied via ArgoCD/Flux — **no `kubectl apply` by hand in prod**.

## Layer 2 — Admission-Time Guardrail (Defense in Depth)

Use **OPA Gatekeeper / Kyverno admission policies** as a second guardrail that *rejects* any `PeerAuthentication` resource attempting to set `mtls.mode: PERMISSIVE` or `DISABLE` in namespaces tagged as production/regulated — **regardless of what's in Git** — because GitOps alone only protects against process bypass, not a misconfigured PR that gets approved by a reviewer who didn't catch it.

## Enforcement Pipeline (ASCII)

```
  Developer PR
        |
        v
  Code Review
        |
        v
  ArgoCD applies to cluster
        |
        v
  OPA Gatekeeper admission check
        |
   +----+----+
   |         |
   v         v
 Violates   Compliant
 STRICT     |
 mTLS       v
 policy    Applied
   |
   v
 REJECTED at admission,
 never reaches etcd
```

## Why Two Layers, Not Just One

> "GitOps gives you an audit trail and prevents ad-hoc changes, but it doesn't prevent a *bad* change from being merged and applied correctly — a reviewer can approve a PR that quietly weakens mTLS in a namespace. The admission controller is the layer that makes that mistake structurally impossible, not just discouraged. I always design for 'the guardrail survives human error,' not 'the guardrail survives if everyone follows process.'"

---
See also: [19-Scenario-Zero-Downtime-Mesh-Migration.md](19-Scenario-Zero-Downtime-Mesh-Migration.md), [25-Advanced-Multi-Tenant-Platform-Design.md](25-Advanced-Multi-Tenant-Platform-Design.md)
