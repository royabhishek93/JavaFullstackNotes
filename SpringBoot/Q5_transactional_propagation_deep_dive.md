# Q5: @Transactional Propagation — Deep Internals for Architect Interviews (15-Yr Level)

**Study Time:** 25-30 minutes | **Frequency:** 90% in architect rounds 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "Walk me through what AbstractPlatformTransactionManager does differently for REQUIRED vs REQUIRES_NEW vs NESTED. How does it suspend a transaction? Where does the savepoint live? What happens to the ThreadLocal?" — Real architect question.

---

## NEW LEARNER FOUNDATION — Read This First

### What is Transaction Propagation? (Plain English)
```
Propagation answers: "When method A (already in a transaction) calls method B,
                      what should method B do with the transaction?"

Think of it like a meeting room booking:
  REQUIRED     = "Use the room that's already booked. If none, book a new one."
  REQUIRES_NEW = "Always book a SEPARATE room. Don't use the existing one."
  NESTED       = "Stay in the same room but mark a checkpoint on the whiteboard.
                  If my part fails, erase back to the checkpoint. Room stays open."
  MANDATORY    = "I refuse to work without an already-booked room. Throw error if none."
  NOT_SUPPORTED= "I don't need a room. If one is booked, step out while I work."
```

### What is a Savepoint? (Plain English)
```
A savepoint is like a "game save" inside a transaction.

Normal transaction: all-or-nothing
  Step 1: save order     ──┐
  Step 2: save items     ──┤ All committed together OR all rolled back
  Step 3: update stock   ──┘

Savepoint: partial rollback within a transaction
  Step 1: save order           ← committed in outer TX
  SAVEPOINT sp1                ← mark this point
  Step 2: save reward points   ← try this
  → FAILS                      → rollback TO sp1 (only step 2 undone)
  Step 1 data still safe → outer TX can continue and commit step 1

SQL equivalent: SAVEPOINT sp1; ... ROLLBACK TO SAVEPOINT sp1;
```

### What is "Suspending" a Transaction? (Plain English)
```
REQUIRES_NEW needs to start a completely independent transaction.
But there's already an active transaction on this thread.

"Suspending" = put the current transaction in a drawer.
               Take a new connection from the pool.
               Do your work in the new independent transaction.
               Open the drawer, restore the old transaction.

Technically: unbind the current ConnectionHolder from ThreadLocal,
             store it in a SuspendedResourcesHolder,
             start fresh, then restore when done.
```

---

## BIG PICTURE — The Three Propagation Types Visualised

```
 SCENARIO: OrderService.placeOrder() calls AuditService.log()
           and RewardService.addPoints()

 ──────────────────────────────────────────────────────────────────
 REQUIRED (default) — one transaction, shared connection:
 ──────────────────────────────────────────────────────────────────

 Thread: ───────────────────────────────────────────────────────►
         │                                                       │
   BEGIN TX (conn#42, autoCommit=off)                     COMMIT │
         │                                                       │
   placeOrder()──────────────────────────────────────────────────│
         │ orderRepo.save()    → conn#42                         │
         │ inventoryService.deductStock() → JOINS conn#42        │
         │   inventoryRepo.save() → conn#42 (SAME TX!)           │
         └────────────────────────────────────────────────────►  │
                                                 conn#42.commit()─┘
 ThreadLocal: { DataSource → conn#42 } throughout entire call

 ──────────────────────────────────────────────────────────────────
 REQUIRES_NEW — independent TX, two separate connections:
 ──────────────────────────────────────────────────────────────────

 Thread: ───────────────────────────────────────────────────────►
         │                                                       │
   BEGIN TX (conn#42)                                   COMMIT   │
         │                                             conn#42   │
   placeOrder()─────────────────────────────────────────────────►│
     │                                                           │
     │  SUSPEND conn#42 ← saved in SuspendedResourcesHolder     │
     │  ThreadLocal = {}  ← unbound!                            │
     │                                                           │
     │  BEGIN NEW TX (conn#99)                                   │
     │  auditService.log()────────────────────►                  │
     │    auditRepo.save() → conn#99           │ COMMIT conn#99  │
     │  ◄──────────────────────────────────────┘                 │
     │                                                           │
     │  RESUME conn#42 ← restored to ThreadLocal                │
     │  ThreadLocal = { DS → conn#42 }                          │
     │                                                           │
     └─── continues on conn#42 ──────────────────────►COMMIT───►│

 Even if conn#42 rolls back: conn#99 audit already committed ✅

 ──────────────────────────────────────────────────────────────────
 NESTED — savepoint inside same TX, same connection:       ◄◄◄ THIS FILE
 ──────────────────────────────────────────────────────────────────

 Thread: ───────────────────────────────────────────────────────►
         │                                                       │
   BEGIN TX (conn#42)                                   COMMIT   │
         │                                             conn#42   │
   placeOrder()─────────────────────────────────────────────────►│
     │ paymentRepo.save() → conn#42                              │
     │                                                           │
     │  SAVEPOINT sp1 on conn#42 ← checkpoint                   │
     │  rewardService.addPoints()────────────────────►           │
     │    rewardRepo.save() → conn#42                 │          │
     │    ← THROWS RewardException                   │          │
     │  ROLLBACK TO sp1 ← only reward undone          │          │
     │  RELEASE SAVEPOINT sp1                         │          │
     │                                                           │
     │  paymentRepo.markComplete() → conn#42 (still open)       │
     └─── conn#42.commit() ──────────────────────────────────►  │

 Payment saved ✅  Rewards NOT saved (rolled to savepoint) ✅
```

---

## The Core: AbstractPlatformTransactionManager.getTransaction()

```
This is THE method that implements all propagation logic.
Every propagation type decision happens here.

Inputs:
  - TransactionDefinition (has propagation, isolation, timeout, readOnly)
  - Current TransactionSynchronizationManager state (is there an active TX?)

The decision tree:
```

```java
// AbstractPlatformTransactionManager.getTransaction() — logic (simplified):

public final TransactionStatus getTransaction(TransactionDefinition def) {
    Object transaction = doGetTransaction();
    // doGetTransaction() checks TransactionSynchronizationManager:
    //   - DataSourceTransactionManager: looks for ConnectionHolder in ThreadLocal
    //   - JpaTransactionManager: looks for EntityManagerHolder in ThreadLocal
    // Returns a transaction object with info about current state

    boolean txExists = isExistingTransaction(transaction);
    // true = there IS an active TX on this thread

    if (txExists) {
        return handleExistingTransaction(def, transaction);
        // Routes to REQUIRED / REQUIRES_NEW / NESTED / MANDATORY / etc.
    }

    // No current TX:
    if (def.getPropagation() == MANDATORY) throw new IllegalTransactionStateException();
    if (def.getPropagation() == REQUIRED || REQUIRES_NEW || NESTED) {
        // start fresh TX
        return startTransaction(def, transaction);
    }
    // SUPPORTS / NOT_SUPPORTED / NEVER → run without TX
}
```

---

## Part 1: REQUIRED (Default) — Join the Existing TX

```java
// AbstractPlatformTransactionManager for REQUIRED with existing TX:
// → reuses the ConnectionHolder already bound to the thread
// → NO new connection acquired, NO new transaction started
// → inner and outer share the SAME DB connection, SAME TX

@Service @Transactional  // opens TX (REQUIRED default)
public class OrderService {
    public void placeOrder(Order order) {
        orderRepo.save(order);
        inventoryService.deductStock(order.getProductId(), order.getQty());
        // inventoryService is REQUIRED too → joins the SAME TX
    }
}

@Service @Transactional(propagation = REQUIRED)
public class InventoryService {
    public void deductStock(Long productId, int qty) {
        // Shares the SAME connection (same ThreadLocal ConnectionHolder)
        // If this throws → entire outer TX rolls back (same TX)
        inventoryRepo.deduct(productId, qty);
    }
}
```

```
REQUIRED TX Flow (ThreadLocal view):

Thread starts:
  TSM.resources = {}

OrderService.placeOrder() called:
  TSM.resources = { DataSource → ConnectionHolder(conn#42, TX active) }

  InventoryService.deductStock() called (REQUIRED):
    isExistingTransaction() → true
    handleExistingTransaction(REQUIRED) → return existing TX status
    TSM.resources = { DataSource → ConnectionHolder(conn#42, TX active) }  ← unchanged
    deductStock runs on conn#42 ✅

  Back in placeOrder → commit:
    conn#42.commit()
    TSM.resources = {}  ← cleared
```

---

## Part 2: REQUIRES_NEW — Suspend and Create Independent TX

### What "Suspend" Actually Means

```java
// AbstractPlatformTransactionManager for REQUIRES_NEW with existing TX:
protected TransactionStatus handleExistingTransaction(TransactionDefinition def, Object transaction) {
    if (def.getPropagation() == REQUIRES_NEW) {

        // STEP 1: Suspend the outer transaction
        SuspendedResourcesHolder suspendedResources = suspend(transaction);
        // suspend() does:
        //   1. Unbinds ConnectionHolder from TSM ThreadLocal
        //      TSM.resources no longer has an active connection
        //   2. Saves the outer TX state into SuspendedResourcesHolder:
        //      { outerConnection, outerSynchronizations, outerTXName, outerReadOnly }
        //   3. Clears all TSM ThreadLocal state

        // STEP 2: Start a fresh transaction on a NEW connection
        startTransaction(def, transaction);
        // acquires a new connection from HikariCP (conn#99)
        // conn#99.setAutoCommit(false)
        // TSM.bindResource(dataSource, ConnectionHolder(conn#99))
        // Now thread has a brand-new independent TX

        // suspendedResources is stored in the inner TransactionStatus
        // When inner TX completes, it calls resume(suspendedResources)
    }
}

// After inner REQUIRES_NEW TX completes (commit OR rollback):
// resume(suspendedResources):
//   1. Releases conn#99 back to pool (or rolls it back)
//   2. Re-binds outer ConnectionHolder (conn#42) to TSM ThreadLocal
//   3. Outer TX resumes as if nothing happened
```

```
REQUIRES_NEW TX Flow (ThreadLocal view):

Thread starts:
  TSM.resources = {}

OrderService.placeOrder() → REQUIRED:
  TSM.resources = { DS → ConnectionHolder(conn#42, TX active) }

  AuditService.log() → REQUIRES_NEW:
    SUSPEND:  SuspendedHolder = { conn#42, synchronizations... }
              TSM.resources = {}  ← outer connection UNBOUND

    START NEW TX:
              TSM.resources = { DS → ConnectionHolder(conn#99, TX active) }

    audit.save() on conn#99 ✅
    COMMIT conn#99 ← audit permanently saved, independent of outer TX

    RESUME:   TSM.resources = { DS → ConnectionHolder(conn#42, TX active) }  ← restored

  Back in placeOrder → outer TX on conn#42 continues...
  inventoryService.deduct() → fails, throws RuntimeException
  ROLLBACK conn#42 ← order NOT saved, inventory NOT deducted
  TSM.resources = {}

Result: audit record PERSISTED, order NOT saved ← exactly what REQUIRES_NEW guarantees
```

### The Deadlock Trap With REQUIRES_NEW

```java
// DANGER: REQUIRES_NEW accessing the same table as outer TX

@Service @Transactional
public class OrderService {
    public void placeOrder(Order order) {
        // OUTER TX: holds a row lock on ORDER table (SELECT FOR UPDATE or row-level lock)
        Order o = orderRepo.findByIdForUpdate(order.getId());  // ← LOCK ACQUIRED

        auditService.log(order.getId());  // REQUIRES_NEW ↓
    }
}

@Service @Transactional(propagation = REQUIRES_NEW)
public class AuditService {
    public void log(Long orderId) {
        // INNER TX (new connection conn#99):
        // Tries to read ORDER table to denormalize some fields into audit log
        Order o = orderRepo.findById(orderId);  // ← TRIES TO READ LOCKED ROW
        // conn#99 waits for conn#42 (outer) to release lock
        // conn#42 (outer) is SUSPENDED, waiting for conn#99 (inner) to finish
        // → DEADLOCK: neither can proceed
        // DB timeout → exception → both TXs roll back
    }
}

// FIX: REQUIRES_NEW inner TX must ONLY write to tables not locked by outer TX
// Pass all needed data as method parameters (don't re-query locked rows inside inner TX)
@Service @Transactional(propagation = REQUIRES_NEW)
public class AuditService {
    public void log(Long orderId, String eventType) {  // data passed in, no re-query
        auditRepo.save(new AuditLog(orderId, eventType));
    }
}
```

---

## Part 3: NESTED — Savepoint Inside the Same TX

### What "Savepoint" Actually Means

```java
// AbstractPlatformTransactionManager for NESTED with existing TX:
protected TransactionStatus handleExistingTransaction(TransactionDefinition def, Object transaction) {
    if (def.getPropagation() == NESTED) {
        if (!isNestedTransactionAllowed()) throw new NestedTransactionNotSupportedException();

        // Uses the SAME connection (no new connection acquired)
        // Creates a SAVEPOINT on that connection
        SavepointManager savepointManager = (SavepointManager) transaction;
        Object savepoint = savepointManager.createSavepoint();
        // JDBC: connection.setSavepoint("SAVEPOINT_1")
        // This tells the DB: "remember this point in the TX"

        DefaultTransactionStatus status = new DefaultTransactionStatus(...);
        status.setSavepoint(savepoint);
        return status;
        // If inner code throws and is caught by outer:
        //   connection.rollback(savepoint) → undo inner changes, keep outer changes
        //   connection.releaseSavepoint(savepoint) → remove savepoint marker
        // If inner succeeds:
        //   savepoint is released (but not committed — outer TX still controls commit)
        // If outer rolls back:
        //   entire TX rolls back including inner — savepoint is just gone
    }
}
```

```
NESTED TX Flow (ThreadLocal view — SAME connection throughout):

OrderService.processPayment() → REQUIRED:
  TSM.resources = { DS → ConnectionHolder(conn#42, TX active) }

  conn#42: BEGIN (implicit, autocommit=false)
  conn#42: INSERT INTO payments ... ← payment saved in TX

  RewardService.addPoints() → NESTED:
    conn#42: SAVEPOINT sp1  ← DB marks position in TX
    conn#42: INSERT INTO rewards ...

    → THROWS RewardException

    CATCH in outer:
    conn#42: ROLLBACK TO SAVEPOINT sp1  ← only reward insert undone
    conn#42: RELEASE SAVEPOINT sp1

  Back in processPayment → continues without rewards
  conn#42: INSERT INTO payment_audit ...

  COMMIT conn#42 ← payment + audit saved, reward NOT saved
```

```java
// Production code pattern:
@Service @Transactional
public class PaymentService {
    public void processPayment(Payment payment) {
        paymentRepo.save(payment);

        try {
            rewardService.addPoints(payment.getUserId(), payment.getAmount());
        } catch (RewardException ex) {
            log.warn("Reward failed — payment still succeeds: {}", ex.getMessage());
            // Savepoint rolled back automatically when NESTED threw
            // Outer TX continues cleanly
        }

        paymentRepo.markComplete(payment.getId());
        // Commits: payment saved + marked complete, rewards NOT added
    }
}

@Service @Transactional(propagation = Propagation.NESTED)
public class RewardService {
    public void addPoints(Long userId, BigDecimal amount) {
        rewardRepo.addPoints(userId, calculatePoints(amount));
    }
}
```

### DB Support Check

```
Savepoints are standard SQL but not all drivers handle them the same:
  PostgreSQL:  ✅ Full savepoint support
  MySQL 5.7+:  ✅ Savepoints supported (InnoDB engine)
  Oracle:      ✅ Native savepoints
  H2:          ✅ Supported (great for testing NESTED)
  SQL Server:  ✅ Supported
  MariaDB:     ✅ Supported

Spring checks useSavepointForNestedTransaction() at startup
If driver doesn't support it → NestedTransactionNotSupportedException at runtime
Test with @DataJpaTest (H2) to verify your NESTED logic
```

---

## Part 4: MANDATORY and NOT_SUPPORTED

```java
// MANDATORY: I REFUSE to run without an existing TX
// Use to enforce architectural contracts — prevent accidental standalone calls

@Service
public class InventoryService {

    @Transactional(propagation = Propagation.MANDATORY)
    public void deductStock(Long productId, int qty) {
        // Can ONLY be called from within a @Transactional context
        // Standalone call → IllegalTransactionStateException
        // Why: this method does a partial update, MUST be atomic with caller
    }
}

// How AbstractPlatformTransactionManager implements this:
if (def.getPropagation() == MANDATORY) {
    if (!isExistingTransaction(transaction)) {
        throw new IllegalTransactionStateException(
            "No existing transaction found for transaction marked with propagation 'mandatory'"
        );
    }
    // If TX exists: just join it (same as REQUIRED behavior)
}
```

```java
// NOT_SUPPORTED: suspend TX if one exists, run WITHOUT a transaction
// Use for: cache reads, reporting queries that must NOT be in a TX
//          (prevents TX holding a connection open during long reads)

@Service
public class ReportingService {

    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public List<OrderSummary> getOrderReport(LocalDate from, LocalDate to) {
        // If called from within a TX:
        //   outer TX is SUSPENDED (same suspend mechanism as REQUIRES_NEW)
        //   this method runs WITHOUT a transaction (autocommit mode)
        //   outer TX is RESUMED when method returns
        //
        // Why: long-running report query should not hold a DB connection locked
        //      in a TX. Read uncommitted is acceptable for reporting.
        return orderRepo.findSummariesBetween(from, to);
    }
}
```

---

## Part 5: Self-Invocation Propagation Trap (Most Dangerous Production Bug)

```java
@Service
public class OrderService {

    @Transactional  // REQUIRED — opens outer TX
    public void placeOrder(Order order) {
        orderRepo.save(order);
        this.auditOrder(order);  // SELF INVOCATION — proxy bypassed!
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void auditOrder(Order order) {
        // You think: runs in independent TX, commits even if outer fails
        // Reality: runs in the SAME outer TX (REQUIRES_NEW ignored)
        // If outer fails → BOTH order AND audit roll back!
        auditRepo.save(new AuditLog(order.getId()));
    }
}

// Why: 'this.auditOrder()' calls the REAL object method
// The real object is NOT the proxy — it has no interceptor chain
// AbstractPlatformTransactionManager never sees REQUIRES_NEW
// getTransaction() is never called for the inner method
// It executes inside the outer TX as if no @Transactional existed on auditOrder

// Evidence: add logging to AbstractPlatformTransactionManager
// logging.level.org.springframework.transaction=TRACE
// You will see: getTransaction() called ONCE, not twice
```

---

## Part 6: TransactionSynchronizationManager — The Full Picture

```
TSM holds (ALL ThreadLocal — one copy per thread):

  resources:              Map<Object, Object>
    DataSource → ConnectionHolder    ← the active DB connection
    EntityManagerFactory → EntityManagerHolder  ← for JPA

  synchronizations:       Set<TransactionSynchronization>
    → registered by @TransactionalEventListener, Hibernate session, etc.
    → fired on: afterCommit(), afterRollback(), afterCompletion()

  currentTransactionName: String (e.g. "OrderService.placeOrder")
  currentTransactionReadOnly: Boolean
  currentTransactionIsolationLevel: Integer
  actualTransactionActive: Boolean

Why ThreadLocal?
  Each HTTP request = one thread (in traditional servlet model)
  ThreadLocal makes TX state "magically" available to all code on the thread
  without passing a "transaction context" parameter everywhere
  ALL repositories/services called on the same thread share the same TX

Virtual Threads (Java 21) + ThreadLocal:
  Virtual threads INHERIT ThreadLocal values from their parent at creation time
  But are NOT shared — each virtual thread has its own copy
  @Transactional works correctly with virtual threads
  (Spring Boot 3.2 tested and confirmed)
```

---

## Quick Reference: Propagation Decision Matrix

```
Outer TX: YES
┌──────────────────┬─────────────────────────────────────────────────────────┐
│ Propagation      │ What happens                                            │
├──────────────────┼─────────────────────────────────────────────────────────┤
│ REQUIRED         │ Join outer TX (same connection, same commit)            │
│ REQUIRES_NEW     │ Suspend outer, start new TX on new connection           │
│                  │ Outer resumes after inner completes                     │
│ NESTED           │ Create savepoint on same connection                     │
│                  │ Inner rollback → rollback to savepoint only             │
│                  │ Outer rollback → kills inner too (same TX)              │
│ MANDATORY        │ Join outer TX (enforces contract)                       │
│ NOT_SUPPORTED    │ Suspend outer, run without TX                           │
│ NEVER            │ Throw exception (TX must NOT exist)                     │
│ SUPPORTS         │ Join outer TX                                           │
└──────────────────┴─────────────────────────────────────────────────────────┘

Outer TX: NO
┌──────────────────┬─────────────────────────────────────────────────────────┐
│ REQUIRED         │ Create new TX                                           │
│ REQUIRES_NEW     │ Create new TX                                           │
│ NESTED           │ Create new TX                                           │
│ MANDATORY        │ THROW IllegalTransactionStateException ←                │
│ NOT_SUPPORTED    │ Run without TX                                          │
│ NEVER            │ Run without TX                                          │
│ SUPPORTS         │ Run without TX                                          │
└──────────────────┴─────────────────────────────────────────────────────────┘
```

---

## Architect Decision Guide

```
Need sub-operation to always commit regardless of outer TX failure?
  → REQUIRES_NEW (audit logs, notifications, idempotency keys)
  → ⚠️ Never re-query rows locked by outer TX → deadlock

Need sub-operation to be "retryable" without affecting outer?
  → NESTED (optional enrichment, batch item processing)
  → ⚠️ Outer rollback still kills inner (same TX)
  → ⚠️ Only works on DBs that support savepoints

Need to enforce caller must always be transactional?
  → MANDATORY (domain aggregate mutations, core data writes)

Need to prevent a slow read from holding a TX open?
  → NOT_SUPPORTED (reporting, cache warming)

Cross-service distributed atomicity?
  → @Transactional does NOT span service boundaries
  → Use Saga + Compensating Transactions + Transactional Outbox
```

---

## Interview Cheat Sheet

> "All propagation logic lives in AbstractPlatformTransactionManager.getTransaction(). It checks TransactionSynchronizationManager's ThreadLocal to determine if an active TX exists. REQUIRED simply joins the existing ConnectionHolder already bound to the thread — no new connection, no new TX. REQUIRES_NEW calls suspend(), which unbinds the outer ConnectionHolder and saves its state in a SuspendedResourcesHolder, then starts a fresh TX on a new connection — creating a true independent transaction; when the inner TX commits or rolls back, resume() re-binds the outer connection. NESTED uses JDBC setSavepoint() on the SAME connection — if the inner code throws and the outer catches it, only the inner portion is rolled back via rollback(savepoint); if the outer rolls back, the savepoint vanishes with it. The deadlock risk with REQUIRES_NEW is that the inner TX may try to access rows that the suspended outer TX still holds locks on — fix by passing all needed data as parameters rather than re-querying inside the inner TX."
