# Distributed Logging Part 2 — Appenders In-Depth (Console, File, Rolling File)

## What is this? (Plain English)

Part 1 covered how loggers, levels, and the parent-child hierarchy work. Part 2 zooms into **appenders** — the component that decides *where* a log statement physically ends up (console, a file, a database, Kafka...) — and **encoders**, which decide *how* it's formatted once it gets there. Appender = destination. Encoder = format. These are configured in `logback-spring.xml` under `src/main/resources`.

## `logback-spring.xml` — Basic Structure

```xml
<configuration>
    <appender name="console" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>%d %level %logger{36} - %msg%n</pattern>
        </encoder>
    </appender>

    <logger name="com.concepts.PaymentController" level="INFO" additivity="true">
        <appender-ref ref="console"/>
    </logger>

    <root level="INFO">
        <appender-ref ref="console"/>
    </root>
</configuration>
```

- **`<appender>`**: name + class (which appender implementation to use) + an `<encoder><pattern>` describing the log line format.
- **`<logger>`**: name + level + `additivity` + one or more `<appender-ref>` entries.
- **`<root>`**: the fallback ancestor of everything — if you don't write a `logback-spring.xml` at all, the default is `root` at `INFO` level with a console appender, which is why logs appear on console even with zero explicit configuration.

## `additivity` — The Most Confused Setting in Logback

**`additivity` controls ONLY whether an accepted log's appenders propagate upward to parent loggers — it has nothing to do with level inheritance.** These are two independent mechanisms that get mixed up constantly:

- **Level inheritance**: if a logger has no explicit level, it *always* inherits from its nearest parent with one — regardless of `additivity`.
- **Additivity**: if `true` (the default), an accepted log runs its *own* appender, then walks up and runs *every ancestor's* appender too, all the way to root. If `false`, it runs only its own logger's appenders and stops — it will **not** run any parent appenders.

**The trap:** setting `additivity="false"` without giving that logger at least one appender of its own means the log goes **nowhere** — you get a runtime warning ("no appenders present") and silently lose that log entirely.

```
additivity=true  (default): own appender -> parent's appender -> ... -> root's appender
additivity=false: own appender ONLY, propagation stops here
```

## Appender Types

### 1. Console Appender
```xml
<appender name="console" class="ch.qos.logback.core.ConsoleAppender">
    <encoder><pattern>%d %level %logger{36} - %msg%n</pattern></encoder>
</appender>
```
Writes to the **standard output (stdout)** stream — that's all "console" really means in code; what actually *displays* that stream differs by environment (a local terminal, Docker's logging driver, Azure Monitor, etc.). **Not persistent** — nothing is saved, it's purely a live stream that some downstream tool reads.

### 2. File Appender — NOT production-safe
```xml
<appender name="file" class="ch.qos.logback.core.FileAppender">
    <file>logs/app.log</file>
    <append>true</append>  <!-- true = keep old logs across restarts; false = truncate on restart -->
    <encoder><pattern>%d %level %logger{36} - %msg%n</pattern></encoder>
</appender>
```
Persists to a real file — but with **no size control**, the file can grow unbounded and exhaust disk space. Fine for local dev, unsafe for production.

### 3. Rolling File Appender (Time-Based) — better, still incomplete
```xml
<appender name="rollingFileTime" class="ch.qos.logback.core.rolling.RollingFileAppender">
    <file>logs/app.log</file>
    <rollingPolicy class="ch.qos.logback.core.rolling.TimeBasedRollingPolicy">
        <fileNamePattern>logs/app-%d{yyyy-MM-dd-HH-mm}.log</fileNamePattern>
        <maxHistory>30</maxHistory>
    </rollingPolicy>
    <encoder><pattern>%d %level %logger{36} - %msg%n</pattern></encoder>
</appender>
```
- The date pattern's granularity controls rotation frequency: `yyyy-MM-dd` → daily rotation, `yyyy-MM-dd-HH` → hourly, `yyyy-MM-dd-HH-mm` → every minute.
- `maxHistory=30` means "keep the last 30 rotation periods" — 30 days if rotating daily, 30 hours if rotating hourly, etc.
- **Still incomplete**: no cap on individual file size — a very high-traffic minute/hour/day could still produce a huge single file.

### 4. Rolling File Appender (Size + Time Based) — production standard
```xml
<appender name="rollingFileSizeTime" class="ch.qos.logback.core.rolling.RollingFileAppender">
    <file>logs/app.log</file>
    <rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">
        <fileNamePattern>logs/app-%d{yyyy-MM-dd}.%i.log</fileNamePattern>
        <maxFileSize>100MB</maxFileSize>
        <totalSizeCap>2GB</totalSizeCap>
        <maxHistory>30</maxHistory>
    </rollingPolicy>
    <encoder><pattern>%d %level %logger{36} - %msg%n</pattern></encoder>
</appender>
```
- `maxFileSize=100MB`: once the active file for the current day hits this size, it's archived (`app-2025-12-19.0.log`) and a new one starts (`app-2025-12-19.1.log`, `.2.log`, etc. — the `%i` index increments within the same day).
- `totalSizeCap=2GB`: the combined size across **all** archived files, regardless of `maxHistory` — once exceeded, the oldest files are deleted to stay under the cap.
- **The trap**: `maxHistory=30` and `totalSizeCap=2GB` can silently conflict — if traffic is heavy enough that even a single day's logs approach 2GB, you may lose data well before 30 days have passed, because the size cap deletes older files first regardless of your intended retention window. Tune both together based on real traffic volume.

## Appender Decision Flow

```
                    ┌───────────────────────────────────┐
                    │ Log event arrives at appender        │
                    └───────────────────┬───────────────────┘
                                        v
                    ┌───────────────────────────────────┐
                    │           Appender type?             │
                    └───┬───────────┬───────────┬─────────┘
                Console │      File │           │ RollingFile Time-Based
                        v           v           v
            ┌───────────────┐ ┌───────────────────────────┐  ┌─────────────────────────────┐
            │ Write to      │ │ Append to logs/app.log     │  │ Rotation period elapsed?     │
            │ stdout (not   │ │ (unbounded growth)          │  │ (min/hour/day)                │
            │ persistent)   │ └───────────────────────────┘  └──────┬─────────────┬──────────┘
            └───────────────┘                                   Yes │             │ No
                                                                     v             v
                                                    ┌───────────────────────────┐ ┌───────────────────────────┐
                                                    │ Archive current file,      │ │ Append to current period's │
                                                    │ start new one, prune        │ │ file                       │
                                                    │ beyond maxHistory           │ └───────────────────────────┘
                                                    └───────────────────────────┘

            (back at "Appender type?") RollingFile Size+Time
                        v
            ┌───────────────────────────┐
            │ Current file >= maxFileSize?│
            └──────┬─────────────┬───────┘
                Yes│             │No
                    v             v
    ┌───────────────────────────┐ ┌───────────────────────────┐
    │ Roll to next index          │ │ Append to current file     │
    │ (app-date.i+1.log)          │ └───────────────────────────┘
    └───────────────┬───────────┘
                    v
    ┌───────────────────────────────┐
    │ Total archived size >           │
    │ totalSizeCap?                  │
    └──────┬─────────────┬───────────┘
        Yes│             │No
            v             v
┌───────────────────────┐ ┌───────┐
│ Delete oldest archived │ │ Done   │
│ files                  │ └───────┘
└───────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## Rolling File Layout (Example)

```
logs/
 ├─ app.log                       <-- currently active file
 ├─ app-2025-12-18.0.log          <-- archived: day 18, part 0 (rolled at maxFileSize)
 ├─ app-2025-12-18.1.log          <-- archived: day 18, part 1
 ├─ app-2025-12-19.0.log          <-- archived: day 19, part 0
 └─ ...
      maxHistory=30       -> keep at most 30 rotation periods (days here)
      totalSizeCap=2GB    -> hard cap across ALL archived files combined
                             (can force deletion BEFORE maxHistory is reached)
```

## Writing a Custom Appender (e.g. for DB or Kafka)

When no built-in appender fits (you want logs written to a database or published to Kafka), extend `AppenderBase<ILoggingEvent>` and override `append(...)`:

```java
public class DbAppender extends AppenderBase<ILoggingEvent> {
    @Override
    protected void append(ILoggingEvent event) {
        String message = event.getFormattedMessage();
        String loggerName = event.getLoggerName();
        long timestamp = event.getTimeStamp();
        // your custom logic: save to DB, publish to Kafka, etc.
    }
}
```
```xml
<appender name="dbAppender" class="com.concepts.customappender.DbAppender"/>
<!-- No <encoder> needed — you control the format yourself inside append() -->
```

## Important Concepts

- **Appender vs Encoder**: Appender decides the destination; encoder decides the format. A custom appender skips the encoder entirely since formatting logic lives inside your `append()` method.
- **`additivity`**: Controls only whether an accepted log's appenders propagate up the logger hierarchy — completely independent from level inheritance, which always looks upward regardless of this setting.
- **Console = stdout, not a specific UI**: "Console" just means the standard output stream; what tool reads and displays it (terminal, Docker driver, cloud monitor) varies by environment.
- **File Appender**: Persistent but unbounded — never production-safe on its own.
- **`TimeBasedRollingPolicy`**: Rotates files based on a date pattern's granularity (minute/hour/day/month); `maxHistory` = how many rotation periods to retain.
- **`SizeAndTimeBasedRollingPolicy`**: Adds `maxFileSize` (per-file cap, with an auto-incrementing `%i` index within a period) and `totalSizeCap` (aggregate cap across all archived files) — the production-standard combination.
- **Custom Appender**: Extend `AppenderBase<ILoggingEvent>`, override `append()`, for destinations with no built-in support (custom DB schema, Kafka topic, etc.).
