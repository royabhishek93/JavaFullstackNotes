# Scenario 7: How to Migrate an Existing Production Cluster to a Service Mesh With Zero Downtime

**Interviewer:** "How would you migrate an existing production cluster to add a service mesh with zero downtime?"

**You (15-yr Architect):**

## Migration Plan (ASCII step flow)

```
  1. Install control plane
     (no impact - no pods touched yet)
              |
              v
  2. Enable injection on ONE
     non-critical namespace/service first
              |
              v
  3. Rolling restart that service -
     verify 2/2 containers, check logs, check Kiali
              |
              v
  4. Verify mTLS in PERMISSIVE mode
     (both plaintext and mTLS accepted)
              |
              v
  5. Gradually enable injection
     service by service, canary-style
              |
              v
  6. Once ALL services in mesh,
     flip mTLS to STRICT mode
              |
              v
  7. Apply default-deny authorization,
     then allow-list explicit paths
```

## The Critical Detail: PERMISSIVE mTLS Mode

During migration, some pods have sidecars and some don't — if you force **STRICT** mTLS immediately, any non-injected pod can't talk to an injected one at all (connection refused). **PERMISSIVE mode** lets injected sidecars accept *both* plaintext and mTLS simultaneously, so you can migrate incrementally without an all-or-nothing cutover. Only flip to STRICT once 100% of relevant workloads are in the mesh.

```
  PERMISSIVE mode:
    Non-injected pod --plaintext--> Injected pod (sidecar accepts BOTH) --> OK
    Injected pod --mTLS-----------> Injected pod (sidecar accepts BOTH) --> OK

  STRICT mode (only flip AFTER 100% migrated):
    Non-injected pod --plaintext--> Injected pod (sidecar REJECTS plaintext) --> FAILS
```

## Why This Matters for the Interview

> "The single most common zero-downtime-migration mistake is flipping to STRICT mTLS before every workload has a sidecar. PERMISSIVE mode exists specifically to make incremental rollout safe — treat it as a mandatory intermediate step, not something to skip."

---
See also: [01-Concepts-Reference.md — Part 3: Security](01-Concepts-Reference.md#3-security-mtls-and-zero-trust), [23-Advanced-GitOps-Policy-Enforcement.md](23-Advanced-GitOps-Policy-Enforcement.md)
