# Redis Lua Scripting: Atomic Multi-Step Operations — LinkedIn Post

## Post Text (copy-paste ready)

Your GET-then-DEL lock release code has a 2ms window where it can delete someone ELSE's lock. Here's the fix.

- Redis guarantees each individual command is atomic, but NOTHING about what happens between two separate commands from your application code
- Classic bug: GET a lock's owner, compare in app memory, DEL it — in the gap, the lock expires and a different client legitimately acquires it, and your DEL just destroyed THEIR lock
- Fix: push the whole check-then-act sequence into a single Lua script run with EVAL — Redis's single-threaded execution guarantees zero interleaving from any other client
- Production pattern: `SCRIPT LOAD` once (returns a SHA1 hash), then `EVALSHA` on every call — at 10K calls/sec, that's ~0.4MB/sec of overhead instead of ~2MB/sec of resent script text
- The trap: a Lua script blocks Redis's ENTIRE single thread for its full execution — never loop over an unbounded `KEYS *` pattern inside a script, or you'll freeze production for seconds

Swipe → to see the canonical 3-line safe-unlock script and the exact NOSCRIPT failure mode you must handle.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
GET-then-DEL for releasing a Redis lock has a race window that can delete someone else's lock. Here's the atomic fix 👇

### Variant B — Long (400–600 chars)
Redis guarantees individual commands are atomic, but a GET followed by a DEL from application code has a race window in between — long enough for a lock to expire and get legitimately re-acquired by another client before your DEL fires, silently destroying their lock. The fix is a Lua script run with EVAL: the entire check-then-act sequence executes as one atomic, indivisible unit server-side. In production, cache the script with SCRIPT LOAD and call EVALSHA to avoid resending text — but never loop over an unbounded key pattern inside a script, since it blocks the entire single-threaded Redis instance for its duration.

---

## Best Time to Post
Tuesday, 9:00–10:00 AM IST (Redis/infrastructure deep-dives perform well early in the week)

## Engagement Hook
"Has a long-running Lua script or an unbounded KEYS command ever frozen your production Redis instance?"
