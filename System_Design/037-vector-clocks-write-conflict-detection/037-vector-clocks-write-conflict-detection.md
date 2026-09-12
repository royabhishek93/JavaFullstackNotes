# Vector Clocks and Version Vectors
### How to Detect Write Conflicts in Distributed Storage

---

## PART 1 — THE STUDENT CONVERSATION

**The problem: you can't trust wall clocks in distributed systems.**

Two servers in different datacenters both have clocks. Server A's clock says 10:00:00.100. Server B's clock says 10:00:00.095. But Server A's event actually happened AFTER Server B's — the clocks just drifted.

If you use timestamps to decide which write wins (Last Write Wins — LWW), you might keep the WRONG value because one server's clock was slightly ahead.

**Vector clocks solve a different problem:** not "which happened first in wall-clock time" but "did A happen BEFORE B, or did they happen concurrently (potentially conflicting)?"

Think of it like version numbers, but one per node.

**Analogy:** You and a colleague are both editing a Google Doc but offline. You make 3 edits. They make 2 edits. When you reconnect, Google Docs knows you both edited the same paragraph at the "same logical time" — and shows you a conflict to resolve. Vector clocks are the mechanism that detects this.

---

## PART 2 — HOW VECTOR CLOCKS WORK

### The Structure

```
Vector clock: one counter per node in the system

  Nodes: A, B, C
  Initial state: { A:0, B:0, C:0 }

  When Node A writes something:
    Increment A's own counter → { A:1, B:0, C:0 }
    Attach this clock to the written value

  When Node B writes something:
    Increment B's own counter → { A:0, B:1, C:0 }
    Attach this clock to the written value

  When Node A sends a message to Node B:
    A's clock: { A:3, B:1, C:0 }
    B receives it, merges: take max of each position
    B's clock after merge: { A:3, B:2, C:0 }
    (B:2 because B increments its own after receiving)
```

### Conflict Detection

```
Shopping cart example (Amazon Dynamo-style):
────────────────────────────────────────────────────────────────

  Initial cart: ["shoes"]  clock: {}

  User adds "hat" from laptop (Node A handles it):
    cart: ["shoes", "hat"]  clock: { A:1 }
    Replicated to Node B and C.

  Network partition occurs. User is online on mobile (Node B) and laptop simultaneously.

  User on laptop (Node A):
    Adds "jacket"
    cart: ["shoes", "hat", "jacket"]  clock: { A:2 }

  User on mobile (Node B) at same time:
    Removes "hat", adds "gloves"
    cart: ["shoes", "gloves"]  clock: { A:1, B:1 }
    (starts from A:1 — the last synced state)

  Network heals. Now we have two versions:
    Version 1: ["shoes", "hat", "jacket"]  clock: { A:2 }
    Version 2: ["shoes", "gloves"]         clock: { A:1, B:1 }

  Compare clocks:
    Is { A:2 } ≥ { A:1, B:1 }?  Check each component:
      A: 2 ≥ 1 ✓
      B: 0 ≥ 1 ✗  (Version 1 has B:0, Version 2 has B:1)
    Neither vector dominates the other → CONCURRENT WRITES → CONFLICT
```

### The "Happened Before" Rules

```
Clock X "happened before" Clock Y  (X → Y)  if:
  Every component of X ≤ corresponding component of Y
  AND at least one component of X < Y

  Example:
    X = { A:1, B:0, C:0 }
    Y = { A:2, B:1, C:0 }
    A: 1≤2 ✓, B: 0≤1 ✓, C: 0≤0 ✓  → X happened before Y
    Y dominates X → Y is the latest version, no conflict

Clock X and Clock Y are CONCURRENT if:
  X does NOT dominate Y AND Y does NOT dominate X

  Example:
    X = { A:2, B:0 }
    Y = { A:1, B:1 }
    X vs Y: A: 2>1, B: 0<1 → neither dominates → CONCURRENT → CONFLICT
```

---

## PART 3 — RESOLVING CONFLICTS

```
What happens after a conflict is detected:
────────────────────────────────────────────────────────────────

Option 1: Last Write Wins (LWW) — simple, lossy
  Keep Version 1 (higher timestamp), discard Version 2.
  Risk: lose legitimate writes.
  Used by: Cassandra (default), DynamoDB (optional).

Option 2: Return all conflicting versions to client — correct, complex
  Return both Version 1 and Version 2 to the application.
  Application decides how to merge.
  Used by: Amazon Dynamo (original paper), Riak.

  Shopping cart resolution:
  App receives both: ["shoes","hat","jacket"] and ["shoes","gloves"]
  Smart merge: union of both = ["shoes","hat","jacket","gloves"]
  (conservative: never silently lose items from a shopping cart)
  Merged clock: { A:2, B:1 } (max of each component)

Option 3: CRDTs (Conflict-free Replicated Data Types) — best for counters/sets
  Data structures designed so concurrent updates always merge correctly.
  G-Counter (grow-only): each node has its own counter, total = sum of all.
  PN-Counter: positive counter + negative counter.
  OR-Set (observed-remove set): tracks which node added each element.
  Used by: Redis (counter type), Riak (native CRDTs), Cassandra counters.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "In your collaborative document editor (Google Docs), how do you handle two users editing the same paragraph simultaneously?"

**You (architect answer):**

> "Conflict detection in collaborative editing is typically handled with Operational
> Transformation (OT) or CRDTs rather than vector clocks directly — but the underlying
> concurrency detection concept is the same.
>
> Here's the problem: User A inserts 'Hello' at position 5. User B simultaneously deletes
> the character at position 3. Both clients had the same document version. Both operations
> are valid, but applying them in different orders produces different results.
>
> With vector clocks: the server tracks the document version each operation was based on.
> If two operations both have a base version of V5, they're concurrent — potential conflict.
> If one has base V5 and the other has base V6, the second was based on V6 which already
> included the first operation — no conflict, just apply in order.
>
> For the actual merge: OT transforms operations based on each other. 'Delete position 3'
> when applied after 'insert at position 5' needs to be transformed to 'delete position 3'
> (position < 5, not affected). But if User B's delete was at position 6, after User A's
> insert it becomes 'delete position 7' (shifted by the insert).
>
> For a simpler conflict model — like two people editing different fields of a document —
> I'd use version vectors per field. Each field has its own vector clock. Concurrent edits
> to the same field are flagged for manual merge. Concurrent edits to different fields
> merge automatically."

---

## PART 5 — VERSION VECTORS VS VECTOR CLOCKS

```
These terms are often confused:

Vector Clock: attached to events/operations
  "This write happened at logical time { A:3, B:2 }"
  Used to determine causal ordering of events

Version Vector: attached to data replicas
  "This replica of the data was last written at { A:3, B:2 }"
  Used to determine which replica is newer or if there's a conflict

In practice:
  DynamoDB / Riak use version vectors on objects
  Cassandra uses timestamps (not vector clocks) → LWW, no conflict detection
  Google Docs uses OT (related concept, tracks operation history)
  Git uses DAG of commits (similar concept, tracks ancestry)

Git analogy:
  Two branches from the same commit → concurrent → merge conflict possible
  One branch contains the other (linear history) → no conflict, just fast-forward
  This is exactly "happened-before" vs "concurrent" in vector clock terms
```

---

## QUICK REFERENCE CARD

```
Vector clock: { node_id: counter, ... } attached to each write
  Increment your own counter on each write
  Merge by taking max of each component on receive

Compare two clocks:
  X happens-before Y: all X[i] ≤ Y[i] AND at least one strictly <
  X concurrent with Y: X not before Y AND Y not before X → CONFLICT

Conflict resolution options:
  LWW (timestamp)     → simple, may lose data
  Return all versions → correct, app must merge
  CRDTs               → auto-merge for specific data types (counters, sets)

Used in:
  Amazon Dynamo (original paper): version vectors on every object
  Riak: native vector clocks
  Cassandra: timestamps only (LWW — no true conflict detection)
  CouchDB: revision IDs (simplified version vectors)
  Git: DAG ancestry (equivalent concept)

Interview one-liner:
"Vector clocks track which writes causally preceded others. If two writes
both increment different nodes' counters from the same base, neither
happened-before the other — they're concurrent — and you have a conflict
to resolve. Timestamps alone can't detect this because clocks drift."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Any time your system allows offline edits or multi-device writes, the interviewer will ask "how do you handle conflicts?" — vector clocks are the precise answer.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **04 — Chat** | Offline message ordering. Alice sends while Bob is offline. Bob replies when online. Vector clocks detect causal ordering vs concurrency — display messages in the right sequence rather than arrival order. |
| **10 — Cloud Storage** | Conflict detection for offline edits. Alice edits on laptop, Bob edits same file on mobile, both offline. {laptop:3} vs {mobile:2} are concurrent → create conflict copy. {laptop:4} dominates {laptop:3} → no conflict, just a newer version. |
| **18 — Text Editor (Google Docs)** | Each edit tagged with vector clock. Concurrent inserts at same position → deterministic merge using clock ordering. This is the foundation of operational transforms. |

**Architect's one-liner for the interview:**
*"Vector clocks don't tell you the wall-clock time — they tell you which writes causally preceded others, so you can distinguish 'Bob edited after Alice' from 'they both edited at the same time and we have a conflict.'"*
