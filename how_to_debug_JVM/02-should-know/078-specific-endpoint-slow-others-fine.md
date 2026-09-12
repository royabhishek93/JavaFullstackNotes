# #78 — Specific Endpoint Slow, Others Fine

> **Category:** CPU Profiling & Flame Graphs | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"The `/search` endpoint takes 2s at p99. All others are sub-100ms. CPU is elevated only during search calls."

## 😊 Explain It Simply (for anyone)
Imagine a hospital where every department runs efficiently except the X-ray room, which has a long line every time someone needs a scan. If you only watch the whole hospital's overall busyness, the X-ray bottleneck gets diluted by all the fast departments and looks unremarkable. To find the real problem, you need a security camera pointed specifically at the X-ray room while patients are being sent there — not a wide shot of the whole building. In software, that means profiling isn't useful in general; you need to profile while specifically hammering the slow endpoint (`/search`), and you need a mode that watches threads even when they're waiting (like a patient waiting in a chair, not doing anything), not just when they're actively "running." That waiting-included view is called wall-clock profiling, and it reveals things a normal "only when busy" profiler misses, such as a thread stuck waiting on a slow database call or JSON parser. Once you can see specifically what the search threads are doing, common causes emerge: too many small database queries per search request, or expensive re-parsing of data on every call.

## 📊 Visualize It
```
Normal endpoints:  [req] -> [quick work] -> [done]     (<100ms)

/search endpoint:  [req] -> [DB query 1] -> [DB query 2] -> ... -> [JSON parse] -> [done]
                                    ^ N+1 queries or heavy re-parsing here (2s, p99)

Wall-clock profiling (-e wall) sees threads even while WAITING on I/O,
not just while actively burning CPU.
```

## 🏭 The Real Production Answer (15-YOE Level)
Endpoint-scoped profiling. I want to correlate CPU samples with just the search code path.

```bash
# Wall-clock mode to catch all threads including I/O waits
./profiler.sh -e wall -d 30 -t -f /tmp/wall.html <pid>
```

Wall-clock mode shows threads even while they're blocked — useful for distinguishing CPU-bound vs I/O-bound work.

While profiling, hammer the search endpoint:
```bash
ab -n 1000 -c 10 https://myservice/search?q=test
```

Look in the flame graph for the search thread pool. Common findings: Lucene/Elasticsearch client doing repeated JSON deserialization, N+1 database queries expanding into heavy ORM work, or Hibernate second-level cache miss loading full entity graphs.

## 🔑 Key Takeaway
When only one endpoint is slow, profile with wall-clock mode while driving load specifically at that endpoint — CPU-only sampling can miss I/O-bound bottlenecks like N+1 queries.
