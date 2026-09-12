# #80 — Memory Allocation Storm Driving GC CPU

> **Category:** CPU Profiling & Flame Graphs | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"CPU usage is high, async-profiler flame graph shows `GC worker` threads at the top. Application code looks clean. What next?"

## 😊 Explain It Simply (for anyone)
Imagine a recycling plant that has to run its sorting machines nonstop because the delivery trucks are dumping in an enormous amount of disposable packaging every minute — way more than a normal load. The plant workers themselves aren't the problem; it's the sheer volume of throwaway material arriving that keeps the machines maxed out. In Java, "throwaway material" is short-lived objects — things like temporary strings or arrays created and discarded almost instantly. The recycling plant is the Garbage Collector (GC), the JVM's automatic memory cleaner. If your code creates too much garbage per second, GC has to work constantly to keep up, and that GC work itself shows up as high CPU — even though your business logic "looks clean." The trick is to stop looking at what the code computes and start looking at what the code creates: a special profiling mode tracks allocation sites (exactly which line of code is generating all this garbage), which usually reveals things like rebuilding a heavy object (e.g. a JSON parser) on every single request instead of reusing one.

## 📊 Visualize It
```
CPU flame graph:
 [GC worker thread ] <- 70% CPU, looks "clean" otherwise
 [GC worker thread ] <- 70% CPU

Switch to ALLOCATION profiling instead:
 [String.format()  ] <- allocates millions of char[] per second
 [new ObjectMapper()] <- ~1MB alloc, created PER REQUEST (should be reused)

Diagnosis: app isn't CPU-heavy, it's GARBAGE-heavy -> GC burns the CPU.
```

## 🏭 The Real Production Answer (15-YOE Level)
The application is generating garbage faster than GC can collect. CPU is consumed by GC, not app logic. Profiling the wrong thing.

Switch to allocation profiling:
```bash
./profiler.sh -e alloc -d 30 -f /tmp/alloc.html <pid>
```

This shows allocation sites. Common findings: `String.format()` or `+` concatenation in a hot loop creating millions of char arrays, `ArrayList.toArray()` called repeatedly, `new ObjectMapper()` per request (heavyweight, ~1MB allocation cost), Lombok `@Builder` creating intermediate objects per field.

Also look at JFR:
```bash
jcmd <pid> JFR.start duration=60s filename=/tmp/alloc.jfr settings=profile
```

JFR "Allocation in New TLAB" events show exactly what's being allocated and where.

## 🔑 Key Takeaway
If GC worker threads dominate the CPU flame graph, stop profiling CPU and start profiling allocations (`-e alloc`) — the fix is reducing garbage, not optimizing app logic.
