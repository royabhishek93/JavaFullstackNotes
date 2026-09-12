> **Sequence 02/19 (Tier 1 🔥)** — See [README.md](README.md) for the full ranked index. Builds on [01-why-webflux-over-mvc-netty-vs-tomcat.md](01-why-webflux-over-mvc-netty-vs-tomcat.md).

# The #1 production pitfall: one blocking call poisons the whole event loop

**Interview framing:** "What's the #1 production pitfall architects need to warn teams about when adopting WebFlux?"

**The trap:** WebFlux's benefit only exists if the **entire call chain is non-blocking, end-to-end**. A single blocking call anywhere inside a reactive pipeline — a legacy JDBC call, a `RestTemplate` call, a synchronous file read, even a rogue `Thread.sleep()` — **blocks one of the tiny number of event-loop threads**.

**Why this is *worse* than the equivalent mistake in Spring MVC:** Tomcat has ~200 threads to burn through before the server falls over. Netty's event loop might only have a handful of threads (e.g., 4–8). Blocking even ONE of them can stall a disproportionate share of ALL concurrent traffic on the server — a single bad blocking call in WebFlux has a much bigger blast radius than the same mistake in a traditional thread-per-request server.

**Concrete example of the mistake:**
```java
// BAD: blocking JDBC call executed inside a reactive pipeline — blocks an event-loop thread
public Mono<Order> getOrder(String id) {
    return Mono.fromCallable(() -> jdbcOrderRepository.findById(id)) // still blocking under the hood!
               .subscribeOn(Schedulers.boundedElastic()); // MUST offload blocking work like this
}
```
If you forget `.subscribeOn(Schedulers.boundedElastic())` (or don't have it at all), that blocking JDBC call runs directly on an event-loop thread.

**How to actually fix it:**
1. Use non-blocking drivers/clients everywhere in the chain: **R2DBC** instead of JDBC, **WebClient** instead of `RestTemplate`/Feign (see [06-webclient-vs-resttemplate-feign.md](06-webclient-vs-resttemplate-feign.md)), reactive Mongo/Redis drivers.
2. If you're forced to call a blocking API (legacy library, JDBC), explicitly offload it to a separate bounded thread pool with `.subscribeOn(Schedulers.boundedElastic())` so it doesn't steal an event-loop thread — this doesn't make the blocking call non-blocking, but it isolates the damage.

> **One-line takeaway:** WebFlux is only as non-blocking as its weakest link. One forgotten blocking call in the chain can degrade the entire server, not just that one request — this is the top production incident cause in early WebFlux adoptions.

---
**Next:** [03-publisher-subscriber-backpressure.md](03-publisher-subscriber-backpressure.md) — the mechanism that makes non-blocking flow control possible in the first place.
