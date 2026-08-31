# Hot Partition Problem and Solutions
### Why celebrity users, Black Friday, and trending topics break distributed systems — and how to fix them

---

## PART 1 — THE STUDENT CONVERSATION

Picture a highway with 10 lanes. Traffic is normally spread evenly — each lane carries about 10% of all vehicles. Nice and smooth.

One day, a celebrity's convoy enters the highway. Ten thousand journalists, paparazzi, and fans follow them. Suddenly 99% of all traffic is in Lane 3. Lane 3 is completely gridlocked. Lanes 1, 2, and 4-10 are nearly empty. You can't solve this by adding more lanes to the highway — the problem isn't total capacity, it's that 99% of traffic is routing to one lane.

This is the hot partition problem. In distributed systems, you split data across multiple shards or partitions to distribute load. But if your partitioning key is uneven — if one key generates far more traffic than others — one partition drowns while all the others idle.

Real examples:
- **Kafka, keyed by user_id:** Cristiano Ronaldo has 500M followers. Every action he takes triggers 500M fan feed updates, all with the same Kafka partition key. His partition processes 1000x more messages than the average user's partition.
- **Database, sharded by date:** New orders always write to the "today" shard. Historical data is cold. The current-day shard handles 95% of all reads and writes — it's a hot shard even though you have 100 shards.
- **Cache, keyed by product_id:** One product goes viral on TikTok. 10 million users hit the same product page in 10 minutes. Even if the cache holds the data, the single cache node for that product_id saturates its network bandwidth.

The tricky part: your monitoring shows total throughput is fine (the overall system isn't overloaded), but one node is throwing errors or slowing down. You have to look at PER-PARTITION metrics, not averages.

---

## PART 2 — THE HOT PARTITION DIAGRAMS

### Hot Partition in Kafka

```
Topic: "user-events"  (6 partitions)
Partition key = user_id
hash(user_id) % 6 determines partition

Normal day — even distribution:
  P0: ████░░░░░░  2K events/sec  (normal users)
  P1: ████░░░░░░  2K events/sec
  P2: ████░░░░░░  2K events/sec
  P3: ████░░░░░░  2K events/sec
  P4: ████░░░░░░  2K events/sec
  P5: ████░░░░░░  2K events/sec
  Total: 12K events/sec

When Cristiano Ronaldo (500M followers) posts:
  hash("user_12345") % 6 = 3   ← Ronaldo maps to P3

  P0: ████░░░░░░  2K events/sec  (unchanged)
  P1: ████░░░░░░  2K events/sec
  P2: ████░░░░░░  2K events/sec
  P3: ████████████████████████  50K events/sec  ← ALL of Ronaldo's events
  P4: ████░░░░░░  2K events/sec
  P5: ████░░░░░░  2K events/sec
  Total: 62K events/sec

  P3 consumer: overwhelmed, consumer lag grows from 0 → millions
  P3 consumer: "NullPointerException: heap exhausted" (OOMKilled)
  P0-P2, P4-P5 consumers: completely fine, sitting idle

  Result: Ronaldo's fans don't see feed updates for 2 hours.
          Your status page says "All systems normal" (average looks fine).
```

### Hot Shard in Database — Bad Sharding Key Choice

```
Table: orders
Shard key: created_at (DATE)

Shard distribution today (system has been running 4 years):
  Shard 1: orders from 2021  → ~5%  reads (mostly archived, nobody looks)
  Shard 2: orders from 2022  → ~10% reads (some returns/disputes still active)
  Shard 3: orders from 2023  → ~20% reads (recent history queries)
  Shard 4: orders from 2024  → ~30% reads + writes (recent, still browsed)
  Shard 5: 2025-today        → ~35% reads + 100% writes  ← HOT SHARD

  All new orders write to Shard 5.
  "Recent order history" queries hit Shard 5.
  Shard 5 CPU: 95%.   Shards 1-4 CPU: 5-20%.

  Lesson: time-based shard keys are almost always a bad idea.
  Better shard keys: hash(user_id), hash(order_id) — uniform distribution.
```

### Hot Key in Cache

```
Normal product page traffic:
  Redis node 1: product_A (1K req/s), product_B (900 req/s), ...
  Redis node 2: product_C (1.1K req/s), product_D (800 req/s), ...
  Redis node 3: product_E (950 req/s), product_F (1K req/s), ...
  Each node: ~5K req/s total. Redis can handle 500K req/s. Fine.

TikTok influencer posts video wearing product_G:
  Redis node 2 (where product_G hashes to): 200K req/s
  Redis node 2: CPU 100%, network card saturated
  Redis node 1, 3: completely normal

  Even though you have 3 Redis nodes, 1 node handles ALL traffic
  for the viral product. The solution can't just be "add more Redis nodes"
  — you need to change how the hot key is distributed.
```

### Detection: Finding Hot Partitions

```bash
# Kafka: consumer lag per partition
kafka-consumer-groups.sh \
  --bootstrap-server kafka:9092 \
  --describe --group my-consumer-group | \
  sort -k5 -nr | head -20

# Output (sorted by LAG descending):
# GROUP           TOPIC        PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
# my-group        user-events  3          4000000         54000000        50000000  ← HOT!
# my-group        user-events  0          2000000         2100000         100000
# my-group        user-events  1          1500000         1600000         100000

# Partition 3 has 50M lag. Partitions 0,1,2,4,5 have <200K lag.
# Classic hot partition signature.

# Database hot shard detection:
SELECT schemaname, tablename,
       n_tup_ins + n_tup_upd + n_tup_del AS writes,
       seq_scan, idx_scan
FROM pg_stat_user_tables
ORDER BY writes DESC;

# Shard routing logs (grep for which shard gets the most requests):
grep "routing to shard" app.log | awk '{print $NF}' | sort | uniq -c | sort -nr
```

---

## PART 3 — SOLUTIONS IN DEPTH

### Solution 1: Add a Salt/Random Prefix (Kafka)

The simplest fix: instead of routing ALL of Ronaldo's events to one partition, spread them across 10 partitions by appending a random suffix.

```java
// Producer side:
public String buildPartitionKey(String userId, boolean isCelebrity) {
    if (isCelebrity) {
        // Spread across 10 "sub-partitions"
        int salt = ThreadLocalRandom.current().nextInt(10);
        return userId + "_" + salt;  // "user_12345_7" → hashes to different partition
    }
    return userId;
}

// Consumer side (aggregation required):
// To process all of Ronaldo's events, you must consume from ALL partitions
// Events for "user_12345_0" through "user_12345_9" are spread across all 6 partitions.
// You cannot rely on "all events for user X are in one partition" anymore.

// Trade-off: ordering guarantee broken. Events for user_12345_3 and user_12345_7
// may arrive out of order relative to each other.
// Solution: add a sequence number to each event, re-sort on consumer side.
```

### Solution 2: Dedicated Partitions for Hot Keys

Pre-identify known hot keys and give them their own partition (or even their own topic).

```python
CELEBRITY_USER_IDS = load_from_redis("celebrity_set")  # pre-populated, updated hourly

def get_kafka_key(user_id):
    if user_id in CELEBRITY_USER_IDS:
        # Route to dedicated "celebrity" topic with many partitions
        return f"celebrity:{user_id}"  # use a separate topic: "celebrity-events"
    return user_id

# Kafka topics:
# "user-events"        -- 6 partitions for normal users
# "celebrity-events"   -- 100 partitions for verified celebrities
# Celebrity consumers: more instances, more memory, dedicated cluster if needed

# Detecting new celebrities automatically:
# If user_id generates > X events/minute, add to celebrity_set in Redis
# Prometheus alert: if any partition has 10x the average event rate → alert
```

### Solution 3: Cell-Based Sharding (Database / Account Balances)

For databases where you need to spread a single hot entity across rows:

```sql
-- Problem: Alice makes 10K transactions/second (institutional trader).
-- All her writes go to one row in the accounts table.

-- Cell-based approach: split Alice across 10 "cells"
CREATE TABLE account_cells (
    account_id VARCHAR(50),
    cell_id    INT,           -- 0 to 9
    balance    DECIMAL(18,2),
    PRIMARY KEY (account_id, cell_id)
);

-- Write: randomly pick a cell
-- Java: int cell = ThreadLocalRandom.current().nextInt(10);
INSERT INTO account_cells (account_id, cell_id, balance)
VALUES ('alice', 7, 99.50)   -- random cell 7
ON CONFLICT (account_id, cell_id)
DO UPDATE SET balance = account_cells.balance + EXCLUDED.balance;

-- Read: aggregate all cells (10 rows instead of 1, but no single hot row)
SELECT account_id, SUM(balance) AS total_balance
FROM account_cells
WHERE account_id = 'alice'
GROUP BY account_id;
```

### Solution 4: Read Replicas + Local Cache (Cache Hot Keys)

For cache hot keys (viral product on Redis):

```java
@Component
public class ProductCacheService {

    private final RedisTemplate<String, Product> redis;

    // Local in-process cache: Caffeine (avoid Redis entirely for hottest keys)
    private final Cache<String, Product> localCache = Caffeine.newBuilder()
        .maximumSize(1000)          // top 1000 hottest products
        .expireAfterWrite(1, SECONDS)  // 1s TTL to stay fresh
        .build();

    public Product getProduct(String productId) {
        // Check local cache first (zero network, ~100ns)
        Product local = localCache.getIfPresent(productId);
        if (local != null) return local;

        // Check Redis (1ms)
        Product cached = redis.opsForValue().get("product:" + productId);
        if (cached != null) {
            localCache.put(productId, cached);
            return cached;
        }

        // DB fallback + cache population
        Product product = productRepository.findById(productId).orElseThrow();
        redis.opsForValue().set("product:" + productId, product, 5, MINUTES);
        localCache.put(productId, product);
        return product;
    }
}

// At 200K req/sec for product_G:
// - If 100 app instances, each handles 2K req/sec
// - Each instance caches product_G locally with 1s TTL
// - Redis gets at most 100 requests per second (one per instance per TTL refresh)
// - Redis is no longer the bottleneck
```

### Solution 5: Adaptive Rate Limiting / Backpressure

Detect and throttle hot partitions before they cause cascading failures:

```yaml
# Kafka Streams / consumer config:
max.poll.records: 100      # Process 100 records per poll, not 10K at once
fetch.max.wait.ms: 100     # Reduce poll interval
pause.on.lag: true         # Custom: pause consumer if lag grows too fast

# Application-level backpressure:
# If partition lag > 1M records: pause consumer on that partition, wake up when lag < 100K
# Prevents OOM: consumer doesn't try to process 50M messages at once
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your social media platform stores user events in Kafka, keyed by user_id. You notice one partition has 10x more lag than the others. What's happening and how do you fix it?"

**You (architect answer):**

> "This is a hot partition caused by a celebrity user — someone with disproportionately more activity than the average user. When you key Kafka messages by user_id, all events for that user hash to the same partition. If that user is Cristiano Ronaldo with 500 million followers, any action he takes fans out into hundreds of millions of events, all landing on one partition. The other partitions sit idle while partition 3 — or whichever partition Ronaldo hashes to — is overwhelmed.
>
> The immediate diagnosis: check `kafka-consumer-groups.sh --describe` sorted by lag. If one partition has 50 million lag and the others have 100K, you have a hot partition, not a capacity problem.
>
> The fix depends on how quickly you need to solve it. Short-term: scale up the consumer for that partition specifically. Assign it a dedicated consumer instance with higher thread count and memory.
>
> Long-term, I'd use a two-tier topic approach. I'd pre-identify verified celebrities (the set that changes rarely) and route their events to a separate `celebrity-events` topic with far more partitions — say 100 instead of 6. Normal users stay on the original topic with the original fan-out logic. Celebrity consumers are independently scalable.
>
> If I can't easily pre-identify hot keys, I'd add a salt: append a random integer 0-9 to the user_id before hashing. This distributes Ronaldo's events across all 10 partitions. The trade-off is losing strict per-user ordering — you'd need a sequence number in each event and re-sort on the consumer side if ordering matters.
>
> I'd also add monitoring at the partition level — alert when any single partition carries more than 5x the average event rate. Hot partitions always show up before they cause outages, if you're watching the right metrics."

---

## PART 5 — DECISION FRAMEWORK

### Hot Partition Mitigation by Layer

| Layer | Symptom | Root Cause | Solution |
|---|---|---|---|
| **Kafka** | One partition's consumer lag grows while others are flat | Skewed partition key (user_id, merchant_id) | Salt the key OR dedicated topic for hot keys |
| **Database shard** | One DB node at 95% CPU, others at 10% | Time-based shard key OR single high-traffic entity | Re-shard with hash(entity_id) OR cell-based sharding |
| **Cache (Redis)** | One Redis node saturated, others idle | Viral/trending item hashes to one node | Local in-process cache (Caffeine) for top N hot keys |
| **CDN/HTTP** | One origin server overwhelmed | Popular resource not cached | CDN caching + stale-while-revalidate |
| **Load balancer** | Sticky sessions → uneven node load | Session affinity sends users to same node | Round-robin OR IP-hash with session migration |

### Decision Tree: Which Fix to Apply

```
Is the hot key PREDICTABLE (celebrity users, large merchants, trending products)?
  YES ─→ DEDICATED PARTITION/SHARD
         Put hot keys in their own bucket with more resources
         E.g.: celebrity-events topic (100 partitions), vs normal-events (10 partitions)

  NO  ─→ Is the hot key TEMPORARY (viral content, flash sale)?
           YES ─→ LOCAL CACHE (in-process)
                  Cache hot items per app instance, TTL 1-5 seconds
                  Absorbs thundering herd without hitting downstream

           NO  ─→ Is ORDERING required per entity?
                    YES ─→ SALT + SEQUENCE NUMBER
                           Spread across N buckets, add sequence for re-ordering
                    NO  ─→ RANDOM SALT (simplest fix)
                           Append random(0..N) to partition key
                           Spreads load uniformly, no re-ordering needed

Is the hot partition at DATABASE LAYER?
  Time-based shard key? → Immediate problem, re-shard with hash(entity_id) ASAP
  Single entity too large? → Cell-based sharding (split entity across rows)
  Read-heavy hot shard? → Add read replicas for that shard specifically
```

### Numbers: When Does It Become a Problem?

```
Kafka partition throughput limits (rule of thumb):
  Single partition max: ~50MB/s write, ~150MB/s read
  Typical safe operating range: 10MB/s write, 30MB/s read
  If one partition > 5x average throughput → hot partition threshold

Redis single-node limits:
  ~500K simple ops/sec (GET/SET)
  ~200K complex ops/sec (ZRANGE, GEORADIUS)
  Network bandwidth: ~10Gbps on cloud instances
  If single key receives > 50K req/sec → local cache recommended

PostgreSQL single-shard limits:
  ~5K writes/sec with indexes (single table, typical workload)
  ~50K reads/sec with buffer pool hits
  If one shard > 3x average → re-shard or read replicas
```

---

## QUICK REFERENCE CARD

```
DETECTION:
  Kafka:  kafka-consumer-groups.sh --describe | sort by LAG descending
  DB:     SELECT ... FROM pg_stat_user_tables ORDER BY writes DESC
  Redis:  redis-cli --hotkeys (requires maxmemory-policy allkeys-lru)
  Rule:   Any partition with > 5x average traffic = hot partition

SOLUTIONS BY SPEED OF FIX:
  Immediate (no code change):
    - Scale up consumer for hot partition (more threads/memory)
    - Add read replicas to hot DB shard
    - Enable local Caffeine cache in app instances

  Short-term (small code change):
    - Salt partition key: key = userId + "_" + random(0..9)
    - Local in-process cache with 1-5s TTL for top N keys

  Long-term (architectural):
    - Dedicated topic/shard for pre-identified hot entities
    - Cell-based sharding for database hot rows
    - Separate scaling tier (celebrity-events, large-merchant-payments)

KEY TRADE-OFF OF SALTING:
  Before: all events for user X in one partition → ordering guaranteed
  After:  events for user X spread across N partitions → ordering lost
  Fix:    add sequence number to event, sort on consumer side
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** In any system design interview, after you propose a sharding strategy, the interviewer will push: "what happens when one user/entity generates far more traffic than others?" The answer is hot partition, and you should proactively mention it before they ask.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **05 — Social Media** | Celebrity users generate 1000x more events than average (post → 500M fan feed updates). Keying Kafka by user_id means one partition drowns on celebrity activity. Solution: detect verified celebrities in real-time via event rate monitoring, route their events to a dedicated high-throughput topic with 10x more partitions and dedicated consumer scaling. |
| **07 — Payment** | Large merchants (Amazon, Apple Pay) generate 1000x more payment transactions than a small shop. Merchant_id as a Kafka partition key creates a hot partition on large-merchant events. Solution: sub-partition large merchants by payment_type or apply a random salt, with compensating aggregation in the consumer to reconstruct merchant-level views. |
| **13 — Leaderboard** | The top-ranked player may have 100x more score update events than average players (popular streamer, tournament winner). Redis ZINCRBY handles concurrent updates well (single-threaded command, atomic). But the Kafka topic that feeds Redis scores — if keyed by player_id — will have a hot partition for the top player. Monitor partition lag as a leading indicator. |

**Architect's one-liner for the interview:**
*"The hot partition problem is where your load distribution assumption fails — you assumed uniform traffic per key but got power-law distribution, so you fix it either by splitting the hot key across multiple partitions with a salt or by giving predictably hot entities their own dedicated partition tier that can scale independently."*

---
