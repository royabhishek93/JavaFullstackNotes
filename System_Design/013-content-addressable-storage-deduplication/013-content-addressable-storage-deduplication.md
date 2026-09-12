# Content-Addressable Storage
### Store File by Hash of Content — Deduplication for Free

---

## PART 1 — THE STUDENT CONVERSATION

**What if instead of naming files by what they are, you named them by what they contain?**

Normal storage: you name files "photo.jpg", "document.pdf", "video.mp4". Two different users upload the same file — you store it twice, under two different names.

Content-addressable storage: you compute the hash (SHA-256 or MD5) of the file's content. The hash IS the filename. If two different users upload the same file, they produce the same hash → you only store one copy.

This is the core idea behind:
- **Google Drive / Dropbox** deduplication (saves 30–50% storage)
- **Git** (every commit, tree, and blob is stored by its SHA-1 hash)
- **Docker images** (each layer is stored by content hash, shared across images)
- **IPFS** (InterPlanetary File System, the peer-to-peer web)

---

## PART 2 — HOW IT WORKS

```
Normal storage (path-based):
────────────────────────────────────────────────────────────────────

  User A uploads "vacation.jpg" (2MB, SHA256: abc123...)
    → Store at: /users/alice/vacation.jpg  [2MB used]

  User B uploads "summer_photo.jpg" (same file, 2MB, SHA256: abc123...)
    → Store at: /users/bob/summer_photo.jpg  [2MB used]

  User C uploads "photo.jpg" (same file again, 2MB, SHA256: abc123...)
    → Store at: /users/carol/photo.jpg  [2MB used]

  Total stored: 6MB for 1 unique file.

Content-addressable storage:
────────────────────────────────────────────────────────────────────

  User A uploads "vacation.jpg" (2MB, SHA256: abc123...)
    → Check: does blob abc123... exist in storage? NO
    → Store blob at: /content/ab/c1/abc123...  [2MB used]
    → Write metadata: { user: alice, name: vacation.jpg, blob: abc123... }

  User B uploads "summer_photo.jpg" (SHA256: abc123...)
    → Check: does blob abc123... exist? YES
    → Don't store it again. 0 bytes added.
    → Write metadata: { user: bob, name: summer_photo.jpg, blob: abc123... }

  User C uploads "photo.jpg" (SHA256: abc123...)
    → Already exists. 0 bytes added.
    → Write metadata: { user: carol, name: photo.jpg, blob: abc123... }

  Total stored: 2MB for 3 uploads of the same file.
  Deduplication ratio: 66% storage saved.

  The "abc123..." hash IS the address. Content determines the address.
```

---

## PART 3 — THE DATA MODEL

```
Database schema (Dropbox-style):
────────────────────────────────────────────────────────────────────

  -- Content-addressable blob store (S3 or distributed filesystem)
  -- S3 key = content hash
  /blobs/
    ab/c1/abc123def456...  (2MB — the actual file bytes)
    7f/e2/7fe2891abc...    (5MB — different file)

  -- Metadata DB (MySQL or PostgreSQL)

  files table:
  ┌─────────────────────────────────────────────────────────────┐
  │  file_id  │  user_id  │  filename        │  content_hash    │
  ├─────────────────────────────────────────────────────────────┤
  │  101      │  alice    │  vacation.jpg    │  abc123def456... │
  │  102      │  bob      │  summer_photo.jpg│  abc123def456... │  ← same hash!
  │  103      │  carol    │  photo.jpg       │  abc123def456... │  ← same hash!
  │  104      │  alice    │  document.pdf    │  7fe2891abc...   │
  └─────────────────────────────────────────────────────────────┘

  blobs table (reference counting for garbage collection):
  ┌────────────────────┬────────────────────┬─────────────┐
  │  content_hash      │  size_bytes        │  ref_count  │
  ├────────────────────┼────────────────────┼─────────────┤
  │  abc123def456...   │  2,097,152 (2MB)   │  3          │  ← 3 users share this
  │  7fe2891abc...     │  5,242,880 (5MB)   │  1          │
  └────────────────────┴────────────────────┴─────────────┘

  When a user deletes file_id=102:
    ref_count for abc123... decremented: 3 → 2
    Blob still exists (2 other users reference it)

  When ref_count reaches 0:
    Blob is orphaned → garbage collection deletes the actual bytes
    This is exactly how Git's garbage collection works too.
```

---

## PART 4 — CHUNKED CONTENT-ADDRESSABLE STORAGE

```
Real Dropbox goes further: hash individual chunks, not whole files.
────────────────────────────────────────────────────────────────────

  Scenario: user has a 1GB file. Makes a small edit on page 5.

  Naive approach: re-upload 1GB with new hash. Old blob deleted, new blob stored.
  → 1GB upload for a 1KB edit. Terrible.

  Chunked CAS (Dropbox uses 4MB blocks):
    Split 1GB file into 256 chunks of 4MB each.
    Each chunk has its own hash.
    Store each chunk by its hash.

    Original file: [chunk_hash_1][chunk_hash_2]...[chunk_hash_103]...[chunk_hash_256]
    After edit to chunk 103: [chunk_hash_1][chunk_hash_2]...[chunk_hash_103_NEW]...[chunk_hash_256]

    Only chunk 103 changed (new hash).
    Only upload: 4MB (one chunk).
    All other 255 chunks: already in storage, reference them with their hashes.

    File metadata stores: [list of chunk hashes in order]
    To reconstruct: fetch chunks by hash, concatenate in order.

  This is why Dropbox sync is so fast — it only uploads changed blocks.
  Git does the same at a file level (git pack objects, delta compression).
```

---

## PART 5 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your cloud storage system (Google Drive clone) serves 100M users. How do you handle storage efficiently?"

**You (architect answer):**

> "Content-addressable storage is the key optimization. Before storing any file, I compute
> its SHA-256 hash. I check if that hash already exists in the blob store. If yes, I just
> create a new metadata record pointing to the existing blob — zero new bytes stored.
>
> At 100M users uploading files, deduplication rates of 20–50% are typical for documents
> and images (photos taken of the same public events, shared templates, common software
> packages). For a 1 petabyte logical storage volume, you might physically store only
> 600–800 TB.
>
> But I'd go further with chunk-level deduplication. Each file is split into 4MB chunks.
> Each chunk is stored by its hash. When a user edits one page of a 100MB PowerPoint,
> only the modified chunk (4MB) is uploaded. The other 25 chunks are already in storage.
> This dramatically reduces sync bandwidth — Dropbox's competitive advantage early on.
>
> For the architecture: S3 stores blobs at key = content_hash (first 2 chars as prefix
> for S3 key distribution, then full hash). A metadata DB (MySQL, sharded by user_id)
> stores the file tree and maps filenames to content hashes. Reference counting ensures
> blobs are deleted when no files point to them.
>
> One security consideration: because blobs are shared across users, I must verify
> ownership before sharing a blob reference. A malicious user can't guess a SHA-256
> hash to access another user's file — but we still validate that the requesting user
> has a metadata record pointing to that blob."

---

## PART 6 — WHERE ELSE CAS IS USED

```
Git:
  Every blob (file contents), tree (directory), and commit is stored by SHA-1.
  git cat-file -p <sha1>  ← read any object by hash
  Two files with same content → one blob, two trees pointing to it
  No deduplication at file level between repos, but within a repo: automatic.

Docker:
  Each image layer is content-addressed.
  ubuntu:20.04 layer sha256:abc...  ← shared across all images using ubuntu base
  Your app image = ubuntu layer + your code layer
  docker pull: only downloads layers you don't already have (same hash = skip)
  docker push: only uploads changed layers
  Registry storage: Netflix sharing the same Node.js base = one copy of Node.js

IPFS (InterPlanetary File System):
  Files are split into blocks, each stored by CID (content identifier = multihash)
  To retrieve: ask network "who has block CID abc123?" → any node with it can serve
  Immutable: changing content = new CID. Old CID always points to old content.

BitTorrent:
  Torrent file contains SHA-1 hashes of all pieces.
  Download verifies each piece: if piece hash doesn't match → discard and re-download.
  This is why BitTorrent is reliable even through corrupt networks.

Interview one-liner:
"Content-addressable storage uses content hash as the key.
Same content = same hash = same key = stored once.
Deduplication is automatic and free. Files become immutable references
to content — deleting a file just removes the reference, not the blob
(until ref_count reaches zero)."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Deduplication is a differentiating follow-up answer in cloud storage and document system interviews — it shows you think about storage efficiency at scale.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **10 — Cloud Storage (Google Drive/Dropbox)** | Core deduplication — SHA-256 of each 4MB block is the S3 key. 100 users upload same template.docx → stored once. Edit one page of a 1GB file → upload 4MB (one changed block), not 1GB. Dropbox's competitive advantage: sync is fast because only changed blocks upload. |
| **18 — Text Editor (Google Docs/Notion)** | Document version history. Each version stores a list of block hashes. Unchanged blocks share storage across versions. Storing 100 versions of a 10MB doc costs ~10MB (shared blocks) not 1GB (100 full copies). |

**Architect's one-liner for the interview:**
*"Content-addressable storage makes deduplication automatic — same bytes produce the same hash, so you store the content once and reference it everywhere."*
