# 🧭 Strategy Design Pattern - Interview Guide
## _15 YOE Architect-Level Conversational Script_

**📗 Difficulty: Beginner** — ideal starting point for a new developer; read this before tackling applied system-design questions.

> _(Companion to `transcript.md` — that file is the raw lecture transcript and is left untouched. This guide re-frames the same content as a scenario-driven interview discussion with diagrams, written the way I'd walk a new joiner through it on a whiteboard.)_

---

**Interviewer**: "Design a `Vehicle` hierarchy where every vehicle can `drive()`, but different vehicles drive very differently. How would you avoid a mess as the number of vehicle types grows?"

**You**: "This is the classic sign that we need the **Strategy Pattern** — whenever behavior varies across siblings in a class hierarchy and plain inheritance starts causing code duplication, Strategy is the fix."

---

## 1. The Problem With Plain Inheritance

```
                 ┌────────────────────┐
                 │      Vehicle         │  drive() -> "normal driving logic"
                 └─────────┬────────────┘
        ┌──────────────────┼───────────────────┐
        ▼                  ▼                    ▼
┌───────────────┐  ┌────────────────┐   ┌────────────────┐
│ PassengerVehicle│  │  SportsVehicle  │   │ OffRoadVehicle  │
│ (uses parent's │  │ overrides drive()│   │ overrides drive()│
│  drive() as-is) │  │ "special logic A"│   │ "special logic A" │  <-- DUPLICATE!
└───────────────┘  └────────────────┘   └────────────────┘
```

**You**: "The moment two *sibling* classes need the **same specialized behavior** that isn't in the parent, you're forced to copy-paste it into both. As the hierarchy grows (Off-road, Sports, Racing, Goods…), the duplication multiplies. That's not scalable — this is a code smell, not just a style preference."

---

## 2. Applying Strategy Pattern

```
┌──────────────────┐        ┌──────────────────────┐
│      Vehicle        │ has-a  │   DriveStrategy (I)    │
│ ------------------ │───────▶│ ------------------------ │
│ - driveStrategy     │        │ + drive()                │
│ + drive() {          │        └───────────┬──────────────┘
│    driveStrategy      │                    │ implements
│      .drive();         │        ┌───────────┼───────────────┐
│ }                     │        ▼           ▼               ▼
└──────────────────┘  ┌─────────┐ ┌───────────┐   ┌─────────────┐
                        │NormalDrive│ │SportsDrive │   │ XyzDrive... │
                        └─────────┘ └───────────┘   └─────────────┘
```

```java
interface DriveStrategy {
    void drive();
}

class NormalDriveStrategy implements DriveStrategy {
    public void drive() { System.out.println("Normal driving capability"); }
}

class SportsDriveStrategy implements DriveStrategy {
    public void drive() { System.out.println("Sports driving capability"); }
}

class Vehicle {
    private final DriveStrategy driveStrategy;   // <-- composition, not inheritance!

    protected Vehicle(DriveStrategy driveStrategy) {  // Constructor Injection
        this.driveStrategy = driveStrategy;
    }

    public void drive() {
        driveStrategy.drive();   // delegate to the strategy object
    }
}

class OffRoadVehicle extends Vehicle {
    OffRoadVehicle() { super(new SportsDriveStrategy()); }  // reuses the SAME strategy object
}

class SportsVehicle extends Vehicle {
    SportsVehicle() { super(new SportsDriveStrategy()); }   // no duplicated logic anymore!
}

class GoodsVehicle extends Vehicle {
    GoodsVehicle() { super(new NormalDriveStrategy()); }
}
```

**You**: "Notice the key design decision: I never hardcode `new NormalDriveStrategy()` *inside* the base `Vehicle` class — that would defeat the purpose. The **child decides which strategy object to inject** via the constructor. This is `Vehicle` HAS-A `DriveStrategy`, not IS-A — composition over inheritance."

---

## 3. Scenario-First Explanation

**Interviewer**: "How do you decide — Strategy Pattern or just override the method?"

**You**: "Ask one question: *are two or more sibling classes going to need the exact same specialized behavior that the parent doesn't provide?* If yes → extract it into a Strategy interface, because tomorrow a third sibling will need it too, and overriding leads to copy-paste. If a behavior is truly unique to ONE child forever, plain override is fine."

---

## 4. Cross Questions

**Q: "Isn't this just Dependency Injection?"**
**A:** "Strategy Pattern is the design pattern; constructor-based Dependency Injection is the *mechanism* I use to wire the strategy into the context object at runtime instead of hardcoding `new XStrategy()`. They work together — DI frameworks like Spring make Strategy trivial to wire via `@Autowired`/`@Qualifier`."

**Q: "How is this different from the Template Method pattern?"**
**A:** "Template Method fixes the *skeleton/order* of steps in the parent and lets children override individual steps. Strategy swaps out an *entire algorithm* as one pluggable object, at runtime, without touching class hierarchy at all — I can even change `vehicle.setStrategy(new XyzDrive())` after construction."

---

## 5. Trade-offs

| Aspect | Inheritance-only | Strategy Pattern |
|---|---|---|
| Code duplication across siblings | High (copy-paste) | None (shared strategy objects) |
| Runtime behavior change | Impossible (fixed at compile time) | Possible (`setStrategy()`) |
| Number of classes | Fewer initially | More (one per algorithm) — but each is small & focused |
| Adding a new behavior | Touch existing base class or many children | Add ONE new strategy class (Open/Closed Principle) |

---

## 6. Senior Trap Questions

**Trap: "Why not just add an `if/else` in `drive()` based on vehicle type?"**
**✅ Senior answer:** "That violates Open/Closed Principle — every time a new drive type is added, I have to modify the tested `Vehicle.drive()` method, risking regression in ALL vehicles. With Strategy, adding `RacingDriveStrategy` means writing ONE new class; `Vehicle` is never touched again."

---

## 🔥 Real-World Production Issue: The Payment Gateway `if/else` Explosion

*In plain English: an ever-growing if/else chain for each new payment type eventually causes one change to accidentally break a completely different, unrelated one.*

**The war story I tell new developers:**

"At a previous company, our `PaymentProcessor.process()` method started as a clean 10-line function. Eighteen months later, after Product added UPI, wallets, EMI, and BNPL, it looked like this — and it caused a P1 incident."

```
┌───────────────────────────────────────────────────────────┐
│  process(PaymentRequest req) {                              │
│    if (req.type == CREDIT_CARD) { ... 40 lines ... }         │
│    else if (req.type == UPI)     { ... 35 lines ... }         │
│    else if (req.type == WALLET)  { ... 50 lines ... }         │
│    else if (req.type == EMI)     { ... 60 lines ... }         │
│    else if (req.type == BNPL)    { ... BUG introduced here! } │◄── deploying BNPL
│  }                                    accidentally broke     │
│                                        the UPI branch due to  │
│                                        a shared mutable var   │
└───────────────────────────────────────────────────────────┘
       ⬇ incident: UPI payments started double-debiting
       for 40 minutes before rollback
```

**Root cause:** every new payment method required editing ONE giant tested/live method. A bug fix for BNPL accidentally shared a mutable local variable used by the UPI branch too — classic blast-radius problem from NOT following Open/Closed Principle.

**The fix — refactor into Strategy Pattern:**

```
┌────────────────┐        ┌────────────────────────┐
│ PaymentProcessor │  has-a │  PaymentStrategy (I)     │
│  (unchanged after│───────▶│  + pay(amount)            │
│   the fix, ever!) │        └───────────┬──────────────┘
└────────────────┘             ┌─────────┼───────────┬───────────┐
                                 ▼         ▼           ▼           ▼
                          CreditCardPay UPIPay   WalletPay   BNPLPay (NEW)
                          (untouched)  (untouched)(untouched) (isolated!)
```

- Each payment type became an isolated `PaymentStrategy` implementation, injected via a `Map<PaymentType, PaymentStrategy>` (Spring bean map).
- Adding BNPL = adding ONE new class + one map entry. **Zero risk to existing UPI/credit card code paths** since they are separate compiled classes with no shared mutable state.
- We also added a unit test per strategy in isolation, which caught the exact bug class that caused the incident, in CI, before it ever reached production again.

**Lesson for a new developer:** "If you see a method that keeps growing an `if/else` or `switch` ladder every sprint, that is your signal to reach for Strategy Pattern *before* the next production incident, not after."

---

## 🎓 Final Tips
1. Use Strategy when **sibling classes need identical specialized behavior** the parent lacks.
2. Composition (HAS-A) beats inheritance (IS-A) for pluggable/varying behavior.
3. Inject the concrete strategy via the **constructor** (Dependency Injection) — never `new` it inside the base class.
4. Growing `if/else`/`switch` ladders in production code = red flag → refactor to Strategy to restore Open/Closed Principle.

Good luck! 🚀
