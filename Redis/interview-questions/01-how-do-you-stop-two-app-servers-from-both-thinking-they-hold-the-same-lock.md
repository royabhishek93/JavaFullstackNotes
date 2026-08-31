# How do you stop two app servers from both thinking they hold the same lock?

**Type:** Scenario-Based
**Topic:** Redis Core Data Types — Locking & Atomicity
**Level:** Senior Interview (8–12+ YOE)

## Direct Answer
Use `SET key value NX PX <ttl>` as a single atomic command. `NX` means "only set if the key doesn't already exist," so if two servers race to acquire the lock at the same instant, Redis guarantees only one `SET` succeeds — the other gets a nil response and knows it failed to acquire the lock.

## Easy Explanation
Think of a lock like a single bathroom key hanging on a hook. `SET ... NX` is like a rule: "you may only take the key if it's still on the hook." If two people grab for it at the exact same moment, only one of them actually gets it — the other's hand closes on empty air and they know to wait. Without `NX`, both people could "successfully" walk away holding a key, which defeats the whole point of a lock.

## Diagram
```
Server A                         Redis                         Server B
   |--- SET lock:order-1 A NX PX 5000 ---> |
   |                                        | key doesn't exist -> SET succeeds
   |<----------------- OK ----------------- |
   |                                        |<--- SET lock:order-1 B NX PX 5000 ---
   |                                        | key ALREADY exists -> SET fails
   |                                        |----------------- nil ---------------->|
   |                                        |
[ Server A proceeds, holds the lock ]     [ Server B backs off / retries later ]
```

## Production Example
Two instances of a scheduled job (running on different pods for high availability) must not both process the same nightly billing batch:

```bash
SET lock:billing-batch pod-7f3a NX PX 30000
# only one pod's SET returns OK; the other retries or exits immediately
```

If the winning pod finishes early, it should delete the lock (ideally comparing the value first, see the advanced version of this question) rather than waiting for the full 30-second TTL to expire.

## Why Interviewers Ask This
It's the most common introductory distributed-locking question. It checks whether the candidate reaches for an *atomic* single command instead of a "check if exists, then set" sequence done as two separate calls — which reintroduces the exact race condition the lock was meant to prevent.
