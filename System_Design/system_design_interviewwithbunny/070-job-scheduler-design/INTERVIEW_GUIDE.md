# Job Scheduler / Distributed Task Scheduler — Interview Script
## Design Quartz / Airflow / AWS EventBridge / Celery Beat
### Speak This Word-for-Word to Your Interviewer

> How to use: Page 1-3 first, then Page 4+. Speak aloud 2-3x.

---

# ═══════════════ PAGE 1 — START HERE ═══════════════

## BIG PICTURE

A distributed job scheduler lets you say "run this code at 2am every day" or "run this job in 5 minutes" — reliably, even when servers crash, networks partition, and midnight brings a thundering herd of 10,000 jobs all firing at once.

The design-defining challenge is: **at-least-once execution with no missed jobs and no stuck jobs.**

- If the scheduler server crashes mid-job, who detects it? Who reschedules?
- How do you prevent double-execution when the original crashed server recovers?
- How do you prevent 10,000 cron jobs all scheduled for 2am from hammering your workers simultaneously?

Every architectural decision traces back to these three problems.

---

WHY JOB SCHEDULER VS JOB QUEUE — WHAT IS THE DIFFERENCE? (Beginner Explanation)
  Think of a restaurant kitchen. The JOB SCHEDULER is the head chef who reads the reservation
  book and decides what to cook and when — "start the soufflé at 7:40pm, it takes 20 minutes."
  The JOB QUEUE is the ticket rail where orders hang, waiting to be picked up by a line cook.
  The WORKER is the cook who grabs a ticket off the rail and actually cooks the dish.
  Without the scheduler, nobody knows when to enqueue the job — it never starts on time.
  Without the queue, the scheduler must hand every ticket directly to a cook and wait —
  one cook busy means everything else is blocked.
  Without workers, tickets pile up forever and no actual work gets done.
  All three together = jobs run on time, in parallel, without chaos.

---

## RAPID ANSWER — If You Only Have 5 Minutes

"I'd build this with four services:

**1. API Service** — REST API for creating, reading, updating, deleting job definitions.

**2. Scheduler Service** — A leader-elected background process that reads Cassandra for jobs due in the next 60 seconds and pushes them into a Redis sorted set, scored by next_run_timestamp.

**3. Worker Pool** — N stateless workers that call `ZPOPMIN` on Redis to atomically pop the next due job, execute it, and update status back to Cassandra.

**4. Monitor Service** — A background thread that scans for jobs stuck in RUNNING state with no heartbeat update in 90 seconds, marks them FAILED, and re-enqueues them.

The data stores: **Redis** as the job queue (sorted set, ZPOPMIN is atomic so multiple workers can't grab the same job), and **Cassandra** as the source of truth for job definitions and execution history.

Key insight: Redis sorted set `ZPOPMIN` gives us time-based priority. Kafka is FIFO and can't answer 'give me all jobs due RIGHT NOW regardless of when they were scheduled.' That's why we use Redis, not Kafka.

For exactly-once semantics: each execution gets a UUID. Jobs must be idempotent. For non-idempotent jobs, we use a Redis distributed lock with NX — only one worker can hold the lock per job at a time."

---

# ═══════════════ PAGE 2 — GLOSSARY ═══════════════

| Term | Definition |
|------|------------|
| **Cron expression** | String like `0 2 * * *` meaning "2am daily". Quartz uses 6 fields (adds seconds). Parsed to compute next_run timestamp. |
| **ZPOPMIN** | Redis command: atomically removes and returns the element with the lowest score from a sorted set. Atomic = only one caller gets each element. |
| **Sorted set (ZSET)** | Redis data structure: each member has a numeric score. `ZADD`, `ZPOPMIN`, `ZRANGEBYSCORE` are O(log N). Score here = next_run_unix_timestamp. |
| **ZRANGEBYSCORE** | Redis: returns all members with score between min and max. `ZRANGEBYSCORE job_queue 0 now()` = all jobs due now. |
| **SETNX** | Redis SET if Not eXists. Used for leader election and distributed locks. Returns 1 if key was set (you won the lock), 0 if already exists. |
| **Heartbeat** | Executing worker writes `SET job_heartbeat:{jobId} workerId EX 90` every 30 seconds. Expiry means worker died. |
| **Leader election** | Scheduler Service: multiple instances run, only ONE may enqueue jobs. Leader holds a Redis key with TTL 30s; must renew every 15s. |
| **Look-ahead window** | Scheduler queries Cassandra for jobs due in the next 60 seconds. Runs every 30 seconds. Prevents last-second DB queries. |
| **Look-back window** | On leader failover: new leader queries Cassandra for jobs due in the past 5 minutes that were never enqueued. |
| **At-least-once** | Every job executes at minimum once. May execute twice on crash+recovery. Jobs must be idempotent. Simpler than exactly-once. |
| **Exactly-once** | Each job executes exactly once. Requires distributed locks + idempotency keys. Harder; only needed for non-idempotent jobs. |
| **Idempotent** | Running an operation multiple times produces the same result. "Send welcome email" checks if already sent → idempotent. "Charge $10" without dedup → not idempotent. |
| **execution_id** | UUID generated for each individual run of a job. Worker A (crashed) and Worker B (reschedule) get different execution_ids. Both may complete — system records both. |
| **DAG** | Directed Acyclic Graph. Workflow where Job B depends on Job A completing first. Airflow uses DAGs. |
| **Dead letter** | Job that has hit max_retries. No more automatic retry. Moved to DEAD_LETTER state. Requires manual investigation + re-trigger. |
| **Jitter** | Random delay added to next_run. Spreads thundering herd: `next_run = cron_time + random(0, 300s)`. Deterministic per job (seeded by job_id hash). |
| **Thundering herd** | 10K jobs all due at midnight → all workers busy at once → downstream services overwhelmed. Solved with jitter. |
| **TIMEUUID** | Cassandra UUID that embeds timestamp. Used as clustering key in job_executions — gives natural time-ordering for free. |
| **Exponential backoff** | Retry delay doubles each attempt: 1s, 2s, 4s, 8s… Prevents retry storms when dependent services are down. |

---

WHY CRON EXPRESSIONS EXIST? (Beginner Explanation)
  A cron expression is a recipe card for time, written in 5 (or 6) fields: minute, hour,
  day-of-month, month, day-of-week. "0 9 * * 1-5" reads: at minute 0, hour 9, any date,
  any month, Monday-through-Friday. Translation: "Run every weekday at 9:00 AM sharp."
  The * means "I don't care about this field — match every value."
  Without cron you'd write: "if today is a weekday AND the clock just ticked to 9:00 AND
  it hasn't run yet today…" — one bug and your report silently never runs again.
  Cron is a compact, battle-tested time language every developer recognises instantly.
  "0 0 1 * *" = midnight on the 1st of every month. 11 characters, zero ambiguity.
  Alternative — storing a plain timestamp — only handles one-time jobs.
  Cron handles "every Monday forever" without ever needing to be updated.

WHY DELAYED EXECUTION USES A SORTED SET? (Beginner Explanation)
  Imagine scheduling 1,000 alarm clocks. Each has a ring-time written on it. To find which
  alarms should ring RIGHT NOW you need them sorted by time so you can grab the earliest
  ones instantly. A Redis sorted set is exactly this: job IDs each stamped with a Unix
  timestamp as their score. ZRANGEBYSCORE job_queue 0 now() = "which alarms are ringing?"
  — answered in O(log N) regardless of queue size.
  For a job scheduled 30 minutes from now: ZADD job_queue (now + 1800) job_id.
  It sits in the sorted set invisible to workers (score > now) until 30 minutes pass,
  then ZPOPMIN surfaces it and a worker grabs it automatically.
  Alternative: store jobs in a plain list, scan every second for due jobs.
  With 1 million jobs that is 1 million comparisons per second — catastrophic.

WHY IDEMPOTENCY MATTERS? (Beginner Explanation)
  "Idempotent" means pressing the lift button twice gets you to the same floor as pressing
  it once. The lift does not go twice. In job scheduling, networks crash and workers die —
  the system's safe response is to run the job again. If your job charges a credit card,
  running it twice charges the customer twice. That is a nightmare.
  Idempotent jobs protect against this: check first, act second.
  "Did I already send this welcome email for user 42 today? Yes → skip."
  The alternative — relying on the scheduler to guarantee exactly-once — is technically
  very hard (distributed transactions, two-phase commit). It is far simpler to make each
  job self-aware: "I check whether I already ran before doing anything irreversible."
  Rule of thumb: if running your job 10 times looks identical to running it once, it is idempotent.

WHY DISTRIBUTED LOCKING EXISTS? (Beginner Explanation)
  Imagine two cashiers both grabbing the same customer's order slip simultaneously and
  both charging the card. Distributed locking is the physical act of one cashier picking
  up the slip and tucking it in their apron — now the other cashier cannot grab it.
  With many workers all watching the same queue, two workers can race to start the same job.
  Redis SETNX ("SET if Not eXists") is the atomic "grab the slip" move — Redis guarantees
  only one caller wins even if 100 workers call it at the exact same millisecond.
  Without locking: double-charges, duplicate emails, duplicate database rows.
  The TTL on the lock is the safety valve: if the winning worker dies mid-job, the lock
  auto-releases after N seconds so the next worker can proceed. No TTL = stuck lock forever.

WHY DEAD LETTER QUEUE EXISTS? (Beginner Explanation)
  A dead letter queue is the "problem mail" tray on a postal worker's desk — letters they
  tried to deliver three times and nobody answered. They do not throw them away, and they
  do not keep knocking forever. They set them aside for a supervisor to investigate.
  In job scheduling: a job that fails three times in a row has a structural problem — bad
  input data, a crashed downstream service, or a bug in the code.
  Retrying it a hundredth time wastes CPU and can cause retry storms that take down other
  services alongside the already-broken one.
  DEAD_LETTER status means: "Stop retrying. Alert a human. This needs investigation."
  Without it: a broken job retries forever, burning resources, filling logs, and hammering
  a downstream service that is already struggling to recover.

---

# ═══════════════ PAGE 3 — WHY EACH COMPONENT ═══════════════

| Component | Choice | Why This / Why NOT Alternatives |
|-----------|--------|----------------------------------|
| **Job queue** | Redis sorted set | `ZPOPMIN` is atomic — multiple workers can't grab same job. Score = timestamp → time-based priority. Fast in-memory. **NOT Kafka**: Kafka is FIFO, can't query "give me all jobs due NOW". **NOT RabbitMQ**: No time-based priority queue. **NOT DB polling**: 1M jobs × SELECT/sec = overload. |
| **Source of truth** | Cassandra | Wide-column, naturally models time-series (job_id partition, execution TIMEUUID clustering). High write throughput. Scales horizontally. **NOT MySQL**: single-node, schema changes painful at scale. **NOT DynamoDB**: vendor lock-in, pricing at high write volume. |
| **Scheduler** | Leader-elected single process | No duplicate enqueue — only leader pushes to Redis. Fast failover via TTL. **NOT all nodes enqueue**: every node would enqueue same job = multiple copies in Redis. |
| **Workers** | Stateless pool | Horizontal scaling. Any worker can execute any job. ZPOPMIN distributes load automatically. **NOT stateful workers**: complicates failover, hard to scale. |
| **Monitor** | Background scan service | Detects stuck jobs (heartbeat expired). Re-enqueues with fresh execution_id. **NOT worker self-reporting**: crashed worker can't report its own crash. |
| **Heartbeat store** | Redis (TTL keys) | Auto-expiry built in — no cleanup needed. Fast SET/GET. **NOT Cassandra**: TTL support is weaker; Redis EX is purpose-built for this. |
| **Distributed lock** | Redis SETNX + EX | Atomic: only one process acquires. Auto-releases on TTL if holder dies. **NOT DB-level lock**: doesn't span distributed workers. **NOT Zookeeper**: extra infra; Redis is already in stack. |
| **Cron parser** | Quartz 6-field format | Industry standard. Adds seconds field. Libraries exist in all languages. **NOT UNIX cron (5-field)**: no seconds granularity. |
| **Payload store** | S3 (large), Cassandra (small) | Job payload in ZSET would slow ZPOPMIN. Large payloads stored in S3; only S3 key in Cassandra. **NOT inline in queue**: bloats Redis memory, slow pop. |

---

# ═══════════════ PAGE 4 — FULL INTERVIEW SCRIPT ═══════════════

## OPENING

"Great, I'd like to design a distributed job scheduler — something like Quartz, Celery Beat, AWS EventBridge, or Apache Airflow's scheduler component.

Before I start drawing, let me ask a few clarifying questions to make sure I'm solving the right problem."

---

## STEP 1 — Requirements Gathering

**Say this first:** "I'm going to ask a few questions — feel free to steer me."

| YOU ASK | INTERVIEWER SAYS (typical) |
|---------|---------------------------|
| "What types of jobs do we need to support — one-time, recurring, or both?" | "Both. Cron-style recurring and one-time delayed jobs." |
| "Do we need DAG/dependency support — Job B runs after Job A?" | "Nice to have, but start with independent jobs." |
| "What's the scale? How many jobs, how many executions per second?" | "About 1 million scheduled jobs, 10,000 executions per second." |
| "What's the acceptable latency between a job's scheduled time and when it actually starts?" | "Within a second or two is fine." |
| "What are the execution semantics — at-least-once or exactly-once?" | "At-least-once is acceptable. Jobs should be designed to be idempotent." |
| "Do we need job priorities?" | "Basic priority support — high, medium, low." |
| "What happens when a job fails — manual retry or automatic?" | "Automatic retry with configurable max_retries." |
| "Any SLA on availability?" | "99.99% — we cannot silently drop jobs." |

---

**Requirements box** — confirm these before proceeding:

```
FUNCTIONAL:
  ✓ Schedule one-time jobs (run at specific timestamp)
  ✓ Schedule recurring jobs (cron expression: "0 2 * * *")
  ✓ Track job status through full lifecycle
  ✓ Retry failed jobs with exponential backoff, configurable max_retries
  ✓ Cancel / pause / resume scheduled jobs
  ✓ View execution history per job
  ✗ Real-time stream processing (out of scope)
  ✗ Complex multi-stage DAG orchestration (out of scope for v1)

NON-FUNCTIONAL:
  Scale:        1 million scheduled job definitions
  Throughput:   10,000 executions / second
  Latency:      Job starts within 1-2 seconds of scheduled time
  Availability: 99.99% — no silent job drops
  Semantics:    At-least-once execution (jobs must be idempotent)
```

---

## STEP 2 — Capacity Estimation

"Let me do a quick back-of-envelope before designing."

```
JOBS:
  1,000,000 job definitions
  10,000 executions / second
  10,000 × 86,400 seconds/day = 864,000,000 executions/day  (~864M/day)

REDIS SORTED SET (job_queue):
  1,000,000 jobs × ~100 bytes/entry = 100 MB   ← trivial for Redis

HEARTBEAT KEYS:
  At peak: 10,000 concurrent RUNNING jobs
  10,000 × 50 bytes = 500 KB in Redis           ← trivial

CASSANDRA — job_executions:
  864M writes/day → Cassandra handles this comfortably
  Partition key = job_id → hot partition risk for high-frequency jobs
  Mitigated by TIMEUUID clustering key (natural time ordering)

NETWORK — Scheduler Service to Redis:
  Every 30 seconds: ZADD up to (10K × 60s / 30s) = 20K entries
  ZADD bulk is O(N log N) — fine for Redis

STORAGE — payload:
  Job payload avg 1 KB → 1M × 1KB = 1 GB for definitions (Cassandra, fine)
  Large payloads (>64KB) → S3, store S3 key in Cassandra
```

"The numbers are manageable. Redis stays under 1GB easily. Cassandra is the write-heavy store — time-series partitioning handles it."

---

## STEP 3 — Core Entities

"Let me define the core entities before drawing the architecture."

```
Job (definition — lives in Cassandra):
  - job_id          UUID, primary key
  - name            VARCHAR
  - cron_expr       VARCHAR  (null for one-time jobs)
  - job_type        ENUM: CRON | ONE_TIME | DEPENDENT
  - payload         JSON  (or S3 key if large)
  - max_retries     INT
  - timeout_seconds INT
  - status          ENUM: ACTIVE | PAUSED | DELETED
  - next_run_at     TIMESTAMP
  - created_at      TIMESTAMP

JobExecution (one run instance — lives in Cassandra):
  - job_id          UUID     (partition key)
  - execution_id    TIMEUUID (clustering key — time-ordered)
  - worker_id       VARCHAR
  - status          ENUM: SCHEDULED | ENQUEUED | RUNNING | SUCCESS |
                          FAILED | TIMEOUT | CANCELLED | DEAD_LETTER
  - started_at      TIMESTAMP
  - finished_at     TIMESTAMP
  - retry_count     INT
  - error           TEXT

Worker:
  - Stateless. No persisted state. Identity = hostname/pod name.
  - Pulls from Redis. Executes job. Updates Cassandra.

Scheduler Service:
  - Leader-elected. Reads Cassandra. Pushes to Redis.

Monitor Service:
  - Reads Cassandra for stuck jobs. Re-enqueues to Redis.
```

**Job state machine:**
```
SCHEDULED → ENQUEUED → RUNNING → SUCCESS
                              ↘ FAILED → (retry) → RUNNING
                              ↘ TIMEOUT → (retry) → RUNNING
                              ↘ CANCELLED
                              ↘ DEAD_LETTER  (max_retries exceeded)
```

WHY JOB STATES EXIST? (Beginner Explanation)
  Job states are like parcel tracking: ORDERED → SHIPPED → OUT FOR DELIVERY → DELIVERED.
  You always know exactly where your parcel is, and each state only moves to legal next states —
  a delivered parcel cannot go back to "out for delivery."
  Without states, you cannot answer: "Is this job running right now or did it already finish?"
  "Was it ever started?" "Should a worker pick it up or is someone already on it?"
  SCHEDULED = "recorded in the database, not yet in the queue."
  ENQUEUED = "sitting in Redis, waiting for a free worker."
  RUNNING = "a worker is actively executing it right now."
  Each transition is a checkpoint. The Monitor Service depends entirely on state —
  it looks for jobs stuck in RUNNING with no heartbeat update for 90 seconds.
  Without states, the Monitor would have no way to detect a crashed worker's orphaned job.
  Alternative: track only SUCCESS / FAILED with nothing in between.
  Then you can never detect a job that started but never finished — it simply vanishes silently.

---

## STEP 4 — API Design

"Here are the key API endpoints I'd expose from the API Service."

**Create a job:**
```
POST /jobs

Request:
{
  "name": "daily-report-generator",
  "cron_expr": "0 2 * * *",
  "job_type": "CRON",
  "payload": {
    "report_type": "sales",
    "output_bucket": "s3://reports/daily/"
  },
  "max_retries": 3,
  "timeout_seconds": 1800
}

Response 201:
{
  "job_id": "a7f3c891-4b2e-4d8f-9c1a-3e5f7b9d2a4c",
  "name": "daily-report-generator",
  "next_run_at": "2026-08-22T02:00:00Z",
  "status": "ACTIVE"
}
```

**Get job definition:**
```
GET /jobs/{jobId}

Response 200:
{
  "job_id": "a7f3c891-...",
  "name": "daily-report-generator",
  "cron_expr": "0 2 * * *",
  "status": "ACTIVE",
  "next_run_at": "2026-08-22T02:00:00Z",
  "last_execution": {
    "execution_id": "...",
    "status": "SUCCESS",
    "started_at": "2026-08-21T02:00:01Z",
    "finished_at": "2026-08-21T02:14:37Z"
  }
}
```

**Trigger immediately:**
```
POST /jobs/{jobId}/trigger

Response 202:
{
  "execution_id": "b8e4d721-...",
  "job_id": "a7f3c891-...",
  "status": "ENQUEUED",
  "triggered_at": "2026-08-21T09:43:00Z"
}
```

**Get execution history:**
```
GET /jobs/{jobId}/executions?limit=20&page_token=...

Response 200:
{
  "executions": [
    {
      "execution_id": "b8e4d721-...",
      "status": "SUCCESS",
      "started_at": "...",
      "finished_at": "...",
      "retry_count": 0
    },
    ...
  ],
  "next_page_token": "..."
}
```

**Cancel / pause / delete:**
```
POST /jobs/{jobId}/cancel
POST /jobs/{jobId}/pause
POST /jobs/{jobId}/resume
DELETE /jobs/{jobId}
```

**List all jobs:**
```
GET /jobs?status=ACTIVE|PAUSED|DELETED&page_token=...&limit=50

Response 200:
{
  "jobs": [
    {
      "job_id": "a7f3c891-...",
      "name": "daily-report-generator",
      "cron_expr": "0 2 * * *",
      "status": "ACTIVE",
      "next_run_at": "2026-08-22T02:00:00Z"
    },
    ...
  ],
  "next_page_token": "..."
}
```

**Retry a failed job:**
```
POST /jobs/{jobId}/retry

Response 202:
{
  "execution_id": "c9f5e832-...",
  "job_id": "a7f3c891-...",
  "status": "ENQUEUED",
  "retry_count": 1,
  "triggered_at": "2026-08-21T09:50:00Z"
}
```

**Get execution logs:**
```
GET /jobs/{jobId}/executions/{executionId}/logs?page_token=...&limit=100

Response 200:
{
  "execution_id": "b8e4d721-...",
  "job_id": "a7f3c891-...",
  "log_lines": [
    { "timestamp": "2026-08-21T02:00:01Z", "level": "INFO",  "message": "Job started" },
    { "timestamp": "2026-08-21T02:00:05Z", "level": "INFO",  "message": "Processing 42,000 rows..." },
    { "timestamp": "2026-08-21T02:14:37Z", "level": "ERROR", "message": "Connection timeout to DB replica" }
  ],
  "next_page_token": "..."
}
```

> **WHY `GET /jobs`?** Without a list endpoint, operators cannot browse job definitions or filter by status (e.g., "show me all PAUSED jobs"). During incidents, this is the first call an on-call engineer makes — "which jobs are currently ACTIVE and due in the next hour?" Every job management dashboard depends on this endpoint. Pagination via `page_token` is essential at 1M job definitions; offset-based pagination would be slow on Cassandra.

> **WHY `POST /jobs/{jobId}/retry`?** `/trigger` fires the job regardless of its current state — it is an on-demand execution. `/retry` is semantically distinct: it is only valid when the last execution is in `FAILED` or `DEAD_LETTER` state, it increments `retry_count`, and it preserves the audit trail of why the job ran again. Interviewers specifically ask "how does an operator recover a dead-lettered job?" — this is the answer. Without it, recovering a `DEAD_LETTER` job requires calling the internal Monitor Service or manually patching the DB, which is an operational anti-pattern.

> **WHY `GET /jobs/{jobId}/executions/{executionId}/logs`?** The execution history endpoint tells you a job failed; the logs endpoint tells you *why*. In a distributed system where workers are ephemeral pods, stdout/stderr must be persisted centrally (typically to S3 or a log aggregator like CloudWatch/Loki). This endpoint is the API surface over that store. Without it, debugging a failed job requires SSH access to the worker node — which may no longer exist. Interviewers will ask "how would an engineer debug a job that failed at 3am?" — this endpoint is the answer.

---

## STEP 5 — High-Level Architecture

**► DRAW THIS ◄**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     JOB SCHEDULER — HIGH LEVEL ARCHITECTURE                 │
└─────────────────────────────────────────────────────────────────────────────┘

  Clients (REST)
       │
       ▼
┌─────────────────┐
│   API Service   │  CRUD jobs, trigger immediately, view execution history
│  (stateless,    │
│   load balanced)│
└────────┬────────┘
         │  INSERT/UPDATE job definitions
         ▼
┌─────────────────────────────────────────────────────┐
│              CASSANDRA  (Source of Truth)            │
│  ┌──────────────────┐    ┌──────────────────────┐   │
│  │  jobs table      │    │  job_executions table │   │
│  │  (definitions)   │    │  (execution history)  │   │
│  └──────────────────┘    └──────────────────────┘   │
└────────────────────────┬────────────────────────────┘
                         │
         ┌───────────────┴──────────────────┐
         │                                  │
         ▼                                  ▼
┌─────────────────┐               ┌──────────────────┐
│ SCHEDULER SVC   │               │  MONITOR SVC     │
│ (leader-elected)│               │ (background scan)│
│                 │               │                  │
│ Every 30s:      │               │ Every 30s:       │
│ Read jobs due   │               │ Find RUNNING jobs│
│ in next 60s →   │               │ with heartbeat   │
│ ZADD to Redis   │               │ expired (>90s)   │
│                 │               │ → mark FAILED    │
│ Only 1 leader   │               │ → re-enqueue     │
│ via Redis SETNX │               │                  │
└────────┬────────┘               └──────────┬───────┘
         │  ZADD job_queue                   │  ZADD job_queue
         ▼                                   ▼
┌─────────────────────────────────────────────────────┐
│                      REDIS                          │
│                                                     │
│  job_queue   (SORTED SET)                           │
│  ┌─────────────────────────────────────────────┐   │
│  │ score=1724198400  →  job_id: "abc-123"      │   │
│  │ score=1724198401  →  job_id: "def-456"      │   │
│  │ score=1724198460  →  job_id: "ghi-789"      │   │
│  │ ...                                         │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  job_heartbeat:{jobId}  (STRING, EX 90)             │
│  ┌─────────────────────────────────────────────┐   │
│  │ job_heartbeat:abc-123 → "worker-node-04"    │   │
│  │ job_heartbeat:def-456 → "worker-node-07"    │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  scheduler_leader  (STRING, EX 30)                  │
│  ┌─────────────────────────────────────────────┐   │
│  │ scheduler_leader → "scheduler-node-02"      │   │
│  └─────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────┘
                           │  ZPOPMIN (atomic)
                           ▼
┌─────────────────────────────────────────────────────┐
│                   WORKER POOL                        │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Worker 1 │  │ Worker 2 │  │ Worker N │  ...      │
│  │(stateless│  │(stateless│  │(stateless│           │
│  │ pod/node)│  │ pod/node)│  │ pod/node)│           │
│  └──────────┘  └──────────┘  └──────────┘          │
│                                                     │
│  Each worker loop:                                  │
│  1. ZPOPMIN job_queue  → get jobId                  │
│  2. Read job from Cassandra                         │
│  3. SET job_heartbeat:{jobId} self EX 90            │
│  4. Execute job logic                               │
│  5. Renew heartbeat every 30s during execution      │
│  6. UPDATE job_executions status → SUCCESS/FAILED   │
│  7. If CRON: compute next_run, UPDATE jobs.next_run │
└─────────────────────────────────────────────────────┘
         │
         └──► Large payloads: read from S3 (only key stored in Cassandra)
```

WHY WORKER POOL EXISTS? (Beginner Explanation)
  Imagine a restaurant where every time a customer orders, the manager walks into the kitchen,
  personally cooks the meal, then walks back out. The restaurant serves exactly one customer
  at a time. A worker pool is like hiring 20 line cooks always on standby — the manager
  drops a ticket on the rail and any free cook picks it up immediately.
  "Running jobs inline" — inside the scheduler itself — means: while job A runs for 30 minutes,
  every other job is blocked waiting. At 10,000 jobs per second that is catastrophic.
  Workers are stateless — they remember nothing between jobs, share no memory, and can be
  added or removed without reconfiguring anything. Scale to 100 workers by simply starting
  100 processes. Each one calls ZPOPMIN and gets its own independent job to execute.
  The ZPOPMIN atomic pop is the magic: it guarantees two workers never grab the same job,
  so load balancing across the pool is completely automatic — no coordinator needed.
  Alternative: a single-threaded scheduler that runs jobs one by one.
  Works fine for 3 cron jobs. Completely useless at 10,000 executions per second.

---

## STEP 5b — SEQUENCE DIAGRAM

**► DRAW THIS ◄**

**Sequence 1: Job Creation + First Schedule**
```
Client          API Service      Cassandra       Scheduler Svc      Redis
  │                  │               │                 │               │
  │  POST /jobs      │               │                 │               │
  │─────────────────►│               │                 │               │
  │                  │  INSERT job   │                 │               │
  │                  │──────────────►│                 │               │
  │                  │  job_id, OK   │                 │               │
  │                  │◄──────────────│                 │               │
  │  201 job_id      │               │                 │               │
  │◄─────────────────│               │                 │               │
  │                  │               │                 │               │
  │                  │               │  (every 30s)    │               │
  │                  │               │  SELECT jobs    │               │
  │                  │               │  WHERE next_run │               │
  │                  │               │  < now+60s      │               │
  │                  │               │◄────────────────│               │
  │                  │               │  return due jobs│               │
  │                  │               │─────────────────►               │
  │                  │               │                 │  ZADD          │
  │                  │               │                 │  job_queue     │
  │                  │               │                 │  score=ts      │
  │                  │               │                 │───────────────►│
```

**Sequence 2: Job Execution (Happy Path)**
```
Worker          Redis            Cassandra           Job Logic (external)
  │               │                  │                      │
  │  ZPOPMIN      │                  │                      │
  │──────────────►│                  │                      │
  │  jobId        │                  │                      │
  │◄──────────────│                  │                      │
  │               │                  │                      │
  │  READ job definition             │                      │
  │─────────────────────────────────►│                      │
  │  job payload, config             │                      │
  │◄─────────────────────────────────│                      │
  │               │                  │                      │
  │  INSERT execution row (RUNNING)  │                      │
  │─────────────────────────────────►│                      │
  │               │                  │                      │
  │  SET heartbeat EX 90             │                      │
  │──────────────►│                  │                      │
  │               │                  │                      │
  │  execute job logic ─────────────────────────────────────►│
  │               │                  │                      │
  │  (every 30s)  │                  │                      │
  │  SETEX heartbeat EX 90           │                      │
  │──────────────►│                  │                      │
  │               │                  │                      │
  │  job done ◄──────────────────────────────────────────────│
  │               │                  │                      │
  │  UPDATE execution → SUCCESS      │                      │
  │─────────────────────────────────►│                      │
  │               │                  │                      │
  │  (if CRON) UPDATE next_run_at    │                      │
  │─────────────────────────────────►│                      │
```

**Sequence 3: Failure Detection + Recovery**
```
Monitor Svc     Cassandra        Redis            Worker B
  │                 │               │                 │
  │  (every 30s)    │               │                 │
  │  SELECT exec WHERE              │                 │
  │  status=RUNNING AND             │                 │
  │  last_heartbeat > 90s ago       │                 │
  │────────────────►│               │                 │
  │  [stuck: job_id=abc, exec=xyz]  │                 │
  │◄────────────────│               │                 │
  │                 │               │                 │
  │  UPDATE exec xyz → FAILED       │                 │
  │────────────────►│               │                 │
  │                 │               │                 │
  │  ZADD job_queue score=now jobId │                 │
  │─────────────────────────────────────────────────  │
  │                               ──►│                │
  │                                  │ ZADD done      │
  │                                  │                │
  │                                  │  (Worker B loop)
  │                                  │  ZPOPMIN ──────►
  │                                  │  jobId ◄───────│
  │                                  │                │
  │                                  │  NEW execution_id (UUID)
  │                                  │  INSERT → RUNNING
  │                                  │  execute...    │
```

---

## STEP 6 — Database Schema

**► DRAW THIS ◄**

```sql
-- ─────────────────────────────────────────
--   CASSANDRA: jobs table (job definitions)
-- ─────────────────────────────────────────
CREATE TABLE jobs (
    job_id          UUID,
    name            VARCHAR,
    cron_expr       VARCHAR,       -- null for one-time jobs
    job_type        VARCHAR,       -- CRON | ONE_TIME | DEPENDENT
    payload         TEXT,          -- JSON payload or S3 key
    max_retries     INT,
    timeout_seconds INT,
    status          VARCHAR,       -- ACTIVE | PAUSED | DELETED
    next_run_at     TIMESTAMP,
    created_at      TIMESTAMP,
    updated_at      TIMESTAMP,
    PRIMARY KEY (job_id)
);

-- Index by next_run_at for Scheduler Service queries
-- (Cassandra: materialized view or secondary index)
CREATE MATERIALIZED VIEW jobs_by_next_run AS
    SELECT * FROM jobs
    WHERE status = 'ACTIVE' AND next_run_at IS NOT NULL
    PRIMARY KEY (status, next_run_at, job_id);


-- ────────────────────────────────────────────────
--   CASSANDRA: job_executions table (run history)
-- ────────────────────────────────────────────────
CREATE TABLE job_executions (
    job_id          UUID,          -- PARTITION KEY → one partition per job
    execution_id    TIMEUUID,      -- CLUSTERING KEY → time-ordered within partition
    worker_id       VARCHAR,
    status          VARCHAR,       -- SCHEDULED|ENQUEUED|RUNNING|SUCCESS|FAILED|
                                   -- TIMEOUT|CANCELLED|DEAD_LETTER
    started_at      TIMESTAMP,
    finished_at     TIMESTAMP,
    retry_count     INT,
    error           TEXT,
    PRIMARY KEY (job_id, execution_id)
) WITH CLUSTERING ORDER BY (execution_id DESC);  -- newest first


-- ────────────────────────────────────────────────
--   CASSANDRA: running_jobs index (for Monitor Svc)
--   Avoids full scan for stuck jobs
-- ────────────────────────────────────────────────
CREATE TABLE running_jobs (
    shard_date      DATE,          -- PARTITION KEY (e.g., "2026-08-21")
    job_id          UUID,          -- CLUSTERING KEY
    execution_id    TIMEUUID,
    worker_id       VARCHAR,
    started_at      TIMESTAMP,
    PRIMARY KEY (shard_date, job_id)
);
-- Worker inserts row on RUNNING; removes on completion.
-- Monitor queries: SELECT * FROM running_jobs WHERE shard_date = today
-- Then checks Redis heartbeat for each → expired = stuck.


-- ────────────────────────────────────────────────
--   REDIS KEY SPACE
-- ────────────────────────────────────────────────

-- Job queue (sorted set):
--   key:    job_queue
--   member: job_id (UUID string)
--   score:  next_run_unix_timestamp (float)
--
--   ZADD job_queue 1724202000 "a7f3c891-4b2e-..."
--   ZPOPMIN job_queue          → returns lowest-score member
--   ZRANGEBYSCORE job_queue 0 1724202060  → jobs due in next 60s

-- Heartbeat keys:
--   key:    job_heartbeat:{job_id}
--   value:  worker_id string
--   TTL:    90 seconds (auto-expires if worker dies)
--
--   SET job_heartbeat:a7f3c891 "worker-node-04" EX 90

-- Leader election:
--   key:    scheduler_leader
--   value:  scheduler instance id
--   TTL:    30 seconds (must renew every 15s)
--
--   SET scheduler_leader "scheduler-02" NX EX 30

-- Distributed lock (for non-idempotent jobs):
--   key:    job_executing:{job_id}
--   value:  execution_id (UUID)
--   TTL:    timeout_seconds + buffer
--
--   SET job_executing:a7f3c891 "exec-uuid-xyz" NX EX 1800
```

---

## STEP 6b — ER RELATIONSHIP DIAGRAM

**► DRAW THIS ◄**

```
┌─────────────────────────────────────────────────────────────────┐
│                        ER DIAGRAM                               │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────┐         ┌──────────────────────────────┐
│         jobs             │         │       job_executions         │
├──────────────────────────┤         ├──────────────────────────────┤
│ PK  job_id    UUID       │ 1     N │ PK  job_id        UUID      │
│     name      VARCHAR    ├─────────┤ PK  execution_id  TIMEUUID  │
│     cron_expr VARCHAR    │         │     worker_id     VARCHAR   │
│     job_type  ENUM       │         │     status        ENUM      │
│     payload   TEXT       │         │     started_at    TIMESTAMP │
│     max_retries  INT     │         │     finished_at   TIMESTAMP │
│     timeout_sec  INT     │         │     retry_count   INT       │
│     status    ENUM       │         │     error         TEXT      │
│     next_run_at TIMESTAMP│         └──────────────────────────────┘
│     created_at TIMESTAMP │
└──────────────────────────┘

         │                           ┌──────────────────────────────┐
         │                           │        running_jobs          │
         │                           │    (Monitor Service index)   │
         │ 1                     N   ├──────────────────────────────┤
         └───────────────────────────┤ PK  shard_date  DATE        │
                                     │ PK  job_id      UUID        │
                                     │     execution_id TIMEUUID   │
                                     │     worker_id   VARCHAR     │
                                     │     started_at  TIMESTAMP   │
                                     └──────────────────────────────┘


  REDIS (not relational, but shown for completeness):

  job_queue (ZSET)              job_heartbeat:{job_id} (STRING)
  ┌────────────────────┐        ┌──────────────────────────────┐
  │ score │  job_id    │        │ value: worker_id             │
  │───────┼────────────│        │ TTL:   90 seconds            │
  │ 1724… │ abc-123    │        └──────────────────────────────┘
  │ 1724… │ def-456    │
  │ 1724… │ ghi-789    │        scheduler_leader (STRING)
  └────────────────────┘        ┌──────────────────────────────┐
                                 │ value: scheduler instance id │
                                 │ TTL:   30 seconds            │
                                 └──────────────────────────────┘
```

---

## STEP 7 — Deep Dive: Exactly-Once Execution

"This is the hardest part of the design. Let me walk through exactly what happens during a crash."

WHY AT-LEAST-ONCE VS EXACTLY-ONCE MATTERS? (Beginner Explanation)
  Think of a postal guarantee. "At-least-once delivery" = your letter arrives, but occasionally
  a duplicate copy also arrives because the carrier was not sure the first one got through.
  "Exactly-once delivery" = guaranteed single arrival, but the postal service now needs
  synchronised tracking across every truck, depot, and carrier — enormously complex and costly.
  In distributed systems, servers crash, networks partition, and clocks drift. Guaranteeing
  a job runs exactly once across all these failures requires distributed transactions — the
  engineering cost is extremely high and correctness is difficult to prove.
  At-least-once is the pragmatic choice: accept that a job may run twice on a crash/recovery,
  but make each job smart enough to detect and skip duplicate work (idempotency).
  Implementing idempotency is usually a few lines per job type — doable in an afternoon.
  Exactly-once infrastructure (distributed locks + idempotency keys + rollback) takes months.
  Reserve exactly-once (via Redis SETNX lock) only for jobs that truly cannot deduplicate
  themselves — legacy payment processors, third-party APIs with no dedup support, etc.

**The problem:**
```
t=0:00  Worker A picks up job123 via ZPOPMIN
t=0:01  Worker A starts executing, sets heartbeat EX 90
t=0:30  Worker A renews heartbeat
t=1:00  Network partition — Worker A disconnected from Redis
t=1:30  Heartbeat expires (90s TTL)
t=1:31  Monitor detects expired heartbeat → re-enqueues job123
t=1:32  Worker B picks up job123 via ZPOPMIN, starts execution
t=2:00  Worker A's network recovers — continues executing job123
t=2:30  BOTH Worker A and Worker B may complete job123
```

**Two executions exist. How do we handle this?**

**Solution 1: Idempotent jobs (preferred)**
```
- Each run gets a unique execution_id (UUID)
- Job logic checks: "Was this execution_id already processed?"
- Example: "send email" → check emails table for job_id + date → if exists, skip
- Example: "generate report" → check S3 for output key → if exists, skip
- Worker A and Worker B both complete. Both create execution records.
  The job's business outcome is identical (email sent once, report generated once).
```

**Solution 2: Distributed lock for non-idempotent jobs**
```
Before executing:
  SET job_executing:{jobId} {execution_id} NX EX {timeout+buffer}

If NX succeeds:  This worker holds the lock. Proceed with execution.
If NX fails:     Another worker is already executing. Skip / return.

Worker A holds lock.
Worker B's SETNX fails → Worker B skips.
Worker A completes → DEL job_executing:{jobId}.

Risk: Worker A crashes holding the lock.
      Lock auto-releases after TTL.
      Monitor re-enqueues.
      Next Worker C picks up, acquires lock, executes.

Mark job as idempotent=true or idempotent=false at definition time.
Idempotent=false → system automatically uses distributed lock.
```

**Retry logic with exponential backoff:**
```
Attempt 1: immediate
Attempt 2: 1 second delay
Attempt 3: 2 second delay
Attempt 4: 4 second delay
...
Attempt max_retries+1: status = DEAD_LETTER
                        alert fired to ops team
                        manual intervention required
```

---

## STEP 8 — Trade-offs

| Decision | Choice | Trade-off |
|----------|--------|-----------|
| **Queue store** | Redis sorted set | Fast + atomic `ZPOPMIN` vs. not durable. If Redis crashes, in-flight enqueued jobs are lost. Mitigated: Cassandra is source of truth; Scheduler Service re-enqueues on startup. |
| **Execution semantics** | At-least-once | Simpler than exactly-once. Allows easy horizontal scaling. Requires jobs to be idempotent — discipline required from job authors. |
| **Scheduler topology** | Single leader | No thundering herd, no duplicate enqueues. Single point of failure — mitigated by fast failover (TTL = 30s, gap is tolerable for most batch jobs). |
| **Heartbeat interval** | 30s (TTL 90s) | Faster detection (< 2 min) vs. more Redis writes per running job. 3 missed heartbeats before timeout = 3x safety margin. |
| **Retry strategy** | Exponential backoff | Avoids thundering herd when downstream service is down. Slower recovery for time-sensitive jobs — tradeoff accepted. |
| **Payload storage** | S3 for large, Cassandra for small | Large payloads in ZSET would slow `ZPOPMIN` and bloat Redis. S3 adds latency per job start. Threshold: 64KB. |
| **Execution history** | Cassandra time-series per job | O(1) reads for history of a specific job. No index needed. Job with 10K executions/day → large partition (use TTL to prune old executions). |

---

## STEP 9 — Scalability

**BOTTLENECK 1 — Midnight batch spike (thundering herd)**
```
Problem:  10,000 cron jobs all set to "0 0 * * *" (midnight).
          All due at the same second → 10K ZPOPMIN in 1 second.
          Workers overwhelmed, downstream services DDoS'd.

Solution: Jitter at schedule time.
          next_run = cron_computed_time + random_jitter(0, 300 seconds)
          
          Deterministic jitter: jitter = hash(job_id) % 300
          Same job always gets same jitter offset → predictable spread.
          
          Result: 10,000 jobs spread over 5 minutes = ~33 jobs/sec.
          Workers drain steadily.
```

**BOTTLENECK 2 — ZPOPMIN throughput**
```
Problem:  10,000 executions/sec → 10,000 ZPOPMIN/sec on Redis.
          Redis is single-threaded for atomic ops.

Reality:  Redis processes ~100K-1M simple ops/sec on modern hardware.
          10K ZPOPMIN/sec is well within capacity.
          
Mitigation if needed:
  - Use ZPOPMIN with COUNT argument: pop 10 at once per worker iteration.
  - Redis Cluster: shard job_queue by job_type or partition key.
    (Loses global time ordering across shards — acceptable if priority
     is within type, not across all jobs globally.)
```

**BOTTLENECK 3 — Monitor Service polling for stuck jobs**
```
Problem:  Monitor scans for RUNNING jobs with expired heartbeat.
          Naive approach: SELECT * FROM job_executions WHERE status='RUNNING'
          → full table scan across partitions → Cassandra hates this.

Solution: running_jobs index table.
          Partition key = shard_date (e.g., "2026-08-21")
          Clustering key = job_id
          
          Worker A starts → INSERT into running_jobs.
          Worker A finishes → DELETE from running_jobs.
          Monitor: SELECT * FROM running_jobs WHERE shard_date = today()
          → single partition read → fast.
          Then cross-check Redis heartbeat: GET job_heartbeat:{job_id}
          If nil → job is stuck → re-enqueue.
```

**BOTTLENECK 4 — Large job payloads**
```
Problem:  Job payload stored inline in Cassandra and passed through Redis.
          A 10MB payload in ZSET member → slow ZPOPMIN, huge Redis memory.

Solution: Payload tiering.
          payload_size < 64KB → store inline in jobs.payload (Cassandra)
          payload_size >= 64KB → upload to S3
                                  store S3 key in jobs.payload
          
          Worker reads job → if payload starts with "s3://" → fetch from S3.
          ZPOPMIN passes only job_id → tiny → fast.
          Cassandra row stays lean.
```

---

---

## STEP 10 — ARCHITECTURE VARIANT B: PostgreSQL + Kafka + Watcher (from image)

> The guide above uses Cassandra + Redis ZPOPMIN. This is the **PostgreSQL + Kafka** variant shown in the design image. Both are valid — know both.

```
VARIANT B — HIGH LEVEL (from image):

  clients/users
       │
       ▼
  LB + API Gateway
  (authentication & authorization, rate limiting, routing)
       │
       ▼
  Job Svc  ──────────────────────►  Job DB (PostgreSQL)
                                         ▲
  Job Executor  ◄── pull jobs ──────────┘
       │
       └──────── update status of the job ──────────► Job DB


VARIANT B — LOW LEVEL (from image):

  clients/users
       │
       ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  LB + API Gateway                                                │
  │  (authentication & authorization, rate limiting, routing)        │
  └────────────────────────────────────────────────────────────────  │
       │ submit/edit the jobs
       ▼
  ┌────────────┐       ┌───────────────┐
  │  Job Svc   │       │ Job Search Svc│ ◄── read from Job DB
  └──────┬─────┘       └───────────────┘
         │ read/write
         ▼
  ┌────────────────────────────────────────────────────────────┐
  │             Job DB (Postgres)                              │
  │                                                            │
  │  Jobs table:                  Job_runs table:             │
  │  - id (index)                 - id                        │
  │  - name                       - job_id (index)            │
  │  - schedule_type              - status (index)            │
  │  - schedule_time (partition)    [queued/running/          │
  │  - status                        success/failed]          │
  │    [paused/scheduled/cancel]  - start_time                │
  │  - cron_expression            - end_time                  │
  │  - payload                    - modified_time (index) ◄── │
  │  - retries (3)                - executor_id               │
  │  - meta                       - attempt_number            │
  └────────────────────────────────────────────────────────────┘
         ▲                      ▲
         │ -read 20s            │ Consumer Svc writes
         │                      │
  ┌──────────────┐       ┌──────────────┐     ┌──────────────────────┐
  │   watcher    │       │ Consumer Svc │     │     Kafka            │
  │              │       └──────────────┘     │                      │
  │ Checks:      │              ▲             │  topic: run          │
  │ last_polled_ │──────────────┘ write       │  topic: retry        │
  │ time (Redis) │                            │  topic: dead         │
  │              │──── push to ──────────────►│  topic: cancel       │
  │ POLL LOGIC:  │     kafka                  │  topic: completed    │
  │ Every 10/20s │                            └──────────┬───────────┘
  │ Pull jobs in │                                       │
  │ [now,now+5m] │                                       ▼
  │ → mark Queued│                              ┌────────────────────┐
  │              │                              │  Job Consumer Svc  │
  │ STUCK CHECK: │                              └──────────┬─────────┘
  │ status=runnin│                                         │ dispatch
  │ AND modified_│                                         ▼
  │ time > 15s   │                         ┌──────────────────────────┐
  │ → reschedule │                         │  Executor Svc (1-100)    │
  └──────────────┘                         │  Executor Svc            │
         │                                 │  Executor Svc            │
         ▼                                 │  Executor Svc            │
       Redis                               │  Executor Svc      ──────┼──► Redis
  (last_polled_time)                       │  Executor Svc            │    job: 1232
                                           └──────────────────────────┘    request: cancel
                                                    │                       TTL
                                                    │ failed job back to kafka for retry
                                                    ▼
                                                 Kafka (retry topic)

KEY DIFFERENCES vs Variant A (Cassandra+ZPOPMIN):
  ┌────────────────────┬──────────────────────────┬──────────────────────────┐
  │ Aspect             │ Variant A (guide above)   │ Variant B (image/blog)   │
  ├────────────────────┼──────────────────────────┼──────────────────────────┤
  │ DB                 │ Cassandra                 │ PostgreSQL               │
  │ Queue              │ Redis sorted set ZPOPMIN  │ Kafka topics             │
  │ Scheduling         │ Leader-elected Scheduler  │ Watcher + last_polled_time│
  │ Watcher interval   │ 30s look-ahead            │ 10/20s, [now, now+5min]  │
  │ Stuck detection    │ Heartbeat TTL (90s Redis) │ modified_time > 15s ago  │
  │ Executor count     │ N stateless workers       │ 1-100 Executor Svcs      │
  │ Cancel signal      │ Kafka cancel topic        │ Redis key + TTL          │
  │ runNow path        │ ZADD immediate score      │ push directly to queue   │
  └────────────────────┴──────────────────────────┴──────────────────────────┘

WATCHER QUERY (Variant B):
  -- Fetch jobs ready to run
  SELECT * FROM jobs
  WHERE schedule_time <= NOW() + INTERVAL '5 minutes'
    AND status = 'scheduled'
    AND last_polled_time < NOW() - INTERVAL '30 seconds'
  LIMIT 1000

  -- Stuck job detection
  SELECT * FROM job_runs
  WHERE status = 'running'
    AND modified_time < NOW() - INTERVAL '15 seconds'
  → reschedule these back to Kafka retry topic

REDIS CANCEL KEY PATTERN (Variant B):
  When user calls POST /jobs/{jobId}/cancel:
    → Job Svc writes to Redis: key = "job: {jobId}", value = "request: cancel", TTL = 60s
    → Executors poll Redis for their current job's cancel key every few seconds
    → If cancel key exists → executor sends SIGTERM → marks job 'cancelled'
    → Redis key auto-expires after TTL (cleanup)

RUNOW / IMMEDIATE EXECUTION (Variant B):
  POST /jobs/{jobId}/runNow
    → Bypasses watcher completely
    → Job Svc pushes job directly into Kafka 'run' topic
    → Job Consumer Svc receives → dispatches to available Executor Svc
    → No waiting for watcher poll cycle
```

---

## STEP 11 — ALTERNATIVE APPROACHES (from blog)

```
APPROACH 1: Event-Driven (Amazon EventBridge)
  Concept:         Jobs triggered by events instead of time-based polling
  Implementation:  EventBridge rules match cron expressions → trigger Lambda or SQS
  Pros:            Serverless, auto-scaling, no polling overhead, pay-per-execution
  Cons:            Vendor lock-in (AWS), limited to 300 targets per rule, cold start latency
  Use case:        Simple scheduled tasks, cloud-native architectures

APPROACH 2: Managed Service (AWS Step Functions, Temporal)
  Concept:         Workflow orchestration as a service
  Implementation:  Define workflows as JSON (Step Functions) or code (Temporal)
                   Service handles execution, retry, state management
  Pros:            No infrastructure management, built-in monitoring,
                   durable execution (survives crashes mid-execution)
  Cons:            Cost (per state transition), learning curve, less control
  Use case:        Complex workflows, enterprise applications, long-running sagas

APPROACH 3: Custom with Delay Queue (Amazon SQS, RabbitMQ)
  Concept:         Use message queue's delay feature to schedule jobs
  Implementation:  Publish message with delay = (scheduled_time - now)
                   Consumer picks up when delay expires
  Pros:            Simple, leverages existing queue, supports priorities
  Cons:            SQS max delay = 15 minutes (need rescheduling for longer),
                   no native cron support, poor for recurring jobs
  Use case:        One-time delayed jobs, reminder systems

WHEN TO USE EACH:
  Proprietary SaaS, AWS-native, simple tasks → EventBridge
  Complex multi-step workflows, durable execution → Temporal / Step Functions
  Custom control, high throughput, cron + retry → Variant A (Redis ZSET) or Variant B (Postgres+Kafka)
  One-time delays only, simple → SQS delay queue

NOTE from image: Redis Sorted Set and Amazon SQS are listed as alternatives to the
Kafka-based queue in Variant B — specifically "SQS (support scheduling at exact time stamp)".
```

---

WHY PRIORITY QUEUES EXIST? (Beginner Explanation)
  At an ER, a patient with a broken finger waits while doctors treat a heart attack victim —
  even if the broken finger patient arrived first. Priority queues apply the same logic to jobs.
  Without priorities, a low-priority "generate monthly analytics CSV" job queued at 10,000
  jobs/second could delay the high-priority "send 2FA login code" job a user is waiting on
  right now. That is a terrible user experience.
  Separate queues per priority level = separate pools of workers dedicated to each tier.
  High-priority gets more workers and is polled first; low-priority runs when spare capacity exists.
  The aging mechanism (boost priority after waiting 1 hour) prevents starvation: a low-priority
  job does not wait forever just because high-priority jobs keep arriving.
  Alternative: one queue, first-come-first-served. Simple, but completely ignores business
  importance — your real-time billing job waits behind someone's weekly background report.

## STEP 12 — PRIORITY SCHEDULING (from blog)

```
PRIORITY QUEUE SYSTEM:
  Jobs have priority field: 1–10 (10 = highest)

  VARIANT B (Kafka-based) — Separate topics per priority level:
  ┌────────────────────┬───────────────────────┬──────────────────────┐
  │ Priority           │ Kafka Topic           │ Consumer Instances   │
  ├────────────────────┼───────────────────────┼──────────────────────┤
  │ High   (8-10)      │ high_priority_run     │ 50 instances         │
  │ Medium (5-7)       │ medium_priority_run   │ 30 instances         │
  │ Low    (1-4)       │ low_priority_run      │ 20 instances         │
  └────────────────────┴───────────────────────┴──────────────────────┘

  VARIANT A (Redis ZSET) — Separate queues per priority:
    ZADD job_queue_high  score job_id   (workers poll high first)
    ZADD job_queue_med   score job_id
    ZADD job_queue_low   score job_id

  STARVATION PREVENTION:
    If low-priority job waiting > 1 hour → temporarily boost to medium
    (aging algorithm: priority += 1 for every 30min waiting)

  EXAMPLE:
    Job A (priority 9) and Job B (priority 3) scheduled at same time:
    → A → high_priority_run topic → 50 consumers → starts in <1s
    → B → low_priority_run topic → 20 consumers → waits 5s for executor

  TRADE-OFF:
    More topics = more operational complexity but better isolation
    Single topic = simpler but consumers need priority-aware polling logic
```

---

## STEP 13 — COMPLETE REDIS + KAFKA KEY REFERENCE (from blog)

```
REDIS KEYS (complete list):

  lock:job:{job_id}:schedule      STRING {watcher_id}  NX EX 60
    → Distributed lock: prevents two watchers scheduling same job

  executor:{executor_id}:heartbeat STRING {timestamp}  updated every 10s
    → Health check: if > 60s stale → executor marked unhealthy

  executors:available             HASH {executor_id: active_job_count}
    → Load balancing: Job Consumer Svc checks before dispatching

  job:{job_id}:cache              HASH (cached job definition, TTL: 5 min)
    → Reduces DB reads by 90% for executor job definition lookups

  last_poll_time                  STRING timestamp of last successful watcher poll
    → Backfill detection: on watcher restart, compare vs now to find missed jobs

  job: {job_id} (Variant B cancel) STRING "request: cancel"  TTL: 60s
    → Cancellation signal: executor polls this key, sends SIGTERM if present


KAFKA TOPICS (complete list):

  run        Jobs ready for immediate execution    10 partitions by job_id
  retry      Failed jobs with remaining retries    5 partitions
  dead       Permanently failed jobs               1 partition (low volume)
  cancel     Cancellation requests for running     3 partitions
  completed  Job completion events for downstream  10 partitions

  Retention: 7 days on all topics (allows replay/backfill)

  PARTITION STRATEGY:
    Partition by job_id → same job's messages always go to same partition
    Guarantees ordering (retry for job X processed in order)
    Prevents race conditions between retry and run messages for same job
```

---

## WHAT NOT TO SAY ✗

```
✗ "Use Kafka as the job queue" (when using time-based scheduling)
  → Kafka is FIFO. It cannot answer "give me all jobs due RIGHT NOW
    regardless of when they were enqueued." You'd need ZRANGEBYSCORE.
    CLARIFICATION: Kafka IS valid when paired with a watcher that polls DB
    for due jobs and pushes them to Kafka (Variant B). The trap is saying
    Kafka alone replaces a time-ordered queue — you still need the DB poll.

✗ "Just use a cron daemon on a single server"
  → Single point of failure. Server restarts = missed jobs.
    No distribution. Doesn't scale to 10K executions/sec.

✗ "Poll the database every second for due jobs"
  → 1,000,000 jobs × SELECT/sec = catastrophic DB load.
    Use a look-ahead window (60s) polled every 30s. Redis queue buffers.

✗ "At-most-once execution is fine"
  → Missing a scheduled job (billing run, report, ETL) is usually
    worse than running it twice. At-least-once + idempotency is the
    standard. Only use at-most-once for truly fire-and-forget metrics.

✗ "Store large payloads in the job record / Redis queue"
  → Bloats Redis. Slows ZPOPMIN. Wastes memory.
    S3 for anything over 64KB. Store only the S3 key in Cassandra.

✗ "Each Scheduler node independently enqueues jobs"
  → Multiple enqueues = same job appears in Redis N times = N workers
    execute the same job. Use leader election — only one node enqueues.
```

---

## SENIOR TRAP QUESTIONS (15 YOE Level)

### CATEGORY 1 — EXACTLY-ONCE EXECUTION

**Q: "Worker A picks up job123. Network partitions for 3 minutes. Monitor re-enqueues. Worker B executes. Worker A's network recovers. What happens?"**

A: "Worker A's execution_id is a UUID generated when it started. Worker B gets a different UUID. Both may complete. The system records two execution rows in job_executions — they have different execution_ids.

If the job is idempotent — say it generates a report and uploads to S3 — the second run just overwrites with the same output. No harm.

If the job is NOT idempotent — say it charges a customer's credit card — we have a double-charge problem.

Solution: the job definition has an idempotent flag. For idempotent=false jobs, we use a distributed lock:

`SET job_executing:{jobId} {execution_id} NX EX {timeout}`

NX means only one worker can acquire it. Worker B's SETNX returns 0 (fails) while Worker A holds the lock. Worker B skips.

If Worker A crashes holding the lock: TTL auto-releases. Monitor re-enqueues. Worker C acquires the lock cleanly.

The guarantee: at any point, at most one lock holder is actively executing the job. Combined with the heartbeat TTL, we get effectively-exactly-once for non-idempotent jobs."

---

**Q: "Scheduler leader crashes at 2:59am. The 3am cron jobs are never enqueued. How do you handle this?"**

A: "Two mechanisms.

First, failover speed. The leader lock TTL is 30 seconds. When the leader crashes, its lock expires within 30 seconds. A follower Scheduler instance polls for the lock, acquires it via SETNX, and becomes the new leader.

Second, look-back window on startup. When the new leader takes over, it doesn't just look ahead — it queries Cassandra for jobs where:

`next_run_at BETWEEN (now - 5 minutes) AND now`

Any jobs that were due in the past 5 minutes and never picked up (no execution record, or execution status = SCHEDULED not ENQUEUED) get re-enqueued immediately.

The gap is at most 30 seconds (the lock TTL). For most batch jobs, a 30-second delay is completely acceptable. If sub-second accuracy is critical, you'd reduce the TTL to 10 seconds, accepting more frequent leader renewals.

For the 3am scenario: new leader starts at 2:59:30. It runs look-back, finds 3am jobs due in 30 seconds, ZADDs them. Workers pick them up at 3:00:30. One-minute delay worst case. Fine."

---

**Q: "Two Scheduler instances both think they're the leader simultaneously (split-brain). What happens?"**

A: "This is the classic split-brain scenario. It can happen if the leader's Redis connection is slow but not broken — it stops renewing but is still running.

SETNX with TTL gives us a window where both think they're leader: old leader's TTL hasn't expired yet, new leader hasn't won the lock. In that window, only the old leader is active.

After the TTL expires, only one can win SETNX. Redis is a single process — SETNX is atomic. There's no scenario where both get NX=1 simultaneously.

The true split-brain risk is: old leader wins lock, but enqueues a job twice due to retry on network error. Solution: make ZADD idempotent — `ZADD NX` (don't update score if member already exists). So even if the same jobId is ZADD'd twice by a confused leader, it only appears once in the sorted set with one score. ZPOPMIN gives one worker one copy."

---

### CATEGORY 2 — SCALE

**Q: "All 10,000 cron jobs are set to '0 2 * * *' (2am daily). How do you prevent thundering herd?"**

A: "Jitter injection at scheduling time. When computing the next_run from the cron expression, we don't use the raw cron timestamp. Instead:

`next_run = cron_next_time + jitter`

where `jitter = hash(job_id) % max_jitter_seconds`

With max_jitter = 300 seconds, 10,000 jobs spread uniformly over 5 minutes. That's ~33 jobs/second instead of 10,000/second spike.

The jitter is deterministic — seeded by job_id hash. So the same job always fires at the same offset past the hour. Operators can reason about it: 'this job always fires at 2:03:47.' It's not random noise each time.

I'd expose a max_jitter_seconds setting per job definition — maybe default 300s, configurable to 0 if the operator needs precise timing."

---

**Q: "Your Scheduler looks ahead 60 seconds and runs every 30 seconds. What about jobs due in the 'gap' between runs?"**

A: "The 60-second look-ahead window always overlaps with the previous run's window. If the Scheduler runs at T=0 (enqueueing jobs due T+0 to T+60) and again at T=30 (enqueueing jobs due T+30 to T+90), there's a 30-second overlap zone (T+30 to T+60) where both runs try to enqueue the same jobs.

This is handled by `ZADD NX` — we only add a job_id to the sorted set if it's not already there. No duplicates.

Alternatively, once a job is enqueued (status = ENQUEUED in Cassandra), the Scheduler skips it next iteration. The Scheduler checks: for each due job, does an ENQUEUED or RUNNING execution already exist? If yes, skip. This is more expensive (Cassandra read per job) but more conservative.

In practice, `ZADD NX` is sufficient and cheaper."

---

**Q: "Cassandra's job_executions partition for a high-frequency job will be enormous. How do you handle hot partitions?"**

A: "Right — a job running 10K times/second would create a single partition with 864M rows/day. That's a Cassandra anti-pattern.

Solutions:

Option 1 — Time-bucket the partition key: `job_id + date_bucket`. E.g., partition key = `(job_id, date)`. Each day's executions are a separate partition. Partition size = executions per day per job — manageable.

Option 2 — Add a shard suffix: `job_id_shard = job_id + (execution_id_hash % N)`. Creates N partitions per job. Reads need to fan out across N shards — slightly more complex queries.

Option 3 — For extremely high-frequency jobs, store execution summary in Cassandra (hourly aggregates) and stream raw events to a data warehouse (Redshift/BigQuery) for deep history. API returns summary from Cassandra for recent, warehouse for historical.

I'd start with Option 1 (date-bucket) — it matches the natural query pattern ('show me executions for job X on August 21st') and keeps partition sizes bounded by day."

---

### CATEGORY 3 — FAILURE MODES

**Q: "Job takes 10 hours but timeout is 30 minutes. Worker killed after 30 min. Job re-enqueued. Runs again. Killed again. Infinite retry loop. How do you prevent this?"**

A: "Retry count tracked in job_executions. Each time a job is re-enqueued by the Monitor, we increment retry_count.

When retry_count reaches max_retries: status = DEAD_LETTER. The job is NOT re-enqueued. An alert fires to the ops team (PagerDuty, Slack, whatever the alerting stack is). The job requires manual investigation before it can be re-triggered.

This stops the infinite loop. Resources aren't burned forever.

For the specific scenario of a 10-hour job with a 30-minute timeout — that's a configuration error. The alert message should include: 'Job exceeded timeout (execution lasted longer than timeout_seconds). Consider increasing timeout_seconds for this job type.'

Bonus: you can add a TIMEOUT state distinct from FAILED. FAILED = job threw an exception. TIMEOUT = job exceeded timeout_seconds. Different alerts, different investigation paths."

---

**Q: "Worker pool auto-scales. New workers come up during a job execution spike. They start hammering Redis with ZPOPMIN. At what point does this hurt Redis?"**

A: "Redis single-threaded throughput for simple ops is roughly 100K-1M ops/sec on modern hardware. 10K ZPOPMIN/sec is 1-10% of Redis capacity. Auto-scaling to 50K workers would push it to 50K ZPOPMIN/sec — still within range.

The real concern is ZPOPMIN latency under lock contention — multiple workers blocked waiting for atomic access to the same sorted set. At very high concurrency (>100K workers), this becomes latency-sensitive.

Mitigations:
1. Batch ZPOPMIN: `ZPOPMIN job_queue 10` — each worker gets 10 jobs per call. 10x reduction in Redis round trips.
2. Shard the queue: job_queue_high, job_queue_medium, job_queue_low (priority shards). Workers check high first.
3. Redis Cluster: shard by job_type. Different job types on different Redis nodes. Linear scale.

For our scale (10K exec/sec), single Redis is fine. I'd add sharding at 100K+ exec/sec."

---

**Q: "Monitor Service is down for 2 hours. Workers crash during that time. What's the state of the system when Monitor comes back?"**

A: "Two hours of crashed workers without Monitor means potentially hundreds of jobs stuck in RUNNING with expired heartbeats.

When Monitor restarts:
1. It scans running_jobs for today's date partition.
2. For each row, checks Redis heartbeat. All are nil (expired 2 hours ago).
3. Marks all as FAILED in job_executions.
4. ZADDs all back to Redis job_queue with score = now (immediate execution).

Problem: if 1,000 jobs are stuck, all 1,000 get re-enqueued simultaneously. Workers spike. Thundering herd on restart.

Solution: Monitor re-enqueues with staggered timestamps:
`re_enqueue_time = now + (index * 100ms)`

Spreads 1,000 jobs over 100 seconds rather than all at once. Workers drain steadily.

Also: Monitor should have a circuit breaker. If it detects an abnormally large stuck-job count (>10x normal), it alerts before re-enqueueing, in case the root cause is still active (workers are still crashing)."

---

**Q: "How do you handle time zone conversions for scheduled jobs?"**

A: "All timestamps in the database are stored as UTC. When a user creates a job, they supply a timezone:

```
{ schedule: '0 0 * * *', timezone: 'America/New_York' }
```

The backend converts to UTC using a timezone library (pytz in Python):
cron '0 0 * * *' in EST (UTC-5) → stored as '0 5 * * *' UTC.

When displaying to the user, we convert back from UTC to their local timezone.

The watcher always works in UTC — it never needs timezone awareness.

The hard case is DST: if a user schedules '2 AM EST daily' and that's the day clocks spring forward — 2am doesn't exist. Options:
1. Skip to 3am (next valid time)
2. Run at 1am (previous valid time)
3. Make this configurable per job (preferred)

We recalculate next_run_time whenever DST changes (March and November in the US).

For Variant B (PostgreSQL): store `timezone` column in Jobs table. Watcher converts to UTC on every poll. For Variant A (Cassandra): same pattern — all stored as UTC, conversion happens at create-time and display-time only."

---

**Q: "What's the difference between FAILED and TIMEOUT states? Why have both?"**

A: "FAILED means the job threw an exception or returned a non-zero exit code — the job code itself broke.

TIMEOUT means the job ran longer than timeout_seconds (e.g., 3600s default) — the job was forcibly killed, not because it failed but because it didn't finish in time.

These need different responses:
- FAILED → investigate the error_msg, fix code, retry
- TIMEOUT → the job may be correct but too slow. Options: increase timeout, optimize job, break into smaller chunks.

In the DB, the status enum includes:
SCHEDULED → ENQUEUED → RUNNING → SUCCESS
                              ↘ FAILED        (exception/error)
                              ↘ TIMEOUT       (exceeded timeout_seconds)
                              ↘ CANCELLED     (user requested)
                              ↘ DEAD_LETTER   (max_retries exceeded)
                              ↘ EXECUTOR_DIED (executor crashed mid-run)

Monitoring alerts separately on TIMEOUT vs FAILED — different runbooks."

---

**Q: "What are your alerting thresholds for the monitoring system?"**

A: "Multi-level alerting:

  Single job failure rate:  > 50% failure rate (6 of last 10 runs failed) → CRITICAL alert
  System failure rate:      > 10% failure rate overall in 1 hour → WARNING alert
  Dead letter queue:        > 100 messages in dead topic → CRITICAL (systemic issue)
  Executor capacity:        < 30% healthy executors remaining → CRITICAL (capacity crisis)
  SLA breach:               job end_time - scheduled_at > SLA threshold → SLA alert
  Queue depth:              > 10K jobs backlogged in run topic → LATENCY alert

Alert channels:
  PagerDuty: critical alerts (single job failed 5+ times, executor pool <30%)
  Slack:     warnings (system rate >10%, queue depth spike)
  Email:     daily digest of all failures + dead letter summary

Dashboard metrics (Grafana):
  Jobs by status (pie): scheduled / running / success / failed / dead
  Execution time trend (line graph): avg duration per job type over 24h
  Failure reasons (bar): top 10 error messages
  Executor utilization (gauge): active / idle / unhealthy executor counts"

---

# ═══════════════ KEY NUMBERS ═══════════════

```
┌─────────────────────────────────────────────────────────────────┐
│                   KEY NUMBERS — MEMORIZE THESE                  │
└─────────────────────────────────────────────────────────────────┘

Scale:
  1,000,000    scheduled job definitions
  10,000       executions per second
  864,000,000  executions per day (10K × 86,400)
  100–1000     executor instances for parallel execution

Redis (Variant A — Redis ZPOPMIN):
  100 MB       job_queue ZSET size (1M jobs × 100 bytes)
  500 KB       heartbeat keys at peak (10K concurrent × 50 bytes)
  30 s         scheduler_leader lock TTL
  90 s         job_heartbeat TTL
  30 s         heartbeat renewal interval (3× before expiry)

Redis (Variant B — PostgreSQL+Kafka):
  60 s         lock:job:{job_id}:schedule TTL (distributed lock)
  10 s         executor heartbeat update interval
  60 s         executor marked unhealthy (3 missed × 10s heartbeats = 30s lag + buffer)
  5 min        job:{job_id}:cache TTL (job definition cache)
  60 s         Redis cancel key TTL (job: {id}, request: cancel)

Scheduler / Watcher:
  Variant A:   60 s look-ahead, 30 s poll interval
  Variant B:   10/20 s poll interval, [now, now+5min] window
  Variant B:   15 s → modified_time threshold to detect stuck running jobs
  5 min        look-back window on leader failover (Variant A)
  < 30 s       max job delay on leader failover (= lock TTL)
  1000         max jobs fetched per watcher poll (batch processing)

Retry & Recovery:
  3            default retry count (4 total attempts)
  formula:     retry_delay = base_delay × (2 ^ attempt) + random(0, base_delay/2)
  example:     attempt 1 → 60s, attempt 2 → 120s+jitter, attempt 3 → 240s+jitter
  DEAD_LETTER  status after max_retries exceeded
  30 s         SIGTERM grace period before SIGKILL on cancellation
  3600 s       default job timeout (1 hour), configurable per job
  100 jobs/sec backfill rate (controlled, to avoid overloading executors)

Jitter:
  0–300 s      jitter window for thundering herd prevention
  5 min        spread window for 10K midnight jobs → ~33 jobs/sec instead of 10K spike

Cassandra (Variant A):
  job_id       partition key for job_executions
  TIMEUUID     clustering key → time-ordered execution history
  shard_date   partition key for running_jobs index

Kafka:
  7 days       retention on all topics (allows replay/backfill)
  10           partitions on 'run' and 'completed' topics
  5            partitions on 'retry' topic
  3            partitions on 'cancel' topic
  1            partition on 'dead' topic (low volume)

Priority Queue (Variant B — Kafka):
  High (8-10)  50 consumer instances
  Medium (5-7) 30 consumer instances
  Low (1-4)    20 consumer instances
  1 hour       wait threshold before priority boost (aging)

Alerting Thresholds:
  > 50%        single job failure rate (6/10 runs) → CRITICAL
  > 10%        system failure rate in 1 hour → WARNING
  > 100        dead letter queue messages → CRITICAL
  < 30%        healthy executors remaining → CRITICAL

Throughput ceiling (single Redis):
  ~100K–1M     simple ops/sec (10K ZPOPMIN/sec = 1–10% capacity)

Payload thresholds:
  < 64 KB      inline in Cassandra / PostgreSQL
  ≥ 64 KB      S3 reference only (store S3 key, not raw payload)

Job Definition Cache:
  5 min        Redis TTL for cached job definitions
  90%          read reduction achieved by caching job definitions
```

---

*Print: monospace font, 10pt, portrait, standard margins. All ASCII diagrams are print-ready.*

---

## KEY PATTERNS REFERENCED IN THIS DESIGN

> **For the 2-year developer:** These are the hidden concepts behind design decisions in this system. Each has a dedicated deep-dive file.

### Leader Election
**Why it matters here:** Only ONE scheduler instance should trigger a given job at a time. Without leader election: all 5 instances wake up at 2:00 AM and all try to run the same cron job → 5× work, 5× DB load, potential duplicate emails/charges. ZooKeeper ephemeral node or Redis SETNX for distributed lock per job.
**Deep dive:** `../../Leader_Election_Zookeeper_Raft.md`

### Idempotency Keys
**Why it matters here:** Job execution must be idempotent. If the scheduler fires a job, the worker crashes halfway, and the scheduler retries — the job must produce the same result whether run once or twice. Design every job to be safely re-runnable.
**Deep dive:** `../../Idempotency_Keys_Prevent_Double_Processing.md`

### CAP Theorem
**Why it matters here:** Job scheduler is CP — it is better to miss a job execution (return 503 or skip) than to run it twice. Duplicate job execution (double-charge, double-email) is worse than a delayed job. Consistency over availability.
**Deep dive:** `../../CAP_Theorem_Applied_What_Actually_Breaks.md`

### Timeout Strategy
**Why it matters here:** Each job must have a maximum execution timeout. A job that hangs indefinitely blocks the executor thread. Set timeout = expected job duration × 3. Job exceeds timeout → mark as TIMED_OUT → retry with fresh worker.
**Deep dive:** `../../Timeout_Strategy_Too_Short_Too_Long.md`

### [Redlock — Distributed Locking](../../Redlock_Distributed_Lock.md)
**Why this system uses it:** A job scheduler deployed across 10 instances must ensure only one instance runs each scheduled job (no duplicate execution). Redlock with 3 Redis nodes: lock key = `cron:job:{job_id}`, TTL = job_expected_duration × 1.5. The winning instance acquires the lock and runs the job. If the instance crashes mid-job, the lock TTL expires and another instance picks it up on the next polling cycle. For production: ShedLock library (Spring) implements this pattern with either Redis or the jobs database as the lock backend — the DB-backed variant is safer for jobs where exactly-once execution is critical (financial reports, billing jobs).

### [AWS API Gateway — REST vs HTTP vs WebSocket](../../../aws/22.api-gateway-rest-http-websocket-architect-interview.md)
**Why this system uses it:** Job submission API uses the 29s async pattern by design: POST /jobs returns jobId immediately, the job runs asynchronously (minutes to hours), client polls GET /jobs/{id}. API Gateway WebSocket alternative for real-time job completion push notification — scheduler sends a message to the client's connectionId when job completes.

### [DynamoDB Single-Table Design + GSI Hot Partitions](../../../aws/21.dynamodb-single-table-design-gsi-hot-partitions-dax.md)
**Why this system uses it:** Job state storage is a DynamoDB sweet spot: `PK=JOB#{id}`, attributes for status/scheduledAt/completedAt/result. GSI trap: a GSI on `status=PENDING` hot-partitions as thousands of jobs transition to PENDING at cron time. Fix: GSI on `next_execution_bucket` (time bucket + shard suffix) for polling "what jobs are due?". On-demand capacity handles the cron burst without pre-provisioning.

### [Kinesis vs MSK Kafka vs SQS — Streaming Decision](../../../aws/23.kinesis-vs-msk-kafka-vs-sqs-streaming-decision.md)
**Why this system uses it:** Job execution uses SQS FIFO — `MessageGroupId=jobId` ensures exactly-once execution per job. JobScheduler → SQS FIFO → Worker pool. Visibility timeout = job execution SLA (e.g., 30 minutes). If worker crashes, job becomes visible again after timeout for retry. DLQ captures jobs that fail 3+ times.

### [EventBridge — Scheduler (Core Pattern)](../../../aws/25.eventbridge-scheduler-event-routing-architect-interview.md)
**Why this system uses it:** EventBridge Scheduler IS the job scheduler for one-time and recurring jobs. Architecture: POST /jobs creates an EventBridge Schedule (one-time `at()` or recurring `cron()`) → schedule fires → Lambda executes job → Lambda deletes the schedule. This replaces the need to build a custom scheduler that polls DynamoDB for due jobs. Flexible time window (±30 minutes) reduces Lambda cold starts. EventBridge event routing: job_completed event → content-based rules → notify success handler vs failure handler vs retry handler based on `detail.exitCode`.

### [CloudWatch + X-Ray Observability](../../../aws/24.cloudwatch-xray-observability-architect-interview.md)
**Why this system uses it:** Custom metrics: JobExecutionLatency (P99 per job type), JobFailureRate, JobQueueDepth, MissedJobCount (jobs that fired but Lambda was throttled). P99 alarm: if job execution P99 > SLA threshold → alert job owner. CloudWatch Logs Insights: `filter jobId = "abc123" | sort @timestamp asc` to trace all events for a specific job execution. X-Ray traces the job execution path: Scheduler → Lambda → downstream service calls — identifies which external API call is causing job timeouts.

### [KMS Envelope Encryption + Secrets Manager](../../../aws/28.kms-envelope-encryption-secrets-manager-architect-interview.md)
**Why this system uses it:** Job payloads may contain sensitive parameters (API keys, credentials for the target system). Secrets Manager stores credentials per job type — job worker fetches credentials at execution time, never stores in job payload. Job results with PII encrypted with envelope encryption before storing in DynamoDB. IRSA: job worker Lambda assumes role → GetSecretValue for target system credentials → executes job → credentials never logged or stored.
