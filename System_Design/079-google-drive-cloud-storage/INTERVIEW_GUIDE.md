# Google Drive — Interview Script
## Design Google Drive / Dropbox / OneDrive
### Speak This Word-for-Word to Your Interviewer

> **How to use this:**
> **Step 1 — Read Big Picture** (PAGE 1): burn the overview into your head.
> **Step 2 — Read Glossary** (PAGE 2): know every term before the deep-dive.
> **Step 3 — Read Component Choices** (PAGE 3): know WHY each tech was chosen.
> **Step 4 — Read the Interview Script** (PAGE 4 onward): speak each step aloud 2-3 times.
>
> **Print tip:** Portrait A4 at 10pt monospace fits all diagrams. Glossary → landscape if needed.

---

# ═══════════════ PAGE 1 — START HERE ═══════════════

## BIG PICTURE (Understand This Before Anything Else)

> **► STUDY this diagram, don't draw it ◄**
> Two things make Google Drive different from YouTube:
> (1) files can be ANY type, (2) the same file must sync to ALL devices.
> Burn these two flows into your head.

```
┌─────────────────────────────────────────────────────────────────────┐
│                   GOOGLE DRIVE — BIG PICTURE                         │
└─────────────────────────────────────────────────────────────────────┘

DEVICE A uploads/edits file          ALL OTHER DEVICES get the change
        │                                          │
        ▼                                          ▼
┌──────────────────┐               ┌──────────────────────────────┐
│  CLIENT APP      │               │  DEVICE B / C / D            │
│  Desktop/Mobile  │               │  Phone, Tablet, Web          │
│  ┌────────────┐  │               └──────────────┬───────────────┘
│  │File Watcher│  │                              │ receives sync push
│  │(inotify /  │  │               ┌──────────────▼───────────────┐
│  │ FSEvents)  │  │               │  Sync Service                │
│  └────┬───────┘  │               │  (fans out to all devices)   │
│       │file      │               └──────────────┬───────────────┘
│       │changed   │                              │ Kafka event
└───────┼──────────┘               ┌──────────────▼───────────────┐
        │                          │  Kafka Broker                 │
        ▼                          │  topic: file-events           │
  CLIENT CHUNKER                   └──────────────────────────────┘
  (splits file into                              ▲
   5 MB chunks,                                  │ on commit
   SHA-256 per chunk)                            │
        │                          ┌─────────────┴────────────────┐
        │ UPLOAD PIPELINE          │  File Upload Service         │
        ▼                          │  + Validator Service         │
  API GATEWAY                      └──────────────────────────────┘
  (auth, routes)                                 ▲
        │                                        │
        ▼                          ┌─────────────┴────────────────┐
  File Upload Service              │  Metadata DB (MySQL)         │
  1. Check quota                   │  folders, files, versions,   │
  2. Return presigned S3 URLs      │  chunks, permissions         │
  3. Client uploads DIRECTLY to S3 └──────────────────────────────┘
  4. On commit → validate hashes
  5. Save metadata to MySQL                ┌──────────────────────┐
  6. Kafka event → Sync Service            │  S3 Blob Storage     │
                                           │  actual file chunks  │
                                           │  partitioned by      │
                                           │  fileId/chunkId      │
                                           └──────────────────────┘

THE CORE INSIGHT:
  Our servers NEVER touch file bytes. Only metadata.
  Clients upload chunks DIRECTLY to S3 via presigned URLs.
  This is why Google Drive can scale to billions of files.

SYNC IN ONE SENTENCE:
  Device A commits upload → Kafka event → Sync Service → push to
  Device B/C/D → each device downloads only changed chunks (delta sync).
```

---

## RAPID ANSWER — If You Only Have 5 Minutes

*Read this first. Understand the whole answer before going deep.*

```
"I'd design Google Drive with five pieces:

1. FILE UPLOAD (Chunked, direct to S3):
   Files can be up to 15 GB — can't upload in one HTTP request.
   Split into 5 MB chunks client-side. Compute SHA-256 per chunk.
   Backend generates a presigned S3 URL per chunk. Client uploads
   directly to S3 (bypasses our servers — they never see file bytes).
   On commit, Validator Service confirms chunk hashes match.
   Metadata (path, size, version, chunk IDs) saved to MySQL.

2. SYNC ACROSS DEVICES (Kafka + push/pull):
   After commit, Kafka event → Sync Service → push notification to
   all linked devices. Each device downloads only CHANGED chunks
   (delta sync: re-hash all chunks, compare to local metadata index,
   upload only the ones whose hash changed).
   If a device was offline → it polls on reconnect (pull sync).

3. STORAGE (S3 + MySQL + Cassandra):
   S3 for file bytes (250 PB, can't store in a DB).
   MySQL for metadata (folders, files, versions, permissions) —
   needs JOINs (e.g., 'all files in folder X with permissions').
   Cassandra for chunks table (pure lookup by chunkId, high writes).
   Redis for upload session state and quota reservation.

4. DEDUPLICATION:
   File-level: hash entire file on INIT. If same hash exists →
   skip upload entirely, create new version pointing to old chunks.
   Chunk-level: same chunk across files/users → stored once in S3.
   Result: significant storage savings on re-uploads and identical files.

5. SHARING + PERMISSIONS:
   Permission model: VIEW, COMMENT, EDIT per file/folder per user.
   Folder permissions cascade to all children.
   Cached in Redis (5-min TTL). Permission check on every API call."
```

---

# ═══════════════ PAGE 2 — GLOSSARY ═══════════════

## Terminology — Know These Before Reading Further

*Every term you will encounter in this guide, explained simply.*
*Print tip: switch to landscape orientation or 9pt font if table wraps.*

```
┌──────────────────┬──────────────────────────────────────────────────────┐
│ Term             │ What It Means (Simply)                               │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Chunked Upload   │ Splitting a large file into small fixed-size pieces  │
│                  │ (5 MB each) and uploading each piece independently.  │
│                  │ If one chunk fails, only that chunk is re-uploaded.  │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Presigned URL    │ A temporary URL (expires in 5 min) that lets the     │
│                  │ client upload a chunk directly to S3 without routing │
│                  │ through our backend servers.                         │
├──────────────────┼──────────────────────────────────────────────────────┤
│ SHA-256 Hash     │ A fingerprint of a file or chunk. If the content     │
│                  │ changes even by 1 byte, the hash changes completely. │
│                  │ Used to detect corruption and duplicate chunks.      │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Delta Sync       │ When a file changes, only the MODIFIED chunks are    │
│                  │ re-uploaded. A 100 MB file with 1 changed paragraph  │
│                  │ → only ~5 MB uploaded, not 100 MB.                   │
├──────────────────┼──────────────────────────────────────────────────────┤
│ File Watcher     │ OS-level process that watches a folder for changes.  │
│ (inotify /       │ When you save a file, inotify (Linux) / FSEvents     │
│  FSEvents)       │ (Mac) fires an event immediately. Dropbox/Drive use  │
│                  │ this to detect changes without polling.              │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Local Metadata   │ A SQLite database on each device. Stores the hash    │
│ Index            │ of every chunk uploaded. Used to detect which chunks │
│                  │ changed on delta sync.                               │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Deduplication    │ If two users upload the same file (identical hash),  │
│                  │ S3 stores it only once. Both users' metadata points  │
│                  │ to the same S3 object. Saves storage.               │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Versioning       │ Every upload creates a new FileVersion record.       │
│                  │ Old versions kept for rollback. Only the N most      │
│                  │ recent versions stored to save space.                │
├──────────────────┼──────────────────────────────────────────────────────┤
│ S3               │ Amazon cloud storage. Stores file chunks. Unlimited  │
│                  │ scale, cheap, durable (11-nines). Not a database.    │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Kafka            │ Message queue. After upload commits, publishes an    │
│                  │ event. Sync Service consumes it to notify devices.   │
│                  │ Decouples upload from sync.                          │
├──────────────────┼──────────────────────────────────────────────────────┤
│ MySQL            │ Relational DB. Stores folders, files, versions,      │
│                  │ permissions metadata. Needs JOINs — can't use        │
│                  │ Cassandra for this.                                  │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Cassandra        │ NoSQL DB for chunk metadata. Pure lookup by chunkId, │
│                  │ high write volume — perfect for Cassandra.           │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Redis            │ In-memory store. Holds upload session state (which   │
│                  │ chunks completed), quota reservation, permission     │
│                  │ cache. Sub-millisecond reads.                        │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Push Sync        │ Server-initiated notification. After Device A        │
│                  │ uploads, server pushes "file changed" to Device B/C.│
│                  │ Real-time. Uses WebSocket or Firebase FCM.           │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Pull Sync        │ Client-initiated check. Device comes back online →   │
│                  │ asks server "what changed since timestamp T?"        │
│                  │ Fallback when push notifications are missed.         │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Quota            │ Storage limit per user (e.g. 15 GB free). Enforced  │
│                  │ atomically via Redis Lua script on upload INIT to    │
│                  │ prevent race conditions.                             │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Validator Svc    │ After all chunks uploaded, re-hashes chunks in S3,  │
│                  │ compares to client-sent hashes. Confirms no          │
│                  │ corruption during upload. Then saves final metadata. │
└──────────────────┴──────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 3 — WHY EACH COMPONENT ═══════════════

## Component Choices — Why We Picked Each One

*The most common follow-up in interviews. Know these.*

```
┌─────────────────────┬──────────────────────────────────────────────────┐
│  COMPONENT          │  WHY THIS? NOT SOMETHING ELSE?                   │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  S3                 │ WHY: 250 PB of file chunks. No database can      │
│  (Blob Storage)     │ store binary blobs at this scale cheaply.        │
│                     │ S3: unlimited, cheap ($0.02/GB), 11-nines        │
│                     │ durability, streams well over HTTP.              │
│                     │                                                  │
│                     │ WHY NOT DB for blobs: PostgreSQL BLOBs explode   │
│                     │ table size. 250 PB in a relational DB = disaster. │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Presigned URL      │ WHY: Files can be 15 GB. If our backend forwards │
│  (Direct S3 Upload) │ every file: 100M DAU × 10 MB = 1 TB/sec through │
│                     │ our load balancer. Impossible to scale.          │
│                     │ Presigned URL: client uploads directly to S3.   │
│                     │ Our servers only handle metadata (tiny payloads).│
│                     │                                                  │
│                     │ WHY NOT proxy via backend: Double network hop,  │
│                     │ massive memory usage, backend becomes bottleneck. │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Chunked Upload     │ WHY: 15 GB files can't go in one HTTP request.  │
│  (5 MB chunks)      │ Problems with single-request upload:             │
│                     │ (1) LB timeouts at 30-120s (15 GB = hours).     │
│                     │ (2) Network drop = restart from scratch.         │
│                     │ (3) No progress indicator.                       │
│                     │ (4) Server buffers entire file in memory.        │
│                     │ Chunks: each is small, retryable, parallelizable.│
│                     │                                                  │
│                     │ WHY NOT multipart S3 upload directly: S3         │
│                     │ multipart works but we'd lose: hash validation,  │
│                     │ dedup, quota checks, chunk-level dedup.          │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  MySQL              │ WHY: File metadata is RELATIONAL by nature.      │
│  (Metadata)         │ folders → files → versions → chunks → permissions│
│                     │ A query like "all files in folder X with their   │
│                     │ permissions" needs JOINs. Cassandra can't do     │
│                     │ JOINs — you'd need 4 separate tables + app-side  │
│                     │ joins = complex, inconsistent.                   │
│                     │                                                  │
│                     │ WHY NOT Cassandra for all metadata: No JOINs,   │
│                     │ no FK constraints, no transactions across rows.  │
│                     │ CORRECT to use Cassandra for chunks table        │
│                     │ (pure lookup by chunkId, no joins needed).       │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Redis              │ WHY: Upload sessions are short-lived state.      │
│  (Upload Session +  │ During a multi-chunk upload, we track which      │
│   Quota)            │ chunks are done, their hashes. This state is     │
│                     │ read/written for every chunk (many times).       │
│                     │ Redis: sub-ms, TTL support (auto-cleanup).       │
│                     │ Quota: Lua script for atomic check-and-reserve.  │
│                     │                                                  │
│                     │ WHY NOT MySQL for session state: Too slow for    │
│                     │ per-chunk reads/writes. DB rows have no TTL.     │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Kafka              │ WHY: Sync must not be on the critical upload path.│
│  (Sync Events)      │ After commit, we need to notify 3-5 other devices│
│                     │ per user. Doing this synchronously delays the    │
│                     │ upload response. With Kafka: publish one event,  │
│                     │ Sync Service handles fan-out async.              │
│                     │ If Sync Service is slow, upload is unaffected.  │
│                     │                                                  │
│                     │ WHY NOT direct push in upload response: Tight    │
│                     │ coupling. One slow device notification blocks all.│
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  CDN (CloudFront)   │ WHY: Downloads (not uploads) benefit from CDN.  │
│  (Download Only)    │ A shared company document downloaded by 1000     │
│                     │ employees → CDN caches it at the edge PoP.      │
│                     │ Each employee gets it in ~5ms, not ~200ms from  │
│                     │ S3 us-east-1. Also: CDN Range request support   │
│                     │ enables resumable downloads.                     │
│                     │                                                  │
│                     │ WHY NOT CDN for uploads: Uploads are user-unique.│
│                     │ Can't cache an upload. CDN is for reads only.   │
│                     │                                                  │
└─────────────────────┴──────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 4+ — FULL INTERVIEW SCRIPT ═══════════════

---

## OPENING — When Interviewer Says "Design Google Drive"

*"Great question. Google Drive is a distributed file storage platform
with sync across devices. Before I design it, I want to ask a few
questions — because the upload protocol and sync mechanism depend
heavily on the constraints."*

---

## STEP 1 — Requirements Gathering (Speak This Out Loud)

```
YOU ASK:                                 INTERVIEWER SAYS:
────────────────────────────────────────────────────────────────────
"Can users upload any file type?"      → "Yes — any file, up to quota"
"Max file size?"                       → "Up to 10-15 GB"
"Auto-sync across all linked devices?" → "Yes — all devices sync"
"Real-time collaborative editing?"     → "Out of scope — that's Docs"
"File versioning needed?"              → "Yes — rollback to old versions"
"Sharing with permissions?"            → "Yes — view/comment/edit"
"Storage quota per user?"              → "Yes — 15 GB free"
"How many users?"                      → "500M registered, 100M DAU"
────────────────────────────────────────────────────────────────────
```

*"Let me summarize what this means for the design..."*

```
┌──────────────────────────────────────────────────────────────────┐
│                  REQUIREMENTS SUMMARY                             │
├──────────────────────────────────────────────────────────────────┤
│  FUNCTIONAL:                                                      │
│  Upload/download any file (up to 15 GB)                          │
│  Auto-sync changes to all linked devices                         │
│  Share files/folders with view/comment/edit permissions          │
│  Folder hierarchy (create, rename, delete, move)                 │
│  File versioning and rollback                                     │
│  Storage quota per user                                          │
│  [Out of scope]: Real-time collaborative editing                  │
├──────────────────────────────────────────────────────────────────┤
│  NON-FUNCTIONAL:                                                  │
│  Scale:     500M users, billions of files                        │
│  CAP:       HIGH AVAILABILITY                                     │
│             Eventual consistency for sync (seconds lag OK)        │
│             Strong consistency for quota (no over-quota uploads)  │
│  Durability: ZERO data loss once committed                        │
│  Latency:   Sync lag < 5 seconds after commit                    │
└──────────────────────────────────────────────────────────────────┘
```

*"One critical insight: files can be 15 GB. This means we CANNOT
use a simple POST /upload. We need a chunked upload protocol.
This is the most unique part of this design."*

---

## STEP 2 — Capacity Estimation (Speak This Out Loud)

```
STORAGE:
──────────────────────────────────────────────────────────────────
"500M users × avg 1,000 files × 500 KB avg = 250 PB total.
 This immediately tells us: MUST use blob storage (S3).
 Not a database. No DB can store 250 PB of binary blobs cheaply."

METADATA:
──────────────────────────────────────────────────────────────────
"500B files × ~1 KB metadata each = 500 TB of metadata.
 Sharded MySQL can handle this. ~5 TB per shard with 100 shards."

SYNC EVENTS:
──────────────────────────────────────────────────────────────────
"100M DAU × 5 file changes/day = 500M sync events/day
 = ~5,800 sync events/sec.
 Too high for polling. Needs event-driven sync (Kafka)."

UPLOAD THROUGHPUT:
──────────────────────────────────────────────────────────────────
"10M new files/day × avg 1 MB = 10 TB/day ingested.
 But files can be 15 GB → 1 large upload per user can saturate
 a naive backend. Solution: presigned URLs to S3 directly."
```

---

## STEP 3 — Core Entities

```
┌──────────────────────────────────────────────────────────────────┐
│                       CORE ENTITIES                               │
├──────────────────┬───────────────────────────────────────────────┤
│ Entity           │ What it holds                                 │
├──────────────────┼───────────────────────────────────────────────┤
│ User             │ userId, email, quotaUsed, quotaLimit          │
│ File             │ fileId, name, ownerId, parentFolderId, status  │
│ Folder           │ folderId, name, ownerId, parentFolderId       │
│ FileVersion      │ versionId, fileId, checksum, s3Path, size     │
│ Chunk            │ chunkId, fileId, chunkIndex, hash, s3Key      │
│ Permission       │ fileId/folderId, userId, role (VIEW/EDIT)     │
└──────────────────┴───────────────────────────────────────────────┘

KEY INSIGHT: "A folder is NOT a real directory. It is just a metadata
record with type=FOLDER. Creating a folder = inserting one row in MySQL.
Deleting a folder = soft-deleting that row and all child rows.
No actual directory structure in S3."
```

---

## STEP 4 — API Design (Speak This Out Loud)

*"For Google Drive, API design is more important than usual.
The upload flow is NOT a simple POST — it is a 5-step protocol."*

### Folder APIs

```
┌────────────┬──────────────────────────────────────────────────────┐
│ POST       │ /api/v1/folders                                      │
│            │ { name, parentFolderId }  → creates folder (1 DB row)│
├────────────┼──────────────────────────────────────────────────────┤
│ GET        │ /api/v1/folders/{id}/contents                        │
│            │ → returns list of files + subfolders inside          │
├────────────┼──────────────────────────────────────────────────────┤
│ PATCH      │ /api/v1/folders/{id}  → rename / move               │
├────────────┼──────────────────────────────────────────────────────┤
│ DELETE     │ /api/v1/folders/{id}  → soft-delete + all children   │
└────────────┴──────────────────────────────────────────────────────┘
```

### File Upload — 5-Step Protocol

*"This is the key design question. Walk through each step."*

```
STEP 1 — INIT (client tells server it wants to upload)
──────────────────────────────────────────────────────
POST /api/v1/files/upload/init
{ "fileName": "design.pdf", "fileSizeBytes": 52428800,
  "parentFolderId": "folder-123", "fileHash": "sha256:abc..." }

Server:
  1. Validate JWT
  2. Check quota: quotaUsed + 50MB <= quotaLimit? (Redis Lua script)
  3. Reserve quota atomically in Redis
  4. Generate fileId + uploadId
  5. Init Redis key: upload:{uploadId} → { fileId, chunkMap: {} }

Response:
{ "fileId": "file-uuid", "uploadId": "up-uuid",
  "chunkSize": 5242880,       ← 5 MB
  "existingChunks": []        ← for resumable: already uploaded chunks
}

STEP 2 — CLIENT CHUNKS THE FILE (client-side only, no server call)
──────────────────────────────────────────────────────────────────
Client splits 50 MB file into 10 chunks × 5 MB.
Client computes SHA-256 hash for each chunk locally.
Client checks existingChunks[] → skips already-uploaded chunks.

STEP 3 — GET SIGNED URL (one call per chunk)
──────────────────────────────────────────────────────────────────
POST /api/v1/files/upload/chunk-url
{ "uploadId": "up-uuid", "chunkIndex": 0, "chunkHash": "sha256:xyz" }

Server:
  1. Stores chunkHash in Redis: upload:{uploadId}.chunkMap[0] = "xyz"
  2. Generates presigned S3 URL (TTL: 5 min)

Response: { "presignedUrl": "https://s3.amazonaws.com/...?sig=..." }

STEP 4 — CLIENT UPLOADS CHUNK DIRECTLY TO S3
──────────────────────────────────────────────────────────────────
PUT {presignedUrl}  (client browser/app → S3 directly)
← Our backend NEVER sees file bytes. Only metadata flows through us.
200 OK from S3.

(Repeat Steps 3+4 for all 10 chunks, 3 in parallel)

STEP 5 — COMMIT (upload complete)
──────────────────────────────────────────────────────────────────
POST /api/v1/files/upload/commit
{ "uploadId": "up-uuid", "fileId": "file-uuid" }

Server:
  1. Validator Service: re-hashes each chunk in S3, compares to
     Redis chunkMap → confirms no corruption
  2. If valid: write metadata to MySQL (file, version, chunks)
  3. Publish Kafka event: { fileId, ownerId, action: CREATED }
  4. Return 202 Accepted (validation is async)

Client polls: GET /api/v1/files/{fileId}/status
  → PROCESSING | ACTIVE | CORRUPTED | FAILED
```

### Download + Share APIs

```
GET  /api/v1/files/{id}/download    → returns presigned S3 URL
POST /api/v1/files/{id}/share       → { userId, role: VIEW|COMMENT|EDIT }
GET  /api/v1/files/{id}/versions    → list all versions
POST /api/v1/sync/pull?since={ts}   → returns { changed[], deleted[] }
```

---

### JSON Request / Response Examples

```json
// POST /api/v1/files/upload/init
// Request:
{
  "fileName": "quarterly_report.pdf",
  "fileSize": 52428800,
  "mimeType": "application/pdf",
  "chunkSize": 5242880,
  "chunkHashes": ["sha256_chunk0", "sha256_chunk1", "sha256_chunk9"]
}
// Response 200 OK:
{
  "uploadId": "upload_abc123",
  "fileId": "file_xyz789",
  "chunks": [
    { "chunkIndex": 0, "uploadUrl": "https://s3.amazonaws.com/.../chunk0?X-Amz-Signature=...", "expiresIn": 3600 },
    { "chunkIndex": 1, "uploadUrl": "https://s3.amazonaws.com/.../chunk1?X-Amz-Signature=...", "expiresIn": 3600 }
  ]
}

// POST /api/v1/files/upload/commit
// Request:
{
  "uploadId": "upload_abc123",
  "chunkETags": ["etag_chunk0", "etag_chunk1"]
}
// Response 200 OK:
{
  "fileId": "file_xyz789",
  "name": "quarterly_report.pdf",
  "version": 1,
  "size": 52428800,
  "status": "PROCESSING",
  "createdAt": "2025-01-21T10:00:00Z"
}

// GET /api/v1/files/{id}/download
// Response 200 OK:
{
  "fileId": "file_xyz789",
  "downloadUrl": "https://cdn.googledrive.com/file_xyz789?X-Amz-Signature=...",
  "expiresIn": 300
}

// POST /api/v1/files/{id}/share
// Request:
{ "userId": "user_bob", "role": "EDIT" }
// Response 200 OK:
{ "shareId": "share_abc", "fileId": "file_xyz789", "sharedWith": "user_bob", "role": "EDIT" }
```

---

## STEP 5 — High-Level Architecture (Draw on Whiteboard)

> **► DRAW THIS on the whiteboard ◄**
> Draw the CLIENT box at top with 3 sub-components (Watcher, Chunker, Sync Engine).
> Draw API Gateway → File Upload Service + Metadata Service.
> Draw S3 on the right. Draw Kafka at bottom → Sync Service.
> Show the TWO flows: upload (left to right) and sync (bottom to devices).

```
                ╔═══════════════════════════════════════════╗
                ║        GOOGLE DRIVE ARCHITECTURE           ║
                ╚═══════════════════════════════════════════╝

┌───────────────────────────────────────────────────────────────┐
│             CLIENT APP (Desktop / Mobile)                      │
│  ┌──────────────┐  ┌─────────────────┐  ┌──────────────────┐ │
│  │ File Watcher │  │ Upload Manager  │  │  Sync Engine     │ │
│  │ (inotify /   │→ │ • Calls INIT    │  │  • Push: receives│ │
│  │  FSEvents)   │  │ • Gets sign URLs│  │    Kafka notifs  │ │
│  │ Detects file │  │ • Uploads chunks│  │  • Pull: polls   │ │
│  │ changes      │  │ • Sends COMMIT  │  │    on reconnect  │ │
│  └──────────────┘  └────────┬────────┘  └──────────────────┘ │
│                             │                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Chunker: splits file → 5 MB chunks                     │ │
│  │  Local Metadata Index (SQLite): SHA-256 per chunk stored │ │
│  │  → enables delta sync (re-upload only changed chunks)   │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬────────────────────────────────┘
                               │ HTTPS
                               ▼
                  ┌────────────────────────────┐
                  │   API GATEWAY              │
                  │   Auth, Rate Limit, Route  │
                  └──────────┬─────────────────┘
                             │
              ┌──────────────┴──────────────────┐
              │                                 │
              ▼                                 ▼
  ┌────────────────────────┐    ┌──────────────────────────────┐
  │  FILE UPLOAD SERVICE   │    │  FILE METADATA SERVICE       │
  │                        │    │                              │
  │  • Init upload session │    │  • Folder CRUD               │
  │  • Issue presigned URLs│    │  • File metadata CRUD        │
  │  • Store chunk state   │    │  • Permission checks         │
  │    in Redis            │    │  • Version management        │
  │  • Receive commit      │    └──────────────┬───────────────┘
  │  • Trigger validator   │                   │
  └──────────┬─────────────┘                   ▼
             │                    ┌──────────────────────────┐
             │ on valid           │  Metadata DB (MySQL)      │
             ▼                    │  • folders                │
  ┌────────────────────┐          │  • files                  │
  │  VALIDATOR SERVICE │          │  • file_versions          │
  │                    │          │  • permissions            │
  │  Re-hash chunks    │          └──────────────────────────┘
  │  Compare vs Redis  │
  │  chunkMap          │     ┌────────────────────────────────┐
  └──────────┬─────────┘     │   Cassandra                    │
             │               │   • chunks table               │
             │   S3 upload   │   (chunkId → s3Key, hash)      │
             ▼   (direct)    │   High write volume, no joins  │
  ┌────────────────────────┐ └────────────────────────────────┘
  │  S3 BLOB STORAGE       │
  │  vid-bucket/           │ ┌────────────────────────────────┐
  │  {fileId}/{chunkId}    │ │  Redis                         │
  └────────────────────────┘ │  • upload:{uploadId} sessions  │
                             │  • quota:{userId} reservation  │
             │               │  • permission:{fileId} cache   │
             ▼               └────────────────────────────────┘
  ┌────────────────────────┐
  │    KAFKA BROKER        │
  │  topic: file-events    │
  └──────────┬─────────────┘
             │
             ▼
  ┌────────────────────────────────────────────────────┐
  │   SYNC SERVICE                                      │
  │   • Reads event: { fileId, ownerId, action }        │
  │   • Fetches all devices linked to ownerId from DB   │
  │   • Sends push notification to each device:         │
  │     "File X changed — download version Y"          │
  │   • Handles pull requests from offline-returning    │
  │     devices: GET /sync/pull?since={timestamp}       │
  └────────────────────────────────────────────────────┘
```

---

> **► DRAW THIS on the whiteboard ◄**

## SEQUENCE DIAGRAM — CHUNKED FILE UPLOAD

```
  Client App   Upload Service     S3           Kafka      Validator
     │               │              │             │            │
     │ POST /upload  │              │             │            │
     │ INIT {name,   │              │             │            │
     │  size, hash[]}│              │             │            │
     │──────────────▶│              │             │            │
     │               │ Reserve quota (Redis Lua atomic)        │
     │               │ INSERT file + version record            │
     │               │ Presign S3 URL for each chunk           │
     │               │─────────────▶│             │            │
     │               │◀─────────────│             │            │
     │ {uploadId,    │  [presignedUrls[], uploadId]            │
     │  chunkUrls[]} │              │             │            │
     │◀──────────────│              │             │            │
     │               │              │             │            │
     │ PUT chunkUrl0 │              │             │            │
     │──────────────────────────────▶             │            │
     │◀──────────────────────────────             │            │
     │  [200 ETag]   │              │             │            │
     │               │              │             │            │
     │ PUT chunkUrl1..N (parallel)  │             │            │
     │──────────────────────────────▶             │            │
     │◀──────────────────────────────             │            │
     │               │              │             │            │
     │ POST /upload/commit          │             │            │
     │ {uploadId,    │              │             │            │
     │  chunkETags[]}│              │             │            │
     │──────────────▶│              │             │            │
     │               │ Update file_versions status=COMMITTED   │
     │               │ Publish upload.completed    │            │
     │               │──────────────────────────────────────────▶
     │ {fileId,      │              │             │            │
     │  version:1}   │              │             │            │
     │◀──────────────│              │             │            │
     │               │              │             │  Validator │
     │               │              │◀────────────│  consumes  │
     │               │              │  verify     │            │
     │               │              │  SHA-256    │            │
     │               │              │  per chunk  │            │
```

---

## STEP 6 — Database Schema Design (Draw on Whiteboard)

> **► DRAW THIS on the whiteboard ◄**
> Draw 4 boxes: files table (MySQL), file_versions table, permissions table, chunks (Cassandra).
> Show FK relationships. Show the partition key for Cassandra chunks.

```
files table (MySQL)
┌──────────────────┬──────────────────────────────────────────┐
│ file_id          │ UUID (PK)                                │
│ name             │ VARCHAR(255) NOT NULL                    │
│ owner_id         │ UUID (FK → users)                        │
│ parent_folder_id │ UUID (FK → folders, nullable)            │
│ status           │ ENUM(PROCESSING, ACTIVE, DELETED)        │
│ checksum         │ VARCHAR(64)  ← full-file SHA-256 hash    │
│ created_at       │ TIMESTAMP                                │
│ updated_at       │ TIMESTAMP                                │
└──────────────────┴──────────────────────────────────────────┘
CREATE INDEX idx_files_owner ON files(owner_id);
CREATE INDEX idx_files_folder ON files(parent_folder_id);
CREATE INDEX idx_files_checksum ON files(checksum);  ← dedup

file_versions table (MySQL)
┌──────────────────┬──────────────────────────────────────────┐
│ version_id       │ UUID (PK)                                │
│ file_id          │ UUID (FK → files)                        │
│ version_number   │ INT NOT NULL                             │
│ size_bytes       │ BIGINT                                   │
│ s3_path          │ VARCHAR(500)                             │
│ checksum         │ VARCHAR(64)                              │
│ created_by       │ UUID (FK → users)                        │
│ created_at       │ TIMESTAMP                                │
└──────────────────┴──────────────────────────────────────────┘

permissions table (MySQL)
┌──────────────────┬──────────────────────────────────────────┐
│ permission_id    │ UUID (PK)                                │
│ resource_id      │ UUID (file_id OR folder_id)              │
│ resource_type    │ ENUM(FILE, FOLDER)                       │
│ user_id          │ UUID (FK → users)                        │
│ role             │ ENUM(VIEW, COMMENT, EDIT)                │
│ created_at       │ TIMESTAMP                                │
└──────────────────┴──────────────────────────────────────────┘

chunks table (Cassandra — NOT MySQL)
┌──────────────────┬──────────────────────────────────────────┐
│ file_id          │ UUID (partition key)                     │
│ version_id       │ UUID (clustering key)                    │
│ chunk_index      │ INT (clustering key)                     │
│ chunk_hash       │ TEXT                                     │
│ s3_key           │ TEXT                                     │
│ size_bytes       │ INT                                      │
└──────────────────┴──────────────────────────────────────────┘
WHY Cassandra here: Pure lookup by (file_id, version_id, chunk_index).
No joins needed. High write volume during chunk commit. Perfect fit.
```

---

> **► DRAW THIS on the whiteboard ◄**

## ER RELATIONSHIP DIAGRAM

```
┌────────────────────────────────────────────────────────────────────┐
│                GOOGLE DRIVE — ENTITY RELATIONSHIP                   │
└────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────────────────────────┐
│    users     │     │             files                  │
│    (MySQL)   │     │            (MySQL)                 │
├──────────────┤     ├──────────────────────────────────┤
│ PK user_id   │─────│ PK file_id UUID                  │
│    email TEXT│ 1 N │ FK owner_id UUID → users         │
│    quota_used│     │    name VARCHAR                  │
│    plan ENUM │     │    size_bytes BIGINT             │
└──────────────┘     │    mime_type VARCHAR             │
                     │    current_version INT           │
                     │    is_deleted BOOL               │
                     │    created_at TIMESTAMP          │
                     │    updated_at TIMESTAMP          │
                     └──────────────┬───────────────────┘
                                    │ 1
                                    │ N
               ┌────────────────────▼──────────────────┐
               │              file_versions              │
               │               (MySQL)                  │
               ├───────────────────────────────────────┤
               │ PK version_id INT                     │
               │ FK file_id UUID                       │
               │    s3_key VARCHAR (storage path)      │
               │    size_bytes BIGINT                  │
               │    checksum_sha256 VARCHAR            │
               │    created_by UUID                    │
               │    created_at TIMESTAMP               │
               └──────────────────────────────────────-┘

               ┌───────────────────────────────────────┐
               │          file_chunks (Cassandra)       │
               ├───────────────────────────────────────┤
               │ PK file_id UUID   (PARTITION KEY)     │
               │    chunk_index INT (CLUSTERING KEY)   │
               │    chunk_hash VARCHAR (SHA-256)       │
               │    s3_key VARCHAR                     │
               │    size_bytes INT                     │
               │    upload_status ENUM                 │
               └───────────────────────────────────────┘

               ┌───────────────────────────────────────┐
               │         file_shares (MySQL)            │
               ├───────────────────────────────────────┤
               │ PK share_id UUID                      │
               │ FK file_id UUID                       │
               │ FK shared_with UUID → users           │
               │    permission ENUM(VIEW,EDIT,COMMENT) │
               │    created_at TIMESTAMP               │
               └───────────────────────────────────────┘
```

---

## STEP 7 — Sync Deep Dive

*"Let me walk through how sync works across all three scenarios..."*

```
SCENARIO 1: DEVICE ONLINE (push sync)
─────────────────────────────────────────────────────────────────
Device A commits upload → Validator confirms
→ MySQL metadata saved → Kafka: { fileId, ownerId, version: 2 }
→ Sync Service reads event
→ Fetches devices for ownerId: [deviceB, deviceC]
→ Push notification to deviceB + deviceC:
  "file-123 updated to version 2 — download latest"
→ Each device's Sync Engine calls:
  GET /files/file-123/versions/2/download → presigned S3 URL
→ Device downloads, updates Local Metadata Index

SCENARIO 2: DEVICE COMES BACK ONLINE (pull sync)
─────────────────────────────────────────────────────────────────
DeviceB was offline for 3 hours. Reconnects.
Sync Engine calls:
  POST /sync/pull { "deviceId": "...", "lastSyncAt": 1721500000 }

Server checks Metadata DB:
  SELECT * FROM file_events
  WHERE owner_id = ? AND created_at > 1721500000

Returns: { changed: ["file-123", "file-456"], deleted: ["file-789"] }
Device downloads only those 3 files.

SCENARIO 3: LARGE FILE EDIT (delta sync — the smart part)
─────────────────────────────────────────────────────────────────
User edits a 100 MB document — changes only 1 paragraph.

WITHOUT delta sync: re-upload 100 MB (terrible)
WITH delta sync:
1. Chunker re-hashes all 20 chunks of the modified file
2. Compares each hash to Local Metadata Index:
   Chunks 0-11: hash unchanged → SKIP (not re-uploaded)
   Chunk 12:    hash changed   → UPLOAD only this 5 MB chunk
   Chunks 13-19: hash unchanged → SKIP
3. INIT: server returns existingChunks = [0,1,2,...,11,13,...,19]
4. Only chunk 12 is uploaded → 5 MB instead of 100 MB!

KEY: Local Metadata Index (SQLite) makes delta sync possible.
```

---

## STEP 8 — Scalability

```
BOTTLENECK 1: STORAGE COST (250 PB)
─────────────────────────────────────────────────────────────────
S3 lifecycle: Standard → IA (90 days) → Glacier (1 year)
Cross-user deduplication: if 1000 users upload same file,
only 1 S3 object stored. All 1000 metadata records → same s3_key.
Result: effective storage can be 30-50% less than raw file count.

BOTTLENECK 2: SYNC FAN-OUT (user with 50 linked devices)
─────────────────────────────────────────────────────────────────
Power user has 50 devices. Each upload → 50 push notifications.
100M DAU × 5 changes/day × avg 3 devices = 1.5B notifications/day.
Sync Service is horizontally scalable (stateless, Kafka consumer).
50 notifications per upload = trivial per-event cost.
Scale Sync Service instances to match Kafka consumer lag.

BOTTLENECK 3: METADATA DB SHARDING
─────────────────────────────────────────────────────────────────
500B files × 1KB = 500 TB metadata.
Shard MySQL by owner_id (user ID).
All a user's files are on the same shard → no cross-shard joins.
100 shards × 5 TB = manageable.
Read replicas per shard for read-heavy workloads.
```

---

## STEP 8 — TRADE-OFFS

*"Let me walk through the key architectural trade-offs I made and why."*

```
┌─────────────────────────────┬────────────────────────────┬──────────────────────────────────────────────────────────┐
│ DECISION                    │ CHOICE MADE                │ TRADE-OFF                                                │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Upload protocol             │ Chunked upload (5MB chunks)│ Resumable on network failure, parallel chunks vs.        │
│                             │                            │ complexity (client must track chunk state)               │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Chunk size                  │ 5MB default                │ Balances retry cost (re-upload only 5MB on failure) vs.  │
│                             │                            │ too many chunks for large files increases S3 PUT count   │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Deduplication               │ SHA-256 per chunk          │ Same 5MB chunk stored once across users, massive savings │
│                             │                            │ vs. SHA-256 compute overhead on every upload             │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Metadata storage            │ MySQL (not Cassandra)      │ ACID for ownership, sharing permissions, quota + JOINs   │
│                             │                            │ (user → files → shares) vs. requires sharding for 1B+   │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Chunk storage               │ Cassandra (file_id +       │ Fast partition scan for "all chunks of file X" vs.       │
│                             │ chunk_index)               │ doesn't need full ACID — chunk write is idempotent       │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Sync protocol               │ Push (inotify/FSEvents) +  │ Near-real-time sync vs. missed events while offline      │
│                             │ Pull on reconnect          │ require full reconciliation on reconnect                 │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Conflict resolution         │ Last Writer Wins + conflict│ Simple, no user prompt needed vs. silent data loss if    │
│                             │ copy                       │ two users edit simultaneously — conflict copy preserves  │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Quota enforcement           │ Redis Lua atomic           │ No over-quota race condition vs. Redis crash loses       │
│                             │ check-and-reserve          │ reservation (auto-heal on next request)                  │
└─────────────────────────────┴────────────────────────────┴──────────────────────────────────────────────────────────┘
```

*"The most critical trade-off is MySQL vs. Cassandra for metadata. At first glance, 1B files seems like Cassandra territory. But Drive's access patterns are: 'get all files owned by user X' (one query), 'get all users sharing file Y' (JOIN), 'check if user has quota space' (ACID UPDATE). These are relational patterns. We shard MySQL by user_id and accept the complexity — Cassandra would lose the JOIN and ACID guarantees we actually need for correctness."*

---

## WHAT NOT TO SAY ✗

```
✗ "I'll route the file upload through my backend server"
  → 100M DAU × 10 MB = 1 TB/sec through your servers. Impossible.
    Use presigned URLs: client uploads directly to S3.

✗ "Just upload in one HTTP POST request"
  → 15 GB files timeout at LB (30-120s). Network drop = restart.
    No progress indicator. Must use chunked upload protocol.

✗ "A folder is a real directory in S3"
  → S3 has no directories. A folder = just a row in MySQL.
    parent_folder_id column creates the hierarchy. No S3 mkdir.

✗ "Use Cassandra for all metadata because it scales"
  → File metadata needs JOINs: files + permissions + versions.
    Cassandra has no joins. Use MySQL for metadata.
    Cassandra IS correct for the chunks table (no joins, high writes).

✗ "I'll poll for sync every 5 seconds"
  → 100M devices × every 5s = 20M requests/sec just for polling.
    Use OS file watchers (inotify/FSEvents) + Kafka push.
    Polling is a last resort fallback, not the primary sync.

✗ "On network failure, restart the upload from zero"
  → This is why chunked upload exists. Server stores which chunks
    are done (Redis). Client checks existingChunks on re-INIT.
    Resumes from the first failed chunk.
```

---

## SENIOR TRAP QUESTIONS (15 YOE Level)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 1 — RACE CONDITIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "User has 10 MB quota left. Uploads two 8 MB files simultaneously.
   Both pass the quota check. Total = 16 MB. How do you prevent this?"

A: This is a classic check-then-act race condition.
   Fix: Redis atomic reservation with a Lua script.
   On INIT (before any upload starts):
     EVAL (runs atomically on Redis server):
       current = GET quota:{userId}
       if current + fileSize > quotaLimit: return -1 (deny)
       SET quota:{userId} (current + fileSize)
       return 1 (approved)
   Lua script is a single atomic Redis operation — no race possible.
   If upload fails later: DECRBY quota:{userId} fileSize (release).
   If commit succeeds: quota reservation already applied — persist
   to MySQL: UPDATE users SET quota_used = quota_used + fileSize.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "What happens if the Validator Service crashes after all chunks
   are uploaded but before metadata is written to MySQL?"

A: Idempotent retry. All the data is still intact:
   - Chunks: in S3 (not deleted yet)
   - Chunk hashes: in Redis with TTL=24h (not expired)
   The Validator Service can re-run validation from scratch:
   Re-read all hashes from Redis, re-hash chunks in S3, compare.
   Same result every time (idempotent).
   Fix: Kafka retries the commit event. DLQ after 5 retries.
   Client polls GET /files/{id}/status → still shows PROCESSING.
   If corrupt chunk found: notify client with { badChunks: [7, 12] }
   → Client re-uploads only those chunks, re-commits.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 2 — FAILURE MODES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "User is in Mumbai. S3 bucket is in us-east-1. How do you
   make their 10 GB upload fast?"

A: Two options:
   Option A: S3 Transfer Acceleration.
   AWS routes the upload via CloudFront edge (Mumbai PoP)
   → AWS private backbone → us-east-1 S3.
   AWS backbone is much faster than public internet.
   Cost: ~2× more per GB. Recommended for large files.
   Option B: Regional S3 buckets.
   INIT response includes { uploadRegion: "ap-south-1" }.
   Presigned URL points to ap-south-1 bucket (~10ms latency).
   S3 Cross-Region Replication copies to primary bucket.
   Metadata written after replication completes.
   Server picks region from user's IP geolocation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "Two devices edit the same file offline. Both sync when reconnected.
   How do you handle the conflict?"

A: Conflict detection via version number + last-write-wins (default).
   Each FileVersion has: { versionNumber, deviceId, modifiedAt }.
   When Device B syncs:
   1. Server checks: is the base version Device B edited still latest?
   2. If no conflict (Device A synced, Device B based on same version):
      → merge or overwrite, increment version.
   3. If conflict (both A and B modified the same base version):
      → Create two conflict copies:
        "report.pdf" (Device A's version)
        "report (conflicted copy from Device B 2024-01-15).pdf"
      → Notify user: "Conflict found. Please resolve."
   This is exactly how Google Drive and Dropbox handle conflicts.
   "Conflict copies" are the safest UX — never silently lose data.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 3 — DESIGN DECISIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "How do folder permissions cascade to child files?"

A: Permission check walks up the parent chain at query time.
   "Can userId X read file F?"
   1. Check permissions table for { resource_id: F, user_id: X }
   2. If not found: check F's parent folder G
   3. If not found: check G's parent folder H
   4. Continue until root or explicit permission found
   Optimization: cache permission check in Redis (TTL: 5 min).
   Cache key: perm:{userId}:{fileId} → { allowed: true/false }.
   Invalidate all child-resource cache on any permission change
   to parent (use wildcard DEL or event-based invalidation).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

QUICK SUMMARY — The 4 things that show 15 YOE thinking:
  1. Failure modes: "Validator crashes" — idempotent retry from S3+Redis
  2. Race conditions: quota check — Redis Lua atomic reservation
  3. WHY decisions: MySQL vs Cassandra (joins vs no-joins)
  4. Client architecture: delta sync, local metadata index, file watcher
     (many candidates forget the CLIENT is half the system)
```

---

## KEY NUMBERS — Memorize These

```
┌──────────────────────────────────┬──────────────────────────┐
│              METRIC              │  VALUE                   │
├──────────────────────────────────┼──────────────────────────┤
│ Registered users                 │ 500 million              │
│ Daily Active Users               │ 100 million              │
│ Total files                      │ 500 billion              │
│ Average file size                │ 500 KB                   │
│ Total storage                    │ 250 PB                   │
│ Max single file size             │ 10-15 GB                 │
│ Chunk size                       │ 5 MB                     │
│ Free storage quota               │ 15 GB                    │
│ Daily sync events                │ 500 million              │
│ Sync events per second           │ ~5,800                   │
│ Upload session TTL (Redis)       │ 24 hours                 │
│ Presigned URL TTL                │ 5 minutes                │
│ Permission cache TTL (Redis)     │ 5 minutes                │
│ Sync push latency target         │ < 5 seconds              │
└──────────────────────────────────┴──────────────────────────┘
```

---

*Study order: STEP 5 Architecture (15 min) → STEP 4 Upload Protocol (15 min)
→ STEP 7 Sync Deep Dive (10 min) → STEP 2 Capacity (5 min) → Rapid Answer (5 min)*
