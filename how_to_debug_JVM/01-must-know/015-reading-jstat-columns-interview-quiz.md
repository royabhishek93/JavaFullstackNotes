# #15 — Reading jstat Columns — Interview Quiz

> **Category:** Production Debugging Tools | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"What does each column in `jstat -gcutil` mean?"

## 😊 Explain It Simply (for anyone)
Imagine a factory dashboard with a row of gauges: one for the "incoming parts bin" (Eden), one for "partially finished goods waiting for inspection" (Survivor spaces), one for "finished goods warehouse" (Old Gen), and counters for "how many times the quick sorting line ran" (Young GC) versus "how many times the whole warehouse was shut down for a full inventory count" (Full GC). Each gauge alone tells you a little; together they tell you whether the factory is running smoothly or about to grind to a halt.

`jstat -gcutil` is exactly this dashboard for Java's automatic memory cleanup system (garbage collection). Once you memorize what each letter stands for, you can glance at one line of output and instantly know: is the "warehouse" (Old Gen) dangerously full? Is the "full inventory count" (Full GC) happening too often and eating up all the factory's working time? This is one of the most commonly asked rote-memorization questions in senior interviews because it proves you've actually operated production JVMs, not just read about them.

## 📊 Visualize It
```
 jstat -gcutil columns
 ┌─────┬───────────────────────────────┐
 │ S0/S1│ Survivor spaces (%)          │
 │ E    │ Eden (%)                     │
 │ O    │ Old Gen (%)  ── watch >80%   │
 │ M    │ Metaspace (%)                │
 │ CCS  │ Compressed Class Space (%)   │
 │ YGC  │ Young GC count (cumulative)  │
 │ YGCT │ Young GC time (s, cumul.)    │
 │ FGC  │ Full GC count (cumulative)   │
 │ FGCT │ Full GC time (s, cumul.)     │
 │ GCT  │ YGCT + FGCT                  │
 └─────┴───────────────────────────────┘
```

## 🏭 The Real Production Answer (15-YOE Level)
```
S0   — Survivor space 0 utilization (%)
S1   — Survivor space 1 utilization (%)
E    — Eden space utilization (%)
O    — Old Gen (Tenured) utilization (%)
M    — Metaspace utilization (%)
CCS  — Compressed Class Space utilization (%)
YGC  — Young GC count (cumulative)
YGCT — Young GC time (seconds cumulative)
FGC  — Full GC count (cumulative)
FGCT — Full GC time (seconds cumulative)
GCT  — Total GC time = YGCT + FGCT

Alert thresholds:
  O > 80%       → investigate retention / heap size
  FGC > 1/hr    → too frequent for latency-sensitive service
  FGCT/uptime   → if >5% of uptime spent in Full GC → GC overhead limit
  M > 90%       → Metaspace leak, classloader leak
```

**Pro tip for interview:** Calculate GC overhead: `FGCT / (uptime_seconds)`. If >5%, GC is eating your throughput.

## 🔑 Key Takeaway
Memorize the jstat column glossary cold — being able to instantly translate S0/E/O/M/YGC/FGC into "healthy vs critical" is a baseline expectation at senior level.
