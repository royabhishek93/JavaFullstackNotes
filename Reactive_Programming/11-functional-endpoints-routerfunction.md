> **Sequence 11/19 (Tier 3 👍)** — See [README.md](README.md) for the full ranked index.

# Functional endpoints: `RouterFunction`/`HandlerFunction` vs `@RestController`

**Interview framing:** "Spring WebFlux supports both `@RestController` annotated endpoints AND a completely different 'functional endpoint' style (`RouterFunction`/`HandlerFunction`). When would an architect mandate the functional style?"

**Easy English explanation of the functional style:** instead of annotations (`@GetMapping`, `@RestController`) doing "magic" routing behind the scenes, you **explicitly compose** routing as pure functions:

- A **`HandlerFunction<ServerResponse>`** — takes a `ServerRequest`, returns a `Mono<ServerResponse>`. This is your actual request-handling logic.
- A **`RouterFunction`** — declares which `RequestPredicate` (e.g., `GET /hello`) maps to which `HandlerFunction`.

```java
@Configuration
public class HelloRouter {

    @Bean
    public RouterFunction<ServerResponse> routerConfig(HelloHandler handler) {
        return RouterFunctions.route()
            .GET("/hello", handler::hello)
            .GET("/hello/{name}", handler::helloWithName)
            .build();
    }
}

@Component
public class HelloHandler {

    public Mono<ServerResponse> hello(ServerRequest request) {
        Flux<String> data = Flux.just("Hello", "World");
        return ServerResponse.ok().body(data, String.class);
    }

    public Mono<ServerResponse> helloWithName(ServerRequest request) {
        String name = request.pathVariable("name");
        Mono<String> response = Mono.just("Your name is " + name);
        return ServerResponse.ok().body(response, String.class);
    }
}
```

**Common gotcha (a real "producer type is unknown" `IllegalArgumentException`):** `ServerResponse.ok().body(...)` always expects a **`Publisher`** (a `Mono`/`Flux`), never a raw value. If you build a plain `String` response and pass it directly to `.body()`, you'll get a runtime error — always wrap single values with `Mono.just(...)` first.

**Why an architect might mandate this style over annotated controllers:**
- **Explicit composition over annotation magic** — routing logic is plain Java code you can read top-to-bottom, unit test as pure functions, and compose/refactor without relying on classpath scanning or reflection-based dispatch. Useful in library/gateway-style code where predictability matters more than developer convenience.
- **Fine-grained control over content negotiation** — e.g., explicitly setting `Content-Type: text/event-stream` to stream Server-Sent Events (SSE) for a live feed use case (stock ticker, live dashboard, notification stream), something you'd otherwise configure indirectly via annotations.

```java
public Mono<ServerResponse> streamPrices(ServerRequest request) {
    Flux<Price> prices = priceService.streamLivePrices().delayElements(Duration.ofSeconds(1));
    return ServerResponse.ok()
        .contentType(MediaType.TEXT_EVENT_STREAM)
        .body(prices, Price.class);
}
```

**The trade-off (what to actually tell your team):** annotated controllers (`@RestController`) are simpler, more familiar to teams coming from Spring MVC, and sufficient for 90% of typical CRUD-style reactive APIs. Functional endpoints add value in specific cases — API gateways, highly dynamic routing, or teams that want testable pure-function handlers without Spring's annotation-processing layer in the loop. Don't mandate functional style just because it's "more reactive-native" — it's a stylistic/architectural choice, not a performance one; both compile down to the same non-blocking Netty runtime.

> **One-line takeaway:** Functional endpoints (`RouterFunction`/`HandlerFunction`) trade annotation convenience for explicit, composable, easily-unit-tested routing — reach for them in gateway/library-style code, not as a default replacement for `@RestController` in ordinary CRUD services.

---
**Next:** [12-stepverifier-testing.md](12-stepverifier-testing.md)
