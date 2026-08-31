# 🏧 ATM System - Low Level Design Interview Guide
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

## **Design Patterns Used**: State Design Pattern + Chain of Responsibility

**Interviewer**: "Design an ATM system."

**You**: "Great question! Let me clarify the scope first. I'm thinking of an ATM that handles card insertion, PIN authentication, balance check, cash withdrawal, and cash deposit. Should I also include features like PIN change and transaction history?"

**Interviewer**: "Yes, cover those. Focus on cash withdrawal and PIN authentication."

**You**: "Perfect. The key insight here is that an ATM has **distinct states** and **cash dispensing logic**. I'll use **State Pattern** for state management and **Chain of Responsibility** for cash withdrawal. Let me show you..."

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ATM ARCHITECTURE                                │
└─────────────────────────────────────────────────────────────────────────────┘

                            ┌──────────────┐
                            │    USER      │
                            │  (+ Card)    │
                            └──────┬───────┘
                                   │
                                   │ Inserts Card
                                   ▼
                         ┌──────────────────────┐
                         │      ATM MACHINE     │
                         │                      │
                         │  CurrentState: State │
                         │  Balance: Money      │
                         │  CashDispenser       │
                         └──────────┬───────────┘
                                   │
                 ┌─────────────────┼─────────────────┐
                 │                 │                 │
                 ▼                 ▼                 ▼
         ┌─────────────┐   ┌──────────────┐  ┌─────────────┐
         │ IDLE STATE  │   │  HAS CARD    │  │  SELECT     │
         │             │   │   STATE      │  │ OPERATION   │
         │ insertCard()│   │ authenticatePin│ │ withdraw()  │
         └─────────────┘   └──────────────┘  │ deposit()   │
                                              │ checkBalance│
                                              └─────────────┘

                         ┌──────────────────────┐
                         │  CASH WITHDRAWAL     │
                         │     PROCESSOR        │
                         │   (Chain Pattern)    │
                         └──────────┬───────────┘
                                   │
                 ┌─────────────────┼─────────────────┐
                 ▼                 ▼                 ▼
         ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
         │ 2000 Rupee   │  │  500 Rupee   │  │  100 Rupee   │
         │  Processor   │→│   Processor  │→│   Processor  │
         │ Notes: 5     │  │  Notes: 10   │  │  Notes: 20   │
         └──────────────┘  └──────────────┘  └──────────────┘
```

### **Why This Design?**

**You**: "See, an ATM has very distinct operational states:
- **Idle**: Waiting for card insertion
- **Has Card**: Card accepted, waiting for PIN
- **Select Operation**: PIN verified, user selects withdraw/deposit/balance
- **Cash Withdrawal**: Processing withdrawal request

Each state allows only specific operations. That's **State Pattern**. And for cash withdrawal, I need to dispense notes efficiently—that's **Chain of Responsibility** where each processor handles its denomination."

---

## 2. API Design

**Interviewer**: "What APIs would your ATM expose?"

**You**: "ATMs typically have a hardware interface, but let me design REST APIs for a software-simulated ATM or a mobile banking app that simulates ATM operations."

### **2.1 Card & Authentication APIs**

```http
POST /api/v1/atm/{atmId}/insertCard
Request:
{
  "cardNumber": "1234-5678-9012-3456",
  "cvv": "123"
}

Response: 200 OK
{
  "sessionId": "sess-uuid-1234",
  "cardAccepted": true,
  "expiresAt": "2026-08-31T10:05:00Z"  // 5-min session
}

---

POST /api/v1/atm/sessions/{sessionId}/authenticatePin
Request:
{
  "pin": "1234",
  "encryptionKey": "..."  // Encrypted PIN
}

Response: 200 OK
{
  "authenticated": true,
  "accountId": "acc-9876",
  "accountType": "SAVINGS",
  "availableBalance": 50000.00
}

// Wrong PIN (3 attempts allowed):
Response: 401 UNAUTHORIZED
{
  "error": "INVALID_PIN",
  "attemptsRemaining": 2,
  "message": "Incorrect PIN. 2 attempts remaining."
}
```

### **2.2 Transaction APIs**

```http
GET /api/v1/atm/sessions/{sessionId}/balance
Response: 200 OK
{
  "accountId": "acc-9876",
  "availableBalance": 50000.00,
  "ledgerBalance": 52000.00,  // Includes pending transactions
  "currency": "INR"
}

---

POST /api/v1/atm/sessions/{sessionId}/withdraw
Request:
{
  "amount": 2700,
  "accountType": "SAVINGS"
}

Response: 200 OK
{
  "transactionId": "txn-5678",
  "amount": 2700,
  "dispensedNotes": {
    "2000": 1,
    "500": 1,
    "100": 2
  },
  "newBalance": 47300.00,
  "receiptUrl": "/receipts/txn-5678.pdf"
}

// Insufficient funds:
Response: 400 BAD_REQUEST
{
  "error": "INSUFFICIENT_FUNDS",
  "availableBalance": 1500.00,
  "requestedAmount": 2700
}

// ATM out of cash:
Response: 503 SERVICE_UNAVAILABLE
{
  "error": "ATM_CASH_UNAVAILABLE",
  "message": "ATM does not have sufficient notes"
}

---

POST /api/v1/atm/sessions/{sessionId}/deposit
Request:
{
  "amount": 5000,
  "depositType": "CASH",  // or "CHEQUE"
  "currency": "INR"
}

Response: 202 ACCEPTED
{
  "transactionId": "txn-9999",
  "amount": 5000,
  "status": "PENDING_VERIFICATION",
  "estimatedCreditTime": "2026-09-01T00:00:00Z"
}

---

DELETE /api/v1/atm/sessions/{sessionId}
// Eject card & end session
Response: 204 NO_CONTENT
```

### **Why This API Design?**

**You**: "Notice:
1. **Session-based**: Card insertion creates a session with TTL (5 min). Prevents session hijacking.
2. **PIN encryption**: Never send PIN in plaintext. Use RSA/AES encryption.
3. **Optimistic dispensing**: Calculate notes before actually dispensing (avoid cash stuck in machine).
4. **Idempotency**: Transaction IDs ensure duplicate withdrawal requests don't double-debit."

---

## 3. ER Diagram & Database Design

```
┌───────────────────────────────────────────────────────────────────────────┐
│                            ER DIAGRAM                                     │
└───────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐                    ┌──────────────┐
    │     ATM     │                    │     CARD     │
    │─────────────│                    │──────────────│
    │*atmId       │                    │*cardNumber   │
    │ location    │                    │ cardHolderName│
    │ bankId      │                    │ expiryDate   │
    │ cashBalance │                    │ cvv          │
    │ status      │                    │ pinHash      │
    └──────┬──────┘                    │ accountId(FK)│
           │                            └──────┬───────┘
           │                                   │
           │                                   │
           │                                   ▼
           │                            ┌──────────────┐
           │                            │  BANK        │
           │                            │  ACCOUNT     │
           │                            │──────────────│
           │                            │*accountId    │
           │                            │ accountNumber│
           │                            │ accountType  │
           │                            │ balance      │
           │                            │ status       │
           │                            │ customerId   │
           │                            └──────┬───────┘
           │                                   │
           │                                   │
           │                            ┌──────┴───────┐
           │                            │   CUSTOMER   │
           │                            │──────────────│
           │                            │*customerId   │
           │                            │ name         │
           │                            │ phoneNumber  │
           │                            │ email        │
           │                            └──────────────┘
           │
           ▼
    ┌──────────────┐
    │ ATM_CASH     │
    │ _INVENTORY   │
    │──────────────│
    │*atmId   (FK) │
    │*denomination │
    │ noteCount    │
    │ lastRestocked│
    └──────────────┘

    ┌──────────────┐
    │ TRANSACTION  │
    │──────────────│
    │*transactionId│
    │ atmId    (FK)│
    │ accountId(FK)│
    │ type         │  // WITHDRAWAL, DEPOSIT, BALANCE_INQUIRY
    │ amount       │
    │ status       │
    │ createdAt    │
    │ completedAt  │
    └──────────────┘
```

### **Schema Details**

```sql
CREATE TABLE atm_cash_inventory (
    atm_id VARCHAR(50) NOT NULL,
    denomination INT NOT NULL,  -- 2000, 500, 100, etc.
    note_count INT NOT NULL DEFAULT 0,
    last_restocked TIMESTAMP,
    
    PRIMARY KEY (atm_id, denomination),
    CHECK (denomination IN (2000, 500, 100, 50, 20, 10)),
    CHECK (note_count >= 0)
);

CREATE TABLE transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    atm_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    card_number VARCHAR(20),  -- Masked: 1234-****-****-3456
    type VARCHAR(20) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',
    dispensed_notes JSON,  -- {"2000": 1, "500": 1}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    INDEX idx_account_id (account_id),
    INDEX idx_atm_created (atm_id, created_at),
    INDEX idx_status (status),
    
    FOREIGN KEY (atm_id) REFERENCES atms(atm_id),
    FOREIGN KEY (account_id) REFERENCES bank_accounts(account_id)
);

CREATE TABLE bank_accounts (
    account_id VARCHAR(50) PRIMARY KEY,
    account_number VARCHAR(20) UNIQUE NOT NULL,
    account_type VARCHAR(20) NOT NULL,
    balance DECIMAL(15,2) NOT NULL DEFAULT 0,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    customer_id VARCHAR(50) NOT NULL,
    
    CHECK (balance >= 0),
    CHECK (account_type IN ('SAVINGS', 'CURRENT', 'SALARY')),
    INDEX idx_customer_id (customer_id)
);
```

### **Why This Schema?**

**You**: "Key decisions:
1. **`atm_cash_inventory`**: Tracks notes per denomination per ATM. Critical for knowing if ATM can dispense requested amount.
2. **`dispensed_notes` JSON**: Stores exact breakdown of notes dispensed. Useful for reconciliation and auditing.
3. **Masked card numbers**: PCI-DSS compliance—never store full card numbers in logs/transactions.
4. **Transaction status tracking**: PENDING → IN_PROGRESS → COMPLETED/FAILED. Enables retry logic."

---

## 4. Sequence Diagrams

### **4.1 Happy Path: Cash Withdrawal**

```
User    ATM     ATMState    CardReader   BankAPI   CashDispenser   DB
 │        │         │            │           │            │         │
 │─Insert Card─▶│         │            │           │            │         │
 │        ├─setState(HasCard)─▶│            │           │            │         │
 │        │         │─readCard──▶│           │            │         │
 │        │         │◀cardData───│           │            │         │
 │◀Card OK──│         │            │           │            │         │
 │        │         │            │           │            │         │
 │─Enter PIN──▶│         │            │           │            │         │
 │        │─authenticatePin────────────────▶│            │         │
 │        │◀PIN_VALID──────────────────────│            │         │
 │        ├─setState(SelectOperation)───▶│            │            │         │
 │◀Options─────│         │            │           │            │         │
 │        │         │            │           │            │         │
 │─Withdraw 2700▶│         │            │           │            │         │
 │        │─checkBalance───────────────────▶│            │         │
 │        │◀balance:50000───────────────────│            │         │
 │        │─calculateNotes──────────────────────────▶│         │
 │        │         │            │           │  2000×1, 500×1, 100×2│
 │        │◀notesAvailable─────────────────────────│         │
 │        │─debitAccount───────────────────▶│            │         │
 │        │◀success─────────────────────────│            │         │
 │        │─dispenseNotes──────────────────────────▶│         │
 │        │─saveTransaction────────────────────────────────▶│
 │◀Cash───────│         │            │           │            │         │
 │◀Receipt────│         │            │           │            │         │
 │        ├─setState(Idle)──────▶│            │           │            │         │
```

### **4.2 Failed Withdrawal: Insufficient ATM Cash**

```
User    ATM     CashDispenser   BankAPI    DB
 │        │           │            │         │
 │─Withdraw 15000─▶│           │            │         │
 │        │─checkATMBalance───▶│            │         │
 │        │           SELECT denomination, note_count
 │        │           FROM atm_cash_inventory────────▶│
 │        │           │◀2000×3, 500×2────────────────│
 │        │           │ Total: 7000 (insufficient!)  │
 │        │◀ATM_CASH_UNAVAILABLE──│            │         │
 │        │─logFailure──────────────────────────────▶│
 │◀"ATM low on cash, try another ATM"│            │         │
```

**You**: "See, I validate ATM inventory BEFORE calling bank API. Saves unnecessary API calls and prevents 'money deducted but not dispensed' scenarios."

---

## 5. Scenario-First Explanations

### **5.1 Why State Pattern for ATM?**

**Scenario**: "User inserts card → enters PIN → selects withdraw → cash dispensed → card ejected"

**You**: "Each step is a distinct **state** with allowed operations:

- **Idle State**: Can only accept card insertion
- **Has Card State**: Can authenticate PIN or eject card
- **Select Operation**: Can withdraw/deposit/check balance
- **Cash Withdrawal**: Can only dispense cash or fail

Without State Pattern:
```java
class ATM {
    void insertCard() {
        if (currentState == IDLE) {
            // accept card
        } else {
            throw new Exception("Card already inserted!");
        }
    }
    
    void withdraw(int amount) {
        if (currentState == IDLE) {
            throw new Exception("Insert card first!");
        } else if (currentState == HAS_CARD) {
            throw new Exception("Authenticate PIN first!");
        } else if (currentState == SELECT_OPERATION) {
            // process withdrawal ✓
        }
    }
}
// ❌ Messy! Every method checks all states!
```

With State Pattern:
```java
interface ATMState {
    void insertCard();
    void authenticatePin(String pin);
    void withdraw(int amount);
}

class IdleState implements ATMState {
    void insertCard() {
        atm.setState(new HasCardState());  // ✓
    }
    void withdraw(int amount) {
        throw new IllegalStateException("Insert card first");
    }
}

class SelectOperationState implements ATMState {
    void withdraw(int amount) {
        // process withdrawal ✓
        atm.setState(new CashWithdrawalState());
    }
}
// ✅ Clean! Each state handles only relevant operations
```

**Benefits**: Easy to add new states (e.g., MaintenanceState), no if-else hell."

### **5.2 Why Chain of Responsibility for Cash Dispensing?**

**Scenario**: "User withdraws ₹2700. ATM has 2000, 500, 100 notes. How to dispense optimally?"

**You**: "This is classic **greedy algorithm** + **chain pattern**:

```
Amount: 2700
↓
2000 Processor: Can I give 2000 notes?
  → YES! Give 1 note. Remaining: 700
  → Pass 700 to next processor
↓
500 Processor: Can I give 500 notes?
  → YES! Give 1 note. Remaining: 200
  → Pass 200 to next processor
↓
100 Processor: Can I give 100 notes?
  → YES! Give 2 notes. Remaining: 0
  → DONE!

Result: {2000: 1, 500: 1, 100: 2}
```

Implementation:
```java
class TwoThousandProcessor extends CashProcessor {
    void withdraw(int amount) {
        int notes = Math.min(amount / 2000, noteCount);
        amount -= notes * 2000;
        noteCount -= notes;
        
        if (amount > 0 && nextProcessor != null) {
            nextProcessor.withdraw(amount);  // Chain!
        }
    }
}

// Chain setup:
twoK.setNext(fiveHundred);
fiveHundred.setNext(hundred);
```

**Why not just calculate directly?**
- Easy to add new denominations (50, 20, 10 rupee notes)
- Each processor independent—easy to test
- Follows SRP: Each processor handles one denomination"

### **5.3 Why PIN Hashing + Salt?**

**Scenario**: "Database breached. Attacker gets `cards` table. Can they steal PINs?"

**You**: "Absolutely NOT if we hash properly:

```sql
-- ❌ BAD: Plain text PIN
cards (card_number, pin)
'1234-5678-9012-3456', '1234'
-- Attacker instantly knows PIN!

-- ❌ ALSO BAD: Simple hash
cards (card_number, pin_hash)
'1234-5678-9012-3456', 'SHA256(1234)' 
-- Attacker uses rainbow tables for common PINs!

-- ✅ GOOD: Hash + Salt
cards (card_number, pin_hash, salt)
'1234-5678-9012-3456', 'bcrypt(1234 + random_salt)', 'xY9k...'
```

**How bcrypt works**:
1. Generate random salt per card: `salt = random()`
2. Hash PIN with salt: `hash = bcrypt(PIN + salt, rounds=12)`
3. Store both salt and hash
4. Verification: `bcrypt(inputPIN + stored_salt) == stored_hash`

**Why bcrypt over SHA256**:
- **Slow by design**: Takes ~100ms to hash (prevents brute force)
- **Adaptive**: Can increase rounds as hardware improves
- **Built-in salt**: No manual salt management

**Real-world**: Banks use HSM (Hardware Security Module) for PIN storage, but bcrypt is acceptable for software ATMs."

---

## 6. Cross Questions

**Interviewer**: "What if user enters wrong PIN 3 times?"

**You**: "Great question! This is critical for security. Here's my approach:

```java
class CardAuthentication {
    private static final int MAX_PIN_ATTEMPTS = 3;
    private Map<String, Integer> cardAttempts = new ConcurrentHashMap<>();
    
    boolean authenticatePin(Card card, String pin) {
        String cardNumber = card.getCardNumber();
        int attempts = cardAttempts.getOrDefault(cardNumber, 0);
        
        if (attempts >= MAX_PIN_ATTEMPTS) {
            blockCard(cardNumber);
            throw new CardBlockedException("Card blocked due to multiple failed attempts");
        }
        
        if (verifyPin(card, pin)) {
            cardAttempts.remove(cardNumber);  // Reset on success
            return true;
        } else {
            cardAttempts.put(cardNumber, attempts + 1);
            
            if (attempts + 1 >= MAX_PIN_ATTEMPTS) {
                blockCard(cardNumber);
                notifyCustomer(card.getCustomerId(), "CARD_BLOCKED");
            }
            return false;
        }
    }
    
    void blockCard(String cardNumber) {
        cardRepo.updateStatus(cardNumber, CardStatus.BLOCKED);
        // Also update in bank's core banking system
        bankAPI.blockCard(cardNumber, "EXCEEDED_PIN_ATTEMPTS");
    }
}
```

**Additional safeguards**:
1. **Per-session limit**: Reset attempt counter after 15 minutes
2. **Physical card retention**: Some ATMs actually **capture the card** after 3 failed attempts
3. **SMS/Email alert**: Notify customer immediately
4. **Unblock mechanism**: Customer must visit branch or call customer care

**Production example**: HDFC Bank blocks card + sends SMS instantly."

---

**Interviewer**: "How do you handle concurrent withdrawals from same account?"

**You**: "This is the classic race condition problem. Two ATMs, same card cloned, simultaneous withdrawals:

**Problem**:
```
ATM 1                        ATM 2                 Account
Check balance: 10,000        Check balance: 10,000
Withdraw: 8,000              Withdraw: 8,000
Debit: -8,000 → 2,000        Debit: -8,000 → -6,000  ❌ OVERDRAFT!
```

**Solution 1: Database-Level Locking**
```java
@Transactional(isolation = Isolation.SERIALIZABLE)
public void withdraw(String accountId, BigDecimal amount) {
    // SELECT FOR UPDATE locks the row
    BankAccount account = accountRepo.findByIdWithLock(accountId);
    
    if (account.getBalance().compareTo(amount) < 0) {
        throw new InsufficientFundsException();
    }
    
    account.setBalance(account.getBalance().subtract(amount));
    accountRepo.save(account);
}

// SQL generated:
// SELECT * FROM bank_accounts WHERE account_id = ? FOR UPDATE;
// UPDATE bank_accounts SET balance = balance - ? WHERE account_id = ?;
```

**Solution 2: Optimistic Locking with Version**
```java
@Entity
class BankAccount {
    @Id private String accountId;
    private BigDecimal balance;
    @Version private Long version;  // Auto-incremented by JPA
}

// Transaction 1: Updates version 1 → 2 (SUCCESS)
// Transaction 2: Tries to update version 1 (FAILS - StaleObjectException)
```

**Solution 3: Distributed Lock (Redis)**
```java
public void withdraw(String accountId, BigDecimal amount) {
    String lockKey = "account:lock:" + accountId;
    String lockValue = UUID.randomUUID().toString();
    
    // Try to acquire lock (TTL 5 seconds)
    boolean locked = redis.set(lockKey, lockValue, "NX", "EX", 5);
    
    if (!locked) {
        throw new ConcurrentTransactionException("Another transaction in progress");
    }
    
    try {
        // Process withdrawal
        debitAccount(accountId, amount);
    } finally {
        // Release lock (only if we own it)
        redis.eval("if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) end", 
                   lockKey, lockValue);
    }
}
```

**My recommendation**: **Optimistic locking for most cases**, **distributed lock for critical accounts** (high-frequency traders, business accounts).

**Real-world**: Visa/Mastercard use distributed consensus (Paxos/Raft) for card transactions across global network."

---

**Interviewer**: "ATM dispenses cash but database update fails. How to handle?"

**You**: "This is a **distributed transaction** problem. Two resources: Physical cash dispenser + Database.

**Failure modes**:
1. **Cash dispensed, DB update fails**: Customer gets money, but balance not updated (bank loses money!)
2. **DB updated, cash dispenser jams**: Customer charged but no money (customer loses money!)

**Solution: Two-Phase Commit (2PC)**
```
Phase 1: PREPARE
1. Lock account in DB (BEGIN TRANSACTION)
2. Reserve cash in dispenser (mark notes as 'allocated')
3. Both respond: READY

Phase 2: COMMIT
4. If both READY → COMMIT
   - Update DB balance
   - Dispense physical cash
5. If any FAILED → ROLLBACK
   - Unlock account
   - Un-reserve cash
```

**In practice, this is hard**. Better approach:

**Idempotent Retry with Compensation**:
```java
@Transactional
public WithdrawalResult withdraw(String accountId, int amount) {
    // Step 1: Create transaction record (INITIATED)
    Transaction txn = createTransaction(accountId, amount, TransactionStatus.INITIATED);
    
    try {
        // Step 2: Debit account
        debitAccount(accountId, amount);
        txn.setStatus(TransactionStatus.ACCOUNT_DEBITED);
        saveTxn(txn);
        
        // Step 3: Dispense cash (can fail here!)
        DispenserResult result = cashDispenser.dispense(amount);
        
        if (result.isSuccess()) {
            txn.setStatus(TransactionStatus.COMPLETED);
            txn.setDispensedNotes(result.getNotes());
        } else {
            // Cash dispenser failed → COMPENSATE
            creditAccount(accountId, amount);  // Reverse debit
            txn.setStatus(TransactionStatus.FAILED);
            txn.setFailureReason("DISPENSER_JAM");
        }
        
        saveTxn(txn);
        return WithdrawalResult.from(txn);
        
    } catch (Exception e) {
        // Any failure → rollback
        txn.setStatus(TransactionStatus.FAILED);
        saveTxn(txn);
        throw e;
    }
}
```

**Monitoring**:
- Background job checks for ACCOUNT_DEBITED transactions > 5 min old
- Auto-refund or manual reconciliation

**Real ATMs**: Have cash sensors + multiple retries. If dispenser fails 3 times, transaction is reversed and ATM goes into maintenance mode."

---

## 7. Trade-offs

### **7.1 State Pattern vs If-Else**

| Aspect | State Pattern | If-Else Chains |
|--------|---------------|----------------|
| **Readability** | High (each state is a class) | Low (nested if-else) |
| **Maintainability** | Easy to add states | Hard (modify all methods) |
| **Testability** | Easy (test each state) | Hard (complex mocking) |
| **Performance** | Slight overhead (polymorphism) | Faster (direct branching) |

**You**: "For ATMs, **State Pattern wins** because:
- ATMs have 5-10 well-defined states
- States rarely change (stable domain)
- Readability matters for compliance/audits

But for simple 2-3 state machines (like toggle switch), if-else is fine."

### **7.2 Chain of Responsibility vs Greedy Algorithm**

| Aspect | Chain Pattern | Direct Greedy |
|--------|---------------|---------------|
| **Flexibility** | Easy to add/remove denominations | Hard-coded |
| **Extensibility** | OCP compliant | Violates OCP |
| **Performance** | O(n) processors | O(n) iterations (same) |

**You**: "Chain pattern is **engineering overhead for correctness**. Yes, direct greedy is faster to code, but:
- What if RBI introduces ₹200 notes? Chain: Just add new processor. Greedy: Rewrite algorithm.
- What if some ATMs don't have ₹2000 notes? Chain: Skip that processor. Greedy: Complex if-else.

**Production example**: Most banks use configurable dispensers—each ATM can have different denominations."

### **7.3 Pessimistic vs Optimistic Locking**

| Scenario | Pessimistic (FOR UPDATE) | Optimistic (Version) |
|----------|--------------------------|----------------------|
| **High contention** (same account, many ATMs) | Better (avoids retries) | Worse (many conflicts) |
| **Low contention** (different accounts) | Worse (unnecessary locks) | Better (no locking overhead) |
| **Deadlock risk** | Higher | None |

**You**: "For ATMs, I'd use **hybrid approach**:
- **Optimistic** for regular accounts (most transactions succeed first try)
- **Pessimistic** for VIP/business accounts (high transaction volume)

**Code**:
```java
if (account.getType() == AccountType.BUSINESS) {
    return withdrawWithPessimisticLock(account, amount);
} else {
    return withdrawWithOptimisticLock(account, amount);
}
```

**Real-world**: ICICI Bank uses tiered locking based on account balance."

---

## 8. Senior Trap Questions

### **Trap #1: "Just use a single ATM_STATE table!"**

**Interviewer**: "Why not store ATM state in a database table instead of in-memory?"

**❌ Junior Answer**: "Sure, we can persist state to DB."

**✅ Senior Answer**: "That's a common misconception. Let me explain why **in-memory state** is better for ATMs:

**Problem with DB-persisted state**:
```java
// Every state transition = DB write
class ATM {
    void setState(ATMState newState) {
        atmRepo.update(this.atmId, newState);  // ❌ DB call!
    }
}

// Typical ATM session:
INSERT_CARD → DB write
AUTHENTICATE_PIN → DB write
SELECT_OPERATION → DB write
CASH_WITHDRAWAL → DB write
RETURN_CARD → DB write

// 5 DB writes for single withdrawal! 
// At 10ms latency = 50ms overhead
```

**Why in-memory state wins**:
1. **Performance**: State transitions happen in nanoseconds, not milliseconds
2. **Simplicity**: No DB connection management for state
3. **Crash recovery**: ATM state doesn't need to survive crashes—just reset to IDLE on restart

**When to persist**:
- **Transaction state** (INITIATED → IN_PROGRESS → COMPLETED): YES, persist!
- **ATM operational state** (Idle → HasCard → SelectOperation): NO, keep in-memory

**Code**:
```java
class ATM {
    private ATMState currentState;  // In-memory (transient)
    
    void withdraw(int amount) {
        // Persist transaction, not ATM state
        Transaction txn = new Transaction(this.atmId, amount);
        txn.setStatus(TransactionStatus.INITIATED);
        txnRepo.save(txn);  // ✓ Persist THIS
        
        // State transition (in-memory)
        currentState.processWithdrawal(amount);  // ✓ Fast!
    }
}
```

**Real ATMs**: Maintain state in embedded software (C/C++). Only persist transaction logs to disk/DB."

---

### **Trap #2: "Store PIN in encrypted form!"**

**Interviewer**: "Should we encrypt PINs in the database?"

**❌ Junior Answer**: "Yes, use AES-256 encryption with a secret key."

**✅ Senior Answer**: "Actually, **encryption is WRONG** for PINs. Let me explain why:

**Problem with encryption**:
```
Encryption: Reversible
PIN '1234' → AES_ENCRYPT('1234', secret_key) → 'a9f8e7d6...'
                       ↓
            AES_DECRYPT('a9f8e7d6...', secret_key) → '1234'
            
If secret_key is compromised → ALL PINS exposed!
```

**Why hashing is correct**:
```
Hashing: One-way (irreversible)
PIN '1234' → bcrypt('1234', salt) → '$2a$12$Xg9...'
                    ↓
            Can NEVER recover '1234' from hash
            
Verification: bcrypt(input_PIN, stored_salt) == stored_hash
```

**Real-world attack**:
- 2013: Adobe breach—encrypted passwords with same key → all users' passwords recovered
- Correct approach: Banks use HSM (Hardware Security Module) for PIN storage

**Why HSM**:
- PIN never leaves hardware
- Physical tamper-detection
- FIPS 140-2 Level 3 certified

**For software ATMs**:
```java
// ❌ WRONG
card.setPin(AES.encrypt(pin, SECRET_KEY));

// ✅ CORRECT
String salt = BCrypt.gensalt(12);  // Cost factor 12 (slow!)
String hash = BCrypt.hashpw(pin, salt);
card.setPinHash(hash);

// Verification
boolean valid = BCrypt.checkpw(inputPin, card.getPinHash());
```

**Senior insight**: Encryption is for **data in transit** (TLS) or **data at rest** (disk encryption). Passwords/PINs should **always be hashed**."

---

### **Trap #3: "Use microservices for ATM!"**

**Interviewer**: "Should we build ATM as microservices?"

**❌ Junior Answer**: "Yes, microservices are scalable and modern."

**✅ Senior Answer**: "For ATMs, microservices are **over-engineering**. Here's why:

**ATM characteristics**:
1. **Embedded system**: Runs on a single physical machine (Raspberry Pi / x86 SBC)
2. **No scaling needs**: 1 ATM = 1 software instance (not millions of users)
3. **Network unreliability**: ATMs often have poor connectivity (rural areas, basements)

**Microservices overhead**:
```
Monolith ATM:
- Single process
- In-process method calls (nanoseconds)
- Simple deployment: Copy binary to ATM

Microservices ATM:
- Card Service (separate process)
- PIN Service (separate process)
- Cash Dispenser Service (separate process)
- Network calls between services (milliseconds + network failure risk)
- Complex orchestration
- Requires load balancer on single machine! (overkill)
```

**What happens on network failure**:
```
Monolith: ATM goes offline → Clear error to user
Microservices: Card service up, PIN service down → Confusing partial failure
```

**When microservices MAKE SENSE**:
- **Bank backend**: YES! Millions of accounts, need independent scaling
- **Mobile banking app**: YES! API gateway → multiple microservices
- **Single ATM software**: NO! Classic monolith use case

**Correct architecture**:
```
ATM (Monolith)
├── CardReader module
├── PINValidator module
├── CashDispenser module
└── TransactionManager module

                    ↓ HTTPS/REST
            
        Bank Backend (Microservices)
        ├── Account Service
        ├── Transaction Service
        ├── Fraud Detection Service
        └── Notification Service
```

**Real-world**: Diebold Nixdorf ATMs run monolithic C++ software. Only backend is microservices."

---

### **Trap #4: "Just check balance before withdrawal!"**

**Interviewer**: "To prevent overdraft, check balance before withdrawing, right?"

**❌ Junior Answer**: "Yes, check if balance >= amount, then debit."

**✅ Senior Answer**: "That's a classic **TOCTOU** (Time-Of-Check-Time-Of-Use) bug!

**The problem**:
```java
// ❌ WRONG (race condition)
public void withdraw(String accountId, int amount) {
    BankAccount account = accountRepo.findById(accountId);
    
    // Check (Time-of-Check)
    if (account.getBalance() >= amount) {
        // ⏱️ GAP! Another transaction can execute here!
        
        // Use (Time-of-Use)
        account.setBalance(account.getBalance() - amount);
        accountRepo.save(account);
    }
}

// Concurrent execution:
Thread 1: Check balance (10,000) → Pass
Thread 2: Check balance (10,000) → Pass
Thread 1: Debit 8,000 → Balance = 2,000
Thread 2: Debit 8,000 → Balance = -6,000  ❌ OVERDRAFT!
```

**Correct approach: Atomic check-and-debit**:
```sql
-- ✅ CORRECT (atomic SQL)
UPDATE bank_accounts 
SET balance = balance - ?  
WHERE account_id = ? AND balance >= ?;

-- Returns affected rows: 1 (success) or 0 (insufficient funds)
```

```java
// ✅ CORRECT (single atomic operation)
public void withdraw(String accountId, BigDecimal amount) {
    int rowsAffected = jdbcTemplate.update(
        "UPDATE bank_accounts SET balance = balance - ? WHERE account_id = ? AND balance >= ?",
        amount, accountId, amount
    );
    
    if (rowsAffected == 0) {
        throw new InsufficientFundsException();
    }
}
```

**Why this works**:
- Database ensures **atomicity**: Check and update happen in single operation
- No race condition possible
- Works even without explicit locks

**Alternative with JPA**:
```java
@Modifying
@Query("UPDATE BankAccount a SET a.balance = a.balance - :amount " +
       "WHERE a.accountId = :accountId AND a.balance >= :amount")
int debitAccount(@Param("accountId") String accountId, 
                 @Param("amount") BigDecimal amount);
```

**Senior insight**: Always use **compare-and-swap** operations for financial transactions. Read-then-write is a code smell."

---

## 9. Technology Choices

### **9.1 Database: PostgreSQL vs MySQL**

| Aspect | PostgreSQL | MySQL |
|--------|-----------|-------|
| **ACID Compliance** | Stronger (SERIALIZABLE isolation) | Good (REPEATABLE_READ default) |
| **JSON Support** | JSONB (indexed, queryable) | JSON (limited indexing) |
| **Concurrency** | MVCC (better for reads) | InnoDB (row-level locks) |
| **Transaction Safety** | Better (no silent failures) | Can lose data on crash |

**When PostgreSQL**:
```sql
-- ATM with JSON metadata (dispenser config, cash inventory)
CREATE TABLE atms (
    atm_id VARCHAR(50) PRIMARY KEY,
    location JSONB,  -- {"lat": 12.9716, "lng": 77.5946, "address": "..."}
    cash_inventory JSONB,  -- {"2000": 100, "500": 200}
    last_reconciled TIMESTAMP
);

-- Query ATMs with low cash
SELECT atm_id, location->>'address' 
FROM atms 
WHERE (cash_inventory->>'2000')::int < 10;

-- ✅ PostgreSQL allows indexed JSON queries
```

**When MySQL**:
```sql
-- Simple CRUD for bank accounts
SELECT account_id, balance FROM bank_accounts WHERE account_number = ?;

-- ✅ MySQL is 10-15% faster for simple queries
-- ✅ More DBAs know MySQL (easier hiring)
```

**My Choice: PostgreSQL**
- ATMs need **strong ACID** (money involved!)
- JSONB for flexible cash inventory (denominations vary by country)
- Better concurrency for multi-ATM deployments

**Real-world**: ICICI Bank uses Oracle (enterprise), smaller banks use PostgreSQL.

---

### **9.2 Caching: Redis vs Memcached**

| Aspect | Redis | Memcached |
|--------|-------|-----------|
| **Data Structures** | Strings, Sets, Hashes, Sorted Sets | Key-Value only |
| **Persistence** | RDB + AOF snapshots | None |
| **Atomic Operations** | INCR, DECR, SETNX | Limited |
| **Use Case** | Session store, rate limiting | Pure caching |

**When Redis**:
```java
// Track PIN attempts (atomic, TTL-based)
public boolean recordPINAttempt(String cardNumber) {
    String key = "pin_attempts:" + cardNumber;
    Long attempts = redis.incr(key);  // Atomic increment
    
    if (attempts == 1) {
        redis.expire(key, 900);  // 15 min TTL
    }
    
    if (attempts >= 3) {
        blockCard(cardNumber);
        return false;
    }
    return true;
}

// ATM session management
redis.setex("atm_session:" + sessionId, 300, sessionData);  // 5 min TTL

// ✅ Redis handles TTL, atomic ops, persistence
```

**When Memcached**:
```java
// Simple cache for account details
String cacheKey = "account:" + accountId;
Account account = memcached.get(cacheKey);

if (account == null) {
    account = accountRepo.findById(accountId);
    memcached.set(cacheKey, account, 3600);  // 1 hour
}

// ✅ Memcached is faster for pure GET/SET
```

**My Choice: Redis**
- Need **atomic operations** (PIN attempts, session management)
- Need **TTL per key** (session expiry)
- **Persistence** helps recover ATM state after crash

**Production**: Most banks use Redis for session management + rate limiting.

---

### **9.3 Message Queue: Kafka vs RabbitMQ**

| Aspect | Kafka | RabbitMQ |
|--------|-------|----------|
| **Throughput** | 1M+ msg/sec (batched) | 10K-50K msg/sec |
| **Latency** | 10-50ms | <5ms |
| **Use Case** | Event streaming, audit logs | Task queues, notifications |

**When Kafka**:
```java
// ATM transaction event stream (for analytics, fraud detection)
TransactionEvent event = new TransactionEvent(
    atmId, accountId, amount, timestamp, location
);
kafkaProducer.send("atm-transactions", event);

// Consumers:
// 1. Fraud detection service (real-time ML)
// 2. Data warehouse (batch analytics)
// 3. Compliance audit log (long-term storage)

// ✅ Kafka allows multiple consumers, replay-ability
```

**When RabbitMQ**:
```java
// SMS notification queue (one-time task)
NotificationTask task = new NotificationTask(
    phone, "Your withdrawal of Rs.2700 is successful. Balance: Rs.47300"
);
rabbitMQ.publish("sms-queue", task);

// Worker consumes once, sends SMS, acknowledges
// ✅ RabbitMQ ensures exactly-once delivery
```

**My Choice: Both!**
- **Kafka**: Transaction events (immutable audit log)
- **RabbitMQ**: SMS/email notifications (task queue)

**Real-world**: HDFC uses Kafka for transaction logs + RabbitMQ for customer notifications.

---

### **9.4 Language: Java vs Go**

| Aspect | Java | Go |
|--------|------|-----|
| **Ecosystem** | Mature (Spring Boot, Hibernate) | Growing |
| **Concurrency** | Threads (heavyweight) | Goroutines (lightweight) |
| **Startup Time** | Slow (JVM warmup) | Fast (<100ms) |
| **Memory** | Higher (GC overhead) | Lower (efficient) |

**When Java**:
```java
// Rich ecosystem for ATM backend
@RestController
@RequestMapping("/api/v1/atm")
class ATMController {
    @Autowired private TransactionService txnService;
    @Autowired private BankAPIClient bankAPI;
    
    @PostMapping("/withdraw")
    @Transactional
    public ResponseEntity<WithdrawalResponse> withdraw(...) {
        // Spring Boot handles: DI, transactions, error handling
    }
}

// ✅ Mature libraries: JPA, Spring Security, logging
// ✅ Large talent pool (easy hiring)
```

**When Go**:
```go
// ATM embedded software (runs on Raspberry Pi)
func main() {
    cardReader := hardware.NewCardReader("/dev/ttyUSB0")
    cashDispenser := hardware.NewDispenser("/dev/ttyUSB1")
    
    atm := NewATM(cardReader, cashDispenser)
    atm.Run()  // Low memory, fast startup
}

// ✅ Single binary (no JVM dependency)
// ✅ Low memory footprint (<50MB vs Java's 200MB+)
// ✅ Great for embedded systems
```

**My Choice: Hybrid**
- **ATM embedded software**: Go (or C++ for production)
- **Bank backend**: Java (Spring Boot ecosystem)

**Real-world**: ATM firmware is C/C++ (NCR, Diebold). Backend is Java/C#.

---

### **9.5 Authentication: JWT vs Session**

| Aspect | JWT (Stateless) | Session (Stateful) |
|--------|-----------------|---------------------|
| **Server Memory** | None | Requires session store |
| **Scalability** | Excellent | Needs sticky sessions or Redis |
| **Security** | Token theft risk | Session hijacking risk |
| **Revocation** | Hard (need blacklist) | Easy (delete session) |

**When JWT**:
```java
// Mobile banking app (millions of users, distributed ATMs)
String jwt = Jwts.builder()
    .setSubject(userId)
    .claim("accountId", accountId)
    .setExpiration(Date.from(Instant.now().plus(15, ChronoUnit.MINUTES)))
    .signWith(privateKey)
    .compact();

// ATM validates JWT without calling backend
// ✅ Scales horizontally (no shared state)
```

**When Session**:
```java
// ATM machine (single user at a time, short session)
HttpSession session = request.getSession();
session.setAttribute("atmId", atmId);
session.setAttribute("cardNumber", cardNumber);
session.setMaxInactiveInterval(300);  // 5 min

// ✅ Easy to invalidate (eject card → destroy session)
// ✅ No token theft risk (session ID rotates)
```

**My Choice: Session for ATMs**
- ATM serves **one user at a time** (no scaling needs)
- **Security**: Easy to destroy session on card ejection
- **Simplicity**: No JWT signing/verification overhead

**Mobile banking**: Use JWT (millions of concurrent users).

---

## 🎓 **Final Tips for 15 YOE ATM Interview**

1. **Think Security First**: ATMs deal with money—mention encryption, hashing, audit logs, fraud detection
2. **State Pattern is Key**: ATM is the textbook example—nail this pattern
3. **Cash Dispensing Algorithm**: Greedy + Chain of Responsibility—explain both
4. **Database Transactions**: Show you understand ACID, locks, race conditions
5. **Real-World Experience**: Reference actual ATMs (Diebold, NCR, physical hardware constraints)

**Senior-level insights**:
- Mention **HSM (Hardware Security Module)** for PIN storage
- Discuss **EMV chip** vs **magnetic stripe** security
- Talk about **cash reconciliation** (daily ATM balancing)
- Consider **offline mode** (ATM works when bank backend is down)

**Good luck!** Remember: ATM design tests your understanding of **state machines**, **security**, and **concurrency**. Show you can build production-grade financial systems! 🚀
