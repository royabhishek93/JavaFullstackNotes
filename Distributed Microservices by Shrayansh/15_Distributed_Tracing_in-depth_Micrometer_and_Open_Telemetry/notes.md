# Distributed Tracing — Micrometer and OpenTelemetry

## What is this? (Plain English)

**Logs** tell you what happened *inside one application*. **Tracing** tells you the *journey of a single request as it hops across multiple microservices* — which service called which, in what order, and how long each step took. They're complementary, not competing: logs are deep-but-narrow (one app), tracing is shallow-but-wide (the whole request path).

## The Problem It Solves

If `order-service` logs "order created for user 55" and `payment-service` independently logs "payment timeout for user 55," there is **nothing connecting these two log lines** — you can't tell they belong to the same API request, and you can't tell how long the hand-off between the two services took. Logs are application-scoped by nature; they have no visibility into what happens once the request leaves the current process.

## Trace ID and Span ID — The Two Concepts That Make This Work

- **Trace ID**: One unique ID per incoming API request, shared by **every** service the request touches. One request = one trace ID, no matter how many microservices it visits.
- **Span ID**: Each unit of work (an incoming request, an outgoing call, a DB operation you wrap manually) gets its own unique span ID, plus a reference to its **parent span**. A span records when it started, when it ended, and therefore how long it took.

```
                    ┌───────────────────────────────────────┐
                    │ Service A: span=S1, parent=null,        │
                    │ trace=T1                                 │
                    └───────────────┬───────────────┬─────────┘
                                    │               │
                                    v               v
            ┌───────────────────────────┐  ┌───────────────────────────┐
            │ Service B: span=S2,        │  │ Service C: span=S3,        │
            │ parent=S1, trace=T1        │  │ parent=S1, trace=T1        │
            └───────────────┬───────────┘  └───────────────────────────┘
                            │
                            v
            ┌───────────────────────────┐
            │ Service D: span=S4,        │
            │ parent=S2, trace=T1        │
            └───────────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

By default, a new span is automatically created for: an **incoming** HTTP request, an **outgoing** HTTP call to another service, and a new **thread hand-off**. You can also create **manual/custom spans** to measure a specific chunk of work (e.g. a slow DB call) that wouldn't otherwise get its own span.

**Bonus payoff:** modern distributed logging systems attach the trace ID to every log line, which is what finally lets you "stitch together" logs from multiple services that belong to the same request — search by trace ID and pull every relevant log line from every service, in order.

## Legacy vs Modern Tracing Stack

| | Legacy | Modern |
|---|---|---|
| Tracing API | Spring Cloud Sleuth | **Micrometer Tracing** (interface only) |
| Implementation/SDK | Brave library (hardcoded) | **OpenTelemetry SDK** (pluggable) |
| Backend compatibility | Zipkin-specific format | **OTLP** (OpenTelemetry Protocol) — vendor-agnostic; Zipkin, Jaeger, and Grafana all accept it |

**Why the migration happened:** Spring Cloud Sleuth's Brave library generated span data in a Zipkin-specific format — switching to Jaeger or Grafana required real workarounds. Micrometer + OpenTelemetry decouples the tracing API from any specific backend: every major backend now speaks OTLP, so switching backends is just changing an endpoint URL, not your code or dependencies.

## Architecture

```
Spring Boot App
  ├── Actuator (brings in Micrometer Tracing API automatically)
  ├── micrometer-tracing-bridge-otel   (OpenTelemetry SDK — implements the Micrometer API:
  │                                      creates trace IDs, span IDs, handles propagation)
  └── opentelemetry-exporter-otlp      (reads completed spans from an in-memory async queue,
                                         pushes them in OTLP format to the backend endpoint)

                     │  OTLP over HTTP/gRPC
                     ▼
         Jaeger / Zipkin / Grafana (any OTLP-compatible backend, builds the trace tree UI)
```

## Key Code / Config

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-tracing-bridge-otel</artifactId>
</dependency>
<dependency>
    <groupId>io.opentelemetry</groupId>
    <artifactId>opentelemetry-exporter-otlp</artifactId>
</dependency>
```
```properties
spring.application.name=trace-app-one
management.tracing.sampling.probability=1.0
# ^ 1.0 = trace 100% of requests. Default is much lower (~10%) — fine for
#   high-traffic prod, but set to 1.0 for demos/low-traffic debugging.
management.otlp.tracing.endpoint=http://localhost:4318/v1/traces
# ^ Jaeger's OTLP-over-HTTP port. Switching backends = changing only this URL.
```

That's the entire setup — no manual instrumentation code required for basic HTTP request/response tracing. Incoming requests and outgoing REST calls are automatically wrapped in spans.

### Propagating Trace Context on Outgoing Calls — the RestClient Trap
```java
// CORRECT — builder-created RestClient automatically gets an interceptor
// that adds the "traceparent" header (trace ID + parent span ID) to outgoing calls
RestClient restClient = RestClient.builder().build();

// WRONG — RestClient.create() does NOT attach the tracing interceptor.
// The downstream service will start a BRAND NEW trace ID instead of
// continuing the current one — breaking the end-to-end trace.
RestClient restClient = RestClient.create();
```
- **RestClient / RestTemplate**: must be built via the `.builder()` pattern (or, for `RestTemplate`, registered with an `ObservationRestTemplateCustomizer`) — otherwise no `traceparent` header is added and the trace chain breaks at that hop.
- **FeignClient**: gets the propagation interceptor automatically — but always verify with a real trace, don't assume.

### Manual/Custom Spans (e.g. wrapping a slow DB call)
```java
@Autowired
private Tracer tracer;

public void doWork() {
    Span parent = tracer.currentSpan();               // the auto-created incoming-request span
    Span child = tracer.nextSpan(parent).name("db-lookup").start();

    try (Tracer.SpanInScope ws = tracer.withSpan(child)) {
        // withSpan() marks `child` as the CURRENT span — important if this
        // block itself creates further nested spans, so they get the right parent
        performSlowDbCall();
    } finally {
        child.end();  // stops the timer; withSpan's try-with-resources restores
                       // the PARENT span as current once this block closes
    }
}
```
- `tracer.nextSpan(parentSpan)` creates a new span as a **child** of the given parent, reusing the same trace ID.
- Starting a span (`.start()`) only starts its timer — it does **not** automatically become the "current span" unless you explicitly call `tracer.withSpan(...)`.
- Always close the span (`.end()`) and the scope (`SpanInScope.close()`, via try-with-resources) — otherwise the "current span" pointer never resets back to the parent, and any code that queries "what's the current span" downstream gets the wrong answer.

## Important Concepts

- **Trace ID**: One per API request, shared across every microservice it visits.
- **Span ID**: One per unit of work (incoming request, outgoing call, thread hand-off, or manual span); records start/end time and parent span reference.
- **Micrometer**: A vendor-neutral tracing API/interface for Spring Boot apps — doesn't do the actual tracing work itself.
- **OpenTelemetry (OTel) SDK**: A pluggable implementation of the Micrometer tracing API; the modern replacement for the old Brave-library-based Spring Cloud Sleuth.
- **OTLP (OpenTelemetry Protocol)**: A vendor-agnostic wire format for span data that Zipkin, Jaeger, and Grafana all understand — switching backends is just an endpoint change.
- **Sampling Probability**: What fraction of requests actually get traced end-to-end; tune down in high-traffic production to control tracing overhead/storage cost.
- **`traceparent` header**: The HTTP header carrying trace ID + parent span ID on outgoing calls, letting the downstream service continue the same trace instead of starting a new one.
- **Filter (incoming) vs Interceptor (outgoing)**: A filter (`ServerHttpObservationFilter`) creates a new span for incoming requests (reusing the trace ID if a `traceparent` header is present, else starting a fresh trace); an interceptor on the HTTP client appends the `traceparent` header on outgoing calls.
