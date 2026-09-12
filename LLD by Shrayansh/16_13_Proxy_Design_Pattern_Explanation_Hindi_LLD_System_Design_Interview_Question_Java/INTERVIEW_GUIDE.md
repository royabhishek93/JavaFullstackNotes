# 🛡️ Proxy Design Pattern - Interview Guide
## _15 YOE Architect-Level Conversational Script_

**📗 Difficulty: Beginner** — ideal starting point for a new developer; read this before tackling applied system-design questions.

---

## 📋 Table of Contents
1. Architecture & Core Concept
2. Code Example
3. API Design (Proxy Service)
4. Sequence Diagrams
5. Scenario-First Explanations
6. Cross Questions
7. Trade-offs
8. Senior Trap Questions
9. Technology Choices

---

**Interviewer**: "Explain the Proxy Design Pattern with a real-world example."

**You**: "Proxy Pattern provides a **surrogate/placeholder for another object to control access to it**. Three common use cases: **Lazy initialization** (Virtual Proxy), **Access control** (Protection Proxy), and **Remote object access** (Remote Proxy)."

---

## 1. Architecture Diagram

```
Client ──▶ Subject (interface) ◄── implements ── RealSubject (expensive object)
                    ▲
                    │ implements
                    │
              ProxyObject
              - holds reference to RealSubject
              - controls access (lazy load, auth check, logging)
```

---

## 2. Code Example - Virtual Proxy (Lazy Loading)

```java
interface Image {
    void display();
}

class RealImage implements Image {
    private String filename;
    
    RealImage(String filename) {
        this.filename = filename;
        loadFromDisk();  // Expensive operation!
    }
    
    private void loadFromDisk() {
        System.out.println("Loading " + filename + " from disk (slow, 2 sec)...");
    }
    
    public void display() {
        System.out.println("Displaying " + filename);
    }
}

class ProxyImage implements Image {
    private String filename;
    private RealImage realImage;  // Lazily initialized!
    
    ProxyImage(String filename) {
        this.filename = filename;
        // NOTE: Does NOT load image yet!
    }
    
    public void display() {
        if (realImage == null) {
            realImage = new RealImage(filename);  // Load only when actually needed
        }
        realImage.display();
    }
}

// Usage:
Image image = new ProxyImage("large_photo.jpg");  // Instant, no loading yet
// ... later, only if user actually views the image:
image.display();  // NOW it loads from disk
```

## 2.1 Protection Proxy (Access Control)

```java
interface BankAccount {
    void withdraw(double amount);
}

class RealBankAccount implements BankAccount {
    public void withdraw(double amount) {
        System.out.println("Withdrew " + amount);
    }
}

class ProtectedBankAccountProxy implements BankAccount {
    private RealBankAccount realAccount;
    private User currentUser;
    
    public void withdraw(double amount) {
        if (!currentUser.hasRole("ACCOUNT_OWNER")) {
            throw new SecurityException("Access denied");
        }
        if (amount > currentUser.getDailyLimit()) {
            throw new SecurityException("Exceeds daily withdrawal limit");
        }
        realAccount.withdraw(amount);  // Delegate to real object only after checks pass
    }
}
```

---

## 3. Scenario-First Explanations

### **Why Proxy Instead of Modifying RealSubject Directly?**

**You**: "Open/Closed Principle - `RealImage` and `RealBankAccount` remain UNCHANGED. All the lazy-loading or access-control logic lives in the Proxy wrapper. This also means you can COMPOSE proxies - a `LoggingProxy` wrapping a `CachingProxy` wrapping a `ProtectionProxy` wrapping the `RealSubject` - each adds one concern (very similar to middleware chains in web frameworks)."

---

## 4. Cross Questions

**Interviewer**: "How is Proxy different from Decorator Pattern? They look structurally identical!"

**You**: "Great question - structurally, YES, both wrap an object implementing the same interface. The difference is **INTENT**:
- **Proxy**: Controls ACCESS to the object (lazy load, security, remote access) - same core behavior, just gated
- **Decorator**: ADDS NEW BEHAVIOR/responsibilities to the object (e.g., adding scrollbars to a window, adding compression to a stream)

A Proxy typically manages the underlying object's LIFECYCLE (creates it, controls access). A Decorator assumes the object already exists and just enhances it. In practice, code can look identical - the pattern name signals INTENT to other developers reading your code."

---

## 5. Trade-offs

| Aspect | Proxy Pattern | Direct Object Access |
|--------|-----------------|--------------------------|
| **Performance** | Extra indirection layer | Direct, faster |
| **Flexibility** | Easy to add cross-cutting concerns | Must modify original class |
| **Use Case** | Remote objects, expensive objects, access control | Simple, no special needs |

---

## 6. Senior Trap Questions

### **Trap: "Just use lazy initialization directly in RealImage's constructor with a flag!"**

**✅ Senior**: "You could add an `isLoaded` boolean flag inside `RealImage` itself, but that VIOLATES Single Responsibility Principle - `RealImage` would handle BOTH image display logic AND lazy-loading logic. Proxy Pattern cleanly SEPARATES these concerns: `RealImage` only knows how to load/display, `ProxyImage` only knows WHEN to trigger that. This separation also enables REUSE - the same `ProxyImage` pattern can wrap any `Image` implementation, and you can stack multiple proxies (caching + lazy-load + logging) without touching `RealImage` at all."

---

## 7. Technology Choices

**You**: "**Spring AOP** and **Hibernate's lazy-loaded entities** are real-world Proxy Pattern implementations - Hibernate generates a CGLIB proxy for `@OneToMany` lazy associations, deferring the actual DB query until you access the collection. This is EXACTLY the Virtual Proxy pattern shown above, auto-generated by the framework."

---

## 🔥 Real-World Production Issue: The Hibernate Lazy-Proxy `LazyInitializationException` Outage

*In plain English: using a lazy-loaded object outside the exact window in which it's allowed to load throws a confusing runtime error.*

**The war story:**

"A REST API returned a JPA entity with a `@OneToMany` lazy-loaded collection directly as the JSON response body. It worked perfectly in every manual test — because in dev/QA, the collection was always accessed (and thus lazily loaded) INSIDE the same transaction/Hibernate session as the DB fetch."

```
@GetMapping("/orders/{id}")
Order getOrder(@PathVariable Long id) {
    return orderRepo.findById(id);   // returns entity with LAZY proxy for order.items
}                                      // <- Hibernate session CLOSES when this method returns

Jackson (JSON serializer) tries to access order.getItems() to serialize it
  -> triggers the lazy proxy's real DB fetch
  -> but the Hibernate Session is ALREADY CLOSED at this point
  -> throws LazyInitializationException: could not initialize proxy
     -> 500 error returned to the client
```

**Incident:** worked fine for months in low-traffic staging (where connection pooling sometimes kept sessions open longer by coincidence) but failed intermittently in production once traffic increased and connection/session lifecycle timing became tighter — a classic "works on my machine" bug rooted in a fundamental misunderstanding of WHEN the Proxy's real fetch actually happens.

**Root cause:** nobody on the team realized `order.getItems()` returns a **Virtual Proxy** (exactly this guide's pattern) that defers the real DB call until first access — and that access was happening OUTSIDE the proxy's valid "loading window" (the open Hibernate session), so the proxy had no way to fulfill the request.

**The fix:** switched to DTOs (explicit `OrderDto` with plain fields, no lazy proxies) constructed INSIDE the transactional service method where the session is guaranteed open, and never returned raw JPA entities from REST controllers again — a now-standard team convention enforced via architecture tests.

**Lesson for a new developer:** "Every time you see 'lazy loading' in a framework, that's a Proxy Pattern with a specific, narrow validity window for triggering the real fetch. Understand exactly when that window closes (transaction/session boundary) — using a lazy proxy outside its valid window is one of the most common real-world Java production bugs."

---

## 🎓 Final Tips
1. **Virtual Proxy**: Lazy initialization of expensive objects
2. **Protection Proxy**: Access control/authorization checks  
3. **Remote Proxy**: Represents object in different address space (RPC stubs)
4. **Key distinction from Decorator**: Proxy controls ACCESS, Decorator ADDS BEHAVIOR

Good luck! 🚀
