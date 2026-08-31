# Why does SET NX silently do nothing when you expect it to overwrite a stale lock?

**Type:** Trap Question
**Topic:** Redis Core Data Types — Locking Semantics
**Level:** Mid–Senior Interview (5–10+ YOE) — common gotcha

## Direct Answer
Because `NX` means "only set if the key does **not** exist" — by design, it will never overwrite an existing value, even if that value is old, stale, or left behind by a crashed process. If you forgot to set an expiry (`PX`/`EX`) when the lock was created, the key can live forever, and every future `SET ... NX` attempt will keep failing silently (returning nil) since the key technically still "exists."

## Easy Explanation
`NX` is a promise, not a bug: "don't touch it if it's already there." If a process crashed without ever cleaning up its lock, and that lock has no expiry, then as far as Redis is concerned the lock is still validly "held" — forever. Nobody told Redis the holder is gone, so it keeps honoring the do-not-overwrite rule. The fix isn't to override `NX`'s behavior — it's to make sure every lock is created *with* an expiry in the first place, so a crashed holder's lock eventually times out on its own.

## Diagram
```
Server A: SET lock:report-gen ownerA NX     <- no PX/EX given!  -> OK, lock created, NEVER expires
Server A: process CRASHES before ever deleting the lock

... hours later ...

Server B: SET lock:report-gen ownerB NX     -> key STILL exists -> fails, returns nil
Server C: SET lock:report-gen ownerC NX     -> key STILL exists -> fails, returns nil
                                                (this can go on forever — no one can ever proceed)

Correct pattern from the start:
  SET lock:report-gen ownerA NX PX 30000    <- always pair NX with an expiry
  (if Server A crashes, the lock self-destructs after 30s, unblocking everyone else)
```

## Production Example
A batch-report job used `SET lock:report-gen <owner> NX` without a TTL "because we'll clean it up in the `finally` block." A deploy killed the pod mid-run, the `finally` block never ran, and the report generation job silently stopped running entirely — every subsequent attempt from any pod failed the `NX` check, with no expiry to ever release it. The fix was adding `PX 30000` (and, for long-running jobs, a periodic TTL "heartbeat" refresh) so a crash could never permanently strand the lock.

```bash
# BROKEN — no expiry, a crash strands the lock forever
SET lock:report-gen ownerA NX

# CORRECT — self-healing after a crash
SET lock:report-gen ownerA NX PX 30000
```

## Why Interviewers Ask This
It's a very common real incident: engineers correctly reach for `NX` to prevent double-acquisition, but forget the expiry, turning a temporary outage (one crashed pod) into a permanent one (the lock never releases). This question checks whether the candidate treats "atomic acquire" and "guaranteed eventual release" as two separate concerns that must both be handled.
