# #32 — GC Overhead Limit Exceeded vs Heap Space OOM

> **Category:** Heap Dump Analysis | **Type:** Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"You see 'GC overhead limit exceeded' — same as heap space OOM?"

## 😊 Explain It Simply (for anyone)
Imagine the cleanup crew (Garbage Collector) working around the clock, running back and forth constantly trying to find space, but nearly every trip they come back with almost nothing cleared. Eventually the warehouse manager says "the crew is spending literally all its time cleaning and getting almost nothing back — this is unsustainable," and shuts things down even though technically there might be a tiny sliver of shelf space left.

That's different from the warehouse being 100% completely full (heap space OOM) — this is more like being told "you're allowed to keep cleaning forever but it's pointless, so we're stopping now" because the cost (CPU time) of continued cleaning outweighs the benefit.

## 📊 Visualize It
```
Full GC #1: CPU 98%, reclaimed 1.8% of OldGen
Full GC #2: CPU 99%, reclaimed 1.5% of OldGen
Full GC #3: CPU 98%, reclaimed 1.1% of OldGen
Full GC #4: CPU 99%, reclaimed 0.9% of OldGen
Full GC #5: CPU 98%, reclaimed 0.7% of OldGen
                     ─────────────────────────
      >98% CPU on GC AND <2% reclaimed, 5x in a row
                     ─────────────────────────
         ⇒ "GC overhead limit exceeded" thrown
            (app is alive but effectively frozen)
```

## 🏭 The Real Production Answer (15-YOE Level)

Mechanically different trigger, same root cause category.

The JVM throws this when it spends more than 98% of CPU time on GC and recovers less than 2% of heap across the last 5 consecutive Full GCs. The default thresholds are `-XX:GCTimeLimit=98 -XX:GCHeapFreeLimit=2`.

This often surfaces *before* raw heap exhaustion. The process is technically alive but effectively frozen — every thread is blocked waiting for GC to complete.

Diagnosis:
```bash
# Check GC log for "GC overhead" trigger vs heap exhaustion
grep -i "overhead\|OutOfMemory" /logs/gc.log

# Use jstat to watch live GC behavior (safer than heap dump capture)
jstat -gcutil <pid> 1000 60
# Columns: S0 S1 E(den) O(ld) M(etaspace) YGC YGCT FGC FGCT GCT
# Watch: FGC climbing fast, O column near 100% = Old Gen full, leak confirmed
```

Fix approach: Same as heap space OOM — find the retention root. Do NOT just add `-XX:-UseGCOverheadLimit` to suppress the error; that hides the symptom, not the cause.

## 🔑 Key Takeaway
This error fires before full exhaustion — treat it as an early warning of the same leak, not a different bug, and never suppress it with `-XX:-UseGCOverheadLimit`.
