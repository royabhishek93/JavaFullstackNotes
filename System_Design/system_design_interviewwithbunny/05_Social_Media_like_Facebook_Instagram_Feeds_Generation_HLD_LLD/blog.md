Social Media Platform (Facebook/Instagram)

"Graph database for social connections → Fanout on write for feed generation → CDN for media delivery → Redis cache for hot data"

1. Functional Requirements

Feature 1: User should be able to register and login to the application with profile management
Feature 2: Create posts (text/image/video) with multimedia content up to 500MB
Feature 3: Follow other users to build social graph (send friend requests for bidirectional connections)
Feature 4: Like and comment on posts with nested comment threads
Feature 5: View personalized feed of posts from followed users in reverse chronological order
Feature 6: Search for users, posts, hashtags with real-time suggestions
Feature 7: Receive notifications for interactions (likes, comments, follows, mentions)
2. Non-Functional Requirements

Scale
Daily Active Users — 500M DAU (2 billion total registered users)
Posts Volume — 100M posts per day, 1.2K posts/second average
Reads/Writes Ratio — 100:1 (heavy read system, users scroll feeds >> create posts)
Media Storage — Petabytes of images/videos, 10TB uploaded daily
Performance
Latency — Low latency: 500ms to load feed, <200ms for likes/comments
Feed Generation — Fanout on write for normal users (<5K followers), pull model for celebrities
Media Upload — Async processing, immediate confirmation with background transcoding
Reliability
CAP Theorem — Availability >> Consistency (eventual consistency acceptable)
Data Durability — S3 for media (11 9's), database replication for user data
Availability Target — 99.99% uptime (52 minutes downtime/year)
3. Core Entities

Entity 1: User - Profile with user_id, username, email, bio, profile_pic_url, created_at
Entity 2: Post - Content with post_id, user_id, content (text/media URLs), created_at, visibility
Entity 3: Followers - Bidirectional social graph (follower_id, followee_id, created_at)
Entity 4: Like/Comment - Engagement data with reaction types, timestamps, metadata
Entity 5: Feeds - Precomputed feed cache for users with feed_id, user_id, post_ids[], updated_at
4. API Designing

User Onboarding
POST /api/v1/users/register — Create new user account with email, password, username
POST /api/v1/users/login — Authenticate user and return JWT token
GET /api/v1/users/{user_id}/profile — Fetch user profile with follower/following counts, posts count
PUT /api/v1/users/{user_id}/profile — Update user profile (bio, profile pic, settings)
Post Operations
POST /api/v1/posts — Create new post with {content, media_urls[], visibility, mentions[]}
GET /api/v1/posts/{post_id} — Retrieve single post with engagement metrics (likes, comments count)
PUT /api/v1/posts/{post_id} — Update post content (only author can edit)
DELETE /api/v1/posts/{post_id} — Soft delete post, mark as deleted but keep for analytics
GET /api/v1/posts/feed?limit={limit}&offset={offset} — Fetch personalized feed with pagination (infinite scroll)
Interactions
POST /api/v1/posts/{post_id}/like — Like a post (idempotent, second call unlikes)
DELETE /api/v1/posts/{post_id}/unlike — Remove like from post
GET /api/v1/posts/{post_id}/comments — Fetch comments with pagination, supports nested threads
POST /api/v1/comments/{comment_id} — Add comment to post or reply to another comment
POST /api/v1/users/{user_id}/follow — Follow a user (async fanout to followers' feeds)
DELETE /api/v1/{id}/unfollow — Unfollow a user
5. High Level Design

Users/Clients → API Gateway & Load Balancer: Authentication, routing, rate limiting (1K req/min per user)
User Service → User DB (PostgreSQL): Manages user profiles, credentials, settings with read replicas
Content Service → Post DB (Cassandra): Stores posts partitioned by user_id, optimized for writes
Content Service → S3: Stores media files (images/videos) with CDN for fast delivery
Feed Service → Feed Cache (Redis): Precomputed feeds for users, hot data in memory
Follower Service → Follower DB (Graph DB or PostgreSQL): Manages social graph with bidirectional edges
Engagement Service → Comment DB & Like DB: Stores interactions with denormalized counts
Feed Service → Kafka: Async fanout on write to populate followers' feeds
Notification Service: Triggered by engagement events, sends push/email notifications
6. Deep Dive Design (Low Level)

Step 1: User Registration & Login
Client sends: POST /api/v1/users/register with {username: 'john_doe', email: 'john@example.com', password: 'hashed_password'}
User Service validates: Username uniqueness (DB query), email format, password strength (8+ chars, special chars)
Service creates: User record in PostgreSQL with bcrypt hashed password (cost factor 12), generates user_id (UUID)
Service provisions: Empty feed in Redis, creates default privacy settings in Settings DB
Service returns: {user_id, username, token (JWT with 7-day expiry)} for session management
Login flow: Verify password hash match, generate JWT with {user_id, username, exp}, return token
Step 2: Post Creation
Client sends: POST /api/v1/posts with {content: 'Hello World!', media_files: [File], visibility: 'public', mentions: ['@jane_doe']}
Content Service validates: JWT token, content length (<5000 chars), media size (<500MB), file types (JPEG, PNG, MP4)
Service uploads: Media to S3 with key pattern {user_id}/{year}/{month}/{uuid}.{ext}, returns S3 URLs
Service creates: Post record in Cassandra with partition key=user_id, clustering key=created_at DESC for efficient user timeline queries
Service publishes: Event to Kafka topic 'post.created' with {post_id, user_id, created_at, media_urls}
Service returns: {post_id, status: 'published', media_urls[]} immediately (202 Accepted), fanout happens async
Step 3: Media Upload & Processing
Client uploads: Media file via multipart/form-data or presigned S3 URL for large files (>100MB)
Content Service generates: Presigned PUT URL for S3 upload (valid for 15 minutes), client uploads directly to S3
S3 upload triggers: Lambda function for async processing (image resizing, video transcoding)
Image processing: Generate thumbnails (150x150, 400x400, 1080x1080) using ImageMagick, store in S3 with CDN
Video processing: Transcode to multiple resolutions (360p, 720p, 1080p) using FFmpeg, HLS format for adaptive streaming
Post Consumer Service: Polls Kafka 'post.created', extracts metadata (dimensions, duration), updates PostDB with processed URLs
Step 4: Feed Generation (Fanout on Write)
Feed Service consumes: Kafka 'post.created' event with {post_id, user_id, created_at}
Service queries: Follower DB for all followers of user_id (e.g., 500 followers)
Service updates: Each follower's feed in Redis - LPUSH feed:{follower_id} {post_id}, LTRIM to keep latest 1000 posts
Redis structure: List data structure feed:{user_id} = [post_id_1, post_id_2, ..., post_id_1000] sorted by timestamp
Celebrity handling: If user has >5K followers, skip fanout on write, use pull model (fetch posts on demand during feed load)
Hybrid model: Small users (<5K) use push (fanout on write), celebrities use pull (fanout on read), medium users (1K-5K) use hybrid
Step 5: Feed Loading (Pull Model)
Client requests: GET /api/v1/posts/feed?limit=20&offset=0 with Authorization header
Feed Service checks: Redis feed:{user_id} for cached feed
Cache hit: LRANGE feed:{user_id} 0 19 returns list of post_ids [post_123, post_456, ...]
Service fetches: Post details from PostDB using post_ids (batch query with IN clause), includes {content, media_urls, created_at, user_id}
Service enriches: Fetch engagement counts (likes, comments) from Like DB and Comment DB, fetch author details from User DB
Cache miss: For celebrities or cold feeds, query FollowDB for followed users, fetch their recent posts from PostDB sorted by timestamp, cache result
Service returns: {posts: [{post_id, author: {user_id, username, profile_pic}, content, media_urls, likes_count, comments_count, created_at}], next_offset: 20}
Step 6: Like/Comment Interaction
Client sends: POST /api/v1/posts/{post_id}/like with user_id from JWT
Engagement Service checks: Redis cache like:{user_id}:{post_id} for idempotency (prevent double-like)
Service writes: Like record to Like DB (Cassandra) with composite key (post_id, user_id, created_at)
Service increments: Like counter in Redis - INCR likes_count:{post_id}, async sync to PostDB every 5 min (write batching)
Service publishes: Event to Kafka 'post.liked' topic for notification service
Comment flow: Similar but writes to Comment DB with support for nested threads using parent_comment_id field
Denormalization: PostDB stores like_count and comment_count for fast reads, updated via background job from Like/Comment DB
Step 7: Follow/Unfollow Operation
Client sends: POST /api/v1/users/{user_id}/follow with follower_id from JWT
Follower Service validates: Not already following, not self-follow, user exists
Service creates: Follower record in Follower DB with {follower_id, followee_id, created_at}
Service updates: Follower counts - INCR followers_count:{followee_id} and INCR following_count:{follower_id} in Redis
Service triggers: Backfill job to add followee's recent posts (last 100) to follower's feed in Redis
Unfollow: DELETE from Follower DB, decrement counts, purge followee's posts from follower's feed (LREM)
Step 8: Notification Generation
Notification Service consumes: Kafka topics 'post.liked', 'post.commented', 'user.followed'
Service checks: User preferences for notification types (likes: true, comments: true, follows: true)
Service aggregates: Multiple likes within 5 min → single notification 'John and 15 others liked your post'
Service publishes: To notification topic with {user_id, type, message, actor_ids[], post_id, created_at}
Delivery: Push notification via FCM/APNS, in-app notification stored in Notification DB (PostgreSQL)
Read receipts: Mark as read updates notification status, cleanup after 30 days
Step 9: Search Functionality
Client sends: GET /api/v1/search?q=john&type=users&limit=10
Search Service routes: To Elasticsearch cluster with query DSL
User search: Match query on username, name, bio fields with fuzzy matching (edit distance 2)
Post search: Full-text search on content field with hashtag extraction, time-based boosting (recent posts ranked higher)
Index updates: Post Consumer Service indexes new posts to Elasticsearch async via Kafka
Autocomplete: Prefix query on username field with suggest API for typeahead, cached in Redis for popular searches
Step 10: CDN & Media Delivery
Media request: Client requests https://cdn.example.com/media/{user_id}/{uuid}.jpg
CDN (CloudFront) checks: Edge location cache for media, cache hit returns immediately (<50ms)
Cache miss: CDN fetches from S3 origin, caches with TTL=30 days for images, 7 days for videos
Optimization: Serve optimized images based on device (mobile gets 400x400, desktop gets 1080x1080) using CloudFront Lambda@Edge
Video streaming: HLS manifest (m3u8) with multiple bitrates, adaptive streaming based on network speed
Purge strategy: On post deletion, invalidate CDN cache via API call, S3 object marked for deletion (lifecycle policy)
7. Client-Side Components

Component 1: Feed UI - Infinite scroll with virtual scrolling for performance, lazy load images
Component 2: Post Composer - Rich text editor with @mentions autocomplete, media upload with progress bar
Component 3: Interaction Buttons - Optimistic UI updates (like button animates immediately, rollback on failure)
Component 4: Media Player - Video player with adaptive bitrate streaming, thumbnail previews
Component 5: Notification Center - Real-time updates via WebSocket or SSE, unread badge count
Component 6: Search Bar - Debounced autocomplete (300ms delay), recent searches cached locally
Component 7: Profile Manager - Edit profile, privacy settings, account management
8. Database Schema Details

Users (PostgreSQL with read replicas)
user_id — uuid PRIMARY KEY
username — varchar(50) UNIQUE, INDEXED
email — varchar(255) UNIQUE, INDEXED
password_hash — varchar(255) (bcrypt with cost 12)
full_name — varchar(255)
bio — text (max 500 chars)
profile_pic_url — varchar(500)
followers_count — bigint DEFAULT 0 (denormalized for fast reads)
following_count — bigint DEFAULT 0
posts_count — bigint DEFAULT 0
created_at — timestamp
updated_at — timestamp
Posts (Cassandra - optimized for writes)
user_id — uuid (partition key - distributes posts by user)
created_at — timestamp (clustering key DESC - sorts posts newest first)
post_id — uuid (clustering key - uniqueness within user partition)
content — text (post caption, max 5000 chars)
media_urls — list<text> (array of S3 URLs for images/videos)
media_metadata — map<text, text> (dimensions, duration, thumbnails)
visibility — text (public, friends, private)
likes_count — bigint (denormalized, updated by background job)
comments_count — bigint
hashtags — set<text> (extracted from content)
mentions — set<uuid> (user_ids mentioned in post)
is_deleted — boolean (soft delete flag)
PostDB_indexed (Secondary index for global queries)
post_id — uuid PRIMARY KEY (allows global post lookup)
user_id — uuid INDEXED
created_at — timestamp INDEXED (for feed queries)
content — text
media_urls — jsonb
likes_count — bigint
comments_count — bigint
Followers (PostgreSQL or Graph DB)
follower_id — uuid (who is following)
followee_id — uuid (who is being followed)
created_at — timestamp
status — enum (pending, accepted) for friend requests
PRIMARY KEY — (follower_id, followee_id)
INDEX — on followee_id for reverse lookup (find all followers)
Likes (Cassandra - high write volume)
post_id — uuid (partition key)
user_id — uuid (clustering key)
created_at — timestamp (clustering key for ordering)
reaction_type — text (like, love, haha, wow, sad, angry)
metadata — map<text, text>
PRIMARY KEY — (post_id, user_id) - composite for uniqueness
Comments (PostgreSQL with nested structure)
comment_id — uuid PRIMARY KEY
post_id — uuid INDEXED FK → Posts
user_id — uuid FK → Users
parent_comment_id — uuid NULL (NULL for top-level, UUID for replies)
content — text (max 2000 chars)
likes_count — bigint DEFAULT 0
created_at — timestamp INDEXED
updated_at — timestamp
is_deleted — boolean
FeedDB (Redis - precomputed feeds)
feed:{user_id} — LIST of post_ids (LPUSH new posts, LTRIM to 1000)
likes_count:{post_id} — STRING counter (INCR on like, DECR on unlike)
comments_count:{post_id} — STRING counter
like:{user_id}:{post_id} — STRING flag (exists = liked, for idempotency)
followers_count:{user_id} — STRING counter (synced to PostgreSQL hourly)
following_count:{user_id} — STRING counter
Elasticsearch Index (posts_index)
post_id — keyword (unique identifier)
user_id — keyword
username — text with autocomplete analyzer
content — text with standard analyzer (full-text search)
hashtags — keyword array (exact match, aggregations)
created_at — date (for sorting and range filters)
likes_count — integer (for popularity boosting)
visibility — keyword (filter private posts)
9. Feed Ranking & Recommendation

Feed Ranking Algorithm
Trigger: User loads feed, service fetches candidate posts from Redis or Pull model
Scoring: Each post scored based on: (1) Recency - exponential decay (posts <1 hour = 1.0, 1 day = 0.5, 7 days = 0.1), (2) Engagement - likes_count * 0.3 + comments_count * 0.5, (3) Author affinity - close friends (frequent interactions) weighted 2x
Ranking: Sort posts by composite score = recency_score * 0.4 + engagement_score * 0.4 + affinity_score * 0.2
Diversity: Inject content from less-followed users (10% of feed) to prevent echo chambers
ML Model: Advanced systems use gradient boosted trees (XGBoost) trained on click-through rate, watch time, shares to predict engagement probability
Fanout Models Comparison
Push Model (Fanout on Write): When user posts, immediately push to all followers' feeds. Pros: Fast read (feed pre-generated), Cons: Slow write (500 followers = 500 writes), storage intensive (1000 posts * 500 followers = 500K feed entries)
Pull Model (Fanout on Read): When user loads feed, fetch posts from followed users on-demand. Pros: Fast write (single post write), no storage overhead, Cons: Slow read (query 100 followed users' posts, sort, merge)
Hybrid Model: Push for users with <5K followers, Pull for celebrities (>5K), Mixed for medium (1K-5K). Example: Taylor Swift (500M followers) uses pull, normal user uses push, verified accounts (100K followers) use hybrid
Implementation: Celebrity flag in User table, Feed Service checks before fanout, uses pull model for celebrity posts
10. Scaling & Optimization

Technique 1: Database Sharding - Posts sharded by user_id (1000 shards), Followers sharded by follower_id, enables horizontal scaling
Technique 2: Read Replicas - 5 PostgreSQL replicas for User reads (profile views), writes go to primary only, 99% queries hit replicas
Technique 3: Redis Caching - Feed cache (TTL=10 min), user profile cache (1 hour), like counts (5 min), reduces DB load by 90%
Technique 4: CDN for Media - CloudFront caches images/videos at edge locations, 95% cache hit rate, reduces S3 reads by 95%
Technique 5: Lazy Loading - Infinite scroll loads 20 posts at a time, images lazy loaded when in viewport, reduces initial page load from 5s to 500ms
Technique 6: Kafka for Async - Post creation, feed fanout, notifications all async via Kafka, decouples write from propagation
Technique 7: Connection Pooling - API servers maintain 100 DB connections each (50 servers = 5K total), reduces connection overhead from 50ms to 1ms
Technique 8: Denormalization - Like counts, follower counts stored in Post/User tables, avoids expensive COUNT queries, updated by background jobs
Technique 9: Batch Processing - Like count updates batched every 5 min (1000 likes = 1 DB write instead of 1000), reduces write load by 100x
Technique 10: Elasticsearch for Search - Async indexing via Kafka, handles 10K searches/sec, autocomplete with <50ms latency
Technique 11: Rate Limiting - 1K requests/min per user prevents abuse, 100 posts/day limit prevents spam
Technique 12: WebSocket for Real-time - Notifications delivered via WebSocket persistent connections, 1M concurrent connections per server
11. Common Interview Questions

Q
Why use fanout on write instead of fanout on read for normal users?
A
Read-heavy optimization: Social media has 100:1 read/write ratio. Users read feeds 100x more than posting. Fanout on write:

(1) Fast reads - feed pre-generated in Redis, LRANGE returns 20 posts in <10ms,

(2) Predictable latency - post creation takes 200ms to fanout to 500 followers, but every feed load is <50ms,

(3) Better user experience - users don't wait for feed generation, instant scroll. Trade-off: Write amplification (1 post = 500 writes) vs slow reads (query 100 users' posts, sort, merge = 500ms). For celebrities with 10M followers, fanout on write is impractical (1 post = 10M writes, takes minutes), so we use pull model where fans query celebrity's posts on-demand.

Q
How do you handle the celebrity/hotspot problem in feed generation?
A
Multi-tier approach:

(1) User classification - Flagging users as celebrity (>5K followers) in User table,

(2) Hybrid fanout - Push model for <5K followers (precompute feeds), Pull model for >5K (fetch on-demand),

(3) Feed merging - During feed load, combine pushed posts (from normal users) + pulled posts (from celebrities) and sort by timestamp,

(4) Caching - Celebrity posts cached separately in Redis with higher TTL (1 hour vs 10 min), all followers share same cache,

(5) Pagination - Celebrity timelines paginated, followers see latest 100 posts max. Example: User follows 90 normal users (pushed feeds) + 10 celebrities (pulled). Feed Service: LRANGE feed:{user_id} for pushed, fetch celebrity posts from PostDB, merge and rank. Performance: Combined latency 100ms (50ms pushed + 50ms pulled) vs pure pull would be 500ms.

Q
How do you ensure consistency between like counts in cache vs database?
A
Eventual consistency with reconciliation:

(1) Write path - user likes post → write to Like DB (Cassandra), increment Redis counter INCR likes_count:{post_id},

(2) Background sync - cron job runs every 5 min, queries Like DB for actual count (SELECT COUNT(*) GROUP BY post_id), updates PostDB with authoritative count,

(3) Cache invalidation - if Redis count differs from DB by >10%, invalidate cache and reload from DB,

(4) Conflict resolution - DB is source of truth, Redis is best-effort cache. Edge cases: Redis evicts key due to memory pressure → next read fetches from DB, subsequent reads cache again. Redis crashes → all counters lost → background job rebuilds from DB within 5 min. Accept window: Counters may be off by ±5% for <5 min, acceptable for social media (not financial system). Alternative: Use Redis persistence (AOF + RDB) for durability, but adds write latency 10ms → 50ms.

Q
What happens if a user with 1M followers posts? How do you prevent system overload?
A
Rate limiting + async processing:

(1) Classification - user_id tagged as 'celebrity' if followers_count > 5K, stored in User table,

(2) Bypass fanout - celebrity posts skip push fanout entirely, stored only in PostDB,

(3) Pull model - when follower loads feed, query celebrity's recent posts (last 100) from PostDB, merge with normal pushed posts,

(4) Async notification - instead of 1M push notifications, send to notification aggregator, batch into 'trending' notifications,

(5) Rate limiting - limit celebrity to 10 posts/hour to prevent spam. Implementation: Feed Service checks if poster.followers_count > 5K, if yes: write to PostDB only, publish 'celebrity.posted' event to Kafka, skip fanout worker. Followers see post when they load feed (pull), not pushed to their feeds. Notification Service sends to 1000 most engaged followers immediately, rest get aggregated daily digest. Prevents: 1M database writes, 1M Redis writes, 1M push notifications from overwhelming system.

Q
How do you handle nested comment threads efficiently?
A
Hierarchical storage with lazy loading:

(1) Database schema - Comment table has parent_comment_id (NULL for top-level, UUID for replies), creates tree structure,

(2) Loading strategy - fetch top-level comments first (WHERE parent_comment_id IS NULL LIMIT 20), load replies only when user expands thread (WHERE parent_comment_id = {comment_id}),

(3) Depth limit - max 3 levels (post → comment → reply → no further nesting) to prevent UI complexity,

(4) Denormalization - each comment stores reply_count for 'Show 5 replies' link without counting,

(5) Sorting - top-level sorted by likes_count DESC (best first), replies sorted by created_at ASC (chronological). Query optimization: Composite index on (post_id, parent_comment_id, created_at) enables fast queries. Alternative: Nested set model or closure table for complex hierarchies, but adds write complexity. Example: Post has 10K comments → fetch top 20, user expands comment #5 → fetch replies WHERE parent_comment_id = comment_5_id LIMIT 10, lazy load 'Show more' pagination.

Q
How do you implement real-time notifications without polling?
A
WebSocket + pub/sub pattern:

(1) Connection - client opens WebSocket to Notification Service on app launch, authenticated via JWT,

(2) Subscription - server subscribes to Redis pub/sub channel notifications:{user_id},

(3) Event flow - when user A likes user B's post, Engagement Service publishes to Redis channel 'notifications:{user_B_id}',

(4) Push - Notification Service listening on that channel receives event, sends JSON over WebSocket to user B's client,

(5) Fallback - if client offline, store notification in Notification DB, deliver when client reconnects. Scalability: 1M concurrent WebSocket connections = 1000 servers (1K connections each), Redis pub/sub handles 100K messages/sec, load balanced using consistent hashing on user_id. Alternative: Server-Sent Events (SSE) for one-way streaming (simpler), or long polling (fallback for old browsers). Battery optimization: Mobile apps use FCM/APNS push notifications instead of persistent WebSocket, WebSocket only for active users in-app.

Q
How do you handle media upload failures and retries?
A
Multi-stage upload with resumability:

(1) Presigned URL - client requests POST /api/v1/posts/upload/init, server generates presigned S3 PUT URL (valid 15 min), returns {upload_id, presigned_url},

(2) Chunked upload - for large files (>100MB), client uses multipart upload, splits into 5MB chunks, uploads in parallel (10 concurrent),

(3) Progress tracking - each chunk upload stores progress in Redis upload:{upload_id} = {chunks_uploaded: [1,2,3], total_chunks: 20},

(4) Retry - on failure, client queries GET /api/v1/posts/upload/{upload_id}/status, server returns missing chunks, client uploads only missing parts,

(5) Finalize - after all chunks uploaded, client calls POST /api/v1/posts/upload/{upload_id}/complete, server assembles chunks in S3, creates post. Timeouts: Presigned URL expires in 15 min, upload_id expires in 24 hours (Redis TTL). Network resilience: Exponential backoff (1s, 2s, 4s), circuit breaker after 3 consecutive failures. Alternative: Direct S3 multipart upload using AWS SDK, but loses control over progress tracking.

Q
What's your database partitioning strategy for Posts at scale?
A
Multi-dimensional sharding:

(1) Primary partitioning - Cassandra partitions by user_id (partition key), distributes user's posts across cluster based on hash(user_id), each node handles 1000 users,

(2) Clustering - within partition, sort by (created_at DESC, post_id) for efficient time-range queries,

(3) Global access - separate PostDB_indexed table with post_id as primary key for direct post lookup (GET /posts/{post_id}),

(4) Replication - RF=3 for high availability, QUORUM consistency for reads/writes. Query patterns: User timeline (SELECT * FROM posts WHERE user_id = {id} LIMIT 20) hits single partition = fast. Feed generation (SELECT * FROM posts WHERE user_id IN (100 followees)) fans out to 100 partitions = slow, mitigated by fanout on write. Hotspots: Celebrity users have high partition load, mitigated by pull model (followers query celebrity partition, not written to follower feeds). Scaling: Add nodes increases partition count from 1000 to 2000, Cassandra rebalances automatically using consistent hashing.

Q
How do you prevent duplicate likes when user clicks multiple times?
A
Multi-layer idempotency:

(1) Client-side - debounce like button 300ms, disable button immediately on click (optimistic UI),

(2) API level - check Redis cache like:{user_id}:{post_id}, if exists return 200 OK (already liked),

(3) Database level - Cassandra composite primary key (post_id, user_id) enforces uniqueness, duplicate insert fails silently,

(4) Transaction - atomic check-and-set in Redis: if SETNX like:{user_id}:{post_id} success → write to DB + INCR counter, if fails → already liked,

(5) Race condition - if 2 parallel requests both pass Redis check (race), Cassandra constraint prevents duplicate, one request succeeds, other gets 409 Conflict. Implementation: POST /api/v1/posts/{post_id}/like checks Redis, if not exists: start transaction, write to Like DB, set Redis key (TTL=24h), increment counter, commit. Counters: Use INCR for increment, DECR for unlike, background job syncs actual count from DB every 5 min to fix any drift. Edge case: Redis eviction loses idempotency cache → user can re-like → DB constraint prevents duplicate row, counter incremented correctly.

Q
How do you implement privacy controls (public vs friends-only posts)?
A
Multi-layer visibility filtering:

(1) Storage - Post table has visibility enum (public, friends, private),

(2) Feed generation - during fanout on write, check relationship between poster and follower, only push to feeds if: visibility=public OR (visibility=friends AND is_mutual_follower),

(3) Direct access - GET /posts/{post_id} checks: if public → allow, if friends → verify requester.user_id in poster's friends list, if private → only author can view,

(4) Feed filtering - pull model queries: SELECT * FROM posts WHERE user_id IN (followees) AND (visibility = 'public' OR (visibility = 'friends' AND mutual = true)),

(5) Caching - privacy checks cached in Redis friend:{user_A}:{user_B} = boolean (TTL=1 hour). Friend determination: Mutual follow check - query Followers table for bidirectional edge (A follows B AND B follows A). Performance: Privacy checks add 10ms latency, mitigated by batch checking (verify 100 posts in single Redis MGET). Alternative: Facebook-style fine-grained lists (close friends, acquaintances, custom lists), stored as relationship tags in graph database.

12. Key Numbers to Remember

Scale & Volume
Daily Active Users — 500M DAU (2 billion total registered users)
Posts Created — 100M posts/day = 1.2K posts/second average
Feed Loads — 10 billion feed requests/day = 115K req/sec
Media Storage — Petabytes total, 10TB uploaded daily
Read/Write Ratio — 100:1 (heavy read system)
Performance Metrics
Feed Load Latency — p95 <500ms (includes 20 posts with media thumbnails)
Like/Comment Latency — p95 <200ms (Redis write + DB async)
Post Creation — p95 <300ms (write to DB, publish to Kafka, fanout async)
Media Upload — 100MB video in ~30s (S3 direct upload)
Search Latency — p95 <100ms (Elasticsearch autocomplete)
Caching & Storage
Feed Cache — Redis stores latest 1000 posts per user, TTL=10 min
Profile Cache — TTL=1 hour, reduces DB reads by 90%
Like Count Cache — TTL=5 min, synced to DB every 5 min
CDN Cache Hit — 95% for images/videos, TTL=30 days
DB Replication — 5 read replicas for PostgreSQL, 99% reads from replicas
Fanout & Feed
Normal User Fanout — <5K followers = push model (fanout on write)
Celebrity Fanout — >5K followers = pull model (fanout on read)
Fanout Latency — 500 followers in 200ms (100 writes/sec per worker)
Feed Size — 1000 posts cached per user = 1KB per post = 1MB/user
Feed Refresh — Pull latest 20 posts every scroll
Database Partitioning
Posts Sharding — 1000 shards by user_id, 1M users per shard
Cassandra Writes — 10K writes/sec per node, 100 nodes = 1M writes/sec
PostgreSQL — 5 read replicas, 1 primary, handle 50K reads/sec
Replication Factor — RF=3 for Cassandra, tolerates 1 node failure
Rate Limits & Quotas
API Rate Limit — 1000 requests/min per user
Post Creation Limit — 100 posts/day per user (prevents spam)
Media Upload Size — Max 500MB per file, 10 files per post
Follow Limit — 1000 follows/day (anti-spam)
Comment Length — Max 2000 characters
Example Calculation - Feed Load
Step 1: Redis Feed Query — LRANGE feed:{user_id} 0 19 = 10ms (20 post_ids)
Step 2: Batch Post Fetch — SELECT * WHERE post_id IN (...) = 50ms (20 posts from PostDB)
Step 3: User Info Fetch — SELECT * WHERE user_id IN (...) = 30ms (20 authors from cache)
Step 4: Engagement Counts — MGET likes:{post_id} x20 = 20ms (Redis batch)
Total Feed Load — 110ms (well under 500ms p95 target)
Cost Optimization
CDN Savings — 95% cache hit = 95% fewer S3 reads = $10K/month saved
Redis Savings — 90% fewer DB queries = 10x fewer DB instances needed
Denormalization — Storing counts avoids COUNT(*) queries (100ms → 1ms)
Batch Updates — Like counts batched = 100x fewer DB writes
S3 Lifecycle — Move old media to Glacier after 1 year = 90% storage cost reduction
Key Interview Tips

⚠️
NEVER use fanout on write for celebrities with millions of followers. 1 post = 10M writes would take minutes and overwhelm the system. Always use pull model (fanout on read) for users with >5K followers.

⭐
Interviewers ALWAYS ask: 'Why use Redis for feed instead of database?'. Answer: (1) Speed - LRANGE from Redis <10ms vs DB query 100ms+, (2) Scalability - Redis handles 100K ops/sec, (3) Feed is ephemeral data, loss is acceptable (rebuild from DB), (4) Reduces DB load by 90%.

💡
Key optimization: Denormalization. Store like_count, comment_count, follower_count IN the Post/User tables. COUNT(*) queries are expensive (100ms+), denormalized counts are instant (1ms). Accept eventual consistency - counts updated by background jobs every 5 min.

⭐
Must mention: 100:1 read/write ratio for social media. Users scroll feeds 100x more than posting. Optimize for READS (caching, CDN, read replicas) over writes. This is why fanout on write works - slow write (once) enables fast reads (100x).

⚠️
NEVER store media in database as BLOBs. Use S3 for object storage, store only URLs in database. BLOB storage: slow queries, expensive replication, no CDN support. S3: cheap ($0.023/GB/month), durable (11 9's), CDN-friendly.

💡
Hybrid fanout model is critical at scale. Push model (<5K followers) enables instant feeds. Pull model (>5K) prevents write amplification. Medium users (1K-5K) use hybrid: push to active followers, pull for inactive. This handles 99% of users efficiently.

⭐
Interviewers love asking: 'How to handle hot partition in Cassandra?'. Answer: Celebrity users create hotspots (1M followers all query same partition). Solution: (1) Pull model - distribute load across follower reads, not write-heavy fanout, (2) Cache celebrity posts in Redis, (3) Add read replicas for hot partitions.

⚠️
NEVER synchronously process media during upload. Video transcoding takes 30s-5min. Return 202 Accepted immediately, process async via Lambda/queue. User sees 'Processing...' status, gets notification when complete. Synchronous = API timeout + poor UX.

💡
Idempotency is critical for likes. User clicks like button 3 times due to slow network → only 1 like recorded. Use Redis SETNX + Cassandra composite key (post_id, user_id). Both layers prevent duplicates even under race conditions.

⭐
Must explain: Why eventual consistency is acceptable for social media. Like counts off by 10 for 5 min? Not critical. Feed shows post 2 seconds late? Fine. Unlike banking (need strong consistency), social media prioritizes availability + low latency over perfect consistency (AP in CAP theorem).

system-design
social-media
Facebook
Instagram
feed-generation
fanout-on-write
fanout-on-read
Cassandra
PostgreSQL
