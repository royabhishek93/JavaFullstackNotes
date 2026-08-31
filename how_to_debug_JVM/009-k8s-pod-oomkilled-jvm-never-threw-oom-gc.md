# #9 — Our Kubernetes pod keeps getting OOMKilled but the JVM never throws OOM

> **Category:** GC Tuning & Debugging | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"Our Kubernetes pod keeps getting OOMKilled but the JVM never throws OOM. What's happening?"

## 😊 Explain It Simply (for anyone)
Think of the JVM (the engine that runs your Java program) as a tenant renting an apartment (a Kubernetes pod) with a strict total floor-space limit. The tenant only watches *one* room carefully — the "living room" (the heap, where most of your data lives) — and only complains ("throws OutOfMemoryError") if that one room gets too full. But the tenant also has a garage, a closet, and a basement (things like thread stacks, JIT-compiled code storage, and off-heap memory) that also take up floor space and aren't being watched as closely. If those extra rooms plus the living room together exceed the *building's* total floor limit, the landlord (the Linux kernel/container) doesn't wait for the tenant to complain — it just evicts them immediately. That's why you can get kicked out (OOMKilled) even though the tenant (JVM) never felt like their main room (heap) was full.

## 📊 Visualize It
```
Container Memory Limit (e.g. 2GB)
┌─────────────────────────────────────┐
│ Heap (-Xmx)         ████████ 1.5GB  │ ← JVM watches this, feels fine
│ Metaspace           ██ 0.3GB        │
│ Thread stacks       █ 0.2GB         │ ← JVM does NOT track vs container limit
│ Code cache          █ 0.2GB         │
│ Direct buffers      █ 0.1GB         │
└─────────────────────────────────────┘
  Total: 2.3GB > 2GB limit → kernel OOM-killer kills pod (JVM never saw it coming)
```

## 🏭 The Real Production Answer (15-YOE Level)
> The Linux kernel's OOM killer is killing the pod because the JVM's native memory usage exceeds the container memory limit — before the JVM itself hits the heap limit and triggers GC or OOM.
>
> The JVM uses more memory than just the heap:
> - Heap (your -Xmx)
> - Metaspace (class metadata)
> - Thread stacks (~512KB per thread default)
> - Code cache (JIT-compiled code)
> - Direct ByteBuffers (off-heap NIO)
> - GC data structures

**The container memory formula:**

```
Container Memory Limit should be:
  Xmx + Metaspace + (threads × stack) + code cache + direct memory + headroom

Example for a service with 512 threads, 256MB Metaspace, 256MB code cache:
  Heap:        2048MB  (-Xmx2g)
  Metaspace:    256MB  (-XX:MaxMetaspaceSize=256m)
  Stacks:       256MB  (512 × 0.5MB, -Xss512k)
  Code cache:   256MB  (-XX:ReservedCodeCacheSize=256m)
  Direct mem:   128MB  (-XX:MaxDirectMemorySize=128m)
  Headroom:     256MB
  ─────────────────
  Total:       3200MB  ← set container limit to 3.5GB

# Critical flag for containers (Java 10+):
-XX:+UseContainerSupport  # Enabled by default Java 10+
# Makes JVM read cgroup memory limits for ergonomic heap sizing
# Without this (Java 8 before 8u191): JVM reads HOST memory, ignores cgroup limit

# Ergonomic heap sizing in containers:
-XX:InitialRAMPercentage=50.0   # Initial heap = 50% of container memory
-XX:MaxRAMPercentage=75.0       # Max heap = 75% of container memory
# Leaves 25% for non-heap JVM memory

# Check what ergonomics calculated:
java -XX:+PrintFlagsFinal -XX:MaxRAMPercentage=75 -version 2>&1 | grep -E "MaxHeapSize|InitialHeapSize"
```

## 🔑 Key Takeaway
OOMKilled with no JVM OOM means non-heap memory (stacks, Metaspace, code cache, direct buffers) pushed total usage past the container limit — size the container for the whole JVM, not just `-Xmx`.
