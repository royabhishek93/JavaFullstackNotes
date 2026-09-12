# #137 — Explain G1GC concurrent mark cycle and when it fails

> **Category:** GC Tuning & Debugging | **Type:** Advanced Scenario Q&A | **Priority:** ⚙️ Expert/Niche

## 🗣️ The Interview Question
"Explain G1GC concurrent mark cycle and when it fails."

## 😊 Explain It Simply (for anyone)
Think of a huge warehouse that needs an inventory audit to find items nobody wants anymore, so they can be thrown out and shelf space reclaimed. Instead of shutting the whole warehouse down for the audit (which would upset customers), the audit team works *while the warehouse stays open* — quietly walking the aisles marking items as "still needed" or "junk" as workers keep restocking and picking items. There are a few brief moments where things do pause completely: at the very start (to snapshot which items were already marked "needed"), and near the end (to double-check nothing changed mid-audit). The catch: if new junk piles up faster than the audit team can walk through and mark it, the audit never catches up — by the time they're done, the warehouse is already overflowing again, forcing an emergency full shutdown-and-clean (a Full GC) to catch up.

## 📊 Visualize It
```
Concurrent Mark Cycle phases:
1. Initial Mark    [STW]         — piggybacks on Young GC
2. Root Region Scan [concurrent] — scan Survivor → Old refs
3. Concurrent Mark  [concurrent] — mark all live Old objects
4. Remark          [STW]         — finalize marks, drain SATB queues
5. Cleanup         [STW-partial] — reclaim empty regions

Failure mode: allocation rate > marking speed
  → heap fills before marking finishes → Full GC forced
```

## 🏭 The Real Production Answer (15-YOE Level)
> G1GC's concurrent mark cycle runs in the background to identify garbage in the Old generation. It has five phases:
>
> 1. **Initial Mark** (STW, piggybacks on Young GC): marks roots
> 2. **Root Region Scan** (concurrent): scans Survivor regions for references to Old
> 3. **Concurrent Mark** (concurrent): marks all live objects in Old gen
> 4. **Remark** (STW): finalizes the marking, processes SATB buffers
> 5. **Cleanup** (STW for part): reclaims empty regions, sorts by liveness
>
> The cycle is triggered when Old gen occupancy exceeds `InitiatingHeapOccupancyPercent` (default 45%). The key failure mode is that the application allocates faster than the concurrent mark can finish — by the time marking is done, the heap has filled up and G1GC cannot complete a mixed collection in time, forcing a Full GC.

```bash
# Tune when concurrent cycle triggers:
-XX:InitiatingHeapOccupancyPercent=35   # Default 45%; trigger earlier = more headroom
# Risk: triggers more frequent cycles, slightly more CPU overhead

# How many Old regions to collect per mixed GC:
-XX:G1MixedGCCountTarget=8              # Default 8; collect Old in 8 mixed cycles
# Lower value = fewer Old regions per cycle = shorter pauses, but more cycles needed

# Maximum % of mixed GC candidates to leave alive:
-XX:G1HeapWastePercent=5                # Default 5%; stop mixed GC when waste < 5%

# Diagnostic: log concurrent cycle activity:
-Xlog:gc+marking=debug:file=/var/log/app/gc.log:time,uptime
```

## 🔑 Key Takeaway
G1's concurrent mark cycle fails when allocation outpaces marking speed — lowering `InitiatingHeapOccupancyPercent` buys the marking phase more headroom to finish before the heap fills.
