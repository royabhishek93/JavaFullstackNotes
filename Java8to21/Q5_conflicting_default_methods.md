# Q5: What happens with conflicting default methods?

**Study Time:** 2-3 minutes

---

## Problem

Understanding the "diamond problem" when a class implements two interfaces with the same default method.

## ❌ The Problem

```java
public interface ClientLogger {
    default void log(String msg) {
        System.out.println("CLIENT: " + msg);
    }
}

public interface ServerLogger {
    default void log(String msg) {
        System.out.println("SERVER: " + msg);
    }
}

// Which log() should this class use?
public class PaymentService implements ClientLogger, ServerLogger {
    // ❌ Compiler error: ambiguous method log()
    // Reference to method is ambiguous!
}
```

## ✅ Solution 1: Provide Your Own Implementation

```java
public class PaymentService implements ClientLogger, ServerLogger {
    @Override
    public void log(String msg) {
        // Your choice - your implementation
        System.out.println("PAYMENT: " + msg);
    }
}

// Usage
PaymentService service = new PaymentService();
service.log("test");  // Prints: PAYMENT: test
```

## ✅ Solution 2: Delegate to One Interface

```java
public class PaymentService implements ClientLogger, ServerLogger {
    @Override
    public void log(String msg) {
        // Use ClientLogger's version
        ClientLogger.super.log(msg);
    }
}

// Usage
PaymentService service = new PaymentService();
service.log("test");  // Prints: CLIENT: test
```

## ✅ Solution 3: Combine Both

```java
public class PaymentService implements ClientLogger, ServerLogger {
    @Override
    public void log(String msg) {
        ClientLogger.super.log(msg);  // Log client
        ServerLogger.super.log(msg);  // Log server
    }
}

// Usage
PaymentService service = new PaymentService();
service.log("test");
// Prints:
// CLIENT: test
// SERVER: test
```

## Key Rule: InterfaceName.super.methodName()

```java
// Syntax to call specific interface's default method
InterfaceName.super.methodName(args);

// Example:
ClientLogger.super.log("message");
```

## Interview Tip

"When implementing multiple interfaces with same default method, you must override to resolve ambiguity. Use `InterfaceName.super.methodName()` to call specific default. This shows you understand the diamond problem and can make design decisions."

## Quick Checklist

- ✅ Ambiguous default methods = compiler error
- ✅ Must override to resolve conflict
- ✅ `InterfaceName.super.method()` to delegate to specific interface
- ✅ Can call multiple super methods in one override
- ✅ Your implementation takes precedence if you override
- ✅ Shows understanding of multiple inheritance

---

## ⚠️ Common Pitfalls

**Pitfall 1: Silently using ONE interface's default without realizing ambiguity**

❌ **Wrong approach:**
```java
public interface OrderLogger {
    default void log(String msg) {
        System.out.println("ORDER: " + msg);
    }
}

public interface ShippingLogger {
    default void log(String msg) {
        System.out.println("SHIPPING: " + msg);
    }
}

// ❌ This will NOT compile!
public class ShipmentService implements OrderLogger, ShippingLogger {
    // Compiler screams: "ambiguous method log(String)"
}

// But if you DON'T reference log() in the class,
// it silently fails when someone calls it
```
**Why it fails:** Compiler forces you to resolve, but developers often just ignore the error, leading to mysterious issues later.

✅ **Right approach:**
```java
public class ShipmentService implements OrderLogger, ShippingLogger {
    @Override
    public void log(String msg) {
        // You decide
        System.out.println("SHIPMENT: " + msg);
    }
}
```

---

**Pitfall 2: Using wrong interface.super() reference**

❌ **Wrong approach:**
```java
public class PaymentService implements ClientService, ServerService {
    @Override
    public void notify(String msg) {
        // Meant to call ServerService but called ClientService
        ClientService.super.notify(msg);  // ❌ Wrong one!
    }
}
```
**Why it fails:** No compile-time check - you get the wrong behavior silently.

✅ **Right approach:**
```java
public class PaymentService implements ClientService, ServerService {
    @Override
    public void notify(String msg) {
        // Be explicit about WHICH interface you're delegating to
        ServerService.super.notify(msg);  // ✅ Clear intent
    }
}
```

---

## 🛑 When NOT to Use Multiple Interface Defaults

1. **When you actually need different behavior** → Create separate classes, not multiple implements
2. **For conflicting contracts** → Rethink design - interfaces should be orthogonal
3. **When you don't understand which one wins** → Simplify design, use composition

---

**Next:** Study Q6 on Records for immutable data classes
