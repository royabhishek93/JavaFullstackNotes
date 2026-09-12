# Split Brain Problem
### Two Nodes Both Think They're Primary — What Data Corruption Happens

---

## PART 1 — THE STUDENT CONVERSATION

**Imagine a company with two CEOs who stopped talking to each other.**

Both think they're the boss. Both are making decisions. Both are signing contracts with different clients. When communication resumes, the company discovers conflicting contracts, double-spent budgets, and customers with conflicting promises.

That's split brain. Two database nodes both believe they are the primary (writer). Both accept writes. When the network partition heals, you have two divergent data sets. Which one is correct?

This is one of the most dangerous failure modes in distributed systems — and one of the most commonly asked senior/architect interview questions.

---

## PART 2 — HOW SPLIT BRAIN HAPPENS

```
Normal operation (MySQL Primary-Replica):
──────────────────────────────────────────────────────────────────

  ┌─────────────────┐          ┌─────────────────┐
  │   PRIMARY       │ ─sync──► │   REPLICA       │
  │   (writes here) │          │   (read-only)   │
  └─────────────────┘          └─────────────────┘
        ↑
  App writes here

Network partition:
──────────────────────────────────────────────────────────────────

  ┌─────────────────┐    ✗     ┌─────────────────┐
  │   PRIMARY       │ ─ ✗ ─── │   REPLICA       │
  │   Still primary │          │                 │
  └─────────────────┘          └─────────────────┘

  Replica waits... heartbeat timeout fires (say 30 seconds)
  Replica thinks: "Primary is dead. I must become primary."
  Replica promotes itself.

  ┌─────────────────┐    ✗     ┌─────────────────┐
  │   OLD PRIMARY   │          │   NEW PRIMARY   │
  │   (still alive) │          │   (promoted)    │
  └─────────────────┘          └─────────────────┘
        ↑                             ↑
  Some app servers                Some app servers
  still write here!              now write here!

  SPLIT BRAIN: two primaries, both accepting writes
```

### The Corruption

```
Both primaries running simultaneously (t=0 to t=60 seconds):
──────────────────────────────────────────────────────────────────

  OLD PRIMARY receives:                NEW PRIMARY receives:
  ─────────────────────                ──────────────────────
  ORDER #1001: user=Alice, $200        ORDER #1001: user=Bob, $150
  ORDER #1002: user=Charlie, $50       ORDER #1003: user=Diana, $300
  UPDATE balance user=Alice: -$200     UPDATE balance user=Bob: -$150

  t=60s: network heals. Both nodes can talk again.

  CONFLICT:
  - ORDER #1001 exists on both but with different users!
  - Alice's balance was debited on OLD PRIMARY
  - Bob's balance was debited on NEW PRIMARY
  - One of these writes will be lost
  - One customer gets charged, other doesn't

  RESULT:
  → Alice ordered something, got charged, order gone (lost write)
  → ORDER #1001 ID collision in DB
  → Inventory decremented twice for different users
  → Money and data integrity destroyed
```

---

## PART 3 — HOW TO PREVENT SPLIT BRAIN

### Solution 1: Fencing / STONITH ("Shoot The Other Node In The Head")

```
When new primary is elected, it sends a FENCE command to the old primary:
  → cut off old primary's network access
  → force-shutdown old primary's MySQL process
  → revoke old primary's disk access

Before new primary accepts writes:
  "Did old primary stop? Confirmed? Then I'll start accepting writes."

  ┌─────────────────┐    ✗     ┌─────────────────┐
  │   OLD PRIMARY   │  ←FENCE  │   NEW PRIMARY   │
  │   FENCED/KILLED │          │   (safe to write│
  └─────────────────┘          └─────────────────┘

Only ONE primary can exist at a time — old one is dead before new one starts.
```

### Solution 2: Quorum / Majority Vote

```
MySQL Group Replication / Orchestrator:
  "I will only accept writes if I can communicate with a MAJORITY of nodes."

  N=3 nodes: Node A (primary), Node B, Node C

  Partition: A can't reach B or C
  Node A: "I can only see myself (1/3). I do NOT have majority. Stepping down."
  Node A: refuses writes, returns errors.

  B and C: "We see each other (2/3). We have majority. Elect B as primary."
  Node B: "I have majority. I am the primary."

  Result: only one primary at a time. Old one steps down voluntarily.

  This is how etcd, ZooKeeper, and Raft work:
  "A leader must maintain a majority lease to remain leader."
```

### Solution 3: Redis Sentinel Anti-Split-Brain

```
Redis Sentinel with min-slaves-to-write:

  redis.conf on PRIMARY:
    min-replicas-to-write 1
    min-replicas-max-lag 10

  Meaning: "I will only accept writes if at least 1 replica is connected
            and replication lag is under 10 seconds."

  Partition: primary loses connection to all replicas
  Primary: "Zero replicas connected. Refusing writes."
  → Clients get READONLY errors
  → New primary elected (has replicas connected)
  → Only 1 writable primary at any time
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your Redis primary goes down and Sentinel promotes a replica. What are the risks?"

**You (architect answer):**

> "The main risk is split brain — especially if the original primary comes back online before
> all clients have reconnected to the new primary.
>
> Here's the scenario: primary dies, Sentinel promotes a replica. The old primary comes back
> after 30 seconds — maybe it was just a transient network blip. Now two Redis instances both
> think they're writable if clients haven't updated their connection strings yet.
>
> Redis Sentinel has two safeguards. First, min-replicas-to-write: the primary refuses writes
> if it has zero replicas connected — so when the old primary comes back isolated, it won't
> accept writes. Second, clients using Redis Sentinel-aware drivers will query Sentinel for
> the current master address before each connection — they'll discover the new primary and
> stop hitting the old one.
>
> The window where data loss can occur is between the primary failing and the replica being
> fully promoted. Any writes acknowledged by the primary but not yet replicated are lost.
> You can tune this window with repl-diskless-sync and the min-replicas-max-lag setting.
>
> For a leaderboard or cache, losing a few writes is acceptable — we can rebuild from Kafka.
> For a payments system, Redis is never the source of truth — MySQL is — so Redis data loss
> is a cache miss, not a financial error."

---

## PART 5 — SPLIT BRAIN IN REAL PRODUCTS

```
How major systems handle it:
────────────────────────────────────────────────────────────────────

ZooKeeper:
  Uses Zab (ZooKeeper Atomic Broadcast) protocol
  Leader election requires quorum (majority of ZK nodes)
  Old leader that loses quorum → immediately stops being leader
  No split brain possible — two leaders can't both have majority

etcd (Kubernetes' backend):
  Uses Raft consensus
  Leader must send heartbeats to majority every 150ms
  If leader can't reach majority → steps down
  At most one leader at all times — mathematically provable

Cassandra:
  No single primary — all nodes are equal (leaderless)
  Concurrent writes to same key from different nodes → LWW (last write wins)
  "Split brain" = two nodes accepting conflicting writes → resolved by timestamp
  Risk: clock skew between nodes → wrong winner

MySQL with Orchestrator:
  Orchestrator uses "virtual co-master" detection
  If it sees two primaries → immediately fences one using hooks
  Triggers STOP SLAVE, FLUSH PRIVILEGES on the demoted one

The general pattern:
  Prevention: majority voting (can't have 2 majorities simultaneously)
  Detection: each node checks if it still has a quorum lease
  Recovery: fencing — kill the old primary before new one starts
```

---

## QUICK REFERENCE CARD

```
Split Brain: two nodes both believe they are primary → divergent writes → data corruption

Prevention strategies:
  1. Fencing (STONITH)     → kill old primary before new one starts
  2. Quorum requirement    → primary refuses writes without majority
  3. Epoch/term checking   → new primary has higher epoch; old primary rejects
                              any write with lower epoch

Systems and their approach:
  MySQL           → Orchestrator + fencing via topology hooks
  Redis           → Sentinel + min-replicas-to-write safeguard
  ZooKeeper/etcd  → Raft/Zab — mathematically impossible to have 2 leaders
  Cassandra       → Leaderless; resolves via LWW (clock-dependent)
  PostgreSQL       → Patroni uses etcd/Consul for leader election + fencing

Data loss window (even with correct prevention):
  Any writes acknowledged by old primary but not replicated = LOST
  Tune with synchronous replication (higher latency, zero loss)
  or accept async replication (low latency, small loss window)

Interview one-liner:
"Split brain is when two nodes both think they're primary. The solution
is to ensure only one can have a majority at a time — either through
quorum requirements or fencing the old primary before promoting the new one."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Any time you say "primary/replica" in an interview, the follow-up will be "what happens if the network partitions between them?" — split brain is that answer.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **04 — Chat** | WebSocket connection state in Redis. Split brain → two Redis primaries → "Alice is online" written to Node 1, Node 2 doesn't know → presence inconsistency. Redis Sentinel prevents via quorum election. |
| **07 — Payment** | PostgreSQL primary/replica split brain → two primaries → concurrent debits both succeed → account goes negative. Quorum requirement (STONITH fencing) for primary election. |
| **13 — Leaderboard** | Redis Cluster split brain → two nodes accept ZINCRBY for same user → score diverges. min-replicas-to-write=1 prevents primary from accepting writes without at least 1 replica confirming. |

**Architect's one-liner for the interview:**
*"Split brain happens when two nodes both think they're primary — the fix is always quorum: a node can only be primary if a majority of the cluster agrees, so two primaries are mathematically impossible."*
