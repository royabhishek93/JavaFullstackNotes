> **Sequence 06/19 (Tier 1 🔥)** — See [README.md](README.md) for the full ranked index. Related: [02-blocking-call-poisons-event-loop.md](02-blocking-call-poisons-event-loop.md).

# `WebClient` vs `RestTemplate`/Feign for inter-service calls

**Interview framing:** "Two microservices need to talk to each other. What client should you use in a reactive service, and why does it matter?"

**Easy English explanation:**
- `RestTemplate` — **blocking**. Deprecated/maintenance-mode in modern Spring.
- Feign client (declarative REST client, common in Spring Cloud) — **blocking** by default.
- `WebClient` — **non-blocking**, built specifically for reactive stacks, part of the `spring-boot-starter-webflux` dependency.

**Why it matters in production:** calling a **blocking** client (`RestTemplate`/Feign) from inside a reactive pipeline reintroduces the exact thread-blocking problem WebFlux exists to avoid (see [02-blocking-call-poisons-event-loop.md](02-blocking-call-poisons-event-loop.md)) — it blocks an event-loop thread while waiting for the downstream service's HTTP response, just like the original Tomcat problem, except now inside your "reactive" service.

```java
// Non-blocking inter-service call, preserves the reactive chain end-to-end
public Mono<InventoryResponse> getInventory(String skuId) {
    return webClient.get()
        .uri("/inventory/{skuId}", skuId)
        .retrieve()
        .bodyToMono(InventoryResponse.class);
}
```

> **One-line takeaway:** In a WebFlux service, always use `WebClient` for outbound calls — using `RestTemplate`/blocking Feign inside a reactive chain silently defeats the entire architecture.

---
**Next:** [07-stream-vs-flux-replayability.md](07-stream-vs-flux-replayability.md) (Tier 2 — core reactive semantics)
