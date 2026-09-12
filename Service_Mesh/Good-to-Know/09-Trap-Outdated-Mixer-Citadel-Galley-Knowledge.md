# Trap 9: "Istio's Control Plane Is Made Up of Pilot, Citadel, Galley, and Mixer, Right?"

**Interviewer:** "Istio's control plane is made up of Pilot, Citadel, Galley, and Mixer, right?"

**Correct Answer: Outdated — this is a trap for stale knowledge.**

```
  BEFORE Istio 1.5:                    AFTER Istio 1.5 (current):
  ------------------------              ---------------------------
  Pilot   (config/routing)     -----\
  Citadel (certs/CA)           ------>   ALL MERGED into
  Galley  (config validation)  ------>   ONE single binary:
  Mixer   (telemetry & policy  -----/       istiod
          checks - IN THE
          REQUEST PATH, caused
          latency - REMOVED
          ENTIRELY, not just merged)
```

That was true **before Istio 1.5**. Since 1.5, all of these were consolidated into the single `istiod` binary, and **Mixer's in-request policy/telemetry checks were removed entirely** for performance reasons (not just merged elsewhere — the per-request policy check pattern itself was deprecated).

## Why It Was Consolidated

- Simpler operations, fewer moving parts to upgrade/monitor
- Lower latency (Mixer's per-request policy check was on the critical path of every single request, adding real overhead)
- Policy enforcement moved into Envoy itself (via native filters/WASM), not a separate out-of-process call

## Why This Trap Exists

Reciting the old 4-component architecture in a current-year interview signals **outdated, memorized documentation knowledge** rather than real, current operational experience. Correcting this (tactfully, if an interviewer states it as fact) is actually a great way to demonstrate depth — you know the history AND the current state.

---
See also: [01-Concepts-Reference.md — Part 7: Istio Architecture History](../Must-Know/01-Concepts-Reference.md#7-istio-deep-dive-architecture)
