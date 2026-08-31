# How do you build a safe distributed lock that survives a crashed lock holder?

**Type:** Advanced Scenario-Based
**Topic:** Redis Core Data Types — Locking & Atomicity
**Level:** Staff Interview (12–15+ YOE)

## Direct Answer
Combine `SET key uniqueOwnerToken NX PX <ttl>` (atomic acquire with auto-expiry) with a **safe release**: only delete the key if its value still matches your own unique token, checked and deleted atomically via a Lua script (`EVAL`). This prevents both "the lock leaks forever because the holder crashed" and "a server accidentally deletes someone else's lock."

## Easy Explanation
An unsafe lock never expires — if the holder crashes while holding it, everyone else is locked out forever. So we add an automatic timer (`PX`) that releases the key on its own. But that raises a new danger: if Server A's task runs *longer* than the timer, the lock auto-expires, Server B grabs it, and then Server A finishes and blindly deletes "the lock" — actually deleting *Server B's* lock. The fix is: each server writes its own unique "name tag" as the value, and only deletes the lock if the name tag still matches its own — checked and deleted as one atomic step.

## Diagram
```
Server A                                        Redis
  SET lock:job-9 "A-token-123" NX PX 5000  --->  OK (A now holds lock, auto-expires in 5s)
  ...job takes longer than expected (7s)...
  (at 5s) lock:job-9 auto-EXPIRES              --->  key removed by Redis itself

Server B
  SET lock:job-9 "B-token-456" NX PX 5000  --->  OK (B now holds lock)

Server A finishes late, tries to release:
  UNSAFE:  DEL lock:job-9                  --->  deletes B's lock! (bug)
  SAFE:    EVAL "if redis.call('get', KEYS[1]) == ARGV[1]
                  then return redis.call('del', KEYS[1])
                  else return 0 end"
                 1 lock:job-9 "A-token-123" --->  0 (no-op — value doesn't match A anymore)
```

## Production Example
```java
String token = UUID.randomUUID().toString();
Boolean acquired = redisTemplate.opsForValue()
    .setIfAbsent("lock:billing-batch", token, Duration.ofSeconds(30));

if (Boolean.TRUE.equals(acquired)) {
    try {
        runBillingBatch();
    } finally {
        // release only if we still own it — Lua script makes check+delete atomic
        redisTemplate.execute(RELEASE_LOCK_SCRIPT,
            List.of("lock:billing-batch"), token);
    }
}
```

This pattern (often called a "fencing token" approach) is the foundation of libraries like Redisson's `RLock`, which add extra features such as auto-renewing the TTL ("watchdog") while the task is still running.

## Why Interviewers Ask This
It probes whether a candidate understands that a naive lock (`SET NX` + plain `DEL`) has two distinct failure modes — leaking forever, and deleting someone else's lock — and can fix both without introducing a new race condition.
