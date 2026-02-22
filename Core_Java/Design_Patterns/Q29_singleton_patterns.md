# 🎯 Q29: Singleton Pattern - Best Implementations?

> **Interview Frequency:** 70% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

Config manager should have only ONE instance throughout application. How to guarantee?

---

## 📌 Implementation Approaches

### 1. **Eager Initialization** (Simplest)
```java
public class Config {
    public static final Config INSTANCE = new Config();
    private Config() {}
}
```
- Thread-safe by design
- Always loaded (wasteful if unused)

### 2. **Lazy Initialization with Synchronized** (Old)
```java
public class Config {
    private static Config instance;
    public static synchronized Config getInstance() {
        if (instance == null) {
            instance = new Config();
        }
        return instance;
    }
}
```
- Lazy-loaded
- Synchronized every time (slow)

### 3. **Bill Pugh Singleton** (Best for Java < 9) ⭐
```java
public class Config {
    private Config() {}
    private static class Holder {
        static final Config INSTANCE = new Config();
    }
    public static Config getInstance() {
        return Holder.INSTANCE;  // Lazy + thread-safe
    }
}
```
- Lazy load (class loads on first access)
- Thread-safe (class loader guarantee)
- No synchronization overhead

### 4. **Enum Singleton** (Best for Java 9+) ⭐⭐
```java
public enum Config {
    INSTANCE;
    // methods...
}
```
- Thread-safe by enum guarantee
- Prevents reflection attacks
- Handles serialization automatically
- **Recommended in 2026**

---

## 💬 Interview Tip (Say This Exactly)

"Use Enum singleton in Java 9+. Use Bill Pugh in older versions. Avoid synchronized() singleton - performance hit. Spring manages singletons for beans automatically."

---

## ☑️ Checklist

- ✅ Enum singleton (Java 9+): Safest
- ✅ Bill Pugh (Java <9): Safe + lightweight
- ✅ Avoid synchronized(): Performance cost
- ✅ Avoid double-checked locking: Complex, easy to get wrong
- ✅ Prevent reflection: Add in private constructor if critical

---

**Last Updated:** February 22, 2026  
**Next: [Q30_factory_pattern.md](Q30_factory_pattern.md)**
