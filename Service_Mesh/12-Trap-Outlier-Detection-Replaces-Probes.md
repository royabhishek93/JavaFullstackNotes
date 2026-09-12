# Trap 12: "The Mesh Handles Health Checking, So We Don't Need K8s Readiness/Liveness Probes Anymore, Right?"

**Interviewer:** "Since the mesh handles health checking of pods via outlier detection, we don't need Kubernetes readiness/liveness probes anymore."

**Correct Answer: No.**

```
  READINESS/LIVENESS PROBES                OUTLIER DETECTION (Envoy)
  (Kubernetes-level)                       (Mesh-level)
  --------------------------                ---------------------------
  Tells the Kubernetes Service/             Short-term, STATISTICAL
  Endpoints controller whether a            mechanism that temporarily
  pod should receive traffic AT ALL         EJECTS an endpoint from the
  (removes it from the Service's            LOAD-BALANCING POOL based
  endpoint list ENTIRELY)                   on RECENT ERROR PATTERNS

  Binary: in the pool, or not               Re-includes it after a
                                             cooldown to TEST recovery
                                             (half-open state)
```

Kubernetes' own readiness/liveness probes and the mesh's outlier detection operate at **different layers and different purposes**. Readiness probes are the authoritative signal for "is this pod part of the Service's endpoint list at all." Outlier detection is a shorter-term, statistical, Envoy-level mechanism layered on top of whatever endpoints are already in that list.

## You Need Both

```
  You need BOTH mechanisms - they COMPLEMENT each other:

  Readiness probe FAILS  --> pod removed from Endpoints list entirely
                              (Kubernetes-level, authoritative)

  Outlier detection       --> pod temporarily ejected from LB pool
  triggers                    due to recent errors, even though it's
                               still technically "ready" per K8s
                               (Envoy-level, statistical, short-term)
```

Neither replaces the other.

## Why This Trap Exists

"The mesh does health checking too" is true but incomplete — it tests whether you understand these are **two different layers solving two different problems** (membership in the endpoint list vs. short-term traffic-shaping based on recent error rates), not a redundant overlap where one can be safely dropped.

---
See also: [21-Scenario-Rescheduled-Pod-Discovery-vs-Draining.md](21-Scenario-Rescheduled-Pod-Discovery-vs-Draining.md), [01-Concepts-Reference.md — Part 4: Circuit Breaking](01-Concepts-Reference.md#4-traffic-management-canary-retries-circuit-breaking)
