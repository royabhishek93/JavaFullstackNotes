# #86 — Setting Up JFR for Always-On Production Profiling

> **Category:** Production Debugging Tools | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"How would you set up Java Flight Recorder for production use?"

## 😊 Explain It Simply (for anyone)
Think of a car's dashcam that's always recording in a loop, constantly overwriting the oldest footage, so it only ever keeps, say, the last hour. If a crash happens, you don't have to have predicted it in advance — you just pull the last hour of footage from the camera's memory and watch exactly what happened right before impact.

Java Flight Recorder (JFR) is that dashcam for a running Java application. You turn it on once, when the app starts, and it continuously records everything important — CPU usage, memory cleanups (garbage collection), slow I/O, exceptions — into a circular buffer (a fixed-size recording area that keeps overwriting old data). The overhead is tiny (under 1%), so it's safe to leave running forever. When something goes wrong, you don't need to reproduce the bug — you just "rewind the dashcam" and dump the last 30 minutes or so to a file, then open it in a viewer (Java Mission Control) to see exactly what was happening at the moment of the incident.

## 📊 Visualize It
```
 JVM Startup
   │
   ▼
 ┌───────────────────────────────┐
 │  JFR "continuous" recording   │
 │  (circular buffer, 250MB/1h)  │
 │  CPU | GC | Threads | I/O ... │
 └───────────────────────────────┘
   │             ▲
   │  incident!  │
   ▼             │
 jcmd JFR.dump ──┘  → incident.jfr → open in JMC
```

## 🏭 The Real Production Answer (15-YOE Level)
**JVM startup flags (always-on with circular buffer):**
```bash
-XX:StartFlightRecording=name=continuous,
    settings=profile,
    maxsize=250m,
    maxage=1h,
    dumponexit=true,
    filename=/var/log/jfr/exit.jfr
```

**Dump on incident:**
```bash
# Dump last 30 minutes of data
jcmd <pid> JFR.dump name=continuous filename=/tmp/incident.jfr maxage=30m

# Start a timed recording
jcmd <pid> JFR.start duration=120s filename=/tmp/timed.jfr settings=profile

# Check recording status
jcmd <pid> JFR.check
```

**What JFR captures (overhead <1%):**
- CPU samples (method profiling)
- GC events with pause times
- Thread states and locks
- I/O latency
- Exceptions and errors
- Class loading events
- Heap statistics

**Analyze with JMC (Java Mission Control):** Open `.jfr` file, check "Automated Analysis" tab for top issues.

## 🔑 Key Takeaway
Always-on JFR with a circular buffer means you can retroactively "rewind" to any production incident without needing to reproduce it first.
