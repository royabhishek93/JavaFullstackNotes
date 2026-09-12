# Bulkhead Pattern — Fault Tolerance in Distributed Microservices

## What is this? (Plain English)

A ship is built with separate watertight compartments (bulkheads). If one compartment floods, the walls stop the water from spreading into the rest of the ship — the ship stays afloat. The Bulkhead pattern applies the same idea to microservices: you split up your limited resources (threads) into isolated pools, so that if one downstream service becomes slow, it can only ever exhaust *its own* pool — never starve the rest of your application.

**Bulkhead vs Rate Limiter — the distinction interviewers probe for:**
- **Rate Limiter** protects your service **from its clients** (how many requests can come *in*). It never talks about concurrency — just a count per time window.
- **Bulkhead** protects your service **from its own downstream calls** (how many concurrent requests can go *out* to a dependency at once).

## The Problem It Solves

### Scenario 1 — A fragile downstream that can only take so much
`Product Service` is lightweight and can only safely handle 3 concurrent requests. It has no rate limiter of its own. Without a bulkhead, `Order Service` could fire an unbounded number of parallel calls at it and overwhelm it. A **Semaphore Bulkhead** caps concurrent calls to exactly 3 — the 4th caller waits (or fails) until a slot frees up.

### Scenario 2 — The "noisy neighbor" problem, narrowed to threads
`Order Service` exposes two APIs:
- `API 1` calls a **fast** `Product Service` (~100ms).
- `API 2` calls a **slow** `Payment Service` (~5s), which itself calls a third-party endpoint.

If traffic to `API 2` suddenly spikes, all of Order's threads (say, a pool of 10) get blocked waiting 5 seconds each on the slow payment call. Now a completely unrelated request to the fast `API 1` has **no threads left** to run on — even though `Product Service` is perfectly healthy. One slow endpoint has starved every other endpoint in the same application. This is a narrow, thread-pool-scoped version of the classic "noisy neighbor" system-design problem.

A **Thread Pool Bulkhead** fixes this by giving `API 2` its own dedicated, capped thread pool (e.g. max 5 threads) — so no matter how much `API 2` traffic spikes, `API 1` still has its own threads free to serve requests.

## Architecture Diagram

```
                     ORDER SERVICE (thread pool: 10 threads)
        ┌─────────────────────────────────────────────────────────────┐
        │                                                             │
        │   API 1 ──(uses shared/general threads)──► Product (fast)  │
        │                                                             │
        │   API 2 ──(bulkhead: max 5 dedicated)────► Payment (slow)  │
        │            threads reserved ONLY for this call              │
        │            spike in API 2 traffic can NEVER consume         │
        │            more than its 5 allotted threads                 │
        │                                                             │
        └─────────────────────────────────────────────────────────────┘

Semaphore Bulkhead (Scenario 1):
  Product API critical section — max 3 concurrent calls allowed via a
  semaphore counter. 4th caller waits up to maxWaitDuration, then fails
  and its fallback method runs.

Thread Pool Bulkhead (Scenario 2):
  Dedicated ExecutorService per downstream — core threads, max threads,
  and a bounded queue. Once queue AND max threads are full, further
  calls are rejected immediately and routed to the fallback method.
```

## How It Works — Step by Step

### Semaphore Bulkhead
1. AOP proxy intercepts the annotated method call.
2. It checks a semaphore counter: is a permit available (below `maxConcurrentCalls`)?
3. Yes → acquire the permit, proceed with the call, release the permit when done.
4. No → wait up to `maxWaitDuration` for a permit; if none frees up, reject and invoke the fallback method.

### Thread Pool Bulkhead
1. AOP proxy intercepts the annotated method and wraps the entire method body as a task.
2. The task is submitted to a **dedicated** `ThreadPoolExecutor` (core size, max size, bounded queue — all configured per bulkhead name), *not* the application's general thread pool.
3. If a core thread is free → task runs immediately.
4. If all core threads are busy but the queue has room → task is queued.
5. If the queue is full but max threads hasn't been reached → a new thread is spun up (up to `maxThreadPoolSize`).
6. If both the queue AND max threads are exhausted → the call is rejected immediately and the fallback method runs.
7. Because the method must return a `CompletableFuture`, your code wraps the actual return value in `CompletableFuture.completedFuture(...)` — it must **not** call `supplyAsync(...)` yourself, since the AOP proxy is the one responsible for submitting the task to the *bulkhead's* executor. Manually calling `supplyAsync` would run your code on the default/common pool instead of the isolated bulkhead pool, defeating the entire purpose.

## Key Code / Config

### Semaphore Bulkhead
```java
@Service
public class OrderService {

    @Autowired
    private ProductClient productClient;

    // type = SEMAPHORE limits concurrent calls using a counter (semaphore lock)
    @Bulkhead(name = "productBulkhead", type = Bulkhead.Type.SEMAPHORE,
              fallbackMethod = "productFallback")
    public String invokeProductApi(String productId) {
        return productClient.getProductById(productId);
    }

    public String productFallback(String productId, Throwable t) {
        return "Product service is busy. Please try again.";
    }
}
```
```properties
# Semaphore bulkhead — max 2 concurrent calls into the critical section
resilience4j.bulkhead.instances.productBulkhead.max-concurrent-calls=2
# how long a caller waits for a free permit before failing immediately
resilience4j.bulkhead.instances.productBulkhead.max-wait-duration=0
```

### Thread Pool Bulkhead
```java
@Service
public class OrderService {

    @Autowired
    private PaymentClient paymentClient;

    // type = THREADPOOL gives this call its OWN dedicated executor
    @Bulkhead(name = "paymentBulkhead", type = Bulkhead.Type.THREADPOOL,
              fallbackMethod = "paymentFallback")
    public CompletableFuture<String> invokePaymentApi(String orderId) {
        // Correct: wrap the value, don't call supplyAsync yourself —
        // AOP already submits this whole method as a task to the bulkhead pool.
        return CompletableFuture.completedFuture(paymentClient.charge(orderId));
    }

    public CompletableFuture<String> paymentFallback(String orderId, Throwable t) {
        return CompletableFuture.completedFuture("Payment service is busy.");
    }
}
```
```properties
resilience4j.thread-pool-bulkhead.instances.paymentBulkhead.core-thread-pool-size=2
resilience4j.thread-pool-bulkhead.instances.paymentBulkhead.max-thread-pool-size=3
resilience4j.thread-pool-bulkhead.instances.paymentBulkhead.queue-capacity=2
```

## Mermaid Diagram — Thread Pool Bulkhead Saturation

```
                ┌──────────────────────────────────────┐
                │ Incoming call to bulkhead-protected   │
                │ method                                 │
                └───────────────────┬────────────────────┘
                                    v
                ┌──────────────────────────────────────┐
                │          Core thread free?             │
                └───────────┬────────────────┬──────────┘
                        Yes │                │ No
                            v                v
            ┌───────────────────────┐  ┌───────────────────────┐
            │ Run immediately on    │  │   Queue has room?      │
            │ core thread           │  └──────┬─────────┬──────┘
            └───────────────────────┘     Yes │         │ No
                                                v         v
                                ┌───────────────────┐  ┌───────────────────────────┐
                                │ Wait in bounded    │  │ Max thread pool size       │
                                │ queue              │  │ reached?                   │
                                └───────────────────┘  └──────┬─────────────┬───────┘
                                                            No │             │ Yes
                                                                v             v
                                                ┌──────────────────────┐  ┌───────────────────────────────┐
                                                │ Spin up new thread   │  │ Reject immediately -> fallback │
                                                │ (up to max)          │  │ method                          │
                                                └──────────────────────┘  └───────────────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## Important Concepts

- **Bulkhead Pattern**: Isolates a limited resource (usually threads) per downstream dependency so one slow/overloaded dependency can't starve the rest of the application — named after ship compartments that stop flooding from spreading.
- **Noisy Neighbor Problem (narrow version)**: One endpoint's traffic spike consumes all shared threads, starving unrelated, healthy endpoints. Broader noisy-neighbor problems also include DB connections and infra resources, not just threads.
- **Semaphore Bulkhead**: Uses a semaphore lock to cap concurrent calls with a simple counter. Good for simple "only N concurrent calls allowed" cases. Rejects synchronously and immediately once the limit is hit (or waits up to `maxWaitDuration`).
- **Thread Pool Bulkhead**: Gives a downstream call its own dedicated `ThreadPoolExecutor` (core size, max size, bounded queue), completely separate from the application's shared/common thread pool. Method must return `CompletableFuture`.
- **Critical Section**: The specific block of code (usually just the downstream call) that the bulkhead annotation protects. Only put the downstream invocation here — not unrelated business logic or DB calls — otherwise you're accidentally bulkheading things you didn't intend to.
- **`CompletableFuture.completedFuture(...)` vs `supplyAsync(...)`**: Use `completedFuture` to just wrap your already-computed result — the AOP proxy handles submitting the task to the bulkhead's executor. Calling `supplyAsync` yourself bypasses the dedicated pool and uses the default/common pool instead, silently breaking the isolation the bulkhead is supposed to provide.
- **AOP-generated proxy**: Same mechanism as Rate Limiter — Resilience4j's `@Bulkhead` annotation triggers Spring AOP to wrap your method call in proxy code that manages the semaphore or thread pool for you at runtime.
