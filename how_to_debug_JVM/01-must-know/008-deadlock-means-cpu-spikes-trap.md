# #8 — "A Deadlock Means the CPU Spikes to 100%" (Trap)

> **Category:** Thread Dump Analysis | **Type:** Senior Trap Question | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
Interviewer plants: "We had a deadlock last week — CPU was pegged at 100%, definitely a deadlock."

## 😊 Explain It Simply (for anyone)
Picture two people frozen mid-argument, each with their arms crossed, refusing to move until the other backs down first. They're not sweating, not moving, not burning any energy at all — they're just... stuck, silently, forever. That's a real deadlock: total stillness, zero effort being spent, because nobody is doing anything, they're just frozen waiting on each other.

Now compare that to someone furiously pedaling a stationary bike as hard as they can, going nowhere, but clearly burning tons of energy. That's what a genuinely busy CPU (100% spike) looks like — a thread stuck in a loop, working extremely hard but making no real progress, or the garbage collector (the JVM's automatic memory cleanup crew) running nonstop. These are two completely different problems that just happen to both feel like "things are stuck," but one uses zero energy and the other uses maximum energy.

## 📊 Visualize It
```
DEADLOCK                        HIGH CPU (NOT deadlock)
─────────                       ───────────────────────
CPU:  ▁▁▁▁▁ (≈0%)               CPU:  ██████████ (100%)
State: BLOCKED                  State: RUNNABLE (infinite loop / GC storm)
Threads: frozen, waiting        Threads: spinning, burning cycles
```

## 🏭 The Real Production Answer (15-YOE Level)
"Actually, a deadlock produces the *opposite* CPU pattern — CPU drops to near *zero*. That's one of the diagnostic signatures I use to distinguish deadlock from other issues.

In a deadlock, all involved threads are in BLOCKED state — they're not executing any code, not consuming CPU. They're just sitting there waiting for locks that will never be released. The JVM scheduler doesn't even give them CPU time because they have nothing runnable to do.

High CPU — 100% — suggests a different problem: a runaway loop (infinite loop in RUNNABLE state), a garbage collection storm (GC threads running constantly), or CPU-intensive work without throttling.

If you saw 100% CPU, you likely had a livelock (threads keep retrying and failing), a tight polling loop, or significant GC pressure — all of which look very different in a thread dump."

## 🔑 Key Takeaway
A true deadlock drives CPU to near zero, not 100% — high CPU points instead to a runaway loop, livelock, or GC storm, each with a distinct thread-dump signature.
