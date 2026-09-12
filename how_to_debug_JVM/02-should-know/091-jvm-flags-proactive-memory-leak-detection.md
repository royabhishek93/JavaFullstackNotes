# #91 — JVM Flags for Proactive Memory Leak Detection

> **Category:** Memory Leaks End-to-End | **Type:** Advanced Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"What JVM flags do you set in production to help detect and recover from memory leaks?"

## 😊 Explain It Simply (for anyone)
Think of these JVM flags (startup switches that configure how the Java runtime behaves) like the safety systems in a car: a "black box" that records data right before a crash (heap dump on OOM), a fuel gauge that alerts you before you're empty (GC and memory monitoring), and an auto-shutoff valve that stops a gas leak before it becomes dangerous (auto-restarting the app on OutOfMemory). You don't wait for a leak to become a full-blown outage — you configure the car ahead of time so that when something goes wrong, it captures evidence AND recovers automatically instead of just dying silently.

## 📊 Visualize It
```
  [App running] --> [OOM occurs]
        |                |
        |                v
        |     -XX:+HeapDumpOnOutOfMemoryError
        |     (captures snapshot for MAT analysis)
        |                |
        v                v
  Monitoring        -XX:OnOutOfMemoryError="kill -9 %p"
  (Grafana/JMX)     (pod restarts immediately in K8s)
```

## 🏭 The Real Production Answer (15-YOE Level)

```bash
# Heap sizing
-Xms4g -Xmx4g                        # Equal min/max prevents heap resizing pauses
-XX:NewRatio=2                         # Old Gen = 2/3 of heap

# Heap dump on OOM
-XX:+HeapDumpOnOutOfMemoryError
-XX:HeapDumpPath=/var/log/heapdumps/   # Dedicated volume, not ephemeral

# GC selection and logging (Java 17 — G1GC is default)
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200
-Xlog:gc*:file=/var/log/gc.log:time,level,tags:filecount=10,filesize=20m

# Metaspace
-XX:MaxMetaspaceSize=512m             # Prevent native memory exhaustion
-XX:MetaspaceSize=128m                # Initial commit

# OOM action: restart pod (in K8s + Spring Boot Actuator)
-XX:OnOutOfMemoryError="kill -9 %p"  # Ensures pod restarts immediately

# NativeMemoryTracking for diagnosing off-heap
-XX:NativeMemoryTracking=summary      # Adds ~5% overhead but worth it
```

Monitoring:
- Alert on: Old Gen post-GC trending above 60% for 15 minutes.
- Alert on: GC overhead > 5% of CPU time (via `GarbageCollectionNotificationInfo` JMX).
- Dashboard: Grafana with Micrometer JVM metrics (`jvm_memory_used_bytes`, `jvm_gc_pause_seconds`).

For K8s: set `limits.memory` to `Xmx + 20%` to account for off-heap (Metaspace, native buffers, JIT code cache, direct ByteBuffers).

## 🔑 Key Takeaway
Configure `-XX:+HeapDumpOnOutOfMemoryError`, `-XX:OnOutOfMemoryError="kill -9 %p"`, and Old-Gen-based alerting BEFORE an incident happens, not after.
