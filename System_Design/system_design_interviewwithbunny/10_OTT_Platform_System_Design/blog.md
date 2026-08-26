OTT Platform (Netflix/Amazon Prime/Hotstar)

> **Related:** [INTERVIEW_GUIDE.md](INTERVIEW_GUIDE.md) — word-for-word interview script with diagrams, ABR deep-dive, senior trap questions, and key numbers to memorize.

"Video upload (transcoding) → CDN delivery → Adaptive Streaming (HLS/DASH) → Low-latency playback → Subscription management → Analytics"

1. Functional Requirements

Feature 1: User should be able to create account and opt for subscription (register/login/logout/subscription plans)
Feature 2: User should be able to search and find movies/shows based on product title or names
Feature 3: Users can watch videos in different resolutions (1080p, 4K, 720p, 480p, etc.) based on device and network
Feature 4: User should be able to watch the video without nominal or negligible buffering (adaptive streaming)
Feature 5: Content creators can upload videos (movies, series, documentaries) with metadata
2. Non-Functional Requirements

Scale
Users — 200M users and 10k total videos (~1 hour each)
Daily Active Users — 20M DAU streaming video
Storage — Total: 400M = 10k videos × 400k GB = 400TB (accounting for multiple resolutions)
Performance & Availability
CAP Theorem — Highly available >> consistency (eventual consistency acceptable for metadata)
Video Streaming — Low-latency streaming with adaptive bitrate (HLS/DASH)
Payment Consistency — Consistent with respect to placing the order & payment (strong consistency for subscriptions)
Buffering — Minimal buffering <2-3 seconds, smooth playback even on poor network
3. Core Entities (Identify Core Entity)

Entity 1: User - Customer with user_id, name, email, subscription_status, watch_history[], preferences
Entity 2: User Metadata - Additional user data like device info, viewing patterns, subscription details
Entity 3: Video - Content with video_id, title, description, genre, duration, content_rating, release_date
Entity 4: Video Metadata & Static Image - Thumbnail, poster, metadata (actors, director, etc.), subtitles, audio tracks
4. API Designing

User Management
POST /v1/users/register — Register user {name, email, password} → {userId, token} (login/logout/fetch)
GET /v1/subscription/plans — Get available subscription plans → List<Plan>
POST /v1/subscriptions — Create subscription {userId, planId, paymentDetails} → SubscriptionId
Video Search & Discovery
GET /v1/videos/search — Search videos {q={name}} → List<VideoId (Partial)> with pagination
GET /api/v1/videos/{videoId} — Return the video details {metadata, thumbnails, available resolutions} (json)
Video Playback
GET /api/v1/videos/{videoId}/play — Start the video → Return master playlist URL (HLS/DASH manifest)
GET /api/v1/videos/{videoId}/stream/{resolution} — Stream video chunks for specific resolution
5. High Level Design

Users → API Gateway: Load balancing, authentication, authorization, rate limiting
User Service → User DB: User profiles, authentication, preferences
Search Service → Elasticsearch: Video search by title, genre, actors with full-text search
Play Service: Generates manifest file (HLS/DASH) for video streaming
Uploader: Content creators upload raw video files to Blob storage (S3)
Video Processing Pipeline: Transcoding, compression, multiple resolutions (4K, 1080p, 720p, 480p, 360p)
Video Metadata DB: Stores video metadata, thumbnail URLs, available resolutions, subtitle tracks
Blob Storage (S3): Raw uploaded videos and transcoded video files (organized by video_id/resolution/)
CDN: Delivers video chunks with edge caching for low-latency global playback
6. Deep Dive Design (Low Level)

Step 1: Video Upload & Metadata
Content creator uploads: Raw video file (e.g., movie.mp4, 50GB 4K), metadata {title, description, genre, actors, duration, language}
Uploader service: (1) Generates video_id (UUID), (2) Creates multipart upload to S3: s3://videos-raw/{video_id}/original.mp4, (3) Stores metadata in Video Metadata DB: {video_id, title, description, genre, duration, upload_status: 'PROCESSING', created_at}
Upload completion: Triggers Lambda/SQS event with {video_id, s3_path}
Metadata includes: Title, description, genre[], actors[], director, release_date, content_rating (PG-13, R), language[], subtitle_tracks[], audio_tracks[], thumbnail_url, poster_url
Images uploaded separately: Thumbnails and posters to S3 → s3://video-images/{video_id}/thumbnail.jpg, served via CDN
Step 2: Video Transcoding Pipeline (Critical for Adaptive Streaming)
Trigger: Lambda consumes SQS message with {video_id, s3_path: 's3://videos-raw/{video_id}/original.mp4'}
Video transcoding service: (1) Downloads original video from S3, (2) Uses FFmpeg/AWS MediaConvert to transcode into multiple resolutions and bitrates, (3) Resolutions: 4K (3840×2160, 20 Mbps), 1080p (1920×1080, 8 Mbps), 720p (1280×720, 5 Mbps), 480p (854×480, 2.5 Mbps), 360p (640×360, 1 Mbps)
For EACH resolution: (a) Transcode video, (b) Split into segments/chunks (10-second chunks for HLS/DASH), (c) Upload to S3: s3://videos-processed/{video_id}/{resolution}/segment_001.ts, segment_002.ts, ..., (d) Generate manifest file (master.m3u8 for HLS or master.mpd for DASH)
HLS (HTTP Live Streaming): Apple standard, .m3u8 playlist, .ts video segments
DASH (Dynamic Adaptive Streaming over HTTP): MPEG standard, .mpd manifest, .m4s segments
Chunker service: Splits video into 10-second chunks, uploads to S3 organized by resolution
Manifest file structure: Master playlist points to resolution-specific playlists → each resolution playlist lists segment URLs
Example master.m3u8: #EXTM3U, #EXT-X-STREAM-INF:BANDWIDTH=8000000,RESOLUTION=1920x1080 → 1080p/playlist.m3u8, #EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1280x720 → 720p/playlist.m3u8
Video encoder: Compresses at different bitrates (lower bitrate for same resolution = smaller file, lower quality)
Update metadata: UPDATE video_metadata SET processing_status='COMPLETED', resolutions=['4K','1080p','720p','480p','360p'], manifest_url='s3://videos-processed/{video_id}/master.m3u8' WHERE video_id={video_id}
Transcoding time: ~30-60 min for 2-hour 4K movie using parallel processing on GPU instances
Cost optimization: Use spot instances for transcoding, auto-scale based on queue depth
Step 3: Video Search (Elasticsearch)
User searches: GET /v1/videos/search?q=Inception&genre=Sci-Fi&language=English
Search Service queries: Elasticsearch with full-text search on title, description, actors, director
ES query: { 'query': { 'bool': { 'must': [ { 'multi_match': { 'query': 'Inception', 'fields': ['title^3', 'description', 'actors', 'director'] } } ], 'filter': [ { 'term': { 'genre': 'Sci-Fi' } }, { 'term': { 'language': 'English' } } ] } }, 'sort': [ { 'popularity_score': 'desc' } ], 'size': 20 }
Popularity score: Combination of view_count, rating, recency, calculated offline and updated periodically
Response: [{ video_id, title, thumbnail_url, duration, rating, genre }]
Caching: Popular searches cached in Redis with TTL=10 min
CDC pipeline: Video Metadata DB → Kafka → Elasticsearch indexer keeps search index in sync
Index structure: Each video document has video_id, title (text), description (text), genre (keyword), actors (text), language (keyword), popularity_score (float), release_date (date)
Step 4: Video Playback Request
User clicks play: GET /api/v1/videos/{video_id}/play
Play Service: (1) Validates user subscription status (check if active subscription exists), (2) Fetches manifest URL from Video Metadata DB: SELECT manifest_url, resolutions FROM video_metadata WHERE video_id={video_id}, (3) Generates CDN-signed URL (CloudFront signed URL with expiry=4 hours), (4) Returns manifest URL to client: { manifest_url: 'https://cdn.example.com/{video_id}/master.m3u8?Expires=...&Signature=...' }
Client video player: (1) Fetches master.m3u8 manifest, (2) Parses available resolutions and bitrates, (3) Selects initial resolution based on network speed (adaptive bitrate logic), (4) Starts downloading video segments
Adaptive streaming: Player monitors buffer level and network speed, switches resolution dynamically (e.g., 1080p → 720p if network degrades)
Segment requests: GET https://cdn.example.com/{video_id}/1080p/segment_001.ts, segment_002.ts, ... (each segment ~2-3 MB for 10-second chunk)
CDN caching: Edge locations cache segments, 95%+ cache hit rate for popular content, <50ms latency
Player buffering: Downloads 3-5 segments ahead (30-50 seconds), ensures smooth playback even during network fluctuations
Step 5: Adaptive Streaming - How it Works
Adaptive bitrate streaming: Dynamically switches video quality based on network conditions
Player logic: (1) Measure download speed: time to download last segment / segment size = throughput (Mbps), (2) Estimate available bandwidth, (3) Select appropriate resolution: if bandwidth > 8 Mbps → 1080p, 5-8 Mbps → 720p, 2.5-5 Mbps → 480p, <2.5 Mbps → 360p
Switching: Player seamlessly switches between playlists (resolution levels) mid-playback without rebuffering
Buffer management: Maintain 20-40 second buffer, if buffer drops below 10 seconds → switch to lower quality to prevent stalling
Quality metrics: Track and minimize: (1) Initial buffering time (time to first frame), (2) Rebuffering events (mid-playback stalls), (3) Bitrate switches (too frequent = poor UX)
Example scenario: User starts watching on WiFi (8 Mbps) → Player selects 1080p → User moves, WiFi degrades to 3 Mbps → Player detects slow download → Switches to 480p → Buffering continues smoothly
Keyframe alignment: Ensure video segments start with I-frames (keyframes) for seamless quality switching
How this Adaptive Streaming works: (1) Switching happens only if keyframe is set at 0th second, (2) Now lets assume the keyframe is set at 0th second, (3) At this keyframe point depending on the client bandwidth, player's either can resume from the old video format(1080) or some or different resolution
Step 6: CDN Architecture for Video Delivery
CDN setup: Origin = S3 bucket (s3://videos-processed/), Edge locations = CloudFront PoPs (200+ globally)
Request flow: (1) User in India requests segment: GET cdn.example.com/{video_id}/1080p/segment_050.ts, (2) DNS routes to nearest edge (Mumbai PoP), (3) Edge checks cache, (4) If miss: Fetch from origin S3 (us-east-1) → 200ms, cache at edge for 24 hours, (5) If hit: Serve from edge cache → 10ms
Cache hit ratio: 95%+ for popular content (trending movies, recent releases)
Cache eviction: LRU (Least Recently Used), prioritize popular content
Origin shield: Additional caching layer between edge and origin, reduces origin load by 90%
Compression: Gzip/Brotli compression for manifest files (.m3u8, .mpd), saves bandwidth
Security: Signed URLs with expiry prevent hotlinking and unauthorized access, URL valid for 4 hours
Monitoring: CloudWatch tracks: cache hit rate, error rate (4xx, 5xx), bandwidth usage, origin requests
Cost: CDN bandwidth ~$0.085/GB, 10M users streaming 2 hours/day = 20M hours × 3 GB/hour × $0.085 = $5.1M/month in bandwidth
Step 7: Subscription Management
User subscribes: POST /v1/subscriptions with {user_id, plan_id: 'premium', payment_method_id}
Subscription Service: (1) Validates plan exists: SELECT * FROM subscription_plans WHERE plan_id={plan_id}, (2) Creates payment intent via Payment Gateway (Stripe/Razorpay) with {amount, currency, customer_id, metadata: {user_id, plan_id}}, (3) Returns payment_url to client
Payment success webhook: POST /webhooks/payment with {payment_id, status: 'success', metadata}, (1) Subscription Service: BEGIN TRANSACTION; INSERT INTO subscriptions (subscription_id, user_id, plan_id, status='ACTIVE', start_date=now(), end_date=now()+30days, payment_id); UPDATE users SET subscription_status='ACTIVE'; COMMIT;, (2) Publish Kafka event: 'subscription.created'
Subscription plans: Basic ($9/month, 720p, 1 screen), Standard ($13/month, 1080p, 2 screens), Premium ($17/month, 4K, 4 screens)
Auto-renewal: Cron job runs daily, checks subscriptions ending in 3 days, triggers payment for renewal, if payment fails → send notification, grace period 7 days before downgrade
Cancellation: PUT /v1/subscriptions/{subscription_id}/cancel → UPDATE subscriptions SET status='CANCELLED', cancelled_at=now(), access until end_date
Access control: On every video play request, validate: SELECT status, end_date FROM subscriptions WHERE user_id={user_id} AND status='ACTIVE' AND end_date > now(), if fails return 403 Forbidden with upgrade prompt
Step 8: Watch History & Recommendations
Tracking playback: Client sends heartbeat every 10 seconds: POST /v1/videos/{video_id}/progress with {user_id, current_time_seconds, device_id}
Play Service: (1) Updates watch progress in Redis: HSET watch_progress:{user_id}:{video_id} 'current_time' {current_time}, 'last_updated' {timestamp}, TTL=7 days, (2) Periodically (every 60s) batch writes to Cassandra/DynamoDB for persistence
Resume playback: GET /v1/videos/{video_id}/play → check Redis for watch_progress:{user_id}:{video_id}, return {resume_from: {current_time}}, client seeks to position
Watch history: Cassandra table {user_id, video_id, watched_at, completion_percentage, device_type} partitioned by user_id
Kafka event stream: Publish 'video.watched' events with {user_id, video_id, duration_watched, timestamp} → consumed by Recommendation Service and Analytics Service
Recommendation engine: (1) Collaborative filtering: Users who watched video X also watched Y, (2) Content-based: Recommend similar genre/actors, (3) ML model (TensorFlow) trained on watch history, ratings, search queries → predicts user preferences, (4) Results cached in Redis per user, refreshed daily
Step 9: Analytics & Monitoring
Real-time analytics: Kafka stream processing with Apache Flink/Spark Streaming
Metrics tracked: (1) Play events (video started, paused, completed), (2) Quality metrics (buffering events, bitrate changes, errors), (3) Engagement (watch time, completion rate, drop-off points), (4) Popular content (trending videos by region)
Event schema: {event_type: 'play_started', user_id, video_id, device_type, resolution, timestamp, session_id, geo_location}
Aggregations: (1) Hourly: View counts per video, average watch time, buffering ratio, (2) Daily: User retention, content popularity rankings, revenue metrics
Storage: Raw events → Kafka → S3 (data lake) for long-term storage and batch analytics, Aggregated metrics → PostgreSQL/BigQuery for dashboards
Dashboards: Grafana/Tableau showing: concurrent viewers, bandwidth usage, cache hit rate, error rates, top videos, user growth
Alerts: PagerDuty/Opsgenie notifications for: CDN errors >1%, origin load >80%, transcoding queue depth >1000, subscription payment failures >5%
Step 10: Content Delivery Optimization
Pre-warming CDN cache: For new releases, pre-fetch segments to edge locations before launch (predictive caching)
Peak load handling: Auto-scale video processing workers, CDN bandwidth, API servers during new release (e.g., new season drops)
Geo-based optimization: Store video files in regional S3 buckets (us-east-1, eu-west-1, ap-south-1), CDN fetches from nearest origin
Compression: Use H.265/HEVC codec instead of H.264 for 40-50% better compression (smaller files, same quality), but requires decoder support
Thumbnail optimization: Generate multiple thumbnail sizes (small, medium, large), serve WebP format (30% smaller than JPEG)
Preloading: Client preloads first 2-3 segments of next episode for binge-watching (reduce time to start next episode)
Offline downloads: Mobile app feature, download encrypted video to local storage, DRM ensures can't be copied, expires after subscription ends
7. Database Schema Details

Users (PostgreSQL)
user_id — uuid PRIMARY KEY
name — varchar(255)
email — varchar(255) UNIQUE
password — varchar(255) (bcrypt hash)
subscription_status — enum (ACTIVE, INACTIVE, CANCELLED)
subscription_id — uuid FK → Subscriptions
metadata — jsonb (preferences, device info, viewing patterns)
expire_date — timestamp (subscription expiry)
Video Metadata (PostgreSQL or MongoDB)
video_id — uuid PRIMARY KEY
title — varchar(500)
description — text
genre — varchar(100)[] (array: ['Action', 'Thriller'])
actors — varchar(255)[] (with external actor_id mapping)
director — varchar(255)
duration — integer (seconds)
release_date — date
content_rating — varchar(10) (PG-13, R, TV-MA)
language — varchar(50)[] (primary language + dubbed versions)
subtitle_tracks — jsonb [{lang: 'en', url: 's3://...'}, {lang: 'es', url: '...'}]
audio_tracks — jsonb [{lang: 'en', type: '5.1'}, {lang: 'hi', type: 'stereo'}]
thumbnail_url — varchar(500) (CDN URL)
poster_url — varchar(500)
manifest_url — varchar(500) (master.m3u8 or master.mpd)
resolutions — varchar(10)[] (['4K', '1080p', '720p', '480p', '360p'])
processing_status — enum (UPLOADING, PROCESSING, COMPLETED, FAILED)
Subscriptions (PostgreSQL)
subscription_id — uuid PRIMARY KEY
user_id — uuid FK → Users
plan_id — varchar(50) FK → SubscriptionPlans
status — enum (ACTIVE, CANCELLED, EXPIRED, PAYMENT_FAILED)
start_date — timestamp
end_date — timestamp
payment_id — varchar(255) (from payment gateway)
auto_renew — boolean
SubscriptionPlans (PostgreSQL)
plan_id — varchar(50) PRIMARY KEY
name — varchar(100) (Basic, Standard, Premium)
price — decimal(10,2)
currency — varchar(3)
max_resolution — varchar(10) (720p, 1080p, 4K)
max_screens — integer (concurrent devices allowed)
billing_period — varchar(20) (monthly, annual)
Watch_History (Cassandra/DynamoDB - high write throughput)
Partition Key — user_id
Clustering Key — watched_at DESC (sort by recency)
video_id — uuid
current_time — integer (seconds watched)
completion_percentage — integer (0-100)
device_type — varchar(50) (web, iOS, Android, TV)
Elasticsearch - Video Search Index
video_id — keyword
title — text (analyzed for full-text search)
description — text
genre — keyword (exact match for filters)
actors — text
director — text
language — keyword
popularity_score — float (for ranking)
release_date — date
Redis - Caching & Session
watch_progress:{userId}:{videoId} — HASH {current_time, last_updated} TTL 7 days
search:{hash(query+filters)} — STRING (JSON search results) TTL 10 min
user:{userId}:subscription — STRING (JSON subscription details) TTL 1 hour
recommendations:{userId} — LIST [video_ids] TTL 24 hours
S3 - Blob Storage Structure
videos-raw/ — {video_id}/original.mp4 (uploaded raw files)
videos-processed/ — {video_id}/{resolution}/segment_001.ts, segment_002.ts, ... + manifest files
video-images/ — {video_id}/thumbnail.jpg, poster.jpg
subtitles/ — {video_id}/{language}.vtt (WebVTT subtitle files)
Kafka Topics
video.uploaded — {video_id, s3_path, metadata} - triggers transcoding
video.transcoded — {video_id, resolutions[], manifest_url} - updates search index
video.watched — {user_id, video_id, duration, timestamp} - analytics & recommendations
subscription.created — {user_id, plan_id, payment_id} - notifications
subscription.renewed — {subscription_id, end_date} - consumer updates user access
8. Streaming Protocols Deep Dive

HLS (HTTP Live Streaming) - Apple Standard
Format — Master playlist (.m3u8) → Resolution playlists (.m3u8) → Segments (.ts files, 10 sec each)
Master Playlist — #EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=8000000,RESOLUTION=1920x1080\n1080p/playlist.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1280x720\n720p/playlist.m3u8
Resolution Playlist — #EXTM3U\n#EXT-X-TARGETDURATION:10\n#EXTINF:10.0,\nsegment_001.ts\n#EXTINF:10.0,\nsegment_002.ts
Browser Support — Safari (native), Chrome/Firefox (via hls.js library)
Advantages — Wide support (iOS, macOS, most smart TVs), adaptive bitrate, reliable
DASH (Dynamic Adaptive Streaming over HTTP) - MPEG Standard
Format — Media Presentation Description (.mpd XML) → Segments (.m4s files)
MPD Structure — XML with <AdaptationSet> per resolution, <Representation> defines bitrate/resolution, <SegmentTemplate> for segment URLs
Browser Support — Chrome, Firefox, Edge (via dash.js), NOT Safari (use HLS for Apple)
Advantages — Codec agnostic (H.264, H.265, VP9), DRM support, open standard
Comparison: HLS vs DASH
HLS Pros — Apple ecosystem support, simpler format, broad device compatibility
DASH Pros — Codec flexibility, lower latency possible, open standard
Production Choice — Most platforms support BOTH: serve HLS for Apple devices, DASH for others
Segment Duration — HLS: 10 sec typical, DASH: 2-10 sec (lower = better adaptability, more requests)
For Reference: DASH vs HLS Differences
Manifest Format — HLS: .m3u8 (Media Playlist), DASH: .mpd (Media Presentation Description)
Segment Format — HLS: .ts (Transport Stream) or .m4s, DASH: .m4s (fragmented MP4) or .webm
Codec Binding — HLS: Mostly H.264 (can use H.265), DASH: Codec agnostic (H.264, H.265, VP9, AV1)
Segment Loading — HLS: Can fetch bytes/s at once, DASH: Loads only only one bitrate at a time
Latency — HLS: Lower latency (DASH-LL supports <2s), DASH: Higher latency (4-8 sec typically), supports LL-DASH
9. Estimation & Capacity Planning

Storage Calculation (from image)
1 Min Video — 720p: 100MB/hr, 1080p: 200MB/hr, 4K: 400MB/hr
1 Hour Video — 720p: 6GB, 1080p: 12GB, 4K: 24GB (approximate)
Total Videos — 10k videos × ~1 hour each
Per Video Storage — Original (4K): 24GB + Transcoded (4K + 1080p + 720p + 480p + 360p): ~16GB = 40GB per video
Total Storage — 10k videos × 40GB = 400TB ≈ 400M (400 million GB as mentioned in image)
Bandwidth & Traffic
Daily Active Users — 20M users streaming
Avg Watch Time — 2 hours per user per day
Avg Bitrate — 5 Mbps (mix of resolutions, weighted average)
Data per User — 5 Mbps × 2 hours = 10 Mb/sec × 7200 sec = 72,000 Mb = 9 GB per user
Total Daily Traffic — 20M users × 9 GB = 180M GB = 180 PB per day
Peak Concurrent Users — 2M concurrent (10% of DAU during prime time 8-11 PM)
Peak Bandwidth — 2M users × 5 Mbps = 10 Tbps (Terabits per second)
Transcoding Capacity
New Uploads — 100 new videos per day (movies + series episodes)
Transcoding Time — 1 hour video → ~30-60 min transcoding (parallel, GPU instances)
Worker Capacity — 50 transcoding workers (GPU instances) processing 24/7
Daily Capacity — 50 workers × 24 hours / 0.5 hour per video = 2400 videos/day (20x buffer)
Database & Cache
Video Metadata — 10k videos × 5 KB avg = 50 MB (tiny, fits in memory)
User Data — 200M users × 1 KB = 200 GB
Watch History — 200M users × 100 entries × 500 bytes = 10 TB (Cassandra)
Redis Cache — 100 GB (watch progress, search cache, recommendations)
10. Scaling & Optimization Techniques

Technique 1: CDN Multi-Tier Caching - CloudFront edge (200+ PoPs) → Origin Shield → S3, 95% cache hit rate, <50ms latency globally
Technique 2: Adaptive Bitrate Streaming (HLS/DASH) - Client auto-switches 4K ↔ 1080p ↔ 720p based on bandwidth, prevents buffering
Technique 3: Video Chunking (10-second segments) - Progressive download, fast seek, parallel downloads, efficient caching
Technique 4: Transcoding Pipeline Auto-Scaling - SQS queue triggers auto-scale (10-100 GPU workers), processes 100 videos/day
Technique 5: Elasticsearch for Search - Full-text search on title/actors/genre, <100ms latency, sharded by popularity
Technique 6: Redis for Watch Progress - HSET per user+video with TTL=7 days, batch write to Cassandra every 60s
Technique 7: Geo-Sharding S3 Buckets - Regional buckets (US, EU, Asia), CDN fetches from nearest origin, reduces latency 60%
Technique 8: Lazy Loading Thumbnails - Load images on-demand as user scrolls, WebP format (30% smaller than JPEG)
Technique 9: Pre-warming CDN for Releases - Push segments to edge locations before new season launch, instant playback
Technique 10: Compression Codecs - H.265/HEVC for 50% better compression vs H.264, AV1 for 30% better than H.265 (future)
Technique 11: Connection Pooling - API servers maintain 200 DB connections, prevents exhaustion at scale
Technique 12: Kafka Event Streaming - Async analytics, recommendations, notifications, decouples services, horizontal scaling
11. Common Interview Questions

Q
How does adaptive bitrate streaming work in Netflix/YouTube?
A
Adaptive bitrate streaming (ABR) dynamically adjusts video quality based on network conditions:

(1) Video preparation: Original video transcoded into multiple resolutions (4K/2160p at 20 Mbps, 1080p at 8 Mbps, 720p at 5 Mbps, 480p at 2.5 Mbps, 360p at 1 Mbps) using FFmpeg/MediaConvert,

(2) Segmentation: Each resolution split into 10-second chunks (segments),

(3) Manifest file: HLS master.m3u8 or DASH master.mpd lists all available resolutions with bitrates,

(4) Player logic:

(a) Client requests manifest,

(b) Measures current bandwidth by timing segment downloads: bandwidth = segment_size / download_time,

(c) Selects appropriate resolution: if bandwidth > 8 Mbps → request 1080p segments, 5-8 Mbps → 720p, 2.5-5 Mbps → 480p, <2.5 Mbps → 360p,

(d) Downloads segments sequentially,

(e) Monitors buffer level (20-40 sec ahead),

(f) If bandwidth drops or buffer depletes → switch to lower resolution for next segment,

(5) Seamless switching: Segments aligned on keyframes (I-frames at 0th second), player switches between playlists mid-playback without rebuffering,

(6) Quality metrics: Track initial buffering time, rebuffering events, bitrate switches (too frequent = poor UX). Example: User on WiFi (8 Mbps) → Player starts with 1080p → WiFi degrades to 3 Mbps → Player detects slow download after 2-3 segments → Switches to 480p → User continues watching without stall. Key insight from image: 'Switching happens only if keyframe is set at 0th second, at this keyframe point depending on client bandwidth, player either can resume from old video format

(1080) or some or different resolution.' HLS vs DASH: HLS uses .m3u8 + .ts segments (Apple standard), DASH uses .mpd + .m4s segments (MPEG standard, codec agnostic). Production: Serve both HLS (for Apple devices) and DASH (for others).

Q
Explain the video upload and transcoding pipeline end-to-end.
A
End-to-end video processing flow:

(1) Upload: Content creator uploads raw video (e.g., movie.mp4, 50GB 4K) + metadata {title, description, genre, actors, duration},

(2) Uploader Service:

(a) Generates video_id (UUID),

(b) Multipart upload to S3: s3://videos-raw/{video_id}/original.mp4 (parallel chunks for faster upload),

(c) Stores metadata: INSERT INTO video_metadata (video_id, title, processing_status='UPLOADING'),

(d) On upload completion → Publish Kafka event 'video.uploaded' with {video_id, s3_path},

(3) Transcoding Pipeline:

(a) Lambda/Worker consumes Kafka event,

(b) Downloads original from S3,

(c) FFmpeg/AWS MediaConvert transcodes to multiple resolutions: 4K (3840×2160, H.265, 20 Mbps), 1080p (1920×1080, H.264, 8 Mbps), 720p (1280×720, 5 Mbps), 480p (2.5 Mbps), 360p (1 Mbps),

(d) For EACH resolution: Encode video, Split into 10-sec segments (.ts for HLS or .m4s for DASH), Upload to S3: s3://videos-processed/{video_id}/{resolution}/segment_001.ts, ...,

(e) Generate manifest files: Master.m3u8 (points to all resolution playlists), 1080p/playlist.m3u8 (lists segment URLs for 1080p),

(f) Upload manifests to S3,

(4) Metadata Update: UPDATE video_metadata SET processing_status='COMPLETED', manifest_url='s3://.../master.m3u8', resolutions=['4K','1080p','720p','480p','360p'],

(5) Search Indexing: Kafka CDC event → Elasticsearch indexes video for search,

(6) CDN Distribution: CloudFront pulls segments from S3, caches at edge locations globally. Transcoding optimizations:

(a) Parallel processing: Each resolution transcoded on separate GPU instance, total time ~30 min for 2-hour movie,

(b) Spot instances for cost savings (transcoding is batch, interruptible),

(c) Two-pass encoding for better quality,

(d) Auto-scale workers based on SQS queue depth (10-100 instances). Storage: Original 4K (24GB) + Transcoded (4K+1080p+720p+480p+360p ≈ 16GB) = 40GB per 1-hour video.

Q
How do you minimize video buffering and ensure smooth playback?
A
Multi-layer buffering prevention strategy:

(1) Adaptive bitrate: Automatically reduce quality when bandwidth drops (8 Mbps → 1080p, 3 Mbps → 480p), prevents stalling during network fluctuations,

(2) Buffering strategy: Player maintains 20-40 sec buffer (downloads 3-5 segments ahead), if buffer <10 sec → aggressive switch to lower resolution + increase segment prefetch,

(3) CDN edge caching: Segments cached at 200+ CloudFront PoPs globally, 95% cache hit rate, <50ms latency vs 200ms from origin,

(4) Segment size: 10-sec segments (vs 30-sec) enable faster quality switching and seeking, smaller download chunks reduce impact of network interruptions,

(5) Preloading: On video start, download first 2-3 segments at lower quality for instant playback, then switch to optimal quality,

(6) Connection optimization: HTTP/2 multiplexing for parallel segment downloads, connection keep-alive reduces handshake overhead,

(7) Predictive prefetching: If user watching series, preload first 2 segments of next episode,

(8) Network condition monitoring: Player tracks: segment download time, throughput (Mbps), buffer level, packet loss → adjusts quality proactively,

(9) Fallback quality: If multiple segments fail to download at current quality, immediately drop 2 levels (1080p → 480p instead of gradual 1080p → 720p → 480p),

(10) CDN failover: If edge location errors (5xx), automatically retry from different PoP or origin shield,

(11) Client-side optimization: Hardware decoding (GPU) for H.264/H.265 reduces CPU load, video.js/hls.js optimized players with smart buffering logic. Quality metrics tracked: Initial buffering time (time to first frame, target <2 sec), Rebuffering ratio (time spent buffering / total watch time, target <0.5%), Bitrate switches (too frequent = annoying, target <5 switches per hour). Example scenario: User starts watching → Player requests 1080p → First 2 segments download fast (WiFi, buffer at 20 sec) → User moves, WiFi weakens → Segment 3 download slow (detected) → Player switches to 720p for segment 4 → Buffering continues uninterrupted → User never sees spinner.

Q
How do you design the CDN architecture for global video delivery?
A
Multi-tier CDN architecture for global scale:

(1) Origin: S3 buckets in multiple regions (us-east-1, eu-west-1, ap-south-1) with cross-region replication, stores transcoded video segments,

(2) Origin Shield: CloudFront feature, centralized caching layer between edge and origin, acts as 'shield' to collapse requests (100 edge requests → 1 shield request to origin), reduces origin load by 90%, improves cache hit rate,

(3) Edge Locations: 200+ CloudFront PoPs globally (NYC, London, Mumbai, Tokyo, etc.), cache segments with TTL=24 hours, serve 95% of requests without origin hit,

(4) Request flow: User in Mumbai requests segment → DNS routes to nearest edge (Mumbai PoP) → Edge checks cache (cache key: video_id/resolution/segment_number) → If HIT: Return cached segment (10-50ms) → If MISS: Request from Origin Shield (us-east-1) → Shield checks cache → If miss: Fetch from S3 → Shield caches + returns → Edge caches + returns (200ms first time, <50ms subsequent),

(5) Cache optimization:

(a) Popular content (trending movies): Pre-warmed to edges before release (push invalidation),

(b) Long-tail content: Cached on-demand (first request slower, subsequent fast),

(c) Purge strategy: Invalidate segments only when video updated (rare), otherwise rely on TTL,

(6) Geo-routing: S3 buckets per region (us-west-2, eu-west-1, ap-south-1), CloudFront fetches from nearest origin based on edge location, reduces latency by 60% (500ms → 200ms for origin fetches),

(7) Signed URLs: CloudFront signed URLs with expiry=4 hours prevent hotlinking and unauthorized access, signature validates user has active subscription,

(8) Compression: Gzip/Brotli for manifest files (.m3u8, .mpd) saves 70% bandwidth, not for video segments (already compressed),

(9) HTTP/2: Multiplexing allows parallel segment downloads over single connection, reduces handshake overhead,

(10) Monitoring: CloudWatch tracks: cache hit rate (target >95%), origin requests (target <5%), error rate (4xx, 5xx <0.1%), bandwidth usage. Cost calculation: 20M DAU × 2 hours × 5 Mbps / 8 = 20M × 2 × 5/8 GB = 25M GB/day = 750M GB/month → 750M GB × $0.085/GB = $63M/month in CDN bandwidth. Optimization: Cache hit rate 95% → only 5% hits origin → $63M × 0.05 = $3.15M origin bandwidth cost.

Q
How do you implement video search with filters (genre, actor, language)?
A
Elasticsearch-based video search with filters:

(1) Index mapping: PUT /videos { 'mappings': { 'properties': { 'video_id': {'type': 'keyword'}, 'title': {'type': 'text', 'analyzer': 'standard', 'fields': {'keyword': {'type': 'keyword'}}}, 'description': {'type': 'text'}, 'genre': {'type': 'keyword'}, 'actors': {'type': 'text', 'fields': {'keyword': {'type': 'keyword'}}}, 'director': {'type': 'text'}, 'language': {'type': 'keyword'}, 'content_rating': {'type': 'keyword'}, 'release_date': {'type': 'date'}, 'popularity_score': {'type': 'float'} } } },

(2) Indexing: Video metadata from PostgreSQL → Kafka CDC → Elasticsearch indexer, each video document indexed with all searchable fields,

(3) Search query: GET /v1/videos/search?q=Inception&genre=Sci-Fi&actor=Leonardo DiCaprio&language=English&sort=popularity → Backend builds ES query: POST /videos/_search { 'query': { 'bool': { 'must': [ { 'multi_match': { 'query': 'Inception', 'fields': ['title^3', 'description', 'actors', 'director'], 'type': 'best_fields' } } ], 'filter': [ { 'term': { 'genre': 'Sci-Fi' } }, { 'match': { 'actors': 'Leonardo DiCaprio' } }, { 'term': { 'language': 'English' } } ] } }, 'sort': [ { 'popularity_score': 'desc' } ], 'from': 0, 'size': 20 },

(4) Scoring:

(a) Text relevance: 'title^3' boosts title matches 3x over description,

(b) Popularity: popularity_score = log(view_count) + 0.5 × avg_rating + recency_boost, calculated offline daily via batch job,

(c) Personalization (advanced): Boost genres user previously watched, use ML model (collaborative filtering) to rerank results,

(5) Faceted search: Add aggregations: 'aggs': { 'genres': { 'terms': { 'field': 'genre', 'size': 20 } }, 'languages': { 'terms': { 'field': 'language' } }, 'rating_buckets': { 'histogram': { 'field': 'popularity_score', 'interval': 1 } } } → Returns counts: {Sci-Fi: 150, Action: 200, ...} for UI filters,

(6) Autocomplete: Separate index with edge_ngram tokenizer for type-ahead suggestions, queries update every keystroke with debouncing (300ms),

(7) Caching: Redis caches popular queries: Key = hash(query_text + filters + sort), Value = JSON result, TTL = 10 min, Cache hit rate 60-70%,

(8) Performance: ES cluster: 10 data nodes (5 primary shards, 1 replica each), query latency p95 <100ms for 10M videos,

(9) Index updates: Near real-time via Kafka, new videos searchable within 1-2 seconds of metadata creation. Example: User searches 'leonardo' → Autocomplete suggests 'Leonardo DiCaprio', 'The Revenant', 'Inception' → User selects 'Inception' → Full search returns Inception + similar movies → User filters by 'Sci-Fi' → Results filtered client-side or re-query with filter.

Q
How do you handle subscription management and payment processing?
A
Subscription lifecycle with payment integration:

(1) Subscription plans: Table subscription_plans {plan_id: 'basic', name: 'Basic', price: 9.99, currency: 'USD', max_resolution: '720p', max_screens: 1, billing_period: 'monthly'}, Plans: Basic ($9/mo, 720p, 1 screen), Standard ($13/mo, 1080p, 2 screens), Premium ($17/mo, 4K, 4 screens),

(2) User subscribes: POST /v1/subscriptions with {user_id, plan_id: 'premium', payment_method_id: 'pm_abc123' (from Stripe)},

(3) Payment flow:

(a) Subscription Service calls Stripe API: stripe.subscriptions.create({ customer: user.stripe_customer_id, items: [{price: plan.stripe_price_id}], payment_behavior: 'default_incomplete', expand: ['latest_invoice.payment_intent'] }),

(b) Returns client_secret for confirming payment on frontend,

(c) User confirms payment in browser (3D Secure if required),

(d) Stripe sends webhook POST /webhooks/stripe with {type: 'invoice.paid', subscription_id, payment_intent},

(4) Webhook handling:

(a) Validate signature (security),

(b) Idempotency check: SELECT * FROM subscriptions WHERE stripe_subscription_id={subscription_id}, if exists return 200 (already processed),

(c) BEGIN TRANSACTION; INSERT INTO subscriptions (subscription_id, user_id, plan_id, status='ACTIVE', start_date=now(), end_date=now()+30days, stripe_subscription_id, stripe_payment_intent_id); UPDATE users SET subscription_status='ACTIVE', subscription_id={subscription_id}; COMMIT;,

(d) Invalidate Redis cache: DEL user:{user_id}:subscription,

(e) Publish Kafka 'subscription.created' → Notification Service sends welcome email,

(5) Access control: On video playback request:

(a) GET /v1/videos/{video_id}/play → Validate subscription: SELECT status, end_date, plan_id FROM subscriptions WHERE user_id={user_id} AND status='ACTIVE',

(b) Check plan allows video quality: if requesting 4K but plan.max_resolution='1080p' → return 403 with upgrade prompt,

(c) Check concurrent streams: SELECT COUNT(*) FROM active_sessions WHERE user_id={user_id} → if count >= plan.max_screens → return 403 'Too many devices',

(d) Generate signed CDN URL with expiry,

(6) Auto-renewal:

(a) Stripe automatically charges on renewal date (30 days from start),

(b) If payment succeeds → webhook 'invoice.paid' → UPDATE subscriptions SET end_date=end_date+30days,

(c) If payment fails → webhook 'invoice.payment_failed' → Notification Service sends email, grace period 7 days before downgrade, retry payment 3 times,

(d) After grace period: UPDATE subscriptions SET status='EXPIRED' → user downgraded to free tier (if exists) or blocked,

(7) Cancellation: PUT /v1/subscriptions/{subscription_id}/cancel → stripe.subscriptions.update({subscription_id, cancel_at_period_end: true}) → User keeps access until end_date, then status='CANCELLED',

(8) Billing history: GET /v1/users/{user_id}/billing → fetch from Stripe API: stripe.invoices.list({customer: stripe_customer_id}) → display in user dashboard. Edge cases:

(1) Dunning: Failed payment → retry with exponential backoff, send notification,

(2) Refunds: if user cancels within 7 days, pro-rated refund via stripe.refunds.create(),

(3) Upgrades: Mid-cycle upgrade from Basic to Premium → calculate pro-rated charge for remaining days,

(4) Regional pricing: Different prices per country stored in subscription_plans_regional table.

Q
How do you track and store watch history for 200M users?
A
Scalable watch history with Cassandra + Redis:

(1) Real-time progress tracking: Client sends heartbeat every 10 seconds: POST /v1/videos/{video_id}/progress with {user_id, current_time_seconds: 1245, timestamp},

(2) Redis for hot data:

(a) Write to Redis: HSET watch_progress:{user_id}:{video_id} 'current_time' {current_time} 'last_updated' {timestamp} 'device_id' {device_id},

(b) TTL: EXPIRE watch_progress:{user_id}:{video_id} 604800 (7 days), auto-cleanup old sessions,

(c) Read on resume: GET /v1/videos/{video_id}/play → HGET watch_progress:{user_id}:{video_id} 'current_time' → return {resume_from: 1245}, client seeks to position,

(3) Cassandra for persistence:

(a) Background job (every 60s): Batch write from Redis to Cassandra,

(b) Table schema: CREATE TABLE watch_history (user_id uuid, video_id uuid, watched_at timestamp, current_time int, completion_percentage int, device_type text, PRIMARY KEY (user_id, watched_at)) WITH CLUSTERING ORDER BY (watched_at DESC), partition by user_id for fast user-specific queries,

(c) INSERT: INSERT INTO watch_history (user_id, video_id, watched_at, current_time, completion_percentage, device_type) VALUES ({user_id}, {video_id}, now(), {current_time}, {percentage}, {device_type}),

(4) Analytics pipeline:

(a) Kafka event stream: On every progress update, publish 'video.watched' event: {user_id, video_id, session_id, current_time, duration_watched, timestamp, geo_location, device_type},

(b) Stream processing: Apache Flink/Spark Streaming consumes events, calculates aggregations: total_watch_time, unique_viewers, completion_rate, drop-off_points,

(c) Results stored in analytics DB (BigQuery/Redshift) for dashboards,

(5) Recommendations:

(a) Collaborative filtering: Users who watched X also watched Y,

(b) Content-based: Similar genre, actors,

(c) ML model (TensorFlow) trained on: watch_history (implicit feedback: user watched = positive signal), explicit ratings if available, search queries,

(d) Inference: Batch job runs nightly, generates top 20 recommendations per user, stored in Redis: SET recommendations:{user_id} '[video_ids]' EX 86400,

(e) Real-time updates: As user watches, update recommendations incrementally,

(6) Scalability:

(a) Cassandra: Partitioned by user_id, 200M users × 100 entries avg × 500 bytes = 10 TB, replicated 3x = 30 TB,

(b) Redis: Only active sessions (10M concurrent users × 1 KB = 10 GB),

(c) Cassandra write throughput: 20M DAU × 1 update/10s = 2M writes/sec, Cassandra handles 1M writes/sec per node, 3 nodes sufficient with replication,

(7) Data retention: Cassandra TTL on rows: WITH default_time_to_live = 31536000 (1 year), old data auto-deleted. Example: User pauses at 20:45 → Client sends progress → Redis updated → Background job syncs to Cassandra → User opens app next day → Resume API queries Redis → Returns last_position=1245s → Player seeks to 20:45 → Seamless resume.

Q
How do you optimize video delivery cost at scale (CDN, storage, transcoding)?
A
Multi-layer cost optimization:

(1) CDN caching: 95% cache hit rate → only 5% requests hit origin, saves 95% of origin bandwidth cost, Cost: 20M DAU × 2h × 5Mbps / 8 = 25M GB/day → 750M GB/month, CDN $0.085/GB → $63M/month, Origin (5%) $0.023/GB → $63M × 0.05 × 0.023/0.085 = $0.86M/month, Total CDN: $63.86M/month → Optimization: Negotiate volume discounts (50% off at petabyte scale) → ~$32M/month,

(2) Storage tiering:

(a) Hot data (recent releases, popular content): S3 Standard ($0.023/GB) → 20% of catalog = 80 TB × $0.023 = $1,840/month,

(b) Warm data (1-year old): S3 Infrequent Access ($0.0125/GB) → 30% = 120 TB × $0.0125 = $1,500/month,

(c) Cold data (>2 years old, rarely watched): S3 Glacier ($0.004/GB) → 50% = 200 TB × $0.004 = $800/month, Total storage: $4,140/month vs $9,200 all-standard (55% savings),

(3) Transcoding optimization:

(a) Spot instances: Use EC2 spot for 70% of transcoding workers → 70% discount vs on-demand ($2.50/hr → $0.75/hr), Risk: Interruption → batch job idempotent, restarts from checkpoint,

(b) Auto-scaling: Scale workers 10-100 based on queue depth (SQS), average 30 instances × 24h × 30 days × $0.75 = $16,200/month,

(c) Smart resolution selection: Don't transcode 4K for all content (only blockbusters), save 30% transcoding cost,

(4) Compression:

(a) H.265/HEVC: 50% better compression vs H.264, reduces storage and bandwidth by 40%, 10k videos × 40GB → with HEVC 10k × 24GB = 240 TB vs 400 TB, savings: 160 TB × $0.023 = $3,680/month storage + proportional CDN savings,

(b) AV1 (future): 30% better than HEVC, but slower encoding (2x time), not yet widely supported,

(5) Lazy transcoding: Don't transcode all resolutions immediately, transcode on-demand when requested (e.g., only 1% watch 4K), saves 40% transcoding cost,

(6) Content pruning: Delete unpopular content after 5 years (watched <100 times), frees storage, saves $500/month,

(7) Regional optimization: Store content in S3 bucket closest to main audience region (US content in us-east-1), reduces cross-region transfer costs,

(8) Manifest file compression: Gzip .m3u8 files saves 70% → 10k videos × 10 KB × 0.7 = negligible but good practice,

(9) Reserved capacity: Reserve 50% baseline CDN bandwidth for 1-year term → 30% discount vs on-demand,

(10) Monitoring and alerting: Track cost per video, cost per user, shutdown zombie resources (unused transcoding workers, orphaned S3 objects). Total monthly cost (before optimizations): CDN $63M + Storage $9K + Transcoding $50K + Misc $100K ≈ $63.2M → After optimizations: CDN $32M + Storage $4K + Transcoding $16K + Misc $50K ≈ $32.1M (49% savings).

Q
How do you implement DRM (Digital Rights Management) to prevent piracy?
A
DRM implementation for content protection:

(1) DRM standards:

(a) Widevine: Google standard, used by Chrome, Android,

(b) FairPlay: Apple standard, used by Safari, iOS,

(c) PlayReady: Microsoft standard, used by Edge, Xbox,

(2) Encryption:

(a) Video segments encrypted during transcoding using AES-128 or AES-256,

(b) Each segment encrypted with unique encryption key,

(c) Encryption keys stored in License Server (AWS Elemental MediaPackage, BuyDRM, etc.),

(3) Key delivery:

(a) Player requests manifest → receives encrypted segment URLs + license_url,

(b) Player requests decryption key: GET {license_url} with user_token and device_id,

(c) License Server validates: User has active subscription, Device is registered (max 5 devices per user), DRM client installed (not emulator/rooted device),

(d) If valid: Returns decryption key encrypted with device's public key (only that device can decrypt),

(e) Player decrypts segments in memory, renders video to screen (encrypted buffer → decryption → display pipeline),

(4) Content protection:

(a) HDCP (High-bandwidth Digital Content Protection): Prevents screen recording via HDMI, enforced by hardware,

(b) Watermarking: Invisible forensic watermark embedded with user_id, if leaked can trace source,

(c) Screen capture blocking: DRM API blocks screen recording apps, screenshots show black screen,

(5) Offline downloads:

(a) Download encrypted segments to local storage (mobile app),

(b) License downloaded with expiry (e.g., 30 days),

(c) On playback: Validate license not expired, decrypt and play,

(d) On subscription end: License invalidated, downloaded content unplayable,

(6) Implementation:

(a) Transcoding: FFmpeg with DRM packaging: ffmpeg -i input.mp4 -c:v libx264 -encryption_scheme cenc -encryption_key {key} -encryption_kid {key_id} output.mp4,

(b) Manifest: HLS includes #EXT-X-KEY:METHOD=SAMPLE-AES,URI={license_server_url},KEYFORMAT='com.apple.streamingkeydelivery',

(c) Player: Use ExoPlayer (Android), AVPlayer (iOS), Shaka Player (web) with DRM plugin,

(7) Multi-DRM: Support all 3 standards for cross-platform: if Safari → FairPlay, if Chrome → Widevine, if Edge → PlayReady, use unified license server (BuyDRM, Irdeto) that handles all,

(8) Challenges:

(a) Performance: Decryption overhead ~5-10% CPU, use hardware-accelerated decryption (GPU),

(b) Compatibility: Older devices may not support, fallback to lower DRM level or no DRM,

(c) Cost: License server $0.01-0.05 per view, 20M daily views = $200K-$1M/month,

(9) Anti-piracy:

(a) Geofencing: Block VPNs, restrict content by region,

(b) Concurrent stream limits: Max 2-4 devices simultaneously,

(c) Token expiry: Signed URLs valid for 4 hours, forces re-authentication. Example: User clicks play → Player requests manifest → Manifest includes encrypted segment URLs + license_url → Player requests license from server with user_token → Server validates subscription + device → Returns decryption key (encrypted) → Player decrypts using device key → Segments decrypted in memory and rendered → User cannot save or share video file.

Q
What's your disaster recovery and fault tolerance strategy for a streaming platform?
A
Multi-region DR with automated failover:

(1) Architecture: Primary region us-east-1, Secondary us-west-2, Tertiary eu-west-1,

(2) Data replication:

(a) PostgreSQL: Primary in us-east-1, streaming replication to us-west-2 (warm standby, lag <5s) and eu-west-1 (read replica, lag <10s),

(b) S3: Cross-region replication (CRR) enabled, video segments replicated to all 3 regions automatically within minutes,

(c) Redis: Redis Sentinel for automatic failover, master-slave replication (lag <1s), AOF persistence for durability,

(d) Cassandra: Multi-DC deployment with replication_factor=3 across all regions, LOCAL_QUORUM for reads/writes,

(3) CDN resilience: CloudFront automatically routes to healthy origins, if us-east-1 S3 fails → CloudFront fetches from us-west-2 bucket transparently, no user impact,

(4) Failover procedure:

(a) Health checks: Route53 health checks on primary region every 30s (TCP, HTTP, latency),

(b) Trigger: If 3 consecutive checks fail (90s) → Route53 updates DNS to point to us-west-2,

(c) Database promotion: us-west-2 PostgreSQL promoted to primary (pg_ctl promote), takes ~2-3 min,

(d) Application servers: Auto-scaling groups in us-west-2 pre-warmed (min 10% capacity always running), scale up to 100% within 5 min,

(e) DNS propagation: 5-10 min for DNS TTL, progressive migration as clients refresh,

(5) RPO/RTO targets:

(a) RPO (Recovery Point Objective): <5 seconds data loss (streaming replication lag),

(b) RTO (Recovery Time Objective): <10 minutes service restoration,

(6) Service degradation:

(a) Read-only mode: If primary DB fails but replicas healthy → serve read-only, users can watch but not subscribe/update profiles,

(b) CDN-only mode: If all origins down → serve cached content only (95% of requests), new uploads fail,

(c) Graceful degradation: Disable non-critical features (recommendations, continue watching) to reduce load,

(7) Testing:

(a) Monthly DR drills: Simulate primary region failure, execute failover, verify RTO met,

(b) Chaos engineering: Randomly terminate instances in production (during low-traffic hours), verify auto-recovery,

(c) Game days: Simulate various failure scenarios (DB corruption, CDN outage, DDoS attack),

(8) Monitoring:

(a) Datadog/New Relic: Real-time metrics (latency, error rate, throughput),

(b) Alerts: PagerDuty for critical issues (DB lag >10s, API error rate >1%, CDN cache hit rate <90%),

(c) Dashboards: Grafana showing: concurrent viewers, video playback errors, buffering ratio, DB replication lag,

(9) Backup and restore:

(a) S3: Versioning enabled, accidental deletes recoverable,

(b) Database: Daily full backups + hourly incremental to S3 Glacier, retention 30 days,

(c) Point-in-time recovery: Can restore DB to any point within last 7 days,

(d) Backup restore testing: Quarterly restore from backup to staging environment, verify data integrity,

(10) DDoS protection:

(a) AWS Shield Advanced: Protects against L3/L4 DDoS,

(b) CloudFront rate limiting: Geo-blocking suspicious traffic, WAF rules block malicious patterns,

(c) Auto-scaling: Absorb traffic spikes up to 10x normal load. Example failure: Primary region (us-east-1) suffers power outage at 2:00 PM → Route53 health checks fail at 2:01:30 → DNS updated to us-west-2 at 2:02 → PostgreSQL promoted at 2:04 → Users experience brief buffering (current segment completes from cache, next segment from us-west-2) → Service fully restored at 2:10 PM → Data loss: <5s of watch progress for in-flight requests. Total cost: Multi-region setup adds 30-40% infrastructure cost, insurance against revenue loss during outages (1 hour outage = $500K lost revenue + reputation damage).

12. Key Numbers to Remember

Scale & Volume
Total Users — 200M registered users globally
Daily Active Users — 20M DAU streaming video
Total Videos — 10k videos (~1 hour avg duration each)
Total Storage — 400TB = 10k videos × 40GB (original + transcoded)
Daily Traffic — 180 PB/day = 20M users × 2 hours × 5 Mbps
Peak Concurrent — 2M concurrent viewers (10% of DAU, prime time 8-11 PM)
Video Bitrates & Storage (from image)
1080p — ~8 Mbps bitrate, ~200 MB/hr, 12 GB for 1-hour video
720p — ~5 Mbps bitrate, ~100 MB/hr, 6 GB for 1-hour video
4K — ~20 Mbps bitrate, ~400 MB/hr, 24 GB for 1-hour video
480p — ~2.5 Mbps bitrate, ~50 MB/hr, 3 GB for 1-hour video
360p — ~1 Mbps bitrate, ~20 MB/hr, 1.2 GB for 1-hour video
Performance & Latency
CDN Edge Latency — 10-50ms (cache hit), 200ms (cache miss to origin)
Initial Buffering — Target <2 seconds (time to first frame)
Segment Duration — 10 seconds (HLS/DASH standard)
Player Buffer — Maintain 20-40 seconds ahead (3-5 segments)
Transcoding Time — 30-60 min for 2-hour 4K movie (parallel GPU instances)
Search Latency — <100ms (Elasticsearch p95)
Streaming Protocols
HLS — .m3u8 manifest + .ts segments (Apple standard)
DASH — .mpd manifest + .m4s segments (MPEG standard)
Codec H.264 — Standard, widely supported, baseline compression
Codec H.265/HEVC — 50% better compression than H.264, 4K/HDR
Codec AV1 — 30% better than HEVC, future standard, slower encoding
Costs (Monthly)
CDN Bandwidth — $32M/month (750M GB × $0.085/GB with 50% volume discount)
Storage (S3) — $4K/month (tiered: Standard + IA + Glacier)
Transcoding — $16K/month (30 spot instances × $0.75/hr)
DRM License — $200K-$1M/month ($0.01-0.05 per view × 20M daily views)
Total Infrastructure — ~$32.5M/month (dominated by CDN bandwidth)
Business Metrics
Subscription Plans — Basic $9/mo (720p, 1 screen), Standard $13/mo (1080p, 2 screens), Premium $17/mo (4K, 4 screens)
Avg Watch Time — 2 hours per user per day
Cache Hit Rate — 95% (CDN edge locations)
Conversion Rate — 5-10% (free trial to paid subscription)
Key Interview Tips

⚠️
CRITICAL: Adaptive streaming requires keyframes at segment boundaries (0th second). Without this, quality switching causes stuttering. FFmpeg: -g 300 -keyint_min 300 for 10-sec segments at 30fps (300 frames).

⭐
Interviewers ALWAYS ask: 'How does adaptive bitrate streaming work?'. Answer: (1) Transcode to multiple resolutions (4K, 1080p, 720p, 480p), (2) Split into 10-sec segments, (3) Generate manifest with all options, (4) Player measures bandwidth, (5) Selects appropriate resolution dynamically, (6) Switches seamlessly on keyframes.

💡
CDN optimization: 95% cache hit rate is critical. Popular content (trending movies) pre-warmed to edges before release. Long-tail cached on-demand. Saves $30M/month in origin bandwidth costs.

⭐
Must mention: HLS vs DASH. HLS (.m3u8 + .ts) for Apple devices, DASH (.mpd + .m4s) for others. Production platforms serve BOTH. Segments aligned on keyframes enable seamless quality switching.

⚠️
NEVER transcode synchronously on upload. Use async pipeline: Upload → S3 → Kafka event → Workers → Transcoding → S3. 2-hour 4K movie takes 30-60 min to transcode. Queue-based with auto-scaling.

💡
Storage tiering: 20% hot (S3 Standard), 30% warm (S3 IA), 50% cold (S3 Glacier). Saves 55% storage cost vs all-standard. Automate with S3 Lifecycle policies based on view frequency.

⭐
Interviewers love: 'How to minimize buffering?'. Answer: (1) Adaptive bitrate (auto-reduce quality on network drop), (2) CDN edge caching (95% hit rate, <50ms), (3) 20-40 sec buffer, (4) Preload 3-5 segments ahead, (5) HTTP/2 multiplexing.

⚠️
NEVER store watch progress in PostgreSQL directly. Use Redis (1ms latency) for hot data, batch write to Cassandra every 60s. 20M users × 1 update/10s = 2M writes/sec, Redis handles this, PostgreSQL does not.

💡
DRM for piracy prevention: Widevine (Chrome/Android), FairPlay (Apple), PlayReady (Microsoft). Segments encrypted, license server validates subscription + device. Costs $0.01-0.05 per view but essential for premium content.

⭐
Must explain: Transcoding pipeline. Upload raw video → S3 → Kafka event → FFmpeg workers transcode to 4K, 1080p, 720p, 480p, 360p → Split into 10-sec segments → Generate HLS/DASH manifests → Upload to S3 → CDN distributes globally.