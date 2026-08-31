# #100 — "G1GC always performs better than Parallel GC because it's newer"

> **Category:** JVM Tuning Production Playbook | **Type:** Senior Trap Question | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"G1GC always performs better than Parallel GC because it's newer."

## 😊 Explain It Simply (for anyone)
Newer isn't automatically better — it depends on the job. A modern hybrid car (G1GC) is fantastic for stop-and-go city driving where smooth, predictable behavior matters (a live, user-facing service where pause times matter). But if you just need to haul the maximum amount of cargo across an empty highway overnight with nobody around to notice a bumpy ride (an overnight batch job processing huge data with no live users waiting), an old-fashioned diesel truck built purely for raw hauling power (Parallel GC) can actually get the job done faster, because it isn't spending extra fuel and effort trying to be smooth and considerate along the way.

## 📊 Visualize It
```
                Parallel GC            G1GC
Batch job       ✅ max throughput      overhead from region mgmt
Small heap<2GB  ✅ efficient           overhead not worth it
Latency SLA     ❌ long pauses         ✅ tunable pause target
Large heap 4GB+ ❌ pauses grow         ✅ handles it well
```

## 🏭 The Real Production Answer (15-YOE Level)
> "G1GC is the better default for most workloads, but Parallel GC is still superior for
> specific scenarios. 'Newer' does not mean 'always better.'
>
> Parallel GC wins when:
> 1. Batch processing jobs: You're processing 100GB of data, and you don't have users waiting.
>    You want maximum throughput, and pause times are irrelevant.
>    Parallel GC dedicates all GC threads to stop-the-world collection = higher throughput.
>
> 2. Simple heaps: If your service has simple object lifecycle (allocate, process, discard),
>    no long-lived objects, Parallel GC's simple generational approach is very efficient.
>    G1GC's complexity adds overhead for simple workloads.
>
> 3. Small heaps (<2GB): G1GC's region-based approach adds overhead below certain heap sizes.
>    For small heaps, Parallel GC or even Serial GC is more efficient.
>
> G1GC wins when:
> - Mixed workloads with both short-lived and long-lived objects
> - Latency matters (G1GC can target pause times with MaxGCPauseMillis)
> - Large heaps (4GB+) where Parallel GC pauses become unacceptable
> - Services with SLAs or user-facing latency requirements
>
> Example production scenario where I used Parallel GC:
> Nightly ETL job processing 50GB of customer records, runs from 2am-4am,
> no users affected by pauses, needs maximum throughput.
> Parallel GC with -XX:ParallelGCThreads=16 was 25% faster than G1GC for this workload."

## 🔑 Key Takeaway
Choose the GC by workload shape, not by release date — Parallel GC still wins for throughput-only batch jobs and small simple heaps, while G1GC wins for latency-sensitive, mixed-object, large-heap services.
