# #96 — High CPU Usage After Deployment Despite Low Traffic

> **Category:** JVM Tuning Production Playbook | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"Immediately after deployment, CPU is pegged at 80-90% even with only 10 RPS. After 2 minutes it drops to 5%. What's happening?"

## 😊 Explain It Simply (for anyone)
Picture movers unloading a truck (starting the app) — for the first few minutes there's a flurry of intense activity (boxes flying everywhere, people running), but once everything is unpacked and organized, things calm down to a normal pace. That initial CPU spike is the JVM's "compiler workers" (the JIT) furiously translating your frequently-used code into fast machine instructions all at once, even though actual customer traffic (10 RPS) is light. This is usually healthy and expected — the real question is only whether your health-check systems (Kubernetes probes) get spooked by the noise and kill the pod before the movers finish unpacking.

## 📊 Visualize It
```
CPU %
 90 |██████████
    |██████████
    |██████████
  5 |██████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
    └──────────┴──────────────────────────────► time
     0        2 min                    (steady state)
     JIT compiling hot methods at startup burst
```

## 🏭 The Real Production Answer (15-YOE Level)
> "This is the JIT compiler at work. During warm-up, the JIT compilation threads run at full blast
> compiling hot methods. For a Spring Boot app, startup involves a burst of class loading and
> compilation activity.
>
> This is actually expected and generally healthy. The question is whether it's causing a problem.
>
> If 2 minutes of high CPU causes pods to be killed by K8s liveness probes or causes SLO violations:
>
> Fix 1: Tune liveness probe to give JVM time to warm up
>   livenessProbe:
>     initialDelaySeconds: 60    # Was 10
>     periodSeconds: 10
>     failureThreshold: 3
>
> Fix 2: Separate readiness from liveness
>   readinessProbe: check if app is ready to serve
>   livenessProbe: check if app is still alive (longer timeout)
>
> Fix 3: Limit JIT compiler thread count to reduce startup CPU burst
>   -XX:CICompilerCount=2    # Default is proportional to CPU count
>   Trade-off: slower warm-up but smoother CPU curve
>
> Fix 4: If using HPA (Horizontal Pod Autoscaler), it may scale up during startup thinking it needs
> more pods. Add a cool-down period or use custom metrics that exclude startup phase."

## 🔑 Key Takeaway
A CPU spike right after deploy that settles down on its own is usually the JIT compiler working as designed — tune your probes and HPA, don't tune away the compiler.
