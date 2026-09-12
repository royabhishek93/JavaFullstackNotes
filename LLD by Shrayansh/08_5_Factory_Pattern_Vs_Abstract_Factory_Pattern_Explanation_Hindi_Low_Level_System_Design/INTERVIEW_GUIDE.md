# 🏭 Factory vs Abstract Factory Pattern - Interview Guide
## _15 YOE Architect-Level Conversational Script_

**📗 Difficulty: Beginner** — ideal starting point for a new developer; read this before tackling applied system-design questions.

> _(Companion to `transcript.md`, left untouched. Scenario-driven whiteboard walkthrough.)_

---

**Interviewer**: "You have `Circle`, `Square`, `Rectangle` shape classes scattered with `new Circle()` calls across 100 places in the codebase. Product now wants a condition-based rule for which shape gets created. How do you avoid touching 100 files?"

**You**: "Whenever object creation logic needs to live in ONE place instead of scattered across the codebase, and especially when it's conditional, that's the **Factory Pattern**."

---

## 1. Factory Pattern — Architecture Diagram

```
┌───────────────┐          ┌────────────────────┐
│  Client Code(s)  │ ──asks──▶│    ShapeFactory        │
│  (100 call-sites) │          │  + getShape(type)         │
└───────────────┘          │      switch(type) {         │
                              │        CIRCLE -> new Circle()│
                              │        SQUARE -> new Square()│
                              │      }                          │
                              └───────────┬──────────────────┘
                                            ▼
                                   ┌────────────────┐
                                   │   Shape (I)        │
                                   │  + draw()             │
                                   └───────┬────────────┘
                              ┌────────────┼─────────────┐
                              ▼            ▼               ▼
                          Circle       Square          Rectangle
```

```java
interface Shape { void draw(); }
class Circle implements Shape    { public void draw() { System.out.println("Circle"); } }
class Square implements Shape    { public void draw() { System.out.println("Square"); } }
class Rectangle implements Shape { public void draw() { System.out.println("Rectangle"); } }

class ShapeFactory {
    static Shape getShape(String type) {
        switch (type) {
            case "CIRCLE": return new Circle();
            case "SQUARE": return new Square();
            default: return new Rectangle();
        }
    }
}

// Client
Shape s = ShapeFactory.getShape("CIRCLE");
s.draw();
```

**You**: "Now if creation logic ever changes — say a new business rule dictates when a `Square` becomes a `Rectangle` — I change it **once**, inside `ShapeFactory`, not at 100 call-sites."

---

## 2. Abstract Factory — "A Factory of Factories"

**Interviewer**: "Now extend it: cars come in two families — Economy and Luxury — and each family has multiple models. Design object creation for this."

**You**: "This is **Abstract Factory** — when you have *multiple related families of products*, and each family needs its own factory, you introduce one more layer: a factory that returns the *right factory* first."

```
┌────────────────────────┐
│  CarFactoryProducer         │
│  + getFactory(type)             │
│      "ECONOMIC" -> EconomicCarFactory │
│      "LUXURY"   -> LuxuryCarFactory   │
└─────────────┬──────────────────┘
              ▼
   ┌─────────────────────┐
   │  CarFactory (I, abstract) │
   │  + getInstance(price)        │
   └──────────┬──────────────────┘
     ┌──────────┴───────────────┐
     ▼                            ▼
┌────────────────────┐   ┌──────────────────┐
│ EconomicCarFactory     │   │ LuxuryCarFactory     │
│  price<X -> EconCar1     │   │  price<Y -> LuxCar1     │
│  else    -> EconCar2     │   │  else    -> LuxCar2     │
└────────────────────┘   └──────────────────┘
```

```java
interface CarFactory { Car getInstance(int price); }

class EconomicCarFactory implements CarFactory {
    public Car getInstance(int price) {
        return price < 500000 ? new EconomicCar1() : new EconomicCar2();
    }
}
class LuxuryCarFactory implements CarFactory {
    public Car getInstance(int price) {
        return price < 5000000 ? new LuxuryCar1() : new LuxuryCar2();
    }
}

class CarFactoryProducer {
    static CarFactory getFactory(String segment) {
        return segment.equals("LUXURY") ? new LuxuryCarFactory() : new EconomicCarFactory();
    }
}

// Client: two-step resolution
CarFactory factory = CarFactoryProducer.getFactory("LUXURY");  // step 1: which family?
Car car = factory.getInstance(6000000);                         // step 2: which model?
```

---

## 3. Scenario-First Explanation: The Key Difference

**You**: "The single sentence I'd give an interviewer: **Factory Pattern returns a PRODUCT. Abstract Factory returns a FACTORY (which then returns a product).** Use plain Factory when you have one family of related objects behind one creation condition. Use Abstract Factory when there are **multiple families**, each requiring its own creation rules, and you want a consistent interface to pick the right family first, then the right member of that family."

---

## 4. Cross Questions

**Q: "When would plain Factory NOT be enough, forcing you to Abstract Factory?"**
**A:** "When object families must stay internally consistent — e.g. a UI toolkit with `WindowsButton`+`WindowsCheckbox` vs `MacButton`+`MacCheckbox`. You never want a `WindowsButton` paired with a `MacCheckbox` by accident. Abstract Factory guarantees the whole family comes from the same factory, so consistency is enforced structurally, not by convention."

**Q: "Doesn't the factory itself become a God-class / violate Single Responsibility if it grows?"**
**A:** "Yes, that's a real risk — a factory with a huge `switch` for 30 product types becomes a maintenance burden. Two common fixes: (1) register creators in a `Map<String, Supplier<Shape>>` populated at startup instead of a switch statement, or (2) split into per-family factories (which is exactly what Abstract Factory does)."

---

## 5. Trade-offs

| Aspect | Simple Factory | Abstract Factory |
|---|---|---|
| Layers of indirection | 1 (client → factory → product) | 2 (client → factory-producer → factory → product) |
| Use case | One family of related products | Multiple related families that must stay consistent |
| Complexity | Low | Higher — only worth it when you truly have multiple families |

---

## 6. Senior Trap Questions

**Trap: "Isn't Abstract Factory just over-engineering? Why not one giant factory with more conditions?"**
**✅ Senior answer:** "A single factory with nested conditions (segment AND price AND model) becomes an unreadable decision tree, and worse, it couples unrelated families' creation logic into one class — a change to Luxury pricing rules risks breaking Economic car creation through shared code paths or accidental typos in a giant switch. Abstract Factory isolates each family's creation logic into its own class, so they can evolve, be tested, and be deployed independently."

---

## 🔥 Real-World Production Issue: The Notification-Channel Factory That Leaked Memory

*In plain English: turning a "factory" into an accidental unbounded cache is how memory leaks sneak into production.*

**The war story:**

"Our notification service had a `NotificationFactory.getSender(channel)` returning `EmailSender`, `SMSSender`, `PushSender` objects. To 'optimize', a developer changed it to cache and reuse Sender objects in a static `Map` inside the factory — a well-intentioned attempt at object pooling."

```
┌─────────────────────────────────────────────────────┐
│ class NotificationFactory {                              │
│   static Map<String, Sender> cache = new HashMap<>();      │
│   static Sender getSender(String channel, String userToken){│
│     return cache.computeIfAbsent(channel + userToken,        │  ◄── BUG: keyed by
│         k -> new Sender(channel, userToken));                 │      per-USER token!
│   }                                                             │
│ }                                                                │
└─────────────────────────────────────────────────────┘
        ⬇
   Every unique user created a NEW cached entry that was NEVER evicted
   → static Map grew unbounded → OutOfMemoryError after ~3 days in prod
```

**Root cause:** the "factory" was mutated into an implicit, unbounded cache keyed by unpredictable, ever-growing keys (per-user tokens) — a subtle but very common production bug when engineers blur the line between "Factory Pattern" (stateless creation) and "Object Pool Pattern" (managed, bounded reuse) without realizing they picked up the drawbacks of pooling (memory growth) without its safeguards (bounded size, eviction).

```
   ASCII: Heap growth over 3 days
   Memory
   │                                       ╱▲ OOM crash
   │                                   ╱────
   │                             ╱────
   │                       ╱────
   │                 ╱────
   │            ╱────
   └──────────────────────────────────────────▶ time
        (unbounded cache growth, one entry per user token, no TTL/eviction)
```

**The fix:**
- Reverted `NotificationFactory` to be a **pure, stateless factory** — `new` a fresh `Sender` per call, since `Sender` objects were lightweight (no actual pooling was needed).
- Where genuine reuse of expensive resources was needed (e.g. pooled SMTP connections), used a proper **bounded** Object Pool Pattern with max-size + eviction, and a `Singleton` pool manager — never an unbounded static `Map` inside a "Factory".

**Lesson for a new developer:** "Factory Pattern's job is to decide *which class to instantiate*, not to manage object lifetime/caching. The moment you introduce caching/reuse inside a factory, you've actually started building an Object Pool — go do that deliberately, with bounds and eviction, rather than accidentally growing an unbounded cache."

---

## 🎓 Final Tips
1. Factory = one method decides *which concrete class* to instantiate, centralizing that decision.
2. Abstract Factory = a factory that returns the *right factory* first, for consistent families of related objects.
3. Don't let a Factory's `switch`/`if-else` become a God-method — extract per-family factories or a registration map.
4. Never blur Factory (stateless creation) with Object Pool (bounded, managed reuse) — that's how memory leaks sneak into production.

Good luck! 🚀
