> **Sequence 01/19 (Tier 1 🔥)** — See [README.md](README.md) for the full ranked index.

# Why choose Spring WebFlux over Spring MVC? Netty vs Tomcat

**Interview framing:** "Why would an architect choose Spring WebFlux over Spring MVC for a new microservice? What production problem does it actually solve?"

**The production scenario:** a microservice built on Spring MVC (running on **Tomcat**) starts timing out under a real traffic spike (e.g., a flash sale, Black Friday load). Requests queue up and clients see timeouts, even though the server "isn't doing much work" per request — it's mostly waiting on a slow downstream DB call or another microservice's REST API.

**Easy English explanation — the Tomcat thread-per-request model:**

Tomcat uses a **thread-per-request model**: every incoming HTTP request is handed to one thread from a fixed-size pool (e.g., 200 threads), and that thread is **occupied for the entire request lifecycle** — including any time spent **blocked** waiting on a DB query, a downstream REST call, or disk I/O. If that DB call takes 3 seconds, the thread just sits idle for 3 seconds, unable to do anything else, but still counted as "busy" from the server's perspective.

Under high concurrent load in a microservices environment (lots of small, chatty, I/O-bound calls), you run out of threads long before you run out of CPU — the server can't accept new requests even though it's mostly just *waiting*, not computing. The "solution" teams often reach for is **buying bigger/more servers** — which costs real money and doesn't fix the underlying inefficiency.

**How Spring WebFlux solves it — Netty + non-blocking I/O:**

Spring WebFlux (added in Spring Framework 5.0) runs on **Netty** by default instead of Tomcat, using an **event-loop, non-blocking I/O model**. When a WebFlux handler starts an I/O operation (DB call, downstream HTTP call), the handling thread does **not block and wait** — it's released back to the pool to handle other requests. When the I/O operation's data becomes available, **any available thread** picks up processing that result and continues. A small, fixed number of event-loop threads (often just a handful, e.g. `2 × CPU cores`) can service **far more concurrent connections** than Tomcat's thread-per-request model, because threads are never wasted sitting idle on I/O.

```java
@RestController
public class OrderController {
    @GetMapping("/orders")
    public Flux<Order> streamOrders() {
        return orderRepository.findAll(); // reactive repository, non-blocking end-to-end
    }
}
```

Proof this is really non-blocking: add `.log()` and watch the thread names — you'll see the subscription and each emission handled by **different threads** (`parallel-1`, `parallel-2`, `reactor-http-nio-2`, etc.), not one thread blocked start-to-finish.

> **One-line takeaway:** WebFlux/Netty doesn't make individual requests faster — it makes the server handle **far more concurrent requests with far fewer threads**, by never letting a thread sit idle waiting on I/O. This is a **scalability/cost** decision, not a raw-speed decision.

---
**Next:** [02-blocking-call-poisons-event-loop.md](02-blocking-call-poisons-event-loop.md) — the trap that undoes this entire benefit.
