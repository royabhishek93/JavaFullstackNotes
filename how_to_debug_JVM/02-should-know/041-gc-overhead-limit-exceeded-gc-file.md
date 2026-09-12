# #41 — We're getting java.lang.OutOfMemoryError: GC overhead limit exceeded

> **Category:** GC Tuning & Debugging | **Type:** Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"We're getting java.lang.OutOfMemoryError: GC overhead limit exceeded. What does this error mean and how do you fix it?"

## 😊 Explain It Simply (for anyone)
Picture a warehouse worker whose entire job is sorting boxes into "keep" and "throw away" piles. Now imagine the throw-away pile has shrunk to almost nothing — the worker is spending 98% of their shift just walking around searching for anything to discard, and only manages to clear out a tiny sliver of space each time. At some point, the warehouse manager says "this is pointless, we're not gaining anything" and shuts the whole operation down. That's what this error means: the JVM's garbage collector (its "sorting worker") is working almost non-stop but barely freeing any memory. Rather than let the app spin in this useless loop forever, the JVM gives up and throws an error. It's the JVM's way of saying "I'm not stuck, I'm just fighting a losing battle" — usually because something in your code keeps creating objects that never get thrown away (a memory leak), or the workload has simply outgrown the amount of memory it's given.

## 📊 Visualize It
```
GC Effort vs Memory Freed:
  ┌─────────────────────────────┐
  │ CPU Time:  ██████████████ 98%│ ← spent in GC
  │ Freed:     █ 2%              │ ← barely any space reclaimed
  └─────────────────────────────┘
        JVM: "Not worth continuing" → throws OOM
```

## 🏭 The Real Production Answer (15-YOE Level)
> This error is triggered by the JVM ergonomics when 98% of CPU time is spent in GC and less than 2% of the heap is being freed. The JVM decides it's more useful to throw an OOM than to keep thrashing.
>
> It's almost always a memory leak or a workload that has outgrown the heap. The GC is working correctly — it just cannot win.

**Diagnostic approach:**

```bash
# Add heap dump on OOM to capture the leak
-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/var/dumps/heapdump.hprof

# Analyze with jmap (if still running before OOM):
jmap -histo:live <pid> | head -30
# Look for: which classes dominate object count AND retained size

# jstat for live monitoring:
jstat -gcutil <pid> 1000 60
# Output columns: S0 S1 E   O    M    CCS  YGC  YGCT  FGC  FGCT  GCT
# Watch O (Old gen %) — if it hits 99% and stays there, you have a leak
```

**Fix strategies:**
1. **Code-level**: Find and fix the leak (cache with no eviction, static collections, listener not deregistered, ThreadLocal not removed)
2. **Temporary relief**: Increase heap size to buy time for investigation
3. **Disable the limit** (use only for investigation, never production): `-XX:-UseGCOverheadLimit`

## 🔑 Key Takeaway
"GC overhead limit exceeded" means the GC is working correctly but losing — it's a memory leak signal, not a GC tuning problem.
