# Advanced Scenario 1: Multi-Region Active-Active E-Commerce Architecture With Automatic Failover

**Interviewer:** "Design a multi-region active-active architecture for an e-commerce platform using service mesh, with automatic failover."

**You (15-yr Architect):**

📐 **Editable diagram:** [`Diagram-06-Multi-Cluster-Mesh-Gateway.drawio`](Diagram-06-Multi-Cluster-Mesh-Gateway.drawio) (base pattern extended below)

```
   Global Load Balancer / GeoDNS
   (latency-based routing)
        |                    |
        v                    v
 +----------------+   +----------------+
 | Region US (EKS)|   | Region EU (LKE)|
 |                |   |                |
 | Mesh Gateway US|<->| Mesh Gateway EU|
 |                |   |                |
 | payment-svc US |---locality-aware->| payment-svc EU|
 |                | failover if US     |                |
 |                | region unhealthy   |                |
 +----------------+   +----------------+
```

## Three-Layer Architecture (Diagram)

```
┌─ L1: Layer 1: GeoDNS / Global Load Balancer (outside the mesh) ─────────────┐
│  [DNS] Latency-based / Anycast routing to nearest healthy region           │
└───────────────────┬───────────────────────────────────┬────────────────────┘
                     │ DNS-->GW_US                        │ DNS-->GW_EU
                     v                                    v
┌─ L2US: Layer 2: Mesh Failover - Region US ──┐   ┌─ L2EU: Layer 2: Mesh Failover - Region EU ──┐
│  [GW_US] Mesh Gateway US ──> [SVC_US]        │   │  [GW_EU] Mesh Gateway EU ──> [SVC_EU]        │
│           payment-service US                 │   │           payment-service EU                 │
└───────────────────────────┬───────────────────┘   └────────────────────────────┬──────────────────┘
           SVC_US ┄┄┄ "locality failover if US unhealthy" ┄┄┄> SVC_EU
                                │ SVC_US-->DB_US                                │ SVC_EU-->DB_EU
                                v                                                v
┌─ L3: Layer 3: Database Replication (separate concern) ──────────────────────────────────────┐
│   [DB_US] DB US <────── "replication (eventual/strong consistency)" ──────> [DB_EU] DB EU   │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## Three Layers of the Design

1. **GeoDNS / Global Load Balancer** routes users to the nearest healthy region — **outside the mesh's job entirely**. This is DNS-level or Anycast-level routing.
2. **Within the mesh:** configure **locality-weighted load balancing** so services prefer same-region replicas first, and only failover cross-region when the local region's health checks fail (using `ServiceResolver`/`OutlierDetection` + cluster peering — the same mechanism demoed with Consul's shipping-service cross-cluster failover).
3. **Stateful data (the database)** is a **separate concern** — the mesh routes *service* traffic, it does not solve data replication/consistency. Pair this with a multi-region database strategy (e.g., DynamoDB Global Tables, CockroachDB, or an active-passive DB with regional read replicas).

## The Critical Distinction to State Out Loud

> "I always clarify this boundary in interviews and in design reviews: mesh failover handles *where a request is routed*, not *whether the data is consistent across regions*. People conflate 'the mesh failed over' with 'the system is fully consistent now' — those are two different problems solved by two different subsystems."

## Failure Mode Walkthrough

| Failure | What Handles It |
|---|---|
| US region's `payment-service` pods all unhealthy | Mesh locality failover routes to EU region's `payment-service` |
| Entire US region network partition | GeoDNS/Global LB stops routing new users to US; in-flight sessions may need reconnect logic at the client |
| Data written in US not yet replicated to EU before failover | **Not solved by the mesh** — requires the database layer's own replication/consistency guarantees (this is where you discuss CAP trade-offs, eventual vs strong consistency) |

---
See also: [01-Concepts-Reference.md — Part 6: Multi-Cluster](01-Concepts-Reference.md#6-multi-cluster-multi-datacenter-hybrid-vm)
