# Social Media Feed Generation — Beginner's Learning Guide

> **System Goal:** Build personalized news feeds like Facebook/Instagram that load in &lt;500ms for 500M daily active users

## 🎯 What You'll Learn

This guide walks you through the **#1 challenge in social media architecture**: generating personalized feeds at scale. By the end, you'll understand:

1. **Why naive database JOINs break** at 115K feed loads/second
2. **Fanout on write (PUSH)** vs **Fanout on read (PULL)** models
3. **When to use which database** (PostgreSQL vs Cassandra vs Redis)
4. **How denormalization** trades consistency for speed
5. **Celebrity problem** and why 400M followers need a different strategy

---

## 📚 Study Plan

### **Day 1: The Feed Generation Problem** (2 hours)

**Read:** [01-context-BEGINNER.drawio](01-context-BEGINNER.drawio)

**Key Questions to Answer:**
- Why does `SELECT * FROM posts JOIN followers` fail at scale?
- What is fanout? Why is it called that?
- What's the newspaper printing press analogy?
- Why can't we fanout Selena Gomez's posts to 400M followers?

**Hands-On:**
```sql
-- Try this on a local PostgreSQL with 1M rows:
EXPLAIN ANALYZE
SELECT p.* FROM posts p
JOIN followers f ON p.user_id = f.followee_id
WHERE f.follower_id = 'bob'
ORDER BY p.created_at DESC LIMIT 20;

-- Notice the query plan: Sequential Scan → Hash Join → Sort
-- At 115K queries/sec, your DB would melt
```

**Interview Prep:**
> **Q:** "Why can't we just cache the JOIN query?"
> 
> **A:** "The feed is personalized per user. 500M users × 200 follows each = 100B possible JOIN combinations. Even with a 1% cache hit rate, that's still 1.15K queries/sec hitting the database. The cache would be enormous and mostly stale (feeds change every time someone posts). Fanout pre-builds the result so there's zero DB load on read."

---

### **Day 2: Architecture Components** (3 hours)

**Read:** [02-architecture-components-BEGINNER.drawio](02-architecture-components-BEGINNER.drawio)

**Key Questions:**
- Why Redis for feed cache instead of Memcached?
- Why Cassandra for posts instead of PostgreSQL?
- What does "denormalized counter" mean?
- How does write amplification work in fanout?

**Hands-On:**
```bash
# Install Redis locally
brew install redis
redis-server

# Try feed operations
redis-cli
> LPUSH feed:bob post_123
> LPUSH feed:bob post_122
> LPUSH feed:bob post_121
> LRANGE feed:bob 0 19         # Read 20 posts instantly
> LTRIM feed:bob 0 999         # Keep only latest 1000
```

**Interview Prep:**
> **Q:** "Why separate Post Service and Feed Service?"
> 
> **A:** "They scale differently. Post Service handles 1.2K writes/sec with high CPU for media processing. Feed Service handles 115K reads/sec with high memory for caching. If bundled, scaling one wastes resources on the other. Also, separate services mean independent deployments — a bug in feed serving doesn't take down post creation."

---

### **Day 3: Push vs Pull Deep Dive** (3 hours)

**Read:** [03-feed-flow-sequence-BEGINNER.drawio](03-feed-flow-sequence-BEGINNER.drawio)

**Key Questions:**
- What happens in the 2-second fanout window?
- Why is Alice's response 202 Accepted, not 200 OK?
- How does the hybrid model (5K threshold) work?
- What's the exact timing breakdown for Bob's feed load?

**Hands-On:**
```python
# Simulate fanout timing
import time

followers = 500  # Alice has 500 followers
redis_write_time = 0.004  # 4ms per LPUSH

start = time.time()
for i in range(followers):
    # Simulate LPUSH feed:follower_{i} post_123
    time.sleep(redis_write_time)
end = time.time()

print(f"Fanout time: {end - start:.2f}s")  # ~2 seconds
```

**Interview Prep:**
> **Q:** "What if a celebrity has 10M followers but only 1M are active users?"
> 
> **A:** "The hybrid model optimizes for this. We'd PUSH to the 1M active users (logged in last 7 days) and store that list in Redis. The 9M inactive users get PULL on-demand when they return. This avoids 9M wasted writes to users who won't even open the app. The active user list is refreshed daily via a background job."

---

### **Day 4: Data Model & Denormalization** (3 hours)

**Read:** [04-data-model-BEGINNER.drawio](04-data-model-BEGINNER.drawio)

**Key Questions:**
- Why is `likes_count` stored in 3 places?
- What's the PRIMARY KEY for Cassandra posts table and why?
- Why INDEX ON `followee_id` in the followers table?
- When is eventual consistency acceptable vs not?

**Hands-On:**
```sql
-- PostgreSQL: Test the follower lookup index
CREATE INDEX idx_followee ON followers(followee_id);

EXPLAIN ANALYZE
SELECT follower_id FROM followers WHERE followee_id = 'alice';
-- Should show "Index Scan" not "Seq Scan"

-- Cassandra: Test partition key distribution
CREATE TABLE posts (
  user_id uuid,
  created_at timestamp,
  post_id uuid,
  content text,
  likes_count bigint,
  PRIMARY KEY (user_id, created_at, post_id)
) WITH CLUSTERING ORDER BY (created_at DESC);

-- Query by user_id hits one partition = fast
SELECT * FROM posts WHERE user_id = ? ORDER BY created_at DESC LIMIT 100;
```

**Interview Prep:**
> **Q:** "Why not use a graph database for followers?"
> 
> **A:** "Graph DBs (like Neo4j) excel at multi-hop traversals — 'friends of friends', 'people you may know'. For simple follower lookups ('who follows Alice?'), a PostgreSQL index on `followee_id` is fast enough and much simpler to operate. Graph DBs add value only when you need 2-hop or 3-hop queries at scale. Instagram uses PostgreSQL for the social graph and only introduced graph DB for recommendation features."

---

### **Day 5: Scale Calculations** (2 hours)

**Calculate These Yourself:**

1. **Redis Memory:**
   - 500M DAU, avg 1000 posts cached per user
   - Each entry: 50 bytes (post_id + metadata)
   - Total: ?

2. **Fanout Load:**
   - 100M posts/day = 1,157 posts/sec
   - Avg 200 followers per user
   - Redis writes/sec during peak: ?

3. **Database Queries:**
   - 115K feed loads/sec
   - Each feed = 1 Redis LRANGE + 1 Cassandra batch SELECT
   - Redis QPS: ?
   - Cassandra QPS: ?

**Answers:**
1. 500M × 1000 × 50 bytes = 25 GB
2. 1,157 posts/sec × 200 followers = 231,400 Redis LPUSH/sec
3. Redis: 115K LRANGE/sec, Cassandra: 115K batch SELECTs/sec

---

## 🎤 Interview Mock Scenarios

### **Scenario 1: Clarification Questions** (2 min)

**Interviewer:** "Design a social media feed system."

**You:** "Let me clarify a few things before diving in:

1. **Scope:** Are we doing just the feed, or also post creation, likes, comments?
2. **Scale:** 500M DAU? 1B? What's the read/write ratio?
3. **Latency:** What's the target feed load time? &lt;500ms?
4. **Consistency:** Is it okay if a post takes 5-10 minutes to appear in feeds, or must it be instant?
5. **Feed type:** Reverse chronological, or ranked by engagement?"

---

### **Scenario 2: Deep Dive — Redis vs Database**

**Interviewer:** "Why not just cache the database query result in Redis?"

**You:** "Two problems:

1. **Cache key explosion:** 500M users × personalized feeds = 500M cache keys. A user follows 200 people, any of whom can post anytime. The cache invalidation matrix is 500M × 200 = 100B edges. Nightmare to invalidate correctly.

2. **Cache miss penalty:** When Bob's cache expires and he requests his feed, we're back to the slow JOIN query. At 115K reads/sec with even a 5% miss rate, that's 5,750 JOINs/sec hitting the database. Still collapses.

Fanout pre-builds the feed incrementally as posts arrive. There's no cache expiry problem because the cache is the source of truth for 'what should Bob see', not a copy of a query result."

---

### **Scenario 3: Trade-Off Discussion**

**Interviewer:** "Your fanout system writes 1 post to 500 followers. Isn't that wasteful?"

**You:** "It is write amplification — 1 write becomes 500. But it's a deliberate trade-off:

**Pros:**
- Reads are instant (&lt;10ms Redis LRANGE vs 200ms JOIN)
- Read/write ratio is 100:1 — we optimize for the hot path (reads)
- Redis handles 231K writes/sec easily with clustering

**Cons:**
- 500× more writes than posts created
- Breaks for celebrities (millions of writes) → that's why we have the PULL model for &gt;5K followers

The alternative is to JOIN on every read. At 115K reads/sec, the read amplification is worse: 115K queries × 200 followers scanned each = 23M row scans per second. Redis can't even cache that effectively because the result set is too large and changes constantly."

---

## 🔧 Common Mistakes to Avoid

### ❌ **"I'd use a graph database for everything"**
**Why Wrong:** Graph DBs are overkill for simple follower lookups. PostgreSQL with an index is simpler and faster for 1-hop queries. Graph DBs earn their place only for multi-hop traversals.

### ❌ **"Fanout can be synchronous"**
**Why Wrong:** Fanning out to 500 followers takes 2 seconds. The user would wait 2 seconds to see "Post created" — terrible UX. Always fanout async via Kafka.

### ❌ **"Store exact like counts in PostgreSQL"**
**Why Wrong:** A viral post getting 50K likes/min would create a write hotspot on a single row (the post's `likes_count` column). Use Redis INCR (lock-free, 100K ops/sec) and sync to DB in background.

### ❌ **"Cache the entire post object in Redis feed"**
**Why Wrong:** 500M users × 1000 posts × 2KB/post = 1 PB of Redis memory. Too expensive. Store only post_ids (8 bytes each) and hydrate from Cassandra on read.

---

## 📊 What to Draw on the Whiteboard

**Step 1 (30 sec):** High-level flow
```
Client → API GW → Feed Service → Redis (LRANGE) → return post_ids
                → Cassandra (batch SELECT) → return post data
```

**Step 2 (60 sec):** Fanout flow
```
Alice posts → Content Service → Cassandra (store)
                              → Kafka (publish)
                              → Fanout Service → FollowerDB (find 500)
                                               → Redis (LPUSH × 500)
```

**Step 3 (45 sec):** Database choices
```
┌─────────────┬──────────────┬─────────────────────┐
│ PostgreSQL  │ Cassandra    │ Redis               │
├─────────────┼──────────────┼─────────────────────┤
│ Users       │ Posts        │ feed:{user_id}      │
│ Followers   │ Likes        │ likes_count:{post}  │
│ Comments    │              │ like:{user}:{post}  │
└─────────────┴──────────────┴─────────────────────┘
```

**Step 4 (20 sec):** Push vs Pull threshold
```
<5K followers   → PUSH (fanout on write)
>5K followers   → PULL (fanout on read)
```

---

## 🎯 Interview Closing Statement

**You:** "To summarize:

We use **fanout on write** to pre-build feeds in Redis, turning 115K personalized queries into simple cache lookups. Posts are stored in Cassandra for high write throughput, users and followers in PostgreSQL for relational integrity, and feeds in Redis for sub-10ms reads.

For celebrities with &gt;5K followers, we switch to **fanout on read** to avoid write amplification. Their posts are queried on-demand and cached for 10 minutes.

Counters are denormalized across Redis, Cassandra, and PostgreSQL, synced by background jobs. This trades perfect consistency for the ability to handle 50K likes per minute without database locks.

The system handles 500M DAU, 100M posts per day, and keeps feed loads under 110ms end-to-end. Would you like me to dive deeper into any specific component?"

---

## 📖 Further Reading

- **Instagram Engineering Blog:** [Feed Ranking](https://engineering.fb.com/2021/01/26/ml-applications/news-feed-ranking/)
- **Cassandra Use Cases:** [Why Netflix Uses Cassandra](https://netflixtechblog.com/benchmarking-cassandra-scalability-on-aws-over-a-million-writes-per-second-39f45f066c9e)
- **Redis Patterns:** [Cache Patterns](https://redis.io/docs/manual/patterns/)
- **Fanout Explanation:** [Push vs Pull for News Feeds](https://www.youtube.com/watch?v=QmX2NPkJTKg)

---

## ✅ Self-Check Questions

Before your interview, make sure you can answer these:

1. **Why does the naive JOIN approach fail?** (Answer: 115K queries/sec × 200 followers = 23M row scans/sec)
2. **What is write amplification?** (Answer: 1 post → 500 fanout writes; acceptable trade-off for 100:1 read/write ratio)
3. **When to use PUSH vs PULL?** (Answer: &lt;5K followers = PUSH; &gt;5K = PULL)
4. **Why denormalize like counts?** (Answer: Avoid write hotspot on viral posts; Redis INCR is lock-free)
5. **Why Redis LIST not SORTED SET?** (Answer: LIST saves 8 bytes overhead per entry = 50 GB memory at scale)
6. **Why Cassandra partition by user_id?** (Answer: All posts by one user together = efficient timeline queries)
7. **Why index followers.followee_id?** (Answer: Query "who follows Alice" for fanout; without index = full table scan)
8. **Why TTL on idempotency keys?** (Answer: Save memory; old keys from days ago aren't needed)

---

## 🚀 Next Steps

After mastering this system, move on to:
- **Notification System** (Kafka + WebSocket + FCM)
- **Search & Autocomplete** (Elasticsearch + Trie)
- **Video Upload & Streaming** (S3 + CloudFront + HLS transcoding)

Good luck with your interview! 🎉
