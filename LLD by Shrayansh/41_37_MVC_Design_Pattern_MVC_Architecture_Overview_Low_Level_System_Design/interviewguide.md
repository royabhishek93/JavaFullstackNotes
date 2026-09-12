# Interview Guide: MVC (Model-View-Controller) Architecture Overview

## 🗣️ The Interview Scenario

> "We've discussed several LLD problems with you — parking lot, elevator, Splitwise, BookMyShow. Now, explain how MVC applies to designs like these. Is MVC a design pattern or an architecture? Walk me through what belongs in the Model, what belongs in the Controller, and what belongs in the View, and explain why separating them this way actually benefits a real production system — not just in theory."

Interviewers ask this specifically because candidates often *use* MVC implicitly (every LLD design naturally has entities + business logic + output) without being able to *articulate* it, and freeze when asked directly, as happened to the engineer mentioned in the source material.

## 🏗️ Architect's Explanation (For a New Developer)

Think of a restaurant. The **kitchen** (Model) holds all the raw ingredients and knows how to actually cook a dish — it doesn't know or care who ordered it or how it will be presented. The **waiter** (Controller) takes your order, translates it into something the kitchen understands, decides things like "the kitchen is out of onions, substitute with something else" (business logic/validation), and hands the finished dish to be served. The **table setting/plate presentation** (View) is just what gets shown to you — it has zero cooking logic in it; it just displays what it was handed.

**MVC = Model, View, Controller.** It's important to be precise here (and this is explicitly called out as a common point of confusion): **MVC is best described as an architecture** for structuring an entire application, rather than a narrow, single-purpose design pattern like Singleton or Observer. Frameworks like Spring Boot (Java) and Django (Python) are built around this architecture.

- **Model** = your data/entities (POJOs/dumb classes) + the logic for how that data is fetched/persisted (which DB to talk to, queries).
- **Controller** = the brain — accepts requests, performs validation and business logic, orchestrates calls to the Model, and hands off a result.
- **View** = purely presentational — renders whatever it's given to the client, with **no logic** of its own.

## 📊 Visualize It

**Component flow:**

```
   Client
     │
     ▼
   ┌──────┐        commands / requests         ┌────────────┐        fetch/update        ┌─────────┐
   │ View │ ───────────────────────────────────▶│ Controller │────────────────────────────▶│  Model  │
   │(dumb)│◀─────────────────────────────────── │ (the brain)│◀──────────────────────────── │ (dumb)  │
   └──────┘         rendered result              └────────────┘         data returned        └────┬────┘
                                                                                                     │
                                                                                                     ▼
                                                                                                  Database
```

**Mapped onto an already-solved LLD problem (e.g., Snake & Ladder), per the transcript:**

```
   Model        → Board class (POJO/entity) — pure data, no logic
   Controller   → BoardController — updateBoard(), fetchBoard(), business rules,
                   validation, dependency on a "board repo/service" that talks to the DB
   View         → whatever gets returned to the caller (e.g., a JSON response in a
                   Spring Boot REST controller) — no business logic embedded in it
```

## 🔧 Deep Dive: How It Actually Works

### 1. Model — entities + data access
- Holds **entities/POJOs** — the same "dumb classes" you already create in every LLD problem: e.g., `Car` in a parking-lot design, `Expense` in Splitwise, `Board` in Snake & Ladder.
- Also owns **data-related logic**: which DB to connect to, and can expose an interface (e.g., `get`/`insert`) that the Controller depends on.
- **Crucially "dumb"**: it holds data and persistence mechanics, but no business rules about *when* or *why* something should be updated.

### 2. Controller — the brain
- Accepts the **user request**, interprets it, and performs **business logic**: validation, authorization checks, configuration, caching decisions.
- Then issues a **command to the Model**: "fetch me this," "update this."
- Whatever comes back from the Model, the Controller may further **transform/modify** before handing it onward.
- Has a **dependency on the Model** (e.g., a repository/service interface) to invoke its operations — this is explicitly called out: "controller has the dependency of model."
- In a Spring Boot context, this maps directly to `@RestController` classes exposing REST endpoints (e.g., `GET /fetch`, `POST /insert`) that the View (front end) calls.

### 3. View — purely presentational, "dumb"
- Front-end concerns: forms, buttons, rendering.
- **No logic should live here** — it just renders whatever the Controller/Model pipeline produced.
- In a backend-only interview context, the "View" is often simply **the JSON response returned by the Controller** to the client.

### Why split into three separate components? (the actual engineering payoff)
- **Loose coupling**: if you migrate your Model from a relational DB to Cassandra/Postgres tomorrow, only the Model component's queries/connection logic change — the Controller still just calls the same `get`/`insert` interface, completely unaffected.
- **Independent scaling and testing**: Model is lightweight and fast to unit-test/deploy; Controller (heavier — REST APIs, business logic, config, caching) can be tested and scaled independently; View (front end) scales on its own, independent of both.
- **Separate repos/components in big companies**: the transcript explicitly notes that at scale, Model, Controller, and View often literally live in **separate repositories/components** owned by different teams.

### Explicit trade-off: when NOT to use MVC
- MVC brings **maintenance overhead** — you now manage three separate components instead of one, and complexity increases.
- **Not recommended for small applications** — for small/simple LLD problems or small services, keeping everything in one cohesive module is simpler; MVC's benefits (independent scaling, decoupled testing, team ownership boundaries) only pay off for **mid-to-large applications**.

## 🔥 Real Production Incident & Fix

**What broke:** A mid-sized booking platform initially built as a single monolithic module mixed business validation logic directly inside what were meant to be simple entity classes (`Booking`, `Seat`) — e.g., a `Booking.confirm()` method that both mutated the entity's state *and* directly executed SQL to check seat availability *and* triggered notification logic, all in the "model" layer.

**How the team noticed:** When the team needed to switch their seat-availability check from a relational DB query to a Redis-backed cache (for performance under a ticket-sale spike), they discovered the availability-check SQL was hardcoded inside the `Booking` entity itself, called from a dozen different unrelated code paths (some through the API layer, some through a batch job that bypassed the API layer entirely). QA caught it as a wave of double-booked seats during a load test, and monitoring showed a sudden spike in "seat conflict" errors that hadn't existed in earlier tests.

**Root cause:** There was no real Controller layer — business logic (deciding *whether* a seat could be booked, validation, and orchestration) was smeared directly into the Model (entity) layer and invoked inconsistently from multiple call sites, so the DB migration (a pure Model-layer concern) accidentally touched behavior that different code paths depended on differently.

**The fix:** The team restructured strictly along MVC lines: `Seat`/`Booking` became pure POJOs (Model) with a dedicated repository interface for persistence; **all** validation and orchestration ("is this seat available, is this booking valid, trigger notification") moved into a single `BookingController` service layer; every caller — API and batch job alike — was forced through that one Controller. The subsequent Redis migration only touched the repository implementation behind the Model's interface — zero changes to the Controller, and the batch job could no longer bypass validation because it now had to go through the same Controller path.

```
BEFORE: business logic scattered inside entities,      AFTER: single Controller owns all business
multiple inconsistent call paths bypass validation       logic; Model is a pure, swappable data layer

  Booking.confirm() {                                     BookingController.confirm(bookingReq) {
    // SQL availability check                                validate(); checkAvailability(); // ALL paths
    // mutate state                                           go through here
    // trigger notification                                }
  }  <- called inconsistently from API AND batch job        Booking (POJO) + BookingRepository (swappable
                                                              DB impl) <- Controller's only dependency
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Is MVC a design pattern or an architecture — why does this distinction matter?**
A: It's best treated as an **architecture** — a way of structuring an entire application into three cooperating layers — rather than a narrow, reusable solution to one specific recurring problem the way Singleton or Observer are. This matters because when an interviewer says "design X using MVC," they're really asking you to organize your entities/business-logic/output into these three layers, not asking you to apply a small structural trick.

**Q2: Where does validation logic belong — Model or Controller?**
A: Controller. The Model should remain "dumb" — pure entities and persistence mechanics. All business rules, including validation ("is this request well-formed," "is this operation allowed"), belong in the Controller, which is explicitly described as holding "all the business logic" and being "the brain" of the application.

**Q3: If Model and Controller are in separate components/repos, how does the Controller actually invoke the Model?**
A: The Model exposes an **interface** (e.g., `get`, `insert` endpoints/methods), and the Controller takes a **dependency** on that interface/repo. The Controller never knows or cares how the Model implements persistence internally — it only calls the exposed contract, which is exactly what enables the DB engine underneath to change without touching the Controller.

**Q4: What's the actual cost of adopting MVC, and when would you advise against it?**
A: The cost is added complexity and maintenance overhead from managing three separate components (each needs its own testing, deployment, and possibly its own repo/team). For a **small application**, this overhead isn't justified — a single cohesive module is simpler and faster to build and maintain. MVC pays off specifically at **mid-to-large scale**, where independent testing, independent scaling, and clear ownership boundaries between teams become valuable.

**Q5: How does the View relate to a backend-only LLD interview (there's no "UI" in most LLD problems)?**
A: In a backend-heavy context (e.g., a Spring Boot REST API), the View is effectively **the response the Controller returns to the client** (e.g., a JSON payload) — it's not necessarily an HTML page. The important invariant is the same regardless: the View layer (or response-shaping logic) must contain **no business logic** — it just reflects what the Controller/Model already decided.

**Q6: Give a concrete example of "the same MVC structure" applied to a different LLD problem you've already solved.**
A: In a Splitwise-style expense-splitting design, `Expense` and `User` are the Model (POJOs plus a repository for persistence); an `ExpenseController` (or `SplitwiseService`) holds the business logic — computing splits, validating that shares sum to the total amount, deciding which settlement algorithm to use — and depends on the Model's repository interface; whatever gets returned to the client (e.g., a settlement summary) is the View. The exact same three-layer shape recurs across parking lot, elevator, and BookMyShow-style designs.

## 🔑 Key Takeaway

MVC is an **architecture**, not a narrow design pattern: keep Models "dumb" (entities + persistence only), put **all** business logic in Controllers, keep Views logic-free, and only reach for this three-way split on mid-to-large applications where the payoff — loose coupling, independent testing/scaling — outweighs the added complexity of managing three components.
