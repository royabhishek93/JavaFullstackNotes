# Advanced Scenario 3: Migrating From Sidecar Mode to Istio Ambient Mesh

**Interviewer:** "You're moving from a sidecar-based mesh to Istio's 'ambient mesh.' What's the trade-off and when would you recommend it?"

**You (15-yr Architect):**

## Sidecar Mode vs Ambient Mode (ASCII comparison)

```
  SIDECAR MODE (traditional)
  +--------------------------------+
  | Pod: App + Envoy sidecar        |
  | 1 sidecar PER POD               |
  +--------------------------------+
  (repeated for every single pod on the node)


  AMBIENT MODE
  +------------------+
  | Pod: App only     |
  | (no sidecar)      |
  +------------------+
          |
          v
  +---------------------------+
  | ztunnel                    |   <- node-level L4 proxy,
  | shared by ALL pods         |      SHARED across every pod
  | on the node                |      on this node
  +---------------------------+
          |
          v (only when L7 features needed)
  +---------------------------+
  | waypoint proxy              |  <- optional, namespace-level,
  | (per-namespace, on demand)  |     for L7 traffic management
  +---------------------------+
```

## Trade-Offs to Discuss

| | Sidecar Mode | Ambient Mode |
|---|---|---|
| **Resource overhead** | One Envoy per pod — expensive at thousands of pods | Massive reduction — shared `ztunnel` per node |
| **Upgrades** | Rolling restart every pod to bump Envoy version | Upgrade `ztunnel` on the node, no pod restarts needed |
| **Onboarding** | Injection webhook, namespace labeling gymnastics | Simpler — no per-pod injection needed for baseline mTLS |
| **Maturity** | Battle-tested, most production usage today | Newer, less battle-tested |
| **L7 features (retries, header routing)** | Always available per-pod | Requires deploying a **waypoint proxy** where needed — adds complexity back in a scoped way |
| **Blast radius of proxy failure** | One pod affected | `ztunnel` failure affects **all pods on that node** |

## My Recommendation

> "For a large multi-tenant platform with thousands of low-complexity services that mostly need mTLS plus basic routing, ambient is compelling purely for cost and operational reasons — the sidecar tax at that scale is real money and real upgrade pain. For a smaller number of services needing rich L7 traffic control — extensive canarying, fault injection, header manipulation — sidecar mode is still more mature and predictable, and I wouldn't migrate those workloads first."

---
See also: [22-Scenario-Sidecar-Latency-Tax-Business-Justification.md](22-Scenario-Sidecar-Latency-Tax-Business-Justification.md), [01-Concepts-Reference.md — Part 7: Istio Architecture](01-Concepts-Reference.md#7-istio-deep-dive-architecture)
