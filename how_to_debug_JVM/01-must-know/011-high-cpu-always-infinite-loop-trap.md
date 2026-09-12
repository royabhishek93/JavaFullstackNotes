# #11 — "High CPU Always Means Infinite Loop"

> **Category:** CPU Profiling & Flame Graphs | **Type:** Senior Trap Question | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"If CPU is at 100%, you have an infinite loop somewhere, right?"

## 😊 Explain It Simply (for anyone)
Picture a busy restaurant kitchen at 100% activity — every burner is on, every chef is chopping, plating, and cooking nonstop. That doesn't necessarily mean anything is broken; it might just mean the restaurant is genuinely slammed with legitimate orders and is running at full, healthy capacity. But 100% kitchen activity could also mean something is actually wrong — like a chef stuck repeatedly re-checking if an oven timer went off instead of doing anything useful, or a brand-new trainee who's slow because they're still learning the layout (which gets faster once they're warmed up), or the whole staff doing a big one-time deep-clean of all the pots and pans (this happens periodically, similar to Garbage Collection, the JVM's automatic memory cleanup). So "100% CPU" is just a symptom with many possible honest explanations, only one of which is "something is truly stuck in a broken infinite loop." A good engineer checks whether real work is getting done (are orders going out? are GC pauses excessive? did the service just restart?) before assuming the worst.

## 📊 Visualize It
```
100% CPU can mean:
  [GC threads]        <- garbage collection is legitimately busy
  [100 worker threads]<- genuinely serving 100 concurrent requests (healthy!)
  [JIT compiler burst] <- normal warm-up right after deploy/restart
  [tight retry loop]   <- ACTUALLY broken, no backoff

Diagnosis order:
  1. jstat -gcutil   -> is it GC?
  2. is throughput/requests actually completing?
  3. just restarted?  -> JIT warm-up, expected
  4. only then: look for a real spinning loop
```

## 🏭 The Real Production Answer (15-YOE Level)
This is wrong — and a senior engineer should immediately push back.

High CPU has multiple root causes. An infinite loop is one, but consider:

- **GC CPU**: GC threads are JVM threads. During a Full GC or G1 mixed collection, GC can use all available cores. `jstat -gcutil <pid> 1s` will show this immediately. The fix is heap sizing and allocation reduction, not fixing application loops.

- **Thread pool saturation**: If 100 threads are all RUNNABLE doing legitimate work (request handling, serialization), that's also 100% CPU — but it's doing useful work. Check throughput: if requests are completing, it's just load. If they're not completing, then investigate.

- **JIT compilation burst**: After a restart or after a new deployment, the JIT recompiles all hot methods from scratch. This can spike CPU for the first 30-60 seconds as the JVM "warms up". Expected behavior, not a bug.

- **Tight retry loops**: Not infinite, but a retry loop with no backoff (e.g., while DB is unavailable) can spin at 100% CPU doing nothing useful.

Diagnosis order: check GC first, check if work is completing, then look for loops.

## 🔑 Key Takeaway
100% CPU has at least four common causes — GC, real load, JIT warm-up, and spinning loops — so check GC and throughput before assuming an infinite loop.
