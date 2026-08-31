Distributed Storage (Google Drive / Dropbox)

"Initiate upload → chunk & hash → pre-signed URLs → parallel chunk upload → commit → metadata versioning → sync events to other devices (eventual)"

1. Functional Requirements

Upload/download files (large files supported) and create folders
Resumable uploads (resume after disconnect)
Share files/folders with permissions
Version history (restore older versions)
Cross-device sync (push/pull updates)
2. Non-Functional Requirements

Scale & Durability
Scale — Billions of files; large total storage; multi-region
Durability — No data loss for stored blobs (multi-AZ/replication)
Consistency
Metadata — Strong consistency for file/folder metadata operations
Sync — Eventual consistency is acceptable for cross-device synchronization
3. Core Entities

User
Folder (folder_id, parent_folder_id, owner_id, name)
File (file_id, parent_folder_id, owner_id, name, size_bytes, current_version_id)
FileVersion (version_id, file_id, created_at, created_by, size_bytes)
Chunk (chunk_id, object_key, size_bytes, checksum)
FileVersionChunk (version_id, chunk_index, chunk_id)
4. Upload Flow (resumable, matches diagram)

Initiate: client calls /files/upload/init with fileName, fileSize, parentFolderId
Client chunks file locally and computes checksum (e.g., SHA-256) per chunk
Client requests signed URL for chunk N → service checks if already uploaded and returns URL
Client uploads chunks in parallel; on reconnect, server returns existingChunks so client resumes
Commit: /files/upload/commit persists metadata + version + chunk map and emits sync event to Kafka
5. Deep Dive: Deduplication & Validation

Dedup is typically chunk-level using content hash; identical chunks can be reused across files/versions
Blob store is not the metadata source of truth; metadata DB + version mapping is authoritative
Validations can include checksum verification, size validation, malware scan (async), and quota checks
6. Deep Dive: Sync Engine

Client watcher/local index detects filesystem changes and uploads deltas
Server publishes change events; other devices receive via push (fanout) or pull (polling)
Conflicts resolved via versioning + merge rules (app-specific; for binary files, last-writer-wins is common)
Part of the "System Design Complete Course" course · Interview With Bunny

Stay Updated
Subscribe to my Channel
Connect
"Let's have a coffee together..."
FIND ME EVERYWHERE

Philosophy
How to become successful.!!
Dream life() {
while(!succeed) {
try();
}
return dreamFulfilled();
}
@Copyright?? Really?  ·  If you want, I'll clone this website too... and give you the source code