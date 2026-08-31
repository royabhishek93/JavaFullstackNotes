# Blob Storage vs Database for Files
### Never Store Files as BLOBs in MySQL — Why?

---

## PART 1 — THE STUDENT CONVERSATION

**It seems convenient: your database can store anything, including files. Why not just put the photo in the users table?**

```sql
CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    profile_photo BLOB    ← storing 2MB image in MySQL row
);
```

This feels elegant — everything in one place, ACID transactions, easy queries. But at scale, it destroys database performance, increases costs by 10-100x, and makes operations a nightmare.

The rule of thumb adopted by every production engineering team: **store files in object storage (S3), store file metadata (path, size, type) in the database.**

Let me explain why this rule exists with concrete examples.

---

## PART 2 — WHAT GOES WRONG WITH BLOBS IN MYSQL

```
Row size explosion:
────────────────────────────────────────────────────────────────────

  Normal user row: id(8) + name(50) + email(50) + created_at(8) = ~116 bytes
  With profile_photo BLOB: 116 bytes + 2,000,000 bytes = ~2 MB per row

  InnoDB row format: rows must fit in pages. Max row size = ~65,535 bytes.
  2MB row DOES NOT FIT in a single InnoDB page!
  MySQL stores overflow in external off-page storage.
  This means every row with a large BLOB requires an extra I/O just to read
  the non-BLOB fields. Even "SELECT name FROM users WHERE id=42" might
  trigger a BLOB page read. Performance tanks.
```

```
Buffer pool contamination:
────────────────────────────────────────────────────────────────────

  InnoDB buffer pool: the RAM cache of frequently-accessed pages.
  Default: 1GB–8GB. Tuned to cache your "hot" rows for fast reads.

  With BLOB columns:
  SELECT * FROM users LIMIT 1000;
  → Loads 1000 × 2MB BLOB pages = 2GB into buffer pool
  → Evicts your actual hot data (index pages, row data)
  → All subsequent queries that used to be served from RAM now hit disk
  → Database latency spikes from 1ms to 100ms across ALL queries

  One BLOB query degrades your entire database for minutes.
```

```
Backup and replication nightmare:
────────────────────────────────────────────────────────────────────

  100K users × 2MB profile photos = 200 GB of BLOB data in MySQL.
  
  mysqldump (logical backup): 200GB dump file. Takes 6 hours.
  Normal backup without BLOBs: 2GB. Takes 5 minutes.

  MySQL binary log replication:
  Every INSERT/UPDATE with a 2MB BLOB gets written to the binary log.
  Binary log grows at 2MB per user created.
  Replica must download and apply these logs.
  Replication lag spikes when many users sign up simultaneously.
  
  With S3:
  S3 is backed up automatically (11 nines durability, cross-region replication).
  MySQL only replicates the 50-byte S3 URL string.
  Binary log: tiny. Replication: fast.
```

```
No HTTP serving from database:
────────────────────────────────────────────────────────────────────

  To serve a profile photo from MySQL:
  Client → Your API Server → MySQL → Load 2MB BLOB → HTTP response to client

  Your API server must:
  1. Open DB connection (from pool)
  2. Run SELECT to get BLOB
  3. Buffer 2MB in memory
  4. Stream 2MB over HTTP to client
  
  At 10,000 concurrent image requests:
  10,000 DB connections (pool exhausted)
  10,000 × 2MB = 20GB RAM consumed by API servers
  Your real API traffic (orders, user lookups) gets no threads/connections

  With S3 + CDN:
  Client → CDN → S3 (direct, no API server involved)
  Your API servers handle zero image bytes.
  DB connections: free for actual business logic.
```

---

## PART 3 — THE RIGHT PATTERN

```
Correct architecture: metadata in DB, bytes in S3
────────────────────────────────────────────────────────────────────

  MySQL (metadata only):
  ┌─────────────────────────────────────────────────────────────────┐
  │  users table                                                     │
  │  id: 42                                                          │
  │  name: "Alice"                                                   │
  │  profile_photo_key: "profiles/alice/photo-v3.jpg"   ← S3 key   │
  │  profile_photo_size: 2097152  (2MB, for display)                │
  │  profile_photo_updated_at: 2026-08-01                           │
  └─────────────────────────────────────────────────────────────────┘

  S3 (actual bytes):
  /profiles/alice/photo-v3.jpg  ← 2MB stored here
  CDN: https://cdn.myapp.com/profiles/alice/photo-v3.jpg  ← served to clients

  Row size: ~200 bytes (no BLOB). Buffer pool: clean. Replication: tiny.
  Image serving: CDN → S3, zero API server load.
```

### The Update Flow

```
User uploads new profile photo:
────────────────────────────────────────────────────────────────────

  1. Client → API Server:
     PUT /users/42/profile-photo
     Content-Type: image/jpeg
     Body: [2MB image bytes]

  2. API Server:
     a. Validate: is it actually a JPEG? Max 5MB? No malicious content?
     b. Upload to S3: PUT s3://bucket/profiles/alice/photo-{uuid}.jpg
     c. Get S3 URL: https://bucket.s3.amazonaws.com/profiles/alice/photo-{uuid}.jpg
     d. UPDATE users SET profile_photo_key = 'profiles/alice/photo-{uuid}.jpg'
                       WHERE id = 42
     e. (optionally) delete old photo from S3: DELETE old key

  3. Return 200 OK with new photo URL.

  Consistency: if S3 upload succeeds but DB update fails:
    → Orphaned S3 object (nobody references it). No user-visible impact.
    → Clean up with S3 lifecycle policy: delete objects not referenced in DB after 7 days.
    → Or: S3 key includes UUID, store UUID in outbox, confirm cleanup later.
```

---

## PART 4 — WHEN IS BLOB IN DB ACCEPTABLE?

```
Tiny files (< 1KB):
  Icons stored as SVG strings in DB: fine.
  Short thumbnails (base64, <1KB): fine.
  Why: row size impact negligible, no I/O overhead for small blobs.

Private, encrypted, access-controlled files:
  Medical records, legal documents, financial statements.
  If you need: "only authenticated users can access, no CDN, no public URL"
  S3 with presigned URLs still works → get URL valid for 1 hour.
  But some compliance environments require database-level encryption at rest
  with full audit trails → PostgreSQL bytea type can work.
  Still: limit to <1MB per file.

Extremely small config/state:
  User avatar in base64 (<5KB): fine if you strip on SELECT with partial columns.
  Large config JSON (10MB): move to S3.

Rule: if any file can be >100KB → never store in DB. Use object storage.
      If ALL files are guaranteed <1KB → DB is acceptable.
      Gray zone 1KB–100KB: prefer S3 unless strong reason otherwise.
```

---

## PART 5 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your user service has a profile photo field. Where do you store it and why?"

**You (architect answer):**

> "Always object storage — S3 in practice. The DB stores only the metadata: the S3 key,
> the file size for display, and the content type.
>
> The reasons are concrete:
>
> First, InnoDB page efficiency. A MySQL page is 16KB. My user row without the photo is
> about 200 bytes — I fit ~80 users per page. With a 2MB BLOB, one user takes 125+ pages.
> Queries that scan users become 125x slower just from the row size.
>
> Second, buffer pool contamination. MySQL's buffer pool caches frequently-accessed pages.
> Serving a BLOB means reading 2MB worth of pages into the pool, evicting your index pages
> and hot row data. Query latency for everything else spikes.
>
> Third, serving. To serve an image from the DB, every request goes through the API server,
> which opens a DB connection, loads 2MB into memory, and streams it back. At 10K concurrent
> image requests: 10K DB connections and 20GB RAM consumed by image data. My actual business
> API traffic gets starved of connections.
>
> With S3: the image goes directly from the CDN edge to the user's browser. Zero API server
> involvement. Zero DB connections. The CDN serves it from cache in 5ms from a node near
> the user.
>
> The DB stores only: profile_photo_key (50 bytes, the S3 path). That's it."

---

## QUICK REFERENCE CARD

```
Never store in DB (beyond a few KB):
  ✗ Profile photos, avatars
  ✗ User-uploaded documents (PDFs, Word files)
  ✗ Videos, audio files
  ✗ Large binary data

Always store in DB:
  ✓ S3 key / URL (50 bytes)
  ✓ File metadata: size, content_type, created_at
  ✓ Access control: who owns it, who can read it
  ✓ Hash (for deduplication / integrity check)

DB stores:
  users.profile_photo_key = "profiles/alice/abc123.jpg"  ← 50 bytes

S3 stores:
  /profiles/alice/abc123.jpg  ← 2MB actual bytes

Why S3, not DB:
  InnoDB: large BLOBs overflow pages → extra I/O even for non-BLOB columns
  Buffer pool: BLOB reads evict hot index/row data → all queries slow down
  Backup: mysqldump with 200GB of BLOBs = hours. Without: minutes.
  Serving: S3+CDN serves directly to browser. DB route requires API server memory.
  Replication: binary log with 2MB events → replica lag spikes.

Acceptable in DB:
  < 1KB text/JSON blobs (icons, small configs)
  Compressed tiny images (< 5KB, rare use case)

Interview one-liner:
"Store S3 key in DB, bytes in S3. A 2MB BLOB in MySQL corrupts the buffer pool,
bloats the binary log, and forces every image request through your API server.
S3 + CDN serves images directly to browsers — zero API server load, zero DB impact."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Storing file bytes in a database is one of the most common junior mistakes in system design interviews — knowing exactly why it fails (buffer pool contamination, backup bloat) shows senior-level thinking.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **10 — Cloud Storage (Google Drive/Dropbox)** | Classic interview mistake — storing 5MB file bytes as BLOBs in PostgreSQL. At 10M users × 5MB average = 50TB of BLOBs in DB. pg_dump takes days. Buffer pool contaminated by BLOB reads. Each S3 key is 50 bytes; the DB stores only metadata. S3 stores bytes. |
| **17 — OTT Platform (Netflix/Hotstar)** | Video thumbnails as BLOBs in MySQL = terrible. Thumbnails are 100KB–500KB each, served directly to browsers on every page load, and there are millions of them. S3 + CDN serves thumbnails directly. DB stores: thumbnail_s3_key (50 bytes). Subtitles as text in DB = fine (50KB each, infrequent access pattern). |

**Architect's one-liner for the interview:**
*"Binary files belong in blob storage, not in your database — storing them in the DB contaminates the buffer pool, bloats backups, and forces every file request through your API layer."*
