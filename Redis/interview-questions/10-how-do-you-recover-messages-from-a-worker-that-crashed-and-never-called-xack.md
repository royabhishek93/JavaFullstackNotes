# How do you recover messages from a worker that crashed and never called XACK?

**Type:** Advanced Scenario-Based
**Topic:** Redis Streams — Consumer Groups & Recovery
**Level:** Staff Interview (12–15+ YOE)

## Direct Answer
Use `XAUTOCLAIM` (or the older `XPENDING` + `XCLAIM` combo) to transfer messages that have been idle longer than your chosen threshold to a healthy consumer. Run it on a schedule (a small recovery job), and size the idle threshold above your slowest realistic processing time — not an arbitrary "safe-looking" number.

## Easy Explanation
When a worker dies holding a task, that task doesn't just vanish — it sits in a "still checked out" list (the PEL) with a timer on it. `XAUTOCLAIM` is like a supervisor who periodically walks the floor and says, "Any task checked out for longer than my patience threshold, hand it to someone else." The key skill is setting that patience threshold correctly — too short, and you interrupt workers who are simply doing a slow but legitimate task.

## Diagram
```
Timeline for message 1050-0:

t=0s    worker-a XREADGROUP's 1050-0  -> PEL: {1050-0, owner=worker-a, idle=0}
t=5s    worker-a CRASHES (process killed, no XACK ever sent)
t=5s..  PEL still shows {1050-0, owner=worker-a, idle=growing...}
t=90s   recovery job runs:
        XAUTOCLAIM stream group worker-b MIN-IDLE-TIME=60000 0-0 COUNT 50
                                          |
                                          v
        PEL updated: {1050-0, owner=worker-b, idle=0}
t=91s   worker-b processes 1050-0 and calls XACK -> PEL entry removed
```

## Production Example
A background image-resizing service runs a recovery sweep every 30 seconds:

```java
@Scheduled(fixedDelay = 30_000)
public void recoverStuckMessages() {
    redisTemplate.opsForStream().autoClaim(
        "image-resize-workers",
        "recovery-worker",
        Duration.ofSeconds(60),   // idle threshold, above p99 resize time
        "0-0"
    ).forEach(this::process);
}
```

The 60-second threshold was chosen because the slowest legitimate resize (a very large image) takes about 20 seconds — the margin protects healthy-but-slow workers from having their work stolen mid-task.

## Why Interviewers Ask This
It reveals whether the candidate understands that "recovery" and "false-positive interruption" are two sides of the same knob, and whether they've actually operated a scheduled reclaim job rather than only reading about `XAUTOCLAIM` in documentation.
