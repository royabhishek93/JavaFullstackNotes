# Notification System Design — Diagrams for New Learners
## Every diagram explained in plain English first, then drawn

---

## DIAGRAM 1: The Simplest Possible View

```
In plain English:
  Someone asks us to send a message.
  We figure out HOW to send it.
  We send it.
  We track whether it arrived.

─────────────────────────────────────────────────────────────────

  YOUR APP           OUR SYSTEM              USER'S DEVICE
  (Amazon)           (Notification           (Alice's phone/email)
                      System)

  "Send OTP         ────────────►   Figures out:        ──────►  📱 SMS arrives
   to Alice"                        - Is Alice opted in?        📧 Email arrives
                                    - Use Twilio or SendGrid?   🔔 Push arrives
                                    - OTP or marketing priority?
```

---

## DIAGRAM 2: What Happens Step by Step

```
STEP 1         STEP 2              STEP 3        STEP 4      STEP 5
─────          ──────              ──────        ──────      ──────

Amazon         API Gateway         Notification  Kafka       Consumer
sends          checks:             Service       (Queue)     Worker
POST ──────►   ✅ Valid token?  ──► checks:   ──► stores  ──► picks up
request        ✅ Under limit?     ✅ Template?    message     message
               ✅ Route it         ✅ User prefs?              │
                                   ✅ Render it                │
                                   ✅ Save to DB               ▼
                                                          Provider API
                                                          (Twilio/SendGrid/
                                                           FCM/APNS)
                                                               │
                                                               ▼
                                                          📧📱🔔 Delivered

STEP 6: Provider calls us back via WEBHOOK:
  "Message delivered to Alice at 10:32:05"
  We update our DB: status = DELIVERED ✅
```

---

## DIAGRAM 3: Template Rendering (Fill-in-the-Blanks)

```
BEFORE (stored in Template DB):
┌────────────────────────────────────────────────────────────┐
│  Template: "order_confirmation"                            │
│  Subject:  "Order {{order_id}} confirmed"                  │
│  Body:     "Hi {{name}},                                   │
│             your order {{order_id}} is confirmed.          │
│             Total: {{amount}}"                             │
└────────────────────────────────────────────────────────────┘
                           │
           Variables provided: { name: "Alice",
                                  order_id: "ORD456",
                                  amount: "₹2,499" }
                           │
                           ▼ (render/fill in)

AFTER (ready to send):
┌────────────────────────────────────────────────────────────┐
│  Subject:  "Order ORD456 confirmed"                        │
│  Body:     "Hi Alice,                                      │
│             your order ORD456 is confirmed.                │
│             Total: ₹2,499"                                 │
└────────────────────────────────────────────────────────────┘
```

---

## DIAGRAM 4: User Preferences — Should We Send or Skip?

```
Request arrives: Send order confirmation to user123 via [email, sms, push]

Fetch preferences from Redis:
┌─────────────────────────────────────────────────────────────┐
│  user123 preferences:                                       │
│  channels:  email=✅  sms=❌  push=✅  inapp=✅             │
│  types:     transactional=✅  promotional=❌  alerts=✅     │
│  do_not_disturb: false                                      │
└─────────────────────────────────────────────────────────────┘

Decision tree:
                    Request: order_confirmation (transactional)
                                    │
               ┌────────────────────┼────────────────────┐
               │                    │                    │
           EMAIL                   SMS                 PUSH
           channel=✅              channel=❌           channel=✅
           type=✅                  SKIP ❌             type=✅
               │                                         │
          ✅ SEND                                    ✅ SEND


If it was a PROMOTIONAL notification instead:
           EMAIL                   SMS                 PUSH
           channel=✅              channel=❌           channel=✅
           type=❌ (promo off)      SKIP ❌             type=❌ (promo off)
               │                                         │
           SKIP ❌                                    SKIP ❌

→ Nothing gets sent. User's choice is respected.
```

---

## DIAGRAM 5: The Outbox Pattern — Why We Never Lose Messages

```
THE PROBLEM WITHOUT OUTBOX:
────────────────────────────
  Notification Service
       │
       ├─ Step 1: Write to DB         ✅ (success)
       │
       │   *** CRASH / POWER CUT ***  💥
       │
       └─ Step 2: Publish to Kafka   NEVER HAPPENS ❌

  Result: DB shows notification as PENDING forever.
          No consumer ever picks it up.
          Alice never gets her email.
          No error, no log. Silent loss. 😱


THE SOLUTION WITH OUTBOX:
──────────────────────────
  Notification Service
       │
       └─ ONE ATOMIC TRANSACTION:
            ┌──────────────────────────────────────┐
            │  BEGIN TRANSACTION                   │
            │    INSERT notifications (PENDING)    │
            │    INSERT notifications_outbox       │
            │      (published = false)             │
            │  COMMIT                              │ ← both or neither
            └──────────────────────────────────────┘

  Background Publisher (polls every 100ms):
       │
       ├─ SELECT * FROM outbox WHERE published=false
       │
       ├─ Publish each to Kafka
       │
       └─ UPDATE outbox SET published=true

  Even if publisher crashes:
  → outbox rows still have published=false
  → publisher restarts, finds them, publishes
  → message is NEVER lost ✅


VISUAL TIMELINE:
────────────────
  t=0s:  Transaction commits (both rows written)
  t=0.1s: Publisher picks up outbox row
  t=0.2s: Publishes to Kafka, marks published=true
  t=0.5s: Consumer picks up from Kafka
  t=0.8s: SendGrid called
  t=1.2s: Email sent to Alice ✅
```

---

## DIAGRAM 6: Kafka Priority Queues

```
ANALOGY: Emergency Room Triage
──────────────────────────────
  Heart attack patient   → Treated in 2 minutes    (CRITICAL)
  Broken arm patient     → Treated in 30 minutes   (STANDARD)
  Routine checkup        → Treated in 2 hours      (PROMOTIONAL)
  Insurance paperwork    → Processed tomorrow      (BULK)

KAFKA TOPICS = the different waiting rooms:
──────────────────────────────────────────

  notifications.critical.sms    ◄── OTP, security alerts
  ┌────────────────────────────┐     20 consumers watching
  │ msg1 │ msg2 │ msg3 │       │ ──► SMS delivered in <10s ⚡
  └────────────────────────────┘

  notifications.standard.email  ◄── Order confirmations
  ┌──────────────────────────────────┐
  │ msg1 │ msg2 │ ... │ msg500 │     │ ──► Email in 5-10s
  └──────────────────────────────────┘ 10 consumers

  notifications.promotional.email ◄── Marketing campaigns
  ┌───────────────────────────────────────────────────────┐
  │ msg1 │ msg2 │ ... │ ... │ ... │ ... │ msg50000 │      │
  └───────────────────────────────────────────────────────┘
  5 consumers → 30 min to process all (acceptable)

  notifications.retry           ◄── Failed deliveries
  ┌──────────────────────────────────┐
  │ retry1 │ retry2 │               │ ──► Retried after delay
  └──────────────────────────────────┘ 3 consumers

KEY INSIGHT:
  OTP queue has 20 consumers → fast even when busy
  Marketing queue has 5 consumers → slow is fine
  Both use the SAME Kafka cluster, different topics
  OTP never waits behind marketing ✅
```

---

## DIAGRAM 7: Rate Limiting (Token Bucket)

```
ANALOGY: ATM withdrawal limit
  ATM allows ₹10,000/day.
  You can't withdraw ₹15,000 even if you have the balance.
  Provider rate limits work the same way.

  SendGrid: max 50 emails/second
  Twilio:   max 100 SMS/second
  FCM:      max 10,000 push/second

TOKEN BUCKET (how we enforce this):
────────────────────────────────────

  BUCKET for email:sendgrid
  ┌──────────────────────────────┐
  │ capacity: 50 tokens          │  ← max you can burst
  │ refill: 50 per second        │  ← long-term rate
  │ current: 47 tokens           │
  └──────────────────────────────┘

  Send 1 email → take 1 token (47 → 46)
  Send 1 email → take 1 token (46 → 45)
  ...
  Send 47th email → 0 tokens left
  Send 48th email → NO TOKENS → WAIT
  ...1 second passes → 50 tokens refilled
  Send 48th email → 49 tokens remaining ✅

  Stored in Redis (atomic Lua script):
  ┌───────────────────────────────────────────────┐
  │  key = "rate_limit:email:sendgrid"            │
  │  IF tokens >= 1:                              │
  │    DECR tokens by 1                           │
  │    return "proceed"                           │
  │  ELSE:                                        │
  │    return "wait"  (consumer slows down)       │
  └───────────────────────────────────────────────┘
```

---

## DIAGRAM 8: Email Delivery Flow (With SendGrid)

```
Consumer Worker
     │
     ├─ [1] Check idempotency:
     │       SELECT * FROM delivery_status
     │       WHERE notification_id='NOTIF789' AND channel='EMAIL'
     │       → 0 rows found → proceed (not already sent)
     │
     ├─ [2] Check rate limit → token available → proceed
     │
     ├─ [3] Call SendGrid API:
     │       POST https://api.sendgrid.com/v3/mail/send
     │       {
     │         to:      "alice@example.com",
     │         from:    "noreply@amazon.com",
     │         subject: "Order ORD456 confirmed",
     │         html:    "<h1>Hi Alice...</h1>"
     │       }
     │       ← Response 202: { id: "msg_abc123" }
     │         (202 = "I received it, will deliver soon")
     │
     ├─ [4] Update DB:
     │       notifications.status = 'SENT'
     │       delivery_status: { provider_message_id: 'msg_abc123',
     │                           status: 'SENT', sent_at: now() }
     │
     └─ [5] WAIT for webhook...

  ──── a few seconds later ────

  SendGrid → POST /webhooks/sendgrid
  { event: "delivered",
    sg_message_id: "msg_abc123",
    timestamp: 1721234567 }

  Our webhook handler:
  UPDATE delivery_status SET status='DELIVERED',
    delivered_at = from_timestamp(1721234567)
  WHERE provider_message_id = 'msg_abc123' ✅
```

---

## DIAGRAM 9: Push Notifications to Multiple Devices

```
Alice has 3 devices:
┌─────────────────────────────────────────────────────────┐
│  users table:                                           │
│  user_id: "alice123"                                    │
│  device_tokens: [                                       │
│    "fcm_token_abc"   ← Android phone                   │
│    "apns_token_xyz"  ← iPhone                          │
│    "fcm_token_web"   ← Chrome browser                  │
│  ]                                                      │
└─────────────────────────────────────────────────────────┘
                    │
          Send push to ALL 3 tokens
                    │
        ┌───────────┼────────────┐
        │           │            │
        ▼           ▼            ▼
  FCM API       APNS API     FCM API
  (Android)     (iPhone)     (Web)
        │           │            │
   ✅ Delivered  ✅ Delivered  ❌ Token invalid
   (phone got    (phone got    (Alice uninstalled
    notification) notification) Chrome extension)
        │                        │
        │                  Remove invalid token:
        │                  UPDATE users
        │                  SET device_tokens =
        │                    array_remove(device_tokens,
        │                    "fcm_token_web")
        │
  delivery_status: 3 rows (one per device/attempt)
```

---

## DIAGRAM 10: Retry with Exponential Backoff

```
SCENARIO: Twilio is temporarily overloaded (HTTP 429 Too Many Requests)

TIMELINE:
─────────────────────────────────────────────────────────────────

  t=0:00   Consumer tries to send SMS
           Twilio responds: 429 Too Many Requests ❌

  t=0:00   Publish to notifications.retry
           { notification_id: NOTIF789, retry_count: 1 }

  t=1:00   Retry consumer picks up (after 1 minute wait)
           Try Twilio again... 429 again ❌
           retry_count → 2
           Publish back to retry queue

  t=6:00   Retry consumer picks up (after 5 more minutes)
           Try Twilio again... success! ✅
           SMS delivered to Alice.
           delivery_status.status = 'DELIVERED'

IF ALL 3 RETRIES FAIL:
─────────────────────────────────────────────────────────────────

  t=0:00   Attempt 1 fails (retry_count=1)
  t=1:00   Attempt 2 fails (retry_count=2)
  t=6:00   Attempt 3 fails (retry_count=3)

           retry_count >= 3 → move to DLQ

  notifications.dlq (Dead Letter Queue):
  ┌───────────────────────────────────────────────────────┐
  │  notification_id: NOTIF789                            │
  │  channel: SMS                                         │
  │  error: "Twilio 500 Internal Server Error"            │
  │  retry_count: 3                                       │
  │  last_attempt: 2024-01-15 10:45:00                    │
  └───────────────────────────────────────────────────────┘
  Ops team is alerted → investigates → replays if needed

WHY EXPONENTIAL BACKOFF (1m, 5m, 15m)?
  If Twilio is overloaded and you hammer it every second:
  → You make it worse (more load on already-overloaded service)
  Waiting progressively longer:
  → Gives Twilio time to recover
  → Spreads your retry load over time
  → Standard practice across all distributed systems
```

---

## DIAGRAM 11: OTP Fast Path vs Normal Path

```
NORMAL ORDER CONFIRMATION:
──────────────────────────
  API → Notification Svc
      → Outbox → CDC Publisher
      → Kafka: notifications.standard.email
      → 10 consumers (shared with all standard emails)
      → Maybe 1000 emails queued before yours
      → Wait 5-30 seconds
      → SendGrid
      → 📧 Email arrives

OTP LOGIN CODE:
───────────────
  API → Notification Svc (priority: "critical")
      → Outbox → CDC Publisher
      → Kafka: notifications.critical.sms  ← DIFFERENT TOPIC
      → 20 dedicated consumers (for critical only)
      → 0 marketing emails ahead of you
      → No rate limiting (critical path)
      → Twilio immediately
      → 📱 SMS arrives in <10 seconds

COMPARISON:
                    OTP         Order Email
  Kafka topic:      critical    standard
  Consumers:        20          10
  Rate limiting:    NONE        Yes (50/sec)
  Target time:      <10s        5-30s
  Can it wait?      NO          Yes


REDIS OTP STORAGE:
  ┌────────────────────────────────────────────────────┐
  │  Key:   "otp:alice123:login"                       │
  │  Value: "382910"                                   │
  │  TTL:   300 seconds (5 minutes, auto-deletes)      │
  └────────────────────────────────────────────────────┘

  User enters "382910" in app:
    GET otp:alice123:login → "382910" → matches ✅ → login!
    GET otp:alice123:login → nil (expired) → resend OTP
    GET otp:alice123:login → "382910" but user typed "111111" → wrong OTP
```

---

## DIAGRAM 12: Full System — One Notification's Journey

```
"Alice just placed an order on Amazon. Send her a confirmation."

  AMAZON SERVER
       │
       │  POST /api/v1/notifications
       │  { templateId: "order_conf", recipientId: "alice123",
       │    variables: {name:"Alice", order_id:"ORD456"},
       │    channels: ["email","push"], priority: "high" }
       ▼
  API GATEWAY
  ┌─────────────────────────────────────────┐
  │  ✅ JWT token valid (Amazon is allowed) │
  │  ✅ Under rate limit (50/min)           │
  │  → Route to Notification Service       │
  └─────────────────────────────────────────┘
       │
       ▼
  NOTIFICATION SERVICE
  ┌─────────────────────────────────────────────────────────────┐
  │  1. Fetch template "order_conf" from Template DB            │
  │     Subject: "Order {{order_id}} confirmed"                 │
  │     Body: "Hi {{name}}, your order {{order_id}}..."         │
  │                                                             │
  │  2. Get Alice's prefs from Redis:                           │
  │     email=✅ sms=❌ push=✅ promotional=❌ transactional=✅  │
  │     → Will send: email ✅, push ✅  (not sms, not promo)   │
  │                                                             │
  │  3. Render template:                                        │
  │     "Order ORD456 confirmed" + "Hi Alice, your order..."   │
  │                                                             │
  │  4. Atomic transaction:                                     │
  │     INSERT notifications (id=NOTIF789, status=PENDING)     │
  │     INSERT outbox (notification_id=NOTIF789, pub=false)    │
  └─────────────────────────────────────────────────────────────┘
       │
       ▼
  CDC PUBLISHER (polls every 100ms)
       │  Found outbox row: published=false
       │  Publishes to Kafka: notifications.standard.email
       │  Publishes to Kafka: notifications.standard.push
       │  Marks outbox: published=true
       │
       ├──────────────────────────────────────────┐
       ▼                                          ▼
  EMAIL CONSUMER                            PUSH CONSUMER
  ┌────────────────────────────┐       ┌────────────────────────────┐
  │ Idempotency check: not sent│       │ Fetch device tokens:        │
  │ Rate limit: token avail.   │       │ ["fcm_abc", "apns_xyz"]     │
  │ Call SendGrid API          │       │ Call FCM (Android)          │
  │ Response: msg_abc123       │       │ Call APNS (iPhone)          │
  │ Update DB: status=SENT     │       │ Update DB: status=SENT×2   │
  └────────────────────────────┘       └────────────────────────────┘
       │                                          │
       ▼ (2 seconds later)                       ▼ (1 second later)
  SENDGRID WEBHOOK                          FCM/APNS RESPONSE
  POST /webhooks/sendgrid                   200 OK = delivered
  { event: "delivered",
    id: "msg_abc123" }

       │                                          │
       ▼                                          ▼
  UPDATE delivery_status                 UPDATE delivery_status
  SET status='DELIVERED' ✅              SET status='DELIVERED' ✅

  FINAL STATE:
  Alice's email inbox: 📧 "Order ORD456 confirmed" ✅
  Alice's Android:     🔔 "Order Confirmed" push notification ✅
  Alice's iPhone:      🔔 "Order Confirmed" push notification ✅
```

---

## Quick Reference — Databases Used

```
┌─────────────────┬────────────────────┬───────────────────────────┐
│  Database        │  What's stored      │  Why this database?       │
├─────────────────┼────────────────────┼───────────────────────────┤
│  PostgreSQL      │  notifications      │  ACID transactions for    │
│  (main DB)       │  outbox             │  Outbox pattern safety    │
│                  │  delivery_status    │                           │
│                  │  templates          │                           │
├─────────────────┼────────────────────┼───────────────────────────┤
│  PostgreSQL      │  user preferences   │  Relational, complex      │
│  (UserPref DB)   │  (per channel/type) │  queries (joins)          │
├─────────────────┼────────────────────┼───────────────────────────┤
│  Redis           │  Preference cache   │  <1ms reads, reduces      │
│  (Cache)         │  OTP codes (TTL)    │  DB load by 10x           │
│                  │  Rate limit tokens  │  Auto-expiry for OTPs     │
│                  │  Idempotency keys   │                           │
├─────────────────┼────────────────────┼───────────────────────────┤
│  Kafka           │  Notification msgs  │  Buffer between fast      │
│  (Message Queue) │  (prioritized)      │  producers and slow       │
│                  │  Retry queue        │  providers                │
│                  │  DLQ               │  Replay, durability        │
└─────────────────┴────────────────────┴───────────────────────────┘
```

---

## Key Vocabulary Cheat Sheet

```
Term                  What it means (plain English)
──────────────────────────────────────────────────────────────────
Template              Email/SMS skeleton with {{placeholders}}
Render                Fill in the placeholders with real values
Outbox Pattern        Write DB + queue message in one transaction
CDC Publisher         Background job that reads outbox → Kafka
Kafka                 Message queue — stores msgs until consumed
Consumer              Worker that reads from Kafka and acts on it
Token Bucket          Rate limiting algorithm — like a bucket of tokens
Exponential Backoff   Wait 1m, then 5m, then 15m before retrying
Dead Letter Queue      Where messages go after too many retry failures
Idempotency           "Already processed? Skip it" — prevents duplicates
Webhook               Provider calls YOUR API to give you an update
FCM                   Firebase Cloud Messaging — push to Android/Web
APNS                  Apple Push Notification Service — push to iPhone
TTL                   Time To Live — auto-delete after X seconds (Redis)
At-least-once         Guarantee: may send twice, but NEVER zero times
```
