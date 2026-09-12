# Interview Guide: Template Method Design Pattern

## 🗣️ The Interview Scenario

> "In our payments system, there are two flows: paying a friend (peer-to-peer) and paying a merchant. Both need to go through the same sequence — validate the request, debit the sender, calculate platform fees, and credit the receiver — but each flow calculates fees and validates requests differently. How would you design this so every payment flow is *guaranteed* to follow the same step order, while still letting each flow customize the actual logic inside each step?"

This tests whether you recognize the specific signature of **"same skeleton, different step implementations, order must be enforced"** and reach for **Template Method** instead of just letting each subclass freely override one big method (which offers no ordering guarantee).

## 🏗️ Architect's Explanation (For a New Developer)

Think of a recipe card for making any sandwich: "1) toast the bread, 2) add the spread, 3) add the filling, 4) close it up." The **order of steps is fixed and non-negotiable** — every sandwich follows exactly this sequence. But *what* goes in step 2 (butter vs. mayo) and step 3 (turkey vs. cheese) is completely up to whoever's making that particular sandwich. Nobody making a sandwich gets to reorder the recipe — they can only fill in the blanks within each step.

That's exactly the **Template Method pattern**: you identify a signal — *"when you want all classes to follow the specific steps to process a task, but also need the flexibility that each class can have its own logic in that specific step"* — and you encode the fixed sequence once, in a `final` method on an abstract base class, calling out to `abstract` methods for each step. Subclasses **must** provide the step implementations, but they **cannot** change the order — the order is locked in the parent's template method, and marking it `final` is what makes that guarantee unbreakable.

## 📊 Visualize It

**Class structure:**

```
     abstract class PaymentFlow
   ------------------------------------
   + final sendMoney()                 <-- the TEMPLATE METHOD, cannot be overridden
       {
         validateRequest();
         debitAmount();
         calculateFees();
         creditAmount();
       }
   + abstract validateRequest()
   + abstract debitAmount()
   + abstract calculateFees()
   + abstract creditAmount()
               ▲
               | extends
       ┌───────┴────────┐
  PayToFriendFlow   PayToMerchantFlow
  - validateRequest(): friend-specific validation
  - debitAmount(): ...
  - calculateFees(): 0% fee
  - creditAmount(): full amount credited
                    - validateRequest(): merchant-specific validation
                    - debitAmount(): ...
                    - calculateFees(): 2% platform fee
                    - creditAmount(): amount minus fee credited
```

**Runtime sequence (order is enforced regardless of subclass):**

```
PaymentFlow obj = new PayToFriendFlow();
obj.sendMoney();     // resolves to the PARENT's sendMoney() — it's final, never overridden

   sendMoney() [fixed order, defined once in PaymentFlow]
       │
       ├──1──▶ validateRequest()  ──dispatches to──▶ PayToFriendFlow.validateRequest()
       ├──2──▶ debitAmount()      ──dispatches to──▶ PayToFriendFlow.debitAmount()
       ├──3──▶ calculateFees()    ──dispatches to──▶ PayToFriendFlow.calculateFees()   (0%)
       └──4──▶ creditAmount()     ──dispatches to──▶ PayToFriendFlow.creditAmount()
```

## 🔧 Deep Dive: How It Actually Works

### 1. The abstract base class defines the template method as `final`
```java
abstract class PaymentFlow {

    // THE TEMPLATE METHOD — defines the fixed order of steps. Marked final:
    // no subclass can override it and reorder/skip steps.
    public final void sendMoney() {
        validateRequest();
        debitAmount();
        calculateFees();
        creditAmount();
    }

    protected abstract void validateRequest();
    protected abstract void debitAmount();
    protected abstract void calculateFees();
    protected abstract void creditAmount();
}
```

### 2. Concrete subclasses fill in only the step logic
```java
class PayToFriendFlow extends PaymentFlow {
    protected void validateRequest() { /* friend-specific validation */ }
    protected void debitAmount()     { /* debit sender */ }
    protected void calculateFees()   { /* 0% — no platform fee between friends */ }
    protected void creditAmount()    { /* credit the FULL amount to the friend */ }
}

class PayToMerchantFlow extends PaymentFlow {
    protected void validateRequest() { /* merchant-specific validation */ }
    protected void debitAmount()     { /* debit sender */ }
    protected void calculateFees()   { /* e.g., 2% platform fee */ }
    protected void creditAmount()    { /* credit (amount - fee) to the merchant */ }
}
```

### 3. Client usage
```java
PaymentFlow flow = new PayToFriendFlow();
flow.sendMoney();   // guaranteed order: validate -> debit -> fees -> credit, every time
```
Because `sendMoney()` only exists on the parent and is `final`, calling `obj.sendMoney()` **always** resolves to the parent's implementation — subclasses can never accidentally (or intentionally) reorder steps, e.g., doing `credit` before `debit`.

### Two concrete signals that tell you "this is a Template Method problem" (from the source)
1. **"When you want all classes to follow the specific steps to process the task"** — i.e., there's a mandatory sequence that every implementation must honor.
2. **"You also need to provide the flexibility that each class can have their own logic in that specific step"** — i.e., the *what* varies per subclass even though the *order* must not.

If only signal #1 is true (fixed order, no per-class variation needed), you don't need this pattern at all — a plain concrete method suffices. If only signal #2 is true (varying logic, no ordering constraint), a simpler strategy/polymorphic dispatch is enough. **Both together** is what makes Template Method the right tool.

### Why not just let each subclass override one big `sendMoney()` method directly?
If `sendMoney()` weren't a `final` template method and each subclass simply overrode it independently, **nothing guarantees they follow the same step order** — one subclass might validate, then debit, then charge fees, then credit; another might (accidentally or due to a bug) credit before debiting. The template method's entire value proposition is: *the parent owns and guarantees the sequence; children only own the step contents.*

## 🔥 Real Production Incident & Fix

**What broke:** A payments platform had two payment flows — peer-to-peer and peer-to-merchant — implemented as two *independent* classes, each with its own full `processPayment()` method (no shared template). A new engineer, adding a "gift card top-up" flow, copy-pasted the merchant flow as a starting point and, while refactoring for the new use case, accidentally reordered the copy so `creditAmount()` was called **before** `calculateFees()` had actually run (a leftover variable held a stale, zero fee value at credit time).

**How the team noticed:** Finance reconciliation flagged that the platform's fee revenue for gift-card top-ups was showing as ₹0 across all transactions for several days, while the ledger showed money moving between accounts as expected. It wasn't caught by functional tests because the "happy path" of money moving from sender to receiver still worked — only the *fee* was silently wrong, and only end-of-day reconciliation surfaced the discrepancy.

**Root cause:** There was no enforced, shared step order across payment flows — each flow's method was free-form, so copy-paste-and-modify introduced a subtle step-ordering bug that compiled fine and passed "money moved" assertions, because nothing structurally prevented steps from running out of order.

**The fix:** The team refactored all three flows (peer-to-peer, peer-to-merchant, gift-card top-up) to extend a shared abstract `PaymentFlow` with a `final sendMoney()` template method enforcing `validate → debit → calculateFees → credit`, exactly as in this transcript. Now, structurally, **it is impossible** to credit before calculating fees — the compiler and class design itself prevent that class of bug, because subclasses only implement the four step methods and have no ability to touch the ordering.

```
BEFORE: each flow is a free-standing method, ordering       AFTER: shared final template method enforces
is just "whatever the author happened to write" (fragile)   order; subclasses can only fill in step logic

  GiftCardFlow.processPayment() {                            abstract PaymentFlow {
     validate(); credit(); debit(); calculateFees();  //       final sendMoney() {
     // BUG: credit ran with stale/zero fee value               validate(); debit(); calculateFees(); credit();
  }                                                            }
                                                              }
                                                              GiftCardFlow extends PaymentFlow { ...steps only... }
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why must the template method (`sendMoney`) be declared `final`?**
A: Marking it `final` is what actually *guarantees* the fixed step order — without `final`, any subclass could override `sendMoney()` entirely and implement the steps in a different order (or skip one), completely defeating the pattern's purpose. `final` is the language-level enforcement mechanism that turns "please follow this order" into "you structurally cannot do otherwise."

**Q2: How is this different from just calling four separate methods manually in the client code, in order, every time?**
A: If the client (caller) is responsible for calling `validate()`, then `debit()`, then `calculateFees()`, then `credit()` in the right order every time, that ordering logic gets duplicated across every call site and is trivially easy to get wrong once. Template Method centralizes the ordering **once**, inside the class hierarchy itself, so callers just invoke a single `sendMoney()` and correctness is guaranteed regardless of how many call sites exist.

**Q3: Can a Template Method have "optional" steps that a subclass may skip?**
A: Yes — this is commonly done via **hook methods**: give a step a default (often empty or no-op) implementation in the abstract base class instead of making it purely `abstract`. Subclasses can then override it if they need custom behavior, or simply leave the default in place if the step is a no-op for them, without being forced to write an empty override.

**Q4: Isn't this just the Strategy pattern in disguise?**
A: No — they solve different problems. Strategy is about swapping an entire interchangeable **algorithm** at runtime (e.g., choosing between different sorting algorithms), with no inherent ordering constraint across steps. Template Method is about **enforcing a fixed sequence of steps** while allowing each *step's* implementation to vary — the point isn't "pick one of several complete algorithms," it's "guarantee everyone follows the same skeleton."

**Q5: How would you unit test this design effectively?**
A: Because the step order is centralized and guaranteed by the `final` template method, you don't need to re-test step ordering for every new subclass — you test it once against the abstract contract (e.g., using a test double subclass), and then each concrete subclass's tests only need to verify **its own step implementations** (validation rules, fee percentage, etc.) in isolation, since the base class already guarantees correct sequencing.

**Q6: Is this pattern actually common in real production codebases, or mostly academic?**
A: It's noted as being **very frequently used in the industry**, often without engineers realizing they're applying a named pattern — any time you see an abstract class with a `final` (or non-overridable) orchestrating method calling several `abstract`/hook methods in a fixed order (common in frameworks' lifecycle methods, batch-job pipelines, or request-processing pipelines), that's Template Method in production use.

## 🔑 Key Takeaway

When multiple classes must execute the **same fixed sequence of steps** but need to customize the **logic within** each step, put the sequence in a `final` template method on an abstract base class that calls abstract step methods — this structurally guarantees ordering can never drift between implementations, which a free-form override can never guarantee.
