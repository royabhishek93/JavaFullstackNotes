# Rate Limiter Diagrams — BEGINNER-FRIENDLY Edition

## 📖 What You'll Find Here

These diagrams are designed for **college students, bootcamp graduates, and junior engineers** preparing for system design interviews. They explain not just WHAT components exist, but **WHY each exists** with real-world analogies.

---

## 📂 Files in This Folder

### 01-context-BEGINNER.drawio
**The Big Picture — Restaurant Analogy**

Shows:
- **Without Rate Limiter**: 1 buggy client → entire API crashes for everyone
- **With Rate Limiter**: Request quota enforced → backend protected
- **Restaurant analogy**: "10 tables per hour max, others wait"
- **Request flow**: Client → API Gateway (check budget) → Redis (token state) → Backend OR 429
- **Key numbers**: <5ms latency, 1M req/sec scale, Free=100/min Premium=1000/min

**Use this for:** Interview opener, explaining "why rate limiting exists"

---

### 02-algorithm-comparison-BEGINNER.drawio
**4 Algorithms Visual Comparison**

Shows:
- **Fixed Window Counter**: Simplest, but has boundary spike problem (99 req at 10:00:58 + 100 at 10:01:00 = 199 in 2 sec!)
- **Sliding Window Log**: Most accurate, stores every timestamp, memory-heavy (10B entries for 100M users!)
- **Token Bucket ⭐ (RECOMMENDED)**: Industry standard (AWS, Stripe, GitHub), handles bursts, low memory
- **Leaky Bucket**: Smooths bursts, good for traffic shaping (not user limits)

**Comparison table**: Memory cost, accuracy, burst support, production use

**WHY Token Bucket wins:**
- Burst support: Mobile app fires 20 requests on open → allowed if tokens saved
- Low memory: Just 2 integers per user (vs 100M timestamps for Sliding Log)
- Two knobs: `capacity` (max instant burst) + `refill_rate` (sustained throughput)
- No boundary exploitation (smooth refill, no midnight reset gaming)

**Use this for:** "Which algorithm should we use?" question

---

### 03-token-bucket-flow-BEGINNER.drawio
**Step-by-Step Flow with Exact Timing**

Shows two flows:

**FLOW 1: REQUEST ALLOWED (Green Path)**
1. 0ms: Client sends GET /api/users
2. +0.5ms: Gateway checks policy cache in Redis → {limit:100, refill:10}
3. +1.0ms: Execute Lua script (ATOMIC):
   - Read tokens=95, last_refill=5sec ago
   - Refilled: 5 × 10 = 50 tokens
   - New tokens: min(100, 95+50) = 100 (capped)
   - Deduct 1 → 99 tokens left
   - Return ALLOW
4. +0.5ms: Forward to backend
5. +20ms: Backend returns 200 OK + data
   - Headers: `X-RateLimit-Remaining: 99`, `X-RateLimit-Reset: {timestamp}`

**Total: 2.5ms added by rate limiter**

**FLOW 2: REQUEST REJECTED (Red Path)**
1. Same steps 1-3
2. Lua script: tokens=0 → Return REJECT
3. Gateway immediately returns **HTTP 429** (backend NOT called!)
   - Headers: `Retry-After: 1`, `X-RateLimit-Remaining: 0`

**Use this for:** "Walk me through what happens when..." question

---

### 04-data-model-BEGINNER.drawio
**Database Schema + Redis Structures**

Shows:

**POSTGRES TABLE: rate_limit_rules**
- `rule_id`, `subject_type` (USER_ID/TIER/IP/GLOBAL), `subject_value`
- `endpoint` ('/api/users' or '*'), `algorithm` (TOKEN_BUCKET)
- `request_limit`, `window_sec`, `burst_capacity`, `refill_rate`
- `enforce_by` (USER_ID = per-user bucket, TENANT_ID = shared org bucket)
- **Index**: `(subject_type, subject_value, endpoint)` for fast lookup

**WHY each field:**
- `subject_type + subject_value`: Multi-level limits (per-user, per-tier, global)
- `burst_capacity vs refill_rate`: Instant burst vs sustained throughput
- `enforce_by`: Per-user quota vs per-org shared quota
- `is_active`: Soft-delete (audit trail)

**REDIS STRUCTURE 1: Token State (HASH)**
```
Key: rate_limit:user_123:/api/users
Fields:
  tokens      → 95
  last_refill → 1706270445
TTL: 3600 sec (auto-expire inactive buckets)
```

**REDIS STRUCTURE 2: Policy Cache (JSON)**
```
Key: policy:user_123:/api/users
Value: {"limit":100, "refill_rate":10, "burst_capacity":100, ...}
TTL: 3600 sec (write-through on policy update)
```

**Memory calculation:**
- 50M users × 3 endpoints × 170 bytes = 25.5 GB (but 10% active = 2.5 GB actual)
- Policy cache: 1.75 GB
- **Total: 4-5 GB for 50M users**

**Data flow on policy update (write-through):**
1. UPDATE Postgres (source of truth)
2. SET Redis policy cache
3. PUBLISH policy_update
4. All gateways invalidate local cache
5. Propagation time: <1 sec (vs 1 hour if TTL-only)

**Use this for:** "Show me your schema" or "How do you store policies?"

---

## 🎓 How to Use These for Interview Prep

### Day 1: Understand the WHY
- Open `01-context-BEGINNER.drawio`
- Read all the "WHY" boxes (why Redis not DB, why API gateway, why distributed)
- Practice the restaurant analogy out loud

### Day 2: Learn the Algorithm
- Open `02-algorithm-comparison-BEGINNER.drawio`
- Memorize Token Bucket wins: burst support + low memory + production-proven
- Practice explaining: "I recommend Token Bucket because..."

### Day 3: Master the Flow
- Open `03-token-bucket-flow-BEGINNER.drawio`
- Trace both flows (allowed + rejected)
- Memorize timing: 2.5ms total
- Practice explaining Lua script atomicity

### Day 4: Data Model Deep Dive
- Open `04-data-model-BEGINNER.drawio`
- Understand `enforce_by` (per-user vs per-tenant)
- Memorize memory: ~170 bytes per bucket
- Practice explaining write-through cache

### Day 5: Mock Interview
- Draw from memory: context → algorithms → flow → data model
- Explain trade-offs: Fixed Window vs Token Bucket
- Answer: "What if Redis goes down?" (circuit breaker, fail-open)

---

## 💡 Interview Tips

### When Interviewer Asks: "Design a rate limiter"
1. **Clarify scope** (1M rps? Per-user? Per-IP? Configurable?)
2. **Draw context diagram first** (`01-context`)
3. **Recommend Token Bucket** (cite AWS/Stripe usage)
4. **Show data model** (Postgres for policy, Redis for hot state)
5. **Walk through flow** (explain Lua script atomicity)

### Key Points to Mention
- ✅ **<5ms latency**: Redis in-memory (vs 10-50ms DB)
- ✅ **Distributed**: All gateways share same Redis counter
- ✅ **Burst support**: Token Bucket natural burst (mobile app open = 20 req)
- ✅ **Multi-level**: Per-user + per-IP + per-endpoint + global
- ✅ **Write-through cache**: Policy updates propagate <1 sec
- ✅ **Circuit breaker**: Redis down → fail-open (availability > strict enforcement)
- ✅ **Headers**: `X-RateLimit-*` + `Retry-After` for client backoff

### Common Cross-Questions

| Question | Strong Answer |
|----------|---------------|
| Why not enforce in each service? | API Gateway = single front door, one place to enforce, shared counter across all services |
| What if Redis goes down? | Circuit breaker: 10 failures → fail-open for 30s → auto-recover. Availability > strict limits |
| Why Token Bucket over Fixed Window? | Fixed Window has boundary spike (199 req in 2 sec). Token Bucket: smooth refill, no gaming |
| How do you handle policy updates? | Write-through: UPDATE Postgres + SET Redis + PUBLISH. Propagation <1 sec via Pub/Sub |
| Per-user or per-tenant quota? | Controlled by `enforce_by` field. USER_ID = each user separate. TENANT_ID = org shares quota |
| How do you prevent race conditions? | Lua script in Redis = atomic. Two gateways can't both see "1 token" and both allow |

---

## 🔗 Comparison: Original vs BEGINNER Diagrams

| Aspect | Original Diagrams | BEGINNER Diagrams |
|--------|------------------|-------------------|
| **Text size** | 10-12pt | 14-18pt (readable) |
| **Analogies** | None | Restaurant, tokens, fridge |
| **WHY boxes** | Few | Every component |
| **Color coding** | Minimal | Green=allowed, Red=rejected |
| **Timing** | Not shown | Exact ms per step |
| **Examples** | Abstract | Real (50M users, 100 req/min) |
| **Target** | 5+ YOE | College students, bootcamp grads |

---

## 📦 Next Steps

After mastering these diagrams:
1. Read the main interview guide: `Distributed_Rate_Limiter_Interview_Guide.md`
2. Practice drawing these from memory (whiteboard/iPad)
3. Watch the narrated architecture video for deeper insights
4. Compare with existing production systems (Stripe API docs, AWS API Gateway limits)

---

## ✨ What Makes These BEGINNER-Friendly?

✅ **Real-world analogies**: Restaurant host, token bucket as coins in a jar  
✅ **WHY explanations**: Not just "use Redis" but "Redis = 0.5ms, DB = 10-50ms"  
✅ **Step-by-step timing**: Shows exact latency added per operation  
✅ **Production examples**: AWS, Stripe, GitHub use Token Bucket  
✅ **Visual**: Green paths (allowed), Red paths (rejected), color-coded  
✅ **Beginner boxes**: Explains Lua script atomicity, enforce_by field, write-through cache  

Good luck with your interviews! 🚀
