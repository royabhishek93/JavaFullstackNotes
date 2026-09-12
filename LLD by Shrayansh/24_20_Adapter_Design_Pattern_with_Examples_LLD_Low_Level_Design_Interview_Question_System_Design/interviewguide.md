# Interview Guide: Adapter Design Pattern

## 🗣️ The Interview Scenario

> "We have a `WeightMachine` interface that our legacy hardware SDK exposes, and it only reports weight in pounds. Our new client dashboard is built entirely around kilograms, and we can't touch the legacy SDK code (it's owned by a hardware vendor and shipped as a compiled JAR). How would you design a solution so the dashboard can consume this legacy interface without changing either side? Walk me through the classes you'd introduce."

This is a classic "integrate two incompatible interfaces without modifying either" prompt — exactly what the Adapter pattern exists for.

## 🏗️ Architect's Explanation (For a New Developer)

Think about your phone charger. Your wall socket outputs a certain plug shape (or in another country, a completely different shape), but your phone only accepts a USB-C cable. You don't rewire your phone, and you certainly don't take a hammer to the wall socket. Instead, you buy a small physical adapter that plugs into the socket on one end and gives you the connector your phone wants on the other end.

That little block is doing exactly one job: it **speaks two languages** — it knows how to talk to the "existing" thing (the socket), and it exposes the shape the "client" (your phone) expects. Nothing about the socket changes, nothing about your phone changes. The adapter sits in the middle and translates.

In software terms:
- **Client** = the code that has expectations about what interface it wants to call.
- **Existing interface / Adaptee** = the thing that already exists and works, but speaks a different "shape" (different method names, different data format, different units).
- **Adapter** = a new class that implements the interface the client wants, and internally holds/calls the existing interface, translating between the two.

That's it. No business logic changes on either side — the adapter is a pure translation layer. This is why the Adapter pattern is classified as a **structural** design pattern: it's about composing existing pieces into a new shape, not about creating objects (creational) or changing runtime behavior of an algorithm (behavioral).

## 📊 Visualize It

**Class relationships (UML-style):**
```
                 uses                          implements
   Client  ─────────────────►  AdapterInterface ◄───────────────  ConcreteAdapter
(expects AdapterInterface)      + request()                        + request()
                                                                         │
                                                                         │ has-a (composition)
                                                                         ▼
                                                                 ExistingInterface / Adaptee
                                                                  (adaptee's own methods)
```

Notice this pattern uniquely combines **both** relationships in one place:
- `ConcreteAdapter` **is-a** `AdapterInterface` (implements it, so the client can call it polymorphically).
- `ConcreteAdapter` **has-a** `Adaptee` (holds a reference, so it knows how to delegate to the existing code).

**Concrete example — Weight Machine (pounds → kilograms):**
```
 Client (dashboard, understands only KG)
     │  calls
     ▼
WeightMachineAdapter (interface)
   + getWeightInKgs()
     ▲
     │ implements
WeightMachineAdapterImpl (concrete adapter)
   + getWeightInKgs() {
        pounds = weightMachine.getWeightInPound();   // delegate to adaptee
        return convertPoundsToKg(pounds);             // translate
     }
     │  has-a
     ▼
WeightMachine (existing interface / adaptee)
   + getWeightInPound()   // returns e.g. 28
```

**Runtime interaction sequence:**
```
Client              WeightMachineAdapterImpl        WeightMachine
  │  getWeightInKgs()      │                             │
  │────────────────────────►                             │
  │                        │   getWeightInPound()        │
  │                        │─────────────────────────────►
  │                        │        returns 28 (lbs)      │
  │                        │◄─────────────────────────────
  │                        │  convert 28 lbs → 12.7 kg    │
  │   returns 12.7 (kg)    │                             │
  │◄────────────────────────                             │
```

## 🔧 Deep Dive: How It Actually Works

### The core structure from the transcript's weight-machine example

1. **`WeightMachine` (Adaptee / existing interface)** — already exists in production. It has a method like `getWeightInPound()` and simply returns weight, e.g., `28` (pounds). You cannot and should not touch this class — it might be a vendor SDK, or ten other components might already depend on it as-is.

2. **`WeightMachineAdapter` (Adapter interface)** — a brand-new interface that declares exactly what the **client** wants: `getWeightInKgs()`. This is the "shape" the client understands.

3. **`WeightMachineAdapterImpl` (Concrete Adapter)** — implements `WeightMachineAdapter`, and internally **holds a reference** to a `WeightMachine` instance (composition/has-a). Inside `getWeightInKgs()`, it:
   - Calls `weightMachine.getWeightInPound()` to get the raw value from the existing interface.
   - Applies the conversion logic (`pounds * 0.453592`).
   - Returns the converted value in the format the client expects.

4. **Client** — only ever talks to the `WeightMachineAdapter` interface. It has zero knowledge that a pound-based system exists underneath.

### Other real-world variants covered in the transcript (use these to show breadth in an interview)

- **Power socket / power adapter**: square socket (existing interface) vs. oval plug (client) — adapter has a square pin on one side and an oval socket on the other, bridging the two shapes.
- **XML → JSON adapter**: a server returns XML, but the client only understands JSON. An adapter class calls the XML-returning service, parses it, and republishes it as JSON.
- **Anti-corruption layer for external vendors**: if your company depends on an external partner's API and that partner changes their response format (e.g., from `"1"` to `"1#"`), and 10 internal components consume that response directly, *all 10* break. Instead, route every internal consumer through **one adapter**. When the vendor changes their format, you update **one place** (the adapter's translation logic), and all 10 consumers keep working unmodified. This is arguably the most important interview-relevant use case — it demonstrates you understand adapters as a **resilience/isolation boundary** against third-party API churn, not just a unit-conversion trick.
- **USB-C charging cable**: the wall socket is the adaptee, your phone is the client, the cable/adapter bridges them.

### Why it's a Structural pattern

The three GoF categories are Creational, Structural, Behavioral. Adapter is Structural because its whole purpose is **clubbing together two or more existing objects/interfaces to form a bigger, usable structure** — it doesn't create new object lifecycles (that's creational) and it doesn't change an algorithm's runtime behavior (that's behavioral).

### Quick code skeleton (Java-style)

```java
interface WeightMachine {
    double getWeightInPound();
}

// existing / adaptee — do not modify
class InfantWeightMachine implements WeightMachine {
    public double getWeightInPound() { return 28.0; }
}

// what the client wants
interface WeightMachineAdapter {
    double getWeightInKgs();
}

// concrete adapter — bridges the two
class WeightMachineAdapterImpl implements WeightMachineAdapter {
    private final WeightMachine weightMachine; // has-a adaptee

    WeightMachineAdapterImpl(WeightMachine weightMachine) {
        this.weightMachine = weightMachine;
    }

    public double getWeightInKgs() {
        double pounds = weightMachine.getWeightInPound();
        return pounds * 0.453592; // translation logic
    }
}
```

## 🔥 Real Production Incident & Fix

**What broke:** A mid-size fintech company integrated a third-party KYC (Know Your Customer) verification vendor. Ten different microservices — onboarding, fraud-check, loan-approval, compliance-reporting, and six others — each called the vendor's REST API **directly** and parsed the JSON response themselves, pulling out a field like `"verificationStatus": "1"` (where `"1"` meant "verified").

One weekend, the vendor pushed a "backward compatible" API update (their words) that changed the status field from a bare code `"1"` to a structured object `{"code": "1", "reason": null}`. Within an hour of the vendor's rollout, the on-call engineer for the fraud-check service started getting paged: verification checks across **all ten services** started failing silently, because each service's ad-hoc parsing code (`response.get("verificationStatus").equals("1")`) now compared a string against a JSON object and always evaluated `false`.

**How the team noticed:** Dashboards showed KYC "verified" rates dropping from ~92% to ~0% within minutes, and the compliance-reporting service started throwing `ClassCastException` in logs when trying to cast the new object shape to a `String`. A flood of customer complaints ("my account got flagged as unverified even though I completed KYC yesterday") hit support within the hour.

**Root cause:** No isolation layer between the vendor's response format and 10 internal consumers. Every team had copy-pasted their own parsing logic directly against the vendor's raw JSON shape — exactly the "existing interface changes and breaks everyone" scenario the transcript warns about.

**The fix:** The team introduced a single `KycVendorAdapter` class implementing an internal `KycVerificationPort` interface (`isVerified(userId)`, `getReason(userId)`). All 10 services were migrated to depend only on `KycVerificationPort`. The adapter became the **only** piece of code that touched the vendor's raw response shape. When the vendor changed formats again six months later (as vendors do), the team updated the adapter's parsing logic in one file, deployed it, and zero downstream services needed a code change or redeploy.

```
BEFORE (fragile — 10 services coupled to vendor's raw shape)
 Service A ─┐
 Service B ─┼──► directly parses vendor JSON  ──► vendor format change = 10 breakages
 ... (x10) ─┘

AFTER (resilient — single adapter absorbs vendor changes)
 Service A ─┐
 Service B ─┼──► KycVerificationPort (stable) ──► KycVendorAdapter ──► Vendor API
 ... (x10) ─┘                                     (only place that knows vendor's raw shape)
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: How is the Adapter pattern different from the Facade pattern?**
Facade simplifies/hides a *complex subsystem* behind one easy method (reducing many calls to one), while Adapter's job is purely *translation between two incompatible interfaces* that otherwise couldn't talk to each other at all. Facade doesn't necessarily involve incompatibility — it's about convenience; Adapter exists specifically because two contracts don't match.

**Q2: Is Adapter a creational, structural, or behavioral pattern, and why?**
It's structural — its purpose is composing/bridging existing interfaces into a usable structure for the client, not managing object creation lifecycles (creational) or changing runtime algorithmic behavior (behavioral).

**Q3: Can you have a "two-way" adapter, and when would you need one?**
Yes — a bidirectional adapter implements both interfaces and can translate calls in either direction, useful when two legacy systems need to talk to each other in both directions (e.g., an old XML-based system and a new JSON-based system both need to send/receive from each other). In practice most real systems just chain two one-way adapters instead, since bidirectional adapters get complex.

**Q4: What's the difference between a "class adapter" (via inheritance) and an "object adapter" (via composition)?**
A class adapter extends the adaptee class and implements the target interface (multiple inheritance via interfaces in Java), tightly coupling the adapter to one specific adaptee class. An object adapter (the version shown in this transcript, and the one used almost universally in Java) holds a reference/composition to the adaptee instance, which is more flexible because it can adapt any subclass of the adaptee at runtime and doesn't require inheritance.

**Q5: Doesn't introducing an adapter add an extra layer of indirection/performance overhead?**
Yes, technically one extra method call and possibly an object translation cost, but it's usually negligible compared to network/IO calls already involved (as in the vendor API example), and the resilience/maintainability benefit — one place to fix instead of ten — vastly outweighs the marginal CPU cost.

**Q6: When would you NOT use an Adapter?**
If you own both sides of the interface and can freely change either, it's often simpler to just make them compatible directly rather than adding an indirection layer — Adapter earns its keep specifically when one side is immutable (a legacy system, third-party SDK, or external vendor API) and you can't or shouldn't change it.

## 🔑 Key Takeaway

Adapter is a translation layer, not a business-logic layer — reach for it whenever you must connect a client to an existing/external interface you cannot change, especially as a resilience boundary against third-party API changes.
