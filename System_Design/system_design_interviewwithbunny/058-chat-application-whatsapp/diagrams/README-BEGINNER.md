# WhatsApp Chat Application — BEGINNER Draw.io Diagrams

> **4 beginner-friendly diagrams** explaining real-time messaging at 1B+ users scale

## 🎯 What You'll Learn

- Why WebSocket exists (phone call vs walkie-talkie analogy)
- Why Cassandra for messages, Redis for queues, PostgreSQL for users
- Complete message flow: Alice → Bob in <100ms (step-by-step timing)
- Data model: Cassandra schema, Redis Streams, S3 pre-signed URLs

---

## 📁 Files in This Folder

| File | Purpose | Key Content |
|------|---------|-------------|
| **01-context-BEGINNER.drawio** | Big picture: actors, system boundary | WebSocket analogy, with/without comparison, 7 core components, scale numbers (1B users, 700K msg/sec) |
| **02-architecture-components-BEGINNER.drawio** | Component breakdown with WHY boxes | WHY Cassandra? WHY Redis Streams? WHY Chat Service as hub? 6-step Chat Service flow |
| **03-message-flow-sequence-BEGINNER.drawio** | Step-by-step: Alice sends "Hi!" to Bob | Timing breakdown (0-2ms, 2-5ms, ...), Green path (Bob online), Red path (Bob offline + push notification) |
| **04-data-model-BEGINNER.drawio** | Database schemas | PostgreSQL tables (users, groups), Cassandra message schema, Redis Streams structure, S3 upload/download flow |

---

## 🚀 How to Open

1. **Online**: [diagrams.net](https://app.diagrams.net) → File → Open → select `.drawio` file
2. **VS Code**: Install "Draw.io Integration" extension
3. **Desktop**: [Download draw.io app](https://github.com/jgraph/drawio-desktop/releases)

---

## 📚 Learning Path (Beginner → Advanced)

### Day 1: Context & Problem
**Start here:** `01-context-BEGINNER.drawio`
- Read the "WebSocket = Phone Call" analogy box
- Compare WITHOUT vs WITH real-time architecture
- Study the 7 core components inside the system boundary
- Memorize key numbers: 1B users, 700K msg/sec, <100ms delivery

**Interview script:**
> "WhatsApp uses persistent WebSocket connections instead of HTTP polling. Polling would mean 1 billion users × 1 request/second = 1 billion requests/second, and 99.9% would return nothing. WebSocket keeps one connection open, and the server pushes messages instantly when they arrive. This reduces latency from 1 second to <100ms and saves battery."

---

### Day 2: Architecture Components
**Next:** `02-architecture-components-BEGINNER.drawio`
- Read the 3 WHY boxes at top:
  - WHY Cassandra for messages? (receipt roll analogy)
  - WHY Redis Streams for hot path? (sub-millisecond latency)
  - WHY Chat Service as hub? (avoid N² peer connections)
- Study the 6-step Chat Service flow (validate → stamp seq ID → persist → queue → ACK → Kafka)
- Understand data layer: Cassandra, Redis Streams, S3+CDN, PostgreSQL, Kafka

**Interview script:**
> "I'd use Cassandra for the message store because chat messages are append-only and always read in time order per conversation. MySQL would need extreme sharding at 700K writes/sec. Cassandra handles this natively—just add more nodes. Redis Streams handles the hot delivery path with <1ms latency, while Kafka is reserved for async consumers like search indexing and analytics."

---

### Day 3: Message Flow Timing
**Deep dive:** `03-message-flow-sequence-BEGINNER.drawio`
- Follow the Green Path (Bob online):
  - 0-2ms: WebSocket send
  - 2-5ms: gRPC to Chat Service
  - 5-8ms: Cassandra write
  - 8-10ms: Redis XADD
  - 10-15ms: ACK to Alice (single ✓)
  - 10-30ms: Poll stream
  - 30-50ms: Push to Bob
  - Total: <100ms
- Study the Red Path (Bob offline):
  - Message stays in Redis Stream
  - Triggers FCM/APNs push notification
  - When Bob reconnects, fetch undelivered messages from Cassandra

**Interview script:**
> "When Alice sends a message, it goes through the Chat Service which persists it to Cassandra (source of truth) and publishes to a Redis Stream targeted at Bob's WebSocket server. The server polls the stream every 5ms and pushes to Bob's connection. Alice gets a single checkmark when the server receives it, double checkmark when Bob's device receives it, and blue checkmark when Bob reads it. Total latency is under 100ms P99."

---

### Day 4: Data Model
**Technical details:** `04-data-model-BEGINNER.drawio`
- PostgreSQL: users, contacts, groups, group_members (structured data, ACID transactions)
- Cassandra messages table:
  - PRIMARY KEY: ((conv_id), timestamp DESC, message_id)
  - Why? All messages for one conversation in ONE partition, sorted newest-first
  - Query: `SELECT * FROM messages WHERE conv_id = 'alice-bob' ORDER BY timestamp DESC LIMIT 50;`
  - Blazing fast! <10ms
- Redis Streams: `server.ws87.inbox` → one stream per WebSocket server
- S3 + CloudFront: Pre-signed URL upload (server never touches bytes), CDN edge cache (90% hit rate)

**Interview script:**
> "I'd use different databases for different access patterns. PostgreSQL for structured user data with ACID transactions. Cassandra for message history because it's optimized for time-series append-only writes—partition by conversation, cluster by timestamp descending. Redis Streams for the hot delivery queue with <1ms latency. S3 + CloudFront for media storage—clients upload directly with pre-signed URLs, and downloads are served from the CDN edge with 90% cache hit rate. This keeps the Chat Service stateless and scalable."

---

### Day 5: Cross-Questions & Edge Cases

**Expect follow-up questions:**

1. **"What if a user has 2 devices (phone + laptop)?"**
   - Each device gets its own WebSocket connection
   - Chat Service publishes to Redis Streams for BOTH servers (fanout)
   - Sequence IDs prevent duplicates (client deduplicates by seq_id)

2. **"How do you handle message ordering?"**
   - Cassandra clustering key: timestamp DESC
   - Chat Service stamps sequence IDs per conversation (1, 2, 3, ...)
   - Client has reorder buffer: if seq 3 arrives before seq 2, wait briefly then re-sort

3. **"What if Cassandra write fails but Redis Stream succeeds?"**
   - Write to Cassandra FIRST (source of truth)
   - Only publish to Redis after Cassandra ACK
   - If Cassandra fails, return error to Alice (no single ✓)
   - Never deliver a message that isn't persisted

4. **"Group chat fanout: write or read?"**
   - WhatsApp: Fanout on WRITE (push to each member's inbox)
   - Why? Simpler, low read latency
   - Trade-off: 256-member group = 256 Cassandra writes
   - For Twitter-scale (100K followers), use fanout on read + hybrid

5. **"How do you prevent duplicate messages?"**
   - Client-side deduplication: use message_id (UUID)
   - If network retry sends same msg twice, client sees same UUID and ignores

6. **"Media upload: what if user cancels mid-upload?"**
   - S3 pre-signed URL expires in 5 minutes
   - If client never sends the message, media_id is never referenced
   - Orphaned files cleaned up by S3 lifecycle policy (delete unreferenced objects after 24 hours)

---

## 🎨 Diagram Design Principles

### BEGINNER-Friendly Features:
✅ **Large fonts** (14-18pt) — easy to read  
✅ **Real-world analogies** — "WebSocket = phone call", "Cassandra = receipt roll"  
✅ **WHY boxes** — explain decision rationale, not just "what"  
✅ **Color-coded paths** — Green = online, Red = offline  
✅ **Step-by-step timing** — exact milliseconds for message flow  
✅ **Capacity numbers** — 1B users, 700K msg/sec, 2 PB media, <100ms latency  

### What Makes These Different from Typical Diagrams:
- **Not just boxes and arrows** — every component has a WHY explanation
- **Beginner analogies** — no assumption of prior knowledge
- **Production numbers** — actual scale (700K writes/sec, not vague "high throughput")
- **End-to-end flow** — complete path from Alice's tap to Bob's notification
- **Edge cases** — Red path (offline), duplicate prevention, retry logic

---

## 🔗 Related Files in Parent Folder

- `WhatsApp_Chat_System_Design_Interview_Guide.md` — Full interview guide (900+ lines)
- `chat-application-production-presentation.html` — Narrated slides
- `chatapps.md` — Additional notes

---

## 💡 Tips for Interview Prep

1. **Start with analogies** — non-technical explanation first
2. **State the problem before solution** — "Without WebSocket, we'd need polling which burns battery"
3. **Call out trade-offs** — "Fanout on write vs fanout on read: I'd choose write for simplicity at WhatsApp's 256-member limit"
4. **Use exact numbers** — "700K messages/sec, <100ms P99 latency, 2 PB media storage"
5. **Explain WHY, not just WHAT** — "Cassandra because messages are append-only time-series data"

---

## 📊 Capacity Planning Cheat Sheet

```
Users:           1B registered, 500M DAU
Throughput:      700K msg/sec peak (3× average)
Latency:         <100ms message delivery (P99)
Storage:         4.4 TB/day messages, 200 TB/day media
WebSocket:       2,500 servers × 400K connections = 1B total
Cassandra:       400 TB cluster (30-day retention, RF=3)
Redis:           65 GB (streams + presence)
S3 + CDN:        2 PB, 90% cache hit rate
```

---

## ✅ Interview Checklist

Before your interview, make sure you can:
- [ ] Explain WebSocket vs HTTP polling (walkie-talkie vs phone analogy)
- [ ] Draw the 7 core components from memory
- [ ] Walk through Alice→Bob message flow with timing (0-2ms, 2-5ms, ...)
- [ ] Explain Cassandra PRIMARY KEY: ((conv_id), timestamp DESC, message_id)
- [ ] Describe Redis Streams consumer groups (XREADGROUP, pending entries)
- [ ] Explain S3 pre-signed URL upload flow
- [ ] Answer "Why Cassandra?" vs MySQL/PostgreSQL
- [ ] Handle offline user scenario (Red path)
- [ ] Discuss group chat fanout trade-offs
- [ ] State capacity numbers (1B users, 700K msg/sec, <100ms, 2 PB)

---

**Created:** 2026-08-30  
**Style:** BEGINNER (architect creating materials for developers)  
**Purpose:** Interview preparation for real-time messaging systems at scale  

Open any diagram and start learning! 🚀
