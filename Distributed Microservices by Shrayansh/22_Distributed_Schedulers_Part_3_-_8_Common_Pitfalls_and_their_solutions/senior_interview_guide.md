# Distributed Scheduler Pitfalls — 15 YOE Architect Interview Guide

---

## How a Senior Architect Frames This Topic

> "Schedulers look trivial on the surface — a cron annotation and you're done. But at scale they are one of the highest-risk components in a system. I've seen data corruption, double-debits, and production outages all trace back to a scheduler that 'worked fine in staging.' Let me walk you through the failure modes in order of increasing complexity."

This framing signals: you've shipped this in prod, you've been burned, you know the blast radius.

---

## Pitfall 1 — Timezone Misconfiguration

### Junior answer
"Use `zone` in `@Scheduled`."

### Architect answer
> "Timezone bugs are insidious because they are silent — the job runs, just at the wrong time. In a globally distributed system I always treat time as a first-class concern. Our convention: **all cron expressions are in UTC at the application layer**, and business-level offsets (send at 9am user local time) are handled by partitioning jobs per region or storing user timezone in the job payload. Hardcoding `Asia/Calcutta` in an annotation is a deployment hazard — if the service moves to a different region or the JVM default changes, you get drift with no compile-time warning. I prefer externalizing the timezone to config (`scheduler.timezone=UTC`) so ops can override without a redeploy."

### Trap question: "What if you need per-user timezone scheduling?"
> "You don't use a fixed cron at all. You push per-user scheduled events into a job queue (SQS/Kafka/Quartz with a DB store) with the absolute UTC fire time computed at enqueue time. The scheduler becomes a simple dequeuer, not a cron. This also solves DST transitions automatically."

---

## Pitfall 2 — Missing `@Transactional`

### Junior answer
"Wrap the method in `@Transactional`."

### Architect answer
> "The real trap is **transaction boundary design**, not just slapping `@Transactional` on the scheduler method. If the scheduler method is `@Transactional` AND it calls another `@Transactional` method, Spring's default propagation is `REQUIRED` — you get one big transaction. That's almost never what you want in a scheduler because a single failure rolls back everything processed so far. I design scheduler transactions to be **short-lived and granular** — one transaction per record or per small batch, not one transaction for the entire job run. The scheduler method itself is deliberately non-transactional; it's an orchestrator."

### Trap question: "What about `@Transactional(readOnly = true)` on the fetch query?"
> "Yes, I always do this on the SELECT phase and a separate write transaction on the processing phase. `readOnly=true` tells Hibernate to skip dirty checking and flush, which is a meaningful CPU and memory saving when you're loading 50,000 entities just to read them. On some databases like PostgreSQL it also routes to a read replica automatically via the datasource routing proxy."

---

## Pitfall 3 — Fetching Huge Data / OOM

### Junior answer
"Use batch processing with `LIMIT 1000`."

### Architect answer
> "Batch size is not a magic number — it's derived from your JVM heap budget, entity size, and GC pressure. My formula: `safe_batch_size = (available_heap * 0.1) / avg_entity_size_bytes`. I use 10% of heap as the budget because you need headroom for the processing work itself. In practice I'd also add a circuit breaker: if the batch size after processing still returns exactly N records three times in a row, that's a signal the query is returning duplicates or the status update is silently failing — alert and halt rather than spin forever. I also instrument batch duration via Micrometer so we can see if batch time is trending up over weeks — that's early warning of a data growth problem before it becomes an outage."

### Trap question: "Why not use JPA pagination (`Pageable`) instead of `LIMIT` in the query?"
> "JPA pagination with `OFFSET` has O(n) cost on most databases — fetching page 85 requires the DB to scan and discard the first 84,000 rows. For a scheduler that processes all rows this compounds badly. Keyset/seek pagination (using `WHERE id > last_processed_id ORDER BY id`) is O(1) per page. Alternatively, status-based pagination like we discussed — `WHERE status NOT IN ('EXPIRED','FAILED') LIMIT 1000` — avoids offset entirely and is what I prefer in practice."

---

## Pitfall 4 — First-Level Cache Memory Leak

### Junior answer
"Use a separate `@Transactional` per batch in a separate `@Service`."

### Architect answer
> "This is a Spring internals trap that catches even senior engineers. The root cause is that JPA's `EntityManager` (persistence context) acts as a **Unit of Work** — it tracks every entity it loads for dirty checking. If your scheduler has one long-running transaction, that context accumulates all loaded entities and holds hard references that prevent GC. The fix — one transaction per batch — works, but there's a subtlety: you **cannot** call a `@Transactional` method on the same bean from within the same bean (self-invocation bypasses Spring's proxy). If you do, you get no new transaction at all — Spring silently inherits the outer one. This is why the batch logic must be in a **separate Spring bean**, not a private method on the same class. I've reviewed code where engineers added `@Transactional` to a private helper method and wondered why memory kept growing — the proxy never intercepts private methods."

### Trap question: "What is `spring.jpa.open-in-view` and why does it matter here?"
> "Open-Session-In-View is a servlet filter that opens a Hibernate session at the start of an HTTP request and holds it until the response is sent. This means all lazy-loaded relations can be fetched even after the transaction commits — convenient but dangerous because it holds a DB connection for the entire request lifecycle. In schedulers there is no HTTP request so OSIV is irrelevant — each transaction has its own session. But if you're building a REST API that calls the same service as the scheduler, OSIV can mask the boundary problem: it works in the API because the session is kept alive, but silently fails in the scheduler context. I disable OSIV globally (`spring.jpa.open-in-view=false`) in every project — it forces explicit transaction design everywhere."

---

## Pitfall 5 — Exception Handling (Three-Layer Safety Net)

### Junior answer
"Try-catch at record level, batch level, and job level."

### Architect answer
> "Exception handling in schedulers needs an **observability contract**, not just try-catch. At the record level: a failed record must be persisted with status `FAILED` and the exception message (truncated) stored in a `failure_reason` column. This gives ops a queryable audit trail — `SELECT * FROM subscriptions WHERE status = 'FAILED'` — instead of grepping logs. At the batch level: I emit a metric counter `scheduler.batch.failure` with batch number and exception type tags. At the job level: I emit a heartbeat metric `scheduler.job.last_success_timestamp` — if this metric doesn't update within 2× the cron interval, PagerDuty fires. This is called a **dead man's switch pattern**: the alert triggers on absence of a success signal, not on presence of an error. It catches the case where the scheduler silently stops running entirely — no exception, just no execution."

### Trap question: "How do you handle poison-pill records that will always fail?"
> "A fixed retry limit with exponential backoff, then move to a dead-letter store. In the DB model: `retry_count` and `next_retry_at` columns. The scheduler query adds `AND (next_retry_at IS NULL OR next_retry_at <= NOW()) AND retry_count < 3`. On failure, increment `retry_count` and set `next_retry_at = NOW() + 2^retry_count minutes`. After max retries, status becomes `DEAD_LETTER` and an async alert is sent to the engineering team. This is borrowed from message queue patterns and maps cleanly to scheduler record processing."

---

## Pitfall 6 — N+1 SQL / Hibernate Batching

### Junior answer
"Use `spring.jpa.properties.hibernate.jdbc.batch_size=50` and `order_updates=true`."

### Architect answer
> "Hibernate JDBC batching reduces network round trips but the total SQL executed is identical. The actual win is **removing the per-statement TCP overhead and reducing context switches** on both the app server and DB server. In benchmarks I've seen 3–5× throughput improvement on bulk update workloads just from this. However, there's a gotcha: Hibernate JDBC batching is **silently disabled** for entities with `GenerationType.IDENTITY` primary keys. Identity columns require the DB to return the generated ID after each insert, which forces Hibernate to flush one at a time. If you need batching on inserts, use `GenerationType.SEQUENCE` with an `allocationSize` matching your batch size. This is a production performance trap that doesn't show up in unit tests."

### Trap question: "When would you skip Hibernate batching and use JDBC directly or a bulk update statement?"
> "For pure bulk operations with no entity lifecycle events (no `@PreUpdate`, no audit trail needed), a single JPQL bulk update — `UPDATE Subscription s SET s.status = 'EXPIRED' WHERE s.expiryDate < :now` — is an order of magnitude faster than any entity-level batching because it's **one SQL statement**, period. Hibernate batching is the right tool when you need per-entity business logic during processing. If you're just updating a column in bulk, bypass the ORM entirely. I always ask: does this operation need entity-level logic? If no, use a bulk statement. If yes, use batching."

---

## Pitfall 7 — Duplicate Execution in Multi-Instance Deployment

### Junior answer
"Use `SELECT FOR UPDATE` or `SELECT FOR UPDATE SKIP LOCKED`."

### Architect answer
> "Duplicate execution in distributed schedulers is a **correctness problem**, not just a performance problem. The severity depends on idempotency. I first ask: is this operation idempotent by design? If updating a subscription to `EXPIRED` is idempotent (running it twice has the same effect), the blast radius is much smaller — just wasted work. If it's a financial debit or an email send, duplicates cause real customer harm and legal exposure. My approach is layered: **first, make the operation idempotent where possible** (using a natural idempotency key); **second, add a locking strategy** as a second line of defence. Relying only on the lock is fragile — if the lock library has a bug or the lock expires under GC pause, you're exposed. Defence in depth: idempotency + locking.

For the locking strategy itself: `SKIP LOCKED` is the right choice for parallel throughput. Plain `SELECT FOR UPDATE` is only correct when you need strict ordering (process subscription 1 before subscription 2) — in most batch jobs ordering doesn't matter and blocking is pure waste. In a 100-pod deployment with `FOR UPDATE` (no skip), 99 pods are waiting on 1. With `SKIP LOCKED`, all 100 process different rows in parallel — 100× throughput."

### Trap question: "What happens if the instance holding the lock crashes mid-processing?"
> "With `SELECT FOR UPDATE`, the lock is held for the transaction duration. If the JVM crashes, the DB connection is closed and the lock is released — rows revert to unprocessed. This is actually safe for the DB-level lock. The real risk is partial state: the instance updated 400 of 1,000 records before crashing. Those 400 are now `EXPIRED`, the remaining 600 are not. On the next run, the query fetches the 600 (because they're `NOT IN ('EXPIRED')`). This is why **record-level status updates with atomic commits per record** (or at least per batch) are critical — they define exactly where to resume from after a crash."

---

## Pitfall 8 — Only One Instance Should Run (ShedLock)

### Junior answer
"Use ShedLock."

### Architect answer
> "ShedLock solves the **leader election** problem for schedulers cheaply. It works by inserting/updating a row in a `shedlock` table with a `lock_until` timestamp. The instance that successfully writes the row first becomes the leader and runs the job. Others see the row is locked and skip. The key architectural parameter is `lockAtMostFor` — this is the **maximum duration the lock is held even if the leader crashes**. Set it too short and a slow GC pause causes the lock to expire, allowing a second instance to start while the first is still running. Set it too long and a crashed leader blocks all instances for that window.

My rule: `lockAtMostFor = 2 × expected_max_job_duration`. And I always set `lockAtLeastFor` to prevent clock-skew races — without it, on a fast machine the job finishes in 100ms and another pod acquires the lock and reruns within the same cron window.

ShedLock is appropriate when the job is stateful or has side effects that must not run in parallel. For stateless parallel batch work, `SKIP LOCKED` is better — you get horizontal scale. ShedLock is intentionally single-threaded. Using ShedLock for a job that could safely parallelize is over-engineering in the wrong direction."

### Trap question: "ShedLock requires a shared DB — what if the DB is unavailable?"
> "ShedLock's default behaviour on DB failure is to **not run the job** — it fails safe. Whether that's correct depends on your SLA. If the scheduler is critical (payment processing), DB unavailability should already trigger a separate alert. If you need the scheduler to run even when the lock store is unavailable, ShedLock supports a `LockProvider` abstraction — you can back it with Redis or Zookeeper instead of the primary DB. In practice I'd use Redis with a TTL-based lock (Redlock pattern) for high-availability requirements, accepting the known edge cases in Redlock under network partition."

---

## Senior Trap Questions Section (9+)

### Trap Q9: "Your scheduler runs every minute. The job takes 90 seconds. What happens?"
> "With `@Scheduled(fixedRate)`, the next execution fires at T+60 even if T+0 is still running — you get overlapping executions and likely data corruption or deadlocks. With `fixedDelay`, the next execution starts 60 seconds *after the previous completes* — so effective rate becomes 150s, self-regulating but slower than intended. At 15 YOE my answer is: a job that regularly exceeds its cron interval is a **design smell**. The job is doing too much in one run. Fix: reduce batch size, increase worker thread count with a thread pool executor, or move to an event-driven model where the cron just enqueues work. For `@Scheduled` specifically, configure a dedicated `TaskScheduler` with explicit thread pool sizing rather than using the default single-threaded scheduler — one slow job should not block all other scheduled tasks in the application."

### Trap Q10: "Can you use `@Async` on a `@Scheduled` method?"
> "Yes and it's often the right call — it frees the scheduler thread immediately and the job runs on the async thread pool. But there are landmines: `@Async` exceptions are swallowed by default (they go into the returned `Future` which nobody awaits). You must configure an `AsyncUncaughtExceptionHandler` or all exceptions in async scheduled jobs are silently lost. Also, `@Async` bypasses Spring's transaction proxy when called from the same bean — you need the async method in a separate bean to get proper transaction handling. And if the async thread pool is exhausted (all threads busy from previous runs), the new task is queued or rejected depending on the executor config — you can pile up a backlog silently."

### Trap Q11: "How do you test a distributed scheduler in a CI pipeline?"
> "You don't test scheduling behaviour with real time delays in CI — that's slow and flaky. I separate concerns: (1) unit test the business logic in isolation with no scheduler involvement; (2) integration test the locking behaviour with an in-memory H2 or Testcontainers PostgreSQL — run two concurrent threads simulating two instances and assert only one processed each record; (3) test the cron expression itself using a library like `CronSequenceGenerator` to assert the next 10 fire times are what you expect. For ShedLock specifically, there's a test mode (`SimpleLock` that always acquires) and a `NoOpLock` for disabling it in tests. Never rely on `Thread.sleep()` in a scheduler test — it makes CI 10× slower and still isn't reliable."

### Trap Q12: "A scheduler ran at 2am and finished at 4am. Next day DST transition happens. What fires?"
> "With a fixed cron in a DST-affected timezone, the 2am run may not fire (spring-forward — 2am doesn't exist) or fire twice (fall-back — 2am occurs twice). The safe answer: **always schedule in UTC** for infrastructure-level jobs. UTC has no DST. If the job must run at a business-meaningful local time (2am local because that's low traffic), that's a product requirement — model it explicitly with a job definition that stores the intended local time and computes the next UTC fire time at schedule time, accounting for DST transitions. Spring's cron does not do this automatically."

### Trap Q13: "What's the difference between Quartz and Spring `@Scheduled`?"
> "Spring `@Scheduled` is simple, in-process, and has no persistence — if the pod restarts, a missed execution is lost. Quartz has a JDBC job store — job definitions, triggers, and execution history persist in the DB. If a node restarts, Quartz recovers missed triggers (`MISFIRE_INSTRUCTION`). At scale I use Quartz when: (a) I need missed-fire recovery, (b) I need dynamic job management (add/remove/pause jobs at runtime via API), or (c) I need a cluster-aware scheduler without rolling my own ShedLock. Spring `@Scheduled` is fine for simple in-process work where a missed execution on restart is acceptable — most notification jobs, cache warming, etc. Using Quartz for everything is over-engineering; using Spring `@Scheduled` for financial reconciliation is under-engineering."

### Trap Q14: "How do you monitor scheduler health in production?"
> "Three signals: (1) **Last-success timestamp** — a gauge updated on every successful completion. Alert if `now - last_success > 2 * cron_interval`. Dead man's switch. (2) **Batch duration histogram** — if p99 batch time trends upward week-over-week, data volume is growing faster than the scheduler can process. Early warning. (3) **Dead-letter record count** — records in `status = 'DEAD_LETTER'` should be zero in steady state. Alert on any non-zero value. Beyond these, I add structured logging with a correlation ID per job run so I can trace a single execution end-to-end in Splunk/Loki without filtering through thousands of lines."

### Trap Q15: "Is a scheduler the right tool here, or would an event-driven approach be better?"
> "This is the question I ask before writing any scheduler. Schedulers are **polling** — they look for work whether it exists or not. Events are **push** — work is delivered when it's ready. Use a scheduler when: the trigger is purely time-based (generate monthly invoice on the 1st), the data source doesn't emit events (polling a legacy DB), or you need periodic reconciliation as a safety net. Use events when: the trigger is a state change (subscription expires → process it immediately), latency matters (user expects instant action, not up to 1-minute delay), or you want to scale consumers independently. In mature systems I use both: events for low-latency real-time processing, and a scheduler as a **sweeper** that catches anything the event pipeline missed — delayed events, failed consumers, system downtime."

---

## The Closing Statement (to end the scheduler discussion)

> "The through-line in all of these pitfalls is that schedulers are deceptively simple to write and surprisingly hard to operate correctly at scale. The pitfalls map directly to the three dimensions of distributed systems correctness: **consistency** (duplicate execution, transaction boundaries), **availability** (instance crashes, lock expiry), and **observability** (silent failures, missing alerts). I treat any scheduler in a financial or high-stakes system with the same rigour as a distributed transaction — because that's effectively what it is."
