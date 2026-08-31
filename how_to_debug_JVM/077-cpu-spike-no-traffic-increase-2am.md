# #77 — CPU Spike With No Traffic Increase

> **Category:** CPU Profiling & Flame Graphs | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"CPU suddenly goes to 100% at 2 AM with no deployment and no traffic change. What's happening?"

## 😊 Explain It Simply (for anyone)
Think of a warehouse where boxes have been quietly piling up in the aisles all day without anyone noticing, because there's still just enough room to walk through. Then at 2 AM, the nightly cleanup crew shows up, discovers the aisles are jammed, and has to work frantically — moving boxes back and forth — just to make any space at all. From the outside it looks like the crisis started at 2 AM, but the real problem (boxes piling up) was happening all day; 2 AM was just when the system finally ran out of slack and had to react. In JVM terms, "boxes piling up" is memory that never gets released (a leak, or a cache with no size limit), and the "frantic cleanup crew" is the Garbage Collector (GC) — the JVM's automatic memory cleaner. When memory runs low, the JVM triggers a "Full GC," which pauses and rescans everything, burning CPU. If Full GCs start firing every few seconds, that GC work alone can peg CPU at 100% even though no new traffic arrived. The real fix isn't at 2 AM at all — it's finding and bounding whatever has been silently growing since the last restart.

## 📊 Visualize It
```
Time:     8am ---- 12pm ---- 6pm ---- 2am
Old Gen:  [##......][####....][######..][########] <- filling up all day
                                            ^
                                       heap nearly full
                                            v
                                    Full GC every 5s
                                            v
                                     CPU pegged at 100%
                              (no traffic change needed to trigger it)
```

## 🏭 The Real Production Answer (15-YOE Level)
This is a scheduled job or a deferred consequence (memory leak finally triggering full GC).

Check:
```bash
jstat -gcutil <pid> 500 20  # 20 samples at 500ms intervals
```

If Old Gen is near 100% and Full GC is running every 5 seconds, that's your CPU. GC threads consume CPU. The real bug is whatever caused heap exhaustion — a cache that wasn't bounded, a session store leaking, a batch job loading too much data.

Also check: `jcmd <pid> VM.native_memory` for native memory, cron logs for 2 AM jobs.

## 🔑 Key Takeaway
A CPU spike with no traffic change is usually GC working overtime on a heap that's been silently filling up all day — check `jstat -gcutil` before hunting for a "mystery" cause.
