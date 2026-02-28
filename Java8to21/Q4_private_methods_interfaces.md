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

## ⚠️ Common Pitfalls

**Pitfall 1: Using private methods in Java 8 codebase**

❌ **Wrong approach:**
```java
// Target: Java 8 (production server is Java 8)
public interface PaymentProcessor {
    void processPayment(double amount);
    
    default void logTransaction(String msg) {
        validate(msg);  // ❌ Private methods added Java 9!
    }
    
    // This will NOT compile on Java 8!
    private void validate(String msg) {
        if (msg == null) throw new IllegalArgumentException();
    }
}

// Compilation error: Java 8 doesn't support private interface methods
```
**Why it fails:** Feature available only in Java 9+. Will fail at compile time if targeting Java 8.

✅ **Right approach:**
```java
// Option 1: Stay on Java 8 - duplicate code
public interface PaymentProcessor {
    void processPayment(double amount);
    
    default void logTransaction(String msg) {
        if (msg == null) throw new IllegalArgumentException();
        System.out.println("[LOG] " + msg);
    }
    
    default void refund(double amount) {
        if (amount <= 0) throw new IllegalArgumentException();  // Duplication
        System.out.println("[REFUND] " + amount);
    }
}

// Option 2: Upgrade to Java 9+ and use private methods
```

---

**Pitfall 2: Circular dependencies in private methods**

❌ **Wrong approach:**
```java
public interface DataService {
    List<User> getUsers();
    
    private List<User> getValidUsers() {
        return getFilteredUsers(u -> u.isValid());
    }
    
    private List<User> getFilteredUsers(Predicate<User> filter) {
        return getValidUsers().stream()  // ❌ Circular call!
            .filter(filter)
            .collect(toList());
    }
}
```
**Why it fails:** Stack overflow - getValidUsers → getFilteredUsers → getValidUsers → ...

✅ **Right approach:**
```java
public interface DataService {
    List<User> getUsers();
    
    default List<User> getValidUsers() {
        return filterByStatus(getUsers(), "VALID");
    }
    
    private List<User> filterByStatus(List<User> users, String status) {
        return users.stream()
            .filter(u -> u.getStatus().equals(status))
            .collect(toList());
    }
}
```

---

## 🛑 When NOT to Use Private Interface Methods

1. **On Java 8 or earlier** → Not supported, code won't compile
2. **When implementations need to override logic** → Make it abstract or default
3. **For complex internal logic** → Move to abstract class or utility class instead
4. **When multiple unrelated defaults need same logic** → Consider composition over interfaces

---

**Next:** Study Q5 on conflicting default methods
