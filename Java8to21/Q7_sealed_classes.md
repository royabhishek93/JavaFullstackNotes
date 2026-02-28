# Q7: What are sealed classes (Java 17)?

**Study Time:** 2-3 minutes

---

## Problem

Before sealed classes, you couldn't control who could extend your class. Any class could inherit from yours, breaking assumptions.

```java
// You can't prevent unauthorized subclasses
public class PaymentProcessor {
    public void process(Payment payment) {
        // This could be called by ANY subclass
        // Maybe a malicious one?
    }
}

// Anyone can do this
public class FakeProcessor extends PaymentProcessor {
    @Override
    public void process(Payment payment) {
        System.out.println("I'm stealing data!");
    }
}
```

## Why It Matters

You might design a class with specific subclasses in mind. Without sealed classes, you have no control:
- A competitor could extend your secure class
- Unknown subclasses could break your assumptions
- No compile-time safety on allowed implementations

## ❌ Before Sealed Classes (Open to Anyone)

```java
// Anyone can extend this
public class PaymentProcessor {
    protected void log(String msg) {
        System.out.println("[PAYMENT] " + msg);
    }
}

public class CreditCardProcessor extends PaymentProcessor { }
public class BitcoinProcessor extends PaymentProcessor { }
public class EvilFakeProcessor extends PaymentProcessor {
    // ❌ We can't prevent this!
}
```

## ✅ After: Sealed Class (Java 17+)

```java
// Only CreditCardProcessor and BitcoinProcessor allowed
public sealed class PaymentProcessor 
    permits CreditCardProcessor, BitcoinProcessor {
    protected void log(String msg) {
        System.out.println("[PAYMENT] " + msg);
    }
}

public final class CreditCardProcessor extends PaymentProcessor { }
public final class BitcoinProcessor extends PaymentProcessor { }

// ❌ Error: EvilFakeProcessor not permitted
// public class EvilFakeProcessor extends PaymentProcessor { }
```

## Key Rules

```java
// Rule 1: You MUST list all permitted subclasses
public sealed class Shape permits Circle, Square, Triangle { }

// Rule 2: Permitted classes must be "final" or "sealed"
public final class Circle extends Shape { }
public sealed class Square extends Shape permits EmptySquare { }

// Rule 3: Same package or nested classes can inherit without listing
public sealed class Payment { }

// If in same file:
public final class CashPayment extends Payment { }
```

- ✅ `sealed class` + `permits ClassName1, ClassName2`
- ✅ All permitted classes must be `final` or `sealed`
- ✅ Compile-time exhaustion checking with pattern matching
- ✅ Prevents unauthorized subclassing

---

## ⚠️ Common Pitfalls

**Pitfall 1: Forgetting to make permitted classes final or sealed**

❌ **Wrong approach:**
```java
public sealed class Shape permits Circle, Square { }

// ❌ WRONG: Circle is not final or sealed!
public class Circle extends Shape {
    // Now someone can extend Circle:
    public class ColoredCircle extends Circle { }  // ❌ No longer sealed!
}
```
**Why it fails:** Breaks the sealed contract - your Shape hierarchy is no longer controlled.

✅ **Right approach:**
```java
public sealed class Shape permits Circle, Square { }

// ✅ CORRECT: All permitted classes are final
public final class Circle extends Shape { }
public final class Square extends Shape { }

// ✅ Or if you want subcategories, use sealed:
public sealed class Polygon extends Shape permits Square, Triangle { }
public final class Square extends Polygon { }
public final class Triangle extends Polygon { }
```

---

**Pitfall 2: Adding new subclass and forgetting to update permits list**

❌ **Wrong approach:**
```java
public sealed class PaymentMethod permits CreditCard, PayPal { }

// Later, you add a new payment method
public final class Bitcoin extends PaymentMethod { }

// ❌ Won't compile! Bitcoin not in permits!
// But only fails when someone tries to extend
```
**Why it fails:** No compile-time reminder that you forgot to update permits.

✅ **Right approach:**
```java
public sealed class PaymentMethod 
    permits CreditCard, PayPal, Bitcoin, ApplePay {
    // Keep permits list synchronized with actual implementations
}

// Or use same file (nested classes) - then permits not needed:
public sealed class PaymentMethod {
    public static final class CreditCard extends PaymentMethod { }
    public static final class PayPal extends PaymentMethod { }
    public static final class Bitcoin extends PaymentMethod { }
}
```

---

## 🛑 When NOT to Use Sealed Classes

1. **For open-ended frameworks** → Users should be able to extend
2. **For public APIs where flexibility matters** → Don't restrict subclasses
3. **In Java 16 or earlier** → Sealed classes need Java 17+ as finalization
4. **When you don't have all subclasses planned** → Design later, don't seal prematurely

---

## Real Example: Type-Safe Enum Pattern

```java
public sealed class Result<T> permits Success, Failure {
    public abstract <R> R fold(Function<T, R> onSuccess, 
                               Function<Exception, R> onFailure);
}

public final class Success<T> extends Result<T> {
    public T value;
    public Success(T value) { this.value = value; }
    
    @Override
    public <R> R fold(Function<T, R> onSuccess, 
                      Function<Exception, R> onFailure) {
        return onSuccess.apply(value);
    }
}

public final class Failure<T> extends Result<T> {
    public Exception error;
    public Failure(Exception error) { this.error = error; }
    
    @Override
    public <R> R fold(Function<T, R> onSuccess, 
                      Function<Exception, R> onFailure) {
        return onFailure.apply(error);
    }
}

// Usage - compiler knows all possible types
Result<String> result = getPaymentResult();
String output = result.fold(
    success -> "Got: " + success,  // Type-safe!
    failure -> "Error: " + failure.getMessage()
);
```

## When to Use Sealed Classes

🔥 **MUST KNOW:**
- You have a fixed set of subclasses (Strategy pattern)
- You want compile-time exhaustion checking
- You're modeling restricted type hierarchies (Result, Either, Option types)

✅ **SHOULD KNOW:**
- Type-safe enums or sum types
- Sealed interfaces for plugin architectures where you control plugins

👍 **GOOD TO KNOW:**
- Works with records for immutable sealed types
- Reduces need for boolean flags (e.g., success vs failure)

## Interview Tip

"Sealed classes (Java 17+) let you explicitly control which classes can extend yours using `permits`. All permitted classes must be `final` or `sealed`. This is useful for type-safe implementations like Result<T>, restricting inheritance, and enabling pattern matching exhaustion checks. The compiler enforces the restriction."

## Quick Checklist

- ✅ `sealed class` + `permits ClassName1, ClassName2`
- ✅ All permitted classes must be `final` or `sealed`
- ✅ Compile-time exhaustion checking with pattern matching
- ✅ Prevents unauthorized subclassing
- ✅ Great for Result/Either/Option type hierarchies
- ✅ Works with sealed interfaces too

---

**Next:** Study Q8 on pattern matching for advanced type checking
