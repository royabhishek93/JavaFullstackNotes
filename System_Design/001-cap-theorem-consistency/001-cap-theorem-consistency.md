# SD_Q06: CAP Theorem & Consistency Models — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 20-25 minutes | **Frequency:** 80% in architect rounds 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "You're designing a distributed system. Explain CAP theorem and tell me which two properties your design prioritizes and why." — The architect framework question.

---

## NEW LEARNER FOUNDATION

### What is CAP Theorem? (Plain English)
```
CAP Theorem: in a DISTRIBUTED system, you can ONLY guarantee 2 of these 3:

  C — Consistency:    Every read sees the MOST RECENT write.
                      All nodes return the same data at the same time.

  A — Availability:   Every request gets a response (never returns an error).
                      System always responds, even if the data might be stale.

  P — Partition Tolerance: System keeps working even when NETWORK SPLITS happen.
                            (Some nodes can't talk to other nodes — network failure)

WHY CAN'T YOU HAVE ALL THREE?
  In a real network: P (partition) is NOT optional.
  Networks fail. Nodes get disconnected. You MUST handle partitions.
  So in practice: you choose between C and A during a partition.

The REAL choice is:
  CP system: during a network split → refuse requests (maintain consistency)
             "I'd rather be DOWN than return wrong data"
  AP system: during a network split → return possibly stale data (stay available)
             "I'd rather give you old data than give you an error"

CA (no partition tolerance) = only works on a SINGLE machine. Not a distributed system.
```

### What is Consistency in Plain English?
```
Strong Consistency (Linearizability):
  After you write X=5, any read from ANY node immediately returns 5.
  Feels like talking to one computer even though there are 100 servers.
  EXPENSIVE: every write must sync to all nodes before returning.
  Example: bank balance (can't show different balances on different ATMs)

Eventual Consistency:
  After you write X=5, reads may return OLD value for a while.
  BUT eventually (seconds/minutes) all nodes will show 5.
  CHEAP AND FAST: write to one node, replicate in background.
  Example: your Facebook like count might show 2,145 on your phone
           and 2,143 on your friend's phone for a few seconds. Acceptable.

Causal Consistency (middle ground):
  Operations that are causally related appear in correct order.
  If you write a reply to a post, anyone who sees your reply will also see the post.
  You don't see the effect before the cause.
```

---

## BIG PICTURE — CAP in Real Systems

```
 WHERE REAL SYSTEMS FALL ON THE CAP SPECTRUM
 ┌────────────────────────────────────────────────────────────────┐
 │                                                                │
 │  CP SYSTEMS (Consistency + Partition Tolerance):              │
 │  ┌──────────────────────────────────────────────────────────┐ │
 │  │  ZooKeeper: distributed config, leader election          │ │
 │  │  Consul: service discovery, key-value                    │ │
 │  │  HBase: Hadoop-based wide-column store                   │ │
 │  │  MongoDB (with writeConcern: majority)                   │ │
 │  │  → During network split: refuse writes, return error     │ │
 │  │  → Financial systems, config management, elections       │ │
 │  └──────────────────────────────────────────────────────────┘ │
 │                                                                │
 │  AP SYSTEMS (Availability + Partition Tolerance):             │
 │  ┌──────────────────────────────────────────────────────────┐ │
 │  │  Cassandra: wide-column, write-optimized                 │ │
 │  │  DynamoDB (default): key-value at scale                  │ │
 │  │  CouchDB: document store                                 │ │
 │  │  DNS: domain name resolution                             │ │
 │  │  → During network split: return stale data, stay alive   │ │
 │  │  → Shopping carts, social feeds, user preferences        │ │
 │  └──────────────────────────────────────────────────────────┘ │
 │                                                                │
 │  CA SYSTEMS (not truly distributed — single node):            │
 │  ┌──────────────────────────────────────────────────────────┐ │
 │  │  PostgreSQL (single instance)                            │ │
 │  │  MySQL (single instance)                                 │ │
 │  │  → No partitions to handle (one machine)                 │ │
 │  │  → Add replication → becomes CP or AP                    │ │
 │  └──────────────────────────────────────────────────────────┘ │
 │                                                                │
 │  TUNABLE CONSISTENCY (you choose per operation):              │
 │  ┌──────────────────────────────────────────────────────────┐ │
 │  │  Cassandra: ConsistencyLevel.ONE = AP (fast, stale ok)   │ │
 │  │             ConsistencyLevel.QUORUM = CP (slower, fresh) │ │
 │  │  DynamoDB: strongly_consistent_reads=true = CP           │ │
 │  │  MongoDB: readConcern=majority = CP                      │ │
 │  │  Use per operation based on what the business needs      │ │
 │  └──────────────────────────────────────────────────────────┘ │
 │                                                                │
 └────────────────────────────────────────────────────────────────┘
```

---

## Scenario 1: Design the Right Consistency Level Per Feature

### Amazon Shopping Cart — AP (Available > Consistent)
```
User adds item to cart.
Network partition happens: cart writes to Node A, Node B can't see it.

AP choice: serve the cart from Node B (shows old cart, missing the new item).
User sees cart without their latest addition for 5-10 seconds.
Eventually Node B syncs from Node A → correct cart shown.

WHY AP IS CORRECT HERE:
  "Item missing from cart for 5 seconds" → minor annoyance
  "Cart page down with 500 error for 5 seconds" → user leaves site, lost sale
  Amazon's actual design: AP for shopping cart (exactly this reasoning)

CONFLICT RESOLUTION: what if user edits cart on two devices simultaneously?
  Node A: cart has [iPhone, Charger]
  Node B: cart has [iPhone, Case]
  After network heals: two versions, which wins?

  LAST-WRITE-WINS (LWW): take the version with the latest timestamp
  → Might lose the Case if iPhone+Charger was written slightly later
  → Simple, but data loss possible

  MERGE (CRDTs): "Both are right — add all items together"
  → Cart becomes [iPhone, Charger, Case] — the union
  → Amazon actually does this: add-wins, never silently lose an item
  → CRDT (Conflict-free Replicated Data Type) — merge is always safe
```

### Bank Transfer — CP (Consistent > Available)
```
User transfers ₹10,000 from Savings to Checking.
Network partition happens mid-transfer.

AP choice: deduct ₹10,000 from Savings on Node A,
           can't update Checking on Node B (partitioned).
           Show user "Transfer complete" (lying).
           Money gone from Savings, not in Checking.
           This is MONEY LOSS. Catastrophic.

CP choice: during the partition → refuse the transfer.
           Return error: "Service temporarily unavailable. Please try again."
           User is annoyed but NO money is lost.
           After network heals → transaction can proceed correctly.

WHY CP IS CORRECT HERE:
  Financial systems: CORRECTNESS > AVAILABILITY
  Regulatory requirements: can't show inconsistent balances
  "Down for 2 minutes" is recoverable; "lost ₹10,000" is not.
```

### YouTube View Counter — AP with Approximate Counting
```
1 billion people watch a viral video simultaneously.
Strong consistency would require: every view increments a single counter
atomically → this counter becomes a bottleneck → impossible at 1 billion/sec.

AP design:
  Each data center has its own counter.
  Counters are merged periodically (every ~30 seconds).
  View count may be "1,247,423,891" on your screen and
  "1,247,423,856" on your friend's screen (35 views difference).

Does YouTube's view count need to be exact to the millisecond? NO.
"~1.2 billion views" is accurate enough.
STRONG CONSISTENCY here = impossible performance.
EVENTUAL CONSISTENCY = perfectly fine for this use case.
```

---

## Scenario 2: PACELC — A More Useful Model Than CAP

```
CAP only talks about behavior during PARTITIONS (network failures).
But partitions are rare! What about normal operation?

PACELC (more complete model):
  During Partition:     choose between A (Availability) and C (Consistency)
  Else (normal ops):    choose between L (Latency) and C (Consistency)

The ELSE case is what matters most of the time:

Strong Consistency in normal ops:
  Write to 3 replicas → wait for all 3 to confirm → return success
  LATENCY: slowest replica determines response time (P99 is bad)
  If one replica is slow: every write waits for it

Eventual Consistency in normal ops:
  Write to 1 replica → return success immediately
  Replicate to 2 more replicas in background
  LATENCY: just 1 replica's write time → fast
  Downside: replication lag → reads may be stale

PACELC categories:
  PA/EL: Available during partition, Low latency normally (DynamoDB default, Cassandra)
  PC/EC: Consistent during partition, Consistent normally (ZooKeeper, HBase)
  PA/EC: Available during partition, Consistent normally (MySQL with async replication)
```

---

## Scenario 3: Read-Your-Own-Writes Consistency

### The Problem
```
Social network. User posts a status update.
  POST /status {"text": "Just got into IIT!"} → written to PRIMARY replica

User immediately checks their own profile.
  GET /profile/123 → routes to READ REPLICA (50ms behind primary)
  → User's own post is NOT there yet! (replication lag)
  → User thinks their post was lost → posts again → duplicate

This is the "read-your-own-writes" consistency problem.
```

```
SOLUTION: Session consistency (read-your-own-writes guarantee)

Strategy 1: Route post-write reads to primary (simplest)
  After a write, tag the session with: lastWriteAt = now()
  For next 5 seconds: read from primary (not replica)
  After 5 seconds: replica has caught up → read from replica again

  Implementation:
  String primaryRouting = redis.get("user:" + userId + ":lastWriteAt");
  if (primaryRouting != null && /* within 5 seconds */) {
      return primaryRepo.findProfile(userId);
  }
  return replicaRepo.findProfile(userId);  // replica (fast)

Strategy 2: Propagate a "read-after-write token"
  Write response includes: { "token": "lsn:12345678" }
  (LSN = Log Sequence Number — the DB's position after this write)
  GET /profile includes token in header: X-Min-Read-LSN: 12345678
  Any replica that has replicated up to LSN 12345678+ can serve the request
  → Read from the FASTEST replica that's caught up enough
  → Used by Aurora (Global Read Replica with session consistency)
```

---

## Trap: Confusing Consistency Levels in Interviews

```
COMMON INTERVIEW MISTAKE:
  "I'll use strong consistency for everything to avoid bugs."

WRONG for three reasons:

1. Performance: strong consistency requires distributed coordination.
   Coordinating 5 replicas = 5× the write latency.
   For an app making 100,000 writes/sec → catastrophically slow.

2. Availability: strong consistency requires all replicas agree.
   If one replica is down → writes BLOCKED (CP behavior).
   During a deployment, rolling restart → periodic write errors.

3. Unnecessary: most data doesn't NEED to be perfectly consistent.
   Is it a problem if a user sees their follower count as 1,247 instead of 1,248
   for 2 seconds? NO.
   Is it a problem if their bank balance shows wrong for 2 seconds? YES.

CORRECT APPROACH: per-feature consistency design
  Strong consistency: money, inventory, authentication, config
  Eventual consistency: social feeds, likes, view counts, recommendations
  Read-your-own-writes: user-visible mutations (post, profile update)
```

---

## Quick Reference: Consistency Models (Weakest → Strongest)

```
Eventual Consistency       → replicas sync eventually (seconds-minutes)
                             No ordering guarantees. Fast. Cassandra default.

Monotonic Read             → once you read a value, you never read an older one
                             No backward time travel in reads.

Read-Your-Writes           → you always see your own writes immediately
                             Others may still see old values.

Causal Consistency         → causally related ops are seen in order everywhere
                             Reply appears after post for everyone. Not for unrelated ops.

Sequential Consistency     → all nodes see operations in same order
                             Not necessarily real-time order, but consistent order.

Linearizability            → strongest; reads always reflect the most recent write
(Strong Consistency)         Appears as a single machine. Slowest.
```

---

## Interview Cheat Sheet

> "CAP theorem says in a distributed system you can't have Consistency, Availability, AND Partition Tolerance simultaneously — and since partitions are inevitable, the real choice is CP vs AP during a network failure. For financial data (bank transfers, payments): CP — I'd rather be temporarily unavailable than show a user they have money they don't have. For user experience features (shopping cart, social feeds, view counts): AP — brief staleness is acceptable; being down is not. Tunable consistency databases like Cassandra and DynamoDB let you choose per operation: use quorum reads/writes for financial ops, eventual for social metrics. The most common architect mistake is defaulting to strong consistency everywhere — it kills performance and doesn't survive any replica going down. Design consistency level per feature based on the cost of staleness vs the cost of unavailability."
