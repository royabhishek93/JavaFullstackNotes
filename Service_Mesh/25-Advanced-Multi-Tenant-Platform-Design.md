# Advanced Scenario 5: 40 Product Teams Sharing One Mesh Without Breaking Each Other

**Interviewer:** "A platform team supports 40 product teams on one shared mesh. How do you give each team autonomy without them breaking each other?"

**You (15-yr Architect):**

This is a **multi-tenancy** design question. My approach has four parts:

## 1. Namespace-Per-Team Boundary

`AuthorizationPolicy`/intentions scoped per-namespace — teams manage their own service-to-service rules within their namespace via a self-service CRD, but a **platform-owned root/mesh-wide policy** enforces non-negotiables:

```
  Platform-owned (non-negotiable, mesh-wide):
    - Default-deny cross-namespace unless explicitly exported/allowed
    - Mandatory STRICT mTLS cluster-wide

  Team-owned (self-service, scoped to their own namespace):
    - Their own AuthorizationPolicy / intentions within their namespace
    - Their own VirtualService/DestinationRule for their own services
```

## 2. Resource Quotas on Sidecar CPU/Memory

Prevent one team's misconfigured proxy (e.g., an accidental unbounded connection pool) from starving a node that other teams' pods also run on.

## 3. RBAC on CRDs

Teams can create `VirtualService`/`DestinationRule` scoped to their own namespace's `Gateway`, but **cannot** touch the shared `Gateway`/ingress config, which is centrally owned by the platform team.

## Namespace / RBAC Isolation Architecture (Diagram)

```
┌─ Platform: Platform Team (mesh-wide, non-negotiable) ─────────────────────┐
│  [RootPolicy] Default-deny cross-namespace + mandatory STRICT mTLS        │
│  [SharedGW]   Shared Gateway / Ingress (centrally owned)                  │
└───────┬──────────────────────────────────────────┬───────────────────────┘
        │ RootPolicy ┄┄"enforces boundary"┄┄> TeamA │ RootPolicy ┄┄"enforces boundary"┄┄> TeamB
        │ SharedGW ──> TeamA                         │ SharedGW ──> TeamB
        v                                            v
┌─ TeamA: Team A namespace (self-service) ────┐   ┌─ TeamB: Team B namespace (self-service) ────┐
│  [AuthA] AuthorizationPolicy (scoped to ns) │   │  [AuthB] AuthorizationPolicy (scoped to ns) │
│  [VSA]   VirtualService/DestinationRule (ns)│   │  [VSB]   VirtualService/DestinationRule (ns)│
│  [SvcA]  Team A services                    │   │  [SvcB]  Team B services                    │
│                                              │   │                                              │
│  AuthA ──> SvcA                             │   │  AuthB ──> SvcB                             │
│  VSA   ──> SvcA                             │   │  VSB   ──> SvcB                             │
└──────────────────────────────────────────────┘   └──────────────────────────────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## 4. Golden Path Helm Chart / Kustomize Base

So teams don't hand-write mesh CRDs incorrectly — they set high-level values (retry count, canary weight), and the platform team's chart renders the compliant CRDs underneath.

```
  Team's simple input:                Platform chart renders:
  ---------------------                ------------------------
  retries: 3                    -->    VirtualService with
  canaryWeight: 10                     correct retry policy,
                                        timeout, canary split,
                                        and mandatory security
                                        defaults baked in
```

## Why This Matters for the Interview

> "At 40 teams, the platform team's real job isn't writing CRDs for people — it's designing the boundary between 'what teams can self-serve' and 'what must stay centrally enforced,' then making the self-service path so easy that nobody is tempted to bypass it and hand-write raw CRDs incorrectly."

---
See also: [23-Advanced-GitOps-Policy-Enforcement.md](23-Advanced-GitOps-Policy-Enforcement.md)
