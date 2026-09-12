# #145 — Fleet-Wide Continuous Profiling with eBPF (Grafana Pyroscope / Parca)

> **Category:** Modern Observability (2026) | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know (2026 additions)

## 🗣️ The Interview Question
"You run the same Spring Boot service as 300 pods across 12 regions. CPU is intermittently elevated on some unknown subset of pods, at some unknown time. You can't SSH into 300 pods and run `async-profiler` reactively every time it happens. How do you find the hot pod, the hot version, and the hot method — without ever touching a box?"

## 😊 Explain It Simply (for anyone)
Imagine a car dashcam that's *always recording*, versus pulling over every time you hear a weird noise to take a photo of the engine. The old way (SSH in, run `async-profiler` for 60 seconds) is like pulling over — you have to already suspect something is wrong, and you only capture what happens during that one window. Continuous profiling is the dashcam: a tiny recorder runs on every single car (every pod, every node) all the time, constantly saving a low-detail flight log. When something weird happens, you don't drive out to find the car — you just rewind the footage from your office, for any car, any time, any place, because it was always being recorded centrally.

## 📊 Visualize It
```
Node 1                    Node 2                    Node N
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│ eBPF/agent       │      │ eBPF/agent       │      │ eBPF/agent       │
│ DaemonSet        │      │ DaemonSet        │      │ DaemonSet        │
│ (profiles ALL    │      │ (profiles ALL    │      │ (profiles ALL    │
│  processes on    │      │  processes on    │      │  processes on    │
│  the node)       │      │  the node)       │      │  the node)       │
└────────┬─────────┘      └────────┬─────────┘      └────────┬─────────┘
         │  push pprof every 10-15s, tagged:               │
         │  {service="checkout", pod="x", version="v42"}   │
         └──────────────────────┬───────────────────────────┘
                                 v
                    ┌────────────────────────┐
                    │  Pyroscope / Parca      │
                    │  server (queryable by   │
                    │  label, like PromQL)    │
                    └────────────────────────┘
                                 |
        query: service=checkout-service AND version=v42
        over the exact 2-minute window the alert fired
                                 v
                    Flame graph for THAT pod, THAT time
                    — zero SSH, zero manual profiler run
```

## 🏭 The Real Production Answer (15-YOE Level)
"Reactive, per-incident profiling (SSH + `async-profiler.sh -d 60`) doesn't scale past a handful of instances — you can't predict which of 300 pods will spike next. The fix is always-on, fleet-wide continuous profiling, which is where I've used **Grafana Pyroscope** (formerly Pyroscope OSS, now part of Grafana's LGTM stack) or **Parca** (Polar Signals).

**Deployment shape:** roll out the Pyroscope/Parca agent as a Kubernetes DaemonSet (one agent per node, not per pod) using eBPF to sample **every process on the node** without any code change or JVM flag on the target application. It periodically (default ~19Hz–99Hz) walks the stack of running processes via eBPF perf events, tags each sample with Kubernetes metadata (namespace, pod, deployment, container, and — critically — I add a `version` label sourced from the deployment's image tag) and pushes compressed pprof-format profiles to the central Pyroscope server every 10–15 seconds.

**The important nuance most people get wrong:** pure eBPF stack-walking works great for compiled/native code (C, Go, Rust) because frame pointers are stable, but the JVM's JIT-compiled frames historically don't unwind cleanly with generic eBPF stack walkers — the JIT doesn't preserve frame pointers by default. For Java specifically, Pyroscope actually bundles and drives **async-profiler in continuous mode** under the hood (not pure eBPF for the Java call stack itself, though it uses eBPF for the node-level orchestration and off-CPU/lock profiling) — this is a detail I always clarify because it shows you understand *why* Java is a special case, not just that 'eBPF profiles everything.' To get accurate JIT symbolication you still want `-XX:+PreserveFramePointer` set, same flag that matters for perf/eBPF-based Java profiling in general.

**How I actually use it during an incident:** open the Pyroscope UI, filter by `service=checkout-service`, group by `version` label, and select the exact 5-minute window the alert fired. I get a flame graph merged across every pod matching that filter for that time range — if one canary version (`v43`) is hot and the stable version (`v42`) isn't, that's immediately visible as two separate flame graphs I can diff (same differential technique as file #140, but comparing *fleet-wide* data instead of two manual profiler runs). No SSH, no reactive scramble, no missing the window because the spike stopped before I got a terminal open.

**Real gotchas I've hit:**
- eBPF needs `CAP_BPF`/`CAP_SYS_ADMIN` and often `hostPID: true` on the DaemonSet — this is a security review conversation in regulated environments (see file #149 on why this isn't a 'just enable it everywhere blindly' decision).
- Managed Kubernetes (EKS/GKE) sometimes restricts privileged DaemonSets by default — you need a dedicated node group or an exception from the platform team.
- Storage cost: continuous profiling at fleet scale generates a lot of profile data — configure retention (e.g., 7–14 days raw, downsampled/aggregated beyond that) or costs balloon.
- This complements, it doesn't replace, on-demand JFR (file #086) — continuous profiling is lower-fidelity/lower-frequency by design to keep overhead low; when you've narrowed to one pod, a targeted JFR recording still gives you richer event data (allocation profiling, lock contention detail, GC correlation) than the fleet-wide sampled view."

## 🔑 Key Takeaway
Reactive per-incident profiling (SSH + `async-profiler`) doesn't scale past a few instances — continuous eBPF-based fleet profiling (Grafana Pyroscope/Parca) runs as a DaemonSet, tags every sample with k8s labels, and lets you query any pod's flame graph for any past time window with zero SSH access; for Java specifically it still relies on async-profiler under the hood for accurate JIT stack symbolication, not pure eBPF stack walking.
