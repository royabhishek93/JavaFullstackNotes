# Interview Guide: Microservices Design Patterns — Monolith vs Microservices & Decomposition Patterns

## 🗣️ The Interview Scenario

> "Your company runs a 10GB legacy monolith for an e-commerce platform. Builds take forever, IDEs choke trying to load the codebase, and a one-line bug fix requires a full regression cycle before deploy. Walk me through, concretely, what specifically goes wrong in a monolith at this scale, and then show me two different concrete strategies you'd use to decide how to decompose it into microservices."

Interviewers use this question to check whether you can articulate the monolith's failure modes with **specific, concrete pain points** (not just "it doesn't scale") and whether you know **more than one decomposition strategy** and when each applies.

## 🏗️ Architect's Explanation (For a New Developer)

Picture one gigantic shared kitchen used by every restaurant in a food court — one walk-in fridge, one set of ovens, one register. If the taco stand's dish washer breaks, in theory it shouldn't affect the pizza stand — but because everything is jammed into one kitchen, cleaning up, restocking, or fixing anything means the *entire kitchen* has to pause. Scaling is worse: if only the taco stand is busy, you can't just add more taco cooks — you'd have to duplicate the *entire* kitchen (pizza ovens and all) just to get more taco capacity.

That's a **monolith**: every business capability (orders, inventory, billing, login) crammed into one deployable application with one codebase and often one database. It's simple to start with, but as it grows, every change risks breaking something unrelated, every deploy is slow and risky, and scaling one busy piece means scaling the *whole* thing.

**Microservices** split that shared kitchen into independent food stalls — each with its own equipment, own staff, own supply chain. A problem at the taco stand stays at the taco stand. If tacos are popular, you scale up just the taco stand. But now you've traded "one big kitchen to manage" for "many small kitchens that need to coordinate deliveries and orders between each other" — which introduces its own very real challenges (communication overhead, distributed transactions).

The real interview skill isn't reciting "microservices are better" — it's knowing **exactly how** to decide where to cut the monolith into pieces. That's what **decomposition patterns** are for.

## 📊 Visualize It

```
MONOLITH (single deployable, single/shared DB)
┌───────────────────────────────────────────────────────┐
│  Order Mgmt | Inventory | Billing | Payments | Login   │
│   all one IDE-breaking, slow-to-build, 10GB codebase   │
│                    single shared DB                     │
└───────────────────────────────────────────────────────┘
  One-line bug fix ⇒ full regression ⇒ full redeploy ⇒ slow, risky
  Need more Order capacity? ⇒ must scale the ENTIRE monolith, not just Order
```

```
MICROSERVICES (decomposed, independently deployable, independently scalable)
┌────────────┐  ┌──────────────┐  ┌─────────┐  ┌──────────┐  ┌────────┐
│Order Mgmt  │  │  Inventory    │  │ Billing │  │ Payments │  │ Login  │
│   Svc      │  │     Svc       │  │   Svc   │  │   Svc    │  │  Svc   │
└────────────┘  └──────────────┘  └─────────┘  └──────────┘  └────────┘
  Order gets 10x traffic? ⇒ scale ONLY Order Svc instances, nothing else
  Bug in Billing? ⇒ fix, test, deploy Billing ONLY — nothing else touched

  BUT introduces new problems: latency between chatty services,
  and distributed transactions across separate per-service databases
```

## 🔧 Deep Dive: How It Actually Works

### Monolith — concrete disadvantages (the ones an interviewer expects you to name specifically)

1. **IDE overload.** A codebase that grows into gigabytes becomes genuinely difficult (sometimes practically impossible) to load into an IDE (IntelliJ, Eclipse) at reasonable speed — a real, everyday developer-experience cost, not just an abstract "it's big" complaint.
2. **Scaling is hard.** Growing/scaling depends on how fast your sub-operations (like CI pipelines) run. If CI (continuous integration — pushing, running regression, monitoring) is slow because the whole codebase must be validated for every change, your ability to scale the *team* and the *system* both suffer.
3. **Tight coupling.** Order code, product code, payment code all live together; a one-line fix in a shared piece of code can ripple into multiple unrelated domains, forcing full regression testing and full redeploy for a trivial change — this takes "a lot of time."
4. **Can't scale a single business capability independently.** If only the Order API's traffic spikes, you cannot scale *just* Order — you must stand up an entire duplicate of the whole monolith (e.g., a whole extra 10GB app server) even though you only needed more Order capacity. This is explicitly called out as costlier and much harder to scale.

### Microservices — advantages (directly the inverse of the above)

- Managing individual components becomes far easier — a developer only needs to reason about and fix **one service**, not the whole system.
- Scaling becomes targeted and cost-effective — you only add capacity (and pay for infrastructure) for the specific service under load, e.g., scale only Order Management if that's where the traffic is.

### Microservices — disadvantages (this is the part interviewers specifically probe, since "advantages" is the easy half)

1. **Improper decomposition ("not loosely coupled") causes latency issues.** If services are split without real independence — i.e., completing one request requires excessive cross-service communication because of hidden dependencies — the result is **increased latency**. An API that used to respond in 2–5ms internally within a monolith might now take 10ms+ once it has to make network calls to other services to complete the same logical operation. This is explicitly framed as "if we don't divide the components properly / don't decompose the monolithic system properly."
2. **Debugging/monitoring across services is harder.** When Service 1 depends on Service 2, which depends on Service 3, and a bad code change in Service 3 changes its response shape or behavior, it can break Service 2, which then breaks Service 1. Diagnosing "where does the fault actually lie" becomes confusing — an engineer sees Service 1 failing, traces it to "failing because of Service 2," and only then discovers Service 2 is failing "because of Service 3" — a multi-hop debugging chain across team boundaries.
3. **Transaction management becomes genuinely difficult.** In a monolith with a single shared DB, you can wrap a multi-table operation in one local ACID transaction — succeed everything or roll back everything. In microservices, **each service typically owns its own database**. If a single logical request must be processed by two or more services (e.g., Service 1 and Service 2 both need to persist something for one business operation), there is **no single common transaction** spanning both databases anymore. If one service's write succeeds and the other's fails, you need an explicit strategy to roll back the side that succeeded — a shared ACID transaction is no longer available across service boundaries (this is exactly the problem the Saga pattern, covered in Part 2, is designed to solve).

### Decomposition Patterns — the actual "how do I split it" toolkit

The transcript frames microservices adoption as a sequence of **phases**, each governed by its own pattern choices: **Decomposition → Database → Communication → Integration** (and further, observability). Today's focus is specifically the **Decomposition phase**, which has two named patterns:

**Pattern 1 — Decompose by Business Capability**

- Identify the distinct **business functions** your system performs — e.g., for an online ordering app: Order Management, Product Management, Inventory Management, Account Management, Login, Billing, Payment.
- Each distinct business function/capability becomes its own service, **regardless of how large or small that capability's own internal logic is**.
- **Key challenge called out explicitly:** this requires genuinely good, accurate knowledge of what your business's functional capabilities actually are. Without that clarity up front, you risk drawing service boundaries incorrectly.
- **Important nuance on the word "micro":** there is **no fixed size definition for "micro."** A capability like "Order Management" can itself be a large, complex application internally, but in the *context* of this decomposition, it's still considered "one microservice" because it maps to one coherent business capability. "Micro" is relative to the *context* of your specific system, not an absolute size threshold.

**Pattern 2 — Decompose by Subdomain (Domain-Driven Design / DDD)**

- Recognizes that a single business capability (like "Order Management") can itself be genuinely large and can be **further broken down into subdomains**.
- Example given: "Order Management" is one **domain**, but within it you can identify separate subdomains like **Order Tracking** and **Order Placing** — these could become their own separate microservices, rather than being lumped into one "Order Management" service.
- Similarly, "Payment" as a domain can be split into subdomains like **Forward Payment** (the actual outgoing payment capability) and **Reverse Payment** (refund capability) — each potentially its own microservice.
- **The critical distinction from Pattern 1:** Business Capability decomposition looks at *what one coherent function does* and makes it one service. Subdomain/DDD decomposition starts from *one domain* and then intentionally slices *inside* that domain into multiple, more granular independent services. They can look superficially similar but come from a fundamentally different starting point (whole-function-as-a-unit vs. domain-then-subdivide).

## 🔥 Real Production Incident & Fix

**What broke:** A logistics company decomposed its monolith mostly using the Business Capability pattern but rushed the "Shipment Tracking" service — it ended up needing to call the "Order Management" service synchronously for nearly every read (to fetch order metadata needed to render tracking status), and "Order Management" in turn called back into "Shipment Tracking" for status updates on certain admin screens. This created a **circular, tightly-coupled dependency** disguised as two separate microservices.

**How it was detected:** During a routine deploy of Order Management, a minor response-shape change (renaming a field) broke Shipment Tracking's tracking-page rendering in production. The on-call engineer for Shipment Tracking initially assumed the bug was local, spent an hour debugging their own service, and only found the true cause by checking **distributed trace spans (via OpenTelemetry/Jaeger)**, which showed the failing call chain originating from Order Management's changed response payload — exactly the "confusing, multi-hop debugging" problem called out in the deep dive.

**Root cause:** The two "microservices" were not actually loosely coupled — they were tightly interdependent in both directions, meaning a change in one's response contract silently broke the other, and nobody could reason about either service in isolation. This is functionally the "improper decomposition → latency + fragility" failure mode.

**The fix:** The team applied the subdomain (DDD) lens retroactively: they identified that "current shipment status" was actually needed as a **read-only projection**, not a live synchronous call, and moved it to an **asynchronous event** published by Order Management whenever order state changed, consumed and cached locally by Shipment Tracking. This eliminated the circular synchronous dependency entirely, cut Shipment Tracking's p99 latency by removing a network hop from its hot path, and made each service independently deployable again — a contract change in one no longer had a blast radius reaching into the other.

```
BEFORE: circular synchronous coupling (fragile, hard to debug)
   OrderMgmt ──sync call──▶ ShipmentTracking ──sync call──▶ OrderMgmt
        (a field rename in either one breaks the other, silently)

AFTER: one-way async event flow (loosely coupled, independently deployable)
   OrderMgmt ──publishes order-status-changed event──▶ ShipmentTracking
        (ShipmentTracking maintains its own local read cache/projection)
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: What are the advantages and disadvantages of microservices? (a very common standalone question)**
Advantages: independent scalability (scale only the busy service), easier component management (a developer reasons about one small service rather than a huge codebase), and faster, lower-risk deploys per service. Disadvantages: improper decomposition causes latency from excessive inter-service communication, debugging/monitoring becomes harder across service boundaries when a failure's true root cause is multiple hops away, and transaction management becomes genuinely difficult because each service typically owns its own database, so there's no single ACID transaction spanning a multi-service business operation anymore.

**Q2: What's the actual difference between decomposing by business capability versus by subdomain (DDD)?**
Business capability decomposition starts from "what distinct functions does the business perform" and makes each one a service regardless of its internal size or complexity — e.g., all of Order Management becomes one service. Subdomain/DDD decomposition starts from a single domain and deliberately splits *within* it into more granular independent services, e.g., splitting Order Management itself into Order Tracking and Order Placing, or splitting Payment into Forward Payment and Reverse Payment.

**Q3: Is there a fixed minimum or maximum size for a "microservice"?**
No — "micro" is relative to the context of the specific system, not an absolute size threshold. A business capability like Order Management can be a large, complex application on its own and still be considered "one microservice" in a decomposition where the unit of division is the business capability itself, not lines of code or team size.

**Q4: Why does transaction management get harder in microservices, concretely?**
In a monolith, a multi-table write for one logical operation can be wrapped in a single local ACID transaction against one shared database — full commit or full rollback. In microservices, each service generally owns its own database, so if a business operation needs writes in two services' separate databases, there's no shared transaction mechanism; if one write succeeds and the other fails, you need explicit compensating logic (this is exactly why patterns like Saga exist, covered separately).

**Q5: How would you avoid the "improper decomposition causes high communication overhead and latency" trap in practice?**
Validate boundaries against loose coupling before finalizing them — check whether completing a single typical business request requires excessive back-and-forth calls between the proposed services; if it does, that's a strong signal the domain boundary is wrong and the two "services" actually belong together or need an asynchronous, event-based relationship instead of tight synchronous coupling, as in the shipment-tracking incident above.

**Q6: If debugging becomes harder with microservices, how do teams mitigate that in production?**
Distributed tracing (e.g., OpenTelemetry, Jaeger, Zipkin) is the standard mitigation — it lets an engineer follow a single request's full call chain across service boundaries instead of manually asking each team "did your service fail because of mine?" in sequence, which is exactly the slow, confusing multi-hop debugging process this topic calls out as a genuine disadvantage of microservices.

## 🔑 Key Takeaway

Every disadvantage of a monolith (build/scale pain, tight coupling, all-or-nothing deploys) becomes an advantage of microservices, but decomposing improperly trades those problems for new ones — latency from chatty coupling, harder cross-service debugging, and lost cross-service transactions — so always justify your service boundaries using an explicit pattern (Business Capability or Subdomain/DDD) rather than an intuitive guess.
