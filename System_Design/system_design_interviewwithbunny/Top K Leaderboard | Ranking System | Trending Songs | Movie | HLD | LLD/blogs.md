Leaderboard / Top-K / Trending List

"Score events → Kafka → Redis ZSET (real-time top-K) + DB (persistence) → Periodic batch jobs (regional/time-based rankings) → Hybrid: Redis for reads, DB for historical consistency"

1. Functional Requirements

Feature 1: User should be able to insert/update/delete data into our list (video/song/leaderboard/E-dynamic list)
Feature 2: User should be able to query: Top 10 player by score/rank (in case of leaderboard) based on region/group
Feature 3: Time periods should be limited by: day, week, month (leaderboard for different time windows)
Feature 4: User should be able to see all-time rankings in addition to time-bounded rankings
Feature 5: User should get real-time updates (no stale leaderboard data - <1 second latency for top-K)
2. Non-Functional Requirements

Scale
Events — 1M req/sec - billions of songs/videos/players globally
Users — Hundreds of millions querying leaderboards, trending lists simultaneously
Performance & Consistency
CAP Theorem — Availability >> Consistency (eventual consistency acceptable for leaderboards)
Latency — 100ms to get the top-K result, near real-time updates with <1 second lag (to give a soft-real time update)
Accuracy — Return accurate trending list/rank probabilistic (minor ranking errors tolerable, e.g., rank 100 vs 101 acceptable)
3. Core Entity (from image)

Entity 1: Score/View/Like - Metric being tracked (game score, video views, song plays, post likes)
Entity 2: Player/Video/Song - Entity being ranked (user in game, video on platform, song on music app)
Entity 3: TimeFrame (hour/day/week/month) - Time window for rankings (daily leaderboard, weekly trending, monthly top songs)
4. API Designing (from image)

Score Updates
POST /api/v1/scores/view — Record a view/play event for video/song (increments score)
GET /api/v1/leaderboards/{leaderboard_id}/top?window=daily&region=US&limit=10 (Pagination) — Get top-K entries for specific leaderboard with filters (time window, region, limit)
GET /leaderboards/{leaderboard_id}/rank/{user_id}?window=monthly&> (Pagination) — Get user's rank in leaderboard for specific time window
5. High Level Design (from image)

Clients/users → API Gateway & Load Balancer: Authentication, authorization, routing, rate limiting
Score Service: Handles score updates (views, likes, game scores), validates and publishes events
Ranking Service: Computes top-K rankings, serves read queries, manages Redis ZSET for real-time rankings
Score DB: Persistent storage for all score events (historical data, source of truth)
Kafka: Event streaming for score updates, decouples write path from ranking computation
From image shows three approaches: (1) Redis Sorted Set/ZSET, (2) TimeSeriesDB (InfluxDB), (3) Hybrid Approach
6. Deep Dive Design (Low Level - from image)

Step 1: Score Event Ingestion
User watches video: Client sends: POST /api/v1/scores/view with {video_id: 'V123', user_id: 'U456', timestamp: now(), metadata: {region: 'US', category: 'music'}}
Score Service validates: (1) Check video exists, (2) Check user authenticated, (3) Dedup: Check if same user viewed in last 5 min (prevent double-counting spam), Redis: GET view_dedup:{user_id}:{video_id}, if exists → ignore (already counted), else SET view_dedup:{user_id}:{video_id} 1 EX 300 (5 min TTL)
Publish to Kafka: 'score.updated' topic: {event_id: uuid(), video_id: 'V123', score_delta: +1, timestamp, region: 'US', category: 'music'}
Response: 200 OK (async processing, don't wait for leaderboard update)
Kafka partitioning: Partition by video_id hash (ensures all events for same video go to same partition → ordering preserved)
Step 2: Approach 1 - Redis Sorted Set (ZSET) [from image shows 'Redis Sorted Set/ZSET']
From image: '1. Redis Sorted Set (sorted_set), One Sorted_Set (sorted = < id, score> pairs, sorted), leaderboard:music:IN:alltime, leaderboard:music:IN:90days'
Ranking Service consumes Kafka: 'score.updated' event: {video_id: 'V123', score_delta: +1, region: 'US', timestamp}
Update Redis ZSET: (1) All-time leaderboard: ZINCRBY leaderboard:global:alltime 1 V123 (increments V123's score by 1), (2) Daily leaderboard: ZINCRBY leaderboard:global:daily:{YYYY-MM-DD} 1 V123, (3) Regional leaderboard: ZINCRBY leaderboard:US:alltime 1 V123, (4) Category leaderboard: ZINCRBY leaderboard:music:alltime 1 V123
From image note: 'One redis Set (sorted = < id, more> pairs, sorted)' - ZSET stores (member, score) pairs sorted by score
Query top-K: User requests: GET /api/v1/leaderboards/global/top?limit=10, Ranking Service: ZREVRANGE leaderboard:global:alltime 0 9 WITHSCORES (get top 10 with scores, reverse order = highest first), Response: [{video_id: 'V123', score: 1000000}, {video_id: 'V456', score: 950000}, ...], Time complexity: O(log(N) + K) where N = total items, K = limit (very fast, ~1ms for 10M items)
Get user's rank: GET /api/v1/leaderboards/global/rank/V123, Ranking Service: ZREVRANK leaderboard:global:alltime V123 (returns 0-based index, e.g., 42 → rank #43), Response: {video_id: 'V123', rank: 43, score: 500000}
From image: 'Pro: Every rank and data', 'Con: Complete expensive (no need to keep in single node + not possible for 'ideal depth')'
Memory: (1) Each entry: ~100 bytes (video_id + score + ZSET overhead), (2) 10M entries: ~1 GB per leaderboard, (3) Multiple leaderboards (global, regional, daily, weekly, monthly): 5 leaderboards × 1 GB = 5 GB (manageable in Redis)
Step 3: Time-Windowed Leaderboards (Daily/Weekly/Monthly)
From image: 'Time periods should be limited by: day, week, month (leaderboard for different time windows)'
Daily leaderboard: (1) Key format: leaderboard:global:daily:{YYYY-MM-DD}, example: leaderboard:global:daily:2026-01-25, (2) TTL: EXPIRE leaderboard:global:daily:2026-01-25 604800 (7 days = 1 week TTL, auto-delete old daily leaderboards), (3) Update: ZINCRBY leaderboard:global:daily:2026-01-25 1 V123 on every view
Weekly leaderboard: (1) Key format: leaderboard:global:weekly:{YYYY}-W{WW}, example: leaderboard:global:weekly:2026-W04 (week 4 of 2026), (2) TTL: 90 days (keep last ~13 weeks), (3) Update: Same ZINCRBY on weekly key
Monthly leaderboard: (1) Key format: leaderboard:global:monthly:{YYYY-MM}, example: leaderboard:global:monthly:2026-01, (2) TTL: 365 days (keep last 12 months), (3) Update: ZINCRBY on monthly key
All-time leaderboard: (1) Key: leaderboard:global:alltime, (2) No TTL (never expires), (3) Grows indefinitely (pagination essential)
Query with time window: User requests: GET /api/v1/leaderboards/global/top?window=daily&date=2026-01-25&limit=10, Ranking Service: today = '2026-01-25', ZREVRANGE leaderboard:global:daily:2026-01-25 0 9 WITHSCORES, returns today's top 10
Batch job for weekly aggregation (from image shows 'Periodic batch jobs'): (1) Runs every Monday at 12 AM, (2) Aggregates last 7 days: FOR date IN (last 7 days): ZUNIONSTORE leaderboard:global:weekly:{YYYY-W{WW}} 7 leaderboard:global:daily:{date} WEIGHTS 1 (union all daily ZSETs into weekly ZSET), (3) Result: Weekly ZSET contains sum of daily scores
Step 4: Regional & Category Leaderboards
From image: 'leaderboard:music:IN:alltime' - region and category specific
Regional: (1) Event includes region: {video_id, score_delta, region: 'US'}, (2) Update: ZINCRBY leaderboard:US:alltime 1 V123, (3) Query: ZREVRANGE leaderboard:US:alltime 0 9 (top 10 in US)
Category: (1) Event includes category: {video_id, category: 'music'}, (2) Update: ZINCRBY leaderboard:music:alltime 1 V123, (3) Query: ZREVRANGE leaderboard:music:alltime 0 9 (top 10 music videos)
Combined filters: (1) Regional + Category: leaderboard:music:US:alltime (top music videos in US), (2) Regional + Category + Time: leaderboard:music:US:daily:2026-01-25 (top music videos in US today)
From image note: 'littered by region' - leaderboards sharded by region for isolation
Key explosion problem: (1) Dimensions: 5 regions × 10 categories × 4 time windows (daily, weekly, monthly, alltime) = 200 leaderboards, (2) Each leaderboard: 1 GB (10M entries), (3) Total: 200 GB (Redis Cluster can handle, but expensive)
Optimization: (1) Only create leaderboard if needed (lazy initialization), (2) Expire unused leaderboards (if no updates in 30 days → delete), (3) Use separate Redis cluster per region (isolate load)
Step 5: Approach 2 - TimeSeriesDB (InfluxDB) [from image shows 'TimeseriesDB(InfluxDB)']
From image: 'TimeseriesDB(InfluxDB)' with Flink for stream processing
Use case: When you need historical trend analysis, not just current top-K (e.g., 'How did video V123 rank over the past 30 days?')
Score event ingestion: Kafka 'score.updated' → Flink stream processor → InfluxDB
Flink processing: (1) Window aggregation: Group events by (video_id, 1-minute window), count views in window, (2) Output: {video_id: 'V123', views_in_minute: 1000, timestamp: '2026-01-25T10:30:00Z'}, (3) Write to InfluxDB
InfluxDB schema: Measurement: video_scores, Tags: video_id, region, category (indexed for fast filtering), Fields: views_count, likes_count, score (numeric values), Timestamp: time (nanosecond precision)
Write: INSERT video_scores,video_id=V123,region=US views_count=1000,score=1500 1674382200000000000
Query top-K: (1) Aggregate last 24 hours: SELECT SUM(views_count) as total_views FROM video_scores WHERE time > now() - 24h GROUP BY video_id ORDER BY total_views DESC LIMIT 10, (2) Time complexity: Slower than Redis (~100ms vs 1ms), but handles complex time-based queries
From image: 'BitMap: Use Map, (littered by region), Bucket: Bitmap per K. (littered by in some cold storage), All time leaderboard in some (H or K by bits in 1BM window). only aim per tie info' - uses bitmap for space efficiency
Downsampling: (1) Keep 1-minute data for 7 days, (2) Aggregate to 1-hour data (keep for 90 days), (3) Aggregate to 1-day data (keep forever), (4) Continuous queries auto-downsample: CREATE CONTINUOUS QUERY cq_hourly ON leaderboard BEGIN SELECT SUM(views_count) INTO video_scores_hourly FROM video_scores GROUP BY time(1h), video_id END
Pros: Historical analysis (trend over time), Efficient storage (compressed time-series), Complex queries (percentiles, moving averages)
Cons: Slower queries than Redis (100ms vs 1ms), Not suitable for real-time leaderboards (<1 sec latency requirement), More complex setup (Flink + InfluxDB vs just Redis)
Step 6: Approach 3 - Hybrid (Redis + DB) [BEST PRACTICE from image]
From image: '3. Hybrid Approach - All write requests are queued in Kafka. Consumers update Redis ZSET in real-time. Write scores to durable DB (Spanner, Postgres, Cassandra). Redis serves reads, DB serves as fallback and historical source. Periodic jobs snapshot Redis → DB or vice versa for consistency.'
Architecture: Kafka (events) → Redis Consumer (real-time) + DB Consumer (persistence) → Redis (reads, hot data) + DB (writes, cold storage, source of truth)
Write path: (1) Score event → Kafka 'score.updated', (2) Redis Consumer: Consumes from Kafka, ZINCRBY leaderboard:global:alltime 1 V123 (real-time update, <100ms lag), (3) DB Consumer: Consumes from Kafka, INSERT INTO scores (video_id, score_delta, timestamp, region) VALUES ('V123', 1, now(), 'US') (durable write, eventual consistency)
Read path: (1) User queries: GET /api/v1/leaderboards/global/top?limit=10, (2) Ranking Service: Try Redis: ZREVRANGE leaderboard:global:alltime 0 9 WITHSCORES, if Redis miss (rare, maybe Redis restarted) → fallback to DB: SELECT video_id, SUM(score_delta) as total_score FROM scores WHERE leaderboard_id='global' GROUP BY video_id ORDER BY total_score DESC LIMIT 10, (3) Response: Top-10 list
From image: 'Pro: Redis instantly reflects score changes + No data loss + Kafka, Redis Cluster, and DBs can all scale independently + TTL on keys: expire after 1 day/week/month'
From image: 'Con: Complex Architecture + If Redis consumer lags, leaderboard may be stale + If data not present in redis, we need to query db'
Consistency: (1) Redis = latest (eventual consistency with <1 sec lag from Kafka), (2) DB = source of truth (all events persisted), (3) Periodic reconciliation: Nightly job compares Redis vs DB, if mismatch → rebuild Redis from DB
Rebuild Redis from DB: (1) Scenario: Redis crash, all data lost, (2) Background job: SELECT video_id, SUM(score_delta) as total_score FROM scores WHERE timestamp > now() - INTERVAL '7 days' GROUP BY video_id, (3) Populate Redis: FOR EACH row: ZADD leaderboard:global:weekly:{YYYY-W{WW}} {total_score} {video_id}, (4) Time: Rebuild 10M entries takes ~10 minutes (acceptable for disaster recovery)
Step 7: Batch Jobs for Pre-Computed Rankings (from image)
From image: 'PreComputed - All scores are stored in a SQL/NoSQL DB (Spanner, Cassandra, BigQuery). Periodic batch jobs (e.g., hourly/daily) pre-compute top-K rankings. Store results in materialized leaderboard table or cache layer.'
Use case: When real-time updates not critical (e.g., monthly top songs, annual top players)
Batch job flow: (1) Trigger: Cron job runs every day at 2 AM, (2) Query DB: SELECT video_id, SUM(views) as total_views FROM video_views WHERE timestamp >= '2026-01-01' AND timestamp < '2026-02-01' GROUP BY video_id ORDER BY total_views DESC LIMIT 1000 (top 1000 videos in January), (3) Materialize: INSERT INTO leaderboard_snapshots (leaderboard_id: 'global_monthly_2026-01', rank, video_id, score, snapshot_date) (store pre-computed rankings), (4) Cache: SET leaderboard_cache:global:monthly:2026-01 {json_top_1000} EX 86400 (cache for 24 hours)
From image: 'Cons: Batch job runs every X minutes/hours → Leaderboards can be outdated by a few minutes or more'
From image: 'Pros: + Compute Top-K for every dimension (for instant result) + Minimal search duration + Introduce caching (optimization +'
Read path: (1) User queries: GET /api/v1/leaderboards/global/top?window=monthly&date=2026-01, (2) Check cache: GET leaderboard_cache:global:monthly:2026-01, if hit → return cached top-1000 (<1ms), (3) If cache miss: Query DB: SELECT rank, video_id, score FROM leaderboard_snapshots WHERE leaderboard_id='global_monthly_2026-01' ORDER BY rank LIMIT 10, (4) Cache result
Optimization: (1) Incremental updates: Instead of full recompute, batch job only processes new scores since last run (e.g., last 1 hour), merges with existing leaderboard, (2) Parallelization: Batch job runs on Spark cluster, processes 10M videos in parallel (reduce time from 1 hour to 10 minutes)
Step 8: Probabilistic Data Structures (Top-K Approximation)
From image: 'Place to implement: Where we already know, the query before hand (means which dimension of data user is likely to view)'
Use case: When exact top-K not required, approximate ranking acceptable (e.g., 'Trending now' where rank 100 vs 101 doesn't matter)
Count-Min Sketch: (1) Data structure: Probabilistic counter (trade accuracy for space), (2) Size: 1 MB can track billions of items (vs 1 GB for exact counts in Redis), (3) Update: When view event arrives, hash video_id to multiple positions in sketch, increment counters, (4) Query: Hash video_id, read counters, take minimum → estimated count, (5) Error: Overestimation possible (e.g., actual 1000 views, estimated 1050), but never underestimation
HyperLogLog: (1) Use case: Count distinct viewers (cardinality), e.g., '10M unique viewers' (not total views), (2) Size: 12 KB can estimate billions of unique IDs with <2% error, (3) Update: PFADD video:V123:unique_viewers {user_id}, (4) Query: PFCOUNT video:V123:unique_viewers → ~10000000
Bloom Filter: (1) Use case: Check if video already in top-K (membership test), (2) Size: 1 MB for 10M items with 1% false positive rate, (3) Query: 'Is video V123 in top-100?' → Yes (definitely) or No (maybe, 1% chance of false positive)
Top-K approximation algorithm: (1) Heavy Hitters: Maintain approximate top-K using Count-Min Sketch + Min-Heap, (2) Stream processing: Process millions of events/sec, maintain top-100 in memory (heap size = 100 items), (3) Update: If new item's estimated count > heap min → replace heap min with new item, (4) Query: Return heap (approximate top-100), (5) Accuracy: 95% overlap with exact top-100 (5% may be off by a few ranks)
Trade-off: (1) Memory: 100× less than exact (1 MB vs 100 MB), (2) Accuracy: ~95% correct for top-K (acceptable for 'Trending' lists), (3) Latency: Faster updates (no DB writes, in-memory sketch), (4) Use for: Trending topics, viral videos, real-time dashboards where approximate counts sufficient
Step 9: Handling Score Ties (Multiple Items with Same Score)
Problem: Video A and Video B both have 1000 views, how to rank them?
Approach 1 - Timestamp tiebreaker: (1) Store: ZADD leaderboard:global:alltime {score}.{timestamp} V123, example: score=1000, timestamp=1674382200 → 1000.1674382200, (2) Sorting: Redis sorts by float value, earlier timestamp gets higher rank (1000.1674382100 > 1000.1674382200), (3) Query: ZREVRANGE returns items in order: [Video A (1000 views, posted earlier), Video B (1000 views, posted later)]
Approach 2 - Lexicographic tiebreaker: (1) Store: ZADD leaderboard:global:alltime 1000 V123 (score only), (2) Redis ZSET: If scores equal, sorts lexicographically by member (V123 < V456 alphabetically), (3) Result: Deterministic ordering but arbitrary (no semantic meaning)
Approach 3 - Secondary score: (1) Composite score: primary_score × 1000000 + secondary_score, example: views × 1000000 + likes, Video A: 1000 views, 50 likes → 1000050000, Video B: 1000 views, 30 likes → 1000030000, (2) ZADD leaderboard:global:alltime 1000050000 V123, (3) Result: Video A ranks higher (more likes as tiebreaker)
Approach 4 - Random tiebreaker: (1) Add small random value: score + random(0, 1), example: 1000 + 0.5 = 1000.5, (2) Non-deterministic: Same query may return different order for tied items, (3) Use when order doesn't matter (trending lists)
Step 10: Pagination for Large Leaderboards
Problem: Leaderboard has 10M videos, user wants to see ranks 1000-1010 (page 100)
Offset-based pagination: (1) Query: GET /api/v1/leaderboards/global/top?offset=1000&limit=10, (2) Redis: ZREVRANGE leaderboard:global:alltime 1000 1009 WITHSCORES (get items at rank 1000-1009), (3) Time complexity: O(log(N) + offset + K) where offset=1000, K=10, (4) Performance: Efficient even for large offsets (offset=1M still <100ms in Redis)
Cursor-based pagination: (1) First page: ZREVRANGE leaderboard:global:alltime 0 9 WITHSCORES → returns top 10 + cursor = last item's score, (2) Next page: ZREVRANGEBYSCORE leaderboard:global:alltime {cursor} -inf LIMIT 0 10 (get next 10 items with score < cursor), (3) Advantage: Consistent pagination even if leaderboard updates between page requests, (4) Disadvantage: Can't jump to arbitrary page (must paginate sequentially)
Rank jumping: (1) User wants to see 'My rank': GET /api/v1/leaderboards/global/rank/V123 → rank = 50000, (2) Get surrounding entries: ZREVRANGE leaderboard:global:alltime {rank-5} {rank+4} (get 5 entries before + user + 4 entries after), (3) Display: User sees their position in context
Infinite scroll: (1) Client tracks last fetched rank: offset = 0 → 10 → 20 → 30 (as user scrolls), (2) Request next page: GET ?offset={offset}&limit=10, (3) Stop: When ZREVRANGE returns <10 items → end of leaderboard
Step 11: Decay/Time-Based Scoring (Trending Algorithm)
Problem: Old viral video has 10M views, new video has 100K views today → new video should rank higher in 'Trending'
Time-decay formula: score = raw_count / (age_in_hours + 2)^1.5 (Hacker News algorithm), Example: Video A: 10M views, 30 days old (720 hours) → score = 10000000 / (720+2)^1.5 ≈ 515, Video B: 100K views, 1 hour old → score = 100000 / (1+2)^1.5 ≈ 19245, Video B ranks higher (trending now)
Implementation: (1) Batch job runs hourly: Recalculate scores for all videos updated in last 7 days (older videos excluded from trending), (2) Formula: SELECT video_id, view_count / POW(EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600 + 2, 1.5) as trending_score FROM videos WHERE created_at > NOW() - INTERVAL '7 days', (3) Update Redis: FOR EACH video: ZADD leaderboard:trending {trending_score} {video_id}, (4) Expire old entries: ZREMRANGEBYSCORE leaderboard:trending -inf {min_score_threshold} (remove videos with score < threshold)
Reddit Hot algorithm: score = log10(ups - downs) + (age_in_seconds / 45000), (1) Logarithm: Diminishing returns (10 votes vs 100 votes has less impact than 100 vs 1000), (2) Time factor: Older posts decay linearly, (3) Balances engagement and recency
Real-time decay: (1) Problem: Batch job runs hourly, but trending list stale between runs, (2) Solution: Store (raw_count, timestamp) in ZSET, compute score on read: ZREVRANGE → fetch entries, for each entry: score = calculate_decay(raw_count, timestamp), sort by score, return top-K, (3) Trade-off: More CPU on read path, but always fresh scores
Step 12: Monitoring & Alerting
Metrics: (1) Kafka lag: Consumer lag > 1 minute → alert (leaderboard stale), (2) Redis memory: Memory usage > 80% → alert (risk of eviction), (3) Query latency: p99 latency > 100ms → alert (slow queries), (4) Cache hit rate: < 90% → alert (Redis not effective)
Dashboards: (1) Real-time: Current top-10 per leaderboard (visual validation), (2) Lag: Graph of Kafka consumer lag over time, (3) Traffic: Requests/sec per leaderboard endpoint, (4) Errors: 5xx error rate, timeout rate
Alerts: (1) Redis cluster: If 1 node down → auto-failover to replica + alert, (2) Kafka: If partition offline → alert (data loss risk), (3) DB: If replication lag > 10 sec → alert (reads may be stale), (4) Batch jobs: If job fails or takes >2× normal time → alert
Validation: (1) Consistency check: Nightly job compares Redis top-100 vs DB top-100, if mismatch > 5 items → alert (data corruption or consumer lag), (2) Sampling: Random sample 1% of scores, verify Redis matches DB
Load testing: (1) Simulate: 1M req/sec score updates (Kafka load test), 100K req/sec leaderboard queries (Redis load test), (2) Measure: Latency at percentiles (p50, p90, p99, p99.9), error rate, (3) Capacity planning: Current traffic = 100K req/sec, system handles 1M req/sec → 10× headroom
Step 13: Scaling & Performance Optimization
Redis Cluster: (1) Shard by leaderboard ID: {CRC16(leaderboard_id) mod 16384} → determines slot → determines node, (2) 10 nodes (5 masters + 5 replicas): Each node handles ~1-2 GB, distributes 10 GB total, (3) Reads: Route to replica (reduce load on master), (4) Writes: Master handles writes, replicates to replica
Kafka partitioning: (1) Partition 'score.updated' by video_id hash (100 partitions), (2) Consumer group: 100 consumers (1 per partition), parallel processing, (3) Throughput: 100 consumers × 10K events/sec = 1M events/sec
Database sharding: (1) Shard scores table by video_id hash (10 shards), (2) Each shard: 1M videos, reduces query time (scan 1M instead of 10M), (3) Cross-shard queries: Periodic batch jobs aggregate across shards
Caching: (1) Application-level cache: Cache top-100 in app memory (refresh every 10 seconds), serves 90% of queries from memory (no Redis round trip), (2) CDN: Cache API responses at edge (1 min TTL), global users get <50ms latency
Read replicas: (1) Redis: 5 replicas per master, route reads to replicas (5× read capacity), (2) DB: 3 replicas, route leaderboard queries to replicas (primary handles writes)
Materialized views: (1) DB: CREATE MATERIALIZED VIEW top_1000_daily AS SELECT ..., refresh hourly, (2) Queries: SELECT * FROM top_1000_daily WHERE rank <= 10 (instant, no aggregation)
Approximate queries: (1) Use Count-Min Sketch for top-K approximation, (2) 100× less memory, 95% accurate, sufficient for trending lists
Batch optimization: (1) Update Redis in batches: ZADD leaderboard:global:alltime {score1} {video1} {score2} {video2} ... (single command for 100 items), reduces round trips 100× (100 commands → 1 command)
Connection pooling: (1) Each app instance: 50 Redis connections, 50 DB connections, reuse across requests, (2) Redis pipelining: Send multiple commands in single network round trip (ZADD + ZREVRANGE → 1 RTT instead of 2)
7. Database Schema Details (from image)

Scores (Score DB - persistent storage)
score_id — uuid PRIMARY KEY
entity_id — varchar(100) (video_id, song_id, player_id - what's being ranked)
score_delta — int (increment value: +1 for view, +10 for like)
leaderboard_id — varchar(100) (global, regional, category-specific)
region — varchar(10) (US, EU, IN - for regional leaderboards)
category — varchar(50) (music, gaming, sports - for category leaderboards)
timestamp — timestamptz (when event occurred)
metadata — jsonb (additional context: user_id, device_type, etc.)
Indexes — INDEX on (leaderboard_id, timestamp) for batch aggregation, INDEX on (entity_id) for entity lookups
Sharding — Shard by entity_id hash (distribute load across 10 shards)
Leaderboard Snapshots (Materialized rankings)
leaderboard_id — varchar(100) (e.g., 'global_daily_2026-01-25')
rank — int (1, 2, 3, ...)
entity_id — varchar(100)
score — bigint (total accumulated score)
snapshot_date — date (when snapshot was created)
Composite PK — (leaderboard_id, rank)
Use case — Pre-computed rankings for batch approach, updated by periodic jobs
Redis - ZSET (Sorted Sets, from image)
leaderboard:global:alltime — ZSET - All-time global leaderboard, no TTL (permanent)
leaderboard:global:daily:{YYYY-MM-DD} — ZSET - Daily leaderboard, TTL 7 days (auto-expire old days)
leaderboard:global:weekly:{YYYY}-W{WW} — ZSET - Weekly leaderboard, TTL 90 days
leaderboard:global:monthly:{YYYY-MM} — ZSET - Monthly leaderboard, TTL 365 days
leaderboard:{region}:alltime — ZSET - Regional leaderboard (e.g., leaderboard:US:alltime), no TTL
leaderboard:{category}:alltime — ZSET - Category leaderboard (e.g., leaderboard:music:alltime), no TTL
leaderboard:trending — ZSET - Trending (time-decay scoring), updated hourly, TTL 24 hours
Commands — ZINCRBY (update score), ZREVRANGE (get top-K), ZREVRANK (get rank), ZSCORE (get score)
Memory — ~100 bytes per entry, 10M entries = ~1 GB per leaderboard
InfluxDB - Time-Series (from image approach 2)
Measurement — entity_scores (e.g., video_scores, song_scores)
Tags — entity_id, region, category (indexed for fast filtering)
Fields — views_count, likes_count, shares_count, score (numeric values)
Timestamp — time (nanosecond precision)
Retention — 1-min data: 7 days, 1-hour data: 90 days, 1-day data: forever
Queries — SELECT SUM(views_count) FROM entity_scores WHERE time > now() - 24h GROUP BY entity_id ORDER BY SUM DESC LIMIT 10
Kafka Topics (from image)
score.updated — Score events (views, likes, game scores), partition by entity_id (100 partitions)
Consumer groups — redis-consumer (updates Redis ZSET), db-consumer (persists to DB), analytics-consumer (InfluxDB writes)
Aggregated DB (Spanner/Cassandra/BigQuery - from image)
Table — aggregated_scores (materialized aggregates for batch approach)
entity_id — varchar PRIMARY KEY
total_score — bigint (sum of all score deltas)
daily_score — bigint (sum for today, reset daily)
weekly_score — bigint (sum for this week)
monthly_score — bigint (sum for this month)
last_updated — timestamp
Use case — Batch jobs aggregate scores here, materialized for fast queries
8. Approach Comparison - Deep Dive (from image shows 3 approaches)

From image: Shows 3 distinct approaches with pros/cons for each
Approach 1 - Redis Sorted Set/ZSET (from image): Data structure: One ZSET per leaderboard (e.g., leaderboard:music:IN:alltime), stores (entity_id, score) pairs sorted by score. Operations: ZINCRBY (update score in O(log N)), ZREVRANGE (get top-K in O(log N + K)), ZREVRANK (get rank in O(log N)). Pros: (1) Every rank and data available instantly (<1ms queries), (2) Simple implementation (just Redis commands), (3) Atomic operations (ZINCRBY is thread-safe). Cons: (1) Complete expensive (no need to keep in single node + not possible for 'ideal depth'), (2) Memory intensive (10M entries = 1 GB per leaderboard), (3) No persistence (Redis crash = data loss without replica), (4) Hard to do historical analysis (only current state, no time-series). When to use: Real-time leaderboards (gaming, live sports), small-medium scale (<100M entities), simple time windows (daily, weekly, monthly), low latency critical (<10ms).
Approach 2 - TimeSeriesDB (InfluxDB) with Flink (from image): Data flow: Kafka → Flink (stream aggregation) → InfluxDB (time-series storage) → Query for top-K. Flink processing: Window aggregation (1-minute windows), group by entity_id, count events, output to InfluxDB. Pros: (1) Historical trend analysis (how did rank change over time), (2) Efficient storage (compressed time-series, 10× less than raw events), (3) Complex queries (percentiles, moving averages, downsampling). Cons: (1) Slower queries (~100ms vs 1ms in Redis), (2) Complex setup (Flink + InfluxDB + Kafka), (3) Not real-time (<1 sec lag from Flink windowing), (4) Harder to get exact rank (requires aggregation query). When to use: Analytics dashboards (show trend graphs), historical leaderboards (e.g., 'Top songs each month for past year'), large-scale time-series data (billions of events), when exact real-time ranking not critical.
Approach 3 - Hybrid (Redis + DB + Kafka) [BEST PRACTICE from image]: Architecture: Kafka (events) → Redis Consumer (real-time ZSET updates) + DB Consumer (persistent writes) → Redis (reads) + DB (fallback/historical). Write path: (1) Score event → Kafka, (2) Redis Consumer: ZINCRBY (real-time, <100ms lag), (3) DB Consumer: INSERT scores (persistent, eventual consistency). Read path: (1) Try Redis ZREVRANGE (fast, <1ms), (2) If Redis miss → Query DB: SELECT ... GROUP BY ... ORDER BY ... (slower, ~100ms), (3) Rebuild Redis from DB if needed. Pros: (1) Redis instantly reflects score changes (real-time), (2) No data loss (Kafka + DB persistence), (3) All components scale independently (Kafka partitions, Redis cluster, DB sharding), (4) TTL on keys (auto-expire old leaderboards to save memory). Cons: (1) Complex architecture (Kafka + Redis + DB = 3 systems to manage), (2) If Redis consumer lags, leaderboard may be stale, (3) If data not present in Redis, we need to query DB (slower fallback). When to use: Production systems at scale (millions of users), need both real-time updates AND persistence, multi-dimensional leaderboards (regional, category, time windows), critical data that can't be lost.
From image note: 'Bitmap: Use Map, (littered by region), Bucket: Bitmap per K' - Alternative: Use bitmaps for space efficiency when tracking top-K membership (is entity in top-1000?), much smaller than storing full scores.
From image: 'Place to implement: Where we already know, the query before hand (means which dimension of data user is likely to view)' - Pre-compute only the leaderboards users actually query (don't waste resources on unused dimensions).
Decision matrix: Need <10ms latency? → Redis ZSET. Need historical analysis? → InfluxDB. Need scale + reliability? → Hybrid. Small scale (<1M entities)? → Redis. Large scale (>100M entities)? → Hybrid or InfluxDB. Exact ranking required? → Redis. Approximate OK (trending)? → Count-Min Sketch.
Production examples: Gaming leaderboards (Fortnite, PUBG): Hybrid (Redis for real-time, DB for persistence, millions of players), Music streaming (Spotify Top 50): Batch + Redis (daily batch compute, cache in Redis, not real-time), Video platform (YouTube Trending): Time-decay algorithm + Redis (hourly recompute trending scores, cache top-100), Social media (Twitter Trends): Probabilistic (Count-Min Sketch for trending topics, approximate counts acceptable).
9. Scaling & Optimization Techniques

Technique 1: Redis Cluster sharding - Shard by leaderboard_id, 16384 slots distributed across nodes, 10 nodes handle 10 GB
Technique 2: Kafka partitioning - 100 partitions by entity_id hash, 100 parallel consumers, 1M events/sec throughput
Technique 3: Time-windowed leaderboards - Daily/weekly/monthly keys with TTL, auto-expire old data, saves memory
Technique 4: Batch aggregation - ZUNIONSTORE combines multiple ZSETs (daily → weekly), runs periodically (Monday 12 AM)
Technique 5: Lazy initialization - Only create leaderboard when first score arrives, don't pre-create all combinations
Technique 6: Read replicas - Route reads to Redis replicas (5× read capacity), master handles writes only
Technique 7: Application cache - Cache top-100 in app memory (refresh every 10 sec), serve 90% from memory
Technique 8: CDN caching - Cache API responses at edge (1 min TTL), <50ms global latency
Technique 9: Probabilistic structures - Count-Min Sketch for top-K approximation, 100× less memory, 95% accurate
Technique 10: Connection pooling - 50 Redis connections per app instance, pipelining for batch commands
Technique 11: Materialized views - Pre-compute top-1000 in DB, refresh hourly, instant queries
Technique 12: Time-decay scoring - Trending algorithm, batch recompute hourly, balances recency and engagement
10. Common Interview Questions

Q
Design a real-time gaming leaderboard that shows top 100 players globally and by region. How do you handle millions of score updates per second?
A
Real-time gaming leaderboard architecture: Requirements:

(1) Top 100 global,

(2) Top 100 per region (US, EU, APAC),

(3) Millions of score updates/sec,

(4) <100ms query latency,

(5) Handle score ties. Architecture: Kafka (score events) → Redis Consumer (real-time ZSET) + DB Consumer (persistence) → Redis Cluster (reads) + PostgreSQL (backup). Score update flow:

(1) Player scores 1000 points in game → Game server sends: POST /api/v1/scores with {player_id: 'P123', score_delta: 1000, region: 'US', match_id: 'M456', timestamp},

(2) Score Service validates: Check player exists, check match active, check for duplicate (Redis dedup with 5-min TTL),

(3) Publish to Kafka: 'score.updated' topic with {player_id, score_delta: 1000, region: 'US', timestamp}, partition by player_id hash → ensures ordering per player. Redis Consumer (real-time updates):

(1) Consumes from Kafka (100 consumer instances, 1 per partition),

(2) Updates Redis ZSETs: ZINCRBY leaderboard:global:alltime 1000 P123 (global leaderboard), ZINCRBY leaderboard:US:alltime 1000 P123 (regional leaderboard), ZINCRBY leaderboard:global:daily:{YYYY-MM-DD} 1000 P123 (daily leaderboard),

(3) Lag: <100ms from event to Redis update (Kafka consumer lag monitoring). DB Consumer (persistence):

(1) Separate consumer group writes to PostgreSQL,

(2) INSERT INTO scores (player_id, score_delta, region, timestamp, match_id),

(3) Eventual consistency (lag ~1 second, acceptable for backup/analytics). Query flow: User requests top 100: GET /api/v1/leaderboards/global/top?limit=100. Ranking Service:

(1) Check Redis: ZREVRANGE leaderboard:global:alltime 0 99 WITHSCORES (get top 100 with scores), Time: <1ms (Redis in-memory lookup),

(2) Enrich data: For each player_id, fetch player details: MGET player:P123 player:P456 ... (batch fetch from Redis player cache), If cache miss → query DB: SELECT username, avatar_url FROM players WHERE player_id IN (...),

(3) Response: [{rank: 1, player_id: 'P123', username: 'ProGamer', score: 1500000}, {rank: 2, ...}, ...],

(4) Total latency: <10ms (1ms ZREVRANGE + 5ms MGET + 2ms serialization). Regional leaderboard: GET /api/v1/leaderboards/US/top?limit=100, Same flow but query: ZREVRANGE leaderboard:US:alltime 0 99. Handle score ties:

(1) Timestamp tiebreaker: When scores equal, player who reached score first ranks higher,

(2) Implementation: Store score as float: score + (timestamp / 1e12), Example: Player A: 1000 points at t=1674382200 → 1000.000001674382200, Player B: 1000 points at t=1674382300 → 1000.000001674382300, Player A ranks higher (earlier timestamp),

(3) ZADD leaderboard:global:alltime {score_with_timestamp} P123. Scaling for millions of updates/sec:

(1) Kafka: 100 partitions × 10K events/sec/partition = 1M events/sec, add more partitions to scale beyond,

(2) Redis Cluster: 10 master nodes (each handles 100K ZINCRBY/sec) = 1M ZINCRBY/sec, shard by leaderboard_id: hash(leaderboard:global:alltime) mod 10 → node 5,

(3) Redis Consumer: 100 instances (1 per Kafka partition), auto-scale based on Kafka lag (if lag > 1 min → add more consumers). Redis optimization:

(1) Pipelining: Batch updates: PIPELINE; ZINCRBY leaderboard:global:alltime 1000 P123; ZINCRBY leaderboard:US:alltime 1000 P123; EXEC; (send 2 commands in 1 network round trip),

(2) Lua script: EVALSHA to update multiple ZSETs atomically (prevents partial updates if one fails),

(3) Memory: Top 100 leaderboard = 100 entries × 100 bytes = 10 KB (tiny), Global leaderboard (10M players) = 1 GB (manageable). Disaster recovery:

(1) Redis crash: All ZSET data lost (in-memory only),

(2) Rebuild from DB: Background job queries: SELECT player_id, SUM(score_delta) as total_score FROM scores GROUP BY player_id, Populate Redis: FOR EACH player: ZADD leaderboard:global:alltime {total_score} {player_id}, Time: Rebuild 10M players takes ~10 minutes (acceptable),

(3) Redis persistence: Enable RDB snapshots (every 5 min) or AOF (append-only file) for faster recovery. Advanced features:

(1) Player's rank: GET /api/v1/leaderboards/global/rank/P123 → ZREVRANK leaderboard:global:alltime P123 returns rank (0-indexed), Example: rank=42 → display as #43,

(2) Percentile: Player in top 1%? → total_players = ZCARD leaderboard:global:alltime, percentile = (rank / total_players) × 100,

(3) Surrounding players: ZREVRANGE leaderboard:global:alltime {rank-5} {rank+4} WITHSCORES (show 5 above + player + 4 below). Monitoring:

(1) Kafka consumer lag: Alert if lag > 1 min (leaderboard stale),

(2) Redis memory: Alert if > 80% (risk of eviction),

(3) Query latency: p99 < 10ms (SLA),

(4) Consistency check: Hourly job compares Redis top-100 vs DB top-100, alert if mismatch. Production example: Fortnite uses similar architecture, 250M+ players globally, millions of concurrent matches, real-time leaderboards updated every few seconds, Redis Cluster (100+ nodes), Kafka (1000+ partitions), sub-10ms query latency for top 100.

Q
How would you design a YouTube Trending page that shows top 50 trending videos? Explain the time-decay algorithm.
A
YouTube Trending page design with time-decay scoring: Requirements:

(1) Top 50 trending videos (updated hourly),

(2) Balance recency and engagement (new viral video ranks higher than old popular video),

(3) Regional trending (US, UK, India, etc.),

(4) Category trending (Music, Gaming, News). Time-decay algorithm (Hacker News style): Formula: trending_score = engagement_score / (age_in_hours + 2)^gravity, Parameters:

(1) engagement_score: Weighted sum of interactions, engagement_score = views + (likes × 10) + (comments × 20) + (shares × 30), Weights: Shares > Comments > Likes > Views (stronger engagement signal weighted higher),

(2) age_in_hours: Time since video published, age_in_hours = (NOW() - published_at) / 3600 (convert seconds to hours),

(3) gravity: Decay rate (typically 1.5-2.0), Higher gravity = faster decay (older content drops faster), YouTube likely uses gravity ≈ 1.8. Example calculation: Video A (old viral): Published 7 days ago (168 hours), 10M views, 500K likes, 50K comments, 10K shares, engagement_score = 10000000 + (500000×10) + (50000×20) + (10000×30) = 16300000, trending_score = 16300000 / (168+2)^1.8 = 16300000 / 1173 ≈ 13895. Video B (new rising): Published 3 hours ago, 500K views, 50K likes, 5K comments, 1K shares, engagement_score = 500000 + (50000×10) + (5000×20) + (1000×30) = 1130000, trending_score = 1130000 / (3+2)^1.8 = 1130000 / 11.8 ≈ 95763, Video B ranks HIGHER (trending now despite lower absolute engagement). Architecture: Batch computation + Redis caching. Batch job (hourly):

(1) Trigger: Cron runs every hour at :00 (12:00, 13:00, 14:00),

(2) Query recent videos: SELECT video_id, views, likes, comments, shares, published_at FROM videos WHERE published_at > NOW() - INTERVAL '7 days' (only videos from last 7 days eligible for trending),

(3) Calculate trending score: FOR EACH video: age_in_hours = (NOW() - published_at) / 3600, engagement_score = views + (likes×10) + (comments×20) + (shares×30), trending_score = engagement_score / POW(age_in_hours + 2, 1.8),

(4) Sort and store top 1000: ORDER BY trending_score DESC LIMIT 1000,

(5) Write to Redis: DEL leaderboard:trending (clear old), ZADD leaderboard:trending {trending_score} {video_id} (add all 1000 videos), EXPIRE leaderboard:trending 7200 (2-hour TTL, in case batch job fails next run). Regional trending:

(1) Separate batch job per region,

(2) Filter: WHERE region IN ('US', 'CA', 'MX') for North America trending,

(3) Store: ZADD leaderboard:trending:US {trending_score} {video_id}. Category trending:

(1) Filter: WHERE category='Music',

(2) Store: ZADD leaderboard:trending:Music {trending_score} {video_id}. Query flow: User opens Trending page: GET /api/v1/trending?region=US&limit=50. Ranking Service:

(1) Check Redis: ZREVRANGE leaderboard:trending:US 0 49 WITHSCORES (get top 50), Cache hit (99% of requests): Return from Redis (<1ms), Cache miss (rare, during batch job or Redis restart): Fallback to DB query (recalculate trending scores on-the-fly, slower ~500ms),

(2) Enrich video details: For each video_id, fetch metadata: MGET video:V123 video:V456 ... (title, thumbnail, channel),

(3) Response: [{rank: 1, video_id: 'V123', title: 'New Music Video', trending_score: 95763, views: 500K, ...}]. Real-time vs batch trade-off:

(1) Batch (hourly update): Simpler implementation, less compute (recalculate once per hour, not on every query), Staleness: Trending list can be up to 1 hour old (acceptable for most users),

(2) Real-time (per-query calculation): Always fresh scores, High compute cost (recalculate for 1M videos on every query → 100ms query time), YouTube uses batch approach (hourly or even daily updates for trending). Optimization:

(1) Incremental computation: Instead of recalculating all videos every hour, only update videos with new engagement (events in last hour), Kafka stream: Consume view/like/comment events, update trending score in real-time (hybrid),

(2) Materialized view: CREATE MATERIALIZED VIEW trending_videos AS SELECT video_id, ..., REFRESH MATERIALIZED VIEW CONCURRENTLY (non-blocking), Query trending view instead of raw videos table (10× faster). Alternative: Reddit Hot algorithm: Formula: hot_score = log10(engagement) + (age_in_seconds / 45000), Logarithm: Diminishing returns (100 vs 1000 engagement has less impact than 10 vs 100), Linear time decay: Older posts decay steadily, Use case: When you want engagement to matter more than recency (Reddit front page stays stable longer than YouTube trending). Monitoring:

(1) Batch job duration: Alert if job takes >10 min (normally 5 min),

(2) Trending consistency: Compare manual check vs automated trending (validate viral videos appear),

(3) Regional coverage: Ensure all regions have trending data (no empty leaderboards). Advanced: Personalized trending:

(1) User's watch history: SELECT categories_watched, channels_subscribed FROM user_behavior WHERE user_id={user_id},

(2) Boost relevant categories: If user watches Music videos 80% of time, boost Music videos in trending, Formula: personalized_score = trending_score × (1 + category_affinity),

(3) ML model: Train model to predict 'will user click this trending video', Features: trending_score, user_watch_history, video_category, time_of_day. Production: YouTube Trending page updated daily or hourly (not real-time), uses combination of engagement signals + time decay, regional and category-specific trending, reviewed by human moderators (prevent manipulation, ensure quality), ML-based personalization for logged-in users.

Q
Compare Redis ZSET vs database-based leaderboard approaches. When would you choose one over the other?
A
Redis ZSET vs Database leaderboard comparison: Redis ZSET approach: Data structure: Sorted set (ZSET) stores (member, score) pairs, automatically sorted by score. Operations:

(1) ZADD leaderboard {score} {member}: Add/update entry O(log N),

(2) ZINCRBY leaderboard {increment} {member}: Increment score O(log N),

(3) ZREVRANGE leaderboard 0 9: Get top-10 O(log N + K),

(4) ZREVRANK leaderboard {member}: Get rank O(log N),

(5) ZSCORE leaderboard {member}: Get score O

(1). Example: ZADD leaderboard 1000 player1, ZINCRBY leaderboard 500 player1 (now 1500), ZREVRANGE leaderboard 0 2 WITHSCORES → [(player1, 1500), (player2, 1200), (player3, 1000)]. Pros:

(1) Blazing fast: All operations <1ms (in-memory), top-100 query in ~1ms even with 10M players,

(2) Simple: Just Redis commands, no SQL, no indexes, no query optimization,

(3) Atomic: ZINCRBY is thread-safe (no race conditions),

(4) Built-in ranking: ZREVRANK gives rank without scanning,

(5) Auto-sorted: No manual sorting needed. Cons:

(1) Memory only: No persistence by default (RDB/AOF mitigates but not 100% durable),

(2) Single machine limit: One ZSET must fit in RAM of single node (can't shard a single ZSET), For 100M players × 100 bytes = 10 GB (expensive Redis server needed),

(3) No time-series: Only current state, can't query 'What was the leaderboard last week?',

(4) Limited queries: Can't do complex filters (e.g., 'Top players from California who started in 2024'),

(5) Cost: Redis memory expensive (RAM > disk storage by 10-100×). Database approach (PostgreSQL/MySQL): Schema: CREATE TABLE leaderboard (player_id varchar PRIMARY KEY, score bigint, updated_at timestamp); CREATE INDEX idx_score ON leaderboard(score DESC); Query top-10: SELECT player_id, score FROM leaderboard ORDER BY score DESC LIMIT 10; Update score: UPDATE leaderboard SET score = score + {increment} WHERE player_id = {player_id}; Get rank: SELECT COUNT(*) FROM leaderboard WHERE score > (SELECT score FROM leaderboard WHERE player_id = {player_id}); (counts how many players have higher score). Pros:

(1) Persistent: Data on disk, survives crashes (ACID transactions),

(2) Scalable storage: Disk cheaper than RAM (10 GB disk << 10 GB RAM), can store 1B+ players,

(3) Time-series: Add timestamp column, query historical leaderboards ('Top players on 2024-01-01'),

(4) Complex queries: Filter by region, category, date range, etc.,

(5) Mature ecosystem: Backups, replication, monitoring well-established. Cons:

(1) Slower: Top-10 query ~50-100ms (disk I/O, index scan), 100× slower than Redis,

(2) Rank calculation expensive: Get rank query scans all players with score > player's score → O(N) time for large N, For 10M players, rank query takes ~500ms (unacceptable for real-time leaderboards),

(3) Concurrent updates: UPDATE locks row, high contention for popular players (score updated 1000s of times/sec),

(4) Index overhead: Score index needs rebalancing on every UPDATE (slower writes). Hybrid approach (Redis + DB): Best of both worlds. Architecture: Writes: Score event → Kafka →

(1) Redis Consumer: ZINCRBY leaderboard {increment} {player} (real-time),

(2) DB Consumer: INSERT INTO score_events (player_id, score_delta, timestamp) (persistent log). Reads:

(1) Try Redis: ZREVRANGE leaderboard 0 9 (fast, <1ms),

(2) If Redis miss: Query DB: SELECT player_id, SUM(score_delta) FROM score_events GROUP BY player_id ORDER BY SUM DESC LIMIT 10 (slow, ~100ms), rebuild Redis from DB result. Consistency: Redis reflects latest scores (<1 sec lag from Kafka), DB is source of truth (eventual consistency, ~1-5 sec lag), Periodic reconciliation: Nightly job compares Redis vs DB, rebuilds Redis if mismatch. Disaster recovery: Redis crash → rebuild from DB (takes ~10 min for 10M players, acceptable). Decision matrix: Choose Redis ZSET when:

(1) Need low latency (<10ms for top-K queries),

(2) Leaderboard fits in memory (<100M players → <10 GB),

(3) Real-time updates critical (gaming, live sports),

(4) Simple use case (global top-K, no complex filters),

(5) Can tolerate data loss risk (use RDB/AOF for mitigation). Choose Database when:

(1) Need persistence (can't lose leaderboard data),

(2) Large scale (>100M players, >10 GB data),

(3) Historical queries needed ('Top players last month'),

(4) Complex filters (region, category, time ranges),

(5) Lower budget (disk storage 10× cheaper than RAM). Choose Hybrid when:

(1) Need BOTH low latency AND persistence,

(2) Production system with millions of users,

(3) Can manage complexity (Kafka + Redis + DB),

(4) Multi-dimensional leaderboards (regional, category, time windows). Materialized views (advanced DB approach): CREATE MATERIALIZED VIEW top_1000_players AS SELECT player_id, score FROM leaderboard ORDER BY score DESC LIMIT 1000; REFRESH MATERIALIZED VIEW top_1000_players; (refresh hourly). Query: SELECT * FROM top_1000_players LIMIT 10; (~1ms, pre-computed). Trade-off: Freshness vs performance (view can be 1 hour stale). Sharding (scale DB approach): Shard by player_id hash, not by score (score-based sharding causes hotspots → top players all on same shard). Query top-K: Scatter-gather across all shards → merge results → return top-10. Expensive but scales to billions of players. Production examples: Gaming (Fortnite, PUBG): Hybrid (Redis for real-time, DB for persistence), Music (Spotify Top 50): Batch DB + Redis cache (hourly batch, cache top-1000), Social media (Twitter Trends): Redis ZSET (short-lived trending, OK to lose data), Finance (Stock tickers): Database (need ACID transactions, audit trail). Summary: Redis = fast but volatile, Database = slow but durable, Hybrid = best of both but complex. Choose based on latency requirements, data size, durability needs, and budget.

11. Key Numbers to Remember

Scale & Performance
Events/sec — 1M req/sec - billions of score updates globally
Query Latency — 100ms to get top-K (Redis <1ms, DB ~100ms, InfluxDB ~100ms)
Update Lag — <1 second for real-time leaderboard updates (Redis ZSET via Kafka)
Batch Frequency — Hourly or daily for trending algorithms (time-decay recomputation)
Redis ZSET (from image Approach 1)
Memory per entry — ~100 bytes (member + score + ZSET overhead)
10M entries — ~1 GB per leaderboard ZSET
Operations — ZINCRBY O(log N), ZREVRANGE O(log N + K), ZREVRANK O(log N)
Query time — <1ms for top-100 even with 10M entries
Time Windows
Daily leaderboard TTL — 7 days (auto-expire old days)
Weekly leaderboard TTL — 90 days (keep ~13 weeks)
Monthly leaderboard TTL — 365 days (keep 12 months)
All-time leaderboard — No TTL (permanent, grows indefinitely)
Hybrid Approach (from image Approach 3)
Kafka consumer lag — <100ms (Redis consumer), ~1 sec (DB consumer)
Kafka partitions — 100 partitions by entity_id hash, 100 parallel consumers
Redis rebuild time — ~10 minutes to rebuild 10M entries from DB after crash
Consistency check — Nightly job compares Redis vs DB top-100, alerts on mismatch
Key Interview Tips

⚠️
CRITICAL: Redis ZSET is fast (<1ms) but volatile (in-memory). For production leaderboards, use HYBRID approach: Redis for real-time reads + Kafka + DB for persistence. Without persistence, Redis crash = all leaderboard data lost.

⭐
Interviewers ALWAYS ask: 'Redis vs Database for leaderboards?'. Answer: Redis ZSET = <1ms queries but no persistence. Database = persistent but slow (~100ms). Hybrid = Redis (reads) + Kafka (events) + DB (writes) = best of both, industry standard for production.

💡
Time-decay algorithm for Trending: trending_score = engagement / (age_in_hours + 2)^1.8. New viral video (3 hours old, 500K views) ranks higher than old popular video (7 days old, 10M views). Batch recompute hourly to balance recency and engagement.

⭐
Must explain: Handle score ties with timestamp tiebreaker. Store score as float: score + (timestamp / 1e12). Example: Player A reaches 1000 points at t=100 → 1000.0000000001, Player B reaches 1000 at t=200 → 1000.0000000002. Player A ranks higher (earlier timestamp).

⚠️
NEVER create all leaderboard combinations upfront. With 5 regions × 10 categories × 4 time windows = 200 leaderboards × 1 GB = 200 GB Redis memory (expensive!). Use lazy initialization: create leaderboard only when first score arrives. Expire unused leaderboards after 30 days.

💡
Kafka partitioning: Partition 'score.updated' by entity_id hash (not by timestamp). Ensures all events for same entity go to same partition → ordering preserved → Redis consumer processes scores in order → no race conditions.

⭐
Interviewers love: 'How handle millions of score updates/sec?'. Answer: Kafka (1M events/sec = 100 partitions × 10K/sec) → 100 Redis consumers (1 per partition) → Each does ZINCRBY (O(log N) = <1ms) → Total: 1M ZINCRBY/sec with 100 consumers. Scale by adding partitions.

⚠️
NEVER query rank with COUNT(*) in database: SELECT COUNT(*) FROM leaderboard WHERE score > {player_score}. For 10M players, this scans millions of rows → 500ms query time (too slow). Use Redis ZREVRANK instead → <1ms, O(log N).

💡
Batch jobs optimization: Use ZUNIONSTORE to combine daily ZSETs into weekly: ZUNIONSTORE leaderboard:weekly:2026-W04 7 leaderboard:daily:2026-01-19 leaderboard:daily:2026-01-20 ... WEIGHTS 1. Aggregates 7 days in single Redis command (atomic).

⭐
Must mention: From image shows 3 approaches with pros/cons. Approach 1 (Redis ZSET): Fast but no persistence. Approach 2 (InfluxDB): Historical analysis but slow queries. Approach 3 (Hybrid): Best practice for production - Redis + Kafka + DB = real-time + durable + scalable.

system-design
leaderboard
top-k
trending
Redis-ZSET
sorted-sets
