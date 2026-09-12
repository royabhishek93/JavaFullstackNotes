# #23 — OutOfMemoryError: Java Heap Space

> **Category:** Common Production Incidents | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"Walk me through diagnosing: a pod gets OOM-killed by Kubernetes (or the JVM exits) with `java.lang.OutOfMemoryError: Java heap space` in the logs, and the heap dump shows some large retained objects. How do you find and fix the root cause?"

## 😊 Explain It Simply (for anyone)
Imagine your app's memory as a warehouse shelf with limited space. Every time your program needs to remember something (a user session, a cached value), it puts a labeled box on the shelf. A cleanup crew (the "garbage collector," or GC — the JVM's automatic memory-freeing process) walks around and removes boxes nobody needs anymore.

"Heap space" is just the name for that shelf. When the shelf fills up completely and the cleanup crew can't find any boxes to remove (because something is still holding a claim ticket on every single one), the warehouse manager gives up and throws an error — that's `OutOfMemoryError: Java heap space`. The fix is never "build a bigger shelf" (increase heap) as a first move — it's figuring out *which* boxes shouldn't still have claim tickets on them, like an unbounded cache that never throws anything away.

## 📊 Visualize It
```
Shelf (Heap) over time:
 [■□□□□□] 20%  -> [■■■□□□] 55%  -> [■■■■■■] 100% CRASH
   ok            growing            OOM!

Suspects to check (in order):
  1. jcmd GC.class_histogram  -> which class dominates?
  2. jcmd GC.heap_dump        -> full dump for MAT
  3. MAT dominator tree       -> who's the GC root holding it?
```

## 🏭 The Real Production Answer (15-YOE Level)

**Symptoms:**
- Pod OOM-killed by Kubernetes (or JVM exits with OOM)
- Logs show `java.lang.OutOfMemoryError: Java heap space`
- Heap dump shows large retained objects

**Diagnosis:**
```bash
# 1. OOM already happened — check for heap dump (if flag was set)
ls -lh /var/dumps/*.hprof

# 2. If still alive before crash, get histogram (fast)
jcmd <pid> GC.class_histogram | head -30

# 3. Full heap dump (take pod out of LB first)
jcmd <pid> GC.heap_dump /tmp/heap.hprof

# 4. Analyze with MAT — find dominator tree / leak suspects
```

**Root causes (most common):**
1. Unbounded cache (static Map / Caffeine without eviction)
2. Session object accumulation (HttpSession not expiring)
3. List/collection growing forever per request (not cleared)

**Fix:**
```java
// Broken: unbounded static map
private static final Map<String, Data> cache = new HashMap<>();

// Fixed: bounded with eviction
private static final Cache<String, Data> cache = Caffeine.newBuilder()
    .maximumSize(10_000)
    .expireAfterWrite(1, TimeUnit.HOURS)
    .build();
```

**Prevention:** `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/var/dumps/` at all times.

## 🔑 Key Takeaway
Never guess at an OOM — pull a heap histogram or dump and follow the dominator tree to the actual GC root holding the memory.
