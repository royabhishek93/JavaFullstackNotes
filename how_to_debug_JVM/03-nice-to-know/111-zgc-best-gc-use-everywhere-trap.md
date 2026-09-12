# #111 — ZGC is the best GC — we should use it everywhere in production

> **Category:** GC Tuning & Debugging | **Type:** Senior Trap Question | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"ZGC is the best GC — we should use it everywhere in production, right?"

## 😊 Explain It Simply (for anyone)
Think of two delivery vehicles: a nimble motorcycle that can weave through traffic instantly with zero waiting (great for urgent single-package deliveries), versus a big cargo truck that occasionally stops for a few minutes to reload, but can move ten times as many boxes overall per day. If your job is rushing a single urgent envelope across town, the motorcycle wins every time. But if your job is moving a warehouse full of boxes overnight, the truck — despite its occasional stops — gets far more total work done. ZGC is the motorcycle: incredibly smooth, no noticeable stops, perfect for time-sensitive requests. But it burns extra "fuel" (CPU) constantly to stay that responsive, which isn't worth it for bulk, throughput-focused jobs where nobody's watching a stopwatch.

## 📊 Visualize It
```
Workload:              Right GC:        Why:
─────────────────────────────────────────────────────
REST API (p99 SLA)      ZGC              latency matters most
Real-time trading       ZGC/Shenandoah   can't tolerate STW at all
Nightly batch job        ParallelGC       throughput matters, no SLA
Spark executor           ParallelGC       CPU for compute > pause avoidance
```

## 🏭 The Real Production Answer (15-YOE Level)
**WRONG. The experienced answer:**

> ZGC is the right choice for latency-sensitive services with p99 pause SLAs under 10ms. But it has real costs that make it wrong for other workloads.
>
> ZGC's concurrent GC threads consume 20–30% of CPU that would otherwise run application code. For a batch job or stream processor maximizing throughput, that's a significant throughput tax. ParallelGC gives you all the CPU for application work during GC-free periods, then stops briefly.
>
> I'd use ZGC for: REST APIs with latency SLAs, real-time data processing, user-facing services. I'd use ParallelGC or G1GC for: nightly batch jobs, Spark executors, data pipeline stages, anything where throughput > latency.
>
> Using ZGC blindly in a Spark job would be architecturally unsound.

## 🔑 Key Takeaway
GC choice should match the workload's SLA — ZGC for latency-critical services, ParallelGC/G1GC for throughput-focused batch and data pipelines.
