# Interview Guide: SOLID Principles

## 🗣️ The Interview Scenario

> "Here's an `Invoice` class: it holds a marker's name, color, manufacturer, price, and quantity. It has `calculateTotal()`, `printInvoice()`, and `saveToDB()` methods. A few weeks after shipping this, product asks you to also save invoices to a file, add GST/discount calculation, and change how invoices are printed. Before you touch the code — what's wrong with this class as designed, and how would you restructure it? While you're at it, explain all five SOLID principles using this example or similar ones."

This is one of the most common LLD warm-up questions because it tests whether a candidate can *see* design problems in innocent-looking code, not just recite definitions from memory.

## 🏗️ Architect's Explanation (For a New Developer)

SOLID is not a design pattern — it's a set of five *ground rules* that make object-oriented code easier to maintain, extend, and understand, regardless of which patterns you eventually use. Think of it as the "code of conduct" for your classes: follow these rules and you naturally avoid duplicate code, reduce complexity, and make your software flexible enough to survive changing requirements. Each principle answers a different question about your class design:

- **S**ingle Responsibility — "does this class have more than one reason to change?"
- **O**pen/Closed — "can I add new behavior without editing tested, already-live code?"
- **L**iskov Substitution — "can I swap a child object in for its parent without breaking anything?"
- **I**nterface Segregation — "am I forcing a class to implement methods it doesn't need?"
- **D**ependency Inversion — "am I depending on a concrete class when I should depend on an interface?"

## 📊 Visualize It

```
SOLID — FIVE PRINCIPLES AT A GLANCE
────────────────────────────────────
S  Single Responsibility   → one class, one reason to change
O  Open/Closed             → open for extension, closed for modification
L  Liskov Substitution     → child must be substitutable for parent
I  Interface Segregation   → many small interfaces > one fat interface
D  Dependency Inversion    → depend on interfaces, not concrete classes
```

```
SRP VIOLATION (before)                    SRP FIXED (after)
───────────────────────                   ──────────────────
Invoice {                                 Invoice {              ← 1 reason to change:
  calculateTotal()   ─┐ 3 reasons          calculateTotal()        calculation logic
  printInvoice()      │ to change:       }
  saveToDB()         ─┘ calc, print,
}                       persistence      InvoicePrinter {         ← 1 reason: printing
                                            print(Invoice)
                                          }

                                          InvoiceDao {             ← 1 reason: persistence
                                            saveToDB(Invoice)
                                            saveToFile(Invoice)
                                          }
```

```
DIP VIOLATION (before)                    DIP FIXED (after)
───────────────────────                   ──────────────────
class Laptop {                            interface Keyboard {}
  WiredKeyboard keyboard;   ← concrete       WiredKeyboard implements Keyboard
  WiredMouse mouse;         ← concrete       BluetoothKeyboard implements Keyboard
}                                          interface Mouse {}
(can't swap to Bluetooth                    WiredMouse implements Mouse
 without editing Laptop)                    BluetoothMouse implements Mouse

                                           class Laptop {
                                             Keyboard keyboard;  ← interface
                                             Mouse mouse;        ← interface
                                             Laptop(Keyboard k, Mouse m) {...}
                                           }  (constructor injection —
                                              swap implementations freely)
```

## 🔧 Deep Dive: How It Actually Works

### 1. Single Responsibility Principle (SRP)
**"A class should have only one reason to change."**

The running example: an `Invoice` class holding marker attributes (name, color, manufacturer, price) plus `calculateTotal()` (price × quantity), `printInvoice()`, and a method to save the invoice to a database (and later, potentially, to a file). This violates SRP because there are at least **three independent reasons** this one class could need to change:
1. Calculation logic changes (e.g., adding GST or a discount before computing the final price).
2. Printing/formatting logic changes.
3. Persistence logic changes (saving to DB vs. saving to a file).

**Fix:** split into single-purpose classes — `Invoice` keeps only `calculateTotal()`; a separate `InvoicePrinter` class handles `printInvoice()`; a separate data-access class handles persistence (`saveToDB()`, and later `saveToFile()` without touching the other two classes). Result: changing the calculation logic (e.g., adding tax) never risks breaking printing or persistence, because they now live in different classes entirely. This is what makes the code easier to maintain and understand.

### 2. Open/Closed Principle (OCP)
**"Open for extension, but closed for modification."**

Continuing the invoice example: after the classes are split by SRP, you have a persistence class handling `saveToDB()`. It's already tested and live in production. Now a new requirement arrives: also save to a file. The *violation* is directly editing that already-tested, already-live class to bolt on a `saveToFile()` method — you're modifying code that's proven to work, risking regressions in the DB-saving path.

**Fix:** introduce an interface (e.g., an `Invoice`-persistence interface with implementations `InvoiceDBRepository` and `InvoiceFileRepository`). The DB implementation stays untouched; the file-saving requirement becomes a brand-new class implementing the same interface. If a third persistence mechanism shows up later (say, XML export), you again just add a new implementing class — you never have to reopen and modify already-tested code. That's "open for extension, closed for modification."

### 3. Liskov Substitution Principle (LSP)
**"Objects of a subclass should be replaceable with objects of the superclass without breaking the behavior of the program."**

Example: a `Vehicle` base class with `getNumberOfWheels()` and `hasEngine()` (returns `true` by default). Child classes `Motorcycle` (2 wheels) and `Car` (4 wheels, overrides wheel count) both work fine — client code iterating a `List<Vehicle>` and calling `.hasEngine()` works for both.

Now add a `Bicycle` child class that overrides `hasEngine()` to return `null` (because a `Bicycle` has no engine) instead of `false`. Client code doing `vehicle.hasEngine().toString()` now throws a **`NullPointerException`** the moment a `Bicycle` is in the list — because `Bicycle` *reduced* the capability set of its parent instead of only adding to it. If this client pattern exists in even a handful of places, each one now needs defensive `instanceof Bicycle` checks scattered everywhere — a clear sign LSP has been broken.

**Fix (covered in depth in the companion LSP video):** restructure the hierarchy so the base `Vehicle` class only contains truly generic behavior common to *all* vehicles (like `getNumberOfWheels()`), and pull out the engine-specific capability (`hasEngine()`) into a separate subclass — e.g., an `EngineVehicle` class extending `Vehicle`, from which `Car` and `Motorcycle` extend, while `Bicycle` extends `Vehicle` directly and is never exposed to `hasEngine()` at all. Now the compiler (not a runtime null-check) prevents you from ever calling `hasEngine()` on something that might be a `Bicycle`.

### 4. Interface Segregation Principle (ISP)
**"Clients should not be forced to implement unnecessary functions/methods they don't need."**

Example: a `RestaurantEmployee` interface with methods `washUtensils()`, `serveCustomers()`, `cookFood()`, `takeOrder()`. A `Waiter` class implements this interface — but a waiter's job is only to serve customers and take orders, **not** wash utensils or cook food. Yet because the interface bundles all four responsibilities together, `Waiter` is forced to provide (dummy/irrelevant) implementations for methods it will never meaningfully use.

**Fix:** break the fat interface into smaller, role-specific interfaces — e.g., a `WaiterInterface` (with `serveCustomers()`, `takeOrder()`) and a `ChefInterface` (with `cookFood()`, `decideMenu()`), possibly with a shared `HelperInterface` for anything common. Now `Waiter` implements only `WaiterInterface` and is never forced to stub out `cookFood()`.

### 5. Dependency Inversion Principle (DIP)
**"A class should depend on interfaces/abstractions, not on concrete implementations."**

Example: a `Laptop` (or similar) class that directly instantiates and holds `WiredKeyboard` and `WiredMouse` — concrete classes — as its keyboard/mouse fields. If you later want to support a `BluetoothKeyboard` or `BluetoothMouse`, you cannot, because the class is hard-wired to specific concrete types.

**Fix:** define `Keyboard` and `Mouse` interfaces; have `WiredKeyboard`, `BluetoothKeyboard` implement `Keyboard`, and `WiredMouse`, `BluetoothMouse` implement `Mouse`. The consuming class depends only on the interface types, and receives the actual implementation via **constructor injection** — i.e., the caller decides at construction time whether to pass in wired or Bluetooth implementations. Now swapping hardware types requires zero changes to the consuming class — you simply pass a different object into the constructor.

## 🔥 Real Production Incident & Fix

**The incident:** A billing team's `Invoice` class (structured almost exactly like the motivating example above — holding item data plus `calculateTotal()`, `printInvoice()`, and `saveToDB()` all in one class) needed a "quick" change: add GST calculation before computing the total. The engineer made the change directly inside `Invoice.calculateTotal()`. Two days later, a completely unrelated ticket asked for a new invoice PDF export format — another engineer, touching the *same class* to add PDF export logic, accidentally introduced a regression in the *tax calculation* because both changes lived in the same file and a merge conflict resolution silently reverted part of the GST fix.

**How the team noticed:** Finance flagged that a batch of invoices from that week had incorrect tax amounts — caught via a downstream reconciliation report, not a stack trace, which meant it had already gone out to customers before being caught. The post-mortem's root-cause line was blunt: "the Invoice class had three unrelated reasons to change (tax calculation, PDF export, persistence) living in one file, so two engineers editing it in the same sprint stepped on each other's changes without either being aware."

**Root cause:** A textbook Single Responsibility Principle violation — calculation, formatting/export, and persistence were all bundled into one class, so changes for entirely unrelated business reasons collided in the same source file and the same code review, making the blast radius of *any* change unnecessarily large.

**The fix:** The team split `Invoice` into `Invoice` (data + `calculateTotal()` only), `InvoiceExporter` (handles PDF/print formatting), and `InvoiceRepository` (handles persistence). Tax logic changes now only touch `Invoice`; export format changes now only touch `InvoiceExporter` — the two workstreams can no longer collide in the same file.

```
BEFORE: one class, three reasons to change     AFTER: SRP applied, isolated blast radius
────────────────────────────────────────       ─────────────────────────────────────────
Invoice {                                      Invoice { calculateTotal() }      ← tax team
  calculateTotal()  ← tax team edits here
  printInvoice()    ← export team edits here   InvoiceExporter { export() }      ← export team
  saveToDB()
}                    (both teams, same file,    InvoiceRepository { saveToDB() } ← untouched
                      same sprint → conflict)
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: How is SOLID different from a design pattern like Strategy or Factory?**
A: SOLID principles are evaluation criteria/ground rules for what makes an object-oriented design "good" — they don't prescribe a specific class structure. Design patterns are concrete, reusable structures that *happen to satisfy* SOLID principles for recurring problems. You use SOLID to judge whether your Strategy-pattern implementation, for example, is actually well-designed or just superficially matches the pattern's shape.

**Q2: Can you give an example where following SRP too aggressively becomes counterproductive?**
A: Yes — if you split a class into so many single-method classes that a simple change now requires touching five files instead of one, and there's no meaningful independent reason for each to change separately, you've over-engineered it. SRP is about isolating genuinely independent reasons for change (like tax logic vs. persistence vs. formatting), not mechanically minimizing method count per class.

**Q3: How do OCP and DIP work together in practice?**
A: OCP says you should be able to add new behavior without modifying existing, tested code; DIP says your classes should depend on interfaces rather than concrete implementations. In practice, DIP is often *what enables* OCP — because you depend on an interface, you can add a brand-new implementation (extension) without ever touching the class that depends on that interface (no modification).

**Q4: Explain LSP with a scenario where a subclass's overridden method changes its *return type semantics* rather than throwing an exception, and why that's still a violation.**
A: In the `Vehicle`/`Bicycle` example, `hasEngine()` returning `null` instead of `false` is exactly this — the method signature (`Boolean`) didn't change, but the semantic contract silently weakened (from "always returns a usable boolean" to "may return null"), and any caller written against the original contract (`.toString()` on the result) breaks with an NPE. It's a subtle LSP violation precisely because it compiles fine and only fails at runtime.

**Q5: When would you deliberately choose *not* to split a fat interface under ISP?**
A: If every implementing class genuinely needs every method in the interface (no class is ever forced to stub out irrelevant methods), splitting it further adds indirection without benefit. ISP is about avoiding forced, unnecessary implementations — not about minimizing interface size for its own sake.

**Q6: How would you detect a DIP violation just by reading a class's constructor or field declarations?**
A: Look for fields or constructor parameters typed as concrete classes (e.g., `private WiredKeyboard keyboard`) instead of interfaces/abstract types (e.g., `private Keyboard keyboard`). If you see `new SomeConcreteClass()` being constructed *inside* the dependent class rather than being passed in, that's both a DIP violation and typically a sign the class can't be unit-tested in isolation (you can't inject a mock/fake).

## 🔑 Key Takeaway

SOLID isn't five arbitrary rules to memorize for an interview — each principle exists to prevent one specific, recurring maintenance failure (tangled responsibilities, fragile modification of live code, broken substitutability, forced unnecessary implementations, and rigid concrete dependencies), so the fastest way to explain any of them in an interview is to show the *before* code, name the specific pain it causes, and then show the *after* structure that removes it.
