# Interview Approach - Rate Limiter System LLD

## 1. Start With Intent
"A rate limiter protects fairness and capacity, but the wrong policy can also break legitimate traffic."

## 2. Define Core Guarantees
- Consistent enforcement across nodes
- Bounded burst behavior
- Tenant/endpoint-specific policies
- Low-latency decisions

## 3. Walk Through Happy Path
1. Request arrives.
2. Build rate-limit key.
3. Fetch policy from cache.
4. Evaluate algorithm in Redis/Lua.
5. Return allow/deny with headers.

## 4. Walk Through Failure Path
1. Counter store unavailable.
2. Decide fail-open vs fail-closed.
3. Emit alert and degrade safely.

## 5. Mention Scale Levers
- Redis clustering
- Hot-key sharding
- Local token warm cache
- Separate write-heavy throttle logs from decision path

## 6. Trade-offs
- Token bucket for burst tolerance
- Sliding window for fairness/accuracy
- Fixed window for simplicity

## 7. Close Strongly
"In production, the design choice is mostly about fairness, latency, and failure semantics, not just textbook algorithm names."
