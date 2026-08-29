Real-Time Collaborative Text Editor (Google Docs)

"WebSocket session → Operations (insert/delete) → OT (Operational Transformation) or CRDT → Op-log persistence → Periodic snapshots → Eventual convergence"

1. Functional Requirements

Feature 1: Users should be able to create/update/delete documents with rich text formatting
Feature 2: Multiple users can edit the same document simultaneously in real-time (concurrent editing)
Feature 3: Users should be able to view each other's changes in real-time with cursor positions and presence
Feature 4: Share documents with permissions (view only, edit, comment)
Feature 5: Version history and ability to rollback to previous versions
Feature 6: Offline editing with automatic sync when connection restored
Feature 7: Auto-save to prevent data loss (periodic snapshots)
2. Non-Functional Requirements

Scale
Users — Millions of users with millions of documents
Concurrent Editors — Hot docs: Up to 50-100 users editing same document simultaneously
Document Size — Support large documents (1.02M characters Google Docs limit)
Performance & Consistency
CAP Theorem — Availability & Consistency (formal Document) - eventual consistency acceptable with guaranteed convergence
Latency — Updates should be live (< 300ms) for real-time collaboration experience
Convergence — Goal: All clients must end up with the same document state (strong eventual consistency)
3. Core Entities (from image)

Entity 1: Document - doc_id, owner_id, title, metadata (created_at, updated_at, permissions)
Entity 2: Operation/Edit - op_id, doc_id, user_id, type (insert/delete), position, content, timestamp, client_version
Entity 3: Snapshot/Version - version_id, doc_id, snapshot_blob_path (S3), operations_count, timestamp
Entity 4: Cursor/Presence - Ephemeral data (user_id, cursor_position, selection_range, color) - not persisted in DB
4. API Designing (from image)

Document Management
POST /v1/api/docs/create — Create a document - Returns a document ID
GET /v1/api/docs/{docId} — View Document (ReadOnly) - Fetch latest snapshot
GET /v1/api/docs/{docId}/version — Get all the versions (version history)
GET /v1/api/docs/{docId}/version/{versionId} — Open a specific version (rollback capability)
Real-Time Editing (WebSocket)
WS /v1/api/docs/{docId}/edit — WebSocket connection for collaborative editing - bidirectional operation stream
Client → Server — Send operations (insert/delete/format) with optimistic local updates
Server → Client — Broadcast transformed operations to all connected clients for synchronization
5. High Level Design (from image)

Clients (users/clients) → LB/API Gateway: Load balancing and authentication & authorization & routing
WebSocket LB + Gateway: Maintains persistent WebSocket connections, handles 10K connections per instance
Document Metadata Service → DB: Stores document metadata (owner, permissions, title) - PostgreSQL
Document Editor Service: Core business logic, maintains canonical state in memory, processes operations
Blob Storage (S3): Stores document snapshots for fast recovery, organized as docs/{doc_id}/v{version}.txt
Redis (Canonical Copy): Short-lived cache of current document state for fast access across instances
Op-log (DB): Persistent storage of all operations (append-only), enables replay and versioning
Kafka: Event streaming for operations, decouples editor service from consumers
Reconciliation Service (from image): Rebuilds document from op-log, resolves conflicts, generates new snapshots
CDN: Serves static assets (editor UI, fonts, styles) for fast global access
6. Deep Dive Design (Low Level - from image)

Step 1: Document Creation & Loading
User creates: POST /v1/api/docs/create with {title: 'Meeting Notes', owner_id: user_A}
Document Metadata Service: INSERT INTO documents (doc_id, owner_id, title, created_at, updated_at, permissions) VALUES ({uuid}, {user_A}, 'Meeting Notes', now(), now(), '{}')
Create initial snapshot: Upload to S3 docs/{doc_id}/v0.txt with empty content, store reference: INSERT INTO snapshots (snapshot_id, doc_id, version, blob_path, operations_since_last: 0, created_at)
Response: {doc_id, edit_url: '/docs/{doc_id}/edit'}
User opens document: GET /v1/api/docs/{doc_id}
Check permissions: SELECT permissions FROM documents WHERE doc_id={doc_id}, if user not owner and not in shared_with[] → return 403 Forbidden
Fetch latest snapshot: SELECT blob_path, version FROM snapshots WHERE doc_id={doc_id} ORDER BY version DESC LIMIT 1
Download from S3: GET docs/{doc_id}/v0.txt → current content
Fetch operations since snapshot: SELECT * FROM operations WHERE doc_id={doc_id} AND timestamp > {snapshot_timestamp} ORDER BY timestamp ASC
Apply operations: Replay operations on snapshot to get current state (if any ops exist since last snapshot)
Return: {doc_id, content, current_version, permissions}
Step 2: WebSocket Connection & Presence
User clicks 'Edit': Client establishes WebSocket: WS /v1/api/docs/{doc_id}/edit with Authorization: Bearer {JWT}
WebSocket Gateway: (1) Authenticates token, (2) Validates user has 'edit' permission, (3) Creates session {session_id, user_id, doc_id, connected_at}
Load current state: (a) Check Redis: GET doc:{doc_id}:state, if hit return cached state (1ms), (b) If miss: fetch snapshot from S3 + replay recent operations from op-log, cache in Redis with TTL=30 min
Send initial state: Server → Client via WebSocket: {type: 'init', content: {current_document_text}, current_version: 42, active_users: [{user_id, name, cursor_pos, color}]}
Broadcast presence: Server → All connected clients: {type: 'user_joined', user: {user_id: A, name: 'Alice', color: '#FF5733'}}
Client displays: Active users list in top bar, colored cursor indicators for each user
Step 3: Real-Time Editing - Operation Flow (from image)
User A types: insert(R, 29) - inserts character 'R' at position 29
Client optimistic update: Immediately shows 'R' in local editor (no wait for server), queues operation for sending
Client sends operation: Via WebSocket → {type: 'operation', op: {op_id: uuid(), type: 'insert', position: 29, content: 'R', client_version: 42, user_id: A, timestamp: now()}}
WebSocket Gateway receives: Validates session active, forwards to Document Editor Service
Document Editor Service: (1) Assigns server timestamp and sequence number, (2) Appends to op-log: INSERT INTO operations (op_id, doc_id, user_id, type, position, content, client_version, server_version, timestamp), (3) Publishes to Kafka 'doc.operations' topic: {doc_id, op_id, type, position, content, user_id, server_version: 43}
OT/CRDT Transformation (if concurrent ops exist - explained in next step)
Gateway broadcasts: Transformed operation to all OTHER connected clients (User B, C, D) via WebSocket: {type: 'operation', op: {type: 'insert', position: 29, content: 'R', user_id: A}}
Clients B, C, D apply: Receive operation, apply to their local state at position 29, see 'R' appear in real-time
Step 4: Conflict Resolution - Operational Transformation (OT) [from image diagram]
Scenario: User A and User B both editing at same time, document version 10, content: 'abc'
User A types at position 0: insert('A', 0) → 'Aabc', sends to server
User B types at position 3: insert('D', 3) → 'abcD', sends to server
Server receives both: (1) A's operation arrives first (network timing), assigned server_version: 11, (2) B's operation arrives second, assigned server_version: 12
OT Service processes B's operation: (1) Checks: B's client_version=10, but server is now at version 11 (A's op applied), (2) Transformation needed: B intended position 3 in 'abc', but A inserted at 0 → doc now 'Aabc' (4 chars), (3) Transform B's position: original position 3 + 1 (A inserted before) = new position 4, (4) Transformed operation: insert('D', 4) applies to 'Aabc' → 'AabcD'
Broadcast: (1) Send A's op to B: insert('A', 0), (2) Send transformed B's op to A: insert('D', 4), (3) Both clients apply operations
Final state: Both clients converge to 'AabcD', order guaranteed by server sequencing
Key insight (from image): 'Switching happens only if keyframe is set at 0th second' - operations must be sequenced by server to ensure all clients see same order
Delete transformation example: User A: delete(2), User B: insert('X', 5), if A's delete executed first → B's position shifts: 5 → 4 (one char removed before position)
Step 5: Alternative - CRDT Approach (from image diagram)
CRDT (Conflict-Free Replicated Data Types): Operations designed to be commutative (can be applied in any order)
Character-based CRDT: Each character has unique ID (site_id + sequence_number): 'A' = {site: 1, seq: 1}, 'B' = {site: 1, seq: 2}
User A inserts: {site: 1, seq: 10, char: 'X', after: {site: 1, seq: 5}}, User B inserts: {site: 2, seq: 5, char: 'Y', after: {site: 1, seq: 5}}
Both operations can be applied in ANY order: (1) A then B: ...X...Y..., (2) B then A: ...Y...X..., (3) Conflict resolution: Deterministic ordering rule (e.g., site_id tiebreaker) ensures same final order
Advantages: (1) No central server sequencing required, (2) Works offline (operations stored locally), (3) Multi-master replication (multiple servers can accept writes)
Disadvantages: (1) More complex data structure (tombstones for deletes), (2) Larger metadata overhead (each char has unique ID), (3) Memory grows with edit history
Example (from image): ABC → BCD, (1) User A sees 'ABC', inserts at 0: 'AABC' (marked inconsistent), (2) User B sees 'ABC', deletes at 0: 'BC', (3) With OT: Server sequences, both converge to 'BC', (4) With CRDT: Operations commute, both converge to 'BC' (delete wins based on ID ordering)
Step 6: Cursor & Presence Updates (from image shows real-time updates)
User A moves cursor: Client detects cursor position change: {cursor_pos: 15, selection_start: 10, selection_end: 15}
Throttling: Batch cursor updates every 100ms (reduce WebSocket traffic), if no change in 100ms → skip
Client sends: Via WebSocket: {type: 'cursor', user_id: A, cursor_pos: 15, selection: {start: 10, end: 15}, timestamp}
Gateway broadcasts: To all OTHER clients (B, C, D): {type: 'cursor_update', user: {user_id: A, name: 'Alice', color: '#FF5733', cursor_pos: 15, selection: {start: 10, end: 15}}}
Clients render: (1) Colored cursor at position 15 with label 'Alice', (2) Selection highlight from 10-15 in Alice's color (semi-transparent), (3) Update active users list showing position
Ephemeral data: Cursor positions NOT persisted in DB (recreated on reconnect), stored in Redis with TTL=5 min: HSET cursors:{doc_id} user:{user_id} '{cursor_pos, selection, timestamp}' EX 300
User disconnects: Server removes cursor: DELETE cursors:{doc_id} user:{user_id}, broadcasts: {type: 'user_left', user_id: A} → other clients remove cursor indicator
Step 7: Auto-Save & Snapshot Creation (from image shows TTL and S3)
Trigger: Every 50 operations OR every 5 minutes (whichever comes first)
Background job checks: SELECT COUNT(*) FROM operations WHERE doc_id={doc_id} AND timestamp > {last_snapshot_timestamp}, if count >= 50 → trigger snapshot
Reconciliation Service (from image): (1) Fetch latest snapshot: GET S3 docs/{doc_id}/v{last_version}.txt, (2) Fetch operations since snapshot: SELECT * FROM operations WHERE doc_id={doc_id} AND server_version > {last_version} ORDER BY server_version ASC, (3) Replay operations: Apply each operation sequentially to reconstruct current state, (4) Generate new snapshot content
Upload to S3: PUT docs/{doc_id}/v{new_version}.txt with current content (50 operations applied)
Update database: INSERT INTO snapshots (snapshot_id, doc_id, version, blob_path, operations_since_last: 50, created_at: now()), UPDATE documents SET latest_snapshot_version={new_version}, updated_at=now()
Update Redis cache: SET doc:{doc_id}:state {current_content} EX 1800 (30 min TTL)
Publish event: Kafka 'doc.snapshot_created' → {doc_id, version, operations_count: 50} for analytics
Step 8: Version History & Rollback (from image shows version API)
User requests: GET /v1/api/docs/{doc_id}/version → fetch version history
Service queries: SELECT version, created_at, operations_since_last, created_by FROM snapshots WHERE doc_id={doc_id} ORDER BY version DESC LIMIT 20
Response: [{version: 5, created_at: '2026-01-22T10:30:00Z', operations: 50, label: 'Auto-save'}, {version: 4, ...}, ...]
User selects version: GET /v1/api/docs/{doc_id}/version/3 to rollback to version 3
Service fetches: (1) Snapshot: GET S3 docs/{doc_id}/v3.txt, (2) Display read-only preview to user
User confirms restore: POST /v1/api/docs/{doc_id}/restore with {target_version: 3}
Service creates new version: (1) Fetch v3 content, (2) Upload as new snapshot: PUT S3 docs/{doc_id}/v{new_version}.txt with v3 content, (3) INSERT new snapshot record, (4) Update doc latest_snapshot_version
Notify active editors: Via WebSocket: {type: 'document_restored', version: 3, restored_by: user_B, message: 'Document restored to version 3, refresh to see changes'}
Clients refresh: Fetch latest version, reload content, discard local unsaved changes
Step 9: Offline Editing & Sync (from image shows offline capability)
User goes offline: WebSocket connection closes (network failure), client detects via error/close event
Client switches to offline mode: (1) Display banner 'Working offline, changes will sync when online', (2) Store operations locally: IndexedDB or localStorage, (3) Continue editing (optimistic updates), (4) Queue all operations: [{op_id, type, position, content, timestamp, client_version}]
Local storage: SET offline_ops:{doc_id} [{op1, op2, op3, ...}], last_known_version: 42
User comes online: Network restored, WebSocket reconnects automatically (retry with exponential backoff)
Client sends sync request: Via WebSocket: {type: 'sync_request', doc_id, last_known_version: 42, queued_operations_count: 5}
Server responds: (1) Fetch operations from server since version 42: SELECT * FROM operations WHERE doc_id={doc_id} AND server_version > 42 ORDER BY server_version, (2) Send to client: {type: 'sync_response', server_operations: [{op1, op2, ...}], current_version: 50}
Client reconciliation: (1) Apply server operations using OT (transform local queued ops against server ops), (2) Send transformed local operations to server: {type: 'operations_batch', ops: [{transformed_op1, transformed_op2, ...}]}, (3) Server validates and applies if no conflicts
Conflict resolution: If conflicts detected → display modal 'Conflicts detected during sync, review changes', allow user to choose: keep local, keep server, or merge manually
Step 10: Locking Protocol (Pessimistic - Optional, from image)
Use case: Some applications require pessimistic locking (e.g., editing a specific section/paragraph at a time)
Optimistic (Git merge): Default for Google Docs - all users edit freely, conflicts resolved via OT/CRDT
Pessimistic (Banking): Lock sections before editing to prevent conflicts
Implementation: (1) User A selects paragraph: POST /v1/api/docs/{doc_id}/lock with {section_id: 'para_5'}, (2) Server acquires lock: SETNX lock:doc:{doc_id}:para_5 {user_A} EX 300 (5 min TTL), (3) If successful: return {locked: true, expires_at}, (4) If failed: return {locked: false, locked_by: user_B}, (5) User A edits paragraph → sends operations → Server validates lock still held → applies operations
Release lock: (1) User A finishes: DELETE lock:doc:{doc_id}:para_5, (2) Auto-release: TTL expires after 5 min if user disconnects, (3) Broadcast: {type: 'lock_released', section_id: 'para_5'} → other users can now request lock
From image note: 'Pessimistic (Banking)' - used when strong locking required, not typical for docs
Trade-off: Pessimistic reduces concurrent editing flexibility but eliminates conflicts entirely
Step 11: File Replacement (from image shows DataFlow)
Scenario: User uploads a new version of document (replaces existing content)
User clicks 'Replace file': Upload new document via POST /v1/api/docs/{doc_id}/replace with file in multipart/form-data
From image DataFlow: (1) User Uploads A Document (Read-Only Mode), (2) Initiate WebSocket to Document Editor Service, (3) Frontend fetches the document snapshot from S3 (Blob Storage), (4) Opening A document Loads snapshot + replay operations from DB, (5) Download is shown in local
Upload Service: (1) Validates file format (DOCX, TXT, PDF), (2) Extracts text content (if DOCX/PDF), (3) Creates new operation: {type: 'replace_all', content: {new_content}, user_id, timestamp}
Document Editor Service: (1) Append to op-log: INSERT INTO operations (op_id, doc_id, type: 'replace_all', content, user_id, timestamp), (2) Create new snapshot immediately: PUT S3 docs/{doc_id}/v{new_version}.txt with new content, (3) Update Redis: SET doc:{doc_id}:state {new_content} EX 1800
Notify active editors: Via WebSocket: {type: 'document_replaced', message: 'Document content replaced by User X, refresh to see new version'}
Clients reload: Fetch latest snapshot, discard local changes, display new content
Step 12: Reconciliation Service (from image shows Reconciliation Consumer)
Purpose: Ensures data consistency, rebuilds canonical state from op-log, generates snapshots
Kafka consumer: Subscribes to 'doc.operations' topic with consumer group 'reconciliation-service'
Processing: (1) Receives operation event: {doc_id, op_id, type, position, content, server_version}, (2) Checks if snapshot needed: if operations_since_last_snapshot >= 50 → trigger snapshot creation, (3) Rebuilds document: Fetch last snapshot + replay all operations → validate consistency
Conflict detection: If inconsistency found (e.g., operation position > document length) → alert, log error, skip operation
From image shows: Reconciliation Consumer → DB (for operation log) → S3 (generate snapshots) → Kafka (emit reconciliation events)
Periodic full reconciliation: Nightly job (2 AM) validates ALL documents: (1) Fetch snapshot + operations, (2) Replay to verify integrity, (3) Generate new snapshot if needed, (4) Report: {total_docs, snapshots_created, errors: []}
Error handling: If op-log corrupted → restore from last known good snapshot, mark operations as 'skipped', notify admin for manual review
Step 13: Events Passing via WebSockets (from image highlights this)
All real-time updates flow through WebSockets (from image shows 'Events passing via websockets connecter')
Event types: (1) 'operation' - edit operations (insert/delete/format), (2) 'cursor' - cursor position updates, (3) 'presence' - user joined/left, (4) 'lock' - section locked/unlocked, (5) 'sync' - sync request/response for offline users, (6) 'notification' - document restored/replaced/shared
WebSocket protocol: (1) Client sends: JSON over WebSocket {type: 'operation', op: {...}}, (2) Server broadcasts: JSON to all connected clients in same doc_id room, (3) Compression: Use WebSocket compression (permessage-deflate) to reduce bandwidth
Load balancing: WebSocket LB uses sticky sessions (session affinity), ensures user's WebSocket stays on same backend instance for duration of session
Failover: If WebSocket Gateway instance dies, client auto-reconnects to different instance (retry with exponential backoff), requests sync to catch up on missed operations
Step 14: Performance Optimization & Scaling
Redis as canonical copy: Short-lived cache (TTL 30 min) of current document state, serves 90% of read requests without hitting S3/DB, evicted when TTL expires or memory pressure
WebSocket Gateway scaling: Horizontal scaling with 10K connections per instance, auto-scale based on connection count (target: 7K connections per instance for headroom)
Op-log partitioning: Partition operations table by doc_id hash, each partition handles subset of documents, enables parallel processing
Snapshot compression: gzip compress snapshots before S3 upload (reduces storage cost by 70%), decompress on read
CDN for static assets: Editor UI, fonts, icons served via CDN (CloudFront) for fast global load times
Operation batching: Client batches rapid keystrokes (e.g., typing 'hello' sends 1 operation with 'hello' instead of 5 separate chars) if typing speed > 5 chars/sec
Lazy loading: Load document sections on-demand for very large docs (>100K chars), initial load shows first 10K chars, rest loaded as user scrolls
Garbage collection: Periodic cleanup of old operations (>90 days) after snapshots created, archive to S3 Glacier for compliance
7. Database Schema Details (from image)

Documents (PostgreSQL)
doc_id — uuid PRIMARY KEY
owner_id — uuid FK → Users
title — varchar(255)
metadata — jsonb ({created_at, updated_at, file_type, tags})
permissions — jsonb ([{user_id, role: 'view'/'edit'/'comment'}])
latest_snapshot_version — int (current version number)
Operations (PostgreSQL - Op-log, append-only)
op_id — uuid PRIMARY KEY
doc_id — uuid FK → Documents, INDEXED for queries
user_id — uuid (who made the edit)
type — enum ('insert', 'delete', 'format', 'replace_all')
position — int (character position in document)
content — text (inserted text or deleted text)
client_version — int (client's version when op created)
server_version — int (server-assigned sequence number)
timestamp — timestamp (server timestamp for ordering)
Composite Index — INDEX on (doc_id, server_version) for range queries
Snapshots (PostgreSQL)
snapshot_id — uuid PRIMARY KEY
doc_id — uuid FK → Documents, INDEXED
version — int (version number, incremental)
blob_path — varchar(500) (S3 path: docs/{doc_id}/v{version}.txt)
operations_since_last — int (count of operations applied)
created_at — timestamp
created_by — uuid (user_id or 'system' for auto-save)
Redis - Canonical Copy & Locks (from image shows Redis with TTL)
doc:{docId}:state — STRING (current document content) EX 1800 (30 min TTL)
cursors:{docId} — HASH {user_id: {cursor_pos, selection, timestamp}} EX 300 (5 min ephemeral)
lock:doc:{docId}:{sectionId} — STRING {user_id} EX 300 (pessimistic lock, 5 min TTL)
session:{sessionId} — HASH {user_id, doc_id, connected_at, last_activity} EX 3600
S3 - Blob Storage (from image shows S3)
Snapshot path — docs/{doc_id}/v{version}.txt (gzip compressed)
Archive path — archive/{doc_id}/ops_{year}_{month}.json.gz (old operations)
Lifecycle policy — Standard (0-30 days) → IA (30-90 days) → Glacier (>90 days)
8. OT vs CRDT - Deep Comparison (from image diagrams)

Operational Transformation (OT)
Core idea — Transform concurrent operations to account for changes made by other operations (conflict resolution via transformation)
Requirements — Requires central server to sequence operations, all clients must apply in same order
Algorithm — Transform(op1, op2) adjusts op1 based on op2's effect (e.g., position shift after insert/delete)
Pros — Simpler data structure (just the document text), smaller memory footprint, efficient for centralized systems
Cons — Complex transformation functions, requires central ordering point (single point of failure), difficult for multi-master setup
Best for — Client-server architecture like Google Docs (central server sequences all operations)
Conflict-Free Replicated Data Types (CRDT)
Core idea — Operations designed to be commutative (can be applied in any order and still converge to same state)
Requirements — Each character has unique ID (site_id + sequence), operations include metadata for deterministic ordering
Algorithm — Operations automatically commute, no transformation needed, eventual consistency guaranteed by design
Pros — No central server needed (peer-to-peer), works offline (operations stored locally), multi-master replication, simpler conflict resolution
Cons — Larger memory overhead (metadata per character), tombstones for deletes grow over time, complex data structure (CRDT tree/list)
Best for — Distributed systems, offline-first apps, peer-to-peer collaboration (e.g., Figma, some note-taking apps)
Production Usage
Google Docs — Uses OT (Operational Transformation) with central server sequencing
Figma — Uses CRDT for design collaboration (offline-first, multi-master)
Notion — Uses OT for real-time editing with central server
Hybrid approach — Some systems use OT for real-time + CRDT for offline/sync (best of both)
9. Collaborative Editing Problem (from image diagrams)

Problem scenario (from image): Document content 'ABC', User A and User B edit simultaneously offline/concurrently
User A operation: insert(R, 29) at position 29, document becomes 'ABC...R...' (A inserts at end)
User B operation: delete(0) at position 0, document becomes 'BC' (B deletes first character)
Challenge: How to merge these concurrent operations without conflicts? Both users see different intermediate states
Without OT/CRDT: Naive merge would lose one user's changes or create inconsistent state
With OT solution: (1) Server receives A's op first, assigns version 1, broadcasts to B, (2) Server receives B's op, transforms based on A's op: delete(0) needs no transform if A inserted at end, (3) Both clients replay operations in server order: A's insert → B's delete → converge to 'BC...R...'
With CRDT solution: (1) Each character has unique ID: 'A'={1,1}, 'B'={1,2}, 'C'={1,3}, (2) User A: insert 'R' with ID {1,29}, (3) User B: delete {1,1}, (4) Operations commute: delete {1,1} removes 'A' regardless of R's insertion, (5) Both clients converge to 'BC...R...' deterministically
From image note: 'Inconsistent' state shown during concurrent edits, final state must be 'consistent' after OT/CRDT resolution
Key guarantee: Strong eventual consistency - all clients that have seen the same set of operations will converge to identical state
10. Scaling & Optimization Techniques

Technique 1: WebSocket connection pooling - Each gateway instance handles 10K concurrent connections with persistent TCP connections
Technique 2: Redis canonical copy - Cache current document state with TTL=30 min, serves 90% of reads, evicts on expiry
Technique 3: Operation log partitioning - Partition by doc_id hash, enables parallel processing and horizontal scaling
Technique 4: Snapshot compression - gzip compress before S3 upload (70% size reduction), decompress on read
Technique 5: Cursor update throttling - Batch cursor updates every 100ms to reduce WebSocket traffic by 90%
Technique 6: Operation batching - Batch rapid keystrokes into single operation (5 chars/sec threshold) reduces op-log size
Technique 7: CDN for static assets - Editor UI, fonts, icons served via CloudFront for fast global access
Technique 8: Lazy loading - Load large documents (>100K chars) in chunks, initial 10K chars + load on scroll
Technique 9: Op-log archival - Move old operations (>90 days) to S3 Glacier after snapshots created, reduces hot storage cost
Technique 10: Auto-scaling - WebSocket gateways scale based on connection count (target 7K per instance), editor service scales on CPU
Technique 11: Snapshot strategy - Create snapshot every 50 operations OR 5 minutes, balances storage vs replay time
Technique 12: Kafka for decoupling - Document operations streamed to Kafka, consumers (reconciliation, analytics) process independently
11. Common Interview Questions

Q
How does Operational Transformation (OT) work to resolve conflicts in concurrent editing?
A
OT transforms concurrent operations to account for each other's effects: Scenario: Document 'hello', version 10. User A: insert('!', 5) → 'hello!', User B: delete

(1) → 'hllo'. Server receives A first (version 11), then B (version 12). When B's operation arrives, server sees B's client_version=10 but current server_version=11 (A's op applied). Transformation needed: B intended delete at position 1 in 'hello', but A inserted at position 5 (after), so delete position unchanged. Transform B's op: delete

(1) still valid. Apply to 'hello!' → 'hllo!'. Broadcast:

(1) Send A's insert to B,

(2) Send B's delete to A. Both clients apply operations in server order → converge to 'hllo!'. Complex case: If A inserted at position 0 instead: insert('X', 0) → 'Xhello'. B's delete

(1) needs transformation: original target was 'h' at position 1, but now 'h' shifted to position 2 (X inserted before). Transformed op: delete

(2). Apply to 'Xhello' → 'Xello'. Key rules:

(1) Insert before target position → shift target right (+1),

(2) Delete before target position → shift target left (-1),

(3) Operations applied in server-assigned order ensures all clients converge. Why server sequencing?: Without central ordering, Client A and B might apply operations in different orders → divergent states. Server acts as single source of truth for operation sequence. Edge cases:

(1) Concurrent inserts at same position → server orders arbitrarily (e.g., by timestamp or user_id),

(2) Overlapping deletes → first delete wins, second becomes no-op or shifts position. Production: Google Docs uses OT with central server handling millions of concurrent operations per second, operation log persisted for replay and versioning.

Q
What are CRDTs and how do they differ from Operational Transformation?
A
CRDT (Conflict-Free Replicated Data Types) are data structures designed so operations commute (can be applied in any order and converge to same state): Character-based CRDT example: Each character has unique ID = {site_id, sequence_number}. Document 'hello': 'h'={1,1}, 'e'={1,2}, 'l'={1,3}, 'l'={1,4}, 'o'={1,5}. User A offline: insert 'X' after 'h' → creates {1,6} with position 'after {1,1}'. User B offline: delete {1,1} (deletes 'h'). When A and B sync:

(1) A applies B's delete: removes 'h'={1,1}, document is 'ello' with X={1,6} positioned 'after {1,1}' → X goes at beginning → 'Xello',

(2) B applies A's insert: adds X={1,6} 'after {1,1}' but {1,1} deleted → deterministic rule: insert at position of deleted anchor → 'Xello'. Both converge to 'Xello' regardless of operation order. Key properties:

(1) Commutativity: op1(op2(doc)) = op2(op1(doc)),

(2) Associativity: (op1 ∘ op2) ∘ op3 = op1 ∘ (op2 ∘ op3),

(3) Idempotency: applying same operation twice has no additional effect. CRDT advantages:

(1) No central server needed (peer-to-peer),

(2) Works offline (store operations locally, sync later),

(3) Multi-master replication (multiple servers can accept writes),

(4) Simpler conflict resolution (operations designed to commute). CRDT disadvantages:

(1) Larger memory: each character has metadata (site_id, sequence), document 'hello' = 5 chars but CRDT structure = 5 objects with IDs + position pointers,

(2) Tombstones: deleted characters leave tombstones (invisible markers) that accumulate over time, require garbage collection,

(3) Complex data structure: CRDT typically uses tree or linked list (e.g., RGA - Replicated Growable Array) instead of simple string. OT vs CRDT comparison: OT: Central server sequences operations, simpler data structure (just text), smaller memory, complex transformation functions, single point of failure. CRDT: Decentralized (no central server), complex data structure (IDs + tombstones), larger memory, simpler operations (no transformation), works offline. Production usage: Google Docs uses OT (centralized architecture, millions of users), Figma uses CRDT (offline design collaboration), Notion uses OT (real-time editing with server), Automerge library implements CRDT for distributed apps. Hybrid approach: Some systems use OT for real-time editing (low latency, central server) + CRDT for offline sync (store local changes, merge when online) to get best of both. Example scenario: Collaborative design tool (Figma): User A offline: moves object 10px right, User B offline: moves same object 5px up, CRDT: Both operations commute → final position is (+10px right, +5px up) regardless of merge order. With OT: Would need server to transform one operation based on the other → more complex, requires connectivity.

Q
How do you handle offline editing and sync when the user reconnects?
A
Offline editing with sync-on-reconnect ensures no data loss and eventual consistency: Offline flow:

(1) User editing document, WebSocket connection drops (network failure),

(2) Client detects: WebSocket onerror/onclose event fires,

(3) Switch to offline mode: Display banner 'Working offline, changes will sync when online', enable local storage,

(4) User continues editing: All operations stored locally: IndexedDB.put('offline_ops', {doc_id, ops: [{op_id, type: 'insert', position: 10, content: 'hello', timestamp}]}), also store last_known_version: 42 (last version received from server),

(5) Optimistic UI: Show changes immediately in editor (user sees edits despite offline). Reconnect flow:

(1) Network restored, WebSocket reconnects (auto-retry with exponential backoff: 1s, 2s, 4s, 8s, max 30s),

(2) Client sends sync request: {type: 'sync_request', doc_id, last_known_version: 42, queued_ops_count: 5},

(3) Server responds: {type: 'sync_response', server_ops: [{op1, op2, op3}], current_version: 50},

(4) Server operations: ops that happened on server while client was offline (from other users),

(5) Client reconciliation:

(a) Apply server operations first: replay ops 43-50 from server to catch up,

(b) Transform local queued operations: use OT to transform local ops against server ops (adjust positions based on server changes),

(c) Apply transformed local ops: insert into local document,

(d) Send to server: {type: 'operations_batch', ops: [{transformed_op1, transformed_op2}]},

(6) Server validates: Check operations don't conflict with latest state, if valid → apply and broadcast to other users, if invalid (rare) → reject and request full resync. Conflict detection: If local op position > document length after applying server ops → conflict, show modal 'Conflicts detected during sync', options:

(a) Keep local changes (discard server changes in conflict area),

(b) Keep server changes (discard local changes),

(c) Manual merge (show diff, let user choose per-change). Example scenario: User A offline: deletes 'hello' at position 0-5, server state: 'hello world', User B (online): inserts '!!!' at position 6, server state: 'hello !!!world', User A reconnects:

(1) Server sends: insert('!!!', 6) operation,

(2) Client applies: 'hello' already deleted locally → transform insert position: 6 → 1 (5 chars deleted before position 6), apply: '!!!world',

(3) Client sends: delete(0, 5) operation,

(4) Server receives: document is 'hello !!!world', apply delete → '!!!world',

(5) All clients converge to '!!!world'. Edge cases:

(1) Very long offline period: If offline >24 hours with 1000s of operations, skip OT transformation, fetch latest snapshot from server, display merge UI showing local changes vs server state side-by-side,

(2) Document deleted: If document deleted on server while offline, on reconnect show 'Document no longer exists, save local changes as new document?',

(3) Permission revoked: If edit permission removed while offline, on reconnect convert operations to 'suggested changes' instead of direct edits. Performance optimization:

(1) Compress local operations: merge consecutive inserts ('h' + 'e' + 'l' + 'l' + 'o' → 'hello') before sending,

(2) Incremental sync: send operations in batches of 50 rather than all at once to avoid overwhelming server,

(3) Background sync: use Service Worker to attempt sync even when browser tab closed. Production: Google Docs supports offline editing via Chrome extension + local storage, syncs when online with OT transformation, shows conflicts if unsolvable automatically, provides version history to rollback if needed.

Q
How do you implement cursor presence and real-time cursor updates for multiple users?
A
Cursor presence shows where each user is typing/selecting in real-time: Architecture:

(1) Client tracks cursor position: Editor onChange event fires on every cursor move (arrow keys, mouse click, text selection),

(2) Throttle updates: Batch cursor position changes every 100ms to avoid flooding WebSocket (user typing fast = 10 chars/sec = 100 cursor updates/sec → throttled to 10 updates/sec),

(3) Send via WebSocket: {type: 'cursor', user_id: A, cursor_pos: 15, selection: {start: 10, end: 15}, timestamp},

(4) Server receives: Validates session active, extracts user info (name, color from session),

(5) Broadcast to others: {type: 'cursor_update', user: {user_id: A, name: 'Alice', color: '#FF5733', cursor_pos: 15, selection: {start: 10, end: 15}}},

(6) Other clients render: Colored cursor indicator at position 15 with label 'Alice', selection highlight from 10-15 in semi-transparent color. Cursor positioning: Calculate pixel position from character position:

(1) Document text: 'Hello\nWorld' (\n = newline),

(2) User A cursor at position 8 (in 'World'),

(3) Client calculates: Line 1 = 'Hello\n' (6 chars), position 8 = line 2, column 2 (W-o),

(4) Measure text: Use canvas measureText() or DOM getBoundingClientRect(), line 2 top = 20px, column 2 left = 15px,

(5) Render cursor: <div style={{position: 'absolute', top: 20px, left: 15px, borderLeft: '2px solid #FF5733'}}><label>Alice</label></div>. Selection rendering: Create overlay div with semi-transparent background: {position: 'absolute', top: 20px, left: 10px (start), width: 40px (end - start), height: 20px (line height), background: 'rgba(255,87,51,0.3)'}. Multiple users: Assign each user a unique color on join: colors = ['#FF5733', '#33FF57', '#3357FF', '#FF33F5'], user_color = colors[user_id % colors.length], persist in session: Redis HSET session:{session_id} 'color' {color}, broadcast to all clients on join. Ephemeral data: Cursor positions NOT persisted in database (too frequent updates, not durable data), stored in Redis with short TTL: HSET cursors:{doc_id} user:{user_id} '{cursor_pos: 15, selection: {...}, timestamp}' EX 300 (5 min), auto-expires when user disconnects. User disconnect handling: WebSocket close event → server removes cursor: HDEL cursors:{doc_id} user:{user_id}, broadcast to other clients: {type: 'cursor_removed', user_id: A}, clients remove cursor indicator and label. Cursor transformation (OT): When operations applied, cursor positions must be adjusted: User A cursor at position 10, User B inserts 'hello' at position 5, A's cursor position transforms: 10 → 15 (5 chars inserted before cursor), client automatically adjusts cursor position when receiving B's operation. Selection transformation: User A selected text 10-20, User B deletes chars 5-8 (3 chars before selection), A's selection transforms:

(1) start: 10 → 7 (3 chars deleted before start),

(2) end: 20 → 17 (3 chars deleted before end), adjusted selection: 7-17. Mobile optimization: On mobile, cursor updates less frequent (200ms throttle instead of 100ms), smaller cursor indicators (no labels, just dots), tap to see user name tooltip. Performance: 10 concurrent users × 10 cursor updates/sec = 100 WebSocket messages/sec, with throttling → 10 users × 1 update/0.1sec = 10 messages/sec per document (90% reduction), enables scaling to 100+ concurrent editors per document. Example UI: Google Docs shows: colored cursors with user names, selection highlights in user's color, active users list in top-right corner with colors, hover over cursor to see user name if label hidden. Advanced features:

(1) Cursor following: Click user in active list → scroll to their cursor position,

(2) Cursor hide: Toggle to hide other users' cursors if distracting,

(3) Collaborative editing analytics: track how long each user's cursor stays in each section (engagement metrics).

Q
How do you implement auto-save and periodic snapshots?
A
Auto-save prevents data loss and snapshots enable fast recovery: Triggering snapshots: Two conditions (whichever comes first):

(1) Operation count: Every 50 operations applied to document,

(2) Time-based: Every 5 minutes since last snapshot. Background job: Runs every minute, checks all active documents: SELECT doc_id, COUNT(*) as op_count FROM operations WHERE timestamp > (SELECT max(created_at) FROM snapshots WHERE doc_id=operations.doc_id) GROUP BY doc_id HAVING COUNT(*) >= 50. Snapshot creation flow:

(1) Reconciliation Service picks up: Triggered by job or Kafka event {type: 'snapshot_needed', doc_id, op_count: 52},

(2) Fetch last snapshot: SELECT blob_path, version FROM snapshots WHERE doc_id={doc_id} ORDER BY version DESC LIMIT 1 → gets S3 path docs/{doc_id}/v10.txt,

(3) Download snapshot: GET S3 docs/{doc_id}/v10.txt → base content 'Hello world',

(4) Fetch operations: SELECT * FROM operations WHERE doc_id={doc_id} AND server_version > 10 ORDER BY server_version ASC → 52 operations,

(5) Replay operations: FOR EACH op: apply to document (insert/delete/format) → final content 'Hello world! This is a test.',

(6) Validate: Check document integrity (no negative positions, content length matches expected),

(7) Compress: gzip compress final content (reduces size by 70%: 1000 chars → 300 bytes),

(8) Upload to S3: PUT docs/{doc_id}/v11.txt.gz with compressed content,

(9) Update database: BEGIN TRANSACTION; INSERT INTO snapshots (snapshot_id, doc_id, version: 11, blob_path: 's3://...v11.txt.gz', operations_since_last: 52, created_at: now()); UPDATE documents SET latest_snapshot_version=11, updated_at=now(); COMMIT;,

(10) Update Redis cache: SET doc:{doc_id}:state {uncompressed_content} EX 1800 (30 min),

(11) Publish event: Kafka 'doc.snapshot_created' → {doc_id, version: 11, op_count: 52} for analytics. Incremental snapshots: Instead of full document, store delta: {base_version: 10, operations: [op1, op2, ...52]}, saves storage but slower to reconstruct, full snapshot every 10 versions (versions 10, 20, 30, 40) for faster recovery. Auto-save indication: Client shows:

(1) 'Saving...' indicator when operations sent,

(2) 'Saved' with timestamp when server acknowledges: {type: 'ack', op_id, server_version},

(3) 'All changes saved to Drive' when idle for 5 seconds,

(4) 'Unsaved changes' if WebSocket disconnected (operations queued locally). Fast recovery from snapshot: User opens document:

(1) Fetch latest snapshot: GET S3 docs/{doc_id}/v11.txt.gz,

(2) Decompress: gunzip → 'Hello world! This is a test.',

(3) Fetch recent operations: SELECT * FROM operations WHERE doc_id={doc_id} AND server_version > 11 (only ops after snapshot),

(4) Replay: Apply 5 operations (since last snapshot 2 min ago) → current state,

(5) Load time: Snapshot fetch (50ms) + decompress (10ms) + replay 5 ops (5ms) = 65ms vs 500ms to replay 1000 ops from beginning. Garbage collection: Cleanup old operations after snapshots:

(1) Archive operations: SELECT * FROM operations WHERE doc_id={doc_id} AND server_version <= {snapshot_version - 1000},

(2) Store in S3 Glacier: PUT archive/{doc_id}/ops_2026_01.json.gz with compressed ops,

(3) Delete from hot DB: DELETE FROM operations WHERE doc_id={doc_id} AND server_version <= {snapshot_version - 1000},

(4) Retention: Keep operations for 90 days in hot storage, then archive, keep snapshots forever. Snapshot versioning: Each snapshot is a version: v1 (initial), v2 (after 50 ops), v3 (after 100 ops), enables rollback: user clicks 'Version history' → sees v1, v2, v3 with timestamps, can restore to any version. Concurrent editing during snapshot: Snapshot creation happens in background:

(1) Operations continue to be applied during snapshot generation,

(2) Snapshot captures state at specific server_version (e.g., version 62),

(3) New operations (version 63+) applied after snapshot completes, no downtime. Production numbers: Google Docs generates ~100M snapshots/day across all documents, average snapshot size 50KB (compressed), stored in GCS (Google Cloud Storage) with lifecycle management (hot → cold → archive), enables sub-second document loading for 99% of users.

Q
How do you handle version history and rollback to previous versions?
A
Version history enables users to view and restore previous document states: Version creation: Automatic versioning via snapshots:

(1) Every 50 operations → new snapshot = new version,

(2) Manual versions: user clicks 'Name current version' → creates named snapshot with label (e.g., 'Final draft v1'),

(3) Timestamps: each version stores created_at for sorting and display. Fetching version history: User clicks 'Version history' button: GET /v1/api/docs/{doc_id}/versions →

(1) Query database: SELECT snapshot_id, version, created_at, operations_since_last, created_by, label FROM snapshots WHERE doc_id={doc_id} ORDER BY version DESC LIMIT 50,

(2) Join with users: get creator names,

(3) Response: [{version: 11, created_at: '2026-01-22T10:30:00Z', label: null, created_by: 'system', ops_count: 52}, {version: 10, created_at: '10:25:00Z', label: 'Draft 1', created_by: 'Alice', ops_count: 50}],

(4) UI displays: Timeline with version numbers, timestamps, creators, operation counts. Viewing specific version: User clicks version 10: GET /v1/api/docs/{doc_id}/version/10 →

(1) Fetch snapshot: GET S3 docs/{doc_id}/v10.txt.gz,

(2) Decompress and return: {version: 10, content: 'Hello world', metadata: {created_at, created_by}},

(3) Display: Read-only preview with banner 'Viewing version 10 from 10:25 AM',

(4) Show changes: Diff current version vs selected version (highlight additions in green, deletions in red),

(5) Navigation: 'Previous version' / 'Next version' buttons to browse history. Restoring version: User clicks 'Restore this version': POST /v1/api/docs/{doc_id}/restore with {target_version: 10} →

(1) Validate: Check user has edit permission,

(2) Fetch target version content: GET S3 docs/{doc_id}/v10.txt.gz → 'Hello world',

(3) Create restore operation: {type: 'replace_all', content: {v10_content}, user_id, timestamp},

(4) Append to op-log: INSERT INTO operations (op_id, doc_id, type: 'restore', content, server_version: 63),

(5) Create new snapshot: Upload to S3 docs/{doc_id}/v12.txt.gz with v10 content (restored state becomes new version 12),

(6) Update database: INSERT INTO snapshots (version: 12, label: 'Restored from v10', created_by: user_id),

(7) Notify active editors: Broadcast via WebSocket {type: 'document_restored', from_version: 10, to_version: 12, by_user: 'Bob'},

(8) Clients reload: Fetch latest version (v12), discard local unsaved changes (with confirmation prompt). Version comparison: Side-by-side diff: User selects two versions (v8 vs v10) → server computes diff:

(1) Fetch both contents from S3,

(2) Run diff algorithm (Myers diff): computes line-by-line changes,

(3) Response: [{type: 'equal', text: 'Hello'}, {type: 'delete', text: 'old'}, {type: 'insert', text: 'world'}],

(4) UI renders: Side-by-side view with color coding (red=deleted, green=added, white=unchanged),

(5) Merge option: 'Accept left' / 'Accept right' / 'Accept both' for conflicting changes. Named versions: User can name versions for milestones:

(1) Click 'Name current version' → modal prompts for name,

(2) POST /v1/api/docs/{doc_id}/versions with {label: 'Final draft before review'},

(3) Creates snapshot with label: INSERT INTO snapshots (..., label: 'Final draft before review'),

(4) Shows in version history with special marker (star icon). Auto-naming: System automatically names versions:

(1) Major edits: 'Version from 2 hours ago (50 operations)',

(2) Daily: 'January 22, 2026 10:30 AM',

(3) User-triggered: 'Saved by Alice'. Retention policy: Keep all versions for:

(1) 30 days: full access and restore,

(2) 90 days: view-only (can't restore directly, must copy content),

(3) 1 year: archived to Glacier (retrieve takes 12 hours),

(4) Forever: named versions never expire (user-marked important milestones). Change attribution: Version history shows:

(1) Who made changes: SELECT DISTINCT user_id FROM operations WHERE doc_id={doc_id} AND server_version BETWEEN {v8} AND {v10},

(2) Change summary: 'Alice added 500 words, Bob deleted 200 words, Carol formatted 3 paragraphs',

(3) Activity timeline: Graph showing edit activity over time (operations/hour),

(4) Detailed changes: Drill down to see individual operations by user. Optimizations:

(1) Lazy loading: Load version list (50 most recent), load older versions on scroll (pagination),

(2) Thumbnail previews: Generate image thumbnails of document at each version (first page screenshot) for visual navigation,

(3) Fast diff: Use precomputed diffs between consecutive versions instead of computing on-demand,

(4) Compression: Old versions compressed more aggressively (bzip2 instead of gzip) to save storage. Mobile UX: Simplified version history: show only major versions (daily snapshots), restore requires confirmation with explanation, diff view shows inline changes instead of side-by-side (screen space limited). Production example: Google Docs stores version history for all documents: millions of versions generated per day, enables rollback to any point in time within 30 days, named versions kept forever, change attribution shows exactly who made each edit with timestamps.

Q
How do you implement the Reconciliation Service and what does it do?
A
Reconciliation Service ensures data consistency by validating and rebuilding canonical document state from operation log: Purpose:

(1) Validate consistency: Ensure operations applied correctly and document state matches expectations,

(2) Generate snapshots: Create periodic snapshots for fast recovery,

(3) Detect anomalies: Identify corrupted operations or invalid states,

(4) Rebuild state: Reconstruct document from op-log if cache/snapshot lost. Architecture: Kafka consumer + background jobs:

(1) Kafka consumer: Subscribes to 'doc.operations' topic with consumer group 'reconciliation-service', processes every operation in real-time,

(2) Background jobs: Periodic full reconciliation runs nightly (2 AM) to validate all documents. Real-time reconciliation flow:

(1) Operation published: Editor Service → Kafka 'doc.operations' topic: {doc_id, op_id, type: 'insert', position: 10, content: 'hello', user_id, server_version: 42, timestamp},

(2) Reconciliation Service consumes: Receives operation event from Kafka,

(3) Validate operation:

(a) Check position valid: position <= document_length (can't insert at position 1000 if doc only 100 chars),

(b) Check user permissions: query DB to ensure user_id has edit permission,

(c) Check sequence: server_version increments by 1 from previous (no gaps),

(4) Update metrics: Increment counters {operations_processed, operations_by_doc, operations_by_user},

(5) Check snapshot trigger: SELECT COUNT(*) FROM operations WHERE doc_id={doc_id} AND timestamp > (SELECT max(created_at) FROM snapshots WHERE doc_id={doc_id}), if count >= 50 → trigger snapshot creation. Snapshot generation:

(1) Fetch last snapshot: SELECT blob_path, version FROM snapshots WHERE doc_id={doc_id} ORDER BY version DESC LIMIT 1 → S3 path docs/{doc_id}/v10.txt.gz,

(2) Download: GET S3 docs/{doc_id}/v10.txt.gz → base content,

(3) Fetch operations: SELECT * FROM operations WHERE doc_id={doc_id} AND server_version > 10 ORDER BY server_version ASC → 52 operations since v10,

(4) Replay operations: Apply each operation to document:

(a) insert(10, 'hello') → insert 'hello' at position 10,

(b) delete(15, 3) → delete 3 chars starting at position 15,

(c) Validate after each: check position valid, content length matches expected,

(5) Compute checksum: SHA256 hash of final content for integrity verification,

(6) Upload snapshot: PUT S3 docs/{doc_id}/v11.txt.gz with compressed content + checksum metadata,

(7) Update DB: INSERT INTO snapshots (snapshot_id, doc_id, version: 11, blob_path, checksum, operations_since_last: 52, created_at),

(8) Update Redis: SET doc:{doc_id}:state {content} EX 1800. Anomaly detection:

(1) Invalid position: If operation position > document length → log error, skip operation, flag document for review: INSERT INTO reconciliation_errors (doc_id, op_id, error: 'Invalid position', severity: 'high'),

(2) Sequence gap: If server_version jumps (42 → 44, missing 43) → check if operation 43 lost, attempt recovery from Kafka offset,

(3) Checksum mismatch: After snapshot creation, recompute checksum from replay vs stored checksum, if mismatch → document state corrupted → alert admin,

(4) Performance anomaly: If snapshot generation takes >10 seconds → document too large or operations too complex → flag for optimization. Full reconciliation (nightly):

(1) Trigger: Cron job at 2 AM (low traffic time),

(2) Batch process: SELECT doc_id FROM documents WHERE updated_at > now() - INTERVAL '7 days' ORDER BY updated_at DESC → active documents,

(3) FOR EACH document:

(a) Fetch last snapshot,

(b) Replay all operations since snapshot,

(c) Compute checksum,

(d) Compare with Redis cache (if exists),

(e) If mismatch: Generate new snapshot, log inconsistency,

(4) Report: {total_docs_checked: 10000, snapshots_created: 500, errors_detected: 2, total_time: '45 min'},

(5) Alerts: If errors_detected > 10 → PagerDuty alert to on-call engineer. State rebuild: If document state lost (Redis evicted, snapshot corrupted):

(1) Service receives request: GET /v1/api/docs/{doc_id},

(2) Fetch operations from beginning: SELECT * FROM operations WHERE doc_id={doc_id} ORDER BY server_version ASC,

(3) Replay all operations from empty document: start with '', apply each insert/delete sequentially,

(4) Generate snapshot: Save current state to S3,

(5) Cache in Redis: SET doc:{doc_id}:state {content} EX 1800,

(6) Time: Replaying 10K operations takes ~5 seconds (acceptable fallback). Metrics & monitoring:

(1) Grafana dashboards: operations/sec, snapshot creation rate, reconciliation errors, op-log replay time,

(2) Alerts: if reconciliation_errors > 10/hour → alert, if snapshot_creation_time > 10 sec → alert (doc too large),

(3) SLIs: 99.9% of operations processed within 1 sec, 99% of snapshots created within 5 sec. Scaling:

(1) Kafka consumer parallelism: 10 consumer instances process 10 partitions (partition by doc_id hash),

(2) Snapshot workers: 50 workers in thread pool handle snapshot generation concurrently,

(3) Rate limiting: Max 100 snapshots/sec to avoid overloading S3, queue excess for later. Error recovery:

(1) Corrupted operation: Skip and log, continue with next, mark document as 'inconsistent' for manual review,

(2) Database failure: Kafka retains events for 7 days, replay from offset after recovery,

(3) S3 failure: Retry snapshot upload with exponential backoff, temporarily serve from Redis cache only. Production: Google Docs reconciliation processes billions of operations daily, generates millions of snapshots, detects and auto-corrects inconsistencies, ensures 99.99% data integrity, enables disaster recovery (rebuild any document from op-log).

Q
How would you scale this system to handle 1 million concurrent editors?
A
Scaling to 1M concurrent editors requires horizontal scaling at every layer: WebSocket Gateway scaling:

(1) Capacity: Each instance handles 10K connections, need 1M / 10K = 100 instances,

(2) Load balancing: Use TCP load balancer (ELB/ALB) with sticky sessions (IP hash), ensures user's WebSocket stays on same instance for duration,

(3) Auto-scaling: Scale based on connection count, target 7K connections/instance (30% headroom),

(4) Connection handling: WebSocket upgrade from HTTP, maintain persistent TCP connections, heartbeat every 30 sec to detect disconnects,

(5) Memory: 10K connections × 10 KB/connection = 100 MB per instance (manageable),

(6) Network: 10K connections × 10 updates/sec × 500 bytes = 50 MB/sec = 400 Mbps per instance. Document Editor Service scaling:

(1) Stateless service: Each instance can process any document (no affinity),

(2) Horizontal scaling: 200 instances to handle operations from 1M users,

(3) Load distribution: Operations partitioned by doc_id hash, Kafka topic has 100 partitions (2 instances per partition for redundancy),

(4) Operation processing: Each instance processes 5K ops/sec (1M users / 200 instances, assuming 1 operation per user per second average),

(5) Cache hit rate: Redis provides 95% cache hits for document state, only 5% hit DB. Redis scaling:

(1) Redis Cluster: 50 nodes (master + replicas), each node handles 20K documents,

(2) Sharding: Shard by doc_id hash, hash(doc_id) % 50 = shard_id,

(3) Memory: 1M active documents × 50 KB avg = 50 GB, with replication (3x) = 150 GB total,

(4) Throughput: 50 nodes × 100K ops/sec = 5M ops/sec capacity (1M users × 10 ops/sec = 10M ops/sec required, so need 100 nodes),

(5) Eviction policy: LRU eviction with TTL=30 min for document state, hot documents stay cached, cold documents evicted and refetched from S3. Database (PostgreSQL) scaling:

(1) Read replicas: 10 replicas for read queries (fetching operations, user permissions, version history),

(2) Write primary: 1 primary for writes (append operations to op-log),

(3) Sharding: Partition operations table by doc_id hash (100 shards), each shard handles 1% of documents,

(4) Write throughput: 1M users × 1 operation/sec = 1M ops/sec, with batching (10 ops per transaction) = 100K transactions/sec, PostgreSQL handles ~10K txn/sec per shard, need 10 shards minimum,

(5) Connection pooling: Each API instance maintains 200 connections, 200 instances × 200 connections = 40K connections (use PgBouncer to pool down to 500 connections per database). Kafka scaling:

(1) Cluster: 20 brokers with replication factor 3,

(2) Partitions: 100 partitions for 'doc.operations' topic, enables parallel consumption,

(3) Throughput: 1M ops/sec × 500 bytes/op = 500 MB/sec write, Kafka handles 1 GB/sec per broker, 20 brokers = 20 GB/sec capacity (plenty of headroom),

(4) Retention: 7 days retention (enables replay for disaster recovery),

(5) Consumers: 100 consumer instances (1 per partition) for Reconciliation Service, Notification Service, Analytics Service. S3 scaling:

(1) Snapshots: 1M active documents × 1 snapshot/5 min = 12M snapshots/hour = 3333 snapshots/sec,

(2) S3 write capacity: 5500 requests/sec per prefix (first letter of doc_id), use multiple prefixes (a/, b/, c/, ... z/) = 5500 × 26 = 143K writes/sec (sufficient),

(3) Read capacity: Document opening = fetch snapshot, 1M users opening docs over 10 min = 100K opens/min = 1666 ops/sec (well within limits),

(4) CDN caching: CloudFront caches frequent snapshots (popular documents), 90% cache hit rate reduces S3 reads by 10x. Network bandwidth:

(1) WebSocket traffic: 1M users × 10 ops/sec × 500 bytes = 5 GB/sec = 40 Gbps,

(2) Kafka traffic: 500 MB/sec write + 500 MB/sec × 3 consumers = 2 GB/sec = 16 Gbps,

(3) S3 traffic: 3333 snapshots/sec × 50 KB = 166 MB/sec = 1.3 Gbps,

(4) Total: ~60 Gbps, use AWS VPC with 100 Gbps capacity. Cost optimization:

(1) Spot instances: Use spot instances for WebSocket Gateway (70% discount), graceful failover on interruption,

(2) Reserved instances: Reserve Editor Service instances (1-year commitment for 40% discount),

(3) S3 lifecycle: Move old snapshots (>90 days) to Glacier (10x cheaper),

(4) Compression: gzip snapshots (70% size reduction), saves S3 storage and transfer costs,

(5) Total cost: ~$500K/month for 1M concurrent users (WebSocket $200K + Databases $150K + Kafka $50K + S3 $50K + Network $50K). Monitoring & observability:

(1) Metrics: operations/sec, WebSocket connections, cache hit rate, snapshot generation time, error rate,

(2) Dashboards: Grafana with real-time graphs per service,

(3) Alerts: PagerDuty for critical errors (DB down, Kafka lag >1 min, 5xx errors >1%),

(4) Distributed tracing: Jaeger for request tracing across services (WebSocket → Editor → Kafka → DB → S3). Failure handling:

(1) WebSocket instance failure: Client auto-reconnects to different instance (exponential backoff), requests sync to catch up on missed operations,

(2) Editor Service failure: Kafka retains events, new instance replays from last committed offset,

(3) Redis failure: Fallback to fetching snapshots from S3 + replaying recent operations from DB,

(4) Database failure: Promote read replica to primary (2-3 min RTO), Kafka retains events for replay after recovery,

(5) S3 failure: Serve from Redis cache (covers last 30 min of activity), queue snapshot writes for later. Production examples: Google Docs handles millions of concurrent editors using similar architecture, scales horizontally at every layer, uses custom OT algorithm optimized for millions of operations per document, maintains 99.9% uptime, handles peak loads during major events (e.g., collaborative planning for large conferences).

12. Key Numbers to Remember

Scale & Performance
Concurrent Editors — Up to 50-100 users per document simultaneously
Document Size — 1.02M characters limit (Google Docs)
Update Latency — <300ms for operations to propagate to all clients
WebSocket Connections — 10K connections per gateway instance
Caching & Snapshots
Redis Cache TTL — 30 minutes for document state (canonical copy)
Cursor Cache TTL — 5 minutes (ephemeral presence data)
Snapshot Trigger — Every 50 operations OR every 5 minutes
Snapshot Compression — gzip reduces size by 70% (1000 chars → 300 bytes)
Operation Processing
Operation Log — Append-only, indexed by (doc_id, server_version)
OT Transformation — Position adjustment based on concurrent insert/delete operations
Cursor Update Throttle — 100ms batching (reduces WebSocket traffic by 90%)
Replay Time — 10K operations replay in ~5 seconds for state rebuild
Scaling Numbers
1M Concurrent Users — 100 WebSocket instances + 200 Editor Service instances + 50 Redis nodes
Operations/Second — 1M ops/sec (1M users × 1 op/sec avg), peaks at 10M ops/sec
S3 Snapshots — 3333 snapshots/sec at scale (1M docs × 1 snapshot/5 min)
Network Bandwidth — ~60 Gbps total (WebSocket 40 Gbps + Kafka 16 Gbps + S3 1.3 Gbps)
Key Interview Tips

⚠️
CRITICAL: Operations MUST be sequenced by central server in OT approach. Without server-assigned order, clients will apply operations in different sequences → divergent states. Server version number is the single source of truth for operation order.

⭐
Interviewers ALWAYS ask: 'OT vs CRDT difference?'. Answer: OT requires central server sequencing, transforms concurrent ops, simpler data structure. CRDT operations commute (any order), no server needed, works offline, but larger memory overhead (IDs + tombstones).

💡
Snapshot strategy optimization: Create snapshot every 50 operations OR 5 minutes. Balances storage cost vs replay time. With 50 ops snapshots, max replay = 50 ops (~50ms) vs 10K ops replay = 5 seconds.

⭐
Must mention: Redis as canonical copy with TTL=30 min. Serves 90% of reads without hitting S3/DB. Evicted documents refetched from S3 snapshot + replay recent ops. Hot documents stay cached.

⚠️
NEVER persist cursor positions in database. Cursor updates are ephemeral (100 updates/sec/user). Store in Redis with TTL=5 min, broadcast via WebSocket, removed on disconnect.

💡
Offline editing sync: Store operations locally (IndexedDB), on reconnect: (1) Fetch server ops since last_known_version, (2) Transform local ops using OT, (3) Apply transformed ops to server. Ensures eventual consistency.

⭐
Interviewers love: 'How does collaborative editing problem get solved?'. Walk through: User A inserts, User B deletes concurrently → Server sequences (A first) → Transforms B's position based on A's insert → Both clients replay in server order → converge to same state.

⚠️
NEVER skip operation log validation. Check: (1) position <= document length, (2) user has edit permission, (3) server_version increments by 1. Invalid operations → skip + log error + flag for review. Prevents corruption.

💡
Reconciliation Service ensures consistency: Validates operations, generates snapshots, detects anomalies, rebuilds state from op-log. Runs nightly full reconciliation, processes operations in real-time via Kafka.

⭐
Must explain: WebSocket for real-time. HTTP polling (old approach) = 1 request/sec = 1M users = 1M req/sec. WebSocket = persistent connection = only send when data changes = 100x less traffic.

system-design
collaborative-editing
google-docs
