# #114 — Profiling Async/Reactive Code (WebFlux)

> **Category:** CPU Profiling & Flame Graphs | **Type:** Advanced Scenario Q&A | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"Your service uses Project Reactor (WebFlux). Standard CPU flame graphs show `reactor.core.publisher.*` as the top consumer, but you can't see which business logic is hot. How do you profile reactive code?"

## 😊 Explain It Simply (for anyone)
Imagine a relay race where the baton (a task) gets passed between many different runners (threads), and each runner only knows "I'm currently holding the baton," not "who handed it to me three exchanges ago" or "what the whole race plan looks like." If you take a photo of any single runner mid-race, you see them running, but you have no idea which team or which leg of the strategy they represent — you just see generic "runner running" activity. That's what happens when you profile reactive/asynchronous code with a normal profiler: it shows you the plumbing (the relay hand-off machinery, called the "operator pipeline") instead of your actual business logic, because the work has been chopped up and handed between threads so many times that the original context is lost. The fix is to add visible markers along the relay route — checkpoints — so that when you take a snapshot, you can tell which leg of the business logic each runner represents, or to attach a special instrumentation agent that records the full logical race plan at the moment it was set up, so you can trace it back later even though execution is scattered across threads.

## 📊 Visualize It
```
Business logic view (what you WANT to see):
  [fetch order] -> [transform] -> [enrich] -> [respond]

What a normal profiler shows instead:
  [reactor.core.publisher.FluxMap] -> [reactor.core.publisher.FluxFlatMap] -> ...
       ^ operator plumbing, not YOUR code

Fix: checkpoint("after-transform") markers, OR reactor-tools javaagent
     for full assembly-time logical stack capture.
```

## 🏭 The Real Production Answer (15-YOE Level)
Standard sampling profilers show the operator pipeline, not the logical call chain. You need context propagation.

Option 1 — async-profiler wall-clock mode with thread filtering:
```bash
./profiler.sh -e wall -t --filter "reactor-http-nio" -d 30 -f /tmp/reactive.html <pid>
```

This shows the wall-clock profile of reactor worker threads, and you can see the operator chain.

Option 2 — Reactor's built-in instrumentation:
```java
// Enable checkpoint() to add stack trace markers
Flux.from(source)
    .map(this::transform)
    .checkpoint("after-transform")
    .flatMap(this::enrich)
    .checkpoint("after-enrich")
    .subscribe();
```

Checkpoints add operator identifiers visible in stack traces and JFR events.

Option 3 — reactor-tools agent for full assembly-time stack capture:
```bash
java -javaagent:reactor-tools.jar -jar myapp.jar
```

This instruments every Flux/Mono at assembly time, providing full logical stack traces when profiling.

The key insight: in reactive code, the "caller" and the "computation thread" are decoupled. Wall-clock profiling per-thread gives you real execution, not logical call chains.

## 🔑 Key Takeaway
Reactive code decouples "who called this" from "which thread runs it," so add `checkpoint()` markers or use the reactor-tools agent instead of expecting a normal flame graph to show your business logic.
