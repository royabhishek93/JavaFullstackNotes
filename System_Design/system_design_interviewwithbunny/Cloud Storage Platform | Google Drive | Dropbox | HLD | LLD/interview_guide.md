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
| **Upload Manager** | Manages parallel chunk uploads (3 at a time), retries |
| **Sync Engine** | Handles push/pull sync with server; resolves conflicts |

### Server Services

| Service | Role |
|---|---|
| **LB & API Gateway** | Rate limiting, auth, routing |
| **User Onboarding Svc** | Auth, quota management |
| **File Uploader Svc** | Upload init, pre-signed URL generation, commit + metadata write |
| **File Metadata Svc** | CRUD on File/Folder/Version/Permission; updates metadata after commit |
| **Read/Download Svc** | Generates signed S3 URLs for downloads; refresh/pull |
| **Validator Svc** | Validates chunk hash, size, quota, malware scan (async) |
| **Deduplication Svc** | Checks if chunk already exists by content hash; reuses blob |
| **Sync Svc** | Fanout (push) or pull-based sync to all connected devices |

### Storage Layer

| Store | Purpose |
|---|---|
| **User DB** | User accounts (userId, emailId, password, createdDate) |
| **S3 (Blob)** | Raw chunk storage; object key = `s3://bucket/path` |
| **MetaDB** | File, Folder, FileVersion, Chunk, Permissions tables |
| **Redis** | Upload session state: chunk bitmap, retry count, temp upload info |
| **Kafka** | Change event bus: File Uploader Svc publishes → Sync Svc consumes |

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
