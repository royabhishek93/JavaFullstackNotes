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

> **WHY ENROLLMENT AND CONTENT ACCESS ARE STORED SEPARATELY? (Beginner Explanation)**
> Enrollment = joining a gym. Access = the keycard that lets you through the door today. They look the same but have completely different lifecycles. Once enrolled, you're a student forever — that row is a historical record and never gets deleted. But your access can be revoked (refund within 30 days), can expire (monthly subscription plan), or can have different scope (lifetime one-time purchase vs. rolling subscription). If you shoved access state into the enrollment row, a refund would mean mutating enrollment history. Worse: subscription users could be "enrolled" in 50 courses — you'd need to check a subscription status completely unrelated to any single enrollment row. The Access table is a separate "keycard service" — the Video Playback Svc checks it before serving a single byte of video. Separating them means: you can revoke access without touching enrollment history, subscriptions and one-time purchases coexist cleanly, and audits show both "who ever enrolled" and "who can watch right now" as independent answers.

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

### Lessons & Video
```
GET  /courses/{courseId}/curriculum                              — ordered sections + lessons (title, duration, free preview flag)
GET  /courses/{courseId}/lessons/{lessonId}/video               — signed CloudFront URL for HLS stream (requires enrollment/access check)
```

### Assignments
```
POST /courses/{courseId}/lessons/{lessonId}/assignment/submit   — upload file or text answer for manual instructor grading
GET  /courses/{courseId}/lessons/{lessonId}/assignment/result   — fetch grade + instructor feedback after grading
```

### Reviews
```
POST /courses/{courseId}/reviews                                 — submit rating (1–5) + comment (one per enrolled student)
GET  /courses/{courseId}/reviews?page=&sort=recent|helpful      — paginated reviews list
```

### Certificates
```
GET  /me/certificates/{courseId}                                 — signed S3 download URL for issued certificate (404 if not completed)
```

> **WHY GET /courses/{courseId}/curriculum?**
> A student landing on a course detail page needs to see the full table of contents — sections, lesson titles, durations, and which lessons are free previews — before deciding to buy. Without this endpoint, the client would have to call `GET /courses/{courseId}` and embed the entire curriculum in that response, making the course-listing API bloated. Separating it means the catalog can return lightweight cards, and the browser fetches curriculum only when a user opens a course detail page (lazy-load). It also lets unauthenticated visitors browse the syllabus without being enrolled.

> **WHY GET /courses/{courseId}/lessons/{lessonId}/video?**
> Video streaming is not just a URL hand-off — it is an access-control checkpoint. The Video Playback Svc checks the `Access` table (not just Enrollments) before generating a short-lived CloudFront signed URL (expires in 24 hours). Without a dedicated endpoint, the client would either embed the CDN URL directly in the curriculum response (exposing it to non-enrolled users who intercept the network response) or re-check enrollment on every HLS segment request (impossible at CDN level). This endpoint is the single gate: enroll + pay → Access row exists → signed URL issued → student watches. Revoked access (refund) means the next video load returns 403 — no change needed to CDN config.

> **WHY POST /courses/{courseId}/lessons/{lessonId}/assignment/submit?**
> Quiz submit already exists for MCQ auto-grading, but assignments are different: they are files or long-form text reviewed by the instructor, not auto-graded. They need their own endpoint to handle multipart file uploads, store the submission linked to a specific attempt, and trigger a Kafka event that notifies the instructor. Without this endpoint, the quiz flow would need to branch on question type — mixing auto-graded and manually-graded paths in one endpoint, complicating both the API contract and the Assignment Svc logic.

> **WHY POST /courses/{courseId}/reviews AND GET /courses/{courseId}/reviews?**
> Reviews are the primary trust signal on an online learning platform — the Comment & Review Svc is already called out in the HLD diagram, but without REST endpoints it has no public interface. POST enforces the "one review per enrolled student" rule (UNIQUE constraint on user_id + course_id) and fires a Kafka event to update the denormalized `course_stats.avg_rating` asynchronously. GET is separate so it can be cached at the CDN layer (reviews change slowly) while write traffic hits the Review Svc directly.

> **WHY GET /me/certificates/{courseId}?**
> Certificate generation is async (Kafka consumer, described in Section 11), so the client cannot get the PDF URL from the enrollment flow directly. This endpoint lets the frontend poll (or deep-link from the completion email) to retrieve the signed S3 download URL. A 404 response means the certificate worker has not yet processed the completion event — the client can show "Generating certificate..." and retry. Without this endpoint, the only way to surface the certificate URL is by embedding it in the enrollment row response, which couples the enrollment API to the certificate lifecycle.

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

> **WHY ASYNC VIDEO TRANSCODING + HLS EXISTS? (Beginner Explanation)**
> Think of uploading a raw video like handing a chef a whole raw chicken — it needs to be prepped before it can be served. A 2 GB, 1080p `.mp4` is not streamable as-is: it has to be cut into 6-second chunks, encoded at 4 different quality levels (1080p/720p/480p/360p), and packaged into HLS playlists so any device on any network speed can play it smoothly. This FFmpeg processing takes 10–15 minutes. If you did it synchronously — making the instructor wait for an HTTP response — the connection would time out, waste server CPU, and deliver a terrible UX. Instead: instructor uploads directly to S3 (bypassing your server), an S3 event triggers Lambda, Lambda drops a message on Kafka, and a pool of cheap Spot EC2 workers picks it up asynchronously. Instructor gets an instant "upload received" confirmation and an email 15 min later saying "video ready." The alternative — synchronous transcoding in the upload API — would block the HTTP connection for 15 min, crash on timeouts, and triple your compute bill by running it on always-on servers instead of 70%-cheaper Spot instances.

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

> **WHY CDN EXISTS FOR VIDEO STREAMING? (Beginner Explanation)**
> CDN = local warehouse near you instead of one central warehouse. Your raw HLS segments live in one S3 bucket in, say, us-east-1 (Virginia). A student in Mumbai requesting a 6-second video segment would wait 200–400 ms just for the round-trip to Virginia — before any actual data arrives. At 10 segments/minute that's constant buffering. CloudFront has 200+ edge locations worldwide; the first student in Mumbai to watch a popular course causes CloudFront to fetch the segments from S3 and cache them at the Mumbai edge. Every student after that hits the local edge at <50 ms. Cache hit rate for popular courses is 95%+ — meaning 95% of requests never touch S3. Why not just replicate S3 to every region? S3 replication is expensive, slow to propagate, and not designed for high-frequency tiny-file reads (billions of 6-second `.ts` segments). CDN is purpose-built: immutable content, massive read throughput, 30-day cache TTL per segment, automatic routing to the nearest edge.

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

> **WHY PROGRESS TRACKING WORKS THE WAY IT DOES? (Beginner Explanation)**
> Imagine dog-earing a book at two places: the page you're on right now, and the farthest page you've ever reached. That's exactly `last_position_sec` (resume point) and `max_position_sec` (completion check). You can't just save the player's current timestamp — if a student rewinds to minute 1 to re-listen a concept, then closes the tab, their "current time" is 60 seconds even though they'd previously watched 40 minutes. Storing only current time would un-complete their progress. So `max_position_sec` uses `GREATEST(existing, new)` — it can only go up, never down on rewind. "37% complete" is computed as max_position_sec / duration_sec per lesson, aggregated across all lessons. Why batch events every 30 seconds instead of every second? 1 million students × 1 heartbeat/second = 1 million API calls/second on your Progress service. At 30-second batching it drops to ~33K calls/second — a 30x reduction achieved purely by buffering 3 events on the client before sending. The Kafka buffer then absorbs bursts, returning 200 OK immediately so video playback is never blocked waiting for a DB write.

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

> **WHY INSTRUCTOR PAYOUT IS SEPARATE FROM THE MAIN PAYMENT FLOW? (Beginner Explanation)**
> When a student pays $49.99, that's one Stripe transaction — clean, instant, done. But the instructor's 70% ($34.99) cannot and should not be sent in the same moment. Payouts are batched weekly or monthly, subject to fraud holds, minimum thresholds, and tax reporting. Instructors use Stripe Connect — a separate sub-account per instructor — which is a completely different Stripe feature from the customer-facing PaymentIntent. Mixing payout logic into the enrollment payment flow means: a payout failure would block enrollment, one instructor's bad bank details would delay a student's course access, and payout schedules would be tightly coupled to purchase events. Instead: student pays → payment.completed event → enrollment created → done. The payout system runs on a cron schedule, reads from a payout_ledger table (recording each platform's share and instructor's share per transaction), and calls Stripe Connect transfers independently. The 70/30 split is computed, logged, and transferred as a completely isolated background process — failure there never touches a student's course access.

---

> **WHY QUIZ ATTEMPT STATE IS MANAGED THIS WAY? (Beginner Explanation)**
> A quiz is like a sealed exam envelope. You need to track: did the student open the envelope yet (so they can't "start" two attempts simultaneously), what time did they open it (so you can enforce the countdown), how many envelopes have they used (so they can't retry indefinitely), and what answers were inside when they sealed it back (so they can't change answers after time runs out). The `quiz_attempts` row created on POST .../quiz/start is that sealed envelope — status='IN_PROGRESS', start_time=now(), attempt_number=N. If the student closes their browser mid-quiz, the row still exists with its timestamp. When they reconnect, the server computes remaining_time = time_limit - (now() - start_time) and can auto-submit when it hits zero. Without this state: a student could open 5 browser tabs to start 5 simultaneous attempts, submit answers after the timer, or refresh to get unlimited retries. The attempt row is the contract — once created, it is the source of truth for that quiz session.

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

> **WHY CERTIFICATE GENERATION WORKS THE WAY IT DOES? (Beginner Explanation)**
> A certificate is a fancy receipt that gets printed exactly once, the moment you finish. The system does not generate a PDF on every page load — that would mean rendering a document for every profile visit, wasting CPU and producing different PDFs each time. Instead, completion_status hitting 100% fires a Kafka event exactly once. A certificate consumer worker fetches a pre-designed template from S3 (think a blank diploma with logos and borders), fills in the student's name, course title, instructor name, and completion date, renders it to a PDF, and uploads that permanent file back to S3. The student gets a stable, signed download URL. Idempotency is critical here: Kafka can redeliver the same "course.completed" event if a consumer restarts. Without the "does this certificate already exist?" guard, a student could receive 3 identical certificates in their inbox. The PDF is a one-time artifact stored in S3 — not a dynamically rendered page — because it's cheap to store ($0.023/GB), instantly downloadable from CDN, and verifiable as a permanent record even years later.

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

> **WHY ELASTICSEARCH INSTEAD OF SQL LIKE FOR COURSE SEARCH? (Beginner Explanation)**
> `SQL LIKE '%machine learning%'` is like searching a library by walking every single aisle and reading every book spine. It cannot use an index, so it scans the entire courses table — 100K rows, each with a 500-word description, on every keypress. Elasticsearch is like a librarian who pre-built an inverted index: for every word, it already knows exactly which courses mention it. Type "machine learning" → instant ranked results. It also handles things SQL cannot do without serious pain: typos ("mechine lerning" still finds results via fuzzy matching), relevance scoring (title match ranked higher than description match), faceted filters (category=Programming AND price<$50 AND rating≥4 in a single sub-millisecond query), and autocomplete suggestions as you type (ngram tokenizer). The CDC aggregator pipeline keeps Elasticsearch in sync with Course DB changes asynchronously — so search is always near-real-time but never in the hot write path. The alternative — SQL LIKE with multiple WHERE clauses — degrades exponentially as filters compound, is impossible to rank by relevance, and would require a full-table scan on every search request.

> **WHY THE RECOMMENDATION ENGINE ("STUDENTS ALSO WATCHED") WORKS THE WAY IT DOES? (Beginner Explanation)**
> "Students also watched" is collaborative filtering — not magic. The simplest mental model: find every student who enrolled in the same course as you, look at what else they bought that you haven't, and surface the most common overlaps. The platform collects behavioral signals: enrollments, completion rates, ratings, search queries, and time spent on course detail pages. These feed a batch ML job (runs nightly, not in real-time) that computes similarity scores between courses and between users. Results are pre-computed and written to Redis — because computing personalized recommendations at query time for every page load would require scanning millions of enrollment rows per user per request. When you open the homepage, the recommendation service does a fast Redis key lookup, not a live ML inference. Why not recommend "most popular courses" to everyone? It ignores what you already know — a backend developer with 5 Java courses gets the same beginner Python suggestion as a complete newcomer, which is both useless and a wasted personalization opportunity.

> **WHY LIVE CLASS AND RECORDED CLASS ARE ARCHITECTURALLY DIFFERENT? (Beginner Explanation)**
> A recorded video is like a book — it exists before you open it, you can pause, rewind, and watch at any speed. A live class is like a phone call — both instructor and student must be present at the same moment, and you cannot rewind real-time. This difference drives completely different infrastructure. Recorded videos use S3 → CDN → HLS: pull-based, heavily cached, segments pre-exist on 200 edge servers worldwide before the student even clicks play. Live classes use WebRTC or RTMP → a media server (e.g., AWS IVS or Agora) → push-based stream to students — there is nothing to cache yet because the content is being created millisecond by millisecond. Live classes also need real-time signaling: WebSocket connections for hand-raises, chat messages, participant list updates, and mute/unmute controls — none of which exist in the VOD pipeline. The critical failure modes are different too: a CDN hiccup on a recorded video just stalls for a second; a media server hiccup on a live class disconnects all students simultaneously. Live streams are typically later recorded and ingested into the VOD pipeline (S3 → Kafka → Transcode) so they become replayable assets, but while live they are an entirely separate real-time system.

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

---

## KEY PATTERNS REFERENCED IN THIS DESIGN

> **For the 2-year developer:** These are the hidden concepts behind design decisions in this system. Each has a dedicated deep-dive file.

### CDN Origin Pull vs Origin Push
**Why it matters here:** Course videos → origin pull (can't predict which courses are popular, millions of them). Live class recordings → origin push immediately after recording ends (students log in within minutes, so pre-warm all CDN edges before they arrive). Cache-Control: video segments use immutable + 1-year TTL with content-addressed URLs.
**Deep dive:** `../../CDN_Origin_Pull_vs_Origin_Push.md`

### Object vs Block vs File Storage
**Why it matters here:** Video lecture bytes → S3 (object storage). Course materials, PDFs → S3. PostgreSQL on EBS for: user progress, enrollments, certificates, quiz scores. CDN in front of S3 for global video delivery.
**Deep dive:** `../../Object_vs_Block_vs_File_Storage_S3_EBS_EFS.md`

### Cursor Pagination
**Why it matters here:** Course catalog with 100K+ courses. Students browse by category, filter by rating, scroll infinitely. OFFSET pagination scans thousands of rows. Cursor on (rating, course_id) = direct index seek per page, consistent during enrollment count updates.
**Deep dive:** `../../Cursor_Pagination_vs_Offset_Pagination.md`

### Graceful Degradation
**Why it matters here:** Certificate generation service is down → show "Your certificate will be emailed shortly" and queue the generation. Don't fail the course completion flow because certificate service is unavailable. Student still gets confirmation; certificate generates when service recovers.
**Deep dive:** `../../Graceful_Degradation.md`

### CAP Theorem
**Why it matters here:** AP for course catalog and video playback (slightly stale course info is fine). CP for enrollment and payment (don't risk enrolling a user without charging them, or charging without enrolling — during partition, reject enrollment writes rather than risk inconsistency).
**Deep dive:** `../../CAP_Theorem_Applied_What_Actually_Breaks.md`
