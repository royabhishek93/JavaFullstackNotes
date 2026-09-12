# Interview Guide: Strategy Design Pattern

## 🗣️ The Interview Scenario

> "You're modeling different vehicle types — `PassengerVehicle`, `OffRoadVehicle`, `SportyVehicle` — all extending a `Vehicle` base class with a `drive()` method. `PassengerVehicle` is happy with the base class's normal drive behavior, but `OffRoadVehicle` and `SportyVehicle` both need a special, aggressive drive algorithm — and it happens to be *identical* for both. Right now you're duplicating that special drive logic in two separate subclasses because the base class doesn't have it. As the system grows (more vehicle types, more capabilities like display, fuel handling), how do you redesign this so you stop duplicating code, without piling everything into the base class either?"

This is the canonical setup for the Strategy pattern in an LLD interview — a plain inheritance hierarchy that starts leaking duplicate code across sibling subclasses because they need shared-but-not-universal behavior.

## 🏗️ Architect's Explanation (For a New Developer)

Normal inheritance works great when a capability genuinely belongs to *everyone* below a certain point in the hierarchy — you put it in the base class and every child gets it for free. The trouble starts when only **some siblings** at the same level need the *same* special behavior, but that behavior doesn't belong to *all* children, so it can't live in the shared base class. If you leave it there, you're forcing behavior onto children that don't want it (or you'd be violating LSP/ISP); if you don't, each sibling that needs it has to write (and duplicate) its own copy.

The Strategy pattern's fix: **stop putting "how to do X" inside the class hierarchy at all.** Instead, pull "how to drive" out into its own family of interchangeable objects (a `DriveStrategy` interface with implementations like `NormalDriveStrategy`, `SportDriveStrategy`), and give the `Vehicle` class a *reference* to whichever strategy object it needs — supplied from the outside via the constructor. Now `Vehicle` doesn't contain any single "the one true way to drive" — it just knows "I `HAS-A` `DriveStrategy`, and whatever object is plugged in, I'll delegate to it." Two completely unrelated vehicle subclasses that both need the "sporty" behavior simply get handed the *same* `SportDriveStrategy` object — zero duplication, and adding a brand-new drive behavior later means writing one new class, not touching the vehicle hierarchy at all.

## 📊 Visualize It

```
WITHOUT STRATEGY (inheritance-only — duplicated code)
──────────────────────────────────────────────────────
                    Vehicle
                 drive() { normal drive algorithm }
        ┌───────────┬────────────┬───────────────┐
        │            │            │               │
PassengerVehicle OffRoadVehicle SportyVehicle  GoodsVehicle
(uses parent's   drive() {      drive() {      (uses parent's
 normal drive —   special code   special code    normal drive)
 no override)     A }            A }  ← DUPLICATE of OffRoad's code!
```

```
WITH STRATEGY PATTERN (composition — zero duplication)
────────────────────────────────────────────────────────
        <<interface>>
        DriveStrategy
        + drive()
       ▲      ▲       ▲
       │      │       └───────────────┐
NormalDriveStrategy  SportDriveStrategy   (future: XYZDriveStrategy...)
                            ▲
                            │ implements
                            │
     Vehicle  ── HAS-A ──►  DriveStrategy driveObj     (composition, not inheritance)
        │
        │ constructor injection: passes the RIGHT strategy object
   ┌────┴─────┬───────────────┬───────────────┐
PassengerVehicle OffRoadVehicle SportyVehicle  GoodsVehicle
(injects         (injects       (injects        (injects
 NormalDriveStrategy) SportDriveStrategy) SportDriveStrategy) NormalDriveStrategy)
                       ▲ same object type reused, no duplicate code ▲
```

## 🔧 Deep Dive: How It Actually Works

### The problem, precisely
A `Vehicle` base class has a `drive()` method containing "normal drive capability" logic. Subclasses `PassengerVehicle`, `OffRoadVehicle`, and `SportyVehicle` all extend `Vehicle` (classic IS-A relationships — `SportyVehicle is a Vehicle`). `PassengerVehicle` never overrides `drive()` because the parent's normal behavior is exactly what it needs. But `OffRoadVehicle` needs special drive capability, so it overrides `drive()` with its own implementation; `SportyVehicle` independently needs the *same kind* of special capability and also overrides `drive()` with essentially identical logic.

This is fine as a one-off, but the pattern of the problem is: **whenever multiple sibling subclasses at the same level need identical behavior that the base class doesn't provide, you get code duplication** — and it compounds as the system grows (more features like `display()`, more subclasses added over time), because each new sibling requiring an existing "special" behavior has to re-implement it rather than reuse it.

### The Strategy-based redesign, step by step
1. **Extract the varying behavior into its own interface.** Create `DriveStrategy` with a single `drive()` method.
2. **Create one implementation class per distinct behavior.** `NormalDriveStrategy implements DriveStrategy` (contains the normal-drive algorithm); `SportDriveStrategy implements DriveStrategy` (contains the special/aggressive-drive algorithm). Any future new behavior (e.g., an "XYZ" drive mode) just becomes another implementation class — the set of strategies is open-ended and doesn't touch existing code.
3. **Change `Vehicle` from "owns the algorithm" to "owns a reference to an algorithm object."** `Vehicle` now declares `private DriveStrategy driveObj;` — this is a **HAS-A relationship** (composition), replacing what used to be behavior baked directly into the class via inheritance.
4. **Never `new` a specific strategy inside `Vehicle` itself.** If `Vehicle`'s constructor did `driveObj = new NormalDriveStrategy()` directly, every `Vehicle` would be hard-coded to normal driving, defeating the purpose. Instead, `Vehicle` exposes a constructor that *accepts* a `DriveStrategy` object from the caller — this is **constructor injection**: `Vehicle(DriveStrategy obj) { this.driveObj = obj; }`.
5. **`drive()` simply delegates.** `Vehicle.drive()` becomes: `driveObj.drive();` — it doesn't know or care *which* concrete strategy it's holding; it just calls the interface method.
6. **Each subclass decides which strategy to inject, via its own constructor calling `super(...)`.** `OffRoadVehicle`'s constructor calls `super(new SportDriveStrategy())`; `SportyVehicle`'s constructor *also* calls `super(new SportDriveStrategy())` — the same strategy class, reused, zero duplicated drive logic; `GoodsVehicle`'s constructor calls `super(new NormalDriveStrategy())`.

### Why this solves the scaling problem
Before, code reusability broke down specifically when sibling subclasses (not connected by direct inheritance to each other) needed the same non-universal behavior. After the refactor, "needing the same behavior" simply means "constructing with the same strategy object" — there's no relationship between `OffRoadVehicle` and `SportyVehicle` needed at all; they both just happen to be configured with `SportDriveStrategy`. As the system grows — more vehicle types, more behavioral variants — you only ever add new `DriveStrategy` implementations (extension) instead of duplicating logic across a widening set of subclasses.

### When to reach for this pattern (the practical trigger)
The signal to use Strategy: you're building a parent/child hierarchy, and you notice that **certain children, which aren't otherwise special-cased, need functionality that isn't present in the base class — and more than one sibling needs the exact same functionality.** That's the moment plain inheritance stops scaling and composition-via-Strategy takes over.

## 🔥 Real Production Incident & Fix

**The incident:** A ride-hailing backend modeled fare calculation using inheritance: a `Ride` base class with `calculateFare()`, and subclasses `StandardRide`, `PoolRide`, `PremiumRide`, `AirportRide`. When `PremiumRide` needed a "surge-aware, minimum-fare-guaranteed" calculation, an engineer overrode `calculateFare()` in `PremiumRide` with the new logic. Three months later, `AirportRide` needed the exact same surge-aware, minimum-fare-guaranteed calculation (airport rides during peak hours had the identical business rule) — a different engineer, unaware of the `PremiumRide` override, copy-pasted the logic into `AirportRide.calculateFare()` rather than reusing it, because there was no shared home for that logic outside of directly copying a sibling subclass's override.

**How the team noticed:** A pricing bug was reported for `PremiumRide` — a rounding fix for the minimum-fare guarantee was applied, but `AirportRide` fares stayed wrong for two more weeks because nobody remembered (or knew) that the same logic existed, duplicated, in a second file. It was caught during a code review for an unrelated fare feature, when the reviewer noticed nearly identical fare-calculation blocks in two different `Ride` subclasses and flagged it as suspicious duplication.

**Root cause:** Fare-calculation behavior that was shared by *some but not all* sibling `Ride` subclasses had nowhere to live except being copy-pasted into each subclass that needed it, because the base `Ride` class only contained the *standard* fare logic — exactly the same structural problem as `OffRoadVehicle`/`SportyVehicle` both needing special drive behavior not present in `Vehicle`.

**The fix:** The team extracted a `FareStrategy` interface with `calculateFare(RideContext ctx)`, implemented `StandardFareStrategy` and `SurgeAwareMinimumFareStrategy`. `Ride` was changed to hold a `FareStrategy` via constructor injection instead of overriding `calculateFare()` per subclass. `PremiumRide` and `AirportRide` both now construct with `new SurgeAwareMinimumFareStrategy()` — the same object type, the fix applied once benefits both instantly, and any future ride type needing the same pricing rule just injects the same strategy with no code duplication.

```
BEFORE: fare logic duplicated across siblings   AFTER: Strategy pattern — shared, injected
──────────────────────────────────────────────  ─────────────────────────────────────────
Ride { calculateFare() }                        <<interface>> FareStrategy
  ├─ StandardRide (uses parent's default)          ├─ StandardFareStrategy
  ├─ PoolRide (uses parent's default)               └─ SurgeAwareMinimumFareStrategy
  ├─ PremiumRide.calculateFare() { logic A }
  └─ AirportRide.calculateFare() { logic A }      Ride HAS-A FareStrategy (constructor-injected)
       ↑ COPY-PASTED, diverged over time            ├─ PremiumRide → SurgeAwareMinimumFareStrategy
                                                      └─ AirportRide → SurgeAwareMinimumFareStrategy
                                                           (same object type, one fix covers both)
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: How is the Strategy pattern different from just using method overriding (plain inheritance)?**
A: Method overriding ties a behavior variant permanently to a specific subclass at compile time via the class hierarchy, and forces any sibling needing the same variant to either inherit from that subclass (usually wrong, since they aren't conceptually the same type) or duplicate the code. Strategy decouples the behavior into its own object family entirely, so *any* class — regardless of its position in the inheritance hierarchy — can be configured with any strategy object at runtime via composition, without needing to share a common subclass.

**Q2: Why use constructor injection for the strategy object instead of just calling `new NormalDriveStrategy()` directly inside the `Vehicle` base class?**
A: If `Vehicle` hard-codes which strategy it creates, every `Vehicle` (and every subclass) is stuck with that one behavior — you'd lose the entire point of the pattern, which is letting each subclass (or even each individual object, if needed) choose its own behavior independently. Constructor injection keeps the decision external and flexible, and also makes the class easily unit-testable (you can inject a mock/fake strategy in tests).

**Q3: Can two different objects of the same class use two different strategies at runtime, not just two different subclasses?**
A: Yes — since the strategy is just a field set via the constructor (or a setter), two instances of the exact same class could be constructed with different `DriveStrategy` objects if the use case calls for per-instance configurability, not just per-subclass configurability. This is more flexible than inheritance, which fixes behavior at the class level, not the instance level.

**Q4: What's the relationship notation between `Vehicle` and `DriveStrategy` called, and why does it matter?**
A: It's a HAS-A relationship (composition/aggregation, specifically "Vehicle has-a DriveStrategy"), as opposed to the IS-A relationship used between `Vehicle` and its subclasses. It matters because Strategy is fundamentally about favoring composition over inheritance for *behavior* that varies independently of the object's core identity/type.

**Q5: How would you extend this design if a brand-new drive behavior needs to be added six months from now?**
A: You add one new class implementing `DriveStrategy` (e.g., `AutonomousDriveStrategy`) — no existing `Vehicle` subclass, no existing strategy class, and no client code needs to change at all. This is the Open/Closed Principle in action: the system is open for extension (new strategies) but closed for modification (nothing existing is touched).

**Q6: Isn't this the same as the Strategy pattern being confused with the State pattern? How do you tell them apart in an interview?**
A: Structurally they look almost identical (a context class holding a reference to an interface with multiple implementations), but the *intent* differs: Strategy is about the *client/caller* choosing an algorithm/behavior once (e.g., at construction) and it typically doesn't change based on the object's own internal condition; State is about the object's *own internal state* determining which behavior implementation is active, and the object itself often triggers transitions between states as it operates (e.g., a vending machine moving from `Idle` to `HasMoney` to `Dispensing`).

## 🔑 Key Takeaway

Reach for the Strategy pattern the moment you notice sibling subclasses duplicating identical logic because a shared base class can't hold it without over-generalizing — extract that logic into an interchangeable, constructor-injected strategy object instead of letting inheritance force you into copy-pasted code.
