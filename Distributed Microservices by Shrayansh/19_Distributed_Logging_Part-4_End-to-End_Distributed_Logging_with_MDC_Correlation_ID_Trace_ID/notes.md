# MDC, Correlation ID & Trace ID — End-to-End Distributed Logging

## What is this? (Plain English)

Think of every incoming request as a **package** moving through a chain of courier hubs (your microservices). At the very first hub, the package gets a **tracking number** stamped on it. Every hub it passes through writes its own notes ("received", "sorted", "dispatched") but always references that same tracking number. Later, if a customer complains about a lost package, you don't have to search every hub's entire logbook by hand — you just search for that one tracking number across all hubs and instantly see the package's full journey.

That tracking number is your **Correlation ID** (and, in a distributed system, the **Trace ID**). The mechanism that lets each hub "remember" the tracking number while writing its own notes — without you manually repeating it in every single log line — is called **MDC (Mapped Diagnostic Context)**.

MDC is a **per-thread key-value map**. You put a value in once (`MDC.put("correlationId", "T1")`), and from that point on, every log statement made **on that same thread** automatically has that value attached to it — without you passing it as a parameter to every log call. The catch: it's per-*thread*, not per-*request*. If your app reuses threads (thread pools) or spins up new threads (`@Async`), that per-thread nature causes two very real bugs covered below.

## The Problem It Solves

In a single log file (`app.log`) serving many concurrent requests, and in a distributed system where one request fans out across several microservices, you're faced with two problems:

1. **Attaching context to logs without repeating yourself.** You want every log line for a request to carry things like `paymentId`, `userId`, or a request ID — but manually passing these into every `log.info(...)` call everywhere in the codebase isn't practical.
2. **Finding "all the logs for this one request"** out of thousands of interleaved log lines — both within a single service, and across every service the request touched. Without a shared identifier stamped on every log line, there's no way to filter for just this request when a customer reports "my request failed."

Solving these cleanly surfaces two more subtle problems that trip engineers up in production:

- **Log pollution from thread reuse.** Thread pools reuse threads across different requests. If a request's MDC data isn't cleared before the thread is handed back to the pool, the *next* request to reuse that same thread inherits the previous request's stale MDC data (e.g., logs for "request B / user2" wrongly show `userId=user1`).
- **MDC doesn't cross thread boundaries.** MDC is per-thread. When a method runs `@Async` (creating a brand-new thread), that new thread gets its own **empty** MDC — the parent thread's context (`paymentId`, `userId`, correlation ID, etc.) is *not* copied over automatically.

## How MDC Flows Through a Request (Diagrams)

### Correlation ID / Trace ID flowing across services and into every log line

**ASCII version (same flow):**

```text
Client                Service A                       Service B                    Log Aggregator
  |                       |                               |                              |
  |--- HTTP request ----->|                                                              |
  |                       | ServerHttpObservationFilter: no traceId in header           |
  |                       |   -> generates traceId = T1                                 |
  |                       | CorrelationIdFilter: reuses T1 as correlationId             |
  |                       |   -> MDC.put(traceId=T1, correlationId=T1)                  |
  |                       | log.info("processing payment")  [traceId=T1, correlationId=T1]|
  |                       |                               |                              |
  |                       |--- call Service B, header traceId=T1 ---------------------->|
  |                       |                               | ServerHttpObservationFilter:  |
  |                       |                               |   traceId=T1 already in header|
  |                       |                               |   -> reuse it, no new id       |
  |                       |                               | CorrelationIdFilter: reuses T1 |
  |                       |                               |   -> MDC.put(traceId=T1, ...)  |
  |                       |                               | log.info("payment recorded")  |
  |                       |                               |   [traceId=T1, correlationId=T1]|
  |                       |<-------------- response ------|                              |
  |                       | MDC.clear() (finally block, both services)                  |
  |<-- resp header: X-Correlation-Id=T1 --|                                              |
  |                       |                               |                              |
  |-- "failed! correlationId T1" ------------------------------------------------------->|
  |<---------------------------- all log lines where traceId/correlationId = T1 ---------|
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

### MDC does NOT cross thread boundaries — how `TaskDecorator` fixes it for `@Async`

**ASCII version (same flow):**

```text
Parent thread                     TaskDecorator NOT set          TaskDecorator IS set
MDC = {paymentId=P1,                    |                              |
       userId=U1}                       |                              |
      |                                  |                              |
      | @Async call intercepted          |                              |
      | by Spring's proxy                |                              |
      v                                  |                              |
Runnable created (no MDC yet)            |                              |
      |                                  |                              |
      +---- decorator == null? ---------+---- decorator != null? ----->+
      |                                  |                              |
      |                          submitted as-is           decorate() runs on PARENT thread:
      |                                  |                    captures MDC.getCopyOfContextMap()
      |                                  |                              |
      |                                  v                              v
      |                       Worker thread runs it.         Wraps runnable:
      |                       Its own MDC is EMPTY.            1) MDC.setContextMap(parentMap)
      |                       logs show NO paymentId/userId    2) run actual task
      |                                                          3) MDC.clear() (finally)
      |                                                              |
      |                                                              v
      |                                                  Worker thread runs wrapped task.
      |                                                  MDC now = {paymentId=P1, userId=U1}
      |                                                  log.info(...) includes both fields
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## Key Code / Config

### 1. `logback-spring.xml` — three appenders showing how MDC data is read

```xml
<configuration>

    <!-- Prints only ONE specific MDC key's value: %X{key} -->
    <appender name="CONSOLE_MDC_SINGLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>%date %-5level %logger{36} - %msg paymentId=%X{paymentId}%n</pattern>
        </encoder>
    </appender>

    <!-- Prints ALL MDC key=value pairs: %X -->
    <appender name="CONSOLE_MDC_ALL" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>%date %-5level %logger{36} - %msg %X%n</pattern>
        </encoder>
    </appender>

    <!-- Structured JSON output - MDC fields are included automatically (includeMdc defaults to true) -->
    <appender name="CONSOLE_JSON" class="ch.qos.logback.core.ConsoleAppender">
        <encoder class="net.logstash.logback.encoder.LogstashEncoder">
            <includeMdc>true</includeMdc>
        </encoder>
    </appender>

    <logger name="com.concepts.paymentcontroller" level="INFO" additivity="false">
        <appender-ref ref="CONSOLE_MDC_SINGLE"/>
        <appender-ref ref="CONSOLE_MDC_ALL"/>
        <appender-ref ref="CONSOLE_JSON"/>
    </logger>

</configuration>
```

`%X` = print every key/value currently in the MDC (e.g. `paymentId=P123, userId=U123`). `%X{key}` = print only that one key's **value** (the key name itself is not printed). Be deliberate about what you put in the MDC — whatever is there gets attached to **every single log statement** on that thread, so an MDC with hundreds of fields will bloat every log line.

### 2. Simple usage + why `MDC.clear()` matters (avoiding log pollution)

```java
@RestController
public class PaymentController {

    private static final Logger log = LoggerFactory.getLogger(PaymentController.class);

    @GetMapping("/payment")
    public String getPayment(@RequestParam String paymentId, @RequestParam String userId) {
        try {
            MDC.put("paymentId", paymentId);
            MDC.put("userId", userId);

            log.info("payment is successful");
            return "OK";
        } finally {
            // MUST clear before the thread goes back to the pool.
            // Otherwise, the NEXT request that reuses this same thread will
            // inherit this request's paymentId/userId in its own logs (log pollution).
            MDC.clear();
        }
    }
}
```

**Log pollution example:** a thread pool has `Thread-1` and `Thread-2`. Request A (user1) is handed `Thread-1`, which sets `MDC = {userId=user1}`. If `MDC.clear()` is skipped, and Request B (user2) later reuses `Thread-1` from the pool, Request B's log lines will incorrectly show `userId=user1` — because the MDC map belongs to the thread, not the request.

### 3. `TaskDecorator` — copying the parent thread's MDC into an `@Async` child thread

```java
public class MdcTaskDecorator implements TaskDecorator {

    @Override
    public Runnable decorate(Runnable runnable) {
        // Runs on the PARENT thread, so we can still read its MDC here.
        Map<String, String> contextMap = MDC.getCopyOfContextMap();

        return () -> {
            try {
                if (contextMap != null) {
                    MDC.setContextMap(contextMap);
                }
                runnable.run();
            } finally {
                MDC.clear();
            }
        };
    }
}
```

```java
@Configuration
@EnableAsync
public class AsyncConfig {

    @Bean(name = "taskExecutor")
    public Executor taskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(5);
        executor.setMaxPoolSize(10);
        executor.setQueueCapacity(25);
        executor.setTaskDecorator(new MdcTaskDecorator()); // <-- wires MDC copy into every @Async task
        executor.initialize();
        return executor;
    }
}
```

Flow: `@Async` proxy intercepts the call → builds the actual `Runnable` → before submitting it to the executor's queue, it checks `taskDecorator != null` → if set, `decorate()` runs *while still on the parent thread*, captures the parent's MDC, and returns a **new** wrapped `Runnable` that sets the MDC, runs the real task, then clears the MDC → that wrapped runnable is what actually gets queued and picked up by a worker thread. `TaskDecorator` itself is a plain Spring Framework concept (`org.springframework.core.task.TaskDecorator`) — it has nothing to do with the logging framework; it's just a wrapper around a `Runnable`.

### 4. Correlation ID filter (works with or without distributed tracing enabled)

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 10) // run after the tracing filter so a traceId already exists, if any
public class CorrelationIdFilter extends OncePerRequestFilter {

    private static final String CORRELATION_ID_HEADER = "X-Correlation-Id";
    private static final String CORRELATION_ID_MDC_KEY = "correlationId";

    private final Tracer tracer; // io.micrometer.tracing.Tracer, only present if tracing is enabled

    public CorrelationIdFilter(@Autowired(required = false) Tracer tracer) {
        this.tracer = tracer;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                     FilterChain filterChain) throws ServletException, IOException {
        try {
            String correlationId = currentTraceId();
            if (correlationId == null) {
                // Tracing disabled/removed, or request came with its own id already -> fall back
                correlationId = request.getHeader(CORRELATION_ID_HEADER) != null
                        ? request.getHeader(CORRELATION_ID_HEADER)
                        : UUID.randomUUID().toString();
            }

            MDC.put(CORRELATION_ID_MDC_KEY, correlationId);
            response.setHeader(CORRELATION_ID_HEADER, correlationId);

            filterChain.doFilter(request, response);
        } finally {
            MDC.clear();
        }
    }

    private String currentTraceId() {
        if (tracer == null || tracer.currentSpan() == null) {
            return null;
        }
        return tracer.currentSpan().context().traceId();
    }
}
```

Why keep this filter even when distributed tracing (Micrometer + OpenTelemetry) already auto-generates a trace ID and auto-adds it to the MDC via `ServerHttpObservationFilter`? Two reasons from the video:

1. **The response header still needs to be set explicitly** — the tracing filter doesn't add the trace ID to the outgoing response for the client/developer to quote back later.
2. **Tracing might be disabled** in some environments/company policy. If the correlation logic only worked by reading an existing trace ID, it would break the moment tracing is turned off. The filter above falls back to generating its own ID when no trace ID is available, so it always works.

When Service A calls Service B, Micrometer's instrumentation automatically propagates the trace ID in the outgoing request header. Service B's own `ServerHttpObservationFilter` sees the header already has a trace ID and reuses it instead of creating a new one, then puts it into Service B's MDC. Since the exact same `CorrelationIdFilter` code is deployed to every service, every service ends up logging the same `traceId`/`correlationId` for that request — with zero extra propagation code needed between services.

### 5. `application.properties` — enabling tracing (Jaeger via Micrometer + OpenTelemetry)

```properties
# Send 100% of traces (tune down in real production traffic)
management.tracing.sampling.probability=1.0

# Jaeger/OTLP collector endpoint, as configured in the video
management.otlp.tracing.endpoint=http://localhost:4318/v1/traces

spring.application.name=order-service
```

## Important Concepts

- **MDC (Mapped Diagnostic Context)**: a per-thread key-value map. `MDC.put(key, value)` makes that value visible to the logging framework, which copies it into every subsequent log event's `MDC property map` field on that same thread.
- **How a log line actually gets MDC data**: `log.info(...)` (SLF4J) → the concrete implementation (Logback/Log4j2) converts it into an `ILoggingEvent` object → that event has an MDC-property-map field populated from the current thread's MDC → the logger level check accepts/rejects it → the appender's formatter (pattern encoder or JSON encoder) reads that event's MDC property map and writes it out.
- **`%X` vs `%X{key}`**: `%X` prints every MDC key/value pair; `%X{key}` prints only that key's value (not the key name).
- **`includeMdc` (JSON/logstash encoder)**: defaults to `true` — MDC fields are added automatically to the JSON output as `"key": "value"`.
- **Log pollution**: stale MDC data leaking into a different request's logs because a thread was reused from a thread pool without clearing its MDC first. Always `MDC.clear()` in a `finally` block.
- **MDC and thread boundaries**: a new thread (e.g. spawned by `@Async`) gets its own empty MDC — the parent thread's MDC is *not* inherited automatically.
- **`TaskDecorator`**: a Spring Framework wrapper around a `Runnable`, used to copy the parent thread's MDC snapshot into the child thread before it runs the real task, and clear it afterward. Not a logging-framework feature.
- **Correlation ID**: a unique ID assigned per request, added to the MDC (via a filter) so every log line for that request carries it, and returned in the response header so a developer can search log-aggregation tools (e.g. Datadog) by it later.
- **Trace ID vs Correlation ID**: Trace ID (from distributed tracing) tracks the *path* a request follows across microservices, but doesn't do detailed per-service logging. Correlation ID ties detailed log lines within each service to the same request. Since both are unique per request, most companies simply reuse the trace ID as the correlation ID rather than maintaining two separate IDs — simpler for the log aggregation tool, which can use one ID to get both the request's path and its logs.
- **`ServerHttpObservationFilter`**: the filter brought in by Micrometer tracing; on each request it reuses an existing trace ID from the incoming header (or creates one if absent), propagates it to downstream calls automatically, and adds it to the MDC.

## Interview Q&A

**Q1: What is MDC, and why is it scoped per-thread instead of per-request?**
A: MDC (Mapped Diagnostic Context) is a key-value map maintained by the logging framework, and it's scoped per-thread because that's the unit the logging framework has visibility into when a log statement executes — it doesn't inherently know about "requests." The logging framework reads whatever is in the current thread's MDC and attaches it to the `ILoggingEvent` it builds for that log statement, which the appender then formats and outputs. Because it's thread-scoped rather than request-scoped, thread reuse (thread pools) and new-thread creation (`@Async`) both need explicit handling — clearing on completion, and copying on hand-off to a new thread.

**Q2: What causes "log pollution," and how do you prevent it?**
A: It happens when a thread pool reuses a thread across requests. If Request A sets `MDC.put("userId", "user1")` on `Thread-1` and finishes without clearing it, and `Thread-1` is later handed to Request B (for `user2`), Request B's log lines will incorrectly show `userId=user1` because the MDC map belongs to the thread, not to the request. The fix is to always call `MDC.clear()` in a `finally` block once the request finishes — typically done inside a filter that wraps every request.

**Q3: Why doesn't MDC data show up in logs written inside an `@Async` method, and how do you fix it?**
A: MDC is per-thread, and `@Async` methods run on a brand-new thread from the executor pool, which starts with its own empty MDC — the parent thread's MDC is never copied automatically. The fix is a `TaskDecorator`: it runs on the parent thread just before the task is queued, captures a snapshot of the parent's MDC (`MDC.getCopyOfContextMap()`), and wraps the actual `Runnable` so that when the worker thread eventually runs it, it first restores that snapshot (`MDC.setContextMap(...)`), then runs the real logic, then clears the MDC. You register this decorator on your `ThreadPoolTaskExecutor` bean via `setTaskDecorator(...)`.

**Q4: What's the difference between a Trace ID and a Correlation ID, and why do many companies just use one ID for both?**
A: A Trace ID (from distributed tracing) tracks the *path* a request takes across microservices — which service called which — but doesn't capture detailed log content. A Correlation ID ties every detailed log line within a service to a single request. Both are unique per request, so instead of managing two separate identifiers, most companies simply reuse the trace ID as the correlation ID: it's already auto-generated, auto-propagated across service calls, and auto-added to the MDC by the tracing filter, so the log-aggregation tool can search on one ID and get both the request's cross-service path and every log line associated with it.

**Q5: If distributed tracing already puts a trace ID into the MDC automatically, why write a separate correlation ID filter at all?**
A: Two reasons. First, the tracing filter doesn't set the ID on the outgoing HTTP response, so a developer can't quote it back later when debugging a customer-reported issue — the correlation filter explicitly adds it to the response header. Second, tracing can be disabled or removed entirely in some environments; if your correlation logic depends solely on an existing trace ID, it silently breaks the moment tracing is off. A dedicated correlation filter checks for a current trace ID first and falls back to generating its own unique ID when none is available, so request correlation keeps working either way.
