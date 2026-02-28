# Q3: What are static methods in interfaces for?

**Study Time:** 2 minutes

---

## Problem

Understanding static interface methods and their use cases.

## Core Concept

Static methods in interfaces are **utility functions** that belong to the interface itself, not to instances. They **cannot be overridden**.

## ✅ Use Case 1: Factory Pattern

```java
public interface PaymentProcessor {
    void processPayment(double amount);
    
    // Static method - factory function
    static PaymentProcessor create(String type) {
        return switch (type.toLowerCase()) {
            case "stripe" -> new StripePayment();
            case "paypal" -> new PayPalPayment();
            case "crypto" -> new CryptoPayment();
            default -> throw new IllegalArgumentException("Unknown: " + type);
        };
    }
}

// Usage - called on INTERFACE, not instance
PaymentProcessor processor = PaymentProcessor.create("stripe");
// NOT: new StripePayment().create() ❌
// Static methods belong to interface, not instances
```

## ✅ Use Case 2: Utility Methods

```java
public interface PaymentProcessor {
    void processPayment(double amount);
    
    // Static utility
    static void validateAmount(double amount) {
        if (amount <= 0) {
            throw new IllegalArgumentException("Amount must be positive");
        }
    }
    
    // Default method CAN call static method
    default void pay(double amount) {
        PaymentProcessor.validateAmount(amount);  // Use static method
        processPayment(amount);
    }
}
```

## Key Difference: Can't Override Static Methods

```java
public interface PaymentProcessor {
    static PaymentProcessor create(String type) {
        return new GenericPayment();
    }
}

public class StripePayment implements PaymentProcessor {
    // ❌ WRONG - Can't override static methods!
    @Override
    static PaymentProcessor create(String type) {
        // Compilation error!
    }
}

// Static methods just hide/shadow - don't override
PaymentProcessor p1 = PaymentProcessor.create("test");
// Uses interface version

StripePayment p2 = StripePayment.create("test");
// Calls StripePayment version (different method, not override!)
```

## Real-World Examples

```java
// Collections API uses static methods
List<String> empty = Collections.emptyList();
Set<String> singleton = Collections.singleton("value");
Map<String, String> unmodifiable = Collections.unmodifiableMap(map);

// Stream API
Stream<Integer> range = Stream.iterate(1, i -> i + 1).limit(10);
```

## Interview Tip

"Static methods in interfaces are utilities and factories. They can't be overridden - they're not polymorphic. Use them for factory patterns like `Collections.emptyList()` or validation utilities."

## ⚠️ Common Pitfalls

**Pitfall 1: Trying to override static interface methods**

❌ **Wrong approach:**
```java
public interface PaymentProcessor {
    static PaymentProcessor create(String type) {
        return switch (type) {
            case "stripe" -> new StripePayment();
            default -> new GenericPayment();
        };
    }
}

public class StripePayment implements PaymentProcessor {
    @Override
    // ❌ WRONG: Can't override static methods!
    static PaymentProcessor create(String type) {
        return new StripePayment();
    }
}
```
**Why it fails:** Static methods aren't polymorphic. You're just shadowing, not overriding. Interfaces can't override interface static methods.

✅ **Right approach:**
```java
// Static methods in interfaces are utilities, not part of contract
public interface PaymentProcessor {
    void processPayment(double amount);  // Abstract - must override
    
    // Static utility - not overridable
    static PaymentProcessor create(String type) {
        return switch (type) {
            case "stripe" -> new StripePayment();
            default -> new GenericPayment();
        };
    }
}

// When you need polymorphic factory:
public class StripePayment implements PaymentProcessor {
    public static StripePayment create() {  // Same name, different class
        return new StripePayment();
    }
}
```

---

**Pitfall 2: Putting stateful logic in static interface methods**

❌ **Wrong approach:**
```java
public interface UserService {
    static Map<Integer, User> cache = new HashMap<>();  // ❌ Static in interface!
    
    static User getCachedUser(int id) {
        return cache.get(id);  // Shared by ALL classes
    }
}

public class DatabaseUserService implements UserService { }
public class CachingUserService implements UserService { }

// Both classes share the SAME cache!
DatabaseUserService.getCachedUser(1);  // Uses shared cache
CachingUserService.getCachedUser(1);   // Uses same shared cache
```
**Why it fails:** Static fields in interfaces are shared by everything. One class might poison the cache for another.

✅ **Right approach:**
```java
// Static utilities should be stateless
public interface UserService {
    User getUser(int id);
    
    // Utility - stateless
    static boolean isValidId(int id) {
        return id > 0;
    }
}

// State belongs in implementing classes
public class CachingUserService implements UserService {
    private final Map<Integer, User> cache = new HashMap<>();
    // ✅ Each instance has its own cache
}
```

---

## 🛑 When NOT to Use Static Interface Methods

1. **For creating instances with state** → Use factory classes instead
2. **For operations that need to share state** → Use singleton classes
3. **When visibility should differ per implementation** → Use abstract methods
4. **For methods that must be overridden** → Make them abstract

---

## Quick Checklist

- ✅ `static` keyword + method body in interface
- ✅ Called on interface, not instance (`InterfaceName.methodName()`)
- ✅ Can't override (can shadow only)
- ✅ Cannot access instance fields
- ✅ Use for: factories, utilities, helpers
- ✅ Perfect for static factory methods

---

**Next:** Study Q4 on private methods in interfaces (Java 9+)
