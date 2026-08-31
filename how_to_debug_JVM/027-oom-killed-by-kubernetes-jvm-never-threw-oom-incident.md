# #27 — OOM-Killed by Kubernetes — JVM Never Threw OOM

> **Category:** Common Production Incidents | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"Walk me through diagnosing: `kubectl describe pod` shows `OOMKilled` as the restart reason, but there's no `java.lang.OutOfMemoryError` anywhere in the application logs, and JVM heap usage looked completely fine. How can the pod be OOM-killed if the JVM never complained?"

## 😊 Explain It Simply (for anyone)
Imagine you rent an apartment (the container) with a strict total-weight limit for everything you bring in, and you also have a smaller personal closet inside it (the JVM heap) with its own separate size limit. You could keep your closet perfectly tidy and under its limit forever, but if you also have furniture, boxes in the hallway, and other stuff scattered around the apartment (metaspace, thread stacks, native memory, JVM overhead) that together push the *whole apartment* over its weight limit, the building manager (the Linux kernel's OOM-killer) will evict you immediately — without ever caring whether your personal closet was tidy. That's why the JVM itself never logs an OOM: it wasn't the heap that broke the limit, it was everything else the JVM needs that lives outside the heap.

## 📊 Visualize It
```
Container memory limit: 4GB
┌─────────────────────────────────────┐
│ Heap (-Xmx2g)     [██████████] 2GB  │  <- JVM watches this, looks "fine"
│ Metaspace          [███] 0.3GB      │
│ Code cache         [██] 0.2GB       │
│ Thread stacks       [██] 0.3GB      │
│ Native/overhead    [████] 0.5GB     │
├─────────────────────────────────────┤
│ Total RSS ~ 3.3-4.2GB  --> exceeds 4GB sometimes --> SIGKILL by kernel │
└─────────────────────────────────────┘
     (no JVM OOM log, no heap dump — kernel just kills the process)
```

## 🏭 The Real Production Answer (15-YOE Level)

**Symptoms:**
- Pod restarts with `OOMKilled` reason in `kubectl describe pod`
- No `java.lang.OutOfMemoryError` in application logs
- JVM heap usage looks fine

**Why:** Linux kernel OOM-killer acts on total RSS (Resident Set Size), not just JVM heap. JVM RSS = heap + metaspace + code cache + thread stacks + direct buffers + JVM overhead. If RSS exceeds the container memory limit, the kernel kills the process with SIGKILL — no JVM OOM, no heap dump, just a dead pod.

**Diagnosis:**
```bash
kubectl describe pod <pod-name> | grep -A 5 "Last State"
# Shows: Reason: OOMKilled

# In container, check total memory usage
cat /proc/<pid>/status | grep VmRSS
# Or
jcmd <pid> VM.native_memory summary  # if NMT enabled
```

**Fix:**
```bash
# Leave headroom above -Xmx
# JVM native overhead = ~500MB-1GB on top of heap

# If container limit = 4GB:
-Xmx2g                          # heap
-XX:MaxMetaspaceSize=256m       # metaspace cap
-XX:ReservedCodeCacheSize=256m  # code cache
-Xss512k                        # thread stacks (if many threads)
# Estimated RSS: 2G + 0.25G + 0.25G + threads + ~300MB overhead = ~3.2G
# 800MB headroom in 4G container

# OR use percentage-based sizing:
-XX:MaxRAMPercentage=70.0       # Use 70% of container RAM for heap
```

## 🔑 Key Takeaway
`OOMKilled` with no JVM OOM error means the kernel killed on total RSS, not heap — always leave 1-1.5GB of headroom above `-Xmx` for metaspace, code cache, and native overhead.
