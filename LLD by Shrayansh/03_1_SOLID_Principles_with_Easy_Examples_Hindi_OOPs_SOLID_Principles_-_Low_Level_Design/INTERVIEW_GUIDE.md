# 🧱 SOLID Principles - Interview Guide
## _15 YOE Architect-Level Conversational Script_

**📗 Difficulty: Beginner** — ideal starting point for a new developer; read this before tackling applied system-design questions.

> _(Companion to `transcript.md`, left untouched. Whiteboard-style scenario discussion, the foundation every other guide in this repo builds on.)_

---

**Interviewer**: "Walk me through SOLID principles with real examples, not just definitions."

**You**: "SOLID is 5 principles that, together, keep code easy to maintain, understand, and extend as it grows. Let me take you through each with the exact example that makes it click."

---

## 1. Single Responsibility Principle (SRP) — "A class should have only ONE reason to change"

```
❌ BEFORE (violates SRP):                     ✅ AFTER (follows SRP):
┌─────────────────────┐                  ┌──────────┐   ┌───────────────┐   ┌──────────┐
│      Invoice              │                  │  Invoice   │   │ InvoicePrinter     │   │ InvoiceRepo  │
│  - calculateTotal()          │                  │ (data +   │   │ (printInvoice)       │   │ (saveToDB,   │
│  - printInvoice()            │                  │ calculate  │   └───────────────┘   │  saveToFile) │
│  - saveToDB()                  │                  │  Total only)│                                     └──────────┘
│  - saveToFile()                 │                  └──────────┘
│  3 REASONS to change:            │                  1 reason each to change:
│  pricing logic, print format,     │                  Invoice changes only if pricing
│  storage format                    │                  logic changes; printer only if
└─────────────────────┘                  format changes; repo only if storage changes
```

**You**: "Ask: *if I add GST/tax calculation, which classes change?* In the 'before' version, `Invoice` changes for pricing AND printing AND storage reasons — three unrelated triggers for change in one class. Split them, and each class now has exactly one reason to change."

---

## 2. Open/Closed Principle (OCP) — "Open for extension, CLOSED for modification"

```
❌ BEFORE: modifying an already-tested, LIVE class          ✅ AFTER: extend via interface
┌─────────────────────┐                          ┌────────────────┐
│  InvoiceDao (already live) │                          │  InvoiceDao (I)      │
│  + saveToDB()                  │                          │  + save()               │
│  + saveToFile()  <- added later,│                          └────────┬───────────┘
│      MODIFIES tested class!     │                              ┌─────┴──────┐
└─────────────────────┘                          ▼               ▼
                                              ┌─────────┐   ┌───────────┐
                                              │ DBSaver     │   │ FileSaver     │
                                              │ (untouched) │   │ (NEW, isolated) │
                                              └─────────┘   └───────────┘
```

**You**: "The moment you add `saveToFile()` directly onto an already-live, already-tested `InvoiceDao` class, you're **re-risking tested code** for every new persistence type. Extract an interface; new persistence types become new classes that extend, never modify."

---

## 3. Liskov Substitution Principle (LSP) — "Child must be substitutable for Parent WITHOUT breaking the program"

_(Deep-dive with full solution in the dedicated LSP guide — summary here.)_

```
Vehicle.hasEngine() -> true (default)
  ├── Motorcycle (inherits, true)
  ├── Car (inherits, true)
  └── Bicycle (OVERRIDES to return null!)   ❌ reduces capability -> NullPointerException
                                                   downstream when client calls .hasEngine().toString()
```

**You**: "LSP is violated the moment a subclass REDUCES capability the parent promised, breaking client code that relied on that capability existing for ALL vehicles."

---

## 4. Interface Segregation Principle (ISP) — "Don't force a class to implement methods it doesn't need"

```
❌ BEFORE: one fat interface                    ✅ AFTER: segregated, focused interfaces
┌─────────────────────┐                ┌───────────┐  ┌────────────┐
│  RestaurantEmployee (I)      │                │ Waiter (I)   │  │ Chef (I)         │
│  + washDishes()                  │                │ + serveCust()│  │ + cookFood()      │
│  + serveCustomer()                │                │ + takeOrder()│  │ + decideMenu()    │
│  + cookFood()                      │                └───────────┘  └────────────┘
│  + decideMenu()                    │
└─────────────────────┘
class Waiter implements RestaurantEmployee {  class Waiter implements Waiter {
  washDishes() { /* forced, unused! */ }         serveCustomer() { ... }     <- only what
  cookFood() { /* forced, unused! */ }           takeOrder() { ... }            it needs
  ... }
```

---

## 5. Dependency Inversion Principle (DIP) — "Depend on abstractions, not concrete classes"

```
❌ BEFORE: hardcoded to concrete classes          ✅ AFTER: depends on interfaces
┌──────────────┐                          ┌──────────────┐
│    Laptop          │                          │    Laptop          │
│  - WiredKeyboard      │  <- concrete class          │  - Keyboard (I)     │  <- interface
│  - WiredMouse           │  <- concrete class          │  - Mouse (I)         │  <- interface
└──────────────┘                          └──────────────┘
Cannot swap to Bluetooth without            Constructor injection: pass ANY
changing Laptop's code                        Keyboard/Mouse implementation
```

```java
class Laptop {
    private final Keyboard keyboard;    // interface, not WiredKeyboard/BluetoothKeyboard
    private final Mouse mouse;
    Laptop(Keyboard keyboard, Mouse mouse) {   // Constructor Injection
        this.keyboard = keyboard;
        this.mouse = mouse;
    }
}
new Laptop(new BluetoothKeyboard(), new WiredMouse());   // any combination works!
```

---

## Cross Questions

**Q: "Which SOLID principle is most frequently violated in real codebases, in your experience?"**
**A:** "SRP and OCP, by far — because they're violated *gradually*. A class starts clean, then 'just one more method' gets added repeatedly until it has 5 unrelated responsibilities (SRP violation), and 'just one more `if` branch' gets added to a tested method repeatedly until it's an unmaintainable decision tree (OCP violation). Neither happens in one bad commit — they erode over dozens of 'reasonable-looking' small commits, which is why code review discipline matters more than any single design decision."

**Q: "Do all 5 principles apply equally to every class, or is there a pragmatic limit?"**
**A:** "Pragmatically, yes — over-applying SOLID (e.g. creating an interface for every single class 'just in case') adds indirection without payoff, sometimes called 'premature abstraction'. Apply ISP/DIP proactively where you KNOW multiple implementations will exist (e.g. persistence layer, payment methods); for stable, unlikely-to-vary classes, a direct concrete dependency is fine and simpler."

---

## Senior Trap Questions

**Trap: "Doesn't following SOLID always mean more classes and more complexity upfront?"**
**✅ Senior answer:** "Yes, there's real upfront cost — more files, more indirection. The trade-off is deliberate: you're paying a small, constant upfront cost to avoid a much larger, compounding cost later (regression risk on every change, inability to test in isolation, inability to swap implementations). Senior-level judgment is knowing WHEN that trade-off is worth it — not applying SOLID dogmatically to every single class regardless of whether it will ever actually vary."

---

## 🔥 Real-World Production Issue: The SRP Violation That Caused a Multi-Team Outage

*In plain English: cramming unrelated responsibilities into one class means a bug in a low-stakes feature can take down a completely unrelated, critical one.*

**The war story:**

"A `UserAccountService` class handled user creation, password validation, AND — because 'it was convenient' — also synced user data to a third-party marketing analytics platform (SRP violation: 3 unrelated responsibilities, 3 unrelated reasons to change)."

```
┌────────────────────────────────────────────┐
│ class UserAccountService {                       │
│   createUser(...)             // core responsibility  │
│   validatePassword(...)       // core responsibility  │
│   syncToMarketingPlatform(...) // UNRELATED responsibility,│
│                                    added "for convenience"  │
│ }                                                            │
└────────────────────────────────────────────┘
        ⬇
   Marketing team pushed a change to `syncToMarketingPlatform()`
   that introduced an unhandled exception on a specific edge case
   (special characters in a user's name)
        ⬇
   Because it lived in the SAME class/deployment unit as `createUser()`,
   the exception propagated and caused ALL new user sign-ups
   (an unrelated, CRITICAL business function) to fail for 20 minutes
```

**Root cause:** two completely unrelated business capabilities (core account creation vs marketing analytics sync) were coupled into ONE class with ONE deployment lifecycle, purely because "it was convenient to add the method here." A bug in the low-stakes, rarely-changing marketing integration took down the high-stakes, business-critical sign-up flow — exactly the blast-radius risk SRP exists to prevent.

**The fix:**
- Extracted `MarketingSyncService` into its own class, and further, into its own asynchronous, decoupled process (a message queue consumer) so it could NEVER block or crash the core `UserAccountService` request path, even under bugs or third-party API outages.
- Added an architecture rule (via `ArchUnit`) forbidding `UserAccountService` from having any dependency on marketing/analytics packages, enforced in CI so this coupling could never silently creep back in.

**Lesson for a new developer:** "SRP isn't an academic nicety — 'this class has more than one reason to change' is a direct predictor of blast radius when something in ANY of those responsibilities breaks. Before adding 'just one more method' to an existing class, ask: does this new method share the SAME reason to change as the existing ones? If not, it belongs in a new class, ideally in a separate deployable/testable unit."

---

## 🎓 Final Tips
1. **SRP**: one class, one reason to change — split by *reason for change*, not just by feature.
2. **OCP**: extend via new classes/interfaces; never modify already-tested, live classes.
3. **LSP**: a subclass must never reduce capability the parent guarantees — it breaks client code relying on that guarantee.
4. **ISP**: split fat interfaces so no implementer is forced to implement methods it doesn't need.
5. **DIP**: depend on interfaces, inject concrete implementations via constructor — never hardcode concrete classes.
6. In production, SOLID violations rarely cause immediate bugs — they quietly increase blast radius until an unrelated change causes an unexpected outage.

Good luck! 🚀
