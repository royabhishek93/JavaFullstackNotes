# Trap 8: "Enabling Mesh-Wide Auto-Injection for Everything Is the Recommended Production Practice, Right?"

**Interviewer:** "Setting `connectInject.default=true` (Consul) or enabling namespace-wide injection (Istio) for the whole cluster is the recommended production practice, since it's simpler."

**Correct Answer: Careful/nuanced answer required — this is a trade-off, not a flat yes/no.**

```
  Namespace/cluster-wide auto-injection = TRUE
                |
                v
  EVERY pod in that scope gets a sidecar automatically,
  including things you might NOT want in the mesh:
    - Short-lived Jobs/CronJobs
    - Third-party Helm-installed tools
    - Monitoring agents with their own service accounts
      that shouldn't be subject to the same
      authorization policies as business services
```

It's simpler operationally (no per-deployment annotations), and that's genuinely useful. But in regulated/production environments, many architects prefer **explicit opt-in per namespace or per deployment annotation** for tighter control over what's actually inside the mesh's trust boundary — even though it's more manual.

## The Trap Inside the Trap

There's no universally "correct" answer here — the actual trap is answering with a flat **yes** ("yes, always enable it, it's simpler") or a flat **no** ("no, never enable it, always be explicit") instead of discussing the **trade-off**:

| Approach | Pro | Con |
|---|---|---|
| Cluster/namespace-wide auto-inject | Simple, no per-deployment boilerplate | Every pod in scope is in the mesh trust boundary, including things you may not want there |
| Explicit opt-in annotation per deployment | Tight control over exactly what's in the mesh | More manual, easy to forget on a new service (accidentally leaving it unprotected) |

## Why This Trap Exists

Interviewers use "isn't X simpler, so we should always do X" framing specifically to see if you'll take the bait and give a one-sided answer, versus demonstrating judgment about when the simpler default is appropriate and when it isn't.

---
See also: [01-Concepts-Reference.md — Part 2: Sidecar Injection](../Must-Know/01-Concepts-Reference.md#2-sidecar-pattern-control-plane-vs-data-plane)
