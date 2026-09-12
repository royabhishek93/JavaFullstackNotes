# Redlock — Distributed Locking with Redis — LinkedIn Post

## Post Text (copy-paste ready)

Your JVM pauses for 12 seconds. Your lock expires. Another client grabs it. You wake up still thinking you own it.

- A single Redis SETNX lock is a single point of failure — if that node dies, the lock either vanishes or gets stuck.
- Redlock fixes this by acquiring a lock across 5 independent Redis nodes — you only need a majority (3 of 5) to hold a valid lock.
- Even Redlock isn't bulletproof: a GC pause longer than the TTL means Client A resumes still believing it holds the lock, while Client B already acquired it.
- The real fix is a fencing token — a monotonically increasing number (e.g., token 33) that gets rejected by storage once a newer token (34) has already been seen.
- Not every problem needs Redlock: PostgreSQL advisory lock for single-DB mutual exclusion, ShedLock for cron jobs across replicas, Redlock for cross-service locking, ZooKeeper/etcd when you need fencing and absolute correctness.

Real example: a Ticket Booking system uses Redlock on `lock:event:{id}:seat:{seatId}` with TTL=10 minutes so two booking pods can never sell the same seat during checkout.

Swipe → to see: the GC-pause failure scenario, the Redlock majority algorithm, and the decision tree for picking the right lock.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Redlock in 150 chars: majority lock across 5 Redis nodes beats single SETNX — but only a fencing token stops a GC-paused client from double-writing.

### Variant B — Long (400–600 chars)
A single Redis lock (SETNX) is one node crash away from disaster — the lock either gets stuck forever or vanishes and two clients run the "exclusive" section at once. Redlock solves this by requiring a majority (3 of 5 independent Redis nodes) to grant the lock, so no single failure breaks the guarantee. But Redlock alone can't stop a GC-paused client from resuming after its lock expired and someone else already took over — that needs a fencing token, a monotonically increasing number the storage layer uses to reject stale writes. Know when to reach for PostgreSQL advisory locks, ShedLock, Redlock, or ZooKeeper — that decision is what separates a senior candidate from the rest in a system design interview.

---

## Best Time to Post
Tuesday–Thursday, 8:00–10:00 AM local time (peak professional scrolling before/after commute).

## Engagement Hook
Ask in comments: "Have you ever had a distributed lock silently fail in production? What caused it — a GC pause, a network partition, or something else?"
