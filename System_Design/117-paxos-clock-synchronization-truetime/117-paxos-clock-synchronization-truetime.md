# Paxos, Clock Synchronization, and TrueTime: Consensus Beyond Raft
### How Google Spanner gets globally consistent transactions without a single shared clock

---

## PART 1 — THE STUDENT CONVERSATION

You already know from [033-leader-election-zookeeper-raft.md](033-leader-election-zookeeper-raft.md) that Raft solves consensus by electing one leader who dictates the order of everything, and everyone else just replicates that order. Raft is deliberately designed to be an "understandable" simplification of an older, more general algorithm called **Paxos** — and the interview-relevant question isn't "which is theoretically better" (they're provably equivalent in what they guarantee), it's "why does Paxos have a reputation for being notoriously hard to implement correctly, and why would anyone still care about it?"

Picture an old-fashioned parliament where representatives can't all be in the same room — they can only send messengers with written proposals. A representative who wants a law passed doesn't just announce it; first they send a messenger asking "would you PROMISE to consider MY proposal number 7, ignoring any earlier or lower-numbered proposal?" (the **Prepare/Promise** phase). Only once a majority of representatives promise do they send a second messenger with the actual proposed law asking for a formal **Accept** vote. This two-phase "ask permission to propose, THEN propose" dance — instead of Raft's simpler "there's one elected leader, everyone defers to them" — is exactly what lets Paxos tolerate MULTIPLE representatives simultaneously believing they should propose something (no strict single-leader requirement), at the cost of being much harder to reason about and implement without subtle bugs, which is precisely why Raft was invented as a teachable, leader-first alternative for the same guarantee.

Now a completely different but related problem: even AFTER you have consensus on "what order did these writes happen in," a globally distributed database like Spanner needs to answer "did transaction A definitely happen BEFORE transaction B," across data centers on different continents, where no two physical clocks are perfectly synchronized. If you naively used each server's local wall-clock timestamp to order transactions, you'd get wrong answers whenever two servers' clocks drifted apart even slightly — a transaction that "happened later" in real life could get a smaller timestamp than one that happened earlier, because its server's clock was running a hair slow.

Google's answer is architecturally bold: instead of pretending clocks are perfectly synced, **TrueTime** openly represents every timestamp as an UNCERTAINTY INTERVAL — "the true time is somewhere between earliest and latest," typically a few milliseconds wide, using GPS receivers and atomic clocks in every data center to keep that interval tight. Then, before committing a transaction, Spanner deliberately **waits out the uncertainty window** (`commit-wait`) so that by the time it tells anyone the transaction succeeded, real wall-clock time has DEFINITELY passed the transaction's timestamp everywhere in the world — turning "we're not sure exactly what time it is" into "we're sure enough time has passed that ordering can never be wrong." A cheaper middle-ground used by systems like CockroachDB, called a **Hybrid Logical Clock (HLC)**, combines a physical clock reading with a logical counter (like the vector clocks in [037-vector-clocks-write-conflict-detection.md](037-vector-clocks-write-conflict-detection.md)) so you get "close enough to real time for humans to read" ordering WITHOUT needing GPS/atomic-clock hardware in every data center, at the cost of a looser causality guarantee than TrueTime's.

---

## PART 2 — THE CONSENSUS & CLOCK DIAGRAMS

### Paxos: Two-Phase Proposal (Basic Paxos, Single Value)

```
Proposer                    Acceptor 1      Acceptor 2      Acceptor 3
────────                    ──────────      ──────────      ──────────
Phase 1 (Prepare):
 "Promise on proposal #7?"  ────────────────────────────────────────>
                            <── Promise ──  <── Promise ──  (no reply, down)
                            (majority of 3 = 2 promised → proceed)

Phase 2 (Accept):
 "Accept value=X, #7"       ────────────────────────────────────────>
                            <── Accepted ── <── Accepted ──
                            (majority accepted → VALUE X IS CHOSEN,
                             durable even if the proposer crashes NOW)

Key subtlety that makes Paxos hard: if TWO proposers race with
proposal numbers #7 and #8 simultaneously, acceptors must always obey
the HIGHER-numbered promise, which can force a proposer's Phase 2 to
fail after its Phase 1 succeeded — requiring a retry with an even
higher number. Multiple competing proposers with no elected leader can
livelock this way, which is why real systems layer a leader-election
step (Multi-Paxos) on top, converging toward Raft's model in practice.
```

### TrueTime: Uncertainty Intervals and Commit-Wait

```
Every TrueTime call returns an INTERVAL, not a point:
  TT.now() = [earliest=100.001s, latest=100.006s]   (~5ms uncertainty,
                                                       kept tight via GPS/
                                                       atomic clocks per DC)

Transaction commit protocol:
  1. Transaction acquires locks, picks commit timestamp s = TT.now().latest
  2. COMMIT WAIT: before releasing locks / acknowledging commit,
     wait until TT.now().earliest > s
     (i.e., wait out the uncertainty so real time has DEFINITELY passed s
      everywhere on Earth, not just on this one server)
  3. Only THEN release locks and return success to the client

Result: if transaction B starts after transaction A's commit is
ACKNOWLEDGED to any client anywhere, B is guaranteed a LARGER
timestamp than A — external consistency across the whole globe,
without a single shared clock, at the cost of ~milliseconds of added
commit latency per transaction (the commit-wait duration).
```

### Hybrid Logical Clock (HLC): Physical Time + Logical Counter

```
HLC timestamp = (physical_time_ms, logical_counter)

Node A sends message at (1719850000123, 0)
Node B receives it, its own physical clock reads 1719850000100 (slightly
behind A's), so B sets its HLC to:
  physical = max(own_physical_clock, received.physical_time) = 1719850000123
  logical  = 0 (reset, since physical part advanced)          → (1719850000123, 0+1=1)

If two events happen with the SAME physical millisecond, the logical
counter breaks the tie, same idea as a vector clock's per-node counter
but collapsed into a single, roughly-time-ordered value that's cheap to
compare and doesn't need GPS hardware — this is why CockroachDB and
YugabyteDB use HLC instead of TrueTime.
```

---

## PART 3 — INTERNALS AND REAL NUMBERS

### Paxos vs Raft vs ZAB (ZooKeeper) — What's Actually Different

```
Paxos:  No inherent leader requirement; any node can propose; correct
        but famously hard to implement/debug because of the "dueling
        proposers" livelock scenario and the subtlety of Multi-Paxos
        optimizations needed for real throughput.

Raft:   Deliberately simplifies by REQUIRING a single elected leader for
        all writes at any given time (a "term"); log replication is
        leader-to-followers only, never follower-to-follower. Same
        safety guarantees as Paxos, dramatically easier to implement
        and to reason about in code review — this is WHY it won in
        industry (etcd, Consul) despite Paxos being older/more general.

ZAB (ZooKeeper Atomic Broadcast): Similar to Raft's leader-based model,
        purpose-built for ZooKeeper's specific need (a durable, ordered
        broadcast log), predates Raft's publication.
```

### Real Numbers

```
TrueTime uncertainty window in Google data centers: typically 1-7ms,
  kept tight by GPS + atomic clock references in every DC — this
  directly bounds commit-wait latency, i.e., the "tax" every Spanner
  write transaction pays for global external consistency.
NTP-only clock sync (no GPS/atomic clocks): uncertainty can be 10s of
  milliseconds to full seconds under network jitter — too loose for
  TrueTime-style commit-wait to be cheap, which is exactly why Google
  invested in dedicated hardware instead of relying on NTP alone.
HLC comparison cost: O(1), just comparing two (physical, logical)
  tuples — negligible overhead vs vector clocks, which grow with the
  number of nodes tracked.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "How does Google Spanner achieve strongly consistent transactions across multiple continents when no two servers' clocks are perfectly synchronized?"

**You (architect answer):**

> "The key insight is Spanner doesn't pretend to have a perfectly synchronized clock — it explicitly represents uncertainty. TrueTime returns an interval, `[earliest, latest]`, bounded to a few milliseconds using GPS and atomic clock references in every data center, rather than one falsely-precise timestamp. Before Spanner acknowledges a transaction's commit, it deliberately waits — commit-wait — until the earliest bound of its NEXT TrueTime call has passed the transaction's chosen commit timestamp. That guarantees that by the time any client anywhere in the world learns the transaction committed, real time actually has moved past that timestamp everywhere on Earth, not just locally. So any later transaction, started after this one's commit is visible, is mathematically guaranteed a larger timestamp — that's what gives Spanner external consistency without a single global clock.
>
> The cost is real: commit-wait adds latency proportional to the uncertainty window, typically a few milliseconds per write transaction — that's the price paid for the guarantee. If I didn't have Google's GPS/atomic-clock investment available, I'd reach for a Hybrid Logical Clock instead — combining physical clock readings with a logical counter, the same idea as a vector clock but collapsed to a single comparable value — which gets me a looser but much cheaper causal ordering guarantee, which is exactly the tradeoff CockroachDB makes."

---

## PART 5 — DECISION FRAMEWORK

| Mechanism | Guarantee | Hardware Cost | Complexity | Used By |
|---|---|---|---|---|
| **Raft** | Leader-based consensus, linearizable log | None special | Low (deliberately simplified) | etcd, Consul, CockroachDB (Raft per range) |
| **Paxos / Multi-Paxos** | Same safety as Raft, no strict single-leader requirement | None special | High (subtle correctness bugs) | Chubby, Spanner's internal replication |
| **ZAB** | Leader-based atomic broadcast | None special | Low-Medium | ZooKeeper |
| **TrueTime + commit-wait** | External consistency (global real-time ordering) | GPS + atomic clocks per DC | Very High (custom hardware/infra) | Google Spanner |
| **Hybrid Logical Clock** | Causal ordering, roughly real-time-comparable | None special | Low-Medium | CockroachDB, YugabyteDB |
| **Plain NTP timestamps** | No ordering guarantee under clock drift | None | Lowest | Anything NOT requiring cross-node ordering guarantees |
