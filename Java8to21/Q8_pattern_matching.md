# Q8: What is pattern matching (Java 16+)?

**Study Time:** 2-3 minutes

---

## Problem

Before pattern matching, type checking required boilerplate casting everywhere.

```java
// ❌ Old way: check type, then cast
if (obj instanceof String) {
    String str = (String) obj;  // Redundant cast
    System.out.println("Length: " + str.length());
}

if (obj instanceof Integer) {
    Integer num = (Integer) obj;  // Cast again
    System.out.println("Number: " + num);
}
```

This is repetitive and error-prone.

## ✅ Pattern Matching: Type Checking + Binding

```java
// Java 16+: check type AND get variable in one line
if (obj instanceof String str) {
    System.out.println("Length: " + str.length());  // str already bound!
}

if (obj instanceof Integer num) {
    System.out.println("Number: " + num);
}
```

The variable is automatically bound - no separate cast needed.

## Before vs After

### ❌ Before (Java 15)
```java
public String processPayment(Object obj) {
    if (obj instanceof Payment) {
        Payment payment = (Payment) obj;  // Manual cast
        return "Amount: " + payment.getAmount();
    }
    if (obj instanceof String) {
        String str = (String) obj;  // Another cast
        return "Note: " + str;
    }
    return "Unknown";
}
```

### ✅ After (Java 16+)
```java
public String processPayment(Object obj) {
    if (obj instanceof Payment payment) {
        return "Amount: " + payment.getAmount();  // payment bound automatically
    }
    if (obj instanceof String str) {
        return "Note: " + str;  // str bound automatically
    }
    return "Unknown";
}
```

## Switch Pattern Matching (Java 17+)

```java
// Modern switch with pattern matching
public String describeShape(Object obj) {
    return switch (obj) {
        case Square s -> "Area: " + (s.side * s.side);
        case Circle c -> "Area: " + (Math.PI * c.radius * c.radius);
        case String s -> "Name: " + s;
        case Integer i -> "Number: " + i;
        case null -> "Nothing";
        default -> "Unknown type";
    };
}
```

## Guarded Patterns (Java 17+)

Add conditions to patterns:

```java
public String classifyNumber(Object obj) {
    return switch (obj) {
        case Integer i when i > 0 -> "Positive: " + i;
        case Integer i when i < 0 -> "Negative: " + i;
        case Integer i -> "Zero";
        case String s when s.length() > 5 -> "Long string: " + s;
        case String s -> "Short string: " + s;
        default -> "Unknown";
    };
}

// Usage
System.out.println(classifyNumber(42));        // Positive: 42
System.out.println(classifyNumber(-5));        // Negative: -5
System.out.println(classifyNumber("hello!"));  // Long string: hello!
```

## Record Pattern Matching (Java 19+)

Pattern match on record fields:

```java
public record Payment(String id, double amount, String status) {}

public String handlePayment(Object obj) {
    return switch (obj) {
        case Payment(String id, double amt, "completed") -> 
            "Processed: $" + amt;
        case Payment(String id, double amt, "pending") -> 
            "Still pending: $" + amt;
        case Payment(String id, double amt, String st) -> 
            "Status " + st + ": $" + amt;
        default -> "Not a payment";
    };
}

// Usage
System.out.println(handlePayment(
    new Payment("P123", 100.0, "completed")
)); // Prints: Processed: $100.0
```

## Real Example: Result Type Handling

```java
public record Success<T>(T value) {}
public record Failure(Exception error) {}

public String handleResult(Object result) {
    return switch (result) {
        case Success(String value) when value.startsWith("OK") -> 
            "Success confirmed: " + value;
        case Success(String value) -> 
            "Success: " + value;
        case Failure(Exception error) -> 
            "Failed: " + error.getMessage();
        case null -> 
            "No result";
        default -> 
            "Unknown result type";
    };
}
```

## Evolution Timeline

```java
// Java 14: First preview (instanceof pattern)
if (obj instanceof String str) { }

// Java 15: Second preview

// Java 16: Standard feature (instanceof pattern confirmed)

// Java 17: Switch patterns added
switch (obj) {
    case String s -> ...
}

// Java 19+: Record patterns
case Success(String value) -> ...
```

## Interview Tip

"Pattern matching eliminates boilerplate by combining type checking and variable binding. `instanceof String str` checks type AND binds `str` in one line. Switch pattern matching (Java 17+) extends this for exhaustive type handling. Record patterns (Java 19+) let you destructure records directly in patterns - very powerful for sum types and Result<T> patterns."

## Quick Checklist

- ✅ `instanceof Type variable` = check + bind in one line
- ✅ Eliminates manual casting
- ✅ Switch expressions support pattern matching (Java 17+)
- ✅ Guarded patterns with `when` for conditions
- ✅ Record patterns for destructuring (Java 19+)
- ✅ Enables exhaustiveness checking in switch
- ✅ Growing feature - new patterns added regularly

---

## ⚠️ Common Pitfalls

**Pitfall 1: Incomplete switch - forgetting the default case (exhaustiveness issue)**

❌ **Wrong approach:**
```java
// With sealed classes, compiler can check exhaustiveness
public sealed class Result permits Success, Failure { }

public String handle(Result result) {
    return switch (result) {
        case Success s -> "Success!";
        // ❌ Missing Failure case!
        // Compiler ERROR (if sealed) or returns null
    };
}
```
**Why it fails:** Compiler can't guarantee all cases handled. If new type added to sealed class, old switch statements silently fail.

✅ **Right approach:**
```java
public String handle(Result result) {
    return switch (result) {
        case Success s -> "Success!";
        case Failure f -> "Failed: " + f.error();  // All cases covered
    };
}
```

---

**Pitfall 2: Nested record patterns getting too complex**

❌ **Wrong approach:**
```java
// Deeply nested destructuring is hard to read
public String processData(Object data) {
    return switch (data) {
        case Payment(String id, Amount(Currency c, double amt), Status(String st)) -> {
            // 4 levels deep! Hard to understand
            System.out.println(c + ": " + amt + " (" + st + ")");
        }
        default -> "Unknown";
    };
}
```
**Why it fails:** Pattern gets hard to understand and debug. Good code is readable.

✅ **Right approach:**
```java
// Either break into simpler patterns:
public String processData(Object data) {
    return switch (data) {
        case Payment payment -> handlePayment(payment);
        default -> "Unknown";
    };
}

private String handlePayment(Payment payment) {
    // Process with explicit variables, not nested patterns
    String id = payment.id();
    Amount amount = payment.amount();
    String status = payment.status().toString();
    
    return amount.currency() + ": " + amount.value() + " (" + status + ")";
}
```

---

## 🛑 When NOT to Use Pattern Matching

1. **When traditional if-else is clearer** → Pattern matching is style, not always better
2. **For simple type checks** → Don't over-engineer (e.g., if (obj instanceof String) is fine)
3. **With non-sealed hierarchies** → Pattern matching less useful without exhaustiveness checks
4. **When targeting Java < 16** → Pattern matching not available

---

**Next:** Study Q9 on text blocks for multiline strings
