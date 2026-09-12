# Rapid-Fire Cheat Sheet

Quick review pass — read top to bottom the night before the interview.

| Question | One-Line Answer |
|---|---|
| What is a service mesh? | Infra layer (control plane + data plane sidecars) handling discovery, security, traffic control, observability outside app code |
| Sidecar pattern? | Proxy container injected alongside app container in the same pod, intercepts all in/out traffic |
| Control plane vs data plane? | Control plane = brain (config/certs/registry); data plane = hands (actual traffic movement via proxies) |
| Istio control plane component? | `istiod` (Pilot+Citadel+Galley merged since 1.5; Mixer removed) |
| Consul control plane component? | Consul Servers (Raft consensus, 3-5 replicas) |
| Data plane proxy in both? | Envoy |
| mTLS purpose? | Encryption + mutual identity verification (not one-way like browser HTTPS) |
| Zero trust = mTLS? | No, mTLS is identity+encryption; Zero Trust also needs explicit authorization policies (default-deny) |
| VirtualService vs DestinationRule? | VS = routing (where); DR = policy (how — LB, circuit breaker, TLS mode, subsets) |
| Consul equivalent of AuthorizationPolicy? | Service Intentions |
| Mesh gateway purpose? | Secure, single ingress/egress point for cross-cluster/cross-DC traffic (not every pod exposed) |
| Cluster peering (Consul)? | Token-based trust establishment between two Consul deployments, enabling cross-cluster service export/failover |
| Canary deployment mechanism? | Weighted traffic split (e.g. 90/10) via VirtualService/service resolver, decouples deploy from release |
| Circuit breaker in mesh terms? | Outlier detection — ejects unhealthy endpoint from LB pool after error threshold, retries later (half-open) |
| Retry storm risk? | Retries amplify load on already-struggling service; must pair with idempotency + circuit breaking |
| Does mesh give full distributed tracing for free? | Spans per hop yes; end-to-end correlation needs app to propagate trace headers |
| PERMISSIVE mTLS mode use case? | Migration period — accept both plaintext and mTLS so non-injected and injected pods can still talk |
| Ambient mesh? | Sidecar-less Istio mode — shared node-level `ztunnel` + optional per-namespace `waypoint` for L7 |
| Does mesh replace API gateway? | No — API gateway = north-south (external), mesh = east-west (internal); often used together |
| App label significance in Istio? | Required for Kiali topology graph / visualization correlation, not for basic traffic to function |
| Sidecar injection on existing pods? | Doesn't retroactively apply — must delete/recreate or rolling-restart pods after enabling injection |
| Control plane outage impact? | Not immediate — Envoy caches last config/certs; new pods & cert rotation & topology updates stop working |
| VM support strength? | Consul historically stronger/native (VM-first heritage); Istio via WorkloadEntry/WorkloadGroup |
| When NOT to use a mesh? | Very small service count (<~10), single team, low language diversity — overhead may not be worth it |
| Canary vs Blue-Green? | Canary = gradual % traffic split, both versions live concurrently; Blue-Green = atomic all-at-once cutover |
| Localhost traffic (app <-> own sidecar) encrypted? | No — plaintext, only the pod-to-pod (sidecar-to-sidecar) hop is mTLS encrypted |
| Outlier detection replaces readiness probes? | No — different layers; readiness = endpoint list membership, outlier detection = short-term LB pool ejection |

## Full File Map

- [`Must-Know/01-Concepts-Reference.md`](Must-Know/01-Concepts-Reference.md) — foundational to advanced architecture, with ASCII diagrams
- `Diagram-01` through `Diagram-09` (root) — 9 key editable `.drawio` architecture diagrams
- [`Must-Know/`](Must-Know/) — 11 files, highest-yield trap + scenario questions (`02`–`07`, `15`–`18`)
- [`Good-to-Know/`](Good-to-Know/) — 11 files, common operational-depth questions (`08`–`12`, `19`–`24`)
- [`Nice-to-Have/`](Nice-to-Have/) — 6 files, niche/staff-level questions (`13`, `14`, `25`–`28`)
- [`30-STAR-Answer-Framework.md`](30-STAR-Answer-Framework.md) — how to structure your spoken answer in the real interview
- [`00-Index.md`](00-Index.md) — full navigable map of this folder
