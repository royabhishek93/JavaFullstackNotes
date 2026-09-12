# Distributed Scheduler Part 4 — ShedLock (Single-Instance Job Execution)

## What is this? (Plain English)

In the earlier parts of this series, every instance of your app was allowed to *attempt* the scheduled job, and a **pessimistic row lock** (`SELECT ... FOR UPDATE`) was used to stop them from double-processing the *same rows*. All instances stayed busy — they just avoided colliding on individual records.

**ShedLock is a different strategy: only ONE instance is allowed to run the job at all.** Every other instance doesn't wait, doesn't queue, doesn't retry — it simply **skips its own execution entirely** and goes back to sleep until the next scheduled tick. Think of it like an on-call rota where, instead of every engineer picking up the same alert and racing to fix it, only the engineer whose name is on the rota that hour even picks up the phone — everyone else's phone doesn't even ring.

The core trick: ShedLock does **not** use a real database lock (no `FOR UPDATE`, no row-level locking). It uses **optimistic locking** via plain `INSERT`/`UPDATE` statements on a dedicated tracking table. "Acquiring the lock" really just means "I successfully inserted/updated one row in a table, and the database's atomicity guaranteed only one of us could win."

## The Problem It Solves

You have `N` instances of the same service, all with the identical `@Scheduled` job. You want **exactly one** instance to actually execute the job on each tick — the rest should be completely idle for that job (free to do other work), not busy-waiting or retrying. Two follow-on requirements this must satisfy:

1. **No manual coordination code.** You shouldn't have to write your own "try to claim a row, retry, handle races" logic — ShedLock's library should do all of that via annotations.
2. **Crash safety.** If the instance that's holding the "lock" crashes mid-job, some *other* instance must eventually be allowed to pick the job up — the lock can't be held forever.

## How ShedLock Works Internally

### The `shedlock` table

A single tracking table with **one row per job name** (job name is the primary key):

| Column | Meaning |
|---|---|
| `name` | Unique job name (primary key) — one row per distinct scheduled method |
| `lock_until` | Timestamp until which this job is considered "locked" — nobody else may pick it up before this time |
| `locked_at` | Timestamp when the current holder acquired the lock |
| `locked_by` | Identifier of the instance/pod that currently holds it |

### The proxy mechanism

`@EnableSchedulerLock` scans for every method annotated `@SchedulerLock` at startup and wraps it in a **generated proxy subclass**. It's the proxy — not your original method — that actually gets placed into the JVM's internal delay queue (the same `ScheduledThreadPoolExecutor` queue from Part 1). When the scheduled tick fires, the proxy runs **pre-processing → your real method → post-processing**, all transparently:

```
Lanes: Q = Delay Queue (per instance) | Proxy = ShedLock Proxy | DB = shedlock table | Job = Your real @Scheduled method

1)  Q     ──────────> Proxy : tick fires, invoke proxy method
2)  Proxy ──────────> DB    : pre-processing: row for "my job" exist?
    ┌─ alt: first ever run ────────────────────────────────────────────────────────┐
3)  │  Proxy ──────────> DB : INSERT (name, locked_at=now, lock_until=now+lockAtMostFor, locked_by=me)  │
    ├─ else: row already exists ──────────────────────────────────────────────────┤
4)  │  Proxy ──────────> DB : UPDATE ... SET lock_until=now+lockAtMostFor, locked_by=me           │
    │                                   WHERE name='my job' AND lock_until <= now                     │
    └────────────────────────────────────────────────────────────────────────────────────┘
5)  Proxy <────────── DB : 1 row affected (I won) OR 0 rows affected (someone else already holds it)
    ┌─ alt: won the lock ────────────────────────────────────────────────────────┐
6)  │  Proxy ──────────────────────────> Job : super.runMyJob() — actual business logic executes           │
7)  │  Proxy <───────────────────────── Job : done                                                     │
8)  │  Proxy ──────────> DB  : post-processing: UPDATE lock_until = MAX(now, locked_at + lockAtLeastFor) │
9)  │  Proxy ──────────> Q   : compute next run time, re-queue                                │
    ├─ else: lost the lock ─────────────────────────────────────────────────┤
10) │  Proxy ──────────> Q   : skip entirely — compute next run time, re-queue (no wait, no retry) │
    └──────────────────────────────────────────────────────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

**Why this is "optimistic," not pessimistic:** no `FOR UPDATE`, no held connection, no blocking. Every instance just tries an `INSERT` or a conditional `UPDATE ... WHERE lock_until <= now`. Because SQL `UPDATE`/`INSERT` execution is atomic at the row level, if two instances race, the database guarantees exactly one of them gets "1 row affected" and the other gets "0 rows affected" — that's the entire locking mechanism.

### The two duration parameters

| Parameter | Stored in DB? | Meaning |
|---|---|---|
| `lockAtMostFor` | Yes (`lock_until`) | **Maximum** time the lock can be held. Mandatory — if the job crashes or hangs, this is the safety net that eventually lets another instance take over. Can be set as an app-wide default via `@EnableSchedulerLock(defaultLockAtMostFor = "10m")`. |
| `lockAtLeastFor` | No — config only | **Minimum** time the lock must be held, even if the job finishes early. Prevents a fast-finishing job (e.g. finishes in 3s) from immediately becoming eligible for a second run seconds later. Post-processing sets `lock_until = MAX(now, locked_at + lockAtLeastFor)`. |

### The overrun edge case (interview favorite)

If a job's actual runtime exceeds `lockAtMostFor`, **a second instance CAN legitimately acquire the lock while the first instance is still running** — because from the database's point of view, `lock_until` has already passed, so the `WHERE lock_until <= now` condition succeeds for a new claimant. This is the one scenario where ShedLock allows brief duplicate execution:

```
Pod A: locked_at=9:00, lock_until=9:08 (lockAtMostFor=8m) — job STILL running at 9:15 (overran badly)
Pod B: tick at 9:15 → checks lock_until (9:08) <= now (9:15)? YES → Pod B acquires the lock and ALSO starts running
```
**Takeaway:** `lockAtMostFor` must be set comfortably longer than the job's worst-case runtime, or you risk two instances processing the same batch simultaneously — the exact problem ShedLock was meant to prevent.

## Key Code / Config

```xml
<!-- Core integration between ShedLock and Spring -->
<dependency>
    <groupId>net.javacrumbs.shedlock</groupId>
    <artifactId>shedlock-spring</artifactId>
    <version>5.x</version>
</dependency>
<!-- Wrapper matching your storage: JDBC, Redis, MongoDB, etc. -->
<dependency>
    <groupId>net.javacrumbs.shedlock</groupId>
    <artifactId>shedlock-provider-jdbc-template</artifactId>
    <version>5.x</version>
</dependency>
```

```java
@Configuration
@EnableScheduling
@EnableSchedulerLock(defaultLockAtMostFor = "10m")
public class SchedulerConfig {

    @Bean
    public LockProvider lockProvider(DataSource dataSource) {
        return new JdbcTemplateLockProvider(
            JdbcTemplateLockProvider.Configuration.builder()
                .withJdbcTemplate(new JdbcTemplate(dataSource))
                .usingDbTime() // use DB server time, not app server clock, to avoid clock-skew bugs
                .build()
        );
    }
}
```

```java
@Service
public class ReportJob {

    @Scheduled(fixedRate = 60_000) // every 1 minute
    @SchedulerLock(
        name = "myJob",           // optional; defaults to class+method name
        lockAtMostFor = "8m",     // mandatory safety ceiling
        lockAtLeastFor = "4m"     // optional floor
    )
    public void runMyJob() {
        // your actual business logic — ShedLock never touches this
    }
}
```

```sql
-- schema.sql
CREATE TABLE shedlock (
    name       VARCHAR(64) PRIMARY KEY,
    lock_until TIMESTAMP(3) NOT NULL,
    locked_at  TIMESTAMP(3) NOT NULL,
    locked_by  VARCHAR(255) NOT NULL
);
```

## Interview Q&A

**Q: How is ShedLock different from the pessimistic row-locking approach used earlier in this series?**
A: Pessimistic locking (`SELECT FOR UPDATE`) lets *every* instance run the job but stops them from touching the same *row*. ShedLock stops all but *one instance* from running the job *at all* — the rest skip execution completely, they don't queue or wait.

**Q: Is ShedLock's lock a real database lock?**
A: No — it's optimistic. There's no `FOR UPDATE`, no held connection. It's a plain `INSERT`/conditional `UPDATE` on a tracking table; the database's row-level atomicity is what prevents two instances from both succeeding.

**Q: What happens if the instance holding the lock crashes?**
A: The lock self-expires at `lock_until` (`locked_at + lockAtMostFor`). Once that time passes, any other instance's `UPDATE ... WHERE lock_until <= now` will succeed and it takes over. No manual cleanup or heartbeat is needed.

**Q: Can two instances ever run the same job at the same time with ShedLock?**
A: Yes — if the job's real runtime exceeds `lockAtMostFor`. Once `lock_until` passes, a second instance can legitimately claim the lock while the first is still executing. The mitigation is to set `lockAtMostFor` well above the job's realistic worst-case duration.

**Q: Why does `lockAtLeastFor` exist if the job already finished?**
A: To stop rapid back-to-back re-execution when a job finishes unusually fast. Without it, a job that normally takes minutes but occasionally finishes in seconds could become immediately eligible to run again, defeating the intended cadence.

**Q: Why do you need a separate "wrapper" dependency (`shedlock-provider-jdbc-template`) instead of just JDBC directly?**
A: The wrapper is what understands the `shedlock` table's specific schema (`name`, `lock_until`, `locked_at`, `locked_by`) and issues the correct insert/update statements against it. Swap the wrapper (Redis, MongoDB, DynamoDB, etc.) to change the storage backend without touching your `@SchedulerLock` annotations.
