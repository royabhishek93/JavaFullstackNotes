# Service Mesh Interview Prep — Master Index (Istio + Consul, 15-Year Architect Level)

Files are grouped into **three tier folders by interview importance**, so you can prioritize your study time:

- **[`Must-Know/`](Must-Know/)** — highest-yield content. If you only have limited prep time, master this folder completely.
- **[`Good-to-Know/`](Good-to-Know/)** — commonly asked, adds real depth and operational credibility.
- **[`Nice-to-Have/`](Nice-to-Have/)** — niche/staff-level or emerging-tech topics. Read these last, for the extra edge.

Filenames keep their original interview-priority number (`01`–`28`) even across folders, so you always know the relative rank of a file no matter which tier it's in. Diagrams (prefixed `Diagram-`) and final-prep files stay at this root level since they're referenced from all three tiers.

## 0. Prerequisite — Concepts (read this first, regardless of tier)

📄 [`Must-Know/01-Concepts-Reference.md`](Must-Know/01-Concepts-Reference.md) — one combined, conversational file covering:
1. Why Does Service Mesh Even Exist
2. Sidecar Pattern, Control Plane vs Data Plane
3. Security: mTLS and Zero Trust
4. Traffic Management: Canary, Retries, Circuit Breaking
5. Observability: Metrics, Tracing, Kiali/Grafana
6. Multi-Cluster, Multi-Datacenter, Hybrid VM
7. Istio Deep-Dive Architecture
8. Consul Deep-Dive Architecture

## Editable Architecture Diagrams (`.drawio`, kept at root)

📐 **Combined poster:** [`Diagram-00-Master-Overview-Combined.drawio`](Diagram-00-Master-Overview-Combined.drawio) — all 9 diagrams below, laid out in one 3×3-grid single page for a print/study overview.

| # | File | What It Shows |
|---|---|---|
| 1 | [`Diagram-01-Sidecar-Pattern.drawio`](Diagram-01-Sidecar-Pattern.drawio) | App + Envoy sidecar per pod, localhost vs mTLS hop |
| 2 | [`Diagram-02-Control-Plane-vs-Data-Plane.drawio`](Diagram-02-Control-Plane-vs-Data-Plane.drawio) | Control plane pushing config to data-plane proxies |
| 3 | [`Diagram-03-mTLS-Handshake.drawio`](Diagram-03-mTLS-Handshake.drawio) | Full mTLS cert issuance + mutual handshake flow |
| 4 | [`Diagram-04-Zero-Trust-Microsegmentation.drawio`](Diagram-04-Zero-Trust-Microsegmentation.drawio) | Allow/deny intentions around payment-service |
| 5 | [`Diagram-05-Canary-Traffic-Split.drawio`](Diagram-05-Canary-Traffic-Split.drawio) | Weighted 90/10 canary routing |
| 6 | [`Diagram-06-Multi-Cluster-Mesh-Gateway.drawio`](Diagram-06-Multi-Cluster-Mesh-Gateway.drawio) | Cross-cluster mesh gateway connectivity |
| 7 | [`Diagram-07-Hybrid-VM-Kubernetes.drawio`](Diagram-07-Hybrid-VM-Kubernetes.drawio) | Kubernetes + legacy VM datacenter connectivity |
| 8 | [`Diagram-08-Istio-Architecture.drawio`](Diagram-08-Istio-Architecture.drawio) | istiod + ingress gateway + Envoy request flow |
| 9 | [`Diagram-09-Consul-Architecture.drawio`](Diagram-09-Consul-Architecture.drawio) | Consul servers (Raft) + client agents (gossip) |

## 1. [`Must-Know/`](Must-Know/) — 11 files, master these completely

| # | File | Topic |
|---|---|---|
| 01 | [`01-Concepts-Reference.md`](Must-Know/01-Concepts-Reference.md) | Foundational concepts (see above) |
| 02 | [`02-Trap-mTLS-Equals-Zero-Trust.md`](Must-Know/02-Trap-mTLS-Equals-Zero-Trust.md) | Trap: "mTLS everywhere = Zero Trust achieved" |
| 03 | [`03-Trap-Mesh-Replaces-API-Gateway.md`](Must-Know/03-Trap-Mesh-Replaces-API-Gateway.md) | Trap: "Mesh replaces the API gateway" |
| 04 | [`04-Trap-Do-You-Even-Need-A-Mesh.md`](Must-Know/04-Trap-Do-You-Even-Need-A-Mesh.md) | Trap: "3 microservices? Definitely adopt a full mesh" |
| 05 | [`05-Trap-Control-Plane-Outage-Impact.md`](Must-Know/05-Trap-Control-Plane-Outage-Impact.md) | Trap: "Control plane down = instant total outage" |
| 06 | [`06-Trap-More-Retries-Always-Better.md`](Must-Know/06-Trap-More-Retries-Always-Better.md) | Trap: "More retries = more resilience, always" |
| 07 | [`07-Trap-Canary-vs-Blue-Green.md`](Must-Know/07-Trap-Canary-vs-Blue-Green.md) | Trap: "Canary and Blue-Green are the same thing" |
| 15 | [`15-Scenario-Unauthorized-Service-Bypass.md`](Must-Know/15-Scenario-Unauthorized-Service-Bypass.md) | Scenario: frontend bypassing checkout to call payment directly |
| 16 | [`16-Scenario-Cascading-Latency-From-Slow-Dependency.md`](Must-Know/16-Scenario-Cascading-Latency-From-Slow-Dependency.md) | Scenario: slow (not down) dependency causes cascading latency |
| 17 | [`17-Scenario-Blind-Retries-Everywhere-Bad-Idea.md`](Must-Know/17-Scenario-Blind-Retries-Everywhere-Bad-Idea.md) | Scenario: why blanket retries=5 is dangerous |
| 18 | [`18-Scenario-Canary-Rollout-Undetected-Error-Spike.md`](Must-Know/18-Scenario-Canary-Rollout-Undetected-Error-Spike.md) | Scenario: canary error spike goes unnoticed for 20 minutes |

## 2. [`Good-to-Know/`](Good-to-Know/) — 11 files, adds real operational depth

| # | File | Topic |
|---|---|---|
| 08 | [`08-Trap-Injection-Not-Retroactive.md`](Good-to-Know/08-Trap-Injection-Not-Retroactive.md) | Trap: "Labeling the namespace injects existing pods" |
| 09 | [`09-Trap-Outdated-Mixer-Citadel-Galley-Knowledge.md`](Good-to-Know/09-Trap-Outdated-Mixer-Citadel-Galley-Knowledge.md) | Trap: "Istio control plane = Pilot+Citadel+Galley+Mixer" (outdated) |
| 10 | [`10-Trap-Tracing-Requires-Header-Propagation.md`](Good-to-Know/10-Trap-Tracing-Requires-Header-Propagation.md) | Trap: "Full distributed tracing is 100% automatic" |
| 11 | [`11-Trap-Localhost-Traffic-Not-Encrypted.md`](Good-to-Know/11-Trap-Localhost-Traffic-Not-Encrypted.md) | Trap: "App-to-own-sidecar traffic is encrypted too" |
| 12 | [`12-Trap-Outlier-Detection-Replaces-Probes.md`](Good-to-Know/12-Trap-Outlier-Detection-Replaces-Probes.md) | Trap: "Outlier detection replaces readiness/liveness probes" |
| 19 | [`19-Scenario-Zero-Downtime-Mesh-Migration.md`](Good-to-Know/19-Scenario-Zero-Downtime-Mesh-Migration.md) | Scenario: migrating an existing cluster into the mesh with zero downtime |
| 20 | [`20-Scenario-Rolling-Deployment-502-Errors.md`](Good-to-Know/20-Scenario-Rolling-Deployment-502-Errors.md) | Scenario: 502s during rolling deploys — sidecar race conditions |
| 21 | [`21-Scenario-Rescheduled-Pod-Discovery-vs-Draining.md`](Good-to-Know/21-Scenario-Rescheduled-Pod-Discovery-vs-Draining.md) | Scenario: discovery vs connection draining after a reschedule |
| 22 | [`22-Scenario-Sidecar-Latency-Tax-Business-Justification.md`](Good-to-Know/22-Scenario-Sidecar-Latency-Tax-Business-Justification.md) | Scenario: justifying sidecar latency overhead to the CFO |
| 23 | [`23-Advanced-GitOps-Policy-Enforcement.md`](Good-to-Know/23-Advanced-GitOps-Policy-Enforcement.md) | Advanced: enforcing mesh policy via GitOps + admission control |
| 24 | [`24-Advanced-Multi-Region-Active-Active-Failover.md`](Good-to-Know/24-Advanced-Multi-Region-Active-Active-Failover.md) | Advanced: multi-region active-active with automatic failover |

## 3. [`Nice-to-Have/`](Nice-to-Have/) — 6 files, niche/staff-level, read last

| # | File | Topic |
|---|---|---|
| 13 | [`13-Trap-App-Label-Functional-Significance.md`](Nice-to-Have/13-Trap-App-Label-Functional-Significance.md) | Trap: "The `app` label is purely cosmetic" |
| 14 | [`14-Trap-Inject-Everything-Tradeoff.md`](Nice-to-Have/14-Trap-Inject-Everything-Tradeoff.md) | Trap: "Auto-inject everything is simply the best practice" |
| 25 | [`25-Advanced-Multi-Tenant-Platform-Design.md`](Nice-to-Have/25-Advanced-Multi-Tenant-Platform-Design.md) | Advanced: 40 teams sharing one mesh without breaking each other |
| 26 | [`26-Advanced-Mesh-Wide-Certificate-Rotation-At-Scale.md`](Nice-to-Have/26-Advanced-Mesh-Wide-Certificate-Rotation-At-Scale.md) | Advanced: rotating certs mesh-wide at scale without downtime |
| 27 | [`27-Advanced-Chaos-Engineering-Fault-Injection.md`](Nice-to-Have/27-Advanced-Chaos-Engineering-Fault-Injection.md) | Advanced: validating resilience proactively via fault injection |
| 28 | [`28-Advanced-Ambient-Mesh-Migration.md`](Nice-to-Have/28-Advanced-Ambient-Mesh-Migration.md) | Advanced: sidecar mode vs Istio ambient mesh trade-offs |

## 4. Final Prep (root level)

- 📄 [`29-Cheat-Sheet.md`](29-Cheat-Sheet.md) — rapid-fire one-line answers for last-minute review
- 📄 [`30-STAR-Answer-Framework.md`](30-STAR-Answer-Framework.md) — how to structure your spoken answer for any scenario question

---

**Recommended study order:** `Must-Know/01-Concepts-Reference.md` → rest of `Must-Know/` (files `02`–`18`) → all of `Good-to-Know/` (files `08`–`24`) → all of `Nice-to-Have/` (files `13`–`28`) → `29-Cheat-Sheet.md` the night before → `30-STAR-Answer-Framework.md` right before you walk in.
