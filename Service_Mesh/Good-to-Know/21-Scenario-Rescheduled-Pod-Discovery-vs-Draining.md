# Scenario 8: A Rescheduled Pod Causes 30 Seconds of Breakage Despite "Service Discovery"

**Interviewer:** "The recommendation-service depends on user-auth-service and product-catalog. One day user-auth-service was rescheduled to a new pod and everything broke for 30 seconds. Isn't service discovery supposed to prevent that?"

**You (15-yr Architect):**

Kubernetes' own `ClusterIP` Service already solves the "IP changed" problem via a stable virtual IP + DNS. So this isn't a discovery issue — it's more likely a **connection draining** issue: the old pod's connections were abruptly cut instead of drained gracefully, or the sidecar's health-check interval was too slow to detect the new endpoint.

## What Actually Happened (ASCII)

```
  user-auth-service pod (old) -- gets terminated / rescheduled
              |
              v
  Old pod's in-flight connections abruptly cut
  (no connection draining configured)
              |
              v
  Mesh's outlier detection / health check interval
  is too slow to mark old endpoint dead / new endpoint ready
              |
              v
  ~30 seconds of failed requests until endpoints list
  and health status converge
```

## Where to Look

| Setting | What It Controls |
|---|---|
| `readinessProbe` timing (`initialDelaySeconds`, `periodSeconds`) | How fast Kubernetes marks a new pod ready to receive traffic in the first place |
| Outlier detection `interval` / `baseEjectionTime` | How fast Envoy detects an endpoint is unhealthy and stops sending it traffic |
| `preStop` hook + `terminationGracePeriodSeconds` | Whether the old pod is given time to finish in-flight requests before hard termination |
| Connection draining config | Whether existing connections are allowed to complete before the endpoint is fully removed |

## Why This Matters for the Interview

> "Service discovery answers 'where is this service now' — Kubernetes and the mesh both do that well. This incident was about *timing*: how fast the system detects a change and how gracefully it drains the old endpoint. Those are two completely different mechanisms, and conflating them is a common mistake when debugging these incidents."

---
See also: [20-Scenario-Rolling-Deployment-502-Errors.md](20-Scenario-Rolling-Deployment-502-Errors.md), [12-Trap-Outlier-Detection-Replaces-Probes.md](12-Trap-Outlier-Detection-Replaces-Probes.md)
