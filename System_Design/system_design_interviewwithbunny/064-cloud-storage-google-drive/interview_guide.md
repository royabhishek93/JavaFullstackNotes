# Cloud Storage Platform — Interview Guide
### (Google Drive / Dropbox)

> **One-liner to open with:**
> "Initiate upload → chunk & hash → pre-signed URLs → parallel chunk upload → commit → metadata versioning → sync events to other devices (eventual)"

---

## 1. Functional Requirements

| Feature | Detail |
|---|---|
| Upload / Download | Large files; multi-part supported |
| Resumable Uploads | Resume after network disconnect |
| Folder Operations | Create, delete, rename, organise folders |
| Sharing | Share files/folders with per-user permissions |
| Version History | Restore older file versions |
| Cross-Device Sync | Changes propagate to all devices automatically |
| Quota | Storage limit enforced per user |

---

## 2. Non-Functional Requirements

| Dimension | Target |
|---|---|
| Scale | Millions of users; billions of files; multi-region |
| Durability | No data loss — multi-AZ / replication for blobs |
| Metadata Consistency | **Strong** consistency (file/folder metadata) |
| Sync Consistency | **Eventual** consistency is acceptable |
| Availability > Consistency | CAP theorem: availability wins for sync |
| Latency | Upload latency should be minimal |
| Security | Encrypted at rest and in transit |

---

## 3. Core Entities

```
User
  └── userId, emailId, password, createdDate, metadata

Folder
  └── folder_id, parent_folder_id (NULL = root), owner_id, created_at, metadata

File
  └── file_id, parent_folder_id, owner_id, name, size_bytes,
      current_version_id, created_at, is_deleted, metadata

FileVersions
  └── version_id, file_id, size_bytes, created_at

FileVersionChunks  (join table)
  └── version_id, chunk_index, chunk_id

Chunks
  └── chunk_id, object_key (s3://bucket/path), size_bytes,
      checksum (content hash), created_at

Permissions
  └── permission_id, resource_type (file|folder), resource_id,
      userId, role, created_at, metadata
```

> **Interview tip:** The `Chunks` table is the dedup key — two files sharing the same chunk_id point to the **same blob** in S3. No data duplication.

```
WHY ACCESS CONTROL / PERMISSIONS EXISTS? (Beginner Explanation)
  The Permissions table is the bouncer's list at a nightclub — every API
  request checks "is this userId on the list for this resource, and what
  are they allowed to do?" A role of "viewer" means read-only (no write,
  no delete). "Editor" means read + write. "Owner" means everything.
  When you share a folder with a colleague, a row is inserted into
  Permissions with their userId, the folder's resource_id, and the granted
  role. Every call to read or modify that resource does a permission lookup
  first. Without this table, you'd have to copy the file for every person —
  wasteful, and impossible to revoke access cleanly later.
```

---

## 4. API Design

### Folder Operations
```
POST   /api/v1/folders                        — create folder
GET    /api/v1/folders/{folderId}             — get folder info
GET    /api/v1/folders/{folderId}/contents    — list contents
... other CRUD
```

### File Upload Operations
```
POST   /api/v1/files/upload/init              — initialise upload session
POST   /api/v1/files/uploadId/chunks          — upload chunk
POST   /api/v1/files/uploadId/chunk-url       — get pre-signed URL for chunk N
POST   /api/v1/files/uploadId/commit          — confirm/finalise upload
GET    /api/v1/files/{fileId}/download        — download file
PUT/DEL /api/v1/files/{fileId}               — update / delete
... other CRUD
```

### Sharing
```
POST   /api/v1/files/{fileId}/share           — share file with a user (body: userId, role)
POST   /api/v1/folders/{folderId}/share       — share folder with a user (body: userId, role)
DELETE /api/v1/files/{fileId}/share/{userId}  — revoke file access for a user
DELETE /api/v1/folders/{folderId}/share/{userId} — revoke folder access for a user
```

> **WHY SHARE ENDPOINTS?** Sharing is a core functional requirement. A dedicated endpoint keeps permission management explicit — the body carries `userId` and `role` (viewer/editor/owner), which maps directly to an INSERT into the `Permissions` table. Separate DELETE endpoints are needed so revocation is a first-class operation; without them you'd have to expose the full permission record and PATCH it, which is awkward and error-prone.

### Version History
```
GET    /api/v1/files/{fileId}/versions                          — list all versions of a file
POST   /api/v1/files/{fileId}/versions/{versionId}/restore     — restore a previous version as current
```

> **WHY VERSION HISTORY ENDPOINTS?** Version History is a listed functional requirement. `GET /versions` lets the UI display a timeline of past saves — it queries `FileVersions` by `file_id` ordered by `created_at`. `POST /restore` is interview-critical: it shows you understand that restore is NOT a data copy operation — it simply updates `current_version_id` on the `File` row to point back to the target `version_id`. This is O(1) metadata write regardless of file size.

### Search
```
GET    /api/v1/files/search?q={query}&folderId={id}&type={ext} — search files by name/content
```

> **WHY SEARCH?** Google Drive and Dropbox both expose search as a first-class API. In an interview, this endpoint signals awareness that MetaDB needs a full-text index (e.g., PostgreSQL `tsvector` on file name, or an Elasticsearch sidecar) separate from the primary key lookups used by other endpoints. Optional query params (`folderId` to scope, `type` to filter by extension) show practical API design instincts.

---

## 5. Upload Flow — Two Scenarios

### Scenario 1: Brand-New File (First-time upload)

```
POST /api/v1/files/upload/init
Request:  { fileName: "vacation.mp4", fileSize: 524288000, parentFolderId: "root" }
Response: { fileId: "file_789", uploadId: "upload_123", chunkSize: 5MB, existingChunks: [] }
```

`existingChunks: []` → nothing on the server yet; client uploads all chunks.

### Scenario 2: Resume Upload (Connection dropped)

```
POST /api/v1/files/upload/init
Request:  { fileName: "vacation.mp4", fileSize: 524288000, resumeUploadId: "upload_123" }
Response: { fileId: "file_789", uploadId: "upload_123", chunkSize: 5MB, existingChunks: [1,2,3,4,5] }
```

`existingChunks: [1,2,3,4,5]` → client skips those and resumes from chunk 6.

---

## 6. High-Level Design (HLD)

```
Clients
   │
   └──► LB & API Gateway
              │
              ├──► User Onboarding Svc ──► User DB
              │
              ├──► File Uploader Svc   ──► Blob (S3)
              │
              └──► File Metadata Svc  ──► MetaDB
```

**Three core services behind the gateway:**
- **User Onboarding Svc** — registration, auth, quota
- **File Uploader Svc** — manages upload sessions, pre-signed URLs, commit
- **File Metadata Svc** — file/folder/version metadata (strong consistency)

---

## 7. Low-Level Design (LLD) — Deep Dive

### Client Components

| Component | Role |
|---|---|
| **Watcher** | Monitors local filesystem for changes |
| **Local Metadata Index** | Tracks local file state to compute deltas |
| **Chunker** | Splits file into fixed-size chunks; computes SHA-256 per chunk |

```
WHY CHUNKING EXISTS? (Beginner Explanation)
  Think of uploading a 1 GB video like moving furniture: you don't push
  the entire sofa through the door in one go — you disassemble it first.
  Chunking splits a big file into small blocks (e.g., 5 MB each). If your
  internet drops on chunk 7 of 200, you only re-upload chunk 7, not the
  whole file. You can also upload chunks 1, 2, 3 simultaneously on multiple
  connections — like three people carrying boxes at once (parallel upload).
  Deduplication also works chunk-by-chunk: identical blocks in different
  files only get stored once. Without chunking: a 500 MB upload that fails
  at 99% forces you to start completely over.
```

| **Upload Manager** | Manages parallel chunk uploads (3 at a time), retries |
| **Sync Engine** | Handles push/pull sync with server; resolves conflicts |

### Server Services

| Service | Role |
|---|---|
| **LB & API Gateway** | Rate limiting, auth, routing |
| **User Onboarding Svc** | Auth, quota management |
| **File Uploader Svc** | Upload init, pre-signed URL generation, commit + metadata write |
| **File Metadata Svc** | CRUD on File/Folder/Version/Permission; updates metadata after commit |

```
WHY A SEPARATE METADATA SERVICE? (Beginner Explanation)
  File data (the actual bytes) is huge but dumb — it doesn't know its own
  name. Metadata (file name, owner, version, folder path, permissions) is
  tiny but must be queryable, consistent, and searchable instantly. Mixing
  them is like storing your recipe book inside each ingredient jar — you'd
  have to open every jar just to see what's inside. Keeping metadata in a
  relational DB (fast queries, strong consistency) and raw bytes in S3
  (cheap, durable, bulk storage) gives you the best of both worlds: you
  can list a folder of 10,000 files in milliseconds without touching S3.
```

| **Read/Download Svc** | Generates signed S3 URLs for downloads; refresh/pull |

```
WHY CDN FOR FILE DOWNLOADS? (Beginner Explanation)
  S3 buckets live in one or a few regions (e.g., us-east-1 in Virginia).
  If you're in Tokyo downloading a file stored in Virginia, every byte
  travels across the Pacific — slow and expensive. A CDN (Content Delivery
  Network) is like a chain of convenience stores: the first Tokyo user gets
  the file from Virginia, but a cached copy lands at the Tokyo CDN node.
  The next thousand Tokyo users get it locally — fast, cheap, no ocean
  crossing. For frequently-accessed files this cuts latency by ~10x and
  slashes bandwidth costs. The Read/Download Svc issues short-lived signed
  URLs that can point to CDN edges instead of the origin S3 bucket.
```

| **Validator Svc** | Validates chunk hash, size, quota, malware scan (async) |
| **Deduplication Svc** | Checks if chunk already exists by content hash; reuses blob |
| **Sync Svc** | Fanout (push) or pull-based sync to all connected devices |

### Storage Layer

| Store | Purpose |
|---|---|
| **User DB** | User accounts (userId, emailId, password, createdDate) |
| **S3 (Blob)** | Raw chunk storage; object key = `s3://bucket/path` |

```
WHY OBJECT STORAGE (S3) INSTEAD OF A FILESYSTEM? (Beginner Explanation)
  A traditional filesystem is like a filing cabinet: folders inside folders,
  each file has a path. It works on one machine but doesn't scale across
  thousands of servers. Object storage (S3) is like a giant flat warehouse
  with a barcode scanner — every item gets a unique key (the barcode), and
  you retrieve it by key regardless of which physical shelf it's on. S3
  handles replication, durability (11 nines = 99.999999999%), and global
  access automatically. Trying to do that with a regular filesystem means
  you'd have to build the entire warehouse management system yourself.
```

| **MetaDB** | File, Folder, FileVersion, Chunk, Permissions tables |
| **Redis** | Upload session state: chunk bitmap, retry count, temp upload info |
| **Kafka** | Change event bus: File Uploader Svc publishes → Sync Svc consumes |

```
WHY KAFKA FOR SYNC EVENTS? (Beginner Explanation)
  Kafka is the order-ticket printer in a busy restaurant — the waiter
  (File Uploader Svc) drops the ticket and walks away immediately. The
  kitchen (Sync Svc) picks it up and processes it at its own pace. Without
  Kafka, the uploader would have to wait for every device to acknowledge
  the sync before finishing the upload — slow, brittle, and broken if any
  device is offline. Kafka decouples them: upload completes fast, sync
  events queue up durably, and each device's Sync Svc consumes them when
  ready. If a device was offline for an hour, it catches up on all missed
  events when it reconnects.
```

---

## 8. Upload Flow — Step-by-Step (LLD)

```
Step 1 — Initiate
  Client → POST /files/upload/init
  Body:   { fileName, fileSize, parentFolderId }
  Response: { fileId, uploadId, existingChunks }

Step 2 — Chunk & Hash (client-side)
  Chunker splits file into N chunks (e.g., 5 MB each)
  Computes SHA-256 per chunk → chunk hash array [0..9]

Step 3 — Get Pre-signed URL for each chunk
  Client → POST /upload/chunk-url
  Body:   { uploadId, chunkId, chunkHash }
  File Uploader Svc:
    ├── Validates uploadId + permission
    ├── Calls Deduplication Svc (is this hash already in S3?)
    └── Generates pre-signed PUT URL → { signedUrl: "https://s3...." }

Step 4 — Upload Chunks in Parallel (3 at a time)
  Client PUTs each chunk directly to S3 via pre-signed URL
  On reconnect: call init with resumeUploadId → server returns existingChunks

Step 5 — Commit
  Client → POST /uploads/{uploadId}/commit
  File Uploader Svc:
    └── Updates file metadata, creates FileVersion + FileVersionChunks records

Step 6 — Emit Sync Event
  File Uploader Svc → Kafka (change event)
  Sync Svc consumes event → pushes to all other connected devices (fanout)
```

---

## 9. Deduplication

```
WHY DEDUPLICATION EXISTS? (Beginner Explanation)
  Imagine a library that keeps one physical copy of "Harry Potter" on the
  shelf, and 10,000 readers each get a bookmark pointing to that same book.
  Dedup does this with file chunks — if two users upload the same 5 MB video
  intro, the system stores it once and both files point to that single blob.
  A content hash (SHA-256) is the fingerprint: same bytes = same hash = same
  blob, no upload needed. Without dedup, a company logo embedded in 50,000
  employee documents would be stored 50,000 times, wasting enormous space.
  The savings compound: identical OS backup chunks, duplicate attachments,
  copied folders — all collapse to a single stored copy.
```

- Dedup happens at **chunk level** using content hash (SHA-256).
- If `Deduplication Svc` finds an existing chunk with the same hash → return existing `object_key`; skip upload.
- Saves significant storage: a 20 MB file sharing most chunks with a 17 MB file stores only the delta.

```
File A: 20 MB  ──► 4 chunks reused + 1 new chunk
File B: 17 MB  ──► 4 chunks already in S3 (hash match)
                   Storage saved: ~17 MB
```

---

## 10. Sync Engine — Push vs Pull

```
WHY DELTA SYNC? (Beginner Explanation)
  When you fix a typo in a 50 MB Word document, you changed maybe 50 bytes
  out of 52 million. Delta sync is like mailing only the edited page, not
  reprinting and re-mailing the entire book. The client re-hashes all chunks
  after a local change — chunks whose hash hasn't changed are skipped. Only
  modified chunks get uploaded. For large files with small edits this can
  reduce upload size by 99%. The alternative — re-upload the whole file on
  every keystroke autosave — would eat your data plan and make sync unusably
  slow on large files.
```

```
HOW YOUR PHONE KNOWS A FILE CHANGED? (Beginner Explanation)
  Your phone can't just "wait" for a notification — HTTP is request/response,
  not the other way around. WebSocket is like leaving a phone line open: once
  connected, the server taps you on the shoulder the moment a change event
  arrives, no polling needed. SSE (Server-Sent Events) is similar but
  one-way: server pushes, client listens. Long-polling is the fallback: the
  client fires a request and the server holds it open until something happens,
  then responds immediately. When you're offline, the Sync Svc queues the
  events in Kafka; when you reconnect, your device catches up on everything
  it missed — no changes lost.
```

```
Sync Svc
  ├── Push (Fanout)
  │     Server pushes change events (via WebSocket / SSE) to all active devices
  │     Low latency; preferred for active sessions
  │
  └── Pull (Polling)
        Device polls for changes periodically
        Fallback for clients that missed push events (e.g., was offline)
```

**Conflict resolution:** For binary files → last-writer-wins is common. For text files → merge or flag conflict copy.

```
WHY CONFLICT RESOLUTION IS HARD? (Beginner Explanation)
  Imagine two people editing the same document offline — each on a plane on
  their own laptop. When both land and sync, the server sees two different
  "latest" versions. For binary files (images, videos) you can't merge lines,
  so the system keeps the most recently saved one (last-writer-wins) and
  saves the other as a conflict copy — like "report (Abhishek's conflicted
  copy).docx". For text files it's like a Git merge: non-overlapping edits
  get stitched together automatically, but lines both people changed get
  flagged for the user to resolve. Without any conflict resolution, one
  person's work silently disappears — not acceptable.
```

---

## 11. Key Interview Questions & Answers

**Q: Why chunk files instead of uploading whole?**
> Enables resumable uploads (only re-upload failed chunks), parallel upload, deduplication at chunk level, and efficient delta sync.

**Q: Why pre-signed URLs instead of proxying through backend?**
> Client uploads directly to S3 — offloads bandwidth from backend, reduces cost, improves throughput. Backend only issues short-lived signed URLs.

**Q: Why Redis for upload session state?**
> Fast TTL-based storage for chunk bitmap (which chunks are done), retry count, and transient upload metadata — avoids polluting the main MetaDB.

**Q: How is resumable upload implemented?**
> On `/upload/init`, server checks Redis for existing upload session. Returns `existingChunks` bitmap. Client skips uploaded chunks and resumes from where it left off.

**Q: Why eventual consistency for sync but strong consistency for metadata?**
> Metadata (file name, version, permissions) must be immediately consistent to prevent conflicts. Sync across devices can tolerate slight delay — user expects near-real-time but not instant cross-device propagation.

**Q: How does versioning work?**
> Each commit creates a new `FileVersion` row and a new set of `FileVersionChunk` rows. Old version chunks remain in S3 until retention policy cleans them. `current_version_id` on the `File` row points to the latest.

```
HOW VERSIONING WORKS? (Beginner Explanation)
  Think of it like Google Docs "version history" — every time you save, the
  system doesn't overwrite the old file; it creates a new snapshot and moves
  the "current" pointer to it. Here, each commit creates a new FileVersion
  row and a fresh set of FileVersionChunk pointers. The old chunks stay in
  S3 — they're just not pointed to by the current version anymore. "Restore
  to version 3" simply means updating the current_version_id pointer back to
  version 3's row. Storage cost grows with history depth, so a retention
  policy (e.g., keep 30 versions max) eventually deletes orphaned old blobs
  to reclaim space.
```

**Q: How do you handle quota?**
> User quota is tracked in User DB. On upload init, Validator Svc checks `fileSize` against `remainingQuota`. Also enforced at commit. Quota includes all versions (not just current).

**Q: What does Kafka do here?**
> After commit, File Uploader Svc publishes a change event to Kafka. Sync Svc subscribes and fans out to all connected devices. Decouples upload flow from sync — upload doesn't wait for sync propagation.

---

## 12. Database Schema — Quick Reference

```sql
-- File (core entity)
Files: file_id | parent_folder_id | owner_id | name | size_bytes
       current_version_id | created_at | is_deleted | metadata

-- Version tracking
FileVersions: version_id | file_id | size_bytes | created_at

-- Chunk map for a version
FileVersionChunks: version_id | chunk_index | chunk_id

-- Dedup table
Chunks: chunk_id | object_key (s3://bucket/path) | size_bytes | checksum | created_at

-- Sharing
Permissions: permission_id | resource_type | resource_id | userId | role | created_at
```

---

## 13. HLD → LLD Summary Diagram

```
              ┌──────────────────────────────────┐
              │         client                   │
              │  watcher → chunker → uploader    │
              │  sync engine ← local index       │
              └──────────────┬───────────────────┘
                             │ HTTPS
              ┌──────────────▼───────────────────┐
              │     LB & API Gateway             │
              └──┬──────────┬────────────────────┘
                 │          │
        ┌────────▼──┐  ┌────▼────────┐   ┌──────────────┐
        │ Uploader  │  │  Metadata   │   │ Read/Download│
        │   Svc     │  │    Svc      │   │    Svc       │
        └────┬──────┘  └────┬────────┘   └──────┬───────┘
             │              │                   │
    ┌────────▼──┐    ┌───────▼──────┐    ┌──────▼──────┐
    │ Validator │    │   MetaDB     │    │  S3 (Blob)  │
    │ Dedup Svc │    │ (Postgres)   │    │             │
    └─────┬─────┘    └──────────────┘    └─────────────┘
          │
    ┌─────▼──────┐   ┌──────────────┐
    │   Redis    │   │    Kafka     │──► Sync Svc ──► devices
    │(upload state│  │(change events)│
    └────────────┘   └──────────────┘
```

---

## KEY PATTERNS REFERENCED IN THIS DESIGN

> **For the 2-year developer:** These are the hidden concepts behind design decisions in this system. Each has a dedicated deep-dive file.

### Object vs Block vs File Storage
**Why it matters here:** File bytes → S3 (object storage, unlimited scale, cheap, HTTP). File metadata (tree, sharing) → PostgreSQL on EBS (block storage, fast random reads). Never EBS for file bytes — too expensive and single-machine.
**Deep dive:** `../../Object_vs_Block_vs_File_Storage_S3_EBS_EFS.md`

### Chunked Upload / Multipart Upload
**Why it matters here:** Users upload 5GB+ files. S3 multipart: split into 5MB chunks, upload in parallel, resumable. If interrupted at 60%: resume from chunk 61. Presigned URLs: client uploads directly to S3 — your servers handle zero file bytes.
**Deep dive:** `../../Chunked_Upload_Multipart_Upload.md`

### Content-Addressable Storage
**Why it matters here:** Core deduplication — SHA-256 of each 4MB block is the storage key. 100 users upload same template.docx → stored once. Edit one page of 1GB file → upload 4MB (one changed block), not 1GB.
**Deep dive:** `../../Content_Addressable_Storage_Deduplication.md`

### Blob Storage vs Database
**Why it matters here:** Classic mistake: store file bytes as BLOBs in PostgreSQL. At 10M users × 5MB = 50TB of BLOBs in DB. Buffer pool contaminated. Backup takes days. S3 stores bytes; DB stores only: file_hash, s3_key, size, owner_id.
**Deep dive:** `../../Blob_Storage_vs_Database_For_Files.md`

### CDN Origin Pull vs Origin Push
**Why it matters here:** User-shared files served via CDN. Origin pull — first download from any region fetches from S3, cached at CDN edge. No pre-warming needed (can't predict which files get shared). For popular shared files: origin pull with origin shield prevents S3 stampede.
**Deep dive:** `../../CDN_Origin_Pull_vs_Origin_Push.md`

### Quorum Reads/Writes
**Why it matters here:** File metadata in Cassandra. W=QUORUM before acknowledging upload success. User must not re-upload a file that was saved but not yet replicated to quorum.
**Deep dive:** `../../Quorum_Reads_Writes_Cassandra_W_R_N.md`

### Vector Clocks
**Why it matters here:** Conflict detection for offline edits — Alice edits on laptop, Bob edits same file on mobile, both offline. Vector clock detects concurrent edits → create conflict copy. This is how Dropbox's "conflicted copy" works.
**Deep dive:** `../../Vector_Clocks_Write_Conflict_Detection.md`

### CAP Theorem
**Why it matters here:** CP for file metadata operations (don't lose track of which files a user has — during partition, block writes rather than risk metadata inconsistency). AP for file serving (cached CDN copies available even during origin partition).
**Deep dive:** `../../CAP_Theorem_Applied_What_Actually_Breaks.md`

### [Write-Ahead Log (WAL)](../../Write_Ahead_Log_WAL_Crash_Recovery.md)
**Why this system uses it:** File metadata (which S3 key a file maps to, folder structure, sharing permissions) is stored in PostgreSQL with WAL-backed crash recovery. If the metadata service crashes during a rename or move operation (updating multiple rows), WAL ensures the transaction is either fully applied or fully rolled back on recovery — no partial renames that leave the folder tree inconsistent. `synchronous_commit=on` for metadata writes: losing the mapping between a filename and its S3 key is catastrophic (file becomes unreachable).
