# #17 — "jmap -dump Is the Standard Way to Get a Heap Dump" — Trap

> **Category:** Production Debugging Tools | **Type:** Senior Trap Question | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"jmap -dump is the standard way to get a heap dump."

## 😊 Explain It Simply (for anyone)
This is a trick statement, like saying "the standard way to check if someone is alive is to shake them as hard as you can." Sure, it might technically work, but it's an old, rough, and risky method compared to modern gentler alternatives that experienced professionals actually use.

`jmap -dump` is an older command for photographing all the objects living in a Java application's memory (a heap dump). The problem is that its "live" mode first forces a full, disruptive memory cleanup (a full garbage collection) before taking the photo, which can freeze the whole application for a long time. It also uses a somewhat forceful, invasive way of attaching to the process, and if the application is already nearly out of memory, this "extra" step can actually be the final straw that crashes it. A senior engineer knows there's a gentler, JVM-native way to take the same photo, and even a way to have the JVM automatically take it exactly when it's needed with zero manual intervention.

## 📊 Visualize It
```
 ❌ jmap -dump:live  ──▶ forces full GC ──▶ long STW pause
                                          ──▶ can OOM mid-dump

 ✅ jcmd GC.heap_dump ──▶ JVM's own safe path

 ✅✅ -XX:+HeapDumpOnOutOfMemoryError ──▶ auto-fires exactly on OOM
```

## 🏭 The Real Production Answer (15-YOE Level)
**WRONG.** `jmap -dump` is legacy and risky in production:
- With `live` option, triggers a full GC before dump (causes STW pause)
- Attaches via PTRACE, can destabilize processes under load
- Can fail with OOM if heap is already near limit (dump requires extra memory)

**Correct answer:** Use `jcmd <pid> GC.heap_dump /path/file.hprof` — it uses the JVM's internal safe-dump mechanism. Better yet, set `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps/` at startup so it captures automatically on OOM without any intervention.

## 🔑 Key Takeaway
Don't reach for legacy `jmap -dump:live` — use `jcmd GC.heap_dump`, or better, let `-XX:+HeapDumpOnOutOfMemoryError` capture it automatically at the moment of failure.
