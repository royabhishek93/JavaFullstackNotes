# Interview Guide: Top-K / Leaderboard / Trending System

> Design a real-time dashboard to track top players, ranks, scores across games, regions, and time windows with instant updates.

---

## 1. Clarify Requirements (say this out loud)

### Functional
| # | Requirement |
|---|-------------|
| 1 | Insert / update / delete entries (video, song, player, post) |
| 2 | Query top-K by score/rank, filterable by region/group |
| 3 | Time-windowed rankings: day / week / month |
| 4 | All-time rankings |
| 5 | Real-time updates — leaderboard must feel live |

### Non-Functional
| Dimension | Target |
|-----------|--------|
| Scale | 1M events/sec, billions of entities globally |
| Query latency | ≤ 100ms for top-K result |
| Update lag | < 1 second (soft real-time) |
| Consistency | Availability >> Consistency (eventual OK) |
| Accuracy | Minor rank errors tolerable (rank 100 vs 101 acceptable for trending) |

---

## 2. Core Entities

```
Score/View/Like     → the metric being tracked (game score, video views, song plays)
Player/Video/Song   → the entity being ranked
TimeFrame           → hour / day / week / month (the window)
```

---

## 3. API Design

```
# Record a score event
POST /api/v1/scores/view
Body: { entity_id, user_id, timestamp, region, category }

# Get top-K with filters (REST or WebSocket for live push)
GET  /api/v1/leaderboards/{leaderboard_id}/top
     ?window=daily&region=US&limit=10    ← pagination
WS   /ws/leaderboards/{leaderboard_id}/top   ← real-time push (optional)

# Get a specific entity's rank
GET /api/v1/leaderboards/{leaderboard_id}/rank/{entity_id}
    ?window=monthly
```

---

## 4. High-Level Design (from diagram)

```
Clients/Users
    │
    ▼
API Gateway & Load Balancer
  (Auth, Authorization, Routing, Rate Limiting)
    │               │
    ▼               ▼
Score Svc       Ranking Svc
    │               │
    ▼               ▼
Score DB  ←────  Redis ZSET / DB
```

**Score Service** — validates events, deduplicates, publishes to Kafka  
**Ranking Service** — consumes Kafka, maintains Redis ZSET, serves read queries  
**Score DB** — persistent source of truth for all score events

### Score Event Ingestion — Step-by-Step Trace

```
1. Client sends:  POST /api/v1/scores/view
   Body: { video_id: 'V123', user_id: 'U456', timestamp: now(),
           metadata: { region: 'US', category: 'music' } }

2. Score Service validates:
   a) Check entity exists
   b) Check user is authenticated
   c) Dedup check (prevent same user double-counting in 5 min):
        Redis GET view_dedup:U456:V123
          → exists?  → return 200 OK, ignore (already counted)
          → missing? → SET view_dedup:U456:V123 1 EX 300

3. Publish to Kafka topic 'score.updated':
   { event_id: uuid(), entity_id: 'V123', score_delta: +1,
     timestamp, region: 'US', category: 'music' }
   Partition key: entity_id hash
   → all events for V123 go to same partition → ordering preserved

4. Return 200 OK immediately (async — don't wait for leaderboard update)
```

---

## 5. Deep Dive — Three Approaches (from diagram)

### Approach 1: Redis Sorted Set (ZSET)

```
Clients → API GW → Score Svc → Kafka → Redis Consumer Svc
                                  │
                                  ▼
                             Redis Sorted Set/ZSET
                          leaderboard:music:IN:alltime
                          leaderboard:music:IN:90days
                          leaderboard:music:IN:30days
                                  │
                              Ranking Svc ← reads
```

**Key Redis Commands:**
```
# Write (O(log N))
ZINCRBY leaderboard:global:alltime 1 V123

# Read top-K (O(log N + K))
ZREVRANGE leaderboard:global:alltime 0 9 WITHSCORES

# Get rank (O(log N))
ZREVRANK leaderboard:global:alltime V123
```

**Time-windowed keys with TTL:**
```
leaderboard:global:daily:2026-01-25    → TTL 7 days
leaderboard:global:weekly:2026-W04     → TTL 90 days
leaderboard:global:monthly:2026-01     → TTL 365 days
leaderboard:global:alltime             → no TTL
```

| Pros | Cons |
|------|------|
| Every rank available instantly (<1ms) | Memory-only (crash = data loss) |
| Atomic ZINCRBY (thread-safe) | Hard to scale beyond single node |
| O(log N) for all operations | No historical time-series queries |
| 10M entries ≈ 1 GB | Complex multi-dimensional = key explosion |

**When to use:** Real-time leaderboards (gaming, live sports), scale <100M entities, low latency critical (<10ms), simple time windows.

---

### Regional & Category Leaderboards

**Multi-dimensional keys:**
```
ZINCRBY leaderboard:US:alltime 1 V123           ← region only
ZINCRBY leaderboard:music:alltime 1 V123        ← category only
ZINCRBY leaderboard:music:US:alltime 1 V123     ← combined
ZINCRBY leaderboard:music:US:daily:2026-01-25 1 V123  ← combined + time
```

**Key explosion problem:**
```
5 regions × 10 categories × 4 time windows = 200 leaderboards
× 1 GB per leaderboard = 200 GB Redis (expensive!)

Fix:
  1. Lazy init — create key only when first score arrives
  2. EXPIRE unused keys after 30 days of no updates
  3. Separate Redis cluster per region to isolate load
```

**Query:**
```
ZREVRANGE leaderboard:music:US:alltime 0 9   ← top music in US
ZREVRANGE leaderboard:music:IN:90days 0 9    ← top music in India, 90-day window
```

---

### Approach 2: PreComputed Batch + TimeseriesDB (InfluxDB)

```
Clients → API GW → Score Svc → Kafka → Flink (stream processor)
                                           │
                                    ┌──────┴──────┐
                                    ▼             ▼
                              Aggregated DB   TimeseriesDB
                              (Spanner /      (InfluxDB)
                               Cassandra /
                               BigQuery)
                                    │
                              Ranking Svc ← cache layer ← reads
```

**Batch job flow (e.g. cron at 2 AM):**
```sql
SELECT entity_id, SUM(views) as total
FROM video_views
WHERE timestamp >= '2026-01-01'
GROUP BY entity_id
ORDER BY total DESC
LIMIT 1000
```
→ Write to `leaderboard_snapshots` table  
→ Cache in Redis: `SET leaderboard_cache:global:monthly:2026-01 {json} EX 86400`

**InfluxDB schema:**
```
Measurement: entity_scores
Tags:         entity_id, region, category   ← indexed
Fields:       views_count, likes_count, score
Timestamp:    nanosecond precision
Retention:    1-min data: 7d → 1-hour data: 90d → 1-day data: forever

Write:
  INSERT video_scores,video_id=V123,region=US views_count=1000,score=1500 <ts>

Query top-K last 24h:
  SELECT SUM(views_count) FROM video_scores
  WHERE time > now() - 24h
  GROUP BY video_id ORDER BY SUM DESC LIMIT 10
```

**Continuous query for auto-downsampling:**
```sql
CREATE CONTINUOUS QUERY cq_hourly ON leaderboard BEGIN
  SELECT SUM(views_count) INTO video_scores_hourly
  FROM video_scores GROUP BY time(1h), video_id
END
-- keeps 1-min raw data for 7 days, hourly aggregates for 90 days
```

**Bitmap approach (space-efficient membership):**
```
Instead of storing full scores, use a bitmap per leaderboard bucket:
  Bucket = bitmap per top-K band (top-100, top-1000)
  Bit set → entity IS in that bucket
  1 MB bitmap covers 8M entity IDs
  Use case: "Is V123 in top-1000?" — yes/no in O(1), tiny memory
```

| Pros | Cons |
|------|------|
| Historical trend analysis | Leaderboard can be stale (hours) |
| Efficient compressed storage | Slower queries (~100ms vs <1ms) |
| Complex queries (percentiles, moving avg) | Requires Flink + InfluxDB + cron |
| Minimal read latency after pre-compute | Not real-time |

**When to use:** Analytics dashboards, historical leaderboards (top songs each month for past year), large-scale time-series, when exact real-time ranking not critical.

---

### Approach 3: Hybrid (Redis + Kafka + DB) — BEST PRACTICE

```
Clients → API GW → Score Svc → Kafka
                                  │
                    ┌─────────────┼────────────────┐
                    ▼             ▼                 ▼
             DB Consumer    Redis Consumer      Analytics
                Svc              Svc             Consumer
                    │             │
                    ▼             ▼
               Score DB      Redis Sorted        Flink
            (Spanner /        Set/ZSET              │
            Cassandra /    leaderboard keys         ▼
            BigQuery)           │             Aggregated DB
                    │           │             (TimeseriesDB)
                    └─────── Ranking Svc ────────────┘
                                  │
                             reads: Redis (hot)
                             fallback: DB (cold)
```

**Write path:**
```
Score event → Kafka 'score.updated'
   ├── Redis Consumer:  ZINCRBY leaderboard:global:alltime 1 V123   (<100ms lag)
   └── DB Consumer:     INSERT INTO scores (entity_id, score_delta, ...) (~1s lag)
```

**Read path:**
```
GET /api/v1/leaderboards/global/top?limit=10
   1. Try Redis: ZREVRANGE leaderboard:global:alltime 0 9  → <1ms
   2. If miss:   SELECT ... GROUP BY ... ORDER BY ... LIMIT 10  → ~100ms
   3. Rebuild Redis from DB if needed (~10 min for 10M entries)
```

| Pros | Cons |
|------|------|
| Redis reflects score changes instantly | Complex (Kafka + Redis + DB = 3 systems) |
| No data loss (Kafka + DB persistence) | Redis consumer lag → stale leaderboard |
| All components scale independently | Cache miss → slower DB fallback |
| TTL on keys → auto-expire old leaderboards | |

**When to use:** Production at scale (millions of users), need both real-time + persistence, multi-dimensional leaderboards (regional, category, time windows), critical data that can't be lost.

---

## 6. Database Schema

### Score DB (persistent)
```sql
CREATE TABLE scores (
  score_id     UUID PRIMARY KEY,
  entity_id    VARCHAR(100),       -- video_id / player_id / song_id
  score_delta  INT,                -- +1 view, +10 like
  leaderboard_id VARCHAR(100),     -- 'global', 'US', 'music'
  region       VARCHAR(10),
  category     VARCHAR(50),
  timestamp    TIMESTAMPTZ,
  metadata     JSONB               -- user_id, device_type, etc.
);
-- Indexes
CREATE INDEX ON scores (leaderboard_id, timestamp);
CREATE INDEX ON scores (entity_id);
-- Shard by entity_id hash (10 shards)
```

### Leaderboard Snapshots (pre-computed, batch approach)
```sql
CREATE TABLE leaderboard_snapshots (
  leaderboard_id VARCHAR(100),     -- 'global_daily_2026-01-25'
  rank           INT,
  entity_id      VARCHAR(100),
  score          BIGINT,
  snapshot_date  DATE,
  PRIMARY KEY (leaderboard_id, rank)
);
```

### Redis ZSET Key Taxonomy
```
leaderboard:global:alltime              → permanent
leaderboard:global:daily:{YYYY-MM-DD}  → TTL 7 days
leaderboard:global:weekly:{YYYY}-W{WW} → TTL 90 days
leaderboard:global:monthly:{YYYY-MM}   → TTL 365 days
leaderboard:{region}:alltime           → e.g. leaderboard:US:alltime
leaderboard:{category}:alltime         → e.g. leaderboard:music:alltime
leaderboard:{category}:{region}:alltime → e.g. leaderboard:music:IN:alltime
leaderboard:trending                   → TTL 24h, updated hourly
```

### Aggregated DB (Spanner / Cassandra / BigQuery — Batch Approach)
```sql
CREATE TABLE aggregated_scores (
  entity_id      VARCHAR PRIMARY KEY,
  total_score    BIGINT,           -- sum of all score deltas (all-time)
  daily_score    BIGINT,           -- sum for today, reset daily
  weekly_score   BIGINT,           -- sum for this week
  monthly_score  BIGINT,           -- sum for this month
  last_updated   TIMESTAMP
);
-- Batch jobs aggregate scores here → Ranking Svc queries for pre-computed top-K
```

### Kafka Topics
```
Topic:           score.updated
Partition key:   entity_id hash  (100 partitions)
                 → ensures all events for same entity → same partition → ordered

Consumer groups:
  redis-consumer     → updates Redis ZSET in real-time
  db-consumer        → persists raw events to Score DB
  analytics-consumer → writes to InfluxDB / aggregated DB

Message schema:
  { event_id, entity_id, score_delta, timestamp, region, category }
```

---

## 7. Key Deep-Dive Topics

### Score Deduplication (prevent double-counting)
```
On view event: Redis GET view_dedup:{user_id}:{entity_id}
  → exists?   ignore (already counted within 5 min)
  → missing?  SET view_dedup:{user_id}:{entity_id} 1 EX 300
              → then publish to Kafka
```

### Score Ties — 4 Approaches

**Approach 1 — Timestamp tiebreaker (most common):**
```
Store score as float: score + (timestamp / 1e12)
  Player A: 1000 pts at t=100  → 1000.0000000001  (smaller float)
  Player B: 1000 pts at t=200  → 1000.0000000002
  → Player A ranks higher (reached score first)
```

**Approach 2 — Lexicographic (automatic in Redis):**
```
ZADD leaderboard 1000 V123   (score only, no float trick)
Redis ZSET: when scores equal → sorts members alphabetically
  V123 < V456 → V123 ranks higher
  Deterministic but semantically arbitrary
```

**Approach 3 — Composite / Secondary score:**
```
composite = primary_score × 1_000_000 + secondary_score
Example: views × 1_000_000 + likes
  Video A: 1000 views, 50 likes  → 1_000_050_000
  Video B: 1000 views, 30 likes  → 1_000_030_000
  → Video A ranks higher (more likes as tiebreaker)
ZADD leaderboard 1000050000 V123
```

**Approach 4 — Random (for trending lists where order doesn't matter):**
```
Store: score + random(0, 1)  e.g. 1000 + 0.5 = 1000.5
Non-deterministic: same query may return different order for tied items
Use when: trending lists, approximate rankings
```

### Time-Decay / Trending Algorithm

**Hacker News formula (gravity=1.5):**
```
trending_score = engagement_score / (age_in_hours + 2)^1.8

engagement_score = views + (likes×10) + (comments×20) + (shares×30)

Example:
  Video A: 10M views, 7 days old  → score ≈ 13,895
  Video B: 500K views, 3 hours old → score ≈ 95,763
  → Video B ranks HIGHER (trending)
```

**Reddit Hot algorithm (alternative):**
```
hot_score = log10(ups - downs) + (age_in_seconds / 45000)
  Logarithm → diminishing returns (10→100 votes matters less than 1→10)
  Linear time decay → older posts drop steadily
  Use when: engagement matters more than recency (stable front page)
```

**Batch vs Real-time decay trade-off:**
```
Batch (recommended):
  Cron runs hourly → recalculate for videos from last 7 days only
  SQL: SELECT entity_id,
            view_count / POW(EXTRACT(EPOCH FROM (NOW()-created_at))/3600 + 2, 1.5)
            AS trending_score
       FROM videos WHERE created_at > NOW() - INTERVAL '7 days'
  → Write to Redis:
      DEL leaderboard:trending                         ← clear old list
      ZADD leaderboard:trending {score} {entity_id}   ← write new top-1000
      EXPIRE leaderboard:trending 7200                 ← 2h TTL safety net
                                                         (if next batch job fails,
                                                          stale list expires itself)
  → Expire low-score entries: ZREMRANGEBYSCORE leaderboard:trending -inf {threshold}
  Staleness: up to 1 hour (acceptable)

Incremental (optimization):
  Instead of full recompute every hour, only process videos with new engagement
  in the last hour (Kafka stream: consume view/like events, update score real-time)
  Reduces compute from O(7M videos) → O(new events per hour)

Real-time on read (avoid at scale):
  Store (raw_count, timestamp) in ZSET as float score
  On ZREVRANGE: fetch entries, compute decay per item, re-sort
  Always fresh but: expensive CPU per query at 1M QPS
```
Run batch on last 7 days only — older videos are excluded from trending.

### Weekly Aggregation from Daily ZSETs
```
ZUNIONSTORE leaderboard:global:weekly:2026-W04 7
    leaderboard:global:daily:2026-01-19
    leaderboard:global:daily:2026-01-20
    ... (7 daily keys)
    WEIGHTS 1
```

### Probabilistic Structures (when approximate is OK)
| Structure | Use Case | Size | Error |
|-----------|----------|------|-------|
| Count-Min Sketch | Approximate view counts for trending | 1 MB → billions of items | Overestimates only, never under |
| HyperLogLog | Count distinct viewers (cardinality) | 12 KB | <2% |
| Bloom Filter | "Is entity in top-K?" membership test | 1 MB for 10M items | 1% false positive |

**Heavy Hitters — Count-Min Sketch + Min-Heap (Top-K approximation):**
```
Maintain in-memory: Count-Min Sketch (estimates counts) + Min-Heap (size = K)

On each score event:
  1. Hash entity_id → multiple positions in sketch, increment counters
  2. estimated_count = min of those counters
  3. If estimated_count > heap.min → replace heap.min with entity_id

Query top-K:
  Return heap contents (approximate top-K)

Stats:
  Memory: 1 MB sketch vs 1 GB exact Redis ZSET → 1000× less
  Accuracy: 95% overlap with exact top-K
  Use for: Trending topics, viral videos, real-time dashboards
```

**When to use probabilistic:** Pre-compute only leaderboards for dimensions users are likely to query — don't compute every combination.

### Pagination
```
# Offset-based (supports random page jump)
ZREVRANGE leaderboard:global:alltime 1000 1009 WITHSCORES   O(log N + offset + K)

# Cursor-based (stable during leaderboard updates)
First page:  ZREVRANGE leaderboard:global:alltime 0 9 WITHSCORES
             → cursor = last item's score
Next page:   ZREVRANGEBYSCORE leaderboard:global:alltime {cursor} -inf LIMIT 0 10
Advantage:   Consistent even if scores change between page requests
Disadvantage: Can't jump to arbitrary page

# User's rank + surrounding context
ZREVRANK  → rank=49999
ZREVRANGE leaderboard:global:alltime 49994 50003   (5 above + user + 4 below)

# Get a specific entity's score
ZSCORE leaderboard:global:alltime V123   → O(1)

# Percentile (e.g. "Top 1%?")
total = ZCARD leaderboard:global:alltime
percentile = (rank / total) × 100

# Infinite scroll
Client tracks offset: 0 → 10 → 20 → 30 (as user scrolls)
Stop: when ZREVRANGE returns < limit items → end of leaderboard
```

### Response Enrichment (MGET pattern)
```
After ZREVRANGE returns [V123, V456, V789, ...]:

# Batch-fetch entity metadata in ONE round trip
MGET entity:V123 entity:V456 entity:V789 ...   ← 1ms

If any cache miss → DB fallback:
  SELECT title, thumbnail, channel FROM videos WHERE video_id IN (...)

Total read latency breakdown:
  1ms  ZREVRANGE (top-K from Redis)
  5ms  MGET (batch metadata fetch)
  2ms  serialization
  ─────────────────────────────
  <10ms total end-to-end
```

---

## 8. Scaling Techniques

| Technique | How |
|-----------|-----|
| Redis Cluster | Shard by leaderboard_id (16384 slots via CRC16), 10 nodes (5 masters + 5 replicas) = 10 GB total |
| Kafka partitioning | 100 partitions by entity_id hash → 100 parallel consumers → 1M events/sec |
| DB sharding | Shard scores table by **entity_id hash** (10 shards) — NOT by score (score-based sharding = hotspot: all top players land on same shard). Each shard scans 1M vs 10M rows; cross-shard aggregation via batch jobs |
| Read replicas | 5 Redis replicas per master (5× read capacity); 3 DB replicas for leaderboard queries |
| App-level cache | Cache top-100 in app memory, refresh every 10 sec (serves 90% from RAM, no Redis RTT) |
| CDN | Cache API responses at edge (1 min TTL) → <50ms globally |
| Lazy initialization | Create leaderboard key only on first score, expire after 30 days of inactivity |
| Redis pipelining | `PIPELINE; ZINCRBY ...; ZINCRBY ...; EXEC` → multiple ZSETs in 1 network RTT instead of N |
| Batch ZADD | `ZADD leaderboard score1 id1 score2 id2 ... (100 items)` → 1 command vs 100 → 100× fewer round trips |
| Lua scripting | `EVALSHA` to update multiple ZSETs atomically (prevents partial update if one fails): `ZINCRBY global +1 V123; ZINCRBY US +1 V123; ZINCRBY music +1 V123` all or nothing |
| ZUNIONSTORE | Combine 7 daily ZSETs → weekly in single atomic command |
| Connection pooling | 50 Redis connections + 50 DB connections per app instance, reused across requests |
| Materialized views | `CREATE MATERIALIZED VIEW top_1000_daily` refresh hourly, instant queries |

**Key Explosion Problem:**
```
5 regions × 10 categories × 4 time windows = 200 leaderboards × 1 GB = 200 GB
Fix: Lazy init + expire unused keys after 30 days
```

---

## 9. Approach Comparison

| | Redis ZSET | Batch + InfluxDB | Hybrid (Best) |
|--|------------|-----------------|---------------|
| Latency | <1ms | ~100ms | <1ms (Redis) |
| Persistence | No (in-memory) | Yes | Yes (DB) |
| Historical | No | Yes | Yes |
| Real-time | Yes | No | Yes |
| Complexity | Low | Medium | High |
| Scale | Up to ~10 GB/node | Very large | Unlimited |
| Use when | Gaming, live sports | Analytics dashboards | Production at scale |

**Decision Rule:**
- Need <10ms latency + small scale → Redis ZSET
- Need historical analysis → InfluxDB
- Production + millions of users → Hybrid

---

## 10. Monitoring

**Metrics & alerts:**
| Signal | Alert Threshold |
|--------|----------------|
| Kafka consumer lag | > 1 minute (leaderboard going stale) |
| Redis memory | > 80% (eviction risk) |
| Query latency p99 | > 100ms |
| Cache hit rate | < 90% |
| Redis top-100 vs DB top-100 mismatch | > 5 items (nightly consistency check) |
| DB replication lag | > 10 sec (reads may be stale) |
| Batch job duration | > 2× normal time → alert |

**Dashboards:**
```
1. Real-time: current top-10 per leaderboard (visual sanity check)
2. Lag: Kafka consumer lag graph over time
3. Traffic: requests/sec per leaderboard endpoint
4. Errors: 5xx rate, timeout rate
```

**Component alerts:**
```
Redis cluster: 1 node down → auto-failover to replica + alert
Kafka: partition offline → alert (data loss risk)
Batch jobs: failure or > 2× normal duration → alert
Consistency: nightly job compares Redis top-100 vs DB top-100
             mismatch > 5 items → alert (corruption or lag)
Sampling: random 1% of scores verified Redis matches DB
```

**Load testing targets:**
```
Score updates:  1M req/sec (Kafka load test)
Leaderboard reads: 100K req/sec (Redis load test)
Measure: latency at p50 / p90 / p99 / p99.9 + error rate
Capacity headroom: system handles 1M req/sec vs current 100K → 10× buffer
```

---

## 11. Disaster Recovery

**Scenario: Redis cluster crashes — all ZSET data lost**

```
Step 1: Detect via monitoring (Redis node down alert)
Step 2: Serve reads from DB fallback during rebuild
        SELECT entity_id, SUM(score_delta) as total_score
        FROM scores
        WHERE timestamp > NOW() - INTERVAL '7 days'
        GROUP BY entity_id

Step 3: Rebuild Redis from DB results
        FOR EACH row:
          ZADD leaderboard:global:weekly:{YYYY-W{WW}} {total_score} {entity_id}

Step 4: Rebuild time → ~10 minutes for 10M entries (acceptable)
```

**Prevention:**
```
Enable Redis RDB snapshots every 5 min → reduces rebuild scope
Enable AOF (append-only file) → near-zero data loss on crash
Redis Cluster replicas: auto-failover to replica if master dies
Nightly reconciliation: compare Redis top-100 vs DB top-100
```

---

## 12. Key Numbers to Memorize

| Metric | Value |
|--------|-------|
| Redis ZSET memory per entry | ~100 bytes |
| 10M entries | ~1 GB per ZSET |
| ZINCRBY / ZREVRANGE / ZREVRANK | O(log N) |
| Top-100 query in Redis | <1ms even at 10M entries |
| Kafka: 100 partitions × 10K/sec | = 1M events/sec |
| Redis rebuild after crash | ~10 min for 10M entries |
| Trending batch job | Hourly, last 7 days eligible |
| Daily leaderboard TTL | 7 days |
| Weekly leaderboard TTL | 90 days |
| Monthly leaderboard TTL | 365 days |
| Key explosion | 5 regions × 10 categories × 4 windows = 200 leaderboards × 1 GB = 200 GB |
| Count-Min Sketch vs exact Redis | 1 MB vs 1 GB — 1000× less memory, 95% accurate |

---

## 13. Top Interview Q&A

**Q: Redis vs Database for leaderboards?**
> Redis ZSET = <1ms but volatile (in-memory). DB = persistent but slow (~100ms rank scan). **Hybrid = Redis reads + Kafka events + DB writes** = industry standard.

**Q: How do you handle millions of score updates/sec?**
> Kafka (100 partitions × 10K/sec = 1M/sec) → 100 Redis consumers (1 per partition) → each does `ZINCRBY` (O(log N), <1ms). Scale by adding partitions. Auto-scale consumers: if Kafka lag > 1 min → add more consumer instances. Use Redis pipelining + Lua scripts to update multiple ZSETs (global, regional, daily) atomically in 1 RTT.

**Q: How do you get a user's rank fast?**
> `ZREVRANK leaderboard:global:alltime P123` — O(log N), <1ms. `ZSCORE` gets their score in O(1). Never use `SELECT COUNT(*) WHERE score > X` in DB — O(N) scan, ~500ms for 10M rows. Percentile: `rank / ZCARD leaderboard × 100`.

**Q: How does trending work (YouTube style)?**
> `trending_score = engagement / (age_hours + 2)^1.8` where `engagement = views + likes×10 + comments×20 + shares×30`. New viral video (3h, 500K views) scores ~95K; old popular (7d, 10M views) scores ~14K. Hourly batch: `DEL leaderboard:trending` → `ZADD` top-1000 → `EXPIRE 7200` (2h safety TTL if next batch fails). Alternative: Reddit Hot — `log10(engagement) + (age_seconds / 45000)`. Personalized: `personalized_score = trending_score × (1 + category_affinity)`.

**Q: What happens if Redis crashes?**
> Rebuild from DB: `SELECT entity_id, SUM(score_delta) FROM scores GROUP BY entity_id` → `ZADD`. Takes ~10 min for 10M entries. Enable RDB snapshots (every 5 min) to reduce rebuild time. Serve DB fallback reads during the rebuild window.

**Q: How do you handle score ties?**
> 4 options: (1) Timestamp float: `score + ts/1e12` — deterministic, most common. (2) Lexicographic: Redis default when scores equal. (3) Composite: `views × 1M + likes` — semantically meaningful tiebreaker. (4) Random: `score + rand(0,1)` — for trending lists where order doesn't matter.

**Q: How do you prevent key explosion with multi-dimensional leaderboards?**
> Lazy initialization (create key only on first score event) + `EXPIRE` unused keys after 30 days + separate Redis cluster per region. Only pre-compute dimensions users actually query.

**Q: How do you aggregate daily → weekly leaderboards?**
> `ZUNIONSTORE leaderboard:global:weekly:2026-W04 7 leaderboard:daily:Mon ... leaderboard:daily:Sun WEIGHTS 1` — single atomic Redis command, runs every Monday at midnight.

---

## 14. Production Examples

| Product | Approach | Scale |
|---------|----------|-------|
| Fortnite / PUBG | Hybrid — Redis real-time + DB persistence | 250M+ players, 100+ Redis nodes, 1000+ Kafka partitions, sub-10ms queries |
| Spotify Top 50 | Batch + Redis cache — daily batch compute, not real-time | Millions of songs, cached top-1000 per region |
| YouTube Trending | Time-decay + Redis — hourly recompute, cache top-100 | Regional + category trending, human moderation, ML personalization |
| Twitter Trends | Count-Min Sketch — approximate counts, probabilistic top-K | Real-time, approximate OK, ~1h staleness acceptable |
