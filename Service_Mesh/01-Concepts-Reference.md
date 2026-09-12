# Service Mesh Concepts Reference — Scratch to Architect (Istio + Consul)

> Companion file to the numbered Q&A files (`02-` through `28-`) in this same folder. Read this once, top to bottom, like a conversation between a **Mentor** and a **Student**. Diagrams here are ASCII (render anywhere, even in a terminal or plain text editor). The 9 most important architecture diagrams also have a matching editable `.drawio` file (prefixed `Diagram-`) in this same folder — open those in the draw.io / VS Code Draw.io Integration extension if you want to tweak or present them.

## Table of Contents
1. [Why Does Service Mesh Even Exist](#1-why-does-service-mesh-even-exist)
2. [Sidecar Pattern, Control Plane vs Data Plane](#2-sidecar-pattern-control-plane-vs-data-plane)
3. [Security: mTLS and Zero Trust](#3-security-mtls-and-zero-trust)
4. [Traffic Management: Canary, Retries, Circuit Breaking](#4-traffic-management-canary-retries-circuit-breaking)
5. [Observability: Metrics, Tracing, Kiali/Grafana](#5-observability-metrics-tracing-kialigrafana)
6. [Multi-Cluster, Multi-Datacenter, Hybrid VM](#6-multi-cluster-multi-datacenter-hybrid-vm)
7. [Istio Deep-Dive Architecture](#7-istio-deep-dive-architecture)
8. [Consul Deep-Dive Architecture](#8-consul-deep-dive-architecture)

---

## 1. Why Does Service Mesh Even Exist

**Mentor:** Let's not start with "what is a service mesh" — that's how people give robotic, memorized answers in interviews. Let's start with a story, because that's what a 15-year architect actually does: they explain the *problem* so well that the *solution* sounds obvious.

Imagine you're building Amazon. You've broken your monolith into microservices — `product-catalog`, `cart`, `payment`, `order`, `auth`, `recommendation`, `shipping`. Nice, clean, independently deployable. Except now every one of those services needs to talk to several others.

```
                +--------------+
                |   Frontend   |
                +--------------+
                 |    |    |    \
                 v    v    v     v
           +------+ +----+ +-----+ +-------+
           | Auth | |Cart| |Order| |Catalog|
           +------+ +----+ +-----+ +-------+
                       |      |
                       v      v
                  +---------+ +---------+
                  | Payment | | Shipping|
                  +---------+ +---------+
                       |
                       v
                 +------------+
                 | Bank / Ext |
                 | Payment GW |
                 +------------+

  Recommendation-Service ---> Auth-Service
  Recommendation-Service ---> Catalog-Service
```

**Student:** Okay, that's just... microservices. What's the actual problem?

**Mentor:** The problem is *everything that's not business logic* that now has to live **inside** every one of those services:

- **Discovery** — how does `cart` know the IP/port of `payment` today, when pods get rescheduled constantly?
- **Resilience** — what happens when `payment` is slow or down? Does `cart` retry? Timeout? Give up?
- **Security** — is the traffic between `cart` and `payment` encrypted? Can literally any pod in the cluster talk to `payment`?
- **Observability** — how do you know `payment` is having a bad day, versus `cart` sending malformed requests?

Without a mesh, every team writes this logic **inside their own app**, in whatever language they use, with whatever quality bar they have. That's the monolith-to-microservices tax nobody warns you about.

```
   WITHOUT A SERVICE MESH: every team reinvents the wheel
   --------------------------------------------------------
   +--------------------+        +--------------------+
   |  Cart Service code |        | Payment Service code|
   |  + retry logic     |        |  + retry logic       |
   |  + TLS handling    |        |  + TLS handling       |
   |  + metrics client  |        |  + metrics client     |
   |  + discovery client|        |  + discovery client   |
   +--------------------+        +--------------------+
      (duplicated, inconsistent, in every language, every team)
```

**Student:** So the mesh takes all four of those cross-cutting concerns out of the app?

**Mentor:** Exactly. That's the one-sentence definition you should give in an interview:

> "A service mesh is a dedicated infrastructure layer that handles service-to-service communication — discovery, security (mTLS), traffic control (retries/timeouts/canary), and observability — **outside of the application code**, usually via a sidecar proxy, so developers only write business logic."

Notice I didn't say "Istio" or "Consul" in that sentence. That's important — **know the concept before the product**. Interviewers love asking "would this still work if you used Linkerd instead of Istio?" — and the answer should always be yes, because the concept is tool-agnostic.

---

## 2. Sidecar Pattern, Control Plane vs Data Plane

**Mentor:** Here's the single most important diagram in your entire service-mesh vocabulary. Get this into your head permanently.

📐 **Editable diagram:** [`Diagram-01-Sidecar-Pattern.drawio`](Diagram-01-Sidecar-Pattern.drawio)

```
 +-----------------------------+           +-----------------------------+
 |   Pod: cart-service         |           |   Pod: payment-service      |
 |                             |           |                             |
 |  +-------------+   local-  |           |  local-   +-------------+   |
 |  | App:        |   host    |           |  host     | App:        |   |
 |  | cart-svc    |<--------->|  Envoy    |<--------->| payment-svc |   |
 |  +-------------+   plain   |  Sidecar  |   plain   +-------------+   |
 |                    text    |  Proxy    |    text                    |
 +-----------------------------+     |     +-----------------------------+
                                      |
                             mTLS encrypted
                          (the ONLY network hop)
                                      |
                                      v
                              (Envoy <-> Envoy)
```

**Student:** So the app doesn't even know the proxy exists?

**Mentor:** Correct, and that's the magic. Think of it like a **personal assistant** (the analogy HashiCorp uses for Consul, and it's a great one): you don't email your customer directly, you tell your assistant "send this to payment" and the assistant looks up the real address, wraps it securely, sends it, and hands you back the reply. You never had to learn networking.

Now — **who configures the assistant**? That's where control plane vs data plane comes in.

📐 **Editable diagram:** [`Diagram-02-Control-Plane-vs-Data-Plane.drawio`](Diagram-02-Control-Plane-vs-Data-Plane.drawio)

```
                +-------------------------------------+
                |   CONTROL PLANE (the brain)          |
                |   istiod / Consul Servers            |
                +-------------------------------------+
                    |            |             |
          pushes config,   pushes config, pushes config,
          certs, registry  certs, registry certs, registry
          (xDS)                  |             |
                    v            v             v
              +---------+  +---------+   +---------+
              | Envoy   |  | Envoy   |   | Envoy   |
              | proxy A |<>| proxy B |<> | proxy C |
              +---------+  +---------+   +---------+
                  DATA PLANE (the hands) - actual mTLS traffic
```

| Concept | Control Plane | Data Plane |
|---|---|---|
| **Job** | Decides the rules (routing, security, certs) | Actually moves the bytes, per request |
| **Istio component** | `istiod` (since 1.5; before that: Pilot, Citadel, Galley, Mixer) | Envoy sidecars |
| **Consul component** | Consul **servers** (3 or 5 for quorum) | Consul **clients/agents** + Envoy sidecars |
| **If it goes down** | New config/certs stop propagating, but *existing* proxies keep working using cached config | Immediate impact — that pod can't talk to anyone |
| **Analogy** | Head office / HQ | Personal assistants in every building |

**Student:** Wait — you said if control plane goes down, existing proxies keep working? That's a trap question I've heard before...

**Mentor:** Good catch — see [`05-Trap-Control-Plane-Outage-Impact.md`](05-Trap-Control-Plane-Outage-Impact.md). Short answer: yes, Envoy caches its last-known-good config (xDS), so a control plane outage is not immediately catastrophic — but new pods can't get proxies injected, certs can't rotate, and topology changes won't propagate. That nuance is exactly what separates a mid-level engineer's answer from an architect's answer.

**How does the sidecar actually get there?** This is the part people gloss over — it's a **Kubernetes Mutating Admission Webhook**:

```
  kubectl apply deployment.yaml
             |
             v
      K8s API Server ---- "should I mutate this pod?" ----> Mutating Webhook
             |                                          (istio-sidecar-injector /
             |                                           consul-connect-inject)
             |<----------------- "Yes, inject sidecar" -----------|
             v
      Scheduler creates pod with:
        1. init-container   (sets up iptables / certs)
        2. app container    (your business logic)
        3. sidecar proxy    (istio-proxy / consul-dataplane)
```

Nobody edits your `deployment.yaml` to add a proxy container manually — the webhook intercepts the pod creation request and injects it on the fly. This is *exactly* why, in practice, labeling the namespace with `istio-injection=enabled` (Istio) or setting `connectInject.default=true` (Consul Helm chart) was the only step needed.

**Trap embedded here:** if you apply your deployment **before** enabling injection, the pods will **not** get sidecars retroactively. You must delete/recreate the pods (or do a rollout restart) after enabling injection. See [`08-Trap-Injection-Not-Retroactive.md`](08-Trap-Injection-Not-Retroactive.md).

---

## 3. Security: mTLS and Zero Trust

**Mentor:** Let's talk security, because this is where architects are expected to go deep — not just "it encrypts traffic," but *how* and *why it matters for compliance*.

📐 **Editable diagram:** [`Diagram-03-mTLS-Handshake.drawio`](Diagram-03-mTLS-Handshake.drawio)

```
   Control Plane CA
   (issues short-lived certs)
      |                                                  |
      | 1. issue cert                    1. issue cert   |
      v                                                   v
  +---------+                                       +-----------+
  | App1    |   2. plain HTTP    +---------+   3. mTLS   +---------+   4. decrypted   +---------+
  | (Cart)  |------------------->| Envoy   |----handshake--------->| Envoy   |----plain HTTP--->| App2    |
  +---------+                    | Sidecar |   (mutual   |Sidecar  | Sidecar |                   |(Payment)|
                                  | (Cart)  |   cert      |(Payment)+---------+                  +---------+
                                  +---------+   verify)   +---------+
```

**Student:** Why "mutual"? Normal HTTPS on the internet is one-way — my browser verifies the server, not the other way round.

**Mentor:** Exactly the right question. In the browser case, the **client is a human with a password**, so identity is proven at login. But inside a mesh, **both sides are services**, and both need to cryptographically prove who they are — not just "are you real," but "are you the `payment-service`'s proxy or an attacker's pod pretending to be it?" That mutual verification unlocks two huge features:

1. **Encryption in transit** (nobody sniffing the network can read anything)
2. **Strong service identity** — the cert itself becomes the identity, which lets you write authorization rules.

📐 **Editable diagram:** [`Diagram-04-Zero-Trust-Microsegmentation.drawio`](Diagram-04-Zero-Trust-Microsegmentation.drawio)

```
  checkout-service ------ ALLOWED (explicit intention) -----> payment-service
  frontend --------- x -- DENIED (default-deny) ------------> payment-service
  recommendation ---- x -- DENIED (default-deny) ------------> payment-service
  any other service -- x -- DENIED (default) ---------------> payment-service
```

This is called **micro-segmentation** — in Istio it's an `AuthorizationPolicy`, in Consul it's a **service intention**. The key architectural point:

> "Instead of one big firewall around the whole cluster (perimeter security), every single service gets its own tiny firewall based on cryptographic identity, not IP address. IPs are ephemeral in Kubernetes — pods die and get new IPs constantly — so IP-based firewalls don't scale. Identity-based (SPIFFE/cert) firewalls do."

This is literally the definition of **Zero Trust Networking**: *never trust based on network location, always verify identity.*

**Real production example to say in an interview:**
> "In my last project, we had PCI-DSS scope for the payment service. Instead of putting the whole cluster in PCI scope (expensive, huge audit surface), we used mesh-level authorization policies so that only `checkout-service` could reach `payment-service`, and everything else was default-deny. That shrunk our compliance boundary to two services instead of the whole namespace."

That single sentence signals "architect," not "engineer."

---

## 4. Traffic Management: Canary, Retries, Circuit Breaking

### Canary / Traffic Splitting

📐 **Editable diagram:** [`Diagram-05-Canary-Traffic-Split.drawio`](Diagram-05-Canary-Traffic-Split.drawio)

```
  User Requests --> Ingress / Mesh Gateway --> VirtualService (routing rule)
                                                     |         \
                                                 90% |          \ 10%
                                                     v           v
                                        payment-service v2.0   payment-service v3.0
                                             (stable)               (canary)
```

**Student:** Why not just deploy v3.0 and see if it breaks?

**Mentor:** Because "see if it breaks" in production means real customers hit real bugs. With the mesh doing **weighted traffic splitting at Layer 7 (HTTP)**, you separate two concerns that used to be coupled in Kubernetes-only deployments:

- **Deployment** (rolling out new pods) — a Kubernetes concept
- **Traffic exposure** (who actually receives requests) — a mesh concept

You can have v3.0 fully deployed and running, receiving **zero** production traffic, while you smoke-test it internally, then dial it up 1% → 10% → 50% → 100%. If error rates spike, dial back to 0% instantly — no redeploy needed.

### Retries, Timeouts, Circuit Breaking

```
        +-----------------------------------------------------------+
        |                                                             |
        v                                                             |
   [ CLOSED ] --error threshold exceeded (e.g. 5 x 5xx)--> [ OPEN ]  |
   traffic flows                                       requests fail  |
   normally                                             fast, no      |
        ^                                                traffic sent |
        |                                                     |       |
        | trial request succeeds                  after sleep window  |
        |                                          (e.g. 30s)         |
        |                                                     v       |
        +----------------------- [ HALF-OPEN ] <--------------+       |
                                  send 1 trial request                 |
                                  request fails ------------------------+
```

**Mentor:** This is the **circuit breaker pattern**, implemented via **outlier detection** (Istio `DestinationRule`) — if an instance/pod of `payment-service` keeps returning 5xx, the mesh **ejects that specific pod** from the load-balancing pool temporarily, without touching the other healthy replicas. Your app never wrote a single line of "if 5 errors then stop calling this pod" logic.

**The trap here:** "So if I configure retries at the mesh level, do I still need error handling in my app?" — **Yes.** Mesh retries handle **transient network failures**, not legitimate business errors (e.g. "insufficient funds" is a valid response, not something to retry — and retrying a payment call after a lost response could **double-charge** a customer if the original request actually succeeded!). See [`06-Trap-More-Retries-Always-Better.md`](06-Trap-More-Retries-Always-Better.md).

> **Architect-level insight:** "Mesh-level retries must only be applied to idempotent operations, or safe HTTP methods like GET. For POST/payment operations, I explicitly disable retries at the mesh layer or ensure idempotency keys are used."

---

## 5. Observability: Metrics, Tracing, Kiali/Grafana

**Mentor:** Because every request passes through an Envoy proxy on both ends, and it's *the same proxy binary everywhere*, you get **uniform telemetry for free**.

```
  Every hop generates the SAME shaped data:

   Envoy(cart)    --metrics-->  Prometheus  --used by-->  Grafana Dashboards
   Envoy(payment) --metrics-->  Prometheus
   Envoy(order)   --metrics-->  Prometheus

   Envoy(cart)    --spans-->    Jaeger/Zipkin --used by--> Kiali Topology View
   Envoy(payment) --spans-->    Jaeger/Zipkin
   Envoy(order)   --spans-->    Jaeger/Zipkin
```

**Student:** Why is "same shape" such a big deal?

**Mentor:** Because before the mesh, if `cart` is Node.js with a Prometheus client, `payment` is Java using Micrometer, and `order` is Python — they'll all report metrics slightly differently. Now you have to normalize all of that before you can build one dashboard. With Envoy sitting in front of every one of them, regardless of the app's language, you get identical metric names (`istio_requests_total`, `envoy_cluster_upstream_rq_time`, etc.) — instant unified dashboards.

**The one required label — the classic trap:** In Istio, the `app` label on Pods/Deployments is what Kiali uses to build the topology graph. Miss the label, pods still work fine (no errors), but Kiali shows nothing meaningful. See [`13-Trap-App-Label-Functional-Significance.md`](13-Trap-App-Label-Functional-Significance.md).

**Distributed Tracing gotcha:** Envoy can generate spans, but it can't stitch together a *full* trace across multiple hops **unless the application propagates trace headers** (`x-request-id`, `x-b3-traceid`, `traceparent`, etc.) from incoming request to any outgoing request it makes. See [`10-Trap-Tracing-Requires-Header-Propagation.md`](10-Trap-Tracing-Requires-Header-Propagation.md).

---

## 6. Multi-Cluster, Multi-Datacenter, Hybrid VM

**Mentor:** This is where you separate a "mid-level mesh user" from a "platform architect." Anyone can install Istio/Consul in one cluster. The real value is **cross-environment connectivity**.

### Multi-Cluster with Mesh Gateways

📐 **Editable diagram:** [`Diagram-06-Multi-Cluster-Mesh-Gateway.drawio`](Diagram-06-Multi-Cluster-Mesh-Gateway.drawio)

```
 +----------------------------------+        +----------------------------------+
 | Cluster A (AWS EKS) - dc: us     |        | Cluster B (Linode LKE) - dc: eu  |
 |                                  |        |                                  |
 | payment-service                 |        |                     shipping-svc |
 |     |                           |        |                           ^      |
 |     v                           |        |                           |      |
 | Envoy Sidecar                   |        |                     Envoy Sidecar|
 |     |                           |        |                           ^      |
 |     v                           |        |                           |      |
 | Mesh Gateway A <================================> Mesh Gateway B          |
 |                    secure cross-cluster mTLS tunnel  |                     |
 |                        (over public internet)        |                     |
 +----------------------------------+        +----------------------------------+
```

**Student:** Why do I need a "mesh gateway" — why can't the sidecars just talk directly across clusters?

**Mentor:** Two reasons:

1. **Network reachability** — pod IPs are private, cluster-internal, and usually *not routable* across two different VPCs/clouds. You'd need full VPC peering/VPN for every pod, which doesn't scale and is a security nightmare.
2. **Security chokepoint** — the mesh gateway is the **single, controlled ingress/egress point** between two trust domains. Only it needs to be internet/cross-VPC reachable — not every single pod.

This is the "city guard at the gate" analogy — instead of every resident needing a passport to cross into another city, there's one checkpoint (the gateway) that handles the crossing for everyone.

### Consul-Specific: Cluster Peering Flow

```
 Cluster A (EKS)                                Cluster B (LKE)
 Consul Server                                  Consul Server
      |                                              |
      |-- generate peering token ------------------->|
      |                                              |-- establish peering using token
      |                                              |    (via mesh gateways)
      |<------------------- PEERING ACTIVE  -------->|
      |                                              |
      |                                              |-- export shipping-service
      |-- create ServiceResolver: failover to        |
      |   peer's shipping-service                    |
      |                                              |
   [local shipping-service pod CRASHES]               |
      |                                              |
      |== automatic failover -> traffic redirected ==>|
      |   to peer's shipping-service via mesh gateway |
```

**Student:** So this is literally disaster recovery / failover built into the mesh, without writing any failover logic in the app?

**Mentor:** Exactly, and that's the "wow" answer for an architect interview. The app (`checkout-service`) never knows shipping moved to another continent — it just says "talk to shipping" and the mesh figures out routing, including cross-cluster failover, via a `ServiceResolver` (Consul) or `ServiceEntry` + locality failover (Istio's equivalent).

### Hybrid: Kubernetes + Legacy VMs

📐 **Editable diagram:** [`Diagram-07-Hybrid-VM-Kubernetes.drawio`](Diagram-07-Hybrid-VM-Kubernetes.drawio)

```
 +--------------------------+          +----------------------------------+
 | Kubernetes Cluster       |          | On-Prem Data Center (VMs)        |
 |                          |          |                                  |
 | payment-service pod      |          |                Legacy Database   |
 |     |                    |          |                       ^          |
 |     v                    |          |                       |          |
 | Sidecar                  |          |            Consul Client Agent   |
 |     |                    |          |                       ^          |
 |     v                    |          |                       |          |
 | Mesh Gateway <===============================> Mesh Gateway           |
 |                     secure tunnel        |                              |
 +--------------------------+          +----------------------------------+
```

**Mentor:** Real talk: this scenario comes up constantly in 15+ year architect interviews because most large enterprises **still have legacy systems on VMs** that will never be "cloud-native." The point to make: Consul specifically treats VM workloads as **first-class citizens** — you install a Consul client agent directly on the VM (no Kubernetes needed), and it participates in the mesh the same way a sidecar-injected pod does. Istio can do this too (via `WorkloadEntry`/`WorkloadGroup`), but Consul's story here is historically stronger, given its VM-first heritage.

**Interview gold line:** *"You don't migrate the database to Kubernetes just to get mesh benefits — you extend the mesh to where the database already lives."*

---

## 7. Istio Deep-Dive Architecture

📐 **Editable diagram:** [`Diagram-08-Istio-Architecture.drawio`](Diagram-08-Istio-Architecture.drawio)

```
                     +----------------------------------------------+
                     | Control Plane                                |
                     |  istiod (Pilot+Citadel+Galley merged;         |
                     |  Mixer removed since v1.5)                    |
                     +----------------------------------------------+
                         | xDS config, certs   | xDS       | xDS
                         v                     v           v
     +--------------------------------------------------------------+
     | Data Plane                                                    |
     |  +------------------+   +----------------+   +----------------+|
     |  | Istio Ingress GW |-->| Envoy svc A    |-->| Envoy svc B    ||
     |  +------------------+   +----------------+   +----------------+|
     +--------------------------------------------------------------+
             ^     VirtualService routing      DestinationRule policy
             |
     External User (HTTPS request)
```

Two CRDs matter most, and interviewers *love* asking "what's the difference between VirtualService and DestinationRule":

| | VirtualService | DestinationRule |
|---|---|---|
| **Answers** | "**Where** should this request go?" (routing) | "**How** should I treat traffic once it's arrived?" (policy) |
| **Examples** | Path/header routing, weighted traffic split (canary), retries, timeouts, fault injection | Load balancing algorithm, TLS mode, connection pool limits, outlier detection (circuit breaker), subsets (v1/v2 labels) |
| **Analogy** | The GPS directions — which road to take | The car's driving rules once on that road |

```
  User -> Gateway -> VirtualService (routing) -> DestinationRule (policy) -> payment-service v2 pod
                                                                                  |
                                                                    (traced + metrics collected along the way)
```

**Student:** Why did they merge Mixer/Citadel/Galley/Pilot into `istiod`?

**Mentor:** Great trap-awareness question — proves you know **history**, which signals real experience.

- **Before 1.5:** Separate pods for Pilot (config), Citadel (certs), Galley (config validation/ingestion), Mixer (telemetry & policy checks — this one was *in the request path*, causing serious latency, deprecated first).
- **After 1.5:** All merged into a single `istiod` binary — simpler operations, fewer moving parts, lower latency (Mixer's per-request policy check removed entirely; enforcement moved into Envoy itself).

If someone in 2026 describes Istio with "Mixer does telemetry" — that's outdated, deprecated architecture. See [`09-Trap-Outdated-Mixer-Citadel-Galley-Knowledge.md`](09-Trap-Outdated-Mixer-Citadel-Galley-Knowledge.md).

**Istio Gateway vs Ingress Gateway vs Kubernetes Ingress:**

```
  Kubernetes Ingress Resource --(generic K8s API,
                                  needs a controller like nginx-ingress)--> Any ingress controller

  Istio Gateway CRD --(Istio-specific, L4-L6: ports, TLS, hosts)--> Istio Ingress Gateway pod (= Envoy standalone)
                    --(paired with VirtualService for L7 routing)-->
```

Istio Gateway handles connection-level concerns (which port, which TLS cert, which hostnames) — always paired with a `VirtualService` for the actual L7 routing logic. This two-CRD split is intentional (separation of concerns between infra team who owns the Gateway, and app team who owns the VirtualService).

---

## 8. Consul Deep-Dive Architecture

📐 **Editable diagram:** [`Diagram-09-Consul-Architecture.drawio`](Diagram-09-Consul-Architecture.drawio)

```
              +---------------------------------------------------+
              | Control Plane (HQ office)                          |
              | Consul Server 1 <-Raft-> Server 2 <-Raft-> Server 3|
              +---------------------------------------------------+
                    | gossip, catalog, certs        | gossip, catalog, certs
                    v                                v
     +-----------------------------+   +-----------------------------+
     | Data Plane (assistants)     |   | Data Plane (assistants)     |
     | Consul Client Agent +       |<->| Consul Client Agent +       |
     | Envoy - Pod A                | mTLS| Envoy - Pod B              |
     +-----------------------------+   +-----------------------------+
```

Key architectural facts an architect must know cold:

1. **Consul servers use the Raft consensus algorithm** for leader election and data replication — deploy **3 or 5** (odd numbers, to survive quorum loss without split-brain). One replica = no fault tolerance = never do this in prod (a single-replica setup is only a demo simplification).
2. **Gossip protocol** (SWIM-based, called Serf under the hood) is how Consul agents discover each other's health without the server being a bottleneck for every single health check.
3. **Consul Connect** = the service mesh feature name (sidecar injection + mTLS + intentions). Vocabulary trap: "Consul" is the whole product (also does service discovery/KV-store/config outside of any mesh context); "Consul Connect" specifically is the mesh capability.
4. **Consul Service Intentions** = the authorization/allow-deny rules (Consul's equivalent of Istio's `AuthorizationPolicy`).
5. **Mesh Gateway** = cross-cluster/cross-datacenter traffic relay (see Part 6).

**Consul vs Istio — the table every architect interview eventually asks for:**

| Feature | Istio | Consul |
|---|---|---|
| Data plane proxy | Envoy | Envoy (via `consul-dataplane`) |
| Control plane | `istiod` | Consul Servers (Raft) |
| Primary platform | Kubernetes-native/first | Kubernetes **and** VMs/bare-metal as first-class citizens |
| Config style | Kubernetes CRDs (`VirtualService`, `DestinationRule`, `AuthorizationPolicy`) | Kubernetes CRDs **or** Consul-native config (HCL/API) — works without K8s at all |
| Multi-cluster | `ServiceEntry` + east-west gateway, or multi-primary/multi-network models | **Cluster peering** (or older WAN federation) via mesh gateways — very mature story |
| VM support | Possible (`WorkloadEntry`) but K8s-centric in practice | Native, historically Consul's core strength (started as VM service discovery tool) |
| Traffic mgmt richness | Very rich (fault injection, mirroring, header manipulation) | Good, slightly less granular out of the box |
| Learning curve | Steeper (many CRDs) | Gentler UI/CLI for basic use, still complex at scale |
| Best fit | Pure Kubernetes shops wanting maximum traffic-control granularity | Hybrid enterprises with mixed VM + K8s + multi-cloud/multi-DC |

---

**Next:** head to files `15-` through `22-` for production incident Q&A, `23-` through `28-` for architect-level design questions, `02-` through `14-` for the trap questions designed to catch you out, and [`29-Cheat-Sheet.md`](29-Cheat-Sheet.md) for rapid-fire review. See [`00-Index.md`](00-Index.md) for the full map.
