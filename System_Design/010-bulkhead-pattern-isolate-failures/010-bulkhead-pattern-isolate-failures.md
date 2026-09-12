# Bulkhead Pattern
### Isolate Failures So One Slow Service Doesn't Exhaust Thread Pool for All Services

---

## PART 1 — THE STUDENT CONVERSATION

**The name comes from ship design.**

A ship's hull is divided into watertight compartments (bulkheads). If one compartment floods, the others stay dry. The ship doesn't sink — it loses one section but keeps floating.

Without bulkheads: a hole in one section floods the entire ship → sinks.

In software: your Order Service has 200 threads. It calls three downstream services: Payment, Inventory, and Notification. Payment Service goes down and starts responding in 60 seconds. Those 200 threads start getting stuck on payment calls. Within 3 minutes, all 200 threads are blocked waiting for Payment. Inventory and Notification calls — which are working fine — can't get threads. Orders fail across the board, not just payment-related ones.

**Bulkhead isolates thread pools per downstream service.** Payment calls get 50 threads. Inventory calls get 50. Notification calls get 50. General work gets 50. If Payment eats all its 50 threads, Inventory and Notification still have their own threads and keep working.

---

## PART 2 — THE DIAGRAMS

### Without Bulkhead — Single Thread Pool

```
Order Service: 200 shared threads
──────────────────────────────────────────────────────────────────

  t=0:  Payment Service degrades (60s response time)

  Thread pool state over time:
  t=0s:   [ 200 available ]
  t=60s:  [  5 blocked on Payment | 195 available ]
  t=120s: [ 50 blocked on Payment | 150 available ]
  t=180s: [150 blocked on Payment |  50 available ]
  t=240s: [200 blocked on Payment |   0 available ]

  At t=240s:
  - Inventory calls arrive: no threads → queue → timeout → fail ✗
  - Notification calls arrive: no threads → timeout → fail ✗
  - New order requests arrive: no threads → HTTP 504 to user ✗

  The entire Order Service is effectively down.
  Root cause: Payment Service slowness consumed ALL shared threads.
```

### With Bulkhead — Isolated Thread Pools

```
Order Service: 4 dedicated thread pools
──────────────────────────────────────────────────────────────────

  ┌──────────────────┐  ┌──────────────────┐
  │ Payment Pool     │  │ Inventory Pool   │
  │ 50 threads       │  │ 50 threads       │
  │                  │  │                  │
  │ t=240s:          │  │ t=240s:          │
  │ [50 blocked] ✗  │  │ [45 available] ✓ │
  └──────────────────┘  └──────────────────┘

  ┌──────────────────┐  ┌──────────────────┐
  │ Notification Pool│  │ General Pool     │
  │ 50 threads       │  │ 50 threads       │
  │                  │  │                  │
  │ t=240s:          │  │ t=240s:          │
  │ [48 available] ✓│  │ [40 available] ✓ │
  └──────────────────┘  └──────────────────┘

  Payment pool is saturated → payment calls fail fast (pool rejected)
  Inventory, Notification, General: still fully functional ✓

  Failure is CONTAINED to the payment bulkhead.
  Users can still browse, add to cart, check inventory.
  Only checkout (payment) fails.
```

---

## PART 3 — TWO TYPES OF BULKHEAD

### Type 1: Thread Pool Isolation (most common)

```
Each downstream service gets its own dedicated thread pool.
If pool is full → new requests are REJECTED immediately (not queued).

When to use: when calls may block for variable durations (HTTP calls, DB queries).
Works well with: circuit breaker (if circuit opens, reject immediately)
Trade-off: more threads total → more memory (each thread = 0.5–1MB stack)

Resilience4j configuration:
  bulkhead = ThreadPoolBulkheadConfig.custom()
      .maxThreadPoolSize(20)          // max threads for THIS downstream service
      .coreThreadPoolSize(10)         // always-alive threads
      .queueCapacity(5)               // brief queue before rejection
      .keepAliveDuration(Duration.ofSeconds(20))
      .build();

Behavior:
  0–10 requests in flight: handled by core threads
  11–15: new threads created (up to maxThreadPoolSize)
  16–20: queued (up to queueCapacity=5)
  21+: BulkheadFullException → immediate rejection
```

### Type 2: Semaphore Isolation (for non-blocking operations)

```
Uses a counting semaphore instead of a separate thread pool.
Limits concurrent calls without context switching overhead.

When to use: in-memory operations, reactive/async code (WebFlux).
Works well with: async/non-blocking code where threads aren't blocked.
Trade-off: doesn't protect against thread exhaustion as well.

  bulkhead = BulkheadConfig.custom()
      .maxConcurrentCalls(25)          // max 25 concurrent calls allowed
      .maxWaitDuration(Duration.ZERO)  // don't queue — reject immediately
      .build();
```

---

## PART 4 — IMPLEMENTATION

```java
// Thread pool bulkhead for Payment Service calls:
ThreadPoolBulkheadConfig paymentBulkheadConfig = ThreadPoolBulkheadConfig.custom()
    .maxThreadPoolSize(20)
    .coreThreadPoolSize(10)
    .queueCapacity(5)
    .build();

ThreadPoolBulkhead paymentBulkhead =
    ThreadPoolBulkhead.of("paymentService", paymentBulkheadConfig);

// Wrap the payment call:
@Service
public class OrderService {

    public CompletableFuture<PaymentResult> processPayment(Order order) {
        Supplier<PaymentResult> paymentCall =
            () -> paymentService.charge(order.getUserId(), order.getAmount());

        return paymentBulkhead.executeSupplier(paymentCall)
            .exceptionally(ex -> {
                if (ex instanceof BulkheadFullException) {
                    // Pool exhausted → fail fast with specific error
                    log.warn("Payment bulkhead full. Rejecting order {}", order.getId());
                    return new PaymentResult("REJECTED", "System busy, try again");
                }
                throw new RuntimeException(ex);
            });
    }
}

// Combine with circuit breaker and retry:
Supplier<PaymentResult> decorated =
    Decorators.ofSupplier(paymentCall)
        .withThreadPoolBulkhead(paymentBulkhead)   // 1st: limit concurrency
        .withCircuitBreaker(paymentCircuitBreaker)  // 2nd: short-circuit if failing
        .withRetry(retryConfig)                     // 3rd: retry on transient errors
        .decorate();
// Order matters: retry wraps circuit breaker wraps bulkhead
```

---

## PART 5 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your e-commerce platform calls Recommendation Service, Inventory Service, and Payment Service in a single order-view request. Recommendation Service starts timing out. What happens and how do you fix it?"

**You (architect answer):**

> "Without isolation, all three share the same Tomcat thread pool. If Recommendation Service
> responds in 10 seconds and we have 500 order-view requests per second, within 20 seconds
> the thread pool is full — Inventory and Payment calls get no threads. The page load fails
> entirely, not because inventory or payment is broken, but because recommendations are slow.
>
> The fix is a bulkhead on each downstream service. I'd give Recommendation Service its own
> thread pool of 20 threads — since recommendations are optional UI content, not critical to
> order functionality. If those 20 threads are all blocked, new recommendation requests are
> rejected immediately (BulkheadFullException), and we return a fallback: an empty
> recommendations section. The page loads without personalized recommendations.
>
> Inventory and Payment each get their own pools sized appropriately — Payment might get
> 100 threads since it's critical and I never want it to be starved.
>
> I'd pair the Recommendation bulkhead with a circuit breaker: if recommendation failures
> exceed 50%, the circuit opens and we skip calling the service entirely, returning the
> fallback immediately without wasting even one thread.
>
> The metric I watch: bulkhead_rejected_calls per service. If recommendation bulkhead
> rejection rate is high, that's a signal to either scale recommendation service or
> increase its thread pool size."

---

## PART 6 — SIZING BULKHEADS

```
How to size each thread pool:
────────────────────────────────────────────────────────────────────

Formula:
  thread_pool_size = (requests_per_sec × avg_latency_secs) × 1.2 safety factor

Example — Payment Service:
  Peak: 500 payment calls/sec
  Avg latency: 200ms = 0.2s
  Threads needed: 500 × 0.2 × 1.2 = 120 threads

Example — Recommendation Service:
  Peak: 200 calls/sec
  Avg latency: 100ms = 0.1s (normal) / 10s (degraded)
  Thread for normal: 200 × 0.1 × 1.2 = 24 threads
  → Size to 25 threads. On degradation: pool fills and rejects,
    returning fallback quickly. Acceptable trade-off.

Queue capacity:
  Set small (5–10) or zero.
  Large queues hide problems — you don't want to queue 500 requests,
  you want to reject them and return a fast fallback.
  "Fail fast" is better than "queue and wait forever."
```

---

## QUICK REFERENCE CARD

```
Bulkhead: each downstream service gets its own isolated resource pool.
  Failure in one pool cannot consume resources of other pools.

Types:
  Thread pool:  separate threads per service. Best for blocking I/O calls.
  Semaphore:    concurrent call limit. Best for async/reactive code.

Size the pool for normal operation with a small buffer.
Set queueCapacity small or zero — reject fast, return fallback.

Fallback options when bulkhead is full:
  → Return cached data
  → Return empty/default response
  → Return HTTP 503 with Retry-After header
  → Publish event to async queue for later processing

Always combine:
  Bulkhead → limits concurrency per service
  + Circuit Breaker → stops calling broken services
  + Timeout → prevents threads from blocking forever
  + Retry + Jitter → recovers from transient failures

Monitoring:
  bulkhead.available_concurrent_calls → how much headroom
  bulkhead.rejected_calls             → failure rate alert
  thread_pool.active_threads          → saturation

Interview one-liner:
"Bulkhead prevents one slow service from starving all other services.
Thread pool isolation means Payment's 50 threads being all blocked
doesn't affect Inventory's 50 threads. Failures are contained."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Bulkhead comes up whenever you need to explain why one failing service shouldn't crash everything else — it's the answer to "how do you contain blast radius?"

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **07 — Payment** | Fraud detection thread pool isolated from payment processing pool. Fraud service hangs → its 20-thread pool fills up. Payment processing pool (separate, 30 threads) continues unaffected. Payments go through; fraud check degrades gracefully. |
| **08 — Food Delivery** | Driver assignment thread pool isolated from notification thread pool. Notification service goes down → notification pool exhausts. Driver assignment pool is separate → drivers still get assigned → orders fulfilled. |
| **09 — E-Commerce** | Product catalog thread pool isolated from checkout thread pool. Black Friday: catalog search is overwhelmed (slow response). Checkout pool is separate and unaffected → users can still complete purchases even while search degrades. |

**Architect's one-liner for the interview:**
*"Bulkhead means Payment's 50 threads being fully blocked on a slow fraud API cannot starve the 50 threads handling checkout — failures are physically contained, not just logically isolated."*
