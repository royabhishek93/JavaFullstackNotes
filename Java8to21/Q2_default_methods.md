# Q2: What is a default method?

**Study Time:** 2-3 minutes

---

## Problem

Understanding default method syntax and behavior.

## Core Concept

A default method is a method **IN THE INTERFACE** with an **IMPLEMENTATION** (not just abstract declaration).

## ✅ Syntax

```java
public interface PaymentProcessor {
    // Abstract method - no implementation
    void processPayment(double amount);
    
    // Default method - HAS implementation
    default void logTransaction(String msg) {
        System.out.println("[LOG] " + msg);  // Body!
    }
}

// Classes implementing:
public class StripePayment implements PaymentProcessor {
    @Override
    public void processPayment(double amount) {
        // Must implement abstract method
    }
    
    // logTransaction() inherited automatically
    // Can call it: this.logTransaction("Payment processed");
}
```

## When to Override (Optional)

```java
public class Crypto Payment implements PaymentProcessor {
    @Override
    public void processPayment(double amount) {
        // Implement abstract
    }
    
    @Override
    // Optional: override if you want custom behavior
    default void logTransaction(String msg) {
        // Custom crypto-specific logging
        System.out.println("[CRYPTO] " + msg);
    }
}
```

## Key Pattern: Default Methods Call Abstract Methods

```java
public interface DataService {
    List<User> getUsers();  // Abstract - how to fetch
    
    default int getUserCount() {
        // Uses the abstract method, delegates to implementation
        return getUsers().size();
    }
}

// Different implementations, same default behavior
public class DatabaseService implements DataService {
    @Override
    public List<User> getUsers() {
        return database.query("SELECT * FROM users");
    }
    // getUserCount() works - returns size of query result
}

public class CachedService implements DataService {
    @Override
    public List<User> getUsers() {
        return cache.getOrFetch("users", () -> database.query(...));
    }
    // getUserCount() works - returns size of cached result
}
```

## Interview Tip

"Default methods have implementations in the interface. Classes inherit them automatically but can override if needed. Perfect for adding utility methods to existing interfaces without breaking implementations."

## Quick Checklist

- ✅ `default` keyword + method body
- ✅ Optional to override (unlike abstract methods)
- ✅ Inherited by implementations automatically
- ✅ Can call other interface methods from default
- ✅ Multiple classes can use same default logic
- ✅ Java 8+

---

## ⚠️ Common Pitfalls

**Pitfall 1: Calling default methods from constructors expecting initialization**

❌ **Wrong approach:**
```java
public interface PaymentProcessor {
    default void initialize() {
        System.out.println("Initializing " + getProcessorName());
    }
    
    String getProcessorName();  // Abstract
}

public class StripeProcessor implements PaymentProcessor {
    private String name;
    
    public StripeProcessor() {
        initialize();  // ❌ Calls getProcessorName()
        // But name is NOT set yet! Can return null
    }
    
    @Override
    public String getProcessorName() {
        return name;  // Not initialized!
    }
}
```
**Why it fails:** Default method assumes initialization is complete, but constructor hasn't finished yet.

✅ **Right approach:**
```java
public class StripeProcessor implements PaymentProcessor {
    private String name;
    
    public StripeProcessor() {
        this.name = "Stripe";  // Initialize first
        initialize();  // Now it's safe
    }
}

// Or better: Don't call from constructor at all
```

---

**Pitfall 2: Assuming default method can access instance state**

❌ **Wrong approach:**
```java
public interface DataService {
    // Default assumes there's a cache field
    default List<User> getCachedUsers() {
        return this.cache.getUsers();  // ❌ null - no cache!
    }
    
    List<User> getUsers();
}

public class DatabaseService implements DataService {
    // No cache implementation provided
    @Override
    public List<User> getUsers() {
        return database.query("SELECT...");
    }
    
    // getCachedUsers() inherited but tries to use non-existent cache
}
```
**Why it fails:** Default method assumes implementation has state it doesn't have.

✅ **Right approach:**
```java
public interface DataService {
    List<User> getUsers();
    
    // Default only calls abstract methods
    default List<User> getActiveUsers() {
        return getUsers().stream()
            .filter(u -> u.isActive())
            .collect(toList());
    }
}
```

---

## 🛑 When NOT to Use Default Methods

1. **When behavior must vary significantly** → Make abstract, don't provide default
2. **For stateful operations** → Don't assume instance fields exist
3. **For expensive operations** → Default will be called by class with no custom optimization
4. **For security-sensitive code** → Don't hide important logic in defaults

---

**Next:** Study Q3 on static methods in interfaces
