# 🎯 Q32: Decorator Pattern with Real Examples

> **Interview Frequency:** 52% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Add logging, caching, authentication to any method without modifying original code.

---

## 📌 Pattern

```java
interface Service {
    String execute();
}

class AuthDecorator implements Service {
    Service wrapped;
    public String execute() {
        authenticate();
        return wrapped.execute();
    }
}

class LoggingDecorator implements Service {
    Service wrapped;
    public String execute() {
        log("Before");
        String result = wrapped.execute();
        log("After: " + result);
        return result;
    }
}

// Usage: Stack decorators
Service service = new LoggingDecorator(
    new AuthDecorator(
        new DatabaseService()
    )
);
```

---

## 📚 Real Examples

- **Java I/O:** `BufferedInputStream`, `GZIPInputStream` decorate `InputStream`
- **Spring:** `@Transactional`, `@Cacheable` decorate methods
- **Web:** Add compression, encryption, logging to HTTP responses

---

## 💬 Interview Tip (Say This Exactly)

"Decorator wraps object and adds responsibility without modifying original. Chain decorators for multiple concerns. Better than inheritance for cross-cutting concerns."

---

**Last Updated:** February 22, 2026  
**Next: [Q33_strategy_pattern.md](Q33_strategy_pattern.md)**
