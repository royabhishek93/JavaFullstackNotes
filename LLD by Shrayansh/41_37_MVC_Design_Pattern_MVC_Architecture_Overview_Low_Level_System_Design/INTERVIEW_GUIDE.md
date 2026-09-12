# 🧩 MVC Design Pattern - Interview Guide
## _15 YOE Architect-Level Conversational Script_

**📗 Difficulty: Beginner** — ideal starting point for a new developer; read this before tackling applied system-design questions.

> _(Companion to `transcript.md`, left untouched. Whiteboard-style scenario discussion.)_

---

**Interviewer**: "Design Snake and Ladder / any LLD question using MVC. Also — is MVC even a 'design pattern'?"

**You**: "Good catch on the second question first: I treat MVC more as an **architectural style** than a GoF design pattern — it describes how to organize a whole application into layers, not how to solve one specific object-creation/behavior problem. But if an interviewer frames it as 'design pattern', don't argue semantics — just show you understand the separation of concerns."

---

## 1. Architecture Diagram

```
   ┌────────┐        ┌──────────────┐        ┌────────┐
   │  Client   │◀──────▶│   View (Front-  │◀──────▶│Controller│
   │ (Browser/ │        │   end / JSON      │        │(Mediator, │
   │  App)      │        │   response)        │        │ business  │
   └────────┘        └──────────────┘        │ logic)   │
                                                └────┬─────┘
                                                       │  uses
                                                       ▼
                                                ┌────────────┐
                                                │   Model         │
                                                │ (POJOs/Entities,│
                                                │  DB access)       │
                                                └────────────┘
```

- **Model**: "dumb" data classes (POJOs/entities) + the logic to persist/retrieve them (which DB, which query).
- **View**: also "dumb" — just renders whatever it's given (HTML, JSON) to the client. No business logic.
- **Controller**: the "brain" — accepts user requests, validates, applies business logic, orchestrates the Model, and hands the result to the View.

---

## 2. Scenario-First Explanation: Snake and Ladder via MVC

**You**: "In every LLD question I've solved — Parking Lot, Splitwise, BookMyShow — I was *already* doing MVC without naming it:"

```
Model       -> Board, Player, Dice, Snake, Ladder  (POJOs, no logic beyond data)
Controller  -> GameController: rollDice(), movePlayer(), checkSnakeOrLadder(), checkWin()
View        -> whatever renders the board state back to the "client" (console println,
               or in a real app, the JSON returned by a REST endpoint)
```

"So when an interviewer says 'design X using MVC', they're really just asking: **can you cleanly separate data (Model), presentation (View), and orchestration/business-logic (Controller)?** In an LLD interview, the scope is usually just Model + Controller since there's rarely a real front-end or DB involved."

---

## 3. Cross Questions

**Q: "Why does Controller depend on Model, but Model never depends on Controller?"**
**A:** "Dependency should flow toward the *more stable*, *less frequently changing* layer. Model (entities + DB access) is inherently more stable — it doesn't need to know about business rules. Controller changes far more often (new business rules, new validations) — if Model depended on Controller, every business rule change would risk destabilizing your data layer. This is the Dependency Inversion Principle applied at an architectural level."

**Q: "What's the actual advantage of separating these three, versus one big class?"**
**A:** "**Loose coupling → independent scalability & testability.** If tomorrow we swap Postgres for Cassandra, only the Model layer changes — Controller and View are untouched. Model is lightweight and fast to unit-test. Controller can be tested with a mocked Model. Each layer can literally live in a separate repo/service and scale independently in a microservices setup."

---

## 4. Trade-offs

| Aspect | MVC | Single "God" Class |
|---|---|---|
| Testability | High (mock Model, test Controller in isolation) | Low (everything entangled) |
| Change isolation | DB change only touches Model | Any change risks breaking everything |
| Overhead for tiny apps | Unnecessary (3 components to manage) | Simple, fast to build |
| Team scalability | Different teams can own View/Controller/Model | Hard to parallelize work |

---

## 5. Senior Trap Questions

**Trap: "Should I use MVC for every LLD question, no matter how small?"**
**✅ Senior answer:** "No — MVC (and layered architectures generally) add real overhead: three components to maintain, deploy, and test independently, plus the discipline to keep business logic OUT of Model/View. For a tiny script or a single-purpose CLI tool, this is pure overhead with no payoff. MVC pays off for **medium-to-large applications** with a genuine need for independent scaling/testing/team-ownership boundaries — recognizing *when NOT to use a pattern* is itself a senior-level signal."

---

## 🔥 Real-World Production Issue: Business Logic Leaking Into the Model Layer

*In plain English: sneaking business logic into the "dumb" data layer means it can silently vanish the next time that layer gets regenerated.*

**The war story:**

"A 'small' feature request — 'apply a 10% discount for premium users at checkout' — got implemented by a well-meaning engineer directly inside the `Order` **entity** class (the Model layer), because 'it was the fastest place to add the `if` statement'."

```
┌────────────────────────────────────────────────┐
│ class Order {                    // MODEL — should be "dumb"! │
│   double total;                                     │
│   User user;                                          │
│   double getFinalPrice() {                              │
│     if (user.isPremium()) return total * 0.9;   ◄── BUSINESS │
│     return total;                                RULE LEAKED  │
│   }                                                INTO MODEL   │
│ }                                                                │
└────────────────────────────────────────────────┘
```

**What went wrong months later:** the team migrated the persistence layer from MySQL to a document DB for performance, and re-generated the `Order` entity class from a schema tool — **wiping out the hand-written discount logic** because nobody expected business logic to live inside an auto-generated Model class. Premium users were silently overcharged in production for 3 days until a customer complaint surfaced it.

```
   Timeline:
   Day 0:  Discount logic added directly to Order entity (Model layer)  — "quick fix"
   Day 90: DB migration regenerates Order.java from schema -> discount logic silently deleted
   Day 93: Customer complaint: "I'm premium but paying full price!"
   Day 93: Root cause found — business logic was never in the Controller where it belonged
```

**The fix:**
- Moved ALL pricing/discount logic into `OrderController` / a dedicated `PricingService`, keeping `Order` as a pure data holder (getters/setters only).
- Added an architectural linting rule (ArchUnit) that **fails the build** if any class in the `model` package contains conditional business logic (`if`/`switch` beyond simple null-checks) or calls to service-layer classes.
- Documented the rule in the team's architecture decision record (ADR): "Model = data only. Business rules ALWAYS live in Controller/Service layer."

**Lesson for a new developer:** "MVC's value isn't the diagram — it's the **discipline of keeping business logic out of Model and View**. The moment logic creeps into your 'dumb' data classes, you lose the exact benefits (safe DB swaps, safe codegen, independent testing) that MVC promised. Enforce it with architecture tests, not just code review vigilance."

---

## 🎓 Final Tips
1. MVC is best thought of as an **architectural style** for separating data, presentation, and business logic — not a single-object creational/behavioral pattern.
2. Model and View should be "dumb" — Controller holds ALL business logic.
3. Dependency direction: Controller → Model, never the reverse.
4. Don't over-apply MVC to trivial problems — the 3-layer overhead only pays off at real scale.
5. In production, enforce "no business logic in Model" with architecture tests, not just review discipline.

Good luck! 🚀
