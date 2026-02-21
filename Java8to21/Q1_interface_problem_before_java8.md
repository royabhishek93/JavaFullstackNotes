# Q1: What was the main problem before Java 8 interfaces?

**Study Time:** 2-3 minutes

---

## Problem

Understanding why default methods were added to interfaces.

## Why It Happens

Before Java 8, interfaces could ONLY have abstract methods. Adding any method forced ALL implementations to update - potentially breaking hundreds of classes.

## ❌ Before Java 8 (The Problem)

```java
// Large ecosystem: 500+ classes implement this
public interface PaymentProcessor {
    void processPayment(double amount);
    void refund(double amount);
    // No new methods - existing implementations depend on stability
}

// New requirement: add validation
// ONLY option: make it abstract
public interface PaymentProcessor {
    void processPayment(double amount);
    void refund(double amount);
    void validatePaymentMethod();  // NEW - breaks 500+ classes!
}

// Every implementing class now has compiler errors!
// 500+ files need updates = massive refactor = production risk!
```

## ✅ After Java 8 (The Solution)

```java
public interface PaymentProcessor {
    void processPayment(double amount);
    void refund(double amount);
    
    // Default method - NEW without breaking changes!
    default void validatePaymentMethod() {
        System.out.println("Validating...");
    }
}

// Existing implementations?
public class StripePayment implements PaymentProcessor {
    @Override
    public void processPayment(double amount) { /* ... */ }
    
    @Override
    public void refund(double amount) { /* ... */ }
    
    // No changes needed! validatePaymentMethod() inherited
}

// No breaking changes! ✅
```

## Real-World Example: Collections API

Java 8 added `forEach()` to `Iterable`:

```java
// If they made it abstract, ALL collection classes would break
// Instead they used default method:
public interface Iterable<T> {
    Iterator<T> iterator();
    
    default void forEach(Consumer<? super T> action) {
        for (T t : this) {
            action.accept(t);
        }
    }
}

// All collections got forEach() for free!
// No implementation changes needed
```

## Interview Tip

"Before Java 8, adding a method to an interface meant breaking ALL implementations - sometimes hundreds of classes. This was a maintenance nightmare. Default methods solved this by letting interfaces provide default implementation. This evolved the API safely."

## Quick Checklist

- ✅ Problem: Interface evolution = breaking change for all implementations
- ✅ Solution: Default methods (Java 8+)
- ✅ Backward compatible: old code still works
- ✅ Real example: Collections API evolution (forEach, stream, etc.)
- ✅ Preserved millions of lines of legacy code

---

**Next:** Study Q2 to understand what is a default method
