# Scenario 5: The CFO Asks If a Few Extra Milliseconds of Latency Is Worth the Mesh

**Interviewer:** "We noticed our microservices latency went up by ~3-8ms per hop after installing the mesh. The CFO is asking if it's worth it."

**You (15-yr Architect):**

This is real and expected — every hop now goes app → local sidecar → network → remote sidecar → app, instead of app → network → app directly. That's the "sidecar tax." My answer to the CFO isn't to deny it, it's to frame the trade-off.

## The Honest Trade-Off

```
  Without mesh:   App A ------------------------------> App B
                          (direct network hop)

  With mesh:      App A -> Sidecar A -> [network] -> Sidecar B -> App B
                          (extra 2 local hops, ~3-8ms typically)
```

- A few milliseconds of added latency, in exchange for: consistent mTLS everywhere (which would otherwise require *months* of dev effort per team), zero-code circuit breaking/retries, and full observability — that's usually a very good trade for anything beyond a handful of services.
- If latency is truly critical (e.g., a sub-millisecond trading system), that's a case where you might not use a sidecar mesh at all, or you'd look at **ambient mesh** (Istio's sidecar-less mode using node-level proxies, `ztunnel`) which reduces the per-pod overhead, or a lighter mesh like Linkerd (written in Rust, historically lower overhead than Envoy/C++).

## Framing for a Non-Technical Stakeholder

| Cost | Benefit Received in Exchange |
|---|---|
| ~3-8ms latency per hop | mTLS everywhere with zero dev effort per team |
| Extra CPU/memory per pod (sidecar) | Zero-code retries, timeouts, circuit breaking |
| New operational surface (control plane to run/upgrade) | Uniform observability across every service, regardless of language |
| Learning curve for the platform team | Consistent security/compliance posture, auditable centrally |

## Why This Matters for the Interview

> "I don't sell the mesh as 'free.' I sell it as a trade of a small, measurable latency cost for a large reduction in per-team engineering effort and security risk. And if the workload genuinely can't tolerate that cost, I'd recommend evaluating ambient mesh or a lighter-weight proxy instead of forcing sidecar mode everywhere."

---
See also: [28-Advanced-Ambient-Mesh-Migration.md](28-Advanced-Ambient-Mesh-Migration.md), [04-Trap-Do-You-Even-Need-A-Mesh.md](04-Trap-Do-You-Even-Need-A-Mesh.md)
