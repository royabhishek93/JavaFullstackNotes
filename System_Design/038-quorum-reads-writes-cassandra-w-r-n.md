# Quorum Reads and Writes
### Cassandra W + R > N Gives Strong Consistency — The Trade-offs

---

## PART 1 — THE STUDENT CONVERSATION

**Quorum means "majority vote."**

Imagine you have 3 senators. A decision is valid if 2 out of 3 agree. You don't need all 3 — just a majority. This prevents deadlock and tolerates one senator being unavailable.

In Cassandra, your data is replicated across N nodes (N = replication factor). When you write or read, you choose how many nodes must confirm before the operation is considered successful.

- **N** = total replicas (e.g., 3)
- **W** = write quorum — how many nodes must confirm the write
- **R** = read quorum — how many nodes must respond to the read

**The magic rule: if W + R > N, you get strong consistency.**

Why? Because with W + R > N, the read set and the write set MUST overlap by at least one node. That node has the latest data. The read will always find it.

---

## PART 2 — THE DIAGRAMS

### Quorum with N=3, W=2, R=2 (Strong Consistency)

```
Write operation: user updates balance from $100 to $150
──────────────────────────────────────────────────────────────────

  Client
    │
    ▼ write balance=$150
  Cassandra Coordinator
    │
    ├──► Node 1: writes $150  ✓ ACK
    ├──► Node 2: writes $150  ✓ ACK   ← W=2 achieved, return OK to client
    └──► Node 3: writes $150  (async, coordinator doesn't wait)

  Client gets "write successful" after 2/3 nodes confirm.
  Node 3 will get it eventually.

Read operation: user reads balance
──────────────────────────────────────────────────────────────────

  Client
    │
    ▼ read balance
  Cassandra Coordinator
    │
    ├──► Node 1: returns $150 with timestamp T2
    ├──► Node 2: returns $150 with timestamp T2   ← R=2 achieved
    └──► Node 3: (not asked)

  Coordinator compares: both have $150 at T2 → return $150 ✓

W + R = 2 + 2 = 4 > N=3 → overlap guaranteed by at least 1 node
```

### The Overlap Proof

```
Why W + R > N guarantees consistency:
───────────────────────────────────────────────────────────────

  Nodes: [1] [2] [3]    N=3

  Write W=2 writes to: [1] [2]         (any 2 of 3)
  Read  R=2 reads from: [2] [3]        (any 2 of 3)

  Overlap: Node [2] must have been written AND is being read
  → Node 2 has the latest data
  → Read will find it

  Even in worst case:
  Write went to: [1] [2]
  Read comes from: [2] [3]  → overlap is [2]  ✓
  Read comes from: [1] [3]  → overlap is [1]  ✓
  Read comes from: [1] [2]  → overlap is [1] and [2]  ✓

  All cases: at least 1 overlapping node → always consistent
```

### Quorum with N=3, W=1, R=1 (Eventual Consistency — Cassandra default)

```
  Client writes $150 → goes to Node 1 only (W=1)
  Client immediately reads → hits Node 3 (R=1)
  Node 3 still has $100 (hasn't received replication yet)
  Client reads $100 → STALE ✗

  W + R = 1 + 1 = 2 ≤ N=3 → no guaranteed overlap
  → Eventual consistency: correct eventually, not immediately
```

---

## PART 3 — CASSANDRA CONSISTENCY LEVELS

```
Cassandra consistency levels (for both reads and writes):
──────────────────────────────────────────────────────────

  ONE          → W=1 or R=1  (fastest, no consistency guarantee)
  TWO          → W=2 or R=2
  THREE        → W=3 or R=3
  QUORUM       → W or R = (N/2)+1  (majority)
                 For N=3: QUORUM = 2
                 For N=5: QUORUM = 3
  ALL          → W or R = N  (strongest, slowest — one node down = failure)
  LOCAL_QUORUM → quorum within the local datacenter only (for multi-DC)
  EACH_QUORUM  → quorum in every datacenter (strongest multi-DC guarantee)

Common production combinations:
  Read ONE + Write QUORUM  → fast reads, consistent writes (good for write-heavy feeds)
  Read QUORUM + Write QUORUM → strong consistency (good for financial data)
  Read ALL + Write ONE     → never use (slow reads, no write consistency)
```

---

## PART 4 — READ REPAIR (THE HIDDEN MECHANISM)

```
What happens when a read finds stale data on one node?
──────────────────────────────────────────────────────────

  Read with R=2:
    Node 1 returns: $150, timestamp T2
    Node 2 returns: $100, timestamp T1   ← stale!

  Coordinator:
    Sees disagreement → picks the one with latest timestamp → $150
    Returns $150 to client ✓

    Background: sends $150 to Node 2 to update it (READ REPAIR)
    Node 2 is now consistent.

  This is how Cassandra heals stale data — reads actively fix inconsistencies.
  Read repair rate is configurable (read_repair_chance, default: 10%)
  → 10% of reads trigger a full repair even if no inconsistency found
```

---

## PART 5 — THE INTERVIEW CONVERSATION

**Interviewer:** "You said Cassandra for the payment system. How do you handle consistency?"

**You (architect answer):**

> "Honestly, for a payment system I wouldn't use Cassandra as the primary transaction store
> — I'd use MySQL or PostgreSQL with ACID guarantees. But if we're discussing Cassandra
> for the transaction log or audit history, here's how consistency works:
>
> Cassandra's replication factor is typically 3. By default it uses W=1, R=1 — eventual
> consistency. For anything financial, you need W + R > N.
>
> I'd configure: write consistency = QUORUM (2/3 nodes must confirm), read consistency = QUORUM
> (read from 2/3 nodes, return the latest). W + R = 4 > N=3, so the read set and write set
> always overlap by at least one node — that node has the latest data.
>
> The trade-off is latency. QUORUM reads wait for the second-slowest node to respond.
> If Node 2 is 50ms and Node 3 is 200ms, a QUORUM read takes 200ms (worse case). With
> ONE consistency, you'd always get the fastest node at maybe 10ms.
>
> For the actual payment debit/credit I'd still use MySQL with InnoDB transactions.
> Cassandra is better suited for the high-write activity log: every transaction event
> published there with QUORUM writes to ensure durability, read with QUORUM for
> consistency during dispute resolution."

---

## PART 6 — TUNABLE CONSISTENCY MATRIX

```
N=3 (3 replicas)
──────────────────────────────────────────────────────────

W  │  R  │  W+R  │ Consistent? │ Availability               │ Use case
───┼─────┼───────┼─────────────┼────────────────────────────┼──────────────────
1  │  1  │   2   │ No          │ Survive 2 node failures    │ Metrics, counters
1  │  2  │   3   │ No          │ Survive 1 node failure     │ Cache-like reads
2  │  1  │   3   │ No          │ Survive 1 node failure     │ Write-heavy, stale OK
2  │  2  │   4   │ Yes ✓       │ Survive 1 node failure     │ Strong consistency
3  │  1  │   4   │ Yes ✓       │ ALL nodes must be up       │ Max durability writes
1  │  3  │   4   │ Yes ✓       │ ALL nodes must be up       │ Max freshness reads
3  │  3  │   6   │ Yes ✓       │ Zero failures tolerated    │ Never use in practice

Rule: if W + R > N → consistent. If a node is down:
  write needs W nodes to be up → if W=2 and 1 is down with N=3: OK (2 of 2 remaining)
  read needs R nodes to be up  → same math

QUORUM (ceil(N/2)+1) for both = strongest practical setting:
  N=3, QUORUM=2: tolerate 1 node failure
  N=5, QUORUM=3: tolerate 2 node failures
```

---

## QUICK REFERENCE CARD

```
Formula: W + R > N  →  strong consistency (at least 1 overlap)

Cassandra defaults: W=1, R=1 (eventual consistency, fastest)
Production for critical data: W=QUORUM, R=QUORUM

Latency impact:
  ONE:    reads/writes complete as soon as 1 node responds  → ~1ms
  QUORUM: wait for (N/2)+1 nodes                           → ~5-10ms
  ALL:    wait for all N nodes                              → limited by slowest node

Read repair: Cassandra auto-heals stale replicas during reads
Hinted handoff: if a node is down during write, coordinator stores a "hint"
                and replays it when the node comes back up

Interview one-liner:
"QUORUM on both reads and writes guarantees that at least one
node in the read set was written to. That node has fresh data.
The cost is you wait for the (N/2)+1th response instead of the first."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** W, R, N is the knob you turn when an interviewer asks "how do you ensure consistency in your Cassandra cluster?" — answer with the math, not just the word "quorum."

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **04 — Chat** | Message history in Cassandra. W=2, R=2, N=3 guarantees read-your-own-writes via quorum overlap. Before W+R>N was understood, users saw their sent messages disappear on refresh. |
| **07 — Payment** | Cassandra ledger entries. W=ALL before 200 OK — every replica has the record. R=QUORUM for audit reads. Sacrifice write latency for zero data loss. |
| **10 — Cloud Storage** | File metadata in Cassandra. W=QUORUM, R=QUORUM. Strong consistency for file ops — user must not re-upload a file that was already saved but not yet replicated. |

**Architect's one-liner for the interview:**
*"W+R greater than N is the quorum overlap guarantee — at least one node that was written to is always in your read set, so you always get fresh data."*
