# Fan-Out on Write vs Fan-Out on Read
### Instagram Post: Push to All Followers' Feeds (Write) vs Pull at Read Time

---

## PART 1 — THE STUDENT CONVERSATION

**Instagram has a user with 50 million followers (Cristiano Ronaldo). He posts a photo. When should his 50 million followers' feeds get updated?**

**Fan-out on Write (Push model):** The moment he posts, his 50 million followers' feeds are immediately updated in the background. When any follower opens the app, their feed is already pre-computed. Reading is instant. Writing is expensive.

**Fan-out on Read (Pull model):** Nobody's feed is pre-computed. When a follower opens the app, the system fetches all the people they follow, gets each person's latest posts, merges and sorts them. Reading is expensive. Writing is instant.

Neither is perfect. The right answer, for most production social networks including Instagram, is a **hybrid**:
- Normal users (< 1000 followers): fan-out on write. Writing is cheap for small followings.
- Celebrities (millions of followers): fan-out on read. Can't afford to write to 50M feeds every post.

---

## PART 2 — FAN-OUT ON WRITE (PUSH)

```
Cristiano posts a photo (50M followers):
────────────────────────────────────────────────────────────────────

POST /posts { photo: ..., caption: "Goal!" }
       │
       ▼
  Post Service
  ├── INSERT post into Posts DB → post_id = 99999
  └── Publish to Kafka: { event: "NewPost", post_id: 99999, user_id: CR7 }

       │ (async — Cristiano gets 200 OK immediately)
       ▼
  Fan-out Worker (Kafka consumer)
  ├── Fetch all follower IDs of CR7: [follower_1, follower_2, ... follower_50M]
  │   (this is 50M rows from Followers table — takes seconds)
  │
  └── For each follower:
      INSERT INTO feed_cache (user_id, post_id, score=timestamp)
      INTO Redis ZSET: ZADD feed:follower_1 <timestamp> 99999
                       ZADD feed:follower_2 <timestamp> 99999
                       ...
                       ZADD feed:follower_50M <timestamp> 99999
  → 50 million Redis writes per celebrity post

READ (any follower opens app):
  ZRANGE feed:follower_123 0 19 REV WITHSCORES
  ← instant! Feed is pre-built in Redis. O(log N + K). <1ms
```

**Problem:**
```
  CR7 posts → 50M Redis writes → takes 10–30 minutes to complete
  Follower opens app immediately after post → might not see it yet
  → Inconsistency window

  50 celebrities post simultaneously → 50 × 50M = 2.5 billion Redis writes
  → Fan-out queue explodes, system overwhelmed
```

---

## PART 3 — FAN-OUT ON READ (PULL)

```
Cristiano posts a photo (50M followers):
────────────────────────────────────────────────────────────────────

POST /posts { photo: ..., caption: "Goal!" }
       │
       ▼
  Post Service
  └── INSERT post into Posts DB → post_id = 99999
      (that's it — no fan-out)

READ (follower opens app):
  GET /feed for follower_123
       │
       ▼
  Feed Service
  ├── Fetch follower's followings: [userA, userB, CR7, userD, ...]
  │   (from Following table → typically 200–500 accounts followed)
  │
  ├── For each following, fetch their latest N posts:
  │   SELECT * FROM posts WHERE user_id = CR7 ORDER BY created_at DESC LIMIT 10
  │   SELECT * FROM posts WHERE user_id = userA ORDER BY created_at DESC LIMIT 10
  │   ... (500 DB queries for 500 followings)
  │
  └── Merge all results, sort by timestamp, return top 20

READ is expensive:
  500 DB queries per feed load
  DB has 50M posts from CR7 alone → indexes help but still slow
  User with 1000 followings → 1000 DB queries per feed load

  At 1M users opening feeds simultaneously:
  1M × 500 queries = 500M DB queries per second → impossible
```

---

## PART 4 — THE HYBRID (WHAT INSTAGRAM ACTUALLY DOES)

```
Hybrid fan-out model:
────────────────────────────────────────────────────────────────────

On POST:
  If poster has < 10,000 followers:
    → Fan-out on WRITE: immediately push post_id to all follower feeds in Redis
    → 10,000 writes is fast (~10ms)

  If poster has ≥ 10,000 followers (influencer/celebrity):
    → No fan-out. Just INSERT into Posts DB.
    → Mark user as "celebrity" in Users table.

On READ (follower opens feed):
  Step 1: Load pre-built feed from Redis ZSET
          ZRANGE feed:{follower_id} 0 99 REV WITHSCORES
          This contains post_ids from regular users (fan-out-on-write posts)

  Step 2: Fetch celebrity posts dynamically (fan-out-on-read for celebrities)
          For each celebrity the user follows:
          SELECT post_id FROM posts WHERE user_id = ? ORDER BY created_at DESC LIMIT 10
          (user follows ~5 celebrities → 5 queries, not 500)

  Step 3: Merge celebrity posts with pre-built feed
          Sort combined list by timestamp
          Return top 20

  Step 4: Cache merged result in Redis for 60 seconds (avoid re-computation)

Result:
  Feed write (regular user): cheap, instant fan-out to small follower set
  Feed write (celebrity): zero fan-out, just 1 DB insert
  Feed read: fast from Redis (pre-built) + small number of celebrity queries
  Consistency: regular users' posts arrive instantly, celebrity posts pulled live
```

---

## PART 5 — THE INTERVIEW CONVERSATION

**Interviewer:** "Design the Instagram feed. How do posts show up in followers' feeds?"

**You (architect answer):**

> "The core decision is fan-out strategy — do we pre-compute feeds on write or assemble
> them on read? Pure fan-out on write is fast to read but breaks for celebrities: Cristiano
> posting means 50 million Redis writes — the write queue never drains. Pure fan-out on read
> is simple to write but requires 500 DB queries per feed load — doesn't scale either.
>
> Instagram's public engineering posts describe a hybrid: fan-out on write for normal users,
> fan-out on read for celebrities.
>
> When a user posts: if they have fewer than 10,000 followers, a fan-out worker reads their
> follower list from Cassandra (sharded by follower_id) and pushes the post_id to each
> follower's feed in Redis (ZADD with post timestamp as score). 10K writes is under 100ms.
>
> For a celebrity post: nothing is pushed. The post is just stored in the Posts DB.
>
> On read: we fetch the pre-built Redis ZSET (post_ids from fan-out-on-write), then for each
> celebrity the user follows (typically 3–10 out of their 500 followings), we query the
> Posts DB directly for their latest posts. Merge everything by timestamp, return top 20.
>
> The threshold (10K followers) is tunable. We'd expose it as a config value and adjust based
> on observed Redis write queue depth. At 1M users × average 200 followings, we can compute
> the cross-over point where fan-out-on-write cost exceeds fan-out-on-read cost."

---

## PART 6 — DATA MODEL

```
Feed storage (Redis ZSET per user):
  Key:   feed:{user_id}
  Score: timestamp (epoch ms) → enables time-sort
  Value: post_id

  ZADD feed:user123 1704067200000 "post_99999"
  ZADD feed:user123 1704067180000 "post_99990"

  ZRANGE feed:user123 0 19 REV WITHSCORES  → top 20 posts, newest first

Posts table (Cassandra — partition by poster_id):
  PRIMARY KEY: (user_id, created_at DESC, post_id)
  → fast fetches of latest posts for a given user (celebrity fan-out-on-read)

Followers table (Cassandra — two tables for both directions):
  Following: (follower_id → list of followed_ids)  ← "who does user X follow?"
  Followers: (followed_id → list of follower_ids)  ← "who follows user X?"
  Both needed: following for feed assembly, followers for fan-out worker.
```

---

## QUICK REFERENCE CARD

```
Fan-out on Write (Push):
  On post: push post_id to all follower feeds
  On read: fetch from pre-built Redis ZSET (instant)
  Best for: users with small follower counts (<10K)
  Bottleneck: celebrities blow up write queue

Fan-out on Read (Pull):
  On post: just store the post
  On read: query all followings' recent posts, merge
  Best for: celebrities (no write amplification)
  Bottleneck: N queries per feed load

Hybrid (production reality):
  Small accounts: fan-out on write → Redis feed cache
  Celebrity accounts: fan-out on read → direct Posts DB query
  Threshold: typically 10K–100K followers (tunable)
  Read path: merge Redis pre-built + celebrity pull → cache merged result

Companies using hybrid:
  Instagram, Twitter (prior to acquisition), Facebook, LinkedIn

Interview one-liner:
"Fan-out on write pre-builds feeds — great for reads but write-amplification
kills you for celebrities. Fan-out on read is write-cheap but read-expensive.
The hybrid: fan out small accounts on write, pull celebrity posts on read.
Most production social networks do exactly this."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Every social feed interview will ask you this — if you say "just push to all followers" without mentioning the celebrity problem, the interviewer knows you haven't thought it through.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **05 — Social Media (Instagram/Facebook)** | The core feed architecture decision. Regular users (<10K followers): fan-out on write — post_id pushed to all follower Redis ZSETs immediately. Celebrities (10M followers): fan-out on read — pull their posts at read time, merged with pre-built feed. Hybrid is the production answer Instagram uses. |

**Architect's one-liner for the interview:**
*"Fan-out on write is fast to read but explodes on celebrities — the hybrid approach fans out small accounts and pulls celebrity posts at read time."*
