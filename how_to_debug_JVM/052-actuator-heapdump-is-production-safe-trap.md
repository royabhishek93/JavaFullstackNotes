# #52 — "Spring Actuator /heapdump Is Production-Safe" — Trap

> **Category:** Production Debugging Tools | **Type:** Senior Trap Question | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"Spring Actuator /heapdump is production-safe."

## 😊 Explain It Simply (for anyone)
Imagine ordering a full-body MRI scan for a patient in the middle of a busy emergency room, where the patient must lie perfectly still for many minutes while the entire scan completes — but the room needs that bed for the next incoming emergency the whole time. It's not that the MRI is inherently bad; it's that doing it at the wrong moment, in the wrong place, causes a pileup of other problems.

Spring Actuator's `/heapdump` endpoint is exactly that full-body MRI. Requesting it forces the application to first do a big, thorough memory cleanup (a full garbage collection) so it only captures "live" objects, and then writes the entire memory contents to a file, all before it can even respond to the web request that asked for it. For an application with several gigabytes of memory, that single request can take anywhere from 20 to 60 seconds to complete — during which the application looks completely frozen to everyone else, including the load balancer's health checks, which may then decide the "patient" (server) is dead and start sending traffic elsewhere in a panic, causing a cascade of failures across the fleet.

## 📊 Visualize It
```
 Request /actuator/heapdump
   │
   ▼
 Full GC (STW pause) ──▶ write entire heap to disk
   │                          │
   │        20-60 seconds     │
   ▼                          ▼
 Health check times out ──▶ LB marks pod unhealthy ──▶ 🔴 cascading failure
```

## 🏭 The Real Production Answer (15-YOE Level)
**WRONG.** `/actuator/heapdump` triggers:
1. A full GC (to capture live objects only)
2. Writes entire heap to disk synchronously
3. The HTTP response doesn't return until the dump is written

For a 4GB heap, this means a potential 20-60 second response time and STW pause. On a load-balanced service, this causes timeouts and health-check failures on that pod.

**Correct answer:** Either set `-XX:+HeapDumpOnOutOfMemoryError` and let JVM auto-dump, or use `jcmd GC.heap_dump` after first draining traffic from the pod via load balancer removal.

## 🔑 Key Takeaway
Never hit `/actuator/heapdump` on a live, load-balanced instance — drain traffic first, or rely on `-XX:+HeapDumpOnOutOfMemoryError` to capture it automatically.
