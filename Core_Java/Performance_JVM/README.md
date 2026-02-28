# Performance & JVM

Interview preparation for JVM internals, garbage collection, memory management, and profiling.

## Quick Q&A Files (3-5 minutes per question)

| Q# | Question | Study Time |
|----|----------|-----------|
| [Q41](Q41_garbage_collection_types.md) | GC types (G1, ZGC, Shenandoah)? | 4m |
| [Q42](Q42_heap_vs_stack.md) | Heap vs stack memory? | 3m |
| [Q43](Q43_memory_leak_detection.md) | Memory leak detection - Tools and patterns? | 5m |
| [Q44](Q44_jvm_tuning.md) | JVM tuning - Flags and configuration? | 4m |
| [Q45](Q45_profiling_tools.md) | Profiling tools (VisualVM, YourKit, JFR)? | 4m |

## Interview Prep Strategy

1. **Start here:** Q42 (heap vs stack - 3 minutes)
2. **Then:** Q41 (GC types - 4 minutes)
3. **Advanced:** Q43-Q44 (memory leaks, tuning - 9 minutes)
4. **Tools:** Q45 (profiling - 4 minutes)
5. **Practice:** Analyze heap dump with MAT (1-2 hours)

## Interview Frequency

- **48%** - Q42 Heap vs stack
- **45%** - Q41 GC types, Q44 JVM tuning
- **42%** - Q43 Memory leak detection
- **40%** - Q45 Profiling tools

## Key Topics Covered

- Garbage collectors (Serial, Parallel, G1GC, ZGC)
- Memory areas (Young Gen, Old Gen, Metaspace)
- Stack memory and thread-local allocation
- Memory leak patterns (static collections, listeners)
- JVM flags (-Xmx, -Xms, -XX:+UseG1GC)
- Profiling with JFR, VisualVM, heap dumps

---

**Suggested study time:** 25-30 minutes for all Q&A files

**Interview frequency:** 40-48% (advanced/niche topics)
