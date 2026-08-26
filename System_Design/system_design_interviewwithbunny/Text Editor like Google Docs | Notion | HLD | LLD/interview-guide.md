# System Design Interview Guide: Real-Time Collaborative Text Editor (Google Docs)

> **One-liner to open with**: "WebSocket session → Operations (insert/delete) → OT/CRDT → Op-log persistence → Periodic snapshots → Eventual convergence"

---

## Step 1: Clarify Requirements (2-3 min)

### Functional Requirements
| Feature | Detail |
|---|---|
| Create / update / delete documents | Rich text formatting |
| Real-time concurrent editing | Multiple users, same document, simultaneously |
| Cursor presence | See each other's cursors and selections live |
| Document sharing | View / Edit / Comment permissions |
| Version history | Rollback to any previous version |
| Offline editing | Queue ops locally, auto-sync on reconnect |
| Auto-save | Periodic snapshots to prevent data loss |

### Non-Functional Requirements
| Dimension | Target |
|---|---|
| Scale | Millions of users, millions of documents |
| Concurrent editors | 50–100 per hot document |
| Document size | Up to 1.02M characters |
| Latency | < 300ms for operations to propagate |
| Consistency model | Availability + Eventual consistency (CAP: AP with convergence guarantee) |
| Convergence guarantee | Strong eventual consistency — all clients with same ops → same state |

---

## Step 2: Core Entities

```
Document   → doc_id, owner_id, title, metadata, permissions, latest_snapshot_version
Operation  → op_id, doc_id, user_id, type(insert/delete/format), position, content,
             client_version, server_version, timestamp
Snapshot   → snapshot_id, doc_id, version, blob_path (S3), operations_since_last, created_at
Cursor     → EPHEMERAL (not persisted): user_id, cursor_pos, selection_range, color
```

> **Key insight**: Cursor is ephemeral — never persist in DB, only Redis TTL=5 min.

---

## Step 3: API Design

### REST — Document Management
```
POST   /v1/api/docs/create                      → creates doc, returns doc_id
GET    /v1/api/docs/{docId}                     → fetch latest snapshot (read-only)
GET    /v1/api/docs/{docId}/version             → list all versions
GET    /v1/api/docs/{docId}/version/{versionId} → open specific version (rollback)
POST   /v1/api/docs/{docId}/restore             → restore to target_version
```

### WebSocket — Real-Time Editing
```
WS  /v1/api/docs/{docId}/edit    → bidirectional stream
Client → Server: { type: 'operation', op: { type, position, content, client_version } }
Server → Client: { type: 'operation', op: { transformed_op } }   (broadcast to others)
                 { type: 'cursor_update', user, cursor_pos, selection }
                 { type: 'user_joined' / 'user_left' }
                 { type: 'sync_response', server_ops, current_version }
```

> **Why WebSocket over HTTP polling?** HTTP polling = 1M users × 1 req/sec = 1M req/sec. WebSocket = persistent connection, only sends on change = 100x less traffic.

---

## Step 4: High-Level Design (HLD)

```
Users/Clients
    │
    ├── REST ──▶ LB + API Gateway (auth, routing, rate limiting)
    │                │
    │                └──▶ Document Metadata Service ──▶ PostgreSQL (metadata, permissions)
    │
    └── WS ───▶ WebSocket LB + Gateway (sticky sessions, 10K conn/instance)
                    │
                    └──▶ Document Editor Service ──▶ Redis (canonical copy, TTL 30min)
                                │                └──▶ Op-log DB (append-only operations)
                                │                └──▶ S3 / Blob (snapshots, compressed)
                                └──▶ Kafka (doc.operations topic)
                                         │
                                         ├──▶ Reconciliation Service (snapshots + validation)
                                         ├──▶ Metadata Consumer (update metadata)
                                         └──▶ Operation Consumer Svc (analytics, audit)
                    CDN (static assets — editor UI, fonts, icons)
```

---

## Step 5: Low-Level Design (LLD) — Key Flows

### Flow 1: Document Open
```
1. GET /v1/api/docs/{doc_id}
2. Check permissions → 403 if not allowed
3. Fetch latest snapshot from S3 (docs/{doc_id}/v{N}.txt.gz)
4. Fetch ops since snapshot: SELECT * FROM operations WHERE server_version > N
5. Replay ops on snapshot → current state
6. Return { content, current_version, permissions }
```

### Flow 2: WebSocket Connect + Presence
```
1. Client opens WS /v1/api/docs/{doc_id}/edit
2. Gateway authenticates JWT, validates edit permission
3. Check Redis for doc:{doc_id}:state
   - HIT  → return cached state (1ms)
   - MISS → S3 snapshot + op replay, cache in Redis TTL=30min
4. Send to client: { type: 'init', content, current_version, active_users }
5. Broadcast to all: { type: 'user_joined', user: { id, name, color } }
```

### Flow 3: Edit Operation (Critical Path)
```
User A types insert(R, 29):

Client               WebSocket GW          Editor Service            DB / Kafka
  │──optimistic──────▶│                         │                       │
  │ show R locally    │──forward──────────────▶ │                       │
  │                   │                         │──assign server_ts──▶  │
  │                   │                         │──INSERT op_log ──────▶│
  │                   │                         │──publish to Kafka ────▶│
  │                   │◀──broadcast to B,C,D ───│                       │
  │                   │──OT transform if needed▶│                       │
  B,C,D apply op
```

### Flow 4: OT Conflict Resolution (The Core Problem)

**Scenario**: Document = 'abc', version 10
```
User A: insert('A', 0) → 'Aabc'   (server_version: 11)
User B: insert('D', 3) → 'abcD'   (arrives at server_version 10, but current is 11)

OT Transform:
  B's intended position 3 in 'abc'
  A inserted 1 char at position 0 (before position 3)
  → shift B's position: 3 + 1 = 4
  Transformed op: insert('D', 4)
  Applied to 'Aabc' → 'AabcD'

Both clients converge to 'AabcD' ✓
```

**Transform rules**:
- Insert before your position → shift right (+1)
- Delete before your position → shift left (-1)
- Same position → server order (timestamp / user_id tiebreak)

### Flow 5: CRDT Alternative

```
Each character gets unique ID: {site_id, sequence_number}
'abc' → 'a'={1,1}, 'b'={1,2}, 'c'={1,3}

User A (offline): insert 'X' after {1,1} → creates {1,10} with anchor 'after {1,1}'
User B (offline): delete {1,1}

Sync — operations commute (apply in any order):
  A then B: X goes to start of remaining chars → 'Xbc'
  B then A: delete 'a', then insert X after deleted anchor → 'Xbc'
  Both → same result ✓

No central server sequencing needed.
```

| | OT | CRDT |
|---|---|---|
| Central server | Required | Not required |
| Data structure | Simple string | Tree / linked list with IDs |
| Memory overhead | Low | High (IDs + tombstones) |
| Offline support | Hard | Native |
| Conflict resolution | Transform functions | Commutative by design |
| Used by | Google Docs, Notion | Figma, Automerge |

---

## Step 6: Cursor Presence

```
1. User moves cursor → client detects onChange
2. Throttle: batch every 100ms (90% traffic reduction)
3. Send: { type: 'cursor', user_id, cursor_pos: 15, selection: {start:10, end:15} }
4. Gateway broadcasts to all OTHER clients
5. Redis: HSET cursors:{doc_id} user:{user_id} '{cursor_pos, selection}' EX 300
6. On disconnect: HDEL cursors:{doc_id} user:{user_id}, broadcast user_left

Cursor transform with OT:
  User A cursor at pos 10, User B inserts 'hello' at pos 5
  → A's cursor: 10 + 5 = 15 (adjust for B's insert before cursor)
```

> **NEVER persist cursors in DB** — 100 updates/sec/user, ephemeral by nature.

---

## Step 7: Auto-Save & Snapshots

**Trigger**: Every 50 operations OR every 5 minutes (whichever first)

```
Reconciliation Service (Kafka consumer on doc.operations):
  1. Count ops since last snapshot for doc_id
  2. If count >= 50:
     a. Fetch last snapshot from S3 (docs/{doc_id}/v10.txt.gz)
     b. Fetch ops from op-log since that version
     c. Replay ops sequentially → current content
     d. Validate: checksum, positions, lengths
     e. gzip compress (70% size reduction)
     f. PUT S3 docs/{doc_id}/v11.txt.gz
     g. INSERT INTO snapshots (version:11, blob_path, ops_count:52)
     h. UPDATE documents SET latest_snapshot_version=11
     i. SET Redis doc:{doc_id}:state {content} EX 1800
     j. Publish Kafka: doc.snapshot_created
```

**Fast document load** (why snapshots matter):
- Without: replay 10,000 ops = ~5 seconds
- With snapshot + 5 ops replay = ~65ms ✓

---

## Step 8: Version History & Rollback

```
GET  /v1/api/docs/{docId}/version         → list snapshots DESC
GET  /v1/api/docs/{docId}/version/{id}    → read-only preview (fetch from S3)
POST /v1/api/docs/{docId}/restore         → { target_version: 10 }

Restore flow:
  1. Fetch S3 v10 content
  2. Create restore op: { type: 'replace_all', content: v10_content }
  3. Append to op-log
  4. Upload as NEW version (v12 = restored v10) — never mutate history
  5. Broadcast: { type: 'document_restored', by_user, from_version: 10 }
  6. All clients reload latest version
```

**Retention policy**:
- 0–30 days: hot storage, full restore
- 30–90 days: IA, view-only
- 90+ days: Glacier archive
- Named versions: never expire

---

## Step 9: Offline Editing & Sync

```
Offline:
  1. WebSocket closes (network failure)
  2. Client shows banner: "Working offline"
  3. Store ops locally: IndexedDB [{ op_id, type, position, content, client_version }]
  4. Store: last_known_version = 42

Reconnect:
  1. WS reconnects with exponential backoff (1s, 2s, 4s, 8s, max 30s)
  2. Send: { type: 'sync_request', last_known_version: 42 }
  3. Server: fetch ops 43–50 from op-log, send to client
  4. Client: apply server ops first (replay 43–50)
  5. Client: OT-transform local queued ops against server ops
  6. Send transformed ops to server as batch
  7. If conflict detected → modal: keep local / keep server / manual merge
```

---

## Step 10: Locking Protocol (from image — point 2)

**Optimistic (default — Google Docs)**:
- All users edit freely, no locks
- Conflicts resolved via OT/CRDT after the fact
- Best for collaborative documents

**Pessimistic (Banking / section-level)**:
- Lock a section before editing to prevent conflicts entirely
- Use case: financial documents, legal contracts, wiki sections

```
Lock acquire:
  POST /v1/api/docs/{docId}/lock  { section_id: 'para_5' }
  → SETNX lock:doc:{docId}:para_5 {user_A} EX 300
  → if success: { locked: true, expires_at }
  → if fail:    { locked: false, locked_by: user_B }

User edits paragraph → server validates lock still held → applies ops

Lock release:
  User finishes → DELETE lock:doc:{docId}:para_5
  Auto-release: TTL=300s if user disconnects (prevents deadlock)
  Broadcast: { type: 'lock_released', section_id: 'para_5' }
```

> Trade-off: Pessimistic eliminates conflicts but kills concurrent editing flexibility.

---

## Step 11: File Replacement (from image — point 1)

**Scenario**: User uploads a new document to replace existing content.

```
DataFlow (from image):
  1. User Uploads A Document (Read-Only Mode)
  2. Initiate WebSocket to Document Editor Service
  3. Frontend fetches the document snapshot from S3 (Blob Storage)
  4. Opening A document loads snapshot + replay operations from DB
  5. Download is shown locally

Replacement flow:
  POST /v1/api/docs/{docId}/replace  multipart/form-data (DOCX/TXT/PDF)

  Upload Service:
    1. Validate file format
    2. Extract text content (if DOCX/PDF)
    3. Create op: { type: 'replace_all', content: new_content, user_id, timestamp }

  Editor Service:
    1. INSERT INTO operations (type: 'replace_all', content, server_version)
    2. Create snapshot immediately: PUT S3 docs/{docId}/v{N}.txt.gz
    3. SET Redis doc:{docId}:state {new_content} EX 1800
    4. Broadcast: { type: 'document_replaced', message: 'Content replaced by User X' }
    5. All clients reload latest snapshot, discard local changes
```

---

## Step 12: Events Passing via WebSockets (from image — point 3)

All real-time updates flow exclusively through WebSocket connections.

**Complete event catalogue**:
```
Direction      Event Type          Payload
Client→Server  'operation'         { op: { type, position, content, client_version } }
Client→Server  'cursor'            { cursor_pos, selection: { start, end } }
Client→Server  'sync_request'      { last_known_version, queued_ops_count }
Server→Client  'operation'         { transformed_op, user_id }
Server→Client  'cursor_update'     { user_id, name, color, cursor_pos, selection }
Server→Client  'user_joined'       { user_id, name, color }
Server→Client  'user_left'         { user_id }
Server→Client  'lock'              { section_id, locked_by / released }
Server→Client  'sync_response'     { server_ops, current_version }
Server→Client  'notification'      { type: document_restored/replaced/shared, ... }
```

**Protocol details**:
- Format: JSON over WebSocket
- Compression: `permessage-deflate` extension (reduces bandwidth)
- Load balancing: sticky sessions (IP hash) — same user stays on same gateway instance
- Failover: if gateway instance dies → client auto-reconnects (exponential backoff) → sends sync_request to catch up missed ops

---

## Step 13: Reconciliation Service

**Purpose**: Validate consistency, generate snapshots, detect anomalies, rebuild state.

```
Real-time (Kafka consumer):
  - Validate each op: position <= doc_length, user has edit permission, server_version = prev+1
  - Trigger snapshot if op_count >= 50

Nightly full reconciliation (2 AM):
  - For all docs updated in last 7 days:
    fetch snapshot + replay all ops → compute checksum → compare with Redis
    if mismatch → generate new snapshot, log inconsistency

State rebuild (cache miss / corruption):
  - Fetch ALL ops from op-log ordered by server_version
  - Replay from empty string → generate snapshot → cache in Redis
```

---

## Database Schema

### PostgreSQL

**documents**
```sql
doc_id                uuid PRIMARY KEY
owner_id              uuid FK → Users
title                 varchar(255)
metadata              jsonb
permissions           jsonb   -- [{user_id, role: 'view'/'edit'/'comment'}]
latest_snapshot_version int
```

**operations** (append-only op-log)
```sql
op_id            uuid PRIMARY KEY
doc_id           uuid   INDEX
user_id          uuid
type             enum('insert','delete','format','replace_all')
position         int
content          text
client_version   int
server_version   int    -- server-assigned sequence (single source of truth)
timestamp        timestamp
INDEX (doc_id, server_version)  -- critical for range queries
```

**snapshots**
```sql
snapshot_id          uuid PRIMARY KEY
doc_id               uuid   INDEX
version              int
blob_path            varchar(500)  -- S3: docs/{doc_id}/v{N}.txt.gz
operations_since_last int
created_at           timestamp
created_by           uuid  -- or 'system'
```

### Redis Keys
```
doc:{docId}:state          STRING  content            EX 1800  (30 min)
cursors:{docId}            HASH    user_id → {pos,sel} EX 300  (5 min)
lock:doc:{docId}:{section} STRING  user_id            EX 300  (pessimistic)
session:{sessionId}        HASH    user_id, doc_id, color     EX 3600
```

### S3 Layout
```
docs/{doc_id}/v{N}.txt.gz          active snapshots
archive/{doc_id}/ops_{yr}_{mo}.gz  archived op-logs
Lifecycle: Standard → IA (30d) → Glacier (90d)
```

---

## Scaling Numbers

| Component | Capacity | At 1M Users |
|---|---|---|
| WebSocket Gateway | 10K conn/instance | 100 instances |
| Document Editor Service | — | 200 instances |
| Redis Cluster | — | 100 nodes |
| PostgreSQL | — | 100 shards (by doc_id hash) |
| Kafka | 1 GB/sec/broker | 20 brokers, 100 partitions |
| S3 Snapshots | — | 3,333 snapshots/sec |
| Network | — | ~60 Gbps total |

**Cursor update math**: 10 users × 10 updates/sec = 100 msg/sec → with 100ms throttle = 10 msg/sec (90% reduction)

---

## Key Optimizations

| Optimization | Impact |
|---|---|
| Redis canonical copy (TTL 30 min) | 90% reads skip S3/DB |
| Snapshot every 50 ops / 5 min | Max replay = 50 ops (~50ms) |
| gzip snapshot compression | 70% storage reduction |
| Cursor throttle 100ms | 90% WebSocket traffic reduction |
| Op batching (5 chars/sec threshold) | Reduces op-log size |
| CDN for static assets | Fast global editor load |
| Lazy load >100K char docs | Initial 10K chars, rest on scroll |
| Op-log archival >90 days | S3 Glacier, 10x cost reduction |

---

## Key Numbers to Remember

| Category | Metric | Value |
|---|---|---|
| Scale | Concurrent editors per hot doc | 50–100 |
| Scale | Document size limit | 1.02M characters |
| Scale | WebSocket connections per gateway | 10K |
| Scale | Update latency target | < 300ms |
| Caching | Redis doc state TTL | 30 minutes |
| Caching | Redis cursor TTL | 5 minutes (ephemeral) |
| Caching | Redis cache hit rate | 90% of reads |
| Snapshots | Trigger: operation count | Every 50 ops |
| Snapshots | Trigger: time-based | Every 5 minutes |
| Snapshots | gzip compression gain | 70% size reduction |
| Ops | Cursor update throttle | 100ms batching |
| Ops | Traffic reduction from throttling | 90% |
| Ops | 10K ops replay time | ~5 seconds |
| Ops | Snapshot + 5 ops load time | ~65ms |
| Scaling | 1M users → WS Gateway instances | 100 |
| Scaling | 1M users → Editor Service instances | 200 |
| Scaling | 1M users → Redis nodes | 100 |
| Scaling | Kafka brokers | 20, 100 partitions |
| Scaling | S3 snapshots/sec at 1M users | 3,333/sec |
| Scaling | Total network bandwidth | ~60 Gbps |
| Cost | Estimated at 1M concurrent users | ~$500K/month |

---

## Critical Interview Tips

> **⚠️ CRITICAL** — Operations MUST be sequenced by the central server in OT. Without server-assigned order, clients apply ops in different sequences → divergent states. `server_version` is the single source of truth.

> **⭐ ALWAYS ASKED** — "OT vs CRDT difference?" → OT: central server, transforms concurrent ops, simpler data structure. CRDT: operations commute in any order, no server needed, works offline, larger memory (IDs + tombstones).

> **⭐ ALWAYS ASKED** — "How does collaborative editing conflict get solved?" → Walk through: User A inserts, User B deletes concurrently → Server sequences (A first, v11) → B's op arrives at v10, transform position → both replay in server order → converge.

> **💡 MUST MENTION** — Redis as canonical copy with TTL=30 min serves 90% of reads. Evicted docs refetch from S3 snapshot + replay recent ops only.

> **⚠️ NEVER** persist cursor positions in DB. 100 updates/sec/user = 10K writes/sec for 100 editors, all ephemeral. Redis HASH with TTL=5 min, broadcast via WebSocket, removed on disconnect.

> **💡 SNAPSHOT STRATEGY** — Every 50 ops OR 5 min balances storage vs replay time. Worst-case: 50 ops replay (~50ms). Without snapshots: 10K ops = 5 seconds.

> **⚠️ NEVER skip op-log validation** — Always check: (1) position ≤ doc_length, (2) user has edit permission, (3) server_version increments by 1. Invalid ops → skip + log + flag for review.

> **⭐ MUST EXPLAIN** — WebSocket vs HTTP polling: polling = 1M req/sec overhead, WebSocket = send only when data changes = 100x less traffic.

> **💡 OFFLINE SYNC** — Store ops in IndexedDB with last_known_version. On reconnect: fetch server ops since last_known_version → OT-transform local ops → send batch. Ensures eventual consistency.

---

## Common Interview Questions & Answers

### Q1: How does OT resolve concurrent edits?
Server assigns sequential version numbers. When User B's op arrives but server advanced since B's client_version, OT transforms B's position: insert-before-you → shift right, delete-before-you → shift left. Server order = single source of truth. All clients apply in that order → convergence guaranteed.

### Q2: OT vs CRDT?
OT: central server sequences ops, simpler data structure, complex transform functions, single point of failure.
CRDT: operations commute (any order), each char has unique ID, no central server, works offline natively, but memory overhead (IDs + tombstones).
Google Docs = OT. Figma = CRDT. Hybrid = OT real-time + CRDT offline sync.

### Q3: How do you handle offline editing?
Store ops in IndexedDB with last_known_version. On reconnect: server sends ops since last_known_version → client applies them → OT-transforms local queued ops → sends batch to server. Conflict = show merge modal.

### Q4: Why not persist cursors in DB?
Cursor updates fire at 100 updates/sec/user. At 100 concurrent editors that's 10,000 writes/sec just for cursors — all ephemeral, never needed for recovery. Redis HASH with TTL=5 min is sufficient. Auto-expires on disconnect.

### Q5: How does snapshot strategy balance storage vs latency?
Every 50 ops OR 5 min. At 50-op snapshots, worst-case replay = 50 ops (~50ms). Without snapshots, replaying 10K ops = 5 seconds. gzip compression cuts storage 70%. Old ops archived to Glacier after 90 days.

### Q6: What does the Reconciliation Service do?
Kafka consumer that validates every op (position valid, permission, sequence), triggers snapshot generation at 50-op threshold, runs nightly full reconciliation to detect state drift, and rebuilds canonical state from op-log if cache/snapshot lost.

### Q7: How do you implement version history and rollback?
Every snapshot = one version. Fetch list: `SELECT version, created_at, created_by FROM snapshots WHERE doc_id ORDER BY version DESC`. View a version: fetch from S3, show read-only preview with diff vs current. Restore: fetch target content → create `replace_all` op → upload as **new** version (never mutate history) → broadcast `document_restored` to all editors → clients reload. Named versions (user-labeled milestones) never expire. Retention: 30d hot restore, 90d view-only, 1yr+ Glacier.

---

## Interview Anti-Patterns to Avoid

| Wrong | Right |
|---|---|
| "Save cursor to DB" | Redis HASH, TTL=5 min, ephemeral |
| "Use HTTP polling for real-time" | WebSocket persistent connections |
| "Clients order operations" | Server assigns order (server_version) — critical for OT |
| "Skip op validation" | Always check position, permission, sequence gap |
| "Load entire op-log on open" | Load latest snapshot + only recent ops |
| "CRDT needs a server" | CRDT is peer-to-peer by design, OT needs central server |

---

## Diagram Reference

```
From HLD diagram (image):
  LB+API Gateway → Document Metadata Svc → DB
  WebSocket LB+Gateway → Document Editor Svc → Redis (canonical, TTL)
                                             → Kafka → Reconciliation Svc (Replay) → S3
                                                    → Op Consumer → DB (op-log)
                       → S3 (snapshots)
  CDN (static assets)

From LLD diagram (image):
  OT: BC(v0,1) + BCD(v0,1,2) → server sequences → both converge to ABCD
  CRDT: A,B,C → A inserts → B deletes → operations commute → converge regardless of order
  DataFlow: User opens doc → WS → Editor Svc checks Redis → if miss: S3 + Kafka replay
            → client sends ops → Editor Svc: OT reconcile, update Redis, broadcast, Kafka
```
