# #85 — Arthas in Production — What's Safe vs Risky

> **Category:** Production Debugging Tools | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"A colleague suggests using Arthas to debug a production issue. What's safe vs risky?"

## 😊 Explain It Simply (for anyone)
Think of a doctor's toolkit. A stethoscope, a thermometer, and a blood-pressure cuff are all "observation only" tools — they can never harm the patient, they just report information. But a syringe or a scalpel can change something about the patient, so those require much more caution and preparation.

Arthas is a toolkit for "listening in" on a running Java application. Most of its tools — like watching how long a method takes, or how often it's called — are pure observation, just like a stethoscope. They're extremely safe to use on a live, breathing production system. But a few of its tools can actually change something — like temporarily swapping out a piece of code while the program is running (like a mid-surgery graft) or running an arbitrary "command" that could accidentally trigger some real action (like accidentally telling the system to reload its configuration for real). Those need the same care a surgeon uses: test on a dummy or in a rehearsal room (staging environment) first.

## 📊 Visualize It
```
 Arthas Toolkit
 ┌─────────────────────────────┐
 │ SAFE (read-only)            │
 │  trace / watch / monitor    │
 │  version / jvm / sysprop    │
 │  classloader / sc / sm      │
 │  profiler start/stop        │
 ├─────────────────────────────┤
 │ USE WITH CARE (mutating)    │
 │  redefine (hot-swap)        │
 │  ognl (can call any method) │
 │  field (sets a value)       │
 └─────────────────────────────┘
```

## 🏭 The Real Production Answer (15-YOE Level)
**Safe (read-only operations):**
```bash
# Method call tracing — shows timing tree
trace com.app.Service method '#cost > 200'

# Method monitoring — call count, avg time, error rate
monitor com.app.Service method -c 5  # 5-second cycles

# Watch return values (be careful of sensitive data)
watch com.app.Service method returnObj -x 2

# JVM flags and system info
version / jvm / sysprop / sysenv

# Class/classloader info
classloader -l
sc com.app.*  # class search
sm com.app.Service  # method search

# CPU profiling (async-profiler integration)
profiler start --event cpu
profiler stop --file /tmp/cpu.html
```

**Use with care:**
```bash
# Redefine class (hot-swap) — changes behavior
redefine /tmp/MyClass.class

# Exec OGNL expressions — can trigger side effects
ognl "@com.app.Config@getInstance().reload()"

# Set field value
field com.app.MyService #timeout 5000
```

**Rule:** Arthas uses Java instrumentation — it does NOT change bytecode on disk. Safe for read ops. Hot-swap (`redefine`) should be tested in staging first.

## 🔑 Key Takeaway
Anything Arthas that only reads (trace/watch/monitor) is production-safe; anything that mutates (redefine/ognl/field) needs a staging rehearsal first.
