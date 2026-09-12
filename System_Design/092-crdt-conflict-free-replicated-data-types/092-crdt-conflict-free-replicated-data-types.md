# CRDTs: Conflict-Free Replicated Data Types
### How Figma and offline-first apps merge concurrent edits without ever talking to a server

---

## PART 1 — THE STUDENT CONVERSATION

Picture two people each keeping their own private grocery list on their own notepad, with no phone, no way to call each other, while grocery shopping in different aisles of the same store. Later they'll combine lists. If both notepads only ever ADD items (never cross things out), combining them is trivial: just union the two lists together. Order doesn't matter, duplicates don't matter (buying eggs twice on the combined list just means "we need eggs" is still true) — you can merge in any order, any number of times, and always get the same result.

Now suppose one person crosses an item off their own copy. If you just "union the lists" naively, the crossed-off item might reappear from the other person's uncrossed copy. So instead of erasing, they leave a little tombstone mark — "milk (bought)" — rather than deleting the line entirely. Now merging is safe again: whichever copy has the tombstone, the tombstone wins.

This is the whole idea behind a **CRDT (Conflict-free Replicated Data Type)**: design your data structure so that **merging two replicas is a mathematical operation with three specific properties** — commutative (order of merging doesn't matter), associative (grouping of merges doesn't matter), and idempotent (merging the same update twice does nothing extra). If your merge function has all three properties, you can replicate the data to as many nodes as you want, let them go offline, let them see each other's updates in any order or even the same update multiple times, and they are **mathematically guaranteed** to converge to the same final state — with zero central coordinator, zero locking, and zero "transform this operation against that operation" logic.

This is fundamentally different from Operational Transformation (see 090-operational-transformation-collaborative-editing.md), where a central server must transform incoming operations against everything it has already committed. CRDTs push that work into the data structure itself: you don't need anyone to referee, because the merge function can never produce a conflict by construction.

The cost of this freedom: CRDTs typically carry more metadata per element (unique IDs, tombstones for deleted items that can never be fully forgotten without a garbage-collection pass) than OT's lean position-based operations. You're trading network/server simplicity for a heavier per-item footprint.

---

## PART 2 — THE CRDT ARCHITECTURE DIAGRAMS

### G-Counter (Grow-Only Counter) — The Simplest CRDT

```
Use case: distributed "like" counter across 3 datacenter replicas,
no coordination needed, eventually consistent total.

Each replica tracks its OWN increments in a per-replica slot:

Replica A (US-East)          Replica B (EU-West)          Replica C (AP-South)
────────────────────         ────────────────────         ─────────────────────
state = {A:0, B:0, C:0}       state = {A:0, B:0, C:0}       state = {A:0, B:0, C:0}

User likes post (local):     User likes post x3 (local):  User likes post (local):
  A increments OWN slot        B increments OWN slot         C increments OWN slot
  state = {A:1, B:0, C:0}      state = {A:0, B:3, C:0}       state = {A:0, B:0, C:1}

Network partition heals — replicas gossip their state to each other.

MERGE FUNCTION (state-based / CvRDT):
  merge(s1, s2) = { key: max(s1[key], s2[key]) for every key }
  This is commutative, associative, idempotent — take element-wise MAX.

A merges B's state into its own:
  merge({A:1,B:0,C:0}, {A:0,B:3,C:0}) = {A:1, B:3, C:0}

A merges C's state:
  merge({A:1,B:3,C:0}, {A:0,B:0,C:1}) = {A:1, B:3, C:1}

B and C independently do the same merges (in ANY order, ANY number of
times — re-merging an already-seen state changes nothing because max()
is idempotent).

FINAL CONVERGED STATE on all 3 replicas: {A:1, B:3, C:1}
Total count = sum of all slots = 1 + 3 + 1 = 5 likes

Why not just one shared integer with +1 increments? Because two replicas
incrementing the SAME shared counter concurrently is exactly the
lost-update race condition — you'd need locking or CAS across a network
partition, defeating the whole point of offline-tolerant replication.
Splitting the counter per-replica-origin sidesteps the race entirely.
```

### RGA (Replicated Growable Array) — Sequence CRDT for Collaborative Text

```
Problem: G-Counter works for a number, but a text document is an ORDERED
sequence of characters that can be inserted/deleted anywhere. You can't
just "union" characters — you need stable ordering with no central
"position 5" concept, because position 5 means different things on
different replicas mid-edit (this is the same index-shift problem OT
solves via transforms — RGA solves it via unique, immutable position IDs).

Each character gets a globally unique ID: (replicaId, logicalClock)
and a reference to the ID of the character it was inserted AFTER.
This is a Logoot/RGA-style approach — no central authority assigns IDs.

Document "AB" represented as a linked structure of unique-ID nodes:

  START -> [id:(R1,1), char:'A'] -> [id:(R1,2), char:'B'] -> END

Two replicas go OFFLINE and both insert into the SAME logical position
(after 'A') concurrently:

Replica 1 (R1) inserts 'X' after (R1,1):        Replica 2 (R2) inserts 'Y' after (R1,1):
  new node: id:(R1,3), char:'X',                  new node: id:(R2,1), char:'Y',
            after:(R1,1)                                    after:(R1,1)

  R1 local sequence:                              R2 local sequence:
  START -> A(R1,1) -> X(R1,3) -> B(R1,2) -> END   START -> A(R1,1) -> Y(R2,1) -> B(R1,2) -> END

Replicas reconnect and exchange their inserted nodes (operation-based
CmRDT broadcast, or state-based full-structure merge — either works).

TIE-BREAK RULE (deterministic, no coordination required):
  Two nodes inserted after the SAME parent are ordered by a total order
  on their ID tuple — e.g., higher logicalClock wins, ties broken by
  replicaId lexicographic order. Every replica applies the SAME rule,
  so every replica computes the SAME resulting order independently.

  (R1,3) vs (R2,1): compare logicalClock first: 3 > 1 → X sorts before Y

MERGED FINAL SEQUENCE on BOTH replicas (deterministically identical):
  START -> A(R1,1) -> X(R1,3) -> Y(R2,1) -> B(R1,2) -> END
  Rendered text: "AXYB"

Neither replica needed to contact a server or another replica AT THE TIME
of insertion — the merge is purely a function of the two structures and
a fixed, universally-agreed tie-break rule.
```

### Tombstones and Metadata Growth (The Real Cost)

```
Deleting a character in RGA does NOT remove the node — it marks it
with a tombstone flag, because a concurrent remote insert might still
reference "after this node" and needs the node to exist for ordering.

  START -> A(R1,1) -> X(R1,3)[DELETED] -> Y(R2,1) -> B(R1,2) -> END
  Rendered text (tombstones hidden from user): "AYB"

Over a long editing session, tombstones accumulate:
  - A 10,000-character document that has had 50,000 total keystrokes
    (including deletes/retypes) may carry 40,000+ tombstoned nodes
    that are invisible to the user but still consume memory and
    still get transmitted/merged on every sync.
  - Per-character metadata: (replicaId ~8 bytes, logicalClock ~8 bytes,
    parent-ref ~16 bytes, tombstone flag 1 byte) ≈ 33+ bytes of overhead
    PER CHARACTER, dwarfing the 1-2 bytes of actual text content.

Garbage collection strategy used by production CRDT libraries
(e.g., Automerge, Yjs):
  - Once ALL replicas have acknowledged they've seen a tombstoned node
    (tracked via vector clocks / version vectors, see
    037-vector-clocks-write-conflict-detection.md), it's safe to
    physically compact it out of the structure.
  - Yjs specifically uses "integer sequence" compaction: contiguous
    surviving characters from the same insert are merged back into a
    single string run, and long-dead tombstone runs are periodically
    pruned once causal stability is confirmed.
  - This GC step is the single biggest practical engineering challenge
    in production CRDT text editors — skip it and memory grows unbounded
    over a long-lived document's history.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### State-Based (CvRDT) vs Operation-Based (CmRDT)

```
CvRDT (Convergent / state-based):
  - Replicas exchange their FULL current state (or a delta of it)
  - merge(stateA, stateB) -> mergedState must be commutative,
    associative, idempotent
  - Simple to reason about, but can be bandwidth-heavy for large
    documents if you naively ship the whole state on every sync
  - Example: G-Counter above — ship the whole {A:n,B:n,C:n} map

CmRDT (Commutative / operation-based):
  - Replicas exchange individual OPERATIONS (e.g., "insert char X after
    node R1,1"), not full state
  - Requires a reliable broadcast channel that delivers every operation
    to every replica AT LEAST ONCE (duplicates are fine due to
    idempotency design, but drops are NOT fine — a missing operation
    means a permanently missing edit)
  - Lower bandwidth per sync, but the delivery-guarantee requirement
    pushes complexity into the transport layer
  - Example: RGA insert/delete ops above

Most production systems (Automerge, Yjs) are hybrid: operation-based
for live real-time sync, with periodic state-based snapshots for fast
new-client bootstrap and GC compaction.
```

### G-Counter Implementation (Java)

```java
public class GCounter {
    private final String replicaId;
    private final Map<String, Long> counts = new ConcurrentHashMap<>();

    public GCounter(String replicaId) {
        this.replicaId = replicaId;
        counts.put(replicaId, 0L);
    }

    // Local increment — only ever touches OUR OWN slot, never another replica's
    public void increment() {
        counts.merge(replicaId, 1L, Long::sum);
    }

    public long value() {
        return counts.values().stream().mapToLong(Long::longValue).sum();
    }

    // The merge function: commutative, associative, idempotent by construction
    public void mergeFrom(GCounter other) {
        for (Map.Entry<String, Long> e : other.counts.entrySet()) {
            counts.merge(e.getKey(), e.getValue(), Math::max);
        }
    }
}

// Usage across 3 replicas after a network partition heals:
GCounter replicaA = new GCounter("A"); replicaA.increment();               // {A:1}
GCounter replicaB = new GCounter("B"); replicaB.increment(); replicaB.increment(); replicaB.increment(); // {B:3}
GCounter replicaC = new GCounter("C"); replicaC.increment();               // {C:1}

replicaA.mergeFrom(replicaB);   // A: {A:1, B:3}
replicaA.mergeFrom(replicaC);   // A: {A:1, B:3, C:1}
replicaA.value();               // 5 — merge order doesn't matter, re-merging is a no-op
```

### RGA Node Structure and Insert Logic (Java)

```java
public class RgaNode implements Comparable<RgaNode> {
    final String replicaId;
    final long logicalClock;   // Lamport clock, see 034-gossip-protocol-node-discovery.md
    char value;
    boolean tombstoned = false;
    RgaNode parentRef;         // "insert after this node" pointer

    @Override
    public int compareTo(RgaNode other) {
        // Total order tie-break — every replica MUST use this exact rule
        if (this.logicalClock != other.logicalClock)
            return Long.compare(other.logicalClock, this.logicalClock); // higher clock first
        return other.replicaId.compareTo(this.replicaId);
    }
}

public class RgaSequence {
    private final LinkedList<RgaNode> nodes = new LinkedList<>();
    private long lamportClock = 0;
    private final String replicaId;

    // Local insert: create a new node, broadcast it, apply immediately
    public RgaNode localInsert(RgaNode afterNode, char c) {
        lamportClock++;
        RgaNode node = new RgaNode(replicaId, lamportClock, c, afterNode);
        applyRemoteInsert(node);   // apply to self immediately for local echo
        broadcastToPeers(node);   // op-based propagation
        return node;
    }

    // Remote insert: place the node deterministically among siblings of the
    // same parent using the total order — this is what guarantees convergence
    public void applyRemoteInsert(RgaNode node) {
        int insertIdx = nodes.indexOf(node.parentRef) + 1;
        while (insertIdx < nodes.size()
               && nodes.get(insertIdx).parentRef == node.parentRef
               && nodes.get(insertIdx).compareTo(node) < 0) {
            insertIdx++;   // skip past siblings that sort BEFORE this node
        }
        nodes.add(insertIdx, node);
    }

    public void applyRemoteDelete(String replicaId, long logicalClock) {
        nodes.stream()
             .filter(n -> n.replicaId.equals(replicaId) && n.logicalClock == logicalClock)
             .findFirst()
             .ifPresent(n -> n.tombstoned = true);   // never physically remove here
    }

    public String render() {
        StringBuilder sb = new StringBuilder();
        for (RgaNode n : nodes) if (!n.tombstoned) sb.append(n.value);
        return sb.toString();
    }
}
```

### Real Numbers: Overhead and Throughput

```
Metadata overhead per character (Yjs production measurements, roughly):
  - Naive per-char CRDT ID: 33-40 bytes/char (as detailed in Part 2)
  - Optimized "run-length" encoding (Yjs, Automerge): batches contiguous
    same-origin inserts into a single ID range → drops to ~2-4 bytes/char
    amortized for typical typing patterns (not one-ID-per-keystroke, but
    one-ID-per-contiguous-insert-run)

Sync payload size:
  - CmRDT operation broadcast: single-character insert ≈ 40-60 bytes
    (id + parent-ref + char + metadata), comparable to an OT op
  - Full CvRDT state sync for a 5,000-character doc with moderate edit
    history: 50-150 KB uncompressed, ~15-40 KB after gzip — this is why
    CvRDT full-state sync is normally reserved for initial bootstrap,
    not every keystroke

Offline merge time: merging two divergent RGA sequences of ~5,000 nodes
each takes low-single-digit milliseconds on typical hardware — the
sort/insert-position lookup is O(log n) to O(n) depending on
implementation (tree-based RGA implementations like Yjs's use a
balanced structure to keep this sub-linear even for large documents).

Figma's real-world case (publicly discussed in their engineering blog):
they use a custom CRDT-like multiplayer system (not textbook RGA, but
the same core commutative-merge philosophy) for their canvas objects,
because vector shapes/properties merge more like independent
last-writer-wins fields per property than like a linear text sequence —
a reminder that "CRDT" is a family of techniques, not one fixed algorithm.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "You're building an offline-first collaborative whiteboard — users can lose connectivity for minutes at a time, keep editing locally, and need their changes to merge automatically when they reconnect, with no server available to referee conflicts in real time. How would you design the data model?"

**You (architect answer):**

> "The moment 'no server available to referee in real time' is a hard requirement, Operational Transformation is off the table — OT fundamentally needs a central authority to transform incoming operations against everything it's already committed, and that authority has to be reachable at merge time. CRDTs solve the same convergence problem without that requirement, because the merge logic lives inside the data structure itself rather than in a coordinating service.
>
> For whiteboard objects — shapes, positions, styling — I'd model each object's properties as independent CRDT registers, roughly last-writer-wins per field with a Lamport or hybrid logical clock for tie-breaking, since two users are unlikely to fight over the exact same pixel property at the exact same instant, and if they do, a deterministic tie-break is an acceptable outcome. For anything sequence-like — say, an ordered list of shapes in a layer stack, or freeform text labels — I'd use a sequence CRDT like RGA, where every inserted element gets a globally unique ID and a reference to what it was inserted after, so two offline clients can independently insert into 'the same visual position' and still converge to one deterministic order once they resync, with zero coordination at insert time.
>
> The tradeoff I'd flag upfront is metadata overhead. Naive per-element CRDT IDs can be tens of bytes of bookkeeping per user-visible unit of content, dwarfing the actual data — and deletions can't be physically removed immediately, because a concurrently-arriving remote operation might still reference that deleted element for its own ordering. Those tombstones accumulate. My mitigation is to track causal stability with a version vector — once I can prove every replica has seen a tombstone, I compact it out during a periodic garbage-collection pass, the same approach production CRDT libraries like Yjs and Automerge use. I'd also batch contiguous same-origin insertions into a single ID range rather than one ID per character, which is what actually gets the overhead down to a few bytes per character in practice instead of tens."

---

## PART 5 — DECISION FRAMEWORK

### CRDT vs Alternatives for Conflict-Free Merging

| Approach | How It Works | Consistency/Tradeoff | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **CRDT (CvRDT/CmRDT)** | Merge function is commutative/associative/idempotent by construction; no central authority | Strong eventual consistency, provably convergent | Works fully offline; converges whenever peers next sync | Medium-High (choosing the right CRDT type per data shape) | Unbounded tombstone/metadata growth without a GC pass |
| **Operational Transformation (see 090)** | Central server transforms ops against committed history | Strong eventual consistency, but requires the server | 50-150ms with server reachable; broken if server unreachable | High (transform function correctness) | No offline support — needs a reachable authority to merge |
| **Last-write-wins (LWW) register** | Every field has a timestamp; highest timestamp wins on merge | Convergent but LOSSY — loses the "losing" write entirely | Instant, trivially offline-capable | Very low | Any case where losing a concurrent write is unacceptable (e.g., two people editing different parts of the "same" field) |
| **3-way merge (git-style)** | Diff both replicas against a common ancestor, auto-merge non-overlapping changes, flag true conflicts to a human | Not automatically convergent — conflicts need manual resolution | Merge is fast; conflict resolution is human-speed | Medium | Frequent overlapping edits create constant manual-merge friction, unsuitable for real-time collab |
| **Central DB with optimistic locking** (see 021-optimistic-vs-pessimistic-locking.md) | Version column, reject conflicting writes, client retries | Strongly consistent but requires connectivity to reject/retry | Needs round-trip to DB per write | Low-Medium | No offline support at all; retries under high contention degrade UX |

### When CRDTs Are the Right Choice

```
Use CRDTs when:
  ✓ Clients must support extended offline editing (mobile apps, spotty wifi)
  ✓ You want true peer-to-peer sync with no mandatory central server
  ✓ Your data naturally decomposes into independently-mergeable pieces
    (counters, sets, per-field registers, ordered sequences)
  ✓ You can afford to invest in a garbage-collection strategy for tombstones
  ✓ You need mathematically provable convergence, not "works in our test suite"

Skip CRDTs when:
  ✗ You always have a reliable, low-latency connection to a central server
    anyway — OT or simple server-authoritative locking is simpler to build
  ✗ Your data model is highly relational / cross-references many entities
    with strict invariants (CRDTs shine on independent/loosely-coupled data)
  ✗ Metadata overhead is a hard constraint (embedded/IoT devices with tight
    memory budgets) and you can't run periodic GC compaction
  ✗ You need strong (not eventual) consistency — e.g., a bank balance that
    must never be read in a transiently-inconsistent state
```

---

## QUICK REFERENCE CARD

```
MERGE FUNCTION REQUIREMENTS (must hold for correctness):
  Commutative:  merge(a, b) == merge(b, a)
  Associative:  merge(merge(a, b), c) == merge(a, merge(b, c))
  Idempotent:   merge(a, a) == a

CvRDT (state-based):  ship full/delta state, merge() combines states
CmRDT (op-based):     ship individual ops, requires reliable at-least-once broadcast

G-COUNTER:
  state = { replicaId -> count }     (each replica writes ONLY its own slot)
  merge(s1, s2) = elementwise max()
  value() = sum of all slots

RGA / SEQUENCE CRDT (collaborative text/lists):
  each element: (replicaId, logicalClock, parentRef, tombstoneFlag)
  insert: place deterministically among siblings via total order (clock, then replicaId)
  delete: mark tombstoned, never physically remove until causal stability proven
  render: skip tombstoned elements

GARBAGE COLLECTION:
  track causal stability via version/vector clocks (see 037-vector-clocks-write-conflict-detection.md)
  once ALL replicas have seen a tombstone -> safe to physically compact

CROSS-REF: 090-operational-transformation-collaborative-editing.md (central-server alternative)
           037-vector-clocks-write-conflict-detection.md (causal stability tracking)
           079-google-drive-cloud-storage/ (offline sync case study)
```
