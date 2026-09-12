# UPI Payment Routing: VPA Resolution, Sponsor Banks, and the NPCI Switch
### How ₹500 sent from a GPay app reaches a bank account the app never even sees

---

## PART 1 — THE STUDENT CONVERSATION

Imagine you want to send a letter to a friend, but you only know their nickname, not their street address. You hand the letter to a directory-assistance office that keeps a private mapping of "nickname → real address" for millions of people. They look up the nickname, relabel the envelope with the real address, and route it through the postal system. You never learn your friend's real address, and they never learn yours — the directory service is the only party that holds both mappings.

That's exactly what a **VPA (Virtual Payment Address)** is in UPI — India's real-time payment rail. Instead of sharing your actual bank account number and IFSC code with every person who wants to pay you, you share a human-friendly alias like `alice@okhdfcbank`. When someone initiates a payment to that VPA, a central directory — NPCI's mapper service — resolves it to the real account + bank behind the scenes. Neither side ever needs to expose their actual account number to the other.

Now, who runs the app you're actually tapping buttons in — GPay, PhonePe, Paytm? Here's the twist: **none of those companies are banks**. They have no regulatory license to hold your money or directly plug into the banking network. So each of them partners with an actual licensed bank — called a **sponsor bank** — that has the real regulatory connection into NPCI's switch. Think of GPay as a travel booking website: it gives you a slick UX to search and book flights, but the actual ticket, the actual seat inventory, the actual regulatory relationship with aviation authorities belongs to the airline. GPay is the UX layer; the sponsor bank (say, ICICI or Axis) is the "airline" actually plugged into the network.

Now the money movement itself. You can't just credit the payee's account first and hope the payer's account had the money — that risks creating money that never actually existed if the debit later fails. And you can't blindly debit the payer and hope the credit succeeds — if the credit leg fails for any reason (payee's account closed, bank temporarily down), the payer's money is now stuck in limbo. So UPI uses a **two-phase debit-then-credit** flow: NPCI first asks the payer's bank "debit this account and confirm success," and *only after* that confirmation does it instruct the payee's bank to credit. If the credit leg somehow fails after the debit already succeeded, the switch doesn't leave the money "in transit" forever — it automatically triggers a **reversal credit** back to the payer, guaranteed within a defined SLA (typically by T+1 working day, often instant).

And because every leg of this journey — app to sponsor bank, sponsor bank to NPCI, NPCI to payee bank — can time out and get retried by an anxious client or an anxious server, every single hop is built around one non-negotiable rule: the **same transaction retried must never be processed twice**. That's why every transaction carries a unique reference number (RRN) that every party in the chain uses to deduplicate retries.

---

## PART 2 — THE UPI ARCHITECTURE DIAGRAMS

### Actor Flow: App → Sponsor Bank → NPCI Switch → Sponsor Bank → Account

```
Payer                     Payer's PSP App        Payer's Sponsor    NPCI UPI Switch      Payee's Sponsor     Payee's
(Bob)                     (e.g. Google Pay)       Bank (e.g. ICICI)  (Central Router)     Bank (e.g. HDFC)    Account (Alice)
  │                              │                       │                  │                   │                │
  │ "Pay alice@okhdfcbank        │                       │                  │                   │                │
  │  ₹500"                       │                       │                  │                   │                │
  ├─────────────────────────────>│                       │                  │                   │                │
  │                              │ Sign txn request w/   │                  │                   │                │
  │                              │ device fingerprint,    │                  │                   │                │
  │                              │ UPI PIN (encrypted)    │                  │                   │                │
  │                              ├──────────────────────>│                  │                   │                │
  │                              │                       │ Forward txn to   │                   │                │
  │                              │                       │ NPCI w/ RRN      │                   │                │
  │                              │                       ├─────────────────>│                   │                │
  │                              │                       │                  │ 1. RESOLVE VPA:   │                │
  │                              │                       │                  │ query NPCI Mapper  │                │
  │                              │                       │                  │ "alice@okhdfcbank" │                │
  │                              │                       │                  │ → {bank: HDFC,     │                │
  │                              │                       │                  │    acct: XXXX1234, │                │
  │                              │                       │                  │    IFSC: HDFC0001} │                │
  │                              │                       │                  │                   │                │
  │                              │                       │  <── (see Part 2 next diagram for the debit/credit legs) │
  │                              │                       │                  │                   │                │
  │      Push notification: "₹500 sent to alice@okhdfcbank — Ref: 425678901234"                                    │
  │<─────────────────────────────┴───────────────────────┴──────────────────┴───────────────────┴────────────────┤
  │                                                                                                                 │

Key point: Bob's app never sees Alice's real account number XXXX1234 — only NPCI's
mapper service resolves that, and only Alice's sponsor bank (HDFC) ever touches
the real account for the credit.
```

### Two-Phase Debit-Credit Flow with RRN Tracking

```
                    NPCI SWITCH (Central Orchestrator)
                    RRN: 425678901234  |  Amount: Rs 500.00  |  Timestamp: 2026-08-31T14:22:03Z
                              │
        PHASE 1: DEBIT REQUEST│
                              v
      ┌───────────────────────────────────────┐
      │ Payer Sponsor Bank (ICICI)             │
      │  1. Check UPI PIN valid                │
      │  2. Check account balance >= Rs 500     │
      │  3. DEBIT account, hold funds           │
      │  4. Respond: DEBIT_SUCCESS, RRN echoed  │
      └───────────────────────────────────────┘
                              │
                  DEBIT_SUCCESS ack (t + 800ms)
                              │
                              v
      NPCI logs: "Debit leg CONFIRMED for RRN 425678901234"
      ⚠ Money is now DEBITED from Bob but NOT yet credited to Alice
      ⚠ NPCI/switch is now responsible for completing or reversing this
                              │
        PHASE 2: CREDIT REQUEST│
                              v
      ┌───────────────────────────────────────┐
      │ Payee Sponsor Bank (HDFC)               │
      │  1. Validate account XXXX1234 active     │
      │  2. CREDIT account Rs 500                │
      │  3. Respond: CREDIT_SUCCESS, RRN echoed  │
      └───────────────────────────────────────┘
                              │
                 CREDIT_SUCCESS ack (t + 1400ms)
                              │
                              v
      NPCI marks RRN 425678901234 = SETTLED
      Both banks + both apps notified: transaction COMPLETE
      Total round-trip: ~1.4-2.5 seconds (NPCI SLA target: well under 10s;
      hard technical timeout ceiling ~15-30s before auto-decline/reversal)
```

### Edge Case: Credit Leg Fails After Debit Succeeds → Auto-Reversal

```
                    NPCI SWITCH — RRN: 425678901299
                              │
        PHASE 1: DEBIT REQUEST│
                              v
      Payer Sponsor Bank (ICICI): DEBIT_SUCCESS  ✓  (Bob's Rs 500 is gone)
                              │
        PHASE 2: CREDIT REQUEST│
                              v
      Payee Sponsor Bank (HDFC): ✗ TIMEOUT — bank's core banking system
                                    unresponsive for 12 seconds, OR account
                                    XXXX1234 found to be frozen/closed
                              │
                              v
      NPCI switch state: "DEBIT CONFIRMED, CREDIT UNCONFIRMED"
      ⚠ This is the dangerous middle state — money debited from Bob,
        NOT credited to Alice. Must NEVER be left unresolved.
                              │
                              v
      ┌─────────────────────────────────────────────┐
      │ AUTO-REVERSAL MECHANISM (triggered by NPCI)   │
      │  1. Detect credit leg failure/timeout for RRN │
      │  2. Generate REVERSAL transaction, same RRN   │
      │     tagged as "reversal", linked to original   │
      │  3. Instruct Payer Sponsor Bank: CREDIT BACK   │
      │     Rs 500 to Bob's account                    │
      │  4. SLA: reversal MUST complete within T+1      │
      │     working day (often automatic + near-       │
      │     instant in practice; T+1 is the outer       │
      │     regulatory ceiling, not the typical case)   │
      └─────────────────────────────────────────────┘
                              │
                              v
      Bob's app notification: "Rs 500 debited then auto-reversed —
      transaction failed, refund credited. Ref: 425678901299-R"
      NPCI marks original RRN = FAILED_REVERSED (not "pending" forever)

WHY IDEMPOTENCY MATTERS HERE: Bob's flaky mobile network causes his app to
retry the ORIGINAL payment request 3 times before getting a response. Every
sponsor bank and NPCI hop must recognize "same RRN, already processing/
processed" and return the cached result rather than debiting Bob three
times. See 012-idempotency-keys-prevent-double-processing.md — RRN here
plays exactly the role of an idempotency key at every hop in the chain.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Simplified UPI Transaction Request Payload

```json
{
  "txnId": "UPI2026083114220312345",
  "rrn": "425678901234",
  "txnType": "PAY",
  "timestamp": "2026-08-31T14:22:03.512Z",
  "payer": {
    "vpa": "bob@okicici",
    "accountRef": "ICICI-ENCRYPTED-REF",
    "deviceId": "AND-a1b2c3d4e5f6",
    "mobileNumberHash": "sha256:9f8e7d..."
  },
  "payee": {
    "vpa": "alice@okhdfcbank",
    "merchantCategoryCode": null
  },
  "amount": {
    "value": "500.00",
    "currency": "INR"
  },
  "note": "Lunch split",
  "credentials": {
    "type": "UPI_PIN",
    "encryptedBlock": "BASE64_ENCRYPTED_PIN_BLOCK"
  }
}

/* Real numbers (NPCI published UPI statistics, 2024):
   - UPI processes roughly 12-14 billion transactions per MONTH nationally
   - Average transaction value: approx Rs 1,400-1,600
   - Success rate target: >99.5% (technical decline rate closely monitored)
   - NPCI mandates response SLA per leg well under 10 seconds; hard ceiling
     before auto-timeout/auto-decline typically in the 15-30 second range
   - Reversal SLA for failed/stuck transactions: T+1 working day maximum,
     auto-reversal in practice usually completes within minutes-to-hours */
```

### VPA Resolution (Pseudocode, NPCI Mapper Lookup)

```python
def resolve_vpa(vpa: str) -> AccountBinding:
    """
    NPCI's central mapper is the ONLY entity holding vpa -> real account
    mappings. Sponsor banks register their customers' VPAs here when a
    VPA is created; they never expose the reverse mapping to other banks.
    """
    handle = vpa.split("@")[1]           # e.g. "okhdfcbank"
    issuing_bank = HANDLE_TO_BANK[handle]  # "okhdfcbank" -> HDFC Bank

    binding = npci_mapper.lookup(vpa)
    if binding is None:
        raise VPANotFoundError(f"{vpa} not registered")

    return AccountBinding(
        bank_ifsc=binding.ifsc,          # e.g. "HDFC0000001"
        account_number=binding.account,   # never returned to the payer's app —
        bank_ref=binding.internal_ref,    # only used internally by NPCI/payee bank
    )
    # Payer's app/sponsor bank receives only a CONFIRMATION that resolution
    # succeeded plus payee's display name — never the raw account number.
```

### Idempotency Enforcement at Each Hop (Java, Sponsor Bank Switch Layer)

```java
@Service
public class UpiTransactionProcessor {

    @Autowired
    private TransactionRepository transactionRepo;   // UNIQUE constraint on rrn

    @Transactional
    public TransactionResult processDebit(UpiDebitRequest request) {
        // Idempotency check FIRST — before touching the ledger
        Optional<Transaction> existing = transactionRepo.findByRrn(request.getRrn());
        if (existing.isPresent()) {
            // Retry of an already-processed request: return cached result,
            // do NOT debit again
            return TransactionResult.fromExisting(existing.get());
        }

        try {
            Transaction txn = new Transaction(request.getRrn(), DEBIT_INITIATED);
            transactionRepo.save(txn);   // UNIQUE(rrn) constraint catches races

            ledgerService.debit(request.getAccountRef(), request.getAmount());
            txn.markStatus(DEBIT_SUCCESS);
            return TransactionResult.success(txn);

        } catch (DataIntegrityViolationException dup) {
            // Two concurrent retries raced past the findByRrn check —
            // the UNIQUE constraint is the real source of truth
            Transaction winner = transactionRepo.findByRrn(request.getRrn())
                .orElseThrow();
            return TransactionResult.fromExisting(winner);
        }
    }
}

/*
CREATE TABLE transactions (
    id          BIGSERIAL PRIMARY KEY,
    rrn         VARCHAR(20) NOT NULL UNIQUE,   -- the idempotency key
    status      VARCHAR(20) NOT NULL,
    amount      NUMERIC(12,2) NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);
-- The UNIQUE(rrn) constraint is the actual enforcement mechanism;
-- the application-level check is just an optimization to skip
-- redundant ledger calls on the common-case retry.
*/
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Design the transaction processing layer for a bank acting as a sponsor bank in a UPI-like real-time payment network. Specifically: how do you handle the case where you've successfully debited the payer, but the downstream credit to the payee times out — and how do you make sure a flaky mobile client retrying the same payment three times doesn't debit the customer three times?"

**You (architect answer):**

> "These are actually two different failure classes that need two different mechanisms, and it's important not to conflate them.
>
> For the retry problem — a client retrying the same logical payment — every request carries a unique reference number, the RRN, generated once at the origin and preserved unchanged through every retry. At my layer, the very first thing the debit handler does, before touching the ledger, is check whether that RRN already exists in my transactions table. If it does, I return the cached result instead of processing again. But I don't rely on that check alone, because two retries can race each other concurrently — the real enforcement is a UNIQUE constraint on the RRN column at the database level, so even if both racing requests pass the initial check simultaneously, only one insert succeeds and the other catches the constraint violation and falls back to reading the winning row. That's the difference between an idempotency check that's a performance optimization versus one that's an actual guarantee — the guarantee has to live in the database constraint.
>
> For the debit-succeeds-credit-fails case, that's a distributed consistency problem, not a retry problem. I never leave that transaction in an ambiguous 'processing' state indefinitely. The moment the credit leg times out or comes back with a hard failure — payee account frozen, bank system down — my orchestration layer transitions the transaction to a reversal workflow: generate a linked reversal transaction against the same RRN, and credit the payer's account back. I'd set an aggressive internal SLA for this — say, attempt reversal within seconds to minutes automatically, retry the reversal itself with backoff if the payer's bank is also temporarily unavailable — well inside the regulatory outer bound of T+1 working day. The operational concern I'd flag is that the reversal path itself needs the same idempotency discipline as the original transaction — if my reversal retries, I don't want to double-credit the payer either. So the reversal transaction gets its own unique reference, linked to but distinct from the original RRN, and goes through the exact same UNIQUE-constraint-backed idempotency check before touching the ledger a second time."

---

## PART 5 — DECISION FRAMEWORK

### UPI Two-Phase Switch Routing vs. Alternative Payment Rail Patterns

| Approach | How It Works | Consistency Model | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **UPI / NPCI-style switch (debit-then-credit, two-phase)** | Central switch orchestrates: confirm debit, then instruct credit; auto-reversal on credit failure | Eventually consistent with a bounded reversal SLA; never silently stuck | ~1-3 seconds typical | Medium-High (switch must track state per RRN) | Reversal delayed if payer bank is also down; requires idempotent reversal path |
| **Card network authorization + capture (Visa/Mastercard)** | Auth reserves funds first (hold), separate capture step actually moves money, can be voided before capture | Two explicit phases with an explicit void/expiry window | Auth: ~1-2s; capture: async, hours-days later | Medium | Auth expires before capture (typically 7 days) → merchant must re-auth |
| **Batch ACH / NEFT** | Transactions queued and settled in scheduled batches (e.g. hourly net settlement windows) | Consistent only at batch settlement time, not real-time | Minutes to hours (batch-window dependent) | Low-Medium | Not real-time; a failed item in a batch requires manual reconciliation |
| **RTGS (Real-Time Gross Settlement)** | Each transaction settled individually and immediately, gross (not netted) between banks | Immediate, atomic per transaction, no batching | Seconds to a couple minutes | Medium (used for high-value transfers) | High per-transaction overhead; not designed for high-volume small-value consumer payments |
| **Blockchain/DLT settlement** | Transaction recorded on a shared ledger, finality after consensus confirmation | Eventually consistent, "final" after N confirmations | Seconds (permissioned) to minutes (public chains) | High (consensus, key management) | Confirmation delay under network congestion; no built-in reversal — finality is often irreversible by design |

### When the UPI-Style Two-Phase Switch Pattern Is Right

```
Use a central-switch, debit-then-credit, auto-reversal design when:
  ✓ You need real-time (seconds, not minutes/hours) consumer payment confirmation
  ✓ Multiple independent banks/PSPs must interoperate through one neutral router
  ✓ You cannot allow money to be "created" (credit before debit confirmed) or
    silently "lost" (debit succeeds, credit unconfirmed, no reversal)
  ✓ Retries are expected at every hop (mobile networks, bank system hiccups) and
    must be made safe via a durable, uniquely-keyed transaction reference

Skip it (use batch settlement / RTGS instead) when:
  ✗ Transaction volume is low enough that batch netting reduces settlement
    overhead without materially hurting user experience (e.g. B2B bulk payroll)
  ✗ Transaction values are large enough that real-time gross settlement's
    higher per-transaction overhead is justified for stronger settlement finality
  ✗ You're building within a single bank's own ledger (no cross-bank switch
    needed at all — just a local ACID transaction)
```

---

## QUICK REFERENCE CARD

```
UPI ACTORS:
  Payer PSP App (GPay/PhonePe) -> Payer Sponsor Bank -> NPCI Switch
    -> Payee Sponsor Bank -> Payee Account

VPA FORMAT:
  <username>@<bank-handle>   e.g. alice@okhdfcbank
  Resolved ONLY by NPCI's central mapper; real account number never
  exposed to the payer's app.

WHY A SPONSOR BANK:
  PSP apps are not banks; they have no direct NPCI switch connection.
  Sponsor bank = the licensed entity actually plugged into the network.

TWO-PHASE FLOW:
  1. DEBIT REQUEST -> payer bank confirms debit success
  2. CREDIT REQUEST -> payee bank confirms credit success
  3. If credit fails/times out after debit succeeded -> AUTO-REVERSAL
     (SLA ceiling: T+1 working day; usually much faster in practice)

IDEMPOTENCY:
  Every transaction keyed by a unique RRN.
  Enforcement = UNIQUE(rrn) DB constraint, NOT just an app-level check.
  Retried requests return the cached result, never reprocess.
  See 012-idempotency-keys-prevent-double-processing.md

REAL NUMBERS (approx, NPCI 2024 published data):
  ~12-14 billion transactions/month nationally
  Avg transaction value: ~Rs 1,400-1,600
  Per-leg SLA target: well under 10s; hard ceiling ~15-30s
  Success rate target: >99.5%
```
