# Interview Guide: What is Low-Level Design (LLD)?

## 🗣️ The Interview Scenario

> "Before we dive into designing a parking lot, quick question: how would you explain Low-Level Design to a junior engineer who's only ever written business logic and has never heard the term? And while you're at it — when you draw your class diagram in the next 45 minutes, how are you going to represent 'a Car has an Engine' versus 'a Car is a Vehicle'? Walk me through that."

Interviewers frequently open LLD rounds with this kind of grounding question — not to test trivia, but to confirm the candidate has a mental model of *where* LLD sits in the software lifecycle and *how* they'll communicate relationships under time pressure, before they commit 40 minutes to a specific problem.

## 🏗️ Architect's Explanation (For a New Developer)

Picture software design as three zoom levels on a map:

1. **High-Level Design (HLD)** — the country-level view. "We have Service A, Service B, a database, a cache, a load balancer — here's how they talk to each other." No classes, no methods, just boxes and arrows between systems.
2. **Low-Level Design (LLD)** — the city-level view. You zoom into *one* of those boxes (say, "Component 1") and ask: what classes and objects live inside it? How do they interact? What are their responsibilities?
3. **Actual code** — the street-level view. The literal Java/Python/C++ that implements the classes you designed in step 2.

LLD is the bridge between "we know what the system looks like" and "here's the code" — and it's the step people most often skip, which is a mistake, because **the entire point of LLD is to produce clean code**: code that's flexible (easy to extend), maintainable (easy to change without fear), and testable (easy to verify in isolation). Writing code isn't the hard part — even AI can write code today. Good design is what makes that code worth writing.

## 📊 Visualize It

```
 HIGH-LEVEL DESIGN                LOW-LEVEL DESIGN              ACTUAL CODE
 (architecture)                   (classes & objects)           (implementation)
┌───────────┐   ┌───────────┐     ┌───────────────────┐        class ParkingSpot {
│Component 1│───│Component 2│ ──► │ Double-click into  │  ──►     private boolean occupied;
└───────────┘   └───────────┘     │ Component 1:        │        void park(Vehicle v){...}
      │               │           │  ParkingLot         │      }
┌───────────┐         │           │  ParkingSpot        │
│Component 3│─────────┘           │  Ticket, Payment    │
└───────────┘                     │  (how they interact) │
                                   └───────────────────┘
```

```
LLD PATTERN CATEGORIES                    IS-A vs HAS-A
───────────────────────                   ──────────────
Creational   → controls OBJECT CREATION   Vehicle ◄── TwoWheeler   (IS-A / inheritance)
 (Singleton, Builder, Factory,            Vehicle ◄── FourWheeler  (IS-A / inheritance)
  Abstract Factory, Object Pool, Prototype)

Structural   → arranges classes/objects   Library ◇──── Books     (HAS-A, weak = Aggregation)
 into a flexible "skeleton"                                        (hollow diamond; Book
 (Decorator, Proxy, Composite,                                      survives if Library is destroyed)
  Adapter, Bridge, Facade, Flyweight)

Behavioral   → governs how objects        House  ◆──── Rooms      (HAS-A, strong = Composition)
 communicate/coordinate                                             (filled diamond; Room cannot
 (Strategy, Observer, State,                                         exist if House is destroyed)
  Command, etc.)
```

## 🔧 Deep Dive: How It Actually Works

### Where LLD sits, precisely
LLD is placed *between* HLD and actual code. HLD answers "what are the components and how do they talk to each other at a system level?" LLD takes one of those components and answers "what classes and objects exist inside it, and how do they collaborate?" That collaboration model then gets translated directly into code.

### The purpose of LLD (why it exists at all)
The stated goal is to produce code with three properties:
- **Flexible** — easy to extend with new requirements without rewriting existing, tested code.
- **Maintainable** — easy to understand and safely modify later (by you or someone else).
- **Testable** — easy to verify individual pieces in isolation.

The framing is deliberately blunt: "writing code is not difficult; coming up with a proper design is what's actually hard and valuable" — because a good design is what *lets* you write the code easily and confidently afterward.

### The three categories of LLD/design patterns
Every classic design pattern exists to solve a problem that keeps recurring, so you don't reinvent the same solution each time. They fall into three buckets:

1. **Creational** — controls *how objects get created*. Examples: Singleton (only one instance ever exists and is shared with every caller), Builder (construct a complex object step-by-step), Factory, Abstract Factory, Object Pool, Prototype.
2. **Structural** — controls *how classes/objects are arranged together* to solve a larger problem in the most flexible way. Analogy: if you're building a car out of separate objects (wheel, engine, headlights, steering), structural patterns are about how those pieces get assembled into a coherent "skeleton." Examples: Decorator, Proxy, Composite, Adapter, Bridge, Facade, Flyweight.
3. **Behavioral** — controls *how objects communicate or interact* once the skeleton (structural arrangement) exists. If structural patterns build the skeleton, behavioral patterns define how that skeleton *behaves*: which object calls which, whether there's a central orchestrator, how responsibility is divided. This is the category Strategy, Observer, State, Command, etc. belong to.

Important nuance: **understanding a named pattern is not mandatory** to solve an LLD problem. You might naturally discover the same class structure a pattern already describes just by working through the problem's constraints — the value of knowing the pattern is that you don't have to reinvent an already-solved shape, and it gives you and your interviewer shared vocabulary.

### IS-A vs HAS-A — and how to represent them without over-thinking UML

**IS-A relationship = inheritance.** A `TwoWheeler` **is a** `Vehicle`; a `FourWheeler` **is a** `Vehicle`. A `CEO` **is an** `Employee`; a `Manager` **is an** `Employee`. Parent/child.

**HAS-A relationship = association** — a link between two independent-ish objects, e.g., "a Library has Books," "a School has Students." This has two flavors:

- **Aggregation (weak relationship)** — the existence of one object does *not* depend on the other. A `Library` has `Books`, but if the `Library` object is destroyed, the `Book` objects can still exist independently (and a library "knows about" its books but doesn't manage their lifecycle — it doesn't create or delete them). Represented with a **hollow diamond** and a line.
- **Composition (strong relationship)** — the existence of one object *depends* on the other. A `House` has `Rooms`; if the `House` is destroyed, the `Rooms` cease to exist too — a `Room` cannot exist independently of its `House`. Represented with a **filled/solid diamond** and a line. Practically, this also means the "owning" class (`House`) is responsible for creating the dependent objects (`Room`), because their lifecycle is tied together.

### Practical UML advice for the actual interview (time management)
A very concrete, experience-based tip: LLD rounds are typically either a ~2-hour machine-coding round (expects a fully working implementation) or a 40–45 minute round (often *still* expects working code, even if less complete). Given that time pressure, **don't over-invest in drawing a textbook-perfect UML diagram** — spend roughly 10–15 minutes max identifying classes, IS-A vs HAS-A relationships, and responsibilities, then move to code, because if you don't produce code in a 40–45 minute round, your chances of a pass drop significantly. A pragmatic shortcut: instead of memorizing whether a relationship needs a filled or hollow diamond, just draw an arrow and label it "is-a" or "has-a" directly — it communicates the same design intent faster and with zero ambiguity.

## 🔥 Real Production Incident & Fix

**The incident:** A backend team building a hotel-booking-style internal tool modeled `Room` as directly owning and constructing its own `Building` reference during startup — effectively inverting a composition relationship. The intent was "a Room belongs to a Building" (correct conceptually — composition, since a Room can't exist without a Building), but the implementation had `Building`'s constructor *fetch* pre-existing `Room` objects from a cache that could, in rare startup-race conditions, still hold `Room` objects from a *previously torn-down* `Building` (e.g., during blue-green deployment swaps).

**How the team noticed:** After a deployment, support tickets came in reporting rooms showing "available" for buildings that had been decommissioned that same day. Debugging traced it to stale `Room` objects outliving their `Building` in the cache — a direct violation of what composition is supposed to guarantee (dependent object lifecycle tied to the owner).

**Root cause:** The team had *conceptually* called it composition ("Building has Rooms, filled diamond") in their design doc, but never enforced it in code — nothing guaranteed that a `Room` was destroyed/invalidated when its `Building` was torn down. It was actually behaving like aggregation (Rooms outliving their parent) while being labeled and assumed to be composition, and no one had explicitly asked "should this object be able to exist without its parent?" during the design review — the IS-A/HAS-A and aggregation/composition question that a clean LLD process forces you to ask up front.

**The fix:** The team introduced an explicit `Building` lifecycle hook that invalidated/evicted all associated `Room` cache entries on teardown, and renamed the relationship's intent in the design doc and code comments to make the strong ownership explicit, closing the gap between the *stated* design (composition) and the *actual* runtime behavior.

```
BEFORE: labeled "composition" but                AFTER: composition enforced in code
behaved like aggregation (bug)                    ─────────────────────────────────
Building ◆── Room (label only, no                 Building ◆── Room
enforcement — Room cache entries                  Building.teardown() explicitly
survived Building teardown)                       invalidates/removes all owned
                                                   Room entries — lifecycle now
                                                   actually tied together
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why is LLD described as sitting "between" HLD and actual code rather than being part of either?**
A: HLD describes system-level architecture (services, databases, how they connect) with no notion of classes; actual code is the literal implementation. LLD is the missing translation layer — it decides what classes/objects live inside one architectural component and how they collaborate, which is what the code will directly implement. Skipping it means jumping from "boxes and arrows" straight to code with no intermediate object model, which tends to produce ad-hoc, hard-to-maintain classes.

**Q2: What's a concrete failure mode of not doing LLD before coding?**
A: You typically get classes with mixed responsibilities that grew organically to satisfy immediate feature requests, making the code hard to extend (violates flexibility), hard to reason about (violates maintainability), and hard to unit test in isolation (violates testability) — the exact three properties LLD is meant to guarantee.

**Q3: Is it ever acceptable to solve an LLD problem without knowing the "official" pattern name for your solution?**
A: Yes — pattern knowledge is a shortcut/vocabulary tool, not a hard requirement. If your class design naturally satisfies the constraints (e.g., you built something that lets behavior vary independently and later realize it's structurally the Strategy pattern), that's a perfectly valid outcome. The risk only appears if you *don't* recognize an already-known-good structure and end up reinventing (and potentially messing up) something well-established.

**Q4: How would you decide whether a relationship should be aggregation or composition in a design?**
A: Ask: "if the owning object is destroyed, does the owned object still make sense to exist independently?" If yes (e.g., a Book outliving a destroyed Library object/reference), it's aggregation — weak, hollow diamond. If no (e.g., a Room without a Building is meaningless), it's composition — strong, filled diamond, and the owner is typically responsible for creating/destroying the dependent objects.

**Q5: In a time-boxed 40–45 minute LLD interview, how much time should you spend on UML/diagramming versus coding?**
A: A practical rule of thumb is roughly 10–15 minutes on identifying classes and relationships (even informally, with simple "is-a"/"has-a" labeled arrows instead of strict UML notation), reserving the bulk of the time for producing actual working code, since many interviewers still expect functioning code even in shorter rounds.

**Q6: What's the difference between a creational, structural, and behavioral pattern in one sentence each?**
A: Creational patterns control *how* objects are created (e.g., Singleton ensures only one instance ever exists); structural patterns control *how* objects/classes are composed together into a working skeleton to solve a bigger problem (e.g., Decorator layers behavior onto an object); behavioral patterns control *how* objects that already exist within that skeleton communicate and coordinate responsibility (e.g., Observer notifies dependents of state changes).

## 🔑 Key Takeaway

LLD exists specifically to produce flexible, maintainable, testable code by modeling classes and their relationships (IS-A via inheritance, HAS-A via aggregation/composition) *before* you write implementation — and in an interview, that modeling should be fast and pragmatic (simple labeled arrows), not a perfectly formatted UML diagram that eats into your coding time.
