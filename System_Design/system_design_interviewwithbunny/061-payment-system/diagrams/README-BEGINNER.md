# Payment System (Stripe/Razorpay) — Beginner Study Guide

> **Complexity Level**: 🔴 HIGHEST  
> **Time Investment**: 7-10 days (this is NOT a CRUD app — it's a distributed financial system)  
> **Interview Frequency**: 🔥 Most asked after "design URL shortener"  
> **Real-World Examples**: Stripe, Razorpay, PayPal, Square, Braintree

---

## 🎯 What Makes Payment System Design UNIQUE?

**Payment system is the ONLY system design where correctness matters MORE than performance.**

- URL shortener down for 5 minutes? Users retry, life goes on.
- Payment system charges customer twice? **Legal liability, financial loss, regulatory violation.**

**The hard part is NOT performance** (MySQL handles 10K TPS easily). The hard part is:

1. **Exactly-once money movement** — network failures cause retries, retries must never double-charge
2. **ACID guarantees** — partial writes = money created from nothing or lost forever
3. **Immutable audit trail** — regulatory requirement (SOX, PCI-DSS), every transaction traceable
4. **Reconciliation** — your ledger vs bank statement, final safety net when all automation fails

**Interview focus**: 40% design, **60% proving you understand what happens when things fail.**

---

## 📂 Diagram Files in This Folder

| File | What It Shows | When to Use |
|------|---------------|-------------|
| **01-context-BEGINNER.drawio** | System boundary, actors (Client, Bank, Admin), external systems (Redis, Kafka, MySQL), key challenges (idempotency, double-entry, ACID) | First 5 minutes — explain scope |
| **02-architecture-components-BEGINNER.drawio** | High-level architecture (Client → Gateway → Services → Data), WHY boxes (MySQL ACID, Redis idempotency, Outbox pattern, Optimistic locking, Saga) | Core design — show components |
| **03-payment-flow-sequence-BEGINNER.drawio** | Complete payment flow: initiation → 202 Accepted → Outbox → Kafka → Bank API → SUCCESS update, plus failure scenarios (idempotency hit, timeout) | Deep dive — prove correctness |
| **04-data-model-BEGINNER.drawio** | MySQL schema (payments, accounts with version, ledger_entries append-only, outbox_events), Redis patterns (idempotency cache), Kafka topics, S3 reconciliation | Data modeling — show storage |

---

## 📅 5-7 Day Study Plan (Beginner-Friendly)

### **Day 1: Understand the Problem Space** (2-3 hours)
- **Read**: `01-context-BEGINNER.drawio` in Draw.io
- **Focus**: What is idempotency? Why double-entry bookkeeping? What is the outbox pattern?
- **Activity**: Draw the system boundary on paper — actors, external systems, key challenges
- **Self-Check**: Can you explain why `0.1 + 0.2 != 0.3` breaks payment systems?

### **Day 2: Study the Architecture** (3-4 hours)
- **Read**: `02-architecture-components-BEGINNER.drawio`
- **Focus**: Why MySQL (not Cassandra)? Why Redis for idempotency? Why outbox pattern (not direct Kafka)?
- **Activity**: For each WHY box, write in your own words why the alternative (e.g., direct Kafka publish) fails
- **Self-Check**: What happens if app crashes after MySQL COMMIT but before Kafka publish?

### **Day 3: Trace the Payment Flow** (4-5 hours)
- **Read**: `03-payment-flow-sequence-BEGINNER.drawio`
- **Focus**: Follow every arrow from Client → Bank API → SUCCESS update
- **Activity**: Trace the sequence diagram step-by-step, note when transactions BEGIN/COMMIT
- **Self-Check**: At what point does the client get 202 Accepted? When does bank actually charge?

### **Day 4: Master the Data Model** (3-4 hours)
- **Read**: `04-data-model-BEGINNER.drawio`
- **Focus**: MySQL schema (accounts.version for optimistic locking), ledger_entries append-only, outbox_events
- **Activity**: Write the SQL for a payment: INSERT payment, INSERT 2 ledger rows (DEBIT/CREDIT), INSERT outbox
- **Self-Check**: Why does `SUM(ledger_entries.amount)` MUST equal zero? What breaks if it doesn't?

### **Day 5: Interview Q&A Practice** (2-3 hours)
- **Read**: "Interview Q&A" section below
- **Focus**: Strong vs weak answers, what interviewers want to hear
- **Activity**: Record yourself answering 3 questions, listen back, improve
- **Self-Check**: Can you explain idempotency in < 30 seconds without jargon?

### **Day 6: Failure Scenarios Deep Dive** (3-4 hours)
- **Focus**: What happens when Redis down? MySQL crashes mid-transaction? Bank timeout?
- **Activity**: For each failure, trace what happens (rollback? retry? compensate?)
- **Self-Check**: If payment stuck in PROCESSING for 2 hours, how do you fix it?

### **Day 7: Whiteboard Practice** (2-3 hours)
- **Activity**: Set 20-minute timer, draw the full system on whiteboard without looking
- **Focus**: Can you go from requirements → architecture → sequence → data model in 20 min?
- **Self-Check**: Did you mention idempotency? ACID? Outbox? Reconciliation?

---

## 🔑 7 Key Concepts to Master

### 1. **Idempotency Key** (Prevents Double-Charge on Retry)
**Definition**: Client-generated UUID sent with every payment request. Server caches the result (Redis, 24hr TTL). Retry with same key → return cached response, no re-processing.

**Why it exists**: Network timeout causes client to retry. Without idempotency, retry = new payment = double-charge.

**Example**:
```http
POST /payments
Idempotency-Key: user_123_order_456_abc
{ "amount": 10000, "from": "alice", "to": "bob" }

First call: Creates payment_xyz, returns 202 Accepted
Retry (same key): Redis hit, returns cached {paymentId: payment_xyz, status: INITIATED}
→ Only ONE payment created, not two.
```

**Interview trap**: "Why not just check DB for duplicate payment_id?" → Payment ID is server-generated (UUID v4). Client doesn't know it before calling API. Idempotency key is CLIENT-generated, so client can retry with same key.

---

### 2. **ACID Transactions** (All-or-Nothing Writes)
**Definition**: MySQL transaction ensures atomicity — either ALL writes succeed or ALL fail. No partial writes.

**Why it exists**: Payment creation touches 3 tables: payments, ledger_entries, outbox_events. If only payments row written but ledger missing → money disappeared from source, never arrived at destination.

**Example**:
```sql
BEGIN;
  INSERT INTO payments (payment_id, status) VALUES ('pay_xyz', 'INITIATED');
  INSERT INTO ledger_entries (payment_id, account_id, amount, type) 
    VALUES ('pay_xyz', 'alice', -10000, 'DEBIT');
  INSERT INTO ledger_entries (payment_id, account_id, amount, type) 
    VALUES ('pay_xyz', 'bob', +10000, 'CREDIT');
  INSERT INTO outbox_events (payment_id, published) VALUES ('pay_xyz', false);
COMMIT; -- All 4 rows written atomically, or all rolled back on failure
```

**Interview trap**: "Why not use Cassandra?" → Cassandra eventual consistency = two concurrent debits both see sufficient balance, both succeed, overdraft. MySQL ACID prevents this.

---

### 3. **Double-Entry Bookkeeping** (Money Conservation Law)
**Definition**: Every payment creates TWO ledger entries: DEBIT source, CREDIT destination. Sum of all ledger entries = 0.

**Why it exists**: Self-checking mechanism. If sum != 0, money was created or destroyed by a bug. Regulatory requirement (SOX).

**Example**:
```
Payment: Alice pays Bob Rs.100 (10000 paise)

Ledger row 1: account_id=alice, amount=-10000, type=DEBIT   (money leaving)
Ledger row 2: account_id=bob,   amount=+10000, type=CREDIT  (money arriving)

SUM(amount) = -10000 + 10000 = 0 ✓
```

**Interview trap**: "Why store both DEBIT and CREDIT?" → Single-entry only tracks one side. Bug could debit Alice without crediting Bob → money vanishes, no audit trail to find where it went.

---

### 4. **Outbox Pattern** (Zero Event Loss Guarantee)
**Definition**: Write event to DB outbox table in SAME transaction as domain write. Separate relay process publishes to Kafka. Prevents event loss if app crashes.

**Why it exists**: Classic failure: app writes payment to DB → COMMIT → app crashes before Kafka publish → downstream services never notified.

**Flow**:
```
Payment Service:
  BEGIN TX;
    INSERT payments;
    INSERT outbox_events (published=false);  ← Same transaction!
  COMMIT;

Outbox Relay (separate process, polls every 100ms):
  SELECT * FROM outbox_events WHERE published=false;
  FOR EACH event:
    PUBLISH to Kafka;
    UPDATE outbox_events SET published=true;
```

**Interview trap**: "Why not just publish to Kafka directly?" → If app crashes between DB commit and Kafka publish, event silently lost. Outbox guarantees at-least-once delivery.

---

### 5. **Optimistic Locking** (Prevents Overdraft Race Condition)
**Definition**: Accounts table has `version` column (INT). UPDATE increments version, checks expected version. Concurrent debits → one wins, others get 0 rows updated → retry.

**Why it exists**: Alice has Rs.100. Two payments fire simultaneously, both debit Rs.100. Without locking, both see sufficient balance, both succeed → account at -Rs.100 (overdraft).

**Example**:
```sql
-- Alice balance=10000, version=5

Payment A:
  UPDATE accounts 
  SET balance=0, version=6 
  WHERE account_id=alice AND version=5 AND balance >= 10000;
  → 1 row updated (SUCCESS)

Payment B (concurrent):
  UPDATE accounts 
  SET balance=0, version=6 
  WHERE account_id=alice AND version=5 AND balance >= 10000;
  → 0 rows updated (another TX modified it, version != 5)
  → ROLLBACK, return insufficient funds error
```

**Interview trap**: "Why not use SELECT FOR UPDATE (pessimistic lock)?" → Holds row lock during bank API call (100ms-30s). Causes deadlocks at scale. Optimistic lock = no locks held, just version check.

---

### 6. **Saga Pattern** (Compensating Transactions for External APIs)
**Definition**: Chain of local transactions. On failure, execute compensating transaction (reverse the operation). Alternative to 2PC for distributed systems.

**Why it exists**: Bank APIs don't support 2PC PREPARE phase. Can't coordinate distributed transaction with external systems.

**Example**:
```
Cross-bank transfer (Alice at our system → Bob at external bank):

Step 1: Debit Alice (our DB) → COMMIT
Step 2: Call bank API to credit Bob → if SUCCESS:
          UPDATE payment status=SUCCESS
        if FAILED:
          Compensating transaction: Credit Alice (refund)
```

**Interview trap**: "Why not use 2PC?" → 2PC requires all participants support PREPARE/COMMIT phases. External bank APIs are black boxes, no PREPARE support. If bank times out in PREPARE, we hold locks forever.

---

### 7. **Reconciliation** (Final Safety Net)
**Definition**: Nightly job downloads bank statement CSV, compares each transaction to our ledger. Mismatch → alert ops, freeze account.

**Why it exists**: Catches bugs that slip through all other layers. Bank charged customer but our DB write failed. Or our system shows SUCCESS but bank rejected.

**Flow**:
```
Daily at 02:00 AM:
  1. Download yesterday's bank CSV from S3
  2. Parse each row → lookup payment_id in our DB
  3. Compare bank amount vs our ledger amount, bank status vs our status
  4. If mismatch:
       INSERT INTO reconciliation_discrepancies;
       Alert ops via Slack/PagerDuty;
       Freeze account if discrepancy > Rs.10,000;
```

**Interview trap**: "Why daily, not real-time?" → Real-time reconciliation = calling bank status API for every payment. Bank rate-limits API, charges per call. Daily balances cost vs risk.

---

## 💬 Interview Q&A (10 Must-Know Questions)

### Q1: Why store money as BIGINT (paise/cents) and not FLOAT/DECIMAL?

**❌ Weak answer**: "BIGINT is more efficient than DECIMAL."

**✅ Strong answer**:
> "Floating-point arithmetic has precision errors. In JavaScript: `0.1 + 0.2 = 0.30000000000000004`. In production, this means Rs.1000.00 + Rs.0.01 could be stored as Rs.1000.0099999999, which rounds unpredictably. Over millions of transactions, these errors accumulate into real money loss. 
>
> **Solution**: Store money as integer smallest unit — paise for INR, cents for USD. Rs.100.50 = 10050 paise (BIGINT). Division only at display layer: `10050 / 100 = Rs.100.50`. MySQL schema: `amount BIGINT NOT NULL`. API response converts paise → rupees with 2 decimals.
>
> This is what Stripe, Razorpay, PayPal all do. Non-negotiable for financial systems."

---

### Q2: How do you prevent double-charging when client retries after timeout?

**❌ Weak answer**: "Check if payment_id already exists in DB."

**✅ Strong answer**:
> "Payment ID is server-generated UUID — client doesn't know it before the API call. So client can't check for duplicates by payment_id.
>
> **Solution: Idempotency key**. Client generates a UUID per payment attempt and sends it as a header: `Idempotency-Key: uuid_abc123`. Before processing, we check Redis: `GET idempotency:uuid_abc123`. If HIT → return cached response (same payment_id, no re-processing). If MISS → create payment, cache response with 24hr TTL.
>
> **Example scenario**: Client taps Pay, network times out after 2 sec. Client taps again. First tap created payment_xyz. Second tap: Redis hit, return {paymentId: payment_xyz, status: INITIATED}. Client sees same payment twice, only one charge to bank.
>
> **Why 24hr TTL?** Covers all reasonable retry windows. After 24hr, idempotency key expires. New order should use new UUID anyway."

---

### Q3: What happens if app crashes after MySQL COMMIT but before Kafka publish?

**❌ Weak answer**: "The payment is saved in DB but downstream services are never notified."

**✅ Strong answer**:
> "This is the classic event-loss scenario that the **Outbox pattern** solves.
>
> **Outbox pattern flow**:
> 1. Payment Service writes payment AND outbox event in SAME MySQL transaction:
>    ```sql
>    BEGIN;
>      INSERT INTO payments (status='INITIATED');
>      INSERT INTO outbox_events (payment_id, published=false);
>    COMMIT;
>    ```
> 2. Separate Outbox Relay process (polls every 100ms):
>    ```sql
>    SELECT * FROM outbox_events WHERE published=false;
>    FOR EACH event:
>      PUBLISH to Kafka;
>      UPDATE outbox_events SET published=true;
>    ```
>
> **If app crashes after COMMIT**: Outbox relay picks up the unpublished event on next poll (within 100ms). Event delivery guaranteed, even if app crashes.
>
> **Without outbox**: Direct Kafka publish after COMMIT → if app crashes between COMMIT and publish, event silently lost. Fraud detection, email notification, settlement — all downstream services never triggered. No error, just silent data loss."

---

### Q4: How do you handle race condition — two concurrent debits from same account with low balance?

**❌ Weak answer**: "Use SELECT FOR UPDATE to lock the row."

**✅ Strong answer**:
> "Pessimistic locking (SELECT FOR UPDATE) holds a row lock for the entire payment duration — including the bank API call, which takes 100ms-30sec. This causes deadlocks and lock timeouts at scale.
>
> **Better solution: Optimistic locking**. Accounts table has `version` column (INT). Every balance update increments version and checks expected version:
> ```sql
> UPDATE accounts 
> SET balance = balance - 10000, version = version + 1
> WHERE account_id = 123 
>   AND version = 10 
>   AND balance >= 10000;
> ```
>
> **If 0 rows updated** → another transaction modified the row (version changed). Current transaction ROLLBACK, return insufficient funds or retry.
>
> **Scenario**: Alice balance=Rs.100, version=10. Two payments fire simultaneously (both debit Rs.100):
> - Payment A: WHERE version=10 → 1 row updated (SUCCESS, version now 11)
> - Payment B: WHERE version=10 → 0 rows updated (version already 11, FAIL)
>
> **No locks held** during bank API call. Just a version check at write time. This is what Stripe uses."

---

### Q5: Why use Saga pattern instead of 2PC for cross-bank transfers?

**❌ Weak answer**: "Saga is more scalable than 2PC."

**✅ Strong answer**:
> "Two-phase commit (2PC) requires all participants to support PREPARE and COMMIT phases. External bank APIs don't support this — they either execute the charge immediately or they don't. There's no 'prepare to charge but don't commit yet' mode.
>
> **2PC problem with external APIs**: If bank times out during PREPARE phase, we hold locks on our side indefinitely waiting for bank to respond. Our system deadlocks.
>
> **Saga pattern**: Chain of local transactions with compensating steps on failure:
> 1. **Step 1**: Debit Alice (our system) → local ACID transaction → COMMIT
> 2. **Step 2**: Call bank API to credit Bob → if SUCCESS: UPDATE payment status=SUCCESS
> 3. **Step 3**: If bank fails: Compensating transaction = refund Alice (reverse the debit)
>
> **Trade-off**: Saga provides eventual consistency, not immediate consistency. Between Step 1 and Step 2, money is temporarily 'in flight' (debited but not yet credited). This is acceptable because:
> - Most payments complete in 1-30 sec
> - Daily reconciliation is final safety net
> - Banks operate on eventual consistency too (ACH, SWIFT are all async)
>
> **Real-world**: Stripe, Razorpay all use Saga for cross-bank transfers. 2PC only works within systems you control."

---

### Q6: What is double-entry bookkeeping and why is it required for payment systems?

**❌ Weak answer**: "It's an accounting practice to track debits and credits."

**✅ Strong answer**:
> "Every payment creates TWO ledger entries: DEBIT source account, CREDIT destination account. The ledger is append-only — never UPDATE or DELETE.
>
> **Example**: Alice pays Bob Rs.100 (10000 paise):
> - Ledger row 1: account_id=alice, amount=-10000, type=DEBIT
> - Ledger row 2: account_id=bob, amount=+10000, type=CREDIT
> - SUM(amount) = -10000 + 10000 = 0
>
> **Why this matters**:
> 1. **Self-checking**: SUM of all ledger entries MUST equal zero. If not, money was created or destroyed by a bug.
> 2. **Immutable audit trail**: Regulators (SOX, PCI-DSS) require proof that every transaction is traceable and unmodified. Ledger provides this.
> 3. **Balance reconciliation**: `accounts.balance` is a materialized view (fast reads). If it diverges from ledger (bug), we trust the ledger: `SUM(ledger_entries.amount WHERE account_id=X)` is source of truth.
>
> **Interview insight**: Accounts table balance is a denormalized cache for performance. Ledger is the truth. This is a classic trade-off: read performance vs write complexity."

---

### Q7: How does reconciliation work and why is it necessary despite all the safety mechanisms?

**❌ Weak answer**: "Compare our database to the bank's records."

**✅ Strong answer**:
> "Reconciliation is the **final safety net** that catches what all automated layers missed.
>
> **Process** (nightly at 02:00 AM):
> 1. Download yesterday's bank statement CSV from S3
> 2. Parse each row (txn_id, amount, status, timestamp)
> 3. Lookup our payment by bank reference ID
> 4. Compare:
>    - Bank amount vs our ledger amount
>    - Bank status vs our payment status
>    - Bank timestamp vs our created_at
> 5. If mismatch:
>    - INSERT into reconciliation_discrepancies table
>    - Alert ops via Slack/PagerDuty
>    - Freeze account if discrepancy > Rs.10,000
>
> **Scenarios reconciliation catches**:
> - Bank charged customer but our DB write failed → customer charged, no record in our system
> - Our system shows SUCCESS but bank rejected → we credited merchant, bank didn't debit customer
> - Network split: ledger DEBIT exists, CREDIT missing → money creation bug
> - Manual ops error: someone did direct DB UPDATE (bypassed code validation)
>
> **Why necessary despite idempotency/outbox/ACID?** Because bugs exist. A subtle race condition in version 1.2.3 that only triggers under load. A bank API that returns SUCCESS but actually failed silently. Reconciliation is insurance — we verify the bank's official statement (source of truth for money movement) matches our records.
>
> **Why nightly, not real-time?** Real-time = calling bank status API per payment. Banks rate-limit, charge per call. Nightly balances cost vs detection speed. Most discrepancies are caught within 24hr, which is acceptable for regulatory purposes."

---

### Q8: Walk me through the payment flow from client request to bank confirmation.

**❌ Weak answer**: "Client sends request, we save to DB, call bank, return response."

**✅ Strong answer** (follow the sequence diagram):
> "**Phase 1: Payment Initiation (0-100ms)**
> 1. Client: `POST /payments` with idempotencyKey (client-generated UUID)
> 2. API Gateway → Redis: `GET idempotency:uuid_abc` → MISS (first time)
> 3. Payment Service → MySQL BEGIN TX:
>    - INSERT payments (status=INITIATED)
>    - INSERT outbox_events (published=false)
>    - COMMIT ✓
> 4. Payment Service → Redis: SET idempotency:uuid_abc = {paymentId, status} TTL 24hr
> 5. **Client gets 202 Accepted** with paymentId (payment NOT yet confirmed by bank)
>
> **Phase 2: Outbox → Kafka (async, after client response)**
> 6. Outbox Relay (polls every 100ms): SELECT unpublished events
> 7. Publish to Kafka topic `payment.commands`
> 8. Mark outbox published=true
>
> **Phase 3: Payment Processor → Bank API (1-30 sec)**
> 9. Processor consumes Kafka event → UPDATE payment status=PROCESSING
> 10. Check balance (optimistic lock): SELECT balance, version WHERE account_id=alice
> 11. Call bank API: `POST /charge` → [3 sec latency] → Bank returns SUCCESS
> 12. MySQL BEGIN TX:
>     - UPDATE payment status=SUCCESS, bank_ref=HDFC_XYZ
>     - UPDATE accounts balance=balance-10000, version=version+1 WHERE version=expected
>     - UPDATE accounts balance=balance+10000 (destination)
>     - INSERT ledger_entries (DEBIT alice -10000)
>     - INSERT ledger_entries (CREDIT bob +10000)
>     - COMMIT ✓
>
> **Phase 4: Notification**
> 13. Kafka: Publish payment.success
> 14. Notification Service consumes → Send email/SMS: 'Payment Rs.100 SUCCESS'
>
> **Key insights**:
> - Client gets 202 in <100ms, bank confirmation takes 1-30s (async)
> - Idempotency prevents double-charge if client retries
> - Outbox guarantees event delivery even if app crashes
> - Optimistic lock prevents overdraft race condition
> - Double-entry ledger: DEBIT + CREDIT sum to zero"

---

### Q9: How do you scale the payment system to 100K TPS (PayPal scale)?

**❌ Weak answer**: "Add more servers and load balancers."

**✅ Strong answer**:
> "**Bottleneck 1: MySQL writes serialize through single primary.**
>
> At 100 TPS, single MySQL primary handles it easily (10K TPS capacity). At 100K TPS (PayPal scale), we need horizontal scaling.
>
> **Solution: Shard MySQL by account_id**. 16 shards, each handles ~6K TPS:
> - Hash: `account_id % 16` → shard ID
> - All of one user's data on same shard (payments, accounts, ledger)
> - **Same-shard payment**: Local ACID transaction (fast, no distributed coordination)
> - **Cross-shard payment** (Alice shard 1 → Bob shard 2):
>   - Saga pattern: Debit shard 1 → Credit shard 2 → if failed, compensate
>   - Alternative: 2PC within our system (we control both shards)
>   - Cross-shard < 5% of total (most P2P within same country/PSP)
>
> **Bottleneck 2: Bank API calls block threads.**
>
> Bank API latency: 100ms-30s. If processor holds thread per payment:
> - At 100K TPS, need 100K concurrent threads just waiting on I/O → unsustainable
>
> **Solution: Non-blocking I/O** (Java WebClient/Netty, Node.js native async):
> - Send bank request, release thread, callback fires on response
> - 10 threads with async I/O handle 10K+ concurrent bank calls
> - Timeout: 30 sec. On timeout → UPDATE status=PENDING → retry with exponential backoff
>
> **Bottleneck 3: Redis idempotency cache single-instance.**
>
> At 100K TPS, single Redis instance saturates (CPU-bound on GET).
>
> **Solution: Redis Cluster** (6 nodes, sharded by idempotency key hash):
> - Each node handles 16K TPS (100K / 6)
> - Replication: 3 replicas per node for HA
>
> **Numbers**:
> - MySQL: 16 shards × 6K TPS = 96K TPS capacity
> - Redis: 6 nodes × 16K TPS = 96K TPS capacity
> - Payment Processor: 100 instances × 1K TPS = 100K TPS capacity
> - Bank API: Async I/O, no thread blocking, scales horizontally
>
> **Real-world**: Stripe uses MySQL sharding + async I/O. PayPal uses similar architecture (Oracle instead of MySQL, but same sharding principles)."

---

### Q10: What are the failure scenarios and how does the system recover?

**❌ Weak answer**: "We retry on failure and log errors."

**✅ Strong answer**:
> "**Failure 1: Client network timeout after request sent**
> - Client retries with same idempotency key
> - Redis GET → HIT (payment already created)
> - Return cached response {paymentId, status}
> - **Result**: Client sees same payment twice, only one charge
>
> **Failure 2: App crashes after MySQL COMMIT, before Kafka publish**
> - Outbox event written to DB (same TX as payment)
> - Outbox relay picks up unpublished event on next poll (within 100ms)
> - Publishes to Kafka, marks published=true
> - **Result**: Zero event loss, guaranteed at-least-once delivery
>
> **Failure 3: Bank API timeout (no response after 30 sec)**
> - Processor: UPDATE payment status=PENDING
> - Schedule retry with exponential backoff: 30s, 1min, 2min, 4min, ...
> - Poll bank status API: `GET /charge/{paymentId}` → eventually returns SUCCESS/FAILED
> - **Result**: Payment eventually settles, customer not charged twice (bank idempotency)
>
> **Failure 4: Bank returns SUCCESS but our DB update fails**
> - Kafka at-least-once delivery → processor re-consumes event on restart
> - Check payment current status: if already SUCCESS (idempotent check) → skip
> - If still PROCESSING → re-attempt status update (retry)
> - **Result**: Eventually consistent, bank charge recorded
>
> **Failure 5: Two concurrent debits, insufficient balance**
> - Optimistic locking: first UPDATE wins (version increments)
> - Second UPDATE: WHERE version=old → 0 rows updated
> - Second payment ROLLBACK, return insufficient funds
> - **Result**: No overdraft, one payment succeeds, one rejected
>
> **Failure 6: Ledger sum != 0 (money creation bug)**
> - Daily batch job: `SELECT SUM(amount) FROM ledger_entries` → expected: 0
> - If != 0: Alert ops, freeze all accounts, investigate
> - Trace ledger history to find which payment missing DEBIT or CREDIT
> - **Result**: Caught within 24hr, financial integrity preserved
>
> **Failure 7: Our ledger vs bank statement mismatch**
> - Reconciliation (nightly): Compare bank CSV to our ledger
> - Bank charged Rs.100 but our ledger shows Rs.0 → discrepancy found
> - Alert ops, freeze account, manual investigation
> - **Result**: Final safety net, catches silent bank errors or our bugs"

---

## 🧪 Self-Check Questions (Test Your Understanding)

### **Architecture Questions**
1. Why must payment amounts be stored as BIGINT (not FLOAT)?
2. What happens if you use Cassandra instead of MySQL for payments?
3. Why is idempotency key client-generated (not server-generated)?
4. Explain the outbox pattern in 3 sentences.
5. What is the difference between optimistic locking and pessimistic locking?

### **Flow Questions**
6. At what point does the client receive 202 Accepted?
7. When does the bank actually charge the customer's account?
8. What happens if the bank API call times out after 30 seconds?
9. How does the system prevent double-charge if client retries?
10. Walk through the MySQL transaction for a successful payment (include ledger entries).

### **Failure Scenarios**
11. App crashes after MySQL COMMIT but before Kafka publish — what happens?
12. Two concurrent debits from same account with Rs.100 balance, each for Rs.100 — what happens?
13. Bank returns SUCCESS but our DB is down — how does system recover?
14. Payment stuck in PROCESSING status for 2 hours — how do you debug?
15. Reconciliation finds mismatch: bank charged Rs.100 but our ledger shows Rs.0 — what do you do?

### **Scaling Questions**
16. What is the bottleneck at 100K TPS and how do you solve it?
17. How do you handle cross-shard payments (Alice shard 1 → Bob shard 2)?
18. Why use async I/O for bank API calls instead of blocking threads?
19. How many Redis instances needed for 100K TPS idempotency checks?
20. When should you use 2PC vs Saga pattern?

---

## 📊 Key Numbers to Memorize for Interview

| Metric | Value | Why Important |
|--------|-------|---------------|
| Idempotency key TTL | **24 hours** | Covers all retry windows |
| Client API response time | **<100ms** | Returns 202 Accepted (before bank confirmation) |
| Bank API latency | **100ms-30sec** | Never hold DB lock during this |
| Outbox relay poll interval | **100ms** | Near-real-time event delivery |
| Optimistic lock collision rate | **<0.1%** | Rare, most payments non-concurrent |
| Kafka retention | **7 days** | Replay capability for debugging |
| MySQL shard count (at scale) | **16 shards** | 160K TPS total (10K TPS per shard) |
| Cross-shard payment % | **<5%** | Most P2P within same shard |
| Reconciliation frequency | **Nightly 02:00 AM** | Balance cost vs detection lag |
| Ledger sum invariant | **SUM(amount) = 0** | Double-entry bookkeeping guarantee |
| S3 statement retention | **7 years** | Regulatory requirement (SOX) |
| Rate limit per user | **10 payments/min** | Prevent abuse/fraud |
| Payment state transitions | **INITIATED → PROCESSING → SUCCESS/FAILED** | Enforced by state machine |
| MySQL TPS per shard | **~10K TPS** | Single MySQL primary capacity |
| Redis GET latency | **<1ms** | Idempotency check overhead |

---

## 🎨 20-Minute Whiteboard Interview Template

### **Minute 0-2: Requirements Gathering**
"Let me clarify the requirements:
- Payment gateway or wallet system? → **Both** (accept cards + P2P transfers)
- Volume? → **1M txn/day (~100 TPS peak)**
- Latency? → **API <500ms, bank settlement async**
- Consistency? → **Strong ACID, no eventual**
- Refunds? → **Yes**
- Fraud detection? → **Yes, but async**"

### **Minute 2-4: Core Entities**
"Four main entities:
1. **payments** (payment_id, idempotency_key UNIQUE, amount BIGINT, status ENUM)
2. **accounts** (account_id, balance BIGINT, version INT for optimistic locking)
3. **ledger_entries** (append-only, DEBIT/CREDIT, SUM=0 invariant)
4. **outbox_events** (published BOOLEAN, for Kafka relay)"

### **Minute 4-8: High-Level Architecture** (Draw boxes and arrows)
"Client → API Gateway (TLS, JWT, rate limit) → Payment Service → MySQL (ACID) + Outbox → Kafka → Payment Processor → Bank API → Update MySQL success/failed → Notification Service.

**Key design decisions**:
- **MySQL ACID** (not Cassandra) — atomicity non-negotiable for money
- **Redis idempotency cache** — prevent double-charge on retry
- **Outbox pattern** — zero event loss guarantee
- **Optimistic locking** — prevent overdraft race condition
- **Saga for external banks** — compensating transactions on failure"

### **Minute 8-12: Payment Flow Sequence**
"Phase 1 (0-100ms): Client POST → Redis idempotency check (MISS) → MySQL BEGIN TX (INSERT payment + outbox) → COMMIT → Redis cache result → **202 Accepted to client**.

Phase 2 (async): Outbox relay polls → Kafka publish → mark published=true.

Phase 3 (1-30s): Processor consumes Kafka → UPDATE status=PROCESSING → call bank API → on SUCCESS: MySQL BEGIN TX (UPDATE payment + UPDATE balances + INSERT ledger DEBIT/CREDIT) → COMMIT."

### **Minute 12-15: Failure Scenarios**
"**Retry**: Client retries → Redis HIT → return cached response.

**App crash**: Outbox relay picks up unpublished event within 100ms.

**Bank timeout**: UPDATE status=PENDING → retry with exponential backoff → poll bank status API.

**Race condition**: Optimistic locking — first debit wins, second gets 0 rows updated → insufficient funds.

**Reconciliation**: Nightly compare bank CSV vs our ledger → alert on mismatch."

### **Minute 15-18: Data Model Deep Dive**
"**payments table**: idempotency_key UNIQUE constraint prevents duplicate processing at DB layer.

**accounts table**: version INT for optimistic locking. UPDATE SET balance=balance-X, version=version+1 WHERE version=expected.

**ledger_entries**: Append-only. Every payment = 2 rows (DEBIT source, CREDIT dest). SUM(amount) MUST = 0. Regulatory audit trail.

**outbox_events**: Same TX as payment. Relay publishes to Kafka. Prevents event loss."

### **Minute 18-20: Scaling**
"At 100K TPS:
- **Shard MySQL** by account_id (16 shards, 6K TPS each)
- **Cross-shard payments**: Saga pattern (debit shard 1 → credit shard 2 → compensate on failure)
- **Non-blocking I/O**: Async bank API calls (10 threads handle 10K concurrent calls)
- **Redis Cluster**: 6 nodes, sharded by idempotency key hash

Monitoring: TPS, success rate, optimistic lock collision rate, outbox lag, reconciliation mismatch count."

---

## ⚠️ 10 Common Mistakes to Avoid

### 1. **Using FLOAT/DECIMAL for money**
❌ `amount DECIMAL(10,2)` → precision errors accumulate  
✅ `amount BIGINT` (store paise/cents), divide by 100 at display layer

### 2. **Server-generated idempotency key**
❌ Server generates UUID, client can't retry with same key  
✅ Client generates UUID, sends as `Idempotency-Key: uuid_abc`

### 3. **Updating ledger_entries rows**
❌ `UPDATE ledger_entries SET amount=X` → audit trail corrupted  
✅ Ledger is append-only. Correction = new entry (reversal)

### 4. **Direct Kafka publish (no outbox)**
❌ App crashes between DB commit and Kafka publish → event lost  
✅ Outbox pattern: write event to DB in same TX, relay publishes

### 5. **Pessimistic locking for balance updates**
❌ `SELECT FOR UPDATE` holds lock during bank API call (100ms-30s) → deadlocks  
✅ Optimistic locking: version column, no locks held during external call

### 6. **Using 2PC with external bank APIs**
❌ Bank APIs don't support PREPARE phase → 2PC deadlocks  
✅ Saga pattern: local transactions + compensating steps

### 7. **Not checking idempotency on retry**
❌ Every retry creates new payment → double-charge  
✅ Redis GET idempotency key → if HIT, return cached response

### 8. **Single-entry bookkeeping**
❌ Only record DEBIT, no CREDIT → no way to verify money conservation  
✅ Double-entry: DEBIT source + CREDIT dest, SUM = 0

### 9. **Eventual consistency for account balance**
❌ Cassandra stale reads → two debits both see sufficient balance → overdraft  
✅ MySQL ACID + optimistic locking → strong consistency

### 10. **No reconciliation**
❌ Trust that all automated layers work perfectly → bugs go undetected  
✅ Nightly reconciliation: bank statement vs ledger, alert on mismatch

---

## ✅ Interview Sign-Off Checklist

Before you say "I'm done with my design", ensure you covered:

- [ ] **Idempotency key** — client-generated UUID, Redis cache, 24hr TTL, prevents double-charge
- [ ] **ACID transactions** — MySQL BEGIN/COMMIT, atomicity for payment + ledger + outbox
- [ ] **Double-entry ledger** — every payment = DEBIT + CREDIT, SUM = 0, append-only
- [ ] **Outbox pattern** — write event to DB in same TX, relay publishes to Kafka, zero event loss
- [ ] **Optimistic locking** — accounts.version, no locks held during bank call, prevents overdraft
- [ ] **Saga pattern** — compensating transactions for external bank APIs (not 2PC)
- [ ] **Reconciliation** — nightly bank statement vs ledger, final safety net
- [ ] **202 Accepted** — client gets response <100ms, bank settlement is async (1-30s)
- [ ] **BIGINT for money** — store paise/cents, never FLOAT (precision errors)
- [ ] **State machine** — INITIATED → PROCESSING → SUCCESS/FAILED, invalid transitions rejected
- [ ] **Failure scenarios** — retry, timeout, crash, race condition, and how system recovers
- [ ] **Scaling** — shard MySQL by account_id, async I/O for bank calls, Redis cluster
- [ ] **Monitoring** — TPS, success rate, optimistic lock collisions, outbox lag, reconciliation mismatches
- [ ] **Real-world examples** — "This is what Stripe/Razorpay does" (shows you've researched)

---

## 🚀 Next Steps After Mastering This

1. **Read Stripe API docs**: [https://stripe.com/docs/api](https://stripe.com/docs/api) — see idempotency keys, webhooks, refunds in production
2. **Study PCI-DSS compliance**: Understand why payment systems NEVER store raw card numbers (tokenization)
3. **Read "Designing Data-Intensive Applications"** by Martin Kleppmann — Chapter 9 (Consistency and Consensus) is gold for payment systems
4. **Build a mini payment system**: Just payment creation + idempotency + MySQL + basic reconciliation. Prove to yourself you understand.
5. **Compare with other financial systems**: Stock trading (similar correctness requirements), banking core systems

---

## 📚 Additional Resources

- **Stripe Engineering Blog**: [https://stripe.com/blog/engineering](https://stripe.com/blog/engineering) — real-world payment challenges
- **Martin Fowler: Patterns of Enterprise Application Architecture** — Money pattern, Unit of Work pattern
- **DDIA Chapter 9**: Linearizability, consensus algorithms for distributed transactions
- **ACM Queue: "The Trouble with Timestamps"** — why wall-clock time is unreliable in distributed systems
- **Jepsen.io**: Distributed systems testing (shows how even "ACID" databases can fail under network partitions)

---

## 🎓 Final Advice

**Payment system design is 40% architecture, 60% proving correctness.**

Don't just draw boxes and arrows. Interviewers will ask: "What happens if...?"

- Redis goes down?
- MySQL crashes mid-transaction?
- Bank API returns SUCCESS but you never get the response?
- Two payments fire simultaneously from same account with low balance?

**Strong candidates walk through failure scenarios confidently. Weak candidates freeze.**

**Study this guide, trace the sequence diagrams, understand every WHY box. You'll ace the interview.**

Good luck! 🚀

---

**Last Updated**: January 2025  
**Difficulty**: 🔴 Advanced (requires understanding of distributed transactions, consistency models, financial domain)  
**Estimated Study Time**: 7-10 days for beginners, 3-5 days if you have distributed systems background
