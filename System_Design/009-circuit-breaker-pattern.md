# Circuit Breaker Pattern
### Service Calls Notification Service — It's Slow. How Circuit Breaker Stops the Cascade

---

## PART 1 — THE STUDENT CONVERSATION

**The problem: one slow service can bring down your entire system.**

Your Order Service calls Notification Service to send a confirmation email. Notification Service is having issues — it's responding in 30 seconds instead of 200ms. Your Order Service thread pool has 200 threads. Each thread is now blocked for 30 seconds waiting for a response. Within minutes, all 200 threads are blocked on Notification Service calls. New order requests queue up, eventually time out, and users see errors — not because the order logic failed, but because email sending is slow.

**This is cascade failure.** One unhealthy downstream service exhausts the resources of every service that calls it.

**Circuit breaker is an electrical analogy.** When a circuit is overloaded, a physical circuit breaker "trips" — it opens the circuit to protect downstream components. Once the electrical issue is fixed, you reset the breaker.

A software circuit breaker "trips" when a downstream service is failing: it immediately returns an error or a fallback instead of waiting for the slow service. It protects your thread pool. And after a cool-down period, it "tries" the downstream service again to see if it recovered.

---

## PART 2 — THE THREE STATES

```
Circuit Breaker State Machine:
────────────────────────────────────────────────────────────────────

  ┌─────────────────────────────────────────────────────────────────┐
  │                                                                   │
  │  ┌─────────┐   failure threshold    ┌──────────┐                 │
  │  │  CLOSED  │ ──── exceeded ──────► │   OPEN   │                 │
  │  │(normal)  │                       │(tripped) │                 │
  │  └─────────┘                        └──────────┘                 │
  │      ▲                                    │                       │
  │      │ success                            │ wait timeout expires  │
  │      │                                    ▼                       │
  │      │                         ┌─────────────────┐               │
  │      └─────────────────────────│  HALF-OPEN      │               │
  │                                │  (testing)      │               │
  │                                └─────────────────┘               │
  │                                      │ failure → back to OPEN    │
  └─────────────────────────────────────────────────────────────────┘

CLOSED state (normal operation):
  Requests pass through to the downstream service.
  Circuit breaker counts failures.
  If failures exceed threshold (e.g., 5 failures in 60 seconds):
    → Trip to OPEN state.

OPEN state (circuit tripped):
  ALL requests immediately fail without calling downstream.
  Returns error or fallback instantly — no waiting.
  Thread pool not blocked. System protected.
  After wait timeout (e.g., 30 seconds):
    → Move to HALF-OPEN state.

HALF-OPEN state (recovery probe):
  Allow ONE request through to the downstream service.
  If it SUCCEEDS: → Close circuit (downstream recovered) ✓
  If it FAILS:    → Back to OPEN state (still broken, wait again)
```

### The Cascade Without Circuit Breaker

```
Order Service (200 threads) calling Notification Service (degraded, 30s response):
────────────────────────────────────────────────────────────────────

  t=0:  1,000 orders/min arrive. Each needs email notification.
        Notification Service is slow: 30s per call.

  t=1s: 17 threads blocked (17 orders × 1s each, each taking 30s)
  t=10s: 170 threads blocked. 30 threads available for order processing.
  t=12s: 200 threads blocked. ALL threads waiting for Notification.
         New orders arriving → queue → timeout after 5s → HTTP 504 to user.

  NOTHING IS WRONG WITH ORDER LOGIC. But users see "service unavailable."
  Notification slowness killed Order Service.

With Circuit Breaker:
  t=0:  First 5 calls to Notification fail within 60s → CIRCUIT OPENS
  t=5s: All subsequent Notification calls fail instantly (no thread blocked)
        Order processing continues normally.
        Email notifications are dropped (or queued for later retry).
  t=35s: HALF-OPEN: one probe request to Notification
         Still slow → CIRCUIT stays OPEN
  t=65s: HALF-OPEN: one probe → Notification recovered → CIRCUIT CLOSES
         Normal email sending resumes.
```

---

## PART 3 — IMPLEMENTATION (Resilience4j — Java)

```java
// 1. Configuration
CircuitBreakerConfig config = CircuitBreakerConfig.custom()
    .failureRateThreshold(50)           // open if 50% of calls fail
    .slowCallRateThreshold(50)          // open if 50% of calls are slow
    .slowCallDurationThreshold(Duration.ofSeconds(2)) // "slow" = >2s
    .waitDurationInOpenState(Duration.ofSeconds(30))  // wait 30s in OPEN
    .permittedNumberOfCallsInHalfOpenState(3)         // 3 probes in HALF-OPEN
    .slidingWindowSize(10)              // evaluate last 10 calls
    .build();

CircuitBreaker cb = CircuitBreaker.of("notificationService", config);

// 2. Wrap your service call
@Service
public class OrderService {

    private final CircuitBreaker circuitBreaker;

    public void placeOrder(Order order) {
        // Save order first (local transaction — always succeeds)
        orderRepo.save(order);

        // Send notification with circuit breaker + fallback
        Supplier<Void> notifyCall = CircuitBreaker
            .decorateSupplier(circuitBreaker,
                () -> notificationService.sendConfirmation(order));

        Try.ofSupplier(notifyCall)
           .recover(CallNotPermittedException.class,
               ex -> { enqueueForRetry(order); return null; })  // fallback
           .recover(Exception.class,
               ex -> { enqueueForRetry(order); return null; }); // fallback
    }

    private void enqueueForRetry(Order order) {
        // Push to Kafka/SQS — notification sent later when service recovers
        retryQueue.push(new PendingNotification(order.getId()));
    }
}
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Order Service is calling Notification Service which is slow. Orders are failing. How do you fix this?"

**You (architect answer):**

> "The core problem is that email notification is in the critical path of order placement.
> It shouldn't be. Sending a confirmation email is not what makes an order 'placed' — saving
> the order to the database is. So the first fix is architectural: make the notification async.
>
> Order Service saves the order, publishes an OrderPlaced event to Kafka, returns 200 to the user.
> A separate Notification Consumer reads from Kafka and calls Notification Service. Even if
> Notification Service is down for an hour, the Kafka consumer retries until it succeeds.
> The order placement is never blocked.
>
> But for cases where the call genuinely must be synchronous — like calling a fraud scoring
> service before approving payment — I'd add a circuit breaker using Resilience4j.
> Configuration: trip after 50% failure rate over the last 10 calls, wait 30 seconds before
> probing. In the OPEN state, the fraud check returns a 'allow with monitoring' fallback
> instead of blocking. This is fail-open: slightly more risk, but orders continue flowing.
>
> The circuit breaker metrics are exposed to Prometheus: failure rate, state (OPEN/CLOSED),
> call count. When the circuit trips, an alert fires, on-call engineers investigate Notification
> Service. The circuit self-recovers when Notification Service heals."

---

## PART 5 — CIRCUIT BREAKER METRICS TO MONITOR

```
Key metrics to track (Prometheus / Grafana):
────────────────────────────────────────────────────────────────────

  resilience4j_circuitbreaker_state{name="notificationService"}
    0 = CLOSED, 1 = OPEN, 2 = HALF_OPEN

  resilience4j_circuitbreaker_failure_rate{name="notificationService"}
    Current failure rate % — alert if > 40%

  resilience4j_circuitbreaker_calls_total{kind="failed"}
    Cumulative failed calls — good for SLO tracking

  resilience4j_circuitbreaker_calls_total{kind="not_permitted"}
    Calls short-circuited — this is how many calls you SAVED from blocking

  Application-level:
  orders_notification_retry_queue_depth   ← how many notifications are pending
  orders_placed_total vs orders_notified_total ← notification lag

Alert rules:
  circuit_breaker_state == 1 for > 5 minutes → page on-call
  notification_retry_queue_depth > 10000     → notification backlog building
```

---

## QUICK REFERENCE CARD

```
States:
  CLOSED:    normal, calls pass through, counting failures
  OPEN:      tripped, calls fail immediately (no blocking)
  HALF-OPEN: recovery probe, one request allowed through

Config knobs:
  failureRateThreshold:     % failures to trip (e.g., 50%)
  slowCallRateThreshold:    % slow calls to trip (e.g., 50%)
  slowCallDurationThreshold: what counts as "slow" (e.g., 2s)
  waitDurationInOpenState:  how long to stay OPEN before HALF-OPEN (e.g., 30s)
  slidingWindowSize:        evaluate last N calls (e.g., 10)

Always pair with a fallback:
  → Return cached data
  → Return a default value
  → Enqueue for async retry (Kafka/SQS)
  → Fail-open (allow request with degraded behavior)

Libraries:
  Java:   Resilience4j (modern), Hystrix (deprecated, Netflix)
  Go:     gobreaker, hystrix-go
  Python: pybreaker
  Spring: spring-cloud-circuitbreaker (wraps Resilience4j)

Related patterns:
  Retry (see Retry_Exponential_Backoff_Jitter.md)    → combine with circuit breaker
  Bulkhead (see Bulkhead_Pattern.md)                  → isolate thread pools
  Timeout (see Timeout_Strategy.md)                  → fail fast before circuit trips

Interview one-liner:
"Circuit breaker prevents cascade failure by short-circuiting calls to
a failing downstream service. In OPEN state, calls return immediately
with a fallback — no threads blocked, no cascade. After a cooldown,
one probe request tests recovery. If successful, circuit closes."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Any time you draw a service calling another service in an interview, you should be able to say what happens when that downstream service slows down — circuit breaker is your answer.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **03 — Notification** | Notification service calls FCM. FCM goes slow (500ms vs 50ms normal). Without circuit breaker: thread pool fills with slow FCM calls, ALL notification flows degrade. Circuit OPEN: fail fast → other notification channels (in-app, SMS) unaffected. |
| **07 — Payment** | Payment service calls fraud detection. Fraud service is overloaded. Circuit OPEN: skip fraud check, use rule-based fallback (ML score cached from last check). Payments continue without waiting for slow fraud API. |
| **08 — Food Delivery** | Order service calls restaurant confirmation API. Restaurant's system is down for maintenance. Circuit OPEN: auto-accept order, notify restaurant via SMS. Users see "Order placed" immediately — restaurant outage is invisible. |

**Architect's one-liner for the interview:**
*"Circuit breaker stops calling a failing service and returns a fallback immediately — no threads blocked, no cascade — then probes for recovery after a cooldown."*
