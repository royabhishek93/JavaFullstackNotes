# #83 — "Fix the Hottest Method First"

> **Category:** CPU Profiling & Flame Graphs | **Type:** Senior Trap Question | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"The flame graph shows `computeHash()` taking 60% of CPU. Start there."

## 😊 Explain It Simply (for anyone)
Imagine a delivery company complains that their busiest driver spends 60% of the workday behind the wheel, so management concludes "let's buy that driver a faster car." But if the real problem is that dispatch keeps sending that driver on the same short trip fifty extra times a day for no good reason, buying a faster car barely helps — the fix should be sending fewer, smarter trips instead. The same trap applies to a "hot" function in a flame graph: seeing 60% of CPU time attributed to `computeHash()` tells you it's busy, but it doesn't tell you *why*. It could genuinely be doing expensive work each time it's called (in which case, yes, optimize the function itself), or it could be a perfectly cheap operation that's simply being called an absurd number of times unnecessarily (in which case the real fix is calling it less often, not making it faster). You have to check both the "cost per call" and the "number of calls" before deciding where the actual fix belongs — otherwise you might spend days optimizing an already-fast function while ignoring the caller that's needlessly hammering it millions of times.

## 📊 Visualize It
```
Flame graph: [computeHash() ================] <- 60% of CPU, looks "hottest"

Two very different explanations:
  (a) EXPENSIVE per call: 1ms x 1000 calls/sec  -> optimize the algorithm
  (b) CHEAP but overcalled: 1μs x 60,000,000 calls/sec -> reduce call frequency!

Must check: invocations/sec AND per-call duration AND the CALLER above it
            before deciding where the real fix belongs.
```

## 🏭 The Real Production Answer (15-YOE Level)
The hottest method isn't always where the fix lives.

You need to distinguish between two causes of a method appearing hot:

1. **The method is inherently expensive** — it does too much work per call. Fix: optimize the algorithm, cache results, use a faster implementation.

2. **The method is called too often** — each call is fast, but it's called millions of times unnecessarily. Fix: reduce call frequency, add caching at the caller, batch calls.

The flame graph tells you a method is hot, but not which case applies. You need to check:

- **Call count**: Use async-profiler's `-e itimer` mode or Arthas `monitor` to get invocations per second.
- **Per-call duration**: If `computeHash()` takes 1µs but is called 60M times per second, that's a call frequency problem. Caching the hash result in the key object would be the fix.
- **Caller context**: Who is calling `computeHash()` this often? Go up the flame graph to find the caller — maybe it's `HashMap.containsKey()` inside a hot loop that could use `computeIfAbsent()` pattern with a pre-stored key.

Optimizing the hash function itself when the real problem is redundant calls would be wasted effort.

## 🔑 Key Takeaway
Before optimizing the hottest method, check its call count and the caller above it — an over-called cheap function needs a caching fix at the call site, not algorithmic tuning.
