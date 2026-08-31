# Redis — Why Single-Threaded Handles 100 Million Requests
### The Event Loop, epoll, and In-Memory Speed Explained from First Principles

---

## PART 1 — THE STUDENT CONVERSATION

**How can a single-threaded process handle 100 million requests? Doesn't single-threaded mean it can only do one thing at a time?**

Yes — but the key insight is: **for Redis, "one thing at a time" is fast enough because each thing takes 100 nanoseconds.**

The confusion comes from comparing Redis to a Java Spring Boot service backed by MySQL. Those services are slow not because of CPU but because they spend 99.98% of their time sleeping — waiting for disk reads and network round-trips. You need hundreds of threads just to keep the CPU busy while hundreds of threads sleep.

Redis has no disk. Everything is in RAM. A GET command is a hash table lookup — 100 nanoseconds. There's nothing to sleep on.

The real question is: **how does one thread manage thousands of concurrent connections without sleeping on any of them?**

The answer is **epoll** — Linux kernel I/O multiplexing. One thread tells the OS: "watch all 10,000 sockets, wake me when any of them have data." The OS wakes the thread, it processes every ready connection, and goes back to waiting. No sleeping per connection. No thread-per-connection. One tight loop, pure speed.

---

## PART 2 — WHERE THE TIME ACTUALLY GOES

### The Java + MySQL comparison (why threads exist)

```
One request to fetch a user from MySQL:
────────────────────────────────────────────────────────────────────

  Client sends HTTP request
  │
  ▼
  Java thread picks it up                 ←  1 microsecond (CPU work)
  │
  ▼
  Thread sends SQL to MySQL over network  ←  1 millisecond (network)
  │
  ▼
  MySQL reads row from disk               ←  5-10 milliseconds (disk I/O)
  │
  ▼
  MySQL sends result back over network    ←  1 millisecond (network)
  │
  ▼
  Java thread formats HTTP response       ←  1 microsecond (CPU work)

Total: ~10 milliseconds
CPU actually working: ~0.002 ms  (0.02% of the time)
Thread is SLEEPING: 99.98% of the time, waiting for disk and network.

That's why Java uses thread pools — while Thread A sleeps waiting for
MySQL, Thread B handles another request. You need 500 threads to handle
500 concurrent "sleeping" requests.
```

### The Redis comparison (no disk, no sleep)

```
One request to fetch a key from Redis:
────────────────────────────────────────────────────────────────────

  Client sends GET user:123
  │
  ▼
  Redis receives bytes from socket        ←  network (same as MySQL)
  │
  ▼
  Redis looks up key in hash table        ←  100 NANOSECONDS (RAM!)
  │
  ▼
  Redis writes bytes back to socket       ←  network (same as MySQL)

Total: ~0.1 milliseconds
The actual "work" (hash table lookup): 100 nanoseconds.

100 nanoseconds = 0.0001 milliseconds = 100,000x faster than disk.

The bottleneck is the network round-trip, not the computation.
Adding more CPU threads doesn't speed up network round-trips.
```

---

## PART 3 — HOW epoll WORKS (THE SECRET WEAPON)

### Blocking I/O — what Java threads do by default

```
Blocking I/O per connection:
────────────────────────────────────────────────────────────────────

  Thread: "read from socket 1"
  Socket 1 has no data yet...
  Thread SLEEPS  ← OS parks it, doing nothing
  ...
  Socket 1 data arrives
  OS wakes thread  ← context switch (expensive: ~1-5 microseconds)
  Thread processes request
  Thread SLEEPS again waiting for next request

  To handle 10,000 connections:
  → Need 10,000 threads
  → 10,000 × 1MB stack = 10GB RAM just for thread stacks
  → Constant context switching overhead
  → OS scheduler managing 10,000 threads = expensive
```

### epoll — one thread, 10,000 connections

```
epoll I/O multiplexing:
────────────────────────────────────────────────────────────────────

  Thread registers ALL sockets with epoll:
  epoll_ctl(epfd, ADD, socket_1)
  epoll_ctl(epfd, ADD, socket_2)
  ...
  epoll_ctl(epfd, ADD, socket_10000)

  Thread calls:
  ready_list = epoll_wait(epfd)
  ← OS blocks HERE until ANY socket has data

  OS: "socket 42 has data, socket 891 has data, socket 3301 has data"
  OS returns immediately with the list of ready sockets.

  Thread:
  ┌─────────────────────────────────────────────────────────────────┐
  │  for each socket in ready_list:                                  │
  │    bytes = read(socket)          ← data already in kernel buffer │
  │    command = parse(bytes)        ← "GET user:123"               │
  │    result = execute(command)     ← hash table lookup, 100ns     │
  │    write(socket, result)         ← put reply in kernel buffer   │
  └─────────────────────────────────────────────────────────────────┘

  Thread calls epoll_wait() again. Repeat forever.

  No context switches between connections.
  No 10,000 threads.
  One thread, zero sleep per connection.
```

### The Redis event loop (actual internal model)

```
Redis main loop:
────────────────────────────────────────────────────────────────────

  while (server_running) {

      // Fire any time-based callbacks (expiry, persistence)
      process_time_events()

      // Wait for I/O (epoll_wait / kqueue on macOS)
      ready_fds = ae_poll(event_loop, timeout)

      // Process every ready file descriptor
      for each fd in ready_fds:
          if fd.type == READABLE:
              read_query_from_client(fd.client)   // read bytes
              process_command(fd.client)           // execute in RAM
          if fd.type == WRITABLE:
              write_reply_to_client(fd.client)     // send bytes back

      // No threads, no locks, no sleeping per connection
  }
```

---

## PART 4 — WHY MULTIPLE THREADS WOULD HURT REDIS

This is the counterintuitive part. Adding threads makes Redis SLOWER for command execution.

```
Problem: shared mutable state
────────────────────────────────────────────────────────────────────

  Redis has one global hash table: { "user:123" → "{name: Alice}" }

  If two threads process commands simultaneously:
  Thread 1: SET user:123 = {name: Bob}
  Thread 2: SET user:123 = {name: Carol}
  ← Which one wins? RACE CONDITION → data corruption

  To prevent this, you need a mutex lock:
  Thread 1: LOCK → SET → UNLOCK
  Thread 2: waiting for lock... waiting... LOCK → SET → UNLOCK

Lock acquisition: ~50 nanoseconds
Actual SET work:  ~100 nanoseconds

You're paying 50% overhead for locking on every operation.
For 100ns operations, mutex overhead is enormous relative to the work.

Single thread math:  100ns work + 0ns locking  = 100ns per op
Multi-thread math:   100ns work + 50ns locking = 150ns per op (50% slower!)

Single-threaded wins because the operations are too fast to benefit
from parallelism. The synchronization cost exceeds the work itself.
```

```
Amdahl's Law applied to Redis:
────────────────────────────────────────────────────────────────────

  Sequential fraction of Redis work (must be single-threaded):
  - Hash table lookup: 100% of a GET
  - Command parsing: 100% sequential
  - Data structure mutation: 100% sequential

  Parallel fraction: 0% of the actual command work.
  (The only parallelizable part is socket I/O — which Redis 6 did add.)

  Adding 8 cores to pure sequential code: zero speedup.
  It just adds lock overhead.
```

---

## PART 5 — THE NUMBERS: HOW 100M REQUESTS ACTUALLY WORKS

```
100 million requests/day:
────────────────────────────────────────────────────────────────────

  100,000,000 ÷ 86,400 seconds = ~1,157 requests/second (average)
  Peak traffic (10x average) = ~11,570 requests/second

  Single Redis instance benchmark (typical):
  ┌────────────────────────────────────────────────────────────┐
  │  GET commands:       ~100,000–200,000 ops/sec (single core) │
  │  SET commands:       ~80,000–150,000 ops/sec               │
  │  Pipeline (batched): ~500,000–1,000,000 ops/sec            │
  └────────────────────────────────────────────────────────────┘

  Peak of 11,570 req/sec is ~10% of a single Redis instance's capacity.
  One Redis node handles your 100M/day traffic with 90% headroom.

  For true 100M req/SECOND:
  Redis Cluster: 6 primary nodes × 100K ops/sec = 600K ops/sec
  Pipeline + cluster: 6 nodes × 500K = 3M ops/sec
  Still possible with horizontal scaling.
```

---

## PART 6 — REDIS 6: WHERE THREADING WAS ADDED

```
What Redis 6 changed (I/O Threading):
────────────────────────────────────────────────────────────────────

  Bottleneck before Redis 6:
  ┌─────────────────────────────────────────────────────────────┐
  │  Single thread: read bytes + parse + execute + write bytes   │
  │                 ↑                              ↑             │
  │            network I/O                   network I/O         │
  │  At 1M ops/sec, socket read/write consumed ~30% of the thread│
  └─────────────────────────────────────────────────────────────┘

  Redis 6 solution: I/O threading
  ┌─────────────────────────────────────────────────────────────┐
  │  I/O Thread 1: read bytes from socket group A               │
  │  I/O Thread 2: read bytes from socket group B               │
  │  I/O Thread 3: read bytes from socket group C               │
  │                         │                                    │
  │  Main Thread:   [parse + EXECUTE + EXECUTE + EXECUTE]        │
  │                 ← still single-threaded, no locks needed →  │
  │                         │                                    │
  │  I/O Thread 1: write bytes to socket group A               │
  │  I/O Thread 2: write bytes to socket group B               │
  └─────────────────────────────────────────────────────────────┘

  Result: saturates 10Gbps+ NICs.
  Command execution: still single-threaded.
  Rule unchanged: only I/O is parallel, not the data structures.
```

---

## PART 7 — THE INTERVIEW CONVERSATION

**Interviewer:** "Redis is single-threaded. How does it handle millions of requests per second? Doesn't single-threaded mean it's slow?"

**You (architect answer):**

> "Single-threaded doesn't mean slow — it means no lock contention, which for Redis is actually faster. Let me explain why.
>
> First, Redis is entirely in-memory. A GET command is a hash table lookup — 100 nanoseconds. Compare that to a MySQL query which waits 5-10 milliseconds for disk reads. Redis operations are 100,000 times faster per operation.
>
> Second, Redis uses Linux epoll for I/O multiplexing. Instead of creating one thread per connection — which would need 10,000 threads for 10,000 connections — Redis has one thread that tells the OS: 'watch all 10,000 sockets and wake me up when any are ready.' The OS returns a list of ready sockets. Redis processes each in ~100 nanoseconds and loops back. No sleeping per connection, no context switches, one tight event loop.
>
> Third, adding threads would hurt, not help. A Redis GET is 100 nanoseconds. A mutex lock costs 50 nanoseconds. Locking overhead would consume 50% of operation time. Single-threaded eliminates all synchronization cost.
>
> In Redis 6, I/O threading was added for socket reads and writes — but command execution remains single-threaded. This lets Redis saturate 10Gbps network cards.
>
> For truly massive scale — like Swiggy handling 10 million orders a day — we'd use Redis Cluster with 6 nodes. Each node handles 100K-200K ops/sec independently. No cross-node locking. Six nodes give you 600K-1.2M ops/sec, which handles any realistic traffic pattern."

---

## QUICK REFERENCE CARD

```
Why Redis is fast — 5 reasons:
────────────────────────────────────────────────────────────────────

1. IN-MEMORY:    RAM = 100ns. Disk = 5-10ms. 100,000x faster.
2. epoll:        One thread watches 10,000 connections simultaneously.
                 OS notifies thread only when data is ready.
3. NO LOCKS:     Single-threaded command execution = zero mutex overhead.
                 Lock cost (50ns) > operation cost (100ns) for multi-thread.
4. SIMPLE OPS:   GET/SET = O(1) hash lookup. No SQL parsing, no joins.
5. TIGHT LOOP:   Event loop processes all ready connections in one pass.
                 No context switches between connections.

Key numbers to memorize:
  RAM access:        100 nanoseconds
  Disk access:       5,000,000 nanoseconds (5ms)
  Mutex lock cost:   ~50 nanoseconds
  Redis GET:         ~100 nanoseconds
  Single instance:   100,000-200,000 ops/second
  With pipelining:   500,000-1,000,000 ops/second
  Redis Cluster (6): ~600,000-1,200,000 ops/second

What changed in Redis 6:
  Before: single thread handles read bytes + execute + write bytes
  After:  multiple I/O threads read/write bytes, main thread executes
  Rule:   command execution is STILL single-threaded (no locks needed)

Thread analogy:
  MySQL app (blocking I/O): 500 threads, each sleeping 99.98% of time
  Redis (epoll):             1 thread, never sleeping, processing all sockets

Interview one-liner:
"Redis is fast because 100ns RAM operations don't need threads —
one event loop with epoll processes 10,000 connections without sleeping,
and single-threaded execution eliminates lock overhead that would cost
more than the operations themselves."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** "Why is Redis fast?" is a classic follow-up question in any system that uses Redis as a cache. Knowing the event loop model and epoll separates you from candidates who just say "it's in-memory."

| System | Why Redis internals matter here |
|--------|---------------------------------|
| **04 — Chat (WhatsApp)** | Redis pub/sub for real-time message delivery. Interviewer asks: "How does Redis handle millions of users sending messages simultaneously?" → single-threaded event loop, all pub/sub operations serialized, no race conditions on channel subscriber lists. |
| **02 — Rate Limiter** | Redis INCR + EXPIRE for token bucket. "Why doesn't Redis INCR have race conditions?" → single-threaded execution makes INCR atomic by default. No need for MULTI/EXEC just for INCR. |
| **09 — E-Commerce** | Redis for session + cart cache. "Can Redis handle Black Friday traffic spike — 100x normal?" → single instance handles 100K-200K ops/sec; Redis Cluster for 10x headroom; epoll means connection count spike doesn't create thread explosion. |
| **13 — Leaderboard / Top-K** | Redis ZADD/ZRANGE for sorted sets. "Why is Redis the right choice for leaderboards vs a relational DB?" → ZRANGEBYSCORE is O(log N + M), executes in microseconds in RAM; MySQL equivalent requires ORDER BY with index, still 10ms disk I/O. |
| **16 — Job Scheduler** | Redis for distributed lock (job claiming). "Why is SETNX atomic?" → single-threaded means no two threads can both see the key as absent and both succeed. The atomicity is free from the architecture. |

**Architect's one-liner for the interview:**
*"Redis is fast not because it uses many threads, but because it needs none — 100ns RAM operations with epoll I/O multiplexing means one thread outperforms a thread pool by eliminating all synchronization overhead."*

---

## PART 8 — SINGLE-THREADED vs MULTI-THREADED: WHAT IS EACH?

### The simple rule

```
SINGLE-THREADED (always, since Redis 1.0):
────────────────────────────────────────────────────────────────────
  ✓ Reading and parsing commands from sockets
  ✓ Executing commands (GET, SET, ZADD, INCR, LPUSH, etc.)
  ✓ Writing replies back to clients
  ✓ Everything that touches the main data structures

MULTI-THREADED — I/O only (added Redis 6.0, optional, off by default):
────────────────────────────────────────────────────────────────────
  ✓ Reading raw bytes FROM the socket (network I/O read)
  ✓ Writing raw bytes TO the socket (network I/O write)
  ✗ Does NOT execute commands — main thread still does that

BACKGROUND THREADS (always existed, even Redis 1.0):
────────────────────────────────────────────────────────────────────
  ✓ Saving RDB snapshot to disk    (BGSAVE — fork + write)
  ✓ Rewriting AOF log              (BGREWRITEAOF)
  ✓ Freeing memory for large keys  (lazy free — DEL of 10M items)
  ✓ Cluster bus communication      (node-to-node heartbeats)
  These NEVER touch the main hash table. They operate on a fork
  or on their own separate memory region.
```

---

### Visual: what each thread does for one request (Redis 6+)

```
Redis 6 with io-threads enabled (e.g., io-threads 4):
────────────────────────────────────────────────────────────────────

  I/O Thread 1: [read bytes from socket A] ──────────────────────► [write reply bytes to socket A]
  I/O Thread 2: [read bytes from socket B] ──────────────────────► [write reply bytes to socket B]
  I/O Thread 3: [read bytes from socket C] ──────────────────────► [write reply bytes to socket C]
                        │                                                    ▲
                        │  (raw bytes handed to main thread)                │
                        ▼                                                    │
  Main Thread:  [parse "GET user:123"] → [hash lookup, 100ns] → [format reply "+Alice\r\n"]
                ←──────────────── SINGLE-THREADED ZONE ─────────────────────►

  I/O threads do the boring byte shuffling from the kernel buffer.
  Main thread owns ALL data access. No locks anywhere.
```

---

### Why command execution MUST stay single-threaded

```
The INCR race condition if two threads executed simultaneously:
────────────────────────────────────────────────────────────────────

  Redis has: page_views = 99

  Thread A: reads  page_views → 99
  Thread B: reads  page_views → 99   ← reads BEFORE Thread A writes
  Thread A: writes page_views → 100
  Thread B: writes page_views → 100  ← should be 101. LOST AN INCREMENT.

  Single-threaded solution (no locks needed):
  Main thread: reads page_views → 99
  Main thread: writes page_views → 100
  (Thread B's INCR queued, executes next)
  Main thread: reads page_views → 100
  Main thread: writes page_views → 101  ✓ correct

  This is why ALL Redis commands are atomic by default:
  INCR, SETNX, GETSET, LPUSH, ZADD — no MULTI/EXEC needed for
  single-command atomicity. The architecture guarantees it for free.
```

---

### Background threads — what they do and why they're safe

```
BGSAVE (RDB snapshot):
  Redis forks the process. The child process gets a copy-on-write
  snapshot of memory. Main thread keeps serving requests.
  Child writes snapshot to disk. Main thread never blocks.
  (fork() on Linux: copy-on-write, only modified pages are copied)

AOF rewrite (BGREWRITEAOF):
  A background thread rewrites the append-only log to compact it.
  Main thread continues appending to the old log.
  When rewrite completes, the two are merged. Zero downtime.

Lazy free (Redis 4.0+):
  Problem: DEL a key holding 10 million items → freeing 10M list
           nodes takes ~500ms → main thread blocked for 500ms → bad.
  Solution: UNLINK command (async DEL). Main thread removes the key
            reference instantly (1 operation, ~100ns). Lazy-free
            background thread does the actual memory freeing.
  Config: lazyfree-lazy-expire yes  (expired keys freed lazily too)
```

---

### Version history

| Version | Threading model |
|---------|----------------|
| **Redis 1.0 – 5.x** | Pure single-threaded for all I/O and execution. Background threads only for disk persistence. |
| **Redis 6.0 (2020)** | Optional I/O threads for socket reads/writes (`io-threads 4`). Command execution still single-threaded. Disabled by default. |
| **Redis 7.0 (2022)** | Improved lazy free threading, better cluster bus handling, function scripts. Core model unchanged. |

---

### One-liner for interview

> *"Redis command execution has always been single-threaded — that's what makes every command atomic without locks. Redis 6 added optional I/O threads that handle reading/writing raw bytes from sockets in parallel, but the actual GET/SET/ZADD commands still execute on one main thread sequentially. Background threads have always handled disk persistence and large-key memory cleanup without ever touching the main data structures."*
