# Spring Boot Actuator in Depth

## What is this? (Plain English)

Think of the dashboard warning lights and diagnostic port in a car: you don't need to open the engine to know the oil level, coolant temperature, or whether the check-engine light is on — you just plug in a diagnostic reader and read the data. Spring Boot Actuator is that diagnostic port for your running application. Instead of guessing whether your app is healthy, how much memory it's using, or what's happening inside its thread pool, Actuator exposes a set of ready-made HTTP endpoints that let you (or your monitoring tooling) query the live internal state of the application — without adding any of that plumbing yourself.

## The Problem It Solves

Once an application is deployed and running in production, you need visibility into it that source code alone doesn't give you:
- **Is the application actually up and healthy** — and not just "the process is running," but "the app plus its dependencies (DB, cache, message broker, etc.) are all in a good state"?
- **What is the runtime behavior** — memory usage, garbage collection activity, thread pool sizes, HTTP request counts/latencies?
- **What is happening right now**, e.g. diagnosing a deadlock or a thread leak via a thread dump?
- **How do you extend this** to include your own custom checks (like a DB health check) or your own custom management operations, without writing a full controller/security stack from scratch?
- **How do you feed this data into a monitoring platform** (Datadog, Prometheus, CloudWatch, etc.) so it can be visualized and alerted on, instead of being stuck only accessible via raw HTTP calls?

Actuator answers all of this with a single dependency plus configuration — it provides production-ready endpoints for health, metrics, environment, thread state, and more, and lets you plug in custom logic and custom endpoints into the same framework.

## Actuator Endpoint Request Flow

*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

```text
HTTP Request: GET /manage/health
        |
        v
 Is endpoint exposed? (management.endpoints.web.exposure.include)
        |
   +----+---------------------------------+
   | not in include list                  | exposed
   | (default: only health, info exposed) |
   v                                       v
404 Not Found              Security Filter Chain
                            (health, info => permitAll
                             everything else => authenticated)
                                       |
                                       v
                              Authenticated? -- No --> 401 Unauthorized
                                       |
                                      Yes / not required
                                       v
                          Endpoint Handler Dispatch
                                       |
            +--------------------------+--------------------------+
            |                          |                           |
            v                          v                           v
    Health Endpoint            Metrics Endpoint          Custom Actuator Endpoint
            |                          |                  (@Endpoint id=myCustomStats)
   +--------+--------+                 |                           |
   v                 v                 v                    HTTP method + selectors
DatabaseHealthIndicator  CacheHealthIndicator                       |
   .health()               .health()               +----------+----------+---------+
       |                       |                    |          |                    |
       +-----------+-----------+                   GET        POST                DELETE
                   v                                 |          |                    |
        Aggregate Status                    @ReadOperation  @WriteOperation   @DeleteOperation
   (UP only if all components UP)              method       (auth required)   (auth required)
                   |                                |          |                    |
    show-details=always? --yes--> status+details     |          |                    |
                   |                                 |          |                    |
                  no                                 |          |                    |
                   v                                 |          |                    |
          aggregated status only          MeterRegistry lookup  |                    |
                   |                    (jvm.memory.used, etc.) |                    |
                   |                          |                 |                    |
                   +--------------------------+-----------------+--------------------+
                                               v
                                        HTTP Response
```

## Key Code / Config

### 1. Dependency (pom.xml)

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

This is the only dependency required to bring Actuator into a project — new or existing.

### 2. Base configuration (application.properties)

```properties
# Optional. Default base path is /actuator. Here it is overridden to /manage.
management.endpoints.base-path=/manage

# Optional. Default: only "health" and "info" endpoints are exposed over the web.
# "*" exposes all available endpoints (metrics, loggers, threaddump, env, beans, etc).
# To expose a specific subset instead of everything, use a comma-separated list, e.g.:
# management.endpoints.web.exposure.include=health,info,metrics,loggers
management.endpoints.web.exposure.include=*

# By default, the health endpoint only shows the aggregated status (never shows details).
# "always" shows the full breakdown for every registered health indicator.
management.endpoint.health.show-details=always

# heapdump and shutdown are considered critical/dangerous endpoints:
# - shutdown stops the application.
# - heapdump can expose sensitive info (tokens, passwords, etc. present in memory).
# Even with exposure set to "*", these two remain blocked until explicitly unrestricted.
management.endpoint.heapdump.access=unrestricted
management.endpoint.shutdown.access=unrestricted
```

With the above, endpoints are reachable at `/manage/health`, `/manage/metrics`, `/manage/metrics/{metricName}`, `/manage/threaddump`, `/manage/heapdump`, `/manage/shutdown`, `/manage/env`, `/manage/beans`, `/manage/loggers`, etc. (base path `/actuator` is used instead of `/manage` if `management.endpoints.base-path` is not set).

### 3. Custom health indicators (DB + cache)

```java
@Component
public class DatabaseHealthIndicator implements HealthIndicator {

    @Override
    public Health health() {
        boolean dbIsUp = checkDatabaseConnection(); // simulate/perform an actual DB check in production
        if (dbIsUp) {
            return Health.up().withDetail("message", "DB available").build();
        }
        return Health.down().withDetail("message", "DB not available").build();
    }

    private boolean checkDatabaseConnection() {
        return true; // for demo purposes
    }
}
```

```java
@Component
public class CacheHealthIndicator implements HealthIndicator {

    @Override
    public Health health() {
        boolean cacheIsUp = checkCacheStatus();
        if (cacheIsUp) {
            return Health.up().withDetail("message", "Cache available").build();
        }
        return Health.down().withDetail("message", "Cache not available").build();
    }

    private boolean checkCacheStatus() {
        return false; // forced down, for demo purposes
    }
}
```

Every registered `HealthIndicator` bean becomes a named sub-component under `/health`. The top-level aggregated status is `UP` only if **every** sub-component is `UP`; if any one sub-component is `DOWN`, the overall aggregated status is also `DOWN`. With `show-details=always`, the response includes each sub-component's individual status and detail message (e.g. `DB available`, `Cache not available`); without it, only the single aggregated top-level status is returned.

### 4. Useful built-in metrics endpoints

```
GET /manage/metrics                         -> list of all available metric names
GET /manage/metrics/executor.pool.core      -> thread pool executor core size info
GET /manage/metrics/jvm.memory.used         -> current memory used by the JVM
GET /manage/metrics/jvm.memory.max          -> maximum memory the JVM can use
GET /manage/metrics/jvm.gc                  -> GC event count, total time spent, longest pause
GET /manage/metrics/http.server.requests    -> total request count, total time spent, longest single request
GET /manage/threaddump                      -> full thread dump (thread state: RUNNABLE/BLOCKED/WAITING, stack traces)
GET /manage/heapdump                        -> heap dump (restricted; requires access=unrestricted)
```

### 5. Custom actuator endpoint

```java
@Component
@Endpoint(id = "myCustomStats")
public class MyCustomStatsEndpoint {

    // GET /manage/myCustomStats
    @ReadOperation
    public String readAll() {
        return "Hello Spring Boot";
    }

    // GET /manage/myCustomStats/{name}/{message} — matched via selectors, in sequence
    @ReadOperation
    public String readWithSelectors(@Selector String name, @Selector String message) {
        return "Hello " + name + ", " + message;
    }

    // POST /manage/myCustomStats — write operations are treated as critical, auth required
    @WriteOperation
    public String refresh() {
        return "refresh done";
    }

    // DELETE /manage/myCustomStats/{key} — delete operations are treated as critical, auth required
    @DeleteOperation
    public String reset(@Selector String key) {
        return "reset done for " + key;
    }
}
```

The custom endpoint also needs to be exposed like any other, either explicitly (`management.endpoints.web.exposure.include=myCustomStats,...`) or via `*`. `@ReadOperation` maps to `GET`, `@WriteOperation` maps to `POST`, `@DeleteOperation` maps to `DELETE`, and `@Selector` parameters act as path placeholders matched in sequence after the endpoint id. This same custom-endpoint mechanism is what many Spring frameworks use internally — e.g. Spring Cloud Config's refresh-scope endpoint.

### 6. Securing actuator endpoints

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
</dependency>
```

```java
@Configuration
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/manage/health", "/manage/info").permitAll()
                // e.g. .requestMatchers("/manage/**").hasRole("ADMIN") is an alternative
                .anyRequest().authenticated()
            )
            .httpBasic(Customizer.withDefaults()); // basic auth, for testing purposes
        return http.build();
    }
}
```

```properties
spring.security.user.name=admin
spring.security.user.password=admin123
```

All actuator endpoints (`/health`, `/info`, `/metrics/*`, etc.) are public HTTP endpoints by default — anyone who knows the URL and port can call them, and some expose sensitive system information. `@WriteOperation` and `@DeleteOperation` on custom endpoints are always treated as critical by Spring Boot and require authentication, even without any extra configuration; `@ReadOperation` endpoints are reachable without authentication unless the security filter chain says otherwise.

### 7. Pushing metrics to a monitoring platform (e.g. Datadog)

```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-datadog</artifactId>
</dependency>
```

```properties
management.datadog.metrics.export.api-key=YOUR_DATADOG_API_KEY
management.datadog.metrics.export.enabled=true
management.datadog.metrics.export.step=5s
```

With the Micrometer Datadog registry dependency and the above config, Actuator's metrics (e.g. `http.server.requests`, JVM memory, GC stats) are automatically pushed to Datadog every 5 seconds and become visible as graphs under Datadog's Metrics summary/explore views. (In a real deployment, the API key should come from an environment variable / secret store, not be committed to `application.properties`.)

## Important Concepts

- **Actuator**: Provides production-ready HTTP endpoints to monitor and manage a running Spring Boot application, via a single starter dependency.
- **`management.endpoints.base-path`**: Optional; changes the endpoint prefix from the default `/actuator` to a custom path (e.g. `/manage`).
- **`management.endpoints.web.exposure.include`**: Optional; controls which endpoints are reachable over HTTP. Default exposes only `health` and `info`. `*` exposes all; a comma-separated list exposes a specific subset.
- **`HealthIndicator`**: Interface for plugging custom checks (DB, cache, message broker, etc.) into the `/health` endpoint. The aggregated top-level status is `UP` only if every registered indicator reports `UP`.
- **`management.endpoint.health.show-details`**: Optional (`never` by default); `always` reveals each sub-component's individual status/details, not just the aggregated top-level status.
- **Metrics endpoint (`/metrics`, `/metrics/{name}`)**: Lists and exposes individual metrics — JVM memory usage, garbage collection stats, thread pool sizes, HTTP request counts/latency, and more.
- **Thread dump / heap dump**: `/threaddump` helps diagnose deadlocks and thread leaks (thread state + stack traces). `/heapdump` and `/shutdown` are blocked by default even when exposure is `*`, and require `management.endpoint.<id>.access=unrestricted` because they can leak sensitive data or stop the application.
- **Custom actuator endpoints (`@Endpoint`, `@ReadOperation`, `@WriteOperation`, `@DeleteOperation`, `@Selector`)**: Lets you add your own management operations exposed the same way as built-in endpoints; write/delete operations are always treated as critical and require authentication.
- **Security**: All actuator endpoints are public by default; secure them the same way as any other endpoint via Spring Security (permit `health`/`info`, authenticate everything else, or apply role-based rules to the actuator path prefix).
- **Metrics export**: Micrometer registries (e.g. `micrometer-registry-datadog`) let Actuator push its metrics on a schedule to external monitoring platforms like Datadog, Prometheus, or CloudWatch.

## Interview Q&A

**Q1: What is the minimum you need to add Actuator to a Spring Boot project?**
A: Just the `spring-boot-starter-actuator` dependency. No other code is required to get default endpoints like `/actuator/health` and `/actuator/info` working.

**Q2: By default, which actuator endpoints are exposed over HTTP, and how do you expose more?**
A: Only `health` and `info` are exposed by default. To expose more, set `management.endpoints.web.exposure.include` to a comma-separated list of endpoint names, or `*` to expose all available endpoints.

**Q3: If you add three custom `HealthIndicator` beans and one of them reports `DOWN`, what does `/health` return, and how do you see which specific component failed?**
A: The aggregated top-level status will be `DOWN`, since the overall status is `UP` only when every sub-component is `UP`. To see which specific component failed and why, set `management.endpoint.health.show-details=always`, which returns each sub-component's individual status and detail message instead of just the aggregated status.

**Q4: Why are `/shutdown` and `/heapdump` still blocked even after setting `management.endpoints.web.exposure.include=*`?**
A: They're considered critical/dangerous — `shutdown` stops the running application, and `heapdump` can expose sensitive in-memory data like tokens and passwords. Spring Boot requires an explicit extra opt-in per endpoint (`management.endpoint.<id>.access=unrestricted`) as confirmation that the risk has been accepted, separate from just exposing the endpoint.

**Q5: How do you add a fully custom actuator endpoint, and how does Spring Boot pick which method to invoke?**
A: Annotate a Spring-managed bean class with `@Endpoint(id = "...")`. Inside it, `@ReadOperation` maps to GET, `@WriteOperation` to POST, and `@DeleteOperation` to DELETE. Method dispatch is based on matching the HTTP method plus any `@Selector` path parameters (matched in sequence) declared on the candidate methods.

**Q6: Do custom actuator endpoints need authentication?**
A: `@ReadOperation` (GET) endpoints are reachable without authentication unless your security config says otherwise. `@WriteOperation` and `@DeleteOperation` are always treated by Spring Boot as critical operations and require authentication regardless of other config, since they can change or delete state.
