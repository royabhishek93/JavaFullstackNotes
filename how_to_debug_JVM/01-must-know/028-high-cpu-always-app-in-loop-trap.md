# #28 — "High CPU Always Means My Application Code Is in a Loop"

> **Category:** Common Production Incidents | **Type:** Senior Trap Question | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"High CPU always means my application code is in a loop, right?"

## 😊 Explain It Simply (for anyone)
It's tempting to assume 100% CPU means "someone wrote broken code that spins forever," but that's like assuming a fully-lit stove in a kitchen means something is burning. Often it just means the cleanup crew (garbage collection — the JVM's automatic memory-freeing process) is working overtime because the shelves (memory) are nearly full, and that cleanup work shows up as "the java process" using CPU too, even though your actual business logic isn't looping at all. A good engineer checks the cleanup crew's workload first, because if that's the real cause, the fix is memory-related, not a hunt through business logic for a stray loop.

## 📊 Visualize It
```
top: java process = 600% CPU. WHY?
   jstat -gcutil <pid> 1000 10
        |
   FGCT climbing fast? (>1 Full GC / 10s)
        |
   YES --> GC threads ARE the CPU consumer, app threads are STW (stopped)
   NO  --> now look for an actual application-level hot loop
```

## 🏭 The Real Production Answer (15-YOE Level)
**WRONG.** GC threads are counted as Java process CPU. When Old Gen is >95% and Full GC fires every 10 seconds:
- GC threads can consume 4-8 CPU cores
- Application threads are STW (stopped), adding nothing
- `top` shows 400-800% java CPU — all of it is GC

**Correct answer:** Before profiling application code, run `jstat -gcutil <pid> 1000` for 10 seconds. If `FGCT` is climbing and `FGC` is in double digits per minute, GC is the CPU consumer. Fix the memory issue first (leak, heap size), CPU will normalize.

## 🔑 Key Takeaway
Rule out GC with `jstat -gcutil` before you go hunting for a hot loop in application code — GC-driven CPU is far more common than an actual infinite loop.
