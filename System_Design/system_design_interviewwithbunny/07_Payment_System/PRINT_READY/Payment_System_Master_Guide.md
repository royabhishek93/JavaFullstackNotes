# Payment System Design — Master Interview Guide (Gateway + Processing)
Complete combined guide: gateway architecture, PCI tokenization, state machine, idempotency, failure handling, reconciliation, and 15-year closing answers.

Print settings: Landscape mode, monospace font (Courier New/Consolas 9-10pt), narrow margins.

---

## BEGINNER PRIMER — READ THIS FIRST (NEW LEARNERS START HERE)

### What is a Payment System?

When you buy something online, money moves from your bank account to the merchant's bank account.
This sounds simple but involves many systems talking to each other in under a second.
A Payment System is the set of services that orchestrate this money movement safely, correctly, and at scale.

### The Key Players (Plain English)

```text
You (Customer)       : the person paying
Merchant             : the shop/website receiving money (e.g. Amazon, Flipkart)
Payment Gateway      : the middleman that collects your card details securely,
                       checks fraud, and routes the payment to the right processor.
                       Think of it as the "traffic controller" of payments.
Payment Processor    : the company that actually talks to your bank and the card
                       network (Visa/Mastercard) to move the money.
                       Examples: Razorpay, Stripe, PayU (they are gateways AND processors).
Card Network         : Visa, Mastercard, RuPay — the rails connecting all banks globally.
Issuing Bank         : YOUR bank (the one that gave you the card). It approves/declines.
Acquiring Bank       : the MERCHANT's bank (receives the money on merchant's behalf).
PSP                  : Payment Service Provider — umbrella term for gateway + processor combined.
```

### Money Flow in Plain English

```text
Step 1: You click "Pay Now" on Amazon.
Step 2: Amazon's checkout page (or a gateway-hosted page) collects your card number.
Step 3: The gateway tokenizes your card (replaces card number with a safe token).
Step 4: The gateway sends the token to the processor.
Step 5: The processor asks Visa/Mastercard: "Is this card valid? Does the customer have funds?"
Step 6: Visa/Mastercard asks your issuing bank: "Approve or decline?"
Step 7: Your bank says "Approved" (or "Declined").
Step 8: The response travels back: bank -> card network -> processor -> gateway -> merchant -> you.
Step 9: Money is not moved instantly. It is "authorized" now and "settled" in 1-2 days.
```

### Glossary — Every Term Explained Simply

```text
Idempotency        : Doing the same action multiple times gives the same result once.
                     Example: if your internet cuts off after clicking "Pay", and your app
                     retries — idempotency ensures you are NOT charged twice.

Tokenization       : Replacing sensitive card data (card number/CVV) with a random token.
                     The real card data is stored only in a secure vault. The token is useless
                     to a hacker because it cannot be used to charge a card directly.

PCI DSS            : Payment Card Industry Data Security Standard. A set of strict rules
                     any system that handles card data must follow. If you store raw card
                     numbers without PCI compliance, you can be fined or lose the ability
                     to process cards.

HSM                : Hardware Security Module. A physical tamper-proof device that encrypts
                     card data. Even if a hacker gets inside your server, the HSM keys
                     cannot be extracted. Banks and gateways use HSMs for tokenization.

BIN                : Bank Identification Number. The first 6 digits of a card number.
                     Tells you which bank issued the card and what type (credit/debit/prepaid).

State Machine      : A way to model what "states" an object can be in and what transitions
                     are allowed. Example: a payment can go from CREATED -> PROCESSING ->
                     CAPTURED. It cannot jump from CREATED directly to REFUNDED.
                     State machines prevent invalid transitions (e.g. charging a cancelled order).

Idempotency Key    : A unique ID sent by the client with every request. If the same request
                     is sent twice (due to retry), the server detects the same key and returns
                     the original response without doing the action again.

Reconciliation     : The process of comparing what YOUR system recorded vs what the bank/PSP
                     recorded. Like balancing a checkbook. Done daily to catch any mismatch
                     (e.g. PSP charged the customer but your system shows "failed").

Webhook            : A callback. When the PSP finishes processing a payment, it sends an HTTP
                     POST to your server saying "payment succeeded" or "payment failed".
                     Your system must verify the webhook is genuine (signature check) and
                     handle duplicates (PSPs often send the same webhook more than once).

Circuit Breaker    : A pattern to stop calling a failing service. If PSP-A fails 5 times in
                     a row, the circuit "opens" — you stop sending requests to PSP-A and
                     switch to PSP-B. After some time, you try PSP-A again.

Ledger             : A financial record of every debit and credit. Double-entry means every
                     transaction has TWO entries: money leaves one account, enters another.
                     The sum of all debits must always equal the sum of all credits.
                     This is how banks have tracked money for 500 years.

Outbox Pattern     : A reliable way to publish events from a database. Instead of writing to
                     DB AND sending a Kafka message (which can fail partially), you write ONLY
                     to a DB table called "outbox". A background worker reads the outbox and
                     publishes to Kafka. This ensures you never lose an event.

CQRS               : Command Query Responsibility Segregation. Separate the "write" path
                     (create/update orders) from the "read" path (dashboards/reports).
                     Writes go to a fast OLTP database. Reads go to a separate analytics store.

CDC                : Change Data Capture. A technique to stream every database change
                     (insert/update/delete) into a Kafka topic in real time.
                     Tool example: Debezium reads PostgreSQL's write-ahead log and publishes
                     every change as a Kafka event.

Saga Pattern       : A way to handle multi-step transactions across services without
                     distributed locking. Each step is a local transaction. If a step fails,
                     you run "compensating transactions" to undo earlier steps.
                     Example: reserve funds -> authorize payment -> update ledger.
                     If ledger update fails, you undo the authorization, then release the funds.

3DS / SCA          : 3D Secure is an extra authentication step for card payments. When fraud
                     risk is high, the cardholder is redirected to their bank's page to
                     verify via OTP or biometrics. SCA (Strong Customer Authentication) is
                     the EU regulation that mandates this for most online payments.

ECI Code           : Electronic Commerce Indicator. A number that tells the card network
                     how strongly the payment was authenticated.
                     ECI 05 = full 3DS — liability shifts to issuing bank if fraud occurs.
                     ECI 07 = no 3DS — merchant bears full fraud liability.

Chargeback         : When a customer disputes a charge with their bank ("I didn't buy this").
                     The bank reverses the money from the merchant pending investigation.
                     The merchant must submit evidence to fight it. If they lose, the money
                     is permanently taken from the merchant.

BNPL               : Buy Now Pay Later. Customer pays in installments (e.g. 3 EMIs).
                     Requires a saga-style multi-step flow: reserve full amount, charge
                     installment 1 now, schedule future charges.

Sharding           : Splitting a database table across multiple physical servers (shards)
                     so no single server handles all the load. Each shard holds a subset
                     of the data. A router directs each query to the correct shard.

Consistent Hashing : A sharding algorithm where adding/removing a shard moves only a small
                     fraction of data, not a full reshuffle. Uses a "ring" of virtual nodes.

Optimistic Locking : A concurrency control strategy. Each row has a "version" number.
                     When you update a row, you check: "is the version still the same as
                     when I read it?" If another process changed it, the update fails and
                     you retry. Prevents two processes from overwriting each other's changes.

p95 / p99 Latency  : The response time that 95% (or 99%) of requests are faster than.
                     p95 < 300ms means 95 out of 100 requests finish in under 300ms.
                     The remaining 5% may be slower. p99 catches the worst cases.
```

### How to Read This Guide as a New Learner

```text
1. Read this Primer fully first. Know every term above before moving on.
2. Read Section 0 and Section 1 — understand the scope and scale.
3. Read Section 2 — study the architecture diagram. Map each box to the glossary.
4. Read Section 7 — understand the state machine before the sequence flows.
5. Read Section 6 — now the sequence flows will make sense.
6. Read Section 8 — understand the schema (tables and indexes).
7. Read Sections 9-12 — failure handling, tradeoffs, security, observability.
8. Sections 17-20 — advanced topics (chargeback, saga, 3DS, sharding).
9. Sections 14-16 — closing answers and whiteboard summary for interview use.
```

---

## SECTION 0: HOW I START THE INTERVIEW

Before drawing anything, I call out a critical distinction:

**Payment Gateway vs Payment Processor — they are different systems.**

```text
Payment Gateway  : collects payment details securely, tokenizes, orchestrates flow,
                   routes to processor, tracks status, reconciles outcomes.
Payment Processor: actually talks to card network and bank to authorize/capture/settle.
```

You:
"I will design the full payment system — gateway and processing layers combined."
"I will structure this in five steps:"

"Step 1: Lock scope, distinguish gateway vs processor, and set non-functional targets."
"Step 2: Draw end-to-end architecture from checkout through processor to reconciliation."
"Step 3: Define state machine, idempotency, PCI tokenization, and schema."
"Step 4: Cover failure handling and reconciliation."
"Step 5: Close with tradeoffs, observability, and security posture."

---

## SECTION 1: REQUIREMENTS AND CAPACITY

### 1.1 Functional Scope

```text
[OK] Merchant creates payment intent
[OK] Gateway creates hosted checkout session (user enters card on gateway page)
[OK] Secure card tokenization in PCI zone
[OK] Route to processor via adapters
[OK] Confirm payment (auth/capture)
[OK] Support cards, UPI, netbanking, wallet
[OK] Full and partial refunds
[OK] Webhook callbacks from PSPs/processors
[OK] Reconciliation with PSP/bank settlement files
[OK] Audit trail and transaction history
[X]  Lending/EMI underwriting
[X]  Crypto rails
[X]  Part payment (descoped for this round)
```

### 1.2 Non-Functional Targets

You:
"For payments, correctness is first. I design for no double charge, no silent loss, full traceability."

```text
Availability     : 99.99%
Latency          : p95 < 200ms (tokenization), p95 < 300ms (create intent), p95 < 700ms (confirm API)
Consistency      : strong for financial writes, eventual for dashboards/analytics
Idempotency      : mandatory for all mutating APIs
Scale target     : 10K TPS write headroom, 80K RPS read APIs
Security         : PCI DSS compliant zone for card data, TLS everywhere, encryption at rest
CAP position     : consistency over availability for money state transitions
```

### 1.3 Capacity Estimation

You:
"Let me do quick math and then apply headroom for spikes and retries."

```text
Assumptions:
- 20M DAU
- 0.5 payment attempts per user per day
- Peak factor: 5x

Daily attempts = 10,000,000
Average TPS    = 10,000,000 / 86,400  ~= 116 TPS
Peak TPS       ~= 580 TPS

Design target  = 10,000 TPS
Reason         = campaign spikes + retry amplification + provider failovers
```

---

## SECTION 2: HIGH-LEVEL ARCHITECTURE (WHAT I DRAW)

### 2.1 End-to-End Architecture Diagram (ASCII)

```text
                        +-----------------------------+
                        | Merchant App / Client SDK   |
                        +-------------+---------------+
                                      |
                                      v
                        +-----------------------------+
                        | API Gateway + WAF + Auth    |
                        | Rate limit + Idempotency    |
                        +-------------+---------------+
                                      |
           +--------------------------+--------------------------+
           |                          |                          |
           v                          v                          v
+----------------------+  +------------------------+  +---------------------+
| Payment Intent Svc   |  | Checkout Session Svc   |  | Txn Status API      |
| - create_intent      |  | - create session (Redis|  | - get_status        |
| - store metadata     |  |   TTL=10 min)          |  | - merchant polling  |
+----------+-----------+  | - return checkout_url  |  +---------------------+
           |              +----------+-------------+
           |                         |
           |              checkout_url with session_id
           |                         v
           |              +-----------------------------+
           |              | Hosted Checkout Frontend    |
           |              | (gateway-hosted, not        |
           |              |  merchant-hosted)           |
           |              +----------+------------------+
           |                         |  card details
           |                         v
           |              +-----------------------------+
           |              | Checkout Backend Svc        |
           |              | - validate session          |
           |              | - anti-replay check         |
           |              +----------+------------------+
           |                         |
           |                         v
           |              +-----------------------------+
           |              | Tokenization / PCI Zone     |
           |              | - validate PAN (Luhn)       |
           |              | - fingerprint generation    |
           |              | - HSM-backed encryption     |
           |              | - return encrypted token    |
           |              +----------+------------------+
           |                         |
           v                         v
+--------------------------------------------------------------------------+
| Payment API Service (confirm, refund, status)                            |
+--------------------------------------------------------------------------+
                                      |
              +-----------------------+-----------------------+
              |                                               |
              v                                               v
+-------------------------------+                 +-------------------------------+
| Payment Orchestrator          |                 | Webhook Intake Service        |
| - state transition owner      |                 | - verify PSP signature        |
| - route to processor          |                 | - dedupe by psp_event_id      |
| - post to ledger              |                 | - enqueue reconcile jobs      |
+---------------+---------------+                 +---------------+---------------+
                |                                                 |
                v                                                 v
+--------------------------------------------------------------------------+
| Event Bus / Queue (Kafka/SQS)                                            |
| payment-events | webhook-events | callback_status | settlement_final     |
+---------------------------+---------------------------+------------------+
                            |                           |
                            v                           v
              +---------------------------+   +---------------------------+
              | Gateway Router            |   | Reconciliation Worker     |
              | - merchant preference     |   | - PSP polling API         |
              | - PSP-A / PSP-B routing   |   | - settlement file parsing |
              | - circuit breaker         |   | - MATCHED/MISMATCH        |
              +-------------+-------------+   +-------------+-------------+
                            |                               |
             +--------------+----------+                    |
             |                         |                    v
   +-----------------+       +-----------------+   +-------------------+
   | PSP Adapter A   |       | PSP Adapter B   |   | Ledger Service    |
   | (adapter pattern|       | (adapter pattern|   | double-entry      |
   +---------+-------+       +---------+-------+   +---------+---------+
             |                         |                     |
             +------------+------------+                     v
                          v                          +-------------------+
                  +-------------------+              | Ledger DB         |
                  | Processor/Bank    |              | immutable entries |
                  | Network           |              +-------------------+
                  +--------+----------+
                           |
                           v
                  +-------------------+
                  | Callback Collector|
                  +-------------------+

+--------------------------------------------------------------------------+
| Payment DB (orders, intents, sessions, attempts, refunds, idempotency)   |
+--------------------------------------------------------------------------+
```

### 2.2 How I Explain This Diagram

You:
"I separate synchronous request handling from asynchronous finalization."

"The gateway layer — intent, session, hosted checkout, tokenization — runs synchronously so the user gets a fast checkout experience."

"The processing layer — orchestrator, adapters, callbacks, reconciliation — handles provider latency, retries, and webhook noise asynchronously."

"The hosted checkout page is on the gateway domain, not the merchant domain. This keeps raw card data out of merchant PCI scope entirely."

"Immediate processor callback gives near-real-time status. Delayed settlement file gives final financial truth. Reconciliation resolves any gap."

### 2.3 Plain English Walkthrough (For New Learners)

```text
Read the architecture diagram top to bottom like a story:

1. MERCHANT APP / CLIENT SDK
   The merchant's website or mobile app. The customer is shopping here.
   It does NOT handle card data — it just starts the payment flow.

2. API GATEWAY + WAF + AUTH
   The front door. Every request passes through here.
   - WAF (Web Application Firewall) blocks malicious traffic.
   - Auth checks: is this a valid merchant? Is the token valid?
   - Rate limiter: prevents one merchant from flooding the system.
   - Idempotency check: have we seen this request before?

3. PAYMENT INTENT SERVICE
   The merchant calls this first: "I want to collect 500 rupees from customer X."
   This creates a record in the database — the "intention to pay".
   Nothing is charged yet.

4. CHECKOUT SESSION SERVICE + HOSTED CHECKOUT FRONTEND
   A short-lived session (10 minutes) is created and a secure URL is returned.
   The customer is redirected to THIS gateway-hosted page to enter card details.
   WHY? Because the merchant's website never sees the card number.
   The gateway hosts the page, so PCI compliance burden stays with the gateway.

5. TOKENIZATION / PCI ZONE
   When the customer submits their card, it goes into a locked-down zone.
   The real card number is encrypted using an HSM.
   A safe token is returned — this is what travels through the rest of the system.
   Raw card data never leaves this zone.

6. PAYMENT API SERVICE
   Handles confirm, refund, and status requests from merchants.
   Passes work to the Orchestrator.

7. PAYMENT ORCHESTRATOR
   The brain of the system. It:
   - Decides which PSP (payment processor) to route to
   - Owns the state machine (what state can transition to what)
   - Posts entries to the Ledger after a successful capture
   - Handles unknown outcomes from processor timeouts

8. GATEWAY ROUTER + PSP ADAPTERS
   The router picks the best PSP based on success rates, merchant preference,
   and circuit breaker status. Each PSP has an adapter — a translator that
   converts internal payment commands to that PSP's API format.

9. WEBHOOK INTAKE SERVICE
   PSPs send callbacks asynchronously ("payment succeeded").
   This service verifies the signature (is it really from the PSP?),
   deduplicates (PSPs often send the same webhook 2-3 times),
   and puts the event on the queue for processing.

10. EVENT BUS (KAFKA/SQS)
    Decouples synchronous request handling from async processing.
    Payment events, webhook events, and reconciliation jobs flow through here.

11. RECONCILIATION WORKER
    Runs daily (or more often). Compares your records vs PSP's settlement file.
    Catches any mismatch — e.g. PSP says "captured" but your DB says "unknown".

12. LEDGER SERVICE
    Maintains the financial truth. Every capture and refund posts two entries
    (debit + credit). Immutable — entries are never deleted or updated.

13. PAYMENT DB
    Stores all payment orders, attempts, sessions, idempotency records, and refunds.
```

---

## SECTION 3: CLASS DIAGRAM (LLD VIEW)

### 3.1 Full Class Diagram (ASCII)

```text
+------------------------------+
| PaymentController            |
| +createIntent(req)           |
| +createSession(req)          |
| +confirmPayment(req)         |
| +createRefund(orderId, req)  |
| +getStatus(orderId)          |
+--------------+---------------+
               |
               v
+------------------------------+        +------------------------------+
| PaymentService               |------->| IdempotencyService           |
| +createIntent(cmd)           |        | +checkAndStore(...)          |
| +createSession(cmd)          |        +------------------------------+
| +confirmPayment(cmd)         |
| +createRefund(cmd)           |------->+------------------------------+
| +getStatus(orderId)          |        | PaymentRepository            |
+------+-----------------------+        | +saveIntent(...)             |
       |                                | +saveOrder(...)              |
       |                                | +saveAttempt(...)            |
       |                                | +findOrder(...)              |
       |                                +------------------------------+
       |
       +-------------------------------> +------------------------------+
       |                                 | PaymentOrchestrator          |
       |                                 | +transition(...)             |
       |                                 | +handleUnknown(...)          |
       |                                 | +routeToProcessor(...)       |
       |                                 +-------------+----------------+
       |                                               |
       v                                               v
+------------------------------+         +------------------------------+
| GatewayRouter                |-------->| PSPAdapter (interface)       |
| +route(merchant, ctx)        |         | +authorize(...)              |
| +fallback(...)               |         | +capture(...)                |
+-------------+----------------+         | +refund(...)                 |
              |                          | +verifyWebhook(...)          |
              v                          +-------------+----------------+
     +-------------------+                             |
     | PSPAAdapter       |                   +---------+---------+
     +-------------------+                   | PSPAAdapter       |
     +-------------------+                   | PSPBAdapter       |
     | PSPBAdapter       |                   +-------------------+
     +-------------------+

+------------------------------+
| TokenizationService          |
| +validatePAN(...)            |
| +generateFingerprint(...)    |
| +encryptViaHSM(...)          |
+--------------+---------------+
               |
               v
+------------------------------+
| HSMClient                    |
| +encrypt(plaintext, keyId)   |
+------------------------------+

+------------------------------+         +------------------------------+
| LedgerService                |<--------| PaymentOrchestrator          |
| +postCaptureEntries(...)     |         +------------------------------+
| +postRefundEntries(...)      |
+--------------+---------------+
               |
               v
+------------------------------+
| LedgerRepository             |
| +insertEntries(...)          |
| +findByTxnGroup(...)         |
+------------------------------+

+------------------------------+
| WebhookController            |
| +receive(psp, payload)       |
+--------------+---------------+
               |
               v
+------------------------------+
| WebhookService               |
| +verifySignature(...)        |
| +dedupeEvent(...)            |
| +enqueueForProcessing(...)   |
+------------------------------+
```

### 3.2 How I Explain This LLD

You:
"Controllers stay thin — they validate shape, extract merchant context, and delegate."

"PaymentService is the application facade. It coordinates idempotency checks, persistence, and orchestration in deterministic order. This is where retry-safe behavior is enforced before mutation."

"PaymentOrchestrator is the only owner of legal state transitions. No other class directly mutates money state. That guard prevents duplicate webhook side effects and out-of-order callback corruption."

"TokenizationService is fully isolated in the PCI zone. It validates PAN format, generates a fingerprint for dedupe/risk, and delegates HSM calls. No raw card data exits this boundary."

"GatewayRouter and PSPAdapter isolate provider-specific contracts. Processor changes update only the adapter, not core business logic."

"LedgerService is isolated so financial posting rules remain auditable and immutable."

---

## SECTION 4: API CONTRACT AND IDEMPOTENCY

### 4.1 APIs

```http
POST /v1/payment-intents
POST /v1/payment-sessions
POST /v1/payment-orders/{id}/confirm
GET  /v1/payment-orders/{id}
POST /v1/payment-orders/{id}/refunds
POST /v1/webhooks/{psp}
```

Intent of each:
```text
payment-intents          : register purchase metadata -> return payment_intent_id
payment-sessions         : create short-lived Redis session -> return checkout_url
payment-orders/{id}/confirm : submit tokenized card, trigger processor routing
payment-orders/{id}      : merchant polls/queries current status
payment-orders/{id}/refunds : create full or partial refund
webhooks/{psp}           : receive async callback from PSP/processor
```

### 4.2 Idempotency

You:
"Idempotency is mandatory for payments because client retries are normal under network failures."

```text
Headers:
- Idempotency-Key: <uuid>
- X-Merchant-Id: <merchant_id>

Rules:
- same key + same payload   -> return original response (deterministic replay)
- same key + different body -> 409 Conflict
- enforced at: PaymentService entry + DB unique constraint (merchant_id, idempotency_key)
```

### 4.3 Status Codes

```text
201 Created               payment order/intent created
202 Accepted              processing started / pending finalization
200 OK                    status query success
409 Conflict              idempotency payload mismatch
422 Unprocessable Entity  business validation failed (over-refund, invalid state)
502/504                   upstream PSP failure/timeout
```

---

## SECTION 5: PCI TOKENIZATION ZONE (DEEP DIVE)

You:
"The card entry happens on a gateway-hosted page, never merchant-hosted. This keeps raw card data out of merchant PCI scope entirely."

### 5.1 Three Operations in Tokenization Service

```text
1. Card validation
   - PAN format check + Luhn algorithm
   - Card metadata extraction (BIN lookup, scheme, issuer)

2. Fingerprint generation
   - Input: BIN(first 6) + last4 + expiry + cardholder name
   - Store fingerprint hash for dedupe and risk pattern detection

3. HSM-backed encryption
   - Never use app-level key files
   - Return encrypted_card_token to checkout backend
```

### 5.2 Tokenization Flow (ASCII)

```text
[Hosted Checkout Frontend]
       | card details (TLS)
       v
[Checkout Backend Validation]
  1. session_id exists in Redis
  2. session not expired (TTL=10 min)
  3. session maps to exact intent + merchant + order
  4. nonce/anti-replay check passes
       | validated
       v
[Tokenization Service / PCI Zone]
  +---------------------------+
  | validate PAN (Luhn)       |
  | generate fingerprint hash |
  | call HSM for encryption   |
  +------------+--------------+
               |
               v
       encrypted_card_token
               |
               v
[Payment Orchestrator]  -> route to processor
```

---

## SECTION 6: SEQUENCE FLOWS (ASCII)

### 6.1 Full End-to-End Happy Path

```text
User   Merchant   IntentSvc   SessionSvc  CheckoutFE  CheckoutBE  TokenSvc  Orchestrator  Processor
 |        |           |            |           |           |           |           |           |
 | buy    |           |            |           |           |           |           |           |
 |------->|           |            |           |           |           |           |           |
 |        | createIntent           |           |           |           |           |           |
 |        |---------->| save DB    |           |           |           |           |           |
 |        |<----------| intent_id  |           |           |           |           |           |
 |        | createSession          |           |           |           |           |           |
 |        |----------------------->| save Redis|           |           |           |           |
 |        |<-----------------------| checkout_url          |           |           |           |
 | redirect to checkout_url        |           |           |           |           |           |
 |------------------------------------------>  |           |           |           |           |
 | card details                               |----------->|           |           |           |
 |                                            |            |---------->| validate   |           |
 |                                            |            |           |---------> | tokenize  |
 |                                            |            |           |<--------- | token     |
 |                                            |            |           |<-token----|           |
 |                                            |            |           |           |---------->|
 |                                            |            |           |           |<----------|
 |                                            |            |           |<--result--|           |
 | poll status                                |----------->| read DB   |           |           |
 |<-------------------------------------------|            |           |           |           |
```

### 6.1a Plain English Walkthrough (For New Learners)

```text
Read the sequence diagram as a left-to-right story with time flowing downward.

Step 1 — User clicks Buy
  The user triggers a purchase on the merchant app.

Step 2 — Merchant calls createIntent
  The merchant backend calls the Intent Service:
  "I want to collect money for this order."
  A payment_intent_id is saved to the database. Nothing is charged yet.

Step 3 — Merchant calls createSession
  The merchant calls the Session Service to get a checkout URL.
  A short-lived session (10 minutes) is stored in Redis.
  The merchant redirects the user to this URL.

Step 4 — User enters card on Hosted Checkout Frontend
  The user is now on the GATEWAY's page, not the merchant's page.
  The merchant never sees the card number.

Step 5 — Checkout Backend validates the session
  Before accepting any card data, the backend checks:
  - Is this session still valid (not expired)?
  - Does it belong to the correct merchant and order?
  - Has this nonce been used before (anti-replay)?

Step 6 — Tokenization
  Card details go into the PCI zone.
  The HSM encrypts the card and returns a safe token.
  Raw card data never leaves this zone.

Step 7 — Processor authorization
  The Orchestrator sends the token to the PSP/Processor.
  The Processor talks to the card network and issuing bank.
  Authorization result comes back (approved / declined).

Step 8 — User polls for status
  The user's browser polls the status API.
  The API reads the database and returns the current payment state.
```

### 6.2 Timeout / Unknown Outcome

```text
1) Client confirms payment
2) Orchestrator sends charge request to PSP/Processor
3) PSP timeout or uncertain response
4) attempt_status = UNKNOWN
5) API returns 202 PENDING to merchant
6) Webhook and reconciliation jobs race to resolve truth
7) Transition to CAPTURED or FAILED
8) Notify merchant and customer
```

You:
"I never auto-fail unknown outcomes immediately. UNKNOWN is a valid state until reconciliation confirms truth."

### 6.3 Webhook Processing Flow

```text
PSP callback -> Webhook Service
Webhook Service -> verify signature -> dedupe by psp_event_id
Webhook Service -> publish to event bus
Worker -> fetch payment order -> validate state transition
Worker -> update order + write ledger (if needed)
Worker -> publish notification
```

### 6.4 Callback vs Settlement (Two Async Truth Channels)

```text
[Processor Callback Collector]
       |
       +--> topic: callback_status  (near-real-time, used for UX status)
       |
       +--> topic: settlement_final (delayed hours/day, used for ledger finality)

[Orchestrator Consumer] reads callback_status -> updates payment status
[Reconciliation Service] reads settlement_final -> posts final ledger entries

Reconciliation outcome states:
- MATCHED_SUCCESS
- MATCHED_FAILED
- MISMATCH_REVIEW
```

---

## SECTION 7: PAYMENT STATE MACHINE

### 7.1 State Diagram (ASCII)

```text
CREATED
   |
   v
SESSION_CREATED
   |
   v
PROCESSING
   |
   +--------> VALIDATION_FAILED (bad card, expired session)
   |
   v
SENT_TO_PROCESSOR
   |
   +--------> UNKNOWN (timeout/no ack)
   |               |
   |               +--> CAPTURED (webhook/recon resolves)
   |               +--> FAILED   (webhook/recon resolves)
   v
AUTHORIZED
   |
   v
CAPTURED
   |
   +--------> REFUND_INITIATED
                   |
                   v
               PARTIALLY_REFUNDED or FULLY_REFUNDED

CAPTURED -> RECON_SUCCESS or RECON_MISMATCH
FAILED   -> RECON_FAILED  or RECON_MISMATCH
```

You:
"The orchestrator is the single owner of these transitions. Any webhook or callback must pass through transition guards — I never allow a direct jump to CAPTURED from any arbitrary starting state."

### 7.2 Plain English Walkthrough (For New Learners)

```text
A state machine answers: "What is this payment right now, and what can it become next?"

CREATED
  The payment intent record exists in the database. Nothing sent to PSP yet.

SESSION_CREATED
  A checkout URL was generated. The user is on the checkout page entering card details.

PROCESSING
  Card details submitted. Tokenization is happening. About to call the PSP.

VALIDATION_FAILED
  Something was wrong before we even called the PSP:
  - card was expired, Luhn check failed
  - session had expired (user took too long)
  - anti-replay check failed
  No money was moved. End state.

SENT_TO_PROCESSOR
  The PSP received our authorization request. We are waiting for a response.

UNKNOWN
  IMPORTANT: We sent the request to the PSP but got no response (timeout/network drop).
  We do NOT know if the PSP charged the customer or not.
  We must NOT fail the payment — the customer might have been charged.
  We wait for a webhook callback or reconciliation to tell us the truth.

AUTHORIZED
  The issuing bank approved the charge. Funds are reserved but not yet moved.
  (Some PSPs combine auth+capture into one step — AUTHORIZED may be skipped.)

CAPTURED
  Funds are confirmed captured. The merchant will receive the money on settlement day.
  This is the "success" state. The ledger entry is posted here.

REFUND_INITIATED -> PARTIALLY_REFUNDED / FULLY_REFUNDED
  Merchant requested money back to the customer.
  Partial = some amount refunded. Full = entire capture refunded.

RECON_SUCCESS / RECON_MISMATCH
  After reconciliation with the PSP's settlement file:
  - SUCCESS: our records match the PSP's records perfectly.
  - MISMATCH: discrepancy found — needs manual investigation.

KEY RULE: The orchestrator enforces ALL transitions.
No other service can directly change payment status.
This prevents webhooks or retries from corrupting the state.
```

---

## SECTION 8: SCHEMA DIAGRAM (ER + INDEX VIEW)

### 8.1 ER Diagram (ASCII)

```text
+---------------------------+         +---------------------------+
| merchants                 |         | customers                 |
|---------------------------|         |---------------------------|
| merchant_id (PK)          |         | customer_id (PK)          |
| name                      |         | email                     |
| status                    |         | phone                     |
+----------+----------------+         +----------+----------------+
           |                                     |
           | N                                   | N
           v                                     v
+--------------------------------------------------------------------------+
| payment_intents                                                          |
|--------------------------------------------------------------------------|
| intent_id (PK)                                                           |
| merchant_id (FK)                                                         |
| customer_id (FK)                                                         |
| amount_minor                                                             |
| currency                                                                 |
| method_type                                                              |
| status                                                                   |
| created_at                                                               |
+----------+---------------------------------------------------------------+
           |
           | 1
           v
+---------------------------+
| payment_orders            |
|---------------------------|
| order_id (PK)             |
| intent_id (FK)            |
| merchant_id (FK)          |
| customer_id (FK)          |
| amount_minor              |
| currency                  |
| status                    |
| idempotency_key           |
| version                   |          (optimistic lock)
| created_at                |
| updated_at                |
+-------------+-------------+
              |
    +---------+---------+
    | 1                 | 1
    v                   v
+---------------------------+   +---------------------------+
| payment_attempts          |   | refunds                   |
|---------------------------|   |---------------------------|
| attempt_id (PK)           |   | refund_id (PK)            |
| order_id (FK)             |   | order_id (FK)             |
| psp                       |   | amount_minor              |
| psp_txn_id (UNIQUE)       |   | status                    |
| status                    |   | psp_refund_id (UNIQUE)    |
| attempt_no                |   | created_at                |
| error_code                |   +---------------------------+
| created_at                |
+---------------------------+

+---------------------------+   +---------------------------+
| idempotency_records       |   | webhook_events            |
|---------------------------|   |---------------------------|
| merchant_id (PK1, FK)     |   | event_id (PK)             |
| idempotency_key (PK2)     |   | psp                       |
| request_hash              |   | psp_event_id (UNIQUE)     |
| response_blob             |   | event_type                |
| expires_at                |   | payload_hash              |
| created_at                |   | processed_at              |
+---------------------------+   +---------------------------+

+---------------------------+   +---------------------------+
| checkout_sessions         |   | ledger_entries            |
|---------------------------|   |---------------------------|
| session_id (PK)           |   | entry_id (PK)             |
| intent_id (FK)            |   | txn_group_id (INDEX)      |
| merchant_id               |   | account_id (INDEX)        |
| nonce                     |   | side (DEBIT/CREDIT)       |
| expires_at                |   | amount_minor              |
| created_at                |   | reference_type            |
+---------------------------+   | reference_id              |
   (also stored in Redis         | created_at                |
    TTL=10 min for speed)        +---------------------------+
```

### 8.1a Plain English Walkthrough (For New Learners)

```text
The schema shows how data is organised in the database. Read it as connected tables.

merchants
  One row per business using the payment gateway. Holds name, status, config.

customers
  One row per end user. Stores contact info. Linked to their payment orders.

payment_intents
  Created first when a merchant says "I want to collect money."
  Holds the amount, currency, and method type. No PSP call made yet.

payment_orders
  Created when the user actually attempts to pay. One intent can have
  one order (most cases). The version column enables optimistic locking —
  prevents two processes from overwriting each other's status update.
  The idempotency_key ensures the same request cannot create two orders.

payment_attempts
  Each time we call a PSP, one attempt row is created.
  One order can have multiple attempts (e.g. PSP-A failed, retry on PSP-B).
  psp_txn_id is unique per PSP — prevents duplicate charge recording.

refunds
  One row per refund request on an order.
  psp_refund_id is unique — prevents double-recording a refund.

idempotency_records
  Stores the request hash and original response for every mutating API call.
  If a client retries with the same idempotency_key, we return the stored
  response without processing again. Expires after a retention window (e.g. 24h).

webhook_events
  Every callback from a PSP is recorded here first.
  psp_event_id is unique — if the PSP sends the same webhook twice,
  the second insert fails the unique constraint and is discarded.

checkout_sessions
  Short-lived record (10 min TTL) linking a session_id to an intent.
  Stored in BOTH Redis (for fast lookup) and DB (for audit trail).
  The nonce field prevents replay attacks on the checkout form.

ledger_entries
  Financial truth. Every capture posts two rows (debit + credit).
  Every refund posts two rows (reversed direction).
  Rows are NEVER updated or deleted — append-only.
  txn_group_id links the two sides of each transaction.
  Sum of all debits must always equal sum of all credits.
```

### 8.2 Indexing Strategy

You:
"Idempotency and dedupe are enforced at DB boundary, not just application logic."

```text
payment_orders:
- UNIQUE (merchant_id, idempotency_key)
- INDEX  (merchant_id, created_at DESC)
- INDEX  (status, updated_at)

payment_attempts:
- UNIQUE (psp, psp_txn_id)
- INDEX  (order_id, attempt_no DESC)

refunds:
- UNIQUE (psp, psp_refund_id)
- INDEX  (order_id, created_at DESC)

webhook_events:
- UNIQUE (psp, psp_event_id)
- INDEX  (processed_at)

ledger_entries:
- INDEX  (txn_group_id)
- INDEX  (reference_type, reference_id)
```

### 8.3 Ledger Invariant

```text
For every txn_group_id:
sum(DEBIT amounts) == sum(CREDIT amounts)

Example capture posting:
DEBIT  customer_clearing_account  1000
CREDIT merchant_payable_account   1000

Example refund posting:
DEBIT  merchant_payable_account   500
CREDIT customer_clearing_account  500
```

---

## SECTION 9: FAILURE SCENARIOS (WHAT SENIOR INTERVIEWERS TEST)

### 9.1 Retry Storm from Clients

```text
Risk: duplicate charge
Controls:
- idempotency key enforced at edge
- unique constraint (merchant_id, idempotency_key) in DB
- deterministic replay response
Outcome: one effective financial action regardless of retry count
```

### 9.2 PSP Charged But Callback Delayed

```text
Risk: local status remains pending indefinitely
Controls:
- UNKNOWN state in state machine
- webhook event processing
- active reconciliation polling on settlement files
Outcome: eventual CAPTURED or FAILED with full audit trail
```

### 9.3 Duplicate Webhook Deliveries

```text
Risk: repeated state transitions
Controls:
- unique (psp, psp_event_id) in webhook_events table
- transition guards in orchestrator (e.g., cannot CAPTURE already CAPTURED)
Outcome: one effective state transition
```

### 9.4 PSP Partial Outage

```text
Risk: success rate collapse
Controls:
- circuit breaker per PSP
- gateway router shifts traffic to secondary PSP
- controlled retry policy (exponential backoff with jitter)
Outcome: graceful degradation, merchant success rate preserved
```

### 9.5 Invalid Refund Beyond Captured Amount

```text
Risk: accounting inconsistency
Controls:
- transactional bound check: refunded_total + requested_refund <= captured_total
Outcome: reject 422 Unprocessable Entity
```

### 9.6 Expired or Tampered Session

```text
Risk: replay attack or stale checkout
Controls:
- Redis TTL=10 min on checkout_sessions
- session maps exactly to (intent_id + merchant_id + order_id)
- nonce/anti-replay check before tokenization
Outcome: reject immediately at checkout backend validation
```

---

## SECTION 10: TRADEOFFS (SAY THIS CLEARLY)

```text
Choice                              Advantage                      Tradeoff
-------------------------------------------------------------------------------------
Strong consistency for ledger        financial correctness          higher write latency
Hosted checkout on gateway domain    PCI scope reduction            UX customization limit for merchants
Redis for checkout sessions          low-latency validation         TTL-bound, not durable
Async webhook + reconcile flow       resiliency + decoupling        eventual status visibility
Multi-PSP routing                    better availability            operational complexity
Aggressive retries                   improved success rate          retry amplification risk
Long idempotency retention           safer client retries           storage overhead
Separate ledger service              auditability + stability       service boundary overhead
```

You:
"I enforce strong consistency where money commits, and allow eventual consistency where user dashboards can tolerate lag."

You:
"In the CAP tradeoff, for payment state writes I always choose consistency. A temporarily unavailable payment is recoverable. An incorrect debit state is not."

---

## SECTION 11: SECURITY, COMPLIANCE, AND FRAUD

### 11.1 Security Controls

```text
- hosted checkout on gateway domain (card data never touches merchant app)
- tokenize card data via HSM; no PAN/CVV storage outside PCI zone
- TLS in transit everywhere; mTLS for high-risk internal links
- KMS encryption at rest for all sensitive fields
- strict IAM and least-privilege service accounts
- immutable audit logs (ledger_entries, webhook_events, idempotency_records)
- signed webhook verification before any mutation
```

### 11.2 Fraud Baseline

```text
Signals:
- velocity by card fingerprint / device / merchant
- geo mismatch between billing address and IP
- repeated declines in short window
- unusual amount distribution for BIN

Action tiers:
- ALLOW  : proceed
- CHALLENGE: 3DS / OTP step-up
- BLOCK  : reject and flag for review
```

You:
"Fraud controls must be explainable and traceable, especially when transactions are challenged or blocked."

---

## SECTION 12: OBSERVABILITY AND SLO RUNBOOK

### 12.1 Key Metrics

```text
Business:
- payment_success_rate (by PSP, by BIN, by merchant)
- auth_to_capture_dropoff
- refund_success_rate
- unknown_age_bucket (how long UNKNOWN states live)

Technical:
- p95/p99 latency by API stage
- tokenization latency
- webhook processing lag
- reconciliation backlog depth
- PSP error rate by provider
```

### 12.2 Alerts

```text
- success rate below threshold for 5 minutes
- p99 latency above threshold for 10 minutes
- webhook backlog continuously rising
- UNKNOWN payments breaching SLA age (e.g., >30 min)
- reconciliation mismatch rate above baseline
```

### 12.3 Incident Runbook Snippet

```text
If PSP-A success rate falls:
1) open circuit breaker for PSP-A
2) route traffic incrementally to PSP-B
3) raise reconcile frequency
4) reduce retry aggressiveness temporarily (backoff multiplier)
5) notify merchant ops + incident channel
6) monitor UNKNOWN age buckets for drift
```

---

## SECTION 13: JAVA/SPRING IMPLEMENTATION NOTES

```text
- optimistic locking (version column) on payment_orders to prevent concurrent mutation
- @Transactional boundary: state transition + outbox write in one unit
- outbox pattern for reliable event publish (no dual write inconsistency)
- verify webhook signature before any DB mutation
- PSP integrations behind PSPAdapter interface — contract tests per adapter
- Redis session store with TTL auto-expiry
- HSM client injected via interface for testability
```

---

## SECTION 14: 15-YEAR CLOSING ANSWER

You:
"I design payment systems with one rule: never lose money truth."

"The gateway layer handles secure collection — hosted checkout, PCI tokenization, session validation — so raw card data never enters merchant or core payment systems."

"The processing layer manages orchestration, state transitions, and provider routing through adapters so processor changes never leak into business logic."

"Workflow states can be retried and reconciled, but ledger truth is immutable and auditable."

"I combine idempotency, strict transition rules, webhook dedupe, and reconciliation to survive partial failures without double charges."

"At scale, multi-PSP routing and circuit breakers preserve success rates, and observability gives early detection and controlled response."

One-line close:
"Correctness first, resilience second, speed third."

---

## SECTION 15: CROSS-QUESTIONS AND STRONG ANSWERS

Q1: What is the difference between a payment gateway and a payment processor?
A: "Gateway: collects, tokenizes, orchestrates, routes. Processor: talks to card network and bank for auth/capture/settlement. I own the gateway layer here."

Q2: Why host the checkout page on the gateway domain?
A: "To keep raw card data out of merchant scope entirely. The merchant never sees PAN/CVV. Their PCI compliance surface drops dramatically."

Q3: How do you guarantee no double charge?
A: "Idempotency at edge, unique constraints in DB, deterministic replay responses, deduped webhooks, and transition guards in orchestrator."

Q4: What if PSP times out but customer was charged?
A: "Mark UNKNOWN, return 202 pending, reconcile via webhook plus PSP polling and settlement file. Never auto-fail unknown outcomes."

Q5: Why not exactly-once everywhere?
A: "Distributed exactly-once is expensive and brittle. I use at-least-once with idempotent consumers and strict state guards to achieve business-level exactly-once outcome."

Q6: How do you handle partial refunds safely?
A: "Transactional bound check: refunded_total + requested_refund <= captured_total, with refund idempotency key and reconciliation trail."

Q7: What changes immediately when one PSP degrades?
A: "Circuit opens, traffic shifts to secondary PSP, retry profile reduces, alerts fire, and reconciliation polling frequency increases."

Q8: Why Redis for checkout sessions and not just RDBMS?
A: "Sessions are short-lived (10 min TTL), high-volume, and low-risk to lose (user retries the checkout). Redis auto-expiry and sub-millisecond reads are the right tradeoff here."

---

## SECTION 16: QUICK WHITEBOARD VERSION (2 MIN)

```text
1) Edge         : API Gateway + Auth + Idempotency + Rate Limit
2) Intent       : Payment Intent Service -> DB
3) Session      : Checkout Session Service -> Redis (TTL)
4) Checkout     : Hosted Frontend + Backend Validation
5) Tokenization : PCI Zone + HSM -> encrypted token
6) Core         : Payment Orchestrator -> State machine
7) Routing      : Gateway Router -> PSP Adapters -> Processor
8) Async        : Webhooks + Kafka + Reconciliation Worker
9) Ledger       : Immutable double-entry, txn_group_id invariant
10) Reliability : UNKNOWN handling + circuit breaker + retries
11) Ops         : success rate + webhook lag + unknown age + recon backlog
```

Closing line:
"This design assumes retries, duplicates, expired sessions, and partial failures are normal — and still guarantees financially correct outcomes."

---

## SECTION 17: CHARGEBACK FLOW (TRAP QUESTION AT 15 YEARS)

You:
"Chargebacks are initiated by the cardholder's issuing bank, not the merchant. The gateway must hold funds, collect evidence, and track resolution — without touching the original ledger entries."

### 17.1 Chargeback Lifecycle (ASCII)

```text
[Cardholder]
     | disputes charge with bank
     v
[Issuing Bank]
     | initiates chargeback with card network (Visa/Mastercard)
     v
[Card Network]
     | notifies acquiring bank / processor
     v
[Acquiring Bank / Processor]
     | sends chargeback notification to gateway
     v
[Gateway: Chargeback Intake Service]
     | 1. create chargeback record (status=OPEN)
     | 2. freeze or debit merchant_payable_account (hold amount)
     | 3. notify merchant (email + webhook)
     | 4. start evidence deadline timer (typically 7-20 days)
     v
[Merchant]
     | submits evidence (transaction receipts, delivery proof, comms logs)
     v
[Gateway: Chargeback Evidence Service]
     | 1. validate evidence docs
     | 2. package and submit to acquirer/card network
     | 3. set status=EVIDENCE_SUBMITTED
     v
[Card Network / Issuing Bank]
     | reviews evidence
     v
[Two outcomes]
     +---> REVERSED  : merchant wins, hold released, credit merchant_payable_account
     +---> FINALIZED : issuer wins, merchant loses funds permanently
```

### 17.2 Chargeback State Machine (ASCII)

```text
OPEN
  |
  v
NOTIFIED_TO_MERCHANT
  |
  +-------> EXPIRED (evidence not submitted in time -> auto-FINALIZED)
  |
  v
EVIDENCE_SUBMITTED
  |
  v
UNDER_REVIEW
  |
  +-------> REVERSED   (merchant wins -> release hold -> post credit ledger entry)
  +-------> FINALIZED  (issuer wins  -> debit merchant -> post debit ledger entry)
  +-------> PRE_ARBITRATION (escalated -> second evidence round)
```

### 17.3 Chargeback Schema (ASCII)

```text
+---------------------------+
| chargebacks               |
|---------------------------|
| chargeback_id (PK)        |
| order_id (FK)             |
| merchant_id (FK)          |
| amount_minor              |
| currency                  |
| reason_code               |  (e.g. 4853 - not as described)
| status                    |
| evidence_deadline         |
| network_ref_id (UNIQUE)   |
| created_at                |
| updated_at                |
+---------------------------+

+---------------------------+
| chargeback_evidence       |
|---------------------------|
| evidence_id (PK)          |
| chargeback_id (FK)        |
| doc_type                  |  (receipt, delivery, comms)
| storage_url               |
| submitted_at              |
+---------------------------+
```

### 17.4 Ledger Posting for Chargeback

```text
On OPEN (hold):
  DEBIT  merchant_payable_account   amount  (reduce available balance)
  CREDIT chargeback_hold_account    amount

On REVERSED (merchant wins):
  DEBIT  chargeback_hold_account    amount  (release hold)
  CREDIT merchant_payable_account   amount

On FINALIZED (issuer wins):
  DEBIT  chargeback_hold_account    amount  (finalise loss)
  CREDIT issuer_settlement_account  amount
```

### 17.5 Cross-Questions on Chargeback

Q: How do you prevent a merchant from double-spending held funds?
A: "The hold debit on merchant_payable_account at OPEN time ensures balance checks for new payouts see reduced available funds. Payout service reads ledger balance — it cannot pay out held amounts."

Q: What if a chargeback arrives for an already-refunded order?
A: "Validate: if refund_total == order_amount and refund_status == COMPLETED, auto-submit evidence with refund proof. The issuing bank typically reverses chargeback immediately on confirmed refund evidence."

Q: How do you handle pre-arbitration?
A: "PRE_ARBITRATION is a second evidence round at higher cost. Gate it behind merchant consent — surface the cost to the merchant and let them decide to fight or accept the loss."

---

## SECTION 18: DISTRIBUTED SAGA PATTERN (MULTI-LEG PAYMENTS)

You:
"For single-leg payments, a local transaction suffices. For multi-leg flows — BNPL installments, split-merchant payouts, or cross-border multi-hop — I use the Saga pattern with compensating transactions instead of a distributed 2PC."

### 18.1 Why Not 2PC?

```text
2PC problems:
- coordinator becomes single point of failure
- blocking protocol: all participants lock until coordinator responds
- PSPs and banks do not expose 2PC APIs — they are external systems

Saga advantages:
- each step is a local transaction
- if a step fails, compensating transactions undo prior steps
- fully async, no coordinator lock
```

### 18.2 Orchestration-Based Saga (what I recommend)

```text
[Saga Orchestrator]
       |
       |---> Step 1: Reserve customer funds
       |       success -> continue | fail -> END (no compensation needed yet)
       |
       |---> Step 2: Authorize payment with PSP
       |       success -> continue | fail -> compensate Step 1 (release reservation)
       |
       |---> Step 3: Credit merchant account in ledger
       |       success -> continue | fail -> compensate Step 2 (void auth) + Step 1
       |
       |---> Step 4: Schedule installment plan (BNPL)
       |       success -> SAGA COMPLETE | fail -> compensate Steps 3, 2, 1
       v
[SAGA_COMPLETED or SAGA_COMPENSATED]
```

### 18.3 Saga State Machine (ASCII)

```text
SAGA_STARTED
  |
  v
FUNDS_RESERVED
  |
  +-------> FUNDS_RESERVE_FAILED -> SAGA_COMPENSATED
  v
AUTH_SENT
  |
  +-------> AUTH_FAILED -> compensate FUNDS_RESERVED -> SAGA_COMPENSATED
  v
LEDGER_CREDITED
  |
  +-------> LEDGER_FAILED -> compensate AUTH + FUNDS -> SAGA_COMPENSATED
  v
INSTALLMENT_SCHEDULED
  |
  +-------> SCHEDULE_FAILED -> compensate LEDGER + AUTH + FUNDS -> SAGA_COMPENSATED
  v
SAGA_COMPLETED
```

### 18.4 Saga Schema (ASCII)

```text
+---------------------------+
| sagas                     |
|---------------------------|
| saga_id (PK)              |
| order_id (FK)             |
| saga_type                 |  (BNPL, SPLIT_PAYOUT, CROSS_BORDER)
| status                    |
| current_step              |
| created_at                |
+---------------------------+

+---------------------------+
| saga_steps                |
|---------------------------|
| step_id (PK)              |
| saga_id (FK)              |
| step_name                 |
| status                    |  (PENDING, DONE, COMPENSATED, FAILED)
| compensation_payload      |  (stored at step completion for rollback)
| executed_at               |
+---------------------------+
```

### 18.5 Cross-Questions on Saga

Q: What if the compensating transaction also fails?
A: "Compensations must be designed idempotent and retryable with backoff. If compensation keeps failing, the saga enters COMPENSATION_FAILED state and raises a manual ops alert — a human must resolve. This is a known Saga limitation. In practice, compensations fail rarely because they are simpler operations (void, release, cancel)."

Q: Choreography vs Orchestration — which do you choose?
A: "Orchestration for payments. Choreography distributes saga logic across services via events — debugging a failed multi-step flow across six event handlers is extremely hard in production. An orchestrator centralises the decision flow, gives a single audit table, and makes compensation explicit. The coordination overhead is worth the observability gain at this scale."

---

## SECTION 19: 3DS / SCA STEP-UP FLOW

You:
"3D Secure is a cardholder authentication protocol. I trigger it selectively — not on every payment — based on fraud score, regulatory mandate (PSD2 SCA in EU), or card scheme requirement. It adds a step-up loop between authorization and capture."

### 19.1 3DS Flow (ASCII)

```text
[User submits payment on Hosted Checkout]
       |
       v
[Checkout Backend]
  validate session + tokenize card
       |
       v
[Fraud Engine]
  compute risk score
       |
       +---> LOW RISK:   skip 3DS -> proceed to PSP authorization directly
       |
       +---> HIGH RISK / SCA REQUIRED:
                 |
                 v
         [3DS Request Service]
           POST /3ds/authenticate
             - send card BIN, amount, merchant, device fingerprint
             to card network ACS (Access Control Server)
                 |
                 v
         [ACS (Issuing Bank)]
           +---> frictionless: issuer silently approves (low risk on issuer side)
           |         |
           |         v
           |     authentication_value (cryptogram) returned
           |
           +---> challenge: redirect user to issuer OTP/biometric page
                     |
                     | user completes challenge
                     v
                 authentication_value returned
       |
       v
[Payment Orchestrator]
  include authentication_value in PSP authorization request
  PSP forwards to card network -> issuer validates cryptogram
       |
       v
[AUTHORIZED -> CAPTURED]
```

### 19.2 3DS State Extension on Payment Order

```text
Payment order status additions for 3DS:

PROCESSING
  |
  +-------> CHALLENGE_REQUIRED  (issuer demands OTP)
                 |
                 +-------> CHALLENGE_COMPLETED -> SENT_TO_PROCESSOR
                 +-------> CHALLENGE_FAILED    -> VALIDATION_FAILED
                 +-------> CHALLENGE_TIMEOUT   -> VALIDATION_FAILED
  |
  +-------> FRICTIONLESS_AUTH   -> SENT_TO_PROCESSOR (no user action needed)
```

### 19.3 3DS Schema Addition

```text
+---------------------------+
| payment_authentications   |
|---------------------------|
| auth_id (PK)              |
| order_id (FK)             |
| eci_code                  |  (Electronic Commerce Indicator: 05=full, 06=attempted)
| authentication_value      |  (cryptogram, passed to PSP)
| ds_transaction_id         |  (card network ref)
| status                    |  (FRICTIONLESS, CHALLENGED, FAILED)
| created_at                |
+---------------------------+
```

### 19.4 Cross-Questions on 3DS

Q: What is an ECI code and why does it matter?
A: "ECI is the Electronic Commerce Indicator. ECI 05 means full 3DS authentication — liability shifts to the issuing bank if fraud occurs. ECI 06 means attempted but not completed — partial liability shift. ECI 07 means no 3DS — merchant bears full liability. At 15 years, knowing liability shift is the business reason behind 3DS."

Q: Can you skip 3DS for low-value transactions?
A: "Yes — PSD2 SCA has transaction risk analysis (TRA) exemptions for low-value transactions (under €30) and trusted beneficiaries. The gateway can request exemption in the authentication request. Issuers may still step up if their own risk model overrides. You request exemption; you cannot guarantee it."

Q: What if the 3DS challenge times out?
A: "Mark CHALLENGE_TIMEOUT -> VALIDATION_FAILED. Do not retry the challenge silently — the user must re-initiate checkout. Stale authentication values are rejected by card networks."

---

## SECTION 20: SHARDING STRATEGY (SCALE QUESTION AT 15 YEARS)

You:
"At 10K TPS sustained write, a single PostgreSQL primary will top out on payment_orders. I shard — but the key choice drives query patterns for years, so I choose it deliberately."

### 20.1 Shard Key Options and Tradeoffs

```text
Option A: Shard by merchant_id
  Pros:
  - All orders for a merchant land on one shard -> merchant dashboards are fast
  - Idempotency check (merchant_id, idempotency_key) is single-shard
  - Compliance audit queries per merchant are local
  Cons:
  - Hotspot risk: one large merchant (e.g. Amazon) monopolises a shard
  - Cross-merchant analytics require scatter-gather

Option B: Shard by order_id (hash-based)
  Pros:
  - Uniform distribution, no hotspot
  Cons:
  - Merchant dashboard queries scatter across all shards -> expensive
  - Idempotency check requires broadcast or central table

Option C: Shard by merchant_id + consistent hashing with virtual nodes
  Pros:
  - Balances load via virtual node rebalancing
  - Isolates large merchants by splitting their range across multiple physical shards
  Cons:
  - Adds routing layer complexity

CHOSEN: Option C — consistent hashing on merchant_id with virtual nodes.
Large merchants get more virtual nodes (split across more shards).
Small merchants are co-located.
```

### 20.2 Shard Architecture (ASCII)

```text
[Payment API Service]
       |
       v
[Shard Router]
  hash(merchant_id) -> virtual node -> physical shard
       |
       +-----------> Shard-1 (merchants A-F: small + 1/3 of Merchant-X)
       +-----------> Shard-2 (merchants G-M: small + 1/3 of Merchant-X)
       +-----------> Shard-3 (merchants N-Z: small + 1/3 of Merchant-X)
       +-----------> Shard-N (expand as needed)

Each shard:
  +---------------------------+
  | Primary (write)           |
  | Replica x2 (read)         |
  | Tables: payment_orders,   |
  |   attempts, refunds,      |
  |   idempotency_records     |
  +---------------------------+

Cross-shard tables (kept global, not sharded):
  +---------------------------+
  | merchants                 |  (low write volume, cacheable)
  | customers                 |  (profile reads, not payment hot path)
  | webhook_events            |  (sharded by psp_event_id separately)
  +---------------------------+

Ledger DB (separate cluster, not sharded with payment_orders):
  +---------------------------+
  | ledger_entries            |  (append-only, partition by created_at month)
  | Immutable, high-read      |
  +---------------------------+
```

### 20.3 CQRS Split for Analytics

```text
Write path: payment_orders -> sharded OLTP DB (strong consistency)
Read path:  payment_orders -> replicated OLAP store (Redshift/BigQuery/ClickHouse)

CDC pipeline:
  payment_orders change -> Debezium -> Kafka -> OLAP store

Merchant dashboards query OLAP (eventual, seconds lag).
Reconciliation queries OLAP.
Status API queries OLTP primary (strong).
```

### 20.4 Hotspot Mitigation

```text
Problem: flash sale event causes one merchant to spike 100x
Controls:
- virtual node count for that merchant pre-scaled before event
- per-merchant rate limit at API Gateway (isolate blast radius)
- read replicas absorb polling/status queries
- payment_orders write sharding keeps writes local
- circuit breaker fires per-shard if write latency spikes
```

### 20.5 Cross-Questions on Sharding

Q: Why not just use a NewSQL database like CockroachDB and skip manual sharding?
A: "Valid choice for greenfield. CockroachDB / Spanner give automatic range-based sharding with strong consistency. Tradeoff: higher write latency due to distributed consensus (Raft/Paxos), vendor/operational dependency, and less tuning control for hot-partition mitigation. At a company already on PostgreSQL with a strong DBA team, explicit sharding with a routing layer is often preferred. I'd evaluate both and choose based on operational maturity."

Q: How do you handle cross-shard queries, e.g. global reconciliation?
A: "Reconciliation runs against the OLAP store, not OLTP shards. CDC replication keeps the OLAP store seconds behind. For legal/audit queries that need exact current state, I scatter-gather across shards with a page size cap — not a real-time operation so latency is acceptable."

Q: How do you rebalance when you add a new shard?
A: "Consistent hashing means only the keys in the moved range migrate. I use a double-write phase: new shard receives writes, old shard still accepts reads. Background migration job copies historical rows. After verification, reads cut over. Zero-downtime with a read-fallback to old shard during migration window."
