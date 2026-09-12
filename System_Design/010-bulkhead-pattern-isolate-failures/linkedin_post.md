# Bulkhead Pattern — LinkedIn Post

## Post Text (copy-paste ready)

Recommendation Service slowed down. Checkout broke. Payment Service was perfectly healthy the whole time.

- A shared thread pool is a single point of failure for EVERY service that uses it — one slow dependency exhausts the pool for all of them
- Bulkhead pattern (named after ship compartments): give each downstream service its own dedicated thread pool, so one flooding compartment can't sink the ship
- Sizing formula: pool size = (requests/sec × avg latency in seconds) × 1.2 safety factor — Payment at 500 req/s × 200ms = 120 threads
- Keep queue capacity small (5-10) or zero — a big queue just delays the failure and hides the real problem; reject fast and return a fallback instead
- Never use bulkhead alone — pair it with a circuit breaker so you stop even attempting calls once a service is clearly broken

Swipe → to see thread-pool vs semaphore isolation compared, and the exact sizing math for critical vs non-critical services.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
A slow recommendation service broke checkout — even though payment was 100% healthy. Here's the fix: bulkhead isolation 👇

### Variant B — Long (400–600 chars)
When multiple downstream services share one thread pool, a slowdown in ANY of them can exhaust that pool for ALL of them — a healthy Payment Service goes down because a slow Recommendation Service ate every thread. Bulkhead pattern fixes this by giving each dependency its own isolated thread pool, sized with (requests/sec × avg latency) × 1.2. Keep queues small so failures surface fast instead of hiding behind a growing backlog, and always pair bulkheads with a circuit breaker.

---

## Best Time to Post
Monday, 9:00–10:00 AM IST (resilience-pattern content performs well opening the work week)

## Engagement Hook
"Has a shared thread pool ever caused an unrelated service to fail in your systems? What tipped you off?"
