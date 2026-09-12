# Object Storage vs Block Storage vs File Storage
### S3 vs EBS vs EFS — When to Use Which

---

## PART 1 — THE STUDENT CONVERSATION

**Storage is not one thing. There are three completely different ways to store data, each designed for a different job.**

**Object Storage (S3):** Think of it like a postal warehouse. You ship packages (files/objects) and get a tracking number (URL/key). You can retrieve any package by its tracking number. You can't "open" a package and modify one page — you retrieve the whole thing, modify it, and ship a new version back. Scales to billions of objects. Cheap. Globally accessible.

**Block Storage (EBS):** Think of it like the hard drive inside your laptop. It's formatted with a filesystem. Programs can open a file, seek to byte 5000, write 4 bytes, and save. Low latency random access. But it's attached to ONE machine — nobody else can use it. Like a hard drive, if you unplug it from one computer and attach it to another, you have to unmount/mount it.

**File Storage (EFS/NFS):** Think of it like a shared network drive. Multiple machines mount it at the same time. Team members share files. No need to copy — they all access the same directory. But it's slower than block storage and you pay for the network.

---

## PART 2 — THE DIAGRAMS

### Object Storage (S3)

```
S3 Bucket: my-app-videos
────────────────────────────────────────────────────────────────────

  Objects (each is a key → blob pair):
  ─────────────────────────────────────────────────────────────────
  Key:   videos/user123/intro.mp4
  Value: [binary blob, 500MB]
  Metadata: { Content-Type: video/mp4, size: 500MB, created: ..., ETag: md5hash }

  Key:   images/product/shoes-red.jpg
  Value: [binary blob, 2MB]

  Key:   logs/2026/08/31/app.log.gz
  Value: [binary blob, 100KB]

Access:
  GET https://my-app-videos.s3.amazonaws.com/videos/user123/intro.mp4
  PUT to upload. GET to download. DELETE to remove. No partial writes.

Architecture:
  ┌──────────────────────────────────────────────────────────────┐
  │  S3 Cluster (thousands of distributed servers)               │
  │                                                              │
  │  Object → replicated to 3+ availability zones automatically  │
  │  Objects stored in erasure-coded chunks                       │
  │  ANY object accessible via HTTP from anywhere                 │
  │  11 nines (99.999999999%) durability                         │
  └──────────────────────────────────────────────────────────────┘

Best for:
  User uploads (photos, videos, documents)
  Static website assets
  Backups and archives
  Data lake / analytics storage
  CDN origin storage
```

### Block Storage (EBS)

```
EBS Volume: 500GB SSD, attached to EC2 instance
────────────────────────────────────────────────────────────────────

  ┌─────────────────────────────────────────────────────────────┐
  │  EC2 Instance (your application server)                      │
  │                                                              │
  │  /dev/sda1 (root volume) ──────► EBS Volume 1 (50GB OS)    │
  │  /dev/sdb  (data volume)  ──────► EBS Volume 2 (500GB data) │
  │                                                              │
  │  MySQL data files:                                           │
  │  /var/lib/mysql/ibdata1          ← random reads/writes here │
  │  /var/lib/mysql/redo_log         ← sequential writes here   │
  └─────────────────────────────────────────────────────────────┘

  EBS is a network-attached "hard drive" but with SSD performance.
  MySQL can do: fseek(file, offset), fwrite(data, 4096 bytes) — partial writes OK.

  Features:
  → Snapshots: point-in-time backup to S3 (takes seconds to initiate)
  → Multi-attach: EBS io2 volumes can attach to up to 16 EC2 instances simultaneously
    (but requires cluster-aware filesystem like Oracle RAC — rare)
  → IOPS: up to 64,000 IOPS for io2 (for high-performance databases)

Best for:
  Database storage (MySQL, PostgreSQL)
  Transactional application files
  OS root volume
  Any workload needing low-latency random I/O on a single machine
```

### File Storage (EFS / NFS)

```
EFS (Elastic File System) — shared across multiple instances
────────────────────────────────────────────────────────────────────

  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
  │  EC2 Instance 1  │  │  EC2 Instance 2  │  │  EC2 Instance 3  │
  │  (web server)    │  │  (web server)    │  │  (web server)    │
  │                  │  │                  │  │                  │
  │  mount /app/data │  │  mount /app/data │  │  mount /app/data │
  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
           │                     │                     │
           └─────────────────────┼─────────────────────┘
                                 │ NFS protocol
                                 ▼
                         ┌───────────────┐
                         │  EFS Volume   │
                         │  /app/data/   │
                         │  ├── config.json
                         │  ├── uploads/
                         │  └── shared_state/
                         └───────────────┘

  All three EC2 instances read/write to the SAME /app/data directory.
  Changes on Instance 1 are immediately visible to Instances 2 and 3.

Best for:
  Shared configuration files across multiple servers
  Shared application state (legacy apps that use filesystem for state)
  Machine learning training data (multiple GPU instances read same dataset)
  WordPress media uploads (shared across web cluster)
  CI/CD artifact sharing
```

---

## PART 3 — COMPARISON TABLE

```
┌──────────────────────┬──────────────────┬──────────────────┬──────────────────┐
│                      │  Object (S3)     │  Block (EBS)     │  File (EFS)      │
├──────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Access via           │ HTTP (REST API)  │ OS filesystem    │ NFS mount        │
│ Attached to          │ Any client (URL) │ Single EC2       │ Multiple EC2     │
│ Read/write unit      │ Whole object     │ Any byte range   │ Any byte range   │
│ Latency              │ 50–200ms         │ <1ms (SSD)       │ 1–10ms           │
│ Throughput           │ Very high (GB/s) │ Up to 4GB/s      │ Up to 10GB/s     │
│ Scale                │ Unlimited        │ Up to 64TB/vol   │ Auto-scales      │
│ Cost (per GB/month)  │ $0.023           │ $0.08–$0.10      │ $0.30            │
│ Durability           │ 11 nines         │ 5 nines          │ 11 nines         │
│ Multi-machine share  │ Yes (via HTTP)   │ No (1 machine)   │ Yes (NFS)        │
│ Partial writes       │ No               │ Yes              │ Yes              │
│ POSIX filesystem     │ No               │ Yes              │ Yes              │
└──────────────────────┴──────────────────┴──────────────────┴──────────────────┘
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Users upload videos to your OTT platform. Where do you store them?"

**You (architect answer):**

> "Videos are a perfect use case for object storage — S3 or equivalent. Here's why:
>
> Videos are immutable blobs. Once uploaded, we read them back but never partially modify them.
> Object storage is designed exactly for this: write-once, read-many, HTTP access, unlimited scale,
> and extremely cheap per GB ($0.023/GB/month vs $0.10/GB/month for block storage).
>
> The upload flow: the client uploads directly to S3 via a pre-signed URL — our backend never
> handles the video bytes, just issues the URL. This avoids our servers becoming a bandwidth
> bottleneck. After upload, we publish an event to Kafka, a transcoding job picks it up,
> produces multiple HLS segments at different bitrates (480p, 720p, 1080p) and stores those
> in S3 too.
>
> For serving: we put CloudFront (CDN) in front of S3. Users stream from the nearest CDN
> edge node — not from S3 directly. S3 serves as the CDN origin.
>
> I'd never use EBS for video storage — it's attached to a single EC2 instance, expensive,
> and can't serve thousands of concurrent streams. EFS could work but costs 10x more than S3.
>
> EBS is where I'd store the PostgreSQL database (user accounts, view history, subscriptions).
> MySQL data files need low-latency random reads — EBS SSD provides that."

---

## QUICK REFERENCE CARD

```
Choose Object Storage (S3) when:
  ✓ Files accessed via URL/HTTP
  ✓ No need to partially modify files
  ✓ Scale to billions of objects
  ✓ Cost-sensitive per GB
  ✓ CDN origin
  → User uploads, videos, images, backups, data lake, static assets

Choose Block Storage (EBS) when:
  ✓ Database data files (MySQL, PostgreSQL, MongoDB)
  ✓ Need low-latency random I/O (<1ms)
  ✓ Need POSIX filesystem semantics (seek, partial write)
  ✓ Attached to a single server
  → Databases, OS root volumes, transactional workloads

Choose File Storage (EFS/NFS) when:
  ✓ Multiple servers need the SAME filesystem simultaneously
  ✓ Application uses filesystem APIs (not S3 SDK)
  ✓ Shared config, shared state between servers
  → Shared app configs, ML training data, legacy multi-server apps

Cost hierarchy (cheapest to most expensive):
  S3 Standard:    $0.023/GB/month
  EBS gp3:        $0.080/GB/month
  EFS Standard:   $0.300/GB/month

Interview one-liner:
"Object storage is for files you access by URL — S3 is cheap, unlimited, HTTP.
Block storage is for databases — attached to one machine, fast random I/O.
File storage is for shared filesystems — multiple servers, same directory.
For user uploads and videos: always S3."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Every system with files, videos, or attachments will test whether you correctly separate bytes (S3) from metadata (database on EBS) — conflating them is a common junior mistake.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **10 — Cloud Storage (Google Drive/Dropbox)** | S3 (object) for file bytes — unlimited scale, $0.023/GB, HTTP access. PostgreSQL on EBS (block storage) for file metadata — fast random reads for tree traversal. EFS not needed: no shared filesystem between servers required. |
| **17 — OTT Platform (Netflix/Hotstar)** | S3 for video bytes and transcoded HLS segments. PostgreSQL on EBS for user/subscription/view-history database. CDN sits in front of S3 for global delivery. Never EBS for video — too expensive and can't serve concurrent streams. |
| **20 — Email (Gmail/Outlook)** | S3 for attachments (can be 25MB+, binary, random access never needed). PostgreSQL on EBS for email metadata (headers, folder structure, read/unread status, search index). Attachment bytes in DB would kill backup/replication performance. |

**Architect's one-liner for the interview:**
*"S3 holds the bytes, the database holds the address — never store binary files in a relational database."*
