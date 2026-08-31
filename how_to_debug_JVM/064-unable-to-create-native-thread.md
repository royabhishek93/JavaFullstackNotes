# #64 — "Unable to Create Native Thread" Is Not a Heap Problem

> **Category:** Heap Dump Analysis | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"'OutOfMemoryError: unable to create new native thread' — is this a heap problem?"

## 😊 Explain It Simply (for anyone)
This error sounds like a memory problem, but it's actually more like a hotel that's run out of ROOMS (operating system threads), not run out of FOOD (heap memory) — a completely different resource. Your program (a hotel manager) asks the operating system (the hotel building) for a new room every time it wants to create a thread (a worker doing a task), but a hotel building only has so many rooms, and the city (the OS) also caps how many rooms any one hotel manager is allowed to book (a "ulimit").

If your code keeps requesting new rooms without ever checking guests out (never stopping old threads, or spawning a new thread per request instead of reusing a pool), you eventually hit the room cap or the building's absolute limit, and asking for one more room fails — even though the kitchen (heap) still has plenty of food left.

## 📊 Visualize It
```
OS thread capacity: ulimit -u = 4096 (or /proc/.../threads-max)

Thread pool (bad pattern):
 req1 → new Thread() ┐
 req2 → new Thread() ├─ never join(), never pooled
 req3 → new Thread() ┘
   ...
 req4096 → new Thread()  → OS refuses: no more native threads
                          → "unable to create new native thread"

Fix: bounded ThreadPoolTaskExecutor
 req1..reqN → [ fixed pool: 20 threads ] → reused, capped
```

## 🏭 The Real Production Answer (15-YOE Level)

No — this is an OS-level resource exhaustion, not heap. The JVM cannot create a new OS thread. Two root causes:

1. **Too many threads** — thread pool misconfigured, thread leak, virtual thread misconfiguration in Java 21
2. **OS ulimit too low** — `ulimit -u` (max user processes) or `/proc/sys/kernel/threads-max`

Diagnosis:
```bash
# Count current threads in the JVM process
jcmd <pid> Thread.print | grep "^\"" | wc -l

# Or via /proc
ls /proc/<pid>/task | wc -l

# Check OS limit
ulimit -u
cat /proc/sys/kernel/threads-max

# Thread dump to identify what threads are doing
jcmd <pid> Thread.print > /tmp/threaddump.txt
# Look for patterns: hundreds of threads in WAITING state on the same lock/queue
```

Common thread leak patterns:
```java
// Thread leak — new thread per request
@PostMapping("/process")
public ResponseEntity<?> process(@RequestBody Request req) {
    new Thread(() -> doWork(req)).start(); // Never pooled, never joins
    return ResponseEntity.ok().build();
}

// Fix — use bounded executor
@Autowired
private ThreadPoolTaskExecutor taskExecutor; // Configured with max pool size

@PostMapping("/process")
public ResponseEntity<?> process(@RequestBody Request req) {
    taskExecutor.execute(() -> doWork(req));
    return ResponseEntity.ok().build();
}
```

## 🔑 Key Takeaway
This is OS thread-resource exhaustion, not heap — fix by bounding thread creation and checking ulimit, not by tuning heap flags.
