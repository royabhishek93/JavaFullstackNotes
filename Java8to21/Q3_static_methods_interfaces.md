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

## Quick Checklist

- ✅ `static` keyword + method body in interface
- ✅ Called on interface, not instance (`InterfaceName.methodName()`)
- ✅ Can't override (can shadow only)
- ✅ Cannot access instance fields
- ✅ Use for: factories, utilities, helpers
- ✅ Perfect for static factory methods

---

**Next:** Study Q4 on private methods in interfaces (Java 9+)
