# Trap 4: "If the Control Plane Goes Down, All Communication Stops Immediately, Right?"

**Interviewer:** "If the Istio control plane (`istiod`) or Consul servers go down, all service-to-service communication stops immediately, right?"

**Correct Answer: No, not immediately.**

This is the trap that separates people who've actually run these in production from people who've only read the docs.

```
  Control plane (istiod / Consul servers) GOES DOWN
                |
                v
  Envoy proxies still have their LAST-KNOWN xDS config
  and certificates CACHED locally
                |
                v
  EXISTING traffic keeps flowing normally
                |
                v
  What actually breaks:
    - New pods CANNOT get sidecars injected/configured
    - Certificate rotation STOPS
      (eventually, once existing certs expire,
       mTLS connections WILL start failing)
    - Topology changes (new/removed services)
      will NOT propagate to other proxies
```

## Why Production Runs 3-5 Replicas

This exact behavior is why production deployments run **3-5 control plane replicas** with quorum (Raft for Consul), not a single instance — to make control plane outages rare in the first place, since the "grace period" from cached config is finite and eventually degrades.

## Why This Trap Exists

It sounds like a simple, alarmist yes/no question, but the nuanced answer — **cached config buys you time, but doesn't make the control plane optional** — is exactly the kind of operational detail that only shows up if you've actually operated one of these systems through an incident.

---
See also: [01-Concepts-Reference.md — Part 2: Control Plane vs Data Plane](01-Concepts-Reference.md#2-sidecar-pattern-control-plane-vs-data-plane), [01-Concepts-Reference.md — Part 8: Consul Raft](01-Concepts-Reference.md#8-consul-deep-dive-architecture)
