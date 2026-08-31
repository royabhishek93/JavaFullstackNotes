# #40 — Our API p99 latency spiked from 80ms to 2 seconds intermittently

> **Category:** GC Tuning & Debugging | **Type:** Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"Our API p99 latency spiked from 80ms to 2 seconds intermittently. How do you diagnose?"

## 😊 Explain It Simply (for anyone)
Imagine a busy restaurant kitchen where, every so often, the head chef yells "everybody freeze!" so the kitchen can be tidied up — dirty plates cleared, counters wiped — before service resumes. Most of the time this tidy-up is quick, a few seconds, and customers barely notice. But sometimes the tidy-up takes much longer because there's a huge mess to clean, and every order grinds to a halt during that time. That's exactly what's happening in your API: the JVM (the program running your Java app) periodically "freezes" everything to clean up memory (this is called Garbage Collection, or GC — like the kitchen cleanup). The first step in diagnosing a latency spike is simple: check if the "freeze" (GC pause) happened at exactly the same moment as the slow request. If they line up every time, you've found your culprit. Then you figure out *what kind* of cleanup was happening — a quick daily wipe-down (small GC) or a full deep-clean of the entire kitchen (a "Full GC", the most expensive kind).

## 📊 Visualize It
```
Request Timeline:
  ...80ms...80ms...80ms...[STOP-THE-WORLD GC]...80ms...
                              │
                    App Threads: ⏸️ PAUSED
                    GC Threads:  🧹 cleaning heap
                              │
                         2000ms later
                    App Threads: ▶️ RESUME
                              │
                 p99 latency spike = GC pause duration
```

## 🏭 The Real Production Answer (15-YOE Level)
> First, correlate the latency spike timestamp with GC log timestamps. If every spike aligns with a GC pause, you have your answer.
>
> Check what type of GC: Young GC at 2 seconds is unusual and points to a huge young gen or excessive live objects. Mixed GC at 2 seconds suggests old gen work is too expensive per mixed cycle. Full GC at 2 seconds means the entire heap is too large, or something forced a Full GC prematurely.
>
> Look for these patterns in the GC log around the spike time:
> - `Pause Full` — definitive Full GC, find the trigger
> - `To-space exhausted` — evacuation failure, survivor regions full
> - `Humongous object allocation` — large objects bypassing young gen

**Root cause investigation steps:**

```bash
# Find Full GC events in log
grep "Pause Full" /var/log/app/gc.log | tail -20

# Find events > 500ms (adjust threshold)
grep -E "\) [0-9]{3,}(\.[0-9]+)?ms$" /var/log/app/gc.log

# Check Humongous allocations
grep -i "humongous" /var/log/app/gc.log | tail -20

# Check heap occupancy trend (before→after pattern)
grep "Pause Young\|Pause Mixed\|Pause Full" /var/log/app/gc.log \
  | awk '{print $NF, $(NF-1)}' | tail -50
```

**Fix path:**
1. If Full GC: find what caused it (promotion failure, humongous, Metaspace)
2. If humongous: increase `-XX:G1HeapRegionSize` so objects < half region size
3. If promotion failure: increase `-XX:G1NewSizePercent` or total heap

## 🔑 Key Takeaway
Always correlate latency spikes with GC log timestamps first — the GC type (Young/Mixed/Full) tells you exactly where to look next.
