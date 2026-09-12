# #49 — NMT — Finding Native Memory Growth Beyond -Xmx

> **Category:** Production Debugging Tools | **Type:** Advanced Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"Your Java process RSS grows past `-Xmx` by 2GB. Where is the extra memory?"

## 😊 Explain It Simply (for anyone)
Imagine someone is on a strict diet with a fixed food budget, yet they keep gaining weight anyway. A good doctor doesn't just stare at the food log — they investigate other sources: water retention, medication side effects, or maybe muscle mass from a new exercise routine. The "diet budget" isn't the only thing affecting body weight.

`-Xmx` is the "diet budget" for a Java application's main memory area (the heap, where regular objects live). But the total memory a process actually uses (RSS — Resident Set Size, how much real RAM it's occupying) includes lots of other things beyond the heap: thread stacks, compiled-code caches, and special "off-heap" memory buffers used for fast networking. Native Memory Tracking (NMT) is the diagnostic tool that itemizes all these other "body systems" so you can see, category by category, where the mysterious extra weight is coming from. In this case, it turns out "Direct Buffers" (memory used for fast networking, often by libraries like Netty) is quietly growing and growing — a sign that buffers are being allocated but never released, a classic native memory leak.

## 📊 Visualize It
```
 RSS budget (4GB container)
 ┌───────────────────────────────┐
 │ Java Heap       2048MB (-Xmx) │
 │ Thread stacks   2100MB 🔴 huge│
 │ Metaspace        256MB        │
 │ Code Cache       156MB        │
 │ Direct Buffers   400MB 📈grow │
 └───────────────────────────────┘
   Total ≈ 5.8GB committed — over budget!
```

## 🏭 The Real Production Answer (15-YOE Level)
Enable NMT (Native Memory Tracking) at startup:
```bash
-XX:NativeMemoryTracking=summary   # low overhead, show categories
-XX:NativeMemoryTracking=detail    # higher overhead, show per-allocation
```

```bash
# Baseline snapshot
jcmd <pid> VM.native_memory baseline

# After memory growth
jcmd <pid> VM.native_memory summary.diff
```

**Sample output:**
```
Total: reserved=6.2GB, committed=5.8GB  (+800MB since baseline)

-       Java Heap (reserved=2048MB, committed=2048MB)
-          Thread (reserved=2100MB, committed=2100MB)   ← 2100 threads × 1MB stack
-       Metaspace (reserved=512MB, committed=256MB)
-    Code Cache    (reserved=256MB, committed=156MB)
- Direct Buffers  (reserved=400MB, committed=400MB)    ← GROWING
```

**Root cause:** Direct Buffers 400MB and growing = Netty ByteBuf not being released, or NIO ByteBuffer.allocateDirect() leak. Track with `-Dio.netty.leakDetection.level=PARANOID` in non-prod.

## 🔑 Key Takeaway
When RSS exceeds `-Xmx`, enable NMT and diff a baseline against a later snapshot to pinpoint which off-heap category (threads, direct buffers, metaspace) is actually leaking.
