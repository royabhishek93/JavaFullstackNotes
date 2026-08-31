# #130 — JVM Native Crash (hs_err_pid file)

> **Category:** Common Production Incidents | **Type:** Scenario Q&A | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"Walk me through diagnosing: the JVM process just disappears with no graceful shutdown, and you find an `hs_err_pid<PID>.log` file in the working directory. How do you figure out what actually killed it?"

## 😊 Explain It Simply (for anyone)
Normally, when a Java program crashes because of a bug in *your* Java code, the JVM catches it gracefully and prints a normal-looking error. But sometimes the crash happens one level deeper — inside the JVM's own engine room, often because of "native" code (code written in C/C++ that Java is calling out to, like a compression library or a networking driver). When that engine room itself blows up, the whole ship goes down instantly with no warning, and the JVM leaves behind a black-box flight recorder — the `hs_err_pid` file — describing exactly where and how the crash happened, so engineers can figure it out after the fact.

## 📊 Visualize It
```
Java code (safe)           Native library (JNI/C++)
  |                                |
  v                                v
[JVM] -----------calls into------> [libnetty_native.so]
                                        |
                                  SIGSEGV (bad memory access)
                                        |
                                  hs_err_pid12345.log written
                                  process dies immediately, no cleanup
```

## 🏭 The Real Production Answer (15-YOE Level)

**Symptoms:**
- JVM process disappears (no graceful shutdown)
- `hs_err_pid<PID>.log` file in working directory (or /tmp)
- Usually caused by JNI code, native libraries, or JDK bugs

**Diagnosis:**
```bash
# Read the crash file
cat hs_err_pid12345.log | head -100

# Key sections to check:
# 1. "SIGSEGV (0xb)" or "SIGBUS" — native memory access violation
# 2. "Current thread" — which thread crashed
# 3. "Stack" — native frames showing the crash location
# 4. "Java frames (J=compiled Java code..." — Java call stack
# 5. "Heap" section — heap state at time of crash
```

**Sample hs_err header:**
```
#
# A fatal error has been detected by the Java Runtime Environment:
#
#  SIGSEGV (0xb) at pc=0x00007f9a12345678, pid=12345, tid=0x00007f9a00000001
#
# JRE version: OpenJDK 17.0.8 (17.0.8+7)
# Java VM: OpenJDK 64-Bit Server VM (17.0.8+7, mixed mode, tiered, compressed oops)
# Problematic frame:
# C  [libnetty_transport_native.so+0x12345]  <- native library crash
```

**Common causes:**
- JNI library bug (Netty native transport, RocksDB, Snappy compression)
- Out-of-bounds native memory access
- JDK bug (check JDK release notes)
- Native memory corruption from direct ByteBuffer misuse

**Fix:** Update native library version, switch to Java implementation (remove native transport), or upgrade JDK.

## 🔑 Key Takeaway
Look at the "Problematic frame" line first — a `C [...]` frame means the crash is in native code (a library or JNI bug), not in your Java logic.
