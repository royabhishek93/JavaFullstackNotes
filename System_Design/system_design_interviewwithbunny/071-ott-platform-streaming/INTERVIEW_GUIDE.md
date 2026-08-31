# OTT Platform — Interview Script
## Netflix / Amazon Prime / Hotstar
### Speak This Word-for-Word to Your Interviewer

> **Related:** [blog.md](blog.md) — full technical reference with deep-dives on transcoding, CDN architecture, DB schemas, capacity planning, and common interview Q&A.

> **How to use this:**
> **Step 1 — Read Big Picture** (section marked PAGE 1): burn the overview diagram into your head.
> **Step 2 — Read Glossary** (PAGE 2): know every term before the deep-dive.
> **Step 3 — Read Component Choices** (PAGE 3): know WHY each tech was chosen.
> **Step 4 — Read the Interview Script** (PAGE 4 onward): speak each step aloud 2-3 times.
>
> **Print tip:** Portrait A4 at 10pt monospace fits all diagrams. Glossary → print landscape if needed.

---

# ═══════════════ PAGE 1 — START HERE ═══════════════

## BIG PICTURE (Understand This Before Anything Else)

*Before reading any detail, burn this picture into your head.*

> **► STUDY this diagram, don't draw it ◄**
> Spend 5 minutes on this before reading anything else.
> Goal: close your eyes and trace the flow from "user presses Play" to "video starts."

```
┌─────────────────────────────────────────────────────────────────┐
│                    OTT PLATFORM — BIG PICTURE                    │
└─────────────────────────────────────────────────────────────────┘

WHO UPLOADS CONTENT?          WHO WATCHES CONTENT?
Backend team only             200 million subscribers
        │                              │
        ▼                              ▼
┌───────────────┐            ┌──────────────────┐
│  STUDIO FILE  │            │  CLIENT DEVICE   │
│  (100 GB raw) │            │  Phone / TV / Web│
└───────┬───────┘            └────────┬─────────┘
        │                             │ presses Play
        │ INGESTION PIPELINE          │
        ▼                             ▼
  Chunker Service            ┌──────────────────┐
  (splits into 10s pieces)   │   CDN EDGE       │◄── 95% of video
        │                    │   (near the user)│    served from here
        ▼                    └────────┬─────────┘
  Encoder Service                     │ cache miss only
  (makes 4K/1080p/720p/480p)          ▼
        │                    ┌──────────────────┐
        ▼                    │   API GATEWAY    │
  S3 Storage                 │   (traffic cop)  │
  (stores all video files)   └────────┬─────────┘
        │                             │
        │ manifest URL saved          ▼
        ▼                    ┌──────────────────┐
  Video DB (MongoDB)         │   MICROSERVICES  │
  (stores what to play)      │  User │ Sub │Play│
                             └────────┬─────────┘
                                      │
                             ┌────────▼─────────┐
                             │    DATABASES     │
                             │ MySQL │ Cassandra │
                             │ MongoDB │ Redis   │
                             └──────────────────┘

THE CORE FLOW IN ONE SENTENCE:
  User presses Play → API Gateway routes to Play Service
  → Play Service fetches manifest from MongoDB (cached in Redis)
  → Client uses manifest to pull video segments from CDN
  → CDN serves segments at the right quality for user's bandwidth
  → Video plays without buffering
```

---

## RAPID ANSWER — If You Only Have 5 Minutes

*Read this first. Understand the whole answer before going deep.*

```
"I'd design this OTT platform with five pieces:

1. USER + SUBSCRIPTION (MySQL + Kafka):
   Users register and pay for a plan (Basic/Standard/Premium).
   Payment goes via Stripe. On success, a Kafka event fires two
   consumers in parallel: one sends a welcome email, the other
   updates the user's subscription status in MySQL.
   Kafka is used so the payment flow is never blocked by a slow DB.

2. CONTENT INGESTION (S3 + Chunker + Kafka + Encoder):
   Backend team uploads a 100 GB master file to S3.
   Chunker Service splits it into 10-second segments and creates
   a manifest file (the table of contents for the video).
   Each chunk goes via Kafka to the Encoder, which makes four
   quality versions: 4K, 1080p, 720p, 480p.
   The manifest URL is stored in MongoDB (Video DB).

3. VIDEO STREAMING (MongoDB + Redis + CDN + ABR):
   User clicks Play → Play Service fetches manifest from MongoDB
   (Redis-cached for 1 hour) → returns manifest URL to client.
   Client measures bandwidth → requests segments from CDN at
   matching quality. Every 6-10 seconds it re-checks bandwidth
   and switches quality up or down. CDN serves 95% of traffic.
   This is Adaptive Bitrate Streaming (ABR) using HLS or DASH.

4. SEARCH (Elasticsearch + CDC):
   Elasticsearch for full-text search.
   MongoDB changes flow via a CDC pipeline (Debezium → Kafka)
   into Elasticsearch. Never query MongoDB directly for search.

5. SCALE:
   CDN handles 2.5 million segment requests/sec (95% cache hit).
   Cassandra handles 500K heartbeat writes/sec (watch progress).
   Redis atomic INCR enforces concurrent stream limits per plan."
```

---

# ═══════════════ PAGE 2 — GLOSSARY ═══════════════

## Terminology — Know These Before Reading Further

*Every term you will encounter in this guide, explained simply.*
*Print tip: if table wraps on your printer, switch to landscape orientation or 9pt font.*

```
┌──────────────────┬──────────────────────────────────────────────────────┐
│ Term             │ What It Means (Simply)                               │
├──────────────────┼──────────────────────────────────────────────────────┤
│ OTT              │ Over-The-Top. Video delivered over the internet,     │
│                  │ not via cable/satellite. Netflix, Prime = OTT.       │
├──────────────────┼──────────────────────────────────────────────────────┤
│ VOD              │ Video On Demand. Watch any video any time.           │
│                  │ Opposite of live TV (scheduled broadcast).           │
├──────────────────┼──────────────────────────────────────────────────────┤
│ CDN              │ Content Delivery Network. Servers placed around the  │
│                  │ world. When you watch Netflix in Mumbai, the video   │
│                  │ comes from a nearby CDN server, not from the US.     │
│                  │ Makes video fast. CloudFront (AWS) is a popular CDN. │
├──────────────────┼──────────────────────────────────────────────────────┤
│ ABR              │ Adaptive Bitrate. Automatically changes video quality │
│                  │ based on your internet speed. Slow internet = 480p.  │
│                  │ Fast internet = 4K. No buffering.                    │
├──────────────────┼──────────────────────────────────────────────────────┤
│ HLS              │ HTTP Live Streaming. Protocol by Apple. Videos split  │
│                  │ into chunks, served via HTTP. Uses .m3u8 files.      │
│                  │ Mandatory on iPhone/iPad/Safari.                     │
├──────────────────┼──────────────────────────────────────────────────────┤
│ DASH             │ Dynamic Adaptive Streaming over HTTP. Open standard. │
│                  │ Like HLS but faster quality switching. Uses .mpd.    │
│                  │ Used on Android, Web, Smart TV.                      │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Manifest File    │ A text file that lists all video chunks in order.    │
│                  │ Like a table of contents. Without it, the player     │
│                  │ doesn't know which segment comes next.               │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Segment / Chunk  │ A small piece of video, typically 6-10 seconds long. │
│                  │ A 2-hour movie = ~720 chunks. Player downloads       │
│                  │ one chunk at a time, plays them seamlessly.          │
├──────────────────┼──────────────────────────────────────────────────────┤
│ DRM              │ Digital Rights Management. Encrypts video so only    │
│                  │ paying subscribers can watch. Widevine (Google),     │
│                  │ FairPlay (Apple), PlayReady (Microsoft).             │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Transcoding /    │ Converting raw video into multiple formats and       │
│ Encoding         │ qualities (4K, 1080p, 720p, 480p). One source file  │
│                  │ → many output files for different devices/speeds.    │
├──────────────────┼──────────────────────────────────────────────────────┤
│ MySQL /          │ Relational databases. Store data in tables with rows │
│ PostgreSQL       │ and columns. Support ACID (no partial data loss).    │
│                  │ Good for payments, user accounts.                    │
├──────────────────┼──────────────────────────────────────────────────────┤
│ MongoDB          │ Document database. Stores data as JSON-like objects. │
│                  │ Flexible — each document can have different fields.  │
│                  │ Good for video metadata (movies ≠ series schemas).   │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Cassandra        │ NoSQL database built for massive write throughput.   │
│                  │ Can handle millions of writes/sec. Used for watch    │
│                  │ history (500K writes/sec from heartbeats).           │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Redis            │ In-memory key-value store. Sub-millisecond reads.    │
│                  │ Used for caching (manifests, sessions, tokens).      │
│                  │ Data lives in RAM — very fast, but limited size.     │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Kafka            │ Message queue / event bus. Service A publishes an    │
│                  │ event. Services B and C consume it independently.    │
│                  │ Decouples services so one slow service can't block   │
│                  │ another. Used here for payment events, video chunks. │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Elasticsearch    │ Search engine database. Excellent for full-text      │
│                  │ search (titles, descriptions, cast names). Much      │
│                  │ faster than SQL LIKE queries at scale.               │
├──────────────────┼──────────────────────────────────────────────────────┤
│ CDC              │ Change Data Capture. Listens for database changes    │
│ (Debezium)       │ and streams them elsewhere. Used to sync MongoDB     │
│                  │ changes into Elasticsearch automatically.            │
├──────────────────┼──────────────────────────────────────────────────────┤
│ S3               │ Amazon Simple Storage Service. Cheap, durable cloud  │
│                  │ storage. Perfect for storing large video files.      │
├──────────────────┼──────────────────────────────────────────────────────┤
│ API Gateway      │ The front door of the backend. Handles auth, rate    │
│                  │ limiting, and routes each request to the right       │
│                  │ microservice.                                        │
├──────────────────┼──────────────────────────────────────────────────────┤
│ JWT              │ JSON Web Token. A signed token the server gives on   │
│                  │ login. Client sends it on every request to prove     │
│                  │ identity. Expires in 15 minutes (access token).      │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Microservices    │ Architecture where each feature is a separate small  │
│                  │ service. User Service, Subscription Service, Play    │
│                  │ Service etc. Each can scale independently.           │
├──────────────────┼──────────────────────────────────────────────────────┤
│ I-frame          │ A complete video frame (not a delta). Segment        │
│ (Keyframe)       │ boundaries always land on I-frames. Client          │
│                  │ pre-fetches the next segment at the I-frame point.  │
└──────────────────┴──────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 3 — WHY EACH COMPONENT ═══════════════

## Component Choices — Why We Picked Each One

*The most common follow-up questions in interviews. Know these.*

```
┌────────────────────────────────────────────────────────────────────┐
│  COMPONENT          │  WHY THIS? NOT SOMETHING ELSE?               │
├─────────────────────┼──────────────────────────────────────────────┤
│                     │                                              │
│  MySQL / PostgreSQL │ WHY: User registration and payments need     │
│  (for Users +       │ ACID guarantees. If a payment row is written │
│   Payments)         │ halfway and the server crashes, we must not  │
│                     │ lose money or double-charge the user.        │
│                     │ MySQL gives us transactions — all-or-nothing.│
│                     │                                              │
│                     │ WHY NOT MongoDB: No multi-document ACID.     │
│                     │ WHY NOT Cassandra: No joins, no transactions.│
│                     │                                              │
├─────────────────────┼──────────────────────────────────────────────┤
│                     │                                              │
│  MongoDB            │ WHY: Video metadata has different shapes.    │
│  (for Video DB)     │ A MOVIE has {duration, director}.            │
│                     │ A SERIES has {seasons → episodes[]}.         │
│                     │ A LIVE EVENT has {scheduledAt, streamUrl}.   │
│                     │ MongoDB's flexible schema handles all three. │
│                     │ Also stores the manifest URL as a field.     │
│                     │                                              │
│                     │ WHY NOT MySQL: Would need 5+ joined tables   │
│                     │ just to represent one series. Slow at reads. │
│                     │                                              │
├─────────────────────┼──────────────────────────────────────────────┤
│                     │                                              │
│  Cassandra          │ WHY: Watch history gets 500K writes/sec      │
│  (for Watch         │ (15M streams × heartbeat every 30s).        │
│   History)          │ MySQL handles ~50K writes/sec max.           │
│                     │ Cassandra is built for exactly this —        │
│                     │ millions of writes/sec, linear scale.        │
│                     │ We partition by profileId so all progress    │
│                     │ for one user is on one node = fast reads.    │
│                     │                                              │
│                     │ WHY NOT MySQL: Dies at 500K writes/sec.      │
│                     │ WHY NOT MongoDB: Also not built for this     │
│                     │ write volume.                                │
│                     │                                              │
├─────────────────────┼──────────────────────────────────────────────┤
│                     │                                              │
│  Redis              │ WHY: Sub-millisecond reads from RAM.         │
│  (for Cache +       │ Used for: manifest URL cache (1hr TTL),      │
│   Sessions)         │ session tokens (15min TTL), concurrent        │
│                     │ stream counter (atomic INCR), trending list.  │
│                     │ If Play Service hits MongoDB every time →    │
│                     │ ~5ms per call. Redis brings this to ~0.1ms. │
│                     │                                              │
│                     │ WHY NOT MongoDB/MySQL for this: Too slow.    │
│                     │ Redis is not persistent (lost on restart) —  │
│                     │ fine for cache, not fine for source of truth.│
│                     │                                              │
├─────────────────────┼──────────────────────────────────────────────┤
│                     │                                              │
│  Elasticsearch      │ WHY: Full-text search on 10,000 titles.      │
│  (for Search)       │ SQL LIKE queries ("title LIKE '%action%'")   │
│                     │ scan the entire table — slow at 100K req/sec.│
│                     │ Elasticsearch uses inverted indexes:         │
│                     │ "action" → [titleId1, titleId5, titleId9]   │
│                     │ Look up in microseconds, not milliseconds.   │
│                     │ Also supports fuzzy match (typos), filters,  │
│                     │ sorting by rating/popularity.                │
│                     │                                              │
│                     │ WHY NOT query MongoDB directly: Not optimized│
│                     │ for full-text. Slow at scale.                │
│                     │                                              │
├─────────────────────┼──────────────────────────────────────────────┤
│                     │                                              │
│  Kafka              │ WHY: Decouples services. After payment       │
│  (Message Queue)    │ succeeds, we need to: (1) send welcome email │
│                     │ AND (2) update User DB. If we call both      │
│                     │ synchronously, a slow email server blocks    │
│                     │ the payment response. With Kafka, we publish │
│                     │ one event and two consumers handle it        │
│                     │ independently in parallel.                   │
│                     │ Also: if email service crashes, Kafka        │
│                     │ replays the event when it recovers.          │
│                     │                                              │
│                     │ WHY NOT direct REST calls: Tight coupling.   │
│                     │ One slow/crashed service breaks the chain.   │
│                     │                                              │
├─────────────────────┼──────────────────────────────────────────────┤
│                     │                                              │
│  CDN                │ WHY: 15M concurrent streams × 1 segment      │
│  (CloudFront)       │ per 6s = 2.5M requests/sec. S3 alone cannot │
│                     │ handle this. CDN caches segments at 200+     │
│                     │ edge servers worldwide. User in Mumbai gets  │
│                     │ video from Mumbai PoP, not Virginia (5ms vs  │
│                     │ 200ms). CDN absorbs 95% of all video traffic.│
│                     │                                              │
│                     │ WHY NOT just serve from S3: S3 is in one     │
│                     │ region. High latency globally. No scale.     │
│                     │                                              │
├─────────────────────┼──────────────────────────────────────────────┤
│                     │                                              │
│  S3                 │ WHY: We need to store 500 PB of video files. │
│  (Object Storage)   │ S3 is designed for massive file storage:     │
│                     │ cheap (pennies per GB), durable (11 9s),     │
│                     │ unlimited scale, integrates with CloudFront. │
│                     │                                              │
│                     │ WHY NOT a regular database: Databases store  │
│                     │ structured data (rows/columns), not binary   │
│                     │ video blobs. S3 is purpose-built for files.  │
│                     │                                              │
├─────────────────────┼──────────────────────────────────────────────┤
│                     │                                              │
│  HLS / DASH         │ WHY: You cannot stream a raw MP4 file         │
│  (Streaming         │ efficiently. It's too large, no quality      │
│   Protocols)        │ switching, no seeking. HLS/DASH split the    │
│                     │ video into chunks, create manifest files,    │
│                     │ and enable the client to switch quality per  │
│                     │ chunk based on bandwidth. Result: no         │
│                     │ buffering regardless of internet speed.      │
│                     │                                              │
│                     │ WHY NOT just progressive MP4 download: Can't │
│                     │ switch quality mid-stream. Slow start.       │
│                     │                                              │
├─────────────────────┼──────────────────────────────────────────────┤
│                     │                                              │
│  Microservices      │ WHY: 200M users cannot be served by one      │
│  (Architecture)     │ server. Microservices let each component     │
│                     │ scale independently. Play Service needs      │
│                     │ 500 instances during peak. Auth Service      │
│                     │ needs only 10. With microservices, you scale │
│                     │ only what needs scaling.                     │
│                     │                                              │
│                     │ WHY NOT monolith: One server handles all     │
│                     │ traffic. Cannot scale video streaming without│
│                     │ also scaling user registration unnecessarily.│
│                     │                                              │
└─────────────────────┴──────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 4+ — FULL INTERVIEW SCRIPT ═══════════════

---

## OPENING — When Interviewer Says "Design Netflix/Hotstar"

*"Great question. Before I jump into the design, let me ask a few clarifying
questions to make sure I'm solving the right problem."*

---

## STEP 1 — Requirements Gathering (Speak This Out Loud)

*"So the first thing I want to understand is — what features are we building?
I'm assuming this is an OTT platform like Netflix where users pay for
a subscription and then watch content. Let me just confirm a few things..."*

```
YOU ASK:                        INTERVIEWER SAYS:
────────────────────────────────────────────────────────────
"Can users upload videos?"   →  "No, only backend team uploads content"
"VOD only or live too?"      →  "VOD for now, mention live as extension"
"Do we need a recommendation
 engine?"                    →  "Keep it out of scope"
"Offline downloads?"         →  "Not required"
"Single region or global?"   →  "Global — Netflix scale"
────────────────────────────────────────────────────────────
```

*"Perfect. So let me summarize what I'm building..."*

```
┌─────────────────────────────────────────────────────────┐
│               REQUIREMENTS SUMMARY                       │
├─────────────────────────────────────────────────────────┤
│  FUNCTIONAL (what we build):                            │
│  1. User registers and opts for a subscription plan     │
│  2. User searches movies/shows by title or genre        │
│  3. User plays video at 480p / 720p / 1080p / 4K        │
│                                                         │
│  OUT OF SCOPE: Recommendation engine, uploads by user,  │
│               offline downloads, live streaming         │
├─────────────────────────────────────────────────────────┤
│  NON-FUNCTIONAL (how it behaves):                       │
│  Scale:     200 million subscribers, 10,000 videos      │
│  CAP:       HIGH AVAILABILITY >> Consistency            │
│             Exception: Payment = must be CONSISTENT     │
│  Latency:   ZERO buffering while video is playing       │
│  Arch:      Microservices (can't serve 200M on 1 server)│
└─────────────────────────────────────────────────────────┘
```

*"One important thing to note — unlike YouTube, users cannot upload content here.
Our backend team uploads content. That changes the design significantly because
we have full control over the video processing pipeline and we have time to process
before publishing."*

---

## STEP 2 — Capacity Estimation (Speak This Out Loud)

*"Let me do a quick back-of-envelope calculation so we know what we're building for..."*

```
STORAGE:
──────────────────────────────────────────────────────────
"We have 10,000 videos at 1 hour each.
 Each video is encoded in 5 quality levels.
 Average bitrate across qualities = about 10 Mbps.

 10,000 × 5 qualities × 3,600 seconds × 10 Mbps / 8
 = roughly 450 TB for video files.
 With redundancy → about 500 PB total."

BANDWIDTH:
──────────────────────────────────────────────────────────
"At peak, Netflix has about 15 million concurrent streams.
 Average bitrate = 10 Mbps per stream.

 15 million × 10 Mbps = 150 Terabits per second.
 
 That's about 15% of all internet traffic at peak!
 This is why CDN is not optional — it's the core of the design."

WRITE LOAD:
──────────────────────────────────────────────────────────
"Every active stream sends a heartbeat every 30 seconds.
 15 million streams ÷ 30 = 500,000 writes per second
 just for tracking watch progress. Needs Cassandra."
```

*"So to summarize the scale — 500 PB storage, 150 Tbps bandwidth (CDN absorbs 95%),
and 500K writes per second for watch history. Now let me draw the architecture..."*

---

## STEP 3 — Core Entities (Speak This Out Loud)

*"Before I get to the APIs, let me identify the core entities in our system..."*

```
┌──────────────────────────────────────────────────────────────┐
│                    CORE ENTITIES                              │
├──────────────────┬───────────────────────────────────────────┤
│ Entity           │ What it holds                             │
├──────────────────┼───────────────────────────────────────────┤
│ User             │ name, email, password, country_code       │
│ UserMeta         │ subscription_status, expiry_date, user_id │
│ SubscriptionPlan │ plan_id, name, price, validity, currency  │
│ Video            │ video_id, title, description, genre       │
│ VideoMetadata    │ manifest_url, thumbnails, duration        │
│ WatchProgress    │ profile_id, video_id, position_sec        │
└──────────────────┴───────────────────────────────────────────┘
```

---

## STEP 4 — API Design (Speak This Out Loud)

*"Now let me design the APIs. I always do this as a direct mapping from
functional requirements — one requirement, one or more endpoints."*

### Requirement 1: User Registration + Subscription

*"For user onboarding, I need three endpoints..."*

```
┌────────────────────────────────────────────────────────────────────┐
│                     USER + SUBSCRIPTION APIs                        │
├────────────┬───────────────────────────────┬───────────────────────┤
│ Method     │ Endpoint                      │ Purpose               │
├────────────┼───────────────────────────────┼───────────────────────┤
│ POST       │ /api/v1/auth/register         │ Create new account    │
│ POST       │ /api/v1/auth/login            │ Login → returns JWT   │
│ POST       │ /api/v1/auth/logout           │ Revoke refresh token  │
├────────────┼───────────────────────────────┼───────────────────────┤
│ GET        │ /api/v1/subscriptions/plans   │ List all plans        │
│ POST       │ /api/v1/subscriptions         │ Subscribe to a plan   │
│ PUT        │ /api/v1/subscriptions/cancel  │ Cancel subscription   │
└────────────┴───────────────────────────────┴───────────────────────┘

POST /api/v1/auth/register
  Request Body:
  {
    "name":     "Abhishek Roy",
    "email":    "abhi@email.com",
    "password": "hashed_on_client",
    "country":  "IN"
  }
  Response 201:
  {
    "userId":       "uuid-123",
    "accessToken":  "eyJ...",   ← JWT, 15 min TTL
    "refreshToken": "eyJ..."    ← JWT, 30 day TTL
  }

GET /api/v1/subscriptions/plans
  Response 200:
  [
    { "planId": "basic",    "price": 149,  "maxStreams": 1, "maxRes": "HD"  },
    { "planId": "standard", "price": 499,  "maxStreams": 2, "maxRes": "FHD" },
    { "planId": "premium",  "price": 649,  "maxStreams": 4, "maxRes": "UHD" }
  ]

POST /api/v1/subscriptions
  Request Body:
  {
    "userId":              "uuid-123",
    "planId":              "premium",
    "paymentMethodToken":  "tok_stripe_xxx"  ← from Stripe.js
  }
  Response 201:
  {
    "subscriptionId": "sub-uuid",
    "status":         "ACTIVE",
    "expiresAt":      "2025-08-21"
  }
```

### Requirement 2: Search + Browse

*"For search, I need two endpoints — one to search, one to get full details
of a specific title once the user clicks on it..."*

```
┌────────────────────────────────────────────────────────────────────┐
│                       SEARCH + BROWSE APIs                          │
├────────────┬───────────────────────────────┬───────────────────────┤
│ Method     │ Endpoint                      │ Purpose               │
├────────────┼───────────────────────────────┼───────────────────────┤
│ GET        │ /api/v1/search                │ Search by title/genre │
│ GET        │ /api/v1/videos/{videoId}      │ Get full metadata     │
└────────────┴───────────────────────────────┴───────────────────────┘

GET /api/v1/search?q=action&genre=thriller&page=1&limit=20
  Response 200:                    ← paginated — MUST mention this
  {
    "page": 1,
    "total": 147,
    "results": [
      {
        "videoId":      "vid-abc",
        "title":        "Extraction 2",
        "genre":        ["action", "thriller"],
        "thumbnail":    "https://cdn.../thumb.jpg",  ← partial data only
        "rating":       8.2,
        "releaseYear":  2023
      },
      ...
    ]
  }
  NOTE: Returns PARTIAL data only (no manifest, no full description).
        Full detail fetched separately when user clicks a title.

GET /api/v1/videos/{videoId}
  Response 200:
  {
    "videoId":     "vid-abc",
    "title":       "Extraction 2",
    "description": "Tyler Rake is back...",
    "cast":        ["Chris Hemsworth", ...],
    "duration":    "2h 3m",
    "genres":      ["action", "thriller"],
    "maturity":    "18+",
    "seasons":     null,            ← null for movies
    "thumbnail":   "https://cdn...",
    "backdrop":    "https://cdn..."
  }
```

### Requirement 3: Play Video

*"The play endpoint is the most important one. This is what kicks off streaming..."*

```
┌────────────────────────────────────────────────────────────────────┐
│                         PLAY APIs                                   │
├────────────┬───────────────────────────────┬───────────────────────┤
│ Method     │ Endpoint                      │ Purpose               │
├────────────┼───────────────────────────────┼───────────────────────┤
│ POST       │ /api/v1/stream/play           │ Initiate playback     │
│ POST       │ /api/v1/stream/heartbeat      │ Update watch position │
│ POST       │ /api/v1/stream/stop           │ End stream session    │
└────────────┴───────────────────────────────┴───────────────────────┘

POST /api/v1/stream/play
  Headers:  { Authorization: "Bearer eyJ..." }
  Request:
  {
    "videoId":          "vid-abc",
    "episodeId":        null,               ← null for movies
    "profileId":        "prof-123",
    "preferredQuality": "1080P",
    "drmSystem":        "widevine"          ← client tells us its DRM
  }
  Response 200:
  {
    "manifestUrl":      "https://cdn.../vid-abc/master.m3u8",
    "licenseServerUrl": "https://drm.../license",
    "drmToken":         "eyJ...",
    "resumeAt":         1234,               ← seconds (continue watching)
    "sessionId":        "sess-uuid"         ← for heartbeat calls
  }

POST /api/v1/stream/heartbeat      ← called every 30 seconds while watching
  {
    "sessionId":       "sess-uuid",
    "profileId":       "prof-123",
    "videoId":         "vid-abc",
    "positionSeconds": 1264
  }
  Response: 204 No Content

POST /api/v1/stream/stop
  { "sessionId": "sess-uuid", "finalPosition": 3601 }
  Response: 204 No Content
```

*"Now that we have the APIs, let me draw the high-level architecture..."*

---

### Additional Standard APIs — Complete the API Surface

*"A few more endpoints are needed to complete the platform: watchlist, personalised
recommendations, content rating, the continue-watching read path, and the admin
ingestion entry point."*

```
┌────────────────────────────────────────────────────────────────────┐
│                        WATCHLIST APIs                               │
├────────────┬───────────────────────────────┬───────────────────────┤
│ Method     │ Endpoint                      │ Purpose               │
├────────────┼───────────────────────────────┼───────────────────────┤
│ GET        │ /api/v1/watchlist             │ Fetch user's My List  │
│ POST       │ /api/v1/watchlist/{videoId}   │ Add title to My List  │
│ DELETE     │ /api/v1/watchlist/{videoId}   │ Remove from My List   │
└────────────┴───────────────────────────────┴───────────────────────┘

GET /api/v1/watchlist
  Headers:  { Authorization: "Bearer eyJ..." }
  Response 200:
  {
    "items": [
      {
        "videoId":   "vid-abc",
        "title":     "Extraction 2",
        "thumbnail": "https://cdn.../thumb.jpg",
        "type":      "MOVIE",
        "addedAt":   "2025-08-01T10:00:00Z"
      }
    ]
  }

POST /api/v1/watchlist/{videoId}
  Headers:  { Authorization: "Bearer eyJ..." }
  Response 201:  { "videoId": "vid-abc", "message": "Added to watchlist" }

DELETE /api/v1/watchlist/{videoId}
  Headers:  { Authorization: "Bearer eyJ..." }
  Response 204 No Content
```

> **WHY WATCHLIST?** Users curate a personal list of titles to watch later ("My List" / bookmarks). Write volume is low (explicit user action), so MySQL (userId + videoId + addedAt) is fine here. GET powers the "My List" screen; POST/DELETE fire when the user clicks the bookmark icon on a title card. Without these, the platform has no "save for later" feature — a standard OTT UX expectation.

```
┌────────────────────────────────────────────────────────────────────┐
│                   RECOMMENDATIONS API                               │
├────────────┬───────────────────────────────┬───────────────────────┤
│ Method     │ Endpoint                      │ Purpose               │
├────────────┼───────────────────────────────┼───────────────────────┤
│ GET        │ /api/v1/recommendations       │ Personalised title row│
└────────────┴───────────────────────────────┴───────────────────────┘

GET /api/v1/recommendations?limit=20
  Headers:  { Authorization: "Bearer eyJ..." }
  Response 200:
  {
    "items": [
      {
        "videoId":   "vid-xyz",
        "title":     "Squid Game",
        "genre":     ["thriller", "drama"],
        "thumbnail": "https://cdn.../thumb.jpg",
        "score":     0.94     ← ML relevance score (internal, not shown to user)
      }
    ],
    "cachedAt": "2025-08-21T09:00:00Z"   ← Redis TTL 24 hrs
  }
```

> **WHY RECOMMENDATIONS?** The ML recommendation engine (collaborative filtering + content-based, described in STEP 10) pre-computes a ranked list per user and caches it in Redis with a 24-hour TTL. This endpoint is the delivery path — essentially a single Redis GET keyed by userId. Without it, the ML output has nowhere to go. The `score` field is returned so clients can decide display order, but is never shown in the UI.

```
┌────────────────────────────────────────────────────────────────────┐
│                  CONTENT RATING API                                 │
├────────────┬───────────────────────────────┬───────────────────────┤
│ Method     │ Endpoint                      │ Purpose               │
├────────────┼───────────────────────────────┼───────────────────────┤
│ POST       │ /api/v1/videos/{videoId}/rating│ Rate a title         │
└────────────┴───────────────────────────────┴───────────────────────┘

POST /api/v1/videos/{videoId}/rating
  Headers:  { Authorization: "Bearer eyJ..." }
  Request Body:
  {
    "rating": 4     ← integer 1–5; or thumbs-up/down: 1 | -1
  }
  Response 200:
  {
    "videoId":      "vid-abc",
    "userRating":   4,
    "avgRating":    8.2,
    "totalRatings": 142300
  }
```

> **WHY CONTENT RATING?** Ratings are a strong ML training signal (a 5-star rating carries more weight than a passive watch). They also power the `rating` field returned by GET /api/v1/search and drive the `sort by rating` in Elasticsearch queries. Written to a MySQL ratings table (userId, videoId, rating, timestamp) with an async aggregate update. One endpoint that feeds both search ranking and the recommendation engine.

```
┌────────────────────────────────────────────────────────────────────┐
│                  WATCH HISTORY (READ) API                           │
├────────────┬───────────────────────────────┬───────────────────────┤
│ Method     │ Endpoint                      │ Purpose               │
├────────────┼───────────────────────────────┼───────────────────────┤
│ GET        │ /api/v1/watch-history         │ "Continue Watching" row│
└────────────┴───────────────────────────────┴───────────────────────┘

GET /api/v1/watch-history?limit=20
  Headers:  { Authorization: "Bearer eyJ..." }
  Response 200:
  {
    "items": [
      {
        "videoId":         "vid-abc",
        "title":           "Extraction 2",
        "thumbnail":       "https://cdn.../thumb.jpg",
        "positionSeconds": 1264,
        "durationSeconds": 7380,
        "percentDone":     17.1,
        "lastWatchedAt":   "2025-08-20T22:15:00Z"
      }
    ]
  }
```

> **WHY WATCH HISTORY (GET)?** POST /api/v1/stream/heartbeat already WRITES progress to Cassandra every 30 seconds. This endpoint READS it back to power the "Continue Watching" row on the home screen. It executes the Cassandra query shown in the schema section: `SELECT * FROM watch_progress WHERE profile_id = ? ORDER BY last_watched DESC LIMIT 20`. Without this endpoint, watch progress is stored but never surfaced — the resume feature works on Play but the home screen has no "Continue Watching" row.

```
┌────────────────────────────────────────────────────────────────────┐
│               ADMIN — CONTENT INGESTION API                         │
├────────────┬───────────────────────────────┬───────────────────────┤
│ Method     │ Endpoint                      │ Purpose               │
├────────────┼───────────────────────────────┼───────────────────────┤
│ POST       │ /api/v1/content               │ Trigger ingest pipeline│
│ PUT        │ /api/v1/content/{videoId}     │ Update title metadata │
│ DELETE     │ /api/v1/content/{videoId}     │ Unpublish / remove    │
└────────────┴───────────────────────────────┴───────────────────────┘

POST /api/v1/content
  Headers:  { Authorization: "Bearer eyJ...", X-Role: "ADMIN" }
  Request Body:
  {
    "title":       "Extraction 3",
    "type":        "MOVIE",                ← MOVIE | SERIES | LIVE
    "genre":       ["action", "thriller"],
    "cast":        ["Chris Hemsworth"],
    "director":    "Sam Hargrave",
    "releaseYear": 2026,
    "maturity":    "18+",
    "country":     ["IN", "US", "GB"],     ← geo availability list
    "s3RawKey":    "raw/extraction3.mov"   ← already uploaded to S3
  }
  Response 202 Accepted:            ← 202 not 201 — processing is async
  {
    "videoId": "vid-new-123",
    "status":  "PROCESSING",        ← Chunker + Encoder pipeline starts
    "message": "Ingestion pipeline triggered"
  }
```

> **WHY ADMIN CONTENT INGESTION?** The content pipeline (S3 → Chunker → Kafka → Encoder → MongoDB) is described in STEP 5, but it needs an API entry point. This endpoint: (1) creates a video record in MongoDB with status=PROCESSING, (2) publishes an event to Kafka to kick off the Chunker service, and (3) returns **202 Accepted** — not 201 — because transcoding takes minutes and completes asynchronously. The 202 vs 201 distinction is a strong interview signal: it shows you understand async pipeline design. Admin-only — enforced via role check in the API Gateway.

---

## STEP 5 — High-Level Architecture (Draw on Whiteboard)

*"Let me draw this out. There are two main flows — the USER watching flow,
and the CONTENT INGESTION flow by the backend team. I'll start with the user flow."*

> **► DRAW THIS on the whiteboard ◄**
> Start with two boxes: CLIENT and CDN. Add API Gateway below CDN.
> Fan out to 4 services. Add databases under each service.
> Draw the Kafka bus for payment flow. Then draw ingestion pipeline separately.

---

WHY THE CONTENT DELIVERY PIPELINE EXISTS? (Beginner Explanation)
  Think of uploading a movie like submitting a manuscript to a publisher.
  You send the raw 800-page manuscript (the 100 GB master video file).
  The publisher's team chops it into chapters (10-second segments),
  prints it in hardcover/paperback/ebook/pocket editions (4K/1080p/720p/480p),
  creates a table of contents (the manifest file listing every segment in order),
  and ships copies to bookstores worldwide (the CDN edge servers).
  Only THEN is the book "published" and available for readers (subscribers) to open instantly.
  The pipeline: Upload to S3 → Chunker splits into segments → Kafka queues each chunk
  → Encoder makes 4 quality versions → S3 stores all encoded files
  → MongoDB records the manifest URL so the Play Service can find it.
  Problem it solves: a 100 GB raw file must become millions of playable chunks before anyone watches.
  Without it: you would have to do all of this manually for each of 10,000 videos.

---

```
                        ╔══════════════════════════════════════╗
                        ║         COMPLETE ARCHITECTURE         ║
                        ╚══════════════════════════════════════╝

════════════════════════════════════════════════════════════════════════
  USER FLOW  (how a viewer watches content)
════════════════════════════════════════════════════════════════════════

┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT DEVICES                             │
│       📱 Mobile      💻 Web       📺 Smart TV      🎮 Console    │
└─────────────────────────────┬────────────────────────────────────┘
                              │  HTTPS requests
                              │
                 ┌────────────▼────────────┐
                 │      CDN EDGE LAYER      │◄── Video segments served HERE
                 │  CloudFront / Akamai    │    (95% of all video traffic)
                 │  200+ global PoPs       │    TTL: 7 days (immutable)
                 └────────────┬────────────┘
                              │ cache miss only (~5%)
                 ┌────────────▼────────────┐
                 │   API GATEWAY (Kong)     │
                 │  ✓ JWT Auth validation  │
                 │  ✓ Rate limiting        │
                 │  ✓ Request routing      │
                 │  ✓ Load balancing       │
                 │    (Round Robin)        │
                 └──┬──────┬──────┬───┬───┘
                    │      │      │   │
          ┌─────────┘  ┌───┘  ┌──┘   └──────────────┐
          │            │      │                       │
          ▼            ▼      ▼                       ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐  ┌──────────────────┐
   │   USER   │ │SUBSCRIPT-│ │  SEARCH  │  │  PLAY / STREAM   │
   │ SERVICE  │ │  ION     │ │ SERVICE  │  │    SERVICE       │
   └────┬─────┘ │ SERVICE  │ └────┬─────┘  └────────┬─────────┘
        │       └────┬─────┘      │                  │
        ▼            │            ▼                  ▼
  ┌──────────┐       │     ┌──────────────┐   ┌──────────────┐
  │ User DB  │       │     │ Elasticsearch│   │  Video DB    │
  │(PostgreSQL│      │     │  (Search     │   │ (MongoDB)    │
  │  MySQL)  │       │     │   Index)     │   │ stores       │
  └──────────┘       │     └──────▲───────┘   │ manifest URL │
                     │            │           └──────┬───────┘
                     │        CDC Pipeline           │
                     │        (Debezium)             │ manifest
                     │            │                  │ cached in
                     │     ┌──────┴──────┐           ▼
                     │     │  Video DB   │     ┌──────────┐
                     │     │ (MongoDB)   │     │  Redis   │
                     │     └─────────────┘     │ (Cache)  │
                     │                         └──────────┘
                     │
                     ▼
              ┌──────────────┐      ┌─────────────────┐
              │   PAYMENT    │─────▶│ Payment Gateway │
              │   SERVICE    │      │ (Stripe/Razorpay│
              └──────┬───────┘      └─────────────────┘
                     │
                     ▼ Kafka Event: subscription.created
              ┌──────────────────────────────────┐
              │          KAFKA BROKER            │
              └──────────────┬───────────────────┘
                       ┌─────┴──────┐
                       ▼            ▼
              ┌──────────────┐ ┌───────────────────┐
              │NOTIFICATION  │ │ CONSUMER SERVICE  │
              │SERVICE       │ │ (updates User DB) │
              │(sends email) │ └───────────────────┘
              └──────────────┘

════════════════════════════════════════════════════════════════════════
  CONTENT INGESTION FLOW  (how backend team uploads content)
════════════════════════════════════════════════════════════════════════

  ┌────────────┐
  │ BACKEND    │  (NOT the end user — internal team only)
  │ TEAM       │
  └─────┬──────┘
        │ uploads raw video (100 GB master file)
        ▼
  ┌───────────────┐    ┌─────────────────────────────────┐
  │ S3 RAW BUCKET │───▶│        CHUNKER SERVICE          │
  │ (master.mov)  │    │                                 │
  └───────────────┘    │  1. Splits into 2-10s segments  │
                       │  2. Creates MANIFEST FILE        │
                       │     HLS  →  .m3u8               │
                       │     DASH →  .mpd                │
                       │  3. Pushes chunks to Kafka       │
                       └──────────────┬──────────────────┘
                                      │ Kafka: "video-chunks"
                                      ▼
                       ┌─────────────────────────────────┐
                       │       VIDEO ENCODER SERVICE     │
                       │                                 │
                       │  For each chunk → 4 variants:  │
                       │  ┌──────┬───────┬──────┬──────┐ │
                       │  │  4K  │1080p  │ 720p │ 480p │ │
                       │  │H.265 │H.264  │H.264 │H.264 │ │
                       │  │.mp4/ │.mp4/  │.mp4/ │.mp4/ │ │
                       │  │ .ts  │ .ts   │ .ts  │ .ts  │ │
                       │  └──────┴───────┴──────┴──────┘ │
                       └──────────────┬──────────────────┘
                                      │ encoded segments
                                      ▼
                       ┌─────────────────────────────────┐
                       │      S3 ENCODED BUCKET          │
                       │  title-123/4K/seg001.ts          │
                       │  title-123/1080p/seg001.ts       │
                       │  title-123/720p/seg001.ts        │
                       │  title-123/manifest.m3u8         │
                       │  title-123/manifest.mpd          │
                       └──────────────┬──────────────────┘
                                      │ save manifest URL
                                      ▼
                       ┌─────────────────────────────────┐
                       │         VIDEO DB (MongoDB)       │
                       │  { titleId, manifestUrl, status }│
                       └─────────────────────────────────┘
                                      │ CDC → Elasticsearch
                                      ▼
                       ┌─────────────────────────────────┐
                       │         ELASTICSEARCH           │
                       │  (indexed: title, genre, cast)  │
                       └─────────────────────────────────┘
```

---

> **► DRAW THIS on the whiteboard ◄**

## SEQUENCE DIAGRAM — VIDEO STREAMING (Happy Path)

```
  User App     CDN Edge       API Gateway    Streaming Svc    DRM Service    S3 + Transcoder
     │               │              │               │               │               │
     │ GET /videos/  │              │               │               │               │
     │ {id}/stream   │              │               │               │               │
     │──────────────▶│              │               │               │               │
     │               │ cache miss   │               │               │               │
     │               │─────────────▶│               │               │               │
     │               │              │ Auth + check  │               │               │
     │               │              │ subscription  │               │               │
     │               │              │──────────────▶│               │               │
     │               │              │               │ Check DRM     │               │
     │               │              │               │ license valid │               │
     │               │              │               │──────────────▶│               │
     │               │              │               │◀──────────────│               │
     │               │              │               │  {license_ok} │               │
     │               │              │               │               │               │
     │               │              │               │ Generate      │               │
     │               │              │               │ presigned HLS │               │
     │               │              │               │ manifest URL  │               │
     │               │              │               │──────────────────────────────▶│
     │               │              │               │◀──────────────────────────────│
     │               │              │ {manifestUrl, │               │               │
     │               │              │  drmToken}    │               │               │
     │◀──────────────│◀─────────────│               │               │               │
     │               │              │               │               │               │
     │ GET manifest  │              │               │               │               │
     │ (.m3u8)       │              │               │               │               │
     │──────────────▶│              │               │               │               │
     │◀──────────────│ {HLS playlist│               │               │               │
     │               │  resolutions}│               │               │               │
     │               │              │               │               │               │
     │ GET segment   │              │               │               │               │
     │ (video chunk) │              │               │               │               │
     │──────────────▶│              │               │               │               │
     │◀──────────────│ {.ts segment}│               │               │               │
     │               │ CDN caches   │               │               │               │
     │               │ at edge PoP  │               │               │               │
     │               │              │               │               │               │
     │ (Player adapts│              │               │               │               │
     │  quality based│              │               │               │               │
     │  on bandwidth)│              │               │               │               │
```

## SEQUENCE DIAGRAM — VIDEO UPLOAD (Content Creator)

```
  Creator App   Upload Service    S3             Kafka       Transcoder     DB
      │               │             │              │               │          │
      │ POST /upload  │             │              │               │          │
      │ INIT          │             │              │               │          │
      │──────────────▶│             │              │               │          │
      │               │ Presign S3  │              │               │          │
      │               │ multi-part  │              │               │          │
      │               │────────────▶│              │               │          │
      │ {uploadUrls}  │◀────────────│              │               │          │
      │◀──────────────│             │              │               │          │
      │               │             │              │               │          │
      │ PUT parts     │             │              │               │          │
      │ (parallel)    │             │              │               │          │
      │───────────────────────────▶│              │               │          │
      │◀───────────────────────────│              │               │          │
      │               │             │              │               │          │
      │ POST /commit  │             │              │               │          │
      │──────────────▶│             │              │               │          │
      │               │ INSERT video│              │               │          │
      │               │ status=PROC │              │               │          │
      │               │────────────────────────────────────────────────────▶ │
      │               │             │              │               │          │
      │               │ publish     │              │               │          │
      │               │ video.uploaded             │               │          │
      │               │──────────────────────────▶│               │          │
      │ 202 {videoId} │             │              │               │          │
      │◀──────────────│             │              │               │          │
      │               │             │              │               │          │
      │               │             │              │ Transcoder    │          │
      │               │             │              │ consumes      │          │
      │               │             │              │──────────────▶│          │
      │               │             │              │               │ Transcode│
      │               │             │              │               │ 1080p,   │
      │               │             │              │               │ 720p,    │
      │               │             │              │               │ 480p,    │
      │               │             │              │               │ 360p HLS │
      │               │             │              │               │──────────▶
      │               │             │              │               │          │
      │               │             │              │               │ UPDATE   │
      │               │             │              │               │ status=  │
      │               │             │              │               │ READY    │
      │               │             │              │               │──────────▶
```

---

## STEP 6 — Database Schema Design (Draw on Whiteboard)

*"Now let me talk about which database I'd use for each service and show the schema."*

> **► DRAW THIS on the whiteboard ◄**
> Draw 3 boxes: users table (MySQL), videos document (MongoDB), watch_progress table (Cassandra).
> Write the key columns only — don't draw every field. Show the partition key for Cassandra.

### User DB — PostgreSQL/MySQL

*"User and subscription data needs to be ACID-compliant — payments must be
consistent. I'll use MySQL here."*

```
┌─────────────────────────────────────────────┐
│                  users                       │
├───────────────────┬─────────────────────────┤
│ user_id           │ UUID (PK)               │
│ name              │ VARCHAR(100)            │
│ email             │ VARCHAR(255) UNIQUE     │
│ password_hash     │ VARCHAR(255)            │
│ country_code      │ CHAR(2)                 │
│ subscription_status│ ENUM(ACTIVE,EXPIRED...) │
│ subscription_expiry│ DATE                   │
│ created_at        │ TIMESTAMP               │
└───────────────────┴─────────────────────────┘

┌─────────────────────────────────────────────┐
│            subscription_plans               │
├───────────────────┬─────────────────────────┤
│ plan_id           │ UUID (PK)               │
│ name              │ VARCHAR(50)             │  Basic/Standard/Premium
│ price             │ DECIMAL(10,2)           │
│ validity_days     │ INT                     │  30 / 365
│ currency          │ CHAR(3)                 │  INR / USD
│ max_streams       │ INT                     │  1 / 2 / 4
│ max_resolution    │ VARCHAR(10)             │  HD / FHD / UHD
└───────────────────┴─────────────────────────┘

┌─────────────────────────────────────────────┐
│              payments                        │
├───────────────────┬─────────────────────────┤
│ payment_id        │ UUID (PK)               │
│ user_id           │ UUID (FK → users)       │
│ amount            │ DECIMAL(10,2)           │
│ currency          │ CHAR(3)                 │
│ status            │ ENUM(SUCCESS,FAILED...) │
│ gateway_txn_id    │ VARCHAR(100)            │  Stripe charge ID
│ paid_at           │ TIMESTAMP               │
└───────────────────┴─────────────────────────┘
```

### ER Diagram — MySQL Tables (Relationships)

*"Let me show how all the relational tables connect to each other..."*

```
┌──────────────────────────┐
│          users            │
├──────────────────────────┤
│ PK  user_id  UUID         │
│     name                  │
│     email  (UNIQUE)        │
│     password_hash          │
│     country_code           │
│     subscription_status    │
│     subscription_expiry    │
│     created_at             │
└────────────┬─────────────┘
             │ 1
             │
             │ has many
             │
             ▼ N
┌──────────────────────────┐         ┌──────────────────────────┐
│        payments           │         │    subscription_plans     │
├──────────────────────────┤         ├──────────────────────────┤
│ PK  payment_id  UUID      │         │ PK  plan_id  UUID         │
│ FK  user_id ──────────────┼────────▶│     name  (Basic/Premium) │
│     amount                │  N:1    │     price  DECIMAL        │
│     currency              │         │     validity_days  INT    │
│     status                │         │     max_streams  INT      │
│     gateway_txn_id        │         │     max_resolution        │
│     paid_at               │         │     currency  CHAR(3)     │
└──────────────────────────┘         └──────────────────────────┘
                                               ▲
                                               │ N:1
                              (users.subscription_status
                               resolved via plan_id lookup)

Relationship Summary:
  users     ──(1:N)──▶  payments          (one user, many payments)
  users     ──(N:1)──▶  subscription_plans (many users, one plan)
  payments  ──(N:1)──▶  subscription_plans (payment tied to a plan)

NOTE: Watch history lives in CASSANDRA (not MySQL) — too many writes.
      Video metadata lives in MONGODB — flexible schema needed.
```

---

---

WHY S3 (OBJECT STORAGE) FOR VIDEO FILES? (Beginner Explanation)
  A regular database (MySQL, MongoDB) stores structured data — rows, columns, documents.
  Asking MySQL to hold a 50 GB video file is like asking your office filing cabinet
  to store a surfboard: wrong tool, completely wrong shape.
  S3 is an object store — a giant, infinitely scalable hard drive in the cloud.
  You give it a file (any size) and a name (key); it stores it durably and gives it back
  on demand. At 11 nines of durability (99.999999999%), losing a file is essentially impossible.
  With 10,000 videos × 5 quality levels × average 2-hour runtimes, we need ~500 PB of space.
  S3 scales to petabytes without any provisioning, costs pennies per GB, and integrates
  directly with CloudFront CDN — making it the only realistic choice.
  Problem it solves: storing 500 PB of video files cheaply, durably, and at unlimited scale.
  Without it: you would need to manage thousands of physical hard drives across data centres.

### Video DB — MongoDB

*"I choose MongoDB here because the schema is NOT uniform across content types.
A movie has a duration field. A series has seasons and episodes.
A live event has a scheduled time. MongoDB's flexible document model
handles this perfectly. The manifest URL also lives here as a field."*

```
┌──────────────────────────────────────────────────────────┐
│                VIDEO DB DOCUMENT (MongoDB)                │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Movie document:                                         │
│  {                                                       │
│    "_id":         "vid-abc",                             │
│    "type":        "MOVIE",                               │
│    "title":       "Extraction 2",                        │
│    "description": "Tyler Rake returns...",               │
│    "genre":       ["action", "thriller"],                │
│    "cast":        ["Chris Hemsworth"],                   │
│    "director":    "Sam Hargrave",                        │
│    "duration":    7380,                    ← seconds     │
│    "releaseYear": 2023,                                  │
│    "maturity":    "18+",                                 │
│    "country":     ["IN","US","GB"],        ← geo access  │
│    "thumbnail":   "s3://ott-static/...",                 │
│    "manifestHls": "s3://ott-encoded/.../hls.m3u8",  ←KEY│
│    "manifestDash":"s3://ott-encoded/.../dash.mpd",  ←KEY│
│    "qualities":   ["4K","1080P","720P","480P"],          │
│    "status":      "PUBLISHED"                            │
│  }                                                       │
│                                                          │
│  Series document:                                        │
│  {                                                       │
│    "_id":    "vid-xyz",                                  │
│    "type":   "SERIES",                                   │
│    "title":  "Squid Game",                               │
│    "seasons": [                                          │
│      {                                                   │
│        "seasonNum": 1,                                   │
│        "episodes": [                                     │
│          {                                               │
│            "episodeId":   "ep-001",                      │
│            "title":       "Red Light, Green Light",      │
│            "duration":    3660,                          │
│            "manifestHls": "s3://.../s1e1/hls.m3u8", ←KEY│
│            "manifestDash":"s3://.../s1e1/dash.mpd"       │
│          }                                               │
│        ]                                                 │
│      }                                                   │
│    ]                                                     │
│  }                                                       │
│                                                          │
│  WHY MONGODB: Movie ≠ Series ≠ Live Event schema         │
│               Manifest URL stored as field in document   │
└──────────────────────────────────────────────────────────┘
```

### Watch History — Cassandra

*"Watch history gets 500K writes per second from heartbeats. That kills MySQL.
Cassandra is designed for exactly this — millions of writes per second,
and I partition by profileId so all progress for one user is co-located."*

```
┌──────────────────────────────────────────────────────────┐
│           WATCH_PROGRESS TABLE (Cassandra)                │
├───────────────────┬──────────────────────────────────────┤
│ profile_id        │ UUID  ← PARTITION KEY                │
│ last_watched      │ TIMESTAMP ← CLUSTERING KEY (DESC)    │
│ video_id          │ UUID                                 │
│ episode_id        │ UUID (null for movies)               │
│ position_sec      │ INT   ← resume from here             │
│ duration_sec      │ INT                                  │
│ percent_done      │ DECIMAL                              │
│ completed         │ BOOLEAN  (true if >90% watched)      │
└───────────────────┴──────────────────────────────────────┘

Query: SELECT * FROM watch_progress
       WHERE profile_id = ?
       ORDER BY last_watched DESC
       LIMIT 20                  ← "Continue Watching" row

Why Cassandra:
  partition_key = profile_id
  → All progress for one user on ONE node = fast reads
  → Linear write scale: add nodes = more write throughput
  → 500K writes/sec? No problem.
```

### Redis — What Gets Cached

```
┌──────────────────────────────────────────────────────────┐
│                   REDIS CACHE KEYS                        │
├──────────────────────────┬──────────────────────────────┤
│ Key                      │ Value / TTL                  │
├──────────────────────────┼──────────────────────────────┤
│ manifest:{videoId}       │ manifest URL string / 1hr    │
│ entitlement:{userId}     │ plan details / 5min          │
│ streams:active:{userId}  │ INT counter (INCR/DECR)      │
│ token:blacklist:{jti}    │ "1" / 15min (logout)         │
│ trending:{countryCode}   │ sorted set of titleIds / 5min│
└──────────────────────────┴──────────────────────────────┘

"Play Service: before hitting MongoDB,
 check Redis for manifest:{videoId}.
 Cache hit = instant. Cache miss = MongoDB query + cache for 1hr."
```

---

> **► DRAW THIS on the whiteboard ◄**

## ER RELATIONSHIP DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────┐
│                  OTT PLATFORM — ENTITY RELATIONSHIP                  │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌────────────────────────────────────┐
│      users        │     │              videos                 │
│     (MySQL)       │     │             (MySQL)                 │
├──────────────────┤     ├────────────────────────────────────┤
│ PK user_id UUID  │─────│ PK video_id UUID                  │
│    email TEXT    │ 1 N │ FK creator_id UUID → users        │
│    plan ENUM     │     │    title VARCHAR                  │
│    created_at TS │     │    description TEXT               │
└──────────────────┘     │    duration_sec INT               │
         │               │    status ENUM(PROCESSING,READY)  │
         │ N             │    thumbnail_url TEXT             │
         │               │    uploaded_at TIMESTAMP          │
┌────────▼────────────┐  └──────────────┬───────────────────┘
│   subscriptions      │                 │ 1
│     (MySQL)          │                 │ N
├─────────────────────┤  ┌──────────────▼──────────────────┐
│ PK sub_id UUID      │  │         video_segments           │
│ FK user_id UUID     │  │          (Cassandra)             │
│    plan ENUM        │  ├─────────────────────────────────┤
│    status ENUM      │  │ PK video_id UUID (PARTITION)    │
│    started_at TS    │  │    resolution ENUM (CLUSTERING) │
│    expires_at TS    │  │    s3_manifest_url TEXT         │
└─────────────────────┘  │    segment_count INT            │
                         │    processing_status ENUM       │
┌──────────────────────┐ └─────────────────────────────────┘
│   watch_history       │
│    (Cassandra)        │  Redis:
├──────────────────────┤  ┌──────────────────────────────────────────┐
│ PK user_id (PART)    │  │ watch_position:{userId}:{videoId} INT sec│
│    video_id (CLUST)  │  │ content_meta:{videoId} HASH title,thumb  │
│    watch_position INT│  │ popular_videos ZSET score→videoId        │
│    completed BOOL    │  │ session:{token} HASH user session        │
│    last_watched TS   │  └──────────────────────────────────────────┘
└──────────────────────┘
```

---

## STEP 7 — Video Streaming Deep Dive (Most Important!)

*"Now the most important part — how does video actually stream without buffering?
Let me explain the whole thing from scratch."*

---

WHY VIDEO TRANSCODING EXISTS? (Beginner Explanation)
  A film studio delivers a raw 4K master file — often 100 GB or more for a 2-hour movie.
  Your grandma watches Netflix on a 3G phone. Your friend watches on a 4K OLED TV.
  They cannot both stream the same 100 GB file — grandma's connection would buffer for hours.
  Transcoding = taking that one massive source file and baking multiple smaller copies:
  4K (large, crisp), 1080p (medium), 720p (smaller), 480p (tiny, works on 3G).
  Think of it like a bakery that receives one giant master cake and slices it into
  small/medium/large portions so every customer gets the right size.
  The encoder also splits the video into 6-10 second segments at each quality level,
  which is what makes quality-switching mid-stream possible.
  Problem it solves: one video must be watchable on a 3G phone AND a 4K TV simultaneously.
  Without it: you would either force everyone onto 4K (buffering hell) or cap everyone at 480p.

### The Problem

```
"A 4K movie = roughly 100 GB raw.

 You CANNOT:
   × Download 100 GB before playing (takes hours)
   × Stream a single quality (4K on 2G is impossible)

 You NEED:
   ✓ Split video into small pieces
   ✓ Encode each piece at multiple quality levels
   ✓ Dynamically switch quality based on bandwidth
   ✓ Pre-fetch next piece before current one ends"
```

---

WHY ADAPTIVE BITRATE STREAMING (HLS / DASH) EXISTS? (Beginner Explanation)
  Imagine watching a movie on a train. In the city your signal is great (4K).
  You enter a tunnel — connection drops to barely 3G. You exit — it's back to strong.
  Old-school video download forced you to pick one quality upfront: pick 4K and the
  tunnel gives you a 30-second freeze; pick 480p and the city scenes look blurry.
  ABR (Adaptive Bitrate) solves this: the video is pre-chopped into 6-10 second chunks,
  each chunk encoded at multiple quality levels (4K/1080p/720p/480p).
  Every 6-10 seconds your video player measures your current internet speed and requests
  the NEXT chunk at the best quality for right now — automatically, invisibly.
  Going into a tunnel? Next chunk is 480p. Back in the city? Jumps back to 1080p.
  HLS (.m3u8) and DASH (.mpd) are the two standard protocols that define how
  chunks are listed, requested, and stitched together — HLS is mandatory on Apple,
  DASH is used everywhere else.
  Problem it solves: zero buffering regardless of changing network conditions.
  Without it: you would either freeze constantly or be forced to watch everything in safe low quality.

### The Manifest File — Draw This

*"The key to this whole thing is the manifest file. Think of it as a
table of contents for the video. Without it, you can't stitch segments together."*

```
                    MANIFEST FILE STRUCTURE
                    ════════════════════════

    master.m3u8 (or manifest.mpd for DASH)
    ─────────────────────────────────────
    "I am the MASTER playlist.
     Pick a quality, I'll point you to its segment list."

           │
           ├──▶  1080p/playlist.m3u8
           │         "Here are all the 1080p segments in order"
           │          seg001.ts  (0-10 sec)
           │          seg002.ts  (10-20 sec)
           │          seg003.ts  (20-30 sec)
           │          ...
           │
           ├──▶  720p/playlist.m3u8
           │         seg001.ts  (0-10 sec) ← same time, lower quality
           │         seg002.ts  (10-20 sec)
           │         ...
           │
           └──▶  480p/playlist.m3u8
                     seg001.ts  (0-10 sec)
                     ...

HLS format  → .m3u8  (mandatory on Apple iOS/Safari)
DASH format → .mpd   (used on Android, Web, Smart TV)
```

### Adaptive Bitrate (ABR) — The Core Loop

*"Here's exactly what happens second by second when you press Play..."*

> **► SAY THIS out loud + draw the timeline ◄**
> Draw a horizontal timeline. Mark t=0, t=6, t=10. Show bandwidth check at t=6,
> pre-fetch at t=6, seamless switch at t=10. Interviewers love this timeline.

```
t=0s   USER PRESSES PLAY
       │
       │  Play Service → MongoDB → returns manifest URL
       │  Client fetches master.m3u8 from CDN
       │
       │  Client measures bandwidth: 3 Mbps
       │  Picks: 720p playlist (needs 2.5 Mbps)
       ▼
t=0s   GET  cdn.../720p/seg001.ts    ← downloads in ~0.5s
       Starts playing segment 1 (0-10 seconds at 720p)

t=6s   ← I-FRAME BOUNDARY (60% through segment)
       Client re-measures bandwidth: NOW 8 Mbps!
       Decides: upgrade to 1080p for next segment
       GET  cdn.../1080p/seg002.ts   ← pre-fetches in background

t=10s  Segment 1 ends → segment 2 (1080p) is already ready
       Seamless quality upgrade — zero gap — zero rebuffering ✓

t=16s  Re-measures again: still 8 Mbps → stays 1080p
       GET  cdn.../1080p/seg003.ts

t=22s  Bandwidth drops to 1.5 Mbps (network congestion)
       Picks: 480p for next segment
       GET  cdn.../480p/seg004.ts    ← drops quality, NO buffering

  ... this loop runs forever until video ends ...
```

### What is an I-Frame?

*"Quick question you might get — what is an I-frame and why does it matter?"*

```
Video frames:
  I-frame = complete full image (large, ~50KB)
  B-frame = only the CHANGE from last I-frame (tiny, ~2KB)

Timeline:
  [I][B][B][B][B][B][B][B][B][B] | [I][B][B][B][B]...
   ←───────── Segment 1 ─────────→  ←── Segment 2

Rules:
  1. Every segment STARTS on an I-frame (clean cut point)
  2. You cannot START playback mid-segment (would show corrupted video)
  3. Client pre-fetches next segment at ~60% through current
     → download completes before current ends → ZERO REBUFFERING

This is why HLS uses 6-10 second segments and DASH uses 2-4 seconds.
Shorter segments = faster quality switching but more manifest overhead.
```

---

WHY CDN EXISTS FOR VIDEO DELIVERY? (Beginner Explanation)
  Imagine Netflix stores all its video files in one warehouse in Virginia, USA.
  Someone in Mumbai presses Play — the request travels 14,000 km to Virginia and
  all the way back before a single frame appears. That is 200ms+ just in travel time,
  before any actual video data moves. Multiply by 15 million people pressing Play
  simultaneously and the Virginia warehouse instantly catches fire.
  A CDN (Content Delivery Network) is like placing mini-warehouses near every major city.
  Mumbai gets video from a Mumbai edge server (5ms away). London from London. Sydney from Sydney.
  The first time anyone in Mumbai watches a show, the CDN server fetches it from Virginia
  and keeps a local copy. Every viewer after that gets it from the local copy — no cross-ocean trip.
  Video segments are immutable (they never change), making them perfect for long CDN caching.
  Problem it solves: fast, low-latency video for 200M global users without killing the origin server.
  Without it: 2.5 million segment requests/sec would slam S3 directly — instant catastrophic failure.

### CDN — Why It's Not Optional

```
WITHOUT CDN:
  Client request path:
  Mobile → Load Balancer → Play Service → S3 (Virginia)
  Latency: ~200-500ms per segment
  Origin load: 2.5 MILLION requests/sec → origin dies instantly

WITH CDN:
  Client request path:
  Mobile → CloudFront PoP (Mumbai, 5ms away) → cache HIT
  Latency: ~5ms per segment
  Origin load: only 5% cache misses = ~125K req/sec → manageable

CDN cache rules:
  Video segments  → TTL = 7 days  (immutable, perfect for cache)
  Master manifest → TTL = 5 min   (may change quality options)
  Thumbnails      → TTL = 24 hrs
  DRM license     → NOT cached    (user-specific, can't cache)
```

---

### Sequence Diagram — Full Play Flow (Draw Step by Step)

*"Let me show the exact sequence of calls when a user presses Play..."*

> **► DRAW THIS on the whiteboard ◄**
> Draw 7 vertical lines (Client, API GW, Play Svc, Redis, MongoDB, DRM Svc, CDN).
> Add horizontal arrows left to right for each call. Number each arrow.
> This diagram wins interviews — it shows you understand the full request lifecycle.

```
Client       API GW      Play Svc     Redis     MongoDB    DRM Svc     CDN
  │             │             │          │           │          │        │
  │─POST /play─▶│             │          │           │          │        │
  │             │─route──────▶│          │           │          │        │
  │             │             │─GET manifest─────────▶          │        │
  │             │             │  manifest:{videoId}  │          │        │
  │             │             │◀─MISS───────────────-│          │        │
  │             │             │─GET title───────────────────────▶        │
  │             │             │◀─{manifestUrl}──────────────────│        │
  │             │             │─SET manifest (1hr)──▶│           │        │
  │             │             │─INCR streams:active─▶│           │        │
  │             │             │─genDrmToken─────────────────────────────▶│
  │             │             │◀─{drmToken, licenseUrl}──────────────────│
  │◀─200 PlayResponse─────────│          │           │          │        │
  │  {manifestUrl,            │          │           │          │        │
  │   drmToken,               │          │           │          │        │
  │   resumeAt: 1234s}        │          │           │          │        │
  │                           │          │           │          │        │
  │─GET master.m3u8────────────────────────────────────────────────────▶│
  │◀─manifest (cache HIT, ~5ms)─────────────────────────────────────────│
  │                           │          │           │          │        │
  │─POST wv-license────────────────────────────────────────────▶│        │
  │  {licenseRequest, drmToken}│         │           │          │        │
  │◀─content key (in hardware CDM)──────────────────────────────│        │
  │                           │          │           │          │        │
  │─GET seg001.ts (720p)───────────────────────────────────────────────▶│
  │◀─video segment (~50ms)──────────────────────────────────────────────│
  │  🎬 VIDEO PLAYS           │          │           │          │        │
  │                           │          │           │          │        │
  │  [every 30s]              │          │           │          │        │
  │─POST /heartbeat───────────▶         │           │          │        │
  │             │─upsert progress──────▶│           │          │        │
  │◀─204─────────────────────-│          │           │          │        │
  │                           │          │           │          │        │
  │  [at I-frame ~6s]         │          │           │          │        │
  │─GET seg002.ts (1080p)──────────────────────────────────────────────▶│
  │◀─next segment───────────────────────────────────────────────────────│
  │  [seamless quality upgrade]│         │           │          │        │

TOTAL TIME TO FIRST FRAME: ~200-500ms
  API call:       ~20ms  (entitlement + manifest fetch)
  DRM license:    ~30ms
  First segment:  ~50ms  (CDN hit)
  ─────────────────────
  Total:          ~100-200ms  🎬

NOTE: On cache HIT for manifest (Redis) — API call drops to ~5ms.
      Second play of same title = near-instant start.
```

---

---

WHY DRM (DIGITAL RIGHTS MANAGEMENT) EXISTS? (Beginner Explanation)
  Imagine every video file is a locked box, and only paying subscribers get a key.
  Without DRM, video segments are just files at CDN URLs — anyone who intercepts or
  finds the URL can download raw bytes, copy them, and upload to piracy sites.
  With DRM, segments are AES-encrypted: even if a pirate downloads them, they see random garbage.
  To decrypt you need a license key — and the license server only issues that key after checking:
  "Is this user's subscription active? Is this title available in their country?"
  The key is delivered into a hardware security chip (TEE — Trusted Execution Environment)
  built into the device. Your own app code can never read it, which is exactly why
  screen recording is blocked on Netflix content in iOS and Android.
  Three DRM systems cover all devices: Widevine (Google/Android/Chrome), FairPlay (Apple),
  PlayReady (Windows/Xbox). You must support all three.
  Problem it solves: stops piracy and enforces geo-licensing without trusting the client.
  Without it: premium content would appear on piracy sites within hours of release.

### DRM Flow — How Content Is Protected

*"DRM is the most OTT-specific thing. Let me walk through it simply..."*

```
THE CORE IDEA:
  Video segments in S3/CDN are ENCRYPTED (AES-128).
  Even if someone gets the CDN URL, the file is unreadable.
  The decryption key ONLY comes from the license server
  AFTER verifying the user has an active subscription.

THREE DRM SYSTEMS (know these):
  ┌─────────────┬──────────────────────────────┐
  │ Widevine    │ Android, Chrome, Firefox, TV │
  │ FairPlay    │ iOS, macOS, Safari (Apple)   │
  │ PlayReady   │ Windows, Edge, Xbox          │
  └─────────────┴──────────────────────────────┘
  Client tells server which one via: drmSystem: "widevine"

FULL DRM FLOW:
  ┌──────────┐                                    ┌─────────────────┐
  │  CLIENT  │                                    │  LICENSE SERVER │
  │(Android) │                                    │  (Widevine)     │
  └────┬─────┘                                    └────────┬────────┘
       │                                                   │
       │  1. POST /stream/play                             │
       │─────────────────────────────────────────────────▶ Play Svc
       │                                                   │
       │  2. Receive: { manifestUrl, drmToken }            │
       │◀──────────────────────────────────────────────── Play Svc
       │                                                   │
       │  3. GET manifest.mpd from CDN                     │
       │     (sees: content is encrypted, needs license)   │
       │                                                   │
       │  4. POST license request                          │
       │     { licenseRequest (Protobuf), drmToken }       │
       │──────────────────────────────────────────────────▶│
       │                                                   │
       │     License server verifies drmToken:             │
       │     ✓ Valid JWT?                                  │
       │     ✓ Subscription ACTIVE?                        │
       │     ✓ Title available in user's country?          │
       │                                                   │
       │  5. Returns: content decryption key               │
       │◀──────────────────────────────────────────────────│
       │                                                   │
       │  6. Widevine CDM (hardware chip / TEE)            │
       │     receives key — NEVER accessible to app code   │
       │     decrypts video segment in secure memory       │
       │                                                   │
       │  7. 🎬 VIDEO PLAYS (decrypted only inside chip)   │

KEY POINTS TO SAY:
  "The key never touches app memory — lives inside hardware TEE.
   That's why screen recording APIs are blocked on DRM content.
   If user cancels subscription → license server returns 403
   → downloaded content stops playing too."
```

---

## STEP 8 — Subscription + Payment Flow (Speak This)

*"Let me now walk through what happens when a user subscribes..."*

```
User selects Premium plan (₹649/month)
             │
             │  POST /api/v1/subscriptions
             ▼
      ┌─────────────────┐
      │ SUBSCRIPTION    │
      │   SERVICE       │
      └────────┬────────┘
               │
               ▼
      ┌─────────────────┐      ┌──────────────────┐
      │   PAYMENT       │─────▶│  STRIPE / RAZORPAY│
      │   SERVICE       │      │  (3rd party)      │
      └────────┬────────┘      └──────────┬────────┘
               │                          │
               │        payment.succeeded │
               │◀─────────────────────────┘
               │
               │  Publishes Kafka event:
               │  { userId, planId, status: ACTIVE }
               ▼
       ┌──────────────┐
       │ KAFKA BROKER │
       └──────┬───────┘
              │
     ┌────────┴──────────┐
     ▼                   ▼
┌──────────────┐  ┌────────────────────────┐
│NOTIFICATION  │  │  USER DB CONSUMER      │
│SERVICE       │  │  (updates MySQL)       │
│              │  │                        │
│ Sends email: │  │  UPDATE users SET      │
│ "Welcome to  │  │    subscription_status │
│  Netflix!"   │  │      = 'ACTIVE',       │
└──────────────┘  │    subscription_expiry │
                  │      = DATE + 30 DAYS  │
                  │  WHERE user_id = :id   │
                  └────────────────────────┘

WHY KAFKA NOT DIRECT CALL?
  Subscription Service should NOT own User DB.
  If User DB is slow → payment flow is NOT blocked.
  Two consumers run in PARALLEL → faster.
  If Notification Service crashes → Kafka replays the event.
```

---

## STEP 9 — Search Service (CDC Pipeline)

*"For search, the key insight is we NEVER query MongoDB directly from the
search service. We use Elasticsearch with a CDC pipeline to keep it updated."*

```
THE PROBLEM:
  "Find all action movies from 2023 available in India"
  → Scanning 10K MongoDB documents = slow at 100K req/sec

THE SOLUTION: Elasticsearch

CDC PIPELINE (how MongoDB changes reach Elasticsearch):
┌──────────────┐    ┌──────────┐    ┌───────────┐    ┌──────────────┐
│  Video DB    │───▶│ Debezium │───▶│   Kafka   │───▶│Elasticsearch │
│  (MongoDB)   │    │  (CDC)   │    │  "video-  │    │  Indexer     │
│              │    │captures  │    │  metadata"│    │  Consumer    │
│ new video    │    │all inserts│    │  topic    │    │              │
│ published    │    │/updates  │    │           │    │ upserts doc  │
└──────────────┘    └──────────┘    └───────────┘    └──────┬───────┘
                                                            │
                                                            ▼
                                                   ┌──────────────────┐
                                                   │  ES Index        │
                                                   │  {title, genre,  │
                                                   │   cast, country, │
                                                   │   rating, year}  │
                                                   └──────────────────┘

SEARCH QUERY FLOW:
  User: "action 2023 india"
  Search Service → Elasticsearch:
  {
    must: { multi_match: "action 2023" on [title, description, cast] }
    filter: [ { term: { country: "IN" } },
              { term: { status: "PUBLISHED" } } ]
    sort: [ { rating: desc }, { popularity: desc } ]
    size: 20
  }
  → Returns top 20 (paginated), PARTIAL data only (id, title, thumbnail)
```

---

## STEP 10 — Watch History & Recommendations (Speak This Out Loud)

*"Let me walk through how we track watch progress and power 'Continue Watching'..."*

---

WHY WATCH HISTORY AND RESUME POSITION EXIST? (Beginner Explanation)
  Think of a bookmark in a physical book — except it must survive dropping the book,
  switching to a different copy, and picking up where you left off three weeks later.
  Every 30 seconds while you watch, your device quietly tells the server: "still at 20m 45s."
  If your phone dies at 20:45, next time you open the app it says "resume from 20:45" —
  even if you switch from phone to TV or TV to laptop.
  Two storage layers: Redis keeps your current position in RAM (reads in under 1ms)
  for instant resume; Cassandra stores it permanently so it survives Redis restarts
  and holds years of your watch history.
  Problem it solves: without this, every crash or device switch forces you to restart a movie.
  Without it: users would need to remember timestamps manually across devices — a UX disaster.

---

```
TRACKING WATCH PROGRESS:
  Client sends heartbeat every 30s:
  POST /api/v1/stream/heartbeat { profileId, videoId, positionSeconds }

TWO-LAYER STORAGE:
  ┌─────────────────────────────────────────────────────┐
  │  LAYER 1 — REDIS (hot, fast)                        │
  │  HSET watch_progress:{userId}:{videoId}             │
  │       current_time {seconds}                        │
  │       last_updated {timestamp}                      │
  │  TTL = 7 days                                       │
  │  Purpose: instant resume (sub-millisecond read)     │
  ├─────────────────────────────────────────────────────┤
  │  LAYER 2 — CASSANDRA (persistent)                   │
  │  Background job flushes Redis → Cassandra every 60s │
  │  Partition key = profile_id (all history on 1 node) │
  │  Purpose: long-term storage, survives Redis restart  │
  └─────────────────────────────────────────────────────┘

RESUME PLAYBACK FLOW:
  User clicks Play → Play Service:
    1. HGET watch_progress:{userId}:{videoId} → Redis hit
    2. Returns { resumeAt: 1245 } in play response
    3. Client seeks to 20:45 before first segment loads
    → Seamless "Continue Watching" experience

WHY NOT POSTGRESQL FOR WATCH PROGRESS?
  20M DAU × 1 heartbeat/30s = ~670K writes/sec
  PostgreSQL max: ~50K writes/sec → dies instantly
  Redis handles millions of writes/sec from RAM.
  Cassandra handles millions of writes/sec with linear scale.

KAFKA EVENT FOR ANALYTICS + RECOMMENDATIONS:
  On every progress update → publish 'video.watched':
  { userId, videoId, durationWatched, timestamp, deviceType }
       │
       ├──▶ Analytics Service  (view counts, completion rate)
       └──▶ Recommendation Service (collaborative filtering)

RECOMMENDATIONS ENGINE:
  Collaborative filtering: "Users who watched X also watched Y"
  Content-based: Same genre, actors, director
  ML model (TensorFlow):
    Inputs: watch_history, search queries, ratings
    Output: ranked list of 20 recommended titles
  Results cached in Redis per user (TTL = 24 hours)
```

---

WHY A RECOMMENDATION ENGINE EXISTS? (Beginner Explanation)
  Imagine a librarian who secretly watched everything you've read for two years.
  They don't just know your favourite genres — they know you finish thrillers but
  abandon rom-coms after 10 minutes, and you binge action series in one sitting.
  "Continue Watching" is the easy part: just read your last position from the database.
  "You May Also Like" is the clever part — collaborative filtering asks:
  "What do people who watched the exact same titles as you, in the same order,
  with the same completion rates, watch next?" That pattern reveals taste without asking.
  An ML model (TensorFlow) takes your watch history, search queries, and ratings as
  inputs and outputs a ranked list of 20 titles, cached in Redis for 24 hours.
  Problem it solves: with 10,000 titles, users would never discover great content on their own.
  Without it: churn rises sharply because users stall at "what should I watch tonight?"

---

## STEP 11 — Analytics & Monitoring (Speak This Out Loud)

*"For observability, I'd set up a real-time analytics pipeline and dashboards..."*

```
REAL-TIME ANALYTICS PIPELINE:
  All events → Kafka → Apache Flink (stream processing)
                            │
              ┌─────────────┼──────────────────┐
              ▼             ▼                  ▼
         Aggregations   Anomaly            Raw events
         (hourly/daily) Detection          → S3 (data lake)
              │
         PostgreSQL/BigQuery (dashboards)

EVENTS TRACKED:
  play_started    → { userId, videoId, deviceType, resolution, geo }
  play_paused     → { sessionId, positionSeconds }
  quality_switch  → { from: "1080p", to: "720p", reason: "bandwidth" }
  rebuffer_event  → { sessionId, stallDuration }
  play_completed  → { videoId, watchDuration, completionPercent }

METRICS AGGREGATED:
  Hourly:  view counts per video, avg watch time, buffering ratio
  Daily:   user retention, content popularity by region, revenue

DASHBOARDS (Grafana):
  ┌────────────────────────────────────────────────┐
  │  concurrent viewers   │  CDN cache hit rate     │
  │  bandwidth usage      │  error rate (4xx, 5xx)  │
  │  buffering ratio      │  top 10 videos today    │
  │  DB replication lag   │  transcoding queue depth│
  └────────────────────────────────────────────────┘

ALERTS (PagerDuty):
  CDN error rate   > 1%   → page on-call
  Origin load      > 80%  → scale up
  Transcoding queue> 1000 → add workers
  Payment failures > 5%   → page payments team
```

---

## STEP 12 — Content Delivery Optimization (Speak This Out Loud)

*"A few optimizations worth mentioning for senior-level discussions..."*

---

WHY THUMBNAIL GENERATION EXISTS? (Beginner Explanation)
  When you browse Netflix, every title shows a picture before you click.
  Those preview images don't come from a graphic designer — they're auto-extracted
  from the video itself during the transcoding pipeline.
  Think of it like a photo-booth that snaps a frame every 10 seconds of the movie
  and saves each one as a small image file.
  Hover previews (the animated strip that plays when you mouse over a title) are just
  many of those images loaded in quick sequence, like a flipbook.
  Thumbnails are stored in S3 as WebP files (30% smaller than JPEG) and served via CDN —
  the same way video segments are, since they are served millions of times on browse pages.
  Problem it solves: users need visual previews to judge a title without playing the video first.
  Without it: every title would show a blank grey box, and nobody would know what to click.

---

```
1. CDN PRE-WARMING (New Release Strategy)
   Problem: New season drops → 200M users hit CDN simultaneously
            → All requests are cache MISSES → origin spike
   Solution: Before launch, push top segments to edge PoPs:
             for each edge in cdn.edgeLocations:
               prefetch(manifestUrl, first5Segments)
             → Cache is HOT before first user presses Play

2. H.265 / HEVC CODEC
   H.264: baseline standard, widely supported
   H.265: 50% better compression at same quality
          4K movie: 24 GB (H.264) → 12 GB (H.265)
   AV1:   30% better than H.265, future standard
          Slower to encode, not yet universally supported
   Strategy: Use H.265 for new content, H.264 as fallback

3. BINGE-WATCHING PRELOAD
   User is 80% through episode 3 → client silently prefetches
   first 2 segments of episode 4 in the background.
   Result: episode 4 starts instantly (<500ms) instead of
   fetching manifest + DRM token from scratch.

4. THUMBNAIL OPTIMIZATION
   Serve WebP instead of JPEG → 30% smaller files
   Generate multiple sizes (small/medium/large)
   Lazy load: only fetch thumbnails as user scrolls
   → Saves significant CDN bandwidth on browse pages

5. OFFLINE DOWNLOADS (Mobile)
   User downloads encrypted segments to local storage
   DRM license downloaded with 30-day expiry
   On subscription end → license server returns 403
   → Downloaded content becomes unplayable automatically

6. GEO-BASED S3 BUCKETS
   Store content in regional buckets closest to audience:
   US content → us-east-1
   EU content → eu-west-1
   Asia content → ap-south-1
   CDN fetches from nearest origin → reduces latency 60%
```

---

## STEP 13 — Scalability Discussion

*"Let me now address the main scalability bottlenecks..."*

---

WHY CONCURRENT STREAM LIMITS EXIST? (Beginner Explanation)
  Think of your Netflix subscription like a movie ticket — the Basic plan buys you
  one seat, not unlimited seats for your whole apartment building.
  Without enforcement, one shared account could stream on 50 phones at once.
  A concurrent stream counter in Redis acts like a bouncer at the door:
  when you press Play, the counter goes up by 1 (INCR); when you stop, it goes down (DECR).
  If the counter is already at your plan's limit (e.g., 1 for Basic), you get blocked instantly.
  Redis is used — not MySQL — because INCR is a single atomic CPU instruction
  that safely handles thousands of simultaneous "can I play?" checks per second.
  Problem it solves: stops account sharing that would let one subscription serve unlimited viewers.
  Without it: revenue would collapse — one household plan would serve an entire neighbourhood.

---

```
BOTTLENECK 1 → 2.5M segment requests/sec
─────────────────────────────────────────
Problem:  Play Service + S3 cannot handle 2.5M req/sec
Solution: CDN absorbs 95% → origin sees only 125K req/sec
          Video segments are immutable → PERFECT for CDN caching

BOTTLENECK 2 → 500K watch history writes/sec
─────────────────────────────────────────────
Problem:  MySQL dies at ~50K writes/sec
Solution: Cassandra → designed for millions of writes/sec
          Partition by profileId → linear scale (add nodes)

BOTTLENECK 3 → Concurrent stream enforcement
─────────────────────────────────────────────
Problem:  Basic plan = 1 stream. How to enforce at scale?
Solution: Redis atomic counter per user:
          ┌─────────────────────────────────────────────┐
          │  INCR streams:active:{userId}               │
          │  if count > plan.maxStreams:                 │
          │    DECR streams:active:{userId}             │
          │    return HTTP 429 "Too many streams"        │
          │  else:                                       │
          │    allow play, set TTL = 4 hours            │
          │  On heartbeat timeout (60s): auto DECR      │
          └─────────────────────────────────────────────┘

BOTTLENECK 4 → DRM license per stream start
─────────────────────────────────────────────
Problem:  15M concurrent streams → 15M license requests at startup
Solution: Cache valid DRM licenses in Redis (TTL = 4hrs)
          Only ~1% hit the actual license server (cache miss)

BOTTLENECK 5 → Manifest fetch on every play
─────────────────────────────────────────────
Problem:  MongoDB roundtrip on every play button click
Solution: Redis cache: SET manifest:{videoId} {url} EX 3600
          Play Service checks Redis first → cache hit = instant
```

---

## HLS vs DASH — Say This When Asked

*"If the interviewer asks about protocols, here's the clean comparison..."*

```
┌───────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│ Feature                   │       DASH                   │       HLS                    │
├───────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ Manifest format           │ .mpd (XML)                   │ .m3u8 (M3U playlist)         │
│ Segment format            │ .mp4 (fMP4) or .ts           │ .ts or .m4s (fMP4)           │
│ Bitrate switching control │ More flexible — client can   │ More sequential — client     │
│                           │ pre-fetch multiple segments  │ loads one segment at a time  │
│ Default segment interval  │ Usually 2s – 4s              │ Usually 6s – 10s             │
│ Segment loading           │ Can fetch multiple bitrates  │ Loads only one bitrate       │
│                           │ at once                      │ at a time                    │
│ Latency                   │ Lower (DASH-LL supports 1-3s)│ Higher (LL-HLS supports 2-6s)│
│ Quality switching         │ Faster (smaller segments)    │ Slower (bigger segments)     │
│ Mandatory on              │ Android, Web, Smart TV       │ Apple (iOS / Safari)         │
│ DRM                       │ Widevine + PlayReady         │ FairPlay (Apple)             │
│ Codec support             │ Agnostic (H.264, H.265, VP9) │ Mostly H.264 / H.265         │
└───────────────────────────┴──────────────────────────────┴──────────────────────────────┘

"In practice, an OTT platform serves BOTH.
 Client sends X-DRM-System header.
 Server returns HLS for Apple, DASH for everyone else."
```

---

## TRADE-OFFS TO MENTION (Shows Senior Thinking)

```
"A few trade-offs worth calling out..."

1. OWN CDN vs CLOUDFRONT
   Netflix built its own (Open Connect Appliance — servers inside ISPs).
   Cost at scale → own CDN is cheaper. For a startup → CloudFront is fine.

2. HLS vs DASH
   Must serve both. Can't drop HLS — Apple mandates it.
   DASH preferred everywhere else (faster quality switching).

3. CONSISTENCY in watch progress
   Eventual consistency is FINE here.
   5-second lag in saving position is invisible to user.
   Don't use strong consistency for 500K writes/sec.

4. MONGODB for Video DB
   Flexible schema wins over relational for mixed content types.
   Trade-off: no ACID transactions across documents.
   Acceptable — video metadata updates are rare and low-risk.

5. CASSANDRA for Watch History
   Perfect for writes. Trade-off: no complex queries / joins.
   That's fine — we only ever query by profileId (partition key).
```

---

## 5-MINUTE RAPID ANSWER (If Time Is Short)

*"If you only have 5 minutes, speak this entire block:"*

```
"I'd design this OTT platform with these five pieces:

ONE — USER + SUBSCRIPTION:
  MySQL for users and payments (ACID).
  On payment success → Kafka event → two consumers run in parallel:
  one sends welcome email, the other updates subscription_status in User DB.
  I use Kafka so the payment flow isn't blocked by a slow User DB.

TWO — CONTENT INGESTION (backend team only):
  Raw video to S3 → Chunker splits into 10-second segments and creates
  a manifest file. Manifest goes to Kafka → Video Encoder makes four
  quality versions — 4K, 1080p, 720p, 480p — and saves them back to S3.
  The manifest URL is stored in MongoDB (Video DB).

THREE — VIDEO STREAMING (the hot path):
  User clicks Play → Play Service fetches manifest from MongoDB
  (Redis-cached for 1 hour) → returns manifest URL to client.
  Client measures bandwidth → requests segments from CDN at matching quality.
  Every 6 seconds at the I-frame boundary, client re-measures bandwidth
  and pre-fetches next segment at the appropriate quality.
  CDN serves 95% of traffic — 2.5 million requests per second.
  This is called Adaptive Bitrate Streaming — HLS or DASH protocol.

FOUR — SEARCH:
  Elasticsearch for full-text search. MongoDB changes streamed via
  CDC pipeline (Debezium) → Kafka → Elasticsearch indexer.
  Never query MongoDB directly for search.

FIVE — SCALE:
  CDN handles 2.5M segment requests/sec with 95% cache hit.
  Cassandra handles 500K heartbeat writes/sec.
  Redis atomic INCR enforces concurrent stream limits per plan.
  DRM licenses cached in Redis — only 1% hit the license server."
```

---

## WHAT NOT TO SAY ✗

```
✗ "I'd use MySQL for watch history"
  → 500K writes/sec kills MySQL. Say Cassandra.

✗ "The client downloads the whole video first"
  → That's a download, not streaming. Say chunks + ABR.

✗ "CDN is optional here"
  → Without CDN, 2.5M req/sec hits origin → instant failure.

✗ "I'll skip the manifest file — just serve video from S3"
  → Without manifest, there's no way to sequence segments
    or switch quality. Manifest is mandatory.

✗ Confusing .m3u8 and .mpd
  → .m3u8 = HLS (Apple). .mpd = DASH (everyone else).

✗ "HLS and DASH are interchangeable"
  → Apple mandates HLS. You must serve both.
```

---

## SENIOR TRAP QUESTIONS (15 YOE Level)

*These are the follow-up questions that separate a 5-YOE answer from a 15-YOE answer.
An interviewer will ask these AFTER you give the standard answer. Know all of them.*

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 1 — RACE CONDITIONS & CONCURRENCY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "You use Redis INCR to enforce concurrent stream limits. What if
   two devices hit INCR at exactly the same time?"

A: INCR is atomic in Redis — it's a single CPU instruction on the
   Redis server. No race condition possible. But there IS a different
   race: what if the user closes the app without hitting /stream/stop?
   The DECR never fires. Counter stays inflated forever.

   FIX: Heartbeat timeout. If /stream/heartbeat stops for 90 seconds,
   auto-DECR using a Redis key with TTL:
     SET stream:alive:{sessionId}  1  EX 90
   A background job cleans up expired sessions and DECRs the counter.
   Or use a Lua script for atomic check-and-set:
     EVAL "if redis.call('GET', KEYS[1]) < ARGV[1] then
             redis.call('INCR', KEYS[1]) return 1
           else return 0 end" 1 streams:active:{userId} maxStreams

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "What if a payment webhook from Stripe is delivered twice?"

A: Classic duplicate-event problem. Fix: idempotency key.
   Every Stripe webhook has a unique event ID. Before processing:
     IF EXISTS payment_events WHERE stripe_event_id = 'evt_xxx' → skip
     ELSE → process + INSERT stripe_event_id into processed_events table
   This is idempotent — second delivery is a no-op.
   Also: Stripe guarantees at-least-once delivery, not exactly-once.
   Always design payment handlers to be idempotent.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "MongoDB doesn't support transactions — how is manifest URL saved
   atomically with the video status?"

A: This is a single-document update — not a cross-document operation:
     db.videos.updateOne(
       { titleId: "abc" },
       { $set: { manifestUrl: "...", status: "READY" } }
     )
   MongoDB guarantees atomic reads/writes on a single document.
   No multi-document transaction needed here.
   Multi-document transactions (MongoDB 4.0+) exist if needed.
   But the better design is: put both fields in the same document.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 2 — SCALE & FAILURE MODES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "New popular show drops. All 200M users search + click Play
   simultaneously. What breaks first?"

A: Called the thundering herd problem. Three hotspots:
   1. SEARCH: Elasticsearch gets 200M req/sec.
      Fix: Redis cache for top-N search queries (1 min TTL).
      "Stranger Things 5" will be searched 10M times identically.
   2. MANIFEST FETCH: Play Service → Redis → miss → MongoDB spike.
      Fix: Redis should be pre-warmed before the show drops.
      Set manifest cache key manually at publish time (TTL = 24hrs).
   3. CDN: First request for a segment is a cache miss → S3 spike.
      Fix: CDN request collapsing. When 1000 users hit the same
      uncached segment, CDN makes ONE request to S3, not 1000.
      CloudFront does this automatically (Origin Shield).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "What if Kafka goes down mid-payment?"

A: The payment itself is synchronous (Stripe webhook → our DB).
   Payment never goes through Kafka — it hits the DB directly.
   Kafka is only used for DOWNSTREAM events (email, User DB update).
   So if Kafka is down:
   - Payment still succeeds (Stripe already charged the card)
   - Welcome email is delayed (sent when Kafka recovers)
   - User DB update is delayed (subscription_status stays PENDING)
   Fix for delayed User DB: Kafka has persistent storage. When it
   recovers, the consumer replays the event and updates the DB.
   Kafka retention: configure at least 7 days for this topic.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "A user's subscription expires while they're mid-stream.
   What happens?"

A: The heartbeat is the enforcement point.
   Every 30 seconds, client calls POST /stream/heartbeat.
   Play Service validates entitlement on EVERY heartbeat:
     → Check Redis entitlement cache (TTL = 5 min)
     → If subscription expired → return 403
     → Client receives 403 → shows "Your subscription has ended"
   The user gets ~5 minutes of grace (Redis TTL) after expiry.
   That's intentional — we don't want to cut mid-scene exactly at
   the billing second. Acceptable business trade-off.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "Video encoding job fails halfway through 10,000 chunks. How do
   you recover without re-encoding from scratch?"

A: Each chunk is independent — this is exactly why we use Kafka.
   Design the encoder as an idempotent consumer:
   - Each chunk has a unique chunkId (titleId + segmentNumber)
   - Encoder saves progress: { chunkId, status: DONE/FAILED } in DB
   - On failure, Kafka retries the FAILED chunk (not all 10,000)
   - Dead Letter Queue (DLQ): after 3 retries, move to DLQ + alert
   - Re-trigger: re-publish only FAILED chunks to Kafka topic
   Result: failure of chunk #5000 only re-encodes chunk #5000.
   This is why chunked pipeline > monolithic encoding job.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 3 — SECURITY & DRM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "Can't you just use signed URLs instead of DRM? Why pay for
   Widevine/FairPlay?"

A: Signed URLs prove access — they don't protect the content itself.
   A signed URL lets you DOWNLOAD the file. Once downloaded, the
   raw video bytes are in memory/disk — user can copy them.
   DRM encrypts the video. Even if you have the bytes, you can't
   decode them without the decryption key. The key lives in a
   hardware-protected TEE (Trusted Execution Environment) on the
   device. The DRM system also enforces:
   - No screen recording (blocks OBS/screenshot on premium content)
   - No HDCP bypass on HDMI output
   - Key expiry after session ends
   Use BOTH: signed URL for CDN access + DRM for content protection.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "Why not cache DRM license responses in Redis?"

A: DRM licenses are user-specific + device-specific.
   The license encodes: userId, deviceId, titleId, expiry.
   Caching it means User A could potentially get User B's key.
   Also: license expiry is intentionally short (4-8 hours).
   It MUST be re-issued for a new session. Caching defeats this.
   What IS cached: the entitlement check result (Redis, 5min TTL).
   That's separate from the license itself.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 4 — DATA CONSISTENCY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "Why CDC (Debezium) to sync MongoDB → Elasticsearch, instead of
   dual-write (write to both at the same time)?"

A: Dual-write has a fundamental consistency problem:
   Step 1: Write to MongoDB ✓
   Step 2: Write to Elasticsearch ✗ (times out)
   Now MongoDB has the new title. Elasticsearch doesn't.
   Search is broken for that title. No automatic recovery.
   CDC reads the MongoDB oplog AFTER the DB write succeeds.
   It guarantees: if the data is in MongoDB, it WILL reach
   Elasticsearch eventually. At-least-once delivery.
   Also: if Elasticsearch is down, CDC replays from the oplog
   when it recovers. Dual-write has no replay mechanism.
   The only downside of CDC: ~1-5 second search lag.
   Acceptable — content metadata changes are rare.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "Cassandra partition key is profileId. If a power user watches
   10,000 videos, is that a hot partition?"

A: For STORAGE: not a problem. 10,000 rows × ~100 bytes = 1 MB.
   Cassandra handles gigabytes per partition fine.
   For WRITES: 500K writes/sec are spread across 200M profileIds.
   Each profileId gets ~0.0025 writes/sec. No hot partition.
   A hot partition would only happen if one profileId gets
   disproportionate writes — can't happen here (one user = one
   profile = their own heartbeats only).
   Hot partitions in Cassandra happen with categorical keys:
   e.g., partition by country_code → 1.4B users in "IN".
   profileId (UUID) distributes uniformly. No issue.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 5 — ARCHITECTURE DECISIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "Why not use gRPC for all services? It's faster than REST."

A: gRPC IS used for internal service-to-service calls:
   Play Service → DRM Service (high frequency, low latency)
   Play Service → Recommendation Service (same reason)
   REST is used for client-facing APIs because:
   1. Browser support: gRPC requires HTTP/2 + binary framing.
      Not all browsers support it natively.
   2. CDN cacheability: CDN can cache HTTP GET responses.
      gRPC calls are not cacheable by CDN.
   3. Mobile SDK complexity: REST is simpler to implement
      on iOS/Android for public APIs.
   4. Debuggability: REST responses are human-readable JSON.
   Rule: gRPC inside the datacenter, REST at the edge.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "How does quality switching work on a slow connection without
   the user seeing a freeze or rebuffer?"

A: ABR + pre-fetch is the answer. Key insight:
   The client never waits until the current segment finishes to
   request the next one. At 60% through the current segment:
   1. Client measures current bandwidth
   2. Picks quality for next segment (may be lower or higher)
   3. Issues GET for next segment NOW (while still playing)
   4. Next segment arrives before current one ends
   Result: seamless switch, no rebuffer.
   Buffer size also matters: client maintains 2-3 segments
   in the buffer (~20-30 seconds ahead). Even if bandwidth
   drops to zero for 15 seconds, playback continues.
   Only if buffer empties completely does the user see a freeze.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 6 — DISASTER RECOVERY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "Primary region goes down mid-stream for 15M users. What's
   your recovery plan? What's your RPO and RTO?"

A: Multi-region active-passive setup:

   REGIONS:
     Primary:   us-east-1  (handles all writes)
     Secondary: us-west-2  (warm standby, pre-warmed to 10% capacity)
     Tertiary:  ap-south-1 (read replicas, CDN origin)

   DATA REPLICATION (before failure):
     PostgreSQL → streaming replication to us-west-2 (lag <5s)
     S3         → Cross-Region Replication to all regions (minutes)
     Redis      → Sentinel with master-slave (lag <1s)
     Cassandra  → Multi-DC replication, LOCAL_QUORUM reads/writes
     CDN        → Already global — no failover needed

   FAILOVER SEQUENCE:
     t=0s   Region fails. Route53 health checks start failing.
     t=90s  3 consecutive checks fail → Route53 DNS updated
            to point to us-west-2.
     t=4min PostgreSQL in us-west-2 promoted to primary.
     t=5min Auto-scaling groups in us-west-2 scale to 100%.
     t=10m  Service fully restored.

   WHAT USERS EXPERIENCE:
     CDN serves current segment (already buffered 20-40s ahead).
     Next segment fetch fails → player retries → us-west-2 CDN hit.
     Briefly higher latency. No black screen for most users.

   RPO (Recovery Point Objective): <5 seconds
     → PostgreSQL streaming replication lag
   RTO (Recovery Time Objective): <10 minutes
     → Time to DNS propagation + DB promotion + scale-up

   GRACEFUL DEGRADATION (if only DB fails, not full region):
     Read-only mode: users can watch but not subscribe/update profile
     CDN-only mode:  95% of video served from cache even if APIs down

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

QUICK SUMMARY — The 4 things that show 15 YOE thinking:
  1. You mention failure modes (what happens WHEN X fails, not IF)
  2. You mention race conditions (concurrent stream limit, heartbeat)
  3. You explain WHY (CDC vs dual-write, gRPC vs REST, signed URL vs DRM)
  4. You quantify trade-offs (5 min entitlement cache lag is acceptable)
```

---

## KEY NUMBERS — Memorize These

```
┌────────────────────────────────────────────────────────┐
│              NUMBERS TO REMEMBER                        │
├──────────────────────────────┬─────────────────────────┤
│ Total subscribers            │ 200 million             │
│ Videos in catalogue          │ 10,000                  │
│ Peak concurrent streams      │ 15 million              │
│ Peak bandwidth               │ 150 Tbps                │
│ CDN cache hit rate           │ 95%                     │
│ Watch heartbeat writes/sec   │ 500K                    │
│ Segment requests/sec (CDN)   │ 2.5 million             │
│ HLS segment size             │ 6 - 10 seconds          │
│ DASH segment size            │ 2 - 4 seconds           │
│ Video startup target         │ < 2 seconds             │
│ Total storage                │ ~500 PB                 │
│ DRM systems                  │ Widevine / FairPlay /   │
│                              │ PlayReady               │
│ JWT access token TTL         │ 15 minutes              │
│ JWT refresh token TTL        │ 30 days                 │
└──────────────────────────────┴─────────────────────────┘
```

---

*Study order: Step 7 Streaming (20 min) → Step 5 Architecture (15 min) →
Step 4 APIs (10 min) → Step 8 Subscription (10 min) → Rapid Answer (5 min)*

---

## KEY PATTERNS REFERENCED IN THIS DESIGN

> **For the 2-year developer:** These are the hidden concepts behind design decisions in this system. Each has a dedicated deep-dive file.

### Object vs Block vs File Storage
**Why it matters here:** Video bytes → S3 (object storage, unlimited scale, $0.023/GB). Transcoded HLS segments → S3. User/subscription/view-history database → PostgreSQL on EBS (block storage, fast random reads). CDN sits in front of S3 for global delivery.
**Deep dive:** `../../Object_vs_Block_vs_File_Storage_S3_EBS_EFS.md`

### Chunked Upload / Multipart Upload
**Why it matters here:** Content creators upload 50GB+ 4K videos. S3 multipart mandatory for >5GB. Presigned URLs: creator uploads directly to S3 — your servers handle zero video bytes. 5 parallel chunks × creator's bandwidth = 5× upload speed. Resumable.
**Deep dive:** `../../Chunked_Upload_Multipart_Upload.md`

### CDN Origin Pull vs Origin Push
**Why it matters here:** New major release → pre-warm all 220 CDN edges before premiere (origin push). First user anywhere hits cache not S3. Long-tail catalog → origin pull with origin shield (prevents S3 stampede). Cache-Control: HLS segments use immutable + 1-year TTL with content-addressed URLs.
**Deep dive:** `../../CDN_Origin_Pull_vs_Origin_Push.md`

### Blob Storage vs Database
**Why it matters here:** Video thumbnails (100KB–500KB each) as BLOBs in MySQL = catastrophic. At 10M videos: buffer pool is contaminated, backups take days. S3 for thumbnails, DB stores only: thumbnail_s3_key. Subtitles (50KB text) can go in DB — small, rarely accessed, never in hot path.
**Deep dive:** `../../Blob_Storage_vs_Database_For_Files.md`

### Cursor Pagination
**Why it matters here:** Video catalog browsing — 10M videos across genres. OFFSET 200000 = 200K rows scanned per page load. Cursor on (upload_date, video_id): direct index seek, 0 wasted rows. At 1M concurrent browsers: the difference is DB stability.
**Deep dive:** `../../Cursor_Pagination_vs_Offset_Pagination.md`

### Graceful Degradation
**Why it matters here:** Recommendation engine is down → show "Top 10 Trending" (cached, refreshed every 10 minutes). User lands on home screen with content immediately. Recommendation failure is invisible. Define which features are critical (video playback, search) vs non-critical (personalized recommendations, continue-watching sync).
**Deep dive:** `../../Graceful_Degradation.md`

### CAP Theorem
**Why it matters here:** AP for video catalog and recommendations (stale recommendation is fine). CP for billing/subscription status (wrong entitlement = legal issue — during partition, reject subscription changes rather than risk serving premium content to free users).
**Deep dive:** `../../CAP_Theorem_Applied_What_Actually_Breaks.md`

### [Read Replica Lag & Read-Your-Own-Writes](../../Read_Replica_Lag_Read_Your_Own_Writes.md)
**Why this system uses it:** User resumes watching a show on their phone → switches to TV → "Continue Watching" shows the wrong position (replica lag). Netflix tolerates this — "Continue Watching" position can be up to 30 seconds stale (AP system). The write (update watch position) goes to primary. The read ("continue watching" list) comes from replica. Staleness is acceptable: worst case, user re-watches 30 seconds. For subscription status (is user's subscription valid?), always read from primary — stale subscription data = unpaid access.

### [Cache Stampede / Thundering Herd](../../Cache_Stampede_Thundering_Herd.md)
**Why this system uses it:** "Top 10 Trending" content cache expires at midnight. 5 million night-owl users are simultaneously online. All 5M users' homepage loads trigger the trending cache miss simultaneously. Fix: probabilistic early expiry — starting 10 minutes before midnight, a randomly-selected subset of requests triggers a cache refresh. By midnight, the cache has already been refreshed by background refresh; users see continuous fresh trending data with no stampede. Alternatively: cron job refreshes trending at 11:59 PM before cache expires.

### [DynamoDB Single-Table Design + GSI Hot Partitions](../../../aws/21.dynamodb-single-table-design-gsi-hot-partitions-dax.md)
**Why this system uses it:** User watch history and content metadata in DynamoDB. `PK=USER#{id}, SK=WATCHED#{contentId}` for watch history (resume position, completion status). GSI trap: GSI on `genre` hot-partitions on "Action" during launch week. Fix: sparse GSI on `featured_until` date — only promoted content indexed. DAX for content metadata page (thumbnail, title, description) — same 50ms latency globally vs 10ms with DAX.

### [AWS API Gateway — REST vs HTTP vs WebSocket](../../../aws/22.api-gateway-rest-http-websocket-architect-interview.md)
**Why this system uses it:** HTTP API for content catalog browsing (high QPS, cost-sensitive). The 29s timeout forces async transcoding: POST /content/upload returns contentId, transcoding pipeline (FFmpeg, can take 20+ minutes for a feature film) runs asynchronously, client polls GET /content/{id}/status. WebSocket for live sports: real-time score updates pushed to viewer via WebSocket connectionId.

### [Kinesis vs MSK Kafka vs SQS — Streaming Decision](../../../aws/23.kinesis-vs-msk-kafka-vs-sqs-streaming-decision.md)
**Why this system uses it:** Clickstream (play, pause, seek, buffer events) → Kinesis Data Streams (partitionKey=userId) → Kinesis Firehose → S3 Parquet. Athena queries this for viewing analytics and recommendation model training. Enhanced Fan-Out: recommendation engine consumer + fraud detection consumer each get dedicated throughput on the same stream. Content processing uses SQS for transcoding job queue.

### [CloudWatch + X-Ray Observability](../../../aws/24.cloudwatch-xray-observability-architect-interview.md)
**Why this system uses it:** OTT-specific custom metrics: BufferingRatio (rebuffer events per play hour — Netflix target < 0.1%), VideoStartTime P99 (< 2s), BitrateDropRate. P99 alarm: BufferingRatio > 0.5% → triggers CDN pre-warm for that content + auto-scales transcoding workers. X-Ray service map for video playback: API GW → Metadata Service → DynamoDB → CDN origin check — identifies whether slow video start is metadata lookup or CDN miss. Container Insights: transcode workers OOMKill on 4K content → auto-increase pod memory limit.

### [EventBridge — Event Routing](../../../aws/25.eventbridge-scheduler-event-routing-architect-interview.md)
**Why this system uses it:** Content upload event routing: `{"detail-type":"ContentUploaded","detail":{"format":"4K","type":"movie"}}` routes to: 4K transcode Lambda + thumbnail generation Lambda + metadata indexing Lambda + CDN pre-warm Lambda — all triggered simultaneously from one EventBridge rule. EventBridge Scheduler for content expiry: when a licensed movie expires (one-time `at()` schedule) → Lambda removes from catalog, updates DRM. Scheduled content availability: movie premieres at exactly midnight → EventBridge Scheduler publishes to catalog.

### [S3 Data Lake + Athena — Viewing Analytics](../../../aws/26.s3-athena-data-lake-lifecycle-architect-interview.md)
**Why this system uses it:** Viewing events (play, pause, seek, buffer, quality-change) → Kinesis Firehose → S3 Parquet partitioned by date/content/region. Athena: "which content has >20% drop-off in first 5 minutes?" for content quality scoring. "Which region has highest buffering ratio?" for CDN optimization. S3 lifecycle: recent views Standard (hot ML training data) → IA after 90 days → Glacier Deep Archive after 1 year. Cost: Athena queries at $0.05/query vs $2,000/month data warehouse for the same analytics.

### [WAF + Shield + GuardDuty — Security](../../../aws/27.waf-shield-guardduty-security-architect-interview.md)
**Why this system uses it:** OTT platforms face account sharing crackdowns and credential stuffing. WAF rate-based rule: > 100 login attempts/5min from same IP → block (credential stuffing). AWSManagedRulesBotControlRuleSet: blocks headless browsers scraping content catalog. Shield Advanced ($3K/month justified): IPL/World Cup live streams attract DDoS from geo-blocked users — AWS DRT available during major events. GuardDuty: compromised user accounts streaming from 15 different countries simultaneously → HIGH finding → auto-suspend + notify user.

### [Route53 Advanced Routing](../../../aws/29.route53-routing-policies-dns-failover-architect-interview.md)
**Why this system uses it:** Latency-based routing: Indian users → ap-south-1 (Mumbai CDN origin + API), US users → us-east-1 — reduces video start time for each region. Failover: if Mumbai CDN origin unhealthy → Route53 serves from us-east-1 origin (slightly higher latency but no outage). Geolocation routing for content licensing: users in Germany cannot access US-licensed content → Route53 geolocation routes german IPs to EU endpoint which serves EU-licensed catalog only.

### [Multi-Region Architecture](../../../aws/30.multi-region-aurora-global-dynamodb-global-tables.md)
**Why this system uses it:** Active-active global architecture — Netflix serves 190+ countries. DynamoDB Global Tables for user watch history, preferences, continue-watching list (LWW acceptable — last device sync wins). Aurora Global Database for subscription/billing records (consistency needed). Video content: S3 single master (us-east-1) + CloudFront global CDN (content-addressed, no multi-region DB needed). Data residency: EU user watch history stays in eu-west-1 (GDPR) — DynamoDB Global Tables with application-layer residency routing.
