# #94 — P99 Latency Spikes Every 2 Hours

> **Category:** JVM Tuning Production Playbook | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"Our service has P99 latency of 15ms normally. Every ~2 hours we see a spike to 2-5 seconds for about 30 seconds. The pattern is regular. What would you investigate?"

## 😊 Explain It Simply (for anyone)
Imagine a busy restaurant kitchen (your service) that runs smoothly all day, but every two hours the entire kitchen stops cooking for 30 seconds while the head chef does a full deep-clean of every single pot, pan, and surface (a "Full Garbage Collection" — the JVM stopping everything to clean up unused memory). Random messes are annoying but not alarming; a mess that happens like clockwork every two hours tells you something specific is filling up on a schedule — like a shelf (Old Generation memory) that only has room for two hours' worth of leftovers before it must be emptied all at once. Finding what fills that shelf, and how fast, is the key to stopping the freeze.

## 📊 Visualize It
```
Latency (ms)
 5000 |                    ▄▄
 2000 |                    ██
      |                    ██
   15 |▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁██▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁
      └───────────────────────────────────────────────────────► time
             ~2 hours              ~2 hours
      (Old Gen fills)        (Full GC fires again)
```

## 🏭 The Real Production Answer (15-YOE Level)
> "That timing regularity is the key signal. Random latency spikes are harder — regular ones usually point
> to a scheduled event. My differential is:
>
> 1. Full GC triggered by Old Gen exhaustion (most likely)
>    Check: gc.log for 'Pause Full' or 'GC(N) Pause Young (Full)' entries
>    The 30-second duration at 2-hour intervals fits a large heap Full GC
>
> 2. Scheduled tasks: Spring's @Scheduled, cron jobs, cache eviction timers
>
> 3. Connection pool maintenance: HikariCP has housekeeping thread every 30 seconds but that wouldn't
>    cause 2-hour intervals
>
> My investigation:
>
> First, grep GC logs:
>   grep 'Pause Full' /logs/gc.log | awk '{print $1, $NF}'
>
> If Full GCs are there, the follow-up question is why Old Gen fills every 2 hours:
> - Objects surviving too many Young GC cycles (tenure threshold too low)
> - Actual memory leak with slow accumulation
> - Large object allocation going directly to Old Gen (TLAB overflow)
>
> Tune path for G1GC:
>   -XX:G1HeapRegionSize=16m           # Prevents large objects bypassing Young Gen
>   -XX:G1NewSizePercent=30            # More Young Gen space
>   -XX:G1MaxNewSizePercent=50
>   -XX:MaxGCPauseMillis=100           # More aggressive GC scheduling
>
> If after tuning Full GCs persist, the answer is ZGC — its concurrent collection eliminates Full GC pauses
> by design, though you take the CPU overhead hit."

## 🔑 Key Takeaway
A perfectly regular latency spike is a scheduling clue, not randomness — grep the GC log for Full GC pauses first before chasing exotic theories.
