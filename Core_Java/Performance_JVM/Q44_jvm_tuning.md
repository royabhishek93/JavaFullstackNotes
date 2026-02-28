# 🎯 Q44: JVM Flags and Tuning?

> **Interview Frequency:** 45% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

App running slow. How to tune JVM?

---

## 📌 Important Flags

```bash
# Heap sizing (VERY IMPORTANT)
-Xms2g          # Min heap (set = max to prevent resizing)
-Xmx2g          # Max heap

# GC selection
-XX:+UseG1GC    # G1 collector (default)
-XX:+UseZGC     # ZGC (low latency)

# GC tuning
-XX:G1MaxGCPauseMillis=200       # Target pause time
-XX:ParallelGCThreads=8          # GC threads

# Memory pressure
-XX:+HeapDumpOnOutOfMemoryError  # Generate dump on OOM
-XX:HeapDumpPath=/tmp            # Where to save

# Logging
-Xlog:gc*:file=gc.log:time,level,tags
```

---

## ✅ Production Settings

```bash
java \
  -Xms4g -Xmx4g \
  -XX:+UseG1GC \
  -XX:MaxGCPauseMillis=200 \
  -XX:+HeapDumpOnOutOfMemoryError \
  -Xlog:gc*:file=gc.log \
  -jar app.jar
```

---

## 💬 Interview Tip (Say This Exactly)

"Always set -Xms = -Xmx (prevents heap resize). Use G1GC for most workloads. Monitor -Xlog:gc* output. Set HeapDumpOnOutOfMemoryError to debug leaks. Adjust ParallelGCThreads based on CPU cores."

---

## ⚠️ Common Pitfalls

**Pitfall 1: Tuning without baseline**
```text
// ❌ Changing GC flags blindly

// ✅ Measure current GC pause + throughput first
```

**Pitfall 2: Oversizing heap**
```text
// ❌ Huge heap → long GC pauses
-Xms32g -Xmx32g

// ✅ Right-size heap based on usage
```

**Pitfall 3: Using dev settings in prod**
```text
// ❌ Small heap from local dev
-Xmx512m

// ✅ Production-specific sizing
```

---

## 🛑 When NOT to Tune JVM Flags

- ❌ Before identifying bottleneck (CPU, I/O, DB?)
- ❌ Without monitoring GC logs
- ✅ DO use: After profiling confirms GC is the bottleneck

---

**Last Updated:** February 22, 2026  
**Next: [Q45_profiling_tools.md](Q45_profiling_tools.md)**
