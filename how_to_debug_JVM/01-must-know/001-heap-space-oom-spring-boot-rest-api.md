# #1 — Heap Space OOM in a Spring Boot REST API

> **Category:** Heap Dump Analysis | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"Your Spring Boot service is OOM-killing every 4–6 hours with 'Java heap space.' Heap is 4 GB. How do you approach this?"

## 😊 Explain It Simply (for anyone)
Think of your application's memory (the "heap") as a big warehouse where every piece of information your program needs gets stored as a labeled box. When a worker (your code) is done using a box, a cleanup crew (the "Garbage Collector" or GC) is supposed to notice nobody holds a claim ticket to that box anymore and haul it away, freeing up shelf space.

The problem here is that some boxes are being kept around by mistake — maybe a supervisor's clipboard (a cache, a static list, an open database session) keeps writing down "keep this box, might need it" even though nobody ever needs it again. Every few hours, more and more boxes pile up, the cleanup crew works harder and harder but can't clear enough space, and eventually the warehouse manager throws up their hands and shuts the whole warehouse down — that's the "OutOfMemoryError."

The fix isn't to build a bigger warehouse; it's to find out which clipboard is holding onto boxes it shouldn't and stop that.

## 📊 Visualize It
```
Time →   0h        2h         4h        6h (CRASH)
Heap:  [■□□□□□]  [■■■□□□]  [■■■■■□]  [■■■■■■] OOM!
        20%        50%        85%      100%

GC sweep after each cycle:
  Cycle 1: clears 15% (leak grows 5%/cycle net)
  Cycle 2: clears 10%
  Cycle 3: clears  3%   ← reclaim shrinking = LEAK
  Cycle 4: clears  0%   → heap full → crash

Root cause chain (found via MAT):
  GC Root → static field → Cache/Session/ThreadLocal
          → holds millions of unreachable-but-referenced objects
```

## 🏭 The Real Production Answer (15-YOE Level)

Step 1 — Gather evidence without guessing.
```bash
# Confirm OOM type in logs
grep "OutOfMemoryError" /var/log/app/app.log | tail -20

# Check if heap dump was auto-captured
ls -lh /dumps/*.hprof

# If no auto-dump, enable it for next crash
# JVM flag: -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps/
```

Step 2 — Look at GC logs before heap dump (faster signal).
```bash
# If GC logging enabled:
# -Xlog:gc*:file=/logs/gc.log:time,level,tags:filecount=5,filesize=20m
grep "Pause Full" /logs/gc.log | awk '{print $1, $NF}' | tail -30
```
A pattern of increasing Full GC frequency with decreasing space reclaimed = leak.

Step 3 — Open heap dump in MAT.
- Dominator Tree: What single object retains the most heap?
- Check GC root path: Is it reachable via static field, thread-local, classloader?
- Look at object counts histogram: Do you see millions of unexpected objects (String, byte[], char[])?

Step 4 — Common Spring Boot culprits to check:
- `@Cacheable` without `maxSize` or TTL
- Hibernate `Session` objects not closed (OSIV - Open Session In View anti-pattern)
- `HttpClient` / `RestTemplate` connection pool misconfiguration causing response body not consumed
- `ThreadLocal` set but never `remove()`d in thread pool threads

Step 5 — Fix, add metric, verify under load.

## 🔑 Key Takeaway
Chase the retention root with a heap dump and GC logs — never the timestamp of the crash.
