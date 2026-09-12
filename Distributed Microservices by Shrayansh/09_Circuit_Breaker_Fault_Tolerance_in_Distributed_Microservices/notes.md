# Circuit Breaker — Fault Tolerance in Distributed Microservices

## What is this? (Plain English)

Think of a household electrical circuit breaker: when current flows normally, the circuit is **closed** and electricity reaches your appliances. If something goes wrong (a short), the breaker **trips open** and stops the current entirely — protecting the house from further damage. The Circuit Breaker pattern in microservices works the same way: it stops your service from repeatedly calling a downstream dependency that's clearly failing, instead of hammering it (and wasting your own resources) on every single request.

**The core rule:** *closed = calls flow through; open = calls are blocked instantly.* This trips people up because it sounds backwards — "closed" doesn't mean "blocked," it means "circuit is complete, current/calls flow."

## The Problem It Solves

If `Product Service` goes down entirely, `Order Service` calling it repeatedly causes two real problems:
1. **Extra load on an already-struggling service** — hammering a service that's down can make it take even *longer* to recover.
2. **Wasted resources in the calling service** — every failing call still consumes a thread and adds latency while it waits out a timeout before failing. Thousands of doomed calls means thousands of blocked threads for no benefit.

The question a Circuit Breaker answers: **how does `Order Service` know *when* to stop calling `Product Service`, and when it's safe to start again?**

## Architecture Diagram

```
  +----------------+        +-------------------------------+        +------------------+
  |  Order Service |        |   CircuitBreaker AOP Proxy    |        | Product Service  |
  |                |        |   (CircuitBreakerStateMachine)|        |  (may be down)   |
  | invokeProductApi() ---->|  CLOSED: call passes through  | ------>|                  |
  |                |        |  OPEN: call blocked, instant  |        |                  |
  |                |        |        fallback, no network   |        |                  |
  |                |        |  HALF_OPEN: few trial calls   |        |                  |
  +----------------+        +-------------------------------+        +------------------+
                                        |
                                        | schedules OPEN -> HALF_OPEN transition
                                        v
                             +-------------------------------+
                             | ScheduledThreadPoolExecutor    |
                             | + DelayQueue (wait-duration)   |
                             +-------------------------------+
```

## The State Machine

```
[*] --> CLOSED (initial state)

 From        Trigger                                              To
 ──────────  ──────────────────────────────────────────────────   ──────────
 CLOSED      failure rate crosses threshold (e.g. 50% of last 10   OPEN
             calls)
 OPEN        wait duration elapses (e.g. 10s)                     HALF_OPEN
 HALF_OPEN   all trial calls succeed (100% success rate)           CLOSED
 HALF_OPEN   any trial call fails                                  OPEN
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

- **CLOSED** (healthy default state): all calls are allowed through to the downstream. Failures are tracked in a sliding window; if the failure rate crosses the configured threshold, the circuit trips to OPEN.
- **OPEN**: no calls reach the downstream at all — every call fails **instantly** via the fallback method, with zero network latency and zero thread blocking. After a configured wait duration, the circuit automatically moves to HALF_OPEN.
- **HALF_OPEN** (probing): only a small number of "trial" calls are allowed through to test whether the downstream has recovered. If **all** trial calls succeed → back to CLOSED. If **any** trial call fails → back to OPEN, and the wait timer starts again.

## Key Code / Config

```java
@Service
public class OrderService {

    @Autowired
    private ProductClient productClient;

    @CircuitBreaker(name = "productService", fallbackMethod = "productFallback")
    public String invokeProductApi(String productId) {
        return productClient.getProductById(productId);
    }

    // Invoked for EVERY failure — both while CLOSED (individual failures)
    // and while OPEN (instant rejection) or HALF_OPEN (failed trial call).
    public String productFallback(String productId, Throwable t) {
        return "Product service is currently unavailable.";
    }
}
```
```properties
resilience4j.circuitbreaker.instances.productService.sliding-window-type=COUNT_BASED
resilience4j.circuitbreaker.instances.productService.sliding-window-size=10
# ^ track the last 10 calls (or use TIME_BASED with a size in seconds instead)

resilience4j.circuitbreaker.instances.productService.minimum-number-of-calls=5
# ^ don't even START evaluating failure rate until at least 5 calls have happened —
#   avoids false positives from a tiny sample (e.g. "1 out of 2 calls failed" = 50%,
#   but that's not statistically meaningful)

resilience4j.circuitbreaker.instances.productService.failure-rate-threshold=50
# ^ percentage of the window that must fail to trip CLOSED -> OPEN
#   (50% of window size 10 = 5 failures trips the breaker)

resilience4j.circuitbreaker.instances.productService.wait-duration-in-open-state=10s
# ^ how long to stay OPEN before automatically trying HALF_OPEN

resilience4j.circuitbreaker.instances.productService.permitted-number-of-calls-in-half-open-state=3
# ^ how many trial calls to allow through while probing in HALF_OPEN

# By default ALL RuntimeExceptions/Errors count as failures. To control this explicitly:
resilience4j.circuitbreaker.instances.productService.record-exceptions=java.io.IOException,java.net.SocketTimeoutException
resilience4j.circuitbreaker.instances.productService.ignore-exceptions=com.example.ValidationException
```

### Example trace (minimum-calls=5, window=10, threshold=50%, wait=10s, trial-calls=3)
```
Call 1: FAIL  → failureCount=1  (below minimumNumberOfCalls, still CLOSED)
Call 2: FAIL  → failureCount=2  (still CLOSED)
Call 3: FAIL  → failureCount=3  (still CLOSED)
Call 4: FAIL  → failureCount=4  (still CLOSED)
Call 5: FAIL  → failureCount=5  (minimumNumberOfCalls reached: 5/10 = 50% >= threshold)
              → CIRCUIT TRIPS: CLOSED -> OPEN
[10 seconds pass — all calls during this window fail INSTANTLY via fallback, no network hit]
              → OPEN -> HALF_OPEN (automatic, after wait-duration-in-open-state)
Trial 1: FAIL → still probing
Trial 2: FAIL → still probing
Trial 3: FAIL → 3/3 permitted trials done, success rate 0% (not 100%)
              → HALF_OPEN -> OPEN (wait timer restarts)
```

## How It Works Internally (AOP + Scheduling)

Resilience4j's AOP proxy delegates to an internal `CircuitBreakerStateMachine`. On every call outcome (success or failure), it checks: *does this cross the threshold for the current state?* If yes, it transitions state (CLOSED→OPEN, or HALF_OPEN→CLOSED/OPEN).

The interesting internals question interviewers like to ask: **how does the circuit automatically flip from OPEN to HALF_OPEN after the wait duration, with nobody calling it?**

The answer is a **`ScheduledThreadPoolExecutor`**. When the circuit enters OPEN state, a task ("transition to HALF_OPEN") is scheduled to run after `waitDurationInOpenState`. Internally, `ScheduledThreadPoolExecutor` uses a **`DelayQueue`** (typically backed by a priority queue ordered by soonest-expiring delay first):
- The task with the smallest remaining delay always sits at the head of the queue.
- Idle worker threads look at the head of the queue; if its delay hasn't expired yet, the thread blocks for exactly that remaining duration and lets the OS wake it up when the delay elapses.
- Once ready, one worker thread picks up the task and executes it (flipping the state), while other threads move on to check the next-soonest task in the queue.

This is the same mechanism behind a much-loved interview question — *"how would you implement WhatsApp's disappearing messages that auto-delete after 24 hours?"* — the answer is the same delay-queue pattern.

## Important Concepts

- **Circuit Breaker**: Prevents an application from making repeated calls to a downstream service that is likely to fail, by tracking failures and short-circuiting future calls once a threshold is crossed.
- **CLOSED**: Normal state — all calls pass through to the downstream; failures are being tracked against the threshold.
- **OPEN**: Tripped state — calls fail instantly via the fallback, with no network call and no thread blocking, protecting both the caller's resources and the struggling downstream.
- **HALF_OPEN**: Probing state — a small number of trial calls are let through to test recovery; 100% success returns to CLOSED, any failure returns to OPEN.
- **Sliding Window (Count-Based vs Time-Based)**: The sample used to evaluate failure rate — either "last N calls" or "calls in the last N seconds." Distinct from rate-limiter sliding windows — same name, different concept.
- **Minimum Number of Calls**: Guard against false positives from tiny sample sizes (e.g. 1 failure out of 2 calls looking like "50% failure").
- **Failure Rate Threshold**: The percentage of the sliding window that must fail before the circuit trips to OPEN.
- **`ScheduledThreadPoolExecutor` + `DelayQueue`**: The mechanism behind automatic OPEN→HALF_OPEN transition after a timeout, without any external caller — also the standard answer for "implement a disappearing-message / TTL-expiry feature."
