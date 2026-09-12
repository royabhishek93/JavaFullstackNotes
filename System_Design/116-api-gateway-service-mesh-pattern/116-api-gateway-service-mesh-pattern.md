# API Gateway & Service Mesh: Where Cross-Cutting Concerns Live in Microservices
### The difference between the front door of the building and the intercom wiring inside every wall

---

## PART 1 — THE STUDENT CONVERSATION

Imagine an office campus again, but now think about two completely different kinds of "traffic control." First, there's the main reception desk at the campus entrance — every visitor from OUTSIDE the campus (a customer's mobile app, a partner's server) checks in there exactly once: shows ID (authentication), gets a visitor badge with limited access (authorization), and is told which building to walk to (routing). That's **north-south traffic** — traffic entering the system from the outside world — and the reception desk is your **API Gateway** (Kong, AWS API Gateway, Spring Cloud Gateway). One gateway, one place to enforce rate limiting, auth, request/response transformation, and API versioning for everything that crosses the campus boundary.

Second, there's a completely different problem happening entirely INSIDE the campus, invisible to any visitor: building A's mailroom needs to send a package to building C's mailroom, and building C is under renovation and slow to respond today. Does every single building need custom logic to detect "building C is slow, retry with backoff, and if it's still down, circuit-break and reroute"? If every team hand-rolls their own retry/circuit-breaker/mTLS logic in every service's code, you get 20 slightly different, inconsistently-tested implementations of the exact same resilience patterns already covered in [009-circuit-breaker-pattern.md](009-circuit-breaker-pattern.md) and [045-retry-exponential-backoff-jitter.md](045-retry-exponential-backoff-jitter.md). The fix: install an identical, tiny helper booth (a **sidecar proxy**, typically Envoy) right next to the door of EVERY building, and route all inter-building mail through the booth next door instead of directly. The booth handles retries, timeouts, circuit breaking, load balancing between instances of the destination service, and encrypts the mail (mTLS) — completely transparently, without building A's mailroom staff writing a single line of resilience code. This mesh of identical booths, all centrally configured from one control tower that pushes the same rulebook to every booth, is a **Service Mesh** (Istio, Linkerd). This is **east-west traffic** — service-to-service traffic that never leaves the internal network.

The one-sentence distinction that matters in an interview: **API Gateway governs traffic entering the system from outside (north-south); Service Mesh governs traffic between services on the inside (east-west)** — and a mature microservices architecture at real scale typically runs BOTH simultaneously, because they solve different problems and neither one is a substitute for the other. A gateway with no mesh means each service reinvents retry/circuit-breaking logic internally. A mesh with no gateway means external clients would need to know internal service topology and there'd be no single place to rate-limit external abuse.

---

## PART 2 — THE GATEWAY & MESH ARCHITECTURE DIAGRAMS

### North-South (Gateway) vs East-West (Mesh)

```
                              INTERNET (external clients)
                                       |
                                       v
                        ┌───────────────────────────────┐
                        │       API GATEWAY              │   ← north-south
                        │  auth · rate limit · routing   │      (ONE entry point)
                        │  request/response transform    │
                        └────────────┬──────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              v                      v                      v
     ┌──────────────┐      ┌──────────────┐        ┌──────────────┐
     │ Order Svc      │      │ Payment Svc    │        │ Inventory Svc  │
     │ ┌────────────┐ │      │ ┌────────────┐ │        │ ┌────────────┐ │
     │ │ Envoy       │◄┼──────┼►│ Envoy       │◄┼────────┼►│ Envoy       │ │  ← east-west
     │ │ sidecar     │ │ mTLS │ │ sidecar     │ │  mTLS  │ │ sidecar     │ │     (mesh)
     │ └────────────┘ │      │ └────────────┘ │        │ └────────────┘ │
     └──────────────┘      └──────────────┘        └──────────────┘
              ▲                      ▲                      ▲
              └──────────────────────┴──────────────────────┘
                     all sidecars report to / are configured by:
                        CONTROL PLANE (Istio Pilot / istiod)
                     — pushes routing rules, retry policy, mTLS certs
```

### Sidecar Interception: How Traffic Gets Rerouted Transparently

```
Order Service code:
  restTemplate.getForObject("http://payment-service/charge", ...)
       |
       | (application has NO idea a sidecar exists — outbound traffic is
       |  transparently intercepted via iptables rules injected at pod startup)
       v
  ┌─────────────────────────────────────────┐
  │  Envoy sidecar (same pod, localhost)      │
  │  - looks up "payment-service" in its       │
  │    locally-cached service registry         │
  │  - applies retry policy (3x, exp backoff)  │
  │  - applies circuit breaker (open after      │
  │    5 consecutive 5xx)                       │
  │  - wraps connection in mTLS                 │
  │  - load balances across payment-service's   │
  │    3 healthy pod instances                  │
  └─────────────────────────────────────────┘
       |
       v
  Payment Service's sidecar (decrypts mTLS, passes to local app)
```

### API Gateway Routing & Aggregation

```
Mobile client: GET /api/v1/order-summary/789
                       |
                       v
              ┌─────────────────┐
              │   API GATEWAY    │
              │  - verify JWT     │
              │  - rate limit     │
              │    per user       │
              └────────┬─────────┘
                        │  fan-out to 3 backend calls (aggregation)
          ┌─────────────┼─────────────┐
          v              v              v
   Order Service   Payment Service  Shipping Service
          │              │              │
          └──────────────┴──────────────┘
                         │
              gateway MERGES 3 responses into
              ONE response for the mobile client
              — client makes 1 network call, not 3
              (this is the "API composition" pattern,
               see also 122-microservices-decomposition-patterns.md)
```

---

## PART 3 — INTERNALS AND REAL NUMBERS

### Control Plane vs Data Plane

```
DATA PLANE  = the actual sidecar proxies (Envoy instances) that touch
              every real request/response byte — thousands of them,
              one per pod, doing the retry/mTLS/LB work in real time.

CONTROL PLANE = the brain (Istio's istiod) that:
  1. Watches Kubernetes for service/pod changes (service discovery)
  2. Compiles routing/retry/security rules from YAML config (VirtualService,
     DestinationRule) into Envoy-native config
  3. Pushes that config to every sidecar via a gRPC streaming API (xDS protocol)

If the control plane goes down TEMPORARILY, existing sidecars keep
routing traffic fine using their LAST-KNOWN config — the control plane
is not on the per-request hot path, exactly like the flag-service /
SDK-cache separation in 093-feature-flags-dynamic-configuration.md.
```

### Gateway Rate Limiting Config (Illustrative)

```yaml
# Kong / API Gateway style declarative config
routes:
  - path: /api/v1/orders
    service: order-service
    plugins:
      - name: rate-limiting
        config: { minute: 100, policy: redis }   # per-consumer, backed by shared Redis
      - name: jwt
        config: { key_claim_name: kid }
      - name: request-transformer
        config: { add: { headers: ["X-Request-Id:$(uuid)"] } }
```

### Mesh Retry/Circuit-Breaker Policy (Istio-style)

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: payment-service
spec:
  host: payment-service
  trafficPolicy:
    connectionPool:
      http: { http1MaxPendingRequests: 50, maxRequestsPerConnection: 10 }
    outlierDetection:              # this IS the circuit breaker
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s        # ejected pod excluded from LB for 30s
```

### Real Numbers

```
Sidecar proxy latency overhead: typically 1-3ms added per hop (Envoy is
  highly optimized C++, but it IS an extra network hop even on localhost).
Sidecar memory footprint: roughly 40-100MB per pod at moderate traffic —
  multiply by pod count; this is a real, non-trivial infra cost of a mesh.
Control plane push latency for a rule change: often 1-10 seconds to
  propagate a new routing rule to every sidecar in a large cluster.
mTLS handshake overhead: amortized to near-zero due to connection reuse/
  pooling between sidecars — the cost is mostly at connection setup, not
  per-request.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "You have 30 microservices. External mobile clients call a handful of them, but the services also call each other extensively. How do you handle auth, rate limiting, retries, and encryption without every team reinventing this logic?"

**You (architect answer):**

> "I'd split this into two separate concerns that are often conflated. For traffic coming FROM outside — mobile clients, partner integrations — I'd put an API Gateway at the edge as the single enforcement point for authentication, per-consumer rate limiting, and request routing/aggregation. That means none of the 30 services need to re-implement JWT verification or rate limiting themselves; it's centralized at the one place external traffic actually enters.
>
> For traffic BETWEEN the 30 services — which is the majority of the traffic volume in a real system like this — I'd use a service mesh with a sidecar proxy deployed alongside every service instance. That gives me mTLS between every service pair, retries with backoff, and circuit breaking, all applied transparently and consistently, without a single line of resilience code inside any service's business logic. The key benefit over hand-rolled per-service resilience code is consistency: today, if 5 different teams implement their own retry logic, I'd bet on 5 different bugs. With a mesh, the retry policy is centrally defined and centrally auditable.
>
> The tradeoff I'd flag upfront: the mesh adds a real, measurable latency overhead — roughly 1-3ms per hop through a sidecar — and real memory cost per pod. For a system with 30 services and heavy internal fan-out, I'd consider that overhead well worth the consistency and operational visibility it buys. For a much smaller system, 3-4 services, I might skip the mesh and handle resilience in a shared library instead, since the operational complexity of running Istio isn't justified yet."

---

## PART 5 — DECISION FRAMEWORK

| Concern | API Gateway | Service Mesh |
|---|---|---|
| **Traffic direction** | North-south (external → internal) | East-west (internal service-to-service) |
| **Primary job** | AuthN at the edge, rate limiting per external consumer, routing, API composition | mTLS, retries, circuit breaking, load balancing, observability between services |
| **Where it lives** | One (or few) edge instances | A sidecar proxy per service instance |
| **Failure blast radius if down** | External traffic can't enter at all | Existing sidecars keep serving on last-known config; only NEW rule pushes are delayed |
| **Added latency** | One hop, at the edge only | 1-3ms per internal hop, multiplied across a call chain |
| **Adopt when** | You have ANY external clients | You have significant east-west traffic AND want consistent resilience/security without per-service code |
| **Skip when** | Single monolith, no external API surface | Small service count (3-4), low fan-out, or team lacks platform-ops capacity to run/debug a mesh |
