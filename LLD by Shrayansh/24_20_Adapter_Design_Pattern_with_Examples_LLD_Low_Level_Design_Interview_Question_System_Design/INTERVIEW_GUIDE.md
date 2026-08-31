# 🔌 Adapter Design Pattern - Interview Guide
## _15 YOE Architect-Level Conversational Script_

---

**Interviewer**: "Explain the Adapter Design Pattern with a real-world scenario."

**You**: "Adapter Pattern lets **incompatible interfaces work together** by wrapping one interface to look like another. Classic real-world analogy: a **power plug adapter** - your laptop charger (US plug) doesn't fit an Indian socket, so you use a physical adapter that translates between the two interfaces."

---

## 1. Architecture Diagram

```
Client expects:  ┌─────────────┐
                 │ TargetInterface│
                 │ (what client   │
                 │  code calls)   │
                 └───────┬─────┘
                         │ implements
                         ▼
                 ┌─────────────┐
                 │   Adapter    │  ◄── Translates calls
                 │              │
                 │ holds ref to │
                 │ Adaptee      │
                 └───────┬─────┘
                         │ wraps/delegates to
                         ▼
                 ┌─────────────┐
                 │   Adaptee    │  ◄── Existing incompatible class
                 │ (3rd-party   │      (can't modify this!)
                 │  library)    │
                 └─────────────┘
```

## 2. Code Example - Payment Gateway Integration

```java
// Our system's expected interface
interface PaymentProcessor {
    void processPayment(double amount, String currency);
}

// Third-party library with INCOMPATIBLE interface (can't modify!)
class LegacyStripeSDK {
    void makeCharge(int amountInCents, String currencyCode) {
        System.out.println("Charging " + amountInCents + " cents in " + currencyCode);
    }
}

// Adapter bridges the gap
class StripeAdapter implements PaymentProcessor {
    private LegacyStripeSDK stripeSDK;
    
    StripeAdapter(LegacyStripeSDK stripeSDK) {
        this.stripeSDK = stripeSDK;
    }
    
    public void processPayment(double amount, String currency) {
        // Translate: dollars → cents, adapt method name & signature
        int amountInCents = (int) (amount * 100);
        stripeSDK.makeCharge(amountInCents, currency);
    }
}

// Client code only knows about PaymentProcessor - doesn't care about Stripe specifics!
PaymentProcessor processor = new StripeAdapter(new LegacyStripeSDK());
processor.processPayment(49.99, "USD");
```

---

## 3. Scenario-First Explanations

### **Why Adapter Instead of Modifying the Third-Party Class?**

**You**: "You often CAN'T modify third-party/legacy code (no source access, or it's a vendored library). Even if you COULD, modifying it directly couples your business logic with vendor-specific code, making it hard to SWAP providers later. Adapter isolates this translation logic in ONE place - if you switch from Stripe to Razorpay, you write a `RazorpayAdapter`, and ZERO changes needed in the rest of your codebase that depends on `PaymentProcessor`."

---

## 4. Cross Questions

**Interviewer**: "What's the difference between Class Adapter (via inheritance) and Object Adapter (via composition)?"

**You**: "
```java
// Object Adapter (composition) - shown above, PREFERRED approach
class StripeAdapter implements PaymentProcessor {
    private LegacyStripeSDK stripeSDK;  // HAS-A relationship
    // ...
}

// Class Adapter (inheritance) - Java doesn't support multiple inheritance of classes,
// so this only works if Adaptee is an interface or you're in a language like C++
class StripeAdapter extends LegacyStripeSDK implements PaymentProcessor {
    public void processPayment(double amount, String currency) {
        makeCharge((int)(amount * 100), currency);  // Inherited method
    }
}
```

**I prefer Object Adapter (composition)** because:
1. Follows 'favor composition over inheritance' principle
2. Can adapt MULTIPLE adaptees if needed  
3. Doesn't expose Adaptee's other public methods accidentally (encapsulation)
4. Works even in Java's single-inheritance constraint"

---

## 5. Trade-offs

| Aspect | Object Adapter (composition) | Class Adapter (inheritance) |
|--------|----------------------------------|----------------------------------|
| **Flexibility** | Can adapt multiple adaptees | Limited to one (single inheritance) |
| **Encapsulation** | Better (only exposes target interface) | Worse (inherits ALL adaptee's public methods) |
| **Language support** | Universal | Requires multiple inheritance or interfaces |

---

## 6. Senior Trap Questions

### **Trap: "Just modify the client code to call the third-party API directly!"**

**✅ Senior**: "This creates TIGHT COUPLING between your business logic and a specific vendor's API shape. If you have 50 places in your codebase calling Stripe directly, switching providers (or even just upgrading Stripe's SDK to a breaking new version) means changing 50 places. With Adapter Pattern, you change ONE class. This is the Dependency Inversion Principle in action - your business logic depends on YOUR OWN abstraction (`PaymentProcessor`), not on vendor specifics."

---

## 7. Technology Choices

**You**: "**JDBC** is a massive real-world Adapter Pattern example - `Connection`, `Statement`, `ResultSet` are all standard interfaces, and each database vendor (MySQL, PostgreSQL, Oracle) provides a JDBC DRIVER that adapts their proprietary wire protocol to this common interface. Your Java code writes `SELECT * FROM users` through the same `Statement` interface regardless of underlying database."

---

## 🎓 Final Tips
1. **Adapter bridges incompatible interfaces** without modifying existing code
2. **Object Adapter (composition) preferred** over Class Adapter (inheritance)
3. **Dependency Inversion**: depend on your OWN abstraction, adapt vendors to it
4. **Real-world**: JDBC drivers, payment gateway SDKs, legacy system integration

Good luck! 🚀
