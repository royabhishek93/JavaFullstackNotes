# How to Debug JVM — 15 YOE Interview Prep Bundle

**2026 Edition | End-to-end production debugging: Heap · Threads · GC · CPU · Memory Leaks · Tools · Tuning | Scenario Q&As + Senior Trap Questions**

---

## Interview Files (Priority Order)

| # | File | Topic | Stars | Study Time |
|---|------|--------|-------|------------|
| 01 | [01_heap_dump_analysis_interview.md](01_heap_dump_analysis_interview.md) | Heap Dump Analysis (OOM, MAT, Dominator Tree) | ⭐⭐⭐⭐⭐ | 50 min |
| 02 | [02_thread_dump_analysis_interview.md](02_thread_dump_analysis_interview.md) | Thread Dump Analysis (Deadlocks, jstack, States) | ⭐⭐⭐⭐⭐ | 50 min |
| 03 | [03_gc_tuning_debugging_interview.md](03_gc_tuning_debugging_interview.md) | GC Tuning & Debugging (G1GC, ZGC, GC Logs) | ⭐⭐⭐⭐⭐ | 50 min |
| 04 | [04_cpu_profiling_flame_graphs_interview.md](04_cpu_profiling_flame_graphs_interview.md) | CPU Profiling & Flame Graphs (async-profiler, JFR) | ⭐⭐⭐⭐ | 45 min |
| 05 | [05_production_debugging_tools_interview.md](05_production_debugging_tools_interview.md) | Production Debugging Tools (jcmd, Arthas, jstat) | ⭐⭐⭐⭐⭐ | 45 min |
| 06 | [06_memory_leaks_end_to_end_interview.md](06_memory_leaks_end_to_end_interview.md) | Memory Leaks End-to-End (ThreadLocal, Static, Classloader) | ⭐⭐⭐⭐⭐ | 50 min |
| 07 | [07_jvm_tuning_production_playbook_interview.md](07_jvm_tuning_production_playbook_interview.md) | JVM Tuning Production Playbook (Heap, GC, K8s) | ⭐⭐⭐⭐ | 45 min |
| 08 | [08_common_production_incidents_interview.md](08_common_production_incidents_interview.md) | Common Production Incidents (10 scenarios + runbook) | ⭐⭐⭐⭐⭐ | 50 min |

---

## What Each File Contains

Every file includes:
- **Big Picture ASCII diagram** — architecture, workflow, decision trees
- **Conversational script** — exactly how a 15-YOE engineer narrates a production incident
- **8+ Scenario Q&As** — end-to-end incident stories with diagnosis → root cause → fix
- **4+ Advanced scenario Q&As** — deep internals (JVM phases, NMT, virtual threads)
- **6+ Senior Trap Questions** — named traps with the wrong assumption + correct rebuttal
- **Production Java code + shell commands** — all <20 lines, copy-paste ready
- **Interview Cheat Sheet** — quick-reference tables, numbers to know cold, triage mantras

---

## 2-Day Prep Plan

**Day 1 (highest signal):** 08 Incidents → 01 Heap Dump → 02 Thread Dump → 05 Tools

**Day 2 (depth):** 03 GC Tuning → 06 Memory Leaks → 04 CPU Profiling → 07 JVM Tuning

**Quick refresh:** Read only the Cheat Sheet at the bottom of each file (3 min each)

---

## Key Numbers to Know Cold

| Metric | Value |
|--------|-------|
| G1GC default pause target | 200ms (`-XX:MaxGCPauseMillis=200`) |
| ZGC max pause time | <1ms (concurrent, not STW) |
| ZGC CPU overhead vs G1 | +10-20% CPU for concurrent GC work |
| jmap -dump production risk | STW pause + potential OOM during write |
| async-profiler CPU overhead | <3% (safe for production) |
| JFR overhead | <1% with default settings |
| jcmd GC.heap_dump pause | 5-30s STW for 2-4GB heap |
| JVM native overhead above -Xmx | +500MB-1GB (metaspace + code cache + stacks) |
| K8s container limit headroom | Leave 20-25% above JVM total memory |
| Old Gen alert threshold | >80% = investigate; >95% = emergency |
| Full GC frequency (latency svc) | >1/hr = investigate |
| HikariCP default pool size | 10 connections |
| Thread stack size default | 512KB-1MB per thread |

---

## Tool Safety Quick Reference

| Tool | Safety | Use For |
|------|--------|---------|
| `jstat -gcutil` | ✅ Zero risk | GC trend monitoring |
| `jcmd Thread.print` | ✅ Zero risk | Thread dump |
| `jcmd VM.flags` | ✅ Zero risk | JVM configuration |
| `async-profiler cpu` | ✅ <3% overhead | CPU flame graphs |
| `JFR start` | ✅ <1% overhead | Always-on profiling |
| `Arthas trace/watch` | ⚠️ Instruments target class | Live method inspection |
| `jcmd GC.heap_dump` | ⚠️ STW pause | Heap capture |
| `jmap -dump` | ❌ Risky (STW + OOM risk) | Avoid in prod |
| `jstack -F` | ❌ ptrace attach | Last resort |
| `/actuator/heapdump` | ❌ Full GC + write pause | Pod out of LB first |

---

## OOM Type → Root Cause Cheat Sheet

| OOM Message | Root Cause | First Fix |
|-------------|-----------|-----------|
| `Java heap space` | Heap leak or undersized | `GC.class_histogram` → find top retained |
| `GC overhead limit exceeded` | Allocation > collection (leak) | Same as above |
| `Metaspace` | Classloader leak (CGLIB, OSGI) | Check classloader count per deploy |
| `Direct buffer memory` | Netty ByteBuf / NIO not released | `-Dio.netty.leakDetection.level=PARANOID` |
| `Unable to create native thread` | Too many threads | Reduce thread pool sizes or use virtual threads |
| K8s OOMKill (no JVM OOM) | RSS > container limit | Add `-XX:MaxMetaspaceSize` + native headroom |

---

## Triage Mantra (memorize this)

> "CPU high? Check GC with jstat first — if FGC is climbing, GC is the CPU consumer, not the app. Memory growing? jcmd class_histogram, then heap dump if needed. App frozen? Thread dump, look for 'Found deadlock'. K8s OOMKill without JVM OOM? It's RSS not heap — add native memory headroom. JVM crash with no logs? hs_err_pid file is your only clue."

---

## Related Content in This Repo

| Directory | Content |
|-----------|---------|
| [Java/Performance_JVM/](../Java/Performance_JVM/) | Q41-Q48: GC types, profiling tools, production OOM debugging basics |
| [Java/Garbage_Collection/](../Java/Garbage_Collection/) | Q1-Q8: GC theory, heap generations, marking/sweeping, GC algorithms |

> **This `how_to_debug_JVM/` bundle** focuses on **end-to-end production debugging workflows** — the incident investigation stories, tool commands, and trap questions. The files above cover the underlying theory.
