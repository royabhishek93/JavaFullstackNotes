# Interview Guide: Liskov Substitution Principle (LSP) — Diagnosing and Fixing Violations

## 🗣️ The Interview Scenario

> "You have a `Vehicle` base class with `getNumberOfWheels()` and `hasEngine()`. You've built `Motorcycle` and `Car` as subclasses and everything works. Now you're asked to add a `Bicycle` subclass. A `Bicycle` doesn't have an engine — how do you model that? Show me the naive approach, tell me what breaks and why, and then show me how you'd actually fix the hierarchy so it can't break again — ideally so the compiler catches the mistake, not a runtime crash."

This is a very common LSP follow-up question precisely because it has a "trap" — the naive fix (override and return `null`/throw) looks reasonable but silently breaks client code, and interviewers want to see if you catch that *and* know the structural fix.

## 🏗️ Architect's Explanation (For a New Developer)

The Liskov Substitution Principle says: if `B` is a subclass of `A`, you should be able to swap any `A` object for a `B` object anywhere in your program *without breaking anything*. Imagine a vending machine that accepts "any coin object" — if you introduce a new "coin" that's actually a washer with no monetary value, and the machine crashes or misbehaves because of it, you've violated the "any coin can substitute" contract. LSP violations most often happen when a subclass **removes or weakens a capability** that the parent class promised to always provide, instead of only *adding* new capability on top of it. The fix isn't "be more careful with `if` checks" — it's restructuring the class hierarchy so subclasses can only ever be built from parents whose full capability set they can honestly promise to deliver.

## 📊 Visualize It

```
BROKEN HIERARCHY (violates LSP)
────────────────────────────────
        Vehicle
    ┌──────┼────────────┐
    │      │            │
Motorcycle Car        Bicycle
(has engine (has engine (OVERRIDES hasEngine()
 = true)     = true)     to return null —
                          removes a capability
                          the parent promised)

Client code:
for (Vehicle v : list) {
    print(v.hasEngine().toString());   // NPE when v is a Bicycle!
}
```

```
FIXED HIERARCHY (satisfies LSP)
────────────────────────────────
              Vehicle                          (generic: getNumberOfWheels() only)
           ┌─────┴─────┐
           │           │
      EngineVehicle   Bicycle                  (Bicycle never claims to have an engine)
      (adds: hasEngine())
      ┌─────┴─────┐
      │           │
     Car      Motorcycle

Client code using List<Vehicle>:
  → can only call getNumberOfWheels() — safe for ALL vehicles, including Bicycle

Client code using List<EngineVehicle>:
  → can call hasEngine() — Bicycle simply CANNOT be added to this list
    (compile-time safety, not a runtime null check)
```

## 🔧 Deep Dive: How It Actually Works

### Restating the principle precisely
"If you have a parent class and a child class, you should be able to swap/substitute objects of the child class in place of the parent class objects without breaking the program." Concretely: if `parentRef = new Child1()` works, then reassigning `parentRef = new Child2()` or `new Child3()` should keep the program working (the *output* may differ, but the program should not *break* — no crash, no exception, no violated contract).

### Setting up the violation
Base class `Vehicle`:
- `getNumberOfWheels()` → returns `2` by default.
- `hasEngine()` → returns `true` by default.

Subclasses:
- `Motorcycle extends Vehicle` — doesn't override either method (2 wheels, has engine — inherits defaults as-is).
- `Car extends Vehicle` — overrides `getNumberOfWheels()` to return `4`; doesn't override `hasEngine()` (still `true`).

Client code builds `List<Vehicle>`, adds a `Motorcycle` and a `Car`, iterates, and calls `vehicle.hasEngine().toString()` for each — works fine for both, since `hasEngine()` is a `Boolean` and both objects return `true`.

**The break:** a `Bicycle extends Vehicle` is added, and because a bicycle has no engine, the developer overrides `hasEngine()` to return `null` instead of `false` (since the return type is the boxed `Boolean`, `null` is technically assignable). The moment client code adds a `Bicycle` to that same `List<Vehicle>` and calls `.hasEngine().toString()`, it throws a **`NullPointerException`** — `null.toString()` is invalid. 

The deeper issue: `Bicycle` **reduced** the vehicle's capability set (removed "has an engine" instead of only adding new behavior on top of the parent), and any of the potentially many call sites using this pattern across the codebase would now need scattered `if (vehicle instanceof Bicycle) { /* skip hasEngine() call */ }` checks — a maintenance and safety nightmare, and precisely the kind of downstream fragility LSP is designed to prevent.

### The structural fix — split the hierarchy by capability, not just by "is-a"
The core idea: **the base class should contain only the methods that are truly generic and safe for every single subclass.** Anything that not all subclasses can honestly support should be pulled into an *intermediate* subclass that only the vehicles which genuinely support it extend from.

Concretely:
- `Vehicle` — keeps only `getNumberOfWheels()` (generic, defaults to `2`), since literally every vehicle (including a bicycle) has some number of wheels.
- `EngineVehicle extends Vehicle` — a new intermediate class that introduces `hasEngine()`. This is where the "has an engine" capability now lives.
- `Car extends EngineVehicle` and `Motorcycle extends EngineVehicle` — both genuinely have engines, so they correctly inherit `hasEngine()`.
- `Bicycle extends Vehicle` directly (not `EngineVehicle`) — it only inherits `getNumberOfWheels()`, and `hasEngine()` simply does not exist on it at all.

### Why this fix actually works (three client-code scenarios walked through)
1. **`List<Vehicle>` containing `Motorcycle`, `Car`, and `Bicycle`:** you can only call methods available on `Vehicle` — i.e., `getNumberOfWheels()`. This is completely safe for every element, including `Bicycle`, because `Bicycle` genuinely supports that method. No crash is possible.
2. **Trying to call `.hasEngine()` on a `List<Vehicle>` reference:** this is now a **compile-time error** — `Vehicle` was never declared to have a `hasEngine()` method, so the compiler simply won't let you call it, regardless of what's actually in the list at runtime.
3. **`List<EngineVehicle>`:** you *can* add `Car` and `Motorcycle` (both are `EngineVehicle`s) — but you **cannot add a `Bicycle`** to this list at all, because `Bicycle` is not an `EngineVehicle`. This is enforced by the type system itself; there's no way to accidentally put a bicycle where an engine-vehicle is expected.

The key upgrade from "before" to "after": the bug moved from a **runtime NullPointerException** (caught only if you happen to test that exact path) to a **compile-time type error** (impossible to even build the program incorrectly). This is the gold-standard fix for an LSP violation — restructure inheritance so the type system itself prevents the substitution that would have broken behavior, rather than adding defensive runtime checks.

## 🔥 Real Production Incident & Fix

**The incident:** A fleet-management service modeled `Vehicle` as a base class with `getFuelLevel()`, `refuel()`, and `hasEngine()` (all vehicles defaulted to `hasEngine() → true`, since the original fleet was 100% motorized). Business expansion added electric scooters and, later, manually-pedaled cargo bikes to the fleet. The engineer handling the cargo-bike addition overrode `hasEngine()` on the new `CargoBike` subclass to return `false`, and separately overrode `refuel()` to throw an `UnsupportedOperationException("Cargo bikes cannot be refueled")`.

**How the team noticed:** A nightly batch job that iterated `List<Vehicle>` across the entire fleet and called `refuel()` on every vehicle whose fuel level was below a threshold started crashing every night with an `UnsupportedOperationException`, silently skipping the refuel step for the *rest* of the fleet processed after the crash point in that batch run (since the job wasn't wrapped in per-item exception handling). Ops noticed because several genuinely-motorized vehicles started showing "not refueled in 5+ days" alerts — a symptom several steps removed from the actual root cause, which made it take almost a full day to trace back.

**Root cause:** Classic LSP violation — `CargoBike` was substituted into a `List<Vehicle>` that client code (the nightly batch job) assumed could safely have `refuel()` called on every element, because that's what the `Vehicle` contract implied. `CargoBike` silently broke that contract by throwing instead of just doing nothing meaningful, and the base `Vehicle` class had never been designed with "some vehicles fundamentally cannot be refueled" in mind.

**The fix:** The team split the hierarchy the same way as the canonical fix: `Vehicle` kept only truly universal properties (an identifier, a location); a new `FuelPoweredVehicle extends Vehicle` introduced `getFuelLevel()` and `refuel()`; motorized vehicles moved under `FuelPoweredVehicle`; `CargoBike` and electric scooters (which use `chargeBattery()`, a different capability entirely) stayed as direct `Vehicle` subclasses or moved into their own `BatteryPoweredVehicle` branch. The nightly batch job was updated to iterate `List<FuelPoweredVehicle>` specifically for the refuel step — making it structurally impossible to call `refuel()` on a `CargoBike` ever again.

```
BEFORE: one Vehicle class, capability removed      AFTER: capability-based hierarchy
by override + exception (LSP violation)            ─────────────────────────────────
Vehicle { refuel() }                                Vehicle { id, location }
   ├─ Car (refuel works)                                ├─ FuelPoweredVehicle { refuel() }
   ├─ Truck (refuel works)                              │     ├─ Car, Truck
   └─ CargoBike (refuel() throws!) ← breaks             ├─ BatteryPoweredVehicle { chargeBattery() }
      nightly batch iterating List<Vehicle>             │     └─ ElectricScooter
                                                          └─ CargoBike
                                                     Batch job now iterates
                                                     List<FuelPoweredVehicle> only
                                                     → CargoBike structurally excluded
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why is returning `null` from an overridden method considered worse than the "correct" LSP violation of simply not implementing a capability?**
A: Returning `null` from a method whose declared contract implies a real, usable value (e.g., a `Boolean` that callers will invoke `.toString()` or unbox on) creates a *silent* trap — the code compiles fine and the violation only surfaces at runtime, and often only for specific inputs/subclasses, making it hard to catch in testing unless that exact subclass is exercised.

**Q2: Why not just add an `if (vehicle instanceof Bicycle) continue;` check at every call site instead of restructuring the hierarchy?**
A: That "fixes" each individual call site but doesn't fix the design — every new call site added anywhere in the codebase now needs the same defensive check, and it's easy to forget one, especially as the codebase grows and more people touch it. Restructuring the hierarchy fixes the problem *once*, at the source, and makes the invalid usage impossible to write in the first place (a compile-time guarantee beats a scattered set of runtime guards every time).

**Q3: Does fixing an LSP violation always mean introducing a new intermediate class in the hierarchy?**
A: It's the most common fix when the violation is "some subclasses can't honestly support a capability the parent promises," but other valid fixes exist too — e.g., extracting the varying capability into a separate interface/composed strategy object (similar to how the Strategy pattern decouples behavior from inheritance) rather than deepening the inheritance tree. The key requirement is always the same: never let a subclass claim (via inheritance) a capability it can't actually deliver.

**Q4: How would unit tests have caught this LSP violation before it reached production?**
A: A parametrized/table-driven test that runs the *same* assertions (e.g., "calling `hasEngine().toString()` on every `Vehicle` in a representative list never throws") across every known subclass, run automatically whenever a new subclass is added, would have caught the `Bicycle` case immediately — this is sometimes called a "Liskov substitution test" or contract test.

**Q5: Is the "generic methods stay in the parent, specific methods move to an intermediate subclass" strategy specific to LSP, or does it help with other SOLID principles too?**
A: It directly reinforces the Interface Segregation Principle as well — by not forcing every subclass to inherit methods it can't meaningfully support, you're also preventing forced/irrelevant implementations, which is exactly the failure mode ISP addresses for interfaces.

**Q6: What's the practical signal, while reviewing a pull request, that a new subclass might be about to violate LSP?**
A: Watch for a new subclass that overrides an inherited method just to throw an exception, return `null`/a sentinel value, or make the method a no-op — that's almost always a sign the subclass doesn't actually support the parent's contract and should not be inheriting that method at all; it needs to be pulled out into a narrower intermediate type instead.

## 🔑 Key Takeaway

An LSP violation is fixed not by adding runtime `instanceof` checks around a broken capability, but by restructuring the inheritance hierarchy so that only subclasses which can genuinely support a capability inherit it — turning a possible runtime crash into an impossible-to-write, compile-time-safe program.
