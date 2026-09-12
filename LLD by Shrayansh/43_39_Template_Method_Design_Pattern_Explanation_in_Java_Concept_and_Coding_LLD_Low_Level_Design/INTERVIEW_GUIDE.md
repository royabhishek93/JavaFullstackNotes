# 📐 Template Method Design Pattern - Interview Guide
## _15 YOE Architect-Level Conversational Script_

**📗 Difficulty: Beginner** — ideal starting point for a new developer; read this before tackling applied system-design questions.

> _(Companion to `transcript.md`, left untouched. Whiteboard-style scenario discussion.)_

---

**Interviewer**: "Design a payment flow: 'Pay to Friend' and 'Pay to Merchant' must both follow the SAME sequence — validate, debit, calculate fee, credit — but each step's logic differs per flow, and merchants get charged a platform fee while friends don't. How do you guarantee everyone follows the same sequence?"

**You**: "This is the exact signature of the **Template Method Pattern**: *you want all classes to follow a FIXED sequence of steps to accomplish a task, but each class needs its own logic WITHIN each step.*"

---

## 1. Architecture Diagram

```
┌───────────────────────────────────────┐
│         PaymentFlow (abstract class)          │
│  --------------------------------------------  │
│  + final sendMoney() {          <-- TEMPLATE     │
│      validateRequest();          METHOD, marked   │
│      debitAmount();              `final` so NO      │
│      calculateFees();            child can override │
│      creditAmount();             or reorder the steps│
│    }                                                    │
│                                                            │
│  abstract validateRequest();    <-- hook methods,           │
│  abstract debitAmount();            each child MUST          │
│  abstract calculateFees();          provide its own logic       │
│  abstract creditAmount();                                        │
└───────────────────────┬───────────────────────────┘
             ┌───────────────┴────────────────┐
             ▼                                    ▼
   ┌───────────────────┐              ┌─────────────────────┐
   │   PayToFriendFlow      │              │   PayToMerchantFlow      │
   │  fee = 0%                │              │  fee = 2%                  │
   │  credit = full amount   │              │  credit = amount - fee     │
   └───────────────────┘              └─────────────────────┘
```

```java
abstract class PaymentFlow {
    abstract void validateRequest();
    abstract void debitAmount();
    abstract void calculateFees();
    abstract void creditAmount();

    final void sendMoney() {          // TEMPLATE METHOD — locked sequence
        validateRequest();
        debitAmount();
        calculateFees();
        creditAmount();
    }
}

class PayToFriendFlow extends PaymentFlow {
    void validateRequest() { /* friend-specific validation */ }
    void debitAmount()     { /* debit sender */ }
    void calculateFees()   { /* 0% fee */ }
    void creditAmount()    { /* credit full amount to friend */ }
}

class PayToMerchantFlow extends PaymentFlow {
    void validateRequest() { /* KYC / merchant validation */ }
    void debitAmount()     { /* debit sender */ }
    void calculateFees()   { /* 2% platform fee */ }
    void creditAmount()    { /* credit (amount - fee) to merchant */ }
}
```

```java
PaymentFlow flow = new PayToMerchantFlow();
flow.sendMoney();   // guaranteed order: validate -> debit -> fee -> credit, no matter what
```

---

## 2. Scenario-First Explanation

**You**: "The key insight the interviewer wants to hear: *if I only override `sendMoney()` per child (plain polymorphism), NOTHING guarantees each child follows the same step order.* One child might accidentally credit before debiting — a correctness AND a security bug in a payments system. By making the orchestrating method `final` in the parent, and only the individual STEPS abstract, I structurally enforce the sequence — it's not just a convention, the compiler enforces it."

---

## 3. Cross Questions

**Q: "How is this different from Strategy Pattern?"**
**A:** "Strategy swaps an entire algorithm as ONE pluggable object (`vehicle.setStrategy(newStrategy)`), with no fixed 'shape' to the algorithm. Template Method fixes the **shape/order of steps** in the parent (via a `final` method) and lets subclasses fill in the *content* of each step. Rule of thumb: if the sequence itself must be enforced and shared, use Template Method; if the entire algorithm varies and needs runtime swapping, use Strategy."

**Q: "What if two steps need to be conditionally skipped for some subclasses (a 'hook')?"**
**A:** "Add a hook method with a default no-op/boolean implementation in the parent, e.g. `protected boolean shouldChargeFee() { return true; }`, and call it inside the template method: `if (shouldChargeFee()) calculateFees();`. `PayToFriendFlow` overrides it to `return false`. This is the standard 'template method with hooks' variant — very common in real frameworks (e.g. JUnit's `TestCase.setUp()`/`tearDown()` are hook methods around a template-like test execution lifecycle)."

---

## 4. Trade-offs

| Aspect | Template Method | Plain Polymorphism (override whole method) |
|---|---|---|
| Step order guaranteed? | Yes — enforced via `final` | No — each override could do anything |
| Code reuse of the "skeleton" | High — one place | Duplicated in every child |
| Flexibility per step | High (each step overridable) | High but with NO ordering guarantee |

---

## 5. Senior Trap Questions

**Trap: "Why not just document 'please call validate before debit' in a comment/README?"**
**✅ Senior answer:** "Comments and documentation are NOT enforced by the compiler — a future engineer under deadline pressure, or an AI code-gen tool, can easily violate that order in a new subclass, and in a payments system that's a correctness AND security risk (e.g. crediting before validating could allow negative-balance exploits). Making the template method `final` turns a 'social contract' into a **structural guarantee** — this is exactly why senior engineers prefer Template Method over 'just follow the convention'."

---

## 🔥 Real-World Production Issue: The Missing `final` That Allowed a Fraud Bypass

*In plain English: forgetting to make the orchestrating method "final" lets a subclass skip mandatory validation steps entirely.*

**The war story:**

"Our original `PaymentFlow.sendMoney()` template method was NOT marked `final` — an oversight during initial code review, since the team didn't yet know about Template Method Pattern formally; they just 'happened' to write it this way."

```java
abstract class PaymentFlow {
    void sendMoney() {              // ❌ NOT final — anyone can override!
        validateRequest();
        debitAmount();
        calculateFees();
        creditAmount();
    }
}
```

```
Months later, a new "InstantRefundFlow" subclass was added under deadline pressure.
The engineer, trying to make refunds "instant", OVERRODE sendMoney() entirely:

class InstantRefundFlow extends PaymentFlow {
    @Override
    void sendMoney() {
        creditAmount();          // ❌ credits FIRST
        debitAmount();           // then debits -- but validateRequest() was SKIPPED entirely!
    }
}
```

```
   Attack path exploited by fraud ring:
   ┌─────────────────────────────────────────────────┐
   │ 1. Submit refund request with invalid/fake order ID  │
   │ 2. validateRequest() never called -> no rejection      │
   │ 3. creditAmount() runs FIRST -> money credited            │
   │ 4. debitAmount() fails silently (no real order to debit)   │
   │    -> money credited with NOTHING debited                     │
   └─────────────────────────────────────────────────┘
   Result: ~$40,000 in fraudulent "refunds" processed before
           anomaly detection flagged unusual refund volume
```

**Root cause:** because `sendMoney()` wasn't `final`, a subclass was free to completely bypass the mandated order (and even skip `validateRequest()` altogether) — the exact structural guarantee Template Method Pattern is supposed to provide was never actually enforced.

**The fix:**
- Marked `sendMoney()` `final` immediately, which the compiler then used to reject the offending subclass, forcing the engineer to implement `InstantRefundFlow` correctly using the individual step methods instead.
- Added a static analysis / architecture rule flagging any orchestrating method in `*Flow` classes that isn't `final`.
- Retroactively audited every other Template-Method-shaped class in the codebase for the same missing-`final` gap.

**Lesson for a new developer:** "Template Method's entire value proposition is the enforced order — if you forget the `final` keyword, you've just written 'documentation that looks like code' with zero real guarantee. In domains like payments/security, that gap is not academic — it's an exploitable vulnerability."

---

## 🎓 Final Tips
1. Use Template Method when **all subclasses must follow the same step ORDER**, but each step's logic can differ.
2. Mark the orchestrating method `final` — this is not optional if correctness/security depends on the order.
3. Use hook methods (with default implementations) for steps that are optional/conditional per subclass.
4. Template Method vs Strategy: fixed skeleton with pluggable steps vs entirely swappable algorithm.
5. In production, always verify the "guaranteeing" method is actually `final` — a missing keyword can become an exploitable bypass.

Good luck! 🚀
