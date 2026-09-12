# Rate Limiter and Fault Tolerance in Distributed Microservices

## What is this? (Plain English)

Imagine a popular pizza shop — if 1,000 customers flood in at once, the kitchen collapses and no one gets pizza. A rate limiter is a bouncer at the door who says "only 5 people every 10 seconds, no more." Fault tolerance is the broader idea that even if the kitchen (a downstream service) is slow or broken, the rest of the shop (your service) keeps running instead of collapsing too.

In microservices terms: a fault-tolerant service keeps working gracefully even when one of the services it depends on goes down or slows down, instead of crashing the entire system.

## The Problem It Solves

Without fault tolerance, one slow downstream service can bring the entire system down:

1. Service A (Order) calls Service B (Product).
2. Product becomes slow — every call takes 60 seconds.
3. All of Order's threads are now waiting for Product.
4. Order's thread pool runs out. It starts rejecting all incoming requests.
5. Every other service that calls Order now fails too.

This chain reaction is called a **cascading failure**. The entire system crashes because of one bad service. Rate limiting also protects against sudden traffic spikes and denial-of-service (DOS) attacks that would overwhelm a service.

## Architecture Diagram

```
  Internet / Clients
        |
        v
+---------------+
|  API Gateway  |  <-- optional first line of defense
+---------------+
        |
        v
+--------------------+
|   Order Service    |
|                    |
| [@RateLimiter]     |  <-- rate limiter applied HERE on outbound calls
| [Fallback Method]  |
+--------------------+
        |
        |  (calls over network via Feign Client)
        v
+--------------------+        +---------------------+
|  Product Service   |        |  Resilience4j       |
|  (may be slow or   |        |  (Rate Limiter,     |
|   unavailable)     |        |   Bulkhead,         |
+--------------------+        |   TimeLimiter,      |
                              |   CircuitBreaker,   |
                              |   Retry)            |
                              +---------------------+
                                        |
                              Applied via AOP proxy
                              (intercepts method calls
                               before they reach network)
```

## Token Bucket Decision Flow

```
                 ┌───────────────────────────────────┐
                 │ Incoming call to rate-limited      │
                 │ method                             │
                 └──────────────────┬──────────────────┘
                                    │
                                    v
                 ┌───────────────────────────────────┐
             ┌──>│  Token available in bucket?        │
             ¦   └───────────┬──────────────┬────────┘
             ¦         Yes   │              │  No
             ¦               v              v
             ¦  ┌─────────────────────┐  ┌───────────────────────────┐
             ¦  │ Consume 1 token,    │  │ Wait up to timeout-duration│
             ¦  │ proceed to          │<─┤ for a token?               │
             ¦  │ downstream call     │  │ (Token freed in time)      │
             ¦  └─────────────────────┘  └──────────────┬─────────────┘
             ¦                                          │ Still none after timeout
             ¦                                          v
             ¦                           ┌───────────────────────────────────┐
             ¦                           │ Reject -> fallback method          │
             ¦                           │ (e.g. HTTP 429)                    │
             ¦                           └───────────────────────────────────┘
             ¦
   (dashed feedback loop)
   ┌───────────────────────────────────────────────┐
   │ Background refiller adds N tokens every        │
   │ limit-refresh-period                           │──────┘  (feeds back into "Token available?" check)
   └───────────────────────────────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## How It Works — Step by Step

1. A client sends a request to Order Service.
2. Order Service wants to call Product Service. Before it makes the network call, the **Resilience4j AOP proxy intercepts** the method call (because of the `@RateLimiter` annotation).
3. The proxy checks the **token bucket**: does a token exist?
   - Yes — consume one token and let the call proceed to Product Service.
   - No — wait up to the configured timeout (e.g., 1 second) for a token to appear.
4. If no token appears within the timeout, the call is **rejected** and the **fallback method** is invoked instead of crashing.
5. The fallback method returns a safe default response or a user-friendly error (e.g., "Rate limit exceeded, try later").
6. A background **refiller** periodically adds new tokens to the bucket (e.g., 2 tokens every 10 seconds), allowing new requests through after the window resets.

## Key Code / Config

### 1. Maven Dependency (`pom.xml`)
```xml
<!-- Add Resilience4j with Spring Boot starter -->
<dependency>
    <groupId>io.github.resilience4j</groupId>
    <artifactId>resilience4j-spring-boot3</artifactId>
    <version>2.1.0</version> <!-- use latest stable -->
</dependency>
```

### 2. Service Method with Rate Limiter (`OrderService.java`)
```java
@Service
public class OrderService {

    @Autowired
    private ProductClient productClient; // Feign client to call Product Service

    // @RateLimiter intercepts this method via AOP BEFORE the actual network call
    // name = "productRateLimiter" links to the config in application.properties
    // fallbackMethod = what to call if this request is DENIED by the rate limiter
    @RateLimiter(name = "productRateLimiter", fallbackMethod = "rateLimitedFallback")
    public String invokeProductApi(String productId) {
        // This line only runs if a token was available
        return productClient.getProductById(productId);
    }

    // Fallback MUST have the same return type and parameters as the original method
    // PLUS one extra parameter: Throwable (the exception that caused the fallback)
    public String rateLimitedFallback(String productId, Throwable throwable) {
        // Handle gracefully — log it, return a default, or throw a custom exception
        return "Rate limit exceeded. Please try again later.";
    }
}
```

### 3. Feign Client Interface (`ProductClient.java`)
```java
// Feign client — declares how to call the Product Service
// @FeignClient uses service discovery (Eureka) to find "product-service"
@FeignClient(name = "product-service")
public interface ProductClient {
    @GetMapping("/products/{id}")
    String getProductById(@PathVariable String id);
}
```

### 4. Configuration (`application.properties`)
```properties
# Resilience4j rate limiter uses Token Bucket algorithm by default

# "productRateLimiter" matches the name= in @RateLimiter annotation
resilience4j.ratelimiter.instances.productRateLimiter.limit-for-period=2
# ^ max tokens in the bucket = 2 (only 2 requests allowed per window)

resilience4j.ratelimiter.instances.productRateLimiter.limit-refresh-period=10s
# ^ refill the bucket with 2 new tokens every 10 seconds

resilience4j.ratelimiter.instances.productRateLimiter.timeout-duration=1s
# ^ if no token available, wait UP TO 1 second before rejecting the request
# (gives a short grace period instead of instant rejection)
```

## Important Concepts

- **Fault Tolerant Microservice**: A service that keeps working gracefully even when its downstream dependencies fail or go slow.
- **Cascading Failure**: When one slow/failed service causes thread exhaustion in calling services, which then fail, spreading the failure across the whole system.
- **Rate Limiter**: Controls how many requests a service (or its clients) can process in a given time window — protects against traffic spikes and DOS attacks.
- **Resilience4j**: A Java library providing five fault-tolerance mechanisms: Rate Limiter, Bulkhead, Time Limiter, Circuit Breaker, and Retry.
- **Recommended ordering**: Rate Limiter → Bulkhead → Time Limiter → Circuit Breaker → Retry. Rate limiter goes first so you don't waste computation retrying requests that will just get blocked anyway.
- **Fixed Window Counter**: Counts requests in a fixed time slot (e.g., 0–10s, 10–20s). Simple but vulnerable to traffic bursts at window edges.
- **Sliding Log**: Stores exact timestamps of each request; checks how many fall within a rolling window. More accurate but memory-hungry and needs cleanup.
- **Sliding Window Counter (Sub-windows)**: Divides the main window into smaller sub-windows, each tracking its own count. Slides by one sub-window at a time. More accurate but complex.
- **Sliding Window Counter (Weighted)**: Uses fixed windows but applies a percentage weight based on how much the sliding window overlaps each fixed window. Simpler but can over-admit traffic when requests are clustered at window edges.
- **Token Bucket**: A bucket holds N tokens. Each request consumes one token. A refiller adds tokens at a fixed rate. If the bucket is empty, the request is denied. Most common and flexible.
- **Leaky Bucket**: Requests queue up and are processed at a fixed rate. Smooths out bursts but adds latency and the queue becomes a bottleneck.
- **AOP (Aspect-Oriented Programming)**: The mechanism Spring uses to intercept method calls. Resilience4j hooks into your method via an AOP proxy — the rate-limiting logic runs before your actual code executes.
- **Fallback Method**: An alternative method called when the rate limiter (or circuit breaker, etc.) rejects a request. Must match the original method's signature plus a `Throwable` parameter.
- **Limit-for-period**: The maximum number of tokens (requests) allowed per refresh period — effectively the bucket capacity.
- **Limit-refresh-period**: How often the bucket is refilled (e.g., every 10 seconds).
- **Timeout-duration**: How long a request waits for a token before being rejected outright.
- **HTTP 429**: "Too Many Requests" — the standard HTTP status code a rate limiter returns when it denies a request.

## Interview Q&A

**Q1: What is a cascading failure and how does a rate limiter help prevent it?**
A1: A cascading failure happens when one slow downstream service causes the calling service's threads to pile up waiting. Eventually the calling service's thread pool exhausts, and it starts rejecting requests too — spreading the failure up the chain. A rate limiter prevents this by capping how many requests can be in-flight to the downstream service at any time. When the limit is hit, new requests immediately get the fallback response instead of waiting and consuming threads.

**Q2: Why should rate limiter be applied before retry in the Resilience4j chain?**
A2: Because retrying a request that is going to get blocked by the rate limiter wastes CPU, threads, and network resources. If you retry first and rate-limit second, you might retry 3 times only for all 3 attempts to get blocked. Applying rate limiter first means blocked requests fail fast and are never retried — saving resources.

**Q3: What is the difference between Token Bucket and Leaky Bucket?**
A3: Token Bucket allows bursts up to the bucket capacity — if 5 tokens have accumulated, 5 requests can come in simultaneously. Leaky Bucket processes requests at a strictly fixed rate regardless of burst — requests queue up and drain one at a time. Token Bucket gives more flexibility and lower latency; Leaky Bucket gives smoother output at the cost of added queue latency.

**Q4: What happens if you set `limit-for-period=2` and `limit-refresh-period=10s` and send 3 requests in 1 second?**
A4: The first two requests each consume one token and succeed. The third request finds no token available. It waits for up to `timeout-duration` (e.g., 1 second). If no new token is added within that wait (new tokens only arrive every 10 seconds), the third request is rejected and routed to the fallback method, which returns something like "Rate limit exceeded. Try again later."

**Q5: What is the biggest edge-case weakness of the Fixed Window Counter algorithm?**
A5: The boundary burst problem. If your limit is 5 per 10-second window and 5 requests arrive in the last second of window 1, and 5 more arrive in the first second of window 2, your system accepts 10 requests in 2 seconds — double the intended rate — even though no window was exceeded individually. Sliding window algorithms solve this.

**Q6: How does Resilience4j's `@RateLimiter` actually intercept method calls internally?**
A6: It uses Spring AOP. When you annotate a method with `@RateLimiter`, Resilience4j registers an AOP aspect that wraps the method in a proxy. Before the actual method body runs, the aspect executes the rate-limiting logic (token bucket check). If a token is available, it calls `proceed()` to run the real method. If not, it throws a `RequestNotPermitted` exception, which triggers the fallback method.

**Q7: Why must the fallback method have the same signature as the original method?**
A7: Resilience4j uses reflection to find the fallback method at runtime. It looks for a method with the exact same name, return type, and parameter types as the original — plus one extra `Throwable` parameter at the end. If the signature doesn't match, the framework cannot find the fallback and falls back to a default internal handler, which may not behave the way you intend.

**Q8: What happens if you set the Token Bucket capacity too high without careful calculation?**
A8: Accumulated tokens can allow a sudden, massive burst of traffic to pass through simultaneously — defeating the purpose of rate limiting. For example, if capacity is 1,000 and traffic has been low for hours, all 1,000 requests can come in within one second. You must set bucket capacity based on what your downstream service can actually handle concurrently, not just pick an arbitrary large number.

## Common Mistakes

1. **Setting token capacity arbitrarily large**: Engineers pick a round number like 1,000 without considering what the downstream service can handle. This allows burst traffic spikes that overwhelm the downstream service — the opposite of what a rate limiter is meant to do. Always calculate capacity based on downstream throughput limits.

2. **Applying retry before rate limiter**: Wrapping the rate limiter inside a retry means failed requests (ones that would be blocked anyway) get retried multiple times, wasting threads and CPU. Always apply rate limiter first, retry last.

3. **Wrong fallback method signature**: The fallback method must match the original method's return type and parameters exactly, with an additional `Throwable` at the end. A missing parameter, wrong return type, or wrong method name means the framework silently uses its own default fallback — which may not return the user-friendly response you wrote.

4. **Forgetting that rate limiter config is per-instance name**: The `name=` in `@RateLimiter(name = "productRateLimiter")` must exactly match the key in `application.properties` under `resilience4j.ratelimiter.instances.productRateLimiter`. A typo means the annotation uses Resilience4j's global defaults silently, and your custom limits are never applied.

5. **Confusing rate limiter with circuit breaker**: A rate limiter controls *how many* requests pass through per time window — it protects against volume. A circuit breaker detects *failure rate* and stops calls entirely when a downstream service is unhealthy. They solve different problems and are meant to be used together, not interchangeably.