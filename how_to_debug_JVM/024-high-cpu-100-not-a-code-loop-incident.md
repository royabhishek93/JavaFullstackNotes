# #24 — High CPU (100%) — Not a Code Loop

> **Category:** Common Production Incidents | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"Walk me through diagnosing: `top` shows the java process pegged at 100-800% CPU (multi-core), response times have degraded, and `jstat` shows the full-GC counter climbing rapidly. How do you find the actual cause?"

## 😊 Explain It Simply (for anyone)
Think of the JVM as a kitchen with many chefs (threads). "100% CPU" just means the kitchen is fully busy — it doesn't tell you *why*. Maybe the cleanup crew (garbage collection, the automatic memory-freeing process) is scrubbing pots nonstop because dishes pile up faster than they can wash them — that looks like "the whole kitchen is slammed" from the outside, but it's really a memory problem, not a cooking problem. Or maybe one chef is stuck re-reading the same recipe card (a regex pattern) from scratch on every single order instead of memorizing it once. The trick is to figure out *which* kind of busy it is before you start blaming "the code is looping" — check the cleanup crew's workload first, then look at individual chefs.

## 📊 Visualize It
```
CPU 100-800% — WHY?
  ┌─ jstat -gcutil ──> FGCT climbing fast? ──> GC IS the CPU consumer
  │                                             (fix memory, not code)
  └─ not GC? ─> top -H -p <pid> ──> find hot TID
                       │
                       v
               jstack | grep nid=0x<hex>  ──> see what that thread runs
```

## 🏭 The Real Production Answer (15-YOE Level)

**Symptoms:**
- `top` shows java process at 100-800% CPU (multi-core)
- Response times degraded
- `jstat` shows FGCT climbing rapidly

**Diagnosis:**
```bash
# Step 1: Is it GC threads eating CPU?
jstat -gcutil <pid> 1000 10
# If FGCT growing fast (>1 Full GC every 30s) → GC is the CPU consumer

# Step 2: If not GC, find the hot thread
top -H -p <pid>  # show individual threads, find the hot one (TID)
printf "%x\n" <TID>  # convert decimal TID to hex for jstack matching
jstack <pid> | grep -A 20 "nid=0x<hex_tid>"

# Step 3: Or use async-profiler (better)
profiler.sh -e cpu -d 30 -f /tmp/cpu.html <pid>
```

**Root cause examples:**
- `Pattern.compile()` called on every request (should be a static final)
- `String.format()` in a tight loop with large strings
- HashMap with broken `hashCode()` (all objects in same bucket → O(n) lookup)
- GC thrashing because of memory leak (GC is the CPU, not the application)

**Fix:**
```java
// Broken: compile regex per request
boolean isValid(String input) {
    return input.matches("^[a-zA-Z0-9]{8,20}$"); // compiles every call
}

// Fixed: static compiled Pattern
private static final Pattern PATTERN = Pattern.compile("^[a-zA-Z0-9]{8,20}$");
boolean isValid(String input) {
    return PATTERN.matcher(input).matches();
}
```

## 🔑 Key Takeaway
Always check `jstat -gcutil` before profiling application code — high CPU is GC-driven far more often than "someone wrote an infinite loop."
