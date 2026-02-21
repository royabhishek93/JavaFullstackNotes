# Interface Default and Static Methods - Complete Guide

## 🎯 Quick Context
**Before Java 8:** Interfaces could ONLY have abstract methods. Everything changed in Java 8 when default and static methods were added. This is a **senior-level must-know** because it explains interface design decisions and backward compatibility.

---

## 🔥 MUST KNOW: The Real Problem (Before Java 8)

### Scenario: You Have 500 Classes Implementing an Interface

```java
// A widely used interface (used by 500+ classes across the codebase)
public interface PaymentProcessor {
    void processPayment(double amount);
    void refund(double amount);
}

// Implemented by:
public class StripePayment implements PaymentProcessor {
    @Override
    public void processPayment(double amount) { /* ... */ }
    
    @Override
    public void refund(double amount) { /* ... */ }
}

public class PayPalPayment implements PaymentProcessor {
    @Override
    public void processPayment(double amount) { /* ... */ }
    
    @Override
    public void refund(double amount) { /* ... */ }
}
```

### The Problem: New Requirement Arrives
Your manager says: "We need to add a new feature - `validatePaymentMethod()` to all payments."

❌ **WITHOUT default methods (Before Java 8):**
```java
// You MUST add this as abstract method
public interface PaymentProcessor {
    void processPayment(double amount);
    void refund(double amount);
    void validatePaymentMethod(); // NEW - ALL 500+ classes MUST implement this!
}

// Now EVERY implementing class breaks! Compiler error everywhere!
public class StripePayment implements PaymentProcessor {
    @Override
    public void processPayment(double amount) { /* ... */ }
    
    @Override
    public void refund(double amount) { /* ... */ }
    
    // FORCED to add this - even if we don't need it!
    @Override
    public void validatePaymentMethod() { 
        System.out.println("Validating..."); 
    }
}

// 500+ classes to update = massive refactor = production risk!
```

---

## ✅ THE SOLUTION: Default Methods (Java 8+)

Default methods allow you to **provide implementation in the interface** itself.

### ✅ RIGHT Way: Using Default Method

```java
public interface PaymentProcessor {
    void processPayment(double amount);
    void refund(double amount);
    
    // Default method - has implementation!
    default void validatePaymentMethod() {
        System.out.println("Validation: Payment method is active");
    }
}

// Existing implementations? No changes needed!
public class StripePayment implements PaymentProcessor {
    @Override
    public void processPayment(double amount) { 
        System.out.println("Processing $" + amount + " via Stripe"); 
    }
    
    @Override
    public void refund(double amount) { 
        System.out.println("Refunding $" + amount); 
    }
    
    // We inherit validatePaymentMethod() automatically!
    // No need to override unless we want custom behavior
}

// Usage
PaymentProcessor processor = new StripePayment();
processor.processPayment(100);      // Works
processor.validatePaymentMethod();  // Uses default from interface!
```

### Output
```
Processing $100.00 via Stripe
Validation: Payment method is active
```

---

## 📋 When to OVERRIDE Default Methods

Some implementations might need custom behavior:

```java
public class CryptoPayment implements PaymentProcessor {
    @Override
    public void processPayment(double amount) { 
        System.out.println("Processing " + amount + " Bitcoin"); 
    }
    
    @Override
    public void refund(double amount) { 
        System.out.println("Crypto refund initiated"); 
    }
    
    // Override default method with custom logic
    @Override
    default void validatePaymentMethod() {
        // Crypto needs special validation
        System.out.println("Validating wallet address and balance...");
        System.out.println("Checking blockchain...");
    }
}

CryptoPayment crypto = new CryptoPayment();
crypto.validatePaymentMethod(); 
// Output: Validating wallet address and balance...
//         Checking blockchain...
```

---

## ⚙️ Static Methods in Interfaces

Static methods are **utility methods** that belong to the interface itself, not instances.

### Real-World Scenario: Factory Patterns

```java
public interface PaymentProcessor {
    void processPayment(double amount);
    void refund(double amount);
    
    default void validatePaymentMethod() {
        System.out.println("Standard validation");
    }
    
    // Static method - utility function
    static PaymentProcessor createProcessor(String type) {
        switch(type.toLowerCase()) {
            case "stripe":
                return new StripePayment();
            case "paypal":
                return new PayPalPayment();
            case "crypto":
                return new CryptoPayment();
            default:
                throw new IllegalArgumentException("Unknown processor: " + type);
        }
    }
}

// Usage
PaymentProcessor processor = PaymentProcessor.createProcessor("stripe");
processor.processPayment(150);
```

### Key Point: Static Methods Don't Override

```java
public class StripePayment implements PaymentProcessor {
    // ❌ WRONG - You cannot override static methods!
    @Override
    static PaymentProcessor createProcessor(String type) {
        // Compilation error!
    }
    
    // ✅ CORRECT - Static methods belong to the interface only
}

// Called on interface, not implementation
PaymentProcessor p = PaymentProcessor.createProcessor("stripe");

// NOT on StripePayment class
// StripePayment.createProcessor("stripe"); ← Works but confusing
```

---

## 🔍 Default Methods vs Abstract Methods: Side-by-Side Comparison

| Feature | Abstract Method | Default Method |
|---------|-----------------|-----------------|
| **Has implementation?** | ❌ No | ✅ Yes |
| **All classes must implement?** | ✅ Yes (forced) | ❌ No (optional override) |
| **Use case** | Core contract | Optional utility |
| **Backward compatibility** | ❌ Breaks existing code | ✅ Preserves compatibility |
| **Example** | `void process();` | `default void log() {}` |

---

## 🎬 Real Interview Question 1: Multiple Inheritance Problem

**Q: What happens when a class implements TWO interfaces with the SAME default method?**

```java
public interface ClientLogger {
    default void log(String msg) {
        System.out.println("CLIENT LOG: " + msg);
    }
}

public interface ServerLogger {
    default void log(String msg) {
        System.out.println("SERVER LOG: " + msg);
    }
}

// ❌ PROBLEM: Which log() method to use?
public class PaymentService implements ClientLogger, ServerLogger {
    // Compiler error: "Duplicate default methods!"
}
```

**Answer (A):** You MUST resolve the conflict by overriding:

```java
✅ SOLUTION 1: Provide your own implementation
public class PaymentService implements ClientLogger, ServerLogger {
    @Override
    public void log(String msg) {
        System.out.println("PAYMENT LOG: " + msg);
    }
}

✅ SOLUTION 2: Delegate to one interface
public class PaymentService implements ClientLogger, ServerLogger {
    @Override
    public void log(String msg) {
        ClientLogger.super.log(msg); // Use ClientLogger's version
    }
}
```

---

## 🎬 Real Interview Question 2: Why Not Just Use Abstract Classes?

**Q: Interfaces have default methods now... so why use interfaces instead of abstract classes?**

**Answer (A):** Great question! Interfaces are still better because of **multiple inheritance**:

```java
// ✅ A class can implement MULTIPLE interfaces
public interface Payable {
    default void pay() { System.out.println("Paying..."); }
}

public interface Trackable {
    default void track() { System.out.println("Tracking..."); }
}

public interface Loggable {
    default void log() { System.out.println("Logging..."); }
}

// One class, THREE behaviors!
public class PaymentTransaction implements Payable, Trackable, Loggable {
    // Inherits pay(), track(), log() from all three interfaces
}

// ❌ But with abstract classes - you can only extend ONE:
public abstract class PaymentBase { /* ... */ }
public abstract class TrackerBase { /* ... */ }

// Cannot extend both! Limited to single inheritance
public class PaymentTransaction extends PaymentBase, TrackerBase { // ❌ ERROR
}
```

---

## 🎬 Real Interview Question 3: Evolution of Collections API

**Q: Why was Java Collections API updated so much in Java 8+?**

```java
// ❌ BEFORE Java 8 - If they wanted to add forEach(), they would break everything:
public interface Iterable<T> {
    Iterator<T> iterator();
    void forEach(Consumer<? super T> action); // ❌ All 500+ implementations break!
}

// ✅ JAVA 8+ - Used default method instead:
public interface Iterable<T> {
    Iterator<T> iterator();
    
    default void forEach(Consumer<? super T> action) {
        for (T t : this) {
            action.accept(t);
        }
    }
}

// No breaking changes! Existing code still works.
List<String> names = new ArrayList<>();
names.add("Alice");
names.add("Bob");

// Works because forEach is default!
names.forEach(System.out::println);
```

---

## 📊 Quick Checklist: When to Use What?

### ✅ Use Default Method When:
- Adding optional behavior to existing interface
- Providing convenience methods (like `forEach()`)
- Ensuring backward compatibility
- Utility methods that all implementations might need

```java
public interface Database {
    void connect();
    void disconnect();
    
    // Default method - nice to have, not essential
    default void reconnect() {
        disconnect();
        connect();
    }
}
```

### ✅ Use Static Method When:
- Creating factory methods (like `Collections.emptyList()`)
- Utility functions related to the interface
- NOT instance-specific logic

```java
public interface PaymentProcessor {
    void processPayment(double amount);
    
    // Factory - static makes sense
    static PaymentProcessor forCountry(String country) {
        // Returns appropriate processor
    }
}
```

### ✅ Use Abstract Method When:
- Method is CORE to the interface contract
- Every implementation MUST provide it
- No meaningful default behavior

```java
public interface PaymentProcessor {
    // This is core - every processor MUST implement
    void processPayment(double amount);
}
```

---

## 🎯 Interview Tips - What to Say

### Tip 1: Lead with the Problem
**❌ Wrong approach:**
"Default methods were added in Java 8..."

**✅ Right approach:**
"Before Java 8, adding a method to an interface meant updating ALL 500+ implementations. This was a maintenance nightmare. Default methods solved this by letting interfaces provide default implementation."

### Tip 2: Show Real-World Impact
"The Collections API is the perfect example. In Java 8, they added `forEach()` to `Iterable` as a default method. If they'd made it abstract, every single collection class would break. Default methods preserved backward compatibility."

### Tip 3: Explain the Trade-offs
"Default methods are powerful but come with complexity - you need to handle conflicts when implementing multiple interfaces. Use them for optional features, not core contract requirements."

### Tip 4: Mention Static Methods
"Static methods in interfaces are for utilities. `Collections.emptyList()` is a perfect example - it's helper logic that doesn't need an instance."

---

## 🔥 Most Important Insight

**The real purpose of default and static methods: INTERFACE EVOLUTION WITHOUT BREAKING CHANGES**

Before Java 8, interfaces were fragile - change = breaking change = refactor everything.

After Java 8, interfaces are flexible - add optional behavior without touching existing code.

This is why Google Guava library could smoothly integrate with Java 8. This is why legacy code still works with modern Java versions.

---

## 📝 Code Reference: Complete Example

```java
public interface PaymentProcessor {
    // Core contract - must implement
    void processPayment(double amount);
    void refund(double amount);
    
    // Optional behavior - default implementation provided
    default void validatePaymentMethod() {
        System.out.println("Standard validation");
    }
    
    default void logTransaction(double amount, String type) {
        System.out.println("[" + this.getClass().getSimpleName() + "] " 
            + type + ": " + amount);
    }
    
    // Utility method - belongs to interface, not instances
    static PaymentProcessor createProcessor(String type) {
        if (type.equals("stripe")) return new StripePayment();
        if (type.equals("paypal")) return new PayPalPayment();
        throw new IllegalArgumentException("Unknown: " + type);
    }
}

public class StripePayment implements PaymentProcessor {
    @Override
    public void processPayment(double amount) {
        System.out.println("Stripe: Processing $" + amount);
        logTransaction(amount, "PROCESS");
    }
    
    @Override
    public void refund(double amount) {
        System.out.println("Stripe: Refunding $" + amount);
        logTransaction(amount, "REFUND");
    }
}

public class Demo {
    public static void main(String[] args) {
        // Using factory static method
        PaymentProcessor processor = PaymentProcessor.createProcessor("stripe");
        
        // Using abstract methods
        processor.processPayment(100);
        processor.refund(50);
        
        // Using default methods
        processor.validatePaymentMethod();
    }
}
```

**Output:**
```
Stripe: Processing $100
[StripePayment] PROCESS: 100.0
Stripe: Refunding $50
[StripePayment] REFUND: 50.0
Standard validation
```

---

## 🚨 Critical Pitfalls & Advanced Topics (Interview Gold!)
### Ranked by Interview Importance ⭐⭐⭐

---

### 🔥 Pitfall 1: Java 9+ Private Methods in Interfaces (⭐⭐⭐ MOST IMPORTANT)

**Why this matters for 2026 interviews:** This is the differentiator between senior and mid-level developers. Most people don't know this exists!

**Not mentioned in most guides, but CRITICAL for senior interviews!**

```java
public interface PaymentProcessor {
    void processPayment(double amount);
    void refund(double amount);
    
    // Default methods with shared logic
    default void logTransaction(String action, double amount) {
        validateTransaction(action, amount);
        System.out.println(action + ": " + amount);
    }
    
    default void refund(double amount) {
        validateTransaction("REFUND", amount);
        System.out.println("Refunding: " + amount);
    }
    
    // ❌ PROBLEM: logTransaction validates, refund validates
    // Code duplication in default methods!
    
    // ✅ JAVA 9+ SOLUTION: Private methods!
    private void validateTransaction(String action, double amount) {
        if (amount <= 0) {
            throw new IllegalArgumentException("Amount must be positive");
        }
        System.out.println("Validating " + action);
    }
}

public class StripePayment implements PaymentProcessor {
    @Override
    public void processPayment(double amount) {
        // Can't call validateTransaction - it's private to interface!
        // This is intentional - private methods are for interface internal use only
    }
    
    @Override
    public void refund(double amount) {
        System.out.println("Refunding via Stripe");
    }
}
```

**Why Private Methods Matter:**
- Share common logic between default methods without duplication
- Hide implementation details from implementations (encapsulation!)
- Cleaner, more maintainable interface code
- Only available in Java 9+
- Separates "interface contract" from "interface internals"

**Interview Tip:** "Private methods let interfaces share internal logic without exposing it to implementations. Think of them as private utility methods, but for the interface itself. This keeps interfaces DRY and maintainable."

**What to say:** "In Java 9+, we use private methods in interfaces to avoid code duplication in default methods. It's clean encapsulation - implementations don't need to know about internal validation logic."

---

### 🔥 Pitfall 2: The Version Compatibility Trap (⭐⭐⭐ CRITICAL)

**Why this matters:** This is a real production problem that senior developers face. Shows you understand versioning, SemVer, and library design.

**Real scenario from production:**

```java
// Your library interface (version 1.0)
public interface Logger {
    void log(String message);
}

// Client code (someone using your library)
public class MyApp implements Logger {
    @Override
    public void log(String message) {
        System.out.println("APP: " + message);
    }
}

// -----------------------------------
// You release version 2.0 with new features
// -----------------------------------

// Your updated interface (version 2.0)
public interface Logger {
    void log(String message);
    
    // NEW default method added!
    default void logWithLevel(String level, String message) {
        log("[" + level + "] " + message);
    }
}

// ✅ CLIENT CODE STILL WORKS! (Binary compatibility)
// MyApp gets logWithLevel() for free
Logger logger = new MyApp();
logger.logWithLevel("ERROR", "Something broke");
```

But there's a trap:

```java
// ❌ DANGEROUS: If default method has side effects...

public interface Logger {
    void log(String message);
    
    default void logWithLevel(String level, String message) {
        log("[" + level + "] " + message);
        MetricsCollector.increment("logs"); // SIDE EFFECT!
    }
}

// Old MyApp from version 1.0 compiles fine
// But suddenly metrics are being incremented every time
// logWithLevel() is called - OLD CODE NOW HAS NEW BEHAVIOR!
// This is called "semantic versioning violation"
```

**Safe versioning pattern:**

```java
// ✅ Version 2.1 - Multiple default method approach
public interface Logger {
    void log(String message);
    
    // Adding entirely new default method - safe, doesn't change existing behavior
    default void logWithLevel(String level, String message) {
        log("[" + level + "] " + message);
        // No side effects, just delegates to contract method
    }
    
    // Existing default methods unchanged - safe!
}

// Rule: Default methods can be ADDED, but changed defaults break contracts
```

**Interview Tip:** "Default methods are binary compatible but can introduce unexpected behavioral changes. When evolving interfaces, document version changes. Add new defaults safely, but changing existing behavior violates the interface contract."

**What to say:** "This is why libraries like Java Collections, Spring, and AWS SDKs were careful with default methods in Java 8. Adding a default method is backward compatible at compile-time, but if it has side effects or changes behavior, you've broken the semantic contract. Always document it."

---

### 🔥 Pitfall 3: Silent Breaking of Contract (⭐⭐⭐ IMPORTANT)

**Why this matters:** Shows deep understanding of interface semantics and testing implications. Production-relevant.

**The Danger:** Default methods can hide bugs because implementing classes don't update them!

```java
public interface DataService {
    List<User> getUsers();
    
    // Added later as default method
    default int getUserCount() {
        return getUsers().size(); // Seems reasonable...
    }
}

public class CachedDataService implements DataService {
    private List<User> cachedUsers;
    
    @Override
    public List<User> getUsers() {
        // Returns from cache - might be stale!
        return new ArrayList<>(cachedUsers);
    }
    
    // getUserCount() inherited and uses getUsers()
    // But NEVER uses the cache-refresh logic!
    // Default method doesn't know about caching strategy!
}

// Bug: getUserCount() returns stale count!
DataService service = new CachedDataService();
int count = service.getUserCount(); // Uses stale cache!
```

**✅ Safe Pattern:**

```java
public interface DataService {
    List<User> getUsers();
    
    default int getUserCount() {
        return getUsers().size(); // Uses interface contract
    }
}

// If caching strategy changes getUsers() behavior, default method updates too!
public class CachedDataService implements DataService {
    private List<User> cachedUsers;
    private long cacheExpiry;
    
    @Override
    public List<User> getUsers() {
        if (isCacheStale()) {
            refreshCache();
        }
        return new ArrayList<>(cachedUsers);
    }
    
    // getUserCount() now gets fresh count because getUsers() refreshes!
    // This is safe architecture!
}
```

**Interview Tip:** "Default methods should only depend on abstract methods, never on implementation details. This creates a stable interface contract. When an implementation changes its behavior through abstract methods, all default methods automatically adapt."

**What to say:** "The issue is that default methods don't know about implementation-specific optimizations. If you override one contract method, you need to override related default methods too. Or better - design defaults to only call abstract methods."

---

### 🟡 Pitfall 4: Static Methods Don't Benefit from Polymorphism (⭐⭐ IMPORTANT)

**Why this matters:** Clarifies a fundamental limitation that affects design.

```java
public interface PaymentProcessor {
    static PaymentProcessor create(String type) {
        if (type.equals("stripe")) return new StripePayment();
        if (type.equals("paypal")) return new PayPalPayment();
        throw new IllegalArgumentException("Unknown: " + type);
    }
}

public class StripePayment implements PaymentProcessor {
    // ❌ You might think you can override create()
    // But static methods CAN'T be overridden!
    
    static PaymentProcessor create(String type) {
        // This just HIDES the interface's static method (shadowing)
        // It's not overriding!
        return new StripePayment("default");
    }
}

// Usage confusion:
PaymentProcessor p = PaymentProcessor.create("stripe");
// Uses PaymentProcessor.create(), NOT StripePayment.create()

StripePayment sp = StripePayment.create("stripe");
// Uses StripePayment.create() - different method!
```

**This is why static methods should only be utility functions:**

```java
public interface PaymentProcessor {
    void processPayment(double amount);
    
    // ✅ Good use of static: Utility/factory
    static PaymentProcessor create(String type) {
        return switch(type) {
            case "stripe" -> new StripePayment();
            case "paypal" -> new PayPalPayment();
            default -> throw new IllegalArgumentException("Unknown: " + type);
        };
    }
    
    // Static helpers for validation
    static void validateAmount(double amount) {
        if (amount <= 0) {
            throw new IllegalArgumentException("Amount must be positive");
        }
    }
}
```

**Interview Tip:** "Static methods in interfaces aren't polymorphic - they can't be overridden. Use them only for factories and utilities. For dynamic behavior, use default or abstract methods. Also notice modern Java uses `switch` expressions (Java 14+) for cleaner factories."

---

### 🟡 Pitfall 5: Default Methods Can't Access Instance Fields (⭐⭐ FUNDAMENTAL)

**Why this matters:** Basic constraint but important for interface design.

**Q: What's wrong with this code?**

```java
public interface PaymentProcessor {
    // Instance method - cannot access fields!
    default String getPaymentId() {
        return this.paymentId; // ❌ ERROR! Interface doesn't know about paymentId
    }
}

public class StripePayment implements PaymentProcessor {
    private String paymentId; // Only this class knows about this field
}
```

**Why it fails:** Default methods live in the interface, which doesn't know about implementation-specific fields.

**✅ Solution: Force implementations to provide the data**

```java
public interface PaymentProcessor {
    void processPayment(double amount);
    String getPaymentId(); // ← Abstract method, forces implementation
    
    // Default method can now call the abstract method!
    default void logPayment() {
        System.out.println("Payment: " + getPaymentId());
    }
}

public class StripePayment implements PaymentProcessor {
    private String paymentId;
    
    @Override
    public String getPaymentId() {
        return paymentId; // Implementation knows how to get this
    }
    
    // logPayment() inherited and works!
}
```

**Interview Tip:** "Default methods can't directly access instance state. Think of them as utility methods that call abstract methods to get data. This enforces the Dependency Inversion Principle - utilities depend on abstractions, not concrete state."

---

### 🟢 Pitfall 6: Functional Interfaces Don't Get Default Methods (Usually) (⭐ NICE TO KNOW)

**Why this matters:** Design guidance for clean interfaces.

```java
// ❌ WRONG: Mixing Functional Interface with default method
@FunctionalInterface
public interface Processor {
    void process(String input); // Required abstract method
    
    default void log(String msg) { // Default method is allowed, but...
        System.out.println(msg);
    }
}

// This breaks the Functional Interface contract slightly!
// Functional interfaces should have ONE abstract method
// Adding default methods makes them confusing

// Using as lambda STILL works (lambdas only implement abstract methods)
Processor p = input -> System.out.println("Processing: " + input);
p.process("data");      // ✅ Works
p.log("test");          // ✅ Also works (inherited default)

// But it's CONFUSING because Functional Interfaces should be simple!
```

**✅ Better pattern:**

```java
@FunctionalInterface
public interface Processor {
    void process(String input); // One clear purpose
}

// Separate utility class for helpers
public class Processors {
    public static void processWithLogging(Processor p, String input) {
        System.out.println("Processing: " + input);
        p.process(input);
    }
}
```

**Interview Tip:** "Don't add default methods to functional interfaces. They're designed for lambdas - keep them simple. If you need utilities, create a companion class."

---

### 🟢 Pitfall 7: Debugging Becomes Harder with Default Methods (⭐ USEFUL TIP)

**Why this matters:** Practical development concern.

**In the Debugger:**

```java
public interface DataService {
    List<User> getUsers();
    
    default int getUserCount() {
        return getUsers().size();
    }
}

// Which implementation's method are you in?
public class ElasticsearchService implements DataService { 
    @Override public List<User> getUsers() { /* network call */ }
}

public class DatabaseService implements DataService { 
    @Override public List<User> getUsers() { /* SQL query */ }
}

// When you step into getUserCount(), it's not in implementations
// It's in the INTERFACE - confusing for debugging!
// To debug getUsers(), you have to step in again
```

**Good Debugging Practice:**

```java
// If default method complexity > 3 lines, better to be explicit:
public interface DataService {
    List<User> getUsers();
    
    // ✅ Simple one-liner - keep as default
    default int getUserCount() {
        return getUsers().size();
    }
    
    // ❌ Complex logic - make it abstract, let implementations decide
    // (if logic varies per implementation)
    void printUserReport();
}
```

**Guideline:** "Keep default methods simple (under 3 lines). Complex logic should be in implementations, not the interface."

---

## 📋 Interview Question: "What's Wrong With This?"

```java
public interface PaymentProcessor {
    void pay(double amount);
    
    default void refund(double amount) {
        // What happens if pay() is never implemented properly?
        // What if subclass pay() doesn't actually charge the card?
        // This refund() might refund a non-existent payment!
    }
}

public class BuggyPayment implements PaymentProcessor {
    @Override
    public void pay(double amount) {
        System.out.println("Pretending to charge..."); // BUG!
        // Never actually charges anything
    }
}

// Usage
PaymentProcessor p = new BuggyPayment();
p.pay(100);        // Does nothing
p.refund(100);     // Tries to refund non-existent charge!
```

**Answer:** "Default methods assume implementations honor the contract. If an implementation breaks the contract, default methods can cause logical errors. This is why you need integration tests, not just unit tests of the interface."

---

## ✨ Key Takeaway for Interviews

Senior developers know that **default and static methods solved the interface evolution problem** BUT also know their pitfalls:

**What to emphasize:**
1. **Design clarity** - Default methods should serve utility, not hide complexity
2. **Contract honesty** - Implementations must honor the interface contract
3. **Testing burden** - Default methods shift responsibility to integrate/acceptance tests
4. **Refactoring risk** - Adding defaults to existing interfaces can have unexpected side effects
5. **Java 9+ private methods** - Cleaner way to share interface logic

**For 2026 senior interviews, mention:**
- Collections API evolution (still relevant)
- Backward compatibility challenges (architecture thinking)
- Private interface methods for cleaner code (Java 9+)
- Why you still need abstract methods for core contracts
- How default methods revealed the need for better testing strategies

This shows you're not just implementing features - you're thinking about **maintainability, versioning, and production impact**.
