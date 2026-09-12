# Vending Machine — Complete LLD Interview Guide

**Interview Duration: 45 min | Difficulty: Medium | Must-Know: ⭐⭐⭐⭐ | 15-YOE Focus: State Pattern + Thread Safety**

---

## BIG PICTURE — Architecture

```
 ┌──────────────────────────────────────────────────────────────────┐
 │                   VENDING MACHINE SYSTEM                        │
 │                                                                  │
 │  USER ACTIONS          MACHINE STATE           INVENTORY         │
 │  ┌────────────┐        ┌─────────────────┐    ┌─────────────┐  │
 │  │ Insert Coin│──────► │  IDLE           │    │ Item A: 5   │  │
 │  │ Select Item│        │  HAS_MONEY      │    │ Item B: 0   │  │
 │  │ Cancel     │        │  ITEM_SELECTED  │    │ Item C: 3   │  │
 │  │ Collect    │        │  DISPENSING     │    └─────────────┘  │
 │  └────────────┘        │  OUT_OF_STOCK   │                      │
 │                        └────────┬────────┘                      │
 │                                 │                                │
 │                        ┌────────▼────────┐                      │
 │  PAYMENT               │  State Machine  │   DISPENSING         │
 │  ┌────────────┐        │  Context        │   ┌─────────────┐   │
 │  │ CoinSlot   │        │  current state  │   │ Motor/Coil  │   │
 │  │ balance    │        │  transitions    │   │ Drop item   │   │
 │  │ refund()   │        └─────────────────┘   │ Change disp │   │
 │  └────────────┘                               └─────────────┘   │
 └──────────────────────────────────────────────────────────────────┘

 STATE TRANSITION DIAGRAM:
 ┌────────────────────────────────────────────────────────────────┐
 │                                                                │
 │  [IDLE] ──insertCoin()──► [HAS_MONEY]                         │
 │    ▲                           │                              │
 │    │                     selectItem()                         │
 │    │                           │                              │
 │    │                    [ITEM_SELECTED]                       │
 │    │                           │                              │
 │    │                    dispense() / DISPENSING               │
 │    │                           │                              │
 │    └──────── returnChange() ───┘                              │
 │                                                                │
 │  Any state ──itemOutOfStock──► [OUT_OF_STOCK]                 │
 │  [OUT_OF_STOCK] ──restock()──► [IDLE]                        │
 └────────────────────────────────────────────────────────────────┘
```

---

## CONVERSATIONAL SCRIPT

### Phase 1 — Requirements (5 min)

**You:** "Before I start designing, let me clarify the requirements.

For functional requirements:
- Users can insert coins or notes — so we need to track balance
- They select an item by code — A1, B2, etc.
- Machine dispenses the item and returns change
- If item is out of stock, the machine says so
- Admin can restock items and collect cash

For non-functional:
- Thread-safe — multiple concurrent users? Actually a single physical machine, but in software simulation it may be multi-threaded
- Extensible — new payment types (card, UPI) in future
- The state must be consistent — you can't dispense without money

Does the machine need to handle multiple payment methods, or just coins for now?"

**Interviewer:** "Just coins for now, but design so we can add card later."

**You:** "Perfect — I'll use the Strategy pattern for payment and the State pattern for machine behavior. Let me draw the state machine first."

---

### Phase 2 — Core Design (10 min)

**You:** "The key insight here is that a vending machine's behavior depends entirely on its current state. The same action — say, pressing a button — means different things in different states. That's a textbook State pattern.

States:
```
IdleState      → waiting for money
HasMoneyState  → money inserted, waiting for selection
DispensingState→ dispensing item
OutOfStockState→ item unavailable
```

Entities:
```
VendingMachine   → Context, holds current state + inventory + balance
VendingState     → interface with: insertCoin, selectItem, dispense, cancel
Item             → code, name, price, quantity
Inventory        → Map<String, Item>
PaymentStrategy  → interface: addMoney(), refund(), getBalance()
```"

---

### Phase 3 — Full Implementation

```java
// ─── State Interface ───────────────────────────────────────────
public interface VendingState {
    void insertCoin(VendingMachine machine, int amount);
    void selectItem(VendingMachine machine, String itemCode);
    void dispense(VendingMachine machine);
    void cancel(VendingMachine machine);
}

// ─── Item ──────────────────────────────────────────────────────
public class Item {
    private final String code;
    private final String name;
    private final int price;
    private int quantity;

    public Item(String code, String name, int price, int quantity) {
        this.code = code; this.name = name;
        this.price = price; this.quantity = quantity;
    }
    public boolean isAvailable() { return quantity > 0; }
    public void decrementQuantity() { quantity--; }
    public int getPrice() { return price; }
    public int getQuantity() { return quantity; }
    public String getCode() { return code; }
    public String getName() { return name; }
}

// ─── Main Context ──────────────────────────────────────────────
public class VendingMachine {
    private VendingState currentState;
    private int currentBalance;
    private Item selectedItem;
    private final Map<String, Item> inventory;
    private final Object lock = new Object();

    // State singletons — reused across transitions
    private final VendingState idleState       = new IdleState();
    private final VendingState hasMoneyState   = new HasMoneyState();
    private final VendingState dispensingState = new DispensingState();
    private final VendingState outOfStockState = new OutOfStockState();

    public VendingMachine() {
        inventory = new HashMap<>();
        currentState = idleState;
        currentBalance = 0;
    }

    public void addItem(Item item) {
        synchronized (lock) { inventory.put(item.getCode(), item); }
    }

    public void insertCoin(int amount) {
        synchronized (lock) { currentState.insertCoin(this, amount); }
    }

    public void selectItem(String code) {
        synchronized (lock) { currentState.selectItem(this, code); }
    }

    public void dispense() {
        synchronized (lock) { currentState.dispense(this); }
    }

    public void cancel() {
        synchronized (lock) { currentState.cancel(this); }
    }

    // Package-visible for states
    void setState(VendingState state) { this.currentState = state; }
    void addBalance(int amount)       { this.currentBalance += amount; }
    void resetBalance()               { this.currentBalance = 0; }
    int  getBalance()                 { return currentBalance; }
    void setSelectedItem(Item item)   { this.selectedItem = item; }
    Item getSelectedItem()            { return selectedItem; }
    Item getItem(String code)         { return inventory.get(code); }

    VendingState getIdleState()        { return idleState; }
    VendingState getHasMoneyState()    { return hasMoneyState; }
    VendingState getDispensingState()  { return dispensingState; }
    VendingState getOutOfStockState()  { return outOfStockState; }
}

// ─── IdleState ─────────────────────────────────────────────────
public class IdleState implements VendingState {
    @Override
    public void insertCoin(VendingMachine machine, int amount) {
        if (amount <= 0) { System.out.println("Invalid amount"); return; }
        machine.addBalance(amount);
        System.out.println("Balance: ₹" + machine.getBalance());
        machine.setState(machine.getHasMoneyState());
    }

    @Override
    public void selectItem(VendingMachine machine, String code) {
        System.out.println("Please insert coins first");
    }

    @Override
    public void dispense(VendingMachine machine) {
        System.out.println("Please insert coins and select an item");
    }

    @Override
    public void cancel(VendingMachine machine) {
        System.out.println("Nothing to cancel");
    }
}

// ─── HasMoneyState ─────────────────────────────────────────────
public class HasMoneyState implements VendingState {
    @Override
    public void insertCoin(VendingMachine machine, int amount) {
        machine.addBalance(amount);
        System.out.println("Balance: ₹" + machine.getBalance());
    }

    @Override
    public void selectItem(VendingMachine machine, String code) {
        Item item = machine.getItem(code);
        if (item == null) {
            System.out.println("Item not found: " + code);
            return;
        }
        if (!item.isAvailable()) {
            System.out.println("Item out of stock");
            machine.setState(machine.getOutOfStockState());
            return;
        }
        if (machine.getBalance() < item.getPrice()) {
            System.out.println("Insufficient balance. Need ₹" + item.getPrice()
                + ", have ₹" + machine.getBalance());
            return;
        }
        machine.setSelectedItem(item);
        System.out.println("Selected: " + item.getName() + " (₹" + item.getPrice() + ")");
        machine.setState(machine.getDispensingState());
        machine.dispense();  // auto-dispense after selection
    }

    @Override
    public void dispense(VendingMachine machine) {
        System.out.println("Please select an item first");
    }

    @Override
    public void cancel(VendingMachine machine) {
        int refund = machine.getBalance();
        machine.resetBalance();
        machine.setState(machine.getIdleState());
        System.out.println("Cancelled. Returning ₹" + refund);
    }
}

// ─── DispensingState ───────────────────────────────────────────
public class DispensingState implements VendingState {
    @Override
    public void insertCoin(VendingMachine machine, int amount) {
        System.out.println("Please wait, dispensing in progress");
    }

    @Override
    public void selectItem(VendingMachine machine, String code) {
        System.out.println("Dispensing in progress");
    }

    @Override
    public void dispense(VendingMachine machine) {
        Item item = machine.getSelectedItem();
        int change = machine.getBalance() - item.getPrice();
        item.decrementQuantity();
        machine.resetBalance();
        System.out.println("Dispensing: " + item.getName());
        if (change > 0) System.out.println("Change returned: ₹" + change);
        machine.setSelectedItem(null);
        machine.setState(machine.getIdleState());
    }

    @Override
    public void cancel(VendingMachine machine) {
        System.out.println("Cannot cancel — dispensing in progress");
    }
}

// ─── OutOfStockState ───────────────────────────────────────────
public class OutOfStockState implements VendingState {
    @Override
    public void insertCoin(VendingMachine machine, int amount) {
        System.out.println("Machine out of stock. Returning ₹" + amount);
    }

    @Override
    public void selectItem(VendingMachine machine, String code) {
        System.out.println("Item out of stock");
    }

    @Override
    public void dispense(VendingMachine machine) {
        System.out.println("Nothing to dispense");
    }

    @Override
    public void cancel(VendingMachine machine) {
        int refund = machine.getBalance();
        machine.resetBalance();
        machine.setState(machine.getIdleState());
        if (refund > 0) System.out.println("Refunded ₹" + refund);
    }
}
```

---

## Component Choices — Why We Picked Each

```
COMPONENT          CHOICE           WHY
─────────────────────────────────────────────────────────────────────
Behavior model     State Pattern    Machine behavior depends on state.
                                    Same input, different output by state.
                                    vs if-else chains: unmanageable at scale.

Payment extension  Strategy Pattern Payment logic varies (coin/card/UPI).
                                    Open/Closed: add new payment without
                                    changing VendingMachine class.

Thread safety      synchronized     Single machine = low concurrency.
                                    synchronized(lock) on public methods.
                                    ReentrantLock overkill for this use case.

State instances    Singleton states State objects are stateless (all data
                                    lives in VendingMachine context).
                                    Reuse same instances → no GC pressure.

Inventory          HashMap          O(1) item lookup by code.
                                    ConcurrentHashMap if multi-machine mgmt.
```

---

## ASCII — State Flow With Balance

```
  User Actions        State Transitions           Output
  ────────────        ─────────────────           ──────
  insertCoin(10) ──► IDLE → HAS_MONEY            "Balance: ₹10"
  insertCoin(10) ──► HAS_MONEY (stay)            "Balance: ₹20"
  selectItem("A1")──► HAS_MONEY → DISPENSING    "Selected: Chips ₹15"
                                  → auto dispense()
                   DISPENSING → IDLE             "Dispensing: Chips"
                                                  "Change: ₹5"

  insertCoin(10) ──► IDLE → HAS_MONEY            "Balance: ₹10"
  selectItem("B2")──► B2 qty=0                   "Out of stock"
                   HAS_MONEY → OUT_OF_STOCK
  cancel()        ──► OUT_OF_STOCK → IDLE        "Refunded ₹10"
```

---

## Senior Trap Questions (15-YOE Level)

**Q1: "What if two threads call selectItem at the same time for the last item?"**
```
Without synchronization:
  Thread 1: item.isAvailable() → true (qty=1)
  Thread 2: item.isAvailable() → true (qty=1) ← same check, both pass!
  Thread 1: item.decrementQuantity() → qty=0
  Thread 2: item.decrementQuantity() → qty=-1 ← OVERSELL BUG!

Fix: synchronized block on the machine lock wraps entire selectItem+dispense
     sequence. The lock in VendingMachine.selectItem() + dispense() covers this.
     Both operations happen atomically — Thread 2 sees qty=0 after Thread 1 runs.
```

**Q2: "How do you handle partial payment — user inserts coins one by one?"**
```
HAS_MONEY state allows multiple insertCoin calls.
Each call accumulates balance: machine.addBalance(amount).
selectItem checks: if balance < item.price → reject but KEEP state in HAS_MONEY.
User can insert more coins to make up the difference.
Only cancel() returns to IDLE and refunds balance.
```

**Q3: "What if the dispense motor fails mid-operation?"**
```
This is a hardware-software contract question.
In production:
  DispensingState.dispense() calls hardware API.
  If hardware throws DispenseException:
    - DO NOT decrement inventory (item wasn't dispensed)
    - Refund full balance
    - Transition to MAINTENANCE state (new state)
    - Alert maintenance team

  MAINTENANCE state: rejects all user interactions, shows "Out of Service"
  Admin clears maintenance state after physical inspection.

This is why states are important — you can add MAINTENANCE without
changing other states.
```

**Q4: "Design the admin refill flow without interrupting users."**
```
Admin operations should:
  1. Try to acquire lock (will block until current transaction completes)
  2. Restock item: inventory.get(code).setQuantity(newQty)
  3. If machine was in OUT_OF_STOCK → transition back to IDLE
  4. Release lock

Admin should NOT interrupt a mid-transaction user.
The synchronized block ensures admin waits for current user's transaction to finish.
```

**Q5: "How would you extend this for card payment?"**
```java
// Strategy pattern — add without changing existing code
public interface PaymentStrategy {
    boolean processPayment(int amount);
    void refund(int amount);
    int getBalance();
}

public class CoinPayment implements PaymentStrategy { ... }
public class CardPayment implements PaymentStrategy {
    private CardReader cardReader;
    @Override
    public boolean processPayment(int amount) {
        return cardReader.charge(amount); // calls bank API
    }
}

// VendingMachine takes PaymentStrategy in constructor
// HasMoneyState uses machine.getPaymentStrategy().processPayment()
// Zero changes to state classes — Open/Closed Principle
```

---

## Failure Modes & Consistency

```
FAILURE SCENARIO          WHAT HAPPENS              FIX
─────────────────────────────────────────────────────────────────────
Motor fails after coin     Money taken, no item      Hardware exception →
inserted                                             refund + MAINTENANCE state

Power failure mid-dispense State lost in memory      Persistent state (DB/file)
                                                     On restart: check last state,
                                                     refund if interrupted TX

Negative change bug        item.price > balance but  Balance check in HasMoneyState
                           state advanced             before transition. Never
                                                     advance without balance check.

Concurrent oversell        Two threads decrement      synchronized block covers
                           from qty=1 → qty=-1       the full select+dispense
                                                     sequence atomically.

Admin restocks during TX   Item qty corrupted         Admin waits for lock.
                                                     No mid-TX interference.
```

---

## Interview Cheat Sheet

> "I'd use the State pattern as the core of this design. A vending machine has 4-5 states — Idle, HasMoney, Dispensing, OutOfStock — and the behavior of every user action depends on which state we're in. Each state implements the same interface (insertCoin, selectItem, dispense, cancel) but behaves differently. The VendingMachine is the Context that delegates to the current state. I'd use Strategy pattern for payment so we can add card/UPI later without touching the state classes. Thread safety: synchronized on a single lock object since all state transitions need to be atomic — especially the check-and-decrement on inventory to prevent oversell. The key trap question is concurrent last-item selection: both threads check isAvailable(), both see true, both decrement — the synchronized block prevents this by making the whole select+dispense sequence atomic."
