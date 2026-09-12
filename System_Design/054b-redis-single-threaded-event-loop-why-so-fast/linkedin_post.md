# Redis Single-Threaded Event Loop — Why So Fast — LinkedIn Post

## Post Text (copy-paste ready)

Redis is single-threaded. It still does 100,000-200,000 ops/sec on ONE core. Adding more threads would make it slower — here's the math.

- A MySQL-backed request spends 99.98% of its 10ms round-trip SLEEPING on disk and network — that's why Java needs 500-thread pools. Redis has no disk: a GET is a 100-nanosecond hash lookup, so there's nothing to sleep on
- The real trick is epoll — one thread registers all 10,000 sockets and calls epoll_wait(), which blocks until ANY socket has data, then hands back the ready list in one wake-up. No thread-per-connection, no 10GB of RAM burned on thread stacks
- The trap almost everyone falls into: assuming more threads = faster. A mutex lock costs ~50ns, a Redis SET costs ~100ns — multi-threaded execution is 150ns/op (50% SLOWER) because the lock overhead exceeds the work itself. Amdahl's Law: 0% of command execution is parallelizable
- The INCR race condition proof: two threads both read page_views=99 before either writes back → you lose an increment, landing on 100 instead of 101. Single-threaded Redis can't have this bug — that's WHY INCR/SETNX/ZADD are atomic by default, no MULTI/EXEC needed
- Redis 6 added I/O threads (io-threads 4) — but ONLY for reading/writing raw socket bytes. Command execution is still 100% single-threaded. At 1M ops/sec, socket I/O was consuming 30% of the thread before this fix

Swipe → to see the epoll flow, the mutex-overhead math, and the exact interview one-liner.

Save this. You'll need it the next time someone asks "isn't single-threaded a bottleneck?"

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Redis: 1 thread, 100K-200K ops/sec, zero locks. Here's why adding threads would make it SLOWER, not faster 👇

### Variant B — Long (400–600 chars)
Redis is single-threaded and still handles 100M+ requests a day. The reason isn't magic — it's that RAM access takes 100 nanoseconds while disk takes 5-10 milliseconds, so there's nothing to sleep on, unlike a MySQL-backed service where threads spend 99.98% of their time waiting. One thread + epoll watches 10,000 sockets at once. And multi-threading would actually hurt: a mutex lock (50ns) costs half as much as the operation itself (100ns) — that's why INCR, SETNX, and ZADD stay atomic with zero locks. Redis 6's I/O threads only touch socket bytes, never the data.

---

## Best Time to Post
Tuesday, 9:00–10:00 AM IST (systems-internals deep dives perform best early week when engineers are planning interview prep)

## Engagement Hook
"Have you ever been asked 'if Redis is single-threaded, how is it so fast?' in an interview — what was your answer?"
