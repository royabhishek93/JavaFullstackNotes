# YouTube — Interview Script
## Design YouTube / Vimeo / Dailymotion
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
> Spend 5 minutes here. Close your eyes and trace the flow:
> "user uploads" and separately "user watches." Two separate pipelines.

```
┌─────────────────────────────────────────────────────────────────────┐
│                      YOUTUBE — BIG PICTURE                           │
└─────────────────────────────────────────────────────────────────────┘

WHO UPLOADS?                          WHO WATCHES?
ANY logged-in user                    100 million users/day
        │                                     │
        ▼                                     ▼
┌───────────────┐                   ┌──────────────────┐
│  USER'S FILE  │                   │  CLIENT DEVICE   │
│  (raw video,  │                   │  Phone/TV/Web    │
│   up to 2 GB) │                   └────────┬─────────┘
└───────┬───────┘                            │ presses Play
        │ UPLOAD PIPELINE                    │
        ▼                                    ▼
  S3 Raw Bucket              ┌──────────────────────────┐
        │                    │   CDN EDGE (near user)   │◄── 90% of video
        ▼                    │   CloudFront / Akamai    │    served here
  Kafka (video.uploaded)     └────────────┬─────────────┘
        │                                 │ cache miss only
        ▼                                 ▼
  Video Processor            ┌──────────────────────────┐
  (FFmpeg transcoder)        │     API GATEWAY          │
  makes 4 quality levels:    │  (auth, rate limit,      │
  1080p / 720p / 480p / 360p │   route to services)     │
        │                    └────────────┬─────────────┘
        ▼                                 │
  S3 Encoded Bucket         ┌────────────▼─────────────┐
  + HLS manifest (.m3u8)    │       MICROSERVICES       │
        │                   │  User │ Video │ Comment   │
        │ metadata saved    │  Search │ Recommendation  │
        ▼                   └────────────┬─────────────┘
  Video DB (PostgreSQL)                  │
  (stores manifest URL,     ┌────────────▼─────────────┐
   status, metadata)        │       DATABASES           │
                            │ MySQL │ Redis │ Cassandra │
                            │ Elasticsearch │ S3        │
                            └──────────────────────────┘

UPLOAD FLOW IN ONE SENTENCE:
  User uploads → S3 stores raw file → Kafka triggers processor
  → FFmpeg makes 4 quality versions → S3 stores encoded → manifest URL
  saved in Video DB → video is live.

WATCH FLOW IN ONE SENTENCE:
  User clicks Play → Video Service returns manifest URL (Redis-cached)
  → Client fetches m3u8 manifest from CDN → pulls segments at matching
  quality → CDN serves 90% of traffic → video plays without buffering.
```

---

## RAPID ANSWER — If You Only Have 5 Minutes

*Read this first. Understand the whole answer before going deep.*

```
"I'd design YouTube with five pieces:

1. USER ACCOUNTS (MySQL + Redis):
   Users register, log in, manage channels. JWT for auth.
   Redis caches sessions (15-min access token TTL).
   MySQL for users and video metadata (ACID for uploads).

2. VIDEO UPLOAD + PROCESSING (S3 + Kafka + FFmpeg):
   User uploads raw file directly to S3 via a presigned URL
   (not via backend — too large). On upload, S3 triggers a Kafka
   event. A Video Processor (FFmpeg) consumes the event and
   transcodes to 4 quality levels: 1080p, 720p, 480p, 360p.
   Outputs + HLS manifest (.m3u8) stored back to S3.
   Manifest URL saved in Video DB (PostgreSQL).
   Video status: PROCESSING → READY.

3. VIDEO STREAMING (CDN + HLS + ABR):
   Client calls GET /videos/{id}/play → gets manifest URL.
   Client fetches .m3u8 from CDN. Every 8-10 seconds, client
   measures bandwidth and pulls next segment at the right quality.
   CDN serves 90% of traffic. 100M users × 5 videos/day =
   ~30K RPS peak — CDN absorbs almost all of it.

4. SEARCH + RECOMMENDATIONS (Elasticsearch + Spark + Redis):
   Elasticsearch for title/description/tag search.
   Spark batch job nightly → collaborative filtering →
   precomputed top-20 list per user → stored in Redis.
   Updated per view in real-time.

5. VIEW COUNT (Redis write-back):
   View counts hit Redis (100K writes/sec capacity).
   Background job flushes to MySQL every 5 minutes.
   Deduplication: 30-second watch threshold + cookie per session."
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
│ CDN              │ Content Delivery Network. Servers near every user.   │
│                  │ YouTube Mumbai users get video from Mumbai, not USA. │
│                  │ CloudFront (AWS) / Akamai are popular CDNs.          │
├──────────────────┼──────────────────────────────────────────────────────┤
│ HLS              │ HTTP Live Streaming. Apple's streaming protocol.     │
│                  │ Video split into chunks. Master playlist (.m3u8)     │
│                  │ lists all quality variants. Client picks per chunk.  │
├──────────────────┼──────────────────────────────────────────────────────┤
│ ABR              │ Adaptive Bitrate. Client automatically switches      │
│                  │ quality (1080p → 480p) based on current bandwidth.   │
│                  │ Result: no buffering on slow internet.               │
├──────────────────┼──────────────────────────────────────────────────────┤
│ m3u8 / manifest  │ A text file listing all video segment URLs in order. │
│                  │ The player's table of contents. Without it, the      │
│                  │ player doesn't know which chunk comes next.          │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Transcoding      │ Converting raw video (MP4/MOV) into multiple         │
│ / FFmpeg         │ quality levels (1080p, 720p, 480p, 360p). FFmpeg     │
│                  │ is the open-source tool used to do this.             │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Presigned URL    │ A temporary S3 URL that lets the user upload         │
│                  │ directly to S3 without going through the backend.    │
│                  │ Expires in ~15 minutes. Used for large file uploads. │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Kafka            │ Message queue. Upload triggers an event. Video       │
│                  │ Processor consumes it asynchronously. Upload API     │
│                  │ returns immediately without waiting for processing.  │
├──────────────────┼──────────────────────────────────────────────────────┤
│ S3               │ Amazon cloud storage. Stores raw + encoded video     │
│                  │ files. Cheap, durable, unlimited scale.              │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Redis            │ In-memory store. Used for: view count buffer,        │
│                  │ recommendation cache, session tokens. Sub-ms reads.  │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Elasticsearch    │ Search engine. Full-text search on video titles,     │
│                  │ descriptions, tags. Much faster than SQL LIKE.       │
├──────────────────┼──────────────────────────────────────────────────────┤
│ MySQL/PostgreSQL │ Relational DB. Stores users, video metadata (title,  │
│                  │ views, status, manifest URL), subscriptions.         │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Cassandra        │ NoSQL DB for high write throughput. Used for         │
│                  │ watch history (resume position per user).            │
├──────────────────┼──────────────────────────────────────────────────────┤
│ JWT              │ JSON Web Token. Signed token given at login.         │
│                  │ Client sends it on every request. 15-min TTL.        │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Microservices    │ Each feature (Video, User, Comment, Search) is a     │
│                  │ separate service that scales independently.          │
├──────────────────┼──────────────────────────────────────────────────────┤
│ DLQ              │ Dead Letter Queue. After 3 Kafka retries, a failed   │
│ (Dead Letter Q)  │ message goes here. Engineer investigates. Prevents   │
│                  │ infinite retry loops crashing the consumer.          │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Write-back cache │ Write to Redis first (fast). Background job syncs    │
│                  │ to the DB later in batches. Used for view counts.    │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Collaborative    │ Recommendation algorithm: "users who watched what    │
│ Filtering        │ you watched, also watched X." Computed offline with  │
│                  │ Apache Spark on watch history data nightly.          │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Content ID       │ YouTube's copyright system. Computes a fingerprint   │
│                  │ of every uploaded video. Matches against a database  │
│                  │ of reference fingerprints from copyright owners.     │
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
│  MySQL / PostgreSQL │ WHY: Video metadata + user accounts need ACID.   │
│  (Video Metadata)   │ If a video is half-uploaded and the server fails, │
│                     │ we must not corrupt the status or manifest URL.  │
│                     │ MySQL transactions ensure all-or-nothing writes. │
│                     │                                                  │
│                     │ WHY NOT MongoDB: Flexible schema not needed here. │
│                     │ All videos have the same shape. ACID is more     │
│                     │ important. WHY NOT Cassandra: No ACID, no joins. │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  S3                 │ WHY: 5 PB/day of video. No database stores       │
│  (Video Storage)    │ binary blobs at this scale cheaply.             │
│                     │ S3: unlimited, 11-nines durability, $0.02/GB.   │
│                     │ Integrates natively with CloudFront (CDN).       │
│                     │                                                  │
│                     │ WHY NOT own disk/NFS: Doesn't scale. Expensive   │
│                     │ to manage redundancy manually.                   │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  CDN (CloudFront)   │ WHY: 100M users × 5 videos/day = ~30K RPS peak. │
│                     │ S3 origin in one region can't serve this. CDN    │
│                     │ caches segments at 200+ PoPs worldwide. User in  │
│                     │ Mumbai gets video from Mumbai PoP (5ms vs 200ms).│
│                     │ CDN absorbs 90% of all video traffic.            │
│                     │                                                  │
│                     │ WHY NOT just serve from S3: High latency, high   │
│                     │ cost, no geographic distribution, no scale.      │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Kafka              │ WHY: Upload must return instantly to the user.   │
│  (Video Processing) │ We can't make the user wait 10 minutes while     │
│                     │ FFmpeg transcodes. Kafka decouples upload from   │
│                     │ processing. Upload API returns "PROCESSING" in   │
│                     │ 200ms. Kafka delivers to transcoder async.       │
│                     │ If transcoder crashes, Kafka replays the event.  │
│                     │                                                  │
│                     │ WHY NOT synchronous transcoding: User waits      │
│                     │ 10+ minutes. Upload API times out. Bad UX.       │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Redis              │ WHY: View counts are written ~11K times/sec      │
│  (View Count +      │ (1B views/day ÷ 86400s). MySQL handles ~50K      │
│   Recommendations)  │ writes/sec but at high cost. Redis handles       │
│                     │ 1M writes/sec from RAM. Write-back pattern:      │
│                     │ increment Redis INCR → flush to MySQL every 5m.  │
│                     │ Also stores precomputed recommendations per user.│
│                     │                                                  │
│                     │ WHY NOT write views directly to MySQL: DB dies   │
│                     │ at 11K writes/sec from a single hot counter.     │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Elasticsearch      │ WHY: Full-text search on 800M videos. SQL LIKE   │
│  (Search)           │ queries are O(n) table scans — impossibly slow.  │
│                     │ Elasticsearch uses inverted indexes: "cooking" → │
│                     │ [vid1, vid7, vid42]. Lookup in microseconds.     │
│                     │ Supports fuzzy match (typos), filters, ranking.  │
│                     │                                                  │
│                     │ WHY NOT MySQL full-text: Decent for <10M rows,   │
│                     │ not for 800M videos with complex ranking.        │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Presigned URL      │ WHY: Videos are up to 2 GB. Routing through our  │
│  (S3 Direct Upload) │ backend wastes: bandwidth (doubled), time (slow),│
│                     │ memory (server buffers entire file). Presigned   │
│                     │ URL lets browser upload directly to S3. Backend  │
│                     │ only generates the URL (10ms call).              │
│                     │                                                  │
│                     │ WHY NOT upload to backend, forward to S3:       │
│                     │ 2 GB × 8 uploads/sec = 16 GB/sec backend traffic.│
│                     │ Backend becomes a bottleneck.                    │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  HLS + ABR          │ WHY: Can't stream a raw 2 GB MP4 efficiently.    │
│  (Streaming Proto.) │ HLS splits video into 6-10s chunks. Client picks │
│                     │ quality per chunk based on measured bandwidth.   │
│                     │ Result: seamless quality switching, no full      │
│                     │ re-download on quality change, fast start.       │
│                     │                                                  │
│                     │ WHY NOT progressive MP4 download: No quality     │
│                     │ switching. Entire file must buffer to start.     │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Cassandra          │ WHY: Watch history (resume position) gets writes  │
│  (Watch History)    │ from every active viewer every 30 seconds.       │
│                     │ 100M DAU × fraction watching = millions of       │
│                     │ writes/sec. Cassandra partitioned by userId so   │
│                     │ all history for one user is on one node.         │
│                     │                                                  │
│                     │ WHY NOT MySQL: Dies at this write volume.        │
│                     │                                                  │
└─────────────────────┴──────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 4+ — FULL INTERVIEW SCRIPT ═══════════════

---

## OPENING — When Interviewer Says "Design YouTube"

*"Great question. Before I start designing, let me ask a few clarifying
questions to make sure I'm solving the right problem."*

---

## STEP 1 — Requirements Gathering (Speak This Out Loud)

*"I want to confirm the core features and constraints first..."*

```
YOU ASK:                              INTERVIEWER SAYS:
────────────────────────────────────────────────────────────────
"Can anyone upload videos?"        →  "Yes, any logged-in user"
"Live streaming in scope?"         →  "No, only pre-recorded"
"Max video size / length?"         →  "Up to 2 GB, 2 hours max"
"Recommendations needed?"          →  "Basic collaborative filtering"
"Comments, likes, subscriptions?"  →  "Yes, all in scope"
"How many users?"                  →  "100 million daily active"
"Global or single region?"         →  "Global — YouTube scale"
────────────────────────────────────────────────────────────────
```

*"Perfect. Let me summarize..."*

```
┌───────────────────────────────────────────────────────────────┐
│                    REQUIREMENTS SUMMARY                        │
├───────────────────────────────────────────────────────────────┤
│  FUNCTIONAL (what we build):                                  │
│  1. Any user uploads videos (up to 2 GB)                      │
│  2. Videos processed into multiple quality levels             │
│  3. Users stream videos with adaptive quality                 │
│  4. Search by title, description, tags                        │
│  5. Like, comment, subscribe to channels                      │
│  6. Basic recommendations per user                            │
├───────────────────────────────────────────────────────────────┤
│  NON-FUNCTIONAL (how it behaves):                             │
│  Scale:    100M DAU, 500 hrs/min uploaded, ~30K RPS peak      │
│  CAP:      HIGH AVAILABILITY >> Consistency                   │
│            Exception: video metadata upload = CONSISTENT      │
│  Latency:  <200ms video start time, <50ms search              │
│  Arch:     Microservices (100M users can't run on 1 server)   │
└───────────────────────────────────────────────────────────────┘
```

*"Key difference from OTT: ANY user can upload here. That means we
must handle untrusted input — validation, malware scanning, copyright
detection. The ingestion pipeline is much more complex."*

---

## STEP 2 — Capacity Estimation (Speak This Out Loud)

*"Let me do back-of-envelope to understand the scale..."*

```
STORAGE:
─────────────────────────────────────────────────────────────────
"500 hours uploaded every minute.
 Average bitrate per quality level = ~2 Mbps across 4 variants.
 Each hour = 3600s × 2 Mbps × 4 variants / 8 = ~3.6 GB/hour

 500 hours/min × 60 min × 3.6 GB/hour = ~108 TB/day new uploads
 With redundancy × 3: ~300 TB/day.
 Over 5 years: ~500 PB total."

BANDWIDTH:
─────────────────────────────────────────────────────────────────
"100M DAU × 5 videos/day × avg 50 MB per view = 25 PB/day
 Peak = 25 PB / 86,400s × 3 (peak factor) = ~870 GB/sec
 CDN handles 90% → origin only sees ~87 GB/sec"

WRITE LOAD (view counts):
─────────────────────────────────────────────────────────────────
"1 billion views/day = ~11,500 writes/sec on view counters.
 Too hot for MySQL. Use Redis write-back (Redis: 1M writes/sec)."

REQUESTS PER SECOND:
─────────────────────────────────────────────────────────────────
"100M DAU × 5 views/day = 500M requests/day
 Peak (3x average): ~17K RPS for API calls
 CDN segment requests: ~30K RPS"
```

*"So the headline numbers: 500 PB storage, 30K RPS peak on CDN,
11K writes/sec on view counts. Now let me draw the architecture."*

---

## STEP 3 — Core Entities

*"Before APIs, let me identify the core data entities..."*

```
┌──────────────────────────────────────────────────────────────┐
│                     CORE ENTITIES                             │
├──────────────────┬───────────────────────────────────────────┤
│ Entity           │ What it holds                             │
├──────────────────┼───────────────────────────────────────────┤
│ User             │ userId, email, password, channelName      │
│ Video            │ videoId, userId, title, status, viewCount │
│ VideoAsset       │ videoId, quality, s3Url, manifestUrl      │
│ Comment          │ commentId, videoId, userId, text, likes   │
│ Subscription     │ subscriberId, channelId, createdAt        │
│ WatchHistory     │ userId, videoId, positionSec, watchedAt   │
└──────────────────┴───────────────────────────────────────────┘
```

---

## STEP 4 — API Design (Speak This Out Loud)

*"One requirement = one or more endpoints. Let me map them..."*

### Upload API

```
┌────────────────────────────────────────────────────────────────────┐
│                        UPLOAD APIs                                  │
├────────────┬───────────────────────────────┬───────────────────────┤
│ Method     │ Endpoint                      │ Purpose               │
├────────────┼───────────────────────────────┼───────────────────────┤
│ POST       │ /api/v1/videos/upload-url     │ Get presigned S3 URL  │
│ POST       │ /api/v1/videos               │ Save metadata post-S3 │
│ GET        │ /api/v1/videos/{videoId}     │ Get video status/info │
└────────────┴───────────────────────────────┴───────────────────────┘

POST /api/v1/videos/upload-url
  Headers: { Authorization: "Bearer eyJ..." }
  Request: { "fileName": "tutorial.mp4", "fileSizeBytes": 104857600 }
  Response 200:
  {
    "uploadUrl": "https://s3.amazonaws.com/yt-raw/...?X-Amz-Signature=...",
    "videoId":   "vid-uuid-123",
    "expiresIn": 900   ← URL expires in 15 minutes
  }

POST /api/v1/videos   ← called AFTER S3 upload completes
  Request:
  {
    "videoId":     "vid-uuid-123",
    "title":       "System Design Tutorial",
    "description": "Learn HLD in 30 mins",
    "tags":        ["tech", "system-design"],
    "visibility":  "PUBLIC"
  }
  Response 201:
  {
    "videoId": "vid-uuid-123",
    "status":  "PROCESSING",   ← not READY yet
    "message": "Video is being processed. We'll notify you when ready."
  }
```

### Watch API

```
┌────────────────────────────────────────────────────────────────────┐
│                        WATCH APIs                                   │
├────────────┬───────────────────────────────┬───────────────────────┤
│ Method     │ Endpoint                      │ Purpose               │
├────────────┼───────────────────────────────┼───────────────────────┤
│ GET        │ /api/v1/videos/{id}/play      │ Get manifest URL      │
│ POST       │ /api/v1/videos/{id}/view      │ Record a view         │
│ POST       │ /api/v1/stream/heartbeat      │ Save watch position   │
└────────────┴───────────────────────────────┴───────────────────────┘

GET /api/v1/videos/{videoId}/play
  Response 200:
  {
    "manifestUrl": "https://cdn.youtube.com/vid-123/master.m3u8",
    "resumeAt":    342,    ← seconds (continue watching)
    "title":       "System Design Tutorial",
    "duration":    1845
  }
```

### Search API

```
GET /api/v1/search?q=system+design&sort=relevance&page=1&limit=20
  Response 200:
  {
    "page": 1,
    "total": 48200,
    "results": [
      {
        "videoId":    "vid-123",
        "title":      "System Design Interview",
        "thumbnail":  "https://cdn.youtube.com/thumb/vid-123.jpg",
        "views":      1250000,
        "duration":   "32:14",
        "channelName":"TechWithAbhi",
        "uploadedAt": "2024-01-15"
      }
    ]
  }
```

---

## STEP 5 — High-Level Architecture (Draw on Whiteboard)

*"Two separate flows — let me draw them both."*

> **► DRAW THIS on the whiteboard ◄**
> Start left: User box. Split into two flows (upload and watch).
> Upload path: S3 → Kafka → Processor → S3 → DB.
> Watch path: Client → CDN → API GW → Video Service → Redis → S3/CDN.
> Draw databases at the bottom.

```
                ╔══════════════════════════════════════════╗
                ║        YOUTUBE ARCHITECTURE               ║
                ╚══════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════════
  UPLOAD FLOW  (creator uploads a video)
═══════════════════════════════════════════════════════════════════

┌──────────┐
│ CREATOR  │
│ (browser)│
└────┬─────┘
     │ 1. POST /videos/upload-url → gets presigned S3 URL
     │ 2. PUT directly to S3 (browser → S3, no backend)
     │ 3. POST /videos (save metadata, trigger processing)
     ▼
┌───────────────────┐
│  API GATEWAY      │  → validates JWT, routes to Video Service
└────────┬──────────┘
         │
         ▼
┌───────────────────┐    saves metadata    ┌───────────────┐
│  VIDEO SERVICE    │ ──────────────────▶  │  Video DB     │
│                   │                      │  (MySQL)      │
│  status=PROCESSING│    Kafka event       │  status:      │
│                   │ ──────────────────▶  │  PROCESSING   │
└───────────────────┘                      └───────────────┘
                              │
                              ▼ Kafka: "video.uploaded"
                   ┌──────────────────────┐
                   │  VIDEO PROCESSOR     │
                   │  (FFmpeg workers)    │
                   │                      │
                   │  Downloads raw S3    │
                   │  Transcodes to:      │
                   │  ┌──────┬──────┐     │
                   │  │1080p │ 720p │     │
                   │  │ 480p │ 360p │     │
                   │  └──────┴──────┘     │
                   │  Creates .m3u8       │
                   └──────────┬───────────┘
                              │
                    ┌─────────┴──────────┐
                    │                    │
                    ▼                    ▼
          ┌──────────────┐    ┌──────────────────┐
          │  S3 ENCODED  │    │   Video DB       │
          │  (segments + │    │   status: READY  │
          │   .m3u8 file)│    │   manifestUrl:...|
          └──────────────┘    └──────────────────┘
                    │
                    ▼
          ┌──────────────┐
          │ ELASTICSEARCH│  ← CDC or direct write on READY
          │ (title, tags,│
          │  description)│
          └──────────────┘

═══════════════════════════════════════════════════════════════════
  WATCH FLOW  (viewer watches a video)
═══════════════════════════════════════════════════════════════════

┌──────────────────────┐
│  CLIENT DEVICE       │
│  (phone / TV / web)  │
└──────────┬───────────┘
           │  GET /videos/{id}/play
           ▼
┌──────────────────────┐
│   CDN EDGE           │◄── Video SEGMENTS served here (90%)
│   CloudFront PoP     │    TTL: 7 days (immutable)
└──────────┬───────────┘
           │ cache miss (first request only)
           ▼
┌──────────────────────┐
│   API GATEWAY        │
│   JWT validate       │
│   Rate limit         │
└──────────┬───────────┘
           │
     ┌─────┴──────────────────┐
     │                        │
     ▼                        ▼
┌──────────┐           ┌─────────────┐
│  VIDEO   │           │   SEARCH    │
│ SERVICE  │           │   SERVICE   │
│          │           │             │
│ Redis    │           │ Elasticsearch│
│ (manifest│           │ (full-text) │
│  cache,  │           └─────────────┘
│  1hr TTL)│
│    ↓     │
│ MySQL    │
│ (fallback│
│  if miss)│
└──────────┘

           │ returns manifest URL
           ▼
  Client fetches .m3u8 from CDN
  → measures bandwidth → picks quality
  → fetches segments every 8-10 seconds
  → ABR switches quality automatically
  → VIDEO PLAYS
```

---

> **► DRAW THIS on the whiteboard ◄**

## SEQUENCE DIAGRAM — VIDEO UPLOAD + PROCESSING

```
  Creator     Upload Service    S3          Kafka       Transcoder   CDN
     │               │            │             │             │         │
     │ POST /videos  │            │             │             │         │
     │ (metadata)    │            │             │             │         │
     │──────────────▶│            │             │             │         │
     │               │ Presign S3 │             │             │         │
     │               │ upload URL │             │             │         │
     │               │───────────▶│             │             │         │
     │ {uploadUrl,   │◀───────────│             │             │         │
     │  videoId}     │            │             │             │         │
     │◀──────────────│            │             │             │         │
     │               │            │             │             │         │
     │ PUT uploadUrl │            │             │             │         │
     │ [raw video]   │            │             │             │         │
     │──────────────────────────▶│             │             │         │
     │◀──────────────────────────│             │             │         │
     │  [200 OK ETag]│            │             │             │         │
     │               │            │             │             │         │
     │ POST /videos/ │            │             │             │         │
     │ {id}/publish  │            │             │             │         │
     │──────────────▶│            │             │             │         │
     │               │ UPDATE     │             │             │         │
     │               │ status=    │             │             │         │
     │               │ PROCESSING │             │             │         │
     │               │ publish    │             │             │         │
     │               │ video.uploaded           │             │         │
     │               │──────────────────────────▶            │         │
     │ 202 {videoId, │            │             │             │         │
     │  status:PROC} │            │             │             │         │
     │◀──────────────│            │             │             │         │
     │               │            │             │             │         │
     │               │            │             │ Transcoder  │         │
     │               │            │             │ consumes    │         │
     │               │            │             │────────────▶│         │
     │               │            │             │             │ transcode│
     │               │            │             │             │ 4K,1080p│
     │               │            │             │             │ 720p,   │
     │               │            │             │             │ 480p    │
     │               │            │             │             │ → HLS   │
     │               │            │             │             │ manifest│
     │               │            │             │             │ upload  │
     │               │            │             │             │ to S3   │
     │               │            │             │             │────────▶│
     │               │            │             │             │         │
     │               │            │             │             │ UPDATE  │
     │               │            │             │             │ video   │
     │               │            │             │             │ status= │
     │               │            │             │             │ READY   │
```

## SEQUENCE DIAGRAM — VIDEO PLAYBACK

```
  Viewer      CDN Edge      API Gateway    Auth Service    S3 (HLS)
     │              │             │              │               │
     │ GET /videos/ │             │              │               │
     │ {id}/stream  │             │              │               │
     │─────────────▶│             │              │               │
     │              │ cache miss  │              │               │
     │              │────────────▶│              │               │
     │              │             │ Verify JWT   │               │
     │              │             │ + sub plan   │               │
     │              │             │─────────────▶│               │
     │              │             │◀─────────────│               │
     │              │             │  {VALID}     │               │
     │              │ {manifest   │              │               │
     │              │  presigned  │              │               │
     │◀─────────────│  URL}       │              │               │
     │              │             │              │               │
     │ GET .m3u8    │             │              │               │
     │─────────────▶│             │              │               │
     │◀─────────────│ {playlist:  │              │               │
     │              │  360p,720p, │              │               │
     │              │  1080p URLs}│              │               │
     │              │             │              │               │
     │ GET .ts seg  │             │              │               │
     │ (ABR: picks  │             │              │               │
     │  best quality│             │              │               │
     │  for bandwidth)            │              │               │
     │─────────────▶│             │              │               │
     │◀─────────────│ {video chunk│              │               │
     │              │  cached PoP}│              │               │
```

---

## STEP 6 — Database Schema Design (Draw on Whiteboard)

*"Three key schemas to draw — MySQL for video metadata,
Redis for view counts, and the .m3u8 manifest structure."*

> **► DRAW THIS on the whiteboard ◄**
> Draw 3 boxes: videos table (MySQL), view_count key (Redis),
> master.m3u8 structure. Show the status enum on videos table.

### Video DB — MySQL

```
┌─────────────────────────────────────────────────────┐
│                      videos                          │
├──────────────────────┬──────────────────────────────┤
│ video_id             │ UUID (PK)                    │
│ user_id              │ UUID (FK → users)            │
│ title                │ VARCHAR(200) NOT NULL        │
│ description          │ TEXT                         │
│ status               │ ENUM(PROCESSING,READY,FAILED)│
│ manifest_url         │ VARCHAR(500)  ← CDN path     │
│ duration_sec         │ INT           ← set on READY │
│ view_count           │ BIGINT DEFAULT 0             │
│ visibility           │ ENUM(PUBLIC,PRIVATE,UNLISTED)│
│ content_hash         │ VARCHAR(64)   ← for dedup    │
│ created_at           │ TIMESTAMP                    │
└──────────────────────┴──────────────────────────────┘
CREATE INDEX idx_videos_user ON videos(user_id);
CREATE INDEX idx_videos_status ON videos(status);
CREATE INDEX idx_videos_hash ON videos(content_hash);  ← dedup

┌─────────────────────────────────────────────────────┐
│                      users                           │
├──────────────────────┬──────────────────────────────┤
│ user_id              │ UUID (PK)                    │
│ email                │ VARCHAR(255) UNIQUE NOT NULL │
│ password_hash        │ VARCHAR(255)                 │
│ channel_name         │ VARCHAR(100)                 │
│ created_at           │ TIMESTAMP                    │
└──────────────────────┴──────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                   subscriptions                      │
├──────────────────────┬──────────────────────────────┤
│ subscriber_id        │ UUID (FK → users)            │
│ channel_id           │ UUID (FK → users)            │
│ created_at           │ TIMESTAMP                    │
│ PRIMARY KEY          │ (subscriber_id, channel_id)  │
└──────────────────────┴──────────────────────────────┘
```

### Redis — View Count Architecture

```
KEY STRUCTURE:
  views:vid:{videoId}   → integer (INCR on each view)
  reco:{userId}         → JSON list of top-20 videoIds (TTL 1hr)
  session:{userId}      → JWT session data (TTL 15min)

VIEW COUNT FLOW:
  User watches video
       │
       ▼
  POST /videos/{id}/view
       │
       ▼
  Redis: INCR views:vid:123          ← atomic, <1ms
       │
       ▼ (every 5 minutes, background job)
  SELECT key, value FROM Redis WHERE key LIKE 'views:vid:*'
       │
       ▼
  UPDATE videos SET view_count = view_count + redis_delta
       │
       ▼
  DELETE Redis keys                  ← reset counters
```

### HLS Manifest Structure

```
master.m3u8 (table of contents — client downloads this first)
──────────────────────────────────────────────────────────────
#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080
https://cdn.youtube.com/vid-123/1080p/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=1280x720
https://cdn.youtube.com/vid-123/720p/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=854x480
https://cdn.youtube.com/vid-123/480p/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=500000,RESOLUTION=640x360
https://cdn.youtube.com/vid-123/360p/playlist.m3u8

720p/playlist.m3u8 (segment index for one quality)
──────────────────────────────────────────────────────────────
#EXTM3U
#EXT-X-TARGETDURATION:10
#EXTINF:10.0,
https://cdn.youtube.com/vid-123/720p/seg001.ts
#EXTINF:10.0,
https://cdn.youtube.com/vid-123/720p/seg002.ts
#EXT-X-ENDLIST
```

> **► DRAW THIS on the whiteboard ◄**

## ER RELATIONSHIP DIAGRAM

```
┌──────────────────────────────────────────────────────────────────┐
│                YOUTUBE — ENTITY RELATIONSHIP                      │
└──────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────────────────────────┐
│    users     │     │            videos                 │
│   (MySQL)    │     │           (MySQL)                 │
├──────────────┤     ├──────────────────────────────────┤
│ PK user_id   │─────│ PK video_id UUID                 │
│    username  │ 1 N │ FK channel_id UUID               │
│    email TEXT│     │    title VARCHAR                 │
│    plan ENUM │     │    description TEXT              │
└──────┬───────┘     │    status ENUM(PROC,READY,FAILED)│
       │             │    duration_sec INT              │
       │             │    view_count BIGINT             │
       │             │    thumbnail_url TEXT            │
       │             │    uploaded_at TIMESTAMP         │
       │             └──────────────┬───────────────────┘
       │                            │ 1
┌──────▼──────────┐                 │ N
│    channels     │    ┌────────────▼──────────────────┐
│    (MySQL)      │    │       video_segments           │
├─────────────────┤    │        (Cassandra)             │
│ PK channel_id   │    ├───────────────────────────────┤
│ FK user_id      │    │ PK video_id UUID (PART)       │
│    name VARCHAR │    │    resolution ENUM (CLUST)    │
│    subscriber_ct│    │    s3_manifest_url TEXT       │
│    created_at   │    │    processing_status ENUM     │
└─────────────────┘    │    created_at TIMESTAMP       │
                       └───────────────────────────────┘

                       ┌───────────────────────────────┐
                       │     view_events (Kafka→CH)    │
                       ├───────────────────────────────┤
                       │    video_id UUID              │
                       │    user_id UUID               │
                       │    watch_duration_sec INT     │
                       │    device_type ENUM           │
                       │    timestamp TIMESTAMP        │
                       └───────────────────────────────┘

Redis:
┌────────────────────────────────────────────────────┐
│ view_count:{videoId}    INT   INCR (hot counter)   │
│ liked_by:{videoId}      SET   userIds (50M max)    │
│ video_meta:{videoId}    HASH  title,thumb,dur etc  │
│ feed:{userId}           ZSET  score→videoId        │
└────────────────────────────────────────────────────┘
```

---

## STEP 7 — Video Upload Deep Dive

*"Let me walk through exactly what happens when a creator uploads a video..."*

> **► DRAW THIS on the whiteboard ◄**
> Draw 6 vertical lines: Creator, Browser, API GW, Video Svc, Kafka, Processor.
> Show presigned URL request, direct S3 upload, metadata POST, Kafka event, processing, READY notification.

```
Creator     API GW     Video Svc     S3       Kafka     Processor
   │            │           │         │           │          │
   │─ POST /upload-url ────▶│         │           │          │
   │            │─────────────────────────────────────────▶  │
   │            │           │─ generate presigned URL ──▶│   │
   │            │◀──────────────────────────── uploadUrl ─│   │
   │◀─ uploadUrl ─────────▶ │         │           │          │
   │                        │         │           │          │
   │─── PUT (raw video) ─────────────▶│           │          │
   │◀──────── 200 OK ─────────────────│           │          │
   │                        │         │           │          │
   │─ POST /videos ─────────▶         │           │          │
   │            │─────────────────────────────────────────▶  │
   │            │           │─ save metadata ─────────────▶  │
   │            │           │─ publish event ───────────▶│   │
   │◀─ 201 PROCESSING ──────│         │           │          │
   │                        │         │           │          │
   │                        │         │           │◀─ consume │
   │                        │         │           │          │─ download raw
   │                        │         │           │          │─ transcode
   │                        │         │◀──────────────────── │ upload encoded
   │                        │         │           │          │
   │                        │         │◀─ update status READY│
   │◀── push notification ──│         │           │          │
   │   "Your video is live!"│         │           │          │
```

---

## STEP 8 — Scalability

*"Let me address the three main bottlenecks at YouTube scale..."*

```
BOTTLENECK 1: VIEW COUNT WRITES (11K writes/sec)
─────────────────────────────────────────────────────────────────
Problem: 1B views/day = 11K writes/sec. MySQL max = ~50K writes/sec
but a single hot row (counter per video) causes lock contention.
Solution: Redis write-back.
  → INCR Redis counter on each view (atomic, 1M writes/sec capacity)
  → Background job every 5min: batch UPDATE MySQL
  → View count lags ~5min. Acceptable.
Deduplication: 30-second watch threshold (short views don't count).
Cookie-based dedup: same browser can't inflate count within 24hrs.

BOTTLENECK 2: VIRAL VIDEO (1M concurrent viewers on 1 video)
─────────────────────────────────────────────────────────────────
Problem: All 1M users fetch the same segments simultaneously.
CDN is the answer. 1M viewers × 1 segment/8s = 125K req/sec on CDN.
CDN has 200+ PoPs. Each PoP handles ~625 req/sec. Easy.
Cache hit ratio for viral video = 99.9% (everyone gets same segments).
Origin (S3) only serves ~125 requests (0.1%) = trivial.
CloudFront Origin Shield: consolidates all PoP cache misses to ONE
request to S3. Only 1 S3 request per segment per PoP max.

BOTTLENECK 3: STORAGE COST (500 PB total)
─────────────────────────────────────────────────────────────────
S3 lifecycle policies:
  0-90 days:    S3 Standard ($0.023/GB) — hot content
  90-365 days:  S3 Infrequent Access ($0.0125/GB) — warm
  1yr+:         S3 Glacier ($0.004/GB) — cold
  2yr+ <100 views: DELETE (no audience, reclaim space)
Also: H.265 codec instead of H.264 → 50% smaller files at same quality.
Result: ~60% storage cost reduction vs naive approach.
```

---

## STEP 8 — TRADE-OFFS

*"Let me walk through the key architectural trade-offs I made and why."*

```
┌─────────────────────────────┬────────────────────────────┬──────────────────────────────────────────────────────────┐
│ DECISION                    │ CHOICE MADE                │ TRADE-OFF                                                │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Video storage format        │ HLS multi-bitrate (ABR)    │ Quality adapts per network vs. requires transcoding to   │
│                             │                            │ 4-5 resolutions (CPU-intensive upload pipeline)          │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ CDN strategy                │ Push to CDN on upload      │ Popular videos always at edge vs. storage cost for       │
│                             │                            │ videos with 0 views (use pull CDN for long-tail)         │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ View count storage          │ Redis INCR + write-back    │ Real-time view count, handles 10M views/min vs.          │
│                             │                            │ 5-min eventual consistency to MySQL                      │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Metadata DB                 │ MySQL                      │ ACID, normalized, complex queries (trending by region)   │
│                             │                            │ vs. needs sharding for 800M videos                       │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Video search                │ Elasticsearch              │ Full-text, geo, faceted search in one query vs.          │
│                             │                            │ eventual consistency (new video takes minutes to index)  │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Thumbnail generation        │ Async (extract frame at    │ Non-blocking upload vs. default thumbnail (frame 0) may  │
│                             │ upload time)               │ be black screen — creator should upload custom thumb     │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Comment system              │ Cassandra (partition by    │ Handles 500M comments/day vs. hot partition for viral    │
│                             │ video_id)                  │ videos — mitigated by read-replica + Redis top cache     │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Recommendation engine       │ Two-tower ML model         │ Personalized watch history + video embeddings vs. cold   │
│                             │                            │ start problem for new users and new videos               │
└─────────────────────────────┴────────────────────────────┴──────────────────────────────────────────────────────────┘
```

*"The most interesting video streaming trade-off is HLS vs. DASH. Both use segmented ABR streaming. HLS has better device support (native on iOS/Safari). DASH is an open standard with finer bitrate ladder control. YouTube uses DASH internally but wraps it in their custom format. For an interview: say HLS, explain ABR adaptation, and mention that segment size (2-10 seconds) trades startup latency for seek accuracy."*

---

## WHAT NOT TO SAY ✗

```
✗ "The backend receives the video upload, then sends to S3"
  → 2 GB × 8 uploads/sec = 16 GB/sec through your backend.
    Use presigned URLs — browser uploads directly to S3.

✗ "I'll transcode synchronously in the upload API response"
  → 10-minute transcoding blocks the API. User gets a timeout.
    Use Kafka for async processing. Return 202 Accepted immediately.

✗ "View counts write directly to MySQL on every request"
  → 11K writes/sec on a single row causes lock contention.
    Use Redis INCR + write-back batch to MySQL every 5 minutes.

✗ "CDN is optional — S3 can serve the video"
  → S3 is in ONE region. 1M concurrent viewers in India hitting
    Virginia S3 = 200ms latency + massive egress cost.
    CDN is non-negotiable.

✗ "Just use SQL LIKE for search"
  → 800M videos × SQL LIKE = full table scan. Use Elasticsearch.

✗ "No need to deduplicate views"
  → Page refreshes, bot traffic, and repeat loads would inflate
    counts instantly. 30-second threshold + cookie dedup is minimum.
```

---

## SENIOR TRAP QUESTIONS (15 YOE Level)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 1 — UPLOAD & PROCESSING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "What if two users upload the exact same video file?"
A: Duplicate detection via content hash.
   Before generating presigned URL:
   1. Client computes MD5 hash of file locally (before upload)
   2. Sends hash to backend: POST /videos/upload-url {contentHash}
   3. Backend checks: SELECT * FROM videos WHERE content_hash = ?
   4. If found → return existing videoId, skip upload entirely
   5. Save ~2 GB of S3 storage and 10 min of transcoding per dupe.
   Works for exact duplicates. Re-encoded/cropped copies are NOT
   caught by hash (need perceptual hashing / Content ID for that).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "The video processor transcodes halfway through 10,000 segments
   and crashes. Do you re-transcode from scratch?"
A: No. Each segment is independent. Encoder is idempotent:
   1. Each segment has a unique key: {videoId}_{segmentNumber}_{quality}
   2. Processor saves: { segmentKey, status: DONE/FAILED } in DB
   3. On crash: Kafka retries (not re-delivered — offset not committed)
   4. Processor checks which segments are DONE, skips them
   5. After 3 retries → DLQ → alert engineer
   6. Engineer re-triggers only FAILED segments via admin API
   Result: failure at segment 5000 → only re-encode from segment 5000.
   This is why Kafka + chunked encoding beats a monolithic job.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 2 — VIEW COUNT & CONSISTENCY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "What if Redis crashes during view count write-back?"
A: Two risks:
   1. Redis crashes BEFORE flush → lose buffered view counts.
      Fix: Redis AOF persistence (appends every write to disk).
      On restart, Redis replays AOF → counts restored.
   2. Redis crashes MID-flush (some counts flushed, some not).
      Fix: use idempotent batch: store {videoId, delta, batchId}
      in MySQL. On retry, check if batchId already applied. If yes, skip.
   Acceptable data loss: ~5 minutes of view counts is business
   decision. Even YouTube's view count lags by design.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "A video goes viral — 1M views in 1 hour. The CDN edge near
   the creator's city hasn't cached it yet. What happens?"
A: Called 'cache stampede' or 'thundering herd' on the CDN edge.
   1M users request the same uncached segment simultaneously.
   Without protection: 1M requests hit S3 in parallel → S3 throttled.
   Fix: CDN request collapsing (CloudFront does this by default).
   When 1000 users hit the same uncached segment:
   → CDN makes ONE request to S3 for that segment
   → Serves all 1000 users from that one response
   Also: Origin Shield — all PoPs consolidate behind one origin
   proxy. S3 never sees more than 1 concurrent request per segment.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 3 — SEARCH & RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "New video uploaded. When does it appear in search results?"
A: Near-real-time via a sync pipeline:
   1. Video status → READY event published to Kafka
   2. Elasticsearch Indexer consumer picks up the event
   3. Indexes: title, description, tags, channelName, uploadedAt
   4. Appears in search within ~1-5 seconds of going READY
   Alternative: CDC from MySQL (Debezium watches videos table,
   streams changes to Kafka). Either works. Kafka event is simpler
   since we already publish the READY event for notifications.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "New user — no watch history. How do recommendations work?"
A: Cold start problem. Three-phase approach:
   Phase 1 (0 views): Show trending videos globally + by region.
   Phase 2 (1-3 views): Show more from the same categories watched.
   Phase 3 (10+ views): Collaborative filtering kicks in:
     "Users who watched X also watched Y."
   Collaborative filtering (Spark ALS offline, nightly):
   → User-item matrix (users × videos watched)
   → Decompose into latent factors
   → Find users with similar taste vectors
   → Recommend videos those similar users watched
   Precomputed top-20 per user → stored in Redis (1hr TTL).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 4 — SECURITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "How do you prevent users from downloading premium/private videos?"
A: Two layers:
   1. Signed URLs: CDN segment URLs include a signature that
      expires in 24 hours. Even if a URL is shared, it stops working.
      Signature = HMAC(segmentPath + expiry, secret).
   2. Auth check at manifest level: GET /videos/{id}/play validates
      JWT + checks visibility (PRIVATE = only owner can access).
      If unauthorized, manifest URL is never returned.
   Note: For truly premium content (paid), add DRM (Widevine/FairPlay)
   on top — signed URLs prevent link sharing but not screen recording.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

QUICK SUMMARY — The 4 things that show 15 YOE thinking:
  1. Failure modes: "what happens WHEN processor crashes" not IF
  2. Race conditions: view count stampede, Redis crash recovery
  3. WHY decisions: presigned URL vs proxy upload, Redis vs MySQL
  4. Quantify: "Redis handles 1M writes/sec, MySQL 50K — that's
     why Redis for view counts"
```

---

## KEY NUMBERS — Memorize These

```
┌──────────────────────────────────┬──────────────────────────┐
│              METRIC              │  VALUE                   │
├──────────────────────────────────┼──────────────────────────┤
│ Daily Active Users               │ 100 million              │
│ Videos uploaded per minute       │ 500 hours                │
│ New storage per day              │ ~300 TB (with redundancy) │
│ Total storage (5 years)          │ ~500 PB                  │
│ CDN cache hit ratio              │ 90%                      │
│ Peak RPS (CDN segments)          │ ~30K                     │
│ View count writes/sec            │ ~11,500                  │
│ Video start latency target       │ < 200ms                  │
│ Search latency target            │ < 50ms                   │
│ Read/write ratio                 │ 100:1                    │
│ HLS segment duration             │ 6-10 seconds             │
│ Presigned URL TTL                │ 15 minutes               │
│ Recommendation cache TTL (Redis) │ 1 hour                   │
│ S3 Standard → IA lifecycle       │ 90 days                  │
│ S3 IA → Glacier lifecycle        │ 1 year                   │
└──────────────────────────────────┴──────────────────────────┘
```

---

*Study order: STEP 5 Architecture (15 min) → STEP 7 Upload Flow (10 min)
→ STEP 4 APIs (10 min) → STEP 2 Capacity (10 min) → Rapid Answer (5 min)*
