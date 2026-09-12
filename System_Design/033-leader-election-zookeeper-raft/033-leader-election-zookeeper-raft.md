# Leader Election
### How ZooKeeper and Raft Elect a Leader — What Happens During Election

---

## PART 1 — THE STUDENT CONVERSATION

**Why do distributed systems need a leader?**

Imagine 5 database nodes all receiving write requests. If all 5 can accept writes independently, you'll have conflicts — two nodes both write different values to the same key simultaneously. Split brain.

The solution: designate one node as the **leader** (primary). All writes go through the leader. The leader replicates to followers. Only one writer, no conflicts.

But who picks the leader? You can't have humans manually do it — services restart at 3am. You need an automated, fair election that:
1. Always picks exactly one leader (no split brain)
2. Picks a leader even if some nodes are down
3. Detects when the leader dies and elects a new one automatically

This is the leader election problem. ZooKeeper and Raft are the two dominant solutions in production systems.

---

## PART 2 — ZOOKEEPER-BASED LEADER ELECTION

### How ZooKeeper ephemeral nodes work

```
ZooKeeper stores data in a tree of "znodes" (like a filesystem).
An EPHEMERAL node automatically deletes itself when the creator disconnects.

Leader election using ephemeral sequential nodes:
────────────────────────────────────────────────────────────────────

Step 1: All 5 candidates try to create:
  /election/candidate-0000000001  (Node A creates this)
  /election/candidate-0000000002  (Node B creates this)
  /election/candidate-0000000003  (Node C creates this)
  /election/candidate-0000000004  (Node D creates this)
  /election/candidate-0000000005  (Node E creates this)

  ZooKeeper guarantees sequential numbering — no two nodes get same number.

Step 2: Each node checks: "Am I the LOWEST numbered node?"
  Node A: I created 0001. Is 0001 the lowest? Yes → I AM THE LEADER ✓
  Node B: I created 0002. Is 0002 the lowest? No → I am a follower.
  Node C: I created 0003. Is 0003 the lowest? No → I am a follower.
  ...

Step 3: Each follower watches the node just BELOW its own number:
  Node B (0002) watches Node A (0001) — "tell me if 0001 dies"
  Node C (0003) watches Node B (0002) — "tell me if 0002 dies"
  Node D (0004) watches Node C (0003) — "tell me if 0003 dies"
  Node E (0005) watches Node D (0004) — "tell me if 0004 dies"

  Why watch the one just below? To avoid the "herd effect":
  If all 4 followers watched the leader, when leader dies → 4 simultaneous
  election attempts → thundering herd on ZooKeeper.
  With chain watching: only Node B gets notified, only B re-evaluates.
```

### Leader Failure and Re-election

```
Node A (leader, /election/0000000001) crashes:
────────────────────────────────────────────────────────────────────

  t=0: Node A disconnects from ZooKeeper
  t=1: ZooKeeper detects via session timeout (typically 10–30s)
  t=2: ZooKeeper DELETES /election/0000000001 (ephemeral node auto-deleted)
  t=3: Node B receives notification: "0000000001 was deleted"

  Node B checks: "Am I now the lowest numbered node?"
  Remaining nodes: 0002, 0003, 0004, 0005
  Node B (0002): YES, I am the lowest → Node B becomes leader ✓

  Election completed without any voting, without any coordination.
  No two nodes can become leader simultaneously (ZooKeeper serializes operations).

  Total re-election time: ZooKeeper session timeout = 10–30s
  During this window: writes are rejected (no leader to accept them)
```

---

## PART 3 — RAFT CONSENSUS

### The 3 Roles

```
Raft has 3 roles:
  Leader:     receives all writes, replicates to followers
  Follower:   passive, replicates from leader, responds to client reads
  Candidate:  in election mode, requesting votes

Node states:
  All nodes start as FOLLOWER
  If a follower doesn't hear from leader for election_timeout (150–300ms random):
    → becomes CANDIDATE, starts election
```

### Raft Election Process

```
Normal operation — leader sends heartbeats:
────────────────────────────────────────────────────────────────────

  Leader ──heartbeat──► Follower 1
  Leader ──heartbeat──► Follower 2
  Leader ──heartbeat──► Follower 3
  Leader ──heartbeat──► Follower 4

  All followers reset their election timeout counter on each heartbeat.
  Election timeout: random between 150ms and 300ms (randomized to avoid ties)

Leader crashes (no more heartbeats):
────────────────────────────────────────────────────────────────────

  t=0:    Leader dies
  t=150ms: Follower 2's election timeout fires first (it had the shortest timeout)

  Follower 2 → Candidate:
  1. Increments term counter: term = 5 (was 4)
  2. Votes for itself
  3. Sends RequestVote(term=5, candidateId=Node2, lastLogIndex=99, lastLogTerm=4)
     to all other nodes

  Follower 1 receives RequestVote:
    Checks: Is term 5 > my current term 4? YES.
    Checks: Is Node2's log as up-to-date as mine? YES (lastLogIndex=99).
    Grants vote to Node2. Updates own term to 5.

  Follower 3 receives RequestVote: same check → grants vote.

  Node2: received 3 votes (self + 1 + 3) out of 5 total nodes = majority ✓
  Node2 declares itself LEADER for term=5.
  Node2 immediately sends heartbeats to all followers.

  Time elapsed: ~150ms (one election timeout)
```

### Why Randomized Timeout Prevents Split Vote

```
Problem: if all 4 followers had the same timeout, all 4 become candidates simultaneously.
Each votes for itself. Nobody gets majority. Stalemate.

Solution: each node picks a RANDOM election timeout in range [150ms, 300ms].

Node 2: timeout = 153ms ← first to fire
Node 1: timeout = 201ms ← Node 2 already leader, resets to follower
Node 3: timeout = 267ms ← same
Node 4: timeout = 289ms ← same

One node almost always wins before others even start their election.
Rare ties: both reset to new random timeout → one wins next round.
```

---

## PART 4 — RAFT LOG SAFETY (WHY STALE NODES CAN'T WIN)

```
Raft's safety guarantee: only a node with the most up-to-date log can win.

When voting, each follower checks:
  Is the candidate's lastLogTerm ≥ my lastLogTerm?
  AND if equal: is candidate's lastLogIndex ≥ mine?
  If both: grant vote. Otherwise: deny.

Scenario: Node A (leader) replicated log entries 1–100 to Nodes B, C, D.
Node E was partitioned and only has entries 1–85.

Node A crashes. Election starts.
  Node E becomes candidate first (random timeout).
  Node E asks for votes with lastLogIndex=85.
  Node B (has 100 entries): "85 < 100, candidate is stale. DENY."
  Node C: "DENY." Node D: "DENY."
  Node E cannot win — no majority.

  Node B becomes candidate with lastLogIndex=100.
  Nodes C, D grant votes → B wins → B has all entries → no data loss. ✓
```

---

## PART 5 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your TinyURL service uses ZooKeeper for ID range allocation. What happens during a ZooKeeper leader election?"

**You (architect answer):**

> "ZooKeeper itself runs in a cluster (typically 3 or 5 nodes) using Zab protocol, which is
> similar to Raft. If the ZooKeeper leader fails, the remaining ZooKeeper nodes hold their
> own election — this takes roughly 200ms to a few seconds, which is much faster than the
> 10–30 second session timeout we'd see for application-level elections.
>
> During the ZooKeeper election, ZooKeeper is temporarily unavailable. Any request to
> ZooKeeper — including our TinyURL nodes trying to acquire new ID ranges — will receive
> a connection exception.
>
> The TinyURL nodes handle this with local buffering: each node pre-allocates a range of
> 1,000 IDs from ZooKeeper and serves from its local buffer. If ZooKeeper is down for
> 5 seconds, the node continues generating IDs from its buffer. It only needs ZooKeeper
> when it exhausts its current range (every 1,000 IDs × generation rate).
>
> For extra resilience, I'd configure ZooKeeper with 5 nodes across 3 availability zones.
> With 5 nodes, we can lose 2 simultaneously and still have a 3-node majority for quorum.
> The ZK session timeout is set to 10 seconds — shorter means faster failure detection,
> longer means more tolerance for network blips without unnecessary re-elections."

---

## PART 6 — ZOOKEEPER vs RAFT vs ETCD

```
System comparison:
────────────────────────────────────────────────────────────────────────

                  ZooKeeper          etcd (Raft)        Self-implemented Raft
────────────────  ─────────────────  ─────────────────  ─────────────────────
Protocol          Zab (similar Raft) Raft               Raft
Election time     ~200ms (ZK itself) ~150-300ms         ~150-300ms
Session timeout   10-30s (default)   lease-based        configurable
Maturity          Very mature        Widely used         Depends on impl
Language          Java               Go                  Your choice
Use case          App coordination,  Kubernetes etcd,   Embedded in app
                  distributed locks  service discovery
Data model        Hierarchical znodes Key-value          Key-value
Watches           Yes (event-based)   Watch streams      varies

When ZooKeeper is used:
  Kafka (controller election, topic metadata)
  Hadoop YARN (ResourceManager HA)
  HBase (master election)
  TinyURL (ID range allocation — common interview example)

When etcd is used:
  Kubernetes (all cluster state — API server is the single coordinator)
  Consul (alternative, also supports leader election)
  CockroachDB (distributed transaction coordinator)

Raft resources:
  raft.github.io — visual simulation of Raft election
  "In Search of an Understandable Consensus Algorithm" — the original Raft paper
```

---

## QUICK REFERENCE CARD

```
Leader election: select exactly one leader from N candidates

ZooKeeper approach:
  Each candidate creates /election/candidate-SEQ# (ephemeral + sequential)
  Lowest sequence number = leader
  Each non-leader watches the node just below it (chain watching)
  Leader dies → ZK deletes ephemeral node → next-in-line takes over
  Time: ZK session timeout (10–30s) + election (~1ms)

Raft approach:
  Randomized election timeout (150–300ms) → one node becomes candidate first
  Candidate requests votes: term++, vote for self, ask others
  Others vote if: candidate term ≥ theirs AND candidate log ≥ theirs
  First to get majority (N/2 + 1 votes) wins
  Time: ~150–300ms for initial election, ~300–600ms worst case

Safety guarantee (Raft):
  Node with stale log cannot win → voters deny if candidate log is behind
  At most one leader per term (term number is monotonically increasing)

Real-world election times:
  etcd:       150–300ms (Raft)
  ZooKeeper:  ~200ms (Zab)
  Redis Sentinel: 10–30s (configured session timeout)

Interview one-liner:
"Leader election solves the single-writer problem in distributed systems.
Raft uses randomized timeouts and a log-currency check — the node with the
most up-to-date log wins. This guarantees at most one leader per term
and prevents stale nodes from winning and overwriting committed data."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Any time only one instance should do something — generate IDs, process a scheduled job, own a partition — leader election is the mechanism; knowing ZooKeeper vs Raft vs Redis SETNX shows depth.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **01 — Tiny URL** | ID generation leader — only one service instance should allocate sequential ID ranges at a time. ZooKeeper ephemeral node: winner gets the lock, allocates range [1M..2M], releases, next leader takes [2M..3M]. |
| **07 — Payment** | Scheduled payment processor (recurring charges). Only ONE instance should process a given payment at a time. Leader election ensures no duplicate charges from multiple instances waking up simultaneously. |
| **15 — Distributed Logging** | Kafka partition leadership. One broker is elected primary for each partition. All writes go to the leader, replicas follow. Raft ensures leader election completes within seconds of a broker failure. |

**Architect's one-liner for the interview:**
*"Leader election is how you get a single writer in a distributed system without a human deciding who's in charge — Raft does it with randomized timeouts and a log-currency check so the most up-to-date node wins."*
