# Online Learning Platform — Interview Guide (Udemy / Coursera / EdTech)

> One-liner to anchor: _"Instructor uploads video → S3 presigned URL → FFmpeg transcode (1080p/720p/480p/360p) → HLS 6-sec segments → CloudFront CDN (<2sec startup) → Student watches → Progress batched 30sec → Kafka consumer upserts (last_position_sec resume, max_position_sec completion) → Stripe payment with idempotency → Certificate on 100% completion"_

---

## 1. Functional Requirements

| Actor | Feature |
|---|---|
| Student | Browse, search, filter courses (category, difficulty, rating, price) |
| Student | Enroll in free or paid courses |
| Student | Track video progress with resume (last watched position) |
| Student | Take quizzes (MCQ auto-grade) and submit assignments (manual grade) |
| Student | Review & rate courses (1-5 stars, helpful votes) |
| Instructor | Onboarding with identity verification (Uidai / KYC) + Stripe Connect payout setup |
| Instructor | Create courses: videos, quizzes, assignments, resources (up to 5GB video, 100MB file) |
| Instructor | Publish course (admin approval required for first course) |
| System | Certificate issued on 100% completion |
| System | 70/30 revenue split (instructor / platform) |

---

## 2. Non-Functional Requirements

| Property | Requirement |
|---|---|
| Scale | 100K+ courses, millions of enrolled students globally |
| Video files | Billions of HLS segments in S3, petabytes of content |
| Traffic | Millions of video requests/day, thousands of enrollments/hour |
| Video startup | **< 2 sec** (adaptive bitrate HLS + CloudFront) |
| API latency | < 200ms course listing, < 100ms enrollment check |
| Availability | 99.9% uptime — **Availability >> Consistency** for video streaming |
| Payment | Highly consistent (ACID, no double charging) |
| Durability | 11 nines for video (S3 cross-region replication) |
| CAP | AP for streaming; CP for payments & enrollment |

---

## 3. Core Entities

```
User/Instructor
  userId, name, email/phone, password(encrypted), role, status
  instructor_profile { name, verification_status, avg_rating,
                       rating_count, students_count, course_count,
                       promo_video_asset_id, stripe_account_id }

Course
  course_id (PK), owner_instructor_id, title, description,
  category_id, level (BEGINNER/INTERMEDIATE/ADVANCED),
  thumbnail_url, status (DRAFT/IN_REVIEW/PUBLISHED/REJECTED/ARCHIVED)

course_pricing
  course_id (PK/FK), price_amount, currency

course_stats (denormalized — updated async via Kafka)
  course_id, avg_rating, total_reviews, enrolled, completion_rate

Enrollment
  enrollment_id, user_id, course_id, owner_instructor_id,
  enrolled_at (DATETIME), completion_status DECIMAL(5,2),
  payment_id, metadata
  UNIQUE(user_id, course_id)

Progress (MySQL)
  user_id, course_id, video_id (if lesson is video),
  duration_sec, max_position_sec (farthest watched — for completion),
  last_position_sec (resume point), completed (bool), metadata
  PK: (user_id, course_id, lesson_id)  — sharded by user_id

Access
  access_id (PK), user_id, course_id,
  scope_type (LIFETIME/SUBSCRIPTION),
  status (ACTIVE/REVOKED/EXPIRED), purchase_date

Orders
  order_id (PK), user_id, currency, amount_total, status, metadata

Payment
  payment_id, user_id, course_id, amount DECIMAL,
  status (PENDING/COMPLETED/FAILED/REFUNDED),
  stripe_payment_id, enrollment_request_id (idempotency key)

Quizzes
  quiz_id, course_id, lesson_id, title, rating_count, pass_score

Questions
  question_id (PK), quiz_id,
  type (MCQ_SINGLE/MULTI_SELECT/FILL/SELECT/TRUE_FALSE/TEXT),
  points, status, metadata

Review
  review_id, user_id, course_id, rating (1-5), comment, helpful_votes
```

---

## 4. API Design

### Courses
```
GET  /courses?search=&category=&price=&rating=&level=&sort=
GET  /courses/{courseId}
POST /instructor/courses
POST /instructor/courses/{courseId}/publish
```

### Enrollments
```
POST /courses/{courseId}/enroll          — free enroll
GET  /me/enrollments?courseId=...        — enrolled courses + progress %
```

### Progress
```
POST /progress/events                    — batched watch events (every 30 sec)
GET  /me/courses/{courseId}/progress     — last position, % watched, status
```

### Quiz
```
POST /courses/{courseId}/lessons/{lessonId}/quiz/start
GET  /courses/{courseId}/lessons/{lessonId}/quiz/questions
POST /courses/{courseId}/lessons/{lessonId}/quiz/submit
```

---

## 5. High Level Design (from diagram)

```
                         ┌──────────┐
                         │  UserDB  │
                         └────┬─────┘
                              │ User Svc
                         ┌────▼──────────────────────────────────┐
                         │  Comment & Review Svc  →  Course DB   │
users/students           │  Course Search Svc     →  ElasticSearch│
    │                    │  Video Playback Svc    →  Blob (S3)    │
    ▼                    │                           + CDN        │
[LB & API Gateway] ──►  │  User Progress Svc     →  Progress DB  │
                         │  Enrollment Svc        →  Course       │
                         │                           Enrollment DB│
                         │  Payment Svc  ──────►  Payment DB      │
                         │               ──────►  Payment Gateway │
                         │  Assignment Svc                        │
                         └───────────────────────────────────────┘

                                        ┌────────────────────────┐
                                        │  Catalog Svc → Course DB│
instructor                              │  Media Uploader Svc → S3│
    │                                   │  Course Moderator Svc   │
    ▼                                   │  Permission Sync Svc    │
[LB & API Gateway] ──────────────────►  │                        │
                                        └────────────────────────┘

admin/moderator ──► [LB & API Gateway] ──► Course Moderator Svc
```

**S3 stores:**
- Videos (chunks in ordered format)
- Thumbnails
- Attachments

**Aggregator CDC pipeline** syncs Course DB changes → Elasticsearch for search.

**Kafka** drives:
- `user_tracking_consumer_svc` → Progress DB (async progress writes)
- `payment.completed` → Enrollment creation
- `video.uploaded` → Transcoding worker

**Notification Svc** consumes Kafka events for email/push notifications.

**Permission Sync Svc** — listens to Kafka events (payment.completed, refund.issued, subscription.expired) and keeps the `Access` table consistent:
- `payment.completed` → INSERT access (scope_type=LIFETIME, status=ACTIVE)
- `refund.issued` (within 30-day window) → UPDATE access SET status=REVOKED
- `subscription.expired` → UPDATE access SET status=EXPIRED
- Video Playback Svc checks `Access` table (not just Enrollments) before serving video — separates "enrolled" from "currently has access"

**Rate limiting** at API Gateway — 100 req/min per user (token bucket, keyed by userId from JWT). Protects against:
- Quiz brute-force (guess answers rapidly)
- Progress event flooding
- Scraping course catalog

---

## 6. Deep Dive: Video Upload & Transcoding

```
Instructor
  POST /instructor/courses/{courseId}/lessons/{lessonId}/video
      │
      ▼
Media Uploader Svc
  s3.generatePresignedUrl('putObject', {
    Bucket: 'course-videos-raw',
    Key: 'courses/C123/lessons/L456/original.mp4',
    Expires: 3600
  })
  Response: { uploadURL, videoId: 'V789' }
      │
      ▼  (client uploads directly to S3 — bypasses server)
  S3 PUT {presignedURL}   ← chunked, resumable, up to 5GB
      │
      ▼  S3 event triggers Lambda
  Lambda publishes Kafka 'video.uploaded':
    { videoId, courseId, lessonId, s3Key, fileSize }
      │
      ▼  Video Processing Worker (Kafka consumer — Spot instances)
  1. Download original.mp4 from S3
  2. FFmpeg transcode to 4 resolutions:
       1080p  1920×1080  5 Mbps
        720p  1280×720   2.5 Mbps
        480p   854×480   1 Mbps
        360p   640×360   500 Kbps
  3. HLS packaging:
       ffmpeg -i 1080p.mp4 -c copy -f hls -hls_time 6 \
         -hls_segment_filename '1080p_segment_%03d.ts' 1080p.m3u8
       → master.m3u8 + variant playlists + .ts segments (6 sec each)
  4. Thumbnail extraction: frames at 0s, 5s, 10s (JPEG)
  5. Upload all to S3: s3://course-videos-cdn/.../master.m3u8
  6. UPDATE lessons SET video_url='https://cdn.../master.m3u8',
       processing_status='COMPLETED', duration_sec=1200
      │
      ▼
  Notification Svc → email instructor "Video ready"
```

**Why async?** 2 GB video = 10–15 min processing. NEVER sync transcode during upload.

---

## 7. Deep Dive: Video Streaming (< 2 sec startup)

```
Student: GET /courses/C123/lessons/L456/video
    │
    ▼
Video Playback Svc
  1. Enrollment check:
       SELECT COUNT(*) FROM enrollments
       WHERE user_id=? AND course_id='C123'
       → 0 → 403 'Enroll first'
  2. Fetch video URL from lessons table
  3. Generate CloudFront signed URL (expires 24h, prevents sharing):
       cloudfront.getSignedUrl({ url: videoUrl, expires: now()+86400 })
  4. Response: { videoURL: signedURL, thumbnailURL, duration, variants }
    │
    ▼
Client (Video.js / Plyr)
  1. Loads HLS manifest: fetch(signedURL) → master.m3u8
  2. Adaptive bitrate: measures bandwidth via first segment download
       ≥10 Mbps → 1080p
       ~2.5 Mbps → 720p
       ~1 Mbps → 480p
       <1 Mbps → 360p
     Switches mid-stream seamlessly if bandwidth changes
  3. Fetches .ts segments sequentially (buffers 30 sec ahead)
```

**Startup time breakdown:**
```
DNS lookup            50 ms
TCP/TLS handshake    100 ms
Manifest download    200 ms
First segment (6s)   500 ms  (≈2 MB at 480p from edge)
─────────────────────────────
Total                850 ms  ✓ (well under 2 sec)
```

**CDN optimization:**
- CloudFront 200+ edge locations — user routed to nearest (<50ms)
- Segment cache TTL: 30 days (immutable content)
- Manifest cache TTL: 1 hour
- Cache hit rate: 95%+ for popular courses

---

## 8. Deep Dive: Progress Tracking

```
Video player (client)
  Heartbeat every 10 sec: { courseId, lessonId, videoId, position: 120, action:'WATCHING' }
  Batches 3 events (30 sec) → POST /progress/events
  → Reduces API calls 3× (1M students × 6 events/min = 6M → 2M calls/min)
      │
      ▼
User Progress Svc
  Publishes each event → Kafka 'video.progress' (100 partitions, key=user_id)
  Returns 200 OK immediately — async, doesn't block video
      │
      ▼
user_tracking_consumer_svc (10 instances, 100 partitions)
  Upsert:
    INSERT INTO progress (user_id, course_id, lesson_id, video_id,
      last_position_sec=140, max_position_sec=140, updated_at=now())
    ON CONFLICT (user_id, course_id, lesson_id) DO UPDATE SET
      last_position_sec = 140,                              ← always latest (resume)
      max_position_sec  = GREATEST(existing, 140),          ← never decreases on rewind
      updated_at        = now()

  Completion check:
    IF max_position_sec >= duration_sec × 0.95 (95%)
      → UPDATE progress SET status='COMPLETED', completed_at=now()
      → UPDATE enrollments SET completion_status = (completed_lessons / total) × 100
```

**Two fields explained:**
- `last_position_sec` — where to resume (always the latest sent position)
- `max_position_sec` — farthest ever watched (for completion; never decreases on rewind)

**Resume:**
```
GET /me/courses/C123/lessons/L456/progress
→ { lastPosition: 140, duration: 1200, percentWatched: 11.7%, status: 'IN_PROGRESS' }
Client seeks video to 140s automatically
```

---

## 9. Deep Dive: Payment & Enrollment

```
POST /courses/C123/enroll  ($49.99)
    │
    ▼
Payment Svc
  1. Create Stripe PaymentIntent:
       POST /v1/payment_intents {
         amount: 4999,  currency: 'usd',
         metadata: { courseId, userId, enrollmentRequestId: 'REQ123' }  ← client UUID
       }
       → { id: 'pi_abc123', client_secret, status: 'requires_payment_method' }
  2. INSERT payments (status='PENDING', stripe_payment_id='pi_abc123',
                       enrollment_request_id='REQ123')
  3. Return { paymentIntentId, clientSecret } to client
    │
    ▼
Client
  stripe.confirmCardPayment(clientSecret, { payment_method: { card: cardElement } })
  → Stripe processes (2-5 sec) — single atomic DB transaction
    │
    ▼
Stripe Webhook → POST /webhooks/stripe
  { type: 'payment_intent.succeeded', data.object.id: 'pi_abc123' }
  1. Verify signature (prevents fake webhooks)
  2. UPDATE payments SET status='COMPLETED'
  3. Publish Kafka 'payment.completed' → { paymentId, userId, courseId, amount }
    │
    ▼
Enrollment Consumer (Kafka)
  1. Idempotency check:
       SELECT COUNT(*) FROM enrollments WHERE user_id=? AND course_id=?
       → count > 0 → SKIP (duplicate webhook, already enrolled)
       → count = 0 → proceed
  2. INSERT enrollments (completion_status=0.0)
  3. UPDATE courses SET students_enrolled += 1
  4. Send welcome email
```

**Idempotency safeguards (5 layers):**

| Layer | Mechanism |
|---|---|
| 1. Client double-click | Same `enrollmentRequestId` → Stripe returns existing PaymentIntent (no 2nd charge) |
| 2. Webhook duplicate | Kafka consumer checks DB before INSERT |
| 3. Race condition | `UNIQUE(user_id, course_id)` constraint |
| 4. Webhook lost | Polling backup — queries Stripe every 5 min for PENDING payments |
| 5. Out-of-order events | All paths converge to same idempotent outcome |

---

## 10. Deep Dive: Quiz System

```
Quiz structure:
  quiz_id, lesson_id, title, pass_score: 70%, time_limit: 600s, attempts_allowed: 3

Questions:
  question_id, quiz_id, question text,
  type: MCQ_SINGLE / MULTI_SELECT / FILL / SELECT / TRUE_FALSE / TEXT,
  options: JSON [{id:'A', text:'...'}, ...],
  correct_answer: 'A', points: 10

Flow:
  1. POST .../quiz/start     → INSERT quiz_attempts (status='IN_PROGRESS')
  2. GET  .../quiz/questions → { questions, timeLimit: 600, totalPoints: 100 }
  3. POST .../quiz/submit    → { answers: [{question_id:'Q1', answer:'A'}, ...] }
  4. Auto-grade MCQ:
       FOR EACH answer: IF answer == correct_answer THEN score += points
       percentage = (score / total_points) × 100
       passed = percentage >= 70
  5. UPDATE quiz_attempts SET score, percentage, status='COMPLETED', passed, completed_at
  6. IF passed → UPDATE progress SET status='COMPLETED' for quiz lesson

Retake policy:
  IF failed AND attempts_left > 0 → allow retake (cooldown: 24h between attempts)
  IF attempts exhausted → 403 'No attempts remaining, contact instructor'
```

---

## 11. Deep Dive: Certificate Generation

```
Trigger: enrollment.completion_status reaches 100%

How completion_status hits 100%:
  user_tracking_consumer_svc detects max_position_sec >= duration × 0.95 per lesson
  → marks lesson progress status='COMPLETED'
  → recomputes:
      completion_status = (completed_lessons / total_lessons) × 100
      UPDATE enrollments SET completion_status = X.XX WHERE enrollment_id=?
  → IF completion_status = 100.00:
      Publish Kafka 'course.completed': { userId, courseId, enrollmentId, completedAt }

Certificate Consumer (Kafka):
  1. Verify: SELECT completion_status FROM enrollments = 100.00 (guard against duplicates)
  2. Generate certificate:
       certificate_id = UUID
       template = fetch course certificate template (S3)
       fill: student name, course title, instructor name, completion date
       render → PDF/PNG → upload to S3: s3://certificates/{userId}/{courseId}.pdf
  3. INSERT certificates (certificate_id, user_id, course_id, issued_at, s3_url)
  4. Notification Svc → email student with certificate download link (signed S3 URL)
  5. UPDATE enrollments SET certificate_url = signedS3Url

Idempotency:
  SELECT COUNT(*) FROM certificates WHERE user_id=? AND course_id=?
  → count > 0 → SKIP (don't re-issue on Kafka retry)
```

---

## 12. Database Schema Highlights

### Indexes that matter
```sql
-- Course listing (category browse, sorted by rating)
INDEX ON courses(category, rating)
INDEX ON courses(instructor_id, created_at)
INDEX ON courses(published_status)

-- Enrollment queries
UNIQUE INDEX ON enrollments(user_id, course_id)
INDEX ON enrollments(user_id, enrolled_at)

-- Progress (sharded by user_id — user's data on same shard)
PRIMARY KEY (user_id, course_id, lesson_id)
```

### Denormalized for read speed
```
course_stats  — avg_rating, total_reviews, enrolled, completion_rate
               updated async via Kafka (Aggregator CDC pipeline → writes back)
               avoids COUNT aggregations on hot course listing queries

courses.students_enrolled  — counter, incremented on enrollment Kafka event
courses.rating             — DECIMAL(3,2), updated from reviews async
```

### Sharding strategy
| Table | Shard key | Reason |
|---|---|---|
| Progress | `user_id` | User's all progress on one shard (range queries) |
| Payments | `created_at` | Time-based for historical queries |

---

## 13. Scaling Techniques (with numbers)

| Technique | What | Numbers |
|---|---|---|
| CDN | CloudFront 200+ edges | 95% cache hit, <50ms latency, <2s startup |
| Async transcode | S3 → Lambda → Kafka → Spot workers | 70% cheaper (Spot), 10-15 min async |
| Progress batching | Client batches 3 events/30s | 3× fewer API calls, 2M calls/min at 1M students |
| Read replicas | 1 master + 5 replicas | Read/write split, scales to millions of queries |
| Kafka partitioning | 100 partitions by user_id | 100K events/sec (10K/consumer × 10 consumers) |
| Elasticsearch | CDC pipeline from Course DB | Full-text + filters < 100ms |
| Redis cache | Course details 1h TTL, enrollment check 24h | 90% hit rate, 10× DB load reduction |
| HLS adaptive | 4 resolutions, 6-sec segments | Auto-switches mid-stream, no buffering on slow network |
| S3 lifecycle | Raw → Glacier after 90 days | 80% storage cost savings ($0.004 vs $0.023/GB) |
| Kafka consumer scaling | Auto-scale on lag > 1000 messages | Linear throughput scale |

---

## 14. Common Interview Questions

### Q1: How do you achieve < 2 second video startup?
**Answer outline:**
1. Transcoding pipeline: FFmpeg → 4 resolutions → HLS 6-sec segments → master.m3u8
2. CDN: CloudFront 200+ edges, user → nearest edge (<50ms), 95% cache hit
3. Adaptive bitrate: player measures bandwidth via first segment, selects resolution, switches seamlessly
4. Math: DNS 50ms + TLS 100ms + manifest 200ms + first segment 500ms = **850ms** ✓

### Q2: How do you track progress for millions of concurrent students?
**Answer outline:**
1. Client batches 3 heartbeats/30s → fewer API calls
2. Kafka 'video.progress' (100 partitions by user_id) → 200 OK immediately (async)
3. Consumer upserts: `last_position_sec` (resume) vs `GREATEST(max_position_sec, new)` (completion, never decreases on rewind)
4. Completion at 95% watched (`max >= duration * 0.95`)
5. Idempotent upsert — safe to reprocess on Kafka restart

### Q3: How do you prevent double enrollment / double charging?
**Answer outline (5 layers):**
1. `enrollmentRequestId` (client UUID) → Stripe deduplicates PaymentIntent
2. Webhook signature verification → prevents fake events
3. Kafka consumer DB check before INSERT → skip if already enrolled
4. `UNIQUE(user_id, course_id)` → DB-level safety net
5. Polling backup → catches webhook lost scenarios (5 min max delay)

### Q4: Why two position fields in Progress table?
- `last_position_sec`: where user left off — **always the latest value** → resume here
- `max_position_sec`: farthest ever watched — **never decreases** → completion check
- If user rewinds to 0s and closes: `last=0`, `max=800` → correctly resumes at 0 but counts as watched

### Q5: Why not sync transcode on upload?
- 2 GB video = 10-15 min (4 resolutions + HLS + thumbnails via FFmpeg)
- Holding HTTP connection 10+ min = timeouts, wasted resources, terrible UX
- Async: instructor gets immediate upload confirmation, email when processing completes
- Spot instances = 70% cost reduction for batch workloads

### Q6: How does instructor verification work?
- Uidai (India) / KYC identity check on instructor onboarding
- `verification_status` field in instructor_profile
- Admin/moderator approves first course publish (prevents spam)
- Stripe Connect payout setup: `stripe_account_id` stored on instructor profile
- 70/30 revenue split automated via Stripe Connect transfers

### Q7: How does search scale?
- Aggregator CDC pipeline listens to Course DB changes → syncs to Elasticsearch
- Elasticsearch handles: full-text on title/description/tags, filter by category/price/rating/difficulty, autocomplete (ngram tokenizer), complex aggregations < 100ms
- Redis caches popular search results (1h TTL)

---

## 15. Critical Gotchas (Don't Forget in Interview)

| # | Gotcha |
|---|---|
| 1 | **HLS + CDN is mandatory** for <2sec. Raw S3 = 200-500ms latency globally = fails |
| 2 | **NEVER sync transcode** during upload — always S3 → Lambda → Kafka → Worker |
| 3 | **Two position fields** — `last` for resume, `max` for completion (rewind ≠ unwatching) |
| 4 | **Enrollment idempotency has 5 layers** — mention all to show rigor |
| 5 | **course_stats is denormalized** — no COUNT(*) on enrollment queries in hot path |
| 6 | **Progress sharded by user_id** — keeps one user's data co-located |
| 7 | **CAP tradeoff is explicit** — AP for video, CP for payments |
| 8 | **Kafka partitioned by user_id** — ordering guaranteed per user, parallel across users |
| 9 | **enrollment_request_id is client-generated** — server never generates idempotency keys |
| 10 | **Access table is separate from Enrollments** — handles subscription vs one-time purchase scope |
