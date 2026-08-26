# 🎯 Q63: Structured Logging and JSON Logs?

> **Interview Frequency:** 38% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Millions of text-based logs. Hard to parse, query, and alert. Need structure!

---

## 📌 Text vs Structured

### ❌ Text (Hard to Parse)
```
2026-02-22 10:30:00 INFO User 123 created from IP 192.168.1.1 with email john@example.com
```

### ✅ JSON (Easy to Parse)
```json
{
  "timestamp": "2026-02-22T10:30:00Z",
  "level": "INFO",
  "userId": 123,
  "ip": "192.168.1.1",
  "email": "john@example.com",
  "service": "auth"
}
```

---

## ✅ Logback JSON Configuration

```xml
<dependency>
    <groupId>ch.qos.logback.contrib</groupId>
    <artifactId>logback-json-classic</artifactId>
    <version>0.1.5</version>
</dependency>

<appender name="json" class="ch.qos.logback.contrib.json.JsonAppender">
    <jsonFormatter class="ch.qos.logback.contrib.json.classic.JsonFormatter">
        <appendLineSeparator>true</appendLineSeparator>
    </jsonFormatter>
    <target>System.out</target>
</appender>
```

---

## 💬 Interview Tip (Say This Exactly)

"Use structured JSON logging for easy parsing in ELK/Splunk. Include: timestamp, level, service, userId, requestId. Enables alerting, querying, and correlation."

---

**Last Updated:** February 22, 2026  
**Next: [Q64_log_aggregation.md](Q64_log_aggregation.md)**
