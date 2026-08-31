# 📝 Logging System - Low Level Design Interview Guide
## _15 YOE Architect-Level Conversational Script_

---

## 📋 **Table of Contents**
1. [Architecture Diagram](#1-architecture-diagram)
2. [API Design](#2-api-design)
3. [ER Diagram & Database Design](#3-er-diagram--database-design)
4. [Sequence Diagrams](#4-sequence-diagrams)
5. [Scenario-First Explanations](#5-scenario-first-explanations)
6. [Cross Questions](#6-cross-questions)
7. [Trade-offs](#7-trade-offs)
8. [Senior Trap Questions](#8-senior-trap-questions)
9. [Technology Choices](#9-technology-choices)

---

## **Design Pattern Used**: Chain of Responsibility

**Interviewer**: "Design a logging framework (like Log4j)."

**You**: "The core insight here is: **log messages have severity levels (DEBUG < INFO < WARN < ERROR), and each logger handles messages at or above its configured level, passing others down the chain.**

This is a textbook **Chain of Responsibility** pattern - very similar to the ATM cash dispenser chain, but for log level filtering!"

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                  LOGGING SYSTEM ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────┘

    Application Code
           │
           │ logger.log(ERROR, "Database connection failed")
           ▼
    ┌──────────────┐
    │ DEBUG Logger │  Level: DEBUG (1)
    │ (Console)    │  Handles: DEBUG only, passes rest down
    └──────┬───────┘
           │ (ERROR > DEBUG, pass down)
           ▼
    ┌──────────────┐
    │ INFO Logger  │  Level: INFO (2)
    │ (File)       │  Handles: INFO only, passes rest down
    └──────┬───────┘
           │ (ERROR > INFO, pass down)
           ▼
    ┌──────────────┐
    │ ERROR Logger │  Level: ERROR (4)
    │ (Email/Slack)│  Handles: ERROR! Matches, sends alert
    └──────────────┘

    CHAIN SETUP:
    debugLogger.setNext(infoLogger);
    infoLogger.setNext(warnLogger);
    warnLogger.setNext(errorLogger);
```

---

## 2. API Design

```http
POST /api/v1/logs
Request:
{
  "level": "ERROR",
  "message": "Database connection timeout",
  "service": "payment-service",
  "metadata": {"userId": "user-123", "traceId": "trace-456"}
}

Response: 202 ACCEPTED
{
  "logId": "log-9999",
  "processedBy": ["CONSOLE", "FILE", "ALERT_SYSTEM"]
}

---

GET /api/v1/logs/search?service=payment-service&level=ERROR&from=2026-08-30&to=2026-08-31
Response: 200 OK
{
  "logs": [
    {"logId": "log-9999", "level": "ERROR", "message": "...", "timestamp": "..."}
  ],
  "totalCount": 42
}
```

---

## 3. ER Diagram & Database Design

```sql
-- Logs typically go to file/Elasticsearch, but if DB-backed:
CREATE TABLE logs (
    log_id VARCHAR(50) PRIMARY KEY,
    level VARCHAR(10) NOT NULL,
    message TEXT NOT NULL,
    service VARCHAR(100),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (level IN ('DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL')),
    INDEX idx_service_level_time (service, level, created_at)
);

CREATE TABLE logger_config (
    logger_name VARCHAR(100) PRIMARY KEY,
    min_level VARCHAR(10) NOT NULL,
    appender_type VARCHAR(20),  -- CONSOLE, FILE, DATABASE, EMAIL, SLACK
    enabled BOOLEAN DEFAULT TRUE
);
```

---

## 4. Sequence Diagrams

```
App     DebugLogger   InfoLogger   WarnLogger   ErrorLogger
 │           │             │            │             │
 │─log(ERROR,"DB failed")▶│             │            │             │
 │           │  level(ERROR) >= DEBUG? YES but this logger only WRITES at its own level
 │           │  Actually: passes to next() always, EACH may write if level matches
 │           ├─setNext.handle()───────▶│            │             │
 │           │             │  level(ERROR) not INFO, pass down    │
 │           │             ├─setNext.handle()────────▶│             │
 │           │             │            │  level(ERROR) not WARN, pass down
 │           │             │            ├─setNext.handle()─────────▶│
 │           │             │            │             │  level(ERROR) == ERROR! ✓
 │           │             │            │             │  Send email alert
 │           │             │            │             │  Write to error log file
```

---

## 5. Scenario-First Explanations

### **5.1 Why Chain of Responsibility (Not Simple If-Else)?**

**You**: "Without Chain pattern:
```java
// ❌ Every log call has if-else for EVERY level and EVERY appender combo
void log(LogLevel level, String message) {
    if (level == DEBUG) {
        console.write(message);
    } else if (level == INFO) {
        console.write(message);
        file.write(message);
    } else if (level == ERROR) {
        console.write(message);
        file.write(message);
        email.send(message);
        slack.notify(message);
    }
    // Adding new appender = modify this method everywhere!
}
```

**With Chain of Responsibility**:
```java
abstract class LogProcessor {
    protected LogProcessor nextLogger;
    protected LogLevel level;
    
    void setNext(LogProcessor next) {
        this.nextLogger = next;
    }
    
    void log(LogLevel messageLevel, String message) {
        if (messageLevel.ordinal() >= this.level.ordinal()) {
            write(message);
        }
        if (nextLogger != null) {
            nextLogger.log(messageLevel, message);
        }
    }
    
    abstract void write(String message);
}

class ConsoleLogger extends LogProcessor {
    void write(String message) {
        System.out.println("[CONSOLE] " + message);
    }
}

class FileLogger extends LogProcessor {
    void write(String message) {
        fileWriter.write(message);
    }
}

class ErrorAlertLogger extends LogProcessor {
    void write(String message) {
        emailService.send("ALERT: " + message);
        slackService.notify(message);
    }
}

// Setup chain:
LogProcessor logger = new ConsoleLogger(DEBUG);
logger.setNext(new FileLogger(INFO));
logger.getNext().setNext(new ErrorAlertLogger(ERROR));

// Usage:
logger.log(ERROR, "Payment failed");  
// → Flows through ALL loggers, each independently decides to write or skip
```

**Key insight**: Each logger in the chain independently checks if IT should handle the message (based on level), regardless of what other loggers do. This is subtly different from typical Chain of Responsibility (where only ONE handler processes) - here it's more like a **pipeline where multiple handlers can act**."

### **5.2 Why Configurable Log Levels Matter (Production Reality)**

**You**: "In production, you NEVER want DEBUG logs flooding production systems:

```yaml
# application.yml
logging:
  level:
    root: INFO           # Production: INFO and above only
    com.payment: DEBUG   # But debug THIS specific package during investigation
```

**Why this matters**: 
- DEBUG logs at scale = massive I/O overhead, disk fill-up
- Being able to dynamically change log level for ONE misbehaving service (without redeploying) is CRITICAL for incident response
- Log4j2's runtime reconfiguration capability (via JMX or config file watch) is a major production feature"

---

## 6. Cross Questions

**Interviewer**: "How do you prevent logging from becoming a performance bottleneck?"

**You**: "**Async logging with a ring buffer** (like Log4j2's AsyncLogger using LMAX Disruptor):

```java
class AsyncLogger {
    private final BlockingQueue<LogEvent> queue = new LinkedBlockingQueue<>(10000);
    private final ExecutorService writerThread = Executors.newSingleThreadExecutor();
    
    void log(LogLevel level, String message) {
        // Non-blocking: just enqueue (microseconds)
        queue.offer(new LogEvent(level, message, System.currentTimeMillis()));
    }
    
    // Separate thread does actual I/O
    @PostConstruct
    void startWriter() {
        writerThread.submit(() -> {
            while (true) {
                LogEvent event = queue.take();  // Blocks until available
                actualWriteToDisk(event);  // Slow I/O happens here, off critical path
            }
        });
    }
}
```

**Why this matters**: Application thread doesn't wait for disk I/O. Trade-off: if app crashes, buffered logs in queue are lost. Mitigate with periodic flush + reasonable queue size."

---

## 7. Trade-offs

### **Sync vs Async Logging**

| Aspect | Synchronous | Asynchronous |
|--------|-------------|---------------|
| **Performance** | Slower (I/O blocks thread) | Faster (I/O offloaded) |
| **Reliability** | Guaranteed write | Risk of loss on crash |
| **Use Case** | Audit logs (must not lose) | High-throughput app logs |

**You**: "Use **sync for audit/compliance logs** (financial transactions - must never lose), **async for application debug/info logs** (performance matters more than 100% durability)."

---

## 8. Senior Trap Questions

### **Trap: "Just use System.out.println() everywhere, simpler!"**

**✅ Senior Answer**: "`println` is synchronous, unbuffered, and unstructured. Production issues:
1. **No log levels** - can't filter DEBUG from ERROR in production
2. **No structured format** - can't parse into ELK/Splunk easily  
3. **Blocking I/O** - stdout writes can block under high load
4. **No rotation** - single file grows unbounded, fills disk

Real logging frameworks (Log4j2, Logback) solve all of these: async I/O, JSON structured output, automatic file rotation by size/date, and centralized configuration."

---

## 9. Technology Choices

### **Log Storage: ELK Stack vs Splunk vs CloudWatch**

**You**: "**ELK (Elasticsearch-Logstash-Kibana)** for self-hosted, cost-sensitive setups with high log volume. **Splunk** for enterprise with budget (excellent search, but expensive per GB). **CloudWatch Logs** for AWS-native simplicity (less powerful querying but zero infra management)."

---

## 🎓 **Final Tips**

1. **Chain of Responsibility**: Multiple handlers each independently decide to act (variant of classic pattern)
2. **Async Logging**: Critical for performance - decouple write from log call
3. **Log Levels**: Runtime-configurable without redeployment
4. **Structured Logging**: JSON format for machine parsing (ELK/Splunk)

Good luck! This tests your understanding of the **Chain of Responsibility pattern** and **production logging concerns**. 🚀
