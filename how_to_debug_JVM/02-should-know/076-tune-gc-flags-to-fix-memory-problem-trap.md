# #76 — Let's tune GC flags to fix our memory problem

> **Category:** GC Tuning & Debugging | **Type:** Senior Trap Question | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"Let's tune GC flags to fix our memory problem — good first move?"

## 😊 Explain It Simply (for anyone)
Imagine your house keeps flooding, and instead of checking for the leaking pipe, you buy a bigger mop and a faster drain. That might briefly help, but if the pipe keeps leaking, you'll eventually be overwhelmed no matter how good your mop is. Tuning garbage collector settings (the JVM's cleanup crew) when you have a real memory problem is exactly like buying a better mop instead of fixing the pipe. Before touching any cleanup-crew settings, you should first ask: is the house actually generating way more mess than it should (an unusually high rate of creating short-lived junk), is stuff being deliberately kept around forever when it shouldn't be (a growing, never-emptied cache), or are things being "held onto" accidentally (like leaving items reserved in a locker that never gets cleared out)? Fixing those root causes in the code almost always beats trying to out-tune a garbage collector against a fundamentally leaky application.

## 📊 Visualize It
```
Memory Problem
      │
      ▼
  Tune GC flags first?  ❌ WRONG ORDER
      │
      ▼
  1. Profile allocation rate (async-profiler)
  2. Check object lifetimes (hot-path garbage?)
  3. Audit unbounded caches
  4. Audit ThreadLocal cleanup
      │
      ▼
  Fix code → THEN tune GC if still needed  ✅ RIGHT ORDER
```

## 🏭 The Real Production Answer (15-YOE Level)
**WRONG. The experienced answer:**

> GC tuning is the last resort, not the first. Before touching a single JVM flag, I look at the application:
>
> 1. **Allocation rate**: use async-profiler's allocation profiling to find which code paths allocate the most. A hot path allocating megabytes per request is the real problem.
> 2. **Object lifetime**: are objects being allocated in hot paths but most of them are dead after one method call? Those should never reach Old gen but will if they're large.
> 3. **Cache sizing**: is the old gen filling up because of unbounded caches? A Guava cache without eviction is a memory leak in disguise.
> 4. **ThreadLocal cleanup**: are ThreadLocals being set in request handling but never removed? Classic leak in thread-pool environments.
>
> Once the code is clean, tune GC. Not before.

## 🔑 Key Takeaway
GC flag tuning is a last resort — profile allocation rate, object lifetimes, cache growth, and ThreadLocal leaks in the code first.
