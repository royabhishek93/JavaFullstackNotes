# #29 — "A Restart Fixes the Production Incident"

> **Category:** Common Production Incidents | **Type:** Senior Trap Question | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"A restart fixes the production incident, right? Once the service is back up, we're done."

## 😊 Explain It Simply (for anyone)
Restarting a crashed service is like putting a bucket under a leaky pipe — the puddle on the floor disappears immediately, and everyone in the room feels relieved. But the pipe is still leaking. Come back tomorrow and the puddle will be right back where it was, growing at exactly the same rate, because nothing about the leak itself was fixed. A restart clears the symptom (memory pressure, stuck threads, exhausted connections) instantly, which is genuinely useful for keeping customers happy in the moment — but it says nothing about *why* it happened, and the same failure will recur on the same schedule unless someone finds and patches the actual leak.

## 📊 Visualize It
```
Restart timeline (leak NOT fixed):
Day 1: restart -> healthy -> leak grows -> OOM
Day 8: restart -> healthy -> leak grows -> OOM   <- same cycle, forever
Day 15: restart -> ...

Restart + RCA (leak actually fixed):
Day 1: restart -> capture baseline -> find root cause -> patch -> stays healthy
```

## 🏭 The Real Production Answer (15-YOE Level)
**WRONG** (for your incident postmortem). A restart is an operational response that restores service, but it is NOT a fix. Memory leaks, deadlocks, thread pool misconfigurations, and connection leaks will all recur on the same schedule.

**Correct answer:** Restart buys time for root cause analysis. After restart: capture metrics (jstat, thread counts, connection pool stats) to establish baseline. Monitor the trend. Schedule RCA within 24 hours. The fix is in code or configuration — not in restart scripts.

## 🔑 Key Takeaway
A restart restores service, not health — treat it as buying time for root cause analysis, not as the resolution itself.
