# Why does setting XAUTOCLAIM idle time to 5 seconds cause orders to be processed twice?

**Type:** Trap Question
**Topic:** Redis Streams — Consumer Groups & Recovery
**Level:** Senior/Staff Interview (10–15+ YOE) — common gotcha

## Direct Answer
Because 5 seconds is shorter than the time a perfectly healthy worker sometimes needs to finish a real request (e.g., a slow downstream call). `XAUTOCLAIM` doesn't know the difference between "dead worker" and "busy worker" — it only measures idle time. If the threshold is too aggressive, a still-working worker gets treated as dead and its message is handed to someone else, so both end up processing it.

## Easy Explanation
Imagine a manager who reassigns any task if the employee hasn't reported back within 5 seconds — but the task sometimes genuinely takes 8 seconds to finish properly. The manager isn't rescuing failed work; they're interrupting people who were about to finish, and now two people do the same job. The fix isn't removing the safety net — it's setting the timer to something longer than the slowest *normal* case.

## Diagram
```
Idle threshold = 5s (too aggressive)

t=0s   worker-a starts processing message 900-0 (calls a partner API)
t=5s   XAUTOCLAIM sweep runs -> sees idle=5s -> claims 900-0 for worker-b
t=6s   worker-b starts processing SAME message 900-0
t=7s   worker-a's original partner call finally returns -> worker-a ALSO finishes and writes result
t=7.2s worker-b also finishes and writes result
                              |
                              v
                  message 900-0 processed TWICE, concurrently

Correct threshold = p99 processing time + safety margin, e.g. 60s
t=0s   worker-a starts
t=7s   worker-a finishes normally, calls XACK      <- no claim ever needed, no duplicate
```

## Production Example
A retry-happy team set `XAUTOCLAIM ... MIN-IDLE-TIME 5000` on an order-verification stream. The partner verification API had a p99 latency of 8 seconds under load. Result: during peak traffic, roughly 15% of orders were verified twice, briefly double-reserving inventory until a reconciliation job caught it.

```bash
# BEFORE (too aggressive)
XAUTOCLAIM order-events order-verifiers worker-b 5000 0-0 COUNT 20

# AFTER (measured from real p99 latency + margin)
XAUTOCLAIM order-events order-verifiers worker-b 60000 0-0 COUNT 20
```

The permanent fix combined a safer threshold *and* an idempotency key on the order-verification write, so even a rare duplicate claim would no longer double-reserve inventory.

## Why Interviewers Ask This
It's a very realistic production incident, and it tests whether a candidate treats `XAUTOCLAIM` idle time as a tuning parameter that must be derived from real latency data, not a value copied from a tutorial.
