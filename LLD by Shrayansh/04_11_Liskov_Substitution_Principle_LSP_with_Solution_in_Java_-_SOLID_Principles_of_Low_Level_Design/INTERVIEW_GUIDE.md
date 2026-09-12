# 🔀 Liskov Substitution Principle (LSP) - Interview Guide
## _15 YOE Architect-Level Conversational Script_

**📗 Difficulty: Beginner** — ideal starting point for a new developer; read this before tackling applied system-design questions.

> _(Companion to `transcript.md`, left untouched. Deep-dive on the SOLID principle that's hardest to get right in practice.)_

---

**Interviewer**: "You have a `Vehicle` class with `hasEngine()` returning `true` by default. `Motorcycle` and `Car` inherit it fine. Now add a `Bicycle` subclass. What breaks, and how do you fix the DESIGN (not just patch the bug)?"

**You**: "This is the textbook LSP violation, and more importantly, let me show you the actual **structural fix**, not just 'be careful' advice."

---

## 1. The Problem

```
┌─────────────────┐
│      Vehicle           │  getNumberOfWheels() -> 2 (default)
│                          │  hasEngine() -> true (default)
└─────────┬────────────┘
    ┌───────┼─────────────────┐
    ▼        ▼                    ▼
┌─────────┐ ┌─────────┐    ┌─────────────┐
│Motorcycle │ │  Car       │    │  Bicycle       │
│(inherits,   │ │(overrides    │    │ hasEngine()      │
│ true)         │ │ wheels=4)    │    │ OVERRIDDEN to     │
└─────────┘ └─────────┘    │ return null!!  │  ❌ LSP VIOLATION
                              └─────────────┘
```

```java
List<Vehicle> vehicles = List.of(new Motorcycle(), new Car(), new Bicycle());
for (Vehicle v : vehicles) {
    System.out.println(v.hasEngine().toString());   // Bicycle.hasEngine() returns null
}                                                       // -> NullPointerException!!
```

**You**: "This is Liskov Substitution Principle in one sentence: **a subclass object must be substitutable for its parent, anywhere the parent is used, without breaking the program.** `Bicycle` REDUCED a capability (`hasEngine`) the parent promised for ALL vehicles — and any client code that iterates a `List<Vehicle>` and blindly calls `hasEngine()` now crashes, potentially at 100 different call-sites across the codebase."

---

## 2. The Structural Fix — Split the Hierarchy by Actual Capability

```
                    ┌─────────────┐
                    │    Vehicle       │   getNumberOfWheels()   <- generic, ALL vehicles have this
                    └──────┬──────────┘
              ┌───────────┼──────────────────┐
              ▼                                ▼
      ┌─────────────┐                 ┌────────────┐
      │  EngineVehicle    │                 │   Bicycle       │  <- extends Vehicle directly,
      │  hasEngine()          │                 │  (no engine     │      NEVER has hasEngine()
      └──────┬──────────┘                 │   capability      │      exposed at all!
        ┌────┴─────┐                     │   claimed)          │
        ▼            ▼                     └────────────┘
   ┌─────────┐ ┌─────────┐
   │Motorcycle │ │  Car       │
   └─────────┘ └─────────┘
```

```java
class Vehicle { int getNumberOfWheels() { return 2; } }

class EngineVehicle extends Vehicle {
    boolean hasEngine() { return true; }     // only vehicles WITH an engine have this method AT ALL
}

class Motorcycle extends EngineVehicle {}
class Car extends EngineVehicle { int getNumberOfWheels() { return 4; } }
class Bicycle extends Vehicle {}              // extends Vehicle directly — no hasEngine() to violate!
```

**You**: "Now watch what happens with three different client code shapes:"

```java
// 1. List<Vehicle> — only generic methods available, ALWAYS safe
List<Vehicle> all = List.of(new Motorcycle(), new Car(), new Bicycle());
all.forEach(v -> v.getNumberOfWheels());     // ✅ works for everyone, no crash possible

// 2. List<Vehicle> trying to call hasEngine() — COMPILE-TIME error, not runtime crash!
all.forEach(v -> v.hasEngine());             // ❌ won't even compile — Vehicle has no hasEngine()

// 3. List<EngineVehicle> — Bicycle literally CANNOT be added, compiler enforces it
List<EngineVehicle> withEngines = List.of(new Motorcycle(), new Car());  // Bicycle not allowed here!
withEngines.forEach(v -> v.hasEngine());     // ✅ safe, guaranteed by the type system
```

---

## 3. Scenario-First Explanation

**You**: "The key insight that makes LSP click: **push capabilities DOWN the hierarchy to only where they're guaranteed to apply, instead of defaulting them at the top and having subclasses opt OUT.** The original design put `hasEngine()` on `Vehicle` (the top) and expected exceptions (`Bicycle`) to override it away — that's backwards. The fix creates an intermediate `EngineVehicle` class so only vehicles that TRULY have this capability inherit the method at all. This converts a **runtime NullPointerException** (found in production, maybe by a customer) into a **compile-time error** (found by the compiler, before the code ever ships)."

---

## 4. Cross Questions

**Q: "How do you spot an LSP violation during code review, before it becomes a production bug?"**
**A:** "Watch for subclasses that (a) override a method to throw `UnsupportedOperationException`, (b) override a method to return `null`/empty where the parent guaranteed a real value, or (c) override a method to do nothing (silently) where the parent's contract implied real work happens. All three are the same smell: the child is silently breaking a promise the parent's interface made to callers."

**Q: "Isn't LSP just 'don't override badly' — is it really a separate principle from just writing correct code?"**
**A:** "It's more specific than that: LSP is about the *behavioral contract* of the type hierarchy holding for ALL substitutions, not just 'don't have bugs'. A method can be perfectly bug-free in isolation and still violate LSP if it changes the parent's implied contract (e.g. a `Rectangle.setWidth()` that a naive `Square extends Rectangle` overrides to also change height — technically 'working' but breaking any client code that assumes setting width doesn't affect height)."

---

## 5. Trade-offs

| Aspect | Deep, capability-based hierarchy (the fix) | Flat hierarchy + `instanceof` checks everywhere |
|---|---|---|
| Safety | Compile-time enforced | Runtime, easy to forget a check |
| Hierarchy complexity | More intermediate classes | Fewer classes, more scattered conditionals |
| Scalability | New capability = new intermediate class, clean | New capability = more `instanceof` checks sprinkled everywhere |

---

## 6. Senior Trap Questions

**Trap: "Why not just add `if (vehicle instanceof Bicycle) skip;` at every call-site instead of restructuring the hierarchy?"**
**✅ Senior answer:** "That 'fixes' each call-site individually but doesn't fix the DESIGN — the underlying contract violation still exists, and every NEW call-site that iterates `List<Vehicle>` and calls `hasEngine()` will hit the same bug again, requiring the same manual `instanceof` check to be remembered, every single time, forever. The intermediate `EngineVehicle` class fixes it ONCE, structurally, and the compiler enforces it for all future code — nobody has to remember anything."

---

## 🔥 Real-World Production Issue: The Refund Processor LSP Violation

*In plain English: a subclass that fakes success instead of admitting it can't do something will quietly corrupt every process that trusts it.*

**The war story:**

"We had a `PaymentMethod` interface with a `refund(amount)` method, implemented by `CreditCardPayment`, `UPIPayment`, and `GiftCardPayment`. A new `CashOnDeliveryPayment` was added, and since COD genuinely can't be refunded electronically, the engineer implemented `refund()` to silently do nothing and return successfully (`return RefundStatus.SUCCESS`) rather than represent that refunds aren't supported."

```java
class CashOnDeliveryPayment implements PaymentMethod {
    public RefundStatus refund(double amount) {
        // TODO: COD refunds handled manually by ops team, nothing to do here
        return RefundStatus.SUCCESS;    // ❌ LSP VIOLATION: silently lies about doing work
    }
}
```

```
┌──────────────────────────────────────────────────┐
│  Generic refund-processing job (runs nightly):                     │
│  for (Order order : ordersMarkedForRefund) {                          │
│      RefundStatus status = order.paymentMethod.refund(order.amount);   │
│      if (status == SUCCESS) {                                            │
│          order.markRefundComplete();       // ❌ marked complete,          │
│          closeOrderTicket();                    but customer NEVER got money │
│      }                                                                      │
│  }                                                                          │
└──────────────────────────────────────────────────┘
```

**Incident:** the generic nightly refund-reconciliation job trusted `refund()`'s return value uniformly across ALL payment methods (as LSP promises it should be able to). Because `CashOnDeliveryPayment.refund()` lied and returned `SUCCESS` without doing any real work, ~1,200 customer support tickets over 6 weeks were auto-closed as "refund complete" while customers had received nothing — discovered only when a customer escalated to social media.

**Root cause:** `CashOnDeliveryPayment` violated LSP by not honestly representing its actual capability — instead of properly signaling "refund not supported through this automated path", it silently returned a value indistinguishable from a real, successful refund, breaking every piece of generic client code (the nightly job) that trusted the `PaymentMethod` contract.

**The fix:**
```java
// ✅ Honest contract: represent the REAL capability, don't fake success
interface PaymentMethod {
    boolean supportsAutomaticRefund();
    RefundStatus refund(double amount);   // only called if supportsAutomaticRefund() == true
}
class CashOnDeliveryPayment implements PaymentMethod {
    public boolean supportsAutomaticRefund() { return false; }
    public RefundStatus refund(double amount) {
        throw new UnsupportedOperationException("COD refunds require manual ops action");
    }
}
```
- The nightly job now checks `supportsAutomaticRefund()` first, and routes non-automatic refunds to a manual ops queue instead of silently marking them complete.

**Lesson for a new developer:** "LSP violations in production don't always crash loudly with a `NullPointerException` — sometimes they're much worse: a subclass that silently lies about doing work, which is invisible until a downstream audit or a very unhappy customer surfaces it weeks later. When a capability genuinely doesn't apply to a subclass, make that explicit (`supportsX()` checks, or a documented exception) rather than faking success."

---

## 🎓 Final Tips
1. LSP: a subclass must NEVER reduce or fake a capability the parent's contract promises.
2. Fix violations structurally — push capability-specific methods DOWN into an intermediate class, don't leave them at the top with subclasses opting out.
3. This converts runtime crashes into compile-time errors — the strongest form of guarantee.
4. In production, the most dangerous LSP violations are subclasses that SILENTLY fake success rather than crash loudly — always make unsupported operations explicit.

Good luck! 🚀
