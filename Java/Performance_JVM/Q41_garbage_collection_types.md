# 🎯 Q41: Garbage Collection Types (G1GC, ZGC, Shenandoah)?

> **Interview Frequency:** 45% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

App has 30GB heap. GC pauses (stop-the-world) are 2 seconds. Users see lag. Which GC to use?

---

## 📌 GC Types

| GC | Heap | Latency | Throughput | Use |
|----|------|---------|-----------|-----|
| **G1GC** | 0-10GB | ~200ms | Good | Default (Java 9+) |
| **ZGC** | Large (TB) | <10ms | Good | Ultra-low latency |
| **Shenandoah** | Any | <10ms | Good | Low-pause apps |

---

## ✅ Tuning

```bash
# Default G1GC (good for most)
java -XX:+UseG1GC -Xmx30g

# Ultra-low latency (trading throughput)
java -XX:+UseZGC -Xmx30g

# Monitor: log GC pauses
java -Xlog:gc*:file=gc.log
```

---

## 💬 Interview Tip (Say This Exactly)

"G1GC default for most apps. Use ZGC/Shenandoah for real-time systems where pause times critical. Tune -Xmx/-Xms equal to prevent heap resizing. Monitor pause times with jstat."

---

## ⚠️ Common Pitfalls

**Pitfall 1: Choosing ZGC without need**
```text
// ❌ Switching to ZGC for small heap (<4GB)
// Overhead with no benefit

// ✅ Use G1GC for most apps, ZGC for large heap + low-latency needs
```

**Pitfall 2: Not setting -Xms = -Xmx**
```text
// ❌ Heap resizes during traffic spikes
java -Xms1g -Xmx8g

// ✅ Fix heap size to avoid resizing pauses
java -Xms8g -Xmx8g
```

**Pitfall 3: Ignoring GC logs**
```text
// ❌ No GC logs, blind tuning

// ✅ Enable GC logs and measure
-Xlog:gc*:file=gc.log
```

---

## 🛑 When NOT to Use ZGC/Shenandoah

- ❌ Small heaps (<4GB) and low latency requirements
- ❌ CPU-bound apps where throughput matters more
- ✅ DO use: Large heaps, strict pause SLAs

---

**Last Updated:** February 22, 2026  
**Next: [Q42_heap_vs_stack.md](Q42_heap_vs_stack.md)**
