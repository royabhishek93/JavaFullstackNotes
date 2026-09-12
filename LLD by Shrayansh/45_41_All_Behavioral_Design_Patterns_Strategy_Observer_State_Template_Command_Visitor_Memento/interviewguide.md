# Interview Guide: All Behavioral Design Patterns (Strategy, Observer, State, Chain of Responsibility, Template Method, Interpreter, Command, Iterator, Visitor, Mediator, Memento)

## 🗣️ The Interview Scenario

> "We've been discussing individual design patterns in previous rounds. Now, at a high level, walk me through the different *behavioral* design patterns you know, give me one concrete example use case for each, and — most importantly — tell me how you'd decide which one applies to a given problem in the next 60 seconds of an interview."

This is a **breadth-and-recognition** question: the interviewer isn't asking you to deep-dive one pattern, they're testing whether you have a fast, reliable mental map across *all* behavioral patterns and can pattern-match a scenario to the right tool almost immediately — a skill that matters enormously under interview time pressure.

## 🏗️ Architect's Explanation (For a New Developer)

Here's the one-sentence umbrella definition worth memorizing: **behavioral design patterns guide how different objects communicate with each other effectively** — they're fundamentally about **distributing responsibility for a task** across objects in a way that keeps the system flexible and easy to maintain. Whenever objects need a *necessity* to talk to each other because a task has been split up between them, a behavioral pattern is usually the right lens.

Below is each pattern explained the same way a mentor would sketch it on a whiteboard in 30 seconds, followed by the exact recurring example from the source material — memorize the *trigger phrase* for each; that's your fast-recognition key in an interview.

## 📊 Visualize It

**The full family, at a glance:**

```
BEHAVIORAL PATTERNS = "how objects communicate/distribute a task"

 State          →  object changes behavior as its internal state changes
 Observer       →  one subject notifies many dependent observers on state change
 Strategy       →  swap one interchangeable algorithm for a task at runtime
 Chain of Resp. →  pass a request along a chain until someone handles it
 Template Method→  fixed step order, per-subclass step logic
 Interpreter    →  evaluate an expression tree against a context
 Command        →  turn a request into an object; decouples sender from receiver
 Iterator       →  uniform traversal over different underlying collection structures
 Visitor        →  add new operations to elements without modifying element classes
 Mediator       →  objects communicate only via a central hub, never directly
 Memento        →  save/restore an object's state (undo/snapshot)
```

**Trigger-phrase decision table (fast recognition):**

```
"object behaves differently depending on its current status"     → State
"many things need to know when one thing's state changes"        → Observer
"pick one of several interchangeable algorithms at runtime"       → Strategy
"pass a request down a line of handlers until one accepts it"     → Chain of Responsibility
"same step order for everyone, different logic per step"          → Template Method
"evaluate an expression given some context/grammar"               → Interpreter
"decouple who asks for an action from who performs it"            → Command
"iterate over different collection types the same way"           → Iterator
"add operations to existing classes without touching them"        → Visitor
"objects must NOT talk directly to each other"                   → Mediator
"need undo / rollback / history of an object's state"            → Memento
```

## 🔧 Deep Dive: How It Actually Works

### 1. State Pattern
**Definition:** allows an object to alter its behavior when its internal state changes.
**Example (vending machine):** a `VendingMachine` has behaviors (`insertCoin()`, `dispenseItem()`) and states (`IdleState`, `WorkingState`). While `idle`, `insertCoin()` transitions the machine to `working` state (`product.setMachineState(workingState)`); while `working`, `dispenseItem()` might transition it to another state. The object's *behavior for the same method call* differs depending on which state object is currently active.

### 2. Observer Pattern
**Definition:** an `observable` maintains a list of dependent `observers` and notifies them of any state change.
**Example (stock notification):** an `Observable` interface exposes `addObserver()`, `removeObserver()`, `notifyAll()`; a concrete class maintains the observer list, and when an item goes back in stock (`setData()`), it calls `notify()`, which iterates the list and invokes `update()` on every registered observer.

### 3. Strategy Pattern
**Definition:** define multiple algorithms for a task and select any one of them dynamically depending on the situation.
**Example (payments):** a `PayStrategy` interface has implementations `CreditCardStrategy`, `UPIStrategy`, `CashStrategy`. A `ShoppingCart` receives the strategy via its constructor (not hardcoded) and calls `pay()` — the caller decides *which* algorithm to plug in at runtime.

### 4. Chain of Responsibility
**Definition:** allow multiple objects to handle a request without the sender knowing which object will ultimately process it.
**Example (logging):** a `LogProcessor` interface holds a reference to the *next* processor (set via constructor). `InfoLogProcessor` and `DebugLogProcessor` each check "can I handle this log level?" — if not, they call `super.logMessage()` to forward to whichever processor was set as `next`. The chain ends when `next` is `null`.

### 5. Template Method Pattern
**Definition:** enforce that all classes follow a fixed step sequence for a task, while letting each class supply its own logic within each step.
**Example (payments):** an abstract `PaymentFlow` has a `final sendMoney()` template method calling `validateRequest() → debitAmount() → calculateFees() → creditAmount()`, all `abstract`. `PayToFriendFlow` and `PayToMerchantFlow` extend it, each implementing the four steps differently (e.g., 0% vs. 2% fee) but **never able to reorder the steps** because `sendMoney()` is `final`.

### 6. Interpreter Pattern
**Definition:** defines a grammar/context for interpreting and evaluating an expression.
**Example (`a * b`):** an `Expression` interface (`interpret(context)`) is implemented by `NonTerminalExpression` (e.g., `MultiplyNonTerminalExpression`, holding `left`/`right` sub-expressions) and `TerminalExpression` (resolves a variable directly from a `Context` map, e.g., `a → 2`). Evaluating recursively resolves `left.interpret(context) * right.interpret(context)`.

### 7. Command Pattern
**Definition:** turns a request/command into an object, so it can be parameterized, queued, and — most importantly — **decouples the sender from the receiver**.
**Example (remote control for an AC):** instead of the sender directly calling multiple internal steps on an `AirConditioner` (turn on condenser, then compressor, then fan — several tightly-coupled steps), you create a `Command` interface with concrete `TurnACOnCommand`/`TurnACOffCommand` objects. The sender just calls `command.execute()`; the receiver-specific multi-step logic lives inside the command object, so sender and receiver never need direct knowledge of each other.

### 8. Iterator Pattern
**Definition:** provides a way to access elements of a collection sequentially **without exposing the underlying representation** of the collection.
**Example (Java Collections):** every collection type (array-backed list, linked list, hash-based set) stores data completely differently internally, but all expose the *same* traversal contract: an `Iterator` interface with `hasNext()` and `next()`. A `Collector`/collection class exposes `createIterator()`, returning a type-specific `Iterator` implementation (e.g., a list iterator) — client code iterates identically regardless of internal storage.

### 9. Visitor Pattern
**Definition:** allows adding new operations to existing classes without modifying them — encourages the Open/Closed Principle.
**Example (hotel room operations):** a `Room` element (`SingleRoom`, `DoubleRoom`, `DeluxeRoom`) exposes only `accept(RoomVisitor visitor)`. Each *operation* (pricing, maintenance) becomes its own `RoomVisitor` implementation (`RoomPricingVisitor`, `RoomMaintenanceVisitor`) with a `visit()` method per room type. New operations = new visitor classes; existing room classes are never touched again.

### 10. Mediator Pattern
**Definition:** encourages loose coupling by keeping objects from referring to each other explicitly — they communicate only through a mediator object.
**Example (auction):** `Colleague` (a `Bidder`) never talks to another `Bidder` directly — it calls `auctionMediator.placeBid()`. The `AuctionMediator`/`Auction` maintains the list of colleagues and, on receiving a bid, iterates the list and calls `receiveBidNotification()` on every *other* bidder — the bidders themselves hold zero references to each other.

### 11. Memento Pattern
**Definition:** provides the ability to revert an object to a previous state — undo/snapshot functionality — without exposing the object's internal implementation.
**Example (configuration undo):** an `Originator` (`Configuration`, with `height`/`width`) exposes `createMemento()`/`restoreMemento()`. A `Memento` (`ConfigurationMemento`) holds just the fields worth saving. A `Caretaker` maintains the history list (`addMemento()`, `undo()` — pops the last snapshot). The originator alone decides what's captured; the caretaker never inspects memento contents.

## 🔥 Real Production Incident & Fix

**What broke:** A logistics dispatch platform needed to: (1) route delivery-status log messages to the right handler by severity, (2) let drivers undo an incorrect delivery-status update, (3) notify multiple downstream systems (billing, customer notifications, analytics) whenever a delivery's status changed, and (4) support three different fee-calculation algorithms depending on delivery zone. The original implementation crammed **all four concerns into one `DeliveryStatusService` class**: a giant `if/else` for log severity, manual "previous value" fields for undo, direct method calls to billing/notification/analytics services baked into the status-update method, and a `switch` on delivery zone for fee calculation.

**How the team noticed:** Adding a fifth downstream consumer (a new fraud-detection service that needed to know about every status change) required directly editing `DeliveryStatusService.updateStatus()` — a business-critical, heavily-called method. During that change, an engineer's edit accidentally broke the "undo last status change" feature (the manual previous-value tracking was overwritten in the wrong order), which was reported by support tickets from drivers saying "undo brought back the wrong status," and confirmed via session replay logs showing the previous-value field held stale data.

**Root cause:** Four genuinely distinct behavioral concerns — notification fan-out, undo/history, algorithm selection, and severity-based routing — were tangled into a single class instead of being modeled as the four distinct patterns that actually fit them (Observer for fan-out, Memento for undo, Strategy for fee calculation, Chain of Responsibility for severity routing). Because they were tangled, an unrelated change (adding a new observer) touched and broke unrelated logic (undo).

**The fix:** The team decomposed `DeliveryStatusService` into the appropriate patterns: an `Observable` status object that downstream systems (billing, notifications, analytics, and the new fraud service) subscribe to independently (Observer); a `Caretaker`/`Memento` pair dedicated solely to undo history; a `FeeStrategy` interface for zone-based fee algorithms (Strategy); and a `LogProcessor` chain for severity-based routing (Chain of Responsibility). Adding the fraud-detection consumer became "call `addObserver(fraudService)`" — zero risk to the now-isolated undo logic.

```
BEFORE: one class tangles 4 unrelated behavioral concerns     AFTER: each concern isolated in its own
(editing one breaks another, unrelated one)                    pattern — independently extensible/testable

 DeliveryStatusService.updateStatus() {                         StatusObservable.notifyAll()  (Observer)
   if(severity)... routing logic                                Caretaker.undo()                (Memento)
   prevStatus = ...  // undo tracking, fragile                  FeeStrategy.calculate()          (Strategy)
   billingService.charge(); notifyUser(); logAnalytics();        LogChain.process()   (Chain of Resp.)
   switch(zone) { fee = ... }                                    (adding fraud service = one addObserver call)
 }
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: How do you quickly distinguish State from Strategy — both involve swapping behavior?**
A: In **State**, the object *itself* transitions between states as a side effect of its own behavior executing (e.g., inserting a coin moves the vending machine from idle to working) — the state change is internally driven and part of the object's lifecycle. In **Strategy**, an external caller explicitly *chooses* which algorithm to plug in, and there's no notion of the object automatically transitioning between algorithms as a result of using one.

**Q2: How do you distinguish Mediator from Observer — both seem to involve "someone notifying multiple others"?**
A: Their *intent* is different despite superficial similarity. Mediator's purpose is to prevent objects from referring to each other directly at all — communication is inherently bidirectional and peer-like (bidders both send and receive through the mediator). Observer's purpose is to propagate a *state change* from one subject to any number of dependents — it's fundamentally one-directional (subject → observers) and about notification of change, not about avoiding peer coupling.

**Q3: How do you distinguish Visitor from Strategy — both seem to "plug in behavior"?**
A: Strategy separates out **algorithms that are independent of the object** using them (the algorithm could apply uniformly regardless of which concrete object invokes it). Visitor separates out **operations that are specific to each element type** (pricing logic for a `SingleRoom` is fundamentally tied to that type, not an interchangeable algorithm). If you find yourself creating "one strategy per (element type × operation)" combination, that's actually a sign you want Visitor.

**Q4: What's the difference between Chain of Responsibility and just calling a sequence of methods that each check a condition?**
A: In Chain of Responsibility, each handler in the chain is **fully decoupled from the sender** — the sender doesn't know or care which handler ultimately processes the request, and each handler only knows the *next* handler in the chain (not the whole chain). A hardcoded sequence of `if` checks in the sender's own code means the sender must know about every possible handler, which defeats the decoupling goal.

**Q5: Iterator pattern seems almost invisible in day-to-day Java work — why does it matter for interviews?**
A: It's one of the best real-world proofs that a pattern can be so pervasive it becomes invisible — every Java `Collection` (ArrayList, LinkedList, HashSet) implements this exact pattern under the hood via `Iterator`'s `hasNext()`/`next()`, letting completely different internal storage structures be traversed with identical client code. Interviewers use it to check whether you can recognize patterns you already use daily, not just ones you'd consciously design from scratch.

**Q6: If a single interview problem seems to need two or three of these patterns at once, is that a red flag?**
A: Not necessarily — real systems often combine behavioral patterns naturally (e.g., Command + Memento for full undo/redo, or Observer + Mediator in event-driven architectures). The red flag is combining patterns *without being able to articulate why each one is there* — a strong candidate can say precisely which concern each pattern is solving, exactly as broken down pattern-by-pattern above.

## 🔑 Key Takeaway

Behavioral patterns are fundamentally about **how a task's responsibility gets distributed across communicating objects** — build a fast mental trigger-phrase map (state-change → State, notify-many → Observer, swap-algorithm → Strategy, fixed-order-different-steps → Template Method, decouple-sender-receiver → Command, no-direct-peer-talk → Mediator, undo/history → Memento, add-operations-without-touching-classes → Visitor) so you can pattern-match a scenario to the right one within seconds under interview pressure.
