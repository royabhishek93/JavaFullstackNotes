# Q4: What about Java 9+ private methods in interfaces?

**Study Time:** 2-3 minutes

---

## Problem

Sharing logic between default methods without code duplication.

## Why It Happens

Multiple default methods might need shared validation or formatting logic. Private methods let you share code without exposing it to implementations (true encapsulation).

## ❌ Before Java 9 (Code Duplication)

```java
public interface PaymentProcessor {
    void processPayment(double amount);
    
    default void logTransaction(String action, double amount) {
        // Validation logic duplicated
        if (amount <= 0) throw new IllegalArgumentException();
        System.out.println("[" + action + "] " + amount);
    }
    
    default void refund(double amount) {
        // Same validation logic repeated!
        if (amount <= 0) throw new IllegalArgumentException();
        System.out.println("[REFUND] " + amount);
    }
}
```

## ✅ After Java 9 (Private Method)

```java
public interface PaymentProcessor {
    void processPayment(double amount);
    
    default void logTransaction(String action, double amount) {
        validate(amount);  // Call private method
        System.out.println("[" + action + "] " + amount);
    }
    
    default void refund(double amount) {
        validate(amount);  // Reuse private method
        System.out.println("[REFUND] " + amount);
    }
    
    // Private method - hidden from implementations
    private void validate(double amount) {
        if (amount <= 0) throw new IllegalArgumentException("Amount must be > 0");
    }
}
```

## Usage

```java
public class StripePayment implements PaymentProcessor {
    @Override
    public void processPayment(double amount) {
        System.out.println("Stripe: Processing $" + amount);
    }
}

// Usage
PaymentProcessor processor = new StripePayment();
processor.logTransaction("PROCESS", 100);  // ✅ Works, uses private validate()
processor.validate(100);  // ❌ Compilation error - private!
```

## Encapsulation Benefits

```java
// Private method encapsulates internal logic
private void validate(double amount) {
    if (amount <= 0) throw new IllegalArgumentException();
    if (amount > 1_000_000) throw new IllegalArgumentException();
}

// Implementations don't need to know about these validation rules
// Only see: logTransaction(), refund(), processPayment()
```

## Interview Tip

"Java 9 added private methods to interfaces for code reuse between defaults. They're hidden from implementations - use them for internal logic that multiple defaults need. This is true encapsulation at the interface level."

## Quick Checklist

- ✅ Java 9+ only (not available in Java 8)
- ✅ `private` keyword + method body
- ✅ Can call from default methods
- ✅ Can call from static methods
- ✅ Can't call from implementations (it's private)
- ✅ Perfect for: shared validation, formatting, internal utilities
- ✅ Improves maintainability and DRY principle

---

**Next:** Study Q5 on conflicting default methods
