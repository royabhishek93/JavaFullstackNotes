# #131 — Multiple Kubernetes Pods OOM-Killing Simultaneously

> **Category:** Heap Dump Analysis | **Type:** Advanced Scenario Q&A | **Priority:** ⚙️ Expert/Niche

## 🗣️ The Interview Question
"All 8 pods of a service OOM-kill within 2 minutes of each other every day at 2 AM. What's happening and how do you debug it?"

## 😊 Explain It Simply (for anyone)
If ONE store in a chain runs out of shelf space randomly, that's probably that store's own local problem (a slow leak). But if ALL 8 stores in the chain run out of space at the EXACT same time, every single day, at 2 AM — that's not a coincidence, that's a scheduled event affecting all of them at once, like a company-wide truck delivery that dumps way more inventory into every store simultaneously every night.

In software terms, this points to something like a nightly batch job, a scheduled task, or a report-generation process that runs on a timer and briefly needs a huge amount of memory across every instance of the service at the same moment — not a gradual leak building up over hours.

## 📊 Visualize It
```
00:00        02:00 (CRON FIRES)     02:02 (ALL PODS DIE)
Pod1: [■■□□] → [■■■■■■] OOM-killed
Pod2: [■■□□] → [■■■■■■] OOM-killed
Pod3: [■■□□] → [■■■■■■] OOM-killed
 ...    (all 8 pods spike together)
Pod8: [■■□□] → [■■■■■■] OOM-killed

Simultaneous spike ⇒ shared scheduled trigger, NOT per-pod leak
  Look for: @Scheduled, cron jobs, batch endpoints loading
            full DB tables into a List<Entity> in memory

Fix: JpaRepository.stream() + chunked processing
     → memory footprint flat instead of spiking at 2 AM
```

## 🏭 The Real Production Answer (15-YOE Level)

The simultaneous pattern rules out a gradual per-pod leak. This is a scheduled load event. Likely candidates:
1. A nightly batch job triggering this service (cron job, scheduled task)
2. A scheduled `@Scheduled` method in the service itself
3. Report generation / cache warm-up that creates large temporary objects

Investigation:
```bash
# Check scheduled tasks in codebase
grep -r "@Scheduled\|@Cron\|quartz\|scheduler" src/ --include="*.java"

# Check upstream call patterns — did request rate spike at 2 AM?
# Query Prometheus/Grafana: rate(http_server_requests_total[1m]) at 02:00

# Enable JVM GC logging and compare 2 AM vs normal hours
# -Xlog:gc*:file=/logs/gc.log:time,level,tags:filecount=10,filesize=50m

# Heap profiling with async-profiler (allocation profiler) for 5 min at 2 AM
./profiler.sh -e alloc -d 300 -f /tmp/alloc.html <pid>
# Shows call stack that allocated the most bytes — pinpoints the code path
```

Common cause: A batch endpoint loads entire DB table into a `List<Entity>`, processes in-memory, holds the list in scope for the full duration. At 2 AM batch size peaks.

Fix: Stream the result set using `JpaRepository.stream()` inside a transaction, process in chunks, never materialize the full list.

## 🔑 Key Takeaway
Simultaneous multi-pod OOMs point to a shared scheduled trigger, not independent leaks — correlate the crash time with cron jobs and batch endpoints, not with heap dumps first.
