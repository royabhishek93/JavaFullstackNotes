# #134 — Programmatic Deadlock Detection with ThreadMXBean

> **Category:** Thread Dump Analysis | **Type:** Advanced Scenario Q&A | **Priority:** ⚙️ Expert/Niche

## 🗣️ The Interview Question
"You need to add automated deadlock detection to your service that fires an alert and triggers a heap dump when detected. How do you implement this?"

## 😊 Explain It Simply (for anyone)
Instead of waiting for a human on-call engineer to notice something's wrong and manually run diagnostic commands, imagine installing a smoke detector inside the building that constantly sniffs the air, and the instant it detects smoke, it automatically calls the fire department AND snaps a photo of the room for later investigation — all without anyone needing to press a button. That's what building automated deadlock detection means: code that periodically checks "is anyone stuck waiting on anyone else in a circle?" and, if so, immediately pages someone and saves a snapshot of memory for later analysis.

The "smoke detector" here is a built-in JVM tool called `ThreadMXBean` — think of it as a security camera system that's always watching every thread and can instantly tell you which ones are stuck in a circular wait, without you having to manually run commands.

## 📊 Visualize It
```
 [ Scheduled check every 10s ]
           │
           ▼
 ThreadMXBean.findDeadlockedThreads()
           │
     found? ──No──► do nothing
           │
          Yes
           ▼
   log details + fire alert + dump heap
```

## 🏭 The Real Production Answer (15-YOE Level)
```java
@Component
public class DeadlockDetector {

    private static final Logger log = LoggerFactory.getLogger(DeadlockDetector.class);
    private final ThreadMXBean mxBean = ManagementFactory.getThreadMXBean();

    @Scheduled(fixedDelay = 10_000) // every 10 seconds
    public void detectDeadlocks() {
        long[] deadlockedThreadIds = mxBean.findDeadlockedThreads();
        // findDeadlockedThreads() covers java.util.concurrent locks too
        // findMonitorDeadlockedThreads() only covers synchronized monitors

        if (deadlockedThreadIds == null) return;

        log.error("DEADLOCK DETECTED! {} threads involved", deadlockedThreadIds.length);

        ThreadInfo[] threadInfos = mxBean.getThreadInfo(
            deadlockedThreadIds,
            true,   // include locked monitors
            true    // include locked synchronizers
        );

        for (ThreadInfo info : threadInfos) {
            log.error("Thread: {} State: {} Blocked on: {}",
                info.getThreadName(),
                info.getThreadState(),
                info.getLockName());
            log.error("Lock owner: {}", info.getLockOwnerName());
        }

        alertingService.fireAlert("DEADLOCK", "Deadlock detected in " +
            deadlockedThreadIds.length + " threads");
        triggerHeapDump(); // optional: capture heap state
    }

    private void triggerHeapDump() {
        try {
            MBeanServer server = ManagementFactory.getPlatformMBeanServer();
            HotSpotDiagnosticMXBean hotspot = ManagementFactory.newPlatformMXBeanProxy(
                server, "com.sun.management:type=HotSpotDiagnostic",
                HotSpotDiagnosticMXBean.class);
            hotspot.dumpHeap("/tmp/deadlock-heapdump.hprof", true);
        } catch (Exception e) {
            log.error("Failed to dump heap", e);
        }
    }
}
```

"Note: `findDeadlockedThreads()` detects deadlocks involving both intrinsic monitors (`synchronized`) AND `java.util.concurrent` locks (`ReentrantLock`). The older `findMonitorDeadlockedThreads()` only detects `synchronized` monitor deadlocks. Always use `findDeadlockedThreads()` in modern code."

## 🔑 Key Takeaway
Use `ThreadMXBean.findDeadlockedThreads()` (not the older monitor-only variant) in a scheduled check to auto-detect deadlocks across both `synchronized` and `java.util.concurrent` locks, then alert and heap-dump automatically.
