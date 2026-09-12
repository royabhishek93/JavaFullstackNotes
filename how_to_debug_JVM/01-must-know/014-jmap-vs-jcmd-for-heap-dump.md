# #14 — jmap vs jcmd for Heap Dumps — Which Do You Use?

> **Category:** Production Debugging Tools | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"You need to capture a heap dump from production. Do you use jmap or jcmd?"

## 😊 Explain It Simply (for anyone)
Imagine you need to photograph everyone in a crowded, busy room to see who's there. One method is to demand total silence, make every single person freeze in an awkward pose, and take a slow, careful photo — this disrupts the room for a long time and might even cause a panic if the room is already overcrowded. The other method is to use a modern security camera that's built into the room, designed to take the snapshot cleanly and efficiently with minimal disruption.

A heap dump is a snapshot of every object ("everyone in the room") living in a Java application's memory. `jmap -dump` is the old, disruptive method — it forces a full cleanup (garbage collection) first, which can freeze the whole application for a long time, and can even fail if memory is already nearly full. `jcmd GC.heap_dump` is the modern, built-in security-camera approach — it uses the JVM's own internal, safer mechanism to take the same photo with less risk. Even better: you can tell the JVM in advance, "if you ever run completely out of memory, automatically take this photo for me right then" — so you get the snapshot exactly when it's needed, with zero extra planning.

## 📊 Visualize It
```
 Need a heap dump?
   │
   ├─▶ jmap -dump:live  ──▶ forces full GC ──▶ 🔴 risky STW pause
   │
   ├─▶ jcmd GC.heap_dump ─▶ JVM-safe path  ──▶ ✅ preferred
   │
   └─▶ -XX:+HeapDumpOnOutOfMemoryError ─▶ ✅ zero extra pause, auto-fires on OOM
```

## 🏭 The Real Production Answer (15-YOE Level)
Always `jcmd` first. Here's why:

```bash
# Preferred: jcmd GC.heap_dump
jcmd <pid> GC.heap_dump /tmp/heap-$(date +%Y%m%d-%H%M%S).hprof
# Safe, uses JVM's built-in mechanism, signals JVM cleanly

# Legacy: jmap -dump (avoid in production)
jmap -dump:format=b,live,file=/tmp/heap.hprof <pid>
# Issues: triggers full GC (live filter), can cause OOM mid-dump if heap is near limit

# Best: set flag at startup, JVM auto-dumps on OOM
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/var/dumps/
# Zero extra pause — JVM writes dump during OOM handling
```

**Mitigating the pause:** Heap dump writes all live objects. For 4GB heap, this can take 10-30 seconds of STW pause. Mitigate by:
1. Route traffic to other instances first (take pod out of LB)
2. Schedule during low traffic window
3. Use `-XX:+HeapDumpOnOutOfMemoryError` so it only fires when OOM is inevitable anyway

## 🔑 Key Takeaway
Prefer `jcmd GC.heap_dump` over legacy `jmap -dump`, and set `-XX:+HeapDumpOnOutOfMemoryError` so the dump captures itself automatically at the moment of failure.
