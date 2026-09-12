# Operational Transformation (OT): Resolving Concurrent Edits
### How Google Docs and Etherpad let two people type in the same sentence at the same time without corrupting the document

---

## PART 1 — THE STUDENT CONVERSATION

Imagine you and a coworker are both editing the same physical piece of paper at the same time, but you're in different rooms, and a courier carries your changes back and forth. You cross out a word at position 12. At the exact same moment, your coworker inserts a sentence at position 5. By the time the courier delivers your coworker's change to your paper, your "position 12" doesn't mean the same thing anymore — the sentence they inserted shifted everything after position 5 to the right. If you blindly apply "cross out word at position 12" now, you'll cross out the wrong word entirely.

This is the **index shift problem**, and it's the core reason naive "replay the edit at the same position" collaborative editing breaks. Every edit is expressed as an operation relative to a document state, but by the time that operation reaches another replica, the document has already moved on.

Operational Transformation is the courier's rulebook: a mathematical procedure that takes two concurrent operations and **rewrites one of them** so that, no matter which order they're applied in, every replica ends up with the identical final document. It doesn't prevent concurrent edits — it makes concurrent edits commute.

Map the analogy to real terms:
- **Operation** — a small, structured description of a change: `insert(pos, text)` or `delete(pos, length)`. Not "the new document", just the delta.
- **Revision number** — a version counter on the document. Every operation is tagged with the revision it was created against ("I made this edit when the doc was at revision 47").
- **Transform function `xform(opA, opB)`** — given two operations that were both created against the *same* revision (i.e., concurrently, neither had seen the other), produce an adjusted version of `opA` that accounts for the fact that `opB` already happened.
- **Server-authoritative OT** — instead of every client transforming against every other client (which gets combinatorially painful), one server is the single source of truth. Clients send `(operation, revision)` to the server; the server transforms the incoming op against every op it has committed since that revision, applies the transformed op, bumps the revision, and broadcasts the transformed op to everyone else.
- **TP2 property (Transformation Property 2)** — the correctness invariant: transforming `opA` against `opB` and then `opB` against `opA` must yield a state where applying `(opA', opB)` and `(opB', opA)` in either valid order produces the *same* document. This is what makes convergence provable rather than "it seems to work in testing."

Why not just lock the document while someone edits it? Because that's not collaborative editing, that's a queue — and it's exactly what OT and CRDTs (see 092-crdt-conflict-free-replicated-data-types.md) exist to avoid.

---

## PART 2 — THE OT ARCHITECTURE DIAGRAMS

### Concurrent Insert + Delete: The Canonical Example

```
Starting document (revision 10): "Hello"
                                    H e l l o
Character positions:               0 1 2 3 4

Client A (Alice)                                      Client B (Bob)
─────────────────                                      ─────────────
Sees "Hello" @ rev 10                                   Sees "Hello" @ rev 10

Alice inserts "X" at position 2                         Bob deletes 1 char at position 3
  op_A = insert(2, "X")                                   op_B = delete(3, 1)
  Alice's local doc → "HeXllo"                            Bob's local doc → "Helo"
  (locally applied immediately,                           (locally applied immediately,
   sent to server tagged rev=10)                           sent to server tagged rev=10)

                    Both ops arrive at the SAME server, both claim base revision 10
                    → they are CONCURRENT. Server must transform.

Server has already committed op_A first (arrived a few ms earlier):
  Server document is now "HeXllo" @ revision 11

  Now op_B = delete(3, 1) arrives, still tagged rev=10.
  Server must transform op_B against op_A before applying it.

  xform(delete(3,1), insert(2,"X")):
    op_A inserted 1 char at position 2, which is <= op_B's position 3
    → op_B's position must shift right by the length of the insert
    → op_B' = delete(4, 1)

  Why position 4? Because "Hello" → "HeXllo" shifted the 'l' Bob wanted to
  delete (originally at index 3) one slot to the right (now at index 4).

  Server applies op_B' = delete(4,1) to "HeXllo":
    H  e  X  l  l  o
    0  1  2  3  4  5
    delete index 4 ('l') → "HeXlo"

  Server document: "HeXlo" @ revision 12
  Server broadcasts op_A to Bob and op_B' (transformed) back to Alice's
  peers (Alice already has it locally).

Alice's client receives nothing new for her own op (server ACKs rev 11).
Bob's client receives op_A = insert(2,"X") to apply on top of his local "Helo":
    H  e  l  o
    0  1  2  3
    insert "X" at position 2 → "HeXlo"

FINAL STATE — both converge:
  Alice: "HeXlo"   Bob: "HeXlo"   Server: "HeXlo"   ✓ CONVERGED
```

### Server-Authoritative OT Pipeline

```
                         ┌─────────────────────────────┐
                         │   OT SERVER (single truth)   │
                         │  document rev = 47           │
                         │  op_log = [op@42, op@43,      │
                         │            op@44, op@45,       │
                         │            op@46]              │
                         └──────────────┬────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                               │                               │
        v                               v                               v
   Client A (rev 45)              Client B (rev 47)              Client C (rev 46)
   sends: insert(9,"!")           sends: delete(2,3)             sends: insert(0,"# ")
   base_rev = 45                  base_rev = 47                  base_rev = 46
        │                               │                               │
        └───────────────┬───────────────┴───────────────┬───────────────┘
                         v                                v
              1. Server receives op from A (base_rev=45)
                 Missed ops: [op@46, op@47]  (2 ops committed since A last synced)
                 Transform op_A against op@46, then result against op@47
                 → op_A' (adjusted for 2 concurrent edits)
                 Apply op_A' → doc is now rev 48
                 Broadcast op_A' to B and C

              2. Server receives op from C (base_rev=46)
                 Missed ops: [op@47, op_A' (rev48)]
                 Transform op_C against both in sequence → op_C'
                 Apply op_C' → doc is now rev 49
                 Broadcast op_C' to A and B

              3. Server receives op from B (base_rev=47) — already current
                 Missed ops: [op_A'(48), op_C'(49)]
                 Transform op_B against both → op_B'
                 Apply op_B' → doc is now rev 50
                 Broadcast op_B' to A and C

   Key invariant: the SERVER'S op_log is the append-only sequence of truth.
   Clients never apply their own raw op to remote peers — only the
   server-transformed version is ever broadcast. This is why OT needs a
   central authority (unlike CRDTs, which don't).
```

### Failure Mode: Out-of-Order Delivery / Network Partition

```
Client A goes offline for 8 seconds mid-edit (flaky wifi).
While offline, it queues 3 local ops: op1, op2, op3 (each built on the
previous local state, all tagged with base_rev=200, the last rev A saw).

Meanwhile the server has moved on to rev 205 from other clients.

Reconnect:
  Client A sends op1 (base_rev=200) → server transforms against
  [rev201..205] → op1' applied, doc → rev 206
                → server sends op1' ACK + the 5 missed remote ops to A
                → A applies the 5 missed ops locally to catch its view up

  Client A still has op2, op3 queued LOCALLY against its OLD state.
  → A must first transform op2 and op3 against its own op1 AND the
    5 newly-received remote ops before sending them (this is why real OT
    clients maintain a small pending-ops buffer + client-side transform,
    not just a fire-and-forget queue).

  If the client skips this step and sends op2 with a stale base_rev,
  the server transform will still mathematically converge (TP2 holds),
  but the user's LOCAL view will visibly "jump" when the correction
  arrives — a classic OT bug seen in early Etherpad/Google Wave clients.

Mitigation used by production OT systems (Google Docs, ShareDB):
  - Client keeps exactly one "in-flight" op awaiting server ACK
  - Additional local edits are composed into a single "buffer" op
  - On ACK, buffer is transformed against any newly broadcast ops, then sent
  - This bounds the client-side transform complexity to O(1) pending ops,
    not O(n) queued ops — critical for typing-speed responsiveness
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### The Operation Model

```java
// A minimal operation representation used by real OT engines (ShareDB, ot.js)
public abstract class Operation {
    int position;
}

public class InsertOp extends Operation {
    String text;
    InsertOp(int position, String text) {
        this.position = position;
        this.text = text;
    }
}

public class DeleteOp extends Operation {
    int length;
    DeleteOp(int position, int length) {
        this.position = position;
        this.length = length;
    }
}

// Every op carries the revision it was authored against
public class TaggedOperation {
    Operation op;
    int baseRevision;   // e.g. 45 — "I wrote this when the doc was at rev 45"
    String clientId;
}
```

### The Transform Function — Insert/Insert, Insert/Delete, Delete/Delete

```java
public class OTTransform {

    // Transform opA against opB: both were created concurrently (same base revision).
    // Returns opA' — an adjusted version of opA that can be safely applied
    // AFTER opB has already been applied.
    public static Operation transform(Operation opA, Operation opB) {

        if (opA instanceof InsertOp && opB instanceof InsertOp) {
            InsertOp a = (InsertOp) opA, b = (InsertOp) opB;
            if (a.position < b.position ||
               (a.position == b.position && a.clientIdLessThan(b))) {
                // a comes first, no shift needed
                return new InsertOp(a.position, a.text);
            } else {
                // b's insert already pushed a's target position to the right
                return new InsertOp(a.position + b.text.length(), a.text);
            }
        }

        if (opA instanceof DeleteOp && opB instanceof InsertOp) {
            DeleteOp a = (DeleteOp) opA; InsertOp b = (InsertOp) opB;
            if (b.position <= a.position) {
                // b inserted before a's delete range → shift a right
                return new DeleteOp(a.position + b.text.length(), a.length);
            }
            return new DeleteOp(a.position, a.length); // no overlap, no shift
        }

        if (opA instanceof InsertOp && opB instanceof DeleteOp) {
            InsertOp a = (InsertOp) opA; DeleteOp b = (DeleteOp) opB;
            if (a.position <= b.position) {
                return new InsertOp(a.position, a.text); // unaffected
            }
            // a's insert point was inside/after b's deleted range → shift left
            int shift = Math.min(a.position - b.position, b.length);
            return new InsertOp(a.position - shift, a.text);
        }

        if (opA instanceof DeleteOp && opB instanceof DeleteOp) {
            DeleteOp a = (DeleteOp) opA, b = (DeleteOp) opB;
            if (a.position >= b.position + b.length) {
                // a's range is entirely after b's deleted range
                return new DeleteOp(a.position - b.length, a.length);
            }
            if (a.position + a.length <= b.position) {
                return new DeleteOp(a.position, a.length); // no overlap
            }
            // Overlapping delete ranges — the classic hard case.
            // Real engines (ot.js) compute the intersection and only
            // delete the characters NOT already removed by b.
            int newPos = Math.min(a.position, b.position);
            int overlapStart = Math.max(a.position, b.position);
            int overlapEnd = Math.min(a.position + a.length, b.position + b.length);
            int overlap = Math.max(0, overlapEnd - overlapStart);
            int newLen = Math.max(0, a.length - overlap);
            return new DeleteOp(newPos, newLen);
        }
        throw new IllegalStateException("Unhandled op combination");
    }
}
```

### Server-Side Apply Loop (ShareDB-Style)

```java
@Service
public class OTDocumentServer {

    private final Map<String, DocumentState> documents = new ConcurrentHashMap<>();

    public synchronized TransformResult applyClientOp(
            String docId, TaggedOperation clientOp) {

        DocumentState doc = documents.get(docId);
        int missedCount = doc.currentRevision - clientOp.baseRevision;

        if (missedCount < 0) {
            throw new IllegalStateException("Client references future revision");
        }

        Operation transformed = clientOp.op;
        // Transform against every committed op the client hasn't seen yet,
        // in the exact order they were committed — order matters for TP2.
        for (int i = doc.opLog.size() - missedCount; i < doc.opLog.size(); i++) {
            transformed = OTTransform.transform(transformed, doc.opLog.get(i));
        }

        doc.applyToText(transformed);
        doc.opLog.add(transformed);
        doc.currentRevision++;

        // Broadcast the TRANSFORMED op (not the client's original) to all
        // other connected clients via WebSocket (see 039-websocket-vs-sse-vs-long-polling.md)
        broadcastToOthers(docId, clientOp.clientId, transformed, doc.currentRevision);

        return new TransformResult(transformed, doc.currentRevision);
    }
}
```

### Real Numbers: Latency, Throughput, and the Op Log

```
Typing latency budget (Google Docs target, publicly discussed at various
Google engineering talks): local echo must feel instant — under 16ms
(one animation frame) — because the client applies its own op OPTIMISTICALLY
before the server even sees it. The round-trip to the server (50-150ms
typical WAN) only matters for CONVERGENCE with other users, not for the
typing user's own perceived responsiveness.

Op log growth: a typical editing session generates ~1 operation per
keystroke batch (editors debounce rapid keystrokes into ~50-200ms windows,
so "hello" typed quickly might be ONE insert(pos,"hello") op, not 5).
  - Average op size: ~20-80 bytes (position + text + metadata)
  - A 2-hour collaborative editing session: ~2,000-6,000 ops
  - Op log for that session: ~100-300 KB (kept in memory server-side,
    periodically compacted/snapshotted to avoid unbounded growth)

Transform cost: transforming 1 op against N concurrently-missed ops is
O(N) per client message. In practice N stays small (1-5) because clients
sync every keystroke-batch, not once per session. Pathological case:
a client reconnecting after being offline for 10 minutes in a
high-traffic doc could face N in the hundreds — this is why production
systems snapshot the document state periodically and let a reconnecting
client re-fetch the full snapshot + current revision instead of replaying
the entire op log from an ancient base revision.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Design the concurrent editing engine for a Google-Docs-like product. Two users type in the same paragraph at the same time — how do you make sure they don't corrupt each other's changes, and why would you pick your approach over sending the whole document on every keystroke?"

**You (architect answer):**

> "Sending the whole document on every keystroke doesn't scale — for a 50-page document that's megabytes of payload per character typed, and it doesn't even solve the conflict problem, because you still need to decide whose full document 'wins' when two people save at once.
>
> Instead I'd model every edit as a small operation — `insert(position, text)` or `delete(position, length)` — tagged with the document revision the client last saw. This keeps payloads tiny, on the order of tens of bytes per edit, and it's the foundation for Operational Transformation.
>
> The core insight is that two operations created concurrently — before either client has seen the other's change — will reference stale positions once both are applied. If Alice inserts at position 2 and Bob deletes at position 3 based on the same starting document, applying both naively without adjustment can delete the wrong character. OT solves this with a transform function: given two concurrent ops, it rewrites one so that applying them in either order converges to the same final document. This is a provable property — sometimes called TP2 — not just an empirical hope.
>
> I'd make this server-authoritative rather than fully peer-to-peer: one server holds the canonical revision and op log. Clients apply their own edits optimistically and locally for instant feedback, but they send `(operation, base_revision)` to the server. The server transforms the incoming op against everything committed since that revision, applies it, and broadcasts the *transformed* op to everyone else over a WebSocket. This avoids the combinatorial explosion of every client transforming against every other client, and it gives me one place to enforce ordering.
>
> The operational concern I'd flag up front is reconnect behavior. A client that drops offline for even a few seconds can accumulate several local ops against a now-stale base revision. If I naively replay the full backlog against a firehose of server-committed ops, the transform cost grows with how far behind the client is, and a busy document could leave a reconnecting client transforming against hundreds of missed ops. My mitigation is to cap the client to a single in-flight op with any additional local edits composed into one buffered op, and to periodically snapshot the document server-side so a badly-behind client can just re-fetch the current snapshot plus revision number instead of replaying the entire op log from scratch."

---

## PART 5 — DECISION FRAMEWORK

### OT vs Alternatives for Concurrent Multi-User Editing

| Approach | How It Works | Consistency/Tradeoff | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **Pessimistic locking (edit lock)** | Only one user can edit a section/doc at a time | Strongly consistent, no conflicts possible | Instant for lock holder, blocked for others | Low | Terrible UX for real collaboration; lock holder disconnecting strands others |
| **Last-write-wins (full doc overwrite)** | Whole document replaced on save, timestamp/version decides winner | Silently loses data — no merge at all | Fast | Very low | Any true concurrent edit — one user's work vanishes |
| **Operational Transformation** | Ops transformed against concurrently-committed ops via a central server | Strong eventual consistency, provable convergence (TP2) | 50-150ms to converge across clients | High (transform function correctness is subtle) | Requires the server to be available; transform bugs are notoriously hard to test exhaustively |
| **CRDTs (see 092-crdt-conflict-free-replicated-data-types.md)** | Merge function is commutative/associative/idempotent, no central authority needed | Strong eventual consistency, mathematically guaranteed merge | Can merge fully offline/peer-to-peer | Medium-High | Metadata overhead (tombstones, unique IDs) grows unboundedly without garbage collection |
| **Google Wave-style OT with client-side prediction** | OT + optimistic local apply + server reconciliation | Same as OT but with better perceived latency | ~16ms perceived (optimistic), 50-150ms actual convergence | High | Same transform correctness burden, plus a rollback/replay path if server rejects |

### When OT Is the Right Choice

```
Use OT when:
  ✓ You already have (or want) a central server as the source of truth
  ✓ Clients are usually online / low-latency to the server (real-time collab, not offline-first)
  ✓ You need tight control over how conflicts resolve (custom transform rules per data type)
  ✓ You're editing linear/sequential structures (text) where position-based ops are natural
  ✓ You want smaller network payloads than full-document diff/sync

Skip OT when:
  ✗ Clients need to edit fully offline for extended periods and merge later (CRDTs fit better)
  ✗ You need peer-to-peer sync with no central server (P2P collaboration tools)
  ✗ Your data model isn't naturally sequence-based (e.g., a graph or set — CRDTs generalize easier)
  ✗ Your team can't invest in exhaustively testing transform function correctness — a subtly
    wrong transform function silently diverges document state, which is very hard to detect
    after the fact (Google Wave's OT bugs were a known contributor to the project's struggles)
```

---

## QUICK REFERENCE CARD

```
CORE MODEL:
  Operation = insert(pos, text) | delete(pos, length)
  TaggedOperation = { op, baseRevision, clientId }

TRANSFORM CONTRACT:
  xform(opA, opB) -> opA'
    opA and opB are CONCURRENT (same baseRevision)
    opA' is safe to apply AFTER opB has already been applied
    Must satisfy TP2: order of transform application doesn't affect final convergence

INSERT/INSERT:   later position wins tie-break by clientId; earlier insert shifts later one right
INSERT/DELETE:   insert position shifts left if it falls inside the deleted range
DELETE/INSERT:   delete position shifts right if insert happened before it
DELETE/DELETE:   compute range overlap, subtract already-deleted overlap length

SERVER LOOP (per incoming client op):
  missed = opLog[baseRevision : currentRevision]
  for each m in missed: op = transform(op, m)
  apply(op); opLog.append(op); currentRevision++
  broadcast(op) to all other clients

CLIENT LOOP:
  apply own op locally IMMEDIATELY (optimistic)
  send (op, baseRevision) to server
  buffer any further local edits into ONE pending op until ACK received
  on receiving remote op: transform against own pending op, then apply

CROSS-REF: 092-crdt-conflict-free-replicated-data-types.md (no-central-server alternative)
           082-google-docs-collaborative-editing/ (case study folder)
           039-websocket-vs-sse-vs-long-polling.md (transport for broadcast)
```
