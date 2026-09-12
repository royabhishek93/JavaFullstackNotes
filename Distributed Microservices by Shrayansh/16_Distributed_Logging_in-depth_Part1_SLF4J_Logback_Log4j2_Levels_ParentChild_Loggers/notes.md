# Distributed Logging Part 1 — SLF4J, Logback/Log4j2, Levels, Parent-Child Loggers

## What is this? (Plain English)

Logging means recording application events (requests, responses, errors, warnings, useful info) so developers can monitor and debug what an app is doing at runtime. Before tackling *distributed* logging (stitching logs together across microservices), you need to understand how logging works **inside a single application** — that foundation makes everything about multi-service logging click into place.

## Architecture — The Logging Stack

```
Spring Boot Application
        │
        ▼
   SLF4J (Simple Logging Facade for Java) — an INTERFACE only, zero implementation
   (same idea as the Facade design pattern: expose an API, hide the implementation)
        │
        ▼
   Implementation library — Logback (Spring Boot's default) OR Log4j2
        │
        ▼
   Appender — decides the DESTINATION of a log (console, file, DB, Kafka, cloud...)
        │
        ▼
   Output (console stream / log file / DB row / Kafka message)
        │
        ▼
   Log aggregation tools (Datadog, Elasticsearch+Kibana, Promtail...) read the output
```

**SLF4J** provides only APIs like `LoggerFactory.getLogger(...)` — no implementation. **Logback** is what Spring Boot bundles by default (via `spring-boot-starter-web` → `spring-boot-starter-logging` → `logback-classic` + `logback-core`); **Log4j2** is an alternative implementation you can swap in.

**The multi-provider trap:** if you manually add `spring-boot-starter-log4j2` without excluding the default `spring-boot-starter-logging`, you now have **two** SLF4J implementations on the classpath. Spring's `LoggerFactory` code simply does `providers.get(0)` — which one that is isn't guaranteed, so your app might silently pick either Logback or Log4j2. **Never rely on this in production** — if you want Log4j2, explicitly exclude the logging starter:
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
    <exclusions>
        <exclusion>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-logging</artifactId>
        </exclusion>
    </exclusions>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-log4j2</artifactId>
</dependency>
```

## How `LoggerFactory.getLogger(...)` Actually Works

```java
private static final Logger log = LoggerFactory.getLogger(PaymentController.class);
```
1. `LoggerFactory` (SLF4J API) detects which implementation is on the classpath (Logback or Log4j2).
2. It delegates to `ILoggerFactory` (also an SLF4J interface) — implemented by e.g. Logback's `LoggerContext`.
3. That implementation maintains a **cache (`Map<String, Logger>`)** keyed by logger name — so calling `getLogger()` with the same name repeatedly returns the **same** object instead of creating a new one every time.
4. The name is typically the fully qualified class name (`com.concepts.PaymentController`) — the convention is "one logger per class."

## Log Levels

Five levels, in decreasing priority: **ERROR > WARN > INFO (default) > DEBUG > TRACE**.

**Rule:** a logger only prints a log statement whose level is **equal to or higher priority than** the logger's configured level. If a logger's level is `WARN`, only `WARN` and `ERROR` statements print — `INFO`, `DEBUG`, `TRACE` are silently skipped.

```properties
# Override a specific logger's level
logging.level.com.concepts.PaymentController=DEBUG
```

## Parent-Child Logger Hierarchy — The Core Mental Model

Creating `LoggerFactory.getLogger("com.concepts.PaymentController")` doesn't create just **one** logger object — it silently creates an entire **chain**: `root` → `com` → `com.concepts` → `com.concepts.PaymentController`. `root` is always present and is the ultimate ancestor of every logger.

```
┌─────────────────────────────────────────────┐
│ root logger (always exists, has default       │
│ console appender)                             │
└───────────────────┬───────────────────────────┘
                    v
            ┌───────────────┐
            │      com       │
            └───────┬───────┘
                    v
            ┌───────────────────┐
            │   com.concepts     │
            └───────┬───────────┘
                    v
    ┌───────────────────────────────────────┐
    │  com.concepts.PaymentController         │
    └───────────────────────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

### Why the hierarchy matters — two big payoffs
1. **Level inheritance**: if a logger doesn't have its own level explicitly set, it inherits from its nearest parent that does. You can set the level once on a high-level package logger (e.g. `com`) and every child logger underneath inherits it — no need to configure thousands of individual classes.
2. **Accepted logs propagate upward and run every ancestor's appenders**: once a log statement is *accepted* (its level clears the logger's threshold), the logging framework walks up the parent chain and runs **every appender it finds along the way, all the way to root** — this is why you see console output even when you never wrote an appender for your own class's logger: it propagates up to `root`, which has a built-in default console appender.

**The trap:** "rejected" logs never propagate — if a statement's level is below the logger's threshold, it's dropped immediately at that logger and never reaches any appender, including the root's.

## Important Concepts

- **SLF4J**: An interface-only logging facade — no implementation of its own.
- **Logback / Log4j2**: Concrete implementations of the SLF4J API; Logback is Spring Boot's default.
- **Appender**: Decides the *destination* of a log statement (console, file, DB, Kafka, cloud). Not the same as level or logger.
- **Logger Cache**: One logger object per unique name, reused rather than recreated on every `getLogger()` call.
- **Level Inheritance**: A logger without an explicit level inherits from its nearest ancestor with one set.
- **Upward Propagation**: An accepted log runs its own appender AND every ancestor logger's appender, all the way to root — unless this is disabled (`additivity=false`, covered in Part 2).
- **Root Logger**: The ultimate ancestor of every logger; always exists, cannot be deleted, and has a default console appender out of the box.
