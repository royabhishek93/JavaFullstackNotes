# #13 — Interpreting jstat Output in Production

> **Category:** Production Debugging Tools | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"You run `jstat -gcutil <pid> 1000`. The output shows: `S0=0 S1=98 E=85 O=97 M=78 YGC=1432 YGCT=12.4 FGC=8 FGCT=45.2`. What does this tell you?"

## 😊 Explain It Simply (for anyone)
Picture your car's dashboard: fuel gauge, engine temperature, oil pressure. No single gauge tells the whole story — you read them together. If the fuel gauge is near empty AND the temperature is climbing, that's a much more urgent situation than either alone.

`jstat` prints a row of "gauges" for the Java memory system (garbage collection, or GC — the process that automatically frees up memory no longer being used). Each letter is a gauge: how full is the "waiting room" for young objects (Eden), how full is the "long-term storage" for older objects (Old Gen), how many times has the "big cleanup" (Full GC) happened, and how long did those cleanups take. When you see the long-term storage gauge (Old Gen) sitting at 97% full and climbing, that's the equivalent of your fuel gauge blinking red — a crash (an OutOfMemoryError) could be imminent, and it's time to dig deeper immediately.

## 📊 Visualize It
```
Dashboard read: S0=0 S1=98 E=85 O=97 M=78

┌───────────────┬──────┬────────────────────────┐
│ Survivor S1    │ 98%  │ actively copying       │
│ Eden           │ 85%  │ next minor GC soon     │
│ Old Gen        │ 97%  │ 🔴 CRITICAL — near OOM │
│ Metaspace      │ 78%  │ fine                   │
└───────────────┴──────┴────────────────────────┘
YGC=1432 (frequent)   FGC=8, FGCT=45.2s (long pauses)
```

## 🏭 The Real Production Answer (15-YOE Level)
```
S0=0    S1=98   → Survivor 1 is 98% full — active copying into S1 from last minor GC
E=85           → Eden 85% full — another minor GC coming soon
O=97           → Old Gen 97% full — CRITICAL, about to trigger Full GC or OOM
M=78           → Metaspace 78% fine
YGC=1432       → 1432 young GCs (check uptime: 1432 GCs in 1 hour = one every 2.5s, frequent)
YGCT=12.4      → 12.4 seconds total young GC time
FGC=8          → 8 Full GCs (this is high)
FGCT=45.2      → 45.2 seconds in Full GC (each Full GC ~5.6s — very long)
```

**Action:** Old Gen 97% is the emergency. Run `jcmd <pid> GC.class_histogram` to find retention. Old Gen this high means either a leak or heap is undersized. With FGC=8 and FGCT=45.2s, we're potentially over the "98% in GC, <2% work done" threshold for GC overhead limit.

## 🔑 Key Takeaway
Never read a single jstat column in isolation — Old Gen % combined with FGC/FGCT tells you whether you're facing a leak, an undersized heap, or normal transient pressure.
