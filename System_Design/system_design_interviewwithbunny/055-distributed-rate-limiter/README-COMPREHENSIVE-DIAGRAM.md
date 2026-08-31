# Distributed Rate Limiter — Comprehensive Landscape Diagram

This single Draw.io file contains a **1920×1080 landscape** system design diagram with 7 integrated sections:

## 📐 Diagram Sections

### 1. **BIG PICTURE** (Top Strip)
- **Title**: Distributed Rate Limiter — System Design
- **Challenge Statement**: Enforce quotas across distributed instances without race conditions at 1M RPS
- **Write Path**: Client → API GW → Redis EVAL Lua → 200 OK (1M req/sec)
- **Read Path**: API GW → Redis cache (99% hit, 1hr TTL) → PostgreSQL fallback (<0.5ms avg)

### 2. **HIGH-LEVEL ARCHITECTURE** (Left-Center, Largest Section)
**Components:**
- 🌐 Client layer
- ⚖️ Load Balancer
- 🚪 API Gateway instances (stateless, distributed)
- ⚡ Redis Cluster (8 shards, shared state)
- 🗄️ PostgreSQL (policy storage)
- 🔧 Backend Services (UserSvc, OrderSvc, PaymentSvc, SearchSvc)
- 📊 Monitoring & Alerting

**Why Boxes:**
- WHY SHARED REDIS? → 40 instances with local counters = 4000/min instead of 100/min
- WHY LUA SCRIPT? → Prevents race condition from GET+DECR separation
- TOKEN BUCKET VISUAL → Shows refill mechanism and burst behavior

**Comparisons:**
- Algorithm comparison (Token Bucket ✅, Fixed Window ❌, Leaky Bucket ⚠️)
- Circuit breaker strategy
- Multi-level limits (per-user, per-IP, per-endpoint, global)

### 3. **LOW-LEVEL DESIGN** (Right-Center)
**Step-by-step Token Bucket flow:**
1. Extract client identity (JWT → user_id)
2. Lookup policy (Redis cache GET)
3. Cache miss? Fetch from PostgreSQL + write-through
4. Execute Lua script (atomic: read → calculate refill → deduct → write)
5. Decision: allow or reject
6. ALLOW: Forward + add X-RateLimit headers
7. REJECT: Return 429 + Retry-After

**Lua Script Visualization:**
- Complete atomic script showing read, refill calculation, deduction logic
- Single-threaded Redis execution prevents race conditions

### 4. **DATABASE SCHEMA** (Bottom-Left)
**PostgreSQL Tables:**
- `clients`: client_id, api_key, tier, quota
- `rate_limit_rules`: rule_id, subject_type, algorithm, request_limit, window_sec, burst_capacity, refill_rate, enforce_by

**Redis Key Patterns:**
- Token State (HASH): `rate_limit:user123:/api/users` → `{tokens:95, last_refill:ts}`
- Policy Cache (JSON): `policy:user123:/api/users` → `{limit:100,refill:10,burst:100}`
- Sliding Window (ZSET): For SWL algorithm only

### 5. **TECHNOLOGIES USED** (Right Panel)
| Component | Technology | Why This Choice? |
|-----------|-----------|------------------|
| ⚡ Cache | Redis Cluster | In-memory, <1ms p99, Lua atomicity |
| 🗄️ Policy DB | PostgreSQL | ACID, relational integrity, fast INDEX |
| ⚙️ Algorithm | Token Bucket | Burst support, low memory, production-proven |
| 🔒 Atomicity | Lua Scripts | Single-threaded, no race conditions |
| 📡 Policy Sync | Redis Pub/Sub | <1sec propagation, event-driven |
| 🔌 Resilience | Circuit Breaker | Fail open (availability > strict limiting) |

### 6. **LATENCY BUDGET** (Bottom-Center)
**p95 Breakdown:**
- Extract client identity: 0.1ms
- Policy cache lookup: 0.5ms
- Lua script EVAL: 1.0ms
- Network roundtrip: 1.0ms
- Header injection: 0.1ms
- **TOTAL: 2.7ms** ✅ (target <5ms)

**Cache miss penalty:** +10ms (only 1% of requests)

### 7. **SCENARIO QUESTIONS** (Bottom-Right)
**5 Critical Interview Q&As:**
1. **Race conditions?** → Redis Lua script (atomic execution)
2. **Token vs Leaky Bucket?** → Token=burst allowed, Leaky=smooth output
3. **Redis failure?** → Circuit breaker, fail open (availability>strict)
4. **Multi-region?** → Per-region limits (simplest) vs Global Redis
5. **Fixed vs Sliding Window?** → Fixed has boundary spike exploit

**Key Takeaways:**
- Centralized Redis = shared state
- Lua script = atomic, no races
- Token Bucket = burst + low memory
- Fail open = availability first
- Multi-level limits = comprehensive protection

## 🎯 Scale Numbers
- **1M req/sec** across cluster
- **50M active users**
- **<5ms added latency**
- **8 Redis shards** (consistent hashing)
- **40 API Gateway instances** (stateless)
- **99% cache hit rate** (1hr TTL)

## 🖥️ How to View

**Option 1: Online (Recommended)**
1. Go to [diagrams.net](https://app.diagrams.net)
2. File → Open → select `distributed-rate-limiter-comprehensive.drawio`
3. View in landscape mode (1920×1080)

**Option 2: VS Code**
1. Install "Draw.io Integration" extension
2. Click the `.drawio` file
3. Use zoom controls to see all sections

**Option 3: Desktop App**
1. Download [draw.io desktop](https://github.com/jgraph/drawio-desktop/releases)
2. Open the file
3. Export to PNG/SVG for presentations

## 💡 Export for Presentations

1. File → Export as → PNG
2. Settings:
   - **Width:** 1920px
   - **Transparent:** No
   - **Border:** 10px
   - **DPI:** 300 (for print quality)

## 📝 Based On

This diagram synthesizes the complete [Distributed_Rate_Limiter_Interview_Guide.md](./Distributed_Rate_Limiter_Interview_Guide.md):
- All algorithms (Token Bucket, Leaky Bucket, Fixed/Sliding Window)
- Production architecture patterns (AWS API Gateway, Stripe, GitHub)
- Senior trap questions and answers
- Capacity estimation and scaling strategies
- LLD code patterns (Strategy Pattern, Lua scripts)

---

**Created:** 2026-08-30  
**Format:** Draw.io XML (mxGraph schema)  
**Dimensions:** 1920×1080 landscape  
**Sections:** 7 integrated views
