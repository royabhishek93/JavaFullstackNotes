# 🎭 All Behavioral Design Patterns - Interview Guide
## _Strategy · Observer · State · Template · Command · Visitor · Memento · Mediator · Chain of Responsibility · Iterator · Interpreter — 15 YOE Architect-Level Script_

**📘 Difficulty: Intermediate** — assumes you already know the core patterns; focuses on applying them to a real, moderately complex system.

> _(Companion to `transcript.md`, left untouched. Rapid revision guide covering all 11 behavioral patterns with one scenario + diagram each.)_

---

**Interviewer**: "Rapid fire — all behavioral patterns, one-liner + example each."

**You**: "Behavioral patterns all answer: *how do objects communicate/distribute responsibility efficiently* so the system stays flexible. Let's go through all 11."

---

## 1. State — "Object changes behavior when its internal state changes"
```
VendingMachine: IdleState ──insertCoin()──▶ WorkingState ──dispenseItem()──▶ IdleState
```
Each state implements the same behavior interface differently, and transitions itself to the next state.

## 2. Observer — "One-to-many notification on state change"
```
Stock(Observable) --notifyAll()--> [EmailObserver, SMSObserver, PushObserver]
```
_(Full detail in dedicated Observer guide.)_

## 3. Strategy — "Swap an entire algorithm at runtime"
```
ShoppingCart(has-a PayStrategy) --pay()--> CreditCardStrategy | UPIStrategy | CashStrategy
```
_(Full detail in dedicated Strategy guide.)_

## 4. Chain of Responsibility — "Pass a request along a chain until someone handles it"
```
client.log(msg) ──▶ InfoLogProcessor ──(can't handle? forward)──▶ ErrorLogProcessor ──▶ DebugLogProcessor
```
```java
abstract class LogProcessor {
    LogProcessor next;
    LogProcessor(LogProcessor next) { this.next = next; }
    void log(String msg) { if (next != null) next.log(msg); }
}
```
Sender doesn't know WHICH handler in the chain will process the request.

## 5. Template Method — "Fix the algorithm's skeleton, let subclasses fill in steps"
```
final sendMoney() { validate(); debit(); calculateFee(); credit(); }  // order LOCKED (final)
PayToFriend overrides validate/debit/calculateFee/credit with its own logic
PayToMerchant overrides them with different logic (e.g. charges 2% fee)
```

## 6. Interpreter — "Evaluate an expression based on a grammar/context"
```
Expression: a * b   (non-terminal "*" splits into two terminals: a, b)
context = {a: 2, b: 4}
interpret(context) -> TerminalExpression("a").interpret(ctx) * TerminalExpression("b").interpret(ctx) = 8
```
Used for parsing/evaluating rule engines, SQL-like DSLs, calculators.

## 7. Command — "Turn a request into an object, decoupling sender from receiver"
```
Sender: remote.pressButton() --> command.execute() --> Receiver.turnOnCondenser()... (N internal steps)
```
```java
interface Command { void execute(); }
class TurnAcOnCommand implements Command {
    AC receiver;
    public void execute() { receiver.turnOnCondenser(); receiver.setTemp(); /* etc */ }
}
```
Sender only knows `command.execute()` — zero knowledge of how many steps the receiver needs internally.

## 8. Iterator — "Traverse a collection without exposing its internal structure"
```
Library.createIterator() -> BookIterator (hasNext()/next())
```
Same traversal API works whether the collection is backed by an array, linked list, or hashmap internally.

## 9. Visitor — "Add new operations to existing classes without modifying them"
```
Room(element) accepts RoomPricingVisitor | RoomMaintenanceVisitor | (new)RoomCleaningVisitor
```
```java
interface RoomVisitor { void visit(SingleRoom r); void visit(DoubleRoom r); }
```
New operation = new Visitor class; **existing Room classes are never touched again** (Open/Closed Principle in its purest form).

## 10. Mediator — "Objects talk through a middleman, never directly"
```
Bidder1 ──placeBid()──▶ AuctionMediator ──notifies──▶ [Bidder2, Bidder3, ...]  (never Bidder1↔Bidder2 directly)
```

## 11. Memento — "Snapshot + restore an object's state, without exposing internals"
```
Originator.createMemento() -> Memento{height, width}  -> Caretaker.add(memento)
   ... later ...
Caretaker.undo() -> returns last Memento -> Originator.restoreMemento(memento)
```
Memento only stores what the Originator itself decides to expose — encapsulation preserved.

---

## The One-Page Decision Table

| Symptom | Pattern |
|---|---|
| "Behavior changes based on internal state/lifecycle" | State |
| "One event, many independent listeners" | Observer |
| "Swap an entire algorithm at runtime" | Strategy |
| "Unknown which handler will process a request" | Chain of Responsibility |
| "Fixed step order, but each step's logic varies per subclass" | Template Method |
| "Need to evaluate expressions against a grammar/context" | Interpreter |
| "Decouple sender from receiver; queue/undo/parameterize actions" | Command |
| "Traverse different collection internals uniformly" | Iterator |
| "Add new operations without touching existing classes" | Visitor |
| "Objects shouldn't reference each other directly" | Mediator |
| "Need undo / rollback to a previous state" | Memento |

---

## Senior Trap Questions

**Trap: "Command vs Chain of Responsibility — both seem to 'decouple sender from receiver'?"**
**✅ Senior answer:** "Command wraps ONE request as an object so it can be queued, logged, undone, or parameterized — there's exactly one receiver known at construction time. Chain of Responsibility passes a request through a **sequence of potential handlers**, where the sender doesn't know (or care) which one — possibly NONE — will actually handle it. Command = 'do this specific thing later/decoupled'. CoR = 'find whoever can handle this, in order'."

**Trap: "Visitor pattern seems to violate encapsulation — Visitor classes reach INTO Room's data?"**
**✅ Senior answer:** "It's a deliberate trade-off: Visitor sacrifices a bit of encapsulation (the Room must expose an `accept(Visitor)` method and enough data for visitors to compute) in exchange for **Open/Closed Principle at the operation level** — you can add unlimited new operations without ever re-touching or re-testing existing, live Room classes. Use it when new *operations* are added far more often than new *element types*."

---

## 🔥 Real-World Production Issue: The Chain of Responsibility With No Terminal Handler

*In plain English: a chain of handlers with no guaranteed end can loop forever and freeze every thread that touches it.*

**The war story:**

"Our log-processing chain was `InfoLogProcessor -> DebugLogProcessor -> ErrorLogProcessor -> null`. A new engineer added a `CriticalLogProcessor` to handle P1 alerts, but wired it in the MIDDLE of the chain instead of the end, and forgot that the chain's `next` pointer for the last node MUST be `null` (or a guaranteed catch-all) to terminate recursion."

```
BEFORE (correct, terminates):
Info -> Debug -> Error -> null                     ✅ chain always terminates

AFTER (bug introduced):
Info -> Debug -> Critical -> Error -> Critical      ❌ Critical accidentally pointed
                    ▲___________________|              back into an earlier processor
                    INFINITE LOOP for any log message that
                    none of Info/Debug/Error could handle
```

**Incident:** Any log message not matching Info/Debug/Error's handling condition caused an **infinite loop**, spinning that request-handling thread at 100% CPU forever. Because logging is called from almost every request, within 10 minutes most of the thread pool was stuck in this loop, and the service became unresponsive — classic thread-starvation outage.

```
   Thread pool state during incident:
   ┌────────────────────────────────────────┐
   │ Thread 1: STUCK in infinite CoR loop        │
   │ Thread 2: STUCK in infinite CoR loop        │
   │ Thread 3: STUCK in infinite CoR loop        │
   │  ...                                          │
   │ Thread 47: STUCK                              │
   │ Thread 48: waiting for a free thread (BLOCKED)│  ◄── new requests can't get served
   └────────────────────────────────────────┘
```

**Root cause:** Chain of Responsibility pattern's correctness DEPENDS on the chain being a proper, finite, acyclic linked structure that always terminates (either a handler processes the request, or the chain ends in `null`/a catch-all default handler). This is an invariant the pattern doesn't enforce at compile time — it's a runtime contract, easy to break during a rushed change.

**The fix:**
- Added a mandatory catch-all `DefaultLogProcessor` at the END of every chain that always handles anything unhandled (never forwards further, guaranteeing termination).
- Added a unit test that walks the chain at startup and asserts no cycles exist and the chain terminates within N hops.
- Added a max-hop-count safety counter in the base `LogProcessor.log()` as defense-in-depth, throwing/alerting if a request bounces more than N times.

**Lesson for a new developer:** "Chain of Responsibility (and any linked-list-like pattern) is only as safe as its invariants — 'the chain terminates'. When wiring up or modifying a chain, always verify termination explicitly, and add a catch-all/default handler and a cycle-detection safety net before it ever reaches production."

---

## 🎓 Final Tips
1. All 11 behavioral patterns are about *distributing responsibility* between communicating objects.
2. Match the **symptom** (not the vocabulary) to the pattern — interviewers care that you can recognize the shape of the problem.
3. Command decouples "what to do" from "who does it"; Chain of Responsibility decouples "who *can* do it" from the sender.
4. Any pattern built on a linked structure (Chain of Responsibility) needs an explicit termination guarantee in production — verify it, don't assume it.

Good luck! 🚀
