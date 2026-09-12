# Retry with Exponential Backoff and Jitter
### Why Retrying Immediately Makes It Worse — What Jitter Does

---

## PART 1 — THE STUDENT CONVERSATION

**The problem: service fails. Retry immediately. Service is still failing. Retry again. And again. All at the same time.**

Imagine a restaurant has a 5-minute wait. 100 people are told "come back later." All 100 leave, wait exactly 5 minutes, and all walk back in at the same moment. The restaurant is now overwhelmed with 100 people arriving simultaneously. Same problem all over again.

That's what happens when distributed systems retry without backoff and jitter. A downstream service goes down momentarily. Thousands of callers get an error. They all retry at t=1 second. Service gets slammed by all of them at once — still can't recover. They all retry at t=1 second again. **Thundering herd.** The retry storm is worse than the original failure.

**Exponential backoff:** wait longer between each retry. First retry: 1s. Second retry: 2s. Third: 4s. Fourth: 8s. The delay doubles (or multiplies by a factor). This gives the downstream service progressively more time to recover.

**Jitter:** add randomness to the backoff delay. Instead of everyone waiting exactly 4s before the third retry, each caller waits between 2s and 6s. Retries are spread out over time. No thundering herd.

---

## PART 2 — THE DIAGRAMS

### Without Backoff (Immediate Retry)

```
1000 clients, downstream service goes down at t=0:
──────────────────────────────────────────────────────────────────

t=0s:    1000 requests fail.
t=1s:    1000 retries arrive simultaneously → service still down, 1000 fail.
t=2s:    1000 retries → fail.
t=3s:    1000 retries → fail.
t=4s:    Service tries to recover → gets hit by 1000 requests → overwhelmed again → fails.
t=5s:    1000 retries → fail.
         ...

  Request load on downstream service:
  ████████████████████████████████ ← constant hammering, service can never recover
  t=0    t=1    t=2    t=3    t=4
```

### With Exponential Backoff (No Jitter)

```
1000 clients, same scenario:
──────────────────────────────────────────────────────────────────

t=0s:    1000 requests fail.
t=1s:    1000 retries arrive simultaneously → fail. (base delay = 1s)
t=3s:    1000 retries arrive simultaneously → fail. (2s wait after 2nd fail = t=1+2=3)
t=7s:    1000 retries arrive simultaneously → fail. (4s wait after 3rd fail = t=3+4=7)
t=15s:   1000 retries arrive simultaneously → fail. (8s wait)

  Better: service gets breathing room between waves.
  Still bad: all 1000 arrive at the EXACT same moment each wave.
  Service may recover between waves but gets slammed again on each retry spike.

  Request load:
  ████        ████        ████        ████
  t=0         t=1         t=3         t=7
  spike      spike       spike       spike
```

### With Exponential Backoff + Jitter (Best)

```
Each client picks: delay = random_between(0, base_delay * 2^attempt)
──────────────────────────────────────────────────────────────────

t=0s:    1000 requests fail.
t=0–2s:  1000 retries spread randomly across 2-second window.
          ~50 requests per 100ms. Service sees gentle load.
t=2–6s:  1000 retries spread across 4-second window.
          ~25 requests per 100ms. Service has more breathing room.
t=6–14s: 1000 retries spread across 8-second window.
          ~12 requests per 100ms. Very gentle.

  Request load:
  ▓▓▓▓▓▓▓▓    ▓▓▓▓▓▓▓▓▓▓▓▓    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
  t=0–2       t=2–6           t=6–14
  spread      spread          spread

  Service can recover because it's never hit by 1000 simultaneous requests.
```

---

## PART 3 — JITTER STRATEGIES

```
Full Jitter (recommended for most cases):
  delay = random(0, min(cap, base * 2^attempt))

  attempt=1: delay = random(0, min(30s, 1s * 2)) = random(0, 2s)
  attempt=2: delay = random(0, min(30s, 1s * 4)) = random(0, 4s)
  attempt=3: delay = random(0, min(30s, 1s * 8)) = random(0, 8s)
  attempt=4: delay = random(0, min(30s, 1s * 16)) = random(0, 16s)
  attempt=5: delay = random(0, min(30s, 1s * 32)) = random(0, 30s) ← capped

  Spreads retries most evenly. Best at preventing thundering herd.

Equal Jitter:
  delay = (base * 2^attempt) / 2 + random(0, (base * 2^attempt) / 2)
  Always waits at least half the backoff time.
  Useful when you need a minimum guaranteed wait before retry.

Decorrelated Jitter (AWS recommendation):
  delay = random(base, previous_delay * 3)
  delay starts at random(1s, 3s), then random(prev, prev*3)
  Adapts based on actual previous delay — good for high-contention scenarios.

Exponential Backoff (NO jitter):
  delay = min(cap, base * 2^attempt)
  ALL clients wait the same amount → synchronized spikes
  AVOID in any scenario with multiple concurrent callers.
```

---

## PART 4 — IMPLEMENTATION

```java
// Java — manual exponential backoff with full jitter:
public <T> T retryWithBackoff(Callable<T> operation, int maxAttempts) throws Exception {
    long baseDelayMs = 1000;
    long capMs = 30_000;
    Random random = new Random();

    for (int attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
            return operation.call();
        } catch (RetryableException e) {
            if (attempt == maxAttempts) throw e;  // exhausted retries

            // Full jitter: random between 0 and min(cap, base * 2^attempt)
            long maxDelay = Math.min(capMs, baseDelayMs * (1L << attempt));  // 2^attempt
            long jitteredDelay = (long)(random.nextDouble() * maxDelay);

            log.warn("Attempt {} failed. Retrying in {}ms", attempt, jitteredDelay);
            Thread.sleep(jitteredDelay);
        }
    }
    throw new RuntimeException("All retries exhausted");
}

// Resilience4j (preferred):
RetryConfig config = RetryConfig.custom()
    .maxAttempts(5)
    .waitDuration(Duration.ofMillis(500))
    .intervalBiFunction((attempt, result) -> {
        // Exponential backoff with full jitter
        long baseMs = 500L * (1L << (attempt - 1));   // 500, 1000, 2000, 4000...
        long capped = Math.min(baseMs, 30_000L);
        return (long)(Math.random() * capped);
    })
    .retryOnException(e -> e instanceof IOException || e instanceof TimeoutException)
    .retryOnResult(response -> ((HttpResponse)response).getStatusCode() == 503)
    .build();

// Retry is idempotent-safe only for GET/idempotent operations.
// For POST payments: use idempotency keys + retry.
```

---

## PART 5 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your notification service is sending emails via SendGrid. SendGrid returns 429 Too Many Requests. How do you handle retries?"

**You (architect answer):**

> "A 429 means we're hitting SendGrid's rate limit. The correct response is to back off and retry,
> but not all retries are equal.
>
> First, I check the Retry-After header that SendGrid includes in the 429 response. If it says
> 'wait 60 seconds,' that's authoritative — I wait exactly 60 seconds before the next attempt.
>
> If there's no Retry-After header, I use exponential backoff with full jitter. Base delay 1 second,
> doubling each attempt, capped at 30 seconds. Full jitter means each retry attempt waits a random
> amount between 0 and the calculated backoff. If we're processing 10,000 notifications in a burst,
> jitter spreads them across the backoff window instead of all retrying at the same second.
>
> I'd configure: max 5 attempts, retry only on 429, 503, 502, and network errors — not on 400,
> 401, 422 (those are permanent failures, retrying won't help). Each notification is processed via
> Kafka, so if all retries exhaust, the message goes to a dead-letter queue for manual inspection.
>
> The idempotency piece: SendGrid email sends are not naturally idempotent — if our retry succeeds
> after the original also succeeded (but we didn't know), the user gets two emails. We prevent this
> with a deduplication key per email: SendGrid accepts an X-Message-ID header which we set to the
> notification UUID. If we retry, we send the same X-Message-ID. SendGrid deduplicates on their end."

---

## PART 6 — WHAT TO RETRY AND WHAT NOT TO

```
Retry:
  ✓ 429 Too Many Requests    → rate limited, back off
  ✓ 503 Service Unavailable  → downstream down, retry later
  ✓ 502 Bad Gateway          → proxy error, transient
  ✓ 504 Gateway Timeout      → timeout, retry
  ✓ Network errors           → connection reset, timeout
  ✓ 500 Internal Server Error (sometimes) → depends on idempotency

Do NOT retry:
  ✗ 400 Bad Request          → our request is malformed, retry won't fix it
  ✗ 401 Unauthorized         → auth token invalid, retry with same token → same error
  ✗ 403 Forbidden            → permissions issue, retry won't help
  ✗ 404 Not Found            → resource doesn't exist, retry won't create it
  ✗ 422 Unprocessable Entity → validation failed, retry with same data → same error

Max retries by use case:
  Email notification:   5 retries, exponential backoff (failure = delayed email, not critical)
  Payment processing:   3 retries, exponential backoff + idempotency key
  DB write:             3 retries (on transient errors like deadlock)
  External API call:    3-5 retries with circuit breaker
  Background jobs:      Up to 10 retries with long backoff (hours/days via cron retry)
```

---

## QUICK REFERENCE CARD

```
Exponential backoff formula:
  delay = min(cap, base * 2^attempt)
  With full jitter: delay = random(0, min(cap, base * 2^attempt))
  Typical values: base=1s, cap=30s, maxAttempts=5

Attempt  No Jitter  Full Jitter (range)
───────  ─────────  ──────────────────
  1        1s        0–2s
  2        2s        0–4s
  3        4s        0–8s
  4        8s        0–16s
  5       16s        0–30s (capped)

Always check Retry-After header — use it if present.

Never retry non-idempotent operations without idempotency keys.

Combine with:
  Circuit breaker → stop retrying when downstream is clearly broken
  Dead-letter queue → capture messages that exhaust all retries

Interview one-liner:
"Immediate retries create thundering herd — all callers storm the recovering
service simultaneously. Exponential backoff gives it breathing room.
Jitter spreads retries over time so even the backoff waves don't arrive
simultaneously. The three together let a service recover without being
overwhelmed by its own clients."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Retries are everywhere in distributed systems — the question is always whether your retry strategy helps recovery or makes the outage worse.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **03 — Notification** | APNs returns 429 (rate limited). Retry immediately = still 429. Full jitter: random(0, min(cap, base × 2^attempt)). Spread retries randomly → APNs rate limit clears → notifications delivered. |
| **07 — Payment** | Bank gateway times out. 1000 simultaneous payment timeouts retry without jitter → thundering herd hammers already-struggling gateway. Full jitter spreads 1000 retries across a window, gateway recovers. |
| **08 — Food Delivery** | Restaurant API returns 503. 50 simultaneous orders retry every 4s without jitter → spike every 4s. With full jitter: smooth retry curve, restaurant server gets steady stream not burst. |
| **20 — Email** | SMTP server rejection (4xx transient). Email standard (RFC 5321) mandates retry with exponential backoff: 5min, 10min, 20min, 40min, up to 24 hours. This is built into every production email system. |

**Architect's one-liner for the interview:**
*"Exponential backoff gives a struggling service breathing room between retries; jitter ensures those retries don't all arrive at the same moment and recreate the original spike."*
