# 🎯 Q45: Profiling Tools and Benchmarking?

> **Interview Frequency:** 40% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

Method X is slow. Is it CPU-bound or I/O-bound? How to measure?

---

## 📌 Profiling Tools

| Tool | Use | Output |
|------|-----|--------|
| **JProfiler** | GUI profiler | CPU, memory, threads |
| **YourKit** | Commercial profiler | Deep analysis |
| **async-profiler** | Sampling (low overhead) | CPU/allocation |
| **JFR (JDK Flight Recorder)** | Built-in (Java 8+) | Events, analysis |
| **jstat** | GC monitoring | Heap, GC stats |

---

## 📌 Benchmarking (JMH)

```java
@Benchmark
public void stringConcatenation() {
    String result = "";
    for (int i = 0; i < 1000; i++) {
        result += "x";  // Bad: creates 1000 strings
    }
}

// Run: java -jar jmh-benchmark.jar
// Output: Throughput, avg time, GC impact
```

---

## ✅ Process

1. **Identify slow method** - Use profiler CPU sampling
2. **Check CPU vs I/O** - Look at I/O waits
3. **Benchmark changes** - JMH to measure improvement
4. **Memory - Check allocations** - async-profiler memory mode
5. **Monitor GC** - jstat or -Xlog:gc

---

## 💬 Interview Tip (Say This Exactly)

"Use async-profiler for low-overhead sampling. JFR for events. JMH for benchmarking changes. Don't guess, measure. Profile production with low sampling rates to avoid overhead."

---

**Last Updated:** February 22, 2026  
**Previous: [Q44_jvm_tuning.md](Q44_jvm_tuning.md) | Next: [../Testing/Q46_test_types.md](../Testing/Q46_test_types.md)**
