# API Gateway & Service Mesh — LinkedIn Post

## Post Text (copy-paste ready)

5 teams. 5 different retry implementations calling one payment service. One retry storm.

That's what happens when microservices have no shared traffic layer. Here's the fix, in one architectural distinction most engineers blur in interviews:

- API Gateway = north-south traffic (outside → in). ONE place for auth, per-consumer rate limiting, routing, and request aggregation — a mobile client hits one endpoint, the gateway fans out to 3 services and merges the response.
- Service Mesh = east-west traffic (service ↔ service). A sidecar proxy (Envoy) next to every instance handles retries, circuit breaking, mTLS, and load balancing — transparently, with zero resilience code in your business logic.
- The mesh isn't free: ~1-3ms latency per hop and ~40-100MB memory per pod. At 3-4 services with low fan-out, skip it and use a shared library instead.
- Control plane (istiod) ≠ hot path. If it goes down, sidecars keep serving on last-known config — but new rule propagation still takes 1-10 seconds across a large cluster.
- Real production systems run BOTH. Gateway with no mesh = every service reinvents resilience. Mesh with no gateway = no single place to stop external abuse.

Swipe → to see the north-south vs east-west diagram, the sidecar interception mechanism, and the exact decision table.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
5 teams, 5 retry implementations, 1 outage. Gateway vs Mesh — the distinction every system design interview tests. 🎥👇

### Variant B — Long (400-600 chars)
30 microservices. 5 teams each hand-rolled their own retry logic for calling payment-service. One team retried 10x with zero backoff — and turned a 10-second blip into a 20-minute outage. This is why real systems run an API Gateway (north-south: auth, rate limits, routing at the edge) AND a Service Mesh (east-west: sidecar-based retries, circuit breaking, mTLS between services) — not one or the other. Sidecars cost ~1-3ms/hop and 40-100MB/pod, so skip the mesh below 3-4 services. Full breakdown, real config examples, and the interview answer that nails this question — link below.

---

## Best Time to Post
Tuesday or Wednesday, 8:30–9:30 AM IST (before the Indian tech workday starts, peak LinkedIn scroll for engineers commuting/starting work).

## Engagement Hook
Do you run an API Gateway, a Service Mesh, or both at your company — and if you skipped one, what made you decide against it?
