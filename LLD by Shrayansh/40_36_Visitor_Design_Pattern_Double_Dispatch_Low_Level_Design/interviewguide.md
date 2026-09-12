# Interview Guide: Visitor Design Pattern & Double Dispatch

## 🗣️ The Interview Scenario

> "Here's a `HotelRoom` class with methods `getRoomPrice()`, `initiateRoomMaintenance()`, and `reserveRoom()`. Over time, you'll need to keep adding new operations to this class — and there are also multiple room subtypes (single, double, deluxe). Every time you add an operation, you risk having to re-test the entire class. How would you redesign this so new operations can be added without touching or re-testing existing, already-shipped code? And can you explain what 'double dispatch' means and where it happens in your design?"

This tests whether you recognize a **"class keeps growing with unrelated operations"** smell and can correctly apply **Visitor**, plus whether you actually understand the *mechanism* (double dispatch) rather than just reciting the UML.

## 🏗️ Architect's Explanation (For a New Developer)

Picture a hotel with three room types: Single, Double, Deluxe. Today you need to calculate `price()` for each. Tomorrow, someone wants `initiateMaintenance()`. Next month, `reserveRoom()`. If you keep adding these as methods directly on the `Room` classes, two things go wrong:
1. **Every existing, already-tested operation lives in the same class as new ones** — so adding operation #4 forces you to touch (and re-test) a class you already shipped and verified.
2. **The class grows without bound** — today 3 methods, in six months maybe 50, because nobody knows how many operations will eventually be needed.

The **Visitor pattern** solves this by physically **separating the operations from the objects they operate on**. Instead of the `Room` classes hosting all their own logic, you create a separate `Visitor` hierarchy — one concrete visitor *class* per operation (e.g., `RoomPricingVisitor`, `RoomMaintenanceVisitor`). The `Room` classes keep exactly one method forever: `accept(visitor)`. Adding operation #50 means writing one new visitor class — **you never touch `Room` or any existing visitor again.**

The mechanism that makes this "route to the correct combination of (room type, operation)" trick work is called **double dispatch** — the actual method that runs is decided not by one object (like normal polymorphism) but by **two** objects together: the room *and* the visitor.

## 📊 Visualize It

**Class structure:**

```
      <<interface>>                          <<interface>>
      RoomElement                            RoomVisitor
    ------------------                    ---------------------
    + accept(RoomVisitor v)                + visit(SingleRoom)
           ▲                               + visit(DoubleRoom)
           | implements                    + visit(DeluxeRoom)
   ┌───────┼────────────┐                          ▲
   |       |            |                          | implements
SingleRoom DoubleRoom DeluxeRoom      ┌──────────────┼───────────────┐
                                RoomPricingVisitor RoomMaintenanceVisitor  ReserveRoomVisitor
                                (implements all 3 visit() methods, one per room type)
```

**Double dispatch trace (accept() call, then visit() call):**

```
singleRoomObj.accept(pricingVisitor);
      │
      ▼ [DISPATCH #1 — single dispatch: decided by the CALLER's runtime type]
SingleRoom.accept(RoomVisitor v) {
      v.visit(this);            // "this" is statically known to be a SingleRoom
}
      │
      ▼ [DISPATCH #2 — decided by BOTH the visitor's runtime type AND the argument's type]
RoomPricingVisitor.visit(SingleRoom room) { ... computes single-room price ... }
```

## 🔧 Deep Dive: How It Actually Works

### 1. The element side — `RoomElement`
```java
interface RoomElement {
    void accept(RoomVisitor visitor);
}

class SingleRoom implements RoomElement {
    public void accept(RoomVisitor visitor) {
        visitor.visit(this);   // passes itself, statically typed as SingleRoom
    }
}
// DoubleRoom, DeluxeRoom implement accept() identically, each passing "this" as their own type
```
Any future room type (e.g., `PresidentialSuite`) just implements `accept()` the same way.

### 2. The visitor side — `RoomVisitor`
```java
interface RoomVisitor {
    void visit(SingleRoom room);
    void visit(DoubleRoom room);
    void visit(DeluxeRoom room);
}

class RoomPricingVisitor implements RoomVisitor {
    public void visit(SingleRoom room) { /* single-room pricing logic */ }
    public void visit(DoubleRoom room) { /* double-room pricing logic */ }
    public void visit(DeluxeRoom room) { /* deluxe-room pricing logic */ }
}

class RoomMaintenanceVisitor implements RoomVisitor {
    public void visit(SingleRoom room) { /* single-room maintenance logic */ }
    public void visit(DoubleRoom room) { /* double-room maintenance logic */ }
    public void visit(DeluxeRoom room) { /* deluxe-room maintenance logic */ }
}
```
Adding `reserveRoom` as a third operation is just `RoomReserveVisitor implements RoomVisitor { ... }` — **`SingleRoom`, `DoubleRoom`, `DeluxeRoom`, `RoomPricingVisitor`, and `RoomMaintenanceVisitor` are never modified.**

### 3. Single Dispatch vs. Double Dispatch (the part interviewers really probe)

**Single dispatch** — plain polymorphism you already know:
```java
RoomElement obj = new DeluxeRoom();
obj.accept(visitor);   // which accept() runs? Decided by ONE thing: obj's runtime type (DeluxeRoom)
```

**Double dispatch** — the method that ultimately runs is decided by **two** objects together:
```java
singleRoomObj.accept(pricingVisitor);
```
- **First dispatch** (single dispatch, on the caller): `singleRoomObj`'s runtime type is `SingleRoom`, so `SingleRoom.accept()` runs.
- Inside that `accept()`, it calls `visitor.visit(this)` — but `visitor`'s *runtime* type could be `RoomPricingVisitor` or `RoomMaintenanceVisitor`.
- **Second dispatch**: which `visit(...)` overload actually executes is now resolved based on **both** the visitor's runtime type (which concrete visitor class) **and** the compile-time type of the argument being passed (`this`, statically known as `SingleRoom` inside `SingleRoom.accept`).

So: *"the method to be invoked depends on two objects — the caller and the argument passed"* — that is the working definition of double dispatch, taken directly from the source explanation.

### 4. Visitor vs. Strategy (a very commonly confused pair)
A junior might propose: "why not just have `SingleRoomPricingStrategy`, `SingleRoomMaintenanceStrategy`, `DeluxeRoomPricingStrategy`, etc., and swap them at runtime?" This is **wrong** because it conflates two different concerns:
- **Strategy** separates out **interchangeable algorithms** that are independent of which object uses them (e.g., all room types might use the exact same discount-calculation algorithm; the algorithm doesn't inherently belong to any one room type).
- **Visitor** separates out **operations that are specific to each element type** (single room pricing logic is *not* interchangeable with deluxe room pricing logic — they're fundamentally tied to that element).

If you catch yourself building "one strategy class per (element type × operation) combination," that's a signal you actually want Visitor, not Strategy.

## 🔥 Real Production Incident & Fix

**What broke:** A hotel-booking backend's `Room` base class (with `SingleRoom`, `DoubleRoom`, `DeluxeRoom` subclasses) had grown organically to include `getPrice()`, `reserveRoom()`, `cancelReservation()`, `initiateMaintenance()`, `applyLoyaltyDiscount()`, and `generateInvoiceLine()` — six operations, each duplicated with type-specific logic across three room subclasses (18 methods total, tightly coupled).

**How the team noticed:** A product request came in to add a *seventh* operation: `applySeasonalSurge()`. The engineer assigned to it modified the base `Room` class to add an abstract method, which forced edits to all three subclasses. During that change, a merge conflict silently reverted a recent bug fix in `DeluxeRoom.applyLoyaltyDiscount()` from two sprints earlier. It shipped, and the regression was caught by a finance audit report showing deluxe-room loyalty discounts weren't being applied for a two-week window — costing the business a measurable refund/goodwill payout.

**Root cause:** Every operation lived inside the room class hierarchy itself, so any new operation touched a shared, business-critical file (`Room.java` and its subclasses), and unrelated logic (loyalty discount) sat right next to logic being actively changed (surge pricing), with no isolation between them. No test suite failure caught it because the regression was a **silent revert via merge conflict**, not a compile error.

**The fix:** The team refactored to the Visitor pattern from this transcript: each operation became an isolated `RoomVisitor` implementation (`SurgePricingVisitor`, `LoyaltyDiscountVisitor`, etc.), each independently owned, reviewed, and tested. `Room` subclasses were frozen to just `accept(RoomVisitor)` — a file that essentially never changes again. Adding `applySeasonalSurge()` afterward required creating one new file with zero risk to `LoyaltyDiscountVisitor`.

```
BEFORE: 3 room classes each hosting 6+ operations       AFTER: room classes frozen (accept-only);
(new operation = edit all 3, risk to unrelated logic)    each operation isolated in its own visitor

  SingleRoom { getPrice(), reserve(), maintain(),         SingleRoom { accept(visitor) }  <- never touched again
               loyaltyDiscount(), surge(), invoice() }
  DoubleRoom { ...same 6, duplicated logic... }           SurgePricingVisitor   { visit(Single/Double/Deluxe) }
  DeluxeRoom { ...same 6, duplicated logic... }           LoyaltyDiscountVisitor{ visit(Single/Double/Deluxe) }
                                                            (each independently deployable/testable)
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: What's the actual definition of double dispatch, and where exactly does it happen in this design?**
A: Double dispatch means the method that gets invoked is determined by **two** objects, not one — the object the method is called *on* (the caller) and the object passed as an *argument*. Here it happens in two steps: `element.accept(visitor)` resolves via normal single-dispatch polymorphism to the correct element's `accept()`; inside that method, `visitor.visit(this)` resolves to the correct overload based on both the visitor's concrete type and the statically-known type of `this` at that call site.

**Q2: What's the main drawback of the Visitor pattern?**
A: Adding a **new element type** (e.g., `PresidentialSuite`) is expensive — every existing visitor interface and every concrete visitor class must be updated with a new `visit(PresidentialSuite)` method. Visitor trades "easy to add operations" for "hard to add new element types." You should only reach for it when operations change far more often than element types.

**Q3: How is Visitor different from just using `instanceof` checks inside one big method?**
A: An `instanceof`/type-switch approach keeps growing a single method and violates the Open/Closed Principle every time a new element type is added — you must edit that method. Visitor instead uses the compiler/runtime dispatch mechanism (double dispatch) to route to the correct type-specific code automatically, and adding a new *operation* requires zero changes to existing classes — only a type-check approach can't offer that isolation.

**Q4: Could you combine all three `visit()` overloads in a visitor into a single method with `if/else` on type?**
A: Technically yes if you don't have separate overloads and instead accept a common supertype and branch internally — but that reintroduces the exact problem Visitor is meant to avoid (a growing conditional inside one method) and loses compile-time safety (the compiler can't guarantee every element type is handled). Keeping distinct `visit(SingleRoom)`, `visit(DoubleRoom)`, `visit(DeluxeRoom)` overloads is the idiomatic, type-safe form.

**Q5: When would you choose Visitor over just adding a method to the base class with a default implementation?**
A: When the class is stable in its type hierarchy but operations are expected to grow frequently and independently (different teams/releases own different operations), and especially when you must avoid re-testing already-shipped classes for every new feature — exactly the scenario in the prompt. If new element types are added far more often than new operations, a simple virtual method on the base class is usually simpler and Visitor would be overkill.

**Q6: How does Visitor relate to the Open/Closed Principle?**
A: It's a textbook embodiment of OCP applied to *operations*: the element hierarchy is closed for modification (you never touch `Room`/`SingleRoom`/etc. again) but the system is open for extension (you can always add a new visitor class for a new operation) — with the trade-off that OCP is *not* preserved in the other direction (adding element types requires modifying every visitor).

## 🔑 Key Takeaway

When a class is at risk of growing indefinitely because *new operations* keep getting bolted onto it, pull those operations out into a separate `Visitor` hierarchy and use double dispatch (`accept(visitor)` → `visitor.visit(this)`) to route to the right type-specific logic — new operations become new classes, and existing, already-tested code is never touched again.
