# #79 — Thread Contention Causing CPU Spin

> **Category:** CPU Profiling & Flame Graphs | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"You see 50 threads all RUNNABLE, CPU is 100%, but throughput is near zero. What's going on?"

## 😊 Explain It Simply (for anyone)
Picture 50 people all frantically jiggling the handle of a single locked door, convinced that if they just keep trying really hard, it'll open — meanwhile nobody is actually getting through. From a distance it looks like a hive of activity (everyone is "working"), but zero people are actually accomplishing anything. That's exactly what a CPU spin or busy-loop looks like in software: dozens of threads show as "RUNNABLE" (meaning the CPU considers them active, not idle), but they're stuck re-checking the same condition over and over instead of making progress — often because they're all fighting over the same lock or resource. You can catch this red-handed by taking a snapshot of what every thread is doing (a "thread dump") a couple of seconds apart, twice. If the same threads are frozen at the exact same spot in both snapshots, they're not doing new work — they're spinning in place. The fix is to make waiting threads actually rest (sleep briefly) instead of endlessly re-checking, similar to telling the door-jigglers to wait for a knock instead of yanking the handle nonstop.

## 📊 Visualize It
```
dump1 (t=0s):  Thread-1 RUNNABLE at CasLoop.retry()
               Thread-2 RUNNABLE at CasLoop.retry()
               ... (48 more, same spot)

dump2 (t=2s):  Thread-1 RUNNABLE at CasLoop.retry()  <- same place!
               Thread-2 RUNNABLE at CasLoop.retry()  <- same place!
               ... (48 more, still spinning)

CPU: 100%        Throughput: ~0        Diagnosis: busy-wait spin
```

## 🏭 The Real Production Answer (15-YOE Level)
Classic spin-wait / busy-loop anti-pattern. Threads are RUNNABLE but not making progress — spinning on a lock or a tight retry loop.

```bash
# Take 3 thread dumps 2 seconds apart
jstack <pid> > /tmp/dump1.txt && sleep 2 && jstack <pid> > /tmp/dump2.txt

# Look for same threads appearing RUNNABLE with same stack trace
grep -A 20 "RUNNABLE" /tmp/dump1.txt
```

If you see the same threads in the same place across all dumps, they're spinning. Common cause: hand-written spinlock, a `while (!done) {}` polling loop, or CAS-retry in a lock-free structure under extreme contention.

Fix: introduce backoff, use `LockSupport.parkNanos()`, or replace with proper `ReentrantLock` / `Semaphore`.

## 🔑 Key Takeaway
RUNNABLE threads at 100% CPU with near-zero throughput means spinning, not working — confirm with two thread dumps taken seconds apart and look for identical stacks.
