# Microservices Decomposition Patterns: Strangler Fig, BFF, and Anti-Corruption Layer
### How you migrate off a 10-year-old monolith without a risky, all-or-nothing rewrite

---

## PART 1 — THE STUDENT CONVERSATION

Imagine an old, fully-occupied office building that needs to be replaced — but you can't evacuate every tenant and demolish it, because the business running inside can't stop operating for the two years a full rebuild would take. The strategy real construction crews use in this exact situation, named after a real botanical phenomenon, is the **strangler fig pattern**: the fig plant grows AROUND an existing host tree, sending down roots alongside it, gradually taking over more and more of the structural load, until eventually the original tree can be removed entirely and the fig stands on its own — and at no single moment did anything visibly collapse. Applied to software: you put a routing facade (often literally your API Gateway, see [116-api-gateway-service-mesh-pattern.md](116-api-gateway-service-mesh-pattern.md)) in FRONT of the old monolith, and you migrate ONE capability at a time — say, just the "search" endpoint — to a new, independently-built service, redirecting only THAT route through the facade to the new service while every other route still hits the old monolith unchanged. Tenants (users) never notice the migration happening one room at a time, and if the new search service turns out to be broken, you flip that one route back to the monolith instantly — the blast radius of a mistake is always just the one capability you're currently migrating, never the whole system at once.

A second, related problem: once you DO have several independent services, a single mobile app screen often needs data assembled from three or four of them at once — say, a product page needing product details, current price, user's wishlist status, and inventory count. If the mobile app itself calls all four services directly, every one of those services now has to support a UI-shaped, mobile-specific response format, AND a completely different web-frontend team's needs, AND maybe a partner API's needs — three different consumers pulling each backend service in three different directions. The fix: give each TYPE of consumer its own dedicated aggregation layer — a **Backend-For-Frontend (BFF)** — that calls the various backend services and shapes the response exactly the way THAT client needs it. The mobile BFF can be lean and battery/bandwidth-conscious; the web BFF can return a richer payload; neither one forces the underlying services to compromise their own clean data model to satisfy every consumer's competing preferences at once.

A third problem shows up specifically during a strangler-fig migration: your shiny new "Order" service has a clean, modern domain model, but it still needs to read some data from the ancient monolith's database, which represents "an order" with 15 years of accumulated legacy quirks (a status field that's really three different concepts crammed into one column, because a fix from 2014 that was supposed to be temporary). If your new service's code directly understands and depends on those legacy quirks, you've just imported the monolith's mess into your brand-new service — defeating the entire point of the rewrite. The fix is an **Anti-Corruption Layer (ACL)**: a thin, deliberate translation layer that sits between the new service and the legacy system, converting the legacy model's quirks into your new service's clean domain model at the boundary — the new code never sees the legacy mess directly, and if the legacy system's quirks ever change, only the translation layer needs updating, not your core domain logic.

Finally, once you've split services apart, each with its OWN database (database-per-service, a deliberate choice so services don't get re-coupled through a shared table the way they were coupled through shared code in the monolith), a single business question that used to be one SQL JOIN — "show me this customer's order history with current product names and prices" — now needs data from two or three separate databases that can't be joined directly. This is solved either by **API composition** (a coordinating service calls each backend, joins the results in application code — simple, but can be slow if each is a network call) or, at higher scale, by maintaining a **precomputed, denormalized read model** kept in sync via events (this is exactly the CQRS pattern from [025-cqrs-event-sourcing.md](025-cqrs-event-sourcing.md) applied specifically to the cross-service read problem).

---

## PART 2 — THE DECOMPOSITION ARCHITECTURE DIAGRAMS

### Strangler Fig: Routing Facade Migrates One Capability at a Time

```
                          Client Traffic
                                │
                                v
                    ┌───────────────────────┐
                    │   ROUTING FACADE         │   (often the API Gateway)
                    │  /search  → NEW service   │
                    │  /orders  → OLD monolith   │
                    │  /profile → OLD monolith   │
                    │  /reviews → OLD monolith   │
                    └───────┬───────────┬───────┘
                            │           │
              (migrated)    │           │   (not yet migrated)
                            v           v
                  ┌──────────────┐  ┌────────────────────┐
                  │  NEW Search    │  │  OLD MONOLITH        │
                  │  Service       │  │  (still serves         │
                  │  (own DB,      │  │  orders, profile,      │
                  │  clean model)  │  │  reviews, and search    │
                  └──────────────┘  │  DATA the new service    │
                                     │  may still read via an   │
                                     │  Anti-Corruption Layer    │
                                     │  during the transition)   │
                                     └────────────────────┘

Timeline: repeat this for /orders next month, /profile the month
after — the monolith shrinks incrementally, and at every stage the
system is fully working and fully deployable. If /search breaks in
week 1, the fix is flipping ONE route back — never a rollback of the
"whole migration."
```

### Backend-For-Frontend (BFF): One Aggregation Layer Per Client Type

```
   Mobile App              Web App                Partner API
       │                      │                       │
       v                      v                       v
 ┌────────────┐        ┌────────────┐         ┌────────────┐
 │ Mobile BFF   │        │  Web BFF     │         │ Partner BFF  │
 │ (lean, small │        │ (rich data,  │         │ (contract-   │
 │  payloads)   │        │  more fields)│         │  stable API) │
 └──────┬─────┘        └──────┬─────┘         └──────┬─────┘
        │                      │                       │
        └──────────────┬───────┴───────────┬──────────┘
                        v                   v
              ┌──────────────┐    ┌──────────────┐
              │ Product Svc    │    │ Inventory Svc  │
              └──────────────┘    └──────────────┘

Each BFF calls the SAME backend services, but shapes/filters/aggregates
the response differently for its one consumer — backend services stay
generic and don't have to satisfy 3 competing response-shape demands
in one shared API contract.
```

### Anti-Corruption Layer: Isolating New Code From Legacy Data Quirks

```
NEW Order Service (clean domain model)
  interface: OrderStatus { PLACED, PAID, SHIPPED, DELIVERED, CANCELLED }
        │
        v
┌──────────────────────────────────────┐
│    ANTI-CORRUPTION LAYER                │
│                                           │
│    translates:                           │
│    legacy.status_code == 3 AND            │
│    legacy.payment_flag == 'Y'    →  PAID   │
│                                           │
│    legacy.status_code == 3 AND            │
│    legacy.payment_flag == 'N'    →  PLACED │
│    (a 2014 hotfix repurposed status_code=3 │
│     for two different real-world meanings, │
│     disambiguated only by payment_flag —   │
│     the NEW service never has to know this) │
└──────────────────────────────────────┘
        │
        v
LEGACY MONOLITH DATABASE (15 years of schema quirks, untouched)
```

### API Composition: Joining Across Database-Per-Service Boundaries

```
Client: GET /customer/789/order-history-with-current-prices
                    │
                    v
        ┌────────────────────────┐
        │  Composition Service     │   (or a BFF doing this same job)
        └───────┬──────────┬──────┘
                v            v
       Order Service    Product Service
       (own DB: order    (own DB: current
       history, historic  prices, product
       price paid)         names)
                │            │
                └─────┬──────┘
                      v
        Composition Service JOINS in application
        code: order.productId → product.currentPrice
        (a network-call join, not a SQL join — slower
         per-request than the monolith's single JOIN
         used to be, but each service stays independently
         deployable, independently scalable, and owns its
         own schema without any other service reaching in)
```

---

## PART 3 — INTERNALS AND REAL NUMBERS

### Strangler Fig Migration Order — Which Capability First?

```
Prioritize migrating capabilities that are:
  1. LOW-RISK if something goes wrong (not the payment/checkout path
     on day one of the migration strategy)
  2. HIGH-VALUE to prove the pattern works (a capability the team is
     already planning to rewrite/improve anyway)
  3. LOOSELY COUPLED in the legacy code (a module that doesn't reach
     into six other modules' internal tables directly)

Common real-world order: read-heavy, low-risk features first (search,
product catalog display) → then write paths with lower blast radius
(profile updates) → checkout/payment LAST, once the pattern, the
routing facade, and the team's confidence are all proven.
```

### Real Numbers

```
API composition added latency: each additional service call in a
  composition adds its own network round-trip, commonly 5-50ms per
  hop depending on same-DC vs cross-region — a composition joining
  4 services sequentially could add 100-200ms versus a single
  monolith SQL JOIN's single-digit milliseconds; this is why
  composition calls are usually made in PARALLEL (fan-out, not
  sequential) wherever the joined services don't depend on each
  other's results.
Anti-corruption layer maintenance cost: typically small and localized
  — a translation layer touching one legacy table's quirks — versus
  the alternative of spreading legacy-aware conditional logic across
  every consumer of that data, which is the actual "corruption"
  the pattern is named to prevent.
Strangler fig migration timelines for a large monolith: commonly
  measured in many months to a few years for a full migration,
  precisely BECAUSE it's deliberately incremental — the tradeoff for
  never having a single high-risk cutover event.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your company has a 10-year-old monolith that's become hard to scale and deploy. How would you migrate to microservices without a risky big-bang rewrite?"

**You (architect answer):**

> "I would explicitly reject a big-bang rewrite — rewriting 10 years of business logic from scratch, then cutting over all at once, is one of the highest-risk moves available, and it's also usually where these migrations fail in practice, because the new system is validated against real production traffic for the first time on the same day it fully replaces the old one.
>
> Instead, I'd use the strangler fig pattern: put a routing facade in front of the monolith, and migrate ONE capability at a time, starting with something read-heavy and low-risk, like the product search feature, not the checkout flow. Only that one route gets redirected to the new service; everything else keeps hitting the monolith completely unchanged. If the new search service has a problem, the fix is flipping one route back, not rolling back a company-wide migration.
>
> While the new service is being built, if it still needs to read data the monolith owns, I'd put an anti-corruption layer between them — a thin translation layer that converts the monolith's 10 years of schema quirks into the new service's clean domain model at the boundary, so none of that legacy mess leaks into the new codebase.
>
> As more capabilities move over and each new service gets its own database — which I'd insist on, specifically so services can't get silently re-coupled through a shared table the way they were coupled through shared code in the monolith — I'd expect some previously-trivial SQL JOINs to become cross-service API composition calls instead, and I'd budget for the added network latency that introduces, generally by parallelizing those calls rather than chaining them sequentially. And for any client-facing aggregation — mobile app, web app — I'd introduce a BFF per client type, so the underlying services can stay generically shaped rather than each one trying to satisfy three different consumers' competing response formats."

---

## PART 5 — DECISION FRAMEWORK

| Pattern | Problem It Solves | Cost/Tradeoff |
|---|---|---|
| **Strangler fig** | Migrating off a monolith incrementally, without a risky big-bang cutover | Migration takes months-years; requires a routing facade and careful capability ordering |
| **Backend-For-Frontend (BFF)** | Multiple client types (mobile/web/partner) with competing response-shape needs | Extra layer to maintain per client type; can duplicate some aggregation logic across BFFs |
| **Anti-Corruption Layer** | New service needs legacy data without importing legacy schema quirks into its clean domain model | Extra translation code to maintain, but isolates and contains legacy mess to one boundary |
| **Database-per-service** | Prevents services re-coupling through shared tables | Cross-service reads that used to be a JOIN become API composition or a precomputed read model |
| **API composition** | Joining data across service boundaries at query time | Added per-request latency (mitigate with parallel fan-out); simplest to implement |
| **Precomputed/denormalized read model (CQRS-style)** | Frequent, performance-sensitive cross-service reads | More infra (event pipeline, separate read store) but much faster reads at higher scale |
