# 🎰 Vending Machine - Low Level Design Interview Guide
## _15 YOE Architect-Level Conversational Script_

---

## 📋 **Table of Contents**
1. [Architecture Diagram](#1-architecture-diagram)
2. [API Design](#2-api-design)
3. [ER Diagram & Database Design](#3-er-diagram--database-design)
4. [Sequence Diagrams](#4-sequence-diagrams)
5. [Scenario-First Explanations](#5-scenario-first-explanations)
6. [Cross Questions](#6-cross-questions)
7. [Trade-offs](#7-trade-offs)
8. [Senior Trap Questions](#8-senior-trap-questions)
9. [Technology Choices](#9-technology-choices)

---

## **Design Pattern Used**: State Design Pattern

**Interviewer**: "Design a Vending Machine."

**You**: "Great question! Let me clarify the scope first. Should the machine:
1. Accept coins/cash?
2. Dispense products when user selects item code?
3. Return change if overpaid?
4. Support refund if user cancels?
5. Handle inventory management?"

**Interviewer**: "Yes, all of those. Focus on state transitions."

**You**: "Perfect! The key insight here is that a vending machine has **distinct states** with specific allowed operations in each state:

- **Idle State**: Can only accept 'insert coin' button press
- **Has Money State**: Can accept more coins, select product, or refund
- **Selection State**: Can choose product, get change, or refund
- **Dispense State**: Can only dispense product

This is a textbook **State Design Pattern** problem. Let me show you..."

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      VENDING MACHINE ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────────┘

                            ┌──────────────────┐
                            │  VENDING MACHINE │
                            │                  │
                            │ CurrentState:    │
                            │ - Idle           │
                            │ - HasMoney       │
                            │ - Selection      │
                            │ - Dispense       │
                            │                  │
                            │ Inventory        │
                            │ CoinBalance      │
                            └────────┬─────────┘
                                     │
                     ┌───────────────┼───────────────┐
                     │               │               │
                     ▼               ▼               ▼
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │  IDLE STATE  │ │ HAS MONEY    │ │  SELECTION   │
            │              │ │   STATE      │ │    STATE     │
            │ Operations:  │ │ Operations:  │ │ Operations:  │
            │ - insertCoin │ │ - insertCoin │ │ - chooseItem │
            │   Button()   │ │ - selectProd │ │ - getChange()│
            │              │ │ - refund()   │ │ - refund()   │
            └──────────────┘ └──────────────┘ └──────────────┘
                     │               │               │
                     │               │               ▼
                     │               │       ┌──────────────┐
                     │               │       │  DISPENSE    │
                     │               │       │    STATE     │
                     │               │       │ Operations:  │
                     │               │       │ - dispense() │
                     │               │       └──────────────┘
                     │               │               │
                     └───────────────┴───────────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │    INVENTORY     │
                            │                  │
                            │ ItemShelf[]      │
                            │   [101] → Coke   │
                            │   [102] → Pepsi  │
                            │   [103] → Water  │
                            │                  │
                            │ Each shelf has:  │
                            │ - code           │
                            │ - item           │
                            │ - soldOut flag   │
                            └──────────────────┘
```

### **Why This Design?**

**You**: "See, the vending machine **operates in distinct states**, and each state allows only specific operations:

1. **Idle State**:
   - Only operation: Press 'Insert Coin' button
   - All other operations → throw exception

2. **Has Money State**:
   - Can insert more coins
   - Can press 'Select Product' button
   - Can press 'Cancel/Refund' button
   - Cannot choose product yet (need to activate selection mode first)

3. **Selection State**:
   - Can choose product by entering code
   - Can get change (if overpaid)
   - Can refund (if changed mind)
   - Cannot insert more coins

4. **Dispense State**:
   - Only operation: Dispense product
   - No refund, no adding coins, no selecting other products

**This state-wise operation is EXACTLY why State Pattern exists**. Each state is a separate class implementing common interface. Clean separation of concerns!"

---

## 2. API Design

### **2.1 Machine Control APIs**

```http
POST /api/v1/machines/{machineId}/insertCoinButton
Response: 200 OK
{
  "machineId": "vm-1234",
  "currentState": "HAS_MONEY",
  "message": "Ready to accept coins"
}

---

POST /api/v1/machines/{machineId}/coins
Request:
{
  "coinType": "QUARTER",  // QUARTER=25¢, DIME=10¢, NICKEL=5¢
  "count": 4
}

Response: 200 OK
{
  "totalInserted": 100,  // cents
  "message": "Accepted 4 QUARTER coins"
}

// Invalid state error:
Response: 400 BAD_REQUEST
{
  "error": "INVALID_STATE_OPERATION",
  "message": "Cannot insert coins in IDLE state. Press 'Insert Coin' button first."
}

---

POST /api/v1/machines/{machineId}/selectProductButton
Response: 200 OK
{
  "currentState": "SELECTION",
  "message": "Enter product code (101-110)",
  "availableProducts": [
    {"code": 101, "name": "Coke", "price": 75, "available": true},
    {"code": 102, "name": "Pepsi", "price": 75, "available": false},
    {"code": 103, "name": "Water", "price": 50, "available": true}
  ]
}
```

### **2.2 Product Selection APIs**

```http
POST /api/v1/machines/{machineId}/selectProduct
Request:
{
  "productCode": 102
}

Response: 200 OK
{
  "product": "Pepsi",
  "price": 75,
  "moneyInserted": 100,
  "change": 25,
  "currentState": "DISPENSE",
  "message": "Dispensing Pepsi. Change: 25¢"
}

// Insufficient funds:
Response: 402 PAYMENT_REQUIRED
{
  "error": "INSUFFICIENT_FUNDS",
  "productPrice": 75,
  "moneyInserted": 50,
  "shortfall": 25,
  "refunded": 50
}

// Product sold out:
Response: 410 GONE
{
  "error": "PRODUCT_SOLD_OUT",
  "productCode": 102,
  "refunded": 100,
  "message": "Pepsi is sold out. Money refunded."
}

---

POST /api/v1/machines/{machineId}/refund
Response: 200 OK
{
  "refundedAmount": 100,
  "currentState": "IDLE",
  "message": "Refunded 100¢. Thank you!"
}
```

### **2.3 Admin/Inventory APIs**

```http
POST /api/v1/machines/{machineId}/inventory
Request:
{
  "productCode": 102,
  "item": {
    "name": "Pepsi",
    "type": "SODA",
    "price": 75
  },
  "quantity": 10
}

Response: 201 CREATED
{
  "productCode": 102,
  "itemName": "Pepsi",
  "quantity": 10,
  "soldOut": false
}

---

GET /api/v1/machines/{machineId}/inventory
Response: 200 OK
{
  "machineId": "vm-1234",
  "items": [
    {"code": 101, "name": "Coke", "quantity": 5, "price": 75, "soldOut": false},
    {"code": 102, "name": "Pepsi", "quantity": 0, "price": 75, "soldOut": true},
    {"code": 103, "name": "Water", "quantity": 8, "price": 50, "soldOut": false}
  ]
}
```

### **Why This API Design?**

**You**: "Notice:
1. **State-aware error responses**: API returns specific error if operation invalid for current state
2. **Stateful session**: Machine remembers inserted coins and current state per session
3. **Atomic operations**: Selecting product → validating funds → dispensing → refunding change happens atomically
4. **Inventory management separate**: Admin APIs for restocking independent of user operations"

---

## 3. ER Diagram & Database Design

```
┌───────────────────────────────────────────────────────────────────────────┐
│                            ER DIAGRAM                                     │
└───────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │   MACHINE    │
    │──────────────│
    │*machineId    │
    │ location     │
    │ currentState │
    │ lastStocked  │
    │ status       │
    └──────┬───────┘
           │
           │ 1:N
           ▼
    ┌──────────────┐                    ┌──────────────┐
    │ ITEM_SHELF   │                    │     ITEM     │
    │──────────────│                    │──────────────│
    │*shelfId      │───────────────────▶│*itemId       │
    │ machineId(FK)│                    │ name         │
    │ code         │                    │ type         │
    │ itemId   (FK)│                    │ price        │
    │ quantity     │                    └──────────────┘
    │ soldOut      │
    └──────────────┘

    ┌──────────────┐
    │  TRANSACTION │
    │──────────────│
    │*transactionId│
    │ machineId(FK)│
    │ itemId   (FK)│
    │ amount       │
    │ moneyInserted│
    │ change       │
    │ status       │
    │ createdAt    │
    └──────────────┘

    ┌──────────────┐
    │SESSION_STATE │
    │──────────────│
    │*sessionId    │
    │ machineId(FK)│
    │ currentState │
    │ coinsInserted│
    │ startedAt    │
    │ expiresAt    │
    └──────────────┘
```

### **Schema Details**

```sql
CREATE TABLE machines (
    machine_id VARCHAR(50) PRIMARY KEY,
    location VARCHAR(255),
    current_state VARCHAR(20) DEFAULT 'IDLE',
    last_stocked TIMESTAMP,
    status VARCHAR(20) DEFAULT 'OPERATIONAL',
    
    CHECK (current_state IN ('IDLE', 'HAS_MONEY', 'SELECTION', 'DISPENSE')),
    CHECK (status IN ('OPERATIONAL', 'MAINTENANCE', 'OUT_OF_SERVICE'))
);

CREATE TABLE item_shelf (
    shelf_id VARCHAR(50) PRIMARY KEY,
    machine_id VARCHAR(50) NOT NULL,
    code INT NOT NULL,  -- Display code like 101, 102
    item_id VARCHAR(50) NOT NULL,
    quantity INT DEFAULT 0,
    sold_out BOOLEAN DEFAULT FALSE,
    
    UNIQUE (machine_id, code),
    CHECK (quantity >= 0),
    CHECK ((quantity = 0 AND sold_out = TRUE) OR (quantity > 0 AND sold_out = FALSE)),
    INDEX idx_machine_code (machine_id, code)
);

CREATE TABLE transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    machine_id VARCHAR(50) NOT NULL,
    item_id VARCHAR(50) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    money_inserted DECIMAL(10,2) NOT NULL,
    change_returned DECIMAL(10,2) DEFAULT 0.00,
    status VARCHAR(20) DEFAULT 'COMPLETED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (status IN ('COMPLETED', 'REFUNDED', 'FAILED')),
    INDEX idx_machine_created (machine_id, created_at)
);

CREATE TABLE session_state (
    session_id VARCHAR(50) PRIMARY KEY,
    machine_id VARCHAR(50) NOT NULL,
    current_state VARCHAR(20) DEFAULT 'IDLE',
    coins_inserted INT DEFAULT 0,  -- In cents
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    
    INDEX idx_machine_id (machine_id)
);
```

### **Why This Schema?**

**You**: "Key decisions:

1. **`session_state` table**: Stores per-session state (coins inserted, current state). Session expires after 5 minutes of inactivity - auto-refund.

2. **`item_shelf` CHECK constraint**: Ensures `sold_out` flag matches `quantity`. Can't have quantity > 0 AND sold_out = true.

3. **`transactions` audit log**: Every completed purchase recorded for analytics and reconciliation.

4. **State in machine table**: `current_state` column for display/monitoring. Actual state transitions handled in-memory (state objects)."

---

## 4. Sequence Diagrams

### **4.1 Happy Path: Successful Purchase**

```
User    Machine   IdleState   HasMoneyState   SelectionState   DispenseState   Inventory
 │         │           │              │                │               │            │
 │─Press InsertCoin──▶│           │              │                │               │            │
 │         ├─setState─▶│              │                │               │            │
 │         │           ├─clickInsertCoinButton──▶│                │               │            │
 │         │           │              │   Machine state → HAS_MONEY   │            │
 │         │           │◀─────────────│                │               │            │
 │◀State: HAS_MONEY───│           │              │                │               │            │
 │         │           │              │                │               │            │
 │─Insert QUARTER─────▶│           │              │                │               │            │
 │         │           │              ├─insertCoin(QUARTER)────────▶│               │            │
 │         │           │              │  coinBalance += 25          │               │            │
 │◀Accepted 25¢───────│           │              │                │               │            │
 │         │           │              │                │               │            │
 │─Insert 3 more──────▶│           │              │   (repeat)      │               │            │
 │◀Total: 100¢────────│           │              │                │               │            │
 │         │           │              │                │               │            │
 │─Press SelectProduct▶│           │              │                │               │            │
 │         │           │              ├─selectProductButton()────────▶│               │            │
 │         │           │              │                │   Machine state → SELECTION │            │
 │◀State: SELECTION───│           │              │                │               │            │
 │         │           │              │                │               │            │
 │─Choose 102─────────▶│           │              │                │               │            │
 │         │           │              │                ├─chooseProduct(102)──────────▶│
 │         │           │              │                │               │   Check inventory────▶│
 │         │           │              │                │               │◀Item available────────│
 │         │           │              │                │               │   Price: 75¢          │
 │         │           │              │                │               │                       │
 │         │           │              │                │               │   Deduct quantity─────▶│
 │         │           │              │                │  Change = 100 - 75 = 25¢      │
 │         │           │              │                │  setState(DISPENSE)────▶│      │
 │◀Dispensing Pepsi───│           │              │                │               │            │
 │◀Change: 25¢────────│           │              │                │               │            │
 │         │           │              │                │               ├─dispense()────▶│
 │◀Product dispensed──│           │              │                │               │            │
 │         │           │              │                │               ├─setState(IDLE)│
```

### **4.2 Refund Scenario**

```
User    Machine   HasMoneyState   IdleState
 │         │            │              │
 │─Insert 100¢────▶│            │              │
 │         │            │  coinBalance = 100   │
 │◀Total: 100¢─────│            │              │
 │         │            │              │
 │─Press Cancel────▶│            │              │
 │         │            ├─refund()──────────────▶│
 │         │            │  Calculate refund = 100¢
 │         │            │  coinBalance = 0      │
 │         │            │  setState(IDLE)───────▶│
 │◀Refunded 100¢───│            │              │
```

---

## 5. Scenario-First Explanations

### **5.1 Why State Pattern?**

**Scenario**: "User tries to select product without inserting coins"

**You**: "Without State Pattern:
```java
class VendingMachine {
    private String currentState = "IDLE";
    
    void selectProduct(int code) {
        if (currentState.equals("IDLE")) {
            throw new Exception("Insert coins first!");
        } else if (currentState.equals("HAS_MONEY")) {
            throw new Exception("Press 'Select Product' button first!");
        } else if (currentState.equals("SELECTION")) {
            // Process selection ✓
            dispenseProduct(code);
        } else if (currentState.equals("DISPENSE")) {
            throw new Exception("Product already dispensing!");
        }
    }
    
    void insertCoin(Coin coin) {
        if (currentState.equals("IDLE")) {
            throw new Exception("Press 'Insert Coin' button first!");
        } else if (currentState.equals("HAS_MONEY")) {
            // Accept coin ✓
            coinBalance += coin.getValue();
        } else if (currentState.equals("SELECTION")) {
            throw new Exception("Cannot add coins during selection!");
        }
        // ... if-else hell for every method!
    }
}
// ❌ Messy! Every method checks ALL states!
```

With State Pattern:
```java
interface VendingMachineState {
    void clickInsertCoinButton(VendingMachine machine);
    void insertCoin(VendingMachine machine, Coin coin);
    void selectProductButton(VendingMachine machine);
    void chooseProduct(VendingMachine machine, int code);
    void refund(VendingMachine machine);
    void dispense(VendingMachine machine);
}

class IdleState implements VendingMachineState {
    void clickInsertCoinButton(VendingMachine machine) {
        machine.setState(new HasMoneyState());  // ✓ Allowed
    }
    
    void insertCoin(VendingMachine machine, Coin coin) {
        throw new IllegalStateException("Press 'Insert Coin' button first");
    }
    
    void selectProductButton(VendingMachine machine) {
        throw new IllegalStateException("Insert coins first");
    }
    // ... other methods throw exception
}

class HasMoneyState implements VendingMachineState {
    void insertCoin(VendingMachine machine, Coin coin) {
        machine.addCoin(coin);  // ✓ Allowed
    }
    
    void selectProductButton(VendingMachine machine) {
        machine.setState(new SelectionState());  // ✓ Allowed
    }
    
    void refund(VendingMachine machine) {
        machine.refundMoney();
        machine.setState(new IdleState());  // ✓ Allowed
    }
    
    void chooseProduct(VendingMachine machine, int code) {
        throw new IllegalStateException("Press 'Select Product' button first");
    }
}
// ✅ Clean! Each state handles only relevant operations
```

**Benefits**:
1. **Single Responsibility**: Each state class handles one state's logic
2. **Open/Closed**: Add new state (e.g., MaintenanceState) without modifying existing code
3. **No if-else hell**: State-specific behavior encapsulated"

### **5.2 Why Separate States for Money and Selection?**

**Scenario**: "Why not combine HAS_MONEY and SELECTION into one state?"

**You**: "User experience! Consider this flow:

**With separate states**:
```
1. User inserts ₹1
2. User inserts ₹2
3. User inserts ₹5  (Total: ₹8)
4. User presses 'Select Product' → Pad activates
5. User enters 102
6. Product dispensed
```

**Without separate states (combined)**:
```
1. User inserts ₹1 → Product pad immediately active
2. User accidentally presses 102 while reaching for more coins!
3. Product dispensed prematurely (user wanted to add more money!)
```

**The 'Select Product' button acts as a** ***confirmation*** **that user is done adding money**.

**Code**:
```java
class HasMoneyState implements VendingMachineState {
    void selectProductButton(VendingMachine machine) {
        // Explicit user intent: "I'm ready to select product"
        machine.setState(new SelectionState());
        machine.displayMessage("Enter product code (101-110)");
    }
    
    void insertCoin(VendingMachine machine, Coin coin) {
        // Still allows adding more money
        machine.addCoin(coin);
    }
}

class SelectionState implements VendingMachineState {
    void insertCoin(VendingMachine machine, Coin coin) {
        // ❌ Not allowed! Selection mode active
        throw new IllegalStateException("Cannot add coins during selection");
    }
    
    void chooseProduct(VendingMachine machine, int code) {
        // ✓ Process product selection
        Product product = machine.getInventory().getItem(code);
        // ...
    }
}
```

**Real vending machines**: Have physical button labels - 'INSERT COINS' vs 'MAKE SELECTION'. Two distinct modes!"

### **5.3 Why Inventory Separate from State?**

**Scenario**: "Should inventory management be part of vending machine states?"

**You**: "NO! **Separation of Concerns**:

**Vending Machine States**: User interaction flow (coins → selection → dispense)
**Inventory**: Product availability and stock management

**Bad design (tight coupling)**:
```java
class SelectionState {
    void chooseProduct(VendingMachine machine, int code) {
        // ❌ State class knows about inventory structure!
        List<ItemShelf> shelves = machine.getShelves();
        for (ItemShelf shelf : shelves) {
            if (shelf.getCode() == code) {
                if (shelf.isSoldOut()) {
                    refund(machine);
                }
                // ...
            }
        }
    }
}
```

**Good design (loose coupling)**:
```java
class Inventory {
    private List<ItemShelf> shelves;
    
    Item getItem(int code) throws SoldOutException {
        ItemShelf shelf = findShelfByCode(code);
        if (shelf.isSoldOut()) {
            throw new SoldOutException("Product " + code + " is sold out");
        }
        return shelf.getItem();
    }
    
    void updateQuantity(int code, int quantity) {
        ItemShelf shelf = findShelfByCode(code);
        shelf.setQuantity(quantity);
        shelf.setSoldOut(quantity == 0);
    }
}

class SelectionState {
    void chooseProduct(VendingMachine machine, int code) {
        try {
            // ✓ State delegates to inventory
            Item item = machine.getInventory().getItem(code);
            processPayment(machine, item);
            machine.setState(new DispenseState(item));
            
        } catch (SoldOutException e) {
            machine.displayMessage(e.getMessage());
            refund(machine);
        }
    }
}
```

**Benefits**:
1. **Inventory can be replaced**: Use database, cache, or in-memory - state classes don't care
2. **Testability**: Mock inventory for unit testing states
3. **Reusability**: Same inventory class can be used for multiple machines"

---

## 6. Cross Questions

**Interviewer**: "What if user inserts coins but doesn't select product for 5 minutes?"

**You**: "Session timeout with auto-refund:

```java
class SessionManager {
    private static final int TIMEOUT_SECONDS = 300;  // 5 minutes
    private Map<String, ScheduledFuture<?>> sessions = new ConcurrentHashMap<>();
    private ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);
    
    void startSession(VendingMachine machine) {
        String sessionId = UUID.randomUUID().toString();
        
        // Schedule auto-refund after 5 minutes
        ScheduledFuture<?> timeoutTask = scheduler.schedule(() -> {
            if (!machine.getCurrentState().equals(IdleState.class)) {
                machine.refundMoney();
                machine.setState(new IdleState());
                machine.displayMessage("Session expired. Money refunded.");
            }
        }, TIMEOUT_SECONDS, TimeUnit.SECONDS);
        
        sessions.put(sessionId, timeoutTask);
    }
    
    void endSession(String sessionId) {
        ScheduledFuture<?> task = sessions.remove(sessionId);
        if (task != null && !task.isDone()) {
            task.cancel(false);  // Cancel timeout
        }
    }
}

class VendingMachine {
    private SessionManager sessionManager;
    
    void clickInsertCoinButton() {
        setState(new HasMoneyState());
        sessionManager.startSession(this);  // ✓ Start timeout
    }
    
    void dispenseProduct(Product product) {
        // Successful purchase
        sessionManager.endSession(currentSessionId);  // ✓ Cancel timeout
        setState(new IdleState());
    }
}
```

**Behavior**:
```
00:00 - User inserts ₹10
00:30 - User walks away (forgot about machine)
05:00 - Auto-refund triggered
05:01 - ₹10 returned to coin return slot
       Machine resets to IDLE
```

**Production**: Real vending machines have 30-60 second timeouts. Shorter timeout = better throughput!"

---

**Interviewer**: "How do you handle exact change problem? User pays exact amount."

**You**: "Exact payment → Skip change return:

```java
class SelectionState {
    void chooseProduct(VendingMachine machine, int code) {
        Item item = machine.getInventory().getItem(code);
        int price = item.getPrice();
        int moneyInserted = machine.getCoinBalance();
        
        if (moneyInserted < price) {
            machine.displayMessage("Insufficient funds. Need ₹" + (price - moneyInserted));
            refund(machine);
            return;
        }
        
        int change = moneyInserted - price;
        
        if (change == 0) {
            // ✓ Exact payment - skip change dispensing
            machine.setState(new DispenseState(item, 0));
            machine.dispenseProduct(item);
            
        } else {
            // Need to give change
            if (machine.canReturnChange(change)) {
                machine.setState(new DispenseState(item, change));
                machine.dispenseProduct(item);
                machine.returnChange(change);
            } else {
                // ❌ Machine doesn't have enough change
                machine.displayMessage("Exact change only. Refunding...");
                refund(machine);
            }
        }
    }
}

class VendingMachine {
    private Map<Coin, Integer> changeInventory;  // Available coins for change
    
    boolean canReturnChange(int amount) {
        // Greedy algorithm: Try to make change with available coins
        Map<Coin, Integer> changeNeeded = calculateChange(amount);
        
        for (Map.Entry<Coin, Integer> entry : changeNeeded.entrySet()) {
            if (changeInventory.get(entry.getKey()) < entry.getValue()) {
                return false;  // Not enough coins of this denomination
            }
        }
        return true;
    }
    
    Map<Coin, Integer> calculateChange(int amount) {
        Map<Coin, Integer> change = new HashMap<>();
        
        // Greedy: Largest coin first
        for (Coin coin : Coin.values()) {
            int count = amount / coin.getValue();
            if (count > 0) {
                change.put(coin, count);
                amount -= count * coin.getValue();
            }
        }
        
        return change;
    }
}
```

**Edge case: Machine out of change**:
```
User: Buys ₹10 item with ₹20
Machine: Needs ₹10 change
Machine: Only has 2×₹2 coins (₹4 total)
Result: Refund ₹20, display "Exact change only"
```

**Real vending machines**: Display "EXACT CHANGE ONLY" when low on coins."

---

## 7. Trade-offs

### **7.1 State Pattern vs If-Else**

| Aspect | State Pattern | If-Else Chains |
|--------|---------------|----------------|
| **Readability** | High (each state is a class) | Low (nested conditions) |
| **Maintainability** | Easy to add states | Hard (modify all methods) |
| **Performance** | Slight overhead (polymorphism) | Faster (direct branching) |
| **Testability** | Easy (test each state independently) | Hard (complex mocking) |

**You**: "For vending machines, **State Pattern wins** because:
- Clear state transitions (FSM - Finite State Machine)
- Easily extensible (add MaintenanceState, ServiceState)
- Production systems need maintainability > micro-optimizations

**If-else acceptable for**: Simple 2-3 state systems (toggle switch, traffic light with fixed timing)."

### **7.2 In-Memory State vs Database State**

| Aspect | In-Memory | Database-Persisted |
|--------|-----------|---------------------|
| **Speed** | Instant (nanoseconds) | Slow (10-50ms per write) |
| **Persistence** | Lost on restart | Survives crashes |
| **Complexity** | Simple | Requires DB connection |
| **Recovery** | Manual reset | Auto-recovery |

**You**: "For vending machines, **in-memory state** is correct:

**Why**:
```
Typical vending machine session:
1. Insert coin → state change
2. Insert coin → state change
3. Insert coin → state change
4. Select product → state change
5. Choose item → state change
6. Dispense → state change

6 state changes in 30 seconds!
DB writes = 6 × 20ms = 120ms overhead (20% of transaction time!)
```

**What to persist**:
- ✓ Completed transactions (audit log)
- ✓ Inventory levels
- ✓ Total sales
- ❌ NOT current state (ephemeral, session-based)

**Crash recovery**:
```java
class VendingMachine {
    void onRestart() {
        // Reset to IDLE
        setState(new IdleState());
        
        // If coins were inserted, they're in physical mechanism
        // Machine will detect and refund on next use
        coinBalance = 0;
    }
}
```

**Real vending machines**: Embedded systems, no DB. State in RAM, only transactions logged to disk."

---

## 8. Senior Trap Questions

### **Trap #1: "Use Enum for states!"**

**Interviewer**: "Why not just use an Enum for states?"

**❌ Junior Answer**: "Sure, enum is simpler."

**✅ Senior Answer**: "Enum for state STORAGE is fine, but **not for behavior**:

**Problem with Enum-only**:
```java
enum State {
    IDLE, HAS_MONEY, SELECTION, DISPENSE
}

class VendingMachine {
    private State currentState = State.IDLE;
    
    void insertCoin(Coin coin) {
        switch (currentState) {
            case IDLE:
                throw new Exception("Press button first");
            case HAS_MONEY:
                coinBalance += coin.getValue();  // Logic here!
                break;
            case SELECTION:
                throw new Exception("Can't add coins");
            case DISPENSE:
                throw new Exception("Dispensing");
        }
    }
    
    void selectProduct(int code) {
        switch (currentState) {
            case IDLE:
                throw new Exception("Insert coins");
            case HAS_MONEY:
                throw new Exception("Press button");
            case SELECTION:
                // Complex logic here!
                processSelection(code);
                break;
            case DISPENSE:
                throw new Exception("Already dispensing");
        }
    }
    // ❌ Every method has switch statement! If-else hell in disguise!
}
```

**Correct: Enum + State Pattern**:
```java
enum StateType {
    IDLE, HAS_MONEY, SELECTION, DISPENSE
}

interface VendingMachineState {
    StateType getType();  // ✓ For logging/monitoring
    void insertCoin(VendingMachine machine, Coin coin);
    void selectProduct(VendingMachine machine, int code);
}

class IdleState implements VendingMachineState {
    public StateType getType() { return StateType.IDLE; }
    
    public void insertCoin(VendingMachine machine, Coin coin) {
        throw new IllegalStateException("Press 'Insert Coin' button first");
    }
}

class HasMoneyState implements VendingMachineState {
    public StateType getType() { return StateType.HAS_MONEY; }
    
    public void insertCoin(VendingMachine machine, Coin coin) {
        machine.addCoin(coin);  // ✓ Behavior in state class
    }
}
// ✅ Clean! Enum for identification, classes for behavior
```

**When Enum-only is acceptable**:
```java
// Simple state machine with NO complex logic per state
enum TrafficLight {
    RED, YELLOW, GREEN;
    
    TrafficLight next() {
        return values()[(ordinal() + 1) % values().length];
    }
}
// ✓ OK - state transitions are trivial
```

**Senior insight**: Use **Enum for state identity**, **classes for state behavior**. Don't confuse State Pattern with state storage!"

---

## 9. Technology Choices

### **9.1 Embedded System: Java vs C++ vs Go**

| Aspect | Java | C++ | Go |
|--------|------|-----|-----|
| **Startup Time** | Slow (JVM) | Fast | Fast |
| **Memory** | High (200MB+) | Low (10MB) | Medium (50MB) |
| **Ecosystem** | Rich | Limited | Growing |

**When Java**:
```java
// Networked vending machine with cloud connectivity
@RestController
class VendingMachineController {
    @GetMapping("/inventory")
    public List<Item> getInventory() {
        return inventoryService.getAllItems();
    }
    
    @PostMapping("/purchase")
    public Transaction purchase(@RequestBody PurchaseRequest request) {
        return vendingService.processPurchase(request);
    }
}
// ✅ Spring Boot ecosystem, easy REST APIs
```

**When C++**:
```cpp
// Embedded vending machine (Raspberry Pi, ARM)
class VendingMachine {
    void dispenseProduct(int code) {
        // Direct GPIO control
        gpio_set_pin(MOTOR_PIN_1, HIGH);
        delay_ms(2000);
        gpio_set_pin(MOTOR_PIN_1, LOW);
    }
};
// ✅ Low memory, hardware control, real-time
```

**When Go**:
```go
// Modern vending machine with high concurrency
func (vm *VendingMachine) HandleRequest(req Request) {
    go vm.processTransaction(req)  // Goroutine per transaction
}
// ✅ Lightweight concurrency, fast startup
```

**My Choice**: **C++ for embedded**, **Java for networked/cloud-connected** machines.

---

## 🎓 **Final Tips for 15 YOE Vending Machine Interview**

1. **State Pattern is Key**: Nail state transitions and allowed operations per state
2. **Separation of Concerns**: States ≠ Inventory ≠ Payment
3. **Session Management**: Timeout and auto-refund
4. **Inventory Management**: Sold-out detection, restocking
5. **Real Hardware Constraints**: Mention embedded systems, GPIO, motor control

**Senior insights**:
- Discuss **coin acceptance sensors** (detect fake coins)
- Mention **change-making algorithm** (greedy vs dynamic programming)
- Talk about **remote monitoring** (IoT, telemetry)
- Consider **payment methods** (cashless - NFC, QR codes)

**Good luck!** Vending Machine is the CLASSIC State Pattern problem. Show you can build production-grade embedded systems! 🚀
