# Designing a Rate Limiter System (LLD)

## Requirements
1. Limit requests by user, IP, API key, tenant, or endpoint.
2. Support multiple algorithms: fixed window, sliding window, token bucket.
3. Work in a distributed environment across many app servers.
4. Provide low-latency allow/deny decisions.
5. Support different plans and quotas per tenant.
6. Handle bursts gracefully.
7. Expose remaining quota and reset time.
8. Provide observability and auditability.

## Core Components
1. Policy Service
- Stores rate limit rules by scope and endpoint.
- Supports plan-based overrides.

2. Decision Engine
- Evaluates the correct algorithm for a request.
- Returns allow/deny plus remaining tokens.

3. Counter Store
- Usually Redis for atomic increments and expiry.
- Optionally local in-memory cache for hot paths.

4. Config Cache
- Caches policies close to application nodes.

5. Metrics Pipeline
- Tracks throttled requests, hot keys, and saturation.

6. Admin Service
- Allows policy updates, exemptions, and emergency overrides.

## Core Entities
1. RateLimitPolicy
- id, scopeType, scopeValue, endpointPattern, algorithm, limitValue, windowSec, burstLimit

2. RateLimitCounter
- key, currentValue, windowStart, expiresAt

3. ThrottleEvent
- id, requestKey, decision, reason, endpoint, createdAt

4. QuotaOverride
- id, tenantId, endpointPattern, temporaryLimit, expiresAt

## APIs
- POST /v1/rate-limit/check
- GET /v1/rate-limit/policies
- POST /v1/rate-limit/policies
- PUT /v1/rate-limit/policies/{id}
- POST /v1/rate-limit/overrides

## Algorithms
1. Fixed Window
- Simple but can allow boundary burst.

2. Sliding Window Log
- Accurate but storage-heavy.

3. Sliding Window Counter
- Better trade-off for distributed systems.

4. Token Bucket
- Best when bursts are allowed but average rate must stay bounded.

## Decision Flow
1. Derive request key: tenant:user:endpoint.
2. Load effective policy.
3. Atomically update/check counter in Redis.
4. Return allow/deny with metadata.
5. Emit throttle metrics if denied.

## Concurrency Strategy
- Use Redis atomic ops or Lua script for consistent updates.
- Avoid race conditions by doing read-modify-write on server side in one operation.
- For local fallback mode, use approximate counters only for best-effort protection.

## Failure Scenarios
1. Redis unavailable
- Fail-open for low-risk APIs or fail-closed for high-risk APIs.
- Decision depends on endpoint criticality.

2. Hot key for one abusive tenant
- Add key hashing, local pre-filter, or dedicated shard.

3. Policy updated mid-window
- Apply new policy immediately to new checks; counters may continue until expiry.

## Interview One-Liner
The hard part is not the algorithm alone; it is making the decision correct and cheap under distributed contention.
