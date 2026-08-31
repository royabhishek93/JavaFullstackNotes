# Google Docs — Interview Script
## Design Google Docs / Notion / Confluence (Real-Time Collaborative Editor)
### Speak This Word-for-Word to Your Interviewer

> **How to use this:**
> **Step 1 — Read Big Picture** (PAGE 1): burn the overview into your head.
> **Step 2 — Read Glossary** (PAGE 2): know every term before the deep-dive.
> **Step 3 — Read Component Choices** (PAGE 3): know WHY each tech was chosen.
> **Step 4 — Read the Interview Script** (PAGE 4 onward): speak each step aloud 2-3 times.
>
> **Print tip:** Portrait A4 at 10pt monospace. Landscape for the OT example diagrams.

---

# ═══════════════ PAGE 1 — START HERE ═══════════════

## BIG PICTURE (Understand This Before Anything Else)

> **► STUDY this diagram, don't draw it ◄**
> Google Docs is the HARDEST collaborative system design because of ONE question:
> "Two users edit the same position at the same time. Whose change wins?"
> The answer is: BOTH. The OT algorithm makes both changes visible, correctly.

```
┌─────────────────────────────────────────────────────────────────────┐
│                  GOOGLE DOCS — BIG PICTURE                           │
└─────────────────────────────────────────────────────────────────────┘

ALICE types "H" at position 0     BOB types "D" at position 2
while document shows "BC"          at the same time, same document

        │                                    │
        ▼                                    ▼
┌──────────────────────────────────────────────────┐
│            CLIENT-SIDE OT ENGINE                  │
│  Both clients apply their own op LOCALLY first.  │
│  Alice sees "HBC" immediately (low latency).      │
│  Bob sees "BCD" immediately.                     │
│  Then they sync. Final state must be "HBCD".     │
└──────────────────────────┬───────────────────────┘
                           │ WebSocket
                           ▼
              ┌─────────────────────────────┐
              │  WEBSOCKET GATEWAY          │
              │  Sticky: docId → same server│
              │  ALL users of one doc land  │
              │  on the SAME WS server      │
              └──────────────┬──────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │  DOCUMENT EDITOR SERVICE    │
              │                             │
              │  OT Engine (server-side):   │
              │  "Bob's op was INSERT at 2  │
              │   based on 'BC'. But Alice  │
              │   already inserted at 0.    │
              │   Bob's pos 2 → becomes 3." │
              │                             │
              │  Applies to Redis canonical │
              │  copy. Broadcasts to all.   │
              └──────────────┬──────────────┘
                             │
          ┌──────────────────┼─────────────────┐
          ▼                  ▼                  ▼
 ┌─────────────────┐ ┌───────────────┐ ┌───────────────┐
 │  Redis          │ │    Kafka      │ │   Cassandra   │
 │                 │ │               │ │               │
 │  canonical copy │ │  op events    │ │  ops log      │
 │  version counter│ │  (durability) │ │  (persistent) │
 │  cursor:{u}:{d} │ │               │ │  metadata     │
 └─────────────────┘ └───────────────┘ └───────────────┘
                                               │
                                        ┌──────▼──────┐
                                        │  S3 Blob    │
                                        │  document   │
                                        │  snapshots  │
                                        │  + versions │
                                        └─────────────┘

THE CORE INSIGHT:
  Delta ops, NOT full file. "INSERT H at 0" = ~50 bytes, not 50 KB.
  OT algorithm adjusts positions so both edits apply correctly.
  All ops go through ONE server per document (sticky routing) for
  OT to work — total ordering of operations is required.
  Redis holds the live document. S3 holds the permanent snapshots.
```

---

## RAPID ANSWER — If You Only Have 5 Minutes

*Read this first. Understand the whole answer before going deep.*

```
"I'd design Google Docs with five pieces:

1. REAL-TIME LAYER (WebSocket + sticky routing):
   25 million edit events/sec — REST is impossible (50ms overhead each).
   WebSocket: persistent, bidirectional, ~1ms per event.
   All users editing the same doc MUST land on the same WS server.
   Why: OT (Operational Transformation) requires total ordering of ops.
   We use consistent hashing on documentId for sticky routing.

2. OT ALGORITHM (conflict resolution):
   Alice types 'H' at pos 0, Bob types 'D' at pos 2 concurrently.
   Server receives Alice first → updates canonical to 'HBC'.
   Bob's op arrives: 'insert D at pos 2' was based on 'BC'.
   OT transforms it: pos 2 → pos 3 (Alice's insert shifted it).
   Both edits applied → 'HBCD'. Both users converge.
   Alternative: CRDT (fractional position IDs, used by Figma/Notion).

3. CANONICAL COPY (Redis):
   Redis holds the live, in-memory document being edited.
   Every op: read Redis canonical → apply → write back → broadcast.
   TTL-based: exists only while editors are active.
   When last editor leaves → flush to S3, delete from Redis.

4. PERSISTENCE (Kafka + Cassandra + S3):
   Every op published to Kafka synchronously (before ACK to client).
   Kafka consumer persists to Cassandra ops log.
   Auto-save every 10-20s → snapshot to S3 as minor version.
   Session end → Reconciliation Job: replay all ops on base version
   → create major version in S3 → delete minor versions + ops log.

5. EVENT SOURCING:
   The ops log IS the source of truth. Redis canonical copy is just
   a materialized view — always rebuildable from S3 base + ops.
   Redis fails? Reload from S3 + Cassandra. Zero data loss."
```

---

# ═══════════════ PAGE 2 — GLOSSARY ═══════════════

## Terminology — Know These Before Reading Further

*Print tip: switch to landscape or 9pt font if table wraps.*

```
┌──────────────────┬──────────────────────────────────────────────────────┐
│ Term             │ What It Means (Simply)                               │
├──────────────────┼──────────────────────────────────────────────────────┤
│ OT               │ Operational Transformation. When two users edit the  │
│ (Operational     │ same position concurrently, OT adjusts (transforms)  │
│  Transform)      │ the later-arriving op so both edits are applied.     │
│                  │ "Alice inserted before your position — shift yours." │
├──────────────────┼──────────────────────────────────────────────────────┤
│ CRDT             │ Conflict-free Replicated Data Type. Uses fractional  │
│                  │ position IDs (e.g. 0.25, 0.375) instead of integer   │
│                  │ positions. Positions never collide — no transform    │
│                  │ needed. Used by Figma, Notion, Atom.                 │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Delta Op         │ A change described as "what changed" rather than     │
│                  │ "what the document looks like now." Example:         │
│                  │ { INSERT, pos: 5, char: "H" } — 50 bytes.           │
│                  │ vs. sending the full document — 50 KB.              │
│                  │ 1000× smaller. Required for 25M ops/sec.            │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Canonical Copy   │ The single authoritative version of a document       │
│                  │ while it is being actively edited. Stored in Redis.  │
│                  │ All editors' views converge to this. When the last   │
│                  │ editor leaves, it is flushed to S3.                  │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Sticky Routing   │ All users editing document X are routed to the SAME  │
│                  │ WS server (via consistent hash on docId). Required   │
│                  │ for OT: the server must see ALL ops in order.        │
│                  │ If ops go to different servers, total ordering is    │
│                  │ lost and OT produces wrong results.                  │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Version Counter  │ Redis counter: incremented each time an op is        │
│                  │ applied to the canonical copy. Clients include their  │
│                  │ "version" when sending ops. Server uses this to know  │
│                  │ which concurrent ops to transform against.           │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Reconciliation   │ When the last editor leaves a document, a cleanup    │
│ Job              │ job runs: replays all ops on the base version,       │
│                  │ creates one clean "major version" in S3, deletes all │
│                  │ minor auto-save snapshots and the ops log.           │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Minor Version    │ Auto-save snapshot (every 10-20s during editing).    │
│                  │ e.g. v10.1, v10.2. Temporary — deleted after the     │
│                  │ reconciliation job runs at session end.              │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Major Version    │ A permanent snapshot of the document. Created at     │
│                  │ the start of a session (v10) and at the end (v11).   │
│                  │ Minor versions between them are deleted.             │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Event Sourcing   │ Storing the HISTORY of changes (ops log) rather than │
│                  │ just the current state. State = apply(ops) on base.  │
│                  │ Enables undo, version history, recovery from Redis   │
│                  │ failure, and audit trails.                           │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Forward Secrecy  │ (In OT context) An op with version=5 can still be    │
│ (version field)  │ processed even if server is at version 10 — the      │
│                  │ server transforms it against ops 6, 7, 8, 9, 10.    │
├──────────────────┼──────────────────────────────────────────────────────┤
│ X3DH / Double    │ Not applicable here (that's WhatsApp). Google Docs   │
│ Ratchet          │ is NOT end-to-end encrypted. Google CAN read docs.  │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Cursor Position  │ Each active user's cursor shown to all collaborators.│
│                  │ Stored in Redis with 30s TTL. Also OT-transformed:   │
│                  │ if someone inserts before your cursor, cursor shifts.│
└──────────────────┴──────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 3 — WHY EACH COMPONENT ═══════════════

## Component Choices — Why We Picked Each One

```
┌─────────────────────┬──────────────────────────────────────────────────┐
│  COMPONENT          │  WHY THIS? NOT SOMETHING ELSE?                   │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  WebSocket          │ WHY: 25M edit events/sec. REST has ~50ms         │
│  (not REST)         │ overhead per call. At 25M/sec via REST:           │
│                     │ 25M × 50ms = crushing latency + CPU.             │
│                     │ WebSocket: persistent connection, ~1ms overhead. │
│                     │ Server can PUSH transformed op back to all       │
│                     │ collaborators immediately. REST can't push.      │
│                     │                                                  │
│                     │ WHY NOT Long-Polling: Reconnects constantly.     │
│                     │ Still slower. Doesn't scale to 25M ops/sec.     │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Sticky Routing     │ WHY: OT requires TOTAL ORDERING of operations.   │
│  (consistent hash   │ If Alice's op goes to Server A and Bob's op goes │
│   on docId)         │ to Server B simultaneously, A and B may apply    │
│                     │ them in different orders → documents DIVERGE.   │
│                     │ Sticky routing: ALL ops for docX go to Server 3. │
│                     │ Server 3 is the single arbiter of order.         │
│                     │                                                  │
│                     │ WHY NOT random routing: Breaks OT. Different     │
│                     │ servers = different op ordering = divergence.    │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Redis              │ WHY: Canonical copy needs sub-ms read/write.     │
│  (Canonical Copy)   │ Each edit = READ canonical + apply op + WRITE.   │
│                     │ At 5 ops/sec × 5M active docs = 25M ops/sec.    │
│                     │ Redis: microsecond reads/writes. No other DB     │
│                     │ comes close at this speed.                       │
│                     │ Also: TTL support — auto-delete when session ends.│
│                     │                                                  │
│                     │ WHY NOT MySQL/Cassandra: Millisecond reads,      │
│                     │ not microseconds. Can't sustain 25M ops/sec.    │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  OT Algorithm       │ WHY: Two users type at the same position at the  │
│  (not locking)      │ same time. Options:                              │
│                     │ (1) Pessimistic lock: Block all other users.     │
│                     │     Terrible — destroys the collaboration UX.   │
│                     │ (2) Optimistic lock: Both edit, then merge       │
│                     │     manually. Also terrible UX.                  │
│                     │ (3) OT: Both edits applied automatically.        │
│                     │     Google Docs standard since 2010.             │
│                     │                                                  │
│                     │ WHY NOT CRDT: OT uses less storage per char.     │
│                     │ CRDT attaches a position ID to every character.  │
│                     │ For very large docs, CRDT storage explodes.      │
│                     │ CRDT IS better for offline editing (switch then).│
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  S3                 │ WHY: Document versions are immutable blobs.      │
│  (Snapshots)        │ 10B docs × avg 50 KB × 10 versions = 5 PB.     │
│                     │ No DB stores 5 PB of binary content cheaply.    │
│                     │ S3: unlimited, cheap, CDN-friendly.             │
│                     │                                                  │
│                     │ WHY NOT Cassandra for doc content: Cassandra     │
│                     │ stores small values efficiently. A 50 KB doc     │
│                     │ blob is too large per row. S3 is designed for   │
│                     │ exactly this: large blobs.                       │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Cassandra          │ WHY: Ops log writes are high-volume and time-    │
│  (Ops Log +         │ series in nature. Partition by docId. Cluster   │
│   Metadata)         │ by op timestamp. "All ops for doc-123 after      │
│                     │ time T" = single-partition range scan.           │
│                     │ Also: document metadata (title, versions list)   │
│                     │ — high read throughput, no complex joins.        │
│                     │                                                  │
│                     │ WHY NOT MySQL: Write throughput for ops log.     │
│                     │ Ops are transient (deleted after reconciliation) │
│                     │ — no FK constraints needed. Cassandra fits.      │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Kafka              │ WHY: Ops must be durable BEFORE the ACK is sent  │
│  (Durability)       │ to the client. If WS server crashes after ACK   │
│                     │ but before writing to Cassandra, op is lost.    │
│                     │ Kafka: publish first (synchronous), then ACK    │
│                     │ the client. Kafka consumer writes to Cassandra  │
│                     │ at its own pace. Ops never lost.                │
│                     │                                                  │
│                     │ WHY NOT write directly to Cassandra: Same issue.│
│                     │ Kafka decouples the WS server from DB latency.  │
│                     │                                                  │
└─────────────────────┴──────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 4+ — FULL INTERVIEW SCRIPT ═══════════════

---

## OPENING — When Interviewer Says "Design Google Docs"

*"Great question — this is one of the most algorithmically interesting system designs.
The core challenge isn't storage or scale — it's conflict resolution.
When two users edit the same position simultaneously, who wins?
The answer is BOTH — and the algorithm that makes this work is OT.
Let me ask a few clarifying questions first."*

---

## STEP 1 — Requirements Gathering

```
YOU ASK:                                    INTERVIEWER SAYS:
────────────────────────────────────────────────────────────────────
"Multiple users edit simultaneously?"      → "Yes — real-time collab"
"See other users' cursors?"                → "Yes — color per user"
"Document versioning + rollback?"          → "Yes"
"Rich text (bold, tables) or plain text?"  → "Start with plain text"
"Offline editing?"                         → "Nice to have (CRDT handles)"
"How many users / docs?"                   → "500M users, 10B documents"
"How many concurrent editors per doc?"     → "Up to 100"
────────────────────────────────────────────────────────────────────
```

```
┌──────────────────────────────────────────────────────────────────┐
│                  REQUIREMENTS SUMMARY                             │
├──────────────────────────────────────────────────────────────────┤
│  FUNCTIONAL:                                                      │
│  Create / edit / delete documents                                │
│  Real-time collaborative editing (multiple users simultaneously) │
│  See each other's cursors (color-coded)                          │
│  Document version history + rollback                             │
│  Auto-save (no data loss)                                        │
│  Share with view/comment/edit permissions                        │
├──────────────────────────────────────────────────────────────────┤
│  NON-FUNCTIONAL:                                                  │
│  Scale:     500M users, 10B documents, 5M active at peak         │
│  Latency:   < 100ms edit propagation between collaborators       │
│  Availability: High (auto-recovery from server failures)         │
│  Consistency: Strong within active editing session               │
│  Durability: Zero data loss — every keystroke persisted          │
└──────────────────────────────────────────────────────────────────┘
```

*"The design-defining number I want to derive next is edit events per second —
because that single number tells you why REST is impossible."*

---

## STEP 2 — Capacity Estimation

```
EDIT EVENTS:
──────────────────────────────────────────────────────────────────
"5M active docs × ~5 keystrokes/sec per active editor = 25M events/sec.
 This is the design-defining number.
 REST overhead: ~50ms per call. 25M × 50ms = impossible.
 WebSocket overhead: ~1ms per call. 25M × 1ms = manageable.
 This number forces WebSocket."

WEBSOCKET CONNECTIONS:
──────────────────────────────────────────────────────────────────
"100M DAU × 30% active at peak = 30M concurrent WebSocket connections.
 At 100K connections/server → 300 WebSocket servers needed."

STORAGE:
──────────────────────────────────────────────────────────────────
"Document content: 10B docs × 50KB avg = 500 TB. Must use S3.
 Version snapshots: 10 versions × 50KB × 10B docs = 5 PB in S3.
 Ops log: transient (deleted after reconciliation). ~20-50ms of ops
 kept in Cassandra at any time."
```

---

## STEP 3 — Core Entities

```
┌──────────────────────────────────────────────────────────────────┐
│                       CORE ENTITIES                               │
├──────────────────┬───────────────────────────────────────────────┤
│ User             │ userId, name, profilePicUrl                    │
│ Document         │ docId, title, ownerId, currentVersion, blobUrl│
│ Operation        │ opId (Snowflake), docId, userId, type,        │
│                  │ position, char/length, clientVersion          │
│ Version          │ versionId, docId, versionNumber, blobUrl,     │
│                  │ isMajor, createdAt                             │
│ Permission       │ docId, userId, role (VIEWER/COMMENTER/EDITOR) │
└──────────────────┴───────────────────────────────────────────────┘

OPERATION TYPES:
  INSERT: { type: INSERT, pos: 5, char: "H" }
  DELETE: { type: DELETE, pos: 5, length: 2 }
  The position field is the key — this is what OT adjusts.

KEY INSIGHT about Operation:
"It also has a 'clientVersion' field — the document version number
 the client had when they made this change. The server uses this to
 know which concurrent operations to transform against."
```

---

> **► DRAW THIS on the whiteboard ◄**

## ER RELATIONSHIP DIAGRAM

```
┌────────────────────────────────────────────────────────────────────┐
│               GOOGLE DOCS — ENTITY RELATIONSHIP                     │
└────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────────────────────────┐
│    users     │     │           documents               │
│   (MySQL)    │     │            (MySQL)                │
├──────────────┤     ├──────────────────────────────────┤
│ PK user_id   │─────│ PK doc_id UUID                  │
│    email TEXT│ 1 N │ FK owner_id UUID → users        │
│    created_at│     │    title VARCHAR                │
└──────────────┘     │    current_version_id BIGINT    │
                     │    status ENUM(COLD,WARM,SAVING) │
                     │    created_at TIMESTAMP          │
                     │    updated_at TIMESTAMP          │
                     └──────────────┬───────────────────┘
                                    │ 1
                                    │ N
          ┌─────────────────────────┴────────────────────┐
          │                         │                     │
          │ N                       │ N                   │ N
┌─────────▼──────────┐   ┌─────────▼──────────┐   ┌─────▼────────────────┐
│  document_ops       │   │   doc_versions      │   │   doc_permissions    │
│  (Cassandra)        │   │   (Cassandra)       │   │    (MySQL)           │
├────────────────────┤   ├────────────────────┤   ├──────────────────────┤
│ PK doc_id (PART)   │   │ PK doc_id (PART)   │   │ PK doc_id UUID       │
│    op_id TIMEUUID  │   │    version BIGINT  │   │ PK user_id UUID      │
│ FK user_id UUID    │   │    s3_key TEXT     │   │    role ENUM         │
│    op_type ENUM    │   │    created_at TS   │   │  (VIEW,EDIT,COMMENT) │
│    position INT    │   │    op_count INT    │   │    granted_at TS     │
│    content TEXT    │   │    is_major BOOL   │   └──────────────────────┘
│    version BIGINT  │   └────────────────────┘
│    applied_at TS   │
└────────────────────┘

Redis (Live Document State):
┌────────────────────────────────────────────────────────┐
│ doc:{docId}:content     STRING  full document text     │
│ doc:{docId}:version     INT     current version counter│
│ doc:{docId}:cursors     HASH    userId → {line,col}    │
│ doc:{docId}:active_users SET   userIds (TTL 30s)       │
└────────────────────────────────────────────────────────┘
```

---

## STEP 4 — API Design

### REST APIs (non-editing)

```
POST /api/v1/documents              → create document
GET  /api/v1/documents/{id}         → fetch latest version
GET  /api/v1/documents/{id}/versions → list all versions
GET  /api/v1/documents/{id}/versions/{vId} → fetch specific version
POST /api/v1/documents/{id}/share   → { userId, role }
DELETE /api/v1/documents/{id}       → soft delete
```

### WebSocket Events (all editing goes here)

```
CONNECT:
  ws://editor/{docId}?userId={uid}
  On connect: server sends current canonical copy + version number
  Client renders document, ready to edit.

CLIENT → SERVER:
┌──────────────────┬────────────────────────────────────────────────┐
│ OPERATION        │ { type: INSERT/DELETE, pos, char, clientVer }  │
├──────────────────┼────────────────────────────────────────────────┤
│ CURSOR_MOVE      │ { pos, color }                                 │
└──────────────────┴────────────────────────────────────────────────┘

SERVER → CLIENT:
┌──────────────────┬────────────────────────────────────────────────┐
│ OP_ACK           │ { opId, serverVersion } — your op was applied  │
├──────────────────┼────────────────────────────────────────────────┤
│ OP_BROADCAST     │ { opId, userId, type, pos, char, serverVer }   │
│                  │ TRANSFORMED op from another user               │
├──────────────────┼────────────────────────────────────────────────┤
│ CURSOR_UPDATE    │ { userId, pos, color }                         │
└──────────────────┴────────────────────────────────────────────────┘

WHY WEBSOCKET for editing:
  REST: one HTTP round trip per keystroke = 50ms overhead × 25M/sec.
  WebSocket: persistent connection, ~1ms per event. 50× less overhead.
  Server can also PUSH transformed ops from other users to you —
  REST cannot do server-initiated push without long-polling hacks.
```

---

### JSON / WebSocket Message Examples

```json
// Client → Server: OPERATION event
{
  "type": "OPERATION",
  "docId": "doc_xyz789",
  "operation": {
    "type": "INSERT",
    "position": 0,
    "content": "A",
    "clientVersion": 42
  },
  "userId": "user_alice",
  "sessionId": "sess_abc"
}

// Server → Client: OP_ACK
{
  "type": "OP_ACK",
  "operationId": "op_7234891",
  "serverVersion": 44,
  "transformedPosition": 0
}

// Server → ALL clients: OP_BROADCAST
{
  "type": "OP_BROADCAST",
  "sourceUserId": "user_alice",
  "operation": {
    "type": "INSERT",
    "position": 0,
    "content": "A"
  },
  "serverVersion": 44
}

// Server → Client: CURSOR_UPDATE
{
  "type": "CURSOR_UPDATE",
  "userId": "user_alice",
  "cursor": { "line": 1, "col": 3 },
  "color": "#FF5733",
  "displayName": "Alice Smith"
}

// REST: POST /api/v1/documents
// Request:
{ "title": "Q1 Planning Doc" }
// Response 201 Created:
{ "docId": "doc_xyz789", "title": "Q1 Planning Doc", "ownerId": "user_alice", "createdAt": "2025-01-21T09:00:00Z" }

// REST: POST /api/v1/documents/{id}/share
// Request:
{ "userId": "user_bob", "role": "EDITOR" }
// Response 200 OK:
{ "docId": "doc_xyz789", "sharedWith": "user_bob", "role": "EDITOR" }
```

---

## STEP 5 — High-Level Architecture (Draw on Whiteboard)

> **► DRAW THIS on the whiteboard ◄**
> Draw left column: Client box showing OT Engine + WebSocket.
> Draw center: WS Gateway (label: consistent hash on docId → sticky).
> Draw center-right: Document Editor Service + OT Engine.
> Draw right column: Redis (canonical) → Kafka → Cassandra → S3.

```
                ╔══════════════════════════════════════════════╗
                ║       GOOGLE DOCS ARCHITECTURE                ║
                ╚══════════════════════════════════════════════╝

┌───────────────────────────────────────────────────────────────┐
│  CLIENTS (Browser / Desktop)                                   │
│  ┌──────────────────────────┐  ┌────────────────────────────┐ │
│  │ OT Engine (client-side)  │  │  Local Op Queue            │ │
│  │ Apply own op immediately │  │  Unacked ops buffered here │ │
│  │ (low latency UX)         │  │  Retransmit on reconnect   │ │
│  └──────────────────────────┘  └────────────────────────────┘ │
└──────────────────────────────────┬────────────────────────────┘
                                   │ WebSocket
                                   ▼
               ┌────────────────────────────────────────┐
               │  WEBSOCKET GATEWAY (Layer 4 NLB)        │
               │                                        │
               │  Consistent hash on documentId:        │
               │  All users of doc-123 → WS Server 3   │
               │  All users of doc-456 → WS Server 7   │
               │                                        │
               │  CRITICAL: OT requires all ops for     │
               │  one doc go through ONE server!         │
               └──────────────────┬─────────────────────┘
                                  │
                    (hash doc-123 → WS Server 3)
                                  │
               ┌──────────────────▼─────────────────────┐
               │   DOCUMENT EDITOR SERVICE               │
               │                                        │
               │   OT Engine:                           │
               │   1. Read version V from Redis          │
               │   2. If op.clientVersion < V:           │
               │      Transform op against ops v+1..V   │
               │   3. Apply to canonical:{doc-123}       │
               │   4. Increment version:{doc-123}        │
               │   5. Broadcast transformed op           │
               │   6. Publish to Kafka (durability)      │
               └───────────────┬────────────────────────┘
                               │
         ┌─────────────────────┼──────────────────────┐
         ▼                     ▼                       ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Redis           │  │    Kafka         │  │  Auto-Save       │
│                  │  │  topic: doc-ops  │  │  Scheduler       │
│  canonical:{d}   │  │  key: docId      │  │  (every 10-20s)  │
│  version:{d}     │  │  (ordered by     │  │  Read Redis →    │
│  cursor:{d}:{u}  │  │   docId ensures  │  │  snapshot to S3  │
│  activeUsers:{d} │  │   same partition)│  └────────┬─────────┘
└──────────────────┘  └─────────┬────────┘           │
                                │                     │ S3 PUT
                                ▼                     ▼
                    ┌──────────────────┐   ┌──────────────────┐
                    │  Op Consumer     │   │   S3 Blob        │
                    │  Service         │   │   doc-123/v10.1  │
                    │                  │   │   doc-123/v10.2  │
                    │  Writes ops to   │   │   doc-123/v11    │
                    │  Cassandra       │   │   (major)        │
                    └──────────┬───────┘   └──────────────────┘
                               │
                               ▼
                    ┌──────────────────────────┐
                    │   Cassandra               │
                    │   ops table:              │
                    │   partition: docId        │
                    │   cluster: op timestamp   │
                    │                          │
                    │   metadata table:         │
                    │   docs, versions, perms   │
                    └──────────────────────────┘
```

---

> **► DRAW THIS on the whiteboard ◄**

## SEQUENCE DIAGRAM — CONCURRENT EDIT WITH OPERATIONAL TRANSFORMATION

```
  Alice Browser   WS Server (sticky: doc1→srv1)    Redis      Kafka     Cassandra
       │                  │                           │           │            │
       │ WS CONNECT       │                           │           │            │
       │ /docs/doc1       │                           │           │            │
       │─────────────────▶│                           │           │            │
       │                  │ GET doc:doc1:content      │           │            │
       │                  │───────────────────────────▶           │            │
       │◀─────────────────│ {content, version:42}     │           │            │
       │                  │                           │           │            │
  Bob Browser             │                           │           │            │
       │ WS CONNECT       │                           │           │            │
       │ /docs/doc1       │                           │           │            │
       │─────────────────▶│   (same server — sticky routing)      │            │
       │◀─────────────────│ {content, version:42}     │           │            │
       │                  │                           │           │            │
       │ Alice types "A"  │                           │           │            │
       │ INSERT pos=0     │                           │           │            │
       │─────────────────▶│                           │           │            │
       │                  │                           │           │            │
       │ Bob types "D"    │                           │           │            │
       │ INSERT pos=2     │                           │           │            │
       │─────────────────▶│                           │           │            │
       │                  │                           │           │            │
       │                  │ OT Engine: transform ops  │           │            │
       │                  │ Alice v42 INSERT@0 → apply│           │            │
       │                  │ Bob v42 INSERT@2 → transform → INSERT@3           │
       │                  │ (Alice's insert shifted Bob's position)            │
       │                  │                           │           │            │
       │                  │ INCR doc:doc1:version → 44            │            │
       │                  │───────────────────────────▶           │            │
       │                  │                           │           │            │
       │                  │ Publish ops to Kafka (durability before ACK)      │
       │                  │───────────────────────────────────────▶           │
       │                  │◀───────────────────────────────────────           │
       │                  │   [ACK]       │           │           │            │
       │                  │                           │           │            │
       │ OP_ACK {newVersion:44}           │           │           │            │
       │◀─────────────────│               │           │           │            │
       │                  │               │           │           │            │
       │                  │ OP_BROADCAST to Bob (transformed op)              │
       │◀─────────────────│───────────────────────────────────────────────────│
       │ [Alice and Bob   │               │           │           │            │
       │  both see "ABCD"]│               │           │           │            │
```

---

## STEP 6 — OT Deep Dive (The Core Algorithm)

> **► DRAW THIS on the whiteboard ◄**
> Draw initial state "BC". Draw two users with their ops.
> Show the 5-step OT process. Circle the KEY insight: positions shift.

```
STEP-BY-STEP OT EXAMPLE:

  Initial document: "BC"  (B at index 0, C at index 1)

  Alice: INSERT "A" at position 0  (based on clientVersion = 5)
  Bob:   INSERT "D" at position 2  (based on clientVersion = 5)

  ─────────────────────────────────────────────────────────────────
  STEP 1: Alice applies her op LOCALLY → her screen shows "ABC"
          Bob applies his op LOCALLY   → his screen shows "BCD"
  ─────────────────────────────────────────────────────────────────
  STEP 2: Both clients send ops to server.
          Server receives Alice's op first (race determines order).
          Server applies: INSERT A at 0 → canonical = "ABC", version = 6
  ─────────────────────────────────────────────────────────────────
  STEP 3: Server receives Bob's op: { INSERT D at pos 2, clientVer=5 }
          clientVersion 5 < server version 6 → concurrent op detected!
  ─────────────────────────────────────────────────────────────────
  STEP 4: OT TRANSFORM Bob's op against Alice's op:
          ┌──────────────────────────────────────────────────────┐
          │  Alice INSERT at pos 0 (earlier).                    │
          │  Bob INSERT at pos 2.                                │
          │  RULE: if op2 (Alice) INSERT at P, and op1 (Bob)    │
          │         pos > P → op1.pos += 1                       │
          │  Bob's pos 2 > Alice's pos 0 → Bob's pos becomes 3  │
          │  Transformed: { INSERT D at pos 3, ver=6 }           │
          └──────────────────────────────────────────────────────┘
  ─────────────────────────────────────────────────────────────────
  STEP 5: Apply transformed op: "ABC" + INSERT D at 3 = "ABCD" ✓
          version = 7
          Broadcast to all users:
            Alice receives: { INSERT D at pos 3 }  → "ABCD" ✓
            Bob receives:   { INSERT A at pos 0 }  → "ABCD" ✓

  RESULT: Both users converge to "ABCD". Neither edit was lost.

OT TRANSFORM RULES (memorize these):

  Transforming op1 AGAINST op2 (op2 already applied):

  ┌──────────────────────────────────────────────────────────────┐
  │  op2 = INSERT at position P:                                 │
  │    op1 = INSERT: pos > P → pos++; pos < P → unchanged        │
  │                  pos = P → tie-break by userId (lower wins)  │
  │    op1 = DELETE: pos >= P → pos++; pos < P → unchanged       │
  ├──────────────────────────────────────────────────────────────┤
  │  op2 = DELETE at position P:                                 │
  │    op1 = INSERT: pos > P → pos--; pos <= P → unchanged       │
  │    op1 = DELETE: pos > P → pos--; pos = P → NOOP (gone)     │
  │                  pos < P → unchanged                         │
  └──────────────────────────────────────────────────────────────┘

  NOOP = the character op1 was going to delete was already deleted
         by op2. The delete op1 becomes a no-op.
```

---

## STEP 7 — CRDT (Alternative Algorithm — Know Both)

```
CRDT CORE INSIGHT:
  OT's problem: integer positions shift when insertions happen.
  CRDT solution: don't use integer positions — use FRACTIONAL IDs.

  Between any two fractions, there's always room for another:
  0.25 and 0.5 → insert at 0.375. Never conflicts.

CRDT EXAMPLE:
  Initial: "BC"  → B=0.50, C=0.75

  Alice INSERT "A" before B → assigns position 0.25
  Bob INSERT "D" after C → assigns position 0.875

  Merge: sort all characters by their fractional position:
    A=0.25, B=0.50, C=0.75, D=0.875 → "ABCD" ✓

  No transformation needed! The positions themselves don't conflict.

OT vs CRDT — KNOW THESE TRADE-OFFS:
┌──────────────────┬───────────────────────┬──────────────────────────┐
│  Dimension       │  OT                   │  CRDT                    │
├──────────────────┼───────────────────────┼──────────────────────────┤
│  Core idea       │  Transform positions  │  Fractional position IDs │
│  Single server?  │  YES (sticky routing) │  NO (peer-to-peer OK)    │
│  Offline edit    │  Poor (many transforms│  Excellent (just merge)  │
│  Storage/char    │  Low (just chars)     │  Higher (pos ID per char) │
│  Used by         │  Google Docs          │  Figma, Notion, Atom     │
│  Multi-region    │  Hard (needs primary) │  Natural (commutative)   │
└──────────────────┴───────────────────────┴──────────────────────────┘

"For this interview I'll implement OT (Google's approach).
 I'd mention CRDT as the right choice IF we needed offline editing
 or true multi-region active-active. OT is simpler to reason about
 when you have a single primary server per document."
```

---

## STEP 8 — Document Lifecycle + Auto-Save + Reconciliation

```
DOCUMENT LIFECYCLE:

  COLD state (nobody editing):
    doc lives only in S3 (major version v10)
    no Redis key exists

  User opens doc → WARM state:
    canonical:{doc-123} loaded from S3 into Redis
    version:{doc-123} = 10
    activeUsers:{doc-123} = { alice }

  Editing happens → minor auto-saves every 10-20s:
    Read canonical from Redis → PUT to S3 as v10.1, v10.2, ...
    Update minor version rows in Cassandra
    → SAVING state briefly, then back to WARM

  Last user disconnects → CLOSING state:
    Reconciliation Job triggers:
    ┌──────────────────────────────────────────────────────────┐
    │  1. Fetch base version v10 from S3                       │
    │  2. Fetch ALL ops AFTER v10 from Cassandra               │
    │     (everything logged since session started)            │
    │  3. Replay all ops on v10 → final document state         │
    │  4. PUT to S3 as v11 (MAJOR version)                     │
    │  5. Update Cassandra: currentVersion = 11                │
    │  6. DELETE v10.1 through v10.50 from S3 (minor versions) │
    │  7. DELETE all session ops from Cassandra                │
    │  8. DELETE canonical:{doc-123} from Redis                │
    └──────────────────────────────────────────────────────────┘
    → back to COLD state

  WHY KEEP MINOR VERSIONS DURING SESSION?
    If WS server crashes → new server loads canonical from Redis.
    If Redis ALSO fails → load last minor version from S3 + replay
    remaining ops from Cassandra. Zero data loss.

  WHY DELETE MINOR VERSIONS AFTER SESSION?
    50 minor versions × 50 KB = 2.5 MB per doc per session.
    1M sessions/day = 2.5 TB/day of wasted minor version storage.
    Major version is the clean source of truth. Minors are scaffolding.
```

---

## STEP 9 — Scalability

```
BOTTLENECK 1: STICKY ROUTING CREATES HOT SERVERS
─────────────────────────────────────────────────────────────────
A very popular document (100 concurrent editors) concentrates
all load on one WS server. That server handles:
  100 users × 5 ops/sec = 500 ops/sec → moderate, manageable.
  But OT transforms: each new op transforms against recent ops.
  At 500 ops/sec: transform queue may grow if server is slow.

Mitigation:
  Prioritize this document server (more CPU/memory).
  Limit max concurrent editors per doc to 100 (Google Docs' actual limit).
  For very large collaborative sessions: consider region-based OT
  sharding (Google's "Jupiter protocol" — each region has an OT server,
  regions sync every 100ms). Accept 100ms cross-region lag.

BOTTLENECK 2: REDIS MEMORY (5M canonical copies simultaneously)
─────────────────────────────────────────────────────────────────
5M active docs × 50 KB avg = 250 GB of canonical copies.
Redis cluster: shard by docId (e.g. 100 Redis shards × 2.5 GB each).
TTL: canonical key expires 30 minutes after last edit.
Inactive docs don't stay in Redis. Total in-memory footprint manageable.

BOTTLENECK 3: CASSANDRA OPS LOG WRITE RATE
─────────────────────────────────────────────────────────────────
25M ops/sec to Cassandra via Kafka.
Kafka buffers: WS server publishes, consumer writes at controlled pace.
Cassandra partition key = docId. Each doc writes to its own partition.
5M active docs × 5 ops/sec = 5M partitions writing in parallel.
Cassandra handles this well — no hot partition (writes spread by docId).

BOTTLENECK 4: RECONCILIATION JOB FAILURES
─────────────────────────────────────────────────────────────────
Reconciliation job is idempotent:
  Check: does major version for this session exist?
  YES → already done, skip.
  NO → run.
Retry with exponential backoff (10s, 30s, 2m, 10m).
DLQ after 5 failures → on-call alert.
S3 lifecycle policy: minor versions auto-expire after 30 days.
Even if reconciliation never runs, storage self-heals.
```

---

## WHAT NOT TO SAY ✗

```
✗ "I'll use REST APIs for real-time editing"
  → 25M edit events/sec × 50ms REST overhead = impossible.
    WebSocket with ~1ms overhead is the only option.

✗ "I'll use database locking so only one user edits at a time"
  → Pessimistic locking destroys the collaborative editing feature.
    Users would block each other constantly. This is pre-Google Docs UX.

✗ "I'll just save the whole document on every keystroke"
  → 25M keystrokes/sec × 50KB doc = 1.25 PB/sec network traffic.
    Delta ops (~50 bytes each) is 1000× more efficient.

✗ "I'll route edit ops to any available server"
  → OT requires total ordering. All ops for a document MUST go
    through the same server (sticky routing via consistent hash on docId).
    Random routing → different op orders → documents diverge.

✗ "No need to clean up ops log after editing session ends"
  → Ops log grows unbounded. A 1-hour session at 5 ops/sec = 18,000 ops
    per doc. 1M sessions/day = 18 billion op rows forever in Cassandra.
    Reconciliation job deletes them after creating the major version.

✗ "Redis is the primary storage for the document"
  → Redis is volatile. It's a materialized view, not source of truth.
    Source of truth = S3 (snapshots) + Cassandra (ops log).
    Redis can always be rebuilt from those two.
```

---

## SENIOR TRAP QUESTIONS (15 YOE Level)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 1 — FAILURE MODES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "The WS server holding doc-123 crashes. 50 users lose connection.
   In-flight ops (sent but not yet ACKed) are lost from memory.
   How do you recover without data loss?"

A: Three safety layers protect against this.
   1. Kafka durability: Op is published to Kafka BEFORE ACK is sent
      to the client. If WS server crashes after publishing but before
      ACKing, the op is in Kafka. Kafka consumer writes it to Cassandra.
      A new WS server rehydrates from Redis canonical + Cassandra ops.
   2. Client-side op queue: Every client maintains a queue of unACKed
      ops. On reconnect, client sends: { reconnect, docId, lastSeenVer }.
      Server sends back all ops since that version. Client transforms
      queued ops against them, resubmits.
   3. Redis canonical copy: Redis is a SEPARATE cluster from WS servers.
      It survives WS server crashes. New server loads canonical from Redis.
   Net result: no data loss. Users see "Reconnecting..." for <1 second.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "The Redis node holding canonical:{doc-123} fails. Last auto-save
   was 15 seconds ago. How do you recover the last 15 seconds of work?"

A: Event sourcing saves us. We never lose data because:
   Every applied op is in the Cassandra ops log (via Kafka consumer).
   The Kafka consumer acknowledges BEFORE the WS server ACKs the client.
   So every client-acknowledged op is durable in Cassandra.
   Recovery:
   1. Redis GET canonical:{doc-123} = nil → cache miss
   2. Fetch last MAJOR version from S3 (say v10 from 2 minutes ago)
   3. Fetch ALL ops after v10 from Cassandra (including last 15 seconds)
   4. Replay ops on v10 → reconstruct canonical copy
   5. Load into Redis, resume editing
   Total recovery time: ~170ms (S3 fetch + Cassandra read + replay).
   Users see a brief "Reconnecting..." flash. Zero data lost.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 2 — OT CORRECTNESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "Alice and Bob both DELETE the same character at position 5
   simultaneously. What does OT do?"

A: This is the DELETE-DELETE conflict — handled by the NOOP rule.
   Initial doc: "ABCDEFGH" — both users select and delete char at pos 5 ('F').
   Alice: { DELETE, pos=5 }  Server version: 10
   Bob:   { DELETE, pos=5 }  Server version: 10
   Server receives Alice first → DELETE 'F' → "ABCDEGH", version=11.
   Bob's op arrives: { DELETE pos=5, clientVer=10 }
   OT transform: op2 was DELETE at pos 5. op1 (Bob) is DELETE at pos=5.
   Rule: pos = P → NOOP. (The character is already gone.)
   Bob's op becomes NOOP. Applied: nothing changes. Version=12.
   Result: 'F' deleted once. Both users see "ABCDEGH". Correct.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "Can you run OT with active-active multi-region setup
   (US-East and EU-West both accept writes for the same document)?"

A: No — not with standard OT. This is the hardest trap.
   OT requires TOTAL ORDERING of operations.
   With two active regions:
     US-East receives ops in order: [A, B, C]
     EU-West receives ops in order: [A, C, B] (network reordering)
   Different op ordering → different OT transformation results
   → Documents in US and EU DIVERGE. Users see different text.
   What Google actually does (Jupiter protocol):
     Primary server per document (single region holds lock).
     All ops route to that primary. Other regions are read replicas.
     Users near the primary get 10-30ms latency.
     Users far away accept 50-150ms latency. That's the trade-off.
   True multi-region active-active for collaborative editing?
   → Switch to CRDT. CRDT merges commutatively — order doesn't matter.
   OT: centralized, simple. CRDT: distributed, more storage. Pick one.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 3 — SCALE + STORAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "A malicious user sends 10,000 ops/second to the server.
   How do you defend without impacting legitimate users?"

A: Defense in layers:
   Layer 1: API Gateway rate limit.
     Max 100 ops/sec per (userId, docId) pair.
     Token bucket: allows short bursts, prevents sustained abuse.
     Exceeded → 429 response, client backs off exponentially.
   Layer 2: WS server circuit breaker per connection.
     If user sends > 200 ops/sec → close WebSocket connection.
     Flag userId for review.
   Layer 3: Client-side batching (cooperative throttle).
     Legitimate clients batch keystrokes: "HELLO" typed in 200ms
     = 1 batch op { INSERT "HELLO" at pos X }, not 5 single-char ops.
     Reduces actual op volume 5× for normal users.
   Layer 4: Op size limit (max 10 KB per op).
     Prevents giant INSERT attacks ("insert 1 MB string").
   Result: OT engine for legitimate users is unaffected.
   The malicious user is rate-limited, disconnected, and flagged.
```

---

## KEY NUMBERS — Memorize These

```
┌──────────────────────────────────┬──────────────────────────┐
│              METRIC              │  VALUE                   │
├──────────────────────────────────┼──────────────────────────┤
│ Registered users                 │ 500 million              │
│ Daily Active Users               │ 100 million              │
│ Total documents                  │ 10 billion               │
│ Simultaneously active docs       │ ~5 million               │
│ Edit events per second           │ 25 million               │
│ Max concurrent editors per doc   │ 100                      │
│ WS connections at peak           │ 30 million               │
│ WS servers needed                │ ~300                     │
│ Document avg size                │ 50 KB                    │
│ Total document storage (S3)      │ 500 TB (content)         │
│ Total version storage (S3)       │ ~5 PB                    │
│ Auto-save interval               │ every 10-20 seconds      │
│ Edit propagation latency target  │ < 100ms                  │
│ Cursor position TTL (Redis)      │ 30 seconds               │
│ Canonical copy TTL (Redis)       │ 30 min post last edit    │
│ Google Docs character limit      │ ~1 million chars (~1 MB) │
└──────────────────────────────────┴──────────────────────────┘
```

---

*Study order: STEP 6 OT Algorithm (20 min) → STEP 5 Architecture (15 min)
→ STEP 8 Lifecycle/Reconciliation (10 min) → STEP 7 CRDT comparison (5 min)
→ Rapid Answer (5 min)*
