# Dynamic Concurrency Adjustment During a Database Incident
> **Topic:** Task Scheduler | **Level:** Intermediate | **Frequency:** Medium

## The Setup

At 2am during a database incident, the on-call engineer needs to reduce the scheduler's concurrency from 10 to 2 to relieve DB pressure — without restarting the service and without killing in-flight tasks (which would cause data corruption). This scenario tests whether the candidate understands graceful degradation versus hard cutoff.

## The Question

"During a database incident, the on-call engineer wants to reduce the scheduler's concurrency from 10 to 2 without restarting the service. How do you implement `setConcurrency()` and what is the correct behavior for already-running tasks?"

## Diagram

```
GRACEFUL REDUCTION (concurrency: 10 → 2):
==========================================

  Before: 10 tasks running, 5 in queue
  Engineer calls: scheduler.setConcurrency(2)

  Correct behavior:
    - 10 running tasks continue to completion (NOT killed)
    - As each running task finishes, runningTasks decrements
    - runNextTask() checks: runningTasks(9) >= concurrency(2) → skip
    - More tasks finish: 8, 7, 6, 5, 4, 3 → still above 2 → skip
    - Eventually: runningTasks reaches 1 → runNextTask() starts next queued task
    - Steady state: max 2 tasks in-flight

  WRONG behavior (hard cutoff):
    - Kill 8 running tasks immediately
    - Mid-flight DB writes aborted → data corruption
    - Payment charges partially completed → duplicate charges

INCREASE (concurrency: 2 → 10):
=================================

  Before: 2 tasks running, 20 in queue
  Engineer calls: scheduler.setConcurrency(10)

  Correct behavior:
    - Call runNextTask() 8 more times (newLimit - oldLimit = 8)
    - 8 queued tasks start immediately to fill new slots
    - Queue drains from 20 to 12
```

## Model Answer (15 YOE)

```js
setConcurrency(newLimit) {
  if (newLimit < 1) throw new Error('Concurrency must be at least 1');

  const oldLimit = this.concurrency;
  this.concurrency = newLimit;

  if (newLimit > oldLimit) {
    // Concurrency increased — drain queue to fill new slots
    const newSlots = newLimit - oldLimit;
    for (let i = 0; i < newSlots; i++) {
      this.runNextTask();
    }
  }
  // If newLimit < oldLimit:
  // Running tasks finish naturally.
  // runNextTask() will not start new tasks until runningTasks drops below newLimit.
  // No explicit action needed — the guard condition handles it.
}
```

Why reducing concurrency does NOT stop in-flight tasks:

In-flight tasks are already past the `runNextTask()` guard. They are executing. Stopping them mid-flight would mean:
- Partial DB writes → inconsistent data
- Half-charged payments → duplicate charges on retry
- Open file handles → resource leaks

The correct model is graceful degradation: existing tasks complete, new tasks are throttled. The scheduler naturally reaches the new lower concurrency as tasks finish.

Why increasing concurrency needs explicit action:

When concurrency increases, `runningTasks` is already below the new limit, but `runNextTask()` was not called after the limit changed. Without explicitly calling it, queued tasks would wait for the next task completion to trigger `runNextTask()`. Calling it `newSlots` times immediately fills the newly opened capacity.

## Follow-up

**Q:** "What if the engineer sets `concurrency = 0` accidentally?"

**A:** The constructor and `setConcurrency` should both validate `newLimit >= 1`. A limit of 0 means no tasks ever run — the scheduler deadlocks. Throw an error immediately rather than silently creating an unusable state.

**Q:** "How would you expose this in a real incident response API?"

**A:** Expose a REST endpoint: `POST /admin/scheduler/concurrency { limit: 2 }`. Guard it with internal auth (API key or service-to-service mTLS). Log the change with the operator's identity and timestamp for the post-incident review. Alert if limit is set below a minimum safe value.
