# #93 — "We Fixed the Leak — Heap Is Stable"

> **Category:** Memory Leaks End-to-End | **Type:** Senior Trap Question | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"The team says they fixed the leak because heap usage is now stable after the fix. How do you verify this is actually fixed?"

## 😊 Explain It Simply (for anyone)
Declaring victory because "the graph looks flat now" is like checking if it's raining by looking outside for two seconds during a lull between showers — you might just be looking at a quiet moment, not the actual end of the storm. Memory usage can look stable simply because traffic happens to be lower right now (it's a slow period), not because the underlying bug is actually gone. Real verification means deliberately forcing a "cleanup" (triggering garbage collection) at multiple points in time and confirming the LOWEST POINT after cleanup stays the same — not just eyeballing a chart during a calm moment.

## 📊 Visualize It
```
 "Looks stable" chart (could be misleading):
  ____________________
              (traffic just happens to be low right now)

 Proper verification — Old Gen FLOOR after forced GC:

  T+0h: GC.run -> Old Gen floor = 500 MB
  T+1h: GC.run -> Old Gen floor = 500 MB   (SAME -> fixed)
  T+2h: GC.run -> Old Gen floor = 500 MB

  vs. still leaking:
  T+0h: 500 MB -> T+1h: 620 MB -> T+2h: 740 MB  (rising floor -> NOT fixed)
```

## 🏭 The Real Production Answer (15-YOE Level)

**Trap answer to reject:** "Great, heap is stable, we're done."

**Expert answer:**

"Heap stable" after a fix needs structured verification, not a visual check. Heap can appear stable because:
- Load dropped after deployment (it's weekend, or the fix coincided with lower traffic)
- GC pressure increased and is now keeping up temporarily
- The leak rate slowed but didn't stop — you need to watch for 24-48 hours under production load

Proper verification:
1. **Old Gen post-GC floor test**: trigger `jcmd <pid> GC.run` at T+0, T+1h, T+2h. If the floor is constant (±5%), the leak is fixed. If the floor creeps up, it still leaks.
2. **Soak test**: run your load test at 1.5x production load for 4 hours. Monitor Old Gen. Regression: Old Gen never decreases after GC.
3. **Heap dump comparison**: take a dump before fix deployment and after. Compare `Histogram` — the class counts for the leaked class should be bounded, not correlated with request count.
4. **Monitor for 24 hours of production traffic** before closing the incident — memory leaks are often traffic-pattern-dependent (e.g., only certain API paths trigger the leak).

Also run `jstat -gcutil <pid> 30s` for the first hour post-deployment and watch both `O` (Old Gen %) and `GCT` (cumulative GC time). GCT should grow at a constant low rate, not accelerate.

## 🔑 Key Takeaway
Never close a memory-leak incident from a visual "flat chart" alone — verify with a forced-GC floor test and a 24-48 hour soak under real production load.
