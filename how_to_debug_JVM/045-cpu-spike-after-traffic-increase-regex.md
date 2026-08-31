# #45 — Service CPU Spike After Traffic Increase

> **Category:** CPU Profiling & Flame Graphs | **Type:** Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"Your REST service runs fine at 1k RPS. At 5k RPS, CPU jumps to 95% and latency degrades. How do you find the cause?"

## 😊 Explain It Simply (for anyone)
Picture a fast-food counter that runs smoothly with a few customers an hour. Now imagine that for every single order, the cashier has to first flip through the entire recipe book from page one before ringing it up — even though the recipe never changes between orders. At low traffic nobody notices, because there's plenty of idle time between customers to absorb the wasted flipping. At high traffic, that "re-read the whole book" step happens thousands of times per minute and eats all the cashier's available time, so the whole line backs up even though no single order got harder. In software terms, that "recipe book" is a regular expression (regex) — a pattern used to validate text like "is this alphanumeric?" Building (compiling) that pattern from scratch is expensive, and doing it fresh on every request instead of once at startup scales terribly. The bug hides at low load because there's slack in the system, but at high load every wasted microsecond multiplies across thousands of requests per second, so CPU shoots up while latency degrades. The fix is simply to build the pattern once and reuse it forever, like keeping a laminated recipe card taped to the register.

## 📊 Visualize It
```
1k RPS: [req] -> [compile regex, 1μs] -> [match] -> idle... (fine)

5k RPS: [req][req][req][req][req]
          |    |    |    |    |
      [compile][compile][compile][compile][compile]  <- 40% of all CPU!
          |    |    |    |    |
       [match][match][match][match][match]

Fix: compile ONCE at class-load time, reuse Pattern object forever.
```

## 🏭 The Real Production Answer (15-YOE Level)
Traffic-proportional CPU escalation — likely a per-request operation that doesn't scale. Safepoint bias is irrelevant here; I need to see what's hot at load.

Step 1 — triage:
```bash
top -H -p <pid>          # which threads are hot
jstat -gcutil <pid> 1000 # is GC involved
```

Step 2 — async-profiler at peak load:
```bash
./profiler.sh -e cpu -d 60 -f /tmp/spike.html <pid>
```

Step 3 — read flame graph. At 5k RPS I've seen `Pattern.compile()` show up as 40% of CPU because an engineer added a regex validator in a request filter without caching the Pattern. Fix: compile once as a static final field.

```java
// WRONG — compiles on every request
public boolean validate(String input) {
    return input.matches("^[a-zA-Z0-9]+$");
}

// RIGHT — compile once
private static final Pattern ALPHANUMERIC = Pattern.compile("^[a-zA-Z0-9]+$");
public boolean validate(String input) {
    return ALPHANUMERIC.matcher(input).matches();
}
```

## 🔑 Key Takeaway
When CPU scales worse than traffic, profile at peak load with async-profiler — the usual culprit is a per-request object (like a compiled `Pattern`) that should have been created once and reused.
