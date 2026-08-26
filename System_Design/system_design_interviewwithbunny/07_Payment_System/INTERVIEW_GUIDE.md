# Payment System (Stripe / Razorpay) — Interview Script
## Design Real Examples: Stripe, Razorpay, Braintree, Square
### Speak This Word-for-Word to Your Interviewer

> How to use this: Read PAGE 1 and PAGE 2 tonight — understand the consistency model cold.
> This system is unique: the interview is 40% design, 60% proving you understand failure modes.
> Every follow-up question will be about what happens when something goes wrong.

# ═══════════════ PAGE 1 — START HERE ═══════════════

## BIG PICTURE (Understand This Before Anything Else)

> **► STUDY this diagram, don't draw it ◄**
> A payment system is not a CRUD app. It is a distributed state machine enforcing exactly-once
> execution of money movement across systems you do not fully control. The hardest problems are
> NOT performance — they are correctness under failure: partial writes, network timeouts, and
> retries that must never result in a double charge.

```
  PAYMENT INITIATION                      ASYNC BANK COMMUNICATION
  ──────────────────                      ────────────────────────

  Client (Mobile/Web)
    │
    │ POST /payments { idempotencyKey, amount, from, to }
    ▼
  ┌───────────────────────────────────────────────────────┐
  │                   API Gateway                         │
  │        (TLS, Auth, Rate Limiting)                     │
  └────────────────────────┬──────────────────────────────┘
                           │
                           ▼
  ┌───────────────────────────────────────────────────────┐
  │              Payment Service                          │
  │                                                       │
  │  1. Check idempotencyKey in Redis → if exists,        │
  │     return cached response (NO re-processing)         │
  │                                                       │
  │  2. BEGIN MySQL transaction:                          │
  │     a. INSERT payment (status=INITIATED)              │
  │     b. INSERT outbox_event (unpublished)              │
  │     COMMIT                                            │
  │                                                       │
  │  3. Return 202 Accepted to client                     │
  └────────────────────────┬──────────────────────────────┘
                           │
                           │ Outbox Relay (separate process)
                           ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                        Kafka                                                │
  │                   Topic: payment.commands                                   │
  └────────────────────────────────────────────┬────────────────────────────────┘
                                               │
                           ┌───────────────────┘
                           │
                           ▼
  ┌───────────────────────────────────────────────────────┐
  │            Payment Processor Service                  │
  │                                                       │
  │  1. UPDATE payment status → PROCESSING               │
  │  2. Call bank/card-network API (100ms–3000ms)         │
  │  3. On success: UPDATE → SUCCESS                      │
  │     INSERT ledger_entries (debit + credit)            │
  │  4. On failure: UPDATE → FAILED                       │
  │  5. On timeout: UPDATE → TIMEOUT, schedule retry     │
  └────────────────────────┬──────────────────────────────┘
                           │
                           ▼
  ┌─────────────────────────────────────┐   ┌──────────────────────────────────┐
  │       MySQL (ACID)                  │   │   Double-Entry Ledger            │
  │                                     │   │                                  │
  │  payments table       (state)       │   │  ledger_entries (append-only)    │
  │  accounts table       (balance)     │   │  DEBIT: source account  -$100    │
  │  ledger_entries table (audit)       │   │  CREDIT: dest account   +$100    │
  │  outbox_events table  (relay)       │   │  Sum always = 0.                 │
  └─────────────────────────────────────┘   └──────────────────────────────────┘
                           │
                           │ Compensating transaction on failure
                           ▼
  ┌───────────────────────────────────────────────────────┐
  │          Reconciliation Service (nightly)             │
  │  Compare our ledger vs bank statement CSV             │
  │  Any mismatch → alert ops, freeze account             │
  └───────────────────────────────────────────────────────┘
```

---

## RAPID ANSWER — If You Only Have 5 Minutes

*Read this first. Understand the whole answer before going deep.*

```
"I'd design a payment system with five pieces:

1. Idempotency Layer: Every API call carries a client-generated idempotencyKey.
   Before processing, we check Redis for this key. If it exists, we return the
   cached response immediately — no re-charge, no matter how many retries the
   client sends. This is the single most important correctness guarantee.

2. ACID Database (MySQL): All financial data — payments, accounts, ledger entries —
   live in MySQL. ACID is non-negotiable for money. No Cassandra, no MongoDB,
   no eventual consistency. Every payment flows through a single MySQL transaction.

3. Double-Entry Bookkeeping: Every payment creates two ledger entries: a DEBIT on
   the source account and a CREDIT on the destination. The ledger is append-only —
   never UPDATE a ledger row. This creates an immutable audit trail where the sum
   of all entries is always zero. Auditors love this.

4. Outbox Pattern for Kafka: We write the payment record AND the Kafka event in
   the SAME MySQL transaction. A separate relay process reads unpublished outbox
   events and publishes to Kafka. This prevents the scenario where the DB write
   succeeds but the Kafka message is lost.

5. Saga Pattern for External Banks: We never use 2PC across external bank APIs.
   Instead: write PROCESSING, call bank async, on success write SUCCESS, on failure
   write a compensating transaction (refund). Daily reconciliation is the final
   safety net — our ledger vs bank statement, any mismatch triggers an alert."
```

---

# ═══════════════ PAGE 2 — GLOSSARY ═══════════════

## Terminology — Know These Before Reading Further

```
┌───────────────────────────────┬──────────────────────────────────────────────────────────┐
│ Term                          │ What It Means (Simply)                                   │
├───────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Idempotency                   │ Running the same operation multiple times produces the   │
│                               │ same result as running it once. Critical for safe retries.│
├───────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Idempotency Key               │ A unique UUID the client generates per payment attempt.  │
│                               │ Server uses this to detect and suppress duplicate requests│
├───────────────────────────────┼──────────────────────────────────────────────────────────┤
│ ACID                          │ Atomicity, Consistency, Isolation, Durability. MySQL      │
│                               │ guarantees that a transaction either fully commits or     │
│                               │ fully rolls back — no partial writes to DB.               │
├───────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Double-Entry Bookkeeping      │ Every financial event records both the source (debit) and │
│                               │ destination (credit). Sum of all entries = 0 always.      │
├───────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Ledger                        │ Append-only record of all financial events. Never updated.│
│                               │ Current balance = sum of all entries for an account.     │
├───────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Optimistic Locking            │ Read a version number, write only if version unchanged.  │
│                               │ Prevents two concurrent debits from both succeeding on a  │
│                               │ low-balance account without using row-level locks.        │
├───────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Pessimistic Locking           │ SELECT FOR UPDATE — locks the row until transaction ends. │
│                               │ Simple but causes deadlocks at scale. Avoid for payments. │
├───────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Two-Phase Commit (2PC)        │ Distributed transaction protocol: PREPARE phase, then     │
│                               │ COMMIT phase. Works within one system. NEVER use across  │
│                               │ external bank APIs you don't control.                    │
├───────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Saga Pattern                  │ Chain of local transactions with compensating steps on   │
│                               │ failure. Alternative to 2PC for distributed transactions.│
├───────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Outbox Pattern                │ Write event to a DB table (outbox) in the same transaction│
│                               │ as your domain write. Separate relay publishes to Kafka. │
│                               │ Prevents event loss if app crashes after DB write.        │
├───────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Compensating Transaction      │ A reverse operation that undoes a prior transaction.     │
│                               │ e.g., if bank credit fails, debit the source again.      │
├───────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Reconciliation                │ Comparing your internal ledger to the bank's statement.  │
│                               │ Finds discrepancies that slipped through all other checks.│
├───────────────────────────────┼──────────────────────────────────────────────────────────┤
│ State Machine                 │ Payment moves through defined states (INITIATED →         │
│                               │ PROCESSING → SUCCESS/FAILED). Only allowed transitions   │
│                               │ are permitted. Invalid transitions are rejected by DB.    │
├───────────────────────────────┼──────────────────────────────────────────────────────────┤
│ BIGINT (for money)            │ Store money as integer cents/paise. NEVER float.         │
│                               │ 0.1 + 0.2 = 0.30000000000000004 in floating point.       │
├───────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Immutable Audit Trail         │ Financial records are never deleted or updated. Every     │
│                               │ correction is a new entry. Regulatory requirement.        │
├───────────────────────────────┼──────────────────────────────────────────────────────────┤
│ Sharding (by account_id)      │ Split MySQL data across servers. Shard by account_id so  │
│                               │ all of one user's data is on one shard (local transactions)│
└───────────────────────────────┴──────────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 3 — WHY EACH COMPONENT ═══════════════

## Component Choices — Why We Picked Each One

```
┌──────────────────────────┬───────────────────────────────────────────────────────────────┐
│ COMPONENT                │ WHY THIS? NOT SOMETHING ELSE?                                 │
├──────────────────────────┼───────────────────────────────────────────────────────────────┤
│ MySQL for all            │ WHY: ACID transactions guarantee atomicity — a payment debit  │
│ financial data           │ and ledger insert either both commit or both roll back.        │
│                          │ Strong consistency is required: a customer seeing a stale      │
│                          │ balance and making a payment that overdrafts is catastrophic. │
│                          │ MySQL's row-level locking with MVCC handles concurrent         │
│                          │ payments without data corruption.                             │
│                          │ WHY NOT Cassandra/MongoDB: Cassandra offers only eventual      │
│                          │ consistency. Two concurrent reads of the same balance could    │
│                          │ both see sufficient funds, leading to double-spend. MongoDB's  │
│                          │ multi-document transactions are weaker than MySQL ACID and      │
│                          │ add operational complexity for no financial use case benefit.  │
├──────────────────────────┼───────────────────────────────────────────────────────────────┤
│ Redis for idempotency    │ WHY: O(1) key lookup with TTL. Before any payment processing,  │
│ key storage              │ check Redis for idempotencyKey. If present → return cached     │
│                          │ response without touching DB. TTL of 24 hours covers all       │
│                          │ reasonable retry windows. Sub-millisecond check adds no        │
│                          │ perceptible latency.                                           │
│                          │ WHY NOT MySQL: A DB query for idempotency check on every        │
│                          │ request adds 5-10ms latency and creates a high-read table that │
│                          │ competes with transactional writes. Redis is purpose-built for  │
│                          │ this ephemeral caching use case.                               │
├──────────────────────────┼───────────────────────────────────────────────────────────────┤
│ Outbox Pattern           │ WHY: The classic failure scenario: DB write commits, but app   │
│ for Kafka                │ crashes before publishing to Kafka. Payment is in DB but       │
│                          │ downstream services (email, fraud check) never get the event.  │
│                          │ Outbox writes the event in the SAME DB transaction as the       │
│                          │ payment. A separate relay process (Debezium CDC or polling)     │
│                          │ reads unpublished outbox rows and publishes to Kafka.          │
│                          │ WHY NOT direct Kafka publish: App could crash between DB       │
│                          │ commit and Kafka publish → event silently lost. No recovery    │
│                          │ path. The outbox guarantees at-least-once Kafka delivery.      │
├──────────────────────────┼───────────────────────────────────────────────────────────────┤
│ Saga (not 2PC) for       │ WHY: 2PC requires both participants to honor PREPARE and       │
│ cross-bank               │ COMMIT phases. External bank APIs (SWIFT, NEFT) do not support │
│ transactions             │ a prepare-only mode — they either execute or they don't.       │
│                          │ Saga works with what banks actually support: try the operation, │
│                          │ and if something downstream fails, issue a compensating         │
│                          │ transaction (reversal/refund) rather than rolling back.        │
│                          │ WHY NOT 2PC across external systems: External systems can be   │
│                          │ unavailable during the PREPARE phase indefinitely — holding    │
│                          │ locks on your side forever. 2PC requires trust and contracts   │
│                          │ with every participant. Use Saga + reconciliation instead.     │
├──────────────────────────┼───────────────────────────────────────────────────────────────┤
│ Optimistic Locking       │ WHY: Concurrent payments from the same account need to be      │
│ on accounts              │ serialized to prevent overdraft. Optimistic locking uses a     │
│                          │ version column: UPDATE accounts SET balance=balance-X,          │
│                          │ version=version+1 WHERE account_id=? AND version=expected       │
│                          │ AND balance >= X. If 0 rows updated → another transaction       │
│                          │ modified the row → retry. No DB locks held during bank call.   │
│                          │ WHY NOT SELECT FOR UPDATE: Pessimistic lock holds a row lock    │
│                          │ for the entire payment duration — including the bank API call   │
│                          │ (100-3000ms). This causes deadlocks and lock timeouts at scale. │
└──────────────────────────┴───────────────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 4 — FULL INTERVIEW SCRIPT ═══════════════

---

## OPENING — When Interviewer Says "Design a Payment System"

"The fundamental challenge here is correctness under failure. In distributed systems, the rule is:
anything that can fail, will fail. For a payment system that means: money must never be created from
nothing, lost, or moved twice. Every single design decision I make will be driven by the question:
what happens when this component fails mid-operation? Let me start by clarifying requirements."

---

## STEP 1 — Requirements Gathering

```
┌────────────────────────────────────────────┬──────────────────────────────────────────────┐
│ YOU ASK                                    │ INTERVIEWER SAYS (typical)                   │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ Is this a payment gateway (like Stripe)    │ Gateway + wallet — accept cards and          │
│ or a wallet system?                        │ allow P2P transfers between our users.        │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ Do we process payments directly or via     │ Via third-party banks and card networks       │
│ a payment processor?                       │ (Visa, Mastercard, bank APIs).               │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ What transaction volume are we targeting?  │ ~1M transactions/day at peak.                │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ Do we need refunds and chargebacks?        │ Yes, refunds. Chargebacks handled by bank.   │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ What currencies?                           │ Multi-currency — INR, USD, EUR primarily.    │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ What are the latency requirements?         │ Payment initiation < 500ms. Settlement async. │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ Do we need fraud detection?                │ Yes, but it can be async — don't block txn.  │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ What consistency is required?              │ Strong — no double charges, no lost payments. │
└────────────────────────────────────────────┴──────────────────────────────────────────────┘
```

```
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ REQUIREMENTS SUMMARY                                                                       │
├──────────────────────────────────────────────┬─────────────────────────────────────────────┤
│ FUNCTIONAL                                   │ NON-FUNCTIONAL                              │
├──────────────────────────────────────────────┼─────────────────────────────────────────────┤
│ 1. Create payment (card, bank transfer)      │ Scale: 1M transactions/day (~12 TPS avg,    │
│ 2. Wallet-to-wallet transfer (P2P)           │   ~100 TPS peak)                            │
│ 3. Check payment status                      │ Latency: API response < 500ms               │
│ 4. Refund a payment                          │ Consistency: Strong (ACID, no eventual)     │
│ 5. View transaction history                  │ Availability: 99.99% (4-nines)             │
│ 6. Multi-currency support                    │ Data retention: 7 years (regulatory)        │
│ 7. Idempotent retry support                  │ Fraud detection: async, < 5 sec             │
│ 8. Async fraud detection                     │ Audit: every transaction immutably logged   │
└──────────────────────────────────────────────┴─────────────────────────────────────────────┘
```

Key insight: Volume (100 TPS) is NOT the design constraint here. MySQL handles 10,000+ TPS per shard trivially. The constraint is correctness: exactly-once execution, immutable audit trail, zero money creation or loss.

---

## STEP 2 — Capacity Estimation

```
TRANSACTION VOLUME:
  1M transactions/day ÷ 86,400 = ~12 transactions/sec average
  Peak (8x avg for flash sales): ~100 TPS
  → MySQL on a single primary handles 10K TPS easily. Volume is NOT the challenge.

STORAGE:
  payments table row: ~500 bytes
  ledger_entries: 2 rows per payment × 200 bytes = 400 bytes
  Total per payment: ~900 bytes
  1M payments/day × 900 bytes × 365 days × 7 years = ~2.3 TB
  → Single MySQL shard with replicas handles this. Shard only when needed.

IDEMPOTENCY REDIS:
  1M payment attempts/day (including retries, ~1.5M keys)
  TTL: 24 hours → at any time ~1.5M keys in Redis
  Each key: ~100 bytes → 150 MB total
  → Trivially small Redis footprint.

BANK API CALL LATENCY:
  Domestic bank API: 100-500ms
  International SWIFT: 1-30 seconds
  Card network (Visa/MC): 200-800ms
  → NEVER hold a DB transaction open during these calls.
    Open transaction = held locks = deadlocks at scale.
```

---

## STEP 3 — Core Entities

```
┌──────────────────────┬─────────────────────────────────────────────────────────────────┐
│ Entity               │ Key Fields                                                      │
├──────────────────────┼─────────────────────────────────────────────────────────────────┤
│ Payment              │ payment_id (UUID PK), idempotency_key (UNIQUE), amount (BIGINT  │
│                      │ cents), currency (CHAR 3), from_account_id, to_account_id,      │
│                      │ status (ENUM), created_at, updated_at, bank_reference_id        │
├──────────────────────┼─────────────────────────────────────────────────────────────────┤
│ Account              │ account_id (BIGINT PK), user_id, balance (BIGINT cents),        │
│                      │ currency, version (INT for optimistic locking), status           │
├──────────────────────┼─────────────────────────────────────────────────────────────────┤
│ LedgerEntry          │ entry_id (BIGINT PK), payment_id (FK), account_id, amount       │
│                      │ (BIGINT), entry_type (ENUM: DEBIT/CREDIT), created_at           │
│                      │ → NEVER UPDATED. Append-only. Immutable.                        │
├──────────────────────┼─────────────────────────────────────────────────────────────────┤
│ OutboxEvent          │ event_id (BIGINT PK), payment_id, event_type, payload (JSON),   │
│                      │ published (BOOLEAN), created_at                                 │
│                      │ → Written in same TX as payment. Relay publishes to Kafka.      │
└──────────────────────┴─────────────────────────────────────────────────────────────────┘
```

KEY INSIGHT: Balance in the accounts table is a "materialized view" of the ledger — maintained for fast reads. The ledger is the source of truth. If they diverge (a bug), you reconstruct balance by summing the ledger. Never trust the balance field without a ledger reconciliation path.

---

## STEP 4 — API Design

```
1. INITIATE PAYMENT
   POST /api/v1/payments
   Headers: Idempotency-Key: <client-UUID>
   Request:  { "fromAccountId": "acc_123", "toAccountId": "acc_456",
               "amount": 10000, "currency": "INR", "description": "Order #789" }
   Response: { "paymentId": "pay_abc123", "status": "INITIATED",
               "amount": 10000, "currency": "INR", "createdAt": "..." }
   Status: 202 Accepted (async processing) | 409 Conflict (duplicate idempotency key,
           returns original response) | 422 Unprocessable (insufficient funds detected early)

2. GET PAYMENT STATUS
   GET /api/v1/payments/{paymentId}
   Response: { "paymentId": "...", "status": "SUCCESS", "settledAt": "...",
               "bankReferenceId": "HDFC20240101XYZ" }
   Status: 200 OK | 404 Not Found

3. REFUND PAYMENT
   POST /api/v1/payments/{paymentId}/refund
   Headers: Idempotency-Key: <client-UUID>
   Request:  { "amount": 5000, "reason": "Customer request" }
   Response: { "refundId": "ref_xyz789", "originalPaymentId": "pay_abc123",
               "status": "REFUND_INITIATED", "amount": 5000 }
   Note: A refund creates a NEW payment record — it does NOT modify the original payment.

4. GET ACCOUNT BALANCE
   GET /api/v1/accounts/{accountId}/balance
   Response: { "accountId": "...", "balance": 150000, "currency": "INR",
               "availableBalance": 145000 }
   Note: availableBalance = balance minus any pending holds.

5. GET TRANSACTION HISTORY
   GET /api/v1/accounts/{accountId}/transactions?from=2024-01-01&to=2024-01-31&limit=50
   Response: { "transactions": [...], "nextCursor": "..." }
   Note: Cursor-based pagination (not offset) for consistency during concurrent inserts.
```

### API JSON EXAMPLES

#### 1. POST /api/v1/payments — Initiate Payment

```json
// Request:
POST /api/v1/payments
Idempotency-Key: user_123_txn_abc789
{
  "fromAccountId": "acc_alice_001",
  "toAccountId": "acc_bob_002",
  "amount": 50000,
  "currency": "INR",
  "description": "Rent payment"
}

// Response 202 Accepted:
{
  "paymentId": "pay_9f2a3b4c5d6e",
  "status": "INITIATED",
  "amount": 50000,
  "currency": "INR",
  "createdAt": "2025-01-21T10:30:00Z",
  "estimatedCompletionMs": 3000
}

// Response 409 Conflict (duplicate idempotency key — returns original response):
{
  "paymentId": "pay_9f2a3b4c5d6e",
  "status": "SUCCESS",
  "amount": 50000,
  "currency": "INR",
  "createdAt": "2025-01-21T10:30:00Z"
}
```

#### 2. GET /api/v1/payments/{paymentId} — Get Payment Status

```json
// Response 200 OK (completed):
{
  "paymentId": "pay_9f2a3b4c5d6e",
  "status": "SUCCESS",
  "amount": 50000,
  "currency": "INR",
  "fromAccountId": "acc_alice_001",
  "toAccountId": "acc_bob_002",
  "bankReferenceId": "HDFC20250121XYZ",
  "completedAt": "2025-01-21T10:30:03Z",
  "ledgerEntries": [
    { "type": "DEBIT",  "accountId": "acc_alice_001", "amount": 50000 },
    { "type": "CREDIT", "accountId": "acc_bob_002",   "amount": 50000 }
  ]
}

// Response 200 OK (still processing):
{
  "paymentId": "pay_9f2a3b4c5d6e",
  "status": "PROCESSING",
  "amount": 50000,
  "currency": "INR"
}
```

#### 3. POST /api/v1/payments/{paymentId}/refund — Refund Payment

```json
// Request:
POST /api/v1/payments/pay_9f2a3b4c5d6e/refund
Idempotency-Key: refund_abc_001
{
  "amount": 50000,
  "reason": "Customer request"
}

// Response 202 Accepted:
{
  "refundId": "ref_xyz789",
  "originalPaymentId": "pay_9f2a3b4c5d6e",
  "status": "REFUND_INITIATED",
  "amount": 50000,
  "currency": "INR"
}
```

---

## STEP 5 — High-Level Architecture

> **► DRAW THIS on the whiteboard ◄**
> Draw the WRITE path as a vertical flow: Client → API Gateway → Payment Service → MySQL (with
> Outbox) → Kafka → Payment Processor → Bank API → MySQL update. Emphasize the outbox and
> the separation between the initial response (202 Accepted) and the async bank processing.

```
  CLIENT
    │
    │ POST /payments { idempotencyKey, amount, from, to }
    ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                        API GATEWAY                                     │
  │              TLS termination, JWT auth, rate limiting                  │
  └──────────────────────────────────┬──────────────────────────────────────┘
                                     │
                        ┌────────────▼─────────────┐
                        │   Idempotency Check       │
                        │   Redis: GET idempotencyKey│
                        │   HIT → return cached resp│
                        │   MISS → proceed          │
                        └────────────┬──────────────┘
                                     │ MISS
                                     ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                      Payment Service (stateless)                        │
  │                                                                         │
  │   BEGIN TRANSACTION (MySQL ACID)                                        │
  │     1. Validate payment request (amount > 0, valid accounts, etc.)     │
  │     2. Check account balance with optimistic lock (version check)       │
  │     3. INSERT payment (status=INITIATED)                                │
  │     4. INSERT outbox_event (published=false)                            │
  │   COMMIT                                                                │
  │                                                                         │
  │   Store in Redis: idempotencyKey → {paymentId, status} (TTL=24h)       │
  │   Return 202 Accepted to client                                         │
  └──────────────────────────────────┬───────────────────────────────────────┘
                                     │ (async, after response sent)
                     ┌───────────────▼──────────────────┐
                     │       Outbox Relay Service        │
                     │  Polls outbox_events WHERE        │
                     │  published=false, publishes to    │
                     │  Kafka, marks published=true      │
                     └───────────────┬──────────────────┘
                                     │
                                     ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                         Kafka                                           │
  │                   Topic: payment.process                                │
  │              Partitioned by from_account_id (locality)                  │
  └──────────────────────────────────┬──────────────────────────────────────┘
                                     │
                                     ▼
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                   Payment Processor Service                             │
  │                                                                         │
  │   1. UPDATE payment status → PROCESSING                                 │
  │   2. Optimistic lock check on source account balance                   │
  │   3. Call external bank/card API (async, non-blocking)                 │
  │   4a. On SUCCESS:                                                       │
  │       BEGIN TX                                                          │
  │         UPDATE payment status → SUCCESS                                 │
  │         UPDATE accounts SET balance=balance-X WHERE ... AND version=V  │
  │         UPDATE accounts SET balance=balance+X WHERE ... (destination)  │
  │         INSERT ledger_entries (DEBIT source, CREDIT dest)              │
  │       COMMIT                                                            │
  │   4b. On FAILURE:                                                       │
  │       UPDATE payment status → FAILED                                   │
  │   4c. On TIMEOUT:                                                       │
  │       UPDATE payment status → PENDING, schedule status-check retry    │
  └──────────────────────────────────┬───────────────────────────────────────┘
                                     │
                      ┌──────────────┴─────────────┐
                      │                            │
                      ▼                            ▼
  ┌─────────────────────────┐     ┌───────────────────────────────┐
  │   MySQL (Primary +      │     │   External Bank / Card        │
  │   Read Replicas)        │     │   Network API                 │
  │                         │     │   (HDFC, SBI, Visa, MC)       │
  │  payments               │     │   Response: SUCCESS/FAILED/   │
  │  accounts               │     │   PENDING (with ref ID)       │
  │  ledger_entries         │     └───────────────────────────────┘
  │  outbox_events          │
  └─────────────────────────┘
                │
                │ nightly batch
                ▼
  ┌─────────────────────────────────────────────────────┐
  │          Reconciliation Service                     │
  │  Download bank statement CSV                        │
  │  Compare each bank txn to our ledger_entries        │
  │  Mismatch → alert ops, freeze account               │
  └─────────────────────────────────────────────────────┘
```

---

> **► DRAW THIS on the whiteboard ◄**

## STEP 5b — PAYMENT SEQUENCE DIAGRAM (Happy Path + Failure Recovery)

```
  Client          API Service      DB (MySQL)       Kafka          Bank API
    │                  │               │               │               │
    │ POST /pay        │               │               │               │
    │ {idempotencyKey, │               │               │               │
    │  amount, from,to}│               │               │               │
    │─────────────────▶│               │               │               │
    │                  │ Check Redis:  │               │               │
    │                  │ idempotency   │               │               │
    │                  │ key seen?     │               │               │
    │                  │ [NO — first   │               │               │
    │                  │  time]        │               │               │
    │                  │               │               │               │
    │                  │ BEGIN TX      │               │               │
    │                  │──────────────▶│               │               │
    │                  │ Check balance │               │               │
    │                  │ (optimistic   │               │               │
    │                  │  lock)        │               │               │
    │                  │──────────────▶│               │               │
    │                  │ INSERT payment│               │               │
    │                  │ status=INIT.  │               │               │
    │                  │──────────────▶│               │               │
    │                  │ INSERT outbox │               │               │
    │                  │ event         │               │               │
    │                  │──────────────▶│               │               │
    │                  │ COMMIT TX     │               │               │
    │                  │──────────────▶│               │               │
    │                  │               │               │               │
    │ 202 ACCEPTED     │               │               │               │
    │ {paymentId,      │               │               │               │
    │  status:INIT}    │               │               │               │
    │◀─────────────────│               │               │               │
    │                  │               │               │               │
    │                  │     Outbox Relay reads outbox event            │
    │                  │               │──────────────▶│               │
    │                  │               │               │ publish       │
    │                  │               │               │ payment.init  │
    │                  │               │               │               │
    │                  │     Payment Processor consumes from Kafka      │
    │                  │               │               │               │
    │                  │               │               │ POST /charge  │
    │                  │               │               │──────────────▶│
    │                  │               │               │               │
    │                  │               │               │◀──────────────│
    │                  │               │               │  {SUCCESS}    │
    │                  │               │               │               │
    │                  │ UPDATE payment│               │               │
    │                  │ status=SUCCESS│               │               │
    │                  │──────────────▶│               │               │
    │                  │ INSERT ledger │               │               │
    │                  │ DEBIT+CREDIT  │               │               │
    │                  │──────────────▶│               │               │
    │                  │               │               │               │
    │                  │ TIMEOUT SCENARIO (bank no response after 30s) │
    │                  │               │               │               │
    │                  │ UPDATE payment│               │               │
    │                  │ status=PENDING│               │               │
    │                  │──────────────▶│               │               │
    │                  │               │               │               │
    │                  │ Schedule status-poll retry (exponential backoff)
    │                  │ Poll bank GET /charge/{paymentId} → {SUCCESS/FAILED}
```

---

## STEP 6 — Database Schema

> **► DRAW THIS on the whiteboard ◄**

```
TABLE: payments
┌────────────────────┬──────────────────────┬────────────────────────────────────────────────┐
│ Column             │ Type                 │ Notes                                          │
├────────────────────┼──────────────────────┼────────────────────────────────────────────────┤
│ payment_id         │ VARCHAR(36) UUID PK  │ UUID v4. Primary key.                          │
│ idempotency_key    │ VARCHAR(64) UNIQUE   │ Client-provided. UNIQUE constraint prevents    │
│                    │                      │ duplicate processing at DB layer.              │
│ amount             │ BIGINT NOT NULL      │ In SMALLEST currency unit (paise/cents).       │
│                    │                      │ NEVER FLOAT. Rs.100 = 10000 paise.            │
│ currency           │ CHAR(3) NOT NULL     │ ISO 4217: 'INR', 'USD', 'EUR'                │
│ from_account_id    │ BIGINT NOT NULL      │ FK to accounts. Source of funds.              │
│ to_account_id      │ BIGINT NOT NULL      │ FK to accounts. Destination of funds.         │
│ status             │ ENUM NOT NULL        │ INITIATED, PROCESSING, SUCCESS, FAILED,       │
│                    │                      │ REFUNDED, TIMEOUT, CANCELLED                  │
│ bank_reference_id  │ VARCHAR(100)         │ Reference ID from bank/card network.          │
│ description        │ VARCHAR(500)         │ Human-readable note.                          │
│ created_at         │ TIMESTAMP            │ Immutable. Set once on insert.                │
│ updated_at         │ TIMESTAMP            │ Updated on every status change.               │
└────────────────────┴──────────────────────┴────────────────────────────────────────────────┘

TABLE: accounts
┌────────────────────┬──────────────────────┬────────────────────────────────────────────────┐
│ Column             │ Type                 │ Notes                                          │
├────────────────────┼──────────────────────┼────────────────────────────────────────────────┤
│ account_id         │ BIGINT AUTO_INC PK   │ Shard key.                                     │
│ user_id            │ BIGINT NOT NULL      │ FK to users table.                             │
│ balance            │ BIGINT NOT NULL      │ Current balance in paise/cents.               │
│ currency           │ CHAR(3)              │ ISO 4217                                       │
│ version            │ INT NOT NULL DEFAULT │ Optimistic locking version counter.            │
│                    │ 0                    │ Incremented on every balance update.           │
│ status             │ ENUM                 │ ACTIVE, FROZEN, CLOSED                        │
│ created_at         │ TIMESTAMP            │                                                │
└────────────────────┴──────────────────────┴────────────────────────────────────────────────┘

CRITICAL QUERY — Optimistic lock balance deduction:
  UPDATE accounts
  SET balance = balance - :amount, version = version + 1
  WHERE account_id = :id
    AND version = :expectedVersion
    AND balance >= :amount
    AND status = 'ACTIVE';
  -- If rows_affected = 0 → conflict or insufficient funds → retry or fail

TABLE: ledger_entries  (APPEND-ONLY, NEVER UPDATE)
┌────────────────────┬──────────────────────┬────────────────────────────────────────────────┐
│ Column             │ Type                 │ Notes                                          │
├────────────────────┼──────────────────────┼────────────────────────────────────────────────┤
│ entry_id           │ BIGINT AUTO_INC PK   │                                                │
│ payment_id         │ VARCHAR(36)          │ FK to payments table.                          │
│ account_id         │ BIGINT               │ Which account this entry affects.              │
│ amount             │ BIGINT               │ Positive value (direction given by entry_type).│
│ entry_type         │ ENUM                 │ DEBIT (money going out) or CREDIT (money in).  │
│ running_balance    │ BIGINT               │ Account balance after this entry. Snapshot.   │
│ created_at         │ TIMESTAMP            │ Immutable creation time.                      │
└────────────────────┴──────────────────────┴────────────────────────────────────────────────┘

For every payment (pay_123, Rs.100 from acc_A to acc_B):
  Row 1: payment_id=pay_123, account_id=acc_A, amount=10000, entry_type=DEBIT
  Row 2: payment_id=pay_123, account_id=acc_B, amount=10000, entry_type=CREDIT
  Sum of DEBIT entries for payment = Sum of CREDIT entries = Rs.100. Money is conserved.

TABLE: outbox_events
┌────────────────────┬──────────────────────┬────────────────────────────────────────────────┐
│ Column             │ Type                 │ Notes                                          │
├────────────────────┼──────────────────────┼────────────────────────────────────────────────┤
│ event_id           │ BIGINT AUTO_INC PK   │                                                │
│ payment_id         │ VARCHAR(36)          │ FK to payments.                                │
│ event_type         │ VARCHAR(50)          │ 'PAYMENT_INITIATED', 'PAYMENT_SUCCESS', etc.   │
│ payload            │ JSON                 │ Full event payload for downstream consumers.   │
│ published          │ BOOLEAN DEFAULT false│ Set to true after Kafka publish confirmed.     │
│ created_at         │ TIMESTAMP            │                                                │
└────────────────────┴──────────────────────┴────────────────────────────────────────────────┘
```

---

> **► DRAW THIS on the whiteboard ◄**

## ER RELATIONSHIP DIAGRAM

```
┌──────────────────────────────────────────────────────────────────────┐
│                PAYMENT SYSTEM — ENTITY RELATIONSHIP                   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────┐           ┌───────────────────────┐
│    users     │           │      accounts          │
├──────────────┤           ├───────────────────────┤
│ PK user_id   │◄─────────│ PK account_id BIGINT  │
│    name TEXT │  1    N   │ FK user_id BIGINT     │
│    email TEXT│           │    balance BIGINT     │
│    kyc_status│           │    currency CHAR(3)   │
└──────────────┘           │    version INT        │  ← optimistic lock
                           └──────────┬────────────┘
                                      │ 1 (from_account / to_account)
                                      │
          ┌───────────────────────────▼──────────────────────────┐
          │                     payments                          │
          ├──────────────────────────────────────────────────────┤
          │ PK payment_id        UUID                            │
          │    idempotency_key   VARCHAR UNIQUE                  │
          │ FK from_account_id   BIGINT ──────────────┐          │
          │ FK to_account_id     BIGINT ──────────────┤→accounts │
          │    amount            BIGINT (cents)        │          │
          │    currency          CHAR(3)               │          │
          │    status            ENUM                  │          │
          │    created_at        TIMESTAMP             │          │
          │    updated_at        TIMESTAMP             │          │
          └────────────┬─────────────────────────────┘          │
                       │ 1                                        │
                       │ N                                        │
          ┌────────────▼──────────────────┐                      │
          │       ledger_entries           │                      │
          ├───────────────────────────────┤                      │
          │ PK entry_id    BIGINT         │                      │
          │ FK payment_id  UUID           │                      │
          │ FK account_id  BIGINT → accounts                     │
          │    amount      BIGINT                                 │
          │    entry_type  ENUM(DEBIT, CREDIT)                   │
          │    created_at  TIMESTAMP                              │
          │                                                       │
          │  ⚠ APPEND-ONLY. NEVER UPDATE.                        │
          └───────────────────────────────┘

          ┌───────────────────────────────┐
          │       outbox_events            │
          ├───────────────────────────────┤
          │ PK event_id    BIGINT         │
          │ FK payment_id  UUID           │
          │    event_type  VARCHAR        │
          │    payload     JSON           │
          │    published   BOOLEAN        │
          │    created_at  TIMESTAMP      │
          └───────────────────────────────┘
```

---

## STEP 7 — Deep Dive: Exactly-Once Payment Execution

This is the hardest part of payment system design. Be able to explain this without notes.

```
THE PROBLEM: Network failures create ambiguous states.

Scenario: Payment processor sends request to bank. Bank debits the customer.
Network fails. Processor never gets the SUCCESS response.
Processor retries. Now: does the bank charge again?

This is the exactly-once problem. There are three parties:
  1. Our system (knows about the payment)
  2. Kafka (the message bus)
  3. The external bank (executes the debit)

SOLUTION LAYERS (each layer handles a different failure):

LAYER 1 — Client → Our API (idempotency key in Redis):
  Client retries with same idempotency key.
  We check Redis. Key exists → return original response. No DB touched.
  Handles: client network failure, client timeout, client retry.

LAYER 2 — Our API → DB (ACID transaction):
  Payment INSERT and outbox_event INSERT happen atomically.
  If app crashes mid-transaction → MySQL rolls back. No partial state.
  Handles: app crash during write, DB connection failure.

LAYER 3 — DB → Kafka (Outbox pattern):
  Outbox relay reads unpublished events. Publishes. Marks published=true.
  If relay crashes after publish but before marking: Kafka gets duplicate event.
  Kafka consumer is idempotent: check if payment_id already processed → skip.
  Handles: relay crash between publish and acknowledgment.

LAYER 4 — Our processor → Bank API (bank-side idempotency):
  Every bank API call includes our payment_id as the merchant_reference_id.
  Bank deduplicates by merchant_reference_id.
  Retry with same payment_id → bank returns original result, no double charge.
  Handles: network failure between processor and bank, timeout, partial response.

LAYER 5 — Bank SUCCESS → Our DB (status update):
  Processor receives SUCCESS from bank. Updates payment status + inserts ledger entries
  in one ACID transaction.
  If processor crashes after bank SUCCESS but before our DB update:
    On restart, processor re-reads payment from Kafka (at-least-once delivery).
    Checks payment current status. If already SUCCESS (idempotent DB check) → skip.
    If still PROCESSING → re-attempt (bank idempotency handles the duplicate bank call).
  Handles: processor crash after bank response, DB unavailability.

LAYER 6 — Daily Reconciliation (the ultimate safety net):
  Even if all above layers work correctly, we compare our ledger to the bank statement.
  Any payment in bank statement not in our ledger (or vice versa) → alert + investigate.
  This catches bugs that slip through all other layers.
  Handles: bugs in our logic, silent bank errors, data corruption.
```

---

## STEP 8 — Scalability

```
BOTTLENECK 1: All payments serialize through MySQL writes
  PROBLEM: At 100 TPS, MySQL is fine. At 10K TPS (PayPal scale), a single MySQL
    primary becomes a bottleneck for balance updates.
  SOLUTION: Shard MySQL by account_id. Each shard owns a range of account_ids.
    Payments between accounts on the same shard are a local ACID transaction.
    Payments between accounts on different shards use the Saga pattern:
      Shard A: debit source (local ACID)
      Shard B: credit destination (local ACID)
      On Shard B failure: compensating transaction on Shard A (re-credit).
    This is the industry standard — even Stripe shards their MySQL.

BOTTLENECK 2: Bank API calls block payment processor threads
  PROBLEM: Bank APIs take 100-3000ms. If processor holds a thread per payment, at
    100 TPS you need 100-3000 threads just waiting on I/O. This is unsustainable.
  SOLUTION: Non-blocking I/O with async HTTP client (Java: WebClient/Netty, not RestTemplate).
    Processor sends bank request, releases thread, callback fires when response arrives.
    At 100 TPS, 10 threads with async I/O can handle 1000+ concurrent bank calls.
    Timeouts: set bank call timeout to 30 seconds. On timeout → mark PENDING → retry.

BOTTLENECK 3: Fraud detection blocking payment path
  PROBLEM: ML fraud model takes 200-500ms per transaction. If called synchronously,
    every payment has 500ms added to its latency. This is unacceptable.
  SOLUTION: Async fraud detection after returning 202 Accepted.
    Payment status starts as PROCESSING. Fraud service consumes from Kafka.
    On HIGH_RISK result: update payment to FRAUD_BLOCKED, notify user, don't execute.
    Trade-off: there is a small window where payment is processing before fraud check.
    Mitigate: pre-payment lightweight rule check (velocity, blacklist) synchronously in <5ms.
    The heavy ML model runs async.

BOTTLENECK 4: Read traffic on payment status queries
  PROBLEM: Mobile apps poll GET /payments/{id} every 2 seconds waiting for async result.
    At 1M concurrent users polling → 500K status reads/sec on MySQL.
  SOLUTION: Serve status reads from Redis. On every payment state change, update Redis:
    SET payment_status:{paymentId} {status, updatedAt} EX 3600 (1 hour TTL).
    Status queries hit Redis first. MySQL only for cache misses or detailed history.
    Better: WebSockets or Server-Sent Events to push status update to client, eliminating polling.
```

---

## WHAT NOT TO SAY ✗

```
✗ "I'll use MongoDB for the payments database — it's flexible and scalable"
  Why wrong: MongoDB's multi-document transactions are weaker than MySQL ACID.
  A payment debit + ledger insert is a two-document operation that MUST be atomic.
  MongoDB's transaction support is an afterthought — MySQL was built for this exact use case.
  Financial data needs ACID. Say MySQL or PostgreSQL. Period.

✗ "I'll store the payment amount as a FLOAT or DOUBLE"
  Why wrong: This is an instant fail in financial system design interviews.
  0.1 + 0.2 = 0.30000000000000004 in IEEE 754 floating point. At scale, these
  rounding errors accumulate and your ledger will never balance. Always store money as
  BIGINT in the smallest denomination (paise, cents). Rs.10.50 → 1050 paise.

✗ "I'll call the bank API synchronously while holding the DB transaction open"
  Why wrong: Bank API calls take 100-3000ms. A MySQL transaction holding row locks
  for 3 seconds will block every other payment touching those accounts. At 100 TPS,
  you'd need to serialize hundreds of operations behind each other. Deadlocks cascade.
  Always: commit the DB transaction, THEN call the bank API async.

✗ "I'll use 2PC across our system and the external bank"
  Why wrong: 2PC requires both participants to hold locks until the coordinator decides.
  External banks don't implement PREPARE — they either execute or they don't. You cannot
  ask HDFC Bank to "prepare but don't commit." Use Saga + compensating transactions instead.

✗ "I'll UPDATE the ledger entry if there's a correction"
  Why wrong: Ledger entries are legally immutable. Financial regulations (RBI, PCI-DSS)
  require an audit trail showing exactly what happened. If a payment amount was wrong,
  you don't UPDATE the original entry — you create a new CREDIT or DEBIT entry to correct
  the balance. The original entry remains forever.

✗ "I'll use SELECT FOR UPDATE (pessimistic lock) on the accounts table"
  Why wrong: Locks are held for the entire transaction duration — including the bank API
  call (up to 3 seconds). Two concurrent payments from the same account will serialize
  completely, and any failure causes a lock timeout. Use optimistic locking (version column)
  instead — retry on conflict, no locks held during I/O.

✗ "If reconciliation finds a mismatch, I'll auto-correct the balance"
  Why wrong: A balance mismatch between your ledger and the bank's statement means
  something fundamentally wrong happened — a bug, a security incident, or a bank error.
  Auto-correcting silently masks the root cause. Always: alert the ops team, freeze
  the account pending investigation, and require human review before any correction.
```

---

## SENIOR TRAP QUESTIONS (15 YOE Level)

### Category 1: Failure During Bank Call

**Q: Bank API times out after 30 seconds. Our payment is in PROCESSING state. The customer is staring at a spinner. What do you do?**

A: Mark the payment status as PENDING_CONFIRMATION in our DB. Return the current status to the
client immediately — do not keep them waiting. Schedule a background job to poll the bank's status
query API using our merchant_reference_id (payment_id). Bank's status API returns COMPLETED or FAILED.
On COMPLETED: update our payment to SUCCESS, insert ledger entries, notify customer via push notification.
On FAILED: update to FAILED, ensure no balance deduction occurred (verify via ledger), notify customer.
Critical: we must NEVER retry the original payment initiation with the same payment_id as a new request —
that's how you double-charge. We only query status using the idempotent bank reference. The bank's
idempotency key (our payment_id) ensures that if the bank DID process the payment, polling will return
the original result. If the bank's status API also times out repeatedly, escalate to manual ops review
after 24 hours — do not auto-retry indefinitely.

**Q: Our DB write of the SUCCESS status fails AFTER the bank has confirmed and debited the customer. Money left the customer's account but our system shows PROCESSING. What now?**

A: This is the "lost update" scenario — the most dangerous failure case. Prevention: the Payment Processor
reads Kafka events at-least-once. When it retries processing this payment, it calls the bank status API
with our payment_id before attempting a new bank call. The bank returns the original COMPLETED result
with its reference ID. Now the processor can update the DB to SUCCESS with the bank reference ID as proof.
If the DB write keeps failing (DB outage), the payment stays in PROCESSING in our DB but the customer's
bank account was debited. This is a reconciliation case: the nightly reconciliation will find a bank
statement entry that has no corresponding SUCCESS entry in our ledger → alert ops → manual correction.
This is why reconciliation is the safety net: it catches exactly this scenario.

---

### Category 2: Concurrency and Correctness

**Q: A user has Rs.100 and submits two payments of Rs.80 simultaneously from two different devices. Both should fail (only one should succeed). How does your system guarantee at most one succeeds?**

A: Optimistic locking on the accounts table is the answer. Both requests read the account with version=5
and balance=10000 (paise). Both then attempt:
  UPDATE accounts SET balance=2000, version=6 WHERE account_id=X AND version=5 AND balance>=8000
The first to execute succeeds: rows_affected=1, version becomes 6.
The second executes and finds version=5 no longer matches (it's now 6): rows_affected=0 → conflict.
The second payment returns INSUFFICIENT_FUNDS (we also need to re-read the balance to confirm).
The balance is now 2000 paise (Rs.20), not negative. Double-spend prevented.
Critical edge case: after the first payment PROCESSING state is set but before the SUCCESS update,
the second payment check reads balance=10000 (the pre-deduction balance). This is why the final
balance deduction happens in the SUCCESS commit step with the optimistic lock check — not in the
INITIATED step. The balance check in INITIATED is a fast early-fail; the definitive deduction
with locking happens in SUCCESS.

**Q: How do you handle refunds for a payment that has already been partially settled?**

A: A refund is modeled as a new payment in the reverse direction — NOT a modification of the
original payment. We create a new payment record with type=REFUND and reference to the original
payment_id. The refund goes through the same pipeline: idempotency check, outbox pattern, bank API
call (reverse transfer or card refund). We insert two new ledger entries: CREDIT the source account
(customer gets money back), DEBIT the destination account (merchant). The original payment and its
ledger entries remain immutable. Partial refunds work the same way — a refund payment for a partial
amount. The original payment remains SUCCESS; the refund creates its own SUCCESS entry. Balance
reflects the net of all entries. This design also makes the audit trail clean: the compliance team
can see exactly what happened step by step.

---

### Category 3: Architecture and Regulations

**Q: PCI-DSS compliance requires that cardholder data (card numbers, CVV) is never stored in our systems unless encrypted. How does your architecture handle this?**

A: Our system should NEVER store raw card numbers or CVV. The card tokenization flow is:
Client-side: the payment form uses a Stripe.js-like SDK that sends card data directly to the card
network's secure tokenization endpoint (not through our servers). The SDK returns a single-use token.
Our API receives only this token — we never see the raw card number. We store only the token, the
last 4 digits (for display), and the card brand. When charging, we pass the token to the card
processor. The token is useless to an attacker — it can only be used by our merchant account.
For recurring payments: the card network provides a permanent token (network token). We store this
for future charges. Network tokenization is handled entirely outside our DB. This means we are not
in PCI-DSS scope for card storage — we only handle tokens, which dramatically reduces our compliance
burden. Our infrastructure still needs PCI-DSS Level 1 certification for the payment processing
environment, but card data never touches our application servers.

---

## KEY NUMBERS — Memorize These

```
┌────────────────────────────────────────────┬──────────────────────────────────────────────┐
│ Metric                                     │ Value                                        │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ Transaction volume (Stripe-scale)          │ ~1B transactions/year = ~32 TPS global       │
│ Transaction volume (Razorpay India)        │ ~100M transactions/month = ~38 TPS           │
│ MySQL TPS capacity (single node)           │ 10,000 TPS (payments are NOT a DB bottleneck)│
│ Bank API latency (domestic)                │ 100–500ms                                    │
│ Bank API latency (international SWIFT)     │ 1–30 seconds                                 │
│ Card network (Visa/Mastercard)             │ 200–800ms                                    │
│ Idempotency key TTL in Redis               │ 24 hours                                     │
│ Data retention requirement (regulatory)   │ 7 years minimum (RBI mandate in India)       │
│ Amount storage                             │ BIGINT — smallest denomination (paise/cents) │
│ Optimistic lock: rows affected             │ 0 = conflict, retry; 1 = success             │
│ Ledger entries per payment                 │ 2 (1 DEBIT + 1 CREDIT). Sum always = 0.     │
│ Reconciliation frequency                  │ Daily (nightly batch)                        │
│ Saga compensating transaction window       │ T+1 day for auto-reversal                    │
│ Redis idempotency cache size               │ ~150 MB for 1M payments/day (trivially small)│
└────────────────────────────────────────────┴──────────────────────────────────────────────┘
```

*Study order hint: Start with RAPID ANSWER → understand idempotency cold. The deep dive (STEP 7)
on exactly-once execution is what separates senior candidates — know all 6 layers. The WHAT NOT
TO SAY section contains instant-fail answers — review it before every interview.*
