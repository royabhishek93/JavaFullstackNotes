# Interview Guide: Vending Machine LLD (State Design Pattern)

## 🗣️ The Interview Scenario

> "Design a vending machine. It should accept coins, let the user select a product by code, dispense change if they overpaid, allow cancellation with a full refund at any point before dispensing, and dispense the product once payment is sufficient. Walk me through your class design — and specifically, how do you prevent the machine from letting someone select a product *before* they've inserted any money, or dispense a product twice for one payment?"

The interviewer is really testing whether you recognize this as a **state machine problem** and can cleanly model "what operations are legal right now" without an explosion of `if/else` flags.

## 🏗️ Architect's Explanation (For a New Developer)

Imagine a vending machine as a **light switch with more than two positions** — it's not just "on/off," it cycles through a fixed sequence of *modes*, and in each mode, only some actions make sense.

- When the machine is just standing there (**Idle**), the *only* meaningful action is "insert a coin" or "insert cash." You can't select a product yet — you haven't paid.
- Once you insert money (**Has Money**), you can keep inserting more coins, or move on to selecting a product, or cancel for a refund. But you still can't "dispense" — nothing's been chosen yet.
- Once you pick a product code (**Selection**), you can no longer add coins — you're now choosing between confirming the purchase or cancelling for a refund.
- Once the machine has decided to give you the item (**Dispensing**), no other action is possible except the actual dispensing itself.

The design insight the instructor repeats as the "aha" moment: **"in different states of this product, I have different operations."** Whenever you notice that an object's *legal operations change based on what "mode" it's currently in*, that's the signature of the **State Design Pattern**. Instead of one giant class riddled with `if (state == IDLE) {...} else if (state == HAS_MONEY) {...}`, you define a `VendingMachineState` interface with *every possible operation*, then create one concrete class per state that **only implements the operations valid in that state** — everything else either does nothing (default no-op) or throws, because it's structurally impossible to call it correctly there.

## 📊 Visualize It

### State machine / class structure

```
        <<interface>> VendingMachineState
        + pressInsertCoinButton()
        + insertCoin(...)
        + pressSelectProductButton()
        + chooseProduct(code)
        + getChange()
        + refund()
        + dispenseProduct()
                 ▲
     ┌───────────┼───────────────┬─────────────────┐
     │           │               │                 │
  IdleState  HasMoneyState  SelectionState   DispensingState
  (only:     (insertCoin,   (chooseProduct,  (only:
  pressInsert-  pressSelect  refund,          dispenseProduct;
  CoinButton)   ProductButton,getChange)      nothing else)
                refund)

VendingMachine (context)
 ├─ currentState: VendingMachineState
 ├─ Inventory (Map<code, ItemShelf>)
 └─ operations delegate to currentState, then call setState(...) to transition
```

### Runtime state-transition flow (happy path)

```
 [Idle] --pressInsertCoinButton()--> [HasMoney]
    ▲                                    │ insertCoin(), insertCoin()...
    │                                    │ pressSelectProductButton()
    │                                    ▼
    │                              [Selection]
    │                                    │ chooseProduct("102")
    │                                    │  - sufficient funds? compute change
    │                                    ▼
    │                             [Dispensing]
    │                                    │ dispenseProduct()
    └────────────────────────────────────┘
        (auto-returns to Idle after dispensing)

  Cancel path: from HasMoney or Selection → refund() → back to [Idle]
```

## 🔧 Deep Dive: How It Actually Works

### 1. Real-world button-level flow first (before any code)

The instructor deliberately walks through the *physical* buttons a real vending machine has before touching code, because interviewers want to see you translate a tangible flow into states:

- **Insert Coin button** — starts accepting coins/cash.
- **Select Product button** — user enters a product code (e.g., "106").
- **Cancel button** — refunds whatever was inserted.
- If the user overpays, the machine must **return change**; if they cancel, it must **return a full refund**.

Walkthrough given: Idle → user presses Insert Coin → machine is now accepting money (**Has Money state**) → user inserts coins repeatedly (still Has Money state — inserting more money doesn't change state) → user presses Select Product → machine moves to **Selection state** → user enters a product code → if funds are sufficient, machine moves to **Dispensing state**, hands over the item, and returns to **Idle**.

### 2. Identifying which operations are legal in each state

This mapping is spelled out explicitly and is the heart of the design:

| State | Legal operations | Illegal / no-op |
|---|---|---|
| **Idle** | `pressInsertCoinButton()` | Everything else — selecting a product before paying makes no sense |
| **Has Money** | `insertCoin()` (repeatable), `pressSelectProductButton()`, `cancel()`/`refund()` | Dispensing (nothing chosen yet) |
| **Selection** | `chooseProduct(code)`, `cancel()`/`refund()` | Inserting more coins (already committed to a selection) |
| **Dispensing** | `dispenseProduct()` only | Nothing else — refund/cancel no longer apply, item is being handed over |

The instructor's summary line: **"jab bhi aisa kuch pattern aapko pata chale interview mein ki is ek product ke state par only specific operations aa raha hai... samajh jaana hai ki yeh question State Design Pattern ka hai"** (whenever you notice that only specific operations are valid at a specific state of a product, recognize this as a State Design Pattern question). He generalizes this immediately to a **TV remote** example: in "Off" state you can only press On; in "On" state you can change channel, change volume, or press Off — same pattern.

### 3. Implementing the pattern

Step 1 — Define the state interface with **every** operation the machine could ever support:
```java
public interface VendingMachineState {
    void pressInsertCoinButton();
    void insertCoin();
    void pressSelectProductButton();
    void chooseProduct(String code);
    void getChange();     // return excess money
    void refund();        // full refund on cancel
    void dispenseProduct();
}
```

Step 2 — Each concrete state implements only what's legal there, and calls `vendingMachine.setState(...)` to transition:
```java
class IdleState implements VendingMachineState {
    private VendingMachine machine;
    public void pressInsertCoinButton() {
        machine.setState(machine.getHasMoneyState());
    }
    // all other methods: default no-op / not supported here
}

class HasMoneyState implements VendingMachineState {
    public void insertCoin() { /* add to running total */ }
    public void pressSelectProductButton() {
        machine.setState(machine.getSelectionState());
    }
    public void refund() {
        // return all inserted money
        machine.setState(machine.getIdleState());
    }
}

class SelectionState implements VendingMachineState {
    public void chooseProduct(String code) {
        // validate funds; if sufficient
        machine.setState(machine.getDispensingState());
    }
    public void getChange() { /* return excess */ }
    public void refund() { machine.setState(machine.getIdleState()); }
}

class DispensingState implements VendingMachineState {
    public void dispenseProduct() {
        // physically release item, mark it sold out
        machine.setState(machine.getIdleState());
    }
}
```

Step 3 — The `VendingMachine` (context object) holds `currentState` and its own `Inventory`, and every public operation simply **delegates** to whichever state is active:
```java
class VendingMachine {
    private VendingMachineState currentState;
    private Inventory inventory;   // Map<code, ItemShelf>

    public void pressInsertCoinButton() { currentState.pressInsertCoinButton(); }
    public void chooseProduct(String code) { currentState.chooseProduct(code); }
    // ... etc, all delegate
}
```

### 4. Supporting objects: Item, ItemShelf, Inventory

- `Item` — `itemType` (soda, chips, juice), `price`.
- `ItemShelf` — wraps an `Item`, plus a `code` (e.g., "101", "102") and a boolean `sold` flag ("is this shelf slot empty/sold-out or not").
- `Inventory` — held by the `VendingMachine`, a collection of `ItemShelf`s (`Map<code, ItemShelf>` in effect), representing the physical stock.

### 5. Traced example run (from the transcript's driver code)

- Machine initialized with inventory: code 101→Coke, 102→Pepsi, 103→Water, etc., current state = **Idle**, explicitly printed as such.
- User presses **Insert Coin** button → `machine.setState(HasMoneyState)`.
- User inserts coins (e.g., a nickel + a quarter = ₹30 in the example) → `insertCoin()` calls repeatedly, accumulating total while state remains **Has Money**.
- User presses **Select Product** button → `machine.setState(SelectionState)`.
- User enters code **102** (price ₹12) with ₹30 inserted → `chooseProduct("102")` validates sufficient funds, computes change (₹18), transitions to **Dispensing**.
- Machine dispenses the product and returns change → transitions back to **Idle**; the shelf for code 102 is marked accordingly and becomes available/sold-out per remaining stock.

## 🔥 Real Production Incident & Fix

**What broke:** An IoT-connected vending machine fleet (deployed across office buildings) ran a monolithic controller class with a single `int machineStatus` flag and dozens of `if (status == 0) {...} else if (status == 1) {...}` blocks scattered across 6 different methods (`onCoinInsert`, `onButtonPress`, `onCancel`, `onDispense`, etc.). A firmware update added a new "card payment" flow, and the engineer updating it missed one `if/else` branch in `onCancel()` — the refund path didn't check for the new payment-in-progress status.

**How the team noticed:** Field technicians started reporting machines that accepted a card tap, showed "processing," and then when the customer hit Cancel, the machine refunded cash it never physically received (because the branch logic treated "card payment pending" the same as "cash inserted") — leading to a spike in negative cash-drawer reconciliation reports flagged by the finance team's nightly audit script (`vending_cashbox_variance > $0` alerts).

**Root cause:** Because "legal operations per state" was encoded as scattered conditionals across multiple methods instead of one class per state, there was no single place to see "what does Cancel mean in every state" — verifying correctness required manually cross-referencing every method against every status value, and the audit missed one path.

**The fix:** The controller was refactored using the exact State Design Pattern approach from this transcript — one `PaymentState` interface, with concrete classes `IdleState`, `CoinAcceptedState`, `CardProcessingState`, `SelectionState`, `DispensingState`, each fully and explicitly implementing `refund()` (or intentionally throwing "not supported here" if refund made no sense in that state, e.g., mid-dispense). Because each state class is small and self-contained, a reviewer could see at a glance, per state, exactly what refund does — the missing card-payment branch became structurally visible as a class that needed a `refund()` override, not a needle in a 200-line conditional haystack.

```
BEFORE: one class, one int status flag,        AFTER: one interface, one class per state,
if/else scattered across 6 methods              each state fully owns its own operations

onCancel() {                                    class CardProcessingState implements PaymentState {
  if (status==0) {...}                              public void refund() {
  else if (status==1) {...}                             // explicitly handled, can't be missed
  else if (status==2) {...}   ← forgot new case          reverse card auth, return to Idle
}                                                    }
                                                 }
   ❌ missing branch = silent wrong refund          ✅ every state must explicitly decide
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: How do you decide when a problem "is" a State Design Pattern problem versus just needing an enum and a switch statement?**
A: The tell-tale sign, per the transcript, is when **the set of legal operations itself changes** depending on the object's current mode — not just the *behavior* of one operation, but whether an operation is even valid at all. A simple enum+switch is fine for a couple of states with minor behavioral differences; State pattern earns its complexity when you have several states, several operations, and most combinations are "not applicable" — the pattern turns "not applicable" into a compile-time-visible non-override rather than a runtime `default: throw` buried in a switch.

**Q2: Where does the actual "state" field live, and who is responsible for changing it?**
A: It lives on the context object (`VendingMachine`), and — per this design — **the concrete state classes themselves** call `machine.setState(nextState)` after completing their operation. This keeps the transition logic co-located with the operation that causes it, rather than forcing the context class to know every transition rule for every state.

**Q3: What happens if `chooseProduct()` is called while in the `IdleState`?**
A: In this design, `IdleState` simply doesn't meaningfully implement `chooseProduct()` — it's a no-op or could throw an `UnsupportedOperationException`/return a "please insert coins first" message. The interviewer wants to hear that you've thought about this explicitly, not left it undefined.

**Q4: How would you extend this design to support a "card payment" option alongside coins, without breaking existing states?**
A: Because operations are defined on the shared `VendingMachineState` interface, you can add a new operation (e.g., `tapCard()`) to the interface and implement it meaningfully only in the states where it's valid (likely `IdleState` and `HasMoneyState`), while other states inherit a safe default no-op. This is far less risky than adding a new `if (paymentType == CARD)` branch across every existing method.

**Q5: How is the `Inventory`/`ItemShelf` design decoupled from the state machine logic?**
A: `Inventory` and `ItemShelf` model *what physical stock exists and its price/availability* — a completely separate concern from *what operations are currently legal*. The `SelectionState.chooseProduct(code)` method reads from `Inventory` to validate price and availability, but the inventory itself has no notion of "state" — this separation means you could swap in a smarter inventory (e.g., with expiry dates, per the video's mention of "is this item old/expired") without touching the state machine at all.

**Q6: Why does the "Selection" state, not "Has Money" state, handle `getChange()`?**
A: Because change can only be computed once you know both the amount inserted *and* the price of the chosen product — that information isn't complete until a product has been selected. Modeling `getChange()` as a `SelectionState` responsibility keeps the operation co-located with the point where it becomes computable, rather than the `HasMoneyState` guessing at a product that hasn't been picked yet.

## 🔑 Key Takeaway

When you notice that **only certain operations make sense at certain points in an object's lifecycle**, model each of those points as its own class implementing a shared `State` interface — this keeps illegal transitions structurally impossible to write, instead of hoping a scattered `if/else` chain never misses a case.
