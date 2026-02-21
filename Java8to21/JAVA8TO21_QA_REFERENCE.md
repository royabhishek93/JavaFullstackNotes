# Java 8-21 Modern Features - Q&A Reference Guide

> **Format:** Each question → Problem → Why It Happens → Wrong vs Right Code → Interview Tip → Checklist
> 
> **Use Case:** Modern Java features that seniors must know for 2026 interviews.

---

## 🎁 Interface Default & Static Methods

### Q1: What was the main problem before Java 8 interfaces?

**Problem:** Understanding why default methods were added.

**Why It Happens:**
Before Java 8, interfaces could ONLY have abstract methods. Adding any method forced ALL implementations to update.

**❌ Before Java 8 (The Problem):**
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
// 500+ files need updates
// Production risk, testing nightmare
```

**✅ After Java 8 (The Solution):**
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

// No breaking changes!
```

**Interview Tip:**
"Before Java 8, adding a method to an interface meant breaking ALL implementations - sometimes hundreds of classes. Default methods solved this by letting interfaces provide default implementation. This evolved the API safely."

**Quick Checklist:**
- ✅ Problem: Interface evolution = breaking change
- ✅ Solution: Default methods (Java 8+)
- ✅ Backward compatible: old code still works
- ✅ Real example: Collections API evolution

---

### Q2: What is a default method?

**Problem:** Understanding default method syntax and behavior.

**Core Concept:**
A default method is a method IN THE INTERFACE with an IMPLEMENTATION.

**✅ Syntax:**
```java
public interface PaymentProcessor {
    // Abstract method - no implementation
    void processPayment(double amount);
    
    // Default method - HAS implementation
    default void logTransaction(String msg) {
        System.out.println("[LOG] " + msg);  // Body!
    }
}

// Classes implementing:
public class StripePayment implements PaymentProcessor {
    @Override
    public void processPayment(double amount) {
        // Must implement abstract
    }
    
    // logTransaction() inherited automatically
}
```

**Interview Tip:**
"Default methods have implementations in the interface. Classes inherit them automatically but can override if needed. Perfect for adding utility methods to existing interfaces without breaking implementations."

**Quick Checklist:**
- ✅ `default` keyword + method body
- ✅ Optional to override (unlike abstract)
- ✅ Inherited by implementations automatically
- ✅ Can call other interface methods

---

### Q3: What are static methods in interfaces for?

**Problem:** Understanding static interface methods (factory functions).

**Core Concept:**
Static methods in interfaces are utility functions that can't be overridden.

**✅ Use Case - Factory Pattern:**
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

// Usage - called on interface, not instance
PaymentProcessor processor = PaymentProcessor.create("stripe");
```

**Interview Tip:**
"Static methods in interfaces are utilities and factories. They can't be overridden - they're not polymorphic. Use them for factory patterns like Collections.emptyList() or validation utilities."

**Quick Checklist:**
- ✅ Static + implementation in interface
- ✅ Called on interface, not instance
- ✅ Can't override (can shadow only)
- ✅ Use for: factories, utilities

---

### Q4: What about Java 9+ private methods in interfaces?

**Problem:** Sharing logic between default methods without code duplication.

**Why It Happens:**
Multiple default methods might need shared logic. Private methods let you share without exposing to implementations.

**❌ Before Java 9 (Code Duplication):**
```java
public interface PaymentProcessor {
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

**✅ After Java 9 (Private Method):**
```java
public interface PaymentProcessor {
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

**Interview Tip:**
"Java 9 added private methods to interfaces for code reuse between defaults. They're hidden from implementations - use them for internal logic that multiple defaults need."

**Quick Checklist:**
- ✅ Java 9+ only
- ✅ `private` keyword + implementation
- ✅ Can call from default/static methods
- ✅ Can't call from implementations (it's private)

---

### Q5: What happens with conflicting default methods?

**Problem:** When two interfaces have the same default method.

**❌ The Problem:**
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
}
```

**✅ Solution: Own Implementation**
```java
public class PaymentService implements ClientLogger, ServerLogger {
    @Override
    public void log(String msg) {
        // Your choice - your implementation
        System.out.println("PAYMENT: " + msg);
    }
}
```

**✅ Alternative: Delegate to One**
```java
public class PaymentService implements ClientLogger, ServerLogger {
    @Override
    public void log(String msg) {
        // Use ClientLogger's version
        ClientLogger.super.log(msg);
    }
}
```

**Interview Tip:**
"When implementing multiple interfaces with same default method, you must override to resolve ambiguity. Use `InterfaceName.super.methodName()` to call specific default."

**Quick Checklist:**
- ✅ Ambiguous = compiler error
- ✅ Must override to resolve
- ✅ `InterfaceName.super.method()` to delegate
- ✅ Can combine multiple super calls

---

## 📝 Records

### Q6: What are Records and why were they added?

**Problem:** Boilerplate for immutable data holders (DTOs).

**Traditional Class (Lots of Boilerplate):**
```java
public class Person {
    private final String name;
    private final int age;
    
    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }
    
    public String getName() { return name; }
    public int getAge() { return age; }
    
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Person person = (Person) o;
        return age == person.age && Objects.equals(name, person.name);
    }
    
    @Override
    public int hashCode() {
        return Objects.hash(name, age);
    }
    
    @Override
    public String toString() {
        return "Person{" + "name='" + name + '\'' + ", age=" + age + '}';
    }
}
```

**✅ Record (Same Class - 1 Line):**
```java
public record Person(String name, int age) {}

// Gets automatically:
// ✅ Constructor Person(String name, int age)
// ✅ Getters name() and age()
// ✅ equals() comparing all fields
// ✅ hashCode() using all fields
// ✅ toString() showing all fields
// ✅ Immutability (final fields)
```

**Interview Tip:**
"Records eliminate boilerplate for immutable data classes. One line replaces ~40. They're final, all fields immutable, and auto-generate equals/hashCode/toString. Perfect for DTOs, value objects, and domain objects."

**Quick Checklist:**
- ✅ `public record Name(Type field1, Type field2) {}`
- ✅ Auto-generates: constructor, getters, equals, hashCode, toString
- ✅ Fields are final (immutable)
- ✅ Record cannot extend (but can implement interfaces)
- ✅ Getters named `fieldName()` not `getFieldName()`

---

### Q7: What about Sealed Classes?

**Problem:** Controlling inheritance hierarchies.

**Why It Matters:**
Sometimes you want to limit which classes can extend yours.

**❌ Without Sealed (Anyone can extend):**
```java
public class Payment {
    public void process() { /* ... */ }
}

// Anyone in the world can extend
class FakePayment extends Payment {  // Sneaky!
    @Override
    public void process() {
        stealMoney();  // Evil!
    }
}
```

**✅ With Sealed (Control inheritance):**
```java
// Only StripePayment, PayPalPayment, CryptoPayment can extend
public sealed class Payment permits StripePayment, PayPalPayment, CryptoPayment {
    public void process() { /* ... */ }
}

public final class StripePayment extends Payment {
    @Override
    public void process() { stripePay(); }
}

public final class PayPalPayment extends Payment {
    @Override
    public void process() { paypalPay(); }
}

public final class CryptoPayment extends Payment {
    @Override
    public void process() { cryptoPay(); }
}

// ❌ This won't compile - not permitted!
class FakePayment extends Payment {  // Error
    @Override
    public void process() { stealMoney(); }
}
```

**Interview Tip:**
"Sealed classes let you define a fixed set of allowed subclasses. They document your design intent - 'these are the ONLY implementations'. Combined with pattern matching, enables exhaustive checking."

**Quick Checklist:**
- ✅ `public sealed class Name permits Impl1, Impl2, Impl3`
- ✅ Permitted classes must be `final` or `sealed`
- ✅ Enables pattern matching exhaustiveness
- ✅ Documents design intent

---

### Q8: What is Pattern Matching?

**Problem:** Ugly instanceof + casting code.

**❌ Before Pattern Matching:**
```java
Object obj = getObject();

if (obj instanceof String) {
    String str = (String) obj;  // Cast needed
    System.out.println("String length: " + str.length());
} else if (obj instanceof Integer) {
    Integer num = (Integer) obj;  // Cast needed
    System.out.println("Number: " + num * 2);
}
```

**✅ With Pattern Matching (Java 16+):**
```java
Object obj = getObject();

if (obj instanceof String s) {         // Type AND bind in one!
    System.out.println("String length: " + s.length());
} else if (obj instanceof Integer n) {  // Variable n is already int
    System.out.println("Number: " + n * 2);
}
```

**Interview Tip:**
"Pattern matching combines type checking and casting. Instead of `if instanceof then cast`, write `if instanceof Type var`. The variable is automatically in scope. Reduces casting code dramatically."

**Quick Checklist:**
- ✅ `instanceof Type variable` (Java 16+)
- ✅ Variable automatically in scope
- ✅ Works with generics: `List<?>`
- ✅ Works in switch expressions (Java 21+)

---

### Q9: What are Text Blocks?

**Problem:** Multi-line strings (SQL, JSON, HTML).

**❌ Before Text Blocks:**
```java
String json = "{\n" +
    "  \"name\": \"John\",\n" +
    "  \"age\": 30,\n" +
    "  \"active\": true\n" +
    "}";

// Ugly escaping!
```

**✅ With Text Blocks (Java 13+):**
```java
String json = """
    {
      "name": "John",
      "age": 30,
      "active": true
    }
    """;

// Clean and readable!
```

**Interview Tip:**
"Text blocks use triple quotes for multi-line strings. Preserve formatting, no escape characters needed. Huge readability improvement for JSON, SQL, and HTML embedded in Java."

**Quick Checklist:**
- ✅ `"""` triple quotes
- ✅ Java 13+
- ✅ Preserves formatting (indentation, newlines)
- ✅ No `\n` or `+` needed

---

## 🔄 CompletableFuture

### Q10: What is CompletableFuture?

**Problem:** Handling asynchronous operations and composing them.

**Simple Example:**
```java
CompletableFuture<String> future = new CompletableFuture<>();

// Start background work
new Thread(() -> {
    try {
        Thread.sleep(2000);
        future.complete("Data ready!");
    } catch (Exception e) {
        future.completeExceptionally(e);
    }
}).start();

System.out.println("Main: Started");

// Later, get the result (blocks until ready)
String result = future.get();
System.out.println("Main: Got " + result);
```

**Better: Factory Methods:**
```java
// supplyAsync - returns value
CompletableFuture<String> future1 = CompletableFuture.supplyAsync(() -> {
    return "Data from background";
});

// runAsync - no return value
CompletableFuture<Void> future2 = CompletableFuture.runAsync(() -> {
    System.out.println("Background task");
});
```

**Interview Tip:**
"CompletableFuture is a promise that a value will be available later. Use `supplyAsync()` to run work in background thread. Use `.get()` to wait for result. Perfect for calling APIs or slow operations without blocking."

**Quick Checklist:**
- ✅ `CompletableFuture<T>` - promise of T
- ✅ `supplyAsync(Supplier)` - background task returning value
- ✅ `runAsync(Runnable)` - background task returning void
- ✅ `.get()` - blocks until complete
- ✅ `.complete(value)` - fulfill promise

---

### Q11: How do you chain async operations?

**Problem:** Composing multiple async operations (A, then B using A's result).

**❌ Wrong Way (Blocking):**
```java
User user = userFuture.get();  // BLOCKS
List<Order> orders = fetchOrders(user.getId()).get();  // BLOCKS again
```

**✅ Right Way - Non-Blocking Chaining:**

**Method 1: `thenApply()` - Transform**
```java
CompletableFuture<String> usernameFuture = userFuture
    .thenApply(user -> user.getName());
```

**Method 2: `thenCompose()` - Chain async**
```java
CompletableFuture<List<Order>> ordersFuture = userFuture
    .thenCompose(user -> fetchOrders(user.getId()));
    
List<Order> orders = ordersFuture.get();  // No blocking before this!
```

**Method 3: `thenCombine()` - Combine two futures**
```java
CompletableFuture<String> combined = userFuture
    .thenCombine(profileFuture, (user, profile) ->
        user.name + " - " + profile.bio
    );
```

**Interview Tip:**
"Chain async operations with `thenCompose()` (return CompletableFuture) or `thenApply()` (return value). Don't call `.get()` in the middle - it defeats the purpose. Build the chains first, then `.get()` at the end."

**Quick Checklist:**
- ✅ `thenApply(Function)` - transform value
- ✅ `thenCompose(Function)` - chain async
- ✅ `thenCombine(other, BiFunction)` - combine two
- ✅ Don't `.get()` in the middle!

---

### Q12: How do you handle exceptions?

**Problem:** Exceptions in async operations.

**Method 1: `exceptionally()` - Recover**
```java
CompletableFuture<String> future = fetchData()
    .exceptionally(ex -> {
        System.out.println("Error: " + ex.getMessage());
        return "DEFAULT_VALUE";
    });
```

**Method 2: `handle()` - Handle both**
```java
CompletableFuture<String> future = fetchData()
    .handle((data, ex) -> {
        if (ex != null) {
            return "ERROR: " + ex.getMessage();
        } else {
            return "SUCCESS: " + data;
        }
    });
```

**Method 3: `whenComplete()` - Side effects**
```java
CompletableFuture<String> future = fetchData()
    .whenComplete((result, ex) -> {
        if (ex != null) {
            System.out.println("Error occurred");
        } else {
            System.out.println("Success: " + result);
        }
    });
```

**Interview Tip:**
"Use `exceptionally()` to recover with a default value. Use `handle()` for complex error handling. Use `whenComplete()` for side effects like logging. Chain them appropriately in your async pipeline."

**Quick Checklist:**
- ✅ `exceptionally(Function)` - recover with default
- ✅ `handle(BiFunction)` - handle success/failure
- ✅ `whenComplete(BiConsumer)` - side effects only
- ✅ Exceptions propagate down chain

---

**Last Updated:** February 2026
