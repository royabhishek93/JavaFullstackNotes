# Cassandra Deep Dive for Beginners - Instagram Likes System

## Table of Contents
1. [Why Choose Cassandra Over PostgreSQL?](#why-choose-cassandra-over-postgresql)
2. [What is Throughput?](#what-is-throughput)
3. [How Cassandra Works Internally](#how-cassandra-works-internally)
4. [LSM Tree vs B-Tree (Simple Examples)](#lsm-tree-vs-b-tree)
5. [Write Sharding Explained](#write-sharding-explained)
6. [MongoDB vs Cassandra](#mongodb-vs-cassandra)
7. [Advanced Interview Questions](#advanced-interview-questions)

---

## Why Choose Cassandra Over PostgreSQL?

### Real-World Scenario: Instagram Likes

```
Instagram Scale:
- 500 million users liking posts every day
- 5 billion likes per day
- 58,000 likes per SECOND on average
- 200,000 likes per second during PEAK times
```

### The Problem with PostgreSQL

Let's say **Cristiano Ronaldo** posts a photo. He has **600 million followers**.

```
┌─────────────────────────────────────────────────────────────┐
│              POSTGRES APPROACH (Traditional DB)              │
└─────────────────────────────────────────────────────────────┘

Ronaldo's Post ID: post_123

Likes Table in Postgres:
┌────────────┬─────────────┬──────────────────────┐
│  post_id   │  user_id    │    created_at        │
├────────────┼─────────────┼──────────────────────┤
│  post_123  │  user_001   │  2026-04-16 10:00:00 │
│  post_123  │  user_002   │  2026-04-16 10:00:01 │
│  post_123  │  user_003   │  2026-04-16 10:00:02 │
│    ...     │    ...      │        ...           │
└────────────┴─────────────┴──────────────────────┘

Problem: When 100,000 people like at SAME SECOND
↓
ALL WRITES GO TO SAME ROW (post_123)
↓
LOCK CONTENTION (everyone waiting in line)
↓
SYSTEM SLOWS DOWN ❌
```

**What Happens in PostgreSQL:**
```
User 1 tries to like: LOCK acquired → Write → UNLOCK (10ms)
User 2 tries to like: WAITING for lock... ⏳
User 3 tries to like: WAITING for lock... ⏳
User 4 tries to like: WAITING for lock... ⏳
...
User 100,000: Still waiting after 16 minutes! 😱

Result: Database CRASHES 💥
```

---

### The Cassandra Solution

```
┌─────────────────────────────────────────────────────────────┐
│              CASSANDRA APPROACH (Distributed DB)             │
└─────────────────────────────────────────────────────────────┘

Same scenario: 100,000 people like Ronaldo's post

Cassandra Cluster:
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  Node 1  │  │  Node 2  │  │  Node 3  │  │  Node 4  │
│ (25K     │  │ (25K     │  │ (25K     │  │ (25K     │
│  writes) │  │  writes) │  │  writes) │  │  writes) │
└──────────┘  └──────────┘  └──────────┘  └──────────┘

All writing SIMULTANEOUSLY (no locks!) ✅
Result: 100,000 writes complete in 2 SECONDS
```

**Key Differences:**

| Feature | PostgreSQL | Cassandra |
|---------|-----------|-----------|
| **Write Speed** | Slow (locks required) | Fast (no locks) |
| **Scaling** | Vertical (bigger machine) | Horizontal (more machines) |
| **Hot Spot Problem** | YES (single row bottleneck) | NO (distributed) |
| **Best For** | Complex queries, JOINs | Simple queries, high writes |
| **Cost at Scale** | Expensive (need huge machine) | Cheaper (many small machines) |

---

## What is Throughput?

### Throughput = How many operations per second

Think of it like a **highway**:

```
┌─────────────────────────────────────────────────────────────┐
│                    HIGHWAY ANALOGY                           │
└─────────────────────────────────────────────────────────────┘

Low Throughput Highway (PostgreSQL):
═══════════════════════════════════════════════
🚗 ← Single lane, cars wait in line
═══════════════════════════════════════════════
Throughput: 1,000 cars/hour

High Throughput Highway (Cassandra):
═══════════════════════════════════════════════
🚗🚗🚗 ← 10 lanes, cars go simultaneously
═══════════════════════════════════════════════
Throughput: 50,000 cars/hour
```

### Instagram Likes Throughput Requirements:

```
Average: 58,000 likes per second
Peak: 200,000 likes per second

PostgreSQL can handle: ~5,000 writes/second (1 node)
Cassandra can handle: 500,000 writes/second (10 nodes)

Cassandra wins! ✅
```

---

## How Cassandra Works Internally

### Simple Example: Adding a Like

Let's see what happens when **User Alice** likes **Post 123**:

```
┌─────────────────────────────────────────────────────────────┐
│              STEP-BY-STEP: CASSANDRA WRITE                   │
└─────────────────────────────────────────────────────────────┘

Request: INSERT INTO likes (post_id, user_id, created_at) 
         VALUES ('post_123', 'alice', '2026-04-16 10:00:00');

Step 1: Write to Commit Log (WAL - Write Ahead Log)
┌─────────────────────────────────────────┐
│  Commit Log (on disk, sequential)       │
│  ─────────────────────────────────────  │
│  [Log Entry]: post_123, alice, 10:00:00 │  ← Appended
└─────────────────────────────────────────┘
Time: 1ms (very fast because it's append-only!)

Step 2: Write to MemTable (in memory)
┌─────────────────────────────────────────┐
│  MemTable (RAM - sorted)                │
│  ─────────────────────────────────────  │
│  post_123 → alice → 10:00:00            │  ← Added
└─────────────────────────────────────────┘
Time: <1ms (memory is super fast!)

Step 3: Acknowledge to User
Response: "Like saved!" ✅
Total Time: ~2ms

Step 4: Background Flush (later, async)
When MemTable gets full (e.g., 128 MB), flush to disk
┌─────────────────────────────────────────┐
│  SSTable (disk file, immutable)         │
│  ─────────────────────────────────────  │
│  post_123 → alice → 10:00:00            │
│  post_456 → bob → 10:00:05              │
│  ...                                    │
└─────────────────────────────────────────┘

Important: User doesn't wait for this! Already got response.
```

**Why is this FAST?**
1. ✅ Write goes to memory first (MemTable)
2. ✅ Commit log is append-only (no seeking on disk)
3. ✅ No locks needed
4. ✅ User gets response immediately (~2ms)

---

## LSM Tree vs B-Tree (Simple Examples)

### What is a B-Tree? (Used by PostgreSQL)

Think of a **B-Tree** like a **filing cabinet**:

```
┌─────────────────────────────────────────────────────────────┐
│                  B-TREE (PostgreSQL)                         │
└─────────────────────────────────────────────────────────────┘

Filing Cabinet Analogy:
┌──────────────────────────────────────────┐
│         DRAWER A-M                       │  ← Organized drawers
│  ┌─────┬─────┬─────┬─────┐              │
│  │ A-C │ D-F │ G-I │ J-M │              │
│  └─────┴─────┴─────┴─────┘              │
├──────────────────────────────────────────┤
│         DRAWER N-Z                       │
│  ┌─────┬─────┬─────┬─────┐              │
│  │ N-P │ Q-S │ T-V │ W-Z │              │
│  └─────┴─────┴─────┴─────┘              │
└──────────────────────────────────────────┘

Adding a new file "David":
1. Open correct drawer (D-F)
2. Find correct position (alphabetically)
3. SHIFT all papers to make space  ← SLOW! ❌
4. Insert "David"
5. Close drawer

Problem: If drawer is full, need to REORGANIZE entire cabinet! 😰
```

**B-Tree Write Operation:**
```
Write "Like from Alice":
1. Navigate tree (read multiple nodes) → 3 disk reads
2. Find correct leaf node
3. Check if node is full
4. If full, SPLIT node (expensive!)
5. Update parent node
6. Lock row to prevent conflicts ← BOTTLENECK!
7. Write to disk
8. Unlock row

Total Time: 10-20ms (slow because of steps 1, 4, 6)
```

---

### What is an LSM Tree? (Used by Cassandra)

Think of an **LSM Tree** like **inbox on your desk**:

```
┌─────────────────────────────────────────────────────────────┐
│                  LSM TREE (Cassandra)                        │
└─────────────────────────────────────────────────────────────┘

Inbox Analogy:
┌──────────────────────────────────────────┐
│  NEW MAIL (Today)                        │  ← Just drop on top!
│  ──────────────────────────────           │
│  📧 Letter from Alice (10:00)            │
│  📧 Letter from Bob (09:55)              │
│  📧 Letter from Charlie (09:50)          │
├──────────────────────────────────────────┤
│  OLD MAIL (Last Week) - Sorted           │  ← Organized later
│  ──────────────────────────────           │
│  📁 Folder A-M                           │
│  📁 Folder N-Z                           │
└──────────────────────────────────────────┘

Adding a new letter "David":
1. Just DROP it on top of inbox  ← SUPER FAST! ✅
2. Keep working!

Later (when you have time):
- Sort inbox
- Move to organized folders
- You don't stop for this!
```

**LSM Tree Write Operation:**
```
Write "Like from Alice":
1. Append to commit log (sequential write) → 1ms
2. Add to MemTable (in memory) → <1ms
3. Return SUCCESS! ✅

Total Time: ~2ms (FAST!)

Background work (you don't wait):
4. When MemTable full, flush to SSTable
5. Periodically merge SSTables (compaction)
```

---

### Visual Comparison

```
┌─────────────────────────────────────────────────────────────┐
│                    WRITE PERFORMANCE                         │
└─────────────────────────────────────────────────────────────┘

B-Tree (PostgreSQL):
Timeline: ├─read─┼─seek─┼─lock─┼─split─┼─write─┼─unlock─┤
Time:     0ms    3ms    6ms    10ms    15ms    20ms
Result: 20ms per write ❌

LSM Tree (Cassandra):
Timeline: ├─append─┼─memory─┤
Time:     0ms      1ms      2ms
Result: 2ms per write ✅

Speed Difference: LSM is 10x FASTER!
```

---

### What is WAL (Write-Ahead Log)?

**WAL = Safety backup before actual write**

```
┌─────────────────────────────────────────────────────────────┐
│               WAL (Write-Ahead Log) Analogy                  │
└─────────────────────────────────────────────────────────────┘

Think of it like a DIARY:

You're painting a house:
1. Write in diary: "I will paint wall blue" ← WAL
2. Actually paint the wall blue          ← Actual work

Why?
If power goes out after step 1, you can read diary and continue!
If power goes out before step 1, you don't know what you were doing!

Same in Cassandra:
1. Write to commit log: "Alice liked post_123" ← Crash-safe!
2. Write to MemTable: Add like to memory
3. Eventually flush to SSTable

If crash happens:
- Commit log survives (on disk)
- Replay commit log → recover data ✅
```

---

## Write Sharding Explained

### The Hot Spot Problem

```
┌─────────────────────────────────────────────────────────────┐
│                    HOT SPOT PROBLEM                          │
└─────────────────────────────────────────────────────────────┘

Scenario: Cristiano Ronaldo posts → 1 MILLION likes in 1 minute

Without Sharding:
┌────────────────────────────────────────┐
│  Like Counter Table                    │
├────────────────────────────────────────┤
│  post_id    │  count                   │
├─────────────┼──────────────────────────┤
│  post_123   │  1,000,000  ← HOT SPOT!  │
└─────────────┴──────────────────────────┘
              ↑
              All 1M writes go here!
              Database row becomes bottleneck ❌

Problem:
- Single row gets hammered
- Disk contention
- Memory contention
- System slows down
```

---

### Solution: Write Sharding

**Sharding = Splitting data across multiple "buckets"**

```
┌─────────────────────────────────────────────────────────────┐
│                    WITH SHARDING                             │
└─────────────────────────────────────────────────────────────┘

Instead of 1 counter, use 100 sharded counters:

┌──────────────────────────────────────────────────────────┐
│  Sharded Counter Table                                   │
├──────────────────────────────────────────────────────────┤
│  post_id    │  shard_id  │  count                        │
├─────────────┼────────────┼───────────────────────────────┤
│  post_123   │  0         │  10,000   ← 1% of traffic     │
│  post_123   │  1         │  10,100   ← 1% of traffic     │
│  post_123   │  2         │  9,800    ← 1% of traffic     │
│  post_123   │  3         │  10,200   ← 1% of traffic     │
│     ...     │  ...       │  ...                          │
│  post_123   │  99        │  9,900    ← 1% of traffic     │
└─────────────┴────────────┴───────────────────────────────┘
                ↑
                Each shard handles 1% of writes!
                Load distributed ✅

Total likes for post_123:
= sum(shard_0 to shard_99)
= 10,000 + 10,100 + 9,800 + ... + 9,900
= 1,000,000
```

---

### How Sharding Works: Step-by-Step Example

**Scenario: 5 users like Ronaldo's post at the same time**

```
┌─────────────────────────────────────────────────────────────┐
│              SHARDING EXAMPLE (5 shards)                     │
└─────────────────────────────────────────────────────────────┘

Users:
- Alice (user_id: 12345)
- Bob (user_id: 67890)
- Charlie (user_id: 11111)
- Diana (user_id: 99999)
- Eve (user_id: 55555)

Post: post_123

Step 1: Calculate shard for each user
─────────────────────────────────────
Shard = hash(user_id) % 5

Alice:   hash(12345) % 5 = 0 → Shard 0
Bob:     hash(67890) % 5 = 2 → Shard 2
Charlie: hash(11111) % 5 = 1 → Shard 1
Diana:   hash(99999) % 5 = 4 → Shard 4
Eve:     hash(55555) % 5 = 3 → Shard 3

Step 2: Write to respective shards (PARALLEL!)
─────────────────────────────────────────────

Shard 0: UPDATE SET count = count + 1 WHERE post_id='post_123' AND shard=0
Shard 1: UPDATE SET count = count + 1 WHERE post_id='post_123' AND shard=1
Shard 2: UPDATE SET count = count + 1 WHERE post_id='post_123' AND shard=2
Shard 3: UPDATE SET count = count + 1 WHERE post_id='post_123' AND shard=3
Shard 4: UPDATE SET count = count + 1 WHERE post_id='post_123' AND shard=4

All 5 writes happen SIMULTANEOUSLY! ✅
No contention, no waiting!

Step 3: Read total count
─────────────────────────
SELECT SUM(count) FROM like_counts WHERE post_id = 'post_123'

Result:
Shard 0: 234,567
Shard 1: 232,890
Shard 2: 235,123
Shard 3: 233,456
Shard 4: 234,789
─────────────────
Total:  1,170,825 likes
```

---

### Code Example: Write Sharding

```python
# Configuration
NUM_SHARDS = 100  # For normal posts
NUM_SHARDS_VIRAL = 1000  # For viral posts

def like_post(user_id, post_id):
    """
    Like a post with write sharding.
    """
    
    # Step 1: Determine number of shards
    if is_viral_post(post_id):
        num_shards = NUM_SHARDS_VIRAL
    else:
        num_shards = NUM_SHARDS
    
    # Step 2: Calculate shard ID
    shard_id = calculate_shard(user_id, num_shards)
    
    # Step 3: Insert like record (normal table, not sharded)
    cassandra.execute(
        """
        INSERT INTO likes (post_id, user_id, created_at)
        VALUES (?, ?, ?)
        """,
        [post_id, user_id, datetime.now()]
    )
    
    # Step 4: Increment sharded counter
    cassandra.execute(
        """
        UPDATE like_counts_sharded
        SET count = count + 1
        WHERE post_id = ? AND shard_id = ?
        """,
        [post_id, shard_id]
    )
    
    # Step 5: Update cache (optional)
    invalidate_cache(post_id)
    
    return {"status": "success", "shard": shard_id}

def calculate_shard(user_id, num_shards):
    """
    Calculate which shard to write to.
    Uses consistent hashing.
    """
    # Convert user_id to integer hash
    user_hash = hashlib.md5(user_id.encode()).hexdigest()
    user_hash_int = int(user_hash, 16)
    
    # Modulo to get shard
    shard_id = user_hash_int % num_shards
    
    return shard_id

def get_like_count(post_id):
    """
    Get total like count by summing all shards.
    """
    
    # Try cache first
    cached = redis.get(f"like:count:{post_id}")
    if cached:
        return int(cached)
    
    # Cache miss: Query all shards
    result = cassandra.execute(
        """
        SELECT SUM(count) as total
        FROM like_counts_sharded
        WHERE post_id = ?
        """,
        [post_id]
    )
    
    total = result.one().total or 0
    
    # Cache for 5 minutes
    redis.setex(f"like:count:{post_id}", 300, total)
    
    return total

def is_viral_post(post_id):
    """
    Detect if post is viral (needs more shards).
    """
    # Check like rate in last 5 minutes
    recent_likes = cassandra.execute(
        """
        SELECT COUNT(*) as count
        FROM likes
        WHERE post_id = ? AND created_at > ?
        """,
        [post_id, datetime.now() - timedelta(minutes=5)]
    ).one().count
    
    # More than 10,000 likes in 5 min = viral
    return recent_likes > 10000
```

---

### Option 1: Static Sharding

**Static = Fixed number of shards from the beginning**

```
┌─────────────────────────────────────────────────────────────┐
│                  STATIC SHARDING                             │
└─────────────────────────────────────────────────────────────┘

When Post is Created:
┌────────────────────────────────────────┐
│  Post: post_123                        │
│  Shards: 100 (fixed)                   │
│  ─────────────────────────────────     │
│  Shard 0: count = 0                    │
│  Shard 1: count = 0                    │
│  ...                                   │
│  Shard 99: count = 0                   │
└────────────────────────────────────────┘

Pros:
✅ Simple to implement
✅ Predictable performance
✅ No dynamic logic needed

Cons:
❌ Over-sharding for small posts (waste)
❌ Under-sharding for viral posts (still bottleneck)
❌ Can't adjust after creation

Example:
Normal post (10 likes): 100 shards is overkill!
Viral post (10M likes): 100 shards not enough!
```

---

### Option 2: Dynamic Sharding

**Dynamic = Adjust shards based on traffic**

```
┌─────────────────────────────────────────────────────────────┐
│                  DYNAMIC SHARDING                            │
└─────────────────────────────────────────────────────────────┘

Timeline of a Post:

Hour 0 (Just Posted):
┌────────────────────────────────┐
│  post_123                      │
│  Shards: 10 (initial)          │
│  Traffic: Low                  │
└────────────────────────────────┘
Likes/min: 100

Hour 1 (Getting Popular):
┌────────────────────────────────┐
│  post_123                      │
│  Shards: 100 (scaled up 10x)   │  ← Auto-scaled!
│  Traffic: Medium               │
└────────────────────────────────┘
Likes/min: 5,000

Hour 2 (Gone Viral!):
┌────────────────────────────────┐
│  post_123                      │
│  Shards: 1,000 (scaled up 10x) │  ← Auto-scaled again!
│  Traffic: VIRAL                │
└────────────────────────────────┘
Likes/min: 100,000

Pros:
✅ Efficient (right-sized shards)
✅ Handles viral posts automatically
✅ Cost-effective

Cons:
❌ Complex to implement
❌ Need to migrate data (old shards → new shards)
❌ Potential downtime during scaling
```

---

### How Dynamic Sharding Works Internally

```python
def dynamic_sharding_example():
    """
    Dynamic sharding with auto-scaling.
    """
    
    # Monitor like rate
    likes_per_minute = get_likes_per_minute(post_id)
    current_shards = get_current_shard_count(post_id)
    
    # Thresholds
    SCALE_UP_THRESHOLD = 1000  # likes/min per shard
    SCALE_DOWN_THRESHOLD = 100  # likes/min per shard
    
    # Calculate ideal shards
    ideal_shards = likes_per_minute / SCALE_UP_THRESHOLD
    
    if ideal_shards > current_shards * 2:
        # Need to scale up!
        new_shards = current_shards * 10
        scale_up_shards(post_id, current_shards, new_shards)
    
    elif ideal_shards < current_shards / 10:
        # Can scale down (save resources)
        new_shards = current_shards / 10
        scale_down_shards(post_id, current_shards, new_shards)

def scale_up_shards(post_id, old_shards, new_shards):
    """
    Scale up shards (e.g., 100 → 1000).
    """
    
    print(f"Scaling {post_id}: {old_shards} → {new_shards} shards")
    
    # Step 1: Create new shard records
    for shard_id in range(new_shards):
        cassandra.execute(
            """
            INSERT INTO like_counts_sharded (post_id, shard_id, count)
            VALUES (?, ?, 0)
            IF NOT EXISTS
            """,
            [post_id, shard_id]
        )
    
    # Step 2: Update metadata
    cassandra.execute(
        """
        UPDATE post_metadata
        SET shard_count = ?
        WHERE post_id = ?
        """,
        [new_shards, post_id]
    )
    
    # Step 3: Migrate old counts (optional, can be lazy)
    # Option A: Redistribute old counts across new shards
    # Option B: Keep old shards, add new ones (easier!)
    
    # We choose Option B (lazy migration):
    # - Old shards keep their counts
    # - New likes go to new shards
    # - When reading, sum ALL shards (old + new)
    
    print(f"✅ Scaled up to {new_shards} shards")
```

---

### Visual: How Data Splits During Scaling

```
┌─────────────────────────────────────────────────────────────┐
│              SHARD SCALING VISUALIZATION                     │
└─────────────────────────────────────────────────────────────┘

Before Scaling (10 shards):
┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐
│ S0 │ S1 │ S2 │ S3 │ S4 │ S5 │ S6 │ S7 │ S8 │ S9 │
├────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤
│100k│100k│100k│100k│100k│100k│100k│100k│100k│100k│
└────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘
Total: 1,000,000 likes

After Scaling (100 shards):
┌──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┐
│S0│S1│...│S9│S10│S11│S12│...│S97│S98│S99│  ← Old + New
├──┼──┼───┼──┼───┼───┼───┼───┼───┼───┼───┤
│100k (old)│0 │0  │0  │... │0  │0  │0  │  ← New shards empty
└──┴──┴───┴──┴───┴───┴───┴───┴───┴───┴───┘

New likes after scaling:
- User hash(12345) % 100 = 45 → goes to S45 (new shard)
- User hash(67890) % 100 = 78 → goes to S78 (new shard)

Reading total count:
= sum(S0 to S99)
= 100k + 100k + ... + 0 + 0 + ...
= 1,000,000 (still correct!)

Over time, old shards stay same, new shards grow ✅
```

---

### Application-Level Sharding

**Application = Your code decides sharding, not database**

```
┌─────────────────────────────────────────────────────────────┐
│             APPLICATION-LEVEL SHARDING                       │
└─────────────────────────────────────────────────────────────┘

Without App-Level Sharding:
┌──────────────┐
│ Application  │
│    Code      │
└──────┬───────┘
       │ INSERT INTO likes (post_id, user_id)...
       ▼
┌──────────────┐
│  Database    │  ← Database handles everything
│  (Auto)      │
└──────────────┘

Problem: Database doesn't know sharding strategy!

───────────────────────────────────────────────────────────

With App-Level Sharding:
┌──────────────────────────────────┐
│ Application Code                 │
│  ──────────────────────────────  │
│  1. Calculate shard: hash % 100  │  ← YOU control this!
│  2. Route to correct partition   │
│  3. Execute write                │
└────────┬─────────────────────────┘
         │
         ├─────────┬─────────┬─────────┐
         ▼         ▼         ▼         ▼
    ┌────────┐┌────────┐┌────────┐┌────────┐
    │Shard 0 ││Shard 1 ││Shard 2 ││Shard 3 │
    └────────┘└────────┘└────────┘└────────┘
```

**Code Example:**

```python
class LikeService:
    def __init__(self):
        self.shard_config = {
            "post_123": {"shards": 100, "viral": False},
            "post_456": {"shards": 1000, "viral": True},
            # ... more posts
        }
    
    def like_post(self, user_id, post_id):
        """
        Application-level sharding logic.
        """
        
        # STEP 1: Get shard config (app decides!)
        config = self.shard_config.get(post_id)
        if not config:
            # First like on this post
            config = {"shards": 10, "viral": False}
            self.shard_config[post_id] = config
        
        num_shards = config["shards"]
        
        # STEP 2: Calculate shard (app decides!)
        shard_id = self.calculate_shard(user_id, num_shards)
        
        # STEP 3: Write to specific shard (app controls!)
        self.write_to_shard(post_id, user_id, shard_id)
        
        # STEP 4: Check if need to scale (app monitors!)
        self.check_and_scale(post_id)
    
    def calculate_shard(self, user_id, num_shards):
        """App decides sharding function."""
        return hash(user_id) % num_shards
    
    def write_to_shard(self, post_id, user_id, shard_id):
        """App controls where data goes."""
        cassandra.execute(
            """
            UPDATE like_counts_sharded
            SET count = count + 1
            WHERE post_id = ? AND shard_id = ?
            """,
            [post_id, shard_id]
        )
    
    def check_and_scale(self, post_id):
        """App decides when to scale."""
        likes_per_min = self.get_like_rate(post_id)
        
        if likes_per_min > 10000:  # Viral!
            current = self.shard_config[post_id]["shards"]
            new_shards = current * 10
            
            print(f"🔥 Viral post detected! Scaling {current} → {new_shards}")
            
            self.shard_config[post_id] = {
                "shards": new_shards,
                "viral": True
            }
```

---

## MongoDB vs Cassandra

### MongoDB Limitations

```
┌─────────────────────────────────────────────────────────────┐
│              MONGODB (Document Database)                     │
└─────────────────────────────────────────────────────────────┘

Architecture:
- Uses B-Tree indexes (same as PostgreSQL)
- Single-leader replication (one primary, many replicas)
- Sharding available, but...

Problem: Write Bottleneck
┌────────────────────────────────────┐
│  Primary Node (Leader)             │  ← ALL writes go here
│  ──────────────────────────────    │
│  Handles all writes                │
│  Bottleneck at ~50K writes/sec     │  ❌
└────────────────────────────────────┘
       │
       ├───────────┬───────────┐
       ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│Replica 1 │ │Replica 2 │ │Replica 3 │  ← Only reads
└──────────┘ └──────────┘ └──────────┘

Instagram needs 200K writes/sec → MongoDB can't handle! ❌
```

**Why MongoDB is Slower:**

```
MongoDB Write Path:
1. Write goes to PRIMARY only
2. Primary writes to journal (B-Tree)
3. Primary updates indexes (B-Tree)
4. Primary replicates to secondaries (async)
5. Acknowledge to client

Time: ~10ms
Max throughput: 50,000 writes/sec

Cassandra Write Path:
1. Write goes to ANY node (no leader!)
2. Node writes to commit log (append-only)
3. Node writes to memtable (memory)
4. Acknowledge immediately

Time: ~2ms
Max throughput: 500,000+ writes/sec (10x faster!)
```

---

### Detailed Comparison

| Feature | MongoDB | Cassandra |
|---------|---------|-----------|
| **Write Model** | Leader-based (bottleneck) | Leaderless (distributed) |
| **Write Speed** | ~10ms | ~2ms |
| **Max Throughput** | 50K writes/sec | 500K+ writes/sec |
| **Horizontal Scaling** | Limited (leader bottleneck) | Unlimited (linear) |
| **Hot Spot Handling** | Poor (leader overload) | Excellent (distributed) |
| **Best For** | Flexible queries, documents | High writes, simple queries |

**Real Example:**

```
Test: 100,000 likes per second

MongoDB Setup:
- 1 Primary node (handles all writes)
- 5 Replica nodes (handle reads only)

Result:
- Primary node at 100% CPU
- Write latency: 50ms (slow!)
- Many requests timeout ❌
- Database struggles

Cassandra Setup:
- 10 nodes (all handle writes!)
- No leader, no bottleneck

Result:
- Each node at 40% CPU
- Write latency: 2ms (fast!)
- All requests succeed ✅
- Database happy
```

---

## Advanced Interview Questions

### Q1: What happens if shard count changes mid-flight?

**Scenario:**
```
Timeline:
T0: Post has 100 shards
T1: User Alice likes (calculated: shard 45)
T2: System scales to 1000 shards
T3: Write reaches database

Question: Does write go to shard 45 or recalculated?
```

**Answer:**
```python
# Solution: Version-based sharding

def like_post_with_versioning(user_id, post_id):
    # Step 1: Get current shard config with version
    config = get_shard_config(post_id)
    # config = {"shards": 100, "version": 1}
    
    # Step 2: Calculate shard based on THIS version
    shard_id = hash(user_id) % config["shards"]
    
    # Step 3: Write with version check
    try:
        cassandra.execute(
            """
            UPDATE like_counts_sharded
            SET count = count + 1
            WHERE post_id = ? AND shard_id = ? AND version = ?
            IF version = ?
            """,
            [post_id, shard_id, config["version"], config["version"]]
        )
    except VersionMismatch:
        # Version changed! Retry with new config
        return like_post_with_versioning(user_id, post_id)
```

---

### Q2: How do you prevent data loss during shard migration?

**Answer:**
```
┌─────────────────────────────────────────────────────────────┐
│              SAFE SHARD MIGRATION                            │
└─────────────────────────────────────────────────────────────┘

Phase 1: Dual Write (Safe)
──────────────────────────
Write to BOTH old and new shards
┌──────────────┐     ┌──────────────┐
│  Old Shards  │ ◄───┤  New Likes   │
│  (100)       │     │  (go here    │
└──────────────┘     │   too!)      │
                     └─────┬────────┘
┌──────────────┐           │
│  New Shards  │ ◄─────────┘
│  (1000)      │
└──────────────┘

Duration: Until all old data migrated

Phase 2: Read from New (Verify)
────────────────────────────────
Read from new shards, fallback to old if needed
- Monitor for discrepancies
- Compare counts

Phase 3: Delete Old (Cleanup)
──────────────────────────────
Once verified, delete old shards
- All traffic on new shards
- Old shards deleted
```

---

### Q3: How would you handle partial writes (some shards succeed, some fail)?

**Answer:**
```python
def like_post_with_retries(user_id, post_id):
    """
    Ensure eventual consistency even with partial failures.
    """
    
    shard_id = calculate_shard(user_id, num_shards)
    
    # Write to likes table
    like_written = False
    for attempt in range(3):
        try:
            cassandra.execute(
                "INSERT INTO likes (post_id, user_id) VALUES (?, ?)",
                [post_id, user_id]
            )
            like_written = True
            break
        except Exception as e:
            if attempt == 2:
                # All retries failed
                write_to_dlq(post_id, user_id, "like_insert_failed")
                return {"status": "failed", "reason": str(e)}
    
    # Write to counter (even if main write failed, log to DLQ)
    counter_written = False
    for attempt in range(3):
        try:
            cassandra.execute(
                "UPDATE like_counts_sharded SET count = count + 1 ...",
                [post_id, shard_id]
            )
            counter_written = True
            break
        except Exception as e:
            if attempt == 2:
                # Counter failed, but like succeeded
                # Log for reconciliation
                write_to_dlq(post_id, user_id, "counter_increment_failed")
    
    # Publish to Kafka (best effort)
    try:
        kafka.produce("like-events", {
            "post_id": post_id,
            "user_id": user_id,
            "shard_id": shard_id
        })
    except:
        pass  # Non-critical
    
    return {
        "status": "success" if like_written else "partial",
        "like_written": like_written,
        "counter_written": counter_written
    }
```

---

### Q4: How do you maintain consistent counts with sharding?

**Answer:**
```python
# Periodic reconciliation job

def reconcile_sharded_counts():
    """
    Verify shard counts match actual data.
    Run hourly.
    """
    
    # Get all posts with recent activity
    active_posts = get_active_posts(last_hour=1)
    
    for post in active_posts:
        # Get sum of all shards
        shard_total = cassandra.execute(
            "SELECT SUM(count) FROM like_counts_sharded WHERE post_id = ?",
            [post.post_id]
        ).one().sum
        
        # Get actual count
        actual_count = cassandra.execute(
            "SELECT COUNT(*) FROM likes WHERE post_id = ?",
            [post.post_id]
        ).one().count
        
        # Compare
        if shard_total != actual_count:
            drift = abs(shard_total - actual_count)
            
            logger.warning(f"Count mismatch for {post.post_id}: "
                          f"shards={shard_total}, actual={actual_count}, "
                          f"drift={drift}")
            
            # Fix: Redistribute counts
            redistribute_counts(post.post_id, actual_count)
```

---

### Q5: What if hash function changes? (Re-sharding nightmare)

**Answer:**
```python
# Solution: Consistent hashing with virtual nodes

class ConsistentHashRing:
    def __init__(self, num_shards):
        self.num_shards = num_shards
        self.ring = []
        
        # Create virtual nodes (100 per shard)
        for shard_id in range(num_shards):
            for vnode in range(100):
                hash_val = hash(f"shard_{shard_id}_vnode_{vnode}")
                self.ring.append((hash_val, shard_id))
        
        # Sort ring
        self.ring.sort()
    
    def get_shard(self, user_id):
        """
        Find shard using consistent hashing.
        """
        user_hash = hash(user_id)
        
        # Binary search for closest hash on ring
        for hash_val, shard_id in self.ring:
            if hash_val >= user_hash:
                return shard_id
        
        # Wrap around
        return self.ring[0][1]
    
    def add_shards(self, additional_shards):
        """
        Add shards without rehashing everything!
        """
        old_shard_count = self.num_shards
        self.num_shards += additional_shards
        
        # Only add new virtual nodes
        for shard_id in range(old_shard_count, self.num_shards):
            for vnode in range(100):
                hash_val = hash(f"shard_{shard_id}_vnode_{vnode}")
                self.ring.append((hash_val, shard_id))
        
        self.ring.sort()
        
        # Result: Only ~10% of data needs to move (not 100%!)
```

---

### Q6: How do you test sharding logic?

```python
import pytest

def test_sharding_distribution():
    """
    Verify shards receive roughly equal traffic.
    """
    NUM_SHARDS = 100
    NUM_USERS = 100000
    
    shard_counts = [0] * NUM_SHARDS
    
    # Simulate 100K users liking a post
    for user_id in range(NUM_USERS):
        shard = calculate_shard(user_id, NUM_SHARDS)
        shard_counts[shard] += 1
    
    # Each shard should get ~1000 likes (±10%)
    expected = NUM_USERS / NUM_SHARDS
    tolerance = expected * 0.1
    
    for shard_id, count in enumerate(shard_counts):
        assert abs(count - expected) < tolerance, \
            f"Shard {shard_id} imbalanced: {count} (expected ~{expected})"
    
    print("✅ Shard distribution is balanced")

def test_sharding_consistency():
    """
    Verify same user always goes to same shard.
    """
    user_id = "user_12345"
    NUM_SHARDS = 100
    
    # Calculate shard 1000 times
    shards = [calculate_shard(user_id, NUM_SHARDS) for _ in range(1000)]
    
    # Should all be the same!
    assert len(set(shards)) == 1, "User mapping is inconsistent!"
    
    print(f"✅ User {user_id} consistently maps to shard {shards[0]}")

def test_scaling_preserves_data():
    """
    Verify scaling up doesn't lose data.
    """
    post_id = "post_123"
    
    # Initial: 100 shards with 1M likes
    initial_count = get_total_count_from_shards(post_id, num_shards=100)
    assert initial_count == 1000000
    
    # Scale up to 1000 shards
    scale_up_shards(post_id, old=100, new=1000)
    
    # Verify count preserved
    new_count = get_total_count_from_shards(post_id, num_shards=1000)
    assert new_count == 1000000, "Data lost during scaling!"
    
    print("✅ Scaling preserved all data")
```

---

## Summary Cheat Sheet

```
┌─────────────────────────────────────────────────────────────┐
│                      QUICK REFERENCE                         │
└─────────────────────────────────────────────────────────────┘

Why Cassandra?
✅ Write-heavy workloads (LSM tree, no locks)
✅ Horizontal scaling (add nodes = more throughput)
✅ No hot spots (distributed writes)
✅ High availability (no single leader)

Throughput = Operations per second
- Instagram: 200,000 likes/sec (peak)
- Cassandra: Can handle it ✅
- PostgreSQL: Cannot handle it ❌

LSM Tree = Log-Structured Merge Tree
- Writes go to memory (fast!)
- Flush to disk later (async)
- No locks, no contention

B-Tree = Traditional index
- Writes require locks
- In-place updates (slow)
- Used by PostgreSQL, MongoDB

Sharding = Split data across multiple partitions
- Avoids hot spots
- Distributes load
- Improves throughput

Application-Level Sharding = Your code controls sharding
- More flexible
- Can adapt to traffic
- You decide strategy

MongoDB limitations:
- Leader-based writes (bottleneck)
- B-Tree indexes (slower writes)
- Max 50K writes/sec (not enough for Instagram)

Key Interview Points:
1. Explain LSM vs B-Tree (inbox vs filing cabinet)
2. Show sharding code with hash % num_shards
3. Discuss dynamic scaling strategy
4. Mention consistency trade-offs
5. Demonstrate understanding of throughput requirements
```

---

## Interview Practice Questions

### Question 1:
**"Why not just use a bigger PostgreSQL server?"**

**Answer:**
```
Vertical scaling (bigger server) has limits:
- Max CPU: ~128 cores
- Max RAM: ~4 TB
- Max throughput: ~100K writes/sec
- Cost: $50,000/month

Instagram needs 200K writes/sec → Can't fit on one server!

Horizontal scaling (Cassandra, many servers):
- 10 nodes × 20K writes/sec = 200K total
- Linear scaling: add more nodes = more capacity
- Cost: 10 × $5,000 = $50,000/month (same price, better scaling!)

Answer: Horizontal scaling is the only way to reach Instagram scale.
```

---

### Question 2:
**"How do you avoid re-sharding when scaling?"**

**Answer:**
```
Use consistent hashing with virtual nodes:
- Each physical shard has 100 virtual nodes
- When adding shards, only ~10% of data moves
- No full re-hash needed

Example:
- 100 shards → 1000 shards
- Without consistent hashing: 90% data moves (nightmare!)
- With consistent hashing: 10% data moves (manageable!)

Plus: Use dual-write during migration (write to both old and new)
- Zero downtime
- Gradual migration
- Rollback possible
```

---

### Question 3:
**"What if two data centers both increment the same shard counter simultaneously?"**

**Answer:**
```
Cassandra handles this with CRDT (Conflict-free Replicated Data Type):

Scenario:
- DC-A: counter += 5
- DC-B: counter += 3
- Network partition (can't sync)

Later (partition heals):
- Cassandra merges: counter += (5 + 3) = +8 ✅
- No conflict, no data loss

Why it works:
- Counter operations are commutative (order doesn't matter)
- 5 + 3 = 3 + 5
- Last-write-wins doesn't apply (additive merge)

Final count is always correct!
```

---

**End of Document**

This guide covers everything from basics to advanced topics for interviews!
