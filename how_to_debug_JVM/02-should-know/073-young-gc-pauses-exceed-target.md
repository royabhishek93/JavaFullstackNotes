# #73 — Young GC pauses are 300ms but we set MaxGCPauseMillis=100

> **Category:** GC Tuning & Debugging | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"Young GC pauses are 300ms but we set MaxGCPauseMillis=100. Why isn't G1GC respecting the pause target?"

## 😊 Explain It Simply (for anyone)
Imagine telling a moving crew "please finish emptying this room in 10 minutes" — that's a target, not a magic spell. The crew will try their best: they'll bring fewer helpers into a room, or move smaller loads, to try to hit your 10-minute goal. But if the room turns out to have way more furniture than expected, or the hallway is jammed with other movers, the job might still take 25 minutes no matter how hard they try. G1GC's pause target (`MaxGCPauseMillis`) works the same way — it's a goal the garbage collector aims for by choosing how much work to do, but it can't refuse to do *necessary* work. If the necessary cleanup (like clearing out all of Eden, the "waiting room" for new objects) is simply bigger than what fits in the target time, the pause will run over — there's no way around it.

## 📊 Visualize It
```
MaxGCPauseMillis=100ms target, but actual breakdown:
┌───────────────────────┬────────┐
│ Root scanning          │  80ms  │
│ Eden evacuation        │ 120ms  │
│ Survivor copy          │  30ms  │
├───────────────────────┼────────┤
│ Actual pause           │ 230ms  │ ← target missed, work was mandatory
└───────────────────────┴────────┘
```

## 🏭 The Real Production Answer (15-YOE Level)
> This is the most common misconception about G1GC. `MaxGCPauseMillis` is a **target and a hint**, not a guarantee or a hard limit. G1GC uses it as input to its adaptive region selection algorithm — it picks fewer regions to collect when trying to meet the target. But it cannot always meet it.
>
> G1GC will exceed the target when: the minimum young collection work (all Eden must be collected) already exceeds the target, when reference processing takes longer than expected, or when root scanning is slow due to large thread counts or JNI roots.

**Why the pause exceeds the target:**

```
MaxGCPauseMillis=100ms, but:
  - Root scanning:          80ms  (many live threads, large JNI)
  - Eden evacuation:        120ms (Eden too large for the budget)
  - Survivor copy:          30ms
  ─────────────────────────────
  Actual pause:             230ms  ← G1 had no choice
```

**Tuning approach:**

```bash
# Reduce Eden size so evacuation fits in the budget:
-XX:G1NewSizePercent=5      # Min young gen (default 5%)
-XX:G1MaxNewSizePercent=20  # Max young gen (default 60%)
# Smaller young gen = shorter pause but more frequent GC (tradeoff)

# Check GC pause breakdown to find what's eating time:
-Xlog:gc+phases=debug:file=/var/log/app/gc.log:time,uptime
# Look for: "Scan RS", "Code Root Scanning", "Object Copy" durations
```

## 🔑 Key Takeaway
`MaxGCPauseMillis` is a target G1 aims for, never a hard guarantee — mandatory work like full Eden evacuation can and will exceed it.
