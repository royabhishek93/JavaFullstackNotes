Social Media Platform — Interview Guide (Facebook / Instagram)

> One-liner to open with: "Graph database for social connections → Fanout on write for feed generation → CDN for media delivery → Redis cache for hot data"

---

## Step 1: Clarify Requirements (2 min)

### Functional Requirements
| # | Feature | Notes |
|---|---------|-------|
| 1 | Register / Login | Profile management |
| 2 | Create post | text / image / video, up to 500MB |
| 3 | Follow users | Unidirectional follow OR bidirectional friend-request |
| 4 | Like / Comment | Nested threads, reaction types |
| 5 | View feed | Personalized, posts from followed users, reverse-chrono |
| 6 | Search | Users, hashtags, posts with autocomplete |
| 7 | Notifications | Likes, comments, follows, mentions |

### Non-Functional Requirements
- **Scale**: 500M DAU, 2B registered users
- **Volume**: 100M posts/day → 1.2K posts/sec
- **Read/Write**: 100:1 (heavy reads)
- **CAP**: Availability >> Consistency (eventual consistency acceptable)
- **Latency**: Feed load <500ms, Likes/Comments <200ms, Post creation <300ms
- **Media**: 10TB uploaded daily, petabytes total

---

## Step 2: Core Entities (1 min)

```
User          user_id, username, email, bio, profile_pic_url, followers_count (denorm)
Post          post_id, user_id, content, media_urls[], visibility, likes_count (denorm)
Followers     follower_id, followee_id, status (pending/accepted), created_at
Like          post_id + user_id (composite PK), reaction_type
Comment       comment_id, post_id, parent_comment_id (NULL = top-level), likes_count
Feed          feed:{user_id} → Redis LIST of post_ids (latest 1000)
```

---

## Step 3: API Design (2 min)

### User Onboarding
```
POST   /api/v1/users/register          → {user_id, token}
POST   /api/v1/users/login             → {token}
GET    /api/v1/users/{user_id}/profile
PUT    /api/v1/users/{user_id}/profile
```

### Post Operations
```
POST   /api/v1/posts                                       → 202 Accepted (async fanout)
GET    /api/v1/posts/{post_id}
PUT    /api/v1/posts/{post_id}                             (author only)
DELETE /api/v1/posts/{post_id}                             (soft delete)
GET    /api/v1/posts/feed?limit={limit}&offset={offset}   (infinite scroll)
GET    /api/v1/users/{user_id}/posts                      (profile timeline)
```

### Interactions
```
POST   /api/v1/posts/{post_id}/like
DELETE /api/v1/posts/{post_id}/unlike
GET    /api/v1/posts/{post_id}/comments
POST   /api/v1/comments/{comment_id}           (reply or new comment)
POST   /api/v1/users/{user_id}/follow
DELETE /api/v1/users/{user_id}/unfollow
```

---

## Step 4: High Level Design

```
                         ┌──────────────┐
                         │   User DB    │ (PostgreSQL + read replicas)
                         │  (postgres)  │
                         └──────────────┘
                               ▲
                         ┌──────────────┐
              ┌──────────│  User Svc    │
              │          └──────────────┘
              │
              │          ┌──────────────┐    ┌──────────┐
              ├──────────│ Content Svc  │───▶│  Post DB │ (Cassandra)
              │          └──────────────┘    └──────────┘
              │                │
              │                ▼
┌─────────┐   │          ┌──────────────┐
│users /  │──▶│ API GW & │              │    (media files)
│clients  │   │ LB       │     S3       │◀── CDN (CloudFront)
└─────────┘   │          └──────────────┘
              │
              │          ┌──────────────┐    ┌──────────────┐
              ├──────────│  Feed Svc    │───▶│  Feed Cache  │ (Redis)
              │          └──────────────┘    └──────────────┘
              │
              │          ┌──────────────┐    ┌──────────────┐
              ├──────────│ Follower Svc │───▶│ Follower DB  │ (PostgreSQL/Graph)
              │          └──────────────┘    └──────────────┘
              │
              │          ┌──────────────┐    ┌────────────┐
              └──────────│Engagement Svc│───▶│ Comment DB │ (PostgreSQL)
                         └──────────────┘    └────────────┘
                                             ┌────────────┐
                                             │  Like DB   │ (Cassandra)
                                             └────────────┘
```

**API Gateway responsibilities**: Authentication/JWT, Rate Limiting (1K req/min per user), Routing

**Key database choices**:
| Service | DB | Why |
|---------|-----|-----|
| User Svc | PostgreSQL + replicas | Relational, profile lookups |
| Content Svc | Cassandra | High write throughput, partition by user_id |
| Follower Svc | PostgreSQL (or graph DB) | Bidirectional edge queries |
| Engagement | Cassandra (likes), PostgreSQL (comments) | High write volume |
| Feed | Redis | Sub-10ms LRANGE, ephemeral data |

---

## Step 5: Low Level Design (Deep Dive)

### Architecture Overview
```
                                                    ┌─────────────────────────────────┐
                                                    │  Post Schema (Cassandra)        │
                                                    │  - post_id, user_id, post_type  │
                                                    │  - content/text, media_url      │
                                                    │  - thumbnail_url, share_count   │
                          ┌──────────────┐          │  - like_count, comment_count    │
              ┌───────────│   User Svc   │──▶UserDB │  - metadata                     │
              │           └──────────────┘          └─────────────────────────────────┘
              │
              │           ┌──────────────┐          ┌──────────────────┐
              ├───────────│ Content Svc  │──────────▶│   PostDB         │──▶ S3
              │           └──────────────┘          └──────────────────┘
              │                 │                          ▲
              │         Post Serializer               Post Consumer Svc
              │                 │                    (text/metadata, image/video)
              │                 ▼
┌─────────┐   │ API GW  ┌──────────────┐   raw_post    ┌──────────────┐
│users /  │──▶│ & LB    │    Kafka     │──────────────▶│ Notification │
│clients  │   │         └──────────────┘   filtered     │    Svc       │
└─────────┘   │                │           blocked       └──────────────┘
              │                ▼
              │           ┌──────────┐  <post, List<FriendsUserId>>   ┌─────────────┐
              │           │  Fanout  │─────────────────────────────▶  │   Kafka     │
              │           │  Svc     │                                └──────┬──────┘
              │           │  (PUSH)  │                                       │
              │           └──────────┘                              Fanout Consumer
              │                │                                            │
              │           Redis (author_latest_post,                        ▼ -write
              │           reset DB post)                          ┌──────────────────┐
              │                                                   │   Feed Cache     │◀── -read
              │           ┌──────────────┐                       │   (Redis)        │
              ├───────────│  Feed Svc    │──read──────────────────┤                  │
              │           └──────────────┘                       └──────────────────┘
              │                 │                                       -write ▼
              │         Followers Cache                            ┌──────────────────┐
              │         (top followers)                            │    FeedDB        │
              │                                                    └──────────────────┘
              │           ┌──────────────┐
              ├───────────│ Follower Svc │──▶ FollowerDB (postgres)
              │           └──────────────┘   - follow_id, follower_id, following_id
              │                              - status, timestamp, metadata
              │           ┌─────────────┐
              │    Kafka──▶Engagement   │──▶ Comment DB
              └───────────│    Svc      │    - comment_id, post_id, user_id
                          └─────────────┘    - like_count, metadata
                                         ──▶ Like DB (postgres)
                                             - like_id, post_id/comment_id
                                             - user_id, reaction_type, metadata
```

### Feed Generation — The Core Problem

#### Push Model (Fanout on Write) — normal users <5K followers
```
User posts
    → Kafka 'post.created'
    → Fanout Svc reads event
    → Query FollowerDB: SELECT follower_id WHERE followee_id = poster_id   (e.g. 500 followers)
    → For each follower: LPUSH feed:{follower_id} {post_id}
                         LTRIM feed:{follower_id} 0 999   (keep latest 1000)
    → Feed pre-built, read is instant: LRANGE feed:{user_id} 0 19  → <10ms
```

#### Pull Model (Fanout on Read) — celebrities >5K followers
```
User loads feed
    → Feed Svc: check Redis feed:{user_id}  (normal users)
    → For each celebrity followed: SELECT * FROM PostDB WHERE user_id = {celebrity_id} LIMIT 100
    → Merge pushed posts + pulled celebrity posts, sort by timestamp
    → Cache merged result in Redis (TTL = 10 min)
```

#### Hybrid Model (production reality)
```
<5K followers   → pure PUSH   (pre-built feeds)
1K–5K           → hybrid      (push to active followers, pull for inactive)
>5K followers   → pure PULL   (no fanout, query on-demand)
```

### Post Creation Flow
```
1. Client: POST /api/v1/posts  {content, media_files, visibility, mentions}
2. Content Svc: validate JWT, content length <5000, media <500MB
3. Media path: generate presigned S3 PUT URL (valid 15 min)
       → client uploads direct to S3
       → S3 triggers Lambda: resize images (150/400/1080px), transcode video (360/720/1080p HLS)
4. Create Post row in Cassandra: partition_key=user_id, clustering_key=created_at DESC
5. Publish to Kafka 'post.created': {post_id, user_id, created_at, media_urls}
6. Return 202 Accepted immediately  ← fanout is ASYNC
```

### Feed Load Flow
```
Client: GET /api/v1/posts/feed?limit=20&offset=0

Step 1 (10ms):  LRANGE feed:{user_id} 0 19           → 20 post_ids from Redis
Step 2 (50ms):  SELECT * FROM PostDB WHERE post_id IN (...)   → post content
Step 3 (30ms):  SELECT * FROM UserDB WHERE user_id IN (...)   → author profiles (or cache)
Step 4 (20ms):  MGET likes_count:{post_id} x20              → engagement counts Redis

Total: ~110ms  (well under 500ms target)
```

### Like Interaction — Idempotency
```
Client: POST /api/v1/posts/{post_id}/like

1. Client-side: debounce 300ms, disable button (optimistic UI)
2. Redis: SETNX like:{user_id}:{post_id}  → if 0, already liked → return 200
3. Like DB: INSERT (post_id, user_id) — Cassandra composite PK prevents duplicate
4. Redis: INCR likes_count:{post_id}
5. Kafka: publish 'post.liked' → Notification Svc
6. Background job (5 min): COUNT(*) from Like DB → sync to PostDB (source of truth)
```

### Follow / Unfollow
```
Follow:
  1. INSERT INTO Followers (follower_id, followee_id)
  2. INCR followers_count:{followee_id}, INCR following_count:{follower_id} in Redis
  3. Backfill: add followee's last 100 posts to follower's feed in Redis

Unfollow:
  1. DELETE FROM Followers
  2. DECR counts
  3. LREM feed:{follower_id} — purge followee's posts from feed
```

### Notification Flow
```
Kafka topics consumed: 'post.liked', 'post.commented', 'user.followed'
    → Check user preferences (notification settings)
    → Aggregate: 5 likes within 5 min → "John and 4 others liked your post"
    → Deliver: WebSocket (in-app active users) / FCM/APNS (mobile background)
    → Store in Notification DB (PostgreSQL) for inbox, clean after 30 days
```

---

## Step 6: Database Schema

### Users (PostgreSQL)
```sql
user_id          UUID PRIMARY KEY
username         VARCHAR(50) UNIQUE INDEXED
email            VARCHAR(255) UNIQUE INDEXED
password_hash    VARCHAR(255)          -- bcrypt cost=12
bio              TEXT                  -- max 500 chars
profile_pic_url  VARCHAR(500)
followers_count  BIGINT DEFAULT 0      -- DENORMALIZED
following_count  BIGINT DEFAULT 0      -- DENORMALIZED
posts_count      BIGINT DEFAULT 0      -- DENORMALIZED
created_at       TIMESTAMP
```

### Posts (Cassandra)
```
PRIMARY KEY: (user_id, created_at DESC, post_id)
             ^^^^^^^^ partition    ^^^^^^^^^^^^^^^^ clustering (newest first)

post_id       uuid
content       text               -- max 5000 chars
media_urls    list<text>         -- S3 URLs
visibility    text               -- public / friends / private
likes_count   bigint             -- DENORMALIZED, updated by background job
comments_count bigint
hashtags      set<text>
is_deleted    boolean            -- soft delete
```

### Followers (PostgreSQL)
```sql
follower_id   UUID
followee_id   UUID
status        ENUM('pending','accepted')
created_at    TIMESTAMP
PRIMARY KEY (follower_id, followee_id)
INDEX ON followee_id                   -- reverse lookup: find all followers
```

### Likes (Cassandra — high write volume)
```
PRIMARY KEY: (post_id, user_id)         -- enforces uniqueness
reaction_type text                      -- like/love/haha/wow/sad/angry
created_at    timestamp
```

### Comments (PostgreSQL — nested threads)
```sql
comment_id          UUID PRIMARY KEY
post_id             UUID INDEXED
user_id             UUID
parent_comment_id   UUID NULL           -- NULL = top-level; UUID = reply
content             TEXT               -- max 2000 chars
likes_count         BIGINT DEFAULT 0
reply_count         BIGINT DEFAULT 0   -- DENORMALIZED for "Show N replies"
created_at          TIMESTAMP INDEXED
is_deleted          BOOLEAN
INDEX ON (post_id, parent_comment_id, created_at)
```

### Redis Key Patterns
```
feed:{user_id}                LIST     → post_ids (LPUSH, LTRIM 1000)
likes_count:{post_id}         STRING   → INCR/DECR
comments_count:{post_id}      STRING   → INCR/DECR
like:{user_id}:{post_id}      STRING   → exists = liked (idempotency, TTL=24h)
followers_count:{user_id}     STRING   → synced to PostgreSQL hourly
author_latest_post:{user_id}  STRING   → cache for celebrities
```

---

## Step 7: Key Numbers

| Metric | Value |
|--------|-------|
| DAU | 500M |
| Posts/day | 100M = 1.2K/sec |
| Feed loads/day | 10B = 115K req/sec |
| Read/Write ratio | 100:1 |
| Feed load latency (p95) | <500ms |
| Like/Comment latency (p95) | <200ms |
| Feed cache TTL | 10 min |
| Feed size per user | 1000 posts ≈ 1MB |
| Push model threshold | <5K followers |
| Pull model threshold | >5K followers |
| CDN cache hit rate | 95% |
| Redis DB load reduction | 90% |
| Like count sync interval | 5 min |

---

## Step 8: Common Interview Questions

**Q: Why fanout on write for normal users?**
100:1 read/write ratio. Pre-generating feeds means 1 slow write enables 100 fast reads. LRANGE from Redis = <10ms. For celebrities with 10M followers, 1 post = 10M writes → impractical, so switch to pull.

**Q: How to handle the celebrity hotspot?**
(1) Flag users as celebrity if followers_count > 5K in User table.
(2) Celebrity posts → PostDB only, skip fanout.
(3) Feed load: merge pushed posts (LRANGE) + pulled celebrity posts (query PostDB).
(4) Celebrity posts cached in Redis with higher TTL (1hr vs 10min), all followers share same cache.

**Q: How to ensure like count consistency between cache and DB?**
Eventual consistency: Redis INCR is fast and best-effort. Cron job every 5 min queries `SELECT COUNT(*) GROUP BY post_id` from Like DB → updates PostDB. If Redis count differs from DB by >10%, invalidate and reload. Redis crash → background job rebuilds within 5 min. Accept ±5% drift for <5 min (not a financial system).

**Q: How to prevent duplicate likes?**
3-layer idempotency: (1) Client-side: debounce 300ms + disable button. (2) Redis: `SETNX like:{user_id}:{post_id}` — if key exists, already liked. (3) Cassandra composite PK (post_id, user_id) — duplicate insert fails silently.

**Q: How to handle nested comments efficiently?**
Schema: `parent_comment_id` (NULL = top-level). Load strategy: fetch top-level first (`WHERE parent_comment_id IS NULL LIMIT 20`), lazy-load replies on expand. Max depth = 3 levels. Index: `(post_id, parent_comment_id, created_at)`.

**Q: Why Redis for feed instead of database?**
(1) Speed: LRANGE = <10ms vs DB query = 100ms+. (2) Scale: Redis handles 100K ops/sec. (3) Feed is ephemeral — loss acceptable (rebuild from DB). (4) Reduces DB load by 90%.

**Q: What happens when a user with 1M followers posts?**
Celebrity flag bypasses fanout entirely. Post written to PostDB only. Followers see it on next feed load (pull). Notifications batched — top 1000 engaged followers notified immediately, rest get digest. Prevents: 1M DB writes + 1M Redis writes + 1M push notifications.

**Q: How to handle media upload failures?**
Presigned S3 URL (15 min expiry) → chunked multipart upload (5MB chunks, 10 parallel). Progress in Redis: `upload:{upload_id} = {chunks_uploaded, total_chunks}`. On failure: query missing chunks, upload only those. `POST /upload/{id}/complete` assembles in S3. Exponential backoff (1s, 2s, 4s), circuit breaker after 3 failures.

**Q: How to implement real-time notifications?**
WebSocket + Redis pub/sub: Client opens WS on app launch (JWT auth). Server subscribes to `notifications:{user_id}` Redis channel. Engagement event → Redis pub/sub → WS push to client. Offline: store in Notification DB, deliver on reconnect. Mobile: FCM/APNS instead of persistent WS.

**Q: How to handle privacy controls?**
`visibility` enum on Post (public/friends/private). Fanout on write: only push to follower's feed if `visibility=public` OR `visibility=friends AND is_mutual_follower`. Direct access: check relationship at read time. Mutual follow = bidirectional edge in Followers table. Privacy check cached: `friend:{A}:{B}` in Redis (TTL=1hr).

**Q: How to scale at 500M DAU?**
DB sharding by user_id (1000 shards). 5 PostgreSQL read replicas (99% reads). Redis caching cuts DB load 90%. CDN 95% cache hit for media. Kafka decouples write from fanout. Denormalization avoids COUNT(*) queries. Connection pooling (100 connections/server × 50 servers = 5K total).

---

## Step 9: Scaling Techniques

| Technique | Impact |
|-----------|--------|
| Cassandra sharding by user_id | Horizontal scale for posts |
| PostgreSQL read replicas (×5) | 99% reads hit replicas |
| Redis feed cache (TTL=10min) | 90% fewer DB queries |
| CDN (CloudFront) | 95% media cache hit, <50ms |
| Kafka async fanout | Decouples post creation from propagation |
| Denormalization (like/follower counts) | 100ms COUNT → 1ms field read |
| Batch like count sync (5min) | 100× fewer DB writes |
| Elasticsearch for search | 10K searches/sec, <100ms autocomplete |
| Rate limiting (1K req/min) | Prevents abuse |
| Lazy loading (20 posts/scroll) | Page load 5s → 500ms |

---

## Critical Don'ts (Interviewer Red Flags)

- NEVER fanout on write for celebrities (1 post = 10M writes = system overload)
- NEVER store media as BLOBs in DB (use S3 + store URLs only)
- NEVER process video synchronously (return 202, transcode async via Lambda)
- NEVER use strong consistency for like counts (eventual consistency is fine)
- NEVER forget idempotency for likes (Redis SETNX + Cassandra composite PK)
- NEVER skip the hybrid fanout model — it's what makes the system scale

---

## Interview Flow Cheatsheet

```
1. Requirements   (2 min)  → Functional + NFR, confirm DAU/scale
2. Core Entities  (1 min)  → User, Post, Follower, Like, Comment, Feed
3. API Design     (2 min)  → CRUD + feed + interactions
4. HLD            (5 min)  → 6 microservices + their DBs + API Gateway
5. Deep Dive      (10 min) → Feed generation (push/pull/hybrid) + fanout via Kafka
6. Scaling        (5 min)  → Redis, CDN, sharding, replicas, denormalization
7. Q&A            (5 min)  → Celebrity problem, idempotency, consistency
```
