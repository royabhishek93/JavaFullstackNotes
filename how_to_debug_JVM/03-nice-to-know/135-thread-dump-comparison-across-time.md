# #135 — Thread Dump Comparison Across Time

> **Category:** Thread Dump Analysis | **Type:** Advanced Scenario Q&A | **Priority:** ⚙️ Expert/Niche

## 🗣️ The Interview Question
"You have thread dumps captured 30 seconds apart. How do you systematically compare them to identify stuck threads vs. normally cycling threads?"

## 😊 Explain It Simply (for anyone)
Imagine taking two photographs of a busy office, 30 seconds apart, and trying to figure out who's actually working versus who's frozen in place. If someone is in the exact same pose, holding the exact same paper, doing the exact same thing in both photos, they're probably stuck — genuinely frozen, not just naturally still for a moment. But if most people have shifted slightly — different papers, different poses — they're actively cycling through normal work.

This is exactly how you compare two thread dumps: take a "photo" of the whole system's threads at two moments in time, then look for exact matches. A thread showing the identical line of code in both snapshots isn't just busy — it's truly stuck there. You can also treat it like tracing "who is everyone waiting on" — if the same person is holding the stapler in both photos and everyone is still queued behind them, they are your bottleneck.

## 📊 Visualize It
```
dump1 (t=0s)                 dump2 (t=30s)
─────────────                ─────────────
http-exec-5:                 http-exec-5:
  OrderService.java:87  ══════  OrderService.java:87   ← IDENTICAL = STUCK

http-exec-9:                 http-exec-9:
  OrderService.java:40  ──►   OrderService.java:112     ← moved = cycling normally
```

## 🏭 The Real Production Answer (15-YOE Level)
"I do this in three passes:

**Pass 1: Thread state distribution**
Count states in each dump. If BLOCKED count grows dump-over-dump, you have escalating contention. If it's stable but high, you have a steady-state bottleneck.

```bash
grep "java.lang.Thread.State:" dump1.txt | sort | uniq -c
grep "java.lang.Thread.State:" dump2.txt | sort | uniq -c
```

**Pass 2: Identify stuck threads**
A thread is stuck if its stack trace is byte-for-byte identical across dumps. I extract each thread's stack:
```bash
# Get all thread names + first 5 stack frames from dump1
awk '/^"/{name=$0} /at /{print name": "$0}' dump1.txt | head -100
```

If `http-nio-exec-5` shows the exact same `OrderService.java:87` in both dumps, that thread is stuck.

**Pass 3: Lock ownership tracking**
Find who owns contended locks. In dump1, if Lock-X is held by Thread-A and 50 threads wait for it, and in dump2 it's still held by Thread-A — Thread-A is your bottleneck. Trace what Thread-A is doing.

For large thread dumps (hundreds of threads), I use fastthread.io — paste your dump, it generates a visual breakdown of states, groups identical stack traces, and highlights stuck threads immediately. TDA (Thread Dump Analyzer) is a local GUI option if you can't share dumps externally."

## 🔑 Key Takeaway
Compare thread dumps taken seconds apart: a thread frozen on the *exact same* stack frame across snapshots is truly stuck, while shifting stack frames indicate normal, healthy cycling.
