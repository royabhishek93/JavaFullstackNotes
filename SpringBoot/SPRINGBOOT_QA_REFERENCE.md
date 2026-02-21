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

**Real Example: Collections API**
```java
// Java 8 added forEach() to Iterable
public interface Iterable<T> {
    Iterator<T> iterator();
    
    // NEW: default method (not abstract)
    default void forEach(Consumer<? super T> action) {
        for (T t : this) {
            action.accept(t);
        }
    }
}

// All collections (ArrayList, HashMap, etc.) got forEach() for free
// No need to update 100+ collection classes
```

**Interview Tip:**
"Before Java 8, adding a method to an interface meant breaking ALL implementations - sometimes hundreds of classes. Default methods solved this by letting interfaces provide default implementation. This evolved the API safely."

**Quick Checklist:**
- ✅ Problem: Interface evolution = breaking change
- ✅ Solution: Default methods (Java 8+)
- ✅ Backward compatible: old code still works
- ✅ Real example: Collections API evolution
- ✅ Also enabled: functional programming (lambdas)

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
    // Can call it:
    // this.logTransaction("Payment processed");
}
```

**When to Override:**
```java
public class CryptoPayment implements PaymentProcessor {
    @Override
    public void processPayment(double amount) {
        // Implement abstract method
    }
    
    @Override
    // Optional: override if needed
    default void logTransaction(String msg) {
        // Custom crypto-specific logging
        System.out.println("[CRYPTO] " + msg);
    }
}
```

**Real-World Pattern:**
```java
// Common pattern: default calls abstract method
public interface DataService {
    List<User> getUsers();  // Abstract - how to get data
    
    default int getUserCount() {
        // Uses abstract method, delegates to implementation
        return getUsers().size();
    }
}

// Different implementations, same default behavior
public class DatabaseService implements DataService {
    @Override
    public List<User> getUsers() {
        return database.query("SELECT * FROM users");
    }
    // getUserCount() works - returns size of query result
}

public class CachedService implements DataService {
    @Override
    public List<User> getUsers() {
        return cache.getOrFetch("users", () -> database.query(...));
    }
    // getUserCount() works - returns size of cached result
}
```

**Interview Tip:**
"Default methods have implementations in the interface. Classes inherit them automatically but can override if needed. Perfect for adding utility methods to existing interfaces without breaking implementations."

**Quick Checklist:**
- ✅ `default` keyword + method body
- ✅ Optional to override (unlike abstract)
- ✅ Inherited by implementations automatically
- ✅ Can call other interface methods
- ✅ NOT instance-specific (can't access fields)

---

### Q3: What are static methods in interfaces for?

**Problem:** Understanding static interface methods.

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

// Usage
PaymentProcessor processor = PaymentProcessor.create("stripe");
// NOT: new StripePayment().create()
// Static methods belong to interface, not instances
```

**✅ Another Use Case - Utilities:**
```java
public interface PaymentProcessor {
    void processPayment(double amount);
    
    // Static utility
    static void validateAmount(double amount) {
        if (amount <= 0) {
            throw new IllegalArgumentException("Amount must be positive");
        }
    }
    
    // Can be used anywhere
    default void pay(double amount) {
        PaymentProcessor.validateAmount(amount);  // Use static method
        processPayment(amount);
    }
}
```

**Key Difference - Can't Override:**
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
    
    // Static methods just hide/shadow - don't override
}

// Usage
PaymentProcessor p1 = PaymentProcessor.create("test");      // Uses interface version
StripePayment p2 = StripePayment.create("test");           // Calls StripePayment version (different method!)
```

**Interview Tip:**
"Static methods in interfaces are utilities and factories. They can't be overridden - they're not polymorphic. Use them for factory patterns like Collections.emptyList() or validation utilities."

**Quick Checklist:**
- ✅ Static + implementation in interface
- ✅ Called on interface, not instance
- ✅ Can't override (can shadow only)
- ✅ Use for: factories, utilities
- ✅ Perfect for: switch expressions (Java 14+)

---

### Q4: What about Java 9+ private methods in interfaces?

**Problem:** Sharing logic between default methods without duplication.

**Why It Happens:**
Multiple default methods might need shared logic. Private methods let you share without exposing to implementations.

**❌ Before Java 9 (Code Duplication):**
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

**✅ After Java 9 (Private Method):**
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

// Implementations can't call validate() - it's private!
public class StripePayment implements PaymentProcessor {
    @Override
    public void processPayment(double amount) {
        // validate(amount);  // ❌ Compilation error - private!
    }
}
```

**Interview Tip:**
"Java 9 added private methods to interfaces for code reuse between defaults. They're hidden from implementations - use them for internal logic that multiple defaults need. Improves maintainability and DRY principle."

**Quick Checklist:**
- ✅ Java 9+ only
- ✅ `private` keyword + implementation
- ✅ Can call from default/static methods
- ✅ Can't call from implementations (it's private)
- ✅ Perfect for: shared validation, formatting, utils

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

**Solution 1: Own Implementation**
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

**Solution 2: Delegate to One**
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

**Solution 3: Combine Both**
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

**Interview Tip:**
"When implementing multiple interfaces with same default method, you must override to resolve ambiguity. Use `InterfaceName.super.methodName()` to call specific default. Shows you understand multiple inheritance of type."

**Quick Checklist:**
- ✅ Ambiguous = compiler error
- ✅ Must override to resolve
- ✅ `InterfaceName.super.method()` to delegate
- ✅ Can combine multiple super calls
- ✅ Shows understanding of interface contracts

---

## 📝 Records

### Q6: What are Records and why were they added?

**Problem:** Boilerplate for immutable data holders (DTOs).

**Traditional Class (Lots of Boilerplate):**
```java
public class Person {
    private final String name;
    private final int age;
    
    // Constructor
    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }
    
    // Getters
    public String getName() { return name; }
    public int getAge() { return age; }
    
    // Equals
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Person person = (Person) o;
        return age == person.age && Objects.equals(name, person.name);
    }
    
    // HashCode
    @Override
    public int hashCode() {
        return Objects.hash(name, age);
    }
    
    // ToString
    @Override
    public String toString() {
        return "Person{" + "name='" + name + '\'' + ", age=" + age + '}';
    }
}

// Total: ~40 lines for simple data holder!
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

// Total: 1 line! Everything else generated.
```

**Usage Is Same:**
```java
// Traditional
Person p1 = new Person("John", 30);
String name = p1.getName();
int age = p1.getAge();

// Record  
Person p2 = new Person("John", 30);
String name = p2.name();  // Note: name() not getName()
int age = p2.age();       // Note: age() not getAge()

// Equals works the same
System.out.println(p1.equals(p2));  // true

// Collections work the same
Set<Person> people = new HashSet<>();
people.add(p1);
people.add(p2);

// Maps work the same
Map<Person, String> map = new HashMap<>();
map.put(p1, "Developer");
```

**Interview Tip:**
"Records eliminate boilerplate for immutable data classes. One line replaces ~40. They're final, all fields immutable, and auto-generate equals/hashCode/toString. Perfect for DTOs, value objects, and domain objects."

**Quick Checklist:**
- ✅ `public record Name(Type field1, Type field2) {}`
- ✅ Auto-generates: constructor, getters, equals, hashCode, toString
- ✅ Fields are final (immutable)
- ✅ Record cannot extend (but can implement interfaces)
- ✅ Getters named `fieldName()` not `getFieldName()`
- ✅ Perfect for: DTOs, value objects, data carriers

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
class FakePayment extends Payment {  // Error: class not in permits list
    @Override
    public void process() { stealMoney(); }
}
```

**Benefits:**
```java
// Compiler knows all possible types
sealed class Shape permits Circle, Rectangle, Triangle { }

public final class Circle extends Shape { /* ... */ }
public final class Rectangle extends Shape { /* ... */ }
public final class Triangle extends Shape { /* ... */ }

// Pattern matching can be exhaustive
void calculateArea(Shape shape) {
    if (shape instanceof Circle c) {
        return Math.PI * c.radius * c.radius;
    } else if (shape instanceof Rectangle r) {
        return r.width * r.height;
    } else if (shape instanceof Triangle t) {
        return t.base * t.height / 2;
    }
    // Compiler knows we covered all cases!
}
```

**Interview Tip:**
"Sealed classes let you define a fixed set of allowed subclasses. They document your design intent - 'these are the ONLY implementations'. Combined with pattern matching, enables exhaustive checking."

**Quick Checklist:**
- ✅ `public sealed class Name permits Impl1, Impl2, Impl3`
- ✅ Permitted classes must be `final` or `sealed`
- ✅ Enables pattern matching exhaustiveness
- ✅ Documents design intent
- ✅ Works with records too: `sealed record`

---

### Q8: What is Pattern Matching?

**Problem:** Ugly instanceof + casting code.

**❌ Before Pattern Matching:**
```java
Object obj = getObject();

// Ugly boilerplate
if (obj instanceof String) {
    String str = (String) obj;  // Cast needed
    System.out.println("String length: " + str.length());
} else if (obj instanceof Integer) {
    Integer num = (Integer) obj;  // Cast needed
    System.out.println("Number: " + num * 2);
} else if (obj instanceof List) {
    List list = (List) obj;  // Cast needed
    System.out.println("List size: " + list.size());
}
```

**✅ With Pattern Matching (Java 16+):**
```java
Object obj = getObject();

if (obj instanceof String s) {         // Type AND bind in one!
    System.out.println("String length: " + s.length());
} else if (obj instanceof Integer n) {  // Variable n is already int
    System.out.println("Number: " + n * 2);
} else if (obj instanceof List<?> list) { // Generic type
    System.out.println("List size: " + list.size());
}
```

**Benefits:**
1. Less boilerplate
2. Variable in scope automatically
3. Type-safe (compiler checks)
4. Readable

**Advanced Pattern Matching:**
```java
// Switch with patterns (Java 21+)
String result = switch (obj) {
    case String s -> "Length: " + s.length();
    case Integer n -> "Double: " + (n * 2);
    case List<?> list -> "Size: " + list.size();
    default -> "Unknown";
};
```

**Interview Tip:**
"Pattern matching combines type checking and casting. Instead of `if isinstance then cast`, write `if instanceof Type var`. The variable is automat in scope. Reduces boilerplate significantly."

**Quick Checklist:**
- ✅ `instanceof Type variable` (Java 16+)
- ✅ Variable automatically in scope
- ✅ Works with generics: `List<?>`
- ✅ Works in switch expressions (Java 21+)
- ✅ Reduces casting code dramatically

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

String sql = "SELECT * FROM users\n" +
    "WHERE age > 18\n" +
    "AND status = 'active'";

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

String sql = """
    SELECT * FROM users
    WHERE age > 18
    AND status = 'active'
    """;

// Clean and readable!
```

**Practical Benefits:**
```java
// REST API JSON
String request = """
    {
        "method": "POST",
        "url": "https://api.example.com/payment",
        "headers": {
            "Content-Type": "application/json"
        },
        "body": {
            "amount": 100,
            "currency": "USD"
        }
    }
    """;

// HTML templates
String html = """
    <html>
        <body>
            <h1>Welcome!</h1>
            <p>Your payment was processed.</p>
        </body>
    </html>
    """;
```

**Interview Tip:**
"Text blocks use triple quotes for multi-line strings. Preserve formatting, no escape characters needed. Huge readability improvement for JSON, SQL, and HTML embedded in Java."

**Quick Checklist:**
- ✅ `"""` triple quotes
- ✅ Java 13+
- ✅ Preserves formatting (indentation, newlines)
- ✅ No `\n` or `+` needed
- ✅ Perfect for: JSON, SQL, XML, HTML

---

## 🔄 CompletableFuture

### Q10: What is CompletableFuture?

**Problem:** Handling asynchronous operations and composing them.

**Core Concept:**
A promise that a value will be available in the future.

**Simple Example:**
```java
// Create a CompletableFuture that completes in background
CompletableFuture<String> future = new CompletableFuture<>();

// Start background work
new Thread(() -> {
    try {
        Thread.sleep(2000);  // Simulate work
        future.complete("Data ready!");  // Fulfill promise
    } catch (Exception e) {
        future.completeExceptionally(e);  // Or error
    }
}).start();

// Main thread doesn't wait - continues here
System.out.println("Main: Started");

// Later, get the result (blocks until ready)
String result = future.get();  // Blocks here
System.out.println("Main: Got " + result);

// Output:
// Main: Started
// (2 second pause)
// Main: Got Data ready!
```

**Better: CompletableFuture Factory Methods:**
```java
// Method 1: supplyAsync - background thread produces value
CompletableFuture<String> future1 = CompletableFuture.supplyAsync(() -> {
    return "Data from background";  // Runs in thread pool
});

// Method 2: runAsync - background thread, no return value
CompletableFuture<Void> future2 = CompletableFuture.runAsync(() -> {
    System.out.println("Background task");  // Runs in thread pool
});

// Get results
String data = future1.get();  // Blocks
future2.get();
```

**Real-World Example:**
```java
// Fetch data from API without blocking main thread
public CompletableFuture<User> fetchUser(String userId) {
    return CompletableFuture.supplyAsync(() -> {
        // Background thread makes HTTP request
        return httpClient.get("/users/" + userId);  // May take seconds
    });
}

// Usage
CompletableFuture<User> userFuture = fetchUser("123");

System.out.println("Fetching...");  // Continues immediately

// Later, when ready:
User user = userFuture.get();
System.out.println("Got: " + user.name);
```

**Interview Tip:**
"CompletableFuture is a promise that a value will be available later. Use `supplyAsync()` to run work in background thread. Use `.get()` to wait for result. Perfect for calling APIs or slow operations without blocking."

**Quick Checklist:**
- ✅ `CompletableFuture<T>` - promise of T
- ✅ `supplyAsync(Supplier)` - background task returning value
- ✅ `runAsync(Runnable)` - background task returning void
- ✅ `.get()` - blocks until complete
- ✅ `.complete(value)` - fulfill promise
- ✅ `.completeExceptionally(e)` - fulfill with error

---

### Q11: How do you chain async operations?

**Problem:** Composing multiple async operations (operation A, then B using A's result).

**Scenario:**
```java
// Step 1: Fetch user
CompletableFuture<User> userFuture = fetchUser("123");

// Step 2: Fetch user's orders (needs user ID from step 1)
// How do we pass user ID from step 1 to step 2?
```

**❌ Wrong Way (Blocking):**
```java
User user = userFuture.get();  // BLOCKS - defeats purpose of async
List<Order> orders = fetchOrders(user.getId()).get();  // BLOCKS again
System.out.println(orders);

// Main thread blocked twice - not leveraging async!
```

**✅ Right Way (Non-Blocking Chaining):**

**Method 1: `thenApply()` - Transform the result**
```java
CompletableFuture<User> userFuture = fetchUser("123");

CompletableFuture<String> usernameFuture = userFuture
    .thenApply(user -> user.getName());  // Transform User -> String

String username = usernameFuture.get();
```

**Method 2: `thenCompose()` - Chain async operations**
```java
CompletableFuture<User> userFuture = fetchUser("123");

CompletableFuture<List<Order>> ordersFuture = userFuture
    .thenCompose(user -> fetchOrders(user.getId()));
    // Takes result of userFuture, returns new CompletableFuture

List<Order> orders = ordersFuture.get();  // No BLOCKING before this!
```

**Method 3: `thenCombine()` - Combine two futures**
```java
CompletableFuture<User> userFuture = fetchUser("123");
CompletableFuture<Profile> profileFuture = fetchProfile("123");

CompletableFuture<String> combined = userFuture
    .thenCombine(profileFuture, (user, profile) ->
        user.name + " - " + profile.bio
    );

String result = combined.get();
```

**Full Real-World Example:**
```java
// Fetch user → fetch orders → calculate total
CompletableFuture<User> userFuture = fetchUser("123");

CompletableFuture<Double> totalFuture = userFuture
    .thenCompose(user -> fetchOrders(user.getId()))  // Get orders
    .thenApply(orders -> orders.stream()
        .mapToDouble(Order::getAmount)
        .sum());  // Calculate total

System.out.println("Fetching...");  // No blocks so far
Double total = totalFuture.get();   // Block only here
System.out.println("Total: " + total);

// All processing chains as futures, main thread doesn't block until final .get()
```

**Interview Tip:**
"Chain async operations with `thenCompose()` (return CompletableFuture) or `thenApply()` (return value). Don't call `.get()` in the middle - it defeats the purpose. Build the chains first, then `.get()` at the end."

**Quick Checklist:**
- ✅ `thenApply(Function)` - transform value
- ✅ `thenCompose(Function)` - chain async operations
- ✅ `thenCombine(other, BiFunction)` - combine two futures
- ✅ Don't `.get()` in the middle - chain first!
- ✅ `.get()` only at the end when you actually need value

---

### Q12: How do you handle exceptions?

**Problem:** Exceptions in async operations.

**Methods:**

**1. `exceptionally()` - Recover from exception**
```java
CompletableFuture<String> future = fetchData()
    .thenApply(data -> data.toUpperCase())
    .exceptionally(ex -> {
        System.out.println("Error: " + ex.getMessage());
        return "DEFAULT_VALUE";  // Fallback
    });

String result = future.get();  // Gets either uppercase or DEFAULT_VALUE
```

**2. `handle()` - Handle both success and failure**
```java
CompletableFuture<String> future = fetchData()
    .handle((data, ex) -> {
        if (ex != null) {
            return "ERROR: " + ex.getMessage();
        } else {
            return "SUCCESS: " + data;
        }
    });

String result = future.get();
```

**3. `whenComplete()` - Run code regardless**
```java
CompletableFuture<String> future = fetchData()
    .whenComplete((result, ex) -> {
        if (ex != null) {
            System.out.println("Error occurred");
        } else {
            System.out.println("Success: " + result);
        }
    });

// No blocking unless needed
```

**Real-World Pattern:**
```java
public CompletableFuture<String> fetchWithRetry(String url, int maxRetries) {
    return fetchData(url)
        .exceptionally(ex -> {
            if (maxRetries > 0) {
                return fetchWithRetry(url, maxRetries - 1)
                    .join();  // Block here to retry
            } else {
                throw new RuntimeException("Max retries exceeded", ex);
            }
        });
}
```

**Interview Tip:**
"Use `exceptionally()` to recover with a default value. Use `handle()` for more complex error handling. Use `whenComplete()` for side effects like logging. Chain them appropriately in your async pipeline."

**Quick Checklist:**
- ✅ `exceptionally(Function)` - recover with default
- ✅ `handle(BiFunction)` - handle both success/failure
- ✅ `whenComplete(BiConsumer)` - side effects only
- ✅ Exceptions propagate down the chain
- ✅ Last handler wins if multiple

---

Done! Now let me create the SpringBoot Q&A guide:
<function_calls>
<invoke name="create_file">
<parameter name="content"># Spring Boot - Q&A Reference Guide

> **Format:** Each question → Problem → Why It Happens → Wrong vs Right Code → Interview Tip → Checklist

---

## 🌟 Spring Bean Scopes

### Q1: What are the main bean scopes in Spring?

**Problem:** Understanding how Spring creates and manages bean lifecycle.

**Five Main Scopes:**

**1. Singleton (default) - One instance per Spring container**
```java
@Component
public class UserService {  // Default scope = singleton
    // One instance, created once, reused everywhere
}

// Spring container
UserService service1 = context.getBean(UserService.class);
UserService service2 = context.getBean(UserService.class);

System.out.println(service1 == service2);  // true - SAME object!
```

**2. Prototype - New instance each time**
```java
@Component
@Scope(BeanScope.PROTOTYPE)
public class UserRequest {
    // New instance each time you request it
}

// Spring container
UserRequest req1 = context.getBean(UserRequest.class);
UserRequest req2 = context.getBean(UserRequest.class);

System.out.println(req1 == req2);  // false - DIFFERENT objects
```

**3. Request - New instance per HTTP request**
```java
@Component
@Scope("request")
public class RequestsContext {
    // New instance for each HTTP request
    // Lives only during that request (dies after response)
}

@RestController
public class PaymentController {
    @Autowired
    private RequestContext context;  // Different instance each request
    
    @PostMapping("/pay")
    public String pay() {
        // context is unique to this request
        return "paid";
    }
}
```

**4. Session - New instance per HTTP session**
```java
@Component
@Scope("session")
public class UserSession {
    private String userId;
    // One instance per logged-in user (stores session data)
}

@RestController
public class UserController {
    @Autowired
    private UserSession session;  // Same across multiple requests from same user
    
    @GetMapping("/profile")
    public String getProfile() {
        return session.getUserId();  // Same session data
    }
}
```

**5. Application - One instance for entire application**
```java
@Component
@Scope("application")
public class AppConfig {
    // One instance for entire application lifetime
    // Persists shutdown
}
```

**Comparison Table:**

| Scope | Instances | Lifetime | Use Case |
|-------|-----------|----------|----------|
| Singleton | 1 | Container startup → shutdown | Services, DAOs, config |
| Prototype | N per request | Created when needed | Stateful objects |
| Request | 1 per HTTP request | Request start → end | Request-scoped data |
| Session | 1 per user | Login → logout | User data, cart |
| Application | 1 | Startup → shutdown | Global config |

**Interview Tip:**
"Singleton is default - one instance for entire app lifecycle. Prototype creates new each time. Request/Session are web-specific - Request per HTTP request, Session per user. Application is like singleton but web-aware."

**Quick Checklist:**
- ✅ Singleton (default): 1 instance, reused
- ✅ Prototype: new instance each time
- ✅ Request: new per HTTP request
- ✅ Session: new per user session
- ✅ Application: 1 for entire app

---

### Q2: What happens when you inject a Prototype bean into a Singleton?

**Problem:** Understanding scope mismatch issues.

**❌ The Problem:**
```java
@Component
public class SingletonService {
    @Autowired
    private PrototypeRequest prototypeBean;
    
    public void process() {
        // Uses prototypeBean
    }
}

@Component
@Scope("prototype")
public class PrototypeRequest {
    private String requestId;
}

// What happens?
SingletonService singleton1 = context.getBean(SingletonService.class);
SingletonService singleton2 = context.getBean(SingletonService.class);

System.out.println(singleton1 == singleton2);  // true - same singleton

// But what about prototypeBean?
singleton1.process();  // Uses prototypeBean instance X
singleton2.process();  // Uses SAME prototypeBean instance X!

// PROBLEM: Expected new instance but got the same one!
```

**Why It Happens:**
- Singleton created ONCE → constructor runs once
- Dependency injection happens at construction
- Same prototypeBean instance injected and never updated
- Breaks the Prototype contract!

**❌ Wrong Way to Fix (Doesn't Work):**
```java
@Component
public class SingletonService {
    @Autowired
    private List<PrototypeRequest> prototypes;  // Get multiple instances
    
    public void process() {
        PrototypeRequest bean = prototypes.get(0);  // Still same instance!
    }
}
```

**✅ Solution 1: ObjectFactory (Best Practice)**
```java
@Component
public class SingletonService {
    @Autowired
    private ObjectFactory<PrototypeRequest> prototypeFactory;
    
    public void process() {
        PrototypeRequest newInstance = prototypeFactory.getObject();  // New instance!
        // Use newInstance
    }
}

// Usage
SingletonService singleton = context.getBean(SingletonService.class);
singleton.process();  // Gets new PrototypeRequest
singleton.process();  // Gets DIFFERENT PrototypeRequest
```

**✅ Solution 2: Provider (Alternative)**
```java
@Component
public class SingletonService {
    @Autowired
    private Provider<PrototypeRequest> prototypeProvider;
    
    public void process() {
        PrototypeRequest newInstance = prototypeProvider.get();  // New instance!
    }
}
```

**✅ Solution 3: Method Injection (Rare)**
```java
@Component
public class SingletonService {
    // Abstract method resolver
    public abstract PrototypeRequest createRequest();
    
    public void process() {
        PrototypeRequest newInstance = createRequest();
    }
}
```

**Real-World Example:**
```java
@Component
public class PaymentProcessor {
    @Autowired
    private ObjectFactory<PaymentRequest> requestFactory;
    
    public void processPayment(String orderId) {
        // Each payment gets fresh request object
        PaymentRequest request = requestFactory.getObject();
        request.setOrderId(orderId);
        // Process...
    }
}
```

**Interview Tip:**
"When injecting Prototype into Singleton, inject ObjectFactory<Prototype> instead. Call .getObject() each time to get new instance. This respects Prototype scope. Otherwise, Singleton keeps same instance forever."

**Quick Checklist:**
- ✅ Problem: Singleton + Prototype = scope mismatch
- ✅ Solution: Use ObjectFactory<Prototype>
- ✅ Call `.getObject()` each time for new instance
- ✅ Alternative: Use Provider<Prototype>
- ✅ Respect scope boundaries!

---

### Q3: Is a Singleton bean thread-safe?

**Problem:** Understanding thread-safety in singleton beans.

**Short Answer:** NOT automatically thread-safe.

**❌ Unsafe Singleton:**
```java
@Component
public class Counter {  // Singleton by default
    private int count = 0;  // Shared mutable state!
    
    public void increment() {
        count++;  // Race condition!
    }
    
    public int getCount() {
        return count;
    }
}

// Usage
@RestController
public class CounterController {
    @Autowired
    private Counter counter;
    
    @GetMapping("/increment")
    public int increment() {
        counter.increment();
        return counter.getCount();
    }
}

// Multiple HTTP requests from different threads
// Thread 1: increment() → count = ?, count = ?
// Thread 2:          increment() → count = ?
// Expected: 2, Actual: might be 1 (race condition!)
```

**Why It's Unsafe:**
- One singleton instance
- Multiple threads call methods simultaneously
- Shared mutable state (count variable)
- No synchronization → unpredictable results

**✅ Solution 1: Immutable Fields (Best)**
```java
@Component
public class ImmutableCounter {
    private final AtomicInteger count = new AtomicInteger(0);
    
    public void increment() {
        count.incrementAndGet();  // Thread-safe
    }
    
    public int getCount() {
        return count.get();  // Thread-safe
    }
}

// Or use immutable objects instead of mutable state
// Avoid shared mutable state altogether
```

**✅ Solution 2: Synchronized (Works but Slower)**
```java
@Component
public class SyncCounter {
    private int count = 0;
    
    public synchronized void increment() {  // Synchronized!
        count++;  // Thread-safe but slower
    }
    
    public synchronized int getCount() {
        return count;
    }
}
```

**✅ Solution 3: Volatile for Simple Cases**
```java
@Component
public class VolatileFlag {
    private volatile boolean active = false;  // Visibility guaranteed
    
    public void setActive(boolean val) {
        this.active = val;  // All threads see latest value
    }
    
    public boolean isActive() {
        return active;
    }
}

// Good for: flags, stops
// Bad for: count++, counters
```

**✅ Solution 4: ThreadLocal (One instance per thread)**
```java
@Component
public class ThreadLocalData {
    private ThreadLocal<String> data = ThreadLocal.withInitial(() -> "");
    
    public void setData(String val) {
        data.set(val);  // Each thread has own value
    }
    
    public String getData() {
        return data.get();  // Gets thread's own value
    }
}
```

**Best Practices:**

| Approach | Thread-Safe? | Performance | Use Case |
|----------|-------------|-------------|----------|
| Immutable fields | ✅ YES | ⚡ Fast | Read-only state |
| AtomicInteger | ✅ YES | ⚡ Fast | Counters |
| Synchronized | ✅ YES | 🐢 Slow | Complex logic |
| Volatile | ✅ YES (visibility) | ⚡ Fast | Flags only |
| ThreadLocal | ⚠️ Maybe | ⚡ Fast | Per-thread state |

**Real-World Pattern:**
```java
@Component
public class UserCache {  // Singleton
    private final ConcurrentHashMap<String, User> cache =
        new ConcurrentHashMap<>();  // Thread-safe collection!
    
    public void put(String id, User user) {
        cache.put(id, user);  // Thread-safe
    }
    
    public User get(String id) {
        return cache.get(id);  // Thread-safe
    }
}
```

**Interview Tip:**
"Spring singletons are NOT thread-safe by default. Use immutable fields, AtomicInteger, synchronized, or thread-safe collections (ConcurrentHashMap). Or avoid shared mutable state entirely."

**Quick Checklist:**
- ✅ Singleton NOT thread-safe by default
- ✅ Problem: shared mutable state
- ✅ Solution 1: Use AtomicInteger (best for counters)
- ✅ Solution 2: Use ConcurrentHashMap (for collections)
- ✅ Solution 3: Synchronized (simple but slow)
- ✅ Solution 4: Immutable objects (best overall)

---

### Q4: What's the difference between Singleton and Thread-local?

**Problem:** Understanding two different "one instance" concepts.

**Singleton: One instance per container**
```java
@Component
public class UserService {  // Singleton
    private String Name;
}

// Spring container has ONE UserService instance
UserService service1 = context.getBean(UserService.class);
UserService service2 = context.getBean(UserService.class);

System.out.println(service1 == service2);  // true - same object
```

**ThreadLocal: One instance per thread**
```java
public class ThreadLocalUserContext {
    private static ThreadLocal<User> userThreadLocal =
        ThreadLocal.withInitial(() -> null);
    
    public static void setUser(User user) {
        userThreadLocal.set(user);  // Thread A sets its own value
    }
    
    public static User getUser() {
        return userThreadLocal.get();  // Thread A gets its own value
    }
}

// Usage
Thread threadA = new Thread(() -> {
    ThreadLocalUserContext.setUser(new User("Alice"));
    System.out.println(ThreadLocalUserContext.getUser());  // Alice
});

Thread threadB = new Thread(() -> {
    ThreadLocalUserContext.setUser(new User("Bob"));
    System.out.println(ThreadLocalUserContext.getUser());  // Bob
});

threadA.start();
threadB.start();

// Each thread has its own value - no interference!
```

**Comparison:**

| Aspect | Singleton | ThreadLocal |
|--------|-----------|------------|
| Instances | 1 per container | 1 per thread |
| Shared? | Yes, all threads | No, each thread separate |
| Use Case | Stateless services | User context, request data |
| Thread-Safe? | No (need sync) | Yes (isolated) |
| Memory | Minimal | Higher (thread count × instances) |

**Singleton + Synchronization vs ThreadLocal:**
```java
// Singleton + Sync - Forces serialize (slow)
@Component
public class SyncUserService {
    private User currentUser;
    
    public synchronized void setUser(User user) {  // One thread at a time
        this.currentUser = user;
    }
}

// ThreadLocal - No serialization (fast)
@Component
public class ThreadLocalUserService {
    private ThreadLocal<User> userLocal = ThreadLocal.withInitial(() -> null);
    
    public void setUser(User user) {  // Each thread independent
        userLocal.set(user);
    }
}

// ThreadLocal is much faster for request-scoped data!
```

**Spring Request Scope (Uses ThreadLocal Internally):**
```java
@Component
@Scope("request")  // Spring uses ThreadLocal under the hood
public class RequestContext {
    private String requestId;
    
    // Spring automatically ensures one instance per request thread
}
```

**Interview Tip:**
"Singleton = one instance shared by all threads (needs synchronization). ThreadLocal = one instance per thread (no sync needed). For request-scoped data, Spring's request scope uses ThreadLocal internally and is safer."

**Quick Checklist:**
- ✅ Singleton: shared, needs sync for mutable state
- ✅ ThreadLocal: isolated per thread, no sync needed
- ✅ Spring Request scope = ThreadLocal under hood
- ✅ ThreadLocal uses more memory (thread × instances)
- ✅ ThreadLocal faster when many concurrent accesses

---

### Q5: How does Spring handle circular dependencies?

**Problem:** Understanding circular dependency detection and resolution.

**What Is It?**
```
A → B → A (direct cycle)
A → B → C → A (indirect cycle)
```

**❌ Circular Dependency Error:**
```java
@Component
public class UserService {
    @Autowired
    private OrderService orderService;  // Uses OrderService
}

@Component
public class OrderService {
    @Autowired
    private UserService userService;  // Uses UserService
    // CYCLE: UserService → OrderService → UserService
}

// Spring startup error:
// BeanCurrentlyInCreationException: 
// Error creating bean with name 'userService': 
// Requested bean is currently in creation: Is there an unresolvable circular reference?
```

**Why It Fails:**
- Spring tries to create UserService
- Needs OrderService (constructor/setter injection)
- Tries to create OrderService
- Needs UserService (but it's still being created!)
- Circular wait → ERROR

**Dependency Detection:**
```
Init UserService
├─ Need OrderService
│  └─ Init OrderService
│     └─ Need UserService
│        └─ ERROR: UserService already in progress
└─ (never completes)
```

**✅ Solution 1: Setter Injection**
```java
@Component
public class UserService {
    private OrderService orderService;
    
    @Autowired
    public void setOrderService(OrderService orderService) {
        this.orderService = orderService;  // Setter, not constructor
    }
}

@Component
public class OrderService {
    private UserService userService;
    
    @Autowired
    public void setUserService(UserService userService) {
        this.userService = userService;  // Setter, not constructor
    }
}

// Spring can create both partially, then inject dependencies via setters
// No circular problem!
```

**How It Works:**
```
Create UserService (without dependencies)
├─ Create OrderService (without dependencies)
├─ Inject OrderService into UserService
└─ Inject UserService into OrderService
// Both created successfully!
```

**✅ Solution 2: @Lazy**
```java
@Component
public class UserService {
    @Autowired
    @Lazy  // Don't inject immediately, wait until first use
    private OrderService orderService;
}

@Component
public class OrderService {
    @Autowired
    private UserService userService;
}

// Spring can create both (OrderService lazy-initialized later)
```

**✅ Solution 3: ObjectFactory**
```java
@Component
public class UserService {
    @Autowired
    private ObjectFactory<OrderService> orderServiceFactory;
    
    public void process() {
        OrderService orderService = orderServiceFactory.getObject();  // Get on demand
    }
}

@Component
public class OrderService {
    @Autowired
    private UserService userService;
}

// UserService doesn't depend on OrderService immediately
```

**✅ Solution 4: Refactor Architecture (Best Long-term)**
```java
// Problem: UserService <-> OrderService

// Solution: Introduce intermediary
@Component
public class PaymentService {
    // Coordinates both without circular dependency
}

@Component
public class UserService {
    @Autowired
    private PaymentService paymentService;  // Not OrderService
}

@Component
public class OrderService {
    @Autowired
    private PaymentService paymentService;  // Not UserService
}

// No circular dependency!
```

**Interview Tip:**
"Spring detects circular dependencies at startup and throws an error. Fix it with setter injection (not constructor), @Lazy, ObjectFactory, or refactor the architecture. Setter injection is the quick fix - Spring can partially create beans and inject via setters later."

**Quick Checklist:**
- ✅ Circular dependency = detected at startup
- ✅ BeanCurrentlyInCreationException error
- ✅ Solution 1: Setter injection (quick fix)
- ✅ Solution 2: @Lazy (if one depends on the other)
- ✅ Solution 3: ObjectFactory (explicit control)
- ✅ Solution 4: Refactor (best long-term)

---

## 📊 Quick Interview Cheat Sheet

**Top Spring Bean Questions:**

1. **What scopes exist?** → Singleton, Prototype, Request, Session, Application
2. **Singleton thread-safe?** → NO! Use AtomicInteger or synced
3. **Prototype in Singleton?** → Use ObjectFactory<Prototype>
4. **Circular dependency fix?** → Use setter injection or @Lazy
5. **Request scope lifetime?** → One per HTTP request, dies after response
6. **Session scope lifetime?** → One per logged-in user, lives until logout

---

**Last Updated:** February 2026

