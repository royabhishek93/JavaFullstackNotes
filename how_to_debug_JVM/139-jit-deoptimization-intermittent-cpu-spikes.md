# #139 — JIT Deoptimization Causing Intermittent CPU Spikes

> **Category:** CPU Profiling & Flame Graphs | **Type:** Advanced Scenario Q&A | **Priority:** ⚙️ Expert/Niche

## 🗣️ The Interview Question
"You see periodic CPU spikes every ~5 minutes lasting 200ms. Flame graphs look clean. JFR shows anything?"

## 😊 Explain It Simply (for anyone)
Imagine a highly skilled interpreter who, after hearing the same few phrases repeated over and over, memorizes them and can respond instantly without thinking. Now imagine that occasionally, a brand-new, slightly different phrase comes in that breaks their assumption, and they suddenly have to stop, think everything through from scratch the slow way, before eventually re-memorizing the new pattern. That temporary "forgot the shortcut, back to slow thinking" moment is exactly what happens inside the JVM's Just-In-Time (JIT) compiler, which turns frequently-run code into super-fast machine instructions based on assumptions about how the code behaves. When something violates those assumptions — like a brand-new subclass suddenly appearing — the JVM has to throw away its fast shortcut (this is called deoptimization) and fall back to slow, step-by-step execution until it can safely re-learn and re-optimize. Because this fallback is 10 to 100 times slower than the optimized version, even a short burst of it causes a visible CPU spike, and because it's rare and brief, a normal profiling snapshot often won't catch it — you need a tool that specifically records these "forgot the shortcut" events.

## 📊 Visualize It
```
Normal:   [req] -> [JIT-optimized fast path] -> [done]      (fast, cheap)

Deopt event (new subclass loaded, breaks JIT assumption):
          [req] -> [DEOPTIMIZED! fall back to interpreter, 10-100x slower]
                       -> [JIT recompiles in background]
                       -> [req] -> [fast path restored]
                              ^
                     200ms spike, every ~5min, "invisible" in normal flame graph
```

## 🏭 The Real Production Answer (15-YOE Level)
This pattern — periodic short spikes — often points to JIT deoptimization and recompilation cycles.

JFR captures `jdk.Deoptimization` events. When a method is deoptimized (e.g., because a new subclass was loaded that breaks an inlining assumption), the JVM falls back to interpreted bytecode — which is 10-100x slower — until the JIT recompiles.

```bash
jcmd <pid> JFR.start duration=300s filename=/tmp/deopt.jfr settings=profile
# Wait for a spike to occur
jcmd <pid> JFR.dump filename=/tmp/deopt.jfr
```

In JMC, look at the "JIT Compilation" and "Deoptimization" event views. If you see mass deoptimizations following a class loading event, the fix is either: avoid dynamic class loading in hot paths, or use `@Stable` fields to give JIT stronger inlining hints.

Also check: `-XX:+PrintCompilation` output piped to a file during the spike (costs log I/O but fine for a short diagnostic window).

## 🔑 Key Takeaway
Periodic short CPU spikes with a "clean" flame graph point to JIT deoptimization — capture a long JFR session and inspect the `jdk.Deoptimization` events, not the CPU samples.
