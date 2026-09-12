# Interview Guide: Observer Design Pattern

## 🗣️ The Interview Scenario

> "This is an actual question we ask: On a product page on an e-commerce site, if an item is out of stock, there's a 'Notify Me' button. Design the system so that the moment the product comes back in stock, every customer who clicked 'Notify Me' gets notified — some by email, some by SMS, potentially both. Walk me through your class design, and make sure it's easy to add a new notification channel later without touching existing, tested code."

This is a real, frequently-asked low-level design question (asked in an actual interview at a large retailer) and is the textbook use case for the Observer pattern — one subject whose state changes needs to broadcast that change to a dynamic, pluggable set of interested parties.

## 🏗️ Architect's Explanation (For a New Developer)

Think of the Observer pattern as a subscription/newsletter system. You have **one publisher** (in pattern terms, the "Observable" or "Subject") — say, a specific product's stock status. You have **many potential subscribers** (the "Observers") — customers who want to know when that product's stock changes, and each subscriber might want to be reached differently (email vs. SMS). The publisher doesn't need to know *how* each subscriber wants to be notified or *how many* subscribers there are — it just maintains a list of "whoever is currently subscribed" and, whenever its own state changes, loops through that list and tells each one "hey, something changed, go do whatever you need to do." The subscribers, in turn, all agree to expose one common method (`update()`) that the publisher can call — so the publisher's code never has to change no matter how many new subscriber types get invented later.

## 📊 Visualize It

```
CLASS STRUCTURE
────────────────
      <<interface>>                    <<interface>>
      Observable                       Observer
      + add(Observer)                  + update()
      + remove(Observer)
      + notifyObservers()
             ▲                                ▲
             │ implements                     │ implements
             │                    ┌───────────┼──────────────┐
        StockObservable      EmailAlertObserver  MobileAlertObserver
        - List<Observer>     - email (injected    - mobileNumber (injected
        - stockCount           via constructor)      via constructor)
        + setStock(qty)      + update() {          + update() {
          (business logic:      sendEmail()}          sendMessageToMobile()}
          if stock 0→N,
          call notifyObservers())

Relationship: StockObservable "has-a" List<Observer>  (0..* — one subject, many observers)
```

```
RUNTIME SEQUENCE (Amazon "Notify Me" use case)
────────────────────────────────────────────────
1. StockObservable iPhoneStock = new StockObservable()
2. iPhoneStock.add(new EmailAlertObserver(iPhoneStock, "user1@mail.com"))
3. iPhoneStock.add(new MobileAlertObserver(iPhoneStock, "9999999999"))
4. iPhoneStock.setStock(10)      // stock was 0, now > 0 → trigger!
        │
        ▼
   notifyObservers()
        │
   ┌────┴─────┐
   ▼          ▼
EmailAlert  MobileAlert
.update()   .update()
   │          │
sendEmail() sendSms()
```

## 🔧 Deep Dive: How It Actually Works

### The two core interfaces

**`Observable` interface** — represents "the thing whose state changes and needs to broadcast that change." Declares:
- `add(Observer o)` — also known as **register/subscribe**; adds an observer to the internal tracking list.
- `remove(Observer o)` — unsubscribes an observer.
- `notifyObservers()` — takes **no parameters**; iterates every currently-registered observer and calls its `update()` method.
- `setStockCount(...)` / `getStockCount()` (or generically "set data / get data") — where the actual business state and business logic triggering a notification lives.

**`Observer` interface** — represents "anything that wants to be told when the observable changes." Declares a single method: `update()`.

### The concrete `Observable` implementation
A class like `StockObservable implements Observable` maintains `private List<Observer> observerList` internally (the **HAS-A relationship** is a `0..*` — "zero to many" — cardinality: one observable can have many observers). Its methods:
- `add(Observer o)` → `observerList.add(o)`.
- `remove(Observer o)` → `observerList.remove(o)`.
- `notifyObservers()` → loops `for (Observer obs : observerList) { obs.update(); }`.
- `setStockCount(int newStock)` → this is where the actual business rule lives: e.g., "if `currentStock == 0` and `newStock > 0`" (item was out of stock and just became available), then update `currentStock = newStock` and call `notifyObservers()`. This prevents redundant notifications — stock going from 20 → 15 shouldn't re-trigger "back in stock" alerts; only the `0 → N` transition should.

### Passing the observable's own data to observers: two design options
Once `notifyObservers()` calls `obs.update()`, how does the observer actually get the data it needs (e.g., the current stock count)? Two approaches were considered:

1. **Pass the `Observable` object as a parameter to `update(Observable obs)`.** The observer then has to `instanceof`-check and cast to figure out *which* concrete observable it received (since many different observables could implement the same `Observer`-facing interface) — described explicitly as an approach the author dislikes ("I don't like this — doing `instanceof` checks").
2. **Constructor injection instead (preferred approach).** When constructing a concrete observer (e.g., `EmailAlertObserver`), pass the specific `Observable` object it should watch directly into its constructor and store it as a field. Then `update()` can directly call `observableRef.getData()` (or the equivalent getter) without any casting or type-checking — this mirrors the same constructor-injection technique used in the Strategy pattern. The trade-off explicitly noted: this simpler approach works well for a single relationship, but if an observer legitimately needs to react differently depending on *multiple different kinds* of observables, `instanceof` checks (or a more advanced dispatch mechanism) become necessary again.

### Concrete observer implementations for the "Notify Me" feature
- **`EmailAlertObserver implements Observer`** — constructed with the specific `Observable` (e.g., a specific product's `StockObservable`) plus an email address. `update()` implementation: calls `sendEmail()` (pseudocode: "send mail to [email]").
- **`MobileAlertObserver implements Observer`** — constructed with the `Observable` plus a mobile number. `update()` implementation: pulls whatever data it needs from the observable (e.g., current stock count) and calls `sendMessageToMobile()`.

### Walking through the full "Notify Me" scenario
For a specific product (e.g., iPhone), create one `StockObservable`. As customers click "Notify Me," each selects a channel (email or mobile) — for each, construct the matching observer type (`EmailAlertObserver` or `MobileAlertObserver`), passing in the `StockObservable` reference and their contact detail, then call `iPhoneStockObservable.add(thatObserver)`. When the stock actually transitions from `0` to a positive number via `setStockCount(...)`, `notifyObservers()` fires, and every registered observer's `update()` runs — sending emails to the email subscribers and SMS messages to the mobile subscribers, in one pass, with **zero changes needed to the `Observable` implementation** regardless of how many observer types exist. Calling `setStockCount` again with another positive value does *not* re-trigger notifications, because the business rule only fires on the `0 → positive` transition.

### A second illustrative example: WeatherStation
A parallel example generalizes the same shape: a `WeatherStation` (the observable) periodically updates its current temperature; a `TVDisplay` and `MobileDisplay` (both implementing a `Display`/`Observer`-style interface) are registered as observers. Whenever the station's temperature changes, it calls `notifyObservers()`, and every registered display updates itself — again using constructor injection to give each display direct access to the specific weather station it's observing, avoiding `instanceof` checks, and even allowing the *same* observer interface to be reused for a completely different observable (e.g., a `CricketScoreObservable`) since the observer only needs to satisfy the shared `update()` contract.

## 🔥 Real Production Incident & Fix

**The incident:** An e-commerce team building the exact "Notify Me" feature initially implemented it *without* the Observer pattern — a single `StockService.setStock(productId, qty)` method containing a hard-coded block: `if (channel == EMAIL) { sendEmail(...) } else if (channel == SMS) { sendSms(...) }`, with subscriber contact info stored in two separate flat lists (`emailSubscribers`, `smsSubscribers`) inside the same class. Everything worked for the initial launch (email + SMS only).

**How the team noticed:** Three weeks later, product asked for a third channel — push notifications through the mobile app. The engineer assigned had to modify `StockService.setStock()` directly (the same method handling the already-live, already-tested email and SMS paths) to add a third `else if` branch and a third subscriber list. During QA regression testing, a tester found that SMS notifications had silently stopped firing for a subset of products — traced to a copy-paste error in the new push-notification branch that accidentally overwrote a shared loop-index variable also used by the SMS branch, because all three notification paths lived in one long method with shared local state.

**Root cause:** The design had no `Observable`/`Observer` abstraction at all — adding a new notification channel meant directly editing a shared, live method instead of extending the system by adding a new independent class, a direct Open/Closed Principle violation with the same blast-radius problem the Observer pattern is specifically designed to prevent (an observable's `notifyObservers()` loop should never need to change just because a new observer type is added).

**The fix:** The team refactored to a proper `Observable`/`Observer` structure: `StockObservable` (holding just the stock-change business logic and a generic `List<Observer>`), with `EmailAlertObserver`, `SmsAlertObserver`, and the new `PushNotificationObserver` each as fully independent classes implementing `Observer`. Adding push notifications required writing exactly one new class and registering instances of it — zero changes to the existing email/SMS code paths, and the SMS regression became structurally impossible to reintroduce via a push-notification change, since the two now share no code or state at all.

```
BEFORE: all channels in one method (fragile)     AFTER: Observer pattern (isolated)
──────────────────────────────────────────────   ───────────────────────────────────
StockService.setStock(id, qty) {                 StockObservable.setStock(qty) {
  if (email) sendEmail() ┐                          if (0 → N) notifyObservers()
  if (sms)   sendSms()   │ shared loop-index      }
  if (push)  sendPush() ─┘ var, one bug breaks         │  notifies list of...
             (new branch    an unrelated branch    ┌───┴──────┬─────────────┐
              added here)                      EmailAlert  SmsAlert   PushNotification
                                                Observer    Observer   Observer
                                                (independent classes, zero shared state)
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why does `notifyObservers()` take no parameters in this design, and where does the "what changed" data come from instead?**
A: Passing the changed data as a parameter through `update(data)` would tightly couple the `Observer` interface's signature to one specific observable's data shape, making it hard to reuse the same `Observer` interface across different kinds of observables. The preferred approach used here instead is constructor injection — the observer stores a reference to the specific observable it cares about and pulls whatever data it needs on demand inside its own `update()` implementation.

**Q2: What's the downside of passing the `Observable` object into `update(Observable obs)` and using `instanceof` to figure out the concrete type?**
A: It couples every observer implementation to knowing about every possible concrete observable type it might receive, requiring a growing chain of `instanceof` checks and casts as more observable types are introduced — brittle, and a maintenance burden every time a new observable type is added. It also violates the spirit of depending on abstractions rather than concrete types (echoing the Dependency Inversion Principle).

**Q3: How do you prevent duplicate/spam notifications if `setStockCount()` is called multiple times while stock is already positive?**
A: The business rule inside the observable's setter method should only call `notifyObservers()` on the specific transition that matters — in this case, "stock was zero and just became positive" — not on every single write. This state-transition check lives entirely inside the observable and never needs to be duplicated inside each observer.

**Q4: How would you support a customer who wants to be notified via *both* email and SMS for the same product?**
A: Simply register two separate observer objects (one `EmailAlertObserver`, one `MobileAlertObserver`, potentially both carrying the same underlying customer identity/contact details) against the same `Observable`. Since the observable just holds a list and calls `update()` on everything in it, supporting multiple channels per customer requires no special-casing at all — it falls out naturally from the list-based design.

**Q5: What's the cardinality between `Observable` and `Observer`, and why does that matter for the data structure choice?**
A: It's zero-to-many (`0..*`) — one observable can have any number of observers registered (including zero), which is exactly why the observable stores its observers in a `List` rather than a single reference; the list needs to support dynamic add/remove as subscriptions change over time.

**Q6: How is Observer different from just having the "subscriber" objects poll the subject on a timer to check for changes?**
A: Polling means every subscriber has to independently check "has anything changed yet?" repeatedly, wasting resources and adding latency between the actual change and the subscriber noticing it. Observer inverts this — the subject actively pushes a notification the *instant* its state changes, so subscribers react immediately and never waste cycles checking when nothing has changed.

## 🔑 Key Takeaway

Use the Observer pattern whenever one object's state change needs to reach an open-ended, pluggable set of interested parties — model it as an `Observable` holding a list of `Observer`s and calling a no-argument `notifyObservers()` on state change, and prefer constructor injection over passing the observable as a parameter so new observer types can be added without any `instanceof` checks or changes to existing code.
