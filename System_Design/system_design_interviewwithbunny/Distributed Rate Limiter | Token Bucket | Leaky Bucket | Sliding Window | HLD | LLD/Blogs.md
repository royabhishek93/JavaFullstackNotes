Pre-Interview Memory Refresher
20 min revision
Updated 2026-01-26
Bonus: beyond the video + interview questions
Rate Limiter System

"Client request → API Gateway checks auth → Rate Limiter queries Redis (token bucket/sliding window) → if allowed (tokens available) → forward to Backend → if exceeded → 429 Too Many Requests with retry-after header → Policy updates propagated via write-through cache"

1. Functional Requirements

Feature 1: Limit number of requests a client (by User ID / API Key / IP) can make within a time window
Feature 2: Rate limit rules must be configurable at runtime (update limits without redeployment)
Feature 3: When the limit is exceeded, return HTTP 429 Too Many Requests with retry-after header
Feature 4: Support different rate limits based on client tier (Free: 100 req/min, Premium: 1000 req/min)
Feature 5: Support different limiters per client tier (Free/Premium) with granular control
2. Non-Functional Requirements

Scale & Performance
Scale — 1 Million requests per second (rps) - high-traffic APIs
CAP — Availability >> Consistency (eventual consistency acceptable, slight over-limit tolerable)
Latency — Ultra low <5ms per request added latency (rate limit check must be fast, not bottleneck)
3. Core Entity

Entity 1: RateLimitPolicy/Rules - rule_id, subject_type (USER/API_KEY/IP), subject_value (specific user ID or global), limit (100 requests), window (60 seconds), endpoint (*/api/login for specific endpoint), created_at
Entity 2: Client - client_id, tier (FREE/PREMIUM), api_key, quota (rate limit), created_at
Entity 3: RequestCounter - Tracks request count per client per window, stored in Redis for fast access
4. API Designing

Admin Operations (Create rules)
POST /v1/admin/rules — Create rate limit rule with {subjectType, subjectValue, limit, window, endpoint}
GET /v1/admin/rules?clientId={xyz} (CRUD) — Get rate limit rules for specific client
Admin: GET /v1/admin/rate-limit/metrics?resource={url} — Get rate limiting metrics for monitoring
5. High Level Design (HLD)

Architecture: client → Load Balancer → Rate Limiter (with API Gateway) → Backend Svc (protected resources)
Load Balancer: Distributes traffic across multiple Rate Limiter instances, health checks
Rate Limiter + API Gateway: Core component, checks auth, queries Redis for rate limit state, enforces limits before forwarding
Backend Svc: Protected API services (multiple instances), only receives allowed requests
Algorithms supported: Fixed Window Counter, Sliding Window Log, Sliding Window Counter, Token Bucket (most common), Leaky Bucket
6. Deep Dive Design (Low Level - LLD)

Algorithm 1: Fixed Window Counter
How it works: Divide time into fixed windows (e.g., every 60s), count requests per window, reset counter at window boundary
Example: Window: 10:00:00-10:00:59, limit: 100 requests, at 10:00:10 → 50 requests → allow, at 10:00:58 → 99 requests → allow, at 10:01:00 → reset counter to 0 (new window starts)
Implementation: Redis key: rate_limit:{user_id}:{window_start_timestamp}, Value: request count (integer), Increment: INCR rate_limit:user123:1706270400 (window starting at Unix timestamp 1706270400), Set TTL: EXPIRE rate_limit:user123:1706270400 60 (auto-delete after window expires), Check: current_count = GET rate_limit:user123:1706270400, if current_count < limit → allow, else → reject 429
Pros: Simple + easy to implement, low memory (one counter per window), cons: boundary problem (spike at window edges: 99 requests at 10:00:59 + 100 requests at 10:01:00 = 199 requests in 2 seconds, violates spirit of 100/min limit)
Algorithm 2: Sliding Window Log
How it works: Store timestamp of every request, count logs in last N seconds (true sliding window)
Example: Current time: 10:00:45, window: 60s (last minute), stored timestamps: [10:00:05, 10:00:12, 10:00:30, ...], filter: only timestamps >= 10:00:45 - 60s = 09:59:45, count: 85 requests in last 60s, allow only if count < 100
Implementation: Redis sorted set (ZSET), Key: rate_limit_log:user123, Members: request_id (or UUID), Scores: timestamp (Unix time in seconds), Add request: ZADD rate_limit_log:user123 {current_timestamp} {request_id}, Remove old: ZREMRANGEBYSCORE rate_limit_log:user123 0 {current_timestamp - window_size} (cleanup logs older than window), Count: ZCOUNT rate_limit_log:user123 {current_timestamp - 60} {current_timestamp} → returns count in last 60 sec, if count < limit → ZADD (allow + store), else → reject 429
Pros: Highly accurate (true rolling window, no boundary problem), cons: expensive memory (stores every request timestamp, 100 req/min × millions users = massive storage), cleanup overhead
Algorithm 3: Sliding Window Counter
How it works: Hybrid of fixed window + sliding window, calculate weighted count from current window and previous window depending on how much current window has elapsed
Example: Current time: 10:00:45, Previous window (09:59:00-09:59:59): 80 requests, Current window (10:00:00-10:00:59): 30 requests, Elapsed in current window: 45 seconds (75% of 60s window), Weighted count: (previous_window_count × (1 - elapsed%)) + current_window_count = (80 × (1 - 0.75)) + 30 = (80 × 0.25) + 30 = 20 + 30 = 50 requests, if 50 < 100 → allow
Implementation: Two Redis keys: rate_limit:user123:{current_window}, rate_limit:user123:{previous_window}, Calculate: elapsed_pct = (current_time % window_size) / window_size, weighted_count = (prev_count × (1 - elapsed_pct)) + curr_count, if weighted_count < limit → INCR current window, else → reject
Pros: More accurate than fixed window (smooths boundary spikes), slightly more complex than fixed window, cons: not always some as typical API rate limiting expectation, approximation (not 100% accurate like sliding log)
Algorithm 4: Token Bucket (MOST COMMON - recommended)
How it works: Bucket contains tokens (capacity), tokens refill at steady rate (refill_rate tokens/sec), each request consumes one token, if tokens available → allow + consume, else → reject
Example: Capacity: 100 tokens, Refill rate: 10 tokens/sec (600 tokens/min = 100 req/10sec avg), Scenario: Burst: 100 requests in 1 sec (consumes all 100 tokens) → all allowed (burst supported), After 10 sec: bucket refilled to 100 tokens (10 tokens/sec × 10 sec), Steady: 10 req/sec sustained → allowed (matches refill rate)
Implementation (Redis Lua script for atomicity): local key = KEYS[1], local capacity = tonumber(ARGV[1]) -- 100, local refill_rate = tonumber(ARGV[2]) -- 10 tokens/sec, local now = tonumber(ARGV[3]) -- current timestamp, local tokens = tonumber(redis.call('HGET', key, 'tokens')) or capacity, local last_refill = tonumber(redis.call('HGET', key, 'last_refill')) or now, local elapsed = now - last_refill, local refilled = math.min(capacity, tokens + (elapsed * refill_rate)), if refilled >= 1 then redis.call('HSET', key, 'tokens', refilled - 1), redis.call('HSET', key, 'last_refill', now), redis.call('EXPIRE', key, 3600), return 1 -- allow, else return 0 -- reject
Pros: Supports bursts naturally (bucket capacity = burst size), smooth refill model (no sudden resets), widely used in real systems (AWS API Gateway, Stripe API), cons: Slightly more complex state management (track tokens + last_refill time)
Algorithm 5: Leaky Bucket
How it works: Requests enter bucket/queue, they leak out at fixed rate (processed), if bucket full → reject new requests
Example: Bucket capacity: 100 requests, Leak rate: 10 req/sec, Scenario: 50 requests arrive instantly → all queued in bucket, Leak: processes 10 req/sec (fixed rate), After 5 sec: all 50 processed, 100 requests arrive instantly → 100 queued (bucket full), 101st request → rejected (bucket full)
Implementation: Redis list (queue), LPUSH rate_limit_queue:user123 {request_id} (add to queue), LLEN rate_limit_queue:user123 → queue_size, if queue_size < capacity → allow (queue request), else → reject, Background processor: pops from queue at fixed rate (10/sec), RPOP rate_limit_queue:user123 → process request
Pros: Smooth output traffic (fixed processing rate), good for shaping traffic (prevent downstream overload), cons: Can delay/drop requests (not always ideal for synchronous APIs), more complex (requires queue + background processor), some OS typical API rate limiting expectation
Production Implementation (Token Bucket with Redis + Policy DB)
Architecture: Client → Load Balancer → API Gateway (Rate Limiter logic) → Rate Limiter/Policy Svc → Policy DB (rules) + Redis (token state)
Request flow: (1) Client: GET /api/users (with API key or user session), (2) API Gateway: Auth check (validate API key/JWT), Extract subject: user_id='user123' OR api_key='key_abc', Call Rate Limiter: check_rate_limit(user_id, endpoint='/api/users'), (3) Rate Limiter fetches policy: Policy Cache (Redis): GET policy:user123 → {limit: 100, window: 60, refill_rate: 10}, if cache miss → query Policy DB: SELECT limit, window FROM rate_limit_rules WHERE subject_value='user123' AND endpoint='/api/users', cache result: SET policy:user123 {limit, window, refill_rate} EX 3600 (1 hour TTL), (4) Check token bucket (Redis Lua script): EVAL lua_script 1 'rate_limit:user123' 100 10 {current_timestamp}, Returns: 1 (allow) or 0 (reject), (5) If allowed (1): Forward to Backend Svc, return response to client, If rejected (0): Return 429 Too Many Requests with headers: X-RateLimit-Limit: 100, X-RateLimit-Remaining: 0, X-RateLimit-Reset: 1712340788 (Unix timestamp when limit resets), Retry-After: 30 (seconds until retry allowed), Body: {error: 'rate_limit_exceeded', message: 'You have exceeded 100 requests/min. Retry after 30 seconds.'}
Policy updates (write-through cache): Admin updates rule: PUT /v1/admin/rules/{ruleId} {limit: 200}, Policy Svc: UPDATE rate_limit_rules SET limit=200, Invalidate cache: DEL policy:user123 (next request fetches new limit), OR write-through: SET policy:user123 {limit: 200, ...} (immediate update), Propagation: All Rate Limiter instances fetch new policy within 1 hour (cache TTL) OR immediately (if write-through + Redis pub/sub notification)
Multi-Tier Rate Limiting (Free vs Premium)
Tier-based rules: Free tier: limit=100 req/min, window=60s, endpoints=['*'] (all endpoints), Premium tier: limit=1000 req/min, window=60s, endpoints=['*'], Enterprise tier: limit=10000 req/min, custom limits per endpoint
Rule applies to all premium users but quota is tracked + scoped across entire tenant: subject_type='TIER', subject_value='PREMIUM' (shared quota for all premium users globally?), NO - typically per-user: subject_type='USER', subject_value='user123', lookup tier: SELECT tier FROM clients WHERE user_id='user123' → 'PREMIUM', fetch rule: SELECT limit FROM rate_limit_rules WHERE tier='PREMIUM' → 1000 req/min
Multi-level limiting: Per-user: 100 req/min (individual user limit), Per-IP: 1000 req/min (prevent single IP abuse), Per-API-key: 10000 req/min (API key quota), Per-endpoint: /api/login → 10 req/min (prevent brute force), Global: 1M req/sec (cluster capacity), Check all levels: if ANY limit exceeded → reject 429, enforce_by field indicates what the limit is scoped by (USER, IP, TENANT_ID, API_KEY) - tenant_id means the quota is shared across the entire tenant
7. Database Schema Details

Rate_limit_rules (Policy DB)
rule_id — uuid PRIMARY KEY
subject_type — enum (USER, API_KEY, IP, TIER, GLOBAL) - what the limit applies to
subject_value — varchar(255) - specific value (user_id='user123', api_key='key_abc', tier='PREMIUM', global='*')
endpoint — varchar(500) - API endpoint pattern ('*' for all, '/api/login' for specific, '/api/*' for prefix)
request_limit — int - number of requests allowed (100, 1000)
window_sec — int - time window in seconds (60 for 1 min, 3600 for 1 hour)
refill_rate — decimal(10,2) - for token bucket (10.0 tokens/sec)
enforce_by — varchar(50) - USER, IP, TENANT_ID (quota scope: per-user or shared across tenant)
created_at — timestamptz
Indexes — INDEX on (subject_type, subject_value, endpoint) for fast rule lookup
Clients
client_id — uuid PRIMARY KEY
api_key — varchar(255) UNIQUE (hashed for security)
tier — enum (FREE, PREMIUM, ENTERPRISE)
quota — int - rate limit (100 for FREE, 1000 for PREMIUM)
created_at — timestamptz
Redis - Token State (Token Bucket)
rate_limit:{subject}:{endpoint} — HASH - {tokens: 95, last_refill: 1706270445} (token count + last refill timestamp)
Example — rate_limit:user123:/api/users → {tokens: 95, last_refill: 1706270445}
TTL — 3600 sec (1 hour) - auto-expire inactive buckets to save memory
Lua script — Atomic check + decrement tokens, calculate refill based on elapsed time
Redis - Policy Cache
policy:{subject}:{endpoint} — STRING (JSON) - {limit: 100, window: 60, refill_rate: 10, enforce_by: 'USER'}
Example — policy:user123:/api/users → {limit: 100, window: 60, refill_rate: 10}
TTL — 3600 sec (1 hour) - cache policy rules, revalidate hourly or on invalidation
Write-through — On policy update → update DB + SET cache (immediate propagation)
Redis - Sliding Window Log (ZSET)
rate_limit_log:{subject} — ZSET - members: request_id (UUID), scores: timestamp (Unix time)
Operations — ZADD (add request), ZREMRANGEBYSCORE (cleanup old), ZCOUNT (count in window)
Memory — High - stores every request (not recommended for high-traffic APIs)
8. Scaling & Optimization

Technique 1: Redis Lua scripts for atomicity - Single atomic operation (check + decrement tokens), prevents race conditions (multiple requests checking simultaneously), faster than multiple Redis roundtrips
Technique 2: Policy caching - Cache rules in Redis (1 hour TTL), 99% cache hit rate (rules rarely change), reduces Policy DB load 100×, write-through on updates (immediate propagation)
Technique 3: Token Bucket algorithm - Supports bursts naturally (capacity = burst size), smooth refill (no boundary problem), production-proven (AWS, Stripe, GitHub all use token bucket)
Technique 4: Distributed rate limiting - Redis cluster (master + replicas), consistent hashing (route user123 to same shard), synchronization: Redis atomic operations ensure consistency across API Gateway instances
Technique 5: Multi-tier rate limiting - Check multiple levels (per-user, per-IP, per-endpoint, global), enforce strictest limit (if any exceeded → reject), tiered quotas (FREE: 100, PREMIUM: 1000, ENTERPRISE: 10K)
Technique 6: Horizontal scaling of API Gateway - Stateless API Gateway instances (10-100+), Redis shared state (all instances check same Redis), load balancer distributes requests, auto-scaling based on CPU/latency
Technique 7: Redis optimization - TTL for inactive buckets (auto-expire after 1 hour idle, saves memory), Pipelining (batch multiple Redis commands), Connection pooling (reuse connections, avoid handshake overhead)
Technique 8: Graceful degradation - If Redis down: Fail open (allow all requests, log error) OR fail closed (reject all with 503, safer but impacts availability), Circuit breaker (if Redis fails 10× → open circuit for 30 sec, skip Redis checks)
Technique 9: Rate limit headers - X-RateLimit-Limit: 100 (total quota), X-RateLimit-Remaining: 45 (remaining requests), X-RateLimit-Reset: 1712340788 (Unix timestamp when resets), Retry-After: 30 (seconds to wait), helps clients implement backoff
Technique 10: Monitoring & alerting - Track: Request count, rejection rate (% of 429 responses), Redis latency (p50, p99), policy cache hit rate, Alert: if rejection rate > 5% (potential attack or wrong limit), if Redis latency > 10ms (performance degradation)
Technique 11: Dynamic limit adjustment - Auto-scale limits based on load (if cluster at 80% capacity → reduce limits 20%), DDoS protection (if spike detected → temporary stricter limits), allowlist (trusted IPs bypass limits)
Technique 12: Write-through cache updates - On policy change: UPDATE DB + SET Redis cache (both in transaction), publish Redis pub/sub: PUBLISH policy_update {rule_id}, API Gateway instances subscribe, invalidate local cache, ensures <1 sec propagation (vs 1 hour with TTL)
9. Common Interview Questions

Q
Compare the 5 rate limiting algorithms (Fixed Window, Sliding Window Log, Sliding Window Counter, Token Bucket, Leaky Bucket). Which would you choose for a production API and why?
A
Comparison of 5 rate limiting algorithms:

(1) Fixed Window Counter: Pros: Simple (single counter per window), low memory (one int per user), fast (single INCR), Cons: Boundary problem (spike at edges: 100 req at 10:00:59 + 100 req at 10:01:00 = 200 req in 2 sec), Implementation: Redis INCR + EXPIRE, Use case: Simple internal APIs, not user-facing.

(2) Sliding Window Log: Pros: Highly accurate (true rolling window, no boundary issue), perfect precision, Cons: Expensive memory (stores every request timestamp: 100 req/min × 1M users = 100M timestamps), cleanup overhead (ZREMRANGEBYSCORE on each request), Implementation: Redis ZSET (ZADD, ZCOUNT, ZREMRANGEBYSCORE), Use case: Low-traffic critical APIs where accuracy crucial (fraud detection).

(3) Sliding Window Counter: Pros: More accurate than fixed window (smooths boundaries), lower memory than log (2 counters vs all timestamps), Cons: Approximation (not 100% accurate), complexity (weighted calculation), Implementation: Two counters (current + previous window), weighted sum, Use case: Good middle ground, not widely adopted (token bucket preferred).

(4) Token Bucket (RECOMMENDED): Pros: Supports bursts naturally (capacity = burst size, e.g., 100 token bucket allows 100 instant requests then refills), smooth refill (10 tokens/sec = steady 600/min), production-proven (AWS API Gateway, Stripe, GitHub), handles spiky traffic well, Cons: Slightly complex (track tokens + last_refill), Implementation: Redis HASH (tokens, last_refill) + Lua script (atomic check + refill calculation), Use case: Production APIs (most common choice).

(5) Leaky Bucket: Pros: Smooth output traffic (fixed processing rate), good for traffic shaping (prevent downstream overload), Cons: Can delay/drop requests (queuing), requires background processor (leak at fixed rate), not typical for sync APIs, Implementation: Redis LIST (queue) + background worker, Use case: Traffic shaping, not typical API rate limiting. Production choice: Token Bucket. Reasoning:

(1) Supports bursts: Users expect to make 100 requests instantly if quota available (e.g., batch operations), token bucket allows this, fixed/sliding window would reject after hitting limit in burst,

(2) Smooth refill: No sudden resets at window boundaries, users can make requests continuously at refill rate (10/sec),

(3) Industry standard: AWS, Stripe, GitHub all use token bucket, proven at scale (billions of requests/day),

(4) Good UX: Burst + refill feels natural to users,

(5) Reasonable complexity: Redis Lua script handles atomicity, not much more complex than fixed window. Implementation example (Token Bucket): Capacity: 100 tokens, Refill: 10 tokens/sec, Scenario: User makes 100 requests in 1 sec (burst) → all allowed (consumes all 100 tokens), After 5 sec: bucket refilled to 50 tokens (10 tokens/sec × 5 sec), User makes 50 requests → all allowed, User makes 51st request → rejected (bucket empty), After 1 sec: 10 tokens refilled, user can make 10 more requests. Result: Flexible (supports bursts), fair (smooth refill), production-ready (proven algorithm).

Q
How do you implement distributed rate limiting across multiple API Gateway instances using Redis? Handle race conditions and ensure consistency.
A
Distributed rate limiting with Redis:

(1) Challenge: Multiple API Gateway instances (10-100+), each handling 10K req/sec, all must enforce same limit (100 req/min per user), without coordination → race conditions (2 instances allow request simultaneously → user gets 101 requests in window).

(2) Redis as shared state: All API Gateway instances connect to same Redis cluster, Token state stored in Redis: rate_limit:user123 → {tokens: 95, last_refill: 1706270445}, Every rate limit check queries Redis (centralized truth).

(3) Race condition problem: Request 1 (Instance A): GET tokens → 1 token remaining, allow request, Request 2 (Instance B): Simultaneously GET tokens → also sees 1 token, also allows, DECR tokens (both execute), Result: tokens = -1 (over-limit, race condition!).

(4) Solution: Redis Lua script (atomic execution): lua_script = local key = KEYS[1], local capacity = tonumber(ARGV[1]), local refill_rate = tonumber(ARGV[2]), local now = tonumber(ARGV[3]), local bucket = redis.call('HMGET', key, 'tokens', 'last_refill'), local tokens = tonumber(bucket[1]) or capacity, local last_refill = tonumber(bucket[2]) or now, local elapsed = now - last_refill, local refilled = math.min(capacity, tokens + (elapsed * refill_rate)), if refilled >= 1 then redis.call('HMSET', key, 'tokens', refilled - 1, 'last_refill', now), redis.call('EXPIRE', key, 3600), return 1 -- allow, else return 0 -- reject, end, API Gateway call: result = redis.eval(lua_script, 1, 'rate_limit:user123', 100, 10, current_timestamp), Atomicity: Lua script runs as single atomic operation in Redis, no other command can interleave, guarantees: only one instance decrements token, race condition prevented.

(5) Consistency guarantees: Redis single-threaded execution: Commands processed serially (one at a time), Lua scripts: Execute atomically (all-or-nothing), even across Redis Cluster, Result: Distributed consistency without locks, CAP tradeoff: CP within Redis (consistent), AP across system (if Redis down, fail open for availability).

(6) Redis Cluster (horizontal scaling): Multiple Redis shards (master + replicas), Consistent hashing: hash(user_id) → shard (user123 always routes to same shard), Read from replicas: GET operations can use replicas (reduce master load), Write to master: EVAL (Lua script) must go to master (consistency), Replication lag: <1ms (acceptable slight over-limit during lag).

(7) Performance optimization: Connection pooling: Each API Gateway maintains 50 Redis connections (reuse, avoid handshake), Pipelining: Batch multiple rate limit checks (if checking 10 users → send 10 EVAL in one round-trip), Redis latency: p99 <5ms (fast enough for rate limiting, doesn't bottleneck API), Local cache: Cache policy rules (limit, refill_rate) locally (avoid Redis query for policy, only check token state).

(8) Failure handling: Redis unavailable: Circuit breaker: After 10 consecutive Redis failures → open circuit for 30 sec, During open circuit: Fail open (allow all requests, log error) OR fail closed (reject with 503), Auto-recovery: After 30 sec → half-open (try one request), if succeeds → close circuit (resume normal), Monitoring: Alert if Redis errors > 1% (investigate), track latency (if p99 > 10ms → scaling issue).

(9) Multi-region: Redis in each region: us-east-1, eu-west-1, asia-south-1 (low latency), Global rate limit: Aggregate across regions (complex, eventual consistency), OR per-region limit: 100 req/min per region (simpler, slightly relaxed global limit). Result: Distributed rate limiting with strong consistency (Redis atomic Lua), scales horizontally (Redis Cluster + multiple API Gateways), low latency (<5ms), handles failures gracefully (circuit breaker).

Q
Walk through complete request flow: client makes request → rate limiter checks → either allowed or rejected. Include policy lookup, token bucket check, and 429 response with headers.
A
Complete rate limiting flow (Token Bucket):

(1) Client request: GET /api/users (with header: Authorization: Bearer {jwt_token}), Load Balancer: Routes to API Gateway instance (round-robin).

(2) API Gateway authentication: Extract JWT: Parse token, validate signature, extract user_id: 'user123', (or extract api_key from header: X-API-Key).

(3) Rate Limiter: Identify subject: user_id='user123', endpoint='/api/users', Fetch policy (with caching): Check Redis cache: policy:user123:/api/users, if cache hit: policy = {limit: 100, window: 60, refill_rate: 10, enforce_by: 'USER'}, if cache miss: Query Policy DB: SELECT limit, window, refill_rate, enforce_by FROM rate_limit_rules WHERE (subject_type='USER' AND subject_value='user123' AND endpoint='/api/users') OR (subject_type='USER' AND subject_value='user123' AND endpoint='*') OR (subject_type='TIER' AND subject_value=(SELECT tier FROM clients WHERE user_id='user123') AND endpoint='*'), Fetch first matching rule (specific endpoint > wildcard, user > tier), Cache: SET policy:user123:/api/users {limit: 100, window: 60, refill_rate: 10} EX 3600.

(4) Token Bucket check (Redis Lua script): Prepare: key = 'rate_limit:user123:/api/users', capacity = 100, refill_rate = 10, now = current_unix_timestamp, Execute: result = redis.eval(lua_script, 1, key, capacity, refill_rate, now), Lua script logic: Fetch bucket: tokens, last_refill = redis.call('HMGET', key, 'tokens', 'last_refill'), Calculate refill: elapsed = now - last_refill (e.g., 5 seconds since last request), refilled = min(capacity, tokens + elapsed × refill_rate) = min(100, 90 + 5×10) = min(100, 140) = 100 tokens (capped at capacity), Check: if refilled >= 1 (100 >= 1 → true), Consume: tokens = 100 - 1 = 99, Update: redis.call('HMSET', key, 'tokens', 99, 'last_refill', now), Return: 1 (allow).

(5) Request allowed: result = 1 (allow), Calculate remaining: remaining = 99 tokens, Calculate reset time: reset = now + (capacity - remaining) / refill_rate = now + (100 - 99) / 10 = now + 0.1 sec (when bucket fully refilled), Forward request: Proxy to Backend Svc: GET /api/users, Add headers: X-RateLimit-Limit: 100, X-RateLimit-Remaining: 99, X-RateLimit-Reset: {reset_timestamp}, Backend response: {users: [...]}, Forward to client: 200 OK with data + rate limit headers.

(6) Request rejected (if no tokens): Scenario: User already made 100 requests in last 10 sec, tokens = 0, Lua script: refilled = min(100, 0 + 0×10) = 0 (no refill yet, too soon), Check: refilled >= 1 → false, Return: 0 (reject),

(7) Return 429 Too Many Requests: Status: 429 Too Many Requests, Headers: X-RateLimit-Limit: 100, X-RateLimit-Remaining: 0, X-RateLimit-Reset: 1712340788 (Unix timestamp when bucket refills to 1 token), Retry-After: 1 (seconds until retry allowed, ceil((1 - 0) / 10) = 1 sec), Body (JSON): {error: 'rate_limit_exceeded', message: 'You have exceeded 100 requests per minute. Retry after 1 second.', limit: 100, remaining: 0, reset_at: '2024-04-05T10:01:28Z'}, Client behavior: Receive 429, parse Retry-After: 1, wait 1 second, retry request → likely succeeds (1 token refilled).

(8) Monitoring: Log rate limit events: {user_id, endpoint, allowed: false, tokens_remaining: 0, timestamp}, Metrics: Increment counter: rate_limit_rejections.incr(labels={endpoint='/api/users', tier='FREE'}), Track: Rejection rate (% of requests rejected), per-endpoint breakdown, Dashboard: Alert if rejection rate > 5% (potential attack or misconfigured limit). Result: Complete flow with policy caching (fast lookup), atomic token check (race-free), proper 429 response (helps client implement backoff), monitoring (visibility into rate limiting).

Key Interview Tips

⚠️
CRITICAL: Use Redis Lua scripts for atomic rate limit checks. NEVER use separate GET + DECR (race condition: 2 instances both GET → both see 1 token → both DECR → over-limit). Lua script executes atomically in Redis (single-threaded), prevents races across distributed API Gateways.

⭐
Token Bucket is production standard (AWS, Stripe, GitHub). Supports bursts (capacity=100 allows 100 instant requests), smooth refill (10 tokens/sec), no boundary problem. Implementation: Redis HASH {tokens, last_refill} + Lua script (atomic check + refill calculation based on elapsed time).

💡
Fixed Window has boundary problem: 100 req at 10:00:59 + 100 req at 10:01:00 = 200 req in 2 sec (violates 100/min spirit). Token Bucket avoids this with continuous refill. Sliding Window Log is accurate but expensive (stores every timestamp, high memory).

⭐
429 response must include headers: X-RateLimit-Limit (quota), X-RateLimit-Remaining (left), X-RateLimit-Reset (Unix timestamp when resets), Retry-After (seconds to wait). Helps clients implement exponential backoff, avoid hammering API.

⚠️
NEVER store rate limit state locally in API Gateway memory (lost on restart, no consistency across instances). MUST use Redis (centralized state, atomic operations). Redis down → circuit breaker: fail open (allow all, log) OR fail closed (reject with 503, safer).

💡
Cache policy rules in Redis (1 hour TTL, 99% hit rate). Write-through on updates: UPDATE DB + SET cache + PUBLISH Redis pub/sub → API Gateways invalidate local cache within <1 sec. Avoids stale limits for 1 hour (TTL-only approach).

⭐
Multi-tier limiting: Check per-user (100/min), per-IP (1000/min), per-endpoint (login: 10/min), global (1M/sec cluster capacity). Enforce strictest limit (if ANY exceeded → 429). Prevents abuse at multiple levels (user quota + IP-based DDoS protection + endpoint brute-force prevention).