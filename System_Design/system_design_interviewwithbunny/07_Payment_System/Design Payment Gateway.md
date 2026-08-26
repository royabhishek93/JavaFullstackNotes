# Design Payment Gateway - Transcript Aligned Interview Script (15+ Years)

This version is intentionally aligned to the transcript discussion order and phrasing style, but rewritten as a clean, interviewer-ready, senior conversational script with ASCII diagrams.

Print settings:
- Orientation: Landscape
- Font: Consolas or Courier New, 9-10 pt
- Margins: Narrow
- Line spacing: 1.0 or 1.05
- Export: PDF with page numbers enabled

---

## 0) How I Would Start in Interview

Interviewer, before I jump into architecture, I want to align on one critical distinction so scope is clear.

A payment gateway and a payment processor are different systems:
- Payment gateway: collects payment details securely, tokenizes, orchestrates flow, and reports status.
- Payment processor: actually talks to card network and bank to authorize/capture/settle money.

So in this design, I will build the payment gateway layer, not bank rails.

---

## 1) Functional Requirements (Transcript-Aligned)

I would state this exactly in interview style:

1. Client (merchant) should be able to create a payment intent.
2. Gateway should create a temporary checkout session/page for user card entry.
3. Gateway must securely handle PCI DSS sensitive card data.
4. Gateway should return transaction status to merchant.

Out of scope (as in transcript):
- Part payment
- Refund/return flows

---

## 2) Non-Functional Requirements (Transcript-Aligned)

- Scale target: 10,000 TPS
- Consistency over availability for money states
- Gateway-side authorization/tokenization latency target: under 200 ms
- Security posture: PCI DSS compliant zone for card data

How I phrase the CAP point:
- In payment state transitions, correctness wins. A temporarily stale status is acceptable; wrong debit state is not.

---

## 3) Core Entities (Transcript-Aligned)

- Merchant/Client
- User/Customer
- Payment Transaction
- Payment Method
- Payment Session
- Webhook/Callback

---

## 4) API Design (Transcript-Aligned)

```http
POST /v1/payment-intents
POST /v1/payment-sessions
POST /v1/payments/confirm
GET  /v1/transactions/{transactionId}
```

Intent of each:
- payment-intents: register purchase metadata, return payment_intent_id
- payment-sessions: create short-lived session + checkout URL
- payments/confirm: submit payment from hosted page to gateway backend
- transactions/{id}: merchant polls/queries current status

---

## 5) Payment Journey in 3 Main Steps (As Discussed in Transcript)

```text
Step 1: Merchant -> Gateway : Create Payment Intent
Step 2: Merchant -> Gateway : Create Payment Session (receive hosted checkout URL)
Step 3: User enters card on hosted page -> Gateway confirms payment -> Processor
```

ASCII quick flow:

```text
[User] -> [Merchant App] -> [Gateway: Intent API] -> intent_id
                            -> [Gateway: Session API] -> checkout_url(session_id)
[User Browser] -> [Gateway Hosted Checkout Page] -> [Gateway Confirm API]
                                             -> [Processor] -> [Callback] -> [Status]
```

---

## 6) High-Level Block Diagram

```text
+-------------------+           +---------------------------+
| User/Customer     | --------> | Merchant App/Backend      |
+-------------------+           +-------------+-------------+
                                              |
                                              v
                              +-------------------------------+
                              | API Gateway + Load Balancer   |
                              +---------------+---------------+
                                              |
             +--------------------------------+--------------------------------+
             |                                |                                |
             v                                v                                v
+--------------------------+      +--------------------------+      +------------------------+
| Payment Intent Service   |      | Checkout Session Service |      | Transaction Status API |
+------------+-------------+      +------------+-------------+      +-----------+------------+
             |                                 |                                 |
             v                                 v                                 v
+--------------------------+      +--------------------------+      +------------------------+
| Payment Intent DB        |      | Redis Session Store      |      | Payment Txn DB (read) |
| (RDBMS)                  |      | TTL=10 min               |      +------------------------+
+--------------------------+      +--------------------------+
                                              |
                                              | checkout URL with session_id
                                              v
                                  +------------------------------+
                                  | Hosted Checkout Frontend     |
                                  | (separate LB as needed)      |
                                  +--------------+---------------+
                                                 |
                                                 v
                                  +------------------------------+
                                  | Checkout Backend Service     |
                                  +--------------+---------------+
                                                 |
                                                 v
                                  +------------------------------+
                                  | Tokenization PCI Zone        |
                                  | (validate + fingerprint +    |
                                  | encrypt via HSM)             |
                                  +--------------+---------------+
                                                 |
                                                 v
                                  +------------------------------+
                                  | Orchestrator Service         |
                                  +--------------+---------------+
                                                 |
                                    +------------+------------+
                                    |                         |
                                    v                         v
                         +-------------------+      +-------------------+
                         | Processor Adapter |      | Processor Adapter |
                         | A                 |      | B                 |
                         +---------+---------+      +---------+---------+
                                   \                      /
                                    \                    /
                                     v                  v
                                 +--------------------------+
                                 | Processor Gateway        |
                                 | (external)               |
                                 +------------+-------------+
                                              |
                                              v
                                 +--------------------------+
                                 | Processor/Bank Network   |
                                 +------------+-------------+
                                              |
                                              v
                                 +--------------------------+
                                 | Callback Collector       |
                                 +------------+-------------+
                                              |
                                              v
                                 +--------------------------+
                                 | Kafka/Event Bus          |
                                 | topic1: callback_status  |
                                 | topic2: settlement_final |
                                 +------------+-------------+
                                              |
                                              v
                                 +--------------------------+
                                 | Reconciliation Service   |
                                 | + Ledger Finalization    |
                                 +--------------------------+
```

---

## 7) LLD View + Deep-Dive Script (Exactly How I Would Speak)

Interviewer, now I will switch from HLD to LLD and walk responsibility boundaries first, then component behavior.

### 7.1 LLD Class Diagram (ASCII)

```text
+------------------------------+
| PaymentController            |
| +createIntent(req)           |
| +createSession(req)          |
| +confirmPayment(req)         |
| +getStatus(txnId)            |
+--------------+---------------+
             |
             v
+------------------------------+        +------------------------------+
| PaymentService               |------->| IdempotencyService           |
| +createIntent(cmd)           |        | +checkAndStore(...)          |
| +createSession(cmd)          |        +------------------------------+
| +confirmPayment(cmd)         |
| +getStatus(txnId)            |------->+------------------------------+
+------+-----------------------+        | PaymentRepository            |
      |                                | +saveIntent(...)             |
      |                                | +saveAttempt(...)            |
      |                                | +findStatus(...)             |
      |                                +------------------------------+
      |
      +-------------------------------> +------------------------------+
      |                                 | PaymentOrchestrator          |
      |                                 | +transition(...)             |
      |                                 | +routeToProcessor(...)       |
      |                                 +-------------+----------------+
      |                                               |
      v                                               v
+------------------------------+         +------------------------------+
| GatewayRouter                |-------->| PSPAdapter (interface)       |
| +route(merchant,ctx)         |         | +authorize(...)              |
| +fallback(...)               |         | +verifyCallback(...)         |
+-------------+----------------+         +-------------+----------------+
            |                                         |
            v                                         v
     +-------------------+                     +-------------------+
     | ProcessorAAdapter |                     | ProcessorBAdapter |
     +-------------------+                     +-------------------+

+------------------------------+         +------------------------------+
| LedgerService                |<--------| PaymentOrchestrator          |
| +postFinalEntries(...)       |         +------------------------------+
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
| +receiveCallback(...)        |
+--------------+---------------+
               |
               v
+------------------------------+
| WebhookService               |
| +verifySignature(...)        |
| +dedupe(...)                 |
| +publishEvent(...)           |
+------------------------------+
```

### 7.2 How I Explain This LLD in Interview (Natural Script)

At the edge, PaymentController is intentionally thin. It validates request shape, extracts merchant context, and delegates.

PaymentService is the application facade. It coordinates idempotency checks, persistence, and orchestration in deterministic order. This is where I ensure retry-safe behavior before mutation.

PaymentOrchestrator is the only owner of legal state transitions. No other class should directly mutate money state. That guard prevents duplicate webhook side effects and out-of-order callback corruption.

GatewayRouter and PSPAdapter isolate provider-specific contracts. If Processor A changes payload fields, I update only Adapter A, not core business flow.

LedgerService is isolated so financial posting rules remain auditable and immutable.

WebhookController and WebhookService are split deliberately: verify signature, dedupe callback, then publish event. Raw callbacks never mutate final money state directly.

### 7.3 LLD Interaction Runtime Diagram (ASCII)

```text
Client
  |
  v
PaymentController
  |
  v
PaymentService ----> IdempotencyService ----> Idempotency Store
  |
  +----> PaymentRepository ----> Payment DB
  |
  +----> PaymentOrchestrator
             |
             +----> GatewayRouter ----> PSPAdapterA/B ----> Processor
             |
             +----> LedgerService ----> LedgerRepository ----> Ledger DB
             |
             +----> Outbox/Event Publish ----> Event Bus

Processor Callback
  |
  v
WebhookController -> WebhookService -> verify signature + dedupe -> Event Bus
                                                     |
                                                     v
                                             Orchestrator Consumer
```

### 7.4 Component Deep-Dive in Transcript Order

Payment Intent Service
- Merchant calls create intent.
- Store non-sensitive metadata: amount, currency, merchant_id, customer_id, order_id, method type.
- Generate and return payment_intent_id.

Example schema snapshot:

```text
payment_intent(
      intent_id PK,
      merchant_id,
      customer_id,
      order_id,
      amount_minor,
      currency,
      method_type,
      status,
      created_at,
      updated_at
)
```

Checkout Session Service
- Merchant sends payment_intent_id and order metadata.
- Create short-lived session in Redis with TTL=10 minutes.
- Return session_id and redirect URL: https://gateway.example.com/checkout/{session_id}

Why session_id in URL?
- Confirm API re-validates session mapping and rejects tampered requests.

Hosted Checkout Frontend
- User enters card details on gateway-hosted page, not merchant page.
- This keeps card data out of merchant PCI scope.
- At high scale, frontend can have dedicated load balancing.

Checkout Backend Validation
1. Session exists
2. Session not expired
3. Session maps to exact intent + merchant + order
4. Nonce/anti-replay check passes

If any validation fails, reject immediately.

### 7.5 What Senior Interviewers Usually Ask at This LLD Point

1. Where is idempotency enforced?
Answer: At PaymentService entry before write, plus DB unique constraints for hard guarantees.

2. Who owns legal state transitions?
Answer: PaymentOrchestrator only.

3. Where do you isolate processor-specific behavior?
Answer: PSPAdapter implementations behind GatewayRouter.

4. Where do you prevent duplicate webhook side effects?
Answer: Webhook dedupe plus orchestrator transition guards.

---

## 8) PCI Tokenization Zone (Transcript-Aligned Detail)

The transcript emphasizes 3 key operations, so I keep the same:

1. Card validation
- PAN format + Luhn checks + basic card metadata checks

2. Fingerprint generation
- fingerprint input = BIN(first 6) + last4 + expiry + cardholder name
- store fingerprint hash for dedupe/risk patterns

3. Encryption/token creation
- use HSM-backed key operations (not plain app-level key files)
- return encrypted card token to checkout backend

ASCII for tokenization path:

```text
[Checkout Backend]
      |
      v
+-------------------------+
| Tokenization Service    |
| - validate PAN          |
| - create fingerprint    |
| - call HSM for encrypt  |
+------------+------------+
             |
             v
      encrypted_card_token
```

---

## 9) Routing, Processor Selection, and Adapters

How I explain it verbally:

- I do not hardcode a single processor.
- Merchant preference decides default processor path.
- Orchestrator checks merchant preference mapping DB.
- Then it routes through processor-specific adapters.

Why adapters?
- Processor request/response contracts differ.
- Adapter pattern isolates connector differences.

ASCII adapter view:

```text
[Orchestrator] -> [Merchant Preference DB]
      |
      +--> [Adapter: Processor A] --> [Processor Gateway]
      |
      +--> [Adapter: Processor B] --> [Processor Gateway]
```

---

## 10) Callback, Eventing, and Reconciliation

Important transcript point: immediate processor acknowledgement is not final money confirmation.

So I separate two asynchronous truth channels:

1. Immediate callback status topic
- processor accepted/rejected/pending signal
- used for near-real-time UX status updates

2. Delayed settlement/final topic
- arrives later (hours/day), represents stronger financial finality
- used by reconciliation to mark final ledger truth

ASCII event model:

```text
[Processor Callback Collector]
          |
          +--> topic: callback_status (near-real-time)
          |
          +--> topic: settlement_final (delayed finality)

[Orchestrator Consumer] reads callback_status -> updates payment status
[Reconcile Service] reads settlement_final -> posts final ledger state
```

Reconciliation outcome states:
- MATCHED_SUCCESS
- MATCHED_FAILED
- MISMATCH_REVIEW

---

## 11) Sequence Diagram (Detailed)

```text
User      Merchant      IntentSvc      SessionSvc     CheckoutFE    CheckoutBE   TokenSvc   Orchestrator  Processor
 |            |             |              |              |             |            |            |           |
 | buy now    |             |              |              |             |            |            |           |
 |----------->|             |              |              |             |            |            |           |
 |            | create intent              |              |             |            |            |           |
 |            |------------>| save DB      |              |             |            |            |           |
 |            |<------------| intent_id    |              |             |            |            |           |
 |            | create session             |              |             |            |            |           |
 |            |--------------------------->| save Redis   |             |            |            |           |
 |            |<---------------------------| checkout_url |             |            |            |           |
 | redirect to checkout_url                |              |             |            |            |           |
 |---------------------------------------->|              |             |            |            |           |
 | card details submit                                    |-----------> | validate    |            |           |
 |                                                        |             |-----------> | tokenize   |           |
 |                                                        |             |<----------- | token      |           |
 |                                                        |             |------------------------->| route     |
 |                                                        |             |                          |---------> |
 |                                                        |             |                          |<--------- |
 | poll status                                            |-----------> | read status |            |           |
 |<-------------------------------------------------------|              |             |            |           |
```

---

## 12) Payment State Diagram (ASCII)

```text
CREATED -> SESSION_CREATED -> PROCESSING -> SENT_TO_PROCESSOR
                                      |              |
                                      |              +--> CALLBACK_PENDING
                                      |                        |
                                      |                        +--> SUCCESS_ACK
                                      |                        +--> FAILED_ACK
                                      |
                                      +--> VALIDATION_FAILED

SUCCESS_ACK/FAILED_ACK are not always final settlement truth.
Final truth comes after reconciliation:
SUCCESS_ACK -> RECON_SUCCESS or RECON_MISMATCH
FAILED_ACK  -> RECON_FAILED  or RECON_MISMATCH
```

---

## 13) Tradeoffs and Edge Questions (15-Year Level)

Tradeoffs I call out explicitly:

1. Consistency vs availability
- For financial state writes, consistency wins.

2. Sync status vs async finality
- Sync API gives acceptance status quickly.
- Async callback/reconciliation gives final truth.

3. Single processor vs multi-processor routing
- Single is simpler.
- Multi gives resilience and better success-rate control.

4. Redis-only vs RDBMS+Redis
- Redis for short-lived session speed.
- RDBMS for durable financial correctness.

Edge questions I would ask interviewer:
1. Card-only or include UPI/netbanking/wallet?
2. Is auth-capture split needed, or immediate capture only?
3. Multi-region active-active required from day one?
4. Accepted pending duration SLA for merchant UX?
5. Processor priority: success rate first or MDR cost first?

---

## 14) Security and Observability Summary

Security:
- PAN/CVV only in PCI zone
- TLS everywhere, mTLS for internal high-risk links
- HSM-backed encryption/tokenization
- Signed callbacks/webhooks and replay protection
- No raw card data in app logs

Observability:
- Success rate by processor/BIN/issuer
- p95/p99 latency by stage
- Callback lag and reconciliation lag
- Unknown/pending age buckets
- Duplicate callback suppression count

---

## 15) Closing Script (Natural Interview Finish)

To summarize, my gateway design follows the transcript flow exactly:
- intent creation
- session generation with hosted checkout
- secure tokenization in PCI boundary
- processor routing through orchestrator/adapters
- immediate callback handling
- delayed reconciliation for final money truth

The core principle is simple: do not optimize first for speed, optimize first for financial correctness, then scale and latency.

If you want, I can now deep-dive into one specific area: idempotency model, reconciliation algorithm, or multi-processor failover strategy.
