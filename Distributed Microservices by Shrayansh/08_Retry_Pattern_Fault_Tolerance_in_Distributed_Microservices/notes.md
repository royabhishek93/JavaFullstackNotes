# Retry Pattern — Fault Tolerance in Distributed Microservices

## What is this? (Plain English)

In a distributed system, a call to a downstream service can fail because of a **transient issue** — a short, temporary glitch like a network blip or a momentary timeout. If you simply retry the same call a moment later, it often succeeds. The Retry pattern automates that "try again" logic so your service recovers from blips without bothering the caller — or worse, throwing away work that was already 90% done.

**Why retry inside the service instead of asking the client to call again?** Every request that reaches 90% completion before failing represents real cost — CPU, memory, time. If you discard it and make the *client* retry your entire API from scratch, you redo that whole 90% of work again. Retrying just the failed downstream call (the last 10%) avoids duplicating everything that already succeeded.

## The Problem It Solves

Retry sounds free, but done wrong it causes more harm than good. Two decisions matter: **when to retry**, and **how to retry**.

### When to Retry — A Decision Table by HTTP Status
| Status | Category | Retry? | Why |
|---|---|---|---|
| 2xx | Success | No | Already succeeded |
| 4xx (400, 401, 403, 404) | Client/validation error | **No — permanent failure** | Input is wrong; retrying the same input always fails the same way |
| 429 Too Many Requests | Rate limited | Yes, with delay | Transient — capacity may free up |
| 5xx (500, 502, 503) | Server/system error | **Yes — retryable** | Input was valid; a transient system issue caused it |
| Network error / timeout | Transient | Yes | But **only if the operation is idempotent** |

**The idempotency trap:** if Service A calls a "create" API on Service B, and the request times out on A's side *after* B already wrote the row to its DB, a naive retry creates a **duplicate row** — a second order, a second charge. Never retry a non-idempotent operation unless the API was specifically designed to detect and ignore duplicate submissions (e.g. via an idempotency key).

### How to Retry — Four Strategies

**1. Fixed Interval** — constant delay between attempts (e.g. every 2s).
- ✅ Simple to configure and debug.
- ❌ High risk of a **retry storm / thundering herd**: if a bug makes a service fail for everyone at once, every client retries at the exact same fixed delay, creating a synchronized wave of retry traffic that can be *worse* than the original load and can crowd out brand-new requests.

**2. Exponential Backoff** — delay grows exponentially: `delay = baseDelay * factor^attemptNumber`.
- Example: base 100ms, factor 2 → retries at 100ms, 200ms, 400ms, 800ms...
- ✅ Gives a struggling downstream service breathing room to recover instead of piling on more load.
- ❌ Still no randomness — if every client uses the same base/factor, they still retry in lockstep, so thundering herd risk is *reduced*, not eliminated. Also adds unnecessary latency if the outage was actually very short.

**3. Exponential Backoff + Jitter** — same exponential growth, but the actual delay is a **random number between 0 and min(maxDelay, exponentialFormula)**.
- ✅ Spreads retries out over time — this is what actually breaks the thundering herd, because clients no longer retry in sync.
- ❌ Harder to reason about and debug because delays are no longer deterministic.
- **This is the strategy used in production the vast majority of the time.**

**4. Custom Interval** — you write your own delay function (e.g. Fibonacci: 1, 1, 2, 3, 5, 8...).
- ✅ Full control.
- ❌ You own all the logic and maintenance — the framework won't help you.

## Architecture / Decision Flow

```
                ┌──────────────────────────┐
                │ Downstream call fails    │<─────────────────────────────┐
                └────────────┬─────────────┘                              │
                             v                                            │
                ┌──────────────────────────────────────┐                 │
                │ Permanent failure? (4xx /             │                 │
                │ non-idempotent op)                     │                 │
                └───────┬────────────────────┬──────────┘                 │
                    Yes │                    │ No                         │
                        v                    v                            │
        ┌─────────────────────────┐   ┌────────────────────────────────┐  │
        │ Do NOT retry -> return  │<──┤ 5xx / network error / timeout, │  │
        │ error to caller         │No │ and idempotent?                 │  │
        └─────────────────────────┘   └──────────────┬──────────────────┘  │
                                                  Yes │                     │
                                                       v                     │
                                        ┌───────────────────────┐            │
                                        │ Attempts remaining?    │            │
                                        └──────┬─────────┬──────┘            │
                                            Yes│         │No                 │
                                               v         v                   │
                              ┌─────────────────────────────┐  ┌───────────────────────────┐
                              │ Wait (fixed / exponential /  │──┤ All retries exhausted ->   │
                              │ exponential+jitter / custom) │  │ fallback method             │
                              └───────────────┬─────────────┘  └───────────────────────────┘
                                              └──────────────────────────────────────────────┘
                                              (loops back up to "Downstream call fails")
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## Key Code / Config

### Fixed Interval Retry (Resilience4j default)
```java
@Service
public class OrderService {

    @Autowired
    private ProductClient productClient;

    @Retry(name = "productService", fallbackMethod = "productFallback")
    public String invokeProductApi(String productId) {
        return productClient.getProductById(productId);
    }

    public String productFallback(String productId, Throwable t) {
        return "Product service is busy.";
    }
}
```
```properties
# Total attempts = 1 original call + N-1 retries
resilience4j.retry.instances.productService.max-attempts=3
resilience4j.retry.instances.productService.wait-duration=2s
# fixed interval is the DEFAULT retry type — no extra config needed for it
```

### Exponential Backoff
```properties
resilience4j.retry.instances.productService.max-attempts=4
resilience4j.retry.instances.productService.wait-duration=1s
resilience4j.retry.instances.productService.enable-exponential-backoff=true
resilience4j.retry.instances.productService.exponential-backoff-multiplier=2
# delay = 1000ms * 2^(failedAttempts): 1s, 2s, 4s...
```

### Exponential Backoff + Jitter
```properties
resilience4j.retry.instances.productService.max-attempts=4
resilience4j.retry.instances.productService.wait-duration=1s
resilience4j.retry.instances.productService.enable-exponential-backoff=true
resilience4j.retry.instances.productService.exponential-backoff-multiplier=2
resilience4j.retry.instances.productService.enable-randomized-wait=true
# actual delay = random(0, min(maxDelay, exponentialFormula))
```

### Custom Retry Logic (no annotation — manually built, e.g. Fibonacci delays)
```java
@Configuration
public class RetryConfig {

    @Bean
    public Retry customRetry() {
        IntervalFunction fibonacciInterval = attempt -> {
            // your own delay-computation logic per attempt (e.g. Fibonacci sequence)
            return computeFibonacciDelayMillis(attempt);
        };

        RetryConfig config = RetryConfig.custom()
            .maxAttempts(4)
            .intervalFunction(fibonacciInterval)
            .retryExceptions(IOException.class, TimeoutException.class)
            .build();

        return Retry.of("customRetry", config);
    }
}

@Service
public class OrderService {
    @Autowired private Retry customRetry;
    @Autowired private ProductClient productClient;

    public String invokeProductApi(String productId) {
        // Manually wrap the call — @Retry annotation can't be used
        // because there's no application.properties config to bind to.
        try {
            return customRetry.executeSupplier(() -> productClient.getProductById(productId));
        } catch (Exception e) {
            return "Product service is busy."; // manual fallback
        }
    }
}
```

## How It Works Internally (AOP)

Resilience4j's `@Retry` is powered by Spring AOP, which builds (at runtime) roughly this structure:
1. **`IntervalFunction`** — the delay-computation logic (fixed / exponential / exponential+jitter all have ready-made implementations in `IntervalFunction`; you only write your own for custom logic).
2. **`RetryConfig`** — holds `maxAttempts`, which exceptions to retry on, and which `IntervalFunction` to use.
3. **`Retry` object** — built from the config; your annotated method body is wrapped inside `retry.executeSupplier(...)`, exactly like the manual custom-retry code above. This is *the same thing AOP does for you automatically* when you use `@Retry`.

## Important Concepts

- **Transient Issue**: A short-lived, temporary problem (network blip, momentary timeout) likely to succeed if retried shortly after.
- **Permanent Failure**: An error that will never succeed no matter how many times you retry (typically 4xx validation errors) — retrying wastes resources and delays returning a real error to the caller.
- **Idempotency**: A property of an API where making the same request multiple times has the same effect as making it once. Non-idempotent operations must never be blindly retried — you risk duplicate resource creation (e.g. duplicate orders/charges).
- **Retry Storm / Thundering Herd**: Many clients retrying at the same moment, creating a traffic spike that can be worse than the original failure and can starve brand-new requests.
- **Exponential Backoff**: `delay = baseDelay * factor^attempt` — growing delay reduces load on a recovering downstream, but without randomness still risks synchronized retries.
- **Jitter**: Randomizing the delay (within a bound) to desynchronize client retries and meaningfully reduce thundering herd risk. The production-standard combination is **exponential backoff + jitter**.
- **Retry Decision Table**: 4xx → never retry (permanent). 5xx / network / timeout → retry, but only if idempotent.
