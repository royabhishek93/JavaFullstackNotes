# Database Sharding: Partition Strategies & Consistency

**Study Time:** 12-15 minutes | **Frequency:** 85% in senior interviews | **Difficulty:** ⭐⭐⭐⭐⭐

---

## 🤔 Problem Scenario

Your database has 1 billion users. Single database can't handle the load:

```
Single Database (BOTTLENECK):
┌──────────────────┐
│ users (1B rows)  │ ← ALL queries hit here
│ orders (10B rows)│ ← Slow, locks, timeouts
│ payments (5B)    │
└──────────────────┘
Performance: 100 queries/sec max

Sharded Database (DISTRIBUTED):
Shard 1        Shard 2        Shard 3        Shard 4
users: 250M    users: 250M    users: 250M    users: 250M

Performance: 100 × 4 = 400 queries/sec!
```

**Challenge:** How to split data? How to query? What about joins?

---

## 🧠 Key Principle: Three Sharding Strategies

| Strategy | Key | Trade-offs |
|----------|-----|-----------|
| **Range-based** | User ID range (0-250M, 250M-500M) | Hotspots, uneven distribution |
| **Hash-based** | hash(user_id) % 4 | Even distribution, but resharding hard |
| **Directory-based** | Lookup table (user_id → shard) | Most flexible, extra lookup |

---

## ✅ Strategy 1: Range-Based Sharding

```
Shard the data by ranges:

Shard 1: user_id 1-250M
Shard 2: user_id 250M-500M
Shard 3: user_id 500M-750M
Shard 4: user_id 750M-1B

Query: SELECT * FROM users WHERE user_id = 500000001
→ Go to Shard 2 (because 250M < ID < 500M)
```

### Implementation:

```java
public class RangeBasedSharding {
    
    private final List<Database> shards = new ArrayList<>();
    
    public Database getShard(long userId) {
        // Determine shard based on range
        if (userId <= 250_000_000) return shards.get(0);
        if (userId <= 500_000_000) return shards.get(1);
        if (userId <= 750_000_000) return shards.get(2);
        return shards.get(3);
    }
    
    public User getUser(long userId) {
        Database shard = getShard(userId);
        return shard.query("SELECT * FROM users WHERE id = ?", userId);
    }
    
    public void insertUser(User user) {
        Database shard = getShard(user.getId());
        shard.execute("INSERT INTO users VALUES (?)", user);
    }
}
```

### Problems:

```
Problem 1: HOTSPOTS
- Range 0-250M has 60% of active users
- Shard 1 overloaded, others idle

Problem 2: RESHARDING
- Oops, need 8 shards instead of 4
- Move 50% of data from Shard 1 to new shards
- Downtime, expensive operation

Problem 3: UNEVEN DISTRIBUTION
- User registration concentrated in certain ID ranges
- Historical ranges (0-100M) have archive data
- Modern ranges (900M-1B) have hot data
```

---

## ✅ Strategy 2: Hash-Based Sharding

```
Hash the key and mod number of shards:

user_id = 500000001
hash(500000001) = 8374582
8374582 % 4 = 2 → Shard 2

Distributes evenly!
```

### Implementation:

```java
public class HashBasedSharding {
    
    private final List<Database> shards = new ArrayList<>();
    private static final int SHARD_COUNT = 4;
    
    public Database getShard(long userId) {
        // Consistent hash
        return shards.get(Math.abs(Objects.hash(userId) % SHARD_COUNT));
    }
    
    public User getUser(long userId) {
        Database shard = getShard(userId);
        return shard.query("SELECT * FROM users WHERE id = ?", userId);
    }
}
```

### Advantages:

```
✅ Even distribution - no hotspots
✅ Simple logic - just hash and mod
✅ Works at scale
```

### Problems:

```
Problem: RESHARDING IS HARD
- Add Shard 5: hash % 5 changes everything!
- user_id 500000001: was in Shard 2, now in Shard 1
- Need to migrate half the data!

Solution: Consistent Hashing
hash(key) maps to "ring" of shards
Adding 1 shard only affects 25% of keys
Much less data movement!

Implementation:
class ConsistentHashRing {
    Map<Integer, Shard> ring;  // hash → shard
    TreeMap<Integer, Shard> sortedRing;
    
    Shard getShard(long key) {
        int hash = hash(key);
        SortedMap<Integer, Shard> tailMap = sortedRing.tailMap(hash);
        return tailMap.isEmpty() ? ring.values().iterator().next() 
                                 : tailMap.values().iterator().next();
    }
}
```

---

## ✅ Strategy 3: Directory-Based Sharding

```
Keep a lookup table: user_id → shard_id

shardDirectory table:
user_id     │ shard_id
────────────┼─────────
500000001   │ 2
500000002   │ 1
500000003   │ 3
...

Query: SELECT shard_id FROM shardDirectory WHERE user_id = 500000001
→ Shard 2
```

### Implementation:

```java
public class DirectoryBasedSharding {
    
    private final List<Database> shards = new ArrayList<>();
    private final Database directoryDb;  // Central lookup
    
    public Database getShard(long userId) {
        // Query directory for shard
        Integer shardId = directoryDb.queryOne(
            "SELECT shard_id FROM shard_directory WHERE user_id = ?",
            userId
        );
        return shards.get(shardId);
    }
    
    public void insertUser(User user) {
        // Choose which shard (round-robin, least-used, etc.)
        int shardId = chooseOptimalShard();
        
        // Update directory
        directoryDb.execute(
            "INSERT INTO shard_directory (user_id, shard_id) VALUES (?, ?)",
            user.getId(), shardId
        );
        
        // Insert data
        shards.get(shardId).execute("INSERT INTO users VALUES (?)", user);
    }
    
    private int chooseOptimalShard() {
        // Implement: round-robin, least-loaded, etc.
        return 0;
    }
}
```

### Advantages:

```
✅ No hotspots - choose shard based on load
✅ Resharding is easy - just update directory
✅ Flexible - can rebalance data anytime
```

### Problems:

```
Problem: EXTRA LOOKUP
- Every query hits directory DB first
- Adds latency: Query Directory (5ms) + Shard Query (5ms) = 10ms

Solution: Cache the directory
- Cache user_id → shard_id in local/Redis
- Directory only for cache misses
```

---

## 📊 Sharding Strategy Comparison

| Aspect | Range | Hash | Directory |
|--------|-------|------|-----------|
| **Distribution** | Uneven | Even | Configurable |
| **Hotspots** | YES (problem) | NO | NO |
| **Resharding** | Painful | Very painful | Easy |
| **Query latency** | O(1) | O(1) | O(2) + cache |
| **Complexity** | Low | Medium | Medium |
| **Best for** | Sequential IDs | Distributed scale | Dynamic load |

---

## 🚨 Sharding Challenges

### Challenge 1: Cross-Shard Queries

```sql
-- Works (single shard):
SELECT * FROM users WHERE user_id = 12345;  -- Goes to Shard 2

-- Breaks (needs all shards):
SELECT * FROM users WHERE country = 'USA';  -- Must query Shard 1, 2, 3, 4
→ Scatter-gather (slow!)

Solution:
- Denormalize country to all shards
- Or: Secondary shard by country
```

---

### Challenge 2: Joins Across Shards

```sql
-- Problem:
SELECT orders.*, users.*
FROM orders
JOIN users ON orders.user_id = users.id
WHERE user_id = 12345;

-- If orders and users sharded differently:
- orders shard: 1
- users shard: 2
- Join requires cross-shard call (slow!)

Solution:
- Shard both by user_id (co-locate)
- Denormalize user data to orders table
- Cache join results
```

---

### Challenge 3: Global Sequences

```java
// Problem: How to generate unique user IDs across shards?
// Can't just: AUTO_INCREMENT (each shard gets 1, 2, 3...)

// Solution 1: Centralized ID Generator
class IdGenerator {
    private long nextId = 0;
    
    synchronized long nextId() {
        return nextId++;  // Bottleneck!
    }
}

// Solution 2: Twitter Snowflake
// 64-bit ID = [timestamp:41][datacenter:5][shard:5][sequence:13]
// Each shard generates unique IDs without coordination

// Solution 3: UUID
String uuid = UUID.randomUUID().toString();
// Guaranteed unique, but larger
```

---

## 🎯 Interview Q&A

### Q1: "Which sharding strategy?"

**Answer:**
```
Range: User registration IDs (0, 1, 2, ...)
- Sequential, know growth pattern
- Acceptable hotspots in new ranges

Hash: Distributed user base
- Random distribution, no patterns
- Equal load across shards

Directory: Multi-tenant, complex logic
- Different customers on different shards
- Dynamic load balancing needed

For most cases: Hash-based with consistent hashing
```

---

### Q2: "How to handle resharding?"

**Answer:**
```
Scenario: Growing from 4 shards to 8 shards

Approach 1: Stop world (DOWNTIME)
- Lock all shards
- Rehash and migrate data
- Restart

Approach 2: Rolling resharding (NO downtime)
- Keep 4 shards + 4 new shards
- Route reads to both
- Migrate data in background
- Eventually all on new shards
- Decommission old shards

Approach 3: Directory-based (EASIEST)
- Just update directory: user_id → new_shard_id
- No data migration upfront
- Migrate data lazily

Best in production: Approach 2 (rolling)
```

---

### Q3: "Database consistency with sharding?"

**Answer:**
```
Challenge: Distributed ACID is hard

Option 1: Per-shard ACID
- Single shard transaction: ACID guaranteed
- Cross-shard: NO guarantees (eventually consistent)

Option 2: Eventual consistency
- Accept temporary inconsistency
- Reconciliation process

Option 3: Shard colocation
- Keep related data in same shard
- More ACID guarantees

Example:
Orders and Order_Items in SAME shard (by order_id)
→ Cross-shard join on Orders guaranteed
But Orders with different shards can't join
→ Must denormalize or query separately
```

---

## 🔑 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Strategy selection | Right choice for scenario | ⭐⭐⭐⭐⭐ |
| Distribution evenness | Avoiding hotspots | ⭐⭐⭐⭐⭐ |
| Resharding cost | Operational understanding | ⭐⭐⭐⭐ |
| Cross-shard queries | Real challenge awareness | ⭐⭐⭐⭐ |
| Consistency implications | Trade-off thinking | ⭐⭐⭐⭐ |

---

**Priority:** 🔥 MUST KNOW (85% senior interviews)

**Related:**
- Replication
- Consistency Models
- Distributed Transactions

---

**Last Updated:** March 5, 2026
