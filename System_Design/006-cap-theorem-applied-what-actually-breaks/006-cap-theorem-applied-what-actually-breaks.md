# CAP Theorem Applied
### Not the Theory — "Your System Chose AP. What Actually Breaks?"

---

## PART 1 — THE STUDENT CONVERSATION

**Everyone teaches CAP theorem as theory. Interviewers test it as practice.**

The theory: a distributed system can only guarantee 2 of 3 — Consistency, Availability, Partition tolerance.

The practice: **partitions always happen** (network cables get cut, servers hang, datacenters lose connectivity). So the real choice is always: **when the network fails, do you stay available (AP) or do you stay consistent (CP)?**

Let's make this concrete.

**Consistency (C):** Every read sees the most recent write. If User A writes "balance=$100", User B reading immediately after always sees $100 — never stale data.

**Availability (A):** Every request gets a response (not an error). You might get stale data, but you always get *something*.

**Partition Tolerance (P):** The system keeps working even when network messages between nodes are lost. You can't turn this off — networks fail. So P is mandatory.

Real choice: **C vs A when partition happens.**

---

## PART 2 — WHAT ACTUALLY BREAKS (THE REAL INTERVIEW ANSWER)

### Scenario: Your social media feed is AP

```
Normal operation:
────────────────────────────────────────────────────────────
  User A posts "I'm at the beach!"
        │
        ▼
   Primary DB  ──replicates──►  Replica 1 (US-East)
               ──replicates──►  Replica 2 (EU-West)

  User B in EU reads feed → hits Replica 2 → sees the post ✓

Network partition happens:
────────────────────────────────────────────────────────────
  Primary DB  ✗──────────────  Replica 2 (EU-West) ISOLATED

  User A posts "I'm leaving for hospital"

  User B in EU reads feed:
    → hits Replica 2
    → Replica 2 is isolated, has stale data
    → User B sees the last synced version (beach post, not hospital)
    → AP system: "still alive, here's what I have"   ← stale read

  User A's family in EU: no idea about hospital. They see "beach" post.

  WHAT BROKE: data staleness — reads return outdated data
  ACCEPTABLE FOR: social feed (few seconds stale = OK)
  NOT ACCEPTABLE FOR: bank balance ("your account has $5000" — actually $0 after withdrawal)
```

### Scenario: Your payment system is CP

```
Network partition happens:
────────────────────────────────────────────────────────────
  Primary DB  ✗──────────────  Replica (EU-West) ISOLATED

  User tries to pay for order:
    → Request hits EU replica
    → Replica can't confirm it has latest balance (can't reach primary)
    → CP system: "I refuse to answer rather than give wrong data"
    → Returns: HTTP 503 Service Unavailable

  WHAT BROKE: availability — requests return errors during partition
  ACCEPTABLE FOR: payments (error > wrong balance)
  NOT ACCEPTABLE FOR: feed (500 error on scroll is terrible UX)
```

---

## PART 3 — THE DIAGRAM

```
CAP in practice across your 21 systems:
────────────────────────────────────────────────────────────────────

           C (Consistency)
           ▲
           │
           │   CP Systems               AP Systems
           │   ─────────────────        ────────────────────
           │   MySQL (strict reads)     Cassandra
           │   ZooKeeper                DynamoDB
           │   HBase                    CouchDB
           │   etcd                     Redis (cluster mode)
           │   PostgreSQL (sync rep)    Riak
           │
           └──────────────────────────────────────────► A (Availability)
                                P (always required)

Your systems mapped:
  CP: Payment (07), Ticket Booking (11), Hotel Booking (12) → wrong answer worse than no answer
  AP: Social Feed (05), Leaderboard (13), OTT Feed (17)    → stale is OK, downtime is not
  Depends: Chat (04) → messages must not be lost (CP), but "online" status can be stale (AP)
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "You chose Cassandra for the social feed. What does that mean for consistency?"

**You (architect answer):**

> "Cassandra is an AP system. When a network partition occurs, Cassandra keeps serving reads
> from whatever replica is reachable, even if that replica hasn't received the latest writes.
>
> For a social feed, this means users might see posts that are a few seconds or a few minutes
> stale during a partition. Someone posts 'I'm live now!' and a user in another region sees
> it 30 seconds late. That's acceptable — nobody's account balance is wrong.
>
> What I'd want to flag: the feed's 'like count' might briefly show 1,234 to one user and
> 1,230 to another. Cassandra resolves write conflicts using Last-Write-Wins (LWW) with
> timestamps. If two replicas both accepted writes during the partition, the one with the
> later timestamp survives on merge. For counters, I'd use Cassandra counter columns which
> use CRDT (Conflict-free Replicated Data Types) — they merge by summing, not overwriting.
>
> The trade-off I made: availability over consistency. The product requirement was '99.99%
> uptime, tolerate minor staleness.' If the requirement were 'never show a stale price,'
> I'd use MySQL with synchronous replication — but then I'd need a plan for when the
> primary is unreachable."

---

## PART 5 — PACELC (WHAT INTERVIEWERS ACTUALLY PROBE)

> Most senior architects know CAP is incomplete. PACELC is the better model.

```
PACELC:
  P: if there's a Partition:
     A: choose Availability
     C: or choose Consistency

  EL: Else (no partition, normal operation):
     L: trade-off between Latency
     C: and Consistency

Normal operation trade-off (no partition):
  Cassandra: you CAN get strong consistency with QUORUM reads/writes
             but it's slower (must wait for 2/3 nodes to reply)
             → Choose: LOW LATENCY (read from 1 node) or STRONG CONSISTENCY (read from 2)

  MySQL with sync replication:
             → Every write waits for replica to confirm → higher write latency
             → But consistent reads

Real interview question: "Your Cassandra read latency spiked. Why?"
  Answer: "We turned on QUORUM consistency for a feature. Reads now wait for 2/3 nodes
           instead of 1. Fixed by: either accept eventual consistency or pre-aggregate
           the data in Redis."
```

---

## QUICK REFERENCE CARD

```
┌──────────────┬──────────────────────┬──────────────────────┐
│ System       │ Choice               │ What breaks          │
├──────────────┼──────────────────────┼──────────────────────┤
│ Cassandra    │ AP (default)         │ Stale reads after    │
│              │ CP (with QUORUM)     │   partition          │
│ DynamoDB     │ AP (default)         │ Same as Cassandra    │
│              │ CP (strong reads)    │                      │
│ MySQL        │ CP (sync replicas)   │ 503 errors during    │
│              │ AP (async replicas)  │   failover           │
│ ZooKeeper    │ CP always            │ Unavailable during   │
│              │                      │   leader election    │
│ Redis Cluster│ AP                   │ Writes lost during   │
│              │                      │   failover           │
└──────────────┴──────────────────────┴──────────────────────┘

Interview one-liner:
"CAP isn't a choice you make at design time — it's a description of
what your system does under failure. For payments, I want CP: fail
loudly rather than give wrong data. For feeds, I want AP: stay
available even if data is slightly stale."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Every system you design makes an implicit CAP choice — knowing which choice and why turns a vague answer into a senior-level one.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **02 — Rate Limiter** | CP choice — fail-closed during Redis partition. A wrong rate-limit decision costs money; better to 503 than allow overcharging. |
| **04 — Chat** | AP choice — messages may arrive late during partition but users must still be able to send. Availability trumps ordering guarantees. |
| **07 — Payment** | CP — return 503 during partition rather than risk double-charge. A missed payment is recoverable; a double-charge is a customer support nightmare. |
| **09 — E-Commerce** | Split CAP — product catalog is AP (stale price for 30s is fine), inventory decrement is CP (oversell is not acceptable). |
| **10 — Cloud Storage** | CP for file metadata — don't lose track of what files a user has. During partition, block writes rather than risk data inconsistency. |
| **13 — Leaderboard** | AP — stale score for 10 seconds is fine. Users must see the leaderboard even during partial Redis failures. |
| **17 — OTT Platform** | AP for video catalog (stale recommendation is fine). CP for billing/subscription status (wrong entitlement = legal issue). |
| **19 — Stock Broker** | CP for order execution — during partition, reject new orders rather than risk executing at stale prices. |

**Architect's one-liner for the interview:**
*"Different subsystems in the same product make different CAP choices — catalog is AP, payments is CP, and the art is knowing which is which before you start drawing boxes."*
