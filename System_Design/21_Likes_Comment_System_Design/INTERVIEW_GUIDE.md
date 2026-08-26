# Likes and Comments System — Interview Script
## Design Instagram/YouTube Likes & Comments at Scale
### Speak This Word-for-Word to Your Interviewer

> How to use this: Read PAGE 1 to internalize the big picture before the interview.
> PAGE 2 gives you exact vocabulary — use these terms naturally.
> PAGE 4+ is the word-for-word script — follow it step by step.

# ═══════════════ PAGE 1 — START HERE ═══════════════

## BIG PICTURE (Understand This Before Anything Else)

> **► STUDY this diagram, don't draw it ◄**
> Likes and Comments look trivially simple — until a viral post receives 100,000 likes per second on a single counter. The like count is NOT stored in the posts table. Comments use Cassandra partitioned by postId so all comments for one post live in one partition scan. These two decisions — Redis counters + Cassandra comment partitions — are the entire design.

```
                        ┌─────────────────────────────────────────────────────┐
                        │                    CLIENTS                          │
                        │         iOS / Android / Web Browsers                │
                        └──────────────────────┬──────────────────────────────┘
                                               │ HTTPS
                                               ▼
                        ┌──────────────────────────────────────────────────────┐
                        │              API GATEWAY / Load Balancer             │
                        └────────┬──────────────────┬───────────────────────┬─┘
                                 │                  │                       │
                    ┌────────────▼──────┐  ┌────────▼────────┐  ┌──────────▼───────┐
                    │   Like Service    │  │ Comment Service  │  │ Notification Svc  │
                    │  (stateless pods) │  │ (stateless pods) │  │  (async consumer) │
                    └────────┬──────────┘  └────────┬─────────┘  └──────────┬───────┘
                             │                      │                        │
                    ┌────────▼──────────┐  ┌────────▼─────────┐   ┌─────────▼──────┐
                    │   Redis Cluster   │  │    Cassandra      │   │     Kafka       │
                    │ likes:{postId}    │  │  comments table   │   │  like-events    │
                    │ liked_by:{postId} │  │  (partition per   │   │  topic          │
                    │ comment_likes:{}  │  │   postId)         │   └────────┬───────┘
                    └────────┬──────────┘  └───────────────────┘            │
                             │                                    ┌──────────▼──────┐
                    ┌────────▼──────────┐                         │  Notification   │
                    │  Write-back Job   │                         │  Push (FCM/     │
                    │  (every 5 min)    │                         │  APNs)          │
                    └────────┬──────────┘                         └─────────────────┘
                             │
                    ┌────────▼──────────┐
                    │    Cassandra      │
                    │  like_counts      │
                    │  (durable store)  │
                    └───────────────────┘
```

---

## RAPID ANSWER — If You Only Have 5 Minutes

"Like counts are stored in Redis, not in the posts table. A Redis INCR on likes:{postId} is atomic and handles millions of ops per second. Every 5 minutes a write-back job persists counters to Cassandra for durability.

For the liked-by check — has a user already liked this post — we use a Redis SET: liked_by:{postId}. For viral posts with 10 million likers, that SET becomes too large to hold in one key. We shard it: liked_by:{postId}:{userId mod 100}. Or we use a Bloom filter which is probabilistic but never gives a false negative.

Comments are stored in Cassandra. Partition key is postId, clustering key is a TIMEUUID — so all comments for one post are in one partition, ordered by time. Pagination is cursor-based: give me 20 comments after this commentId.

Notifications on likes are always async — Kafka topic, consumed by a Notification Service that calls FCM or APNs. Never synchronous on the like endpoint.

Like count consistency: we show approximately '1.2M likes', not an exact number. A 5-second lag is acceptable. Eventual consistency is the deliberate tradeoff here."

---

# ═══════════════ PAGE 2 — GLOSSARY ═══════════════

```
┌──────────────────────────────┬──────────────────────────────────────────────────────────────────┐
│ Term                         │ What It Means                                                    │
├──────────────────────────────┼──────────────────────────────────────────────────────────────────┤
│ Redis INCR                   │ Atomic increment of an integer value; used for like counters     │
│ Redis DECR                   │ Atomic decrement; used for unlike operations                     │
│ SADD / SISMEMBER / SREM      │ Redis SET operations: add, check membership, remove              │
│ Bloom Filter                 │ Probabilistic data structure: no false negatives, rare false +   │
│ Write-back pattern           │ Redis holds live counts; batch job writes to Cassandra every 5m  │
│ Partition key (Cassandra)    │ Determines which node stores the row; postId here                │
│ Clustering key (Cassandra)   │ Determines sort order within partition; TIMEUUID for comments    │
│ TIMEUUID                     │ UUID with embedded timestamp; globally unique, time-ordered      │
│ Cursor-based pagination      │ Next page = start after last seen ID; no OFFSET scans            │
│ Soft delete                  │ Mark is_deleted=true; never remove row — replies still reference │
│ Threaded comments            │ Replies to replies; Instagram uses max 2 levels deep             │
│ parent_comment_id            │ NULL for top-level comment; set to parent UUID for replies       │
│ Toxicity classifier          │ ML model that detects harmful content; runs async via Kafka      │
│ is_hidden                    │ Soft-hide for toxic comments; author still sees their own        │
│ Idempotency key              │ Token that deduplicates repeated requests (double-tap unlike)    │
│ Kafka async notification     │ Like event → Kafka topic → Notification Service → FCM/APNs      │
│ Write contention             │ Multiple writes competing on one row/key; the hot-row problem    │
│ ZPOPMIN / ZADD               │ Redis sorted set ops; not needed here but related infra          │
│ SimHash                      │ Near-duplicate content detection hash                            │
│ Rate limiting (comments)     │ Redis INCR with TTL: max 3 comments/min/post per user           │
└──────────────────────────────┴──────────────────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 3 — WHY EACH COMPONENT ═══════════════

```
┌───────────────────────┬──────────────────────────────────────────┬────────────────────────────────────────────┐
│ Component             │ WHY use it                               │ WHY NOT the alternative                    │
├───────────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────┤
│ Redis for like count  │ INCR is atomic, sub-ms, millions of      │ SQL UPDATE on posts table = row lock        │
│                       │ ops/sec on a single key                  │ contention on viral posts. Kills throughput │
├───────────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────┤
│ Cassandra for         │ Write-heavy; wide rows; partition per     │ MySQL: 500M inserts/day on one table =     │
│ comments             │ postId = single partition scan for all    │ painful. No natural post-scoped partitions  │
│                       │ comments of a post                       │                                            │
├───────────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────┤
│ TIMEUUID clustering   │ Globally unique + time-ordered. Inserts  │ Auto-increment INT: requires coordination   │
│ key                   │ are append-only (no hotspot)             │ across distributed nodes                   │
├───────────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────┤
│ Bloom filter for      │ O(1) membership check; constant memory   │ Redis SET liked_by:{postId}: 10M likers =  │
│ liked-by at scale     │ regardless of set size                   │ ~100MB per viral post. Hundreds of posts   │
│                       │                                          │ = GB of RAM just for like tracking         │
├───────────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────┤
│ Kafka for             │ Decouples like action from notification  │ Synchronous call to Notification Service:  │
│ notifications         │ delivery. Like API returns 200ms,        │ adds 100-300ms to every like. Terrible UX  │
│                       │ notification may take seconds            │                                            │
├───────────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────┤
│ Cursor-based          │ Stable under concurrent inserts; no      │ OFFSET pagination: page 5 shifts when new  │
│ pagination            │ skipping/duplicating comments            │ comments inserted. Users see gaps/dupes    │
├───────────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────┤
│ Soft delete           │ Preserves reply chains, notification     │ Hard delete: orphaned replies, broken       │
│                       │ history, like counts on deleted comments │ notification deep-links, audit trail gone  │
├───────────────────────┼──────────────────────────────────────────┼────────────────────────────────────────────┤
│ Async ML toxicity     │ ML inference ~50-200ms; can be batched;  │ Sync inline check: adds 200ms to every     │
│ check (Kafka)         │ doesn't block the user's comment submit  │ comment submit. Unacceptable latency       │
└───────────────────────┴──────────────────────────────────────────┴────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 4 — FULL INTERVIEW SCRIPT ═══════════════

## OPENING

"Before I start drawing components, I want to clarify what we're designing, because likes and comments are two different systems that share infrastructure. I'll treat them together since they're typically co-designed.

I'll go through: requirements, capacity, data model, API, architecture, database schema, deep dives on the hard parts — which are like counter contention and comment threading — and then scalability bottlenecks. Does that sound good?"

---

## STEP 1 — Requirements Gathering

"Let me ask a few clarifying questions."

```
┌────────────────────────────────────┬───────────────────────────────────────────────────────┐
│ Question                           │ Answer / Assumption                                   │
├────────────────────────────────────┼───────────────────────────────────────────────────────┤
│ Which product is this closest to?  │ Instagram-style: 2-level comments + like counts       │
│ Do we need unlike?                 │ Yes                                                   │
│ Comment threading depth?           │ 2 levels: top-level + replies (no reply-to-reply)     │
│ Comment editing?                   │ Yes, within 15 minutes                                │
│ Comment deletion?                  │ Yes (soft delete)                                     │
│ Notification on like?              │ Yes, push notification to post owner                  │
│ Toxicity filtering?                │ Yes, async                                            │
│ Sort comments by?                  │ Recent first (default) + top comments by likes        │
│ Exact like count vs approximate?   │ Approximate is fine ("1.2M"), 5-second lag OK         │
│ Scale?                             │ Instagram scale: ~500M DAU                            │
└────────────────────────────────────┴───────────────────────────────────────────────────────┘
```

**Functional Requirements Box:**
```
LIKES:
  [x] User can like/unlike a post
  [x] Like count displayed on post (approximate, eventually consistent)
  [x] Has-user-liked check before rendering heart icon
  [x] Notification to post owner on like (async)

COMMENTS:
  [x] User can post, edit, delete a comment on a post
  [x] User can reply to a comment (2-level threading)
  [x] Paginate comments (cursor-based, 20/page)
  [x] Like/unlike a comment
  [x] Sort: most recent (default) + top comments
  [x] Async toxicity filtering

NON-FUNCTIONAL:
  [x] Like write throughput: 48,600/sec average, 100,000/sec peak on viral post
  [x] Comment write: 5,787/sec
  [x] Like display latency: eventual consistency, 5-sec lag OK
  [x] Comment read latency: < 100ms p99
  [x] High availability: 99.99% uptime
```

---

## STEP 2 — Capacity Estimation

"Let me run through the numbers so my technology choices make sense."

**Likes:**
- Instagram: 4.2 billion likes/day
- Average write rate: 4.2B / 86,400 = ~48,600 likes/sec
- Viral post peak: 100,000 likes/sec on a single postId
- Like read (display count): 100:1 read/write ratio = ~4.86M reads/sec → Redis cache handles trivially
- liked-by check: per page load, per post rendered in feed → very high read rate

**Comments:**
- 500M comments/day = ~5,787 comments/sec
- Assume avg 200 bytes/comment = 500M × 200B = 100GB/day new data
- Monthly: ~3TB new comment data
- Comment reads: 10:1 read:write = ~58,000 comment reads/sec

**Storage:**
- Redis: likes:{postId} counter = 8 bytes per post × 1B posts = 8GB (trivial)
- Redis liked_by SET: 8 bytes per userId × 1M likers = 8MB per viral post → need sharding or Bloom filter at scale
- Cassandra comments: 100GB/day × 365 = ~36TB/year; manageable with proper partitioning

---

## STEP 3 — Core Entities

```
Post         { post_id, user_id, content, created_at }
User         { user_id, username, profile_pic_url }
Like         { post_id, user_id, created_at }          ← existence record only
Comment      { post_id, comment_id, user_id,
               parent_comment_id, content,
               is_deleted, is_hidden, created_at }
CommentLike  { comment_id, user_id, created_at }
Notification { notification_id, recipient_user_id,
               actor_user_id, type, entity_id,
               created_at, is_read }
```

Key relationships:
- One Post → Many Likes (existence records in Cassandra or Redis)
- One Post → Many Comments
- One Comment → Many Comments (parent_comment_id for replies)
- One Comment → Many Likes

---

## STEP 4 — API Design

**Likes API:**
```
POST   /v1/posts/{postId}/like
       Response: { post_id, like_count, user_has_liked: true }

DELETE /v1/posts/{postId}/like
       Response: { post_id, like_count, user_has_liked: false }

GET    /v1/posts/{postId}/likes?cursor=&limit=20
       Response: { likers: [{ user_id, username, avatar }], next_cursor }
```

**Comments API:**
```
POST   /v1/posts/{postId}/comments
       Body: { content, parent_comment_id? }
       Response: { comment_id, content, user, created_at }

GET    /v1/posts/{postId}/comments?sort=recent|top&cursor=&limit=20
       Response: { comments: [...], next_cursor }

GET    /v1/posts/{postId}/comments/{commentId}/replies?cursor=&limit=10
       Response: { replies: [...], next_cursor }

PUT    /v1/posts/{postId}/comments/{commentId}
       Body: { content }
       Response: { comment_id, content, edited_at }

DELETE /v1/posts/{postId}/comments/{commentId}
       Response: { success: true }  ← soft delete only

POST   /v1/comments/{commentId}/like
DELETE /v1/comments/{commentId}/like
```

---

### JSON Request / Response Examples

```json
// POST /v1/posts/{postId}/like
// Response 200 OK:
{ "postId": "7234891234567890", "likeCount": 843, "hasLiked": true }

// Response 409 Already Liked:
{ "error": "ALREADY_LIKED", "likeCount": 843 }

// POST /v1/posts/{postId}/comments
// Request:
{ "content": "Absolutely stunning!", "parent_comment_id": null }
// Response 201 Created:
{
  "commentId": "7234891234560001",
  "postId": "7234891234567890",
  "author": { "userId": "user_bob", "username": "bob123" },
  "content": "Absolutely stunning!",
  "likeCount": 0,
  "createdAt": "2025-01-21T18:35:00Z"
}

// GET /v1/posts/{postId}/comments?sort=recent&cursor=&limit=20
// Response 200 OK:
{
  "comments": [
    {
      "commentId": "7234891234560001",
      "author": { "userId": "user_bob", "username": "bob123" },
      "content": "Absolutely stunning!",
      "likeCount": 12,
      "replyCount": 3,
      "createdAt": "2025-01-21T18:35:00Z"
    }
  ],
  "nextCursor": "7234891234559999"
}

// Response 429 Too Many Requests (rate limit):
{ "error": "RATE_LIMITED", "message": "Too many comments. Try again in 45 seconds.", "retryAfter": 45 }
```

---

## STEP 5 — High-Level Architecture

**► DRAW THIS ◄**

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                               CLIENTS                                        │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                        ┌────────────▼────────────┐
                        │    API Gateway           │
                        │  (rate limiting, auth,   │
                        │   JWT validation)        │
                        └──────┬────────┬──────────┘
                               │        │
               ┌───────────────▼─┐    ┌─▼───────────────┐
               │  Like Service   │    │ Comment Service  │
               │  (stateless,    │    │ (stateless,      │
               │   horizontally  │    │  horizontally    │
               │   scalable)     │    │  scalable)       │
               └────┬────────────┘    └────────┬─────────┘
                    │                          │
         ┌──────────▼──────────┐    ┌──────────▼──────────┐
         │   Redis Cluster     │    │     Cassandra        │
         │                     │    │                      │
         │ likes:{postId}      │    │  comments table      │
         │   → INT counter     │    │  (partition=postId)  │
         │                     │    │                      │
         │ liked_by:{postId}   │    │  comment_counts      │
         │ :{userId%100}       │    │  (partition=postId)  │
         │   → SET of userIds  │    └──────────────────────┘
         │                     │
         │ comment_likes:      │    ┌──────────────────────┐
         │ {commentId} → INT   │    │     Kafka Cluster    │
         └──────────┬──────────┘    │                      │
                    │               │  like-events topic   │
         ┌──────────▼──────────┐    │  comment-events      │
         │   Write-back Job    │    │  toxicity-check      │
         │  (every 5 minutes)  │    └────────────┬─────────┘
         │  Redis → Cassandra  │                 │
         └─────────────────────┘    ┌────────────▼─────────┐
                                    │  Notification Service │
                                    │  ML Toxicity Service  │
                                    │  (consumers)          │
                                    └──────────────────────┘
```

**Component Responsibilities:**
- API Gateway: Auth (JWT), rate limiting (100 req/sec/user), SSL termination
- Like Service: INCR/DECR Redis, SADD/SREM liked_by set, publish to Kafka
- Comment Service: Write to Cassandra, read with cursor pagination, enforce rate limit
- Write-back Job: Async, every 5 min, syncs Redis counters to Cassandra for durability
- Kafka: Decouples notifications and ML toxicity from hot path
- Notification Service: Consumes like/comment events → FCM/APNs push
- ML Toxicity Service: Classifies comment content; sets is_hidden=true if toxic

---

> **► DRAW THIS on the whiteboard ◄**

## SEQUENCE DIAGRAM — LIKE A POST

```
  User App    Like Service      Redis (Lua)     Cassandra      Kafka
     │               │               │               │             │
     │ POST /posts/  │               │               │             │
     │ {id}/like     │               │               │             │
     │──────────────▶│               │               │             │
     │               │ Lua script (atomic):           │             │
     │               │ SISMEMBER liked_by:{id} userId │             │
     │               │ if member: return ALREADY_LIKED│             │
     │               │ else: SADD + INCR likes:{id}  │             │
     │               │──────────────▶│               │             │
     │               │◀──────────────│               │             │
     │               │  [newCount=843]               │             │
     │ {likeCount:843│               │               │             │
     │  hasLiked:true│               │               │             │
     │◀──────────────│               │               │             │
     │               │               │               │             │
     │               │ publish like.created (async)  │             │
     │               │──────────────────────────────────────────▶  │
     │               │               │               │             │
     │               │ [every 5 min: batch write-back to Cassandra] │
     │               │               │ UPDATE like_counts          │
     │               │               │ WHERE post_id=?             │
     │               │──────────────────────────────▶              │
```

## SEQUENCE DIAGRAM — ADD COMMENT

```
  User App   Comment Service   Redis (rate limit)   Cassandra   Kafka
     │               │               │                  │           │
     │ POST /posts/  │               │                  │           │
     │ {id}/comments │               │                  │           │
     │ {text}        │               │                  │           │
     │──────────────▶│               │                  │           │
     │               │ INCR comment_rate:{uid}:{postId} │           │
     │               │ EX 60 (1-min window)             │           │
     │               │──────────────▶│                  │           │
     │               │◀──────────────│                  │           │
     │               │  count=1 (< 3 limit OK)          │           │
     │               │               │                  │           │
     │               │ INSERT comment (post_id, TIMEUUID, userId, text)  │
     │               │──────────────────────────────────▶            │
     │               │◀──────────────────────────────────            │
     │ {commentId,   │               │                  │           │
     │  createdAt}   │               │                  │           │
     │◀──────────────│               │                  │           │
     │               │ publish comment.created          │           │
     │               │──────────────────────────────────────────────▶
```

---

## STEP 6 — Database Schema

**► DRAW THIS ◄**

**Cassandra — comments table:**
```
CREATE TABLE comments (
    post_id         UUID,
    comment_id      TIMEUUID,
    user_id         BIGINT,
    parent_comment_id TIMEUUID,       -- NULL for top-level
    content         TEXT,
    is_deleted      BOOLEAN,
    is_hidden       BOOLEAN,          -- toxicity soft-hide
    like_count      COUNTER,          -- or use Redis
    created_at      TIMESTAMP,
    PRIMARY KEY (post_id, comment_id)
) WITH CLUSTERING ORDER BY (comment_id DESC);
```

**Cassandra — likes table (existence records):**
```
CREATE TABLE post_likes (
    post_id    UUID,
    user_id    BIGINT,
    created_at TIMESTAMP,
    PRIMARY KEY (post_id, user_id)
);
-- Used for "who liked this post" queries, NOT for counting
-- Count lives in Redis
```

**Redis Key Schema:**
```
likes:{postId}              → STRING  (integer counter, INCR/DECR)
liked_by:{postId}:{n}       → SET     (n = userId % 100, sharded)
comment_likes:{commentId}   → STRING  (integer counter)
comment_count:{postId}      → STRING  (integer counter)
comment_rate:{userId}:{postId} → STRING (rate limit, EX 60)
```

**Cassandra — like_counts (write-back target):**
```
CREATE TABLE like_counts (
    post_id     UUID PRIMARY KEY,
    like_count  BIGINT,
    updated_at  TIMESTAMP
);
```

---

> **► DRAW THIS on the whiteboard ◄**

## ER RELATIONSHIP DIAGRAM

```
┌────────────────────────────────────────────────────────────────────┐
│             LIKES & COMMENTS — ENTITY RELATIONSHIP                  │
└────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────────────┐
│    users     │     │        posts          │
│   (MySQL)    │     │      (Cassandra)      │
├──────────────┤     ├──────────────────────┤
│ PK user_id   │     │ PK post_id Snowflake │
│    username  │     │ FK user_id UUID      │
│    created_at│     │    caption TEXT      │
└──────┬───────┘     │    media_urls LIST   │
       │ N           └──────────┬───────────┘
       │                        │ 1
       │ ┌──────────────────────┤
       │ │                      │ N
┌──────▼─▼──────────────┐   ┌──▼───────────────────────────┐
│       comments         │   │       likes (Redis)           │
│      (Cassandra)       │   ├──────────────────────────────┤
├───────────────────────┤   │ likes:{postId}   INT counter │
│ PK post_id UUID (PART)│   │ liked_by:{postId} SET userIds│
│    comment_id TIMEUUID│   │                              │
│ FK user_id UUID       │   │ Write-back to Cassandra:      │
│    parent_comment_id  │   │ like_counts (post_id, count) │
│    content TEXT       │   │  every 5 minutes (batch)     │
│    is_deleted BOOL    │   └──────────────────────────────┘
│    is_hidden BOOL     │
└───────────────────────┘

  comment_likes (Redis):
  ┌──────────────────────────────────────────────────────────────┐
  │ comment_likes:{commentId}  INT  INCR counter                 │
  │ comment_rate:{userId}:{postId} INT EX 60                     │  ← rate limit
  └──────────────────────────────────────────────────────────────┘
```

---

## STEP 7 — Deep Dive: The Hard Parts

### Deep Dive A: 100K Likes/Sec on a Single Viral Post

"This is the core challenge of the like system. Let me walk through it."

**The counter is NOT the bottleneck:**
- Redis INCR on a single key: Redis processes ~1 million ops/sec single-threaded.
- 100K likes/sec on `likes:{postId}` → Redis handles this without breaking a sweat.
- The counter is fine. The problem is the liked_by check.

**The liked_by SET is the bottleneck:**
```
Problem: 100K SADD/sec to liked_by:{postId} = one very hot Redis key.
         At 10M likers: SET holds 10M members × 8 bytes = 80MB in one key.
         Redis is single-threaded per key: 100K SADD/sec → contention.

Solution 1 — Shard the SET:
  liked_by:{postId}:{userId % 100}
  → 100 sub-keys, each receives 1K SADD/sec (100K / 100)
  → Check if user liked: SISMEMBER liked_by:{postId}:{userId % 100}
  → List all likers: SUNION liked_by:{postId}:0 ... liked_by:{postId}:99
     (expensive — only do for "show who liked" feature, not count display)

Solution 2 — Bloom Filter:
  Trade: probabilistic (1% false positive rate), never false negative.
  "You haven't liked this" → always correct.
  "You have liked this" → 99% correct (1% phantom like, acceptable).
  Memory: 10M users, 1% error → ~12MB per post (vs 80MB for exact SET).
  Use case: showing the heart icon state. Bloom filter is ideal.
```

**Unlike race condition:**
```
Problem: User A and B both click unlike simultaneously.
         Two DECR calls: counter goes from 1 → -1.

Solution: Lua script (atomic in Redis):
  local count = redis.call('GET', KEYS[1])
  if tonumber(count) > 0 then
    redis.call('DECR', KEYS[1])
  end
  return redis.call('GET', KEYS[1])
```

### Deep Dive B: Comment Threading and Pagination

**Two-level threading implementation:**
```
Top-level query:
  SELECT * FROM comments
  WHERE post_id = ? AND parent_comment_id = NULL
  AND comment_id > {cursor}
  LIMIT 20

Replies to a comment:
  SELECT * FROM comments
  WHERE post_id = ? AND parent_comment_id = {commentId}
  AND comment_id > {cursor}
  LIMIT 10
```

**TIMEUUID as cursor:**
- TIMEUUID is time-ordered globally unique ID
- Cursor = last comment_id seen
- Next page: WHERE comment_id > cursor LIMIT 20
- Stable: new comments inserted don't shift pages

**Top comments sort:**
```
Problem: Cassandra can't sort by like_count (it's dynamic).
         Can't use like_count as clustering key — it changes.

Solution:
  Step 1: On GET /comments?sort=top — check Redis cache first.
          Key: top_comments:{postId} → cached JSON of top 20
          TTL: 5 minutes

  Step 2: If cache miss:
          - Read top 500 recent comments from Cassandra (fast, one partition)
          - For each, GET comment_likes:{commentId} from Redis (pipeline)
          - Sort by like count in application layer
          - Cache result in Redis with 5-min TTL
          - Return top 20

  This is exactly what YouTube does: "top comments" = periodically computed.
```

### Deep Dive C: Write-Back Pattern (Redis → Cassandra)

```
Why write-back:
  - Redis loses data on crash/restart (without AOF persistence)
  - Cassandra is durable but slower to write for counters
  - Solution: Redis = hot layer (live counts), Cassandra = cold layer (durable)

Write-back job (runs every 5 minutes):
  1. SCAN Redis for keys matching likes:*
  2. For each key: GET current value
  3. UPSERT into Cassandra like_counts table
  4. Clear Redis key (reset to 0) — risky window!

Better approach (double-write):
  On each like action:
    INCR likes:{postId}        ← Redis (fast, synchronous)
    Kafka publish like-event   ← async
  Kafka consumer (like-count-persister):
    Batch 1000 events → single Cassandra batch write
    ~ every 100ms flush
```

---

## STEP 8 — Scalability

**BOTTLENECK 1: Viral Post Like Flood**
```
Problem: One postId receives 100K likes/sec.
         Redis SET liked_by:{postId} becomes hot key.

Solution:
  - Shard liked_by SET into 100 sub-keys by userId % 100
  - Each shard handles 1K ops/sec (well within Redis limits)
  - For read (has-user-liked): single SISMEMBER on correct shard
  - For bulk (who liked): SUNION all shards (expensive, avoid)
  - OR: Bloom filter per post for like existence checks
```

**BOTTLENECK 2: Comment Write Amplification**
```
Problem: Inserting 5,787 comments/sec; heavy posts get millions of comments.
         One Cassandra partition per postId → partition can get huge.

Solution:
  - Cassandra handles large partitions well (not a hot partition, just a large one)
  - Limit partition size: if comment_count > 10M, create a sub-partition
    Key: (post_id, bucket) where bucket = comment_count / 1_000_000
  - Compaction strategy: TWCS (TimeWindowCompactionStrategy) — comments are
    write-heavy, time-ordered → TWCS minimizes write amplification
```

**BOTTLENECK 3: Notification Fan-out on Viral Likes**
```
Problem: Celebrity post gets 1M likes in 10 minutes.
         1M Kafka events → 1M push notifications to post owner.
         Post owner's phone explodes.

Solution:
  - Notification throttle: max 1 notification per 10 minutes per post for likes.
  - Batch: "10,000 people liked your post" instead of 10,000 notifications.
  - Implementation: Redis counter notifications:{postId}:{userId} with 10-min TTL.
    If counter < 1 → send notification, set counter.
    If counter >= 1 → skip notification, increment batch count.
    After TTL expires → send "and X more people liked your post".
```

**BOTTLENECK 4: Read Amplification on Comment Load**
```
Problem: 10M users load a viral post simultaneously.
         Each load fetches top 20 comments.
         10M requests to Cassandra for same data.

Solution:
  - CDN caching for top-20 comments on viral posts (TTL 30 seconds)
  - Redis cache for top_comments:{postId} (TTL 5 minutes)
  - Cache key invalidation on new comment: DEL top_comments:{postId}
  - For very viral posts: pre-compute and push to edge CDN nodes
```

---

## STEP 8 — TRADE-OFFS

*"Let me walk through the key architectural trade-offs I made and why."*

```
┌─────────────────────────────┬────────────────────────────┬──────────────────────────────────────────────────────────┐
│ DECISION                    │ CHOICE MADE                │ TRADE-OFF                                                │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Like count storage          │ Redis INCR                 │ Atomic, sub-ms, handles 100K likes/sec vs. not durable   │
│                             │                            │ (5-min write-back to Cassandra, could lose ~5 min)       │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Like existence check        │ Redis SET (liked_by)       │ O(1) SISMEMBER vs. at 10M likers, SET uses ~500MB per    │
│                             │                            │ viral post — mitigated by Bloom filter                   │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Comment storage             │ Cassandra (partition by    │ All comments for one post = one partition scan vs. hot   │
│                             │ post_id)                   │ partition for viral posts (millions of comments)         │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Comment sorting             │ Recent-first (TIMEUUID)    │ Free (time-ordered clustering) vs. top-first requires    │
│                             │                            │ separate Redis cache of top-N, updated every 5 min       │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Toxicity detection          │ Async ML (Kafka classifier)│ Non-blocking, doesn't slow comment submission vs.        │
│                             │                            │ toxic comments visible for seconds before hidden         │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Reply threading             │ 2-level max (Instagram)    │ Simpler query (parent_comment_id filter) vs. Reddit-     │
│                             │                            │ style deep nesting requires recursive queries            │
├─────────────────────────────┼────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Notification on like        │ Async Kafka → FCM/APNs     │ Non-blocking, batched efficiently vs. slight delay       │
│                             │                            │ (seconds) before notification arrives                    │
└─────────────────────────────┴────────────────────────────┴──────────────────────────────────────────────────────────┘
```

*"The most important trade-off is Redis INCR vs. Cassandra COUNTER for like counts. Cassandra COUNTERs use LWW (Last Write Wins) semantics with known issues under high contention. Redis INCR is atomic single-threaded — no contention possible. The downside is durability: 5-minute write-back window means we could lose a few minutes of likes on Redis crash. For social media, that's completely acceptable."*

---

## WHAT NOT TO SAY ✗

```
✗  "Store like count in the posts table"
   → Massive UPDATE lock contention on viral posts. 100K likes/sec
     all hitting UPDATE posts SET like_count=like_count+1 WHERE id=?
     This serializes all likes through one row lock. Database melts.

✗  "Use MySQL for comments at scale"
   → 500M inserts/day on a single MySQL table. No natural sharding strategy.
     Cassandra's partition-per-post model is architecturally correct here.

✗  "Hard delete comments"
   → Breaks reply chains (orphaned replies still reference deleted parent).
     Breaks notification deep-links. Breaks audit trail. Always soft delete.

✗  "Synchronous ML toxicity check on comment submit"
   → ML inference = 50-200ms. Adds this to every comment POST. Use Kafka
     to make it async. Comment shows immediately; if toxic, hide within seconds.

✗  "Use OFFSET pagination for comments"
   → OFFSET N scans and discards N rows. Unstable under concurrent inserts.
     New comment on page 1 shifts all subsequent pages → duplicates/gaps.
     Cursor-based pagination is the correct approach.

✗  "Store exact like count for every post in real time"
   → Approximate counts ("1.2M") are acceptable. Exact strong consistency
     would require distributed locking, killing throughput. Not worth it.

✗  "Use Redis pub/sub for notifications"
   → Redis pub/sub doesn't persist messages. If Notification Service is down
     when event fires, notification is lost forever. Use Kafka for durability.
```

---

## SENIOR TRAP QUESTIONS (15 YOE Level)

### Category 1: Counter Accuracy and Consistency

**Q: If Redis crashes before the write-back job runs, we lose 5 minutes of like data. How do you handle this?**

A: "Two approaches. First: enable Redis AOF (Append-Only File) persistence with fsync=everysec. This limits data loss to at most 1 second of likes on crash. Second: the Kafka like-event topic is durable (retention 7 days). Even if Redis loses its state, we can replay the last 5 minutes of Kafka events to recompute the exact count. The write-back consumer can be a Kafka consumer that writes directly to Cassandra, making Cassandra the ground truth and Redis just a cache layer that can always be rebuilt from Kafka."

**Q: What if two users unlike at the exact same millisecond and the counter goes negative?**

A: "This is prevented by a Lua script executed atomically in Redis. The script checks if count > 0 before decrementing. Since Redis executes Lua scripts atomically — no other command can interleave — this prevents negative counts. Additionally, the like existence check (SISMEMBER liked_by SET) is performed before calling unlike. If user hasn't liked, we return early without touching the counter. Both guards together make negative counts impossible."

### Category 2: Distributed Systems Corner Cases

**Q: User quickly double-taps to like then immediately taps again to unlike. The unlike request arrives at the server BEFORE the like request due to network jitter. How do you handle out-of-order requests?**

A: "This is an idempotency problem. Solution: version-stamp each like/unlike with a client-generated timestamp. Like Service accepts the request with the later timestamp and discards earlier ones for the same (userId, postId) pair. In practice: Redis key `like_ts:{userId}:{postId}` stores the timestamp of the last accepted action. If incoming request's timestamp < stored timestamp → reject as stale. If timestamp is newer → process and update stored timestamp. This makes the final state correct regardless of network ordering."

**Q: The write-back job reads Redis counters and writes to Cassandra. If the job runs while new likes are arriving, do we have a TOCTOU (Time Of Check Time Of Use) race?**

A: "Yes. The naive approach — GET counter, write to Cassandra, reset counter to 0 — has a race: new likes arrive between GET and reset, and they get zeroed out. The correct approach is GETSET (atomic get-and-set to 0) or GETDEL. Redis GETDEL atomically retrieves and deletes the key. Any likes that arrive after GETDEL go into a fresh counter key. In Cassandra, use a counter column with ADD delta (not SET absolute value), so: `UPDATE like_counts SET count = count + delta WHERE post_id = ?`. This way multiple write-back jobs can run safely without coordination."

### Category 3: Product and Feature Depth

**Q: Instagram wants to add "reaction types" (love, haha, wow, sad, angry) like Facebook. How does this change your like system?**

A: "Three changes: First, the like count becomes per-reaction-type. Redis keys become: `reaction:{postId}:{reactionType}` → INT counter. Six keys per post instead of one, same INCR pattern. Second, the liked_by structure needs to store which reaction: `reacted_by:{postId}:{userId}` → STRING (reaction type). This replaces the SET with a HASH or STRING per user. Third, the user can switch reactions (love → wow). This is: HSET reacted_by:{postId}:{userId} wow, then DECR reaction:{postId}:love, INCR reaction:{postId}:wow. All three Redis operations should be wrapped in a Lua script for atomicity. The write-back job now writes 6 counter values per post to Cassandra."

**Q: How would you implement the "3 mutual friends liked this" annotation under a post? (e.g., "John, Mary, and 2 others liked this")**

A: "This requires a social graph intersection at read time. When rendering a post for user X: (1) Get user X's following list (or friends) from Social Graph Service — cached in Redis as a SET: `following:{userId}`. (2) Get recent likers of the post — from Cassandra post_likes table, last 1000 likers, sorted by time DESC. (3) Intersect the two sets. In practice: SINTERSTORE intersection:{userId}:{postId} following:{userId} recent_likers:{postId} — with recent_likers loaded into a temp Redis SET. (4) SRANDMEMBER to pick 3 for display. This is expensive for every post render. Optimization: precompute per-user notifications (friend liked your feed post) and cache the result at feed generation time."

---

## KEY NUMBERS

```
┌─────────────────────────────────────────┬─────────────────────────────────────────────┐
│ Metric                                  │ Number                                      │
├─────────────────────────────────────────┼─────────────────────────────────────────────┤
│ Instagram likes/day                     │ 4.2 billion                                 │
│ Average likes/sec                       │ 48,600                                      │
│ Peak likes/sec (viral post)             │ 100,000 on one postId                       │
│ Comments/day                            │ 500 million                                 │
│ Average comments/sec                    │ 5,787                                       │
│ Redis INCR throughput (single key)      │ ~1,000,000 ops/sec                         │
│ Redis SET size at 10M likers            │ ~80 MB (8 bytes × 10M userIds)             │
│ Bloom filter size at 10M, 1% FPR        │ ~12 MB                                     │
│ Cassandra partition for active post     │ Handles millions of rows, single partition │
│ Comment read latency (Cassandra)        │ < 10ms (single partition scan)             │
│ Write-back job interval                 │ Every 5 minutes                            │
│ Like display lag (eventual consistency) │ Up to 5 seconds                            │
│ Comment data growth/day                 │ ~100 GB (500M × 200 bytes)                 │
│ Liked_by shard count                    │ 100 sub-keys (userId % 100)                │
│ Max comments before sub-partitioning    │ 10 million per post                        │
└─────────────────────────────────────────┴─────────────────────────────────────────────┘
```
