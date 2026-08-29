Interview With Bunny
System Design Complete Course
Video 15

System Design 15: Design Scalable Notifications System | SMS | OTP | Email & Push | HLD | LLD

In this video, we design a complete Notification System from scratch, explaining how large-scale companies like Netflix, Walmart, and Amazon send millions of notifications per minute reliably using Kafka, Outbox pattern, Redis, and microservices architecture.

Design Diagram

Design for System Design 15: Design Scalable Notifications System | SMS | OTP | Email & Push | HLD | LLD
Pre-Interview Memory Refresher
22 min revision
Updated 2026-01-26
Bonus: beyond the video + interview questions
Notification System (Multi-Channel Delivery)

"Client triggers notification → API Gateway → Notification Svc validates template & user preferences → Kafka queue (prioritized) → Notification Queue consumers → Provider routing (Email/SMS/Push/In-app) → External services (Twilio/SendGrid/FCM/APNS) → Delivery status → Rate limiting → Reporting"

1. Functional Requirements

Feature 1: Support multiple delivery channels (email, SMS, push notifications, in-app notifications)
Feature 2: Create, update, and manage notification templates with variables/placeholders
Feature 3: Support user preferences per channel and notification type (promotional, transactional, alerts)
Feature 4: Support immediate and scheduled notification delivery (send now or schedule for future)
Feature 5: Track delivery status for each notification (PENDING, SCHEDULED, SENT, DELIVERED, FAILED, CANCELLED)
Feature 6: Support bulk notifications (campaigns, announcements) with rate limiting
Feature 7: Provide reporting and analytics (delivery rates, open rates, click rates, failures)
Feature 8: Retry mechanism for failed deliveries with exponential backoff
2. Non-Functional Requirements

Scale & Performance
Scale — 1M+ notifications/min during peak (Black Friday, breaking news alerts)
CAP Theorem — Availability >> Consistency (eventual consistency for delivery status acceptable)
Latency & Reliability
Real-time delivery — High-priority notifications (OTP) delivered within 5-10s delay for transactional notifications acceptable
Reliability — At-least-once delivery guarantee (no notification should be lost), retry failed deliveries
3. Core Entity

Entity 1: User + Client - user_id, email, phone, device_tokens[] (FCM/APNS), preferences {channels, types, do_not_disturb}
Entity 2: NotificationPreferences - user_id, channels {email: true, sms: false, push: true, inapp: true}, types {promotional: false, transactional: true, alerts: true}, do_not_disturb: false
Entity 3: NotificationContent - notification_id, user_id (or recipient_id), external_user_id, template_id, channel (EMAIL/SMS/PUSH/INAPP), payload {variables}, status (PENDING/SCHEDULED/SENT/DELIVERED/FAILED/CANCELLED), priority (high/normal/low), scheduled_at, created_at, metadata
Entity 4: Template - template_id, name, channel (EMAIL/SMS/PUSH/INAPP), subject (for email), body (with {{variable}} placeholders), variables[] (list of expected variables like {name, order_id}), version, is_active, created_at
Entity 5: DeliveryStatus - delivery_id, notification_id, channel, provider (Twilio/SendGrid/FCM/APNS), provider_message_id, status (SENT/DELIVERED/FAILED), sent_at, delivered_at, error_message, retry_count
Entity 6: Notifications_outbox - outbox_id, notification_id, event_type, payload, published (boolean), created_at (for transactional outbox pattern)
Entity 7: Notifications table - notification_id, user_id (or recipient_id for position), external_user_id, template_id, channel, payload, status, priority, scheduled_at, metadata
4. API Designing

Notification Operations
POST /api/v1/notifications — Send notification with {templateId, recipientId, variables, channels[], priority, scheduledAt}
GET /api/v1/notifications/{notificationId}/status — Get delivery status for specific notification (PENDING/SENT/DELIVERED/FAILED)
Template Management
POST /api/v1/templates — Create notification template with placeholders
GET /api/v1/templates — List all templates (paginated)
GET /api/v1/templates/{templateId}/{version} — Get specific template version
CRUD — Create, Read, Update, Delete templates
User Preferences
PUT /api/v1/preferences — Update user notification preferences {channels: {email: bool, sms: bool}, types: {promotional: bool}}
..CRUD — Create, Read, Update, Delete user preferences
5. High Level Design (HLD)

Architecture: clients (Amazon/Uber) → API Gateway & Load Balancer → Services → Databases
Template Svc → Template DB: CRUD operations on notification templates, version management
User Preference Svc → UserPref DB: Manage user preferences (channels, types, DND), cache in Redis
Notification Svc → Notification Provider (Email/InApp/SMS/Push): Core orchestrator, validates template & preferences, publishes to Kafka
Notification Evt (MQ): Message Queue (Kafka) for async notification processing, prioritized queues (critical, standard, promotional, bulk)
Reporting Svc: Tracks delivery metrics, analytics (sent, delivered, failed, open rates, click rates)
6. Deep Dive Design (Low Level - LLD)

Step 1: Notification Creation & Template Rendering
Client triggers notification: POST /api/v1/notifications with {templateId: 'order_confirmation', recipientId: 'user123', variables: {name: 'Alice', order_id: 'ORD456'}, channels: ['email', 'push'], priority: 'high'}
API Gateway validation: (1) Authentication & Authorization (JWT token, API key), (2) Rate limiting (100 req/min per client), (3) Route to Notification Svc
Notification Svc: (1) Fetch template: Template Svc read: SELECT * FROM templates WHERE template_id='order_confirmation' AND is_active=true, Template: {template_id, name: 'Order Confirmation', channel: 'EMAIL', subject: 'Order {{order_id}} confirmed', body: 'Hi {{name}}, your order {{order_id}} has been confirmed...', variables: ['name', 'order_id']}, (2) Validate variables: Check all required variables present ({name: 'Alice', order_id: 'ORD456'}), if missing → return 400 'Missing variable: name'
Fetch user preferences: User Preference Svc: Check Redis cache: GET user_pref:user123 → {channels: {email: true, sms: false, push: true}, types: {promotional: false, transactional: true}}, if cache miss → query UserPref DB → cache result (24 hour TTL), Check opt-in: if channels.email=false → skip email channel, if types.promotional=false AND notification type='promotional' → skip entirely
Render template: Replace placeholders: subject: 'Order ORD456 confirmed', body: 'Hi Alice, your order ORD456 has been confirmed...', Result: {subject, body, channel: 'EMAIL'}
Generate notification_id (UUID): notification_id = 'NOTIF789'
Step 2: Transactional Outbox Pattern & Kafka Publishing
Transactional write (Outbox pattern - critical for reliability): BEGIN TRANSACTION, (1) INSERT INTO notifications (notification_id: 'NOTIF789', user_id: 'user123', template_id, channel: 'EMAIL', payload: {subject, body, to: 'alice@example.com'}, status: 'PENDING', priority: 'high', created_at: now()), (2) INSERT INTO notifications_outbox (outbox_id, notification_id: 'NOTIF789', event_type: 'notification.created', payload: {notification_id, channel, priority, recipientId}, published: false), COMMIT (atomic - both inserts succeed or both fail)
Why Outbox pattern: Prevents lost notifications, Problem: If publish to Kafka succeeds but DB write fails → notification lost (no record), If DB write succeeds but Kafka publish fails → notification stuck (never sent), Solution: Outbox ensures if DB commit succeeded, message will EVENTUALLY be published (CDC polling)
CDC/Publisher service polls outbox: SELECT * FROM notifications_outbox WHERE published=false ORDER BY created_at LIMIT 1000 (batch processing), For each unpublished record: (1) Publish to Kafka: Determine topic by priority: high → 'notifications.critical.email', normal → 'notifications.standard.email', low → 'notifications.promotional.email', Kafka.send(topic: 'notifications.critical.email', key: notification_id, value: payload), (2) Mark published: UPDATE notifications_outbox SET published=true, published_at=now() WHERE outbox_id={id}, (3) If Kafka fails: published stays false, retry on next poll (at-least-once delivery)
Kafka topics hierarchy (prioritized queues): notifications.critical.{channel} - OTP, security alerts (processed immediately, dedicated consumers), notifications.standard.{channel} - order confirmations, shipping updates (5 min SLA), notifications.promotional.{channel} - marketing emails, newsletters (30 min SLA), notifications.bulk.{channel} - batch campaigns (low priority), notifications.retry - failed deliveries with exponential backoff
Step 3: Notification Queue Processing & Provider Routing
Notification Queue consumers (Dlvy Cons): Consumer groups subscribe to Kafka topics, Email consumers: 20 instances consume 'notifications.*.email' (critical: 10, standard: 20, promotional: 5), SMS consumers: 15 instances for 'notifications.*.sms', Push consumers: 10 instances for 'notifications.*.push'
Consumer receives message: Consumes from 'notifications.critical.email', Message: {notification_id: 'NOTIF789', channel: 'EMAIL', payload: {subject, body, to: 'alice@example.com'}, priority: 'high'}
Idempotency check (prevent duplicates): Check delivery log: SELECT COUNT(*) FROM delivery_status WHERE notification_id='NOTIF789' AND channel='EMAIL', if exists → skip (already processed), Kafka may deliver duplicate messages (at-least-once), idempotency prevents sending duplicate emails
Rate limiting (ABC - provider limits): Token bucket algorithm with Redis, Bucket key: rate_limit:email:sendgrid, Capacity: 100 tokens (emails), Refill: 100 tokens/sec (SendGrid limit), Atomic check: Lua script: check tokens >= 1 → DECR token count → proceed, else wait, Prevents overwhelming provider (Twilio 100 SMS/sec, SendGrid 50 email/sec, FCM 10K push/sec), Backpressure: If rate limited → consumer slows down, Kafka buffers messages (millions of messages capacity)
Provider routing: Based on channel: EMAIL → Email Svc Provider (SendGrid/AmazonSES), SMS → SMS Svc Provider (Twilio/MSG91), Push → inAPP Svc Provider (FCM for Android, APNS for iOS), OTP → OTP Svc (dedicated, high priority)
Step 4: Email Delivery (SendGrid/AmazonSES)
Email Svc Provider: Render final email: HTML body with CSS styling, Plain text fallback, Attachments (if any), Unsubscribe link (for promotional emails, CAN-SPAM compliance)
Send via SendGrid: POST https://api.sendgrid.com/v3/mail/send with {personalizations: [{to: [{email: 'alice@example.com'}]}], from: {email: 'noreply@company.com', name: 'Company Name'}, subject: 'Order ORD456 confirmed', content: [{type: 'text/html', value: '<html>...'}]}, SendGrid response: 202 Accepted {id: 'msg_abc123'} (async, doesn't mean delivered yet)
Update status: UPDATE notifications SET status='SENT', sent_at=now() WHERE notification_id='NOTIF789', INSERT INTO delivery_status (delivery_id, notification_id: 'NOTIF789', channel: 'EMAIL', provider: 'SendGrid', provider_message_id: 'msg_abc123', status: 'SENT', sent_at: now())
Webhooks (delivery confirmation): SendGrid sends webhooks: POST /webhooks/sendgrid with {event: 'delivered', sg_message_id: 'msg_abc123', timestamp}, Event types: delivered (email reached inbox), opened (user opened email, tracked via 1px image), clicked (user clicked link), bounced (email bounced, invalid address), spam (marked as spam), Update: UPDATE delivery_status SET status='DELIVERED', delivered_at=now() WHERE provider_message_id='msg_abc123'
Step 5: SMS Delivery (Twilio/MSG91)
SMS Svc Provider: Format message (160 chars limit for single SMS, longer messages split), Add opt-out instructions: 'Reply STOP to unsubscribe' (TCPA compliance)
Send via Twilio: POST https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Messages.json with {To: '+919876543210', From: '+12345678901', Body: 'Hi Alice, your order ORD456 has been confirmed. Track: https://track.link/ORD456'}, Twilio response: {sid: 'SM1234abcd', status: 'queued'} (Twilio queues message for delivery)
Update status: UPDATE notifications SET status='SENT', INSERT INTO delivery_status (notification_id: 'NOTIF789', channel: 'SMS', provider: 'Twilio', provider_message_id: 'SM1234abcd', status: 'SENT', sent_at: now())
Twilio webhooks: POST /webhooks/twilio with {MessageSid: 'SM1234abcd', MessageStatus: 'delivered'}, Statuses: sent (to carrier), delivered (to phone), failed (delivery failed), Update: UPDATE delivery_status SET status='DELIVERED' WHERE provider_message_id='SM1234abcd'
Step 6: Push Notification (FCM/APNS)
inAPP Svc Provider (FCM for Android, APNS for iOS): Fetch device tokens: SELECT device_tokens FROM users WHERE user_id='user123', device_tokens: ['fcm_token_android_123', 'apns_token_ios_456'] (user has multiple devices: phone, tablet)
FCM (Firebase Cloud Messaging - Android/Web): POST https://fcm.googleapis.com/v1/projects/{project_id}/messages:send with {message: {token: 'fcm_token_android_123', notification: {title: 'Order Confirmed', body: 'Your order ORD456 has been confirmed'}, data: {order_id: 'ORD456', deep_link: 'app://orders/ORD456'}, android: {priority: 'high', notification: {sound: 'default', click_action: 'OPEN_ORDER'}}}}, FCM response: {name: 'projects/.../messages/0:1234567890'} (success)
APNS (Apple Push Notification Service - iOS): POST https://api.push.apple.com/3/device/{apns_token_ios_456} with HTTP/2 headers: {apns-topic: 'com.company.app', apns-priority: 10}, Body: {aps: {alert: {title: 'Order Confirmed', body: 'Your order ORD456 has been confirmed'}, badge: 1, sound: 'default'}, order_id: 'ORD456'}, APNS response: 200 OK (success) or 410 Gone (token invalid, device uninstalled app)
Multi-device fanout: Send to all 3 tokens (Android phone, iOS tablet, web browser), User receives notification on all devices, INSERT INTO delivery_status for each device (3 records: FCM Android, APNS iOS, FCM Web)
Handling failures: Invalid token (device uninstalled app): FCM returns error: 'invalid-registration-token', Remove token: UPDATE users SET device_tokens = array_remove(device_tokens, 'fcm_token_android_123'), Retry: Don't retry for invalid tokens (permanent failure)
Step 7: OTP Delivery (High Priority)
OTP Svc (dedicated for time-sensitive notifications): Generate OTP: 6-digit code (123456), Store in Redis: SET otp:user123:login '123456' EX 300 (5 min TTL, expires after 5 minutes)
Create notification: POST /api/v1/notifications with {templateId: 'otp_login', recipientId: 'user123', variables: {otp: '123456'}, channels: ['sms'], priority: 'critical'}, Priority: 'critical' (highest priority, bypasses normal queue)
Fast-track delivery: Publish to 'notifications.critical.sms' (dedicated consumer group: 20 workers vs 10 for standard), No rate limiting for OTP (critical path, can't wait), Delivery target: <10 seconds (user waiting on login screen)
Track delivery: User enters OTP within 5 minutes, Verify: GET otp:user123:login from Redis, if matches → login success, if expired (TTL reached) → prompt resend OTP
Step 8: Retry Mechanism (Failed Deliveries)
Failure scenarios: Provider timeout (Twilio didn't respond in 10 sec), Rate limit 429 (hit provider limit, too many requests), Network error (connection refused), Invalid recipient (email bounced, phone number invalid)
Retry strategy: If temporary failure (timeout, rate limit, network error): Exponential backoff: 1st retry after 1 min, 2nd retry after 5 min, 3rd retry after 15 min, Max 3 attempts over 30 minutes, Publish to 'notifications.retry' Kafka topic with retry_count
Retry consumer: Consumes 'notifications.retry', Checks retry_count: if retry_count < 3 → attempt redelivery, if retry_count >= 3 → move to DLQ (Dead Letter Queue), DLQ: 'notifications.dlq' for manual investigation, Alert ops team for persistent failures
Permanent failures (don't retry): Invalid recipient (550 User not found for email, invalid phone number for SMS), Unsubscribed user (user opted out, honor preference), Token expired (APNS 410 Gone, device uninstalled app), Mark: UPDATE delivery_status SET status='FAILED', error_message='Invalid email address'
7. Database Schema Details

Notifications (main table)
notification_id — uuid PRIMARY KEY (unique identifier across system)
user_id / recipient_id — uuid (recipient, for position tracking)
external_user_id — varchar(255) (client's user ID, e.g., Amazon customer ID)
template_id — uuid FK → Templates
channel — enum (EMAIL, SMS, PUSH, INAPP)
payload — jsonb (rendered content: {subject, body, to, variables})
status — enum (PENDING, SCHEDULED, SENT, DELIVERED, FAILED, CANCELLED)
priority — enum (critical/high, normal, low)
scheduled_at — timestamptz (nullable, for scheduled notifications)
created_at — timestamptz
metadata — jsonb (additional data: campaign_id, tags)
Indexes — INDEX on (user_id, created_at), INDEX on (status, scheduled_at), INDEX on (template_id)
Notifications_outbox (transactional outbox pattern)
outbox_id — uuid PRIMARY KEY
notification_id — uuid FK → Notifications
event_type — varchar(50) (e.g., 'notification.created')
payload — jsonb (notification details for Kafka)
published — boolean DEFAULT false (CDC polling checks this)
published_at — timestamptz (nullable, when published to Kafka)
created_at — timestamptz
Purpose — Ensures at-least-once delivery - if DB commit succeeds, message will eventually be published to Kafka
CDC/Publisher — Polls WHERE published=false, publishes to Kafka, marks published=true
Templates
Composite PK — (template_id, version) - immutable versioning
template_id — uuid (same ID across versions)
version — int (starts at 1, increments on update)
name — varchar(255) (e.g., 'Order Confirmation Email')
channel — enum (EMAIL, SMS, PUSH, INAPP)
subject — text (for EMAIL, can contain {{variables}})
body — text (template content with {{variable}} placeholders)
variables — jsonb (array of required variables: ['name', 'order_id'])
is_active — boolean (only active templates can be used)
created_at — timestamptz
Purpose — Immutable versions - on update, create new version (audit trail, rollback capability, A/B testing)
User_preferences (UserPref DB)
Composite PK — (client_id, external_user_id) - client's user identifier
client_id — varchar(100) (e.g., 'amazon', 'uber')
external_user_id — varchar(255) (client's user ID)
channels — jsonb ({email: true, sms: false, push: true, inapp: true})
types — jsonb ({promotional: false, transactional: true, alerts: true})
do_not_disturb — boolean DEFAULT false (DND mode, block all notifications)
updated_at — timestamptz
Enforcement — Check before sending - if email:false, skip email channel; if promotional:false, skip promo notifications
Delivery_status (delivery tracking)
delivery_id — uuid PRIMARY KEY
notification_id — uuid FK → Notifications (INDEXED for quick lookup)
channel — enum (EMAIL, SMS, PUSH, INAPP)
provider — varchar(50) (SendGrid, Twilio, FCM, APNS)
provider_message_id — varchar(255) (external ID from provider, e.g., Twilio SID)
provider_response — jsonb (full response from provider for debugging)
status — enum (SENT, DELIVERED, FAILED, BOUNCED, OPENED, CLICKED)
sent_at — timestamptz
delivered_at — timestamptz (nullable)
error_message — text (nullable, failure reason)
retry_count — int DEFAULT 0 (number of retry attempts)
Indexes — INDEX on (notification_id), INDEX on (provider_message_id) for webhook lookups
Redis Cache
user_pref:{userId} — STRING (JSON) - cached user preferences, TTL 24 hours (86400 sec)
template:{templateId}:{version} — STRING (JSON) - cached templates, TTL 1 hour (3600 sec), 95% hit rate
rate_limit:{channel}:{provider} — INT - token bucket for rate limiting (e.g., rate_limit:email:sendgrid → 100 tokens)
otp:{userId}:{purpose} — STRING - OTP codes, TTL 300 sec (5 min expiry)
Kafka Topics (prioritized queues)
notifications.critical.{channel} — OTP, security alerts, fraud alerts - processed immediately, dedicated consumers (10-20 workers)
notifications.standard.{channel} — Order confirmations, shipping updates, receipts - 5 min SLA, 20-30 workers
notifications.promotional.{channel} — Marketing emails, newsletters, campaigns - 30 min SLA, 5-10 workers (rate limited)
notifications.bulk.{channel} — Batch campaigns (100K+ recipients) - low priority, rate limited
notifications.retry — Failed notifications with exponential backoff (1min, 5min, 15min)
user.preference — User preference update events - consumed by User Pref Consumer, updates cache
8. Scaling & Optimization

Technique 1: Transactional Outbox pattern - Ensures at-least-once delivery (DB + Kafka write atomic), prevents lost notifications, CDC polls outbox → publishes to Kafka → marks published
Technique 2: Prioritized Kafka topics - 4 priority levels (critical/standard/promotional/bulk), critical: OTP processed immediately (<10s), promotional: 30 min SLA, worker allocation: 20/30/10/5 for crit/std/promo/bulk
Technique 3: Rate limiting with token bucket - Redis atomic Lua script (check tokens >= 1 → DECR → proceed), provider limits: Twilio 100 SMS/sec, SendGrid 50 email/sec, prevents overwhelming providers, backpressure to Kafka
Technique 4: Template caching - Redis cache (template:{id}:{version}, 1 hour TTL), 95% hit rate, immutable versioning (create new version on update, never modify existing), enables A/B testing + rollback
Technique 5: User preference caching - Redis cache (user_pref:{userId}, 24 hour TTL), check before sending (if email:false → skip email), Kafka consumer updates cache on preference change
Technique 6: Provider failover - Multi-provider strategy (primary: SendGrid, fallback: AmazonSES for email), if SendGrid fails/rate limited → route to AmazonSES, circuit breaker pattern (if failure rate >50% → open circuit, use fallback)
Technique 7: Idempotent consumers - Check delivery_status before sending (if exists → skip), Kafka at-least-once delivery may send duplicates, prevents duplicate emails/SMS to users
Technique 8: Database partitioning - Notifications table partitioned by created_at (monthly: notifications_2026_01, notifications_2026_02), delivery_status partitioned by sent_at, old partitions archived to S3 (6 month retention)
Technique 9: Batch processing for bulk notifications - Bulk campaigns (100K+ recipients): Batch insert to notifications table (1000 records at a time), SendGrid bulk API (1000 emails per call vs 1 email per call), reduces API calls 1000×
Technique 10: Kafka consumer auto-scaling - Auto-scale based on lag (if lag > 1000 messages → add consumer instances), 100 partitions enables 100 parallel consumers, throughput scales linearly
Technique 11: Webhook processing - Async webhook handling (SendGrid/Twilio webhooks → update delivery_status), don't block provider response (respond 200 OK immediately, process later), batched DB updates (update 100 records at once)
Technique 12: Reporting aggregation - Real-time: Redis counters (INCR sent_count:{date}, HINCRBY stats:{template_id} delivered 1), Batch: Hourly aggregation (Spark/Flink): SELECT template_id, COUNT(*) FROM delivery_status GROUP BY template_id, Store in InfluxDB/BigQuery for dashboards
9. Common Interview Questions

Q
How do you ensure no notification is lost and implement at-least-once delivery guarantee?
A
At-least-once delivery with Transactional Outbox pattern:

(1) Problem with dual writes: Naive approach: INSERT notification to DB, then publish to Kafka, Issues: If Kafka publish succeeds but DB write fails → notification lost (no record in DB), If DB write succeeds but Kafka publish fails → notification stuck (never sent), Network failures, service crashes can cause inconsistency.

(2) Outbox pattern solution: Single transaction: BEGIN TRANSACTION, INSERT INTO notifications (notification_id, user_id, template_id, channel, payload, status: 'PENDING', priority, created_at), INSERT INTO notifications_outbox (outbox_id, notification_id, event_type: 'notification.created', payload, published: false, created_at), COMMIT (atomic - both succeed or both fail).

(3) CDC/Publisher service: Polls outbox table: SELECT * FROM notifications_outbox WHERE published=false ORDER BY created_at LIMIT 1000 (batch processing), For each unpublished record: Determine Kafka topic by priority + channel: high + email → 'notifications.critical.email', normal + sms → 'notifications.standard.sms', Publish: Kafka.send(topic, key: notification_id, value: payload), If successful: UPDATE notifications_outbox SET published=true, published_at=now() WHERE outbox_id={id}, If Kafka fails: published stays false, retry on next poll (every 100ms), Guarantees: If DB COMMIT succeeded → message in outbox → will be published eventually (retries until success).

(4) At-least-once semantics: Outbox → Kafka: at-least-once (may publish same message twice if CDC crashes after Kafka success but before marking published), Kafka → Consumer: at-least-once (Kafka may redeliver messages on consumer restart), Idempotency: Consumer checks delivery_status: SELECT COUNT(*) WHERE notification_id={id} AND channel={channel}, if exists → skip (already sent), prevents duplicate emails/SMS to users.

(5) Exactly-once = at-least-once + idempotency: Outbox ensures message never lost, Idempotent consumers ensure message processed only once, Result: Notification sent exactly once to user, even with failures/retries.

(6) Failure handling: CDC Publisher crashes: Restarts, polls outbox again, republishes unsent messages (published=false), Kafka partition leader fails: Kafka auto-elects new leader, CDC Publisher retries automatically, Consumer crashes: Kafka redelivers message to another consumer (consumer group), idempotency check prevents duplicate send.

(7) Production example: User places order → Order Service calls Notification API, Outbox ensures order confirmation email created (DB persisted), CDC Publisher sends to Kafka within 100ms, Email consumer delivers via SendGrid within 5 sec, Even if any component crashes: notification eventually sent (retries until success). Result: Zero notification loss, at-least-once delivery guaranteed, idempotent consumers prevent duplicates, resilient to failures (services, network, Kafka, providers).

Q
How do you handle rate limiting when sending millions of notifications to prevent overwhelming external providers?
A
Rate limiting with Token Bucket algorithm and Redis:

(1) Provider limits: Twilio SMS: 100 messages/sec per account, SendGrid Email: 50 emails/sec (free tier), 10K/sec (paid), FCM Push: 10K messages/sec, APNS: No documented limit but best practice <5K/sec.

(2) Token Bucket algorithm: Concept: Bucket holds tokens (e.g., 100 tokens), each send consumes 1 token, tokens refill at fixed rate (100 tokens/sec), if bucket empty → wait until refill.

(3) Redis implementation: Bucket key: rate_limit:email:sendgrid, Capacity: 100 tokens (max burst), Refill rate: 100 tokens/sec (matches SendGrid limit), Atomic Lua script (ensures thread-safety): local key = KEYS[1], local capacity = tonumber(ARGV[1]), local refill_rate = tonumber(ARGV[2]), local tokens = redis.call('GET', key) or capacity, local now = redis.call('TIME'), if tokens >= 1 then redis.call('DECR', key), return 1 (proceed), else return 0 (rate limited, wait), end, redis.call('EXPIRE', key, 10) (reset bucket after 10 sec idle).

(4) Consumer flow: Consumer receives notification from Kafka, Before sending: Check rate limit: result = redis.eval(lua_script, 'rate_limit:email:sendgrid', 100, 100), if result = 1 (tokens available): Send email via SendGrid, else (rate limited): Sleep 100ms, retry (busy wait), OR push back to Kafka (better - allows other consumers to process other messages).

(5) Backpressure to Kafka: If all consumers rate limited (provider at max capacity), Consumers slow down (sleep/retry), Kafka buffers messages (millions of messages capacity), Message lag increases (visible in monitoring), Auto-scaling: If lag > 1000 → add more consumers (but still subject to provider rate limit), If provider limit reached: Can't send faster (bottleneck), queue grows, eventual delivery (when capacity available).

(6) Multi-provider strategy: Primary: SendGrid (50 emails/sec), Fallback: AmazonSES (50 emails/sec), Total capacity: 100 emails/sec (both providers), Load balancing: Round-robin or weighted (SendGrid 70%, SES 30%), If SendGrid rate limited: Route to SES (circuit breaker pattern).

(7) Priority handling: Critical notifications (OTP): Bypass rate limiter (can't wait, time-sensitive), OR dedicated rate bucket (critical_rate_limit:sms:twilio with higher limit), Standard/Promotional: Subject to rate limit (acceptable delay).

(8) Batching optimization: SendGrid bulk API: Send 1000 emails in single API call (vs 1 email per call), Effective rate: 50 API calls/sec × 1000 emails/call = 50K emails/sec, Reduces API overhead, increases throughput 1000×.

(9) Monitoring: Track: Tokens available (should not hit 0 frequently), Rate limit events (how often consumers wait), Provider response times (detect slowdowns), Alert: If rate limit hit > 10% of time → increase capacity (upgrade provider tier, add fallback). Result: Providers never overwhelmed (respects rate limits), backpressure prevents system overload, multi-provider increases capacity, batching optimizes throughput, critical notifications prioritized.

Q
Walk through complete notification flow from creation to delivery with all state transitions and failure handling.
A
Complete notification flow (Order Confirmation Email):

(1) Trigger: User places order, Order Service calls: POST /api/v1/notifications {templateId: 'order_confirmation', recipientId: 'user123', variables: {name: 'Alice', order_id: 'ORD456', amount: '$49.99'}, channels: ['email', 'push'], priority: 'normal'}.

(2) Notification Svc validation: Authenticate request (API key/JWT), Fetch template: SELECT * FROM templates WHERE template_id='order_confirmation' AND is_active=true, template: {subject: 'Order {{order_id}} confirmed', body: 'Hi {{name}}, your order {{order_id}} for {{amount}} has been confirmed...'}, Validate variables: Check {name, order_id, amount} present, if missing → 400 error, Fetch user preferences: Redis GET user_pref:user123 → {channels: {email: true, push: true}, types: {transactional: true}}, Check: email enabled ✓, transactional enabled ✓ (order confirmation is transactional).

(3) Render template: Replace: subject: 'Order ORD456 confirmed', body: 'Hi Alice, your order ORD456 for $49.99 has been confirmed...', Generate notification_id: 'NOTIF789'.

(4) Transactional write (Outbox pattern): BEGIN TRANSACTION, INSERT notifications: (notification_id: 'NOTIF789', user_id: 'user123', template_id, channel: 'EMAIL', payload: {subject, body, to: 'alice@example.com'}, status: 'PENDING', priority: 'normal', created_at: now()), INSERT notifications_outbox: (outbox_id, notification_id: 'NOTIF789', event_type: 'notification.created', payload, published: false), COMMIT, Response: 200 OK {notificationId: 'NOTIF789', status: 'PENDING'}.

(5) CDC/Publisher polling: SELECT * FROM notifications_outbox WHERE published=false (polls every 100ms), Finds: {outbox_id, notification_id: 'NOTIF789', payload, published: false}, Publish: Kafka.send('notifications.standard.email', key: 'NOTIF789', value: payload), Update: notifications_outbox SET published=true, published_at=now().

(6) Email Consumer: Subscribes to 'notifications.standard.email', Receives: {notification_id: 'NOTIF789', channel: 'EMAIL', payload: {subject, body, to}}, Idempotency: SELECT COUNT(*) FROM delivery_status WHERE notification_id='NOTIF789' AND channel='EMAIL', if 0 → proceed (first time), Rate limit: Check Redis token bucket: rate_limit:email:sendgrid, if tokens >= 1 → DECR, proceed, Send: POST SendGrid API {to: 'alice@example.com', subject, content: body}, Response: 202 Accepted {id: 'msg_sg123'}.

(7) Update status: UPDATE notifications SET status='SENT', sent_at=now(), INSERT delivery_status: (delivery_id, notification_id: 'NOTIF789', channel: 'EMAIL', provider: 'SendGrid', provider_message_id: 'msg_sg123', status: 'SENT', sent_at: now()).

(8) SendGrid webhook (async): Minutes later: POST /webhooks/sendgrid {event: 'delivered', sg_message_id: 'msg_sg123', email: 'alice@example.com', timestamp}, Webhook handler: UPDATE delivery_status SET status='DELIVERED', delivered_at=now() WHERE provider_message_id='msg_sg123', UPDATE notifications SET status='DELIVERED'.

(9) Push notification (parallel): Same flow for channel='PUSH', Consumer: Push consumer group, Send: FCM.send({token: user_device_token, notification: {title: 'Order Confirmed', body: 'Your order ORD456...'}}), Multi-channel: Email + Push sent independently (both succeed or fail independently).

(10) Failure scenario (temporary): SendGrid timeout (10 sec no response), Consumer: Catch exception, Publish to 'notifications.retry': {notification_id: 'NOTIF789', channel: 'EMAIL', retry_count: 1, scheduled_at: now() + 1 min}, Retry consumer: Waits 1 min, reattempts send, If fails again: retry_count: 2, scheduled_at: now() + 5 min (exponential backoff), Max 3 retries: If all fail → move to DLQ (notifications.dlq), alert ops team.

(11) Failure scenario (permanent): Email bounced (invalid address): SendGrid webhook: {event: 'bounce', reason: 'Invalid email'}, UPDATE delivery_status SET status='FAILED', error_message='Email bounced: invalid address', UPDATE notifications SET status='FAILED', Don't retry (permanent failure), Optionally: Notify sender (Order Service) that email failed.

(12) State transitions: PENDING (created, in outbox) → published to Kafka, SENT (delivered to provider, awaiting confirmation), DELIVERED (provider confirmed delivery to recipient), FAILED (permanent failure, don't retry), CANCELLED (user cancelled notification before sending). Result: Reliable delivery with state tracking, retry for temporary failures, idempotency prevents duplicates, webhooks confirm final delivery, multi-channel support, complete audit trail.

Key Interview Tips

⚠️
CRITICAL: Transactional Outbox pattern mandatory for reliable notifications. NEVER publish to Kafka without DB write in same transaction. If Kafka succeeds but DB fails → notification lost. Outbox guarantees: if DB commit succeeded, message will EVENTUALLY be published (CDC polling + retry).

⭐
Interviewers ALWAYS ask: 'How prevent notification loss?'. Answer: Outbox pattern (single transaction: INSERT notifications + INSERT outbox → COMMIT). CDC polls outbox (published=false) → publishes to Kafka → marks published=true. At-least-once delivery + idempotent consumers = exactly-once to user.

💡
Prioritized Kafka topics: notifications.critical.{channel} (OTP, <10s), notifications.standard.{channel} (orders, 5min), notifications.promotional.{channel} (marketing, 30min), notifications.bulk (campaigns). Worker allocation: 20/30/10/5. Critical bypasses rate limiting.

⭐
Rate limiting: Token bucket with Redis Lua script (atomic check + DECR). Provider limits: Twilio 100/sec, SendGrid 50/sec, FCM 10K/sec. Backpressure: consumers slow → Kafka buffers. Multi-provider failover: primary SendGrid → fallback AmazonSES if rate limited (circuit breaker).

⚠️
NEVER skip user preference checks. Must honor opt-outs (email:false → skip email), DND mode (do_not_disturb:true → skip all), notification types (promotional:false → skip marketing). Regulatory compliance: GDPR, CAN-SPAM (unsubscribe link), TCPA (SMS opt-in). Cache preferences in Redis (24h TTL).

💡
Template versioning: Immutable - create new version on update (never modify existing). Benefits: (1) Audit trail (know exact content sent), (2) A/B testing (route 50% to v1, 50% to v2), (3) Rollback (reactivate old version). Cache: template:{id}:{version} in Redis (1h TTL, 95% hit rate).

⭐
Idempotent consumers: Check delivery_status (if exists → skip). Kafka at-least-once may deliver duplicates (consumer restart, network retry). Without idempotency: user receives 5 duplicate emails (bad UX). SELECT COUNT WHERE notification_id + channel (composite uniqueness check).

system-design
notification-system
multi-channel
kafka-outbox-pattern
sendgrid
twilio
fcm
apns
rate-limiting
token-bucket
at-least-once-delivery
idempotency
template-versioning
user-preferences
Part of the "System Design Complete Course" course · Interview With Bunny

Stay Updated
Subscribe to my Channel
Connect
"Let's have a coffee together..."
FIND ME EVERYWHERE

Philosophy
How to become successful.!!
Dream life() {
while(!succeed) {
try();
}
return dreamFulfilled();
}
@Copyright?? Really?  ·  If you want, I'll clone this website too... and give you the source code