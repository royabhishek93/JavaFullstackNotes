# 🎯 Q14: When Should You Create Custom Exceptions?

> **Interview Frequency:** 82% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Understanding when to create custom exceptions vs reusing built-in ones.

### Code Scenario
```java
// When should we create custom exception?
if (balance < amount) {
    throw new IllegalArgumentException("Insufficient balance");  // Generic
    // OR
    throw new InsufficientBalanceException("Balance: " + balance);  // Custom
}
```

---

## 📌 Why It Happens

**Create custom exceptions when:**
1. **Specific error type** - caller needs to handle differently
2. **Domain-specific** - payment, user, inventory errors
3. **Recurring pattern** - same error happens often
4. **Context matters** - need extra fields (balance, required amount)

**Reuse built-ins when:**
1. **Generic error** - could happen anywhere
2. **One-time** - doesn't recur
3. **Client can't recover** - just log and fail

---

## ❌ Wrong (Over-Creating Custom Exceptions)

```java
// WRONG: Too many custom exceptions
public class FileReadException extends Exception {}
public class FileWriteException extends Exception {}
public class FileValidationException extends Exception {}
// Now client must catch 3 separate exceptions for same domain!

public void readFile(String path) throws FileReadException {
    try {
        Files.readAllLines(Paths.get(path));
    } catch (IOException e) {
        throw new FileReadException(e);  // Unnecessary wrapper
    }
}
```

---

## ✅ Right (Strategic Custom Exceptions)

```java
// RIGHT: One exception for file operations domain
public class FileOperationException extends RuntimeException {
    private final String filePath;
    private final ErrorType type;  // READ, WRITE, VALIDATE
    
    public FileOperationException(String msg, String path, ErrorType type, Exception cause) {
        super(msg, cause);
        this.filePath = path;
        this.type = type;
    }
    
    public String getFilePath() { return filePath; }
    public ErrorType getType() { return type; }
}

public void readFile(String path) {
    try {
        Files.readAllLines(Paths.get(path));
    } catch (IOException e) {
        throw new FileOperationException(
            "Cannot read file: " + path,
            path,
            ErrorType.READ,
            e
        );
    }
}

// Client catches ONE exception with context
try {
    readFile("config.json");
} catch (FileOperationException e) {
    if (e.getType() == ErrorType.READ) {
        // Handle read-specific logic
    }
    logError("File error at: " + e.getFilePath(), e);
}
```

---

## 💬 Interview Tip (Say This Exactly)

"Create custom exceptions for domain-specific errors that clients need to handle differently. Include context (what failed, why). Use unchecked by default. Don't create one exception per method."

---

## ☑️ Quick Checklist

- ✅ Extend `RuntimeException` (unchecked) unless explicitly recoverable
- ✅ Include context fields (id, resource, timestamp)
- ✅ Provide clear exception message
- ✅ Always chain cause: `new CustomException(msg, cause)`
- ✅ One exception per business domain, not per method
- ✅ Make exceptions immutable
- ✅ Group by exception hierarchy
- ✅ Include error codes for logging/monitoring

---

## 📚 Real Flipkart Scenario

```java
// Custom exception hierarchy for payment domain
public class PaymentException extends RuntimeException {
    private final String orderId;
    private final String paymentGateway;
    private final int retryCount;
    
    public PaymentException(String msg, String orderId, 
                           String gateway, int retry, Exception cause) {
        super(msg, cause);
        this.orderId = orderId;
        this.paymentGateway = gateway;
        this.retryCount = retry;
    }
    
    public String getOrderId() { return orderId; }
    public String getPaymentGateway() { return paymentGateway; }
    public int getRetryCount() { return retryCount; }
}

// Specific: User has insufficient funds
public class InsufficientFundsException extends PaymentException {
    private final double requiredAmount;
    private final double availableAmount;
    
    public InsufficientFundsException(String orderId, double required, 
                                     double available, Exception cause) {
        super("Insufficient funds", orderId, "INTERNAL", 0, cause);
        this.requiredAmount = required;
        this.availableAmount = available;
    }
    
    // Client can check specific details
    public boolean canRetryWithDifferentPayment() {
        return availableAmount > 0;
    }
}

// Specific: Gateway timeout - can retry
public class PaymentGatewayTimeoutException extends PaymentException {
    public PaymentGatewayTimeoutException(String orderId, String gateway, 
                                        int retryCount, Exception cause) {
        super("Payment timeout", orderId, gateway, retryCount, cause);
    }
    
    public boolean shouldRetry() {
        return getRetryCount() < 3;
    }
}

// Usage: Different handling for different exceptions
try {
    processPayment(order);
} catch (InsufficientFundsException e) {
    // Tell user to add more funds
    notifyUser("Insufficient balance. Required: " + e.requiredAmount);
} catch (PaymentGatewayTimeoutException e) {
    // Retry logic
    if (e.shouldRetry()) {
        scheduleRetry(e.getOrderId());
    } else {
        cancelOrder(e.getOrderId());
    }
} catch (PaymentException e) {
    // Generic payment error
    logError("Payment failed for order: " + e.getOrderId(), e);
}
```

---

## ➡️ Bonus Follow-ups

1. **"Should custom exceptions be checked or unchecked?"** → Default to unchecked (RuntimeException)
2. **"What information to include?"** → Context needed to handle or debug
3. **"Exception vs error codes?"** → Exceptions for unexpected, error codes for expected conditions

---

## ⚠️ Common Pitfalls

**Pitfall 1: Creating too many custom exceptions**
```java
// ❌ Exception explosion!
class UserNotFoundException extends RuntimeException { }
class UserInactiveException extends RuntimeException { }
class UserDeletedException extends RuntimeException { }
class UserSuspendedException extends RuntimeException { }

// ✅ One exception with type or reason
class UserException extends RuntimeException {
    enum Reason { NOT_FOUND, INACTIVE, DELETED, SUSPENDED }
    private final Reason reason;
    // Constructor with reason
}
```

**Pitfall 2: Not preserving the cause**
```java
// ❌ Lost original cause!
catch (SQLException e) {
    throw new DatabaseException("Query failed");
}

// ✅ Always preserve cause
catch (SQLException e) {
    throw new DatabaseException("Query failed", e);  // Stack trace preserved
}
```

**Pitfall 3: Checked custom exceptions**
```java
public class UserException extends Exception { }  // ❌ Forces try-catch everywhere!

public class UserException extends RuntimeException { }  // ✅ Modern practice
```

**Pitfall 4: Empty exception classes**
```java
public class PaymentException extends RuntimeException { }  // ❌ No context!

// ✅ Add context fields
public class PaymentException extends RuntimeException {
    private final String orderId;
    private final String cardType;
    // Getters, constructors
}
```

---

## 🛑 When NOT to Create Custom Exceptions

- ❌ For every single error case
- ❌ When standard exceptions work (IllegalArgumentException, IllegalStateException)
- ❌ For temporary/local errors (use standard exceptions)
- ✅ DO create: Domain-specific errors (PaymentException, OrderException), errors needing extra context

---

## 🔗 Related Questions

- **Q13:** Checked vs Unchecked design
- **Q15:** Try-with-resources for cleanup
- **Q59:** Logging exceptions properly

---

**Last Updated:** February 22, 2026  
**Next: [Q15_try_with_resources.md](Q15_try_with_resources.md)**
