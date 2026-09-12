# Distributed Logging Part 3 — Async Logging and Structured (JSON) Logging

## What is this? (Plain English)

By default, every step of logging — formatting the message and writing it to its destination — happens **synchronously**, on the same thread that's handling the request. Under heavy traffic, writing to a file/DB/Kafka on every log statement adds real latency to every request. **Async logging** moves the slow part off the request thread. Separately, **structured (JSON) logging** replaces free-form text log lines with machine-parseable JSON, so log aggregation tools (Datadog, ELK, etc.) don't have to guess at a format with fragile regex.

## Async Appender vs Async Logger

| | Async Appender (Logback) | Async Logger (Log4j2 only) |
|---|---|---|
| What's async | Only the formatting + write-to-destination step | The **entire** logging pipeline, from the moment you call `log.info(...)` |
| Latency | Low | Lowest |
| Availability | Logback and Log4j2 | Log4j2 only |

Logback only supports async **appenders**; if you need a fully async **logger**, you need Log4j2.

## Async Appender — How It Works

```
┌───────────────────────────┐   ┌───────────────────────────┐   ┌───────────────────────────────┐
│ Request thread:            │──>│ Build log event            │──>│ In-memory queue                │
│ log.info(...)              │   │ (still sync)                │   │ (async appender)                │
└───────────────────────────┘   └───────────────────────────┘   └───────────────┬───────────────┘
                                                                                  │ request thread freed
                                                                                  │ immediately
                                                                                  v
                                                                    ┌───────────────────────────┐
                                                                    │ Worker thread               │
                                                                    └───────────────┬───────────┘
                                                                                    v
                                                                    ┌───────────────────────────────┐
                                                                    │ Actual appender (file/DB/Kafka) │
                                                                    └───────────────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

An async appender is just a **wrapper** — the real work (writing the log) still happens in the wrapped appender; the async layer only adds a queue + a single worker thread that decouples "accepting the log event" from "actually writing it."

```xml
<appender name="asyncFile" class="ch.qos.logback.classic.AsyncAppender">
    <appender-ref ref="file"/>
    <queueSize>1000</queueSize>            <!-- default 256 -->
    <discardingThreshold>20</discardingThreshold>
    <neverBlock>false</neverBlock>
</appender>
```
- **`queueSize`**: capacity of the in-memory buffer (default 256).
- **`discardingThreshold`**: once the queue is this % full (from the *end*), only critical levels (ERROR/WARN/INFO) are still accepted — DEBUG/TRACE get silently dropped to protect capacity for important events.
- **`neverBlock`**: `false` (default) = the request thread **waits** for queue space if full. `true` = the request thread drops the log immediately and moves on rather than waiting.

**The JVM shutdown risk:** the queue lives in memory. On shutdown, the async appender stops accepting new events and tries to flush what's queued, but this is **not guaranteed** — anything still in the queue when the JVM exits is lost. **Recommendation:** use async for WARN/INFO/DEBUG/TRACE, but keep ERROR logs synchronous (or at minimum `neverBlock=false`) since those are the events most likely to matter during an incident.

### Mixing Sync and Async with Filters
```xml
<appender name="fileNonCritical" class="ch.qos.logback.core.FileAppender">
    <file>logs/non-critical.log</file>
</appender>
<appender name="async" class="ch.qos.logback.classic.AsyncAppender">
    <appender-ref ref="fileNonCritical"/>
    <filter class="ch.qos.logback.classic.filter.LevelFilter">
        <level>ERROR</level>
        <onMatch>DENY</onMatch>
        <onMismatch>NEUTRAL</onMismatch>
    </filter>
</appender>

<appender name="fileCritical" class="ch.qos.logback.core.FileAppender">
    <file>logs/critical.log</file>
    <filter class="ch.qos.logback.classic.filter.ThresholdFilter">
        <level>ERROR</level>  <!-- ERROR and above ONLY -->
    </filter>
</appender>

<logger name="com.concepts.PaymentController" level="INFO" additivity="false">
    <appender-ref ref="async"/>
    <appender-ref ref="fileCritical"/>
</logger>
```
`LevelFilter` matches one exact level (deny/accept/neutral — pass to the next filter if neutral). `ThresholdFilter` accepts a level **and everything above it**. Combining these routes non-critical logs through the fast async path and critical ERROR logs through a synchronous, guaranteed-write path.

## Log Format Best Practices

**Never build log messages via string concatenation:**
```java
// WRONG — the string is built even if the logger will reject this statement (wasted CPU)
log.info("User " + username + " created with ID " + id);

// RIGHT — placeholders are only resolved if the log level is actually accepted
log.info("User {} created with ID {}", username, id);
```
**Exceptions always go last**, after every placeholder — so the stack trace is printed correctly:
```java
log.error("Payment failed for user {}", userId, exception); // exception last, not interleaved
```

## Structured (JSON) Logging

Plain-text log patterns force log aggregation tools to **parse free text with regex** — fragile, because the pattern can differ per appender/logger, and dates/formats aren't guaranteed consistent. JSON is inherently machine-parseable: keys are unambiguous, and aggregation tools can index specific fields (like a `paymentId`) for fast querying — something impossible to reliably extract from a plain sentence.

**Rule of thumb:** don't force *everything* into JSON, and don't hand-roll a JSON string in your pattern either (error-prone, doesn't scale past a handful of fields). Use **Logstash Logback Encoder**, the standard solution:

```xml
<dependency>
    <groupId>net.logstash.logback</groupId>
    <artifactId>logstash-logback-encoder</artifactId>
    <version><!-- latest stable --></version>
</dependency>
```
```xml
<appender name="jsonConsole" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
        <includeMdc>true</includeMdc>  <!-- default true; see MDC below -->
    </encoder>
</appender>
```
This automatically emits fields like `@timestamp`, `@version`, `message`, `logger_name`, `thread_name`, `level`, `stack_trace` — pulled straight from the underlying `ILoggingEvent` object (check `LogstashFieldNames.java` in the library for the full list).

### Dynamic Fields via MDC
```java
MDC.put("paymentId", "123"); // must be set BEFORE the log statement
log.info("Payment successful");
```
With `includeMdc=true`, any key you've put into MDC is automatically merged into the JSON output — e.g. `"paymentId": "123"` appears alongside the standard fields. (MDC itself is covered in depth in Part 4 — it's the mechanism that also powers distributed logging correlation.)

### Masking PII in JSON — JSON Generator Decorator
Never log PII (phone numbers, addresses, national ID numbers, email, OTP, password) unless you're certain it's safe — logging PII by mistake is a compliance/legal risk. The safe pattern for structured logs is a **masking decorator**:
```xml
<encoder class="net.logstash.logback.encoder.LogstashEncoder">
    <jsonGeneratorDecorator class="net.logstash.logback.mask.MaskingJsonGeneratorDecorator">
        <defaultMask>***</defaultMask>
        <path>password</path>
        <path>token</path>
        <path>creditCard</path>
    </jsonGeneratorDecorator>
</encoder>
```
Any field matching these paths — nested or not — is replaced with the mask value before the JSON is written out, so an accidental `MDC.put("password", rawPassword)` doesn't leak into your logs.

## Important Concepts

- **Async Appender (Logback)**: Wraps a real appender with an in-memory queue + single worker thread; only formatting + write is async, not the entire pipeline.
- **Async Logger (Log4j2 only)**: The entire logging call is async from the moment `log.info(...)` is invoked.
- **`discardingThreshold`**: Drops non-critical (DEBUG/TRACE) events once the queue nears capacity, to protect space for ERROR/WARN/INFO.
- **`neverBlock`**: Whether the request thread waits for queue space (`false`, default) or drops the log and moves on (`true`) when the queue is full.
- **JVM Shutdown Risk**: In-memory queued log events can be lost if the JVM exits before they're flushed — keep critical logs synchronous.
- **`LevelFilter` vs `ThresholdFilter`**: LevelFilter matches one exact level with deny/accept/neutral; ThresholdFilter accepts a level and everything above it.
- **Placeholder logging (`{}`)**: Avoids wasted string-concatenation CPU cycles for log statements that end up rejected by the logger's level.
- **Logstash Logback Encoder**: The standard way to emit structured JSON logs in a Logback-based Spring Boot app.
- **MDC + `includeMdc`**: Automatically merges any key/value pairs from the thread's MDC map into the JSON log output.
- **`MaskingJsonGeneratorDecorator`**: Post-processes the generated JSON to mask sensitive field values (password, token, credit card) before writing, as a safety net against accidental PII logging.
