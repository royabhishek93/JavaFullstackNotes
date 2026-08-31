# 🔔 Notification System — Beginner-Friendly Diagrams

## What Makes These Diagrams Special?

These diagrams are designed to **match the architect-level interview guide**. They include:

✅ **Restaurant/Hospital analogies** (explaining async processing)  
✅ **Layer-by-layer breakdown** with exact steps  
✅ **Priority queue visualization** (the critical innovation)  
✅ **"WHY" explanations** showing what problems each part solves  
✅ **Production scenarios** (Black Friday, OTP delays)  
✅ **Latency breakdowns** with real numbers  

## How to Open

### Option 1: Online (Easiest)
1. Go to [diagrams.net](https://app.diagrams.net)
2. File → Open → select any `.drawio` file from this folder
3. Edit, zoom, export as needed

### Option 2: VS Code
1. Install **Draw.io Integration** extension
2. Click any `.drawio` file in this folder
3. Edit directly in VS Code

### Option 3: Desktop App
1. Download [draw.io desktop](https://github.com/jgraph/drawio-desktop/releases)
2. Open any `.drawio` file

## Diagrams in This Folder

### 01-context-BEGINNER.drawio
**The Big Picture — Restaurant Analogy**

Shows three vertical sections:
- **Left**: Producers (Order Service, Payment Service, Auth Service, Marketing)
- **Center**: Notification Platform (API Gateway → Service → Kafka → Workers)
- **Right**: Delivery Channels (SendGrid, Twilio, FCM, WebSocket)

Key concepts explained:
- Why not call SendGrid directly? (coupling problem)
- Fire-and-forget pattern
- Priority lanes (critical vs promotional)
- Rate limiting per provider

**ANALOGY:** Restaurant kitchen — waiter drops ticket, walks away. Kitchen cooks at its own pace.

**Use this for:** Opening answer, showing high-level architecture in first 5 minutes

---

### 02-detailed-flow-BEGINNER.drawio
**Layer-by-Layer Flow — The Interview Winner**

This is the **diagram that wins architect interviews**. Shows 5 layers with exact implementation details:

**LAYER 1 — Request Entry**
- POST /api/v1/notifications
- JWT auth + rate limiting
- ⏱️ 2ms

**LAYER 2 — Notification Service (6 steps)**
- Step 1: Fetch template (Redis cache)
- Step 2: Validate variables
- Step 3: Fetch user preferences
- Step 4: Check opt-in (GDPR compliance)
- Step 5: Render template
- Step 6: **Outbox transaction** (atomic DB write)
- ⏱️ ~5ms → Return 200 OK

**LAYER 3 — Kafka Topics (Priority Lanes)**
- Critical: OTP, fraud (20 workers, 5sec SLA)
- Standard: orders (30 workers, 1min SLA)
- Promotional: ads (10 workers, 1hr SLA)
- Retry: exponential backoff
- DLQ: ops alert

**LAYER 4 — Delivery Consumer (4 steps per channel)**
- ① Idempotency check (no duplicates)
- ② Rate limiter (token bucket)
- ③ Route to provider
- ④ Write delivery status

**LAYER 5 — Delivery Confirmation**
- Provider webhooks (async)
- Retry strategy (temporary vs permanent failures)

**Use this for:** Deep-dive phase, showing you understand production complexities

---

### 03-priority-queues-BEGINNER.drawio
**Priority Queues — The Critical Innovation**

Side-by-side comparison:

**❌ BAD: Single Queue**
- 10M promo emails block 1 critical OTP
- OTP waits 27 hours
- User can't login → P0 incident

**✅ GOOD: Priority Queues**
- Critical lane: 20 workers, 5sec SLA
- Standard lane: 30 workers, 1min SLA
- Promotional lane: 10 workers, 1hr SLA
- OTP processed in 5 seconds, isolated from promo backlog

**ANALOGY:** Hospital ER triage — heart attack patient doesn't wait behind flu patients.

**Use this for:** 
- When interviewer asks "How do you prioritize notifications?"
- Explaining the Black Friday OTP problem
- Showing you understand queue theory

---

### 04-data-model-BEGINNER.drawio
**Database Schema — 5 Tables, 3 Databases, WHY Each Exists**

This is the **most detailed diagram** — shows complete data model:

**Database 1: Notification DB**
- `notifications` table: Main audit log
- `notifications_outbox` table: Transactional outbox pattern explained
- WHY atomic transaction prevents data loss

**Database 2: Template DB**
- `templates` table with **composite primary key** (template_id + version)
- WHY templates are immutable
- Versioning strategy (no surprise content changes)

**Database 3: User Preferences DB**
- `user_preferences` table: Opt-in/opt-out per channel
- JSONB structure explained
- GDPR compliance enforcement

**Database 4: Delivery Tracking**
- `delivery_status` table: Per-channel delivery records
- Idempotency check mechanism
- One-to-many relationship (1 notification → N delivery records)

**Redis Cache Layer:**
- Key patterns with TTL
- Hit rate percentages
- Cache invalidation strategies

**Use this for:**
- When interviewer asks "Walk me through your data model"
- Explaining transactional outbox pattern
- Showing you understand composite keys
- GDPR/compliance questions

---

## Interview Strategy

### Opening (First 2 minutes)
1. Draw **01-context-BEGINNER** (simplified version)
2. Say: *"Before diving in, let me clarify: this is infrastructure. The hard part isn't sending one email — it's sending 1 million per minute on Black Friday, ensuring every OTP lands in under 10 seconds, never duplicating when Kafka replays, and honoring 'do not disturb' preferences."*
3. Point to three sections: Producers → Platform → Providers

### Deep Dive (Next 15 minutes)
1. Use **02-detailed-flow-BEGINNER** as reference
2. Walk through Layer 2 step-by-step (this is where you win)
3. Emphasize:
   - **Outbox pattern** (no lost notifications)
   - **User preferences** (GDPR compliance)
   - **Template versioning** (in-flight consistency)

### Critical Question: "How do you prioritize?"
1. Pull up **03-priority-queues-BEGINNER**
2. Show bad design first (empathy)
3. Explain good design (separate Kafka topics + worker pools)
4. Give Black Friday scenario

## Production Scenarios Covered

These diagrams explain solutions to real problems:

| Scenario | Diagram | Solution Shown |
|----------|---------|----------------|
| Black Friday: 10M promo emails delay OTP | 03 | Priority queues isolate critical traffic |
| Kafka crashes mid-send → notification lost | 02 Layer 2 | Outbox pattern (atomic DB write) |
| SendGrid rate limits → account banned | 02 Layer 4 | Token bucket rate limiter in Redis |
| User opts out but still receives email | 02 Layer 2 Step 4 | User preference check before Kafka publish |
| Duplicate notifications after crash | 02 Layer 4 Step 1 | Idempotency check in delivery_status table |
| Marketing wants to change email wording | 02 Layer 2 Step 1 | Template versioning (no code deploy) |

## Customization Tips

Want to adapt these for your interview?

1. **Change scale**: Update "1M notifications/min" to your requirements
2. **Add channels**: Duplicate a provider box for WhatsApp, Slack, etc.
3. **Show your stack**: Replace SendGrid with your provider
4. **Export for presentation**: File → Export as PNG (1920x1080 for slides)
5. **Print for whiteboard practice**: Export as PDF, practice drawing simplified version

## Compared to Original Diagrams

| Typical Diagrams | These Diagrams |
|------------------|----------------|
| Shows boxes and arrows | Shows WHY each component exists |
| No timing info | Every layer has latency breakdown |
| Single generic queue | Explains priority queue architecture |
| Missing edge cases | Covers idempotency, retries, rate limiting |
| No analogies | Restaurant, hospital ER, hotel Do Not Disturb |

## Learning Path

**Week 1: Understand**
- Day 1-2: Study diagram 01 (big picture) + interview guide sections 1-2
- Day 3-4: Study diagram 02 (detailed flow) + guide section 3
- Day 5: Study diagram 03 (priority queues)

**Week 2: Practice**
- Day 1-2: Practice explaining diagram 02 Layer 2 from memory
- Day 3: Practice drawing simplified diagram 01 on whiteboard
- Day 4: Practice explaining priority queue problem/solution
- Day 5: Mock interview with friend

**Week 3: Deep Dive**
- Study "WHY" boxes in diagram 02
- Memorize latency breakdown (7ms to respond, async delivery)
- Practice answering: "Why not X?" for every component

## Key Concepts You MUST Explain

Interviewers will drill these:

1. **Outbox Pattern** (diagram 02 Layer 2 Step 6)
   - Why it's needed
   - How CDC poller works
   - What happens if Kafka is down

2. **Priority Queues** (diagram 03)
   - Black Friday OTP scenario
   - Separate Kafka topics + worker pools
   - SLA per priority level

3. **Idempotency** (diagram 02 Layer 4 Step 1)
   - Kafka at-least-once delivery
   - delivery_status table check
   - No duplicates even on replay

4. **Rate Limiting** (diagram 02 Layer 4 Step 2)
   - Token bucket in Redis
   - Provider limits (SendGrid 10K/sec)
   - Shared counter across pods

5. **User Preferences** (diagram 02 Layer 2 Step 3-4)
   - GDPR compliance
   - Do Not Disturb
   - Checked BEFORE Kafka publish

## Cross-Questions Covered

These diagrams help you answer:

- **"Why not AWS SNS?"** → Diagram 02 shows template management, user preferences, priority queues
- **"What if SendGrid is down?"** → Diagram 02 Layer 4 shows circuit breaker + fallback
- **"How do you avoid duplicate notifications?"** → Diagram 02 Layer 4 Step 1 (idempotency check)
- **"What happens if the service crashes mid-send?"** → Diagram 02 Layer 2 Step 6 (outbox pattern)
- **"How do you prioritize OTP over ads?"** → Diagram 03 (entire diagram!)

## Questions?

These diagrams are based on the [interview_guide.md](../interview_guide.md) in the parent folder. That guide has full code samples, cross-questions, and architectural rationale.

---

**Remember:** At senior/architect level, interviewers expect you to **anticipate production problems** before they ask. These diagrams show you've thought through the hard parts! 🔥
