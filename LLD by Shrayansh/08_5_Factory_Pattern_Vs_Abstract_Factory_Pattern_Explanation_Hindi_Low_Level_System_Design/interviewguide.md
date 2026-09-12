# Interview Guide: Factory Pattern vs. Abstract Factory Pattern

## 🗣️ The Interview Scenario

> "You're building a payments module that needs to instantiate different `PaymentGateway` implementations — `RazorpayGateway`, `StripeGateway`, `PaypalGateway` — based on a config flag. Six months later, your company also needs to support two *families* of gateways: 'domestic' (Razorpay, UPI) and 'international' (Stripe, PayPal), each with its own notification sender and receipt formatter that must stay consistent with each other. Walk me through how you'd design the object-creation logic for both the initial requirement and the evolved one, and name the patterns you're applying."

This is a classic bait: most candidates jump straight into "Factory Pattern" for both halves of the question and never notice that the second half — needing *matched families* of related objects — is a fundamentally different problem that a plain Factory can't cleanly solve.

## 🏗️ Architect's Explanation (For a New Developer)

Think of the **Factory Pattern** as a vending machine with one slot. You press a button (pass a condition/key), and it hands you exactly one product. It exists to solve a single, very common pain: *"I have a bunch of `if/else` or `switch` blocks scattered across my codebase, all deciding which class to instantiate based on the same condition."* Every time that decision logic is duplicated, you have a bug waiting to happen — if the condition changes, you now have to hunt down every copy. The Factory Pattern centralizes that decision into **one class** with **one method** (commonly `getObject(type)` or similar), so the rest of the code just asks the factory for what it needs and never has to know *how* the decision is made.

Now imagine you don't have one vending machine — you have an entire vending *machine showroom* organized by category. One counter only gives you "luxury" products (Mercedes, BMW), another counter only gives you "ordinary" products (Maruti, Honda). That showroom is the **Abstract Factory Pattern**. It's a "factory of factories": instead of returning one product directly, it returns the *right factory* for a category, and that factory in turn returns the actual product. You reach for this only when you have **multiple families of related products**, and you want client code to pick a family once and then trust that everything it creates from that family is compatible/grouped correctly.

The one-line distinction to say out loud in an interview:
> **Factory Pattern** creates **one type of object** based on a condition. **Abstract Factory Pattern** creates a **family of related factories**, each of which creates a group of related objects.

## 📊 Visualize It

**Factory Pattern** — one factory, condition-based dispatch to concrete products:

```
        +---------------+
        |    Shape      |  <<interface>>
        +---------------+
        | +draw()       |
        +---------------+
              ▲     ▲
      implements     implements
              |          |
     +--------------+  +-------------+
     |  Rectangle   |  |   Circle    |
     +--------------+  +-------------+
     | +draw()      |  | +draw()     |
     +--------------+  +-------------+

              ▲  creates
              |
     +----------------------+
     |     ShapeFactory      |
     +----------------------+
     | +getShape(type):Shape |   switch(type) {
     +----------------------+     case "RECTANGLE" -> new Rectangle();
                                   case "CIRCLE"    -> new Circle(); }
```

**Abstract Factory Pattern** — a factory of factories, grouping related products by family:

```
                +-----------------------+
                |   VehicleFactory       |  <<interface>>
                +-----------------------+
                | +getVehicle(): Vehicle |
                +-----------------------+
                     ▲            ▲
                     |            |
        +--------------------+  +----------------------+
        |  LuxuryFactory     |  |  OrdinaryFactory      |
        +--------------------+  +----------------------+
        | returns: Mercedes, |  | returns: Maruti,      |
        |          BMW       |  |          Honda        |
        +--------------------+  +----------------------+

   Client:  VehicleFactory f = getFactory("LUXURY");   // factory-of-factories decision
            Vehicle v = f.getVehicle();                // family-specific product
```

## 🔧 Deep Dive: How It Actually Works

### Factory Pattern — step by step

1. **The problem it removes**: duplicated conditional object-creation logic. As the transcript puts it — if 50 places in your codebase need "give me object X if condition A, object Y if condition B," you'll eventually have 50 copies of that same `if/else`, and any change means editing all 50.
2. **Structure**:
   - A common interface/abstract type — e.g., `Shape` with a `draw()` method.
   - Concrete implementations — `Rectangle implements Shape`, `Circle implements Shape`, each overriding `draw()`.
   - A single `ShapeFactory` class with one method, e.g. `getShape(String shapeType)`, containing the `switch`/`if-else` that maps a key to a `new Concrete...()` call.
3. **Client usage**: the client never writes `new Rectangle()` directly. It calls `shapeFactory.getShape("CIRCLE")` and gets back a `Shape` reference. This is the essence of the **Dependency Inversion**-flavored benefit: the client only depends on the `Shape` interface, not on concrete classes.

```java
interface Shape {
    void draw();
}

class Rectangle implements Shape {
    public void draw() { System.out.println("Rectangle"); }
}

class Circle implements Shape {
    public void draw() { System.out.println("Circle"); }
}

class ShapeFactory {
    Shape getShape(String shapeType) {
        switch (shapeType) {
            case "CIRCLE":    return new Circle();
            case "RECTANGLE": return new Rectangle();
            default: throw new IllegalArgumentException("Unknown shape: " + shapeType);
        }
    }
}

// Client
ShapeFactory shapeFactory = new ShapeFactory();
Shape s = shapeFactory.getShape("CIRCLE");
s.draw();
```

### Abstract Factory Pattern — step by step

1. **When you need it**: when you have **more than one factory**, and each factory is responsible for a **logically grouped family** of products — not just one product type.
2. **Structure** (built directly on top of the Factory idea):
   - The real products (e.g. `Mercedes`, `BMW`, `Maruti`, `Honda`) each implement a common `Vehicle` interface, exactly like in the simple Factory.
   - Instead of *one* factory containing all the `if/else` logic, you split it: `LuxuryFactory` only ever returns luxury vehicles; `OrdinaryFactory` only ever returns ordinary vehicles. Both implement a common `VehicleFactory` interface.
   - On top of *that*, you add one more level: a factory that decides **which factory** to hand back — this is the "factory of factories." Given some input (e.g., "LUXURY" vs "ORDINARY"), it returns a `VehicleFactory` reference (either `LuxuryFactory` or `OrdinaryFactory`).
   - The client calls the top-level factory once to get the right family's factory, and from then on only talks to that specific factory to get consistent, family-correct products.
3. **Key insight from the transcript**: the internal logic of each concrete factory (`LuxuryFactory.getVehicle()`) is *exactly* the same shape as a simple `ShapeFactory` — it's still condition-based dispatch. What's new is the **extra layer of indirection** that groups multiple such factories under one selection mechanism.

```java
interface Vehicle { String name(); }
class Mercedes implements Vehicle { public String name() { return "Mercedes"; } }
class BMW implements Vehicle { public String name() { return "BMW"; } }
class Maruti implements Vehicle { public String name() { return "Maruti"; } }
class Honda implements Vehicle { public String name() { return "Honda"; } }

interface VehicleFactory { Vehicle getVehicle(String key); }

class LuxuryFactory implements VehicleFactory {
    public Vehicle getVehicle(String key) {
        return key.equals("MERCEDES") ? new Mercedes() : new BMW();
    }
}

class OrdinaryFactory implements VehicleFactory {
    public Vehicle getVehicle(String key) {
        return key.equals("MARUTI") ? new Maruti() : new Honda();
    }
}

// The "factory of factories"
class VehicleFactoryProducer {
    static VehicleFactory getFactory(String category) {
        return category.equals("LUXURY") ? new LuxuryFactory() : new OrdinaryFactory();
    }
}

// Client
VehicleFactory factory = VehicleFactoryProducer.getFactory("LUXURY");
Vehicle v = factory.getVehicle("BMW");
```

### The decision rule to state in an interview

- One product type, one condition → **Factory Pattern**.
- Multiple product *families*, each family needing its own dedicated creation logic, selected via an outer dispatch → **Abstract Factory Pattern**.

## 🔥 Real Production Incident & Fix

**What broke**: A fintech backend had a `NotificationSender` interface with `EmailSender`, `SmsSender`, and `PushSender` implementations, created via a single `NotificationFactory.get(String channel)` — a textbook simple Factory. It worked fine for months. Then the company launched a second product line — a "premium" tier with its own SLA-backed vendors (a dedicated transactional email vendor, a priority SMS gateway, a different push provider) that had to be used *together* as a matched set, because the premium SMS gateway embedded a tracking token that only the premium push provider could correlate for delivery analytics.

Engineers, under deadline pressure, took the fastest path: they added a `boolean isPremium` parameter to the existing `NotificationFactory.get(channel, isPremium)` method and doubled the `switch` cases inline (`"EMAIL_PREMIUM"`, `"SMS_PREMIUM"`, etc.).

**How the team noticed**: Two weeks post-launch, the analytics dashboard showed a spike in "orphaned" delivery-tracking events — premium SMS messages going out with premium tracking tokens, but ~15% of the corresponding push notifications came from the *regular* `PushSender` (missing the correlation code), because one call site in the referral-flow service had been updated to pass `isPremium=true` for SMS but a copy-pasted second call site nearby still hard-coded `isPremium=false` for the paired push call. The bug was found via a metrics anomaly (correlation-rate drop in the analytics pipeline), not a crash — the kind of bug that's invisible in code review because both branches "worked," they just picked from inconsistent families.

**Root cause**: The single Factory's flat `switch` had no structural guarantee that "premium SMS" and "premium push" were requested together — every call site independently chose a channel and a tier flag, so nothing stopped a developer from mixing tiers by mistake. This is precisely the failure mode Abstract Factory prevents: it makes an inconsistent mix *impossible to express* because the client only ever holds one factory reference for one family.

**The fix**: The team refactored to an Abstract Factory. A `NotificationFactoryProvider.getFactory(tier)` returns either a `StandardNotificationFactory` or a `PremiumNotificationFactory`. Each concrete factory exposes `getEmailSender()`, `getSmsSender()`, `getPushSender()` — all guaranteed to come from the same tier because they come from the *same object*. Call sites were refactored to fetch **one factory** per user session and pull every channel sender from it, making the "matched family" invariant impossible to violate by construction rather than relying on every developer remembering to pass the same flag everywhere.

```
BEFORE (flat factory, tier as a stray parameter):        AFTER (Abstract Factory, tier baked into the factory):

 caller A --isPremium=true--> get(SMS)  --> PremiumSMS     caller ---> getFactory(PREMIUM) --> PremiumFactory
 caller B --isPremium=false-> get(PUSH) --> StandardPush                                        |-> getSms()  -> PremiumSMS
      (mismatch possible, no shared context)                                                     |-> getPush() -> PremiumPush
                                                                                                   (always matched)
```

## ❓ Likely Interview Follow-Up Questions & Answers

1. **"Isn't Abstract Factory just a Factory that returns Factories? Why not just add more parameters to one Factory instead?"**
   Technically you *could* keep adding parameters, but that couples every product family into one class and one method, making it grow indefinitely and increasing the chance of picking inconsistent members from different families (as in the incident above). Abstract Factory isolates each family behind its own factory, so once you select a family, everything you create from it is structurally guaranteed to belong together.

2. **"What design principle is Factory Pattern an application of?"**
   It's a direct application of the **Dependency Inversion Principle** and, more broadly, "program to an interface, not an implementation." Client code depends only on the abstract product type (`Shape`, `Vehicle`) and the factory's return type — never on `new ConcreteClass()` — so swapping or adding implementations doesn't touch client code.

3. **"How would you extend the simple Factory example to support a new shape, say Triangle, without breaking existing clients?"**
   Add a new `Triangle implements Shape` class, add one new `case` in `ShapeFactory.getShape()`, and nothing else changes — existing client code that calls `factory.getShape(type)` and depends on the `Shape` interface is completely unaffected. This is the Open/Closed Principle in action: open for extension (new case, new class), closed for modification of client code.

4. **"When would Abstract Factory be overkill?"**
   When you only ever have one dimension of variation (one family of products) — adding the extra factory-of-factories layer for a single family just adds indirection with no benefit. Only introduce it once you actually have two or more product families that must be created and used consistently as a set.

5. **"How does this relate to Spring's `BeanFactory` / `ApplicationContext`?"**
   Spring's `BeanFactory` is essentially a giant Factory Pattern: you ask it for a bean by name/type, and it decides how to construct and wire it, hiding `new` calls from your code. When Spring needs to choose between multiple *profiles* of configuration (e.g., dev vs. prod beans, each wiring a consistent group of related beans), that layered selection is conceptually an Abstract Factory.

6. **"What's a real failure mode of the plain Factory Pattern itself, even without the 'family' problem?"**
   If the factory's `switch`/`if-else` keeps growing as new types are added, the factory class itself becomes a maintenance bottleneck and violates the Open/Closed Principle at the factory level (though not at the client level). Some teams solve this with a registry map (`Map<String, Supplier<Shape>>`) populated at startup instead of a hardcoded `switch`.

## 🔑 Key Takeaway

Factory Pattern centralizes "which single object do I create based on a condition"; Abstract Factory centralizes "which *entire family* of related objects do I create together, guaranteed consistent." If you only remember one sentence for the interview: **reach for Abstract Factory only when you have more than one factory and each factory must return a self-consistent group of products.**
