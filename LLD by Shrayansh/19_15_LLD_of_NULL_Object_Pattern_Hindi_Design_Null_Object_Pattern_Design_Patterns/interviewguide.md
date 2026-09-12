# Interview Guide: Null Object Pattern

## 🗣️ The Interview Scenario

> "Take a look at this codebase. Nearly every method that consumes an object of type `Vehicle` starts with `if (vehicle != null)` before it does anything. Product managers keep adding new vehicle types and every new integration point re-adds this same null check. How would you redesign this so we structurally eliminate the need for null checks scattered across the codebase, without ever risking a `NullPointerException`?"

This question was reported by a viewer as an actual interview question — it's short, but it tests whether you understand that null checks are a *design smell*, not just an inconvenience.

## 🏗️ Architect's Explanation (For a New Developer)

Here's the everyday problem: in any object-oriented language, when you call a method on an object reference that turns out to be `null`, you get a runtime crash (`NullPointerException` in Java). So defensively, developers write:

```java
if (vehicle != null) {
    System.out.println("Seating capacity: " + vehicle.getSeatingCapacity());
    System.out.println("Fuel tank capacity: " + vehicle.getFuelTankCapacity());
}
```

This looks harmless once. But imagine a large, real production codebase — this same `!= null` guard gets copy-pasted into **every method, every class**, wherever this object might flow through. That's not just ugly, it's a maintenance tax paid over and over, and it's exactly the kind of thing a Staff Engineer notices during code review and says "we can eliminate this entire category of check."

The **Null Object Pattern's** core idea, stated plainly: **"a null object replaces the null return type."** Instead of a method returning `null` when there's nothing to give back, it returns a special, harmless object — one that implements the exact same interface as the "real" objects, but whose methods simply return safe/default values (e.g., `0` for a capacity) instead of doing meaningful work. Because the *type* returned is always non-null and always implements the shared interface, **calling code never needs to null-check again** — it just calls the method on whatever it received.

Analogy: think of it like a "guest user" account on a website instead of `user = null`. A guest user object can still respond to `getName()` (returns "Guest") or `getPermissions()` (returns an empty list) without your page-rendering code ever crashing from `null.getName()`.

## 📊 Visualize It

### Class structure

```
        <<interface>> Vehicle
        + getSeatingCapacity()
        + getTankCapacity()
             ▲        ▲        ▲
             │        │        │
        ┌────┘        │        └──────┐
        │              │                │
      Car            Bike          NullVehicle
  (real data)     (real data)   (Null Object — safe defaults)
  seat=5,tank=45   seat=2,tank=15   seat=0, tank=0
```

- `Vehicle` is the common interface/abstract type.
- `Car` and `Bike` are ordinary concrete implementations returning real, meaningful data.
- `NullVehicle` is the **Null Object** — it also implements `Vehicle`, but every method returns a harmless default (`0`, empty string, empty list, no-op) instead of throwing or requiring a null check.

### Before vs. after call-site behavior

```
BEFORE (defensive null-checking everywhere):
   getVehicle() ──► returns Car | Bike | null
                          │
                    caller MUST check:
                    if (vehicle != null) { ... }
                    else { skip / branch logic }

AFTER (Null Object Pattern):
   getVehicle() ──► always returns Car | Bike | NullVehicle
                          │
                    caller NEVER checks:
                    vehicle.getSeatingCapacity()   // always safe
                    (if it's NullVehicle, this just returns 0)
```

## 🔧 Deep Dive: How It Actually Works

### 1. The problem, demonstrated with code

```java
// Unsafe: crashes with NullPointerException if vehicle is null
Vehicle vehicle = getVehicle();
System.out.println("Seating capacity " + vehicle.getSeatingCapacity());
System.out.println("Fuel tank capacity " + vehicle.getTankCapacity());
```

The "correct-but-ugly" fix everyone reaches for first:
```java
// Works, but this guard has to be repeated at every call site,
// in every method, across the whole codebase
if (vehicle != null) {
    System.out.println("Seating capacity " + vehicle.getSeatingCapacity());
    System.out.println("Fuel tank capacity " + vehicle.getTankCapacity());
}
```
The transcript's key observation: in a large real project, "think about how many objects we create... how many null checks get added in every method of every class." That widespread, repeated `!= null` scaffolding is itself the problem to be engineered away — not accepted as a fact of life.

### 2. Applying the pattern

Step 1 — Define the shared interface:
```java
public interface Vehicle {
    int getTankCapacity();
    int getSeatingCapacity();
}
```

Step 2 — Real implementation(s) return meaningful data:
```java
public class Car implements Vehicle {
    public int getTankCapacity()   { return 45; }
    public int getSeatingCapacity(){ return 5;  }
}
```

Step 3 — The Null Object implements the same interface, but returns safe defaults:
```java
public class NullVehicle implements Vehicle {
    public int getTankCapacity()    { return 0; }   // "replace null with 0"
    public int getSeatingCapacity() { return 0; }
}
```

Step 4 — Whatever factory/lookup method used to be able to return `null` now returns `NullVehicle` instead:
```java
public Vehicle getVehicle(String type) {
    if (type.equals("car"))  return new Car();
    if (type.equals("bike")) return new Bike();
    return new NullVehicle(); // instead of: return null;
}
```

Step 5 — Calling code is simplified everywhere, permanently:
```java
Vehicle vehicle = getVehicle("unknown");
System.out.println(vehicle.getSeatingCapacity()); // prints 0, no crash, no if-check
```

### 3. Why this is safe and why it matters

- The instructor's framing: **"no need to put this check [`!= null`] because we have replaced null with... nothing."** The check becomes structurally unnecessary because the type system guarantees you always hold *some* implementer of `Vehicle` — never a bare `null`.
- Demonstrated failure mode it prevents: if you *didn't* apply the pattern and a method returned `null` (e.g., a `getBike()` variant that returns `null` instead of a real bike), calling `.getSeatingCapacity()` on it throws `NullPointerException` immediately — "yeh null pointer exception throw kar dega" (this will throw a null pointer exception), shown explicitly by removing the null-object substitution.
- Practical framing for real systems: "this is a very real problem — actually if you work in a company and look at your system, on every method... you'll find this null pointer object... this is used in real life very often."

### 4. Trade-off to mention in an interview

The Null Object still has to make a semantic choice about what a "safe default" means (0? empty string? no-op logging?), and that choice must never be mistaken for real data downstream. If a caller needs to explicitly distinguish "no vehicle exists" from "a vehicle exists with 0 seats," you need an additional signal (e.g., an `isNull()` marker method, or a distinct type check) — the pattern trades away null-checks in exchange for callers trusting default values are contextually harmless.

## 🔥 Real Production Incident & Fix

**What broke:** A logistics company's fleet-management dashboard displayed vehicle stats (seating capacity, fuel tank) pulled from a `VehicleRepository.findById(id)` call. For decommissioned or not-yet-provisioned vehicle IDs, the repository correctly returned `null`. Over 18 months, five different teams added integrations that called this repository, and **at least two of them forgot the null check** because it wasn't enforced anywhere structurally — it was just convention, documented in a wiki page nobody read before writing new code.

**How the team noticed:** A batch nightly job that computed "total fleet fuel capacity" started throwing `NullPointerException` in production logs at 2 AM, silently failing the entire batch (no partial results were written) — support only found out the next morning when a downstream fuel-budgeting report was empty. The stack trace pointed at `vehicle.getFuelTankCapacity()` inside a `forEach` loop with no null guard.

**Root cause:** The repository's contract implicitly allowed `null` as "vehicle not found," but nothing in the type system or interface communicated that risk to every future caller. Every new consumer had to *remember* to add `if (vehicle != null)`, and inevitably, someone eventually forgot — a classic case of an implicit contract silently rotting as a codebase grows.

**The fix:** The team introduced a `NullVehicle implements Vehicle` (exactly the pattern from this transcript) and changed the repository so `findById()` **never returns `null`** — it returns `NullVehicle.INSTANCE` when nothing is found, with `getFuelTankCapacity()` and `getSeatingCapacity()` both defaulting to `0`. The batch job's aggregation logic (`sum += vehicle.getFuelTankCapacity()`) worked correctly without modification, because summing zero for a missing vehicle is the semantically correct default. No call site needed to change, and no future call site could forget the check, because there was no null to forget checking for.

```
BEFORE:                                    AFTER:
findById() → Vehicle | null                findById() → Vehicle (never null)
    │                                            │
every caller MUST remember                 NullVehicle silently absorbs
`if (v != null)` — one team forgot          "not found" as safe zero-defaults
    │                                            │
  ❌ NPE crashes nightly batch job            ✅ batch job sums correctly, no crash
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Isn't this just hiding bugs? What if a `null` was actually meaningful and should have crashed loudly?**
A: That's a fair concern — the Null Object Pattern is appropriate when "nothing to do here" has a genuinely safe default behavior (e.g., a logger that's a no-op, a discount strategy that applies zero discount). It is **not** appropriate when the absence of an object represents an actual error condition that must halt execution — in that case, you want a checked exception or an `Optional` with explicit `.orElseThrow()`, not a Null Object silently absorbing the problem.

**Q2: How is this different from using Java's `Optional<T>`?**
A: `Optional` makes the *possibility* of absence explicit in the type signature and forces the caller to consciously handle both branches (`isPresent()`/`orElse()`/`map()`), but the caller still branches on presence/absence. The Null Object Pattern goes a step further: it removes the branching entirely by giving the caller an object that behaves safely no matter what, so the calling code has zero special-casing. They can be combined: `Optional<Vehicle>.orElse(new NullVehicle())` is a very natural way to introduce a Null Object at an API boundary.

**Q3: Does the Null Object Pattern violate the Liskov Substitution Principle?**
A: No — in fact it's a textbook demonstration of LSP done right. `NullVehicle` is fully substitutable anywhere a `Vehicle` is expected, because it honors the same interface contract and never throws where a real implementation wouldn't. LSP is violated when a subtype changes behavior in a way that breaks caller expectations (e.g., throwing where the base type wouldn't) — `NullVehicle` deliberately does the *opposite*: it guarantees no surprises.

**Q4: Where else, besides "vehicle lookup," have you seen this pattern used in real systems?**
A: Common real-world examples: a `NullLogger` that implements `Logger` but does nothing (used when logging is disabled without littering code with `if (logger != null)`); a `NullCustomer`/`GuestUser` representing an unauthenticated session; a `NullDiscount` strategy that applies 0% discount instead of every price-calculation method needing to check "does this customer have a discount policy or not."

**Q5: What's the downside of creating a Null Object for every interface in a codebase?**
A: It adds a class per interface purely for this purpose, which is overhead if the interface is rarely at risk of being null, or if there's only one call site (in which case a simple local null-check is simpler and clearer). Apply this pattern where null-propagation risk is widespread across many callers/methods — not as a blanket rule for every interface in the system.

## 🔑 Key Takeaway

Don't scatter `if (x != null)` checks across a codebase as a permanent habit — when a "missing object" has a sensible safe default, replace `null` with a **Null Object** that implements the same interface, so every caller can call methods on it fearlessly and the null-check disappears structurally, not just cosmetically.
