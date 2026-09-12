# Scenario 6: Rolling Deployments Cause a Few Seconds of 502 Errors

**Interviewer:** "During a rolling deployment, we saw 502 errors for a few seconds every time. Why, and how do we fix it?"

**You (15-yr Architect):**

Classic **race condition between the sidecar and the app container starting/stopping**.

## Pod Startup Race Condition (ASCII sequence)

```
  Kubernetes           App Container          Sidecar (Envoy)
      |                     |                       |
      |--- Start Sidecar -------------------------->|
      |--- Start App ------>|   (in parallel, no guaranteed order!)
      |                     |                       |
      |                     |--traffic arrives------>| (iptables rules /
      |                     |   BEFORE sidecar is    |  cert not ready yet)
      |                     |   ready --> REQUEST FAILS
```

## Pod Termination Race Condition (ASCII sequence)

```
  Kubernetes           App Container          Sidecar (Envoy)
      |                     |                       |
      |--- SIGTERM -------->|                       |
      |--- SIGTERM (same time!) -------------------->|
      |                     |                       |
      |                     |  Sidecar exits BEFORE  |
      |                     |  app finishes in-flight|
      |                     |  requests / graceful   |
      |                     |  shutdown --> 502s     |
```

## Startup & Termination Races (Sequence Diagram)

```
Kubernetes (K8s)        App Container               Sidecar (Envoy)
     |                        |                            |
     |==================== Startup race ==========================|
     |--- start sidecar --------------------------------------->|
     |--- start app (parallel, no guaranteed order) ------------>|
     |                        |-- traffic arrives before sidecar  |
     |                        |   iptables/certs ready [self]     |
     |<-- request fails (502) |                            |
     |                        |                            |
     |================== Termination race =========================|
     |--- SIGTERM ------------>|                            |
     |--- SIGTERM (same time) ----------------------------->|
     |                        |                            |-- exits before app
     |                        |                            |   finishes in-flight
     |                        |                            |   requests [self]
     |<-- graceful shutdown interrupted -> 502s -|            |
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## The Fix

Use **Kubernetes native sidecar containers** (`restartPolicy: Always` on init containers, GA since Kubernetes 1.29) so the sidecar is guaranteed to **start first and stop last**, or configure Istio's `holdApplicationUntilProxyStarts` and appropriate `preStop` hooks / termination grace periods so the sidecar outlives the app just long enough to flush in-flight connections.

| Problem | Fix |
|---|---|
| App starts serving before sidecar's iptables/certs are ready | Native sidecar containers, or `holdApplicationUntilProxyStarts: true` |
| Sidecar exits before app finishes in-flight requests | `preStop` hook with a short sleep on the sidecar, longer `terminationGracePeriodSeconds` |

## Why This Matters for the Interview

> "This is a startup/shutdown ordering problem, not a routing problem. Kubernetes doesn't guarantee container start order in a regular pod spec — native sidecar containers (a relatively recent Kubernetes feature) solve this properly instead of relying on brittle sleep-based workarounds."

---
See also: [01-Concepts-Reference.md — Part 2: Sidecar Injection](01-Concepts-Reference.md#2-sidecar-pattern-control-plane-vs-data-plane)
