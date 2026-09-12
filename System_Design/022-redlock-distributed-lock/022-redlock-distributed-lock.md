# Redlock — Distributed Locking with Redis
### Why Redis SETNX Is Unsafe, How Redlock Works, and When to Use a Database Lock Instead

---

## PART 1 — THE STUDENT CONVERSATION

Imagine you have 5 bank vaults (Redis nodes). To claim a lock, you need to physically lock at least 3 of them (majority).

1. You walk to vault 1, insert your key — locked.
2. Vault 2 — locked.
3. Vault 3 — locked.
4. You now hold **3 out of 5** (majority). The lock is yours.

If vault 4 or 5 crashes while you hold the lock, you still have the majority — the lock is valid. If your key expires (TTL), you lose access to all 5 vaults, and another process can now claim 3 of them.

Why not just lock one vault (simple Redis SETNX)? Because if that single Redis node goes down while you hold the lock, everything either gets stuck (can't acquire the lock) or the lock vanishes (nobody knows it existed) — another process takes it and now two processes run the "exclusive" operation simultaneously.

**The core problem Redlock solves**: single-node Redis for locking assumes Redis is always available and that your process doesn't pause unexpectedly. Neither assumption holds in production. Redlock distributes the lock across multiple independent Redis nodes, so no single failure breaks the guarantee.

One more concept: even Redlock isn't bulletproof. If your process pauses for longer than the lock TTL (GC pause, VM preemption), the lock expires and someone else acquires it — but your process resumes thinking it still holds it. The defense is a **fencing token**: a monotonically increasing number attached to every write, so the storage layer can reject stale writes from processes that outlived their lock.

---

## PART 2 — DIAGRAMS

### Simple SETNX Lock and Its Problems

```
Simple Redis lock:
  Client A: SET lock:payment "client_A" EX 30 NX   <-- acquire (TTL=30s)
            ...process payment...
            DEL lock:payment                         <-- release

PROBLEM 1 — GC pause:
  t=0:   Client A acquires lock (TTL=30s)
  t=5:   Client A starts processing
  t=6:   JVM GC pause begins on Client A
  t=36:  Lock expires (30s TTL elapsed during GC)
  t=36:  Client B acquires lock (lock is free)
  t=38:  Client A resumes from GC, still thinks it holds the lock
         Both A and B are now inside the "exclusive" section!

PROBLEM 2 — Deleting someone else's lock:
  t=0:   Client A acquires lock
  t=31:  Client A lock expires (TTL elapsed, A was slow)
  t=31:  Client B acquires lock
  t=32:  Client A wakes up, runs DEL lock:payment
         --> Client A just deleted Client B's lock!
  t=32:  Client C acquires lock (now 2 concurrent holders: B and C)

FIX for Problem 2 — Lua script atomic check-and-delete:
  SET lock:payment "random_token_A" EX 30 NX       <-- include unique token

  -- Lua script (atomic):
  if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
  else
    return 0
  end
  -- Only deletes if the token matches: you only delete YOUR lock
```

### Redlock Algorithm (5 Independent Redis Nodes)

```
Setup: 5 independent Redis instances (no replication between them)
Goal:  Acquire lock "lock:cron_job" with TTL=10s

Step 1: Record start time
  t_start = current_time_ms()

Step 2: Try to acquire lock on ALL 5 nodes (in parallel):
  for each node in [redis1, redis2, redis3, redis4, redis5]:
    SET lock:cron_job <random_token> PX 10000 NX
    (use short timeout ~50ms per node to avoid waiting on failed nodes)

Step 3: Count successes
  acquired_count = number of successful SETs

Step 4: Check majority + validity window
  elapsed = current_time_ms() - t_start
  clock_drift = max(2ms, elapsed * 0.01)    // 1% drift + 2ms constant
  remaining_validity = 10000 - elapsed - clock_drift

  if acquired_count >= 3 AND remaining_validity > 0:
    LOCK ACQUIRED. Valid for `remaining_validity` ms.
    (Use this remaining time, not the original 10s)
  else:
    LOCK FAILED.
    --> Release all partial locks immediately:
        for each acquired node: run Lua check-and-delete
    --> Wait random backoff (e.g., 100-500ms), retry

Step 5: Release
  for each of 5 nodes:
    Lua: if GET lock:cron_job == random_token then DEL lock:cron_job
```

### Fencing Token (Solving the GC Pause Problem)

```
The problem Redlock alone doesn't solve:

  t=0:   Client A acquires Redlock (validity = 9800ms)
  t=1:   Client A writes to storage with token=33
         Storage accepts: last_seen_token=33
  t=2:   Client A pauses for 12 seconds (JVM GC / VM preemption)
  t=10:  Lock expires. Client B acquires Redlock, gets token=34
  t=10:  Client B writes to storage with token=34
         Storage accepts: last_seen_token=34
  t=14:  Client A resumes, writes to storage with token=33
         Storage REJECTS: 33 < last_seen_token=34 [SAFE!]

Fencing token = monotonically increasing integer issued by lock service
Storage layer rejects any write where token < highest_seen_token

Who provides fencing tokens?
  ZooKeeper: zxid (transaction ID) is monotonically increasing -> use this
  etcd: lease revision number -> use this
  Redlock: does NOT provide fencing tokens natively
           Must implement externally (e.g., Redis INCR before lock acquisition)

For absolute correctness: ZooKeeper or etcd. For "good enough" with low probability of collision: Redlock + heartbeat.
```

### Failure Scenarios Comparison

```
+--------------------+------------------+------------------+------------------+
|  Scenario          | SETNX (single)   | Redlock (5 node) | ZooKeeper        |
+--------------------+------------------+------------------+------------------+
| Single Redis crash | Lock lost/stuck  | 2/4 remain -> OK | Leader reelected |
| 2 Redis crash      | N/A (single)     | 2/5 remain ->    | Quorum lost if   |
|                    |                  | lock FAILS SAFE  | > half down      |
| GC pause > TTL     | Dual holders     | Dual holders     | Dual holders     |
|                    |                  | (same problem)   | (same problem)   |
| GC + fencing token | No protection    | No protection    | PROTECTED        |
|                    |                  |                  | (zxid ordering)  |
| Network partition  | Split brain      | Minority cannot  | No split brain   |
|                    |                  | acquire lock     | (quorum write)   |
+--------------------+------------------+------------------+------------------+
```

---

## PART 3 — INTERNALS: CONFIGS, CODE, AND REAL NUMBERS

### Redlock with Redisson (Java Production Library)

```java
// Dependency: com.redisson:redisson:3.24.0

Config config = new Config();
config.useClusterServers()
    .addNodeAddress(
        "redis://redis1:6379",
        "redis://redis2:6379",
        "redis://redis3:6379",
        "redis://redis4:6379",
        "redis://redis5:6379"
    );

RedissonClient redisson = Redisson.create(config);

// Acquire Redlock
RLock lock1 = redisson.getFairLock("lock:cron:billing");  // per-node lock
RLock lock2 = redisson.getFairLock("lock:cron:billing");  // ...
// Redisson's RedissonRedLock wraps multi-node acquisition:
RedissonRedLock redLock = new RedissonRedLock(lock1, lock2, lock3, lock4, lock5);

try {
    // Try to acquire: wait up to 200ms, hold for at most 30s
    boolean acquired = redLock.tryLock(200, 30_000, TimeUnit.MILLISECONDS);
    if (acquired) {
        try {
            runBillingJob();
        } finally {
            redLock.unlock();
        }
    } else {
        log.info("Another instance is running billing job, skipping");
    }
} catch (InterruptedException e) {
    Thread.currentThread().interrupt();
}
```

### ShedLock (Spring Production Library — Simpler)

```java
// Dependency: net.javacrumbs.shedlock:shedlock-spring:5.10.0

// Uses DB OR Redis as backend. No 5-node complexity needed.
// DB backend: creates a shedlock table, advisory lock behavior
// Redis backend: single-node SETNX (simpler but not true Redlock)

@Component
public class BillingScheduler {

    @Scheduled(cron = "0 0 * * * *")   // every hour
    @SchedulerLock(
        name = "billing_job",
        lockAtMostFor = "PT30M",    // lock held at most 30 minutes (safety TTL)
        lockAtLeastFor = "PT5M"     // even if job finishes in 1min, hold lock 5min
                                    // prevents rapid re-execution on clock skew
    )
    public void runBillingJob() {
        // Only ONE instance executes this per hour across all pods
        billingService.processAllPendingInvoices();
    }
}

// ShedLock table (PostgreSQL):
// CREATE TABLE shedlock(
//   name VARCHAR(64) NOT NULL,
//   lock_until TIMESTAMP NOT NULL,
//   locked_at TIMESTAMP NOT NULL,
//   locked_by VARCHAR(255) NOT NULL,
//   PRIMARY KEY (name)
// );
```

### PostgreSQL Advisory Locks (Single-DB Scenarios)

```java
// Session-level advisory lock (held until explicitly released or connection closed)
@Transactional
public void processPayment(long paymentId) {
    // pg_advisory_xact_lock: held for transaction duration, auto-released on commit/rollback
    jdbcTemplate.execute("SELECT pg_advisory_xact_lock(" + paymentId + ")");
    // Only one transaction can hold this lock for paymentId at a time
    // Other transactions BLOCK until this transaction ends
    Payment payment = paymentRepo.findById(paymentId).orElseThrow();
    if (payment.getStatus() == PENDING) {
        chargeCard(payment);
        payment.setStatus(PROCESSED);
        paymentRepo.save(payment);
    }
    // Lock auto-released when @Transactional commits
}

// Try-lock (non-blocking):
Boolean acquired = jdbcTemplate.queryForObject(
    "SELECT pg_try_advisory_xact_lock(?)", Boolean.class, paymentId
);
if (Boolean.TRUE.equals(acquired)) {
    // Got the lock -- process
} else {
    // Someone else is processing this payment right now -- skip or retry
}
```

### Heartbeat Pattern for Long-Running Locked Jobs

```java
// Problem: what if the job takes longer than the lock TTL?
// Solution: heartbeat thread extends the TTL while job runs

ScheduledExecutorService heartbeat = Executors.newSingleThreadScheduledExecutor();
String lockKey = "lock:data_export";
String token = UUID.randomUUID().toString();
long ttlMs = 30_000;  // 30 second TTL

// Acquire
boolean acquired = redis.set(lockKey, token, SetArgs.Builder.nx().px(ttlMs));

if (acquired) {
    // Heartbeat: extend TTL every 10 seconds (1/3 of TTL)
    ScheduledFuture<?> heartbeatTask = heartbeat.scheduleAtFixedRate(() -> {
        String current = redis.get(lockKey);
        if (token.equals(current)) {
            redis.pexpire(lockKey, ttlMs);   // reset TTL
        }
    }, 10, 10, TimeUnit.SECONDS);

    try {
        runLongDataExport();   // might take 5 minutes
    } finally {
        heartbeatTask.cancel(false);
        // Release with Lua script
        redis.eval(
            "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) else return 0 end",
            Collections.singletonList(lockKey),
            Collections.singletonList(token)
        );
    }
}
```

### Real-World TTL Guidelines

```
Job type                    Recommended TTL    Notes
----------------------------+-----------------+--------------------------------------------
Cron job (seconds)          30s - 5m          Must be > max expected job duration
Cron job (minutes)          10m + 20% buffer  Use heartbeat for jobs > 5 minutes
Booking hold (seat/ticket)  10m               Expires if user abandons checkout
Flash sale inventory lock   5-10s             Very short; aggressive retry acceptable
Payment processing          30s               Heartbeat if async external calls involved
Idempotency key             24h               Deduplicate retries, not a mutex
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer**: Your job scheduler needs to ensure only one instance runs a specific cron job even when 10 scheduler instances are deployed. How do you implement distributed locking?

**You**: I'd use ShedLock with a database backend for most cases, or Redlock with Redis for cross-cluster scenarios. Let me explain both.

With ShedLock on PostgreSQL: each scheduler instance tries to INSERT or UPDATE a row in the `shedlock` table for the job name. PostgreSQL's row-level locking ensures only one INSERT wins. The TTL is stored in `lock_until` — if the holder crashes, the lock expires naturally and another instance picks it up. Clean, simple, already using PostgreSQL. This is my default recommendation.

**Interviewer**: What if you need to lock across microservices that each have their own databases?

**You**: Then I'd use Redlock with 3 or 5 Redis nodes. The algorithm acquires the lock on a majority of nodes — so even if one Redis node fails, the lock is still valid. TTL ensures the lock expires if the holder crashes. For a job scheduler, I'd set TTL to expected job duration + 20% buffer, and run a heartbeat thread that extends the TTL every third of that interval while the job is running.

**Interviewer**: Is Redlock bulletproof?

**You**: No. Martin Fowler and Martin Kleppmann have documented a scenario where it fails: if the lock holder pauses for longer than the TTL — due to a GC pause, VM preemption, or network partition — the lock expires and another process acquires it. When the original holder resumes, both processes think they hold the lock simultaneously. The defense is a **fencing token**: a monotonically increasing number issued by the lock service. The storage backend rejects writes with a token lower than the highest it has seen. Redlock doesn't natively provide fencing tokens — ZooKeeper does, via its transaction ID (`zxid`). For truly critical mutual exclusion where double-execution would cause financial damage, I'd use a PostgreSQL advisory lock (single DB) or ZooKeeper (distributed, with fencing). For job schedulers where the worst case is a rare double-execution, Redlock is fine and operationally simpler.

**Interviewer**: Give me a concrete example where a double-execution matters.

**You**: Ticket booking during a flash sale. If two booking service instances both enter the seat assignment code for the same seat simultaneously, you could sell the same seat twice. You can't rely on application-level locking — both pods are separate JVMs. With Redlock keyed on `lock:event:{eventId}:seat:{seatId}`, only one instance proceeds while the other gets a lock failure and returns "seat unavailable." TTL of 10 seconds covers the booking window. If the first instance crashes mid-booking, the TTL ensures the seat is released in 10 seconds for retry.

---

## PART 5 — DECISION FRAMEWORK

### Decision Tree: Which Locking Mechanism to Use

```
Is your critical section in a SINGLE service with ONE database?
    YES --> PostgreSQL advisory lock (pg_advisory_xact_lock)
            Simplest. No Redis needed. Auto-released on tx end. Strong consistency.
    NO  |
        |
        v
Is the critical section time-bounded (< 30 minutes)?
    NO  --> Long-running process lock with heartbeat. Reconsider architecture.
    YES |
        |
        v
Do you need fencing tokens (absolutely no double-execution)?
    YES --> ZooKeeper or etcd ephemeral nodes + monotonic sequence
            Higher operational complexity. Worth it for financial double-debit prevention.
    NO  |
        |
        v
Are you already running Redis in the stack?
    YES --> Redlock with 3-5 independent Redis nodes (or use ShedLock with Redis)
    NO  --> ShedLock with existing DB (PostgreSQL/MySQL)
            Uses existing infrastructure. No new dependency.
```

### Comparison Table

| Mechanism | Consistency | Failure Handling | Fencing Tokens | Operational Cost | Best For |
|---|---|---|---|---|---|
| SETNX single Redis | Weak | Lock lost on Redis crash | No | Low | Dev/testing only |
| Redlock (5 nodes) | Good | Survives minority failure | No (add externally) | Medium | Cross-service jobs, ticket booking |
| ShedLock (DB) | Strong (single DB) | Lock expires via TTL row | No | Very Low | Cron jobs with existing DB |
| PostgreSQL advisory | Strong | Auto-release on crash | No | Very Low | Single-DB mutual exclusion |
| ZooKeeper ephemeral | Strongest | Session expiry on crash | Yes (zxid) | High | Financial, inventory, exactly-once |
| etcd lease | Strongest | TTL expiry, watch API | Yes (revision) | High | Kubernetes-native, distributed config |

---

## QUICK REFERENCE CARD

```
SETNX PATTERN (avoid in production):
  SET key token EX 30 NX                      Acquire
  if GET key == token then DEL key (Lua)      Release safely

REDLOCK ALGORITHM:
  1. Record t_start
  2. SET lock:key <random_token> PX <ttl> NX on ALL N nodes
  3. Count successes. Check remaining validity = ttl - elapsed - drift
  4. If successes >= N/2+1 AND validity > 0: lock acquired
  5. Else: release all partial locks, wait random backoff, retry
  6. Release: Lua check-and-delete on all nodes

JAVA LIBRARIES:
  Redisson: RedissonRedLock (full Redlock implementation)
  ShedLock: @SchedulerLock annotation (DB or Redis backend, production standard for Spring cron)
  Lettuce/Jedis: manual SETNX + Lua (single-node, use for simple cases)

POSTGRESQL ADVISORY:
  pg_advisory_xact_lock(id)       Block until acquired, auto-release on tx end
  pg_try_advisory_xact_lock(id)   Non-blocking, returns true/false

ANTI-PATTERNS:
  DEL key without token check     Deletes another process's lock
  TTL without heartbeat           Long jobs lose lock mid-execution
  Single Redis for critical locks Lock lost on Redis restart/crash
  acks without min.insync.replicas Kafka data loss (different domain, same principle)

GOLDEN RULES:
  Always use unique random token per lock acquisition
  Always use Lua scripts for check-and-delete (atomic)
  TTL = expected duration + 20-50% buffer
  Add heartbeat for any job that might exceed TTL
  Use fencing tokens when double-execution is financially dangerous
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

| System | Lock Used | Why |
|---|---|---|
| **07 Payment System** | PostgreSQL advisory lock OR idempotency key | Single-DB payment processing: `pg_advisory_xact_lock(payment_id)` held for transaction duration. If payments span shards: Redlock on `lock:payment:{payment_id}`. No double-debit allowed. |
| **11 Ticket Booking** | Redlock on `lock:event:{id}:seat:{seatId}` | Flash sale — multiple booking service instances compete for the same seat. Redlock ensures only one instance proceeds. TTL=10 minutes (booking hold time). Customer either completes or seat releases automatically. |
| **16 Job Scheduler** | ShedLock (`@SchedulerLock`) | Classic use case: one instance runs each scheduled job across 10+ replicated pods. ShedLock is the production-grade Spring library. Uses DB (PostgreSQL) or Redis as backend. Lock TTL = job expected duration. |
| **09 E-Commerce Flash Sale** | Redlock on `lock:inventory:{productId}` | Prevent overselling: before decrementing inventory, acquire lock on product. TTL=5s. Lua script checks stock before decrement. Non-blocking variant returns "out of stock" immediately if lock contested. |
| **19 Stock Broker** | PostgreSQL advisory lock for order matching | Order matching engine is single-DB per market. Advisory lock on `instrument_id` prevents concurrent conflicting order modifications. Stronger than Redlock; no distributed system needed within one exchange. |

---

> **Architect one-liner**: "Redlock acquires a majority lock across 3+ Redis nodes — safe against single-node failure, but for absolute correctness use a fencing token from ZooKeeper or a PostgreSQL advisory lock."
