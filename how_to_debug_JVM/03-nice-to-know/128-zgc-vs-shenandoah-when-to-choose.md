# #128 — ZGC vs Shenandoah — When to Choose Which

> **Category:** JVM Tuning Production Playbook | **Type:** Advanced Scenario Q&A | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"Walk me through the differences between ZGC and Shenandoah. When would you pick one over the other in production?"

## 😊 Explain It Simply (for anyone)
Think of both ZGC and Shenandoah as two different brands of "self-cleaning ovens" (low-pause garbage collectors) — both let the kitchen (your app) keep cooking (serving requests) while the cleaning happens quietly in the background, instead of the old-fashioned way where the whole kitchen shuts down for cleaning (a long stop-the-world pause). ZGC is like the newer, official oven from the manufacturer (Oracle/OpenJDK) built for massive kitchens (terabyte-scale heaps) and gets even better with a newer "eco mode" (Generational ZGC in Java 21+). Shenandoah is a competing brand (Red Hat) with a similar self-cleaning feature, notable because it's also available in older ovens (backported to Java 8) if you're stuck with legacy equipment. Neither is "better" universally — the right pick depends on your Java version, heap size, and how much extra electricity (CPU overhead) you're willing to pay for the quiet cleaning.

## 📊 Visualize It
```
        Java 8   Java 11-17   Java 21+
ZGC        ✗         ✓          ✓✓ (Generational, best)
Shenandoah ✓         ✓          ✓
                                  
Pick by: heap size, latency SLO, JDK vendor (Oracle license),
         team familiarity/tooling
```

## 🏭 The Real Production Answer (15-YOE Level)
> "Both are low-pause GC algorithms designed to scale to terabyte heaps with sub-millisecond pauses.
> The key differences:
>
> ZGC:
> - Oracle/OpenJDK developed, production-ready from Java 15
> - Handles heaps from 8MB to 16TB
> - All GC work is concurrent (relocation is also concurrent in ZGC Gen since Java 21)
> - Pause times are O(1) — fixed overhead regardless of heap size
> - Generational ZGC (Java 21+): adds generational collection, better throughput than old ZGC
> - CPU overhead: 10-20% higher than G1GC
>
> Shenandoah:
> - Red Hat developed, available in OpenJDK and GraalVM
> - Similar pause profile to ZGC
> - Available in Java 8 (backport) — useful if you're on older Java but need low pause
> - Concurrent compaction phase slightly different algorithm
> - Often slightly higher throughput than old ZGC pre-Java 21
>
> My production decision tree:
>
> - Java 21+ with large heap (8GB+), latency-critical: Use Generational ZGC
>   -XX:+UseZGC -XX:+ZGenerational
>   Best of both worlds: low pauses AND good throughput
>
> - Java 11-17, large heap, latency-critical: ZGC or Shenandoah are comparable
>   Team familiarity/tooling decides
>
> - Java 8 (legacy constraint), low pause needed: Shenandoah backport is your only option
>
> - Oracle JDK constraint (commercial license), Java 17: G1GC with tuning,
>   ZGC available in Oracle JDK from Java 15
>
> In practice I've run ZGC in production on payment processing services — the sub-millisecond pause
> guarantee is transformative for P99 latency SLOs. The CPU cost was worth it at 10% extra."

## 🔑 Key Takeaway
On Java 21+, Generational ZGC is the default answer for large, latency-critical heaps; Shenandoah earns its place mainly when you're stuck on Java 8 and still need low pauses.
