Online Learning Platform (Udemy / Coursera / EdTech)

"Instructor uploads video → S3 presigned URL → FFmpeg transcode (1080p/720p/480p/360p) → HLS 6-sec segments → CloudFront CDN (<2sec startup) → Student watches → Progress batched 30sec → Kafka consumer upserts (last_position_sec resume, max_position_sec completion) → Stripe payment with idempotency → Certificate on 100% completion"

1. Functional Requirements

Feature 1: User accounts with roles (student/instructor/admin), instructor verification required before teaching
Feature 2: Instructors create courses with videos, quizzes, assignments, category, difficulty, rating, price, resources
Feature 3: Students enroll in courses (free or paid), track progress through video completion and quiz scores
Feature 4: Assessment system with quizzes (auto-grade MCQ), assignments (manual grade essays), pass/fail status
Feature 5: Progress tracking and course completion status with resume functionality (last watched position)
Feature 6: Review and rating system for courses (1-5 stars, written reviews with helpful votes)
Feature 7: Instructor onboarding & verification (identity check, payout setup via Stripe Connect)
Feature 8: Support large files (videos up to 5GB per file, resources up to 100MB per file)
2. Non-Functional Requirements

Scale
Courses & Students — 100K+ courses and millions of enrolled students globally
Video Files — Billions of video segments stored in S3, petabytes of content
Traffic — Millions of video requests/day, thousands of enrollments/hour
Performance
Video Latency — <2sec startup time, adaptive bitrate streaming
API Response — <200ms for course listing, <100ms for enrollment check
Throughput — High bandwidth for 1080p streaming (5 Mbps per concurrent user)
Reliability
Availability — 99.9% uptime (CAP: Availability >> Consistency for video streaming)
Payment Consistency — Highly consistent for payments (ACID transactions, no double charging)
Durability — Video durability 11 9's via S3 cross-region replication
3. Core Entity

Entity 1: User/Instructor - userID, name, email, role (student/instructor/admin), instructor_profile {bio, expertise, verification_status, stripe_account_id}, status, metadata
Entity 2: Course - courseID, instructorID, title, description, category, difficulty (BEGINNER/INTERMEDIATE/ADVANCED from image), rating (DECIMAL), price, students_enrolled, published_status, thumbnail_url, created_at
Entity 3: Enrollment - enrollmentID, userID, courseID (FK), owner_instructor_id, enrolled_at (DATETIME/TIMESTAMP from image), completion_status (DECIMAL 5,2% from image), payment_id, metadata
Entity 4: Progress - user_id, course_id, lesson_id, video_id (if lesson is video from image), last_position_sec (resume from image), max_position_sec (how watched point from image), status (NOT_STARTED/IN_PROGRESS/COMPLETED), completed_at, metadata
Entity 5: Quiz - quiz_id, lesson_id, title, pass_score (70%), time_limit_sec, attempts_allowed, Questions: question_id (FK from image), question, type (MCQ_SINGLE/MULTI_SELECT/FILL/SELECT/TRUE_FALSE/TEXT from image), options (JSON from image), correct_answer, points, metadata
Entity 6: Payment - payment_id, user_id, course_id, amount (DECIMAL), status (PENDING/COMPLETED/FAILED/REFUNDED), stripe_payment_id, payment_method, created_at, metadata
Entity 7: Review - review_id, user_id, course_id, rating (1-5 INT), comment (TEXT), helpful_votes (INT), created_at
Entity 8: Course_stats (denormalized from image) - course_id, avg_rating, total_reviews, enrolled, completion_rate (%) - updated async via Kafka for fast queries
4. API Designing

Courses
GET /courses?search={}category={}price={}rating={}level={}sort= — Search/filter courses by category, price range, rating, difficulty level, sort by popularity/rating/newest
GET /courses/{courseId} — Get course details including curriculum, instructor info, reviews, enrollment count
POST /instructor/courses — Instructor creates new course with title, description, category, price, difficulty
POST /instructor/courses/{courseId}/publish — Publish course (makes visible to students after admin approval if first course)
Enrollments
POST /courses/{courseId}/enroll (free enroll) — Enroll in free course, creates enrollment record, grants access to content
GET /me/enrollments?courseId=... — Get user's enrolled courses with progress percentage, completion status, last accessed
Progress
POST /progress/events (batched events) — Track video watch events (batched every 30 sec), quiz completion, assignment submission
GET /me/courses/{courseId}/progress — Get user's progress for specific course (percentage, last watched position, completed lessons)
5. High Level Design

From image HLD: users/students → LB & API Gateway → Services (User Svc, Comment & Review Svc, Course Search Svc, Video Playback Svc, User Progress Svc, Enrollment Svc, Payment Svc) → Databases
From image HLD: instructor → LB & API Gateway → Catalog Svc, Media Uploader Svc → Course DB, S3 Blob storage
LB & API Gateway: Load balancing, authentication (JWT), authorization (role-based), routing, rate limiting (100 req/min per user)
User Svc → UserDB: User profiles, authentication, instructor verification status, Stripe account linkage
Comment & Review Svc → Course DB: Course reviews (1-5 stars), ratings aggregation, comments on lectures, helpful votes
Course Search Svc → Elastic Search: Full-text search on title/description/tags, filtering by category/price/rating/difficulty, autocomplete suggestions
Video Playback Svc → Blob (S3) → CDN: Streams video content via CloudFront, generates signed URLs (24-hour expiry), adaptive bitrate HLS streaming
User Progress Svc → Kafka → Progress DB: Tracks video watch time (last_position_sec, max_position_sec from image), quiz scores, assignment completion, batched events every 30 sec
Enrollment Svc → Course Enrollments DB: Manages course enrollments, access control checks, completion_status updates (DECIMAL 5,2% from image)
Payment Svc → Payment DB → Stripe: Handles course purchase payments, refunds (30-day window), instructor payouts (70/30 revenue split), idempotency via enrollment_request_id
Catalog Svc (instructor): Course creation, curriculum management (sections/lessons), content organization, publishing workflow
Media Uploader Svc → S3: Uploads videos via presigned URLs, triggers transcoding pipeline, generates thumbnails at 0s/5s/10s
From image LLD: CDN (CloudFront) → S3 for fast global video delivery (<2sec startup from image)
From image LLD: Kafka → user_tracking_consumer_svc → Progress DB for event-driven progress tracking with async updates
6. Deep Dive Design (Low Level

Step 1: Video Upload & Transcoding
Instructor uploads video: POST /instructor/courses/{courseId}/lessons/{lessonId}/video
Media Uploader generates presigned S3 URL: presignedURL = s3.generatePresignedUrl('putObject', {Bucket: 'course-videos-raw', Key: 'courses/C123/lessons/L456/original.mp4', Expires: 3600}), Response: {uploadURL: presignedURL, videoId: 'V789'}
Client uploads directly to S3 (bypasses server, faster): PUT {presignedURL} with video file, chunked upload for large files (5GB max), resumable if network fails
S3 event triggers Lambda: S3 → Lambda on object creation → Lambda publishes Kafka 'video.uploaded': {videoId, courseId, lessonId, s3Key, fileSize: 2GB}
Video Processing Worker (Kafka consumer): (1) Download original.mp4 from S3, (2) Transcode to 4 resolutions: FFmpeg: 1080p (1920×1080, 5 Mbps), 720p (1280×720, 2.5 Mbps), 480p (854×480, 1 Mbps), 360p (640×360, 500 Kbps), (3) HLS packaging: ffmpeg -i 1080p.mp4 -c copy -f hls -hls_time 6 -hls_segment_filename '1080p_segment_%03d.ts' 1080p.m3u8, generates master.m3u8 + variant playlists + .ts segments (6-sec each), (4) Thumbnail extraction: Extract frames at 0s, 5s, 10s (JPEG), (5) Upload all to S3: s3://course-videos-cdn/.../master.m3u8, (6) UPDATE lessons SET video_url='https://cdn.example.com/.../master.m3u8', thumbnail_url, processing_status='COMPLETED', variants={1080p,720p,480p,360p}, duration_sec=1200
S3 shows 'video file chunks in CloudMedia (thumbnail)', processing time ~10-15 min for 2GB video (async, instructor notified when complete)
Step 2: Video Streaming & CDN (<2sec startup from image)
Student watches video: GET /courses/C123/lessons/L456/video
Video Playback Service: (1) Check enrollment: SELECT COUNT(*) FROM enrollments WHERE user_id={user_id} AND course_id='C123', if 0 → return 403 'Enroll first', (2) Fetch video URL: SELECT video_url FROM lessons WHERE lesson_id='L456' → 'https://cdn.example.com/.../master.m3u8', (3) Generate CloudFront signed URL (expires 24 hours, prevents unauthorized sharing): signedURL = cloudfront.getSignedUrl({url: video_url, expires: now() + 86400}), (4) Response: {videoURL: signedURL, thumbnailURL, duration: 1200, variants: [1080p, 720p, 480p, 360p]}
Client-side playback: (1) Video player (Video.js, Plyr) loads HLS manifest: fetch(signedURL) → master.m3u8, (2) Adaptive bitrate: Player measures bandwidth (download speed of first segment), Fast connection (10 Mbps) → selects 1080p, Slow connection (1 Mbps) → selects 480p, switches mid-stream if bandwidth changes (seamless, no buffering), (3) Segment loading: Player fetches .ts segments sequentially: segment_0.ts (6 sec), segment_1.ts, ..., buffers 30 sec ahead for smooth playback
CDN optimization with CloudFront 200+ edge locations, user routed to nearest edge (<50ms latency), Cache TTL: segments 30 days (immutable), manifests 1 hour, Cache hit rate: 95%+ for popular courses
Startup time breakdown: (1) DNS lookup 50ms + TCP/TLS handshake 100ms + Manifest download 200ms + First segment download 500ms (6 sec ≈ 2 MB at 480p) = ~850ms total (well under <2sec target from image), (2) Optimization: Preload first segment while showing intro, HTTP/2 connection reuse
Step 3: Progress Tracking
Shows 'progress_level: course_id, video_id (if lesson is video), max_position_sec (how watched point), last_position_sec (resume), status, metadata'
Video watch events: (1) Client sends heartbeat every 10 seconds: {courseId: 'C123', lessonId: 'L456', videoId: 'V789', position: 120 (seconds), action: 'WATCHING', timestamp}, (2) Batching: Client batches 3 events (30 sec total) before sending: POST /progress/events with {events: [{position: 120}, {position: 130}, {position: 140}]}, reduces API calls 3× (from 1 event/10sec to 1 batch/30sec)
User Progress Service: (1) Receives batch, publishes to Kafka: FOR EACH event: kafka.send('video.progress', {userId, courseId, lessonId, videoId, position, timestamp}), (2) Response: 200 OK immediately (doesn't wait for DB write, async processing)
Progress Consumer (Kafka consumer 'user_tracking_consumer_svc'): (1) Consumes 'video.progress' events (10 consumer instances, 100 partitions by user_id hash), (2) Upsert progress: INSERT INTO progress (user_id, course_id, lesson_id, video_id, last_position_sec: 140, max_position_sec: 140, updated_at: now()) ON CONFLICT (user_id, course_id, lesson_id) DO UPDATE SET last_position_sec=140, max_position_sec=GREATEST(progress.max_position_sec, 140), updated_at=now(), Explanation: last_position_sec=140 (resume point, always latest), max_position_sec=GREATEST(existing, 140) (farthest watched, never decreases if user rewinds), (3) Completion check: if max_position_sec >= duration_sec * 0.95 (watched 95%+): UPDATE progress SET status='COMPLETED', completed_at=now(), trigger enrollment completion_status update
Resume functionality: (1) User reopens lesson: GET /me/courses/C123/lessons/L456/progress → {lastPosition: 140, duration: 1200, percentWatched: 11.7%, status: 'IN_PROGRESS'}, (2) Client seeks video to 140 seconds (resume where left off)
Kafka integration enables event-driven, async updates (doesn't block video playback), idempotent (safe to reprocess events), scales to millions of events/day
Step 4: Payment & Enrollment
Student enrolls in paid course: POST /courses/C123/enroll (price $49.99)
Payment flow: (1) Payment Service creates Stripe payment intent: POST https://api.stripe.com/v1/payment_intents with {amount: 4999 (cents), currency: 'usd', metadata: {courseId: 'C123', userId: 'U456', enrollmentRequestId: 'REQ123'}}, enrollmentRequestId: Client-generated UUID (idempotency key prevents double charging), Stripe response: {id: 'pi_abc123', client_secret: '...', status: 'requires_payment_method'}, (2) INSERT INTO payments (payment_id, user_id, course_id, amount: 49.99, status: 'PENDING', stripe_payment_id: 'pi_abc123', enrollment_request_id: 'REQ123', created_at: now()), (3) Response: {paymentIntentId, clientSecret}
Client-side: (1) Load Stripe.js, mount card element, (2) User enters card details, (3) stripe.confirmCardPayment(clientSecret, {payment_method: {card: cardElement}}) → Stripe processes (2-5 sec)
Payment Gateway shows 'stripe atomic db transaction' for consistency
Stripe webhook: (1) POST /webhooks/stripe with {type: 'payment_intent.succeeded', data: {object: {id: 'pi_abc123', status: 'succeeded'}}}, (2) Payment Service: Verify signature (prevents fake webhooks), UPDATE payments SET status='COMPLETED', completed_at=now() WHERE stripe_payment_id='pi_abc123', Publish Kafka: 'payment.completed' → {paymentId, userId, courseId, amount: 49.99}
Enrollment creation (Kafka consumer): (1) Consumes 'payment.completed', (2) Idempotency check (CRITICAL): SELECT COUNT(*) FROM enrollments WHERE user_id='U456' AND course_id='C123', if count > 0: Log('Already enrolled') and RETURN (prevents double enrollment on duplicate webhook), (3) INSERT INTO enrollments (enrollment_id, user_id, course_id, enrolled_at: now(), payment_id, completion_status: 0.0), (4) UPDATE courses SET students_enrolled = students_enrolled + 1, (5) Send email: 'Welcome to the course!'
Idempotency scenarios: (1) User clicks 'Enroll' twice: Same enrollmentRequestId → Stripe returns existing payment_intent (no duplicate charge), (2) Webhook sent twice: Consumer checks DB before enrollment (skips if exists), (3) Webhook lost: Polling backup queries Stripe API every 5 min for PENDING payments
Step 5: Quiz System
'quizzes: question_id (FK), question, type (MCQ_SINGLE/MULTI_SELECT/FILL/SELECT/TRUE_FALSE/TEXT), quiz_id, options (JSON), pass_score, metadata'
Quiz structure: (1) Quiz: quiz_id, lesson_id, title: 'Module 1 Assessment', pass_score: 70%, time_limit: 600 sec (10 min), attempts_allowed: 3, (2) Questions: question_id, quiz_id, question: 'What is CAP theorem?', type: 'MCQ_SINGLE', options: [{id: 'A', text: 'Consistency, Availability, Partition tolerance'}, {id: 'B', text: 'Concurrency, Atomicity, Performance'}], correct_answer: 'A', points: 10
Student takes quiz: (1) Start: POST /courses/C123/lessons/L456/quiz/start → INSERT INTO quiz_attempts (attempt_id, user_id, quiz_id, started_at, status: 'IN_PROGRESS'), (2) Fetch questions: GET .../quiz/questions → {questions: [...], timeLimit: 600, totalPoints: 100}, (3) Submit: POST .../quiz/submit with {answers: [{question_id: 'Q1', answer: 'A'}, {question_id: 'Q2', answer: ['A', 'C']}]}, (4) Auto-grading (MCQ): FOR EACH answer: if (answer === correct_answer) score += points, total_score = SUM(scores), percentage = (total_score / total_points) × 100, passed = percentage >= pass_score, (5) UPDATE quiz_attempts SET score=85, percentage=85.0, status='COMPLETED', passed=true, completed_at=now(), (6) If passed: UPDATE progress SET status='COMPLETED' for quiz lesson
Retake policy: (1) If failed: attempts_left = attempts_allowed - attempts_used, if attempts_left > 0 → allow retake, (2) Cooldown: Must wait 24 hours between attempts (prevent brute force), (3) If attempts exhausted → return 403 'No attempts remaining, contact instructor'
7. Database Schema Details

Courses (Course DB from image)
course_id — uuid PRIMARY KEY
instructor_id — uuid FK → Users
title — varchar(255)
description — text
category — varchar(100) (Business, IT, Design, Marketing, etc.)
difficulty — enum (BEGINNER, INTERMEDIATE, ADVANCED)
rating — decimal(3,2) (0.00-5.00, denormalized from reviews)
price — decimal(10,2) (0 for free courses)
students_enrolled — int DEFAULT 0 (denormalized counter, updated on enrollment)
published_status — enum (DRAFT, PENDING_APPROVAL, PUBLISHED, ARCHIVED)
Indexes — INDEX on (instructor_id, created_at), INDEX on (category, rating), INDEX on (published_status)
Enrollments (Course Enrollments DB from image)
enrollment_id — uuid PRIMARY KEY
user_id — uuid FK → Users
course_id — uuid FK → Courses')
owner_instructor_id — uuid (denormalized from courses.instructor_id)
enrolled_at — timestamptz%TIMESTAMP/DATETIME')
completion_status — decimal(5,2) (0.00-100.00%, percentage of course completed)
last_accessed_at — timestamptz (when user last opened course)
payment_id — uuid FK → Payments (nullable, null for free courses)
metadata — jsonb
Unique constraint — UNIQUE (user_id, course_id) - user can't enroll twice
Indexes — INDEX on (user_id, enrolled_at), INDEX on (course_id, enrolled_at)
Progress (Progress DB detailed schema)
Composite PK — (user_id, course_id, lesson_id)
user_id — uuid FK → Users
course_id — uuid FK → Courses
lesson_id — uuid FK → Lessons
video_id — uuid (if lesson is video)
last_position_sec — int (last watched position in seconds for resume)
max_position_sec — int (farthest watched position, for completion check)
status — enum (NOT_STARTED, IN_PROGRESS, COMPLETED)
completed_at — timestamptz (nullable, when lesson marked complete)
updated_at — timestamptz
metadata — jsonb (quiz scores, assignment submissions)
Sharding — Shard by user_id (user's progress on same shard for fast queries)
Quizzes (Quiz DB from image)
quiz_id — uuid PRIMARY KEY
lesson_id — uuid FK → Lessons
pass_score — decimal(5,2) (70.00 = 70% to pass)
time_limit_sec — int (nullable, time limit in seconds)
attempts_allowed — int DEFAULT 3
Questions — question_id uuid PK'), quiz_id uuid FK, question text, type enum (MCQ_SINGLE/MULTI_SELECT/FILL/SELECT/TRUE_FALSE/TEXT)
Payments (Payment DB from image)
payment_id — uuid PRIMARY KEY
user_id — uuid FK → Users
course_id — uuid FK → Courses
amount — decimal(10,2)
status — enum (PENDING, COMPLETED, FAILED, REFUNDED)
stripe_payment_id — varchar(255) (Stripe payment intent ID)
enrollment_request_id — varchar(255) (idempotency key, client-generated UUID)
created_at — timestamptz
metadata — jsonb
Course_stats (Denormalized from image)
course_id — uuid PRIMARY KEY FK → Courses
avg_rating — decimal(3,2)
total_reviews — int
enrolled — int (total enrollments)
completion_rate — decimal(5,2) (percentage who completed)
updated_at — timestamptz
Purpose — Materialized view updated async via Kafka for fast course listing queries
8. Scaling & Optimization

Technique 1: CDN video delivery - CloudFront 200+ edge locations, 95% cache hit rate, <2sec startup time (HLS adaptive streaming), reduces S3 egress cost 95%
Technique 2: Async video processing - S3 event → Lambda → Kafka → Worker pool (Spot instances 70% cheaper), transcoding 10-15 min (4 resolutions), instructor notified when complete
Technique 3: Progress event batching - Client batches 3 events every 30 sec (vs 1 event/10sec), reduces API calls 3×, Kafka handles millions events/day with 100 partitions
Technique 4: Database read replicas - 1 master (writes: enrollments, payments) + 5 replicas (reads: course listing, progress queries), read/write split scales to millions of queries
Technique 5: Denormalized stats - course_stats table (avg_rating, total_reviews, students_enrolled) updated async via Kafka, fast course listing queries avoid COUNT aggregations
Technique 6: Elasticsearch for search - Full-text search on title/description/tags, aggregations for category/price filters, autocomplete with ngram tokenizer, handles complex queries <100ms
Technique 7: Redis caching - Course details (1 hour TTL), enrollment check (24 hours), user preferences (24 hours), 90% cache hit rate reduces DB load 10×
Technique 8: Payment idempotency - enrollment_request_id (client-generated UUID), Stripe deduplicates, Kafka consumer checks DB before enrollment, prevents double enrollment on retry/duplicate webhook
Technique 9: HLS adaptive bitrate - 4 resolutions (1080p/720p/480p/360p), 6-sec segments, player switches mid-stream based on bandwidth, users on slow network get 360p (less bandwidth)
Technique 10: Database sharding - Progress table sharded by user_id (user's progress on same shard), Payments sharded by created_at (time-based for historical queries), scales to billions of records
Technique 11: S3 lifecycle policies - Raw videos archived to Glacier after 90 days ($0.004/GB vs $0.023/GB), transcoded videos stay in S3 (frequently accessed), saves 80% storage cost for old content
Technique 12: Kafka consumer auto-scaling - Auto-scale based on lag (if lag > 1000 messages → add instances), 100 partitions enables 100 parallel consumers, throughput scales linearly
9. Common Interview Questions

Q
How do you achieve <2 second video startup time with adaptive bitrate streaming?
A
Video streaming architecture with <2sec startup:

(1) Transcoding pipeline: FFmpeg transcodes to 4 resolutions (1080p 5Mbps, 720p 2.5Mbps, 480p 1Mbps, 360p 500Kbps), HLS packaging creates master.m3u8 + variant playlists + 6-sec .ts segments,

(2) CDN delivery: CloudFront 200+ edge locations, user routed to nearest (<50ms latency), cache hit rate 95% (segments cached 30 days, manifests 1 hour),

(3) Adaptive bitrate: Player loads master.m3u8, measures bandwidth via first segment download, selects resolution (20 Mbps → 1080p, 1 Mbps → 480p), switches mid-stream if bandwidth changes (seamless, no buffering),

(4) Startup optimization: DNS prefetch (saves 50ms), HTTP/2 connection reuse (saves 100ms per segment), preload first segment while showing intro, reduced segment size 4-sec for first segment (faster initial load), Breakdown: DNS 50ms + TLS 100ms + Manifest 200ms + First segment 500ms = 850ms total (under <2sec target). Result: Fast startup globally, adaptive to network conditions, scalable to millions of concurrent viewers.

Q
How do you track progress for millions of students watching videos and taking quizzes?
A
Event-driven progress tracking via Kafka:

(1) Client batching: Video player sends heartbeat every 10 sec with position, batches 3 events (30 sec) before POST /progress/events, reduces API calls 3× (1M students × 6 events/min = 6M → 2M API calls/min),

(2) Kafka publishing: Progress Service publishes each event to 'video.progress' topic (100 partitions by user_id hash), responds 200 OK immediately (async, doesn't block video),

(3) Consumer processing: 10 consumer instances consume from 100 partitions (10K events/sec per consumer = 100K events/sec total capacity), Upsert: INSERT ... ON CONFLICT DO UPDATE SET last_position_sec=140 (resume point), max_position_sec=GREATEST(existing, 140) (farthest watched, never decreases on rewind),

(4) Completion: if max_position_sec >= duration × 0.95 → UPDATE status='COMPLETED',

(5) Idempotency: Kafka consumer may reprocess events (restart, lag), upsert is idempotent (same event processed twice → same DB state),

(6) Scaling: Kafka partitions scale to millions events/day, DB sharded by user_id (user's progress on same shard), consumer auto-scales based on lag. Quiz progress: Submit → auto-grade MCQ → if passed UPDATE progress status='COMPLETED' for quiz lesson. Result: Handles millions of events/day, low latency (<1 sec DB write), resume functionality works reliably, idempotent (safe to retry).

Q
How do you prevent double enrollment when payment succeeds but webhook is duplicated or lost?
A
Payment idempotency with multiple safeguards:

(1) Client-side idempotency: Client generates enrollmentRequestId (UUID), includes in Stripe payment intent metadata, if user clicks 'Enroll' twice → same ID → Stripe returns existing payment_intent (no duplicate charge),

(2) Webhook deduplication: Stripe sends 'payment_intent.succeeded' webhook, Payment Service: Verifies signature (prevents fake webhooks), Updates DB: payment status='COMPLETED', Publishes Kafka 'payment.completed', If webhook sent twice (network retry): Both events reach Kafka (duplicate),

(3) Enrollment consumer idempotency: Consumes 'payment.completed', Checks DB: SELECT COUNT(*) WHERE user_id AND course_id, If count > 0 → already enrolled → SKIP (no duplicate enrollment), If count = 0 → INSERT enrollment (first time), UNIQUE constraint on (user_id, course_id) prevents race conditions,

(4) Webhook lost scenario: Payment succeeds (Stripe status='succeeded') but webhook delayed/lost, Polling backup: Payment Service polls Stripe API every 5 min for PENDING payments: GET /v1/payment_intents/{id}, If status='succeeded' but local='PENDING' → manually update DB + publish Kafka (same flow as webhook), Catches stuck payments within 5 min,

(5) Retry safety: All paths converge: DB check prevents duplicate enrollment, Stripe idempotency prevents duplicate charge, Kafka consumer handles out-of-order/duplicate events. Result: Exactly-once enrollment even with webhook failures/duplicates, payment consistency maintained, no double charging.

Key Interview Tips

⚠️
CRITICAL: Video <2sec startup requires HLS adaptive bitrate + CDN. MUST transcode to 4 resolutions (1080p/720p/480p/360p), 6-sec segments, CloudFront 200+ edges. Without CDN = 200-500ms S3 latency globally (fails requirement).

⭐
Progress tracking: Client batches 3 events/30sec → Kafka 'video.progress' (100 partitions) → Consumer upserts (last_position_sec for resume, max_position_sec for completion check at 95%). Handles millions events/day, idempotent, async (doesn't block video playback).

💡
Two position fields critical - last_position_sec (resume playback here) vs max_position_sec (farthest watched, for completion). User rewinds → last decreases but max stays (prevents marking incomplete on rewind).

⭐
Payment idempotency prevents double enrollment: (1) Client enrollment_request_id, (2) Stripe deduplicates payment_intents, (3) Kafka consumer checks DB (if enrolled → skip), (4) UNIQUE constraint (user_id, course_id), (5) Polling backup if webhook lost. All paths converge to exactly-once enrollment.

⚠️
NEVER sync transcode during upload. 2GB video = 10-15 min processing (FFmpeg 4 resolutions + HLS packaging + thumbnails). MUST async: S3 event → Lambda → Kafka 'video.uploaded' → Worker pool (Spot instances 70% cheaper). Instructor gets immediate upload confirmation, notified when complete.

💡
Kafka integration critical for scale. Shows 'user_tracking_consumer_svc' consuming events, updating Progress DB async. Event-driven architecture decouples video playback from progress writes, enables horizontal scaling (add more consumers as needed).

⭐
HLS adaptive bitrate: master.m3u8 lists 4 variant playlists, player measures bandwidth via first segment, selects resolution (fast → 1080p, slow → 360p), switches mid-stream seamlessly. Users on slow network get lower quality (less bandwidth) instead of buffering. CDN caches segments 30 days (95% hit rate).

system-design
edtech
udemy
coursera
online-learning
video-streaming
hls-adaptive-bitrate
