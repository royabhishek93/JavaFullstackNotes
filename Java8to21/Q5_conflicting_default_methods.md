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

**Next:** Study Q6 on Records for immutable data classes
