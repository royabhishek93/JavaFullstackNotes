# #143 — JIT Compilation — When Code Gets SLOWER After Warmup

> **Category:** JVM Tuning Production Playbook | **Type:** Advanced Scenario Q&A | **Priority:** ⚙️ Expert/Niche

## 🗣️ The Interview Question
"After about 30 minutes of running, our service starts getting slower, not faster. CPU gradually increases. Redeployment fixes it temporarily. What JIT phenomenon causes this?"

## 😊 Explain It Simply (for anyone)
Think of a tailor (the JIT compiler) who, after watching you wear the same style of shirt for a while, makes you a perfectly optimized custom shirt assuming you'll always want that same style (a speculative optimization based on observed patterns). But if you suddenly start wearing a completely different style of shirt (new object types flowing through the code, or new classes being loaded), the tailor has to rip up the custom shirt, go back to using generic off-the-rack clothes for a while (falling back to slower interpreted code), and then start tailoring a new, less confident, less optimized shirt (recompiling with weaker assumptions). If this "rip up and re-tailor" cycle keeps happening, you spend more and more time in slow generic clothes and never settle into a fast custom fit — a fresh JVM restart is like hiring a new tailor with no preconceptions, which is why redeploying "fixes" it temporarily.

## 📊 Visualize It
```
CPU/Time
       ▲
       │              ╱╲    ╱╲
       │           ╱╲╱  ╲╲╱  ╲
       │        ╱╲╱                (gradual increase,
       │     ╱╲╱                    deopt + recompile storms)
       └──────────────────────────► time
      deploy      30 min          later
      (fast, JIT-optimized)   (assumptions broken, deopt cascade)
```

## 🏭 The Real Production Answer (15-YOE Level)
> "JIT deoptimization — specifically speculative deoptimization followed by recompilation storms.
>
> JIT compilers make speculative optimizations based on observed behavior. If those assumptions are
> violated, the JIT must deoptimize (fall back to interpreted or C1-compiled version) and then
> recompile with less aggressive assumptions.
>
> Symptoms:
> - Gradual CPU increase over time
> - Periodic bursts of high CPU
> - Performance degrades instead of improving
> - Redeployment (fresh JVM) temporarily fixes it
>
> Common triggers:
>
> 1. Polymorphic call sites
>    JIT optimizes for a single concrete class at a call site.
>    If new concrete types start flowing through that site (e.g., after cache warmup loads different
>    subclasses), JIT deoptimizes and recompiles as megamorphic (no devirtualization).
>    Megamorphic call sites are significantly slower.
>
> 2. Class loading after warmup
>    A plugin loads new classes into a ClassLoader at runtime.
>    JIT's assumptions about class hierarchy are invalidated.
>    Deoptimization cascade can affect many compiled methods.
>
> 3. Code cache exhaustion
>    When ReservedCodeCacheSize is full, the JVM starts flushing compiled code.
>    Methods fall back to interpreted mode until recompiled.
>    The 'compiler is running' symptom: CPU spike + throughput drop.
>
>    Check:
>      jcmd <pid> Compiler.codecache
>      Look for: 'CodeCache is full. Compiler has been disabled.'
>      Fix: -XX:ReservedCodeCacheSize=512m (default 240MB is often not enough for large apps)
>
> 4. On-Stack Replacement (OSR) failures
>    Long-running methods that were optimized with speculative assumptions
>    hit deopt points while executing (mid-method).
>
> Diagnostic:
>   -XX:+PrintCompilation  # Logs compilation events, deoptimizations marked with 'made not entrant'
>   JFR event: jdk.Deoptimization
>     jfr print --events jdk.Deoptimization recording.jfr | head -50"

## 🔑 Key Takeaway
Code that gets slower over time, not faster, points to a deoptimization storm — check code cache exhaustion and polymorphic call sites via `-XX:+PrintCompilation` before blaming anything else.
