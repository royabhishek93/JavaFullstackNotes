# Notification System Design — Senior Architect Interview Script
### 15 Years Experience Level | Conversational Walk-Through

---

> **How to use this:** Read every block in *italics* out loud — that's your spoken answer.
> Diagrams are drawn on the whiteboard as you speak. Cross-questions test if the interviewer probes deeper.

---

## OPENING — First 60 Seconds (Set the Stage)

*"Before I jump into the design, let me make sure we're aligned on scope. A notification system is infrastructure — it's a platform that other teams at the company send through. Think of it as an internal AWS SNS but with company-specific business logic baked in.*

*The hard part isn't sending one email. The hard part is sending 1 million notifications per minute on Black Friday, making sure every OTP lands in under 10 seconds, never duplicating a notification when Kafka replays a message, and still honoring a user's 'do not disturb' preferences at 2am.*

*So the three principles I'll design around are: no notification loss, no duplicate delivery, and strict priority ordering. Let me draw the big picture first."*

---

## 1. BIG PICTURE — Architecture Diagram

> **Draw this first, always. Top-level, left to right.**

```
╔══════════════════════════════════════════════════════════════════════════════════════════════╗
║                        NOTIFICATION PLATFORM — BIG PICTURE (HLD)                             ║
╠══════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                              ║
║   PRODUCERS (Clients)                  PLATFORM CORE                    DELIVERY LAYER       ║
║  ┌───────────────┐                                                                           ║
║  │  Amazon App   │──┐                                                                        ║
║  │  (order svc)  │  │    ┌──────────┐    ┌──────────────────┐                                 ║
║  └───────────────┘  │    │   API    │    │                  │   ┌────────────────────────┐   ║
║  ┌───────────────┐  ├───▶│ Gateway  │──▶ │  Notification    │──▶│    Kafka Message Bus   │   ║
║  │   Uber App    │  │    │  + LB    │    │    Service       │   │  (6 prioritized topics)│   ║
║  │  (trip svc)   │──┘    └──────────┘    │  (Orchestrator)  │   └──────────┬─────────────┘  ║
║  └───────────────┘         Auth/RL       │                  │              │                 ║
║  ┌───────────────┐                       │  1. Fetch tmpl   │              │                 ║
║  │  Internal     │──────────────────────▶│  2. Check prefs  │    ┌─────────▼──────────────┐ ║
║  │  Services     │                       │  3. Render       │    │   Delivery Consumers   │ ║
║  └───────────────┘                       │  4. Outbox write │    │  (idempotent workers)  │ ║
║                                          └──────────────────┘    └─────────┬──────────────┘ ║
║                                                  │                          │                ║
║  SUPPORT SERVICES                                │               ┌──────────▼─────────────┐  ║
║  ┌──────────────────┐  ┌────────────────────┐    │               │    Provider Gateway    │  ║
║  │  Template Svc    │  │  User Preference   │◀───┘               │  + Rate Limiter (TB)   │  ║
║  │  (versioned)     │  │  Svc + Redis cache │                    └──────────┬─────────────┘  ║
║  └──────────────────┘  └────────────────────┘                               │                ║
║                                                              ┌──────────────┼──────────────┐  ║
║  DATABASES                                                   ▼              ▼              ▼  ║
║  ┌──────────┐ ┌──────────┐ ┌──────────┐            ┌─────────────┐ ┌──────────┐ ┌───────┐  ║
║  │  Notif   │ │ Template │ │ UserPref │            │ SendGrid /  │ │ Twilio / │ │  FCM  │  ║
║  │    DB    │ │    DB    │ │    DB    │            │  SES Email  │ │  MSG91   │ │  APNS │  ║
║  └──────────┘ └──────────┘ └──────────┘            └─────────────┘ └──────────┘ └───────┘  ║
║                                                                                              ║
║  OBSERVABILITY                                                                               ║
║  ┌───────────────────────────────────────────────────────────────────┐                      ║
║  │  Reporting Svc → Redis counters + Spark batch → InfluxDB/Grafana  │                      ║
║  └───────────────────────────────────────────────────────────────────┘                      ║
╚══════════════════════════════════════════════════════════════════════════════════════════════╝
```

> **HOW TO EXPLAIN THE 4 STEPS TO AN INTERVIEWER:**
> *"The Notification Service is the orchestrator — it does four things in a fixed order before any message leaves the system.*
> *First, it fetches the template — message text is never hardcoded in the service, it's stored in a Template DB so marketing can update wording without a code deploy.*
> *Second, it checks user preferences — did this user opt out of SMS? Do they have quiet hours set? I have to check this on every notification, because skipping it is a GDPR violation — you'd be sending to people who explicitly said no.*
> *Third, it renders — it takes the template `'Hi {name}, your order #{id}'` and fills in the actual values to produce the final personalized message.*
> *Fourth, the outbox write — this is the critical one. Before pushing to Kafka, I write the rendered message to the database first. If the service crashes between render and Kafka push, the message is not lost — a CDC process will pick it up from the DB and re-publish it. This guarantees at-least-once delivery."*

> **HOW TO EXPLAIN THE 3 DATABASES TO AN INTERVIEWER:**
> *"I'm separating these into three databases intentionally — each has a completely different access pattern.*
> *The Notification DB is my audit log — every notification sent, its status, timestamp, and channel. I need this for debugging ('why didn't this user get their OTP?') and for compliance reporting.*
> *The Template DB stores message templates. It's written to rarely — only when product or marketing updates copy — but read on literally every notification. By isolating it I can cache it aggressively and scale it independently.*
> *The UserPref DB stores opt-in/opt-out status per user per channel. This is legally non-negotiable — GDPR requires I honor unsubscribes. I keep it separate because it's read on every single notification but updated very rarely — it's a perfect candidate for Redis caching on top of the DB, which is exactly what the User Preference Service does."*

### Scenario: Why This Architecture?

*"The interviewer will ask: why not just call SendGrid directly from the Order Service? Let me tell you why that's a trap.*

*If Order Service calls SendGrid directly:*
*- If SendGrid is down, the order fails. That's wrong.*
*- If Order Service crashes mid-send, did the email go? You don't know.*
*- If we get 100,000 orders in a minute, we'll hit SendGrid's rate limit and start dropping.*
*- You can't prioritize an OTP over a newsletter.*

*So we decouple with Kafka. The Order Service just fires-and-forgets to the Notification API. The API writes to DB and Kafka atomically — that's the outbox pattern. Then async workers process it at whatever rate the provider allows. The Order Service gets a 200 OK and moves on. Notification delivery is now a separate concern, isolated, scalable, and observable."*

> **HOW THE OUTBOX PATTERN ACTUALLY WORKS (Common Confusion):**
> A common mistake: "Order Service writes to Kafka AND the outbox table at the same time." That's wrong — that's the exact problem outbox solves.
>
> **Without outbox (broken):**
> 1. Order Service writes order to DB ✓
> 2. Order Service writes to Kafka ✓ or ✗ — if this crashes, the notification is lost forever
>
> Two separate operations = two failure points. No guarantee both succeed.
>
> **With outbox (correct):**
> 1. Order Service does ONE single DB transaction:
>    - Writes order to `orders` table
>    - Writes `{templateId, recipientId, status: PENDING}` to `outbox` table
>    - Both commit atomically — either both land, or neither does
> 2. Order Service never touches Kafka directly
> 3. A CDC process (e.g. Debezium) watches the `outbox` table for new rows and publishes to Kafka
> 4. Once Kafka confirms receipt, the outbox row is marked `PUBLISHED`
>
> **Key insight:** You replace "DB write + Kafka write" (two systems, two failure points) with just "DB write" (one system, one transaction). The CDC bridge is a separate reliable process — if it crashes, it resumes from where it left off. Nothing is ever lost.
>
> The Order Service and Kafka are never written to simultaneously — the outbox table is the handoff point between them.

> **WHY KAFKA / ASYNC QUEUE EXISTS? (Beginner Explanation)**
> Think of a restaurant. The waiter takes your order, drops a ticket to the kitchen printer, and immediately walks away to serve the next table. He does NOT stand at the kitchen window waiting for your food to be cooked.
> Kafka is that ticket printer. The Order Service drops a "please send notification" ticket and walks away — it gets its 200 OK in milliseconds. The kitchen (Delivery Consumer) cooks the notification at its own pace.
> Without this: Order Service would have to wait for SendGrid to respond before returning "Order Confirmed" to the customer. A 2-second SendGrid hiccup on Black Friday freezes every checkout. The notification system becomes a bottleneck for the entire business.
> With Kafka: two separate concerns, each running at their own speed, completely isolated. SendGrid being slow does not slow down checkouts.

### Cross Questions After This Diagram

| Question | Strong Answer |
|---|---|
| Why not use AWS SNS directly? | SNS has no template management, no user preference checks, no retry with idempotency, no priority queues. It's a building block, not a platform. |
| Why a dedicated Notification Service vs each team integrating directly? | Centralized platform = single source of compliance (GDPR opt-outs), single rate limiter, single retry logic, single observability. Avoids every team reinventing this. |
| What if the Notification Service itself crashes? | Stateless service behind load balancer — restart in seconds. Outbox in DB survives — CDC picks up where it left off. Kafka retains messages up to retention period. |
| How do you handle multi-tenancy? | Each client (`amazon`, `uber`) has its own API key, rate limit, and namespace in user preferences. |

---

## 2. DETAILED LLD — Internal Architecture

> **Draw layer by layer. This is the diagram that wins or loses the interview.**

```
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                    NOTIFICATION SERVICE — LLD (Internal Flow)                        ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║  ┌────────────────────────────────────────────────────────────────────────────────┐  ║
║  │                    LAYER 1 — REQUEST ENTRY                                     │  ║
║  │                                                                                │  ║
║  │  POST /api/v1/notifications                                                    │  ║
║  │  { templateId, recipientId, variables, channels[], priority, scheduledAt? }    │  ║
║  │         │                                                                      │  ║
║  │         ▼                                                                      │  ║
║  │  API Gateway: JWT auth → rate limit 100 req/min/client → route to Notif Svc   │  ║
║  └────────────────────────────────────────────────────────────────────────────────┘  ║
║                         │                                                            ║
║                         ▼                                                            ║
║  ┌────────────────────────────────────────────────────────────────────────────────┐  ║
║  │                    LAYER 2 — NOTIFICATION SERVICE (6 Steps)                    │  ║
║  │                                                                                │  ║
║  │  Step 1: Fetch Template                                                        │  ║
║  │          Redis GET template:{id}:{version} (1h TTL, 95% hit)                  │  ║
║  │          Cache miss → SELECT FROM templates WHERE id=X AND is_active=true      │  ║
║  │                                                                                │  ║
║  │  Step 2: Validate Variables                                                    │  ║
║  │          Check all {{placeholders}} present → 400 if missing                  │  ║
║  │                                                                                │  ║
║  │  Step 3: Fetch User Preferences                                                │  ║
║  │          Redis GET user_pref:{userId} (24h TTL)                               │  ║
║  │          Cache miss → SELECT FROM user_preferences WHERE userId=X              │  ║
║  │                                                                                │  ║
║  │  Step 4: Check Opt-in (BEFORE publishing to Kafka)                             │  ║
║  │          channels.email=false  → skip email                                   │  ║
║  │          types.promotional=false → skip promo                                 │  ║
║  │          do_not_disturb=true   → skip ALL channels                            │  ║
║  │                                                                                │  ║
║  │  Step 5: Render Template                                                       │  ║
║  │          Replace {{name}} → "Alice", {{order_id}} → "ORD456"                  │  ║
║  │                                                                                │  ║
║  │  Step 6: Outbox Transaction (ATOMIC)                                           │  ║
║  │          BEGIN TRANSACTION                                                     │  ║
║  │            INSERT notifications (status=PENDING, channel, priority)           │  ║
║  │            INSERT notifications_outbox (published=false)                      │  ║
║  │          COMMIT ← both or neither                                             │  ║
║  │          Return: 200 OK { notificationId, status: 'PENDING' }                 │  ║
║  └────────────────────────────────────────────────────────────────────────────────┘  ║
║                         │                                                            ║
║                         ▼  (CDC polls every 100ms)                                  ║
║  ┌────────────────────────────────────────────────────────────────────────────────┐  ║
║  │                    LAYER 3 — KAFKA TOPICS (Priority Lanes)                     │  ║
║  │                                                                                │  ║
║  │  notifications.critical.{channel}     ← OTP, fraud, security    20 workers   │  ║
║  │  notifications.standard.{channel}     ← orders, shipping         30 workers   │  ║
║  │  notifications.promotional.{channel}  ← marketing, newsletters   10 workers   │  ║
║  │  notifications.bulk.{channel}         ← mass campaigns            5 workers   │  ║
║  │  notifications.retry                  ← failed, exponential backoff            │  ║
║  │  notifications.dlq                    ← 3 retries exhausted → ops alert       │  ║
║  └────────────────────────────────────────────────────────────────────────────────┘  ║
║                         │                                                            ║
║                         ▼                                                            ║
║  ┌────────────────────────────────────────────────────────────────────────────────┐  ║
║  │                    LAYER 4 — DELIVERY CONSUMER (Per Channel)                   │  ║
║  │                                                                                │  ║
║  │  ① Idempotency check:                                                         │  ║
║  │    SELECT COUNT(*) FROM delivery_status WHERE notif_id=X AND channel=Y        │  ║
║  │    if > 0 → SKIP (Kafka at-least-once may redeliver)                           │  ║
║  │                                                                                │  ║
║  │  ② Rate limiter check (Token Bucket in Redis, atomic Lua):                    │  ║
║  │    rate_limit:{channel}:{provider} → tokens > 0? DECR : backpressure          │  ║
║  │    Critical OTP → separate high-capacity bucket                               │  ║
║  │                                                                                │  ║
║  │  ③ Route to provider:                                                         │  ║
║  │    EMAIL  → SendGrid (primary) / AmazonSES (fallback, circuit breaker)        │  ║
║  │    SMS    → Twilio (primary) / MSG91 (fallback)                               │  ║
║  │    PUSH   → FCM (Android/Web) / APNS (iOS)                                    │  ║
║  │    INAPP  → WebSocket push / long-poll / Redis pub-sub                        │  ║
║  │                                                                                │  ║
║  │  ④ Write delivery record:                                                     │  ║
║  │    INSERT delivery_status (notif_id, channel, provider, status=SENT)          │  ║
║  └────────────────────────────────────────────────────────────────────────────────┘  ║
║                         │                                                            ║
║                         ▼  (async webhook from provider)                            ║
║  ┌────────────────────────────────────────────────────────────────────────────────┐  ║
║  │                    LAYER 5 — DELIVERY CONFIRMATION                             │  ║
║  │                                                                                │  ║
║  │  Provider webhook → POST /webhooks/{provider}                                 │  ║
║  │  Respond 200 OK immediately (never block webhook)                             │  ║
║  │  Queue event → batch update delivery_status SET status=DELIVERED              │  ║
║  │                                                                                │  ║
║  │  Failure path:                                                                 │  ║
║  │  Temporary (timeout, 429) → retry topic → 1m → 5m → 15m → DLQ               │  ║
║  │  Permanent (bounce, invalid token, 410 Gone) → status=FAILED, no retry        │  ║
║  └────────────────────────────────────────────────────────────────────────────────┘  ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
```

### Scenario: Why This Layer Breakdown?

*"Each layer solves a specific failure mode.*

*Layer 2 is the intelligence layer — it decides IF we should send, WHAT to send, and in what form. That logic has to live somewhere, and putting it in the service before we touch any queues keeps the rest of the system dumb-fast.*

*Layer 3 — the Kafka priority lanes — solves the OTP problem. Without priority queues, a Black Friday campaign of 10 million promotional emails could delay a customer's login OTP by 20 minutes. That's a P0 incident. With separate Kafka topics and dedicated worker pools, OTP is completely isolated. A 2am Black Friday email backlog doesn't touch the OTP lane at all.*

*Layer 4 solves the idempotency problem. Kafka guarantees at-least-once delivery. If a consumer crashes mid-processing, Kafka replays the message. Without the idempotency check, the user gets two emails. With the delivery_status check, we detect the duplicate and skip it silently."*

> **WHY NOTIFICATION TEMPLATES EXIST? (Beginner Explanation)**
> Imagine Zomato stores "Hi {{name}}, your order {{order_id}} is on the way!" as a reusable blueprint in a database, separate from all the code.
> Without templates: every team that wants to send a notification writes its own message text inside their own code. Marketing wants to fix a typo in the subject line? Every team has to find the string in their codebase and redeploy.
> With templates: one team owns the message content. Any other team triggers a send by passing just the variable values — name, order ID, amount. Marketing updates the wording via a PUT API call. No deploy needed. No code change.
> Versioning (template_id + version number) means in-flight notifications never silently change mid-send — an order confirmation already in Kafka keeps using version 1, even after marketing publishes version 2.

> **WHY USER PREFERENCE / OPT-OUT STORE EXISTS? (Beginner Explanation)**
> Think of it as a Do Not Disturb sign on a hotel door. Before knocking (sending a notification), the system checks if the sign is up.
> Without this: a user who opts out of promotional emails at 8:00pm still receives the 8:01pm campaign — because the Order Service that fired the notification has no idea about the opt-out.
> With this: one central store that every notification type checks before publishing to Kafka (Step 4 in Layer 2). "Do Not Disturb between 10pm–8am" is honored by every channel automatically. Legal compliance — GDPR unsubscribes, SMS STOP replies — are enforced from this single store universally.

> **WHY RATE LIMITING PER PROVIDER EXISTS? (Beginner Explanation)**
> Think of a tap that controls water flow into a bucket. SendGrid only allows 10,000 emails per second. Open the tap too wide and SendGrid replies HTTP 429 (Too Many Requests) — your notifications are rejected and lost.
> The Token Bucket works like a jar of coins: it starts full (say 10,000 coins), one coin is spent per email sent, and coins refill at the provider's allowed rate per second. If the jar is empty, the consumer waits — instead of hammering the provider.
> Without rate limiting: when 30 consumer pods restart after a 2-hour backlog, they all fire simultaneously at SendGrid at 3am. SendGrid rate-limits or bans the account. Thousands of notifications are dropped.
> The rate limit bucket is stored atomically in Redis (Lua script) so all consumer pods share one counter — not separate per-pod counters that would each think they have a full bucket.

---

## 3. ER DIAGRAM — Data Model

> **Draw this when asked: "Walk me through your data model"**

```
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                    NOTIFICATION SYSTEM — ER DIAGRAM                                  ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                      ║
║  ┌─────────────────────────────┐        ┌──────────────────────────────────┐        ║
║  │         CLIENTS             │        │         USER_PREFERENCES         │        ║
║  ├─────────────────────────────┤        ├──────────────────────────────────┤        ║
║  │ PK  client_id  varchar(100) │        │ PK  client_id  varchar(100)      │        ║
║  │     name       varchar(255) │        │ PK  ext_user_id varchar(255)     │        ║
║  │     api_key    varchar(255) │◀───┐   │     channels   jsonb             │        ║
║  │     rate_limit int          │    │   │     types      jsonb             │        ║
║  │     created_at timestamptz  │    │   │     dnd        boolean           │        ║
║  └─────────────────────────────┘    │   │     updated_at timestamptz       │        ║
║                                     │   └──────────────────────────────────┘        ║
║                                     │                                               ║
║  ┌─────────────────────────────┐    │   ┌──────────────────────────────────┐        ║
║  │         TEMPLATES           │    │   │          NOTIFICATIONS            │        ║
║  ├─────────────────────────────┤    │   ├──────────────────────────────────┤        ║
║  │ PK  template_id  uuid       │    └──▶│ PK  notification_id  uuid        │        ║
║  │ PK  version      int        │        │     client_id   varchar(100)     │        ║
║  │     name         varchar    │        │     ext_user_id varchar(255)     │        ║
║  │     channel      enum       │◀───────│ FK  template_id  uuid            │        ║
║  │     subject      text       │        │     channel     enum             │        ║
║  │     body         text       │        │     payload     jsonb            │        ║
║  │     variables    jsonb      │        │     status      enum             │        ║
║  │     is_active    boolean    │        │     priority    enum             │        ║
║  │     created_at   timestamptz│        │     scheduled_at timestamptz     │        ║
║  └─────────────────────────────┘        │     created_at  timestamptz      │        ║
║           (composite PK)                │     metadata    jsonb            │        ║
║           immutable versioning          └──────────────┬───────────────────┘        ║
║                                                        │ 1:1                        ║
║                                                        │                            ║
║  ┌────────────────────────────────┐    ┌──────────────▼───────────────────┐        ║
║  │     NOTIFICATIONS_OUTBOX       │    │         DELIVERY_STATUS           │        ║
║  ├────────────────────────────────┤    ├──────────────────────────────────┤        ║
║  │ PK  outbox_id       uuid       │    │ PK  delivery_id      uuid        │        ║
║  │ FK  notification_id uuid       │    │ FK  notification_id  uuid        │        ║
║  │     event_type      varchar    │    │     channel          enum        │        ║
║  │     payload         jsonb      │    │     provider         varchar     │        ║
║  │     published       boolean    │    │     provider_msg_id  varchar     │        ║
║  │     published_at    timestamptz│    │     status           enum        │        ║
║  │     created_at      timestamptz│    │     sent_at          timestamptz │        ║
║  └────────────────────────────────┘    │     delivered_at     timestamptz │        ║
║    (transactional outbox pattern)      │     error_message    text        │        ║
║    CDC polls: published=false          │     retry_count      int         │        ║
║                                        └──────────────────────────────────┘        ║
╚══════════════════════════════════════════════════════════════════════════════════════╝

  ENUMS:
  channel:  EMAIL | SMS | PUSH | INAPP
  status:   PENDING | SCHEDULED | SENT | DELIVERED | FAILED | CANCELLED
  priority: CRITICAL | HIGH | NORMAL | LOW

  REDIS KEYS (not in SQL schema but part of data model):
  user_pref:{userId}               → JSON, TTL 24h
  template:{templateId}:{version}  → JSON, TTL 1h
  rate_limit:{channel}:{provider}  → INT (token bucket), no TTL
  otp:{userId}:{purpose}           → STRING (6-digit), TTL 300s
```

### Scenario: Why This ER Design?

*"Two things are unusual in this schema that interviewers will probe.*

*First: Templates has a composite primary key — (template_id, version). That's intentional. Templates are immutable. When you update a template, you INSERT a new version row and set is_active=false on the old one. You never UPDATE a template body in-place. Why? Because right now there are 50,000 notifications in Kafka that were rendered against version 1 of that template. If you change the template, those in-flight notifications are suddenly inconsistent. More importantly, it gives you rollback capability and A/B testing — you can route 10% of users to version 2 while 90% still get version 1.*

*Second: notifications_outbox. This is the transactional outbox pattern and it's critical for correctness. The Notifications table and the outbox are written in the SAME database transaction. If Kafka is down, the message sits in the outbox with published=false. The CDC poller retries it. The notification cannot be lost because it's already persisted in our database."*

> **WHY THE TRANSACTIONAL OUTBOX PATTERN EXISTS? (Beginner Explanation)**
> Imagine you write a cheque and then separately walk to the post office to mail it. If you drop dead between those two steps, the cheque is written but never mailed. That is the bug: two separate operations with a gap between them.
> The outbox pattern staples both actions together. Writing the notification to the DB and writing to the outbox table happen in one atomic database transaction — both succeed or both fail, with no gap. The "postal worker" (CDC poller) then picks up the outbox record and mails it to Kafka on a separate schedule.
> If Kafka is down? The outbox record just sits there with published=false. The poller retries every 100ms until Kafka comes back. The notification is never lost.
> Without this: crash between "DB write" and "Kafka publish" = notification silently disappears. User never gets their password reset email. No alert. No trace.

### Cross Questions — ER Design

| Question | Strong Answer |
|---|---|
| Why not just store rendered content in Kafka directly? | Kafka messages have size limits. More importantly, the DB is our source of truth — if Kafka loses messages, we can replay from the outbox. |
| Why JSONB for payload instead of normalized columns? | Notification payload structure varies by channel and template. Email has subject+body+HTML. SMS has just body. Push has title+body+deep_link+badge. JSONB avoids a wide nullable table. |
| Why separate delivery_status table instead of status column on notifications? | A notification can have multiple delivery records — one per channel, one per retry attempt, one per device for push multi-device fanout. One-to-many relationship. |
| How do you handle GDPR right-to-erasure? | We store only external_user_id from the client, not PII. The client maps their user_id to PII. We can delete all notification rows by external_user_id without knowing the person's name or email. |

---

## 4. SEQUENCE DIAGRAM — End-to-End Happy Path

> **Draw this when asked: "Walk me through a notification from trigger to delivery"**

```
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║            SEQUENCE: Order Confirmation Email (Normal Priority)                           ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                          ║
║  OrderSvc   APIGateway   NotifSvc    Redis     NotifDB    OutboxCDC   Kafka   EmailConsumer  SendGrid  ║
║     │           │           │          │          │           │          │         │           │     ║
║     │ POST /notif│           │          │          │           │          │         │           │     ║
║     │──────────▶│           │          │          │           │          │         │           │     ║
║     │           │ JWT valid? │          │          │           │          │         │           │     ║
║     │           │ RateLimit? │          │          │           │          │         │           │     ║
║     │           │──────────▶│          │          │           │          │         │           │     ║
║     │           │           │ GET template:{id}   │           │          │         │           │     ║
║     │           │           │─────────▶│          │           │          │         │           │     ║
║     │           │           │◀─────────│ (cache hit, 95%)     │          │         │           │     ║
║     │           │           │ GET user_pref:{uid} │           │          │         │           │     ║
║     │           │           │─────────▶│          │           │          │         │           │     ║
║     │           │           │◀─────────│ {email:true,push:true}          │         │           │     ║
║     │           │           │ Render template (replace vars)  │          │         │           │     ║
║     │           │           │          │          │           │          │         │           │     ║
║     │           │           │ BEGIN TRANSACTION               │          │         │           │     ║
║     │           │           │─────────────────────▶ INSERT notifications(PENDING)  │           │     ║
║     │           │           │─────────────────────▶ INSERT outbox(published=false) │           │     ║
║     │           │           │          │          │ COMMIT    │          │         │           │     ║
║     │           │ 200 OK { notificationId: NOTIF789, status: PENDING }   │         │           │     ║
║     │◀──────────│           │          │          │           │          │         │           │     ║
║     │           │           │          │          │           │          │         │           │     ║
║     │           │           │          │     (100ms later — CDC polls)   │         │           │     ║
║     │           │           │          │          │ SELECT outbox WHERE  │         │           │     ║
║     │           │           │          │          │ published=false      │         │           │     ║
║     │           │           │          │          │──────────▶│          │         │           │     ║
║     │           │           │          │          │           │ Kafka.publish(      │           │     ║
║     │           │           │          │          │           │  topic: notif.std.email,        │     ║
║     │           │           │          │          │           │  key: NOTIF789)     │           │     ║
║     │           │           │          │          │           │─────────▶│          │           │     ║
║     │           │           │          │          │           │ UPDATE outbox published=true    │     ║
║     │           │           │          │          │           │          │         │           │     ║
║     │           │           │          │          │           │          │ consume │           │     ║
║     │           │           │          │          │           │          │────────▶│           │     ║
║     │           │           │          │          │           │ Idempotency: SELECT delivery_status   ║
║     │           │           │          │          │←──────────────────────────────│           │     ║
║     │           │           │          │          │ 0 rows → proceed    │          │           │     ║
║     │           │           │          │ GET rate_limit:email:sendgrid   │         │           │     ║
║     │           │           │          │◀──────────────────────────────  │         │           │     ║
║     │           │           │          │ tokens=49, DECR → proceed       │         │           │     ║
║     │           │           │          │          │           │          │ POST /v3/mail/send  │     ║
║     │           │           │          │          │           │          │─────────────────────▶    ║
║     │           │           │          │          │           │          │         │ 202 Accepted    ║
║     │           │           │          │          │           │          │◀────────────────────│    ║
║     │           │           │          │          │ INSERT delivery_status(SENT, msg_sg123)    │    ║
║     │           │           │          │          │◀──────────────────────────────│           │     ║
║     │           │           │          │          │           │          │         │           │     ║
║     │                       (minutes later — SendGrid webhook)           │         │           │     ║
║     │           │           │          │          │           │          │         │ POST /webhooks  ║
║     │           │           │ ◀─────────────────────────────────────────────────────────────── │    ║
║     │           │           │ respond 200 OK immediately      │          │         │           │     ║
║     │           │           │ UPDATE delivery_status SET status=DELIVERED          │           │     ║
║     │           │           │─────────────────────▶           │          │         │           │     ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝

  SEQUENCE: OTP Fast-Track (Critical Priority — <10s SLA)
  ──────────────────────────────────────────────────────
  Auth Svc → POST /notifications { priority: critical, channels: [sms], templateId: otp_login }
           → No rate limit check for critical
           → Topic: notifications.critical.sms (20 dedicated workers)
           → Worker → Twilio API (no queue wait)
           → Target: <10 seconds total
```

### Scenario: Why Async with Outbox and not Direct Kafka Publish?

*"This is the question that separates senior engineers from mid-level. The naive approach is: write to DB, then publish to Kafka. Two separate operations. The problem is there's a window between those two operations.*

*Scenario: The DB write succeeds. Your service crashes before the Kafka publish. The notification is in the DB as PENDING — but Kafka never got the message. Nobody's polling the DB. That notification is stuck forever. User never gets their password reset email.*

*The outbox pattern closes that window. We write the notification AND the outbox record in a single ACID transaction. Either both commit or neither does. A CDC service — Change Data Capture, like Debezium — polls the outbox every 100ms for published=false records. If Kafka is down, the poller just retries next cycle. The notification will never be lost as long as the DB write succeeded.*

*The beautiful part: the caller — Order Service — gets a 200 OK the moment the DB transaction commits. They don't wait for Kafka, they don't wait for SendGrid. The whole delivery chain is now fully asynchronous and durable."*

### Cross Questions — Sequence

| Question | Strong Answer |
|---|---|
| What if the CDC poller publishes to Kafka and then crashes before marking published=true? | Kafka receives the message. On CDC restart, it re-reads the same outbox record (published=false) and publishes again. Kafka now has two copies. That's why we have idempotency on the consumer side — SELECT delivery_status before sending. |
| What if the user updates their opt-out preference while their notification is already in Kafka? | This is a race condition. We check preferences before writing to the outbox. If they opt out after the outbox write, the message is already committed to be sent. We accept this — eventual consistency. For regulatory compliance (GDPR erasure), we honor it on the next notification. |
| Why 100ms poll interval for CDC? | Balance between latency and DB load. 100ms gives us <1s notification pipeline latency. 1000 records per poll batch. At scale, switch to real CDC (Debezium with Postgres WAL) which is event-driven rather than polling. |

---

## 5. API DESIGN — Detailed Contracts

> **Draw this when asked: "Show me your API design"**

### 5.1 Notification Send API

```
POST /api/v1/notifications
Authorization: Bearer {jwt_token} | X-API-Key: {api_key}
Content-Type: application/json

REQUEST:
{
  "templateId": "order_confirmation",
  "templateVersion": 3,              // optional — defaults to latest active version
  "recipientId": "user_abc123",      // client's internal user ID
  "variables": {
    "name": "Alice",
    "order_id": "ORD456",
    "amount": "$49.99",
    "tracking_url": "https://track.co/ORD456"
  },
  "channels": ["email", "push"],     // optional — defaults to template's default channels
  "priority": "normal",              // critical | high | normal | low
  "scheduledAt": "2026-09-01T09:00:00Z",  // optional — omit for immediate send
  "metadata": {
    "campaign_id": "black_friday_2026",
    "idempotency_key": "order-ORD456-email-v1"  // client-supplied dedup key
  }
}

RESPONSE 200 OK:
{
  "notificationId": "notif_f7a9c123",
  "status": "PENDING",
  "channels": ["email", "push"],
  "scheduledAt": null,
  "createdAt": "2026-08-30T14:22:10Z"
}

ERROR RESPONSES:
400 Bad Request  → { "error": "MISSING_VARIABLE", "detail": "Variable 'name' required by template" }
401 Unauthorized → { "error": "INVALID_API_KEY" }
404 Not Found    → { "error": "TEMPLATE_NOT_FOUND", "templateId": "order_confirmation" }
429 Too Many Requests → { "error": "RATE_LIMIT", "retryAfter": 60 }
```

### 5.2 Notification Status API

```
GET /api/v1/notifications/{notificationId}
GET /api/v1/notifications/{notificationId}/status

RESPONSE 200 OK:
{
  "notificationId": "notif_f7a9c123",
  "status": "DELIVERED",
  "channels": {
    "email": {
      "status": "DELIVERED",
      "provider": "SendGrid",
      "sentAt": "2026-08-30T14:22:11Z",
      "deliveredAt": "2026-08-30T14:22:13Z"
    },
    "push": {
      "status": "DELIVERED",
      "provider": "FCM",
      "sentAt": "2026-08-30T14:22:11Z",
      "deliveredAt": "2026-08-30T14:22:12Z"
    }
  }
}
```

### 5.3 Template Management API

```
# Create template (POST → new template, version starts at 1)
POST /api/v1/templates
{
  "name": "order_confirmation",
  "channel": "email",
  "subject": "Order {{order_id}} confirmed",
  "body": "Hi {{name}}, your order {{order_id}} for {{amount}} is confirmed.",
  "variables": ["name", "order_id", "amount"]
}
RESPONSE: { "templateId": "tmpl_xyz", "version": 1, "status": "active" }

# Update template (PUT → creates NEW version, sets old to is_active=false)
PUT /api/v1/templates/{templateId}
{
  "body": "Hi {{name}}, great news! Your order {{order_id}} for {{amount}} is confirmed.",
  "variables": ["name", "order_id", "amount"]
}
RESPONSE: { "templateId": "tmpl_xyz", "version": 2, "previousVersion": 1, "status": "active" }

# Get specific version (for A/B test or rollback)
GET /api/v1/templates/{templateId}/versions/{version}

# Deactivate template (soft delete)
DELETE /api/v1/templates/{templateId}
→ Sets is_active=false. Existing notifications in-flight complete using cached payload.
```

### 5.4 User Preference API

```
# Update preferences
PUT /api/v1/preferences/{userId}
{
  "channels": {
    "email": true,
    "sms": false,
    "push": true,
    "inapp": true
  },
  "types": {
    "promotional": false,
    "transactional": true,
    "alerts": true
  },
  "doNotDisturb": false,
  "dndWindow": { "start": "22:00", "end": "08:00", "timezone": "Asia/Kolkata" }
}
RESPONSE: { "updated": true, "effectiveAt": "2026-08-30T14:25:00Z" }
# Side effect: publishes to Kafka topic user.preference → invalidates Redis cache

# Get preferences
GET /api/v1/preferences/{userId}

# Bulk notification (campaign)
POST /api/v1/campaigns
{
  "name": "Black Friday 2026",
  "templateId": "promo_black_friday",
  "segmentId": "all_active_users",   // filter from user DB
  "scheduledAt": "2026-11-29T00:00:00Z",
  "priority": "low"
}
RESPONSE: { "campaignId": "camp_bfri26", "recipientCount": 4200000, "status": "SCHEDULED" }
```

### Why This API Design?

*"A few design decisions I want to call out. First, the idempotency key in the metadata. If Order Service retries its POST because it timed out waiting for our 200, without an idempotency key we'd create duplicate notifications. The client supplies a stable key — like order-ORD456-email-v1 — and we deduplicate on our side before inserting to the DB.*

*Second, PUT on templates creates a new version rather than updating in-place. This is a content-addressed design. Every notification in the system carries a template_id and version. If you update the template, all future notifications use the new version. All in-flight notifications use their original version. No surprise content changes.*

*Third, the status endpoint returns per-channel delivery status, not just a single status. A notification might be delivered by push but bounced by email. Those are different outcomes for the same notification_id."*

> **WHY FANOUT IS A HARD PROBLEM? (Beginner Explanation)**
> "Fanout" means one event → millions of individual deliveries. Sending a Diwali sale alert to 10 million users = 10 million individual push/SMS sends.
> The naive approach: a for-loop inside the API handler that calls Twilio 10 million times. Problems: the API is blocked for hours, provider rate limits are hit instantly, if the server crashes halfway you don't know where you left off.
> The correct approach: the POST /campaigns API just creates a job record (recipientCount: 10M, templateId: X, scheduledAt: Y) and returns immediately with a campaignId. A separate Fanout Worker service reads the user segment in batches of 1,000, publishes one Kafka message per user, and the normal consumer pool processes them in parallel at whatever rate providers allow.
> The API returned in milliseconds. The actual work fans out across hundreds of consumers over the next several minutes. If a consumer crashes midway, Kafka's offset means it picks up exactly where it stopped — no double-sends, no skipped users.

### 5.5 Notification Inbox & Management APIs

```
# Get notification history for a user (inbox / audit log)
GET /api/v1/notifications?user_id={userId}&page=1&limit=20&unread=true
Authorization: Bearer {jwt_token} | X-API-Key: {api_key}

RESPONSE 200 OK:
{
  "notifications": [
    {
      "notificationId": "notif_f7a9c123",
      "templateId": "order_confirmation",
      "channel": "inapp",
      "status": "DELIVERED",
      "read": false,
      "createdAt": "2026-08-30T14:22:10Z",
      "deliveredAt": "2026-08-30T14:22:12Z",
      "preview": "Hi Alice, your order ORD456 is confirmed."
    }
  ],
  "pagination": { "page": 1, "limit": 20, "total": 143, "hasNext": true }
}

# Mark a notification as read (in-app bell icon acknowledgement)
PATCH /api/v1/notifications/{notificationId}/read
Authorization: Bearer {jwt_token}

RESPONSE 200 OK:
{ "notificationId": "notif_f7a9c123", "read": true, "readAt": "2026-08-30T15:00:00Z" }

# Cancel a pending or scheduled notification (before it reaches SENT)
DELETE /api/v1/notifications/{notificationId}
Authorization: Bearer {jwt_token} | X-API-Key: {api_key}

RESPONSE 200 OK:
{ "notificationId": "notif_f7a9c123", "status": "CANCELLED", "cancelledAt": "2026-08-30T14:30:00Z" }

ERROR RESPONSES:
409 Conflict → { "error": "CANNOT_CANCEL", "detail": "Notification already SENT — cancellation not possible" }

# List all templates for the client
GET /api/v1/templates?channel=email&active=true&page=1&limit=50
Authorization: Bearer {jwt_token} | X-API-Key: {api_key}

RESPONSE 200 OK:
{
  "templates": [
    {
      "templateId": "tmpl_xyz",
      "name": "order_confirmation",
      "channel": "email",
      "latestVersion": 2,
      "isActive": true,
      "createdAt": "2026-01-10T10:00:00Z"
    }
  ],
  "pagination": { "page": 1, "limit": 50, "total": 12, "hasNext": false }
}
```

> **WHY GET /api/v1/notifications (inbox)?** The in-app notification bell icon loads its history via this endpoint on app-open. Users who were offline when notifications arrived pull their backlog here — referenced in Trap 6 above as `GET /notifications/inbox?unread=true`. Also essential for debugging ("why didn't user X get this notification?") and compliance audits ("show all notifications sent to user Y in the last 30 days"). Pagination is mandatory — a user with 3 years of notifications cannot load 10,000 rows at once.

> **WHY PATCH /notifications/{id}/read?** In-app notifications require a read/unread state that is distinct from delivery status. DELIVERED means the message reached the device. READ means the user consciously acknowledged it. PATCH is the correct verb here — you are making a partial update to one boolean field, not replacing the resource. When the user clicks the bell icon, the browser fires this call, which syncs the read state across all the user's devices via the User Preference Service.

> **WHY DELETE /notifications/{id}?** This maps to the CANCELLED state in the lifecycle state machine (Section 6). A client must be able to cancel a scheduled notification before it fires — for example, a flash-sale reminder that is no longer valid because the sale was extended. Only valid for PENDING or SCHEDULED status. Returns 409 Conflict if the notification is already SENT or DELIVERED — you cannot un-ring a bell. Without this endpoint, a client who schedules a campaign for the wrong time has no self-service recovery path.

> **WHY GET /api/v1/templates?** A POST endpoint exists to create templates but there is no way for a client to discover what templates exist. Without a list endpoint, teams must ask the notifications team out-of-band (Slack, wiki, email). A GET /templates endpoint enables self-service: a client portal can list available templates filtered by channel, show the latest active version, and let product teams pick the correct templateId without human intervention. Also required for any admin UI that manages template lifecycle.

---

## 6. STATE MACHINE DIAGRAM

```
╔══════════════════════════════════════════════════════════════════════╗
║              NOTIFICATION LIFECYCLE STATE MACHINE                    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║                    [API Accepted]                                    ║
║                         │                                           ║
║                         ▼                                           ║
║               ┌─────────────────┐                                   ║
║               │    PENDING      │  ← In outbox, not yet in Kafka    ║
║               └────────┬────────┘                                   ║
║                        │ CDC publishes to Kafka                     ║
║                        ▼                                            ║
║          ┌─────────────────────────┐                                ║
║          │  PENDING (in Kafka)     │  OR → SCHEDULED (future send)  ║
║          └────────────┬────────────┘                                ║
║                       │ Consumer picks up                           ║
║                       ▼                                             ║
║             ┌──────────────────┐                                    ║
║             │      SENT        │  ← Provider accepted (202)         ║
║             └──────┬───────────┘                                    ║
║                    │                                                ║
║          ┌─────────┼─────────────┐                                  ║
║          │         │             │                                   ║
║          ▼         ▼             ▼                                   ║
║    ┌──────────┐ ┌────────┐ ┌──────────┐                            ║
║    │DELIVERED │ │FAILED  │ │ RETRYING │                             ║
║    │(webhook) │ │(perm.) │ │(temp err)│                             ║
║    └──────────┘ └────────┘ └────┬─────┘                            ║
║                                 │ after 3 retries                  ║
║                                 ▼                                   ║
║                          ┌────────────┐                             ║
║                          │    DLQ     │ ← Ops alert, manual review  ║
║                          └────────────┘                             ║
║                                                                      ║
║    CANCELLED: can cancel PENDING or SCHEDULED, not SENT/DELIVERED   ║
║                                                                      ║
║    PERMANENT FAILURES (no retry):                                    ║
║    • Email bounced (550 invalid address)                             ║
║    • SMS: STOP reply received (compliance)                           ║
║    • Push: FCM invalid-registration-token, APNS 410 Gone            ║
║    • Unsubscribed user                                               ║
║                                                                      ║
║    TEMPORARY FAILURES (retry with backoff):                          ║
║    • Provider timeout (>10s no response)                             ║
║    • Rate limit 429                                                  ║
║    • Network error, 5xx from provider                                ║
║    Backoff: 1m → 5m → 15m → DLQ                                     ║
╚══════════════════════════════════════════════════════════════════════╝
```

> **WHY RETRY LOGIC AND DEAD LETTER QUEUE EXIST? (Beginner Explanation)**
> Think of a postal delivery attempt. If nobody's home, the postman tries again tomorrow, then the day after. After 3 failed attempts, the package goes to a special shelf at the post office for manual handling — that is the Dead Letter Queue (DLQ).
> Temporary failures (provider timeout, HTTP 429 rate limit, network blip) deserve a second chance — they will very likely succeed on retry.
> Permanent failures (invalid email address, user unsubscribed, FCM device token no longer exists) should NOT be retried — retrying burns money, wastes resources, and risks spam complaints.
> The DLQ is the "something went wrong, please look at this manually" shelf. An ops alert fires when messages land there. Engineers can inspect the message, fix the root cause, and decide whether to replay or discard.
> Without retry: any transient network hiccup = notification permanently lost. Without DLQ: failed notifications pile up silently with no visibility.

---

## 7. TRADE-OFFS TABLE

> **Bring this up proactively — it signals senior-level thinking**

| Decision | Choice | Alternative | Why We Chose This | When Alternative is Better |
|---|---|---|---|---|
| Queue | Kafka | RabbitMQ | Kafka: durable log, replay, partitioned priority lanes, high throughput (1M+/min) | RabbitMQ: simpler, great for complex routing rules, lower operational cost for <100K/day |
| Delivery guarantee | At-least-once + idempotency | Exactly-once Kafka transactions | Simpler to reason about; exactly-once has 30-40% throughput overhead | Financial transactions where duplicate is worse than retry overhead |
| Template storage | DB + Redis cache | CDN / object store | Templates queried per notification, need sub-ms access. DB is source of truth, Redis is speed | Large binary templates (email with images) → store HTML in S3, reference URL |
| User pref storage | PostgreSQL + Redis | Cassandra | Preference writes are low-volume, reads are high. Redis L1 absorbs 95% of reads | Cassandra: better if prefs are updated by every user action (real-time behavioral prefs) |
| Provider failover | Circuit breaker (Resilience4j) | Round-robin load balance | Circuit breaker isolates failures fast. Round-robin sends traffic to a broken provider | Round-robin if providers are equally reliable; circuit breaker if they fail in bursts |
| Notification dedup | delivery_status DB lookup | Bloom filter | DB lookup is exact. Bloom filter has false positives (wrongly skip a valid message) | Bloom filter: 100M+ dedup keys where false positive rate <0.1% is acceptable |
| In-app delivery | WebSocket | Long-poll / Server-Sent Events | WebSocket: bidirectional, low latency, single connection | SSE: simpler, works through HTTP proxies; Long-poll: max compatibility |

> **WHY WEBSOCKET vs LONG POLLING vs SSE? (Beginner Explanation)**
> All three solve the same problem: how does the server push a notification to a browser/app without the user refreshing the page?
>
> **Long Polling** — the browser asks "any new notifications?" and the server holds the connection open until there's something to say, then responds. The browser immediately asks again. Like a kid in the back seat asking "are we there yet?" every time you answer.
> Works everywhere, no special setup, but doubles the number of HTTP requests and adds latency.
>
> **Server-Sent Events (SSE)** — the server opens one HTTP connection and streams events down to the browser whenever they arrive. One-way only (server → browser). Like a radio broadcast — you tune in and listen; you can't talk back.
> Simpler than WebSocket, works through HTTP proxies and firewalls, good for notification feeds.
>
> **WebSocket** — a full two-way connection upgrade from HTTP. After the handshake, server and browser can send messages to each other at any time over a single persistent connection. Like a phone call — both sides can talk whenever they want.
> Best for in-app notification bell icons: low latency, efficient, handles "user read notification" acknowledgements back from the browser.
> The trade-off: WebSockets don't work through all corporate proxies, require stateful connections on the server side, and add operational complexity.

---

## 8. TECHNOLOGY CHOICES — Top 2 Per Category

### 8.1 Message Queue: Kafka vs RabbitMQ

```
┌─────────────────────────────────┬────────────────────────────────────┐
│           KAFKA                 │           RABBITMQ                  │
├─────────────────────────────────┼────────────────────────────────────┤
│ Log-based, durable retention    │ Queue-based, messages deleted on ack│
│ Partitioned for parallelism     │ Exchange + routing keys             │
│ Consumer groups, offset control │ Consumer competes for messages      │
│ Replay on failure (rewind)      │ No native replay                    │
│ 1M+ msgs/sec per broker         │ ~50K msgs/sec per queue             │
│ At-least-once (default)         │ At-most-once or at-least-once       │
│ Pull-based consumers            │ Push-based consumers                │
│ High ops complexity             │ Lower ops complexity                │
├─────────────────────────────────┼────────────────────────────────────┤
│ Why pick Kafka:                 │ Why pick RabbitMQ:                  │
│ 1M+ notifications/min           │ Complex routing logic               │
│ Replay for debugging/recovery   │ Small team, simple ops              │
│ Priority lanes by topic         │ Per-message TTL and DLQ built-in    │
│ Exactly correct consumer lag    │ Flexible exchange types             │
│ Long retention (1 week+)        │ Low volume, low latency             │
└─────────────────────────────────┴────────────────────────────────────┘
```

*"In this system we pick Kafka. The reason is multi-fold. We need replay — if our Email Consumer has a bug and we fix it, we want to replay the last hour of messages. RabbitMQ deletes messages on ack. We need priority lanes — separate Kafka topics for critical/standard/promotional is architecturally clean. And we need scale — at Black Friday peak, we're doing over a million notifications per minute. Kafka is designed for this. RabbitMQ would be the right choice if we were a startup with 50K daily notifications and we wanted simpler ops and complex per-message routing."*

**Realistic Example 1 — Kafka:**
Zomato sends 2M order confirmation notifications on a Sunday evening. Kafka absorbs the burst, consumers process at their own pace. If the SMS consumer crashes at 8PM, on restart it rewinds to its last committed offset and replays the missed messages. No data lost.

**Realistic Example 2 — RabbitMQ:**
An internal HR system sends 5,000 monthly payslip notifications. RabbitMQ topic exchange routes based on department. Dead letter queues handle failures. Ops team manages it with a UI dashboard. No need for Kafka's operational complexity.

---

### 8.2 Email Provider: SendGrid vs Amazon SES

```
┌─────────────────────────────────┬────────────────────────────────────┐
│           SENDGRID              │          AMAZON SES                 │
├─────────────────────────────────┼────────────────────────────────────┤
│ 50/sec free, 10K/sec paid       │ 14/sec (sandbox), thousands+ (prod) │
│ Rich dashboard, analytics UI    │ Basic metrics in CloudWatch         │
│ Template management built-in    │ No template management (you build)  │
│ Bounce/spam handling automated  │ Manual suppression list mgmt        │
│ ~$14.95/month for 100K emails   │ $0.10 per 1K emails (cheapest)      │
│ Strong deliverability tools     │ Excellent deliverability (AWS IPs)  │
│ Easy webhooks setup             │ SNS-based event notifications       │
│ SDKs: Java, Python, Node, etc   │ AWS SDK (standard)                  │
├─────────────────────────────────┼────────────────────────────────────┤
│ Why pick SendGrid:              │ Why pick SES:                       │
│ Rich analytics out-of-box       │ Cost: 90% cheaper at high volume    │
│ Template management via API     │ Already in AWS ecosystem            │
│ Better deliverability tooling   │ Scales to millions seamlessly       │
│ Faster time-to-production       │ Good for transactional only         │
└─────────────────────────────────┴────────────────────────────────────┘
```

*"We use SendGrid as primary and AmazonSES as fallback. Why? SendGrid has better observability — bounce handling, spam reports, open-rate tracking, all via webhooks out of the box. AmazonSES is 90% cheaper. So we route our high-volume promotional emails through SES to save cost, and our transactional emails through SendGrid for better tracking. The circuit breaker detects when SendGrid's failure rate exceeds 50% and flips all traffic to SES automatically."*

**Realistic Example 1 — SendGrid:**
Swiggy sends order confirmation emails. They need open-rate tracking, click tracking, bounce management. SendGrid's analytics dashboard shows them 30% of emails from @yahoo.com bounce — they investigate their suppression list.

**Realistic Example 2 — SES:**
A B2B SaaS company sends 50 million monthly invoice emails. At $0.10 per 1K, that's $5,000/month vs $50,000 with SendGrid. They build their own template rendering, use SES purely as a relay. Huge cost saving at scale.

---

### 8.3 SMS Provider: Twilio vs MSG91

```
┌─────────────────────────────────┬────────────────────────────────────┐
│            TWILIO               │            MSG91                    │
├─────────────────────────────────┼────────────────────────────────────┤
│ Global coverage (180+ countries)│ India-first, excellent IN coverage  │
│ 100 SMS/sec per number          │ Much higher throughput for India    │
│ $0.0075 per SMS (US)            │ ~$0.001 per SMS (India)             │
│ DLR webhooks, status tracking   │ DLR via webhook, push/pull          │
│ Excellent API docs, SDKs        │ Good API, simpler setup for India   │
│ TCPA compliance tools built-in  │ TRAI DND compliance for India       │
│ Programmable messaging          │ OTP-specific APIs                   │
├─────────────────────────────────┼────────────────────────────────────┤
│ Why pick Twilio:                │ Why pick MSG91:                     │
│ Global app (US/EU/APAC)         │ India-only, cost-sensitive          │
│ Best documentation, DX          │ Better delivery rates on IN carriers│
│ Number management at scale      │ Regulatory compliance for India     │
│ WhatsApp business messaging     │ DND filtering built-in              │
└─────────────────────────────────┴────────────────────────────────────┘
```

---

### 8.4 Push Notifications: FCM vs APNS

```
┌─────────────────────────────────┬────────────────────────────────────┐
│            FCM                  │           APNS                      │
│      (Firebase / Google)        │       (Apple Push Notif Svc)        │
├─────────────────────────────────┼────────────────────────────────────┤
│ Android + Web (Chrome/Firefox)  │ iOS, macOS, watchOS only            │
│ HTTP v1 API (REST)              │ HTTP/2 required (APNs protocol)     │
│ 10,000 msgs/sec per app         │ <5,000/sec best practice            │
│ Priority: normal | high         │ Priority: 5 (normal) | 10 (alert)   │
│ Token-based or topic fanout     │ Device token required               │
│ Free                            │ Free                                │
│ Data + notification messages    │ Notification + background modes     │
│ Collapse key for dedup          │ apns-collapse-id header             │
├─────────────────────────────────┼────────────────────────────────────┤
│ Key difference: you MUST use BOTH for a cross-platform mobile app.   │
│ They are not interchangeable — Android phones don't have APNS,       │
│ iOS devices don't have FCM (at native level).                        │
│                                                                       │
│ For multi-device users: send to all device tokens independently.     │
│ Store device_tokens[] per user. Fan out to each token.               │
│ On 410 Gone (APNS) or InvalidRegistration (FCM): remove token.       │
└──────────────────────────────────────────────────────────────────────┘
```

> **WHY FCM AND APNS EXIST? (Beginner Explanation)**
> Your phone cannot stay connected to every app's server 24 hours a day — that would drain the battery in hours. Instead, Apple and Google each run ONE always-on system-level connection per phone.
> When your app wants to send you a push notification, it does NOT connect directly to your phone. Instead, it tells Apple (via APNs) or Google (via FCM): "Hey, wake up this app on this user's phone and show them this message." Apple/Google deliver it through their always-on channel the next time the phone has signal.
> Think of APNs/FCM as the postal service for mobile devices. Your notification service hands the letter to the post office (Apple/Google), who delivers it whenever the phone comes online — even if the app is closed or the phone was sleeping.
> That is why you cannot skip these services: there is no direct socket connection from your server to a phone that is not actively running your app. Android uses FCM; iOS uses APNs. They are NOT interchangeable — you must call the right one per device type.
> Token cleanup matters: when FCM returns `InvalidRegistrationToken` or APNs returns `410 Gone`, the user uninstalled the app. Delete that token immediately or you will keep paying per-API-call to reach a ghost device.

---

## 9. SENIOR TRAP QUESTIONS — 15 YOE Level

> **These are the questions that trip up senior candidates. Model answers below.**

---

### TRAP 1: "You're using Kafka at-least-once. Walk me through exactly how many times a user can receive a duplicate notification and what stops each duplication."

*Strong Answer:*

*"There are four places where duplication can occur and each has a different safeguard.*

*First: CDC publishes the same outbox record twice. This happens if the CDC process crashes after publishing to Kafka but before marking published=true. Fix: consumer-side idempotency check on delivery_status.*

*Second: Kafka consumer receives the message, calls SendGrid successfully, but crashes before committing the Kafka offset. Kafka replays the message. Fix: same idempotency check — SELECT delivery_status WHERE notification_id + channel. If a row exists, skip.*

*Third: SendGrid receives our POST, sends the email, but our HTTP connection drops before we receive the 202. We retry and SendGrid sends it again. Fix: pass a unique message_id in the SendGrid X-Message-Id header — SendGrid deduplicates on their side for 72 hours.*

*Fourth: The webhook from SendGrid fires twice (SendGrid delivers webhooks at-least-once). Fix: ignore duplicate webhook events — we just UPDATE delivery_status SET status=DELIVERED — setting DELIVERED twice is idempotent.*

*So the exact answer: a user could theoretically receive two emails only if all of these break simultaneously: our idempotency check fails AND SendGrid's own dedup fails. In practice, with idempotent consumers, duplicates reach the user 0% of the time despite the at-least-once infrastructure."*

---

### TRAP 2: "Your Redis cache has a 24-hour TTL for user preferences. A user unsubscribes at 9am. They get a promotional email at 9:01am. How do you fix this?"

*Strong Answer:*

*"You're describing a cache consistency problem. The sequence is: user hits PUT /preferences, we update the DB, but we forgot to invalidate the Redis cache. The old cached value has 23h 59m of TTL left.*

*There are three patterns to fix this, and I'll rank them by correctness.*

*Option 1 — Cache invalidation on write: When we write to the DB, we immediately do a Redis DEL on user_pref:{userId}. The next cache miss hits the DB and gets fresh data. This is the simplest and most correct. The window is milliseconds.*

*Option 2 — Kafka-driven cache update: Preference changes publish to Kafka topic user.preference. A User Pref Consumer subscribes and does Redis SET with the new value. This means fresh data propagates asynchronously. Slightly better at scale because it's decoupled.*

*Option 3 — Preference check at consumer, not just at API time: Do a fresh preference check inside the Delivery Consumer just before sending to the provider. This adds a DB read per notification at the consumer side, but it's the last line of defense.*

*In my design, I implement Option 1 and Option 2 together. Option 3 is expensive at scale but I'd add it for the critical unsubscribe case specifically — a flag that says 'check preferences fresh for this user before sending.' Because the legal consequence of sending a promotional email after someone unsubscribed is much worse than a few extra DB reads."*

---

### TRAP 3: "You have 4 Kafka topics by priority. A critical OTP floods the retry topic. Does the retry topic have priority? How does it work?"

*Strong Answer:*

*"This is a real production scenario. If a batch of OTPs fails simultaneously — say a Twilio outage — thousands of CRITICAL OTPs land in the shared retry topic. The retry topic has no priority — it's FIFO. So a promotional email retry from yesterday blocks an OTP retry from right now.*

*The correct fix is separate retry topics by priority:*
*notifications.retry.critical*
*notifications.retry.standard*
*notifications.retry.promotional*

*Worker allocation mirrors the main topics: 20 workers on retry.critical, 5 workers on retry.promotional.*

*The second thing I'd do: for OTP specifically, skip the retry queue entirely. OTPs expire in 5 minutes. If the first send fails after 10 seconds, put it directly back on notifications.critical.sms — don't wait for the backoff schedule. A 1-minute retry backoff on an OTP that expires in 5 minutes is worse than sending immediately.*

*So for OTP: fail → immediately retry on critical channel → if second attempt fails → then use retry topic with 30-second intervals, not 1-minute. And after the OTP expires, mark it FAILED instead of DLQ — there's no point retrying an expired OTP."*

---

### TRAP 4: "Your template cache has 1-hour TTL. Marketing deploys a new template at 2pm but users are still getting the old version at 3pm. How do you fix this without a deploy?"

*Strong Answer:*

*"Templates are cached by (template_id, version). When marketing deploys a new template via PUT /api/v1/templates, we create version 2 and deactivate version 1. The cache key changes from template:abc:1 to template:abc:2. There is no old cache to invalidate — because the key itself is different.*

*This is the beautiful property of immutable versioning: cache invalidation is solved by design, not by adding complexity. Version 1 cache key can sit in Redis until its 1h TTL expires and it doesn't matter — nobody will request version 1 anymore because the DB marks it is_active=false.*

*The only edge case: if the Notification Service was in the middle of processing a notification when the template was upgraded, it fetched version 1 from cache. That notification will use version 1. Is that a problem? Usually no — the in-flight message already went through template validation and rendering. But if you need strict version consistency — for A/B testing with controlled groups — you explicitly pin the version in the API request: templateVersion: 2. Then the consumer always uses the pinned version."*

---

### TRAP 5: "At Black Friday scale — 1M notifications/min — how long does your database survive before it becomes the bottleneck?"

*Strong Answer:*

*"Let me do the math live. 1M notifications/min = 16,667/second. Each notification requires two DB writes: INSERT notifications and INSERT notifications_outbox. That's 33,000 writes/second to one Postgres instance. A well-tuned Postgres on modern hardware can handle 10,000-50,000 writes/second. So we're at the edge.*

*First mitigation: the outbox CDC batch size helps. Instead of 1000 individual Kafka publishes, we SELECT 1000 outbox records per poll, batch publish, batch UPDATE published=true. So the write amplification from CDC is bounded.*

*Second: connection pooling with PgBouncer. 30 Notification Service instances × 10 connections each = 300 connections. Without pooler, Postgres chokes on connection overhead.*

*Third: if we're genuinely bottlenecked, we shard notifications by user_id hash. Notifications_shard_0 through Notifications_shard_3. This distributes writes 4-way.*

*Fourth: consider TimescaleDB or Cassandra for the delivery_status table specifically — it's append-heavy and rarely updated after the fact. Cassandra handles 100K+ writes/second trivially.*

*But honestly — at Black Friday I'd also check: do all 1M notifications need to go in 1 minute? Promotional emails have 30-minute SLA. We can throttle the campaign sender to 10K/minute and smooth out the write load over 100 minutes. The DB never sees the spike."*

---

### TRAP 6: "Interviewer: 'Why not use WebSockets for all channels including email?'"

*Strong Answer:*

*"I want to understand the question — WebSockets are a transport protocol for real-time bidirectional browser/app connection. Email, SMS, and push notifications don't use WebSockets because they work when the user is offline.*

*WebSockets only work when the user's app is open and connected. The moment they close the browser or app, the connection drops. Email and push can reach users hours later when they return.*

*WebSockets are the right mechanism for in-app notifications only — the little bell icon that shows 'Your order is confirmed' while you're actively using the app. For that use case: each logged-in user maintains a WebSocket connection. Notification Service publishes to a Redis pub/sub channel keyed by user_id. A WebSocket Gateway subscribes and pushes to the connected session.*

*If you want to go deeper on in-app: users who are offline when the notification arrives get the notification on their next login via a REST API call — GET /api/v1/notifications/inbox?unread=true. We never lose the notification — it's in the DB. We just delivery it at connection time."*

> **WHY PUSH vs PULL DELIVERY? (Beginner Explanation)**
> **Pull**: the client asks the server "anything new for me?" on a schedule or on app-open. Like checking your mailbox every morning. Simple, reliable, works offline. Downside: latency — you only see the notification when you next open the app.
> Example in this system: GET /notifications/inbox when the user opens the app. All missed in-app notifications load immediately.
>
> **Push**: the server proactively sends the notification to the client the instant it is ready. Like receiving a text message — you do not ask for it; the message finds you. Requires a live connection (WebSocket, FCM, APNs).
> Example in this system: WebSocket pushes the notification to the browser bell icon in real time while the user is actively on the site.
>
> **Why both?** Push is ideal when the user is online (instant, zero latency). Pull is the safety net for offline users — notifications are durably stored in the DB and delivered on next connection. A production system needs both: push for speed, pull for reliability.

---

### TRAP 7: "How do you handle the 'thundering herd' when Kafka consumer restarts after 2 hours of downtime?"

*Strong Answer:*

*"Classic thundering herd. Consumer group was down for 2 hours. 7.2 million messages accumulated in the Kafka topics (at 1M/min that's 120 million in 2 hours, but let's say it's 7.2M in a lower-traffic window). Consumer group restarts with 30 workers. They see 7.2M messages and all 30 start hammering SendGrid simultaneously.*

*Three things I do:*

*First: rate limiter is the circuit breaker here. The token bucket in Redis caps at 10,000 emails/sec regardless of how many consumers are running. So even with 100 consumers, they collectively can't exceed provider limits. The messages will process over time, not in a spike.*

*Second: consumer startup rate limiting. In Kubernetes, I stagger pod startup with an initialDelaySeconds and add a startup rate limit in the consumer code — process only N messages in the first minute, then ramp up. This prevents all 30 pods from hammering the rate limiter simultaneously.*

*Third: dead letter queue monitoring. After 2 hours of backlog, there may be notifications that are now stale — a Black Friday flash sale that ended 90 minutes ago. I add a staleness check: if (now - notification.created_at) > staleness_threshold, mark it CANCELLED instead of sending. A 2-hour-old promotional email might be worse to send than to not send."*

---

### TRAP 8: "How does your system handle a user who has 10 devices — 3 Android phones, 4 iOS tablets, 3 web browsers?"

*Strong Answer:*

*"Great question on multi-device fanout. The user_preferences table stores device_tokens as a JSON array: device_tokens: ['fcm_token_1', 'fcm_token_2', 'fcm_token_3', 'apns_token_1', 'apns_token_2', 'fcm_web_1', ...]*

*When the push consumer picks up a notification for this user, it does a fanout: for each token, create a delivery attempt. So one logical notification_id generates 10 delivery_status rows — one per device.*

*But there's nuance here. FCM and APNS are different providers with different APIs. Android tokens go to FCM. iOS tokens go to APNS. Web push tokens go to Web Push (different from FCM). So the consumer needs to classify tokens by type and call the right provider API.*

*Token cleanup is critical. When FCM returns InvalidRegistrationToken or APNS returns 410 Gone, we know that device uninstalled the app. We remove that token from the user's device_tokens array immediately — UPDATE users SET device_tokens = array_remove(device_tokens, 'bad_token'). Otherwise we accumulate millions of dead tokens and pay per-API-call to send to them.*

*One more thing: for some notification types, you don't want all 10 devices to ring simultaneously. A 'You have a new message' push should maybe only go to the most-recently-active device. I'd add a device_activity_score or last_seen_at per token and only send to devices active in the last 30 days."*

---

## 10. COMPLIANCE AND REGULATORY TRAPS

> **These questions are asked at FAANG and fintech levels. Know these cold.**

### GDPR

*"Under GDPR, when a user requests data erasure, I need to delete all their notification records. But notification_id is a foreign key in delivery_status. I handle this with a soft-delete approach: we don't store the user's PII in our system — we store only external_user_id from the client. The client maps their user_id to name/email/phone. So our DELETE cascades on external_user_id and removes all notification rows, payload columns, and delivery records. The client handles PII deletion on their side.*

*For notification payload, rendered templates contain PII — 'Hi Alice, your order...' The payload column in notifications table gets null-ed on erasure. We keep the row skeleton for audit — notification was sent, date, template, channel — but the content is gone."*

### CAN-SPAM / TCPA

*"Every promotional email must have an unsubscribe link. We inject this automatically in the email template rendering step — if notification_type=promotional, append a standard unsubscribe footer with a signed token link. The unsubscribe link calls PUT /preferences/{userId} with promotional=false. This is enforced at the Notification Service level — even if the client's template doesn't include it, we inject it. Teams can't forget to add it.*

*For SMS: TCPA requires prior written consent to receive marketing texts. We store consent_granted=true in user_preferences. Before any promotional SMS, we check consent. Plus we handle STOP replies — Twilio forwards STOP messages to our webhook, we immediately set sms_channel=false in preferences."*

---

## 11. SCALING SCENARIOS — By Load Type

### Scenario A: Black Friday (10x normal traffic)

*"Black Friday hits at midnight. Traffic goes from 100K notifications/min to 1M notifications/min in 90 seconds.*

*Layer 1 — API Gateway: horizontal scaling is pre-provisioned. We know Black Friday is coming. We scale the Notification Service pods from 10 to 50 at 11:30 PM.*

*Layer 2 — Kafka: already has 100 partitions. Kafka itself handles the throughput without changes.*

*Layer 3 — Consumers: Kubernetes HPA monitors Kafka consumer lag. Lag > 10,000 messages → add consumer pods automatically. Max 100 consumers (one per partition).*

*Layer 4 — Rate limiter: This is the ceiling. SendGrid is limited to 10K emails/sec on our paid plan. At 1M/min ÷ 60sec = 16,667/sec. We can't send faster than SendGrid allows. Solutions: (1) Route promotional emails at 30-min SLA — spread them over 30 minutes. (2) AmazonSES as overflow — total capacity doubles. (3) Pre-warm: for known campaigns, distribute the workload before the spike.*

*Layer 5 — Database: Pre-partition the November partition on notifications table. Archive October to S3 the night before."*

### Scenario B: OTP during login spike

*"Major sale announcement at 9 AM. 500,000 users try to log in simultaneously. Each generates an OTP SMS. That's 500,000 SMS in 60 seconds — 8,333/sec. Twilio's rate limit is 100/sec per number. You need 84 Twilio phone numbers to handle this.*

*In practice: we pre-provision a pool of 100 Twilio numbers for OTP. The rate limiter distributes OTPs across the pool round-robin. Each number sends at 100/sec. 100 numbers × 100/sec = 10,000 OTPs/sec. We can handle 1M OTPs in under 2 minutes.*

*The OTP topic has 20 dedicated consumers. Critical priority means promotional emails never slow down OTPs. Even if the promotional queue has 5M backlogged messages, OTPs have their own separate lane."*

---

## 12. QUICK NUMBERS REFERENCE

| Metric | Value | Why It Matters |
|---|---|---|
| Scale target | 1M+ notifications/min | The baseline for all decisions |
| OTP SLA | < 10 seconds end-to-end | User is waiting, phone in hand |
| Transactional delay | 5-10 seconds acceptable | Order confirmation, shipping update |
| Promotional delay | 30 minutes acceptable | Newsletter, marketing email |
| Twilio SMS rate | 100/sec per number | Need 84+ numbers for 500K OTP spike |
| SendGrid free | 50/sec | Paid plans go to 10K/sec |
| FCM rate | 10,000/sec per project | Push at scale is cheap |
| APNS rate | <5,000/sec (best practice) | Per Apple guidance |
| Token bucket capacity | 100 tokens, refill = provider limit | Matches provider to our limit |
| Retry backoff | 1m → 5m → 15m → DLQ | Exponential to avoid hammering |
| Max retries | 3 | Balance between delivery and giving up |
| Redis user_pref TTL | 24 hours | Low pref-change frequency |
| Redis template TTL | 1 hour, 95% cache hit | Templates change rarely |
| OTP TTL | 5 minutes (300 seconds) | Security + UX balance |
| OTP length | 6 digits | 1M combinations, brute-force resistant |
| Outbox poll interval | 100ms | Sub-second notification pipeline |
| Outbox batch size | 1000 records per poll | Balance throughput vs DB load |
| CDC transition | Polling → Debezium WAL | At >10K/sec, switch to real CDC |
| DB partition retention | 6 months online, then S3 | Cost + query performance |
| SendGrid bulk API | 1000 emails per API call | 1000x fewer API calls |
| Circuit breaker threshold | 50% failure rate in 60s → open | Fast failover to backup provider |
| Consumer lag threshold (HPA) | > 10,000 messages | Trigger Kubernetes autoscale |

---

## 13. ARCHITECTURE EVOLUTION — How to Answer "How Would This Scale to 1 Billion?"

*"Let me walk you through the evolution of this system from startup to hyper-scale.*

*Stage 1 — MVP (1-10K users):*
*Single Spring Boot service → Postgres → sends directly to SendGrid. No Kafka, no Redis. Simple, fast to build. This is fine until you have ~100 notifications/minute.*

*Stage 2 — Growth (1M users):*
*Add Kafka for async decoupling. Add Redis for template and preference caching. Add retry logic. Split into Notification Service + Template Service. This handles 100K notifications/min.*

*Stage 3 — Scale (100M users):*
*What we've designed today. Prioritized Kafka topics. Outbox pattern. Multi-provider with circuit breaker. DB partitioning. This handles 1M+ notifications/min.*

*Stage 4 — Hyper-scale (1B users):*
*Shard the Notification DB by user_id hash — 8 shards minimum. Move to Cassandra for delivery_status (write-heavy, rarely-read-after-write). Replace Debezium single-process CDC with a distributed CDC cluster per shard. Move template storage to a CDN-backed content store for large HTML templates. Add geo-distribution — US users get sent through US-region Kafka, EU through EU, APAC through APAC. This reduces latency and satisfies data residency requirements.*

*The key insight: each stage solves a specific bottleneck. Don't over-engineer stage 1. But design stage 1 in a way that stage 2 is an addition, not a rewrite. The outbox pattern, async design, and prioritized queues should be there from day one because they're architectural choices that are hard to retrofit."*

---

## 14. OPENING AND CLOSING LINES (MEMORIZE THESE)

### Opening
*"A notification system is infrastructure — it's not a product feature, it's a platform. The hard problems aren't about sending one message, they're about never losing a message, never duplicating a message, and processing a million messages a minute while an OTP user is waiting 10 seconds for their login code. Let me design around those three constraints."*

### When asked "What would you do differently?"
*"In hindsight, I would have added an idempotency key at the API layer from day one — a client-supplied unique key so they can safely retry a POST /notifications without creating duplicates. That's the kind of thing that prevents a 3am incident where Order Service retried a notification call during a network blip and 40,000 customers got double emails."*

### Closing
*"The design I've walked through gives you at-least-once delivery guaranteed by the outbox pattern, no duplicate delivery guaranteed by idempotent consumers, sub-10-second OTP guaranteed by priority Kafka topics, and horizontal scalability at every layer. The only theoretical ceiling is provider rate limits — and even those we handle with multi-provider routing and request smoothing. I'm happy to go deeper on any piece of this."*

---

## KEY PATTERNS REFERENCED IN THIS DESIGN

> **For the 2-year developer:** These are the hidden concepts that make this design work. Each one has a dedicated deep-dive file. When asked "why did you choose X?" in your interview — these are the reasons.

### Push Notifications (APNs/FCM)
**Why it matters here:** The entire mobile delivery mechanism lives here — device tokens, APNs HTTP/2 multiplexing, offline storage for undelivered notifications, 410 Gone response for token cleanup, and the difference between background vs alert push types. This is the core of what the notification system actually does at the last mile.
**Deep dive:** `../../Push_vs_Pull_Notification_APNs_FCM.md`

### Circuit Breaker
**Why it matters here:** The notification service calls FCM and APNs as external dependencies. If FCM slows down (not fails — slows), without a circuit breaker every outbound thread blocks waiting for FCM, the thread pool fills, and the entire notification service degrades for all channels including OTP. OPEN state fails fast and uses a fallback (SMS) instead of dragging down the whole system.
**Deep dive:** `../../Circuit_Breaker_Pattern.md`

### Retry + Exponential Backoff + Jitter
**Why it matters here:** APNs returns 429 rate limit errors. Retrying immediately hammers APNs harder and makes the rate limit worse. Full jitter spreads retries randomly across the rate limit window so APNs recovers. Without jitter, all retried notifications fire simultaneously at the same second — a thundering herd of your own making.
**Deep dive:** `../../Retry_Exponential_Backoff_Jitter.md`

### CAP Theorem
**Why it matters here:** Notification system is AP — during a Kafka partition or provider outage, some notifications will arrive late or be retried (duplicate delivery risk). That is acceptable. Blocking all notifications until the partition heals (CP) would mean no OTPs during an outage — users cannot log in. Eventual delivery beats no delivery.
**Deep dive:** `../../CAP_Theorem_Applied_What_Actually_Breaks.md`

### [Kafka Partition Key & Consumer Groups](../../Kafka_Partition_Key_Consumer_Groups_Rebalancing.md)
**Why this system uses it:** Notification events keyed by `notification_id` (not user_id) to distribute load evenly across partitions. If keyed by user_id, a celebrity triggering 10M notifications all land on one partition — that consumer lags while others are idle. Consumer groups: 6 partitions × 3 consumer instances = 2 partitions per consumer. If one consumer dies, Kafka rebalances the 2 partitions to the remaining 2 consumers automatically.

### [Kafka Exactly-Once / At-Least-Once / DLQ](../../Kafka_Exactly_Once_At_Least_Once_DLQ.md)
**Why this system uses it:** Notification delivery uses at-least-once semantics — a duplicate push notification is slightly annoying but not catastrophic. Idempotency check: "has this notification_id already been delivered?" prevents true duplicates. DLQ is critical here: a malformed notification payload (bad device token format, null user_id) must not block the entire partition. After 3 retries, move to DLQ topic for human review; commit the offset and continue.

### [Kafka vs RabbitMQ vs SQS](../../Kafka_vs_RabbitMQ_vs_SQS_When_to_Use_Which.md)
**Why this system uses it:** Kafka as the notification backbone for high throughput (10M+ notifications/min) and replay capability (debug failed notifications by replaying from offset). SQS for Lambda-based email delivery — simple, managed, handles bursty email sends. The hybrid: Kafka → consumer groups for real-time push → SQS FIFO for email delivery with ordering guarantees per recipient.

### [Kafka Log Compaction & Outbox Pattern](../../Kafka_Log_Compaction_Outbox_Pattern.md)
**Why this system uses it:** Notification preferences (user's push token, email address, opted-in channels) stored as a compacted Kafka topic: latest preference per user_id is always available. New notification service deployment reads the compacted topic to initialize its state without needing to query the user DB. Outbox pattern for notification event publishing: in the same DB transaction that marks a notification as "queued," insert into the outbox table — Debezium publishes to Kafka. If the service crashes mid-publish, Debezium replays from WAL offset; no notification events are lost.

### [Backpressure & Reactive Streams](../../Backpressure_Reactive_Streams.md)
**Why this system uses it:** Celebrity post triggers 10M notification events in seconds. Notification delivery workers (APNs, FCM, email) can only process at a fixed rate. Kafka acts as the backpressure buffer — producers write at 10M/sec, consumers read at their own pace (e.g., 100K/sec). No events lost. Lag grows during the burst and drains over minutes. Monitor `kafka_consumer_lag` and autoscale notification worker pods via Kubernetes HPA when lag exceeds 500K messages. This is the correct response to a thundering herd of notifications — not blocking the producer.
