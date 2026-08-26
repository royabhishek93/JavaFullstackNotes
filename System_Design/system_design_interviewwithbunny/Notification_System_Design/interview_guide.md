Notification System — Interview Drawing Guide

---

## How to Open (First 60 Seconds)

Say this out loud:
> "A notification system delivers messages to users across multiple channels — email, SMS, push, in-app. At scale (1M+ notifications/min on Black Friday), the key challenges are: no notification loss, respecting provider rate limits, honoring user preferences, and prioritizing OTP over marketing."

Then write on the board:
```
Clients → API Gateway → Notification Svc → Kafka → Consumers → Providers → User
```

---

## 1. Functional Requirements

Feature 1: Support multiple delivery channels (email, SMS, push, in-app)
Feature 2: Create, update, manage notification templates with variables/placeholders ({{name}}, {{order_id}})
Feature 3: User preferences per channel and notification type (promotional, transactional, alerts)
Feature 4: Immediate and scheduled notification delivery (send now or schedule for future)
Feature 5: Track delivery status per notification (PENDING → SCHEDULED → SENT → DELIVERED → FAILED → CANCELLED)
Feature 6: Bulk notifications (campaigns) with rate limiting
Feature 7: Reporting and analytics (delivery rates, open rates, click rates, failures)
Feature 8: Retry mechanism for failed deliveries with exponential backoff

---

## 2. Non-Functional Requirements

Scale: 1M+ notifications/min during peak (Black Friday, breaking news)
CAP: Availability >> Consistency (eventual consistency for delivery status acceptable)
Latency: Real-time for OTP (<10s), 5–10s delay for transactional, 30 min for promotional
Reliability: At-least-once delivery guarantee — no notification lost, retry failed deliveries

---

## 3. Core Entities

```
Entity 1: User + Client
  user_id, email, phone, device_tokens[] (FCM/APNS), preferences {channels, types, do_not_disturb}

Entity 2: NotificationPreferences
  user_id
  channels  {email: true, sms: false, push: true, inapp: true}
  types     {promotional: false, transactional: true, alerts: true}
  do_not_disturb: false

Entity 3: NotificationContent
  notification_id, user_id (recipient_id), external_user_id
  template_id, channel (EMAIL/SMS/PUSH/INAPP)
  payload {variables}, status, priority (high/normal/low)
  scheduled_at, created_at, metadata

Entity 4: Template
  template_id, name, channel, subject (email), body (with {{variable}} placeholders)
  variables[] (list of expected vars), version, is_active, created_at

Entity 5: DeliveryStatus
  delivery_id, notification_id, channel, provider (Twilio/SendGrid/FCM/APNS)
  provider_message_id, status (SENT/DELIVERED/FAILED), sent_at, delivered_at
  error_message, retry_count

Entity 6: Notifications_outbox
  outbox_id, notification_id, event_type, payload
  published (boolean), created_at
  → Transactional outbox pattern for at-least-once Kafka publish

Entity 7: Notifications (main table)
  notification_id, user_id, external_user_id, template_id, channel
  payload, status, priority, scheduled_at, metadata
```

---

## 4. API Design

### Notification Operations
```
POST /api/v1/notifications
  Body: { templateId, recipientId, variables, channels[], priority, scheduledAt? }
  Response: { notificationId, status: 'PENDING' }

GET /api/v1/notifications/{notificationId}/status
  Response: { status: 'DELIVERED', sentAt, deliveredAt }
```

### Template Management
```
POST   /api/v1/templates              → Create template with placeholders
GET    /api/v1/templates              → List all templates (paginated)
GET    /api/v1/templates/{id}/{ver}   → Get specific template version
PUT    /api/v1/templates/{id}         → Creates new version (immutable, never edits existing)
DELETE /api/v1/templates/{id}         → Deactivates (sets is_active=false)
```

### User Preferences
```
PUT /api/v1/preferences
  Body: { channels: {email: bool, sms: bool, push: bool}, types: {promotional: bool}, dnd: bool }

GET    /api/v1/preferences/{userId}   → Read preferences
DELETE /api/v1/preferences/{userId}   → Reset to defaults
```

---

## 5. Draw the HLD (Top Diagram in Image)

Draw left to right. Start with clients, end with databases.

```
┌──────────┐     ┌─────────────────────┐
│ Clients  │────▶│  API Gateway &      │
│(Amazon/  │     │  Load Balancer      │
│  Uber)   │     └──────┬──────────────┘
└──────────┘            │
                        ├──────────────────▶ Template Svc ──────▶ Template DB
                        │
                        ├──────────────────▶ User Preference Svc ▶ UserPref DB
                        │
                        └──────────────────▶ Notification Svc ───▶ Notification Provider
                                                                     (Email/SMS/Push/InApp)
```

**Say while drawing:**
- API Gateway: Authentication (JWT/API key), Rate limiting (100 req/min per client), Routing, Round-robin LB
- Template Svc: CRUD for notification templates, version management
- User Preference Svc: per-channel and per-type opt-in/out, DND mode, cache in Redis
- Notification Svc: core orchestrator — validates template + user prefs, publishes to Kafka
- Notification Evt (MQ): Kafka for async processing, prioritized queues
- Reporting Svc: tracks delivery metrics, analytics (sent, delivered, failed, open rates)

---

## 6. Draw the LLD (Bottom Diagram in Image)

Draw it in 5 layers:

### Layer 1 — Entry
```
Clients → API Gateway → Notification Svc
```

### Layer 2 — Write Path (Outbox Pattern)
```
Notification Svc
    │
    ▼
┌──────────────────────────────────────┐
│  Single Transaction (DB Write)       │
│                                      │
│  INSERT → Notifications              │  ← status=PENDING
│  INSERT → Notifications_outbox       │  ← published=false
└──────────────────────────────────────┘
    │
    ▼  CDC/Publisher polls outbox every 100ms
    │  SELECT * WHERE published=false LIMIT 1000
    │  Publish to Kafka → UPDATE published=true
    ▼
Kafka (Notification Queue)
```

### Layer 3 — Kafka Topics (draw as 6 lanes)
```
notifications.critical.{channel}    ← OTP, security alerts     (<10s SLA,  20 workers)
notifications.standard.{channel}    ← orders, shipping         (5 min SLA, 30 workers)
notifications.promotional.{channel} ← marketing, newsletters   (30 min SLA, 10 workers)
notifications.bulk.{channel}        ← campaigns (100K+)        (low priority, 5 workers)
notifications.retry                 ← failed, exponential backoff (1m → 5m → 15m)
notifications.dlq                   ← 3 retries exhausted, ops alert
```

### Layer 4 — Consumer to Provider
```
Dlvy Cons (consumer group)
    │
    ├── 1. Idempotency check
    │      SELECT COUNT(*) FROM delivery_status
    │      WHERE notification_id=X AND channel=Y
    │      if exists → SKIP (already sent)
    │
    ├── 2. Rate Limiter (ABC box in diagram)
    │      Redis token bucket per provider
    │      if tokens=0 → backpressure to Kafka
    │
    └── 3. Route by channel:
               EMAIL ──▶ Email Svc Provider  ──▶ SendGrid / AmazonSES
               SMS   ──▶ SMS Svc Provider    ──▶ Twilio / MSG91
               PUSH  ──▶ inAPP Svc Provider  ──▶ FCM (Android) / APNS (iOS)
               OTP   ──▶ OTP Svc             ──▶ dedicated fast-track
```

### Layer 5 — Side Services
```
User Preference Svc ──▶ Kafka (topic: user.preference)
                               │
                               ▼
                         User Pref Consumer ──▶ userpref cache (Redis 24h TTL) ──▶ UserPref DB

Reporting Svc ──▶ reads from Kafka delivery_status events
```

---

## 7. Component Cheat Sheet (What to Say for Each Box)

### API Gateway
- Authentication & Authorization (JWT token, API key)
- Rate limiting: 100 req/min per client
- Routing to correct service
- Round-robin load balancing

### Notification Svc (6-step internal flow)
```
Step 1: Fetch template
  Redis: GET template:{id}:{version} (1h TTL, 95% hit rate)
  On miss: SELECT * FROM templates WHERE template_id=X AND is_active=true

Step 2: Validate variables
  Check all required variables present
  Missing variable → return 400 "Missing variable: name"

Step 3: Fetch user preferences
  Redis: GET user_pref:{userId} (24h TTL)
  On miss: query UserPref DB → cache result (24h)

Step 4: Check opt-in
  channels.email=false  → skip email channel
  types.promotional=false AND type='promotional' → skip entirely
  do_not_disturb=true → skip all channels

Step 5: Render template
  Replace {{name}} → "Alice", {{order_id}} → "ORD456"
  Result: {subject: "Order ORD456 confirmed", body: "Hi Alice..."}

Step 6: Outbox transaction
  BEGIN TRANSACTION
    INSERT notifications (status=PENDING)
    INSERT notifications_outbox (published=false)
  COMMIT
  Return 200 OK { notificationId: 'NOTIF789', status: 'PENDING' }
```

### Transactional Outbox (critical — draw this first when asked about reliability)
```
Problem — dual write race conditions:
  Option A: INSERT DB → Publish Kafka
    If Kafka fails → notification stuck in DB, never sent
  Option B: Publish Kafka → INSERT DB
    If DB fails → notification in Kafka but no record = lost

Solution — Outbox pattern:
  BEGIN TRANSACTION
    INSERT notifications      (status=PENDING)
    INSERT notifications_outbox (published=false)
  COMMIT   ← atomic, both or neither
  ─────────────────────────────────────
  CDC/Publisher polls every 100ms:
    SELECT * FROM notifications_outbox
    WHERE published=false
    ORDER BY created_at LIMIT 1000

    For each record:
      Determine topic by priority + channel:
        high + email   → notifications.critical.email
        normal + sms   → notifications.standard.sms
        low + email    → notifications.promotional.email
      Kafka.send(topic, key: notification_id, value: payload)
      If success → UPDATE SET published=true, published_at=now()
      If Kafka fails → published stays false → retry next poll

Guarantee: If DB COMMIT succeeded → message WILL eventually reach Kafka
```

### Kafka Consumer (Dlvy Cons)
```
1. Consume from topic (e.g., notifications.standard.email)
2. Idempotency:
     SELECT COUNT(*) FROM delivery_status
     WHERE notification_id='NOTIF789' AND channel='EMAIL'
     if > 0 → skip (Kafka at-least-once may redeliver)
3. Rate limit check (Redis Lua script atomic)
4. Call provider API
5. INSERT delivery_status (status=SENT, provider_message_id)
6. Provider sends webhook async → UPDATE status=DELIVERED
```

### Rate Limiter — ABC box (Token Bucket)
```
Algorithm: Token Bucket (Redis)
Key:      rate_limit:email:sendgrid
Capacity: 100 tokens (max burst)
Refill:   100 tokens/sec (matches provider limit)

Atomic Lua script (thread-safe):
  local tokens = redis.call('GET', key) or capacity
  if tokens >= 1 then
    redis.call('DECR', key)
    return 1  -- proceed
  else
    return 0  -- rate limited, wait
  end
  redis.call('EXPIRE', key, 10)

Provider limits:
  Twilio SMS:    100/sec
  SendGrid:       50/sec (free tier), 10K/sec (paid)
  FCM:        10,000/sec
  APNS:        <5,000/sec (best practice)

Backpressure flow:
  Rate limited → consumer sleeps 100ms
  → Kafka buffers messages (millions capacity)
  → lag increases → auto-scale consumers
  → still subject to provider limit (bottleneck)
```

### Email Provider (SendGrid / AmazonSES)
```
Send:
  POST https://api.sendgrid.com/v3/mail/send
  { personalizations: [{to: [{email: 'alice@example.com'}]}],
    from: {email: 'noreply@company.com'},
    subject: 'Order ORD456 confirmed',
    content: [{type: 'text/html', value: '<html>...'}] }
  Response: 202 Accepted { id: 'msg_abc123' }
  (async — 202 does NOT mean delivered yet)

Include for promotional emails:
  Unsubscribe link (CAN-SPAM compliance)
  Plain-text fallback

Webhooks (async delivery confirmation):
  POST /webhooks/sendgrid
  Event types:
    delivered → email reached inbox
    opened    → user opened (tracked via 1px image)
    clicked   → user clicked link
    bounced   → invalid address (permanent failure, don't retry)
    spam      → marked as spam
  Handler: UPDATE delivery_status SET status='DELIVERED'
           WHERE provider_message_id='msg_abc123'
```

### SMS Provider (Twilio / MSG91)
```
Send:
  POST https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages.json
  { To: '+919876543210',
    From: '+12345678901',
    Body: 'Hi Alice, your order ORD456 confirmed. Track: https://track.link/ORD456' }
  Response: { sid: 'SM1234abcd', status: 'queued' }

Rules:
  160 char limit for single SMS (longer messages split, costs more)
  Add opt-out: "Reply STOP to unsubscribe" (TCPA compliance)

Webhooks:
  POST /webhooks/twilio
  { MessageSid: 'SM1234abcd', MessageStatus: 'delivered' }
  Statuses: queued → sent (to carrier) → delivered (to phone) / failed
```

### Push Provider (FCM / APNS)
```
FCM (Android / Web):
  POST https://fcm.googleapis.com/v1/projects/{project_id}/messages:send
  { message: {
      token: 'fcm_token_android_123',
      notification: { title: 'Order Confirmed',
                      body: 'Your order ORD456 confirmed' },
      data: { order_id: 'ORD456', deep_link: 'app://orders/ORD456' },
      android: { priority: 'high' }
    }
  }
  Success: { name: 'projects/.../messages/0:1234567890' }
  Failure: 'invalid-registration-token'
    → device uninstalled app
    → UPDATE users SET device_tokens = array_remove(tokens, 'bad_token')
    → DO NOT retry (permanent)

APNS (iOS):
  POST https://api.push.apple.com/3/device/{apns_token}  (HTTP/2)
  Headers: { apns-topic: 'com.company.app', apns-priority: 10 }
  Body: { aps: { alert: { title: 'Order Confirmed',
                           body: 'Your order ORD456 confirmed' },
                  badge: 1, sound: 'default' },
           order_id: 'ORD456' }
  Success: 200 OK
  Failure: 410 Gone → device uninstalled → remove token, don't retry

Multi-device fanout:
  User has 3 devices: Android phone, iOS tablet, web browser
  → Send to all 3 tokens independently
  → INSERT 3 rows into delivery_status (one per device)
```

### OTP Service (dedicated fast-track)
```
Generate: 6-digit code '123456'
Store:    SET otp:{userId}:login '123456' EX 300  (5 min TTL in Redis)

Create notification:
  POST /api/v1/notifications
  { templateId: 'otp_login', recipientId: 'user123',
    variables: {otp: '123456'}, channels: ['sms'], priority: 'critical' }

Fast-track:
  → notifications.critical.sms (20 dedicated workers)
  → NO rate limiting for OTP (critical path, user waiting)
  → Target: <10 seconds end-to-end

Verify on submit:
  GET otp:{userId}:login from Redis
  if matches + not expired → login success
  if expired (TTL hit) → prompt resend
```

### Retry Mechanism
```
Failure types:
  TEMPORARY (retry):
    - Provider timeout (no response in 10s)
    - Rate limit 429 (hit provider limit)
    - Network error (connection refused)
    Strategy: Exponential backoff
      1st retry: 1 min
      2nd retry: 5 min
      3rd retry: 15 min
      After 3 failures → DLQ (notifications.dlq), alert ops team

  PERMANENT (don't retry):
    - Invalid recipient: 550 User not found, invalid phone
    - Unsubscribed: user opted out → honor preference
    - Token expired: APNS 410 Gone, FCM invalid-registration-token
    - Email bounced: 550/invalid address
    Action: UPDATE delivery_status SET status='FAILED',
            error_message='Invalid email address'
```

### Reporting Svc
```
Real-time (Redis counters):
  INCR sent_count:{date}                       ← total sent today
  HINCRBY stats:{template_id} delivered 1      ← per-template delivery count

Batch (Hourly aggregation — Spark/Flink):
  SELECT template_id, COUNT(*), SUM(delivered), SUM(failed)
  FROM delivery_status
  GROUP BY template_id, DATE_TRUNC('hour', sent_at)

Store: InfluxDB / BigQuery for dashboards
Metrics: delivery rate, open rate, click rate, bounce rate, failure rate
```

---

## 8. State Machine to Draw

Always draw this when asked about notification lifecycle:

```
            ┌─────────────────────────────┐
            │          PENDING            │  ← created, in outbox
            └─────────────┬───────────────┘
                          │ CDC publishes to Kafka
                          ▼
            ┌─────────────────────────────┐
            │         SCHEDULED           │  ← scheduled_at in future, waiting
            └─────────────┬───────────────┘
                          │ scheduled_at reached
                          ▼
            ┌─────────────────────────────┐
            │           SENT              │  ← delivered to provider, awaiting confirmation
            └──────┬──────────────┬───────┘
                   │              │
        webhook    │              │  provider error
        confirmed  │              ▼
                   │   ┌──────────────────────┐
                   │   │  FAILED (permanent)  │  ← invalid email, unsubscribed, 410 Gone
                   │   └──────────────────────┘
                   │
                   │              temp failure → notifications.retry
                   │              → retry_count++ → 1m → 5m → 15m
                   │              → if retry_count >= 3 → DLQ
                   ▼
            ┌─────────────────────────────┐
            │        DELIVERED            │  ← provider confirmed delivery
            └─────────────────────────────┘

CANCELLED: user/system cancelled before send
```

---

## 9. Database Schema

### Notifications (main table)
```
notification_id   uuid PRIMARY KEY
user_id           uuid                  ← internal user ID
external_user_id  varchar(255)          ← client's own user ID (e.g. Amazon customer ID)
template_id       uuid FK → Templates
channel           enum (EMAIL/SMS/PUSH/INAPP)
payload           jsonb                 ← rendered: {subject, body, to, variables}
status            enum (PENDING/SCHEDULED/SENT/DELIVERED/FAILED/CANCELLED)
priority          enum (critical/high/normal/low)
scheduled_at      timestamptz           ← nullable, for future sends
created_at        timestamptz
metadata          jsonb                 ← campaign_id, tags, etc.

Indexes:
  INDEX (user_id, created_at)           ← user notification history
  INDEX (status, scheduled_at)          ← scheduler polling
  INDEX (template_id)                   ← template usage stats

Partitioned by: created_at monthly (notifications_2026_01, _02, ...)
Old partitions: archived to S3 after 6 months
```

### Notifications_outbox (transactional outbox)
```
outbox_id         uuid PRIMARY KEY
notification_id   uuid FK → Notifications
event_type        varchar(50)           ← 'notification.created'
payload           jsonb                 ← notification details for Kafka
published         boolean DEFAULT false ← CDC polls WHERE published=false
published_at      timestamptz           ← nullable, when published
created_at        timestamptz

Purpose: atomic guarantee — if DB COMMIT succeeded, Kafka message will eventually publish
CDC polls: SELECT * WHERE published=false ORDER BY created_at LIMIT 1000
```

### Templates (immutable versioning)
```
PK: (template_id, version)            ← composite PK, same ID across versions

template_id   uuid
version       int                      ← starts at 1, increments on update
name          varchar(255)             ← 'Order Confirmation Email'
channel       enum (EMAIL/SMS/PUSH/INAPP)
subject       text                     ← 'Order {{order_id}} confirmed' (email only)
body          text                     ← 'Hi {{name}}, your order {{order_id}}...'
variables     jsonb                    ← ['name', 'order_id'] (required vars list)
is_active     boolean                  ← only active templates can be used
created_at    timestamptz

On update: INSERT new version (version+1, is_active=true)
           UPDATE old version SET is_active=false
Never modify existing rows → immutable audit trail + rollback capability + A/B testing
```

### User_preferences (UserPref DB)
```
PK: (client_id, external_user_id)     ← composite PK

client_id         varchar(100)         ← 'amazon', 'uber'
external_user_id  varchar(255)         ← client's user ID
channels          jsonb                ← {email: true, sms: false, push: true, inapp: true}
types             jsonb                ← {promotional: false, transactional: true, alerts: true}
do_not_disturb    boolean DEFAULT false ← block all notifications when true
updated_at        timestamptz

Enforcement: check BEFORE publishing to Kafka:
  email=false     → skip email channel
  promotional=false → skip promo notifications
  dnd=true        → skip all
```

### delivery_status (delivery tracking)
```
delivery_id           uuid PRIMARY KEY
notification_id       uuid FK (INDEXED)     ← for idempotency check
channel               enum (EMAIL/SMS/PUSH/INAPP)
provider              varchar(50)            ← SendGrid / Twilio / FCM / APNS
provider_message_id   varchar(255)           ← INDEXED (webhook lookups)
provider_response     jsonb                  ← full provider response for debugging
status                enum (SENT/DELIVERED/FAILED/BOUNCED/OPENED/CLICKED)
sent_at               timestamptz
delivered_at          timestamptz            ← nullable
error_message         text                   ← nullable, failure reason
retry_count           int DEFAULT 0

Indexes:
  INDEX (notification_id)               ← idempotency check
  INDEX (provider_message_id)           ← webhook event lookup
```

### Redis Keys
```
user_pref:{userId}               STRING (JSON)  TTL 24h    ← preferences cache
template:{templateId}:{version}  STRING (JSON)  TTL 1h     ← template cache (95% hit)
rate_limit:{channel}:{provider}  INT            no TTL     ← token bucket count
otp:{userId}:{purpose}           STRING         TTL 300s   ← OTP code (5 min expiry)
```

### Kafka Topics
```
notifications.critical.{channel}    ← OTP, security alerts, fraud   (20 workers)
notifications.standard.{channel}    ← orders, shipping, receipts    (30 workers)
notifications.promotional.{channel} ← marketing, newsletters        (10 workers)
notifications.bulk.{channel}        ← batch campaigns (100K+)       (5 workers)
notifications.retry                 ← failed, exponential backoff
notifications.dlq                   ← 3 retries exhausted, manual investigation
user.preference                     ← preference updates → User Pref Consumer → Redis
```

---

## 10. All 12 Scaling Techniques

### T1: Transactional Outbox
At-least-once delivery. Single DB transaction (INSERT notifications + INSERT outbox). CDC polls outbox → publishes to Kafka → marks published=true. Prevents lost notifications on crash.

### T2: Prioritized Kafka Topics
4 priority levels: critical/standard/promotional/bulk. Critical OTP processed immediately (<10s). Promotional: 30 min SLA. Worker allocation: 20/30/10/5.

### T3: Rate Limiting with Token Bucket
Redis atomic Lua script (check tokens → DECR → proceed). Provider limits: Twilio 100/sec, SendGrid 50/sec, FCM 10K/sec. Backpressure: consumers slow → Kafka buffers. Critical bypasses rate limit.

### T4: Template Caching
Redis key: `template:{id}:{version}`, 1h TTL, 95% hit rate. Immutable versions: never modify, always create new version on update. Enables A/B testing (route 50% to v1, 50% to v2) and rollback.

### T5: User Preference Caching
Redis key: `user_pref:{userId}`, 24h TTL. Check before publishing (not after). Kafka `user.preference` topic → User Pref Consumer updates cache on preference change.

### T6: Provider Failover (Circuit Breaker)
Multi-provider: primary SendGrid, fallback AmazonSES. If SendGrid failure rate >50% → open circuit → route to AmazonSES. Load balance: SendGrid 70%, SES 30%. Total capacity doubles.

### T7: Idempotent Consumers
Check delivery_status before sending: `SELECT COUNT(*) WHERE notification_id + channel`. Kafka at-least-once may redeliver on consumer restart. Without this: user receives 5 duplicate emails.

### T8: Database Partitioning
Notifications partitioned by created_at monthly (notifications_2026_01, _02...). delivery_status partitioned by sent_at. Old partitions archived to S3 after 6 months (cost + query speed).

### T9: Batch Processing for Bulk
Bulk campaigns (100K+ recipients): INSERT 1000 rows at a time to Notifications table. SendGrid bulk API: 1000 emails per call vs 1 email per call → 1000x fewer API calls, same throughput.

### T10: Kafka Consumer Auto-Scaling
100 partitions → 100 parallel consumers max. Monitor consumer lag: if lag > 1000 messages → add consumer instances (Kubernetes HPA). Throughput scales linearly with consumers (up to provider limit).

### T11: Async Webhook Processing
Provider webhooks (SendGrid/Twilio) → respond 200 OK immediately (don't block). Queue webhook events. Batched DB updates: update 100 delivery_status rows at once. Prevents webhook timeouts and retry storms.

### T12: Reporting Aggregation
Real-time: Redis INCR counters per date/template. Batch: Spark/Flink hourly aggregation from delivery_status. Store in InfluxDB/BigQuery for dashboards. Avoids heavy GROUP BY on live Notifications table.

---

## 11. Top Interview Questions — Diagram-First Answers

### Q1: How do you prevent notification loss? (Most asked)

Draw the Outbox box from Layer 2.

> "Transactional Outbox pattern. Single DB transaction writes both the notification row (status=PENDING) and an outbox row (published=false) — both commit or neither does. CDC service polls outbox every 100ms, publishes to Kafka, marks published=true. If Kafka is down, published stays false — retried on next poll. At-least-once from Outbox to Kafka. On consumer side: idempotency check (SELECT from delivery_status — if exists, skip). At-least-once + idempotency = exactly-once delivery to user."

---

### Q2: How do you handle rate limiting at scale?

Point to ABC (Rate Limiter) box.

> "Token bucket per provider in Redis. Atomic Lua script: if tokens >= 1 → DECR → proceed, else wait. Key: rate_limit:email:sendgrid, capacity 100, refill 100/sec matches SendGrid limit. On rate limit: consumer sleeps 100ms or pushes back to Kafka — Kafka buffers the backpressure. Multi-provider failover: primary SendGrid, fallback AmazonSES via circuit breaker (trips at 50% failure rate). Critical OTP bypasses — dedicated bucket with higher limit."

---

### Q3: Walk through complete notification flow end-to-end.

Trace the whole LLD diagram step by step:

```
(1) Trigger:
    POST /api/v1/notifications
    { templateId: 'order_confirmation', recipientId: 'user123',
      variables: {name: 'Alice', order_id: 'ORD456', amount: '$49.99'},
      channels: ['email', 'push'], priority: 'normal' }

(2) Notification Svc:
    → Fetch template: Redis hit → {subject: 'Order {{order_id}} confirmed', body: '...'}
    → Validate: name ✓, order_id ✓, amount ✓
    → Fetch user prefs: Redis hit → {email: true, push: true, transactional: true}
    → Check opt-in: email ✓, transactional ✓

(3) Render:
    subject: 'Order ORD456 confirmed'
    body:    'Hi Alice, your order ORD456 for $49.99 confirmed...'
    Generate notification_id: 'NOTIF789'

(4) Outbox transaction:
    BEGIN TRANSACTION
      INSERT notifications (NOTIF789, status=PENDING, channel=EMAIL, priority=normal)
      INSERT outbox (outbox_id, NOTIF789, published=false)
    COMMIT
    Return: 200 OK { notificationId: 'NOTIF789', status: 'PENDING' }

(5) CDC/Publisher (100ms later):
    SELECT outbox WHERE published=false → finds NOTIF789
    → priority=normal + channel=email → topic: notifications.standard.email
    Kafka.send(topic, key: NOTIF789, payload)
    UPDATE outbox SET published=true

(6) Email Consumer:
    Receives from notifications.standard.email
    Idempotency: SELECT delivery_status WHERE NOTIF789 + EMAIL → 0 rows → proceed
    Rate limit: Redis tokens=49 → DECR → proceed
    POST SendGrid API → 202 Accepted { id: 'msg_sg123' }

(7) Update:
    UPDATE notifications SET status='SENT', sent_at=now()
    INSERT delivery_status (NOTIF789, EMAIL, SendGrid, msg_sg123, SENT)

(8) SendGrid webhook (minutes later):
    POST /webhooks/sendgrid { event: 'delivered', sg_message_id: 'msg_sg123' }
    UPDATE delivery_status SET status='DELIVERED', delivered_at=now()
    UPDATE notifications SET status='DELIVERED'

(9) Push notification (parallel, same time as email):
    Push consumer → FCM.send(fcm_token_android_123, title='Order Confirmed')
    → INSERT delivery_status (NOTIF789, PUSH, FCM, status=SENT)
    → FCM response → INSERT delivery_status for each device

(10) Temporary failure:
    SendGrid times out (10s no response)
    → publish to notifications.retry { NOTIF789, retry_count: 1, scheduled_at: now()+1min }
    Retry consumer: waits 1 min → reattempts
    If fails again: retry_count=2, scheduled_at: now()+5min
    Max 3 retries: if all fail → notifications.dlq + alert ops

(11) Permanent failure:
    SendGrid webhook: { event: 'bounce', reason: 'Invalid email' }
    UPDATE delivery_status SET status='FAILED', error_message='Email bounced'
    UPDATE notifications SET status='FAILED'
    Don't retry (permanent)

(12) Final state transitions:
    PENDING → (outbox published) → in Kafka
    → (consumer picks up) → SENT
    → (webhook confirmed) → DELIVERED
    OR → (provider error, temp) → RETRY → DELIVERED or DLQ
    OR → (provider error, perm) → FAILED
```

---

### Q4: How do you handle user opt-outs and compliance?

Point to User Preference Svc and userpref cache.

> "Check preferences before publishing to Kafka — not after (wasted processing). Three checks: (1) channel: email=false → skip email channel, (2) type: promotional=false → skip all marketing, (3) DND: do_not_disturb=true → skip everything. Cache in Redis (24h TTL) — 95% preference checks never hit DB. Preference changes flow via Kafka user.preference topic → User Pref Consumer → invalidates Redis cache immediately. Compliance: GDPR (right to opt-out honored), CAN-SPAM (unsubscribe link in every marketing email), TCPA (SMS must have prior written consent)."

---

### Q5: How do you scale to 1M notifications/min?

Walk each layer on the diagram:

> "Five layers:
> (1) Kafka 100 partitions → 100 parallel consumers max, auto-scale on lag.
> (2) Worker allocation: 20/30/10/5 for crit/std/promo/bulk.
> (3) DB: Notifications partitioned monthly, old to S3 (hot data stays fast).
> (4) Batching: SendGrid bulk API sends 1000 emails/call → 1000x fewer API calls.
> (5) Redis caching: 95% template hit rate, 24h user pref cache → minimal DB reads.
> (6) Multi-provider: SendGrid + AmazonSES = 2x capacity, circuit breaker on failure."

---

## 12. Key Interview Tips (Memorize These)

**CRITICAL — Transactional Outbox mandatory:**
Never publish to Kafka without DB write in same transaction. If Kafka succeeds but DB fails → notification lost. Outbox guarantees: if DB commit succeeded, message WILL eventually publish.

**Most asked Q: "How prevent notification loss?"**
Answer: Outbox pattern (single transaction: INSERT notifications + INSERT outbox → COMMIT). CDC polls outbox (published=false) → publishes to Kafka → marks published=true. At-least-once delivery + idempotent consumers = exactly-once to user.

**Prioritized Kafka topics (always mention):**
notifications.critical.{channel} — OTP, <10s
notifications.standard.{channel} — orders, 5 min
notifications.promotional.{channel} — marketing, 30 min
notifications.bulk — campaigns
Worker allocation: 20 / 30 / 10 / 5. Critical bypasses rate limiting.

**Rate limiting must-say:**
Token bucket with Redis Lua script (atomic check + DECR). Provider limits: Twilio 100/sec, SendGrid 50/sec, FCM 10K/sec. Backpressure: consumers slow → Kafka buffers. Multi-provider failover: primary SendGrid → fallback AmazonSES (circuit breaker at 50% failure).

**NEVER skip user preference checks:**
Must honor opt-outs BEFORE Kafka publish (not after). Check: channel opt-in, notification type, DND mode. Regulatory compliance: GDPR, CAN-SPAM (unsubscribe link), TCPA (SMS opt-in). Cache in Redis (24h TTL).

**Template versioning:**
Immutable — create new version on update, never modify existing rows.
Benefits: (1) Audit trail, (2) A/B testing (route 50% to v1, 50% to v2), (3) Rollback (reactivate old version). Cache: `template:{id}:{version}` in Redis (1h TTL, 95% hit).

**Idempotent consumers:**
Check delivery_status (if exists → skip). Kafka at-least-once may deliver duplicates on consumer restart. Without idempotency: user receives 5 duplicate emails.

---

## 13. Quick Reference Card (Memorize These Numbers)

| Item | Value |
|---|---|
| Scale target | 1M+ notifications/min |
| OTP SLA | < 10 seconds |
| Transactional delay | 5–10 seconds acceptable |
| Promotional delay | 30 min acceptable |
| Twilio SMS limit | 100/sec |
| SendGrid limit | 50/sec (free), 10K/sec (paid) |
| FCM limit | 10,000/sec |
| APNS limit | <5,000/sec (best practice) |
| Retry schedule | 1 min → 5 min → 15 min → DLQ |
| Max retries | 3 |
| Redis user_pref TTL | 24 hours |
| Redis template TTL | 1 hour, 95% hit rate |
| OTP TTL | 5 minutes (300s) |
| OTP length | 6 digits |
| Outbox poll interval | every 100ms |
| Outbox batch size | 1000 records per poll |
| Kafka topics | critical / standard / promotional / bulk / retry / dlq |
| Critical workers | 20 |
| Standard workers | 30 |
| Promotional workers | 10 |
| Bulk workers | 5 |
| API rate limit per client | 100 req/min |
| DB partition retention | 6 months (then S3) |
| SendGrid bulk API | 1000 emails per call |
| Circuit breaker threshold | 50% failure rate → open |

---

## 14. Red Flags Interviewers Watch For

1. Publishing to Kafka before DB write → notification loss → say "Outbox pattern"
2. Checking user prefs AFTER Kafka → wasted processing → check BEFORE publishing
3. No idempotency → duplicate emails on consumer restart → check delivery_status first
4. Single provider, no failover → single point of failure → SendGrid + AmazonSES + circuit breaker
5. No priority queues → OTP delayed by bulk marketing → show 4-tier Kafka topic hierarchy
6. Synchronous provider calls in request path → high latency → Kafka is the async buffer
7. Modifying templates in-place → no audit trail → immutable versioning (new version on update)
8. No retry/DLQ → lost messages on temporary failure → exponential backoff + DLQ
9. No rate limiting → overwhelm providers → token bucket per provider per channel
10. Not honoring CANCELLED status → sending after user cancels → check status before send
