# Timeout Strategy
### What Timeout Value to Set — Why Too Short = False Failures, Too Long = Cascade

---

## PART 1 — THE STUDENT CONVERSATION

**Every network call needs a timeout. The question is: how long?**

Too short: your service is healthy and fast, but occasionally takes 300ms instead of 200ms due to a GC pause. Your caller times out at 250ms. From the caller's perspective, the service "failed." It retries. The service did the work twice. You have a false failure — a healthy service looked dead because of a too-tight timeout.

Too long: your downstream service is hanging — perhaps it's overloaded or deadlocked. You set a 60-second timeout. You have 200 threads. Each waits 60 seconds. Within a few minutes, all 200 threads are blocked waiting for a service that will never respond. Your entire service hangs. **Cascade failure.**

The right timeout is: **slightly above the 99th percentile latency of the downstream call under normal operation.**

If 99% of calls complete in 500ms, set timeout at 750ms–1000ms. This allows reasonable variance while failing fast when something is truly wrong.

---

## PART 2 — THE CASCADE FAILURE DIAGRAM

```
Without proper timeouts:
──────────────────────────────────────────────────────────────────

  User → API Gateway → Order Service → Payment Service (hanging, 60s timeout)

  t=0s:    1 thread stuck on Payment (60s timeout)
  t=1s:    17 threads stuck (17 req/sec × 1s each)
  t=60s:   200 threads stuck (thread pool exhausted at ~200 × 1/60 = ~3.3 req/sec fill rate)
  t=60s:   All requests to Order Service queue → timeout → HTTP 504

  API Gateway now: Order Service is timing out. Alarm fires.
  On-call engineer investigates: Order Service appears down.
  But Order Service is fine — it's Payment Service that's hanging.
  RCA takes 30 minutes to identify the real culprit.

  Total blast radius: entire checkout flow down for 60s worth of Payment hangs.

With 1s timeout on Payment call:
  t=0s:    1 thread calls Payment.
  t=1s:    Thread times out. Returns error to user. Thread released back to pool.
  t=1s:    A new request can use that thread.
  Thread pool never exhausts.
  Circuit breaker: 50% failures in last 10 calls → OPEN → fallback returned immediately.
  Blast radius: checkout fails gracefully (payment error), but browse/cart/recommendations OK.
```

---

## PART 3 — THE TIMEOUT LAYERS (IMPORTANT!)

```
Every network call has MULTIPLE timeout layers. All must be configured:
──────────────────────────────────────────────────────────────────

Client-side (your service calling downstream):
  ┌─────────────────────────────────────────────────────────────────┐
  │  Connection Timeout: time to establish TCP connection           │
  │  (typical: 500ms–2s)                                            │
  │  If exceeded: "cannot connect" → server not reachable           │
  │                                                                  │
  │  Read Timeout: time to receive response AFTER connected         │
  │  (typical: 1s–5s depending on operation)                        │
  │  If exceeded: "response took too long" → server hung            │
  │                                                                  │
  │  Total Request Timeout: overall end-to-end budget               │
  │  (covers retries + all timeouts combined)                        │
  └─────────────────────────────────────────────────────────────────┘

Database timeout:
  ┌─────────────────────────────────────────────────────────────────┐
  │  Connection pool wait timeout: time to get connection from pool │
  │  (typical: 5s — HikariCP connectionTimeout)                     │
  │                                                                  │
  │  Query timeout: time for DB query to execute                    │
  │  (typical: 5–30s depending on query)                            │
  │                                                                  │
  │  Transaction timeout: max time for an open transaction          │
  │  (typical: 30s — prevents lock holders from sitting forever)    │
  └─────────────────────────────────────────────────────────────────┘

Upstream (protecting yourself from slow callers):
  ┌─────────────────────────────────────────────────────────────────┐
  │  API Gateway timeout: max time before Gateway returns 504       │
  │  (typical: 5–30s for user-facing APIs)                          │
  │                                                                  │
  │  Load Balancer idle timeout: AWS ALB default = 60s              │
  └─────────────────────────────────────────────────────────────────┘

The timeout CHAIN:
  API Gateway (29s) → Order Service (25s) → Payment Service (5s)
  Parent timeout must be LONGER than child.
  If Payment timeout = 5s and Order timeout = 3s:
  Payment call might get 5s but Order Service gives up at 3s → orphaned call on Payment.
```

---

## PART 4 — THE DEADLINE PROPAGATION PATTERN

```
Problem: distributed timeout accounting.

  Client gives API Gateway 10 seconds.
  API Gateway calls Order Service: doesn't tell it "you have 10s."
  Order Service calls Payment Service: doesn't tell it "you have 8s left."
  Payment Service takes 7 seconds.
  Order Service returns at 9 seconds.
  API Gateway had already timed out at 10s → returns 504.
  Meanwhile: payment was actually processed! But user got a 504!
  User retries. Gets charged twice (if no idempotency key).

Fix: pass deadline in headers (gRPC does this natively):

  API Gateway → Order Service:
    Header: X-Request-Deadline: 1704067210.500  (unix timestamp of when this request expires)

  Order Service → Payment Service:
    Header: X-Request-Deadline: 1704067210.500  (same deadline, propagated)

    Before calling Payment:
    remaining = deadline - now()
    if remaining < 200ms: don't even call, return error immediately
    else: set payment call timeout = min(5s, remaining - 100ms buffer)

  This way: no orphaned calls to downstream after client already gave up.
  gRPC handles this automatically via context deadlines.
  HTTP: implement manually or use a tracing library (Zipkin, Jaeger propagate deadlines).
```

---

## PART 5 — THE INTERVIEW CONVERSATION

**Interviewer:** "What timeout do you set for a call from Order Service to Payment Service?"

**You (architect answer):**

> "I start by looking at the P99 latency of the Payment Service in production under normal load.
> If P99 is 300ms, I set the read timeout at 500–750ms — enough headroom for occasional slow
> responses without waiting forever.
>
> But timeout isn't just one value. I configure three independently:
>
> Connection timeout: 500ms — if I can't establish a TCP connection in 500ms, the payment
> server is unreachable. No point waiting longer.
>
> Read timeout: 750ms — if the connection is established but no response in 750ms, something
> is wrong. Payment Service usually responds in 100–300ms.
>
> And I propagate the upstream deadline: if the API Gateway gave me 10 seconds total, I don't
> blindly call Payment with a 750ms timeout 5 times. I track how much of the budget remains
> and won't attempt the call if less than 200ms is left.
>
> The pair to timeout is the circuit breaker. If 50% of calls are timing out, the circuit opens
> and I stop calling Payment entirely, returning a 'payment temporarily unavailable' error
> immediately. This protects my thread pool from filling up with timed-out threads.
>
> For the Database: query timeout at 5 seconds, transaction timeout at 30 seconds, connection
> pool wait at 5 seconds. These prevent a long-running query or forgotten open transaction
> from holding locks indefinitely."

---

## PART 6 — TIMEOUT VALUES BY USE CASE

```
Service call type          │ Connection timeout │ Read timeout  │ Notes
───────────────────────────┼────────────────────┼───────────────┼───────────────────────────
Internal microservice call │ 500ms              │ 1–2s          │ Internal network is fast
Payment gateway (Stripe)   │ 2s                 │ 5s            │ External, slightly slower
Fraud scoring (real-time)  │ 500ms              │ 500ms         │ Must be fast or skip
Email service (async)      │ 1s                 │ 3s            │ Can queue on failure
S3 file upload             │ 2s                 │ 30–120s       │ Large files take time
DB query (OLTP)            │ pool=5s            │ 5–10s         │ Short queries only
DB query (reporting)       │ pool=5s            │ 30–300s       │ Analytics are slow
External geolocation API   │ 1s                 │ 2s            │ Fail gracefully

API Gateway by endpoint:
  /search (read): 5s
  /checkout (critical write): 15s  (give more room for retries)
  /recommendations (optional): 2s  (fail fast, not critical)
  /download (file): 300s

Rule of thumb:
  User-facing, synchronous: P99 + 50% headroom
  Background job: P99 × 3 (can tolerate some slow runs)
  Never: no timeout (unbounded wait = eventual cascade)
```

---

## QUICK REFERENCE CARD

```
Too short: false failures (healthy service looks dead) → unnecessary retries → load increase
Too long:  thread starvation → cascade failure → everything down

Right value: P99 latency of downstream service + 50% buffer

Three timeouts to always configure:
  Connection timeout: 500ms–2s (TCP handshake)
  Read timeout:       P99 + 50% buffer (actual response wait)
  Total/request budget: parent deadline propagation

Timeout chain rule:
  Parent timeout > child timeout + overhead
  API GW (29s) → Service A (25s) → Service B (5s)

Always combine with:
  Circuit breaker → if timeouts are frequent, stop calling
  Bulkhead        → limit threads blocked on any one downstream
  Retry + Jitter  → retry once or twice with backoff after timeout

Deadline propagation:
  Pass X-Request-Deadline header downstream
  Abort call if remaining budget < minimum_useful_time
  gRPC: built-in via context.WithDeadline()

Interview one-liner:
"Too short a timeout causes false positives — healthy services look dead.
Too long causes cascade — slow services exhaust your thread pool.
Right timeout = P99 + buffer. Pair it with circuit breaker so when
timeouts are frequent, you stop calling the service and return a fallback."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Every service-to-service call in your design needs a timeout — interviewers will ask "what timeout would you set?" and this is how you answer with numbers and reasoning, not guesses.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **07 — Payment** | Bank gateway SLA: P99 = 800ms. Set timeout = 1200ms (P99 + 50% buffer). Too short (200ms): false failures on legitimate slow payments during peak. Too long (10s): failed payments occupy thread pool slots for 10s each → thread pool exhaustion cascade. |
| **08 — Food Delivery** | Restaurant confirmation API: 3s total timeout. If no confirmation in 3s → auto-accept and SMS restaurant. Deadline propagated: parent 5s budget → 3s for restaurant call → 2s remaining for driver assignment. |
| **09 — E-Commerce** | Recommendation service: 200ms timeout (non-critical — show empty section if slow). Cart service: 2s timeout (critical — must complete). Timeouts proportional to the feature's criticality and user impact. |

**Architect's one-liner for the interview:**
*"Set timeout at P99 latency plus a buffer — too short creates false failures, too long creates cascades; pair with a circuit breaker so repeated timeouts stop the call entirely."*
