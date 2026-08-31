# #12 — jcmd Commands to Run First When You SSH Into a Production Box

> **Category:** Production Debugging Tools | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"You SSH into a production server. The app is behaving oddly. What jcmd commands do you run in what order?"

## 😊 Explain It Simply (for anyone)
Think of a paramedic arriving at an emergency scene. They don't randomly start doing things — they follow a checklist: check if the patient is breathing, check pulse, check for visible injuries, check medical history. Only after that quick triage do they decide what treatment to give.

`jcmd` is the paramedic's toolkit for a sick Java application. It's a built-in command that talks directly to a running JVM (Java Virtual Machine, the engine that runs Java programs) and asks it questions without ever stopping it. The interview question is really asking: "what's your triage checklist?" A senior engineer has a fixed, memorized order: first find the patient (the process ID), then check what settings it was born with (JVM flags), then check its "heartbeat rhythm" (garbage collection health), then check if it's "frozen in place" (stuck threads), and finally check what's taking up its "internal storage" (memory). Doing this in order means you get the big picture before you commit to a more invasive test.

## 📊 Visualize It
```
SSH into box
   │
   ▼
[1] jps -l ──────────────▶ find PID
   │
   ▼
[2] jcmd VM.flags ───────▶ what heap/GC settings?
   │
   ▼
[3] jstat -gcutil ───────▶ GC health (O%, FGC rising?)
   │
   ▼
[4] jcmd Thread.print ───▶ any threads BLOCKED?
   │
   ▼
[5] GC.class_histogram ──▶ what objects dominate heap?
   │
   ▼
[6] VM.native_memory ────▶ off-heap memory breakdown
```

## 🏭 The Real Production Answer (15-YOE Level)
```bash
# 1. Find the PID
jps -l

# 2. What flags was JVM started with? (heap size, GC, dump-on-OOM?)
jcmd <pid> VM.flags

# 3. GC health — run for 10 iterations, 1 second apart
jstat -gcutil <pid> 1000 10
# Watch: O% (Old Gen) growing every iteration = memory leak
# Watch: FGC column incrementing = Full GC happening
# Watch: FGCT high relative to uptime = GC overhead

# 4. Thread snapshot
jcmd <pid> Thread.print > /tmp/threads.txt
grep -c "java.lang.Thread.State: BLOCKED" /tmp/threads.txt

# 5. Top objects without heap dump pause
jcmd <pid> GC.class_histogram | head -30

# 6. Native memory breakdown (if NMT enabled)
jcmd <pid> VM.native_memory summary
```

## 🔑 Key Takeaway
`jcmd` is the single Swiss-army-knife tool that lets you triage a sick JVM — PID, flags, GC health, threads, objects, memory — all without a restart or a heap-dump pause.
