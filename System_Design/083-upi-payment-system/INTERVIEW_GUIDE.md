# UPI Payment System (PhonePe / Google Pay / NPCI) — Interview Script
## Design Real Examples: PhonePe, Google Pay, Paytm, BHIM, NPCI UPI Switch
### Speak This Word-for-Word to Your Interviewer

> How to use this: This system requires India-specific knowledge most candidates lack.
> Understanding the 3-party model (PSP → NPCI → Bank) is the key differentiator.
> Read PAGE 1 carefully — the UPI architecture is fundamentally different from Stripe.

# ═══════════════ PAGE 1 — START HERE ═══════════════

## BIG PICTURE (Understand This Before Anything Else)

> **► STUDY this diagram, don't draw it ◄**
> UPI is NOT a payment processor. PhonePe/Google Pay are thin UI apps — they hold no money.
> NPCI is the central messaging switch that routes instructions between banks. The actual money
> movement happens between two banks. The PSP (app) role is: VPA resolution + message routing
> + UX. Understanding this three-layer model is what separates strong candidates from weak ones.

```
 SENDER SIDE                    NPCI SWITCH                RECEIVER SIDE
 ───────────                    ───────────                ─────────────

 User on PhonePe
   │
   │ 1. Enter VPA: "friend@oksbi"
   │    Enter amount: Rs.500
   │    Enter UPI PIN (DEVICE ONLY)
   │
   ▼
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │ PhonePe App (TPAP)                                                           │
 │                                                                              │
 │  - UPI PIN entered via device SDK (encrypted on-device, NEVER sent to PSP)  │
 │  - App sends payment request to PhonePe backend                              │
 └────────────────────────────────────────────┬─────────────────────────────────┘
                                              │
                                              ▼
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │ PhonePe PSP Backend                                                          │
 │                                                                              │
 │  1. Generate unique txnId                                                    │
 │  2. Check Redis: VPA "friend@oksbi" → {bankCode:SBI, accountNo:XXXX}        │
 │  3. Build UPI payment request message (ISO 8583 / proprietary format)       │
 │  4. Forward to Sponsor Bank (Yes Bank for PhonePe)                          │
 └────────────────────────────────────────────┬─────────────────────────────────┘
                                              │
                                              ▼
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │ Yes Bank (PhonePe's Sponsor Bank)                                            │
 │                                                                              │
 │  - Validates the request                                                     │
 │  - Forwards to NPCI Switch via IMPS/NFS network                             │
 └────────────────────────────────────────────┬─────────────────────────────────┘
                                              │
                                              ▼
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │                        NPCI SWITCH                                           │
 │                 (National Payments Corporation of India)                     │
 │                                                                              │
 │  - Routes message to receiver's bank (SBI in this case)                     │
 │  - Enforces 30-second timeout                                                │
 │  - Maintains transaction state during routing                                │
 │  - Ensures exactly-once routing with txnId deduplication                    │
 │  - Triggers auto-reversal if credit fails after debit succeeds               │
 └──────────────────────┬─────────────────────────────┬──────────────────────────┘
                        │                             │
              Debit msg │                             │ Credit msg
                        ▼                             ▼
 ┌─────────────────────────┐               ┌──────────────────────────┐
 │  Sender's Bank (HDFC)   │               │  Receiver's Bank (SBI)   │
 │                         │               │                          │
 │  Debit Rs.500 from      │               │  Credit Rs.500 to        │
 │  sender's account       │               │  receiver's account      │
 │  Verify UPI PIN         │               │  (friend@oksbi resolved  │
 │  (bank verifies)        │               │  to SBI account XXXX)    │
 └─────────────────────────┘               └──────────────────────────┘
                        │                             │
                        │ debit result                │ credit result
                        └──────────────┬──────────────┘
                                       │
                                       ▼
                           NPCI sends final result back
                           up the chain to PhonePe app
                           SUCCESS / FAILED / PENDING
```

---

## RAPID ANSWER — If You Only Have 5 Minutes

*Read this first. Understand the whole answer before going deep.*

```
"I'd design a UPI payment system with five pieces:

1. VPA Resolution Layer: A VPA (Virtual Payment Address) like 'user@oksbi' maps to a
   bank account. We cache VPA-to-bank mappings in Redis with a 5-minute TTL. On cache
   miss, we query NPCI's VPA registry. This is the first step in every payment.

2. Transaction Orchestration: The PSP backend generates a unique txnId, builds the
   UPI payment message, and forwards it to the sponsor bank. The sponsor bank routes
   it to NPCI. We persist the transaction with status INITIATED in MySQL before forwarding.

3. NPCI Routing: NPCI is the central switch — it routes debit instructions to the
   sender's bank and credit instructions to the receiver's bank. NPCI enforces a
   30-second end-to-end timeout and handles auto-reversal if credit fails after debit.

4. PIN Security (critical): The UPI PIN is entered on the user's device via a bank SDK.
   It is encrypted on-device using a key only the bank holds. The PSP NEVER sees the PIN.
   The encrypted payload goes directly from device to the bank. This is UPI's security model.

5. Status Polling and Disputes: On NPCI timeout, the PSP marks the transaction PENDING
   and polls NPCI's status API with the txnId. NPCI returns the definitive status.
   If FAILED, NPCI triggers auto-reversal. Disputes go through the CMS (Complaint
   Management System) → NPCI → bank investigation."
```

---

# ═══════════════ PAGE 2 — GLOSSARY ═══════════════

## Terminology — Know These Before Reading Further

```
┌─────────────────────────────────┬────────────────────────────────────────────────────────┐
│ Term                            │ What It Means (Simply)                                 │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ UPI                             │ Unified Payments Interface. RBI-mandated interbank      │
│                                 │ real-time payment protocol. Operates 24x7 including     │
│                                 │ weekends. Built and regulated by NPCI.                  │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ VPA (Virtual Payment Address)   │ Human-readable identifier for a bank account.           │
│                                 │ Format: user@bankhandle. E.g., 9876543210@paytm,        │
│                                 │ john@oksbi. Portable — you can change VPA's linked bank.│
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ NPCI                            │ National Payments Corporation of India. Owns the UPI    │
│                                 │ network. Acts as the central clearing switch between     │
│                                 │ banks. Not a bank itself — just a router.               │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ PSP (Payment Service Provider)  │ The company providing the UPI app. PhonePe, Google Pay, │
│                                 │ Paytm are PSPs. They do not hold money — they route     │
│                                 │ payment instructions on behalf of users.                │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ TPAP (Third Party App Provider) │ A PSP that is NOT a bank. PhonePe and Google Pay are    │
│                                 │ TPAPs. They need a sponsor bank to connect to NPCI.     │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Sponsor Bank                    │ The bank through which a TPAP connects to NPCI.         │
│                                 │ Yes Bank is PhonePe's sponsor bank. Axis Bank is        │
│                                 │ Google Pay's. Messages flow: TPAP → sponsor bank → NPCI.│
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ UPI PIN                         │ 4-6 digit PIN set by user with their bank. Used to      │
│                                 │ authorize debit. Entered on-device, encrypted by bank   │
│                                 │ SDK. PSP NEVER sees this PIN.                            │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ txnId                           │ Unique transaction reference generated by PSP. Used     │
│                                 │ throughout the system for deduplication and status       │
│                                 │ tracking. Also called RRN (Retrieval Reference Number). │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ P2P Payment                     │ Person-to-Person. Sending money to a friend's VPA.      │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ P2M Payment                     │ Person-to-Merchant. Scanning a QR code at a shop.      │
│                                 │ The QR encodes the merchant's VPA.                      │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Collect Request                 │ Merchant initiates (pull payment). Customer receives     │
│                                 │ a notification and approves with UPI PIN. Used for       │
│                                 │ e-commerce checkouts.                                   │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ UPI AutoPay (Mandate)           │ Pre-authorized recurring payment. Customer sets up a    │
│                                 │ mandate (like standing instruction). Used for SIPs,      │
│                                 │ subscriptions, EMIs. Executes without per-txn PIN.      │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ CMS (Complaint Management Sys)  │ NPCI's system for handling disputes and chargebacks.    │
│                                 │ Customer raises dispute in PSP app → forwarded to CMS   │
│                                 │ → bank investigation → resolution.                      │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Auto-Reversal                   │ If NPCI routes a debit successfully but the credit      │
│                                 │ fails, NPCI automatically initiates a debit-reversal    │
│                                 │ within T+1 day to return money to sender.               │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ IMPS                            │ Immediate Payment Service. The underlying interbank      │
│                                 │ fund transfer mechanism UPI uses. Runs 24x7, instant.  │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ T+1 Settlement                  │ Interbank settlement happens the next business day.     │
│                                 │ The user-visible credit is immediate; the actual         │
│                                 │ interbank money movement (RBI settlement) is next day.  │
└─────────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 3 — WHY EACH COMPONENT ═══════════════

## Component Choices — Why We Picked Each One

```
┌────────────────────────────┬──────────────────────────────────────────────────────────────┐
│ COMPONENT                  │ WHY THIS? NOT SOMETHING ELSE?                                │
├────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Redis for VPA Cache        │ WHY: VPA-to-bank resolution is required for every payment.   │
│ (5-min TTL)                │ At 10K TPS, querying NPCI's VPA registry for each payment   │
│                            │ would overwhelm NPCI and add 50-100ms latency per request.  │
│                            │ Redis cache serves 95%+ of VPA lookups in <1ms.             │
│                            │ 5-minute TTL balances freshness (user might change VPA's     │
│                            │ bank) vs. performance (not invalidating too often).          │
│                            │ WHY NOT longer TTL: If a user changes their VPA to a new     │
│                            │ bank, a stale 24h TTL would route payments to the wrong bank.│
│                            │ Bank returns "account not found" — payment fails. 5 min is  │
│                            │ the sweet spot: fast stale recovery, near-zero NPCI load.   │
├────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ MySQL for Transaction      │ WHY: ACID is required. A UPI payment touches: transaction    │
│ State (sharded)            │ record (INSERT), outbox event (INSERT). These must be        │
│                            │ atomic. Eventual consistency would allow a transaction to     │
│                            │ be forwarded to NPCI without a DB record — unrecoverable.   │
│                            │ Shard by txn_id hash for even distribution across peak load. │
│                            │ WHY NOT Cassandra: Cassandra's tunable consistency makes     │
│                            │ it tempting, but "eventual" means two concurrent status       │
│                            │ reads could see different states. For transaction state, we  │
│                            │ need read-your-writes consistency. MySQL InnoDB provides it. │
├────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Device SDK for UPI PIN     │ WHY: UPI's security model requires that the PIN never leave  │
│ (never sent to PSP)        │ the device unencrypted. The bank SDK on the device           │
│                            │ generates a cryptographic challenge-response using a key     │
│                            │ provisioned by the bank during UPI registration. The         │
│                            │ encrypted payload is sent directly to the bank. PSP serves  │
│                            │ only as a message conduit — it cannot decrypt the PIN.       │
│                            │ WHY NOT PSP-server-side PIN: If PSP ever saw raw PINs,       │
│                            │ a single PSP breach would compromise all customer accounts.  │
│                            │ NPCI mandates device-side PIN encryption precisely to        │
│                            │ prevent this — PSPs are not trusted with customer PINs.      │
├────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Kafka for async            │ WHY: After a payment completes, downstream actions (push     │
│ notifications              │ notification, SMS, analytics, fraud check update, loyalty    │
│                            │ points) must NOT block the payment response. A customer       │
│                            │ expects the SUCCESS/FAILURE response within 3-5 seconds       │
│                            │ (NPCI timeout is 30s). Post-payment actions run async        │
│                            │ via Kafka consumers.                                         │
│                            │ WHY NOT synchronous: Notification service failure would      │
│                            │ cause payment API to time out. Payment and notification       │
│                            │ are decoupled concerns. Kafka makes this explicit.           │
├────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Sponsor Bank as            │ WHY: NPCI does not allow TPAPs to connect directly to its    │
│ NPCI Connector             │ network. Only licensed banks (CBS-connected) can be NPCI     │
│                            │ members. TPAPs (PhonePe/GPay) must partner with a sponsor    │
│                            │ bank that serves as the regulated entry point. The sponsor   │
│                            │ bank provides the banking license, NPCI connectivity,         │
│                            │ and assumes regulatory liability for the TPAP's transactions.│
│                            │ WHY NOT direct NPCI connection: Regulatory requirement.      │
│                            │ NPCI mandates bank membership for direct connectivity.       │
│                            │ TPAPs are tech companies, not banks — they cannot hold CBS.  │
└────────────────────────────┴──────────────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 4 — FULL INTERVIEW SCRIPT ═══════════════

---

## OPENING — When Interviewer Says "Design a UPI Payment System"

"UPI is architecturally different from card payment systems. The PSP — the app like PhonePe —
holds no money and has no direct bank access. It is a routing and UX layer sitting on top of
NPCI, which is the central switch that connects 300+ Indian banks. Every payment is an interbank
message exchange with a 30-second regulatory timeout. The hardest problems are: handling NPCI
timeout ambiguity, VPA resolution at 10K TPS, and ensuring the UPI PIN never leaves the device.
Let me confirm requirements first."

---

## STEP 1 — Requirements Gathering

```
┌────────────────────────────────────────────┬──────────────────────────────────────────────┐
│ YOU ASK                                    │ INTERVIEWER SAYS (typical)                   │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ Are we building the PSP app layer or the   │ The PSP layer — like PhonePe backend.        │
│ full NPCI switch?                          │ Assume NPCI is a black box we call.          │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ What payment types: P2P, P2M, mandates?    │ All three: P2P, P2M QR, and collect requests.│
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ What scale are we targeting?               │ 10B transactions/month = ~3,800 TPS avg,     │
│                                            │ ~10K TPS peak (festival days).               │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ What's the end-to-end latency requirement? │ NPCI enforces 30 sec max. We target <5 sec   │
│                                            │ for 99% of transactions.                     │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ Do we need dispute and refund support?     │ Yes — users must be able to raise disputes   │
│                                            │ for failed/pending transactions.             │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ How do we handle NPCI timeouts?            │ Mark as PENDING, poll NPCI, resolve within   │
│                                            │ T+1 day.                                     │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ Multi-bank VPA support?                    │ Yes — user can link multiple bank accounts   │
│                                            │ to one VPA.                                  │
└────────────────────────────────────────────┴──────────────────────────────────────────────┘
```

```
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ REQUIREMENTS SUMMARY                                                                       │
├──────────────────────────────────────────────┬─────────────────────────────────────────────┤
│ FUNCTIONAL                                   │ NON-FUNCTIONAL                              │
├──────────────────────────────────────────────┼─────────────────────────────────────────────┤
│ 1. P2P payment via VPA                       │ Scale: 10B txns/month = 3,800 avg TPS      │
│ 2. P2M payment via QR code                  │ Peak: 10,000 TPS (Diwali/New Year)          │
│ 3. Collect request (pull payments)           │ Latency: <5 sec p99, 30 sec absolute max   │
│ 4. VPA registration and management           │ Availability: 99.99% (NPCI mandates this)  │
│ 5. UPI AutoPay mandates (recurring)          │ Consistency: Strong for transaction state   │
│ 6. Transaction history and status            │ Security: PIN NEVER sent to PSP            │
│ 7. Dispute and complaint management          │ Regulatory: RBI, NPCI compliance           │
│ 8. Push notifications on success/failure     │ Data retention: 7 years                    │
└──────────────────────────────────────────────┴─────────────────────────────────────────────┘
```

The key insight here: unlike card payments, UPI transactions have a MANDATORY third party (NPCI) in every flow. Your system cannot settle payments — it can only request NPCI to settle them. Design accordingly.

---

## STEP 2 — Capacity Estimation

```
TRANSACTIONS:
  10B transactions/month ÷ 30 days ÷ 86,400 sec = 3,858 TPS average
  Peak (festival days, New Year midnight): ~10,000 TPS
  Historical peak: NPCI processed 15,547 TPS during New Year 2024.

VPA RESOLUTIONS:
  Every payment requires VPA resolution = 10,000 VPA lookups/sec at peak
  Without Redis: 10K NPCI VPA queries/sec → NPCI would throttle us immediately
  With Redis (5-min TTL, ~95% hit rate): 500 NPCI queries/sec → manageable

STORAGE:
  Transaction row: ~500 bytes
  10B/month × 500 bytes = 5 TB/month
  7 years retention: 5 TB × 12 × 7 = 420 TB
  → Must shard MySQL. 10 shards × 42 TB each.
  → Cold storage (S3/GCS) for transactions older than 1 year. Query via Athena.

NPCI MESSAGE SIZE:
  UPI ISO format message: ~2 KB per transaction
  10K TPS × 2 KB = 20 MB/sec bandwidth to/from sponsor bank
  → Standard 1 Gbps link handles this with room to spare.

NOTIFICATION VOLUME:
  2 notifications per txn (sender + receiver) × 10K TPS = 20K push notifications/sec
  → Dedicated notification service with Kafka fan-out. FCM/APNS have rate limits
    — batch notifications using FCM batch API (max 500/request).
```

---

## STEP 3 — Core Entities

```
┌──────────────────────┬─────────────────────────────────────────────────────────────────┐
│ Entity               │ Key Fields                                                      │
├──────────────────────┼─────────────────────────────────────────────────────────────────┤
│ Transaction          │ txn_id (UUID PK), upi_ref_id (NPCI reference, UNIQUE),          │
│                      │ sender_vpa, receiver_vpa, amount (BIGINT paise), status (ENUM), │
│                      │ bank_response_code, created_at, settled_at, failure_reason       │
├──────────────────────┼─────────────────────────────────────────────────────────────────┤
│ VPA                  │ vpa (VARCHAR PK), user_id, bank_code, account_no, ifsc,         │
│                      │ is_primary (BOOL), created_at, last_used_at                     │
├──────────────────────┼─────────────────────────────────────────────────────────────────┤
│ User                 │ user_id (BIGINT PK), mobile_number (UNIQUE), device_id,         │
│                      │ kyc_status, created_at                                          │
├──────────────────────┼─────────────────────────────────────────────────────────────────┤
│ Mandate              │ mandate_id (UUID PK), customer_vpa, merchant_vpa,               │
│                      │ amount (BIGINT), frequency (ENUM: DAILY/WEEKLY/MONTHLY),        │
│                      │ start_date, end_date, status, umn (UNIQUE mandate number)       │
├──────────────────────┼─────────────────────────────────────────────────────────────────┤
│ Dispute              │ dispute_id (UUID PK), txn_id (FK), user_id, complaint_type,     │
│                      │ status (ENUM), cms_reference_id, raised_at, resolved_at         │
└──────────────────────┴─────────────────────────────────────────────────────────────────┘
```

KEY INSIGHT: The `upi_ref_id` is assigned by NPCI, not by us. It is globally unique across all banks and is the reference used in bank statements. Our `txn_id` is our internal identifier. Both are needed: `txn_id` for our system, `upi_ref_id` for reconciliation with banks and NPCI.

---

## STEP 4 — API Design

```
1. INITIATE P2P PAYMENT
   POST /api/v1/payments/p2p
   Request:  { "senderVpa": "alice@oksbi", "receiverVpa": "bob@paytm",
               "amount": 50000, "remarks": "Lunch split",
               "encryptedPin": "<bank-SDK-generated>", "txnId": "txn_abc123" }
   Response: { "txnId": "txn_abc123", "status": "INITIATED",
               "message": "Processing payment..." }
   Note: encryptedPin is the bank-encrypted challenge-response. PSP passes it through
         to the bank. PSP cannot decrypt this — it is opaque to us.

2. GET TRANSACTION STATUS
   GET /api/v1/transactions/{txnId}
   Response: { "txnId": "txn_abc123", "upiRefId": "306518769025", "status": "SUCCESS",
               "amount": 50000, "senderVpa": "alice@oksbi",
               "receiverVpa": "bob@paytm", "settledAt": "2024-01-15T10:30:00Z" }

3. RESOLVE VPA
   GET /api/v1/vpa/resolve?vpa=bob@paytm
   Response: { "vpa": "bob@paytm", "name": "Bob Kumar",
               "bankName": "Paytm Payments Bank", "valid": true }
   Note: PSP must verify VPA before showing confirmation screen to sender.

4. RAISE DISPUTE
   POST /api/v1/transactions/{txnId}/dispute
   Request:  { "complainType": "AMOUNT_DEBITED_NOT_CREDITED",
               "description": "Money debited but not received" }
   Response: { "disputeId": "dis_xyz789", "cmsReferenceId": "NPCI-CMS-20240115-001",
               "status": "RAISED", "expectedResolutionBy": "2024-01-17" }

5. CREATE UPI MANDATE
   POST /api/v1/mandates
   Request:  { "customerVpa": "alice@oksbi", "merchantVpa": "netflix@axisbank",
               "amount": 64900, "frequency": "MONTHLY", "startDate": "2024-02-01",
               "endDate": "2025-01-31", "purpose": "Subscription" }
   Response: { "mandateId": "...", "umn": "abc@oksbi@axisbank@MAND", "status": "PENDING_APPROVAL" }
   Note: Customer must approve via UPI PIN before mandate is ACTIVE.
```

### API JSON EXAMPLES

#### 1. POST /api/v1/payments/p2p — Initiate P2P Payment

```json
// Request:
POST /api/v1/payments/p2p
{
  "senderVpa": "alice@oksbi",
  "receiverVpa": "merchant@paytm",
  "amount": 25000,
  "remarks": "Lunch payment",
  "deviceId": "device_xyz_encrypted",
  "encryptedPin": "ENCRYPTED_PIN_BLOCK",
  "txnId": "txn_a1b2c3d4e5"
}

// Response 202 Accepted:
{
  "txnId": "txn_a1b2c3d4e5",
  "status": "INITIATED",
  "amount": 25000,
  "currency": "INR",
  "initiatedAt": "2025-01-21T13:00:00Z",
  "message": "Processing payment..."
}
```

#### 2. GET /api/v1/transactions/{txnId} — Get Transaction Status

```json
// Response 200 OK (success):
{
  "txnId": "txn_a1b2c3d4e5",
  "upiRefId": "401821012345678",
  "status": "CREDIT_SUCCESS",
  "senderVpa": "alice@oksbi",
  "receiverVpa": "merchant@paytm",
  "amount": 25000,
  "settledAt": "2025-01-21T13:00:02Z",
  "bankRespCode": "00"
}

// Response 200 OK (pending):
{
  "txnId": "txn_a1b2c3d4e5",
  "upiRefId": "401821012345678",
  "status": "PENDING",
  "amount": 25000,
  "message": "Payment is being processed. Do not retry."
}

// Response 200 OK (failed with auto-reversal):
{
  "txnId": "txn_a1b2c3d4e5",
  "status": "DEBIT_REVERSED",
  "amount": 25000,
  "bankRespCode": "Z9",
  "failureReason": "Beneficiary bank unavailable. Amount will be reversed within 24 hours."
}
```

#### 3. GET /api/v1/vpa/resolve — Resolve VPA

```json
// Response 200 OK (valid VPA):
{
  "vpa": "merchant@paytm",
  "name": "Merchant Store",
  "bankName": "Paytm Payments Bank",
  "valid": true
}

// Response 404 Not Found (invalid VPA):
{
  "vpa": "unknown@xyz",
  "valid": false,
  "error": "VPA_NOT_FOUND",
  "message": "No account linked to this VPA."
}
```

---

## STEP 5 — High-Level Architecture

> **► DRAW THIS on the whiteboard ◄**
> Draw the three tiers left to right: PSP App Layer (left), NPCI Switch (center), Bank Layer (right).
> Show the sponsor bank as the bridge between PSP and NPCI. Emphasize that the PSP has no
> direct connection to customer banks — everything goes through NPCI via the sponsor bank.

```
  ┌─────────────────────────────────────────────────────────────────────────────────────┐
  │                              CLIENT (PhonePe App)                                   │
  │         Bank SDK handles PIN encryption on device.  PSP app handles UX.            │
  └────────────────────────────────────────┬────────────────────────────────────────────┘
                                           │
                     ┌─────────────────────▼─────────────────────┐
                     │              API Gateway                  │
                     │       TLS, Device Auth, Rate Limiting     │
                     └─────────────────────┬─────────────────────┘
                                           │
              ┌────────────────────────────┼──────────────────────────┐
              │                            │                          │
              ▼                            ▼                          ▼
  ┌───────────────────────┐   ┌────────────────────────┐  ┌──────────────────────────┐
  │  VPA Resolution Svc   │   │   Transaction Svc      │  │   Mandate Service         │
  │                       │   │                        │  │                          │
  │ 1. Check Redis cache  │   │ 1. Validate request    │  │ Create/execute recurring  │
  │ 2. Miss: query NPCI   │   │ 2. Dedup by txnId      │  │ payment mandates          │
  │    VPA registry       │   │ 3. INSERT txn (INIT)   │  │ UMN lifecycle management  │
  │ 3. Cache result 5min  │   │ 4. INSERT outbox event │  └──────────────────────────┘
  └───────────────────────┘   │ 5. Return 202 Accepted │
                              └────────────┬───────────┘
                                           │
                         ┌─────────────────▼──────────────────┐
                         │         Outbox Relay               │
                         │  Polls unpublished outbox events   │
                         │  Publishes to Kafka                │
                         └─────────────────┬──────────────────┘
                                           │
                         ┌─────────────────▼──────────────────┐
                         │    Kafka: payment.commands         │
                         │    Partitioned by sender_vpa       │
                         └─────────────────┬──────────────────┘
                                           │
                         ┌─────────────────▼──────────────────┐
                         │       NPCI Gateway Service         │
                         │                                    │
                         │ 1. UPDATE txn → PROCESSING        │
                         │ 2. Build ISO/UPI message           │
                         │ 3. Send to Sponsor Bank API        │
                         │ 4. Sponsor Bank → NPCI Switch      │
                         └─────────────────┬──────────────────┘
                                           │
                    ┌──────────────────────▼─────────────────────┐
                    │              NPCI SWITCH                   │
                    │  Routes to sender bank (debit)             │
                    │  Routes to receiver bank (credit)          │
                    │  Returns: SUCCESS / FAILED / TIMEOUT       │
                    └──────────────────────┬─────────────────────┘
                                           │
                         ┌─────────────────▼──────────────────┐
                         │       Response Handler             │
                         │                                    │
                         │ SUCCESS → UPDATE txn CREDIT_SUCCESS│
                         │           publish payment.success  │
                         │ FAILED  → UPDATE txn FAILED        │
                         │           publish payment.failed   │
                         │ TIMEOUT → UPDATE txn PENDING       │
                         │           schedule status poll     │
                         └─────────────────┬──────────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
              ▼                            ▼                            ▼
  ┌────────────────────┐   ┌──────────────────────────┐   ┌────────────────────────┐
  │   MySQL Cluster    │   │   Notification Service   │   │   Analytics Service    │
  │   (sharded 10x)    │   │   FCM/SMS via Kafka      │   │   ClickHouse           │
  │   transactions     │   │   2 notifs per txn       │   │   fraud signals        │
  │   vpa_registry     │   └──────────────────────────┘   └────────────────────────┘
  │   mandates         │
  │   disputes         │
  └────────────────────┘
```

---

> **► DRAW THIS on the whiteboard ◄**

## STEP 5b — UPI PAYMENT SEQUENCE DIAGRAM

```
  Sender App    PhonePe PSP    Sponsor Bank    NPCI Switch   Receiver Bank
      │               │               │               │               │
      │ Enter VPA     │               │               │               │
      │ amount + PIN  │               │               │               │
      │──────────────▶│               │               │               │
      │               │ Resolve VPA   │               │               │
      │               │ (Redis cache / NPCI lookup)   │               │
      │               │──────────────────────────────▶│               │
      │               │◀──────────────────────────────│               │
      │               │  {bank=HDFC, acct=xxxx}       │               │
      │               │               │               │               │
      │               │ BEGIN TX: INSERT txn(INITIATED) + outbox       │
      │               │ COMMIT                        │               │
      │               │               │               │               │
      │ 202 ACCEPTED  │               │               │               │
      │ status=INIT   │               │               │               │
      │◀──────────────│               │               │               │
      │               │               │               │               │
      │               │ Outbox relay → Kafka → NPCI Gateway Service   │
      │               │               │               │               │
      │               │ Initiate txn  │               │               │
      │               │──────────────▶│               │               │
      │               │               │ DEBIT_REQUEST │               │
      │               │               │──────────────▶│               │
      │               │               │               │ CREDIT_REQUEST│
      │               │               │               │──────────────▶│
      │               │               │               │◀──────────────│
      │               │               │               │  CREDIT_OK    │
      │               │               │◀──────────────│               │
      │               │               │  TXN_SUCCESS  │               │
      │               │◀──────────────│               │               │
      │ SUCCESS +     │               │               │               │
      │ ref_id shown  │               │               │               │
      │◀──────────────│               │               │               │
      │               │               │               │               │
      │               │ ─ ─ ─ ─ ─ ─ TIMEOUT SCENARIO (30s) ─ ─ ─ ─ ─│
      │               │               │               │               │
      │ TXN_PENDING   │               │               │               │
      │◀──────────────│               │               │               │
      │               │ Poll NPCI for status (with txnId)             │
      │               │──────────────────────────────▶│               │
      │               │◀──────────────────────────────│               │
      │               │  {FAILED / SUCCESS}           │               │
      │               │ NPCI triggers auto-reversal if DEBIT happened  │
```

---

## STEP 6 — Database Schema

> **► DRAW THIS on the whiteboard ◄**

```
TABLE: transactions
┌────────────────────┬──────────────────────┬────────────────────────────────────────────────┐
│ Column             │ Type                 │ Notes                                          │
├────────────────────┼──────────────────────┼────────────────────────────────────────────────┤
│ txn_id             │ VARCHAR(36) UUID PK  │ PSP-generated. Internal identifier.            │
│ upi_ref_id         │ VARCHAR(50) UNIQUE   │ NPCI-assigned. Used in bank statements.        │
│                    │                      │ NULL until NPCI responds.                      │
│ sender_vpa         │ VARCHAR(100)         │ Indexed. For "my payment history" queries.     │
│ receiver_vpa       │ VARCHAR(100)         │ Indexed.                                       │
│ amount             │ BIGINT NOT NULL      │ In paise. Rs.500 = 50000.                      │
│ status             │ ENUM NOT NULL        │ INITIATED, DEBIT_ATTEMPT, DEBIT_SUCCESS,       │
│                    │                      │ CREDIT_ATTEMPT, CREDIT_SUCCESS,                │
│                    │                      │ DEBIT_REVERSED, FAILED, PENDING, TIMEOUT       │
│ bank_response_code │ VARCHAR(10)          │ NPCI/bank response code. 00=success.           │
│ failure_reason     │ VARCHAR(255)         │ Human-readable failure description.            │
│ device_id          │ VARCHAR(100)         │ Device that initiated. For fraud detection.    │
│ ip_address         │ VARCHAR(45)          │ Hashed for privacy. Fraud signal.              │
│ created_at         │ TIMESTAMP            │ Shard this table by MONTH(created_at) +        │
│ settled_at         │ TIMESTAMP NULL       │ HASH(txn_id) for even distribution.            │
└────────────────────┴──────────────────────┴────────────────────────────────────────────────┘

SHARD KEY: HASH(txn_id) % 10  → 10 shards for write distribution
INDEX: (sender_vpa, created_at DESC)    → "show my sent payments"
INDEX: (receiver_vpa, created_at DESC)  → "show payments received"
INDEX: (status, created_at) WHERE status IN ('PENDING','TIMEOUT') → pending txn poller

TABLE: vpa_registry
┌────────────────────┬──────────────────────┬────────────────────────────────────────────────┐
│ Column             │ Type                 │ Notes                                          │
├────────────────────┼──────────────────────┼────────────────────────────────────────────────┤
│ vpa                │ VARCHAR(100) PK      │ e.g., "alice@oksbi". Case-insensitive stored   │
│                    │                      │ as lowercase.                                  │
│ user_id            │ BIGINT               │ FK to users. Who owns this VPA.               │
│ bank_code          │ VARCHAR(10)          │ NPCI bank member code. e.g., "SBI", "HDFC".   │
│ account_no         │ VARCHAR(20)          │ Encrypted at rest. Partial (last 4) for display│
│ ifsc               │ CHAR(11)             │ Branch-level bank identifier.                  │
│ is_primary         │ BOOLEAN              │ User's default VPA for receive.                │
│ is_active          │ BOOLEAN              │ Soft-delete. NPCI VPA deregistration.          │
│ created_at         │ TIMESTAMP            │                                                │
│ updated_at         │ TIMESTAMP            │ On bank change — triggers Redis invalidation.  │
└────────────────────┴──────────────────────┴────────────────────────────────────────────────┘

TABLE: mandates
┌────────────────────┬──────────────────────┬────────────────────────────────────────────────┐
│ Column             │ Type                 │ Notes                                          │
├────────────────────┼──────────────────────┼────────────────────────────────────────────────┤
│ mandate_id         │ VARCHAR(36) UUID PK  │                                                │
│ umn                │ VARCHAR(50) UNIQUE   │ Unique Mandate Number. NPCI-issued.           │
│ customer_vpa       │ VARCHAR(100)         │ Who pays.                                      │
│ merchant_vpa       │ VARCHAR(100)         │ Who receives.                                  │
│ amount             │ BIGINT               │ Fixed per execution. In paise.                 │
│ frequency          │ ENUM                 │ DAILY, WEEKLY, MONTHLY, YEARLY, ON_DEMAND      │
│ start_date         │ DATE                 │                                                │
│ end_date           │ DATE                 │                                                │
│ status             │ ENUM                 │ PENDING_APPROVAL, ACTIVE, PAUSED, CANCELLED    │
│ last_executed_at   │ TIMESTAMP            │ For determining next execution.                │
└────────────────────┴──────────────────────┴────────────────────────────────────────────────┘

REDIS KEY SCHEMA:
  vpa:{vpa_lowercased}           → JSON{bankCode, accountNo, ifsc, userName} (TTL: 5 min)
  txn_dedup:{txnId}              → "1" (TTL: 24h, prevents duplicate submission to NPCI)
  user_velocity:{userId}:{date}  → transaction count (TTL: midnight, fraud rate limiting)
  pending_poll:{txnId}           → retryCount (TTL: 24h, tracks polling attempts)
```

---

> **► DRAW THIS on the whiteboard ◄**

## ER RELATIONSHIP DIAGRAM

```
┌──────────────────────────────────────────────────────────────────┐
│                  UPI SYSTEM — ENTITY RELATIONSHIP                 │
└──────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌────────────────────┐
│    users     │         │   vpa_registry      │
├──────────────┤         ├────────────────────┤
│ PK user_id   │◄────── │ PK vpa VARCHAR     │
│    phone TEXT│  1   N  │ FK user_id BIGINT  │
│    name TEXT │         │    bank_code VARCHAR│
│    kyc_status│         │    account_no TEXT  │
└──────────────┘         │    ifsc VARCHAR     │
                         │    is_primary BOOL  │
                         └────────────────────┘
                                   │
                                   │ (sender_vpa / receiver_vpa)
                                   │
                         ┌─────────▼──────────────────────┐
                         │         transactions             │
                         ├────────────────────────────────┤
                         │ PK txn_id         UUID         │
                         │    upi_ref_id     VARCHAR UNIQ │
                         │    sender_vpa     VARCHAR       │
                         │    receiver_vpa   VARCHAR       │
                         │    amount         BIGINT(paise) │
                         │    status         ENUM          │
                         │    bank_resp_code VARCHAR       │
                         │    initiated_at   TIMESTAMP     │
                         │    settled_at     TIMESTAMP     │
                         └──────────┬─────────────────────┘
                                    │ 1
                                    │ N
                         ┌──────────▼─────────────────────┐
                         │       dispute_cases             │
                         ├────────────────────────────────┤
                         │ PK dispute_id UUID             │
                         │ FK txn_id UUID                 │
                         │ FK raised_by user_id           │
                         │    reason ENUM                 │
                         │    status ENUM                 │
                         │    raised_at TIMESTAMP         │
                         │    resolved_at TIMESTAMP       │
                         └────────────────────────────────┘

                         ┌────────────────────────────────┐
                         │           mandates              │
                         ├────────────────────────────────┤
                         │ PK mandate_id UUID             │
                         │    umn VARCHAR UNIQUE          │
                         │    customer_vpa VARCHAR        │
                         │    merchant_vpa VARCHAR        │
                         │    amount BIGINT               │
                         │    frequency ENUM              │
                         │    status ENUM                 │
                         │    start_date DATE             │
                         │    end_date DATE               │
                         └────────────────────────────────┘
```

---

## STEP 7 — Deep Dive: UPI Payment Flow End-to-End

Know this sequence cold. It is the most common deep-dive question for UPI system design.

```
STEP-BY-STEP UPI P2P PAYMENT (Alice pays Bob Rs.500)

T+0ms: Alice opens PhonePe, enters "bob@paytm", Rs.500, taps "Pay"

T+10ms: PhonePe app:
  - App calls backend: POST /payments with senderVpa=alice@oksbi, receiverVpa=bob@paytm,
    amount=50000, txnId=txn_abc (client-generated)
  - Device SDK displays PIN keyboard — bank SDK, not PhonePe UI

T+20ms: Alice enters UPI PIN:
  - Device SDK encrypts PIN using bank's public key (key provisioned during UPI registration)
  - Produces encryptedCredential = Encrypt(PIN + timestamp + deviceId + txnId, bankPubKey)
  - This encrypted blob is sent to PhonePe backend — PhonePe CANNOT decrypt it

T+30ms: PhonePe backend:
  - Check Redis: txnId=txn_abc → not found (new txn) → proceed
  - Resolve "bob@paytm": Redis HIT → {bank: Paytm Payments Bank, accNo: XXXX}
  - BEGIN MySQL TX:
      INSERT transaction(txn_id=txn_abc, status=INITIATED, ...)
      INSERT outbox_event(txn_id=txn_abc, published=false)
    COMMIT
  - Store in Redis: txn_dedup:txn_abc → "1" (TTL 24h, prevent duplicate submission)
  - Return 202 Accepted to PhonePe app

T+50ms: Outbox relay publishes txn_abc to Kafka → NPCI Gateway Service consumes

T+60ms: NPCI Gateway Service:
  - UPDATE transaction status → DEBIT_ATTEMPT
  - Build UPI message: {txnId, senderVpa, receiverVpa, amount, encryptedCredential}
  - Send to Yes Bank (PhonePe's sponsor bank) via mutual TLS API

T+100ms: Yes Bank → NPCI Switch:
  - Yes Bank validates request format, forwards to NPCI

T+150ms: NPCI Switch routes to Alice's bank (HDFC):
  - "Debit Alice's account linked to alice@oksbi by Rs.500"
  - HDFC verifies encryptedCredential (decrypts with its own private key, validates PIN)
  - HDFC debits Alice's account
  - Returns SUCCESS to NPCI

T+300ms: UPDATE transaction status → DEBIT_SUCCESS

T+350ms: NPCI Switch routes credit to Bob's bank (Paytm Payments Bank):
  - "Credit Bob's account linked to bob@paytm by Rs.500"
  - Paytm Bank credits Bob's account
  - Returns SUCCESS to NPCI

T+500ms: NPCI returns final SUCCESS to Yes Bank → Yes Bank → PhonePe backend:
  - Response includes upi_ref_id (NPCI reference number)
  - UPDATE transaction: status=CREDIT_SUCCESS, upi_ref_id=30651876..., settled_at=NOW()
  - Publish to Kafka: payment.success topic
  - Push notifications sent async to Alice and Bob

T+600ms: PhonePe app receives push notification: "Payment of Rs.500 to Bob successful!"
  - App polls GET /transactions/txn_abc → status=CREDIT_SUCCESS → shows success screen

TOTAL ELAPSED: ~600ms end-to-end for a successful payment

┌──────────────────────────────────────────────────────────────────────────────┐
│ PAYMENT STATE MACHINE                                                        │
│                                                                              │
│  INITIATED → DEBIT_ATTEMPT → DEBIT_SUCCESS → CREDIT_ATTEMPT               │
│                                    │               │                         │
│                                    │           CREDIT_SUCCESS (terminal)    │
│                                    │           CREDIT_FAILED                │
│                                    │               │                         │
│                                    │        DEBIT_REVERSED (NPCI auto)      │
│                            DEBIT_FAILED (terminal)                          │
│                                                                              │
│  Any state can → TIMEOUT (NPCI timeout) → PENDING (polling)                │
│  PENDING → CREDIT_SUCCESS or DEBIT_REVERSED (after polling)                │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## STEP 8 — Scalability

```
BOTTLENECK 1: 10K TPS peak — NPCI Gateway Service becomes throughput bottleneck
  PROBLEM: NPCI has a fixed throughput ceiling. PhonePe cannot exceed NPCI's capacity.
    Our backend must not add latency to the 30-second NPCI budget.
  SOLUTION:
    1. Stateless NPCI Gateway Service — horizontal scaling to 50+ pods during peak.
    2. Dedicated connection pool to sponsor bank API (persistent TLS connections, avoid
       handshake overhead on each request). Connection pool = 100 connections per pod.
    3. Kafka partitioned by sender_vpa: ensures payments from same user are ordered,
       preventing out-of-order processing. 100 partitions = 100 parallel consumers.
    4. Redis pipeline for dedup check + TTL set in single round-trip (sub-millisecond).
  RESULT: Horizontally scalable to NPCI's actual limit. PhonePe is NOT the bottleneck.

BOTTLENECK 2: VPA resolution at 10K/sec
  PROBLEM: Without caching, 10K VPA lookups/sec would hammer NPCI's VPA registry API.
    NPCI rate-limits PSPs — exceeding quota causes throttling and payment failures.
  SOLUTION:
    1. Redis cache: vpa:{vpa} → bankInfo (TTL 5 min). At 95% hit rate → 500 NPCI calls/sec.
    2. Write-through on VPA updates: when a user changes their VPA's linked bank in our app,
       immediately invalidate Redis: DEL vpa:{vpa}. Next lookup refreshes from NPCI.
    3. Pre-warm cache: nightly batch job refreshes top 1M frequently-used VPAs in Redis.
       Reduces cold-start penalty after Redis restart.
  RESULT: NPCI VPA registry sees <5% of our peak traffic. No throttling risk.

BOTTLENECK 3: MySQL transaction table growth (420 TB over 7 years)
  PROBLEM: 420 TB across 10 shards = 42 TB per shard. Queries on sender_vpa index
    for "show my transaction history" would scan large index ranges.
  SOLUTION:
    1. Table partitioning by MONTH: each shard has monthly partitions (84 partitions
       over 7 years). "Recent transactions" query only scans current-month partition.
    2. Tiered storage: transactions older than 12 months are archived to S3 in Parquet
       format. Queries on old data use Athena (S3 SQL) — not MySQL. Users rarely
       need > 12 months of history.
    3. Hot shard mitigation: shard by HASH(txn_id) % 10, NOT by user_id.
       Sharding by user_id would hot-spot the shard for viral merchants (Flipkart VPA
       receiving millions of payments). Hash sharding distributes evenly.
  RESULT: Each MySQL shard handles only recent 12 months (~42 GB/month × 12 = 500 GB).

BOTTLENECK 4: Pending transaction poller at scale
  PROBLEM: NPCI timeouts leave transactions in PENDING state. We must poll NPCI status API
    to resolve them. At 0.1% timeout rate × 10K TPS = 10 PENDING transactions/sec.
    After 24 hours: 864,000 pending transactions need resolution polling.
  SOLUTION:
    1. Delayed queue in Redis: ZADD pending_txns {timestamp+30s} {txnId}.
       Separate poller service: ZRANGEBYSCORE pending_txns 0 {now} → poll NPCI.
    2. Exponential backoff: poll at 30s, 1min, 5min, 15min, 1hr intervals.
    3. Max retries: after 24 hours with no resolution → mark TIMEOUT (terminal),
       alert ops, flag for manual resolution via CMS.
    4. NPCI status API is idempotent: polling with same txnId is safe. Bank-side
       deduplication ensures no double processing.
  RESULT: Pending transactions resolved within minutes in 99% of cases. Manual
    intervention only for genuine bank-side issues.
```

---

## WHAT NOT TO SAY ✗

```
✗ "The PSP (PhonePe) stores and verifies the UPI PIN"
  Why wrong: This is a critical security misunderstanding and an instant fail.
  The UPI PIN is entered via a bank-provided device SDK. It is encrypted on-device
  using a key ONLY the customer's bank holds. PhonePe/Google Pay NEVER see the PIN.
  They are opaque conduits for an encrypted blob. If a PSP ever stored PINs, a single
  breach would compromise every linked bank account for all users.

✗ "The PSP directly accesses customer bank accounts"
  Why wrong: PSPs have zero direct access to bank accounts. The flow is strictly:
  PSP → Sponsor Bank → NPCI → Customer's Bank. The PSP sends a payment instruction
  to NPCI; NPCI instructs the bank; the bank executes the debit. PSPs cannot read
  balances or initiate debits independently. They are message-routing intermediaries.

✗ "Use Cassandra for transaction storage — it handles high write throughput"
  Why wrong: UPI transactions require ACID for exactly-once semantics. The txnId
  deduplication check (SELECT + INSERT must be atomic) cannot be expressed in Cassandra's
  data model without application-level locking. Use sharded MySQL. Cassandra is for
  append-only, idempotent workloads — payment state transitions are neither.

✗ "Real-time settlement means the banks settle money instantly"
  Why wrong: From the USER's perspective, the credit appears instant. But interbank
  settlement (the actual movement of reserves between banks at RBI) is T+1 (next business
  day). The immediate credit the user sees is an internal bank credit pending final RBI
  settlement. NPCI runs net settlement with RBI daily. This distinction matters for
  reconciliation: your ledger vs. the bank's statement may differ by a day's transactions.

✗ "If NPCI times out, retry the original payment"
  Why wrong: Retrying the original payment initiation risks double-debit. The bank may
  have already processed the debit. Always use the status-query API with the original
  txnId (idempotent). NPCI will return the definitive status of the original attempt.
  Only after confirmed FAILED (never PENDING) should you consider a new payment.

✗ "VPA is tied to a phone number and cannot be changed"
  Why wrong: VPA is a portable identifier. A user can change the bank account linked
  to their VPA at any time (e.g., switch from Yes Bank to SBI while keeping @oksbi VPA).
  This is why the Redis VPA cache TTL is only 5 minutes — stale mappings cause
  "account not found" errors. The portability is a feature, not a bug.

✗ "Use 2PC across NPCI, sender bank, and receiver bank"
  Why wrong: NPCI, sender bank, and receiver bank are independent systems operated by
  different organizations. None support PREPARE-phase locking for external coordinators.
  NPCI's model is: route the message, return the result. Auto-reversal is the compensating
  mechanism, not 2PC rollback.
```

---

## SENIOR TRAP QUESTIONS (15 YOE Level)

### Category 1: Failure Handling

**Q: NPCI returns TIMEOUT (no response within 30 seconds). Alice's money may or may not have been debited. What does your system do, step by step?**

A: First, we immediately update the transaction status to PENDING in MySQL and notify Alice in the
app: "Payment is being processed — do not retry." We push the txnId onto a Redis sorted set with
score = current_timestamp + 30_seconds (delayed retry queue). The pending-poller service wakes up,
pulls this txnId, and calls NPCI's status query API with the original txnId — this is an idempotent
query and safe to call repeatedly. If NPCI returns SUCCESS: we update our DB to CREDIT_SUCCESS and
notify Alice and Bob with success messages. If NPCI returns FAILED: we update to FAILED, confirm
no debit occurred (or trigger reversal request), and allow Alice to retry. If NPCI returns PENDING
again (bank is still processing): backoff exponentially — retry at 30s, 1min, 5min, 15min, 1hr.
After 24 hours without resolution: mark as TIMEOUT_FINAL, alert ops, flag for CMS dispute creation.
Critical point: we NEVER create a new payment for Alice during this window. We only poll status of
the existing txnId. Bank-side idempotency on txnId ensures no double charge on the original attempt.

**Q: Debit succeeded (Alice's Rs.500 was debited) but the credit to Bob failed (Bob's bank is down). What does NPCI do, and what does your system do?**

A: NPCI handles this with auto-reversal — this is a built-in NPCI guarantee. When NPCI cannot credit
the receiver after a successful debit, it initiates a DEBIT_REVERSAL instruction to Alice's bank within
T+1 day (typically within hours). Alice's bank credits Rs.500 back to Alice's account. Our system
receives the DEBIT_REVERSAL callback from NPCI. We update the transaction status to DEBIT_REVERSED
(terminal state) and send Alice a notification: "Payment failed. Rs.500 has been refunded to your
account within 24-48 hours." The key principle: we do NOT attempt to re-credit Bob ourselves. NPCI
manages the atomicity of debit-credit pairs. Our role is to record the state and notify the user.
If the auto-reversal also fails (very rare), this becomes a CMS dispute that operations teams handle
with the bank directly.

---

### Category 2: Security and Fraud

**Q: A fraudster registers a device with a stolen SIM card, adds the victim's bank account to Google Pay, and tries to generate a collect request. How does UPI prevent this?**

A: UPI has two device-binding defenses. First, device binding: when a user registers a UPI account,
the app sends an SMS from the device — this verifies that the SIM card is physically in that device.
The bank registers the device's unique IMEI + SIM combination. A different device with the same number
would require re-registration (which requires an OTP to the registered number). Second, for collect
requests (pull payments): the customer must APPROVE the collect request using their UPI PIN. The PIN
is verified by the bank via the encrypted challenge from the bank SDK installed on the registered device.
A fraudster on a different device cannot generate the correct encrypted challenge — they don't have the
cryptographic key provisioned on the victim's registered device. Third, PSP-level velocity checks:
new device registrations triggering high-value collect approvals within minutes is a fraud signal.
We would flag this transaction for manual review and send an out-of-band SMS alert to the registered
mobile number warning the customer.

**Q: You see a sudden spike to 50,000 TPS — 5x your normal peak. How do you distinguish legitimate Diwali traffic from a DDoS or fraudulent payment flood?**

A: We approach this in three layers. First, rate limiting at the API Gateway level: per-user limits
(max 20 payments/minute per VPA), per-device limits (max 5 payments/minute per device_id), and
per-IP limits. Legitimate Diwali traffic is distributed across millions of users — a spike in total
TPS with normal per-user distribution is genuine. A DDoS or fraud burst shows high concentration
on a small set of source IPs or device_ids. Second, real-time fraud signals: Kafka click stream
feeds a Flink streaming job. We compute: transaction velocity per VPA (last 5 min), amount
distribution (sudden spike in Rs.1 test transactions is card enumeration), and new device + new VPA
combination. Third, NPCI coordination: NPCI publishes real-time TPS capacity. If we are approaching
NPCI's limit, we implement backpressure — queue excess payments in Kafka with a processing delay
rather than dropping them. This prevents NPCI throttling while still serving legitimate users.
Fraudulent patterns (concentrated source, test amounts, new devices) are rejected before reaching
NPCI to preserve capacity for legitimate traffic.

---

### Category 3: Operations and Compliance

**Q: You are doing a post-mortem of an incident where 10,000 transactions were marked FAILED in your system but the corresponding bank debits DID happen (money left customer accounts but was never credited). How did this happen and how do you make customers whole?**

A: The root cause is a gap in the NPCI callback handling. Most likely scenario: NPCI sent the SUCCESS
callback, but our NPCI Gateway Service had a transient failure (pod restart, DB connection timeout)
that prevented updating transaction status. NPCI's callback is fire-and-forget — if we return a
non-200, NPCI may not retry. Result: bank has SUCCESS, we have FAILED. Detection: nightly reconciliation
compares our FAILED transactions list against NPCI's settlement file (which NPCI provides daily as a
CSV). Any transaction in NPCI's SUCCESS list but in our FAILED list is a discrepancy. Resolution path:
(1) Cross-reference NPCI settlement file against our transactions table. (2) For each discrepancy:
pull NPCI status API with txnId to confirm STATUS=SUCCESS at NPCI level. (3) Credit the receiver's
account (if not already credited — check bank statement). (4) Update our transaction to CREDIT_SUCCESS,
log a correction event for audit. (5) Notify affected customers proactively. Prevention: implement
NPCI callback idempotency receiver with acknowledgment persistence — write the acknowledgment to
the outbox table before responding 200 to NPCI.

---

## KEY NUMBERS — Memorize These

```
┌────────────────────────────────────────────────┬────────────────────────────────────────────┐
│ Metric                                         │ Value                                      │
├────────────────────────────────────────────────┼────────────────────────────────────────────┤
│ UPI transactions/month (2024)                  │ 10 billion+                                │
│ Average TPS                                    │ ~3,858 TPS                                 │
│ Peak TPS (festival days)                       │ ~10,000 TPS                                │
│ Recorded peak TPS (New Year 2024)              │ 15,547 TPS (NPCI reported)                 │
│ NPCI end-to-end timeout                        │ 30 seconds (hard regulatory limit)         │
│ Typical successful payment latency             │ 300ms – 5 seconds                          │
│ VPA cache TTL (Redis)                          │ 5 minutes                                  │
│ Transaction dedup key TTL (Redis)              │ 24 hours                                   │
│ Interbank settlement (T+1)                     │ Next business day at RBI                   │
│ Data retention requirement                     │ 7 years (RBI mandate)                      │
│ Amount storage format                          │ BIGINT in paise (1 rupee = 100 paise)      │
│ Pending transaction polling: max window        │ 24 hours, then escalate to CMS             │
│ Notifications per transaction                  │ 2 (sender + receiver)                      │
│ Storage per transaction row                    │ ~500 bytes                                 │
│ Total storage (7 year retention)               │ ~420 TB (across 10 MySQL shards)           │
│ Banks connected to NPCI UPI                    │ 300+ banks                                 │
│ UPI market share (PhonePe 2024)                │ ~48% of all UPI transactions               │
└────────────────────────────────────────────────┴────────────────────────────────────────────┘
```

*Study order hint: Master the 3-tier architecture (PSP → Sponsor Bank → NPCI → Banks) first —
this is what most candidates get wrong. Then learn the PIN security model (device SDK, PSP never
sees PIN). Then practice the TIMEOUT handling sequence in STEP 7. The WHAT NOT TO SAY section
has five instant-fail items unique to UPI — review them the morning of the interview.*
