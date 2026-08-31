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

WHY IDEMPOTENCY KEY EXISTS? (Beginner Explanation)
  Imagine you tap your phone to pay at a coffee shop — the network hiccups and you don't
  know if the charge went through. You tap again. Without an idempotency key, you just
  paid twice for one coffee. The idempotency key is like writing your order number on the
  payment slip: the cashier sees the same number a second time and says "already processed
  this one" — and hands back the receipt without charging again.
  Problem it solves: network timeouts cause clients to retry, which without protection
  causes double charges on the customer's card.
  Without it: every retry is a new transaction. A 3-second timeout + 3 retries = 4 charges
  for 1 purchase.

WHY WEBHOOKS / ASYNC CONFIRMATION? (Beginner Explanation)
  When a payment is submitted, the bank doesn't respond instantly — it can take seconds or
  even minutes. Instead of making the client stare at a loading spinner for 30 seconds, we
  return "202 Accepted" immediately and promise to notify when done. A webhook is that
  notification: once the bank confirms, our system fires a POST request to the merchant's
  server: "payment pay_abc123 succeeded." It's like a restaurant buzzer — you sit down and
  do other things; the buzzer goes off when your order is ready. You don't stand at the
  counter blocking everyone else.
  Problem it solves: bank processing is async; holding an HTTP connection open for 30
  seconds per payment is impractical and wastes server resources.
  Without it: every payment API call would time out before the bank responds, and the
  client would have no way to know the true final status.

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

WHY DOUBLE-ENTRY BOOKKEEPING EXISTS? (Beginner Explanation)
  Think of it like a bank passbook where every transaction shows two lines: money leaving
  one account and arriving at another. Alice pays Bob Rs.100 — Alice's side shows -100
  (DEBIT), Bob's side shows +100 (CREDIT). These two entries always cancel out to zero.
  This isn't just accounting tradition — it is a built-in self-checking mechanism. If you
  sum every entry in the ledger and the result isn't zero, you know money was silently
  created or destroyed by a bug somewhere.
  Problem it solves: tracking only one side of a transaction (e.g. only the debit) leaves
  no way to verify the books are balanced.
  Without it: a bug could silently debit Alice without crediting Bob — money vanishes from
  the system with no audit trail to find where it went.

WHY THE OUTBOX PATTERN EXISTS? (Beginner Explanation)
  Picture a restaurant: the waiter writes your order on a ticket (the DB write) AND needs
  to drop a copy in the kitchen's order slot (publish to Kafka). The problem: what if the
  waiter writes the ticket but the app crashes before dropping the kitchen copy? The kitchen
  never gets the order — but the ticket exists. The Outbox pattern solves this by having a
  separate relay process pick up all undelivered kitchen copies automatically. Even if the
  waiter falls over mid-step, the relay eventually delivers the copy.
  Problem it solves: the app can crash in the gap between a successful DB write and a
  successful Kafka publish — losing the event silently with no error and no recovery path.
  Without it: payment saved in DB, but fraud check, email, and settlement services are
  never notified. No error is shown — just silent data loss downstream.

WHY PAYMENT STATES (INITIATED → PROCESSING → SUCCESS / FAILED)? (Beginner Explanation)
  A payment is like a cheque going through the banking system: first it is written
  (INITIATED), then it is deposited and being verified (PROCESSING), then it either clears
  (SUCCESS) or bounces (FAILED). You can't go from SUCCESS back to INITIATED — that would
  be like un-clearing a cheque. The state machine enforces these rules at the DB level so
  no code can put a payment into an impossible combination of states.
  Problem it solves: without defined states, any part of the system could set a payment to
  any status at any time, causing impossible situations like a FAILED payment that still
  has ledger debit entries attached.
  Without it: a retry could re-process an already-completed payment. Customer gets charged
  twice, with no DB constraint to catch it.

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

WHY STRONG CONSISTENCY IS NON-NEGOTIABLE FOR PAYMENTS? (Beginner Explanation)
  "Eventual consistency" means: all nodes will agree on the data... eventually. For a social
  media like count, a few seconds of staleness is harmless. For a bank balance: if two
  servers each see a "sufficient funds" balance due to a stale replica read, both approve
  the payment. You just let someone spend the same Rs.100 twice. Strong consistency means
  when you read a balance, you see the actual current value — not a possibly-stale copy
  from a replica that hasn't caught up yet.
  Problem it solves: stale reads on account balances enable overdrafts and double-spending.
  Without it: Cassandra's eventual consistency model would let two concurrent payments both
  read sufficient funds and both succeed — the account ends up negative, money is gone.

WHY USE A PSP (PAYMENT SERVICE PROVIDER) LIKE STRIPE / RAZORPAY? (Beginner Explanation)
  A PSP is a pre-built bridge to the entire banking and card-network ecosystem. They have
  already: negotiated contracts with Visa, Mastercard, and hundreds of banks; built fraud
  detection; achieved PCI-DSS Level 1 compliance; handled card tokenization; and implemented
  dispute resolution workflows. Building all of this from scratch takes years and hundreds
  of millions of rupees in compliance costs, plus direct bilateral contracts with each bank.
  Problem it solves: connecting directly to card networks requires licenses, regulatory
  approvals, and massive infrastructure investment before a single payment is processed.
  Without it: a startup would spend 2-3 years and tens of millions just on compliance and
  bank integration — before writing a single line of product code.

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

```
6. ADD PAYMENT METHOD
   POST /api/v1/payment-methods
   Request:  { "type": "CARD", "token": "<psp-token>", "nickname": "My Visa" }
   Response: { "methodId": "pm_xyz001", "type": "CARD", "last4": "4242",
               "brand": "VISA", "expiryMonth": 12, "expiryYear": 2027, "isDefault": false }
   Status: 201 Created | 422 Unprocessable (invalid or expired token)
   Note: Raw card numbers NEVER reach our servers. Client tokenizes via PSP SDK; we store only token.

7. LIST PAYMENT METHODS
   GET /api/v1/payment-methods
   Response: { "methods": [{ "methodId": "pm_xyz001", "type": "CARD", "last4": "4242",
               "brand": "VISA", "isDefault": true }, ...] }
   Status: 200 OK

8. DELETE PAYMENT METHOD
   DELETE /api/v1/payment-methods/{methodId}
   Response: 204 No Content
   Status: 204 No Content | 404 Not Found | 409 Conflict (method has active recurring subscription)

9. WEBHOOK — PAYMENT PROVIDER CALLBACK
   POST /api/v1/webhooks/payment
   Headers: X-Webhook-Signature: <HMAC-SHA256 of payload + shared secret>
   Request:  { "event": "payment.success", "paymentId": "pay_abc123",
               "bankReferenceId": "HDFC20240101XYZ", "timestamp": "2025-01-21T10:30:03Z" }
   Response: 200 OK (must respond within 5s or PSP retries — process async, respond fast)
   Note: Verify HMAC-SHA256 signature FIRST before any processing. An unverified endpoint
         lets attackers inject fake payment.success events. Enqueue for async processing;
         never block the 200 response or the PSP will retry and flood the queue.

10. GET TRANSACTION RECEIPT
    GET /api/v1/payments/{paymentId}/receipt
    Response: { "receiptNumber": "RCP-2025-001234", "paymentId": "pay_abc123",
                "amount": 50000, "currency": "INR", "status": "SUCCESS",
                "fromAccount": "acc_alice_001", "toAccount": "acc_bob_002",
                "completedAt": "2025-01-21T10:30:03Z", "bankReferenceId": "HDFC20240101XYZ" }
    Status: 200 OK | 404 Not Found | 425 Too Early (payment not yet in a terminal state)
    Note: Only available once status = SUCCESS or REFUNDED. Safe to cache indefinitely —
          receipts are immutable once issued.
```

> **WHY ADD/LIST/DELETE PAYMENT METHODS (/api/v1/payment-methods)?** Saved cards and bank accounts are a distinct resource from payments — they need their own lifecycle: add once, reuse across many future payments, delete when no longer valid. Without these endpoints, every payment requires fresh card entry. This is also the PCI-DSS boundary: raw card data is tokenized by the PSP SDK on the client side and never reaches your servers. You store only the PSP-issued opaque token, the last 4 digits (for display), and the card brand. This is how Stripe's PaymentMethods API works.

> **WHY POST /api/v1/webhooks/payment?** Payment providers (Stripe, Razorpay) push status updates when a payment settles at the bank — this is the server-push complement to client polling on `GET /payments/{id}`. It closes the loop without requiring the client to poll indefinitely. Security requirement: always verify the `X-Webhook-Signature` HMAC-SHA256 before processing — an unverified endpoint lets any attacker POST a fake `payment.success` and unlock goods without paying. Respond 200 immediately and process async to prevent PSP retry storms when your processing is slow.

> **WHY GET /api/v1/payments/{paymentId}/receipt?** A receipt is a stable, formatted record of a completed payment — distinct from the live status resource. Customers need downloadable proof; merchant support teams need a lookup-by-receipt-number path for dispute resolution. Unlike the status endpoint (which transitions through states), a receipt is only emitted once the payment reaches a terminal state (SUCCESS or REFUNDED) and is then permanently cacheable. The human-readable `receiptNumber` is critical for customer support — it is far easier to cite on a call than a UUID.

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

WHY RECONCILIATION EXISTS? (Beginner Explanation)
  At the end of a shift, a cashier counts the till and compares it to the register receipts.
  If Rs.50 is missing, something went wrong. Reconciliation is the same check run nightly:
  download the bank's official statement and compare it line-by-line to our internal ledger.
  Any mismatch means our system and the bank disagree about what happened. This is the last
  safety net after all the automated technical guarantees have already been applied.
  Problem it solves: bugs, race conditions, or silent bank errors can slip through all
  automated layers — reconciliation catches what everything else missed.
  Without it: money could be debited by the bank without our system recording it (or vice
  versa) and no one would notice until a customer complaint days or weeks later.

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

WHY EXACTLY-ONCE EXECUTION IS HARD? (Beginner Explanation)
  Imagine you ask someone to wire money to a friend over a bad phone line. They call the
  bank — the line drops before they hear confirmation. Did the wire go through? If you call
  again and it already went through, your friend gets paid twice. If you don't call again
  and it didn't go through, the payment never arrives. You can't know which happened. This
  is the exactly-once problem: networks fail mid-operation, and the caller can't distinguish
  "it worked but the reply was lost" from "it never happened." The solution: give every
  payment a unique reference number and require the bank to promise — "if you send the same
  reference again, I return the original result, I never charge twice."
  Problem it solves: retries after network failure cause double-charges without idempotency
  guarantees enforced at every layer of the system.
  Without it: a 30-second bank timeout + 1 retry = customer charged twice, with both
  charges valid from the bank's perspective.

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

WHY FRAUD DETECTION EXISTS? (Beginner Explanation)
  A stolen credit card used at 3am to buy Rs.50,000 of gift cards looks suspicious. Fraud
  detection is a set of rules and ML models checking: Is this card being used from an
  unusual location? Is the amount much higher than this user's normal spend? Has this card
  been used 5 times in the last 2 minutes? Think of it as a security guard scanning each
  transaction against a known-suspicious-behavior profile — most transactions pass in
  milliseconds; only the outliers get flagged.
  Problem it solves: payment systems are prime targets for stolen card fraud; without
  detection, fraudulent transactions drain real customer accounts before anyone notices.
  Why run it async: a complex ML model adds 200-500ms to every payment. 99.9% of payments
  are legitimate — making everyone wait 500ms extra to catch 0.1% fraud is the wrong
  trade-off. A fast rule-based pre-check (velocity limits, blacklists) runs synchronously
  in under 5ms; the heavy ML model runs after the 202 Accepted response is already sent.

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

---

## KEY PATTERNS REFERENCED IN THIS DESIGN

> **For the 2-year developer:** These are the hidden concepts behind design decisions in this system. Each has a dedicated deep-dive file.

### B-tree vs LSM Tree
**Why it matters here:** MySQL B-tree for accounts/balance (range scans on transaction history). Cassandra LSM for audit log (append-only, never updated — LSM handles sequential writes without B-tree fragmentation).
**Deep dive:** `../../BTree_vs_LSM_Tree_MySQL_vs_Cassandra_RocksDB.md`

### UUID as Primary Key
**Why it matters here:** Payments table has millions of daily inserts. Random UUID PK → constant B-tree page splits → 40-50% fill factor. Solution: BIGINT AUTO_INCREMENT PK + public_id UUID for external references.
**Deep dive:** `../../UUID_as_Primary_Key_Why_Its_Bad.md`

### Connection Pooling
**Why it matters here:** 5000 TPS × 3 DB calls = 15K simultaneous connections without pooling. PostgreSQL hard limit ~500. HikariCP pool of 20 connections + queuing handles this safely.
**Deep dive:** `../../Connection_Pooling_Why_One_Connection_Per_Request_Fails.md`

### Optimistic vs Pessimistic Locking
**Why it matters here:** Pessimistic (SELECT FOR UPDATE) on account balance. Two concurrent debits must not both read the same balance. Without locking: both debit 800 from balance=1000 → account goes negative.
**Deep dive:** `../../Optimistic_vs_Pessimistic_Locking.md`

### CAP Theorem
**Why it matters here:** Payment is CP — during partition, return 503 rather than risk double-charge. A missed payment is recoverable; a duplicate charge is a P0 incident.
**Deep dive:** `../../CAP_Theorem_Applied_What_Actually_Breaks.md`

### Quorum Reads/Writes
**Why it matters here:** Cassandra ledger entries use W=ALL before acknowledging payment. Zero data loss is non-negotiable. R=QUORUM for audit reads ensures reading from a majority.
**Deep dive:** `../../Quorum_Reads_Writes_Cassandra_W_R_N.md`

### Split Brain
**Why it matters here:** PostgreSQL primary/replica split brain → two primaries → concurrent debits against same account → balance corruption. Quorum requirement (STONITH) for primary election.
**Deep dive:** `../../Split_Brain_Problem_Two_Primary_Nodes.md`

### Heartbeat Detection
**Why it matters here:** Payment service instances heartbeat to load balancer. Crashed instance stops heartbeating → LB stops routing within 30s → no payments routed to dead pod.
**Deep dive:** `../../Heartbeat_Detection_Dead_vs_Slow_Node.md`

### Gossip Protocol
**Why it matters here:** Cassandra cluster gossip — each node knows all other nodes' health without a central coordinator. Payment writes automatically avoid downed Cassandra nodes.
**Deep dive:** `../../Gossip_Protocol_Node_Discovery.md`

### Two-Phase Commit (2PC)
**Why it matters here:** Debit sender + credit receiver across two DB shards must be atomic. 2PC is the theory — in practice, most payment systems use Saga to avoid the blocking failure mode.
**Deep dive:** `../../Two_Phase_Commit_2PC_Distributed_Transactions.md`

### Saga Pattern
**Why it matters here:** International transfers — debit → currency conversion → credit. Compensating transactions (credit back) if any step fails. Orchestration saga via Temporal manages retry state.
**Deep dive:** `../../Saga_Pattern_Choreography_vs_Orchestration.md`

### Leader Election
**Why it matters here:** Scheduled payment processor (recurring charges). Only ONE instance should process a payment at a time. ZooKeeper/Redis SETNX for distributed lock.
**Deep dive:** `../../Leader_Election_Zookeeper_Raft.md`

### Idempotency Keys
**Why it matters here:** User double-taps "Pay" button. Both requests reach payment service. Idempotency-Key: UUID per button click — server deduplicates, charges exactly once.
**Deep dive:** `../../Idempotency_Keys_Prevent_Double_Processing.md`

### Circuit Breaker
**Why it matters here:** Payment service calls fraud detection. Fraud service is overloaded. Circuit OPEN: skip fraud check, use rule-based fallback. Better than timing out every payment.
**Deep dive:** `../../Circuit_Breaker_Pattern.md`

### Retry + Exponential Backoff + Jitter
**Why it matters here:** Bank gateway timeout. 1000 simultaneous timeouts with full jitter spread retries randomly. Without jitter: all 1000 retry at t=1s, hammer the already-struggling gateway.
**Deep dive:** `../../Retry_Exponential_Backoff_Jitter.md`

### Bulkhead Pattern
**Why it matters here:** Fraud detection thread pool isolated from payment processing pool. Fraud service hangs → its pool fills up, payment processing pool unaffected. Payments continue.
**Deep dive:** `../../Bulkhead_Pattern_Isolate_Failures.md`

### Timeout Strategy
**Why it matters here:** Bank gateway SLA P99 = 800ms. Set timeout = 1200ms (800ms + 50% buffer). Too short = false failures on legitimate slow payments. Too long = failed payments occupy thread pool for 10s each.
**Deep dive:** `../../Timeout_Strategy_Too_Short_Too_Long.md`

### [Database Sharding](../../Database_Sharding_Range_Hash_Consistent_Hashing.md)
**Why this system uses it:** Payments table at 500M rows requires sharding. Shard key = `account_id` (hash sharding via consistent hashing ring). All debits and credits for an account land on the same shard — balance queries hit one shard, no cross-shard joins. Avoid sharding by `payment_date` — all new payments would hammer the "today" shard. Resharding plan: dual-write to old + new shard during migration, then cut over.

### [MVCC — How PostgreSQL Reads Never Block Writes](../../MVCC_How_PostgreSQL_Reads_Never_Block_Writes.md)
**Why this system uses it:** Account balance reads (high frequency: every checkout, every login) must never block behind payment write transactions. PostgreSQL MVCC ensures every balance read gets a consistent snapshot without waiting for in-flight payment writes to commit. A READ COMMITTED read sees the balance as of its start time — no lock contention with concurrent debits. For double-spend prevention, use REPEATABLE READ isolation + optimistic locking to detect concurrent balance modifications.

### [Kafka Partition Key & Consumer Groups](../../Kafka_Partition_Key_Consumer_Groups_Rebalancing.md)
**Why this system uses it:** Payment events keyed by `account_id` — all debit/credit events for one account go to the same partition, guaranteeing ordering. Critical: a debit event must be processed before a subsequent balance check. Consumer group = payment processors; if one processor crashes, Kafka rebalances its partitions to other processors from the last committed offset. Hot partition risk: large merchant (Amazon) generating 10K payments/sec → one partition overwhelmed. Fix: sub-shard by `payment_id % 10` for large merchants.

### [Kafka Exactly-Once / At-Least-Once / DLQ](../../Kafka_Exactly_Once_At_Least_Once_DLQ.md)
**Why this system uses it:** Payment processing requires exactly-once semantics — a duplicate debit is a critical bug. Kafka transactional producer: `beginTransaction()` → publish payment event → `sendOffsetsToTransaction()` → `commitTransaction()`. Both the event and the offset commit happen atomically. If the consumer pod crashes after processing but before commit, it re-reads the same message → idempotency key in PostgreSQL (`INSERT ON CONFLICT DO NOTHING`) prevents double-debit. DLQ: payments rejected by gateway after 3 retries → DLQ for investigation.

### [Kafka vs RabbitMQ vs SQS](../../Kafka_vs_RabbitMQ_vs_SQS_When_to_Use_Which.md)
**Why this system uses it:** Kafka for payment event stream — replay capability for audit, high throughput, exactly-once. When payment fails gateway: SQS with visibility timeout for retry queue — simple task-queue semantics, built-in retry with exponential backoff, DLQ configuration. RabbitMQ not used here — no complex routing needed and Kafka's replay is non-negotiable for financial audit trail.

### [CQRS / Event Sourcing](../../CQRS_Event_Sourcing.md)
**Why this system uses it:** Payment ledger as an immutable event log — every debit/credit stored as an event, current balance = sum of events. Event sourcing enables full regulatory audit trail (SEC/RBI compliance): replay all events for any account at any point in time. CQRS: write side uses event sourcing (PostgreSQL event store), read side uses pre-computed balance projections in Redis (fast balance reads without event replay on every request).

### [CDC / Change Data Capture / Debezium](../../CDC_Change_Data_Capture_Debezium.md)
**Why this system uses it:** Real-time fraud detection needs to see every account balance change the moment it happens. Debezium reads PostgreSQL WAL → publishes account change events to Kafka → fraud detection service consumes and scores in real-time. Without CDC, fraud service would poll DB every second (10K queries/sec wasteful) or require dual-write (transaction risk). CDC gives sub-second latency with zero application code changes.

### [Hot Partition Problem](../../Hot_Partition_Problem_And_Solutions.md)
**Why this system uses it:** High-volume merchants (Apple Pay, Amazon) generate orders of magnitude more payment events than average merchants. `merchant_id` as Kafka partition key → Apple's partition receives 100x more events than others → consumer falls behind. Solution: for top-100 merchants by volume, use dedicated Kafka topic partitions. For all others, hash by `merchant_id`. Monitor partition lag: alert if any partition's lag exceeds 10K messages.

### [Write-Ahead Log (WAL)](../../Write_Ahead_Log_WAL_Crash_Recovery.md)
**Why this system uses it:** Every payment transaction write is first recorded in PostgreSQL's WAL before being applied to data pages. If the payment service crashes mid-transaction (server dies after debit recorded but before commit), WAL recovery either replays the committed debit or discards the uncommitted one — no partial writes, no corrupted balance. `synchronous_commit=on` is mandatory: the WAL must be fsynced to disk before "payment committed" is returned to the client. This is the foundation of payment atomicity — without WAL, a crash at the wrong moment could lose a committed payment or double a debit.

### [Write Skew + Phantom Reads](../../Write_Skew_Phantom_Reads_Isolation_Levels.md)
**Why this system uses it:** Double-spend prevention. Two concurrent transactions both read `balance=1000`, both attempt to debit $900. With READ COMMITTED isolation (MVCC), both succeed — each saw a consistent snapshot. Result: balance goes to $100 (or negative). Fix: `SELECT ... FOR UPDATE` on the account row serializes the reads. First transaction locks the row; second blocks until first commits. After first commits (balance=100), second reads `balance=100` and correctly rejects the overdraft. Alternative: use REPEATABLE READ + optimistic locking with version column — but write skew on phantom inserts (new debit appearing) requires SERIALIZABLE.

### [Kafka ISR & acks Replication](../../Kafka_ISR_acks_Replication_Guarantees.md)
**Why this system uses it:** Payment events published to Kafka with `acks=all + min.insync.replicas=2 + replication_factor=3`. This guarantees that at least 2 out of 3 brokers have confirmed the payment event before "success" is returned. If ISR shrinks to 1 broker (one replica falls behind), the producer gets `NotEnoughReplicasException` and retries — rather than silently succeeding with only 1 replica (which acks=all alone would allow if ISR=1). Financial audit requires: once a payment event is published, it must not be lost.

### [Kafka Log Compaction & Outbox Pattern](../../Kafka_Log_Compaction_Outbox_Pattern.md)
**Why this system uses it:** Outbox pattern for atomic payment event publishing: balance update + outbox row insertion in one PostgreSQL transaction. Debezium reads WAL → publishes PaymentProcessed event to Kafka. No 2PC, no dual-write race condition. Compacted topic for account state: `account-balances` topic (key=account_id, value=current_balance) — any new service can read the compacted topic to get current balances without querying the payments DB.

### [Redlock — Distributed Locking](../../Redlock_Distributed_Lock.md)
**Why this system uses it:** For idempotent payment retry: use PostgreSQL advisory lock (`pg_advisory_xact_lock(payment_id)`) rather than Redlock — single-DB scenario, strongest safety. For cross-shard payment locks (when two accounts are on different DB shards and need coordinated access): Redlock with 3 Redis nodes, TTL=30s. The lock prevents two concurrent transfer operations from racing on the same cross-shard account pair.

### [Long-Tail Latency — P99](../../Long_Tail_Latency_P99_Percentiles.md)
**Why this system uses it:** Checkout P99 latency directly impacts purchase abandonment. P50=20ms but P99=2s means 1% of checkouts take 2 seconds — in a busy payment system, that's thousands of failed transactions per hour. Root causes: slow DB replica serving payment reads (fix: always read account balance from primary for payment authorization), GC pauses on the payment JVM (fix: G1GC with `-XX:MaxGCPauseMillis=100`), lock contention on hot accounts (fix: backoff + retry). SLA: P99 < 300ms. Alert in Grafana on `histogram_quantile(0.99, ...) > 0.3`.

### [AWS API Gateway — REST vs HTTP vs WebSocket](../../../aws/22.api-gateway-rest-http-websocket-architect-interview.md)
**Why this system uses it:** The 29-second API Gateway hard timeout forces the async payment pattern: POST /payments returns a paymentId instantly (< 1s), a worker Lambda processes the payment (Stripe/Razorpay call can take 3–30s), and the client polls GET /payments/{id}/status. REST API (not HTTP API) is required here for Usage Plans (per-merchant rate limiting) and request transformation.

### [DynamoDB Single-Table Design + GSI Hot Partitions](../../../aws/21.dynamodb-single-table-design-gsi-hot-partitions-dax.md)
**Why this system uses it:** Payment state machine (INITIATED → PROCESSING → COMPLETED/FAILED) is a perfect DynamoDB use case: high write throughput, single access pattern (get payment by id), no complex joins. GSI trap: a `status` GSI would hot-partition on PROCESSING — use time-based composite key instead (`PK=PAYMENT#date, SK=paymentId`).

### [EventBridge — Event Routing and Scheduler](../../../aws/25.eventbridge-scheduler-event-routing-architect-interview.md)
**Why this system uses it:** Payment events use EventBridge for content-based routing: `{"detail-type":"PaymentProcessed","detail":{"status":"FAILED","amount":[{">":10000}]}}` routes only high-value failures to fraud team Lambda. Succeeded payments route to accounting, notification, and analytics targets simultaneously — one event, four targets, no code. EventBridge Scheduler for recurring jobs: daily reconciliation at 2am UTC, monthly statement generation (one-time `at()` schedule per billing cycle).

### [KMS Envelope Encryption + Secrets Manager](../../../aws/28.kms-envelope-encryption-secrets-manager-architect-interview.md)
**Why this system uses it:** Payment PII (card details, bank account numbers) uses envelope encryption — CMK encrypts DEK, DEK encrypts payment data (far exceeds 4KB KMS limit). Stripe/Razorpay API keys in Secrets Manager with quarterly auto-rotation — zero downtime rotation via AWSPENDING/AWSCURRENT staging. IRSA: payment pod → GetSecretValue → cache in memory → never log. CMK with strict key policy: only payment-service IAM role can use the key (audited via CloudTrail for PCI compliance).

### [Route53 Advanced Routing Policies](../../../aws/29.route53-routing-policies-dns-failover-architect-interview.md)
**Why this system uses it:** Failover routing for payment gateway HA — primary us-east-1, secondary eu-west-1 warm standby. Health check: HTTP GET /health/payment every 10s (fast checks). Failover timing: TTL=60 + 3×10s = 90s max. Weighted routing for payment gateway migration: 95% to current provider, 5% to new provider — gradual cutover with rollback capability.

### [Multi-Region Architecture](../../../aws/30.multi-region-aurora-global-dynamodb-global-tables.md)
**Why this system uses it:** Active-passive for payments — India RBI requires payment data stored in India (Mumbai primary). Aurora Global Database replicates to Singapore secondary (<1s lag) for AP read queries on transaction history. CRITICAL: DynamoDB Global Tables NOT suitable for payment transactions (LWW would silently lose concurrent updates to account balance). Global Accelerator for payment API — AWS backbone reduces latency for cross-border payments + sub-30s failover without DNS TTL delay.
