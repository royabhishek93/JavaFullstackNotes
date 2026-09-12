# 🔌 Adapter Design Pattern - Interview Guide
## _15 YOE Architect-Level Conversational Script_

**📗 Difficulty: Beginner** — ideal starting point for a new developer; read this before tackling applied system-design questions.

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

## 🔥 Real-World Production Issue: The Adapter That Silently Swallowed a Provider's Breaking Change

*In plain English: a third-party vendor can silently change what a status code MEANS, and your adapter won't notice unless you specifically test for it.*

**The war story:**

"A payments platform used a `PaymentGatewayAdapter` wrapping a third-party provider's SDK (exactly this guide's recommended pattern) so the rest of the codebase depended only on the platform's OWN `PaymentProcessor` interface. The provider shipped a 'minor' SDK upgrade that silently changed a response field's meaning (a status code that used to mean 'pending' started also being returned for 'failed, retry later' cases)."

```
OLD provider SDK: status="PENDING" only meant "processing normally"
NEW provider SDK: status="PENDING" ALSO used for "failed, will retry internally"

Our Adapter (unchanged since it wasn't touched during the SDK bump):
class StripeAdapter implements PaymentProcessor {
    PaymentStatus process(...) {
        String status = stripeSdk.charge(...).getStatus();
        return status.equals("PENDING") ? PaymentStatus.PENDING : ...;
            // <- still mapped PENDING -> PENDING, missing the NEW
            //     failure semantics the vendor silently introduced
    }
}

Result: orders that had actually FAILED were shown to customers as
"payment processing", and inventory was held/reserved indefinitely
for orders that would never complete -- discovered only when
finance reconciliation found a growing backlog of stuck orders
```

**Root cause:** the Adapter Pattern successfully isolated the REST of the codebase from the vendor SDK's shape (exactly as intended) — but that isolation ALSO meant the vendor's silent semantic change was invisible outside the one Adapter class, and nobody had a contract test verifying the Adapter's mapping logic against the vendor's actual current behavior.

**The fix:** added a suite of contract tests that run against the vendor's SANDBOX API on every SDK version bump, asserting the Adapter's status-mapping produces the expected `PaymentStatus` for each of the vendor's documented status codes — these tests would have caught the meaning-drift immediately instead of it surfacing weeks later via a stuck-order backlog.

**Lesson for a new developer:** "Adapter Pattern isolates you from a vendor's API SHAPE (method signatures, field names) — but it does NOT automatically protect you from the vendor silently changing the MEANING of values within that same shape. Any time you bump a third-party SDK version wrapped by an Adapter, run contract tests against the adapter's mapping logic, not just a compile-check that the code still builds."

---

## 🎓 Final Tips
1. **Adapter bridges incompatible interfaces** without modifying existing code
2. **Object Adapter (composition) preferred** over Class Adapter (inheritance)
3. **Dependency Inversion**: depend on your OWN abstraction, adapt vendors to it
4. **Real-world**: JDBC drivers, payment gateway SDKs, legacy system integration

Good luck! 🚀
