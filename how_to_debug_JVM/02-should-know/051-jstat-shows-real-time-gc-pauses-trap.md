# #51 — "jstat Shows Real-Time GC Pauses" — Trap

> **Category:** Production Debugging Tools | **Type:** Senior Trap Question | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"jstat shows real-time GC pauses."

## 😊 Explain It Simply (for anyone)
Think about your car's total odometer reading — it shows the total lifetime miles the car has ever driven, not how fast you're going right now. If you want to know your current speed, you need the speedometer, not the odometer. But you can still figure out an average speed from the odometer by checking it twice, a few minutes apart, and doing the math.

`jstat`'s garbage collection time columns work the same way — they're cumulative counters (running totals) that have been adding up since the application started, not a live readout of "how long did the pause I'm seeing right now last." To get a sense of current pause behavior, an engineer takes two readings some seconds apart and calculates the difference — the same trick as checking the odometer twice to estimate speed. But for the true, precise "speedometer" of individual pause durations, there's a better tool designed exactly for that: GC logging or Java Flight Recorder, which record each pause event with an exact timestamp and duration.

## 📊 Visualize It
```
 jstat FGCT column = cumulative total (like an odometer)
   t=0s   FGCT=40.0s
   t=10s  FGCT=45.2s   ← delta = 5.2s of Full GC in this window
                           (5.2 / 10) × 100 = 52% GC overhead!

 For exact pause timestamps → use:
   -Xlog:gc*:file=gc.log:time,uptime   or JFR
```

## 🏭 The Real Production Answer (15-YOE Level)
**WRONG.** `jstat -gcutil <pid> 1000` shows **cumulative counters**. The YGCT/FGCT columns accumulate from JVM startup. To get current pause time:
- Take two readings 10 seconds apart
- Calculate delta: `FGCT_now - FGCT_before` = GC time in that window
- `(delta / window_seconds) × 100` = % time in GC

**Correct answer:** `jstat` is for trend analysis, not instantaneous pause time. For real-time GC events with exact pause durations, use GC logging: `-Xlog:gc*:file=gc.log:time,uptime` or JFR.

## 🔑 Key Takeaway
jstat's GC time columns are lifetime cumulative totals — diff two readings for a rate, but use GC logging or JFR when you need exact individual pause durations.
