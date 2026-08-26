# Q12: Circuit Breaker & Resilience4j — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 20-25 minutes | **Frequency:** Every microservices architect round 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "Our payment service goes down → checkout service piles up threads → entire platform down in 90 seconds." — This is why circuit breakers exist.

---

## The Core Mental Model (Plain English)

Think of a circuit breaker like your home electrical breaker:
- **CLOSED** = current flows normally, calls go through
- **OPEN** = breaker tripped, calls fail fast (no network attempt)
- **HALF-OPEN** = testing if service recovered (let a few calls through)

```
     CLOSED ──────────────► OPEN
     (healthy)  failure      (tripped)
        ▲       threshold       │
        │       exceeded        │
        │                       │ wait timeout
        │                       ▼
        └─────── success ── HALF-OPEN
                 threshold   (probing)
```

---

## Scenario 1: Cascading Failure (The Classic 3 AM Incident)

### The Incident
Payment service response time degrades from 200ms → 30s.
Checkout service has 200 HTTP threads. All 200 blocked waiting on payment.
New checkout requests queue up. Checkout is now unresponsive.
Users can't browse products (same JVM, shared thread pool). Entire platform down.

### Without Circuit Breaker
```
Checkout ──────────────────────────────► Payment (slow/down)
         Thread 1 blocked (30s timeout)
         Thread 2 blocked (30s timeout)
         ...
         Thread 200 blocked (30s timeout)
         ↓
     No threads to serve ANY request
         ↓
     ENTIRE APP UNRESPONSIVE
```

### With Circuit Breaker
```java
@Service
public class CheckoutService {

    @CircuitBreaker(name = "payment", fallbackMethod = "paymentFallback")
    public PaymentResponse charge(Order order) {
        return paymentClient.charge(order);   // fast-fails when OPEN
    }

    // Fallback: degrade gracefully, don't crash
    public PaymentResponse paymentFallback(Order order, Exception ex) {
        // Queue payment for async retry, show "payment pending" to user
        asyncPaymentQueue.enqueue(order);
        return PaymentResponse.pending(order.getId());
    }
}
```

```yaml
# application.yml
resilience4j:
  circuitbreaker:
    instances:
      payment:
        slidingWindowSize: 10              # evaluate last 10 calls
        minimumNumberOfCalls: 5            # need at least 5 calls before opening
        failureRateThreshold: 50           # open if 50%+ calls fail
        waitDurationInOpenState: 10s       # stay OPEN for 10s, then probe
        permittedNumberOfCallsInHalfOpenState: 3
        slowCallRateThreshold: 80          # also open if 80%+ calls are slow
        slowCallDurationThreshold: 2s      # "slow" = takes > 2s
```

### Interview Answer
> "Without circuit breakers, a slow downstream causes thread pool exhaustion — the caller dies even though it's not the faulty service. Resilience4j's circuit breaker tracks a sliding window of calls, opens when failure rate exceeds threshold, and fast-fails all calls while OPEN. This protects threads. The fallback method degrades gracefully — queue for retry, return cached data, or return a safe default."

---

## Scenario 2: Bulkhead — Isolating Thread Pools

### The Problem (Without Bulkhead)
```
App has one HTTP thread pool: 200 threads
Payment service slow → uses 100 threads
Inventory service slow → uses 80 threads
→ Only 20 threads left for everything else
→ Catalog browsing (totally unrelated!) starts timing out
```

### The Fix: Bulkhead Pattern
```java
@Service
public class ExternalCallService {

    // Separate thread pool for payment — can't starve other services
    @Bulkhead(name = "payment", type = Bulkhead.Type.THREADPOOL,
              fallbackMethod = "paymentBulkheadFallback")
    @CircuitBreaker(name = "payment", fallbackMethod = "paymentFallback")
    public CompletableFuture<PaymentResponse> chargeAsync(Order order) {
        return CompletableFuture.supplyAsync(() -> paymentClient.charge(order));
    }

    @Bulkhead(name = "inventory", type = Bulkhead.Type.THREADPOOL,
              fallbackMethod = "inventoryBulkheadFallback")
    public CompletableFuture<InventoryResponse> checkStockAsync(Long productId) {
        return CompletableFuture.supplyAsync(() -> inventoryClient.check(productId));
    }

    public CompletableFuture<PaymentResponse> paymentBulkheadFallback(
            Order order, BulkheadFullException ex) {
        return CompletableFuture.completedFuture(PaymentResponse.rejected("System busy"));
    }
}
```

```yaml
resilience4j:
  bulkhead:
    instances:
      payment:
        maxConcurrentCalls: 20    # payment gets max 20 concurrent threads
        maxWaitDuration: 500ms    # wait max 500ms for a free slot
      inventory:
        maxConcurrentCalls: 10
```

### Easy Analogy
> Bulkhead = watertight compartments on the Titanic. One compartment floods (payment slow), others stay dry (catalog, cart, search unaffected).

---

## Scenario 3: Retry + Circuit Breaker (Order Matters!)

### The Trap: Retry Amplifies Failures
```
3 retries × 200 concurrent users = 600 calls to dying service
→ Makes the downstream worse, not better
→ Circuit breaker never opens because calls are "retried successfully" sometimes
```

### Correct Order: Circuit Breaker wraps Retry
```java
// WRONG ❌ — Retry is outermost, circuit breaker sees retried calls
@Retry(name = "payment")
@CircuitBreaker(name = "payment")
public PaymentResponse charge(Order order) { ... }

// CORRECT ✅ — Circuit breaker outermost, retry inside
// If circuit is OPEN, retry never fires — no amplification
@CircuitBreaker(name = "payment", fallbackMethod = "paymentFallback")
@Retry(name = "payment")
public PaymentResponse charge(Order order) { ... }
```

```
Execution order (Spring AOP, innermost runs first):
   HTTP call → CircuitBreaker → Retry → actual method

So: CircuitBreaker decides whether to even attempt.
    If OPEN → instant fallback (no retry).
    If CLOSED → Retry handles transient failures.
```

```yaml
resilience4j:
  retry:
    instances:
      payment:
        maxAttempts: 3
        waitDuration: 500ms
        exponentialBackoffMultiplier: 2     # 500ms, 1s, 2s
        retryExceptions:
          - java.net.ConnectException        # retry on connect failure
          - java.net.SocketTimeoutException
        ignoreExceptions:
          - com.example.PaymentDeclinedException  # don't retry business errors!
```

---

## Trap 1: Circuit Breaker Not Activating (Wrong Exception List)

### The Bug
```java
resilience4j:
  circuitbreaker:
    instances:
      payment:
        recordExceptions:
          - java.io.IOException   # ← only records IOException
```

```java
// Your HTTP client throws:
feign.FeignException$ServiceUnavailable   // ← NOT an IOException!
// → Circuit breaker sees 0 failures → never opens → no protection
```

### Fix
```yaml
resilience4j:
  circuitbreaker:
    instances:
      payment:
        recordExceptions:
          - java.lang.Exception    # record ALL exceptions (use ignoreExceptions to exclude)
        ignoreExceptions:
          - com.example.BusinessException   # don't count business errors as failures
```

---

## Trap 2: Circuit Breaker on @Async Method (Proxy Bypass)

### The Bug
```java
@Service
public class PaymentService {

    @Async
    @CircuitBreaker(name = "payment")   // ← TRAP: @Async creates a different proxy
    public CompletableFuture<PaymentResponse> chargeAsync(Order order) {
        return CompletableFuture.completedFuture(paymentClient.charge(order));
    }

    public void processOrder(Order order) {
        chargeAsync(order);  // self-invocation → bypasses BOTH proxies
                             // circuit breaker and @Async BOTH silently ignored
    }
}
```

### Fix: Inject self or separate the classes
```java
@Service
public class PaymentService {

    @Autowired
    private PaymentClient paymentClient;  // separate class for external call

    @CircuitBreaker(name = "payment", fallbackMethod = "chargeFallback")
    public PaymentResponse charge(Order order) {
        return paymentClient.charge(order);
    }
}

@Service
public class OrderService {
    @Autowired
    private PaymentService paymentService;  // different bean → proxy works ✅

    public void processOrder(Order order) {
        paymentService.charge(order);       // goes through proxy ✅
    }
}
```

---

## Trap 3: Fallback Method Signature Mismatch

### The Bug
```java
@CircuitBreaker(name = "payment", fallbackMethod = "paymentFallback")
public PaymentResponse charge(Order order) { ... }

// WRONG ❌ — missing the exception parameter
public PaymentResponse paymentFallback(Order order) {
    return PaymentResponse.failed();
}
```

```
Result: Resilience4j can't find the fallback method
        → NoSuchMethodException at runtime (NOT compile time!)
        → Stack trace in production when circuit opens
```

### Fix: Fallback must have same params + Throwable/Exception at end
```java
// CORRECT ✅
public PaymentResponse paymentFallback(Order order, Exception ex) {
    log.warn("Payment fallback triggered: {}", ex.getMessage());
    return PaymentResponse.pending(order.getId());
}

// ALSO VALID — specific exception type for different fallbacks
public PaymentResponse paymentFallback(Order order, CallNotPermittedException ex) {
    // circuit is OPEN
    return PaymentResponse.pending("Circuit open, retrying later");
}

public PaymentResponse paymentFallback(Order order, TimeoutException ex) {
    // timeout specifically
    return PaymentResponse.pending("Timeout, please retry");
}
```

---

## Advanced Scenario: Rate Limiter (Prevent Overloading Downstream)

### The Problem
Your service recovers from an outage. 10,000 queued requests all hit payment at once.
Payment service goes down again immediately (thundering herd).

### Fix: Rate Limiter
```java
@RateLimiter(name = "payment", fallbackMethod = "paymentRateLimited")
@CircuitBreaker(name = "payment", fallbackMethod = "paymentFallback")
public PaymentResponse charge(Order order) {
    return paymentClient.charge(order);
}

public PaymentResponse paymentRateLimited(Order order, RequestNotPermitted ex) {
    // Return 429 Too Many Requests
    throw new TooManyRequestsException("Payment system busy, retry in 1 second");
}
```

```yaml
resilience4j:
  ratelimiter:
    instances:
      payment:
        limitForPeriod: 100          # max 100 calls
        limitRefreshPeriod: 1s       # per second
        timeoutDuration: 0ms         # don't wait — fail immediately if over limit
```

---

## Quick Reference: Which Pattern for Which Problem?

| Problem | Pattern | Why |
|---|---|---|
| Downstream is down | Circuit Breaker | Open circuit, fast-fail, don't exhaust threads |
| Downstream is slow | Circuit Breaker (slowCallDuration) | Count slow calls as failures |
| Transient network blip | Retry with backoff | Retry a few times before giving up |
| Shared thread pool starvation | Bulkhead | Isolate thread pools per dependency |
| Thundering herd on recovery | Rate Limiter | Controlled ramp-up |
| Retry amplifying failures | CB wraps Retry | CB prevents retry when circuit is OPEN |

---

## Interview Cheat Sheet (Say This Confidently)

> "In production, I always combine Circuit Breaker + Retry + Bulkhead. Circuit breaker is outermost (fast-fail when open), retry is inner (handle transient blips), bulkhead isolates thread pools so one slow dependency can't starve others. I set `recordExceptions` to Exception broadly and use `ignoreExceptions` for business exceptions. Fallback methods always have the original params plus a Throwable — Resilience4j won't find them at runtime otherwise, which is a nasty surprise in prod. And I never put @CircuitBreaker on an @Async method called via self-invocation — the proxy is bypassed and neither annotation does anything."
