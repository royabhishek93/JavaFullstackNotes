# Instagram Likes Feature - Interview Follow-up Questions & Answers

## Complete List of Interview Questions with Detailed Answers

---

## Category 1: Scale & Performance (10 Questions)

### Q1: How would you handle 1 million likes per second during a Super Bowl ad?

**Answer:**

**1. Pre-scaling (Before Event):**
```
- Scale Cassandra cluster 10x (from 50 to 500 nodes)
- Add 20 Redis cache clusters (from 5 to 25)
- Increase Kafka partitions (from 100 to 1000)
- Add read replicas in all regions
- Warm up caches with expected hot content
- Alert all on-call engineers
```

**2. Write Optimization:**
```
- Batch writes: 100 likes per DB transaction
- Sharded counters: 1000 shards for hot posts
- Async processing: Move all non-critical operations to Kafka
- Drop low-priority notifications (keep only post owner)
- Enable write coalescing (combine similar writes)
```

**3. Read Optimization:**
```
- CDN for count display (5-10 second stale is acceptable)
- Client-side aggregation (reduce server calls)
- Serve from cache only (bypass DB completely)
- Pre-compute popular views
```

**4. Monitoring & Alerts:**
```
- Real-time dashboard (Grafana, 1-second refresh)
- Auto-scaling triggers at 70% capacity
- PagerDuty alerts for P0 metrics
- Command center with engineers ready
```

**5. Graceful Degradation:**
```
Priority levels:
1. Accept likes (critical)
2. Update counts (high)
3. Show to user (medium)
4. Send notifications (low)
5. Update analytics (lowest)

Drop in reverse order if overwhelmed
```

---

### Q2: What if Redis goes down completely?

**Answer:**

**Immediate Response (< 1 second):**
```
1. Circuit breaker opens automatically
2. Failover to Redis replica (if available)
3. Fallback to direct DB reads
4. Disable write-through cache updates
5. Return cached data even if stale
```

**Short-term (< 5 minutes):**
```
1. If replica also down → Deploy new Redis cluster
2. Enable read-only mode for likes
3. Accept writes but delay count updates
4. Queue cache updates for later replay
```

**Recovery Process:**
```
1. Cache warm-up job (prioritized):
   - Hot posts (top 10K by traffic)
   - Recent posts (last 1 hour)
   - VIP/celebrity posts
   - Background fill for rest

2. Gradual traffic shift:
   - 10% traffic → monitor for 5 min
   - 50% traffic → monitor for 10 min
   - 100% traffic → full recovery

3. Monitor DB load carefully during recovery
```

**Prevention Strategy:**
```
1. Multi-region Redis replication (5 regions)
2. Persistent snapshots every 5 minutes to S3
3. Automated health checks every 30 seconds
4. Auto-failover with no manual intervention
5. Monthly disaster recovery drills
```

**Impact Analysis:**
```
Without Redis:
- Read latency: 10ms → 100ms (10x slower)
- Write latency: 50ms → 150ms (3x slower)
- DB load: Normal → 20x increase
- Cost: +$50K/hour (scaled DB instances)

Acceptable for short periods (< 30 minutes)
```

---

### Q3: How do you handle database write failures?

**Answer:**

**Retry Strategy:**
```
Attempt 1: Immediate retry
Attempt 2: Wait 100ms, retry
Attempt 3: Wait 500ms, retry
Attempt 4: Write to Dead Letter Queue (DLQ)

Total time before giving up: ~1 second
```

**Dead Letter Queue (DLQ):**
```
Structure:
{
  "request_id": "abc123",
  "user_id": "user-456",
  "post_id": "post-789",
  "action": "like",
  "timestamp": "2026-04-16T10:30:00Z",
  "retry_count": 3,
  "last_error": "WriteTimeout"
}

Storage: Kafka topic "likes-dlq"
Retention: 7 days
```

**DLQ Processing:**
```
1. Monitoring: Alert when DLQ size > 1000 messages
2. Recovery: Automated replay job every 5 minutes
3. Deduplication: Check if like already exists before replay
4. Manual intervention: If replay fails 10x, human review
```

**User Experience:**
```
- Return 500 error to client
- Client shows: "Could not process like, please try again"
- Client auto-retries after 2 seconds (with exponential backoff)
- User can manually retry via UI
```

---

### Q4: How would you optimize for read-heavy workload (100:1 read/write ratio)?

**Answer:**

**Read Optimization Strategies:**

**1. Multi-Level Caching:**
```
Layer 1: Client cache (mobile app)
- Cache duration: 1 minute
- Storage: In-memory (LRU cache)
- Size: 1000 posts

Layer 2: CDN (CloudFront)
- Cache duration: 30 seconds
- Hit rate target: 60%
- Reduce backend load by 60%

Layer 3: Redis cluster
- Cache duration: 1 hour
- Hit rate target: 95%
- Reduce DB load by 20x

Layer 4: Database (last resort)
- Only for cache misses
- 5% of total traffic
```

**2. Read Replicas:**
```
Setup:
- 1 primary node (writes only)
- 10 read replicas (reads only)
- Geo-distributed (5 regions)

Routing:
- Write: Always to primary
- Read: Round-robin across replicas
- Consistency: Eventual (5-10 second lag acceptable)
```

**3. Denormalization:**
```
Store pre-computed values:
- like_count directly on post table
- user_liked_status in separate table
- top_likers (first 100) in cache

Trade-off: More storage, faster reads
```

**4. Batch Read APIs:**
```
Instead of:
GET /posts/123/likes/count
GET /posts/456/likes/count
GET /posts/789/likes/count

Use:
POST /posts/likes/batch
Body: { "post_ids": [123, 456, 789] }

Result: 1 request instead of 3 (reduce network overhead)
```

**5. Materialized Views:**
```
Pre-aggregate data:
- Hourly like counts
- Daily trending posts
- Weekly top posts

Background job updates every hour
Serve from pre-computed results (instant response)
```

---

### Q5: How do you prevent thundering herd on a celebrity post?

**Answer:**

**Problem:**
```
Celebrity with 100M followers posts
→ 10M likes in first 5 minutes
→ All hit same database row
→ Database hotspot, contention, slowdown
```

**Solution 1: Sharded Counters**
```
Instead of single counter:
post_count = 1,543,291

Use 100 sharded counters:
shard_0 = 15,432
shard_1 = 15,431
...
shard_99 = 15,433

Sum on read: total = sum(all shards)

Benefits:
- Writes distributed across 100 rows
- 100x less contention
- Linear scalability
```

**Implementation:**
```javascript
// Write (Like)
function incrementLike(postId, userId) {
  const shard = hash(userId) % 100;
  
  cassandra.execute(
    `UPDATE like_counts_sharded 
     SET count = count + 1 
     WHERE post_id = ? AND shard = ?`,
    [postId, shard]
  );
}

// Read (Get Count)
function getLikeCount(postId) {
  // Check cache first
  const cached = redis.get(`like:count:${postId}`);
  if (cached) return cached;
  
  // Cache miss: Sum all shards
  const results = cassandra.execute(
    `SELECT shard, count 
     FROM like_counts_sharded 
     WHERE post_id = ?`,
    [postId]
  );
  
  const total = results.reduce((sum, row) => sum + row.count, 0);
  
  // Cache for 5 minutes
  redis.setex(`like:count:${postId}`, 300, total);
  
  return total;
}
```

**Solution 2: Write Coalescing**
```
Batch similar writes:

Instead of 1000 individual writes:
- INCR count WHERE post_id = 123 (x1000)

Do 1 batched write:
- INCR count BY 1000 WHERE post_id = 123

Reduces DB load by 1000x
```

**Solution 3: Dedicated Cache Cluster**
```
Hot post detection:
- Monitor like rate per post
- If rate > 1000 likes/sec, mark as "hot"
- Move to dedicated Redis cluster (high-memory, high-CPU)
- Isolate from normal posts

Benefits:
- Hot posts don't affect normal posts
- Can scale independently
```

**Solution 4: Rate Limiting per Post**
```
Limit: Max 100K likes/sec per post

If exceeded:
- Queue excess likes (Kafka buffer)
- Process asynchronously
- User sees "processing" state
- Eventually consistent

Trade-off: Slight delay, but system stays stable
```

---

### Q6: How do you handle network partitions between data centers?

**Answer:**

**Scenario:**
```
Data Center A (US-East)
Data Center B (US-West)
Network partition: Cannot communicate for 5 minutes
```

**Cassandra's Approach (Eventual Consistency):**
```
1. Both data centers continue accepting writes
2. Writes stored locally (no cross-DC sync during partition)
3. When partition heals, automatic reconciliation
```

**Conflict Resolution:**

**Option 1: Last Write Wins (LWW)**
```
User likes post at 10:00:00 in DC-A
User unlikes post at 10:00:05 in DC-B (during partition)

After reconciliation:
- Compare timestamps
- 10:00:05 > 10:00:00
- Result: Unlike wins (post is not liked)

Implementation:
- Every write has timestamp
- Cassandra automatically picks latest
```

**Option 2: CRDT (Conflict-free Replicated Data Type)**
```
For counters:
- DC-A: +5 likes
- DC-B: +3 likes
- After merge: +8 likes (commutative)

For like/unlike:
- Track both actions with vector clocks
- Merge based on causality
```

**Prevention:**
```
1. Multi-region replication (3+ regions)
   - If one partition, others still connected
   
2. Quorum reads/writes
   - Require majority acknowledgment
   - Sacrifice availability for consistency
   
3. Monitoring
   - Detect partitions within seconds
   - Alert engineers immediately
   
4. Testing
   - Chaos engineering (simulate partitions)
   - Monthly disaster recovery drills
```

---

### Q7: What's your caching strategy for different post types?

**Answer:**

**Post Type Classification:**

**1. Viral/Trending Posts (0.1% of posts)**
```
Characteristics:
- 10K+ likes per hour
- High read traffic
- Celebrity/influencer content

Cache Strategy:
- Cache location: Dedicated Redis cluster
- TTL: 24 hours (extended)
- Replication: 5x (across regions)
- Update frequency: Real-time (on every like)
- Pre-fetch: Anticipate next requests

Example:
Key: "viral:like:count:post-123"
Value: 5,432,109
TTL: 86400 seconds
```

**2. Hot Posts (1% of posts)**
```
Characteristics:
- 100+ likes per hour
- Active engagement
- Recent posts (< 24 hours old)

Cache Strategy:
- Cache location: Primary Redis cluster
- TTL: 1 hour
- Update frequency: On write
- Invalidation: Active (on like/unlike)

Example:
Key: "hot:like:count:post-456"
Value: 12,543
TTL: 3600 seconds
```

**3. Normal Posts (90% of posts)**
```
Characteristics:
- 1-100 likes per hour
- Standard engagement
- Most user content

Cache Strategy:
- Cache location: Standard Redis cluster
- TTL: 5 minutes
- Update frequency: Lazy (on read)
- Invalidation: TTL-based

Example:
Key: "like:count:post-789"
Value: 234
TTL: 300 seconds
```

**4. Cold Posts (8.9% of posts)**
```
Characteristics:
- 0 likes in last hour
- Old posts (> 7 days)
- Low engagement

Cache Strategy:
- Cache location: None (read from DB)
- Only cache on first read
- TTL: 1 minute
- Eviction: LRU (first to evict)
```

**Adaptive Caching Algorithm:**
```python
def get_cache_strategy(post_id):
    like_rate = calculate_like_rate(post_id, window="1h")
    
    if like_rate > 10000:
        return {
            "tier": "viral",
            "ttl": 86400,
            "cluster": "dedicated",
            "replication": 5
        }
    elif like_rate > 100:
        return {
            "tier": "hot",
            "ttl": 3600,
            "cluster": "primary",
            "replication": 3
        }
    elif like_rate > 1:
        return {
            "tier": "normal",
            "ttl": 300,
            "cluster": "standard",
            "replication": 2
        }
    else:
        return {
            "tier": "cold",
            "ttl": 60,
            "cluster": "standard",
            "replication": 1
        }
```

---

### Q8: How do you measure and improve cache hit rate?

**Answer:**

**Current Metrics:**
```
Target: 95% cache hit rate
Current: 92% cache hit rate
Gap: 3% (needs improvement)

Impact of 3% gap:
- 3% of 500K reads/sec = 15K additional DB queries/sec
- Cost: ~$5K/month in extra DB capacity
```

**Measurement:**
```python
# Instrumentation
def get_like_count(post_id):
    start_time = time.now()
    
    # Try cache
    cached = redis.get(f"like:count:{post_id}")
    
    if cached:
        metrics.increment("cache.hit")
        metrics.histogram("cache.latency", time.now() - start_time)
        return cached
    else:
        metrics.increment("cache.miss")
        
        # Fallback to DB
        count = cassandra.query(...)
        
        # Populate cache
        redis.setex(f"like:count:{post_id}", TTL, count)
        
        return count

# Aggregate metrics
cache_hit_rate = cache.hits / (cache.hits + cache.misses)
```

**Analysis (Why are we missing 3%)?**
```
1. Cache eviction (50% of misses)
   - LRU evicting too aggressively
   - Solution: Increase cache size by 20%

2. TTL expiration (30% of misses)
   - Short TTLs causing unnecessary misses
   - Solution: Increase TTL from 5min to 10min

3. New posts (15% of misses)
   - First read always misses
   - Solution: Pre-warm cache on post creation

4. Cache server restarts (5% of misses)
   - Periodic maintenance causing cold starts
   - Solution: Use persistent Redis (AOF enabled)
```

**Optimization Actions:**

**1. Increase Cache Size**
```
Before: 100 GB per Redis node
After: 120 GB per Redis node
Cost: +$500/month
Benefit: +1.5% hit rate (+7.5K DB queries/sec saved)
ROI: Saves $2.5K/month = +$2K/month net
```

**2. Smarter TTLs**
```
Dynamic TTL based on post age:
- New posts (< 1 hour): TTL = 5 minutes
- Recent posts (< 24 hours): TTL = 30 minutes
- Old posts (> 24 hours): TTL = 2 hours

Result: Reduce TTL expiration misses by 50%
```

**3. Pre-warming**
```
On post creation:
- Immediately set cache: like:count:post-123 = 0
- Pre-fetch user's follower list (for notification)
- Warm related caches (user's profile, etc.)

Result: Eliminate "first read" misses
```

**4. Probabilistic Cache Refresh (Stampede Prevention)**
```python
def get_with_smart_refresh(key, ttl):
    value, remaining_ttl = redis.get_with_ttl(key)
    
    if value is None:
        # Cache miss: fetch from DB
        return fetch_from_db_and_cache(key, ttl)
    
    # Probabilistic early refresh (prevent stampede)
    # Refresh probability increases as TTL decreases
    refresh_probability = 1 - (remaining_ttl / ttl)
    
    if random() < refresh_probability:
        # Async refresh (don't block current request)
        background_job.submit(lambda: fetch_from_db_and_cache(key, ttl))
    
    return value
```

**Expected Improvement:**
```
Before: 92% hit rate
After: 97% hit rate (+5 percentage points)

Impact:
- DB queries reduced: 15K/sec → 5K/sec
- Cost savings: $5K/month → $1.5K/month
- Latency improvement: p99 200ms → 150ms
```

---

### Q9: How do you handle write amplification in Cassandra?

**Answer:**

**Problem:**
```
1 like = Multiple writes:
- Insert into likes table
- Update counter table
- Update secondary index
- Write to commit log
- Write to memtable
- Eventual flush to SSTable

Write amplification factor: 5-10x
```

**Optimization Strategies:**

**1. Batch Writes**
```
Instead of:
INSERT INTO likes (post_id, user_id) VALUES (123, 1);
INSERT INTO likes (post_id, user_id) VALUES (123, 2);
INSERT INTO likes (post_id, user_id) VALUES (123, 3);

Use batch:
BEGIN BATCH
  INSERT INTO likes (post_id, user_id) VALUES (123, 1);
  INSERT INTO likes (post_id, user_id) VALUES (123, 2);
  INSERT INTO likes (post_id, user_id) VALUES (123, 3);
APPLY BATCH;

Benefit: 1 commit log entry instead of 3
```

**2. Reduce Secondary Indexes**
```
Before:
- Index on post_id
- Index on user_id
- Index on created_at
(3 index writes per insert)

After:
- Index on post_id only
- Denormalize other queries
(1 index write per insert)

Trade-off: More storage, less write amplification
```

**3. Tune Compaction**
```
Strategy: Leveled Compaction Strategy (LCS)

Benefits:
- Better read performance
- Lower write amplification
- Predictable behavior

Config:
sstable_size_in_mb: 160
fanout_size: 10
```

**4. Optimize Commit Log**
```
commitlog_sync: periodic
commitlog_sync_period_in_ms: 10000

Trade-off:
- Faster writes (no fsync wait)
- Risk: Lose 10 seconds of data on crash
- Acceptable for likes (non-critical)
```

**5. Memtable Sizing**
```
memtable_heap_space_in_mb: 2048
memtable_offheap_space_in_mb: 2048

Benefit:
- Larger memtable = fewer flushes
- Fewer SSTables = less compaction
- Lower write amplification
```

**Measurement:**
```
# Monitor write amplification
write_amplification_factor = 
  (bytes_written_to_disk) / (bytes_received_from_clients)

Target: < 5x
Current: 7x (needs improvement)

After optimizations: 4x (20% improvement)
```

---

### Q10: How would you implement geo-distributed likes with low latency?

**Answer:**

**Multi-Region Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│                     GLOBAL DISTRIBUTION                      │
└─────────────────────────────────────────────────────────────┘

Region: US-EAST (Virginia)
├─ API Gateway
├─ Like Service (3 instances)
├─ Redis Cluster (5 nodes)
└─ Cassandra Cluster (10 nodes)

Region: US-WEST (Oregon)
├─ API Gateway
├─ Like Service (3 instances)
├─ Redis Cluster (5 nodes)
└─ Cassandra Cluster (10 nodes)

Region: EU-WEST (Ireland)
├─ API Gateway
├─ Like Service (3 instances)
├─ Redis Cluster (5 nodes)
└─ Cassandra Cluster (10 nodes)

Region: ASIA-EAST (Singapore)
├─ API Gateway
├─ Like Service (3 instances)
├─ Redis Cluster (5 nodes)
└─ Cassandra Cluster (10 nodes)
```

**Request Routing (GeoDNS):**
```
User in New York
→ Routed to US-EAST (10ms latency)

User in London
→ Routed to EU-WEST (15ms latency)

User in Tokyo
→ Routed to ASIA-EAST (20ms latency)

Result: <25ms latency globally (vs 200ms single region)
```

**Write Strategy (Local Writes):**
```
User likes post in US-EAST:
1. Write to local Cassandra (US-EAST)
2. Acknowledge to user immediately (20ms)
3. Async replicate to other regions (background)

Benefit:
- User sees instant feedback
- Global consistency achieved eventually (5-10 seconds)
```

**Read Strategy (Read Local, Write Global):**
```
User views post in EU-WEST:
1. Read from local Redis (EU-WEST)
2. Cache hit → Return (5ms)
3. Cache miss → Read from local Cassandra (50ms)

Result: Low latency reads
```

**Consistency Trade-offs:**
```
Scenario: User in US likes, then immediately views from EU

Option 1: Eventual Consistency (Chosen)
- User sees like immediately in US
- User in EU sees stale count (5-10 sec lag)
- Trade-off: Better performance, slight staleness

Option 2: Strong Consistency
- Wait for all regions to ack (200ms)
- User sees consistent state everywhere
- Trade-off: Worse performance, strong consistency

For likes: Eventual consistency is acceptable
```

**Conflict Resolution:**
```
Scenario: User likes post simultaneously from 2 devices in 2 regions

US-EAST: INSERT (user-123, post-456) at 10:00:00.000
EU-WEST: INSERT (user-123, post-456) at 10:00:00.100

Resolution:
- Both writes succeed locally
- Cassandra's last-write-wins (LWW)
- Result: Only 1 like recorded (dedupe by primary key)

No double-counting due to unique constraint
```

---

## Category 2: Consistency & Correctness (8 Questions)

### Q11: How do you prevent double-counting a like?

**Answer:**

**Defense in Depth (Multiple Layers):**

**Layer 1: Client-Side**
```javascript
// Mobile app
let isLiking = false;

function handleLikeButton() {
  if (isLiking) {
    return; // Ignore subsequent clicks
  }
  
  isLiking = true;
  
  // Disable button
  likeButton.disabled = true;
  
  // Debounce (300ms)
  setTimeout(() => {
    apiClient.likePost(postId)
      .then(() => {
        // Update UI
        isLiking = false;
        likeButton.disabled = false;
      });
  }, 300);
}
```

**Layer 2: API Gateway (Rate Limiting)**
```
Per user rate limit:
- 10 likes per second
- 1000 likes per hour

Implementation:
- Token bucket algorithm
- Redis: "rate_limit:user-123"
- If exceeded: Return 429 Too Many Requests
```

**Layer 3: Idempotency Key (Redis)**
```python
def like_post(user_id, post_id):
    idempotency_key = f"idempotent:{user_id}:{post_id}"
    
    # Try to acquire lock (SET NX)
    acquired = redis.set(idempotency_key, "processing", nx=True, ex=5)
    
    if not acquired:
        # Lock exists: request already processing
        return {
            "status": 409,
            "error": "Request already in progress"
        }
    
    # Process like...
    result = process_like(user_id, post_id)
    
    # Release lock
    redis.delete(idempotency_key)
    
    return result
```

**Layer 4: Database Unique Constraint**
```sql
CREATE TABLE likes (
    post_id UUID,
    user_id UUID,
    created_at TIMESTAMP,
    PRIMARY KEY (post_id, user_id)  -- Composite primary key = unique constraint
);

-- Cassandra automatically enforces uniqueness
-- Duplicate INSERT will overwrite (idempotent)
```

**Layer 5: Application Logic**
```python
def process_like(user_id, post_id):
    # Check if already liked
    existing = cassandra.execute(
        "SELECT user_id FROM likes WHERE post_id = ? AND user_id = ?",
        [post_id, user_id]
    )
    
    if existing:
        # Already liked: return current state (idempotent)
        return {
            "status": 200,
            "message": "Already liked",
            "like_count": get_like_count(post_id)
        }
    
    # Not liked yet: insert new like
    cassandra.execute(
        "INSERT INTO likes (post_id, user_id, created_at) VALUES (?, ?, ?)",
        [post_id, user_id, datetime.now()]
    )
    
    # Increment counter
    increment_like_count(post_id)
    
    return {"status": 200, "like_count": get_like_count(post_id)}
```

**Result:**
```
Even if all layers fail, database constraint guarantees no duplicates.

Test case: User double-clicks 10 times within 100ms
- Click 1: Processed ✓
- Clicks 2-10: Blocked by idempotency layer ✗

Database: Only 1 like recorded
Counter: Incremented only once
```

---

### Q12: How do you ensure the like count is accurate?

**Answer:**

**Challenge:**
```
Counter table (fast, eventually consistent)
vs
COUNT(*) query (slow, accurate)

Which to use?
```

**Chosen Approach: Hybrid with Reconciliation**

**Real-Time: Counter Table (Fast but Approximate)**
```sql
-- Counter table (updated on each like/unlike)
CREATE TABLE like_counts (
    post_id UUID PRIMARY KEY,
    count COUNTER
);

-- Update (fast: <5ms)
UPDATE like_counts SET count = count + 1 WHERE post_id = ?;

-- Read (fast: <5ms)
SELECT count FROM like_counts WHERE post_id = ?;

Advantage: Fast
Disadvantage: Can drift (race conditions, failed writes)
```

**Periodic Reconciliation (Accurate but Slow)**
```python
# Nightly reconciliation job
def reconcile_like_counts():
    # Get all posts with likes
    posts = cassandra.execute("SELECT DISTINCT post_id FROM likes")
    
    for post in posts:
        # Accurate count (slow: COUNT query)
        actual_count = cassandra.execute(
            "SELECT COUNT(*) FROM likes WHERE post_id = ?",
            [post.post_id]
        ).one().count
        
        # Counter table value
        counter_value = cassandra.execute(
            "SELECT count FROM like_counts WHERE post_id = ?",
            [post.post_id]
        ).one().count
        
        # Check drift
        drift = abs(actual_count - counter_value)
        drift_percentage = (drift / actual_count) * 100 if actual_count > 0 else 0
        
        if drift_percentage > 1:  # More than 1% drift
            # Correct the counter
            cassandra.execute(
                "UPDATE like_counts SET count = ? WHERE post_id = ?",
                [actual_count, post.post_id]
            )
            
            # Alert engineers
            logger.warning(f"Corrected drift for post {post.post_id}: {counter_value} → {actual_count}")
            
            # Update cache
            redis.setex(f"like:count:{post.post_id}", 3600, actual_count)

# Run daily at 3 AM (low traffic)
schedule.every().day.at("03:00").do(reconcile_like_counts)
```

**Continuous Monitoring**
```python
# Hourly sanity check (sample 1000 random posts)
def sanity_check():
    sample_posts = get_random_posts(1000)
    
    total_drift = 0
    
    for post in sample_posts:
        actual = count_likes(post.post_id)
        cached = get_cached_count(post.post_id)
        
        drift = abs(actual - cached)
        total_drift += drift
    
    average_drift = total_drift / len(sample_posts)
    
    # Alert if average drift > 5 likes
    if average_drift > 5:
        pagerduty.alert(f"High like count drift detected: {average_drift}")

schedule.every().hour.do(sanity_check)
```

**Special Cases:**

**User's Own Posts (Strongly Consistent)**
```python
def get_like_count_for_owner(post_id, owner_id):
    # Owner sees accurate count (even if slower)
    return cassandra.execute(
        "SELECT COUNT(*) FROM likes WHERE post_id = ?",
        [post_id]
    ).one().count
```

**Other Users (Eventually Consistent)**
```python
def get_like_count_for_viewer(post_id):
    # Viewers see cached count (fast, may be slightly stale)
    cached = redis.get(f"like:count:{post_id}")
    
    if cached:
        return cached
    
    # Fallback to counter table (not COUNT query)
    count = cassandra.execute(
        "SELECT count FROM like_counts WHERE post_id = ?",
        [post_id]
    ).one().count
    
    redis.setex(f"like:count:{post_id}", 300, count)
    
    return count
```

**Accuracy Metrics:**
```
Target: 99.9% accuracy (drift < 0.1%)

Monitoring:
- Sample 10K posts hourly
- Calculate: drift = |actual - displayed| / actual
- Alert if drift > 0.1%

Current performance:
- Average drift: 0.03% (3 in 10,000)
- Acceptable for social media use case
```

---

### Q13: How do you handle race conditions when a user rapidly clicks like/unlike?

**Answer:**

**Scenario:**
```
User clicks: Like → Unlike → Like → Unlike (within 500ms)

Naive approach problems:
- Multiple requests in flight simultaneously
- Race condition: which one wins?
- Inconsistent final state
```

**Solution: State Machine with Versioning**

**1. Optimistic Locking (Version Numbers)**
```sql
CREATE TABLE user_like_status (
    user_id UUID,
    post_id UUID,
    liked BOOLEAN,
    version INT,  -- Version number for optimistic locking
    updated_at TIMESTAMP,
    PRIMARY KEY (user_id, post_id)
);
```

**2. Conditional Updates (Compare-and-Swap)**
```python
def toggle_like(user_id, post_id, action):
    # Read current state
    current = cassandra.execute(
        "SELECT liked, version FROM user_like_status WHERE user_id = ? AND post_id = ?",
        [user_id, post_id]
    ).one()
    
    if current is None:
        current_liked = False
        current_version = 0
    else:
        current_liked = current.liked
        current_version = current.version
    
    # Determine new state
    if action == "like":
        new_liked = True
    elif action == "unlike":
        new_liked = False
    else:
        raise ValueError("Invalid action")
    
    # No change needed
    if new_liked == current_liked:
        return {"status": "no_change", "liked": current_liked}
    
    # Conditional update (CAS: Compare-and-Swap)
    result = cassandra.execute(
        """
        UPDATE user_like_status 
        SET liked = ?, version = ?, updated_at = ?
        WHERE user_id = ? AND post_id = ? 
        IF version = ?
        """,
        [new_liked, current_version + 1, datetime.now(), user_id, post_id, current_version]
    )
    
    if result.was_applied:
        # Success: update applied
        update_counter(post_id, new_liked)
        return {"status": "success", "liked": new_liked, "version": current_version + 1}
    else:
        # Conflict: someone else updated in the meantime
        # Retry with exponential backoff
        time.sleep(random.uniform(0.01, 0.05))
        return toggle_like(user_id, post_id, action)
```

**3. Request Ordering (Sequential Processing)**
```python
# Use distributed lock per user-post pair
def process_like_action(user_id, post_id, action):
    lock_key = f"lock:like:{user_id}:{post_id}"
    
    # Acquire lock (blocking, max 5 seconds)
    lock = redis_lock.acquire(lock_key, timeout=5)
    
    if not lock:
        return {"status": "error", "message": "Could not acquire lock"}
    
    try:
        # Process action while holding lock
        result = toggle_like(user_id, post_id, action)
        return result
    finally:
        # Always release lock
        lock.release()
```

**4. Client-Side Debouncing**
```javascript
// Debounce rapid clicks
let debounceTimer = null;
let pendingAction = null;

function handleLikeToggle() {
  // Clear previous timer
  clearTimeout(debounceTimer);
  
  // Toggle local state immediately (optimistic UI update)
  const newState = !currentLikedState;
  updateUIImmediately(newState);
  
  // Store pending action
  pendingAction = newState ? "like" : "unlike";
  
  // Wait 300ms before sending to server
  debounceTimer = setTimeout(() => {
    sendToServer(pendingAction);
  }, 300);
}
```

**5. Idempotency**
```python
# Make all operations idempotent
def like_post(user_id, post_id):
    # Check current state
    already_liked = check_if_liked(user_id, post_id)
    
    if already_liked:
        # Already liked: no-op (idempotent)
        return {"status": "success", "message": "Already liked"}
    
    # Not liked: insert
    insert_like(user_id, post_id)
    increment_counter(post_id)
    
    return {"status": "success", "message": "Liked"}

def unlike_post(user_id, post_id):
    # Check current state
    already_liked = check_if_liked(user_id, post_id)
    
    if not already_liked:
        # Not liked: no-op (idempotent)
        return {"status": "success", "message": "Already not liked"}
    
    # Liked: delete
    delete_like(user_id, post_id)
    decrement_counter(post_id)
    
    return {"status": "success", "message": "Unliked"}
```

**Test Case:**
```python
# Simulate rapid clicks
def test_rapid_clicks():
    user_id = "user-123"
    post_id = "post-456"
    
    # Initial state: not liked
    assert not is_liked(user_id, post_id)
    assert get_like_count(post_id) == 0
    
    # Rapid actions (10 actions in 100ms)
    actions = ["like", "unlike", "like", "unlike", "like", "unlike", "like", "unlike", "like", "unlike"]
    
    threads = []
    for action in actions:
        thread = Thread(target=lambda: process_like_action(user_id, post_id, action))
        threads.append(thread)
        thread.start()
    
    # Wait for all to complete
    for thread in threads:
        thread.join()
    
    # Final state should be consistent
    final_liked = is_liked(user_id, post_id)
    final_count = get_like_count(post_id)
    
    # Either liked or not liked (consistent)
    assert final_liked in [True, False]
    
    # Counter matches state
    if final_liked:
        assert final_count == 1
    else:
        assert final_count == 0
    
    print("✓ Test passed: No race condition")
```

---

### Q14: What if a user likes a post, then deletes their account? How do you handle cascade deletions?

**Answer:**

**Scenario:**
```
1. User-123 likes 10,000 posts
2. User-123 deletes account
3. What happens to those 10,000 likes?
```

**Option 1: Immediate Cascade Delete (Not Recommended)**
```sql
-- Naive approach
DELETE FROM likes WHERE user_id = 'user-123';
-- Problem: Blocks for minutes, timeouts, database lock contention
```

**Option 2: Asynchronous Cascade Delete (Recommended)**
```python
# Step 1: Soft delete user (immediate)
def delete_user(user_id):
    cassandra.execute(
        "UPDATE users SET status = 'deleted', deleted_at = ? WHERE user_id = ?",
        [datetime.now(), user_id]
    )
    
    # Publish event to Kafka
    kafka.produce("user-deleted-events", {
        "user_id": user_id,
        "deleted_at": datetime.now()
    })
    
    return {"status": "success", "message": "User deletion initiated"}

# Step 2: Background cleanup (async)
def cleanup_deleted_user_likes(user_id):
    # Get all likes by this user (paginated)
    page_size = 1000
    page_state = None
    
    while True:
        results = cassandra.execute(
            "SELECT post_id FROM likes WHERE user_id = ? LIMIT ?",
            [user_id, page_size],
            paging_state=page_state
        )
        
        for row in results:
            # Delete like
            cassandra.execute(
                "DELETE FROM likes WHERE user_id = ? AND post_id = ?",
                [user_id, row.post_id]
            )
            
            # Decrement counter
            cassandra.execute(
                "UPDATE like_counts SET count = count - 1 WHERE post_id = ?",
                [row.post_id]
            )
            
            # Invalidate cache
            redis.delete(f"like:count:{row.post_id}")
            
            # Rate limit (don't overwhelm DB)
            time.sleep(0.01)  # 10ms between deletes
        
        # Check if more pages
        if results.has_more_pages:
            page_state = results.paging_state
        else:
            break
    
    # Log completion
    logger.info(f"Cleaned up likes for user {user_id}")

# Kafka consumer processes events
@kafka.consumer("user-deleted-events")
def handle_user_deleted(event):
    user_id = event["user_id"]
    cleanup_deleted_user_likes(user_id)
```

**Option 3: Lazy Deletion (Hybrid Approach)**
```python
# Don't delete immediately, filter on read

def get_likers_list(post_id):
    # Get all likers from DB
    likers = cassandra.execute(
        "SELECT user_id FROM likes WHERE post_id = ?",
        [post_id]
    )
    
    # Filter out deleted users
    active_likers = []
    for liker in likers:
        user = get_user(liker.user_id)
        if user and user.status == "active":
            active_likers.append(liker)
    
    return active_likers

# Background job: Clean up old deleted user likes (weekly)
def cleanup_old_deleted_likes():
    # Get users deleted > 30 days ago
    deleted_users = cassandra.execute(
        "SELECT user_id FROM users WHERE status = 'deleted' AND deleted_at < ?",
        [datetime.now() - timedelta(days=30)]
    )
    
    for user in deleted_users:
        cleanup_deleted_user_likes(user.user_id)
```

**Tombstone Management:**
```python
# Cassandra creates tombstones for deleted rows
# Too many tombstones = slow reads

# Monitor tombstone count
def check_tombstone_health():
    stats = cassandra.execute("SELECT * FROM system.compaction_history")
    
    for table in ["likes", "like_counts"]:
        tombstone_ratio = stats[table]["tombstone_ratio"]
        
        if tombstone_ratio > 0.2:  # More than 20% tombstones
            # Trigger manual compaction
            cassandra.nodetool("compact", table)
            logger.warning(f"High tombstone ratio in {table}: {tombstone_ratio}")

# Run weekly
schedule.every().week.do(check_tombstone_health)
```

**Cascade Delete Performance:**
```
Scenario: User has 10,000 likes

Option 1 (Immediate): 
- Time: 60 seconds (blocking)
- DB load: High (10,000 writes)
- User experience: Slow (waits for completion)

Option 2 (Async):
- Time: < 1 second (user response)
- DB load: Distributed over 10 minutes
- User experience: Fast (immediate confirmation)

Option 3 (Lazy):
- Time: < 1 second (user response)
- DB load: Minimal (eventually cleaned up)
- User experience: Fast (immediate confirmation)

Recommendation: Option 2 (Async) or Option 3 (Lazy + Periodic)
```

---

### Q15: How do you handle "unlike" operations? What if the user never liked the post?

**Answer:**

**Idempotent Unlike Operation:**

```python
def unlike_post(user_id, post_id):
    """
    Idempotent unlike operation.
    Returns success regardless of current state.
    """
    
    # Step 1: Check current state
    existing_like = cassandra.execute(
        "SELECT user_id FROM likes WHERE post_id = ? AND user_id = ?",
        [post_id, user_id]
    ).one()
    
    if not existing_like:
        # Not liked: Return success (idempotent)
        logger.info(f"User {user_id} tried to unlike post {post_id} (not liked)")
        
        return {
            "status": 200,
            "message": "Post not liked (no action needed)",
            "like_count": get_like_count(post_id),
            "user_liked": False
        }
    
    # Step 2: Delete like record
    cassandra.execute(
        "DELETE FROM likes WHERE post_id = ? AND user_id = ?",
        [post_id, user_id]
    )
    
    # Step 3: Decrement counter
    cassandra.execute(
        "UPDATE like_counts SET count = count - 1 WHERE post_id = ?",
        [post_id]
    )
    
    # Step 4: Update cache
    redis.decr(f"like:count:{post_id}")
    redis.setex(f"like:status:{user_id}:{post_id}", 3600, "0")
    
    # Step 5: Publish event
    kafka.produce("like-events", {
        "event_type": "unlike",
        "user_id": user_id,
        "post_id": post_id,
        "timestamp": datetime.now()
    })
    
    return {
        "status": 200,
        "message": "Successfully unliked",
        "like_count": get_like_count(post_id),
        "user_liked": False
    }
```

**Edge Cases:**

**Edge Case 1: Double Unlike**
```python
# User clicks unlike twice rapidly

Request 1: Unlike (post_id=123, user_id=456)
→ Deletes like record
→ Decrements counter
→ Returns success

Request 2: Unlike (post_id=123, user_id=456)  [100ms later]
→ No like record found
→ No decrement
→ Returns success (idempotent)

Result: Counter decremented only once ✓
```

**Edge Case 2: Unlike After Post Deleted**
```python
def unlike_post_safe(user_id, post_id):
    # Check if post exists
    post = get_post(post_id)
    
    if not post or post.status == "deleted":
        # Post deleted: Clean up orphaned like if exists
        cassandra.execute(
            "DELETE FROM likes WHERE post_id = ? AND user_id = ?",
            [post_id, user_id]
        )
        
        return {
            "status": 404,
            "error": "Post not found",
            "message": "Cannot unlike a deleted post"
        }
    
    # Post exists: Proceed with unlike
    return unlike_post(user_id, post_id)
```

**Edge Case 3: Unlike During Network Partition**
```python
# User unlikes in region A
# Network partition occurs
# User views post in region B (still shows liked)

Solution: Eventually consistent
- Region A processes unlike
- Replication to region B takes 5-10 seconds
- User temporarily sees "liked" state in region B
- Eventually converges to "unliked"

Acceptable trade-off for better performance
```

**Edge Case 4: Unlike with Zero Counter**
```python
def decrement_counter_safe(post_id):
    current_count = cassandra.execute(
        "SELECT count FROM like_counts WHERE post_id = ?",
        [post_id]
    ).one().count
    
    if current_count <= 0:
        # Counter already zero: Don't decrement (prevents negative)
        logger.warning(f"Counter for post {post_id} already zero, skipping decrement")
        
        # Fix counter (reconciliation)
        actual_count = cassandra.execute(
            "SELECT COUNT(*) FROM likes WHERE post_id = ?",
            [post_id]
        ).one().count
        
        cassandra.execute(
            "UPDATE like_counts SET count = ? WHERE post_id = ?",
            [actual_count, post_id]
        )
        
        return actual_count
    
    # Safe to decrement
    cassandra.execute(
        "UPDATE like_counts SET count = count - 1 WHERE post_id = ?",
        [post_id]
    )
    
    return current_count - 1
```

**Testing Unlike Idempotency:**
```python
def test_unlike_idempotency():
    user_id = "user-123"
    post_id = "post-456"
    
    # Initial state: liked
    like_post(user_id, post_id)
    assert is_liked(user_id, post_id) == True
    assert get_like_count(post_id) == 1
    
    # Unlike once
    response1 = unlike_post(user_id, post_id)
    assert response1["status"] == 200
    assert is_liked(user_id, post_id) == False
    assert get_like_count(post_id) == 0
    
    # Unlike again (should be no-op)
    response2 = unlike_post(user_id, post_id)
    assert response2["status"] == 200  # Still success
    assert is_liked(user_id, post_id) == False
    assert get_like_count(post_id) == 0  # Count unchanged
    
    # Unlike third time (still no-op)
    response3 = unlike_post(user_id, post_id)
    assert response3["status"] == 200
    assert get_like_count(post_id) == 0  # Count still zero (not negative)
    
    print("✓ Unlike idempotency test passed")
```

---

### Q16: How do you maintain consistency between the likes table and the counter table?

**Answer:**

**Challenge:**
```
Two tables must stay in sync:
1. likes table (individual records)
2. like_counts table (aggregated counter)

Problem: They're updated separately (not atomic)
Risk: Divergence (counter says 100, but only 98 records exist)
```

**Solution: Multi-Phase Consistency**

**Phase 1: Write-Time Consistency (Best Effort)**
```python
def like_post_with_consistency(user_id, post_id):
    # Step 1: Insert like record
    try:
        cassandra.execute(
            "INSERT INTO likes (post_id, user_id, created_at) VALUES (?, ?, ?)",
            [post_id, user_id, datetime.now()]
        )
    except Exception as e:
        logger.error(f"Failed to insert like: {e}")
        return {"status": 500, "error": "Write failed"}
    
    # Step 2: Increment counter
    try:
        cassandra.execute(
            "UPDATE like_counts SET count = count + 1 WHERE post_id = ?",
            [post_id]
        )
    except Exception as e:
        # Counter update failed, but like record exists
        # Write to reconciliation queue
        kafka.produce("counter-reconciliation-queue", {
            "post_id": post_id,
            "action": "increment",
            "timestamp": datetime.now()
        })
        
        logger.error(f"Failed to update counter, queued for reconciliation: {e}")
    
    # Step 3: Update cache (best effort, non-critical)
    try:
        redis.incr(f"like:count:{post_id}")
    except:
        pass  # Cache failure is non-critical
    
    return {"status": 200, "like_count": get_like_count(post_id)}
```

**Phase 2: Periodic Reconciliation (Eventually Consistent)**
```python
# Hourly reconciliation job
def reconcile_counters():
    # Get posts with recent activity (last hour)
    recent_posts = cassandra.execute(
        "SELECT DISTINCT post_id FROM likes WHERE created_at > ?",
        [datetime.now() - timedelta(hours=1)]
    )
    
    for post in recent_posts:
        # Count actual likes
        actual_count = cassandra.execute(
            "SELECT COUNT(*) FROM likes WHERE post_id = ?",
            [post.post_id]
        ).one().count
        
        # Get counter value
        counter_value = cassandra.execute(
            "SELECT count FROM like_counts WHERE post_id = ?",
            [post.post_id]
        ).one()
        
        if counter_value is None:
            # Counter doesn't exist: create it
            cassandra.execute(
                "UPDATE like_counts SET count = ? WHERE post_id = ?",
                [actual_count, post.post_id]
            )
            logger.info(f"Created missing counter for post {post.post_id}: {actual_count}")
        elif counter_value.count != actual_count:
            # Mismatch: fix it
            drift = abs(counter_value.count - actual_count)
            
            cassandra.execute(
                "UPDATE like_counts SET count = ? WHERE post_id = ?",
                [actual_count, post.post_id]
            )
            
            logger.warning(f"Fixed counter drift for post {post.post_id}: {counter_value.count} → {actual_count} (drift: {drift})")
            
            # Alert if large drift
            if drift > 10:
                pagerduty.alert(f"Large counter drift detected: post {post.post_id}, drift: {drift}")

schedule.every().hour.do(reconcile_counters)
```

**Phase 3: On-Demand Verification**
```python
def get_like_count_verified(post_id, verify=False):
    """
    Get like count with optional verification.
    
    verify=False: Fast (use counter, may be slightly stale)
    verify=True: Slow (COUNT query, guaranteed accurate)
    """
    
    if not verify:
        # Fast path: Use counter
        count = cassandra.execute(
            "SELECT count FROM like_counts WHERE post_id = ?",
            [post_id]
        ).one()
        
        return count.count if count else 0
    
    # Slow path: Verify with COUNT query
    actual_count = cassandra.execute(
        "SELECT COUNT(*) FROM likes WHERE post_id = ?",
        [post_id]
    ).one().count
    
    counter_value = cassandra.execute(
        "SELECT count FROM like_counts WHERE post_id = ?",
        [post_id]
    ).one()
    
    if counter_value and counter_value.count != actual_count:
        # Mismatch detected: fix immediately
        cassandra.execute(
            "UPDATE like_counts SET count = ? WHERE post_id = ?",
            [actual_count, post_id]
        )
        
        logger.warning(f"On-demand fix: post {post_id}, counter {counter_value.count} → {actual_count}")
    
    return actual_count
```

**Phase 4: Kafka-Based Reconciliation (Real-Time Catchup)**
```python
# Process failed counter updates from queue
@kafka.consumer("counter-reconciliation-queue")
def process_reconciliation_event(event):
    post_id = event["post_id"]
    action = event["action"]  # "increment" or "decrement"
    
    # Verify if action still needed
    actual_count = cassandra.execute(
        "SELECT COUNT(*) FROM likes WHERE post_id = ?",
        [post_id]
    ).one().count
    
    counter_value = cassandra.execute(
        "SELECT count FROM like_counts WHERE post_id = ?",
        [post_id]
    ).one()
    
    if counter_value is None or counter_value.count != actual_count:
        # Fix counter
        cassandra.execute(
            "UPDATE like_counts SET count = ? WHERE post_id = ?",
            [actual_count, post_id]
        )
        
        logger.info(f"Reconciled counter for post {post_id}: {counter_value.count if counter_value else 0} → {actual_count}")
```

**Consistency Guarantees:**

```
Scenario 1: Both writes succeed
- likes table: ✓ inserted
- counter table: ✓ incremented
- Result: Consistent

Scenario 2: Like inserted, counter fails
- likes table: ✓ inserted
- counter table: ✗ failed
- Queue: ✓ reconciliation event
- Result: Eventually consistent (fixed within 1 hour, or sooner)

Scenario 3: Like fails, counter succeeds
- likes table: ✗ failed
- counter table: ✓ incremented (orphaned)
- Reconciliation: Detects extra count, decrements
- Result: Eventually consistent

Scenario 4: Both writes fail
- likes table: ✗ failed
- counter table: ✗ failed
- Result: Consistent (no change)
```

**Monitoring:**
```python
# Track consistency metrics
def monitor_consistency():
    sample_size = 1000
    sample_posts = get_random_posts(sample_size)
    
    mismatches = 0
    total_drift = 0
    
    for post in sample_posts:
        actual = count_likes(post.post_id)
        counter = get_counter_value(post.post_id)
        
        if actual != counter:
            mismatches += 1
            total_drift += abs(actual - counter)
    
    mismatch_rate = (mismatches / sample_size) * 100
    average_drift = total_drift / mismatches if mismatches > 0 else 0
    
    metrics.gauge("consistency.mismatch_rate", mismatch_rate)
    metrics.gauge("consistency.average_drift", average_drift)
    
    # Alert if mismatch rate > 1%
    if mismatch_rate > 1:
        pagerduty.alert(f"High counter mismatch rate: {mismatch_rate}%")

schedule.every(15).minutes.do(monitor_consistency)
```

---

### Q17: How do you handle likes on deleted posts?

**Answer:**

**Scenario:**
```
1. User tries to like a post
2. Post has been deleted
3. What happens?
```

**Solution: Multi-Layer Checks**

**Check 1: API Layer (Fast Fail)**
```python
def like_post_with_validation(user_id, post_id):
    # Check if post exists (cache first)
    post = get_post_from_cache(post_id)
    
    if not post:
        # Cache miss: check DB
        post = cassandra.execute(
            "SELECT post_id, status FROM posts WHERE post_id = ?",
            [post_id]
        ).one()
    
    if not post:
        return {
            "status": 404,
            "error": "POST_NOT_FOUND",
            "message": "This post does not exist"
        }
    
    if post.status == "deleted":
        return {
            "status": 410,  # HTTP 410 Gone
            "error": "POST_DELETED",
            "message": "This post has been deleted"
        }
    
    # Post exists: proceed with like
    return process_like(user_id, post_id)
```

**Check 2: Database Constraint (Safety Net)**
```sql
-- Foreign key constraint (if supported by DB)
CREATE TABLE likes (
    post_id UUID,
    user_id UUID,
    created_at TIMESTAMP,
    PRIMARY KEY (post_id, user_id),
    FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
);

-- If post deleted → automatically delete all likes
```

**Cassandra Alternative (No Foreign Keys):**
```python
# Background job to clean up orphaned likes
def cleanup_orphaned_likes():
    # Get all liked post IDs
    liked_posts = cassandra.execute(
        "SELECT DISTINCT post_id FROM likes"
    )
    
    for post in liked_posts:
        # Check if post exists
        post_exists = cassandra.execute(
            "SELECT post_id FROM posts WHERE post_id = ?",
            [post.post_id]
        ).one()
        
        if not post_exists:
            # Post deleted: clean up likes
            cassandra.execute(
                "DELETE FROM likes WHERE post_id = ?",
                [post.post_id]
            )
            
            # Delete counter
            cassandra.execute(
                "DELETE FROM like_counts WHERE post_id = ?",
                [post.post_id]
            )
            
            # Invalidate cache
            redis.delete(f"like:count:{post.post_id}")
            
            logger.info(f"Cleaned up orphaned likes for deleted post {post.post_id}")

# Run daily
schedule.every().day.at("02:00").do(cleanup_orphaned_likes)
```

**Check 3: Cascade Delete on Post Deletion**
```python
def delete_post(post_id):
    # Step 1: Soft delete post (immediate)
    cassandra.execute(
        "UPDATE posts SET status = 'deleted', deleted_at = ? WHERE post_id = ?",
        [datetime.now(), post_id]
    )
    
    # Step 2: Publish event for async cleanup
    kafka.produce("post-deleted-events", {
        "post_id": post_id,
        "deleted_at": datetime.now()
    })
    
    return {"status": 200, "message": "Post deleted"}

# Kafka consumer handles cascade deletion
@kafka.consumer("post-deleted-events")
def handle_post_deleted(event):
    post_id = event["post_id"]
    
    # Delete all likes (paginated)
    page_size = 1000
    page_state = None
    total_deleted = 0
    
    while True:
        results = cassandra.execute(
            "SELECT user_id FROM likes WHERE post_id = ? LIMIT ?",
            [post_id, page_size],
            paging_state=page_state
        )
        
        for row in results:
            cassandra.execute(
                "DELETE FROM likes WHERE post_id = ? AND user_id = ?",
                [post_id, row.user_id]
            )
            total_deleted += 1
        
        if results.has_more_pages:
            page_state = results.paging_state
        else:
            break
    
    # Delete counter
    cassandra.execute(
        "DELETE FROM like_counts WHERE post_id = ?",
        [post_id]
    )
    
    # Invalidate cache
    redis.delete(f"like:count:{post_id}")
    redis.delete(f"like:likers:{post_id}")
    
    logger.info(f"Cascade deleted {total_deleted} likes for post {post_id}")
```

**Edge Case: Concurrent Delete and Like**
```
Timeline:
T0: User A clicks like on post-123
T1: User B deletes post-123
T2: Like request reaches server
T3: Like processed (race condition!)

Result: Like inserted on deleted post (orphan)

Solution: Check post status in transaction
```

```python
def like_post_atomic(user_id, post_id):
    # Batch: Check post + insert like (atomic)
    batch = cassandra.batch()
    
    # Check post exists and not deleted
    post = cassandra.execute(
        "SELECT status FROM posts WHERE post_id = ?",
        [post_id]
    ).one()
    
    if not post or post.status == "deleted":
        return {"status": 410, "error": "Post deleted"}
    
    # Insert like (within same batch)
    batch.add(
        "INSERT INTO likes (post_id, user_id, created_at) VALUES (?, ?, ?)",
        [post_id, user_id, datetime.now()]
    )
    
    batch.add(
        "UPDATE like_counts SET count = count + 1 WHERE post_id = ?",
        [post_id]
    )
    
    try:
        batch.execute()
        return {"status": 200, "message": "Liked"}
    except Exception as e:
        return {"status": 500, "error": str(e)}
```

---

### Q18: How do you prevent bots from inflating like counts?

**Answer:**

**Multi-Layer Bot Detection:**

**Layer 1: Rate Limiting**
```python
# Redis-based rate limiting
def check_rate_limit(user_id):
    key = f"rate_limit:like:{user_id}"
    
    # Increment counter
    count = redis.incr(key)
    
    # Set expiry on first increment
    if count == 1:
        redis.expire(key, 60)  # 60 seconds window
    
    # Limits
    if count > 100:  # Max 100 likes per minute
        return {
            "allowed": False,
            "error": "RATE_LIMIT_EXCEEDED",
            "retry_after": redis.ttl(key)
        }
    
    return {"allowed": True}
```

**Layer 2: Behavioral Analysis**
```python
def analyze_like_behavior(user_id):
    # Get user's recent likes
    recent_likes = cassandra.execute(
        """
        SELECT post_id, created_at 
        FROM likes 
        WHERE user_id = ? 
        AND created_at > ?
        ORDER BY created_at DESC
        LIMIT 100
        """,
        [user_id, datetime.now() - timedelta(hours=1)]
    )
    
    # Calculate metrics
    like_count = len(recent_likes)
    
    if like_count < 2:
        return {"risk_score": 0.0, "action": "allow"}
    
    # Time intervals between likes
    intervals = []
    for i in range(len(recent_likes) - 1):
        interval = (recent_likes[i].created_at - recent_likes[i+1].created_at).total_seconds()
        intervals.append(interval)
    
    # Calculate statistics
    avg_interval = sum(intervals) / len(intervals)
    std_interval = calculate_std(intervals)
    
    # Bot indicators
    risk_score = 0.0
    
    # Too fast (< 1 second between likes)
    if avg_interval < 1.0:
        risk_score += 0.5
    
    # Too consistent (low variance = bot-like)
    if std_interval < 0.1:
        risk_score += 0.3
    
    # Too many likes in short time
    if like_count > 50:
        risk_score += 0.2
    
    # Determine action
    if risk_score > 0.8:
        return {"risk_score": risk_score, "action": "block"}
    elif risk_score > 0.5:
        return {"risk_score": risk_score, "action": "challenge"}  # CAPTCHA
    else:
        return {"risk_score": risk_score, "action": "allow"}
```

**Layer 3: Device Fingerprinting**
```python
def check_device_fingerprint(request):
    # Extract device info
    fingerprint = {
        "ip": request.ip,
        "user_agent": request.headers["User-Agent"],
        "screen_resolution": request.headers.get("X-Screen-Resolution"),
        "timezone": request.headers.get("X-Timezone"),
        "language": request.headers.get("Accept-Language")
    }
    
    # Hash fingerprint
    fingerprint_hash = hash(json.dumps(fingerprint, sort_keys=True))
    
    # Check if fingerprint seen before
    key = f"device_fingerprint:{fingerprint_hash}"
    device_data = redis.get(key)
    
    if not device_data:
        # New device: lower trust
        redis.setex(key, 86400, json.dumps({
            "first_seen": datetime.now().isoformat(),
            "like_count": 1
        }))
        return {"trust_level": 0.3}
    
    device = json.loads(device_data)
    device["like_count"] += 1
    
    # Check for suspicious patterns
    # Multiple accounts from same device (account farming)
    accounts_from_device = redis.scard(f"device_accounts:{fingerprint_hash}")
    
    if accounts_from_device > 10:
        return {"trust_level": 0.1, "reason": "Multiple accounts from device"}
    
    # Too many likes from this device
    if device["like_count"] > 1000:
        return {"trust_level": 0.2, "reason": "High like count from device"}
    
    # Normal device
    redis.setex(key, 86400, json.dumps(device))
    return {"trust_level": 0.8}
```

**Layer 4: CAPTCHA Challenge**
```python
def like_post_with_bot_detection(user_id, post_id, request):
    # Step 1: Rate limiting
    rate_limit = check_rate_limit(user_id)
    if not rate_limit["allowed"]:
        return {"status": 429, "error": rate_limit["error"]}
    
    # Step 2: Behavioral analysis
    behavior = analyze_like_behavior(user_id)
    
    # Step 3: Device fingerprinting
    device_trust = check_device_fingerprint(request)
    
    # Step 4: Calculate final risk score
    risk_score = (
        behavior["risk_score"] * 0.6 +  # 60% weight
        (1 - device_trust["trust_level"]) * 0.4  # 40% weight
    )
    
    # Step 5: Take action based on risk
    if risk_score > 0.8:
        # High risk: Block
        logger.warning(f"Blocked suspicious like from user {user_id}, risk: {risk_score}")
        return {
            "status": 403,
            "error": "SUSPICIOUS_ACTIVITY",
            "message": "Your account has been flagged for suspicious activity"
        }
    
    elif risk_score > 0.5:
        # Medium risk: Challenge with CAPTCHA
        captcha_token = generate_captcha(user_id, post_id)
        
        return {
            "status": 449,  # Retry With (Microsoft extension)
            "error": "CAPTCHA_REQUIRED",
            "message": "Please complete CAPTCHA verification",
            "captcha_token": captcha_token
        }
    
    else:
        # Low risk: Allow
        return process_like(user_id, post_id)
```

**Layer 5: Machine Learning Model**
```python
# Features for ML model
def extract_features(user_id, request):
    features = {
        # User features
        "account_age_days": get_account_age(user_id),
        "total_likes_given": get_total_likes_given(user_id),
        "total_posts_created": get_total_posts(user_id),
        "followers_count": get_followers_count(user_id),
        "following_count": get_following_count(user_id),
        
        # Behavioral features
        "likes_last_hour": get_likes_count(user_id, hours=1),
        "likes_last_day": get_likes_count(user_id, hours=24),
        "avg_like_interval": get_avg_like_interval(user_id),
        "std_like_interval": get_std_like_interval(user_id),
        
        # Device features
        "device_age_days": get_device_age(request),
        "accounts_per_device": get_accounts_per_device(request),
        "likes_per_device": get_likes_per_device(request),
        
        # Network features
        "ip_reputation": get_ip_reputation(request.ip),
        "vpn_probability": check_vpn(request.ip),
        
        # Timing features
        "hour_of_day": datetime.now().hour,
        "day_of_week": datetime.now().weekday()
    }
    
    return features

# ML model prediction
def predict_bot_probability(user_id, request):
    features = extract_features(user_id, request)
    
    # Load pre-trained model (e.g., Random Forest, XGBoost)
    model = load_model("bot_detection_model_v3.pkl")
    
    # Predict
    bot_probability = model.predict_proba([features])[0][1]  # Probability of class 1 (bot)
    
    return bot_probability

# Integration
def like_post_with_ml(user_id, post_id, request):
    bot_prob = predict_bot_probability(user_id, request)
    
    if bot_prob > 0.9:
        # Very likely bot: Block + flag for review
        flag_for_review(user_id, "High bot probability", bot_prob)
        return {"status": 403, "error": "Account suspended"}
    
    elif bot_prob > 0.7:
        # Likely bot: Challenge
        return {"status": 449, "error": "CAPTCHA_REQUIRED"}
    
    else:
        # Likely human: Allow
        return process_like(user_id, post_id)
```

**Enforcement Actions:**
```python
# Progressive enforcement
def enforce_bot_policy(user_id, bot_probability):
    key = f"bot_violations:{user_id}"
    violations = redis.incr(key)
    redis.expire(key, 86400)  # 24 hour window
    
    if violations == 1:
        # First violation: Warning
        send_warning(user_id)
        return "warning"
    
    elif violations <= 3:
        # Multiple violations: Temporary restriction
        redis.setex(f"restricted:{user_id}", 3600, "1")  # 1 hour restriction
        return "restricted"
    
    elif violations <= 10:
        # Repeated violations: Shadow ban (likes don't count)
        redis.setex(f"shadowban:{user_id}", 86400, "1")  # 24 hour shadow ban
        return "shadowban"
    
    else:
        # Persistent violations: Account suspension
        suspend_account(user_id, reason="Automated abuse")
        return "suspended"
```

---

(Continuing with more categories...)

Due to length limitations, I'll create a separate file with the remaining categories. Let me know if you'd like me to continue with the rest!

**Remaining Categories:**
- Category 3: Monitoring & Observability (5 questions)
- Category 4: Database & Storage (8 questions)
- Category 5: Security & Privacy (7 questions)
- Category 6: Cost Optimization (5 questions)
- Category 7: Advanced Topics (6 questions)

Would you like me to create those as well?
