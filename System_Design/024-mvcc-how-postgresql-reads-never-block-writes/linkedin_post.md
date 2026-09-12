# MVCC — How PostgreSQL Reads Never Block Writes — LinkedIn Post

## Post Text (copy-paste ready)

Reads never block writes, writes never block reads in PostgreSQL — here's the row-versioning trick that makes it possible.

- Every row has hidden `xmin`/`xmax` columns: xmin = txn that created the version, xmax = txn that superseded it (0 = still live)
- Writes never edit in place — they create a new row version; old readers keep seeing their snapshot untouched
- The only real blocking is write-write on the *same* row — reads vs writes and reads vs reads never queue up
- MVCC creates "dead" row versions → table bloat → AUTOVACUUM must clean them, or a 32-bit XID counter wraps every ~49 days at 1,000 TPS and can force PostgreSQL into read-only mode
- MVCC alone doesn't stop write skew — the classic doctor on-call bug (2 doctors both check "is someone else on-call?", both go off-call, invariant broken) needs SERIALIZABLE isolation to catch the read-write dependency cycle

Swipe → to see: the xmin/xmax versioning diagram, the isolation-level decision table, and how Ticket Booking handles 50K concurrent reads during a flash sale without blocking seat-deduction writes.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
MVCC is why PostgreSQL reads never wait on writes. xmin/xmax versioning explained — plus why write skew still needs SERIALIZABLE.

### Variant B — Long (400–600 chars)
Ever wondered how PostgreSQL serves 10,000 concurrent reads while 1,000 writes/sec hit the same tables — with zero blocking? MVCC. Every write creates a new row version (tracked via xmin/xmax) instead of editing in place, so readers keep seeing their own consistent snapshot. The catch: dead versions cause table bloat, a 32-bit XID counter can wrap in ~49 days under heavy load, and MVCC alone won't stop write skew (the doctor on-call bug) — that needs SERIALIZABLE. Full breakdown + isolation-level cheat sheet inside.

---

## Best Time to Post
Tuesday–Thursday, 8–10 AM local time (peak professional scrolling before/at work start).

## Engagement Hook
Ask: "Have you ever hit an XID wraparound scare or a table-bloat incident in production? Drop your war story below."
