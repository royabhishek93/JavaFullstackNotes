# Payment Gateway — Deep Dive System Design

---

## Table of Contents

1. [Core Concepts: Gateway vs Processor](#1-core-concepts-gateway-vs-processor)
2. [High-Level Design (HLD)](#2-high-level-design-hld)
3. [Full Payment Flow — Sequence Diagram](#3-full-payment-flow--sequence-diagram)
4. [Low-Level Design (LLD) — Component Diagram](#4-low-level-design-lld--component-diagram)
5. [PCI Zone — Tokenization Deep Dive](#5-pci-zone--tokenization-deep-dive)
6. [Event-Driven Architecture — Kafka + Reconciliation](#6-event-driven-architecture--kafka--reconciliation)
7. [Component Choices — Why We Picked Each One](#7-component-choices--why-we-picked-each-one)
8. [Failure Cases & Edge Cases](#8-failure-cases--edge-cases)
9. [Interview Questions — Basic → Advanced → Traps](#9-interview-questions--basic--advanced--traps)

---

## 1. Core Concepts: Gateway vs Processor

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PAYMENT ECOSYSTEM OVERVIEW                           │
│                                                                         │
│  ┌──────────┐      ┌──────────────────┐      ┌────────────────────┐    │
│  │          │      │  PAYMENT GATEWAY │      │  PAYMENT PROCESSOR │    │
│  │   User   │      │                  │      │                    │    │
│  │          │      │  • Collects card  │      │  • Talks to bank   │    │
│  │  Enters  │─────►│    details        │─────►│  • Authorizes txn  │    │
│  │  Card    │      │  • Tokenizes PAN  │      │  • Captures money  │    │
│  │  Details │      │  • Orchestrates   │      │  • Settles funds   │    │
│  │          │      │    flow           │      │                    │    │
│  └──────────┘      └──────────────────┘      └────────────────────┘    │
│                             │                          │                │
│                   "Traffic Controller"          "Moves the Money"       │
│                                                         │               │
│                                               ┌─────────▼──────────┐   │
│                                               │       BANK          │   │
│                                               │  (Issuing/Acquiring)│   │
│                                               └────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘

  Payment Gateway  = orchestration layer (our responsibility)
  Payment Processor = financial network entity (external, e.g. Razorpay, PayU)
  Bank             = ultimate money holder (out of scope)
```

**Key Insight:** We are designing the Gateway only. We never touch the actual bank debit/credit. The processor is a black box we call via API.

---

### Why this diagram exists
The gateway/processor split is the single most common wrong assumption in interviews. Most candidates jump straight into "system that moves money" — which is out of scope. This diagram sets the contract: **gateway owns card capture + tokenization + routing; processor owns bank communication**. If you blur this line, every subsequent design decision becomes incoherent.

### Design choices made here
- Gateway is stateless with respect to banking — it never stores a bank account balance or triggers a debit directly.
- Gateway is responsible for PCI DSS compliance; the processor has its own compliance (usually higher-tier).
- The bank is split into issuing bank (cardholder's bank) and acquiring bank (merchant's bank) — both handled transparently by the processor.

### Cross questions an interviewer will ask
| Question | What they're testing |
|---|---|
| "Why can't Amazon just call the bank directly?" | Whether you know PCI scope and processor licensing |
| "Who is liable if the processor goes down?" | Gateway SLA vs processor SLA distinction |
| "Can one company be both gateway and processor?" | Yes (Stripe, Square) — but they are two logical layers |
| "What is the difference between authorization and settlement?" | Auth = bank reserves funds; Settlement = funds actually move (T+1/T+2) |
| "What is an acquiring bank vs issuing bank?" | Issuing = cardholder's bank; Acquiring = merchant's bank; processor sits between |

---

## 2. High-Level Design (HLD)

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         HIGH-LEVEL DESIGN                                  │
│                                                                            │
│   ┌──────┐     ┌────────────┐                                              │
│   │ User │────►│  Merchant  │  (Amazon, Flipkart, Walmart — our clients)   │
│   └──────┘     └─────┬──────┘                                              │
│                      │                                                      │
│                      ▼                                                      │
│          ┌───────────────────────┐                                         │
│          │   API Gateway +       │  ← Auth, Rate-limiting, Routing         │
│          │   Load Balancer       │                                         │
│          └──────────┬────────────┘                                         │
│                     │                                                       │
│         ┌───────────┼───────────────────────┐                              │
│         ▼           ▼                       ▼                              │
│  ┌──────────┐ ┌───────────┐        ┌────────────────┐                     │
│  │ Payment  │ │ Checkout  │        │    Checkout    │                     │
│  │ Intent   │ │ Session   │        │    Backend     │                     │
│  │ Service  │ │ Service   │        │    Service     │                     │
│  └────┬─────┘ └─────┬─────┘        └───────┬────────┘                     │
│       │             │                       │                              │
│       ▼             ▼                       ▼                              │
│  ┌─────────┐  ┌──────────┐         ┌──────────────┐                       │
│  │Payment  │  │  Redis   │         │ Orchestrator │                       │
│  │Intent DB│  │  Cache   │         │   Service    │                       │
│  │(Postgres)│  │ (Session)│         └──────┬───────┘                       │
│  └─────────┘  └──────────┘                │                               │
│                                           ▼                               │
│                              ┌─────────────────────────┐                  │
│                              │   Processor Connectors  │                  │
│                              │  ┌──────┐  ┌──────────┐ │                  │
│                              │  │PayU  │  │Razorpay  │ │                  │
│                              │  │Conn. │  │Conn.     │ │                  │
│                              │  └──────┘  └──────────┘ │                  │
│                              └───────────┬─────────────┘                  │
│                                          │                                │
│                                          ▼                                │
│                              ┌─────────────────────┐                      │
│                              │  External Processor │                      │
│                              │  Gateway (PayU,      │                      │
│                              │  Razorpay, Stripe)  │                      │
│                              └──────────┬──────────┘                      │
│                                         │                                 │
│                                         ▼                                 │
│                                     ┌───────┐                             │
│                                     │  Bank │                             │
│                                     └───────┘                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### Why this diagram exists
This is the 10,000-foot view. Its purpose is to show **what microservices exist and how traffic flows** — not how each service works internally. Interviewers use this to check if you understand microservice decomposition and the role of an API Gateway.

### Design choices made here
- **Microservice architecture** — chosen because 10k TPS requires independent scaling per service. A monolith cannot scale the checkout page separately from tokenization.
- **API Gateway + Load Balancer at the front** — single entry point for auth/rate-limiting. All merchant API keys are validated here before any downstream service sees a request.
- **Three distinct services** (Intent, Session, Backend) — each maps to one step in the payment lifecycle. They have different scaling needs, different DB dependencies, and different SLAs.
- **Processor Connectors as a separate layer** — the orchestrator doesn't know PayU's API schema; adapters absorb that complexity.

### Cross questions an interviewer will ask
| Question | What they're testing |
|---|---|
| "Why not put all three services into one?" | Independent scalability, single-responsibility principle |
| "What does the API Gateway do that a Load Balancer doesn't?" | API GW handles auth, rate limiting, request transformation; LB only distributes traffic |
| "Why are there multiple databases instead of one?" | Service isolation — each service owns its data; shared DB = tight coupling |
| "What happens if the Orchestrator service goes down?" | Retries, circuit breaker, dead-letter queue — Kafka retains events |
| "How do you handle service discovery in microservices?" | Kubernetes DNS / Consul / Eureka; services register and discover each other |

---

## 3. Full Payment Flow — Sequence Diagram

```
┌──────┐    ┌──────────┐    ┌───────────────┐    ┌────────────────┐    ┌───────────┐    ┌──────┐
│ User │    │ Merchant │    │Payment Gateway│    │  Processor     │    │ Callback  │    │ Bank │
└──┬───┘    └────┬─────┘    └───────┬───────┘    └──────┬─────────┘    │  Service  │    └──┬───┘
   │             │                  │                    │              └─────┬─────┘       │
   │ Click       │                  │                    │                    │              │
   │ "Buy Now"   │                  │                    │                    │              │
   │────────────►│                  │                    │                    │              │
   │             │                  │                    │                    │              │
   │             │ POST             │                    │                    │              │
   │             │ /payment-intent  │                    │                    │              │
   │             │ {amount,         │                    │                    │              │
   │             │  currency,       │                    │                    │              │
   │             │  merchant_id,    │                    │                    │              │
   │             │  order_id}       │                    │                    │              │
   │             │─────────────────►│                    │                    │              │
   │             │                  │ Save to            │                    │              │
   │             │                  │ PaymentIntentDB    │                    │              │
   │             │                  │ (Postgres)         │                    │              │
   │             │                  │──────────┐         │                    │              │
   │             │                  │          │         │                    │              │
   │             │                  │◄─────────┘         │                    │              │
   │             │ 200 OK           │                    │                    │              │
   │             │ {intent_id: X}   │                    │                    │              │
   │             │◄─────────────────│                    │                    │              │
   │             │                  │                    │                    │              │
   │             │ POST             │                    │                    │              │
   │             │ /session         │                    │                    │              │
   │             │ {intent_id: X}   │                    │                    │              │
   │             │─────────────────►│                    │                    │              │
   │             │                  │ Save session to    │                    │              │
   │             │                  │ Redis (TTL=10min)  │                    │              │
   │             │                  │──────────┐         │                    │              │
   │             │                  │          │         │                    │              │
   │             │                  │◄─────────┘         │                    │              │
   │             │ 200 OK           │                    │                    │              │
   │             │ {session_id: S,  │                    │                    │              │
   │             │  url: gw.io/S}   │                    │                    │              │
   │             │◄─────────────────│                    │                    │              │
   │             │                  │                    │                    │              │
   │ Redirect to │                  │                    │                    │              │
   │ gw.io/S     │                  │                    │                    │              │
   │◄────────────│                  │                    │                    │              │
   │             │                  │                    │                    │              │
   │ Checkout    │                  │                    │                    │              │
   │ Page Loads  │                  │                    │                    │              │
   │ (hosted by  │                  │                    │                    │              │
   │  Gateway)   │                  │                    │                    │              │
   │             │                  │                    │                    │              │
   │ Enter card  │                  │                    │                    │              │
   │ details     │                  │                    │                    │              │
   │ Click Pay   │                  │                    │                    │              │
   │─────────────────────────────►  │                    │                    │              │
   │             │                  │ 1. Validate        │                    │              │
   │             │                  │    session (Redis) │                    │              │
   │             │                  │ 2. Tokenize card   │                    │              │
   │             │                  │    (PCI Zone)      │                    │              │
   │             │                  │ 3. Orchestrate →   │                    │              │
   │             │                  │    pick processor  │                    │              │
   │             │                  │──────────────────► │                    │              │
   │             │                  │                    │ Authorize with     │              │
   │             │                  │                    │ Bank               │              │
   │             │                  │                    │───────────────────────────────────►│
   │             │                  │                    │                    │ ACK: order   │
   │             │                  │                    │◄───────────────────────────────────│
   │             │                  │                    │ Async callback     │              │
   │             │                  │                    │───────────────────►│              │
   │             │                  │◄─────────────────────────────────────── │              │
   │             │                  │ Update             │                    │              │
   │             │                  │ PaymentTxnDB       │                    │              │
   │ Poll status │                  │                    │                    │              │
   │─────────────────────────────►  │                    │                    │              │
   │ 200 {status: "success"}        │                    │                    │              │
   │◄─────────────────────────────  │                    │                    │              │
   │             │                  │                    │                    │              │
   │             │  Webhook         │                    │                    │              │
   │             │◄─────────────────│                    │                    │              │
```

### Why this diagram exists
The sequence diagram shows **time-ordered interactions** between every actor. It answers the question "who calls whom and in what order?" — which is exactly what interviewers probe when they ask you to walk through a payment. Without this, you risk describing steps out of order or skipping the async callback entirely.

### Design choices made here
- **Three separate API calls** (intent → session → pay) instead of one big call — each step has a different responsibility and a different failure mode. Merging them would mean one timeout kills the whole flow.
- **Merchant makes the first two calls; user's browser makes the third** — this is intentional. Card data must never pass through the merchant's server. The browser submits directly to the gateway's checkout backend.
- **Poll for status (not wait on the pay response)** — the pay call is async. The browser polls because the processor → bank round-trip can take seconds. A synchronous wait would hold an HTTP connection open and break under load.
- **Webhook to merchant after final status** — the merchant needs to update their order system. This is a server-to-server push, decoupled from the user's browser session.

### Cross questions an interviewer will ask
| Question | What they're testing |
|---|---|
| "Why does the browser poll instead of using WebSockets?" | Polling is simpler, stateless, and works behind proxies. WebSockets are valid but overkill for a one-time transaction. |
| "What if the merchant's server never receives the webhook?" | Retry with exponential backoff + dead-letter queue + merchant can always poll `/transaction/{id}` |
| "Why does the gateway send a redirect URL instead of a full HTML page?" | Separation of concerns — session service creates session data; frontend service renders HTML. Also allows CDN caching of the checkout page template. |
| "What HTTP status codes does each step return?" | Intent: 201 Created; Session: 200 with URL; Pay: 202 Accepted (async); Poll: 200 with status field |
| "What if the intent_id in the session request doesn't match any record?" | Return 400/404. Gateway must validate intent_id exists and belongs to the calling merchant before creating a session. |

---

## 4. Low-Level Design (LLD) — Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              PAYMENT GATEWAY — FULL LLD                                     │
│                                                                                             │
│   ┌──────┐         ┌──────────────────────────────────────────────────────────────────────┐│
│   │ User │         │                   PAYMENT GATEWAY ECOSYSTEM                          ││
│   └──┬───┘         │                                                                      ││
│      │             │  ┌────────┐       ┌────────────────────────────────────────────┐    ││
│   ┌──▼──────────┐  │  │  API   │       │         STEP 1: PAYMENT INTENT             │    ││
│   │  Merchant   │──┼─►│Gateway │──────►│                                            │    ││
│   │  (Amazon,   │  │  │  +LB   │       │  ┌────────────────────┐  ┌──────────────┐ │    ││
│   │  Flipkart)  │  │  └────────┘       │  │  Payment Intent    │  │ PaymentIntent│ │    ││
│   └─────────────┘  │                   │  │  Service           │─►│ DB (Postgres)│ │    ││
│                    │                   │  │                    │  │              │ │    ││
│                    │                   │  │ Captures:          │  │ intent_id    │ │    ││
│                    │                   │  │ • amount           │  │ amount       │ │    ││
│                    │                   │  │ • currency         │  │ currency     │ │    ││
│                    │                   │  │ • merchant_id      │  │ merchant_id  │ │    ││
│                    │                   │  │ • order_id         │  │ customer_id  │ │    ││
│                    │                   │  │ • customer_id      │  │ status       │ │    ││
│                    │                   │  │                    │  │ created_at   │ │    ││
│                    │                   │  │ Returns: intent_id │  └──────────────┘ │    ││
│                    │                   │  └────────────────────┘                   │    ││
│                    │                   └────────────────────────────────────────────┘    ││
│                    │                                                                      ││
│                    │                   ┌────────────────────────────────────────────┐    ││
│                    │                   │         STEP 2: CHECKOUT SESSION           │    ││
│                    │                   │                                            │    ││
│                    │                   │  ┌────────────────────┐  ┌──────────────┐ │    ││
│                    │                   │  │  Checkout Session  │  │  Redis       │ │    ││
│                    │                   │  │  Service           │─►│  Cluster     │ │    ││
│                    │                   │  │                    │  │  (TTL=10min) │ │    ││
│                    │                   │  │ Receives:          │  │              │ │    ││
│                    │                   │  │ • intent_id        │  │ session_id   │ │    ││
│                    │                   │  │ • txn metadata     │  │ intent_id    │ │    ││
│                    │                   │  │                    │  │ merchant_id  │ │    ││
│                    │                   │  │ Returns:           │  │ order_id     │ │    ││
│                    │                   │  │ • session_id       │  │ expiry       │ │    ││
│                    │                   │  │ • redirect_url:    │  └──────────────┘ │    ││
│                    │                   │  │   gw.io/{sess_id}  │                   │    ││
│                    │                   │  └────────────────────┘                   │    ││
│                    │                   │           │                               │    ││
│                    │                   │           ▼                               │    ││
│                    │                   │  ┌─────────────────────────────────────┐  │    ││
│                    │                   │  │  Checkout Frontend Service          │  │    ││
│                    │                   │  │  (Separate LB → CDN-backed)         │  │    ││
│                    │                   │  │  Serves HTML page for card entry    │  │    ││
│                    │                   │  │  Timer shown = Redis TTL            │  │    ││
│                    │                   │  └─────────────────────────────────────┘  │    ││
│                    │                   └────────────────────────────────────────────┘    ││
│                    │                                                                      ││
│                    │                   ┌────────────────────────────────────────────┐    ││
│                    │                   │         STEP 3: PAYMENT PROCESSING         │    ││
│                    │                   │                                            │    ││
│                    │                   │  ┌─────────────────────┐                  │    ││
│                    │                   │  │ Checkout Backend     │                  │    ││
│                    │                   │  │ Service              │                  │    ││
│                    │                   │  │                      │                  │    ││
│                    │                   │  │ Validates:           │                  │    ││
│                    │                   │  │ 1. Session exists?   │──► Redis         │    ││
│                    │                   │  │ 2. Session expired?  │                  │    ││
│                    │                   │  │ 3. Intent valid?     │                  │    ││
│                    │                   │  └──────────┬───────────┘                  │    ││
│                    │                   │             │ (all valid)                  │    ││
│                    │                   │             ▼                              │    ││
│                    │                   │  ┌──────────────────────────────────────┐  │    ││
│                    │                   │  │         PCI ZONE (TLS only)          │  │    ││
│                    │                   │  │                                      │  │    ││
│                    │                   │  │  ┌──────────────────────────────┐    │  │    ││
│                    │                   │  │  │  Tokenization Service        │    │  │    ││
│                    │                   │  │  │                              │    │  │    ││
│                    │                   │  │  │  1. Validate card number     │    │  │    ││
│                    │                   │  │  │  2. Generate Fingerprint     │    │  │    ││
│                    │                   │  │  │     BIN(6) + last4 +         │    │  │    ││
│                    │                   │  │  │     expiry + name → hash     │    │  │    ││
│                    │                   │  │  │  3. Encrypt PAN via HSM      │    │  │    ││
│                    │                   │  │  │     (Hardware Security       │    │  │    ││
│                    │                   │  │  │      Module)                 │    │  │    ││
│                    │                   │  │  │  Returns: encrypted_token    │    │  │    ││
│                    │                   │  │  └──────────────────────────────┘    │  │    ││
│                    │                   │  └──────────────────────────────────────┘  │    ││
│                    │                   │             │                              │    ││
│                    │                   │             ▼                              │    ││
│                    │                   │  ┌────────────────────────────────────┐    │    ││
│                    │                   │  │   Orchestrator Service             │    │    ││
│                    │                   │  │                                    │    │    ││
│                    │                   │  │  1. Read MerchantPreferenceDB      │    │    ││
│                    │                   │  │  2. Pick connector (PayU/Razorpay) │    │    ││
│                    │                   │  │  3. Save txn record (status=SENT) →│    │    ││
│                    │                   │  │     PaymentTransactionDB           │    │    ││
│                    │                   │  │  4. Call Connector → Processor     │    │    ││
│                    │                   │  └────────────┬───────────────────────┘    │    ││
│                    │                   │               │                            │    ││
│                    │                   │    ┌──────────┴──────────┐                 │    ││
│                    │                   │    ▼                     ▼                 │    ││
│                    │                   │  ┌──────┐          ┌──────────┐            │    ││
│                    │                   │  │ PayU │          │ Razorpay │            │    ││
│                    │                   │  │Conn. │          │  Conn.   │            │    ││
│                    │                   │  └──┬───┘          └────┬─────┘            │    ││
│                    │                   └─────┼───────────────────┼──────────────────┘    ││
│                    │                         └─────────┬─────────┘                       ││
│                    │                                   ▼                                 ││
│                    │                      ┌────────────────────────┐                     ││
│                    │                      │  External Processor    │                     ││
│                    │                      │  Gateway               │                     ││
│                    │                      │  (PayU / Razorpay /    │                     ││
│                    │                      │   Stripe)              │ ──► Bank            ││
│                    │                      └────────────────────────┘                     ││
│                    └──────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Why this diagram exists
This is the diagram you draw during the deep-dive phase of the interview. It maps every service to its **internal logic, DB schema, and communication pattern**. It answers: "how does each service actually work?" — not just that it exists.

### Design choices made here

**Step 1 — Payment Intent Service**
- Writes to PostgreSQL immediately because this is a durable business record. Intent must survive for reconciliation days later — Redis would lose it on restart.
- Returns `intent_id` as the only response. No card data here yet; the merchant only provides order metadata.

**Step 2 — Checkout Session Service + Redis**
- Redis TTL = 10 minutes maps directly to the countdown timer in the UI. When TTL expires the session is gone — no cron job needed.
- The redirect URL embeds the `session_id` so the checkout backend can validate it on the Pay request. Without this, any request could fake a payment.
- A separate Checkout Frontend Service (behind its own LB and CDN) serves the HTML page — it scales differently from backend services and doesn't need API key auth.

**Step 3 — Checkout Backend → PCI Zone → Orchestrator**
- Three validations before touching card data: session exists, session not expired, intent valid. Fail fast before expensive HSM operations.
- PCI Zone is a hard network boundary (isolated VPC subnet, mTLS). Only the Checkout Backend has ingress permission to the Tokenization Service.
- Orchestrator writes `status=SENT` to PaymentTransactionDB **before** calling the processor — ensures we have a record even if the processor call hangs.
- Adapter pattern on connectors means the orchestrator is completely decoupled from processor API schemas.

### Cross questions an interviewer will ask
| Question | What they're testing |
|---|---|
| "What schema does PaymentTransactionDB have?" | `txn_id, intent_id, session_id, merchant_id, amount, currency, status, processor, created_at, updated_at` |
| "Why does the Checkout Backend do 3 validation steps in sequence, not parallel?" | Each depends on the previous — can't check session expiry if session doesn't exist |
| "What is mTLS and why use it for the PCI zone?" | Mutual TLS — both client and server present certs. Prevents any rogue service from calling the tokenization service even inside the internal network |
| "Why is the Checkout Frontend behind a separate LB?" | It serves static-ish HTML at browser scale; API Gateway adds unnecessary auth overhead and can't sit behind a CDN efficiently |
| "What happens if MerchantPreferenceDB is down when the Orchestrator reads it?" | Circuit breaker: use cached preference (Redis or in-memory) for X minutes; if cache also empty, default to primary processor or return 503 |

---

## 5. PCI Zone — Tokenization Deep Dive

```
┌───────────────────────────────────────────────────────────────────┐
│                    PCI DSS ZONE (TLS Boundary)                    │
│                                                                   │
│   Input: Raw card data from Checkout Backend                      │
│   {card_number, cvv, expiry, name}                                │
│                                                                   │
│   ┌─────────────────────────────────────────────────────────┐    │
│   │               TOKENIZATION SERVICE                      │    │
│   │                                                         │    │
│   │   STEP 1 — Card Validation                              │    │
│   │   ┌─────────────────────────────────────────────┐       │    │
│   │   │  Luhn Algorithm check on card_number        │       │    │
│   │   │  CVV length / format check                  │       │    │
│   │   │  Expiry date check                          │       │    │
│   │   └────────────────────┬────────────────────────┘       │    │
│   │                        │ valid                          │    │
│   │                        ▼                                │    │
│   │   STEP 2 — Fingerprint Generation                       │    │
│   │   ┌─────────────────────────────────────────────┐       │    │
│   │   │                                             │       │    │
│   │   │   card_number: 4111 1111 1111 1234          │       │    │
│   │   │   ├── BIN (first 6): 411111  ─────────────┐ │       │    │
│   │   │   ├── last 4:         1234  ───────────────┤ │       │    │
│   │   │   ├── expiry:         12/27 ───────────────┤ │       │    │
│   │   │   └── name:           John ───────────────►│ │       │    │
│   │   │                                     SHA256 │ │       │    │
│   │   │                                     hash   │ │       │    │
│   │   │                                     ───────┘ │       │    │
│   │   │   fingerprint = "a3f9...bc12"               │       │    │
│   │   │   (used for dedup — same card = same hash)  │       │    │
│   │   └────────────────────┬────────────────────────┘       │    │
│   │                        │                                │    │
│   │                        ▼                                │    │
│   │   STEP 3 — PAN Encryption via HSM                       │    │
│   │   ┌─────────────────────────────────────────────┐       │    │
│   │   │                                             │       │    │
│   │   │  ┌──────────────┐     ┌──────────────────┐  │       │    │
│   │   │  │ Tokenization │     │  HSM              │  │       │    │
│   │   │  │ Service      │────►│  (Hardware        │  │       │    │
│   │   │  │              │     │   Security        │  │       │    │
│   │   │  │ sends PAN    │     │   Module)         │  │       │    │
│   │   │  └──────────────┘     │                  │  │       │    │
│   │   │                       │  Key never        │  │       │    │
│   │   │                       │  leaves HSM       │  │       │    │
│   │   │                       │  hardware chip    │  │       │    │
│   │   │                       └────────┬─────────┘  │       │    │
│   │   │                                │             │       │    │
│   │   │                    encrypted_token = "ENC_T_xyz"     │    │
│   │   └────────────────────────────────┬────────────┘       │    │
│   │                                    │                    │    │
│   │   Output: { encrypted_token,       │                    │    │
│   │             fingerprint,           │                    │    │
│   │             bin,                   │                    │    │
│   │             last4,                 │                    │    │
│   │             expiry }               │                    │    │
│   └────────────────────────────────────┼────────────────────┘    │
│                                        │                         │
└────────────────────────────────────────┼─────────────────────────┘
                                         │
                            Passed to Orchestrator Service
                            (raw card data NEVER leaves PCI zone)

┌───────────────────────────────────────────────────────────────────┐
│   WHY HSM INSTEAD OF A SOFTWARE KEY STORE?                        │
│                                                                   │
│   Software Key Store      vs      HSM                            │
│   ─────────────────                ───────────────────           │
│   Key lives in memory/disk         Key baked into silicon chip   │
│   Can be extracted if hacked       Physically impossible to read  │
│   Software cert rotation           FIPS 140-2 Level 3 certified  │
│   Slower compliance audit          Required for PCI-DSS L1       │
└───────────────────────────────────────────────────────────────────┘
```

### Why this diagram exists
This is the most security-critical part of the entire design. PCI DSS requires that raw card data never be stored, logged, or transmitted in plaintext. This diagram shows **exactly how a 16-digit card number is transformed into an opaque token** that can safely be passed to processors and stored in databases.

### Design choices made here

**Step 1 — Luhn check before anything else**
- Fail fast. If the card number is structurally invalid, there's no point encrypting it or calling the processor. Luhn is O(n) and costs zero I/O.

**Step 2 — Fingerprint (not the full PAN)**
- The fingerprint lets the system detect if the same card is being used again (for fraud velocity checks, saved cards, dedup) — without ever storing the actual card number.
- SHA-256 is one-way: even if the fingerprint DB leaks, you cannot reverse it back to the card number.
- BIN (first 6 digits) is kept visible because it identifies the issuing bank — needed by the orchestrator to pick the right processor for some routing strategies.

**Step 3 — HSM for encryption (not a software vault)**
- The encryption key never leaves the HSM chip. Even if the Tokenization Service is fully compromised, the attacker gets the encrypted token but not the key to decrypt it.
- HSM is FIPS 140-2 Level 3 certified — a requirement for PCI DSS Level 1 merchants.
- Software vaults (HashiCorp Vault, AWS KMS) are used for other secrets — but for the PAN itself, hardware isolation is mandated.

**TLS-only communication (not HTTPS)**
- mTLS between Checkout Backend and Tokenization Service. HTTPS is browser-to-server; mTLS is service-to-service with mutual cert validation. Ensures only the Checkout Backend can initiate tokenization — not any rogue internal service.

### Cross questions an interviewer will ask
| Question | What they're testing |
|---|---|
| "What is the Luhn algorithm?" | A simple checksum on card numbers. Sum of digits formula that catches typos — not a security check. |
| "Why store a fingerprint at all? Why not just the token?" | Fingerprint enables dedup (same card = same hash) and fraud velocity checks without decrypting the token |
| "What is a BIN number used for?" | Identifies issuing bank and card network (Visa/Mastercard) — used for routing, currency validation, and fraud rules |
| "What happens to the raw card data after tokenization?" | It is NEVER written anywhere. Exists only in Tokenization Service memory during the encryption cycle, then discarded. |
| "Can you decrypt the encrypted token to get the PAN back?" | Yes, but only via the HSM. The HSM decrypts on-demand for the processor call — the token is not permanently decryptable by any software process. |
| "What if the HSM cluster goes down?" | No payment can be processed — this is a hard dependency. Mitigation: active-active HSM cluster with automatic failover. Circuit breaker returns 503 to the user. |

---

## 6. Event-Driven Architecture — Kafka + Reconciliation

```
┌──────────────────────────────────────────────────────────────────────────────┐
│               ASYNC FLOW: CALLBACK + RECONCILIATION                          │
│                                                                              │
│                                                                              │
│  ┌──────────────┐   async call    ┌──────────────────────────────────────┐  │
│  │ Orchestrator │────────────────►│         External Processor           │  │
│  │ Service      │                 │     (PayU / Razorpay / Stripe)       │  │
│  └──────┬───────┘                 └──────────┬───────────────────────────┘  │
│         │                                    │                              │
│         │ saves status=SENT                  │ Two callbacks:               │
│         ▼                                    │  1. Immediate ACK            │
│  ┌──────────────┐                            │     (order placed)           │
│  │  Payment     │                            │  2. Delayed Final            │
│  │  Transaction │                            │     status (~24h)            │
│  │  DB          │                            │                              │
│  │  (Postgres)  │                            │                              │
│  └──────────────┘                            │                              │
│                                              │                              │
│                         ┌────────────────────▼──────────────────────────┐  │
│                         │            Collector Callback Service          │  │
│                         └────────────────────┬──────────────────────────┘  │
│                                              │                              │
│                                              ▼                              │
│                         ┌────────────────────────────────────────────────┐  │
│                         │                KAFKA BROKER                    │  │
│                         │                                                │  │
│                         │   Topic 1: payment.processor.callback_status  │  │
│                         │   ┌─────────────────────────────────────────┐ │  │
│                         │   │ {txn_id, status: "ORDER_PLACED",        │ │  │
│                         │   │  timestamp: NOW,                        │ │  │
│                         │   │  processor: "razorpay"}                 │ │  │
│                         │   └─────────────────────────────────────────┘ │  │
│                         │   (Immediate — comes back in seconds)          │  │
│                         │                                                │  │
│                         │   Topic 2: payment.processor.final_status     │  │
│                         │   ┌─────────────────────────────────────────┐ │  │
│                         │   │ {txn_id, status: "SUCCESS" / "FAILED",  │ │  │
│                         │   │  settled_amount, timestamp: T+24h}      │ │  │
│                         │   └─────────────────────────────────────────┘ │  │
│                         │   (Delayed — comes back after bank settlement) │  │
│                         └──────────────┬───────────────────────────────┘  │
│                                        │                                   │
│              ┌─────────────────────────┼──────────────────────────┐        │
│              ▼                         ▼                          ▼        │
│    ┌──────────────────┐    ┌──────────────────────┐   ┌────────────────┐  │
│    │  Orchestrator    │    │  Reconcile Service   │   │  Webhook       │  │
│    │  Service         │    │                      │   │  Service       │  │
│    │  (consumer)      │    │  (consumer)          │   │  (consumer)    │  │
│    │                  │    │                      │   │                │  │
│    │  Reads Topic 1   │    │  Reads Topic 2       │   │  Sends webhook │  │
│    │  Updates status  │    │  Tallies with        │   │  to merchant   │  │
│    │  in TxnDB        │    │  PaymentIntentDB      │   │  on final      │  │
│    │  status=PLACED   │    │  Writes ledger table │   │  status        │  │
│    └──────────────────┘    │  (immutable record)  │   └────────────────┘  │
│                            └──────────────────────┘                       │
│                                                                            │
│   RECONCILIATION FLOW (T + 24h):                                           │
│   ┌────────────────────────────────────────────────────────────────────┐  │
│   │                                                                    │  │
│   │  PaymentTxnDB (status=PLACED)  ◄──── Reconcile ────► BankLedger  │  │
│   │         ↓                                                          │  │
│   │  If bank says SUCCESS → mark SETTLED, notify merchant via webhook  │  │
│   │  If bank says FAILED  → mark FAILED, trigger refund if needed      │  │
│   │  If no response yet   → retry after another 24h (up to 3x)        │  │
│   │                                                                    │  │
│   └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Why this diagram exists
The processor callback is **asynchronous and unreliable** — the gateway never knows exactly when it will arrive or if it will arrive at all. This diagram shows how Kafka acts as a durable buffer between the callback and the multiple services that need to act on it, and how the reconciliation job handles the "what actually happened at the bank" confirmation that arrives hours or days later.

### Design choices made here

**Two Kafka topics instead of one**
- Topic 1 (immediate ACK) and Topic 2 (final settlement) have fundamentally different consumers, retention needs, and processing logic. Mixing them in one topic means consumers must filter by event type — fragile and error-prone. Two topics give clear ownership.

**Collector Callback Service as a pure ingestor**
- It receives the callback from the processor and immediately puts it on Kafka. It does zero business logic. This keeps it stateless, fast, and easy to scale. Business logic belongs in the consumers.

**Orchestrator as the single DB writer (Topic 1 consumer)**
- Only one service updates `status` in PaymentTransactionDB. If both Orchestrator and Reconciler could write the same row, race conditions corrupt the status field. Single-writer = no race.

**Reconciliation Service (Topic 2 consumer)**
- Writes to an append-only ledger table — never updates existing rows. This gives an immutable audit trail required by financial regulators. The ledger is the source of truth; the transaction table is the operational view.

**Why Kafka offset commit happens AFTER DB write**
- If the consumer crashes between reading the message and writing to DB, Kafka replays the message on restart (offset not committed = message not acknowledged). This gives at-least-once delivery. Combined with DB idempotency (upsert on txn_id), the net effect is exactly-once processing.

### Cross questions an interviewer will ask
| Question | What they're testing |
|---|---|
| "What is the difference between at-least-once and exactly-once delivery?" | At-least-once = message replayed on failure (duplicates possible); exactly-once = deduplication at consumer using idempotency key |
| "Why not use a database queue (Postgres LISTEN/NOTIFY) instead of Kafka?" | Postgres queue doesn't scale to 10k/s, no replay, no fan-out to multiple consumers, no built-in retention |
| "What happens if Topic 2 has a message but the Reconciliation Service is down for 2 days?" | Kafka retains messages per retention policy (default 7 days). Service comes back, reads from its last committed offset, processes all missed messages. No data loss. |
| "Why is the ledger table append-only?" | Financial audit requirement. You must be able to reconstruct every status transition. Updating a row destroys history. |
| "How do you handle duplicate callbacks from the processor?" | Idempotency: consumer checks if `txn_id` already has this status before writing. If yes, skip and commit offset. Kafka key = txn_id ensures same partition = ordered processing. |
| "What if two reconciliation jobs run at the same time?" | Distributed lock (Redis SETNX on job_id) or Kafka consumer group ensures only one instance processes a partition. |

---

## 7. Component Choices — Why We Picked Each One

### 7.1 Database Choices

```
┌────────────────────────────────────────────────────────────────────────────┐
│  SERVICE              │ DB TYPE      │ WHY                                 │
├───────────────────────┼──────────────┼─────────────────────────────────────┤
│ Payment Intent DB     │ PostgreSQL   │ Strong ACID, payment metadata needs  │
│                       │ (RDBMS)      │ consistency. No partial writes.       │
├───────────────────────┼──────────────┼─────────────────────────────────────┤
│ Session Store         │ Redis        │ Short-lived (TTL=10min). Sub-ms      │
│                       │ (Cache)      │ lookup. Low latency requirement.     │
├───────────────────────┼──────────────┼─────────────────────────────────────┤
│ Payment Transaction   │ PostgreSQL   │ Core transactional data. Needs joins │
│ DB                    │ (RDBMS)      │ (txn ↔ intent ↔ merchant). ACID.    │
├───────────────────────┼──────────────┼─────────────────────────────────────┤
│ Merchant Preference   │ PostgreSQL   │ Config data, rarely changes, needs   │
│ DB                    │ (RDBMS)      │ consistency over speed.              │
├───────────────────────┼──────────────┼─────────────────────────────────────┤
│ Reconciliation        │ PostgreSQL   │ Immutable ledger (append-only rows). │
│ Ledger Table          │ (RDBMS)      │ Audit trail, financial compliance.   │
└────────────────────────────────────────────────────────────────────────────┘

  WHY NOT NoSQL (MongoDB/Cassandra)?
  → Payments require strong consistency (CP over AP in CAP theorem).
  → Eventual consistency = risk of double charge or missed debit.
  → RDBMS gives serializable transactions, foreign key integrity, rollback.
```

**Why this choice?** Every financial record must be recoverable, auditable, and immune to partial writes. PostgreSQL's ACID guarantees mean a payment intent row is either fully written or not written at all — no half-created record that confuses reconciliation. The only exception is session data which is intentionally ephemeral, so Redis is the right fit there.

**Cross questions:**
| Question | What they're testing |
|---|---|
| "Can you scale PostgreSQL to 10k TPS?" | Yes: PgBouncer (connection pooling) + read replicas for status queries + partitioning by date |
| "Why not use a single shared DB for all services?" | Tight coupling — schema changes in one service break others. Each service owns its data (database-per-service pattern). |
| "What is PgBouncer and why do we need it?" | Connection pooler. PostgreSQL supports ~500 native connections; 10k services would exhaust them. PgBouncer multiplexes thousands of app connections onto a small DB pool. |
| "Would you use DynamoDB here?" | No for transactional data. DynamoDB is eventually consistent by default; strong consistency is opt-in and slower. For non-financial config data it would be fine. |

```
┌────────────────────────────────────────────────────────┐
│              CAP THEOREM FOR PAYMENT GATEWAY           │
│                                                        │
│   Consistency ────────────────────────────── ✓ CHOSEN │
│   Availability ─────────────────────── ✓ (secondary)  │
│   Partition Tolerance ──────────────── ✓ (always)     │
│                                                        │
│   WE CHOOSE: CP (Consistency + Partition Tolerance)    │
│                                                        │
│   Reason: A user must NEVER be charged twice.          │
│   It is acceptable for the system to be briefly        │
│   unavailable. It is NOT acceptable for data to be     │
│   inconsistent (double debit = financial loss + legal).│
│                                                        │
│   Implication: PostgreSQL with synchronous replication │
│   rather than Cassandra with eventual consistency.     │
└────────────────────────────────────────────────────────┘
```

**Why this choice?** In the CAP theorem you can only pick two of three. Partition tolerance is non-negotiable in any distributed system. So the real choice is C vs A. For money: consistency wins. A brief outage is an inconvenience; a double debit is a lawsuit.

**Cross questions:**
| Question | What they're testing |
|---|---|
| "Does choosing CP mean the system can go down?" | Yes, briefly — during a network partition a CP system rejects writes rather than risking inconsistency. The system prefers to return an error over risking a duplicate charge. |
| "Can you name a real payment system that chose AP and regretted it?" | Yes — some early PayPal and fintech systems using Cassandra saw phantom double charges due to eventual consistency. This is why all major payment rails use RDBMS. |
| "Isn't it possible to be both highly available AND consistent?" | Only with extreme engineering (Google Spanner uses atomic clocks). At normal scale, no. |
| "What does synchronous replication mean vs asynchronous?" | Synchronous = primary waits for replica to confirm write before responding (strong consistency, slower). Async = primary responds immediately, replica catches up later (faster but can lose data). |

```
┌────────────────────────────────────────────────────────┐
│  WHY REDIS FOR SESSION (NOT POSTGRES)?                 │
│                                                        │
│  1. TTL support out-of-the-box (TTL = session timer)   │
│     → Postgres would need a cron job to expire rows    │
│                                                        │
│  2. Sub-millisecond reads → latency SLA = 200ms total  │
│     → Every DB round-trip matters in this budget       │
│                                                        │
│  3. Session data is ephemeral — no need for persistence│
│     → If Redis node dies, user retries (session gone)  │
│     → That is acceptable UX for a payment flow        │
│                                                        │
│  4. Atomic SET NX (set if not exists) prevents         │
│     duplicate session creation under race conditions   │
└────────────────────────────────────────────────────────┘
```

**Why this choice?** Sessions are the one place where speed beats persistence. A 10ms Redis read fits inside the 200ms total latency budget. A Postgres read under load adds 5–20ms and consumes a DB connection — for data that expires in 10 minutes anyway.

**Cross questions:**
| Question | What they're testing |
|---|---|
| "What if Redis goes down and all sessions are lost?" | Users mid-checkout lose their session and must restart. This is acceptable — session loss is UX friction, not a financial inconsistency. Redis Cluster with 2 replicas makes this rare. |
| "What is Redis SETNX and why use it?" | SET if Not eXists — atomically creates a key only if it doesn't already exist. Prevents two concurrent session creation requests from generating two sessions for the same intent. |
| "Why TTL=10 minutes specifically?" | Long enough for a user to enter card details (typical ~2–3 min). Short enough to limit fraud window. The UI countdown is just this TTL rendered visually. |
| "Could you use Memcached instead of Redis?" | Memcached has no TTL-per-key, no SETNX atomicity, no persistence option. Redis is the right choice here. |

### 7.4 Adapter / Strategy Pattern for Processor Connectors

```
┌────────────────────────────────────────────────────────────┐
│  ADAPTER PATTERN — PROCESSOR CONNECTORS                    │
│                                                            │
│  Problem: PayU, Razorpay, Stripe all have different        │
│  request/response schemas.                                 │
│                                                            │
│  ┌──────────────────┐                                      │
│  │  Orchestrator    │                                      │
│  │  (knows only the │                                      │
│  │   interface)     │                                      │
│  └────────┬─────────┘                                      │
│           │ calls ProcessorConnector.charge(token, amount) │
│           │                                                │
│    ┌──────┴───────────────────────────┐                    │
│    │  <<interface>> ProcessorConnector│                    │
│    │  + charge(token, amount): Result │                    │
│    └──────┬──────────────────┬────────┘                    │
│           │                  │                             │
│    ┌──────▼──────┐   ┌───────▼──────┐                     │
│    │ PayuConn.   │   │ RazorpayConn.│  ...                 │
│    │             │   │              │                      │
│    │ translates  │   │ translates   │                      │
│    │ to PayU API │   │ to Razorpay  │                      │
│    │ schema      │   │ API schema   │                      │
│    └─────────────┘   └──────────────┘                      │
│                                                            │
│  Adding a new processor = add one Connector class.         │
│  Orchestrator stays unchanged.                             │
└────────────────────────────────────────────────────────────┘
```

**Why this choice?** Without the Adapter pattern, the Orchestrator would have `if processor == "payu"` ... `else if processor == "razorpay"` ... branches everywhere. Every new processor requires modifying the Orchestrator — violating Open/Closed Principle. With adapters, the Orchestrator is frozen; only a new Connector class is added.

**Cross questions:**
| Question | What they're testing |
|---|---|
| "What design pattern is this?" | Adapter + Strategy. Adapter: each connector translates to a specific API schema. Strategy: Orchestrator selects which connector to use at runtime based on merchant preference. |
| "How do you add a new processor (e.g., Stripe) without downtime?" | Write a new `StripeConnector` implementing `ProcessorConnector` interface. Deploy it. Update MerchantPreferenceDB to route some merchants to Stripe. Zero changes to Orchestrator. |
| "What if a processor changes their API schema?" | Only that specific Connector class is updated. Other connectors and the Orchestrator are untouched. |
| "How does the Orchestrator know which Connector to instantiate?" | Dependency injection or a factory: `ConnectorFactory.get(processorName)` returns the correct implementation. |

```
┌────────────────────────────────────────────────────────────┐
│  WHY KAFKA FOR CALLBACKS (NOT DIRECT DB WRITE)?            │
│                                                            │
│  Direct write problem:                                     │
│  Callback Service ──► DB   ← multiple callbacks for same  │
│                              txn_id can race → duplicates  │
│                                                            │
│  Kafka solves this:                                        │
│  1. Idempotent producer — same message delivered once      │
│  2. Consumer group ensures one consumer processes a msg    │
│  3. Replay capability — if DB is down, messages wait       │
│  4. Decouples callback receiver from DB write logic        │
│  5. Audit trail — Kafka topic is the source of truth       │
│                                                            │
│  Pattern used: Push-Subscribe (Event-Driven)              │
│  Callback Service = Producer                              │
│  Orchestrator + Reconciler = Consumers                    │
└────────────────────────────────────────────────────────────┘
```

**Why this choice?** The processor can send multiple callbacks for the same transaction (retries, status updates). Writing directly to the DB from the callback receiver under concurrent load causes race conditions and duplicate writes. Kafka serializes the events per partition (keyed on `txn_id`), decouples producers from consumers, and gives replay capability when a consumer is down.

**Cross questions:**
| Question | What they're testing |
|---|---|
| "Why not RabbitMQ instead of Kafka?" | RabbitMQ is great for task queues but messages are deleted after consumption — no replay. Kafka retains messages for days, which is critical for reconciliation replay. |
| "What is a consumer group?" | A set of consumers that jointly consume a topic. Each partition is consumed by exactly one consumer in the group — ensures no two consumers process the same message simultaneously. |
| "How do you ensure message ordering?" | Kafka guarantees ordering within a partition. By keying messages on `txn_id`, all events for the same transaction go to the same partition — processed in order. |
| "What is the dead-letter queue for?" | Messages that fail processing after N retries are sent to a DLQ topic. An alert fires; an operator investigates. Prevents one bad message from blocking the consumer indefinitely. |
| "How many partitions should the topic have?" | At least equal to the max expected consumer parallelism. For 10k TPS with ~10 consumer instances, 10–20 partitions is a starting point. More partitions = more parallelism. |

### 7.6 Separate Load Balancer for Checkout Frontend

```
┌────────────────────────────────────────────────────────────┐
│  WHY SEPARATE LB FOR CHECKOUT FRONTEND?                    │
│                                                            │
│  API Gateway (backend services):                          │
│  • Handles auth/authz headers                             │
│  • Routes to microservices                                │
│  • Has rate-limiting per merchant API key                 │
│                                                            │
│  Checkout Frontend LB:                                    │
│  • Pure HTTP traffic (no auth header needed)              │
│  • Serves static-ish HTML — can sit behind CDN            │
│  • Different scaling rules (static asset vs API)          │
│  • Browser-facing, not service-facing                     │
│                                                            │
│  Mixing them = over-engineering the API GW with browser   │
│  traffic rules, and missing CDN caching opportunity.      │
└────────────────────────────────────────────────────────────┘
```

**Why this choice?** The checkout HTML page is essentially a template — same structure for every user, only the session_id changes. Putting it behind a CDN means edge nodes cache the page shell globally, and only the dynamic session token is fetched at runtime. An API Gateway adds auth-header parsing overhead to every page load, which provides zero security benefit for a public HTML page.

**Cross questions:**
| Question | What they're testing |
|---|---|
| "What does a CDN cache in this scenario?" | The HTML template + JS/CSS assets of the checkout page. The session_id is injected client-side after load — it's not baked into the cached HTML. |
| "What if you need to update the checkout page UI?" | Cache invalidation: CDN purge on deploy. Blue-green deployment of the frontend service with CDN cache version bump. |
| "Does the checkout frontend need to be stateless?" | Yes — it renders the same HTML for any session. State lives in Redis (session) and the browser (form inputs). Stateless services scale horizontally without sticky sessions. |
| "Could you just use an S3 bucket + CloudFront for this?" | Almost — but the page needs to verify the session_id exists in Redis before rendering (otherwise dead links get a page). So a thin compute layer (Lambda@Edge or a lightweight service) is still needed. |

---

## 8. Failure Cases & Edge Cases

### 8.1 Failure Matrix

```
┌──────────────────────────────────────────────────────────────────────────┐
│  FAILURE CASE           │ WHAT HAPPENS              │ MITIGATION          │
├─────────────────────────┼───────────────────────────┼─────────────────────┤
│ Redis session expired   │ User clicks Pay after 10  │ Return 440 Session  │
│ before user pays        │ min. Session key missing. │ Timeout. Merchant   │
│                         │                           │ must restart flow.  │
├─────────────────────────┼───────────────────────────┼─────────────────────┤
│ Processor network       │ HTTP call to PayU times   │ Retry with          │
│ timeout                 │ out. No callback arrives. │ exponential backoff │
│                         │                           │ (3 attempts). Mark  │
│                         │                           │ txn as TIMEOUT.     │
│                         │                           │ Reconciliation fixes│
│                         │                           │ status next day.    │
├─────────────────────────┼───────────────────────────┼─────────────────────┤
│ Duplicate Pay request   │ User double-clicks Pay.   │ Idempotency key in  │
│ (double-click / retry)  │ Two identical requests    │ request. Redis SET  │
│                         │ hit backend.              │ NX on txn_id.       │
│                         │                           │ Second request = 409│
├─────────────────────────┼───────────────────────────┼─────────────────────┤
│ Money debited but        │ Bank debits user but      │ Reconciliation job  │
│ gateway never got        │ network drops before      │ at T+24h tallies    │
│ callback                │ callback reaches us.      │ bank ledger vs our  │
│                         │                           │ DB. Auto-refund or  │
│                         │                           │ status fix.         │
├─────────────────────────┼───────────────────────────┼─────────────────────┤
│ Kafka consumer dies      │ Callback status not       │ Kafka offset not    │
│ mid-processing           │ written to DB.            │ committed until DB  │
│                         │                           │ write succeeds.     │
│                         │                           │ Consumer restarts   │
│                         │                           │ and re-processes.   │
├─────────────────────────┼───────────────────────────┼─────────────────────┤
│ HSM unavailable          │ Tokenization fails.       │ HSM cluster (active │
│                         │ Card cannot be encrypted. │ -active). Circuit   │
│                         │                           │ breaker returns     │
│                         │                           │ 503. Retry later.   │
├─────────────────────────┼───────────────────────────┼─────────────────────┤
│ Malformed session ID     │ Attacker modifies session │ Session ID is a     │
│ in URL (tampering)       │ ID in URL.                │ random UUID (not    │
│                         │                           │ guessable). Redis   │
│                         │                           │ lookup fails → 401. │
├─────────────────────────┼───────────────────────────┼─────────────────────┤
│ Payment Intent created  │ Orphan intent in DB.      │ Scheduled cleanup   │
│ but session never        │ Wasted storage.           │ job: delete intents │
│ created                 │                           │ older than 24h with │
│                         │                           │ status=PENDING.     │
└──────────────────────────────────────────────────────────────────────────┘
```

### Why this diagram exists
Failures in a payment system are not edge cases — they are certainties at 10k TPS. This matrix forces you to enumerate every component that can fail and proves you've thought about **recovery, not just the happy path**. Interviewers mark you down heavily if you only describe the success flow.

### Cross questions an interviewer will ask on the failure matrix
| Failure | Cross question | Expected answer |
|---|---|---|
| Redis session expired | "What error code do you return?" | 440 Session Timeout or 408 Request Timeout — not a 500. The user's action is valid; the session just expired. |
| Processor timeout | "How many retries and what backoff?" | 3 attempts: 1s, 5s, 15s. After 3 failures mark txn as TIMEOUT, return 202 to user, reconciliation resolves it. |
| Duplicate Pay request | "What if the idempotency key itself is lost?" | If the merchant doesn't send one, generate one server-side from `session_id + intent_id` hash — same inputs always produce the same key. |
| Money debited, no callback | "How long does the user see 'pending'?" | Until reconciliation runs (~24h). The merchant's UI should show "Payment processing" with a support contact, not a hard failure. |
| Kafka consumer dies | "What guarantees no message is lost?" | Kafka offset only committed after successful DB write. Consumer restart replays from last committed offset. |
| HSM unavailable | "Is HSM a single point of failure?" | No — active-active HSM cluster. But if the entire cluster goes down, no payment can be processed. This is a hard dependency with no software fallback. |

```
┌────────────────────────────────────────────────────────────────────────────┐
│                  DOUBLE DEBIT SCENARIO & PREVENTION                        │
│                                                                            │
│  BAD CASE (without idempotency):                                           │
│                                                                            │
│  User ──► Click Pay ──► Request A ──► Processor ──► Bank debits $100      │
│                                                                            │
│  User ──► (impatient) ──► Click Pay again                                  │
│           Request B ──► Processor ──► Bank debits $100 AGAIN               │
│           Total charged: $200  ← DISASTER                                  │
│                                                                            │
│  SOLUTION — Idempotency Key:                                               │
│                                                                            │
│  Client sends: POST /pay { idempotency_key: "txn_abc123", ... }           │
│                                                                            │
│  Checkout Backend:                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  Redis.SETNX("idem:txn_abc123", "processing", TTL=5min)            │  │
│  │  ├── returns 1 (new key) → process the payment                     │  │
│  │  └── returns 0 (key exists) → return 409 Conflict / cached response│  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  Request A → SETNX returns 1 → processed → bank charges once              │
│  Request B → SETNX returns 0 → rejected immediately → no second charge    │
└────────────────────────────────────────────────────────────────────────────┘
```

### Why this diagram exists
Double debit is the single most catastrophic bug a payment gateway can have. It destroys user trust instantly and triggers regulatory investigation. This diagram shows the specific mechanism — **Redis atomic SETNX as an idempotency gate** — that makes it physically impossible to charge twice for the same transaction.

### Design choices made here
- Idempotency key is sent by the **merchant** (not generated by the user). The merchant generates it from their order_id — same order always produces the same key.
- SETNX has a **TTL** (5 min). After the payment is fully processed (success or failure), the key is deleted. If the merchant retries after 24 hours for a different reason, the key no longer blocks.
- The idempotency check happens **before** tokenization and before the processor call — no HSM call wasted on a duplicate.

### Cross questions an interviewer will ask
| Question | What they're testing |
|---|---|
| "What if two requests with the same idempotency key arrive at the same millisecond?" | Redis SETNX is atomic — guaranteed by Redis's single-threaded command execution. One gets 1 (proceeds), the other gets 0 (rejected). No race. |
| "What response do you return to the duplicate request?" | 409 Conflict with the original response body cached in Redis — the merchant sees the same result as the first call. |
| "What is the difference between idempotency and deduplication?" | Idempotency: same input always produces the same output, safe to retry. Deduplication: detect and discard duplicate messages. Idempotency is the contract; deduplication is the implementation. |
| "What if the merchant forgets to send an idempotency key?" | Server-side: generate one from `hash(session_id + intent_id + amount)`. Same merchant + same session + same amount = same key. Defense in depth. |

### 8.3 Failure Flow — Processor Timeout with Reconciliation

```
Normal flow:
  Orchestrator ──► Processor ──► Bank ──► Callback ──► Kafka ──► DB

Timeout flow:
  Orchestrator ──► Processor ──► Bank (debits)
                          ↓
                   Network drops
                          ↓
  Callback NEVER arrives at Collector Service
                          ↓
  DB status stays as: SENT (stuck)
                          ↓
  ┌──────────────────────────────────────────────┐
  │  RECONCILIATION JOB (runs every 24h)         │
  │                                              │
  │  1. Find all txns with status=SENT older     │
  │     than 1h                                  │
  │  2. Query processor API for final status     │
  │  3a. Processor says SUCCESS → update DB      │
  │  3b. Processor says FAILED  → update DB,     │
  │      trigger refund workflow                 │
  │  3c. Processor has no record → flag for      │
  │      manual review                           │
  └──────────────────────────────────────────────┘
```

### Why this diagram exists
This is the most realistic failure in production payments. Network blips between the orchestrator and processor are common. The diagram shows the **exact state machine** — SENT → stuck → reconciliation resolves — and proves you've thought about what happens when neither success nor failure is confirmed.

### Design choices made here
- Status `SENT` is the "in-flight" marker. Writing it **before** calling the processor ensures a record exists even if the process crashes mid-call.
- The reconciliation job queries the **processor's API** (not just our DB) — it asks "what do you know about txn_id X?" This is the authoritative source for what actually happened at the bank.
- "Processor has no record" is a third outcome — it means the request never reached the processor at all. Safe to retry or cancel.
- Manual review flag is non-negotiable. Financial regulators require a human audit trail for unresolved transactions.

### Cross questions an interviewer will ask
| Question | What they're testing |
|---|---|
| "How long do you wait before running reconciliation?" | At minimum the bank's settlement window (T+1 or T+2). For stuck `SENT` transactions older than 1 hour, the job runs every hour as an early sweep. |
| "What if reconciliation runs twice on the same transaction?" | It must be idempotent. Reading processor status and writing to DB is a read-then-conditional-update: only update if current status allows it (e.g., don't overwrite SETTLED with FAILED). |
| "What's the difference between a timeout and a failure?" | Timeout = no response received (unknown outcome). Failure = processor responded with explicit error (known outcome). Timeout requires reconciliation; failure can be immediately marked. |
| "What if the processor is down during reconciliation?" | Retry the reconciliation query with exponential backoff. After N attempts, flag transaction as UNRESOLVABLE and alert the ops team. Never silently ignore it. |
| "How do you prevent reconciliation from being a DB bottleneck?" | Run in batches (e.g., 1000 txns per batch), during off-peak hours. Use a separate read replica for the query scan. Write updates in bulk transactions. |

---

## 9. Interview Questions — Basic → Advanced → Traps

---

### BASIC SCENARIO QUESTIONS

**Q1. What is the difference between a Payment Gateway and a Payment Processor?**

> Gateway = orchestration layer (collects + tokenizes card data, routes to processor).
> Processor = financial entity that talks to banks (authorizes, captures, settles).
> You are designing the Gateway. The bank debit/credit is out of scope.

**Q2. Why do we need a Payment Intent before a Session?**

> Payment Intent captures the *what* (amount, currency, merchant, order) before the *how* (card details). It gives us a stable record ID to reference throughout the transaction lifecycle. The session is short-lived (10 min); the intent persists for reconciliation.

**Q3. Why is the checkout HTML page served by the Gateway and not the merchant?**

> PCI DSS compliance. If the merchant serves the card entry page, they become a PCI-scoped entity (L1 audit, massive compliance cost). The Gateway serving the page means card data never touches the merchant's servers.

**Q4. Why does the session URL contain the session ID as a query param?**

> The session ID allows the Checkout Backend to validate that the Pay request came from a legitimate session. Any tampered or expired session ID fails the Redis lookup and the request is rejected before any tokenization happens.

**Q5. What does the TTL on the Redis session represent in the UI?**

> The countdown timer visible on the checkout page. When TTL expires, Redis auto-deletes the key. The next Pay request fails validation → user must start over.

---

### INTERMEDIATE SCENARIO QUESTIONS

**Q6. The system gets 10,000 TPS. Which components are bottlenecks and how do you scale them?**

```
Component           │ Bottleneck Risk       │ Scale Strategy
────────────────────┼───────────────────────┼──────────────────────────────
Payment Intent Svc  │ DB write per request  │ Horizontal pod scaling
                    │                       │ DB connection pool (PgBouncer)
────────────────────┼───────────────────────┼──────────────────────────────
Redis Cluster       │ Memory per session    │ Redis Cluster (sharding by
                    │                       │ session_id hash)
────────────────────┼───────────────────────┼──────────────────────────────
Checkout Frontend   │ 10k HTML page loads   │ CDN + horizontal LB replicas
────────────────────┼───────────────────────┼──────────────────────────────
Tokenization/HSM    │ HSM throughput limit  │ HSM cluster (active-active),
                    │                       │ H/W has fixed IOPS ceiling
────────────────────┼───────────────────────┼──────────────────────────────
Kafka               │ Partition throughput  │ Partition by merchant_id or
                    │                       │ txn_id for even distribution
────────────────────┼───────────────────────┼──────────────────────────────
Orchestrator        │ Processor API rate    │ Per-processor rate limiter,
                    │   limits              │ queue overflow to retry topic
```

**Q7. What happens if the user pays successfully but the browser crashes before showing the success page?**

> The payment was already processed at the bank level. The status in PaymentTransactionDB is updated via Kafka regardless of browser state. The merchant receives a webhook with the final status. The user can check order status through the merchant app — the merchant queries our `/transaction/{id}` endpoint to show current status.

**Q8. How do you prevent a merchant from sending fabricated payment intents (e.g., setting amount=0.01 for a $100 item)?**

> Two controls:
> 1. During payment intent creation, the intent is signed with the merchant's API secret (HMAC signature). Any modification of amount/currency invalidates the signature.
> 2. At the Checkout Backend, before tokenization, we cross-check the session's intent_id against the PaymentIntentDB — the original amount is compared to what the processor is being told. Mismatch = reject.

**Q9. Explain the two Kafka topics and what data flows through each.**

```
Topic 1: payment.processor.callback_status
  → Written by: Collector Callback Service
  → Arrival: seconds after processor call
  → Contains: { txn_id, status: "ORDER_PLACED", processor_ref }
  → Consumer: Orchestrator Service (updates DB to PLACED)

Topic 2: payment.processor.final_status
  → Written by: Collector Callback Service
  → Arrival: 24h+ after bank settlement
  → Contains: { txn_id, status: "SUCCESS"/"FAILED", settled_amount }
  → Consumer: Reconciliation Service (writes to ledger, triggers webhooks)
```

**Q10. Why does the Orchestrator Service update the PaymentTransactionDB, not the Callback Service?**

> Single-writer principle. If both services write to the same status field, a race condition can produce inconsistent final states (e.g., FAILED overwriting SUCCESS received milliseconds later). The Orchestrator owns the transaction lifecycle; all status mutations go through it. It also ensures that the Kafka message ordering is respected before writing.

---

### ADVANCED SCENARIO QUESTIONS

**Q11. Design the reconciliation job in detail. How do you handle the case where the processor reports SUCCESS but your DB says FAILED?**

```
Reconciliation conflict resolution:

  DB status=FAILED, Processor says SUCCESS
  ──────────────────────────────────────────
  This means: our gateway marked it failed (maybe timeout)
  but the processor actually succeeded with the bank.

  Steps:
  1. Check if refund was already issued → if yes, refund was wrong,
     initiate refund reversal, mark txn SETTLED
  2. If no refund yet → update DB to SETTLED, notify merchant via webhook
  3. Flag for manual audit (compliance requirement)
  4. Merchant notifies customer of correct status

  DB status=SUCCESS, Processor says FAILED
  ──────────────────────────────────────────
  This means: gateway told merchant success, bank rejected.

  Steps:
  1. Initiate automatic refund workflow (if not already done)
  2. Update DB to REFUNDED
  3. Send webhook to merchant with PAYMENT_FAILED event
  4. Merchant must ask user to retry payment
  5. Log incident for SLA violation tracking
```

**Q12. How do you handle a split payment (out of scope here, but how would you extend)?**

> Extend PaymentIntent with a `splits` array: `[{merchant_id, amount}]`. The Orchestrator would fan out to N processor calls, one per split recipient. Each gets its own txn record in PaymentTransactionDB linked to the parent intent_id. Reconciliation runs per-split txn. If one split fails, we need a compensation saga: attempt refund on all succeeded splits.

**Q13. A high-profile merchant wants to use their own processor for 80% of transactions and failover to yours. How do you support this?**

> Add a routing strategy field to MerchantPreferenceDB:
```
{
  merchant_id: "amazon",
  primary_processor: "amazon_payment_services",
  primary_weight: 80,
  fallback_processor: "razorpay",
  fallback_weight: 20,
  fallback_on: ["TIMEOUT", "PROCESSOR_ERROR"]
}
```
> Orchestrator reads the strategy, uses weighted random selection (or circuit-breaker state) to route. If primary processor returns 5xx or timeout, Orchestrator retries immediately on fallback. This is the Strategy + Circuit Breaker pattern.

**Q14. How would you implement fraud detection in this architecture?**

> Insert a Fraud Detection Service between Checkout Backend and Tokenization:
```
  Checkout Backend
       │
       ▼
  Fraud Detection Service
  • ML model: velocity checks (same card used 5x in 1 min)
  • Fingerprint matching: device fingerprint + card fingerprint
  • Geo-mismatch: billing country ≠ IP country
  • Card BIN vs issuing bank country check
  • Score threshold: < 30 = allow, 30-70 = 3DS challenge, > 70 = reject
       │
  ┌────┴──────────────────┐
  allow         challenge/reject
       │
  Tokenization Service
```
> This is a synchronous check within the 200ms latency budget (model inference ~10ms). High-risk transactions trigger 3D Secure (OTP from bank), adding an out-of-band verification step.

**Q15. How do you ensure PCI DSS compliance across the system?**

```
PCI DSS Control Points:

1. Network segmentation
   └─ PCI zone (Tokenization + HSM) on isolated VPC subnet
   └─ No inbound traffic except from Checkout Backend on port 8443

2. Card data never stored in plaintext
   └─ Only encrypted_token + fingerprint stored
   └─ Raw PAN exists only in HSM memory during encryption cycle

3. TLS everywhere inside PCI zone
   └─ mTLS between Checkout Backend ↔ Tokenization Service
   └─ Standard TLS for all other service communication

4. Access control
   └─ HSM access restricted to Tokenization Service identity only
   └─ No human operator can read HSM keys

5. Audit logging
   └─ Every card touch event logged with timestamp, service_id, operator
   └─ Immutable log (append-only, write once read many)

6. Tokenization
   └─ Token stored in Vault (HashiCorp Vault or cloud equivalent)
   └─ Token can be looked up by Orchestrator for re-auth scenarios

7. Quarterly penetration testing
   └─ External PCI-QSA audit required annually for Level 1 merchants
```

---

### TRAP QUESTIONS

**TRAP 1: "The response from the processor confirms the payment was successful. Why do we still need reconciliation?"**

> The processor's immediate response only confirms the *order was placed* with the bank, not that money was actually settled. Banks operate on settlement cycles (T+1 or T+2). The processor's final settlement confirmation arrives asynchronously. Without reconciliation, you trust an acknowledgment, not a completed financial transaction — and mismatches (insufficient funds discovered after auth, chargeback, card blocked) get missed.

**TRAP 2: "Why not store session data in PostgreSQL? Redis can go down."**

> If Redis goes down, the user simply cannot complete checkout — they see a session error and retry. That is acceptable because: (a) Redis downtime is rare with clustering, (b) session data is ephemeral anyway, and (c) storing 10k sessions/sec in Postgres would add 10k writes/sec to the same DB handling critical payment records. The latency SLA (200ms) would also be at risk.
>
> The trap is assuming Redis unreliability is a reason to avoid it. The correct response is Redis Cluster with replication (1 primary + 2 replicas), which handles single-node failure without data loss.

**TRAP 3: "The merchant says their webhook is failing. How do you ensure they receive the final status?"**

> Webhooks are fire-and-forget by default. To guarantee delivery:
> 1. Webhook Service retries with exponential backoff: 1s, 5s, 30s, 5min, 1hr
> 2. Merchant must return HTTP 200 to acknowledge receipt
> 3. After N failed attempts, escalate to dead-letter queue + alert
> 4. Merchant can always poll `/transaction/{id}` as a fallback
>
> The trap: saying "webhooks are reliable" — they are not. The merchant endpoint can be down, return 5xx, or time out. A robust gateway always pairs push (webhook) with pull (status API).

**TRAP 4: "Can we skip the payment intent step and go directly to session creation?"**

> No. The intent is the root record that ties together the order (merchant side) with the session and transaction (gateway side). Without it:
> 1. No persistent metadata before the short-lived session
> 2. Reconciliation has nothing to anchor the transaction to an order
> 3. No idempotency — merchant could create duplicate sessions for the same order
>
> The intent is the contract between merchant and gateway before any card data is involved.

**TRAP 5: "Since sessions are in Redis with TTL, do we even need to validate session expiry in the Checkout Backend?"**

> Yes, and this is a common trap. Redis TTL eviction is lazy or periodic — there can be a small window where a key is technically expired but has not yet been evicted. Also, the check in Checkout Backend is defensive programming: even if Redis evicts the key, the backend explicitly checks both existence and the session's `created_at` timestamp to ensure no race condition allows an expired session to pass validation.

**TRAP 6: "We have 10k TPS. Should we use a NoSQL database for better throughput?"**

> The CAP theorem argument here is the trap. Payment data requires strong consistency — you cannot afford eventual consistency when money is involved. PostgreSQL at 10k TPS is achievable with:
> 1. PgBouncer connection pooling (prevents connection exhaustion)
> 2. Read replicas for status polling (read-heavy queries go to replicas)
> 3. Partitioning PaymentTransactionDB by date range (hot partition isolation)
> 4. CQRS pattern: write to primary, read from replica
>
> Switching to Cassandra (eventual consistency) to gain throughput introduces the risk of double charges — a business-ending bug.

**TRAP 7: "The checkout page URL contains the session_id. Isn't that a security risk?"**

> It is by design, but mitigated:
> 1. Session IDs are cryptographically random UUIDs — not guessable
> 2. A session ID alone is insufficient — the Pay request must also carry matching intent_id, validated against Redis
> 3. Sessions expire in 10 minutes (TTL)
> 4. HTTPS-only — session ID cannot be intercepted in transit
> 5. Session ID is single-use: once Pay is submitted and processed, the session key is deleted from Redis (invalidated)
>
> The alternative (POST-based session, no ID in URL) requires stateful browser tracking — more complex, no material security gain.

**TRAP 8: "Why do we use Kafka between callback and DB instead of just writing directly to DB from callback service?"**

> Three reasons:
> 1. **Idempotency at scale**: The processor may send duplicate callbacks (retry storms). Kafka's consumer group + offset management ensures exactly-once processing when combined with DB idempotency checks.
> 2. **Fan-out**: Multiple consumers (Orchestrator + Reconciler + Webhook Service) all need the same event. Direct DB write means each must poll DB — Kafka gives event fanout for free.
> 3. **Durability during DB downtime**: If DB is momentarily unavailable, direct writes fail silently. Kafka buffers the callback so no event is lost — consumer retries when DB recovers.

---

```
┌────────────────────────────────────────────────────────────────────────┐
│                    SYSTEM DESIGN CHEAT SHEET                           │
│                                                                        │
│  Scale:          10,000 TPS                                            │
│  CAP Choice:     Consistency > Availability                            │
│  Latency SLA:    < 200ms for authorization                             │
│  Security:       PCI DSS compliant                                     │
│                                                                        │
│  Key DBs:        PostgreSQL (intent, txn, merchant, ledger)            │
│                  Redis (session, idempotency keys)                     │
│                                                                        │
│  Key Patterns:   Adapter (processor connectors)                        │
│                  Strategy (routing logic)                              │
│                  Saga (split payment compensation)                     │
│                  CQRS (read replicas for polling)                      │
│                  Circuit Breaker (processor failover)                  │
│                  Idempotency (duplicate payment prevention)            │
│                  Event-Driven (Kafka for async callbacks)             │
│                                                                        │
│  Out of Scope:   Bank debit/credit internals                          │
│                  Refund/return flows                                   │
│                  Part-payment (partial payment)                       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Rapid Answer Script — 3–5 Minute Interview Framework

> Use this when the interviewer says: "Design a payment gateway." Walk through these blocks in order.

```
BLOCK 1 — CLARIFY SCOPE (30 seconds)
─────────────────────────────────────
"Before I start, let me confirm scope. Are we designing:
  • The payment GATEWAY (card capture, tokenization, routing)? ✓
  • Or the payment PROCESSOR (bank authorization, settlement)?
Assuming gateway only — the processor and bank are external black boxes."

"Scale: 10,000 TPS? CAP preference: consistency over availability?
 Latency SLA: under 200ms for authorization? PCI DSS compliance required?"


BLOCK 2 — THREE STEPS IN EVERY PAYMENT (60 seconds)
─────────────────────────────────────────────────────
"Every payment has exactly 3 steps:

  Step 1 — PAYMENT INTENT
  User clicks Buy Now. Merchant calls us:
    POST /payment-intent {amount, currency, order_id}
  We save metadata to Postgres, return payment_intent_id.
  The card details are NOT involved yet.

  Step 2 — CHECKOUT SESSION
  Merchant calls:
    POST /session {payment_intent_id}
  We create a Redis session (TTL = 10 min), return:
    {session_id, redirect_url: 'gw.io/{session_id}'}
  Merchant redirects user's browser to our URL.
  Our checkout frontend serves the card-entry HTML page.
  The countdown timer = Redis TTL rendered in the UI.

  Step 3 — PAY
  User enters card details on OUR page, clicks Pay.
  Browser posts directly to our checkout backend:
    POST /pay {session_id, card_number, cvv, expiry}
  We validate session → tokenize (PCI zone, HSM) →
  orchestrate to processor → async callback via Kafka."


BLOCK 3 — KEY COMPONENTS (90 seconds)
───────────────────────────────────────
"Five components worth depth:

  1. PCI Zone / HSM: Card never stored in plaintext.
     Tokenization = validate card → fingerprint (BIN+last4+expiry+name → SHA256)
     → encrypt PAN via HSM. Only encrypted_token leaves the zone.

  2. Orchestrator + Adapter Pattern:
     Reads MerchantPreferenceDB → picks connector (PayU/Razorpay) →
     saves status=SENT before calling processor → calls connector.
     Adding a new processor = one new Connector class, Orchestrator unchanged.

  3. Two Kafka Topics:
     Topic 1 (immediate ACK): Collector → Orchestrator updates DB to PLACED
     Topic 2 (final settlement, T+24h): Collector → Reconcile Service → ledger

  4. Idempotency: Redis SETNX on txn_id. Second Pay click = 409 immediately.

  5. Reconciliation: Nightly job tallies Topic 2 against DB. Resolves 'SENT'
     transactions that never got a callback. Writes to immutable ledger table."


BLOCK 4 — CAP + FAILURE (30 seconds)
──────────────────────────────────────
"CAP choice: CP. A brief outage is acceptable; double debit is not.
 All persistence is PostgreSQL (ACID) except session data (Redis, ephemeral).
 Biggest failure: processor callback never arrives.
 Solution: status stays SENT, reconciliation job resolves at T+24h."
```

---

## 11. Functional & Non-Functional Requirements

### Functional Requirements

```
┌─────────────────────────────────────────────────────────────────────┐
│               FUNCTIONAL REQUIREMENTS (In-Scope)                    │
├─────┬───────────────────────────────────────────────────────────────┤
│ FR1 │ Client (merchant) should be able to make a PAYMENT INTENT      │
│     │ request — submit order metadata before card details are given  │
├─────┼───────────────────────────────────────────────────────────────┤
│ FR2 │ Gateway must create a TEMPORARY SESSION PAGE (hosted by us)    │
│     │ where the user can safely enter their card credentials         │
├─────┼───────────────────────────────────────────────────────────────┤
│ FR3 │ Securely handle PCI DSS compliant data — card details must     │
│     │ be tokenized and encrypted; never stored or logged in plaintext│
├─────┼───────────────────────────────────────────────────────────────┤
│ FR4 │ Once transaction is done, return TRANSACTION STATUS to the     │
│     │ client via webhook push AND GET /transaction/{id} pull         │
└─────┴───────────────────────────────────────────────────────────────┘

OUT OF SCOPE:
  ✗  Part payment / split payment
  ✗  Refund or return flows
  ✗  Bank-level debit/credit internals
  ✗  Processor and card network internals
```

### Non-Functional Requirements

```
┌──────────────────────────────────────────────────────────────────────┐
│               NON-FUNCTIONAL REQUIREMENTS                            │
├──────────────┬───────────────────────────────────────────────────────┤
│ Scale        │ 10,000 TPS (transactions per second)                  │
│              │ → Independent horizontal scaling per microservice     │
├──────────────┼───────────────────────────────────────────────────────┤
│ CAP Theorem  │ CP — Consistency over Availability                    │
│              │ We deal with money: brief outage OK, double debit NOT │
├──────────────┼───────────────────────────────────────────────────────┤
│ Latency      │ < 200ms for payment AUTHORIZATION                     │
│              │ (covers: session validation + tokenization only)      │
│              │ The processor → bank round-trip is out of our SLA     │
├──────────────┼───────────────────────────────────────────────────────┤
│ Security     │ PCI DSS compliant                                     │
│              │ • Isolated PCI zone (VPC subnet, mTLS)                │
│              │ • HSM for PAN encryption (FIPS 140-2 Level 3)         │
│              │ • No raw card data stored or logged anywhere          │
└──────────────┴───────────────────────────────────────────────────────┘
```

---

## 12. Core Entities

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          6 CORE ENTITIES                                     │
├──────────────────────┬───────────────────────────────────────────────────────┤
│ Merchant / Client    │ The business that has integrated our gateway           │
│                      │ (Amazon, Flipkart, Walmart). They call our APIs        │
│                      │ on behalf of their customers. They NEVER see raw       │
│                      │ card data.                                             │
├──────────────────────┼───────────────────────────────────────────────────────┤
│ Transaction          │ The actual payment event. Has lifecycle states:        │
│                      │ SENT → PLACED → SETTLED / FAILED                       │
│                      │ Stored in PaymentTransactionDB (Postgres).             │
├──────────────────────┼───────────────────────────────────────────────────────┤
│ Payment Method       │ The card type the user selects — Visa, Mastercard,    │
│                      │ Rupay, debit or credit. BIN (first 6 digits) identifies│
│                      │ the issuing bank and network. Used for routing.        │
├──────────────────────┼───────────────────────────────────────────────────────┤
│ User / Customer      │ The end buyer who enters card details on the           │
│                      │ gateway-hosted checkout page. Their credentials stay  │
│                      │ within our PCI zone — never reach the merchant.        │
├──────────────────────┼───────────────────────────────────────────────────────┤
│ Webhook              │ The server-to-server push notification we send to the  │
│                      │ merchant when payment status changes (success/failure).│
│                      │ Retried with exponential backoff. Merchant must ACK.   │
├──────────────────────┼───────────────────────────────────────────────────────┤
│ Payment Session      │ Short-lived (TTL = 10 min) auth context stored in      │
│                      │ Redis. Created after payment intent. The redirect URL  │
│                      │ embeds the session_id for downstream validation.       │
│                      │ Session expiry = countdown timer in the UI.            │
└──────────────────────┴───────────────────────────────────────────────────────┘
```

**Why entities matter in the interview:**
The interviewer often asks "what are the core entities?" early. Listing these six proves you understand the *domain* before touching architecture. Each entity maps to a service, a DB table, and a failure mode — they are not just data models.

---

## 13. API Design

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    4 API ENDPOINTS — PAYMENT GATEWAY                     │
└──────────────────────────────────────────────────────────────────────────┘

─────────────────────────────────────────────────────────────────────────────
STEP 1 — Create Payment Intent
─────────────────────────────────────────────────────────────────────────────
POST /payment-intent
  Authorization: Bearer <merchant_api_key>

  Request body:
  {
    "amount":       10000,          // in smallest currency unit (paise/cents)
    "currency":     "INR",
    "merchant_id":  "merch_abc",
    "order_id":     "order_xyz",
    "customer_id":  "cust_123",
    "payment_method_type": "CARD"
  }

  Response 201 Created:
  {
    "payment_intent_id": "pi_a1b2c3d4",
    "status": "CREATED",
    "created_at": "2026-08-22T10:00:00Z"
  }

  What happens inside:
  → Payment Intent Service saves all metadata to Postgres (PaymentIntentDB)
  → Returns stable intent_id — anchors this transaction for reconciliation
  → Card data is NOT involved at this step


─────────────────────────────────────────────────────────────────────────────
STEP 2 — Create Checkout Session
─────────────────────────────────────────────────────────────────────────────
POST /session
  Authorization: Bearer <merchant_api_key>

  Request body:
  {
    "payment_intent_id": "pi_a1b2c3d4",
    "transaction_id":    "txn_987",
    "success_url":       "https://amazon.com/order/xyz/success",
    "cancel_url":        "https://amazon.com/order/xyz/cancel"
  }

  Response 200 OK:
  {
    "session_id":       "sess_e5f6g7h8",
    "redirect_url":     "https://checkout.gateway.io/sess_e5f6g7h8",
    "expires_in_secs":  600              // = Redis TTL = UI countdown
  }

  What happens inside:
  → Checkout Session Service stores {session_id, intent_id, merchant_id,
    order_id, expiry} in Redis with TTL=600s
  → redirect_url contains session_id as the path — merchant redirects
    user browser to this URL
  → Checkout Frontend Service serves the card-entry HTML page at this URL


─────────────────────────────────────────────────────────────────────────────
STEP 3 — Submit Payment (card details sent directly to gateway)
─────────────────────────────────────────────────────────────────────────────
POST /pay
  (No merchant auth header — this is a browser-to-gateway call)

  Request body:
  {
    "session_id":    "sess_e5f6g7h8",   // from URL path
    "intent_id":     "pi_a1b2c3d4",
    "card_number":   "4111111111111234",
    "cvv":           "123",
    "expiry":        "12/27",
    "cardholder":    "John Doe",
    "idempotency_key": "idem_abc123"    // generated by merchant from order_id
  }

  Response 202 Accepted (async — payment processing started):
  {
    "txn_id":   "txn_987",
    "status":   "PENDING",
    "poll_url": "https://gateway.io/transaction/txn_987"
  }

  What happens inside:
  → Checkout Backend validates: session exists in Redis? session expired?
    intent_id matches? idempotency key (Redis SETNX) not duplicate?
  → Calls Tokenization Service (PCI zone, mTLS):
      validate card → generate fingerprint → encrypt PAN via HSM
  → Calls Orchestrator Service:
      reads MerchantPreferenceDB → picks connector →
      saves status=SENT to PaymentTransactionDB →
      calls processor connector → external processor → bank
  → Returns 202 immediately; processor callback arrives asynchronously


─────────────────────────────────────────────────────────────────────────────
STEP 4 — Poll Transaction Status
─────────────────────────────────────────────────────────────────────────────
GET /transaction/{txn_id}
  Authorization: Bearer <merchant_api_key>  (or session token for browser poll)

  Response 200 OK:
  {
    "txn_id":      "txn_987",
    "intent_id":   "pi_a1b2c3d4",
    "status":      "PLACED",          // PENDING → PLACED → SETTLED / FAILED
    "amount":      10000,
    "currency":    "INR",
    "merchant_id": "merch_abc",
    "processor":   "razorpay",
    "created_at":  "2026-08-22T10:00:05Z",
    "updated_at":  "2026-08-22T10:00:07Z"
  }

  Status lifecycle:
  PENDING  → request received, not yet sent to processor
  SENT     → sent to processor, awaiting callback
  PLACED   → processor confirmed order placed with bank (Topic 1 callback)
  SETTLED  → bank confirmed final settlement (Topic 2, T+24h)
  FAILED   → explicit failure from processor or bank
  TIMEOUT  → no callback received; pending reconciliation
```

**Interview tip on API design:**
> Interviewers will ask: "Why three calls instead of one?" Answer: each step has different failure modes. Intent fails = no session created (no Redis waste). Session fails = no card entry shown. Pay fails = only the tokenization and processor call are re-done. Three calls = three clean rollback points. Merging them means a single timeout forces re-entering card details.

---

## 14. Glossary — Payment Domain Terms

```
┌────────────────────────────────────────────────────────────────────────┐
│ TERM                   │ PLAIN DEFINITION                              │
├────────────────────────┼────────────────────────────────────────────────┤
│ Payment Gateway        │ Orchestration engine: collects card data,     │
│                        │ tokenizes it, routes to processor. We build   │
│                        │ this.                                         │
├────────────────────────┼────────────────────────────────────────────────┤
│ Payment Processor      │ Financial entity that talks to the bank       │
│                        │ (PayU, Razorpay, Stripe). External black box. │
├────────────────────────┼────────────────────────────────────────────────┤
│ Payment Intent         │ Durable record created before card details    │
│                        │ are given. Captures: what to charge, for      │
│                        │ whom, on which order.                         │
├────────────────────────┼────────────────────────────────────────────────┤
│ BIN Number             │ First 6 digits of a 16-digit card number.     │
│                        │ Bank Identification Number — identifies the   │
│                        │ issuing bank and card network (Visa/MC/Rupay).│
│                        │ Used for processor routing.                   │
├────────────────────────┼────────────────────────────────────────────────┤
│ PAN                    │ Primary Account Number — the full 16-digit    │
│                        │ card number. Never stored in plaintext.       │
├────────────────────────┼────────────────────────────────────────────────┤
│ HSM                    │ Hardware Security Module — a physical chip    │
│                        │ that stores encryption keys in silicon. Key   │
│                        │ never leaves the hardware. Required for PCI   │
│                        │ DSS Level 1. FIPS 140-2 Level 3 certified.    │
├────────────────────────┼────────────────────────────────────────────────┤
│ Fingerprint            │ SHA-256 hash of BIN + last4 + expiry + name.  │
│                        │ Identifies a card without storing the PAN.    │
│                        │ Same card = same fingerprint always.          │
├────────────────────────┼────────────────────────────────────────────────┤
│ PCI DSS                │ Payment Card Industry Data Security Standard. │
│                        │ Global compliance standard for any entity     │
│                        │ that stores/processes/transmits card data.    │
├────────────────────────┼────────────────────────────────────────────────┤
│ Authorization          │ Bank reserves the funds (hold). Does NOT move │
│                        │ money yet. Confirms card is valid and balance  │
│                        │ is sufficient.                                │
├────────────────────────┼────────────────────────────────────────────────┤
│ Settlement             │ Money actually moves from issuing bank to      │
│                        │ acquiring bank. Happens T+1 or T+2 days after │
│                        │ authorization.                                │
├────────────────────────┼────────────────────────────────────────────────┤
│ Issuing Bank           │ The cardholder's bank (who issued the card).  │
├────────────────────────┼────────────────────────────────────────────────┤
│ Acquiring Bank         │ The merchant's bank (who receives the money). │
├────────────────────────┼────────────────────────────────────────────────┤
│ Idempotency Key        │ A unique key per request. If the same key hits │
│                        │ twice, the second is rejected without charging │
│                        │ the user again. Prevents double debit.        │
├────────────────────────┼────────────────────────────────────────────────┤
│ Reconciliation         │ Nightly job that compares gateway DB state vs  │
│                        │ processor's actual settlement report. Resolves │
│                        │ stuck SENT transactions.                       │
└────────────────────────┴────────────────────────────────────────────────┘
```

---

## 15. What NOT to Say

```
✗  "We'll store card details in our database"
   → Immediate disqualifier. PCI DSS prohibits this. Card is tokenized on
     receipt; raw PAN exists only in HSM memory during encryption.

✗  "The merchant handles card entry on their own page"
   → Wrong. The merchant's page is out of PCI scope. The gateway hosts the
     checkout page so card data never touches merchant servers.

✗  "Use MongoDB/Cassandra for payment transactions"
   → Payments require ACID + strong consistency (CP). Eventual consistency
     = risk of double charge. PostgreSQL is the correct choice.

✗  "The pay response is synchronous — return success/failure directly"
   → Wrong. The processor → bank round-trip is async. Return 202 Accepted,
     let the client poll. Holding the HTTP connection open for seconds
     collapses under 10k TPS.

✗  "One Kafka topic for all processor callbacks"
   → Wrong. Immediate ACK (seconds) and final settlement (T+24h) have
     completely different consumers and retention needs. Two topics.

✗  "Reconciliation is optional if the processor is reliable"
   → The processor's immediate response only confirms order_placed, not
     settlement. Insufficient funds, chargebacks, and bank rejects arrive
     asynchronously. Reconciliation is mandatory for all payment gateways.

✗  "We don't need idempotency if the UI disables the Pay button"
   → Network retries, duplicate webhooks, and impatient users bypass UI
     controls. Idempotency must be enforced at the server side (Redis SETNX).

✗  "The session service and checkout frontend can share the same LB"
   → The checkout frontend is browser-facing static HTML that can sit behind
     a CDN. The API Gateway adds auth overhead that has zero security value
     for a public HTML page and prevents CDN caching.
```
