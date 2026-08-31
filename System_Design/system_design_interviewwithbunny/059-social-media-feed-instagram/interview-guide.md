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
GET    /api/v1/posts/feed?limit={limit}&cursor={cursor}   (infinite scroll — cursor-based)
GET    /api/v1/users/{user_id}/posts                      (profile timeline)
```

> **WHY CURSOR-BASED PAGINATION INSTEAD OF PAGE NUMBERS? (Beginner Explanation)**
> Page numbers (offset=0, offset=20, offset=40) seem simple, but imagine scrolling through Instagram. While you scroll, new posts are being added at the top. When you ask for "page 2", the database shifts all rows down — you either see duplicates or skip posts entirely.
> A cursor is a bookmark: "give me the next 20 posts after post_id X, created before timestamp Y". No matter how many new posts arrive, your bookmark stays stable. You always get the next 20 posts cleanly.
> Offset pagination also requires the DB to scan and skip rows (slow at high offsets). Cursor pagination hits an index directly — fast even at post #10,000.

### Interactions
```
POST   /api/v1/posts/{post_id}/like
DELETE /api/v1/posts/{post_id}/unlike
GET    /api/v1/posts/{post_id}/comments
POST   /api/v1/comments/{comment_id}           (reply or new comment)
POST   /api/v1/users/{user_id}/follow
DELETE /api/v1/users/{user_id}/unfollow
```

### Social Graph
```
GET    /api/v1/users/{user_id}/followers?limit={limit}&cursor={cursor}   (who follows this user)
GET    /api/v1/users/{user_id}/following?limit={limit}&cursor={cursor}   (who this user follows)
```

> **WHY SEPARATE FOLLOWERS AND FOLLOWING ENDPOINTS?**
> Every social profile page needs both lists: "1.2M followers" and "800 following" are clickable — users browse them to discover accounts. These are two separate reverse lookups on the Followers table: `SELECT follower_id WHERE followee_id = X` vs `SELECT followee_id WHERE follower_id = X`. Exposing them as two distinct endpoints makes the intent explicit at the API layer and allows independent pagination — a celebrity's followers list may have millions of entries while their following list has 200. Cursor-based pagination (same reason as feed) prevents the offset-shift problem as users follow/unfollow in real time.

### Search
```
GET    /api/v1/search?q={query}&type={users|posts}&limit={limit}&cursor={cursor}
```

> **WHY A DEDICATED SEARCH ENDPOINT?**
> Search is fundamentally different from every other read in this system: it needs full-text tokenisation, hashtag indexing, and autocomplete — none of which PostgreSQL or Cassandra handle well at scale. The `type` parameter routes to the correct Elasticsearch index (`users_index` vs `posts_index`) so a single endpoint serves both user lookup ("@john") and content discovery ("#travel"). Elasticsearch supports 10K searches/sec with sub-100ms autocomplete latency (listed in the Scaling table). Without this endpoint the entire Search functional requirement (FR #6) has no API surface.

### Notifications
```
GET    /api/v1/notifications?limit={limit}&cursor={cursor}              (notification inbox)
PUT    /api/v1/notifications/{notification_id}/read                     (mark one as read)
PUT    /api/v1/notifications/read-all                                   (mark all as read)
```

> **WHY NOTIFICATION READ/UNREAD ENDPOINTS?**
> The notification flow is fully described in the LLD (Kafka → Notification Svc → WebSocket/FCM), but without API endpoints there is no way for a client to fetch the inbox on app launch or mark items read. `GET /notifications` loads stored rows from the Notification DB (PostgreSQL, 30-day TTL) for users who missed the real-time WebSocket push — e.g., after a cold start or offline period. The two `PUT` variants cover the two UX actions: tapping a single notification vs the "Mark all read" button. Using `PUT` (not `POST`) is correct here because the operation is idempotent — calling it twice leaves the resource in the same state.

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

> **WHY CDN EXISTS? (Beginner Explanation)**
> Imagine every Instagram photo stored in a single warehouse in Virginia. Every user in Tokyo, São Paulo, and London waits for the image to travel across the world — 200ms+ per photo, on every scroll.
> A CDN (Content Delivery Network) is a network of caches spread across the globe. The first time someone in Tokyo requests a photo, it fetches from S3 in Virginia and stores a copy at the Tokyo edge server. The next million Tokyo users get it from next door — under 5ms.
> At 10TB of media uploaded daily, serving everything from origin would require enormous bandwidth and latency. CDN cuts that cost by 95% and makes every scroll feel instant regardless of where the user lives.

**Key database choices**:
| Service | DB | Why |
|---------|-----|-----|
| User Svc | PostgreSQL + replicas | Relational, profile lookups |
| Content Svc | Cassandra | High write throughput, partition by user_id |
| Follower Svc | PostgreSQL (or graph DB) | Bidirectional edge queries |
| Engagement | Cassandra (likes), PostgreSQL (comments) | High write volume |
| Feed | Redis | Sub-10ms LRANGE, ephemeral data |

> **WHY SEPARATE POST SERVICE AND FEED SERVICE? (Beginner Explanation)**
> Think of a restaurant: the kitchen (Content/Post Service) cooks and stores food; the waiter (Feed Service) decides what to put on your plate and delivers it. You don't want the waiter running into the kitchen to cook every time a customer orders.
> Content Service owns creating, validating, and storing individual posts. Feed Service owns the personalized timeline — who sees what, assembled in what order, from Redis cache.
> They scale completely differently: Content Service handles 1.2K post writes/sec; Feed Service handles 115K read requests/sec. Bundling them together means you have to scale both even when only one is under pressure — expensive and fragile.

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

> **WHY FANOUT ON WRITE (PUSH MODEL) EXISTS? (Beginner Explanation)**
> Think of a newspaper printing press — it runs once overnight and drops a copy at every subscriber's doorstep before they wake up. When you open the app, your feed is already sitting there, pre-built.
> That's fanout on write: the moment someone posts, the system immediately pushes that post_id into every follower's Redis cache. Reading your feed is instant because the work was done upfront at write time.
> Without it: every time 500M users open the app, each triggers a DB JOIN across posts and followers. That's 115K queries per second hitting the database — it collapses instantly.

#### Pull Model (Fanout on Read) — celebrities >5K followers
```
User loads feed
    → Feed Svc: check Redis feed:{user_id}  (normal users)
    → For each celebrity followed: SELECT * FROM PostDB WHERE user_id = {celebrity_id} LIMIT 100
    → Merge pushed posts + pulled celebrity posts, sort by timestamp
    → Cache merged result in Redis (TTL = 10 min)
```

> **WHY FANOUT ON READ (PULL MODEL) FOR CELEBRITIES? (Beginner Explanation)**
> Selena Gomez has 400M followers. Fanout on write means 1 post = 400M Redis writes in seconds — like trying to print and deliver 400M newspapers simultaneously. The system would catch fire.
> Pull model flips the logic: don't push anything on post creation. When YOU open your feed, the system pulls that celebrity's latest posts on-demand and stitches them in. All 400M followers share the same single cached query result instead of 400M individual cache entries.
> The trade-off: her post takes up to 10 minutes to appear in your feed (the cache TTL). For a social app, nobody notices. For a stock trading app, that would be catastrophic.

#### Hybrid Model (production reality)
```
<5K followers   → pure PUSH   (pre-built feeds)
1K–5K           → hybrid      (push to active followers, pull for inactive)
>5K followers   → pure PULL   (no fanout, query on-demand)
```

> **WHY A HYBRID MODEL? (Beginner Explanation)**
> Pure push breaks for celebrities. Pure pull is slow for everyone else. The hybrid model draws a line at 5K followers.
> Below 5K: you're a normal user — fanout pre-builds your followers' feeds instantly. Above 5K: you're treated as a celebrity — followers pull your posts on-demand at read time.
> This way the system never fans out to millions of caches, but regular users still get sub-10ms feed loads. The 5K threshold is a tunable config, not a magic number — Instagram uses a similar cut-off in production.

### Feed Ranking — Why Not Just Reverse Chronological?

> **WHY FEED RANKING/SCORING EXISTS? (Beginner Explanation)**
> Reverse-chronological (newest first) is simple and fair. But if you follow 500 accounts, the loudest posters bury everyone else — a news account posting 30 times a day drowns out your friend who posts once a week.
> Ranking scores each post by signals: how close are you to the author? how many likes/comments in the first 10 minutes? is this a video (higher engagement)? did you interact with this person recently? Posts you care most about float to the top.
> This system uses reverse-chronological (simpler, covers the interview). In production, Instagram/Facebook run ML ranking models on the assembled feed as a final step before returning it. Mention this as a possible extension if the interviewer probes deeper.

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

> **WHY REDIS FOR FEED CACHE? (Beginner Explanation)**
> Think of Redis as a sticky note on your fridge — you glance at it instantly. The database is a filing cabinet in the basement — accurate, but you have to walk down, find the folder, and read the document.
> At 115K feed loads per second, going to the filing cabinet every time would be catastrophic. Redis stores each user's feed as a pre-built LIST of 1000 post_ids, readable in under 10ms with a single LRANGE command.
> Feed data is also ephemeral — if Redis loses it (crash, restart), the worst case is a slightly slower feed load while it rebuilds from the database. You'd never notice. That's what makes it safe to treat as a cache rather than a source of truth.

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

> **WHY LIKE COUNTERS ARE HARD TO UPDATE? (Beginner Explanation)**
> Imagine a viral post getting 50,000 likes in one minute. Every like needs to increment a single counter in a database row. In a normal DB, that means: read the current value → add 1 → write it back. With 50,000 concurrent requests, each one waits for a lock on that row — requests pile up, the database slows down, everything breaks. This is called a write hotspot.
> The solution: Redis INCR is atomic and lock-free. It handles 100K increments per second on a single key without anyone waiting. The trade-off: Redis isn't the source of truth. A background job every 5 minutes counts the real rows in the Like DB and syncs the number back.
> You might show "10,234 likes" when the true count is 10,241. For a social app, a 5-minute lag is invisible. For a bank balance, it would be a disaster.

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

> **WHY NOT A GRAPH DATABASE FOR FOLLOWERS? (Beginner Explanation)**
> A social graph is all about relationships: "friends of friends", "people you both follow", "second-degree connections". A graph database (like Neo4j) stores these as nodes and edges natively — traversing three hops is a single graph walk instead of three nested JOINs.
> For simple follower lookups (who follows user X?), PostgreSQL with an index on `followee_id` is fast enough and much simpler to operate. Graph DBs earn their place only when you need multi-hop traversals at scale — like Facebook's "people you may know" recommendations.
> This system uses PostgreSQL for followers. If the interviewer asks about friend-of-friend suggestions, that's when you bring up Neo4j or a dedicated graph layer.

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

---

## KEY PATTERNS REFERENCED IN THIS DESIGN

> **For the 2-year developer:** These are the hidden concepts that make this design work. Each one has a dedicated deep-dive file. When asked "why did you choose X?" in your interview — these are the reasons.

### Fan-Out on Write vs Fan-Out on Read
**Why it matters here:** This is the core feed architecture decision for the entire system. Regular users (<10K followers): fan-out on write — push post_id to all follower Redis feeds on post creation. Celebrities (millions of followers): fan-out on read — pull their posts at feed read time. The hybrid model is the production answer and the interviewers' expected conclusion.
**Deep dive:** `../../Fan_Out_Write_vs_Fan_Out_Read.md`

### N+1 Query Problem
**Why it matters here:** Feed loads 20 posts → ORM lazily fetches each post's author profile → 21 queries instead of 1. At 1M users loading feeds simultaneously, that's 21M DB queries/second instead of 1M. This is the most common backend scaling mistake and interviewers probe it directly in feed system designs. Fix: JOIN FETCH or @EntityGraph.
**Deep dive:** `../../N_Plus_1_Query_Problem.md`

### Index Types
**Why it matters here:** Composite B-tree index on (user_id, created_at DESC) for the user timeline query. The left-prefix rule means this single index serves both "all posts by user X" and "posts by user X after date Y" — avoiding redundant indexes and keeping the timeline query at O(log N + K) instead of a full table scan.
**Deep dive:** `../../Index_Types_BTree_Hash_Composite_Covering.md`

### Cursor Pagination
**Why it matters here:** Infinite scroll feed. OFFSET 9980 LIMIT 20 forces the DB to scan and discard 9,980 rows on every scroll. Cursor on (created_at, post_id) is a direct index seek — always scans exactly 20 rows regardless of how deep in the feed the user has scrolled. At 1M concurrent users, this is the difference between O(N) and O(1) per scroll event.
**Deep dive:** `../../Cursor_Pagination_vs_Offset_Pagination.md`

### Graceful Degradation
**Why it matters here:** When the recommendation service is down, the feed should fall back to showing popular posts from a cached static list rather than returning a 503. The user sees content and the recommendation failure is invisible. This is the difference between a partial outage and a full user-facing outage.
**Deep dive:** `../../Graceful_Degradation.md`

### CAP Theorem
**Why it matters here:** Social media feed is AP — during a partition, your feed may be 30 seconds stale or show slightly out-of-order posts. That is completely acceptable. Users must be able to scroll their feed even during partial failures. Availability far outweighs consistency for a feed; no one needs millisecond-perfect ordering of cat photos.
**Deep dive:** `../../CAP_Theorem_Applied_What_Actually_Breaks.md`

### [Database Sharding](../../Database_Sharding_Range_Hash_Consistent_Hashing.md)
**Why this system uses it:** Users table sharded by `user_id` (consistent hashing). Posts table sharded by `user_id` (same shard key keeps user's posts co-located — fan-out query hits one shard). Avoid sharding by `created_at` — all new posts would go to the "current" shard, creating a permanent hot shard. Redis Cluster for feed cache uses consistent hashing with 16,384 slots across shards.

### [Read Replica Lag & Read-Your-Own-Writes](../../Read_Replica_Lag_Read_Your_Own_Writes.md)
**Why this system uses it:** User posts to Instagram → immediately views their own profile → post isn't there. This is read replica lag. Fix: for 5 seconds after a write, route that user's reads to the primary. The session token carries a `last_write_timestamp`; the API gateway routes to primary if `current_time - last_write < 5s`. After 5s, back to replica. All other users can tolerate the replica lag (they don't know you just posted).

### [Cache-Aside vs Write-Through vs Write-Behind](../../Cache_Aside_vs_Write_Through_vs_Write_Behind.md)
**Why this system uses it:** Feed cache (Redis sorted set) uses write-through on fan-out — when a post is created, the fan-out worker writes to both DB and all followers' feed caches simultaneously. User profile cache uses cache-aside — lazy populate on first read, invalidate on profile update. TTL = 5 minutes with random jitter (±30s) to prevent synchronized expiry stampede on popular profiles.

### [Cache Stampede / Thundering Herd](../../Cache_Stampede_Thundering_Herd.md)
**Why this system uses it:** Trending topics cache expires every 5 minutes. At expiry, all dashboard users hit the trending computation simultaneously. Solution: stale-while-revalidate — serve the stale trending list immediately from cache and trigger a background refresh. Users see trends that are at most 5 minutes old while the refresh runs. The async refresh updates the cache without any user request waiting for it.

### [Bloom Filter + HyperLogLog](../../Bloom_Filter_HyperLogLog_Approximate_Data_Structures.md)
**Why this system uses it:** Feed deduplication — "has user X already seen post Y?" With 1B users × 1000 posts each, an exact set is impossibly large. Per-user Bloom filter for "seen post IDs" enables O(1) deduplication before adding a post to the feed. HyperLogLog for "unique daily active users" — 100M DAU counter with 0.81% error using 12KB, instead of a 800MB exact set.

### [Kafka Partition Key & Consumer Groups](../../Kafka_Partition_Key_Consumer_Groups_Rebalancing.md)
**Why this system uses it:** Feed generation events keyed by `author_id` — all posts from one author go to the same partition, ensuring ordered fan-out (post 2 never fans out before post 1). Consumer group = fan-out workers: 12 partitions, 12 worker instances = 1 partition per worker. Hot partition risk: celebrity with 500M followers generates massive fan-out events from one partition. Mitigation: cap fan-out at 1000 followers per event; break into 500K batches.

### [Hot Partition Problem](../../Hot_Partition_Problem_And_Solutions.md)
**Why this system uses it:** Celebrity users (Cristiano Ronaldo, 500M followers) produce vastly more events than average users. Kafka partition key = `author_id` → all celebrity events on one partition → that consumer drowns while others are idle. Solution: for verified celebrity accounts, use a dedicated high-capacity partition; for normal users, hash partition as usual. Alternatively: key fan-out events by `batch_id` (celebrity_id + batch_sequence) to spread across partitions.

### [Cache Eviction — LRU, LFU, TTL](../../Cache_Eviction_LRU_LFU_TTL_Redis_Policies.md)
**Why this system uses it:** Feed cache in Redis uses `allkeys-lfu` — celebrity profiles and trending posts are accessed thousands of times per hour (high LFU frequency counter) and must stay in cache. A one-time visitor's profile accessed once gets a low frequency counter and is evicted first when memory is full. This is the opposite of LRU behavior, which would incorrectly evict a celebrity profile that was accessed 5 minutes ago in favor of a one-time profile accessed 30 seconds ago.

### [Negative Caching](../../Negative_Caching_Cache_Miss_Storm.md)
**Why this system uses it:** Username availability checks ("is @batman taken?") and profile lookups for non-existent users (typos, deleted accounts) hammer the user DB if not cached. Cache "user not found" for 30 seconds. Deleted/suspended account lookups: cache the "not found" result immediately on deletion to prevent stale positive cache entries from serving profile data after deletion. TTL kept short (30s) so newly-created usernames become available quickly after creation.
