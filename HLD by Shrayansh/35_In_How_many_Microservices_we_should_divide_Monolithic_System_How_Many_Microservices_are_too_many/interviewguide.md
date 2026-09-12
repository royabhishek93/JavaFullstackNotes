# Interview Guide: Decomposing a Monolith — How Many Microservices Is "Right"?

## 🗣️ The Interview Scenario

> "We're breaking up our monolithic order-management platform into microservices. As the architect, how would you decide how many services to create? Is there a magic number — five, ten, twenty? Walk me through your actual decision process, not just a gut-feeling answer."

This is a deliberately open-ended, trap-laden question. Interviewers ask it precisely because most candidates panic and try to guess a number. A strong candidate immediately rejects the premise of "a number" and instead presents a **repeatable methodology**.

## 🏗️ Architect's Explanation (For a New Developer)

Here's the first thing I tell every junior engineer: **there is no magic number of microservices.** Anyone who tells you "always aim for 8 services" or "never go below 5" is guessing. The real question isn't "how many?" — it's "does each service earn its right to exist independently?"

Think of it like splitting a big shared apartment into separate flats. You wouldn't just draw random walls. You'd ask: can each flat have its own front door (deploy independently)? Its own utility meter (scale independently)? Can the people inside manage their own space without constantly needing to walk into the neighbor's flat for basic things (low communication overhead)? If yes to all — that's a good flat boundary. If a "flat" needs the neighbor's kitchen for every meal, you've drawn the wall in the wrong place.

So instead of counting services, we test **each candidate service against four properties**, and we use a structured technique called **Domain-Driven Design (DDD)** to help us *find* the candidate boundaries in the first place.

## 📊 Visualize It

```
MONOLITH: Chat Application
┌───────────────────────────────────────────┐
│  Auth | Messaging | Notifications | ...    │
│         (all one deployable, one DB)       │
└───────────────────────────────────────────┘
                     │
      DDD: Event Storming → Bounded Context
                     ▼
┌───────────────┐ ┌───────────────┐ ┌────────────────────┐
│ User Mgmt Svc │ │ Message Svc   │ │ Notification Svc    │
│ (register,    │ │ (sent,        │ │ (user notified,     │
│  login,       │ │  delivered,   │ │  seen, email sent)  │
│  logout)      │ │  deleted)     │ │                      │
└───────────────┘ └───────────────┘ └────────────────────┘
   loosely coupled • independently deployable • independently scalable
```

Failure mode — the "distributed monolith" (Amazon Prime Video's real incident):

```
BEFORE (over-decomposed, tightly coupled):
  [Audio Service] <──sync, chatty calls──> [Video Service]
        both must scale together, both must deploy together
        = microservices in name, monolith in behavior

AFTER (merged back for real independence & 90% cost efficiency):
  [Audio+Video Monolith Component] ── talks loosely to other real microservices
```

## 🔧 Deep Dive: How It Actually Works

### Step 0 — Why do we want microservices at all? (The 4 acceptance tests)

Before deciding *how many*, define *why*. A candidate split only counts as "one microservice" if it satisfies all four:

1. **Loosely coupled** — updating service A should never force an update to service B.
2. **Independent build/test/deploy** — each service has its own engineers, its own release cadence, evolving independently.
3. **Low communication overhead** — services shouldn't need to chat back and forth for every trivial operation (chattiness = hidden coupling = higher latency).
4. **Independent scaling** — if service A gets 10x the traffic, you scale only A's instances, not B's.

If splitting a monolith produces "services" that fail these tests, you haven't created microservices — you've created a **distributed monolith** (all the network overhead of microservices, none of the benefits).

### Step 1 — Alternative slicing strategies (mentioned, but not preferred)

The transcript calls out that different engineers slice differently depending on what they're optimizing for:
- **Database-per-service vs shared database** focus.
- **Configuration-based** split (e.g., separate read config service vs write config service).
- **Technology-based** split (e.g., UI service, Java backend service, data-access service — three services purely because of three different tech stacks).

These are valid in some contexts, but the recommended, more rigorous approach for an interview answer is **Domain-Driven Design (DDD)**.

### Step 2 — The DDD Process (this is the actual algorithm to describe in the interview)

**(a) Understand the Domain**
Sit with domain experts and users. Nail down the problem statement first. Example domain: *"Chat Application."*

**(b) Identify Subdomains via Event Storming**
Event Storming is a collaborative workshop technique:
- **Round 1 — Brainstorm events:** All stakeholders (not just engineers — product, testers, decision-makers) independently list every domain event they can think of. Example events for a chat app: `UserRegistered`, `UserLoggedIn`, `MessageSent`, `MessageDelivered`, `MessageDeleted`.
- **Round 2 — Sequence the events & find gaps:** Arrange events chronologically. This surfaces missing events (e.g., realizing `UserLoggedOut` was never mentioned, or that `MessageDelivered` and `MessageReceived` are two separate events that can happen in parallel branches after `MessageSent`).

**(c) Identify Bounded Contexts**
This is the step most engineers get wrong, so understand it precisely: a **bounded context** is a boundary within which a given object/term has one specific, consistent meaning.
- Classic analogy from the transcript: a **sandwich in a restaurant** context means something you pay for and eat. The *same* sandwich object **in a garbage bin** context means something worthless nobody will touch. Same object, two utterly different meanings — because the *context* changed. These are different bounded contexts, and code/data for one should never leak into the other.
- Applying this to the chat app: `UserRegistered`, `UserLoggedIn`, `UserLoggedOut` all operate on a `User` object that carries meaning like authentication, authorization, and permissions → group them into a **User Management** bounded context.
- `MessageSent`, `MessageDelivered`, `MessageDeleted` operate on a `Message` object with meaning like sender, content, status (pending/delivered/deleted) → **Message** bounded context.
- `UserNotified` *also* touches something called "user" — but here it's barely more than a `userId` plus notification status. It does **not** carry the authentication/authorization meaning from the User Management context, so despite sharing a name, it does **not** belong there. It becomes its own **Notification** bounded context.

**(d) Derive Microservices from Bounded Contexts**
Each bounded context → one candidate microservice: `UserManagementService`, `MessageService`, `NotificationService`. If multiple events map to the *same* object with the *same* meaning, they collapse into **one** service — you don't fragment further just because there are multiple events.

### Step 3 — Accept minimal duplication, reject high dependency

Some duplication (e.g., `userId` appearing in both `User` and `Message` services) is fine and expected. What DDD forbids is **heavy dependency** between contexts — that would violate loose coupling and re-introduce the distributed-monolith trap.

### Step 4 — Guard against the "distributed monolith" anti-pattern

Real-world proof point cited in the transcript: **Amazon Prime Video** split Audio and Video into two microservices, but they ended up so tightly coupled (chatty, must-scale-together) that the overhead outweighed the benefit. Amazon's team **merged them back into one component** and reported a **90% efficiency gain** — while still keeping the rest of their architecture on microservices. The lesson: *don't confuse "many small deployables" with "good microservice boundaries."*

## 🔥 Real Production Incident & Fix

**What broke:** A fintech startup split its monolithic "Payments" module into 6 microservices purely along technical layers (API layer, validation layer, ledger-write layer, notification layer, audit layer, reconciliation layer) without doing any domain analysis.

**How it was detected:** The on-call team noticed that a single "process refund" customer request was generating **11 synchronous inter-service HTTP calls** before returning a response. This was found via **distributed tracing (Jaeger)** — the trace waterfall for one refund request was longer than the entire page. APM dashboards (Datadog) showed p99 latency for `POST /refund` had crept from 180ms to 2.3s over two quarters as more "layer services" were bolted on.

**Root cause:** The team had decomposed by *technical layer*, not by *business subdomain/bounded context*. Every business operation (refund) needed nearly every "service" to participate synchronously, meaning none of them could deploy, scale, or fail independently — a textbook distributed monolith.

**The fix:** The team ran a proper DDD event-storming exercise, identified real bounded contexts (`RefundLifecycle`, `LedgerService`, `NotificationService`), merged the 6 technical-layer services down to 3 domain-oriented ones, and moved cross-service side effects (notifications, audit logging) to **async events** instead of synchronous calls. p99 latency dropped back to ~200ms and on-call incident volume for refunds fell by more than half the following quarter.

```
BEFORE: 1 request → 11 synchronous hops across "layer" services (fragile, slow)
Client → API-svc → Validate-svc → Ledger-Write-svc → Audit-svc → Notify-svc → ... (chain)

AFTER: 1 request → 1 sync call + async events (resilient, fast)
Client → RefundLifecycle-svc ──(publishes event)──▶ LedgerService (async)
                              └─(publishes event)──▶ NotificationService (async)
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: If DDD is the "right" way, why do so many teams still split by technology layer or database access?**
It's often a shortcut when domain expertise isn't available or the team is under deadline pressure — it *feels* faster because you don't need domain workshops. It works short-term for very small systems, but it tends to produce tightly coupled services because a single business operation almost always needs multiple technical layers, forcing synchronous chains between "services." DDD front-loads the analysis cost to avoid that long-term coupling tax.

**Q2: How do you know when a bounded context is genuinely different versus just a naming coincidence?**
Ask the domain expert whether the object carries the *same business rules and lifecycle* in both places. If a `User` in context A needs full authentication/authorization/permission state, but in context B it's reduced to just an ID plus one status field, they're different bounded contexts even though they share a name. The test is behavioral/semantic equivalence, not schema similarity.

**Q3: What's the actual failure mode of over-decomposition, and can you name a real example?**
The failure mode is the "distributed monolith" — many deployable units, but they're so chatty and interdependent that you get all the latency/operational cost of microservices with none of the independent-scaling or independent-deployment benefit. Amazon Prime Video's audio/video services are a well-documented public example: they merged two microservices back into one component and reported a 90% cost/efficiency improvement.

**Q4: How does bounded-context thinking affect database design?**
Each bounded context typically owns its own data store (or at least its own schema/tables) and never lets another context reach in directly. Minimal duplicated fields (like a `userId` foreign key) are acceptable, but shared schemas or cross-context joins are a red flag that the boundary is wrong or that the services are more coupled than they claim to be.

**Q5: Can one bounded context ever map to more than one microservice, or vice versa?**
A single bounded context can be split into multiple microservices later purely for independent scaling reasons (e.g., splitting read and write within the same context), but you generally never want *multiple* bounded contexts collapsed into a single microservice — that reintroduces the "God service" anti-pattern the whole exercise was trying to avoid.

**Q6: What role do "tactical DDD" patterns (aggregates, entities, value objects) play beyond bounded contexts?**
Bounded context is "strategic DDD" — it tells you *where* the walls go. Tactical DDD (aggregates, entities, repositories, domain events) tells you how to model *inside* one bounded context so that consistency boundaries and transactional guarantees stay correct even without cross-service transactions.

## 🔑 Key Takeaway

There is no universal "correct number" of microservices — the right answer is a repeatable process (Domain-Driven Design → event storming → bounded contexts) validated against four hard tests: loose coupling, independent deploy, low communication overhead, and independent scaling. Say this out loud in the interview instead of guessing a number, and back it with the Amazon Prime Video "distributed monolith" cautionary tale.
