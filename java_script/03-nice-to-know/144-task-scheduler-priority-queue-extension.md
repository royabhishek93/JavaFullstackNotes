# Priority Queue Extension — Flipkart Plus Members First
> **Topic:** Task Scheduler | **Level:** Intermediate | **Frequency:** Medium

## The Setup

Flipkart Plus premium members should have their order processing prioritised over regular users. The base scheduler is FIFO. This scenario tests whether the candidate can extend the data structure cleanly without breaking the existing contract, and whether they can reason about trade-offs between two-queue and heap approaches.

## The Question

"Premium Flipkart Plus members should have their order processing prioritised over regular users. How do you extend the TaskScheduler to support priority queuing? What are the trade-offs between a two-queue approach and a min-heap?"

## Diagram

```
TWO-QUEUE APPROACH (high vs normal):
======================================
  highQueue:    [ Plus-order-1,  Plus-order-2 ]
  normalQueue:  [ Reg-order-1,   Reg-order-2,  Reg-order-3 ]

  runNextTask() always drains highQueue first:
    if highQueue.length > 0 → dequeue from highQueue
    else → dequeue from normalQueue

  Starvation risk: if Plus orders arrive continuously,
  regular orders may wait indefinitely.
  Mitigation: age-based promotion or round-robin after N high-priority tasks.

MIN-HEAP APPROACH (numeric priority):
=======================================
  heap: [ {priority:1, task}, {priority:5, task}, {priority:10, task} ]
  extractMin() always returns lowest priority number (highest urgency)
  Supports arbitrary priority levels, not just two tiers.
  Cost: O(log n) insert + extract vs O(1) for array shift.
```

## Model Answer (15 YOE)

**Approach A — Two queues (simple, O(1) for two tiers):**

```js
class PriorityTaskScheduler {
  constructor(concurrency) {
    this.concurrency = concurrency;
    this.runningTasks = 0;
    this.highQueue = [];   // priority 'high'
    this.normalQueue = []; // priority 'normal'
  }

  addTask(task, priority = 'normal') {
    return new Promise((resolve, reject) => {
      const entry = { task, resolve, reject };
      if (priority === 'high') {
        this.highQueue.push(entry);
      } else {
        this.normalQueue.push(entry);
      }
      this.runNextTask();
    });
  }

  runNextTask() {
    if (this.runningTasks >= this.concurrency) return;

    // drain high priority queue first
    const queue = this.highQueue.length > 0 ? this.highQueue : this.normalQueue;
    if (queue.length === 0) return;

    const { task, resolve, reject } = queue.shift();
    this.runningTasks++;

    new Promise(r => r(task()))
      .then(resolve)
      .catch(reject)
      .finally(() => {
        this.runningTasks--;
        this.runNextTask();
      });
  }
}

// Usage
scheduler.addTask(() => processOrder(plusOrder), 'high');
scheduler.addTask(() => processOrder(regularOrder), 'normal');
```

**Approach B — Min-heap (general, O(log n), supports N priority levels):**

```js
// Replace both queues with a min-heap sorted by numeric priority
// addTask(task, priority = 10) — lower number = higher urgency (1 = critical)
// runNextTask() calls heap.extractMin() instead of array.shift()

// Use when:
// - More than 2 priority levels (e.g., critical / high / normal / low / background)
// - Priority values are dynamic or caller-specified
```

**Trade-off table:**

| | Two-queue | Min-heap |
|---|---|---|
| Enqueue | O(1) | O(log n) |
| Dequeue | O(1) | O(log n) |
| Priority levels | 2 (fixed) | Arbitrary |
| Starvation prevention | Manual | Must implement separately |
| Implementation complexity | Low | Moderate |
| Use when | Two tiers, high throughput | Dynamic priorities or N tiers |

For most production systems (Flipkart Plus vs. regular, premium vs. free), two or three priority levels is sufficient. Use the simpler two-queue approach. Add a heap only if requirements demand it.

## Follow-up

**Q:** "What is priority inversion and could it happen here?"

**A:** Priority inversion is when a high-priority task is blocked waiting on a resource held by a low-priority task. In this single-threaded scheduler, a high-priority task cannot be blocked by a running low-priority task — the running task holds the slot, not a mutex. High-priority tasks wait only until a slot frees, regardless of what task is in that slot. True priority inversion is a multi-threaded concern.

**Q:** "How do you prevent starvation of normal-priority tasks when high-priority tasks arrive continuously?"

**A:** Implement aging: track the enqueue timestamp for each task. In `runNextTask()`, promote tasks that have waited longer than a threshold (e.g., 5 seconds) to high priority. Alternatively, use a fair weighted scheduler: for every N high-priority tasks executed, execute 1 normal-priority task unconditionally.
