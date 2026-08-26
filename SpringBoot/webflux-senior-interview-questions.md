# Spring WebFlux: Senior Interview Guide (Canonical)

**Study Time:** 30-40 minutes | **Frequency:** Very high for backend interviews | **Goal:** Clear, precise, scenario-first answers

This is the canonical full guide for WebFlux interview prep.
Companion quick-sheet: `SpringBoot/Q7_blocking_in_reactive_pipeline.md`.

## 1) Reactive vs WebFlux (Most Asked Distinction)

Reactive is the programming paradigm for non-blocking asynchronous streams with backpressure.
WebFlux is Spring's reactive web framework that applies this paradigm to HTTP APIs.

- Reactive: model, operators, scheduling, backpressure
- WebFlux: web stack (controllers/router functions, filters, codecs, WebClient)

Interview line:
"Reactive is the concept; WebFlux is Spring's HTTP framework built on that concept (typically Reactor)."

---

## 2) Event Loop Model and Why It Matters

### Scenario
You have 8 CPU cores and 20k concurrent clients calling an API.

### Key Principle
WebFlux (usually with Netty) uses a small number of event-loop threads to handle many I/O-bound requests.
Threads should not block while waiting for DB/network/file responses.

### What interviewer expects
- You can explain thread efficiency vs thread-per-request.
- You can explain why blocking code destroys this advantage.

### Visual
```text
Client Requests --> Netty Event Loop Threads (small fixed pool)
                   | parse request
                   | dispatch reactive pipeline
                   | return thread immediately while I/O is pending
                   v
             callback/signal resumes pipeline when data arrives
```

---

## 3) The #1 Production Failure: Blocking Inside Reactive Pipeline

### Scenario
A reactive endpoint calls JDBC or `Thread.sleep()` inside `map/flatMap`.

### What happens
- Event-loop thread is occupied waiting.
- Other requests queue up.
- Latency spikes, throughput collapses, timeouts increase.

### Anti-patterns (must recognize)
- JDBC/JPA call in reactive chain
- `RestTemplate` inside reactive flow
- `Thread.sleep()` in operator
- `.block()` in request path

### Example (bad)
```java
@GetMapping("/orders/{id}")
public Mono<OrderDto> get(@PathVariable Long id) {
    return Mono.just(id)
        .map(repo::findById) // blocking JPA/JDBC call
        .map(this::toDto);
}
```

### What interviewer expects
- You explicitly call this out as event-loop starvation.
- You propose migration or offloading options (next section).

---

## 4) Correct Fix Strategy: R2DBC First, Offload as Transition

### Preferred (end state)
Use non-blocking drivers end-to-end (R2DBC + reactive repositories/DatabaseClient).

### Transitional (legacy systems)
If you cannot remove blocking dependency immediately, isolate it:

```java
Mono<Order> orderMono = Mono.fromCallable(() -> legacyDao.fetchOrder(id))
    .subscribeOn(Schedulers.boundedElastic());
```

### Add safety for transitional path
- Apply timeout
- Cap concurrency at caller (`flatMap(..., concurrency)`)
- Avoid unbounded fan-out
- Keep offloaded segment narrow

### What interviewer expects
- "boundedElastic is a bridge, not the final architecture."
- "Real target is non-blocking I/O across the chain."

---

## 5) subscribeOn vs publishOn (Precise)

### Quick truth
- `subscribeOn`: chooses thread context for source/subscription side (upstream influence).
- `publishOn`: switches execution context from that point downstream.

### Example
```java
Mono<String> flow = Mono.fromCallable(this::load)      // source
    .subscribeOn(Schedulers.boundedElastic())          // source runs on boundedElastic
    .map(this::transform)                              // still boundedElastic
    .publishOn(Schedulers.parallel())                  // switch from here
    .map(this::cpuHeavyStep);                          // runs on parallel scheduler
```

### Does publishOn create parallelism by itself?
No. It changes thread context, not parallel fan-out.
Parallelism requires concurrency patterns such as:
- `flatMap(task, concurrency)`
- `parallel().runOn(...)` with careful usage

### What interviewer expects
- You do not claim `publishOn` == automatic parallel processing.

---

## 6) Why `.block()` Is Dangerous in WebFlux Request Flow

### Scenario
`.block()` is called inside request handling chain.

### Failure mode
The calling thread waits synchronously for completion. If that thread is part of event-loop/request processing, you can create starvation and deadlock-like behavior.

### Rule
- Avoid `.block()` in runtime request path.
- Acceptable boundaries: startup/bootstrap code, tests, CLI scripts.

### What interviewer expects
- You identify `.block()` as boundary-only tool.

---

## 7) Backpressure: Controlling Producer vs Consumer Speed

### Scenario
Producer emits faster than downstream can consume.

### Core tools
- `onBackpressureBuffer` (queues, memory tradeoff)
- `onBackpressureDrop` (drop overflow)
- `onBackpressureLatest` (keep newest value)

### Picking strategy
- Financial ticks/dashboard: often `latest`
- Auditing/event durability: usually buffer + limits
- Telemetry firehose: often drop with monitoring

### What interviewer expects
- You can explain why strategy depends on business semantics, not just performance.

---

## 8) Error Handling and Resilience Patterns

### Operator-level
- `onErrorReturn`: static fallback
- `onErrorResume`: dynamic fallback path
- `onErrorMap`: normalize/translate exception type
- `retryWhen`: controlled retries (avoid retry storms)

### Minimal example
```java
return service.fetch(userId)
    .timeout(Duration.ofSeconds(2))
    .onErrorResume(ex -> cacheService.get(userId));
```

### Interview expectation
- Mention timeout + fallback + bounded retry policy.

---

## 9) Data Layer: JDBC/JPA vs R2DBC Reality

### Interview-safe view
- JDBC/JPA: mature ecosystem, but blocking I/O
- R2DBC: non-blocking I/O, better fit for reactive pipeline

### Transaction note
Reactive transactions rely on reactive transaction management and context propagation, not classic thread-bound assumptions.
Use Spring reactive transaction support (`TransactionalOperator` / reactive transaction manager).

### What interviewer expects
- You acknowledge feature trade-offs while keeping architecture consistent.

---

## 10) Combining Multiple Async Calls

### Common patterns
- `zip`: wait for all, combine once
- `merge`: emit as each source arrives
- `concat`: preserve source order sequentially
- `flatMap`: async composition with configurable concurrency

### Scenario
Profile page needs user + orders + recommendations:
- Use `zip` when page requires all pieces together
- Use `merge` for stream-first UX pieces

---

## 11) Testing WebFlux (High Interview Value)

### Tools
- `StepVerifier` for publisher behavior
- `WebTestClient` for endpoint testing

### Example
```java
StepVerifier.create(service.getUser("u1"))
    .expectNextMatches(u -> u.id().equals("u1"))
    .verifyComplete();
```

### What interviewer expects
- You test signal semantics (`next`, `complete`, `error`), not just values.

---

## 12) Real-Time Delivery: WebSocket vs SSE

### Decision
- WebSocket: bidirectional real-time channel
- SSE: server-to-client unidirectional streaming over HTTP

### Typical use
- Chat/collaboration/game control -> WebSocket
- Live feed/notifications/monitoring dashboards -> SSE

---

## 13) Production Choice: WebFlux vs Spring MVC

Use WebFlux when:
- high concurrency
- mostly I/O-bound workloads
- end-to-end non-blocking dependencies are feasible

Use MVC when:
- blocking stack is dominant (JPA-heavy, synchronous integrations)
- team velocity and ecosystem fit are better with servlet model

Interview-safe line:
"Choose by workload and dependency behavior, not trend."

---

## 14) Top Interview Traps (Fast Recall)

1. Claiming `publishOn` gives automatic parallelism.
2. Mixing blocking JDBC in event-loop path.
3. Using `.block()` in runtime request chain.
4. Ignoring backpressure strategy selection.
5. Adding retries without timeout or bounds.
6. Declaring "WebFlux is always faster" without workload context.
7. Using reactive API surface with blocking internals.
8. Not measuring thread saturation and latency percentiles.

---

## 15) 60-Second Architect Answer

"Reactive is the programming model; WebFlux is Spring's reactive web framework. WebFlux scales by using a small event-loop thread pool and non-blocking I/O. The biggest production mistake is placing blocking calls (JDBC, sleep, block) in the request pipeline, which causes event-loop starvation. Correct approach is end-to-end non-blocking (R2DBC/WebClient), or temporary offload with boundedElastic while migrating. I choose backpressure and retry policies based on business semantics, and I validate behavior with StepVerifier and WebTestClient."

---

## References
- Spring Framework Reference (WebFlux)
- Project Reactor Reference Guide
- R2DBC Specification and Spring Data R2DBC docs
