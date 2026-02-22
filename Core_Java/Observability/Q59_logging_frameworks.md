# 🎯 Q59: Logging Frameworks and Best Practices?# 🎯 Q59: Logging Frameworks and Best Practices?































































**Next: [Q60_metrics_collection.md](Q60_metrics_collection.md)****Last Updated:** February 22, 2026  ---"Use SLF4J facade with Logback. Log at proper levels: DEBUG (dev), INFO (events), WARN (issues), ERROR (failures). Use {} placeholder (avoids concatenation). Use async appenders for performance."## 💬 Interview Tip (Say This Exactly)---```logger.error("Payment failed for order: {}", orderId, exception);   // Errorlogger.warn("Connection slow: {}ms", duration);  // Warnlogger.info("Payment processed: {}, amount: {}", orderId, amount);  // Infologger.debug("User created: {}", userId);        // Debug```java## ✅ Best Practices---```</configuration>    </root>        <appender-ref ref="ASYNC" />    <root level="INFO">        <logger name="org.springframework" level="WARN" />    <logger name="com.flipkart" level="INFO" />        </appender>        <appender-ref ref="FILE" />    <appender name="ASYNC" class="ch.qos.logback.classic.AsyncAppender"><configuration><!-- logback.xml -->```xml## ✅ Configuration---```File/Console/Network    ↓Logback (implementation)    ↓SLF4J (facade)```## 📌 Logging Stack---App has millions of logs. Hard to find errors. How to structure?## 🤔 Problem---> **Interview Frequency:** 42% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes
> **Interview Frequency:** 42% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Log everything or lose insights. Log too much or waste disk space.

---

## 📌 Frameworks

| Framework | Use |
|-----------|-----|
| **SLF4J** | Facade (use this) |
| **Logback** | Implementation (recommended) |
| **Log4j2** | Alternative (faster) |
| **java.util.logging** | Built-in (avoid) |

---

## ✅ Best Practices

```java
private static final Logger log = LoggerFactory.getLogger(MyClass.class);

// RIGHT: Info level for important events
log.info("User logged in: {}", userId);

// RIGHT: Debug for development
log.debug("Processing request: {}", request);

// RIGHT: Error with exception
log.error("Payment failed", exception, paymentId);

// WRONG: Too much logging
for (int i = 0; i < 1_000_000; i++) {
    log.debug("Processing item " + i);  // Spam!
}

// RIGHT: Warn about unusual
log.warn("Response time > 5s: {}ms", responseTime);
```

---

## 📌 Log Levels

| Level | Use |
|-------|-----|
| **ERROR** | Something failed, needs attention |
| **WARN** | Something unusual but recoverable |
| **INFO** | Important events (user login, order placed) |
| **DEBUG** | Detailed trace, development only |

---

## 💬 Interview Tip (Say This Exactly)

"Use SLF4J + Logback. Log important events (login, errors), not everything. Use appropriate levels: ERROR for failures, WARN for unusual, INFO for events, DEBUG for dev. Structured logging for parsing."

---

**Last Updated:** February 22, 2026  
**Next: [Q60_metrics_collection.md](Q60_metrics_collection.md)**
