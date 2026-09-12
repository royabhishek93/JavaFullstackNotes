# ATM System — Complete LLD Interview Guide

**Interview Duration: 45 min | Difficulty: Hard | Must-Know: ⭐⭐⭐⭐⭐ | 15-YOE Focus: State Machine + Concurrent Transactions**

---

## BIG PICTURE — Architecture

```
 ┌──────────────────────────────────────────────────────────────────┐
 │                      ATM SYSTEM                                 │
 │                                                                  │
 │  USER JOURNEY          ATM STATE MACHINE        BANK BACKEND    │
 │  ┌────────────┐        ┌─────────────────┐    ┌─────────────┐  │
 │  │ Insert Card│──────► │  IDLE           │    │ Account DB  │  │
 │  │ Enter PIN  │        │  CARD_INSERTED  │◄──►│ Balance Svc │  │
 │  │ Select Txn │        │  PIN_VERIFIED   │    │ Auth Svc    │  │
 │  │ Withdraw   │        │  SELECTING_TXN  │    │ Txn Ledger  │  │
 │  │ Collect    │        │  PROCESSING     │    └─────────────┘  │
 │  └────────────┘        │  DISPENSING     │                      │
 │                        │  CARD_BLOCKED   │   CASH DISPENSER     │
 │                        └─────────────────┘   ┌─────────────┐   │
 │                                               │ Cassette    │   │
 │                                               │ ₹100 notes  │   │
 │                                               │ ₹500 notes  │   │
 │                                               └─────────────┘   │
 └──────────────────────────────────────────────────────────────────┘

 STATE TRANSITION:
 ┌──────────────────────────────────────────────────────────────────┐
 │                                                                  │
 │  [IDLE]─insertCard()─►[CARD_INSERTED]─verifyPIN()─►[VERIFIED]  │
 │    ▲                        │                         │         │
 │    │                    timeout/eject            [SELECTING]    │
 │    │                        │                         │         │
 │    │                        ▼                    selectTxn()    │
 │    │                   [IDLE]                         │         │
 │    │                                            [PROCESSING]    │
 │    │                                                   │         │
 │    │              3 wrong PINs                  dispense /      │
 │    │         [CARD_BLOCKED]◄────────────────── [DISPENSING]    │
 │    │                                                   │         │
 │    └───────────────── ejectCard() ────────────────────┘         │
 └──────────────────────────────────────────────────────────────────┘
```

---

## CONVERSATIONAL SCRIPT

### Phase 1 — Requirements (5 min)

**You:** "Let me clarify before diving in.

Functional:
- User inserts card, enters PIN — 3 wrong attempts blocks card
- Select transaction: withdraw, balance inquiry, mini statement
- Withdraw: check balance, dispense cash, deduct from account
- Print receipt option
- Session timeout — idle on any screen ejects card after 60s

Non-functional:
- Thread safety critical — ATM processes one user at a time physically, but the bank backend may have concurrent requests from multiple ATMs for the same account
- Consistency — if cash dispensed but network drops before debit, account should still be debited (the hard part!)
- Atomicity — withdraw must be atomic: no cash without debit, no debit without cash

The trickiest problem here is: what if we dispense cash but the bank API call to deduct balance fails? Let me design that carefully."

---

### Phase 2 — Core Design

**You:** "Two main design patterns:
1. State Pattern — for ATM machine lifecycle (same as vending machine but more states)
2. Command Pattern — for transactions (withdraw, balance, statement) — each is a Command with execute() and rollback()

```
ATM               → Context: holds current state, card, session
ATMState          → interface
Card              → cardNumber, expiryDate, maskedPAN
Account           → accountNumber, balance (in bank system)
Session           → userId, authenticated, timeout timer
Transaction       → Command interface: execute(), rollback()
WithdrawCommand   → checks balance → debits → signals dispense
CashDispenser     → physical dispense, tracks cassette levels
ReceiptPrinter    → prints receipt
BankService       → interface to core banking
```"

---

### Phase 3 — Implementation

```java
// ─── ATM State Interface ────────────────────────────────────────
public interface ATMState {
    void insertCard(ATM atm, Card card);
    void enterPIN(ATM atm, String pin);
    void selectTransaction(ATM atm, TransactionType type, int amount);
    void ejectCard(ATM atm);
    void sessionTimeout(ATM atm);
}

// ─── Card ───────────────────────────────────────────────────────
public class Card {
    private final String cardNumber;
    private final String maskedPAN;   // "****-****-****-1234"
    private int failedPINAttempts;
    private boolean blocked;

    public Card(String cardNumber) {
        this.cardNumber = cardNumber;
        this.maskedPAN = "*".repeat(12) + cardNumber.substring(12);
        this.failedPINAttempts = 0;
        this.blocked = false;
    }

    public void recordFailedAttempt() {
        failedPINAttempts++;
        if (failedPINAttempts >= 3) blocked = true;
    }

    public boolean isBlocked() { return blocked; }
    public int getFailedAttempts() { return failedPINAttempts; }
    public String getCardNumber() { return cardNumber; }
    public String getMaskedPAN() { return maskedPAN; }
}

// ─── Transaction Command ────────────────────────────────────────
public interface Transaction {
    TransactionResult execute(BankService bankService, String accountId, int amount);
    void rollback(BankService bankService, String accountId, int amount);
}

public enum TransactionResult { SUCCESS, INSUFFICIENT_FUNDS, NETWORK_ERROR, LIMIT_EXCEEDED }

// ─── Withdraw Command ───────────────────────────────────────────
public class WithdrawTransaction implements Transaction {
    @Override
    public TransactionResult execute(BankService bankService, String accountId, int amount) {
        // Step 1: Check balance
        int balance = bankService.getBalance(accountId);
        if (balance < amount) return TransactionResult.INSUFFICIENT_FUNDS;

        // Step 2: Check daily/transaction limits
        if (amount > 20000) return TransactionResult.LIMIT_EXCEEDED;
        if (amount % 100 != 0) throw new IllegalArgumentException("Amount must be multiple of 100");

        // Step 3: Debit atomically (two-phase: reserve then confirm)
        String txnRef = bankService.reserveFunds(accountId, amount);
        if (txnRef == null) return TransactionResult.NETWORK_ERROR;

        return TransactionResult.SUCCESS;
    }

    @Override
    public void rollback(BankService bankService, String accountId, int amount) {
        // Called if cash dispense fails after bank debit
        bankService.reverseTransaction(accountId, amount);
    }
}

// ─── ATM Context ─────────────────────────────────────────────────
public class ATM {
    private volatile ATMState currentState;
    private Card currentCard;
    private String authenticatedAccountId;
    private final CashDispenser cashDispenser;
    private final BankService bankService;
    private final ReceiptPrinter receiptPrinter;
    private ScheduledFuture<?> sessionTimeoutTask;
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();
    private final ReentrantLock lock = new ReentrantLock();

    // States
    private final ATMState idleState        = new IdleState();
    private final ATMState cardInsertedState = new CardInsertedState();
    private final ATMState verifiedState    = new VerifiedState();
    private final ATMState processingState  = new ProcessingState();
    private final ATMState blockedState     = new CardBlockedState();

    public ATM(CashDispenser cashDispenser, BankService bankService) {
        this.cashDispenser  = cashDispenser;
        this.bankService    = bankService;
        this.receiptPrinter = new ReceiptPrinter();
        this.currentState   = idleState;
    }

    public void insertCard(Card card) {
        lock.lock();
        try { currentState.insertCard(this, card); }
        finally { lock.unlock(); }
    }

    public void enterPIN(String pin) {
        lock.lock();
        try { currentState.enterPIN(this, pin); }
        finally { lock.unlock(); }
    }

    public void withdraw(int amount) {
        lock.lock();
        try { currentState.selectTransaction(this, TransactionType.WITHDRAW, amount); }
        finally { lock.unlock(); }
    }

    // ─── Withdraw Flow (called by ProcessingState) ─────────────
    void executeWithdraw(int amount) {
        WithdrawTransaction txn = new WithdrawTransaction();
        TransactionResult result = txn.execute(bankService, authenticatedAccountId, amount);

        if (result == TransactionResult.SUCCESS) {
            boolean dispensed = cashDispenser.dispense(amount);
            if (!dispensed) {
                // CRITICAL: cash failed, roll back bank debit
                txn.rollback(bankService, authenticatedAccountId, amount);
                System.out.println("Dispense failed. Transaction reversed. Please try again.");
            } else {
                bankService.confirmTransaction(authenticatedAccountId, amount);
                receiptPrinter.print(authenticatedAccountId, amount, "WITHDRAWAL");
                System.out.println("Please collect ₹" + amount);
            }
        } else {
            System.out.println("Transaction failed: " + result);
        }
        setState(verifiedState); // return to transaction menu
    }

    void startSessionTimeout() {
        cancelSessionTimeout();
        sessionTimeoutTask = scheduler.schedule(() -> {
            sessionTimeout();
        }, 60, TimeUnit.SECONDS);
    }

    void cancelSessionTimeout() {
        if (sessionTimeoutTask != null) sessionTimeoutTask.cancel(false);
    }

    void sessionTimeout() {
        lock.lock();
        try { currentState.sessionTimeout(this); }
        finally { lock.unlock(); }
    }

    // Package-visible
    void setState(ATMState state) { this.currentState = state; }
    void setCurrentCard(Card card) { this.currentCard = card; }
    Card getCurrentCard() { return currentCard; }
    void setAuthenticatedAccountId(String id) { this.authenticatedAccountId = id; }
    BankService getBankService() { return bankService; }
    ATMState getIdleState()       { return idleState; }
    ATMState getCardInsertedState() { return cardInsertedState; }
    ATMState getVerifiedState()   { return verifiedState; }
    ATMState getProcessingState() { return processingState; }
    ATMState getBlockedState()    { return blockedState; }
}

// ─── CardInsertedState ─────────────────────────────────────────
public class CardInsertedState implements ATMState {
    @Override
    public void insertCard(ATM atm, Card card) {
        System.out.println("Card already inserted");
    }

    @Override
    public void enterPIN(ATM atm, String pin) {
        Card card = atm.getCurrentCard();
        if (card.isBlocked()) {
            System.out.println("Card is blocked. Contact your bank.");
            atm.setState(atm.getBlockedState());
            return;
        }

        String accountId = atm.getBankService().verifyPIN(card.getCardNumber(), pin);
        if (accountId != null) {
            atm.setAuthenticatedAccountId(accountId);
            System.out.println("PIN verified. Welcome!");
            atm.setState(atm.getVerifiedState());
            atm.startSessionTimeout();
        } else {
            card.recordFailedAttempt();
            int remaining = 3 - card.getFailedAttempts();
            if (card.isBlocked()) {
                System.out.println("Card blocked after 3 wrong attempts.");
                atm.getBankService().blockCard(card.getCardNumber());
                atm.setState(atm.getBlockedState());
            } else {
                System.out.println("Wrong PIN. " + remaining + " attempt(s) left.");
            }
        }
    }

    @Override
    public void ejectCard(ATM atm) {
        System.out.println("Card ejected.");
        atm.setCurrentCard(null);
        atm.setState(atm.getIdleState());
    }

    @Override
    public void selectTransaction(ATM atm, TransactionType type, int amount) {
        System.out.println("Please verify PIN first.");
    }

    @Override
    public void sessionTimeout(ATM atm) { ejectCard(atm); }
}
```

---

## Component Choices

```
COMPONENT            CHOICE                  WHY
──────────────────────────────────────────────────────────────────────
Machine lifecycle    State Pattern           Each state has different
                                             behavior for same input.
                                             Eliminates giant if-else.

Transactions         Command Pattern         execute() + rollback().
                                             New transaction types without
                                             changing ATM state classes.

Thread safety        ReentrantLock           Better than synchronized:
                                             tryLock with timeout,
                                             fair ordering (prevents
                                             starvation in high-load).

Session timeout      ScheduledExecutor       Non-blocking 60s timer.
                                             Cancelled on user activity.
                                             Timer fires → sessionTimeout()
                                             ejects card automatically.

Bank communication   Interface (BankService) Decouples ATM from bank impl.
                                             Can mock for testing.
                                             Real impl: ISO 8583 protocol.

Dispense-then-debit  Two-phase protocol      Reserve funds → dispense →
vs debit-then-dispense                       confirm. If dispense fails:
                                             reverse reservation.
                                             Prevents money lost from
                                             account without cash given.
```

---

## Failure Modes — The Hard Problems

```
SCENARIO                    PROBLEM                    SOLUTION
──────────────────────────────────────────────────────────────────────
Network drops after          Account debited,          Two-phase: reserveFunds()
cash dispensed               no confirmation           then confirmTxn().
                                                       If ATM restarts: reconcile
                                                       pending reservations.
                                                       Bank has 24h timeout on
                                                       reservations → auto-reverse.

Cash dispenser jams          Partial cash out          Hardware reports jamCount.
                                                       If jamCount > 0: rollback
                                                       full amount. Flag cassette
                                                       for maintenance.

Power failure mid-           ATM restarts              Persistent transaction log.
transaction                                            On startup: check last state.
                                                       Any "RESERVED" txn: reverse
                                                       it (assume incomplete).

User claims wrong amount     Dispute                   Camera + timestamp logs.
dispensed                                              Cassette audit on EOD.
                                                       Discrepancy triggers alert.

Same account, two ATMs       Concurrent debit          Bank's core uses optimistic
simultaneously               over-draws               locking / row-level lock.
                                                       ATM doesn't handle this —
                                                       bank is the source of truth.
```

---

## Senior Trap Questions

**Q1: "Who is responsible for consistency — the ATM or the bank?"**
```
The BANK is the source of truth for account balance.
The ATM is a terminal — it sends requests to the bank.

ATM's responsibility:
  - Sequence operations correctly (reserve → dispense → confirm)
  - Roll back if dispense fails
  - Not leak card data, not accept jammed cards

Bank's responsibility:
  - Idempotent API (ATM may retry the same transaction after network hiccup)
  - Row-level locking on account balance
  - Idempotency key per transaction reference
```

**Q2: "ATM dispenses ₹5000 but bank reversal API also fails. Now what?"**
```
This is a dual failure — both dispense AND rollback failed.
The ATM has given away money it couldn't account for.

In production:
  1. ATM logs this as a PENDING_REVERSAL state to persistent storage
  2. ATM's EOD reconciliation process retries reversals with exponential backoff
  3. Bank has a 24-72h dispute window to detect ATM reversals
  4. Physical cash audit: count cassette at EOD, compare with transaction log
  5. Insurance covers final unresolvable discrepancy

Software can't fully prevent hardware-software dual failures.
The answer is: detect, log, escalate, reconcile.
```

**Q3: "How do you prevent card skimming in the software design?"**
```
Card number NEVER stored in ATM memory longer than the session.
After session ends: card object nulled, GC'd.
Masked PAN used for all logging: ****-****-****-1234.
PIN never stored — only compared via bank's verifyPIN() which compares hashes.
Communication to bank: TLS 1.3 + ISO 8583 end-to-end encryption.
No card data written to disk on ATM.
```

---

## Interview Cheat Sheet

> "The ATM is a great State pattern problem with the added complexity of transactional consistency. States are Idle, CardInserted, PINVerified, Processing, Dispensing, CardBlocked — and the behavior of every input changes per state. The hardest design decision is the cash-dispense-vs-debit ordering. I use a two-phase protocol: reserve funds at the bank first, then dispense cash, then confirm. If dispense fails: reverse the reservation. If the confirmation fails after dispense: the ATM logs it as PENDING_REVERSAL and retries via reconciliation. The bank's API must be idempotent — the ATM may retry due to network timeouts. Thread safety uses ReentrantLock so we can add tryLock with timeout to detect if a thread is stuck. Session timeout uses ScheduledExecutorService to eject card after 60s of inactivity."
