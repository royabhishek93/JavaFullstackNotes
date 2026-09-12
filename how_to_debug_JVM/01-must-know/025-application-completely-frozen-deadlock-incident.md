# #25 — Application Completely Frozen — Deadlock

> **Category:** Common Production Incidents | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"Walk me through diagnosing: all requests are timing out with no errors, CPU is near 0%, the health check still passes, and requests are piling up in the queue. What's going on and how do you confirm it?"

## 😊 Explain It Simply (for anyone)
Picture two people trying to pass through two narrow doorways at the same time. Person A is holding doorway 1 open but waiting for doorway 2, which person B is holding open while waiting for doorway 1. Neither will let go first — they're stuck forever, and nobody else can get through either doorway. That's a deadlock: two (or more) threads (independent workers inside the same program) each holding a "lock" (an exclusive claim on a resource) that the other one needs, so both wait forever. The building doesn't look "broken" from outside (the front door / health check still opens fine), but nothing inside is moving.

## 📊 Visualize It
```
Thread-1: holds Lock A ---> waiting for Lock B
Thread-2: holds Lock B ---> waiting for Lock A
              ^_______________________|
              (circular wait = deadlock, CPU idle, all stuck)

jstack -l <pid> --> "Found one Java-level deadlock:" (smoking gun)
```

## 🏭 The Real Production Answer (15-YOE Level)

**Symptoms:**
- All requests timeout, no errors, CPU near 0%
- Health check still passes (health endpoint on separate thread)
- Requests pile up in queue

**Diagnosis:**
```bash
# jstack -l includes lock info — will show "Found X deadlock(s)"
jstack -l <pid> > /tmp/threads.txt
grep -A 30 "Found.*deadlock" /tmp/threads.txt

# Or: jcmd (safer, no ptrace)
jcmd <pid> Thread.print -l > /tmp/threads.txt
```

**Deadlock signature in jstack:**
```
Found one Java-level deadlock:
=============================
"Thread-1":
  waiting to lock monitor 0x00007f (object 0x..., a java.lang.Object),
  which is held by "Thread-2"
"Thread-2":
  waiting to lock monitor 0x00007e (object 0x..., a java.lang.Object),
  which is held by "Thread-1"
```

**Classic cause:**
```java
// Lock acquisition in opposite order
// Thread 1: acquires lock A, then tries lock B
// Thread 2: acquires lock B, then tries lock A
synchronized (lockA) {
    synchronized (lockB) { /* Thread 1 */ }
}
synchronized (lockB) {
    synchronized (lockA) { /* Thread 2 */ }
}
```

**Fix:** Always acquire locks in the same consistent order, or use `tryLock()` with timeout:
```java
if (lockA.tryLock(100, TimeUnit.MILLISECONDS)) {
    try {
        if (lockB.tryLock(100, TimeUnit.MILLISECONDS)) {
            try { /* do work */ }
            finally { lockB.unlock(); }
        }
    } finally { lockA.unlock(); }
}
```

## 🔑 Key Takeaway
Near-0% CPU with a passing health check but stuck requests is the classic deadlock fingerprint — `jstack -l` will name the deadlock explicitly, no guessing required.
