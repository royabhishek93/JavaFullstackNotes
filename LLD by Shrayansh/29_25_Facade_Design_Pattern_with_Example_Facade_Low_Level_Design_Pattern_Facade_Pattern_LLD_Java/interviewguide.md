# Interview Guide: Facade Design Pattern

## 🗣️ The Interview Scenario

> "Our `OrderService` currently requires the client to manually call `ProductDao.getProduct()`, `PaymentService.makePayment()`, `InvoiceService.generateInvoice()`, and `NotificationService.sendNotification()`, in that exact order, every time an order is placed. Every client of this service has re-implemented this same four-step sequence. How would you redesign this so clients don't need to know these internal steps — and while we're at it, explain how this is different from a Proxy and from an Adapter, since our team keeps mixing them up."

Facade questions test whether you understand *encapsulating orchestration complexity* behind one simple entry point, and — just as importantly — whether you can crisply distinguish it from two commonly-confused structural patterns: Proxy and Adapter.

## 🏗️ Architect's Explanation (For a New Developer)

Think about driving a car. As the driver (the "client"), you know exactly two things: pressing the accelerator makes the car go faster, and pressing the brake makes it slow down. That's it. You have **zero knowledge** of the actual complexity behind those two pedals — how the engine, the fuel injection system, the transmission, and dozens of other components interact with each other to actually make the car accelerate or decelerate. You don't need to know, and frankly, you shouldn't have to.

That's the entire idea of the Facade pattern: **hide a complex system's internal components behind one simple, easy-to-use interface.** The "system" can have a hundred classes wired together in complicated ways — the Facade doesn't replace or remove any of that complexity, it just gives the client **one clean door** to walk through instead of forcing them to understand and correctly sequence all hundred classes themselves.

Two things to always keep in mind about Facade:
1. **It's not mandatory.** A client is always free to bypass the facade and talk to the underlying system's classes directly, if they specifically need finer control. The facade is a convenience layer, not a locked door.
2. **The facade takes on the responsibility of creating and wiring the objects it depends on.** In the employee example, `EmployeeFacade` internally constructs (or is given) the `EmployeeDao` object it needs — the client never has to construct or know about `EmployeeDao` at all.

## 📊 Visualize It

**Basic structure — hiding a complex system:**
```
                    Client
                      │  (only calls simple, high-level methods)
                      ▼
                 ┌─────────┐
                 │ Facade  │
                 └─────────┘
                      │  (internally coordinates many classes)
        ┌─────────────┼─────────────┬──────────────┐
        ▼             ▼             ▼              ▼
    ProductDao   PaymentService  Invoice      Notification
                                 Service        Service
   (complex subsystem — client never sees or calls these directly)
```

**Concrete example — `OrderFacade.createOrder()`:**
```
Client
  │  orderFacade.createOrder(...)
  ▼
OrderFacade
  │  1. product = productDao.getProduct()
  │  2. payment = paymentService.makePayment()
  │  3. invoice = invoiceService.generateInvoice()
  │  4. notificationService.sendNotification()
  ▼
"Order created successfully" ──► returned to Client
```

**Facades composing other facades:**
```
CheckoutFacade
   ├─ uses ──► OrderFacade   (which itself wraps ProductDao, etc.)
   └─ uses ──► PaymentFacade (which itself wraps 10-15 payment steps)

Client ──► checkoutFacade.checkout()  (one call does an entire order + payment flow)
```

**Facade vs. Proxy vs. Adapter (structural comparison):**
```
FACADE:    Client ──► Facade ──► {many different classes / whole subsystem}
                       (simplifies access to MANY objects)

PROXY:     Client ──► Proxy ──► SAME single object (same interface, one impl)
                       (controls/guards access to ONE specific object)

ADAPTER:   Client ──► Adapter ──► Incompatible existing interface
                       (translates between two INCOMPATIBLE interfaces)
```

## 🔧 Deep Dive: How It Actually Works

### When to reach for Facade

The single rule to internalize: **use Facade whenever you need to hide system complexity from the client.** If a client would otherwise need to know about, construct, and correctly sequence multiple classes just to accomplish one logical task, that's your signal.

### Scenario 1 — Reducing an overwhelming interface (the `EmployeeDao` example)

`EmployeeDao` (a Data Access Object — a class responsible for talking to the database: insert, update, select) can easily accumulate 50-100 methods over time: `insert`, `updateEmployeeName`, `updateEmployeeAddress`, `getEmployeeDetailByEmployeeId`, `getEmployeeDetailByEmail`, and so on. But a given client might only ever care about **two** of those: inserting an employee and fetching employee details by ID. Instead of exposing the entire 100-method `EmployeeDao` to that client, introduce an `EmployeeFacade` that:
- Holds an `EmployeeDao` instance internally (the facade takes responsibility for creating/holding this dependency).
- Exposes only the two methods the client actually needs: `insert(...)` and `getEmployeeDetail(employeeId)`.

The client's code becomes trivially simple — it only ever sees and calls `employeeFacade.getEmployeeDetail(...)`, with zero visibility into the other 98 methods sitting unused on `EmployeeDao`.

### Scenario 2 — Orchestrating a multi-step business process (the `OrderFacade` example)

Consider a subsystem with independent classes: `Product` (with `getProduct()`), `Payment` (with `makePayment()`), `Invoice` (with `generateInvoice()`), and `Notification` (with `sendNotification()`). Creating an order requires calling all four, **in a specific sequence**: get product → make payment → generate invoice → send notification.

Without a facade, the client itself would need to know this entire sequence and call all four classes directly. This creates two concrete, serious problems (both explicitly called out in the transcript):
1. **Sequence changes ripple to the client.** If tomorrow a new step gets added to order creation (say, a fraud-check step between payment and invoice), every client that manually orchestrates these calls must be updated, or the flow silently becomes wrong.
2. **Signature/return-type changes ripple to the client.** If `Payment.makePayment()` changes its return type from `int` to `void` (or `Invoice.generateInvoice()` changes from returning `boolean` to something else), every client directly calling these methods breaks.

The fix: introduce an `OrderFacade` with one method, `createOrder(...)`, that internally performs all four steps in the correct order and returns a simple confirmation ("order created successfully"). Now, if the internal sequence changes or a class's return type changes, **only the facade needs to be updated** — the client, which only ever calls `orderFacade.createOrder(...)`, remains completely unaffected. This is the core value proposition: the facade absorbs the blast radius of internal changes.

### Scenario 3 — Facades composing other facades

A facade is not limited to wrapping raw subsystem classes — it can also **use another facade**. For example, `PaymentFacade` might internally wrap 10-15 raw payment steps behind one `makePayment()` call. A higher-level `CheckoutFacade` can then internally call **both** `OrderFacade` and `PaymentFacade` (first create the order, then make the payment), composing them into an even higher-level single operation: `checkoutFacade.checkout()`. This composability is explicitly called out as part of what makes Facade "much more powerful and easy to use" — you can build layered facades, each hiding progressively more complexity, without the client ever needing to peel back a layer.

### Facade vs. Proxy — the key distinguishing test

Both patterns insert an intermediary between the client and "the real thing," which is why they get confused. The distinguishing test:
- **Proxy** wraps **one single object**, and the proxy implements the **exact same interface** as that one object (e.g., `EmployeeDtoProxy` implements the same interface as `EmployeeDtoImpl`, and only ever stands in for that one specific object/interface pairing — it cannot simultaneously represent an unrelated object like `OrderDto`).
- **Facade** wraps **an entire subsystem of many different classes/objects**, and does not need to share any interface with them — it exposes a brand-new, simplified interface of its own choosing.

So: Proxy = "one object, controlled/guarded access, same interface." Facade = "many objects, simplified access, new interface."

### Facade vs. Adapter — the key distinguishing test

- **Adapter** exists because the client and an existing interface are **incompatible** — they simply cannot talk to each other as-is (different method signatures, different data formats), and the adapter's entire job is translation/compatibility.
- **Facade** exists to **hide complexity**, not to solve an incompatibility problem — the underlying subsystem classes are perfectly usable on their own; the facade just spares the client from having to learn and orchestrate all of them.

So: Adapter = "these two things can't talk to each other; let me translate." Facade = "these things could talk directly, but that's needlessly complex for the client; let me simplify."

## 🔥 Real Production Incident & Fix

**What broke:** An e-commerce backend had no `OrderFacade` — every client service (the mobile app's checkout controller, the admin panel's "create order on behalf of customer" tool, and a batch job that re-processed failed orders) each independently called `ProductService.getProduct()`, `PaymentService.makePayment()`, `InvoiceService.generateInvoice()`, and `NotificationService.sendNotification()` in their own hand-written sequence. When the fraud team mandated a new **fraud-check step** be inserted between payment and invoice generation for regulatory compliance, the change was applied to the mobile checkout controller and the admin panel — but the batch re-processing job was owned by a different team and was missed entirely.

**How the team noticed:** Three weeks after the fraud-check rollout, the finance team flagged a reconciliation discrepancy: a batch of retried orders had invoices and notifications generated **without** the mandatory fraud check ever running, some of which turned out to be fraudulent chargebacks. The incident was traced by comparing invoice-generation timestamps against the fraud-check service's audit log and finding a gap specifically correlated with orders originating from the batch job.

**Root cause:** The order-creation sequence was duplicated across three independent clients instead of being owned by a single piece of code, so a process change (adding a mandatory step) had no single place to apply — it depended on every team remembering to update their own copy of the sequence, and one team simply wasn't in the loop.

**The fix:** The team introduced an `OrderFacade.createOrder(...)` method that owned the entire sequence (product → fraud-check → payment → invoice → notification) as the **only** sanctioned way to create an order, and migrated all three clients (mobile checkout, admin panel, batch job) to call it instead of orchestrating the steps themselves. The next time a step needed to be added (a loyalty-points-award step), it was added in one file, and all three clients picked it up automatically on their next deploy with no code changes on their end.

```
BEFORE: 3 clients each duplicate the order-creation sequence
  MobileCheckout ─┐
  AdminPanel      ├─► each manually calls: product → payment → invoice → notify
  BatchJob       ─┘     (missed the new fraud-check step entirely)

AFTER: one OrderFacade owns the sequence; clients just call createOrder()
  MobileCheckout ─┐
  AdminPanel      ├─► OrderFacade.createOrder()  (owns: product → fraud-check
  BatchJob       ─┘                                → payment → invoice → notify)
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Does using a Facade mean clients can never access the underlying subsystem classes directly?**
No — Facade is explicitly not meant to be a mandatory gate; a client with a specific need for finer-grained control is always free to bypass the facade and call the underlying classes directly, and the facade should never be designed in a way that locks that door.

**Q2: How do you decide what to put inside the Facade versus what to leave exposed to clients?**
Expose only the operations that represent the client's actual intent/use case (e.g., "create an order," "get employee detail") and hide everything the client doesn't conceptually need to know about (e.g., the 98 unused methods on a DAO, or the internal ordering of a 4-step process) — the test is "does the client care about this detail to accomplish their goal?"

**Q3: If `PaymentService.makePayment()` changes its return type, who needs to change their code?**
Only the Facade — since the client only ever calls `orderFacade.createOrder(...)` and never touches `PaymentService` directly, the facade absorbs the change and the client remains completely insulated, which is precisely the resilience benefit facades provide.

**Q4: Can a Facade have business logic in it, or should it be a pure pass-through?**
It's expected and normal for a Facade to contain the sequencing/orchestration logic (call product, then payment, then invoice, then notification, in that specific order) — that sequencing knowledge has to live *somewhere*, and putting it in the Facade (rather than duplicating it across every client) is exactly the point of the pattern.

**Q5: How is Facade different from a plain "helper" or "utility" class?**
A utility class is usually a stateless bag of unrelated static methods with no cohesive purpose, while a Facade specifically wraps and owns a related **subsystem** of collaborating classes to expose one simplified, purposeful entry point for a specific client use case — the distinction is about intentional encapsulation of a subsystem's complexity, not just grouping code together.

**Q6: Give a concrete example of "Facade using another Facade" and why that's useful.**
`CheckoutFacade.checkout()` can internally call `OrderFacade.createOrder()` and then `PaymentFacade.makePayment()`, letting each lower-level facade own its own internal complexity (order creation's 4 steps, payment's 10-15 steps) while `CheckoutFacade` composes them into one even-higher-level operation — this layering lets you build increasingly simple entry points without collapsing everything into one giant class.

## 🔑 Key Takeaway

Reach for Facade whenever a client would otherwise need to know, construct, and correctly sequence multiple subsystem classes just to accomplish one task — and be ready to instantly distinguish it from Proxy ("one object, same interface, controlled access") and Adapter ("solves incompatibility"), since Facade is purely about hiding complexity.
