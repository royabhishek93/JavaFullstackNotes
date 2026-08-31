# Instagram / News Feed — Interview Script
## Design Instagram / Facebook Feed / Twitter Timeline
### Speak This Word-for-Word to Your Interviewer

> **How to use this:**
> **Step 1 — Read Big Picture** (PAGE 1): burn the overview into your head.
> **Step 2 — Read Glossary** (PAGE 2): know every term before the deep-dive.
> **Step 3 — Read Component Choices** (PAGE 3): know WHY each tech was chosen.
> **Step 4 — Read the Interview Script** (PAGE 4 onward): speak each step aloud 2-3 times.
>
> **Print tip:** Portrait A4 at 10pt monospace. Glossary → landscape if needed.

---

# ═══════════════ PAGE 1 — START HERE ═══════════════

## BIG PICTURE (Understand This Before Anything Else)

> **► STUDY this diagram, don't draw it ◄**
> The ENTIRE design lives or dies on one question:
> "Cristiano Ronaldo posts. He has 200M followers. Do you write to all 200M Redis caches?"
> The answer is NO — that's the celebrity problem. The hybrid fan-out solves it.

```
┌─────────────────────────────────────────────────────────────────────┐
│            INSTAGRAM / NEWS FEED — BIG PICTURE                       │
└─────────────────────────────────────────────────────────────────────┘

WRITE PATH: User creates a post
                    │
                    ▼
          ┌──────────────────┐
          │  Post Service    │
          │  • Save to DB    │
          │  • Publish Kafka │
          └────────┬─────────┘
                   │ Kafka: post-created
                   ▼
          ┌──────────────────────────────────────────────┐
          │  Fan-out Worker                               │
          │                                              │
          │  poster.followerCount < 10K?  → PUSH         │
          │    ZADD feed:{followerId} score postId        │
          │    for ALL followers → fast, small set        │
          │                                              │
          │  poster.followerCount >= 10K? → SKIP fan-out │
          │    Celebrity: just stored in Posts DB.        │
          │    Users pull at read time.                   │
          └──────────────────────────────────────────────┘

READ PATH: User loads their feed
                    │
                    ▼
          ┌──────────────────────────────────────────────┐
          │  Feed Service                                 │
          │                                              │
          │  1. Read feed:{userId} from Redis            │
          │     (pre-computed postIds from normal users) │
          │                                              │
          │  2. Fetch list: celeb_followees:{userId}     │
          │     For each celebrity they follow → pull    │
          │     their recent posts from Redis/DB         │
          │                                              │
          │  3. Merge + Rank → return top 20             │
          └──────────────────────────────────────────────┘

STORAGE LAYER:
  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐
  │  Redis       │  │  Cassandra    │  │  S3 + CDN        │
  │              │  │               │  │                  │
  │ feed:{uid}   │  │ posts table   │  │ media (images,   │
  │  sorted set  │  │ followers table│  │ videos,          │
  │ like counts  │  │ followees table│  │ thumbnails)      │
  │ celeb cache  │  │ comments table│  │ served via CDN   │
  └──────────────┘  └───────────────┘  └──────────────────┘

THE CORE INSIGHT:
  Reads >> Writes (100:1 ratio). Optimize for reads.
  Celebrity posts: 200M followers × 1 write each = IMPOSSIBLE.
  Hybrid: push for regular users, pull for celebrities.
  Feed read = Redis lookup + celebrity pull merge. Sub-200ms.
```

---

## RAPID ANSWER — If You Only Have 5 Minutes

*Read this first. Understand the whole answer before going deep.*

```
"I'd design Instagram with five pieces:

1. WRITE PATH (Post Service + Kafka):
   User creates post → Post Service saves to Cassandra, uploads
   media to S3 via presigned URL. Publishes 'post-created' to Kafka.
   Fan-out Worker consumes: if poster has < 10K followers → push
   postId to all followers' Redis feed caches (ZADD). If celebrity
   (>= 10K followers) → skip fan-out. Just store in Cassandra.

2. READ PATH (Hybrid Fan-out):
   Feed Service fetches pre-computed Redis sorted set for user
   (contains postIds from normal users). Also identifies which of
   the user's followees are celebrities → pulls their recent posts
   from a hot Redis cache. Merges both. Ranks. Returns top 20.
   This solves the CELEBRITY PROBLEM — no 200M write storm.

3. FEED RANKING (Two-level):
   Level 1: Pull 200 candidates from Redis feed cache.
   Level 2: Apply ranking signals (recency, likes/comments/shares
   per unit time, user affinity with poster). Return top 20.
   Score = (likes×1 + comments×3 + shares×5) / (hours_old + 2)^1.5

4. STORAGE (Cassandra + Redis + S3):
   Cassandra: posts, followers, followees, comments.
   Redis: pre-computed feed sorted sets (max 500 per user),
   like counts (INCR — atomic), celebrity post cache.
   S3 + CDN: all media (images, videos, thumbnails). CDN is the
   biggest read traffic reducer — media never hits our app servers.

5. SOCIAL GRAPH (Two Cassandra tables):
   Need TWO directions for follow queries:
   followers_by_user: partition=followee → who follows X? (fan-out)
   followees_by_user: partition=follower → who does X follow? (feed read)
   1 trillion follow relationships × 16 bytes = 16 TB. Cassandra."
```

---

# ═══════════════ PAGE 2 — GLOSSARY ═══════════════

## Terminology — Know These Before Reading Further

*Print tip: switch to landscape or 9pt font if table wraps.*

```
┌──────────────────┬──────────────────────────────────────────────────────┐
│ Term             │ What It Means (Simply)                               │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Fan-out          │ When user A posts, distributing that post to all of  │
│                  │ A's followers' feeds. 1 write → N writes.            │
│                  │ Fan-out ratio = number of followers.                 │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Fan-out on Write │ Push model. When a post is created, immediately      │
│ (Push model)     │ push the postId to every follower's Redis feed cache.│
│                  │ Fast reads. Problematic for celebrities.             │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Fan-out on Read  │ Pull model. When user opens their feed, fetch posts  │
│ (Pull model)     │ from all the people they follow at that moment.      │
│                  │ Simple writes. Slow reads (500 DB queries per open). │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Hybrid Fan-out   │ Push for normal users (< 10K followers).             │
│                  │ Pull for celebrities (>= 10K followers).             │
│                  │ Merge both at read time. Instagram's actual approach.│
├──────────────────┼──────────────────────────────────────────────────────┤
│ Celebrity        │ A user with >= 10K followers. Special handling       │
│ Problem          │ needed: writing to 200M Redis keys for one post      │
│                  │ takes minutes. Hybrid fan-out avoids this.          │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Feed Cache       │ Redis sorted set per user: feed:{userId}             │
│                  │ Contains (score → postId) pairs. Pre-computed.      │
│                  │ Reading the feed = ZRANGE O(log N). Sub-ms.          │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Social Graph     │ The network of follow relationships. In a directed   │
│                  │ graph: Alice → Bob means "Alice follows Bob."        │
│                  │ Stored in Cassandra (two tables for two directions). │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Asymmetric Follow│ Twitter/Instagram-style: you can follow someone      │
│                  │ without them following back. vs. Facebook-style      │
│                  │ mutual friends (symmetric — both must accept).       │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Two-Level Ranking│ Step 1: Pull 200 candidate postIds from Redis (cheap)│
│                  │ Step 2: Re-rank those 200 using heavier signals       │
│                  │ (ML affinity, interaction history). Return top 20.   │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Cursor-based     │ Pagination using a pointer (the last postId seen)    │
│ Pagination       │ rather than page numbers. Prevents "page drift"      │
│                  │ when new posts arrive. Efficient on Cassandra.       │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Snowflake ID     │ Time-sortable unique ID (41-bit timestamp + machine  │
│                  │ ID + sequence). postId IS the timestamp — no         │
│                  │ separate created_at column needed for sorting.       │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Presigned URL    │ Temporary S3 upload URL. Client uploads media DIRECT-│
│                  │ LY to S3, bypassing app servers. (Same as Drive.)    │
├──────────────────┼──────────────────────────────────────────────────────┤
│ CDN              │ Content Delivery Network. Caches images/videos at    │
│                  │ edge PoPs near users. 90%+ of media reads served     │
│                  │ from CDN. Massive traffic reducer.                   │
├──────────────────┼──────────────────────────────────────────────────────┤
│ ZADD / ZRANGE    │ Redis sorted set operations. ZADD adds a postId with │
│                  │ a score. ZRANGE retrieves top N by score. O(log N).  │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Like Count       │ Stored as Redis INCR (atomic integer, sub-ms) not    │
│                  │ in the posts table directly. Periodically synced     │
│                  │ back to Cassandra (write-back cache pattern).        │
└──────────────────┴──────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 3 — WHY EACH COMPONENT ═══════════════

## Component Choices — Why We Picked Each One

```
┌─────────────────────┬──────────────────────────────────────────────────┐
│  COMPONENT          │  WHY THIS? NOT SOMETHING ELSE?                   │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Redis Sorted Sets  │ WHY: Feed reads are 100:1 vs writes. We need    │
│  (Feed Cache)       │ feed reads in < 200ms. A sorted set per user     │
│                     │ with pre-computed scores: ZRANGE = O(log N).    │
│                     │ 500M users × 500 postIds × 8 bytes = 2 TB.      │
│                     │ Redis cluster handles this easily.               │
│                     │                                                  │
│                     │ WHY NOT MySQL/Cassandra for live feed: Too slow  │
│                     │ for 115K feed reads/sec. DB query every time     │
│                     │ a user opens the app would collapse under load.  │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Hybrid Fan-out     │ WHY: Pure push (write to all followers on post)  │
│  (not pure push or  │ fails for celebrities: 200M ZADD operations per  │
│   pure pull)        │ post = minutes of delay. Pure pull (fetch all    │
│                     │ followees' posts on feed open) fails for heavy   │
│                     │ followers: 500 people followed × each query =    │
│                     │ 500 DB reads per feed open × 500M users.         │
│                     │ Hybrid: push for the 99% (< 10K followers),     │
│                     │ pull for the 1% celebrities at read time.        │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Cassandra          │ WHY: Social graph = 1 trillion follow            │
│  (Social Graph +    │ relationships. Posts table = 100M inserts/day.   │
│   Posts)            │ High write throughput. No JOINs needed.          │
│                     │ Partition key on followee_id → "all followers    │
│                     │ of X" = single partition scan. Perfect fit.      │
│                     │                                                  │
│                     │ WHY NOT MySQL: Write throughput for posts +      │
│                     │ follow graph at this scale. JOINs not needed.   │
│                     │ MySQL IS correct for users table (auth, profile, │
│                     │ account — needs ACID, smaller volume).           │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Kafka              │ WHY: Post creation must be fast (< 200ms for     │
│  (Async Fan-out)    │ the user). Fan-out, notifications, media         │
│                     │ processing — all async. Kafka decouples post     │
│                     │ creation from all downstream work.               │
│                     │ If fan-out worker is slow → post creation is     │
│                     │ unaffected. Kafka buffers the load.              │
│                     │                                                  │
│                     │ WHY NOT synchronous fan-out: User waits for      │
│                     │ all 10K follower cache updates before getting    │
│                     │ the "post created" response. Unacceptable.      │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  S3 + CDN           │ WHY: 165 TB/day of new media. App servers can't  │
│  (Media)            │ serve this. S3 stores the originals and all      │
│                     │ processed variants (thumbnail, medium, WebP).   │
│                     │ CDN caches at ~250 global edge PoPs.             │
│                     │ 90%+ of media reads never hit S3 origin.         │
│                     │                                                  │
│                     │ WHY NOT serve media from app servers: At 500M   │
│                     │ DAU, media bandwidth would be 1+ TB/sec. No      │
│                     │ fleet of app servers is viable for this.         │
│                     │                                                  │
├─────────────────────┼──────────────────────────────────────────────────┤
│                     │                                                  │
│  Redis INCR         │ WHY: Like counts. Every like = INCR likes:{postId}│
│  (Like Counts)      │ Atomic, sub-ms. 100M likes/day = high write rate.│
│                     │ Cassandra COUNTER columns have known issues with  │
│                     │ consistency under high contention. Redis INCR    │
│                     │ is atomic — no race conditions. Write-back to    │
│                     │ Cassandra every 5 minutes (batch, not per-like). │
│                     │                                                  │
│                     │ WHY NOT UPDATE like_count in posts table: Massive│
│                     │ write contention on a single row. Cassandra      │
│                     │ counters work but have limited guarantees.       │
│                     │                                                  │
└─────────────────────┴──────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 4+ — FULL INTERVIEW SCRIPT ═══════════════

---

## OPENING — When Interviewer Says "Design Instagram"

*"Great. Instagram is a social feed platform — its core challenge is different
from most systems I'd design. The hard part isn't storage or media — it's feed
generation. Specifically: how do you pre-compute feeds for 500M users when a
single celebrity can have 200M followers? Let me ask a few questions first."*

---

## STEP 1 — Requirements Gathering

```
YOU ASK:                                     INTERVIEWER SAYS:
────────────────────────────────────────────────────────────────────
"Create posts with images/videos?"          → "Yes — like Instagram"
"Follow/unfollow — mutual or one-way?"      → "One-way (asymmetric)"
"Feed chronological or ranked?"             → "Ranked"
"Likes and comments?"                       → "Yes"
"Push notifications?"                       → "Yes"
"Stories or Reels?"                         → "Out of scope — feed only"
"How many users?"                           → "500M DAU, 2B total"
"Posts per day?"                            → "100M posts/day"
────────────────────────────────────────────────────────────────────
```

```
┌──────────────────────────────────────────────────────────────────┐
│                  REQUIREMENTS SUMMARY                             │
├──────────────────────────────────────────────────────────────────┤
│  FUNCTIONAL:                                                      │
│  Create posts (images + videos)                                  │
│  Follow / unfollow users (asymmetric)                            │
│  Home feed (ranked, not chronological)                           │
│  Likes + comments on posts                                       │
│  Push notifications (new follower, like, comment)                │
│  [Extension]: Stories, Search, Reels                             │
├──────────────────────────────────────────────────────────────────┤
│  NON-FUNCTIONAL:                                                  │
│  Scale:     500M DAU, 2B users, 100M posts/day                   │
│  Read:Write = 100:1 ratio → heavy optimization for reads         │
│  Feed load: < 200ms                                              │
│  Consistency: Eventual OK (< 5 sec for feed updates)             │
│  Availability: High                                              │
└──────────────────────────────────────────────────────────────────┘
```

*"The key insight: reads are 100× writes. Every design decision should optimize
for reads. And the design-defining constraint is the celebrity problem —
Cristiano Ronaldo has 200M followers. I'll address that in the deep dive."*

---

## STEP 2 — Capacity Estimation

```
POSTS:
──────────────────────────────────────────────────────────────────
"100M posts/day ÷ 86,400 = ~1,160 posts/sec. Small — write path is easy."

FEED READS:
──────────────────────────────────────────────────────────────────
"100:1 ratio → 100M DAU × 100 feed reads/day = 10B reads/day
 = 115,000 feed reads/sec (peak 3× = 345,000/sec).
 This is the system's primary bottleneck. Must be cached."

SOCIAL GRAPH:
──────────────────────────────────────────────────────────────────
"Avg user follows 500 people.
 2B users × 500 = 1 trillion follow relationships.
 1T × 16 bytes = 16 TB for the follow graph."

MEDIA:
──────────────────────────────────────────────────────────────────
"100M posts × 70% images × 200KB = 14 TB/day
 100M posts × 30% videos × 5MB  = 150 TB/day
 Total: ~165 TB/day of new media. Must use S3 + CDN."

CELEBRITY FAN-OUT (the critical number):
──────────────────────────────────────────────────────────────────
"Cristiano Ronaldo: 200M followers. One post.
 Naive fan-out: 200M × ZADD = 200M Redis writes in minutes.
 This is why we can't use pure push fan-out for celebrities."
```

---

## STEP 3 — Core Entities

```
┌──────────────────────────────────────────────────────────────────┐
│                       CORE ENTITIES                               │
├──────────────────┬───────────────────────────────────────────────┤
│ User             │ userId, name, bio, profilePicUrl, followerCount│
│ Post             │ postId (Snowflake), userId, caption,           │
│                  │ mediaUrls[], likeCount, commentCount, createdAt│
│ Follow           │ followerId, followeeId, createdAt              │
│ Feed             │ Computed Redis sorted set (not a DB table)     │
│ Like             │ userId + postId (just a key in Redis + set)    │
│ Comment          │ commentId, postId, userId, text, createdAt     │
└──────────────────┴───────────────────────────────────────────────┘

KEY: "A Feed is NOT a database table. It's a pre-computed Redis sorted set:
 feed:{userId} → { (score=12.5, postId=abc), (score=9.2, postId=xyz)... }
 Reading the feed = ZRANGE — O(log N), sub-millisecond."

"postId is a Snowflake ID — it encodes the creation timestamp.
 No separate created_at column needed. Sort by postId = sort by time."
```

---

## STEP 4 — API Design

```
POST /api/v1/posts
  Request: { caption, mediaType, hashtags[] }
  Response: { postId, mediaUploadUrl } ← presigned S3 URL
  Client uploads media DIRECTLY to S3 (bypasses our servers)

GET /api/v1/feed?cursor={postId}&limit=20
  Returns: { posts: [...], nextCursor: postId }
  Cursor = last postId seen. Prevents page drift on new arrivals.

POST /api/v1/follow/{targetUserId}        → follow
DELETE /api/v1/follow/{targetUserId}      → unfollow

POST /api/v1/posts/{postId}/like          → like post
DELETE /api/v1/posts/{postId}/like        → unlike post

POST /api/v1/posts/{postId}/comments      → add comment
GET  /api/v1/posts/{postId}/comments?cursor=... → list comments

GET /api/v1/users/{userId}/posts?cursor=... → profile page posts

WHY CURSOR PAGINATION (not page=1, page=2):
  If new posts arrive between page 1 and page 2 loads, page numbers
  drift — user sees duplicate posts (post slid from page 1 to page 2).
  Cursor = "give me posts OLDER than this postId" — stable reference.
```

---

### JSON Request / Response Examples

```json
// POST /api/v1/posts — Step 1: Get upload URL
// Request:
{ "mediaType": "IMAGE", "caption": "Sunset at Marine Drive", "hashtags": ["mumbai","sunset"] }
// Response 201 Created:
{
  "postId": "7234891234567890",
  "mediaUploadUrl": "https://s3.amazonaws.com/instagram-media/raw/abc123?X-Amz-Signature=...",
  "uploadExpiresIn": 300
}

// GET /api/v1/feed?cursor=7234891234560000&limit=20
// Response 200 OK:
{
  "posts": [
    {
      "postId": "7234891234567890",
      "author": { "userId": "user_abc", "username": "alice_photos", "profilePic": "https://cdn.instagram.com/pics/abc.jpg" },
      "caption": "Sunset at Marine Drive",
      "mediaUrls": ["https://cdn.instagram.com/posts/xyz_600.jpg"],
      "likeCount": 1284,
      "commentCount": 47,
      "createdAt": "2025-01-21T18:30:00Z",
      "hasLiked": false
    }
  ],
  "nextCursor": "7234891234560000"
}

// POST /api/v1/posts/{postId}/like
// Response 200 OK:
{ "postId": "7234891234567890", "likeCount": 1285, "hasLiked": true }

// Response 409 Already Liked:
{ "error": "ALREADY_LIKED", "message": "You have already liked this post." }
```

---

## STEP 5 — High-Level Architecture (Draw on Whiteboard)

> **► DRAW THIS on the whiteboard ◄**
> Draw two flows side by side: Write (left) and Read (right).
> Write: Client → Post Service → Kafka → Fan-out Worker → Redis.
> Read: Client → Feed Service → Redis (merge) → return top 20.
> Show the celebrity branch explicitly in the fan-out worker box.

```
                ╔══════════════════════════════════════════════╗
                ║    INSTAGRAM / NEWS FEED ARCHITECTURE         ║
                ╚══════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────┐
│                    CLIENTS (Mobile / Web)                          │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTPS
                             ▼
               ┌─────────────────────────────┐
               │  CDN (CloudFront)            │
               │  Serves: images, videos,     │
               │  thumbnails, profile pics    │
               │  90%+ of media reads here    │
               └──────────────┬──────────────┘
                              │ cache miss → origin
                              ▼
               ┌─────────────────────────────┐
               │  API GATEWAY                 │
               │  Auth, Rate limit, Route     │
               └──────┬────────────────┬──────┘
                      │                │
           ┌──────────▼──┐      ┌──────▼─────────┐
           │ POST SERVICE│      │  FEED SERVICE   │
           │             │      │                 │
           │ • Save post │      │ • ZRANGE Redis  │
           │   Cassandra │      │   feed:{userId} │
           │ • Presign   │      │ • Identify      │
           │   S3 URL    │      │   celeb follows │
           │ • Kafka:    │      │ • Pull celeb    │
           │   post-creat│      │   posts (Redis) │
           │   -ed event │      │ • Merge + Rank  │
           └──────┬──────┘      │ • Return top 20 │
                  │             └─────────────────┘
                  │ Kafka
     ┌────────────┼────────────────────┐
     ▼            ▼                    ▼
┌──────────┐ ┌────────────┐ ┌───────────────────┐
│ Fan-out  │ │Notification│ │  Media Pipeline   │
│ Worker   │ │ Worker     │ │  Worker           │
│          │ │            │ │                   │
│ FollowCt │ │ FCM/APNs   │ │ Resize → WebP     │
│  < 10K?  │ │ push notif │ │ Thumbnail gen     │
│   → PUSH │ │ to follower│ │ Video transcode   │
│  >=10K?  │ │ devices    │ │ Upload variants   │
│   → SKIP │ └────────────┘ │ to S3/CDN         │
│ (celeb)  │                └───────────────────┘
└────┬─────┘
     │ ZADD
     ▼
┌─────────────────────────────────────────────────┐
│  Redis                                           │
│                                                 │
│  feed:{userId}         → sorted set (postIds)   │
│  likes:{postId}        → INCR counter           │
│  liked_by:{postId}     → SET of userIds         │
│  celeb_posts:{userId}  → recent posts (hot)     │
│  celeb_followees:{uid} → which of my followees  │
│                          are celebrities        │
└─────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  Cassandra                                              │
│                                                        │
│  posts table          (partition: post_id)             │
│  followers_by_user    (partition: followee_id)         │
│  followees_by_user    (partition: follower_id)         │
│  comments table       (partition: post_id)             │
│  users table          (partition: user_id)             │
└────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  MySQL                                           │
│  users (auth, profile, account settings)        │
│  Needs ACID — payment info, account security    │
└─────────────────────────────────────────────────┘
```

---

> **► DRAW THIS on the whiteboard ◄**

## SEQUENCE DIAGRAM — POST CREATION + HYBRID FAN-OUT

```
  User App    Post Service     S3 + CDN     Kafka        Fan-out Worker    Redis
     │               │             │           │                │              │
     │ POST /posts   │             │           │                │              │
     │ {caption,tags}│             │           │                │              │
     │──────────────▶│             │           │                │              │
     │               │ Get presigned URL       │                │              │
     │               │────────────▶│           │                │              │
     │◀──────────────│ {uploadUrl} │           │                │              │
     │               │             │           │                │              │
     │ PUT uploadUrl │             │           │                │              │
     │ [raw image]   │             │           │                │              │
     │──────────────────────────▶│            │                │              │
     │◀──────────────────────────│            │                │              │
     │  [200 OK]     │            │           │                │              │
     │               │            │           │                │              │
     │ POST /posts   │            │           │                │              │
     │ {caption,     │            │           │                │              │
     │  mediaKey}    │            │           │                │              │
     │──────────────▶│            │           │                │              │
     │               │ INSERT post to Cassandra                │              │
     │               │ publish post-created    │                │              │
     │               │────────────────────────▶               │              │
     │ {postId}      │            │           │                │              │
     │◀──────────────│            │           │                │              │
     │               │            │           │                │              │
     │               │            │           │ Fan-out Worker consumes       │
     │               │            │           │◀───────────────               │
     │               │            │           │                │              │
     │               │            │           │ followerCount < 10K?          │
     │               │            │           │ YES: ZADD feed:{followerId}   │
     │               │            │           │      postId for each follower │
     │               │            │           │──────────────────────────────▶│
     │               │            │           │                │              │
     │               │            │           │ NO (celebrity): SET           │
     │               │            │           │  celeb_posts:{userId}         │
     │               │            │           │──────────────────────────────▶│
```

## SEQUENCE DIAGRAM — FEED READ (HYBRID MERGE)

```
  User App    Feed Service       Redis              Cassandra
     │               │              │                   │
     │ GET /feed     │              │                   │
     │──────────────▶│              │                   │
     │               │ ZRANGE feed:{userId} 0 199       │
     │               │──────────────▶                   │
     │               │◀──────────────                   │
     │               │  [200 normal postIds]             │
     │               │              │                   │
     │               │ GET celeb_followees:{userId}      │
     │               │──────────────▶                   │
     │               │◀──────────────                   │
     │               │  [celebIds: [cr7, gates, ...]]    │
     │               │              │                   │
     │               │ For each celeb:                   │
     │               │ GET celeb_posts:{celebId}         │
     │               │──────────────▶                   │
     │               │◀──────────────                   │
     │               │  [recent postIds]                 │
     │               │              │                   │
     │               │ Merge + Rank (top 200 → top 20)  │
     │               │              │                   │
     │               │ Fetch post details for top 20    │
     │               │──────────────────────────────────▶
     │               │◀──────────────────────────────────
     │               │  [post details]                   │
     │ {posts[20]}   │              │                   │
     │◀──────────────│              │                   │
```

---

## STEP 6 — Fan-out Deep Dive (The Celebrity Problem)

> **► SAY THIS carefully — this is the most asked deep dive ◄**

```
THREE APPROACHES — know all three, explain why hybrid wins:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPROACH 1: FAN-OUT ON READ (Pull — naive)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When user opens feed:
  Fetch all 500 followee IDs → 500 DB queries for their latest posts
  → merge 500 × 20 = 10,000 posts → rank → return top 20.

  VERDICT: Simple writes. Catastrophically slow reads.
  500M DAU × 500 queries = 250B DB reads/sec. Impossible.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPROACH 2: FAN-OUT ON WRITE (Push — standard)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When user creates post:
  Fan-out worker pushes postId to ALL followers' Redis caches.
  Reading feed = ZADD was already done → ZRANGE in <1ms.

  VERDICT: Ultra-fast reads. FATAL celebrity problem.
  Cristiano Ronaldo posts → 200M ZADD operations.
  200M × 1ms each / 1000 parallel workers = minutes of lag.
  His followers see the post 5 minutes after he posted. Unacceptable.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPROACH 3: HYBRID — What Instagram Actually Uses ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

POST CREATION:
  poster.followerCount < 10K  →  PUSH to all followers' Redis caches
  poster.followerCount >= 10K →  SKIP fan-out. Save to DB only.
                                  Cache their recent posts in Redis:
                                  SET celeb_posts:{userId} [postId1, ...]

FEED READ (hybrid merge):
  1. ZRANGE feed:{userId} → postIds from normal users' posts (pre-pushed)
  2. GET celeb_followees:{userId} → list of celebrity IDs they follow
  3. For each celebrity (usually 5-10 at most):
       GET celeb_posts:{celebId} → their recent postIds
       (this is a hot Redis cache — always fast)
  4. Merge all postIds (step 1 + step 3)
  5. Rank → return top 20

WHY THIS WORKS:
┌──────────────────────────────────────────────────────────────┐
│  Regular users (99%): push fan-out is fast and cheap         │
│  (< 10K followers = few thousand ZADD ops)                   │
│                                                              │
│  Celebrities (1%): no fan-out write storm                    │
│  Celebrity posts cached in Redis as a small set              │
│  Users typically follow ≤ 10 celebrities → 10 Redis GETs     │
│  at read time = still under 200ms easily                     │
│                                                              │
│  Inactive users: no wasted writes                            │
│  Feed TTL in Redis: evict feeds inactive > 7 days            │
│  Next time they open the app → cold rebuild (acceptable)     │
└──────────────────────────────────────────────────────────────┘
```

---

## STEP 7 — Feed Ranking

```
TWO-LEVEL RANKING:

Level 1: Candidate Generation (cheap, in Redis)
  ZRANGE feed:{userId} 0 199 WITHSCORES → top 200 candidates
  Score pre-computed on push: relevance estimate at write time

Level 2: Re-ranking (heavier signals, fast on 200 items)
  For each of 200 posts:
    recency:   hours_since_posted
    engagement: likes + comments×3 + shares×5 per unit time
    affinity:  how often does THIS user interact with THIS poster?
               (cached ML score: affinity:{viewerId}:{posterId})
    novelty:   is this post already shown to user? filter seen

  Final score = weighted combination of above signals
  Return top 20.

SIMPLE SCORE FORMULA (say this in interview):
  score = (likes×1 + comments×3 + shares×5)
          ─────────────────────────────────────
                  (hours_since_posted + 2)^1.5

  Gravity denominator ensures old posts sink over time.
  Same formula used by Hacker News. Simple. Explainable.

WHY TWO LEVELS?
  Can't run ML on all 500 candidate postIds in real-time.
  200 candidates × cheap ranking = fast.
  ML re-ranks 200 → 20. Small input = sub-100ms.
  Same pattern: YouTube, TikTok, Twitter.
```

---

## STEP 8 — Media Pipeline

```
Post creation with media:

1. Client: POST /posts → response: { postId, uploadUrl }
   (uploadUrl is a presigned S3 URL, TTL: 5 minutes)

2. Client: PUT uploadUrl → uploads raw image/video to S3
   (bypasses our app servers — they never see media bytes)

3. S3 triggers SNS event → SQS queue

4. Media Worker consumes:
   ┌──────────────────────────────────────────────────────┐
   │  For images:                                         │
   │    Resize to: thumbnail (150×150), medium (600px),  │
   │              full (original)                         │
   │    Convert to WebP (50% smaller, same quality)      │
   │    Upload all 3 variants to S3 with CDN path        │
   │                                                      │
   │  For videos:                                         │
   │    Transcode to: 1080p, 720p, 480p, 360p            │
   │    Generate HLS manifest (.m3u8) for ABR streaming  │
   │    Generate thumbnail from first keyframe           │
   │    Upload all to S3                                 │
   └──────────────────────────────────────────────────────┘

5. Worker updates post record: { mediaUrls: [cdn_url_1, cdn_url_2...] }
   Publishes "post-ready" to Kafka

6. Kafka fan-out worker starts AFTER "post-ready" event
   (not after "post-created") — ensures media is ready before
   the post appears in anyone's feed.

7. CDN: CloudFront pulls from S3 on first access, caches at edge.
   Subsequent reads served from edge PoP (~5ms vs ~100ms from S3).
```

---

## STEP 9 — Database Schema

> **► DRAW THIS on the whiteboard ◄**

```
posts table (Cassandra)
┌──────────────────┬──────────────────────────────────────────┐
│ post_id          │ Snowflake (PK) — encodes timestamp       │
│ user_id          │ UUID                                     │
│ caption          │ TEXT                                     │
│ media_urls       │ LIST<TEXT> (CDN URLs)                    │
│ media_type       │ TEXT  IMAGE | VIDEO                      │
│ hashtags         │ SET<TEXT>                                │
│ created_at       │ TIMESTAMP (redundant — in Snowflake ID) │
└──────────────────┴──────────────────────────────────────────┘

followers_by_user (Cassandra — for fan-out: who follows X?)
┌──────────────────┬──────────────────────────────────────────┐
│ followee_id      │ UUID (PARTITION KEY)                     │
│ follower_id      │ UUID (CLUSTERING KEY)                    │
│ created_at       │ TIMESTAMP                                │
└──────────────────┴──────────────────────────────────────────┘
Query: SELECT follower_id FROM followers_by_user WHERE followee_id=?
→ single partition read, returns all followers.

followees_by_user (Cassandra — for feed read: who does X follow?)
┌──────────────────┬──────────────────────────────────────────┐
│ follower_id      │ UUID (PARTITION KEY)                     │
│ followee_id      │ UUID (CLUSTERING KEY)                    │
│ is_celebrity     │ BOOLEAN (cached on follow action)        │
└──────────────────┴──────────────────────────────────────────┘
Query: SELECT followee_id, is_celebrity FROM followees_by_user
       WHERE follower_id=?
→ identifies regular vs celebrity followees in one query.

comments table (Cassandra)
┌──────────────────┬──────────────────────────────────────────┐
│ post_id          │ UUID (PARTITION KEY)                     │
│ comment_id       │ TIMEUUID (CLUSTERING KEY — time-ordered) │
│ user_id          │ UUID                                     │
│ text             │ TEXT                                     │
└──────────────────┴──────────────────────────────────────────┘

Redis keys:
  feed:{userId}           → ZSET  (score → postId), max 500 entries
  likes:{postId}          → INT   (INCR/DECR counter)
  liked_by:{postId}       → SET   (userIds who liked, for like check)
  celeb_posts:{userId}    → LIST  (recent 100 postIds, for celebrities)
  celeb_followees:{userId}→ SET   (celebrity IDs this user follows)
  affinity:{uid}:{pid}    → FLOAT (ML affinity score, TTL=1h)
```

---

> **► DRAW THIS on the whiteboard ◄**

## ER RELATIONSHIP DIAGRAM

```
┌────────────────────────────────────────────────────────────────────────┐
│              INSTAGRAM NEWS FEED — ENTITY RELATIONSHIP                  │
└────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌───────────────────────────┐
│     users        │     │          posts             │
│     (MySQL)      │     │        (Cassandra)         │
├─────────────────┤     ├───────────────────────────┤
│ PK user_id UUID │─────│ PK post_id Snowflake      │
│    username TEXT│ 1 N │ FK user_id UUID           │
│    bio TEXT     │     │    caption TEXT           │
│    profile_pic  │     │    media_urls LIST<TEXT>  │
│    follower_cnt │     │    media_type ENUM        │
│    followee_cnt │     │    hashtags SET<TEXT>     │
│    is_celebrity │     │    created_at TIMESTAMP   │
└─────────────────┘     └───────────────────────────┘
         │                          │ 1
         │ N                        │ N
         │                          │
┌────────▼─────────────┐  ┌────────▼──────────────────┐
│  followers_by_user    │  │       comments             │
│     (Cassandra)       │  │      (Cassandra)           │
├──────────────────────┤  ├───────────────────────────┤
│ PK followee_id (PART)│  │ PK post_id UUID (PART)    │
│    follower_id (CLUS)│  │    comment_id TIMEUUID    │
│    followed_at TS    │  │ FK user_id UUID           │
└──────────────────────┘  │    text TEXT              │
                          │    is_deleted BOOL        │
┌──────────────────────┐  └───────────────────────────┘
│  followees_by_user   │
│     (Cassandra)      │  Redis Keys:
├──────────────────────┤  ┌──────────────────────────────────────────┐
│ PK follower_id (PART)│  │ feed:{userId}       ZSET  score→postId  │
│    followee_id (CLUS)│  │ likes:{postId}       INT   INCR counter │
│    is_celebrity BOOL │  │ liked_by:{postId}   SET   userId set    │
│    followed_at TS    │  │ celeb_posts:{userId} LIST  recent postIds│
└──────────────────────┘  └──────────────────────────────────────────┘
```

---

## STEP 10 — Scalability

```
BOTTLENECK 1: FEED READ THROUGHPUT (345K reads/sec at peak)
─────────────────────────────────────────────────────────────────
Redis: 345K ZRANGE operations/sec.
Redis cluster: shard feed:{userId} by userId hash.
50 Redis shards × ~7K reads/sec each = comfortable.
Read replicas per shard for additional read capacity.

BOTTLENECK 2: INACTIVE USERS (wasted Redis space)
─────────────────────────────────────────────────────────────────
500M users × 500 postIds × 8 bytes = 2 TB if everyone active.
Reality: not all 500M active daily.
TTL: evict feed:{userId} after 7 days of inactivity.
On cold open: rebuild feed from Cassandra (acceptable 300-500ms once).
Result: actual Redis footprint << 2 TB.

BOTTLENECK 3: UNFOLLOW STALE DATA
─────────────────────────────────────────────────────────────────
User unfollows @john.
John's old postIds are still in the feed:{userId} sorted set.
Two approaches:
  Option A: Lazy filter — at read time, check "still following?" for
  each postId's author before including in feed. O(20 checks for top 20).
  Option B: Active cleanup — on unfollow, scan feed:{userId} and ZREM
  all postIds from that author. Expensive for users with large feeds.
  Instagram uses Option A (lazy filter). Simpler and fast enough.

BOTTLENECK 4: LIKE COUNT HOTSPOTS
─────────────────────────────────────────────────────────────────
Viral post gets 10M likes in 1 hour = 2,778 likes/sec.
Redis INCR likes:{postId}: atomic, O(1), sub-ms. Handles easily.
Write-back to Cassandra: batch every 5 minutes.
liked_by:{postId} SET: check if user already liked (before INCR).
If post_id matches: SISMEMBER liked_by:{postId} {userId} → bool.
```

---

## WHAT NOT TO SAY ✗

```
✗ "Fan-out on write to all followers on every post"
  → Celebrity problem: 200M ZADD ops per post. Minutes of lag.
    You MUST mention hybrid fan-out (push for regular, pull for celeb).

✗ "Query all followees' posts at read time for every feed load"
  → 500M DAU × 500 queries each = 250B DB reads/sec. Impossible.
    Pre-computed Redis feed cache is the answer.

✗ "Use MySQL for the posts table"
  → 100M inserts/day. The social graph has 1 trillion rows.
    MySQL can't handle this write throughput or table size.
    Cassandra is designed for exactly this: high-volume, no-join writes.

✗ "Serve media files from the app server"
  → 165 TB/day of new media + 100:1 read ratio = petabytes of bandwidth.
    CDN (CloudFront/Akamai) + S3 is the only viable answer.
    Clients upload directly to S3 (presigned URL). App servers never
    see media bytes.

✗ "Use page numbers for feed pagination"
  → New posts arrive constantly. Page 2 shifts as page 1 is loaded.
    Users see duplicate posts across pages.
    Cursor pagination (using last-seen postId) is stable.

✗ "One follow table is enough"
  → Two query patterns require two tables:
    Fan-out: "who follows X?" → followers_by_user (partition=followee)
    Feed read: "who does X follow?" → followees_by_user (partition=follower)
    You CANNOT efficiently query both from one Cassandra table.
```

---

## SENIOR TRAP QUESTIONS (15 YOE Level)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 1 — THE CELEBRITY PROBLEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "You set the celebrity threshold at 10K followers. Cristiano Ronaldo
   gains a follower DURING a fan-out operation. Now you need to
   reclassify him. How do you handle the transition?"

A: The threshold is not applied in real-time at exact follower counts.
   We maintain a celebrity_users SET in Redis (or a flag in the users table).
   A background job runs daily (or on significant follower milestones):
     IF user.followerCount crosses 10K threshold → mark as celebrity.
     Remove their future posts from fan-out worker's push path.
     Keep historical push-fanned posts in followers' feeds (don't delete them).
   During the transition window (before the job runs): the user may still
   get push fan-out for a few more posts. That's acceptable — brief overlap
   is harmless. We don't need atomic instant reclassification.
   The key insight: this is an eventual consistency problem, not a
   correctness problem. A few extra fan-out writes during transition
   are far better than building complex atomic reclassification logic.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "User A has 9,999 followers (regular user). They buy followers
   and instantly jump to 15 million. Their previous posts were fan-
   out pushed to 9,999 feed caches. How do you handle this?"

A: Don't retroactively clean up past fan-out. Too expensive.
   Mark the user as a celebrity going forward (background job).
   Their new posts go into the pull path (no more fan-out).
   Their 9,999 old feed writes: those posts age out naturally
   from the sorted sets over time (ZADD with low score → evicted
   when feed reaches 500-entry cap). No active cleanup needed.
   The "stale writes" are harmless — they're just postIds that
   will naturally expire from follower feeds over days/weeks.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 2 — RACE CONDITIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "Alice likes a post. The request fails mid-flight. She taps like
   again. The post now shows 2 likes from Alice. How do you prevent
   this double-like?"

A: Idempotency via a Redis SET.
   Two data structures per post:
   1. likes:{postId}     → INT counter (INCR on like, DECR on unlike)
   2. liked_by:{postId}  → SET of userIds who liked
   On like action:
     SISMEMBER liked_by:{postId} {aliceId} → if TRUE, return 409 (already liked)
     If FALSE: SADD liked_by:{postId} {aliceId} AND INCR likes:{postId}
   This check-and-add must be atomic → use a Lua script:
     EVAL: if SISMEMBER then return 0 else SADD + INCR, return 1
   The Lua script runs atomically on Redis → no race condition.
   Like count is never inflated by retries or double-taps.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 3 — CONSISTENCY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "User deletes a post. But their post was already fan-out pushed
   to 100,000 followers' Redis feed caches. How do you remove it?"

A: Three options, with trade-offs:
   Option 1 (lazy delete — Instagram's approach):
     Mark post as DELETED in Cassandra/Redis.
     When feed is rendered: filter out deleted postIds before returning.
     Simple. No mass Redis cleanup. Deleted posts never shown.
   Option 2 (active cleanup — expensive):
     Scan all 100K followers' feed caches and ZREM the postId.
     At 100K ZREM operations per delete: expensive but fast if rare.
   Option 3 (tombstone TTL):
     Store deleted:{postId} in Redis with TTL matching feed eviction.
     Feed rendering: SISMEMBER deleted → exclude if true.
   Instagram uses Option 1 (lazy delete). Explanation: 99% of posts
   are never deleted. Adding check overhead for the 1% case at read time
   costs ~1ms extra per 20-item feed. Trivial. Clean delete logic.
```

---

## KEY NUMBERS — Memorize These

```
┌──────────────────────────────────┬──────────────────────────┐
│              METRIC              │  VALUE                   │
├──────────────────────────────────┼──────────────────────────┤
│ Registered users                 │ 2 billion                │
│ Daily Active Users               │ 500 million              │
│ Posts per day                    │ 100 million              │
│ Posts per second                 │ ~1,160                   │
│ Feed reads per second            │ ~115,000 (peak 345K)     │
│ Read:Write ratio                 │ 100:1                    │
│ Follow relationships total       │ 1 trillion               │
│ Follow graph storage             │ ~16 TB                   │
│ Media ingested per day           │ ~165 TB                  │
│ Celebrity threshold              │ 10,000 followers         │
│ Redis feed cap per user          │ 500 postIds              │
│ Feed inactive TTL (Redis)        │ 7 days                   │
│ Redis feed cluster size          │ ~2 TB (active users)     │
│ Feed load latency target         │ < 200ms                  │
│ Two-level ranking: candidate set │ 200 posts → top 20       │
└──────────────────────────────────┴──────────────────────────┘
```

---

*Study order: STEP 6 Fan-out deep dive (20 min) → STEP 5 Architecture (15 min)
→ STEP 7 Ranking (10 min) → STEP 8 Media Pipeline (5 min) → Rapid Answer (5 min)*
