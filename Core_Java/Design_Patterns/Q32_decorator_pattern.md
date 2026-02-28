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

## ⚠️ Common Pitfalls

**Pitfall 1: Too many layers**
```java
// ❌ 10 layers deep
Service service = new LoggingDecorator(
    new CachingDecorator(
        new AuthDecorator(
            new RateLimitDecorator(
                new RetryDecorator(
                    // ... 5 more layers
                )
            )
        )
    )
);
// Result: Stack traces 100 lines deep, debugging nightmare

// ✅ Use aspect-oriented programming (Spring AOP)
@Logging @Caching @Auth
public class Service { }
```

**Pitfall 2: Order dependency**
```java
// ❌ Auth must be before logging, wrong order breaks
Service service = new LoggingDecorator(  // Logs even unauthorized!
    new AuthDecorator(actualService)
);

// ✅ Document required order or enforce programmatically
Service service = new AuthDecorator(  // Auth first
    new LoggingDecorator(actualService)  // Then log
);
```

**Pitfall 3: Not delegating correctly**
```java
// ❌ Decorator forgets to call wrapped
class CachingDecorator implements Service {
    public String execute() {
        if (cache.has(key)) return cache.get(key);
        // Forgot to call wrapped.execute()!
        return null;
    }
}

// ✅ Always delegate
public String execute() {
    if (cache.has(key)) return cache.get(key);
    String result = wrapped.execute();
    cache.put(key, result);
    return result;
}
```

---

## 🛑 When NOT to Use Decorator

- ❌ Complex order dependencies (use AOP)
- ❌ Many decorators (hard to manage)
- ❌ When framework provides (Spring @Transactional, @Cacheable)
- ✅ DO use: Adding behavior without modifying code, composable concerns

---
- **Spring:** `@Transactional`, `@Cacheable` decorate methods
- **Web:** Add compression, encryption, logging to HTTP responses

---

## 💬 Interview Tip (Say This Exactly)

"Decorator wraps object and adds responsibility without modifying original. Chain decorators for multiple concerns. Better than inheritance for cross-cutting concerns."

---

**Last Updated:** February 22, 2026  
**Next: [Q33_strategy_pattern.md](Q33_strategy_pattern.md)**
