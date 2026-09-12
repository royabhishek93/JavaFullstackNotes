# Hanging Task and AbortController Limitation (Senior Trap)
> **Topic:** Task Scheduler | **Level:** Senior Trap | **Frequency:** Low

## The Setup

A task that calls a service that is down will wait indefinitely. It holds a slot permanently. With `concurrency=5` and 5 hanging tasks, the scheduler is deadlocked — no new tasks ever start. The correct solution composes a timeout wrapper at the call site rather than building timeout logic into the scheduler. A follow-up trap: aborting the Promise does not necessarily abort the underlying network request.

## The Question

"What happens if a task hangs forever and never resolves? How do you fix it? Why shouldn't timeout logic live inside TaskScheduler itself? And if you use AbortController to cancel the fetch, does that actually stop the network request?"

## Diagram

```
DEADLOCK — 5 hanging tasks on concurrency=5:
=============================================

  T1, T2, T3, T4, T5: all call fetch('/slow-service') → service is DOWN
  All 5 slots occupied
  T6, T7, T8 ... in queue → WAIT FOREVER
  runningTasks = 5 = concurrency → runNextTask() always returns early
  Scheduler is deadlocked

TIMEOUT COMPOSITION — fixes the deadlock:
==========================================

  withTimeout(task, 5000):
    returns () => Promise.race([
      task(),                    ← the real task
      rejectAfter(5000ms)        ← timeout race
    ])

  T2 hangs → after 5000ms, Promise.race rejects with TimeoutError
  .catch(reject) → T2's caller gets TimeoutError
  .finally() → runningTasks-- → slot freed → T6 starts

  Scheduler unblocks automatically.

ABORTCONTROLLER CAVEAT:
========================

  fetch call: fetch(url, { signal: controller.signal })
  controller.abort() called after timeout:
    → Promise rejects with AbortError ← good
    → slot freed ← good
    → BUT: OS TCP connection may still be open
    → server still processing the request
    → "abort" only rejects the JS Promise handle, not the server-side work
```

## Model Answer (15 YOE)

```js
function withTimeout(task, ms) {
  return () => Promise.race([
    task(),
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error(`Task timed out after ${ms}ms`)), ms)
    )
  ]);
}

// Usage — compose at the call site
scheduler.addTask(withTimeout(() => fetch('/slow-service'), 5000));
```

Why timeout logic does NOT belong inside `TaskScheduler`:

Single responsibility. The scheduler manages concurrency — it counts slots and drains a queue. Timeout policy is a per-task concern: different tasks may have wildly different acceptable latencies (a health check: 500ms; a bulk export: 5 minutes). Building timeout into the scheduler forces a single policy onto all tasks. Composing at the call site is flexible, testable, and leaves the scheduler minimal.

The AbortController limitation:

```js
function withTimeout(task, ms) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), ms);

  return () => task(controller.signal)
    .finally(() => clearTimeout(timeoutId));
}

// Task uses the signal
const myTask = (signal) => fetch('/slow-service', { signal });
```

Calling `controller.abort()`:
- Rejects the fetch Promise with `AbortError` — the slot is freed
- Cleans up the browser/Node's fetch plumbing
- Does NOT stop the server from processing the request (the server has already received it)
- Does NOT close the OS TCP connection immediately in all environments

For true cancellation end-to-end, the server must also support a cancellation mechanism (e.g., checking the connection status or a cancellation token). Client-side `AbortController` is a best-effort tool, not a guaranteed hard stop.

**Cleanup — clearing the timeout on success:**

Without `clearTimeout(timeoutId)`, the timeout fires after a successful fast task, triggering `controller.abort()` on an already-settled Promise (harmless but wasteful). Always clear the timeout in `.finally()`.

## Why It's a Trap

Candidates think `AbortController` fully cancels the operation. It cancels the Promise — the JS handle — but the I/O may continue. The distinction matters for billing (API calls that were "cancelled" but still processed), for idempotency (retrying an "aborted" request that may have already committed), and for connection pool behaviour (the server-side connection is held until the OS closes it).

## What NOT to Say

- "AbortController stops the server from processing the request" — it does not.
- "The scheduler should have a global timeout" — violates single responsibility.
- "A hanging task will eventually resolve once the network stack times out" — true but default OS timeouts can be minutes, not seconds.

## Follow-up

**Q:** "What is the difference between a timeout and a deadline?"

**A:** A timeout is relative — "reject after N ms from now." A deadline is absolute — "reject after a specific wall-clock time." For distributed systems, deadlines are more useful: a request entering a pipeline carries a deadline header (`X-Request-Deadline: <timestamp>`), and each service checks if it has enough budget remaining before starting work. This prevents a timed-out upstream from receiving results that are now useless.
