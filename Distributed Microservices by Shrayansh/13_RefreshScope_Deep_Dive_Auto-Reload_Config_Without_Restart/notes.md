# RefreshScope — Auto-Reload Config Without Restart

## What is this? (Plain English)

Centralized configuration (Spring Cloud Config) solves *where* config lives, but not *when* a running instance notices a change. By default, config is read once at startup — if someone edits a value in the central Git repo while your service is already running, your service keeps using the stale value forever, until you restart it. `@RefreshScope` plus the Actuator's `/actuator/refresh` endpoint solves exactly this: **updating configuration values in a live application without a restart.**

## How It Works

`@RefreshScope` marks a bean as eligible for dynamic refresh. "Refresh" literally means: **destroy the old bean instance, create a brand-new one using the latest property values.** This refresh doesn't happen automatically on its own — it's triggered by calling an endpoint that Spring Cloud Config's Actuator integration exposes: `POST /actuator/refresh`.

The behavior of that endpoint depends on **where** you call it:
- Called on the **Config Server** → it re-fetches the latest files from the Git repository (updates its own cache).
- Called on a **Config Client** (e.g. `order-service`) → it does two things: (1) calls the Config Server to fetch the latest values, then (2) destroys and recreates every bean marked `@RefreshScope` using those new values.

```
Lanes: Admin | CS = Config Server | Git = Git Repo | OS = Order Service (@RefreshScope beans)

1)  Admin ──────────> CS   : POST /actuator/refresh
2)  CS    ──────────> Git  : fetch latest properties
3)  CS    <────────── Git  : updated values
4)  Admin ────────────────────────────> OS   : POST /actuator/refresh
5)  OS    ──────────> CS   : fetch latest properties
6)  OS    <────────── CS   : updated values
7)  OS    ──(self-call)─>      : destroy old @RefreshScope beans, create new ones
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## Architecture Diagram

```
  BEFORE /actuator/refresh:
  +-----------------------------+
  | OrderProperties (instance A)|  <-- @RefreshScope, @ConfigurationProperties
  | message = "old value"       |
  +-----------------------------+
              ^
              | injected into
  +-----------------------------+
  | OrderController (NOT        |
  | refresh-scoped, stateless)  |
  +-----------------------------+

  AFTER /actuator/refresh:
  +-----------------------------+
  | OrderProperties (instance A)| --X destroyed
  +-----------------------------+
  +-----------------------------+
  | OrderProperties (instance B)|  <-- brand-new instance, new value
  | message = "new value"       |
  +-----------------------------+
              ^
              | OrderController now points to instance B
```

## The Critical Trap: Never Put `@RefreshScope` on a Controller or Service

Since refresh literally **destroys and recreates the bean**, any in-flight request being handled by that exact bean instance is at risk, and **any state held in that object is lost** the moment refresh runs. If you accidentally put `@RefreshScope` on a `@RestController` or `@Service`, an admin calling `/actuator/refresh` at the wrong moment could drop an in-flight request or wipe out object state.

**The safe pattern:** only ever apply `@RefreshScope` to a **stateless configuration holder** — specifically, a class annotated `@ConfigurationProperties`. This is a plain POJO whose only job is holding config values (no business logic, no request-scoped state), so destroying and recreating it has zero risk.

```java
@Component
@RefreshScope
@ConfigurationProperties(prefix = "custom")
public class OrderProperties {
    private String message;  // maps to custom.message in the properties file
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
}
```
```java
@RestController
public class OrderController {

    @Autowired
    private OrderProperties orderProperties; // NOT refresh-scoped itself — safe

    @GetMapping("/order/fetch")
    public String fetch() {
        return "Fetch order and message: " + orderProperties.getMessage();
    }
}
```

**Proof this matters (from a live demo):** putting `@RefreshScope` directly on the controller and tracking a request counter showed the counter reset from 2 back to 1 after calling `/actuator/refresh` — even though the underlying property value hadn't changed. The bean was destroyed and a fresh instance created either way, silently discarding any state (like that counter) the old instance was holding.

## Key Code / Config

```xml
<!-- Both Config Server AND Config Client need this -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```
```properties
# Must expose the refresh endpoint explicitly — it's not exposed by default
management.endpoints.web.exposure.include=refresh
```

### The refresh sequence in practice
```
1. Edit order-service-dev.properties in the central Git repo, push it.
2. POST http://localhost:8888/actuator/refresh   (on the Config Server)
   -> Config server re-fetches from Git, caches the new values.
3. POST http://localhost:8080/actuator/refresh   (on order-service itself)
   -> Order service calls the config server, gets the new values,
      destroys + recreates every @RefreshScope bean.
4. GET  http://localhost:8080/order/fetch
   -> Now returns the UPDATED message, with zero application restart.
```

## Scaling This to Many Services — the Next Problem

Calling `/actuator/refresh` manually on every one of your hundreds of microservices doesn't scale. The alternative: refresh the Config Server once, and have it **broadcast** a refresh event to every client automatically via a message bus — that's exactly what **Spring Cloud Bus** does (covered separately), turning a single refresh call into a fleet-wide propagation instead of N manual calls.

## Important Concepts

- **`@RefreshScope`**: Marks a bean as eligible for dynamic reload — on refresh, Spring destroys the current instance and creates a new one populated with the latest configuration values.
- **`/actuator/refresh`**: A write (POST) endpoint exposed by Spring Cloud Config's Actuator integration. Behaves differently depending on whether it's called on the Config Server (re-fetch from Git) or a Config Client (fetch + recreate `@RefreshScope` beans).
- **Why `@ConfigurationProperties`, not `@Value`, for refresh-safe beans**: Both read properties correctly, but the safety concern is really about *where you put `@RefreshScope`* — always on a stateless POJO holder, never on a controller/service that holds request state or business logic.
- **State loss on refresh**: Refreshing a bean is destructive — any object state (counters, caches, in-flight work) held by that specific bean instance is lost. This is the core reason to never refresh-scope a controller or service.
- **One-by-one refresh doesn't scale**: Manually calling `/actuator/refresh` on every microservice instance is the naive approach; Spring Cloud Bus solves the fan-out problem by broadcasting the refresh event to all clients automatically.
