# #59 — "Memory Usage Growing Means There's a Memory Leak"

> **Category:** Memory Leaks End-to-End | **Type:** Senior Trap Question | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"Our heap monitoring shows memory growing steadily over 48 hours. The team declares a memory leak. Is that the right conclusion?"

## 😊 Explain It Simply (for anyone)
Seeing your car's fuel gauge slowly climb doesn't necessarily mean it's broken — maybe you just filled the tank, or maybe you're driving more miles than usual (more legitimate load), or maybe the gauge just hasn't updated recently (GC hasn't run yet). Similarly, rising memory usage over time has several innocent explanations — legitimate growing data, more users, a cache filling up to its limit and then stopping — and only ONE of them is a true "leak" (a hole in the tank that never stops draining even after you've truly stopped driving). Jumping straight to "it's a leak, fix the code" without checking these other possibilities wastes engineering time and can even introduce new bugs.

## 📊 Visualize It
```
  Heap usage over 48h (chart looks the same in ALL these cases!):

   /\  <- true leak: floor rises after EVERY GC, never drops
  /  \/\  <- cache filling to its cap, then plateaus (fine)
 /        <- more load = proportionally more heap (fine)
/__________________ time

  TEST: trigger Full GC now, note Old Gen floor.
        Wait 1 hour, trigger again.
        Floor same  -> not a leak
        Floor HIGHER -> real leak
```

## 🏭 The Real Production Answer (15-YOE Level)

**Trap answer to reject:** "Yes, growing memory = memory leak, we should fix the code."

**Expert answer:**

Growing heap usage has multiple explanations, only one of which is a true leak:

1. **GC not running**: If the heap is not under pressure (lots of free space), the JVM defers GC. Heap used can grow steadily even with zero leak, then drop sharply on first GC. Check with: `jstat -gcutil <pid>` — if Old Gen usage drops significantly after a GC trigger, it's not a leak.

2. **Legitimate business data growth**: an order processing service with growing order history in a cache, or an event store accumulating events. Check business metrics against heap trend.

3. **Cache without TTL**: a correctly functioning cache filling to its size limit looks identical to a growing leak in a 48-hour chart — it just plateaus. Check cache stats.

4. **Increased load**: more users = more live sessions = more heap. Heap growing proportionally to load is expected behavior.

5. **True leak**: post-GC heap floor grows over time. The diagnostic test: trigger a Full GC (`jcmd <pid> GC.run`), record Old Gen usage. Wait one hour, trigger again. If Old Gen floor is higher the second time, you have a leak.

Jumping to "fix code" without this analysis leads to wasted engineering effort and potentially introducing new bugs.

## 🔑 Key Takeaway
Growing heap usage alone is inconclusive — always confirm a real leak by comparing the post-GC "floor" over time, not the raw usage chart.
