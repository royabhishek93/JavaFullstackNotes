# Read Replica Lag and Read-Your-Own-Writes
### Why your post disappeared after you posted it — and four ways to fix it

---

## PART 1 — THE STUDENT CONVERSATION

You post a photo on Instagram. You immediately tap your profile to admire it. The photo isn't there.

You posted it two seconds ago. You can see the upload confirmation. But your profile page shows your old posts — the new one is missing.

You refresh. It appears. You think: "Instagram is buggy." But it isn't. This is read replica lag, and it happens in every large-scale system that uses read replicas.

Here's what's happening under the hood. Instagram doesn't read from and write to the same database server. They write to a **primary** (also called master or leader). They read from **replicas** (also called secondaries or followers). The replicas are copies of the primary that stay in sync by replaying a log of changes.

The catch: replication is **asynchronous** by default. The primary doesn't wait for replicas to confirm they received the change before telling you the write succeeded. The primary says "done" the moment it writes locally. The replica catches up... eventually. Usually in milliseconds. Sometimes in seconds.

Your profile page hit a replica that hadn't caught up yet. It returned the snapshot from 500 milliseconds ago, before your photo was written.

This is called a **stale read**. The specific flavor of stale read you care most about in interviews is **read-your-own-writes** — you wrote something, you immediately read it back, and you don't see it.

The question is: does your system need to fix this, and how?

Not every system does. Netflix's "continue watching" row can be 30 seconds stale — you barely notice. But a hotel booking must appear immediately after you book it. A payment confirmation must appear immediately after you pay. There, stale reads are a real user-facing bug.

---

## PART 2 — REPLICATION FLOW AND THE PROBLEM

### Primary/Replica Replication Flow

```
USER WRITE REQUEST
        │
        ▼
  ┌─────────────┐
  │   PRIMARY   │  ← All writes go here
  │   (Leader)  │
  └──────┬──────┘
         │
         │  Binary Log (binlog) / WAL stream
         │  Async — primary does not wait
         │
    ┌────┴─────┬─────────────┐
    ▼          ▼             ▼
┌────────┐ ┌────────┐  ┌────────┐
│Replica │ │Replica │  │Replica │
│   1    │ │   2    │  │   3    │
│(lag:   │ │(lag:   │  │(lag:   │
│ 10ms)  │ │ 150ms) │  │ 800ms) │
└────────┘ └────────┘  └────────┘
    ▲          ▲
    │          │
  READ       READ
requests   requests
 (routed   (routed
  here)     here)

Lag = time between primary write and replica applying it.
Normal: 0–100ms. Under load spikes: seconds.
```

### The Read-Your-Own-Writes Problem

```
Timeline:
─────────────────────────────────────────────────────────────▶ time
     t=0          t=0+5ms       t=0+10ms       t=0+200ms
      │               │              │               │
  User POSTS       Primary       Read request    Replica 2
  new photo        writes        hits Replica 2  finally applies
                   photo         (lag = 200ms)   the write
                   (success)          │
                                      │
                               Replica 2 does NOT
                               have the photo yet
                                      │
                               Returns old profile ← USER SEES BUG
```

### Four Solutions Side-by-Side

```
┌────────────────────────────────────────────────────────────────┐
│              SOLUTION COMPARISON                               │
├──────────────────┬────────────┬──────────────┬────────────────┤
│                  │  Always    │  Monotonic   │  LSN-based     │
│                  │  read      │  reads       │  routing       │
│                  │  primary   │  (sticky)    │                │
├──────────────────┼────────────┼──────────────┼────────────────┤
│ How it works     │ Route all  │ User always  │ Write returns  │
│                  │ reads to   │ hits the     │ LSN. Read waits│
│                  │ primary    │ same replica │ for replica to │
│                  │ after write│              │ reach that LSN │
├──────────────────┼────────────┼──────────────┼────────────────┤
│ Replica load     │ High       │ Normal       │ Normal         │
│ relieved?        │ ✗ No       │ ✓ Yes        │ ✓ Yes          │
├──────────────────┼────────────┼──────────────┼────────────────┤
│ Handles replica  │ N/A        │ ✗ No         │ ✓ Yes          │
│ failure?         │            │ (need        │ (reroute to    │
│                  │            │  fallback)   │  another)      │
├──────────────────┼────────────┼──────────────┼────────────────┤
│ Complexity       │ Very low   │ Low          │ Medium         │
├──────────────────┼────────────┼──────────────┼────────────────┤
│ Latency impact   │ Primary    │ None         │ Slight wait if │
│                  │ takes load │              │ replica is slow│
└──────────────────┴────────────┴──────────────┴────────────────┘

Fourth solution: Semi-sync replication (wait-for-replication)
  → Write doesn't return until at least 1 replica acknowledges
  → Zero lag for that replica, guaranteed
  → Slower writes (write latency += replica RTT)
  → MySQL: rpl_semi_sync_master_enabled=1
  → Used for: financial writes, audit logs, anything that cannot be lost
```

---

## PART 3 — FOUR SOLUTIONS IN DEPTH

### Solution 1: Read from Primary After Write

The simplest fix. For a brief window after a write, route that user's reads back to the primary.

```
POST /photo → write to primary → set cookie: "reads_from_primary=true; max-age=5"
GET /profile → check cookie → if present, route to PRIMARY not replica

After 5 seconds, cookie expires, reads go back to replicas.
```

Simple to implement. The tradeoff is that the primary now absorbs some reads it wouldn't otherwise see. For low-write, high-read systems (most systems), a 5-second window is fine. For high-write systems, this can overload the primary.

### Solution 2: Monotonic Reads (Sticky Replica Routing)

Assign each user to a specific replica, consistently. User 123 always reads from Replica 2. Replica 2 may lag, but it will never go backwards — you'll never see a read at t=200ms that returns data older than your read at t=100ms.

```python
# Routing logic (pseudo-code)
def get_replica_for_user(user_id: int, replicas: list) -> Replica:
    return replicas[hash(user_id) % len(replicas)]
```

This prevents the "time travel" problem where a user refreshes and sees even older data (because a different replica was selected). But it doesn't prevent initial lag — if the user just wrote and immediately reads, the sticky replica may not have caught up.

### Solution 3: LSN-Based Read Routing

The most precise solution. Each write returns a **Log Sequence Number** (LSN in PostgreSQL, binlog position in MySQL). This is a monotonically increasing counter that identifies exactly where in the replication log that write lives.

```
1. User writes → primary returns LSN 9,482,341
2. Application stores LSN in user session (or returns it in response)
3. User reads → request includes "I need at least LSN 9,482,341"
4. Router checks each replica's current applied LSN
5. Routes to any replica where applied_LSN >= 9,482,341
6. If no replica qualifies yet: either wait (poll for 50–200ms) or fall back to primary
```

PostgreSQL exposes replica LSN via:
```sql
-- On replica: current replay LSN
SELECT pg_last_wal_replay_lsn();

-- On primary: replication lag per replica
SELECT client_addr, replay_lsn, write_lag, flush_lag, replay_lag
FROM pg_stat_replication;
```

MySQL equivalent:
```sql
-- On replica
SHOW REPLICA STATUS\G
-- Look at: Seconds_Behind_Source, Exec_Master_Log_Pos
```

### Solution 4: Semi-Synchronous Replication

The write doesn't return until at least one replica has received (not necessarily applied) the change.

```
MySQL config (my.cnf):
  rpl_semi_sync_source_enabled = 1
  rpl_semi_sync_source_timeout = 1000  -- ms, fallback to async if no replica acks
  rpl_semi_sync_source_wait_for_replica_count = 1  -- need 1 replica to ack

Effect:
  Write latency += replica network RTT (~1–5ms same datacenter)
  Guarantee: at least 1 replica has the data when write returns
  If that replica is used for reads → zero read-your-own-writes lag
```

The timeout is critical. If all replicas go down and timeout is hit, MySQL falls back to fully async. This is a safety valve — you don't block writes forever because replicas are unreachable.

### Monitoring Replication Lag in Production

```bash
# PostgreSQL — lag per replica in seconds
SELECT
  client_addr,
  EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds
FROM pg_stat_replication;

# Alert threshold: > 5 seconds is abnormal for same-datacenter replicas
# Alert threshold: > 30 seconds means the replica is probably stuck

# MySQL — check from replica
SHOW REPLICA STATUS\G
# Key fields:
#   Seconds_Behind_Source: 0 = in sync, >10 = investigate, >60 = alert

# Prometheus metric: mysql_slave_status_seconds_behind_master
# Alert rule: mysql_slave_seconds_behind_master > 10 for 2m
```

Typical lag values:
- Same datacenter, light load: 0–10ms
- Same datacenter, heavy write load: 100ms–2s
- Cross-region replica: 50–200ms baseline + write load
- Spike during large batch writes: can reach minutes

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "A user submits a hotel booking. They're immediately redirected to their bookings page. The new booking isn't there. What happened and how do you fix it?"

**You (architect answer):**

> "This is a classic read-your-own-writes violation caused by read replica lag. The booking write went to the primary. The redirect to the bookings page hit a read replica. The replica hadn't applied that write yet — maybe it was 200ms behind. The user sees their old bookings list without the new one.
>
> The fix depends on how strict the requirement is. For a hotel booking, I'd say it's very strict — users expect to see their booking immediately after paying. So I'd use LSN-based routing. When the booking service writes the new booking to the primary, the response includes the WAL LSN of that write. The booking service stores this LSN in the user's session or in a short-lived cache keyed by user_id with a 30-second TTL. When the bookings page query comes in, the router checks this cached LSN, queries pg_last_wal_replay_lsn() on each replica, and routes to the first replica that has caught up past that LSN. If no replica qualifies within 100ms, we fall back to the primary.
>
> An alternative that's simpler to implement is a time-based window: after a write, route that user's reads to the primary for 5 seconds. This works well if booking writes are relatively infrequent per user — which they are, users don't book 10 hotels per second. The primary load impact is minimal.
>
> I'd also add a replication lag monitor. If any replica consistently lags more than 5 seconds, it should be removed from the read pool until it catches up. A lagging replica doesn't just cause stale reads — it means that replica is behind on schema changes too, which causes serious bugs if you recently ran a migration."

---

## PART 5 — DECISION FRAMEWORK: WHICH STRATEGY FOR WHICH SYSTEM

| System Characteristic | Best Strategy | Why |
|----------------------|---------------|-----|
| Low write volume, high read volume | Read-from-primary window (5s) | Writes are rare, primary load impact minimal |
| High write volume, strict consistency | LSN-based routing | Primary can't absorb read overflow; precision needed |
| Users distributed globally | Monotonic reads + regional affinity | User sticks to regional replica — predictable, no cross-region reads |
| Financial writes (payments, bookings) | Semi-sync + LSN routing | Can't lose writes AND need immediate readback |
| Social feed, watch history | Accept lag (no fix needed) | 30s stale is unnoticeable to users |
| Multi-tenant SaaS | LSN per tenant session | Each tenant's write must be visible to that tenant immediately |

### Lag Tolerance by System Type

```
HIGH tolerance (lag OK):
  Social feed              → 10–30s lag fine
  Analytics dashboards     → minutes fine
  Recommendation engine    → hours fine

MEDIUM tolerance (lag bad UX but not critical):
  User profile updates     → 5s lag noticeable
  Shopping cart            → 2s lag annoying
  Search index             → 1s lag acceptable

LOW tolerance (lag = bug):
  Hotel/flight booking     → must show immediately
  Payment confirmation     → must show immediately
  Seat reservation         → must show immediately
  Order placement          → must show within 1s
```

---

## QUICK REFERENCE CARD

```
REPLICATION LAG MONITORING:
  PostgreSQL: SELECT pg_last_wal_replay_lsn();           -- on replica
              SELECT replay_lag FROM pg_stat_replication; -- on primary
  MySQL:      SHOW REPLICA STATUS\G  → Seconds_Behind_Source

ALERT THRESHOLDS:
  > 5s:  investigate (replica probably under load)
  > 30s: replica likely stuck, remove from read pool
  > 60s: escalate, possible replication failure

FOUR SOLUTIONS (ranked by complexity):
  1. Read-from-primary window    — simple, slight primary load
  2. Monotonic reads (sticky)    — no cross-replica time travel
  3. LSN-based routing           — precise, zero false positives
  4. Semi-sync replication       — write-level guarantee, slower writes

POSTGRESQL LSN ROUTING (pseudo):
  write_lsn = db.execute("SELECT pg_current_wal_lsn()").scalar()
  session["min_lsn"] = write_lsn                     # store in session
  # on read:
  for replica in replicas:
      if replica.lsn >= session["min_lsn"]:
          return replica                              # use this replica
  return primary                                     # fallback

MYSQL SEMI-SYNC CONFIG:
  rpl_semi_sync_source_enabled = 1
  rpl_semi_sync_source_timeout = 1000   # ms before async fallback
  rpl_semi_sync_source_wait_for_replica_count = 1
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Read replicas are the first scaling step every production system takes — understanding their lag model prevents the most common class of data consistency bugs.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **05 — Social Media** | User posts content → immediately views their own profile. Post writes to primary, profile reads from replica → lag. Fix: read-from-primary window of 5s after a post, or sticky routing so the user always reads from the same replica they last wrote through. |
| **09 — E-Commerce** | Order placed → order history page must show new order. Read-from-primary window of 5s after order creation. Also: inventory deducted → product page must not show old "in stock" for already-sold items — semi-sync replication for inventory writes. |
| **12 — Hotel Booking** | Hotel booked → bookings page must show it immediately. LSN-based read routing: booking write returns LSN, bookings page waits for a replica at that LSN or falls back to primary. Strictest consistency requirement. |
| **17 — OTT Platform** | Watch history updated → "continue watching" list. This is an AP system — eventual consistency is acceptable. Netflix's continue-watching list can be 30s stale. No fix needed; lag is a non-issue here. Document this trade-off explicitly. |

**Architect's one-liner for the interview:**
*"Read replicas give you horizontal read scaling but introduce lag — the first thing I do when adding replicas is decide per-endpoint whether staleness is acceptable, and implement LSN routing or a primary-read window for the endpoints where it isn't."*
