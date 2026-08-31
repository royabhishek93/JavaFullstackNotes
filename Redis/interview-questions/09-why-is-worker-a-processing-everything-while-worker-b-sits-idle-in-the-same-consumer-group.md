# Why is worker A processing everything while worker B sits idle in the same consumer group?

**Type:** Scenario-Based
**Topic:** Redis Streams — Consumer Groups & Load Distribution
**Level:** Senior Interview (10+ YOE)

## Direct Answer
Most commonly, worker B either crashed/never connected, is blocked on a slow downstream call, or both workers are reading with a small `COUNT`/short `BLOCK` window and worker A simply wins the race on every poll. Check `XINFO CONSUMERS` and `XPENDING` first — they show exactly who is (and isn't) picking up work.

## Easy Explanation
Two cashiers share one queue of customers. If one cashier is fast and always free the moment a customer arrives, they'll naturally serve more people — that's not unfair, that's how a shared queue works. But if the second cashier has *stopped showing up* (crashed) or is stuck on a really slow customer (a slow partner API call), the queue keeps directing everyone to the first cashier, and it looks like "imbalance" when it's really "one worker isn't functioning."

## Diagram
```
Consumer Group: order-verifiers        Redis Stream: order-events
                                         [e1] [e2] [e3] [e4] [e5] [e6]

  worker-a  <---- XREADGROUP ---- constantly polling, fast partner API
  worker-b  <---- XREADGROUP ---- (crashed / stuck / never started)

XINFO CONSUMERS order-events order-verifiers
+-----------+---------+-------------+
| name      | pending | idle (ms)   |
+-----------+---------+-------------+
| worker-a  |   1     |     40      |
| worker-b  |   7      |  620000    |   <- huge idle time = dead or stuck
+-----------+---------+-------------+

Fix: XAUTOCLAIM order-events order-verifiers worker-a 60000 0-0 COUNT 20
     (moves worker-b's stuck messages to a healthy worker after idle > 60s)
```

## Production Example
A notification pipeline has two pods reading from `order-verifiers`. One pod is stuck because its outbound HTTP client has no timeout and a downstream SMS provider is hanging:

```bash
XINFO CONSUMERS order-events order-verifiers
# worker-b shows idle-time of 10+ minutes -> clearly stuck, not "slow but healthy"

XAUTOCLAIM order-events order-verifiers worker-a 60000 0-0 COUNT 20
# reassigns worker-b's stuck messages to worker-a
```

The real fix is adding a request timeout to the SMS call so `worker-b` fails fast and reconnects, instead of relying on `XAUTOCLAIM` as a permanent workaround.

## Why Interviewers Ask This
It tests operational instincts: does the candidate reach for monitoring commands (`XINFO`, `XPENDING`) before guessing, and do they treat imbalance as a symptom to investigate rather than something to patch over with more `XAUTOCLAIM` calls?
