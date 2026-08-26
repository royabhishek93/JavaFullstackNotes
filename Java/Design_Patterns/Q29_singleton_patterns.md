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

## ⚠️ Common Pitfalls

**Pitfall 1: Using synchronized instance method**
```java
// ❌ Every call to getInstance() synchronized (slow!)
public static synchronized Config getInstance() {
    if (instance == null) instance = new Config();
    return instance;
}
// Result: Bottleneck, 100x slower than enum

// ✅ Use enum or Bill Pugh
public enum Config { INSTANCE; }
```

**Pitfall 2: Singleton with mutable state**
```java
// ❌ Singleton holding mutable state (thread-unsafe!)
public enum Config {
    INSTANCE;
    private Map<String, String> settings = new HashMap<>();  // Shared!
    // Multiple threads modify → race conditions
}

// ✅ Use immutable state or thread-safe collections
public enum Config {
    INSTANCE;
    private final ConcurrentHashMap<String, String> settings = new ConcurrentHashMap<>();
}
```

**Pitfall 3: Singletons everywhere**
```java
// ❌ Every class as singleton
public enum UserService { INSTANCE; }
public enum OrderService { INSTANCE; }
public enum PaymentService { INSTANCE; }
// Result: Hard to test, tight coupling

// ✅ Use dependency injection (Spring beans)
@Service
public class UserService { }  // Spring manages as singleton
```

**Pitfall 4: Not preventing reflection attacks**
```java
// ❌ Reflection can break singleton
Constructor<Config> constructor = Config.class.getDeclaredConstructor();
constructor.setAccessible(true);
Config instance2 = constructor.newInstance();  // NEW INSTANCE!

// ✅ Throw exception in constructor
private Config() {
    if (INSTANCE != null) throw new IllegalStateException("Already created");
}
```

---

## 🛑 When NOT to Use Singleton

- ❌ Testing (hard to mock, global state)
- ❌ When you need multiple instances in future
- ❌ Stateful objects (race conditions)
- ✅ DO use: Configuration, logging, database connections (via pool)

---

---

## 🔗 Related Questions

- [Q30_factory_pattern.md](Q30_factory_pattern.md) - Factory vs singleton creation
- [Q31_builder_pattern.md](Q31_builder_pattern.md) - Builder for complex object creation
- [../../SpringBoot/Q2_springboot_autoconfiguration.md](../../SpringBoot/Q2_springboot_autoconfiguration.md) - Spring manages singletons as beans

---

**Last Updated:** February 22, 2026  
**Next: [Q30_factory_pattern.md](Q30_factory_pattern.md)**
