# API Gateway Part 2 — Filters: Authentication, Circuit Breaker, Retry, Rate Limiting

## What is this? (Plain English)

Filters are the mechanism that lets an API Gateway *do* something to a request or response as it passes through — add a header, verify a JWT, apply a circuit breaker, retry on failure, and so on. Spring Cloud Gateway has exactly two filter categories, and knowing which one to reach for is a common interview probe:

- **Global Filters**: run on **every** request that hits the gateway, no matter which route it matches. Best use case: authentication, centralized logging.
- **Route-Specific Filters** (a.k.a. Gateway Filters): run only for requests matching a **particular route**. Best use case: rate limiting, circuit breaker, retry — because different downstream services usually need different configurations.

## The Request/Response Filter Chain

```
┌─────────────────┐
│ Client Request   │
└────────┬─────────┘
         v
┌───────────────────────┐
│ DispatcherHandler      │
└────────┬───────────────┘
         v
┌─────────────────────────────────────────────┐
│ RouteMappingHandler                          │
│ (matches path -> Route object)                │
└────────┬──────────────────────────────────────┘
         v
┌───────────────────────────┐
│ Global Filter(s): pre-logic │
└────────┬─────────────────────┘
         v
┌────────────────────────────────────┐
│ Route-Specific Filter(s): pre-logic  │
└────────┬─────────────────────────────┘
         v
┌──────────────────────────────────────────────────────────────┐
│ Global Filter: RouteToRequestUrlFilter                         │
│ (resolves lb:// via service discovery + load balancing)        │
└────────┬─────────────────────────────────────────────────────┘
         v
┌──────────────────────────────────────────────┐
│ Global Filter: NettyRoutingFilter              │
│ (actually invokes the microservice)            │
└────────┬────────────────────────────────────────┘
         v
┌──────────────────────────────────┐
│ Microservice handles request      │
└────────┬───────────────────────────┘
         v
┌──────────────────────────────────────┐
│ Route-Specific Filter(s): post-logic   │
└────────┬───────────────────────────────┘
         v
┌────────────────────────────┐
│ Global Filter(s): post-logic │
└────────┬─────────────────────┘
         v
┌───────────────────────────────────────────────────────────────┐
│ Global Filter: NettyWriteResponseFilter                          │
│ (order=-1, runs pre-logic first, post-logic LAST)                │
└────────┬────────────────────────────────────────────────────────┘
         v
┌─────────────────┐
│ Client Request   │  (response delivered back)
└─────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

**The ordering trap interviewers probe for:** global filters appear *both before and after* route-specific filters in the chain — this isn't a bug, it's by design. Every filter (global or route-specific) has an **order value**: lower value = higher priority = runs earlier. Most global filters use small/negative order values so they run first. But two special global filters are deliberately given *very high* order values (lowest priority) so they run last in the pre-logic phase: `RouteToRequestUrlFilter` (order ~10000, resolves the actual instance URL via load balancing) and `NettyRoutingFilter` (must run last since it's the one that actually calls the microservice). Conversely, `NettyWriteResponseFilter` has `order = -1` (runs *first* in pre-logic, doing nothing there) specifically so that its **post-logic** — sending the response back to the client — runs **last**, after every other filter's post-logic has already executed. Filters are like a stack: whichever pre-logic runs first has its post-logic run last.

## Architecture Diagram

```
  Every request                          Only requests matching a route
       |                                              |
       v                                              v
 +----------------------+              +-------------------------------+
 |   GLOBAL FILTERS      |              |  ROUTE-SPECIFIC FILTERS       |
 |  (GlobalFilter+Ordered)|             |  (AbstractGatewayFilterFactory)|
 |  e.g. JWT Auth,        |             |  e.g. RateLimiter, Retry,      |
 |       Logging          |             |       CircuitBreaker, Headers |
 |  runs on ALL routes    |             |  runs on ONE route only        |
 +----------------------+              +-------------------------------+
       |                                              |
       +------------------ merged into ----------------+
                                |
                                v
                  Ordered filter chain (by getOrder()/index)
```

## How Filters Are Written

### Global Filter — JWT Authentication Example
```java
@Component
public class JwtAuthGlobalFilter implements GlobalFilter, Ordered {

    @Override
    public int getOrder() {
        return -1; // low value = high priority = runs early, before other filters
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();

        // Skip validation on the token-issuing endpoint itself — the gateway
        // only ever VERIFIES tokens, it never creates them.
        if (path.equals("/auth/login")) {
            return chain.filter(exchange);
        }

        String authHeader = exchange.getRequest().getHeaders().getFirst("Authorization");
        if (authHeader == null) {
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete(); // short-circuit, don't call chain.filter()
        }

        try {
            verifyJwtToken(authHeader); // your JWT validation logic
        } catch (Exception e) {
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }

        // chain.filter() is ASYNCHRONOUS — it does not block waiting for downstream.
        // Post-logic must be attached via Mono.fromRunnable so it only runs once
        // the response has actually come back.
        return chain.filter(exchange)
                .then(Mono.fromRunnable(() -> {
                    // post-logic here (e.g. logging), runs after response arrives
                }));
    }
}
```

### Route-Specific Filter — Using Pre-Existing Filters (no code required)
```properties
# Product route: remove a request header, add response header, retry on failure
spring.cloud.gateway.routes[0].id=product-service
spring.cloud.gateway.routes[0].uri=lb://PRODUCT-SERVICE
spring.cloud.gateway.routes[0].predicates[0]=Path=/products/**

spring.cloud.gateway.routes[0].filters[0].name=RemoveRequestHeader
spring.cloud.gateway.routes[0].filters[0].args.name=X-Internal-Debug

spring.cloud.gateway.routes[0].filters[1].name=AddResponseHeader
spring.cloud.gateway.routes[0].filters[1].args.name=X-Gateway-Response
spring.cloud.gateway.routes[0].filters[1].args.value=api-gateway

spring.cloud.gateway.routes[0].filters[2].name=Retry
spring.cloud.gateway.routes[0].filters[2].args.retries=4
spring.cloud.gateway.routes[0].filters[2].args.methods=GET,DELETE

spring.cloud.gateway.routes[0].filters[3].name=CircuitBreaker
spring.cloud.gateway.routes[0].filters[3].args.name=productServiceCB
spring.cloud.gateway.routes[0].filters[3].args.fallbackUri=forward:/fallback
```

**How the mapping works:** the filter `name` (e.g. `RemoveRequestHeader`) maps to a framework class named `RemoveRequestHeaderGatewayFilterFactory` — Spring Cloud Gateway automatically appends `GatewayFilterFactory` when resolving the name. Each factory class declares a `Config` inner class with the fields you can set via `args.*` (e.g. `name`, `value`). This is why the gateway's built-in circuit breaker filter uses `resilience4j.circuitbreaker.instances.<name>.*` properties — same Resilience4j configuration model covered in the Circuit Breaker topic, just wired in via the gateway's filter config instead of a `@CircuitBreaker` annotation.

### Custom Route-Specific Filter
```java
@Component
public class CustomRouteGatewayFilterFactory
        extends AbstractGatewayFilterFactory<CustomRouteGatewayFilterFactory.Config> {

    public CustomRouteGatewayFilterFactory() {
        super(Config.class);
    }

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            System.out.println("Pre-logic, country=" + config.getCountry());
            return chain.filter(exchange)
                    .then(Mono.fromRunnable(() -> System.out.println("Post-logic")));
        };
    }

    public static class Config {
        private String country;
        public String getCountry() { return country; }
        public void setCountry(String country) { this.country = country; }
    }
}
```
```properties
# name = class name prefix, minus the "GatewayFilterFactory" suffix (auto-appended)
spring.cloud.gateway.routes[0].filters[4].name=CustomRoute
spring.cloud.gateway.routes[0].filters[4].args.country=India
```

## Important Concepts

- **Global Filter**: Runs on every request regardless of route — implements `GlobalFilter` + `Ordered`. Best for auth and logging.
- **Route-Specific (Gateway) Filter**: Runs only for requests matching a specific route — implements/extends `AbstractGatewayFilterFactory`. Best for per-service rate limiting, circuit breaker, retry, header manipulation, and request/response transformation.
- **Filter Order**: Lower order value = higher priority = runs earlier in pre-logic (and later in post-logic, since filters unwind like a stack). Default: global filters get lowest-precedence-last unless specified; route-specific filters default to their index (0, 1, 2...).
- **Pre-logic vs Post-logic**: Code before `chain.filter(exchange)` runs on the way *in*; code attached via `.then(Mono.fromRunnable(...))` runs on the way *out*, after the response is available — because `chain.filter()` is asynchronous, not blocking.
- **`RouteToRequestUrlFilter`**: Global filter (very high order = runs last in pre-phase) that resolves the actual callable URL — including `lb://` service-discovery + load-balancing resolution.
- **`NettyRoutingFilter`**: Global filter that actually performs the network call to the resolved microservice instance.
- **`NettyWriteResponseFilter`**: Global filter with `order = -1` — empty pre-logic (so it starts early) but its post-logic (sending the response to the client) must run dead last, after every other filter's post-logic.
- **Fallback URI (`forward:/fallback`)**: When a circuit breaker filter trips, the gateway internally forwards the request to a local controller endpoint inside the gateway itself (no external network call) to produce a graceful degraded response.
