# Why does a cached unread-message count go out of sync with the real database?

**Type:** Trap Question
**Topic:** Redis Architecture — Caching Computed Values
**Level:** Senior Interview (8–12+ YOE) — common gotcha

## Direct Answer
Because the cached number (e.g., `unread:user:42 = 12`) is a **computed value that must be actively kept in sync** — it doesn't automatically update itself when the underlying messages table changes. If a message gets marked read directly in the database (or through a code path that forgot to also update Redis), the cache silently drifts from reality and nobody notices until a user complains their unread badge is wrong.

## Easy Explanation
A cached count is like writing "you have 12 unread letters" on a sticky note instead of counting your mailbox every time. That's fast and convenient — but if a letter gets read (or a new one arrives) through some path that forgets to update the sticky note, the note becomes a lie. The sticky note isn't the source of truth; it's a shortcut that only stays correct if *every* place that changes the real data remembers to also update it.

## Diagram
```
Source of truth: messages table (Postgres)
Convenience cache: unread:user:42 (Redis)

Path 1 (correct):
  new message arrives -> INSERT INTO messages -> INCR unread:user:42
  user reads message  -> UPDATE messages SET read=true -> DECR unread:user:42
  (both paths keep the cache and the database in sync)

Path 2 (the bug):
  admin tool bulk-marks messages as read directly in the database
  (forgets to touch Redis at all)
                          |
                          v
  unread:user:42 in Redis STILL says "12"
  but the real database now says "0"
                          |
                          v
  user's app shows a stale "12 unread" badge that never matches reality
```

## Production Example
A support team built an internal admin panel that marks all of a user's messages as read directly via SQL, for handling complaints — but it never called the application's normal "mark as read" service method, so it silently bypassed the `DECR unread:user:42` step. The fix was either (a) routing every read-path through one service that always updates both stores, or (b) treating the cached count as *advisory* and periodically reconciling it with a real `COUNT(*) WHERE read=false` query, so drift self-heals.

```java
// Correct: single method is the only way to mark messages read
@Transactional
public void markRead(long userId, long messageId) {
    messageRepo.markRead(messageId);
    redisTemplate.opsForValue().decrement("unread:user:" + userId);
}
```

## Why Interviewers Ask This
It tests whether a candidate recognizes that caching a *computed* value introduces a new responsibility — keeping it consistent with every write path — and that shortcuts like direct database edits or forgotten code paths are the real-world cause of "the cache is lying" bugs.
